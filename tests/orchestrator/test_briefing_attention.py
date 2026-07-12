from __future__ import annotations

from pathlib import Path

from ztare.orchestrator.briefing_attention import (
    compile_attention_agenda,
    render_attention_agenda,
)
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
    MutatorBriefing,
)


class RecordProvider(BriefingProvider):
    name = "record_provider"
    tier = 0
    priority = 10

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return "## Provider Body\nbody\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        return [
            {
                "source_type": "contract_violation",
                "summary": "missing required executable carrier",
                "action": "change contract shape before retry",
                "source_ref": "workspace/contract_violations.jsonl",
            },
            {
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/near.py",
                "sha": "abc123",
                "visible_exact_rows": 923,
                "visible_checked_rows": 1023,
                "visible_wrong_cells": 1800,
                "first_mismatch": "first replay mismatch at row 2",
            },
        ]


def test_attention_agenda_prioritizes_deterministic_gate_receipts() -> None:
    items = compile_attention_agenda(
        [
            {
                "provider": "prose",
                "source_type": "analogy_candidate",
                "summary": "plausible analogy but no gate receipt",
            },
            {
                "provider": "survivors",
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/near.py",
                "visible_exact_rows": 900,
                "visible_checked_rows": 1000,
                "first_mismatch": "first deterministic mismatch",
            },
        ]
    )

    assert items[0].source_type == "deterministic_near_miss"
    assert "deterministic mismatch" in items[0].summary


def test_attention_agenda_surfaces_kernel_role_bindings_above_prose() -> None:
    items = compile_attention_agenda(
        [
            {
                "provider": "notes",
                "source_type": "analogy_candidate",
                "summary": "interesting analogy without a receipt",
            },
            {
                "provider": "strategy_office",
                "source_type": "kernel_role_binding",
                "term": "planner_goal_cue_absent",
                "kernel_roles": ["search_control", "selection", "model_update"],
                "source_ref": "workspace/arc3_play_loop_report.json",
            },
        ]
    )

    assert items[0].source_type == "kernel_role_binding"
    assert "planner_goal_cue_absent" in items[0].summary
    assert "search_control" in items[0].summary


def test_attention_agenda_prioritizes_strategy_cards_over_full_survivors() -> None:
    items = compile_attention_agenda(
        [
            {
                "provider": "survivors",
                "source_type": "full_survivor",
                "summary": "transition carrier passes replay and holdout",
                "source_ref": "workspace/submissions/candidate.py",
            },
            {
                "provider": "strategy_experiments",
                "source_type": "strategy_experiment",
                "kind": "search_control_residue_repair",
                "failure_family_sha": "abcdef0123456789zz",
                "residue_class": "closed_dynamics_no_terminal_progress",
                "repair_class": "target_synthesis_or_discriminating_probe",
                "required_receipt": "STRATEGY_CARD_DISCHARGE",
                "source_ref": "workspace/strategy_experiments.jsonl",
            },
        ]
    )

    assert items[0].source_type == "strategy_experiment"
    assert "STRATEGY_CARD_DISCHARGE" in items[0].summary
    assert "abcdef0123456789" in items[0].summary


def test_attention_agenda_names_strategy_card_transform_obligation() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "strategy_experiments",
                "source_type": "strategy_experiment",
                "kind": "compressed_counterexample_repair",
                "failure_family_sha": "abcdef0123456789zz",
                "residue_class": "action_independent_boundary_update",
                "repair_class": "action_independent_cell_rewrite",
                "required_receipt": "STRATEGY_CARD_DISCHARGE",
                "required_transform": (
                    "lower_certificate_to_carrier_or_refute_or_propose_capability"
                ),
                "source_ref": "workspace/strategy_experiments.jsonl",
            }
        ]
    )

    assert "obligation=lower_certificate_to_carrier_or_refute_or_propose_capability" in rendered


def test_attention_agenda_formats_planner_anomaly_receipts() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "telemetry",
                "source_type": "planner_anomaly",
                "anomaly_class": "low_entropy_residue_broad_search",
                "expected_next_kernel_action": "compressed_counterexample_repair",
                "observed_next_action": "coverage_sweep",
            }
        ]
    )

    assert "low_entropy_residue_broad_search" in rendered
    assert "compressed_counterexample_repair" in rendered
    assert "coverage_sweep" in rendered


def test_attention_agenda_formats_scheduler_counterexample_receipts() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "worldmodel_committee",
                "source_type": "scheduler_counterexample",
                "anomaly_class": "low_yield_loop_control",
                "scheduler_tags": [
                    "r1_declaration_mismatch",
                    "patch_base_no_improvement",
                ],
                "decision_action": "REFRESH_SPECIALISTS",
                "expected_next_kernel_action": (
                    "compile routing failure into quotient repair"
                ),
                "source_ref": "workspace/latest_information_yield.json",
                "action": "require scheduler-disposition receipt before retry",
            }
        ]
    )

    assert "low_yield_loop_control" in rendered
    assert "r1_declaration_mismatch" in rendered
    assert "REFRESH_SPECIALISTS" in rendered
    assert "scheduler-disposition" in rendered


def test_attention_agenda_formats_compressed_counterexample_repair_certificate() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "worldmodel_committee",
                "source_type": "compressed_counterexample",
                "residue_class": "action_independent_boundary_update",
                "cell_count": 2,
                "repair_class": "action_independent_cell_rewrite",
                "repair_sufficient_for_first_step": True,
            }
        ]
    )

    assert "action_independent_boundary_update" in rendered
    assert "action_independent_cell_rewrite" in rendered
    assert "sufficient" in rendered


def test_attention_agenda_marks_first_step_repair_depth_limited() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "worldmodel_committee",
                "source_type": "compressed_counterexample",
                "residue_class": "action_independent_boundary_update",
                "cell_count": 2,
                "repair_class": "action_independent_cell_rewrite",
                "repair_sufficient_for_first_step": True,
                "first_step_repair_generalizes_to_depth": False,
                "exact_steps_after_first_step_repair": 4,
                "local_steps_tested": 16,
            }
        ]
    )

    assert "first-step only" in rendered
    assert "4/16" in rendered


def test_attention_agenda_formats_residual_class_receipt() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "worldmodel_committee",
                "source_type": "residual_class_receipt",
                "source_ref": "workspace/residual_classes_receipt.json",
                "matched_transitions": 5651,
                "transitions": 5813,
                "residual_class_count": 6,
                "admissibility_passed": True,
                "top_residual_classes": [
                    {"rank": 1, "count": 75, "cell_count": 138},
                    {"rank": 2, "count": 36, "cell_count": 4},
                ],
                "action": "route quotient classes before broad mutation",
            }
        ]
    )

    assert "residual quotient receipt replay=5651/5813" in rendered
    assert "classes=6" in rendered
    assert "#2:count=36,cells=4" in rendered
    assert "route quotient classes" in rendered


def test_attention_agenda_formats_level_transfer_receipt() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "worldmodel_committee",
                "source_type": "level_transfer_receipt",
                "source_ref": "workspace/latest_level_transfer_probe.json",
                "verdict_numbers": {"pass": 2, "fail": 1},
                "refinement_hint": "keep the quotient exact; tighten only the boundary classifier",
                "action": "route transfer evidence alongside residual-class receipts",
            }
        ]
    )

    assert "cross-level transfer receipt" in rendered
    assert "pass" in rendered
    assert "keep the quotient exact; tighten only the boundary classifier" in rendered
    assert "route transfer evidence" in rendered


def test_render_attention_agenda_is_compact_and_authority_labeled() -> None:
    rendered = render_attention_agenda(
        [
            {
                "provider": "gate",
                "source_type": "gate_failure",
                "summary": "holdout failed",
                "action": "repair residual before promotion",
            }
        ]
    )

    assert "## Briefing Attention Agenda" in rendered
    assert "provider=gate" in rendered
    assert "type=gate_failure" in rendered
    assert "repair residual" in rendered


def test_mutator_briefing_prepends_attention_agenda_from_structured_records(
    tmp_path: Path,
) -> None:
    briefing = MutatorBriefing()
    briefing.register(RecordProvider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={},
    )

    body = briefing.render(ctx)
    diag = getattr(briefing, "_last_render_diagnostics", {})

    assert body.startswith("## Briefing Attention Agenda")
    assert "workspace/submissions/near.py" in body
    assert "## Provider Body" in body
    assert diag["structured_record_count"] == 2
    assert diag["attention_agenda_chars"] > 0


def test_attention_agenda_can_be_disabled(tmp_path: Path) -> None:
    briefing = MutatorBriefing()
    briefing.register(RecordProvider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={"briefing_attention_agenda": False},
    )

    body = briefing.render(ctx)

    assert body.startswith("## Provider Body")
    assert "Briefing Attention Agenda" not in body


def test_embedding_history_uses_canonical_embedding_engine() -> None:
    source = Path("src/ztare/orchestrator/briefing_providers/embedding_history.py").read_text(
        encoding="utf-8"
    )

    assert "from ztare.common.embeddings import cached_text_embeddings, make_client" in source
    assert "SentenceTransformer" not in source
