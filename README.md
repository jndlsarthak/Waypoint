# IRCC Study Permit & Immigration Guidance Assistant

A RAG tool that answers questions about Canadian study permits and related
immigration guidance by retrieving from official government sources and
citing the exact section relied on. See [CLAUDE.md](CLAUDE.md) for the full
project spec, architecture, and guardrails.

**This is a portfolio/educational project — an informational research tool,
not immigration or legal advice.** It does not replace a licensed RCIC or
immigration lawyer.

## Status: Phase 4 (Temporal Handling) complete

What works end-to-end right now: ask a question via `/query` (or
`generation/generator.py` directly) and it's classified into one of three
categories *before* retrieval or generation (CLAUDE.md §3.4), checked for
cross-source temporal conflicts, then answered with inline `[n]` citations,
a dated source list, and a structured `temporal_conflicts` field.

- **Temporal-conflict detection** (`temporal/conflict_detector.py`): after
  retrieval, checks every pair of retrieved chunks from *different* pages
  whose `date_last_modified` differ and whose **leaf section heading**
  matches (e.g. two pages both have a "How we define work" section) — if
  their text isn't byte-identical, it's flagged as a potential conflict with
  both dates, both URLs, and both headings. This is deliberately gated on the
  heading match, not embedding similarity: bge-small scores unrelated
  sections (e.g. on-campus vs off-campus hour limits) above a naive 0.80
  cosine threshold just from shared domain vocabulary, which produced a flood
  of false positives when tested — confirming, yet again, that this
  embedding model doesn't discriminate finely in this corpus (see the Phase 2
  note below). The heading match is also deliberately *exact-text* gated, not
  a fuzzy similarity ratio: `SequenceMatcher` scores "20 hours" vs "24 hours"
  as ~99% similar, which would silently swallow exactly the conflicts this
  module exists to catch. Verified against a real identical-boilerplate pair
  (correctly NOT flagged — same text, different page, different date, not a
  disagreement) and a synthetic genuine conflict (correctly flagged). Flagged
  conflicts are both injected into the generation prompt (explicit
  instruction to address them) and returned as structured data in the API
  response, independent of whether the model mentions them in prose.
- **Guardrail classifier** (`guardrail/classifier.py`): a cheap Groq model
  (`openai/gpt-oss-20b`) classifies each question as `factual`,
  `individualized_advice`, or `out_of_scope` — run before any retrieval or
  the (more expensive) generation call. `out_of_scope` questions are declined
  immediately with zero retrieval/generation cost. `individualized_advice`
  questions still retrieve general guidance, but generation is instructed to
  never state or imply a personal eligibility determination and to
  explicitly redirect to a licensed RCIC or immigration lawyer instead.
  Classifier failures (network error, bad JSON) fail open to `factual` rather
  than silently blocking every question. Scored 7/7 on a hand-crafted set
  spanning all three categories.
- **Embeddings**: `BAAI/bge-small-en-v1.5` via `sentence-transformers` — local,
  free, no API key.
- **Vector store**: Chroma, persisted to `data/chroma/` (gitignored, rebuild
  with `python -m retrieval.vector_store`). Two hub/overview pages
  (`study-canada-overview`, `work-while-studying-overview`) are excluded from
  the index — see "Known limitations" below.
- **Retrieval**: naive top-k cosine similarity, no reranking yet (per
  CLAUDE.md §3.3/§6, reranking is a Phase 6 iteration on top of this baseline).
- **Generation**: Groq (`openai/gpt-oss-120b`) with a system prompt enforcing
  inline `[n]` citations, a "Sources" footer with per-source last-modified
  dates, explicit conflict-flagging when sources disagree, and (for
  `individualized_advice` questions) a hard rule against personal
  determinations.
- **FastAPI**: `POST /query {"question": "...", "top_k": 5}` →
  `{"answer", "sources", "category", "temporal_conflicts"}`.

Not built yet: reranking and the eval harness (Phases 5–6).

### Known quirk: CLI exit code on macOS

Running `python -m generation.generator "..."` (or any one-shot script that
calls the embedder) correctly computes and prints the answer, but the
process can then exit with code 134 (SIGABRT) due to a native threading
teardown crash (`recursive_mutex lock failed`) somewhere in the
torch/tokenizers/Chroma dependency stack on this macOS setup — confirmed it
happens *after* the correct output is printed, not during computation.
Verified the actual `uvicorn` server (a long-running process that never hits
this exit path between requests) stays stable across repeated `/query`
calls, so this doesn't affect real usage — just don't rely on a one-shot
script's exit code to mean "it failed."

### Known limitations (naive retrieval)

Diagnosed while testing: on some direct factual questions (e.g. "What are the
eligibility requirements for a study permit?"), the exact matching chunk can
rank far down (~80th of 224) because bge-small-en-v1.5 clusters this corpus's
jargon-heavy, topically-narrow text together — chunks about fees, application
steps, and eligibility all score similarly against a generic query. Swapping
to `bge-base-en-v1.5` did not meaningfully fix this, confirming it's the
embedding-similarity weakness CLAUDE.md §3.3 names directly ("naive top-k
similarity search is the most common source of bad RAG answers") and plans to
address with reranking in Phase 6, not a bug in this implementation.

Reassuringly, when retrieval misses the right chunk, generation does not
hallucinate a plausible-sounding number to fill the gap — tested with a
language-requirement question where the retrieved chunks didn't include the
actual CLB score, and the model correctly said the sources didn't specify it
rather than guessing. That's the hallucination-avoidance behavior Phase 5's
eval harness will want to measure.

### Phase 1 (Data Pipeline) details

- **Ingestion** (`ingestion/`) fetches 10 official canada.ca pages covering
  study permit eligibility, PGWP eligibility, and work-while-studying rules.
  Respects `robots.txt`, rate-limits requests (2s between fetches), and
  stores raw HTML + a normalized markdown version + page metadata
  (`page_title`, `date_scraped`, `date_last_modified` from the page's own
  `dcterms.modified` tag, `topic_tags`) for every page.
- **Chunking** (`chunking/`) splits each page's markdown by heading (H2+,
  including PGWP-style `<details>/<summary>` accordions promoted to
  headings) into semantic chunks, each carrying full citation metadata.
  Oversized sections with no internal subheadings (e.g. a long eligibility
  lookup table) are further split into embeddable-sized pieces rather than
  shipped as one giant chunk.

Not built yet: reranking and the eval harness (Phases 5–6).

## Project structure

```
IRCC_Rag/
├── ingestion/          # fetch canada.ca pages -> raw HTML + normalized markdown + metadata
│   ├── pages.py        # registry of the 10 source pages (url, slug, topic_tags)
│   └── scraper.py       # fetcher: robots.txt check, rate limiting, HTML->markdown
├── chunking/           # split normalized markdown into cited, tagged chunks
│   └── chunker.py
├── retrieval/          # embeddings + Chroma vector store + naive top-k retrieval
│   ├── embedder.py      # bge-small-en-v1.5 wrapper (query vs. passage encoding)
│   └── vector_store.py  # build_index() / query() against Chroma
├── guardrail/          # scope classifier, run before retrieval/generation
│   └── classifier.py    # classify_query() -> factual / individualized_advice / out_of_scope
├── temporal/            # cross-source temporal-conflict detection
│   └── conflict_detector.py  # detect_conflicts() -> flag same-heading chunks with differing dates
├── generation/         # LLM answer generation with citations
│   └── generator.py     # classify -> retrieval -> conflict check -> Groq call -> {answer, sources, category, temporal_conflicts}
├── eval/               # (Phase 5+) golden Q&A set, scoring harness
├── frontend/           # (Phase 7) chat UI
├── data/
│   ├── raw_html/       # one .html per page
│   ├── normalized_md/  # one .md per page
│   ├── manifest.json   # page-level metadata for all ingested pages
│   ├── chunks/
│   │   ├── <slug>.json       # chunks for one page
│   │   └── all_chunks.jsonl  # all chunks, one JSON object per line
│   └── chroma/          # Chroma's persisted index (gitignored, rebuildable)
├── main.py             # FastAPI app: /health, /query
├── requirements.txt
├── .env.example        # copy to .env and fill in GROQ_API_KEY
└── CLAUDE.md           # full project spec
```

## Source pages (Phase 1 batch)

All under `canada.ca/en/immigration-refugees-citizenship/services/study-canada/...`,
confirmed live and checked against `canada.ca/robots.txt` (none disallowed):

| Slug | Topic tags |
|---|---|
| study-permit-eligibility | study-permit, eligibility |
| study-permit-overview | study-permit, overview |
| study-permit-apply | study-permit, how-to-apply |
| pgwp-eligibility | pgwp, eligibility |
| pgwp-about | pgwp, overview |
| pgwp-field-of-study | pgwp, field-of-study |
| work-off-campus | off-campus-work |
| work-on-campus | on-campus-work |
| study-canada-overview | study-canada, overview |
| work-while-studying-overview | working-while-studying, overview |

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Fetch pages -> data/raw_html/, data/normalized_md/, data/manifest.json
python -m ingestion.scraper

# Chunk pages -> data/chunks/<slug>.json, data/chunks/all_chunks.jsonl
python -m chunking.chunker

# Build the vector index -> data/chroma/ (224 of 253 chunks; see "Known limitations")
python -m retrieval.vector_store

# Add your Groq API key (free tier, groq.com) — never commit this file
cp .env.example .env && edit .env

# Ask a question directly
python -m generation.generator "How many hours can I work off campus while studying?"

# Or run the API and POST to /query
uvicorn main:app --reload
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" \
  -d '{"question": "How many hours can I work off campus while studying?"}'
```

Current output: 10 pages ingested, 253 chunks written to `data/chunks/`, 224
indexed for retrieval.

## Chunk shape

Each entry in `data/chunks/all_chunks.jsonl` looks like:

```json
{
  "chunk_id": "pgwp-eligibility__s5",
  "text": "You can complete up to 100% of your studies online from outside Canada **between March 2020 and August 31, 2022**...",
  "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html",
  "page_title": "Who can apply",
  "section_heading": "General eligibility — Distance learning from outside of Canada",
  "date_scraped": "2026-09-12",
  "date_last_modified": "2026-06-24",
  "topic_tags": ["pgwp", "eligibility"]
}
```

`date_last_modified` comes from the page's own `dcterms.modified` meta tag,
which canada.ca keeps accurate — this is the field Phase 4's temporal-conflict
detection will key off of.

## Other known limitations (deferred to later phases)

- The oversized-table split (`chunking/chunker.py`, `MAX_CHUNK_CHARS`) is a
  generic safety net (row-batch tables, paragraph-split prose), not tuned
  against retrieval quality — that tuning belongs in Phase 6 (iterate on eval
  failures).
- Only English pages are ingested.
- No scope/guardrail classifier yet (Phase 3) — `/query` will attempt to
  answer individualized-advice or out-of-scope questions rather than
  deflecting them.
- See the naive-retrieval limitation documented above under Phase 2.
