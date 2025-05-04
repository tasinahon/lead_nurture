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
from db.database_schema import Communication, EmailDraft, Profile, Strategy,Campaign,CampaignPlan,User,InitialStrategy


load_dotenv()  


LLM_DEFAULT = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",      
    temperature=0.4,
)


EMAIL_GENERATION_PROMPT = """
    You are a professional AI email copywriter working on a B2B or B2C campaign. 

    Your job is to write a **personalized, strategic email** for **{day}** of a multi-day campaign based on a predefined plan and client insights.

    Plan for This Day:
    - **Title**: {title}
    - **Subject Line**: {subject}
    - **Goal**: {goal}
    - **Content Focus**: {body_idea}

    Who is the recipient?
    - **Profile Summary**: {profile_summary}
    - **Interests**: {interests}
    - **Preferred Channel**: {preferred_contact}
    - **Language**: {preferred_language}

    Recent Communication (if any):
    {recent_communications}

    Sender Info:
    - **Name**: {sender_name}
    - **Email**: {sender_email}

    Strategy Advice:
    - **General Advice**: {general_advice}

    

    How to write:
    - Use the **subject** and **body_idea** as your creative anchor.
    - Tailor the tone to suit the profile and campaign goal.
    - If the recipient is a business buyer, keep it professional but not robotic.
    - If the goal is personal connection, use storytelling or empathy.
    - Include a clear, relevant call-to-action in the closing (meeting, reply, etc.).
    - Make sure it follows natural human email tone.

    Output Format:
    Return only this JSON format:
    {{
    "subject": "Your final email subject line",
    "body_markdown": "Markdown-formatted body of the email"
    }}

    Do not include extra text, commentary, or formatting outside the JSON.
    """




class EmailDraftAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.35)
        self._sf = get_session

    def _get_comms_summary(self, client_id: int) -> str:
        with self._sf() as s:
            comms: List[Communication] = (
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
    
    def _next_version(self, campaign_id: int) -> int:
        with self._sf() as s:
            return s.query(EmailDraft).filter_by(campaign_id=campaign_id).count() + 1

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
            strategy = s.query(InitialStrategy).filter_by(client_id=contact_id).first()
            general_advice = strategy.general_advice if strategy else "No strategy advice available."


        comms_summary = self._get_comms_summary(contact_id)

        
        formatted_prompt = EMAIL_GENERATION_PROMPT.format(
            day=day,
            title=plan.title,
            subject=plan.subject,
            goal=plan.goal,
            body_idea=plan.body_idea,
            profile_summary=profile.summary,
            interests=profile.interests,
            preferred_contact=profile.preferred_contact,
            preferred_language=profile.preferred_language,
            sender_name=user.name,
            sender_email=user.email,
            general_advice=general_advice,
            recent_communications=comms_summary
        )

        # Send to LLM
        raw_output = self.llm.invoke(formatted_prompt)
        raw_content = raw_output.content.strip()

        # Remove code block markers if present
        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content

        try:
            parsed_email = json.loads(cleaned)
            subject = parsed_email["subject"]
            body = parsed_email["body_markdown"]
        except (json.JSONDecodeError, KeyError):
            subject = plan.subject
            body = cleaned  



        with self._sf() as s:
            version = self._next_version(campaign_id)
            draft = EmailDraft(
                campaign_id=campaign_id,
                contact_id=contact_id,
                version_no=version,
                subject=subject,
                body_markdown=body,
                is_approved=False,
                created_at=datetime.utcnow()
            )

            s.add(draft)
            s.commit()
            s.refresh(draft)

        return {
            "status": "draft_created",
            "contact_id": contact_id,
            "subject": subject,
            "draft_id": draft.draft_id
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)











