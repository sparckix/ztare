"""Independent exact oracle for all one-coordinate shortenings of the frozen code.

The campaign proposal is not imported.  This referee enumerates the source
row span once, computes the exact minimum among words whose selected
coordinate is zero, and separately checks the rank of each shortened basis.
"""
from __future__ import annotations

import json
from pathlib import Path

from ztare.leanmill.adapters.binary_linear_code import (
    BinaryGeneratorMatrix,
    gf2_rank_with_dependency,
)
from ztare.leanmill.theory_ir import content_hash


SOURCE = Path(__file__).parents[1] / (
    "axiompack_binary_linear_code_frontier_v1_20260717/"
    "binary_code_control_replay.json"
)


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


payload = json.loads(SOURCE.read_text(encoding="utf-8"))
matrix = BinaryGeneratorMatrix.from_json(payload["extended_matrix"])
required = (1 << matrix.dimension) - 1

best_zero_weight = [matrix.length + 1] * matrix.length
best_zero_witness: list[dict[str, str] | None] = [None] * matrix.length
source_minimum_distance = matrix.length + 1
previous_gray = 0
word = 0
full_support = (1 << matrix.length) - 1

for step in range(1, required + 1):
    gray = step ^ (step >> 1)
    word ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
    weight = word.bit_count()
    source_minimum_distance = min(source_minimum_distance, weight)
    if weight < max(best_zero_weight):
        zero_coordinates = full_support ^ word
        while zero_coordinates:
            low_bit = zero_coordinates & -zero_coordinates
            coordinate = low_bit.bit_length() - 1
            if weight < best_zero_weight[coordinate]:
                best_zero_weight[coordinate] = weight
                best_zero_witness[coordinate] = {
                    "source_message_hex": f"0x{gray:05x}",
                    "source_codeword_hex": f"0x{word:013x}",
                    "shortened_codeword_hex": (
                        f"0x{puncture(word, coordinate):013x}"
                    ),
                }
            zero_coordinates ^= low_bit
    previous_gray = gray

members = []
for coordinate in range(matrix.length):
    kernel_rows = shortening_basis(matrix.rows, coordinate)
    if any((row >> coordinate) & 1 for row in kernel_rows):
        raise AssertionError("shortening basis did not enter the coordinate kernel")
    shortened_rows = tuple(puncture(row, coordinate) for row in kernel_rows)
    rank, dependency = gf2_rank_with_dependency(shortened_rows)
    members.append(
        {
            "coordinate": coordinate,
            "kernel_generator_count": len(kernel_rows),
            "rank": rank,
            "dependency_message_hex": (
                f"0x{dependency:05x}" if dependency is not None else None
            ),
            "minimum_distance": best_zero_weight[coordinate],
            "minimum_word_witness": best_zero_witness[coordinate],
        }
    )

core = {
    "schema": "axiompack.binary_linear_shortening_oracle.v1",
    "source_artifact_sha256": matrix.artifact_sha256,
    "source_length": matrix.length,
    "source_dimension": matrix.dimension,
    "source_minimum_distance": source_minimum_distance,
    "examined_nonzero_source_messages": required,
    "derivation": (
        "shorten at j equals puncture of the source-code kernel of coordinate j"
    ),
    "members": members,
}
print(json.dumps({**core, "receipt_sha256": content_hash(core)}, sort_keys=True))
