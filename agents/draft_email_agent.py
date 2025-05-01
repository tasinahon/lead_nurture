from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent
from langchain.tools import tool
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.agents import AgentFinish

from db.session import get_session
from db.database_schema import Communication, EmailDraft, Profile, Strategy,Campaign


load_dotenv()  


LLM_DEFAULT = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",      
    temperature=0.4,
)


DRAFT_EMAIL_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an email draft agent. Use tools to generate professional emails. Respond only with JSON."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])



@tool
def generate_cta(product_type: str, interests: str = "") -> str:
    """Return a <30‑word B2B call‑to‑action for the given product."""
    prompt = (
        "You are writing a B2B email.\n"
        f"Product Type: {product_type}\n"
        f"Client Interests: {interests}\n"
        "Suggest a strong yet professional CTA (<30 words) motivating the next step (meeting/demo/trial)."
    )
    return LLM_DEFAULT.predict(prompt).strip()


@tool
def adjust_tone(personality_vector: str = "", title: str = "") -> str:
    """Choose an email‑tone string based on persona & seniority."""
    tone = "professional and friendly"
    pv = personality_vector.lower()
    if any(tok in pv for tok in ("visionary", "innovative")):
        tone = "forward‑thinking and strategic"
    if any(k in title.lower() for k in ("chief", "ceo", "founder", "vp")):
        tone = "concise and outcome‑focused"
    return tone


@tool
def suggest_subject_line(strategy_channel: str, last_communication_summary: str) -> str:
    """Generate an email subject line (<60 chars)."""
    prompt = (
        "Suggest a crisp email subject line (<60 chars).\n"
        f"Channel: {strategy_channel}\n"
        f"Recent Topics: {last_communication_summary}\n"
        "It must be professional, engaging, and emoji‑free."
    )
    return LLM_DEFAULT.predict(prompt).strip()[:60]


@tool
def generate_email_opener(profile_summary: str) -> str:
    """Return a personalised 1‑2 sentence opener."""
    prompt = (
        "Generate a friendly, professional first line for an email.\n"
        f"Recipient summary: {profile_summary}\n"
        "It should establish rapport immediately in 1‑2 sentences."
    )
    return LLM_DEFAULT.predict(prompt).strip()


@tool
def summarize_recent_communications(messages: List[str]) -> str:
    """Summarise recent messages in 2‑3 lines."""
    if not messages:
        return "No prior communications."
    prompt = (
        "Here are the recent communications:\n" + "\n".join(messages) + "\n\nSummarise the main themes in 2‑3 lines."
    )
    return LLM_DEFAULT.predict(prompt).strip()


TOOLS = [
    generate_cta,
    adjust_tone,
    suggest_subject_line,
    generate_email_opener,
    summarize_recent_communications,
]



class DraftEmailAgent(Runnable):
    """Creates an EmailDraft row using Gemini tool‑calling and returns draft metadata."""

    def __init__(self):
        self._sf = get_session
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.35)
        self.agent = create_tool_calling_agent(
            self.llm,
            TOOLS,
            DRAFT_EMAIL_AGENT_PROMPT
        )

    
    def _next_version(self, campaign_id: int) -> int:
        with self._sf() as s:
            return (
                s.query(EmailDraft)
                .filter_by(campaign_id=campaign_id)
                .count()
                + 1
            )

    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        strat_id: int = inputs["strategy_id"]

        
        with self._sf() as s:
            strat: Strategy = s.query(Strategy).get(strat_id)
            campaign: Campaign = s.get(Campaign, strat.campaign_id)
            client_id = campaign.client_id

            profile: Profile = s.query(Profile).filter_by(client_id=client_id).one()
            comms: List[Communication] = (
                s.query(Communication)
                .filter_by(client_id=client_id)
                .order_by(Communication.timestamp.desc())
                .limit(3)
                .all()
            )

        last_msgs = [c.content for c in comms]
        comms_summary = summarize_recent_communications.invoke({"messages": last_msgs})

        
        agent_prompt = (
            "You are drafting a strategic outreach email.\n"
            f"Profile Summary: {profile.summary}\n"
            f"Personality Vector: {profile.personality_vector}\n"
            f"Preferred Language: {profile.preferred_language}\n"
            f"Preferred Contact: {profile.preferred_contact}\n"
            f"Interests: {profile.interests}\n"
            f"Strategy Details: Channel={strat.channel}, Schedule={strat.schedule}, Product={strat.product_type}\n"
            f"Recent Communication Summary: {comms_summary}\n"
            "Use the tools to create an opener, subject line, CTA, and tone.\n"
            "Return JSON with keys: subject, body_markdown."
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
            content = {"body_markdown": output_str}

        subject: str = content.get("subject", "(no subject)").strip()
        body_md: str = content.get("body_markdown") or content.get("body") or "(empty)"

        
        with self._sf() as s:
            version = self._next_version(strat.campaign_id)
            draft = EmailDraft(
                campaign_id=strat.campaign_id,
                version_no=version,
                body_markdown=body_md,
                is_approved=False,
                created_at=datetime.utcnow(),
            )
            s.add(draft)
            s.commit()
            s.refresh(draft)  
            draft_id = draft.draft_id

        return {
            "status": "draft_created",
            "draft_id": draft_id,
            "version": draft.version_no,
            "subject": subject,
        }

    
    def invoke(self, input: Dict[str, Any], config=None):  
        return self._call(input)








