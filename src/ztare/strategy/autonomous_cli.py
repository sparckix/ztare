"""Command line for compiling and advancing autonomous JaggedThoughts loops."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .autonomous_report import render_autonomous_strategy_report
from .autonomy import compile_autonomous_profile_file, run_autonomous_step


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jaggedthoughts-auto",
        description="Compile or advance a bounded autonomous strategy loop.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("profile")
    compile_parser.add_argument("--run-state")
    compile_parser.add_argument("--summary", action="store_true")
    compile_parser.add_argument("--output")
    compile_parser.add_argument("--report")
    step_parser = subparsers.add_parser("step")
    step_parser.add_argument("profile")
    step_parser.add_argument("--run-state")
    step_parser.add_argument("--run-state-out", required=True)
    step_parser.add_argument("--adapter-root")
    step_parser.add_argument("--output")
    step_parser.add_argument("--report")
    return parser


def _emit(payload: dict, destination: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if destination:
        Path(destination).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "compile":
        compiled = compile_autonomous_profile_file(
            args.profile,
            run_state_path=args.run_state,
        )
        _emit(compiled.summary() if args.summary else compiled.to_dict(), args.output)
        if args.report:
            render_autonomous_strategy_report(compiled, dest=args.report)
        return 0
    step = run_autonomous_step(
        args.profile,
        run_state_path=args.run_state,
        adapter_root=args.adapter_root,
    )
    Path(args.run_state_out).write_text(
        json.dumps(step.run_state.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _emit(step.to_dict(), args.output)
    if args.report:
        render_autonomous_strategy_report(step.after, dest=args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
