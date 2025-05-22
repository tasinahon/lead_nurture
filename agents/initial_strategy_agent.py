from typing import Dict, Any
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from datetime import datetime
from db.session import get_session
from db.session import SessionLocal
from db.database_schema import Profile,InitialStrategy,ContextQuestion
import os, json


class StrategyOutput(BaseModel):
    engagement_channel: str=None
    tone_style: str=None
    communication_frequency: str=None
    general_advice: str=None


class InitialStrategyAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.prompt = self._build_prompt()
        self.parser = JsonOutputParser(pydantic_schema=StrategyOutput)
        self.session_factory = SessionLocal

    def _build_prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", """
                You are an expert communication strategist helping to initiate a campaign for a new client.

                You will receive the client’s profile information based only on scraped online sources (like LinkedIn, websites). These may not be complete — your job is to make **best-effort strategic guesses**.

                Use this profile context:
                - Summary of their professional background and tone
                - Inferred interests
                - Preferred language and communication channel
                - Engagement timing hints (if any)
                - Full Text (detail info about client)
                - Contextual Q&A: additional background, goals, or communication expectations (when available)

                Your Goal:
                Generate an initial strategy recommendation for outreach — even if incomplete.

                Return this JSON structure:
                {{
                "engagement_channel": "Email | WhatsApp | LinkedIn | Unknown",
                "tone_style": "Formal | Friendly | Concise | Warm | Persuasive | ...",
                "communication_frequency": "1 per week | 1 every 3 days | Daily | ...",
                "general_advice": "Custom notes on how best to approach the client"
                }}

                Notes:
                - If platform preference is unknown, default to 'email'
                - If no engagement_times, guess based on industry or leave blank
                - Be polite but proactive. This is an **initial** strategy — it's okay to revise later.
                - Keep all values short and useful. Your output should be used by email/message generation agents.
                - Guess conservatively if info is missing.
                - Always use context_qna if available — it often has insights about tone, language, or timing.

                Return valid JSON only.
                {format_instructions}
                """),
                        ("user", "{input_context}")
                    ])




    

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        client_id = inputs["client_id"]

        
        with self.session_factory() as session:
            profile = session.query(Profile).filter_by(client_id=client_id).first()
            if not profile:
                raise ValueError("No profile found for client")
            qna = session.query(ContextQuestion).filter_by(client_id=client_id).all()

        
        input_context = json.dumps({
            "summary": profile.summary,
            "interests": profile.interests,
            "preferred_contact": profile.preferred_contact,
            "preferred_language": profile.preferred_language,
            "engagement_times": profile.engagement_times,
            "full_text": profile.full_text,
            "context_qna": [{"question": q.question, "answer": q.answer} for q in qna]
        }, ensure_ascii=False)

        
        formatted_prompt = self.prompt.format_prompt(
            input_context=input_context,
            format_instructions=self.parser.get_format_instructions()
        ).to_string()

        
        raw_output = self.llm.invoke(formatted_prompt)
        raw_content = raw_output.content.strip()

        
        if raw_content.startswith("```"):
            cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned = raw_content


        try:
    
            if not cleaned.strip().startswith("{"):
                cleaned = "{" + cleaned.strip()
            if not cleaned.strip().endswith("}"):
                cleaned = cleaned.strip() + "}"

            parsed_dict = json.loads(cleaned)
            parsed = StrategyOutput(**parsed_dict)
        except Exception as e:
            parsed = StrategyOutput(
                engagement_channel='email',
                tone_style='Formal',
                communication_frequency='1 per week',
                general_advice=f"[ParseError] {str(e)} | Raw: {cleaned[:200]}"
            )

        
        with self.session_factory() as session:
            # existing = session.query(InitialStrategy).filter_by(client_id=client_id).first()
            # if existing:
            #     session.delete(existing)
            #     session.commit() 
            session.query(InitialStrategy).filter_by(client_id=client_id).delete()
            session.commit()
            strategy = InitialStrategy(
                client_id=client_id,
                engagement_channel=parsed.engagement_channel or 'email',
                tone_style=parsed.tone_style,
                communication_frequency=parsed.communication_frequency,
                general_advice=parsed.general_advice,
                generated_at=datetime.utcnow()
            )
            session.add(strategy)
            session.commit()
            session.refresh(strategy)

        # Step 6: Return result
        return {
            "status": "strategy_ready",
            "client_id": client_id,
            "strategy_id": strategy.strategy_id,
            "engagement_channel": strategy.engagement_channel,
            "tone_style": strategy.tone_style,
            "communication_frequency": strategy.communication_frequency,
            "general_advice": strategy.general_advice
        }


    def invoke(self, input: Dict[str, Any], config=None):
        return self._call(input)
