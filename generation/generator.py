"""Generates an answer with inline citations from retrieved chunks, using Groq
(free-tier hosting of open-weight models) via its OpenAI-compatible API.

Runs the scope/guardrail classifier (CLAUDE.md §3.4, guardrail/classifier.py)
before doing anything else:
- "out_of_scope" questions are declined immediately — no retrieval, no
  generation call.
- "individualized_advice" questions still get retrieval + generation, but
  with a system prompt that forbids a definitive personal determination and
  requires an explicit RCIC/lawyer redirect.
- "factual" questions get the normal cited-answer treatment (CLAUDE.md §3.5).
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from guardrail.classifier import classify_query
from retrieval.reranker import retrieve_and_rerank
from retrieval.vector_store import query as vector_search
from temporal.conflict_detector import detect_conflicts

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GENERATION_MODEL = "openai/gpt-oss-120b"
MAX_TOKENS = 2048

# Reranking loads a second ONNX model (~140MB) on top of the embedding model
# and bumps peak memory past 512MB — too much for Render's free tier
# (measured ~508MB for embedding+rerank alone, before FastAPI/uvicorn/Groq
# client overhead even loads). Off by default there; flip back on with an
# env var once/if hosted with more headroom, no code change needed.
ENABLE_RERANKING = os.environ.get("ENABLE_RERANKING", "true").lower() != "false"


def retrieve_chunks(question: str, top_k: int = 5) -> list[dict]:
    if ENABLE_RERANKING:
        return retrieve_and_rerank(question, top_k=top_k)
    return vector_search(question, top_k=top_k)
DEFAULT_TOP_K = 5

OUT_OF_SCOPE_ANSWER = (
    "I can only help with questions about Canadian study permits and related IRCC immigration "
    "guidance — things like study permit eligibility, PGWP eligibility, and working while "
    "studying. That question is outside what I can answer here."
)

BASE_RULES = """You are an assistant that answers questions about Canadian study permits \
and related IRCC immigration guidance, using ONLY the numbered source excerpts provided in \
the user message.

Rules:
- Cite every factual claim with the bracketed source number it came from, using plain ASCII \
square brackets exactly like [1] or [2] — never full-width/unicode brackets such as 【1】.
- Every source excerpt has a "Last modified" date. If two sources conflict, point out both \
dates explicitly, prefer the more recently modified one, and flag the conflict rather than \
silently picking one.
- If the provided sources don't contain enough information to answer, say so plainly instead \
of guessing or using outside knowledge.
- End your answer with a "Sources:" section listing, for each source you cited, its bracket \
number, URL, and "last verified" date (the source's Last modified date).
"""

FACTUAL_SYSTEM_PROMPT = (
    BASE_RULES
    + "\nAnswer the question directly using the sources above."
)

INDIVIDUALIZED_ADVICE_SYSTEM_PROMPT = (
    BASE_RULES
    + """
IMPORTANT: this question asks for an individualized eligibility or advice determination about \
the user's own specific situation. You must NOT state or imply whether they personally \
qualify, will be approved, or what they specifically should do. Instead:
- Explain the relevant general rules and criteria from the sources, with citations, so the \
user understands what factors matter.
- Explicitly and clearly state that determining how these rules apply to their specific case \
requires a licensed RCIC (Regulated Canadian Immigration Consultant) or immigration lawyer — \
this tool provides general information only, not individualized legal advice.
"""
)


def _client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your shell environment or a .env file "
            "in the project root (see .env.example)."
        )
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)


def _format_sources(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(
            f"[{i}] {c['page_title']} — {c['section_heading']}\n"
            f"URL: {c['source_url']}\n"
            f"Last modified: {c['date_last_modified'] or 'unknown'}\n"
            f"Content: {c['text']}"
        )
    return "\n\n".join(blocks)


def _format_conflicts_block(conflicts: list, index_by_chunk_id: dict[str, int]) -> str:
    if not conflicts:
        return ""
    lines = [
        "\nDetected potential temporal conflicts (verify and address explicitly — state "
        "both dates and prefer the more recently modified source):"
    ]
    for c in conflicts:
        n_a, n_b = index_by_chunk_id[c.chunk_id_a], index_by_chunk_id[c.chunk_id_b]
        lines.append(
            f"- [{n_a}] (last modified {c.date_a}) and [{n_b}] (last modified {c.date_b}) "
            f"both address \"{c.section_heading_a}\" / \"{c.section_heading_b}\" — check whether they agree."
        )
    return "\n".join(lines)


def answer_question(question: str, top_k: int = DEFAULT_TOP_K) -> dict:
    classification = classify_query(question)
    category = classification["category"]

    if category == "out_of_scope":
        return {"answer": OUT_OF_SCOPE_ANSWER, "sources": [], "category": category, "temporal_conflicts": []}

    chunks = retrieve_chunks(question, top_k=top_k)
    if not chunks:
        return {
            "answer": "I don't have any indexed guidance to answer that.",
            "sources": [],
            "category": category,
            "temporal_conflicts": [],
        }

    index_by_chunk_id = {c["chunk_id"]: i for i, c in enumerate(chunks, start=1)}
    conflicts = detect_conflicts(chunks)

    system_prompt = (
        INDIVIDUALIZED_ADVICE_SYSTEM_PROMPT if category == "individualized_advice" else FACTUAL_SYSTEM_PROMPT
    )
    user_message = (
        f"Sources:\n\n{_format_sources(chunks)}\n"
        f"{_format_conflicts_block(conflicts, index_by_chunk_id)}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the sources above, with inline [n] citations."
    )

    response = _client().chat.completions.create(
        model=GENERATION_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    answer_text = response.choices[0].message.content

    return {
        "answer": answer_text,
        "category": category,
        "sources": [
            {
                "n": i,
                "url": c["source_url"],
                "page_title": c["page_title"],
                "section_heading": c["section_heading"],
                "date_last_modified": c["date_last_modified"],
            }
            for i, c in enumerate(chunks, start=1)
        ],
        "temporal_conflicts": [
            {
                "source_n_a": index_by_chunk_id[c.chunk_id_a],
                "source_n_b": index_by_chunk_id[c.chunk_id_b],
                "date_a": c.date_a,
                "date_b": c.date_b,
                "url_a": c.source_url_a,
                "url_b": c.source_url_b,
            }
            for c in conflicts
        ],
    }


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What are the eligibility requirements for a study permit?"
    result = answer_question(question)
    print(f"Q: {question}  [category: {result['category']}]\n")
    print(result["answer"])
