import sys
from pathlib import Path

# Project root layout uses `ztare...` as the canonical import path;
# ensure the project root is on sys.path when tests are run directly or via pytest.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
