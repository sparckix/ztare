"""Compatible forecast and observation units for protocol information yield."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Hashable

from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_experiment_protocol import (
    GuardedProtocolCandidate,
    GuardedProtocolPrice,
    ProtocolCost,
)


SCHEMA = "ztare-realized-protocol-information-yield-v1"
MEASURE_SHA256 = stable_sha256({
    "schema": SCHEMA,
    "quantity": "normalized_posterior_committee_reduction",
    "formula": "log2(prior_size/posterior_cell_size)/log2(prior_size)",
    "prior": "uniform_over_frozen_committee_members",
    "singleton_value": 0.0,
    "out_of_partition_value": 1.0,
})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _realized_yield(prior_size: int, posterior_size: int) -> float:
    if prior_size <= 1:
        return 0.0
    if posterior_size <= 0:
        return 1.0
    return math.log2(prior_size / posterior_size) / math.log2(prior_size)


@dataclass(frozen=True)
class ProtocolInformationYieldForecast:
    """Selection-time response partition in normalized reduction units."""

    protocol_id: str
    committee_sha256: str
    partition_sha256: str
    response_cells: tuple[tuple[str, tuple[str, ...]], ...]
    predicted_information_yield: float
    cost: ProtocolCost
    measure_sha256: str = MEASURE_SHA256

    def __post_init__(self) -> None:
        for name in (
            "protocol_id",
            "committee_sha256",
            "partition_sha256",
            "measure_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.measure_sha256 != MEASURE_SHA256:
            raise ValueError("unknown protocol information-yield measure")
        cells = tuple(sorted(
            (
                _nonempty(response_sha, "response_sha256"),
                tuple(sorted({
                    _nonempty(member, "committee_member_sha256")
                    for member in members
                })),
            )
            for response_sha, members in self.response_cells
        ))
        object.__setattr__(self, "response_cells", cells)
        if not cells or any(not members for _response, members in cells):
            raise ValueError("forecast response cells must be nonempty")
        member_ids = [
            member
            for _response, members in cells
            for member in members
        ]
        if len(member_ids) != len(set(member_ids)):
            raise ValueError(
                "forecast committee members must occupy exactly one cell"
            )
        expected_committee_sha = stable_sha256(tuple(sorted(member_ids)))
        if self.committee_sha256 != expected_committee_sha:
            raise ValueError("forecast committee identity drifted")
        partition = tuple(sorted(
            (members for _response, members in cells),
            key=lambda cell: (len(cell), cell),
        ))
        if self.partition_sha256 != stable_sha256(partition):
            raise ValueError("forecast partition identity drifted")
        predicted = float(self.predicted_information_yield)
        if (
            not math.isfinite(predicted)
            or predicted < 0.0
            or predicted > 1.0
        ):
            raise ValueError(
                "predicted_information_yield must lie in [0, 1]"
            )
        object.__setattr__(
            self,
            "predicted_information_yield",
            predicted,
        )
        if not math.isclose(
            predicted,
            self.expected_realized_information_yield,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "predicted identification does not match response partition"
            )

    @property
    def committee_size(self) -> int:
        return sum(len(members) for _response, members in self.response_cells)

    @property
    def response_class_count(self) -> int:
        return len(self.response_cells)

    @property
    def expected_realized_information_yield(self) -> float:
        prior = self.committee_size
        return sum(
            (len(members) / prior)
            * _realized_yield(prior, len(members))
            for _response, members in self.response_cells
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "protocol_information_yield_forecast",
            "protocol_id": self.protocol_id,
            "committee_sha256": self.committee_sha256,
            "partition_sha256": self.partition_sha256,
            "committee_size": self.committee_size,
            "response_class_count": self.response_class_count,
            "response_cells": [
                {
                    "response_sha256": response_sha,
                    "committee_member_sha256s": list(members),
                    "cell_size": len(members),
                }
                for response_sha, members in self.response_cells
            ],
            "predicted_information_yield": (
                self.predicted_information_yield
            ),
            "expected_realized_information_yield": (
                self.expected_realized_information_yield
            ),
            "measure_sha256": self.measure_sha256,
            "cost": self.cost.to_receipt(),
            "task_credit_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_protocol_information_yield_forecast(
    candidate: GuardedProtocolCandidate,
    price: GuardedProtocolPrice,
) -> ProtocolInformationYieldForecast:
    """Freeze the priced committee partition before intervention."""

    if candidate.protocol.protocol_id != price.protocol_id:
        raise ValueError("protocol candidate and price identity mismatch")
    if candidate.protocol != price.protocol:
        raise ValueError("protocol candidate and priced protocol drifted")
    committee = tuple(sorted(
        candidate.committee,
        key=lambda row: row.hypothesis_id,
    ))
    committee_sha = stable_sha256(tuple(
        row.hypothesis_id for row in committee
    ))
    if committee_sha != price.committee_sha256:
        raise ValueError("priced committee identity drifted")
    cells: dict[str, list[str]] = {}
    for member in committee:
        cells.setdefault(
            stable_sha256(member.response),
            [],
        ).append(member.hypothesis_id)
    response_cells = tuple(
        (
            response_sha,
            tuple(sorted(member_ids)),
        )
        for response_sha, member_ids in sorted(cells.items())
    )
    partition = tuple(sorted(
        (members for _response, members in response_cells),
        key=lambda cell: (len(cell), cell),
    ))
    if stable_sha256(partition) != price.partition_sha256:
        raise ValueError("priced response partition drifted")
    return ProtocolInformationYieldForecast(
        protocol_id=price.protocol_id,
        committee_sha256=price.committee_sha256,
        partition_sha256=price.partition_sha256,
        response_cells=response_cells,
        predicted_information_yield=price.identification,
        cost=price.cost,
    )


@dataclass(frozen=True)
class ProtocolInformationYieldObservation:
    """Evidence-owned realized cell reduction for one frozen forecast."""

    forecast_sha256: str
    protocol_id: str
    committee_sha256: str
    partition_sha256: str
    observed_response_sha256: str
    status: str
    posterior_cell_size: int
    observed_information_yield: float
    observation_evidence_ref: str
    measure_sha256: str = MEASURE_SHA256

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "protocol_information_yield_observation",
            "forecast_sha256": self.forecast_sha256,
            "protocol_id": self.protocol_id,
            "committee_sha256": self.committee_sha256,
            "partition_sha256": self.partition_sha256,
            "observed_response_sha256": (
                self.observed_response_sha256
            ),
            "status": self.status,
            "posterior_cell_size": self.posterior_cell_size,
            "observed_information_yield": (
                self.observed_information_yield
            ),
            "observation_evidence_ref": self.observation_evidence_ref,
            "measure_sha256": self.measure_sha256,
            "task_credit_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def observe_protocol_information_yield(
    forecast: ProtocolInformationYieldForecast,
    *,
    observed_response: Hashable,
    observation_evidence_ref: str,
) -> ProtocolInformationYieldObservation:
    """Measure one post-intervention response against a frozen partition."""

    evidence_ref = _nonempty(
        observation_evidence_ref,
        "observation_evidence_ref",
    )
    response_sha = stable_sha256(observed_response)
    posterior_size = next(
        (
            len(members)
            for candidate_sha, members in forecast.response_cells
            if candidate_sha == response_sha
        ),
        0,
    )
    return ProtocolInformationYieldObservation(
        forecast_sha256=forecast.sha256,
        protocol_id=forecast.protocol_id,
        committee_sha256=forecast.committee_sha256,
        partition_sha256=forecast.partition_sha256,
        observed_response_sha256=response_sha,
        status=(
            "witnessed_partition_cell"
            if posterior_size
            else "committee_refuted"
        ),
        posterior_cell_size=posterior_size,
        observed_information_yield=_realized_yield(
            forecast.committee_size,
            posterior_size,
        ),
        observation_evidence_ref=evidence_ref,
    )


__all__ = [
    "MEASURE_SHA256",
    "ProtocolInformationYieldForecast",
    "ProtocolInformationYieldObservation",
    "compile_protocol_information_yield_forecast",
    "observe_protocol_information_yield",
]
