#!/usr/bin/env python3
"""Standalone experimental CLI for primitive operator cards.

This script is intentionally not called by rd_tick_brief.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.research_director.primitive_operator_cards import (  # noqa: E402
    render_obligation_classes,
    render_operator_cards,
    route_obligation_classes,
    write_operator_cards,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--context-file")
    parser.add_argument("--top", type=int, default=2)
    parser.add_argument(
        "--out",
        default="analytics/public/queries/rd_operator_cards_experimental.json",
    )
    args = parser.parse_args(argv)

    context = list(args.context)
    if args.context_file:
        context.append(Path(args.context_file).read_text(encoding="utf-8"))

    cards = write_operator_cards(
        Path(args.out),
        context=context,
        top_n=args.top,
    )
    print(render_obligation_classes(route_obligation_classes(context=context, top_n=args.top)))
    print(render_operator_cards(cards))
    return 0 if cards else 1


if __name__ == "__main__":
    raise SystemExit(main())
