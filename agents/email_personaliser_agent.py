import os
import json
from datetime import datetime
from typing import Dict, Any, List

from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from db.session import get_session
from db.database_schema import Client, Profile, EmailDraft, MessageDraft

from pydantic import BaseModel


class PersonalizedOutput(BaseModel):
    subject: str
    body_markdown: str


class PersonaliserAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
        self.session_factory = get_session
        self.parser = JsonOutputParser(pydantic_schema=PersonalizedOutput)
        self.prompt = self._build_prompt()

    def _build_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", """
                You are a professional AI assistant for personalising and refining email/message drafts.

                You will receive:
                - A draft (subject + body)
                - Client profile
                - Optional feedback from a reviewer

                Your task:
                1. Personalise the draft using the client's profile:
                - Greet by name
                - Mention company/category if relevant
                - Use at least 1 interest hook
                - Include engagement_times suggestion if present
                - If language isn't English, translate the message

                2. If feedback is provided:
                - Respect the tone and intent
                - Improve clarity or rewrite sections as per suggestion
                - DO NOT alter core message unless requested

                3. Keep the result under **150 words** and make it feel human-written.

                Output strictly as JSON:
                {
                "subject": "...",
                "body_markdown": "..."
                }

                No commentary or formatting outside JSON.
                {format_instructions}
                """),
                            ("user", "{input_context}")
                        ])

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        draft_id = inputs["draft_id"]
        channel = inputs.get("channel", "email").lower()
        feedback_text = inputs.get("feedback", "")

        with self.session_factory() as session:
            draft_model = EmailDraft if channel == "email" else MessageDraft
            draft = session.get(draft_model, draft_id)
            client = session.get(Client, draft.client_id)
            profile = session.query(Profile).filter_by(client_id=client.client_id).first()

        input_context = {
            "name": client.full_name,
            "company": client.company,
            "category": client.category,
            "interests": profile.interests.split(",") if profile.interests else [],
            "engagement_times": profile.engagement_times,
            "preferred_language": profile.preferred_language,
            "original_subject": getattr(draft, "subject", ""),
            "original_body": draft.body_markdown if channel == "email" else draft.message_text,
        }

        if feedback_text:
            input_context["feedback"] = feedback_text

        formatted = self.prompt.format_prompt(
            input_context=json.dumps(input_context, ensure_ascii=False),
            format_instructions=self.parser.get_format_instructions()
        ).to_string()

        raw_output = self.llm.invoke(formatted)
        raw_content = raw_output.content.strip()

        # Remove triple backtick code block markers if present
        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content

        try:
            parsed_dict = json.loads(cleaned)
            parsed = PersonalizedOutput(**parsed_dict)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # Fallback: return raw content as body
            parsed = PersonalizedOutput(
                subject=getattr(draft, "subject", "") or "Subject",
                body_markdown=cleaned
            )

        return {
            "status": "personalised",
            "channel": channel,
            "subject": parsed.subject,
            "body_markdown": parsed.body_markdown
        }

    def invoke(self, input: Dict[str, Any], config=None) -> Dict[str, Any]:
        return self._call(input)
































