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
from db.session import SessionLocal
from db.database_schema import Communication, MessageDraft, Profile, Strategy,Campaign,CampaignPlan,User,InitialStrategy


load_dotenv()


# LLM_DEFAULT = ChatGoogleGenerativeAI(
#     model="gemini-1.5-flash",
#     temperature=0.3
# )


# MESSAGE_GENERATION_PROMPT = """
# You are an AI assistant helping create **professional, personalized WhatsApp messages** for a business campaign.

# Your goal is to generate a clear, concise message for **{day}** of a multi-day campaign, based on campaign strategy and client insights.

# Plan for This Day:
# - **Title**: {title}
# - **Message Goal**: {goal}
# - **Key Idea**: {body_idea}

# Who is the recipient?
# - **Profile Summary**: {profile_summary}
# - **Interests**: {interests}
# - **Preferred Language**: {preferred_language}

# Recent Communication:
# {recent_communications}

# Sender Info:
# - **Name**: {sender_name}

# Strategy Advice:
# - **General Advice**: {general_advice}

# Writing Guidelines:
# - Keep it short, friendly, and clear.
# - Use a human tone, like a WhatsApp message from a business contact.
# - Avoid overly formal or robotic language.
# - End with a soft CTA (e.g., “Let me know”, “Would love to hear your thoughts”, etc.)
# - Never include any bracketed or placeholder text like [mention something here].
# - If specific company types or benefits are unknown, write in general terms that still sound complete and persuasive.

# Output Format:
# Return only this JSON format:
# {{
# "message_text": "Your full WhatsApp message text"
# }}

# Do not include extra text or explanations.
# """

MESSAGE_GENERATION_PROMPT = """
You are an AI assistant helping create **professional, personalized outreach messages** for a business campaign.

Your job is to generate a message for **{day}** of a multi-day campaign. The message will be sent via **{channel}** (e.g., WhatsApp, LinkedIn), so you must adapt the tone and format accordingly.

Plan for This Day:
- **Title**: {title}
- **Message Goal**: {goal}
- **Key Idea**: {body_idea}

Who is the recipient?
- **Profile Summary**: {profile_summary}
- **Interests**: {interests}
- **Preferred Language**: {preferred_language}
- **Channel**: {channel}

Recent Communication:
{recent_communications}

Sender Info:
- **Name**: {sender_name}

Strategy Advice:
- **General Advice**: {general_advice}

Writing Guidelines:
- Adjust tone and length based on the channel:
    - For **WhatsApp**: Keep it short, warm, and informal (but professional).
    - For **LinkedIn**: Keep it professional, brief, and respectful. No emojis or overly casual phrasing.
- Always sound human — not robotic or overly scripted.
- Avoid any bracketed or placeholder text like [mention something here].
- If you lack specifics (like company names, percentages, etc.), write in general terms that still sound persuasive and complete.
- End with a soft call-to-action (e.g., “Let me know”, “Would love your thoughts”, “Open to a quick chat?”).

Output Format:
Return only this JSON:
{{
"message_text": "Your full outreach message"
}}
Do not include extra text or explanations.
Only return the JSON. Do not include any extra text or explanations.
"""


class DraftMessageAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.35)
        self._sf = SessionLocal

    def _get_comms_summary(self, client_id: int) -> str:
        with self._sf() as s:
            comms = (
                s.query(Communication)
                .filter_by(client_id=client_id)
                .order_by(Communication.timestamp.desc())
                .limit(3)
                .all()
            )
        messages = [c.content for c in comms]
        if not messages:
            return "No recent communication."
        prompt = "Summarize:\n" + "\n".join(messages)
        return self.llm.predict(prompt).strip()

    def _next_version(self, campaign_id: int,contact_id: int, day: int) -> int:
        with self._sf() as s:
            return s.query(MessageDraft).filter_by(campaign_id=campaign_id, contact_id=contact_id, day=day).count() + 1

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = inputs["campaign_id"]
        contact_id = inputs["contact_id"]
        day = inputs["day"]

        with self._sf() as s:
            campaign = s.query(Campaign).get(campaign_id)
            user = s.query(User).get(campaign.user_id)
            plan = (
                s.query(CampaignPlan)
                .filter_by(campaign_id=campaign_id, day=day)
                .first()
            )
            profile = s.query(Profile).filter_by(client_id=contact_id).first()
            channel = profile.preferred_contact  

            strategy = s.query(InitialStrategy).filter_by(client_id=contact_id).first()
            general_advice = strategy.general_advice if strategy else "No strategy advice available."

        comms_summary = self._get_comms_summary(contact_id)

        formatted_prompt = MESSAGE_GENERATION_PROMPT.format(
            day=day,
            title=plan.title,
            goal=plan.goal,
            body_idea=plan.body_idea,
            profile_summary=profile.summary,
            interests=profile.interests,
            preferred_language=profile.preferred_language,
            sender_name=user.name,
            general_advice=general_advice,
            channel=channel,
            recent_communications=comms_summary
        )

        raw_output = self.llm.invoke(formatted_prompt)
        raw_content = raw_output.content.strip()

        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content

        try:
            parsed_message = json.loads(cleaned)
            message_text = parsed_message["message_text"]
        except (json.JSONDecodeError, KeyError):
            message_text = cleaned

        with self._sf() as s:
            version = self._next_version(campaign_id,contact_id,day)
            draft = MessageDraft(
                campaign_id=campaign_id,
                contact_id=contact_id,
                day=day,
                version_no=version,
                message_text=message_text,
                is_approved=False,
                created_at=datetime.utcnow()
            )

            s.add(draft)
            s.commit()
            s.refresh(draft)

        return {
            "status": "draft_created",
            "contact_id": contact_id,
            "message_text": message_text,
            "draft_id": draft.draft_id
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)

