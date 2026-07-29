"""Exact CEGIS pilot for extending a frozen binary ``[50,19,14]`` code.

The outer solver searches one canonical representative of each coset.  The
inner referee exhausts the full row span and returns an exact low-weight
codeword whenever the candidate coset misses distance 14.  A positive result
is replayed by the registered binary-code verifier.  Solver UNSAT is recorded
as pending an independent certificate; it is not promoted to a mathematical
null by this script alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import z3

from ztare.leanmill.adapters.binary_linear_code import (
    BinaryGeneratorMatrix,
    canonical_row_basis,
    gf2_rank_with_dependency,
    verify_binary_linear_code,
)
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.theory_ir import content_hash


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / (
    "axiompack_binary_linear_code_frontier_v1_20260717/"
    "binary_code_control_replay.json"
)
DEFAULT_OUTPUT = ROOT / "coset_extension_cegis_receipt.json"


def puncture(word: int, coordinate: int) -> int:
    lower = word & ((1 << coordinate) - 1)
    upper = word >> (coordinate + 1)
    return lower | (upper << coordinate)


def shortening_basis(rows: tuple[int, ...], coordinate: int) -> tuple[int, ...]:
    active = [index for index, row in enumerate(rows) if (row >> coordinate) & 1]
    if not active:
        return rows
    pivot = active[0]
    pivot_row = rows[pivot]
    return tuple(
        row if not ((row >> coordinate) & 1) else row ^ pivot_row
        for index, row in enumerate(rows)
        if index != pivot
    )


def frozen_shortening(coordinate: int) -> BinaryGeneratorMatrix:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    source = BinaryGeneratorMatrix.from_json(payload["extended_matrix"])
    if source.length != 51 or source.dimension != 20:
        raise ValueError("coset pilot received a different source category")
    if not 0 <= coordinate < source.length:
        raise ValueError("shortening coordinate is out of range")
    kernel = shortening_basis(source.rows, coordinate)
    rows = tuple(puncture(row, coordinate) for row in kernel)
    rank, dependency = gf2_rank_with_dependency(rows)
    if rank != 19 or dependency is not None:
        raise AssertionError("frozen shortening does not have dimension 19")
    return canonical_row_basis(
        BinaryGeneratorMatrix(length=50, dimension=19, rows=rows)
    )


def quotient_coordinates(
    matrix: BinaryGeneratorMatrix,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    pivots = tuple((row & -row).bit_length() - 1 for row in matrix.rows)
    if len(set(pivots)) != matrix.dimension:
        raise AssertionError("canonical shortening has repeated pivots")
    for row_index, pivot in enumerate(pivots):
        if any(
            ((row >> pivot) & 1) != int(index == row_index)
            for index, row in enumerate(matrix.rows)
        ):
            raise AssertionError("pivot restriction is not the identity")
    free = tuple(index for index in range(matrix.length) if index not in pivots)
    if len(free) != matrix.length - matrix.dimension:
        raise AssertionError("quotient coordinate count is inconsistent")
    return pivots, free


def model_word(model: z3.ModelRef, variables: tuple[z3.BoolRef, ...], free: tuple[int, ...]) -> int:
    word = 0
    for variable, coordinate in zip(variables, free, strict=True):
        if z3.is_true(model.eval(variable, model_completion=True)):
            word |= 1 << coordinate
    return word


def distance_constraint(
    variables: tuple[z3.BoolRef, ...],
    free: tuple[int, ...],
    pivots: tuple[int, ...],
    center: int,
    threshold: int,
    *,
    encoding: str,
) -> z3.BoolRef:
    fixed_weight = sum((center >> coordinate) & 1 for coordinate in pivots)
    literals = [
        variable if ((center >> coordinate) & 1) == 0 else z3.Not(variable)
        for variable, coordinate in zip(variables, free, strict=True)
    ]
    residual = threshold - fixed_weight
    if residual <= 0:
        return z3.BoolVal(True)
    if residual > len(literals):
        return z3.BoolVal(False)
    if encoding == "pb":
        return z3.PbGe([(literal, 1) for literal in literals], residual)
    if encoding == "lia":
        return z3.Sum([z3.If(literal, 1, 0) for literal in literals]) >= residual
    raise ValueError("unknown cardinality encoding")


def exact_coset_minimum(
    matrix: BinaryGeneratorMatrix, representative: int
) -> tuple[int, int, int, int]:
    """Return minimum weight, message, codeword, and examined word count."""

    best_weight = representative.bit_count()
    best_message = 0
    best_codeword = 0
    previous_gray = 0
    codeword = 0
    required = (1 << matrix.dimension) - 1
    for step in range(1, required + 1):
        gray = step ^ (step >> 1)
        codeword ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
        weight = (representative ^ codeword).bit_count()
        if weight < best_weight:
            best_weight = weight
            best_message = gray
            best_codeword = codeword
        previous_gray = gray
    return best_weight, best_message, best_codeword, required + 1


def run_pilot(
    *, coordinate: int, max_iterations: int, timeout_s: int, encoding: str = "pb"
) -> dict[str, object]:
    if max_iterations < 1 or timeout_s < 1:
        raise ValueError("pilot caps must be positive")
    if encoding not in {"pb", "lia"}:
        raise ValueError("encoding must be 'pb' or 'lia'")
    matrix = frozen_shortening(coordinate)
    pivots, free = quotient_coordinates(matrix)
    variables = tuple(z3.Bool(f"q_{index:02d}") for index in range(len(free)))
    solver = z3.Solver()
    solver.set(random_seed=0)
    centers: list[dict[str, object]] = []
    zero_constraint = distance_constraint(
        variables, free, pivots, 0, 14, encoding=encoding
    )
    solver.add(zero_constraint)
    centers.append(
        {
            "message_hex": "0x00000",
            "codeword_hex": "0x0000000000000",
            "constraint_sha256": content_hash({"center": 0, "threshold": 14}),
        }
    )
    trajectory: list[dict[str, object]] = []
    started = time.monotonic()
    status = "iteration_cap_reached"
    candidate_artifact: dict[str, object] | None = None
    verification: dict[str, object] | None = None
    solver_snapshot_sha256 = ""

    for iteration in range(1, max_iterations + 1):
        remaining_ms = int((timeout_s - (time.monotonic() - started)) * 1_000)
        if remaining_ms <= 0:
            status = "time_cap_reached"
            break
        solver.set(timeout=remaining_ms)
        check = solver.check()
        if check == z3.unsat:
            status = "solver_unsat_pending_independent_certificate"
            solver_snapshot_sha256 = content_hash({"smt2": solver.to_smt2()})
            break
        if check != z3.sat:
            status = "solver_unavailable:" + str(solver.reason_unknown())
            break
        representative = model_word(solver.model(), variables, free)
        minimum, message, center, examined = exact_coset_minimum(
            matrix, representative
        )
        coset_word = representative ^ center
        row: dict[str, object] = {
            "iteration": iteration,
            "representative_hex": f"0x{representative:013x}",
            "representative_weight": representative.bit_count(),
            "minimum_coset_weight": minimum,
            "referee_examined_words": examined,
            "referee_message_hex": f"0x{message:05x}",
            "referee_codeword_hex": f"0x{center:013x}",
            "referee_coset_word_hex": f"0x{coset_word:013x}",
        }
        trajectory.append(row)
        if minimum >= 14:
            raw = BinaryGeneratorMatrix(
                length=50,
                dimension=20,
                rows=(*matrix.rows, representative),
            )
            rank, dependency = gf2_rank_with_dependency(raw.rows)
            if rank != 20 or dependency is not None:
                raise AssertionError("surviving coset representative is not independent")
            verification = verify_binary_linear_code(
                raw,
                required_rank=20,
                required_minimum_distance=14,
                max_nonzero_messages=(1 << 20) - 1,
            )
            if verification["status"] != "satisfied":
                raise AssertionError("registered verifier rejected the CEGIS survivor")
            candidate_artifact = raw.to_json()
            status = "witness_found_pending_ratification"
            break
        if (representative ^ center).bit_count() != minimum:
            raise AssertionError("referee witness weight does not replay")
        solver.add(
            distance_constraint(
                variables, free, pivots, center, 14, encoding=encoding
            )
        )
        centers.append(
            {
                "message_hex": f"0x{message:05x}",
                "codeword_hex": f"0x{center:013x}",
                "constraint_sha256": content_hash(
                    {"center": center, "threshold": 14}
                ),
            }
        )
    else:
        solver_snapshot_sha256 = content_hash({"smt2": solver.to_smt2()})

    elapsed_ms = max(1, int((time.monotonic() - started) * 1_000))
    core: dict[str, object] = {
        "schema": "axiompack.binary_coset_extension_cegis.v1",
        "status": status,
        "source_artifact_sha256": matrix.artifact_sha256,
        "shortening_coordinate": coordinate,
        "shortening_length": matrix.length,
        "shortening_dimension": matrix.dimension,
        "shortening_minimum_distance": 14,
        "pivot_coordinates": list(pivots),
        "quotient_coordinates": list(free),
        "quotient_dimension": len(free),
        "gauge": "bits_on_canonical_row_pivots_are_zero",
        "target_coset_distance": 14,
        "cardinality_encoding": encoding,
        "max_iterations": max_iterations,
        "timeout_s": timeout_s,
        "elapsed_ms": elapsed_ms,
        "z3_version": z3.get_version_string(),
        "constraint_centers": centers,
        "trajectory": trajectory,
        "solver_snapshot_sha256": solver_snapshot_sha256,
        "candidate_artifact": candidate_artifact,
        "registered_verification_receipt": verification,
        "claim_scope": (
            "one explicit candidate pending construction-artifact ratification"
            if status == "witness_found_pending_ratification"
            else "bounded coset-search evidence only; no extension-cone or ambient nonexistence authority"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coordinate", type=int, default=0)
    parser.add_argument("--max-iterations", type=int, default=500)
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--encoding", choices=("pb", "lia"), default="pb")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_pilot(
        coordinate=args.coordinate,
        max_iterations=args.max_iterations,
        timeout_s=args.timeout_s,
        encoding=args.encoding,
    )
    write_json_atomic(args.output, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "iterations": len(receipt["trajectory"]),
                "last_minimum_coset_weight": (
                    receipt["trajectory"][-1]["minimum_coset_weight"]
                    if receipt["trajectory"]
                    else None
                ),
                "receipt_sha256": receipt["receipt_sha256"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
