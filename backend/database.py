import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load variables from .env
load_dotenv()

# Use the environment variable, or a fallback if it's missing
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Used as a FastAPI ``Depends(get_db)`` so each request gets its own
    session and the connection is always returned to the pool.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Limit pdoc's rendered surface to the public API. The hidden symbols
# (engine, SessionLocal, SQLALCHEMY_DATABASE_URL) are still importable
# in Python; this just keeps their values out of the docs HTML, since
# their reprs would leak the local connection string.
__all__ = ["Base", "get_db"]
        