"""Guarded preparation-probe-readout protocols priced by information yield.

The common object is an experiment, not a route or a task target.  A protocol
has three separately owned parts:

* a guarded preparation word;
* one probe;
* an externally observed response.

Compatible mechanisms supply the response committee.  Two protocols over the
same committee are extensionally equal when they induce the same partition of
that committee, even when their response labels differ.  Equal protocols are
canonicalized to the cheapest representative before selection.

Cost keeps primitive execution separate from compiled control tokens.  A
learned skill may reduce ``control_units`` while leaving every primitive
intervention in ``preparation_execution_units`` and
``probe_execution_units``.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Hashable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.information_yield_pricing import price_experiment


CANONICAL_PRICING_ENGINE = (
    "ztare.common.information_yield_pricing.price_experiment"
)


def _require_hashable(value: Any, label: str) -> None:
    try:
        hash(value)
    except TypeError as exc:
        raise TypeError(f"{label} must be hashable") from exc


def _finite_nonnegative(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return result


@dataclass(frozen=True)
class ProtocolYieldWeights:
    """Caller-owned weights for the existing composite-yield components."""

    identification: float
    compression: float
    novelty: float

    def __post_init__(self) -> None:
        _finite_nonnegative(self.identification, "identification weight")
        _finite_nonnegative(self.compression, "compression weight")
        _finite_nonnegative(self.novelty, "novelty weight")
        if self.identification + self.compression + self.novelty <= 0:
            raise ValueError("at least one protocol-yield weight must be positive")


@dataclass(frozen=True)
class ProtocolCost:
    """Explicit protocol cost coordinates.

    Primitive execution is never compressed by a learned skill.  The separate
    control coordinate can account for a smaller compiled plan.
    """

    preparation_execution_units: float
    probe_execution_units: float
    readout_units: float = 0.0
    control_units: float = 0.0
    irreversibility_units: float = 0.0

    def __post_init__(self) -> None:
        for label, value in (
            ("preparation_execution_units", self.preparation_execution_units),
            ("probe_execution_units", self.probe_execution_units),
            ("readout_units", self.readout_units),
            ("control_units", self.control_units),
            ("irreversibility_units", self.irreversibility_units),
        ):
            _finite_nonnegative(value, label)
        if self.total_units <= 0:
            raise ValueError("protocol total cost must be positive")

    @property
    def primitive_execution_units(self) -> float:
        return (
            float(self.preparation_execution_units)
            + float(self.probe_execution_units)
        )

    @property
    def total_units(self) -> float:
        return (
            self.primitive_execution_units
            + float(self.readout_units)
            + float(self.control_units)
            + float(self.irreversibility_units)
        )

    def to_receipt(self) -> dict[str, float]:
        return {
            "preparation_execution_units": self.preparation_execution_units,
            "probe_execution_units": self.probe_execution_units,
            "primitive_execution_units": self.primitive_execution_units,
            "readout_units": self.readout_units,
            "control_units": self.control_units,
            "irreversibility_units": self.irreversibility_units,
            "total_units": self.total_units,
        }


@dataclass(frozen=True)
class GuardedExperimentProtocol:
    """Opaque preparation-probe protocol proposed by a substrate lowering."""

    protocol_id: str
    preparation: tuple[Hashable, ...]
    probe: Hashable
    target_key: Hashable
    cost: ProtocolCost
    novel_context: bool
    guard_admitted: bool = True
    guard_reason: str = ""
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.protocol_id).strip():
            raise ValueError("protocol_id must be nonempty")
        for index, operation in enumerate(self.preparation):
            _require_hashable(operation, f"preparation[{index}]")
        _require_hashable(self.probe, "probe")
        _require_hashable(self.target_key, "target_key")
        if not self.guard_admitted and not str(self.guard_reason).strip():
            raise ValueError("a rejected protocol guard requires guard_reason")

    @property
    def operations(self) -> tuple[Hashable, ...]:
        return (*self.preparation, self.probe)

    def identity_receipt(self, *, evidence_cap: int = 20) -> dict[str, Any]:
        refs = tuple(sorted(self.evidence_refs))
        return {
            "protocol_id": self.protocol_id,
            "preparation_operation_sha256s": [
                stable_sha256(operation) for operation in self.preparation
            ],
            "probe_sha256": stable_sha256(self.probe),
            "target_sha256": stable_sha256(self.target_key),
            "operation_count": len(self.operations),
            "novel_context": bool(self.novel_context),
            "guard_admitted": bool(self.guard_admitted),
            "guard_reason": self.guard_reason,
            "cost": self.cost.to_receipt(),
            "evidence_ref_count": len(refs),
            "evidence_refs_sha256": stable_sha256(refs),
            "evidence_refs": list(refs[:max(0, int(evidence_cap))]),
        }


@dataclass(frozen=True)
class ProtocolResponseHypothesis:
    """One evidence-backed compatible mechanism and its predicted response."""

    hypothesis_id: str
    response: Hashable
    description_units: int = 1
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.hypothesis_id).strip():
            raise ValueError("hypothesis_id must be nonempty")
        _require_hashable(self.response, "response")
        if isinstance(self.description_units, bool) or self.description_units <= 0:
            raise ValueError("description_units must be a positive integer")


@dataclass(frozen=True)
class GuardedProtocolCandidate:
    protocol: GuardedExperimentProtocol
    committee: tuple[ProtocolResponseHypothesis, ...]

    def __post_init__(self) -> None:
        identities = [row.hypothesis_id for row in self.committee]
        if len(identities) != len(set(identities)):
            raise ValueError("protocol committee hypothesis IDs must be unique")


def _canonical_committee(
    candidate: GuardedProtocolCandidate,
) -> tuple[ProtocolResponseHypothesis, ...]:
    return tuple(sorted(
        candidate.committee,
        key=lambda row: row.hypothesis_id,
    ))


def _partition_signature(
    committee: Iterable[ProtocolResponseHypothesis],
) -> tuple[tuple[str, ...], ...]:
    cells: dict[Hashable, list[str]] = {}
    for member in committee:
        cells.setdefault(member.response, []).append(member.hypothesis_id)
    return tuple(sorted(
        (tuple(sorted(member_ids)) for member_ids in cells.values()),
        key=lambda cell: (len(cell), cell),
    ))


@dataclass(frozen=True)
class GuardedProtocolPrice:
    protocol_id: str
    status: str
    committee_sha256: str
    partition_sha256: str
    committee_size: int
    response_class_count: int
    identification: float
    compression_gain: float
    novelty: float
    weighted_yield: float
    yield_density: float
    cost: ProtocolCost
    protocol: GuardedExperimentProtocol

    @property
    def extensional_identity(self) -> tuple[str, str]:
        return self.committee_sha256, self.partition_sha256

    def to_receipt(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "status": self.status,
            "committee_sha256": self.committee_sha256,
            "partition_sha256": self.partition_sha256,
            "committee_size": self.committee_size,
            "response_class_count": self.response_class_count,
            "identification": round(self.identification, 8),
            "compression_gain": round(self.compression_gain, 8),
            "novelty": round(self.novelty, 8),
            "weighted_yield": round(self.weighted_yield, 8),
            "yield_density": round(self.yield_density, 8),
            "cost": self.cost.to_receipt(),
            "protocol": self.protocol.identity_receipt(),
            "canonical_pricing_engine": CANONICAL_PRICING_ENGINE,
        }


def price_guarded_protocol(
    candidate: GuardedProtocolCandidate,
    *,
    weights: ProtocolYieldWeights,
) -> GuardedProtocolPrice:
    """Price one admitted protocol against its compatible response committee."""

    protocol = candidate.protocol
    committee = _canonical_committee(candidate)
    committee_sha = stable_sha256(tuple(
        member.hypothesis_id for member in committee
    ))
    partition = _partition_signature(committee)
    partition_sha = stable_sha256(partition)
    if not protocol.guard_admitted:
        status = "guard_rejected"
        components = None
    elif not committee:
        status = "committee_unavailable"
        components = None
    else:
        status = "priced"
        components = price_experiment(
            committee,
            predict=lambda member: member.response,
            size_fn=lambda member: member.description_units,
            novel_context=protocol.novel_context,
        )
    identification = components.identification if components else 0.0
    compression = components.compression_gain if components else 0.0
    novelty = components.novelty if components else 0.0
    weighted = (
        components.score(
            weights.identification,
            weights.compression,
            weights.novelty,
        )
        if components
        else 0.0
    )
    return GuardedProtocolPrice(
        protocol_id=protocol.protocol_id,
        status=status,
        committee_sha256=committee_sha,
        partition_sha256=partition_sha,
        committee_size=len(committee),
        response_class_count=len(partition),
        identification=identification,
        compression_gain=compression,
        novelty=novelty,
        weighted_yield=weighted,
        yield_density=weighted / protocol.cost.total_units,
        cost=protocol.cost,
        protocol=protocol,
    )


@dataclass(frozen=True)
class GuardedProtocolAssignment:
    """Externally sealed instruction to execute one canonical protocol.

    Assignment is an experiment-control authority.  It does not confer task
    value, utility, contrast priority, or information yield on the selected
    protocol.
    """

    assignment_ref: str
    assigned_protocol_id: str
    canonical_protocol_ids: tuple[str, ...]
    decision_choice_authority_sha256: str
    source_assignment_sha256: str
    assignment_evidence_ref: str
    schema: str = "ztare-guarded-protocol-assignment-v1"

    def __post_init__(self) -> None:
        for name in (
            "assignment_ref",
            "assigned_protocol_id",
            "decision_choice_authority_sha256",
            "source_assignment_sha256",
            "assignment_evidence_ref",
        ):
            value = str(getattr(self, name) or "").strip()
            if not value:
                raise ValueError(f"{name} must be nonempty")
            object.__setattr__(self, name, value)
        canonical = tuple(sorted(
            str(protocol_id).strip()
            for protocol_id in self.canonical_protocol_ids
        ))
        if not canonical or any(not row for row in canonical):
            raise ValueError("canonical_protocol_ids must be nonempty")
        if len(set(canonical)) != len(canonical):
            raise ValueError("canonical protocol identities must be unique")
        if self.assigned_protocol_id not in canonical:
            raise ValueError(
                "assigned protocol is outside the frozen canonical set"
            )
        object.__setattr__(self, "canonical_protocol_ids", canonical)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "assignment_ref": self.assignment_ref,
            "assigned_protocol_id": self.assigned_protocol_id,
            "canonical_protocol_ids": list(self.canonical_protocol_ids),
            "decision_choice_authority_sha256": (
                self.decision_choice_authority_sha256
            ),
            "source_assignment_sha256": self.source_assignment_sha256,
            "assignment_evidence_ref": self.assignment_evidence_ref,
            "authority": "sealed_experiment_assignment",
            "task_value_authorized": False,
            "external_utility_authorized": False,
            "information_yield_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class GuardedProtocolSelection:
    status: str
    selected_protocol_id: str
    selected: GuardedProtocolPrice | None
    prices: tuple[GuardedProtocolPrice, ...]
    canonical_protocol_ids: tuple[str, ...]
    deduplicated_protocol_ids: tuple[str, ...]
    weights: ProtocolYieldWeights
    max_primitive_execution_units: float | None = None
    budget_ineligible_protocol_ids: tuple[str, ...] = ()
    task_value_by_protocol_id: tuple[tuple[str, int], ...] = ()
    contrast_priority_by_protocol_id: tuple[tuple[str, int], ...] = ()
    assignment: GuardedProtocolAssignment | None = None
    schema: str = "ztare-guarded-protocol-selection-v1"

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "status": self.status,
            "selected_protocol_id": self.selected_protocol_id,
            "canonical_protocol_ids": list(self.canonical_protocol_ids),
            "deduplicated_protocol_ids": list(
                self.deduplicated_protocol_ids
            ),
            "max_primitive_execution_units": (
                self.max_primitive_execution_units
            ),
            "budget_ineligible_protocol_ids": list(
                self.budget_ineligible_protocol_ids
            ),
            "task_value_by_protocol_id": {
                protocol_id: value
                for protocol_id, value in self.task_value_by_protocol_id
            },
            "task_value_authority": (
                "matched_external_outcome_contrasts_only"
            ),
            "contrast_priority_by_protocol_id": {
                protocol_id: value
                for protocol_id, value
                in self.contrast_priority_by_protocol_id
            },
            "contrast_priority_authority": (
                "unresolved_exact_choice_set_coverage"
            ),
            "weights": {
                "identification": self.weights.identification,
                "compression": self.weights.compression,
                "novelty": self.weights.novelty,
            },
            "prices": [price.to_receipt() for price in self.prices],
            "canonical_pricing_engine": CANONICAL_PRICING_ENGINE,
        }
        if self.assignment is not None:
            payload.update({
                "selection_authority": "sealed_experiment_assignment",
                "assignment": self.assignment.to_receipt(),
                "assignment_sha256": self.assignment.sha256,
                "assignment_task_value_authorized": False,
                "assignment_external_utility_authorized": False,
                "assignment_information_yield_authorized": False,
            })
        return payload


def select_guarded_protocol(
    candidates: Iterable[GuardedProtocolCandidate],
    *,
    weights: ProtocolYieldWeights,
    max_primitive_execution_units: float | None = None,
    task_value_by_protocol_id: Mapping[str, int] | None = None,
    contrast_priority_by_protocol_id: Mapping[str, int] | None = None,
    assignment: GuardedProtocolAssignment | None = None,
) -> GuardedProtocolSelection:
    """Canonicalize feasible equal experiments, then maximize yield density.

    ``max_primitive_execution_units`` is an environment-intervention
    constraint.  Compiled control tokens may change pricing, but they cannot
    make a primitive operation word executable inside a smaller budget.
    """

    primitive_budget = (
        None
        if max_primitive_execution_units is None
        else _finite_nonnegative(
            max_primitive_execution_units,
            "max_primitive_execution_units",
        )
    )
    task_values = {
        str(protocol_id): int(value)
        for protocol_id, value in (
            task_value_by_protocol_id or {}
        ).items()
    }
    if any(value not in {-1, 0, 1} for value in task_values.values()):
        raise ValueError("protocol task values must be -1, 0, or 1")
    contrast_priorities = {
        str(protocol_id): int(value)
        for protocol_id, value in (
            contrast_priority_by_protocol_id or {}
        ).items()
    }
    if any(
        value not in {0, 1}
        for value in contrast_priorities.values()
    ):
        raise ValueError("protocol contrast priorities must be 0 or 1")

    priced = tuple(sorted(
        (
            price_guarded_protocol(candidate, weights=weights)
            for candidate in candidates
        ),
        key=lambda row: row.protocol_id,
    ))
    admitted = [row for row in priced if row.status == "priced"]
    budget_ineligible = [
        row for row in admitted
        if (
            primitive_budget is not None
            and row.cost.primitive_execution_units > primitive_budget
        )
    ]
    feasible = [
        row for row in admitted
        if (
            primitive_budget is None
            or row.cost.primitive_execution_units <= primitive_budget
        )
    ]
    by_identity: dict[tuple[str, str], list[GuardedProtocolPrice]] = {}
    for row in feasible:
        by_identity.setdefault(row.extensional_identity, []).append(row)
    canonical = []
    deduplicated = []
    for rows in by_identity.values():
        rows.sort(key=lambda row: (
            row.cost.total_units,
            row.cost.primitive_execution_units,
            row.cost.control_units,
            row.protocol_id,
        ))
        canonical.append(rows[0])
        deduplicated.extend(row.protocol_id for row in rows[1:])
    canonical.sort(key=lambda row: row.protocol_id)
    eligible = [row for row in canonical if row.weighted_yield > 0]
    canonical_ids = tuple(row.protocol_id for row in canonical)
    if assignment is not None:
        if assignment.canonical_protocol_ids != canonical_ids:
            raise ValueError(
                "protocol assignment crossed the canonical choice set"
            )
        selected = next(
            (
                row for row in eligible
                if row.protocol_id == assignment.assigned_protocol_id
            ),
            None,
        )
        if selected is None:
            raise ValueError(
                "assigned protocol is not a valued affordable canonical option"
            )
    else:
        selected = (
            max(
                eligible,
                key=lambda row: (
                    task_values.get(row.protocol_id, 0),
                    contrast_priorities.get(row.protocol_id, 0),
                    row.yield_density,
                    row.weighted_yield,
                    row.identification,
                    row.compression_gain,
                    row.novelty,
                    -row.cost.total_units,
                    # ``max`` needs the reverse of lexical protocol order.
                    tuple(-ord(char) for char in row.protocol_id),
                ),
            )
            if eligible
            else None
        )
    valued = [row for row in admitted if row.weighted_yield > 0]
    feasible_valued = [
        row for row in feasible if row.weighted_yield > 0
    ]
    status = (
        "selected"
        if selected is not None
        else "no_affordable_protocol"
        if primitive_budget is not None and valued and not feasible_valued
        else "no_valued_protocol"
    )
    return GuardedProtocolSelection(
        status=status,
        selected_protocol_id=(
            selected.protocol_id if selected is not None else ""
        ),
        selected=selected,
        prices=priced,
        canonical_protocol_ids=tuple(
            row.protocol_id for row in canonical
        ),
        deduplicated_protocol_ids=tuple(sorted(deduplicated)),
        weights=weights,
        max_primitive_execution_units=primitive_budget,
        budget_ineligible_protocol_ids=tuple(
            sorted(row.protocol_id for row in budget_ineligible)
        ),
        task_value_by_protocol_id=tuple(sorted(
            (
                protocol_id,
                value,
            )
            for protocol_id, value in task_values.items()
            if protocol_id in {row.protocol_id for row in priced}
        )),
        contrast_priority_by_protocol_id=tuple(sorted(
            (
                protocol_id,
                value,
            )
            for protocol_id, value in contrast_priorities.items()
            if protocol_id in {row.protocol_id for row in priced}
        )),
        assignment=assignment,
    )


__all__ = [
    "CANONICAL_PRICING_ENGINE",
    "GuardedExperimentProtocol",
    "GuardedProtocolCandidate",
    "GuardedProtocolAssignment",
    "GuardedProtocolPrice",
    "GuardedProtocolSelection",
    "ProtocolCost",
    "ProtocolResponseHypothesis",
    "ProtocolYieldWeights",
    "price_guarded_protocol",
    "select_guarded_protocol",
]
