# AI-Powered Online Job Portal — Backend (FastAPI)

Implements the Application/API Layer described in Chapter 3 of the project:
resume upload → text extraction → semantic embedding (`sentence-transformers/all-MiniLM-L6-v2`)
→ cosine similarity → candidate ranking.

## 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The first time the server starts, it will download the free, open-source
`all-MiniLM-L6-v2` model (~90MB) from Hugging Face and cache it locally.
No API key is required.

## 2. Run

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive Swagger UI — you
can register, log in, upload resumes, post jobs, and view rankings
directly from the browser without a frontend.

## 3. Typical flow (matches Chapter 3.5 flowchart)

1. `POST /auth/register` — create a `job_seeker` or `employer` account.
2. `POST /auth/login` — get a JWT (`access_token`).
3. `POST /resumes/upload` *(job seeker, auth required)* — upload a PDF/DOCX
   resume. Text is extracted and an embedding is generated and stored
   immediately.
4. `POST /jobs/` *(employer, auth required)* — post a vacancy. Its
   description is embedded and stored.
5. `POST /applications` *(job seeker, auth required)* — apply with a
   resume to a job. This is where the **semantic matching engine** runs:
   cosine similarity is computed between the resume and job embeddings,
   the result is stored, and every application for that job is
   re-ranked.
6. `GET /jobs/{job_id}/ranked-candidates` *(employer, auth required)* —
   returns applicants sorted by similarity score, highest first —
   the ranked shortlist shown on the employer dashboard.

## 4. Project structure

```
app/
  main.py              FastAPI app, CORS, startup (creates DB tables, warms up model)
  database.py          SQLAlchemy engine/session (SQLite by default)
  models.py            ORM models for the 7 ERD entities
  schemas.py           Pydantic request/response schemas
  routers/
    auth.py            Register / login (JWT)
    resumes.py         Resume upload + text extraction + embedding
    jobs.py             Job posting creation + embedding
    screening.py       Apply-to-job + semantic similarity + ranking
  utils/
    auth.py            Password hashing, JWT issue/verify, role guards
    text_extraction.py PDF/DOCX text extraction (PyMuPDF, python-docx)
    embedding.py       Loads all-MiniLM-L6-v2 once, generates embeddings,
                        computes cosine similarity
requirements.txt
uploads/                Uploaded resume files land here
```

## 5. Deploying to Render (free tier)

Render's free web service has **512 MB RAM** and **no persistent disk**.
Two adjustments matter for that:

1. **Use the Dockerfile in this repo**, don't use Render's native Python
   runtime. It installs the CPU-only PyTorch wheel (the default PyPI wheel
   bundles CUDA support you don't need and won't fit in 512MB) and
   downloads `all-MiniLM-L6-v2` **at build time**, baking it into the
   image. This avoids re-downloading the model from Hugging Face on every
   cold start (Render free instances spin down after 15 min idle, and
   with no persistent disk a runtime download would repeat on every wake-up).

2. **On Render**: New → Web Service → connect this repo → set
   **Environment: Docker** (it will auto-detect the `Dockerfile`) →
   set the `JWT_SECRET_KEY` environment variable to a random string →
   deploy.

**Things to watch on the free tier:**
- Build will take a few minutes the first time (downloading torch + the
  model) — this counts against Render's monthly build-minutes allowance,
  but only runs on deploy, not on every request.
- 512MB RAM is tight. If you see OOM crashes in the Render logs, the
  next lever to pull is switching `all-MiniLM-L6-v2` isn't the issue
  (it's already the smallest common sentence-transformers model) — the
  fix is usually upgrading to Render's paid Starter tier ($7/mo, 512MB→
  more headroom isn't guaranteed either; Standard at 2GB is safer for
  torch-based workloads).
- SQLite (`job_portal.db`) also has no persistent disk on the free tier
  — your data disappears on every redeploy/restart. Fine for a student
  project demo; for anything you need to persist, connect Render's
  Postgres (has its own free tier, 30-day expiry) and swap the
  connection string in `app/database.py`.
- Free instances sleep after 15 min idle; the first request after that
  takes ~30-60s to wake up. Don't be alarmed if a demo feels slow after
  sitting idle — it's spinning back up, not broken.

## 6. Notes

- **Database**: SQLite (`job_portal.db`) is used by default for zero-config
  local development, matching the relational design in Chapter 3.4. Swap
  the connection string in `app/database.py` for Postgres/MySQL in
  production — no other file needs to change.
- **Similarity threshold**: applications scoring ≥ 0.45 cosine similarity
  are auto-marked `shortlisted` (see `SIMILARITY_THRESHOLD` in
  `app/routers/screening.py`) — adjust this to tune sensitivity, or expose
  it as an admin-configurable setting per your Chapter 3.5 design ("a
  configurable threshold").
- **CORS** is currently open (`allow_origins=["*"]`) for development so
  your React frontend can call the API from any port. Restrict this to
  your frontend's actual origin before deployment.
- If you deploy to a host with no internet access at container build time,
  make sure the model is pre-downloaded/cached during the Docker build
  step, since it's fetched from Hugging Face on first load.
