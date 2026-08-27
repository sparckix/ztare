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

- identification: normalized entropy of the partition induced by the existing
  uniform deterministic committee. A separate stochastic primitive computes
  posterior-predictive mutual information when a caller owns calibrated model
  weights and predictive distributions.
- compression gain: expected fraction of committee description-length mass the
  observation retires — killing a structurally large survivor buys more than
  separating same-size variants.
- novelty: 1.0 when the experiment exercises a context the hypothesis language
  distinguishes but no prior experiment has witnessed. Explore what the
  grammar can express, no more.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Hashable, Mapping, Sequence


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


def posterior_predictive_information_bits(
    predictive_distributions: Sequence[Mapping[Hashable, float]],
    model_weights: Sequence[float] | None = None,
) -> float:
    """Return ``I(model; outcome)`` for a finite model belief.

    Each row is one model's categorical predictive distribution for the same
    experiment. ``model_weights`` is the caller-owned structure posterior; a
    missing value means a uniform committee. Parameter inference, likelihoods,
    and the evidence epoch remain the caller's responsibility.
    """

    n_models = len(predictive_distributions)
    if n_models == 0:
        return 0.0
    weights = (
        [1.0 / n_models] * n_models
        if model_weights is None
        else [float(value) for value in model_weights]
    )
    if len(weights) != n_models or any(
        not math.isfinite(value) or value < 0.0 for value in weights
    ):
        raise ValueError("model weights must be finite, nonnegative, and aligned")
    weight_total = sum(weights)
    if weight_total <= 0.0:
        raise ValueError("model weights must have positive mass")
    weights = [value / weight_total for value in weights]

    rows: list[dict[Hashable, float]] = []
    mixture: dict[Hashable, float] = {}
    for weight, raw in zip(weights, predictive_distributions):
        row = {outcome: float(probability) for outcome, probability in raw.items()}
        if not row or any(
            not math.isfinite(value) or value < 0.0 for value in row.values()
        ):
            raise ValueError("predictive distributions must have finite nonnegative mass")
        total = sum(row.values())
        if total <= 0.0:
            raise ValueError("predictive distributions must have positive mass")
        row = {outcome: value / total for outcome, value in row.items() if value > 0.0}
        rows.append(row)
        for outcome, probability in row.items():
            mixture[outcome] = mixture.get(outcome, 0.0) + weight * probability

    bits = 0.0
    for weight, row in zip(weights, rows):
        if weight == 0.0:
            continue
        for outcome, probability in row.items():
            bits += weight * probability * math.log2(probability / mixture[outcome])
    return max(0.0, bits)


def posterior_predictive_task_information_bits(
    experiment_predictives: Sequence[Mapping[Hashable, float]],
    target_predictives: Sequence[Mapping[Hashable, float]],
    model_weights: Sequence[float] | None = None,
) -> float:
    """Return ``I(experiment outcome; target outcome)`` in bits.

    Each aligned row is one posterior state (a model or model-parameter
    particle). Outcomes are conditionally independent within a row; callers
    that need parameter-induced dependence should pass parameter particles as
    separate rows. This is the finite categorical analogue of task-directed
    value of information: prefer a probe only when it resolves the named
    downstream target, not merely the model label.
    """

    if len(experiment_predictives) != len(target_predictives):
        raise ValueError("experiment and target predictions must be aligned")
    n_states = len(experiment_predictives)
    if n_states == 0:
        return 0.0
    weights = (
        [1.0 / n_states] * n_states
        if model_weights is None
        else [float(value) for value in model_weights]
    )
    if len(weights) != n_states or any(
        not math.isfinite(value) or value < 0.0 for value in weights
    ):
        raise ValueError("model weights must be finite, nonnegative, and aligned")
    total_weight = sum(weights)
    if total_weight <= 0.0:
        raise ValueError("model weights must have positive mass")

    joint: dict[tuple[Hashable, Hashable], float] = {}
    experiment_mass: dict[Hashable, float] = {}
    target_mass: dict[Hashable, float] = {}
    for weight, raw_experiment, raw_target in zip(
        weights, experiment_predictives, target_predictives,
    ):
        normalized_weight = weight / total_weight
        experiment = {key: float(value) for key, value in raw_experiment.items()}
        target = {key: float(value) for key, value in raw_target.items()}
        if (
            not experiment or not target
            or any(not math.isfinite(value) or value < 0.0 for value in experiment.values())
            or any(not math.isfinite(value) or value < 0.0 for value in target.values())
        ):
            raise ValueError("predictive distributions require finite nonnegative mass")
        experiment_total, target_total = sum(experiment.values()), sum(target.values())
        if experiment_total <= 0.0 or target_total <= 0.0:
            raise ValueError("predictive distributions must have positive mass")
        for experiment_outcome, experiment_probability in experiment.items():
            experiment_probability /= experiment_total
            experiment_mass[experiment_outcome] = (
                experiment_mass.get(experiment_outcome, 0.0)
                + normalized_weight * experiment_probability
            )
            for target_outcome, target_probability in target.items():
                probability = (
                    normalized_weight * experiment_probability
                    * target_probability / target_total
                )
                joint[(experiment_outcome, target_outcome)] = (
                    joint.get((experiment_outcome, target_outcome), 0.0) + probability
                )
        for target_outcome, target_probability in target.items():
            target_mass[target_outcome] = (
                target_mass.get(target_outcome, 0.0)
                + normalized_weight * target_probability / target_total
            )

    bits = sum(
        probability * math.log2(
            probability / (experiment_mass[experiment_outcome] * target_mass[target_outcome])
        )
        for (experiment_outcome, target_outcome), probability in joint.items()
        if probability > 0.0
    )
    return max(0.0, bits)


def price_experiment(committee: Sequence, predict: "Callable[[object], Hashable]",
                     size_fn: "Callable[[object], int]",
                     novel_context: bool) -> YieldComponents:
    """Price one experiment against the committee. `predict(member)` is the
    member's prediction for this experiment; `size_fn` is the description
    length used for committee ranking; `novel_context` is the caller's verdict
    on whether the experiment's guard context is unwitnessed."""
    n = len(committee)
    predictions = [predict(member) for member in committee]
    cells = partition_by_prediction(committee, predict)
    bits = posterior_predictive_information_bits(
        [{prediction: 1.0} for prediction in predictions],
    )
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
