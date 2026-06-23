#!/usr/bin/env python3
"""Audit public-facing docs for broad claim phrases with no nearby boundary."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[3]

TARGETS = [
    REPO / "README.md",
    REPO / "PRINCIPLES.md",
    REPO / "CONTRIBUTING.md",
    REPO / "SECURITY.md",
    REPO / "priority_roadmap.md",
    REPO / "benchmarks/benchmark_evidence.md",
    REPO / "benchmarks/evaluator_hardening_frozen/README.md",
    REPO / "docs/public_claim_register.md",
    REPO / "docs/concepts/capabilities.md",
    REPO / "docs/concepts/harness_specification.md",
    REPO / "docs/concepts/leanmill_design_history.md",
    REPO / "docs/evidence_atlas",
    REPO / "docs/guides/quickstart.md",
    REPO / "docs/guides/for_researchers.md",
    REPO / "docs/multi_substrate_validation.md",
    REPO / "docs/sprint_70day_journey.md",
]

PATTERNS = [
    re.compile(r"\bSOTA\b", re.IGNORECASE),
    re.compile(r"\bbest autonomous\b", re.IGNORECASE),
    re.compile(r"(?<!-)\bsolved\b(?!-)", re.IGNORECASE),
    re.compile(r"\bapparatus-lift\b", re.IGNORECASE),
]

BOUNDARY_MARKERS = (
    "not ",
    "no ",
    "non-claim",
    "non-claims",
    "does not claim",
    "nothing here claims",
    "do not",
    "without",
    "missing",
    "falsifier",
    "demote",
    "demotion",
    "kept separate",
    "floor, not",
    "no apparatus-lift",
    "not a",
)

INLINE_CODE_RE = re.compile(r"`[^`]*`")
MARKDOWN_MARKER_RE = re.compile(r"[*_`]+")


def iter_files() -> Iterable[Path]:
    for target in TARGETS:
        if target.is_file():
            yield target
        elif target.is_dir():
            yield from sorted(path for path in target.rglob("*.md") if path.is_file())


def classify(path: Path, line_no: int, lines: list[str]) -> dict[str, object] | None:
    line = lines[line_no]
    search_line = INLINE_CODE_RE.sub("", line)
    matches = [pattern.pattern for pattern in PATTERNS if pattern.search(search_line)]
    if not matches:
        return None
    start = max(0, line_no - 2)
    end = min(len(lines), line_no + 3)
    window = MARKDOWN_MARKER_RE.sub("", " ".join(lines[start:end]).lower())
    allowed = any(marker in window for marker in BOUNDARY_MARKERS)
    return {
        "path": str(path.relative_to(REPO)),
        "line": line_no + 1,
        "text": line.strip(),
        "patterns": matches,
        "boundary_context": allowed,
    }


def main() -> int:
    findings = []
    checked_files: list[str] = []
    for path in iter_files():
        checked_files.append(str(path.relative_to(REPO)))
        lines = path.read_text(encoding="utf-8").splitlines()
        for i in range(len(lines)):
            row = classify(path, i, lines)
            if row:
                findings.append(row)

    unbounded = [row for row in findings if not row["boundary_context"]]
    payload = {
        "ok": not unbounded,
        "checked_files": checked_files,
        "finding_count": len(findings),
        "unbounded_count": len(unbounded),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if unbounded:
        raise SystemExit("scope boundary audit failed: broad claim phrase lacks nearby boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
