from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain.tools import tool
from pydantic import BaseModel
from langchain_core.output_parsers import JsonOutputParser

from db.session import get_session
from db.database_schema import MessageDraft, Message, Profile, Communication
from db.database_schema import Client, Profile, EmailDraft, MessageDraft


load_dotenv()


LLM_DEFAULT = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)



class PersonalizedMessageOutput(BaseModel):
    subject: str =None
    body_markdown: str


class MessagePersonaliserAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
        self.session_factory = get_session
        self.parser = JsonOutputParser(pydantic_schema=PersonalizedMessageOutput)
        self.prompt = self._build_prompt()

    def _build_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", """
                You are a message personalisation assistant for professional short-form messages (like WhatsApp, LinkedIn, SMS).

                You will receive:
                - A base message draft
                - Client profile (name, company, interests, etc.)
                - Optional reviewer feedback

                Your job is to:
                1. Personalise the message:
                - Greet by name
                - Mention company or category if relevant
                - Add 1-2 interest-based hooks
                - Use preferred language or translate if needed
                - Mention the best time to connect if provided

                2. If feedback is present:
                - Respect it and revise the message without losing the core intent
                - Make the tone match expectations (e.g., softer, direct, fun, etc.)

                Keep the message concise, conversational, and under 75 words.

                Output strictly in this JSON format:
                {
                "subject": "",  // Leave blank if not applicable
                "body_markdown": "..."
                }

                No commentary. No formatting outside JSON.
                {format_instructions}
                """),
                            ("user", "{input_context}")
                        ])

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        draft_id = inputs["draft_id"]
        feedback_text = inputs.get("feedback", "")

        with self.session_factory() as session:
            draft = session.get(MessageDraft, draft_id)
            client = session.get(Client, draft.client_id)
            profile = session.query(Profile).filter_by(client_id=client.client_id).first()

        input_context = {
            "name": client.full_name,
            "company": client.company,
            "category": client.category,
            "interests": profile.interests.split(",") if profile.interests else [],
            "engagement_times": profile.engagement_times,
            "preferred_language": profile.preferred_language,
            "original_subject": "",
            "original_body": draft.message_text
        }

        if feedback_text:
            input_context["feedback"] = feedback_text

        formatted = self.prompt.format_prompt(
            input_context=json.dumps(input_context, ensure_ascii=False),
            format_instructions=self.parser.get_format_instructions()
        ).to_string()

        raw_output = self.llm.invoke(formatted)
        # parsed = self.parser.parse(raw.content)

        raw_content = raw_output.content.strip()

        
        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content

        try:
            parsed_dict = json.loads(cleaned)
            parsed = PersonalizedMessageOutput(**parsed_dict)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            
            parsed = PersonalizedMessageOutput(
                subject=getattr(draft, "subject", "") or "Subject",
                body_markdown=cleaned
            )

        return {
            "status": "personalised",
            "channel": "message",
            "subject": parsed.subject,
            "body_markdown": parsed.body_markdown
        }

    def invoke(self, input: Dict[str, Any], config=None) -> Dict[str, Any]:
        return self._call(input)

















