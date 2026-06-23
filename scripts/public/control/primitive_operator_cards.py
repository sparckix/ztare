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
    OPERATOR_CARD_ATLAS_MANIFEST_PATH,
    OPERATOR_CARD_ATLAS_PATH,
    build_operator_card_atlas,
    operator_card_catalog_entries,
    render_obligation_classes,
    render_operator_cards,
    route_obligation_classes,
    route_operator_cards_semantic,
    write_operator_cards,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--context-file")
    parser.add_argument("--top", type=int, default=2)
    parser.add_argument("--semantic", action="store_true")
    parser.add_argument("--print-catalog-json", action="store_true")
    parser.add_argument("--build-atlas", action="store_true")
    parser.add_argument("--atlas-out", default=str(OPERATOR_CARD_ATLAS_PATH))
    parser.add_argument("--manifest-out", default=str(OPERATOR_CARD_ATLAS_MANIFEST_PATH))
    parser.add_argument(
        "--out",
        default="analytics/public/queries/rd_operator_cards_experimental.json",
    )
    args = parser.parse_args(argv)

    if args.print_catalog_json:
        import json

        print(json.dumps(operator_card_catalog_entries(), indent=2, sort_keys=True))
        return 0

    if args.build_atlas:
        atlas = build_operator_card_atlas(
            out_emb=Path(args.atlas_out),
            out_manifest=Path(args.manifest_out),
        )
        print(f"wrote operator card atlas: {args.atlas_out} rows={atlas.get('size')}")
        return 0

    context = list(args.context)
    if args.context_file:
        context.append(Path(args.context_file).read_text(encoding="utf-8"))

    if args.semantic:
        cards = route_operator_cards_semantic(context=context, top_n=args.top)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        import json
        from dataclasses import asdict
        from ztare.research_director.primitive_operator_cards import (
            GP219_PROMOTION_POLICY,
            operator_cards_to_kernel_action_schemas,
        )

        Path(args.out).write_text(
            json.dumps(
                {
                    "ok": bool(cards),
                    "routing_mode": "semantic_with_deterministic_fallback",
                    "obligation_route": [
                        asdict(item)
                        for item in route_obligation_classes(context=context, top_n=args.top)
                    ],
                    "top_cards": [asdict(card) for card in cards],
                    "kernel_action_schemas": operator_cards_to_kernel_action_schemas(cards),
                    "promotion_policy": GP219_PROMOTION_POLICY,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
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
