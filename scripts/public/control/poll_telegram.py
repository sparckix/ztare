#!/usr/bin/env python3
"""One-shot CLI poller for GP-128b Telegram inbound channel.

Designed for cron-driven ticks. Calls poll_inbound, prints any new
messages, exits. Use --consume to advance the offset (default: peek).

Examples:
    python scripts/public/control/poll_telegram.py                  # peek, human output
    python scripts/public/control/poll_telegram.py --consume        # advance offset
    python scripts/public/control/poll_telegram.py --json           # JSON for downstream parsing
    python scripts/public/control/poll_telegram.py --authorized-only --consume
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `src.ztare...` importable when run from repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ztare.notifications.telegram import _cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(_cli())
