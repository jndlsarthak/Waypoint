# Waypoint — frontend

Next.js (App Router, TypeScript, Tailwind v4) chat UI for the IRCC study
permit / immigration guidance assistant. Talks to the FastAPI backend in the
repo root over `POST /query`.

Design direction: warm/editorial rather than a generic "AI chatbot" look —
Fraunces for display headlines, Inter for body/UI, a cream background with a
single restrained forest-green accent, hairline borders instead of heavy
shadows. Citations render as designed source cards (not raw markdown links),
and the guardrail categories (`factual` / `individualized_advice` /
`out_of_scope`) and temporal-conflict warnings each get their own visual
treatment instead of being buried in plain text.

## Run it

```bash
# from the repo root, in one terminal: the backend
source .venv/bin/activate  # or .venv/bin/uvicorn directly
uvicorn main:app --reload --port 8000

# in another terminal: this frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. `NEXT_PUBLIC_API_BASE_URL` (see `.env.local`,
copy from `.env.local.example`) points the frontend at the backend —
defaults to `http://127.0.0.1:8000`.

The backend's CORS config (`main.py`) only allows `localhost:3000` /
`127.0.0.1:3000` by default — a deployed frontend will need its origin added
there too.

## Structure

```
src/
├── app/
│   ├── layout.tsx     # fonts (Fraunces + Inter), metadata
│   ├── page.tsx        # composes Header/Hero/StatsStrip/ChatPanel/Footer
│   └── globals.css     # design tokens (@theme), markdown prose styling
├── components/
│   ├── Header.tsx, DisclaimerBar.tsx, Hero.tsx, StatsStrip.tsx, Footer.tsx
│   └── chat/
│       ├── ChatPanel.tsx       # message state, input, suggested questions
│       ├── MessageBubble.tsx   # renders one user/assistant/error message
│       ├── CategoryBadge.tsx   # factual / individualized_advice / out_of_scope
│       ├── SourceCard.tsx      # one cited source (title, heading, date, link)
│       └── ConflictBanner.tsx  # temporal_conflicts warning
└── lib/
    ├── api.ts    # askQuestion() + response types matching the backend
    └── text.ts   # strip the model's own inline "Sources" section (we render
                   # our own from structured data) + normalize citation
                   # brackets (the model occasionally emits full-width 【1】
                   # instead of ASCII [1])
```

## Notes

- The eval numbers in `StatsStrip.tsx` are hardcoded from `../eval/results.json`
  at time of writing — update them by hand if you re-run the eval and the
  numbers change (no live fetch, this is a static marketing-style strip).
- No accounts, no stored chat history, no server-side session — matches
  CLAUDE.md §5 ("no collection of personal/case-specific user data").
