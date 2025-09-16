"""
Automatic Email Reply Scheduler Service

This service automatically checks for email replies to introductory emails
at configurable intervals and triggers appropriate responses.

Features:
- Background scheduling using APScheduler
- Configurable check intervals and retry counts
- Automatic integration with reply detection and immediate response workflow
- Comprehensive logging and monitoring
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from db.session import SessionLocal
from db.database_schema import IntroductoryEmail, User, Email, EmailDraft, Campaign, CampaignPlan, CampaignExecution, Client, Profile
from agents.email_reply_agent import EmailReplyDetectionAgent
from agents.immediate_reply_agent import ImmediateReplyAgent
from agents.automatic_campaign_creator_agent import AutomaticCampaignCreatorAgent
from services.campaign_email_delivery import CampaignEmailDeliveryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomaticReplyScheduler:
    """
    Automatic email reply checking scheduler that:
    1. Checks all introductory emails for replies at configured intervals
    2. Triggers immediate responses and campaign creation when replies are found
    3. Maintains configurable retry logic and scheduling
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.reply_detector = EmailReplyDetectionAgent()
        self.immediate_responder = ImmediateReplyAgent()
        self.campaign_creator = AutomaticCampaignCreatorAgent()
        self.campaign_email_delivery = CampaignEmailDeliveryService()
        
        # Configuration from environment variables
        self.config = {
            "check_count": int(os.getenv("REPLY_CHECK_COUNT", "2")),           # Number of times to check
            "check_interval_minutes": int(os.getenv("REPLY_CHECK_INTERVAL", "3")),  # Minutes between checks
            "max_email_age_hours": int(os.getenv("MAX_EMAIL_AGE_HOURS", "24")),     # Only check emails from last 24h
            "enabled": os.getenv("AUTO_REPLY_CHECK_ENABLED", "true").lower() == "true"
        }
        
        logger.info(f"🔧 AutomaticReplyScheduler initialized with config: {self.config}")
    
    def start(self):
        """Start the automatic reply checking scheduler"""
        if not self.config["enabled"]:
            logger.info("⏸️ Automatic reply checking is disabled via configuration")
            return
        
        logger.info("🚀 Starting automatic email reply checking scheduler...")
        
        # Schedule reply checks at configured intervals
        self.scheduler.add_job(
            func=self._check_all_introductory_emails,
            trigger=IntervalTrigger(minutes=self.config["check_interval_minutes"]),
            id='automatic_reply_check',
            name='Automatic Email Reply Check',
            replace_existing=True,
            max_instances=1  # Prevent overlapping executions
        )
        
        # Schedule campaign email delivery at regular intervals
        self.scheduler.add_job(
            func=self._deliver_scheduled_campaign_emails,
            trigger=IntervalTrigger(minutes=2),  # Check every 2 minutes for emails to deliver
            id='campaign_email_delivery',
            name='Campaign Email Delivery',
            replace_existing=True,
            max_instances=1  # Prevent overlapping executions
        )
        
        self.scheduler.start()
        logger.info(f"✅ Scheduler started - checking every {self.config['check_interval_minutes']} minutes")
        
        # Register shutdown handler
        atexit.register(lambda: self.scheduler.shutdown())
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            logger.info("🛑 Stopping automatic reply checking scheduler...")
            self.scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
    
    def _check_all_introductory_emails(self):
        """
        Main method that checks all recent introductory emails for replies
        and triggers appropriate responses
        """
        logger.info("📧 Starting automatic reply check for all introductory emails...")
        
        try:
            # Get all recent introductory emails
            recent_emails = self._get_recent_introductory_emails()
            logger.info(f"📋 Found {len(recent_emails)} recent introductory emails to check")
            
            replies_found = 0
            errors = 0
            
            for email_data in recent_emails:
                try:
                    # Update reply check count for this email (regardless of whether replies are found)
                    self._update_reply_check_count(email_data['email_id'])
                    
                    # Check if this specific email has replies
                    has_replies = self._check_email_for_replies(email_data)
                    
                    if has_replies:
                        logger.info(f"✉️ Reply found for email ID {email_data['email_id']} to {email_data['recipient_email']}")
                        
                        # Trigger immediate response workflow
                        self._handle_email_reply(email_data)
                        replies_found += 1
                    else:
                        logger.debug(f"📭 No replies for email ID {email_data['email_id']} to {email_data['recipient_email']}")
                
                except Exception as e:
                    logger.error(f"❌ Error checking email ID {email_data.get('email_id', 'unknown')}: {e}")
                    errors += 1
            
            logger.info(f"🎯 Reply check completed - {replies_found} replies found, {errors} errors")
            
            # After checking for replies, also check for emails that have reached max checks with no reply
            self._check_for_no_reply_emails()
            
        except Exception as e:
            logger.error(f"❌ Critical error in automatic reply check: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_recent_introductory_emails(self) -> List[Dict[str, Any]]:
        """
        Get all recent introductory emails that need reply checking
        Only returns emails that haven't exceeded the maximum check count
        Returns list of email data dictionaries
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=self.config["max_email_age_hours"])
        max_checks = self.config["check_count"]
        
        with SessionLocal() as session:
            # Import the correct model
            from db.database_schema import IntroductoryEmail
            
            # Get introductory emails that are:
            # 1. Successfully sent (sent_at is not None)
            # 2. Within the age limit  
            # 3. Not already replied (replied = False)
            # 4. Haven't exceeded maximum check attempts
            intro_emails = session.query(IntroductoryEmail).filter(
                IntroductoryEmail.sent_at.isnot(None),  # Only sent emails
                IntroductoryEmail.sent_at >= cutoff_time,  # Within age limit
                IntroductoryEmail.replied == False,  # Only check emails that haven't been replied to
                IntroductoryEmail.reply_check_count < max_checks  # Haven't exceeded max checks
            ).all()
            
            email_data = []
            for intro_email in intro_emails:
                # Get associated client info
                client = session.query(Client).filter_by(client_id=intro_email.client_id).first()
                
                if client:
                    # Get the draft to extract subject information
                    from db.database_schema import EmailDraft
                    draft = session.query(EmailDraft).filter_by(draft_id=intro_email.draft_id).first()
                    
                    email_data.append({
                        "email_id": intro_email.intro_id,  # Use intro_id as email_id
                        "client_id": intro_email.client_id,
                        "user_id": intro_email.user_id,
                        "recipient_email": client.email,  # Get email from client table
                        "subject": draft.subject if draft else "Introductory Email",  # Get subject from draft
                        "sent_at": intro_email.sent_at,
                        "campaign_id": None,  # Introductory emails don't have campaigns yet
                        "client_name": client.full_name,
                        "client_company": client.company,
                        "communication_method": intro_email.communication_method,
                        "replied": intro_email.replied,
                        "reply_check_count": intro_email.reply_check_count,
                        "last_reply_check": intro_email.last_reply_check
                    })
            
            return email_data
    
    def _check_email_for_replies(self, email_data: Dict[str, Any]) -> bool:
        """
        Check if a specific email has received replies
        Returns True if replies are found, False otherwise
        """
        try:
            # Use existing EmailReplyDetectionAgent with specific email context
            result = self.reply_detector.invoke({
                "user_id": email_data["user_id"],
                "specific_email": {
                    "email_id": email_data["email_id"],
                    "recipient": email_data["recipient_email"],
                    "subject": email_data["subject"],
                    "sent_at": email_data["sent_at"]
                }
            })
            
            # Check if any replies were detected
            return result.get("replies_found", False) and len(result.get("replies", [])) > 0
            
        except Exception as e:
            logger.error(f"❌ Error checking replies for email {email_data['email_id']}: {e}")
            return False
    
    def _handle_email_reply(self, email_data: Dict[str, Any]):
        """
        Handle the workflow when an email reply is detected:
        1. Send immediate reply
        2. Create automatic campaign
        3. Generate campaign plan
        """
        try:
            logger.info(f"🎯 Processing reply workflow for email ID {email_data['email_id']}")
            
            # First, get the reply details to extract the client reply text
            reply_result = self.reply_detector.invoke({
                "user_id": email_data["user_id"],
                "specific_email": {
                    "email_id": email_data["email_id"],
                    "recipient": email_data["recipient_email"],
                    "subject": email_data["subject"],
                    "sent_at": email_data["sent_at"]
                }
            })
            
            # Extract the reply text from the first reply
            client_reply_text = ""
            if reply_result.get("replies") and len(reply_result["replies"]) > 0:
                client_reply_text = reply_result["replies"][0].get("body", "")
            
            logger.info(f"📤 Reply text extracted: {client_reply_text[:100]}..." if len(client_reply_text) > 100 else f"📤 Reply text: {client_reply_text}")
            
            # Analyze sentiment of the reply
            sentiment_analysis = self.reply_detector.analyze_reply_sentiment(
                client_reply_text, 
                email_data["client_name"]
            )
            logger.info(f"🎭 Sentiment analysis: {sentiment_analysis.get('sentiment_category', 'unknown')}")
            
            # Step 1: Send immediate reply with reply text and sentiment analysis
            immediate_result = self.immediate_responder.invoke({
                "client_id": email_data["client_id"],
                "user_id": email_data["user_id"],
                "client_reply_text": client_reply_text,  # ✅ Add the required reply text
                "sentiment_analysis": sentiment_analysis,  # ✅ Add the required sentiment analysis
                "original_email_context": {
                    "subject": email_data["subject"],
                    "recipient": email_data["recipient_email"],
                    "sent_at": email_data["sent_at"]
                },
                "trigger": "automatic_reply_detection"
            })
            
            logger.info(f"📤 Immediate reply result: {immediate_result.get('status')}")
            
            # Step 2: Create automatic campaign (if immediate reply was successful)
            if immediate_result.get("status") == "immediate_reply_sent":
                campaign_result = self.campaign_creator.invoke({
                    "client_id": email_data["client_id"],
                    "user_id": email_data["user_id"],
                    "immediate_reply_context": immediate_result,
                    "trigger": "automatic_reply_workflow"
                })
                
                logger.info(f"📋 Campaign creation result: {campaign_result.get('status')}")
                
                # Step 3: Generate campaign plan (if campaign was created successfully)
                if campaign_result.get("status") == "campaign_auto_created":
                    try:
                        from agents.enhanced_campaign_planner_agent import EnhancedCampaignPlannerAgent
                        
                        planner = EnhancedCampaignPlannerAgent()
                        plan_result = planner.invoke({
                            "campaign_id": campaign_result.get("campaign_id")
                        })
                        
                        logger.info(f"📈 Campaign plan result: {plan_result.get('status')}")
                        logger.info(f"📅 Generated {plan_result.get('total_days', 0)} day plan")
                        
                    except Exception as plan_error:
                        logger.error(f"❌ Error generating campaign plan: {plan_error}")
                        # Continue anyway - campaign was created successfully
                
                # ✅ CRITICAL: Mark the introductory email as replied to prevent duplicate processing
                self._mark_introductory_email_as_replied(email_data["email_id"])
                
                # Log successful workflow completion
                logger.info(f"✅ Complete workflow executed for {email_data['recipient_email']} - Campaign created + Plan generated")
                
            else:
                logger.warning(f"⚠️ Immediate reply failed, skipping campaign creation")
                # Note: We don't mark as replied if the workflow failed, so it can retry later
                
        except Exception as e:
            logger.error(f"❌ Error in reply workflow for email {email_data['email_id']}: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_reply_check_count(self, intro_email_id: int):
        """Update the reply check count and last check timestamp for an introductory email"""
        try:
            from db.session import SessionLocal
            with SessionLocal() as session:
                intro_email = session.query(IntroductoryEmail).filter_by(intro_id=intro_email_id).first()
                
                if intro_email:
                    # Increment the check count
                    intro_email.reply_check_count += 1
                    intro_email.last_reply_check = datetime.utcnow()
                    session.commit()
                    
                    logger.info(f"📊 Updated reply check count for email ID {intro_email_id}: count={intro_email.reply_check_count}")
                else:
                    logger.error(f"❌ Introductory email ID {intro_email_id} not found for check count update")
                    
        except Exception as e:
            logger.error(f"❌ Error updating reply check count for email {intro_email_id}: {e}")
    
    def _check_for_no_reply_emails(self):
        """
        Check for introductory emails that have reached max check count without receiving replies
        and trigger the no-reply follow-up workflow
        """
        logger.info("🔍 Checking for emails that need no-reply follow-up workflow...")
        
        try:
            no_reply_emails = self._get_no_reply_candidate_emails()
            logger.info(f"📭 Found {len(no_reply_emails)} emails ready for no-reply follow-up")
            
            no_reply_workflows_triggered = 0
            
            for email_data in no_reply_emails:
                try:
                    # Trigger no-reply workflow for this email
                    logger.info(f"🚀 Triggering no-reply workflow for email ID {email_data['email_id']} to {email_data['recipient_email']}")
                    
                    # Import and trigger the no-reply workflow orchestrator
                    self._trigger_no_reply_workflow(email_data)
                    no_reply_workflows_triggered += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error triggering no-reply workflow for email {email_data.get('email_id', 'unknown')}: {e}")
            
            logger.info(f"✅ No-reply workflow check completed - {no_reply_workflows_triggered} workflows triggered")
            
        except Exception as e:
            logger.error(f"❌ Error in no-reply email detection: {e}")
    
    def _get_no_reply_candidate_emails(self) -> List[Dict[str, Any]]:
        """
        Get introductory emails that have reached max check count without receiving replies
        and haven't already had the no-reply workflow triggered
        """
        max_checks = self.config["check_count"]
        
        with SessionLocal() as session:
            try:
                # Get emails that have reached max check count, haven't been replied to,
                # and haven't already had no-reply workflow triggered
                intro_emails = session.query(IntroductoryEmail).filter(
                    IntroductoryEmail.sent_at.isnot(None),
                    IntroductoryEmail.replied == False,
                    IntroductoryEmail.reply_check_count >= max_checks,
                    IntroductoryEmail.no_reply_workflow_triggered != True  # Only emails that haven't had workflow triggered
                ).all()
                
                email_data = []
                
                for intro_email in intro_emails:
                    # Get client information
                    client = session.query(Client).filter_by(client_id=intro_email.client_id).first()
                    
                    if client:
                        email_data.append({
                            "email_id": intro_email.intro_id,
                            "client_id": intro_email.client_id,
                            "user_id": intro_email.user_id,
                            "client_name": client.full_name,
                            "recipient_email": client.email,
                            "subject": f"Follow-up: {intro_email.product_services}",
                            "sent_at": intro_email.sent_at,
                            "reply_check_count": intro_email.reply_check_count,
                            "last_reply_check": intro_email.last_reply_check,
                            "client_data": {
                                "full_name": client.full_name,
                                "email": client.email,
                                "phone": client.phone,
                                "company": client.company,
                                "company_website": client.company_website,
                                "linkedin_url": client.linkedin_url
                            },
                            "original_context": {
                                "client_type": intro_email.client_type,
                                "timezone": intro_email.timezone,
                                "preferred_language": intro_email.preferred_language,
                                "communication_method": intro_email.communication_method,
                                "product_services": intro_email.product_services
                            }
                        })
                
                return email_data
                
            except Exception as e:
                logger.error(f"❌ Error querying no-reply candidate emails: {e}")
                return []
    
    def _trigger_no_reply_workflow(self, email_data: Dict[str, Any]):
        """
        Trigger the no-reply follow-up workflow for an email that didn't receive responses
        """
        try:
            logger.info(f"📧 Starting no-reply workflow for client {email_data['client_name']} ({email_data['recipient_email']})")
            
            # Import and initialize the NoReplyWorkflowOrchestrator
            from agents.no_reply_workflow_orchestrator import NoReplyWorkflowOrchestrator
            orchestrator = NoReplyWorkflowOrchestrator()
            
            # Prepare email data for the orchestrator
            workflow_email_data = self._prepare_email_data_for_workflow(email_data)
            
            # Execute the complete no-reply workflow
            workflow_result = orchestrator.orchestrate_no_reply_workflow(workflow_email_data)
            
            if workflow_result["status"] == "workflow_completed":
                logger.info(f"✅ No-reply workflow completed for email ID {email_data['email_id']}, campaign ID {workflow_result['campaign_id']}")
                
                # Mark this email as having the no-reply workflow triggered
                self._mark_no_reply_workflow_triggered(email_data["email_id"], workflow_result["campaign_id"])
            else:
                logger.error(f"❌ No-reply workflow failed for email ID {email_data['email_id']}: {workflow_result.get('error')}")
                # Still mark as triggered to prevent retry loops
                self._mark_no_reply_workflow_triggered(email_data["email_id"])
            
        except Exception as e:
            logger.error(f"❌ Error in no-reply workflow trigger: {e}")
            # Mark as triggered even on error to prevent infinite retries
            self._mark_no_reply_workflow_triggered(email_data["email_id"])
    
    def _prepare_email_data_for_workflow(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare email data in the format expected by the NoReplyWorkflowOrchestrator
        Enhanced with real client profile and context data
        """
        try:
            # Get enhanced client data from database
            enhanced_data = self._get_enhanced_client_data(email_data["client_id"])
            
            return {
                "email_id": email_data["email_id"],
                "client_id": email_data["client_id"],
                "user_id": email_data["user_id"],
                "client_name": email_data["client_name"],
                "recipient_email": email_data["recipient_email"],
                "client_data": {
                    "full_name": email_data["client_name"],
                    "email": email_data["recipient_email"],
                    "company": enhanced_data.get("company", ""),
                    "company_website": enhanced_data.get("company_website", ""),
                    "linkedin_url": enhanced_data.get("linkedin_url", ""),
                    "industry": enhanced_data.get("industry", "Technology"),
                    "job_title": enhanced_data.get("job_title", "Professional"),
                    "interests": enhanced_data.get("interests", []),
                    "summary": enhanced_data.get("summary", "")
                },
                "original_context": {
                    "client_type": enhanced_data.get("client_type", "business"),
                    "timezone": enhanced_data.get("timezone", "UTC"),
                    "preferred_language": enhanced_data.get("preferred_language", "English"),
                    "communication_method": enhanced_data.get("communication_method", "email"),
                    "product_services": enhanced_data.get("product_services", "Professional Services"),
                    "original_subject": enhanced_data.get("original_subject", ""),
                    "business_area": enhanced_data.get("business_area", "operations")
                }
            }
        except Exception as e:
            logger.error(f"❌ Error preparing enhanced email data: {e}")
            # Fallback to basic data structure
            return {
                "email_id": email_data["email_id"],
                "client_id": email_data["client_id"],
                "user_id": email_data["user_id"],
                "client_name": email_data["client_name"],
                "recipient_email": email_data["recipient_email"],
                "client_data": {
                    "full_name": email_data["client_name"],
                    "email": email_data["recipient_email"],
                    "company": email_data.get("client_company", ""),
                    "company_website": ""
                },
                "original_context": {
                    "client_type": "business",
                    "timezone": "UTC",
                    "preferred_language": "English",
                    "communication_method": "email",
                    "product_services": "Professional Services"
                }
            }
    
    def _get_enhanced_client_data(self, client_id: int) -> Dict[str, Any]:
        """
        Get comprehensive client data from database for better personalization
        """
        try:
            from db.database_schema import Client, Profile, IntroductoryEmail, EmailDraft
            
            with SessionLocal() as session:
                # Get client basic data
                client = session.query(Client).filter(Client.client_id == client_id).first()
                
                # Get client profile for interests and industry insights
                profile = session.query(Profile).filter(Profile.client_id == client_id).first()
                
                # Get original introductory email context
                intro_email = session.query(IntroductoryEmail).filter(IntroductoryEmail.client_id == client_id).first()
                
                # Get original email subject if available
                original_subject = ""
                if intro_email and intro_email.draft_id:
                    draft = session.query(EmailDraft).filter(EmailDraft.draft_id == intro_email.draft_id).first()
                    if draft:
                        original_subject = draft.subject
                
                # Build enhanced data
                enhanced_data = {
                    "company": client.company if client else "",
                    "company_website": client.company_website if client else "",
                    "linkedin_url": client.linkedin_url if client else "",
                    "client_type": intro_email.client_type if intro_email else "business",
                    "timezone": intro_email.timezone if intro_email else "UTC",
                    "preferred_language": intro_email.preferred_language if intro_email else "English",
                    "communication_method": intro_email.communication_method if intro_email else "email",
                    "product_services": intro_email.product_services if intro_email else "Professional Services",
                    "original_subject": original_subject
                }
                
                # Add profile-based data for better personalization
                if profile:
                    interests_list = profile.interests.split(',') if profile.interests else []
                    enhanced_data.update({
                        "interests": [interest.strip() for interest in interests_list],
                        "summary": profile.summary or "",
                        # Determine industry from interests/summary
                        "industry": self._extract_industry_from_profile(interests_list, profile.summary),
                        "job_title": self._extract_job_title_from_profile(profile.summary),
                        "business_area": self._extract_business_area_from_profile(interests_list, profile.summary)
                    })
                else:
                    enhanced_data.update({
                        "interests": [],
                        "summary": "",
                        "industry": "Technology",
                        "job_title": "Professional",
                        "business_area": "operations"
                    })
                
                return enhanced_data
                
        except Exception as e:
            logger.error(f"❌ Error getting enhanced client data: {e}")
            return {}
    
    def _extract_industry_from_profile(self, interests: List[str], summary: str) -> str:
        """Extract industry from client interests and summary"""
        tech_keywords = ["software", "react", "node.js", "python", "aws", "cloud", "fintech", "engineering"]
        manufacturing_keywords = ["manufacturing", "production", "supply chain", "logistics"]
        finance_keywords = ["finance", "fintech", "banking", "investment"]
        
        text_to_check = " ".join(interests).lower() + " " + (summary or "").lower()
        
        if any(keyword in text_to_check for keyword in tech_keywords):
            return "Technology"
        elif any(keyword in text_to_check for keyword in finance_keywords):
            return "Financial Services"
        elif any(keyword in text_to_check for keyword in manufacturing_keywords):
            return "Manufacturing"
        else:
            return "Professional Services"
    
    def _extract_job_title_from_profile(self, summary: str) -> str:
        """Extract job title from summary"""
        if not summary:
            return "Professional"
            
        summary_lower = summary.lower()
        if "senior software engineer" in summary_lower:
            return "Senior Software Engineer"
        elif "software engineer" in summary_lower:
            return "Software Engineer"
        elif "manager" in summary_lower:
            return "Manager"
        elif "director" in summary_lower:
            return "Director"
        elif "ceo" in summary_lower or "founder" in summary_lower:
            return "Executive"
        else:
            return "Professional"
    
    def _extract_business_area_from_profile(self, interests: List[str], summary: str) -> str:
        """Extract business area focus from profile"""
        text_to_check = " ".join(interests).lower() + " " + (summary or "").lower()
        
        if any(keyword in text_to_check for keyword in ["development", "engineering", "software"]):
            return "software development"
        elif any(keyword in text_to_check for keyword in ["cloud", "aws", "microservices"]):
            return "cloud infrastructure"
        elif any(keyword in text_to_check for keyword in ["fintech", "finance"]):
            return "financial technology"
        else:
            return "technology operations"
    
    def _mark_no_reply_workflow_triggered(self, intro_email_id: int, campaign_id: int = None):
        """
        Mark an introductory email as having had the no-reply workflow triggered
        to prevent duplicate workflow execution
        """
        try:
            with SessionLocal() as session:
                intro_email = session.query(IntroductoryEmail).filter_by(intro_id=intro_email_id).first()
                
                if intro_email:
                    # Mark as no-reply workflow triggered to prevent duplicates
                    intro_email.no_reply_workflow_triggered = True
                    intro_email.no_reply_workflow_triggered_at = datetime.utcnow()
                    
                    # Campaign_id is already stored in the Campaign table, no need for metadata
                    
                    session.commit()
                    
                    campaign_info = f", campaign ID {campaign_id}" if campaign_id else ""
                    logger.info(f"✅ Marked email ID {intro_email_id} as no-reply workflow triggered{campaign_info}")
                    
                else:
                    logger.error(f"❌ Introductory email ID {intro_email_id} not found for no-reply workflow marking")
                    
        except Exception as e:
            logger.error(f"❌ Error marking no-reply workflow triggered for email {intro_email_id}: {e}")
    
    def _mark_introductory_email_as_replied(self, intro_email_id: int):
        """
        Mark an introductory email as replied to prevent duplicate processing
        
        Args:
            intro_email_id: The intro_id of the introductory email to mark as replied
        """
        try:
            with SessionLocal() as session:
                from db.database_schema import IntroductoryEmail
                
                # Get the introductory email record
                intro_email = session.query(IntroductoryEmail).filter_by(intro_id=intro_email_id).first()
                
                if intro_email:
                    # Update the replied status
                    intro_email.replied = True
                    session.commit()
                    
                    logger.info(f"✅ Marked introductory email ID {intro_email_id} as replied (replied=True)")
                else:
                    logger.error(f"❌ Introductory email ID {intro_email_id} not found in database")
                    
        except Exception as e:
            logger.error(f"❌ Error marking introductory email {intro_email_id} as replied: {e}")
            import traceback
            traceback.print_exc()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and configuration"""
        return {
            "scheduler_running": self.scheduler.running if self.scheduler else False,
            "config": self.config,
            "next_run": self.scheduler.get_job('automatic_reply_check').next_run_time.isoformat() 
                       if self.scheduler and self.scheduler.get_job('automatic_reply_check') else None,
            "jobs_count": len(self.scheduler.get_jobs()) if self.scheduler else 0
        }
    
    def _deliver_scheduled_campaign_emails(self):
        """
        Deliver scheduled campaign emails from CampaignExecution table.
        This method is called by the scheduler every 2 minutes.
        """
        logger.info("📧 Checking for scheduled campaign emails to deliver...")
        
        try:
            self.campaign_email_delivery.process_scheduled_emails()
        except Exception as e:
            logger.error(f"❌ Error in campaign email delivery: {e}")
            import traceback
            traceback.print_exc()

# Global scheduler instance
_scheduler_instance = None

def get_scheduler() -> AutomaticReplyScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AutomaticReplyScheduler()
    return _scheduler_instance

def start_automatic_reply_checking():
    """Start the automatic reply checking service"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler

def stop_automatic_reply_checking():
    """Stop the automatic reply checking service"""
    scheduler = get_scheduler()
    scheduler.stop()

def get_reply_check_status():
    """Get current status of the reply checking service"""
    scheduler = get_scheduler()
    return scheduler.get_status()