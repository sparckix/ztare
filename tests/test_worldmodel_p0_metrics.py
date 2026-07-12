from __future__ import annotations

import json
from pathlib import Path

from ztare.worldmodel.p0_metrics import build_p0_metrics, write_p0_metrics


def test_p0_metrics_summarize_transfer_and_compression(tmp_path: Path) -> None:
    project = tmp_path
    ws = project / "workspace"
    ws.mkdir()
    (ws / "latest_level_transfer_probe.json").write_text(
        json.dumps(
            {
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

    assert metrics["schema"] == "ztare-arc3-p0-metrics-v1"
    assert metrics["scoreboard"]["levels_beaten"] == 1
    assert metrics["scoreboard"]["actions_per_level"] == [18]
    assert metrics["scoreboard"]["relative_human_action_efficiency"] == 0.62
    assert isinstance(metrics["information_theory"]["catalog_size"], int)
    assert metrics["information_theory"]["catalog_growth_velocity"] == 1.0
    assert metrics["information_theory"]["operator_reusability_index"] is None
    assert metrics["information_theory"]["temporal_admissibility_leakage"] == 1.0
    assert metrics["transfer"]["empirical_transfer_depth"] == 4
    assert metrics["transfer"]["local_steps_tested"] == 16
    assert metrics["transfer"]["first_step_repair_generalizes_to_depth"] is False
    assert metrics["compression"]["catalog_proposals"] == 2
    assert metrics["compression"]["catalog_promotions"] == 1
    assert metrics["compression"]["catalog_growth_rate"] == 1.0
    assert metrics["compression"]["operator_reuse_count"] == 1
    assert metrics["kernel_pressure"]["temporal_admissibility_failures"] == 1
    assert metrics["reachability"]["abstract_vertices"] == 7
    assert metrics["reachability"]["abstract_edges"] == 9
    assert metrics["reachability"]["abstract_entropy_bits"] > 4.0


def test_write_p0_metrics_writes_project_workspace_receipt(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()

    path = write_p0_metrics(tmp_path)

    assert path == ws / "p0_metrics.json"
    assert json.loads(path.read_text())["schema"] == "ztare-arc3-p0-metrics-v1"


def test_p0_metrics_preserve_terminal_closure_candidate_boundary(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "terminal_closure_audit.json").write_text(
        json.dumps(
            {
                "schema": "ztare-worldmodel-terminal-closure-audit-v1",
                "status": "terminal_closed_candidate_unpromoted",
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

    assert metrics["scoreboard"]["levels_beaten"] == 1
    closure = metrics["closure_boundaries"]
    assert closure["level_closed"] is True
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


def test_path_a_promotion_counted_by_p0_metrics(tmp_path: Path) -> None:
    """FIX 2: Path A (grammar_reflex) accepted card writes a promotion-contract
    row so p0_metrics.catalog_promotions counts it alongside Path B promotions."""
    from ztare.worldmodel.grammar_extension import ExtensionReceipt, _write_promotion_contract

    ws = tmp_path / "workspace"
    ws.mkdir()
    # Simulate what grammar_reflex writes on DISPOSITION_ACCEPTED (FIX 2 path).
    receipt = ExtensionReceipt(
        env_hint=str(tmp_path),
        model_id="codex",
        prompt_sha256="",
        name="when_effect_rule_coupling",
        python="",
        rationale="fired-this-step coupling",
        verdict="promoted",
        detail="real replay improved",
    )
    _write_promotion_contract(tmp_path, receipt)

    metrics = build_p0_metrics(tmp_path)
    assert metrics["compression"]["catalog_promotions"] == 1, (
        "Path A promotion must be counted by p0_metrics.catalog_promotions"
    )
