"""Evidence-derived persistent component reservoirs for rendered worlds.

The learner sometimes encounters two observations that agree under its current
factor map but have different futures under the same intervention.  This module
offers one substrate-local refinement family: counts of translation-quotiented
equal-value components whose cardinality decreases across the counterexample
sequence.

The component shape and depletion order are invariant structure.  The concrete
cell value is retained separately as a presentation assignment so a palette
renaming can transport the learned coordinate without changing its structural
identity.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Hashable, Iterable, Sequence

from ztare.common.equivariance import stable_sha256


Grid = Sequence[Sequence[Hashable]]
Shape = tuple[tuple[int, int], ...]


def _rectangular(grid: Grid) -> tuple[int, int]:
    if isinstance(grid, (str, bytes, bytearray)):
        raise TypeError(
            "component reservoirs require a two-dimensional observation"
        )
    height = len(grid)
    width = len(grid[0]) if height else 0
    if not height or not width:
        raise ValueError("component reservoirs require a non-empty observation")
    if any(isinstance(row, (str, bytes, bytearray)) for row in grid):
        raise TypeError(
            "component reservoirs require row-valued observations"
        )
    if any(len(row) != width for row in grid):
        raise ValueError("component reservoirs require rectangular observations")
    return height, width


def translation_component_counts(
    observation: Grid,
    *,
    max_area: int = 64,
) -> Counter[tuple[Hashable, Shape]]:
    """Count 4-connected equal-value components modulo translation."""
    height, width = _rectangular(observation)
    area_cap = max(1, int(max_area))
    seen: set[tuple[int, int]] = set()
    counts: Counter[tuple[Hashable, Shape]] = Counter()
    for row in range(height):
        for col in range(width):
            if (row, col) in seen:
                continue
            value = observation[row][col]
            try:
                hash(value)
            except TypeError as exc:
                raise TypeError("observation values must be hashable") from exc
            pending = [(row, col)]
            seen.add((row, col))
            support: list[tuple[int, int]] = []
            while pending:
                current_row, current_col = pending.pop()
                support.append((current_row, current_col))
                for next_row, next_col in (
                    (current_row - 1, current_col),
                    (current_row + 1, current_col),
                    (current_row, current_col - 1),
                    (current_row, current_col + 1),
                ):
                    if (
                        0 <= next_row < height
                        and 0 <= next_col < width
                        and (next_row, next_col) not in seen
                        and observation[next_row][next_col] == value
                    ):
                        seen.add((next_row, next_col))
                        pending.append((next_row, next_col))
            if len(support) > area_cap:
                continue
            min_row = min(point[0] for point in support)
            min_col = min(point[1] for point in support)
            shape = tuple(sorted(
                (point_row - min_row, point_col - min_col)
                for point_row, point_col in support
            ))
            counts[(value, shape)] += 1
    return counts


@dataclass(frozen=True)
class ReservoirWitness:
    observation: Grid = field(compare=False, repr=False)
    outcome: Hashable
    evidence_ref: str
    sequence_id: str = ""
    sequence_index: int | None = None

    def __post_init__(self) -> None:
        if not str(self.evidence_ref).strip():
            raise ValueError("reservoir witnesses require evidence_ref")
        if bool(self.sequence_id) != (self.sequence_index is not None):
            raise ValueError(
                "reservoir sequence identity and position must be paired"
            )
        if self.sequence_index is not None and self.sequence_index < 0:
            raise ValueError("reservoir sequence position must be non-negative")
        try:
            hash(self.outcome)
        except TypeError as exc:
            raise TypeError("reservoir outcomes must be hashable") from exc


@dataclass(frozen=True)
class ComponentReservoirCoordinate:
    """One learned depletion coordinate and its presentation section."""

    normalized_shape: Shape
    active_presentation: Hashable = field(compare=False, repr=False)
    witness_counts: tuple[int, ...]
    exceptional_threshold: int
    evidence_refs: tuple[str, ...]
    max_area: int = 64
    schema: str = "ztare-component-reservoir-coordinate-v1"

    def project(self, observation: Grid) -> int:
        return int(
            translation_component_counts(
                observation,
                max_area=self.max_area,
            ).get(
                (self.active_presentation, self.normalized_shape),
                0,
            )
        )

    def predicts_exception(self, observation: Grid) -> bool:
        return self.project(observation) <= self.exceptional_threshold

    @property
    def structural_sha256(self) -> str:
        return stable_sha256({
            "schema": self.schema,
            "normalized_shape": self.normalized_shape,
            "direction": "nonincreasing",
            "max_area": self.max_area,
        })

    def to_receipt(self) -> dict[str, Any]:
        rows = [point[0] for point in self.normalized_shape]
        cols = [point[1] for point in self.normalized_shape]
        return {
            "schema": self.schema,
            "structural_sha256": self.structural_sha256,
            "normalized_shape": [list(point) for point in self.normalized_shape],
            "component_area": len(self.normalized_shape),
            "bounding_box": [
                1 + max(rows, default=0),
                1 + max(cols, default=0),
            ],
            "witness_counts": list(self.witness_counts),
            "distinct_context_count": len(set(self.witness_counts)),
            "exceptional_threshold": self.exceptional_threshold,
            "presentation_assignment_sha256": stable_sha256(
                self.active_presentation
            ),
            "evidence_refs": list(self.evidence_refs),
        }


def discover_component_reservoir_coordinate(
    witnesses: Iterable[ReservoirWitness],
    *,
    exceptional_outcome: Hashable,
    background_observations: Iterable[Grid] = (),
    max_area: int = 64,
) -> ComponentReservoirCoordinate | None:
    """Select the smallest non-injective monotone component coordinate.

    A candidate must make the witnessed outcome a function of component count,
    put every exceptional witness strictly below every ordinary witness, and
    decrease along evidence order.  Background observations enforce that the
    coordinate is a compression rather than a rendered-state identifier.
    """
    rows = tuple(witnesses)
    if len(rows) < 2:
        return None
    feature_rows = tuple(
        translation_component_counts(
            row.observation,
            max_area=max_area,
        )
        for row in rows
    )
    signatures = {
        signature
        for features in feature_rows
        for signature in features
    }
    background = tuple(background_observations)
    background_features = tuple(
        translation_component_counts(
            observation,
            max_area=max_area,
        )
        for observation in background
    )
    candidates: list[
        tuple[
            tuple[int, int, int, str],
            ComponentReservoirCoordinate,
        ]
    ] = []
    for active_presentation, shape in signatures:
        counts = tuple(
            int(features.get((active_presentation, shape), 0))
            for features in feature_rows
        )
        if len(set(counts)) < 2:
            continue
        sequenced_counts: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for count, row in zip(counts, rows):
            if row.sequence_id:
                sequenced_counts[row.sequence_id].append((
                    int(row.sequence_index),
                    count,
                ))
        if sequenced_counts:
            ordered_sequences = tuple(
                tuple(
                    count
                    for _index, count in sorted(sequence_rows)
                )
                for sequence_rows in sequenced_counts.values()
            )
            if not all(
                all(
                    left >= right
                    for left, right in zip(sequence, sequence[1:])
                )
                for sequence in ordered_sequences
            ):
                continue
            if not any(
                any(
                    left > right
                    for left, right in zip(sequence, sequence[1:])
                )
                for sequence in ordered_sequences
            ):
                continue
        elif (
            not all(left >= right for left, right in zip(counts, counts[1:]))
            or not any(left > right for left, right in zip(counts, counts[1:]))
        ):
            continue
        outcomes_by_count: dict[int, set[Hashable]] = defaultdict(set)
        for count, row in zip(counts, rows):
            outcomes_by_count[count].add(row.outcome)
        if any(len(outcomes) != 1 for outcomes in outcomes_by_count.values()):
            continue
        exceptional_counts = tuple(
            count
            for count, row in zip(counts, rows)
            if row.outcome == exceptional_outcome
        )
        ordinary_counts = tuple(
            count
            for count, row in zip(counts, rows)
            if row.outcome != exceptional_outcome
        )
        if (
            not exceptional_counts
            or not ordinary_counts
            or max(exceptional_counts) >= min(ordinary_counts)
        ):
            continue
        if background_features:
            background_counts = tuple(
                int(features.get((active_presentation, shape), 0))
                for features in background_features
            )
            if len(set(background_counts)) >= len(background_counts):
                continue
        coordinate = ComponentReservoirCoordinate(
            normalized_shape=shape,
            active_presentation=active_presentation,
            witness_counts=counts,
            exceptional_threshold=max(exceptional_counts),
            evidence_refs=tuple(row.evidence_ref for row in rows),
            max_area=max_area,
        )
        max_row = max(point[0] for point in shape)
        max_col = max(point[1] for point in shape)
        candidates.append((
            (
                len(shape),
                (max_row + 1) * (max_col + 1),
                len(set(counts)),
                coordinate.structural_sha256,
            ),
            coordinate,
        ))
    return min(candidates, key=lambda row: row[0])[1] if candidates else None


__all__ = [
    "ComponentReservoirCoordinate",
    "ReservoirWitness",
    "discover_component_reservoir_coordinate",
    "translation_component_counts",
]
