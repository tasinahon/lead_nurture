"""
Initial Approach Strategy Agent

This agent generates follow-up strategies for clients who didn't respond to initial introductory emails.
It creates personalized follow-up approaches based on client profile, original email context, and 
business intelligence to re-engage prospects with different messaging angles.

Key Features:
- Analyzes why initial email may not have resonated
- Creates alternative value propositions and messaging angles
- Generates follow-up email strategies with different approaches
- Reuses existing strategy logic but tailored for "no response" scenarios
- Provides recommendations for timing and frequency of follow-ups
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InitialApproachStrategyAgent:
    """
    Agent for creating follow-up strategies when initial introductory emails don't receive responses
    """
    
    def __init__(self):
        self.agent_name = "InitialApproachStrategyAgent"
        logger.info(f"🎯 {self.agent_name} initialized")
    
    def create_followup_strategy(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a comprehensive follow-up strategy for clients who didn't respond to initial emails
        
        Args:
            email_data: Dictionary containing original email context and client information
            
        Returns:
            Dictionary containing follow-up strategy with different messaging approaches
        """
        
        try:
            logger.info(f"🎨 Creating follow-up strategy for client {email_data['client_name']}")
            
            # Analyze the original context
            original_analysis = self._analyze_original_approach(email_data)
            
            # Generate alternative value propositions
            alternative_approaches = self._generate_alternative_approaches(email_data, original_analysis)
            
            # Create follow-up campaign strategy
            followup_strategy = self._create_followup_campaign_strategy(
                email_data, 
                original_analysis, 
                alternative_approaches
            )
            
            # Add timing and frequency recommendations
            timing_strategy = self._create_timing_strategy(email_data)
            followup_strategy.update(timing_strategy)
            
            logger.info(f"✅ Follow-up strategy created for {email_data['client_name']}")
            
            return {
                "status": "strategy_created",
                "client_id": email_data["client_id"],
                "original_email_context": email_data.get("original_context", {}),
                "strategy": followup_strategy,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating follow-up strategy: {e}")
            return {
                "status": "error",
                "error": str(e),
                "client_id": email_data.get("client_id")
            }
    
    def _analyze_original_approach(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the original introductory email approach to understand potential gaps
        """
        
        original_context = email_data.get("original_context", {})
        
        # Analyze what the original approach focused on
        original_focus = {
            "product_services": original_context.get("product_services", ""),
            "client_type": original_context.get("client_type", ""),
            "communication_method": original_context.get("communication_method", "email")
        }
        
        # Identify potential reasons for no response
        potential_gaps = self._identify_potential_gaps(email_data, original_focus)
        
        return {
            "original_focus": original_focus,
            "potential_gaps": potential_gaps,
            "client_profile": {
                "company": email_data.get("client_data", {}).get("company", ""),
                "industry": self._infer_industry(email_data.get("client_data", {})),
                "company_size": self._estimate_company_size(email_data.get("client_data", {}))
            }
        }
    
    def _identify_potential_gaps(self, email_data: Dict[str, Any], original_focus: Dict[str, Any]) -> List[str]:
        """
        Identify potential reasons why the original email didn't get a response
        """
        
        gaps = []
        
        # Check if original message was too generic
        if not original_focus.get("product_services") or len(original_focus.get("product_services", "")) < 20:
            gaps.append("message_too_generic")
        
        # Check if value proposition wasn't clear
        gaps.append("unclear_value_proposition")
        
        # Check if timing might be off
        gaps.append("timing_mismatch")
        
        # Check if wrong decision maker
        gaps.append("wrong_decision_maker")
        
        # Check if no social proof provided
        gaps.append("lack_social_proof")
        
        return gaps
    
    def _generate_alternative_approaches(self, email_data: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate alternative messaging approaches based on analysis
        """
        
        client_data = email_data.get("client_data", {})
        potential_gaps = analysis.get("potential_gaps", [])
        
        approaches = []
        
        # Approach 1: Value-focused with specific ROI
        approaches.append({
            "approach_name": "value_roi_focused",
            "angle": "specific_roi",
            "subject_template": "Quick question about {company}'s {business_area}",
            "opening": "problem_identification", 
            "value_prop": "quantified_benefits",
            "call_to_action": "low_commitment_offer",
            "tone": "consultative_professional"
        })
        
        # Approach 2: Social proof and case studies
        approaches.append({
            "approach_name": "social_proof_focused", 
            "angle": "success_stories",
            "subject_template": "How {similar_company} achieved {specific_result}",
            "opening": "success_story",
            "value_prop": "peer_validation",
            "call_to_action": "case_study_offer",
            "tone": "confident_informative"
        })
        
        # Approach 3: Industry insight and thought leadership
        approaches.append({
            "approach_name": "insight_focused",
            "angle": "industry_trends",
            "subject_template": "New {industry} regulation affecting {company}?",
            "opening": "industry_insight",
            "value_prop": "expertise_positioning", 
            "call_to_action": "insight_sharing",
            "tone": "advisory_expert"
        })
        
        # Approach 4: Problem-solution focused
        approaches.append({
            "approach_name": "problem_solution_focused",
            "angle": "pain_point_resolution",
            "subject_template": "Solving {specific_problem} at {company}",
            "opening": "problem_agitation",
            "value_prop": "solution_demonstration",
            "call_to_action": "demo_offer",
            "tone": "solution_oriented"
        })
        
        # Approach 5: Relationship building
        approaches.append({
            "approach_name": "relationship_building",
            "angle": "connection_first",
            "subject_template": "Introduction - {sender_name} from {sender_company}",
            "opening": "personal_connection",
            "value_prop": "partnership_opportunity",
            "call_to_action": "informal_conversation",
            "tone": "warm_personal"
        })
        
        return approaches
    
    def _create_followup_campaign_strategy(self, email_data: Dict[str, Any], analysis: Dict[str, Any], approaches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a comprehensive follow-up campaign strategy
        """
        
        # Select the best approaches for this specific client
        selected_approaches = self._select_best_approaches(email_data, analysis, approaches)
        
        # Create a multi-touch campaign sequence
        campaign_sequence = self._create_campaign_sequence(selected_approaches, email_data)
        
        return {
            "campaign_type": "no_reply_followup",
            "total_touches": len(campaign_sequence),
            "campaign_duration_days": self._calculate_campaign_duration(len(campaign_sequence)),
            "selected_approaches": selected_approaches,
            "campaign_sequence": campaign_sequence,
            "personalization_data": self._extract_personalization_data(email_data),
            "success_metrics": {
                "primary_goal": "response_generation", 
                "secondary_goals": ["engagement", "brand_awareness"],
                "target_response_rate": "15%"  # Higher than cold outreach due to previous touch
            }
        }
    
    def _select_best_approaches(self, email_data: Dict[str, Any], analysis: Dict[str, Any], approaches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select the most appropriate approaches for this specific client
        """
        
        client_data = email_data.get("client_data", {})
        company_size = analysis.get("client_profile", {}).get("company_size", "small")
        industry = analysis.get("client_profile", {}).get("industry", "general")
        
        selected = []
        
        # Always start with value/ROI focused approach
        selected.append(approaches[0])  # value_roi_focused
        
        # Add social proof if company is medium/large (more risk-averse)
        if company_size in ["medium", "large"]:
            selected.append(approaches[1])  # social_proof_focused
        
        # Add industry insight approach
        selected.append(approaches[2])  # insight_focused
        
        # Add problem-solution for business clients
        if email_data.get("original_context", {}).get("client_type") == "business":
            selected.append(approaches[3])  # problem_solution_focused
        
        # Limit to 3-4 approaches to avoid being too aggressive
        return selected[:4]
    
    def _create_campaign_sequence(self, approaches: List[Dict[str, Any]], email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create the actual sequence of follow-up emails
        """
        
        sequence = []
        
        # Space out the emails with appropriate timing
        day_intervals = [3, 7, 14]  # 3 days, 1 week, 2 weeks after no reply detection
        
        for i, approach in enumerate(approaches[:3]):  # Max 3 follow-ups
            sequence.append({
                "email_number": i + 1,
                "day": day_intervals[i] if i < len(day_intervals) else day_intervals[-1] + (7 * (i - len(day_intervals) + 1)),
                "approach": approach,
                "subject_personalization": self._get_subject_personalization(email_data, approach),
                "content_personalization": self._get_content_personalization(email_data, approach),
                "priority": "high" if i == 0 else "medium"
            })
        
        return sequence
    
    def _create_timing_strategy(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create timing recommendations for the follow-up campaign
        """
        
        client_timezone = email_data.get("original_context", {}).get("timezone", "UTC")
        
        return {
            "send_timing": {
                "preferred_days": ["Tuesday", "Wednesday", "Thursday"],  # Best response days
                "preferred_hours": [9, 10, 14, 15],  # 9-10 AM, 2-3 PM
                "client_timezone": client_timezone,
                "avoid_days": ["Monday", "Friday"],  # Avoid start/end of week
                "avoid_hours": [12, 13, 17, 18, 19]  # Avoid lunch and after hours
            },
            "follow_up_intervals": {
                "first_followup": 3,   # days after no-reply detection
                "second_followup": 7,  # days after first
                "third_followup": 14,  # days after second
                "max_followups": 3
            }
        }
    
    def _extract_personalization_data(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data for personalizing follow-up emails using enhanced client data
        """
        
        client_data = email_data.get("client_data", {})
        original_context = email_data.get("original_context", {})
        
        # Use enhanced client data if available
        industry = client_data.get("industry") or original_context.get("industry") or self._infer_industry(client_data)
        job_title = client_data.get("job_title", "Professional")
        interests = client_data.get("interests", [])
        business_area = original_context.get("business_area", self._infer_business_area(email_data))
        
        # Handle company name - extract from profile if not available in client data
        company_name = client_data.get("company", "").strip()
        if not company_name:
            # Try to extract company from profile summary
            summary = client_data.get("summary", "")
            if "fintech startup" in summary.lower():
                company_name = f"{client_data.get('full_name', 'Your')} Company"
            elif "startup" in summary.lower():
                company_name = f"{client_data.get('full_name', 'Your')} Company" 
            elif summary and ("at " in summary.lower() or "company" in summary.lower()):
                # Try to extract company name from summary
                company_name = self._extract_company_from_summary(summary)
            else:
                company_name = f"{client_data.get('full_name', 'Your')} organization"
        
        return {
            "client_name": client_data.get("full_name", ""),
            "company_name": company_name,
            "company_website": client_data.get("company_website", ""),
            "linkedin_profile": client_data.get("linkedin_url", ""),
            "industry": industry,
            "job_title": job_title,
            "interests": interests,
            "business_area": business_area,
            "client_summary": client_data.get("summary", ""),
            "original_product_services": original_context.get("product_services", ""),
            "client_timezone": original_context.get("timezone", "UTC"),
            "preferred_language": original_context.get("preferred_language", "English"),
            # Add context for better personalization
            "main_problem": self._get_relevant_problem_for_profile(industry, business_area, interests),
            "value_proposition": self._get_relevant_value_prop_for_profile(industry, business_area, job_title)
        }
    
    def _get_subject_personalization(self, email_data: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get personalization data for email subjects
        """
        
        client_data = email_data.get("client_data", {})
        
        return {
            "company": client_data.get("company", "your company"),
            "client_name": client_data.get("full_name", ""),
            "industry": self._infer_industry(client_data),
            "business_area": self._infer_business_area(email_data),
            "specific_problem": self._infer_main_problem(email_data),
            "sender_name": "Your Business Partner",  # TODO: Get from user profile
            "sender_company": "Our Company"  # TODO: Get from user profile
        }
    
    def _get_content_personalization(self, email_data: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get personalization data for email content
        """
        
        return {
            "value_proposition": self._generate_value_proposition(email_data, approach),
            "social_proof": self._generate_social_proof(email_data, approach),
            "industry_insights": self._generate_industry_insights(email_data),
            "call_to_action": self._generate_call_to_action(approach),
            "personalized_opening": self._generate_personalized_opening(email_data, approach)
        }
    
    # Helper methods for data inference and generation
    def _infer_industry(self, client_data: Dict[str, Any]) -> str:
        """Infer industry from company name and website"""
        company = client_data.get("company", "").lower()
        website = client_data.get("company_website", "").lower()
        
        # Simple industry inference based on keywords
        if any(word in company or word in website for word in ["tech", "software", "app", "digital"]):
            return "technology"
        elif any(word in company or word in website for word in ["health", "medical", "pharma"]):
            return "healthcare"
        elif any(word in company or word in website for word in ["finance", "bank", "invest"]):
            return "finance"
        else:
            return "business_services"
    
    def _estimate_company_size(self, client_data: Dict[str, Any]) -> str:
        """Estimate company size based on available data"""
        # Simple heuristic - in real implementation could use external APIs
        company = client_data.get("company", "")
        if len(company) < 10:
            return "small"
        elif len(company) < 20:
            return "medium" 
        else:
            return "large"
    
    def _infer_business_area(self, email_data: Dict[str, Any]) -> str:
        """Infer main business area to focus follow-up on"""
        product_services = email_data.get("original_context", {}).get("product_services", "")
        
        if "sales" in product_services.lower():
            return "sales operations"
        elif "marketing" in product_services.lower():
            return "marketing strategy"
        elif "operations" in product_services.lower():
            return "operational efficiency"
        else:
            return "business growth"
    
    def _infer_main_problem(self, email_data: Dict[str, Any]) -> str:
        """Infer the main problem our solution addresses"""
        business_area = self._infer_business_area(email_data)
        
        problem_map = {
            "sales operations": "low conversion rates",
            "marketing strategy": "lead generation challenges",
            "operational efficiency": "process bottlenecks",
            "business growth": "scaling limitations"
        }
        
        return problem_map.get(business_area, "efficiency challenges")
    
    def _calculate_campaign_duration(self, num_touches: int) -> int:
        """Calculate total campaign duration in days"""
        if num_touches <= 1:
            return 7
        elif num_touches == 2:
            return 14
        elif num_touches == 3:
            return 21
        else:
            return 30
    
    def _generate_value_proposition(self, email_data: Dict[str, Any], approach: Dict[str, Any]) -> str:
        """Generate specific value proposition for this approach"""
        business_area = self._infer_business_area(email_data)
        
        if approach["approach_name"] == "value_roi_focused":
            return f"Typically help companies improve their {business_area} by 25-40% within 90 days"
        elif approach["approach_name"] == "social_proof_focused":
            return f"Similar companies in your industry have seen significant improvements in {business_area}"
        else:
            return f"Specialized expertise in optimizing {business_area} for companies like yours"
    
    def _generate_social_proof(self, email_data: Dict[str, Any], approach: Dict[str, Any]) -> str:
        """Generate relevant social proof"""
        industry = self._infer_industry(email_data.get("client_data", {}))
        return f"Recently helped 3 other {industry} companies achieve similar results"
    
    def _generate_industry_insights(self, email_data: Dict[str, Any]) -> str:
        """Generate relevant industry insights"""
        industry = self._infer_industry(email_data.get("client_data", {}))
        return f"Latest {industry} industry trends show increasing focus on efficiency and automation"
    
    def _generate_call_to_action(self, approach: Dict[str, Any]) -> str:
        """Generate appropriate call to action for this approach"""
        cta_map = {
            "value_roi_focused": "Quick 15-minute call to discuss potential impact on your business?",
            "social_proof_focused": "Would you like to see the case study and results?", 
            "insight_focused": "Happy to share the industry report - would that be helpful?",
            "problem_solution_focused": "Worth a brief conversation to see if this applies to your situation?",
            "relationship_building": "Would love to connect and learn more about your current priorities"
        }
        
        return cta_map.get(approach["approach_name"], "Would you be open to a brief conversation?")
    
    def _generate_personalized_opening(self, email_data: Dict[str, Any], approach: Dict[str, Any]) -> str:
        """Generate personalized email opening"""
        client_name = email_data.get("client_data", {}).get("full_name", "")
        
        opening_map = {
            "value_roi_focused": f"Hi {client_name}, I reached out last week but wanted to follow up with something specific...",
            "social_proof_focused": f"Hi {client_name}, thought you might find this interesting...",
            "insight_focused": f"Hi {client_name}, came across something that might impact your industry...",
            "problem_solution_focused": f"Hi {client_name}, been thinking about our previous conversation...",
            "relationship_building": f"Hi {client_name}, hope you're doing well..."
        }
        
        return opening_map.get(approach["approach_name"], f"Hi {client_name}, following up on my previous message...")
    
    def _get_relevant_problem_for_profile(self, industry: str, business_area: str, interests: List[str]) -> str:
        """Get relevant problem based on client profile"""
        if "software" in business_area.lower() or any("software" in interest.lower() for interest in interests):
            return "development efficiency and scalability challenges"
        elif "cloud" in business_area.lower() or any("cloud" in interest.lower() or "aws" in interest.lower() for interest in interests):
            return "cloud infrastructure optimization needs"
        elif industry == "Financial Services" or any("fintech" in interest.lower() for interest in interests):
            return "regulatory compliance and performance optimization"
        else:
            return "operational efficiency challenges"
    
    def _get_relevant_value_prop_for_profile(self, industry: str, business_area: str, job_title: str) -> str:
        """Get relevant value proposition based on client profile"""
        if "software" in business_area.lower() or "Engineer" in job_title:
            return "streamline development processes and improve code deployment efficiency by 30-50%"
        elif "cloud" in business_area.lower() or any(tech in job_title.lower() for tech in ["cloud", "devops", "infrastructure"]):
            return "optimize cloud infrastructure costs and improve system reliability by 40%"
        elif industry == "Financial Services":
            return "enhance compliance processes while reducing operational overhead by 25-35%"
        else:
            return "improve operational efficiency and reduce costs by 25-40%"
    
    def _extract_company_from_summary(self, summary: str) -> str:
        """Extract company name from profile summary"""
        import re
        
        # Look for patterns like "at [Company Name]"
        at_pattern = r'at\s+(?:a\s+)?([^,\.\s]+(?:\s+[^,\.\s]+){0,3})'
        at_match = re.search(at_pattern, summary, re.IGNORECASE)
        if at_match:
            company = at_match.group(1).strip()
            # Clean up common patterns
            company = re.sub(r'\b(startup|company|corporation|inc|ltd|llc)\b', '', company, flags=re.IGNORECASE).strip()
            if company and len(company) > 2:
                return f"{company} (fintech startup)" if "fintech" in summary.lower() else company
        
        # Look for company-type keywords
        if "fintech startup" in summary.lower():
            return "fintech startup"
        elif "startup" in summary.lower():
            return "technology startup" 
        elif "company" in summary.lower():
            return "technology company"
        
        # Fallback
        return "current organization"

# Usage example and testing
if __name__ == "__main__":
    # Example usage
    agent = InitialApproachStrategyAgent()
    
    sample_email_data = {
        "email_id": 1,
        "client_id": 123,
        "user_id": 456,
        "client_name": "John Smith",
        "recipient_email": "john@techcompany.com",
        "client_data": {
            "full_name": "John Smith",
            "email": "john@techcompany.com", 
            "company": "Tech Innovations Inc",
            "company_website": "techinnovations.com"
        },
        "original_context": {
            "client_type": "business",
            "timezone": "America/New_York",
            "preferred_language": "English",
            "communication_method": "email",
            "product_services": "sales automation software"
        }
    }
    
    result = agent.create_followup_strategy(sample_email_data)
    print(json.dumps(result, indent=2, default=str))