"""Typed contracts for investment decisions and point-in-time evidence.

The finance substrate owns entity, play, observation, fingerprint, thesis, and
review-packet identity. Recursive policy identity remains owned by
``ztare.strategy`` and paper-book identity remains owned by ``ztare.investment.paper``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Iterable, Literal, Mapping

from ztare.common.equivariance import stable_sha256


MetricDirection = Literal["higher", "lower"]
PositionActionKind = Literal["watch", "start", "add", "hold", "trim", "exit", "hedge"]
ObjectiveDirection = Literal["maximize", "minimize"]
ProfileDataClass = Literal["operator", "reference_fixture"]
ProfileStage = Literal["draft", "active", "reference"]


def require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be nonempty")
    return text


def require_finite(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def canonical_timestamp(value: Any, label: str) -> str:
    text = require_text(value, label)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    normalized = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    return normalized.replace("+00:00", "Z")


def timestamp_key(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)


def require_refs(values: Iterable[Any], label: str) -> tuple[str, ...]:
    refs = tuple(sorted({require_text(value, label) for value in values}))
    if not refs:
        raise ValueError(f"{label} must be nonempty")
    return refs


@dataclass(frozen=True, slots=True)
class InvestmentProfileLifecycle:
    """Governing identity for an editable profile at one compilation epoch."""

    data_class: ProfileDataClass
    stage: ProfileStage
    authority: str = "paper"

    def __post_init__(self) -> None:
        if self.data_class not in {"operator", "reference_fixture"}:
            raise ValueError("profile lifecycle data_class must be operator or reference_fixture")
        if self.stage not in {"draft", "active", "reference"}:
            raise ValueError("profile lifecycle stage must be draft, active, or reference")
        if self.data_class == "reference_fixture" and self.stage != "reference":
            raise ValueError("reference fixtures require the reference lifecycle stage")
        if self.data_class == "operator" and self.stage == "reference":
            raise ValueError("operator profiles cannot use the reference lifecycle stage")
        if require_text(self.authority, "profile lifecycle authority") != "paper":
            raise ValueError("investment profile lifecycle permits paper authority only")

    def to_dict(self) -> dict[str, str]:
        return {
            "data_class": self.data_class,
            "stage": self.stage,
            "authority": self.authority,
        }


@dataclass(frozen=True, slots=True)
class EntityRef:
    entity_id: str
    entity_kind: str
    name: str
    currency: str

    def __post_init__(self) -> None:
        for attr in ("entity_id", "entity_kind", "name", "currency"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), attr))

    def to_dict(self) -> dict[str, str]:
        return {
            "entity_id": self.entity_id,
            "entity_kind": self.entity_kind,
            "name": self.name,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class InvestmentPlay:
    play_id: str
    version: str
    entity_kind: str
    universe: str
    benchmark_id: str
    horizon_days: int
    min_weight: float
    max_weight: float
    allow_short: bool
    transaction_cost_bps: float

    def __post_init__(self) -> None:
        for attr in ("play_id", "version", "entity_kind", "universe", "benchmark_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), attr))
        if isinstance(self.horizon_days, bool) or int(self.horizon_days) < 1:
            raise ValueError("play horizon_days must be positive")
        object.__setattr__(self, "horizon_days", int(self.horizon_days))
        minimum = require_finite(self.min_weight, "play.min_weight")
        maximum = require_finite(self.max_weight, "play.max_weight")
        if not self.allow_short and minimum < 0:
            raise ValueError("a long-only play cannot have a negative min_weight")
        if minimum > maximum:
            raise ValueError("play min_weight cannot exceed max_weight")
        if maximum > 1:
            raise ValueError("play max_weight cannot exceed 1")
        costs = require_finite(self.transaction_cost_bps, "play.transaction_cost_bps")
        if costs < 0:
            raise ValueError("play transaction_cost_bps cannot be negative")
        object.__setattr__(self, "min_weight", minimum)
        object.__setattr__(self, "max_weight", maximum)
        object.__setattr__(self, "transaction_cost_bps", costs)

    @property
    def play_key(self) -> str:
        return f"{self.play_id}@{self.version}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "play_id": self.play_id,
            "version": self.version,
            "play_key": self.play_key,
            "entity_kind": self.entity_kind,
            "universe": self.universe,
            "benchmark_id": self.benchmark_id,
            "horizon_days": self.horizon_days,
            "min_weight": self.min_weight,
            "max_weight": self.max_weight,
            "allow_short": self.allow_short,
            "transaction_cost_bps": self.transaction_cost_bps,
        }


@dataclass(frozen=True, slots=True)
class MetricObservation:
    observation_id: str
    entity_id: str
    metric_id: str
    value: float
    unit: str
    observed_at: str
    available_at: str
    source_ref: str

    def __post_init__(self) -> None:
        for attr in ("observation_id", "entity_id", "metric_id", "unit", "source_ref"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), attr))
        object.__setattr__(self, "value", require_finite(self.value, "observation.value"))
        object.__setattr__(
            self,
            "observed_at",
            canonical_timestamp(self.observed_at, "observation.observed_at"),
        )
        object.__setattr__(
            self,
            "available_at",
            canonical_timestamp(self.available_at, "observation.available_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "entity_id": self.entity_id,
            "metric_id": self.metric_id,
            "value": self.value,
            "unit": self.unit,
            "observed_at": self.observed_at,
            "available_at": self.available_at,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True, slots=True)
class PointInTimeSnapshot:
    snapshot_id: str
    as_of: str
    source_path: str
    source_sha256: str
    observations: tuple[MetricObservation, ...]
    excluded_future_count: int
    snapshot_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", require_text(self.snapshot_id, "snapshot_id"))
        object.__setattr__(self, "as_of", canonical_timestamp(self.as_of, "snapshot.as_of"))
        object.__setattr__(self, "source_path", require_text(self.source_path, "snapshot.source_path"))
        digest = require_text(self.source_sha256, "snapshot.source_sha256")
        if len(digest) != 64:
            raise ValueError("snapshot.source_sha256 must be a SHA-256 digest")
        if self.excluded_future_count < 0:
            raise ValueError("excluded_future_count cannot be negative")
        rows = tuple(sorted(
            self.observations,
            key=lambda row: (row.entity_id, row.metric_id, row.available_at, row.observation_id),
        ))
        if len({row.observation_id for row in rows}) != len(rows):
            raise ValueError("observation identities must be unique")
        if any(timestamp_key(row.available_at) > timestamp_key(self.as_of) for row in rows):
            raise ValueError("snapshot contains an observation unavailable at as_of")
        object.__setattr__(self, "observations", rows)
        object.__setattr__(self, "snapshot_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-point-in-time-snapshot-v1",
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "observations": [row.to_dict() for row in self.observations],
            "excluded_future_count": self.excluded_future_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "snapshot_sha256": self.snapshot_sha256}

    def latest(self, entity_id: str, metric_id: str) -> MetricObservation:
        rows = [
            row for row in self.observations
            if row.entity_id == entity_id and row.metric_id == metric_id
        ]
        if not rows:
            raise KeyError(f"missing point-in-time observation: {entity_id}.{metric_id}")
        latest_key = max(
            (timestamp_key(row.available_at), timestamp_key(row.observed_at))
            for row in rows
        )
        latest = tuple(
            row for row in rows
            if (
                timestamp_key(row.available_at),
                timestamp_key(row.observed_at),
            ) == latest_key
        )
        if len({(row.value, row.unit) for row in latest}) != 1:
            raise ValueError(
                f"conflicting latest observations: {entity_id}.{metric_id}"
            )
        return min(latest, key=lambda row: row.observation_id)

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(sorted({row.source_ref for row in self.observations}))


@dataclass(frozen=True, slots=True)
class FingerprintMetricDefinition:
    metric_id: str
    unit: str
    direction: MetricDirection
    floor: float
    ceiling: float
    weight: float
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", require_text(self.metric_id, "fingerprint.metric_id"))
        object.__setattr__(self, "unit", require_text(self.unit, "fingerprint.unit"))
        if self.direction not in {"higher", "lower"}:
            raise ValueError("fingerprint direction must be higher or lower")
        floor = require_finite(self.floor, "fingerprint.floor")
        ceiling = require_finite(self.ceiling, "fingerprint.ceiling")
        weight = require_finite(self.weight, "fingerprint.weight")
        if floor >= ceiling:
            raise ValueError("fingerprint floor must be below ceiling")
        if weight < 0:
            raise ValueError("fingerprint weight cannot be negative")
        object.__setattr__(self, "floor", floor)
        object.__setattr__(self, "ceiling", ceiling)
        object.__setattr__(self, "weight", weight)

    def normalize(self, value: float) -> float:
        raw = (value - self.floor) / (self.ceiling - self.floor)
        bounded = min(1.0, max(0.0, raw))
        return bounded if self.direction == "higher" else 1.0 - bounded

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "unit": self.unit,
            "direction": self.direction,
            "floor": self.floor,
            "ceiling": self.ceiling,
            "weight": self.weight,
            "required": self.required,
        }


@dataclass(frozen=True, slots=True)
class FingerprintMetric:
    definition: FingerprintMetricDefinition
    observation: MetricObservation
    normalized_score: float

    def __post_init__(self) -> None:
        if self.definition.metric_id != self.observation.metric_id:
            raise ValueError("fingerprint metric identity mismatch")
        if self.definition.unit != self.observation.unit:
            raise ValueError(
                f"unit mismatch for {self.definition.metric_id}: "
                f"expected {self.definition.unit}, got {self.observation.unit}"
            )
        score = require_finite(self.normalized_score, "fingerprint.normalized_score")
        if not 0 <= score <= 1:
            raise ValueError("fingerprint normalized_score must be in [0, 1]")
        object.__setattr__(self, "normalized_score", score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": self.definition.to_dict(),
            "observation": self.observation.to_dict(),
            "normalized_score": self.normalized_score,
        }


@dataclass(frozen=True, slots=True)
class EntityFingerprint:
    fingerprint_id: str
    schema_version: str
    entity: EntityRef
    play_key: str
    evidence_epoch: str
    metrics: tuple[FingerprintMetric, ...]
    missing_optional_metrics: tuple[str, ...]
    aggregate_score: float
    fingerprint_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fingerprint_id", require_text(self.fingerprint_id, "fingerprint_id"))
        object.__setattr__(self, "schema_version", require_text(self.schema_version, "fingerprint.schema_version"))
        object.__setattr__(self, "play_key", require_text(self.play_key, "fingerprint.play_key"))
        object.__setattr__(self, "evidence_epoch", require_text(self.evidence_epoch, "fingerprint.evidence_epoch"))
        rows = tuple(sorted(self.metrics, key=lambda row: row.definition.metric_id))
        if len({row.definition.metric_id for row in rows}) != len(rows):
            raise ValueError("fingerprint metrics must be unique")
        score = require_finite(self.aggregate_score, "fingerprint.aggregate_score")
        if not 0 <= score <= 1:
            raise ValueError("fingerprint aggregate_score must be in [0, 1]")
        object.__setattr__(self, "metrics", rows)
        object.__setattr__(self, "missing_optional_metrics", tuple(sorted(set(self.missing_optional_metrics))))
        object.__setattr__(self, "aggregate_score", score)
        object.__setattr__(self, "fingerprint_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-entity-fingerprint-v1",
            "fingerprint_id": self.fingerprint_id,
            "schema_version": self.schema_version,
            "entity": self.entity.to_dict(),
            "play_key": self.play_key,
            "evidence_epoch": self.evidence_epoch,
            "metrics": [row.to_dict() for row in self.metrics],
            "missing_optional_metrics": list(self.missing_optional_metrics),
            "aggregate_score": self.aggregate_score,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "fingerprint_sha256": self.fingerprint_sha256}


@dataclass(frozen=True, slots=True)
class PremiumEstimate:
    estimate_id: str
    annualized_premium: float
    downside_return: float
    weight: float
    horizon_days: int
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "estimate_id", require_text(self.estimate_id, "premium.estimate_id"))
        object.__setattr__(self, "annualized_premium", require_finite(self.annualized_premium, "premium.annualized_premium"))
        object.__setattr__(self, "downside_return", require_finite(self.downside_return, "premium.downside_return"))
        weight = require_finite(self.weight, "premium.weight")
        if weight <= 0:
            raise ValueError("premium weight must be positive")
        object.__setattr__(self, "weight", weight)
        if isinstance(self.horizon_days, bool) or int(self.horizon_days) < 1:
            raise ValueError("premium horizon_days must be positive")
        object.__setattr__(self, "horizon_days", int(self.horizon_days))
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "premium source ref"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimate_id": self.estimate_id,
            "annualized_premium": self.annualized_premium,
            "downside_return": self.downside_return,
            "weight": self.weight,
            "horizon_days": self.horizon_days,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class MarketStateCommittee:
    committee_id: str
    as_of: str
    horizon_days: int
    estimates: tuple[PremiumEstimate, ...]
    weighted_premium: float = field(init=False)
    weighted_downside: float = field(init=False)
    premium_dispersion: float = field(init=False)
    lower_premium: float = field(init=False)
    upper_premium: float = field(init=False)
    committee_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "committee_id", require_text(self.committee_id, "committee_id"))
        object.__setattr__(self, "as_of", canonical_timestamp(self.as_of, "committee.as_of"))
        if isinstance(self.horizon_days, bool) or int(self.horizon_days) < 1:
            raise ValueError("committee horizon_days must be positive")
        object.__setattr__(self, "horizon_days", int(self.horizon_days))
        rows = tuple(sorted(self.estimates, key=lambda row: row.estimate_id))
        if not rows or len({row.estimate_id for row in rows}) != len(rows):
            raise ValueError("premium estimates must be nonempty and unique")
        if any(row.horizon_days != self.horizon_days for row in rows):
            raise ValueError("premium estimate horizon must match the committee")
        total = sum(row.weight for row in rows)
        premium = sum(row.weight * row.annualized_premium for row in rows) / total
        downside = sum(row.weight * row.downside_return for row in rows) / total
        dispersion = math.sqrt(sum(
            row.weight * (row.annualized_premium - premium) ** 2 for row in rows
        ) / total)
        object.__setattr__(self, "estimates", rows)
        object.__setattr__(self, "weighted_premium", premium)
        object.__setattr__(self, "weighted_downside", downside)
        object.__setattr__(self, "premium_dispersion", dispersion)
        object.__setattr__(self, "lower_premium", min(row.annualized_premium for row in rows))
        object.__setattr__(self, "upper_premium", max(row.annualized_premium for row in rows))
        object.__setattr__(self, "committee_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-market-state-committee-v1",
            "committee_id": self.committee_id,
            "as_of": self.as_of,
            "horizon_days": self.horizon_days,
            "estimates": [row.to_dict() for row in self.estimates],
            "weighted_premium": self.weighted_premium,
            "weighted_downside": self.weighted_downside,
            "premium_dispersion": self.premium_dispersion,
            "lower_premium": self.lower_premium,
            "upper_premium": self.upper_premium,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "committee_sha256": self.committee_sha256}


@dataclass(frozen=True, slots=True)
class InvestmentThesis:
    thesis_id: str
    version: str
    entity_id: str
    play_key: str
    evidence_epoch: str
    claim: str
    mechanism_ids: tuple[str, ...]
    catalysts: tuple[str, ...]
    falsifiers: tuple[str, ...]
    source_refs: tuple[str, ...]
    thesis_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("thesis_id", "version", "entity_id", "play_key", "evidence_epoch", "claim"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"thesis.{attr}"))
        object.__setattr__(self, "mechanism_ids", require_refs(self.mechanism_ids, "thesis mechanism"))
        object.__setattr__(self, "catalysts", tuple(require_text(row, "thesis catalyst") for row in self.catalysts))
        object.__setattr__(self, "falsifiers", require_refs(self.falsifiers, "thesis falsifier"))
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "thesis source ref"))
        object.__setattr__(self, "thesis_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-investment-thesis-v1",
            "thesis_id": self.thesis_id,
            "version": self.version,
            "entity_id": self.entity_id,
            "play_key": self.play_key,
            "evidence_epoch": self.evidence_epoch,
            "claim": self.claim,
            "mechanism_ids": list(self.mechanism_ids),
            "catalysts": list(self.catalysts),
            "falsifiers": list(self.falsifiers),
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "thesis_sha256": self.thesis_sha256}


@dataclass(frozen=True, slots=True)
class UnderwritingCase:
    """Decision challenge that binds outside view and action threshold to a thesis."""

    case_id: str
    entity_id: str
    thesis_id: str
    evidence_epoch: str
    outside_view_reference: str
    outside_view_base_rate: float
    failure_sequence: tuple[str, ...]
    hurdle_rate: float
    next_best_alternative: str
    rival_view: str
    decisive_observation: str
    action_condition_id: str
    source_refs: tuple[str, ...]
    case_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in (
            "case_id", "entity_id", "thesis_id", "evidence_epoch",
            "outside_view_reference", "next_best_alternative", "rival_view",
            "decisive_observation", "action_condition_id",
        ):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"underwriting.{attr}"))
        base_rate = require_finite(self.outside_view_base_rate, "underwriting.outside_view_base_rate")
        if not 0 <= base_rate <= 1:
            raise ValueError("underwriting outside-view base rate must be in [0, 1]")
        hurdle = require_finite(self.hurdle_rate, "underwriting.hurdle_rate")
        if hurdle <= -1:
            raise ValueError("underwriting hurdle rate must exceed -100 percent")
        sequence = tuple(require_text(row, "underwriting failure step") for row in self.failure_sequence)
        if len(sequence) < 2:
            raise ValueError("underwriting failure sequence requires at least two steps")
        object.__setattr__(self, "outside_view_base_rate", base_rate)
        object.__setattr__(self, "hurdle_rate", hurdle)
        object.__setattr__(self, "failure_sequence", sequence)
        object.__setattr__(self, "source_refs", require_refs(
            self.source_refs, "underwriting source ref"
        ))
        object.__setattr__(self, "case_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-underwriting-case-v1",
            "case_id": self.case_id,
            "entity_id": self.entity_id,
            "thesis_id": self.thesis_id,
            "evidence_epoch": self.evidence_epoch,
            "outside_view_reference": self.outside_view_reference,
            "outside_view_base_rate": self.outside_view_base_rate,
            "failure_sequence": list(self.failure_sequence),
            "hurdle_rate": self.hurdle_rate,
            "next_best_alternative": self.next_best_alternative,
            "rival_view": self.rival_view,
            "decisive_observation": self.decisive_observation,
            "action_condition_id": self.action_condition_id,
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "case_sha256": self.case_sha256}


@dataclass(frozen=True, slots=True)
class ThesisReviewPacket:
    packet_id: str
    as_of: str
    entity: EntityRef
    play: InvestmentPlay
    thesis: InvestmentThesis
    underwriting_sha256: str
    fingerprint_sha256: str
    market_state_sha256: str
    calculations: tuple[tuple[str, float], ...]
    source_refs: tuple[str, ...]
    packet_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", require_text(self.packet_id, "packet_id"))
        object.__setattr__(self, "as_of", canonical_timestamp(self.as_of, "packet.as_of"))
        object.__setattr__(self, "underwriting_sha256", require_text(
            self.underwriting_sha256, "packet.underwriting_sha256"
        ))
        object.__setattr__(self, "fingerprint_sha256", require_text(self.fingerprint_sha256, "packet.fingerprint_sha256"))
        object.__setattr__(self, "market_state_sha256", require_text(self.market_state_sha256, "packet.market_state_sha256"))
        calculations = tuple(sorted(
            (require_text(name, "calculation name"), require_finite(value, f"calculation.{name}"))
            for name, value in self.calculations
        ))
        object.__setattr__(self, "calculations", calculations)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "packet source ref"))
        if self.thesis.entity_id != self.entity.entity_id:
            raise ValueError("review packet thesis and entity identities differ")
        if self.thesis.play_key != self.play.play_key:
            raise ValueError("review packet thesis and play identities differ")
        object.__setattr__(self, "packet_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-investment-review-packet-v1",
            "packet_id": self.packet_id,
            "as_of": self.as_of,
            "entity": self.entity.to_dict(),
            "play": self.play.to_dict(),
            "thesis": self.thesis.to_dict(),
            "underwriting_sha256": self.underwriting_sha256,
            "fingerprint_sha256": self.fingerprint_sha256,
            "market_state_sha256": self.market_state_sha256,
            "calculations": dict(self.calculations),
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "packet_sha256": self.packet_sha256}


@dataclass(frozen=True, slots=True)
class PositionActionSpec:
    action_id: str
    kind: PositionActionKind
    description: str
    target_weight: float | None
    weight_delta: float | None
    primitive_cost: float
    irreversibility: float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", require_text(self.action_id, "action.action_id"))
        object.__setattr__(self, "description", require_text(self.description, "action.description"))
        if self.kind not in {"watch", "start", "add", "hold", "trim", "exit", "hedge"}:
            raise ValueError(f"unsupported position action kind: {self.kind}")
        target = None if self.target_weight is None else require_finite(self.target_weight, "action.target_weight")
        delta = None if self.weight_delta is None else require_finite(self.weight_delta, "action.weight_delta")
        if (target is None) == (delta is None):
            raise ValueError("position action requires exactly one of target_weight or weight_delta")
        object.__setattr__(self, "target_weight", target)
        object.__setattr__(self, "weight_delta", delta)
        for attr in ("primitive_cost", "irreversibility"):
            value = require_finite(getattr(self, attr), f"action.{attr}")
            if value < 0:
                raise ValueError(f"action {attr} cannot be negative")
            object.__setattr__(self, attr, value)
        object.__setattr__(self, "evidence_refs", require_refs(self.evidence_refs, "action evidence ref"))

    def target_from(self, current_weight: float) -> float:
        return self.target_weight if self.target_weight is not None else current_weight + float(self.weight_delta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind,
            "description": self.description,
            "target_weight": self.target_weight,
            "weight_delta": self.weight_delta,
            "primitive_cost": self.primitive_cost,
            "irreversibility": self.irreversibility,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class InvestmentObjectiveSpec:
    objective_id: str
    path: str
    direction: ObjectiveDirection
    scale: float
    utility_weight: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective_id", require_text(self.objective_id, "objective.objective_id"))
        object.__setattr__(self, "path", require_text(self.path, "objective.path"))
        if self.direction not in {"maximize", "minimize"}:
            raise ValueError("objective direction must be maximize or minimize")
        scale = require_finite(self.scale, "objective.scale")
        weight = require_finite(self.utility_weight, "objective.utility_weight")
        if scale <= 0:
            raise ValueError("objective scale must be positive")
        if weight < 0:
            raise ValueError("objective utility_weight cannot be negative")
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "utility_weight", weight)

    def utility_component(self, frontier_value: float) -> float:
        return self.utility_weight * frontier_value / self.scale

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "path": self.path,
            "direction": self.direction,
            "scale": self.scale,
            "utility_weight": self.utility_weight,
        }


def mapping_rows(value: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted(
        (require_text(name, "state coordinate"), require_finite(raw, f"state.{name}"))
        for name, raw in value.items()
    ))


__all__ = [
    "EntityFingerprint",
    "EntityRef",
    "FingerprintMetric",
    "FingerprintMetricDefinition",
    "InvestmentObjectiveSpec",
    "InvestmentProfileLifecycle",
    "InvestmentPlay",
    "InvestmentThesis",
    "MarketStateCommittee",
    "MetricObservation",
    "PointInTimeSnapshot",
    "PositionActionSpec",
    "PremiumEstimate",
    "ThesisReviewPacket",
    "UnderwritingCase",
    "canonical_timestamp",
    "mapping_rows",
    "require_finite",
    "require_refs",
    "require_text",
    "timestamp_key",
]
