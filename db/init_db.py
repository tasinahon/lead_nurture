
from sqlmodel import SQLModel
from db.session import engine
from db.database_schema import (
    User, Client, ClientList, ClientListLink, Profile, InitialStrategy,
    Strategy, EmailDraft, MessageDraft, Email, Message, MessageSend,
    CommLog, Engagement, Feedback, ContextQuestion, ScrapedData,
    Communication, Campaign, CampaignClientLink, CampaignPlan,
    EmailReply, IntroductoryEmail
)

def create_db_and_tables():
    """Create all database tables based on SQLModel schema"""
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_db_and_tables()
