from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.utils.auth import require_role
from app.utils.embedding import generate_embedding

router = APIRouter(prefix="/jobs", tags=["Job Postings"])


@router.post("/", response_model=schemas.JobPostingOut, status_code=201)
def create_job_posting(
    job_in: schemas.JobPostingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(models.RoleEnum.employer)),
):
    employer = (
        db.query(models.Employer)
        .filter(models.Employer.user_id == current_user.user_id)
        .first()
    )
    if not employer:
        raise HTTPException(status_code=404, detail="Employer profile not found.")

    # Combine title + description + required skills for a richer embedding.
    text_for_embedding = " ".join(
        filter(None, [job_in.title, job_in.description, job_in.required_skills])
    )
    embedding = generate_embedding(text_for_embedding)

    job = models.JobPosting(
        employer_id=employer.employer_id,
        title=job_in.title,
        description=job_in.description,
        required_skills=job_in.required_skills,
    )
    job.set_embedding(embedding)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/", response_model=list[schemas.JobPostingOut])
def list_job_postings(db: Session = Depends(get_db)):
    return db.query(models.JobPosting).order_by(models.JobPosting.posted_at.desc()).all()


@router.get("/{job_id}", response_model=schemas.JobPostingOut)
def get_job_posting(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.JobPosting).filter(models.JobPosting.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    return job
