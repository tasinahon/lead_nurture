import json
import os
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from db.session import get_session
from db.database_schema import Profile, ScrapedData, ContextQuestion

from pydantic import BaseModel, Field

load_dotenv()

class ProfileSchema(BaseModel):
    summary: str = None
    interests: List[str] = []
    preferred_language: str = None
    preferred_contact: str = None
    engagement_times: str = None
    full_text: str = None

parser = JsonOutputParser(pydantic_schema=ProfileSchema)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant tasked with creating a detailed profile of a client based on scraped LinkedIn data, web searches, and Q&A context provided."),
    ("user", 
    """
    Using the following context, extract and generate a client profile.

    You must extract and strictly fill the following fields:

    1. **summary** (string): A 3-5 sentence description summarizing the client's background, professional activities, and personality traits based on the available data.

    2. **interests** (list of strings): A list of topics, industries, hobbies, or professional areas the client is interested in. These should be concise keywords.

    3. **preferred_language** (string): The primary language the client is most comfortable communicating in (e.g., "English", "Spanish"). If not available, assume "English".

    4. **preferred_contact** (string): The platform the client prefers for communication, based on hints from their activity or context (choose one: 'Email', 'WhatsApp', 'LinkedIn'). If unclear, guess reasonably.

    5. **engagement_times** (string): Suggest best times to engage the client based on behavior. Example: "Monday". If unknown, keep empty.

    6. **full_text** (string): A detailed paragraph (maximum 100 words, minimum 80 words) that expands on the client's professional background, communication style, and any inferred personal preferences. This is used for embedding generation, so be rich in content.

    ---
    {context}

    ---
    Strictly follow this JSON structure without any deviations. 
    Output must be a valid JSON object, not a string, without any extra quotes, characters, or explanations. 
    Your output should be **parseable directly as JSON**.
    Format:

    {format_instructions}

    Do not add any fields or explanations outside the JSON structure.
    """
    )
])

class ProfileBuilderAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        self.embed = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        self.session_factory = get_session

    def build_context(self, cid: int) -> str:
        with self.session_factory() as session:
            scraped: List[ScrapedData] = (
                session.query(ScrapedData)
                .filter_by(client_id=cid)
                .order_by(ScrapedData.scraped_at.desc())
                .limit(10)
                .all()
            )
            qna: List[ContextQuestion] = (
                session.query(ContextQuestion)
                .filter_by(client_id=cid)
                .all()
            )

        context = {
            "scraped_data": [json.loads(row.raw_json) for row in scraped],
            "context_qna": [{"q": qa.question, "a": qa.answer} for qa in qna if qa.answer],
        }

        return json.dumps(context, ensure_ascii=False)[:15000]

    def update_profile(self, cid: int, data: ProfileSchema, embedding: List[float]):
        with self.session_factory() as session:
            profile = session.query(Profile).filter_by(client_id=cid).one_or_none()
            if not profile:
                profile = Profile(client_id=cid)

            profile.summary = data.summary
            profile.interests = ",".join(data.interests)
            profile.personality_vector = json.dumps(embedding)
            profile.preferred_language = data.preferred_language
            profile.preferred_contact = data.preferred_contact
            profile.engagement_times = data.engagement_times

            session.add(profile)
            session.commit()
            session.refresh(profile)

            with open("agent.txt", "a", encoding="utf-8") as f:
                f.write(f"""
======== Profile Update ========
Client ID: {cid}
Summary: {data.summary}
Interests: {", ".join(data.interests)}
Preferred Language: {data.preferred_language}
Preferred Contact: {data.preferred_contact}
Engagement Times: {data.engagement_times}
Embedding Vector Length: {len(embedding)}
================================
""")

        return profile.profile_id

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cid = inputs["client_id"]
        context_json = self.build_context(cid)

        formatted_prompt = prompt.format_prompt(
            context=context_json,
            format_instructions=parser.get_format_instructions()
        ).to_string()

        raw_output = self.llm.invoke(formatted_prompt)
        parsed_dict = parser.parse(raw_output.content)
        parsed_output = ProfileSchema(**parsed_dict)

        embedding = self.embed.embed_query(parsed_output.full_text)
        prof_id = self.update_profile(cid, parsed_output, embedding)

        return {
            "status": "profile_updated",
            "client_id": cid,
            "profile_id": prof_id
        }

    def invoke(self, input: Dict[str, Any], config=None) -> Dict[str, Any]:
        return self._call(input)


