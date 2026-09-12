"""Chroma-backed vector store: builds the index from data/chunks/ and serves
naive top-k similarity retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from chromadb.config import Settings

from retrieval.embedder import embed_passages, embed_query

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks" / "all_chunks.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "ircc_guidance_chunks"

# These hub/overview pages are almost entirely short card-teaser chunks that
# just point to content already ingested in full from dedicated pages (e.g.
# "Stay and work in Canada after you graduate" -> pgwp-about.html). Their
# brevity inflates embedding similarity and buries genuinely relevant chunks
# in naive top-k search, so they're excluded from the index while remaining
# in data/chunks/ on disk as part of the Phase 1 ingestion output.
EXCLUDED_FROM_INDEX_SLUGS = {"study-canada-overview", "work-while-studying-overview"}

_client = None


def _get_client():
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False)
        )
    return _client


def _load_chunks() -> list[dict]:
    chunks = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [c for c in chunks if c["chunk_id"].split("__")[0] not in EXCLUDED_FROM_INDEX_SLUGS]


def _to_chroma_metadata(chunk: dict) -> dict:
    # Chroma metadata values must be str/int/float/bool — no None, no lists.
    return {
        "source_url": chunk["source_url"],
        "page_title": chunk["page_title"],
        "section_heading": chunk["section_heading"],
        "date_scraped": chunk["date_scraped"],
        "date_last_modified": chunk["date_last_modified"] or "",
        "topic_tags": ",".join(chunk["topic_tags"]),
    }


def _from_chroma_metadata(metadata: dict) -> dict:
    return {
        "source_url": metadata["source_url"],
        "page_title": metadata["page_title"],
        "section_heading": metadata["section_heading"],
        "date_scraped": metadata["date_scraped"],
        "date_last_modified": metadata["date_last_modified"] or None,
        "topic_tags": metadata["topic_tags"].split(",") if metadata["topic_tags"] else [],
    }


def build_index() -> int:
    """(Re)builds the collection from data/chunks/all_chunks.jsonl."""
    chunks = _load_chunks()

    client = _get_client()
    client.delete_collection(COLLECTION_NAME) if COLLECTION_NAME in {c.name for c in client.list_collections()} else None
    collection = client.create_collection(COLLECTION_NAME)

    ids = [c["chunk_id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    embeddings = embed_passages(texts)
    metadatas = [_to_chroma_metadata(c) for c in chunks]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)


def query(question: str, top_k: int = 5) -> list[dict]:
    collection = _get_client().get_collection(COLLECTION_NAME)
    query_embedding = embed_query(question)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    hits = []
    for i in range(len(results["ids"][0])):
        chunk = _from_chroma_metadata(results["metadatas"][0][i])
        chunk["chunk_id"] = results["ids"][0][i]
        chunk["text"] = results["documents"][0][i]
        chunk["distance"] = results["distances"][0][i]
        hits.append(chunk)
    return hits


if __name__ == "__main__":
    n = build_index()
    print(f"Indexed {n} chunks into Chroma at {CHROMA_DIR}")
