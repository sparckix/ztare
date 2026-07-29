"""Deterministic automorphism and necklace-quotient oracle for the frozen code.

The oracle enumerates the complete 20-dimensional source code, constructs a
colored coordinate graph from weight-14/16 incidence, enumerates every graph
automorphism by exact backtracking, and checks that the result is precisely
the displayed simultaneous QC shifts.  It performs no candidate search.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.leanmill.adapters.binary_linear_code import BinaryGeneratorMatrix
from ztare.leanmill.theory_ir import content_hash


ORACLE = Path(__file__).resolve()
HERE = ORACLE.parent
SOURCE = HERE.parent / (
    "axiompack_binary_linear_code_frontier_v1_20260717/"
    "binary_code_control_replay.json"
)


def compact_sha256(value: object) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def qc_shift(coordinate: int, amount: int) -> int:
    if coordinate == 50:
        return 50
    block, offset = divmod(coordinate, 10)
    return 10 * block + ((offset + amount) % 10)


def permute_word(word: int, permutation: tuple[int, ...]) -> int:
    result = 0
    for source, target in enumerate(permutation):
        if (word >> source) & 1:
            result |= 1 << target
    return result


payload = json.loads(SOURCE.read_text(encoding="utf-8"))
matrix = BinaryGeneratorMatrix.from_json(payload["extended_matrix"])
assert matrix.length == 51
assert matrix.dimension == 20
assert all(row.bit_count() % 2 == 0 for row in matrix.rows)

sigma = tuple(qc_shift(i, 1) for i in range(51))
expected_row_images = tuple(range(1, 10)) + (0,) + tuple(range(11, 20)) + (10,)
actual_row_images = tuple(
    matrix.rows.index(permute_word(row, sigma)) for row in matrix.rows
)
assert actual_row_images == expected_row_images

incidence = {14: [0] * 51, 16: [0] * 51}
pair_incidence = [[0] * 51 for _ in range(51)]
weight_counts = {14: 0, 16: 0}
previous_gray = 0
word = 0

for step in range(1, 1 << matrix.dimension):
    gray = step ^ (step >> 1)
    word ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
    previous_gray = gray
    word_weight = word.bit_count()
    if word_weight not in incidence:
        continue
    weight_counts[word_weight] += 1
    coordinates: list[int] = []
    remaining = word
    while remaining:
        coordinate = (remaining & -remaining).bit_length() - 1
        remaining &= remaining - 1
        coordinates.append(coordinate)
        incidence[word_weight][coordinate] += 1
    if word_weight == 14:
        for index, left in enumerate(coordinates):
            for right in coordinates[index + 1 :]:
                pair_incidence[left][right] += 1
                pair_incidence[right][left] += 1

colors = tuple(
    (incidence[14][coordinate], incidence[16][coordinate])
    for coordinate in range(51)
)
coordinates_by_color: dict[tuple[int, int], list[int]] = {}
for coordinate, color in enumerate(colors):
    coordinates_by_color.setdefault(color, []).append(coordinate)

# Every exact graph automorphism is enumerated.  At each node choose the
# unmapped coordinate with the smallest color/edge-consistent target set.
assigned: dict[int, int] = {}
used_targets: set[int] = set()
automorphisms: list[tuple[int, ...]] = []
backtracking_nodes = 0


def candidates(source: int) -> list[int]:
    return [
        target
        for target in coordinates_by_color[colors[source]]
        if target not in used_targets
        and all(
            pair_incidence[source][old_source]
            == pair_incidence[target][old_target]
            for old_source, old_target in assigned.items()
        )
    ]


def enumerate_automorphisms() -> None:
    global backtracking_nodes
    backtracking_nodes += 1
    if len(assigned) == 51:
        automorphisms.append(tuple(assigned[i] for i in range(51)))
        return
    options: list[tuple[int, int, list[int]]] = []
    for source in range(51):
        if source in assigned:
            continue
        target_options = candidates(source)
        if not target_options:
            return
        options.append((len(target_options), source, target_options))
    _, source, target_options = min(options, key=lambda item: (item[0], item[1]))
    for target in target_options:
        assigned[source] = target
        used_targets.add(target)
        enumerate_automorphisms()
        used_targets.remove(target)
        del assigned[source]


enumerate_automorphisms()
automorphisms.sort()
expected_automorphisms = sorted(
    tuple(qc_shift(i, amount) for i in range(51)) for amount in range(10)
)
assert automorphisms == expected_automorphisms

upper_triangle = [
    pair_incidence[left][right]
    for left in range(51)
    for right in range(left + 1, 51)
]

period_one_words = 8
period_two_words = 8**2 - period_one_words
period_five_words = 8**5 - period_one_words
period_ten_words = 8**10 - period_one_words - period_two_words - period_five_words
necklace_orbits_by_size = {
    "1": period_one_words,
    "2": period_two_words // 2,
    "5": period_five_words // 5,
    "10": period_ten_words // 10,
}
necklace_orbit_count = sum(necklace_orbits_by_size.values())
assert necklace_orbit_count == (
    8**10 + 4 * 8 + 4 * 8**2 + 8**5
) // 10

core = {
    "schema": "axiompack.qc_automorphism_even_supercode_oracle.v1",
    "oracle_source_sha256": hashlib.sha256(ORACLE.read_bytes()).hexdigest(),
    "deterministic_replay_command": (
        "env PYTHONPATH=src ./venv/bin/python "
        "research_areas/pre_registrations/"
        "axiompack_binary_linear_code_structured_successor_v2_20260719/"
        "qc_automorphism_even_supercode_oracle.py"
    ),
    "runtime_assumptions": {
        "python": "CPython >= 3.11 with arbitrary-precision integer semantics",
        "external_graph_packages": "none; exact backtracking is implemented here",
        "json_encoding": "UTF-8, sorted keys, compact separators for hashed values",
        "candidate_order": (
            "minimum feasible target count, then ascending source and target"
        ),
        "binary_matrix_schema": "leanmill.binary_linear_generator_matrix.v1",
    },
    "source_ref": str(SOURCE.relative_to(HERE.parent)),
    "source_artifact_sha256": matrix.artifact_sha256,
    "complete_nonzero_messages_examined": (1 << matrix.dimension) - 1,
    "weight_counts": {str(key): value for key, value in weight_counts.items()},
    "coordinate_color_definition": ["weight_14_incidence", "weight_16_incidence"],
    "coordinate_color_classes": [
        {
            "coordinates": members,
            "color": list(color),
        }
        for color, members in sorted(
            coordinates_by_color.items(), key=lambda item: item[1][0]
        )
    ],
    "pair_incidence_definition": "weight_14_words_containing_both_coordinates",
    "pair_incidence_upper_triangle_encoding": "compact_json_lexicographic_pairs",
    "pair_incidence_upper_triangle_sha256": compact_sha256(upper_triangle),
    "qc_shift_permutation": list(sigma),
    "qc_shift_row_images": list(actual_row_images),
    "graph_automorphism_count": len(automorphisms),
    "graph_backtracking_nodes": backtracking_nodes,
    "graph_automorphisms": [list(permutation) for permutation in automorphisms],
    "graph_automorphisms_sha256": compact_sha256(automorphisms),
    "coordinate_orbits": [
        list(range(0, 10)),
        list(range(10, 20)),
        list(range(20, 30)),
        list(range(30, 40)),
        list(range(40, 50)),
        [50],
    ],
    "puncture_coordinate_equivalence_classes": 6,
    "even_supercode_quotient_dimension": 30,
    "necklace_alphabet_size": 8,
    "necklace_length": 10,
    "necklace_orbits_by_exact_size": necklace_orbits_by_size,
    "necklace_orbit_count": necklace_orbit_count,
    "claim_boundary": (
        "exact automorphism and symmetry-quotient computation for the frozen source; "
        "no construction witness and no quotient exhaustion"
    ),
}

print(
    json.dumps(
        {**core, "receipt_sha256": content_hash(core)},
        indent=2,
        sort_keys=True,
    )
)
