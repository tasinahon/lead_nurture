import os, json
from typing import List, Dict, Any
from pydantic import BaseModel
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from db.session import get_session
from db.database_schema import (
    Profile, Communication, ContextQuestion,
    Campaign, CampaignPlan, ClientList, Client, ClientListLink
)

FABRICXAI_FEATURES = """
Fabricxai Platform Overview:
Fabricxai is an AI-powered garment automation platform designed to enhance production, communication, and buyer engagement.

Core Features:
- AI-Powered BRM: Real-time LinkedIn monitoring for intelligent buyer engagement (+30% Lead Conversion)
- Production Management: AI-based tracking for deadline management (98% On-time Delivery)
- Inventory Management: AI-forecasted stock optimization (45% Stock Efficiency)
- Predictive Maintenance: Maintenance scheduling to reduce downtime (-45%)
- Instant Website: AI-powered product catalog & chatbot (24/7 Availability)
- Advanced Analytics: End-to-end performance monitoring (360° Visibility)
- AI-Powered Lead Generation: Auto-discovery of potential buyers (30% New Leads/Month)
- Smart Buyer Engagement: Sentiment-based communication (40% Higher Conversion)
- Global Communication: Translations across 40+ languages (24/7 Availability)
- Complete Visibility: Unified order tracking dashboard (100% Transparency)
"""


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

    # def _build_prompt(self):
    #     return ChatPromptTemplate.from_messages([
    #         ("system", (
    #             "You are a senior AI campaign strategist responsible for building multi-day communication plans for email or message campaigns.\n"
    #             "\n"
    #             "Your job is to generate a campaign plan (minimum 2 days, typically 3–5) for outreach based on:\n"
    #             "- A campaign description (goal, context, brand intent)\n"
    #             "- A list of campaign tags (e.g., 'Marketing', 'Exclusive', 'Follow-up')\n"
    #             "\n"
    #             "You must:\n"
    #             "1. Analyze the campaign description and tags to define a single campaign_goal\n"
    #             "2. Depending on the campaign type:\n"
    #             "\n"
    #             "• If it's a single client:\n"
    #             "- Personalize deeply using the full profile, context Q&A, and recent communication logs\n"
    #             "- Adjust tone, subject, and daily goals for maximum relevance\n"
    #             "\n"
    #             "• If it's a client list:\n"
    #             "- You will receive 2–3 sample profiles representing typical members of the list\n"
    #             "- Analyze their shared traits, interests, and categories (e.g., Buyer, Investor)\n"
    #             "- Generalize tone and structure across the group\n"
    #             "- Avoid direct personalization (no names or specific references)\n"
    #             "- Keep the message flexible and broadly relevant to the audience\n"
    #             "\n"
    #             "You must:\n"
    #             "- Echo back the original campaign_tags\n"
    #             "- Decide the number of days based on complexity (2 to 5)\n"
    #             "- Make each day distinct with a title, subject line, goal, and creative idea\n"
    #             "\n"
    #             "Return JSON like:\n"
    #             "{{\n"
    #             "  \"campaign_goal\": \"...\",\n"
    #             "  \"campaign_tags\": [\"...\"],\n"
    #             "  \"days\": [\n"
    #             "    {{\"day\": \"Day 1\", \"title\": \"...\", \"subject\": \"...\", \"goal\": \"...\", \"body_idea\": \"...\" }},\n"
    #             "    ...\n"
    #             "  ]\n"
    #             "}}\n"
    #             "\n"
    #             "Strictly return only valid JSON.\n"
    #             "{format_instructions}"
    #         )),
    #         ("user", "{context}")
    #     ])
    

    def _build_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", (
                "You are a senior AI campaign strategist responsible for building multi-day communication plans for email or message campaigns.\n"
                "\n"
                "Your job is to generate a campaign plan (minimum 2 days, typically 3–5) for outreach based on:\n"
                "- A campaign description (goal, context, brand intent)\n"
                "- A list of campaign tags (e.g., 'Marketing', 'Exclusive', 'Follow-up')\n"
                "\n"
                "You must:\n"
                "1. Analyze the campaign description and tags to define a single campaign_goal\n"
                "2. Depending on the campaign type:\n"
                "• If it's a single client:\n"
                "- Personalize deeply using the full profile, context Q&A, and recent communication logs\n"
                "- Adjust tone, subject, and daily goals for maximum relevance\n"
                "- If there is **no Q&A and no prior communication**, assume this is the client’s **first-ever touchpoint**\n"
                "  - Begin the campaign with a warm, welcoming Day 1\n"
                "  - Introduce the brand or product clearly and gently\n"
                "  - Avoid phrases like 'as we discussed' or anything assuming familiarity\n"
                "  - Focus Day 1 on building trust, rapport, and setting context for future messages\n"
                "\n"
                "• If it's a client list:\n"
                "- You will receive 2–3 sample profiles representing typical members of the list\n"
                "- Analyze their shared traits, interests, and categories (e.g., Buyer, Investor)\n"
                "- Generalize tone and structure across the group\n"
                "- Avoid direct personalization (no names or specific references)\n"
                "- Keep the message flexible and broadly relevant to the audience\n"
                "\n"
                "Important: You are planning this campaign for the company **Fabricxai**. Their offerings should guide tone and content strategy.\n"
                f"{FABRICXAI_FEATURES}\n"
                "\n"
                "Return JSON like:\n"
                "{{\n"
                "  \"campaign_goal\": \"...\",\n"
                "  \"campaign_tags\": [\"...\"],\n"
                "  \"days\": [\n"
                "    {{\"day\": \"Day 1\", \"title\": \"...\", \"subject\": \"...\", \"goal\": \"...\", \"body_idea\": \"...\" }},\n"
                "    ...\n"
                "  ]\n"
                "}}\n"
                "\n"
                "Strictly return only valid JSON.\n"
                "{format_instructions}"
            )),
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
            "profile_summary": profile.summary,
            "persona_text": profile.full_text,
            "qna": [{"q": q.question, "a": q.answer} for q in qna if q.answer],
            "communications": [{"title": c.title, "body": c.body} for c in comms]
        }
        return json.dumps(context, ensure_ascii=False)

    def _get_context_list(self, campaign: Campaign) -> str:
        import random
        with self.session_factory() as s:
            clist = s.query(ClientList).filter_by(clientlist_id=campaign.clientlist_id).first()
            all_links = s.query(ClientListLink).filter_by(list_id=clist.clientlist_id).all()
            links = random.sample(all_links, min(2, len(all_links)))
            sample_profiles = []

            for link in links:
                profile = s.query(Profile).filter_by(client_id=link.client_id).first()
                client = s.query(Client).filter_by(client_id=link.client_id).first()
                if profile:
                    sample_profiles.append({
                        "summary": profile.summary,
                        "interests": profile.interests,
                        "tone_hint": profile.preferred_contact,
                        "category": client.category
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

        raw_output = self.llm.invoke(formatted)
        raw_content = raw_output.content.strip()

        # Remove markdown code block if present
        if raw_content.startswith("```"):
            cleaned_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned_content = raw_content

        # Parse JSON into dict
        parsed_dict = self.parser.parse(cleaned_content)

        # Convert dict to Pydantic object
        parsed = CampaignPlanSchema(**parsed_dict)


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
            "day_count": len(parsed.days),
            "days": parsed.days
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)










#  def _build_prompt(self):
#         return ChatPromptTemplate.from_messages([
#             ("system", """
# You are a senior AI campaign strategist responsible for building multi-day communication plans for email or message campaigns.

# Your job is to generate a campaign plan (minimum 2 days, typically 3–5) for outreach based on:
# - A campaign description (goal, context, brand intent)
# - A list of campaign tags (e.g., 'Marketing', 'Exclusive', 'Follow-up')
# - Profile context (from scraped data or user input)
# - Recent Q&A and communication logs (if available)

# You must:
# 1. Analyze the campaign description and tags to define a single campaign_goal
# 2. Depending on the campaign type:

# • If it's a single client:
#   - Personalize deeply using the full profile, context Q&A, and recent communication logs
#   - If there is **no Q&A and no prior communication**, assume this is the client’s **first-ever touchpoint**
#     - Begin the campaign with a warm, welcoming Day 1
#     - Introduce the brand or product clearly and gently
#     - Avoid phrases like "as we discussed" or anything assuming familiarity
#     - Focus Day 1 on building trust, rapport, and setting context for future messages

# • If it's a client list:
#   - You will receive 2–3 sample profiles representing typical members of the list
#   - Analyze their shared traits, interests, and categories (e.g., Buyer, Investor)
#   - Generalize tone and structure across the group
#   - Avoid direct personalization (no names or specific references)
#   - Keep the message flexible and broadly relevant to the audience

# Example:
# If all profiles show interest in sustainability and the category is "Buyer", structure like:
# - Day 1: The sustainable story
# - Day 2: Case study or offer
# - Day 3: Invitation to connect

# You must:
# - Echo back the original campaign_tags
# - Decide the number of days based on complexity (2 to 5)
# - Make each day distinct with a title, subject line, goal, and creative idea

# Return JSON like:
# {
#   "campaign_goal": "...",
#   "campaign_tags": ["..."],
#   "days": [
#     {"day": "Day 1", "title": "...", "subject": "...", "goal": "...", "body_idea": "..." },
#     ...
#   ]
# }

# Strictly return only valid JSON.
# {format_instructions}
# """),
#             ("user", "{context}")
#         ])

