# db/session.py
from sqlmodel import Session, create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# --------------------------------------------------------------------------- #
# 1.  Load environment variables (DATABASE_URL, etc.)
# --------------------------------------------------------------------------- #
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment")

# --------------------------------------------------------------------------- #
# 2.  Create the engine with a pool sized for Azure PostgreSQL
# --------------------------------------------------------------------------- #
engine = create_engine(
    DATABASE_URL,
    echo=True,          # SQL echo logs; set False in production if noisy
    pool_size=10,       # permanent connections kept open
    max_overflow=20,    # extra burst connections
    pool_timeout=30,    # seconds to wait before TimeoutError
    pool_recycle=1_800, # recycle conns every 30 min (Azure idle timeout)
    pool_pre_ping=True, # validate (ping) conn before each checkout
)

# --------------------------------------------------------------------------- #
# 3.  Session helpers
# --------------------------------------------------------------------------- #

# 3-A. Plain factory for scripts, background tasks, agents, etc.
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,  # keep objects usable after commit() by default
)

# 3-B. FastAPI dependency – yields a session and always closes it
def get_session():
    """
    FastAPI dependency that provides a short-lived SQLModel Session.
    The connection is returned to the pool as soon as the request finishes.
    """
    with SessionLocal() as session:
        yield session
