"""Exact referee for the selected 125-member quasicyclic graph family."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from itertools import product
import json

from ztare.leanmill.adapters.binary_linear_code import (
    BinaryGeneratorMatrix,
    verify_binary_linear_code,
)
from ztare.leanmill.theory_ir import content_hash


BLOCK_LENGTH = 25
MASK25 = (1 << BLOCK_LENGTH) - 1
G = (1 << 0) | (1 << 5)
FIXED_MESSAGE = (1 << 0) | (1 << 10)


def rotate25(value: int, amount: int) -> int:
    shift = amount % BLOCK_LENGTH
    if shift == 0:
        return value & MASK25
    return ((value << shift) | (value >> (BLOCK_LENGTH - shift))) & MASK25


def multiply_mod_x25_minus_one(left: int, right: int) -> int:
    result = 0
    remaining = left
    while remaining:
        low_bit = remaining & -remaining
        result ^= rotate25(right, low_bit.bit_length() - 1)
        remaining ^= low_bit
    return result


def phase_mask(phi: tuple[int, ...]) -> int:
    result = 0
    for residue, phase in enumerate(phi):
        result ^= 1 << (residue + 5 * phase)
        result ^= 1 << (residue + 5 * ((phase + 2) % 5))
    return result


def canonical_shift_orbit(value: int) -> tuple[int, tuple[int, ...]]:
    orbit = tuple(sorted({rotate25(value, shift) for shift in range(25)}))
    return orbit[0], orbit


def graph_matrix(canonical_a: int) -> BinaryGeneratorMatrix:
    second_seed = multiply_mod_x25_minus_one(G, canonical_a)
    rows = tuple(
        rotate25(G, index) | (rotate25(second_seed, index) << BLOCK_LENGTH)
        for index in range(20)
    )
    return BinaryGeneratorMatrix(length=50, dimension=20, rows=rows)


def verify_member(canonical_a: int) -> dict:
    matrix = graph_matrix(canonical_a)
    fixed_word = 0
    for index, row in enumerate(matrix.rows):
        if (FIXED_MESSAGE >> index) & 1:
            fixed_word ^= row
    if fixed_word.bit_count() != 14:
        raise AssertionError("universal weight-14 word failed")
    verification = verify_binary_linear_code(
        matrix,
        required_rank=20,
        required_minimum_distance=14,
        max_nonzero_messages=(1 << 20) - 1,
    )
    if verification["observed_rank"] != 20:
        raise AssertionError("graph-family member lost rank")
    distance = verification["distance_replay"]
    if distance["status"] != "exact" or (
        distance["examined_nonzero_messages"] != (1 << 20) - 1
    ):
        raise AssertionError("graph-family verifier did not exhaust the row span")
    if int(distance["minimum_distance"]) > 14:
        raise AssertionError("exact replay contradicted the universal word")
    core = {
        "schema": "axiompack.qc_graph_family_member_result.v1",
        "parameter_id": f"a25:0x{canonical_a:07x}",
        "canonical_multiplier_hex": f"0x{canonical_a:07x}",
        "artifact": matrix.to_json(),
        "artifact_sha256": matrix.artifact_sha256,
        "universal_message_hex": f"0x{FIXED_MESSAGE:05x}",
        "universal_codeword_hex": f"0x{fixed_word:013x}",
        "universal_codeword_weight": fixed_word.bit_count(),
        "verification": verification,
        "status": (
            "witness_found"
            if verification["status"] == "satisfied"
            else "low_weight_counterexample"
        ),
        "authority": "binary_adapter_exact_referee",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def main() -> None:
    representatives: dict[int, set[tuple[int, ...]]] = {}
    orbit_by_representative: dict[int, tuple[int, ...]] = {}
    for raw in product(range(5), repeat=5):
        phi = tuple(raw)
        canonical, orbit = canonical_shift_orbit(phase_mask(phi))
        representatives.setdefault(canonical, set()).add(phi)
        prior = orbit_by_representative.setdefault(canonical, orbit)
        if prior != orbit:
            raise AssertionError("canonical shift orbit changed identity")

    parameter_masks = sorted(representatives)
    orbit_sizes = [len(orbit_by_representative[row]) for row in parameter_masks]
    multiplicities = [len(representatives[row]) for row in parameter_masks]
    if (
        len(parameter_masks) != 125
        or set(orbit_sizes) != {25}
        or set(multiplicities) != {25}
        or sum(multiplicities) != 5**5
    ):
        raise AssertionError("quasicyclic quotient did not cover its exact domain")

    try:
        with ProcessPoolExecutor(max_workers=4) as pool:
            members = list(pool.map(verify_member, parameter_masks))
    except (OSError, PermissionError):
        members = [verify_member(value) for value in parameter_masks]

    witnesses = [
        {
            "parameter_id": row["parameter_id"],
            "artifact": row["artifact"],
            "artifact_sha256": row["artifact_sha256"],
            "verification_receipt_sha256": row["verification"]["receipt_sha256"],
        }
        for row in members
        if row["status"] == "witness_found"
    ]
    core = {
        "schema": "axiompack.qc_graph_family_oracle.v1",
        "family_id": "qc-graph-g-1-plus-x5-two-separated-phases",
        "parameter_ids": [f"a25:0x{value:07x}" for value in parameter_masks],
        "parameter_domain_sha256": content_hash(parameter_masks),
        "raw_phase_tuple_count": 5**5,
        "canonical_parameter_count": len(parameter_masks),
        "orbit_size_histogram": {"25": len(parameter_masks)},
        "raw_tuple_multiplicity_histogram": {"25": len(parameter_masks)},
        "members": members,
        "witnesses": witnesses,
        "status": "witness_found" if witnesses else "family_exhausted",
        "claim_scope": "exact_125_member_family_only_no_ambient_nonexistence",
        "global_nonexistence_authority": False,
        "kernel_ratification_authority": False,
        "authority": "independent_family_referee_using_binary_adapter",
    }
    print(json.dumps({**core, "receipt_sha256": content_hash(core)}, sort_keys=True))


if __name__ == "__main__":
    main()
