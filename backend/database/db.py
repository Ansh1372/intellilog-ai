import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/intellilog"
)

logger.info(f"[DB] Connecting to database: {DATABASE_URL.split('@')[-1]}")

try:
    engine = create_engine(DATABASE_URL)
    logger.info("[DB] Database engine created successfully")

except Exception as e:
    logger.error(f"[DB] Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """FastAPI dependency for DB session management."""
    logger.debug("[DB] Opening new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("[DB] Database session closed")
