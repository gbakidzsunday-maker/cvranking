"""
Semantic Matching Engine (Chapter 3.3, layer 2b)
---------------------------------------------------
Loads the sentence-transformers/all-MiniLM-L6-v2 model ONCE at startup
(loading it per-request would be slow) and exposes helpers to:
  - generate a 384-dimensional embedding for a piece of text
  - compute cosine similarity between two embeddings

The model is free and runs locally — no external API calls or API keys
are required.
"""
from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """
    Lazily load and cache the embedding model as a singleton.
    First call downloads the model (~90MB) to the local HF cache;
    every subsequent call reuses the already-loaded model in memory.
    """
    return SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> List[float]:
    model = get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def compute_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """Cosine similarity between two embedding vectors, returned as 0-1."""
    a = np.array(vector_a, dtype=np.float32)
    b = np.array(vector_b, dtype=np.float32)
    score = util.cos_sim(a, b).item()
    # Embeddings are normalized, so cos_sim is already in [-1, 1]; clamp for safety.
    return max(0.0, min(1.0, score))
