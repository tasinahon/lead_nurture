import os, re, json, requests
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import tool
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_google_genai import ChatGoogleGenerativeAI

from db.session import get_session
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
        self._sf = get_session
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
            prof_response = requests.get(
                f"{RAPID_BASE}/get-profile-data-by-url",
                headers=headers,
                params={"url": linkedin_url},
            )
            if prof_response.ok:
                prof = prof_response.json()
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

                    with open("agent.txt", "a", encoding="utf-8") as f:
                        f.write(f"""
======== Scraped LinkedIn Profile ========
Client ID: {cid}
Scraped At: {now.isoformat()}
Full Name: {full_name}
Company: {company}
Extracted Summary: {json.dumps(enriched_profile, ensure_ascii=False, indent=2)}
==========================================
""")

        #  LinkedIn Posts 
        if username:
            posts_response = requests.get(
                f"{RAPID_BASE}/get-profile-posts",
                headers=headers,
                params={"username": username},
            )
            if posts_response.ok:
                posts = posts_response.json()
                filtered_posts = [
                    {
                        "text": post.get("text"),
                        "isBrandPartnership": post.get("isBrandPartnership"),
                        "postedDate": post.get("postedDate"),
                    }
                    for post in posts.get("data", [])
                ]

                if filtered_posts:
                    enriched_posts = self.enrich_posts_with_llm(filtered_posts, full_name, company)
                    self._store(cid, "linkedin_post", enriched_posts)

                    with open("agent.txt", "a", encoding="utf-8") as f:
                        f.write(f"""
======== Scraped LinkedIn Posts ========
Client ID: {cid}
Scraped At: {now.isoformat()}
Full Name: {full_name}
Company: {company}
Extracted Posts Insights: {json.dumps(enriched_posts, ensure_ascii=False, indent=2)}
=========================================
""")

        #  Web Search (Tavily) 
        if full_name and company:
            user_prompt = (
                f"You are a research assistant gathering strategic and insightful information about \"{full_name}\" "
                f"and the company \"{company}\". Use the web search tool to discover:\n\n"
                f"1. The company’s long-term strategy or business goals\n"
                f"2. Expansion plans, global moves, or investment efforts\n"
                f"3. Public or media-covered failures, scandals, or unmet goals\n"
                f"4. What the company is most known for, and what sets it apart in its sector\n"
                f"5. Notable leadership styles or decisions by {full_name} or other executives\n"
                f"6. Recent news, funding, acquisitions, or restructuring plans\n\n"
                f"Use focused search queries. Avoid general company summaries — dig into meaningful stories and developments."
            )
            web_snippets = self.agent.run(user_prompt)

            if isinstance(web_snippets, list) and len(web_snippets) > 0:
                self._store(cid, "web_search", web_snippets)

                with open("agent.txt", "a", encoding="utf-8") as f:
                    f.write(f"""
======== Web Search Insights ========
Client ID: {cid}
Scraped At: {now.isoformat()}
Full Name: {full_name}
Company: {company}
Web Search Results: {json.dumps(web_snippets, ensure_ascii=False, indent=2)}
======================================
""")

        return {"status": "scraped", "client_id": cid}

    def invoke(self, input: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
        return self._call(input)
