"""The one shared step every connector funnels through, regardless of
how it got its content — HTML crawl, arXiv API, Wayback snapshot,
whatever comes next. This is the real "interface" this project needed:
not a common fetch() method (crawling a known URL and searching a query
are genuinely different operations), but a common output contract
(url + domain + ExtractedPage) and one canonical way to turn that into
a stored, searchable row.

Connectors' only obligation is producing an ExtractedPage. Everything
after that — hashing, embedding, dedup, storage — lives here exactly
once.
"""

from .embedder import Embedder
from .extractor import ExtractedPage
from .storage import Storage, UpsertOutcome


def ingest(
    storage: Storage, embedder: Embedder, url: str, domain: str, page: ExtractedPage
) -> UpsertOutcome:
    embedding = embedder.embed(f"{page.title}\n\n{page.text}")
    return storage.upsert(url, domain, page, embedding)
