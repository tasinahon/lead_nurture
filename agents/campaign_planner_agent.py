from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from db.session import get_session
from db.database_schema import (
    Profile, Communication, ContextQuestion,
    Campaign, CampaignPlan, ClientList, Client, ClientListLink
)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os, json

class CampaignPlanSchema(BaseModel):
    campaign_goal: str
    campaign_tags: List[str]
    days: List[Dict[str, str]]


class CampaignPlannerAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", temperature=0.4,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.parser = JsonOutputParser(pydantic_schema=CampaignPlanSchema)
        self.prompt = self._build_prompt()
        self.session_factory = get_session

    def _build_prompt(self):
        return ChatPromptTemplate.from_messages([
        ("system", """
        You are a senior AI campaign strategist responsible for building 3-day communication plans for email or message campaigns.
        
        Your job is to generate a **multi-day campaign plan** (minimum 2 days, typically 3–5) for email/message outreach based on:

        The user has provided:
        - A campaign description (goal, context, brand intent)
        - A list of campaign tags (e.g., 'Marketing', 'Exclusive', 'Follow-up')

        You must:
        1. Carefully analyze the user’s **campaign description and tags** to define a single **campaign_goal**.
        2. Based on the mode:
        • If it's a single client → personalize deeply using profile, Q&A, and communications
        • If it's a client list → use representative sample profiles and keep tone generalized

        Then:
        You must:
        - Analyze the **description and tags** to define a high-level `campaign_goal` in 1 sentence
        - Decide the appropriate number of campaign days
        - Make each day distinct and strategically meaningful (intro, story, offer, CTA, etc.)
        - Keep tone aligned with the target audience

        Only return valid JSON matching this format:
        {
        "campaign_goal": "Summarize the user's intent in 1 sentence",
        "campaign_tags": ["..."],  // echo the tags passed in context
        "days": [
            {
            "day": "Day 1",
            "title": "...",
            "subject": "...",
            "goal": "...",
            "body_idea": "..."
            },
            ...
        ]
        }

        Output only valid JSON.
        {format_instructions}
        """),
                ("user", "{context}")
            ])

    def _get_context_single(self, campaign: Campaign) -> str:
        with self.session_factory() as s:
            profile = s.query(Profile).filter_by(client_id=campaign.client_id).first()
            qna = s.query(ContextQuestion).filter_by(client_id=campaign.client_id).all()
            comms = s.query(Communication).filter_by(client_id=campaign.client_id).all()

        context = {
            "type": "single",
            "campaign_description": campaign.description,
            "tags": campaign.tags or [],
            "profile": profile.summary + "\n" + profile.full_text,
            "qna": [{"q": q.question, "a": q.answer} for q in qna if q.answer],
            "communications": [{"title": c.title, "body": c.body} for c in comms]
        }
        return json.dumps(context, ensure_ascii=False)

    def _get_context_list(self, campaign: Campaign) -> str:
        with self.session_factory() as s:
            clist = s.query(ClientList).filter_by(clientlist_id=campaign.clientlist_id).first()
            links = s.query(ClientListLink).filter_by(list_id=clist.clientlist_id).limit(3).all()
            sample_profiles = []

            for link in links:
                profile = s.query(Profile).filter_by(client_id=link.client_id).first()
                if profile:
                    sample_profiles.append({
                        "summary": profile.summary,
                        "interests": profile.interests,
                        "tone_hint": profile.preferred_contact
                    })

        context = {
            "type": "list",
            "list_name": clist.name,
            "campaign_description": campaign.description,
            "tags": campaign.tags or [],
            "sample_profiles": sample_profiles
        }
        return json.dumps(context, ensure_ascii=False)

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = inputs["campaign_id"]

        with self.session_factory() as s:
            campaign = s.query(Campaign).get(campaign_id)

        mode = "list" if campaign.clientlist_id else "single"

        if mode == "single":
            context = self._get_context_single(campaign)
        else:
            context = self._get_context_list(campaign)

        formatted = self.prompt.format_prompt(
            context=context,
            format_instructions=self.parser.get_format_instructions()
        ).to_string()

        raw = self.llm.invoke(formatted)
        parsed = self.parser.parse(raw.content)

        with self.session_factory() as s:
            for day in parsed.days:
                cp = CampaignPlan(
                    campaign_id=campaign_id,
                    day=day["day"],
                    title=day["title"],
                    subject=day["subject"],
                    goal=day["goal"],
                    body_idea=day["body_idea"]
                )
                s.add(cp)
            s.commit()

        return {
            "status": "plan_created",
            "campaign_id": campaign_id,
            "days": parsed.days
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)
