"""Paper-book transitions and prospective economic settlement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import (
    EntityRef,
    InvestmentPlay,
    PositionActionSpec,
    canonical_timestamp,
    require_finite,
    require_text,
    timestamp_key,
)


@dataclass(frozen=True, slots=True)
class PaperPosition:
    entity_id: str
    quantity: float
    last_price: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "position.entity_id"))
        object.__setattr__(self, "quantity", require_finite(self.quantity, "position.quantity"))
        price = require_finite(self.last_price, "position.last_price")
        if price <= 0:
            raise ValueError("position last_price must be positive")
        object.__setattr__(self, "last_price", price)

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price

    def to_dict(self) -> dict[str, float | str]:
        return {
            "entity_id": self.entity_id,
            "quantity": self.quantity,
            "last_price": self.last_price,
            "market_value": self.market_value,
        }


@dataclass(frozen=True, slots=True)
class PaperBook:
    book_id: str
    as_of: str
    currency: str
    cash: float
    positions: tuple[PaperPosition, ...]
    book_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "book_id", require_text(self.book_id, "book.book_id"))
        object.__setattr__(self, "as_of", canonical_timestamp(self.as_of, "book.as_of"))
        object.__setattr__(self, "currency", require_text(self.currency, "book.currency"))
        object.__setattr__(self, "cash", require_finite(self.cash, "book.cash"))
        rows = tuple(sorted(self.positions, key=lambda row: row.entity_id))
        if len({row.entity_id for row in rows}) != len(rows):
            raise ValueError("paper-book positions must have unique entity identities")
        object.__setattr__(self, "positions", rows)
        object.__setattr__(self, "book_sha256", stable_sha256(self._payload()))

    @property
    def total_value(self) -> float:
        return self.cash + sum(row.market_value for row in self.positions)

    def position(self, entity_id: str) -> PaperPosition | None:
        return next((row for row in self.positions if row.entity_id == entity_id), None)

    def weight(self, entity_id: str) -> float:
        if self.total_value <= 0:
            raise ValueError("paper book must have positive total value")
        position = self.position(entity_id)
        return (position.market_value if position else 0.0) / self.total_value

    def marked_value(self, prices: Mapping[str, float]) -> float:
        value = self.cash
        for position in self.positions:
            if position.entity_id not in prices:
                raise ValueError(f"outcome is missing price for {position.entity_id}")
            price = require_finite(prices[position.entity_id], f"price.{position.entity_id}")
            if price <= 0:
                raise ValueError(f"outcome price must be positive: {position.entity_id}")
            value += position.quantity * price
        return value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-paper-book-v1",
            "book_id": self.book_id,
            "as_of": self.as_of,
            "currency": self.currency,
            "cash": self.cash,
            "positions": [row.to_dict() for row in self.positions],
            "total_value": self.total_value,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "book_sha256": self.book_sha256}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PaperBook":
        return cls(
            book_id=str(payload["book_id"]),
            as_of=str(payload["as_of"]),
            currency=str(payload["currency"]),
            cash=float(payload["cash"]),
            positions=tuple(
                PaperPosition(
                    entity_id=str(row["entity_id"]),
                    quantity=float(row["quantity"]),
                    last_price=float(row["last_price"]),
                )
                for row in payload.get("positions", [])
            ),
        )


@dataclass(frozen=True, slots=True)
class PositionProposal:
    proposal_id: str
    decision_id: str
    entity_id: str
    action_id: str
    action_kind: str
    as_of: str
    current_weight: float
    target_weight: float
    price: float
    trade_quantity: float
    trade_notional: float
    estimated_cost: float
    book_before_sha256: str
    book_after_sha256: str
    authority: str = "paper"
    proposal_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in (
            "proposal_id", "decision_id", "entity_id", "action_id", "action_kind",
            "book_before_sha256", "book_after_sha256", "authority",
        ):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"proposal.{attr}"))
        object.__setattr__(self, "as_of", canonical_timestamp(self.as_of, "proposal.as_of"))
        for attr in (
            "current_weight", "target_weight", "price", "trade_quantity",
            "trade_notional", "estimated_cost",
        ):
            object.__setattr__(self, attr, require_finite(getattr(self, attr), f"proposal.{attr}"))
        if self.price <= 0 or self.estimated_cost < 0:
            raise ValueError("proposal price must be positive and cost nonnegative")
        if self.authority != "paper":
            raise ValueError("this compiler permits paper authority only")
        object.__setattr__(self, "proposal_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-position-proposal-v1",
            "proposal_id": self.proposal_id,
            "decision_id": self.decision_id,
            "entity_id": self.entity_id,
            "action_id": self.action_id,
            "action_kind": self.action_kind,
            "as_of": self.as_of,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "price": self.price,
            "trade_quantity": self.trade_quantity,
            "trade_notional": self.trade_notional,
            "estimated_cost": self.estimated_cost,
            "book_before_sha256": self.book_before_sha256,
            "book_after_sha256": self.book_after_sha256,
            "authority": self.authority,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_sha256": self.proposal_sha256}


def apply_paper_action(
    *,
    decision_id: str,
    as_of: str,
    entity: EntityRef,
    play: InvestmentPlay,
    book: PaperBook,
    action: PositionActionSpec,
    price: float,
) -> tuple[PositionProposal, PaperBook]:
    """Apply one selected action to a paper book and charge declared costs."""
    if book.currency != entity.currency:
        raise ValueError("entity and paper-book currencies differ")
    if timestamp_key(book.as_of) > timestamp_key(canonical_timestamp(as_of, "decision.as_of")):
        raise ValueError("paper book is dated after the decision")
    current_price = require_finite(price, "decision price")
    if current_price <= 0:
        raise ValueError("decision price must be positive")
    starting_value = book.total_value
    if starting_value <= 0:
        raise ValueError("paper book must have positive total value")
    current_weight = book.weight(entity.entity_id)
    target_weight = action.target_from(current_weight)
    if target_weight < play.min_weight - 1e-12 or target_weight > play.max_weight + 1e-12:
        raise ValueError(
            f"action {action.action_id} target weight {target_weight:.6f} is outside "
            f"[{play.min_weight:.6f}, {play.max_weight:.6f}]"
        )
    if not play.allow_short and target_weight < -1e-12:
        raise ValueError("a long-only play cannot create a short position")
    current = book.position(entity.entity_id)
    current_notional = current.market_value if current else 0.0
    target_notional = target_weight * starting_value
    trade_notional = target_notional - current_notional
    trade_quantity = trade_notional / current_price
    estimated_cost = abs(trade_notional) * play.transaction_cost_bps / 10_000
    positions = {row.entity_id: row for row in book.positions}
    quantity_after = (current.quantity if current else 0.0) + trade_quantity
    if abs(quantity_after) <= 1e-12:
        positions.pop(entity.entity_id, None)
    else:
        positions[entity.entity_id] = PaperPosition(
            entity_id=entity.entity_id,
            quantity=quantity_after,
            last_price=current_price,
        )
    book_after = PaperBook(
        book_id=f"{book.book_id}@{decision_id}",
        as_of=as_of,
        currency=book.currency,
        cash=book.cash - trade_notional - estimated_cost,
        positions=tuple(positions.values()),
    )
    proposal = PositionProposal(
        proposal_id=f"{decision_id}:{action.action_id}",
        decision_id=decision_id,
        entity_id=entity.entity_id,
        action_id=action.action_id,
        action_kind=action.kind,
        as_of=as_of,
        current_weight=current_weight,
        target_weight=target_weight,
        price=current_price,
        trade_quantity=trade_quantity,
        trade_notional=trade_notional,
        estimated_cost=estimated_cost,
        book_before_sha256=book.book_sha256,
        book_after_sha256=book_after.book_sha256,
    )
    return proposal, book_after


@dataclass(frozen=True, slots=True)
class OutcomeSnapshot:
    decision_record_sha256: str
    observed_at: str
    available_at: str
    prices: tuple[tuple[str, float], ...]
    source_refs: tuple[str, ...]
    outcome_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        digest = require_text(self.decision_record_sha256, "outcome.decision_record_sha256")
        if len(digest) != 64:
            raise ValueError("outcome decision_record_sha256 must be a SHA-256 digest")
        object.__setattr__(self, "decision_record_sha256", digest)
        object.__setattr__(self, "observed_at", canonical_timestamp(self.observed_at, "outcome.observed_at"))
        object.__setattr__(self, "available_at", canonical_timestamp(self.available_at, "outcome.available_at"))
        if timestamp_key(self.available_at) < timestamp_key(self.observed_at):
            raise ValueError("outcome available_at cannot precede observed_at")
        rows = tuple(sorted(
            (require_text(entity_id, "outcome price entity"), require_finite(value, f"outcome.price.{entity_id}"))
            for entity_id, value in self.prices
        ))
        if not rows or len({entity_id for entity_id, _value in rows}) != len(rows):
            raise ValueError("outcome prices must be nonempty and unique")
        if any(value <= 0 for _entity_id, value in rows):
            raise ValueError("outcome prices must be positive")
        refs = tuple(sorted({require_text(ref, "outcome source ref") for ref in self.source_refs}))
        if not refs:
            raise ValueError("outcome source refs must be nonempty")
        object.__setattr__(self, "prices", rows)
        object.__setattr__(self, "source_refs", refs)
        object.__setattr__(self, "outcome_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-investment-outcome-v1",
            "decision_record_sha256": self.decision_record_sha256,
            "observed_at": self.observed_at,
            "available_at": self.available_at,
            "prices": dict(self.prices),
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_sha256": self.outcome_sha256}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OutcomeSnapshot":
        if payload.get("schema") != "jaggedthoughts-investment-outcome-v1":
            raise ValueError("outcome schema must be jaggedthoughts-investment-outcome-v1")
        return cls(
            decision_record_sha256=str(payload["decision_record_sha256"]),
            observed_at=str(payload["observed_at"]),
            available_at=str(payload["available_at"]),
            prices=tuple(
                (str(entity_id), float(value))
                for entity_id, value in dict(payload.get("prices") or {}).items()
            ),
            source_refs=tuple(str(ref) for ref in payload.get("source_refs", [])),
        )


@dataclass(frozen=True, slots=True)
class EconomicScorecard:
    decision_id: str
    decision_record_sha256: str
    outcome_sha256: str
    starting_value: float
    ending_paper_value: float
    ending_no_action_value: float
    paper_return: float
    no_action_return: float
    benchmark_return: float
    net_excess_return: float
    incremental_return_vs_no_action: float
    transaction_cost: float
    scorecard_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", require_text(self.decision_id, "scorecard.decision_id"))
        for attr in ("decision_record_sha256", "outcome_sha256"):
            value = require_text(getattr(self, attr), f"scorecard.{attr}")
            if len(value) != 64:
                raise ValueError(f"scorecard {attr} must be a SHA-256 digest")
            object.__setattr__(self, attr, value)
        for attr in (
            "starting_value", "ending_paper_value", "ending_no_action_value",
            "paper_return", "no_action_return", "benchmark_return",
            "net_excess_return", "incremental_return_vs_no_action", "transaction_cost",
        ):
            object.__setattr__(self, attr, require_finite(getattr(self, attr), f"scorecard.{attr}"))
        if self.starting_value <= 0 or self.transaction_cost < 0:
            raise ValueError("scorecard requires positive starting value and nonnegative cost")
        object.__setattr__(self, "scorecard_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-investment-economic-scorecard-v1",
            "decision_id": self.decision_id,
            "decision_record_sha256": self.decision_record_sha256,
            "outcome_sha256": self.outcome_sha256,
            "starting_value": self.starting_value,
            "ending_paper_value": self.ending_paper_value,
            "ending_no_action_value": self.ending_no_action_value,
            "paper_return": self.paper_return,
            "no_action_return": self.no_action_return,
            "benchmark_return": self.benchmark_return,
            "net_excess_return": self.net_excess_return,
            "incremental_return_vs_no_action": self.incremental_return_vs_no_action,
            "transaction_cost": self.transaction_cost,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "scorecard_sha256": self.scorecard_sha256}


def settle_paper_decision(
    decision: Mapping[str, Any],
    outcome: OutcomeSnapshot,
) -> EconomicScorecard:
    """Score a frozen decision against later prices and two counterfactuals."""
    payload = dict(decision)
    declared_digest = str(payload.pop("decision_record_sha256", ""))
    computed_digest = stable_sha256(payload)
    if declared_digest != computed_digest:
        raise ValueError("decision record content hash mismatch")
    if outcome.decision_record_sha256 != declared_digest:
        raise ValueError("outcome is bound to a different decision record")
    decision_as_of = canonical_timestamp(payload["as_of"], "decision.as_of")
    if timestamp_key(outcome.observed_at) <= timestamp_key(decision_as_of):
        raise ValueError("outcome must occur after the decision as_of")
    book_before = PaperBook.from_dict(payload["paper_book_before"])
    book_after = PaperBook.from_dict(payload["paper_book_after"])
    proposal = payload["position_proposal"]
    prices = dict(outcome.prices)
    benchmark_id = str(payload["play"]["benchmark_id"])
    if benchmark_id not in prices:
        raise ValueError(f"outcome is missing benchmark price for {benchmark_id}")
    benchmark_start = require_finite(payload["benchmark_start_price"], "benchmark_start_price")
    if benchmark_start <= 0:
        raise ValueError("benchmark start price must be positive")
    starting_value = book_before.total_value
    ending_paper = book_after.marked_value(prices)
    ending_no_action = book_before.marked_value(prices)
    paper_return = ending_paper / starting_value - 1
    no_action_return = ending_no_action / starting_value - 1
    benchmark_return = prices[benchmark_id] / benchmark_start - 1
    return EconomicScorecard(
        decision_id=str(payload["decision_id"]),
        decision_record_sha256=declared_digest,
        outcome_sha256=outcome.outcome_sha256,
        starting_value=starting_value,
        ending_paper_value=ending_paper,
        ending_no_action_value=ending_no_action,
        paper_return=paper_return,
        no_action_return=no_action_return,
        benchmark_return=benchmark_return,
        net_excess_return=paper_return - benchmark_return,
        incremental_return_vs_no_action=paper_return - no_action_return,
        transaction_cost=require_finite(proposal["estimated_cost"], "proposal.estimated_cost"),
    )


def positions_from_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[PaperPosition, ...]:
    return tuple(
        PaperPosition(
            entity_id=str(row["entity_id"]),
            quantity=float(row["quantity"]),
            last_price=float(row["last_price"]),
        )
        for row in rows
    )


__all__ = [
    "EconomicScorecard",
    "OutcomeSnapshot",
    "PaperBook",
    "PaperPosition",
    "PositionProposal",
    "apply_paper_action",
    "positions_from_rows",
    "settle_paper_decision",
]
