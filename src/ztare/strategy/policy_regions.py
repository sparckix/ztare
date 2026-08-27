"""Exact state regions for a recursive contingent policy."""

from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Any, Iterable

from ztare.common.equivariance import stable_sha256

from .jaggedthoughts import Program
from .policies import PolicyCondition
from .transitions import StrategicActorState, StrategicState


SCHEMA = "jaggedthoughts-policy-action-regions-v1"
_INVERSE = {"eq": "ne", "ne": "eq", "gt": "le", "ge": "lt", "lt": "ge", "le": "gt"}


def _render_rational(value: Any) -> str:
    fraction = Fraction(value.numerator_as_long(), value.denominator_as_long())
    return str(fraction.numerator) if fraction.denominator == 1 else f"{fraction.numerator}/{fraction.denominator}"


def _condition_expression(z3: Any, variable: Any, condition: PolicyCondition, truth: bool) -> Any:
    operator = condition.operator if truth else _INVERSE[condition.operator]
    right = z3.RealVal(str(condition.value))
    return {
        "eq": variable == right,
        "ne": variable != right,
        "gt": variable > right,
        "ge": variable >= right,
        "lt": variable < right,
        "le": variable <= right,
    }[operator]


def _state_with_values(initial: StrategicState, values: dict[str, float]) -> StrategicState:
    firm = dict(initial.firm)
    actors = {row.actor_id: dict(row.variables) for row in initial.actors}
    for path, value in values.items():
        parts = path.split(".")
        if len(parts) == 2 and parts[0] == "firm" and parts[1] in firm:
            firm[parts[1]] = value
        elif len(parts) == 3 and parts[0] == "actor" and parts[1] in actors and parts[2] in actors[parts[1]]:
            actors[parts[1]][parts[2]] = value
        else:
            raise ValueError(f"policy condition path is absent from the initial state: {path}")
    return StrategicState(
        decision_id=initial.decision_id,
        epoch=initial.epoch,
        firm=tuple(firm.items()),
        actors=tuple(StrategicActorState.from_mapping(actor_id, rows) for actor_id, rows in actors.items()),
        context=initial.context,
    )


def compile_condition_partition_states(
    *,
    initial_state: StrategicState,
    conditions: Iterable[PolicyCondition],
    max_assignments: int = 4096,
) -> tuple[tuple[StrategicState, ...], dict[str, Any]]:
    """Generate one exact representative state for every feasible condition cell."""
    import z3

    rows = tuple(sorted(conditions, key=lambda row: row.condition_id))
    if not rows:
        raise ValueError("condition partition requires conditions")
    assignment_count = 1 << len(rows)
    if assignment_count > max_assignments:
        raise ValueError(f"condition assignment count {assignment_count} exceeds {max_assignments}")
    paths = tuple(sorted({row.path for row in rows}))
    variables = {path: z3.Real(f"condition_state_{index}") for index, path in enumerate(paths)}
    representatives: dict[str, StrategicState] = {initial_state.state_sha256: initial_state}
    cells: list[dict[str, Any]] = []
    infeasible: list[dict[str, Any]] = []
    for truths in product((False, True), repeat=len(rows)):
        solver = z3.Solver()
        solver.set(unsat_core=True)
        labels: dict[str, str] = {}
        for index, (condition, truth) in enumerate(zip(rows, truths, strict=True)):
            label_name = f"condition_assignment_{index}"
            solver.assert_and_track(
                _condition_expression(z3, variables[condition.path], condition, truth),
                z3.Bool(label_name),
            )
            labels[label_name] = condition.condition_id
        verdict = solver.check()
        truth_map = {row.condition_id: truth for row, truth in zip(rows, truths, strict=True)}
        if verdict == z3.unknown:
            raise RuntimeError(f"Z3 could not decide condition partition: {solver.reason_unknown()}")
        if verdict == z3.unsat:
            infeasible.append({
                "condition_truth": truth_map,
                "unsat_core_condition_ids": sorted({
                    labels[str(label)] for label in solver.unsat_core() if str(label) in labels
                }),
            })
            continue
        model = solver.model()
        rendered = {
            path: _render_rational(model.eval(variable, model_completion=True))
            for path, variable in variables.items()
        }
        state = _state_with_values(initial_state, {path: float(Fraction(value)) for path, value in rendered.items()})
        representatives[state.state_sha256] = state
        cells.append({
            "condition_truth": truth_map,
            "state_values": rendered,
            "representative_state_sha256": state.state_sha256,
        })
    evaluation_states = tuple(sorted(representatives.values(), key=lambda row: row.state_sha256))
    body = {
        "schema": "jaggedthoughts-policy-condition-partition-v1",
        "solver": {"name": "z3", "version": z3.get_version_string(), "logic": "QF_LRA"},
        "initial_state_sha256": initial_state.state_sha256,
        "condition_ids": [row.condition_id for row in rows],
        "state_paths": list(paths),
        "assignment_count": assignment_count,
        "feasible_cell_count": len(cells),
        "evaluation_state_count": len(evaluation_states),
        "cells": cells,
        "infeasible_assignments": infeasible,
        "scope_closed": True,
    }
    return evaluation_states, {**body, "condition_partition_sha256": stable_sha256(body)}


def compile_policy_action_regions(
    *,
    program: Program,
    conditions: Iterable[PolicyCondition],
    current_state: StrategicState | None = None,
) -> dict[str, Any]:
    """Partition symbolic state coordinates by the action a policy returns."""
    import z3

    condition_rows = tuple(sorted(conditions, key=lambda row: row.condition_id))
    condition_by_id = {row.condition_id: row for row in condition_rows}
    if len(condition_by_id) != len(condition_rows):
        raise ValueError("policy condition identities must be unique")
    paths: list[tuple[str, tuple[tuple[str, bool], ...]]] = []

    def visit(node: Program, path: tuple[tuple[str, bool], ...]) -> None:
        if node.terminal_id is not None:
            if not node.terminal_id.startswith("act::"):
                raise ValueError("policy region leaf must be an action terminal")
            paths.append((node.terminal_id.removeprefix("act::"), path))
            return
        if node.operator_id != "branch" or len(node.children) != 3:
            raise ValueError("policy regions support recursive branch programs only")
        condition_terminal = node.children[0].terminal_id or ""
        if not condition_terminal.startswith("when::"):
            raise ValueError("policy branch must begin with a condition terminal")
        condition_id = condition_terminal.removeprefix("when::")
        if condition_id not in condition_by_id:
            raise ValueError(f"policy branch references unknown condition: {condition_id}")
        visit(node.children[1], (*path, (condition_id, True)))
        visit(node.children[2], (*path, (condition_id, False)))

    visit(program, ())
    used_condition_ids = tuple(sorted({condition_id for _action, path in paths for condition_id, _truth in path}))
    state_paths = tuple(sorted({condition_by_id[condition_id].path for condition_id in used_condition_ids}))
    variables = {path: z3.Real(f"policy_state_{index}") for index, path in enumerate(state_paths)}

    def expression(condition_id: str, truth: bool) -> Any:
        condition = condition_by_id[condition_id]
        return _condition_expression(z3, variables[condition.path], condition, truth)

    compiled: list[tuple[dict[str, Any], Any]] = []
    unreachable: list[dict[str, Any]] = []
    for path_index, (action_id, path) in enumerate(paths):
        constraints = [expression(condition_id, truth) for condition_id, truth in path]
        formula = z3.And(*constraints) if constraints else z3.BoolVal(True)
        solver = z3.Solver()
        solver.set(unsat_core=True)
        labels: dict[str, str] = {}
        for step, ((condition_id, _truth), constraint) in enumerate(zip(path, constraints, strict=True)):
            label_name = f"policy_path_{path_index}_condition_{step}"
            solver.assert_and_track(constraint, z3.Bool(label_name))
            labels[label_name] = condition_id
        verdict = solver.check()
        if verdict == z3.unknown:
            raise RuntimeError(f"Z3 could not decide policy action region: {solver.reason_unknown()}")
        rendered_conditions = [
            {
                "condition_id": condition_id,
                "path": condition_by_id[condition_id].path,
                "operator": condition_by_id[condition_id].operator if truth else _INVERSE[condition_by_id[condition_id].operator],
                "value": condition_by_id[condition_id].value,
                "branch": "true" if truth else "false",
            }
            for condition_id, truth in path
        ]
        if verdict == z3.unsat:
            unreachable.append({
                "action_id": action_id,
                "conditions": rendered_conditions,
                "unsat_core_condition_ids": sorted({
                    labels[str(label)] for label in solver.unsat_core() if str(label) in labels
                }),
            })
            continue
        model = solver.model()
        witness = {
            path_name: _render_rational(model.eval(variable, model_completion=True))
            for path_name, variable in variables.items()
        }
        row = {"action_id": action_id, "conditions": rendered_conditions, "state_witness": witness}
        row["region_sha256"] = stable_sha256(row)
        compiled.append((row, formula))

    coverage = z3.Solver()
    coverage.add(z3.Not(z3.Or(*[formula for _row, formula in compiled])))
    coverage_verdict = coverage.check()
    if coverage_verdict == z3.unknown:
        raise RuntimeError(f"Z3 could not decide policy coverage: {coverage.reason_unknown()}")
    overlaps: list[dict[str, Any]] = []
    for left_index, (left, left_formula) in enumerate(compiled):
        for right, right_formula in compiled[left_index + 1:]:
            if left["action_id"] == right["action_id"]:
                continue
            overlap = z3.Solver()
            overlap.add(left_formula, right_formula)
            verdict = overlap.check()
            if verdict == z3.unknown:
                raise RuntimeError(f"Z3 could not decide policy overlap: {overlap.reason_unknown()}")
            if verdict == z3.sat:
                model = overlap.model()
                overlaps.append({
                    "action_ids": sorted((left["action_id"], right["action_id"])),
                    "state_witness": {
                        path_name: _render_rational(model.eval(variable, model_completion=True))
                        for path_name, variable in variables.items()
                    },
                })

    current_action_ids: list[str] = []
    if current_state is not None:
        for row, _formula in compiled:
            if all(
                condition_by_id[condition["condition_id"]].matches(current_state)
                == (condition["branch"] == "true")
                for condition in row["conditions"]
            ):
                current_action_ids.append(str(row["action_id"]))
    body = {
        "schema": SCHEMA,
        "program_id": program.program_id,
        "solver": {"name": "z3", "version": z3.get_version_string(), "logic": "QF_LRA"},
        "state_paths": list(state_paths),
        "conditions": [condition_by_id[condition_id].to_dict() for condition_id in used_condition_ids],
        "regions": [row for row, _formula in compiled],
        "unreachable_regions": unreachable,
        "reachable_action_ids": sorted({row["action_id"] for row, _formula in compiled}),
        "total_over_condition_space": coverage_verdict == z3.unsat,
        "deterministic_over_condition_space": not overlaps,
        "overlap_counterexamples": overlaps,
        "current_state_action_ids": sorted(set(current_action_ids)),
        "state_domain": "mathematical_reals_constrained_only_by_policy_conditions",
        "scope_closed": True,
        "use_boundary": (
            "This certificate proves the selected program's branching behavior over its declared condition "
            "coordinates. It does not prove that the thresholds, policy, or resulting action are profitable."
        ),
    }
    return {**body, "policy_action_regions_sha256": stable_sha256(body)}


__all__ = ["SCHEMA", "compile_condition_partition_states", "compile_policy_action_regions"]
