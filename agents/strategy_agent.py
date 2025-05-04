
import os
import json
import numpy as np
from datetime import datetime
from collections import Counter
from typing import Dict, Any, List

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from db.session import get_session
from db.database_schema import Strategy, Profile, Communication
# from graph.draft_graph import draft_phase

load_dotenv()

class StratSchema(BaseModel):
    channel: str = None
    content_theme: str = None
    schedule: str = None
    product_type: str = None

parser = JsonOutputParser(pydantic_schema=StratSchema)


strategy_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a campaign strategy assistant analyzing profile and communication behavior."),
    ("user",
     """
     You are given a client profile and communication history.

     Suggest the best outreach strategy based on their behavior and tone.

     Return a JSON with:
     1. **channel**: Best outreach channel ('Email', 'LinkedIn', 'WhatsApp')
     2. **content_theme**: What message tone or topics fit well?
     3. **schedule**: Use this cadence recommendation as a guide: {suggested_cadence}
     4. **product_type**: What kind of offer or campaign fits best?

     Profile Summary:
     {profile}

     Communication Stats:
     - Most used channel: {most_used_channel}
     - Avg gap between communications (in hours): {average_gap_hours}
     - Messages:
     {message_summaries}

     {format_instructions}
     """)
])


class StrategyAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self._sf = get_session

    def recommend_cadence(self, avg_gap_hours: float) -> str:
        if avg_gap_hours <= 72:
            return "every 2-3 days"
        elif avg_gap_hours <= 168:
            return "once a week"
        elif avg_gap_hours <= 360:
            return "every 2 weeks"
        else:
            return "once a month"

    def summarize_communication(self, comms: List[Communication]) -> Dict[str, Any]:
        channels = [c.channel for c in comms]
        timestamps = sorted([c.timestamp for c in comms], reverse=True)

        channel_counter = Counter(channels)

        gaps = [
            (timestamps[i] - timestamps[i + 1]).total_seconds() / 3600
            for i in range(len(timestamps) - 1)
        ]
        avg_gap = round(np.mean(gaps), 1) if gaps else 72

        return {
            "most_used_channel": channel_counter.most_common(1)[0][0] if channels else "Email",
            "average_gap_hours": avg_gap,
            "suggested_cadence": self.recommend_cadence(avg_gap),
            "message_summaries": [c.content[:150] for c in comms]
        }

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cid = inputs["client_id"]
        campaign_id = inputs.get("campaign_id")

        with self._sf() as s:
            prof = s.query(Profile).filter_by(client_id=cid).one_or_none()
            comms = (
                s.query(Communication)
                .filter_by(client_id=cid)
                .order_by(Communication.timestamp.desc())
                .limit(5)
                .all()
            )

        if not prof or not comms:
            return {"status": "error", "detail": "Missing profile or communications"}

        comm_summary = self.summarize_communication(comms)

        formatted_prompt = strategy_prompt.format_prompt(
            profile=prof.summary,
            most_used_channel=comm_summary["most_used_channel"],
            average_gap_hours=comm_summary["average_gap_hours"],
            suggested_cadence=comm_summary["suggested_cadence"],
            message_summaries="\n".join(comm_summary["message_summaries"]),
            format_instructions=parser.get_format_instructions()
        ).to_string()

        raw_output = self.llm.invoke(formatted_prompt)
        raw_content = raw_output.content.strip()

        if raw_content.startswith("```") and raw_content.endswith("```"):
            cleaned_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned_content = raw_content

        parsed_dict = json.loads(cleaned_content)
        strategy = StratSchema(**parsed_dict)

        with self._sf() as s:
            strat = Strategy(
                campaign_id=campaign_id,
                client_id=cid,
                channel=strategy.channel,
                content_theme=strategy.content_theme,
                schedule=strategy.schedule,
                product_type=strategy.product_type,
                generated_at=datetime.utcnow()
            )
            s.add(strat)
            s.commit()
            s.refresh(strat)
            strategy_id = strat.strategy_id

            # draft_phase.invoke({
            #     "strategy_id": strategy_id,
            #     "channel": strategy.channel
            # })

        log_content = f"""
======== Strategy Generation ========
Client ID: {cid}
Channel: {strategy.channel}
Content Theme: {strategy.content_theme}
Schedule: {strategy.schedule}
Product Type: {strategy.product_type}
Generated At: {datetime.utcnow().isoformat()}
=====================================
"""
        with open("agent.txt", "a", encoding="utf-8") as f:
            f.write(log_content)

        return {
            "status": "strategy_ready",
            "client_id": cid,
            "strategy_id": strategy_id
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)





from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from db.session import get_session
from db.database_schema import (
    Campaign, CampaignPlan, Profile, Strategy, Communication, Engagement, ContextQuestion
)

from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import os, json

class StrategySchema(BaseModel):
    channel: str
    schedule: str
    product_type: str
    tone: Optional[str] = None
    engagement_method: Optional[str] = None


# class StrategyAgent(Runnable):
#     def __init__(self):
#         self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.35)
#         self.parser = JsonOutputParser(pydantic_schema=StrategySchema)
#         self.prompt = self._build_prompt()
#         self.session_factory = get_session

#     def _build_prompt(self):
#         return ChatPromptTemplate.from_messages([
#             ("system", """
# You are an advanced AI campaign strategist. Your task is to create a communication strategy for an outreach campaign.

# You will be given:
# - Campaign goal and tags
# - Client profile and preferences (or sample profile group)
# - Engagement summary (if available)
# - Multi-day campaign plan structure

# 📌 Your job:
# 1. Choose the best **communication channel** based on client preferences and goal.
# 2. Suggest the **schedule** — best days/times for reaching out.
# 3. Specify **product type** if it can be inferred.
# 4. Define an appropriate **tone** — friendly, urgent, consultative, etc.
# 5. Recommend an **engagement method** — reply CTA, link, follow-up, etc.

# ⚠️ If no engagement history or Q&A is available, assume it's a first-time contact. Adjust tone and timing accordingly.

# Return only this JSON:
# {
#   "channel": "email or whatsapp",
#   "schedule": "Monday mornings and Thursday follow-up",
#   "product_type": "software or consulting",
#   "tone": "Warm and consultative",
#   "engagement_method": "Include Calendly link in CTA"
# }

# No commentary. Output must be valid JSON.
# {format_instructions}
# """),
#             ("user", "{input_context}")
#         ])

#     def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
#         campaign_id = inputs["campaign_id"]
#         with self.session_factory() as s:
#             campaign = s.get(Campaign, campaign_id)
#             plans = s.query(CampaignPlan).filter_by(campaign_id=campaign_id).all()
#             profile = s.query(Profile).filter_by(client_id=campaign.client_id).first()
#             qna = s.query(ContextQuestion).filter_by(client_id=campaign.client_id).all()
#             comms = s.query(Communication).filter_by(client_id=campaign.client_id).all()
#             engagement = s.query(Engagement).filter_by(campaign_id=campaign_id).all()

#         input_context = json.dumps({
#             "goal": campaign.goal,
#             "tags": campaign.tags,
#             "profile_summary": profile.summary if profile else "",
#             "preferred_contact": profile.preferred_contact if profile else "",
#             "engagement_summary": [e.event_type for e in engagement],
#             "context_qna": [{"q": q.question, "a": q.answer} for q in qna],
#             "communications": [c.content for c in comms[:3]],
#             "campaign_plan_summary": [
#                 {
#                     "day": p.day,
#                     "title": p.title,
#                     "subject": p.subject,
#                     "goal": p.goal
#                 } for p in plans
#             ]
#         }, ensure_ascii=False)

#         formatted = self.prompt.format_prompt(
#             input_context=input_context,
#             format_instructions=self.parser.get_format_instructions()
#         ).to_string()

#         raw = self.llm.invoke(formatted)
#         parsed = self.parser.parse(raw.content)

#         with self.session_factory() as s:
#             strat = Strategy(
#                 campaign_id=campaign_id,
#                 channel=parsed.channel,
#                 schedule=parsed.schedule,
#                 product_type=parsed.product_type,
#                 generated_at=datetime.utcnow()
#             )
#             s.add(strat)
#             s.commit()
#             s.refresh(strat)

#         return {
#             "status": "strategy_created",
#             "campaign_id": campaign_id,
#             "channel": parsed.channel,
#             "schedule": parsed.schedule,
#             "product_type": parsed.product_type
#         }

#     def invoke(self, input: Dict[str, Any], config=None):
#         return self._call(input)
