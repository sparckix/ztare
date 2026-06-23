from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.supervisor.supervisor_backlog import build_what_next


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the next actionable step for a supervisor run.")
    parser.add_argument("--status-path", type=Path, required=True)
    args = parser.parse_args()

    summary = build_what_next(args.status_path)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
