"""Runs every source declared in sources.yaml through the pipeline built
over the last six lessons. This is the thing a scheduler (cron, Cloud
Scheduler + a Cloud Run Job — same pattern discussed for TruthGuard's
own infra) would actually invoke periodically.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import arxiv
from .crawler import crawl_one
from .embedder import Embedder
from .fetcher import Fetcher
from .ingest import ingest
from .robots import RobotsChecker
from .storage import Storage, UpsertResult


@dataclass
class SeedSummary:
    counts: dict[UpsertResult, int] = field(default_factory=dict)
    skipped: int = 0

    def record(self, result: UpsertResult | None) -> None:
        if result is None:
            self.skipped += 1
        else:
            self.counts[result] = self.counts.get(result, 0) + 1

    def report(self) -> str:
        lines = [f"{result.value}: {count}" for result, count in self.counts.items()]
        lines.append(f"skipped: {self.skipped}")
        return "\n".join(lines)


def run(config_path: Path, db_path: Path) -> SeedSummary:
    config = yaml.safe_load(config_path.read_text())
    summary = SeedSummary()

    storage = Storage(db_path)
    embedder = Embedder()
    fetcher = Fetcher(RobotsChecker())

    for source in config.get("crawl", []):
        for url in source["urls"]:
            outcome = crawl_one(fetcher, storage, embedder, url)
            summary.record(outcome.result if outcome else None)

    for source in config.get("arxiv", []):
        results = arxiv.search(source["query"], max_results=source.get("max_results", 5))
        for result in results:
            outcome = ingest(storage, embedder, result.url, "arxiv.org", result.page)
            summary.record(outcome.result)

    fetcher.close()
    storage.close()
    return summary
