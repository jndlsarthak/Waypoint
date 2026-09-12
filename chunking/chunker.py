"""Splits normalized markdown pages into semantic chunks by H2/H3 heading.

Each chunk carries the metadata needed for citation and later temporal-conflict
handling: source_url, page_title, section_heading, date_scraped,
date_last_modified, and topic_tags.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
CHUNKS_DIR = DATA_DIR / "chunks"
ALL_CHUNKS_PATH = CHUNKS_DIR / "all_chunks.jsonl"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")

# Safety net for sections with no internal subheadings to split on (e.g. a
# single long lookup table) — keeps every chunk small enough to embed.
MAX_CHUNK_CHARS = 4000
TABLE_ROWS_PER_CHUNK = 12


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_url: str
    page_title: str
    section_heading: str
    date_scraped: str
    date_last_modified: str | None
    topic_tags: list[str]


def _split_by_heading(markdown: str) -> list[tuple[str, str]]:
    """Return (section_heading, section_body) pairs for each H2+ section.

    Text preceding the first heading (if any) is kept under an "Overview"
    heading rather than dropped. Headings are qualified with their full
    ancestor chain (e.g. "Post-graduation work permit — Distance learning —
    Distance learning from outside of Canada") so the citation stays specific
    even for deeply nested subsections, e.g. accordion items promoted to
    headings during ingestion.
    """
    sections: list[tuple[str, list[str]]] = []
    heading_stack: list[tuple[int, str]] = []  # (level, text), outermost first
    current_heading = "Overview"
    buffer: list[str] = []

    def flush() -> None:
        sections.append((current_heading, list(buffer)))

    for line in markdown.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            buffer.append(line)
            continue

        level_str, heading_text = match.groups()
        level = len(level_str)
        # Strip markdown link/emphasis syntax (from source <a>/<strong>/<em>
        # tags inside headings, common on hub pages with card-style links)
        # so the heading stays a clean citation label.
        heading_text = MARKDOWN_LINK_RE.sub(r"\1", heading_text.strip()).strip("*_").strip()
        if level == 1:
            continue  # H1 is the page title, not a section boundary

        flush()
        buffer = []
        heading_stack = [entry for entry in heading_stack if entry[0] < level]
        heading_stack.append((level, heading_text))
        current_heading = " — ".join(text for _, text in heading_stack)

    flush()
    return [(heading, "\n".join(body).strip()) for heading, body in sections]


def _split_table_body(body: str) -> list[str] | None:
    """If body contains a markdown table, split its rows into batches (each
    keeping the header + separator row), returning [prefix?, *batches, suffix?].
    Returns None if body has no markdown table to split.
    """
    lines = body.splitlines()
    table_line_idxs = [i for i, line in enumerate(lines) if line.strip().startswith("|")]
    if len(table_line_idxs) < 3:  # need at least header + separator + one row
        return None

    start, end = table_line_idxs[0], table_line_idxs[-1]
    prefix = "\n".join(lines[:start]).strip()
    suffix = "\n".join(lines[end + 1 :]).strip()
    header, separator, *rows = lines[start : end + 1]

    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    for i in range(0, len(rows), TABLE_ROWS_PER_CHUNK):
        batch_rows = rows[i : i + TABLE_ROWS_PER_CHUNK]
        parts.append("\n".join([header, separator, *batch_rows]))
    if suffix:
        parts.append(suffix)
    return parts


def _split_prose(body: str, max_chars: int) -> list[str]:
    """Greedily group paragraphs (blank-line separated) into pieces under max_chars."""
    paragraphs = body.split("\n\n")
    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        para_len = len(para) + 2
        if current and current_len + para_len > max_chars:
            parts.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += para_len
    if current:
        parts.append("\n\n".join(current))
    return parts


def _split_oversized(heading: str, body: str) -> list[tuple[str, str]]:
    """Split a section that's too large to embed as one chunk into smaller
    pieces, preferring table-row batches over mid-paragraph splits."""
    if len(body) <= MAX_CHUNK_CHARS:
        return [(heading, body)]

    raw_parts = _split_table_body(body) or [body]
    parts: list[str] = []
    for part in raw_parts:
        if len(part) > MAX_CHUNK_CHARS:
            parts.extend(_split_prose(part, MAX_CHUNK_CHARS))
        else:
            parts.append(part)

    if len(parts) == 1:
        return [(heading, parts[0])]
    return [(f"{heading} (part {i + 1} of {len(parts)})", part) for i, part in enumerate(parts)]


def chunk_page(record: dict) -> list[Chunk]:
    repo_root = DATA_DIR.parent
    markdown = (repo_root / record["normalized_md_path"]).read_text(encoding="utf-8")

    sections: list[tuple[str, str]] = []
    for heading, body in _split_by_heading(markdown):
        if not body:
            continue
        sections.extend(_split_oversized(heading, body))

    chunks: list[Chunk] = []
    for i, (heading, body) in enumerate(sections):
        chunks.append(
            Chunk(
                chunk_id=f"{record['slug']}__s{i}",
                text=body,
                source_url=record["url"],
                page_title=record["page_title"],
                section_heading=heading,
                date_scraped=record["date_scraped"],
                date_last_modified=record.get("date_last_modified"),
                topic_tags=record["topic_tags"],
            )
        )
    return chunks


def run_chunking() -> list[Chunk]:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    all_chunks: list[Chunk] = []
    for record in manifest:
        page_chunks = chunk_page(record)
        all_chunks.extend(page_chunks)

        per_page_path = CHUNKS_DIR / f"{record['slug']}.json"
        per_page_path.write_text(
            json.dumps([asdict(c) for c in page_chunks], indent=2),
            encoding="utf-8",
        )

    with ALL_CHUNKS_PATH.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(asdict(c)) + "\n")

    print(f"Wrote {len(all_chunks)} chunks from {len(manifest)} pages to {CHUNKS_DIR}")
    return all_chunks


if __name__ == "__main__":
    run_chunking()
