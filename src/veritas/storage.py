"""Persistence for crawled pages, with change detection via content hash.

Why a hash instead of just comparing text directly: it's a fixed-size
fingerprint we can index and compare cheaply, and it's what lets a
re-crawl decide "skip this, nothing changed" in one indexed lookup
rather than pulling the full stored text out of the database just to
diff it.
"""

import hashlib
import sqlite3
from array import array
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from .extractor import ExtractedPage

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    url TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    title TEXT,
    author TEXT,
    published_date TEXT,
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding BLOB,
    first_crawled_at TEXT NOT NULL,
    last_crawled_at TEXT NOT NULL,
    last_changed_at TEXT NOT NULL
);
"""


def _encode_embedding(vector: list[float]) -> bytes:
    # array('f', ...) packs the floats as raw 4-byte-each binary — far
    # more compact than storing them as JSON text, and trivial to
    # reverse with the same array() call on the way out.
    return array("f", vector).tobytes()


def _decode_embedding(blob: bytes) -> list[float]:
    return array("f", blob).tolist()


@dataclass
class SearchResult:
    url: str
    title: str | None
    score: float


class UpsertResult(Enum):
    NEW = "new"
    UNCHANGED = "unchanged"
    UPDATED = "updated"


@dataclass
class UpsertOutcome:
    result: UpsertResult
    content_hash: str


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Storage:
    def __init__(self, db_path: Path) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        # CREATE TABLE IF NOT EXISTS only helps a brand-new database — an
        # existing pages table from before the `embedding` column existed
        # needs it added explicitly. A real project with many schema
        # changes over time would want a proper numbered-migration system;
        # at one column added once, this inline check is honest and enough.
        existing_columns = {row[1] for row in self._conn.execute("PRAGMA table_info(pages)")}
        if "embedding" not in existing_columns:
            self._conn.execute("ALTER TABLE pages ADD COLUMN embedding BLOB")

    def upsert(
        self, url: str, domain: str, page: ExtractedPage, embedding: list[float]
    ) -> UpsertOutcome:
        content_hash = _hash_text(page.text)
        embedding_blob = _encode_embedding(embedding)
        now = datetime.now(UTC).isoformat()

        existing = self._conn.execute(
            "SELECT content_hash, embedding FROM pages WHERE url = ?", (url,)
        ).fetchone()

        if existing is None:
            self._conn.execute(
                """
                INSERT INTO pages
                    (url, domain, title, author, published_date, text,
                     content_hash, embedding, first_crawled_at, last_crawled_at, last_changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (url, domain, page.title, page.author, page.date, page.text,
                 content_hash, embedding_blob, now, now, now),
            )
            self._conn.commit()
            return UpsertOutcome(UpsertResult.NEW, content_hash)

        if existing[0] == content_hash:
            # Content is unchanged, but a row from before the embedding
            # column existed (or before embedding failed for some other
            # reason) still needs one — "unchanged" and "fully populated"
            # aren't the same question.
            if existing[1] is None:
                self._conn.execute(
                    "UPDATE pages SET embedding = ?, last_crawled_at = ? WHERE url = ?",
                    (embedding_blob, now, url),
                )
            else:
                self._conn.execute(
                    "UPDATE pages SET last_crawled_at = ? WHERE url = ?", (now, url)
                )
            self._conn.commit()
            return UpsertOutcome(UpsertResult.UNCHANGED, content_hash)

        self._conn.execute(
            """
            UPDATE pages
            SET title = ?, author = ?, published_date = ?, text = ?,
                content_hash = ?, embedding = ?, last_crawled_at = ?, last_changed_at = ?
            WHERE url = ?
            """,
            (page.title, page.author, page.date, page.text,
             content_hash, embedding_blob, now, now, url),
        )
        self._conn.commit()
        return UpsertOutcome(UpsertResult.UPDATED, content_hash)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        # Brute force: pull every stored embedding, score it against the
        # query, sort. Fine at hundreds-to-low-thousands of rows; the
        # point where this needs to become an indexed vector search
        # (rather than a full scan) is a scale problem for later, not now.
        rows = self._conn.execute("SELECT url, title, embedding FROM pages").fetchall()

        scored = []
        for url, title, embedding_blob in rows:
            if embedding_blob is None:
                continue
            stored_vector = _decode_embedding(embedding_blob)
            # Both vectors are unit-length (see embedder.py), so a plain
            # dot product IS the cosine similarity here.
            score = sum(a * b for a, b in zip(query_embedding, stored_vector, strict=True))
            scored.append(SearchResult(url=url, title=title, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def close(self) -> None:
        self._conn.close()
