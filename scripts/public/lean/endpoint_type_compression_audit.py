#!/usr/bin/env python3
"""GP-223 Layer 3 — endpoint-type-compression post-hoc audit.

Walks recent typed_endpoint_pack failure log entries and verified
patches, attempts a deterministic compression check (does the
endpoint's type match a projection of any carried receipt?) and
flags candidates that COULD have been closed by projection without
LLM patch.

Per GP-223 seam, this is the cheapest mechanization: it doesn't
prevent the issue at PRE-LLM time (that's Layers 1+2 of the gate),
but it produces the empirical ROI evidence needed to justify
shipping Layers 1+2 — and surfaces operator-time tightening
candidates immediately.

Output: ``analytics/public/queries/lean/endpoint_compression_audit.json`` with
per-event flagging + summary metrics. Read by RD on the periodic
review and (eventually) by the reflexive_audit Component 1.

Usage:
    python scripts/public/lean/endpoint_type_compression_audit.py
    python scripts/public/lean/endpoint_type_compression_audit.py --lookback-days 14
    python scripts/public/lean/endpoint_type_compression_audit.py --verbose
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FAILURE_LOG = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "typed_endpoint_failure_log.jsonl"
)
RUNS_DIR = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "typed_endpoint_runs"
)
OUT_PATH = REPO / "analytics" / "public" / "queries" / "lean" / "endpoint_compression_audit.json"


# Heuristic: an endpoint named `<noun>_of_<source_obj_qualifier>` strongly
# suggests projection structure. e.g.,
# `capacity_of_macroscopic_clock_sources` ←→ projection of a clock-sources
# receipt. Pattern-match this name shape as the v0 detector.
ENDPOINT_PROJECTION_NAME_RE = re.compile(
    r"^(?P<core>[a-z][a-z0-9_]*)_of_(?P<qualifier>[a-z][a-z0-9_]*)$"
)


def parse_failure_log(lookback_days: int = 28) -> list[dict]:
    """Read recent CANNOT-PATCH events from the failure log."""
    if not FAILURE_LOG.exists():
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    out = []
    for line in FAILURE_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = str(rec.get("ts") or "")
        if ts and ts < cutoff:
            continue
        out.append(rec)
    return out


def detect_projection_shape(endpoint_field: str) -> dict | None:
    """Layer 3 v0 detector: pattern-match endpoint name shape.

    Returns a candidate dict when the endpoint name is in
    `<core>_of_<qualifier>` form (the canonical projection shape
    surfaced by the NS Track B 2026-05-06 reframe). Returns None
    otherwise.

    This is intentionally narrow: false-positive rate matters more
    than recall here, because the audit's purpose is to surface
    candidates an operator/RD reviews — not to autonomously close
    them.
    """
    m = ENDPOINT_PROJECTION_NAME_RE.match(endpoint_field)
    if not m:
        return None
    core = m.group("core")
    qualifier = m.group("qualifier")
    return {
        "name_pattern": "X_of_Y",
        "core": core,
        "qualifier": qualifier,
        "candidate_explanation": (
            f"Endpoint name `{endpoint_field}` matches the X_of_Y "
            f"projection shape. Per GP-223, check whether `{core}` "
            f"appears as a field accessor on any carried receipt "
            f"object qualified by `{qualifier}` (or its variants); "
            f"if yes, close by projection rather than fresh patch."
        ),
    }


def parse_target_for_carried_receipts(target_text: str) -> list[str]:
    """Best-effort extraction of carried receipt type names from the
    target field of a CANNOT-PATCH event.

    Looks for ``Pattern1Receipt``, ``Foo.bar.BazReceipt`` shapes —
    types ending in `Receipt`, `Bridge`, `Bundle`, `Obligation` are
    common ZTARE-spine conventions per the NS Track B corpus.
    """
    if not isinstance(target_text, str):
        return []
    types = set()
    for m in re.finditer(
        r"\b([A-Z][A-Za-z0-9_]*(?:Receipt|Bridge|Bundle|Obligation|Source|Profile|Stream|Adapter))\b",
        target_text,
    ):
        types.add(m.group(1))
    return sorted(types)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=28)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    print(f"=== GP-223 Layer 3 endpoint-type-compression post-hoc audit ===")
    print(f"  failure log: {FAILURE_LOG}")
    print(f"  lookback: {args.lookback_days} days")

    events = parse_failure_log(lookback_days=args.lookback_days)
    print(f"  events in window: {len(events)}")

    audit_records = []
    n_compression_candidates = 0
    by_pattern: dict[str, int] = {}

    for ev in events:
        endpoint_field = str(ev.get("field", "")).strip()
        target = str(ev.get("target", "")).strip()
        category = str(ev.get("category", "")).strip()
        if not endpoint_field:
            continue

        shape = detect_projection_shape(endpoint_field)
        if shape is None:
            continue

        carried_receipts = parse_target_for_carried_receipts(target)
        record = {
            "ts": ev.get("ts"),
            "target": target,
            "field": endpoint_field,
            "category": category,
            "patch_class": ev.get("patch_class"),
            "name_pattern": shape["name_pattern"],
            "projection_core": shape["core"],
            "projection_qualifier": shape["qualifier"],
            "candidate_carried_receipts": carried_receipts,
            "explanation": shape["candidate_explanation"],
            # Heuristic confidence: low for v0; tightens once
            # Layers 1+2 ship and we measure false-positive rate.
            "confidence": "low",
        }
        audit_records.append(record)
        n_compression_candidates += 1
        by_pattern[shape["name_pattern"]] = by_pattern.get(shape["name_pattern"], 0) + 1

        if args.verbose:
            print(f"  candidate: {endpoint_field}")
            print(f"    target: {target[:80]}")
            print(f"    carried: {carried_receipts[:3]}")

    summary = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "lookback_days": args.lookback_days,
        "events_scanned": len(events),
        "compression_candidates": n_compression_candidates,
        "candidates_by_pattern": by_pattern,
        "decision_threshold": (
            "Layers 1+2 of GP-223 ship-ready when ≥3 candidates surface "
            "across ≥2 distinct substrates over a 28-day window."
        ),
        "next_step": (
            "RD reviews each candidate; for cases where the carried-receipt "
            "structure is verifiably present, sketch the projection "
            "constructor manually as an experiment. Use those experiments "
            "to seed Layer 1's heuristic."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {"summary": summary, "candidates": audit_records}, indent=2
        )
    )
    print(f"\n=== summary ===")
    print(f"  candidates surfaced: {n_compression_candidates} / {len(events)} events")
    print(f"  by pattern: {by_pattern}")
    print(f"  saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
