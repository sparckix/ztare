"""Independent exact oracle for the frozen length-51 puncture family.

This is a post-freeze referee, not a candidate producer.  It enumerates the
source code once and uses the support of minimum words to determine all 51
punctured distances exactly.
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


payload = json.loads(SOURCE.read_text(encoding="utf-8"))
matrix = BinaryGeneratorMatrix.from_json(payload["extended_matrix"])
required = (1 << matrix.dimension) - 1

best_weight = matrix.length + 1
minimum_support_union = 0
minimum_word_count = 0
first_covering_witness: list[dict[str, str] | None] = [None] * matrix.length
previous_gray = 0
word = 0

for step in range(1, required + 1):
    gray = step ^ (step >> 1)
    word ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
    weight = word.bit_count()
    if weight < best_weight:
        best_weight = weight
        minimum_support_union = 0
        minimum_word_count = 0
        first_covering_witness = [None] * matrix.length
    if weight == best_weight:
        minimum_word_count += 1
        minimum_support_union |= word
        for coordinate in range(matrix.length):
            if ((word >> coordinate) & 1) and first_covering_witness[coordinate] is None:
                first_covering_witness[coordinate] = {
                    "message_hex": f"0x{gray:05x}",
                    "source_codeword_hex": f"0x{word:013x}",
                    "punctured_codeword_hex": f"0x{puncture(word, coordinate):013x}",
                }
    previous_gray = gray

members = []
for coordinate in range(matrix.length):
    rank, dependency = gf2_rank_with_dependency(
        tuple(puncture(row, coordinate) for row in matrix.rows)
    )
    covered = bool((minimum_support_union >> coordinate) & 1)
    members.append(
        {
            "coordinate": coordinate,
            "rank": rank,
            "dependency_message_hex": (
                f"0x{dependency:05x}" if dependency is not None else None
            ),
            "minimum_distance": best_weight - 1 if covered else best_weight,
            "minimum_word_cover_witness": first_covering_witness[coordinate],
        }
    )

core = {
    "schema": "axiompack.binary_linear_puncture_oracle.v1",
    "source_artifact_sha256": matrix.artifact_sha256,
    "source_length": matrix.length,
    "source_dimension": matrix.dimension,
    "source_minimum_distance": best_weight,
    "examined_nonzero_messages": required,
    "minimum_word_count": minimum_word_count,
    "minimum_support_union_hex": f"0x{minimum_support_union:013x}",
    "all_coordinates_covered_by_minimum_words": (
        minimum_support_union == (1 << matrix.length) - 1
    ),
    "members": members,
}
print(json.dumps({**core, "receipt_sha256": content_hash(core)}, sort_keys=True))
