import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas.crawler import crawl_one, describe  # noqa: E402
from veritas.embedder import Embedder  # noqa: E402
from veritas.fetcher import Fetcher  # noqa: E402
from veritas.robots import RobotsChecker  # noqa: E402
from veritas.storage import Storage  # noqa: E402

url = "https://www.factcheck.org/2026/07/trumps-distorted-venezuela-elections-claim/"
db_path = Path(__file__).resolve().parent.parent / "data" / "veritas.db"

robots = RobotsChecker()
fetcher = Fetcher(robots)
storage = Storage(db_path)
embedder = Embedder()

print("--- first crawl ---")
outcome = crawl_one(fetcher, storage, embedder, url)
print(describe(outcome))

print("--- second crawl of the SAME url, right away ---")
outcome = crawl_one(fetcher, storage, embedder, url)
print(describe(outcome))

row = storage._conn.execute(
    "SELECT url, title, length(text), last_crawled_at FROM pages WHERE url = ?", (url,)
).fetchone()
print("--- stored row ---")
print(row)

fetcher.close()
storage.close()
