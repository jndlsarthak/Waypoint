"""Scope/guardrail classifier — CLAUDE.md §3.4.

Classifies each incoming question into one of three categories BEFORE any
retrieval or generation call:

1. "factual"               -> answer normally, with citations.
2. "individualized_advice"  -> do not answer definitively; respond with
                               relevant general guidance + an explicit
                               redirect to a licensed RCIC/immigration lawyer.
3. "out_of_scope"           -> decline (not about Canadian study permits or
                               related IRCC guidance at all).

Uses a small, cheap model (gpt-oss-20b) rather than the stronger model used
for generation (gpt-oss-120b) — this is a lightweight prompt-based
classifier per CLAUDE.md's "v1 is fine" guidance, not a trained classifier.
"""

from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
CLASSIFIER_MODEL = "openai/gpt-oss-20b"

CATEGORIES = ("factual", "individualized_advice", "out_of_scope")
DEFAULT_CATEGORY = "factual"

SYSTEM_PROMPT = """You classify questions for a Canadian study-permit / immigration \
information tool. Classify the user's question into EXACTLY one category:

- "factual": a general, informational question about published IRCC rules, requirements, \
processes, deadlines, or definitions. Example: "What's the minimum funds requirement for a \
study permit?", "How many hours can I work off campus?".

- "individualized_advice": the question asks whether THIS SPECIFIC PERSON, given their own \
facts/situation, qualifies, will be approved, or what they personally should do. Signals: \
first-person specific facts about their own case, or asking for a prediction/decision about \
their own situation. Example: "I have a criminal record from 10 years ago, can I still get a \
permit?", "Will I qualify for a PGWP given my program?", "Should I apply now or wait?".

- "out_of_scope": not about Canadian study permits, PGWP, or work-while-studying immigration \
guidance at all. Example: immigration systems of other countries, unrelated general knowledge, \
coding help, small talk.

Respond with ONLY a JSON object of the form {"category": "...", "reason": "<one short \
sentence>"} and nothing else.
"""


def _client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)


def classify_query(question: str) -> dict:
    """Returns {"category": one of CATEGORIES, "reason": str}.

    Falls back to DEFAULT_CATEGORY ("factual") on any classifier failure —
    answering a question is a safer failure mode here than silently
    refusing every question if the classifier call breaks.
    """
    try:
        response = _client().chat.completions.create(
            model=CLASSIFIER_MODEL,
            max_tokens=150,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        raw = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001 - deliberate broad catch for a non-critical classifier call
        return {"category": DEFAULT_CATEGORY, "reason": f"classifier call failed ({exc}); defaulting"}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"category": DEFAULT_CATEGORY, "reason": "classifier returned unparseable output; defaulting"}

    category = parsed.get("category")
    if category not in CATEGORIES:
        return {"category": DEFAULT_CATEGORY, "reason": f"unrecognized category {category!r}; defaulting"}

    return {"category": category, "reason": parsed.get("reason", "")}


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Will I qualify for a study permit given my situation?"
    result = classify_query(question)
    print(f"Q: {question}\n-> {result}")
