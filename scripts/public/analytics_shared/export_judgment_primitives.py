#!/usr/bin/env python3
"""Export the public-safe judgment primitive bundle.

Outputs:
- canonical JSON export inside this repo
- optional generated TypeScript mirrors for sibling product repos

This is the source-of-truth boundary between ZTARE's internal vocabulary stack
and downstream product surfaces.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.product_exports.judgment_primitives import (
    export_judgment_primitives_payload,
    render_typescript_module,
)


REPO = Path(__file__).resolve().parents[3]
DEFAULT_JSON = REPO / "analytics" / "public" / "product_exports" / "judgment_primitives.v1.json"
DEFAULT_TS_TARGETS = {
    "clearjudgment": REPO.parent / "clearjudgment" / "src" / "lib" / "generated" / "judgment-primitives.ts",
    "mini-ztare": REPO.parent / "mini-ztare" / "src" / "lib" / "generated" / "judgment-primitives.ts",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--ts-target",
        action="append",
        default=[],
        help="product repo slug to mirror into (clearjudgment, mini-ztare). Repeatable.",
    )
    args = parser.parse_args()

    payload = export_judgment_primitives_payload()

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote JSON export: {args.json_out}")

    if args.ts_target:
        ts_blob = render_typescript_module()
        for slug in args.ts_target:
            target = DEFAULT_TS_TARGETS.get(slug)
            if target is None:
                raise SystemExit(f"Unknown ts target: {slug}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(ts_blob, encoding="utf-8")
            print(f"Wrote TypeScript mirror: {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
