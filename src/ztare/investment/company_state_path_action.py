"""Prospective two-quarter path-action forecasts on a frozen company-state frontier."""

from __future__ import annotations

from argparse import ArgumentParser
from itertools import product
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256

from .company_state_flow import decompose_transition_counts
from .company_state_partition_frontier import _next_quarter
from .company_state_partition_settlement import _validated_contract
from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key


COMPANY_STATE_PATH_ACTION_PROFILE_SCHEMA = "jaggedthoughts-company-state-path-action-profile-v1"
COMPANY_STATE_PATH_ACTION_RUN_SCHEMA = "jaggedthoughts-company-state-path-action-run-v1"
COMPANY_STATE_PATH_OUTCOME_CONTRACT_SCHEMA = "jaggedthoughts-company-state-path-outcome-contract-v1"

_VALUE = {"expensive": -0.5, "middle": 0.0, "cheap": 0.5}
_DURABILITY = {"low": -1.0, "middle": 0.0, "high": 1.0}


def _coordinates(state_id: str) -> tuple[float, float]:
    parts = dict(part.split("_", 1) for part in state_id.split("__"))
    try:
        return _VALUE[parts["valuation"]], _DURABILITY[parts["durability"]]
    except KeyError as error:
        raise ValueError(f"unsupported company-state identity: {state_id}") from error


def _squared(left: tuple[float, float], right: tuple[float, float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))


def _orientation(left: tuple[float, float], right: tuple[float, float]) -> float:
    return left[0] * right[1] - left[1] * right[0]


def _path_action(
    source: tuple[float, float],
    intermediate: tuple[float, float],
    terminal: tuple[float, float],
    *,
    step_cost: float,
    curvature_cost: float,
    circulation_strength: float,
) -> tuple[float, float]:
    symmetric = step_cost * (
        _squared(source, intermediate) + _squared(intermediate, terminal)
    ) + curvature_cost * sum(
        (terminal[index] - 2.0 * intermediate[index] + source[index]) ** 2
        for index in range(2)
    )
    current = -circulation_strength * (
        _orientation(source, intermediate) + _orientation(intermediate, terminal)
    )
    return symmetric + current, current


def _softmax_actions(rows: list[dict[str, Any]]) -> None:
    floor = min(float(row["mathematical_action"]) for row in rows)
    weights = [math.exp(-(float(row["mathematical_action"]) - floor)) for row in rows]
    total = math.fsum(weights)
    probabilities = [weight / total for weight in weights]
    probabilities[-1] += 1.0 - math.fsum(probabilities)
    for row, probability in zip(rows, probabilities, strict=True):
        row["probability"] = probability


def compile_path_distributions(
    state_ids: Sequence[str], *,
    step_cost: float,
    curvature_cost: float,
    circulation_strength: float,
    empirical_transition_counts: Sequence[Sequence[int | float]] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Enumerate all bounded two-step paths for one challenger and its controls."""
    states = tuple(require_text(state_id, "company state_id") for state_id in state_ids)
    if len(states) < 2 or len(states) != len(set(states)):
        raise ValueError("company states must be unique and contain at least two states")
    coordinates = {state_id: _coordinates(state_id) for state_id in states}
    specs = (
        ("path_action_current", "challenger", step_cost, curvature_cost, circulation_strength),
        ("reversible_action_ablation", "required_control", step_cost, curvature_cost, 0.0),
        ("distance_markov_control", "required_control", step_cost, 0.0, 0.0),
        ("uniform_path_control", "required_control", 0.0, 0.0, 0.0),
    )
    models = []
    for model_id, role, step, curvature, circulation in specs:
        conditionals = []
        for source_id in states:
            rows = []
            for intermediate_id, terminal_id in product(states, repeat=2):
                action, current = _path_action(
                    coordinates[source_id], coordinates[intermediate_id],
                    coordinates[terminal_id], step_cost=step,
                    curvature_cost=curvature, circulation_strength=circulation,
                )
                rows.append({
                    "intermediate_state_id": intermediate_id,
                    "terminal_state_id": terminal_id,
                    "mathematical_action": action,
                    "current_component": current,
                })
            _softmax_actions(rows)
            conditionals.append({"source_state_id": source_id, "paths": rows})
        models.append({
            "model_id": model_id,
            "role": role,
            "parameters": {
                "step_cost": step,
                "curvature_cost": curvature,
                "circulation_strength": circulation,
            },
            "conditional_path_distributions": conditionals,
            "signal_authority": False,
            "capital_authority": False,
        })

    persistence = []
    for source_id in states:
        paths = [{
            "intermediate_state_id": intermediate_id,
            "terminal_state_id": terminal_id,
            "mathematical_action": 0.0 if intermediate_id == terminal_id == source_id else None,
            "current_component": 0.0,
            "probability": 1.0 if intermediate_id == terminal_id == source_id else 0.0,
        } for intermediate_id, terminal_id in product(states, repeat=2)]
        persistence.append({"source_state_id": source_id, "paths": paths})
    models.append({
        "model_id": "persistence_path_control",
        "role": "required_control",
        "parameters": {},
        "conditional_path_distributions": persistence,
        "signal_authority": False,
        "capital_authority": False,
    })
    if empirical_transition_counts is not None:
        counts = [list(row) for row in empirical_transition_counts]
        if not counts:
            raise ValueError("empirical path control requires transition counts")
        transition = decompose_transition_counts(counts, pseudocount=1.0)[
            "directed_transition"
        ]
        empirical = []
        for source_index, source_id in enumerate(states):
            paths = [{
                "intermediate_state_id": intermediate_id,
                "terminal_state_id": terminal_id,
                "mathematical_action": None,
                "current_component": 0.0,
                "probability": (
                    transition[source_index][intermediate_index]
                    * transition[intermediate_index][terminal_index]
                ),
            } for intermediate_index, intermediate_id in enumerate(states)
              for terminal_index, terminal_id in enumerate(states)]
            paths[-1]["probability"] += 1.0 - math.fsum(
                float(row["probability"]) for row in paths
            )
            empirical.append({"source_state_id": source_id, "paths": paths})
        models.append({
            "model_id": "empirical_markov_path_control",
            "role": "required_control",
            "parameters": {
                "pseudocount": 1.0,
                "transition_counts_sha256": stable_sha256(counts),
            },
            "conditional_path_distributions": empirical,
            "signal_authority": False,
            "capital_authority": False,
        })
    return tuple(models)


def _validate_distributions(
    models: Sequence[Mapping[str, Any]], state_ids: Sequence[str],
) -> dict[str, Any]:
    expected = len(state_ids) ** 2
    maximum_residual = 0.0
    for model in models:
        conditionals = list(model["conditional_path_distributions"])
        if {row["source_state_id"] for row in conditionals} != set(state_ids):
            raise ValueError("path model source-state coverage mismatch")
        for conditional in conditionals:
            paths = list(conditional["paths"])
            identities = {
                (row["intermediate_state_id"], row["terminal_state_id"]) for row in paths
            }
            if len(paths) != expected or len(identities) != expected:
                raise ValueError("path enumeration is incomplete or duplicated")
            probabilities = [float(row["probability"]) for row in paths]
            if any(not math.isfinite(value) or value < 0.0 for value in probabilities):
                raise ValueError("path probabilities must be finite and nonnegative")
            residual = abs(math.fsum(probabilities) - 1.0)
            maximum_residual = max(maximum_residual, residual)
            if residual > 1e-12:
                raise ValueError("path probabilities do not normalize")

    by_id = {str(model["model_id"]): model for model in models}
    challenger = by_id["path_action_current"]["conditional_path_distributions"]
    ablation = by_id["reversible_action_ablation"]["conditional_path_distributions"]
    l1_by_source = []
    for candidate_row, control_row in zip(challenger, ablation, strict=True):
        l1_by_source.append(math.fsum(
            abs(float(left["probability"]) - float(right["probability"]))
            for left, right in zip(candidate_row["paths"], control_row["paths"], strict=True)
        ))
    if max(l1_by_source) <= 1e-12:
        raise ValueError("path-action challenger is indistinguishable from its current ablation")
    return {
        "path_count_per_source_state": expected,
        "total_structural_path_count": len(state_ids) * expected,
        "maximum_normalization_residual": maximum_residual,
        "minimum_current_ablation_l1": min(l1_by_source),
        "maximum_current_ablation_l1": max(l1_by_source),
    }


def _contract(body: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(body)
    payload["contract_sha256"] = stable_sha256(payload)
    return payload


def compile_company_state_path_action(
    profile_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Open intermediate and terminal shadow contracts before either outcome exists."""
    root = Path(workspace).expanduser().resolve()
    source = Path(profile_path).expanduser()
    if not source.is_absolute():
        source = root / source
    profile = yaml.safe_load(source.resolve().read_text(encoding="utf-8"))
    if not isinstance(profile, Mapping) or profile.get("schema") != COMPANY_STATE_PATH_ACTION_PROFILE_SCHEMA:
        raise ValueError(f"path-action profile schema must be {COMPANY_STATE_PATH_ACTION_PROFILE_SCHEMA}")
    if int(profile.get("horizon_quarters", 0)) != 2:
        raise ValueError("company-state path action requires exactly two quarters")
    if profile.get("scoring_rule") != "multiclass_brier":
        raise ValueError("company-state path action requires the frozen multiclass Brier rule")

    frontier_path = root / require_text(profile.get("frontier_path"), "frontier_path")
    frontier = json.loads(frontier_path.resolve().read_text(encoding="utf-8"))
    activation, intermediate_identity, candidate, snapshot = _validated_contract(frontier)
    opened_at = canonical_timestamp(profile.get("opened_at"), "path-action opened_at")
    frontier_as_of = canonical_timestamp(frontier.get("as_of"), "partition frontier as_of")
    intermediate_due = canonical_timestamp(
        intermediate_identity["settlement_not_before"], "intermediate settlement horizon",
    )
    terminal_epoch = _next_quarter(str(intermediate_identity["target_epoch"]))
    terminal_due = canonical_timestamp(f"{terminal_epoch}T23:59:59Z", "terminal settlement horizon")
    if not (
        timestamp_key(frontier_as_of) <= timestamp_key(opened_at)
        < timestamp_key(intermediate_due) < timestamp_key(terminal_due)
    ):
        raise ValueError("path-action contract chronology must be frontier <= open < intermediate < terminal")

    parameters = dict(profile.get("mathematical_action") or {})
    step_cost = require_finite(parameters.get("step_cost"), "mathematical_action.step_cost")
    curvature_cost = require_finite(
        parameters.get("curvature_cost"), "mathematical_action.curvature_cost",
    )
    circulation_strength = require_finite(
        parameters.get("circulation_strength"), "mathematical_action.circulation_strength",
    )
    if step_cost < 0.0 or curvature_cost < 0.0 or circulation_strength == 0.0:
        raise ValueError("path action requires nonnegative costs and a nonzero declared circulation")

    state_ids = tuple(str(value) for value in candidate["state_ids"])
    models = compile_path_distributions(
        state_ids, step_cost=step_cost, curvature_cost=curvature_cost,
        circulation_strength=circulation_strength,
        empirical_transition_counts=candidate.get("transition_counts"),
    )
    checks = _validate_distributions(models, state_ids)
    intermediate_contract = _contract({
        "schema": COMPANY_STATE_PATH_OUTCOME_CONTRACT_SCHEMA,
        "leg": "intermediate",
        "status": "prospective_shadow_open",
        "opened_at": opened_at,
        "evidence_id": intermediate_identity["evidence_id"],
        "frontier_evidence_sha256": stable_sha256(intermediate_identity),
        "frontier_evidence_identity": intermediate_identity,
        "source_epoch": intermediate_identity["source_epoch"],
        "target_epoch": intermediate_identity["target_epoch"],
        "settlement_not_before": intermediate_due,
        "required_output": "frozen-cohort intermediate state assignment",
        "signal_authority": False,
        "capital_authority": False,
    })
    terminal_identity = {
        "schema": COMPANY_STATE_PATH_OUTCOME_CONTRACT_SCHEMA,
        "leg": "terminal",
        "status": "prospective_shadow_open",
        "opened_at": opened_at,
        "source_epoch": intermediate_identity["source_epoch"],
        "intermediate_epoch": intermediate_identity["target_epoch"],
        "target_epoch": terminal_epoch,
        "settlement_not_before": terminal_due,
        "partition_sha256": intermediate_identity["partition_sha256"],
        "benchmark_id": intermediate_identity["benchmark_id"],
        "min_years": intermediate_identity["min_years"],
        "source_entity_count": intermediate_identity["source_entity_count"],
        "source_entity_ids_sha256": intermediate_identity["source_entity_ids_sha256"],
        "source_assignments_sha256": intermediate_identity["source_assignments_sha256"],
        "membership_rule": intermediate_identity["membership_rule"],
        "target_threshold_population": intermediate_identity["target_threshold_population"],
        "minimum_target_entity_count": intermediate_identity["minimum_target_entity_count"],
        "availability_rule": intermediate_identity["availability_rule"],
        "required_output": "frozen-cohort terminal state assignment and complete two-step paths",
        "signal_authority": False,
        "capital_authority": False,
    }
    terminal_identity["evidence_id"] = (
        f"company-state-path:{terminal_identity['source_epoch']}:{terminal_epoch}:"
        f"{stable_sha256(terminal_identity)[:16]}"
    )
    terminal_contract = _contract(terminal_identity)

    profile_identity = dict(profile)
    body: dict[str, Any] = {
        "schema": COMPANY_STATE_PATH_ACTION_RUN_SCHEMA,
        "experiment_id": require_text(profile.get("experiment_id"), "experiment_id"),
        "as_of": opened_at,
        "status": "prospective_shadow_open",
        "authority": "experiment_only",
        "opened_at": opened_at,
        "profile_sha256": stable_sha256(profile_identity),
        "partition_frontier_sha256": frontier["partition_frontier_sha256"],
        "activation_sha256": activation["activation_sha256"],
        "partition_sha256": activation["partition_sha256"],
        "source_snapshot": snapshot,
        "source_refs": sorted({
            str(source_ref)
            for assignment in snapshot.get("assignments") or ()
            for source_ref in assignment.get("source_refs") or ()
        }),
        "source_assignments_sha256": intermediate_identity["source_assignments_sha256"],
        "state_ids": list(state_ids),
        "mathematical_action": {
            "family": "two-step discrete Euclidean action with antisymmetric circulation",
            "formula": "step_cost*(|m-s|^2+|t-m|^2)+curvature_cost*|t-2m+s|^2-circulation_strength*(sxm+mxt)",
            "parameters": {
                "step_cost": step_cost,
                "curvature_cost": curvature_cost,
                "circulation_strength": circulation_strength,
            },
            "parameter_source": "declared_before both settlement horizons; not estimated from outcomes",
        },
        "required_control_ids": [
            str(model["model_id"]) for model in models
            if model["role"] == "required_control"
        ],
        "models": list(models),
        "structural_checks": checks,
        "outcome_contracts": [intermediate_contract, terminal_contract],
        "settlement_scoring": {
            "rule": "multiclass_brier_lower_is_better",
            "intermediate_unit": "marginal intermediate-state distribution per frozen entity",
            "terminal_unit": "joint intermediate-terminal path distribution per frozen entity",
            "aggregation": "equal-weight mean over entities admitted by the frozen coverage rule",
            "model_selection": "none; parameters and controls remain frozen",
        },
        "evaluation_status": "awaiting_both_prospective_outcomes",
        "promotion_rule": (
            "No use beyond research until both legs settle and the challenger beats every required "
            "control out of sample under the frozen Brier rule."
        ),
        "signal_authority": False,
        "model_fit_authority": False,
        "capital_authority": False,
        "use_boundary": (
            "This is a prospective path forecast and falsification contract. Mathematical action "
            "does not mean a portfolio action."
        ),
    }
    body["run_id"] = f"{body['experiment_id']}:{stable_sha256(body)[:20]}"
    return {**body, "run_sha256": stable_sha256(body)}


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = compile_company_state_path_action(args.profile, workspace=args.workspace)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPANY_STATE_PATH_ACTION_PROFILE_SCHEMA",
    "COMPANY_STATE_PATH_ACTION_RUN_SCHEMA",
    "COMPANY_STATE_PATH_OUTCOME_CONTRACT_SCHEMA",
    "compile_company_state_path_action",
    "compile_path_distributions",
]
