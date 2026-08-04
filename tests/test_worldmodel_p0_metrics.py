from __future__ import annotations

import json
from pathlib import Path

from ztare.common.continual_skill_memory import (
    ContinualSkillMemory,
    SkillFamilyMemory,
    save_continual_skill_memory,
)
from ztare.worldmodel.p0_metrics import build_p0_metrics, write_p0_metrics
from ztare.worldmodel.carrier_loader import (
    resolve_current_carrier_evidence_identity,
)


def _current_binding(project: Path) -> dict:
    (project / "test_model.py").write_text("VALUE = 1\n", encoding="utf-8")
    return resolve_current_carrier_evidence_identity(project).to_dict()


def test_p0_metrics_summarize_transfer_and_compression(tmp_path: Path) -> None:
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    binding = _current_binding(project)
    (ws / "latest_level_transfer_probe.json").write_text(
        json.dumps(
            {
                "carrier_evidence_identity": binding,
                "post_depth": 4,
                "exact_actions": 1,
                "exact_steps": 2,
                "local_transfer": {
                    "steps_tested": 16,
                    "exact_steps_after_first_step_repair": 4,
                    "first_step_repair_generalizes_to_depth": False,
                },
            }
        )
    )
    (ws / "arc3_play_loop_report.json").write_text(
        json.dumps(
            {
                "cycles": [
                    {"levels_gained": 1, "steps": 18},
                    {"levels_gained": 0, "steps": 200},
                ],
                "rhae": 0.62,
            }
        )
    )
    (ws / "strategy_experiments.jsonl").write_text(
        json.dumps({"disposition": "open"}) + "\n"
    )
    (ws / "operator_proposals.jsonl").write_text("{}\n{}\n")
    (ws / "grammar_extension_promotion_contracts.jsonl").write_text("{}\n")
    (ws / "candidate_memory.json").write_text(
        json.dumps({"records": [{"operator": "translate"}, {"operator": "translate"}]})
    )
    (ws / "latest_reachability.json").write_text(
        json.dumps({"status": "coverage", "states_enumerated": 7, "edges_enumerated": 9})
    )
    (ws / "iteration_telemetry.jsonl").write_text(
        json.dumps({"error": "R1 temporal admissibility failure"}) + "\n"
    )

    metrics = build_p0_metrics(project)

    assert metrics["schema"] == "ztare-arc3-p0-metrics-v2"
    assert metrics["scoreboard"]["levels_beaten"] == 1
    assert metrics["scoreboard"]["actions_per_level"] == [18]
    assert metrics["scoreboard"]["relative_human_action_efficiency"] == 0.62
    assert isinstance(metrics["information_theory"]["catalog_size"], int)
    assert metrics["information_theory"]["catalog_growth_velocity"] is None
    assert metrics["information_theory"]["operator_reusability_index"] is None
    assert metrics["information_theory"]["temporal_admissibility_leakage"] == 1.0
    assert metrics["transfer"]["empirical_transfer_depth"] == 4
    assert metrics["transfer"]["identity_status"] == "current"
    assert metrics["transfer"]["local_steps_tested"] == 16
    assert metrics["transfer"]["first_step_repair_generalizes_to_depth"] is False
    assert metrics["compression"]["catalog_proposals"] == 2
    assert metrics["compression"]["catalog_promotions"] == 1
    assert metrics["compression"]["catalog_growth_rate"] is None
    assert metrics["compression"]["operator_vocabulary_size"] == 0
    assert (
        metrics["metric_contracts"]["information_theory.carrier_fidelity_best"]["status"]
        == "missing_evidence"
    )
    assert metrics["compression"]["operator_reuse_count"] is None
    assert metrics["kernel_pressure"]["temporal_admissibility_failures"] == 1
    assert metrics["reachability"]["abstract_vertices"] == 7
    assert metrics["reachability"]["abstract_edges"] == 9
    assert metrics["reachability"]["abstract_entropy_bits"] > 4.0


def test_write_p0_metrics_writes_project_workspace_receipt(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()

    path = write_p0_metrics(tmp_path)

    assert path == ws / "p0_metrics.json"
    assert json.loads(path.read_text())["schema"] == "ztare-arc3-p0-metrics-v2"


def test_p0_metrics_consume_stable_cross_context_skill_identity(
    tmp_path: Path,
) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    families = tuple(sorted(
        (
            SkillFamilyMemory(
                family_sha256="family-a",
                operation_namespace="actions",
                operation_sha256s=("op-a",),
                operation_reprs=("'a'",),
                revision_sha256s=("revision-a",),
                context_sha256s=("context-1", "context-2"),
                trace_refs=("trace-1", "trace-2"),
            ),
            SkillFamilyMemory(
                family_sha256="family-b",
                operation_namespace="actions",
                operation_sha256s=("op-b",),
                operation_reprs=("'b'",),
                revision_sha256s=("revision-b",),
                context_sha256s=("context-1",),
                trace_refs=("trace-3",),
            ),
        ),
        key=lambda family: family.family_sha256,
    ))
    save_continual_skill_memory(
        ws / "continual_skill_memory.json",
        ContinualSkillMemory(families=families),
    )
    (ws / "arc3_play_loop_report.json").write_text(json.dumps({
        "cycles": [{
            "planning_outcome": {
                "continual_skill_execution_windows": [
                    {
                        "family_sha256": "family-a",
                        "revision_sha256": "revision-a",
                        "context_sha256": "context-1",
                        "start_step": 0,
                        "end_step": 2,
                    },
                    {
                        "family_sha256": "family-b",
                        "revision_sha256": "revision-b",
                        "context_sha256": "context-1",
                        "start_step": 2,
                        "end_step": 3,
                    },
                ],
            },
        }],
    }))

    metrics = build_p0_metrics(tmp_path)

    assert metrics["information_theory"]["operator_reusability_index"] == 0.5
    assert metrics["compression"]["operator_reuse_count"] == 1
    assert metrics["compression"]["continual_skill_family_count"] == 2
    assert metrics["compression"]["continual_skill_revision_count"] == 2
    assert metrics["control_readiness"]["decision_consumer_count"] == 1
    assert (
        metrics["metric_contracts"][
            "information_theory.operator_reusability_index"
        ]["status"]
        == "operational"
    )


def test_p0_transfer_metrics_ignore_unbound_prefix_receipt(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    binding = _current_binding(tmp_path)
    binding["carrier_sha256"] = binding["carrier_sha256"][:12]
    (ws / "latest_level_transfer_probe.json").write_text(json.dumps({
        "carrier_evidence_identity": binding,
        "post_depth": 99,
        "exact_actions": 4,
        "local_transfer": {"exact_steps_after_first_step_repair": 99},
    }))

    metrics = build_p0_metrics(tmp_path)

    assert metrics["transfer"]["identity_status"] == "historical_or_unbound"
    assert metrics["transfer"]["historical_receipt_present"] is True
    assert metrics["transfer"]["empirical_transfer_depth"] is None
    assert (
        metrics["metric_contracts"]["transfer.empirical_transfer_depth"]["status"]
        == "missing_evidence"
    )


def test_p0_metrics_count_environment_verified_self_play_epochs(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "latest_self_play_probe.json").write_text(json.dumps({
        "schema": "ztare-arc3-self-play-probe-v1",
        "status": "goal_reached",
        "levels_before": 1,
        "levels_after": 2,
        "levels_gained": 1,
        "steps_executed": 45,
        "replans": 0,
        "seed_receipt": {
            "interventions_executed": 19,
            "observed_progress_after": 1,
        },
    }))

    metrics = build_p0_metrics(tmp_path)

    assert metrics["scoreboard"]["levels_beaten"] == 2
    assert metrics["scoreboard"]["actions_per_level"] == [19, 45]
    assert [row["target_epoch"] for row in metrics["scoreboard"]["verified_skill_trials"]] == [1, 2]
    assert all(
        row["establishes_task_discharge"] is False
        for row in metrics["scoreboard"]["verified_skill_trials"]
    )
    assert metrics["control_readiness"]["status"] == "observer_only"


def test_p0_metrics_preserve_terminal_closure_candidate_boundary(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "terminal_closure_audit.json").write_text(
        json.dumps(
            {
                "schema": "ztare-worldmodel-terminal-closure-audit-v1",
                "status": "terminal_closed_candidate_unpromoted",
                "task_discharged": True,
                "level_closed": True,
                "search_control_closed": True,
                "terminal_report": {
                    "result": "beat",
                    "levels_gained": 1,
                    "terminal_witness_sha": "abc123",
                },
                "claim_boundaries": {
                    "candidate_promotion": {
                        "proven": False,
                        "reason": "terminal_closure_does_not_promote_candidate",
                    },
                    "autonomous_completion": {
                        "proven": False,
                        "reason": "missing_explicit_unassisted_terminal_provenance",
                    },
                },
                "authority": {
                    "authority_ladder_ok": True,
                    "candidate_promotion_used_for_closure": False,
                },
                "closure_verification": {"ok": True},
            }
        )
    )

    metrics = build_p0_metrics(tmp_path)

    assert metrics["scoreboard"]["levels_beaten"] == 0
    closure = metrics["closure_boundaries"]
    assert closure["task_discharged"] is True
    assert closure["level_closed"] is False
    assert closure["level_projection_status"] == "adapter_progress_required"
    assert closure["search_control_closed"] is True
    assert closure["candidate_promoted_by_terminal"] is False
    assert closure["candidate_promotion_proven"] is False
    assert closure["candidate_promotion_reason"] == "terminal_closure_does_not_promote_candidate"
    assert closure["autonomous_completion_proven"] is False
    assert closure["terminal_witness_sha"] == "abc123"
    assert closure["verification_ok"] is True


def test_p0_metrics_count_latest_strategy_card_disposition(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    family = "same-family"
    (ws / "strategy_experiments.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema": "strategy-experiment-v1",
                        "failure_family": family,
                        "failure_family_sha": "sha1",
                        "disposition": "open",
                    }
                ),
                json.dumps(
                    {
                        "schema": "strategy-experiment-v1",
                        "failure_family": family,
                        "failure_family_sha": "sha1",
                        "disposition": "rejected",
                    }
                ),
                json.dumps(
                    {
                        "schema": "strategy-experiment-v1",
                        "failure_family": "other",
                        "failure_family_sha": "sha2",
                        "disposition": "open",
                    }
                ),
            ]
        )
        + "\n"
    )

    metrics = build_p0_metrics(tmp_path)

    assert metrics["compression"]["open_strategy_cards"] == 1
