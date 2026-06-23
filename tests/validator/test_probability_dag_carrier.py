from __future__ import annotations

import json
from pathlib import Path

from ztare.validator.probability_dag_carrier import (
    build_probability_dag_graph_carrier,
    render_probability_dag_vulnerability_prompt,
    score_probability_dag_nodes,
    summarize_probability_dag_graph_carrier,
)
from ztare.research_director.graph_carrier_actions import graph_carrier_action_rows


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_score_probability_dag_nodes_uses_max_outgoing_weight_and_stable_ties() -> None:
    dag = {
        "nodes": [
            {"id": "b", "label": "B", "probability": 0.5, "watch_signal": "b"},
            {"id": "a", "label": "A", "probability": 0.5, "watch_signal": "a"},
            {"id": "c", "label": "C", "probability": "bad"},
            {"id": "d", "label": "D", "probability": 0.9},
        ],
        "edges": [
            {"from": "b", "to": "x", "weight": 0.2},
            {"from": "b", "to": "y", "weight": 0.8},
            {"from": "a", "to": "x", "weight": 0.8},
            {"from": "c", "to": "x", "weight": 1.0},
        ],
    }

    scored = score_probability_dag_nodes(dag)

    assert [row["node_id"] for row in scored] == ["a", "b", "c"]
    assert [row["urgency"] for row in scored] == [0.4, 0.4, 0.0]
    assert scored[1]["edge_weight"] == 0.8
    assert scored[2]["probability"] == 0.0


def test_render_probability_dag_vulnerability_prompt_orders_low_probability_first() -> None:
    prompt = render_probability_dag_vulnerability_prompt(
        {
            "outcome": {"probability": 0.31},
            "nodes": [
                {"id": "safe", "label": "Safer", "probability": 0.9},
                {
                    "id": "weak",
                    "label": "Weakest",
                    "probability": 0.1,
                    "watch_signal": "boundary",
                },
            ],
        }
    )

    assert "PROBABILITY DAG" in prompt
    assert "Overall outcome probability: 0.31" in prompt
    assert prompt.index("weak") < prompt.index("safe")
    assert "watch: boundary" in prompt


def test_probability_dag_graph_carrier_records_strategy_change(tmp_path: Path) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [{"id": "n1", "probability": 0.7, "watch_signal": "source"}],
            "edges": [{"from": "n1", "to": "outcome", "weight": 0.9}],
        },
    )
    _write_jsonl(
        workspace / "dag_steering_log.jsonl",
        [{"selected_node_id": "n1", "selected_urgency": 0.63}],
    )

    carrier = build_probability_dag_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["graph_id"] == "demo:latest_probability_dag"
    assert carrier["source_artifacts"] == ["projects/demo/latest_probability_dag.json"]
    assert carrier["node_count"] == 1
    assert carrier["edge_count"] == 1
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "selected_next_discriminator": (
            "DAG steering selected node 'n1' as the next focus"
        ),
        "runtime_consumable": True,
    }
    assert carrier["validation"] == {"ok": True, "errors": [], "warnings": []}
    assert summarize_probability_dag_graph_carrier(carrier)["validation"]["ok"] is True


def test_probability_dag_graph_carrier_scores_pending_focus_without_log(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [
                {"id": "n1", "probability": 0.7, "watch_signal": "source"},
                {"id": "n2", "probability": 0.9, "watch_signal": "scope"},
            ],
            "edges": [
                {"from": "n1", "to": "outcome", "weight": 0.9},
                {"from": "n2", "to": "outcome", "weight": 0.1},
            ],
        },
    )

    carrier = build_probability_dag_graph_carrier(project_dir=project, repo=tmp_path)

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "strategy_change",
        "selected_next_discriminator": (
            "DAG scoring selects node 'n1' as the pending in-loop focus; "
            "watch signal: source"
        ),
        "runtime_consumable": True,
    }
    assert carrier["diagnostics"][0]["result_summary"] == (
        "no steering row yet; scored current DAG and selected 'n1' with urgency 0.630"
    )
    assert graph_carrier_action_rows([carrier]) == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo",
            "graph_id": "demo:latest_probability_dag",
            "reason": (
                "DAG scoring selects node 'n1' as the pending in-loop focus; "
                "watch signal: source"
            ),
            "recommended_actor": "autoresearch_loop",
        }
    ]
    assert carrier["validation"]["ok"] is True


def test_probability_dag_graph_carrier_marks_pending_focus_gated_off(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [{"id": "n1", "probability": 0.7, "watch_signal": "source"}],
            "edges": [{"from": "n1", "to": "outcome", "weight": 0.9}],
        },
    )

    carrier = build_probability_dag_graph_carrier(
        project_dir=project,
        repo=tmp_path,
        rubric_data={"enable_dag_steering": False},
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": (
            "DAG has a scorable pending focus, but the effective rubric does "
            "not enable DAG steering"
        ),
        "pending_next_discriminator": (
            "DAG scoring selects node 'n1' as the pending in-loop focus; "
            "watch signal: source"
        ),
        "runtime_consumable": False,
    }
    assert graph_carrier_action_rows([carrier]) == []
    assert carrier["validation"]["ok"] is True


def test_probability_dag_graph_carrier_records_no_strategy_change_when_unscorable(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [{"id": "n1", "probability": 0.7}],
            "edges": [],
        },
    )

    carrier = build_probability_dag_graph_carrier(project_dir=project, repo=tmp_path)

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": (
            "probability DAG exists, but no steering row or scorable outgoing "
            "edge was found"
        ),
    }
    assert carrier["diagnostics"][0]["result_summary"] == (
        "probability DAG present without a scorable steering decision"
    )
    assert carrier["validation"]["ok"] is True


def test_probability_dag_graph_carrier_demotes_stale_steering_row(
    tmp_path: Path,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo"
    workspace = project / "workspace"
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [{"id": "current", "probability": 0.7}],
            "edges": [{"from": "current", "to": "outcome", "weight": 0.9}],
        },
    )
    _write_jsonl(
        workspace / "dag_steering_log.jsonl",
        [{"selected_node_id": "old_node", "selected_urgency": 0.91}],
    )

    carrier = build_probability_dag_graph_carrier(
        project_dir=project,
        workspace_dir=workspace,
        repo=repo,
    )

    assert carrier is not None
    assert carrier["decision_receipt"] == {
        "effect": "misleading_or_noise",
        "reason": (
            "DAG steering selected stale node 'old_node'; node is absent from "
            "current latest_probability_dag.json"
        ),
    }
    assert carrier["diagnostics"][0]["result_summary"] == (
        "latest steering selected stale node 'old_node'; no strategy change admitted"
    )
    assert carrier["validation"] == {"ok": True, "errors": [], "warnings": []}
    assert graph_carrier_action_rows([carrier]) == [
        {
            "action_type": "demote_graph_signal",
            "work_mode": "out_of_loop_review",
            "project": "demo",
            "graph_id": "demo:latest_probability_dag",
            "reason": (
                "DAG steering selected stale node 'old_node'; node is absent from "
                "current latest_probability_dag.json"
            ),
            "recommended_actor": "research_director",
        }
    ]
