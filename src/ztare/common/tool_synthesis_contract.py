from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.common.operator_proposal_contract import family_sha


TOOL_SYNTHESIS_KIND = "tool_synthesis"
TOOL_SYNTHESIS_SCHEMA = "strategy-experiment-v1"

_HARD_KERNEL_PATTERNS = (
    "gate_harness.py",
    "src/ztare/common/control_work_items.py",
    "src/ztare/common/strategy_card_roles.py",
    "src/ztare/validator/core/pre_judge_gate.py",
    "src/ztare/validator/core/strategy_card_gate.py",
    "src/ztare/worldmodel/gates.py",
    "src/ztare/common/operator_proposal_contract.py",
    "rubrics/",
)

_MUTABLE_SURFACE_PATTERNS = (
    "src/ztare/common/ask_spec.py",
    "src/ztare/common/briefing_pack.py",
    "src/ztare/common/leaf_workbench",
    "src/ztare/common/leaf_workbench_executor.py",
    "src/ztare/common/visible_workbench_actions.py",
    "src/ztare/common/visible_workbench_cli.py",
    "src/ztare/common/harness_weakness.py",
    "src/ztare/common/dispatch_model.py",
    "src/ztare/common/subscription_agent_runtime.py",
    "src/ztare/orchestrator/retry_contract.py",
    "src/ztare/orchestrator/submission_path_helpers.py",
    "src/ztare/validator/worldmodel_typed_payload.py",
    "src/ztare/worldmodel/leaf_workbench.py",
    "src/ztare/worldmodel/retry_surface.py",
    "src/ztare/orchestrator/briefing_providers/",
    "src/ztare/common/abstraction_functor.py",
    "src/ztare/validator/core/repair_preflight.py",
    "src/ztare/worldmodel/object_roles.py",
)


def classify_tool_target(path: str | Path) -> str:
    ref = str(path).strip().replace("\\", "/")
    if not ref or ref.startswith("/") or ".." in Path(ref).parts:
        return "invalid"
    if any(pattern in ref for pattern in _HARD_KERNEL_PATTERNS):
        return "immutable_axiom"
    if any(pattern in ref for pattern in _MUTABLE_SURFACE_PATTERNS):
        return "mutable_sensor"
    return "unclassified"


def validate_tool_synthesis_card(card: Any) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    if not isinstance(card, dict):
        return {
            "schema": "tool-synthesis-card-validation-v1",
            "status": "fail",
            "failures": [{"failure": "missing_card"}],
        }
    if card.get("kind") != TOOL_SYNTHESIS_KIND:
        failures.append({"failure": "wrong_kind"})
    plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
    target = str(plan.get("target_artifact") or "")
    mutable_surface = str(plan.get("mutable_surface") or classify_tool_target(target))
    if not target:
        failures.append({"failure": "missing_target_artifact"})
    if mutable_surface != "mutable_sensor":
        failures.append({"failure": f"target_not_mutable_sensor:{mutable_surface}"})
    for key in ("capability_contract", "evaluator", "rollback_condition", "required_next_gate"):
        if plan.get(key) in (None, "", [], {}):
            failures.append({"failure": f"missing_{key}"})
    return {
        "schema": "tool-synthesis-card-validation-v1",
        "status": "pass" if not failures else "fail",
        "failures": failures,
    }


def tool_synthesis_card(
    *,
    proposed_capability_id: str,
    gap_statement: str,
    target_artifact: str,
    capability_contract: dict[str, Any],
    evaluator: str,
    rollback_condition: str,
    source_ref: str,
) -> dict[str, Any]:
    surface = classify_tool_target(target_artifact)
    plan = {
        "target_artifact": str(target_artifact),
        "mutable_surface": surface,
        "capability_contract": dict(capability_contract),
        "evaluator": str(evaluator),
        "rollback_condition": str(rollback_condition),
        "source_ref": str(source_ref),
        "required_next_gate": {
            "command": "tool_synthesis_gate",
            "success_status": "compiled_tool_receipt_plus_regression_pass",
            "adoption_authority": (
                "tool cards may modify mutable sensors only; deterministic gates "
                "and hard-kernel files remain outside this mutation surface"
            ),
        },
    }
    family = "tool_synthesis|" + json.dumps(
        {
            "proposed_capability_id": proposed_capability_id,
            "target_artifact": target_artifact,
            "capability_contract": capability_contract,
        },
        sort_keys=True,
        default=str,
    )
    card = {
        "schema": TOOL_SYNTHESIS_SCHEMA,
        "kind": TOOL_SYNTHESIS_KIND,
        "failure_family": family,
        "failure_family_sha": family_sha(family),
        "rationale": str(gap_statement),
        "falsifiable_prediction": (
            f"implement {proposed_capability_id} as a mutable workbench tool; "
            "it must compile, emit deterministic receipts, and pass its evaluator"
        ),
        "action_plan": plan,
        "kill_condition": str(rollback_condition),
        "disposition": "open",
    }
    validation = validate_tool_synthesis_card(card)
    if validation["status"] != "pass":
        raise ValueError(f"invalid tool_synthesis card: {validation['failures']}")
    return card
