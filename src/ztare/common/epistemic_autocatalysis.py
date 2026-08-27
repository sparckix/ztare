"""Rank-quotiented residual fission and multiplexed temporal settlement.

The module separates cheap counterfactual expansion from promoted knowledge.
Raw residual candidates are quotiented by response direction, compressed to an
exact independent basis, and bound to a minimum-cost observation-axis basis.
Fresh micro-randomized trajectories then settle every basis child at a distinct
decision index.  Trajectory cost is counted once even when the same trajectory
settles several children.

This is a criticality measurement kernel.  It does not generate candidates,
infer substrate semantics, or promote a capability-takeoff claim from a single
generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import itertools
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-epistemic-autocatalysis-v1"


def _nonempty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _finite(value: object, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _nonnegative(value: object, name: str) -> float:
    result = _finite(value, name)
    if result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _probability(value: object, name: str) -> float:
    result = _finite(value, name)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return result


def _canonical(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({_nonempty(value, "identity") for value in values}))


def _ordered(values: Iterable[object], name: str) -> tuple[str, ...]:
    rows = tuple(_nonempty(value, name) for value in values)
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} repeat an identity")
    return rows


def _json_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def stable_sha256(value: Any) -> str:
    encoded = json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fraction(value: object) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("response signature entries cannot be Boolean")
    return value if isinstance(value, Fraction) else Fraction(value)


def _rank(rows: Sequence[Sequence[Fraction]]) -> int:
    matrix = [list(map(_fraction, row)) for row in rows]
    if not matrix:
        return 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("matrix rows have different widths")
    pivot_row = 0
    for column in range(width):
        pivot = next(
            (
                index
                for index in range(pivot_row, len(matrix))
                if matrix[index][column] != 0
            ),
            None,
        )
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = (
            matrix[pivot],
            matrix[pivot_row],
        )
        scale = matrix[pivot_row][column]
        matrix[pivot_row] = [value / scale for value in matrix[pivot_row]]
        for index in range(len(matrix)):
            if index == pivot_row:
                continue
            coefficient = matrix[index][column]
            if coefficient:
                matrix[index] = [
                    left - coefficient * right
                    for left, right in zip(
                        matrix[index],
                        matrix[pivot_row],
                    )
                ]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row


def _direction_key(
    signature: Sequence[Fraction],
) -> tuple[Fraction, ...]:
    frozen = tuple(map(_fraction, signature))
    first = next((value for value in frozen if value), None)
    if first is None:
        raise ValueError("residual response signature cannot be zero")
    magnitude = abs(first)
    return tuple(value / magnitude for value in frozen)


@dataclass(frozen=True)
class ResponseFissionAuthority:
    """Identity that every residual child must inherit unchanged."""

    scope: MemoryScope
    catalog_sha256: str
    source_program_sha256: str
    derivative_sha256: str
    intervention_revision_sha256: str
    primitive_cost_unit: str

    def __post_init__(self) -> None:
        for name in (
            "catalog_sha256",
            "source_program_sha256",
            "derivative_sha256",
            "intervention_revision_sha256",
            "primitive_cost_unit",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "response_fission_authority",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "catalog_sha256": self.catalog_sha256,
            "source_program_sha256": self.source_program_sha256,
            "derivative_sha256": self.derivative_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "primitive_cost_unit": self.primitive_cost_unit,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class MeasurementAxis:
    axis_id: str
    live_cost: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_id", _nonempty(self.axis_id, "axis_id"))
        object.__setattr__(
            self,
            "live_cost",
            _nonnegative(self.live_cost, "live_cost"),
        )

    def to_receipt(self) -> dict[str, Any]:
        return {"axis_id": self.axis_id, "live_cost": self.live_cost}


@dataclass(frozen=True)
class ResidualNicheCandidate:
    """One pre-outcome response question produced by offline replay."""

    authority: ResponseFissionAuthority
    niche_ref: str
    response_signature: tuple[Fraction, ...]
    predicted_information_yield: float
    offline_replay_cost: float
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    parent_child_sha256s: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "niche_ref",
            _nonempty(self.niche_ref, "niche_ref"),
        )
        signature = tuple(map(_fraction, self.response_signature))
        _direction_key(signature)
        object.__setattr__(self, "response_signature", signature)
        object.__setattr__(
            self,
            "predicted_information_yield",
            _probability(
                self.predicted_information_yield,
                "predicted_information_yield",
            ),
        )
        object.__setattr__(
            self,
            "offline_replay_cost",
            _nonnegative(self.offline_replay_cost, "offline_replay_cost"),
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("residual niche requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)
        object.__setattr__(
            self,
            "parent_child_sha256s",
            _canonical(self.parent_child_sha256s),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_niche_candidate",
            "authority_sha256": self.authority.sha256,
            "niche_ref": self.niche_ref,
            "response_signature": _json_value(self.response_signature),
            "response_direction": _json_value(
                _direction_key(self.response_signature)
            ),
            "predicted_information_yield": (
                self.predicted_information_yield
            ),
            "offline_replay_cost": self.offline_replay_cost,
            "evidence_refs": list(self.evidence_refs),
            "parent_child_sha256s": list(self.parent_child_sha256s),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ResidualFissionReceipt:
    authority: ResponseFissionAuthority
    axes: tuple[MeasurementAxis, ...]
    raw_niche_sha256s: tuple[str, ...]
    direction_quotient_classes: tuple[tuple[str, ...], ...]
    basis_niches: tuple[ResidualNicheCandidate, ...]
    pivot_axis_by_niche: tuple[tuple[str, str], ...]
    selected_measurement_axis_ids: tuple[str, ...]
    selected_live_measurement_cost: float

    @property
    def raw_proposal_reproduction(self) -> float:
        return float(len(self.raw_niche_sha256s))

    @property
    def independent_offspring_capacity(self) -> int:
        return len(self.basis_niches)

    @property
    def compression_ratio(self) -> float:
        return len(self.raw_niche_sha256s) / len(self.basis_niches)

    @property
    def lineage_parent_sha256s(self) -> tuple[str, ...]:
        parent_sets = {
            row.parent_child_sha256s for row in self.basis_niches
        }
        if len(parent_sets) != 1:
            raise ValueError("residual basis crossed lineage-parent authority")
        return next(iter(parent_sets))

    def pivot_axis(self, niche_ref: str) -> str:
        matches = [
            axis_id
            for candidate, axis_id in self.pivot_axis_by_niche
            if candidate == str(niche_ref)
        ]
        if len(matches) != 1:
            raise KeyError(f"niche has no unique pivot axis: {niche_ref}")
        return matches[0]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_fission_receipt",
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "axes": [axis.to_receipt() for axis in self.axes],
            "raw_niche_sha256s": list(self.raw_niche_sha256s),
            "raw_niche_count": len(self.raw_niche_sha256s),
            "direction_quotient_classes": [
                list(row) for row in self.direction_quotient_classes
            ],
            "direction_quotient_count": len(
                self.direction_quotient_classes
            ),
            "basis_niches": [row.to_receipt() for row in self.basis_niches],
            "independent_offspring_capacity": (
                self.independent_offspring_capacity
            ),
            "raw_proposal_reproduction": self.raw_proposal_reproduction,
            "compression_ratio": self.compression_ratio,
            "pivot_axis_by_niche": [
                {"niche_ref": niche_ref, "axis_id": axis_id}
                for niche_ref, axis_id in self.pivot_axis_by_niche
            ],
            "selected_measurement_axis_ids": list(
                self.selected_measurement_axis_ids
            ),
            "selected_live_measurement_cost": (
                self.selected_live_measurement_cost
            ),
            "lineage_parent_sha256s": list(
                self.lineage_parent_sha256s
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _perfect_nonzero_matching(
    rows: Sequence[Sequence[Fraction]],
    columns: Sequence[int],
) -> dict[int, int]:
    matched_row_by_column: dict[int, int] = {}

    def assign(row_index: int, seen: set[int]) -> bool:
        for column in columns:
            if column in seen or rows[row_index][column] == 0:
                continue
            seen.add(column)
            incumbent = matched_row_by_column.get(column)
            if incumbent is None or assign(incumbent, seen):
                matched_row_by_column[column] = row_index
                return True
        return False

    for row_index in range(len(rows)):
        if not assign(row_index, set()):
            raise ValueError("selected axes cannot bind every residual niche")
    return {
        row_index: column
        for column, row_index in matched_row_by_column.items()
    }


def compile_residual_fission(
    candidates: Sequence[ResidualNicheCandidate],
    *,
    axes: Sequence[MeasurementAxis],
) -> ResidualFissionReceipt:
    """Invert raw descendants, quotient copies, and keep exact rank only."""

    rows = tuple(candidates)
    axis_rows = tuple(axes)
    if not rows:
        raise ValueError("residual fission requires candidates")
    if not axis_rows:
        raise ValueError("residual fission requires measurement axes")
    if len({axis.axis_id for axis in axis_rows}) != len(axis_rows):
        raise ValueError("measurement axes repeat an identity")
    authority = rows[0].authority
    if any(row.authority != authority for row in rows):
        raise ValueError("residual candidates crossed response authority")
    if len({row.niche_ref for row in rows}) != len(rows):
        raise ValueError("residual candidates repeat a niche ref")
    if len({row.parent_child_sha256s for row in rows}) != 1:
        raise ValueError("residual candidates crossed lineage-parent authority")
    width = len(axis_rows)
    if any(len(row.response_signature) != width for row in rows):
        raise ValueError("residual signature crossed measurement-axis arity")

    classes: dict[tuple[Fraction, ...], list[ResidualNicheCandidate]] = {}
    for row in rows:
        classes.setdefault(
            _direction_key(row.response_signature),
            [],
        ).append(row)
    representatives = []
    quotient_classes = []
    for _key, group in sorted(classes.items(), key=lambda item: str(item[0])):
        ordered = sorted(
            group,
            key=lambda row: (
                -row.predicted_information_yield,
                row.offline_replay_cost,
                row.niche_ref,
            ),
        )
        representatives.append(ordered[0])
        quotient_classes.append(tuple(sorted(row.sha256 for row in group)))

    candidate_order = sorted(
        representatives,
        key=lambda row: (
            -(
                row.predicted_information_yield
                / (1.0 + row.offline_replay_cost)
            ),
            row.niche_ref,
        ),
    )
    basis: list[ResidualNicheCandidate] = []
    basis_matrix: list[tuple[Fraction, ...]] = []
    for row in candidate_order:
        proposed = [*basis_matrix, row.response_signature]
        if _rank(proposed) > len(basis_matrix):
            basis.append(row)
            basis_matrix.append(row.response_signature)
    if not basis:
        raise ValueError("residual fission produced no independent niche")

    selected_columns: list[int] = []
    for column in sorted(
        range(width),
        key=lambda index: (axis_rows[index].live_cost, axis_rows[index].axis_id),
    ):
        proposed = [*selected_columns, column]
        submatrix = [
            tuple(row[index] for index in proposed)
            for row in basis_matrix
        ]
        if _rank(submatrix) > len(selected_columns):
            selected_columns.append(column)
        if len(selected_columns) == len(basis):
            break
    if len(selected_columns) != len(basis):
        raise ValueError("measurement surface cannot settle residual basis")
    matching = _perfect_nonzero_matching(basis_matrix, selected_columns)
    pivot_axis_by_niche = tuple(sorted(
        (
            basis[row_index].niche_ref,
            axis_rows[column].axis_id,
        )
        for row_index, column in matching.items()
    ))
    selected_axis_ids = tuple(
        axis_rows[index].axis_id for index in selected_columns
    )
    return ResidualFissionReceipt(
        authority=authority,
        axes=axis_rows,
        raw_niche_sha256s=tuple(sorted(row.sha256 for row in rows)),
        direction_quotient_classes=tuple(sorted(quotient_classes)),
        basis_niches=tuple(basis),
        pivot_axis_by_niche=pivot_axis_by_niche,
        selected_measurement_axis_ids=selected_axis_ids,
        selected_live_measurement_cost=sum(
            axis_rows[index].live_cost for index in selected_columns
        ),
    )


def _walsh_sign(row_index: int, mask: int) -> int:
    if row_index < 0 or mask <= 0:
        raise ValueError("Walsh row and mask must be positive coordinates")
    return 1 if (row_index & mask).bit_count() % 2 == 0 else -1


@dataclass(frozen=True)
class SparseSettlementSchedule:
    """Pre-outcome Walsh code for main effects and named interactions."""

    fission_sha256: str
    niche_refs: tuple[str, ...]
    modeled_interactions: tuple[tuple[str, ...], ...]
    factor_masks: tuple[tuple[str, int], ...]
    term_masks: tuple[tuple[tuple[str, ...], int], ...]
    assignment_patterns: tuple[tuple[int, ...], ...]
    model_rank: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fission_sha256",
            _nonempty(self.fission_sha256, "fission_sha256"),
        )
        niches = _ordered(self.niche_refs, "niche_refs")
        if niches != tuple(sorted(niches)):
            raise ValueError("sparse settlement niches are not canonical")
        object.__setattr__(self, "niche_refs", niches)
        interactions = _interaction_terms(
            niches,
            self.modeled_interactions,
        )
        object.__setattr__(self, "modeled_interactions", interactions)
        factors = tuple(self.factor_masks)
        if tuple(row[0] for row in factors) != niches:
            raise ValueError("factor masks crossed niche identity")
        masks = tuple(row[1] for row in factors)
        if (
            any(isinstance(mask, bool) or mask <= 0 for mask in masks)
            or len(set(masks)) != len(masks)
        ):
            raise ValueError("factor masks must be distinct and nonzero")
        mask_by_niche = dict(factors)
        terms = (*tuple((niche,) for niche in niches), *interactions)
        expected_term_masks = tuple(
            (term, _term_mask(term, mask_by_niche)) for term in terms
        )
        if self.term_masks != expected_term_masks:
            raise ValueError("modeled term masks crossed factor authority")
        term_mask_values = tuple(mask for _term, mask in self.term_masks)
        if (
            any(mask <= 0 for mask in term_mask_values)
            or len(set(term_mask_values)) != len(term_mask_values)
        ):
            raise ValueError("Walsh settlement terms alias")
        patterns = tuple(tuple(row) for row in self.assignment_patterns)
        if not patterns or len(patterns) & (len(patterns) - 1):
            raise ValueError("Walsh schedule row count must be a power of two")
        expected_patterns = tuple(
            tuple(_walsh_sign(row_index, mask) for mask in masks)
            for row_index in range(len(patterns))
        )
        if patterns != expected_patterns:
            raise ValueError("assignment patterns crossed Walsh factor masks")
        object.__setattr__(self, "assignment_patterns", patterns)
        design = tuple(
            (
                Fraction(1),
                *tuple(
                    Fraction(_walsh_sign(row_index, mask))
                    for mask in term_mask_values
                ),
            )
            for row_index in range(len(patterns))
        )
        exact_rank = _rank(design)
        if self.model_rank != exact_rank or exact_rank != len(terms) + 1:
            raise ValueError("Walsh settlement design is rank deficient")

    @property
    def trajectory_count(self) -> int:
        return len(self.assignment_patterns)

    @property
    def modeled_term_count(self) -> int:
        return len(self.term_masks)

    @property
    def full_factorial_trajectory_count(self) -> int:
        return 2 ** len(self.niche_refs)

    @property
    def trajectory_compression_ratio(self) -> float:
        return self.full_factorial_trajectory_count / self.trajectory_count

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "sparse_settlement_schedule",
            "fission_sha256": self.fission_sha256,
            "niche_refs": list(self.niche_refs),
            "modeled_interactions": [
                list(row) for row in self.modeled_interactions
            ],
            "factor_masks": [
                {"niche_ref": niche_ref, "mask": mask}
                for niche_ref, mask in self.factor_masks
            ],
            "term_masks": [
                {"term": list(term), "mask": mask}
                for term, mask in self.term_masks
            ],
            "assignment_patterns": [
                list(row) for row in self.assignment_patterns
            ],
            "trajectory_count": self.trajectory_count,
            "modeled_term_count": self.modeled_term_count,
            "model_rank": self.model_rank,
            "full_factorial_trajectory_count": (
                self.full_factorial_trajectory_count
            ),
            "trajectory_compression_ratio": (
                self.trajectory_compression_ratio
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _next_power_of_two(value: int) -> int:
    if value <= 0:
        raise ValueError("power-of-two envelope requires a positive value")
    return 1 << (value - 1).bit_length()


def _interaction_terms(
    niche_refs: Sequence[str],
    modeled_interactions: Sequence[Sequence[str]],
) -> tuple[tuple[str, ...], ...]:
    niche_set = set(niche_refs)
    rows = []
    for interaction in modeled_interactions:
        term = _canonical(interaction)
        if len(term) < 2:
            raise ValueError("modeled interaction needs at least two niches")
        if not set(term).issubset(niche_set):
            raise ValueError("modeled interaction crossed residual basis")
        rows.append(term)
    result = tuple(sorted(set(rows)))
    if len(result) != len(rows):
        raise ValueError("modeled interactions repeat a term")
    return result


def _term_mask(
    term: Sequence[str],
    mask_by_niche: Mapping[str, int],
) -> int:
    result = 0
    for niche_ref in term:
        result ^= mask_by_niche[niche_ref]
    return result


def _collision_free_factor_masks(
    niche_refs: tuple[str, ...],
    interactions: tuple[tuple[str, ...], ...],
) -> tuple[int, tuple[int, ...]]:
    term_count = len(niche_refs) + len(interactions)
    row_count = _next_power_of_two(term_count + 1)
    if not interactions:
        return row_count, tuple(range(1, len(niche_refs) + 1))
    if len(niche_refs) > 8:
        raise ValueError(
            "interaction-bearing Walsh search is bounded to eight niches"
        )
    while row_count <= 4096:
        examined = 0
        for masks in itertools.combinations(
            range(1, row_count),
            len(niche_refs),
        ):
            examined += 1
            if examined > 500_000:
                break
            mask_by_niche = dict(zip(niche_refs, masks))
            term_masks = [*masks]
            term_masks.extend(
                _term_mask(term, mask_by_niche) for term in interactions
            )
            if (
                all(mask > 0 for mask in term_masks)
                and len(set(term_masks)) == len(term_masks)
            ):
                return row_count, tuple(masks)
        row_count *= 2
    raise ValueError("no bounded collision-free Walsh settlement code")


def compile_sparse_settlement_schedule(
    fission: ResidualFissionReceipt,
    *,
    modeled_interactions: Sequence[Sequence[str]] = (),
) -> SparseSettlementSchedule:
    """Compile the smallest bounded Walsh code for the declared effect model."""

    niche_refs = tuple(sorted(row.niche_ref for row in fission.basis_niches))
    interactions = _interaction_terms(niche_refs, modeled_interactions)
    row_count, masks = _collision_free_factor_masks(
        niche_refs,
        interactions,
    )
    mask_by_niche = dict(zip(niche_refs, masks))
    main_terms = tuple((niche_ref,) for niche_ref in niche_refs)
    terms = (*main_terms, *interactions)
    term_masks = tuple(
        (term, _term_mask(term, mask_by_niche)) for term in terms
    )
    if (
        any(mask <= 0 for _term, mask in term_masks)
        or len({mask for _term, mask in term_masks}) != len(term_masks)
    ):
        raise ValueError("Walsh settlement terms alias")
    patterns = tuple(
        tuple(_walsh_sign(row_index, mask) for mask in masks)
        for row_index in range(row_count)
    )
    design = tuple(
        (
            Fraction(1),
            *tuple(
                Fraction(_walsh_sign(row_index, mask))
                for _term, mask in term_masks
            ),
        )
        for row_index in range(row_count)
    )
    model_rank = _rank(design)
    if model_rank != len(term_masks) + 1:
        raise ValueError("Walsh settlement design is rank deficient")
    return SparseSettlementSchedule(
        fission_sha256=fission.sha256,
        niche_refs=niche_refs,
        modeled_interactions=interactions,
        factor_masks=tuple(zip(niche_refs, masks)),
        term_masks=term_masks,
        assignment_patterns=patterns,
        model_rank=model_rank,
    )


@dataclass(frozen=True)
class ResidualSettlementTrial:
    """One niche-local eligibility trace inside a shared live trajectory."""

    fission_sha256: str
    trajectory_ref: str
    niche_ref: str
    decision_index: int
    assignment: str
    supported_transport: bool
    contradicted: bool
    pivot_axis_id: str
    local_external_value: float
    observed_information_yield: float
    trajectory_primitive_action_cost: float
    settlement_observation_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "fission_sha256",
            "trajectory_ref",
            "niche_ref",
            "pivot_axis_id",
            "settlement_observation_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if isinstance(self.decision_index, bool) or self.decision_index < 0:
            raise ValueError("decision_index must be a nonnegative integer")
        if self.assignment not in {"offer", "withhold"}:
            raise ValueError("assignment must be offer or withhold")
        object.__setattr__(
            self,
            "local_external_value",
            _finite(self.local_external_value, "local_external_value"),
        )
        object.__setattr__(
            self,
            "observed_information_yield",
            _probability(
                self.observed_information_yield,
                "observed_information_yield",
            ),
        )
        object.__setattr__(
            self,
            "trajectory_primitive_action_cost",
            _nonnegative(
                self.trajectory_primitive_action_cost,
                "trajectory_primitive_action_cost",
            ),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_settlement_trial",
            "fission_sha256": self.fission_sha256,
            "trajectory_ref": self.trajectory_ref,
            "niche_ref": self.niche_ref,
            "decision_index": self.decision_index,
            "assignment": self.assignment,
            "supported_transport": self.supported_transport,
            "contradicted": self.contradicted,
            "pivot_axis_id": self.pivot_axis_id,
            "local_external_value": self.local_external_value,
            "observed_information_yield": (
                self.observed_information_yield
            ),
            "trajectory_primitive_action_cost": (
                self.trajectory_primitive_action_cost
            ),
            "settlement_observation_sha256": (
                self.settlement_observation_sha256
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ResidualChildSettlement:
    niche_ref: str
    pivot_axis_id: str
    status: str
    offer_count: int
    withhold_count: int
    offer_supported_rate: float
    withhold_supported_rate: float
    first_stage_delta: float
    local_value_delta: float
    observed_information_yield_delta: float
    predicted_information_yield: float
    calibration_error: float
    false_edge: bool
    trial_sha256s: tuple[str, ...]
    settlement_observation_sha256s: tuple[str, ...]

    @property
    def promoted(self) -> bool:
        return self.status == "promoted"

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_child_settlement",
            "niche_ref": self.niche_ref,
            "pivot_axis_id": self.pivot_axis_id,
            "status": self.status,
            "offer_count": self.offer_count,
            "withhold_count": self.withhold_count,
            "offer_supported_rate": self.offer_supported_rate,
            "withhold_supported_rate": self.withhold_supported_rate,
            "first_stage_delta": self.first_stage_delta,
            "local_value_delta": self.local_value_delta,
            "observed_information_yield_delta": (
                self.observed_information_yield_delta
            ),
            "predicted_information_yield": (
                self.predicted_information_yield
            ),
            "calibration_error": self.calibration_error,
            "false_edge": self.false_edge,
            "promoted": self.promoted,
            "trial_sha256s": list(self.trial_sha256s),
            "settlement_observation_sha256s": list(
                self.settlement_observation_sha256s
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class EpistemicCriticalityReceipt:
    fission_sha256: str
    parent_count: int
    proposal_reproduction: float
    knowledge_reproduction: float
    error_reproduction: float
    good_spectral_radius: float
    error_spectral_radius: float
    assignment_rank: int
    child_count: int
    promoted_child_count: int
    false_child_count: int
    shared_trajectory_cost: float
    separate_trajectory_cost: float
    multiplexing_gain: float
    max_calibration_error: float
    calibration_tolerance: float
    observed_generations: int
    status: str
    child_settlements: tuple[ResidualChildSettlement, ...]
    trajectory_refs: tuple[str, ...]
    settlement_schedule_sha256: str
    modeled_term_count: int
    modeled_design_rank: int
    full_factorial_trajectory_count: int
    trajectory_compression_ratio: float

    @property
    def trial_sha256s(self) -> tuple[str, ...]:
        return tuple(sorted(
            sha256
            for row in self.child_settlements
            for sha256 in row.trial_sha256s
        ))

    @property
    def settlement_observation_sha256s(self) -> tuple[str, ...]:
        return tuple(sorted(
            sha256
            for row in self.child_settlements
            for sha256 in row.settlement_observation_sha256s
        ))

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "epistemic_criticality_receipt",
            "fission_sha256": self.fission_sha256,
            "parent_count": self.parent_count,
            "proposal_reproduction": self.proposal_reproduction,
            "knowledge_reproduction": self.knowledge_reproduction,
            "error_reproduction": self.error_reproduction,
            "good_spectral_radius": self.good_spectral_radius,
            "error_spectral_radius": self.error_spectral_radius,
            "knowledge_critical_boundary": 1.0,
            "error_critical_boundary": 1.0,
            "assignment_rank": self.assignment_rank,
            "child_count": self.child_count,
            "promoted_child_count": self.promoted_child_count,
            "false_child_count": self.false_child_count,
            "shared_trajectory_cost": self.shared_trajectory_cost,
            "separate_trajectory_cost": self.separate_trajectory_cost,
            "multiplexing_gain": self.multiplexing_gain,
            "max_calibration_error": self.max_calibration_error,
            "calibration_tolerance": self.calibration_tolerance,
            "observed_generations": self.observed_generations,
            "status": self.status,
            "takeoff_supported": self.status == "takeoff_supported",
            "child_settlements": [
                row.to_receipt() for row in self.child_settlements
            ],
            "trajectory_refs": list(self.trajectory_refs),
            "settlement_schedule_sha256": (
                self.settlement_schedule_sha256
            ),
            "modeled_term_count": self.modeled_term_count,
            "modeled_design_rank": self.modeled_design_rank,
            "full_factorial_trajectory_count": (
                self.full_factorial_trajectory_count
            ),
            "trajectory_compression_ratio": (
                self.trajectory_compression_ratio
            ),
            "trial_sha256s": list(self.trial_sha256s),
            "settlement_observation_sha256s": list(
                self.settlement_observation_sha256s
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def settle_residual_fission(
    fission: ResidualFissionReceipt,
    trials: Sequence[ResidualSettlementTrial],
    *,
    parent_count: int = 1,
    minimum_offer_count: int = 2,
    minimum_withhold_count: int = 2,
    minimum_first_stage_delta: float = 1.0,
    minimum_local_value_delta: float = 0.0,
    calibration_tolerance: float = 0.10,
    observed_generations: int = 1,
    require_full_factorial: bool = True,
    settlement_schedule: SparseSettlementSchedule | None = None,
) -> EpistemicCriticalityReceipt:
    """Settle independent children through micro-randomized trajectories."""

    rows = tuple(trials)
    if parent_count <= 0:
        raise ValueError("parent_count must be positive")
    if observed_generations != 1:
        raise ValueError(
            "one residual settlement receipt owns exactly one generation"
        )
    if minimum_offer_count <= 0 or minimum_withhold_count <= 0:
        raise ValueError("minimum assignment counts must be positive")
    tolerance = _nonnegative(calibration_tolerance, "calibration_tolerance")
    expected_niches = tuple(sorted(
        row.niche_ref for row in fission.basis_niches
    ))
    if settlement_schedule is not None:
        if require_full_factorial:
            raise ValueError(
                "sparse settlement schedule requires full factorial disabled"
            )
        if settlement_schedule.fission_sha256 != fission.sha256:
            raise ValueError("settlement schedule crossed fission authority")
        if settlement_schedule.niche_refs != expected_niches:
            raise ValueError("settlement schedule crossed residual-basis identity")
    if not rows:
        raise ValueError("residual settlement requires trials")
    if any(row.fission_sha256 != fission.sha256 for row in rows):
        raise ValueError("settlement trial crossed fission authority")
    if set(row.niche_ref for row in rows) != set(expected_niches):
        raise ValueError("settlement trial did not cover exact residual basis")
    for row in rows:
        if row.pivot_axis_id != fission.pivot_axis(row.niche_ref):
            raise ValueError("settlement trial crossed pivot-axis authority")

    by_trajectory: dict[str, list[ResidualSettlementTrial]] = {}
    for row in rows:
        by_trajectory.setdefault(row.trajectory_ref, []).append(row)
    assignment_patterns = []
    trajectory_costs = {}
    for trajectory_ref, trajectory_rows in sorted(by_trajectory.items()):
        if {row.niche_ref for row in trajectory_rows} != set(expected_niches):
            raise ValueError("trajectory did not settle every residual niche")
        if len(trajectory_rows) != len(expected_niches):
            raise ValueError("trajectory repeated a residual niche")
        decision_indices = [row.decision_index for row in trajectory_rows]
        if len(decision_indices) != len(set(decision_indices)):
            raise ValueError("trajectory reused one decision index")
        costs = {
            row.trajectory_primitive_action_cost for row in trajectory_rows
        }
        if len(costs) != 1:
            raise ValueError("trajectory cost drifted across niche settlements")
        trajectory_costs[trajectory_ref] = next(iter(costs))
        by_niche = {row.niche_ref: row for row in trajectory_rows}
        assignment_patterns.append(tuple(
            1 if by_niche[niche].assignment == "offer" else -1
            for niche in expected_niches
        ))
    if require_full_factorial:
        required_patterns = set(itertools.product((-1, 1), repeat=len(expected_niches)))
        if not required_patterns.issubset(set(assignment_patterns)):
            raise ValueError("settlement schedule omitted a factorial assignment")
    if settlement_schedule is not None and tuple(
        sorted(assignment_patterns)
    ) != tuple(sorted(settlement_schedule.assignment_patterns)):
        raise ValueError("trials differ from compiled sparse settlement schedule")
    design = [
        (Fraction(1), *tuple(Fraction(value) for value in pattern))
        for pattern in assignment_patterns
    ]
    assignment_rank = _rank(design) - 1
    modeled_term_count = (
        settlement_schedule.modeled_term_count
        if settlement_schedule is not None
        else len(expected_niches)
    )
    modeled_design_rank = (
        settlement_schedule.model_rank
        if settlement_schedule is not None
        else assignment_rank + 1
    )

    candidate_by_ref = {
        row.niche_ref: row for row in fission.basis_niches
    }
    child_settlements = []
    for niche_ref in expected_niches:
        niche_rows = tuple(row for row in rows if row.niche_ref == niche_ref)
        offers = tuple(row for row in niche_rows if row.assignment == "offer")
        withholds = tuple(
            row for row in niche_rows if row.assignment == "withhold"
        )
        offer_supported = _mean([
            float(row.supported_transport) for row in offers
        ]) if offers else 0.0
        withhold_supported = _mean([
            float(row.supported_transport) for row in withholds
        ]) if withholds else 0.0
        first_stage = offer_supported - withhold_supported
        value_delta = (
            _mean([row.local_external_value for row in offers])
            - _mean([row.local_external_value for row in withholds])
            if offers and withholds
            else 0.0
        )
        observed_yield_delta = (
            _mean([row.observed_information_yield for row in offers])
            - _mean([
                row.observed_information_yield for row in withholds
            ])
            if offers and withholds
            else 0.0
        )
        predicted = candidate_by_ref[
            niche_ref
        ].predicted_information_yield
        calibration_error = abs(predicted - observed_yield_delta)
        false_edge = bool(
            any(row.supported_transport for row in withholds)
            or any(row.contradicted for row in offers)
        )
        if (
            len(offers) < minimum_offer_count
            or len(withholds) < minimum_withhold_count
        ):
            status = "undersampled"
        elif assignment_rank < len(expected_niches):
            status = "assignment_rank_deficient"
        elif first_stage < float(minimum_first_stage_delta):
            status = "weak_first_stage"
        elif value_delta <= float(minimum_local_value_delta):
            status = "nonpositive_local_value"
        elif calibration_error > tolerance:
            status = "miscalibrated_information_yield"
        elif false_edge:
            status = "false_edge"
        else:
            status = "promoted"
        child_settlements.append(ResidualChildSettlement(
            niche_ref=niche_ref,
            pivot_axis_id=fission.pivot_axis(niche_ref),
            status=status,
            offer_count=len(offers),
            withhold_count=len(withholds),
            offer_supported_rate=offer_supported,
            withhold_supported_rate=withhold_supported,
            first_stage_delta=first_stage,
            local_value_delta=value_delta,
            observed_information_yield_delta=observed_yield_delta,
            predicted_information_yield=predicted,
            calibration_error=calibration_error,
            false_edge=false_edge,
            trial_sha256s=tuple(sorted(row.sha256 for row in niche_rows)),
            settlement_observation_sha256s=tuple(sorted(
                row.settlement_observation_sha256 for row in niche_rows
            )),
        ))
    promoted = sum(row.promoted for row in child_settlements)
    false_children = sum(row.false_edge for row in child_settlements)
    knowledge_reproduction = promoted / parent_count
    error_reproduction = false_children / parent_count
    shared_cost = sum(trajectory_costs.values())
    separate_cost = sum(
        row.trajectory_primitive_action_cost for row in rows
    )
    gain = (
        separate_cost / shared_cost
        if shared_cost > 0.0
        else math.inf if separate_cost > 0.0 else 1.0
    )
    max_calibration = max(
        row.calibration_error for row in child_settlements
    )
    mechanism_passed = bool(
        fission.raw_proposal_reproduction > 1.0
        and knowledge_reproduction > 1.0
        and error_reproduction < 1.0
        and assignment_rank == len(expected_niches)
        and modeled_design_rank == modeled_term_count + 1
        and promoted == len(expected_niches)
        and max_calibration <= tolerance
        and shared_cost < separate_cost
    )
    if mechanism_passed:
        status = "supercritical_mechanism_candidate"
    else:
        status = "subcritical_or_unresolved"
    return EpistemicCriticalityReceipt(
        fission_sha256=fission.sha256,
        parent_count=parent_count,
        proposal_reproduction=fission.raw_proposal_reproduction / parent_count,
        knowledge_reproduction=knowledge_reproduction,
        error_reproduction=error_reproduction,
        good_spectral_radius=knowledge_reproduction,
        error_spectral_radius=error_reproduction,
        assignment_rank=assignment_rank,
        child_count=len(expected_niches),
        promoted_child_count=promoted,
        false_child_count=false_children,
        shared_trajectory_cost=shared_cost,
        separate_trajectory_cost=separate_cost,
        multiplexing_gain=gain,
        max_calibration_error=max_calibration,
        calibration_tolerance=tolerance,
        observed_generations=observed_generations,
        status=status,
        child_settlements=tuple(child_settlements),
        trajectory_refs=tuple(sorted(by_trajectory)),
        settlement_schedule_sha256=(
            settlement_schedule.sha256
            if settlement_schedule is not None
            else ""
        ),
        modeled_term_count=modeled_term_count,
        modeled_design_rank=modeled_design_rank,
        full_factorial_trajectory_count=2 ** len(expected_niches),
        trajectory_compression_ratio=(
            (2 ** len(expected_niches)) / len(by_trajectory)
        ),
    )


def canonical_descendant_program_sha256(
    promoted_child_sha256s: Sequence[str],
) -> str:
    """Compile the exact program-family identity consumed by a descendant."""

    children = _canonical(promoted_child_sha256s)
    if not children:
        raise ValueError("descendant program requires promoted children")
    return stable_sha256({
        "schema": SCHEMA,
        "kind": "promoted_response_program_family",
        "promoted_child_sha256s": list(children),
    })


@dataclass(frozen=True)
class EpistemicGenerationReceipt:
    """One causally identified residual-fission generation."""

    generation_index: int
    authority: ResponseFissionAuthority
    fission_sha256: str
    criticality_sha256: str
    parent_child_sha256s: tuple[str, ...]
    promoted_child_sha256s: tuple[str, ...]
    promoted_child_types: tuple[tuple[str, str], ...]
    false_child_sha256s: tuple[str, ...]
    knowledge_reproduction: float
    error_reproduction: float
    shared_trajectory_cost: float
    separate_trajectory_cost: float
    criticality_status: str
    trajectory_refs: tuple[str, ...]
    trial_sha256s: tuple[str, ...]
    settlement_observation_sha256s: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "epistemic_generation_receipt",
            "generation_index": self.generation_index,
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "fission_sha256": self.fission_sha256,
            "criticality_sha256": self.criticality_sha256,
            "parent_child_sha256s": list(self.parent_child_sha256s),
            "promoted_child_sha256s": list(
                self.promoted_child_sha256s
            ),
            "promoted_child_types": [
                {"child_sha256": child, "type_id": type_id}
                for child, type_id in self.promoted_child_types
            ],
            "false_child_sha256s": list(self.false_child_sha256s),
            "parent_count": len(self.parent_child_sha256s),
            "promoted_child_count": len(self.promoted_child_sha256s),
            "false_child_count": len(self.false_child_sha256s),
            "knowledge_reproduction": self.knowledge_reproduction,
            "error_reproduction": self.error_reproduction,
            "shared_trajectory_cost": self.shared_trajectory_cost,
            "separate_trajectory_cost": self.separate_trajectory_cost,
            "criticality_status": self.criticality_status,
            "trajectory_refs": list(self.trajectory_refs),
            "trial_sha256s": list(self.trial_sha256s),
            "settlement_observation_sha256s": list(
                self.settlement_observation_sha256s
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _response_child_sha256(
    *,
    generation_index: int,
    fission: ResidualFissionReceipt,
    candidate: ResidualNicheCandidate,
    settlement: ResidualChildSettlement,
) -> str:
    return stable_sha256({
        "schema": SCHEMA,
        "kind": "settled_response_child",
        "generation_index": generation_index,
        "authority_sha256": fission.authority.sha256,
        "fission_sha256": fission.sha256,
        "parent_child_sha256s": list(candidate.parent_child_sha256s),
        "candidate_sha256": candidate.sha256,
        "settlement_sha256": settlement.sha256,
    })


def compile_epistemic_generation(
    fission: ResidualFissionReceipt,
    criticality: EpistemicCriticalityReceipt,
    *,
    generation_index: int,
) -> EpistemicGenerationReceipt:
    """Bind one criticality receipt to content-addressed parents and children."""

    if isinstance(generation_index, bool) or generation_index <= 0:
        raise ValueError("generation_index must be a positive integer")
    if criticality.fission_sha256 != fission.sha256:
        raise ValueError("criticality crossed fission authority")
    parents = fission.lineage_parent_sha256s
    if not parents:
        raise ValueError("epistemic generation requires lineage parents")
    if criticality.parent_count != len(parents):
        raise ValueError("criticality parent count crossed lineage authority")
    candidates = {row.niche_ref: row for row in fission.basis_niches}
    settlements = {
        row.niche_ref: row for row in criticality.child_settlements
    }
    if set(candidates) != set(settlements):
        raise ValueError("criticality crossed residual-basis identity")
    if len(criticality.trial_sha256s) != len(
        set(criticality.trial_sha256s)
    ):
        raise ValueError("generation reused a settlement trial")
    observations = criticality.settlement_observation_sha256s
    if len(observations) != len(set(observations)):
        raise ValueError("generation reused a settlement observation")

    promoted = []
    promoted_types = []
    false_children = []
    for niche_ref in sorted(candidates):
        candidate = candidates[niche_ref]
        settlement = settlements[niche_ref]
        child_sha256 = _response_child_sha256(
            generation_index=generation_index,
            fission=fission,
            candidate=candidate,
            settlement=settlement,
        )
        if settlement.promoted:
            promoted.append(child_sha256)
            promoted_types.append((child_sha256, settlement.pivot_axis_id))
        if settlement.false_edge:
            false_children.append(child_sha256)
    if len(promoted) != criticality.promoted_child_count:
        raise ValueError("promoted-child count crossed criticality receipt")
    if len(false_children) != criticality.false_child_count:
        raise ValueError("false-child count crossed criticality receipt")
    return EpistemicGenerationReceipt(
        generation_index=generation_index,
        authority=fission.authority,
        fission_sha256=fission.sha256,
        criticality_sha256=criticality.sha256,
        parent_child_sha256s=parents,
        promoted_child_sha256s=tuple(sorted(promoted)),
        promoted_child_types=tuple(sorted(promoted_types)),
        false_child_sha256s=tuple(sorted(false_children)),
        knowledge_reproduction=criticality.knowledge_reproduction,
        error_reproduction=criticality.error_reproduction,
        shared_trajectory_cost=criticality.shared_trajectory_cost,
        separate_trajectory_cost=criticality.separate_trajectory_cost,
        criticality_status=criticality.status,
        trajectory_refs=criticality.trajectory_refs,
        trial_sha256s=criticality.trial_sha256s,
        settlement_observation_sha256s=observations,
    )


@dataclass(frozen=True)
class EpistemicLineageReceipt:
    """Finite-generation growth receipt with exact causal ancestry."""

    generations: tuple[EpistemicGenerationReceipt, ...]
    knowledge_geometric_growth: float
    error_geometric_growth: float
    knowledge_log_growth: float
    validated_descendant_multiplier: float
    total_shared_trajectory_cost: float
    total_separate_trajectory_cost: float
    multiplexing_gain: float
    status: str

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "epistemic_lineage_receipt",
            "generation_count": len(self.generations),
            "generations": [row.to_receipt() for row in self.generations],
            "root_parent_sha256s": list(
                self.generations[0].parent_child_sha256s
            ),
            "final_promoted_child_sha256s": list(
                self.generations[-1].promoted_child_sha256s
            ),
            "knowledge_growth_factors": [
                row.knowledge_reproduction for row in self.generations
            ],
            "error_growth_factors": [
                row.error_reproduction for row in self.generations
            ],
            "knowledge_geometric_growth": self.knowledge_geometric_growth,
            "error_geometric_growth": self.error_geometric_growth,
            "knowledge_log_growth": self.knowledge_log_growth,
            "validated_descendant_multiplier": (
                self.validated_descendant_multiplier
            ),
            "total_shared_trajectory_cost": (
                self.total_shared_trajectory_cost
            ),
            "total_separate_trajectory_cost": (
                self.total_separate_trajectory_cost
            ),
            "multiplexing_gain": self.multiplexing_gain,
            "status": self.status,
            "takeoff_supported": False,
            "external_settlement_required": True,
            "cross_task_transport_required": True,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _geometric_growth(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("geometric growth requires values")
    if any(value < 0.0 for value in values):
        raise ValueError("growth factors must be nonnegative")
    if any(value == 0.0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))


def _lineage_invariant_authority(
    authority: ResponseFissionAuthority,
) -> tuple[Any, ...]:
    return (
        authority.scope,
        authority.catalog_sha256,
        authority.intervention_revision_sha256,
        authority.primitive_cost_unit,
    )


def compile_epistemic_lineage(
    generations: Sequence[EpistemicGenerationReceipt],
) -> EpistemicLineageReceipt:
    """Compile two or more fresh generations without survivor selection."""

    rows = tuple(generations)
    if len(rows) < 2:
        raise ValueError("epistemic lineage requires at least two generations")
    if tuple(row.generation_index for row in rows) != tuple(
        range(1, len(rows) + 1)
    ):
        raise ValueError("epistemic lineage generations are not contiguous")
    invariant = _lineage_invariant_authority(rows[0].authority)
    if any(
        _lineage_invariant_authority(row.authority) != invariant
        for row in rows[1:]
    ):
        raise ValueError("epistemic lineage crossed invariant authority")
    if len({row.authority.derivative_sha256 for row in rows}) != len(rows):
        raise ValueError("epistemic lineage reused a response derivative")

    for previous, current in zip(rows, rows[1:]):
        if current.parent_child_sha256s != previous.promoted_child_sha256s:
            raise ValueError("descendant consumed a non-promoted parent set")
        expected_program = canonical_descendant_program_sha256(
            previous.promoted_child_sha256s
        )
        if current.authority.source_program_sha256 != expected_program:
            raise ValueError("descendant source program crossed child-family identity")

    for name, extractor in (
        ("trajectory", lambda row: row.trajectory_refs),
        ("trial", lambda row: row.trial_sha256s),
        (
            "settlement observation",
            lambda row: row.settlement_observation_sha256s,
        ),
    ):
        seen: set[str] = set()
        for row in rows:
            values = set(extractor(row))
            if seen.intersection(values):
                raise ValueError(f"epistemic lineage reused a {name}")
            seen.update(values)

    knowledge = tuple(row.knowledge_reproduction for row in rows)
    errors = tuple(row.error_reproduction for row in rows)
    knowledge_growth = _geometric_growth(knowledge)
    error_growth = _geometric_growth(errors)
    shared_cost = sum(row.shared_trajectory_cost for row in rows)
    separate_cost = sum(row.separate_trajectory_cost for row in rows)
    multiplexing_gain = (
        separate_cost / shared_cost
        if shared_cost > 0.0
        else math.inf if separate_cost > 0.0 else 1.0
    )
    passed = bool(
        all(
            row.criticality_status == "supercritical_mechanism_candidate"
            for row in rows
        )
        and all(value > 1.0 for value in knowledge)
        and all(value < 1.0 for value in errors)
        and knowledge_growth > 1.0
        and error_growth < 1.0
        and shared_cost < separate_cost
    )
    status = (
        "multigeneration_mechanism_candidate"
        if passed
        else "subcritical_or_unresolved"
    )
    return EpistemicLineageReceipt(
        generations=rows,
        knowledge_geometric_growth=knowledge_growth,
        error_geometric_growth=error_growth,
        knowledge_log_growth=(
            math.log(knowledge_growth)
            if knowledge_growth > 0.0
            else -math.inf
        ),
        validated_descendant_multiplier=(
            len(rows[-1].promoted_child_sha256s)
            / len(rows[0].parent_child_sha256s)
        ),
        total_shared_trajectory_cost=shared_cost,
        total_separate_trajectory_cost=separate_cost,
        multiplexing_gain=multiplexing_gain,
        status=status,
    )


__all__ = [
    "EpistemicCriticalityReceipt",
    "EpistemicGenerationReceipt",
    "EpistemicLineageReceipt",
    "MeasurementAxis",
    "ResidualChildSettlement",
    "ResidualFissionReceipt",
    "ResidualNicheCandidate",
    "ResidualSettlementTrial",
    "ResponseFissionAuthority",
    "SparseSettlementSchedule",
    "canonical_descendant_program_sha256",
    "compile_epistemic_generation",
    "compile_epistemic_lineage",
    "compile_residual_fission",
    "compile_sparse_settlement_schedule",
    "settle_residual_fission",
]
