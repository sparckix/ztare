#!/usr/bin/env python3
"""Validate local Markdown links in public documentation.

External links are intentionally skipped. The goal is to catch stale local
paths in the public docs and README entry surfaces.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


REPO = Path(__file__).resolve().parents[3]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
DEFAULT_ROOTS = ["README.md", "docs"]


def tracked_markdown(roots: list[str]) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", *roots],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git ls-files failed")
    return [
        REPO / line
        for line in result.stdout.splitlines()
        if line.endswith(".md")
    ]


def normalize_target(raw: str) -> str | None:
    target = raw.strip()
    if not target or target.startswith("#"):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if SCHEME_RE.match(target):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    return unquote(target)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    failures: list[str] = []
    for match in LINK_RE.finditer(text):
        target = normalize_target(match.group(1))
        if target is None:
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(REPO)
        except ValueError:
            failures.append(f"{path.relative_to(REPO)}: link escapes repo: {target}")
            continue
        if not resolved.exists():
            failures.append(f"{path.relative_to(REPO)}: missing link target: {target}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="*", default=DEFAULT_ROOTS)
    args = parser.parse_args()

    failures: list[str] = []
    for path in tracked_markdown(args.roots):
        failures.extend(check_file(path))

    if failures:
        print("markdown link check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"markdown links OK ({len(tracked_markdown(args.roots))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
