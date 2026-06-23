#!/usr/bin/env python3
"""Fail on pyflakes undefined-name findings, and fail if pyflakes cannot run."""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Sequence


UNDEFINED_NAME_MARKER = "undefined name '"


def _load_pyflakes():
    try:
        from pyflakes import api
        from pyflakes.reporter import Reporter
    except Exception as exc:  # pragma: no cover - exercised by missing envs.
        raise RuntimeError(
            "pyflakes is not available; install requirements.txt before trusting this gate"
        ) from exc
    return api, Reporter


def check_paths(paths: Sequence[Path]) -> tuple[list[str], int, str]:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("flake gate path(s) do not exist: " + ", ".join(missing))

    api, reporter_cls = _load_pyflakes()
    stdout = io.StringIO()
    stderr = io.StringIO()
    reporter = reporter_cls(stdout, stderr)
    warning_count = api.checkRecursive([str(path) for path in paths], reporter)
    output = "\n".join(part for part in (stdout.getvalue(), stderr.getvalue()) if part)
    undefined_lines = [
        line for line in output.splitlines() if UNDEFINED_NAME_MARKER in line
    ]
    return undefined_lines, warning_count, output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="F821 tripwire: fail on undefined names and on missing pyflakes."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--label", default="flake scan")
    parser.add_argument(
        "--show-warning-count",
        action="store_true",
        help="Print the count of non-F821 pyflakes findings ignored by this narrow gate.",
    )
    args = parser.parse_args(argv)

    try:
        undefined_lines, warning_count, output = check_paths(args.paths)
    except Exception as exc:
        print(f"{args.label}: pyflakes gate failed to run: {exc}", file=sys.stderr)
        return 2

    if undefined_lines:
        print("\n".join(undefined_lines))
        print(
            f"^ FAIL: {args.label} F821 undefined-name(s) - each is a potential "
            "dead feature or live NameError",
            file=sys.stderr,
        )
        return 1

    ignored = warning_count - len(undefined_lines)
    if ignored and args.show_warning_count:
        print(
            f"{args.label}: 0 undefined names; pyflakes ran "
            f"({ignored} non-F821 warning(s) ignored)"
        )
    else:
        print(f"{args.label}: 0 undefined names; pyflakes import+scan verified")
    if output and not ignored:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
