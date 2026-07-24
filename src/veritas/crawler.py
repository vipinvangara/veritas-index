"""Wires the three lessons together: robots-checked fetch -> extract ->
store-with-dedup. This is deliberately thin — each piece it calls already
owns its own concern, so this module's only job is the order of
operations.
"""

import httpx

from .embedder import Embedder
from .extractor import extract
from .fetcher import Fetcher
from .ingest import ingest
from .storage import Storage, UpsertOutcome, UpsertResult


def crawl_one(
    fetcher: Fetcher, storage: Storage, embedder: Embedder, url: str
) -> UpsertOutcome | None:
    html = fetcher.fetch(url)
    if html is None:
        return None

    page = extract(html, url)
    if page is None:
        return None

    domain = httpx.URL(url).host
    return ingest(storage, embedder, url, domain, page)


def describe(outcome: UpsertOutcome | None) -> str:
    if outcome is None:
        return "SKIPPED (blocked, fetch failed, or no extractable content)"
    return {
        UpsertResult.NEW: "NEW — stored for the first time",
        UpsertResult.UNCHANGED: "UNCHANGED — content hash matched, no rewrite needed",
        UpsertResult.UPDATED: "UPDATED — content changed since last crawl",
    }[outcome.result]
