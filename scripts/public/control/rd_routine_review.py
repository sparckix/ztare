#!/usr/bin/env python3
"""rd_routine_review — standing reconciliation review for the RD pattern catalog.

Ports the cognitive-firm `routine_reviews` primitive: every pattern is a durable
"routine" that must be periodically reviewed, or it rots. This script surfaces
the organizational-forgetting signal — patterns past their `review_due` — and,
for each pattern, reports deployment count and whether it carries a quantified
`falsifiable_test`.

Inputs (read-only):
  org/runtime/pattern_catalog.yaml
  analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl

stdlib + PyYAML only. See CANDIDATE_routine_reviews_port.md for the design.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "org" / "runtime" / "pattern_catalog.yaml"
LEDGER_PATH = (
    REPO_ROOT / "analytics" / "public" / "ledgers" / "pattern_deployment"
    / "pattern_deployment_ledger.jsonl"
)


def load_catalog(path: Path) -> dict:
    """Load the generated pattern catalog."""
    if not path.is_file():
        sys.exit(f"ERROR: pattern catalog not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("patterns", {}) if isinstance(data, dict) else {}


def load_deployment_counts(path: Path) -> dict[str, int]:
    """Count deployments per pattern from the JSONL ledger.

    A row counts toward its primary pattern and each of its secondary patterns.
    """
    counts: dict[str, int] = {}
    if not path.is_file():
        print(f"WARN: deployment ledger not found: {path}", file=sys.stderr)
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            print(f"WARN: skipping malformed ledger line", file=sys.stderr)
            continue
        primary = row.get("primary_pattern") or row.get("pattern_id")
        if primary:
            counts[primary] = counts.get(primary, 0) + 1
        for sec in row.get("secondary_patterns") or []:
            if sec:
                counts[sec] = counts.get(sec, 0) + 1
    return counts


def parse_due(value) -> date | None:
    """Parse a review_due field into a date, tolerating str or date."""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def main() -> int:
    today = date.today()
    patterns = load_catalog(CATALOG_PATH)
    counts = load_deployment_counts(LEDGER_PATH)

    rows = []
    overdue = []
    no_test = []
    for pid, p in sorted(patterns.items()):
        deploys = counts.get(pid, 0)
        due = parse_due(p.get("review_due"))
        is_overdue = due is not None and due < today
        has_test = bool(str(p.get("falsifiable_test", "")).strip())
        rows.append((pid, deploys, due, is_overdue, has_test))
        if is_overdue:
            overdue.append((pid, due))
        if not has_test:
            no_test.append(pid)

    print("=" * 72)
    print(f"RD ROUTINE REVIEW — {today.isoformat()}")
    print(f"catalog: {len(patterns)} patterns | ledger: {sum(counts.values())} dispatches")
    print("=" * 72)
    print(f"{'pattern':<20} {'deploys':>8} {'review_due':>12} {'overdue':>8} {'f-test':>7}")
    print("-" * 72)
    for pid, deploys, due, is_overdue, has_test in rows:
        due_s = due.isoformat() if due else "—"
        print(f"{pid:<20} {deploys:>8} {due_s:>12} "
              f"{('YES' if is_overdue else 'no'):>8} "
              f"{('yes' if has_test else 'MISSING'):>7}")

    print("-" * 72)
    print(f"SUMMARY: {len(overdue)} overdue, {len(no_test)} missing falsifiable_test")
    if overdue:
        print("\nOVERDUE (organizational-forgetting pressure — review now):")
        for pid, due in sorted(overdue, key=lambda x: x[1]):
            print(f"  - {pid}  (due {due.isoformat()})")
    else:
        print("No reviews overdue.")
    if no_test:
        print("\nMISSING falsifiable_test (amend candidates):")
        for pid in no_test:
            print(f"  - {pid}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
