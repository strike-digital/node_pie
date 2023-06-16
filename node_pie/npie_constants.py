from pathlib import Path

POPULARITY_FILE = Path(__file__).parent / "nodes.json"
if not POPULARITY_FILE.exists():
    with open(POPULARITY_FILE, "w") as f:
        pass
POPULARITY_FILE_VERSION = (0, 0, 1)