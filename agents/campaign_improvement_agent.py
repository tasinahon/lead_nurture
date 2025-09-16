"""
Campaign Improvement Agent
Handles user suggestions and improvements for campaign plans
"""

import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

class CampaignImprovementAgent(Runnable):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.7,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
    def improve_campaign_content(self, user_suggestion: str, current_content: Dict[str, Any], specific_day: int = None, specific_field: str = None) -> Dict[str, Any]:
        """
        Process user suggestions and improve campaign content
        
        Args:
            user_suggestion: Natural language suggestion from user
            current_content: Current campaign plan content
            specific_day: Specific day to focus on (optional)
            specific_field: Specific field to focus on (optional)
            
        Returns:
            Dict with improved content in same structure as input
        """
        
        # Create focused context based on specific day/field
        focus_context = ""
        if specific_day:
            focus_context += f"Focus specifically on Day {specific_day}. "
        if specific_field:
            focus_context += f"Focus specifically on the '{specific_field}' field. "
            
        # Build the prompt for AI
        prompt = f"""
You are a Campaign Improvement AI Agent. Your job is to analyze user suggestions and improve campaign content accordingly.

USER SUGGESTION: "{user_suggestion}"
{focus_context}

CURRENT CAMPAIGN CONTENT:
{json.dumps(current_content, indent=2)}

INSTRUCTIONS:
1. Analyze the user's suggestion carefully
2. Understand what specific improvements they want
3. Apply those improvements to the relevant content
4. Keep the same JSON structure
5. Only modify content that relates to the user's suggestion
6. Maintain professional marketing tone unless user specifies otherwise
7. Ensure improvements are actionable and specific

IMPORTANT RULES:
- If user mentions "more engaging" → add compelling hooks, questions, or emotional triggers
- If user mentions "urgency" → add time-sensitive language, deadlines, limited offers
- If user mentions "softer/friendlier" → use warmer, more personal language
- If user mentions specific day → only modify that day's content
- If user mentions specific field (title/subject/objective/content) → only modify that field

Return ONLY the improved content in the EXACT same JSON structure. Do not add explanations or comments.
"""

        try:
            # Call Gemini API through Langchain
            system_message = "You are a professional campaign improvement AI. Return only valid JSON with improved content."
            full_prompt = f"{system_message}\n\n{prompt}"
            
            response = self.llm.invoke(full_prompt)
            
            # Extract and parse the response
            improved_content_str = response.content.strip()
            
            # Try to parse as JSON
            try:
                improved_content = json.loads(improved_content_str)
                return improved_content
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', improved_content_str, re.DOTALL)
                if json_match:
                    improved_content = json.loads(json_match.group())
                    return improved_content
                else:
                    raise Exception("Could not parse AI response as JSON")
                    
        except Exception as e:
            raise Exception(f"AI processing error: {str(e)}")
    
    def analyze_suggestion(self, suggestion: str) -> Dict[str, Any]:
        """
        Analyze user suggestion to extract intent, target day, and field
        
        Returns:
            Dict with analysis: {
                "intent": "improve_engagement|add_urgency|soften_tone|...",
                "target_day": int or None,
                "target_field": "title|subject|objective|content" or None,
                "scope": "single_day|all_days|specific_field"
            }
        """
        
        analysis_prompt = f"""
Analyze this user suggestion for campaign improvement: "{suggestion}"

Extract:
1. Intent (what kind of improvement): improve_engagement, add_urgency, soften_tone, fix_grammar, add_personalization, etc.
2. Target day (if mentioned): number or null
3. Target field (if mentioned): title, subject, objective, content, or null  
4. Scope: single_day, all_days, or specific_field

Return as JSON:
{{
    "intent": "improvement_type",
    "target_day": number_or_null,
    "target_field": "field_or_null", 
    "scope": "scope_type"
}}
"""
        
        try:
            # Use Gemini for analysis
            system_message = "You are a suggestion analysis AI. Return only valid JSON."
            full_prompt = f"{system_message}\n\n{analysis_prompt}"
            
            response = self.llm.invoke(full_prompt)
            
            analysis_str = response.content.strip()
            analysis = json.loads(analysis_str)
            return analysis
            
        except Exception as e:
            # Fallback analysis if AI fails
            return {
                "intent": "general_improvement",
                "target_day": None,
                "target_field": None,
                "scope": "all_days"
            }
            
    def validate_improvements(self, original: Dict[str, Any], improved: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Compare original and improved content to identify specific changes made
        
        Returns:
            List of change records with old/new values
        """
        changes = []
        
        for day_key, day_content in improved.items():
            if day_key in original and isinstance(day_content, dict):
                original_day = original[day_key]
                
                for field, new_value in day_content.items():
                    if field in original_day:
                        old_value = original_day[field]
                        if old_value != new_value:
                            changes.append({
                                "day": day_key,
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                                "change_type": "modification"
                            })
        
        return changes
    
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main invoke method for Runnable interface
        Expected input: {
            "suggestion": str,
            "current_content": dict,
            "day": int (optional),
            "field": str (optional)
        }
        """
        return self.improve_campaign_content(
            user_suggestion=input_data["suggestion"],
            current_content=input_data["current_content"],
            specific_day=input_data.get("day"),
            specific_field=input_data.get("field")
        )