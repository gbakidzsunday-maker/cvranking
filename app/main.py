"""
AI-Powered Online Job Portal — FastAPI Application Layer (Chapter 3.3)

Wires together the four modules described in the design:
  - Resume Parsing and Pre-processing Module (app/utils/text_extraction.py)
  - Semantic Matching Engine (app/utils/embedding.py)
  - Ranking and Shortlisting Module (app/routers/screening.py)
  - Data Persistence Layer (app/database.py, app/models.py)

Run locally with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive Swagger UI.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, resumes, jobs, screening
from app.utils.embedding import get_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (fine for SQLite/dev; use Alembic
    # migrations for production Postgres deployments).
    Base.metadata.create_all(bind=engine)
    # Warm up the embedding model once at startup instead of on the
    # first request, so the first real user isn't hit with the load time.
    get_model()
    yield


app = FastAPI(
    title="AI-Powered Online Job Portal API",
    description=(
        "Backend for resume upload, semantic screening (all-MiniLM-L6-v2), "
        "and candidate ranking."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the React frontend (any origin during development) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(screening.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "AI-Powered Job Portal API is running."}
