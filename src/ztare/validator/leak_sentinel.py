"""Leak sentinel — structural gate that greps mutator-visible files for GT contamination.

Usage:
    python -m src.ztare.validator.leak_sentinel <project_dir> <rubric_path> [--denylist-file PATH]

Exits 0 if clean, exits 1 if any match is found. Designed to run as a
pre-seal gate so that no sandbox ships with GT residue in mutator-visible
artifacts.

This replaces the manual 20-minute grep scrub. If a leak vector is not
in the denylist, it passes — the denylist must be maintained per-substrate
by Division A (the GT-aware author).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MUTATOR_VISIBLE_FILENAMES = {
    "project_charter.md",
    "thesis.md",
    "test_model.py",
    "evidence.txt",
}


def _load_denylist(path: Path | None) -> list[str]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8")
    patterns: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _scan_file(filepath: Path, patterns: list[re.Pattern]) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
    except Exception:
        return hits
    for lineno, line in enumerate(lines, 1):
        for pat in patterns:
            if pat.search(line):
                hits.append((lineno, pat.pattern, line.strip()))
    return hits


def run_sentinel(
    project_dir: Path,
    rubric_path: Path,
    extra_denylist: list[str] | None = None,
) -> dict[str, list[tuple[int, str, str]]]:
    patterns_raw = extra_denylist or []

    compiled = []
    for raw in patterns_raw:
        try:
            compiled.append(re.compile(raw, re.IGNORECASE))
        except re.error:
            compiled.append(re.compile(re.escape(raw), re.IGNORECASE))

    all_hits: dict[str, list[tuple[int, str, str]]] = {}

    for fname in MUTATOR_VISIBLE_FILENAMES:
        fpath = project_dir / fname
        if fpath.exists():
            hits = _scan_file(fpath, compiled)
            if hits:
                all_hits[str(fpath)] = hits

    if rubric_path.exists():
        hits = _scan_file(rubric_path, compiled)
        if hits:
            all_hits[str(rubric_path)] = hits

    return all_hits


def main() -> None:
    parser = argparse.ArgumentParser(description="Leak sentinel for sandbox pre-seal audit")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("rubric_path", type=Path)
    parser.add_argument("--denylist-file", type=Path, default=None)
    parser.add_argument("--denylist", nargs="*", default=[])
    args = parser.parse_args()

    file_patterns = _load_denylist(args.denylist_file)
    all_patterns = file_patterns + list(args.denylist)

    if not all_patterns:
        print("WARNING: empty denylist — sentinel passes vacuously", file=sys.stderr)
        sys.exit(0)

    hits = run_sentinel(args.project_dir, args.rubric_path, all_patterns)

    if not hits:
        print(f"SENTINEL PASSED — {len(all_patterns)} patterns, 0 matches")
        sys.exit(0)

    total = sum(len(v) for v in hits.values())
    print(f"SENTINEL FAILED — {total} match(es) across {len(hits)} file(s):\n")
    for filepath, file_hits in hits.items():
        for lineno, pattern, line_text in file_hits:
            print(f"  {filepath}:{lineno}  pattern={pattern!r}")
            print(f"    {line_text[:120]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
