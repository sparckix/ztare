"""Command-line compiler for declarative JaggedThoughts profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .profile import compile_profile_file
from .exploration import build_exploration_agenda
from .representation import challenge_representation
from .report import render_strategy_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jaggedthoughts",
        description="Compile a typed strategy grammar and frontier certificate.",
    )
    parser.add_argument("profile", help="Path to a JaggedThoughts YAML/JSON profile")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print only certificate identities, counts, and closure states",
    )
    parser.add_argument(
        "--agenda",
        action="store_true",
        help="Print the frontier-sensitive next-question agenda",
    )
    parser.add_argument(
        "--challenge",
        metavar="PROFILE",
        help="Compare the baseline profile with a challenger grammar epoch",
    )
    parser.add_argument(
        "--challenge-id",
        default="jaggedthoughts-cli-challenge",
        help="Stable identity for a representation challenge",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write the compiled JSON artifact to PATH instead of stdout",
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write a named Markdown decision report to PATH",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    compiled = compile_profile_file(args.profile)
    if args.challenge:
        if args.agenda:
            raise SystemExit("--agenda cannot be combined with --challenge")
        challenger = compile_profile_file(args.challenge)
        challenge = challenge_representation(
            challenge_id=args.challenge_id,
            baseline=compiled,
            challenger=challenger,
        )
        payload = challenge.summary() if args.summary else challenge.to_dict()
    elif args.agenda:
        payload = build_exploration_agenda(compiled).to_dict()
    else:
        payload = compiled.summary() if args.summary else compiled.to_dict()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.report:
        if args.challenge:
            raise SystemExit("--report cannot be combined with --challenge")
        render_strategy_report(compiled, dest=args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
