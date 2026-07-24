"""Not a real test yet (that comes once we have pytest wired up) — just a
quick, honest way to see the robots checker work against real sites
before we build anything on top of it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas.robots import RobotsChecker  # noqa: E402

checker = RobotsChecker()

checks = [
    "https://www.reuters.com/world/",
    "https://www.reuters.com/plus/something",
    "https://www.politifact.com/factchecks/",
]

for url in checks:
    allowed = checker.can_fetch(url)
    print(f"{'ALLOWED' if allowed else 'BLOCKED'}  {url}")
