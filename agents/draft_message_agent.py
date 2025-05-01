from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.agents import AgentFinish

from db.session import get_session
from db.database_schema import Strategy, Profile, Communication, MessageDraft,Campaign


load_dotenv()


LLM_DEFAULT = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3
)


DRAFT_MESSAGE_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a WhatsApp outreach assistant. Use tools to create personalized, strategic messages. Respond only with JSON."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


@tool
def generate_whatsapp_opener(profile_summary: str) -> str:
    """Create a quick personalized WhatsApp opening line."""
    prompt = (
        f"Create a friendly 1-line opener for WhatsApp based on:\n"
        f"Profile Summary: {profile_summary}\n"
        "Keep it natural, respectful, and under 20 words."
    )
    return LLM_DEFAULT.predict(prompt).strip()

@tool
def suggest_message_cta(product_type: str, interests: str = "") -> str:
    """Suggest a short call-to-action for WhatsApp messages."""
    prompt = (
        f"Suggest a WhatsApp-style CTA (<20 words) to propose next steps.\n"
        f"Product Type: {product_type}\n"
        f"Client Interests: {interests}\n"
        "Make it actionable (e.g., 'Can we hop on a quick call?')."
    )
    return LLM_DEFAULT.predict(prompt).strip()

@tool
def summarize_communications(messages: List[str]) -> str:
    """Summarize last few communications into a short overview."""
    if not messages:
        return "No prior chats."
    prompt = (
        "Recent WhatsApp communications:\n" + "\n".join(messages) + "\n\nSummarize the themes briefly (1-2 lines)."
    )
    return LLM_DEFAULT.predict(prompt).strip()

@tool
def adjust_message_tone(personality_vector: str = "", title: str = "") -> str:
    """Adjust tone for WhatsApp message based on personality and seniority."""
    tone = "friendly"
    if "strategic" in personality_vector.lower() or "visionary" in personality_vector.lower():
        tone = "visionary and professional"
    if any(t in title.lower() for t in ("chief", "ceo", "founder")):
        tone = "concise and respectful"
    return tone

TOOLS = [
    generate_whatsapp_opener,
    suggest_message_cta,
    summarize_communications,
    adjust_message_tone,
]


class DraftMessageAgent(Runnable):
    """Creates a MessageDraft row using Gemini tool-calling and returns draft metadata."""

    def __init__(self):
        self._sf = get_session
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3
        )
        self.agent = create_tool_calling_agent(
            self.llm,
            TOOLS,
            DRAFT_MESSAGE_AGENT_PROMPT
        )

    def _next_version(self, campaign_id: int) -> int:
        with self._sf() as s:
            return s.query(MessageDraft).filter_by(campaign_id=campaign_id).count() + 1

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        strat_id: int = inputs["strategy_id"]

        with self._sf() as s:
            strat: Strategy = s.get(Strategy, strat_id)
            campaign: Campaign = s.get(Campaign, strat.campaign_id)
            client_id = campaign.client_id

            profile: Profile = s.query(Profile).filter_by(client_id=client_id).one()
            comms: List[Communication] = (
                s.query(Communication)
                .filter_by(client_id=client_id)
                .order_by(Communication.timestamp.desc())
                .limit(5)
                .all()
            )

            last_msgs = [c.content for c in comms]
            summarized_comms = summarize_communications.invoke({"messages": last_msgs})

        agent_prompt = (
            "You are writing a WhatsApp outreach message.\n"
            f"Profile Summary: {profile.summary}\n"
            f"Personality: {profile.personality_vector}\n"
            f"Preferred Contact: {profile.preferred_contact}\n"
            f"Interests: {profile.interests}\n"
            f"Strategy: Channel={strat.channel}, Schedule={strat.schedule}, Product={strat.product_type}\n"
            f"Recent Chat Summary: {summarized_comms}\n"
            "Use the tools to:\n"
            "- Create a friendly opener\n"
            "- Adjust tone\n"
            "- Suggest a WhatsApp CTA\n"
            "Return JSON: {message_text}."
        )

        
        raw = self.agent.invoke({
            "input": agent_prompt,
            "intermediate_steps": []
        })

        if isinstance(raw, AgentFinish):
            output_str = raw.return_values.get("output", "")
        elif isinstance(raw, dict):
            output_str = raw.get("output", "")
        else:
            output_str = str(raw)

        try:
            content = json.loads(output_str)
        except json.JSONDecodeError:
            content = {"message_text": output_str}

        message_text = content.get("message_text", "(empty)").strip()

        with self._sf() as s:
            version = self._next_version(strat.campaign_id)
            draft = MessageDraft(
                campaign_id=strat.campaign_id,
                version_no=version,
                message_text=message_text,
                is_approved=False,
                created_at=datetime.utcnow(),
            )
            s.add(draft)
            s.commit()
            s.refresh(draft)  
            draft_id = draft.draft_id

        return {
            "status": "message_draft_created",
            "draft_id": draft_id,
            "version": draft.version_no,
        }

    def invoke(self, input: Dict[str, Any], config=None):  
        return self._call(input)
