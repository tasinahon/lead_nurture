from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    user_id: int = Field(default=None, primary_key=True)
    name: str
    email: str
    auth_provider: str
    created_at: datetime


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
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    contact_id: int = Field(foreign_key="client.client_id")
    version_no: int
    subject:str
    body_markdown: str
    is_approved: bool
    created_at: datetime

class MessageDraft(SQLModel, table=True):
    draft_id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    contact_id: int = Field(foreign_key="client.client_id")
    version_no: int
    message_text: str
    is_approved: bool
    created_at: datetime

class Email(SQLModel, table=True):
    email_id: int = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="emaildraft.draft_id")
    personalized_body: str
    is_final: bool
    approved_at: Optional[datetime] = None


class Message(SQLModel, table=True):
    message_id: int = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="messagedraft.draft_id")
    personalized_text: str
    is_final: bool
    approved_at: Optional[datetime] = None


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


class Campaign(SQLModel, table=True):
    campaign_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    client_id: Optional[int] = Field(default=None, foreign_key="client.client_id")
    clientlist_id: Optional[int] = Field(default=None, foreign_key="clientlist.clientlist_id")   
    name: str
    description: str
    tags: str  
    created_at: datetime = Field(default_factory=datetime.utcnow)



class CampaignPlan(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.campaign_id")
    day: str  
    title: str  
    subject: str  
    goal: str  
    body_idea: str  
    campaign_goal: Optional[str] = None




# class GeneratedMessage(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     campaign_id: int = Field(foreign_key="campaign.id")
#     contact_id: int = Field(foreign_key="contact.id")
#     campaign_day: int
#     message_type: str  # "email", "message", etc.
#     generated_content: str
#     sent: bool = False
#     sent_at: Optional[datetime] = None
