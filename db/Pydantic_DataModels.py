from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# User Models
class UserBase(BaseModel):
    name: str
    email: str
    auth_provider: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Client Models
class ClientBase(BaseModel):
    full_name: str
    company: str
    title: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_handle: Optional[str] = None

class ClientCreate(ClientBase):
    user_id: int

class Client(ClientBase):
    client_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Profile Models
class ProfileBase(BaseModel):
    summary: str
    interests: str
    personality_vector: str
    preferred_language: str
    preferred_contact: str
    engagement_times: str  # JSON string

class ProfileCreate(ProfileBase):
    client_id: int

class Profile(ProfileBase):
    profile_id: int
    client_id: int

    class Config:
        from_attributes = True

# Campaign Models
class CampaignBase(BaseModel):
    goal: str
    status: str

class CampaignCreate(CampaignBase):
    user_id: int
    client_id: int

class Campaign(CampaignBase):
    campaign_id: int
    user_id: int
    client_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Strategy Models
class StrategyBase(BaseModel):
    channel: str
    schedule: str
    product_type: str

class StrategyCreate(StrategyBase):
    campaign_id: int

class Strategy(StrategyBase):
    strategy_id: int
    campaign_id: int
    generated_at: datetime

    class Config:
        from_attributes = True

# EmailDraft Models
class EmailDraftBase(BaseModel):
    version_no: int
    body_markdown: str
    is_approved: bool

class EmailDraftCreate(EmailDraftBase):
    campaign_id: int

class EmailDraft(EmailDraftBase):
    draft_id: int
    campaign_id: int
    created_at: datetime

    class Config:
        from_attributes = True



# MessageDraft

class MessageDraftBase(BaseModel):
    version_no: int
    message_text: str
    is_approved: bool

class MessageDraftCreate(MessageDraftBase):
    campaign_id: int

class MessageDraft(MessageDraftBase):
    draft_id: int
    campaign_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Email Models
class EmailBase(BaseModel):
    personalized_body: str
    is_final: bool

class EmailCreate(EmailBase):
    draft_id: int

class Email(EmailBase):
    email_id: int
    draft_id: int
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True



class MessageBase(BaseModel):
    personalized_text: str
    is_final: bool

class MessageCreate(MessageBase):
    draft_id: int

class Message(MessageBase):
    message_id: int
    draft_id: int
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True

# MessageSend Models
class MessageSendBase(BaseModel):
    channel: str
    status: str

class MessageSendCreate(MessageSendBase):
    email_id: int

class MessageSend(MessageSendBase):
    send_id: int
    email_id: int
    sent_at: datetime

    class Config:
        from_attributes = True

# CommLog Models
class CommLogBase(BaseModel):
    log_text: str

class CommLogCreate(CommLogBase):
    send_id: int
    client_id: int

class CommLog(CommLogBase):
    log_id: int
    send_id: int
    client_id: int
    logged_at: datetime

    class Config:
        from_attributes = True

# Engagement Models
class EngagementBase(BaseModel):
    event_type: str

class EngagementCreate(EngagementBase):
    campaign_id: int

class Engagement(EngagementBase):
    engagement_id: int
    campaign_id: int
    event_at: datetime

    class Config:
        from_attributes = True

# Feedback Models
class FeedbackBase(BaseModel):
    stage: str
    comments: str
    wants_change: bool

class FeedbackCreate(FeedbackBase):
    # email_id: int
    user_id: int
   
class Feedback(FeedbackBase):
    feedback_id: int
    email_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ContextQuestion Models
# class ContextQuestionBase(BaseModel):
#     question: str
#     answer: str

# class ContextQuestionCreate(ContextQuestionBase):
#     client_id: int
#     user_id: int

# class ContextQuestion(ContextQuestionBase):
#     question_id: int
#     client_id: int
#     user_id: int
#     created_at: datetime

#     class Config:
#         from_attributes = True


class ContextQuestionBase(BaseModel):
    question: str
    answer: str

class ContextQuestionCreate(ContextQuestionBase):
    client_id: int
    user_id: int

class ContextQuestionBatchCreate(BaseModel):
    client_id: int
    user_id: int
    qa_pairs: List[ContextQuestionBase]  

class ContextQuestion(ContextQuestionBase):
    question_id: int
    client_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ScrapedData Models
class ScrapedDataBase(BaseModel):
    source_type: str
    raw_json: str  # JSON string

class ScrapedDataCreate(ScrapedDataBase):
    client_id: int

class ScrapedData(ScrapedDataBase):
    scraped_id: int
    client_id: int
    scraped_at: datetime

    class Config:
        from_attributes = True

# Communication Models
class CommunicationBase(BaseModel):
    channel: str
    content: str

class CommunicationCreate(CommunicationBase):
    user_id: int
    client_id: int

class Communication(CommunicationBase):
    comm_id: int
    user_id: int
    client_id: int
    timestamp: datetime

    class Config:
        from_attributes = True