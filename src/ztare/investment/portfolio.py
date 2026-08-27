"""Exact paper-portfolio assembly over independently compiled entity policies.

Entity analysis proposes one target weight per frozen decision.  This module
owns the cross-entity capital budget: it accepts or declines complete proposals,
checks portfolio constraints, computes a Pareto frontier, and applies a declared
utility only after the frontier is known.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.common.linear_preference_regions import compile_linear_preference_regions

from .contracts import canonical_timestamp, mapping_rows, require_finite, require_refs, require_text


PORTFOLIO_PROFILE_SCHEMA = "jaggedthoughts-portfolio-assembly-profile-v1"
PORTFOLIO_ASSEMBLY_SCHEMA = "jaggedthoughts-portfolio-assembly-v1"
_METRICS = {
    "expected_excess_return",
    "weighted_downside",
    "thesis_confidence",
    "turnover",
    "estimated_cost_weight",
    "cash_weight",
}


@dataclass(frozen=True, slots=True)
class PortfolioMechanismScenario:
    mechanism_id: str
    mechanism_sha256: str
    expected_excess_return: float
    downside_risk: float
    thesis_confidence: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "mechanism_id", require_text(self.mechanism_id, "scenario.mechanism_id"))
        digest = require_text(self.mechanism_sha256, "scenario.mechanism_sha256")
        if len(digest) != 64:
            raise ValueError("portfolio mechanism scenario requires a SHA-256 digest")
        for attr in ("expected_excess_return", "downside_risk", "thesis_confidence"):
            object.__setattr__(self, attr, require_finite(getattr(self, attr), f"scenario.{attr}"))
        if self.downside_risk < 0 or not 0 <= self.thesis_confidence <= 1:
            raise ValueError("scenario downside must be nonnegative and confidence in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "mechanism_sha256": self.mechanism_sha256,
            "expected_excess_return": self.expected_excess_return,
            "downside_risk": self.downside_risk,
            "thesis_confidence": self.thesis_confidence,
        }


@dataclass(frozen=True, slots=True)
class PortfolioCandidate:
    decision_id: str
    decision_record_sha256: str
    entity_id: str
    current_weight: float
    target_weight: float
    expected_excess_return: float
    downside_risk: float
    thesis_confidence: float
    estimated_cost_weight: float
    mechanism_scenarios: tuple[PortfolioMechanismScenario, ...]

    def __post_init__(self) -> None:
        for attr in ("decision_id", "entity_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"candidate.{attr}"))
        digest = require_text(self.decision_record_sha256, "candidate.decision_record_sha256")
        if len(digest) != 64:
            raise ValueError("candidate decision hash must be a SHA-256 digest")
        for attr in (
            "current_weight", "target_weight", "expected_excess_return",
            "downside_risk", "thesis_confidence", "estimated_cost_weight",
        ):
            object.__setattr__(self, attr, require_finite(getattr(self, attr), f"candidate.{attr}"))
        if not 0 <= self.current_weight <= 1 or not 0 <= self.target_weight <= 1:
            raise ValueError("portfolio candidates must be long-only weights in [0, 1]")
        if self.downside_risk < 0 or self.estimated_cost_weight < 0:
            raise ValueError("candidate downside and cost cannot be negative")
        if not 0 <= self.thesis_confidence <= 1:
            raise ValueError("candidate thesis_confidence must be in [0, 1]")
        scenarios = tuple(sorted(self.mechanism_scenarios, key=lambda row: row.mechanism_id))
        if not scenarios or len({row.mechanism_id for row in scenarios}) != len(scenarios):
            raise ValueError("portfolio candidates require a nonempty unique mechanism committee")
        object.__setattr__(self, "mechanism_scenarios", scenarios)

    @property
    def robust_expected_excess_return(self) -> float:
        return min(self.expected_excess_return, *(row.expected_excess_return for row in self.mechanism_scenarios))

    @property
    def robust_downside_risk(self) -> float:
        return max(self.downside_risk, *(row.downside_risk for row in self.mechanism_scenarios))

    @property
    def robust_thesis_confidence(self) -> float:
        return min(self.thesis_confidence, *(row.thesis_confidence for row in self.mechanism_scenarios))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_record_sha256": self.decision_record_sha256,
            "entity_id": self.entity_id,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "expected_excess_return": self.expected_excess_return,
            "downside_risk": self.downside_risk,
            "thesis_confidence": self.thesis_confidence,
            "estimated_cost_weight": self.estimated_cost_weight,
            "mechanism_scenarios": [row.to_dict() for row in self.mechanism_scenarios],
            "robust_bounds": {
                "expected_excess_return_floor": self.robust_expected_excess_return,
                "downside_risk_ceiling": self.robust_downside_risk,
                "thesis_confidence_floor": self.robust_thesis_confidence,
            },
        }

    @classmethod
    def from_decision(cls, decision: Mapping[str, Any]) -> "PortfolioCandidate":
        body = dict(decision)
        declared = str(body.pop("decision_record_sha256", ""))
        if len(declared) != 64 or declared != stable_sha256(body):
            raise ValueError("portfolio candidate decision hash mismatch")
        if body.get("schema") != "jaggedthoughts-investment-decision-v1":
            raise ValueError("unsupported portfolio candidate decision schema")
        if body.get("authority") != "paper":
            raise ValueError("portfolio assembly accepts paper decisions only")
        state = dict(body["initial_state"]["firm"])
        proposal = body["position_proposal"]
        selected = body["policy_selection"]
        initial_state_sha256 = str(body["initial_state"]["state_sha256"])
        mechanism_by_id = {
            str(row["mechanism_id"]): str(row["mechanism_sha256"])
            for row in body["mechanisms"]
        }
        scenario_rows = []
        for rollout in body["policy_synthesis"]["rollouts"]:
            if str(rollout.get("program_id")) != str(selected["program_id"]):
                continue
            rollout_initial = str(
                rollout.get("initial_state_sha256")
                or (rollout.get("state_sha256s") or [""])[0]
            )
            if rollout_initial != initial_state_sha256:
                continue
            mechanism_id = str(rollout["mechanism_id"])
            terminal = rollout["terminal_state"]["firm"]
            scenario_rows.append(PortfolioMechanismScenario(
                mechanism_id=mechanism_id,
                mechanism_sha256=mechanism_by_id.get(mechanism_id, ""),
                expected_excess_return=float(terminal["expected_excess_return"]),
                downside_risk=float(terminal["downside_risk"]),
                thesis_confidence=float(terminal["thesis_confidence"]),
            ))
        if {row.mechanism_id for row in scenario_rows} != set(mechanism_by_id):
            raise ValueError("selected policy rollouts must cover the complete mechanism committee")
        book_value = require_finite(body["paper_book_before"]["total_value"], "book.total_value")
        if book_value <= 0:
            raise ValueError("candidate book total value must be positive")
        return cls(
            decision_id=str(body["decision_id"]),
            decision_record_sha256=declared,
            entity_id=str(body["entity"]["entity_id"]),
            current_weight=float(proposal["current_weight"]),
            target_weight=float(proposal["target_weight"]),
            expected_excess_return=float(state["expected_excess_return"]),
            downside_risk=float(state["downside_risk"]),
            thesis_confidence=float(state["thesis_confidence"]),
            estimated_cost_weight=float(proposal["estimated_cost"]) / book_value,
            mechanism_scenarios=tuple(scenario_rows),
        )


@dataclass(frozen=True, slots=True)
class PortfolioConstraints:
    constraint_id: str
    max_invested_weight: float
    max_candidate_weight: float
    max_turnover_weight: float
    max_weighted_downside: float
    fixed_weighted_downside: float
    max_positions: int | None = None
    min_position_weight: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_id", require_text(self.constraint_id, "constraint_id"))
        for attr in (
            "max_invested_weight", "max_candidate_weight", "max_turnover_weight",
            "max_weighted_downside", "fixed_weighted_downside", "min_position_weight",
        ):
            value = require_finite(getattr(self, attr), f"constraints.{attr}")
            if value < 0:
                raise ValueError(f"constraints.{attr} cannot be negative")
            object.__setattr__(self, attr, value)
        if self.max_invested_weight > 1 or self.max_candidate_weight > 1:
            raise ValueError("portfolio weight constraints cannot exceed 1")
        if self.min_position_weight > 1:
            raise ValueError("minimum position weight cannot exceed 1")
        if self.max_positions is not None:
            if isinstance(self.max_positions, bool) or int(self.max_positions) != self.max_positions or self.max_positions < 1:
                raise ValueError("max_positions must be a positive integer when declared")
            object.__setattr__(self, "max_positions", int(self.max_positions))
        if self.fixed_weighted_downside > self.max_weighted_downside:
            raise ValueError("fixed weighted downside already exceeds the portfolio limit")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "constraint_id": self.constraint_id,
            "max_invested_weight": self.max_invested_weight,
            "max_candidate_weight": self.max_candidate_weight,
            "max_turnover_weight": self.max_turnover_weight,
            "max_weighted_downside": self.max_weighted_downside,
            "fixed_weighted_downside": self.fixed_weighted_downside,
        }
        if self.max_positions is not None:
            body["max_positions"] = self.max_positions
        if self.min_position_weight > 0:
            body["min_position_weight"] = self.min_position_weight
        return body


@dataclass(frozen=True, slots=True)
class PatientCapitalPolicy:
    """Hold by default; sell a sound incumbent only for a superior use."""

    policy_id: str
    minimum_after_cost_return_edge: float
    impairment_return_floor: float
    impairment_confidence_floor: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", require_text(self.policy_id, "patient_capital.policy_id"))
        for attr in (
            "minimum_after_cost_return_edge", "impairment_return_floor",
            "impairment_confidence_floor",
        ):
            object.__setattr__(
                self, attr, require_finite(getattr(self, attr), f"patient_capital.{attr}"),
            )
        if self.minimum_after_cost_return_edge < 0:
            raise ValueError("patient-capital return edge cannot be negative")
        if not 0 <= self.impairment_confidence_floor <= 1:
            raise ValueError("patient-capital confidence floor must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "minimum_after_cost_return_edge": self.minimum_after_cost_return_edge,
            "impairment_return_floor": self.impairment_return_floor,
            "impairment_confidence_floor": self.impairment_confidence_floor,
            "default_action": "hold",
        }


@dataclass(frozen=True, slots=True)
class PortfolioExposureBand:
    """One source-bound linear exposure mandate over candidate weights."""

    exposure_id: str
    minimum: float | None
    maximum: float | None
    fixed_exposure: float
    coefficients: tuple[tuple[str, float], ...]
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "exposure_id", require_text(self.exposure_id, "exposure_id"))
        minimum = None if self.minimum is None else require_finite(self.minimum, "exposure.minimum")
        maximum = None if self.maximum is None else require_finite(self.maximum, "exposure.maximum")
        if minimum is None and maximum is None:
            raise ValueError("exposure band requires a minimum or maximum")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("exposure minimum cannot exceed maximum")
        coefficients = mapping_rows(dict(self.coefficients))
        if not coefficients:
            raise ValueError("exposure coefficients must be nonempty")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)
        object.__setattr__(self, "fixed_exposure", require_finite(
            self.fixed_exposure, "exposure.fixed_exposure",
        ))
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "exposure source_ref"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "exposure_id": self.exposure_id, "minimum": self.minimum, "maximum": self.maximum,
            "fixed_exposure": self.fixed_exposure, "coefficients": dict(self.coefficients),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class PortfolioObjective:
    objective_id: str
    metric: str
    direction: str
    scale: float
    utility_weight: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective_id", require_text(self.objective_id, "objective_id"))
        metric = require_text(self.metric, "portfolio objective metric")
        if metric not in _METRICS:
            raise ValueError(f"unsupported portfolio objective metric: {metric}")
        if self.direction not in {"maximize", "minimize"}:
            raise ValueError("portfolio objective direction must be maximize or minimize")
        scale = require_finite(self.scale, "portfolio objective scale")
        weight = require_finite(self.utility_weight, "portfolio objective utility_weight")
        if scale <= 0 or weight < 0:
            raise ValueError("portfolio objective scale must be positive and weight nonnegative")
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "utility_weight", weight)

    def utility(self, value: float) -> float:
        sign = 1 if self.direction == "maximize" else -1
        return sign * self.utility_weight * value / self.scale

    def no_worse(self, left: float, right: float) -> bool:
        return left >= right - 1e-12 if self.direction == "maximize" else left <= right + 1e-12

    def strictly_better(self, left: float, right: float) -> bool:
        return left > right + 1e-12 if self.direction == "maximize" else left < right - 1e-12

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "metric": self.metric,
            "direction": self.direction,
            "scale": self.scale,
            "utility_weight": self.utility_weight,
        }


@dataclass(frozen=True, slots=True)
class PortfolioAlternative:
    accepted_decision_ids: tuple[str, ...]
    target_weights: tuple[tuple[str, float], ...]
    metrics: tuple[tuple[str, float], ...]
    utility: float
    alternative_id: str = field(init=False)

    def __post_init__(self) -> None:
        accepted = tuple(sorted(set(self.accepted_decision_ids)))
        targets = mapping_rows(dict(self.target_weights))
        metrics = mapping_rows(dict(self.metrics))
        object.__setattr__(self, "accepted_decision_ids", accepted)
        object.__setattr__(self, "target_weights", targets)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "utility", require_finite(self.utility, "portfolio utility"))
        object.__setattr__(self, "alternative_id", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-portfolio-alternative-v1",
            "accepted_decision_ids": list(self.accepted_decision_ids),
            "target_weights": dict(self.target_weights),
            "metrics": dict(self.metrics),
            "utility": self.utility,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "alternative_id": self.alternative_id}


def _dominates(
    left: PortfolioAlternative,
    right: PortfolioAlternative,
    objectives: tuple[PortfolioObjective, ...],
) -> bool:
    a, b = dict(left.metrics), dict(right.metrics)
    return all(row.no_worse(a[row.metric], b[row.metric]) for row in objectives) and any(
        row.strictly_better(a[row.metric], b[row.metric]) for row in objectives
    )


def _nominal_utility(
    alternative: PortfolioAlternative,
    objectives: tuple[PortfolioObjective, ...],
) -> float:
    metrics = dict(alternative.metrics)
    nominal_metric = {
        "expected_excess_return": "nominal_expected_excess_return",
        "weighted_downside": "nominal_weighted_downside",
        "thesis_confidence": "nominal_thesis_confidence",
    }
    return sum(
        objective.utility(metrics[nominal_metric.get(objective.metric, objective.metric)])
        for objective in objectives
    )


def compile_patient_rotation_review(
    candidates: Iterable[PortfolioCandidate],
    target_weights: Mapping[str, float],
    policy: PatientCapitalPolicy,
) -> dict[str, Any]:
    """Match healthy-incumbent reductions to superior after-cost replacements."""

    import z3

    rows = tuple(candidates)
    targets = {str(key): float(value) for key, value in target_weights.items()}
    if set(targets) != {row.entity_id for row in rows}:
        raise ValueError("patient-capital review requires the exact candidate target universe")

    def cost_rate(row: PortfolioCandidate) -> float:
        delta = abs(row.target_weight - row.current_weight)
        return row.estimated_cost_weight / delta if delta > 1e-12 else 0.0

    reductions = [
        (row, row.current_weight - targets[row.entity_id])
        for row in rows if targets[row.entity_id] < row.current_weight - 1e-12
    ]
    increases = [
        (row, targets[row.entity_id] - row.current_weight)
        for row in rows if targets[row.entity_id] > row.current_weight + 1e-12
    ]
    impaired: list[tuple[PortfolioCandidate, float, list[str]]] = []
    healthy: list[tuple[PortfolioCandidate, float, list[str]]] = []
    for row, weight in reductions:
        reasons = []
        if row.robust_expected_excess_return <= policy.impairment_return_floor + 1e-12:
            reasons.append("return_floor_breached")
        if row.robust_thesis_confidence <= policy.impairment_confidence_floor + 1e-12:
            reasons.append("confidence_floor_breached")
        (impaired if reasons else healthy).append((row, weight, reasons))

    edges = []
    for incumbent, sell_weight, _reasons in healthy:
        for challenger, buy_weight in increases:
            edge = (
                challenger.robust_expected_excess_return
                - incumbent.robust_expected_excess_return
                - cost_rate(incumbent)
                - cost_rate(challenger)
            )
            edges.append({
                "incumbent_entity_id": incumbent.entity_id,
                "challenger_entity_id": challenger.entity_id,
                "after_cost_return_edge": edge,
                "qualifies": edge + 1e-12 >= policy.minimum_after_cost_return_edge,
                "sell_capacity": sell_weight,
                "buy_capacity": buy_weight,
            })

    qualifying = [row for row in edges if row["qualifies"]]
    flows: list[dict[str, Any]] = []
    matched = 0.0
    if healthy and qualifying:
        optimizer = z3.Optimize()
        variables = {
            (row["incumbent_entity_id"], row["challenger_entity_id"]): z3.Real(
                f"rotation_{index}"
            ) for index, row in enumerate(qualifying)
        }
        for variable in variables.values():
            optimizer.add(variable >= 0)
        for incumbent, weight, _reasons in healthy:
            optimizer.add(z3.Sum([
                variable for (left, _right), variable in variables.items()
                if left == incumbent.entity_id
            ]) <= z3.RealVal(str(weight)))
        for challenger, weight in increases:
            optimizer.add(z3.Sum([
                variable for (_left, right), variable in variables.items()
                if right == challenger.entity_id
            ]) <= z3.RealVal(str(weight)))
        optimizer.maximize(z3.Sum(list(variables.values())))
        if optimizer.check() == z3.sat:
            model = optimizer.model()
            for edge in qualifying:
                key = (edge["incumbent_entity_id"], edge["challenger_entity_id"])
                value = model.eval(variables[key], model_completion=True)
                fraction = Fraction(value.numerator_as_long(), value.denominator_as_long())
                if fraction > 0:
                    flows.append({
                        "incumbent_entity_id": edge["incumbent_entity_id"],
                        "challenger_entity_id": edge["challenger_entity_id"],
                        "after_cost_return_edge": edge["after_cost_return_edge"],
                        "matched_weight": float(fraction),
                    })
                    matched += float(fraction)

    required = sum(weight for _row, weight, _reasons in healthy)
    blockers = []
    for incumbent, weight, _reasons in healthy:
        incumbent_matched = sum(
            row["matched_weight"] for row in flows
            if row["incumbent_entity_id"] == incumbent.entity_id
        )
        if incumbent_matched + 1e-12 >= weight:
            continue
        available_edges = [
            row["after_cost_return_edge"] for row in edges
            if row["incumbent_entity_id"] == incumbent.entity_id
        ]
        best = max(available_edges, default=None)
        blockers.append({
            "incumbent_entity_id": incumbent.entity_id,
            "unmatched_reduction_weight": weight - incumbent_matched,
            "best_available_after_cost_return_edge": best,
            "minimum_return_edge_must_be_at_most": best,
        })
    compliant = matched + 1e-12 >= required
    status = (
        "blocked_rotation" if blockers else
        "qualified_rotation" if healthy else
        "impairment_exit" if impaired else
        "cash_funded_addition" if increases else
        "hold_default"
    )
    body = {
        "schema": "jaggedthoughts-patient-capital-review-v1",
        "policy": policy.to_dict(),
        "status": status,
        "compliant": compliant,
        "reductions": [{
            "entity_id": row.entity_id,
            "weight": weight,
            "robust_expected_excess_return": row.robust_expected_excess_return,
            "robust_thesis_confidence": row.robust_thesis_confidence,
            "impairment_reasons": reasons,
        } for row, weight, reasons in (*impaired, *healthy)],
        "increases": [{
            "entity_id": row.entity_id,
            "weight": weight,
            "robust_expected_excess_return": row.robust_expected_excess_return,
        } for row, weight in increases],
        "replacement_edges": edges,
        "replacement_flows": flows,
        "healthy_reduction_weight": required,
        "matched_replacement_weight": matched,
        "blockers": blockers,
        "boundary": (
            "A reduction is admissible when the incumbent breaches a declared impairment floor or "
            "its weight is matched to a challenger whose mechanism-safe return advantage clears "
            "both proposal costs and the declared opportunity-cost edge. Taxes remain outside this "
            "policy until a source-bound account tax contract exists."
        ),
    }
    return {**body, "review_sha256": stable_sha256(body)}


def _nominal_robust_utility_frontier(
    alternatives: tuple[PortfolioAlternative, ...],
    nominal_utilities: Mapping[str, float],
) -> tuple[tuple[PortfolioAlternative, ...], list[dict[str, Any]]]:
    """Keep the undominated policies before asking Z3 for exact blend regions."""
    representatives: dict[tuple[float, float], PortfolioAlternative] = {}
    equivalence: list[dict[str, Any]] = []
    for alternative in sorted(alternatives, key=lambda row: row.alternative_id):
        pair = (nominal_utilities[alternative.alternative_id], alternative.utility)
        prior = representatives.setdefault(pair, alternative)
        if prior is not alternative:
            equivalence.append({
                "alternative_id": alternative.alternative_id,
                "representative_alternative_id": prior.alternative_id,
                "witness": "identical_nominal_and_mechanism_safe_utility",
            })
    ordered = sorted(
        representatives.values(),
        key=lambda row: (
            -nominal_utilities[row.alternative_id], -row.utility, row.alternative_id,
        ),
    )
    frontier: list[PortfolioAlternative] = []
    best_robust = float("-inf")
    for alternative in ordered:
        if alternative.utility > best_robust + 1e-12:
            frontier.append(alternative)
            best_robust = alternative.utility
    return tuple(frontier), equivalence


def _enumerate_feasible_acceptance_sets(
    candidates: tuple[PortfolioCandidate, ...],
    constraints: PortfolioConstraints,
    exposure_bands: tuple[PortfolioExposureBand, ...],
    *,
    fixed_invested_weight: float,
    fixed_position_count: int,
) -> tuple[tuple[tuple[str, ...], ...], dict[str, Any]]:
    """Enumerate exact Boolean portfolio choices under linear risk constraints."""
    import z3

    variables = tuple(z3.Bool(f"accept_candidate_{index}") for index in range(len(candidates)))

    def q(value: float) -> Any:
        return z3.RealVal(str(value))

    targets = tuple(
        z3.If(variable, q(candidate.target_weight), q(candidate.current_weight))
        for variable, candidate in zip(variables, candidates, strict=True)
    )
    tracked = [
        (
            "max_invested_weight",
            q(fixed_invested_weight) + z3.Sum(targets) <= q(constraints.max_invested_weight),
        ),
        (
            "max_turnover_weight",
            z3.Sum([
                z3.If(variable, q(abs(candidate.target_weight - candidate.current_weight)), q(0))
                for variable, candidate in zip(variables, candidates, strict=True)
            ]) <= q(constraints.max_turnover_weight),
        ),
        (
            "max_weighted_downside",
            q(constraints.fixed_weighted_downside) + z3.Sum([
                target * q(candidate.robust_downside_risk)
                for target, candidate in zip(targets, candidates, strict=True)
            ]) <= q(constraints.max_weighted_downside),
        ),
        *(
            (
                f"max_candidate_weight:{candidate.entity_id}",
                target <= q(constraints.max_candidate_weight),
            )
            for target, candidate in zip(targets, candidates, strict=True)
        ),
    ]
    if constraints.max_positions is not None:
        tracked.append((
            "max_positions",
            fixed_position_count + z3.Sum([z3.If(target > 0, 1, 0) for target in targets])
            <= constraints.max_positions,
        ))
    if constraints.min_position_weight > 0:
        tracked.extend(
            (
                f"min_position_weight:{candidate.entity_id}",
                z3.Or(target == 0, target >= q(constraints.min_position_weight)),
            )
            for target, candidate in zip(targets, candidates, strict=True)
        )
    exposure_expressions: dict[str, Any] = {}
    for band in exposure_bands:
        coefficients = dict(band.coefficients)
        exposure = q(band.fixed_exposure) + z3.Sum([
            target * q(coefficients[candidate.entity_id])
            for target, candidate in zip(targets, candidates, strict=True)
        ])
        exposure_expressions[band.exposure_id] = exposure
        if band.minimum is not None:
            tracked.append((f"exposure_min:{band.exposure_id}", exposure >= q(band.minimum)))
        if band.maximum is not None:
            tracked.append((f"exposure_max:{band.exposure_id}", exposure <= q(band.maximum)))
    label_to_constraint = {
        f"portfolio_constraint_{index}": constraint_id
        for index, (constraint_id, _expression) in enumerate(tracked)
    }

    def solver() -> Any:
        instance = z3.Solver()
        instance.set(unsat_core=True)
        for label, (_constraint_id, expression) in zip(label_to_constraint, tracked, strict=True):
            instance.assert_and_track(expression, z3.Bool(label))
        return instance

    acceptance_checks: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        probe = solver()
        verdict = probe.check(variables[index])
        if verdict == z3.unknown:
            raise RuntimeError(f"Z3 could not decide portfolio acceptance: {probe.reason_unknown()}")
        row: dict[str, Any] = {
            "decision_id": candidate.decision_id,
            "entity_id": candidate.entity_id,
            "accept_feasible": verdict == z3.sat,
        }
        if verdict == z3.sat:
            model = probe.model()
            row["compatible_decision_ids_witness"] = sorted(
                other.decision_id
                for variable, other in zip(variables, candidates, strict=True)
                if z3.is_true(model.eval(variable, model_completion=True))
            )
        else:
            row["blocking_constraint_ids"] = sorted({
                label_to_constraint[str(label)]
                for label in probe.unsat_core()
                if str(label) in label_to_constraint
            })
        if exposure_bands:
            activation_ranges = []
            for band in exposure_bands:
                excluded = {
                    f"exposure_min:{band.exposure_id}",
                    f"exposure_max:{band.exposure_id}",
                }

                def bound(direction: str) -> tuple[str, float] | None:
                    optimizer = z3.Optimize()
                    optimizer.add(variables[index])
                    optimizer.add(*(
                        expression for constraint_id, expression in tracked
                        if constraint_id not in excluded
                    ))
                    expression = exposure_expressions[band.exposure_id]
                    (optimizer.minimize if direction == "minimum" else optimizer.maximize)(expression)
                    for variable in variables:
                        optimizer.minimize(z3.If(variable, 1, 0))
                    if optimizer.check() != z3.sat:
                        return None
                    value = optimizer.model().eval(expression, model_completion=True)
                    if not z3.is_rational_value(value):
                        raise RuntimeError(f"portfolio exposure boundary is not rational: {value}")
                    fraction = Fraction(value.numerator_as_long(), value.denominator_as_long())
                    exact = (
                        str(fraction.numerator) if fraction.denominator == 1
                        else f"{fraction.numerator}/{fraction.denominator}"
                    )
                    return exact, float(fraction)

                lower, upper = bound("minimum"), bound("maximum")
                activation: dict[str, Any] = {
                    "exposure_id": band.exposure_id,
                    "declared_band": [band.minimum, band.maximum],
                }
                if lower is None or upper is None:
                    activation["status"] = "blocked_by_other_constraints"
                else:
                    activation.update({
                        "status": "solved",
                        "minimum_when_accepted_exact": lower[0],
                        "minimum_when_accepted": lower[1],
                        "maximum_when_accepted_exact": upper[0],
                        "maximum_when_accepted": upper[1],
                        "declared_band_intersects_acceptance_range": (
                            (band.minimum is None or upper[1] >= band.minimum - 1e-12)
                            and (band.maximum is None or lower[1] <= band.maximum + 1e-12)
                        ),
                    })
                    if band.maximum is not None and lower[1] > band.maximum + 1e-12:
                        activation["maximum_must_be_at_least"] = lower[1]
                    if band.minimum is not None and upper[1] < band.minimum - 1e-12:
                        activation["minimum_must_be_at_most"] = upper[1]
                activation_ranges.append(activation)
            row["exposure_activation_ranges"] = activation_ranges
        acceptance_checks.append(row)

    instance = solver()
    assignments: list[tuple[str, ...]] = []
    while True:
        verdict = instance.check()
        if verdict == z3.unsat:
            break
        if verdict == z3.unknown:
            raise RuntimeError(f"Z3 could not enumerate portfolio choices: {instance.reason_unknown()}")
        model = instance.model()
        selected = tuple(
            candidate.decision_id
            for variable, candidate in zip(variables, candidates, strict=True)
            if z3.is_true(model.eval(variable, model_completion=True))
        )
        assignments.append(tuple(sorted(selected)))
        instance.add(z3.Or(*[
            variable != model.eval(variable, model_completion=True)
            for variable in variables
        ]))

    rows = tuple(sorted(assignments))
    body = {
        "schema": "jaggedthoughts-portfolio-feasibility-certificate-v1",
        "solver": {
            "name": "z3", "version": z3.get_version_string(),
            "logic": "QF_LIRA+Bool" if constraints.max_positions is not None else "QF_LRA+Bool",
        },
        "decision_variable_ids": [row.decision_id for row in candidates],
        "candidate_mechanism_counts": {
            row.entity_id: len(row.mechanism_scenarios) for row in candidates
        },
        "constraint_ids": [constraint_id for constraint_id, _expression in tracked],
        "acceptance_checks": acceptance_checks,
        "feasible_assignment_count": len(rows),
        "scope_closed": True,
        "use_boundary": (
            "The solver certifies only the declared accept-or-decline population, rectangular mechanism "
            "committee, and linear portfolio constraints. Scenario consequences remain authored estimates."
        ),
    }
    if exposure_bands:
        body["exposure_bands"] = [row.to_dict() for row in exposure_bands]
    return rows, {**body, "feasibility_sha256": stable_sha256(body)}


def _compile_continuous_allocation_envelope(
    candidates: tuple[PortfolioCandidate, ...],
    constraints: PortfolioConstraints,
    objectives: tuple[PortfolioObjective, ...],
    exposure_bands: tuple[PortfolioExposureBand, ...],
    *,
    fixed_invested_weight: float,
    fixed_position_count: int,
) -> dict[str, Any]:
    """Solve partial-sizing boundaries inside each underwriter's declared weight corridor."""
    import z3

    def q(value: float) -> Any:
        return z3.RealVal(str(value))

    def exact(value: Any) -> tuple[str, float]:
        if not z3.is_rational_value(value):
            raise RuntimeError(f"portfolio optimum is not rational: {value}")
        fraction = Fraction(value.numerator_as_long(), value.denominator_as_long())
        rendered = str(fraction.numerator) if fraction.denominator == 1 else f"{fraction.numerator}/{fraction.denominator}"
        return rendered, float(fraction)

    weights = {
        row.decision_id: z3.Real(f"portfolio_weight_{index}")
        for index, row in enumerate(candidates)
    }
    turnover = {
        row.decision_id: z3.If(
            weights[row.decision_id] >= q(row.current_weight),
            weights[row.decision_id] - q(row.current_weight),
            q(row.current_weight) - weights[row.decision_id],
        )
        for row in candidates
    }
    constraints_by_id: dict[str, tuple[Any, Any]] = {}
    for row in candidates:
        weight = weights[row.decision_id]
        floor = q(min(row.current_weight, row.target_weight))
        ceiling = q(max(row.current_weight, row.target_weight))
        candidate_cap = q(constraints.max_candidate_weight)
        constraints_by_id[f"corridor_floor:{row.entity_id}"] = (weight >= floor, weight == floor)
        constraints_by_id[f"corridor_ceiling:{row.entity_id}"] = (weight <= ceiling, weight == ceiling)
        constraints_by_id[f"max_candidate_weight:{row.entity_id}"] = (weight <= candidate_cap, weight == candidate_cap)
        if constraints.min_position_weight > 0:
            minimum = q(constraints.min_position_weight)
            constraints_by_id[f"min_position_weight:{row.entity_id}"] = (
                z3.Or(weight == 0, weight >= minimum), weight == minimum,
            )
    invested = q(fixed_invested_weight) + z3.Sum(list(weights.values()))
    total_turnover = z3.Sum(list(turnover.values()))
    weighted_downside = q(constraints.fixed_weighted_downside) + z3.Sum([
        weights[row.decision_id] * q(row.robust_downside_risk) for row in candidates
    ])
    constraints_by_id.update({
        "max_invested_weight": (
            invested <= q(constraints.max_invested_weight),
            invested == q(constraints.max_invested_weight),
        ),
        "max_weighted_downside": (
            weighted_downside <= q(constraints.max_weighted_downside),
            weighted_downside == q(constraints.max_weighted_downside),
        ),
        "max_turnover_weight": (
            total_turnover <= q(constraints.max_turnover_weight),
            total_turnover == q(constraints.max_turnover_weight),
        ),
    })
    if constraints.max_positions is not None:
        active_positions = fixed_position_count + z3.Sum([
            z3.If(weights[row.decision_id] > 0, 1, 0) for row in candidates
        ])
        constraints_by_id["max_positions"] = (
            active_positions <= constraints.max_positions,
            active_positions == constraints.max_positions,
        )
    exposure_expressions = {}
    for band in exposure_bands:
        coefficients = dict(band.coefficients)
        exposure = q(band.fixed_exposure) + z3.Sum([
            weights[row.decision_id] * q(coefficients[row.entity_id]) for row in candidates
        ])
        exposure_expressions[band.exposure_id] = exposure
        if band.minimum is not None:
            constraints_by_id[f"exposure_min:{band.exposure_id}"] = (
                exposure >= q(band.minimum), exposure == q(band.minimum),
            )
        if band.maximum is not None:
            constraints_by_id[f"exposure_max:{band.exposure_id}"] = (
                exposure <= q(band.maximum), exposure == q(band.maximum),
            )
    metrics = {
        "expected_excess_return": z3.Sum([
            weights[row.decision_id] * q(row.robust_expected_excess_return) for row in candidates
        ]),
        "weighted_downside": weighted_downside,
        "thesis_confidence": z3.Sum([
            weights[row.decision_id] * q(row.robust_thesis_confidence) for row in candidates
        ]),
        "turnover": total_turnover,
        "estimated_cost_weight": z3.Sum([
            turnover[row.decision_id] * q(
                row.estimated_cost_weight / abs(row.target_weight - row.current_weight)
                if row.target_weight != row.current_weight else 0.0
            )
            for row in candidates
        ]),
        "cash_weight": q(1 - fixed_invested_weight) - z3.Sum(list(weights.values())),
    }
    metrics.update({f"exposure:{identity}": expression
                    for identity, expression in exposure_expressions.items()})
    nominal_metrics = {
        **metrics,
        "expected_excess_return": z3.Sum([
            weights[row.decision_id] * q(row.expected_excess_return) for row in candidates
        ]),
        "weighted_downside": q(constraints.fixed_weighted_downside) + z3.Sum([
            weights[row.decision_id] * q(row.downside_risk) for row in candidates
        ]),
        "thesis_confidence": z3.Sum([
            weights[row.decision_id] * q(row.thesis_confidence) for row in candidates
        ]),
    }

    def optimize(expression: Any, direction: str) -> dict[str, Any]:
        solver = z3.Optimize()
        solver.set(priority="lex")
        solver.add(*(condition for condition, _binding in constraints_by_id.values()))
        (solver.maximize if direction == "maximize" else solver.minimize)(expression)
        for decision_id in sorted(weights):
            solver.minimize(weights[decision_id])
        verdict = solver.check()
        if verdict != z3.sat:
            raise RuntimeError(f"Z3 could not optimize portfolio envelope: {verdict}")
        model = solver.model()
        exact_value, decimal_value = exact(model.eval(expression, model_completion=True))
        return {
            "optimum_exact": exact_value,
            "optimum": decimal_value,
            "target_weights": {
                row.entity_id: exact(model.eval(weights[row.decision_id], model_completion=True))[1]
                for row in candidates
            },
            "binding_constraint_ids": sorted(
                identity for identity, (_condition, binding) in constraints_by_id.items()
                if z3.is_true(model.eval(binding, model_completion=True))
            ),
        }

    capacity = []
    for row in candidates:
        result = optimize(weights[row.decision_id], "maximize")
        capacity.append({
            "decision_id": row.decision_id,
            "entity_id": row.entity_id,
            "corridor": [min(row.current_weight, row.target_weight), max(row.current_weight, row.target_weight)],
            "maximum_feasible_weight_exact": result.pop("optimum_exact"),
            "maximum_feasible_weight": result.pop("optimum"),
            **result,
        })
    objective_optima = []
    for objective in objectives:
        result = optimize(metrics[objective.metric], objective.direction)
        objective_optima.append({
            "objective_id": objective.objective_id,
            "metric": objective.metric,
            "direction": objective.direction,
            **result,
        })
    exposure_ranges = []
    for band in exposure_bands:
        lower = optimize(exposure_expressions[band.exposure_id], "minimize")
        upper = optimize(exposure_expressions[band.exposure_id], "maximize")
        exposure_ranges.append({
            "exposure_id": band.exposure_id,
            "declared_band": [band.minimum, band.maximum],
            "minimum_attainable_exact": lower.pop("optimum_exact"),
            "minimum_attainable": lower.pop("optimum"),
            "minimum_witness": lower,
            "maximum_attainable_exact": upper.pop("optimum_exact"),
            "maximum_attainable": upper.pop("optimum"),
            "maximum_witness": upper,
        })
    utility = z3.Sum([
        q((1 if row.direction == "maximize" else -1) * row.utility_weight / row.scale)
        * metrics[row.metric]
        for row in objectives
    ])
    nominal_utility = z3.Sum([
        q((1 if row.direction == "maximize" else -1) * row.utility_weight / row.scale)
        * nominal_metrics[row.metric]
        for row in objectives
    ])
    robust_optimum = optimize(utility, "maximize")
    nominal_optimum = optimize(nominal_utility, "maximize")
    robustness_price = nominal_optimum["optimum"] - robust_optimum["optimum"]
    if robustness_price < -1e-12:
        raise AssertionError("robust portfolio utility cannot exceed nominal utility")
    body = {
        "schema": "jaggedthoughts-continuous-allocation-envelope-v1",
        "solver": {
            "name": "z3", "version": z3.get_version_string(),
            "logic": "QF_LIRA+ite" if constraints.max_positions is not None else "QF_LRA+ite",
        },
        "uncertainty_set": {
            "kind": "nominal_plus_rectangular_mechanism_committee",
            "candidate_mechanism_counts": {
                row.entity_id: len(row.mechanism_scenarios) for row in candidates
            },
            "return_coordinate": "per-candidate nominal-plus-mechanism floor",
            "downside_coordinate": "per-candidate nominal-plus-mechanism ceiling",
            "confidence_coordinate": "per-candidate nominal-plus-mechanism floor",
            "probability_interpretation": False,
        },
        "candidate_capacity": capacity,
        "objective_optima": objective_optima,
        "declared_utility_optimum": robust_optimum,
        "nominal_utility_optimum": nominal_optimum,
        "price_of_robustness": max(0.0, robustness_price),
        "scope_closed": True,
        "capital_authority": False,
        "use_boundary": (
            "This is a maximin partial-sizing envelope inside frozen current-to-target corridors and the "
            "rectangular product of each nominal state plus its mechanism committee. It assigns no probabilities."
        ),
    }
    if exposure_ranges:
        body["exposure_ranges"] = exposure_ranges
    return {**body, "allocation_envelope_sha256": stable_sha256(body)}


def compile_portfolio_assembly(
    *,
    portfolio_id: str,
    decisions: Iterable[Mapping[str, Any]],
    constraints: PortfolioConstraints,
    objectives: Iterable[PortfolioObjective],
    exposure_bands: Iterable[PortfolioExposureBand] = (),
    patient_capital_policy: PatientCapitalPolicy | None = None,
    max_combinations: int = 65_536,
    profile_source_sha256: str = "",
) -> dict[str, Any]:
    decision_rows = tuple(dict(row) for row in decisions)
    if not decision_rows:
        raise ValueError("portfolio assembly requires at least one decision")
    candidates = tuple(PortfolioCandidate.from_decision(row) for row in decision_rows)
    if len({row.entity_id for row in candidates}) != len(candidates):
        raise ValueError("portfolio candidate entities must be unique")
    objective_rows = tuple(objectives)
    if not objective_rows or len({row.objective_id for row in objective_rows}) != len(objective_rows):
        raise ValueError("portfolio objectives must be nonempty and unique")
    exposure_rows = tuple(sorted(exposure_bands, key=lambda row: row.exposure_id))
    if len({row.exposure_id for row in exposure_rows}) != len(exposure_rows):
        raise ValueError("portfolio exposure bands must be unique")
    candidate_entities = {row.entity_id for row in candidates}
    for band in exposure_rows:
        coefficient_entities = set(dict(band.coefficients))
        if coefficient_entities != candidate_entities:
            raise ValueError(
                f"exposure {band.exposure_id} coefficients must cover the exact candidate universe"
            )
    identity = {
        (
            str(row["owner"]), str(row["as_of"]), str(row["benchmark"]["entity_id"]),
            str(row["paper_book_before"]["book_sha256"]), str(row["paper_book_before"]["currency"]),
        )
        for row in decision_rows
    }
    if len(identity) != 1:
        raise ValueError("portfolio decisions must share owner, epoch, benchmark, currency, and starting book")
    owner, as_of, benchmark_id, book_sha256, currency = next(iter(identity))
    canonical_as_of = canonical_timestamp(as_of, "portfolio as_of")
    book = decision_rows[0]["paper_book_before"]
    total_value = require_finite(book["total_value"], "portfolio book total_value")
    if total_value <= 0:
        raise ValueError("portfolio starting book must have positive value")
    fixed_position_weights = {
        str(row["entity_id"]):
        require_finite(row["market_value"], "portfolio position market_value") / total_value
        for row in book.get("positions", [])
        if str(row["entity_id"]) not in candidate_entities
    }
    fixed_invested_weight = sum(fixed_position_weights.values())
    fixed_position_count = sum(weight > 0 for weight in fixed_position_weights.values())
    combinations = 1 << len(candidates)
    if combinations > max_combinations:
        raise ValueError(
            f"portfolio combination count {combinations} exceeds max_combinations {max_combinations}"
        )

    feasible_assignments, feasibility_certificate = _enumerate_feasible_acceptance_sets(
        candidates, constraints, exposure_rows, fixed_invested_weight=fixed_invested_weight,
        fixed_position_count=fixed_position_count,
    )
    continuous_allocation_envelope = _compile_continuous_allocation_envelope(
        candidates,
        constraints,
        objective_rows,
        exposure_rows,
        fixed_invested_weight=fixed_invested_weight,
        fixed_position_count=fixed_position_count,
    )
    alternatives: dict[tuple[tuple[str, float], ...], PortfolioAlternative] = {}
    patient_reviews: dict[str, dict[str, Any]] = {}
    rotation_rejections: list[dict[str, Any]] = []
    for accepted_decision_ids in feasible_assignments:
        accepted_ids = set(accepted_decision_ids)
        accepted = tuple(
            candidate for candidate in candidates
            if candidate.decision_id in accepted_ids
        )
        targets = tuple(
            (row.entity_id, row.target_weight if row.decision_id in accepted_ids else row.current_weight)
            for row in candidates
        )
        target_map = dict(targets)
        turnover = sum(
            abs(target_map[row.entity_id] - row.current_weight) for row in candidates
        )
        invested = fixed_invested_weight + sum(target_map.values())
        nominal_downside = constraints.fixed_weighted_downside + sum(
            target_map[row.entity_id] * row.downside_risk for row in candidates
        )
        downside = constraints.fixed_weighted_downside + sum(
            target_map[row.entity_id] * row.robust_downside_risk for row in candidates
        )
        exposure_values = {
            band.exposure_id: band.fixed_exposure + sum(
                target_map[entity_id] * coefficient
                for entity_id, coefficient in band.coefficients
            ) for band in exposure_rows
        }
        if (
            invested > constraints.max_invested_weight + 1e-12
            or any(weight > constraints.max_candidate_weight + 1e-12 for weight in target_map.values())
            or turnover > constraints.max_turnover_weight + 1e-12
            or downside > constraints.max_weighted_downside + 1e-12
            or (
                constraints.max_positions is not None
                and fixed_position_count + sum(weight > 1e-12 for weight in target_map.values())
                > constraints.max_positions
            )
            or any(
                1e-12 < weight < constraints.min_position_weight - 1e-12
                for weight in target_map.values()
            )
            or any(
                (band.minimum is not None and exposure_values[band.exposure_id] < band.minimum - 1e-12)
                or (band.maximum is not None and exposure_values[band.exposure_id] > band.maximum + 1e-12)
                for band in exposure_rows
            )
        ):
            continue
        metrics = {
            "expected_excess_return": sum(
                target_map[row.entity_id] * row.robust_expected_excess_return for row in candidates
            ),
            "weighted_downside": downside,
            "thesis_confidence": sum(
                target_map[row.entity_id] * row.robust_thesis_confidence for row in candidates
            ),
            "nominal_expected_excess_return": sum(
                target_map[row.entity_id] * row.expected_excess_return for row in candidates
            ),
            "nominal_weighted_downside": nominal_downside,
            "nominal_thesis_confidence": sum(
                target_map[row.entity_id] * row.thesis_confidence for row in candidates
            ),
            "turnover": turnover,
            "estimated_cost_weight": sum(
                row.estimated_cost_weight for row in accepted
                if row.target_weight != row.current_weight
            ),
            "cash_weight": 1 - invested,
        }
        metrics.update({f"exposure:{identity}": value for identity, value in exposure_values.items()})
        metrics["robustness_return_cost"] = (
            metrics["nominal_expected_excess_return"] - metrics["expected_excess_return"]
        )
        metrics["robustness_downside_buffer"] = (
            metrics["weighted_downside"] - metrics["nominal_weighted_downside"]
        )
        utility = sum(row.utility(metrics[row.metric]) for row in objective_rows)
        alternative = PortfolioAlternative(
            accepted_decision_ids=tuple(accepted_ids),
            target_weights=targets,
            metrics=tuple(metrics.items()),
            utility=utility,
        )
        if patient_capital_policy is not None:
            review = compile_patient_rotation_review(
                candidates, target_map, patient_capital_policy,
            )
            if not review["compliant"]:
                rotation_rejections.append({
                    "alternative_id": alternative.alternative_id,
                    "target_weights": target_map,
                    "utility": utility,
                    "review": review,
                })
                continue
            patient_reviews[alternative.alternative_id] = review
        alternatives.setdefault(alternative.target_weights, alternative)
    rows = tuple(sorted(alternatives.values(), key=lambda row: row.alternative_id))
    if not rows:
        raise ValueError("portfolio constraints admit no candidate assembly")
    frontier = tuple(
        row for row in rows
        if not any(_dominates(other, row, objective_rows) for other in rows if other != row)
    )
    selected = sorted(frontier, key=lambda row: (-row.utility, row.alternative_id))[0]
    nominal_utilities = {
        row.alternative_id: _nominal_utility(row, objective_rows) for row in rows
    }
    nominal_selected = sorted(
        rows, key=lambda row: (-nominal_utilities[row.alternative_id], row.alternative_id),
    )[0]
    domination_witnesses = {
        row.alternative_id: min(
            other.alternative_id for other in rows if _dominates(other, row, objective_rows)
        )
        for row in rows if row not in frontier
    }
    objective_weight_regions = compile_linear_preference_regions(
        objective_names=tuple(row.objective_id for row in objective_rows),
        alternatives={
            alternative.alternative_id: {
                objective.objective_id: (
                    (1 if objective.direction == "maximize" else -1)
                    * dict(alternative.metrics)[objective.metric]
                    / objective.scale
                )
                for objective in objective_rows
            }
            for alternative in frontier
        },
    )
    utility_frontier, utility_equivalence = _nominal_robust_utility_frontier(
        rows, nominal_utilities,
    )
    mechanism_weight_certificate = compile_linear_preference_regions(
        objective_names=("nominal_utility", "mechanism_safe_utility"),
        alternatives={
            row.alternative_id: {
                "nominal_utility": nominal_utilities[row.alternative_id],
                "mechanism_safe_utility": row.utility,
            }
            for row in utility_frontier
        },
    )
    mechanism_weight_body = {
        "schema": "jaggedthoughts-mechanism-weight-regions-v1",
        "certificate": mechanism_weight_certificate,
        "interpretation": {
            "nominal_utility_weight": "weight on the initial-state estimates",
            "mechanism_safe_utility_weight": (
                "weight on the per-candidate adverse bound across the declared mechanism committee"
            ),
            "probability_interpretation": False,
        },
        "frontier_alternative_ids": [row.alternative_id for row in utility_frontier],
        "equivalent_alternatives": utility_equivalence,
    }
    mechanism_weight_regions = {
        **mechanism_weight_body,
        "mechanism_weight_regions_sha256": stable_sha256(mechanism_weight_body),
    }
    robust_nominal_utility = nominal_utilities[selected.alternative_id]
    nominal_robust_utility = nominal_selected.utility
    selection_tradeoff = {
        "allocation_changed_by_mechanism_weight": (
            selected.alternative_id != nominal_selected.alternative_id
        ),
        "nominal_optimal_utility": nominal_utilities[nominal_selected.alternative_id],
        "mechanism_safe_optimal_utility": selected.utility,
        "nominal_utility_of_mechanism_safe_policy": robust_nominal_utility,
        "mechanism_safe_utility_of_nominal_policy": nominal_robust_utility,
        "nominal_opportunity_cost_of_mechanism_safe_policy": max(
            0.0,
            nominal_utilities[nominal_selected.alternative_id] - robust_nominal_utility,
        ),
        "mechanism_protection_of_mechanism_safe_policy": max(
            0.0, selected.utility - nominal_robust_utility,
        ),
    }
    body = {
        "schema": PORTFOLIO_ASSEMBLY_SCHEMA,
        "portfolio_id": require_text(portfolio_id, "portfolio_id"),
        "owner": owner,
        "as_of": canonical_as_of,
        "benchmark_id": benchmark_id,
        "currency": currency,
        "starting_book_sha256": book_sha256,
        "profile_source_sha256": profile_source_sha256,
        "authority": "paper",
        "candidates": [row.to_dict() for row in candidates],
        "uncertainty_set": continuous_allocation_envelope["uncertainty_set"],
        "objective_basis": "maximin over nominal state plus the rectangular declared-mechanism committee",
        "constraints": constraints.to_dict(),
        "objectives": [row.to_dict() for row in objective_rows],
        "fixed_position_weights": fixed_position_weights,
        "fixed_invested_weight": fixed_invested_weight,
        "combination_count": combinations,
        "feasibility_certificate": feasibility_certificate,
        "continuous_allocation_envelope": continuous_allocation_envelope,
        "feasible_alternatives": [row.to_dict() for row in rows],
        "frontier_alternative_ids": [row.alternative_id for row in frontier],
        "domination_witnesses": domination_witnesses,
        "objective_weight_regions": objective_weight_regions,
        "mechanism_weight_regions": mechanism_weight_regions,
        "selected_alternative_id": selected.alternative_id,
        "selected_target_weights": dict(selected.target_weights),
        "selected_metrics": dict(selected.metrics),
        "selected_utility": selected.utility,
        "nominal_selected_alternative_id": nominal_selected.alternative_id,
        "nominal_selected_target_weights": dict(nominal_selected.target_weights),
        "nominal_selected_metrics": dict(nominal_selected.metrics),
        "nominal_selected_utility": nominal_utilities[nominal_selected.alternative_id],
        "selection_tradeoff": selection_tradeoff,
        "scope_closed": True,
    }
    if exposure_rows:
        body["exposure_bands"] = [row.to_dict() for row in exposure_rows]
        body["selected_exposures"] = {
            row.exposure_id: dict(selected.metrics)[f"exposure:{row.exposure_id}"]
            for row in exposure_rows
        }
    if patient_capital_policy is not None:
        body["patient_capital"] = {
            "policy": patient_capital_policy.to_dict(),
            "selected_review": patient_reviews[selected.alternative_id],
            "admissible_alternative_count": len(rows),
            "rejected_rotation_count": len(rotation_rejections),
            "rejected_rotations": sorted(
                rotation_rejections, key=lambda row: row["alternative_id"],
            ),
            "continuous_envelope_boundary": (
                "The continuous envelope reports geometric weight bounds; patient-capital "
                "replacement matching governs the executable discrete alternatives."
            ),
        }
    return {**body, "portfolio_assembly_sha256": stable_sha256(body)}


def compile_portfolio_profile_file(path: str | Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    profile_path = Path(path).expanduser().resolve()
    raw = profile_path.read_text(encoding="utf-8")
    payload = json.loads(raw) if profile_path.suffix.lower() == ".json" else yaml.safe_load(raw)
    if not isinstance(payload, Mapping) or payload.get("schema") != PORTFOLIO_PROFILE_SCHEMA:
        raise ValueError(f"portfolio profile schema must be {PORTFOLIO_PROFILE_SCHEMA}")
    decision_rows: list[dict[str, Any]] = []
    decision_files = payload.get("decision_files", [])
    investment_profiles = payload.get("investment_profile_files", [])
    if not isinstance(decision_files, list) or not isinstance(investment_profiles, list):
        raise ValueError("portfolio decision_files and investment_profile_files must be lists")

    def local_source(relative: Any) -> Path:
        source = (profile_path.parent / require_text(relative, "portfolio input file")).resolve()
        try:
            source.relative_to(profile_path.parent)
        except ValueError as error:
            raise ValueError(f"portfolio input file escapes profile root: {relative}") from error
        return source

    for relative in decision_files:
        source = local_source(relative)
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"portfolio decision must be a JSON object: {relative}")
        decision_rows.append(value)
    if investment_profiles:
        from .compiler import compile_investment_profile_file

        decision_rows.extend(
            compile_investment_profile_file(local_source(relative))
            for relative in investment_profiles
        )
    if not decision_rows:
        raise ValueError("portfolio profile must name at least one decision or investment profile")
    raw_constraints = payload.get("constraints")
    if not isinstance(raw_constraints, Mapping):
        raise ValueError("portfolio constraints must be a mapping")
    constraints = PortfolioConstraints(
        constraint_id=str(raw_constraints.get("id", "")),
        max_invested_weight=float(raw_constraints["max_invested_weight"]),
        max_candidate_weight=float(raw_constraints["max_candidate_weight"]),
        max_turnover_weight=float(raw_constraints["max_turnover_weight"]),
        max_weighted_downside=float(raw_constraints["max_weighted_downside"]),
        fixed_weighted_downside=float(raw_constraints.get("fixed_weighted_downside", 0)),
        max_positions=(
            int(raw_constraints["max_positions"])
            if raw_constraints.get("max_positions") is not None else None
        ),
        min_position_weight=float(raw_constraints.get("min_position_weight", 0)),
    )
    patient_raw = payload.get("patient_capital")
    patient_policy = (
        PatientCapitalPolicy(
            policy_id=str(patient_raw.get("id") or ""),
            minimum_after_cost_return_edge=float(
                patient_raw["minimum_after_cost_return_edge"]
            ),
            impairment_return_floor=float(patient_raw["impairment_return_floor"]),
            impairment_confidence_floor=float(patient_raw["impairment_confidence_floor"]),
        ) if isinstance(patient_raw, Mapping) else None
    )
    exposure_bands = tuple(PortfolioExposureBand(
        exposure_id=str(row.get("id") or ""),
        minimum=float(row["minimum"]) if row.get("minimum") is not None else None,
        maximum=float(row["maximum"]) if row.get("maximum") is not None else None,
        fixed_exposure=float(row.get("fixed_exposure", 0)),
        coefficients=tuple((str(key), float(value)) for key, value in dict(
            row.get("coefficients") or {},
        ).items()),
        source_refs=tuple(str(value) for value in row.get("source_refs") or ()),
    ) for row in payload.get("exposure_bands", []))
    objectives = tuple(PortfolioObjective(
        objective_id=str(row["id"]),
        metric=str(row["metric"]),
        direction=str(row["direction"]),
        scale=float(row["scale"]),
        utility_weight=float(row["utility_weight"]),
    ) for row in payload.get("objectives", []))
    assembly = compile_portfolio_assembly(
        portfolio_id=str(payload.get("portfolio_id", "")),
        decisions=decision_rows,
        constraints=constraints,
        objectives=objectives,
        exposure_bands=exposure_bands,
        patient_capital_policy=patient_policy,
        max_combinations=int(payload.get("max_combinations", 65_536)),
        profile_source_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),
    )
    return assembly, tuple(decision_rows)


__all__ = [
    "PORTFOLIO_ASSEMBLY_SCHEMA",
    "PORTFOLIO_PROFILE_SCHEMA",
    "PatientCapitalPolicy",
    "PortfolioAlternative",
    "PortfolioCandidate",
    "PortfolioConstraints",
    "PortfolioExposureBand",
    "PortfolioMechanismScenario",
    "PortfolioObjective",
    "compile_portfolio_assembly",
    "compile_patient_rotation_review",
    "compile_portfolio_profile_file",
]
