"""
SQLAlchemy database connection setup for the Temporal Agent POC.
Configures PostgreSQL connection and provides session management for all database operations.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connect to PostgreSQL using environment variable, with a fallback for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://dev:dev@localhost:5432/intern")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# This function creates all tables defined in models.py if they don't exist
def init_db():
    from . import models  # This import is necessary to register the models with Base
    Base.metadata.create_all(bind=engine)
