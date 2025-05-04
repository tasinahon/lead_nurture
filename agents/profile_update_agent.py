from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from db.session import get_session
from db.database_schema import Profile, Communication, ContextQuestion

from pydantic import BaseModel, Field
from typing import List, Dict, Any
import os, json

class UpdatedProfileSchema(BaseModel):
    summary: str
    interests: List[str]
    engagement_times: str
    full_text: str

class ProfileUpdateAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.parser = JsonOutputParser(pydantic_schema=UpdatedProfileSchema)
        self.prompt = self._build_prompt()
        self.session_factory = get_session

    def _build_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", """
                You are an AI assistant responsible for **updating an existing client profile**.

                You are provided:
                1. The original profile summary and full persona text
                2. Newly submitted context questions (Q&A)
                3. Recent communication records

                 Your task:
                - Rewrite the profile `summary` with **new insights** added
                - Update the `interests` if new topics emerged
                - Suggest `engagement_times` based on tone/timing of recent conversations
                - Generate a new `full_text` for embeddings (combine old + new perspective)

                 Don't remove valuable original details unless outdated. Just **enhance** and **expand**.

                Return only valid JSON in the following format:
                {format_instructions}
                        """),
                            ("user", "{context}")
                ])

    def _build_context(self, client_id: int) -> str:
        with self.session_factory() as s:
            profile = s.query(Profile).filter_by(client_id=client_id).first()
            qna = s.query(ContextQuestion).filter_by(client_id=client_id).all()
            comms = s.query(Communication).filter_by(client_id=client_id).order_by(Communication.timestamp.desc()).limit(5).all()

        context = {
            "original_summary": profile.summary,
            "original_full_text": profile.full_text,
            "context_questions": [{"q": q.question, "a": q.answer} for q in qna if q.answer],
            "recent_comms": [{"channel": c.channel, "text": c.content} for c in comms]
        }
        return json.dumps(context, ensure_ascii=False)[:15000]

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        client_id = inputs["client_id"]
        context_str = self._build_context(client_id)

        formatted = self.prompt.format_prompt(
            context=context_str,
            format_instructions=self.parser.get_format_instructions()
        ).to_string()

        raw = self.llm.invoke(formatted)
        parsed = self.parser.parse(raw.content)

        with self.session_factory() as s:
            profile = s.query(Profile).filter_by(client_id=client_id).first()
            profile.summary = parsed.summary
            profile.full_text = parsed.full_text
            profile.interests = ",".join(parsed.interests)
            profile.engagement_times = parsed.engagement_times
            s.commit()
            s.refresh(profile)

        return {
            "status": "profile_updated",
            "client_id": client_id,
            "updated_summary": parsed.summary
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)
