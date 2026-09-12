"""Fetches IRCC study-permit / PGWP guidance pages from canada.ca.

Respects robots.txt and rate-limits requests. For each page, stores the raw
HTML, a normalized markdown version (boilerplate nav/pagination/TOC
stripped), and page-level metadata (title, date scraped, date last modified
per the page's own dcterms.modified tag, topic tags) needed for the
temporal-awareness feature in later phases.
"""

from __future__ import annotations

import json
import time
import urllib.robotparser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

from ingestion.pages import PAGES

USER_AGENT = "IRCC-RAG-Research-Bot/0.1 (educational portfolio project; non-commercial)"
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 15

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
NORMALIZED_MD_DIR = DATA_DIR / "normalized_md"
MANIFEST_PATH = DATA_DIR / "manifest.json"


_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


@dataclass
class PageRecord:
    slug: str
    url: str
    page_title: str
    date_scraped: str
    date_last_modified: str | None
    date_issued: str | None
    topic_tags: list[str]
    raw_html_path: str
    normalized_md_path: str


def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    rp = _robots_cache.get(origin)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{origin}/robots.txt")
        # Fetch via requests (uses certifi's CA bundle) rather than rp.read(),
        # which relies on urllib's default SSL context and can fail with
        # CERTIFICATE_VERIFY_FAILED on some local Python installs.
        response = requests.get(f"{origin}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
        rp.parse(response.text.splitlines())
        _robots_cache[origin] = rp
    return rp.can_fetch(USER_AGENT, url)


def _extract_main_content(soup: BeautifulSoup):
    # canada.ca column-layout classes (e.g. "col-md-8") get reused by unrelated
    # small widgets (the page-feedback box) on some templates, so matching on
    # them is unreliable. <main> itself is the stable boundary — strip the
    # known boilerplate (nav, pagination, page-details/feedback, TOC) from it
    # instead of trying to guess a narrower content container.
    content = soup.find("main") or soup

    for nav in content.find_all("nav"):
        nav.decompose()
    for pagination in content.find_all("div", class_="mwspagination"):
        pagination.decompose()
    for details_section in content.find_all("section", class_="pagedetails"):
        details_section.decompose()

    # The page's own <h1> duplicates the title we already capture separately
    # and prepend to the markdown ourselves.
    h1 = content.find("h1", attrs={"property": "name"})
    if h1 is not None:
        h1.decompose()

    # Drop the "On this page" table-of-contents block (heading + its link list) —
    # it duplicates the section headings and adds no content of its own.
    for heading in content.find_all(["h2", "h3"]):
        if heading.get_text(strip=True).lower() == "on this page":
            next_el = heading.find_next_sibling()
            heading.decompose()
            if next_el and next_el.name == "ul":
                next_el.decompose()

    # Promote accordion <summary> labels to real headings — IRCC pages use
    # <details><summary> for genuinely distinct sub-topics (e.g. "Distance
    # learning", "Curriculum licensing agreements"), each with its own rules
    # and dates. Without this they collapse into their parent section's text
    # instead of becoming their own citable chunk.
    for summary in content.find_all("summary"):
        summary.name = "h3"

    return content


def _page_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1", attrs={"property": "name"})
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.replace(" - Canada.ca", "").strip()
    return "Untitled"


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": name})
    return tag["content"].strip() if tag and tag.get("content") else None


def fetch_page(slug: str, url: str, topic_tags: list[str]) -> PageRecord:
    if not _robots_allows(url):
        raise PermissionError(f"robots.txt disallows fetching {url}")

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    raw_html = response.text

    soup = BeautifulSoup(raw_html, "html.parser")
    page_title = _page_title(soup)
    date_last_modified = _meta_content(soup, "dcterms.modified")
    date_issued = _meta_content(soup, "dcterms.issued")

    content = _extract_main_content(soup)
    normalized_md = markdownify(str(content), heading_style="ATX").strip()
    normalized_md = f"# {page_title}\n\n{normalized_md}"

    date_scraped = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    raw_html_path = RAW_HTML_DIR / f"{slug}.html"
    normalized_md_path = NORMALIZED_MD_DIR / f"{slug}.md"
    raw_html_path.write_text(raw_html, encoding="utf-8")
    normalized_md_path.write_text(normalized_md, encoding="utf-8")

    repo_root = DATA_DIR.parent
    return PageRecord(
        slug=slug,
        url=url,
        page_title=page_title,
        date_scraped=date_scraped,
        date_last_modified=date_last_modified,
        date_issued=date_issued,
        topic_tags=topic_tags,
        raw_html_path=str(raw_html_path.relative_to(repo_root)),
        normalized_md_path=str(normalized_md_path.relative_to(repo_root)),
    )


def run_ingestion(pages: list[dict] = PAGES) -> list[PageRecord]:
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_MD_DIR.mkdir(parents=True, exist_ok=True)

    records: list[PageRecord] = []
    for i, page in enumerate(pages):
        print(f"[{i + 1}/{len(pages)}] Fetching {page['url']}")
        record = fetch_page(page["slug"], page["url"], page["topic_tags"])
        records.append(record)
        if i < len(pages) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    MANIFEST_PATH.write_text(
        json.dumps([asdict(r) for r in records], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote manifest for {len(records)} pages to {MANIFEST_PATH}")
    return records


if __name__ == "__main__":
    run_ingestion()
