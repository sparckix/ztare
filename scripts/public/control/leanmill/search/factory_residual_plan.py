#!/usr/bin/env python3
"""Turn Path-C factory residuals into repair-lane work packets.

This is the first scaling layer above the raw residual stream. It does not
prove anything and it does not run Lean. It clusters residual tails into
actionable next-template families so Path C becomes a compiler from failures
to reusable repair work instead of a pile of bespoke errors.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _lanes(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "events" / "path_c_residuals.jsonl").exists())


def _classify(rec: dict[str, Any]) -> tuple[str, str]:
    lane = str(rec.get("lane") or "")
    tail = str(rec.get("sample_tail") or "").lower()
    row_id = str(rec.get("row_id") or "")
    residual_class = str(rec.get("residual_class") or "")
    blob = f"{lane} {row_id} {tail}"
    if "ioc" in blob or "ioo" in blob or "inv_sq" in blob:
        return (
            "interval_alignment_planner",
            "build interval transport templates from Ioo to Ioc plus monotone bound weakening before applying inverse-square sum lemmas",
        )
    if residual_class == "source_action_mismatch" or "could not unify" in blob:
        if "mellin" in blob or "fourier" in blob:
            return (
                "mellin_fourier_shape_planner",
                "build transform-specific shape bridges before applying Fourier/Mellin lemmas; direct apply is a source-action mismatch",
            )
        if "rpow" in blob or "zpow" in blob:
            return (
                "rpow_inequality_shape_planner",
                "instantiate exponent/positivity side conditions and normalize algebraic goal shape before applying rpow inequalities",
            )
        if "rayleigh" in blob or "spectrum" in blob or "eigen" in blob or "possemidef" in blob:
            return (
                "spectral_rayleigh_shape_planner",
                "align operator/spectrum/Rayleigh quotient hypotheses before applying spectral source lemmas",
            )
        if "constantSpeedOnWith".lower() in blob or "lipschitz" in blob:
            return (
                "metric_speed_shape_planner",
                "split iff/zero-speed cases and align Lipschitz/constant-speed carriers before applying source lemmas",
            )
        return (
            "source_action_shape_planner",
            "candidate source resolves but does not match the target head; add a source-shape adapter or rerank by kernel goal delta",
        )
    if residual_class == "unknown_identifier" or "unknown constant" in blob or "unknown identifier" in blob:
        return (
            "target_context_import_or_name_planner",
            "repair source qualification: candidate resolved upstream but is unavailable under the exact target context",
        )
    if residual_class == "repl_step_context_gap":
        return (
            "backend_context_fallback_planner",
            "the fast REPL-step backend could not see context visible to full-file Lean; rerun same-file repair lanes with file backend before treating as a mathematical residual",
        )
    if residual_class == "syntax_or_template_bug":
        return (
            "action_template_bug_planner",
            "fix generated Lean template syntax before spending more proof-execution budget",
        )
    if residual_class == "directional_iff_gap":
        return (
            "iff_direction_planner",
            "split iff/directional targets explicitly and route each direction to a source-shaped subtemplate",
        )
    if "convolution" in blob or "conv_" in blob or "⋆" in blob:
        return (
            "convolution_argument_planner",
            "build convolution-specific templates that instantiate measure/invariance hypotheses and rewrite to the target convolution operator before applying source lemmas",
        )
    if "oscillation" in blob or "continuouswithin" in blob or "continuousat" in blob:
        return (
            "continuity_oscillation_planner",
            "choose the exact continuity/oscillation equivalence direction and normalize nhdsWithin/set hypotheses before applying source lemmas",
        )
    if "openpartialhomeomorph" in blob:
        return (
            "partial_homeomorph_planner",
            "align source/target partial-homeomorphism domains and continuity fields before applying structural lemmas",
        )
    if "orientation" in blob or "areaform" in blob or "kahler" in blob:
        return (
            "orientation_areaform_planner",
            "normalize orientation/area-form map arguments before applying areaForm or volumeForm lemmas",
        )
    if "islocalextr" in blob or "multipliers" in blob or "linear_dependent" in blob:
        return (
            "local_extrema_planner",
            "instantiate local-extrema differentiability and multiplier hypotheses before applying source theorems",
        )
    if "tendsto" in blob or "lim_" in blob or "_lim" in blob:
        return (
            "limit_tendsto_planner",
            "normalize filter/limit hypotheses before applying asymptotic source lemmas",
        )
    if "ennreal" in blob or "tsum" in blob or "∑'" in blob:
        return (
            "ennreal_tsum_condensation_planner",
            "build ENNReal tsum inequality templates; do not apply coe_tsum directly unless the goal has an NNReal coercion shape",
        )
    if "geom_mean" in blob or "iff" in blob:
        return (
            "iff_direction_planner",
            "split iff/directional targets explicitly and route each direction to a source-shaped subtemplate",
        )
    if "summable" in blob or "nnreal" in blob:
        return (
            "nnreal_real_transport_planner",
            "build coercion/transport templates between NNReal and Real using nonnegativity hypotheses",
        )
    if "timeout" in blob:
        return (
            "budget_or_decomposition_planner",
            "separate timeout from semantic failure; reduce candidate breadth or decompose before rerun",
        )
    return (
        "generic_residual_triage",
        "inspect residual tail and promote only if it recurs across rows or exposes a formal missing lemma",
    )


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    rows: list[dict[str, Any]] = []
    for lane in args.lane or _lanes(root):
        rows.extend(_read_jsonl(root / lane / "events" / "path_c_residuals.jsonl"))
    clusters: dict[str, dict[str, Any]] = {}
    for rec in rows:
        family, next_action = _classify(rec)
        if family not in clusters:
            clusters[family] = {
                "repair_family": family,
                "next_action": next_action,
                "rows": [],
                "lanes": Counter(),
                "residual_classes": Counter(),
                "evidence_tails": [],
            }
        c = clusters[family]
        c["rows"].append(str(rec.get("row_id") or ""))
        c["lanes"][str(rec.get("lane") or "unknown")] += 1
        c["residual_classes"][str(rec.get("residual_class") or "unknown")] += 1
        if len(c["evidence_tails"]) < args.max_tails:
            c["evidence_tails"].append(str(rec.get("sample_tail") or "")[-args.tail_chars:])

    packets = []
    for family, c in sorted(clusters.items()):
        lanes = dict(c.pop("lanes"))
        residual_classes = dict(c.pop("residual_classes"))
        rows_unique = sorted(set(c["rows"]))
        priority = len(rows_unique)
        if family != "generic_residual_triage":
            priority += 2
        packets.append({
            **c,
            "rows": rows_unique,
            "row_count": len(rows_unique),
            "lanes": lanes,
            "residual_classes": residual_classes,
            "priority": priority,
            "scale_decision": "promote_to_repair_lane" if priority >= args.promote_threshold else "hold_for_more_evidence",
        })
    packets.sort(key=lambda p: (-int(p["priority"]), str(p["repair_family"])))
    payload = {
        "schema": "leansearch-factory-residual-plan-v1",
        "root": str(root),
        "residual_events": len(rows),
        "cluster_count": len(packets),
        "packets": packets,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    rec = {
        "lane": "interval_inv_sq_sum",
        "row_id": "r",
        "sample_tail": "could not unify Ioc with goal Ioo",
    }
    assert _classify(rec)[0] == "interval_alignment_planner"
    assert _classify({"lane": "mellin_fourier_transport", "residual_class": "source_action_mismatch", "sample_tail": "could not unify Fourier"})[0] == "mellin_fourier_shape_planner"
    assert _classify({"lane": "limit_tendsto_transport", "residual_class": "unknown_identifier", "sample_tail": "Unknown constant Subadditive"})[0] == "target_context_import_or_name_planner"
    assert _classify({"lane": "summability_transport", "residual_class": "repl_step_context_gap", "sample_tail": ""})[0] == "backend_context_fallback_planner"
    assert _classify({"lane": "continuity_oscillation_transport", "sample_tail": "oscillationWithin_eq_zero"})[0] == "continuity_oscillation_planner"
    print("leansearch_factory_residual_plan self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/tmp/rung1/leansearch_factory_mill")
    ap.add_argument("--lane", action="append")
    ap.add_argument("--out")
    ap.add_argument("--promote-threshold", type=int, default=3)
    ap.add_argument("--max-tails", type=int, default=3)
    ap.add_argument("--tail-chars", type=int, default=700)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(build_plan(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
