from __future__ import annotations

import json

from src.ztare.reports.blitz_survival_report import (
    build_blitz_survival_report,
    render_blitz_survival_markdown,
)


def _append_jsonl(path, row):
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def test_blitz_survival_report_joins_tournament_eval_and_telemetry(tmp_path):
    _append_jsonl(
        tmp_path / "parallel_blitz_log.jsonl",
        {
            "iter": 1,
            "k": 3,
            "decision_reason": "stagnation_count=2 >= 1",
            "n_after_recombination": 5,
            "n_crossovers": 2,
            "fusion_succeeded": False,
            "winner_id": 1,
            "winner_persona": "munger_inversion",
            "winner_stage_origin": "mutator_munger_inversion",
            "scores": [
                {"worker_id": 0, "persona": "newton_discovery", "score": 2.1},
                {"worker_id": 1, "persona": "munger_inversion", "score": 5.5},
            ],
        },
    )
    _append_jsonl(
        tmp_path / "pipeline_log.jsonl",
        {
            "record_type": "candidate",
            "iter": 1,
            "candidate_id": "iter001_munger_w01",
            "score": 5.5,
            "selected_as_winner": True,
        },
    )
    _append_jsonl(
        tmp_path / "eval_history.jsonl",
        {
            "iteration": 1,
            "score": 73,
            "weakest_point": "needs a sharper holdout prediction",
        },
    )
    _append_jsonl(
        tmp_path / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 1,
            "score": 73,
            "champion_promoted": True,
            "gate_failure_count": 0,
            "failed_gate_ids": [],
        },
    )

    report = build_blitz_survival_report(tmp_path)

    assert report["summary"]["num_blitz_iterations"] == 1
    assert report["summary"]["downstream_eval_rate"] == 1.0
    assert report["summary"]["champion_promotion_rate"] == 1.0
    assert report["summary"]["gate_clean_positive_rate"] == 1.0
    row = report["rows"][0]
    assert row["tournament_score"] == 5.5
    assert row["selected_candidate_score"] == 5.5
    assert row["eval_score"] == 73
    assert row["survival_class"] == "champion_promoted"
    assert "munger_inversion" in render_blitz_survival_markdown(report)


def test_blitz_survival_report_marks_missing_downstream_eval(tmp_path):
    _append_jsonl(
        tmp_path / "parallel_blitz_log.jsonl",
        {
            "iter": 2,
            "k": 3,
            "decision_reason": "force=True",
            "n_after_recombination": 3,
            "n_crossovers": 0,
            "fusion_succeeded": False,
            "winner_id": 0,
            "winner_persona": "newton_discovery",
            "winner_stage_origin": "mutator_newton_discovery",
            "scores": [{"worker_id": 0, "persona": "newton_discovery", "score": 4.0}],
        },
    )
    _append_jsonl(
        tmp_path / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 2,
            "score": None,
            "champion_promoted": False,
            "gate_failure_count": 0,
            "failed_gate_ids": [],
        },
    )

    report = build_blitz_survival_report(tmp_path)

    assert report["summary"]["num_blitz_iterations"] == 1
    assert report["summary"]["num_downstream_eval_present"] == 0
    assert report["summary"]["survival_class_counts"] == {"no_downstream_eval": 1}
    assert report["rows"][0]["downstream_eval_present"] is False
