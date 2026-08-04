import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.utils.auth import get_current_user, require_role
from app.utils.text_extraction import extract_text
from app.utils.embedding import generate_embedding

router = APIRouter(prefix="/resumes", tags=["Resumes"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=schemas.ResumeOut, status_code=201)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(models.RoleEnum.job_seeker)),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are accepted.")

    job_seeker = (
        db.query(models.JobSeeker)
        .filter(models.JobSeeker.user_id == current_user.user_id)
        .first()
    )
    if not job_seeker:
        raise HTTPException(status_code=404, detail="Job seeker profile not found.")

    # Save the uploaded file to disk with a unique name to avoid collisions.
    unique_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # --- Resume Parsing and Pre-processing Module ---
    raw_text = extract_text(saved_path, file.filename)

    # --- Semantic Matching Engine: generate embedding immediately on upload ---
    embedding = generate_embedding(raw_text)

    resume = models.Resume(
        seeker_id=job_seeker.seeker_id,
        file_path=saved_path,
        raw_text=raw_text,
    )
    resume.set_embedding(embedding)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return schemas.ResumeOut(
        resume_id=resume.resume_id,
        seeker_id=resume.seeker_id,
        file_path=resume.file_path,
        uploaded_at=resume.uploaded_at,
        text_preview=raw_text[:300],
    )


@router.get("/mine", response_model=list[schemas.ResumeOut])
def list_my_resumes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(models.RoleEnum.job_seeker)),
):
    job_seeker = (
        db.query(models.JobSeeker)
        .filter(models.JobSeeker.user_id == current_user.user_id)
        .first()
    )
    if not job_seeker:
        return []

    resumes = (
        db.query(models.Resume)
        .filter(models.Resume.seeker_id == job_seeker.seeker_id)
        .all()
    )
    return [
        schemas.ResumeOut(
            resume_id=r.resume_id,
            seeker_id=r.seeker_id,
            file_path=r.file_path,
            uploaded_at=r.uploaded_at,
            text_preview=(r.raw_text or "")[:300],
        )
        for r in resumes
    ]
