"""Temporal-conflict detection — CLAUDE.md §3.3 / §4 ("Temporal handling").

Given the chunks retrieved for a query, flags pairs that appear to cover the
same specific ground but come from pages last modified on different dates —
so the caller can surface both with their dates rather than silently citing
one and ignoring the other.

Two chunks are flagged only if ALL of the following hold:
1. They come from different source pages (a page can't conflict with itself).
2. Their date_last_modified values differ (no cross-time question otherwise).
3. Their *leaf section heading* matches (case/whitespace-normalized) — e.g.
   "General eligibility — How we define work" and "Who can work off campus —
   How we define work" both match on "how we define work". This is the gate,
   not embedding similarity: this corpus is narrow and jargon-dense enough
   that bge-small scores unrelated sections (e.g. on-campus vs off-campus
   hour limits) above 0.80 cosine similarity just from shared vocabulary,
   producing false positives (confirmed while building this — see git log).
   A matching heading is a far more precise signal that two chunks are "the
   same kind of section" across pages, since headings come straight from the
   page's own document structure (Phase 1 chunking), not a fuzzy metric.
4. Their text is not byte-for-byte identical — canada.ca repeats identical
   boilerplate (e.g. "how we define work") across pages that were last
   touched on different dates for unrelated reasons; that is NOT a conflict
   and must not be flagged as one.

Note step 4 deliberately checks *exact* equality, not a fuzzy similarity
ratio: a character-level diff ratio can't tell "identical text" apart from
"the one number that matters changed" (e.g. "20 hours" vs "24 hours" scores
~99% similar by SequenceMatcher despite being the entire disagreement), so a
fuzzy threshold would silently swallow exactly the conflicts this module
exists to catch.

This is a metadata/heading heuristic (CLAUDE.md's "check via metadata dates"
half of §3.3), not true contradiction/entailment detection — it flags "these
two dated sources cover the same specific point and should both be checked,"
not "source A is definitely wrong." Embedding similarity is still computed
and returned for transparency, but only as informational context.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from retrieval.embedder import embed_passages


def _leaf_heading(section_heading: str) -> str:
    return section_heading.rsplit("—", 1)[-1].strip().lower()


@dataclass
class TemporalConflict:
    chunk_id_a: str
    chunk_id_b: str
    date_a: str
    date_b: str
    source_url_a: str
    source_url_b: str
    section_heading_a: str
    section_heading_b: str
    topic_similarity: float


def detect_conflicts(chunks: list[dict]) -> list[TemporalConflict]:
    """chunks: as returned by retrieval.vector_store.query()."""
    dated = [c for c in chunks if c.get("date_last_modified")]
    if len(dated) < 2:
        return []

    embeddings = np.array(embed_passages([c["text"] for c in dated]))

    conflicts: list[TemporalConflict] = []
    for i in range(len(dated)):
        for j in range(i + 1, len(dated)):
            a, b = dated[i], dated[j]

            if a["source_url"] == b["source_url"]:
                continue
            if a["date_last_modified"] == b["date_last_modified"]:
                continue
            if _leaf_heading(a["section_heading"]) != _leaf_heading(b["section_heading"]):
                continue
            if a["text"].strip() == b["text"].strip():
                continue  # identical boilerplate duplicated across pages, not a disagreement

            conflicts.append(
                TemporalConflict(
                    chunk_id_a=a["chunk_id"],
                    chunk_id_b=b["chunk_id"],
                    date_a=a["date_last_modified"],
                    date_b=b["date_last_modified"],
                    source_url_a=a["source_url"],
                    source_url_b=b["source_url"],
                    section_heading_a=a["section_heading"],
                    section_heading_b=b["section_heading"],
                    topic_similarity=float(embeddings[i] @ embeddings[j]),
                )
            )
    return conflicts
