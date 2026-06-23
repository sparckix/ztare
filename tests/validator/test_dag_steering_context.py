from __future__ import annotations

import json
from pathlib import Path

from ztare.validator.dag_steering_context import compute_dag_steering_context


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_dag_steering_context_import_safe_and_read_only_when_disabled(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "outcome": {"probability": 0.4},
            "nodes": [
                {"id": "n1", "label": "Weak", "probability": 0.2},
                {"id": "n2", "label": "Safer", "probability": 0.8},
            ],
            "edges": [{"from": "n1", "to": "outcome", "weight": 0.9}],
        },
    )

    context = compute_dag_steering_context(
        project,
        {"enable_dag_steering": False},
        workspace,
    )

    assert "PROBABILITY DAG" in context
    assert "YOUR THESIS'S VULNERABLE ASSUMPTIONS" in context
    assert "GP-134 / DAG STEERING" not in context
    assert not (workspace / "dag_steering_log.jsonl").exists()


def test_dag_steering_context_logs_highest_urgency_node(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "outcome": {"probability": 0.4},
            "nodes": [
                {
                    "id": "n1",
                    "label": "Boundary",
                    "probability": 0.7,
                    "watch_signal": "boundary stress",
                },
                {
                    "id": "n2",
                    "label": "Scope",
                    "probability": 0.9,
                    "watch_signal": "scope stress",
                },
            ],
            "edges": [
                {"from": "n1", "to": "outcome", "weight": 0.9},
                {"from": "n2", "to": "outcome", "weight": 0.1},
            ],
        },
    )

    context = compute_dag_steering_context(
        project,
        {"enable_dag_steering": True},
        workspace,
    )

    assert "GP-134 / DAG STEERING" in context
    assert "node 'n1' as highest-urgency" in context
    assert "Watch signal: boundary stress" in context
    rows = [
        json.loads(line)
        for line in (workspace / "dag_steering_log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert rows[-1]["selected_node_id"] == "n1"
    assert rows[-1]["selected_urgency"] == 0.63
    assert rows[-1]["hysteresis_bumped"] is False


def test_dag_steering_context_hysteresis_bumps_repeated_top_node(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "outcome": {"probability": 0.4},
            "nodes": [
                {"id": "n1", "label": "Boundary", "probability": 0.7},
                {"id": "n2", "label": "Scope", "probability": 0.6},
            ],
            "edges": [
                {"from": "n1", "to": "outcome", "weight": 0.9},
                {"from": "n2", "to": "outcome", "weight": 0.8},
            ],
        },
    )
    _write_jsonl(
        workspace / "dag_steering_log.jsonl",
        [
            {"selected_node_id": "n1"},
            {"selected_node_id": "n1"},
            {"selected_node_id": "n1"},
        ],
    )

    context = compute_dag_steering_context(
        project,
        {"enable_dag_steering": True},
        workspace,
    )

    assert "node 'n2' as highest-urgency" in context
    assert "hysteresis-bumped from #1 to #2" in context
    rows = [
        json.loads(line)
        for line in (workspace / "dag_steering_log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert rows[-1]["selected_node_id"] == "n2"
    assert rows[-1]["hysteresis_bumped"] is True
