# IRCC Study Permit & Immigration Guidance Assistant

A RAG tool that answers questions about Canadian study permits and related
immigration guidance by retrieving from official government sources and
citing the exact section relied on. See [CLAUDE.md](CLAUDE.md) for the full
project spec, architecture, and guardrails.

**This is a portfolio/educational project — an informational research tool,
not immigration or legal advice.** It does not replace a licensed RCIC or
immigration lawyer.

## Status: Phase 1 (Data Pipeline) complete

What works end-to-end right now: point the ingestion module at a list of
canada.ca URLs and get back clean, dated, tagged chunks ready for embedding.

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
- **FastAPI skeleton** (`main.py`) — just a `/health` endpoint for now.
  Retrieval/generation endpoints land in later phases.

Not built yet: embeddings, vector store, retrieval, reranking, the
guardrail/scope classifier, generation, and the eval harness (Phases 2–5).

## Project structure

```
IRCC_Rag/
├── ingestion/          # fetch canada.ca pages -> raw HTML + normalized markdown + metadata
│   ├── pages.py        # registry of the 10 source pages (url, slug, topic_tags)
│   └── scraper.py       # fetcher: robots.txt check, rate limiting, HTML->markdown
├── chunking/           # split normalized markdown into cited, tagged chunks
│   └── chunker.py
├── retrieval/          # (Phase 3+) embeddings, vector store, reranking
├── generation/         # (Phase 3+) LLM answer generation with citations
├── eval/               # (Phase 5+) golden Q&A set, scoring harness
├── frontend/           # (Phase 7) chat UI
├── data/
│   ├── raw_html/       # one .html per page
│   ├── normalized_md/  # one .md per page
│   ├── manifest.json   # page-level metadata for all ingested pages
│   └── chunks/
│       ├── <slug>.json       # chunks for one page
│       └── all_chunks.jsonl  # all chunks, one JSON object per line
├── main.py             # FastAPI app (health check only for now)
├── requirements.txt
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

# (optional) run the FastAPI skeleton
uvicorn main:app --reload
```

Current output: 10 pages ingested, 253 chunks written to `data/chunks/`.

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

## Known limitations (deferred to later phases)

- No embeddings/vector store yet — chunks are just JSON on disk.
- The oversized-table split (`chunking/chunker.py`, `MAX_CHUNK_CHARS`) is a
  generic safety net (row-batch tables, paragraph-split prose), not tuned
  against retrieval quality — that tuning belongs in Phase 6 (iterate on eval
  failures).
- Only English pages are ingested.
