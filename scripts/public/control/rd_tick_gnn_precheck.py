#!/usr/bin/env python3
"""GNN advisory precheck for Research Director ticks.

This is a frozen-artifact consumer, not a trainer.  Its job is to make the
lemma-ranker/GNN lane visible at tick start while preserving the v2-v5 lesson:
do not promote architecture changes from one attractive local slice.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DEFAULT_PACKET = (
    REPO / "analytics/public/leanmill/results/v52_ns_advisory_packet.json"
)
DEFAULT_REMOTE_CPU = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v52_residual_hetero_gnn_remote_cpu_sanity.json"
)
DEFAULT_GRAPH = (
    REPO
    / "projects/ns_millennium_hunt/workspace/queries/"
    "ns_l3a_same_tree_obligation_graph.json"
)
DEFAULT_V53 = (
    REPO / "analytics/public/leanmill/results/v53_guarded_advisory_filter.json"
)
DEFAULT_V54 = (
    REPO / "analytics/public/leanmill/results/v54_typed_symmetry_audit.json"
)
DEFAULT_V55 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v55_typed_symmetry_perturbation_canary.json"
)
DEFAULT_V54_REPAIRED = (
    REPO / "analytics/public/leanmill/results/v54_on_v56_top7_typed_symmetry_audit.json"
)
DEFAULT_V55_REPAIRED = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v55_on_v56_top7_typed_symmetry_perturbation_canary.json"
)
DEFAULT_V56 = (
    REPO / "analytics/public/leanmill/results/v56_typed_role_repaired_queue.json"
)
DEFAULT_V57 = (
    REPO / "analytics/public/leanmill/results/v57_patch_attribution_seed.json"
)
DEFAULT_V60 = (
    REPO / "analytics/public/leanmill/results/v60_typed_symmetry_residual_contract.json"
)
DEFAULT_V61 = (
    REPO / "analytics/public/leanmill/results/v61_typed_obligation_hypergraph_contract.json"
)
DEFAULT_V62 = (
    REPO / "analytics/public/leanmill/results/v62_ns_typed_obligation_work_packet.json"
)
DEFAULT_V64 = (
    REPO / "analytics/public/leanmill/results/v64_tri_arm_usefulness_pilot.json"
)
DEFAULT_V65 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v65_gnn_graph_combo_beta_payment_patch_attribution.json"
)
DEFAULT_V66 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v66_gnn_graph_combo_structured_lock_patch_attribution.json"
)
DEFAULT_V67 = (
    REPO / "analytics/public/leanmill/results/v67_gnn_roadmap.json"
)
DEFAULT_V67_HARNESS = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v67_endpoint_occluded_attribution_harness.json"
)
DEFAULT_V68 = (
    REPO / "analytics/public/leanmill/results/v68_non_ns_role_map_canary.json"
)
DEFAULT_V69 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v69_non_ns_real_lean_attribution_canary.json"
)
DEFAULT_V70 = (
    REPO / "analytics/public/leanmill/results/v70_non_ns_generated_patch_attribution.json"
)
DEFAULT_V71 = (
    REPO / "analytics/public/leanmill/results/v71_external_benchmark_intake.json"
)
DEFAULT_V72 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v72_mathlibgraph_external_baseline_summary.json"
)
DEFAULT_V73 = (
    REPO / "analytics/public/leanmill/results/v73_scientific_yield_gate.json"
)
DEFAULT_V76 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v76_leanrank_gated_typed_residual_eval.json"
)
DEFAULT_V79 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v79_endpoint_occluded_repair_benchmark_seed.json"
)
DEFAULT_V80 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v80_leanrank_bm25_gated_eval.json"
)
DEFAULT_V81 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v81_repair_router_baseline_protocol.json"
)
DEFAULT_V82 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v82_actual_declaration_repair_pool_eval.json"
)
DEFAULT_V83 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v83_constrained_repair_queue_eval.json"
)
DEFAULT_V84 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v84_hybrid_repair_router_eval.json"
)
DEFAULT_V85 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v85_literature_positioning_audit.json"
)
DEFAULT_V86 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v86_gnn_graph_combo_pressure_duhamel_audit_patch_attribution.json"
)
DEFAULT_V87 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v87_non_ns_ortho_generated_patch_attribution.json"
)
DEFAULT_V89 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v89_non_ns_charmulconj_generated_patch_attribution.json"
)
DEFAULT_V91 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v91_ns_leray_heat_tent_geometry_patch_attribution.json"
)
DEFAULT_V88 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v88_repair_router_alias_stress.json"
)
DEFAULT_V90 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v90_repair_router_structural_occlusion_stress.json"
)
DEFAULT_V92 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v92_label_blind_hard_decoy_audit.json"
)
DEFAULT_V93 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v93_kernel_shape_feature_probe.json"
)
DEFAULT_V94 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v94_post_patch_dependency_attribution_probe.json"
)
DEFAULT_V95 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v95_lean_check_type_extractor.json"
)
DEFAULT_V96 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v96_lean_expr_ast_graph_extractor.json"
)
DEFAULT_V97 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v97_ast_graph_repair_backtest.json"
)
DEFAULT_V98 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v98_symbolic_expr_graph_repair_backtest.json"
)
DEFAULT_V99 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v99_typed_obligation_expr_graph.json"
)
DEFAULT_V100 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v100_neighborhood_similarity_graph_backtest.json"
)
DEFAULT_V101 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v101_ppr_typed_obligation_graph_backtest.json"
)
DEFAULT_V102 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v102_row_obligation_seeded_role_backtest.json"
)
DEFAULT_V103 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v103_nonbootstrap_interface_role_extractor.json"
)
DEFAULT_V104 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v104_action_delta_type_probe.json"
)
DEFAULT_V105 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v105_metavar_action_delta_probe.json"
)
DEFAULT_V106 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v106_antifailure_repair_router.json"
)
DEFAULT_V107 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v107_tactic_rewrite_delta_probe.json"
)
DEFAULT_V108 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v108_combined_action_delta_router.json"
)
DEFAULT_V109 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v109_tactic_failure_taxonomy_probe.json"
)
DEFAULT_V117 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v117_probe_budget_repair_bundle_harness.json"
)
DEFAULT_V118 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v118_expanded_tactic_action_probe.json"
)
DEFAULT_V119 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v119_expanded_action_bundle_router.json"
)
DEFAULT_V120 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v120_convert_selectivity_audit.json"
)
DEFAULT_V121 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v121_focused_proof_state_witness_probe.json"
)
DEFAULT_V123 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v123_full_goal_snapshot_witness_probe.json"
)
DEFAULT_V124 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v124_target_unit_audit.json"
)
DEFAULT_V125 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v125_target_unit_repair_packet.json"
)
DEFAULT_V126 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v126_full_target_unit_rewrite_packet.json"
)
DEFAULT_V127 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v127_target_aware_policy_eval.json"
)
DEFAULT_V128 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v128_policy_gap_decomposition.json"
)
DEFAULT_V129 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v129_compressed_affordance_policy_eval.json"
)
DEFAULT_V130 = (
    REPO
    / "analytics/public/leanmill/_legacy_lemma_relevance/"
    "v130_label_leakage_static_audit.json"
)
DEFAULT_PRIMITIVE_SURFACE = (
    REPO / "analytics/public/queries/rd_tick_primitive_surface.json"
)
DEFAULT_JSON = REPO / "analytics/public/queries/rd/rd_tick_gnn_precheck.json"
DEFAULT_MD = DEFAULT_JSON.with_suffix(".md")
V57_EMPTY_ATTRIBUTION_WARNING = (
    "v5.7 patch-attribution seed has no successful-edit attribution yet"
)


DANGER_NEEDLES = {
    "endpoint_or_carleson": ("Carleson", "Endpoint", "Final", "FINAL"),
    "event_per_node_tautology": ("EventPerBadNode", "PostHoc", "Tautological"),
    "opaque_bundle": ("FreshFrequencyEventSameTreeLock",),
    "guard_not_constructor": ("DoesNot", "Blocks", "Cannot", "Not", "Guard"),
}

PRIMITIVE_NEEDLES = (
    "FreshComparablePacket",
    "FreshPacket",
    "BoundedFanout",
    "SameCarrier",
    "PrefixDominationFromSubprimitives",
    "NonflatNonInherited",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def candidate_warnings(name: str) -> list[str]:
    warnings = []
    for label, needles in DANGER_NEEDLES.items():
        if any(needle in name for needle in needles):
            warnings.append(label)
    return warnings


def candidate_role(name: str) -> str:
    if any(needle in name for needle in PRIMITIVE_NEEDLES):
        return "primitive_or_adapter"
    if candidate_warnings(name):
        return "danger_or_guard"
    if ".of" in name or name.startswith("of"):
        return "constructor"
    return "context"


def summarize_packet(packet: dict, max_targets: int, top_k: int) -> dict:
    targets = packet.get("targets") or []
    rows = []
    danger = Counter()
    role_counts = Counter()
    candidate_counts = Counter()
    actionable_counts = Counter()
    danger_candidate_counts = Counter()
    known_used_ranked_first = 0
    known_used_any_topk = 0

    for target in targets[:max_targets]:
        known = set(target.get("known_used_lemmas") or [])
        top = target.get("top_candidates") or []
        top_names = [c.get("name", "") for c in top[:top_k]]
        if known and top_names and top_names[0] in known:
            known_used_ranked_first += 1
        if known and any(name in known for name in top_names):
            known_used_any_topk += 1
        candidates = []
        for cand in top[:top_k]:
            name = cand.get("name", "")
            warnings = candidate_warnings(name)
            for warning in warnings:
                danger[warning] += 1
            role = candidate_role(name)
            role_counts[role] += 1
            candidate_counts[name] += 1
            if role in {"primitive_or_adapter", "constructor"} and not warnings:
                actionable_counts[name] += 1
            if warnings:
                danger_candidate_counts[name] += 1
            candidates.append(
                {
                    "name": name,
                    "role": role,
                    "warnings": warnings,
                    "source": cand.get("source", ""),
                    "file": cand.get("file", ""),
                    "line": cand.get("line"),
                }
            )
        rows.append(
            {
                "target_name": target.get("target_name", ""),
                "source_file": target.get("source_file", ""),
                "split": target.get("split", ""),
                "known_used_topk_hit": bool(known and any(name in known for name in top_names)),
                "top_candidates": candidates,
            }
        )

    return {
        "targets_scanned": len(targets),
        "targets_emitted": len(rows),
        "known_used_ranked_first": known_used_ranked_first,
        "known_used_any_topk": known_used_any_topk,
        "danger_counts": dict(sorted(danger.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "top_candidate_names": [
            {"name": name, "count": count}
            for name, count in candidate_counts.most_common(20)
        ],
        "actionable_candidate_names": [
            {"name": name, "count": count}
            for name, count in actionable_counts.most_common(15)
        ],
        "danger_candidate_names": [
            {"name": name, "count": count}
            for name, count in danger_candidate_counts.most_common(15)
        ],
        "targets": rows,
    }


def summarize_graph(graph: dict) -> dict:
    nodes = graph.get("nodes") or []
    labels = [n.get("label", "") for n in nodes]
    atomic_nodes = [
        label
        for label in labels
        if label.startswith("FreshComparablePacket")
        or label.startswith("freshFrequencyEventSameTreeLockUsesDisplayedSubprimitives")
    ]
    return {
        "path": rel(DEFAULT_GRAPH),
        "status": graph.get("status"),
        "target": graph.get("target"),
        "missing_tags": graph.get("missing_tags") or [],
        "thin_tags": graph.get("thin_tags") or [],
        "atomic_nodes_detected": atomic_nodes,
    }


def build_precheck(args: argparse.Namespace) -> tuple[int, dict]:
    warnings = []
    errors = []
    scope = (args.scope or "").strip().lower()
    if scope and not any(
        token in scope
        for token in ("all", "global", "ns", "navier", "stokes", "lean", "math")
    ):
        return 0, {
            "version": "rd_tick_gnn_precheck_v1_2026_05_11",
            "status": "skipped_scope",
            "scope": scope,
            "warnings": [f"no registered GNN advisory precheck for scope `{args.scope}`"],
            "errors": [],
        }

    if not args.packet.exists():
        return 1, {
            "status": "fail_missing_packet",
            "errors": [f"missing packet: {rel(args.packet)}"],
        }
    packet = load_json(args.packet)
    packet_summary = summarize_packet(packet, args.max_targets, args.top_k)

    remote_cpu = None
    if args.remote_cpu.exists():
        remote_cpu = load_json(args.remote_cpu)
    else:
        warnings.append(f"missing optional remote CPU sanity: {rel(args.remote_cpu)}")

    graph_summary = None
    if args.graph.exists():
        graph_summary = summarize_graph(load_json(args.graph))
        if graph_summary["missing_tags"] or graph_summary["thin_tags"]:
            warnings.append("same-tree graph has missing/thin tags")
    else:
        warnings.append(f"missing optional obligation graph: {rel(args.graph)}")

    best_val = float(packet.get("best_val_hit10") or 0.0)
    if best_val < args.min_best_val_hit10:
        warnings.append(
            f"packet best_val_hit10 {best_val:.4f} below advisory floor "
            f"{args.min_best_val_hit10:.4f}"
        )

    if packet_summary["danger_counts"]:
        warnings.append("top candidates include endpoint/guard/tautology danger terms")

    v53 = None
    if DEFAULT_V53.exists():
        v53 = load_json(DEFAULT_V53)
    else:
        warnings.append(f"missing optional v5.3 guarded filter: {rel(DEFAULT_V53)}")

    v54 = None
    if DEFAULT_V54.exists():
        v54 = load_json(DEFAULT_V54)
        if v54.get("status") != "pass_typed_symmetry_audit":
            warnings.append("v5.4 typed-symmetry audit has missing roles or collapse risks")
    else:
        warnings.append(f"missing optional v5.4 typed-symmetry audit: {rel(DEFAULT_V54)}")

    v55 = None
    if DEFAULT_V55.exists():
        v55 = load_json(DEFAULT_V55)
        if v55.get("status") != "pass_typed_symmetry_canary":
            warnings.append("v5.5 typed-symmetry canary indicates alias brittleness")
    else:
        warnings.append(f"missing optional v5.5 typed-symmetry canary: {rel(DEFAULT_V55)}")

    v54_repaired = None
    if DEFAULT_V54_REPAIRED.exists():
        v54_repaired = load_json(DEFAULT_V54_REPAIRED)
        if v54_repaired.get("status") != "pass_typed_symmetry_audit":
            warnings.append("v5.6 repaired queue still fails typed-symmetry audit")
    else:
        warnings.append(f"missing optional repaired v5.4 audit: {rel(DEFAULT_V54_REPAIRED)}")

    v55_repaired = None
    if DEFAULT_V55_REPAIRED.exists():
        v55_repaired = load_json(DEFAULT_V55_REPAIRED)
    else:
        warnings.append(f"missing optional repaired v5.5 canary: {rel(DEFAULT_V55_REPAIRED)}")

    v56 = None
    if DEFAULT_V56.exists():
        v56 = load_json(DEFAULT_V56)
    else:
        warnings.append(f"missing optional v5.6 typed-role repair queue: {rel(DEFAULT_V56)}")

    v57 = None
    if DEFAULT_V57.exists():
        v57 = load_json(DEFAULT_V57)
        if not any((row.get("used_in_successful_edit") is True) for row in (v57.get("rows") or [])):
            warnings.append(V57_EMPTY_ATTRIBUTION_WARNING)
    else:
        warnings.append(f"missing optional v5.7 patch-attribution seed: {rel(DEFAULT_V57)}")

    v60 = None
    if DEFAULT_V60.exists():
        v60 = load_json(DEFAULT_V60)
        decision = (v60.get("architecture_decision") or {})
        if decision.get("generic_e3_equivariant_gnn") == "blocked":
            warnings.append("v6 contract blocks generic E3/CFD equivariant GNN for theorem search")
        if not str(decision.get("typed_symmetry_residual") or "").startswith("design_eligible"):
            warnings.append("v6 typed-symmetry residual contract is not design eligible")
    else:
        warnings.append(f"missing optional v6 typed-symmetry residual contract: {rel(DEFAULT_V60)}")

    v61 = None
    if DEFAULT_V61.exists():
        v61 = load_json(DEFAULT_V61)
        readiness = v61.get("current_readiness") or {}
        if readiness.get("training_allowed") is False:
            warnings.append("v6.1 typed-obligation hypergraph contract is ready for design only, not training")
    else:
        warnings.append(f"missing optional v6.1 typed-obligation hypergraph contract: {rel(DEFAULT_V61)}")

    v62 = None
    if DEFAULT_V62.exists():
        v62 = load_json(DEFAULT_V62)
        if v62.get("training_allowed") is False:
            warnings.append("v6.2 typed-obligation work packet is advisory only")
    else:
        warnings.append(f"missing optional v6.2 typed-obligation work packet: {rel(DEFAULT_V62)}")

    v64 = None
    if DEFAULT_V64.exists():
        v64 = load_json(DEFAULT_V64)
    else:
        warnings.append(f"missing optional v6.4 tri-arm usefulness pilot: {rel(DEFAULT_V64)}")

    patch_attributions = []
    for path in (
        REPO / "analytics/public/leanmill/results/v63_gnn_graph_combo_patch_attribution.json",
        DEFAULT_V65,
        DEFAULT_V66,
        DEFAULT_V70,
        DEFAULT_V86,
        DEFAULT_V87,
        DEFAULT_V89,
        DEFAULT_V91,
    ):
        if path.exists():
            data = load_json(path)
            patch_attributions.append(
                {
                    "path": rel(path),
                    "status": data.get("status"),
                    "compile_checked": (
                        (data.get("ex_post_usefulness") or {}).get("compile_checked")
                        is True
                    ),
                    "added_declarations": (data.get("patch") or {}).get("added_declarations") or [],
                }
            )
        else:
            warnings.append(f"missing optional patch attribution: {rel(path)}")
    if any(row.get("compile_checked") for row in patch_attributions):
        warnings = [w for w in warnings if w != V57_EMPTY_ATTRIBUTION_WARNING]

    v67 = None
    if DEFAULT_V67.exists():
        v67 = load_json(DEFAULT_V67)
    else:
        warnings.append(f"missing optional v6.7/v7 roadmap: {rel(DEFAULT_V67)}")

    v67_harness = None
    if DEFAULT_V67_HARNESS.exists():
        v67_harness = load_json(DEFAULT_V67_HARNESS)
    else:
        warnings.append(f"missing optional v6.7 endpoint-occluded harness: {rel(DEFAULT_V67_HARNESS)}")

    v68 = None
    if DEFAULT_V68.exists():
        v68 = load_json(DEFAULT_V68)
    else:
        warnings.append(f"missing optional v6.8 non-NS role-map canary: {rel(DEFAULT_V68)}")

    v69 = None
    if DEFAULT_V69.exists():
        v69 = load_json(DEFAULT_V69)
    else:
        warnings.append(f"missing optional v6.9 real non-NS Lean attribution canary: {rel(DEFAULT_V69)}")

    v70 = None
    if DEFAULT_V70.exists():
        v70 = load_json(DEFAULT_V70)
    else:
        warnings.append(f"missing optional v7.0 non-NS generated patch attribution: {rel(DEFAULT_V70)}")

    v71 = None
    if DEFAULT_V71.exists():
        v71 = load_json(DEFAULT_V71)
    else:
        warnings.append(f"missing optional v7.1 external benchmark intake: {rel(DEFAULT_V71)}")

    v72 = None
    if DEFAULT_V72.exists():
        v72 = load_json(DEFAULT_V72)
    else:
        warnings.append(f"missing optional v7.2 MathlibGraph baseline summary: {rel(DEFAULT_V72)}")

    v73 = None
    if DEFAULT_V73.exists():
        v73 = load_json(DEFAULT_V73)
    else:
        warnings.append(f"missing optional v7.3 scientific-yield gate: {rel(DEFAULT_V73)}")

    v76 = None
    if DEFAULT_V76.exists():
        v76 = load_json(DEFAULT_V76)
    else:
        warnings.append(f"missing optional v7.6 LeanRank gated residual eval: {rel(DEFAULT_V76)}")

    v79 = None
    if DEFAULT_V79.exists():
        v79 = load_json(DEFAULT_V79)
    else:
        warnings.append(f"missing optional v7.9 repair benchmark seed: {rel(DEFAULT_V79)}")

    v80 = None
    if DEFAULT_V80.exists():
        v80 = load_json(DEFAULT_V80)
    else:
        warnings.append(f"missing optional v8.0 LeanRank BM25 gated eval: {rel(DEFAULT_V80)}")

    v81 = None
    if DEFAULT_V81.exists():
        v81 = load_json(DEFAULT_V81)
        if v81.get("status") == "protocol_debug_complete_not_evidence":
            warnings.append("v8.1 repair-router protocol is mechanics-only; do not treat as evidence")
    else:
        warnings.append(f"missing optional v8.1 repair-router protocol: {rel(DEFAULT_V81)}")

    v82 = None
    if DEFAULT_V82.exists():
        v82 = load_json(DEFAULT_V82)
        if v82.get("status") == "actual_declaration_pool_proxy_not_training_evidence":
            warnings.append("v8.2 actual-declaration repair pool is proxy evidence only")
    else:
        warnings.append(f"missing optional v8.2 actual-declaration repair pool: {rel(DEFAULT_V82)}")

    v83 = None
    if DEFAULT_V83.exists():
        v83 = load_json(DEFAULT_V83)
        if v83.get("status") == "constrained_repair_queue_proxy_not_training_evidence":
            warnings.append("v8.3 constrained repair queue is proxy evidence only")
    else:
        warnings.append(f"missing optional v8.3 constrained repair queue: {rel(DEFAULT_V83)}")

    v84 = None
    if DEFAULT_V84.exists():
        v84 = load_json(DEFAULT_V84)
        if v84.get("status") == "hybrid_repair_router_proxy_not_training_evidence":
            warnings.append("v8.4 hybrid repair router is proxy evidence only")
    else:
        warnings.append(f"missing optional v8.4 hybrid repair router: {rel(DEFAULT_V84)}")

    v85 = None
    if DEFAULT_V85.exists():
        v85 = load_json(DEFAULT_V85)
    else:
        warnings.append(f"missing optional v8.5 literature positioning audit: {rel(DEFAULT_V85)}")

    v88 = None
    if DEFAULT_V88.exists():
        v88 = load_json(DEFAULT_V88)
        metrics = v88.get("metrics") or {}
        if (metrics.get("semantic_alias_hit_at_7") or 0) < 0.9:
            warnings.append("v8.8 repair-router semantic-alias stress is below robustness gate")
        if (metrics.get("name_anonymized_hit_at_7") or 0) < 0.9:
            warnings.append("v8.8 repair-router name-anonymization stress is below robustness gate")
    else:
        warnings.append(f"missing optional v8.8 repair-router alias stress: {rel(DEFAULT_V88)}")

    v90 = None
    if DEFAULT_V90.exists():
        v90 = load_json(DEFAULT_V90)
        metrics = v90.get("metrics") or {}
        if (metrics.get("signature_names_erased_hit_at_7") or 0) < 0.9:
            warnings.append("v9.0 structural occlusion stress is below robustness gate")
        if (metrics.get("role_token_alias_signature_hit_at_7") or 0) < 0.9:
            warnings.append("v9.0 role-token alias signature stress is below robustness gate")
    else:
        warnings.append(f"missing optional v9.0 structural occlusion stress: {rel(DEFAULT_V90)}")

    v92 = None
    if DEFAULT_V92.exists():
        v92 = load_json(DEFAULT_V92)
        static = v92.get("static_label_blind_check") or {}
        if not static.get("passes"):
            warnings.append("v9.2 label-blind static check failed")
        metrics = v92.get("metrics") or {}
        if not metrics.get("all_pools_gt_7"):
            warnings.append("v9.2 hard-decoy pools are too small for hit@7")
    else:
        warnings.append(f"missing optional v9.2 label-blind hard-decoy audit: {rel(DEFAULT_V92)}")

    v93 = None
    if DEFAULT_V93.exists():
        v93 = load_json(DEFAULT_V93)
        metrics = v93.get("metrics") or {}
        if (metrics.get("shape_hit_at_7") or 0) <= (metrics.get("lexical_hit_at_7") or 0):
            warnings.append("v9.3 kernel-shape proxy does not beat lexical")
    else:
        warnings.append(f"missing optional v9.3 kernel-shape feature probe: {rel(DEFAULT_V93)}")

    v94 = None
    if DEFAULT_V94.exists():
        v94 = load_json(DEFAULT_V94)
        metrics = v94.get("metrics") or {}
        if (metrics.get("dependency_hit_at_7") or 0) < 0.75:
            warnings.append("v9.4 post-patch dependency proxy is weak")
    else:
        warnings.append(f"missing optional v9.4 dependency attribution probe: {rel(DEFAULT_V94)}")

    v95 = None
    if DEFAULT_V95.exists():
        v95 = load_json(DEFAULT_V95)
        if v95.get("rows_resolved") != v95.get("row_count"):
            warnings.append("v9.5 Lean environment type extraction did not resolve every row")
    else:
        warnings.append(f"missing optional v9.5 Lean environment type extractor: {rel(DEFAULT_V95)}")

    v96 = None
    if DEFAULT_V96.exists():
        v96 = load_json(DEFAULT_V96)
        if v96.get("resolved_candidate_count") != v96.get("candidate_count"):
            warnings.append("v9.6 Lean Expr AST graph did not resolve every candidate")
    else:
        warnings.append(f"missing optional v9.6 Lean Expr AST graph extractor: {rel(DEFAULT_V96)}")

    v97 = None
    if DEFAULT_V97.exists():
        v97 = load_json(DEFAULT_V97)
        metrics = v97.get("metrics") or {}
        if (metrics.get("ast_shape_hit_at_7") or 0) < 0.75:
            warnings.append("v9.7 name-erased AST-shape signal is below router gate")
    else:
        warnings.append(f"missing optional v9.7 AST graph repair backtest: {rel(DEFAULT_V97)}")

    v98 = None
    if DEFAULT_V98.exists():
        v98 = load_json(DEFAULT_V98)
        redacted = ((v98.get("modes") or {}).get("local_redacted_const") or {})
        if (redacted.get("hit_at_7") or 0) < 0.75:
            warnings.append("v9.8 local-redacted symbolic Expr graph signal is below router gate")
    else:
        warnings.append(f"missing optional v9.8 symbolic Expr graph backtest: {rel(DEFAULT_V98)}")

    v99 = None
    if DEFAULT_V99.exists():
        v99 = load_json(DEFAULT_V99)
        edge_counts = v99.get("edge_kind_counts") or {}
        if not edge_counts.get("candidate_pool_member"):
            warnings.append("v9.9 typed-obligation Expr graph has no row/candidate edges")
    else:
        warnings.append(f"missing optional v9.9 typed-obligation Expr graph: {rel(DEFAULT_V99)}")

    v100 = None
    if DEFAULT_V100.exists():
        v100 = load_json(DEFAULT_V100)
        non_name = ((v100.get("modes") or {}).get("non_name") or {})
        role = ((v100.get("modes") or {}).get("role") or {})
        if (non_name.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.0 non-name typed-neighborhood Jaccard is below router gate")
        if (role.get("hit_at_7") or 0) > (non_name.get("hit_at_7") or 0):
            warnings.append("v10.0 role-neighborhood Jaccard depends on bootstrap role edges")
    else:
        warnings.append(f"missing optional v10.0 typed-neighborhood similarity backtest: {rel(DEFAULT_V100)}")

    v101 = None
    if DEFAULT_V101.exists():
        v101 = load_json(DEFAULT_V101)
        combined = ((v101.get("modes") or {}).get("combined") or {})
        if (combined.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.1 PPR graph baseline is below router gate")
    else:
        warnings.append(f"missing optional v10.1 PPR typed-obligation graph backtest: {rel(DEFAULT_V101)}")

    v102 = None
    if DEFAULT_V102.exists():
        v102 = load_json(DEFAULT_V102)
        metrics = v102.get("metrics") or {}
        if (metrics.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.2 row-obligation seeded role matching is below router gate")
    else:
        warnings.append(f"missing optional v10.2 row-obligation seeded role backtest: {rel(DEFAULT_V102)}")

    v103 = None
    if DEFAULT_V103.exists():
        v103 = load_json(DEFAULT_V103)
        metrics = v103.get("metrics") or {}
        if (metrics.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.3 non-bootstrap static interface roles are below router gate")
    else:
        warnings.append(f"missing optional v10.3 non-bootstrap interface role extractor: {rel(DEFAULT_V103)}")

    v104 = None
    if DEFAULT_V104.exists():
        v104 = load_json(DEFAULT_V104)
        metrics = v104.get("metrics") or {}
        contract = v104.get("contract") or {}
        if (metrics.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.4 Lean action-delta type probe is below router gate")
        if not contract.get("candidate_equals_target_self_matches_excluded"):
            warnings.append("v10.4 action-delta probe does not exclude self-target tautologies")
        if not contract.get("lean_environment_probe"):
            warnings.append("v10.4 action-delta probe is missing Lean-side evidence")
    else:
        warnings.append(f"missing optional v10.4 action-delta type probe: {rel(DEFAULT_V104)}")

    v105 = None
    if DEFAULT_V105.exists():
        v105 = load_json(DEFAULT_V105)
        metrics = v105.get("metrics") or {}
        if (metrics.get("emitted_probe_count") or 0) == 0:
            warnings.append("v10.5 metavariable action-delta probe emitted no probes")
        if (metrics.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.5 raw exact/apply action probe is below router gate")
    else:
        warnings.append(f"missing optional v10.5 metavariable action-delta probe: {rel(DEFAULT_V105)}")

    v106 = None
    if DEFAULT_V106.exists():
        v106 = load_json(DEFAULT_V106)
        metrics = v106.get("metrics") or {}
        action_only = metrics.get("action_only") or {}
        mixed = metrics.get("mixed_antifailure") or {}
        if (action_only.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.6 action-only anti-failure router is below gate")
        if (mixed.get("hit_at_7") or 0) < (action_only.get("hit_at_7") or 0):
            warnings.append("v10.6 mixed text-prior router underperforms action-only; treat text priors as overfit risk")
    else:
        warnings.append(f"missing optional v10.6 anti-failure repair router: {rel(DEFAULT_V106)}")

    v107 = None
    if DEFAULT_V107.exists():
        v107 = load_json(DEFAULT_V107)
        metrics = v107.get("metrics") or {}
        if (metrics.get("tactic_attempt_count") or 0) == 0:
            warnings.append("v10.7 tactic rewrite/simp probe emitted no tactic attempts")
        if (metrics.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.7 tactic rewrite/simp probe is below router gate")
        failure_counts = metrics.get("failure_class_counts") or {}
        if failure_counts.get("other_failure", 0) > failure_counts.get("no_occurrence", 0) * 10 + 100:
            warnings.append("v10.7 failure classifier is too coarse; split other_failure before training")
    else:
        warnings.append(f"missing optional v10.7 tactic rewrite delta probe: {rel(DEFAULT_V107)}")

    v108 = None
    if DEFAULT_V108.exists():
        v108 = load_json(DEFAULT_V108)
        metrics = v108.get("metrics") or {}
        setcover = metrics.get("setcover_tail") or {}
        v107_metrics = (v107.get("metrics") if v107 else {}) or {}
        if (setcover.get("hit_at_7") or 0) < 0.75:
            warnings.append("v10.8 combined action-delta router is below router gate")
        if (setcover.get("mrr") or 0) <= (v107_metrics.get("mrr") or 0):
            warnings.append("v10.8 combination does not beat v10.7 tactic-probe MRR; split failures before adding weights")
    else:
        warnings.append(f"missing optional v10.8 combined action-delta router: {rel(DEFAULT_V108)}")

    v109 = None
    if DEFAULT_V109.exists():
        v109 = load_json(DEFAULT_V109)
        metrics = v109.get("metrics") or {}
        if (metrics.get("tactic_attempt_count") or 0) == 0:
            warnings.append("v10.9 tactic failure-taxonomy probe emitted no tactic attempts")
        if metrics.get("other_failure_rate") is None or metrics.get("other_failure_rate") > 0.05:
            warnings.append("v10.9 failure taxonomy still leaves too much other_failure")
    else:
        warnings.append(f"missing optional v10.9 tactic failure taxonomy probe: {rel(DEFAULT_V109)}")

    v117 = None
    if DEFAULT_V117.exists():
        v117 = load_json(DEFAULT_V117)
        ceiling = v117.get("probe_inventory_ceiling") or {}
        if (ceiling.get("ceiling_bundle_success_rate") or 0) < 0.5:
            warnings.append("v11.7 old action inventory has low repair-bundle ceiling; use expanded actions")
    else:
        warnings.append(f"missing optional v11.7 probe-budget bundle harness: {rel(DEFAULT_V117)}")

    v118 = None
    if DEFAULT_V118.exists():
        v118 = load_json(DEFAULT_V118)
        metrics = v118.get("metrics") or {}
        if (metrics.get("rows_with_gold_progress_witness") or 0) < 6:
            warnings.append("v11.8 expanded action probe has too few gold progress witnesses")
    else:
        warnings.append(f"missing optional v11.8 expanded tactic action probe: {rel(DEFAULT_V118)}")

    v119 = None
    if DEFAULT_V119.exists():
        v119 = load_json(DEFAULT_V119)
        metrics = v119.get("metrics") or {}
        generic_25 = ((metrics.get("generic_fixed_action_order") or {}).get("25") or {})
        v115_25 = ((metrics.get("v115_expanded_affordance") or {}).get("25") or {})
        if (v115_25.get("budget_success") or 0) <= (generic_25.get("budget_success") or 0):
            warnings.append("v11.9 expanded action router does not beat generic fixed action order")
    else:
        warnings.append(f"missing optional v11.9 expanded action bundle router: {rel(DEFAULT_V119)}")

    v120 = None
    if DEFAULT_V120.exists():
        v120 = load_json(DEFAULT_V120)
        metrics = v120.get("metrics") or {}
        if (metrics.get("v115_budget7_progress_precision") or 0) < 0.5:
            warnings.append("v12.0 convert selectivity precision is low; do not trust raw convert progress")
    else:
        warnings.append(f"missing optional v12.0 convert selectivity audit: {rel(DEFAULT_V120)}")

    v121 = None
    if DEFAULT_V121.exists():
        v121 = load_json(DEFAULT_V121)
        metrics = v121.get("metrics") or {}
        small_selective = metrics.get("small_and_selective") or {}
        if (small_selective.get("precision") or 0) < 0.65:
            warnings.append("v12.1 focused witness precision is below promotion gate")
    else:
        warnings.append(f"missing optional v12.1 focused proof-state witness probe: {rel(DEFAULT_V121)}")

    v126 = None
    if DEFAULT_V126.exists():
        v126 = load_json(DEFAULT_V126)
    v126_passed = ((v126.get("evaluation") or {}).get("status") if v126 else None) == "full_target_unit_rewrite_passed"

    v123 = None
    if DEFAULT_V123.exists():
        v123 = load_json(DEFAULT_V123)
        metrics = v123.get("metrics") or {}
        strict = metrics.get("strict_snapshot") or {}
        sort_guarded = metrics.get("strict_sort_guarded_snapshot") or {}
        if (strict.get("precision") or 0) < 0.65 and not v126_passed:
            warnings.append("v12.3 full-snapshot witness gate failed; public candidates and GPU remain blocked")
        if (sort_guarded.get("bundle_success_at_7") or 0) < 0.5 and not v126_passed:
            warnings.append("v12.3 sort guard reveals Type-level closure contamination in structure-declaration rows")
    else:
        warnings.append(f"missing optional v12.3 full goal-snapshot witness probe: {rel(DEFAULT_V123)}")

    v124 = None
    if DEFAULT_V124.exists():
        v124 = load_json(DEFAULT_V124)
        if v124.get("status") != "mixed_target_unit_gap_confirmed":
            warnings.append("v12.4 target-unit audit did not confirm concentration; inspect before rebuilding rows")
    else:
        warnings.append(f"missing optional v12.4 target-unit audit: {rel(DEFAULT_V124)}")

    v125 = None
    if DEFAULT_V125.exists():
        v125 = load_json(DEFAULT_V125)
        if v125.get("status") != "target_unit_repair_packet_passed":
            warnings.append("v12.5 target-unit repair packet failed; do not rewrite benchmark yet")
    else:
        warnings.append(f"missing optional v12.5 target-unit repair packet: {rel(DEFAULT_V125)}")

    if v126 is not None:
        if not v126_passed:
            warnings.append("v12.6 full target-unit rewrite failed; do not run v12.7 policy evaluation yet")
        else:
            warnings.append("v12.6 full target-unit rewrite passed; repaired benchmark unit is available")
    else:
        warnings.append(f"missing optional v12.6 full target-unit rewrite packet: {rel(DEFAULT_V126)}")

    v127 = None
    if DEFAULT_V127.exists():
        v127 = load_json(DEFAULT_V127)
        if (v127.get("evaluation") or {}).get("status") != "target_aware_policy_eval_passed":
            warnings.append("v12.7 target-aware policy eval failed strict gate; do not expand benchmark or use GPU")
    else:
        warnings.append(f"missing optional v12.7 target-aware policy eval: {rel(DEFAULT_V127)}")

    v128 = None
    if DEFAULT_V128.exists():
        v128 = load_json(DEFAULT_V128)
        if v128.get("status") == "policy_gap_decomposition_actionable":
            warnings.append("v12.8 decomposition says next target is action-affordance compression plus v87 queue repair")
        else:
            warnings.append("v12.8 policy-gap decomposition is not actionable")
    else:
        warnings.append(f"missing optional v12.8 policy-gap decomposition: {rel(DEFAULT_V128)}")

    v129 = None
    if DEFAULT_V129.exists():
        v129 = load_json(DEFAULT_V129)
        if (v129.get("evaluation") or {}).get("status") == "compressed_affordance_policy_eval_passed":
            warnings.append("v12.9 compressed affordance passed repaired seed; robustness stress is next, not GPU")
        else:
            warnings.append("v12.9 compressed affordance policy failed; inspect before continuing")
    else:
        warnings.append(f"missing optional v12.9 compressed affordance policy eval: {rel(DEFAULT_V129)}")

    v130 = None
    if DEFAULT_V130.exists():
        v130 = load_json(DEFAULT_V130)
        if v130.get("pre_metric_prohibited_hit_count") != 0:
            warnings.append("v12.10 found pre-metric label leakage; rebuild queue before continuing")
        if v130.get("temporal_context_risk_count"):
            warnings.append("v12.10 found temporal/current-file candidate-pool risk; use pre-patch/scrubbed pools next")
    else:
        warnings.append(f"missing optional v12.10 label leakage static audit: {rel(DEFAULT_V130)}")

    primitive_surface = None
    if DEFAULT_PRIMITIVE_SURFACE.exists():
        primitive_surface = load_json(DEFAULT_PRIMITIVE_SURFACE)
        if not primitive_surface.get("ok"):
            warnings.append("RD primitive surface exists but is not ok")
    else:
        warnings.append("RD primitive surface missing; query primitives before adding metrics/graph algorithms")

    gpu_artifacts_present = False
    warnings.append("GPU v5.1/v5.2 validation pending; do not promote beyond advisory use")
    warnings.append("non-NS v5.2 guard pending; keep scope at NS/math workstation assistance")

    status = "pass_warn" if warnings else "pass"
    out = {
        "version": "rd_tick_gnn_precheck_v1_2026_05_11",
        "status": status,
        "scope": "advisory_only_frozen_artifact_consumer",
        "overfit_guards": {
            "retraining_in_tick": False,
            "uses_frozen_packet": True,
            "gpu_validation_present": gpu_artifacts_present,
            "non_ns_v52_guard_present": False,
            "endpoint_candidates_are_warnings": True,
            "event_per_node_tautology_is_warning": True,
        },
        "packet": {
            "path": rel(args.packet),
            "version": packet.get("version"),
            "best_epoch": packet.get("best_epoch"),
            "best_val_hit10": packet.get("best_val_hit10"),
            "n_pairs_extracted": packet.get("n_pairs_extracted"),
            "n_pairs_with_lemmas_in_vocab": packet.get("n_pairs_with_lemmas_in_vocab"),
        },
        "remote_cpu_sanity": {
            "path": rel(args.remote_cpu),
            "available": remote_cpu is not None,
            "best_epoch": remote_cpu.get("best_epoch") if remote_cpu else None,
            "metrics": remote_cpu.get("metrics") if remote_cpu else None,
        },
        "graph": graph_summary,
        "guarded_filter_v53": {
            "path": rel(DEFAULT_V53),
            "available": v53 is not None,
            "status": v53.get("status") if v53 else None,
            "metrics": v53.get("metrics") if v53 else None,
            "top_actionable_candidates": (v53.get("top_actionable_candidates") if v53 else [])[:8],
            "interpretation": v53.get("interpretation") if v53 else None,
        },
        "typed_symmetry_audit_v54": {
            "path": rel(DEFAULT_V54),
            "available": v54 is not None,
            "status": v54.get("status") if v54 else None,
            "missing_clean_required_roles": (
                v54.get("missing_clean_required_roles") if v54 else []
            ),
            "wrong_equivariance_risks": (
                v54.get("wrong_equivariance_risks") if v54 else []
            ),
            "collapse_risk_count": len(v54.get("collapse_risks") or []) if v54 else 0,
            "clean_role_counts": v54.get("clean_role_counts") if v54 else {},
            "roadmap": v54.get("roadmap") if v54 else [],
        },
        "typed_symmetry_canary_v55": {
            "path": rel(DEFAULT_V55),
            "available": v55 is not None,
            "status": v55.get("status") if v55 else None,
            "perturbations": v55.get("perturbations") if v55 else {},
            "roadmap_decision": v55.get("roadmap_decision") if v55 else {},
        },
        "typed_symmetry_audit_on_v56_top7": {
            "path": rel(DEFAULT_V54_REPAIRED),
            "available": v54_repaired is not None,
            "status": v54_repaired.get("status") if v54_repaired else None,
            "missing_clean_required_roles": (
                v54_repaired.get("missing_clean_required_roles") if v54_repaired else []
            ),
            "wrong_equivariance_risks": (
                v54_repaired.get("wrong_equivariance_risks") if v54_repaired else []
            ),
            "collapse_risk_count": (
                len(v54_repaired.get("collapse_risks") or []) if v54_repaired else 0
            ),
            "explicit_role_bridge_count": (
                len(v54_repaired.get("explicit_role_bridges") or []) if v54_repaired else 0
            ),
            "guard_cross_role_context_count": (
                len(v54_repaired.get("guard_cross_role_context") or []) if v54_repaired else 0
            ),
        },
        "typed_symmetry_canary_on_v56_top7": {
            "path": rel(DEFAULT_V55_REPAIRED),
            "available": v55_repaired is not None,
            "status": v55_repaired.get("status") if v55_repaired else None,
            "perturbations": v55_repaired.get("perturbations") if v55_repaired else {},
        },
        "typed_role_repair_v56": {
            "path": rel(DEFAULT_V56),
            "available": v56 is not None,
            "status": v56.get("status") if v56 else None,
            "missing_roles_repaired": v56.get("missing_roles_repaired") if v56 else [],
            "repair_candidates": [
                {
                    "name": row.get("name"),
                    "kind": row.get("kind"),
                    "line": row.get("line"),
                    "reasons": row.get("v53_reasons") or [],
                }
                for row in ((v56.get("repair_candidates") if v56 else []) or [])[:8]
            ],
        },
        "patch_attribution_v57": {
            "path": rel(DEFAULT_V57),
            "available": v57 is not None,
            "status": v57.get("status") if v57 else None,
            "rows": len(v57.get("rows") or []) if v57 else 0,
            "successful_attributions": sum(
                1 for row in ((v57.get("rows") if v57 else []) or [])
                if row.get("used_in_successful_edit") is True
            ),
            "anti_overfit_rule": v57.get("anti_overfit_rule") if v57 else None,
        },
        "typed_symmetry_residual_contract_v60": {
            "path": rel(DEFAULT_V60),
            "available": v60 is not None,
            "status": v60.get("status") if v60 else None,
            "architecture_decision": v60.get("architecture_decision") if v60 else {},
            "gates": v60.get("gates") if v60 else [],
            "kill_criteria": v60.get("kill_criteria") if v60 else [],
            "next_no_gpu_step": v60.get("next_no_gpu_step") if v60 else None,
        },
        "typed_obligation_hypergraph_contract_v61": {
            "path": rel(DEFAULT_V61),
            "available": v61 is not None,
            "status": v61.get("status") if v61 else None,
            "learned_unit": v61.get("learned_unit") if v61 else {},
            "current_readiness": v61.get("current_readiness") if v61 else {},
            "general_purpose_use": v61.get("general_purpose_use") if v61 else None,
        },
        "typed_obligation_work_packet_v62": {
            "path": rel(DEFAULT_V62),
            "available": v62 is not None,
            "status": v62.get("status") if v62 else None,
            "training_allowed": v62.get("training_allowed") if v62 else None,
            "tactical_vacuums": v62.get("tactical_vacuums") if v62 else [],
            "usefulness_criteria": v62.get("usefulness_criteria") if v62 else {},
        },
        "tri_arm_usefulness_pilot_v64": {
            "path": rel(DEFAULT_V64),
            "available": v64 is not None,
            "status": v64.get("status") if v64 else None,
            "pilot_read": v64.get("pilot_read") if v64 else None,
            "arms": {
                key: {"pilot_credit": value.get("pilot_credit")}
                for key, value in ((v64.get("arms") if v64 else {}) or {}).items()
            },
        },
        "compile_checked_patch_attributions": patch_attributions,
        "gnn_roadmap_v67": {
            "path": rel(DEFAULT_V67),
            "available": v67 is not None,
            "status": v67.get("status") if v67 else None,
            "next_versions": v67.get("next_versions") if v67 else {},
            "gpu_trigger": v67.get("gpu_trigger") if v67 else [],
            "do_not_train_yet": v67.get("do_not_train_yet") if v67 else [],
        },
        "endpoint_occluded_harness_v67": {
            "path": rel(DEFAULT_V67_HARNESS),
            "available": v67_harness is not None,
            "status": v67_harness.get("status") if v67_harness else None,
            "hit_at_3": v67_harness.get("hit_at_3") if v67_harness else None,
            "training_decision": v67_harness.get("training_decision") if v67_harness else None,
        },
        "non_ns_role_map_canary_v68": {
            "path": rel(DEFAULT_V68),
            "available": v68 is not None,
            "status": v68.get("status") if v68 else None,
            "substrates_tested": v68.get("substrates_tested") if v68 else [],
            "training_decision": v68.get("training_decision") if v68 else None,
            "limits": v68.get("limits") if v68 else [],
        },
        "non_ns_real_lean_canary_v69": {
            "path": rel(DEFAULT_V69),
            "available": v69 is not None,
            "status": v69.get("status") if v69 else None,
            "substrate": v69.get("substrate") if v69 else None,
            "role_hit_rate": v69.get("role_hit_rate") if v69 else None,
            "training_decision": v69.get("training_decision") if v69 else None,
        },
        "non_ns_generated_patch_v70": {
            "path": rel(DEFAULT_V70),
            "available": v70 is not None,
            "status": v70.get("status") if v70 else None,
            "substrate": v70.get("substrate") if v70 else None,
            "compile_checked": (
                ((v70.get("ex_post_usefulness") or {}).get("compile_checked") is True)
                if v70 else None
            ),
            "added_declarations": (v70.get("patch") or {}).get("added_declarations") if v70 else [],
        },
        "external_benchmark_intake_v71": {
            "path": rel(DEFAULT_V71),
            "available": v71 is not None,
            "status": v71.get("status") if v71 else None,
            "bench_root": v71.get("bench_root") if v71 else None,
            "training_decision": v71.get("training_decision") if v71 else None,
        },
        "mathlibgraph_external_baseline_v72": {
            "path": rel(DEFAULT_V72),
            "available": v72 is not None,
            "status": v72.get("status") if v72 else None,
            "network_r10": (
                ((v72.get("premise_retrieval_results") or {}).get("Network features") or {}).get("R@10")
                if v72 else None
            ),
            "all_features_r10": (
                ((v72.get("premise_retrieval_results") or {}).get("All features") or {}).get("R@10")
                if v72 else None
            ),
            "hard_network_r10": (
                ((v72.get("premise_retrieval_hard_negatives") or {}).get("Network features") or {}).get("R@10")
                if v72 else None
            ),
            "hard_all_features_r10": (
                ((v72.get("premise_retrieval_hard_negatives") or {}).get("All features") or {}).get("R@10")
                if v72 else None
            ),
            "decision": (v72.get("decision") if v72 else None),
        },
        "scientific_yield_gate_v73": {
            "path": rel(DEFAULT_V73),
            "available": v73 is not None,
            "status": v73.get("status") if v73 else None,
            "gpu_training_allowed": v73.get("gpu_training_allowed") if v73 else None,
            "novelty_claim_allowed": v73.get("novelty_claim_allowed") if v73 else None,
            "evidence": v73.get("evidence") if v73 else None,
        },
        "leanrank_gated_residual_v76": {
            "path": rel(DEFAULT_V76),
            "available": v76 is not None,
            "status": v76.get("status") if v76 else None,
            "best_safe_policy": v76.get("best_safe_policy") if v76 else None,
            "best_safe_delta": (
                ((v76.get("deltas_vs_graph") or {}).get(v76.get("best_safe_policy")) if v76 else None)
            ),
        },
        "repair_benchmark_seed_v79": {
            "path": rel(DEFAULT_V79),
            "available": v79 is not None,
            "status": v79.get("status") if v79 else None,
            "row_count": v79.get("row_count") if v79 else None,
            "generated_non_ns_rows": v79.get("generated_non_ns_rows") if v79 else None,
            "training_decision": v79.get("training_decision") if v79 else None,
        },
        "leanrank_bm25_gated_v80": {
            "path": rel(DEFAULT_V80),
            "available": v80 is not None,
            "status": v80.get("status") if v80 else None,
            "rows_scored": v80.get("rows_scored") if v80 else None,
            "graph_top1_bm25_tail_metrics": (
                ((v80.get("metrics") or {}).get("graph_tail_after_top1_bm25"))
                if v80 else None
            ),
            "graph_top1_bm25_tail_delta": (
                ((v80.get("deltas_vs_graph") or {}).get("graph_tail_after_top1_bm25"))
                if v80 else None
            ),
        },
        "repair_router_protocol_v81": {
            "path": rel(DEFAULT_V81),
            "available": v81 is not None,
            "status": v81.get("status") if v81 else None,
            "row_count": v81.get("row_count") if v81 else None,
            "cheap_baseline_success_at_1": (
                v81.get("cheap_baseline_success_at_1") if v81 else None
            ),
            "typed_router_success_at_1": (
                v81.get("typed_router_success_at_1") if v81 else None
            ),
            "interpretation": v81.get("interpretation") if v81 else None,
        },
        "actual_declaration_repair_pool_v82": {
            "path": rel(DEFAULT_V82),
            "available": v82 is not None,
            "status": v82.get("status") if v82 else None,
            "row_count": v82.get("row_count") if v82 else None,
            "metrics": v82.get("metrics") if v82 else None,
            "interpretation": v82.get("interpretation") if v82 else None,
        },
        "constrained_repair_queue_v83": {
            "path": rel(DEFAULT_V83),
            "available": v83 is not None,
            "status": v83.get("status") if v83 else None,
            "row_count": v83.get("row_count") if v83 else None,
            "metrics": v83.get("metrics") if v83 else None,
            "interpretation": v83.get("interpretation") if v83 else None,
        },
        "hybrid_repair_router_v84": {
            "path": rel(DEFAULT_V84),
            "available": v84 is not None,
            "status": v84.get("status") if v84 else None,
            "row_count": v84.get("row_count") if v84 else None,
            "metrics": v84.get("metrics") if v84 else None,
            "interpretation": v84.get("interpretation") if v84 else None,
        },
        "literature_positioning_v85": {
            "path": rel(DEFAULT_V85),
            "available": v85 is not None,
            "status": v85.get("status") if v85 else None,
            "sources": v85.get("sources") if v85 else [],
            "positioning": v85.get("positioning") if v85 else None,
            "next_test": v85.get("next_test") if v85 else None,
        },
        "repair_router_alias_stress_v88": {
            "path": rel(DEFAULT_V88),
            "available": v88 is not None,
            "status": v88.get("status") if v88 else None,
            "row_count": v88.get("row_count") if v88 else None,
            "metrics": v88.get("metrics") if v88 else None,
            "interpretation": v88.get("interpretation") if v88 else None,
        },
        "repair_router_structural_occlusion_v90": {
            "path": rel(DEFAULT_V90),
            "available": v90 is not None,
            "status": v90.get("status") if v90 else None,
            "row_count": v90.get("row_count") if v90 else None,
            "metrics": v90.get("metrics") if v90 else None,
            "interpretation": v90.get("interpretation") if v90 else None,
        },
        "label_blind_hard_decoy_audit_v92": {
            "path": rel(DEFAULT_V92),
            "available": v92 is not None,
            "status": v92.get("status") if v92 else None,
            "decision": v92.get("decision") if v92 else None,
            "static_label_blind_check": v92.get("static_label_blind_check") if v92 else None,
            "metrics": v92.get("metrics") if v92 else None,
            "interpretation": v92.get("interpretation") if v92 else None,
        },
        "kernel_shape_feature_probe_v93": {
            "path": rel(DEFAULT_V93),
            "available": v93 is not None,
            "status": v93.get("status") if v93 else None,
            "metrics": v93.get("metrics") if v93 else None,
            "interpretation": v93.get("interpretation") if v93 else None,
        },
        "post_patch_dependency_probe_v94": {
            "path": rel(DEFAULT_V94),
            "available": v94 is not None,
            "status": v94.get("status") if v94 else None,
            "metrics": v94.get("metrics") if v94 else None,
            "interpretation": v94.get("interpretation") if v94 else None,
        },
        "lean_environment_type_extractor_v95": {
            "path": rel(DEFAULT_V95),
            "available": v95 is not None,
            "status": v95.get("status") if v95 else None,
            "row_count": v95.get("row_count") if v95 else None,
            "rows_resolved": v95.get("rows_resolved") if v95 else None,
            "interpretation": v95.get("interpretation") if v95 else None,
        },
        "lean_expr_ast_graph_extractor_v96": {
            "path": rel(DEFAULT_V96),
            "available": v96 is not None,
            "status": v96.get("status") if v96 else None,
            "candidate_count": v96.get("candidate_count") if v96 else None,
            "resolved_candidate_count": v96.get("resolved_candidate_count") if v96 else None,
            "ast_node_count": v96.get("ast_node_count") if v96 else None,
            "ast_edge_count": v96.get("ast_edge_count") if v96 else None,
            "const_occurrence_count": v96.get("const_occurrence_count") if v96 else None,
            "ast_kind_counts": v96.get("ast_kind_counts") if v96 else None,
            "interpretation": v96.get("interpretation") if v96 else None,
        },
        "ast_graph_repair_backtest_v97": {
            "path": rel(DEFAULT_V97),
            "available": v97 is not None,
            "status": v97.get("status") if v97 else None,
            "metrics": v97.get("metrics") if v97 else None,
            "interpretation": v97.get("interpretation") if v97 else None,
        },
        "symbolic_expr_graph_backtest_v98": {
            "path": rel(DEFAULT_V98),
            "available": v98 is not None,
            "status": v98.get("status") if v98 else None,
            "modes": {
                mode: {
                    "hit_at_7": data.get("hit_at_7"),
                    "mrr": data.get("mrr"),
                }
                for mode, data in ((v98.get("modes") if v98 else {}) or {}).items()
            },
            "interpretation": v98.get("interpretation") if v98 else None,
        },
        "typed_obligation_expr_graph_v99": {
            "path": rel(DEFAULT_V99),
            "available": v99 is not None,
            "status": v99.get("status") if v99 else None,
            "node_count": v99.get("node_count") if v99 else None,
            "edge_count": v99.get("edge_count") if v99 else None,
            "node_kind_counts": v99.get("node_kind_counts") if v99 else None,
            "edge_kind_counts": v99.get("edge_kind_counts") if v99 else None,
            "interpretation": v99.get("interpretation") if v99 else None,
        },
        "typed_neighborhood_similarity_v100": {
            "path": rel(DEFAULT_V100),
            "available": v100 is not None,
            "status": v100.get("status") if v100 else None,
            "modes": {
                mode: {"hit_at_7": data.get("hit_at_7"), "mrr": data.get("mrr")}
                for mode, data in ((v100.get("modes") if v100 else {}) or {}).items()
            },
            "interpretation": v100.get("interpretation") if v100 else None,
        },
        "ppr_typed_obligation_graph_v101": {
            "path": rel(DEFAULT_V101),
            "available": v101 is not None,
            "status": v101.get("status") if v101 else None,
            "modes": {
                mode: {"hit_at_7": data.get("hit_at_7"), "mrr": data.get("mrr")}
                for mode, data in ((v101.get("modes") if v101 else {}) or {}).items()
            },
            "interpretation": v101.get("interpretation") if v101 else None,
        },
        "row_obligation_seeded_role_backtest_v102": {
            "path": rel(DEFAULT_V102),
            "available": v102 is not None,
            "status": v102.get("status") if v102 else None,
            "metrics": v102.get("metrics") if v102 else None,
            "interpretation": v102.get("interpretation") if v102 else None,
            "next_action": v102.get("next_action") if v102 else None,
        },
        "nonbootstrap_interface_role_extractor_v103": {
            "path": rel(DEFAULT_V103),
            "available": v103 is not None,
            "status": v103.get("status") if v103 else None,
            "metrics": v103.get("metrics") if v103 else None,
            "nonbootstrap_contract": v103.get("nonbootstrap_contract") if v103 else None,
            "role_counts": v103.get("role_counts") if v103 else None,
            "interpretation": v103.get("interpretation") if v103 else None,
            "next_action": v103.get("next_action") if v103 else None,
        },
        "action_delta_type_probe_v104": {
            "path": rel(DEFAULT_V104),
            "available": v104 is not None,
            "status": v104.get("status") if v104 else None,
            "metrics": v104.get("metrics") if v104 else None,
            "contract": v104.get("contract") if v104 else None,
            "interpretation": v104.get("interpretation") if v104 else None,
            "next_action": v104.get("next_action") if v104 else None,
        },
        "metavar_action_delta_probe_v105": {
            "path": rel(DEFAULT_V105),
            "available": v105 is not None,
            "status": v105.get("status") if v105 else None,
            "metrics": v105.get("metrics") if v105 else None,
            "contract": v105.get("contract") if v105 else None,
            "interpretation": v105.get("interpretation") if v105 else None,
            "next_action": v105.get("next_action") if v105 else None,
        },
        "antifailure_repair_router_v106": {
            "path": rel(DEFAULT_V106),
            "available": v106 is not None,
            "status": v106.get("status") if v106 else None,
            "metrics": v106.get("metrics") if v106 else None,
            "contract": v106.get("contract") if v106 else None,
            "interpretation": v106.get("interpretation") if v106 else None,
            "next_action": v106.get("next_action") if v106 else None,
        },
        "tactic_rewrite_delta_probe_v107": {
            "path": rel(DEFAULT_V107),
            "available": v107 is not None,
            "status": v107.get("status") if v107 else None,
            "metrics": v107.get("metrics") if v107 else None,
            "contract": v107.get("contract") if v107 else None,
            "interpretation": v107.get("interpretation") if v107 else None,
            "next_action": v107.get("next_action") if v107 else None,
        },
        "combined_action_delta_router_v108": {
            "path": rel(DEFAULT_V108),
            "available": v108 is not None,
            "status": v108.get("status") if v108 else None,
            "metrics": v108.get("metrics") if v108 else None,
            "contract": v108.get("contract") if v108 else None,
            "interpretation": v108.get("interpretation") if v108 else None,
            "next_action": v108.get("next_action") if v108 else None,
        },
        "tactic_failure_taxonomy_probe_v109": {
            "path": rel(DEFAULT_V109),
            "available": v109 is not None,
            "status": v109.get("status") if v109 else None,
            "metrics": v109.get("metrics") if v109 else None,
            "contract": v109.get("contract") if v109 else None,
            "interpretation": v109.get("interpretation") if v109 else None,
            "failure_samples": v109.get("failure_samples") if v109 else None,
        },
        "probe_budget_repair_bundle_harness_v117": {
            "path": rel(DEFAULT_V117),
            "available": v117 is not None,
            "status": v117.get("status") if v117 else None,
            "probe_inventory_ceiling": v117.get("probe_inventory_ceiling") if v117 else None,
            "metrics": v117.get("metrics") if v117 else None,
            "interpretation": v117.get("interpretation") if v117 else None,
        },
        "expanded_tactic_action_probe_v118": {
            "path": rel(DEFAULT_V118),
            "available": v118 is not None,
            "status": v118.get("status") if v118 else None,
            "metrics": v118.get("metrics") if v118 else None,
            "contract": v118.get("contract") if v118 else None,
            "interpretation": v118.get("interpretation") if v118 else None,
        },
        "expanded_action_bundle_router_v119": {
            "path": rel(DEFAULT_V119),
            "available": v119 is not None,
            "status": v119.get("status") if v119 else None,
            "metrics": v119.get("metrics") if v119 else None,
            "contract": v119.get("contract") if v119 else None,
            "interpretation": v119.get("interpretation") if v119 else None,
        },
        "convert_selectivity_audit_v120": {
            "path": rel(DEFAULT_V120),
            "available": v120 is not None,
            "status": v120.get("status") if v120 else None,
            "metrics": v120.get("metrics") if v120 else None,
            "interpretation": v120.get("interpretation") if v120 else None,
        },
        "focused_proof_state_witness_v121": {
            "path": rel(DEFAULT_V121),
            "available": v121 is not None,
            "status": v121.get("status") if v121 else None,
            "metrics": v121.get("metrics") if v121 else None,
            "interpretation": v121.get("interpretation") if v121 else None,
        },
        "full_goal_snapshot_witness_v123": {
            "path": rel(DEFAULT_V123),
            "available": v123 is not None,
            "status": v123.get("status") if v123 else None,
            "metrics": v123.get("metrics") if v123 else None,
            "interpretation": v123.get("interpretation") if v123 else None,
        },
        "target_unit_audit_v124": {
            "path": rel(DEFAULT_V124),
            "available": v124 is not None,
            "status": v124.get("status") if v124 else None,
            "metrics": v124.get("metrics") if v124 else None,
            "interpretation": v124.get("interpretation") if v124 else None,
        },
        "target_unit_repair_packet_v125": {
            "path": rel(DEFAULT_V125),
            "available": v125 is not None,
            "status": v125.get("status") if v125 else None,
            "metrics": v125.get("metrics") if v125 else None,
            "interpretation": v125.get("interpretation") if v125 else None,
        },
        "full_target_unit_rewrite_v126": {
            "path": rel(DEFAULT_V126),
            "available": v126 is not None,
            "status": ((v126.get("evaluation") or {}).get("status") if v126 else None),
            "metrics": (((v126.get("evaluation") or {}).get("metrics")) if v126 else None),
        },
        "target_aware_policy_eval_v127": {
            "path": rel(DEFAULT_V127),
            "available": v127 is not None,
            "status": ((v127.get("evaluation") or {}).get("status") if v127 else None),
            "metrics": (((v127.get("evaluation") or {}).get("metrics")) if v127 else None),
            "aggregate": (((v127.get("evaluation") or {}).get("aggregate")) if v127 else None),
        },
        "policy_gap_decomposition_v128": {
            "path": rel(DEFAULT_V128),
            "available": v128 is not None,
            "status": v128.get("status") if v128 else None,
            "metrics": v128.get("metrics") if v128 else None,
        },
        "compressed_affordance_policy_v129": {
            "path": rel(DEFAULT_V129),
            "available": v129 is not None,
            "status": ((v129.get("evaluation") or {}).get("status") if v129 else None),
            "metrics": (((v129.get("evaluation") or {}).get("metrics")) if v129 else None),
            "aggregate": (((v129.get("evaluation") or {}).get("aggregate")) if v129 else None),
        },
        "label_leakage_static_audit_v130": {
            "path": rel(DEFAULT_V130),
            "available": v130 is not None,
            "status": v130.get("status") if v130 else None,
            "pre_metric_prohibited_hit_count": v130.get("pre_metric_prohibited_hit_count") if v130 else None,
            "temporal_context_risk_count": v130.get("temporal_context_risk_count") if v130 else None,
        },
        "rd_primitive_surface": {
            "path": rel(DEFAULT_PRIMITIVE_SURFACE),
            "available": primitive_surface is not None,
            "ok": primitive_surface.get("ok") if primitive_surface else None,
            "top_hits": [
                {"id": hit.get("id"), "path": hit.get("path"), "score": hit.get("score")}
                for hit in ((primitive_surface.get("top_hits") if primitive_surface else []) or [])[:10]
            ],
        },
        "packet_summary": packet_summary,
        "warnings": warnings,
        "errors": errors,
        "rd_instruction": (
            "Use top candidates as premise/navigation context only. Prefer atomic "
            "primitives and adapters; treat endpoint, event-per-node, and guard "
            "recommendations as danger/context unless separately justified."
        ),
        "consumption_protocol": [
            "Start from `actionable_candidate_names`, not the raw top-candidate list.",
            "Use danger candidates only as guards or context.",
            "Prefer declarations also present in the same-tree obligation graph.",
            "Do not launch GPU/API/autoresearch spend from this precheck alone.",
            "After a patch, record whether a top candidate actually influenced the edit.",
        ],
    }
    return 0, out


def write_markdown(precheck: dict, path: Path) -> None:
    lines = [
        "# RD Tick GNN Precheck",
        "",
        f"**Status:** `{precheck.get('status')}`",
        "",
        precheck.get("rd_instruction", ""),
        "",
        "## Overfit Guards",
        "",
    ]
    for key, value in (precheck.get("overfit_guards") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Packet", ""])
    packet = precheck.get("packet") or {}
    for key in ("path", "version", "best_epoch", "best_val_hit10", "n_pairs_extracted", "n_pairs_with_lemmas_in_vocab"):
        lines.append(f"- `{key}`: `{packet.get(key)}`")
    remote = precheck.get("remote_cpu_sanity") or {}
    lines.extend(["", "## Remote CPU Sanity", ""])
    lines.append(f"- `available`: `{remote.get('available')}`")
    lines.append(f"- `path`: `{remote.get('path')}`")
    if remote.get("metrics"):
        lines.append(f"- `metrics`: `{remote.get('metrics')}`")
    graph = precheck.get("graph") or {}
    lines.extend(["", "## Graph", ""])
    lines.append(f"- `path`: `{graph.get('path')}`")
    lines.append(f"- `missing_tags`: `{graph.get('missing_tags')}`")
    lines.append(f"- `thin_tags`: `{graph.get('thin_tags')}`")
    if graph.get("atomic_nodes_detected"):
        lines.append("- atomic nodes detected:")
        for node in graph["atomic_nodes_detected"]:
            lines.append(f"  - `{node}`")
    v53 = precheck.get("guarded_filter_v53") or {}
    lines.extend(["", "## v5.3 Guarded Filter", ""])
    lines.append(f"- `available`: `{v53.get('available')}`")
    lines.append(f"- `status`: `{v53.get('status')}`")
    lines.append(f"- `path`: `{v53.get('path')}`")
    metrics = v53.get("metrics") or {}
    if metrics:
        raw = metrics.get("raw_profile") or {}
        filtered = metrics.get("filtered_profile") or {}
        lines.append(f"- raw hit@10: `{metrics.get('raw_hit@10')}`")
        lines.append(f"- filtered hit@10: `{metrics.get('filtered_hit@10')}`")
        lines.append(f"- raw clean actionability: `{raw.get('clean_actionable_fraction')}`")
        lines.append(f"- filtered clean actionability: `{filtered.get('clean_actionable_fraction')}`")
        lines.append(f"- raw danger fraction: `{raw.get('danger_fraction')}`")
        lines.append(f"- filtered danger fraction: `{filtered.get('danger_fraction')}`")
    v54 = precheck.get("typed_symmetry_audit_v54") or {}
    lines.extend(["", "## v5.4 Typed-Symmetry Audit", ""])
    lines.append(f"- `available`: `{v54.get('available')}`")
    lines.append(f"- `status`: `{v54.get('status')}`")
    lines.append(f"- `path`: `{v54.get('path')}`")
    lines.append(f"- `missing_clean_required_roles`: `{v54.get('missing_clean_required_roles')}`")
    lines.append(f"- `wrong_equivariance_risks`: `{v54.get('wrong_equivariance_risks')}`")
    lines.append(f"- `collapse_risk_count`: `{v54.get('collapse_risk_count')}`")
    v55 = precheck.get("typed_symmetry_canary_v55") or {}
    lines.extend(["", "## v5.5 Typed-Symmetry Canary", ""])
    lines.append(f"- `available`: `{v55.get('available')}`")
    lines.append(f"- `status`: `{v55.get('status')}`")
    lines.append(f"- `path`: `{v55.get('path')}`")
    perturb = v55.get("perturbations") or {}
    for key in ("namespace_prefix", "binder_suffix", "semantic_alias"):
        if key in perturb:
            lines.append(
                f"- `{key}` role preservation: "
                f"`{perturb[key].get('role_preservation_rate')}`"
            )
    lines.append(f"- `roadmap_decision`: `{v55.get('roadmap_decision')}`")
    v54r = precheck.get("typed_symmetry_audit_on_v56_top7") or {}
    lines.extend(["", "## v5.4 Audit on v5.6 Repaired Queue", ""])
    lines.append(f"- `available`: `{v54r.get('available')}`")
    lines.append(f"- `status`: `{v54r.get('status')}`")
    lines.append(f"- `path`: `{v54r.get('path')}`")
    lines.append(f"- `missing_clean_required_roles`: `{v54r.get('missing_clean_required_roles')}`")
    lines.append(f"- `wrong_equivariance_risks`: `{v54r.get('wrong_equivariance_risks')}`")
    lines.append(f"- `collapse_risk_count`: `{v54r.get('collapse_risk_count')}`")
    lines.append(f"- `explicit_role_bridge_count`: `{v54r.get('explicit_role_bridge_count')}`")
    v55r = precheck.get("typed_symmetry_canary_on_v56_top7") or {}
    lines.extend(["", "## v5.5 Canary on v5.6 Repaired Queue", ""])
    lines.append(f"- `available`: `{v55r.get('available')}`")
    lines.append(f"- `status`: `{v55r.get('status')}`")
    lines.append(f"- `path`: `{v55r.get('path')}`")
    perturb_r = v55r.get("perturbations") or {}
    if "semantic_alias" in perturb_r:
        lines.append(
            "- `semantic_alias` role preservation: "
            f"`{perturb_r['semantic_alias'].get('role_preservation_rate')}`"
        )
    v56 = precheck.get("typed_role_repair_v56") or {}
    lines.extend(["", "## v5.6 Typed-Role Repair Queue", ""])
    lines.append(f"- `available`: `{v56.get('available')}`")
    lines.append(f"- `status`: `{v56.get('status')}`")
    lines.append(f"- `path`: `{v56.get('path')}`")
    lines.append(f"- `missing_roles_repaired`: `{v56.get('missing_roles_repaired')}`")
    for cand in v56.get("repair_candidates") or []:
        lines.append(
            f"- repair `{cand.get('name')}` `{cand.get('kind')}` line `{cand.get('line')}`"
        )
    v57 = precheck.get("patch_attribution_v57") or {}
    lines.extend(["", "## v5.7 Patch Attribution", ""])
    lines.append(f"- `available`: `{v57.get('available')}`")
    lines.append(f"- `status`: `{v57.get('status')}`")
    lines.append(f"- `path`: `{v57.get('path')}`")
    lines.append(f"- `rows`: `{v57.get('rows')}`")
    lines.append(f"- `successful_attributions`: `{v57.get('successful_attributions')}`")
    lines.append(f"- `anti_overfit_rule`: `{v57.get('anti_overfit_rule')}`")
    v60 = precheck.get("typed_symmetry_residual_contract_v60") or {}
    lines.extend(["", "## v6 Typed-Symmetry Residual Contract", ""])
    lines.append(f"- `available`: `{v60.get('available')}`")
    lines.append(f"- `status`: `{v60.get('status')}`")
    lines.append(f"- `path`: `{v60.get('path')}`")
    lines.append(f"- `architecture_decision`: `{v60.get('architecture_decision')}`")
    lines.append(f"- `next_no_gpu_step`: `{v60.get('next_no_gpu_step')}`")
    v61 = precheck.get("typed_obligation_hypergraph_contract_v61") or {}
    lines.extend(["", "## v6.1 Typed-Obligation Hypergraph Contract", ""])
    lines.append(f"- `available`: `{v61.get('available')}`")
    lines.append(f"- `status`: `{v61.get('status')}`")
    lines.append(f"- `path`: `{v61.get('path')}`")
    readiness = v61.get("current_readiness") or {}
    lines.append(f"- `training_allowed`: `{readiness.get('training_allowed')}`")
    lines.append(f"- `successful_patch_attributions`: `{readiness.get('successful_patch_attributions')}`")
    lines.append(f"- `general_purpose_use`: `{v61.get('general_purpose_use')}`")
    v62 = precheck.get("typed_obligation_work_packet_v62") or {}
    lines.extend(["", "## v6.2 Typed-Obligation Work Packet", ""])
    lines.append(f"- `available`: `{v62.get('available')}`")
    lines.append(f"- `status`: `{v62.get('status')}`")
    lines.append(f"- `path`: `{v62.get('path')}`")
    lines.append(f"- `training_allowed`: `{v62.get('training_allowed')}`")
    for vacuum in v62.get("tactical_vacuums") or []:
        lines.append(f"- tactical `{vacuum.get('name')}` `{vacuum.get('verdict')}`")
    v64 = precheck.get("tri_arm_usefulness_pilot_v64") or {}
    lines.extend(["", "## v6.4 Tri-Arm Usefulness Pilot", ""])
    lines.append(f"- `available`: `{v64.get('available')}`")
    lines.append(f"- `status`: `{v64.get('status')}`")
    lines.append(f"- `path`: `{v64.get('path')}`")
    lines.append(f"- `arms`: `{v64.get('arms')}`")
    lines.append(f"- `pilot_read`: {v64.get('pilot_read')}")
    lines.extend(["", "## Compile-Checked Patch Attributions", ""])
    for row in precheck.get("compile_checked_patch_attributions") or []:
        lines.append(f"- `{row.get('path')}` status `{row.get('status')}` compile `{row.get('compile_checked')}`")
        for decl in row.get("added_declarations") or []:
            lines.append(f"  - `{decl}`")
    v67 = precheck.get("gnn_roadmap_v67") or {}
    lines.extend(["", "## v6.7/v7 Roadmap", ""])
    lines.append(f"- `available`: `{v67.get('available')}`")
    lines.append(f"- `status`: `{v67.get('status')}`")
    lines.append(f"- `path`: `{v67.get('path')}`")
    lines.append(f"- `next_versions`: `{v67.get('next_versions')}`")
    lines.append(f"- `gpu_trigger`: `{v67.get('gpu_trigger')}`")
    lines.append(f"- `do_not_train_yet`: `{v67.get('do_not_train_yet')}`")
    harness = precheck.get("endpoint_occluded_harness_v67") or {}
    lines.extend(["", "## v6.7 Endpoint-Occluded Harness", ""])
    lines.append(f"- `available`: `{harness.get('available')}`")
    lines.append(f"- `status`: `{harness.get('status')}`")
    lines.append(f"- `hit_at_3`: `{harness.get('hit_at_3')}`")
    lines.append(f"- `training_decision`: `{harness.get('training_decision')}`")
    v68 = precheck.get("non_ns_role_map_canary_v68") or {}
    lines.extend(["", "## v6.8 Non-NS Role-Map Canary", ""])
    lines.append(f"- `available`: `{v68.get('available')}`")
    lines.append(f"- `status`: `{v68.get('status')}`")
    lines.append(f"- `substrates_tested`: `{v68.get('substrates_tested')}`")
    lines.append(f"- `training_decision`: `{v68.get('training_decision')}`")
    v69 = precheck.get("non_ns_real_lean_canary_v69") or {}
    lines.extend(["", "## v6.9 Real Non-NS Lean Canary", ""])
    lines.append(f"- `available`: `{v69.get('available')}`")
    lines.append(f"- `status`: `{v69.get('status')}`")
    lines.append(f"- `substrate`: `{v69.get('substrate')}`")
    lines.append(f"- `role_hit_rate`: `{v69.get('role_hit_rate')}`")
    lines.append(f"- `training_decision`: `{v69.get('training_decision')}`")
    v70 = precheck.get("non_ns_generated_patch_v70") or {}
    lines.extend(["", "## v7.0 Non-NS Generated Patch", ""])
    lines.append(f"- `available`: `{v70.get('available')}`")
    lines.append(f"- `status`: `{v70.get('status')}`")
    lines.append(f"- `substrate`: `{v70.get('substrate')}`")
    lines.append(f"- `compile_checked`: `{v70.get('compile_checked')}`")
    lines.append(f"- `added_declarations`: `{v70.get('added_declarations')}`")
    v71 = precheck.get("external_benchmark_intake_v71") or {}
    lines.extend(["", "## v7.1 External Benchmark Intake", ""])
    lines.append(f"- `available`: `{v71.get('available')}`")
    lines.append(f"- `status`: `{v71.get('status')}`")
    lines.append(f"- `bench_root`: `{v71.get('bench_root')}`")
    lines.append(f"- `training_decision`: `{v71.get('training_decision')}`")
    v72 = precheck.get("mathlibgraph_external_baseline_v72") or {}
    lines.extend(["", "## v7.2 MathlibGraph Baseline", ""])
    lines.append(f"- `available`: `{v72.get('available')}`")
    lines.append(f"- `status`: `{v72.get('status')}`")
    lines.append(f"- `network_r10`: `{v72.get('network_r10')}`")
    lines.append(f"- `all_features_r10`: `{v72.get('all_features_r10')}`")
    lines.append(f"- `hard_network_r10`: `{v72.get('hard_network_r10')}`")
    lines.append(f"- `hard_all_features_r10`: `{v72.get('hard_all_features_r10')}`")
    v73 = precheck.get("scientific_yield_gate_v73") or {}
    lines.extend(["", "## v7.3 Scientific-Yield Gate", ""])
    lines.append(f"- `available`: `{v73.get('available')}`")
    lines.append(f"- `status`: `{v73.get('status')}`")
    lines.append(f"- `gpu_training_allowed`: `{v73.get('gpu_training_allowed')}`")
    lines.append(f"- `novelty_claim_allowed`: `{v73.get('novelty_claim_allowed')}`")
    lines.append(f"- `evidence`: `{v73.get('evidence')}`")
    v76 = precheck.get("leanrank_gated_residual_v76") or {}
    lines.extend(["", "## v7.6 LeanRank Gated Residual", ""])
    lines.append(f"- `available`: `{v76.get('available')}`")
    lines.append(f"- `status`: `{v76.get('status')}`")
    lines.append(f"- `best_safe_policy`: `{v76.get('best_safe_policy')}`")
    lines.append(f"- `best_safe_delta`: `{v76.get('best_safe_delta')}`")
    v79 = precheck.get("repair_benchmark_seed_v79") or {}
    lines.extend(["", "## v7.9 Repair Benchmark Seed", ""])
    lines.append(f"- `available`: `{v79.get('available')}`")
    lines.append(f"- `status`: `{v79.get('status')}`")
    lines.append(f"- `row_count`: `{v79.get('row_count')}`")
    lines.append(f"- `generated_non_ns_rows`: `{v79.get('generated_non_ns_rows')}`")
    lines.append(f"- `training_decision`: `{v79.get('training_decision')}`")
    v80 = precheck.get("leanrank_bm25_gated_v80") or {}
    lines.extend(["", "## v8.0 LeanRank BM25 Gated Eval", ""])
    lines.append(f"- `available`: `{v80.get('available')}`")
    lines.append(f"- `status`: `{v80.get('status')}`")
    lines.append(f"- `rows_scored`: `{v80.get('rows_scored')}`")
    lines.append(f"- `graph_top1_bm25_tail_metrics`: `{v80.get('graph_top1_bm25_tail_metrics')}`")
    lines.append(f"- `graph_top1_bm25_tail_delta`: `{v80.get('graph_top1_bm25_tail_delta')}`")
    v81 = precheck.get("repair_router_protocol_v81") or {}
    lines.extend(["", "## v8.1 Repair Router Protocol", ""])
    lines.append(f"- `available`: `{v81.get('available')}`")
    lines.append(f"- `status`: `{v81.get('status')}`")
    lines.append(f"- `row_count`: `{v81.get('row_count')}`")
    lines.append(f"- `cheap_baseline_success_at_1`: `{v81.get('cheap_baseline_success_at_1')}`")
    lines.append(f"- `typed_router_success_at_1`: `{v81.get('typed_router_success_at_1')}`")
    lines.append(f"- `interpretation`: `{v81.get('interpretation')}`")
    v82 = precheck.get("actual_declaration_repair_pool_v82") or {}
    lines.extend(["", "## v8.2 Actual-Declaration Repair Pool", ""])
    lines.append(f"- `available`: `{v82.get('available')}`")
    lines.append(f"- `status`: `{v82.get('status')}`")
    lines.append(f"- `row_count`: `{v82.get('row_count')}`")
    lines.append(f"- `metrics`: `{v82.get('metrics')}`")
    v83 = precheck.get("constrained_repair_queue_v83") or {}
    lines.extend(["", "## v8.3 Constrained Repair Queue", ""])
    lines.append(f"- `available`: `{v83.get('available')}`")
    lines.append(f"- `status`: `{v83.get('status')}`")
    lines.append(f"- `row_count`: `{v83.get('row_count')}`")
    lines.append(f"- `metrics`: `{v83.get('metrics')}`")
    v84 = precheck.get("hybrid_repair_router_v84") or {}
    lines.extend(["", "## v8.4 Hybrid Repair Router", ""])
    lines.append(f"- `available`: `{v84.get('available')}`")
    lines.append(f"- `status`: `{v84.get('status')}`")
    lines.append(f"- `row_count`: `{v84.get('row_count')}`")
    lines.append(f"- `metrics`: `{v84.get('metrics')}`")
    v85 = precheck.get("literature_positioning_v85") or {}
    lines.extend(["", "## v8.5 Literature Positioning", ""])
    lines.append(f"- `available`: `{v85.get('available')}`")
    lines.append(f"- `status`: `{v85.get('status')}`")
    lines.append(f"- `positioning`: `{v85.get('positioning')}`")
    lines.append(f"- `next_test`: `{v85.get('next_test')}`")
    v88 = precheck.get("repair_router_alias_stress_v88") or {}
    lines.extend(["", "## v8.8 Repair Router Alias Stress", ""])
    lines.append(f"- `available`: `{v88.get('available')}`")
    lines.append(f"- `status`: `{v88.get('status')}`")
    lines.append(f"- `row_count`: `{v88.get('row_count')}`")
    lines.append(f"- `metrics`: `{v88.get('metrics')}`")
    v90 = precheck.get("repair_router_structural_occlusion_v90") or {}
    lines.extend(["", "## v9.0 Structural Occlusion Stress", ""])
    lines.append(f"- `available`: `{v90.get('available')}`")
    lines.append(f"- `status`: `{v90.get('status')}`")
    lines.append(f"- `row_count`: `{v90.get('row_count')}`")
    lines.append(f"- `metrics`: `{v90.get('metrics')}`")
    v92 = precheck.get("label_blind_hard_decoy_audit_v92") or {}
    lines.extend(["", "## v9.2 Label-Blind Hard-Decoy Audit", ""])
    lines.append(f"- `available`: `{v92.get('available')}`")
    lines.append(f"- `status`: `{v92.get('status')}`")
    lines.append(f"- `decision`: `{v92.get('decision')}`")
    lines.append(f"- `static_label_blind_check`: `{v92.get('static_label_blind_check')}`")
    lines.append(f"- `metrics`: `{v92.get('metrics')}`")
    v93 = precheck.get("kernel_shape_feature_probe_v93") or {}
    lines.extend(["", "## v9.3 Kernel-Shape Feature Probe", ""])
    lines.append(f"- `available`: `{v93.get('available')}`")
    lines.append(f"- `status`: `{v93.get('status')}`")
    lines.append(f"- `metrics`: `{v93.get('metrics')}`")
    v94 = precheck.get("post_patch_dependency_probe_v94") or {}
    lines.extend(["", "## v9.4 Post-Patch Dependency Probe", ""])
    lines.append(f"- `available`: `{v94.get('available')}`")
    lines.append(f"- `status`: `{v94.get('status')}`")
    lines.append(f"- `metrics`: `{v94.get('metrics')}`")
    summary = precheck.get("packet_summary") or {}
    lines.extend(["", "## Candidate Risk", ""])
    lines.append(f"- `targets_emitted`: `{summary.get('targets_emitted')}`")
    lines.append(f"- `known_used_ranked_first`: `{summary.get('known_used_ranked_first')}`")
    lines.append(f"- `known_used_any_topk`: `{summary.get('known_used_any_topk')}`")
    lines.append(f"- `danger_counts`: `{summary.get('danger_counts')}`")
    lines.append(f"- `role_counts`: `{summary.get('role_counts')}`")
    lines.extend(["", "## Consumption Protocol", ""])
    for item in precheck.get("consumption_protocol") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Actionable Candidates", ""])
    for cand in summary.get("actionable_candidate_names") or []:
        lines.append(f"- `{cand.get('name')}` (`{cand.get('count')}` hits)")
    lines.extend(["", "## Danger Candidates", ""])
    for cand in summary.get("danger_candidate_names") or []:
        lines.append(f"- `{cand.get('name')}` (`{cand.get('count')}` hits)")
    lines.extend(["", "## Warnings", ""])
    for warning in precheck.get("warnings") or []:
        lines.append(f"- {warning}")
    lines.extend(["", "## Top Targets", ""])
    for target in (summary.get("targets") or [])[:8]:
        lines.append(f"### `{target.get('target_name')}`")
        lines.append("")
        for cand in target.get("top_candidates", [])[:5]:
            warn = ", ".join(cand.get("warnings") or []) or "-"
            lines.append(f"- `{cand.get('name')}` ({cand.get('role')}; warnings: {warn})")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n")


def render_text(precheck: dict) -> str:
    lines = [
        f"  GNN precheck: {precheck.get('status')}",
        f"  artifact: {rel(DEFAULT_JSON)}",
        f"  packet: {(precheck.get('packet') or {}).get('path')}",
        "  use: premise/navigation context only; no theorem verdict",
    ]
    packet = precheck.get("packet") or {}
    if packet:
        lines.append(
            "  packet metrics: "
            f"best_val_hit@10={packet.get('best_val_hit10')} "
            f"epoch={packet.get('best_epoch')}"
        )
    summary = precheck.get("packet_summary") or {}
    if summary:
        lines.append(
            "  candidate risk: "
            f"danger_counts={summary.get('danger_counts')} "
            f"role_counts={summary.get('role_counts')}"
        )
        actionable = summary.get("actionable_candidate_names") or []
        if actionable:
            top = ", ".join(
                f"{row.get('name')}({row.get('count')})"
                for row in actionable[:5]
            )
            lines.append(f"  actionable candidates: {top}")
    graph = precheck.get("graph") or {}
    if graph:
        lines.append(
            "  graph guards: "
            f"missing_tags={graph.get('missing_tags')} thin_tags={graph.get('thin_tags')}"
        )
    v53 = precheck.get("guarded_filter_v53") or {}
    if v53.get("available"):
        metrics = v53.get("metrics") or {}
        raw = metrics.get("raw_profile") or {}
        filtered = metrics.get("filtered_profile") or {}
        lines.append(
            "  v5.3 guarded filter: "
            f"{v53.get('status')} "
            f"clean_actionability {raw.get('clean_actionable_fraction')}→"
            f"{filtered.get('clean_actionable_fraction')} "
            f"danger {raw.get('danger_fraction')}→{filtered.get('danger_fraction')}"
        )
        top = v53.get("top_actionable_candidates") or []
        if top:
            lines.append(
                "  v5.3 work queue: "
                + ", ".join(f"{row.get('name')}({row.get('count')})" for row in top[:5])
            )
    v54 = precheck.get("typed_symmetry_audit_v54") or {}
    if v54.get("available"):
        lines.append(
            "  v5.4 typed symmetry: "
            f"{v54.get('status')} "
            f"missing={v54.get('missing_clean_required_roles')} "
            f"wrong_equivariance={v54.get('wrong_equivariance_risks')} "
            f"collapse_risks={v54.get('collapse_risk_count')}"
        )
    v55 = precheck.get("typed_symmetry_canary_v55") or {}
    if v55.get("available"):
        perturb = v55.get("perturbations") or {}
        lines.append(
            "  v5.5 perturbation canary: "
            f"{v55.get('status')} "
            f"namespace={((perturb.get('namespace_prefix') or {}).get('role_preservation_rate'))} "
            f"binder={((perturb.get('binder_suffix') or {}).get('role_preservation_rate'))} "
            f"semantic={((perturb.get('semantic_alias') or {}).get('role_preservation_rate'))} "
            f"decision={((v55.get('roadmap_decision') or {}).get('v6_typed_symmetry_residual'))}"
        )
    v54r = precheck.get("typed_symmetry_audit_on_v56_top7") or {}
    if v54r.get("available"):
        lines.append(
            "  v5.4 on v5.6 repaired queue: "
            f"{v54r.get('status')} "
            f"missing={v54r.get('missing_clean_required_roles')} "
            f"wrong_equivariance={v54r.get('wrong_equivariance_risks')} "
            f"collapse_risks={v54r.get('collapse_risk_count')} "
            f"bridges={v54r.get('explicit_role_bridge_count')}"
        )
    v55r = precheck.get("typed_symmetry_canary_on_v56_top7") or {}
    if v55r.get("available"):
        perturb_r = v55r.get("perturbations") or {}
        lines.append(
            "  v5.5 on v5.6 repaired queue: "
            f"{v55r.get('status')} "
            f"semantic={((perturb_r.get('semantic_alias') or {}).get('role_preservation_rate'))}"
        )
    v56 = precheck.get("typed_role_repair_v56") or {}
    if v56.get("available"):
        repairs = ", ".join(
            row.get("name", "") for row in (v56.get("repair_candidates") or [])[:4]
        )
        lines.append(
            "  v5.6 typed-role repair: "
            f"{v56.get('status')} "
            f"repaired={v56.get('missing_roles_repaired')} "
            f"candidates={repairs}"
        )
    v57 = precheck.get("patch_attribution_v57") or {}
    if v57.get("available"):
        lines.append(
            "  v5.7 patch attribution: "
            f"{v57.get('status')} "
            f"rows={v57.get('rows')} "
            f"successful={v57.get('successful_attributions')}"
        )
    v60 = precheck.get("typed_symmetry_residual_contract_v60") or {}
    if v60.get("available"):
        decision = v60.get("architecture_decision") or {}
        lines.append(
            "  v6 typed-symmetry contract: "
            f"{v60.get('status')} "
            f"typed_residual={decision.get('typed_symmetry_residual')} "
            f"generic_e3={decision.get('generic_e3_equivariant_gnn')} "
            f"plain_gnn={decision.get('plain_gnn_from_scratch')}"
        )
    v61 = precheck.get("typed_obligation_hypergraph_contract_v61") or {}
    if v61.get("available"):
        readiness = v61.get("current_readiness") or {}
        lines.append(
            "  v6.1 typed-obligation hypergraph: "
            f"{v61.get('status')} "
            f"training_allowed={readiness.get('training_allowed')} "
            f"successful_attr={readiness.get('successful_patch_attributions')}"
        )
    v62 = precheck.get("typed_obligation_work_packet_v62") or {}
    if v62.get("available"):
        vacuums = ", ".join(row.get("name", "") for row in (v62.get("tactical_vacuums") or [])[:3])
        lines.append(
            "  v6.2 typed-obligation work packet: "
            f"{v62.get('status')} "
            f"training_allowed={v62.get('training_allowed')} "
            f"top_vacuums={vacuums}"
        )
    v64 = precheck.get("tri_arm_usefulness_pilot_v64") or {}
    if v64.get("available"):
        arms = v64.get("arms") or {}
        lines.append(
            "  v6.4 tri-arm pilot: "
            f"{v64.get('status')} "
            f"graph={((arms.get('graph_alone') or {}).get('pilot_credit'))} "
            f"gnn={((arms.get('gnn_alone') or {}).get('pilot_credit'))} "
            f"combo={((arms.get('gnn_plus_graph') or {}).get('pilot_credit'))}"
        )
    patch_attrs = precheck.get("compile_checked_patch_attributions") or []
    if patch_attrs:
        compile_checked = sum(1 for row in patch_attrs if row.get("compile_checked"))
        lines.append(
            "  compile-checked attributions: "
            f"{compile_checked}/{len(patch_attrs)} "
            + ", ".join(row.get("path", "").split("/")[-1] for row in patch_attrs)
        )
    v67 = precheck.get("gnn_roadmap_v67") or {}
    if v67.get("available"):
        lines.append(
            "  v6.7/v7 roadmap: "
            f"{v67.get('status')} "
            f"next={', '.join((v67.get('next_versions') or {}).keys())} "
            f"gpu_trigger_items={len(v67.get('gpu_trigger') or [])}"
        )
    harness = precheck.get("endpoint_occluded_harness_v67") or {}
    if harness.get("available"):
        lines.append(
            "  v6.7 endpoint-occluded harness: "
            f"{harness.get('status')} hit@3={harness.get('hit_at_3')}"
        )
    v68 = precheck.get("non_ns_role_map_canary_v68") or {}
    if v68.get("available"):
        lines.append(
            "  v6.8 non-NS role canary: "
            f"{v68.get('status')} substrates={len(v68.get('substrates_tested') or [])}"
        )
    v69 = precheck.get("non_ns_real_lean_canary_v69") or {}
    if v69.get("available"):
        lines.append(
            "  v6.9 real non-NS Lean canary: "
            f"{v69.get('status')} substrate={v69.get('substrate')} "
            f"role_hit_rate={v69.get('role_hit_rate')}"
        )
    v70 = precheck.get("non_ns_generated_patch_v70") or {}
    if v70.get("available"):
        lines.append(
            "  v7.0 non-NS generated patch: "
            f"{v70.get('status')} substrate={v70.get('substrate')} "
            f"compile={v70.get('compile_checked')}"
        )
    v71 = precheck.get("external_benchmark_intake_v71") or {}
    if v71.get("available"):
        lines.append(
            "  v7.1 external benchmark intake: "
            f"{v71.get('status')} root={v71.get('bench_root')}"
        )
    v72 = precheck.get("mathlibgraph_external_baseline_v72") or {}
    if v72.get("available"):
        lines.append(
            "  v7.2 MathlibGraph baseline: "
            f"{v72.get('status')} network_R@10={v72.get('network_r10')} "
            f"all_R@10={v72.get('all_features_r10')}"
        )
    v73 = precheck.get("scientific_yield_gate_v73") or {}
    if v73.get("available"):
        lines.append(
            "  v7.3 scientific-yield gate: "
            f"{v73.get('status')} gpu={v73.get('gpu_training_allowed')} "
            f"novelty={v73.get('novelty_claim_allowed')}"
        )
    v76 = precheck.get("leanrank_gated_residual_v76") or {}
    if v76.get("available"):
        lines.append(
            "  v7.6 LeanRank gated residual: "
            f"{v76.get('status')} best={v76.get('best_safe_policy')}"
        )
    v79 = precheck.get("repair_benchmark_seed_v79") or {}
    if v79.get("available"):
        lines.append(
            "  v7.9 repair benchmark seed: "
            f"{v79.get('status')} rows={v79.get('row_count')} "
            f"nonNS={v79.get('generated_non_ns_rows')}"
        )
    v80 = precheck.get("leanrank_bm25_gated_v80") or {}
    if v80.get("available"):
        metrics = v80.get("graph_top1_bm25_tail_metrics") or {}
        lines.append(
            "  v8.0 LeanRank BM25 gated eval: "
            f"{v80.get('status')} hit@1={metrics.get('hit@1')} "
            f"hit@10={metrics.get('hit@10')} mrr={metrics.get('mrr')}"
        )
    v81 = precheck.get("repair_router_protocol_v81") or {}
    if v81.get("available"):
        lines.append(
            "  v8.1 repair-router protocol: "
            f"{v81.get('status')} rows={v81.get('row_count')} "
            f"cheap@1={v81.get('cheap_baseline_success_at_1')} "
            f"typed@1={v81.get('typed_router_success_at_1')}"
        )
    v82 = precheck.get("actual_declaration_repair_pool_v82") or {}
    if v82.get("available"):
        metrics = v82.get("metrics") or {}
        lines.append(
            "  v8.2 actual declaration repair pool: "
            f"{v82.get('status')} lexical@7={metrics.get('lexical_hit_at_7')} "
            f"typed@7={metrics.get('typed_hit_at_7')}"
        )
    v83 = precheck.get("constrained_repair_queue_v83") or {}
    if v83.get("available"):
        metrics = v83.get("metrics") or {}
        lines.append(
            "  v8.3 constrained repair queue: "
            f"{v83.get('status')} constrained@7={metrics.get('constrained_hit_at_7')} "
            f"rank={metrics.get('constrained_mean_first_gold_rank')}"
        )
    v84 = precheck.get("hybrid_repair_router_v84") or {}
    if v84.get("available"):
        metrics = v84.get("metrics") or {}
        lines.append(
            "  v8.4 hybrid repair router: "
            f"{v84.get('status')} hybrid@1={metrics.get('hybrid_top1_gold')} "
            f"hybrid@7={metrics.get('hybrid_hit_at_7')} "
            f"rank={metrics.get('hybrid_mean_first_gold_rank')}"
        )
    v85 = precheck.get("literature_positioning_v85") or {}
    if v85.get("available"):
        lines.append(
            "  v8.5 literature positioning: "
            f"{v85.get('status')} sources={len(v85.get('sources') or [])}"
        )
    v88 = precheck.get("repair_router_alias_stress_v88") or {}
    if v88.get("available"):
        metrics = v88.get("metrics") or {}
        lines.append(
            "  v8.8 repair-router alias stress: "
            f"{v88.get('status')} identity@7={metrics.get('identity_hit_at_7')} "
            f"alias@7={metrics.get('semantic_alias_hit_at_7')} "
            f"anon@7={metrics.get('name_anonymized_hit_at_7')}"
        )
    v90 = precheck.get("repair_router_structural_occlusion_v90") or {}
    if v90.get("available"):
        metrics = v90.get("metrics") or {}
        lines.append(
            "  v9.0 structural occlusion stress: "
            f"{v90.get('status')} docless@7={metrics.get('docless_name_anonymized_hit_at_7')} "
            f"sig-erased@7={metrics.get('signature_names_erased_hit_at_7')} "
            f"role-alias@7={metrics.get('role_token_alias_signature_hit_at_7')}"
        )
    v92 = precheck.get("label_blind_hard_decoy_audit_v92") or {}
    if v92.get("available"):
        metrics = v92.get("metrics") or {}
        lines.append(
            "  v9.2 label-blind hard-decoy audit: "
            f"{v92.get('decision')} hybrid@7={metrics.get('hybrid_hit_at_7')} "
            f"lexical@7={metrics.get('lexical_hit_at_7')} "
            f"hybrid_mrr={metrics.get('hybrid_mrr')}"
        )
    v93 = precheck.get("kernel_shape_feature_probe_v93") or {}
    if v93.get("available"):
        metrics = v93.get("metrics") or {}
        lines.append(
            "  v9.3 kernel-shape feature probe: "
            f"{v93.get('status')} shape@7={metrics.get('shape_hit_at_7')} "
            f"combo@7={metrics.get('combo_hit_at_7')} "
            f"shape_mrr={metrics.get('shape_mrr')}"
        )
    v94 = precheck.get("post_patch_dependency_probe_v94") or {}
    if v94.get("available"):
        metrics = v94.get("metrics") or {}
        lines.append(
            "  v9.4 post-patch dependency probe: "
            f"{v94.get('status')} dep@7={metrics.get('dependency_hit_at_7')} "
            f"dep_mrr={metrics.get('dependency_mrr')}"
        )
    v102 = precheck.get("row_obligation_seeded_role_backtest_v102") or {}
    if v102.get("available"):
        metrics = v102.get("metrics") or {}
        lines.append(
            "  v10.2 row-obligation seeded role backtest: "
            f"{v102.get('status')} hit@7={metrics.get('hit_at_7')} "
            f"mrr={metrics.get('mrr')}"
        )
    v103 = precheck.get("nonbootstrap_interface_role_extractor_v103") or {}
    if v103.get("available"):
        metrics = v103.get("metrics") or {}
        lines.append(
            "  v10.3 non-bootstrap interface role extractor: "
            f"{v103.get('status')} hit@7={metrics.get('hit_at_7')} "
            f"mrr={metrics.get('mrr')}"
        )
    v104 = precheck.get("action_delta_type_probe_v104") or {}
    if v104.get("available"):
        metrics = v104.get("metrics") or {}
        lines.append(
            "  v10.4 action-delta type probe: "
            f"{v104.get('status')} hit@7={metrics.get('hit_at_7')} "
            f"mrr={metrics.get('mrr')} probes={metrics.get('emitted_probe_count')}"
        )
    v105 = precheck.get("metavar_action_delta_probe_v105") or {}
    if v105.get("available"):
        metrics = v105.get("metrics") or {}
        lines.append(
            "  v10.5 metavariable action-delta probe: "
            f"{v105.get('status')} hit@7={metrics.get('hit_at_7')} "
            f"mrr={metrics.get('mrr')} probes={metrics.get('emitted_probe_count')}"
        )
    v106 = precheck.get("antifailure_repair_router_v106") or {}
    if v106.get("available"):
        metrics = v106.get("metrics") or {}
        action = metrics.get("action_only") or {}
        mixed = metrics.get("mixed_antifailure") or {}
        lines.append(
            "  v10.6 anti-failure router: "
            f"action@7={action.get('hit_at_7')} action_mrr={action.get('mrr')} "
            f"mixed@7={mixed.get('hit_at_7')} mixed_mrr={mixed.get('mrr')}"
        )
    v107 = precheck.get("tactic_rewrite_delta_probe_v107") or {}
    if v107.get("available"):
        metrics = v107.get("metrics") or {}
        lines.append(
            "  v10.7 tactic rewrite/simp delta probe: "
            f"{v107.get('status')} hit@7={metrics.get('hit_at_7')} "
            f"mrr={metrics.get('mrr')} attempts={metrics.get('tactic_attempt_count')} "
            f"ok={metrics.get('ok_tactic_attempt_count')}"
        )
    v108 = precheck.get("combined_action_delta_router_v108") or {}
    if v108.get("available"):
        metrics = v108.get("metrics") or {}
        setcover = metrics.get("setcover_tail") or {}
        lines.append(
            "  v10.8 combined action-delta router: "
            f"{v108.get('status')} setcover@7={setcover.get('hit_at_7')} "
            f"setcover_mrr={setcover.get('mrr')} non_ns@7={setcover.get('non_ns_hit_at_7')}"
        )
    v109 = precheck.get("tactic_failure_taxonomy_probe_v109") or {}
    if v109.get("available"):
        metrics = v109.get("metrics") or {}
        lines.append(
            "  v10.9 tactic failure taxonomy: "
            f"{v109.get('status')} other_rate={metrics.get('other_failure_rate')} "
            f"classes={metrics.get('failure_class_counts')}"
        )
    v119 = precheck.get("expanded_action_bundle_router_v119") or {}
    if v119.get("available"):
        metrics = v119.get("metrics") or {}
        v115_7 = ((metrics.get("v115_expanded_affordance") or {}).get("7") or {})
        generic_7 = ((metrics.get("generic_fixed_action_order") or {}).get("7") or {})
        lines.append(
            "  v11.9 action-bundle router: "
            f"v115_budget7={v115_7.get('budget_success')} "
            f"generic_budget7={generic_7.get('budget_success')}"
        )
    v123 = precheck.get("full_goal_snapshot_witness_v123") or {}
    if v123.get("available"):
        metrics = v123.get("metrics") or {}
        strict = metrics.get("strict_snapshot") or {}
        sort_guard = metrics.get("strict_sort_guarded_snapshot") or {}
        lines.append(
            "  v12.3 full snapshot witness: "
            f"{v123.get('status')} strict_precision={strict.get('precision')} "
            f"strict_bundle@7={strict.get('bundle_success_at_7')} "
            f"sort_guard_precision={sort_guard.get('precision')} "
            f"sort_guard_bundle@7={sort_guard.get('bundle_success_at_7')}"
        )
    v124 = precheck.get("target_unit_audit_v124") or {}
    if v124.get("available"):
        metrics = v124.get("metrics") or {}
        lines.append(
            "  v12.4 target-unit audit: "
            f"{v124.get('status')} sort_rows={metrics.get('rows_with_sort_like_target')} "
            f"proof_rows={metrics.get('rows_with_proof_like_target')} "
            f"false_rows={metrics.get('v123_strict_false_positive_rows')}"
        )
    v125 = precheck.get("target_unit_repair_packet_v125") or {}
    if v125.get("available"):
        metrics = v125.get("metrics") or {}
        lines.append(
            "  v12.5 target-unit repair packet: "
            f"{v125.get('status')} repaired={metrics.get('repaired_row_count')} "
            f"exposed={metrics.get('repaired_rows_exposing_intended_obligation')} "
            f"sort_closures={metrics.get('total_sort_closure_count')}"
        )
    v126 = precheck.get("full_target_unit_rewrite_v126") or {}
    if v126.get("available"):
        metrics = v126.get("metrics") or {}
        lines.append(
            "  v12.6 full target-unit rewrite: "
            f"{v126.get('status')} rows={metrics.get('row_count')} "
            f"gold_success={metrics.get('gold_witness_success_count')} "
            f"sort_closures={metrics.get('total_sort_closure_count')}"
        )
    v127 = precheck.get("target_aware_policy_eval_v127") or {}
    if v127.get("available"):
        metrics = v127.get("metrics") or {}
        lines.append(
            "  v12.7 target-aware policy eval: "
            f"{v127.get('status')} generic10={metrics.get('generic_budget10_success_count')} "
            f"best10={metrics.get('best_target_aware_budget10')} "
            f"best25={metrics.get('best_target_aware_budget25')} "
            f"sort_closures={metrics.get('sort_closure_count')}"
        )
    v128 = precheck.get("policy_gap_decomposition_v128") or {}
    if v128.get("available"):
        metrics = v128.get("metrics") or {}
        lines.append(
            "  v12.8 policy gap decomposition: "
            f"{v128.get('status')} classes={metrics.get('class_counts')} "
            f"next={metrics.get('recommended_next_target')}"
        )
    v129 = precheck.get("compressed_affordance_policy_v129") or {}
    if v129.get("available"):
        metrics = v129.get("metrics") or {}
        lines.append(
            "  v12.9 compressed affordance policy: "
            f"{v129.get('status')} generic10={metrics.get('generic_budget10_success_count')} "
            f"best10={metrics.get('best_target_aware_budget10')} "
            f"best25={metrics.get('best_target_aware_budget25')} "
            f"sort_closures={metrics.get('sort_closure_count')}"
        )
    v130 = precheck.get("label_leakage_static_audit_v130") or {}
    if v130.get("available"):
        lines.append(
            "  v12.10 label/static leakage audit: "
            f"{v130.get('status')} pre_metric_hits={v130.get('pre_metric_prohibited_hit_count')} "
            f"temporal_risks={v130.get('temporal_context_risk_count')}"
        )
    for warning in precheck.get("warnings") or []:
        lines.append(f"  WARN: {warning}")
    for error in precheck.get("errors") or []:
        lines.append(f"  ERROR: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope",
        default=None,
        help="Optional RD tick scope. Non math/NS scopes skip cleanly.",
    )
    parser.add_argument(
        "--short",
        action="store_true",
        help="Compatibility flag for RD tick callers; output is already concise.",
    )
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--remote-cpu", type=Path, default=DEFAULT_REMOTE_CPU)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--max-targets", type=int, default=24)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--min-best-val-hit10", type=float, default=0.20)
    args = parser.parse_args()

    status, precheck = build_precheck(args)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(precheck, indent=2, sort_keys=True))
    write_markdown(precheck, args.out_md)
    print(render_text(precheck))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
