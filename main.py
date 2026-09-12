"""FastAPI application entrypoint.

/query runs the scope/guardrail classifier (CLAUDE.md §3.4) before retrieval
or generation, then answers with citations (§3.5). The response includes
which category ("factual" / "individualized_advice" / "out_of_scope") the
question was classified as.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from generation.generator import DEFAULT_TOP_K, answer_question
from retrieval.vector_store import ensure_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Builds the vector index on startup if it isn't already there — some
    # hosts (e.g. Render's free tier) reset the container's disk between
    # restarts, so it can't be assumed to persist from deploy time.
    ensure_index()
    yield


app = FastAPI(title="IRCC Study Permit & Immigration Guidance Assistant", lifespan=lifespan)

# Local dev servers plus any Vercel deployment of the frontend (production
# and preview URLs both match *.vercel.app) — no user accounts or sensitive
# data here, so this permissive-but-scoped list is fine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class QueryRequest(BaseModel):
    question: str
    top_k: int = DEFAULT_TOP_K


@app.post("/query")
def query(request: QueryRequest) -> dict:
    return answer_question(request.question, top_k=request.top_k)
