"""Import-safe probability-DAG steering context for autoresearch."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.validator.probability_dag_carrier import (
    read_json_object,
    render_probability_dag_vulnerability_prompt,
    score_probability_dag_nodes,
)


def compute_dag_steering_context(
    project_dir: str | Path,
    rubric_data: dict[str, Any],
    workspace_dir: str | Path,
) -> str:
    """Render the probability-DAG prompt context and optional steering receipt.

    The vulnerable-assumption block is read-only and appears whenever
    ``latest_probability_dag.json`` is usable. Active steering and
    ``workspace/dag_steering_log.jsonl`` writes remain gated by
    ``enable_dag_steering`` in the effective rubric.
    """
    project_path = Path(project_dir)
    workspace_path = Path(workspace_dir)
    dag_path = project_path / "latest_probability_dag.json"
    if not dag_path.exists():
        return ""

    dag = read_json_object(dag_path)
    vulnerability_block = render_probability_dag_vulnerability_prompt(dag)
    if not rubric_data.get("enable_dag_steering"):
        return vulnerability_block

    scored = score_probability_dag_nodes(dag)
    if not scored:
        return vulnerability_block

    top_node_id = str(scored[0]["node_id"])
    log_path = workspace_path / "dag_steering_log.jsonl"
    recent_top = _recent_steering_node_ids(log_path)

    pick = scored[0]
    if (
        len(scored) >= 2
        and len(recent_top) >= 3
        and all(node_id == top_node_id for node_id in recent_top[-3:])
    ):
        pick = scored[1]
        hysteresis_bumped = True
    else:
        hysteresis_bumped = False

    if len(recent_top) >= 5 and all(node_id == top_node_id for node_id in recent_top[-5:]):
        _emit_dag_stagnation_signal(project_path, top_node_id)

    urgency = float(pick["urgency"])
    node_id = str(pick["node_id"])
    node = pick["node"]
    watch = str(node.get("watch_signal") or "").strip()
    label = str(node.get("label") or "").strip()

    steering_block = (
        "\n\n--- GP-134 / DAG STEERING (priority focus) ---\n"
        f"The Bayesian DAG currently identifies node {node_id!r} as highest-urgency "
        f"(urgency={urgency:.3f}, probability={node.get('probability')}, "
        f"edge_weight={pick['edge'].get('weight')}"
        f"{'; hysteresis-bumped from #1 to #2 due to 3 consecutive iters at same top' if hysteresis_bumped else ''}).\n"
        f"Node label: {label}\n"
        f"Watch signal: {watch}\n"
        "Weight ~50% of your mutation effort on resolving this specific watch signal. "
        "You may pursue other improvements in parallel, but the next iteration's thesis "
        "should produce specific progress on the named node. "
        "Do NOT treat this as an exclusive override - continue addressing other gaps.\n"
        "--- END DAG STEERING ---\n"
    )

    _append_steering_receipt(
        log_path,
        node_id=node_id,
        urgency=urgency,
        node=node,
        edge=pick["edge"],
        hysteresis_bumped=hysteresis_bumped,
        scored=scored,
    )

    blocks = [steering_block]
    if vulnerability_block:
        blocks.append(vulnerability_block)
    return "\n\n".join(blocks)


def _recent_steering_node_ids(log_path: Path) -> list[str]:
    if not log_path.exists():
        return []
    recent: list[str] = []
    try:
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []
    for line in lines[-5:]:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            recent.append(str(rec.get("selected_node_id") or ""))
    return recent


def _emit_dag_stagnation_signal(project_path: Path, top_node_id: str) -> None:
    try:
        from ztare.signals import damage as _damage

        _damage.emit(
            source=f"dag_steering:{project_path.name}",
            kind="dag_stagnation",
            detail=(
                f"DAG node {top_node_id!r} has been top-urgency for 5+ iters; "
                "mutator may be unable to resolve within current grammar. "
                "Consider rubric/charter revision or scope change."
            ),
            severity="warn",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[dag-steering] damage-signal emit failed: {exc}")


def _append_steering_receipt(
    log_path: Path,
    *,
    node_id: str,
    urgency: float,
    node: dict[str, Any],
    edge: dict[str, Any],
    hysteresis_bumped: bool,
    scored: list[dict[str, Any]],
) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "selected_node_id": node_id,
            "selected_urgency": urgency,
            "selected_probability": node.get("probability"),
            "selected_edge_weight": edge.get("weight"),
            "hysteresis_bumped": hysteresis_bumped,
            "all_scored": [(row["urgency"], row["node_id"]) for row in scored],
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as exc:  # noqa: BLE001
        print(f"[dag-steering] log write failed: {exc}")
