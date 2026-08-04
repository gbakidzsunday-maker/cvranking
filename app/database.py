"""
Data Persistence Layer
-----------------------
Sets up the SQLAlchemy engine, session factory, and declarative base used
by every model in the system (USER, JOB_SEEKER, EMPLOYER, RESUME,
JOB_POSTING, APPLICATION, SCREENING_RESULT).

Uses SQLite by default (zero-config, file-based) so the project runs out
of the box. Swap SQLALCHEMY_DATABASE_URL for a Postgres/MySQL URL for
production deployment without changing any other file.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./job_portal.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed only for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
