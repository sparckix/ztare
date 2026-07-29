#!/usr/bin/env python3
"""Audit Question 30 against Cedó--Okniński Theorem 4.2, first case.

The paper defines YBE left actions ``sigma_x``.  The corresponding cycle-set
left translations are ``sigma_x^{-1}``; inversion preserves cycle lengths.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
import argparse
import json
from math import gcd


SCHEMA = "leanmill.cedo_okninski_question30_construction_audit.v1"
SOURCE = "arXiv:2407.07907v1, Theorem 4.2"


Point = tuple[int, int]
Permutation = list[int]


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _compose(left: Permutation, right: Permutation) -> Permutation:
    """Return left after right."""

    return [left[right[index]] for index in range(len(left))]


def _inverse(permutation: Permutation) -> Permutation:
    inverse = [-1] * len(permutation)
    for source, target in enumerate(permutation):
        if not 0 <= target < len(permutation) or inverse[target] != -1:
            raise ValueError("not a permutation")
        inverse[target] = source
    return inverse


def _cycles(permutation: Permutation) -> list[list[int]]:
    seen: set[int] = set()
    result = []
    for start in range(len(permutation)):
        if start in seen:
            continue
        cycle = []
        current = start
        while current not in seen:
            seen.add(current)
            cycle.append(current)
            current = permutation[current]
        if current != start:
            raise ValueError("cycle traversal did not return to its start")
        result.append(cycle)
    return result


def _orbit_is_full(generators: list[Permutation]) -> bool:
    seen = {0}
    queue = deque([0])
    while queue:
        current = queue.popleft()
        for generator in generators:
            target = generator[current]
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return len(seen) == len(generators[0])


@dataclass(frozen=True)
class Construction:
    p: int = 7
    n: int = 1
    q: int = 3
    multiplier: int = 2

    @property
    def modulus(self) -> int:
        return self.p**self.n

    @property
    def points(self) -> list[Point]:
        return [
            (first, second)
            for first in range(self.modulus)
            for second in range(self.modulus)
        ]

    def index(self, point: Point) -> int:
        first, second = point
        return (first % self.modulus) * self.modulus + second % self.modulus

    def point(self, index: int) -> Point:
        return divmod(index, self.modulus)

    def t(self, value: int) -> int:
        return self.multiplier * value % self.modulus

    def j_family(self) -> list[int]:
        """Build the paper's family using paired T-orbit representatives."""

        modulus = self.modulus
        j: list[int | None] = [None] * modulus
        j[0] = 1
        remaining = set(range(1, modulus))
        while remaining:
            representative = min(remaining)
            orbit = []
            current = representative
            for _ in range(self.q):
                if current in orbit:
                    raise ValueError("T-orbit closed before q steps")
                orbit.append(current)
                current = self.t(current)
            if current != representative or len(set(orbit)) != self.q:
                raise ValueError("nonzero T-orbit does not have size q")
            negative_representative = -representative % modulus
            negative_orbit = []
            current = negative_representative
            for _ in range(self.q):
                negative_orbit.append(current)
                current = self.t(current)
            if set(orbit) == set(negative_orbit):
                raise ValueError("an orbit contains its negative")
            for exponent, value in enumerate(orbit):
                coefficient = pow(self.multiplier, exponent, modulus)
                j[value] = (1 - coefficient) % modulus
            for exponent, value in enumerate(negative_orbit):
                coefficient = pow(self.multiplier, exponent, modulus)
                j[value] = (1 - coefficient) % modulus
            remaining.difference_update(orbit)
            remaining.difference_update(negative_orbit)
        if any(value is None for value in j):
            raise ValueError("j family is incomplete")
        return [int(value) for value in j]

    def sigma(self, source: Point, j: list[int]) -> Permutation:
        a, b = source
        result = []
        for c, d in self.points:
            first = (self.t(c) + b) % self.modulus
            second = self.t((d - j[(first - a) % self.modulus]) % self.modulus)
            result.append(self.index((first, second)))
        _inverse(result)
        return result


def _verify_j(construction: Construction, j: list[int]) -> None:
    modulus = construction.modulus
    if j[0] != 1:
        raise ValueError("j_0 checksum failed")
    for value in range(modulus):
        if j[-value % modulus] != j[value]:
            raise ValueError("j_-a = j_a checksum failed")
        current = value
        coefficient = 1
        for _ in range(construction.q):
            left = (j[current] - j[0]) % modulus
            right = coefficient * (j[value] - j[0]) % modulus
            if left != right:
                raise ValueError("T-equivariance checksum failed")
            current = construction.t(current)
            coefficient = construction.t(coefficient)


def _verify_ybe_sigma_identity(sigmas: list[Permutation]) -> None:
    inverses = [_inverse(permutation) for permutation in sigmas]
    for x in range(len(sigmas)):
        for y in range(len(sigmas)):
            left = _compose(sigmas[x], sigmas[inverses[x][y]])
            right = _compose(sigmas[y], sigmas[inverses[y][x]])
            if left != right:
                raise ValueError(f"YBE sigma identity failed at ({x}, {y})")


def _verify_cycle_law(left_translations: list[Permutation]) -> None:
    size = len(left_translations)
    for x in range(size):
        for y in range(size):
            xy = left_translations[x][y]
            yx = left_translations[y][x]
            for z in range(size):
                left = left_translations[xy][left_translations[x][z]]
                right = left_translations[yx][left_translations[y][z]]
                if left != right:
                    raise ValueError(f"cycle law failed at ({x}, {y}, {z})")


def run_audit() -> dict[str, object]:
    construction = Construction()
    modulus = construction.modulus
    if pow(construction.multiplier, construction.q, modulus) != 1:
        raise ValueError("multiplier order does not divide q")
    if any(
        pow(construction.multiplier, exponent, modulus) == 1
        for exponent in range(1, construction.q)
    ):
        raise ValueError("multiplier order is smaller than q")
    if (construction.p - 1) % construction.q:
        raise ValueError("q does not divide p - 1")

    j = construction.j_family()
    _verify_j(construction, j)
    points = construction.points
    sigmas = [construction.sigma(point, j) for point in points]
    left_translations = [_inverse(permutation) for permutation in sigmas]
    squaring_map = [
        left_translations[index][index] for index in range(len(points))
    ]
    _inverse(squaring_map)
    _verify_ybe_sigma_identity(sigmas)
    _verify_cycle_law(left_translations)
    if not _orbit_is_full(sigmas):
        raise ValueError("left-action group is not transitive")

    inverse_base = _inverse(left_translations[0])
    displacement_generators = [
        _compose(translation, inverse_base)
        for translation in left_translations
    ]
    displacement_transitive = _orbit_is_full(displacement_generators)

    profile_counter: Counter[tuple[int, ...]] = Counter()
    coprime_witnesses = []
    for source_index, permutation in enumerate(left_translations):
        cycles = _cycles(permutation)
        profile = tuple(sorted(len(cycle) for cycle in cycles))
        profile_counter[profile] += 1
        for cycle in cycles:
            length = len(cycle)
            if length > 1 and gcd(length, len(points)) == 1:
                coprime_witnesses.append(
                    {
                        "source": list(points[source_index]),
                        "cycle_length": length,
                        "cycle": [list(points[index]) for index in cycle],
                    }
                )

    sigma_zero_cycles = _cycles(sigmas[0])
    core: dict[str, object] = {
        "schema": SCHEMA,
        "source": SOURCE,
        "parameters": {
            "p": construction.p,
            "n": construction.n,
            "q": construction.q,
            "modulus": modulus,
            "t_multiplier": construction.multiplier,
            "carrier_size": len(points),
        },
        "j_family": j,
        "checks": {
            "j_family_relations": "pass",
            "all_sigma_bijective": True,
            "paper_ybe_sigma_identity": "pass",
            "cycle_set_law_for_sigma_inverse": "pass",
            "squaring_map_bijective": True,
            "left_action_transitive": True,
            "displacement_action_transitive": displacement_transitive,
        },
        "translation_cycle_profile_distribution": [
            {
                "cycle_lengths": list(profile),
                "left_translation_count": count,
            }
            for profile, count in sorted(profile_counter.items())
        ],
        "sigma_zero_cycle_lengths": sorted(len(cycle) for cycle in sigma_zero_cycles),
        "coprime_cycle_witness_count": len(coprime_witnesses),
        "first_coprime_cycle_witness": (
            coprime_witnesses[0] if coprime_witnesses else None
        ),
        "result": (
            "published_construction_contains_question30_counterexample"
            if coprime_witnesses
            else "published_construction_does_not_decide_question30_in_first_case"
        ),
        "claim_boundary": (
            "deterministic audit of the p=7,n=1 instance of the published "
            "Theorem 4.2 construction; priority and whether the Question-30 "
            "corollary is already stated require a separate literature audit"
        ),
        "authority": "deterministic_reconstruction_of_published_formula",
    }
    return {**core, "receipt_sha256": _canonical_hash(core)}


def _self_test() -> None:
    construction = Construction()
    assert construction.j_family() == [1, 0, 6, 4, 4, 6, 0]
    three_cycle = [1, 2, 0]
    assert _inverse(three_cycle) == [2, 0, 1]
    assert _compose(three_cycle, _inverse(three_cycle)) == [0, 1, 2]
    assert [len(cycle) for cycle in _cycles(three_cycle)] == [3]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    _self_test()
    if args.self_test:
        print(json.dumps({"schema": SCHEMA, "self_test": "pass"}, sort_keys=True))
        return 0
    print(json.dumps(run_audit(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
