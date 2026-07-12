"""Domain-agnostic information-yield pricing over a candidate committee.

The kernel already prices candidate-side yield per iteration
(`ztare.validator.core.information_yield`: is another candidate worth
generating?). This module is the observation-side counterpart: given a
committee of surviving hypotheses and a set of available experiments, what is
each experiment worth? The two are the opposing sides of one trade, and the
GP-250 `acquire_evidence` pivot is where they meet — the loop pivots to an
experiment when observation-side yield beats candidate-side yield.

Hoisted from `ztare.worldmodel.policy` on the `MDLLibrary` precedent: the math
is domain-free (hypotheses of any type, experiments of any type), with the
domain supplied as two callables. Consumers: `ztare.worldmodel.policy` (grid
transition programs, environment actions); the in-loop evaluator is the
intended second consumer at P1.

Components, each in [0, 1]:

- identification: normalized entropy of the partition the experiment induces
  over the committee's predictions (query-by-committee, named plainly).
- compression gain: expected fraction of committee description-length mass the
  observation retires, under a uniform posterior — killing a structurally
  large survivor buys more than separating same-size variants.
- novelty: 1.0 when the experiment exercises a context the hypothesis language
  distinguishes but no prior experiment has witnessed. Explore what the
  grammar can express, no more.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Hashable, Sequence


@dataclass(frozen=True)
class YieldComponents:
    identification: float
    compression_gain: float
    novelty: float

    def score(self, w_identification: float, w_compression: float, w_novelty: float) -> float:
        return (w_identification * self.identification
                + w_compression * self.compression_gain
                + w_novelty * self.novelty)


@dataclass(frozen=True)
class ResidualYieldCoordinates:
    """Information coordinates after a declared cheap baseline is removed."""

    baseline_ref: str
    candidate_ids: tuple[str, ...]
    baseline_ids: tuple[str, ...]
    residual_ids: tuple[str, ...]
    identification_bits: float
    description_units: float
    verification_cost_units: float

    @property
    def information_per_cost(self) -> float:
        cost = self.description_units + self.verification_cost_units
        return self.identification_bits / cost if cost > 0 else 0.0

    def to_json(self) -> dict[str, object]:
        return {
            "schema": "ztare.residual_information_yield.v1",
            "baseline_ref": self.baseline_ref,
            "candidate_ids": list(self.candidate_ids),
            "baseline_ids": list(self.baseline_ids),
            "residual_ids": list(self.residual_ids),
            "identification_bits": round(self.identification_bits, 8),
            "description_units": round(self.description_units, 8),
            "verification_cost_units": round(self.verification_cost_units, 8),
            "information_per_cost": round(self.information_per_cost, 8),
        }


def partition_by_prediction(committee: Sequence, predict: "Callable[[object], Hashable]"):
    """Group committee members by what they predict for one experiment."""
    cells: "dict[Hashable, list]" = {}
    for member in committee:
        cells.setdefault(predict(member), []).append(member)
    return cells


def identification_bits(cells: "dict[Hashable, list]", committee_size: int) -> float:
    # + 0.0 normalizes a zero-entropy result from IEEE -0.0 to +0.0 (a single-cell partition yields -0.0, which
    # reads as "negative info-yield" to a human downstream); harmless for every nonzero value.
    return -sum((len(cell) / committee_size) * math.log2(len(cell) / committee_size)
                for cell in cells.values()) + 0.0


def price_experiment(committee: Sequence, predict: "Callable[[object], Hashable]",
                     size_fn: "Callable[[object], int]",
                     novel_context: bool) -> YieldComponents:
    """Price one experiment against the committee. `predict(member)` is the
    member's prediction for this experiment; `size_fn` is the description
    length used for committee ranking; `novel_context` is the caller's verdict
    on whether the experiment's guard context is unwitnessed."""
    n = len(committee)
    cells = partition_by_prediction(committee, predict)

    bits = identification_bits(cells, n)
    max_bits = math.log2(n) if n > 1 else 1.0
    identification = bits / max_bits if max_bits > 0 else 0.0

    total = sum(size_fn(m) for m in committee)
    if total <= 0:
        compression = 0.0
    else:
        expected_surviving = sum((len(cell) / n) * sum(size_fn(m) for m in cell)
                                 for cell in cells.values())
        compression = (total - expected_surviving) / total

    return YieldComponents(identification=identification, compression_gain=compression,
                           novelty=1.0 if novel_context else 0.0)


def residual_information_yield(
    candidate_ids: Sequence[str],
    baseline_ids: Sequence[str],
    objects: Sequence[object],
    predict: "Callable[[str, object], Hashable]",
    *,
    baseline_ref: str,
    description_units: float,
    verification_cost_units: float = 0.0,
) -> ResidualYieldCoordinates:
    """Measure verified discriminative information beyond a cheap baseline.

    The caller owns the baseline and prediction semantics. This function only
    performs set subtraction and exact partition entropy, so the same contract
    works for theories, programs, experimental hypotheses, and proof routes.
    """

    if not str(baseline_ref).strip():
        raise ValueError("residual-yield baseline_ref must be nonempty")
    candidates = tuple(dict.fromkeys(str(value) for value in candidate_ids))
    baseline_set = {str(value) for value in baseline_ids}
    baseline = tuple(value for value in candidates if value in baseline_set)
    residual = tuple(value for value in candidates if value not in baseline_set)
    if description_units < 0 or verification_cost_units < 0:
        raise ValueError("residual-yield costs must be nonnegative")
    if not objects or not residual:
        bits = 0.0
    else:
        cells: dict[tuple[Hashable, ...], list[object]] = {}
        for obj in objects:
            signature = tuple(predict(candidate_id, obj) for candidate_id in residual)
            cells.setdefault(signature, []).append(obj)
        bits = identification_bits(cells, len(objects))
    return ResidualYieldCoordinates(
        baseline_ref=str(baseline_ref),
        candidate_ids=candidates,
        baseline_ids=baseline,
        residual_ids=residual,
        identification_bits=bits,
        description_units=float(description_units),
        verification_cost_units=float(verification_cost_units),
    )
