"""
Ranking and Shortlisting Module (Chapter 3.3, layer 2c)
----------------------------------------------------------
Two responsibilities live here:

1. POST /applications  — a job seeker applies to a job posting. This
   immediately runs the semantic matching engine: it loads the resume's
   and job's stored embeddings, computes cosine similarity, and stores
   the result in SCREENING_RESULT.

2. GET /jobs/{job_id}/ranked-candidates — an employer-facing endpoint
   that returns every applicant for a job, ordered by similarity score
   (highest first), i.e. the ranked shortlist described in Chapter 3.5.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.utils.auth import require_role
from app.utils.embedding import compute_similarity

router = APIRouter(tags=["Screening & Ranking"])

# Candidates scoring at or above this threshold are auto-marked "shortlisted".
# Configurable per Chapter 3.5 ("configurable threshold").
SIMILARITY_THRESHOLD = 0.45


@router.post("/applications", response_model=schemas.ScreeningResultOut, status_code=201)
def apply_to_job(
    application_in: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(models.RoleEnum.job_seeker)),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.resume_id == application_in.resume_id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    job_seeker = (
        db.query(models.JobSeeker)
        .filter(models.JobSeeker.user_id == current_user.user_id)
        .first()
    )
    if not job_seeker or resume.seeker_id != job_seeker.seeker_id:
        raise HTTPException(status_code=403, detail="This resume does not belong to you.")

    job = (
        db.query(models.JobPosting)
        .filter(models.JobPosting.job_id == application_in.job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")

    existing = (
        db.query(models.Application)
        .filter(
            models.Application.resume_id == resume.resume_id,
            models.Application.job_id == job.job_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already applied with this resume.")

    # --- Semantic Matching Engine ---
    resume_vector = resume.get_embedding()
    job_vector = job.get_embedding()
    if resume_vector is None or job_vector is None:
        raise HTTPException(
            status_code=422,
            detail="Missing embeddings for resume or job posting; cannot screen application.",
        )
    similarity_score = compute_similarity(resume_vector, job_vector)

    status = (
        models.ApplicationStatus.shortlisted
        if similarity_score >= SIMILARITY_THRESHOLD
        else models.ApplicationStatus.submitted
    )

    application = models.Application(
        resume_id=resume.resume_id, job_id=job.job_id, status=status
    )
    db.add(application)
    db.flush()  # get application_id

    result = models.ScreeningResult(
        application_id=application.application_id,
        similarity_score=similarity_score,
    )
    db.add(result)
    db.commit()

    # --- Ranking Module: recompute rank_position for all applicants of this job ---
    _recompute_rankings(db, job.job_id)
    db.refresh(result)

    return result


def _recompute_rankings(db: Session, job_id: int):
    """Re-ranks every screening result for a job, best score = rank 1."""
    results = (
        db.query(models.ScreeningResult)
        .join(models.Application)
        .filter(models.Application.job_id == job_id)
        .order_by(models.ScreeningResult.similarity_score.desc())
        .all()
    )
    for position, result in enumerate(results, start=1):
        result.rank_position = position
    db.commit()


@router.get(
    "/jobs/{job_id}/ranked-candidates",
    response_model=list[schemas.RankedCandidate],
)
def get_ranked_candidates(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(models.RoleEnum.employer)),
):
    job = db.query(models.JobPosting).filter(models.JobPosting.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")

    employer = (
        db.query(models.Employer)
        .filter(models.Employer.user_id == current_user.user_id)
        .first()
    )
    if not employer or job.employer_id != employer.employer_id:
        raise HTTPException(status_code=403, detail="This job posting does not belong to you.")

    applications = (
        db.query(models.Application)
        .filter(models.Application.job_id == job_id)
        .join(models.ScreeningResult)
        .order_by(models.ScreeningResult.rank_position.asc())
        .all()
    )

    ranked = []
    for app_ in applications:
        resume = app_.resume
        job_seeker = resume.job_seeker
        user = job_seeker.user
        ranked.append(
            schemas.RankedCandidate(
                application_id=app_.application_id,
                resume_id=resume.resume_id,
                seeker_id=job_seeker.seeker_id,
                candidate_name=user.full_name,
                similarity_score=round(app_.screening_result.similarity_score, 4),
                rank_position=app_.screening_result.rank_position,
                status=app_.status,
            )
        )
    return ranked
