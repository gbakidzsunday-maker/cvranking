"""
Pydantic schemas — request/response contracts for the API layer.
Kept separate from the ORM models (app/models.py) so DB structure and
API structure can evolve independently.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr

from app.models import RoleEnum, ApplicationStatus


# ---------- Auth / Users ----------

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: RoleEnum
    # Optional role-specific fields
    company_name: Optional[str] = None      # required if role == employer
    industry: Optional[str] = None
    phone: Optional[str] = None             # optional if role == job_seeker
    location: Optional[str] = None


class UserOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: RoleEnum
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Resumes ----------

class ResumeOut(BaseModel):
    resume_id: int
    seeker_id: int
    file_path: str
    uploaded_at: datetime
    text_preview: Optional[str] = None  # first ~300 chars of raw_text

    class Config:
        from_attributes = True


# ---------- Job Postings ----------

class JobPostingCreate(BaseModel):
    title: str
    description: str
    required_skills: Optional[str] = None


class JobPostingOut(BaseModel):
    job_id: int
    employer_id: int
    title: str
    description: str
    required_skills: Optional[str]
    posted_at: datetime

    class Config:
        from_attributes = True


# ---------- Applications ----------

class ApplicationCreate(BaseModel):
    resume_id: int
    job_id: int


class ApplicationOut(BaseModel):
    application_id: int
    resume_id: int
    job_id: int
    status: ApplicationStatus
    applied_at: datetime

    class Config:
        from_attributes = True


# ---------- Screening / Ranking ----------

class RankedCandidate(BaseModel):
    application_id: int
    resume_id: int
    seeker_id: int
    candidate_name: str
    similarity_score: float
    rank_position: int
    status: ApplicationStatus


class ScreeningResultOut(BaseModel):
    application_id: int
    similarity_score: float
    rank_position: Optional[int]
    processed_at: datetime

    class Config:
        from_attributes = True
