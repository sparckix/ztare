#!/usr/bin/env python3
"""Compatibility shim for the claim-discipline demo.

Use `scripts/public/control/claim_discipline_demo.py` or
`make demo-claim-discipline` for the public entry point.
"""
from __future__ import annotations

from claim_discipline_demo import build_demo_payload, main


if __name__ == "__main__":
    raise SystemExit(main())
