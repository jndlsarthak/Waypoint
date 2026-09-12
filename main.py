"""FastAPI application entrypoint.

Phase 2: naive retrieval + generation with citations. The scope/guardrail
classifier (CLAUDE.md §3.4) is Phase 3 and is not wired in yet — /query will
answer any question the retriever finds chunks for, including ones that
should eventually be deflected to an RCIC/lawyer or declined as out of scope.
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
