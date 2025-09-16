#!/usr/bin/env python3
"""
Campaign Email Delivery Service

This service handles the actual delivery of emails stored in the CampaignExecution table.
It processes emails with status="generated" and sends them via SMTP.
"""

import sys
import os

# Add the parent directory to sys.path so we can import db modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import select
from db.session import SessionLocal
from db.database_schema import CampaignExecution, Campaign, Client, IntroductoryEmail
from agents.email_sender_agent import EmailSenderAgent

logger = logging.getLogger(__name__)


class CampaignEmailDeliveryService:
    """Service to deliver scheduled campaign emails"""
    
    def __init__(self):
        self.session_factory = SessionLocal
        self.email_sender = EmailSenderAgent()
        
    def process_scheduled_emails(self):
        """
        Check for emails ready to be sent and deliver them.
        This should be called periodically by APScheduler.
        """
        
        try:
            logger.info("🔍 Checking for scheduled emails to deliver...")
            
            with self.session_factory() as session:
                # Get emails that are ready to be sent
                ready_emails = self._get_ready_emails(session)
                
                if not ready_emails:
                    logger.info("No emails ready for delivery")
                    return
                
                logger.info(f"📧 Found {len(ready_emails)} emails ready for delivery")
                
                # Process each email
                for execution in ready_emails:
                    try:
                        self._deliver_email(session, execution)
                    except Exception as e:
                        logger.error(f"❌ Failed to deliver email {execution.execution_id}: {e}")
                        self._mark_email_failed(session, execution, str(e))
                
                session.commit()
                
        except Exception as e:
            logger.error(f"❌ Error in process_scheduled_emails: {e}")
    
    def _get_ready_emails(self, session) -> List[CampaignExecution]:
        """
        Get emails that are ready to be sent based on:
        1. Status = "generated" 
        2. Current time >= scheduled_at time
        """
        
        current_time = datetime.utcnow()
        
        ready_emails = session.exec(
            select(CampaignExecution)
            .where(CampaignExecution.status == "generated")
            .where(
                # Send if scheduled_at is null (immediate) or current time >= scheduled time
                (CampaignExecution.scheduled_at.is_(None)) | 
                (CampaignExecution.scheduled_at <= current_time)
            )
            .order_by(CampaignExecution.generated_at)
        ).all()
        
        return list(ready_emails)
    
    def _deliver_email(self, session, execution: CampaignExecution):
        """
        Deliver a single campaign email
        """
        
        logger.info(f"📤 Delivering email {execution.execution_id}: {execution.email_subject}")
        
        # Get campaign details to find recipient
        campaign = session.exec(
            select(Campaign).where(Campaign.campaign_id == execution.campaign_id)
        ).first()
        
        if not campaign:
            raise Exception(f"Campaign {execution.campaign_id} not found")
        
        # Get client details directly from the campaign
        client = session.exec(
            select(Client).where(Client.client_id == campaign.client_id)
        ).first()
        
        if not client:
            raise Exception(f"Client {campaign.client_id} not found")
        
        # Send the email
        try:
            self.email_sender.send_email(
                recipient_email=client.email,
                subject=execution.email_subject,
                body=execution.email_content
            )
            
            # Mark as sent
            execution.status = "sent"
            execution.sent_at = datetime.utcnow()
            
            logger.info(f"✅ Successfully delivered email {execution.execution_id} to {client.email}")
            
        except Exception as e:
            logger.error(f"❌ SMTP delivery failed for email {execution.execution_id}: {e}")
            raise e
    
    def _mark_email_failed(self, session, execution: CampaignExecution, error_message: str):
        """
        Mark an email as failed to send
        """
        
        execution.status = "failed"
        # You might want to add an error_message field to CampaignExecution table
        logger.error(f"📧 Marked email {execution.execution_id} as failed: {error_message}")
    
    def send_immediate_test_email(self, execution_id: int) -> bool:
        """
        Send a specific campaign email immediately (for testing)
        """
        
        try:
            with self.session_factory() as session:
                execution = session.exec(
                    select(CampaignExecution).where(CampaignExecution.execution_id == execution_id)
                ).first()
                
                if not execution:
                    logger.error(f"Campaign execution {execution_id} not found")
                    return False
                
                if execution.status != "generated":
                    logger.error(f"Email {execution_id} has status '{execution.status}', cannot send")
                    return False
                
                self._deliver_email(session, execution)
                session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to send test email {execution_id}: {e}")
            return False
    
    def get_pending_emails_count(self) -> int:
        """
        Get count of emails waiting to be sent
        """
        
        with self.session_factory() as session:
            count = session.exec(
                select(CampaignExecution).where(CampaignExecution.status == "generated")
            ).all()
            
            return len(count)


def main():
    """Test the campaign email delivery service"""
    
    logging.basicConfig(level=logging.INFO)
    
    delivery_service = CampaignEmailDeliveryService()
    
    logger.info("🚀 Testing Campaign Email Delivery Service")
    
    # Check pending emails
    pending_count = delivery_service.get_pending_emails_count()
    logger.info(f"📊 Pending emails: {pending_count}")
    
    if pending_count > 0:
        # Process scheduled emails
        delivery_service.process_scheduled_emails()
        
        # Check again
        new_pending_count = delivery_service.get_pending_emails_count()
        logger.info(f"📊 Pending emails after processing: {new_pending_count}")
    else:
        logger.info("No emails to process")


if __name__ == "__main__":
    main()