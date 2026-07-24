"""arXiv connector — a research-paper source that talks to an official
API instead of crawling. No robots.txt here: arXiv's API has its own
documented usage terms instead (https://info.arxiv.org/help/api/tou.html),
which ask for no more than one request every 3 seconds. Same spirit as
robots.txt — a published contract for how to use the service respectfully
— just a different mechanism than the crawler's.

Deliberately reuses ExtractedPage (the same shape the HTML crawler
produces) rather than inventing a separate "paper" type. `text` holds
the abstract, not the full paper — most papers are paywalled beyond
that, and the abstract is usually what a fact-check actually needs. If
this connector had to invent its own data shape, that would be a sign
storage.py's `upsert()` was accidentally coupled to "came from HTML,"
not actually source-agnostic like we're claiming.
"""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from .extractor import ExtractedPage

API_URL = "https://export.arxiv.org/api/query"
MIN_DELAY_SECONDS = 3.0  # arXiv's documented minimum between requests

_ATOM_NS = "{http://www.w3.org/2005/Atom}"

_last_request_at: float | None = None


@dataclass
class ArxivResult:
    url: str
    page: ExtractedPage


def _wait_for_rate_limit() -> None:
    global _last_request_at
    if _last_request_at is not None:
        remaining = MIN_DELAY_SECONDS - (time.monotonic() - _last_request_at)
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at = time.monotonic()


def search(query: str, max_results: int = 5) -> list[ArxivResult]:
    # `all:"..."` (quoted) searches for the phrase rather than arXiv's
    # default OR-of-terms behavior, which is what tripped us up in the
    # exploratory curl call.
    search_query = f'all:"{query}"'
    url = f"{API_URL}?search_query={quote(search_query)}&start=0&max_results={max_results}"

    _wait_for_rate_limit()
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    results = []
    for entry in root.findall(f"{_ATOM_NS}entry"):
        paper_url = entry.findtext(f"{_ATOM_NS}id")
        title = entry.findtext(f"{_ATOM_NS}title")
        summary = entry.findtext(f"{_ATOM_NS}summary")
        published = entry.findtext(f"{_ATOM_NS}published")
        authors = [
            name.text
            for author in entry.findall(f"{_ATOM_NS}author")
            if (name := author.find(f"{_ATOM_NS}name")) is not None
        ]

        if not paper_url or not title or not summary:
            continue

        page = ExtractedPage(
            title=title.strip(),
            text=summary.strip(),
            author=", ".join(authors) if authors else None,
            date=published,
        )
        results.append(ArxivResult(url=paper_url, page=page))

    return results
