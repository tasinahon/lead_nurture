from typing import Dict, Any
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import json
import os

from db.session import SessionLocal
from db.database_schema import (
    Client, Profile, InitialStrategy, ContextQuestion, 
    Communication, User
)

class EnhancedStrategyAgent(Runnable):
    """
    Enhanced Strategy Agent that works for both initial contacts and existing clients
    Based on BRM workflow - Agent 5: Setup Initial Approach Strategy
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
        Generate strategy based on:
        1. Client profile (from scraping/manual input)
        2. Any existing communication history
        3. Context Q&A if available
        4. User/company information
        """
        client_id = inputs["client_id"]
        user_id = inputs.get("user_id", 1)  # Default to user 1 if not provided
        
        with self.session_factory() as session:
            client = session.get(Client, client_id)
            profile = session.query(Profile).filter_by(client_id=client_id).first()
            qna = session.query(ContextQuestion).filter_by(client_id=client_id).all()
            communications = session.query(Communication).filter_by(client_id=client_id).all()
            user = session.get(User, user_id)
        
        # Determine if this is first contact or existing relationship
        is_first_contact = len(communications) == 0
        
        # Prepare context for AI
        context = {
            "client_profile": {
                "name": client.full_name,
                "company": client.company,
                "category": client.category,
                "email": client.email,
                "phone": client.phone
            },
            "scraped_profile": {
                "summary": profile.summary if profile else "",
                "interests": profile.interests if profile else "",
                "preferred_contact": profile.preferred_contact if profile else "",
                "preferred_language": profile.preferred_language if profile else "English",
                "engagement_times": profile.engagement_times if profile else "",
                "full_text": profile.full_text if profile else ""
            },
            "context_qna": [{"question": q.question, "answer": q.answer} for q in qna],
            "communication_history": [
                {"timestamp": c.timestamp, "channel": c.channel, "content": c.content[:200]}
                for c in communications[-5:]  # Last 5 communications
            ],
            "is_first_contact": is_first_contact,
            "sender_info": {
                "company": user.company_name if user else "FabricX AI",
                "industry": "AI-Powered Garment Manufacturing",
                "sender_role": user.job_title if user else "Business Development"
            }
        }
        
        strategy_prompt = f"""
        You are an expert communication strategist creating an outreach approach strategy.
        
        CONTEXT:
        {json.dumps(context, indent=2, default=str)}
        
        Based on this information, create a strategic approach for communication with this client.
        
        STRATEGY REQUIREMENTS:
        
        1. **Engagement Channel**: Choose the most appropriate channel
           - Email (default for business contacts)
           - WhatsApp (if phone provided and appropriate for region/industry)
           - LinkedIn (for professional networking approach)
        
        2. **Tone & Style**: Define communication approach
           - Formal (corporate, traditional industries)
           - Professional-Friendly (tech, modern businesses)
           - Consultative (solution-focused approach)
           - Warm (relationship-building focus)
        
        3. **Communication Frequency**: Recommend timing
           - If first contact: "Initial sequence: Day 1, Day 3, Week 2"
           - If existing relationship: Based on historical patterns
           - Consider their engagement_times if available
        
        4. **Approach Strategy**: Tactical recommendations
           - How to introduce your company/solution
           - Key pain points to address based on their industry/profile
           - Value propositions most relevant to them
           - Call-to-action strategy (meeting, demo, info sharing)
        
        5. **Cultural Considerations**: 
           - Language preference
           - Regional business practices
           - Industry-specific approaches
        
        Return JSON:
        {{
            "engagement_channel": "Email|WhatsApp|LinkedIn",
            "tone_style": "Professional-Friendly|Formal|Consultative|Warm",
            "communication_frequency": "specific timing recommendation",
            "general_advice": "comprehensive strategy notes including approach tactics, pain points to address, value props, and cultural considerations",
            "recommended_intro_approach": "how to introduce yourself and company",
            "key_value_propositions": ["list of relevant value props for this client"],
            "suggested_cta": "recommended call to action for first/next contact",
            "confidence_level": "High|Medium|Low based on available data quality"
        }}
        
        Make strategic recommendations based on available data. If information is limited, 
        make conservative but professional assumptions and note the confidence level.
        """
        
        response = self.llm.invoke(strategy_prompt)
        content = response.content.strip()
        
        # Clean up JSON response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        try:
            strategy_data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback strategy if JSON parsing fails
            strategy_data = {
                "engagement_channel": "Email",
                "tone_style": "Professional-Friendly",
                "communication_frequency": "Initial sequence: Day 1, Day 3, Week 2",
                "general_advice": "Professional outreach focusing on AI-powered manufacturing solutions. " + content[:500],
                "recommended_intro_approach": "Introduce FabricX AI as AI manufacturing automation platform",
                "key_value_propositions": ["AI-powered efficiency", "Cost reduction", "Quality improvement"],
                "suggested_cta": "Schedule brief consultation call",
                "confidence_level": "Medium"
            }
        
        # Store strategy in database
        with self.session_factory() as session:
            # Remove existing strategy for this client
            session.query(InitialStrategy).filter_by(client_id=client_id).delete()
            session.commit()
            
            strategy = InitialStrategy(
                client_id=client_id,
                engagement_channel=strategy_data.get("engagement_channel", "Email"),
                tone_style=strategy_data.get("tone_style", "Professional-Friendly"),
                communication_frequency=strategy_data.get("communication_frequency", "Weekly"),
                general_advice=strategy_data.get("general_advice", "Standard professional approach"),
                generated_at=datetime.utcnow()
            )
            session.add(strategy)
            session.commit()
            session.refresh(strategy)
        
        return {
            "status": "strategy_created",
            "client_id": client_id,
            "strategy_id": strategy.strategy_id,
            "is_first_contact": is_first_contact,
            "strategy_details": strategy_data,
            "engagement_channel": strategy.engagement_channel,
            "tone_style": strategy.tone_style,
            "communication_frequency": strategy.communication_frequency,
            "confidence_level": strategy_data.get("confidence_level", "Medium")
        }
    
    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)