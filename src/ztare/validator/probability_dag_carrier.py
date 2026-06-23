"""Import-safe helpers for autoresearch probability-DAG carriers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.common.graph_carrier import validate_graph_carrier


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object; return {} for absent, malformed, or non-object files."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def last_jsonl_object(path: Path) -> dict[str, Any]:
    """Return the last object-shaped JSONL row; ignore malformed rows."""
    if not path.exists():
        return {}
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return {}
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def score_probability_dag_nodes(dag: dict[str, Any]) -> list[dict[str, Any]]:
    """Score nodes with the same urgency rule used by DAG steering.

    Urgency is `node.probability * max_outgoing_edge.weight`. Results are
    sorted descending by urgency and then ascending by node id for stable ties.
    """
    nodes = dag.get("nodes")
    edges = dag.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return []

    node_by_id = {
        str(node.get("id")): node
        for node in nodes
        if isinstance(node, dict) and str(node.get("id") or "").strip()
    }
    outgoing: dict[str, dict[str, Any]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from") or "").strip()
        if not src:
            continue
        weight = _float_or_zero(edge.get("weight"))
        current = outgoing.get(src)
        if current is None or weight > _float_or_zero(current.get("weight")):
            outgoing[src] = edge

    scored: list[dict[str, Any]] = []
    for node_id, node in node_by_id.items():
        edge = outgoing.get(node_id)
        if edge is None:
            continue
        probability = _float_or_zero(node.get("probability"))
        edge_weight = _float_or_zero(edge.get("weight"))
        scored.append(
            {
                "node_id": node_id,
                "urgency": probability * edge_weight,
                "probability": probability,
                "edge_weight": edge_weight,
                "label": str(node.get("label") or "").strip(),
                "watch_signal": str(node.get("watch_signal") or "").strip(),
                "node": node,
                "edge": edge,
            }
        )
    scored.sort(key=lambda row: (-float(row["urgency"]), str(row["node_id"])))
    return scored


def render_probability_dag_vulnerability_prompt(dag: dict[str, Any]) -> str:
    """Render the legacy vulnerable-assumptions prompt block from DAG contents."""
    nodes = dag.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ""
    object_nodes = [node for node in nodes if isinstance(node, dict)]
    if not object_nodes:
        return ""
    nodes_sorted = sorted(object_nodes, key=lambda node: _float_or_default(node.get("probability"), 1.0))
    outcome = dag.get("outcome")
    if not isinstance(outcome, dict):
        outcome = {}
    lines = [
        "### PROBABILITY DAG - YOUR THESIS'S VULNERABLE ASSUMPTIONS",
        f"Overall outcome probability: {outcome.get('probability', '?')}",
        "Nodes ranked by vulnerability (WEAKEST FIRST):",
    ]
    for node in nodes_sorted[:3]:
        lines.append(
            f"  - {node.get('id', '?')}: \"{node.get('label', '?')}\" "
            f"(p={node.get('probability', '?')}) "
            f"- watch: {node.get('watch_signal', 'none')}"
        )
    lines.append("Your next thesis MUST strengthen the weakest node above.")
    return "\n".join(lines)


def build_probability_dag_graph_carrier(
    *,
    project_dir: Path,
    workspace_dir: Path | None = None,
    repo: Path | None = None,
    rubric_data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build the canonical graph-carrier payload for a project's latest DAG."""
    dag_path = project_dir / "latest_probability_dag.json"
    if not dag_path.exists():
        return None
    dag = read_json_object(dag_path)
    nodes = dag.get("nodes")
    edges = dag.get("edges")
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []

    node_keys = sorted(
        {
            str(key)
            for node in nodes
            if isinstance(node, dict)
            for key in node
        }
    )
    edge_keys = sorted(
        {
            str(key)
            for edge in edges
            if isinstance(edge, dict)
            for key in edge
        }
    )
    workspace = workspace_dir or project_dir / "workspace"
    steering_row = last_jsonl_object(workspace / "dag_steering_log.jsonl")
    selected_node_id = str(steering_row.get("selected_node_id") or "").strip()
    current_node_ids = {
        str(node.get("id") or "").strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("id") or "").strip()
    }
    scored = score_probability_dag_nodes(dag)
    if selected_node_id and selected_node_id in current_node_ids:
        decision_receipt = {
            "effect": "strategy_change",
            "selected_next_discriminator": (
                f"DAG steering selected node {selected_node_id!r} as the next focus"
            ),
            "runtime_consumable": True,
        }
        result_summary = (
            f"latest steering selected {selected_node_id!r}"
            f" with urgency {steering_row.get('selected_urgency')}"
        )
    elif selected_node_id:
        decision_receipt = {
            "effect": "misleading_or_noise",
            "reason": (
                f"DAG steering selected stale node {selected_node_id!r}; "
                "node is absent from current latest_probability_dag.json"
            ),
        }
        result_summary = (
            f"latest steering selected stale node {selected_node_id!r}; "
            "no strategy change admitted"
        )
    elif scored:
        pick = scored[0]
        node_id = str(pick["node_id"])
        watch_signal = str(pick.get("watch_signal") or "").strip()
        suffix = f"; watch signal: {watch_signal}" if watch_signal else ""
        selected_next_discriminator = (
            f"DAG scoring selects node {node_id!r} as the pending in-loop focus"
            f"{suffix}"
        )
        steering_enabled = (
            True
            if rubric_data is None
            else bool(rubric_data.get("enable_dag_steering"))
        )
        if steering_enabled:
            decision_receipt = {
                "effect": "strategy_change",
                "selected_next_discriminator": selected_next_discriminator,
                "runtime_consumable": True,
            }
        else:
            decision_receipt = {
                "effect": "no_strategy_change",
                "reason": (
                    "DAG has a scorable pending focus, but the effective rubric "
                    "does not enable DAG steering"
                ),
                "pending_next_discriminator": selected_next_discriminator,
                "runtime_consumable": False,
            }
        result_summary = (
            f"no steering row yet; scored current DAG and selected {node_id!r} "
            f"with urgency {float(pick['urgency']):.3f}"
        )
    else:
        decision_receipt = {
            "effect": "no_strategy_change",
            "reason": (
                "probability DAG exists, but no steering row or scorable outgoing "
                "edge was found"
            ),
        }
        result_summary = "probability DAG present without a scorable steering decision"

    carrier = {
        "graph_id": f"{project_dir.name}:latest_probability_dag",
        "graph_kind": "probability_dag",
        "producer": "latest_probability_dag.json",
        "source_artifacts": [_rel(dag_path, repo) if repo is not None else str(dag_path)],
        "consumer": "compute_dag_steering_context",
        "freshness_rule": "rerun after eval_history or probability DAG updates",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_vocabulary": node_keys or ["probability_dag_node"],
        "edge_vocabulary": edge_keys or ["probability_dag_edge"],
        "diagnostics": [
            {
                "method": "edge_weight_times_probability",
                "baseline": "previous run order or no steering",
                "result_summary": result_summary,
            }
        ],
        "noise_filter": "ignore malformed nodes without ids and edges without sources",
        "decision_receipt": decision_receipt,
        "library_anchor": "standard library JSON plus local DAG parser",
        "literature_anchor": "directed acyclic graph scheduling and dependency analysis",
    }
    validation = validate_graph_carrier(carrier)
    carrier["validation"] = {
        "ok": validation.ok,
        "errors": validation.errors,
        "warnings": validation.warnings,
    }
    return carrier


def summarize_probability_dag_graph_carrier(carrier: dict[str, Any]) -> dict[str, Any]:
    """Return the compact carrier view used in trace reports."""
    return {
        "graph_id": carrier["graph_id"],
        "graph_kind": carrier["graph_kind"],
        "source_artifacts": carrier["source_artifacts"],
        "node_count": carrier["node_count"],
        "edge_count": carrier["edge_count"],
        "decision_receipt": carrier["decision_receipt"],
        "validation": carrier["validation"],
    }


def _float_or_zero(value: Any) -> float:
    return _float_or_default(value, 0.0)


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _rel(path: Path, repo: Path | None) -> str:
    if repo is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)
