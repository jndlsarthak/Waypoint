"""Cross-encoder reranking — CLAUDE.md §3.3, Phase 6 iteration.

Phase 2/4 diagnosed a real weakness: bge-small's embedding similarity doesn't
discriminate finely enough in this narrow, jargon-dense corpus (e.g. the
exact chunk answering "What are the eligibility requirements for a study
permit?" ranked ~80th of 224 by cosine similarity). A cross-encoder scores
the query and a candidate's text together (instead of comparing two
independent embeddings), which is slower per-pair but much more precise —
exactly the fix CLAUDE.md names for this failure mode.

Pulls a larger candidate pool from the embedding-based vector store, then
reranks it down to top_k with the cross-encoder before generation sees it.

Caveat found while building this: on that exact adversarial query, the
cross-encoder (tried both ms-marco-MiniLM-L-6-v2 and -L-12-v2) still scores a
PGWP-overview chunk that repeats "eligibility requirements" three times far
higher (+7.9) than the actually-correct study-permit chunk (-2.0), which
never uses that literal phrase. Reranking fixes cases where the embedding
stage's candidate pool contains the right chunk but ranks it too low
generally; it doesn't fix strong literal lexical-overlap traps like this
one. Left as a documented hard case rather than chased further with bigger
models (diminishing returns for a portfolio project's iteration budget).
"""

from __future__ import annotations

from fastembed.rerank.cross_encoder import TextCrossEncoder

from retrieval.vector_store import query as vector_search

# ONNX Runtime build of the same model (via fastembed) instead of
# sentence-transformers/torch — see embedder.py for why (Render OOM).
RERANKER_MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"
DEFAULT_CANDIDATE_K = 30

# Same batching issue as embedder.py's INDEX_BATCH_SIZE: the default batch
# size processes all candidates as one padded ONNX batch, spiking memory —
# worse here since cross-encoders run joint attention over query+doc pairs.
RERANK_BATCH_SIZE = 1

_model: TextCrossEncoder | None = None


def _get_model() -> TextCrossEncoder:
    global _model
    if _model is None:
        _model = TextCrossEncoder(model_name=RERANKER_MODEL_NAME)
    return _model


def retrieve_and_rerank(question: str, top_k: int = 5, candidate_k: int = DEFAULT_CANDIDATE_K) -> list[dict]:
    candidates = vector_search(question, top_k=candidate_k)
    if not candidates:
        return []

    scores = _get_model().rerank(question, [c["text"] for c in candidates], batch_size=RERANK_BATCH_SIZE)

    ranked = sorted(zip(candidates, scores), key=lambda pair: -pair[1])
    return [chunk for chunk, _ in ranked[:top_k]]
