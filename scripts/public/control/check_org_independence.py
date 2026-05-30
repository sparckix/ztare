#!/usr/bin/env python3
"""CI lint: verify `org/` source files don't import ZTARE-specific modules.

Per `org/INTERFACE.md` (Debate B verdict 2026-05-08), `org/` is engineered
to be split-ready. The falsifiable boundary check:

    grep -r 'from src.ztare\|import ztare' org/  ==>  must return empty

This script enforces that constraint over `org/` Python files (if any) and
flags markdown files that contain ZTARE-specific function-call prescriptions
(distinguishing prescription from documentation references).

Exit code:
    0  — clean
    1  — violations found
    2  — runtime error (script bug)

Run as part of CI; also runnable standalone:

    python scripts/public/control/check_org_independence.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ORG_DIR = REPO_ROOT / "org"

# Forbidden imports in `org/` Python source
FORBIDDEN_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+src\.ztare", re.MULTILINE),
    re.compile(r"^\s*import\s+src\.ztare", re.MULTILINE),
    re.compile(r"^\s*from\s+ztare\b", re.MULTILINE),
    re.compile(r"^\s*import\s+ztare\b", re.MULTILINE),
]

# Forbidden patterns in `org/` markdown — actual code prescription, not
# documentation reference. We allow:
#   - relative path mentions (`src/ztare/...`)
#   - documentation discussion in prose
# We forbid:
#   - executable code blocks that import ZTARE
ZTARE_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:python|py)\n.*?(?:from\s+src\.ztare|import\s+(?:src\.ztare|ztare)).*?\n```",
    re.MULTILINE | re.DOTALL,
)


def scan_python_files(org_dir: Path) -> list[tuple[Path, str]]:
    """Find Python files in `org/` that violate import rules."""
    violations: list[tuple[Path, str]] = []
    for py_path in org_dir.rglob("*.py"):
        text = py_path.read_text(encoding="utf-8", errors="replace")
        for pat in FORBIDDEN_IMPORT_PATTERNS:
            match = pat.search(text)
            if match:
                # Find line number
                line_no = text[: match.start()].count("\n") + 1
                violations.append(
                    (py_path, f"line {line_no}: {match.group(0).strip()}")
                )
    return violations


def scan_markdown_code_blocks(org_dir: Path) -> list[tuple[Path, str]]:
    """Find markdown code blocks in `org/` that prescribe ZTARE imports."""
    violations: list[tuple[Path, str]] = []
    for md_path in org_dir.rglob("*.md"):
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for match in ZTARE_CODE_BLOCK_PATTERN.finditer(text):
            line_no = text[: match.start()].count("\n") + 1
            snippet = match.group(0).split("\n")[1] if "\n" in match.group(0) else "<empty>"
            violations.append(
                (md_path, f"line {line_no}: code block imports ZTARE: {snippet[:80]}")
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint org/ for forbidden imports of ZTARE-specific modules"
    )
    parser.add_argument(
        "--org-dir",
        type=Path,
        default=ORG_DIR,
        help="Directory to scan (default: org/)",
    )
    args = parser.parse_args()

    if not args.org_dir.is_dir():
        print(f"ERROR: org dir not found: {args.org_dir}", file=sys.stderr)
        return 2

    py_violations = scan_python_files(args.org_dir)
    md_violations = scan_markdown_code_blocks(args.org_dir)

    if py_violations:
        print("FORBIDDEN ZTARE imports in org/ Python files:")
        for path, msg in py_violations:
            print(f"  {path.relative_to(REPO_ROOT)}: {msg}")
    if md_violations:
        print("FORBIDDEN ZTARE imports in org/ markdown code blocks:")
        for path, msg in md_violations:
            print(f"  {path.relative_to(REPO_ROOT)}: {msg}")

    if py_violations or md_violations:
        print(
            "\norg/ MUST be split-ready per org/INTERFACE.md.\n"
            "Remove ZTARE-specific imports OR move logic to src/ztare/.",
            file=sys.stderr,
        )
        return 1

    print(f"OK — org/ has no ZTARE-specific imports ({len(list(args.org_dir.rglob('*.py')))} .py, {len(list(args.org_dir.rglob('*.md')))} .md scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
