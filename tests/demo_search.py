import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas.crawler import crawl_one, describe  # noqa: E402
from veritas.embedder import Embedder  # noqa: E402
from veritas.fetcher import Fetcher  # noqa: E402
from veritas.robots import RobotsChecker  # noqa: E402
from veritas.storage import Storage  # noqa: E402

urls = [
    "https://www.factcheck.org/2026/07/trumps-distorted-venezuela-elections-claim/",
    "https://www.altnews.in/no-one-fired-pellet-guns-in-delhi/",
]

db_path = Path(__file__).resolve().parent.parent / "data" / "veritas.db"
robots = RobotsChecker()
fetcher = Fetcher(robots)
storage = Storage(db_path)
embedder = Embedder()

for url in urls:
    outcome = crawl_one(fetcher, storage, embedder, url)
    print(f"{describe(outcome)}  <- {url}")

# Deliberately shares almost no literal words with either stored article
# ("election security" is the closest overlap) — this is testing whether
# the match is coming from MEANING, not keyword overlap.
query = "Was there evidence of a foreign attempt to interfere with a country's voting systems?"
query_vector = embedder.embed(query)

print(f"\n--- searching: {query!r} ---")
for result in storage.search(query_vector, top_k=2):
    print(f"{result.score:.4f}  {result.title}")

fetcher.close()
storage.close()
