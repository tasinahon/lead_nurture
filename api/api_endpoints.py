from fastapi import FastAPI, Depends, HTTPException,BackgroundTasks
from graph.strategy_graph import strategy_graph
from sqlmodel import Session, select
from fastapi import APIRouter
from agents.scraper_agent import ScraperAgent 
from agents.campaign_planner_agent import CampaignPlannerAgent
from agents.draft_email_agent import EmailDraftAgent
from agents.draft_message_agent import DraftMessageAgent
from agents.redraft_agent import RedraftAgent
from agents.email_personaliser_agent import PersonaliserAgent
from agents.message_personaliser_agent import MessagePersonaliserAgent
from agents.profile_update_agent import ProfileUpdateAgent
from graph.profile_graph import profile_graph
# from graph.personalise_graph import personalise_phase
from typing import List
from datetime import datetime
from db.session import get_session
from graph.scrape_graph import flow
# from graph.redraft_graph import redraft_phase
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
    Communication, CommunicationCreate,
    ClientListLink,ClientList,
    ClientListCreate,InitialStrategyCreate,InitialStrategy
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
    Communication as CommunicationModel,
    ClientList as ClientListModel,
    ClientListLink as ClientListLinkModel,
    InitialStrategy as InitialStrategyModel,
    CampaignPlan as CampaignPlanModel
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



@router.post("/emails/{email_id}/feedbacks/", response_model=FeedbackModel)
async def create_feedback(
    email_id: int,
    feedback: FeedbackCreate,
    session: Session = Depends(get_session)
):
    # 1. Save feedback entry
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

    
    draft = session.get(EmailDraftModel, email_id)
    is_email = True

    if not draft:
        draft = session.get(MessageDraftModel, email_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        is_email = False

    
    if feedback.stage == "draft":
        strategy = session.exec(
            select(InitialStrategyModel).where(InitialStrategyModel.client_id == draft.contact_id)
        ).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Initial strategy not found")

        channel = strategy.engagement_channel.lower()

        if feedback.wants_change:
            RedraftAgent().invoke({
                "draft_id": draft.draft_id,
                "fb_comments": feedback.comments,
                "channel": channel
            })

    
    elif feedback.stage == "approved":
        if feedback.wants_change:
            if is_email:
                PersonaliserAgent().invoke({
                    "draft_id": draft.draft_id,
                    "feedback": feedback.comments
                })
            else:
                MessagePersonaliserAgent().invoke({
                    "draft_id": draft.draft_id,
                    "feedback": feedback.comments
                })
        else:
            if is_email:
                db_email = EmailModel(
                    draft_id=draft.draft_id,
                    personalized_body=draft.body_markdown,
                    is_final=True,
                    approved_at=datetime.utcnow()
                )
                session.add(db_email)
            else:
                db_msg = MessageModel(
                    draft_id=draft.draft_id,
                    personalized_text=draft.message_text,
                    is_final=True,
                    approved_at=datetime.utcnow()
                )
                session.add(db_msg)

            session.commit()

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

    # if campaign:
    #     background_tasks.add_task(
    #         strategy_graph.invoke,
    #         {"client_id": client_id, "campaign_id": campaign.campaign_id}   
    #     )
    # else:
    #     print(f" No campaign found for client_id={client_id}, strategy_graph not invoked.")

    return db_communication


# 1. Get All Client Lists for a User
@router.get("/users/{user_id}/client-lists/", response_model=List[ClientList])
def read_client_lists(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return session.exec(select(ClientListModel).where(ClientListModel.user_id == user_id)).all()

#  Create a New Client List
@router.post("/users/{user_id}/client-lists/", response_model=ClientList)
def create_client_list(user_id: int, list_data: ClientListCreate, session: Session = Depends(get_session)):
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db_list = ClientListModel(**list_data.dict(), user_id=user_id)
    session.add(db_list)
    session.commit()
    session.refresh(db_list)
    return db_list

#  Add a Client to a List
@router.post("/client-lists/{list_id}/add-client/{client_id}")
def add_client_to_list(list_id: int, client_id: int, session: Session = Depends(get_session)):
    client = session.get(ClientModel, client_id)
    clist = session.get(ClientListModel, list_id)
    if not client or not clist:
        raise HTTPException(status_code=404, detail="Client or List not found")

    link = ClientListLinkModel(client_id=client_id, list_id=list_id)
    session.add(link)
    session.commit()
    return {"status": "linked", "client_id": client_id, "list_id": list_id}

# Get All Clients in a Client List
@router.get("/client-lists/{list_id}/clients/", response_model=List[Client])
def get_clients_in_list(list_id: int, session: Session = Depends(get_session)):
    links = session.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == list_id)).all()
    client_ids = [l.client_id for l in links]
    return session.exec(select(ClientModel).where(ClientModel.client_id.in_(client_ids))).all()

#  Create Campaign (single client or list)
@router.post("/campaigns/", response_model=Campaign)
def create_campaign(campaign: CampaignCreate, session: Session = Depends(get_session)):
    user = session.get(UserModel, campaign.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not campaign.client_id and not campaign.clientlist_id:
        raise HTTPException(status_code=400, detail="Must provide either client_id or clientlist_id")

    if campaign.client_id:
        client = session.get(ClientModel, campaign.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.user_id != campaign.user_id:
            raise HTTPException(status_code=400, detail="Client does not belong to this user")

    if campaign.clientlist_id:
        clist = session.get(ClientListModel, campaign.clientlist_id)
        if not clist:
            raise HTTPException(status_code=404, detail="ClientList not found")

    db_campaign = CampaignModel(**campaign.dict(), created_at=datetime.utcnow())
    session.add(db_campaign)
    session.commit()
    session.refresh(db_campaign)
    return db_campaign




@router.post("/campaigns/{campaign_id}/start/")
def start_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    background_tasks.add_task(run_campaign_plan_and_drafts, campaign_id)
    return {"status": "started", "message": "Planner + Day 1 drafts queued."}


def run_campaign_plan_and_drafts(campaign_id: int):
    
    CampaignPlannerAgent().invoke({"campaign_id": campaign_id})

    with get_session() as s:
        campaign = s.get(CampaignModel, campaign_id)

        
        plan_days = s.exec(
            select(CampaignPlanModel).where(CampaignPlanModel.campaign_id == campaign_id)
        ).all()
        days = [p.day for p in plan_days]

        
        strategies = s.exec(select(StrategyModel).where(StrategyModel.campaign_id == campaign_id)).all()
        if not strategies:
            print(f"[INFO] No final strategies found. Falling back to InitialStrategy.")
            if campaign.client_id:
                initial = s.exec(select(InitialStrategyModel).where(InitialStrategyModel.client_id == campaign.client_id)).first()
                strategies = [initial] if initial else []
            elif campaign.clientlist_id:
                links = s.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == campaign.clientlist_id)).all()
                strategies = []
                for link in links:
                    initial = s.exec(select(InitialStrategyModel).where(InitialStrategyModel.client_id == link.client_id)).first()
                    if initial:
                        strategies.append(initial)

        
        channels = {
            s.channel.lower() if hasattr(s, "channel") else s.engagement_channel.lower()
            for s in strategies
        }

        
        targets = []
        if campaign.client_id:
            targets = [campaign.client_id]
        elif campaign.clientlist_id:
            links = s.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == campaign.clientlist_id)).all()
            targets = [l.client_id for l in links]

        # 6. Run draft agents for each day
        for client_id in targets:
            for day in days:
                if 'email' in channels:
                    EmailDraftAgent().invoke({
                        "campaign_id": campaign_id,
                        "contact_id": client_id,
                        "day": day
                    })
                if 'message' in channels:
                    DraftMessageAgent().invoke({
                        "campaign_id": campaign_id,
                        "contact_id": client_id,
                        "day": day
                    })



# @router.post("/users/{user_id}/clients/full-setup/")
# def full_contact_setup(
#     user_id: int,
#     data: FullContactSetupRequest,
#     session: Session = Depends(get_session)
# ):
#     # 1. Create or update client
#     client = Client(user_id=user_id, **data.client.dict())
#     session.add(client)
#     session.commit()
#     session.refresh(client)

#     # 2. Save context questions
#     if data.context_questions:
#         for qa in data.context_questions:
#             question = ContextQuestion(
#                 client_id=client.client_id,
#                 user_id=user_id,
#                 question=qa.question,
#                 answer=qa.answer
#             )
#             session.add(question)

#     # 3. Save communications
#     if data.communications:
#         for c in data.communications:
#             comm = Communication(
#                 client_id=client.client_id,
#                 user_id=user_id,
#                 content=c.content,
#                 channel=c.channel
#             )
#             session.add(comm)

#     session.commit()

#     # 4. Call profile builder agent
#     ProfileUpdateAgent().invoke({"client_id": client.client_id})

#     return {"status": "success", "client_id": client.client_id}




# def run_campaign_plan_and_drafts(campaign_id: int):
#     # 1. Generate plan
#     CampaignPlannerAgent().invoke({"campaign_id": campaign_id})


#     with get_session() as s:
#         campaign = s.get(CampaignModel, campaign_id)

#         # 2. Fetch strategies; fallback to InitialStrategy if none found
#         strategies = s.exec(select(StrategyModel).where(StrategyModel.campaign_id == campaign_id)).all()

#         if not strategies:
#             print(f"[INFO] No final strategies found. Falling back to InitialStrategy.")
#             if campaign.client_id:
#                 initial = s.exec(select(InitialStrategyModel).where(InitialStrategyModel.client_id == campaign.client_id)).first()

#                 strategies = [initial] if initial else []
#             elif campaign.clientlist_id:
#                 links = s.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == campaign.clientlist_id)).all()
#                 strategies = []
#                 for link in links:
#                     initial = s.exec(select(InitialStrategyModel).where(InitialStrategyModel.client_id == campaign.client_id)).first()
#                     if initial:
#                         strategies.append(initial)

#         # 3. Determine channels from strategy data
#         channels = {s.channel.lower() if hasattr(s, "channel") else s.engagement_channel.lower() for s in strategies}
#         targets = []

#         if campaign.client_id:
#             targets = [campaign.client_id]
#         elif campaign.clientlist_id:
#             links = s.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == campaign.clientlist_id)).all()
#             targets = [l.client_id for l in links]

#         # 4. Run draft agents for Day 1
#         for client_id in targets:
#             for day in days:
#                 if 'email' in channels:
#                     EmailDraftAgent().invoke({
#                         "campaign_id": campaign_id,
#                         "contact_id": client_id,
#                         "day": day
#                     })
#                 if 'message' in channels:
#                     DraftMessageAgent().invoke({
#                         "campaign_id": campaign_id,
#                         "contact_id": client_id,
#                         "day": day
#                     })




@router.get("/clients/{client_id}/initial-strategy/", response_model=InitialStrategy)
def get_initial_strategy(client_id: int, session: Session = Depends(get_session)):
    strategy = session.exec(
        select(InitialStrategyModel).where(InitialStrategyModel.client_id == client_id)
    ).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Initial strategy not found")
    return strategy


@router.post("/clients/{client_id}/initial-strategy/", response_model=InitialStrategy)
def create_initial_strategy(
    client_id: int,
    strategy: InitialStrategyCreate,
    session: Session = Depends(get_session)
):
    if strategy.client_id != client_id:
        raise HTTPException(status_code=400, detail="Client ID mismatch")

    db_strategy = InitialStrategyModel(**strategy.dict(), generated_at=datetime.utcnow())
    session.add(db_strategy)
    session.commit()
    session.refresh(db_strategy)
    return db_strategy










# @router.post("/campaigns/{campaign_id}/start/")
# def start_campaign(campaign_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")

#     # Add planner + draft job to background
#     background_tasks.add_task(run_campaign_plan_and_drafts, campaign_id)
#     return {"status": "started", "message": "Planning + Day 1 draft generation triggered."}


# def run_campaign_plan_and_drafts(campaign_id: int):
#     # 1. Generate multi-day plan
#     CampaignPlannerAgent().invoke({"campaign_id": campaign_id})

#     with get_session() as s:
#         campaign = s.get(CampaignModel, campaign_id)

#         if campaign.client_id:
#             # 2a. For individual contact
#             EmailDraftAgent().invoke({
#                 "campaign_id": campaign_id,
#                 "contact_id": campaign.client_id,
#                 "day": "Day 1"
#             })

#         elif campaign.clientlist_id:
#             # 2b. For each client in list
#             links = s.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == campaign.clientlist_id)).all()
#             for link in links:
#                 EmailDraftAgent().invoke({
#                     "campaign_id": campaign_id,
#                     "contact_id": link.client_id,
#                     "day": "Day 1"
#                 })




    
# @router.post("/campaigns/{campaign_id}/start/")
# def start_campaign(campaign_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")

#     background_tasks.add_task(run_campaign_plan_and_drafts, campaign_id)
#     return {"status": "started", "message": "Planner + Day 1 drafts queued."}


# def run_campaign_plan_and_drafts(campaign_id: int):
#     # 1. Generate plan
#     CampaignPlannerAgent().invoke({"campaign_id": campaign_id})

#     with get_session() as s:
#         campaign = s.get(CampaignModel, campaign_id)
#         strategies = s.exec(select(StrategyModel).where(StrategyModel.campaign_id == campaign_id)).all()

#         channels = {s.channel.lower() for s in strategies}
#         targets = []

#         if campaign.client_id:
#             targets = [campaign.client_id]
#         elif campaign.clientlist_id:
#             links = s.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == campaign.clientlist_id)).all()
#             targets = [l.client_id for l in links]

#         for client_id in targets:
#             if 'email' in channels:
#                 EmailDraftAgent().invoke({
#                     "campaign_id": campaign_id,
#                     "contact_id": client_id,
#                     "day": "Day 1"
#                 })
#             if 'message' in channels:
#                 DraftMessageAgent().invoke({
#                     "campaign_id": campaign_id,
#                     "contact_id": client_id,
#                     "day": "Day 1"
#                 })




    
