"""
ORM models for the seven core entities defined in the project's ERD:
USER, JOB_SEEKER, EMPLOYER, RESUME, JOB_POSTING, APPLICATION,
SCREENING_RESULT.

Embedding vectors (384-dim, from all-MiniLM-L6-v2) are stored as JSON
text rather than a dedicated vector database, matching the design
decision explained in Chapter 3.6 (avoids unnecessary architectural
complexity for an academic-scale project).
"""
import enum
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Enum, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    job_seeker = "job_seeker"
    employer = "employer"
    admin = "admin"


class ApplicationStatus(str, enum.Enum):
    submitted = "submitted"
    shortlisted = "shortlisted"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job_seeker = relationship("JobSeeker", back_populates="user", uselist=False)
    employer = relationship("Employer", back_populates="user", uselist=False)


class JobSeeker(Base):
    __tablename__ = "job_seekers"

    seeker_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    phone = Column(String(30), nullable=True)
    location = Column(String(150), nullable=True)
    skills_summary = Column(Text, nullable=True)

    user = relationship("User", back_populates="job_seeker")
    resumes = relationship("Resume", back_populates="job_seeker")


class Employer(Base):
    __tablename__ = "employers"

    employer_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    company_name = Column(String(150), nullable=False)
    industry = Column(String(150), nullable=True)

    user = relationship("User", back_populates="employer")
    job_postings = relationship("JobPosting", back_populates="employer")


class Resume(Base):
    __tablename__ = "resumes"

    resume_id = Column(Integer, primary_key=True, index=True)
    seeker_id = Column(Integer, ForeignKey("job_seekers.seeker_id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=True)
    embedding_vector = Column(Text, nullable=True)  # JSON-encoded list[float]
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    job_seeker = relationship("JobSeeker", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")

    def set_embedding(self, vector):
        self.embedding_vector = json.dumps(vector)

    def get_embedding(self):
        return json.loads(self.embedding_vector) if self.embedding_vector else None


class JobPosting(Base):
    __tablename__ = "job_postings"

    job_id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.employer_id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(Text, nullable=True)
    embedding_vector = Column(Text, nullable=True)  # JSON-encoded list[float]
    posted_at = Column(DateTime, default=datetime.utcnow)

    employer = relationship("Employer", back_populates="job_postings")
    applications = relationship("Application", back_populates="job_posting")

    def set_embedding(self, vector):
        self.embedding_vector = json.dumps(vector)

    def get_embedding(self):
        return json.loads(self.embedding_vector) if self.embedding_vector else None


class Application(Base):
    __tablename__ = "applications"

    application_id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.resume_id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_postings.job_id"), nullable=False)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.submitted)
    applied_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="applications")
    job_posting = relationship("JobPosting", back_populates="applications")
    screening_result = relationship(
        "ScreeningResult", back_populates="application", uselist=False
    )


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    result_id = Column(Integer, primary_key=True, index=True)
    application_id = Column(
        Integer, ForeignKey("applications.application_id"), unique=True, nullable=False
    )
    similarity_score = Column(Float, nullable=False)
    rank_position = Column(Integer, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="screening_result")
