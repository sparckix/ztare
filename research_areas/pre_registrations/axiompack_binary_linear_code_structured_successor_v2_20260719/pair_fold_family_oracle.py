"""Exact referee for every two-coordinate fold of the frozen [51,20,14] code.

The family and its kill condition were specified in ``lane_cold_family.md``
before this oracle ran.  The referee enumerates the source row span once,
records a minimum-weight word covering each coordinate pair, and checks the
corresponding folded generator directly.  Its conclusion is scoped to the
complete 1,275-member family; it has no ambient code-table authority.
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

from ztare.leanmill.adapters.binary_linear_code import (
    BinaryGeneratorMatrix,
    gf2_rank_with_dependency,
)
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.theory_ir import content_hash


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / (
    "axiompack_binary_linear_code_frontier_v1_20260717/"
    "binary_code_control_replay.json"
)
DEFAULT_OUTPUT = ROOT / "pair_fold_family_oracle_receipt.json"


def fold_pair(word: int, left: int, right: int) -> int:
    """Replace coordinates ``left,right`` by their xor, preserving order."""

    if not 0 <= left < right:
        raise ValueError("fold pair must be strictly ordered")
    combined = ((word >> left) ^ (word >> right)) & 1
    without_right = (word & ((1 << right) - 1)) | ((word >> (right + 1)) << right)
    if combined:
        return without_right | (1 << left)
    return without_right & ~(1 << left)


def evaluate(rows: tuple[int, ...], message: int) -> int:
    word = 0
    for index, row in enumerate(rows):
        if (message >> index) & 1:
            word ^= row
    return word


def build_receipt() -> dict[str, object]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    matrix = BinaryGeneratorMatrix.from_json(payload["extended_matrix"])
    if matrix.length != 51 or matrix.dimension != 20:
        raise ValueError("pair-fold oracle received a different source category")

    pairs = tuple(combinations(range(matrix.length), 2))
    first_covering_witness: dict[tuple[int, int], tuple[int, int]] = {}
    source_minimum_distance = matrix.length + 1
    minimum_word_count = 0
    previous_gray = 0
    word = 0
    required = (1 << matrix.dimension) - 1

    for step in range(1, required + 1):
        gray = step ^ (step >> 1)
        word ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
        weight = word.bit_count()
        if weight < source_minimum_distance:
            source_minimum_distance = weight
            minimum_word_count = 0
            first_covering_witness.clear()
        if weight == source_minimum_distance:
            minimum_word_count += 1
            support = tuple(
                coordinate
                for coordinate in range(matrix.length)
                if (word >> coordinate) & 1
            )
            for pair in combinations(support, 2):
                first_covering_witness.setdefault(pair, (gray, word))
        previous_gray = gray

    if source_minimum_distance != 14:
        raise AssertionError("frozen source no longer has minimum distance 14")
    if set(first_covering_witness) != set(pairs):
        raise AssertionError("minimum-word two-shadow does not cover every pair")

    members: list[dict[str, object]] = []
    for left, right in pairs:
        message, source_word = first_covering_witness[(left, right)]
        folded_rows = tuple(fold_pair(row, left, right) for row in matrix.rows)
        folded_word = fold_pair(source_word, left, right)
        if evaluate(folded_rows, message) != folded_word:
            raise AssertionError("folding did not commute with row-span evaluation")
        if folded_word.bit_count() != 12:
            raise AssertionError("pair witness did not lose exactly two support points")
        rank, dependency = gf2_rank_with_dependency(folded_rows)
        if rank != matrix.dimension or dependency is not None:
            raise AssertionError("pair fold lost source dimension")
        members.append(
            {
                "parameter_id": f"fold_{left:02d}_{right:02d}",
                "pair": [left, right],
                "rank": rank,
                "dependency_message_hex": None,
                "low_weight_witness": {
                    "message_hex": f"0x{message:05x}",
                    "source_codeword_hex": f"0x{source_word:013x}",
                    "folded_codeword_hex": f"0x{folded_word:013x}",
                    "weight": folded_word.bit_count(),
                },
                "target_rejected": True,
            }
        )

    parameter_ids = [str(member["parameter_id"]) for member in members]
    core: dict[str, object] = {
        "schema": "axiompack.binary_linear_pair_fold_oracle.v1",
        "source_artifact_sha256": matrix.artifact_sha256,
        "source_length": matrix.length,
        "source_dimension": matrix.dimension,
        "source_minimum_distance": source_minimum_distance,
        "examined_nonzero_source_messages": required,
        "minimum_word_count": minimum_word_count,
        "family_relation": (
            "replace each unordered coordinate pair by its binary xor and retain "
            "the other 49 coordinates"
        ),
        "declared_cardinality": len(pairs),
        "parameter_domain_sha256": content_hash(parameter_ids),
        "all_pairs_covered_by_minimum_words": True,
        "all_members_rank_20": True,
        "all_members_have_weight_12_counterexample": True,
        "members": members,
        "claim_scope": (
            "complete frozen pair-fold family only; no ambient [50,20,14] "
            "nonexistence or novelty authority"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = build_receipt()
    write_json_atomic(args.output, receipt)
    print(
        json.dumps(
            {
                "status": "exhausted",
                "declared_cardinality": receipt["declared_cardinality"],
                "source_minimum_distance": receipt["source_minimum_distance"],
                "counterexample_weight": 12,
                "receipt_sha256": receipt["receipt_sha256"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
