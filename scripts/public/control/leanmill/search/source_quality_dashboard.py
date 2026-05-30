#!/usr/bin/env python3
"""Report source-funnel quality for GP225 sourcing packets.

The unit here is a source lead, not a proof attempt. It makes the sourcing CRM
explicit:
raw source -> source-safe -> name-resolved -> action-compatible ->
target-compatible -> canary-ready row.

This script is read-only and does not run Lean.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


def _read_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(errors="ignore"))


def _pct(num: int | float, den: int | float) -> float | None:
    if not den:
        return None
    return round(float(num) / float(den), 4)


def _source_rows(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("row_id") or ""): r for r in packet.get("rows") or []}


def _static_rows(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(r.get("row_id") or ""): r
        for r in packet.get("rows") or []
        if not str(r.get("row_id") or "").startswith("__")
    }


def _row_context_rows(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(r.get("row_id") or ""): r
        for r in packet.get("rows") or []
        if not str(r.get("row_id") or "").startswith("__")
    }


def _row_stage(row_id: str, source: dict[str, Any], static: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    raw = int(source.get("retrieved_total") or 0)
    exact_excluded = int(source.get("exact_target_excluded_count") or 0)
    post_target = int(source.get("post_target_forbidden_count") or 0)
    source_safe = int(source.get("usable_candidate_count") or 0)
    resolved = int(static.get("resolved_count") or 0)
    action_compatible = int(static.get("canary_ready_count") or 0)
    target_compatible = int(context.get("row_context_resolved_count") or 0)
    canary_ready = target_compatible > 0
    reasons: Counter[str] = Counter()
    if exact_excluded:
        reasons["exact_target_leak_excluded"] += exact_excluded
    if post_target:
        reasons["post_target_same_file_forbidden"] += post_target
    for cand in static.get("candidates") or []:
        if not cand.get("pre_lean_allowed"):
            reasons[str(cand.get("pre_lean_reason") or "blocked_before_lean")] += 1
        elif not cand.get("name_resolves"):
            reasons[str(cand.get("resolution_status") or "name_resolution_failed")] += 1
        elif not cand.get("usable_for_canary_source"):
            reasons["resolved_but_not_action_compatible"] += 1
    for cand in context.get("candidates") or []:
        if not cand.get("row_context_resolves"):
            sample = str(cand.get("error_sample") or "")
            if "unmapped_row_context_error" in sample:
                reasons["target_context_unmapped_error"] += 1
            elif sample:
                reasons["target_context_name_or_import_failure"] += 1
            else:
                reasons["target_context_not_resolved"] += 1
    if source_safe and not static:
        reasons["not_static_filtered"] += source_safe
    if action_compatible and not context:
        reasons["not_target_context_filtered"] += action_compatible
    stage = "raw"
    if source_safe:
        stage = "source_safe"
    if resolved:
        stage = "resolved"
    if action_compatible:
        stage = "action_compatible"
    if target_compatible:
        stage = "target_compatible"
    if canary_ready:
        stage = "canary_ready"
    return {
        "row_id": row_id,
        "stage": stage,
        "raw_sources": raw,
        "source_safe_sources": source_safe,
        "name_resolved_sources": resolved,
        "action_compatible_sources": action_compatible,
        "target_compatible_sources": target_compatible,
        "canary_ready": canary_ready,
        "exact_target_excluded": exact_excluded,
        "post_target_forbidden": post_target,
        "top_reject_reasons": reasons.most_common(6),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    source = _read_json(args.source_packet)
    static = _read_json(args.static_filter)
    context = _read_json(args.row_context_filter)
    source_by = _source_rows(source)
    static_by = _static_rows(static)
    context_by = _row_context_rows(context)
    row_ids = sorted(set(source_by) | set(static_by) | set(context_by))
    rows = [
        _row_stage(rid, source_by.get(rid, {}), static_by.get(rid, {}), context_by.get(rid, {}))
        for rid in row_ids
    ]
    totals = {
        "rows": len(rows),
        "raw_sources": sum(r["raw_sources"] for r in rows),
        "source_safe_sources": sum(r["source_safe_sources"] for r in rows),
        "name_resolved_sources": sum(r["name_resolved_sources"] for r in rows),
        "action_compatible_sources": sum(r["action_compatible_sources"] for r in rows),
        "target_compatible_sources": sum(r["target_compatible_sources"] for r in rows),
        "canary_ready_rows": sum(1 for r in rows if r["canary_ready"]),
        "exact_target_excluded": sum(r["exact_target_excluded"] for r in rows),
        "post_target_forbidden": sum(r["post_target_forbidden"] for r in rows),
    }
    rates = {
        "source_safe_per_raw": _pct(totals["source_safe_sources"], totals["raw_sources"]),
        "resolved_per_source_safe": _pct(totals["name_resolved_sources"], totals["source_safe_sources"]),
        "action_compatible_per_resolved": _pct(totals["action_compatible_sources"], totals["name_resolved_sources"]),
        "target_compatible_per_action_compatible": _pct(totals["target_compatible_sources"], totals["action_compatible_sources"]),
        "canary_ready_rows_per_row": _pct(totals["canary_ready_rows"], totals["rows"]),
        "canary_ready_rows_per_100_raw_sources": (
            round(100 * totals["canary_ready_rows"] / totals["raw_sources"], 3)
            if totals["raw_sources"] else None
        ),
    }
    stage_counts = Counter(r["stage"] for r in rows)
    reasons: Counter[str] = Counter()
    for row in rows:
        for reason, n in row["top_reject_reasons"]:
            reasons[reason] += int(n)
    bottleneck = "no_sources"
    if totals["raw_sources"] and not totals["source_safe_sources"]:
        bottleneck = "source_safety"
    elif totals["source_safe_sources"] and not totals["name_resolved_sources"]:
        bottleneck = "name_resolution"
    elif totals["name_resolved_sources"] and not totals["action_compatible_sources"]:
        bottleneck = "action_compatibility"
    elif totals["action_compatible_sources"] and not totals["target_compatible_sources"]:
        bottleneck = "target_context_compatibility"
    elif totals["target_compatible_sources"] and not totals["canary_ready_rows"]:
        bottleneck = "row_packaging"
    elif totals["canary_ready_rows"]:
        bottleneck = "downstream_factory_or_path_c"
    payload = {
        "schema": "leansearch-source-quality-dashboard-v1",
        "label": args.label,
        "source_packet": args.source_packet,
        "static_filter": args.static_filter,
        "row_context_filter": args.row_context_filter,
        "totals": totals,
        "rates": rates,
        "row_stage_counts": dict(sorted(stage_counts.items())),
        "top_reject_reasons": reasons.most_common(args.top_reasons),
        "bottleneck": bottleneck,
        "interpretation": {
            "unit": "source leads before Path A spend",
            "optimize": "canary_ready_rows_per_100_raw_sources",
            "not_enough": "raw source volume without target/action-compatible canary rows",
        },
        "rows": rows[: args.max_rows_out],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        _write_md(payload, Path(args.markdown))
    return payload


def _write_md(payload: dict[str, Any], path: Path) -> None:
    t = payload["totals"]
    r = payload["rates"]
    lines = [
        f"# Source Quality Dashboard: {payload['label']}",
        "",
        f"Bottleneck: `{payload['bottleneck']}`",
        "",
        "| Stage | Count |",
        "|---|---:|",
        f"| Raw sources | {t['raw_sources']} |",
        f"| Source-safe sources | {t['source_safe_sources']} |",
        f"| Name-resolved sources | {t['name_resolved_sources']} |",
        f"| Action-compatible sources | {t['action_compatible_sources']} |",
        f"| Target-compatible sources | {t['target_compatible_sources']} |",
        f"| Canary-ready rows | {t['canary_ready_rows']} |",
        "",
        f"Canary-ready rows per 100 raw sources: `{r['canary_ready_rows_per_100_raw_sources']}`",
        "",
        "## Top Reject Reasons",
        "",
    ]
    for reason, n in payload["top_reject_reasons"]:
        lines.append(f"- `{reason}`: {n}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source.json"
        static = root / "static.json"
        context = root / "context.json"
        source.write_text(json.dumps({"rows": [{
            "row_id": "r1",
            "retrieved_total": 3,
            "usable_candidate_count": 2,
            "exact_target_excluded_count": 1,
            "post_target_forbidden_count": 0,
        }]}))
        static.write_text(json.dumps({"rows": [{
            "row_id": "r1",
            "resolved_count": 1,
            "canary_ready_count": 1,
            "candidates": [{"pre_lean_allowed": True, "name_resolves": True, "usable_for_canary_source": True}],
        }]}))
        context.write_text(json.dumps({"rows": [{
            "row_id": "r1",
            "row_context_resolved_count": 1,
            "candidates": [{"row_context_resolves": True}],
        }]}))
        obj = build(argparse.Namespace(
            label="self",
            source_packet=str(source),
            static_filter=str(static),
            row_context_filter=str(context),
            out=None,
            markdown=None,
            top_reasons=10,
            max_rows_out=20,
        ))
        assert obj["totals"]["raw_sources"] == 3, obj
        assert obj["totals"]["canary_ready_rows"] == 1, obj
        assert obj["bottleneck"] == "downstream_factory_or_path_c", obj
    print("leansearch_source_quality_dashboard self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="source_batch")
    ap.add_argument("--source-packet")
    ap.add_argument("--static-filter")
    ap.add_argument("--row-context-filter")
    ap.add_argument("--out")
    ap.add_argument("--markdown")
    ap.add_argument("--top-reasons", type=int, default=12)
    ap.add_argument("--max-rows-out", type=int, default=100)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(args)
    print(json.dumps({
        "label": obj["label"],
        "bottleneck": obj["bottleneck"],
        "totals": obj["totals"],
        "rates": obj["rates"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
