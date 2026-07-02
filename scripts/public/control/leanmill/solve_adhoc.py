#!/usr/bin/env python3
"""Run one formal Lean target through the governed LeanMill solver."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.leanmill.solver.solver_core import solve_adhoc_governed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ztare leanmill solve-adhoc",
        description="Run a single Lean declaration through LeanMill's governed proof path."
    )
    parser.add_argument("--target", required=True, help="Lean declaration name to prove.")
    parser.add_argument("--source-file", required=True, help="Lean file containing the target.")
    parser.add_argument("--goal", default="", help="Optional goal text shown to the solver.")
    parser.add_argument("--provider", default=None, help="Optional solver provider override.")
    parser.add_argument("--timeout", type=int, default=500, help="Attempt timeout in seconds.")
    parser.add_argument("--mode", choices=["cascade", "dag_search"], default="dag_search")
    parser.add_argument("--substrate", default=None, help="Optional Lake project directory.")
    parser.add_argument("--notes", default=None, help="Optional notes file to guide decomposition.")
    parser.add_argument("--json", action="store_true", help="Print JSON. Accepted for symmetry; output is JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else None
    substrate = Path(args.substrate) if args.substrate else None
    result = solve_adhoc_governed(
        args.target,
        source_text,
        args.goal,
        provider=args.provider,
        timeout_s=args.timeout,
        mode=args.mode,
        substrate=substrate,
        notes=notes,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
