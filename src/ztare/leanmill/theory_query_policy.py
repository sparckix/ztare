"""Information-priced boundary queries over a semantic-theory committee."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Hashable, Mapping, Sequence

from ztare.common.kernel_action_schema import KernelActionSchema
from ztare.research_signals import price_experiment


@dataclass(frozen=True)
class BoundaryQuery:
    query_id: str
    query_type: str
    predictions: Mapping[str, Hashable]
    cost_units: float
    target_mapping: str
    nearest_confuser: str
    falsifier: str
    verification_artifact: str
    novel_context: bool = True

    def to_kernel_action(self) -> KernelActionSchema:
        return KernelActionSchema(
            source_kind="frontier_theory_context",
            action_family="boundary_verification",
            action_name=self.query_type,
            source_summary=self.query_id,
            target_mapping=self.target_mapping,
            nearest_confuser=self.nearest_confuser,
            falsifier=self.falsifier,
            verification_artifact=self.verification_artifact,
            action_constraints=[f"cost_units={self.cost_units}"],
            evidence_basis="frozen finalist committee predictions",
            payload={
                "query_id": self.query_id,
                "predictions": dict(self.predictions),
            },
        )


@dataclass(frozen=True)
class PricedBoundaryQuery:
    query: BoundaryQuery
    identification: float
    compression_gain: float
    novelty: float
    information_per_cost: float

    def to_json(self) -> dict[str, Any]:
        return {
            "query_id": self.query.query_id,
            "query_type": self.query.query_type,
            "cost_units": self.query.cost_units,
            "identification": self.identification,
            "compression_gain": self.compression_gain,
            "novelty": self.novelty,
            "information_per_cost": self.information_per_cost,
            "kernel_action": self.query.to_kernel_action().to_dict(),
        }


def rank_boundary_queries(
    committee_ids: Sequence[str],
    queries: Sequence[BoundaryQuery],
    *,
    description_lengths: Mapping[str, int] | None = None,
) -> tuple[PricedBoundaryQuery, ...]:
    committee = tuple(str(row) for row in committee_ids)
    if not committee:
        raise ValueError("boundary query ranking requires a nonempty committee")
    lengths = dict(description_lengths or {})
    priced: list[PricedBoundaryQuery] = []
    for query in queries:
        if query.cost_units <= 0:
            raise ValueError("boundary query cost must be positive")
        if set(query.predictions) != set(committee):
            raise ValueError("query predictions must cover the committee exactly")
        components = price_experiment(
            committee,
            lambda member: query.predictions[member],
            lambda member: max(1, int(lengths.get(member, 1))),
            query.novel_context,
        )
        raw = (
            0.55 * components.identification
            + 0.35 * components.compression_gain
            + 0.10 * components.novelty
        )
        priced.append(
            PricedBoundaryQuery(
                query=query,
                identification=components.identification,
                compression_gain=components.compression_gain,
                novelty=components.novelty,
                information_per_cost=raw / query.cost_units,
            )
        )
    return tuple(sorted(priced, key=lambda row: (-row.information_per_cost, row.query.query_id)))


__all__ = ["BoundaryQuery", "PricedBoundaryQuery", "rank_boundary_queries"]
