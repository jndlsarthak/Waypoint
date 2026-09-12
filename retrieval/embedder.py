"""Wraps the local embedding model used for both indexing and querying.

Uses BAAI/bge-small-en-v1.5 (sentence-transformers) — runs locally, no API
key, no per-call cost.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# bge models expect an instruction prefix on the query side only (not on the
# passages/chunks being indexed) for short-query-to-passage retrieval.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def embed_query(text: str) -> list[float]:
    model = _get_model()
    embedding = model.encode(
        [QUERY_INSTRUCTION + text], normalize_embeddings=True, show_progress_bar=False
    )
    return embedding[0].tolist()
