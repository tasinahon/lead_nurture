
from fastapi import FastAPI
from api.api_endpoints import router as user_api
from db.init_db import create_db_and_tables

app = FastAPI()

@app.on_event("startup")
def on_startup():
    
    create_db_and_tables()


app.include_router(user_api, prefix="/api")
