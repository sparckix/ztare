"""Executable index of LeanMill RCA memories that have regression guards.

The memory files stay narrative. This module is the small machine-readable
bridge from a recurring failure class to the test that prevents it from
returning.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class MemoryRegression:
    id: str
    memory_slug: str
    failure_class: str
    test_file: str
    test_name: str


REGRESSIONS: tuple[MemoryRegression, ...] = (
    MemoryRegression(
        id="stale_refutation_dropped_hypothesis",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="same-name refutation of a weaker proposition reused for a strengthened target",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_refutation_reuse_requires_current_statement",
    ),
    MemoryRegression(
        id="falsify_probe_glob_single_door",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="hand-rolled robust-probe glob missed a truncated target probe",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_falsify_refutation_reuse_uses_canonical_robust_probe_glob",
    ),
    MemoryRegression(
        id="exact_nl_verbatim_reference_reuse",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="semantic reference reused old statement verbatim after an NL strengthening",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_reference_reuse_verbatim_requires_exact_nl_match",
    ),
    MemoryRegression(
        id="cold_dependency_resolution_is_inconclusive",
        memory_slug="reference_substrate_noncompile_silent_campaign_death",
        failure_class="cold compile could not resolve dependencies but was treated as substrate broken",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_cold_compile_dependency_resolution_failure_is_inconclusive",
    ),
    MemoryRegression(
        id="transactional_bank_rollback",
        memory_slug="reference_gale_substrate_death_bank_order_depfloor",
        failure_class="failed bank mutation left substrate bytes changed",
        test_file="tests/test_bank_transactional.py",
        test_name="test_failed_bank_is_byte_identical",
    ),
    MemoryRegression(
        id="bank_candidate_reverify_before_live_swap",
        memory_slug="reference_gale_substrate_death_bank_order_depfloor",
        failure_class="bank reverify exposed uncommitted candidate bytes through the live substrate file",
        test_file="tests/test_bank_transactional.py",
        test_name="test_failed_bank_reverifies_candidate_before_live_swap",
    ),
    MemoryRegression(
        id="reorder_fallback_rollback",
        memory_slug="reference_gale_substrate_death_bank_order_depfloor",
        failure_class="bank reorder/fallback failure did not restore original bytes",
        test_file="tests/test_bank_transactional.py",
        test_name="test_bank_reverts_when_reorder_and_eof_fallback_both_fail",
    ),
    MemoryRegression(
        id="warm_env_content_identity",
        memory_slug="reference_run_scratch_isolation_path_splitbrain",
        failure_class="warm env cache keyed by mtime/size without content identity",
        test_file="tests/test_bank_transactional.py",
        test_name="test_campaign_file_env_cache_key_includes_content_identity",
    ),
    MemoryRegression(
        id="run_manifest_authority_modes",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="launch state inferred from logs/env instead of a run manifest",
        test_file="tests/test_leanmill_cli.py",
        test_name="test_run_manifest_records_launch_authority_modes",
    ),
    MemoryRegression(
        id="run_manifest_code_fingerprints",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="run manifest carried git head but not dirty-worktree source fingerprints",
        test_file="tests/test_leanmill_cli.py",
        test_name="test_run_manifest_records_launch_authority_modes",
    ),
    MemoryRegression(
        id="observability_layering_no_factory_bypass",
        memory_slug="feedback_frustration_diagnosis",
        failure_class="factory intelligence rebuilt run RCA instead of consuming the unified observability bundle",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_observability_layering_no_factory_bypass",
    ),
    MemoryRegression(
        id="control_plane_audit_covers_roadmap",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="control-plane cleanup coverage was inferred from memory instead of an executable audit",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_control_plane_audit_covers_roadmap",
    ),
    MemoryRegression(
        id="diagnostics_reads_run_manifest",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="diagnostics lost launch authority state when attempts DB/log state was missing",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_run_diagnostics_reads_run_manifest_even_when_attempts_db_missing",
    ),
    MemoryRegression(
        id="substrate_liveness_typed_verdicts",
        memory_slug="reference_env_parity_single_door_reverted_noncompile",
        failure_class="substrate liveness RCA emitted prose without typed unavailable/broken verdicts",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_substrate_liveness_emits_typed_verdicts",
    ),
    MemoryRegression(
        id="observability_bundle_joins_ledgers",
        memory_slug="feedback_frustration_diagnosis",
        failure_class="RCA required manual grep across disconnected LeanMill telemetry sources",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_run_observability_bundle_joins_existing_ledgers",
    ),
    MemoryRegression(
        id="cache_env_observability_matrix",
        memory_slug="feedback_frustration_diagnosis",
        failure_class="cache and env-parity RCA lacked a phase/environment transition read model",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_run_observability_bundle_joins_existing_ledgers",
    ),
    MemoryRegression(
        id="proof_flow_observability_timeline",
        memory_slug="feedback_frustration_diagnosis",
        failure_class="RCA could not follow one proof target across attempts, verdicts, banking, and caches",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_run_observability_bundle_joins_existing_ledgers",
    ),
    MemoryRegression(
        id="statement_false_conflict_detection",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="confirmed statement_false refutation was not treated as a proved/refuted convergence conflict",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_state_convergence_conflicts_include_statement_false",
    ),
    MemoryRegression(
        id="statement_false_typed_verdict_surface",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="statement_false no-good recorded without a typed refuted verdict row",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_no_good_statement_false_emits_typed_refuted_verdict",
    ),
    MemoryRegression(
        id="strategy_falsify_single_door",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="strategist falsify/corroborate accepted ¬G outside the shared verdict/memo/no-good door",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_strategy_falsify_uses_shared_statement_false_gate",
    ),
    MemoryRegression(
        id="governance_no_good_typed_verdict_surface",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="confirmed governance no-good recorded without a typed rejected verdict row",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_no_good_governance_classes_emit_typed_rejected_verdict",
    ),
    MemoryRegression(
        id="no_good_statement_id_metadata",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="no-good ledger row lacked first-class statement identity metadata",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_no_good_rows_carry_statement_id_and_legacy_rows_still_load",
    ),
    MemoryRegression(
        id="faithfulness_statement_id_metadata",
        memory_slug="feedback_interface_debt_silent_default",
        failure_class="faithfulness correspondence row lacked first-class statement identity metadata",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_faithfulness_rows_carry_statement_id_and_legacy_rows_still_load",
    ),
    MemoryRegression(
        id="substrate_mutation_receipt",
        memory_slug="reference_env_parity_single_door_reverted_noncompile",
        failure_class="banking mutation lacked typed before/after diagnostics",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_bank_attempts_emit_typed_mutation_receipt",
    ),
    MemoryRegression(
        id="definition_api_receipt",
        memory_slug="reference_representation_dependent_def_weakening_class",
        failure_class="closed artifact lacked a reusable definition/API modeling receipt",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_definition_api_receipt_surfaces_reuse_risks",
    ),
    MemoryRegression(
        id="definition_api_summary_in_diagnostics",
        memory_slug="reference_representation_dependent_def_weakening_class",
        failure_class="definition/API receipt existed but was invisible in run diagnostics",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_run_diagnostics_reads_run_manifest_even_when_attempts_db_missing",
    ),
    MemoryRegression(
        id="library_delta_receipt",
        memory_slug="reference_representation_dependent_def_weakening_class",
        failure_class="kernel-checked artifact lacked declaration/API graph telemetry for review",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_library_delta_receipt_surfaces_api_graph_risks",
    ),
    MemoryRegression(
        id="library_delta_summary_in_diagnostics",
        memory_slug="reference_representation_dependent_def_weakening_class",
        failure_class="library-delta receipt existed but was invisible in run diagnostics",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_run_diagnostics_reads_run_manifest_even_when_attempts_db_missing",
    ),
    MemoryRegression(
        id="campaign_scope_citable_in_scope",
        memory_slug="reference_campaign_substrate_env_crossproc_zero_closures",
        failure_class="notes advertised a citable lemma that was absent from compile scope",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_campaign_probe_assembler_citable_in_scope",
    ),
    MemoryRegression(
        id="markdown_named_banked_lemma_reuse",
        memory_slug="reference_campaign_substrate_env_crossproc_zero_closures",
        failure_class="blueprint lemma named an existing substrate theorem with Markdown code syntax but reuse missed it",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_banked_lemma_reuse_skips_already_proven",
    ),
    MemoryRegression(
        id="soft_refutation_not_confirmed_memory",
        memory_slug="reference_gale_false_flagship_theorem_falsify_bridge",
        failure_class="soft statement-false reformulation hint was persisted as confirmed no-good memory",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_soft_refutation_does_not_pollute_statement_false_memory",
    ),
    MemoryRegression(
        id="triviality_targets_multidecl_theorem_signature",
        memory_slug="reference_double_entry_multidecl_triviality_false_reject",
        failure_class="multi-decl formalization rejected because triviality risk detection inspected the leading definition",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_default_triviality_risk_detector_targets_theorem_in_multidecl",
    ),
    MemoryRegression(
        id="cheap_triviality_probe_bounded_tactics",
        memory_slug="reference_double_entry_multidecl_triviality_false_reject",
        failure_class="cheap non-triviality probe drifted into expensive proof search tactics",
        test_file="tests/test_leanmill_agentic_invariants.py",
        test_name="test_default_triviality_single_theorem_uses_bounded_cheap_tactics",
    ),
)


def validate_memory_regressions(repo_root: str | Path) -> list[str]:
    root = Path(repo_root)
    missing: list[str] = []
    for reg in REGRESSIONS:
        path = root / reg.test_file
        if not path.exists():
            missing.append(f"{reg.id}: missing file {reg.test_file}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not re.search(rf"(?m)^def\s+{re.escape(reg.test_name)}\s*\(", text):
            missing.append(f"{reg.id}: missing test {reg.test_file}::{reg.test_name}")
    return missing
