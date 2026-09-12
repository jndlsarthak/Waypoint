"""FastAPI application entrypoint.

/query runs the scope/guardrail classifier (CLAUDE.md §3.4) before retrieval
or generation, then answers with citations (§3.5). The response includes
which category ("factual" / "individualized_advice" / "out_of_scope") the
question was classified as.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from generation.generator import DEFAULT_TOP_K, answer_question

app = FastAPI(title="IRCC Study Permit & Immigration Guidance Assistant")

# Local frontend dev servers only — this is a portfolio demo with no user
# accounts or sensitive data, so a permissive local-only CORS list is fine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
