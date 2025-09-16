from typing import Dict, Any
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import json
import os
import pytz

from db.session import SessionLocal
from db.database_schema import EmailDraft, Client, Profile, InitialStrategy, Campaign, User, Email, IntroductoryEmail
from agents.email_sender_agent import EmailSenderAgent
from sqlmodel import select

class IntroductoryEmailAgent(Runnable):
    """
    Sends initial contact email based on BRM workflow requirements.
    This is the first touchpoint with a client - separate from campaigns.
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.session_factory = SessionLocal
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        client_id = inputs["client_id"]
        user_id = inputs["user_id"]
        
        with self.session_factory() as session:
            client = session.get(Client, client_id)
            profile = session.query(Profile).filter_by(client_id=client_id).first()
            strategy = session.query(InitialStrategy).filter_by(client_id=client_id).first()
            user = session.get(User, user_id)
        
        # Parameters from workflow diagram - get company info dynamically from user profile
        intro_params = {
            "client_type": client.category or "Business Contact",
            "timezone": "Asia/Dhaka",  # or extract from profile
            "preferred_language": profile.preferred_language if profile else "English", 
            "communication_method": strategy.engagement_channel if strategy else "Email",
            "company_name": user.company_name or "FabricX AI",
            "company_description": user.company_description or "AI-Powered Garment Manufacturing Automation Platform",
            "company_website": user.company_website or "fabricxai.com",
            "sender_title": user.job_title or "Business Development",
            "product_services": user.company_description or "AI-Powered Manufacturing Solutions"
        }
        
        prompt = f"""
        You are writing an introductory email for first contact with a potential client.
        
        CLIENT DETAILS:
        - Name: {client.full_name}
        - Company: {client.company}
        - Type: {intro_params['client_type']}
        - Preferred Language: {intro_params['preferred_language']}
        - Communication Method: {intro_params['communication_method']}
        
        SENDER COMPANY INFO:
        - Company: {intro_params['company_name']}
        - Description: {intro_params['company_description']}
        - Website: {intro_params['company_website']}
        - Sender: {user.name} - {intro_params['sender_title']}
        - Email: {user.email}
        
        CLIENT INTERESTS (if available):
        {profile.interests if profile else "Manufacturing, Technology"}
        
        Write a professional introductory email that:
        1. Introduces yourself, your role, and your company clearly
        2. Briefly explains how you found their information (LinkedIn, industry research)
        3. Mentions 1-2 specific benefits relevant to their industry/interests
        4. Shows knowledge of their company or industry challenges
        5. Includes soft call-to-action for future communication
        6. Respects their {intro_params['preferred_language']} language preference
        7. Keeps professional tone but not overly sales-y
        
        Return JSON:
        {{
            "subject": "Clear, professional subject line", 
            "body_markdown": "Professional email body in markdown format"
        }}
        """
        
        response = self.llm.invoke(prompt)
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
            
        try:
            parsed = json.loads(content)
        except:
            parsed = {
                "subject": "Introduction from FabricX AI",
                "body_markdown": content
            }
        
        # Store as special introductory draft (campaign_id = NULL for intro emails)
        with self.session_factory() as session:
            intro_draft = EmailDraft(
                campaign_id=None,  # Special marker for intro emails
                contact_id=client_id,
                version_no=1,
                subject=parsed["subject"],
                day=0,  # Day 0 = introductory email
                body_markdown=parsed["body_markdown"],
                is_approved=False,
                created_at=datetime.utcnow()
            )
            session.add(intro_draft)
            session.commit()
            session.refresh(intro_draft)
            
            # Create Email record for tracking (similar to campaign emails)
            email_record = Email(
                draft_id=intro_draft.draft_id,
                personalized_body=parsed["body_markdown"],  # For intro emails, body is already personalized
                subject=parsed["subject"],
                is_final=True,  # Auto-approve intro emails
                approved_at=datetime.utcnow()
            )
            session.add(email_record)
            session.commit()
            session.refresh(email_record)
            
            # Create or update IntroductoryEmail record
            intro_email_record = session.exec(
                select(IntroductoryEmail).where(IntroductoryEmail.client_id == client_id)
            ).first()
            
            if not intro_email_record:
                intro_email_record = IntroductoryEmail(
                    client_id=client_id,
                    user_id=user_id,
                    client_type=intro_params['client_type'],
                    timezone=intro_params['timezone'],
                    preferred_language=intro_params['preferred_language'],
                    communication_method=intro_params['communication_method'],
                    product_services=intro_params['product_services'],
                    draft_id=intro_draft.draft_id,
                    replied=False,
                    created_at=datetime.utcnow()
                )
                session.add(intro_email_record)
            else:
                intro_email_record.draft_id = intro_draft.draft_id
                
            session.commit()
            
            # Send the email using EmailSenderAgent
            sender_agent = EmailSenderAgent()
            try:
                sender_agent.send_email(
                    recipient_email=client.email,
                    subject=parsed["subject"],
                    body=parsed["body_markdown"]
                )
                
                # Update sent_at timestamp (store in UTC for consistency)
                intro_email_record.sent_at = datetime.utcnow()
                email_record.sent_at = datetime.utcnow()
                session.add(intro_email_record)
                session.add(email_record)
                session.commit()
                
                email_status = "sent"
                
            except Exception as e:
                print(f"Failed to send introductory email: {e}")
                email_status = "failed"
        
        return {
            "status": f"intro_email_{email_status}",
            "client_id": client_id,
            "draft_id": intro_draft.draft_id,
            "email_id": email_record.email_id,
            "subject": parsed["subject"],
            "sent_to": client.email,
            "company_info": {
                "company_name": intro_params['company_name'],
                "company_description": intro_params['company_description'],
                "sender": f"{user.name} - {intro_params['sender_title']}"
            },
            "intro_params": intro_params
        }
    
    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)