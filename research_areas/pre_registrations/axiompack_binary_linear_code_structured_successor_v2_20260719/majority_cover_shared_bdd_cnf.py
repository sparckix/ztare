#!/usr/bin/env python3
"""Exact shared-ROBDD CNF discriminator for the frozen majority cover.

This is a campaign-local proof-object probe.  It hash-conses ordered BDD nodes
across all named cardinality constraints, asks CaDiCaL for a terminal status,
and replays every SAT support against the original code.  SAT is a negative
result for the proposed core, not a code construction.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Final

from coset_extension_cegis import exact_coset_minimum, frozen_shortening
from majority_cover_core_cegis import all_codewords_by_weight
from ztare.leanmill.adapters.binary_linear_code import (
    BinaryGeneratorMatrix,
    verify_binary_linear_code,
)
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.theory_ir import content_hash


ROOT = Path(__file__).resolve().parent
DEFAULT_PROPOSAL = ROOT / "majority_cover_core_proposal.json"
DEFAULT_OUTPUT = ROOT / "majority_cover_shared_bdd_receipt.json"
FALSE: Final[int] = 0
TRUE: Final[int] = -1


class SharedBDD:
    """One ordered reduced BDD manager and its positive-root CNF encoding."""

    def __init__(self, input_count: int) -> None:
        self.input_count = input_count
        self.variable_count = input_count
        self.nodes: dict[int, tuple[int, int, int]] = {}
        self.unique: dict[tuple[int, int, int], int] = {}
        self.at_most_cache: dict[tuple[tuple[int, ...], int], int] = {}
        self.exact_cache: dict[tuple[tuple[int, ...], int], int] = {}
        self.clauses: list[tuple[int, ...]] = []
        self.roots: list[int] = []

    @staticmethod
    def _append_child(base: tuple[int, ...], child: int) -> tuple[int, ...] | None:
        if child == TRUE:
            return None
        if child == FALSE:
            return base
        return (*base, child)

    def _node(self, coordinate: int, low: int, high: int) -> int:
        if low == high:
            return low
        key = (coordinate, low, high)
        old = self.unique.get(key)
        if old is not None:
            return old
        self.variable_count += 1
        node = self.variable_count
        self.unique[key] = node
        self.nodes[node] = key
        input_variable = coordinate + 1
        low_clause = self._append_child((-node, input_variable), low)
        high_clause = self._append_child((-node, -input_variable), high)
        if low_clause is not None:
            self.clauses.append(low_clause)
        if high_clause is not None:
            self.clauses.append(high_clause)
        return node

    def at_most(self, support: tuple[int, ...], maximum: int) -> int:
        key = (support, maximum)
        old = self.at_most_cache.get(key)
        if old is not None:
            return old
        if maximum < 0:
            result = FALSE
        elif len(support) <= maximum:
            result = TRUE
        elif not support:
            result = TRUE
        else:
            coordinate, rest = support[0], support[1:]
            result = self._node(
                coordinate,
                self.at_most(rest, maximum),
                self.at_most(rest, maximum - 1),
            )
        self.at_most_cache[key] = result
        return result

    def exactly(self, support: tuple[int, ...], target: int) -> int:
        key = (support, target)
        old = self.exact_cache.get(key)
        if old is not None:
            return old
        if target < 0 or target > len(support):
            result = FALSE
        elif not support:
            result = TRUE
        else:
            coordinate, rest = support[0], support[1:]
            result = self._node(
                coordinate,
                self.exactly(rest, target),
                self.exactly(rest, target - 1),
            )
        self.exact_cache[key] = result
        return result

    def assert_root(self, root: int) -> None:
        if root == FALSE:
            raise ValueError("attempted to assert a false BDD root")
        self.roots.append(root)
        if root != TRUE:
            self.clauses.append((root,))

    def evaluate(self, root: int, support_word: int) -> bool:
        while root not in (FALSE, TRUE):
            coordinate, low, high = self.nodes[root]
            root = high if support_word >> coordinate & 1 else low
        return root == TRUE

    def render(self, path: Path) -> dict[str, object]:
        digest = hashlib.sha256()
        byte_count = 0
        with path.open("wb") as handle:
            header = f"p cnf {self.variable_count} {len(self.clauses)}\n".encode("ascii")
            handle.write(header)
            digest.update(header)
            byte_count += len(header)
            for clause in self.clauses:
                row = (" ".join(map(str, clause)) + " 0\n").encode("ascii")
                handle.write(row)
                digest.update(row)
                byte_count += len(row)
        return {
            "cnf_sha256": digest.hexdigest(),
            "cnf_bytes": byte_count,
            "variable_count": self.variable_count,
            "input_variable_count": self.input_count,
            "auxiliary_variable_count": self.variable_count - self.input_count,
            "clause_count": len(self.clauses),
            "unique_bdd_node_count": len(self.nodes),
            "asserted_root_count": len(self.roots),
        }


def find_cadical() -> tuple[str, str]:
    direct = shutil.which("cadical")
    if direct is None:
        repo = next(parent for parent in ROOT.parents if (parent / ".git").exists())
        completed = subprocess.run(
            ["lake", "env", "which", "cadical"],
            cwd=repo / "ztare_proofs",
            check=True,
            capture_output=True,
            text=True,
        )
        direct = completed.stdout.strip().splitlines()[-1]
    version = subprocess.run(
        [direct, "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    return direct, version


def parse_model(path: Path, input_count: int) -> int:
    literals: list[int] = []
    for row in path.read_text(encoding="ascii").splitlines():
        if row.startswith("v "):
            literals.extend(int(value) for value in row.split()[1:] if value != "0")
    assignment = {abs(literal): literal > 0 for literal in literals}
    if any(index not in assignment for index in range(1, input_count + 1)):
        raise ValueError("CaDiCaL witness omitted an input variable")
    return sum(1 << (index - 1) for index in range(1, input_count + 1) if assignment[index])


def encode(constraints: tuple[int, ...]) -> tuple[SharedBDD, list[int]]:
    bdd = SharedBDD(input_count=50)
    exact_root = bdd.exactly(tuple(range(50)), 14)
    bdd.assert_root(exact_root)
    roots: list[int] = []
    for codeword in constraints:
        support = tuple(index for index in range(50) if codeword >> index & 1)
        root = bdd.at_most(support, len(support) // 2)
        bdd.assert_root(root)
        roots.append(root)
    return bdd, roots


def replay_support(
    support: int,
    constraints: tuple[int, ...],
    bdd: SharedBDD,
    roots: list[int],
) -> dict[str, object]:
    if support.bit_count() != 14:
        raise AssertionError("BDD CNF model crossed the exact-weight carrier")
    violations = [
        codeword
        for codeword in constraints
        if (support & codeword).bit_count() > codeword.bit_count() // 2
    ]
    if violations:
        raise AssertionError("BDD CNF model violated a named majority inequality")
    if any(not bdd.evaluate(root, support) for root in roots):
        raise AssertionError("BDD evaluator rejected a CaDiCaL model")
    matrix = frozen_shortening(0)
    minimum, message, codeword, examined = exact_coset_minimum(matrix, support)
    result: dict[str, object] = {
        "support_hex": f"0x{support:013x}",
        "support_weight": support.bit_count(),
        "named_constraint_replay": "passed",
        "exact_coset_minimum": minimum,
        "referee_message_hex": f"0x{message:05x}",
        "referee_codeword_hex": f"0x{codeword:013x}",
        "referee_codeword_weight": codeword.bit_count(),
        "referee_intersection": (support & codeword).bit_count(),
        "referee_reduced_word_hex": f"0x{support ^ codeword:013x}",
        "referee_examined_words": examined,
    }
    if minimum >= 14:
        candidate = BinaryGeneratorMatrix(
            length=50,
            dimension=20,
            rows=(*matrix.rows, support),
        )
        result["registered_candidate_verification"] = verify_binary_linear_code(
            candidate,
            required_rank=20,
            required_minimum_distance=14,
            max_nonzero_messages=(1 << 20) - 1,
        )
    return result


def run_instance(
    *,
    name: str,
    constraints: tuple[int, ...],
    cadical: str,
    timeout_s: int,
    output_dir: Path,
) -> dict[str, object]:
    bdd, roots = encode(constraints)
    cnf_path = output_dir / f"majority_cover_shared_bdd_{name}.cnf"
    model_path = output_dir / f"majority_cover_shared_bdd_{name}.model"
    measurement = bdd.render(cnf_path)
    caps = {
        "variables": 100_000,
        "clauses": 250_000,
        "trimmed_lrat_bytes": 25 * 1024 * 1024,
        "explicit_lean_seconds": 180,
    }
    within_cnf_caps = (
        measurement["variable_count"] <= caps["variables"]
        and measurement["clause_count"] <= caps["clauses"]
    )
    completed = subprocess.run(
        [cadical, "--sat", "-t", str(timeout_s), "-q", "-w", str(model_path), str(cnf_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 10:
        status = "sat"
        support = parse_model(model_path, 50)
        replay = replay_support(support, constraints, bdd, roots)
        proof_disposition = "not_attempted_sat_instance"
    elif completed.returncode == 20:
        status = "unsat"
        replay = None
        proof_disposition = (
            "lrat_generation_required" if within_cnf_caps else "not_attempted_cnf_cap_exceeded"
        )
    else:
        status = "unavailable"
        replay = None
        proof_disposition = "not_attempted_no_terminal_solver_status"
    model_path.unlink(missing_ok=True)
    histogram = Counter(codeword.bit_count() for codeword in constraints)
    return {
        "name": name,
        "constraint_count": len(constraints),
        "constraint_weight_histogram": {
            str(weight): count for weight, count in sorted(histogram.items())
        },
        "constraint_set_sha256": content_hash(
            [f"0x{codeword:013x}" for codeword in constraints]
        ),
        "encoding": {
            "kind": "globally_hash_consed_ordered_reduced_bdd_positive_root_cnf",
            "coordinate_order": list(range(50)),
            **measurement,
            "caps": caps,
            "within_cnf_caps": within_cnf_caps,
        },
        "cadical": {
            "status": status,
            "returncode": completed.returncode,
            "timeout_s": timeout_s,
        },
        "sat_replay": replay,
        "proof_trace_disposition": proof_disposition,
    }


def self_test() -> dict[str, object]:
    cases = 0
    for maximum in range(5):
        bdd = SharedBDD(input_count=6)
        root = bdd.at_most((0, 1, 2, 3, 4, 5), maximum)
        for support in range(1 << 6):
            if bdd.evaluate(root, support) != (support.bit_count() <= maximum):
                raise AssertionError("at-most BDD self-test failed")
            cases += 1
    for target in range(7):
        bdd = SharedBDD(input_count=6)
        root = bdd.exactly((0, 1, 2, 3, 4, 5), target)
        for support in range(1 << 6):
            if bdd.evaluate(root, support) != (support.bit_count() == target):
                raise AssertionError("exact BDD self-test failed")
            cases += 1
    return {"status": "passed", "evaluated_assignments": cases}


def run(*, proposal_path: Path, output_dir: Path, timeout_s: int) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    matrix = frozen_shortening(0)
    _, by_weight = all_codewords_by_weight()
    base = tuple(sorted(by_weight[14]))
    added = tuple(int(row["codeword_hex"], 16) for row in proposal["added_constraints"])
    if len(set((*base, *added))) != len(base) + len(added):
        raise AssertionError("selected core contains duplicate codewords")
    first_mixed_index = next(
        index for index, codeword in enumerate(added) if codeword.bit_count() != 14
    )
    first_mixed = (*base, *added[: first_mixed_index + 1])
    accumulated = (*base, *added)
    cadical, cadical_version = find_cadical()
    runs = [
        run_instance(
            name="base_weight14",
            constraints=base,
            cadical=cadical,
            timeout_s=timeout_s,
            output_dir=output_dir,
        ),
        run_instance(
            name="smallest_mixed_prefix",
            constraints=first_mixed,
            cadical=cadical,
            timeout_s=timeout_s,
            output_dir=output_dir,
        ),
        run_instance(
            name="accumulated_mixed_core",
            constraints=accumulated,
            cadical=cadical,
            timeout_s=timeout_s,
            output_dir=output_dir,
        ),
    ]
    if any(row["cadical"]["status"] == "unsat" for row in runs):
        disposition = "unsat_instance_requires_lrat_followup"
    elif all(row["cadical"]["status"] == "sat" for row in runs):
        disposition = "certificate_unavailable_sat_selected_cores"
    else:
        disposition = "certificate_unavailable_solver_status"
    body = {
        "schema": "axiompack.binary_majority_cover_shared_bdd_discriminator.v1",
        "status": disposition,
        "source_artifact_sha256": matrix.artifact_sha256,
        "core_proposal_receipt_sha256": proposal["receipt_sha256"],
        "encoding_self_test": self_test(),
        "cadical_version": cadical_version,
        "runs": runs,
        "claim_scope": (
            "proof-carrier measurement and exact SAT-model replay for one frozen "
            "shortening; no covering-radius or ambient code-existence conclusion"
        ),
    }
    return {**body, "receipt_sha256": content_hash(body)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, default=DEFAULT_PROPOSAL)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "majority_shared_bdd")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-s", type=int, default=180)
    args = parser.parse_args()
    receipt = run(
        proposal_path=args.proposal,
        output_dir=args.output_dir,
        timeout_s=args.timeout_s,
    )
    write_json_atomic(args.output, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "runs": [
                    {
                        "name": row["name"],
                        "constraints": row["constraint_count"],
                        "variables": row["encoding"]["variable_count"],
                        "clauses": row["encoding"]["clause_count"],
                        "cadical": row["cadical"]["status"],
                        "minimum": (
                            row["sat_replay"]["exact_coset_minimum"]
                            if row["sat_replay"] is not None
                            else None
                        ),
                    }
                    for row in receipt["runs"]
                ],
                "receipt_sha256": receipt["receipt_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
