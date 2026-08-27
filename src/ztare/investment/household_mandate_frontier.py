"""Decision closure over explicitly declared household-planning completions."""

from __future__ import annotations

from itertools import product
import math
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.information_yield_pricing import (
    identification_bits,
    partition_by_prediction,
    posterior_predictive_task_information_bits,
)

from .contracts import require_finite
from .household_allocation_scenario import (
    HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA,
    compile_household_allocation_scenario,
)


HOUSEHOLD_MANDATE_FRONTIER_SCHEMA = "jaggedthoughts-household-mandate-frontier-v1"

_FIELD_SPECS = {
    "annual_contribution": {
        "blockers": {"annual_after_tax_savings_capacity", "goal.annual_contribution"},
        "question": "What annual after-tax contribution should the plan assume?",
    },
    "horizon_years": {
        "blockers": {"goal_horizon", "goal.horizon_years"},
        "question": "Which investment horizon should govern the portfolio target?",
    },
}


def _values(values: Sequence[Any], *, field: str, base: Any) -> list[int | float]:
    rows: list[int | float] = []
    for raw in (*values, base):
        if isinstance(raw, bool):
            raise ValueError(f"{field} domain cannot contain booleans")
        value = require_finite(raw, f"{field} domain value")
        if field == "horizon_years":
            if int(value) != value or not 1 <= int(value) <= 100:
                raise ValueError("horizon_years domain requires integers in [1, 100]")
            value = int(value)
        if value not in rows:
            rows.append(value)
    return sorted(rows)


def declared_household_mandate_domains(
    goal_surface: Mapping[str, Any], base_inputs: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Use only ranges already declared by the private goal-surface design."""
    missing = set(map(str, (goal_surface.get("readiness") or {}).get("missing") or ()))
    matrix = [dict(row) for row in goal_surface.get("hurdle_matrix") or ()]
    raw_values = {
        "annual_contribution": [row.get("annual_contribution_base") for row in matrix],
        "horizon_years": [row.get("horizon_years") for row in matrix],
    }
    domains: dict[str, dict[str, Any]] = {}
    for field, spec in _FIELD_SPECS.items():
        matched = sorted(missing & spec["blockers"])
        if not matched:
            continue
        values = _values(raw_values[field], field=field, base=base_inputs[field])
        if len(values) < 2:
            continue
        domains[field] = {
            "values": values,
            "question": spec["question"],
            "source": "goal_surface.hurdle_matrix",
            "source_blocker_ids": matched,
            "operator_confirmed": False,
        }
    return domains


def _decision_weights(scenario: Mapping[str, Any]) -> dict[str, float]:
    weights = dict((scenario.get("selected_policy") or {}).get("weights") or {})
    if not weights:
        raise ValueError("mandate completion produced no selected policy")
    return {str(key): require_finite(value, f"selected weight {key}") for key, value in sorted(weights.items())}


def _decision_question(
    *, input_id: str, spec: Mapping[str, Any], worlds: list[dict[str, Any]],
    baseline_entropy: float,
) -> dict[str, Any]:
    answer_cells = partition_by_prediction(
        worlds, lambda world: world["completion"][input_id],
    )
    answers = []
    for answer, members in sorted(answer_cells.items(), key=lambda row: row[0]):
        decision_cells = partition_by_prediction(
            members, lambda world: world["decision_id"],
        )
        answers.append({
            "answer": answer,
            "design_world_count": len(members),
            "remaining_decision_ids": sorted(decision_cells),
            "remaining_decision_count": len(decision_cells),
        })
    information = posterior_predictive_task_information_bits(
        [{world["completion"][input_id]: 1.0} for world in worlds],
        [{world["decision_id"]: 1.0} for world in worlds],
    )
    body = {
        "input_id": input_id,
        "question": str(spec.get("question") or input_id),
        "source": str(spec.get("source") or "caller_declared_domain"),
        "source_blocker_ids": sorted(map(str, spec.get("source_blocker_ids") or ())),
        "answer_cells": answers,
        "decision_information_bits": round(information, 8),
        "fraction_of_current_decision_ambiguity": round(
            information / baseline_entropy if baseline_entropy > 0 else 0.0, 8,
        ),
        "worst_case_remaining_decision_count": max(
            row["remaining_decision_count"] for row in answers
        ),
        "decision_pivotal": information > 1e-12,
        "probability_interpretation": False,
    }
    return {**body, "question_sha256": stable_sha256(body)}


def compile_household_mandate_frontier(
    *, base_inputs: Mapping[str, Any], goal_surface: Mapping[str, Any],
    public_basis_acquisition: Mapping[str, Any],
    input_domains: Mapping[str, Mapping[str, Any]] | None = None,
    simulation_paths: int = 128, max_worlds: int = 64,
) -> dict[str, Any]:
    """Enumerate declared completions and ask only questions that split decisions."""
    base = dict(base_inputs)
    if base.get("schema") != HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA:
        raise ValueError(
            f"base inputs must use {HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA}"
        )
    domains = dict(input_domains or declared_household_mandate_domains(goal_surface, base))
    unknown = sorted(set(domains) - set(_FIELD_SPECS))
    if unknown:
        raise ValueError(f"unsupported mandate completion inputs: {', '.join(unknown)}")
    normalized: dict[str, dict[str, Any]] = {}
    for field, raw in sorted(domains.items()):
        spec = dict(raw)
        normalized[field] = {
            **spec,
            "values": _values(spec.get("values") or (), field=field, base=base[field]),
        }
    world_count = math.prod(len(spec["values"]) for spec in normalized.values())
    if world_count > max_worlds:
        raise ValueError(f"mandate completion world count {world_count} exceeds {max_worlds}")

    domain_identity = {
        field: {key: value for key, value in spec.items() if key != "operator_confirmed"}
        for field, spec in normalized.items()
    }
    common_seed = stable_sha256({
        "goal_surface_sha256": goal_surface.get("surface_sha256"),
        "basis_sha256": (public_basis_acquisition.get("capital_market_basis") or {}).get("basis_sha256"),
        "domains": domain_identity,
        "simulation_paths": simulation_paths,
    })
    fields = tuple(normalized)
    combinations = product(*(normalized[field]["values"] for field in fields)) if fields else [()]
    worlds: list[dict[str, Any]] = []
    for values in combinations:
        completion = dict(zip(fields, values, strict=True))
        inputs = {**base, **completion}
        scenario = compile_household_allocation_scenario(
            inputs,
            goal_surface=goal_surface,
            public_basis_acquisition=public_basis_acquisition,
            simulation_paths=simulation_paths,
            simulation_seed_identity=common_seed,
        )
        weights = _decision_weights(scenario)
        decision_id = stable_sha256({"selected_sleeve_weights": weights})
        world_body = {
            "completion": completion,
            "decision_id": decision_id,
            "selected_program_id": (scenario.get("selected_policy") or {}).get("program_id"),
            "selected_sleeve_weights": weights,
            "robust_goal_probability": (scenario.get("selected_policy") or {}).get(
                "robust_goal_probability"
            ),
            "required_constant_return": (scenario.get("goal") or {}).get(
                "required_constant_return"
            ),
        }
        worlds.append({**world_body, "world_id": stable_sha256(world_body)})

    decision_cells = partition_by_prediction(worlds, lambda world: world["decision_id"])
    baseline_entropy = identification_bits(decision_cells, len(worlds))
    base_completion = {field: base[field] for field in fields}
    base_world = next(world for world in worlds if world["completion"] == base_completion)
    decision_classes = []
    for decision_id, members in sorted(decision_cells.items()):
        decision_classes.append({
            "decision_id": decision_id,
            "selected_sleeve_weights": members[0]["selected_sleeve_weights"],
            "design_world_count": len(members),
            "world_ids": sorted(world["world_id"] for world in members),
            "contains_current_default": decision_id == base_world["decision_id"],
        })

    sleeve_ids = sorted(base_world["selected_sleeve_weights"])
    invariant_actions, weight_ranges = [], []
    for sleeve_id in sleeve_ids:
        values = [world["selected_sleeve_weights"][sleeve_id] for world in worlds]
        low, high = min(values), max(values)
        weight_ranges.append({"sleeve_id": sleeve_id, "minimum_weight": low, "maximum_weight": high})
        if low == high:
            invariant_actions.append({
                "action": "planning_weight_invariant",
                "sleeve_id": sleeve_id,
                "target_weight": low,
                "authority": "scenario_comparison_only",
            })

    questions = [
        _decision_question(
            input_id=field, spec=spec, worlds=worlds,
            baseline_entropy=baseline_entropy,
        )
        for field, spec in normalized.items() if len(spec["values"]) > 1
    ]
    questions.sort(key=lambda row: (
        not row["decision_pivotal"], -row["decision_information_bits"],
        row["worst_case_remaining_decision_count"], row["input_id"],
    ))
    next_question = questions[0] if questions and questions[0]["decision_pivotal"] else None
    priced_blockers = {
        blocker for spec in normalized.values()
        for blocker in spec.get("source_blocker_ids") or ()
    }
    all_blockers = set(map(
        str, (goal_surface.get("readiness") or {}).get("missing") or (),
    ))
    body = {
        "schema": HOUSEHOLD_MANDATE_FRONTIER_SCHEMA,
        "goal_surface_sha256": goal_surface.get("surface_sha256"),
        "basis_sha256": (public_basis_acquisition.get("capital_market_basis") or {}).get("basis_sha256"),
        "base_scenario_inputs_sha256": stable_sha256(base),
        "simulation_seed_sha256": stable_sha256(common_seed),
        "input_domains": normalized,
        "design_world_count": len(worlds),
        "decision_class_count": len(decision_classes),
        "decision_entropy_bits": round(baseline_entropy, 8),
        "decision_classes": decision_classes,
        "worlds": worlds,
        "current_default_world_id": base_world["world_id"],
        "current_default_decision_id": base_world["decision_id"],
        "invariant_actions": invariant_actions,
        "sleeve_weight_ranges": weight_ranges,
        "question_priority": questions,
        "highest_voi_unresolved_input": next_question,
        "unpriced_unresolved_inputs": sorted(all_blockers - priced_blockers),
        "status": (
            "decision_invariant_across_declared_completions"
            if len(decision_classes) == 1 else "decision_sensitive_ask_next_input"
        ),
        "information_method": {
            "method": "uniform_design_task_mutual_information",
            "primitive": (
                "ztare.common.information_yield_pricing."
                "posterior_predictive_task_information_bits"
            ),
            "probability_interpretation": False,
            "meaning": "Information over the declared finite completion design; not a posterior belief.",
        },
        "boundary": (
            "This frontier varies only declared planning inputs, closes exact sleeve-weight "
            "decisions, and ranks questions by decision disambiguation. It does not infer "
            "operator preferences, recommend a security, or grant policy, capital, brokerage, "
            "or order authority."
        ),
        "policy_authority": False,
        "capital_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
    }
    return {**body, "mandate_frontier_sha256": stable_sha256(body)}


__all__ = [
    "HOUSEHOLD_MANDATE_FRONTIER_SCHEMA",
    "compile_household_mandate_frontier",
    "declared_household_mandate_domains",
]
