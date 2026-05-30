#!/usr/bin/env python3
"""Qualify source leads before Path-A spend.

This is the source CRM gate for LeanMill. It reads the source packet plus
static/target-context filters and emits explicit row stages, source-quality
scores, reject reasons, and a ranked canary/factory buffer. It runs no Lean.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import leansearch_factory_intake as intake


DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/source_quality_filter.json"
DEFAULT_MD = "analytics/public/leanmill/dashboard_data/source_quality_filter.md"


ACTIVE_FAMILY_KEYWORDS: dict[str, list[str]] = {
    "convolution_argument_planner": ["convolution", "conv", "mconv", "integral_conv"],
    "iff_direction_planner": ["iff", "↔", "geom_mean", "weighted", "eq_arith_mean"],
    "ennreal_tsum_condensation_planner": ["ennreal", "tsum", "summable", "schlomilch", "condensed", "nnreal"],
    "interval_alignment_planner": ["ioc", "ioo", "icc", "interval", "inv_sq", "sum_ioc"],
    "source_action_shape_planner": ["apply", "shape", "could not unify", "contdiff", "linear_dependent"],
    "spectral_rayleigh_shape_planner": ["rayleigh", "spectrum", "eigen", "possemidef"],
    "mellin_fourier_shape_planner": ["mellin", "fourier", "transform"],
    "metric_speed_shape_planner": ["hasconstantspeedonwith", "constant", "speed", "lipschitz"],
    "target_context_import_or_name_planner": ["unknown", "identifier", "areaform", "tendsto", "oscillation"],
}


def _read(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(errors="ignore"))


def _rows(obj: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return obj
    return list(obj.get("rows") or obj.get("corpus") or obj.get("targets") or [])


def _by_row(obj: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _rows(obj):
        rid = str(row.get("row_id") or row.get("id") or "")
        if rid and not rid.startswith("__"):
            out[rid] = row
    return out


def _ready_names(row: dict[str, Any]) -> set[str]:
    names = {
        str(c.get("name") or "")
        for c in (
            row.get("row_context_ready_candidates")
            or row.get("target_context_ready_candidates")
            or row.get("canary_ready_candidates")
            or []
        )
    }
    names.discard("")
    return names


def _static_names(row: dict[str, Any]) -> set[str]:
    names = {str(c.get("name") or "") for c in row.get("canary_ready_candidates") or []}
    if not names:
        names = {
            str(c.get("name") or "")
            for c in row.get("candidates") or []
            if c.get("usable_for_canary_source") or c.get("name_resolves")
        }
    names.discard("")
    return names


def _active_families(blob: str) -> list[str]:
    low = blob.lower()
    out = []
    for family, kws in ACTIVE_FAMILY_KEYWORDS.items():
        if any(kw.lower() in low for kw in kws):
            out.append(family)
    return out


def _source_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    return list(row.get("usable_candidates") or row.get("candidates") or [])


def _candidate_quality(source_cand: dict[str, Any], static_row: dict[str, Any], context_row: dict[str, Any]) -> tuple[int, list[str], bool]:
    score = 0
    reasons: list[str] = []
    name = str(source_cand.get("name") or "")
    if name:
        score += 1
    if source_cand.get("source_order_safe") or source_cand.get("source_safety_status") == "non_target_external_module_candidate":
        score += 2
    else:
        reasons.append(str(source_cand.get("source_safety_status") or "source_safety_unknown"))
    if source_cand.get("post_target_forbidden"):
        score -= 8
        reasons.append("post_target_leakage")
    if source_cand.get("exact_target_excluded"):
        score -= 8
        reasons.append("exact_target_leakage")
    static_ready = name in _static_names(static_row)
    target_ready = name in _ready_names(context_row)
    if static_ready:
        score += 2
    else:
        reasons.append("not_action_compatible")
    if target_ready:
        score += 3
    else:
        reasons.append("not_target_context_ready")
    templates = source_cand.get("candidate_action_templates") or []
    if templates:
        score += 1
    else:
        reasons.append("no_action_template")
    blob = " ".join(str(source_cand.get(k) or "") for k in ("name", "type", "signature", "informal_name", "informal_description"))
    fams = _active_families(blob)
    if fams:
        score += 2
    else:
        reasons.append("no_active_residual_family_match")
    return score, reasons, target_ready


def _row_quality(row_id: str, source: dict[str, Any], static: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    raw = int(source.get("retrieved_total") or len(source.get("usable_candidates") or []))
    source_safe = int(source.get("usable_candidate_count") or len(source.get("usable_candidates") or []))
    resolved = int(static.get("resolved_count") or len(_static_names(static)))
    action_compatible = int(static.get("canary_ready_count") or len(_static_names(static)))
    target_compatible = int(context.get("row_context_resolved_count") or len(_ready_names(context)))
    lane = intake._lane_hint(context or static or {"row_id": row_id, "row_context_ready_candidates": []})
    blob = " ".join([
        row_id,
        str(source.get("theorem") or ""),
        str(source.get("query") or ""),
        " ".join(_ready_names(context)),
        " ".join(str(c.get("name") or "") for c in _source_candidates(source)),
    ])
    families = _active_families(blob)
    stage = "raw"
    if source_safe:
        stage = "source_safe"
    if resolved:
        stage = "resolved"
    if action_compatible:
        stage = "action_compatible"
    if target_compatible:
        stage = "canary_ready"
    reasons: Counter[str] = Counter()
    best_candidates = []
    best_score = -10**9
    target_ready_candidate_count = 0
    for cand in _source_candidates(source):
        score, cand_reasons, target_ready = _candidate_quality(cand, static, context)
        best_score = max(best_score, score)
        target_ready_candidate_count += int(target_ready)
        for reason in cand_reasons:
            reasons[reason] += 1
        if target_ready:
            best_candidates.append({
                "name": cand.get("name"),
                "score": score,
                "actions": cand.get("candidate_action_templates") or [],
                "source_safety_status": cand.get("source_safety_status"),
            })
    if source.get("exact_target_excluded_count"):
        reasons["exact_target_leak_excluded"] += int(source.get("exact_target_excluded_count") or 0)
    if source.get("post_target_forbidden_count"):
        reasons["post_target_same_file_forbidden"] += int(source.get("post_target_forbidden_count") or 0)
    row_score = 0
    row_score += 2 if source_safe else 0
    row_score += 2 if resolved else 0
    row_score += 2 if action_compatible else 0
    row_score += 2 if target_compatible else 0
    row_score += 2 if families else 0
    row_score += max(0, best_score) if best_score != -10**9 else 0
    negative_control_planned = bool(families and target_compatible)
    if negative_control_planned:
        row_score += 2
    else:
        reasons["missing_negative_control_plan"] += 1
    if lane == "unclassified":
        row_score -= 2
        reasons["unclassified_lane"] += 1
    if not target_compatible:
        reasons["not_canary_ready"] += 1
    state = "reject"
    if target_compatible:
        state = "canary_ready"
    if target_compatible and negative_control_planned and row_score >= 12:
        state = "factory_ready"
    return {
        "row_id": row_id,
        "state": state,
        "stage": stage,
        "lane_hint": lane,
        "score": row_score,
        "raw_sources": raw,
        "source_safe_sources": source_safe,
        "name_resolved_sources": resolved,
        "action_compatible_sources": action_compatible,
        "target_compatible_sources": target_compatible,
        "target_ready_candidate_count": target_ready_candidate_count,
        "active_residual_families": families,
        "negative_control_planned": negative_control_planned,
        "top_candidates": sorted(best_candidates, key=lambda c: -int(c["score"]))[:5],
        "reject_reasons": reasons.most_common(8),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_by = _by_row(_read(args.source_packet))
    static_by = _by_row(_read(args.static_filter))
    context_by = _by_row(_read(args.row_context_filter))
    row_ids = sorted(set(source_by) | set(static_by) | set(context_by))
    rows = [_row_quality(rid, source_by.get(rid, {}), static_by.get(rid, {}), context_by.get(rid, {})) for rid in row_ids]
    rows = sorted(rows, key=lambda r: (-int(r["score"]), str(r["row_id"])))
    selected = [r for r in rows if r["state"] == "factory_ready"][: args.max_factory_rows]
    canary = [r for r in rows if r["state"] in {"factory_ready", "canary_ready"}][: args.max_canary_rows]
    reasons: Counter[str] = Counter()
    for row in rows:
        for reason, n in row["reject_reasons"]:
            reasons[reason] += int(n)
    states = Counter(str(r["state"]) for r in rows)
    stages = Counter(str(r["stage"]) for r in rows)
    totals = {
        "rows": len(rows),
        "raw_sources": sum(int(r["raw_sources"]) for r in rows),
        "canary_ready_rows": sum(1 for r in rows if r["state"] in {"canary_ready", "factory_ready"}),
        "factory_ready_rows": len([r for r in rows if r["state"] == "factory_ready"]),
    }
    payload = {
        "schema": "leansearch-source-quality-filter-v1",
        "source_packet": args.source_packet,
        "static_filter": args.static_filter,
        "row_context_filter": args.row_context_filter,
        "score_threshold": 12,
        "totals": totals,
        "rates": {
            "canary_ready_rows_per_100_raw_sources": (
                round(100 * totals["canary_ready_rows"] / totals["raw_sources"], 3)
                if totals["raw_sources"] else None
            ),
            "factory_ready_rows_per_100_raw_sources": (
                round(100 * totals["factory_ready_rows"] / totals["raw_sources"], 3)
                if totals["raw_sources"] else None
            ),
        },
        "state_counts": dict(sorted(states.items())),
        "stage_counts": dict(sorted(stages.items())),
        "top_reject_reasons": reasons.most_common(args.top_reasons),
        "factory_buffer": selected,
        "canary_buffer": canary,
        "rows": rows[: args.max_rows_out],
        "science_rule": "Rows are source-qualified leads only; value credit requires Path-A compile plus Path-B ratification, exact-gap, valid-falsifier, or tested retirement.",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        _write_md(payload, Path(args.markdown))
    return payload


def _write_md(payload: dict[str, Any], path: Path) -> None:
    t = payload["totals"]
    lines = [
        "# Source Quality Filter",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {t['rows']} |",
        f"| Raw sources | {t['raw_sources']} |",
        f"| Canary-ready rows | {t['canary_ready_rows']} |",
        f"| Factory-ready rows | {t['factory_ready_rows']} |",
        f"| Canary-ready / 100 raw | {payload['rates']['canary_ready_rows_per_100_raw_sources']} |",
        f"| Factory-ready / 100 raw | {payload['rates']['factory_ready_rows_per_100_raw_sources']} |",
        "",
        "## Factory Buffer",
        "",
        "| Row | Lane | Score | Families | Top Candidates |",
        "|---|---|---:|---|---|",
    ]
    for row in payload["factory_buffer"]:
        cands = ", ".join(str(c.get("name")) for c in row.get("top_candidates") or [])
        fams = ", ".join(row.get("active_residual_families") or [])
        lines.append(f"| `{row['row_id']}` | `{row['lane_hint']}` | {row['score']} | `{fams}` | `{cands}` |")
    lines.extend(["", "## Top Reject Reasons", ""])
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
            "theorem": "summable_test",
            "query": "summable ENNReal",
            "retrieved_total": 2,
            "usable_candidate_count": 1,
            "usable_candidates": [{
                "name": "ENNReal.tsum_test",
                "kind": "theorem",
                "type": "summable tsum theorem",
                "candidate_action_templates": ["apply ENNReal.tsum_test"],
                "source_safety_status": "non_target_external_module_candidate",
                "source_order_safe": True,
            }],
        }]}))
        static.write_text(json.dumps({"rows": [{
            "row_id": "r1",
            "resolved_count": 1,
            "canary_ready_count": 1,
            "canary_ready_candidates": [{"name": "ENNReal.tsum_test"}],
        }]}))
        context.write_text(json.dumps({"rows": [{
            "row_id": "r1",
            "row_context_resolved_count": 1,
            "row_context_ready_candidates": [{"name": "ENNReal.tsum_test"}],
        }]}))
        obj = build(argparse.Namespace(
            source_packet=str(source),
            static_filter=str(static),
            row_context_filter=str(context),
            out=None,
            markdown=None,
            max_factory_rows=20,
            max_canary_rows=20,
            max_rows_out=20,
            top_reasons=10,
        ))
        assert obj["totals"]["factory_ready_rows"] == 1, obj
        assert obj["factory_buffer"][0]["lane_hint"] == "ennreal_tsum", obj
        assert obj["factory_buffer"][0]["negative_control_planned"], obj
    print("leansearch_source_quality_filter self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-packet", default="")
    ap.add_argument("--static-filter", default="")
    ap.add_argument("--row-context-filter", default="")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--max-factory-rows", type=int, default=20)
    ap.add_argument("--max-canary-rows", type=int, default=40)
    ap.add_argument("--max-rows-out", type=int, default=200)
    ap.add_argument("--top-reasons", type=int, default=12)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    missing = [name for name in ("source_packet", "static_filter", "row_context_filter") if not getattr(args, name)]
    if missing:
        raise SystemExit(f"missing required arguments: {', '.join('--' + m.replace('_', '-') for m in missing)}")
    obj = build(args)
    print(json.dumps({
        "factory_ready_rows": obj["totals"]["factory_ready_rows"],
        "canary_ready_rows": obj["totals"]["canary_ready_rows"],
        "canary_ready_rows_per_100_raw_sources": obj["rates"]["canary_ready_rows_per_100_raw_sources"],
        "factory_ready_rows_per_100_raw_sources": obj["rates"]["factory_ready_rows_per_100_raw_sources"],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
