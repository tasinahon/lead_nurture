import time
from fastapi import FastAPI, Depends, HTTPException,BackgroundTasks
from agents.email_finder_agent import find_email_via_agent
from agents.initial_strategy_agent import InitialStrategyAgent
from graph.strategy_graph import strategy_graph
from sqlmodel import Session, select, func
from fastapi import APIRouter
from db.session import SessionLocal
from pydantic import BaseModel, Field
from typing import Optional, List
from agents.scraper_agent import ScraperAgent 
from agents.campaign_planner_agent import CampaignPlannerAgent
from agents.draft_email_agent import EmailDraftAgent
from agents.draft_message_agent import DraftMessageAgent
from agents.redraft_agent import RedraftAgent
from agents.email_personaliser_agent import PersonaliserAgent
from agents.message_personaliser_agent import MessagePersonaliserAgent
from agents.profile_update_agent import ProfileUpdateAgent
from agents.email_sender_agent import EmailSenderAgent
# from agents.whatsapp_sender_agent import WhatsAppSenderAgent
from agents.introductory_email_agent import IntroductoryEmailAgent
from agents.email_reply_agent import EmailReplyDetectionAgent
from agents.immediate_reply_agent import ImmediateReplyAgent
from graph.profile_graph import profile_graph
# from graph.personalise_graph import personalise_phase
from typing import List, Dict, Any
from typing import Set

from datetime import datetime
from db.session import get_session
from graph.scrape_graph import flow
import traceback
from sqlalchemy import select, exists, and_
# from graph.redraft_graph import redraft_phase
import logging
from db.Pydantic_DataModels import (
    ClientWithProfiles, CombinedOut, ContextQuestionBatchCreate, User, UserCreate,
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
    ClientListCreate,InitialStrategyCreate,InitialStrategy,
    FullContactSetupRequest
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
    CampaignClientLink as CampaignClientLinkModel,
    CampaignPlan as CampaignPlanModel,
    CampaignExecution as CampaignExecutionModel,
    IntroductoryEmail as IntroductoryEmailModel,
    LeadScoringConfig,
    LeadPerformance,
    LeadScore,
    CampaignMetrics,
    ActivityLog
)

# router = FastAPI()
router=APIRouter()

# Include scheduler endpoints
from api.scheduler_endpoints import scheduler_router
router.include_router(scheduler_router)

# ============================================================================
# PYDANTIC REQUEST MODELS FOR SWAGGER UI
# ============================================================================

class UpdateFieldRequest(BaseModel):
    """Request model for updating a single field"""
    value: str = Field(..., description="The new value for the field", example="Updated title for day 1")

class ApprovalRequest(BaseModel):
    """Request model for campaign approval"""
    feedback: Optional[str] = Field(None, description="Optional feedback about the campaign", example="Campaign looks great!")
    approved_days: Optional[List[int]] = Field(None, description="List of day numbers to approve (if not provided, all days will be approved)", example=[1, 2, 3, 4, 5])

class RejectionRequest(BaseModel):
    """Request model for campaign rejection"""
    feedback: str = Field(..., description="Required feedback explaining why the campaign was rejected", example="Please adjust the tone for day 3 and make day 5 more engaging")

class SuggestionRequest(BaseModel):
    """Request model for user suggestions/modifications"""
    suggestion: str = Field(..., description="Natural language suggestion for improvement", example="Make the title more engaging and add urgency to day 3")
    day: Optional[int] = Field(None, description="Specific day to modify (if not provided, AI will determine from suggestion)", example=3)
    field: Optional[str] = Field(None, description="Specific field to modify: title, subject, objective, content", example="title")

class GenerateDayEmailRequest(BaseModel):
    """Request model for generating day-wise email content"""
    day: int = Field(..., description="The day number for which to generate email content (1-5)", example=1, ge=1, le=5)

# ============================================================================
# USER ENDPOINTS
# ============================================================================
@router.get("/users/", response_model=List[User])
def read_users(session: Session = Depends(get_session)):
    users = session.exec(select(UserModel)).scalars().all()
    return list(users)

@router.post("/users/", response_model=User)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = UserModel(**user.dict(), created_at=datetime.utcnow())
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.put("/users/{user_id}/company-info/", response_model=User)
def update_user_company_info(
    user_id: int,
    company_data: Dict[str, str],
    session: Session = Depends(get_session)
):
    """Update user's company information for introductory emails"""
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update company fields
    if "company_name" in company_data:
        user.company_name = company_data["company_name"]
    if "company_description" in company_data:
        user.company_description = company_data["company_description"]
    if "company_website" in company_data:
        user.company_website = company_data["company_website"]
    if "job_title" in company_data:
        user.job_title = company_data["job_title"]
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# Client Endpoints
@router.get("/users/{user_id}/clients/", response_model=List[Client])
def read_clients(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use session.query() to get proper ORM objects
    clients = session.query(ClientModel).filter(ClientModel.user_id == user_id).all()

    # Convert database models to Pydantic models explicitly
    return [
        Client(
            client_id=client.client_id,
            user_id=client.user_id,
            full_name=client.full_name,
            company=client.company,
            email=client.email,
            phone=client.phone,
            company_website=client.company_website,
            linkedin_url=client.linkedin_url,
            facebook=client.facebook,
            instagram=client.instagram,
            whatsapp=client.whatsapp,
            category=client.category,
            created_at=client.created_at
        )
        for client in clients
    ]





@router.post("/users/{user_id}/clients/", response_model=Client)
def create_client(user_id: int, client: ClientCreate, session: Session = Depends(get_session)):
    user = session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if client.user_id != user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")

    

    
    if client.email=="" and client.full_name and client.linkedin_url:
        email = find_email_via_agent(client.full_name, client.linkedin_url)
        if email:  # This checks that email is not None or empty
            client.email = email

    

    db_client = ClientModel(**client.dict(), created_at=datetime.utcnow())
    session.add(db_client)
    session.commit()
    session.refresh(db_client)

    try:
        flow.invoke({"client_id": db_client.client_id}) 
    except Exception as e:
        print(f"Graph failed {db_client.client_id}: {e}")

    return db_client






@router.get("/clients/{client_id}/profiles/")
def read_profiles(client_id: int, session: Session = Depends(get_session)):
    try:
        client = session.get(ClientModel, client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Use session.query instead of session.exec for better object access
        profiles = session.query(ProfileModel).filter(ProfileModel.client_id == client_id).all()

        # Simple response without complex serialization
        return {
            "client_id": client_id,
            "client_name": client.full_name,
            "profile_count": len(profiles),
            "profiles": [
                {
                    "profile_id": p.profile_id,
                    "client_id": p.client_id,
                    "summary": p.summary[:200] + "..." if len(p.summary) > 200 else p.summary,
                    "interests": p.interests,
                    "preferred_language": p.preferred_language,
                    "preferred_contact": p.preferred_contact,
                    "engagement_times": p.engagement_times or "",
                    "full_text": p.full_text[:100] + "..." if p.full_text and len(p.full_text) > 100 else (p.full_text or "")
                }
                for p in profiles
            ]
        }
    except Exception as e:
        print(f"Error in read_profiles: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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
    return list(campaigns)



# EmailDraft Endpoints
# @router.get("/campaigns/{campaign_id}/email-drafts/", response_model=List[EmailDraft])
# def read_email_drafts(campaign_id: int, session: Session = Depends(get_session)):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
#     email_drafts = session.exec(select(EmailDraftModel).where(EmailDraftModel.campaign_id == campaign_id)).all()
#     return email_drafts




# Message Draft
# @router.get("/campaigns/{campaign_id}/message-drafts/", response_model=List[MessageDraft])
# def read_message_drafts(campaign_id: int, session: Session = Depends(get_session)):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
#     message_drafts = session.exec(
#         select(MessageDraftModel).where(MessageDraftModel.campaign_id == campaign_id)
#     ).all()
#     return message_drafts

# Email Endpoints
# @router.get("/email-drafts/{draft_id}/emails/", response_model=List[Email])
# def read_emails(draft_id: int, session: Session = Depends(get_session)):
#     draft = session.get(EmailDraftModel, draft_id)
#     if not draft:
#         raise HTTPException(status_code=404, detail="EmailDraft not found")
#     emails = session.exec(select(EmailModel).where(EmailModel.draft_id == draft_id)).all()
#     return emails



# MessageSend Endpoints
# @router.get("/emails/{email_id}/message-sends/", response_model=List[MessageSend])
# def read_message_sends(email_id: int, session: Session = Depends(get_session)):
#     email = session.get(EmailModel, email_id)
#     if not email:
#         raise HTTPException(status_code=404, detail="Email not found")
#     message_sends = session.exec(select(MessageSendModel).where(MessageSendModel.email_id == email_id)).all()
#     return message_sends

# @router.post("/emails/{email_id}/message-sends/", response_model=MessageSend)
# def create_message_send(email_id: int, message_send: MessageSendCreate, session: Session = Depends(get_session)):
#     email = session.get(EmailModel, email_id)
#     if not email:
#         raise HTTPException(status_code=404, detail="Email not found")
#     if message_send.email_id != email_id:
#         raise HTTPException(status_code=400, detail="Email ID mismatch")
#     db_message_send = MessageSendModel(**message_send.dict(), sent_at=datetime.utcnow())
#     session.add(db_message_send)
#     session.commit()
#     session.refresh(db_message_send)
#     return db_message_send

# CommLog Endpoints
# @router.get("/message-sends/{send_id}/comm-logs/", response_model=List[CommLog])
# def read_comm_logs(send_id: int, session: Session = Depends(get_session)):
#     message_send = session.get(MessageSendModel, send_id)
#     if not message_send:
#         raise HTTPException(status_code=404, detail="MessageSend not found")
#     comm_logs = session.exec(select(CommLogModel).where(CommLogModel.send_id == send_id)).all()
#     return comm_logs

# @router.post("/message-sends/{send_id}/comm-logs/", response_model=CommLog)
# def create_comm_log(send_id: int, comm_log: CommLogCreate, session: Session = Depends(get_session)):
#     message_send = session.get(MessageSendModel, send_id)
#     if not message_send:
#         raise HTTPException(status_code=404, detail="MessageSend not found")
#     client = session.get(ClientModel, comm_log.client_id)
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
#     if comm_log.send_id != send_id:
#         raise HTTPException(status_code=400, detail="Send ID mismatch")
#     db_comm_log = CommLogModel(**comm_log.dict(), logged_at=datetime.utcnow())
#     session.add(db_comm_log)
#     session.commit()
#     session.refresh(db_comm_log)
#     return db_comm_log

# Engagement Endpoints
# @router.get("/campaigns/{campaign_id}/engagements/", response_model=List[Engagement])
# def read_engagements(campaign_id: int, session: Session = Depends(get_session)):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
#     engagements = session.exec(select(EngagementModel).where(EngagementModel.campaign_id == campaign_id)).all()
#     return engagements

# @router.post("/campaigns/{campaign_id}/engagements/", response_model=Engagement)
# def create_engagement(campaign_id: int, engagement: EngagementCreate, session: Session = Depends(get_session)):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
#     if engagement.campaign_id != campaign_id:
#         raise HTTPException(status_code=400, detail="Campaign ID mismatch")
#     db_engagement = EngagementModel(**engagement.dict(), event_at=datetime.utcnow())
#     session.add(db_engagement)
#     session.commit()
#     session.refresh(db_engagement)
#     return db_engagement

# Feedback Endpoints
# @router.get("/emails/{email_id}/feedbacks/", response_model=List[Feedback])
# def read_feedbacks(email_id: int, session: Session = Depends(get_session)):
#     email = session.get(EmailModel, email_id)
#     if not email:
#         raise HTTPException(status_code=404, detail="Email not found")
#     feedbacks = session.exec(select(FeedbackModel).where(FeedbackModel.email_id == email_id)).all()
#     return feedbacks



# @router.post("/emails/{email_id}/feedbacks/", response_model=FeedbackModel)
# async def create_feedback(
#     email_id: int,
#     feedback: FeedbackCreate,
#     session: Session = Depends(get_session)
# ):
#     # 1. Save feedback entry
#     db_feedback = FeedbackModel(
#         email_id=email_id,
#         user_id=feedback.user_id,
#         stage=feedback.stage,
#         comments=feedback.comments,
#         wants_change=feedback.wants_change,
#         created_at=datetime.utcnow()
#     )
#     session.add(db_feedback)
#     session.commit()
#     session.refresh(db_feedback)

    
#     # draft = session.get(EmailDraftModel, email_id)
#     # is_email = True

#     # if not draft:
#     draft = session.get(MessageDraftModel, email_id)
#     if not draft:
#         raise HTTPException(status_code=404, detail="Draft not found")
#     is_email = False

    
#     if feedback.stage == "draft":
#         strategy = session.exec(
#             select(InitialStrategyModel).where(InitialStrategyModel.client_id == draft.contact_id)
#         ).scalars().first()
#         if not strategy:
#             raise HTTPException(status_code=404, detail="Initial strategy not found")

#         channel = strategy.engagement_channel.lower()

#         if feedback.wants_change:
#             RedraftAgent().invoke({
#                 "draft_id": draft.draft_id,
#                 "fb_comments": feedback.comments,
#                 "channel": channel
#             })

    
#     elif feedback.stage == "approved":
#         if not feedback.wants_change:
            
#             if is_email:
#                 db_email = EmailModel(
#                     draft_id=draft.draft_id,
#                     subject=draft.subject,
#                     personalized_body=draft.body_markdown,
#                     is_final=True,
#                     approved_at=datetime.utcnow()
#                 )
#                 session.add(db_email)
#             else:
                
#                 db_msg = MessageModel(
#                     draft_id=draft.draft_id,
#                     personalized_text=draft.message_text,
#                     is_final=True,
#                     approved_at=datetime.utcnow()
#                 )
#                 session.add(db_msg)

#             session.commit()

#     else:
#         raise HTTPException(status_code=400, detail="Invalid feedback stage")
    
#     if is_email:
#         sender = EmailSenderAgent()
#         if sender.all_emails_approved(draft.campaign_id):
#             sender.schedule_emails(draft.campaign_id)
#     # else:
#     #     wa_sender = WhatsAppSenderAgent()
#     #     if wa_sender.all_messages_approved(draft.campaign_id):
#     #         await wa_sender.send_messages_now(draft.campaign_id)

#     return db_feedback





# ContextQuestion Endpoints
# @router.get("/clients/{client_id}/context-questions/", response_model=List[ContextQuestion])
# def read_context_questions(client_id: int, session: Session = Depends(get_session)):
#     client = session.get(ClientModel, client_id)
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
#     questions = session.exec(select(ContextQuestionModel).where(ContextQuestionModel.client_id == client_id)).all()
#     return questions



# get mails/messages of certain day of a campaign

# @router.get("/campaigns/{campaign_id}/day/{day}/comms/", response_model=CombinedOut)
# def get_emails_and_messages_by_campaign_and_day(
#     campaign_id: int,
#     day: int,
#     session: Session = Depends(get_session)
# ):
   

#     # if not final_emails:
#     final_emails = (
#             session.query(EmailDraftModel)
#             .filter(EmailDraftModel.campaign_id == campaign_id, EmailDraftModel.day == day)
#             .all()
#         )

#     # if not final_messages:
#     final_messages = (
#             session.query(MessageDraftModel)
#             .filter(MessageDraftModel.campaign_id == campaign_id, MessageDraftModel.day == day)
#             .all()
#         )

#     return {
#         "emails": final_emails or [],
#         "messages": final_messages or []
#     }






    

#     return db_questions

# ScrapedData Endpoints
# @router.get("/clients/{client_id}/scraped-data/", response_model=List[ScrapedData])
# def read_scraped_data(client_id: int, session: Session = Depends(get_session)):
#     client = session.get(ClientModel, client_id)
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
#     scraped_data = session.exec(select(ScrapedDataModel).where(ScrapedDataModel.client_id == client_id)).all()
#     return scraped_data

# @router.post("/clients/{client_id}/scraped-data/", response_model=ScrapedData)
# def create_scraped_data(client_id: int, scraped_data: ScrapedDataCreate, session: Session = Depends(get_session)):
#     client = session.get(ClientModel, client_id)
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
#     if scraped_data.client_id != client_id:
#         raise HTTPException(status_code=400, detail="Client ID mismatch")
#     db_scraped_data = ScrapedDataModel(**scraped_data.dict(), scraped_at=datetime.utcnow())
#     session.add(db_scraped_data)
#     session.commit()
#     session.refresh(db_scraped_data)
#     return db_scraped_data

# Communication Endpoints
# @router.get("/clients/{client_id}/communications/", response_model=List[Communication])
# def read_communications(client_id: int, session: Session = Depends(get_session)):
#     client = session.get(ClientModel, client_id)
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
#     communications = session.exec(select(CommunicationModel).where(CommunicationModel.client_id == client_id)).all()
#     return communications






# 1. Get All Client Lists for a User
# @router.get("/users/{user_id}/client-lists/", response_model=List[ClientList])
# def read_client_lists(user_id: int, session: Session = Depends(get_session)):
#     user = session.get(UserModel, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     stmt = select(ClientListModel)

#     client_lists = session.exec(stmt).scalars().all()
#     return client_lists
#     # return session.exec(select(ClientListModel)).all()

# #  Create a New Client List
# @router.post("/users/{user_id}/client-lists/", response_model=ClientList)
# def create_client_list(user_id: int, list_data: ClientListCreate, session: Session = Depends(get_session)):
#     user = session.get(UserModel, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     db_list = ClientListModel(**list_data.dict(), user_id=user_id)
#     session.add(db_list)
#     session.commit()
#     session.refresh(db_list)
#     return db_list

# #  Add a Client to a List
# @router.post("/client-lists/{list_id}/add-client/{client_id}")
# def add_client_to_list(list_id: int, client_id: int, session: Session = Depends(get_session)):
#     client = session.get(ClientModel, client_id)
#     clist = session.get(ClientListModel, list_id)
#     if not client or not clist:
#         raise HTTPException(status_code=404, detail="Client or List not found")

#     link = ClientListLinkModel(client_id=client_id, list_id=list_id)
#     session.add(link)
#     session.commit()
#     return {"status": "linked", "client_id": client_id, "list_id": list_id}


# # Remove a Client from a Client List
# @router.delete("/client-lists/{list_id}/remove-client/{client_id}")
# def remove_client_from_list(list_id: int, client_id: int, session: Session = Depends(get_session)):
#     link = session.exec(
#         select(ClientListLinkModel).where(
#             ClientListLinkModel.list_id == list_id,
#             ClientListLinkModel.client_id == client_id
#         )
#     ).first()

#     if not link:
#         raise HTTPException(status_code=404, detail="Client not linked to list")

#     session.delete(link)
#     session.commit()
#     return {"status": "unlinked", "client_id": client_id, "list_id": list_id}


# # Get All Clients in a Client List
# @router.get("/client-lists/{list_id}/clients/", response_model=List[Client])
# def get_clients_in_list(list_id: int, session: Session = Depends(get_session)):
#     links = session.exec(select(ClientListLinkModel).where(ClientListLinkModel.list_id == list_id)).all()
#     client_ids = [l.client_id for l in links]
#     return session.exec(select(ClientModel).where(ClientModel.client_id.in_(client_ids))).all()



# new create campaign
# @router.post("/campaigns/", response_model=Campaign)
# def create_campaign(
#     campaign: CampaignCreate,
#     session: Session = Depends(get_session)
# ):
#     # Validate user exists
#     user = session.get(UserModel, campaign.user_id)
#     if not user:
#         raise HTTPException(404, "User not found")

#     # Validate client exists
#     client = session.get(ClientModel, campaign.client_id)
#     if not client:
#         raise HTTPException(404, "Client not found")

#     # ✅ Create the campaign with direct client relationship - SUPER SIMPLE!
#     db_campaign = CampaignModel(
#         user_id=campaign.user_id,
#         client_id=campaign.client_id,  # Direct relationship - no complex joins!
#         name=campaign.name,
#         description=campaign.description,
#         tags=campaign.tags,
#         created_at=datetime.utcnow(),
#         status="draft",  # Start as draft
#         approval_status="pending_approval"
#     )
#     session.add(db_campaign)
#     session.flush()  # ensures campaign_id is set
    
#     # No need for complex linking - the campaign already has direct client_id! 🎉

#     # ✅ Commit the transaction manually
#     session.commit()
#     session.refresh(db_campaign)
#     return db_campaign







# # start campaign
# @router.post("/campaigns/{campaign_id}/start/")
# def start_campaign(
#     campaign_id: int,
#     background_tasks: BackgroundTasks,
#     session: Session = Depends(get_session)
# ):
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")

#     background_tasks.add_task(run_campaign_plan_and_drafts, campaign_id)
#     return {"status": "started", "message": "Planner + Day 1 drafts queued."}



# def run_campaign_plan_and_drafts(campaign_id: int) -> None:
#     CampaignPlannerAgent().invoke({"campaign_id": campaign_id})

#     with SessionLocal() as s:
#         print("Hello--------------------------------------")

#         campaign = s.get(CampaignModel, campaign_id)
#         if campaign is None:
#             print(f"[WARN] Campaign {campaign_id} not found, aborting.")
#             return

#         days = [
#             row.day for row in
#             s.exec(
#                 select(CampaignPlanModel.day)
#                 .where(CampaignPlanModel.campaign_id == campaign_id)
#             )
#         ]
#         print("DAYS----")
#         print(f"[DEBUG] Campaign days: {days}")
#         if not days:
#             print(f"[WARN] No plan days for campaign {campaign_id}.")
#             return

#         client_ids = [
#             row.client_id for row in
#             s.exec(
#                 select(CampaignClientLinkModel.client_id)
#                 .where(CampaignClientLinkModel.campaign_id == campaign_id)
#             )
#         ]
#         print("CLIENT______")
#         print(f"[DEBUG] Client IDs: {client_ids}")

#         def draft_exists(model, cid: int, day: int) -> bool:
#             return s.exec(
#                 select(exists().where(
#                     and_(
#                         model.campaign_id == campaign_id,
#                         model.contact_id == cid,
#                         model.day == day
#                     )
#                 ))
#             ).scalar()

#         for cid in client_ids:
#             strat = s.exec(
#                 select(InitialStrategyModel)
#                 .where(InitialStrategyModel.client_id == cid)
#             ).scalars().first()

#             print(f"[DEBUG] Raw strat for client {cid} → {strat}")

#             if strat and strat.engagement_channel:
#                 channel = (strat.engagement_channel or "").strip().lower()
#             else:
#                 channel = "message"

#             print(f"[DEBUG] Strategy for client {cid} → channel = {channel}")


#             for day in days:
#                 if channel == "email":
#                     print("LOL--------------------------------------")
#                     if not draft_exists(EmailDraftModel, cid, day):
#                         print("LOL2222--------------------------------------")
#                         print(f"[INFO] Email draft → c{cid} d{day}")
#                         EmailDraftAgent().invoke(
#                             {"campaign_id": campaign_id,
#                              "contact_id": cid,
#                              "day": day}
#                         )
#                 else:
#                     if not draft_exists(MessageDraftModel, cid, day):
#                         print(f"[INFO] Message draft → c{cid} d{day}")
#                         DraftMessageAgent().invoke(
#                             {"campaign_id": campaign_id,
#                              "contact_id": cid,
#                              "day": day}
#                         )


# ============ NEW BRM WORKFLOW ENDPOINTS ============

# Send Introductory Email (from workflow)
@router.post("/clients/{client_id}/send-intro-email/")
def send_introductory_email(
    client_id: int,
    user_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """Send introductory email with parameters from BRM workflow"""
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Create intro email
    result = IntroductoryEmailAgent().invoke({
        "client_id": client_id,
        "user_id": user_id
    })
    
    return {
        "status": result["status"],
        "draft_id": result["draft_id"],
        "email_id": result.get("email_id"),
        "sent_to": result.get("sent_to"),
        "subject": result["subject"],
        "message": f"Introductory email {'sent successfully' if result['status'] == 'intro_email_sent' else 'creation failed'}"
    }

# Check for email replies (Agent 4 from workflow)
@router.post("/emails/{email_id}/check-replies/")
def check_email_replies(
    email_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """Check if client replied to sent email and analyze sentiment"""
    email = session.get(EmailModel, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Check if this email has already been processed for replies (prevent duplicate processing)
    # Look for corresponding IntroductoryEmail record to check reply status
    from db.database_schema import IntroductoryEmail as IntroductoryEmailModel
    
    if email.draft_id:
        draft = session.get(EmailDraftModel, email.draft_id)
        if draft and draft.contact_id:
            intro_email = session.query(IntroductoryEmailModel).filter_by(
                client_id=draft.contact_id
            ).first()
            
            if intro_email and intro_email.replied:
                print(f"⏭️ Skipping reply check for email {email_id} - already marked as replied")
                return {
                    "status": "already_processed",
                    "message": "Email replies have already been processed",
                    "has_reply": True,
                    "email_id": email_id
                }
    
    # Run reply detection agent
    result = EmailReplyDetectionAgent().invoke({"email_id": email_id})
    
    if result["has_reply"]:
        # If reply found, trigger immediate reply preparation synchronously
        try:
            immediate_reply_agent = ImmediateReplyAgent()
            immediate_result = immediate_reply_agent.invoke({
                "client_id": result["client_id"],
                "client_reply_text": result["reply_text"],
                "sentiment_analysis": result["sentiment_analysis"]
            })
            result["immediate_reply"] = immediate_result
        except Exception as e:
            result["immediate_reply_error"] = str(e)
    
    return result

# Prepare immediate reply (from workflow) 
@router.post("/clients/{client_id}/prepare-immediate-reply/")
def prepare_immediate_reply(
    client_id: int,
    reply_data: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """Generate immediate reply based on client sentiment"""
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    result = ImmediateReplyAgent().invoke({
        "client_id": client_id,
        "client_reply_text": reply_data.get("reply_text", ""),
        "sentiment_analysis": reply_data.get("sentiment_analysis", {})
    })
    
    return result

# Check all sent emails for replies (bulk operation)
@router.post("/campaigns/{campaign_id}/monitor-replies/")  
def monitor_campaign_replies(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """Monitor all sent emails in campaign for replies"""
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get all sent emails in campaign
    sent_emails = session.exec(
        select(EmailModel, EmailDraftModel)
        .join(EmailDraftModel, EmailModel.draft_id == EmailDraftModel.draft_id)
        .where(
            EmailDraftModel.campaign_id == campaign_id,
            EmailModel.sent_at.isnot(None)
        )
    ).all()
    
    # Queue reply checking for each email
    for email, draft in sent_emails:
        background_tasks.add_task(
            EmailReplyDetectionAgent().invoke,
            {"email_id": email.email_id}
        )
    
    return {
        "status": "reply_monitoring_started",
        "emails_queued": len(sent_emails),
        "campaign_id": campaign_id
    }


# context-ques and communication both or either or
# @router.post("/users/{user_id}/clients/{client_id}/full-setup/")
# def full_contact_setup(
#     user_id: int,
#     client_id: int,
#     data: FullContactSetupRequest,
#     background_tasks: BackgroundTasks,
#     session: Session = Depends(get_session),
# ):
    
#     if data.context_questions:
#         for qa in data.context_questions:
#             question = ContextQuestionModel(
#                 client_id=client_id,
#                 user_id=user_id,
#                 question=qa.question,
#                 answer=qa.answer,
#                 created_at=datetime.utcnow()
#             )
#             session.add(question)

#     # 2. Save communications
#     if data.communications:
#         for c in data.communications:
#             comm = CommunicationModel(
#                 client_id=client_id,
#                 user_id=user_id,
#                 content=c.content,
#                 channel=c.channel,
#                 timestamp=datetime.utcnow()
#             )
#             session.add(comm)

#     session.commit()

    
#     background_tasks.add_task(ProfileUpdateAgent().invoke, {"client_id": client_id})
#     background_tasks.add_task(InitialStrategyAgent().invoke, {"client_id": client_id})

#     return {"status": "success", "client_id": client_id}








@router.get("/clients/{client_id}/initial-strategy/", response_model=InitialStrategy)
def get_initial_strategy(client_id: int, session: Session = Depends(get_session)):
    strategy = session.query(InitialStrategyModel).filter(
        InitialStrategyModel.client_id == client_id
    ).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Initial strategy not found")
    
    # Convert database model to Pydantic model explicitly
    return InitialStrategy(
        strategy_id=strategy.strategy_id,
        client_id=strategy.client_id,
        engagement_channel=strategy.engagement_channel,
        tone_style=strategy.tone_style,
        communication_frequency=strategy.communication_frequency,
        general_advice=strategy.general_advice,
        generated_at=strategy.generated_at
    )


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



# @router.get("/email-drafts/{draft_id}/final-email/", response_model=Email)
# def get_final_email_for_draft(draft_id: int, session: Session = Depends(get_session)):
#     draft = session.get(EmailDraftModel, draft_id)
#     if not draft:
#         raise HTTPException(status_code=404, detail="Draft not found")

#     final_email = session.exec(
#         select(EmailModel)
#         .where(EmailModel.draft_id == draft_id)
#         .where(EmailModel.is_final == True)
#     ).first()

#     if not final_email:
#         raise HTTPException(status_code=404, detail="Final email not found")

#     return final_email

# # ============ BRIGHTDATA SCRAPING ENDPOINTS ============

# @router.post("/clients/{client_id}/scrape-brightdata/")
# def trigger_brightdata_scraping(
#     client_id: int,
#     background_tasks: BackgroundTasks,
#     session: Session = Depends(get_session)
# ):
#     """Trigger BrightData LinkedIn scraping for a specific client"""
#     client = session.get(ClientModel, client_id)
#     if not client:
#         raise HTTPException(status_code=404, detail="Client not found")
    
#     if not client.linkedin_url:
#         raise HTTPException(status_code=400, detail="Client has no LinkedIn URL")
    
#     # Run BrightData scraping in background
#     from agents.scraper_agent import ScraperAgent
#     background_tasks.add_task(
#         ScraperAgent().invoke,
#         {"client_id": client_id}
#     )
    
#     return {
#         "status": "scraping_triggered",
#         "client_id": client_id,
#         "linkedin_url": client.linkedin_url,
#         "message": "BrightData scraping started in background"
#     }

# @router.post("/scrape-multiple-brightdata/")
# def trigger_multiple_brightdata_scraping(
#     linkedin_urls: List[str],
#     background_tasks: BackgroundTasks
# ):
#     """Trigger BrightData scraping for multiple LinkedIn URLs"""
#     from agents.scraper_agent import ScraperAgent
    
#     scraper = ScraperAgent()
#     result = scraper.trigger_brightdata_scraping(linkedin_urls)
    
#     return {
#         "status": result["status"],
#         "snapshot_id": result.get("snapshot_id"),
#         "urls_count": len(linkedin_urls),
#         "urls": linkedin_urls,
#         "message": f"BrightData scraping triggered for {len(linkedin_urls)} URLs"
#     }


# ============ ENHANCED BRM WORKFLOW ENDPOINTS ============

@router.post("/clients/{client_id}/generate-enhanced-strategy/")
def generate_enhanced_strategy(
    client_id: int,
    user_id: int = 1,
    session: Session = Depends(get_session)
):
    """
    Enhanced strategy generation following BRM workflow
    Agent 5: Setup Initial Approach Strategy
    """
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    from agents.enhanced_strategy_agent import EnhancedStrategyAgent
    strategy_agent = EnhancedStrategyAgent()
    result = strategy_agent.invoke({
        "client_id": client_id,
        "user_id": user_id
    })
    
    return result

@router.post("/clients/{client_id}/auto-create-campaign/")
def auto_create_campaign_for_client(
    client_id: int,
    immediate_reply_data: Dict[str, Any],
    user_id: int = 1,
    session: Session = Depends(get_session)
):
    """
    Automatically create campaign after immediate reply (Following BRM Workflow)
    This replaces manual campaign creation with intelligent auto-creation
    """
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    from agents.automatic_campaign_creator_agent import AutomaticCampaignCreatorAgent
    
    creator_agent = AutomaticCampaignCreatorAgent()
    result = creator_agent.invoke({
        "client_id": client_id,
        "user_id": user_id,
        "immediate_reply_context": immediate_reply_data
    })
    
    # Auto-generate campaign plan
    if result["status"] == "campaign_auto_created":
        from agents.enhanced_campaign_planner_agent import EnhancedCampaignPlannerAgent
        
        planner = EnhancedCampaignPlannerAgent()
        plan_result = planner.invoke({
            "campaign_id": result["campaign_id"]
        })
        
        result["plan_generated"] = True
        result["plan_details"] = plan_result
    
    return result

@router.get("/clients/{client_id}/auto-campaigns/")
def get_client_auto_campaigns(
    client_id: int,
    session: Session = Depends(get_session)
):
    """
    Get all auto-generated campaigns for a client
    """
    client = session.get(ClientModel, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Find campaigns directly for this client
    campaigns = session.query(CampaignModel).filter(CampaignModel.client_id == client_id).all()
    
    client_campaigns = []
    for campaign in campaigns:
        # Get campaign plan status
        plan_count = session.exec(
            select(CampaignPlanModel)
            .where(CampaignPlanModel.campaign_id == campaign.campaign_id)
        ).all()
        plan_count = len(plan_count)
        
        client_campaigns.append({
            "campaign_id": campaign.campaign_id,
            "name": campaign.name,
            "description": campaign.description,
            "tags": campaign.tags,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "has_plan": plan_count > 0,
            "plan_days": plan_count or 0,
            "status": "ready_for_approval" if plan_count > 0 else "planning_needed"
        })
    
    return {
        "client_id": client_id,
        "client_name": client.full_name,
        "auto_campaigns": client_campaigns,
        "total_campaigns": len(client_campaigns)
    }

@router.post("/campaigns/{campaign_id}/generate-enhanced-plan/")
def generate_enhanced_campaign_plan(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Generate comprehensive campaign plan for frontend approval
    Workflow: "Set up a campaign plan"
    """
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    from agents.enhanced_campaign_planner_agent import EnhancedCampaignPlannerAgent
    planner_agent = EnhancedCampaignPlannerAgent()
    result = planner_agent.invoke({"campaign_id": campaign_id})
    
    return result

@router.get("/campaigns/{campaign_id}/plan-for-approval/")
def get_campaign_plan_for_approval(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """
    Get campaign plan formatted for frontend approval interface
    """
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get all campaign plan days - use scalars() to get model instances
    plan_days = session.exec(
        select(CampaignPlanModel)
        .where(CampaignPlanModel.campaign_id == campaign_id)
        .order_by(CampaignPlanModel.day)
    ).scalars().all()
    
    if not plan_days:
        raise HTTPException(status_code=404, detail="No campaign plan found")
    
    # Format for frontend
    formatted_plan = {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "campaign_description": campaign.description,
        "total_days": len(plan_days),
        "created_at": campaign.created_at,
        "approval_status": campaign.approval_status,  # Use actual status from database
        "approved_at": campaign.approved_at.isoformat() if campaign.approved_at else None,
        "user_feedback": campaign.user_feedback,
        "daily_breakdown": [
            {
                "day": plan_day.day,
                "title": plan_day.title,
                "subject_line": plan_day.subject,
                "objective": plan_day.goal,
                "content_idea": plan_day.body_idea,
                "editable": True,
                "approved": False  # Default to not approved
            }
            for plan_day in plan_days
        ],
        "approval_status": "pending_review",
        "modification_options": {
            "can_modify_subjects": True,
            "can_modify_content": True,
            "can_add_days": True,
            "can_remove_days": True,
            "can_change_timing": True
        }
    }
    
    return formatted_plan

# @router.post("/campaigns/{campaign_id}/approve-plan/")
# def approve_campaign_plan(
#     campaign_id: int,
#     approval_data: Dict[str, Any],
#     session: Session = Depends(get_session)
# ):
#     """
#     Frontend approval workflow: "Get from frontend Approve or modify the campaign plan"
#     """
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     approved = approval_data.get("approved", False)
#     user_feedback = approval_data.get("user_feedback", "")
    
#     if approved:
#         # Plan approved - update campaign status and trigger draft generation
#         approved_days = approval_data.get("approved_days")
#         if not approved_days:
#             # Get all days if none specified
#             plan_days = session.exec(
#                 select(CampaignPlanModel.day)
#                 .where(CampaignPlanModel.campaign_id == campaign_id)
#             ).all()
#             approved_days = [day for day in plan_days]
        
#         # Update campaign approval status in database
#         import json
#         from datetime import datetime
        
#         campaign.approval_status = "approved"
#         campaign.approved_at = datetime.utcnow()
#         campaign.user_feedback = user_feedback
#         campaign.approved_days = json.dumps(approved_days)
        
#         session.add(campaign)
#         session.commit()
        
#         # Don't generate drafts immediately - wait for user to start campaign
#         return {
#             "status": "plan_approved",
#             "campaign_id": campaign_id,
#             "approved_days": approved_days,
#             "approved_at": campaign.approved_at.isoformat(),
#             "user_feedback": user_feedback,
#             "next_step": "start_campaign",
#             "message": f"Campaign plan approved for {len(approved_days)} days. Use /campaigns/{campaign_id}/start/ to activate campaign."
#         }
    
#     else:
#         # Plan needs modifications - update status but don't approve
#         campaign.approval_status = "rejected"
#         campaign.user_feedback = user_feedback
#         session.add(campaign)
#         session.commit()
        
#         return {
#             "status": "plan_rejected",
#             "campaign_id": campaign_id,
#             "user_feedback": user_feedback,
#             "modifications_requested": approval_data.get("modifications"),
#             "next_step": "await_modifications"
#         }



# @router.patch("/campaigns/{campaign_id}/days/{day}/title")
# def update_day_title(
#     campaign_id: int,
#     day: int,
#     update_data: UpdateFieldRequest,
#     session: Session = Depends(get_session)
# ):
#     """Update title for a specific day"""
#     plan_day = session.exec(
#         select(CampaignPlanModel)
#         .where(CampaignPlanModel.campaign_id == campaign_id)
#         .where(CampaignPlanModel.day == day)
#     ).scalars().first()
    
#     if not plan_day:
#         raise HTTPException(status_code=404, detail=f"Day {day} not found for campaign {campaign_id}")
    
#     new_title = update_data.value
    
#     old_title = plan_day.title
#     plan_day.title = new_title
#     session.add(plan_day)
#     session.commit()
    
#     return {
#         "status": "updated",
#         "campaign_id": campaign_id,
#         "day": day,
#         "field": "title",
#         "old_value": old_title,
#         "new_value": new_title
#     }

# @router.patch("/campaigns/{campaign_id}/days/{day}/subject")
# def update_day_subject(
#     campaign_id: int,
#     day: int,
#     update_data: UpdateFieldRequest,
#     session: Session = Depends(get_session)
# ):
#     """Update subject line for a specific day"""
#     plan_day = session.exec(
#         select(CampaignPlanModel)
#         .where(CampaignPlanModel.campaign_id == campaign_id)
#         .where(CampaignPlanModel.day == day)
#     ).scalars().first()
    
#     if not plan_day:
#         raise HTTPException(status_code=404, detail=f"Day {day} not found for campaign {campaign_id}")
    
#     new_subject = update_data.value
    
#     old_subject = plan_day.subject
#     plan_day.subject = new_subject
#     session.add(plan_day)
#     session.commit()
    
#     return {
#         "status": "updated",
#         "campaign_id": campaign_id,
#         "day": day,
#         "field": "subject",
#         "old_value": old_subject,
#         "new_value": new_subject
#     }

# @router.patch("/campaigns/{campaign_id}/days/{day}/objective")
# def update_day_objective(
#     campaign_id: int,
#     day: int,
#     update_data: UpdateFieldRequest,
#     session: Session = Depends(get_session)
# ):
#     """Update objective for a specific day"""
#     plan_day = session.exec(
#         select(CampaignPlanModel)
#         .where(CampaignPlanModel.campaign_id == campaign_id)
#         .where(CampaignPlanModel.day == day)
#     ).scalars().first()
    
#     if not plan_day:
#         raise HTTPException(status_code=404, detail=f"Day {day} not found for campaign {campaign_id}")
    
#     new_objective = update_data.value
    
#     old_objective = plan_day.goal
#     plan_day.goal = new_objective
#     session.add(plan_day)
#     session.commit()
    
#     return {
#         "status": "updated",
#         "campaign_id": campaign_id,
#         "day": day,
#         "field": "objective",
#         "old_value": old_objective,
#         "new_value": new_objective
#     }

# @router.patch("/campaigns/{campaign_id}/days/{day}/content")
# def update_day_content(
#     campaign_id: int,
#     day: int,
#     update_data: UpdateFieldRequest,
#     session: Session = Depends(get_session)
# ):
#     """Update content idea for a specific day"""
#     plan_day = session.exec(
#         select(CampaignPlanModel)
#         .where(CampaignPlanModel.campaign_id == campaign_id)
#         .where(CampaignPlanModel.day == day)
#     ).scalars().first()
    
#     if not plan_day:
#         raise HTTPException(status_code=404, detail=f"Day {day} not found for campaign {campaign_id}")
    
#     new_content = update_data.value
    
#     old_content = plan_day.body_idea
#     plan_day.body_idea = new_content
#     session.add(plan_day)
#     session.commit()
    
#     return {
#         "status": "updated",
#         "campaign_id": campaign_id,
#         "day": day,
#         "field": "content",
#         "old_value": old_content,
#         "new_value": new_content
#     }

# @router.post("/campaigns/{campaign_id}/approve")
# def approve_campaign(
#     campaign_id: int,
#     approval_data: ApprovalRequest,
#     session: Session = Depends(get_session)
# ):
#     """Approve campaign plan"""
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     import json
#     from datetime import datetime
    
#     feedback = approval_data.feedback or ""
#     approved_days = approval_data.approved_days
    
#     if not approved_days:
#         # Get all days if none specified
#         plan_days = session.exec(
#             select(CampaignPlanModel.day)
#             .where(CampaignPlanModel.campaign_id == campaign_id)
#         ).scalars().all()
#         approved_days = list(plan_days)
    
#     campaign.approval_status = "approved"
#     campaign.approved_at = datetime.utcnow()
#     campaign.user_feedback = feedback
#     campaign.approved_days = json.dumps(approved_days)
    
#     session.add(campaign)
#     session.commit()
    
#     return {
#         "status": "approved",
#         "campaign_id": campaign_id,
#         "approved_days": approved_days,
#         "feedback": feedback,
#         "approved_at": campaign.approved_at.isoformat(),
#         "next_step": f"/campaigns/{campaign_id}/start/",
#         "message": f"Campaign approved for {len(approved_days)} days"
#     }

# @router.post("/campaigns/{campaign_id}/reject")
# def reject_campaign(
#     campaign_id: int,
#     rejection_data: RejectionRequest,
#     session: Session = Depends(get_session)
# ):
#     """Reject campaign plan"""
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     feedback = rejection_data.feedback
    
#     campaign.approval_status = "rejected"
    
#     campaign.approval_status = "rejected"
#     campaign.user_feedback = feedback
    
#     session.add(campaign)
#     session.commit()
    
#     return {
#         "status": "rejected",
#         "campaign_id": campaign_id,
#         "feedback": feedback,
#         "message": "Campaign rejected with feedback provided"
#     }

@router.post("/campaigns/{campaign_id}/suggest-improvements")
def apply_user_suggestions(
    campaign_id: int,
    suggestion_data: SuggestionRequest,
    session: Session = Depends(get_session)
):
    """
    Apply user suggestions using AI agent to interpret and modify campaign content
    User provides natural language suggestions like 'make title more engaging'
    """
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    from agents.campaign_improvement_agent import CampaignImprovementAgent
    import json
    
    # Get current campaign plan
    if suggestion_data.day:
        # Specific day modification
        plan_days = session.exec(
            select(CampaignPlanModel)
            .where(CampaignPlanModel.campaign_id == campaign_id)
            .where(CampaignPlanModel.day == suggestion_data.day)
        ).scalars().all()
    else:
        # Get all days for analysis
        plan_days = session.exec(
            select(CampaignPlanModel)
            .where(CampaignPlanModel.campaign_id == campaign_id)
            .order_by(CampaignPlanModel.day)
        ).scalars().all()
    
    if not plan_days:
        raise HTTPException(status_code=404, detail="Campaign plan not found")
    
    # Prepare current content for AI agent
    current_content = {}
    for day in plan_days:
        current_content[f"day_{day.day}"] = {
            "title": day.title,
            "subject": day.subject,
            "objective": day.goal,
            "content": day.body_idea
        }
    
    # Use CampaignImprovementAgent to interpret suggestion and create improvements
    try:
        improvement_agent = CampaignImprovementAgent()
        
        # Analyze the suggestion first
        suggestion_analysis = improvement_agent.analyze_suggestion(suggestion_data.suggestion)
        
        # Get AI improvements using the proper campaign agent
        improved_content = improvement_agent.improve_campaign_content(
            user_suggestion=suggestion_data.suggestion,
            current_content=current_content,
            specific_day=suggestion_data.day,
            specific_field=suggestion_data.field
        )
        
        # Parse and apply improvements
        modifications_made = []
        
        # Try to extract improved content from AI response
        # This is a simplified implementation - you might need more robust parsing
        if isinstance(improved_content, dict):
            for day_key, day_content in improved_content.items():
                if day_key.startswith("day_"):
                    day_num = int(day_key.split("_")[1])
                    
                    # Find the corresponding database record
                    plan_day = session.exec(
                        select(CampaignPlanModel)
                        .where(CampaignPlanModel.campaign_id == campaign_id)
                        .where(CampaignPlanModel.day == day_num)
                    ).scalars().first()
                    
                    if plan_day and isinstance(day_content, dict):
                        changes = {}
                        
                        if "title" in day_content and day_content["title"] != plan_day.title:
                            changes["title"] = {"old": plan_day.title, "new": day_content["title"]}
                            plan_day.title = day_content["title"]
                        
                        if "subject" in day_content and day_content["subject"] != plan_day.subject:
                            changes["subject"] = {"old": plan_day.subject, "new": day_content["subject"]}
                            plan_day.subject = day_content["subject"]
                        
                        if "objective" in day_content and day_content["objective"] != plan_day.goal:
                            changes["objective"] = {"old": plan_day.goal, "new": day_content["objective"]}
                            plan_day.goal = day_content["objective"]
                        
                        if "content" in day_content and day_content["content"] != plan_day.body_idea:
                            changes["content"] = {"old": plan_day.body_idea, "new": day_content["content"]}
                            plan_day.body_idea = day_content["content"]
                        
                        if changes:
                            session.add(plan_day)
                            modifications_made.append({
                                "day": day_num,
                                "changes": changes
                            })
        
        # Update campaign status
        campaign.approval_status = "under_review"
        campaign.user_feedback = f"AI-applied suggestion: {suggestion_data.suggestion}"
        session.add(campaign)
        session.commit()
        
        # Validate changes made
        changes_analysis = improvement_agent.validate_improvements(current_content, improved_content)
        
        return {
            "status": "suggestions_applied",
            "campaign_id": campaign_id,
            "original_suggestion": suggestion_data.suggestion,
            "suggestion_analysis": suggestion_analysis,
            "modifications_made": modifications_made,
            "changes_analysis": changes_analysis,
            "message": f"Applied {len(modifications_made)} AI-generated improvements based on your suggestion"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing suggestion with AI: {str(e)}")

# @router.post("/campaigns/{campaign_id}/bulk-suggestions")
# def apply_bulk_suggestions(
#     campaign_id: int,
#     suggestions: List[SuggestionRequest],
#     session: Session = Depends(get_session)
# ):
#     """
#     Apply multiple user suggestions at once
#     """
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     all_modifications = []
    
#     for suggestion in suggestions:
#         try:
#             # Apply each suggestion individually
#             result = apply_user_suggestions(campaign_id, suggestion, session)
#             all_modifications.extend(result.get("modifications_made", []))
#         except Exception as e:
#             # Continue with other suggestions even if one fails
#             all_modifications.append({
#                 "suggestion": suggestion.suggestion,
#                 "error": str(e)
#             })
    
#     return {
#         "status": "bulk_suggestions_processed",
#         "campaign_id": campaign_id,
#         "total_suggestions": len(suggestions),
#         "all_modifications": all_modifications,
#         "message": f"Processed {len(suggestions)} suggestions with AI assistance"
#     }

# ============================================================================
# SIMPLE APPROVAL ENDPOINTS (No Request Body Required)
# ============================================================================

@router.post("/campaigns/{campaign_id}/plan_approve")
def simple_approve_campaign(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """
    Simple campaign approval - no request body required
    Just provide campaign_id in URL and it approves the entire campaign
    """
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    import json
    from datetime import datetime
    
    # Get all days for approval
    plan_days = session.exec(
        select(CampaignPlanModel.day)
        .where(CampaignPlanModel.campaign_id == campaign_id)
    ).scalars().all()
    approved_days = list(plan_days)
    
    if not approved_days:
        raise HTTPException(status_code=404, detail="No campaign plan found to approve")
    
    # Update campaign status
    campaign.approval_status = "approved"
    campaign.approved_at = datetime.utcnow()
    campaign.user_feedback = "Auto-approved via simple endpoint"
    campaign.approved_days = json.dumps(approved_days)
    
    session.add(campaign)
    session.commit()
    
    return {
        "status": "approved",
        "campaign_id": campaign_id,
        "approved_days": approved_days,
        "approved_at": campaign.approved_at.isoformat(),
        "message": f"Campaign approved for {len(approved_days)} days",
        "next_step": f"/campaigns/{campaign_id}/start/"
    }



# ============================================================================
# CORRECTED CAMPAIGN MANAGEMENT WORKFLOW APIs
# ============================================================================

# @router.post("/campaigns/{campaign_id}/start/")
# def start_campaign(
#     campaign_id: int,
#     session: Session = Depends(get_session)
# ):
#     """
#     Start an approved campaign - activates it for daily email generation
#     """
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     if campaign.approval_status != "approved":
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Campaign must be approved first. Current status: {campaign.approval_status}"
#         )
    
#     # Update campaign status to active
#     campaign.approval_status = "active"
#     session.add(campaign)
#     session.commit()
    
#     # Initialize campaign execution tracking for each day
#     from db.database_schema import CampaignExecution
    
#     # Get all campaign plan days
#     plan_days = session.exec(
#         select(CampaignPlanModel.day)
#         .where(CampaignPlanModel.campaign_id == campaign_id)
#         .order_by(CampaignPlanModel.day)
#     ).all()
    
#     # Create execution tracking records for each day
#     for day in plan_days:
#         existing_execution = session.exec(
#             select(CampaignExecution)
#             .where(CampaignExecution.campaign_id == campaign_id)
#             .where(CampaignExecution.day == day)
#         ).first()
        
#         if not existing_execution:
#             execution_record = CampaignExecution(
#                 campaign_id=campaign_id,
#                 day=day,
#                 status="not_generated"
#             )
#             session.add(execution_record)
    
#     session.commit()
    
#     return {
#         "status": "campaign_started",
#         "campaign_id": campaign_id,
#         "campaign_name": campaign.name,
#         "total_days": len(plan_days),
#         "message": f"Campaign activated! Use /campaigns/{campaign_id}/generate-day-email/ to create daily emails.",
#         "next_steps": [
#             f"POST /campaigns/{campaign_id}/generate-day-email/ with day number",
#             "Review generated email",
#             "Send when ready"
#         ]
#     }

@router.post("/campaigns/{campaign_id}/generate-day-email/")
def generate_day_email(
    campaign_id: int,
    request: GenerateDayEmailRequest,
    session: Session = Depends(get_session)
):
    """
    Generate email content for a specific campaign day
    
    Request body should contain:
    - day: The day number (1-5) for which to generate email content
    """
    from db.database_schema import CampaignExecution
    
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "executing":
        raise HTTPException(
            status_code=400,
            detail=f"Campaign must be executing to generate day emails. Current status: {campaign.status}"
        )
    
    day = request.day
    # Day is already validated by Pydantic (required field with range 1-5)
    
    # Get campaign plan for this day
    plan_day = session.exec(
        select(CampaignPlanModel)
        .where(CampaignPlanModel.campaign_id == campaign_id)
        .where(CampaignPlanModel.day == day)
    ).scalars().first()
    
    if not plan_day:
        raise HTTPException(status_code=404, detail=f"No plan found for day {day}")
    
    # Get or create execution record
    execution_record = session.exec(
        select(CampaignExecution)
        .where(CampaignExecution.campaign_id == campaign_id)
        .where(CampaignExecution.day == day)
    ).scalars().first()
    
    if not execution_record:
        execution_record = CampaignExecution(
            campaign_id=campaign_id,
            day=day,
            status="not_generated"
        )
        session.add(execution_record)
        session.commit()
        session.refresh(execution_record)
    
    # Generate email content using existing draft agent
    try:
        # Get client info directly from campaign - MUCH SIMPLER!
        client = session.get(ClientModel, campaign.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="No client found for campaign")
        
        # Create email draft
        from agents.draft_email_agent import EmailDraftAgent
        from datetime import datetime
        
        # Generate personalized content FIRST to get draft_id
        draft_agent = EmailDraftAgent()
        context = {
            "campaign_id": campaign_id,
            "contact_id": client.client_id,
            "day": day
        }
        
        result = draft_agent.invoke(context)
        
        # EmailDraftAgent already created the draft - no need for separate email record
        
        # Update execution record using merge to ensure it's mutable
        from datetime import datetime
        draft_id = result.get("draft_id")
        
        # Refresh the execution record to make it mutable
        session.refresh(execution_record)
        
        execution_record.email_id = draft_id  # Use draft_id as the email reference
        execution_record.generated_at = datetime.utcnow()
        execution_record.status = "generated"
        execution_record.email_subject = result.get("subject", plan_day.subject)
        execution_record.email_content = f"Draft {draft_id} generated successfully"
        
        session.add(execution_record)
        session.commit()
        
        return {
            "status": "email_generated",
            "campaign_id": campaign_id,
            "day": day,
            "draft_id": draft_id,
            "subject": result.get("subject", plan_day.subject),
            "generated_at": execution_record.generated_at.isoformat(),
            "message": f"Day {day} email generated successfully",
            "next_step": f"Review draft {draft_id} and use draft API to send when ready"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"🔍 [DEBUG] Email generation error: {error_details}")
        
        return {
            "status": "error",
            "message": f"Email generation failed: {str(e)}",
            "campaign_id": campaign_id,
            "day": day,
            "debug_info": error_details if len(str(e)) < 10 else str(e)  # Include traceback for short errors
        }

# @router.get("/campaigns/{campaign_id}/daily-status/")
# def get_campaign_daily_status(
#     campaign_id: int,
#     session: Session = Depends(get_session)
# ):
#     """
#     Get the status of daily email generation for a campaign
#     """
#     from db.database_schema import CampaignExecution
    
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     # Get all execution records
#     executions = session.exec(
#         select(CampaignExecution)
#         .where(CampaignExecution.campaign_id == campaign_id)
#         .order_by(CampaignExecution.day)
#     ).all()
    
#     # Get campaign plan for context
#     plan_days = session.exec(
#         select(CampaignPlanModel)
#         .where(CampaignPlanModel.campaign_id == campaign_id)
#         .order_by(CampaignPlanModel.day)
#     ).all()
    
#     # Merge plan and execution data
#     daily_status = []
#     for plan_day in plan_days:
#         execution = next((e for e in executions if e.day == plan_day.day), None)
        
#         status_info = {
#             "day": plan_day.day,
#             "title": plan_day.title,
#             "subject": plan_day.subject,
#             "objective": plan_day.goal,
#             "status": execution.status if execution else "not_generated",
#             "email_id": execution.email_id if execution else None,
#             "generated_at": execution.generated_at.isoformat() if execution and execution.generated_at else None,
#             "sent_at": execution.sent_at.isoformat() if execution and execution.sent_at else None,
#             "can_generate": True,
#             "can_send": execution and execution.status == "generated"
#         }
#         daily_status.append(status_info)
    
#     return {
#         "campaign_id": campaign_id,
#         "campaign_name": campaign.name,
#         "campaign_status": campaign.approval_status,
#         "total_days": len(plan_days),
#         "daily_status": daily_status,
#         "summary": {
#             "not_generated": len([s for s in daily_status if s["status"] == "not_generated"]),
#             "generated": len([s for s in daily_status if s["status"] == "generated"]),
#             "sent": len([s for s in daily_status if s["status"] == "sent"])
#         }
#     }

# ============================================================================
# CAMPAIGN EXECUTION WORKFLOW APIs
# ============================================================================

@router.post("/campaigns/{campaign_id}/start")
def start_campaign_execution(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """
    Start campaign execution - begins sending emails based on approved plan
    This is the next step after plan approval
    """
    from datetime import datetime
    
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.approval_status != "approved":
        raise HTTPException(status_code=400, detail="Campaign must be approved before starting execution")
    
    # Get approved campaign plan
    approved_plan = session.exec(
        select(CampaignPlanModel)
        .where(CampaignPlanModel.campaign_id == campaign_id)
        .order_by(CampaignPlanModel.day)
    ).scalars().all()
    
    if not approved_plan:
        raise HTTPException(status_code=404, detail="No approved campaign plan found")
    
    # SUPER SIMPLE: One campaign = One client!
    if not campaign.client_id:
        raise HTTPException(status_code=400, detail="Campaign has no client assigned")
    
    # Single client for this campaign
    campaign_clients = [campaign.client_id]
    
    # Create execution records for each day and client
    execution_records = []
    for plan_day in approved_plan:
        for client_id in campaign_clients:
            execution = CampaignExecutionModel(
                campaign_id=campaign_id,
                day=plan_day.day,
                status="scheduled"
            )
            session.add(execution)
            execution_records.append({
                "day": plan_day.day,
                "client_count": len(campaign_clients),
                "status": "scheduled"
            })
    
    # Update campaign status (safely handle missing fields)
    try:
        if hasattr(campaign, 'status'):
            campaign.status = "executing"
        if hasattr(campaign, 'started_at'):
            campaign.started_at = datetime.utcnow()
        session.add(campaign)
        session.commit()
    except Exception as e:
        print(f"Warning: Could not update campaign status: {e}")
        # Continue without updating status
        pass
    
    return {
        "status": "campaign_started",
        "campaign_id": campaign_id,
        "execution_plan": execution_records,
        "total_clients": len(campaign_clients),
        "total_days": len(approved_plan),
        "message": f"Campaign execution started for {len(campaign_clients)} clients over {len(approved_plan)} days"
    }

# @router.get("/campaigns/{campaign_id}/debug-info")
# def debug_campaign_info(
#     campaign_id: int,
#     session: Session = Depends(get_session)
# ):
#     """
#     Debug endpoint to check campaign setup
#     """
#     try:
#         campaign = session.get(CampaignModel, campaign_id)
#         if not campaign:
#             return {"error": "Campaign not found", "campaign_id": campaign_id}
        
#         # SUPER SIMPLE: Get the single client directly!
#         campaign_clients = [campaign.client_id] if campaign.client_id else []
        
#         # Check campaign plan
#         campaign_plan = session.exec(
#             select(CampaignPlanModel)
#             .where(CampaignPlanModel.campaign_id == campaign_id)
#         ).all()
        
#         # No need for client list links - we have direct client_id!
        
#         # Safely get campaign attributes
#         campaign_info = {
#             "name": getattr(campaign, 'name', 'N/A'),
#             "approval_status": getattr(campaign, 'approval_status', 'N/A'),
#             "client_id": getattr(campaign, 'client_id', 'N/A'),  # Direct client relationship
#             "user_id": getattr(campaign, 'user_id', 'N/A')
#         }
        
#         # Only add status if it exists
#         if hasattr(campaign, 'status'):
#             campaign_info["status"] = campaign.status
        
#         return {
#             "campaign_id": campaign_id,
#             "campaign": campaign_info,
#             "clients_from_list": [
#                 {"client_id": client_id} for client_id in campaign_clients
#             ],
#             "campaign_plan_days": [
#                 {"day": plan.day, "title": plan.title} for plan in campaign_plan
#             ],
#             "direct_client_id": campaign.client_id,
#             "counts": {
#                 "clients_in_campaign": len(campaign_clients),
#                 "campaign_plan_days": len(campaign_plan)
#             },
#             "explanation": "Campaign has DIRECT client_id relationship - super simple!"
#         }
#     except Exception as e:
#         return {
#             "error": str(e),
#             "campaign_id": campaign_id,
#             "message": "Debug endpoint failed - likely database schema issue"
#         }

# # Removed unnecessary fix endpoint - we use client list directly now!

# @router.get("/campaigns/{campaign_id}/execution-status")
# def get_campaign_execution_status(
#     campaign_id: int,
#     session: Session = Depends(get_session)
# ):
#     """
#     Get current execution status of the campaign
#     """
#     campaign = session.get(CampaignModel, campaign_id)
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     # Get execution summary
#     execution_summary = session.exec(
#         select(
#             CampaignExecutionModel.day,
#             CampaignExecutionModel.status,
#             func.count(CampaignExecutionModel.execution_id).label("count")
#         )
#         .where(CampaignExecutionModel.campaign_id == campaign_id)
#         .group_by(CampaignExecutionModel.day, CampaignExecutionModel.status)
#     ).all()
    
#     # Organize by day
#     status_by_day = {}
#     for day, status, count in execution_summary:
#         if day not in status_by_day:
#             status_by_day[day] = {}
#         status_by_day[day][status] = count
    
#     return {
#         "campaign_id": campaign_id,
#         "campaign_status": campaign.status,
#         "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
#         "execution_summary": status_by_day,
#         "message": "Campaign execution status retrieved"
#     }

# ============================================================================
# LEAD SCORING CONFIGURATION APIs
# ============================================================================

@router.post("/campaigns/{campaign_id}/lead-scoring-config")
def create_lead_scoring_config(
    campaign_id: int,
    config_data: Dict[str, int],
    session: Session = Depends(get_session)
):
    """
    Define lead scoring parameters for the campaign
    """
    campaign = session.get(CampaignModel, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check if config already exists
    existing_config = session.exec(
        select(LeadScoringConfig)
        .where(LeadScoringConfig.campaign_id == campaign_id)
    ).first()
    
    if existing_config:
        # Update existing config
        existing_config.email_open_points = config_data.get("email_open_points", 10)
        existing_config.email_click_points = config_data.get("email_click_points", 25)
        existing_config.email_reply_points = config_data.get("email_reply_points", 50)
        existing_config.website_visit_points = config_data.get("website_visit_points", 15)
        existing_config.social_engagement_points = config_data.get("social_engagement_points", 20)
        existing_config.hot_threshold = config_data.get("hot_threshold", 100)
        existing_config.warm_threshold = config_data.get("warm_threshold", 50)
        existing_config.cold_threshold = config_data.get("cold_threshold", 0)
        existing_config.updated_at = datetime.utcnow()
        session.add(existing_config)
    else:
        # Create new config
        new_config = LeadScoringConfig(
            campaign_id=campaign_id,
            email_open_points=config_data.get("email_open_points", 10),
            email_click_points=config_data.get("email_click_points", 25),
            email_reply_points=config_data.get("email_reply_points", 50),
            website_visit_points=config_data.get("website_visit_points", 15),
            social_engagement_points=config_data.get("social_engagement_points", 20),
            hot_threshold=config_data.get("hot_threshold", 100),
            warm_threshold=config_data.get("warm_threshold", 50),
            cold_threshold=config_data.get("cold_threshold", 0)
        )
        session.add(new_config)
    
    session.commit()
    
    return {
        "status": "config_saved",
        "campaign_id": campaign_id,
        "scoring_config": config_data,
        "message": "Lead scoring configuration saved successfully"
    }

@router.get("/campaigns/{campaign_id}/lead-scoring-config")
def get_lead_scoring_config(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """
    Get current lead scoring configuration
    """
    config = session.exec(
        select(LeadScoringConfig)
        .where(LeadScoringConfig.campaign_id == campaign_id)
    ).first()
    
    if not config:
        # Return default config
        return {
            "campaign_id": campaign_id,
            "config": {
                "email_open_points": 10,
                "email_click_points": 25,
                "email_reply_points": 50,
                "website_visit_points": 15,
                "social_engagement_points": 20,
                "hot_threshold": 100,
                "warm_threshold": 50,
                "cold_threshold": 0
            },
            "message": "Using default scoring configuration"
        }
    
    return {
        "campaign_id": campaign_id,
        "config": {
            "email_open_points": config.email_open_points,
            "email_click_points": config.email_click_points,
            "email_reply_points": config.email_reply_points,
            "website_visit_points": config.website_visit_points,
            "social_engagement_points": config.social_engagement_points,
            "hot_threshold": config.hot_threshold,
            "warm_threshold": config.warm_threshold,
            "cold_threshold": config.cold_threshold
        },
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        "message": "Lead scoring configuration retrieved"
    }

# ============================================================================
# LEAD PERFORMANCE TRACKING APIs
# ============================================================================

@router.post("/campaigns/{campaign_id}/track-performance")
def track_lead_performance(
    campaign_id: int,
    performance_data: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Track lead performance metrics (email opens, clicks, replies, etc.)
    """
    client_id = performance_data.get("client_id")
    day = performance_data.get("day")
    action = performance_data.get("action")  # opened, clicked, replied, visited, engaged
    
    if not all([client_id, day, action]):
        raise HTTPException(status_code=400, detail="client_id, day, and action are required")
    
    # Get or create performance record
    performance = session.exec(
        select(LeadPerformance)
        .where(LeadPerformance.campaign_id == campaign_id)
        .where(LeadPerformance.client_id == client_id)
        .where(LeadPerformance.day == day)
    ).first()
    
    if not performance:
        performance = LeadPerformance(
            campaign_id=campaign_id,
            client_id=client_id,
            day=day
        )
    
    # Update performance based on action - NOW WITH PROPER COUNTING
    current_time = datetime.utcnow()
    
    if action == "opened":
        performance.email_open_count += 1
        performance.email_opened = True
        if not performance.first_opened_at:
            performance.first_opened_at = current_time
        performance.last_opened_at = current_time
        
    elif action == "clicked":
        performance.email_click_count += 1
        performance.email_clicked = True
        if not performance.first_clicked_at:
            performance.first_clicked_at = current_time
        performance.last_clicked_at = current_time
        
    elif action == "replied":
        performance.email_reply_count += 1
        performance.email_replied = True
        if not performance.first_replied_at:
            performance.first_replied_at = current_time
        performance.last_replied_at = current_time
        
    elif action == "visited":
        performance.website_visit_count += 1
        performance.website_visited = True
        if not performance.first_visited_at:
            performance.first_visited_at = current_time
        performance.last_visited_at = current_time
        
    elif action == "engaged":
        performance.social_engagement_count += 1
        performance.social_engaged = True
        
    # Log detailed activity
    activity_log = ActivityLog(
        campaign_id=campaign_id,
        client_id=client_id,
        day=day,
        activity_type=action,
        activity_data=str(performance_data.get("metadata", {})),
        ip_address=performance_data.get("ip_address"),
        user_agent=performance_data.get("user_agent"),
        timestamp=current_time
    )
    session.add(activity_log)
    
    session.add(performance)
    session.commit()
    
    # Recalculate lead score
    updated_score = calculate_lead_score(campaign_id, client_id, session)
    
    return {
        "status": "performance_tracked",
        "campaign_id": campaign_id,
        "client_id": client_id,
        "day": day,
        "action": action,
        "updated_score": updated_score,
        "message": f"Performance action '{action}' tracked for client {client_id}"
    }

@router.get("/campaigns/{campaign_id}/lead-scores")
def get_lead_scores(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """
    Get all lead scores for the campaign
    """
    lead_scores = session.exec(
        select(LeadScore, ClientModel.full_name, ClientModel.email)
        .join(ClientModel, LeadScore.client_id == ClientModel.client_id)
        .where(LeadScore.campaign_id == campaign_id)
        .order_by(LeadScore.total_score.desc())
    ).all()
    
    scores_list = []
    for score, client_name, client_email in lead_scores:
        scores_list.append({
            "client_id": score.client_id,
            "client_name": client_name,
            "client_email": client_email,
            "total_score": score.total_score,
            "email_score": score.email_score,
            "engagement_score": score.engagement_score,
            "lead_status": score.lead_status,
            "last_updated": score.last_updated.isoformat(),
            "notes": score.notes
        })
    
    return {
        "campaign_id": campaign_id,
        "lead_scores": scores_list,
        "total_leads": len(scores_list),
        "message": "Lead scores retrieved successfully"
    }

def calculate_lead_score(campaign_id: int, client_id: int, session: Session) -> Dict[str, Any]:
    """
    Calculate and update lead score based on performance data
    """
    # Get scoring config
    config = session.exec(
        select(LeadScoringConfig)
        .where(LeadScoringConfig.campaign_id == campaign_id)
    ).first()
    
    if not config:
        # Use default scoring
        config = LeadScoringConfig(
            email_open_points=10,
            email_click_points=25,
            email_reply_points=50,
            website_visit_points=15,
            social_engagement_points=20,
            hot_threshold=100,
            warm_threshold=50,
            cold_threshold=0
        )
    
    # Get all performance data for this client
    performances = session.exec(
        select(LeadPerformance)
        .where(LeadPerformance.campaign_id == campaign_id)
        .where(LeadPerformance.client_id == client_id)
    ).all()
    
    # Calculate scores based on ACTUAL COUNTS, not just booleans
    email_score = 0
    engagement_score = 0
    
    for perf in performances:
        # Score based on actual activity counts
        email_score += perf.email_open_count * config.email_open_points
        email_score += perf.email_click_count * config.email_click_points
        email_score += perf.email_reply_count * config.email_reply_points
        engagement_score += perf.website_visit_count * config.website_visit_points
        engagement_score += perf.social_engagement_count * config.social_engagement_points
    
    total_score = email_score + engagement_score
    
    # Determine lead status
    if total_score >= config.hot_threshold:
        lead_status = "hot"
    elif total_score >= config.warm_threshold:
        lead_status = "warm"
    else:
        lead_status = "cold"
    
    # Update or create lead score record
    lead_score = session.exec(
        select(LeadScore)
        .where(LeadScore.campaign_id == campaign_id)
        .where(LeadScore.client_id == client_id)
    ).first()
    
    if lead_score:
        lead_score.total_score = total_score
        lead_score.email_score = email_score
        lead_score.engagement_score = engagement_score
        lead_score.lead_status = lead_status
        lead_score.last_updated = datetime.utcnow()
    else:
        lead_score = LeadScore(
            campaign_id=campaign_id,
            client_id=client_id,
            total_score=total_score,
            email_score=email_score,
            engagement_score=engagement_score,
            lead_status=lead_status
        )
    
    session.add(lead_score)
    session.commit()
    
    return {
        "total_score": total_score,
        "email_score": email_score,
        "engagement_score": engagement_score,
        "lead_status": lead_status
    }

# ============================================================================
# LEAD STATUS MANAGEMENT APIs
# ============================================================================

@router.get("/campaigns/{campaign_id}/leads-by-status/{status}")
def get_leads_by_status(
    campaign_id: int,
    status: str,  # hot, warm, cold
    session: Session = Depends(get_session)
):
    """
    Get all leads with a specific status (hot, warm, cold)
    """
    if status not in ["hot", "warm", "cold"]:
        raise HTTPException(status_code=400, detail="Status must be 'hot', 'warm', or 'cold'")
    
    leads = session.exec(
        select(LeadScore, ClientModel.full_name, ClientModel.email, ClientModel.company)
        .join(ClientModel, LeadScore.client_id == ClientModel.client_id)
        .where(LeadScore.campaign_id == campaign_id)
        .where(LeadScore.lead_status == status)
        .order_by(LeadScore.total_score.desc())
    ).all()
    
    leads_list = []
    for score, client_name, client_email, client_company in leads:
        leads_list.append({
            "client_id": score.client_id,
            "client_name": client_name,
            "client_email": client_email,
            "client_company": client_company,
            "total_score": score.total_score,
            "lead_status": score.lead_status,
            "last_updated": score.last_updated.isoformat()
        })
    
    return {
        "campaign_id": campaign_id,
        "status": status,
        "leads": leads_list,
        "count": len(leads_list),
        "message": f"Retrieved {len(leads_list)} {status} leads"
    }

@router.post("/campaigns/{campaign_id}/update-lead-status")
def update_lead_status(
    campaign_id: int,
    status_update: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Manually update a lead's status and add notes
    """
    client_id = status_update.get("client_id")
    new_status = status_update.get("status")
    notes = status_update.get("notes", "")
    
    if not client_id or not new_status:
        raise HTTPException(status_code=400, detail="client_id and status are required")
    
    if new_status not in ["hot", "warm", "cold"]:
        raise HTTPException(status_code=400, detail="Status must be 'hot', 'warm', or 'cold'")
    
    # Get lead score record
    lead_score = session.exec(
        select(LeadScore)
        .where(LeadScore.campaign_id == campaign_id)
        .where(LeadScore.client_id == client_id)
    ).first()
    
    if not lead_score:
        raise HTTPException(status_code=404, detail="Lead score record not found")
    
    # Update status
    old_status = lead_score.lead_status
    lead_score.lead_status = new_status
    lead_score.notes = notes
    lead_score.last_updated = datetime.utcnow()
    
    session.add(lead_score)
    session.commit()
    
    return {
        "status": "status_updated",
        "campaign_id": campaign_id,
        "client_id": client_id,
        "old_status": old_status,
        "new_status": new_status,
        "notes": notes,
        "message": f"Lead status updated from {old_status} to {new_status}"
    }

# @router.get("/campaigns/{campaign_id}/campaign-metrics")
# def get_campaign_metrics(
#     campaign_id: int,
#     session: Session = Depends(get_session)
# ):
#     """
#     Get overall campaign performance metrics and lead distribution
#     """
#     # Count leads by status
#     lead_counts = session.exec(
#         select(
#             LeadScore.lead_status,
#             func.count(LeadScore.score_id).label("count")
#         )
#         .where(LeadScore.campaign_id == campaign_id)
#         .group_by(LeadScore.lead_status)
#     ).all()
    
#     # Count performance metrics
#     performance_metrics = session.exec(
#         select(
#             func.count(LeadPerformance.performance_id).label("total_activities"),
#             func.sum(func.cast(LeadPerformance.email_opened, int)).label("total_opens"),
#             func.sum(func.cast(LeadPerformance.email_clicked, int)).label("total_clicks"),
#             func.sum(func.cast(LeadPerformance.email_replied, int)).label("total_replies"),
#             func.sum(func.cast(LeadPerformance.website_visited, int)).label("total_visits")
#         )
#         .where(LeadPerformance.campaign_id == campaign_id)
#     ).first()
    
#     # Organize lead counts
#     status_counts = {"hot": 0, "warm": 0, "cold": 0}
#     for status, count in lead_counts:
#         status_counts[status] = count
    
#     total_leads = sum(status_counts.values())
    
#     # Calculate rates
#     total_opens = performance_metrics.total_opens or 0
#     total_clicks = performance_metrics.total_clicks or 0
#     total_replies = performance_metrics.total_replies or 0
    
#     open_rate = (total_opens / total_leads * 100) if total_leads > 0 else 0
#     click_rate = (total_clicks / total_leads * 100) if total_leads > 0 else 0
#     reply_rate = (total_replies / total_leads * 100) if total_leads > 0 else 0
    
#     return {
#         "campaign_id": campaign_id,
#         "lead_distribution": {
#             "hot_leads": status_counts["hot"],
#             "warm_leads": status_counts["warm"], 
#             "cold_leads": status_counts["cold"],
#             "total_leads": total_leads
#         },
#         "performance_metrics": {
#             "total_opens": total_opens,
#             "total_clicks": total_clicks,
#             "total_replies": total_replies,
#             "total_visits": performance_metrics.total_visits or 0,
#             "open_rate": round(open_rate, 2),
#             "click_rate": round(click_rate, 2),
#             "reply_rate": round(reply_rate, 2)
#         },
#         "message": "Campaign metrics calculated successfully"
#     }

# @router.get("/campaigns/{campaign_id}/detailed-analytics")
# def get_detailed_campaign_analytics(
#     campaign_id: int,
#     session: Session = Depends(get_session)
# ):
#     """
#     Get detailed analytics showing actual counts and activity timeline
#     """
#     # Get performance with counts
#     detailed_performance = session.exec(
#         select(
#             LeadPerformance.client_id,
#             LeadPerformance.day,
#             LeadPerformance.email_open_count,
#             LeadPerformance.email_click_count,
#             LeadPerformance.email_reply_count,
#             LeadPerformance.website_visit_count,
#             LeadPerformance.social_engagement_count,
#             ClientModel.full_name,
#             ClientModel.email
#         )
#         .join(ClientModel, LeadPerformance.client_id == ClientModel.client_id)
#         .where(LeadPerformance.campaign_id == campaign_id)
#         .order_by(LeadPerformance.client_id, LeadPerformance.day)
#     ).all()
    
#     # Get activity timeline
#     recent_activities = session.exec(
#         select(ActivityLog, ClientModel.full_name)
#         .join(ClientModel, ActivityLog.client_id == ClientModel.client_id)
#         .where(ActivityLog.campaign_id == campaign_id)
#         .order_by(ActivityLog.timestamp.desc())
#         .limit(50)
#     ).all()
    
#     analytics = []
#     for perf in detailed_performance:
#         analytics.append({
#             "client_id": perf.client_id,
#             "client_name": perf.full_name,
#             "client_email": perf.email,
#             "day": perf.day,
#             "email_opens": perf.email_open_count,
#             "email_clicks": perf.email_click_count,
#             "email_replies": perf.email_reply_count,
#             "website_visits": perf.website_visit_count,
#             "social_engagements": perf.social_engagement_count,
#             "total_activities": (
#                 perf.email_open_count + perf.email_click_count + 
#                 perf.email_reply_count + perf.website_visit_count + 
#                 perf.social_engagement_count
#             )
#         })
    
#     activity_timeline = []
#     for activity, client_name in recent_activities:
#         activity_timeline.append({
#             "client_name": client_name,
#             "activity_type": activity.activity_type,
#             "day": activity.day,
#             "timestamp": activity.timestamp.isoformat(),
#             "ip_address": activity.ip_address
#         })
    
#     return {
#         "campaign_id": campaign_id,
#         "detailed_performance": analytics,
#         "recent_activity_timeline": activity_timeline,
#         "summary": {
#             "total_email_opens": sum(p.email_open_count for p in detailed_performance),
#             "total_email_clicks": sum(p.email_click_count for p in detailed_performance),
#             "total_website_visits": sum(p.website_visit_count for p in detailed_performance),
#             "most_active_client": max(analytics, key=lambda x: x["total_activities"])["client_name"] if analytics else None
#         },
#         "message": "Detailed analytics retrieved with actual activity counts"
#     }


# ============================================================================
# STREAMLIT FRONTEND APIS
# ============================================================================

@router.get("/introductory-emails/", response_model=List[Dict[str, Any]])
def get_all_introductory_emails(user_id: Optional[int] = None, session: Session = Depends(get_session)):
    """Get all introductory emails for Streamlit dashboard, optionally filtered by user_id"""
    try:
        # Query introductory emails with optional user filter
        query = session.query(IntroductoryEmailModel)
        if user_id:
            query = query.filter(IntroductoryEmailModel.user_id == user_id)
        intro_emails = query.all()
        
        result = []
        for intro in intro_emails:
            # Get client info
            client = session.get(ClientModel, intro.client_id)
            
            # Get email draft info if available
            draft = None
            if intro.draft_id:
                draft = session.get(EmailDraftModel, intro.draft_id)
            
            result.append({
                "intro_id": intro.intro_id,
                "client_id": intro.client_id,
                "client_name": client.full_name if client else "Unknown",
                "client_email": client.email if client else "Unknown",
                "client_company": client.company if client else "Unknown",
                "subject": draft.subject if draft else "No Subject",
                "sent_at": intro.sent_at.isoformat() if intro.sent_at else None,
                "replied": intro.replied,
                "reply_check_count": intro.reply_check_count,
                "last_reply_check": intro.last_reply_check.isoformat() if intro.last_reply_check else None,
                "no_reply_workflow_triggered": intro.no_reply_workflow_triggered,
                "no_reply_workflow_triggered_at": intro.no_reply_workflow_triggered_at.isoformat() if intro.no_reply_workflow_triggered_at else None,
                "timezone": intro.timezone,
                "preferred_language": intro.preferred_language,
                "communication_method": intro.communication_method,
                "created_at": intro.created_at.isoformat() if intro.created_at else None
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching introductory emails: {str(e)}")


@router.get("/clients/{client_id}/introductory-email/", response_model=Dict[str, Any])
def get_client_introductory_email(client_id: int, session: Session = Depends(get_session)):
    """Get introductory email information for a specific client"""
    try:
        # Find introductory email by client_id
        intro = session.query(IntroductoryEmailModel).filter(
            IntroductoryEmailModel.client_id == client_id
        ).first()
        
        if not intro:
            raise HTTPException(status_code=404, detail="No introductory email found for this client")
        
        # Get related data - simplified version
        client = session.get(ClientModel, client_id)
        user = session.get(UserModel, intro.user_id) if intro and intro.user_id else None
        draft = session.get(EmailDraftModel, intro.draft_id) if intro and intro.draft_id else None
        
        # Simple return without follow-ups for now
        return {
            "intro_email": {
                "intro_id": intro.intro_id,
                "sent_at": intro.sent_at.isoformat() if intro.sent_at else None,
                "replied": intro.replied,
                "reply_check_count": intro.reply_check_count,
                "last_reply_check": intro.last_reply_check.isoformat() if intro.last_reply_check else None,
                "no_reply_workflow_triggered": intro.no_reply_workflow_triggered,
                "no_reply_workflow_triggered_at": intro.no_reply_workflow_triggered_at.isoformat() if intro.no_reply_workflow_triggered_at else None,
                "timezone": intro.timezone,
                "preferred_language": intro.preferred_language,
                "communication_method": intro.communication_method
            },
            "client": {
                "client_id": client.client_id if client else None,
                "full_name": client.full_name if client else "Unknown",
                "email": client.email if client else "Unknown",
                "company": client.company if client else "Unknown",
                "phone": client.phone if client else None,
                "linkedin_url": client.linkedin_url if client else None
            },
            "user": {
                "user_id": user.user_id if user else None,
                "name": user.name if user else "Unknown", 
                "email": user.email if user else "Unknown"
            },
            "email_draft": {
                "draft_id": draft.draft_id if draft else None,
                "subject": draft.subject if draft else "No Subject",
                "body_markdown": draft.body_markdown if draft else "No Content"
            },
            "follow_up_campaigns": []
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching intro email details: {str(e)}")


@router.get("/campaign-executions/", response_model=List[Dict[str, Any]])
def get_all_campaign_executions(client_id: Optional[int] = None, user_id: Optional[int] = None, session: Session = Depends(get_session)):
    """Get all campaign executions (follow-up emails) for Streamlit dashboard, optionally filtered by client_id or user_id"""
    try:
        # Debug: Check total count in table
        total_count = session.query(CampaignExecutionModel).count()
        print(f"DEBUG: Total CampaignExecution records: {total_count}")
        
        # Start with base query - JOIN with Campaign to get client_id access
        query = session.query(CampaignExecutionModel).join(CampaignModel)
        
        # Apply filters
        if client_id:
            query = query.filter(CampaignModel.client_id == client_id)
            print(f"DEBUG: Filtering by client_id: {client_id}")
        
        if user_id:
            query = query.filter(CampaignModel.user_id == user_id)
            print(f"DEBUG: Filtering by user_id: {user_id}")
            
        executions = query.all()
        print(f"DEBUG: Found {len(executions)} campaign executions after filtering")
        
        result = []
        for execution in executions:
            try:
                # Get campaign and client data through the relationship
                campaign = session.get(CampaignModel, execution.campaign_id) if execution.campaign_id else None
                client = session.get(ClientModel, campaign.client_id) if campaign else None
                
                result.append({
                    "execution_id": execution.execution_id,
                    "campaign_id": execution.campaign_id,
                    "client_id": campaign.client_id if campaign else None,
                    "client_name": client.full_name if client else "Unknown",
                    "client_email": client.email if client else "Unknown", 
                    "client_company": client.company if client else "Unknown",
                    "campaign_name": campaign.name if campaign else f"Campaign {execution.campaign_id}",
                    "subject": execution.email_subject or "No Subject",
                    "personalized_content": execution.email_content[:200] + "..." if execution.email_content and len(execution.email_content) > 200 else execution.email_content,
                    "scheduled_at": execution.scheduled_at.isoformat() if execution.scheduled_at else None,
                    "sent_at": execution.sent_at.isoformat() if execution.sent_at else None,
                    "status": execution.status or "Unknown",
                    "created_at": execution.generated_at.isoformat() if execution.generated_at else None,
                    "day": execution.day
                })
            except Exception as row_error:
                # Skip problematic rows but continue processing
                print(f"Error processing execution {execution.execution_id}: {str(row_error)}")
                continue
        
        return result
        
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "user_id": user_id,
            "client_id": client_id
        }
        raise HTTPException(status_code=500, detail=f"Error fetching campaign executions: {str(e)} - Details: {error_details}")


# @router.get("/clients/{client_id}/campaign-executions/", response_model=List[Dict[str, Any]])
# def get_client_campaign_executions(client_id: int, session: Session = Depends(get_session)):
#     """Get all follow-up campaign executions for a specific client"""
#     try:
#         # Verify client exists
#         client = session.get(ClientModel, client_id)
#         if not client:
#             raise HTTPException(status_code=404, detail="Client not found")
        
#         # Get all campaign executions for this client through Campaign relationship
#         executions = session.query(CampaignExecutionModel).join(CampaignModel).filter(
#             CampaignModel.client_id == client_id
#         ).order_by(CampaignExecutionModel.scheduled_at).all()
        
#         result = []
#         for execution in executions:
#             campaign = session.get(CampaignModel, execution.campaign_id) if execution.campaign_id else None
            
#             result.append({
#                 "execution_id": execution.execution_id,
#                 "campaign_id": execution.campaign_id,
#                 "campaign_name": campaign.name if campaign else f"Campaign {execution.campaign_id}",
#                 "subject": execution.email_subject or "No Subject",
#                 "personalized_content": execution.email_content,
#                 "scheduled_at": execution.scheduled_at.isoformat() if execution.scheduled_at else None,
#                 "sent_at": execution.sent_at.isoformat() if execution.sent_at else None,
#                 "status": execution.status,
#                 "created_at": execution.generated_at.isoformat() if execution.generated_at else None,
#                 "day": execution.day
#             })
        
#         return result
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching client campaign executions: {str(e)}")


# @router.get("/debug/database-counts/")
# def debug_database_counts(session: Session = Depends(get_session)):
#     """Debug endpoint to check record counts in all relevant tables"""
#     try:
#         counts = {
#             "users": session.query(UserModel).count(),
#             "clients": session.query(ClientModel).count(),
#             "introductory_emails": session.query(IntroductoryEmailModel).count(),
#             "campaign_executions": session.query(CampaignExecutionModel).count(),
#             "campaigns": session.query(CampaignModel).count(),
#             "email_drafts": session.query(EmailDraftModel).count()
#         }
        
#         # Get some sample data
#         sample_campaign_executions = session.query(CampaignExecutionModel).limit(3).all()
#         sample_intro_emails = session.query(IntroductoryEmailModel).limit(3).all()
        
#         return {
#             "counts": counts,
#             "sample_campaign_executions": [
#                 {
#                     "execution_id": ce.execution_id,
#                     "client_id": ce.client_id,
#                     "campaign_id": ce.campaign_id,
#                     "subject": ce.subject,
#                     "status": ce.status
#                 } for ce in sample_campaign_executions
#             ],
#             "sample_intro_emails": [
#                 {
#                     "intro_id": ie.intro_id,
#                     "client_id": ie.client_id,
#                     "user_id": ie.user_id,
#                     "replied": ie.replied,
#                     "no_reply_workflow_triggered": ie.no_reply_workflow_triggered
#                 } for ie in sample_intro_emails
#             ]
#         }
#     except Exception as e:
#         return {"error": str(e)}


# @router.get("/analytics/dashboard/", response_model=Dict[str, Any])
# def get_dashboard_analytics(session: Session = Depends(get_session)):
#     """Get overview analytics for Streamlit dashboard"""
#     try:
#         # Get counts
#         total_intro_emails = session.query(IntroductoryEmailModel).count()
#         total_replies = session.query(IntroductoryEmailModel).filter(IntroductoryEmailModel.replied == True).count()
#         total_no_reply_workflows = session.query(IntroductoryEmailModel).filter(IntroductoryEmailModel.no_reply_workflow_triggered == True).count()
#         total_follow_ups = session.query(CampaignExecutionModel).count()
#         total_clients = session.query(ClientModel).count()
#         total_campaigns = session.query(CampaignModel).count()
        
#         # Calculate rates
#         reply_rate = (total_replies / total_intro_emails * 100) if total_intro_emails > 0 else 0
#         no_reply_rate = (total_no_reply_workflows / total_intro_emails * 100) if total_intro_emails > 0 else 0
        
#         # Get recent activity
#         recent_intro_emails = session.query(IntroductoryEmailModel).order_by(
#             IntroductoryEmailModel.sent_at.desc()
#         ).limit(5).all()
        
#         recent_executions = session.query(CampaignExecutionModel).order_by(
#             CampaignExecutionModel.created_at.desc()
#         ).limit(5).all()
        
#         return {
#             "overview": {
#                 "total_intro_emails": total_intro_emails,
#                 "total_replies": total_replies,
#                 "total_no_reply_workflows": total_no_reply_workflows,
#                 "total_follow_ups": total_follow_ups,
#                 "total_clients": total_clients,
#                 "total_campaigns": total_campaigns,
#                 "reply_rate_percentage": round(reply_rate, 2),
#                 "no_reply_rate_percentage": round(no_reply_rate, 2)
#             },
#             "recent_activity": {
#                 "recent_intro_emails": len(recent_intro_emails),
#                 "recent_follow_ups": len(recent_executions)
#             }
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching dashboard analytics: {str(e)}")


# @router.get("/clients/{client_id}/activity-timeline/", response_model=Dict[str, Any])
# def get_client_activity_timeline(client_id: int, session: Session = Depends(get_session)):
#     """Get complete activity timeline for a specific client"""
#     try:
#         client = session.get(ClientModel, client_id)
#         if not client:
#             raise HTTPException(status_code=404, detail="Client not found")
        
#         timeline = []
        
#         # Get introductory email
#         intro = session.query(IntroductoryEmailModel).filter(
#             IntroductoryEmailModel.client_id == client_id
#         ).first()
        
#         if intro:
#             timeline.append({
#                 "timestamp": intro.sent_at.isoformat() if intro.sent_at else intro.created_at.isoformat(),
#                 "type": "introductory_email",
#                 "title": "Introductory Email Sent",
#                 "description": f"Initial outreach email sent to {client.full_name}",
#                 "status": "replied" if intro.replied else "no_reply",
#                 "details": {
#                     "reply_checks": intro.reply_check_count,
#                     "last_check": intro.last_reply_check.isoformat() if intro.last_reply_check else None
#                 }
#             })
            
#             if intro.no_reply_workflow_triggered:
#                 timeline.append({
#                     "timestamp": intro.no_reply_workflow_triggered_at.isoformat(),
#                     "type": "no_reply_workflow",
#                     "title": "No-Reply Workflow Triggered",
#                     "description": "Follow-up campaign sequence initiated",
#                     "status": "active"
#                 })
        
#         # Get follow-up campaigns
#         follow_ups = session.query(CampaignExecutionModel).filter(
#             CampaignExecutionModel.client_id == client_id
#         ).order_by(CampaignExecutionModel.scheduled_at).all()
        
#         for follow_up in follow_ups:
#             timeline.append({
#                 "timestamp": (follow_up.sent_at or follow_up.scheduled_at or follow_up.created_at).isoformat(),
#                 "type": "follow_up_email",
#                 "title": f"Follow-up Email: {follow_up.subject}",
#                 "description": follow_up.personalized_content[:100] + "..." if follow_up.personalized_content and len(follow_up.personalized_content) > 100 else follow_up.personalized_content,
#                 "status": follow_up.status,
#                 "details": {
#                     "execution_id": follow_up.execution_id,
#                     "scheduled_at": follow_up.scheduled_at.isoformat() if follow_up.scheduled_at else None,
#                     "sent_at": follow_up.sent_at.isoformat() if follow_up.sent_at else None
#                 }
#             })
        
#         # Sort timeline by timestamp
#         timeline.sort(key=lambda x: x["timestamp"])
        
#         return {
#             "client": {
#                 "client_id": client.client_id,
#                 "full_name": client.full_name,
#                 "email": client.email,
#                 "company": client.company
#             },
#             "timeline": timeline,
#             "summary": {
#                 "total_activities": len(timeline),
#                 "intro_email_sent": intro is not None,
#                 "replied_to_intro": intro.replied if intro else False,
#                 "follow_ups_sent": len(follow_ups)
#             }
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching client timeline: {str(e)}")
