#!/usr/bin/env python3
"""Exact order-6 boundary query for the coprime-cycle campaign.

The query uses only the primary cycle-set operation.  On a finite carrier,
row bijectivity supplies the rowwise inverse operation and diagonal
bijectivity supplies the inverse diagonal operation from the campaign's
definitional expansion.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
from itertools import permutations
import json
from typing import Iterable

import z3


SCHEMA = "leanmill.cycle_set_coprime_size6_boundary.v1"
CARRIER_SIZE = 6


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _base_solver(name: str, *, timeout_ms: int) -> tuple[z3.Solver, z3.FuncDeclRef]:
    n = CARRIER_SIZE
    operation = z3.Function(name, z3.IntSort(), z3.IntSort(), z3.IntSort())
    solver = z3.Solver()
    solver.set(timeout=timeout_ms, random_seed=0)
    for x in range(n):
        for y in range(n):
            solver.add(operation(x, y) >= 0, operation(x, y) < n)
    for x in range(n):
        solver.add(z3.Distinct(*(operation(x, y) for y in range(n))))
    solver.add(z3.Distinct(*(operation(x, x) for x in range(n))))
    for x in range(n):
        for y in range(n):
            for z in range(n):
                solver.add(
                    operation(operation(x, y), operation(x, z))
                    == operation(operation(y, x), operation(y, z))
                )
    return solver, operation


def _transitivity_constraints(operation: z3.FuncDeclRef) -> list[z3.BoolRef]:
    """Exclude every nonempty proper subset invariant under all left rows."""

    n = CARRIER_SIZE
    constraints = []
    for mask in range(1, (1 << n) - 1):
        constraints.append(
            z3.Or(
                *(
                    operation(x, y) == z
                    for x in range(n)
                    for y in range(n)
                    for z in range(n)
                    if ((mask >> y) & 1) != ((mask >> z) & 1)
                )
            )
        )
    return constraints


def _five_cycle_constraint(operation: z3.FuncDeclRef) -> z3.BoolRef:
    """Require a 5-cycle in some row, the only nontrivial length coprime to 6."""

    n = CARRIER_SIZE
    cases = []
    for x in range(n):
        for fixed in range(n):
            moving = [value for value in range(n) if value != fixed]
            start = min(moving)
            for tail in permutations(value for value in moving if value != start):
                cycle = (start, *tail)
                cases.append(
                    z3.And(
                        operation(x, fixed) == fixed,
                        *(
                            operation(x, cycle[index])
                            == cycle[(index + 1) % len(cycle)]
                            for index in range(len(cycle))
                        ),
                    )
                )
    return z3.Or(*cases)


def _pin_table(
    solver: z3.Solver,
    operation: z3.FuncDeclRef,
    table: list[list[int]],
) -> None:
    for x, row in enumerate(table):
        for y, value in enumerate(row):
            solver.add(operation(x, y) == value)


def _cycles(permutation: list[int]) -> list[list[int]]:
    seen: set[int] = set()
    result = []
    for start in range(len(permutation)):
        if start in seen:
            continue
        cycle = []
        value = start
        while value not in seen:
            seen.add(value)
            cycle.append(value)
            value = permutation[value]
        result.append(cycle)
    return result


def _action_orbits(table: list[list[int]]) -> list[list[int]]:
    n = len(table)
    unseen = set(range(n))
    result = []
    while unseen:
        root = min(unseen)
        orbit = {root}
        queue = deque([root])
        while queue:
            value = queue.popleft()
            for row in table:
                neighbours = (row[value], row.index(value))
                for neighbour in neighbours:
                    if neighbour not in orbit:
                        orbit.add(neighbour)
                        queue.append(neighbour)
        result.append(sorted(orbit))
        unseen -= orbit
    return result


def _verify_table(table: list[list[int]]) -> dict[str, object]:
    n = len(table)
    row_bijective = all(sorted(row) == list(range(n)) for row in table)
    diagonal_bijective = sorted(table[x][x] for x in range(n)) == list(range(n))
    cycle_law = all(
        table[table[x][y]][table[x][z]] == table[table[y][x]][table[y][z]]
        for x in range(n)
        for y in range(n)
        for z in range(n)
    )
    row_cycle_types = [
        sorted((len(cycle) for cycle in _cycles(row)), reverse=True)
        for row in table
    ]
    return {
        "row_bijective": row_bijective,
        "diagonal_bijective": diagonal_bijective,
        "cycle_law": cycle_law,
        "action_orbits": _action_orbits(table),
        "row_cycle_types": row_cycle_types,
    }


def _status(value: z3.CheckSatResult) -> str:
    return str(value)


def run_boundary(*, timeout_ms: int) -> dict[str, object]:
    n = CARRIER_SIZE
    five_cycle = [1, 2, 3, 4, 0, 5]
    six_cycle = [1, 2, 3, 4, 5, 0]
    five_control_table = [list(five_cycle) for _ in range(n)]
    transitive_control_table = [list(six_cycle) for _ in range(n)]

    five_solver, five_operation = _base_solver(
        "five_cycle_control_operation", timeout_ms=timeout_ms
    )
    five_solver.add(_five_cycle_constraint(five_operation))
    _pin_table(five_solver, five_operation, five_control_table)
    five_status = five_solver.check()

    transitive_solver, transitive_operation = _base_solver(
        "transitive_control_operation", timeout_ms=timeout_ms
    )
    transitive_solver.add(*_transitivity_constraints(transitive_operation))
    _pin_table(transitive_solver, transitive_operation, transitive_control_table)
    transitive_status = transitive_solver.check()

    target_solver, target_operation = _base_solver(
        "target_operation", timeout_ms=timeout_ms
    )
    target_solver.add(*_transitivity_constraints(target_operation))
    target_solver.add(_five_cycle_constraint(target_operation))
    target_smt2_sha256 = hashlib.sha256(
        target_solver.sexpr().encode("utf-8")
    ).hexdigest()
    target_status = target_solver.check()

    five_verification = _verify_table(five_control_table)
    transitive_verification = _verify_table(transitive_control_table)
    if (
        five_status != z3.sat
        or transitive_status != z3.sat
        or five_verification["action_orbits"] != [[0, 1, 2, 3, 4], [5]]
        or transitive_verification["action_orbits"] != [[0, 1, 2, 3, 4, 5]]
        or [5, 1] not in five_verification["row_cycle_types"]
        or [5, 1] in transitive_verification["row_cycle_types"]
    ):
        raise RuntimeError("matched controls do not discriminate the target conjunction")

    core: dict[str, object] = {
        "schema": SCHEMA,
        "carrier_size": n,
        "solver": f"z3-{z3.get_version_string()}",
        "timeout_ms": timeout_ms,
        "base_theory": {
            "left_rows_bijective": True,
            "diagonal_bijective": True,
            "cycle_set_identity": "(x*y)*(x*z)=(y*x)*(y*z)",
        },
        "target_predicate": {
            "indecomposable_encoding": (
                "every nonempty proper carrier subset has a membership-crossing "
                "edge under some left translation"
            ),
            "coprime_cycle_lengths": [5],
            "five_cycle_encoding": "full row/fixed-point/cycle disjunction",
        },
        "matched_controls": {
            "five_cycle_without_transitivity": {
                "solver_status": _status(five_status),
                "table": five_control_table,
                "verification": five_verification,
            },
            "transitivity_without_five_cycle": {
                "solver_status": _status(transitive_status),
                "table": transitive_control_table,
                "verification": transitive_verification,
            },
        },
        "target_query": {
            "solver_status": _status(target_status),
            "reason_unknown": target_solver.reason_unknown(),
            "smt2_sha256": target_smt2_sha256,
        },
        "result": (
            "no_order_6_counterexample"
            if target_status == z3.unsat
            else "counterexample_candidate_or_unknown"
        ),
        "claim_boundary": (
            "exact only for order 6 under the displayed finite encoding; UNSAT "
            "does not imply the unrestricted Ramírez-Vendramin statement"
        ),
        "authority": "deterministic_campaign_local_boundary",
    }
    return {**core, "receipt_sha256": _canonical_hash(core)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-ms", type=int, default=900_000)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.timeout_ms < 1:
        parser.error("--timeout-ms must be positive")
    print(json.dumps(run_boundary(timeout_ms=args.timeout_ms), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
