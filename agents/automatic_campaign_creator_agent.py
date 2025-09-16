from typing import Dict, Any
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import json
import os

from db.session import SessionLocal
from db.database_schema import (
    Client, Profile, InitialStrategy, Campaign, User
)

class AutomaticCampaignCreatorAgent(Runnable):
    """
    Automatically creates campaigns after immediate reply sent
    Following BRM workflow: Immediate Reply → Auto Campaign Creation → Planning → Frontend Approval
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.session_factory = SessionLocal
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-create campaign after immediate reply based on:
        1. Client profile and interaction
        2. Immediate reply sentiment and response
        3. Strategic next steps
        """
        client_id = inputs["client_id"]
        user_id = inputs.get("user_id", 1)
        immediate_reply_context = inputs.get("immediate_reply_context", {})
        
        # 🔍 DEBUG: Print the inputs to see what we're getting
        print(f"🔍 [DEBUG] AutomaticCampaignCreatorAgent inputs:")
        print(f"   client_id: {client_id} (type: {type(client_id)})")
        print(f"   user_id: {user_id} (type: {type(user_id)})")
        print(f"   immediate_reply_context: {immediate_reply_context}")
        
        with self.session_factory() as session:
            client = session.get(Client, client_id)
            profile = session.query(Profile).filter_by(client_id=client_id).first()
            strategy = session.query(InitialStrategy).filter_by(client_id=client_id).first()
            user = session.get(User, user_id)
        
        # Analyze context for campaign creation
        context = {
            "client": {
                "name": client.full_name,
                "company": client.company,
                "category": client.category,
                "email": client.email
            },
            "profile": {
                "summary": profile.summary if profile else "",
                "interests": profile.interests if profile else "",
                "industry_focus": client.category or "Manufacturing"
            },
            "strategy": {
                "channel": strategy.engagement_channel if strategy else "Email",
                "tone": strategy.tone_style if strategy else "Professional",
                "advice": strategy.general_advice if strategy else ""
            },
            "immediate_reply": immediate_reply_context,
            "company_info": {
                "name": user.company_name if user else "FabricX AI",
                "focus": "AI-Powered Garment Manufacturing Solutions"
            }
        }
        
        # Generate intelligent campaign parameters
        campaign_prompt = f"""
        You are an expert marketing strategist creating an automatic follow-up campaign after an immediate reply has been sent.
        
        CONTEXT:
        {json.dumps(context, indent=2, default=str)}
        
        SITUATION:
        An immediate reply has been sent to this client, and now we need to create a strategic follow-up campaign to nurture this lead and move them toward conversion.
        
        CAMPAIGN CREATION REQUIREMENTS:
        
        1. **Campaign Name**: Create a professional, descriptive name that reflects:
           - The client's industry/company
           - Our solution focus (AI manufacturing)
           - The campaign objective
        
        2. **Campaign Description**: Write a strategic description explaining:
           - Why this campaign is being created
           - What we aim to achieve
           - How it builds on the immediate reply
        
        3. **Campaign Tags**: Generate 3-5 relevant tags like:
           - Industry tags (e.g., "Manufacturing", "Textiles")
           - Solution tags (e.g., "AI-Automation", "Efficiency")
           - Stage tags (e.g., "Nurture", "Follow-up", "Conversion")
           - Priority tags (e.g., "High-Interest", "Warm-Lead")
        
        4. **Campaign Objective**: Define the primary goal:
           - Schedule demo/meeting
           - Provide detailed solution information  
           - Build relationship and trust
           - Move to sales qualified lead
        
        5. **Urgency Level**: Assess based on immediate reply context:
           - High: Client showed strong interest
           - Medium: Client engaged but needs nurturing
           - Low: Polite response, long-term nurturing
        
        Return JSON:
        {{
            "campaign_name": "Professional campaign name",
            "campaign_description": "Detailed strategic description",
            "campaign_tags": ["tag1", "tag2", "tag3", "tag4"],
            "primary_objective": "Main campaign goal",
            "urgency_level": "High|Medium|Low",
            "expected_duration": "3-5 days recommended duration",
            "success_metrics": ["metric1", "metric2"],
            "reasoning": "Why this campaign approach was chosen"
        }}
        
        Make the campaign strategic and tailored to this specific client context.
        """
        
        response = self.llm.invoke(campaign_prompt)
        content = response.content.strip()
        
        # Clean up JSON response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        try:
            campaign_params = json.loads(content)
        except json.JSONDecodeError:
            # Fallback campaign parameters
            campaign_params = {
                "campaign_name": f"AI Manufacturing Solutions for {client.company}",
                "campaign_description": f"Strategic follow-up campaign for {client.full_name} focusing on AI-powered manufacturing automation solutions.",
                "campaign_tags": ["Manufacturing", "AI-Automation", "Follow-up", "Warm-Lead"],
                "primary_objective": "Schedule discovery meeting and demonstrate solution value",
                "urgency_level": "Medium",
                "expected_duration": "3-4 days",
                "success_metrics": ["Meeting scheduled", "Solution demo completed"],
                "reasoning": "Standard follow-up approach for manufacturing sector client"
            }
        
        # Create campaign with DIRECT client relationship - MUCH SIMPLER!
        with self.session_factory() as session:
            # Create the campaign directly with client_id (no complex linking needed!)
            campaign = Campaign(
                user_id=user_id,
                client_id=client_id,  # ✅ Direct client relationship!
                name=campaign_params["campaign_name"],
                description=campaign_params["campaign_description"],
                tags=json.dumps(campaign_params["campaign_tags"]) if isinstance(campaign_params["campaign_tags"], list) else campaign_params["campaign_tags"],
                created_at=datetime.utcnow(),
                status="draft",
                approval_status="pending_approval"
            )
            session.add(campaign)
            session.commit()
            session.refresh(campaign)
        
        return {
            "status": "campaign_auto_created",
            "campaign_id": campaign.campaign_id,
            "client_id": client_id,
            "direct_client_relationship": True,  # ✅ No complex clientlist needed!
            "campaign_details": campaign_params,
            "next_step": "auto_generate_plan",
            "workflow_stage": "ready_for_planning"
        }
    
    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)