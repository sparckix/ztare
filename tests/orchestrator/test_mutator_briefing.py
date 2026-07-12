from __future__ import annotations

from pathlib import Path
import json

from ztare.orchestrator import mutator_briefing
from ztare.orchestrator.briefing_providers.structural_transport import (
    StructuralTransportProvider,
)
from ztare.orchestrator.briefing_providers.embedding_history import (
    EmbeddingHistoryProvider,
)
from ztare.orchestrator.briefing_providers.worldmodel_committee import (
    WorldmodelCommitteeProvider,
)
from ztare.orchestrator.briefing_providers.leanmill_proof_jobs import (
    LeanMillProofJobsProvider,
)
from ztare.orchestrator.briefing_providers.leaf_workbench import (
    LeafWorkbenchProvider,
)
from ztare.orchestrator.briefing_providers.strategy_experiments import (
    StrategyExperimentsProvider,
)
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
    MutatorBriefing,
    _middle_elide_fragment,
    render_default_briefing_context,
)
from ztare.common.operator_proposal_contract import family_sha


class RaisingProvider(BriefingProvider):
    name = "raising_provider"
    priority = 10
    tier = 0

    def applies(self, ctx: BriefingContext) -> bool:
        raise RuntimeError("fixture applies failure")

    def fragment(self, ctx: BriefingContext) -> str:
        return "unreachable\n"


class StaticProvider(BriefingProvider):
    name = "static_provider"
    priority = 20
    tier = 0

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return "STATIC\n"


class BulkyCappedProvider(BriefingProvider):
    name = "bulky_capped_provider"
    priority = 1
    tier = 1
    max_fragment_chars = 260

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return (
            "AUTHORITY: raw gate over prose\n"
            + ("middle evidence dump\n" * 80)
            + "ACTION: repair compressed counterexample\n"
        )

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        return [
            {
                "source_type": "compressed_counterexample",
                "residue_class": "finite_quotient_residue",
                "cell_count": 4,
                "repair_class": "minimal_patch",
                "source_ref": "workspace/residue.json",
                "action": "repair quotient before broad mutation",
            }
        ]


class StructuredCappedProvider(BriefingProvider):
    name = "structured_capped_provider"
    priority = 1
    tier = 1
    max_fragment_chars = 360

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return (
            "## Structured Contract\n"
            "- ACTION: preserve typed contract\n"
            "LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {\n"
            '  "proposed_capability_id": "inspect_visible_residue",\n'
            '  "input_contract": {"refs": ["a", "b"]},\n'
            '  "output_contract": {"summary": "bounded"}\n'
            "}\n"
            "```python\n"
            "def step(grid, action, t):\n"
            "    return grid\n"
            "```\n"
            + ("middle json-like detail {\"x\": 1}\n" * 40)
            + "- TAIL ACTION: use sidecar artifact\n"
        )


def test_render_default_briefing_context_does_not_reapply_failed_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    briefing = MutatorBriefing()
    briefing.register(RaisingProvider())
    briefing.register(StaticProvider())
    monkeypatch.setattr(mutator_briefing, "default_briefing", lambda: briefing)
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={},
    )

    rendered = render_default_briefing_context(ctx)

    assert "fixture applies failure" in rendered["body"]
    assert "STATIC" in rendered["body"]
    assert rendered["active_providers"] == ["raising_provider", "static_provider"]
    assert rendered["diagnostics"]["active_providers"] == [
        "raising_provider",
        "static_provider",
    ]


def test_mutator_briefing_caps_provider_fragments_without_losing_markers(
    tmp_path: Path,
) -> None:
    briefing = MutatorBriefing()
    briefing.register(BulkyCappedProvider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={"briefing_attention_agenda_chars": 600},
    )

    body = briefing.render(ctx)
    diag = getattr(briefing, "_last_render_diagnostics", {}) or {}

    assert "AUTHORITY: raw gate over prose" in body
    assert "ACTION: repair compressed counterexample" in body
    assert "finite_quotient_residue" in body
    assert "provider fragment elided" in body
    assert any("bulky_capped_provider(provider_cap" in row for row in diag["budget_trimmed"])


def test_mutator_briefing_elides_structured_fragments_without_broken_json_or_code(
    tmp_path: Path,
) -> None:
    briefing = MutatorBriefing()
    briefing.register(StructuredCappedProvider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={"briefing_attention_agenda_chars": 600},
    )

    body = briefing.render(ctx)

    assert "## Structured Contract" in body
    assert "ACTION: preserve typed contract" in body
    assert "provider fragment elided" in body
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {" not in body
    assert "```python" not in body
    assert '"proposed_capability_id"' not in body


def test_structural_transport_applies_does_not_compute_cuts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "champion_spec.json").write_text(
        json.dumps({"actions": {}, "always": [{"op": "identity"}]})
    )
    provider = StructuralTransportProvider()

    def fail_cuts(ctx: BriefingContext):
        raise AssertionError("applies() must not run worldmodel abduction")

    monkeypatch.setattr(provider, "_cuts", fail_cuts)
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=3,
        rubric={},
        stagnation_count=2,
    )

    assert provider.applies(ctx) is True


def test_structural_transport_legacy_cache_renders_without_recomputing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "structural_transports.json").write_text(
        json.dumps(
            {
                "fingerprint_sha": "legacy",
                "candidates": [
                    {
                        "theorem": "Cached theorem",
                        "field": "field",
                        "mechanism": "cached mechanism",
                        "mapping_hint": "hint",
                        "enrichment": 1.0,
                    }
                ],
            }
        )
    )
    provider = StructuralTransportProvider()

    def fail_cuts(ctx: BriefingContext):
        raise AssertionError("legacy cache hit must not run worldmodel abduction")

    monkeypatch.setattr(provider, "_cuts", fail_cuts)
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=3,
        rubric={},
        stagnation_count=2,
    )

    assert "Cached theorem" in provider.fragment(ctx)


def test_worldmodel_committee_missing_abduced_core_receipt_is_read_only(
    tmp_path: Path,
) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "worldmodel_committee.json").write_text(
        json.dumps(
            {
                "status": "grammar_ceiling",
                "committee_size": 0,
                "transitions": 12,
                "evidence_hash": "abc",
                "witnessed_contexts": [],
            }
        )
    )
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={"fit_expression_grammar": "grid_dsl"},
        stagnation_count=2,
    )

    body = WorldmodelCommitteeProvider().fragment(ctx)

    assert "no persisted receipt yet" in body


def test_leanmill_proof_jobs_provider_reads_receipts_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "worldmodel_lean_feedback_receipt.json").write_text(
        json.dumps(
            {
                "schema": "ztare-worldmodel-lean-feedback-v2",
                "async_command": (
                    "./venv/bin/python -m ztare.leanmill.workbench_actions "
                    "autoformalize-notes workspace/worldmodel_lean_command.md "
                    "--project arc3_tu93_gov --save --json"
                ),
                "absorb_command_template": (
                    "./venv/bin/python -m ztare.worldmodel.lean_bridge absorb "
                    "--project projects/arc3_tu93_gov --lean-file <closed.lean> "
                    "--theorem <theorem_name>"
                ),
            }
        )
    )
    job_dir = tmp_path / "leanmill" / "jobs"
    job_dir.mkdir(parents=True)
    (job_dir / "lm_001.json").write_text(
        json.dumps(
            {
                "schema": "ztare-leanmill-background-job-v1",
                "action": "autoformalize-notes",
                "status": "running",
                "target_name": "timer_monotone",
                "expected_artifact": "ztare_proofs/.solver_scratch/timer.lean",
                "paths": {"job": "leanmill/jobs/lm_001.json"},
            }
        )
    )
    provider = LeanMillProofJobsProvider()
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=workspace,
        iter_index=4,
        rubric={},
    )

    assert provider.applies(ctx) is True
    body = provider.fragment(ctx)
    assert "LeanMill Proof Jobs" in body
    assert "launch_async=./venv/bin/python -m ztare.leanmill.workbench_actions" in body
    assert "absorb_on_close=./venv/bin/python -m ztare.worldmodel.lean_bridge absorb" in body
    assert "target=timer_monotone" in body
    assert "status=running; result=pending" in body
    records = provider.structured_records(ctx)
    assert {r["source_type"] for r in records} == {
        "leanmill_feedback_receipt",
        "leanmill_proof_job",
    }


def test_leanmill_proof_jobs_provider_surfaces_wip_hypotheses(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "arc3_tu93_gov"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    scratch = tmp_path / "ztare_proofs" / ".solver_scratch"
    scratch.mkdir(parents=True)
    (scratch / "RobustProbe_timer_monotone_claude_1.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "-- RECEIPT: TRANSPORT - Lyapunov-style nonincrease composes across deterministic branches.",
                "private lemma consume_count_le : True := by trivial",
                "lemma translate_count_le : True := by trivial",
                "theorem timer_monotone : True := by trivial",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    provider = LeanMillProofJobsProvider()
    ctx = BriefingContext(
        project_dir=project,
        workspace_dir=workspace,
        iter_index=4,
        rubric={},
    )

    assert provider.applies(ctx) is True
    body = provider.fragment(ctx)
    assert "wip_surface=ztare_proofs/.solver_scratch/RobustProbe_timer_monotone_claude_1.lean" in body
    assert "status=wip_hypothesis_only" in body
    assert "finite-support predicate-measure witnesses" in body
    assert "timer_monotone" in body
    assert "Lyapunov-style nonincrease" in body
    records = provider.structured_records(ctx)
    rec = next(r for r in records if r["source_type"] == "leanmill_wip_proof_surface")
    assert rec["authority"] == "hypothesis only until absorbed as an invariant certificate"
    assert "translate_count_le" in rec["summary"]


def test_worldmodel_committee_renders_persisted_abduced_core(
    tmp_path: Path,
) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "worldmodel_committee.json").write_text(
        json.dumps(
            {
                "status": "grammar_ceiling",
                "committee_size": 0,
                "transitions": 12,
                "evidence_hash": "abc",
                "witnessed_contexts": [],
            }
        )
    )
    (ws / "abduced_core.json").write_text(
        json.dumps(
            {
                "schema": "ztare-abduced-core-v1",
                "spec": {"actions": {}, "always": [{"op": "identity"}]},
                "transitions": 12,
                "matched_transitions": 9,
                "residuals": [
                    {
                        "t": 4,
                        "action": 2,
                        "cell_count": 1,
                        "cells": ["(0,0) predicted 0 real 1"],
                    }
                ],
            }
        )
    )
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={"fit_expression_grammar": "grid_dsl"},
        stagnation_count=2,
    )

    body = WorldmodelCommitteeProvider().fragment(ctx)

    assert "ABDUCED CORE" in body
    assert "9/12" in body
    assert "(0,0) predicted 0 real 1" in body


def test_worldmodel_committee_exposes_loop_receipts_as_structured_records(
    tmp_path: Path,
) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "worldmodel_committee.json").write_text(
        json.dumps(
            {
                "status": "committee",
                "committee_size": 1,
                "transitions": 12,
                "evidence_hash": "abc",
                "witnessed_contexts": [],
            }
        )
    )
    (ws / "arc3_play_loop_report.json").write_text(
        json.dumps(
            {
                "cycles": [
                    {
                        "cycle": 3,
                        "pursuit": "plan_exhausted",
                        "steps": 250,
                        "levels_gained": 0,
                        "evidence_grown_by": 0,
                        "played": "candidate",
                        "kernel_role_bindings": [
                            {
                                "term": "planner_goal_cue_absent",
                                "roles": ["search_control", "selection", "model_update"],
                            }
                        ],
                    }
                ]
            }
        )
    )
    (ws / "latest_level_transfer_probe.json").write_text(
        json.dumps(
            {
                "schema": "ztare-arc3-level-transfer-probe-v1",
                "residue_quotient": {
                    "residue_class": "action_independent_boundary_update",
                    "cell_count": 2,
                },
                "verdict": {"numbers": {"pass": 2, "fail": 1}},
                "repair_certificate": {
                    "repair_class": "action_independent_cell_rewrite",
                    "sufficient_for_first_step": True,
                },
                "post_depth": 4,
                "refinement_hint": "keep the quotient exact; tighten only the boundary classifier",
                "local_transfer": {
                    "steps_tested": 16,
                    "exact_steps_after_first_step_repair": 4,
                    "first_step_repair_generalizes_to_depth": False,
                },
            }
        )
    )
    (ws / "level_boundary_harvest_episode_002.json").write_text(
        json.dumps(
            {
                "schema": "ztare-arc3-level-boundary-harvest-v1",
                "episode_path": "/tmp/episode_002.jsonl",
                "content_hash": "abc123",
                "transitions": 16,
                "post_depth": 4,
                "branches": [{}, {}, {}, {}],
                "authority": "observed transitions only",
            }
        )
    )
    (ws / "fixture_residual_classes_receipt.json").write_text(
        json.dumps(
            {
                "schema": "ztare-worldmodel-residual-class-receipt-v1",
                "source_receipt": "workspace/abduced_core.json",
                "source_log": "raw/episodes/episode_001.jsonl",
                "status": "descriptive_residual_surface",
                "matched_transitions": 9,
                "transitions": 12,
                "residual_class_count": 2,
                "top_residual_classes": [
                    {
                        "rank": 1,
                        "first_t": 4,
                        "action": 2,
                        "cell_count": 1,
                        "count": 3,
                        "t_values": [4, 7],
                        "first_witnesses": ["(0,0) predicted 0 real 1"],
                    }
                ],
                "kernel_admissibility": {
                    "schema": "ztare-kernel-change-admissibility-v1",
                    "change_class": "quotient_compression",
                    "math_anchors": ["finite_quotient", "mdl", "raw_gate_authority"],
                    "raw_evidence_refs": ["raw/episodes/episode_001.jsonl"],
                    "verification_refs": ["replay_consistency_gate"],
                    "preserves_raw_fiber": True,
                    "raw_gates_unchanged": True,
                    "candidate_promotion_authority": False,
                    "introduces_substrate_specific_rule": False,
                    "quotient_or_abstraction": "raw rows -> counted classes",
                    "raw_witness_projection": ["first_t", "t_values", "first_witnesses"],
                },
            }
        )
    )
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={"fit_expression_grammar": "grid_dsl"},
    )

    provider = WorldmodelCommitteeProvider()
    records = provider.structured_records(ctx)
    body = provider.fragment(ctx)

    by_type = {rec["source_type"]: rec for rec in records}
    assert by_type["kernel_role_binding"]["term"] == "planner_goal_cue_absent"
    assert by_type["planner_anomaly"]["anomaly_class"] == (
        "plan_exhausted_without_reward_or_new_evidence"
    )
    assert by_type["compressed_counterexample"]["residue_class"] == (
        "action_independent_boundary_update"
    )
    assert by_type["compressed_counterexample"]["repair_sufficient_for_first_step"] is True
    assert by_type["compressed_counterexample"]["first_step_repair_generalizes_to_depth"] is False
    assert by_type["level_boundary_harvest"]["source_ref"] == (
        "workspace/level_boundary_harvest_episode_002.json"
    )
    assert by_type["level_boundary_harvest"]["transitions"] == 16
    assert by_type["level_boundary_harvest"]["seed_available"] is False
    assert by_type["residual_class_receipt"]["residual_class_count"] == 2
    assert by_type["residual_class_receipt"]["admissibility_passed"] is True
    assert by_type["residual_class_receipt"]["top_residual_classes"][0]["count"] == 3
    assert by_type["level_transfer_receipt"]["verdict_numbers"] == {"pass": 2, "fail": 1}
    assert by_type["level_transfer_receipt"]["refinement_hint"] == (
        "keep the quotient exact; tighten only the boundary classifier"
    )
    assert "Level-boundary harvest" in body
    assert "observed transitions only" in body
    assert "seed bytes missing" in body
    assert "Residual class receipt" in body
    assert "admissibility=pass" in body
    assert "Cross-level transfer receipt" in body
    assert "keep the quotient exact; tighten only the boundary classifier" in body


def test_worldmodel_committee_records_reach_attention_agenda(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "worldmodel_committee.json").write_text(
        json.dumps(
            {
                "status": "committee",
                "committee_size": 1,
                "transitions": 12,
                "evidence_hash": "abc",
                "witnessed_contexts": [],
            }
        )
    )
    (ws / "arc3_play_loop_report.json").write_text(
        json.dumps(
            {
                "cycles": [
                    {
                        "cycle": 3,
                        "pursuit": "plan_exhausted",
                        "steps": 250,
                        "levels_gained": 0,
                        "evidence_grown_by": 0,
                        "played": "candidate",
                    }
                ]
            }
        )
    )
    briefing = MutatorBriefing()
    briefing.register(WorldmodelCommitteeProvider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={"fit_expression_grammar": "grid_dsl"},
    )

    body = briefing.render(ctx)

    assert body.startswith("## Briefing Attention Agenda")
    assert "plan_exhausted_without_reward_or_new_evidence" in body
    assert "route through Strategy Office" in body


def test_worldmodel_committee_transfer_receipt_absent_renders_nothing(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "worldmodel_committee.json").write_text(
        json.dumps(
            {
                "status": "committee",
                "committee_size": 1,
                "transitions": 12,
                "evidence_hash": "abc",
                "witnessed_contexts": [],
            }
        )
    )
    provider = WorldmodelCommitteeProvider()
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={"fit_expression_grammar": "grid_dsl"},
    )

    body = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "Cross-level transfer receipt" not in body
    assert all(rec.get("source_type") != "level_transfer_receipt" for rec in records)


def test_strategy_experiments_provider_surfaces_repair_cards(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "fam",
                "falsifiable_prediction": "rerun probe reaches exact_first_step_transfer",
                "rationale": "compact residue with sufficiency certificate",
                "action_plan": {
                    "seed_prerequisite": {
                        "status": "replayable_seed_missing",
                        "seed_path": "workspace/level2_seed.json",
                    },
                    "residue_quotient": {
                        "residue_class": "action_independent_boundary_update",
                        "class_count": 36,
                        "bbox": [61, 56, 62, 57],
                        "signature": {
                            "pair_counts": [
                                {"predicted": 8, "real": 3, "count": 4}
                            ]
                        },
                    },
                    "local_residue_quotient": {
                        "classes": [
                            {
                                "refinement_hint": {
                                    "candidate_class": "component_scoped_extremal_count_or_rate_refinement_candidate"
                                }
                            }
                        ]
                    },
                    "repair_certificate": {
                        "repair_class": "action_independent_cell_rewrite",
                    },
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_first_step_transfer",
                    },
                },
                "kill_condition": "rerun still mismatches",
                "disposition": "open",
            }
        )
        + "\n"
    )
    provider = StrategyExperimentsProvider()
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=2,
        rubric={},
    )

    fragment = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "Strategy Office Experiment Cards" in fragment
    assert "exact full `failure_family_sha`" in fragment
    assert "patch the quotient class, not every same-color" in fragment
    assert "compressed_counterexample_repair" in fragment
    assert f"sha={family_sha('fam')}" in fragment
    assert "bbox=[61, 56, 62, 57]" in fragment
    assert "pairs=8->3x4" in fragment
    assert "seed=replayable_seed_missing" in fragment
    assert "seed_path=workspace/level2_seed.json" in fragment
    assert "component_scoped_extremal_count_or_rate_refinement_candidate" in fragment
    assert "no_attempt_blockers=[" in fragment
    assert "requires_external_actions" not in fragment
    assert records[0]["source_type"] == "strategy_experiment"
    assert records[0]["residue_class"] == "action_independent_boundary_update"
    assert records[0]["seed_prerequisite"]["status"] == "replayable_seed_missing"
    assert "pairs=8->3x4" in records[0]["summary"]
    assert records[0]["required_transform"] == (
        "lower_certificate_to_carrier_or_refute_or_propose_capability"
    )
    assert "requires_external_actions" not in records[0]["admissible_no_attempt_blockers"]
    assert records[0]["repair_class"] == (
        "component_scoped_extremal_count_or_rate_refinement_candidate"
    )


def test_strategy_experiments_provider_surfaces_routing_cards(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "search_control_residue_repair",
                "failure_family": "fam",
                "falsifiable_prediction": "next cycle produces terminal event or evidence",
                "rationale": "planner exhausted without information gain",
                "action_plan": {
                    "residue_quotient": {
                        "residue_class": "closed_dynamics_no_terminal_progress",
                    },
                    "routing_class": "target_synthesis_or_discriminating_probe",
                    "discriminator_axis": {
                        "axis": "target_specification_gap_vs_transition_model_gap",
                    },
                    "required_next_gate": {
                        "command": "arc3_play_loop",
                        "spends_external_actions": True,
                        "success_status": "terminal_event_or_new_evidence",
                    },
                },
                "kill_condition": "same residue repeats",
                "disposition": "open",
            }
        )
        + "\n"
    )
    provider = StrategyExperimentsProvider()
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=2,
        rubric={},
    )

    fragment = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "search_control_residue_repair" in fragment
    assert "STRATEGY_CARD_DISCHARGE" in fragment
    assert "sha=" in fragment
    assert "target_synthesis_or_discriminating_probe" in fragment
    assert "target_specification_gap_vs_transition_model_gap" in fragment
    assert "requires_external_actions" in fragment
    assert records[0]["repair_class"] == "target_synthesis_or_discriminating_probe"
    assert "target_specification_gap_vs_transition_model_gap" in records[0]["summary"]
    assert "requires_external_actions" in records[0]["admissible_no_attempt_blockers"]


def test_default_briefing_includes_strategy_experiment_cards(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "fam",
                "falsifiable_prediction": "rerun probe reaches exact_first_step_transfer",
                "rationale": "compact residue with sufficiency certificate",
                "action_plan": {
                    "residue_quotient": {
                        "residue_class": "action_independent_boundary_update",
                    },
                    "repair_certificate": {
                        "repair_class": "action_independent_cell_rewrite",
                    },
                    "required_next_gate": {
                        "command": "arc3_level_transfer_probe",
                        "success_status": "exact_first_step_transfer",
                    },
                },
                "kill_condition": "rerun still mismatches",
                "disposition": "open",
            }
        )
        + "\n"
    )
    rendered = render_default_briefing_context(
        BriefingContext(
            project_dir=tmp_path,
            workspace_dir=ws,
            iter_index=2,
            rubric={},
        )
    )

    assert "strategy_experiments" in rendered["active_providers"]
    assert "Strategy Office Experiment Cards" in rendered["body"]
    assert "workspace/strategy_experiments.jsonl" in rendered["body"]


def test_embedding_history_uses_canonical_vector_cache() -> None:
    source = Path("src/ztare/orchestrator/briefing_providers/embedding_history.py").read_text(
        encoding="utf-8"
    )

    assert "cached_text_embeddings" in source
    assert "embedding_history_vectors.json" in source
    assert "SentenceTransformer" not in source


def test_embedding_history_ignores_run_boundary_rows(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "iteration_telemetry.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"record_type": "run_start", "run_id": 1}),
                json.dumps({"record_type": "iteration", "iteration_index": 1, "score": 0}),
                json.dumps({"iteration_index": 2, "score": 1}),
                json.dumps({"record_type": "run_end", "run_id": 1}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={},
    )

    rows = EmbeddingHistoryProvider()._load_telemetry(ctx)

    assert [row.get("iteration_index") for row in rows] == [1, 2]


def test_leaf_workbench_provider_surfaces_worldmodel_actions(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (tmp_path / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "counterexample_trace": {
                    "mismatch_classes": [
                        {
                            "count": 36,
                            "t": 128,
                            "action": 1,
                            "signature": {
                                "bbox": [61, 56, 62, 57],
                                "pair_counts": [
                                    {"predicted": 8, "real": 3, "count": 4}
                                ],
                            },
                        }
                    ]
                }
            }
        )
    )
    (ws / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "sha": "abc123",
                        "submission": "workspace/submissions/best.py",
                        "visible_exact_rows": 10,
                        "visible_checked_rows": 12,
                        "visible_wrong_cells": 2,
                        "holdout_depth": 0,
                        "gate_score": 0.3,
                    }
                ],
            }
        )
    )
    (ws / "strategy_experiments.jsonl").write_text("{}\n")
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=1,
        rubric={"fit_expression_grammar": "grid_dsl"},
    )

    provider = LeafWorkbenchProvider()
    body = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "## Leaf workbench capabilities" in body
    assert "inspect_worldmodel_patch_base" in body
    assert "inspect_replay_residual_quotient" in body
    assert "LEAF_WORKBENCH_RECEIPT" in body
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL" in body
    assert "grid coordinates are `(row, col)`" in body
    assert "PATCH_BASE" in body
    assert "PATCH_DELTA" in body
    assert any(r["capability_id"] == "score_worldmodel_candidate_delta" for r in records)


def test_briefing_elision_preserves_atomic_control_object_line() -> None:
    control_line = (
        '  - {"type":"LEAF_WORKBENCH_ACTION_REQUEST","payload":'
        '{"capability_id":"run_strategy_required_gate","input_refs":'
        '{"candidate_path":"test_model.py"}}}'
    )
    text = "\n".join(
        [
            "## Provider",
            "- long context " * 80,
            control_line,
            "- tail " * 80,
        ]
    )

    rendered = _middle_elide_fragment(text, 650)

    assert control_line in rendered
    assert "[structured code/json block omitted" not in rendered


def test_leaf_workbench_capability_proposal_example_round_trips(tmp_path: Path) -> None:
    from ztare.validator.worldmodel_typed_payload import render_worldmodel_typed_payload

    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "sha": "abc123",
                        "submission": "workspace/submissions/best.py",
                        "visible_exact_rows": 10,
                        "visible_checked_rows": 12,
                        "visible_wrong_cells": 2,
                        "holdout_depth": 0,
                    }
                ],
            }
        )
    )
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=1,
        rubric={"fit_expression_grammar": "grid_dsl"},
    )

    body = LeafWorkbenchProvider().fragment(ctx)
    marker = "- capability-proposal shape: "
    line = next(line for line in body.splitlines() if line.startswith(marker))
    payload_text = line[len(marker) :].split(". This queues future tool work only;", 1)[0]
    payload = json.loads(payload_text.replace("...", "x"))

    rendered = render_worldmodel_typed_payload(
        {
            "control_receipts": [
                {
                    "type": "LOWERABILITY_BLOCKED",
                    "payload": {
                        "visible_capabilities_attempted": ["read staged source fibers"],
                        "candidate_family_attempted": "candidate search",
                        "obstruction": "current visible surfaces do not expose the needed witness",
                        "missing_witness_or_sensor": "bounded proposal fixture",
                        "next_action": "record tool-gap observation",
                        "evidence_refs": ["workspace/candidate_memory.json"],
                    },
                },
                payload,
            ],
            "thesis_markdown": "proposal paired with typed obstruction",
            "test_model_py": "",
        }
    )

    assert "LOWERABILITY_BLOCKED:" in rendered
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL:" in rendered


def test_default_briefing_includes_leaf_workbench_provider() -> None:
    names = [provider.name for provider in mutator_briefing.default_briefing().providers]

    assert "leaf_workbench" in names


def test_leaf_workbench_surfaces_same_support_context_split(tmp_path: Path) -> None:
    from ztare.worldmodel.episode_log import EpisodeLog

    project = tmp_path
    ws = project / "workspace"
    episodes = project / "raw" / "episodes"
    ws.mkdir()
    episodes.mkdir(parents=True)

    log = EpisodeLog()
    log.append(
        ((7, 8, 8), (7, 8, 8), (0, 0, 0)),
        1,
        ((7, 3, 8), (7, 3, 8), (0, 0, 0)),
        t=5,
    )
    log.append(
        ((0, 8, 8), (0, 8, 8), (0, 0, 0)),
        1,
        ((0, 8, 8), (0, 8, 8), (0, 0, 0)),
        t=5,
    )
    log.write_jsonl(episodes / "episode_001.jsonl")
    (project / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "candidate_regression_receipt": {
                    "schema": "ztare-candidate-regression-receipt-v1",
                    "candidate_relation": "regression",
                    "exact_rows_delta": -1,
                    "wrong_cells_delta": 2,
                    "holdout_depth_delta": 0,
                    "quotient_comparison": {
                        "schema": "ztare-regression-quotient-comparison-v1",
                        "relation": "same_support_changed_pairs",
                        "candidate_top_quotient": {
                            "bbox": [0, 1, 1, 1],
                            "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                            "first_row": 0,
                            "t": 5,
                            "action": 1,
                            "count": 1,
                        },
                        "best_prior_top_quotient": {
                            "bbox": [0, 1, 1, 1],
                            "pair_counts": [{"predicted": 3, "real": 8, "count": 2}],
                            "first_row": 1,
                            "t": 5,
                            "action": 1,
                            "count": 1,
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    records = LeafWorkbenchProvider().structured_records(
        BriefingContext(
            project_dir=project,
            workspace_dir=ws,
            iter_index=1,
            rubric={"fit_expression_grammar": "grid_dsl"},
        )
    )

    context_records = [
        r for r in records
        if r.get("capability_id") == "inspect_worldmodel_counterexample_context"
    ]
    assert context_records
    assert "same_support_changed_pairs" in context_records[0]["summary"]
    assert "context_delta=" in context_records[0]["summary"]
    assert "support_row_sections" in context_records[0]["summary"]


def test_leaf_workbench_prefers_fresh_r1_regression_over_stale_eval(tmp_path: Path) -> None:
    from ztare.worldmodel.episode_log import EpisodeLog

    project = tmp_path
    ws = project / "workspace"
    episodes = project / "raw" / "episodes"
    ws.mkdir()
    episodes.mkdir(parents=True)

    log = EpisodeLog()
    log.append(
        ((7, 8, 8), (7, 8, 8), (0, 0, 0)),
        1,
        ((7, 3, 8), (7, 3, 8), (0, 0, 0)),
        t=5,
    )
    log.append(
        ((0, 8, 8), (0, 8, 8), (0, 0, 0)),
        1,
        ((0, 8, 8), (0, 8, 8), (0, 0, 0)),
        t=5,
    )
    log.write_jsonl(episodes / "episode_001.jsonl")
    stale = {
        "candidate_regression_receipt": {
            "schema": "ztare-candidate-regression-receipt-v1",
            "candidate_relation": "regression",
            "quotient_comparison": {
                "schema": "ztare-regression-quotient-comparison-v1",
                "relation": "changed_support",
                "candidate_top_quotient": {
                    "bbox": [0, 0, 0, 0],
                    "first_row": 0,
                },
                "best_prior_top_quotient": {
                    "bbox": [1, 1, 1, 1],
                    "first_row": 1,
                },
            },
        }
    }
    fresh = {
        "schema": "ztare-latest-patch-base-regression-v1",
        "candidate_regression_receipt": {
            "schema": "ztare-candidate-regression-receipt-v1",
            "candidate_relation": "regression",
            "exact_rows_delta": -3,
            "wrong_cells_delta": 15,
            "holdout_depth_delta": 0,
            "quotient_comparison": {
                "schema": "ztare-regression-quotient-comparison-v1",
                "relation": "same_support_changed_pairs",
                "candidate_top_quotient": {
                    "bbox": [0, 1, 1, 1],
                    "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                    "first_row": 0,
                    "t": 5,
                    "action": 1,
                    "count": 1,
                },
                "best_prior_top_quotient": {
                    "bbox": [0, 1, 1, 1],
                    "pair_counts": [{"predicted": 3, "real": 8, "count": 2}],
                    "first_row": 1,
                    "t": 5,
                    "action": 1,
                    "count": 1,
                },
            },
        },
    }
    (project / "latest_eval_results.json").write_text(json.dumps(stale), encoding="utf-8")
    (ws / "latest_patch_base_regression.json").write_text(
        json.dumps(fresh),
        encoding="utf-8",
    )

    records = LeafWorkbenchProvider().structured_records(
        BriefingContext(
            project_dir=project,
            workspace_dir=ws,
            iter_index=1,
            rubric={"fit_expression_grammar": "grid_dsl"},
        )
    )

    context_records = [
        r for r in records
        if r.get("capability_id") == "inspect_worldmodel_counterexample_context"
    ]
    assert context_records
    assert context_records[0]["source_ref"].startswith(
        "workspace/latest_patch_base_regression.json"
    )
    assert "same_support_changed_pairs" in context_records[0]["summary"]
    assert "context_delta=" in context_records[0]["summary"]


# ── Harness bug fixes: mode-gated budget + render receipts + control-plane floor ──


class BigT4Provider(BriefingProvider):
    """T4 provider whose fragment fills most of the 12k budget but doesn't exceed it alone."""

    name = "big_t4_provider"
    priority = 200
    tier = 4

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        # 11800 chars — fits solo (< 12000) but leaves no room for a sibling
        return "## BigT4\n" + ("x" * 11800) + "\n"


class ControlPlaneT4Provider(BriefingProvider):
    """T4 control-plane provider — must survive the chat-mode budget gate."""

    name = "control_plane_t4"
    priority = 210
    tier = 4
    control_plane = True

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return "## ControlPlaneT4\nCONTROL_PLANE_CONTENT\n"


class SmallT4Provider(BriefingProvider):
    """T4 low-priority provider that should be trimmed in chat mode after BigT4."""

    name = "small_t4_low"
    priority = 300
    tier = 4

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        # 500 chars — with BigT4 at 11800, total would be 12300 > 12000 budget
        return "## SmallT4\n" + "SMALL_CONTENT " * 35 + "\n"


def test_file_mode_does_not_trim_oversized_t4_provider(tmp_path: Path) -> None:
    """Workbench/file mode: every applies()=True provider renders; no budget drop."""
    briefing = MutatorBriefing()
    briefing.register(BigT4Provider())
    briefing.register(SmallT4Provider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=5,
        rubric={},
        stagnation_count=5,
        rendering_mode="file",  # workbench mode — no budget
    )

    body = briefing.render(ctx)
    diag = getattr(briefing, "_last_render_diagnostics", {}) or {}

    assert "BigT4" in body
    assert "SmallT4" in body
    assert len(body) > 11000
    budget_trims = [t for t in diag.get("budget_trimmed", []) if "(T" in t and "(provider_cap" not in t]
    assert budget_trims == [], f"file mode must not trim any provider, got: {budget_trims}"
    assert diag.get("budget_applied") is False
    assert diag.get("rendering_mode") == "file"


def test_file_mode_render_receipt_written(tmp_path: Path) -> None:
    """Render receipt JSONL is written with budget_applied=false in file mode."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    briefing = MutatorBriefing()
    briefing.register(BigT4Provider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=3,
        rubric={},
        stagnation_count=5,
        rendering_mode="file",
    )

    briefing.render(ctx)

    receipts_path = ws / "briefing_render_receipts.jsonl"
    assert receipts_path.exists(), "briefing_render_receipts.jsonl must be written"
    rows = [json.loads(line) for line in receipts_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema"] == "ztare.briefing_render.v1"
    assert row["iter"] == 3
    assert row["mode"] == "file"
    assert row["budget_applied"] is False
    assert "big_t4_provider" in row["providers_applied"]
    assert row["providers_trimmed"] == []


def test_chat_mode_trims_low_priority_t4_but_not_control_plane(tmp_path: Path) -> None:
    """Chat mode: low-priority T4 is trimmed when over budget; control-plane T4 is not."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    briefing = MutatorBriefing()
    # BigT4 (priority=200) fills the budget; SmallT4 (priority=300) should be trimmed;
    # ControlPlaneT4 (priority=210) must survive despite the budget being exhausted.
    briefing.register(BigT4Provider())
    briefing.register(ControlPlaneT4Provider())
    briefing.register(SmallT4Provider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=7,
        # disable attention agenda so its chars don't interfere with the budget accounting
        rubric={"briefing_budget_chars": 12000, "briefing_attention_agenda": False},
        stagnation_count=5,
        rendering_mode="chat",
    )

    body = briefing.render(ctx)
    diag = getattr(briefing, "_last_render_diagnostics", {}) or {}

    assert "BigT4" in body, "BigT4 renders first and fills budget"
    assert "CONTROL_PLANE_CONTENT" in body, "control-plane provider must never be budget-trimmed"
    assert "SMALL_CONTENT" not in body, "low-priority T4 must be trimmed when over budget"
    budget_trims = [t for t in diag.get("budget_trimmed", []) if "(T" in t and "(provider_cap" not in t]
    assert any("small_t4_low" in t for t in budget_trims), f"small_t4_low must be in trimmed: {budget_trims}"
    assert not any("control_plane_t4" in t for t in budget_trims), "control_plane_t4 must NOT be in trimmed"
    assert diag.get("budget_applied") is True
    assert diag.get("rendering_mode") == "chat"


def test_chat_mode_render_receipt_names_trimmed_providers(tmp_path: Path) -> None:
    """Chat mode receipt names what was cut."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    briefing = MutatorBriefing()
    briefing.register(BigT4Provider())
    briefing.register(SmallT4Provider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=2,
        rubric={"briefing_budget_chars": 12000, "briefing_attention_agenda": False},
        stagnation_count=5,
        rendering_mode="chat",
    )

    briefing.render(ctx)

    receipts_path = ws / "briefing_render_receipts.jsonl"
    assert receipts_path.exists()
    rows = [json.loads(line) for line in receipts_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema"] == "ztare.briefing_render.v1"
    assert row["budget_applied"] is True
    assert row["mode"] == "chat"
    assert any("small_t4_low" in t for t in row["providers_trimmed"]), (
        f"trimmed provider must be named in receipt, got: {row['providers_trimmed']}"
    )


def test_forced_reframe_provider_has_control_plane_true() -> None:
    """forced_reframe must be marked control_plane so it's exempt from chat budget gate."""
    from ztare.orchestrator.briefing_providers.forced_reframe import ForcedReframeBriefingProvider

    p = ForcedReframeBriefingProvider()
    assert getattr(p, "control_plane", False) is True, (
        "ForcedReframeBriefingProvider must have control_plane=True"
    )


def test_tried_failed_digest_provider_has_control_plane_true() -> None:
    """tried_failed_digest must be marked control_plane."""
    from ztare.orchestrator.briefing_providers.tried_failed_digest import TriedFailedDigestProvider

    p = TriedFailedDigestProvider()
    assert getattr(p, "control_plane", False) is True, (
        "TriedFailedDigestProvider must have control_plane=True"
    )


def test_render_receipts_accumulate_across_iters(tmp_path: Path) -> None:
    """Multiple renders append rows to briefing_render_receipts.jsonl."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    briefing = MutatorBriefing()
    briefing.register(StaticProvider())

    for i in range(3):
        ctx = BriefingContext(
            project_dir=tmp_path,
            workspace_dir=ws,
            iter_index=i + 1,
            rubric={},
            rendering_mode="file",
        )
        briefing.render(ctx)

    receipts_path = ws / "briefing_render_receipts.jsonl"
    rows = [json.loads(line) for line in receipts_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 3
    assert [row["iter"] for row in rows] == [1, 2, 3]
