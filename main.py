"""FastAPI application entrypoint.

/query runs the scope/guardrail classifier (CLAUDE.md §3.4) before retrieval
or generation, then answers with citations (§3.5). The response includes
which category ("factual" / "individualized_advice" / "out_of_scope") the
question was classified as.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from generation.generator import DEFAULT_TOP_K, answer_question

app = FastAPI(title="IRCC Study Permit & Immigration Guidance Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class QueryRequest(BaseModel):
    question: str
    top_k: int = DEFAULT_TOP_K


@app.post("/query")
def query(request: QueryRequest) -> dict:
    return answer_question(request.question, top_k=request.top_k)
