"""Read-only coverage audit for the LeanMill control-plane cleanup.

This module does not inspect proof results and does not influence proof search.
It answers a narrower maintenance question: for each cleanup roadmap item, do
the expected code artifacts exist and do the promoted RCA classes still point
to executable regression guards?
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ControlPlaneItem:
    item_id: str
    title: str
    artifact_paths: tuple[str, ...]
    regression_ids: tuple[str, ...]
    required_strings: tuple[tuple[str, str], ...] = ()


CONTROL_PLANE_ITEMS: tuple[ControlPlaneItem, ...] = (
    ControlPlaneItem(
        item_id="1",
        title="first_class_statement_identity",
        artifact_paths=(
            "src/ztare/leanmill/control_plane.py",
            "src/ztare/leanmill/solver/proof_cache.py",
            "src/ztare/leanmill/solver/no_good_store.py",
            "src/ztare/leanmill/solver/faithfulness_store.py",
            "src/ztare/leanmill/cache_metadata_backfill.py",
        ),
        regression_ids=(
            "no_good_statement_id_metadata",
            "faithfulness_statement_id_metadata",
        ),
        required_strings=(
            ("src/ztare/leanmill/cache_metadata_backfill.py", "leanmill.cache_metadata_backfill.v1"),
        ),
    ),
    ControlPlaneItem(
        item_id="2",
        title="one_typed_verdict_surface",
        artifact_paths=(
            "src/ztare/leanmill/control_plane.py",
            "src/ztare/leanmill/contracts/kernel.py",
            "src/ztare/leanmill/verdict_store.py",
            "src/ztare/formal/repl_compile.py",
        ),
        regression_ids=(
            "substrate_liveness_typed_verdicts",
            "statement_false_typed_verdict_surface",
            "governance_no_good_typed_verdict_surface",
        ),
        required_strings=(
            ("src/ztare/leanmill/contracts/kernel.py", "class SolveResult"),
        ),
    ),
    ControlPlaneItem(
        item_id="3",
        title="unified_falsify_routing",
        artifact_paths=(
            "src/ztare/leanmill/solver/conjecture.py",
            "src/ztare/leanmill/solver/solver_core.py",
            "src/ztare/leanmill/solver/no_good_store.py",
        ),
        regression_ids=(
            "stale_refutation_dropped_hypothesis",
            "falsify_probe_glob_single_door",
            "strategy_falsify_single_door",
            "statement_false_conflict_detection",
            "soft_refutation_not_confirmed_memory",
        ),
        required_strings=(
            ("src/ztare/leanmill/solver/solver_core.py", "leanmill.dag_move_dispatch_contract.v1"),
        ),
    ),
    ControlPlaneItem(
        item_id="4",
        title="cache_authority_separation",
        artifact_paths=(
            "src/ztare/leanmill/control_plane.py",
            "src/ztare/leanmill/solver/proof_cache.py",
            "src/ztare/leanmill/run_observability.py",
        ),
        regression_ids=(
            "cache_env_observability_matrix",
            "proof_flow_observability_timeline",
        ),
    ),
    ControlPlaneItem(
        item_id="5",
        title="transactional_substrate_mutation",
        artifact_paths=(
            "src/ztare/leanmill/solver/family_lemma_library.py",
            "tests/test_bank_transactional.py",
        ),
        regression_ids=(
            "transactional_bank_rollback",
            "bank_candidate_reverify_before_live_swap",
            "reorder_fallback_rollback",
            "substrate_mutation_receipt",
        ),
    ),
    ControlPlaneItem(
        item_id="6",
        title="run_manifest",
        artifact_paths=(
            "src/ztare/leanmill/solver/autoformalize_notes.py",
            "src/ztare/leanmill/solver/autoformalize.py",
            "src/ztare/leanmill/run_diagnostics.py",
            "src/ztare/leanmill/run_observability.py",
        ),
        regression_ids=(
            "run_manifest_authority_modes",
            "run_manifest_code_fingerprints",
            "diagnostics_reads_run_manifest",
            "observability_layering_no_factory_bypass",
        ),
        required_strings=(
            ("src/ztare/leanmill/solver/autoformalize_notes.py", "leanmill.launch_config.v1"),
            ("src/ztare/leanmill/solver/autoformalize_notes.py", "launch_snapshot_sha256"),
            ("src/ztare/leanmill/solver/autoformalize.py", "class AutoformalizeSolveConfig"),
        ),
    ),
    ControlPlaneItem(
        item_id="7",
        title="memory_to_regression",
        artifact_paths=(
            "src/ztare/leanmill/memory_regressions.py",
            "tests/test_leanmill_agentic_invariants.py",
        ),
        regression_ids=(
            "exact_nl_verbatim_reference_reuse",
            "cold_dependency_resolution_is_inconclusive",
            "warm_env_content_identity",
            "markdown_named_banked_lemma_reuse",
            "triviality_targets_multidecl_theorem_signature",
            "cheap_triviality_probe_bounded_tactics",
        ),
    ),
    ControlPlaneItem(
        item_id="8",
        title="definition_api_contract",
        artifact_paths=(
            "src/ztare/leanmill/definition_contract.py",
            "src/ztare/leanmill/library_delta.py",
            "src/ztare/leanmill/run_diagnostics.py",
        ),
        regression_ids=(
            "definition_api_receipt",
            "definition_api_summary_in_diagnostics",
            "library_delta_receipt",
            "library_delta_summary_in_diagnostics",
        ),
    ),
    ControlPlaneItem(
        item_id="9",
        title="unified_run_observability",
        artifact_paths=(
            "src/ztare/leanmill/run_observability.py",
            "scripts/public/control/leanmill/factory_intelligence.py",
        ),
        regression_ids=(
            "observability_bundle_joins_ledgers",
            "cache_env_observability_matrix",
            "proof_flow_observability_timeline",
            "observability_layering_no_factory_bypass",
        ),
        required_strings=(
            ("src/ztare/leanmill/run_observability.py", "leanmill.operator_readout.v1"),
            ("scripts/public/control/leanmill/factory_intelligence.py", "run_observability_operator_bottleneck"),
        ),
    ),
)


P0_OBJECTIVE_ITEMS_1_7: tuple[ControlPlaneItem, ...] = (
    ControlPlaneItem(
        item_id="1",
        title="first_class_statement_identity",
        artifact_paths=(
            "src/ztare/leanmill/control_plane.py",
            "src/ztare/leanmill/solver/proof_cache.py",
            "src/ztare/leanmill/solver/no_good_store.py",
            "src/ztare/leanmill/solver/faithfulness_store.py",
            "src/ztare/leanmill/cache_metadata_backfill.py",
        ),
        regression_ids=(
            "no_good_statement_id_metadata",
            "faithfulness_statement_id_metadata",
        ),
        required_strings=(
            ("src/ztare/leanmill/control_plane.py", "class StatementId"),
            ("src/ztare/leanmill/solver/proof_cache.py", '"statement_id": sid.to_json()'),
            ("src/ztare/leanmill/solver/no_good_store.py", "statement_id"),
            ("src/ztare/leanmill/solver/faithfulness_store.py", "statement_id"),
        ),
    ),
    ControlPlaneItem(
        item_id="2",
        title="one_verdict_type_for_solver_outcomes",
        artifact_paths=(
            "src/ztare/leanmill/control_plane.py",
            "src/ztare/leanmill/verdict_store.py",
            "src/ztare/leanmill/contracts/kernel.py",
            "src/ztare/formal/repl_compile.py",
        ),
        regression_ids=(
            "substrate_liveness_typed_verdicts",
            "statement_false_typed_verdict_surface",
            "governance_no_good_typed_verdict_surface",
        ),
        required_strings=(
            ("src/ztare/leanmill/control_plane.py", "class VerdictKind"),
            ("src/ztare/leanmill/control_plane.py", "SUBSTRATE_UNAVAILABLE"),
            ("src/ztare/leanmill/verdict_store.py", "leanmill.verdict.v1"),
            ("src/ztare/leanmill/contracts/kernel.py", "class SolveResult"),
        ),
    ),
    ControlPlaneItem(
        item_id="3",
        title="unified_falsify_routing",
        artifact_paths=(
            "src/ztare/leanmill/solver/conjecture.py",
            "src/ztare/leanmill/solver/solver_core.py",
            "src/ztare/leanmill/solver/no_good_store.py",
            "src/ztare/leanmill/state_convergence.py",
        ),
        regression_ids=(
            "stale_refutation_dropped_hypothesis",
            "falsify_probe_glob_single_door",
            "strategy_falsify_single_door",
            "statement_false_conflict_detection",
            "soft_refutation_not_confirmed_memory",
        ),
        required_strings=(
            ("src/ztare/leanmill/solver/conjecture.py", "def adjudicate_statement_false_verdict"),
            ("src/ztare/leanmill/solver/conjecture.py", "robust_probe_glob"),
            ("src/ztare/leanmill/solver/solver_core.py", "leanmill.dag_move_dispatch_contract.v1"),
        ),
    ),
    ControlPlaneItem(
        item_id="4",
        title="separate_affordance_caches_from_proof_credit_caches",
        artifact_paths=(
            "src/ztare/leanmill/control_plane.py",
            "src/ztare/leanmill/solver/proof_cache.py",
            "src/ztare/leanmill/run_observability.py",
        ),
        regression_ids=(
            "cache_env_observability_matrix",
            "proof_flow_observability_timeline",
            "observability_layering_no_factory_bypass",
        ),
        required_strings=(
            ("src/ztare/leanmill/control_plane.py", "class CacheAuthority"),
            ("src/ztare/leanmill/run_observability.py", "leanmill.cache_observability.v1"),
            ("src/ztare/leanmill/run_observability.py", "proof_credit_reuse"),
            ("src/ztare/leanmill/run_observability.py", "near_complete_seed"),
        ),
    ),
    ControlPlaneItem(
        item_id="5",
        title="transactional_substrate_mutation",
        artifact_paths=(
            "src/ztare/leanmill/solver/family_lemma_library.py",
            "tests/test_bank_transactional.py",
        ),
        regression_ids=(
            "transactional_bank_rollback",
            "bank_candidate_reverify_before_live_swap",
            "reorder_fallback_rollback",
            "substrate_mutation_receipt",
        ),
        required_strings=(
            ("src/ztare/leanmill/solver/family_lemma_library.py", "def _commit_if_candidate_reverifies"),
            ("src/ztare/leanmill/solver/family_lemma_library.py", "leanmill.substrate_mutation.v1"),
            ("tests/test_bank_transactional.py", "test_failed_bank_reverifies_candidate_before_live_swap"),
        ),
    ),
    ControlPlaneItem(
        item_id="6",
        title="run_manifest_instead_of_env_var_archaeology",
        artifact_paths=(
            "src/ztare/leanmill/solver/autoformalize_notes.py",
            "src/ztare/leanmill/solver/autoformalize.py",
            "src/ztare/leanmill/run_diagnostics.py",
            "src/ztare/leanmill/run_observability.py",
        ),
        regression_ids=(
            "run_manifest_authority_modes",
            "run_manifest_code_fingerprints",
            "diagnostics_reads_run_manifest",
            "observability_layering_no_factory_bypass",
        ),
        required_strings=(
            ("src/ztare/leanmill/solver/autoformalize_notes.py", "run_manifest.json"),
            ("src/ztare/leanmill/solver/autoformalize_notes.py", "launch_snapshot_sha256"),
            ("src/ztare/leanmill/solver/autoformalize_notes.py", "leanmill.launch_config.v1"),
            ("src/ztare/leanmill/solver/autoformalize.py", "class AutoformalizeSolveConfig"),
        ),
    ),
    ControlPlaneItem(
        item_id="7",
        title="memory_to_regression_pipeline",
        artifact_paths=(
            "src/ztare/leanmill/memory_regressions.py",
            "tests/test_leanmill_agentic_invariants.py",
            "tests/test_bank_transactional.py",
        ),
        regression_ids=(
            "stale_refutation_dropped_hypothesis",
            "exact_nl_verbatim_reference_reuse",
            "falsify_probe_glob_single_door",
            "reorder_fallback_rollback",
            "cold_dependency_resolution_is_inconclusive",
            "transactional_bank_rollback",
            "bank_candidate_reverify_before_live_swap",
            "warm_env_content_identity",
            "substrate_mutation_receipt",
            "control_plane_audit_covers_roadmap",
        ),
        required_strings=(
            ("src/ztare/leanmill/memory_regressions.py", "REGRESSIONS"),
            ("tests/test_leanmill_agentic_invariants.py", "test_memory_regression_registry_points_to_executable_guards"),
            ("tests/test_bank_transactional.py", "test_bank_reverts_when_reorder_and_eof_fallback_both_fail"),
        ),
    ),
)


P0_OBJECTIVE_ITEMS_8_9: tuple[ControlPlaneItem, ...] = (
    ControlPlaneItem(
        item_id="8",
        title="definition_api_contract_layer",
        artifact_paths=(
            "src/ztare/leanmill/definition_contract.py",
            "src/ztare/leanmill/library_delta.py",
            "src/ztare/leanmill/run_diagnostics.py",
            "tests/test_leanmill_agentic_invariants.py",
        ),
        regression_ids=(
            "definition_api_receipt",
            "definition_api_summary_in_diagnostics",
            "library_delta_receipt",
            "library_delta_summary_in_diagnostics",
        ),
        required_strings=(
            ("src/ztare/leanmill/definition_contract.py", "leanmill.definition_api_receipt.v1"),
            ("src/ztare/leanmill/library_delta.py", "leanmill.library_delta_receipt.v1"),
            ("src/ztare/leanmill/run_diagnostics.py", "leanmill.definition_api_summary.v1"),
            ("src/ztare/leanmill/run_diagnostics.py", "leanmill.library_delta_summary.v1"),
            ("tests/test_leanmill_agentic_invariants.py", "test_definition_api_receipt_surfaces_reuse_risks"),
            ("tests/test_leanmill_agentic_invariants.py", "test_library_delta_receipt_surfaces_api_graph_risks"),
        ),
    ),
    ControlPlaneItem(
        item_id="9",
        title="unified_per_run_observability_read_model",
        artifact_paths=(
            "src/ztare/leanmill/run_observability.py",
            "scripts/public/control/leanmill/factory_intelligence.py",
            "tests/test_leanmill_agentic_invariants.py",
            "tests/formal/test_factory_intelligence_golden.py",
        ),
        regression_ids=(
            "observability_bundle_joins_ledgers",
            "cache_env_observability_matrix",
            "proof_flow_observability_timeline",
            "observability_layering_no_factory_bypass",
        ),
        required_strings=(
            ("src/ztare/leanmill/run_observability.py", "leanmill.run_observability_bundle.v1"),
            ("src/ztare/leanmill/run_observability.py", "leanmill.operator_readout.v1"),
            ("src/ztare/leanmill/run_observability.py", "proof_flows"),
            ("scripts/public/control/leanmill/factory_intelligence.py", "build_observability_bundle"),
            ("scripts/public/control/leanmill/factory_intelligence.py", "run_observability_operator_bottleneck"),
            ("tests/test_leanmill_agentic_invariants.py", "test_run_observability_bundle_joins_existing_ledgers"),
        ),
    ),
)


AXIOM_PACK_LANE_ITEMS: tuple[ControlPlaneItem, ...] = (
    ControlPlaneItem(
        item_id="L3",
        title="axiom_pack_theory_induction_lane",
        artifact_paths=(
            "src/ztare/leanmill/axiom_pack.py",
            "src/ztare/leanmill/contracts/proof_gap.py",
            "src/ztare/leanmill/formalization_admission.py",
            "src/ztare/leanmill/typed_axiom_proposal.py",
            "src/ztare/leanmill/theory_ir.py",
            "src/ztare/leanmill/finite_model.py",
            "src/ztare/leanmill/axiom_yield.py",
            "src/ztare/leanmill/axiom_lowering.py",
            "src/ztare/leanmill/axiom_authority.py",
            "src/ztare/leanmill/axiom_pack_band.py",
            "src/ztare/leanmill/axiom_pack_orchestration.py",
            "src/ztare/leanmill/agent_tools.py",
            "src/ztare/leanmill/workbench_actions.py",
            "ztare_proofs/leanmill-formalizations/blueprints/priority_uncrossed_order_axiom_pack.json",
            "src/ztare/leanmill/run_observability.py",
            "docs/internal/roadmap_backlog_2026_06_17.md",
            "docs/concepts/leanmill_architecture.md",
            "tests/test_proof_gap_contract.py",
            "tests/test_typed_axiom_proposal.py",
            "tests/test_axiom_pack_typed_isomorphism.py",
            "tests/test_axiom_pack_semantic_governance.py",
            "tests/test_axiom_pack_band.py",
            "tests/test_axiom_pack_trial_workbench_action.py",
            "tests/test_axiom_pack_orchestration.py",
        ),
        regression_ids=(),
        required_strings=(
            ("src/ztare/leanmill/axiom_pack.py", "leanmill.axiom_pack.v1"),
            ("src/ztare/leanmill/axiom_pack.py", "leanmill.axiom_pack_blueprint.v1"),
            ("src/ztare/leanmill/axiom_pack.py", "theorem_campaign_consumption_gate"),
            ("src/ztare/leanmill/axiom_pack.py", "proof_credit_eligible"),
            ("src/ztare/leanmill/axiom_pack.py", "theorem_campaign_admissible"),
            ("src/ztare/leanmill/axiom_pack.py", "verify_typed_blueprint_construction"),
            ("src/ztare/leanmill/contracts/proof_gap.py", "leanmill.proof_gap_receipt.v1"),
            ("src/ztare/leanmill/contracts/proof_gap.py", "def observe_admitted_proof_gap"),
            ("src/ztare/leanmill/contracts/proof_gap.py", "def evaluate_axiom_pack_escalation"),
            ("src/ztare/leanmill/formalization_admission.py", "class FormalizationAdmission"),
            ("src/ztare/leanmill/typed_axiom_proposal.py", "leanmill.typed_axiom_proposal.v1"),
            ("src/ztare/leanmill/typed_axiom_proposal.py", "semantic_fidelity_checker"),
            ("src/ztare/leanmill/theory_ir.py", "leanmill.first_order_ir.v1"),
            ("src/ztare/leanmill/axiom_yield.py", "leanmill.axiom_shadow_task_manifest.v1"),
            ("src/ztare/leanmill/axiom_yield.py", "def evaluate_shadow_ab"),
            ("src/ztare/leanmill/axiom_lowering.py", "leanmill.axiom_pack_lean_lowering.v1"),
            ("src/ztare/leanmill/axiom_authority.py", "leanmill.axiom_pack_ratification.v2"),
            ("src/ztare/leanmill/axiom_authority.py", "typed_candidate_evidence_missing"),
            ("src/ztare/leanmill/axiom_pack_band.py", "leanmill.axiom_pack_band_pilot.v1"),
            ("src/ztare/leanmill/axiom_pack_band.py", "leanmill.axiom_pack_band_preregistration.v1"),
            ("src/ztare/leanmill/axiom_pack_band.py", "def build_band_preregistration"),
            ("src/ztare/leanmill/axiom_pack_orchestration.py", "leanmill.axiom_pack_typed_orchestration.v1"),
            ("src/ztare/leanmill/axiom_pack_orchestration.py", "def orchestrate_typed_axiom_proposals"),
            ("src/ztare/leanmill/agent_tools.py", "structural-isomorphism move card"),
            ("src/ztare/leanmill/agent_tools.py", "ztare.research_director.research_isomorphism"),
            ("src/ztare/leanmill/workbench_actions.py", "prepare-axiom-pack-trial"),
            ("src/ztare/leanmill/run_observability.py", "leanmill.axiom_pack_observability.v1"),
            ("ztare_proofs/leanmill-formalizations/blueprints/priority_uncrossed_order_axiom_pack.json", "leanmill.axiom_pack_blueprint.v1"),
            ("docs/internal/roadmap_backlog_2026_06_17.md", "Axiom-pack discovery stress lane"),
            ("docs/internal/roadmap_backlog_2026_06_17.md", "cheap receipts first"),
            ("docs/internal/roadmap_backlog_2026_06_17.md", "Goodhart A/B"),
            ("docs/concepts/leanmill_architecture.md", "AxiomPack theory-induction control plane"),
            ("docs/concepts/leanmill_architecture.md", "content-bound ProofGapReceipt"),
            ("docs/concepts/leanmill_architecture.md", "TypedAxiomProposal"),
            ("docs/concepts/leanmill_architecture.md", "budget-matched shadow A/B"),
            ("docs/concepts/leanmill_architecture.md", "conditional Lean lowering"),
            ("tests/test_proof_gap_contract.py", "test_observer_solves_exact_admission_and_preserves_solver_evidence"),
            ("tests/test_typed_axiom_proposal.py", "test_typed_proposal_admits_only_after_signed_fidelity_review"),
            ("tests/test_axiom_pack_typed_isomorphism.py", "test_post_construction_formula_tamper_is_blocked_before_pack_generation"),
            ("tests/test_axiom_pack_semantic_governance.py", "test_agent_origin_ratification_replays_typed_proposal_evidence"),
            ("tests/test_axiom_pack_band.py", "test_band_proposer_brief_excludes_every_operator_only_surface"),
            ("tests/test_axiom_pack_band.py", "test_band_preregistration_separates_signed_operator_packet_and_proposer_view"),
            ("tests/test_axiom_pack_trial_workbench_action.py", "test_execution_rejects_bytes_changed_after_preview"),
            ("tests/test_axiom_pack_orchestration.py", "test_orchestration_verifies_manifest_before_typed_checker"),
        ),
    ),
)


def _audit_items(items_spec: tuple[ControlPlaneItem, ...], root: Path, known_regressions: set[str]) -> list[dict[str, Any]]:
    items = []
    for item in items_spec:
        missing_artifacts = [p for p in item.artifact_paths if not (root / p).exists()]
        missing_regressions = [rid for rid in item.regression_ids if rid not in known_regressions]
        missing_required_strings: list[str] = []
        for rel, needle in item.required_strings:
            path = root / rel
            if not path.exists():
                missing_required_strings.append(f"{rel}:{needle}")
                continue
            if needle not in path.read_text(encoding="utf-8", errors="replace"):
                missing_required_strings.append(f"{rel}:{needle}")
        items.append({
            "item_id": item.item_id,
            "title": item.title,
            "artifact_paths": list(item.artifact_paths),
            "regression_ids": list(item.regression_ids),
            "required_strings": [f"{rel}:{needle}" for rel, needle in item.required_strings],
            "missing_artifacts": missing_artifacts,
            "missing_regression_ids": missing_regressions,
            "missing_required_strings": missing_required_strings,
            "ok": not missing_artifacts and not missing_regressions and not missing_required_strings,
        })
    return items


def audit_control_plane(repo_root: str | Path = REPO) -> dict[str, Any]:
    root = Path(repo_root)
    from ztare.leanmill.memory_regressions import REGRESSIONS, validate_memory_regressions

    known_regressions = {r.id for r in REGRESSIONS}
    executable_guard_gaps = validate_memory_regressions(root)
    items = _audit_items(CONTROL_PLANE_ITEMS, root, known_regressions)
    objective_items = _audit_items(P0_OBJECTIVE_ITEMS_1_7, root, known_regressions)
    objective_8_9_items = _audit_items(P0_OBJECTIVE_ITEMS_8_9, root, known_regressions)
    axiom_pack_items = _audit_items(AXIOM_PACK_LANE_ITEMS, root, known_regressions)
    objective_ok = all(i["ok"] for i in objective_items) and not executable_guard_gaps
    objective_8_9_ok = all(i["ok"] for i in objective_8_9_items) and not executable_guard_gaps
    axiom_pack_ok = all(i["ok"] for i in axiom_pack_items)
    return {
        "schema": "leanmill.control_plane_audit.v1",
        "item_count": len(items),
        "ok": all(i["ok"] for i in items) and objective_ok and objective_8_9_ok and axiom_pack_ok and not executable_guard_gaps,
        "items": items,
        "objective_1_7": {
            "schema": "leanmill.control_plane_objective_1_7.v1",
            "item_count": len(objective_items),
            "ok": objective_ok,
            "items": objective_items,
        },
        "objective_8_9": {
            "schema": "leanmill.control_plane_objective_8_9.v1",
            "item_count": len(objective_8_9_items),
            "ok": objective_8_9_ok,
            "items": objective_8_9_items,
        },
        "axiom_pack_lane": {
            "schema": "leanmill.axiom_pack_lane_audit.v1",
            "item_count": len(axiom_pack_items),
            "ok": axiom_pack_ok,
            "items": axiom_pack_items,
        },
        "executable_guard_gaps": executable_guard_gaps,
    }


def _main() -> int:
    payload = audit_control_plane()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_main())
