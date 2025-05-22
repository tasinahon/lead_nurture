from datetime import datetime
from typing import Dict, Any
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable

from db.session import get_session
from db.session import SessionLocal
from db.database_schema import Email, Message

# Load environment variables
load_dotenv()

class RepersonalizeAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self._sf = SessionLocal

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        current_draft = inputs["draft_content"]
        feedback_text = inputs["feedback_text"]
        channel = inputs.get("channel", "email").lower()

        prompt = (
            "You are an assistant finalizing a professional draft for communication.\n"
            f"Current Draft:\n{current_draft}\n\n"
            f"Final Human Feedback:\n{feedback_text}\n\n"
            "Make minor adjustments based on feedback. Ensure tone, grammar, clarity, and personalization are perfect.\n"
            "Return only the final draft."
        )

        final_draft = self.llm.predict(prompt).strip()

        with self._sf() as s:
            if channel == "email":
                obj = Email(
                    draft_id=inputs["pers_id"],
                    personalized_body=final_draft,
                    is_final=True,
                    approved_at=datetime.utcnow()
                )
            else:
                obj = Message(
                    draft_id=inputs["pers_id"],
                    personalized_text=final_draft,
                    is_final=True,
                    approved_at=datetime.utcnow()
                )
            s.add(obj)
            s.commit()
            s.refresh(obj)

        return {
            "status": "repersonalised",
            "pers_id": obj.email_id if channel == "email" else obj.message_id,
            "draft_content": final_draft,
            "channel": channel
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)