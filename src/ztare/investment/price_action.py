"""Chronology-safe scoring for price-law and symbolic-regression proposals.

This module evaluates frozen predictions.  It does not fit laws, search model
families, or promote a trading rule.  A Lagrangian-labelled candidate must
predict a second observable in addition to return so that a price-only curve
fit cannot masquerade as a dynamical explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_refs, require_text, timestamp_key


PRICE_ACTION_CANDIDATE_SCHEMA = "jaggedthoughts-price-action-candidate-v1"
PRICE_ACTION_OUTCOME_SCHEMA = "jaggedthoughts-price-action-outcome-v1"


@dataclass(frozen=True, slots=True)
class PricePrediction:
    entity_id: str
    start_at: str
    end_at: str
    predicted_return: float
    predicted_linked_change: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "prediction.entity_id"))
        start = canonical_timestamp(self.start_at, "prediction.start_at")
        end = canonical_timestamp(self.end_at, "prediction.end_at")
        if timestamp_key(end) <= timestamp_key(start):
            raise ValueError("prediction end_at must be after start_at")
        object.__setattr__(self, "start_at", start)
        object.__setattr__(self, "end_at", end)
        object.__setattr__(self, "predicted_return", require_finite(self.predicted_return, "prediction.predicted_return"))
        if self.predicted_linked_change is not None:
            object.__setattr__(
                self,
                "predicted_linked_change",
                require_finite(self.predicted_linked_change, "prediction.predicted_linked_change"),
            )


@dataclass(frozen=True, slots=True)
class PriceActionCandidate:
    candidate_id: str
    law_family: str
    trial_family_id: str
    trained_through: str
    issued_at: str
    horizon_days: int
    complexity_terms: int
    predictions: tuple[PricePrediction, ...]
    source_refs: tuple[str, ...]
    candidate_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("candidate_id", "law_family", "trial_family_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"candidate.{attr}"))
        trained = canonical_timestamp(self.trained_through, "candidate.trained_through")
        issued = canonical_timestamp(self.issued_at, "candidate.issued_at")
        if timestamp_key(issued) < timestamp_key(trained):
            raise ValueError("candidate issued_at cannot precede trained_through")
        if self.horizon_days < 1 or self.complexity_terms < 1:
            raise ValueError("candidate horizon_days and complexity_terms must be positive")
        rows = tuple(sorted(self.predictions, key=lambda row: row.entity_id))
        if not rows or len({row.entity_id for row in rows}) != len(rows):
            raise ValueError("candidate predictions must be nonempty and entity-unique")
        if any(timestamp_key(row.start_at) < timestamp_key(issued) for row in rows):
            raise ValueError("candidate contains a prediction period before issuance")
        if self.law_family.lower() == "lagrangian" and any(
            row.predicted_linked_change is None for row in rows
        ):
            raise ValueError("a Lagrangian candidate must predict a linked observable")
        object.__setattr__(self, "trained_through", trained)
        object.__setattr__(self, "issued_at", issued)
        object.__setattr__(self, "predictions", rows)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "candidate source ref"))
        object.__setattr__(self, "candidate_sha256", stable_sha256(self.to_dict(include_hash=False)))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        body = {
            "schema": PRICE_ACTION_CANDIDATE_SCHEMA,
            "candidate_id": self.candidate_id,
            "law_family": self.law_family,
            "trial_family_id": self.trial_family_id,
            "trained_through": self.trained_through,
            "issued_at": self.issued_at,
            "horizon_days": self.horizon_days,
            "complexity_terms": self.complexity_terms,
            "predictions": [
                {
                    "entity_id": row.entity_id,
                    "start_at": row.start_at,
                    "end_at": row.end_at,
                    "predicted_return": row.predicted_return,
                    "predicted_linked_change": row.predicted_linked_change,
                }
                for row in self.predictions
            ],
            "source_refs": list(self.source_refs),
        }
        return {**body, "candidate_sha256": self.candidate_sha256} if include_hash else body

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PriceActionCandidate":
        if payload.get("schema") != PRICE_ACTION_CANDIDATE_SCHEMA:
            raise ValueError(f"candidate schema must be {PRICE_ACTION_CANDIDATE_SCHEMA}")
        return cls(
            candidate_id=str(payload["candidate_id"]),
            law_family=str(payload["law_family"]),
            trial_family_id=str(payload["trial_family_id"]),
            trained_through=str(payload["trained_through"]),
            issued_at=str(payload["issued_at"]),
            horizon_days=int(payload["horizon_days"]),
            complexity_terms=int(payload["complexity_terms"]),
            predictions=tuple(
                PricePrediction(
                    entity_id=str(row["entity_id"]),
                    start_at=str(row["start_at"]),
                    end_at=str(row["end_at"]),
                    predicted_return=float(row["predicted_return"]),
                    predicted_linked_change=(
                        None if row.get("predicted_linked_change") is None
                        else float(row["predicted_linked_change"])
                    ),
                )
                for row in payload.get("predictions", [])
            ),
            source_refs=tuple(str(row) for row in payload.get("source_refs", [])),
        )


def _actual_rows(payload: Mapping[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    if payload.get("schema") != PRICE_ACTION_OUTCOME_SCHEMA:
        raise ValueError(f"outcome schema must be {PRICE_ACTION_OUTCOME_SCHEMA}")
    available = canonical_timestamp(payload.get("available_at"), "price outcome.available_at")
    rows: dict[str, dict[str, Any]] = {}
    for raw in payload.get("rows", []):
        entity_id = require_text(raw.get("entity_id"), "price outcome.entity_id")
        if entity_id in rows:
            raise ValueError(f"duplicate price outcome entity: {entity_id}")
        start_at = canonical_timestamp(raw.get("start_at"), "price outcome.start_at")
        end_at = canonical_timestamp(raw.get("end_at"), "price outcome.end_at")
        start_price = require_finite(raw.get("start_price"), "price outcome.start_price")
        end_price = require_finite(raw.get("end_price"), "price outcome.end_price")
        if start_price <= 0 or end_price <= 0 or timestamp_key(end_at) <= timestamp_key(start_at):
            raise ValueError("price outcome requires positive prices and an increasing period")
        if timestamp_key(available) < timestamp_key(end_at):
            raise ValueError("price outcome was not available by its declared availability time")
        linked_change = None
        if raw.get("linked_start") is not None or raw.get("linked_end") is not None:
            linked_start = require_finite(raw.get("linked_start"), "price outcome.linked_start")
            linked_end = require_finite(raw.get("linked_end"), "price outcome.linked_end")
            linked_change = linked_end - linked_start
        rows[entity_id] = {
            "start_at": start_at,
            "end_at": end_at,
            "actual_return": end_price / start_price - 1,
            "linked_change": linked_change,
        }
    if not rows:
        raise ValueError("price outcome rows must be nonempty")
    return available, rows


def _metrics(
    candidate: PriceActionCandidate,
    outcomes: Mapping[str, Mapping[str, Any]],
    *,
    transaction_cost_bps: float,
) -> dict[str, Any]:
    errors: list[float] = []
    directional: list[float] = []
    strategy: list[float] = []
    linked_errors: list[float] = []
    for prediction in candidate.predictions:
        actual = outcomes.get(prediction.entity_id)
        if actual is None:
            raise ValueError(f"outcome is missing candidate entity: {prediction.entity_id}")
        if prediction.start_at != actual["start_at"] or prediction.end_at != actual["end_at"]:
            raise ValueError(f"candidate/outcome period mismatch: {prediction.entity_id}")
        actual_return = float(actual["actual_return"])
        errors.append(abs(prediction.predicted_return - actual_return))
        predicted_sign = 1 if prediction.predicted_return > 0 else -1 if prediction.predicted_return < 0 else 0
        actual_sign = 1 if actual_return > 0 else -1 if actual_return < 0 else 0
        directional.append(float(predicted_sign == actual_sign))
        strategy.append(predicted_sign * actual_return - abs(predicted_sign) * transaction_cost_bps / 10_000)
        if prediction.predicted_linked_change is not None:
            if actual["linked_change"] is None:
                raise ValueError(f"linked outcome is missing: {prediction.entity_id}")
            linked_errors.append(abs(prediction.predicted_linked_change - float(actual["linked_change"])))
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_sha256": candidate.candidate_sha256,
        "mean_absolute_return_error": sum(errors) / len(errors),
        "directional_accuracy": sum(directional) / len(directional),
        "mean_net_directional_return": sum(strategy) / len(strategy),
        "mean_absolute_linked_error": (
            sum(linked_errors) / len(linked_errors) if linked_errors else None
        ),
        "prediction_count": len(errors),
    }


def evaluate_price_action_candidate(
    candidate: PriceActionCandidate,
    outcome: Mapping[str, Any],
    *,
    baselines: Sequence[PriceActionCandidate],
    transaction_cost_bps: float,
) -> dict[str, Any]:
    """Compare one frozen candidate with at least one frozen control."""
    if not baselines:
        raise ValueError("price-action evaluation requires at least one baseline")
    costs = require_finite(transaction_cost_bps, "transaction_cost_bps")
    if costs < 0:
        raise ValueError("transaction_cost_bps cannot be negative")
    available, actual = _actual_rows(outcome)
    candidates = (candidate, *baselines)
    entity_set = {row.entity_id for row in candidate.predictions}
    for model in candidates:
        if timestamp_key(model.issued_at) >= timestamp_key(available):
            raise ValueError("price-action model must be frozen before outcome availability")
        if {row.entity_id for row in model.predictions} != entity_set:
            raise ValueError("candidate and baselines must predict the same entities")
    candidate_metrics = _metrics(candidate, actual, transaction_cost_bps=costs)
    baseline_metrics = tuple(
        _metrics(model, actual, transaction_cost_bps=costs) for model in baselines
    )
    best_mae = min(row["mean_absolute_return_error"] for row in baseline_metrics)
    best_return = max(row["mean_net_directional_return"] for row in baseline_metrics)
    beats_return_error = candidate_metrics["mean_absolute_return_error"] < best_mae
    beats_economic_control = candidate_metrics["mean_net_directional_return"] > best_return
    body = {
        "schema": "jaggedthoughts-price-action-evaluation-v1",
        "candidate": candidate.to_dict(),
        "baselines": [model.to_dict() for model in baselines],
        "outcome_sha256": stable_sha256(dict(outcome)),
        "outcome_available_at": available,
        "transaction_cost_bps": costs,
        "candidate_metrics": candidate_metrics,
        "baseline_metrics": list(baseline_metrics),
        "beats_return_error_control": beats_return_error,
        "beats_economic_control": beats_economic_control,
        "screen_pass": beats_return_error and beats_economic_control,
        "boundary": "A screen pass permits further prospective evaluation; it does not authorize capital.",
    }
    return {**body, "evaluation_sha256": stable_sha256(body)}


__all__ = [
    "PRICE_ACTION_CANDIDATE_SCHEMA",
    "PRICE_ACTION_OUTCOME_SCHEMA",
    "PriceActionCandidate",
    "PricePrediction",
    "evaluate_price_action_candidate",
]
