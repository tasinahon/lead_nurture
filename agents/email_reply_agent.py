from typing import Dict, Any, List, Optional
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
import imaplib
import email
import json
import os
from datetime import datetime, timedelta

from db.session import SessionLocal
from db.database_schema import Client, Email as EmailModel, EmailDraft, Campaign

class EmailReplyDetectionAgent(Runnable):
    """
    Agent 4 from BRM workflow: Monitors email replies and performs sentiment analysis.
    Determines if client replied (yes/no) and analyzes sentiment for next steps.
    """
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", 
            temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.session_factory = SessionLocal
        
    def check_email_replies(self, client_email: str, sent_subject: str, sent_time: datetime) -> List[Dict]:
        """Check IMAP inbox for replies from specific client"""
        try:
            # IMAP credentials
            imap_server = os.getenv("IMAP_HOST", "mail.privateemail.com")
            username = os.getenv("SMTP_EMAIL")
            password = os.getenv("SMTP_PASSWORD")
            
            print(f"🔍 [DEBUG] Checking replies from: {client_email}")
            print(f"🔍 [DEBUG] Original subject: {sent_subject}")
            print(f"🔍 [DEBUG] Sent time: {sent_time}")
            
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(username, password)
            mail.select('inbox')
            
            # Search for ALL emails from client (remove date restriction for now)
            _, data = mail.search(None, f'FROM "{client_email}"')
            
            print(f"🔍 [DEBUG] Found {len(data[0].split()) if data[0] else 0} emails from client")
            
            replies = []
            for num in data[0].split():
                _, msg_data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                email_subject = msg.get('Subject', '')
                email_date_str = msg.get('Date', '')
                
                print(f"🔍 [DEBUG] Checking email: {email_subject}")
                print(f"🔍 [DEBUG] Email date: {email_date_str}")
                
                # Parse email date to check if it's after our sent time
                try:
                    from email.utils import parsedate_to_datetime
                    import pytz
                    email_date = parsedate_to_datetime(msg.get('Date'))
                    
                    # Convert both times to UTC for proper comparison
                    if email_date and sent_time:
                        # Handle timezone conversion properly
                        if sent_time.tzinfo is None:
                            # Naive datetime - assume UTC (standard for PostgreSQL)
                            sent_time_utc = sent_time.replace(tzinfo=pytz.UTC)
                            print(f"🔍 [DEBUG] Naive datetime - assuming UTC")
                        else:
                            # Timezone-aware datetime - convert to UTC properly
                            sent_time_utc = sent_time.astimezone(pytz.UTC)
                            print(f"🔍 [DEBUG] Timezone-aware datetime: {sent_time} -> {sent_time_utc}")
                        
                        # Convert email date to UTC
                        email_date_utc = email_date.astimezone(pytz.UTC)
                        
                        print(f"🔍 [DEBUG] Time comparison (UTC): Reply {email_date_utc} vs Original {sent_time_utc}")
                        print(f"🔍 [DEBUG] Original database time: {sent_time}")
                        print(f"🔍 [DEBUG] Database timezone aware: {sent_time.tzinfo is not None}")
                        
                        # Add a small buffer to account for processing delays (but not too large)
                        time_buffer = timedelta(seconds=5)  # Small buffer for processing delays
                        
                        if email_date_utc <= (sent_time_utc + time_buffer):
                            print(f"🔍 [DEBUG] Skipping - email sent before/around original time (within 5s)")
                            continue  # Skip emails sent before our original (with small buffer)
                        else:
                            print(f"🔍 [DEBUG] ✅ Valid reply - sent AFTER original! (Difference: {(email_date_utc - sent_time_utc).total_seconds():.0f} seconds)")
                except Exception as e:
                    print(f"🔍 [DEBUG] Date parse error: {e}, including anyway")
                    pass  # If can't parse date, include it anyway
                
                # More flexible subject matching
                email_subject_lower = email_subject.lower()
                original_subject_lower = sent_subject.lower()
                
                print(f"🔍 [DEBUG] Subject comparison: '{email_subject_lower}' vs '{original_subject_lower}'")
                
                # STRICT reply detection - must be a genuine response
                is_reply = (
                    # Must have "Re:" prefix (standard email reply format)
                    email_subject_lower.startswith('re:') or
                    # OR exact subject match with "Re:" added
                    email_subject_lower == f"re: {original_subject_lower}" or
                    # OR must contain significant portion of original subject (at least 50% of words)
                    (len(set(original_subject_lower.split()) & set(email_subject_lower.split())) >= max(1, len(original_subject_lower.split()) // 2))
                )
                
                print(f"🔍 [DEBUG] Is reply: {is_reply}")
                
                if is_reply:
                    print(f"🔍 [DEBUG] ✅ Adding reply to results!")
                    replies.append({
                        'subject': msg.get('Subject'),
                        'body': self._extract_email_body(msg),
                        'received_time': msg.get('Date'),
                        'from': msg.get('From')
                    })
            
            mail.close()
            mail.logout()
            return replies
            
        except Exception as e:
            print(f"Error checking email replies: {e}")
            return []
    
    def _extract_email_body(self, msg) -> str:
        """Extract plain text body from email message"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""
    
    def analyze_reply_sentiment(self, reply_text: str, client_name: str) -> Dict[str, Any]:
        """Perform sentiment analysis on client reply"""
        prompt = f"""
        You are analyzing a client reply email for sentiment and intent.
        
        Client: {client_name}
        Reply Text: {reply_text}
        
        Analyze and return JSON with:
        {{
            "sentiment": "positive|neutral|negative", 
            "interest_level": "high|medium|low|none",
            "response_type": "interested|needs_info|busy|not_interested|spam",
            "key_concerns": ["concern1", "concern2"],
            "suggested_action": "immediate_follow_up|schedule_meeting|send_info|wait_period|end_campaign",
            "urgency": "high|medium|low",
            "summary": "Brief summary of client's response"
        }}
        
        Be accurate in sentiment detection for business decision making.
        """
        
        response = self.llm.invoke(prompt)
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        try:
            return json.loads(content)
        except:
            return {
                "sentiment": "neutral",
                "interest_level": "unknown", 
                "response_type": "unclear",
                "key_concerns": [],
                "suggested_action": "manual_review",
                "urgency": "low",
                "summary": "Could not parse reply properly"
            }
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main workflow from BRM diagram:
        1. Check if client replied (yes/no branch)
        2. If yes, analyze sentiment 
        3. Return action recommendation
        
        Supports two modes:
        - Single email check: pass email_id
        - Specific email check: pass specific_email dict for automatic scheduler
        """
        # Check for specific email mode (used by automatic scheduler)
        if "specific_email" in inputs:
            return self._check_specific_email_replies(inputs["specific_email"], inputs.get("user_id", 1))
        
        # Original single email check mode
        email_id = inputs["email_id"]
        
        with self.session_factory() as session:
            # Get sent email details
            sent_email = session.get(EmailModel, email_id)
            if not sent_email:
                return {"status": "error", "message": "Email not found"}
            
            draft = session.get(EmailDraft, sent_email.draft_id)
            client = session.get(Client, draft.contact_id)
            
        # Check for replies
        replies = self.check_email_replies(
            client.email, 
            sent_email.subject, 
            sent_email.sent_at
        )
        
        if not replies:
            # NO REPLY BRANCH from workflow
            return {
                "status": "no_reply",
                "has_reply": False,
                "email_id": email_id,
                "client_id": client.client_id,
                "next_action": "continue_campaign_or_follow_up"
            }
        
        # YES REPLY BRANCH - Analyze sentiment
        latest_reply = replies[0]  # Most recent
        sentiment_analysis = self.analyze_reply_sentiment(
            latest_reply['body'], 
            client.full_name
        )
        
        # Store reply analysis in database (you may want to create a new table for this)
        analysis_result = {
            "status": "reply_received", 
            "has_reply": True,
            "email_id": email_id,
            "client_id": client.client_id,
            "reply_count": len(replies),
            "sentiment_analysis": sentiment_analysis,
            "reply_text": latest_reply['body'][:500],  # Truncate for storage
            "next_action": sentiment_analysis["suggested_action"]
        }
        
        return analysis_result
    
    def _check_specific_email_replies(self, specific_email: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Check for replies to a specific email (used by automatic scheduler)
        
        Args:
            specific_email: Dict with email_id, recipient, subject, sent_at
            user_id: User ID for context
            
        Returns:
            Dict with reply detection results
        """
        try:
            # Extract email details
            email_id = specific_email["email_id"]
            recipient_email = specific_email["recipient"]
            subject = specific_email["subject"]
            sent_at = specific_email["sent_at"]
            
            print(f"🔍 [SCHEDULER DEBUG] Checking specific email {email_id} to {recipient_email}")
            
            # Use existing reply checking logic
            replies = self.check_email_replies(recipient_email, subject, sent_at)
            
            has_replies = len(replies) > 0
            
            # If replies found, analyze sentiment
            if has_replies:
                print(f"✉️ [SCHEDULER DEBUG] Found {len(replies)} replies for email {email_id}")
                
                # Analyze sentiment for each reply
                analyzed_replies = []
                for reply in replies:
                    sentiment_result = self.analyze_reply_sentiment(reply['body'], recipient_email)
                    analyzed_replies.append({
                        **reply,
                        'sentiment': sentiment_result.get('sentiment_category', 'neutral'),
                        'confidence': sentiment_result.get('confidence_score', 0.5),
                        'next_action': sentiment_result.get('suggested_action', 'follow_up')
                    })
                
                return {
                    "status": "replies_found",
                    "email_id": email_id,
                    "recipient": recipient_email,
                    "replies_found": True,
                    "reply_count": len(analyzed_replies),
                    "replies": analyzed_replies,
                    "overall_sentiment": self._determine_overall_sentiment(analyzed_replies),
                    "recommended_action": "immediate_reply"
                }
            else:
                print(f"📭 [SCHEDULER DEBUG] No replies found for email {email_id}")
                return {
                    "status": "no_replies",
                    "email_id": email_id,
                    "recipient": recipient_email,
                    "replies_found": False,
                    "reply_count": 0,
                    "replies": [],
                    "recommended_action": "wait_or_follow_up"
                }
                
        except Exception as e:
            print(f"❌ [SCHEDULER DEBUG] Error checking email {specific_email.get('email_id', 'unknown')}: {e}")
            return {
                "status": "error",
                "email_id": specific_email.get("email_id"),
                "error": str(e),
                "replies_found": False,
                "reply_count": 0,
                "replies": []
            }
    
    def _determine_overall_sentiment(self, analyzed_replies: List[Dict]) -> str:
        """Determine overall sentiment from multiple replies"""
        if not analyzed_replies:
            return "neutral"
        
        sentiments = [reply.get('sentiment', 'neutral') for reply in analyzed_replies]
        
        # Simple majority rule
        positive_count = sentiments.count('positive')
        negative_count = sentiments.count('negative')
        
        if positive_count > negative_count:
            return "positive" 
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)