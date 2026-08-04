# Deploy target: Render free web service (512MB RAM, 0.1 CPU, no persistent disk).
#
# Two things this Dockerfile does specifically to survive that free tier:
#   1. Installs the CPU-only PyTorch wheel (the default PyPI wheel bundles
#      CUDA/GPU support and is much larger and more memory-hungry than
#      needed for CPU-only inference on a small sentence-transformers model).
#   2. Downloads and caches the all-MiniLM-L6-v2 model at BUILD time, so it
#      is already on disk inside the image. Render's free tier has no
#      persistent disk, so if the model were downloaded at runtime instead,
#      it would re-download from Hugging Face on every cold start (after
#      each 15-minute idle spin-down) — slow, and a network dependency you
#      don't want on your app's critical path.

FROM python:3.12-slim

WORKDIR /app

# System deps needed by PyMuPDF / bcrypt build steps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# CPU-only torch first (small footprint), then the rest of the requirements
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image so no runtime download is needed.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

# Render sets $PORT at runtime; default to 8000 for local docker run.
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
