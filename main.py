# from dotenv import load_dotenv

# from agents.whatsapp_sender_agent import WhatsAppSenderAgent
# load_dotenv()

# import os
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.requests import Request


# from api.api_endpoints import router as user_api
# from db.init_db import create_db_and_tables

# import asyncio, sys
# if sys.platform.startswith("win"):
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# app = FastAPI()

# # Middleware to log Origin headers
# class LogOriginMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         print("Request Origin:", request.headers.get("origin"))
#         return await call_next(request)

# app.add_middleware(LogOriginMiddleware)

# # Get frontend URL from environment variable
# frontend_url = os.getenv("FRONTEND_URL")

# if not frontend_url:
#     raise RuntimeError("FRONTEND_URL environment variable not set")

# # CORS setup using the environment variable
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[frontend_url],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.on_event("startup")
# def on_startup():
#     create_db_and_tables()


# wa_sender = WhatsAppSenderAgent()

# @app.on_event("shutdown")
# async def shutdown_event():
#     await wa_sender.close()
#     print("[WA] Cleaned up resources")


# app.include_router(user_api, prefix="/api")


from dotenv import load_dotenv
load_dotenv()  # Load environment variables FIRST

import os
import asyncio
import sys

# Set event loop policy for Windows BEFORE any async operations
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Import after environment setup
# from agents.whatsapp_sender_agent import WhatsAppSenderAgent
from api.api_endpoints import router as user_api
from db.init_db import create_db_and_tables

app = FastAPI()

# Middleware to log Origin headers
class LogOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        print(f"Request Origin: {origin}")
        response = await call_next(request)
        return response

app.add_middleware(LogOriginMiddleware)

# Get frontend URL from environment variable with default
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

# CORS setup - allow multiple common frontend URLs for development
allowed_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://localhost:8000"  # Allow API itself for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    print("Database initialized")
    
    # Start automatic reply checking scheduler
    try:
        from services.automatic_reply_scheduler import start_automatic_reply_checking
        scheduler = start_automatic_reply_checking()
        print("🚀 Automatic reply checking scheduler started")
        print(f"📋 Scheduler config: {scheduler.config}")
    except Exception as e:
        print(f"❌ Failed to start automatic reply scheduler: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("shutdown") 
async def on_shutdown():
    # Stop automatic reply checking scheduler
    try:
        from services.automatic_reply_scheduler import stop_automatic_reply_checking
        stop_automatic_reply_checking()
        print("🛑 Automatic reply checking scheduler stopped")
    except Exception as e:
        print(f"❌ Error stopping scheduler: {e}")


app.include_router(user_api, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    # pass the app object directly, not the "module:app" string
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        # note: 'reload' only works via the CLI, so drop it here
    )
