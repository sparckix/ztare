from __future__ import annotations

import json

from src.ztare.orchestrator.iteration_telemetry import append_iteration_telemetry


def _usage() -> dict:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "thinking_tokens": 0,
        "estimated_cost_usd": 0.0,
        "cost_known": False,
    }


def test_iteration_telemetry_records_information_yield_rationale(tmp_path):
    append_iteration_telemetry(
        tmp_path,
        run_id=123,
        iteration_index=1,
        iteration_start_utc="2026-06-13T00:00:00+00:00",
        loop_control_action="normal",
        score=42,
        score_improved=False,
        champion_promoted=False,
        stagnation_count=2,
        gate_engagement=False,
        gate_failure_count=0,
        failed_gate_ids=[],
        escalation_flags={},
        falsification_mode="bounded_discriminator",
        mutator_model_id="mutator",
        judge_model_id="judge",
        mutator_usage=_usage(),
        judge_usage=_usage(),
        pending_loop_action="REFRESH_SPECIALISTS",
        information_yield_rationale="Information yield is low; refresh specialists.",
    )

    row = json.loads((tmp_path / "iteration_telemetry.jsonl").read_text())
    assert row["information_yield_rationale"] == (
        "Information yield is low; refresh specialists."
    )


def test_iteration_telemetry_defaults_empty_information_yield_rationale(tmp_path):
    append_iteration_telemetry(
        tmp_path,
        run_id=123,
        iteration_index=1,
        iteration_start_utc="2026-06-13T00:00:00+00:00",
        loop_control_action="normal",
        score=42,
        score_improved=True,
        champion_promoted=True,
        stagnation_count=0,
        gate_engagement=True,
        gate_failure_count=0,
        failed_gate_ids=[],
        escalation_flags={},
        falsification_mode="numerical_proof",
        mutator_model_id="mutator",
        judge_model_id="judge",
        mutator_usage=_usage(),
        judge_usage=_usage(),
        pending_loop_action="CONTINUE",
    )

    row = json.loads((tmp_path / "iteration_telemetry.jsonl").read_text())
    assert row["information_yield_rationale"] == ""
