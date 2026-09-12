"""FastAPI application entrypoint.

Phase 1 only wires up the app skeleton — retrieval and generation endpoints
land in Phase 2/3.
"""

from fastapi import FastAPI

app = FastAPI(title="IRCC Study Permit & Immigration Guidance Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
