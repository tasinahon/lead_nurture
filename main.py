
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from api.api_endpoints import router as user_api
from db.init_db import create_db_and_tables

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://salmon-sand-05f52e90f.6.azurestaticapps.net"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(user_api, prefix="/api")
