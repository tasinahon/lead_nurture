
from sqlmodel import SQLModel
from db.session import engine
from db.database_schema import User, Client  

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
