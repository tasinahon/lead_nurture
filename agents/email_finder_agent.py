from pydantic import BaseModel
from langchain_core.tools import tool
import requests, os
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

class EmailOutput(BaseModel):
    email: str | None



@tool
def tavily_search(query: str) -> str:
    """Search the web using Tavily and return a combined string of content."""
    response = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}"},
        json={"query": query, "num_results": 5}
    )
    results = response.json().get("results", [])
    return "\n\n".join(f"{r['title']}\n{r['content']}" for r in results)




load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.2,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)


parser = JsonOutputParser(pydantic_schema=EmailOutput)


tools = [tavily_search]


agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)



import json

def clean_llm_json(raw_output: str):
    raw_content = raw_output.strip()

    
    if raw_content.startswith("```"):
        cleaned = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
    else:
        cleaned = raw_content

    if not cleaned.strip().startswith("{"):
        cleaned = "{" + cleaned.strip()
    if not cleaned.strip().endswith("}"):
        cleaned = cleaned.strip() + "}"

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"Failed to parse cleaned JSON: {e}")
        return {"email": None}




def find_email_via_agent(full_name: str, linkedin_url: str) -> str | None:

    question = f"""
You are an expert agent tasked with finding professional email addresses using web search.

Use the `tavily_search` tool to search for information about this person:
Name: {full_name}
LinkedIn: {linkedin_url}

After searching, extract the most relevant professional email address.

Return only in the following JSON format:
{{
  "email": "email@example.com"
}}

If no email found, return:
{{
  "email": null
}}
"""
    try:
        result = agent.run(question)
        parsed = clean_llm_json(result)
        print(parsed['email'])
        return parsed.get("email")
    except Exception as e:
        print(f"Email agent failed: {e}")
        return None

# # result = agent.run(question)
# # parsed = clean_llm_json(result)

# # print(parsed["email"])











