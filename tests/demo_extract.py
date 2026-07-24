import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas.extractor import extract  # noqa: E402
from veritas.fetcher import Fetcher  # noqa: E402
from veritas.robots import RobotsChecker  # noqa: E402

url = "https://www.factcheck.org/2026/07/trumps-distorted-venezuela-elections-claim/"

robots = RobotsChecker()
fetcher = Fetcher(robots)

html = fetcher.fetch(url)
if html is None:
    print("Fetch failed or blocked by robots.txt")
else:
    print(f"Raw HTML: {len(html):,} characters")
    page = extract(html, url)
    if page is None:
        print("Extraction found no article content")
    else:
        print(f"Extracted text: {len(page.text):,} characters")
        print(f"Title: {page.title}")
        print(f"Author: {page.author}")
        print(f"Date: {page.date}")
        print("--- first 500 chars of extracted text ---")
        print(page.text[:500])

fetcher.close()
