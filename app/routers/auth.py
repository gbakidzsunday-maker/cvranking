from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.utils.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    if user_in.role == models.RoleEnum.employer and not user_in.company_name:
        raise HTTPException(
            status_code=422, detail="company_name is required for employer accounts."
        )

    user = models.User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.flush()  # populates user.user_id before commit

    if user_in.role == models.RoleEnum.job_seeker:
        db.add(models.JobSeeker(
            user_id=user.user_id,
            phone=user_in.phone,
            location=user_in.location,
        ))
    elif user_in.role == models.RoleEnum.employer:
        db.add(models.Employer(
            user_id=user.user_id,
            company_name=user_in.company_name,
            industry=user_in.industry,
        ))

    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}
