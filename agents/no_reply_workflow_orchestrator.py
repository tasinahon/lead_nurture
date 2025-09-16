"""
No Reply Workflow Orchestrator

This orchestrator coordinates the complete workflow when clients don't respond to initial emails:
1. Strategy creation using InitialApproachStrategyAgent
2. Campaign creation using existing campaign creation agents
3. Campaign planning and scheduling
4. Email execution and tracking
5. Response monitoring setup

This is the central coordinator that integrates all components of the no-reply follow-up system.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Import our agents
from agents.initial_approach_strategy_agent import InitialApproachStrategyAgent
from agents.draft_email_agent import EmailDraftAgent
from agents.email_personaliser_agent import PersonaliserAgent
from agents.enhanced_campaign_planner_agent import EnhancedCampaignPlannerAgent
from agents.email_sender_agent import EmailSenderAgent

# Database imports
from db.session import SessionLocal
from db.database_schema import IntroductoryEmail, User, Email, EmailDraft, Campaign, CampaignPlan, CampaignExecution

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NoReplyWorkflowOrchestrator:
    """
    Orchestrates the complete no-reply follow-up workflow
    """
    
    def __init__(self):
        self.orchestrator_name = "NoReplyWorkflowOrchestrator"
        
        # Initialize all required agents
        self.strategy_agent = InitialApproachStrategyAgent()
        self.draft_agent = EmailDraftAgent()
        self.personaliser_agent = PersonaliserAgent()
        self.campaign_planner = EnhancedCampaignPlannerAgent()
        self.email_sender = EmailSenderAgent()
        
        logger.info(f"🎼 {self.orchestrator_name} initialized with all agents")
    
    def orchestrate_no_reply_workflow(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete orchestration of no-reply follow-up workflow
        
        Args:
            email_data: Dictionary containing original email and client information
            
        Returns:
            Dictionary containing workflow results and campaign information
        """
        
        try:
            logger.info(f"🎼 Starting no-reply workflow orchestration for client {email_data['client_name']}")
            
            # Step 1: Create follow-up strategy
            strategy_result = self._create_followup_strategy(email_data)
            if strategy_result["status"] != "strategy_created":
                return self._handle_workflow_error("strategy_creation", strategy_result)
            
            # Step 2: Create campaign in database
            campaign_result = self._create_followup_campaign(email_data, strategy_result)
            if campaign_result["status"] != "campaign_created":
                return self._handle_workflow_error("campaign_creation", campaign_result)
            
            # Step 3: Generate and personalize follow-up emails
            email_generation_result = self._generate_followup_emails(
                email_data, 
                strategy_result, 
                campaign_result
            )
            if email_generation_result["status"] != "emails_generated":
                return self._handle_workflow_error("email_generation", email_generation_result)
            
            # Step 4: Schedule email delivery
            scheduling_result = self._schedule_email_delivery(
                campaign_result, 
                email_generation_result,
                strategy_result
            )
            if scheduling_result["status"] != "emails_scheduled":
                return self._handle_workflow_error("email_scheduling", scheduling_result)
            
            # Step 5: Setup response monitoring
            monitoring_result = self._setup_response_monitoring(
                campaign_result,
                email_generation_result
            )
            
            logger.info(f"✅ No-reply workflow orchestration completed for client {email_data['client_name']}")
            
            return {
                "status": "workflow_completed",
                "client_id": email_data["client_id"],
                "original_email_id": email_data.get("email_id"),
                "campaign_id": campaign_result["campaign_id"],
                "strategy": strategy_result["strategy"],
                "generated_emails": email_generation_result["emails"],
                "scheduling": scheduling_result,
                "monitoring": monitoring_result,
                "workflow_completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error in no-reply workflow orchestration: {e}")
            return {
                "status": "workflow_error",
                "error": str(e),
                "client_id": email_data.get("client_id"),
                "step_failed": "orchestration"
            }
    
    def _create_followup_strategy(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1: Create follow-up strategy using InitialApproachStrategyAgent
        """
        
        try:
            logger.info("📋 Creating follow-up strategy...")
            
            strategy_result = self.strategy_agent.create_followup_strategy(email_data)
            
            if strategy_result["status"] == "strategy_created":
                logger.info(f"✅ Strategy created with {len(strategy_result['strategy']['campaign_sequence'])} follow-up emails")
            
            return strategy_result
            
        except Exception as e:
            logger.error(f"❌ Error creating follow-up strategy: {e}")
            return {"status": "error", "error": str(e)}
    
    def _create_followup_campaign(self, email_data: Dict[str, Any], strategy_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Create campaign record in database
        """
        
        try:
            logger.info("🗂️ Creating follow-up campaign in database...")
            
            with SessionLocal() as session:
                # Get user information
                user_id = email_data.get("user_id")
                if not user_id:
                    return {"status": "error", "error": "User ID not provided"}
                
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return {"status": "error", "error": f"User not found: {user_id}"}
                
                # Create campaign using existing Campaign model
                strategy = strategy_result["strategy"]
                campaign_sequence = strategy["campaign_sequence"]
                personalization_data = strategy["personalization_data"]
                
                new_campaign = Campaign(
                    user_id=user_id,
                    client_id=email_data["client_id"],
                    name=f"No-Reply Follow-up: {email_data['client_name']}",
                    description=f"Follow-up campaign for {email_data['client_name']} who didn't respond to initial email",
                    tags="no_reply_followup",
                    created_at=datetime.utcnow(),
                    status="executing"
                )
                
                session.add(new_campaign)
                session.commit()
                session.refresh(new_campaign)
                
                # Create campaign plans for each follow-up email
                campaign_plans = []
                for i, email_step in enumerate(campaign_sequence):
                    approach = email_step["approach"]
                    
                    # Personalize the subject template for the campaign plan
                    subject_template = approach.get("subject_template", "Follow-up message")
                    personalized_subject = self._personalize_subject_fallback(subject_template, personalization_data)
                    
                    plan = CampaignPlan(
                        campaign_id=new_campaign.campaign_id,
                        day=email_step["day"],
                        title=f"Follow-up {i + 1}: {approach['approach_name']}",
                        subject=personalized_subject,
                        goal=f"Re-engage client using {approach['approach_name']} approach",
                        body_idea=f"Use {approach['angle']} messaging with {approach['tone']} tone",
                        campaign_goal="Generate response from client who didn't reply to initial email"
                    )
                    campaign_plans.append(plan)
                    session.add(plan)
                
                session.commit()
                
                logger.info(f"✅ Campaign created with ID {new_campaign.campaign_id} and {len(campaign_plans)} plans")
                
                return {
                    "status": "campaign_created",
                    "campaign_id": new_campaign.campaign_id,
                    "campaign_plans": [{"id": plan.id, "day": plan.day} for plan in campaign_plans],
                    "total_plans": len(campaign_plans),
                    "user_info": {
                        "user_id": user.user_id,
                        "name": user.name,
                        "email": user.email,
                        "company_name": user.company_name or "Your Company",
                        "company_description": user.company_description or "",
                        "job_title": user.job_title or "Professional"
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error creating follow-up campaign: {e}")
            return {"status": "error", "error": str(e)}
    
    def _generate_followup_emails(self, email_data: Dict[str, Any], strategy_result: Dict[str, Any], campaign_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Generate and personalize follow-up emails
        """
        
        try:
            logger.info("✍️ Generating follow-up emails...")
            
            strategy = strategy_result["strategy"]
            campaign_sequence = strategy["campaign_sequence"]
            personalization_data = strategy["personalization_data"]
            
            generated_emails = []
            
            for i, email_step in enumerate(campaign_sequence):
                approach = email_step["approach"]
                
                # Create email request for draft agent
                email_request = {
                    "recipient_name": personalization_data["client_name"],
                    "recipient_email": email_data["recipient_email"],
                    "recipient_company": personalization_data["company_name"],
                    "email_type": "follow_up",
                    "approach_type": approach["approach_name"],
                    "tone": approach["tone"],
                    "subject_template": approach["subject_template"],
                    "personalization": personalization_data,
                    "context": {
                        "is_followup": True,
                        "followup_number": i + 1,
                        "original_email_context": email_data.get("original_context", {}),
                        "approach_angle": approach["angle"],
                        "user_info": campaign_result.get("user_info", {})
                    }
                }
                
                # Draft the email
                draft_result = self._draft_followup_email(email_request, approach)
                if draft_result["status"] != "email_drafted":
                    return {"status": "error", "error": f"Failed to draft email {i+1}: {draft_result.get('error')}"}
                
                # Personalize the email
                personalization_result = self._personalize_followup_email(
                    draft_result["email_content"], 
                    personalization_data,
                    approach
                )
                if personalization_result["status"] != "email_personalized":
                    return {"status": "error", "error": f"Failed to personalize email {i+1}: {personalization_result.get('error')}"}
                
                generated_emails.append({
                    "step_number": i + 1,
                    "approach_name": approach["approach_name"],
                    "subject": personalization_result["personalized_email"]["subject"],
                    "content": personalization_result["personalized_email"]["content"],
                    "send_day": email_step["day"],
                    "priority": email_step["priority"],
                    "metadata": {
                        "approach": approach,
                        "personalization_data": personalization_data
                    }
                })
            
            logger.info(f"✅ Generated {len(generated_emails)} follow-up emails")
            
            return {
                "status": "emails_generated",
                "emails": generated_emails,
                "total_emails": len(generated_emails)
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating follow-up emails: {e}")
            return {"status": "error", "error": str(e)}
    
    def _draft_followup_email(self, email_request: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Draft a follow-up email using the DraftEmailAgent
        """
        
        try:
            # Create a structured request for the draft agent
            draft_request = {
                "recipient_info": {
                    "name": email_request["recipient_name"],
                    "email": email_request["recipient_email"],
                    "company": email_request["recipient_company"]
                },
                "email_context": {
                    "email_type": email_request["email_type"],
                    "tone": email_request["tone"],
                    "approach": approach["angle"],
                    "is_followup": True,
                    "followup_context": email_request["context"]
                },
                "personalization": email_request["personalization"],
                "template_guidance": {
                    "subject_template": email_request["subject_template"],
                    "opening_style": approach["opening"],
                    "value_prop_style": approach["value_prop"],
                    "cta_style": approach["call_to_action"]
                }
            }
            
            # Use the draft agent (assuming it has a method for follow-up emails)
            # For now, we'll create a simplified version
            email_content = self._create_followup_email_content(draft_request, approach)
            
            return {
                "status": "email_drafted",
                "email_content": email_content
            }
            
        except Exception as e:
            logger.error(f"❌ Error drafting follow-up email: {e}")
            return {"status": "error", "error": str(e)}
    
    def _create_followup_email_content(self, draft_request: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create follow-up email content based on approach and personalization using templates
        """
        
        try:
            # Import and use the template system
            from agents.followup_email_templates import FollowUpEmailTemplates
            templates = FollowUpEmailTemplates()
            
            recipient_info = draft_request["recipient_info"]
            context = draft_request["email_context"]["followup_context"]
            personalization = draft_request["personalization"]
            
            # Get followup number from context
            followup_number = context.get("followup_number", 1)
            
            # Get the appropriate template
            template = templates.get_template(approach["approach_name"], followup_number)
            
            # Prepare comprehensive personalization data
            template_personalization = self._prepare_template_personalization(
                recipient_info, context, personalization, approach
            )
            
            # Personalize the template
            personalized_email = templates.personalize_template(template, template_personalization)
            
            return {
                "subject": personalized_email["subject"],
                "content": personalized_email["content"], 
                "approach": approach["approach_name"],
                "tone": approach["tone"],
                "template_used": f"{approach['approach_name']}_followup_{followup_number}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating email content with templates: {e}")
            # Fallback to original method
            return self._create_fallback_email_content(draft_request, approach)
    
    def _prepare_template_personalization(self, recipient_info: Dict[str, Any], context: Dict[str, Any], personalization: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare comprehensive personalization data for email templates
        """
        
        followup_number = context.get("followup_number", 1)
        
        # Get user information from campaign result
        user_info = context.get("user_info", {})
        
        # Base personalization using real client data and actual user information
        template_data = {
            "client_name": recipient_info["name"],
            "company_name": recipient_info.get("company", recipient_info["name"] + "'s organization"),
            "sender_name": user_info.get("name", "Your Representative"),
            "sender_company": user_info.get("company_name", "Your Company"),
            "industry": personalization.get("industry", "Technology"),
            "business_area": personalization.get("business_area", "software development"),
            "specific_problem": self._get_relevant_problem(personalization),
            "job_title": personalization.get("job_title", "Professional"),
            "interests": personalization.get("interests", []),
            "client_summary": personalization.get("summary", "")
        }
        
        # Approach-specific personalization based on real client data
        if approach["approach_name"] == "value_roi_focused":
            value_prop = self._get_personalized_value_proposition(template_data)
            template_data.update({
                "value_proposition": value_prop,
                "specific_roi_example": f"For example, a {template_data['industry']} company with similar {template_data['business_area']} challenges saw {self._get_relevant_roi_metric(template_data)} improvements within 90 days.",
                "call_to_action": "Would you be open to a quick 15-minute conversation about this?",
                "specific_benefit": self._get_specific_benefit(template_data),
                "roi_case_study": f"a recent {template_data['industry']} client achieved significant efficiency gains in their first quarter",
                "soft_call_to_action": f"Worth exploring if this could work for {template_data['company_name']} too?",
                "specific_opportunity": f"{template_data['business_area']} optimization",
                "final_value_statement": f"I truly believe we could help {template_data['company_name']} achieve similar results to what we've seen with other {template_data['industry']} organizations.",
                "final_call_to_action": "If you'd like to explore this further, just let me know."
            })
        
        elif approach["approach_name"] == "social_proof_focused":
            template_data.update({
                "similar_company": f"another {template_data['industry']} company",
                "specific_result": "remarkable efficiency improvements",
                "social_proof_story": f"I recently worked with {template_data['similar_company']} that was facing similar challenges to what I imagine {template_data['company_name']} might be experiencing.",
                "industry_context": f"the current {template_data['industry']} market conditions",
                "case_study_offer": "Would you like to see the case study and results?",
                "additional_social_proof": f"Another {template_data['industry']} company achieved even better results using a similar approach.",
                "testimonial_or_quote": "Their CEO mentioned it was 'exactly what they needed at the right time.'",
                "gentle_call_to_action": "Worth a brief conversation to see if this could apply to your situation?",
                "specific_industry": template_data['industry'],
                "compelling_case_study": f"A {template_data['industry']} company very similar to {template_data['company_name']} achieved outstanding results using our approach.",
                "peer_validation_statement": "These companies are happy to share their experience with peers in the industry."
            })
        
        elif approach["approach_name"] == "insight_focused":
            template_data.update({
                "industry_insight": f"Recent developments in the {template_data['industry']} sector are creating both challenges and opportunities for companies like {template_data['company_name']}.",
                "expert_analysis": "Based on my experience working with similar companies, this could significantly impact operational strategies.",
                "insight_sharing_offer": "Happy to share the full analysis - would that be helpful?",
                "specific_trend": f"digital transformation in {template_data['industry']}",
                "market_trend_analysis": f"The latest market research shows significant shifts in how {template_data['industry']} companies are approaching {template_data['business_area']}.",
                "impact_on_business": f"This could have substantial implications for {template_data['company_name']}'s strategic planning.",
                "advisory_offer": "I'd be happy to discuss the potential impact on your business.",
                "specific_topic": f"{template_data['industry']} industry outlook",
                "detailed_industry_report": f"This comprehensive report covers key trends affecting {template_data['industry']} companies over the next 18 months.",
                "strategic_implications": f"There are some specific implications for companies like {template_data['company_name']} that might be worth considering."
            })
        
        elif approach["approach_name"] == "problem_solution_focused":
            template_data.update({
                "problem_agitation": f"Many {template_data['industry']} companies are struggling with {template_data['specific_problem']}, and it's often more costly than businesses realize.",
                "solution_preview": "We've developed an approach that typically addresses this challenge effectively.",
                "demo_offer": "Would a brief demo be helpful to see how this might work for your situation?",
                "pain_point": template_data['specific_problem'],
                "alternative_solution": "a more flexible approach that requires minimal upfront commitment",
                "flexibility_statement": "We understand every company's situation is different.",
                "low_pressure_offer": "No pressure at all - just thought it might be worth exploring.",
                "business_challenge": template_data['specific_problem'],
                "helpful_advice": f"Even if we don't work together, here are some strategies that often help {template_data['industry']} companies address {template_data['specific_problem']}.",
                "resource_offer": "I'm happy to share some resources that might be helpful regardless."
            })
        
        elif approach["approach_name"] == "relationship_building":
            template_data.update({
                "personal_connection": f"I've been working with {template_data['industry']} companies for several years and have developed a genuine appreciation for the challenges you face.",
                "mutual_interest": f"I'm always interested in connecting with professionals in the {template_data['industry']} space.",
                "informal_conversation_offer": "Would you be open to an informal conversation sometime?",
                "community_insight": f"The {template_data['industry']} community is relatively tight-knit, and I value the relationships I've built over the years.",
                "shared_experience": f"We all face similar challenges in growing our {template_data['industry']} businesses.",
                "networking_offer": "I'd love to connect and learn more about your current priorities and challenges.",
                "genuine_interest": f"I have great respect for what you're building at {template_data['company_name']}.",
                "future_connection_offer": "Perhaps we'll have the opportunity to connect at some point in the future."
            })
        
        # Fallback values
        template_data.setdefault("general_value_proposition", f"helping {template_data['industry']} companies like {template_data['company_name']} optimize their operations")
        template_data.setdefault("flexible_call_to_action", "Would you be open to a brief conversation?")
        template_data.setdefault("general_topic", "business optimization opportunities")
        template_data.setdefault("adjusted_approach", "a different perspective that might be more relevant to your current situation")
        template_data.setdefault("understanding_statement", "I understand timing is important, so no pressure at all.")
        template_data.setdefault("final_message", f"I believe there could be value in connecting about {template_data['company_name']}'s growth opportunities.")
        
        return template_data
    
    def _get_relevant_problem(self, personalization: Dict[str, Any]) -> str:
        """Get relevant problem based on client's industry and role"""
        industry = personalization.get("industry", "Technology")
        business_area = personalization.get("business_area", "operations")
        
        if "software" in business_area.lower() or "development" in business_area.lower():
            return "development efficiency and scalability challenges"
        elif "cloud" in business_area.lower():
            return "cloud infrastructure optimization needs"
        elif "fintech" in business_area.lower() or industry == "Financial Services":
            return "regulatory compliance and security requirements"
        else:
            return "operational efficiency challenges"
    
    def _get_personalized_value_proposition(self, template_data: Dict[str, Any]) -> str:
        """Create personalized value proposition based on client profile"""
        industry = template_data["industry"]
        business_area = template_data["business_area"]
        
        if "software" in business_area.lower():
            return f"streamline {business_area} processes and reduce time-to-market by 30-50%"
        elif "cloud" in business_area.lower():
            return f"optimize {business_area} costs and improve system reliability by 40%"
        elif industry == "Financial Services":
            return "enhance compliance processes while reducing operational overhead by 25-35%"
        else:
            return f"improve {business_area} efficiency and reduce operational costs by 25-40%"
    
    def _get_relevant_roi_metric(self, template_data: Dict[str, Any]) -> str:
        """Get relevant ROI metric based on client's focus area"""
        business_area = template_data["business_area"]
        
        if "software" in business_area.lower():
            return "development velocity and code quality"
        elif "cloud" in business_area.lower():
            return "infrastructure efficiency and cost"
        else:
            return "operational efficiency and productivity"
    
    def _get_specific_benefit(self, template_data: Dict[str, Any]) -> str:
        """Get specific benefit relevant to client"""
        business_area = template_data["business_area"]
        
        if "software" in business_area.lower():
            return "development process improvements"
        elif "cloud" in business_area.lower():
            return "infrastructure optimization"
        else:
            return "operational enhancements"
    
    def _create_fallback_email_content(self, draft_request: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback email creation method when templates fail
        """
        
        recipient_info = draft_request["recipient_info"]
        context = draft_request["email_context"]["followup_context"]
        personalization = draft_request["personalization"]
        
        # Generate subject line
        subject_template = draft_request["template_guidance"]["subject_template"]
        subject = self._personalize_subject_fallback(subject_template, personalization)
        
        # Generate email body based on approach
        body = self._generate_email_body(approach, recipient_info, context, personalization)
        
        return {
            "subject": subject,
            "content": body,
            "approach": approach["approach_name"],
            "tone": approach["tone"],
            "fallback_used": True
        }
    
    def _personalize_subject_fallback(self, template: str, personalization: Dict[str, Any]) -> str:
        """
        Fallback method to personalize subject line template with actual data
        """
        
        subject = template
        
        # Create mapping for template placeholders to personalization keys
        placeholder_mapping = {
            "company": personalization.get("company_name", ""),
            "industry": personalization.get("industry", ""),
            "business_area": personalization.get("business_area", ""),
            "client_name": personalization.get("client_name", ""),
            "job_title": personalization.get("job_title", "")
        }
        
        # Replace placeholders with actual values
        for placeholder, value in placeholder_mapping.items():
            template_placeholder = f"{{{placeholder}}}"
            if template_placeholder in subject and value:
                subject = subject.replace(template_placeholder, str(value))
        
        return subject
    
    def _generate_email_body(self, approach: Dict[str, Any], recipient_info: Dict[str, Any], context: Dict[str, Any], personalization: Dict[str, Any]) -> str:
        """
        Generate email body based on approach and personalization
        """
        
        name = recipient_info["name"]
        company = recipient_info["company"]
        followup_number = context.get("followup_number", 1)
        
        # Get approach-specific content elements
        if approach["approach_name"] == "value_roi_focused":
            body = f"""Hi {name},

I reached out last week but wanted to follow up with something specific that might interest you.

I've been working with companies like {company} to help them {personalization.get('value_proposition', 'improve their operations')}. 

{personalization.get('personalized_opening', 'Based on what I know about your industry, this could be particularly relevant right now.')}

{personalization.get('call_to_action', 'Would you be open to a brief 15-minute conversation?')}

Best regards,
Your Business Partner"""
        
        elif approach["approach_name"] == "social_proof_focused":
            body = f"""Hi {name},

Hope you're doing well. Thought you might find this interesting...

{personalization.get('social_proof', 'I recently helped another company in your industry achieve significant results')}, and it made me think of {company}.

{personalization.get('value_proposition', 'The approach we used might be applicable to your situation as well.')}

{personalization.get('call_to_action', 'Would you like to see the case study and results?')}

Best regards,
Your Business Partner"""
        
        elif approach["approach_name"] == "insight_focused":
            body = f"""Hi {name},

Came across something that might impact your industry and thought of {company}.

{personalization.get('industry_insights', 'Recent trends in your sector show some interesting developments')} that could affect how businesses like yours operate.

{personalization.get('value_proposition', 'This is exactly where we help companies stay ahead of the curve.')}

{personalization.get('call_to_action', 'Happy to share the industry report - would that be helpful?')}

Best regards,
Your Business Partner"""
        
        else:  # Default approach
            body = f"""Hi {name},

Following up on my previous message about {company}.

{personalization.get('personalized_opening', 'I understand you\'re likely busy, but wanted to reach out once more.')}

{personalization.get('value_proposition', 'I believe there might be a good fit between what we do and your business needs.')}

{personalization.get('call_to_action', 'Would you be open to a brief conversation?')}

Best regards,
Your Business Partner"""
        
        return body
    
    def _personalize_followup_email(self, email_content: Dict[str, Any], personalization_data: Dict[str, Any], approach: Dict[str, Any]) -> Dict[str, Any]:
        """
        Further personalize the email using the EmailPersonaliserAgent
        """
        
        try:
            # Create personalization request
            personalization_request = {
                "email_content": email_content,
                "client_data": personalization_data,
                "personalization_level": "high",
                "approach": approach
            }
            
            # For now, return the email as-is since we've already personalized it
            # In a full implementation, you would use the EmailPersonaliserAgent here
            
            return {
                "status": "email_personalized",
                "personalized_email": email_content
            }
            
        except Exception as e:
            logger.error(f"❌ Error personalizing follow-up email: {e}")
            return {"status": "error", "error": str(e)}
    
    def _schedule_email_delivery(self, campaign_result: Dict[str, Any], email_generation_result: Dict[str, Any], strategy_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Schedule email delivery based on timing strategy
        """
        
        try:
            logger.info("📅 Scheduling email delivery...")
            
            campaign_id = campaign_result["campaign_id"]
            emails = email_generation_result["emails"]
            timing_strategy = strategy_result["strategy"]["send_timing"]
            
            scheduled_deliveries = []
            
            with SessionLocal() as session:
                # Create CampaignExecution entries for each scheduled email
                for i, email in enumerate(emails):
                    # Calculate optimal send time
                    send_datetime = self._calculate_optimal_send_time(
                        email["send_day"],
                        timing_strategy
                    )
                    
                    # Create campaign execution record
                    execution = CampaignExecution(
                        campaign_id=campaign_id,
                        day=email["send_day"],
                        generated_at=datetime.utcnow(),
                        scheduled_at=send_datetime,
                        status="generated",
                        email_subject=email["subject"],
                        email_content=email["content"]
                    )
                    session.add(execution)
                    
                    scheduled_deliveries.append({
                        "execution_id": execution.execution_id,
                        "day": email["send_day"],
                        "scheduled_datetime": send_datetime.isoformat(),
                        "subject": email["subject"],
                        "approach": email["approach_name"]
                    })
                
                session.commit()
            
            logger.info(f"✅ Scheduled {len(scheduled_deliveries)} emails for delivery")
            
            return {
                "status": "emails_scheduled",
                "scheduled_deliveries": scheduled_deliveries,
                "total_scheduled": len(scheduled_deliveries)
            }
            
        except Exception as e:
            logger.error(f"❌ Error scheduling email delivery: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_optimal_send_time(self, days_offset: int, timing_strategy: Dict[str, Any]) -> datetime:
        """
        Calculate optimal send time based on timing strategy
        """
        
        base_date = datetime.utcnow() + timedelta(days=days_offset)
        
        # Get preferred hours and days
        preferred_hours = timing_strategy.get("preferred_hours", [10, 14])
        preferred_days = timing_strategy.get("preferred_days", ["Tuesday", "Wednesday", "Thursday"])
        
        # Adjust for preferred day of week
        while base_date.strftime("%A") not in preferred_days:
            base_date += timedelta(days=1)
        
        # Set to preferred hour (use first preferred hour)
        preferred_hour = preferred_hours[0] if preferred_hours else 10
        optimal_time = base_date.replace(hour=preferred_hour, minute=0, second=0, microsecond=0)
        
        return optimal_time
    
    def _setup_response_monitoring(self, campaign_result: Dict[str, Any], email_generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 5: Setup response monitoring for follow-up emails
        """
        
        try:
            logger.info("👁️ Setting up response monitoring...")
            
            campaign_id = campaign_result["campaign_id"]
            
            # Setup monitoring configuration
            monitoring_config = {
                "campaign_id": campaign_id,
                "monitor_replies": True,
                "monitor_opens": True,
                "monitor_clicks": True,
                "monitoring_duration_days": 30,
                "response_check_interval_hours": 6,
                "auto_stop_on_reply": True
            }
            
            # This would integrate with the existing AutomaticReplyScheduler
            # For now, we'll just return the configuration
            
            logger.info(f"✅ Response monitoring configured for campaign {campaign_id}")
            
            return {
                "status": "monitoring_setup",
                "monitoring_config": monitoring_config
            }
            
        except Exception as e:
            logger.error(f"❌ Error setting up response monitoring: {e}")
            return {"status": "error", "error": str(e)}
    
    def _handle_workflow_error(self, step_name: str, error_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle errors in workflow steps
        """
        
        logger.error(f"❌ Workflow error in step {step_name}: {error_result.get('error', 'Unknown error')}")
        
        return {
            "status": "workflow_error",
            "step_failed": step_name,
            "error": error_result.get("error", "Unknown error"),
            "error_details": error_result
        }

# Usage example and testing
if __name__ == "__main__":
    # Example usage
    orchestrator = NoReplyWorkflowOrchestrator()
    
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
    
    result = orchestrator.orchestrate_no_reply_workflow(sample_email_data)
    print(json.dumps(result, indent=2, default=str))