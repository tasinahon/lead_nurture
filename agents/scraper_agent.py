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
    """Enhanced LinkedIn scraper using BrightData API"""
    
    def __init__(self):
        self._sf = SessionLocal
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        
        # BrightData configuration
        self.brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
        self.dataset_id = os.getenv("BRIGHTDATA_DATASET_ID")
        self.brightdata_url = f"https://api.brightdata.com/datasets/v3/trigger"

    def get_dummy_linkedin_data(self, linkedin_url: str) -> Dict[str, Any]:
        """Generate realistic dummy LinkedIn data for testing purposes"""
        
        # Extract name from URL if possible, otherwise use default
        slug = extract_linkedin_slug(linkedin_url)
        
        # Sample realistic LinkedIn profiles based on common patterns
        dummy_profiles = {
            "shahrukhrydwan": {
                "full_name": "Shahrukh Rydwan",
                "headline": "Senior Software Engineer | Full-Stack Developer | React, Node.js, Python",
                "summary": "Passionate software engineer with 5+ years of experience building scalable web applications. Expert in React, Node.js, Python, and cloud technologies. Currently leading development team at a fintech startup.",
                "location": "San Francisco, CA",
                "industry": "Technology",
                "company": "TechFlow Solutions",
                "position": "Senior Software Engineer",
                "experience": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "TechFlow Solutions",
                        "duration": "2022 - Present",
                        "description": "Leading development of microservices architecture using Node.js and React. Improved system performance by 40% and reduced deployment time by 60%."
                    },
                    {
                        "title": "Software Developer",
                        "company": "StartupXYZ", 
                        "duration": "2020 - 2022",
                        "description": "Developed customer-facing web applications using React and Python. Collaborated with cross-functional teams to deliver features on time."
                    }
                ],
                "education": [
                    {
                        "degree": "Bachelor of Science in Computer Science",
                        "school": "University of California, Berkeley",
                        "year": "2020"
                    }
                ],
                "skills": ["JavaScript", "Python", "React", "Node.js", "AWS", "Docker", "MongoDB"],
                "connections": 500,
                "posts": [
                    {
                        "content": "Just deployed our new microservices architecture! The performance improvements are incredible. #TechLeadership #Microservices",
                        "date": "2024-03-15",
                        "likes": 45,
                        "comments": 8
                    },
                    {
                        "content": "Attending AWS re:Invent 2024. Excited to learn about the latest cloud technologies and networking with fellow developers! #AWS #CloudComputing",
                        "date": "2024-03-10", 
                        "likes": 32,
                        "comments": 5
                    }
                ]
            },
            "default": {
                "full_name": "Alex Johnson",
                "headline": "Marketing Director | Digital Strategy | Growth Hacking",
                "summary": "Results-driven marketing professional with 7+ years of experience in digital marketing, brand strategy, and growth optimization. Proven track record of increasing revenue by 150% through innovative campaigns.",
                "location": "New York, NY",
                "industry": "Marketing & Advertising", 
                "company": "GrowthCorp",
                "position": "Marketing Director",
                "experience": [
                    {
                        "title": "Marketing Director",
                        "company": "GrowthCorp",
                        "duration": "2021 - Present", 
                        "description": "Leading digital marketing strategy for B2B SaaS products. Increased lead generation by 200% and improved conversion rates by 45%."
                    }
                ],
                "education": [
                    {
                        "degree": "MBA in Marketing",
                        "school": "NYU Stern School of Business",
                        "year": "2019"
                    }
                ],
                "skills": ["Digital Marketing", "SEO/SEM", "Content Strategy", "Analytics", "Growth Hacking"],
                "connections": 850,
                "posts": [
                    {
                        "content": "The future of B2B marketing is personalization at scale. Our latest campaign achieved 3x higher engagement rates! #MarketingStrategy #B2B",
                        "date": "2024-03-12",
                        "likes": 67,
                        "comments": 12
                    }
                ]
            }
        }
        
        # Select appropriate profile or use default
        profile_key = slug if slug and slug in dummy_profiles else "default"
        profile_data = dummy_profiles[profile_key].copy()
        
        # Add metadata
        profile_data.update({
            "scraped_at": datetime.now().isoformat(),
            "source": "dummy_data",
            "linkedin_url": linkedin_url,
            "profile_id": slug or "unknown"
        })
        
        print(f"✅ Generated dummy LinkedIn data for: {profile_data['full_name']}")
        return profile_data



    def _store(self, cid: int, source: str, payload: Dict | List):
        """Store scraped data in database"""
        with self._sf() as s:
            s.add(ScrapedData(
                client_id=cid,
                source_type=source,
                raw_json=json.dumps(payload, ensure_ascii=False),
                scraped_at=datetime.utcnow(),
            ))
            s.commit()

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Main scraping logic using dummy data (BrightData temporarily disabled)"""
        cid = inputs["client_id"]
        
        with self._sf() as s:
            client: Client | None = s.get(Client, cid)
        if not client:
            return {"status": "error", "detail": f"Client {cid} not found"}
        
        linkedin_url = client.linkedin_url
        full_name = client.full_name
        company = client.company
        
        if not linkedin_url:
            return {"status": "error", "detail": "No LinkedIn URL provided"}
        
        try:
            print(f"🔍 Using dummy LinkedIn data for: {linkedin_url}")
            print("ℹ️  Note: BrightData temporarily disabled, using realistic dummy data")
            
            # Generate dummy LinkedIn data
            dummy_profile = self.get_dummy_linkedin_data(linkedin_url)
            
            # Store the dummy data
            self._store(cid, "dummy_linkedin", dummy_profile)
            
            # Enrich with LLM analysis
            enriched_data = self.enrich_profile_with_llm(
                dummy_profile, full_name, company
            )
            
            # Also enrich posts if available
            if dummy_profile.get("posts"):
                post_insights = self.enrich_posts_with_llm(
                    dummy_profile["posts"], full_name, company
                )
                enriched_data["post_insights"] = post_insights
            
            print(f"✅ Profile enrichment completed for: {dummy_profile['full_name']}")
            
            return {
                "status": "success",
                "client_id": cid,
                "profile_data": dummy_profile,
                "enriched_analysis": enriched_data,
                "message": "LinkedIn data processed successfully (using dummy data)",
                "data_source": "dummy"
            }
            
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
            return {
                "status": "error",
                "detail": f"Processing failed: {str(e)}"
            }

    def enrich_profile_with_llm(self, profile: Dict, full_name: str, company: str) -> Dict:
        """Analyze profile data using Google Gemini LLM with fallback to dummy data"""
        try:
            print(f"🧠 Analyzing profile with LLM for: {full_name}")
            
            # Try to use real LLM analysis first
            try:
                import google.generativeai as genai
                import os
                from dotenv import load_dotenv
                import time
                import json
                
                load_dotenv()
                api_key = os.getenv("GOOGLE_API_KEY")
                
                if not api_key:
                    print("⚠️ Google API key not found, using fallback dummy data")
                    return self._get_dummy_profile_insights(profile, full_name, company)
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Create analysis prompt
                prompt = f"""
                Analyze this LinkedIn profile data for {full_name} at {company} and provide insights for sales/marketing outreach:
                
                Profile: {json.dumps(profile, indent=2)}
                
                Please analyze and return ONLY a JSON object (no markdown) with these fields:
                - personality_tone: Their communication style and personality
                - working_habits: Their likely work patterns and preferences  
                - interests: Array of their professional interests
                - approach_suggestions: How to best approach them
                - career_highlights: Key aspects of their career
                - pain_points: Potential business challenges they face
                - engagement_topics: Topics that would interest them
                
                Return only valid JSON.
                """
                
                # Add small delay to avoid rate limits
                time.sleep(1)
                
                response = model.generate_content(prompt)
                
                # Parse LLM response
                try:
                    insights = json.loads(response.text.strip())
                    insights["analysis_source"] = "gemini_llm"
                    insights["analyzed_at"] = datetime.now().isoformat()
                    print(f"✅ LLM analysis completed for {full_name}")
                    return insights
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️ Could not parse LLM response as JSON: {e}")
                    return self._get_dummy_profile_insights(profile, full_name, company)
                    
            except Exception as llm_error:
                print(f"⚠️ LLM analysis failed: {llm_error}")
                if "quota" in str(llm_error).lower() or "429" in str(llm_error):
                    print("🚨 API quota exceeded, using fallback dummy data")
                return self._get_dummy_profile_insights(profile, full_name, company)
                
        except Exception as e:
            print(f"❌ Profile enrichment failed: {str(e)}")
            return self._get_dummy_profile_insights(profile, full_name, company)
    
    def _get_dummy_profile_insights(self, profile: Dict, full_name: str, company: str) -> Dict:
        """Fallback dummy insights when LLM is unavailable"""
        current_position = profile.get('current_position', 'Professional')
        
        # Create role-specific insights
        if 'engineer' in current_position.lower() or 'developer' in current_position.lower():
            return {
                "personality_tone": "Technical and analytical, prefers data-driven discussions",
                "working_habits": "Likely works flexible hours, responsive to technical solutions",
                "interests": ["Software architecture", "Code optimization", "New technologies", "Problem-solving"],
                "approach_suggestions": "Lead with technical benefits, include concrete examples and case studies",
                "career_highlights": f"Experienced {current_position} with strong technical background",
                "pain_points": ["Technical debt", "Scalability challenges", "Integration complexity"],
                "engagement_topics": ["Tech trends", "Development tools", "System architecture"],
                "analysis_source": "dummy_fallback",
                "analyzed_at": datetime.now().isoformat()
            }
        elif 'manager' in current_position.lower() or 'director' in current_position.lower():
            return {
                "personality_tone": "Strategic and results-focused, values efficiency and ROI",
                "working_habits": "Business hours oriented, prefers structured communication",
                "interests": ["Team productivity", "Business growth", "Strategic planning", "Process optimization"],
                "approach_suggestions": "Focus on business impact and ROI, provide executive-level insights",
                "career_highlights": f"Leadership role as {current_position} with management experience",
                "pain_points": ["Team scalability", "Budget optimization", "Strategic alignment"],
                "engagement_topics": ["Leadership strategies", "Business growth", "Team management"],
                "analysis_source": "dummy_fallback",
                "analyzed_at": datetime.now().isoformat()
            }
        else:
            return {
                "personality_tone": "Professional and business-focused, values practical solutions",
                "working_habits": "Standard business hours, prefers structured communication",
                "interests": ["Business efficiency", "Industry trends", "Professional development"],
                "approach_suggestions": "Professional tone with clear value proposition",
                "career_highlights": f"Experienced {current_position} at {company}",
                "pain_points": ["Process efficiency", "Market competition", "Growth challenges"],
                "engagement_topics": ["Industry insights", "Business solutions", "Professional growth"],
                "analysis_source": "dummy_fallback", 
                "analyzed_at": datetime.now().isoformat()
            }

    def enrich_posts_with_llm(self, posts: List[Dict], full_name: str, company: str) -> Dict:
        """Analyze LinkedIn posts using Gemini LLM with fallback to dummy analysis"""
        try:
            print(f"📝 Analyzing {len(posts)} posts for {full_name}")
            
            # Try LLM analysis first
            try:
                import google.generativeai as genai
                import os
                import time
                import json
                from dotenv import load_dotenv
                
                load_dotenv()
                api_key = os.getenv("GOOGLE_API_KEY")
                
                if not api_key or len(posts) == 0:
                    print("⚠️ No API key or no posts, using fallback analysis")
                    return self._get_dummy_post_insights(posts, full_name, company)
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Create analysis prompt
                posts_text = json.dumps(posts, indent=2)
                prompt = f"""
                Analyze these LinkedIn posts from {full_name} at {company} for sales/marketing insights:
                
                Posts: {posts_text}
                
                Please analyze and return ONLY a JSON object with:
                - current_focus: What they're currently focused on professionally
                - passion_topics: Array of topics they're passionate about
                - communication_style: How they communicate on LinkedIn
                - conversation_starters: Array of 2-3 conversation starters based on their posts
                - posting_frequency: How often they post (estimate)
                - engagement_level: Their typical engagement with others
                
                Return only valid JSON.
                """
                
                # Add delay for rate limiting
                time.sleep(1)
                
                response = model.generate_content(prompt)
                
                try:
                    insights = json.loads(response.text.strip())
                    insights["analysis_source"] = "gemini_llm"
                    insights["analyzed_at"] = datetime.now().isoformat()
                    print(f"✅ Post analysis completed for {full_name}")
                    return insights
                    
                except json.JSONDecodeError:
                    print("⚠️ Could not parse LLM response, using fallback")
                    return self._get_dummy_post_insights(posts, full_name, company)
                    
            except Exception as llm_error:
                print(f"⚠️ LLM post analysis failed: {llm_error}")
                if "quota" in str(llm_error).lower() or "429" in str(llm_error):
                    print("� API quota exceeded for posts, using fallback")
                return self._get_dummy_post_insights(posts, full_name, company)
                
        except Exception as e:
            print(f"❌ Post analysis failed: {str(e)}")
            return self._get_dummy_post_insights(posts, full_name, company)
    
    def _get_dummy_post_insights(self, posts: List[Dict], full_name: str, company: str) -> Dict:
        """Fallback dummy post analysis"""
        if not posts:
            return {
                "current_focus": "Professional development and industry insights",
                "passion_topics": ["Business growth", "Industry trends", "Professional networking"],
                "communication_style": "Professional and insightful",
                "conversation_starters": [
                    f"I'd love to connect and discuss industry trends",
                    f"Your work at {company} sounds interesting"
                ],
                "posting_frequency": "Occasional",
                "engagement_level": "Moderate",
                "analysis_source": "dummy_fallback",
                "analyzed_at": datetime.now().isoformat()
            }
        
        # Analyze post content for patterns
        post_contents = [post.get('content', '') for post in posts]
        all_content = ' '.join(post_contents).lower()
        
        # Determine focus based on keywords in posts
        if 'tech' in all_content or 'code' in all_content or 'development' in all_content:
            current_focus = "Technology and software development"
            passion_topics = ["Software engineering", "Tech trends", "Development tools", "Innovation"]
            communication_style = "Technical and informative, shares expertise and insights"
        elif 'leadership' in all_content or 'team' in all_content or 'management' in all_content:
            current_focus = "Leadership and team management"
            passion_topics = ["Team building", "Leadership strategies", "Business growth", "Organizational culture"]
            communication_style = "Inspirational and strategic, focuses on business insights"
        elif 'marketing' in all_content or 'brand' in all_content or 'customer' in all_content:
            current_focus = "Marketing and customer engagement"
            passion_topics = ["Brand building", "Customer experience", "Digital marketing", "Growth strategies"]
            communication_style = "Engaging and creative, emphasizes results and metrics"
        else:
            current_focus = "Professional development and industry insights"
            passion_topics = ["Business efficiency", "Industry trends", "Professional growth", "Networking"]
            communication_style = "Professional and insightful, shares valuable industry knowledge"
        
        # Generate conversation starters based on posts
        conversation_starters = []
        for post in posts[:2]:  # Use first 2 posts
            content = post.get('content', '')
            if content:
                if len(content) > 50:
                    starter = f"I saw your recent post about {content[:50]}... interesting perspective!"
                else:
                    starter = f"Your recent post about {content} caught my attention"
                conversation_starters.append(starter)
        
        if not conversation_starters:
            conversation_starters = [
                f"I noticed your recent activity on LinkedIn and would love to connect",
                f"Your expertise at {company} is impressive - would like to discuss potential collaboration"
            ]
        
        return {
            "current_focus": current_focus,
            "passion_topics": passion_topics,
            "communication_style": communication_style,
            "conversation_starters": conversation_starters,
            "posting_frequency": "Regular" if len(posts) > 3 else "Occasional", 
            "engagement_level": "Active" if any(post.get('likes', 0) > 20 for post in posts) else "Moderate",
            "analysis_source": "dummy_fallback",
            "analyzed_at": datetime.now().isoformat()
        }

    def invoke(self, input: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
        return self._call(input)