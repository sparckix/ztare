"""Untrusted core producer for a proof-producing majority-cover certificate.

The solver searches a weight-14 support satisfying the currently retained
majority inequalities.  The exact row-span referee either finds a lighter word
and adds its original codeword support, or returns a distance-14 extension
witness.  Solver UNSAT is only a proposed core for later CNF/LRAT replay; this
script grants no covering-radius conclusion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import z3

from coset_extension_cegis import exact_coset_minimum, frozen_shortening
from ztare.leanmill.adapters.binary_linear_code import (
    BinaryGeneratorMatrix,
    verify_binary_linear_code,
)
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.theory_ir import content_hash


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "majority_cover_core_proposal.json"


def all_codewords_by_weight() -> tuple[dict[int, int], dict[int, list[int]]]:
    matrix = frozen_shortening(0)
    message_of: dict[int, int] = {0: 0}
    by_weight: dict[int, list[int]] = {}
    previous_gray = 0
    word = 0
    for step in range(1, 1 << matrix.dimension):
        gray = step ^ (step >> 1)
        word ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
        message_of[word] = gray
        by_weight.setdefault(word.bit_count(), []).append(word)
        previous_gray = gray
    if len(message_of) != 1 << matrix.dimension:
        raise AssertionError("frozen row-span enumeration lost a codeword")
    return message_of, by_weight


def add_majority_constraint(
    solver: z3.Solver,
    variables: tuple[z3.BoolRef, ...],
    codeword: int,
) -> None:
    weight = codeword.bit_count()
    if not 14 <= weight <= 26 or weight & 1:
        raise ValueError("majority core received an inapplicable codeword weight")
    support = [(variables[index], 1) for index in range(50) if codeword >> index & 1]
    solver.add(z3.PbLe(support, weight // 2))


def run(*, timeout_s: int, max_added: int) -> dict[str, object]:
    if timeout_s < 1 or max_added < 1:
        raise ValueError("core-producer caps must be positive")
    matrix = frozen_shortening(0)
    message_of, by_weight = all_codewords_by_weight()
    base = tuple(sorted(by_weight[14]))
    variables = tuple(z3.Bool(f"x_{index:02d}") for index in range(50))
    solver = z3.Solver()
    solver.set(random_seed=0)
    solver.add(z3.PbEq([(variable, 1) for variable in variables], 14))
    for codeword in base:
        add_majority_constraint(solver, variables, codeword)

    selected = set(base)
    added: list[dict[str, object]] = []
    trajectory: list[dict[str, object]] = []
    started = time.monotonic()
    status = "added_constraint_cap_reached"
    candidate_artifact = None
    candidate_verification = None

    for iteration in range(1, max_added + 1):
        remaining_ms = int((timeout_s - (time.monotonic() - started)) * 1000)
        if remaining_ms <= 0:
            status = "time_cap_reached"
            break
        solver.set(timeout=remaining_ms)
        check = solver.check()
        if check == z3.unsat:
            status = "unsat_core_proposed_pending_cnf_lrat_and_bridge"
            break
        if check != z3.sat:
            status = "solver_unavailable:" + solver.reason_unknown()
            break
        model = solver.model()
        support = sum(
            1 << index
            for index, variable in enumerate(variables)
            if z3.is_true(model.eval(variable, model_completion=True))
        )
        if support.bit_count() != 14:
            raise AssertionError("solver model crossed the exact-weight carrier")
        minimum, message, codeword, examined = exact_coset_minimum(matrix, support)
        row = {
            "iteration": iteration,
            "support_hex": f"0x{support:013x}",
            "exact_coset_minimum": minimum,
            "referee_message_hex": f"0x{message:05x}",
            "referee_codeword_hex": f"0x{codeword:013x}",
            "referee_codeword_weight": codeword.bit_count(),
            "referee_intersection": (support & codeword).bit_count(),
            "referee_reduced_word_hex": f"0x{support ^ codeword:013x}",
            "referee_examined_words": examined,
        }
        trajectory.append(row)
        if minimum >= 14:
            candidate = BinaryGeneratorMatrix(
                length=50,
                dimension=20,
                rows=(*matrix.rows, support),
            )
            candidate_verification = verify_binary_linear_code(
                candidate,
                required_rank=20,
                required_minimum_distance=14,
                max_nonzero_messages=(1 << 20) - 1,
            )
            if candidate_verification["status"] != "satisfied":
                raise AssertionError("registered adapter rejected the exact survivor")
            candidate_artifact = candidate.to_json()
            status = "witness_found_pending_ratification"
            break
        weight = codeword.bit_count()
        intersection = (support & codeword).bit_count()
        if intersection <= weight // 2 or (support ^ codeword).bit_count() != minimum:
            raise AssertionError("row-span witness does not violate its majority inequality")
        if codeword in selected:
            raise AssertionError("solver repeated a retained majority violation")
        selected.add(codeword)
        add_majority_constraint(solver, variables, codeword)
        added.append(
            {
                "message_hex": f"0x{message_of[codeword]:05x}",
                "codeword_hex": f"0x{codeword:013x}",
                "weight": weight,
            }
        )
    else:
        status = "added_constraint_cap_reached"

    selected_histogram: dict[str, int] = {}
    for codeword in selected:
        key = str(codeword.bit_count())
        selected_histogram[key] = selected_histogram.get(key, 0) + 1
    core = {
        "schema": "axiompack.binary_majority_cover_core_proposal.v1",
        "status": status,
        "source_artifact_sha256": matrix.artifact_sha256,
        "base_selection": "all_weight_14_codewords",
        "base_constraint_count": len(base),
        "base_codeword_set_sha256": content_hash(
            [f"0x{codeword:013x}" for codeword in base]
        ),
        "added_constraints": added,
        "selected_constraint_count": len(selected),
        "selected_weight_histogram": selected_histogram,
        "trajectory": trajectory,
        "candidate_artifact": candidate_artifact,
        "registered_candidate_verification": candidate_verification,
        "timeout_s": timeout_s,
        "max_added": max_added,
        "elapsed_ms": max(1, int((time.monotonic() - started) * 1000)),
        "z3_version": z3.get_version_string(),
        "claim_scope": (
            "untrusted selected-core proposal pending exact CNF, LRAT, explicit "
            "Lean proof construction, and CNF-to-majority-cover bridge"
            if status.startswith("unsat")
            else "bounded core-search evidence only; no covering-radius or ambient authority"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--max-added", type=int, default=2000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run(timeout_s=args.timeout_s, max_added=args.max_added)
    write_json_atomic(args.output, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "selected_constraint_count": receipt["selected_constraint_count"],
                "selected_weight_histogram": receipt["selected_weight_histogram"],
                "iterations": len(receipt["trajectory"]),
                "receipt_sha256": receipt["receipt_sha256"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
