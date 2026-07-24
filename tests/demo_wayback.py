import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas import wayback  # noqa: E402
from veritas.embedder import Embedder  # noqa: E402
from veritas.ingest import ingest  # noqa: E402
from veritas.storage import Storage  # noqa: E402

url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
db_path = Path(__file__).resolve().parent.parent / "data" / "veritas.db"
storage = Storage(db_path)
embedder = Embedder()

# Two snapshots of the SAME original URL, ~2 years apart — should land
# as two distinct rows, not one overwriting the other.
for label, timestamp in [("~2 years ago", "20240701"), ("recent", None)]:
    result = wayback.fetch_snapshot(url, timestamp=timestamp)
    if result is None:
        print(f"{label}: no snapshot found")
        continue
    outcome = ingest(storage, embedder, result.snapshot_url, "web.archive.org", result.page)
    print(f"{label}: {outcome.result.value.upper()}  snapshot={result.timestamp}  "
          f"chars={len(result.page.text)}")
    print(f"  {result.snapshot_url}")

count = storage._conn.execute(
    "SELECT COUNT(*) FROM pages WHERE domain = 'web.archive.org'"
).fetchone()[0]
print(f"\nDistinct web.archive.org rows now stored: {count}")

storage.close()
