#!/usr/bin/env python3
"""Exact order-7 coprime-cycle boundary with two transitivity encodings.

For a witnessed row and cycle, simultaneous relabeling has exactly two cases:
the row index belongs to the cycle or it does not.  The normalized cycle
predicate below enumerates both cases for every nontrivial proper cycle length.
At prime order seven, those are precisely the cycle lengths coprime to seven.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
from itertools import product
import json
import time
from typing import Iterable

import z3


SCHEMA = "leanmill.cycle_set_coprime_size7_boundary.v1"
CARRIER_SIZE = 7


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _base_solver(name: str, *, timeout_ms: int) -> tuple[z3.Solver, z3.FuncDeclRef]:
    n = CARRIER_SIZE
    operation = z3.Function(name, z3.IntSort(), z3.IntSort(), z3.IntSort())
    solver = z3.Solver()
    solver.set(timeout=timeout_ms, random_seed=0)
    for x, y in product(range(n), repeat=2):
        solver.add(operation(x, y) >= 0, operation(x, y) < n)
    for x in range(n):
        solver.add(z3.Distinct(*(operation(x, y) for y in range(n))))
    solver.add(z3.Distinct(*(operation(x, x) for x in range(n))))
    for x, y, z in product(range(n), repeat=3):
        solver.add(
            operation(operation(x, y), operation(x, z))
            == operation(operation(y, x), operation(y, z))
        )
    return solver, operation


def _subset_cut_transitivity(operation: z3.FuncDeclRef) -> list[z3.BoolRef]:
    """Exclude every nonempty proper invariant subset."""

    n = CARRIER_SIZE
    return [
        z3.Or(*(
            operation(x, y) == z
            for x, y, z in product(range(n), repeat=3)
            if ((mask >> y) & 1) != ((mask >> z) & 1)
        ))
        for mask in range(1, (1 << n) - 1)
    ]


def _reachability_transitivity(
    solver: z3.Solver,
    operation: z3.FuncDeclRef,
    *,
    prefix: str,
) -> None:
    """Require every point to be reachable from 0 in the row-action graph."""

    n = CARRIER_SIZE
    reach = [
        [z3.Bool(f"{prefix}_reach_{step}_{value}") for value in range(n)]
        for step in range(n)
    ]
    for value in range(n):
        solver.add(reach[0][value] == (value == 0))
    for step in range(n - 1):
        for target in range(n):
            solver.add(
                reach[step + 1][target]
                == z3.Or(
                    reach[step][target],
                    *(
                        z3.And(
                            reach[step][source],
                            operation(row, source) == target,
                        )
                        for row, source in product(range(n), repeat=2)
                    ),
                )
            )
    solver.add(*(reach[n - 1][value] for value in range(n)))


def _normalized_coprime_cycle(operation: z3.FuncDeclRef) -> z3.BoolRef:
    """Canonicalize a witnessed (row index, proper nontrivial cycle) pair."""

    cases = []
    for length in range(2, CARRIER_SIZE):
        inside_cycle = tuple(range(length))
        cases.append(z3.And(*(
            operation(0, inside_cycle[index])
            == inside_cycle[(index + 1) % length]
            for index in range(length)
        )))

        outside_cycle = tuple(range(1, length + 1))
        cases.append(z3.And(*(
            operation(0, outside_cycle[index])
            == outside_cycle[(index + 1) % length]
            for index in range(length)
        )))
    return z3.Or(*cases)


def _pin_constant_action(
    solver: z3.Solver,
    operation: z3.FuncDeclRef,
    permutation: list[int],
) -> None:
    for x, y in product(range(CARRIER_SIZE), repeat=2):
        solver.add(operation(x, y) == permutation[y])


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
    unseen = set(range(len(table)))
    result = []
    while unseen:
        root = min(unseen)
        orbit = {root}
        queue = deque([root])
        while queue:
            value = queue.popleft()
            for row in table:
                for neighbour in (row[value], row.index(value)):
                    if neighbour not in orbit:
                        orbit.add(neighbour)
                        queue.append(neighbour)
        result.append(sorted(orbit))
        unseen -= orbit
    return result


def _verify_constant_action(permutation: list[int]) -> dict[str, object]:
    n = len(permutation)
    table = [list(permutation) for _ in range(n)]
    return {
        "row_bijective": sorted(permutation) == list(range(n)),
        "diagonal_bijective": sorted(table[x][x] for x in range(n))
        == list(range(n)),
        "cycle_law": all(
            table[table[x][y]][table[x][z]]
            == table[table[y][x]][table[y][z]]
            for x, y, z in product(range(n), repeat=3)
        ),
        "action_orbits": _action_orbits(table),
        "cycle_type": sorted(
            (len(cycle) for cycle in _cycles(permutation)), reverse=True
        ),
    }


def _check(solver: z3.Solver) -> dict[str, object]:
    started = time.monotonic()
    status = solver.check()
    return {
        "solver_status": str(status),
        "reason_unknown": solver.reason_unknown(),
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "smt2_sha256": hashlib.sha256(solver.sexpr().encode("utf-8")).hexdigest(),
    }


def run_boundary(*, timeout_ms: int) -> dict[str, object]:
    n = CARRIER_SIZE
    coprime_control = [1, 0, 2, 3, 4, 5, 6]
    transitive_control = [1, 2, 3, 4, 5, 6, 0]

    coprime_solver, coprime_operation = _base_solver(
        "coprime_control_operation", timeout_ms=timeout_ms
    )
    _pin_constant_action(coprime_solver, coprime_operation, coprime_control)
    coprime_solver.add(_normalized_coprime_cycle(coprime_operation))
    coprime_result = _check(coprime_solver)

    transitive_solver, transitive_operation = _base_solver(
        "transitive_control_operation", timeout_ms=timeout_ms
    )
    _pin_constant_action(
        transitive_solver, transitive_operation, transitive_control
    )
    transitive_solver.add(*_subset_cut_transitivity(transitive_operation))
    transitive_result = _check(transitive_solver)

    target_solver, target_operation = _base_solver(
        "subset_target_operation", timeout_ms=timeout_ms
    )
    target_solver.add(*_subset_cut_transitivity(target_operation))
    target_solver.add(_normalized_coprime_cycle(target_operation))
    target_result = _check(target_solver)

    reachability_solver, reachability_operation = _base_solver(
        "reachability_target_operation", timeout_ms=timeout_ms
    )
    _reachability_transitivity(
        reachability_solver,
        reachability_operation,
        prefix="size7",
    )
    reachability_solver.add(_normalized_coprime_cycle(reachability_operation))
    reachability_result = _check(reachability_solver)

    coprime_verification = _verify_constant_action(coprime_control)
    transitive_verification = _verify_constant_action(transitive_control)
    if (
        coprime_result["solver_status"] != "sat"
        or transitive_result["solver_status"] != "sat"
        or coprime_verification["action_orbits"] != [[0, 1], [2], [3], [4], [5], [6]]
        or transitive_verification["action_orbits"] != [list(range(n))]
        or coprime_verification["cycle_type"] != [2, 1, 1, 1, 1, 1]
        or transitive_verification["cycle_type"] != [7]
    ):
        raise RuntimeError("matched controls do not discriminate the target conjunction")

    core: dict[str, object] = {
        "schema": SCHEMA,
        "carrier_size": n,
        "solver": f"z3-{z3.get_version_string()}",
        "timeout_ms_per_query": timeout_ms,
        "base_theory": {
            "left_rows_bijective": True,
            "diagonal_bijective": True,
            "cycle_set_identity": "(x*y)*(x*z)=(y*x)*(y*z)",
        },
        "target_predicate": {
            "coprime_cycle_lengths": list(range(2, n)),
            "normalization": (
                "under simultaneous carrier relabeling, set the witness row to 0; "
                "if the row index is on the cycle use 0->1->...->k-1->0, and "
                "otherwise use 1->2->...->k->1"
            ),
            "normalization_case_count": 2 * (n - 2),
            "primary_transitivity_encoding": "all proper invariant subset cuts",
            "crosscheck_transitivity_encoding": (
                "bounded reachability from 0 in the union of left-row action edges"
            ),
        },
        "matched_controls": {
            "coprime_cycle_without_transitivity": {
                **coprime_result,
                "permutation": coprime_control,
                "verification": coprime_verification,
            },
            "transitivity_without_coprime_cycle": {
                **transitive_result,
                "permutation": transitive_control,
                "verification": transitive_verification,
            },
        },
        "target_queries": {
            "subset_cut": target_result,
            "reachability_crosscheck": reachability_result,
        },
        "result": (
            "no_order_7_counterexample_two_encodings"
            if target_result["solver_status"] == "unsat"
            and reachability_result["solver_status"] == "unsat"
            else "no_order_7_counterexample_primary_encoding"
            if target_result["solver_status"] == "unsat"
            else "counterexample_candidate_or_unknown"
        ),
        "claim_boundary": (
            "exact only for order 7 under the displayed finite encoding and "
            "conjugacy normalization; no unrestricted implication or priority claim"
        ),
        "authority": "deterministic_campaign_local_boundary",
    }
    return {**core, "receipt_sha256": _canonical_hash(core)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-ms", type=int, default=1_200_000)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.timeout_ms < 1:
        parser.error("--timeout-ms must be positive")
    print(json.dumps(run_boundary(timeout_ms=args.timeout_ms), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
