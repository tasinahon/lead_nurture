"""
Follow-Up Email Templates

This module contains email templates specifically designed for follow-up scenarios
when clients don't respond to initial introductory emails. Templates are organized
by approach type and messaging strategy.

Templates support personalization placeholders and are used by the 
NoReplyWorkflowOrchestrator to generate personalized follow-up emails.
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FollowUpEmailTemplates:
    """
    Centralized repository of follow-up email templates for different approaches and scenarios
    """
    
    def __init__(self):
        self.template_name = "FollowUpEmailTemplates"
        logger.info(f"📧 {self.template_name} initialized")
    
    def get_template(self, approach_name: str, followup_number: int = 1) -> Dict[str, Any]:
        """
        Get email template for specific approach and follow-up sequence number
        
        Args:
            approach_name: Name of the approach (value_roi_focused, social_proof_focused, etc.)
            followup_number: Which follow-up in sequence (1, 2, 3, etc.)
            
        Returns:
            Dictionary containing subject and content templates with personalization placeholders
        """
        
        try:
            template_key = f"{approach_name}_followup_{followup_number}"
            
            # Get the template method
            template_method = getattr(self, f"_get_{approach_name}_template", None)
            if not template_method:
                logger.warning(f"⚠️ No template method found for {approach_name}, using default")
                return self._get_default_template(followup_number)
            
            return template_method(followup_number)
            
        except Exception as e:
            logger.error(f"❌ Error getting template for {approach_name}: {e}")
            return self._get_default_template(followup_number)
    
    def _get_value_roi_focused_template(self, followup_number: int) -> Dict[str, Any]:
        """
        Templates for value/ROI focused follow-up approach
        """
        
        templates = {
            1: {
                "subject": "Quick question about {company_name}'s {business_area}",
                "content": """Hi {client_name},

I reached out last week but wanted to follow up with something specific that caught my attention.

I've been working with companies like {company_name} to help them {value_proposition}, and based on what I know about {industry} companies, this could be particularly relevant right now.

{specific_roi_example}

{call_to_action}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "company_name", "business_area", "value_proposition", 
                    "industry", "specific_roi_example", "call_to_action", "sender_name"
                ]
            },
            2: {
                "subject": "Following up - {specific_benefit} for {company_name}",
                "content": """Hi {client_name},

Hope you're doing well. I wanted to circle back on my previous message about {value_proposition}.

I realize timing might not have been right, but I wanted to share a quick example: {roi_case_study}

This is exactly the kind of impact we typically see with {industry} companies of your size.

{soft_call_to_action}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "company_name", "specific_benefit", "value_proposition",
                    "roi_case_study", "industry", "soft_call_to_action", "sender_name"
                ]
            },
            3: {
                "subject": "Last follow-up - {company_name} and {specific_opportunity}",
                "content": """Hi {client_name},

This will be my last follow-up, but I wanted to reach out one more time because I believe there's a real opportunity for {company_name}.

{final_value_statement}

If now isn't the right time, I completely understand. But if you'd ever like to explore this further, just let me know.

{final_call_to_action}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "company_name", "specific_opportunity", "final_value_statement",
                    "final_call_to_action", "sender_name"
                ]
            }
        }
        
        return templates.get(followup_number, templates[1])
    
    def _get_social_proof_focused_template(self, followup_number: int) -> Dict[str, Any]:
        """
        Templates for social proof focused follow-up approach
        """
        
        templates = {
            1: {
                "subject": "How {similar_company} achieved {specific_result}",
                "content": """Hi {client_name},

Hope you're doing well. Thought you might find this interesting...

{social_proof_story}

The approach we used might be applicable to {company_name}'s situation as well, especially considering {industry_context}.

{case_study_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "similar_company", "specific_result", "social_proof_story",
                    "company_name", "industry_context", "case_study_offer", "sender_name"
                ]
            },
            2: {
                "subject": "Another success story from {industry} sector",
                "content": """Hi {client_name},

Following up on my previous message - wanted to share another relevant example.

{additional_social_proof}

What's interesting is that both companies started with similar challenges to what I imagine {company_name} might be facing.

{testimonial_or_quote}

{gentle_call_to_action}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "industry", "additional_social_proof", "company_name",
                    "testimonial_or_quote", "gentle_call_to_action", "sender_name"
                ]
            },
            3: {
                "subject": "Final case study - {specific_industry} success",
                "content": """Hi {client_name},

This will be my final message, but I wanted to share one last case study that I think is particularly relevant to {company_name}.

{compelling_case_study}

{peer_validation_statement}

If you'd ever like to connect with any of these companies directly or learn more about their results, just let me know.

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "specific_industry", "company_name", "compelling_case_study",
                    "peer_validation_statement", "sender_name"
                ]
            }
        }
        
        return templates.get(followup_number, templates[1])
    
    def _get_insight_focused_template(self, followup_number: int) -> Dict[str, Any]:
        """
        Templates for industry insight focused follow-up approach
        """
        
        templates = {
            1: {
                "subject": "New {industry} regulation affecting {company_name}?",
                "content": """Hi {client_name},

Came across something that might impact your industry and thought of {company_name}.

{industry_insight}

{expert_analysis}

{insight_sharing_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "industry", "company_name", "industry_insight",
                    "expert_analysis", "insight_sharing_offer", "sender_name"
                ]
            },
            2: {
                "subject": "Market trends update - {specific_trend}",
                "content": """Hi {client_name},

Hope you're doing well. Following up with another insight that might be relevant to {company_name}.

{market_trend_analysis}

{impact_on_business}

{advisory_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "specific_trend", "company_name", "market_trend_analysis",
                    "impact_on_business", "advisory_offer", "sender_name"
                ]
            },
            3: {
                "subject": "Industry report - {specific_topic}",
                "content": """Hi {client_name},

This will be my last follow-up, but I wanted to share a comprehensive industry report that I think you'd find valuable.

{detailed_industry_report}

{strategic_implications}

The report is available if you'd like it - no strings attached. Just thought it might be useful for your planning.

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "specific_topic", "detailed_industry_report",
                    "strategic_implications", "sender_name"
                ]
            }
        }
        
        return templates.get(followup_number, templates[1])
    
    def _get_problem_solution_focused_template(self, followup_number: int) -> Dict[str, Any]:
        """
        Templates for problem-solution focused follow-up approach
        """
        
        templates = {
            1: {
                "subject": "Solving {specific_problem} at {company_name}",
                "content": """Hi {client_name},

I reached out previously, but wanted to follow up because I've been thinking about {specific_problem} and how it might be affecting {company_name}.

{problem_agitation}

{solution_preview}

{demo_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "specific_problem", "company_name", "problem_agitation",
                    "solution_preview", "demo_offer", "sender_name"
                ]
            },
            2: {
                "subject": "Alternative solution for {pain_point}",
                "content": """Hi {client_name},

Hope you're doing well. Following up on my previous message about {specific_problem}.

I realize there might be other priorities right now, so I wanted to share a different approach that might be more suitable:

{alternative_solution}

{flexibility_statement}

{low_pressure_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "pain_point", "specific_problem", "alternative_solution",
                    "flexibility_statement", "low_pressure_offer", "sender_name"
                ]
            },
            3: {
                "subject": "Final thoughts on {business_challenge}",
                "content": """Hi {client_name},

This will be my last message, but I wanted to leave you with some thoughts on {business_challenge} that might be helpful even if we don't work together.

{helpful_advice}

{resource_offer}

If you ever want to revisit this conversation in the future, just reach out.

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "business_challenge", "helpful_advice",
                    "resource_offer", "sender_name"
                ]
            }
        }
        
        return templates.get(followup_number, templates[1])
    
    def _get_relationship_building_template(self, followup_number: int) -> Dict[str, Any]:
        """
        Templates for relationship building focused follow-up approach
        """
        
        templates = {
            1: {
                "subject": "Introduction - {sender_name} from {sender_company}",
                "content": """Hi {client_name},

Hope you're doing well. I reached out previously but wanted to try a different approach.

{personal_connection}

{mutual_interest}

{informal_conversation_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "sender_name", "sender_company", "personal_connection",
                    "mutual_interest", "informal_conversation_offer"
                ]
            },
            2: {
                "subject": "Connecting in the {industry} community",
                "content": """Hi {client_name},

Hope you're doing well. I've been thinking about our {industry} community and the challenges we all face.

{community_insight}

{shared_experience}

{networking_offer}

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "industry", "community_insight", "shared_experience",
                    "networking_offer", "sender_name"
                ]
            },
            3: {
                "subject": "Staying connected",
                "content": """Hi {client_name},

This will be my final outreach, but I wanted to say that I'd love to stay connected even if there's no immediate business opportunity.

{genuine_interest}

{future_connection_offer}

Wishing you and {company_name} all the best.

Best regards,
{sender_name}""",
                "placeholders": [
                    "client_name", "genuine_interest", "future_connection_offer",
                    "company_name", "sender_name"
                ]
            }
        }
        
        return templates.get(followup_number, templates[1])
    
    def _get_default_template(self, followup_number: int) -> Dict[str, Any]:
        """
        Default template when specific approach template is not found
        """
        
        templates = {
            1: {
                "subject": "Following up on my previous message",
                "content": """Hi {client_name},

I reached out previously but wanted to follow up to see if there might be an opportunity to connect.

{general_value_proposition}

{flexible_call_to_action}

Best regards,
{sender_name}""",
                "placeholders": ["client_name", "general_value_proposition", "flexible_call_to_action", "sender_name"]
            },
            2: {
                "subject": "Second follow-up - {company_name}",
                "content": """Hi {client_name},

Hope you're doing well. I wanted to reach out one more time about {general_topic}.

{adjusted_approach}

{understanding_statement}

Best regards,
{sender_name}""",
                "placeholders": ["client_name", "company_name", "general_topic", "adjusted_approach", "understanding_statement", "sender_name"]
            },
            3: {
                "subject": "Final follow-up - {company_name}",
                "content": """Hi {client_name},

This will be my last follow-up, but I wanted to reach out one final time.

{final_message}

If there's ever a future opportunity to connect, please don't hesitate to reach out.

Best regards,
{sender_name}""",
                "placeholders": ["client_name", "company_name", "final_message", "sender_name"]
            }
        }
        
        return templates.get(followup_number, templates[1])
    
    def get_available_approaches(self) -> List[str]:
        """
        Get list of available template approaches
        """
        return [
            "value_roi_focused",
            "social_proof_focused", 
            "insight_focused",
            "problem_solution_focused",
            "relationship_building"
        ]
    
    def personalize_template(self, template: Dict[str, Any], personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Personalize a template with actual data
        
        Args:
            template: Template dictionary with subject and content
            personalization_data: Dictionary with personalization values
            
        Returns:
            Personalized template with placeholders replaced
        """
        
        try:
            personalized_subject = template["subject"]
            personalized_content = template["content"]
            
            # Replace placeholders in subject and content
            for placeholder in template.get("placeholders", []):
                placeholder_pattern = f"{{{placeholder}}}"
                replacement_value = personalization_data.get(placeholder, placeholder_pattern)
                
                personalized_subject = personalized_subject.replace(placeholder_pattern, str(replacement_value))
                personalized_content = personalized_content.replace(placeholder_pattern, str(replacement_value))
            
            return {
                "subject": personalized_subject,
                "content": personalized_content,
                "approach": template.get("approach", "default"),
                "personalized_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error personalizing template: {e}")
            return {
                "subject": "Follow-up message",
                "content": "Hi there,\n\nFollowing up on my previous message.\n\nBest regards,\nYour Contact",
                "approach": "error_fallback",
                "error": str(e)
            }

# Usage example and testing
if __name__ == "__main__":
    # Example usage
    templates = FollowUpEmailTemplates()
    
    # Test getting a template
    template = templates.get_template("value_roi_focused", 1)
    print("Template:", template)
    
    # Test personalization
    personalization_data = {
        "client_name": "John Smith",
        "company_name": "Tech Innovations Inc",
        "business_area": "sales operations", 
        "value_proposition": "improve sales conversion rates by 25-40%",
        "industry": "technology",
        "specific_roi_example": "For example, a similar tech company saw a $500K increase in quarterly revenue within 90 days.",
        "call_to_action": "Would you be open to a quick 15-minute call to discuss this?",
        "sender_name": "Alex Johnson"
    }
    
    personalized = templates.personalize_template(template, personalization_data)
    print("\nPersonalized Template:")
    print("Subject:", personalized["subject"])
    print("Content:", personalized["content"])