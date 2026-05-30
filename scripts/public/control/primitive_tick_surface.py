#!/usr/bin/env python3
"""Render the RD tick-start primitive discoverability surface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from src.ztare.research_director.primitive_tick_surface import (  # noqa: E402
    excluded_terms_for_scope,
    query_terms_for_scope,
    render_text,
    write_primitive_tick_surface,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--per-bucket", type=int, default=4)
    parser.add_argument(
        "--scope",
        default=None,
        help=(
            "Use scope-aware query/exclusion terms, e.g. ns or neural_hunt. "
            "Ignored when --term is provided."
        ),
    )
    parser.add_argument(
        "--term",
        action="append",
        default=None,
        help="Override query terms. Repeatable. Defaults to NS/math RD tick terms.",
    )
    args = parser.parse_args()

    surface = write_primitive_tick_surface(
        query_terms=args.term or query_terms_for_scope(args.scope),
        excluded_terms=None if args.term else excluded_terms_for_scope(args.scope),
        top_n=args.top,
        per_bucket=args.per_bucket,
    )
    print(render_text(surface))
    return 0 if surface.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
