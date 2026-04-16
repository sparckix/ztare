"""GP-070 Goal Orchestrator — Config parser (C-9, C-13, C-16).

Reads YAML goal-type configs and validates against the spec constraints.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

from src.ztare.orchestration.core import GoalConfig, StageDefinition, validate_stage_graph
from src.ztare.orchestration.predicates import validate_predicate_schema

GOAL_TYPES_DIR = Path("research_areas/private/goal_types")

REGISTERED_ADAPTERS = {
    "agent",
    "findings_runner",
    "autoresearch",
    "program_autoloop",
    "operator_manual",
}


def parse_goal_config(config_path: Path) -> tuple[GoalConfig | None, list[str]]:
    """Parse a YAML goal-type config and validate it.

    Returns (config, errors). If errors is non-empty, config may be None.
    """
    errors: list[str] = []

    if not config_path.exists():
        return None, [f"Config file not found: {config_path}"]

    try:
        raw = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as e:
        return None, [f"YAML parse error: {e}"]

    if not isinstance(raw, dict):
        return None, ["Config must be a YAML mapping."]

    schema_version = raw.get("schema_version")
    if schema_version != 1:
        errors.append(f"Unsupported schema_version: {schema_version} (expected 1)")

    target_type = raw.get("target_type", "")
    if not target_type:
        errors.append("Missing target_type.")

    description = raw.get("description", "")

    raw_stages = raw.get("stages", [])
    if not isinstance(raw_stages, list) or not raw_stages:
        return None, errors + ["stages must be a non-empty list."]

    stages: list[StageDefinition] = []
    for i, rs in enumerate(raw_stages):
        if not isinstance(rs, dict):
            errors.append(f"Stage {i} must be a mapping.")
            continue
        name = rs.get("name", "")
        if not name:
            errors.append(f"Stage {i} has no name.")
            continue

        closure_pred = rs.get("closure_predicate")
        if closure_pred:
            pred_errors = validate_predicate_schema(closure_pred)
            for pe in pred_errors:
                errors.append(f"Stage '{name}' closure_predicate: {pe}")

        dispatch = rs.get("dispatch", "agent")
        if dispatch not in REGISTERED_ADAPTERS:
            errors.append(
                f"Stage '{name}' dispatch '{dispatch}' not in registered adapters: "
                f"{sorted(REGISTERED_ADAPTERS)}"
            )

        stages.append(
            StageDefinition(
                name=name,
                description=rs.get("description", ""),
                is_gate=rs.get("is_gate", False),
                gate_description=rs.get("gate_description", ""),
                dispatch=dispatch,
                idempotent=rs.get("idempotent", True),
                closure_predicate=closure_pred,
                strict_gate_mode=rs.get("strict_gate_mode", False),
            )
        )

    entry_stage = raw.get("entry_stage", stages[0].name if stages else "")
    terminal_stages = raw.get("terminal_stages", [])
    if not terminal_stages:
        errors.append("No terminal_stages declared.")

    config = GoalConfig(
        target_type=target_type,
        schema_version=schema_version or 0,
        stages=stages,
        entry_stage=entry_stage,
        terminal_stages=terminal_stages,
        description=description,
    )

    graph_errors = validate_stage_graph(config)
    errors.extend(graph_errors)

    if errors:
        return config, errors
    return config, []


def load_goal_config(target_type: str) -> tuple[GoalConfig | None, list[str]]:
    """Load a goal-type config by target_type name from the goal_types directory."""
    config_path = GOAL_TYPES_DIR / f"{target_type}.yaml"
    return parse_goal_config(config_path)


def list_available_goal_types() -> list[str]:
    """List all YAML config files in the goal_types directory."""
    if not GOAL_TYPES_DIR.exists():
        return []
    return sorted(p.stem for p in GOAL_TYPES_DIR.glob("*.yaml"))
