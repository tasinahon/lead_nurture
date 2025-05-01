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
from db.database_schema import MessageDraft, Message, Profile, Communication


load_dotenv()


LLM_DEFAULT = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


PERSONALISER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a professional WhatsApp message rewriter.\n"
     "• Greet using <<fname>>.\n"
     "• Adjust to tone (<<tone>>).\n"
     "• Translate if needed to <<language>>.\n"
     "Keep it natural and concise for WhatsApp."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


@tool
def tone_shift(body: str, tone: str = "friendly") -> str:
    """Rewrite WhatsApp message in requested tone."""
    prompt = f"Rewrite the WhatsApp message below in a {tone} tone:\n---\n{body}"
    return LLM_DEFAULT.predict(prompt).strip()

TOOLS = [tone_shift]


class MessagePersonaliserAgent(Runnable):
    """Generates a personalized Message from MessageDraft and Profile."""

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
            draft: MessageDraft = session.get(MessageDraft, draft_id)
            if not draft:
                raise ValueError(f"MessageDraft id={draft_id} not found")

            
            profile: Profile = (
                session.query(Profile)
                .filter_by(client_id=draft.campaign_id)
                .first()
            )
            if not profile:
                raise ValueError(f"No profile found for campaign_id={draft.campaign_id}")

            
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
            f"{draft.message_text}"
        )

        try:
            raw = self.agent.invoke({"input": agent_input})
            content = raw.get("output") if isinstance(raw, dict) else str(raw)
        except Exception:
            content = draft.message_text

        
        with self._sf() as session:
            message = Message(
                draft_id=draft.draft_id,
                personalized_text=content.strip(),
                is_final=False,
                approved_at=None
            )
            session.add(message)
            session.commit()
            session.refresh(message)

        return {"status": "personalised", "message_id": message.message_id}

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)



















