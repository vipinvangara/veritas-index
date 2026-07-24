"""CLI entrypoint: python scripts/run_seed.py [path/to/sources.yaml]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veritas.seed import run  # noqa: E402

root = Path(__file__).resolve().parent.parent
config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "sources.yaml"
db_path = root / "data" / "veritas.db"

summary = run(config_path, db_path)
print(summary.report())
