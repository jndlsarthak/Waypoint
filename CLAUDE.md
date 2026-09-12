# CLAUDE.md — Canadian Study Permit & Immigration Guidance Assistant

This file is the project brief and working spec. Read this before making architectural changes or adding features — it defines scope, guardrails, and what "done" looks like for each phase.

## 1. Project Summary

A retrieval-augmented generation (RAG) tool that answers questions about Canadian study permits and related immigration guidance (IRCC rules, PGWP eligibility, work-while-studying rules, etc.) by retrieving from official government sources and citing the exact section relied on.

**This is an informational research tool, not an immigration advice service.** It does not make eligibility determinations for individuals and does not replace a licensed RCIC (Regulated Canadian Immigration Consultant) or immigration lawyer. That distinction is a hard architectural constraint, not a disclaimer bolted on at the end — see Section 5.

**Why this project:** IRCC guidance is dense, spread across many pages, updated frequently, and often internally inconsistent across update dates. A naive RAG system will confidently answer using outdated guidance — handling that well is the technically interesting and portfolio-differentiating part of this build.

## 2. Goals (what makes this portfolio-strong, not just functional)

- [ ] Retrieval that's accurate enough to trust — every answer cites the specific source page/section.
- [ ] Temporal awareness — the system knows when guidance was last updated and flags superseded information instead of confidently mixing old and new rules.
- [ ] Scope-limiting — the system recognizes questions that require individualized legal judgment and declines to answer them directly, redirecting to an RCIC/lawyer instead.
- [ ] A quantified eval harness — a golden Q&A set with citation-accuracy and hallucination-rate scoring, so you can report a real number in interviews ("94% citation accuracy on a 50-question eval set").
- [ ] A clean, deployed demo — not just a notebook.

## 3. Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Data Ingestion  │────▶│  Chunking +  │────▶│   Vector Store   │
│  (IRCC scrape /  │     │  Metadata    │     │  (Chroma/        │
│   Open Gov data) │     │  Tagging     │     │   pgvector)      │
└─────────────────┘     └──────────────┘     └────────┬─────────┘
                                                        │
┌──────────────────┐    ┌──────────────┐    ┌─────────▼─────────┐
│   Frontend        │◀───│  Guardrail/  │◀───│    Retriever +     │
│  (chat UI, shows   │    │  Scope Layer │    │  Reranker           │
│   citations +      │    │  (in-scope? │    │                     │
│   "as of" dates)   │    │  refuse?)    │    └─────────┬───────────┘
└──────────────────┘    └──────┬───────┘              │
                                │                       │
                                ▼                       ▼
                         ┌──────────────────────────────────┐
                         │        LLM Generation Layer        │
                         │  (answer + inline citations +      │
                         │   "last verified" date)            │
                         └──────────────────┬─────────────────┘
                                             │
                                             ▼
                                   ┌───────────────────┐
                                   │   Eval Harness      │
                                   │  (golden Q&A set,   │
                                   │   LLM-as-judge,     │
                                   │   citation checker)│
                                   └───────────────────┘
```

### 3.1 Data Ingestion
- Primary source: public IRCC guidance pages (study permits, PGWP, working while studying).
- Prefer **Open Government Portal** bulk/API data over scraping wherever it exists — lower legal friction, more stable structure.
- Where scraping is necessary: respect robots.txt, rate-limit requests, and store the scrape date with every document (critical for the temporal-awareness feature).
- Store raw HTML/text + a normalized markdown version for chunking.

### 3.2 Chunking + Metadata
- Chunk by semantic section (H2/H3 headers), not fixed token windows — IRCC pages are structured, use that structure.
- Metadata per chunk: `source_url`, `page_title`, `section_heading`, `date_scraped`, `date_last_modified` (if available on page), `topic_tags` (e.g. `study-permit`, `pgwp`, `off-campus-work`).
- This metadata is what powers the temporal-conflict handling later — don't skip it.

### 3.3 Vector Store & Retrieval
- Chroma or pgvector for the MVP (both free, both fine at this scale).
- Retrieve top-k chunks, then **rerank** (cross-encoder or LLM-based rerank) before generation — naive top-k similarity search is the most common source of bad RAG answers.
- If two retrieved chunks conflict (check via metadata dates or explicit contradiction detection), surface both with dates rather than silently picking one.

### 3.4 Guardrail / Scope Layer
This is the most important non-obvious component. Before generation, classify the query as one of:
1. **Factual/informational** ("What's the minimum funds requirement for a study permit?") → answer normally, with citations.
2. **Individualized eligibility/advice** ("Will I qualify given my specific situation X, Y, Z?") → do not answer definitively. Respond with the relevant general guidance + an explicit statement that this requires a licensed RCIC or immigration lawyer.
3. **Out of scope** (unrelated to study permits/immigration) → decline.

Implement this as a lightweight classifier (a small prompt-based classifier is fine for v1) sitting *before* the generation call, not as a disclaimer appended after.

### 3.5 Generation
- System prompt enforces: cite every claim to a retrieved chunk, state the "as of" date of the cited guidance, and never answer category-2 queries (see 3.4) definitively.
- Output format: answer text with inline citation markers → linked source list with URLs and last-verified dates at the bottom.

### 3.6 Eval Harness
- Build a golden set of ~40–60 Q&A pairs across categories 1 and 2 above (mix of easy factual questions and edge cases involving updated/superseded rules).
- Metrics to track:
  - **Citation accuracy**: does the cited chunk actually support the claim? (LLM-as-judge or manual scoring)
  - **Hallucination rate**: % of answers containing claims not traceable to any retrieved chunk
  - **Scope-handling accuracy**: % of category-2 questions correctly deflected instead of answered definitively
  - **Temporal correctness**: when guidance has an old/new version, does the system surface the current one and flag the conflict?
- Run this eval any time you change chunking, retrieval, or prompts — track scores over time so you can show improvement, not just a final number.

## 4. Tech Stack (suggested, swap freely)

| Layer | Choice | Notes |
|---|---|---|
| Ingestion | Python + `requests`/`BeautifulSoup`, or Open Gov API | Store raw + normalized text |
| Embeddings | OpenAI/Anthropic embeddings or open-source (bge, e5) | Open-source keeps cost near zero |
| Vector store | Chroma (local) or pgvector (if you want a "real" DB on the resume) | pgvector reads better to data-heavy roles |
| Reranker | Cohere rerank API or a cross-encoder from `sentence-transformers` | |
| LLM | Claude or GPT via API | Use a cheap model for classification, stronger model for final generation — nice tie-in to your cost-optimization project if you build both |
| Backend | FastAPI | |
| Frontend | Simple React/Next.js chat UI, or Streamlit for speed | |
| Eval | Custom script + LLM-as-judge, logged to CSV/simple dashboard | |
| Deployment | Render/Railway (backend), Vercel (frontend) | |

## 5. Legal/Scope Guardrails (do not skip)

- Persistent, visible disclaimer: "This tool provides general information based on public IRCC guidance. It is not immigration or legal advice and does not replace a licensed RCIC or immigration lawyer."
- No individualized eligibility determinations (enforced architecturally per 3.4, not just stated in UI copy).
- No collection of personal/case-specific user data (no accounts, no storing of user-submitted personal details).
- Cite sources accurately; do not reproduce large verbatim blocks of government text — summarize with citation links (also just good RAG practice).
- Non-commercial, portfolio/educational framing throughout (README, UI footer, etc.).

## 6. Milestones

- [ ] **Phase 1 — Data pipeline**: scrape/ingest a first batch of IRCC study permit pages, normalize, chunk, tag metadata.
- [ ] **Phase 2 — Basic RAG**: embeddings + vector store + naive retrieval + generation with citations. Get *something* answering questions end-to-end.
- [ ] **Phase 3 — Guardrail layer**: build the query classifier and scope-limiting logic (Section 3.4).
- [ ] **Phase 4 — Temporal handling**: add date metadata checks, contradiction surfacing when guidance has changed.
- [ ] **Phase 5 — Eval harness**: build the golden Q&A set, run baseline eval, record scores.
- [ ] **Phase 6 — Iterate**: improve chunking/reranking/prompts based on eval failures, re-run eval, track improvement.
- [ ] **Phase 7 — Deploy + polish**: ship a working demo link, write the README with your eval numbers front and center.

## 7. What "done" looks like for the portfolio

A deployed demo link, a README with a clear problem statement, an architecture diagram, and — most importantly — a results section with real numbers from Phase 5/6 (e.g., "improved citation accuracy from 71% to 93% after adding reranking and metadata-based conflict detection"). The eval-driven improvement story is what turns this from "a RAG project" into "a project that shows I can build and validate AI systems responsibly," which is the exact pitch you want across AI Developer, Analyst, and Governance roles.
