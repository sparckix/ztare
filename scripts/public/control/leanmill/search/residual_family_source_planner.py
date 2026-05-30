#!/usr/bin/env python3
"""Rank source leads by residual-family fit.

This is the cheap qualification layer between generic source retrieval and
Path-A spend. It turns recurring Path-C residual families into source-selection
profiles, then scores retrieved candidates by row goal/name, candidate name,
candidate type, and whether the row survived the row-context filter.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_PACKET = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_SOURCE_PACKET.json"
DEFAULT_ROW_CONTEXT = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"
DEFAULT_RESIDUAL_PLAN = "analytics/public/leanmill/dashboard_data/residual_plan_final.json"
DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/residual_family_source_plan.json"
DEFAULT_MD = "analytics/public/leanmill/dashboard_data/residual_family_source_plan.md"
DEFAULT_CANARY_OUT = "analytics/public/leanmill/dashboard_data/residual_family_canary_packets.json"


FAMILY_PROFILES: dict[str, dict[str, Any]] = {
    "target_context_import_or_name_planner": {
        "keywords": [
            "unknown", "identifier", "constant", "continuous", "oscillation", "rpow", "areaForm",
            "eigen", "tendsto", "mellin", "subadditive",
        ],
        "actions": [
            "verify candidate name under the exact target imports",
            "prefer names that pass row-context resolution",
            "downgrade unresolved names to source-quality failures before proof execution",
        ],
        "negative_controls": ["candidate resolves in global search but not in target import context"],
    },
    "source_action_shape_planner": {
        "keywords": ["could", "unify", "contdiff", "linear_dependent", "areaForm", "partialhomeomorph", "apply"],
        "actions": [
            "probe candidate with exact/apply/rw and score kernel goal delta",
            "construct a shape adapter before retrying direct apply",
        ],
        "negative_controls": ["direct apply of a resolvable source with wrong conclusion head"],
    },
    "spectral_rayleigh_shape_planner": {
        "keywords": ["rayleigh", "spectrum", "eigen", "possemidef", "operator", "symmetric", "resolvent"],
        "actions": [
            "align operator, spectrum, and Rayleigh quotient hypotheses",
            "separate positivity, symmetry, and finite-dimensional side goals",
        ],
        "negative_controls": ["spectrum theorem applied to a Rayleigh quotient goal without carrier alignment"],
    },
    "mellin_fourier_shape_planner": {
        "keywords": ["mellin", "fourier", "transform", "integrable", "ioo", "ioc"],
        "actions": [
            "normalize Mellin/Fourier transform definitions before applying Fourier lemmas",
            "split interval-domain alignment from transform equality",
        ],
        "negative_controls": ["Fourier theorem applied directly to a Mellin head"],
    },
    "metric_speed_shape_planner": {
        "keywords": ["hasconstantspeedonwith", "constant", "speed", "lipschitz", "edist", "subsingleton"],
        "actions": [
            "split zero-speed and constant-map cases",
            "route iff goals through constructor before applying Lipschitz lemmas",
        ],
        "negative_controls": ["Lipschitz constant theorem applied directly to HasConstantSpeedOnWith"],
    },
    "convolution_argument_planner": {
        "keywords": ["convolution", "conv", "mconv", "mlconvolution", "integral_conv", "lintegral_conv", "withDensity"],
        "actions": ["unfold convolution_def", "match argument order", "instantiate measure/invariance hypotheses"],
        "negative_controls": ["wrong convolution side", "measure convolution applied to pointwise function goal"],
    },
    "iff_direction_planner": {
        "keywords": ["iff", "↔", "geom_mean", "of_constant", "eq_arith_mean", "weighted"],
        "actions": ["constructor", "try forward and reverse rewrite directions separately", "emit exact gap for missing equality-case direction"],
        "negative_controls": ["wrong iff direction", "whole-iff apply without constructor"],
    },
    "ennreal_tsum_condensation_planner": {
        "keywords": ["ennreal", "tsum", "summable", "condensed", "coe_tsum", "nnreal"],
        "actions": ["normalize ENNReal/NNReal coercion shape", "avoid coe_tsum unless goal is equality of coercions"],
        "negative_controls": ["coe_tsum on inequality goal", "missing nonnegativity bridge"],
    },
    "interval_alignment_planner": {
        "keywords": ["ioc", "ioo", "icc", "interval", "inv_sq", "sum_ioc", "add_sq_le", "finset"],
        "actions": ["prove interval equivalence/subset first", "align Nat endpoints before applying bound"],
        "negative_controls": ["wrong interval endpoint", "post-shift denominator mismatch"],
    },
}


def _read_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(errors="ignore"))


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_]+|[↔]", text)}


def _contains_keyword(blob: str, keyword: str) -> bool:
    return keyword.lower() in blob.lower()


def _row_context_ready(row_context: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in row_context.get("rows") or []:
        out[str(row.get("row_id") or "")] = int(row.get("row_context_resolved_count") or 0)
    return out


def _row_context_ready_names(row_context: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in row_context.get("rows") or []:
        rid = str(row.get("row_id") or "")
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
        out[rid] = names
    return out


def _seed_rows(residual_plan: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {name: set() for name in FAMILY_PROFILES}
    for packet in residual_plan.get("packets") or []:
        family = str(packet.get("repair_family") or "")
        if family in out:
            out[family].update(str(r) for r in packet.get("rows") or [])
    return out


def _score_candidate(family: str, profile: dict[str, Any], row: dict[str, Any], cand: dict[str, Any],
                     target_ready_count: int, seed_rows: set[str]) -> dict[str, Any]:
    row_id = str(row.get("row_id") or "")
    blob = " ".join(str(x or "") for x in [
        row.get("row_id"),
        row.get("theorem"),
        row.get("query"),
        cand.get("name"),
        cand.get("type"),
        cand.get("signature"),
        cand.get("informal_name"),
        cand.get("informal_description"),
    ])
    hits = [kw for kw in profile["keywords"] if _contains_keyword(blob, kw)]
    score = 2 * len(hits)
    seed_match = row_id in seed_rows
    if seed_match:
        score += 8
    if target_ready_count:
        score += 5
    if cand.get("source_order_safe"):
        score += 2
    if cand.get("source_safety_status") == "non_target_external_module_candidate":
        score += 1
    if cand.get("requires_source_order_check") or cand.get("post_target_forbidden") or cand.get("exact_target_excluded"):
        score -= 10
    return {
        "row_id": row.get("row_id"),
        "candidate_name": cand.get("name"),
        "candidate_kind": cand.get("kind"),
        "family": family,
        "score": score,
        "seed_residual_row": seed_match,
        "keyword_hits": hits,
        "target_context_ready_count": target_ready_count,
        "source_safety_status": cand.get("source_safety_status"),
        "source_order_status": cand.get("source_order_status"),
        "candidate_type_sample": str(cand.get("type") or cand.get("signature") or "")[:300],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    packet = _read_json(args.source_packet)
    row_context = _read_json(args.row_context_filter)
    residual_plan = _read_json(args.residual_plan)
    ready_by_row = _row_context_ready(row_context)
    ready_names_by_row = _row_context_ready_names(row_context)
    seeds_by_family = _seed_rows(residual_plan)
    family_leads: dict[str, list[dict[str, Any]]] = {name: [] for name in FAMILY_PROFILES}
    family_rows: dict[str, set[str]] = {name: set() for name in FAMILY_PROFILES}
    for row in packet.get("rows") or []:
        rid = str(row.get("row_id") or "")
        ready_count = ready_by_row.get(rid, 0)
        for cand in row.get("usable_candidates") or []:
            cname = str(cand.get("name") or "")
            ready_names = ready_names_by_row.get(rid) or set()
            if ready_names and cname not in ready_names:
                continue
            for family, profile in FAMILY_PROFILES.items():
                lead = _score_candidate(family, profile, row, cand, ready_count, seeds_by_family.get(family, set()))
                if lead["score"] >= args.min_score and (lead["keyword_hits"] or lead["seed_residual_row"]):
                    family_leads[family].append(lead)
                    family_rows[family].add(rid)
    packets: list[dict[str, Any]] = []
    for family, leads in family_leads.items():
        leads = sorted(leads, key=lambda x: (-int(x["score"]), str(x["row_id"]), str(x["candidate_name"])))
        profile = FAMILY_PROFILES[family]
        packets.append({
            "repair_family": family,
            "lead_count": len(leads),
            "row_count": len(family_rows[family]),
            "rows": sorted(family_rows[family]),
            "seed_rows": sorted(seeds_by_family.get(family, set())),
            "seed_rows_with_leads": sorted(family_rows[family] & seeds_by_family.get(family, set())),
            "top_leads": leads[: args.top_leads],
            "actions": profile["actions"],
            "negative_controls": profile["negative_controls"],
            "next_action": (
                "build family-specific canary packet"
                if leads else "do not spend Path A; source more targeted candidates"
            ),
        })
    reason_counts = Counter()
    for packet_row in packets:
        if not packet_row["lead_count"]:
            reason_counts["no_family_matching_leads"] += 1
    payload = {
        "schema": "leansearch-residual-family-source-plan-v1",
        "source_packet": args.source_packet,
        "row_context_filter": args.row_context_filter,
        "residual_plan": args.residual_plan,
        "min_score": args.min_score,
        "family_count": len(packets),
        "families_with_leads": sum(1 for p in packets if p["lead_count"]),
        "packets": packets,
        "summary": {
            "total_leads": sum(p["lead_count"] for p in packets),
            "top_family": max(packets, key=lambda p: p["lead_count"])["repair_family"] if packets else None,
            "empty_family_count": reason_counts["no_family_matching_leads"],
        },
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.canary_out:
        canary = _build_canary_packets(payload, args.max_canary_rows, args.max_canary_leads)
        Path(args.canary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.canary_out).write_text(json.dumps(canary, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        _write_md(payload, Path(args.markdown))
    return payload


def _build_canary_packets(plan: dict[str, Any], max_rows: int, max_leads: int) -> dict[str, Any]:
    packets = []
    for family in plan.get("packets") or []:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for lead in family.get("top_leads") or []:
            rid = str(lead.get("row_id") or "")
            if not rid:
                continue
            grouped.setdefault(rid, [])
            if len(grouped[rid]) < max_leads:
                grouped[rid].append(lead)
        selected_rows = []
        for rid, leads in list(grouped.items())[:max_rows]:
            selected_rows.append({
                "row_id": rid,
                "candidate_names": [str(l.get("candidate_name")) for l in leads],
                "lead_scores": [int(l.get("score") or 0) for l in leads],
                "expected_action_profile": family.get("actions") or [],
                "required_negative_controls": family.get("negative_controls") or [],
            })
        packets.append({
            "repair_family": family.get("repair_family"),
            "state": "ready_for_canary_build" if selected_rows else "needs_sources",
            "row_count": len(selected_rows),
            "lead_count": sum(len(row["candidate_names"]) for row in selected_rows),
            "selected_rows": selected_rows,
            "science_rule": "Canary packets are work-in-process only; value credit requires compile plus governance ratification or exact-gap/falsifier adjudication.",
        })
    return {
        "schema": "leanmill-residual-family-canary-packets-v1",
        "source_plan": plan.get("source_packet"),
        "row_context_filter": plan.get("row_context_filter"),
        "packet_count": len(packets),
        "ready_packet_count": sum(1 for p in packets if p["state"] == "ready_for_canary_build"),
        "packets": packets,
    }


def _write_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Residual-Family Source Plan",
        "",
        f"Families with leads: `{payload['families_with_leads']}/{payload['family_count']}`",
        f"Total leads: `{payload['summary']['total_leads']}`",
        "",
        "| Family | Rows | Leads | Next Action |",
        "|---|---:|---:|---|",
    ]
    for p in payload["packets"]:
        lines.append(f"| `{p['repair_family']}` | {p['row_count']} | {p['lead_count']} | {p['next_action']} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source.json"
        context = root / "context.json"
        source.write_text(json.dumps({"rows": [{
            "row_id": "r",
            "theorem": "convolution_test",
            "query": "convolution integral",
            "usable_candidates": [{
                "name": "MeasureTheory.integral_conv",
                "kind": "theorem",
                "type": "convolution integral theorem",
                "source_safety_status": "non_target_external_module_candidate",
            }],
        }]}))
        context.write_text(json.dumps({"rows": [{"row_id": "r", "row_context_resolved_count": 1}]}))
        obj = build(argparse.Namespace(
            source_packet=str(source),
            row_context_filter=str(context),
            residual_plan=None,
            min_score=1,
            top_leads=5,
            out=None,
            markdown=None,
            canary_out=None,
            max_canary_rows=2,
            max_canary_leads=2,
        ))
        conv = next(p for p in obj["packets"] if p["repair_family"] == "convolution_argument_planner")
        assert conv["lead_count"] == 1, obj
        assert conv["top_leads"][0]["score"] > 0, obj
        canary = _build_canary_packets(obj, 2, 2)
        assert canary["ready_packet_count"] >= 1, canary
        context.write_text(json.dumps({"rows": [{
            "row_id": "r",
            "row_context_resolved_count": 1,
            "row_context_ready_candidates": [{"name": "Other.name"}],
        }]}))
        obj = build(argparse.Namespace(
            source_packet=str(source),
            row_context_filter=str(context),
            residual_plan=None,
            min_score=1,
            top_leads=5,
            out=None,
            markdown=None,
            canary_out=None,
            max_canary_rows=2,
            max_canary_leads=2,
        ))
        conv = next(p for p in obj["packets"] if p["repair_family"] == "convolution_argument_planner")
        assert conv["lead_count"] == 0, obj
    print("leansearch_residual_family_source_planner self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-packet", default=DEFAULT_SOURCE_PACKET)
    ap.add_argument("--row-context-filter", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--residual-plan", default=DEFAULT_RESIDUAL_PLAN)
    ap.add_argument("--min-score", type=int, default=12)
    ap.add_argument("--top-leads", type=int, default=8)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--canary-out", default=DEFAULT_CANARY_OUT)
    ap.add_argument("--max-canary-rows", type=int, default=3)
    ap.add_argument("--max-canary-leads", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(args)
    print(json.dumps({
        "families_with_leads": obj["families_with_leads"],
        "total_leads": obj["summary"]["total_leads"],
        "top_family": obj["summary"]["top_family"],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
