from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    user_id: int = Field(default=None, primary_key=True)
    name: str
    email: str
    auth_provider: str
    company_name: Optional[str] = None
    company_description: Optional[str] = None
    company_website: Optional[str] = None
    job_title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntroductoryEmail(SQLModel, table=True):
    intro_id: int = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    user_id: int = Field(foreign_key="user.user_id")
    client_type: str
    timezone: str
    preferred_language: str
    communication_method: str
    product_services: str
    draft_id: Optional[int] = Field(foreign_key="emaildraft.draft_id")
    sent_at: Optional[datetime] = None
    replied: bool = Field(default=False)
    reply_check_count: int = Field(default=0)  # Track how many times we've checked for replies
    last_reply_check: Optional[datetime] = None  # When was the last reply check
    
    # No-reply workflow tracking
    no_reply_workflow_triggered: bool = Field(default=False)  # Has no-reply workflow been triggered
    no_reply_workflow_triggered_at: Optional[datetime] = None  # When was no-reply workflow triggered
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Client(SQLModel, table=True):
    client_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    full_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    company_website: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    whatsapp: Optional[str] = None
    category: Optional[str] = None  
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClientList(SQLModel, table=True):
    clientlist_id: int = Field(default=None, primary_key=True)
    # user_id: int = Field(foreign_key="user.user_id") 
    name: str  
    description: Optional[str] = None

class ClientListLink(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    list_id: int = Field(foreign_key="clientlist.clientlist_id")



# class Profile(SQLModel, table=True):
#     profile_id: int = Field(default=None, primary_key=True)
#     client_id: int = Field(foreign_key="client.client_id")
#     summary: str
#     interests: str
#     personality_vector: str
#     preferred_language: str
#     preferred_contact: str
#     engagement_times: str  # Stored as text (JSON)

class Profile(SQLModel, table=True):
    profile_id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    
    summary: str
    interests: str  # Comma-separated keywords
    preferred_language: str
    preferred_contact: str
    engagement_times: str = None

    full_text: str  # For embedding-rich descriptive paragraph
    personality_vector: str  # JSON string of embedding vector

class InitialStrategy(SQLModel, table=True):
    strategy_id: int = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    engagement_channel: str
    tone_style: str
    communication_frequency: str
    general_advice: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)




class Strategy(SQLModel, table=True):
    strategy_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    channel: str
    schedule: str
    product_type: str
    generated_at: datetime

class EmailDraft(SQLModel, table=True):
    draft_id: int = Field(default=None, primary_key=True)
    campaign_id: Optional[int] = Field(default=None, foreign_key="campaign.campaign_id")  # Optional for intro emails
    contact_id: int = Field(foreign_key="client.client_id")
    version_no: int
    subject:str
    day: int
    body_markdown: str
    is_approved: bool
    created_at: datetime

class MessageDraft(SQLModel, table=True):
    draft_id: int = Field(default=None, primary_key=True)
    campaign_id: Optional[int] = Field(default=None, foreign_key="campaign.campaign_id")  # Optional for intro messages  
    contact_id: int = Field(foreign_key="client.client_id")
    version_no: int
    day: int
    message_text: str
    is_approved: bool
    created_at: datetime

class Email(SQLModel, table=True):
    email_id: int = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="emaildraft.draft_id")
    personalized_body: str
    subject:str
    is_final: bool
    approved_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None  
    sent_at: Optional[datetime] = None       



class Message(SQLModel, table=True):
    message_id: int = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="messagedraft.draft_id")
    personalized_text: str
    is_final: bool
    approved_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None  
    sent_at: Optional[datetime] = None


class MessageSend(SQLModel, table=True):
    send_id: int = Field(default=None, primary_key=True)
    email_id: int = Field(foreign_key="email.email_id")
    channel: str
    status: str
    sent_at: datetime

class CommLog(SQLModel, table=True):
    log_id: int = Field(default=None, primary_key=True)
    send_id: int = Field(foreign_key="messagesend.send_id")
    client_id: int = Field(foreign_key="client.client_id")
    log_text: str
    logged_at: datetime

class Engagement(SQLModel, table=True):
    engagement_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    event_type: str
    event_at: datetime

class Feedback(SQLModel, table=True):
    feedback_id: int = Field(default=None, primary_key=True)
    email_id: int = Field(foreign_key="email.email_id")
    user_id: int = Field(foreign_key="user.user_id")
    stage: str
    comments: str
    wants_change:bool
    created_at: datetime

class ContextQuestion(SQLModel, table=True):
    question_id: int = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    user_id: int = Field(foreign_key="user.user_id")
    question: str
    answer: str
    created_at: datetime

class ScrapedData(SQLModel, table=True):
    scraped_id: int = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    source_type: str
    raw_json: str  # Stored as text (JSON)
    scraped_at: datetime

class Communication(SQLModel, table=True):
    comm_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    client_id: int = Field(foreign_key="client.client_id")
    channel: str
    content: str
    timestamp: datetime

# New tables for BRM workflow
class EmailReply(SQLModel, table=True):
    reply_id: int = Field(default=None, primary_key=True)
    original_email_id: int = Field(foreign_key="email.email_id")
    client_id: int = Field(foreign_key="client.client_id")
    reply_subject: str
    reply_body: str
    received_at: datetime
    sentiment: Optional[str] = None  # positive, neutral, negative
    interest_level: Optional[str] = None  # high, medium, low, none
    response_type: Optional[str] = None  # interested, needs_info, busy, not_interested
    analysis_json: Optional[str] = None  # Full sentiment analysis JSON
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Campaign(SQLModel, table=True):
    campaign_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    client_id: int = Field(foreign_key="client.client_id")  # Direct client relationship - much simpler!
    name: Optional[str] = None
    description: str
    tags: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Campaign execution status
    status: str = Field(default="draft")  # draft, approved, executing, completed, paused
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Approval status fields
    approval_status: str = Field(default="pending_approval")  # pending_approval, approved, rejected
    approved_at: Optional[datetime] = None
    user_feedback: Optional[str] = None
    approved_days: Optional[str] = None  # JSON string of approved day numbers

class CampaignClientLink(SQLModel, table=True):
    campaign_id: int = Field(
        foreign_key="campaign.campaign_id", primary_key=True
    )
    client_id: int = Field(
        foreign_key="client.client_id", primary_key=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)





class CampaignPlan(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    day: int  
    title: str  
    subject: str  
    goal: str  
    body_idea: str  
    campaign_goal: Optional[str] = None

class CampaignExecution(SQLModel, table=True):
    execution_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    day: int
    email_id: Optional[int] = Field(default=None, foreign_key="email.email_id")
    generated_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None  # When the email should be sent
    sent_at: Optional[datetime] = None
    status: str = Field(default="not_generated")  # not_generated, generated, sent
    email_subject: Optional[str] = None
    email_content: Optional[str] = None

# ============================================================================
# LEAD SCORING AND PERFORMANCE TRACKING MODELS
# ============================================================================

class LeadScoringConfig(SQLModel, table=True):
    """Configuration for lead scoring parameters"""
    config_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    email_open_points: int = Field(default=10)
    email_click_points: int = Field(default=25)
    email_reply_points: int = Field(default=50)
    website_visit_points: int = Field(default=15)
    social_engagement_points: int = Field(default=20)
    hot_threshold: int = Field(default=100)  # Score >= 100 = Hot lead
    warm_threshold: int = Field(default=50)  # Score >= 50 = Warm lead
    cold_threshold: int = Field(default=0)   # Score < 50 = Cold lead
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class LeadPerformance(SQLModel, table=True):
    """Track individual lead performance metrics with actual counts"""
    performance_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    client_id: int = Field(foreign_key="client.client_id")
    day: int  # Campaign day
    
    # Email tracking counts
    email_sent: bool = Field(default=False)
    email_open_count: int = Field(default=0)  # Count how many times opened
    email_click_count: int = Field(default=0)  # Count how many times clicked
    email_reply_count: int = Field(default=0)  # Count replies
    
    # Website tracking counts  
    website_visit_count: int = Field(default=0)  # Count website visits
    social_engagement_count: int = Field(default=0)  # Count social interactions
    
    # Timestamps - track first and last occurrence
    sent_at: Optional[datetime] = None
    first_opened_at: Optional[datetime] = None
    last_opened_at: Optional[datetime] = None
    first_clicked_at: Optional[datetime] = None
    last_clicked_at: Optional[datetime] = None
    first_replied_at: Optional[datetime] = None
    last_replied_at: Optional[datetime] = None
    first_visited_at: Optional[datetime] = None
    last_visited_at: Optional[datetime] = None
    
    # Derived booleans for backward compatibility
    email_opened: bool = Field(default=False)  # True if opened at least once
    email_clicked: bool = Field(default=False)  # True if clicked at least once
    email_replied: bool = Field(default=False)  # True if replied at least once
    website_visited: bool = Field(default=False)  # True if visited at least once
    social_engaged: bool = Field(default=False)  # True if engaged at least once

class ActivityLog(SQLModel, table=True):
    """Detailed log of every single activity/interaction"""
    activity_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    client_id: int = Field(foreign_key="client.client_id")
    day: int
    activity_type: str  # opened, clicked, replied, visited, engaged
    activity_data: Optional[str] = None  # JSON string with additional data
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
class LeadScore(SQLModel, table=True):
    """Current lead scores and status"""
    score_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    client_id: int = Field(foreign_key="client.client_id")
    total_score: int = Field(default=0)
    email_score: int = Field(default=0)
    engagement_score: int = Field(default=0)
    lead_status: str = Field(default="cold")  # hot, warm, cold
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

class CampaignMetrics(SQLModel, table=True):
    """Overall campaign performance metrics"""
    metric_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    total_leads: int = Field(default=0)
    emails_sent: int = Field(default=0)
    emails_opened: int = Field(default=0)
    emails_clicked: int = Field(default=0)
    emails_replied: int = Field(default=0)
    hot_leads: int = Field(default=0)
    warm_leads: int = Field(default=0)
    cold_leads: int = Field(default=0)
    open_rate: float = Field(default=0.0)
    click_rate: float = Field(default=0.0)
    reply_rate: float = Field(default=0.0)
    last_calculated: datetime = Field(default_factory=datetime.utcnow)
