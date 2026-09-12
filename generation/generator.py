"""Generates an answer with inline citations from retrieved chunks, using Groq
(free-tier hosting of open-weight models, e.g. Llama) via its OpenAI-compatible API.

Phase 2 scope only: naive top-k retrieval + generation with citations (CLAUDE.md
§3.5). The scope/guardrail classifier (§3.4 — declining individualized-advice
and out-of-scope questions) is Phase 3 and is NOT implemented here yet.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from retrieval.vector_store import query as retrieve_chunks

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GENERATION_MODEL = "openai/gpt-oss-120b"
MAX_TOKENS = 2048
DEFAULT_TOP_K = 5

SYSTEM_PROMPT = """You are an assistant that answers questions about Canadian study permits \
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
- Do not make an individualized eligibility determination for the user's own situation — this \
is general informational guidance based on public IRCC guidance, not legal advice, and does \
not replace a licensed RCIC or immigration lawyer.
- End your answer with a "Sources:" section listing, for each source you cited, its bracket \
number, URL, and "last verified" date (the source's Last modified date).
"""


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


def answer_question(question: str, top_k: int = DEFAULT_TOP_K) -> dict:
    chunks = retrieve_chunks(question, top_k=top_k)
    if not chunks:
        return {"answer": "I don't have any indexed guidance to answer that.", "sources": []}

    user_message = (
        f"Sources:\n\n{_format_sources(chunks)}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the sources above, with inline [n] citations."
    )

    response = _client().chat.completions.create(
        model=GENERATION_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    answer_text = response.choices[0].message.content

    return {
        "answer": answer_text,
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
    }


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What are the eligibility requirements for a study permit?"
    result = answer_question(question)
    print(f"Q: {question}\n")
    print(result["answer"])
