from typing import Dict, Any, List
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import json
import os

from db.session import SessionLocal
from db.database_schema import (
    Campaign, CampaignPlan, Client, Profile, InitialStrategy, 
    ClientListLink, User, ContextQuestion, Communication
)

class EnhancedCampaignPlannerAgent(Runnable):
    """
    Enhanced Campaign Planner that creates detailed, approvable campaign plans
    Integrates with the workflow: "Set up a campaign plan" -> "Get from frontend Approve or modify"
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.4,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.session_factory = SessionLocal
    
    def _get_campaign_context(self, campaign_id: int) -> Dict[str, Any]:
        """Gather comprehensive context for campaign planning"""
        with self.session_factory() as session:
            campaign = session.get(Campaign, campaign_id)
            user = session.get(User, campaign.user_id)
            
            # Get the single client for this campaign (direct relationship)
            client = session.get(Client, campaign.client_id)
            profile = session.query(Profile).filter_by(client_id=client.client_id).first()
            strategy = session.query(InitialStrategy).filter_by(client_id=client.client_id).first()
            qna = session.query(ContextQuestion).filter_by(client_id=client.client_id).all()
            comms = session.query(Communication).filter_by(client_id=client.client_id).all()
            
            # Single client data (no more complex client links)
            clients_data = [{
                "client_id": client.client_id,
                "name": client.full_name,
                "company": client.company,
                "category": client.category,
                "profile_summary": profile.summary if profile else "",
                "interests": profile.interests if profile else "",
                "preferred_language": profile.preferred_language if profile else "English",
                "strategy": {
                    "channel": strategy.engagement_channel if strategy else "Email",
                    "tone": strategy.tone_style if strategy else "Professional",
                    "frequency": strategy.communication_frequency if strategy else "Weekly",
                    "advice": strategy.general_advice if strategy else ""
                },
                "has_prior_communication": len(comms) > 0,
                "context_available": len(qna) > 0
            }]
        
        return {
            "campaign": {
                "id": campaign.campaign_id,
                "name": campaign.name,
                "description": campaign.description,
                "tags": campaign.tags or [],
                "created_at": campaign.created_at
            },
            "user": {
                "name": user.name if user else "Team Member",
                "email": user.email if user else "team@fabricxai.com",
                "company": user.company_name if user else "FabricX AI",
                "role": user.job_title if user else "Business Development"
            },
            "clients": clients_data,
            "campaign_type": "single_client" if len(clients_data) == 1 else "multi_client"
        }
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive campaign plan with clear day-by-day strategy
        """
        campaign_id = inputs["campaign_id"]
        context = self._get_campaign_context(campaign_id)
        
        # Create intelligent campaign planning prompt
        planning_prompt = f"""
        You are a senior campaign strategist creating a comprehensive multi-day outreach plan.
        
        CAMPAIGN CONTEXT:
        {json.dumps(context, indent=2, default=str)}
        
        CAMPAIGN PLANNING REQUIREMENTS:
        
        1. **Campaign Overview**:
           - Analyze the campaign description and client profiles
           - Define clear, measurable campaign goal
           - Determine optimal campaign length (3-7 days typically)
        
        2. **Day-by-Day Strategy**:
           For each day, create:
           - Clear objective for that day
           - Compelling subject line
           - Content theme/angle
           - Specific call-to-action
           - Success metrics
        
        3. **Personalization Strategy**:
           - If single client: Deep personalization using profile data
           - If multiple clients: Segment-based approach with variables
           - Consider prior communication history
           - Respect language and cultural preferences
        
        4. **Channel Strategy**:
           - Primary channel based on client strategies
           - Backup channels if needed
           - Cross-channel coordination
        
        CAMPAIGN STRUCTURE GUIDELINES:
        
        **For New Contacts (no prior communication):**
        - Day 1: Warm introduction + value proposition
        - Day 2: Social proof + case study/success story
        - Day 3: Specific offer/invitation to connect
        - Day 4 (optional): Follow-up with additional value
        - Day 5 (optional): Final courteous follow-up
        
        **For Existing Contacts:**
        - Day 1: Reference previous interaction + new value
        - Day 2: Deeper dive into specific benefits
        - Day 3: Strong call-to-action
        
        **Content Themes to Consider:**
        - Industry-specific pain points and solutions
        - AI/automation benefits for manufacturing
        - Cost savings and efficiency gains
        - Quality improvement stories
        - Competitive advantages
        - ROI and measurable outcomes
        
        Return JSON with this structure:
        {{
            "campaign_overview": {{
                "goal": "Clear campaign objective",
                "target_outcome": "Specific desired result",
                "duration_days": number_of_days,
                "primary_channel": "Email|WhatsApp|LinkedIn",
                "campaign_type": "introduction|follow_up|nurture|conversion",
                "personalization_level": "high|medium|low"
            }},
            "daily_plan": [
                {{
                    "day": 1,
                    "objective": "What this day aims to achieve",
                    "title": "Internal reference title",
                    "subject_line": "Email subject (or message preview)",
                    "content_theme": "Main angle/approach for content",
                    "key_message": "Core message to communicate",
                    "call_to_action": "Specific action you want them to take",
                    "success_metrics": "How to measure success",
                    "personalization_notes": "How to customize for this audience"
                }}
            ],
            "approval_notes": {{
                "key_decisions": "Important strategic choices made",
                "customization_options": "Areas where users can modify",
                "risk_factors": "Potential concerns to review",
                "success_probability": "High|Medium|Low with reasoning"
            }}
        }}
        
        Make the plan comprehensive enough that a user can approve it with confidence,
        but flexible enough to allow modifications based on their preferences.
        """
        
        response = self.llm.invoke(planning_prompt)
        content = response.content.strip()
        
        # Clean up JSON response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        try:
            plan_data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback plan if JSON parsing fails
            plan_data = {
                "campaign_overview": {
                    "goal": "Introduce FabricX AI and generate interest",
                    "target_outcome": "Schedule discovery calls",
                    "duration_days": 3,
                    "primary_channel": "Email",
                    "campaign_type": "introduction",
                    "personalization_level": "medium"
                },
                "daily_plan": [
                    {
                        "day": 1,
                        "objective": "Introduce company and establish credibility",
                        "title": "Introduction & Value Proposition",
                        "subject_line": "AI-Powered Manufacturing Solutions for [Company]",
                        "content_theme": "Introduction with industry-specific benefits",
                        "key_message": "FabricX AI helps manufacturers improve efficiency",
                        "call_to_action": "Learn more about our solutions",
                        "success_metrics": "Open rate and click engagement",
                        "personalization_notes": "Customize for industry and company size"
                    }
                ],
                "approval_notes": {
                    "key_decisions": "Email-first approach with professional tone",
                    "customization_options": "Subject lines, content themes, timing",
                    "risk_factors": "Generic messaging without sufficient personalization",
                    "success_probability": "Medium - needs more client-specific data"
                }
            }
        
        # Store campaign plan in database
        with self.session_factory() as session:
            # Clear existing campaign plans
            session.query(CampaignPlan).filter_by(campaign_id=campaign_id).delete()
            session.commit()
            
            # Create new campaign plan entries
            for day_plan in plan_data["daily_plan"]:
                campaign_plan = CampaignPlan(
                    campaign_id=campaign_id,
                    day=day_plan["day"],
                    title=day_plan["title"],
                    subject=day_plan["subject_line"],
                    goal=day_plan["objective"],
                    body_idea=f"{day_plan['content_theme']} - {day_plan['key_message']} - CTA: {day_plan['call_to_action']}"
                )
                session.add(campaign_plan)
            
            session.commit()
        
        return {
            "status": "campaign_plan_created",
            "campaign_id": campaign_id,
            "plan_overview": plan_data["campaign_overview"],
            "daily_plan": plan_data["daily_plan"],
            "approval_notes": plan_data["approval_notes"],
            "total_days": len(plan_data["daily_plan"]),
            "ready_for_review": True,
            "next_step": "frontend_approval_required"
        }
    
    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)