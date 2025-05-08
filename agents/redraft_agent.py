from datetime import datetime, timezone
from typing import Dict, Any

import os
import json
from dotenv import load_dotenv

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from db.session import get_session
from db.database_schema import EmailDraft, MessageDraft

load_dotenv()


class RedraftAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.25,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self._sf = get_session

    def _next_version(self, campaign_id: int, is_email: bool) -> int:
        """Return next incremental version number inside this campaign."""
        with self._sf() as s:
            if is_email:
                return s.query(EmailDraft).filter_by(campaign_id=campaign_id).count() + 1
            else:
                return s.query(MessageDraft).filter_by(campaign_id=campaign_id).count() + 1

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        draft_id = inputs["draft_id"]
        feedback = inputs["fb_comments"]
        channel = inputs.get("channel", "email").lower()  

        is_email = channel == "email"

        with self._sf() as s:
            
            prev = s.query(EmailDraft if is_email else MessageDraft).get(draft_id)
            if not prev:
                return {"status": "error", "detail": f"Draft {draft_id} not found"}

            if is_email:
                original_content = f"Subject: {prev.subject}\n\nBody:\n{prev.body_markdown}"
            else:
                original_content = prev.message_text

            
        prompt = (
            "You are an assistant improving a sales-outreach draft.\n"
            "----- Original Draft -----\n"
            f"{original_content}\n"
            "----- Reviewer Feedback -----\n"
            f"{feedback}\n"
            "--------------------------------\n"
            "If the draft is an email, return valid JSON with subject and body:\n"
            "{ \"subject\": \"...\", \"body_markdown\": \"...\" }\n"
            "If the draft is a message, return just the updated text.\n"
            "Rewrite the draft, applying the feedback precisely while preserving its goal.\n"
            "Return *only* the improved version. No markdown formatting like ```json."
        )

        raw_output = self.llm.invoke(prompt)
        raw_content = raw_output.content.strip()

        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content

        
        if is_email:
            try:
                parsed = json.loads(cleaned)
                subject = parsed["subject"]
                body = parsed["body_markdown"]
            except (json.JSONDecodeError, KeyError):
                subject = prev.subject
                body = cleaned
        else:
            subject = ""
            body = cleaned

        v_no = self._next_version(prev.campaign_id, is_email)

        # Delete previous draft and insert new one
        if is_email:
            s.delete(prev)
            s.commit()  # Commit deletion before inserting new draft

            new_draft = EmailDraft(
                campaign_id=prev.campaign_id,
                contact_id=prev.contact_id,
                day = prev.day,
                version_no=v_no,
                subject=subject,
                body_markdown=body,
                is_approved=False,
                created_at=datetime.now(timezone.utc)
            )
        else:
            s.delete(prev)
            s.commit()

            new_draft = MessageDraft(
                campaign_id=prev.campaign_id,
                contact_id=prev.contact_id,
                day = prev.day,
                version_no=v_no,
                message_text=body,
                is_approved=False,
                created_at=datetime.now(timezone.utc)
            )

        s.add(new_draft)
        s.commit()
        s.refresh(new_draft)

        return {
            "status": "draft_revised",
            "draft_id": new_draft.draft_id,
            "subject": subject,
            "draft_content": body,
            "channel": channel
        }


    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)
