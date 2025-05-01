

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain.tools import tool

from db.session import get_session
from db.database_schema import EmailDraft, Email, Profile, Communication


load_dotenv()


LLM_DEFAULT = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


PERSONALISER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", 
     "You are an expert B2B email copywriter.\n"
     "• Greet using <<fname>>.\n"
     "• Match tone (<<tone>>).\n"
     "• Translate if needed to <<language>>.\n"
     "• Preserve URLs, markdown formatting, and tracking links.\n"
     "Only output the final personalized email body in markdown."
    ),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


@tool
def tone_shift(body: str, tone: str = "friendly") -> str:
    """Rewrite email body in requested tone."""
    prompt = f"Rewrite the email below in a {tone} tone without changing meaning:\n---\n{body}"
    return LLM_DEFAULT.predict(prompt).strip()

TOOLS = [tone_shift]


class EmailPersonaliserAgent(Runnable):
    """Generates a personalized Email from an EmailDraft and Profile."""

    def __init__(self):
        self._sf = get_session
        self.llm = LLM_DEFAULT
        self.agent = create_tool_calling_agent(
            self.llm,
            TOOLS,
            PERSONALISER_PROMPT,
        )

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        draft_id = inputs["draft_id"]

        with self._sf() as session:
            draft: EmailDraft = session.get(EmailDraft, draft_id)
            if not draft:
                raise ValueError(f"EmailDraft id={draft_id} not found")

            
            campaign_id = draft.campaign_id

            profile: Profile = (
                session.query(Profile)
                .filter_by(client_id=campaign_id)
                .first()
            )
            if not profile:
                raise ValueError(f"No profile found for campaign_id={campaign_id}")

            
            from db.database_schema import Client
            client = session.get(Client, profile.client_id)
            full_name = client.full_name if client and client.full_name else "there"

            comms: List[Communication] = (
                session.query(Communication)
                .filter_by(client_id=profile.client_id)
                .order_by(Communication.timestamp.desc())
                .limit(5)
                .all()
            )


        first_name = full_name.split()[0] if full_name else "there"
        preferred_language = profile.preferred_language or "English"
        preferred_tone = profile.preferred_contact or "friendly"
        recent_msgs = [c.content for c in comms]

        
        agent_input = (
            f"<<fname>>: {first_name}\n"
            f"<<tone>>: {preferred_tone}\n"
            f"<<language>>: {preferred_language}\n"
            f"Recent Messages: {recent_msgs}\n"
            "---\n"
            f"{draft.body_markdown}"
        )

        try:
            raw = self.agent.invoke({"input": agent_input})
            body_final = raw.get("output") if isinstance(raw, dict) else str(raw)
        except Exception:
            body_final = draft.body_markdown

        # save Email
        with self._sf() as session:
            email = Email(
                draft_id=draft.draft_id,
                personalized_body=body_final.strip(),
                is_final=False,
                approved_at=None
            )
            session.add(email)
            session.commit()
            session.refresh(email)

        return {"status": "personalised", "email_id": email.email_id}

    def invoke(self, input: Dict[str, Any], config=None) -> Dict[str, Any]:
        return self._call(input)































