"""Wraps the local embedding model used for both indexing and querying.

Uses BAAI/bge-small-en-v1.5 via fastembed (ONNX Runtime) rather than
sentence-transformers/torch — same model, far smaller memory footprint (no
torch), which matters on memory-constrained hosts (hit an OOM on Render's
free 512MB tier with the torch-based stack). Still runs locally, no API key.
"""

from __future__ import annotations

from fastembed import TextEmbedding

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# bge models expect an instruction prefix on the query side only (not on the
# passages/chunks being indexed) for short-query-to-passage retrieval.
# fastembed's own query_embed() does NOT add this automatically (verified:
# it returns the same vector as embed() for this model), so it's still done
# by hand here.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# fastembed's default batch_size (256) processes the whole corpus in one
# ONNX batch, padded to the longest sequence and multiplied across every
# transformer layer's activations — measured this spiking RSS to ~3.7GB for
# just 253 short chunks (vs. ~270MB at batch_size=2), which alone blew the
# 512MB Render free-tier cap. Only matters for embed_passages (index
# building, called once at startup); embed_query always embeds a single
# string so batching doesn't apply there.
INDEX_BATCH_SIZE = 2

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [e.tolist() for e in _get_model().embed(texts, batch_size=INDEX_BATCH_SIZE)]


def embed_query(text: str) -> list[float]:
    return list(_get_model().embed([QUERY_INSTRUCTION + text]))[0].tolist()
