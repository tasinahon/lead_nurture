from typing import Dict, Any
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import os
from datetime import datetime

from db.session import SessionLocal
from db.database_schema import EmailDraft, Client, Profile, InitialStrategy

class ImmediateReplyAgent(Runnable):
    """
    Generates immediate reply emails based on client sentiment analysis.
    Part of BRM workflow after "Agent 4: reading email Sentiment analysis"
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.4,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.session_factory = SessionLocal
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate immediate reply based on:
        1. Client's original reply text
        2. Sentiment analysis results 
        3. Client profile information
        """
        client_id = inputs["client_id"]
        client_reply = inputs["client_reply_text"]
        sentiment_analysis = inputs["sentiment_analysis"]
        
        with self.session_factory() as session:
            client = session.get(Client, client_id)
            profile = session.query(Profile).filter_by(client_id=client_id).first()
            strategy = session.query(InitialStrategy).filter_by(client_id=client_id).first()
        
        # Generate contextual reply based on sentiment
        reply_prompt = f"""
        You are writing an immediate reply to a client's email response.
        
        CLIENT DETAILS:
        - Name: {client.full_name}
        - Company: {client.company}
        - Industry: {client.category or 'Manufacturing'}
        
        CLIENT'S REPLY: 
        {client_reply}
        
        SENTIMENT ANALYSIS:
        - Sentiment: {sentiment_analysis.get('sentiment', 'neutral')}
        - Interest Level: {sentiment_analysis.get('interest_level', 'unknown')}
        - Response Type: {sentiment_analysis.get('response_type', 'unclear')}
        - Key Concerns: {sentiment_analysis.get('key_concerns', [])}
        - Suggested Action: {sentiment_analysis.get('suggested_action', 'follow_up')}
        
        REPLY STRATEGY:
        Based on the sentiment and response type, write an appropriate immediate reply that:
        
        If POSITIVE/INTERESTED:
        - Thank them for their interest
        - Address any specific questions they asked
        - Propose next steps (meeting, demo, call)
        - Provide specific availability times (e.g., "I'm available Tuesday and Wednesday afternoon") 
        - DO NOT use placeholder variables in curly braces - provide real, actionable information
        
        If NEUTRAL/NEEDS_INFO:
        - Acknowledge their response
        - Provide requested information clearly
        - Offer additional resources
        - Gentle follow-up suggestion
        
        If NEGATIVE/NOT_INTERESTED:
        - Respect their decision professionally  
        - Leave door open for future
        - Offer to remove from further communications
        - Thank them for their time
        
        If BUSY/TIMING_ISSUES:
        - Acknowledge their current situation
        - Suggest alternative timing
        - Offer to reconnect later
        - Keep it brief and respectful
        
        Return JSON:
        {{
            "subject": "Re: [original subject or contextual]",
            "body_markdown": "Professional email reply body",
            "priority": "high|medium|low",
            "send_immediately": true/false
        }}
        
        CRITICAL REQUIREMENTS:
        - NEVER use placeholder variables in curly braces like company_name, calendar_link, google_meet_link, etc.
        - All information must be complete and ready to send
        - If mentioning availability, use specific days/times like "Tuesday afternoon" or "next week"
        - If suggesting a meeting, say "let me know your availability" instead of placeholder links
        - The email must be 100% complete with no template variables
        
        Keep it professional, personalized, and action-oriented.
        """
        
        response = self.llm.invoke(reply_prompt)
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        try:
            reply_data = json.loads(content)
        except:
            # Fallback if JSON parsing fails
            reply_data = {
                "subject": f"Re: Thank you for your response",
                "body_markdown": content,
                "priority": "medium", 
                "send_immediately": True
            }
        
        # Store as immediate reply draft and send if auto-send enabled
        with self.session_factory() as session:
            reply_draft = EmailDraft(
                campaign_id=None,  # Immediate replies aren't part of campaigns
                contact_id=client_id,
                version_no=1,
                subject=reply_data["subject"],
                day=-1,  # Special marker for immediate replies
                body_markdown=reply_data["body_markdown"],
                is_approved=reply_data.get("send_immediately", False),  # Auto-approve if marked
                created_at=datetime.utcnow()
            )
            session.add(reply_draft)
            session.commit()
            session.refresh(reply_draft)
            
            # If auto-send is enabled, create Email record and send
            email_status = "draft_created"
            email_id = None
            
            if reply_data.get("send_immediately", False):
                try:
                    # Create Email record
                    from db.database_schema import Email
                    email_record = Email(
                        draft_id=reply_draft.draft_id,
                        personalized_body=reply_data["body_markdown"],
                        subject=reply_data["subject"],
                        is_final=True,
                        approved_at=datetime.utcnow()
                    )
                    session.add(email_record)
                    session.commit()
                    session.refresh(email_record)
                    
                    # Send the email
                    from agents.email_sender_agent import EmailSenderAgent
                    sender_agent = EmailSenderAgent()
                    sender_agent.send_email(
                        recipient_email=client.email,
                        subject=reply_data["subject"],
                        body=reply_data["body_markdown"]
                    )
                    
                    # Update sent timestamp
                    email_record.sent_at = datetime.utcnow()
                    session.add(email_record)
                    session.commit()
                    
                    email_status = "sent"
                    email_id = email_record.email_id
                    
                    # ✨ CAMPAIGN CREATION MOVED TO SCHEDULER
                    # Note: Campaign creation is now handled by AutomaticReplyScheduler 
                    # to prevent duplicate campaigns. The scheduler calls both 
                    # ImmediateReplyAgent and AutomaticCampaignCreatorAgent in sequence.
                    
                    # The workflow is now:
                    # 1. Scheduler detects reply
                    # 2. Scheduler calls ImmediateReplyAgent (this agent) - sends reply only
                    # 3. Scheduler calls AutomaticCampaignCreatorAgent - creates campaign
                    # 4. Campaign planner generates plan
                    
                    # This prevents duplicate campaign creation
                    
                    # Just log that immediate reply was sent successfully
                    print(f"✅ Immediate reply sent to {client.email}")
                    print("📋 Campaign creation will be handled by AutomaticReplyScheduler")
                    
                    # Return success without campaign creation
                    campaign_result = {
                        "status": "deferred_to_scheduler",
                        "message": "Campaign creation handled by scheduler to prevent duplicates"
                    }
                    
                except Exception as e:
                    print(f"Failed to send immediate reply: {e}")
                    email_status = "send_failed"
                    campaign_result = {}
        
        result = {
            "status": f"immediate_reply_{email_status}",
            "client_id": client_id,
            "draft_id": reply_draft.draft_id,
            "email_id": email_id,
            "subject": reply_data["subject"],
            "priority": reply_data["priority"],
            "auto_send": reply_data.get("send_immediately", False),
            "sentiment_handled": sentiment_analysis.get('response_type')
        }
        
        # Add campaign creation result if successful
        if email_status == "sent" and 'campaign_result' in locals():
            result.update({
                "auto_campaign": campaign_result,
                "workflow_completed": "immediate_reply_sent_campaign_created_plan_generated"
            })
        
        return result
    
    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)