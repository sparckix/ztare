from __future__ import annotations

import json

from ztare.orchestrator.iteration_telemetry import append_iteration_telemetry
from ztare.validator.core.compression_progress import (
    evaluate_compression_progress,
    observations_from_rows,
)


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
        raw_judge_score=75,
        score_cap_reason="Global Gate Hard Fail: global_extrapolation_gap",
        score_cap_source="global_gates.hard_fail",
    )

    row = json.loads((tmp_path / "iteration_telemetry.jsonl").read_text())
    assert row["information_yield_rationale"] == (
        "Information yield is low; refresh specialists."
    )
    assert row["raw_judge_score"] == 75
    assert row["score_cap_reason"] == "Global Gate Hard Fail: global_extrapolation_gap"
    assert row["score_cap_source"] == "global_gates.hard_fail"


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


def test_iteration_telemetry_records_mutator_fallback(tmp_path):
    append_iteration_telemetry(
        tmp_path,
        run_id=123,
        iteration_index=1,
        iteration_start_utc="2026-06-13T00:00:00+00:00",
        loop_control_action="normal",
        score=0,
        score_improved=False,
        champion_promoted=False,
        stagnation_count=1,
        gate_engagement=True,
        gate_failure_count=1,
        failed_gate_ids=["global_extrapolation_gap"],
        escalation_flags={},
        falsification_mode="bounded_discriminator",
        mutator_model_id="kimi-k2.6",
        mutator_effective_model_ids=["gemini-3.1-pro-preview"],
        mutator_fallback_events=[
            {"from": "kimi-k2.6", "to": "gemini-3.1-pro-preview"}
        ],
        judge_model_id="grok-4.3",
        mutator_usage=_usage(),
        judge_usage=_usage(),
        pending_loop_action="UNDERIDENTIFIED",
    )

    row = json.loads((tmp_path / "iteration_telemetry.jsonl").read_text())
    assert row["mutator_model_id"] == "kimi-k2.6"
    assert row["mutator_effective_model_ids"] == ["gemini-3.1-pro-preview"]
    assert row["mutator_fallback_events"] == [
        {"from": "kimi-k2.6", "to": "gemini-3.1-pro-preview"}
    ]


def test_iteration_telemetry_records_compression_progress_inputs(tmp_path):
    (tmp_path / "fit_features_result.json").write_text(
        json.dumps({"success": True, "bic": 42.5, "k_params": 3, "n_fit_rows": 40})
    )

    append_iteration_telemetry(
        tmp_path,
        run_id=123,
        iteration_index=1,
        iteration_start_utc="2026-06-13T00:00:00+00:00",
        loop_control_action="normal",
        score=55,
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
    assert row["compression_progress"]["status"] == "available"
    assert row["compression_progress"]["family"] == "fit_bic"
    assert row["compression_progress"]["complexity"] == 42.5
    assert row["compression_progress_advice"]["status"] == "no_signal"
    decision = evaluate_compression_progress(observations_from_rows([row, {
        "iteration_index": 2,
        "compression_progress": {"family": "fit_bic", "complexity": 40.0},
    }]))
    assert decision.recommendation == "continue"

    (tmp_path / "fit_features_result.json").write_text(
        json.dumps({"success": True, "bic": 40.0, "k_params": 3, "n_fit_rows": 40})
    )
    append_iteration_telemetry(
        tmp_path,
        run_id=123,
        iteration_index=2,
        iteration_start_utc="2026-06-13T00:01:00+00:00",
        loop_control_action="normal",
        score=56,
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

    rows = [
        json.loads(line)
        for line in (tmp_path / "iteration_telemetry.jsonl").read_text().splitlines()
    ]
    assert rows[-1]["compression_progress_advice"]["status"] == "available"
    assert rows[-1]["compression_progress_advice"]["recommendation"] == "continue"
