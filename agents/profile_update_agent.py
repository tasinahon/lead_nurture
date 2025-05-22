from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from db.session import get_session
from db.session import SessionLocal
from db.database_schema import Profile, Communication, ContextQuestion

from pydantic import BaseModel, Field
from typing import List, Dict, Any,Optional
import os, json

class UpdatedProfileSchema(BaseModel):
    summary: str | None = None           # allow missing
    interests: str | None = None         # CSV string you store
    full_text: str | None = None
    engagement_times: str | None = None  # ← now optional
    preferred_language: Optional[str] = None
    preferred_contact: Optional[str] = None

class ProfileUpdateAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.embed = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        self.parser = JsonOutputParser(pydantic_schema=UpdatedProfileSchema)
        self.prompt = self._build_prompt()
        self.session_factory = SessionLocal

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
                - engagement_times should be a short string like "Weekdays after 10 AM" or "Evenings" — NOT a list.
                - Include updated `preferred_language` and `preferred_contact` if they are mentioned or implied.
                - If unchanged, return the same values.
                - Provide `interests` as a **comma-separated string** based on old and new data.
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
            "recent_comms": [{"channel": c.channel, "text": c.content} for c in comms],
            "preferred_language": profile.preferred_language,
            "preferred_contact": profile.preferred_contact,
            "interests":profile.interests or ""

        }
        return json.dumps(context, ensure_ascii=False)[:15000]

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        client_id = inputs["client_id"]
        context_str = self._build_context(client_id)

        formatted = self.prompt.format_prompt(
            context=context_str,
            format_instructions=self.parser.get_format_instructions()
        ).to_string()

        raw_output = self.llm.invoke(formatted)
        raw_content = raw_output.content.strip()

        
        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content

        try:
            parsed_dict = json.loads(cleaned)
            if isinstance(parsed_dict.get("engagement_times"), list):
                parsed_dict["engagement_times"] = ", ".join(parsed_dict["engagement_times"])
            parsed = UpdatedProfileSchema(**parsed_dict)
            vector = self.embed.embed_query(parsed.full_text)
        except Exception as e:
            raise ValueError(f"Failed to parse model output: {e} | Raw: {cleaned[:300]}")

        with self.session_factory() as s:
    # delete old profile
            s.query(Profile).filter_by(client_id=client_id).delete()
            # insert new profile
            new_profile = Profile(
                client_id=client_id,
                summary=parsed.summary,
                full_text=parsed.full_text,
                interests=parsed.interests,
                engagement_times=parsed.engagement_times,
                personality_vector=json.dumps(vector),
                preferred_language=parsed.preferred_language or "English",
                preferred_contact=parsed.preferred_contact or "email"
            )
            s.add(new_profile)
            s.commit()
            s.refresh(new_profile)


        return {
            "status": "profile_updated",
            "client_id": client_id,
            "updated_summary": parsed.summary
        }

    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)
