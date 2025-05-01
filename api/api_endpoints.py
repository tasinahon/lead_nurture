from fastapi import FastAPI, Depends, HTTPException,BackgroundTasks
from graph.strategy_graph import strategy_graph
from sqlmodel import Session, select
from fastapi import APIRouter
from agents.scraper_agent import ScraperAgent 
from graph.profile_graph import profile_graph
from graph.personalise_graph import personalise_phase
from typing import List
from datetime import datetime
from db.session import get_session
from graph.scrape_graph import flow
from graph.redraft_graph import redraft_phase
import logging
from db.Pydantic_DataModels import (
    ContextQuestionBatchCreate, User, UserCreate,
    Client, ClientCreate,
    Profile, ProfileCreate,
    Campaign, CampaignCreate,
    Strategy, StrategyCreate,
    EmailDraft, EmailDraftCreate,
    Email, EmailCreate,
    MessageSend, MessageSendCreate,
    MessageDraft,MessageDraftCreate,
    Message,MessageCreate,
    CommLog, CommLogCreate,
    Engagement, EngagementCreate,
    Feedback, FeedbackCreate,
    ContextQuestion, ContextQuestionCreate,
    ScrapedData, ScrapedDataCreate,
    Communication, CommunicationCreate
)
from db.database_schema import (
    User as UserModel,
    Client as ClientModel,
    Profile as ProfileModel,
    Campaign as CampaignModel,
    Strategy as StrategyModel,
    EmailDraft as EmailDraftModel,
    MessageDraft as MessageDraftModel,
    Email as EmailModel,
    Message as MessageModel,
    MessageSend as MessageSendModel,
    CommLog as CommLogModel,
    Engagement as EngagementModel,
    Feedback as FeedbackModel,
    ContextQuestion as ContextQuestionModel,
    ScrapedData as ScrapedDataModel,
    Communication as CommunicationModel
)

# router = FastAPI()
router=APIRouter()

# User Endpoints
@router.get("/users/", response_model=List[User])
def read_users(session: Session = Depends(get_session)):
    users = session.exec(select(UserModel)).all()
    return users

@router.post("/users/", response_model=User)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = UserModel(**user.dict(), created_at=datetime.utcnow())
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

# Client Endpoints
@router.get("/users/{user_id}/clients/", response_model=List[Client])
def read_clients(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    clients = session.exec(select(ClientModel).where(ClientModel.user_id == user_id)).all()
    return clients



@router.post("/users/{user_id}/clients/", response_model=Client)
def create_client(user_id: int, client: ClientCreate, session: Session = Depends(get_session)):
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if client.user_id != user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")

    db_client = ClientModel(**client.dict(), created_at=datetime.utcnow())
    session.add(db_client)
    session.commit()
    session.refresh(db_client)

    
    try:
        flow.invoke({"client_id": db_client.client_id}) 
    except Exception as e:
        print(f"Graph failed {db_client.client_id}: {e}")

    return db_client





@router.get("/clients/{client_id}/profiles/", response_model=List[Profile])
def read_profiles(client_id: int, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    profiles = session.exec(select(ProfileModel).where(ProfileModel.client_id == client_id)).all()
    return profiles

@router.post("/clients/{client_id}/profiles/", response_model=Profile)
def create_profile(client_id: int, profile: ProfileCreate, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if profile.client_id != client_id:
        raise HTTPException(status_code=400, detail="Client ID mismatch")
    db_profile = ProfileModel(**profile.dict())
    session.add(db_profile)
    session.commit()
    session.refresh(db_profile)
    return db_profile

# Campaign Endpoints
@router.get("/campaigns/", response_model=List[Campaign])
def read_campaigns(session: Session = Depends(get_session)):
    campaigns = session.exec(select(CampaignModel)).all()
    return campaigns

@router.post("/campaigns/", response_model=Campaign)
def create_campaign(campaign: CampaignCreate, session: Session = Depends(get_session)):
    user = session.get(UserModel, campaign.user_id)
    client = session.get(ClientModel, campaign.client_id)
    if not user or not client:
        raise HTTPException(status_code=404, detail="User or Client not found")
    if client.user_id != campaign.user_id:
        raise HTTPException(status_code=400, detail="Client does not belong to this user")
    db_campaign = CampaignModel(**campaign.dict(), created_at=datetime.utcnow())
    session.add(db_campaign)
    session.commit()
    session.refresh(db_campaign)
    return db_campaign

# Strategy Endpoints
@router.get("/campaigns/{campaign_id}/strategies/", response_model=List[Strategy])
def read_strategies(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    strategies = session.exec(select(StrategyModel).where(StrategyModel.campaign_id == campaign_id)).all()
    return strategies

@router.post("/campaigns/{campaign_id}/strategies/", response_model=Strategy)
def create_strategy(campaign_id: int, strategy: StrategyCreate, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if strategy.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Campaign ID mismatch")
    db_strategy = StrategyModel(**strategy.dict(), generated_at=datetime.utcnow())
    session.add(db_strategy)
    session.commit()
    session.refresh(db_strategy)
    return db_strategy

# EmailDraft Endpoints
@router.get("/campaigns/{campaign_id}/email-drafts/", response_model=List[EmailDraft])
def read_email_drafts(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    email_drafts = session.exec(select(EmailDraftModel).where(EmailDraftModel.campaign_id == campaign_id)).all()
    return email_drafts

@router.post("/campaigns/{campaign_id}/email-drafts/", response_model=EmailDraft)
def create_email_draft(campaign_id: int, email_draft: EmailDraftCreate, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if email_draft.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Campaign ID mismatch")
    db_email_draft = EmailDraftModel(**email_draft.dict(), created_at=datetime.utcnow())
    session.add(db_email_draft)
    session.commit()
    session.refresh(db_email_draft)
    return db_email_draft


# Message Draft
@router.get("/campaigns/{campaign_id}/message-drafts/", response_model=List[MessageDraft])
def read_message_drafts(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    message_drafts = session.exec(
        select(MessageDraftModel).where(MessageDraftModel.campaign_id == campaign_id)
    ).all()
    return message_drafts

@router.post("/campaigns/{campaign_id}/message-drafts/", response_model=MessageDraft)
def create_message_draft(campaign_id: int, message_draft: MessageDraftCreate, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if message_draft.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Campaign ID mismatch")
    db_message_draft = MessageDraftModel(**message_draft.dict(), created_at=datetime.utcnow())
    session.add(db_message_draft)
    session.commit()
    session.refresh(db_message_draft)
    return db_message_draft

# Email Endpoints
@router.get("/email-drafts/{draft_id}/emails/", response_model=List[Email])
def read_emails(draft_id: int, session: Session = Depends(get_session)):
    draft = session.get(EmailDraftModel, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="EmailDraft not found")
    emails = session.exec(select(EmailModel).where(EmailModel.draft_id == draft_id)).all()
    return emails

@router.post("/email-drafts/{draft_id}/emails/", response_model=Email)
def create_email(draft_id: int, email: EmailCreate, session: Session = Depends(get_session)):
    draft = session.get(EmailDraftModel, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="EmailDraft not found")
    if email.draft_id != draft_id:
        raise HTTPException(status_code=400, detail="Draft ID mismatch")
    db_email = EmailModel(**email.dict())
    session.add(db_email)
    session.commit()
    session.refresh(db_email)
    return db_email

# MessageSend Endpoints
@router.get("/emails/{email_id}/message-sends/", response_model=List[MessageSend])
def read_message_sends(email_id: int, session: Session = Depends(get_session)):
    email = session.get(EmailModel, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    message_sends = session.exec(select(MessageSendModel).where(MessageSendModel.email_id == email_id)).all()
    return message_sends

@router.post("/emails/{email_id}/message-sends/", response_model=MessageSend)
def create_message_send(email_id: int, message_send: MessageSendCreate, session: Session = Depends(get_session)):
    email = session.get(EmailModel, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if message_send.email_id != email_id:
        raise HTTPException(status_code=400, detail="Email ID mismatch")
    db_message_send = MessageSendModel(**message_send.dict(), sent_at=datetime.utcnow())
    session.add(db_message_send)
    session.commit()
    session.refresh(db_message_send)
    return db_message_send

# CommLog Endpoints
@router.get("/message-sends/{send_id}/comm-logs/", response_model=List[CommLog])
def read_comm_logs(send_id: int, session: Session = Depends(get_session)):
    message_send = session.get(MessageSendModel, send_id)
    if not message_send:
        raise HTTPException(status_code=404, detail="MessageSend not found")
    comm_logs = session.exec(select(CommLogModel).where(CommLogModel.send_id == send_id)).all()
    return comm_logs

@router.post("/message-sends/{send_id}/comm-logs/", response_model=CommLog)
def create_comm_log(send_id: int, comm_log: CommLogCreate, session: Session = Depends(get_session)):
    message_send = session.get(MessageSendModel, send_id)
    if not message_send:
        raise HTTPException(status_code=404, detail="MessageSend not found")
    client = session.get(ClientModel, comm_log.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if comm_log.send_id != send_id:
        raise HTTPException(status_code=400, detail="Send ID mismatch")
    db_comm_log = CommLogModel(**comm_log.dict(), logged_at=datetime.utcnow())
    session.add(db_comm_log)
    session.commit()
    session.refresh(db_comm_log)
    return db_comm_log

# Engagement Endpoints
@router.get("/campaigns/{campaign_id}/engagements/", response_model=List[Engagement])
def read_engagements(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    engagements = session.exec(select(EngagementModel).where(EngagementModel.campaign_id == campaign_id)).all()
    return engagements

@router.post("/campaigns/{campaign_id}/engagements/", response_model=Engagement)
def create_engagement(campaign_id: int, engagement: EngagementCreate, session: Session = Depends(get_session)):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if engagement.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Campaign ID mismatch")
    db_engagement = EngagementModel(**engagement.dict(), event_at=datetime.utcnow())
    session.add(db_engagement)
    session.commit()
    session.refresh(db_engagement)
    return db_engagement

# Feedback Endpoints
@router.get("/emails/{email_id}/feedbacks/", response_model=List[Feedback])
def read_feedbacks(email_id: int, session: Session = Depends(get_session)):
    email = session.get(EmailModel, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    feedbacks = session.exec(select(FeedbackModel).where(FeedbackModel.email_id == email_id)).all()
    return feedbacks



@router.post("/emails/{email_id}/feedbacks/", response_model=Feedback)
async def create_feedback(
    email_id: int,
    feedback: FeedbackCreate,
    session: Session = Depends(get_session)
):
    
    db_feedback = FeedbackModel(
        email_id=email_id,
        user_id=feedback.user_id,
        stage=feedback.stage,
        comments=feedback.comments,
        wants_change=feedback.wants_change,
        created_at=datetime.utcnow()
    )
    session.add(db_feedback)
    session.commit()
    session.refresh(db_feedback)

    
    if feedback.stage == "draft":
        draft = session.get(EmailDraftModel, email_id) or session.get(MessageDraftModel, email_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        campaign_id = draft.campaign_id
        strategy = session.exec(select(StrategyModel).where(StrategyModel.campaign_id == campaign_id)).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        channel = strategy.channel.lower()

        redraft_phase.invoke({
            "draft_id": email_id,
            "needs_rewrite": feedback.wants_change,
            "fb_comments": feedback.comments,
            "channel": channel
        })

    
    elif feedback.stage == "approved":
        draft = session.get(EmailDraftModel, email_id)
        is_email = True
        if not draft:
            draft = session.get(MessageDraftModel, email_id)
            if not draft:
                raise HTTPException(status_code=404, detail="Draft not found")
            is_email = False

        
        if is_email:
            from agents.email_personaliser_agent import EmailPersonaliserAgent
            EmailPersonaliserAgent().invoke({"draft_id": draft.draft_id})
        else:
            from agents.message_personaliser_agent import MessagePersonaliserAgent
            MessagePersonaliserAgent().invoke({"draft_id": draft.draft_id})

    else:
        raise HTTPException(status_code=400, detail="Invalid feedback stage")

    return db_feedback





# ContextQuestion Endpoints
@router.get("/clients/{client_id}/context-questions/", response_model=List[ContextQuestion])
def read_context_questions(client_id: int, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    questions = session.exec(select(ContextQuestionModel).where(ContextQuestionModel.client_id == client_id)).all()
    return questions





@router.post("/clients/{client_id}/context-questions/", response_model=List[ContextQuestion])
def create_context_questions(
    client_id: int,
    payload: ContextQuestionBatchCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    client = session.get(ClientModel, client_id)
    user = session.get(UserModel, payload.user_id)
    if not client or not user:
        raise HTTPException(status_code=404, detail="Client or User not found")
    if payload.client_id != client_id:
        raise HTTPException(status_code=400, detail="Client ID mismatch")
    if payload.user_id != client.user_id:
        raise HTTPException(status_code=400, detail="User does not own this client")
    now = datetime.utcnow()
    db_questions = []

    for qa in payload.qa_pairs:
        db_question = ContextQuestionModel(
            client_id=payload.client_id,
            user_id=payload.user_id,
            question=qa.question,
            answer=qa.answer,
            created_at=now
        )
        session.add(db_question)
        db_questions.append(db_question)

    session.commit()
    for q in db_questions:
        session.refresh(q)

    background_tasks.add_task(
        profile_graph.invoke,
        {"client_id": client_id},       
    )
    

    return db_questions

# ScrapedData Endpoints
@router.get("/clients/{client_id}/scraped-data/", response_model=List[ScrapedData])
def read_scraped_data(client_id: int, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    scraped_data = session.exec(select(ScrapedDataModel).where(ScrapedDataModel.client_id == client_id)).all()
    return scraped_data

@router.post("/clients/{client_id}/scraped-data/", response_model=ScrapedData)
def create_scraped_data(client_id: int, scraped_data: ScrapedDataCreate, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if scraped_data.client_id != client_id:
        raise HTTPException(status_code=400, detail="Client ID mismatch")
    db_scraped_data = ScrapedDataModel(**scraped_data.dict(), scraped_at=datetime.utcnow())
    session.add(db_scraped_data)
    session.commit()
    session.refresh(db_scraped_data)
    return db_scraped_data

# Communication Endpoints
@router.get("/clients/{client_id}/communications/", response_model=List[Communication])
def read_communications(client_id: int, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    communications = session.exec(select(CommunicationModel).where(CommunicationModel.client_id == client_id)).all()
    return communications




@router.post("/clients/{client_id}/communications/", response_model=Communication)
def create_communication(
    client_id: int,
    communication: CommunicationCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    client = session.get(ClientModel, client_id)
    user = session.get(UserModel, communication.user_id)
    if not client or not user:
        raise HTTPException(status_code=404, detail="Client or User not found")
    if communication.client_id != client_id:
        raise HTTPException(status_code=400, detail="Client ID mismatch")
    if communication.user_id != client.user_id:
        raise HTTPException(status_code=400, detail="User does not own this client")

    db_communication = CommunicationModel(**communication.dict(), timestamp=datetime.utcnow())
    session.add(db_communication)
    session.commit()
    session.refresh(db_communication)

    
    campaign = session.exec(
        select(CampaignModel).where(CampaignModel.client_id == client_id)
    ).first()

    if campaign:
        background_tasks.add_task(
            strategy_graph.invoke,
            {"client_id": client_id, "campaign_id": campaign.campaign_id}   
        )
    else:
        print(f" No campaign found for client_id={client_id}, strategy_graph not invoked.")

    return db_communication




    

