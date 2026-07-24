import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas import arxiv  # noqa: E402
from veritas.embedder import Embedder  # noqa: E402
from veritas.ingest import ingest  # noqa: E402
from veritas.storage import Storage  # noqa: E402

db_path = Path(__file__).resolve().parent.parent / "data" / "veritas.db"
storage = Storage(db_path)
embedder = Embedder()

print("--- searching arXiv for 'misinformation detection' ---")
results = arxiv.search("misinformation detection", max_results=3)

for result in results:
    outcome = ingest(storage, embedder, result.url, "arxiv.org", result.page)
    print(f"{outcome.result.value.upper()}  {result.page.title}")

# The real test: does a search across the WHOLE index (web pages from
# lessons 1-4 AND arXiv papers from this lesson) correctly surface a
# paper for a paper-shaped question, mixed in with everything else?
query = "How well can automated systems tell AI-generated misinformation apart from human-written misinformation?"
query_vector = embedder.embed(query)

print(f"\n--- searching the WHOLE index: {query!r} ---")
for r in storage.search(query_vector, top_k=5):
    print(f"{r.score:.4f}  {r.title}")

storage.close()
