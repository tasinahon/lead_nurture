from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.api_endpoints import router as user_api
from db.init_db import create_db_and_tables

app = FastAPI()

# Middleware to log Origin headers
class LogOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print("Request Origin:", request.headers.get("origin"))
        return await call_next(request)

app.add_middleware(LogOriginMiddleware)

# Get frontend URL from environment variable
frontend_url = os.getenv("FRONTEND_URL")

if not frontend_url:
    raise RuntimeError("FRONTEND_URL environment variable not set")

# CORS setup using the environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(user_api, prefix="/api")
