import os, re, json, requests
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import time

from dotenv import load_dotenv
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import tool
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_google_genai import ChatGoogleGenerativeAI

from db.session import get_session
from db.session import SessionLocal
from db.database_schema import Client, ScrapedData

load_dotenv()

RAPID_BASE = "https://linkedin-api8.p.rapidapi.com"
headers = {
    "X-Rapidapi-Key": os.getenv("RAPIDAPI_KEY"),
    "X-Rapidapi-Host": os.getenv("RAPIDAPI_HOST", "linkedin-api8.p.rapidapi.com"),
}


@tool
def tavily_search(query: str) -> List[Dict]:
    """Search the web using Tavily API and return relevant snippets."""
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {os.getenv('TAVILY_API_KEY', '')}"},
            json={"query": query, "max_results": 4, "include_answer": False},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as exc:
        return [{"query": query, "error": str(exc)}]


def extract_linkedin_slug(linkedin_url: str) -> Optional[str]:
    if not linkedin_url:
        return None
    path = urlparse(linkedin_url).path.rstrip("/")
    m = re.search(r"/(?:in|pub|company)/([^/?]+)$", path, re.I)
    return m.group(1) if m else None


class ScraperAgent(Runnable):
    def __init__(self):
        self._sf = SessionLocal
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        self.agent = initialize_agent(
            tools=[tavily_search],
            llm=self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,  
            verbose=False,
        )

    def _store(self, cid: int, source: str, payload: Dict | List):
        with self._sf() as s:
            s.add(ScrapedData(
                client_id=cid,
                source_type=source,
                raw_json=json.dumps(payload, ensure_ascii=False),
                scraped_at=datetime.utcnow(),
            ))
            s.commit()

    def enrich_profile_with_llm(self, profile: Dict, full_name: str, company: str) -> Dict:
        prompt = (
            f"You are analyzing a LinkedIn profile of '{full_name}', working at '{company}'. "
            f"Here is the structured profile data:\n\n{json.dumps(profile, indent=2)}\n\n"
            f"From this, extract:\n"
            f"1. Personality or communication tone\n"
            f"2. Likely working habits or available hours\n"
            f"3. Professional interests or focus areas\n"
            f"4. Suggestions on how to best approach this person via email\n"
            f"5. Anything noteworthy from their career summary or roles\n\n"
            f"Return a concise JSON summary with these fields."
        )
        response = self.llm.invoke(prompt)
        raw_content = response.content.strip()

        if raw_content.startswith("```") and raw_content.endswith("```"):
            cleaned_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned_content = raw_content

        return json.loads(cleaned_content)

    def enrich_posts_with_llm(self, posts: List[Dict], full_name: str, company: str) -> Dict:
        prompt = (
            f"You are analyzing LinkedIn posts by or about '{full_name}' at '{company}'.\n"
            f"Here are the posts:\n\n{json.dumps(posts, indent=2)}\n\n"
            f"From this, extract:\n"
            f"1. Any visible company campaigns, launches, or partnerships\n"
            f"2. Clues about the company culture or employee sentiment\n"
            f"3. Topics that {full_name} or the company care about\n"
            f"4. Suggestions for what kind of outreach email would be timely or valuable now\n\n"
            f"Return a JSON with extracted insights and a short communication strategy."
        )
        response = self.llm.invoke(prompt)
        raw_content = response.content.strip()

        if raw_content.startswith("```") and raw_content.endswith("```"):
            cleaned_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]
        else:
            cleaned_content = raw_content

        return json.loads(cleaned_content)

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cid = inputs["client_id"]

        with self._sf() as s:
            client: Client | None = s.get(Client, cid)
        if not client:
            return {"status": "error", "detail": f"Client {cid} not found"}

        linkedin_url = client.linkedin_url
        username = extract_linkedin_slug(linkedin_url)
        full_name = client.full_name
        company = client.company
        now = datetime.utcnow()

       
        if linkedin_url:
            print("yes----------------------------------------")
            prof_response = requests.get(
                f"{RAPID_BASE}/get-profile-data-by-url",
                headers=headers,
                params={"url": linkedin_url},
            )
            # time.sleep(1.5)
            print(prof_response)
            print(headers)
            if prof_response.status_code == 200:
                prof = prof_response.json()
                print(prof.get("summary"))
                filtered_prof = {
                    "summary": prof.get("summary"),
                    "headline": prof.get("headline"),
                    "languages": prof.get("languages"),
                    "position": prof.get("position"),
                    "projects": prof.get("projects"),
                }

                if filtered_prof:
                    enriched_profile = self.enrich_profile_with_llm(filtered_prof, full_name, company)
                    self._store(cid, "linkedin_profile", enriched_profile)

                    

        #  LinkedIn Posts 
        if username:
            posts_response = requests.get(
                f"{RAPID_BASE}/get-profile-posts",
                headers=headers,
                params={"username": username},
            )
            if posts_response.ok:
                posts = posts_response.json()
                print("posts-------------------")
                print(posts)
                filtered_posts = [
                    {
                        "text": post.get("text"),
                        "isBrandPartnership": post.get("isBrandPartnership"),
                        "postedDate": post.get("postedDate"),
                    }
                    for post in posts.get("data", [])
                ]
                print(filtered_posts)

                if filtered_posts:
                    enriched_posts = self.enrich_posts_with_llm(filtered_posts, full_name, company)
                    self._store(cid, "linkedin_post", enriched_posts)

                    

        #  Web Search (Tavily) 
        # if full_name and company:
        #     user_prompt = (
        #         f"You are a research assistant gathering strategic and insightful information about \"{full_name}\" "
        #         f"and the company \"{company}\". Use the web search tool to discover:\n\n"
        #         f"1. The company’s long-term strategy or business goals\n"
        #         f"2. Expansion plans, global moves, or investment efforts\n"
        #         f"3. Public or media-covered failures, scandals, or unmet goals\n"
        #         f"4. What the company is most known for, and what sets it apart in its sector\n"
        #         f"5. Notable leadership styles or decisions by {full_name} or other executives\n"
        #         f"6. Recent news, funding, acquisitions, or restructuring plans\n\n"
        #         f"Use focused search queries. Avoid general company summaries — dig into meaningful stories and developments."
        #     )
        #     web_snippets = self.agent.run(user_prompt)

        #     if web_snippets:
        #         self._store(cid, "web_search", {"summary": web_snippets})

                #  Web Search (Tavily + Gemini summary)
        # if full_name:
        #     search_queries = [
        #         f'"{full_name}" leadership style OR management philosophy',
        #         f'"{full_name}" career history OR professional background',
        #         f'"{full_name}" recent interview OR keynote speech',
        #         f'"{full_name}" industry opinion OR thought leadership',
        #         f'"{full_name}" achievements OR awards OR recognitions',
        #         f'"{full_name}" controversies OR public criticism',
        #         f'"{full_name}" future plans OR vision statements',
        #     ]
        # if company:
        #     search_queries += [
        #         f'"{full_name}" role at "{company}"',
        #         f'"{full_name}" impact on "{company}" performance',
        #     ]



        #     aggregated_results = []
        #     for query in search_queries:
        #         result = tavily_search(query)
        #         aggregated_results.append({
        #             "query": query,
        #             "results": result,
        #         })

        #     # Step: Summarize via Gemini LLM
        #     summary_prompt = (
        #         f"You are an AI research assistant analyzing web search results about the individual \"{full_name}\" "
        #         f"and optionally their association with the company \"{company}\".\n\n"
        #         f"Here are the search queries and their results:\n\n"
        #         f"{json.dumps(aggregated_results, indent=2)}\n\n"
        #         f"Summarize the most relevant insights under the following structured headings:\n"
        #         f"1. Professional background and career history\n"
        #         f"2. Leadership style and management approach\n"
        #         f"3. Public interviews, speeches, or thought leadership\n"
        #         f"4. Awards, recognitions, or notable achievements\n"
        #         f"5. Controversies or public criticism (if any)\n"
        #         f"6. Role and influence at {company} (if applicable)\n"
        #         f"7. Future plans or stated personal/professional vision\n\n"
        #         f"Return the result as **concise, structured JSON**, with keys matching the headings."
        #     )

        #     try:
        #         summary_response = self.llm.invoke(summary_prompt)
        #         summary_cleaned = summary_response.content.strip()
        #         if summary_cleaned.startswith("```"):
        #             summary_cleaned = summary_cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
        #         summary_json = json.loads(summary_cleaned)
        #     except Exception as e:
        #         summary_json = {"error": f"Failed to summarize: {str(e)}", "raw": summary_cleaned[:1000]}

        #     # Step: Store both raw and summarized results
        #     self._store(cid, "web_search", {
        #         "raw_queries": search_queries,
        #         "results": aggregated_results,
        #         "summary": summary_json,
        #     })



               

        return {"status": "scraped", "client_id": cid}

    def invoke(self, input: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
        return self._call(input)
