"""Lightweight eval harness — CLAUDE.md §3.6/§6 Phase 5.

Runs the golden Q&A set through the full pipeline (guardrail -> retrieval ->
generation) and scores deterministic, no-extra-LLM-call metrics:

- scope_accuracy: does the classified category match the expected one?
- citation_validity_rate: for factual/individualized answers, do all [n]
  citation markers point at an actual returned source (no hallucinated
  source numbers)?
- individualized_redirect_rate: do individualized_advice answers actually
  contain the required RCIC/lawyer redirect language?
- out_of_scope_clean_rate: do out_of_scope answers correctly return zero
  sources (i.e. generation was skipped, not just declined in prose)?

This intentionally skips LLM-as-judge scoring (e.g. "does the cited chunk
really support the claim") to avoid extra API calls — that's a natural
Phase 6 enhancement once there's a reason to trust the judge model's own
accuracy on this domain. Results are heuristic signals, not ground truth.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from openai import RateLimitError

from generation.generator import answer_question

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.json"
RESULTS_PATH = Path(__file__).resolve().parent / "results.json"

CITATION_RE = re.compile(r"\[(\d+)\]")
REDIRECT_RE = re.compile(r"\bRCIC\b|immigration lawyer", re.IGNORECASE)

# Groq's free tier has a tokens-per-minute cap; a full golden-set run can get
# close to it. Pace requests and retry with backoff rather than failing the
# whole run partway through.
PACING_SECONDS = 3
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_SECONDS = 12


def _citation_numbers(text: str) -> list[int]:
    return [int(n) for n in CITATION_RE.findall(text)]


def _answer_with_retry(question: str) -> dict:
    for attempt in range(RATE_LIMIT_RETRIES):
        try:
            return answer_question(question)
        except RateLimitError:
            if attempt == RATE_LIMIT_RETRIES - 1:
                raise
            print(f"  rate limited, backing off {RATE_LIMIT_BACKOFF_SECONDS}s...")
            time.sleep(RATE_LIMIT_BACKOFF_SECONDS)


def run_eval() -> list[dict]:
    golden_set = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    results = []

    for item in golden_set:
        result = _answer_with_retry(item["question"])
        time.sleep(PACING_SECONDS)
        category = result["category"]
        answer = result["answer"]
        n_sources = len(result["sources"])

        cited = _citation_numbers(answer)
        valid_citations = [n for n in cited if 1 <= n <= n_sources]
        citation_validity = (len(valid_citations) == len(cited)) if cited else None

        row = {
            "id": item["id"],
            "question": item["question"],
            "expected_category": item["expected_category"],
            "got_category": category,
            "category_correct": category == item["expected_category"],
            "n_sources": n_sources,
            "n_citations": len(cited),
            "citation_validity": citation_validity,
            "has_redirect_language": bool(REDIRECT_RE.search(answer)) if category == "individualized_advice" else None,
            "n_temporal_conflicts": len(result.get("temporal_conflicts", [])),
        }
        results.append(row)
        print(f"[{item['id']}] expected={item['expected_category']:22s} got={category:22s} "
              f"{'OK' if row['category_correct'] else 'MISS'}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def summarize(results: list[dict]) -> None:
    n = len(results)
    scope_correct = sum(r["category_correct"] for r in results)

    factual_and_individualized = [r for r in results if r["expected_category"] in ("factual", "individualized_advice")]
    with_citations = [r for r in factual_and_individualized if r["n_citations"] > 0]
    valid_citation_rows = [r for r in with_citations if r["citation_validity"]]

    individualized = [r for r in results if r["expected_category"] == "individualized_advice"]
    redirect_ok = [r for r in individualized if r["has_redirect_language"]]

    out_of_scope = [r for r in results if r["expected_category"] == "out_of_scope"]
    clean_decline = [r for r in out_of_scope if r["n_sources"] == 0]

    print("\n=== Summary ===")
    print(f"Scope-handling accuracy:     {scope_correct}/{n} ({scope_correct/n:.0%})")
    if with_citations:
        print(f"Citation validity rate:      {len(valid_citation_rows)}/{len(with_citations)} "
              f"({len(valid_citation_rows)/len(with_citations):.0%}) of answers-with-citations "
              f"had zero hallucinated source numbers")
    if individualized:
        print(f"Individualized redirect rate: {len(redirect_ok)}/{len(individualized)} "
              f"({len(redirect_ok)/len(individualized):.0%}) correctly redirected to RCIC/lawyer")
    if out_of_scope:
        print(f"Out-of-scope clean decline:  {len(clean_decline)}/{len(out_of_scope)} "
              f"({len(clean_decline)/len(out_of_scope):.0%}) returned zero sources")


if __name__ == "__main__":
    results = run_eval()
    summarize(results)
