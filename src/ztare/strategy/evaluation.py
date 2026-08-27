"""Automatic multi-scenario factor evaluation for JaggedThoughts programs."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Literal, Sequence

from .jaggedthoughts import CandidateEvaluation, Program


AggregationMode = Literal["scenario_vector", "weighted_mean", "worst_case"]


@dataclass(frozen=True, slots=True)
class StrategicFactor:
    factor_id: str
    requires: tuple[str, ...]
    delta: tuple[float, ...]
    evidence_refs: tuple[str, ...]
    alternatives: tuple[tuple[float, ...], ...] = ()
    question: str = ""
    test: str = ""
    cost: float = 1.0

    def __post_init__(self) -> None:
        if not self.factor_id.strip() or not self.requires:
            raise ValueError("strategic factors require identity and symbols")
        if len(self.requires) != len(set(self.requires)):
            raise ValueError("strategic factor requirements must be unique")
        if not self.delta or not all(math.isfinite(value) for value in self.delta):
            raise ValueError("strategic factor deltas must be finite")
        if not self.evidence_refs:
            raise ValueError("strategic factors require source-bound evidence")
        if any(len(alternative) != len(self.delta) for alternative in self.alternatives):
            raise ValueError("strategic factor alternative arity must match delta")
        if any(
            not all(math.isfinite(value) for value in alternative)
            for alternative in self.alternatives
        ):
            raise ValueError("strategic factor alternatives must be finite")
        if self.alternatives and (not self.question.strip() or not self.test.strip()):
            raise ValueError(
                "uncertain strategic factors require a question and test"
            )
        if not math.isfinite(self.cost) or self.cost <= 0:
            raise ValueError("strategic factor cost must be finite and positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "requires": list(self.requires),
            "delta": list(self.delta),
            "evidence_refs": list(self.evidence_refs),
            "alternatives": [list(values) for values in self.alternatives],
            "question": self.question,
            "test": self.test,
            "cost": self.cost,
        }


@dataclass(frozen=True, slots=True)
class StrategicScenario:
    scenario_id: str
    weight: float
    base: tuple[float, ...]
    factors: tuple[StrategicFactor, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("strategic scenarios require identity")
        if not math.isfinite(self.weight) or self.weight < 0:
            raise ValueError("scenario weight must be finite and non-negative")
        if not self.base or not all(math.isfinite(value) for value in self.base):
            raise ValueError("scenario base values must be finite")
        if not self.evidence_refs:
            raise ValueError("strategic scenarios require source-bound evidence")
        if any(len(factor.delta) != len(self.base) for factor in self.factors):
            raise ValueError("scenario factor arity does not match its base")
        if len({factor.factor_id for factor in self.factors}) != len(self.factors):
            raise ValueError("scenario factor IDs must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "weight": self.weight,
            "base": list(self.base),
            "factors": [factor.to_dict() for factor in self.factors],
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class FactorEvaluationModel:
    model_id: str
    objective_names: tuple[str, ...]
    aggregation: AggregationMode
    scenarios: tuple[StrategicScenario, ...]

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.objective_names:
            raise ValueError("factor model requires identity and objectives")
        if len(self.objective_names) != len(set(self.objective_names)):
            raise ValueError("factor model objective names must be unique")
        if self.aggregation not in {
            "scenario_vector",
            "weighted_mean",
            "worst_case",
        }:
            raise ValueError(f"unsupported aggregation: {self.aggregation}")
        if not self.scenarios:
            raise ValueError("factor model requires at least one scenario")
        if len({scenario.scenario_id for scenario in self.scenarios}) != len(
            self.scenarios
        ):
            raise ValueError("factor model scenario IDs must be unique")
        if any(
            len(scenario.base) != len(self.objective_names)
            for scenario in self.scenarios
        ):
            raise ValueError("scenario base arity does not match objectives")
        if self.aggregation == "weighted_mean" and sum(
            scenario.weight for scenario in self.scenarios
        ) <= 0:
            raise ValueError("weighted_mean requires positive total weight")

    @property
    def compiled_objective_names(self) -> tuple[str, ...]:
        if self.aggregation != "scenario_vector":
            return self.objective_names
        return tuple(
            f"{scenario.scenario_id}::{objective}"
            for scenario in self.scenarios
            for objective in self.objective_names
        )

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(sorted({
            ref
            for scenario in self.scenarios
            for ref in (
                *scenario.evidence_refs,
                *(ref for factor in scenario.factors for ref in factor.evidence_refs),
            )
        }))

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "objective_names": list(self.objective_names),
            "compiled_objective_names": list(self.compiled_objective_names),
            "aggregation": self.aggregation,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
        }


@dataclass(frozen=True, slots=True)
class ScenarioScore:
    scenario_id: str
    values: tuple[float, ...]
    applied_factor_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "values": list(self.values),
            "applied_factor_ids": list(self.applied_factor_ids),
            "evidence_refs": list(self.evidence_refs),
        }


def program_symbol_ids(program: Program) -> frozenset[str]:
    symbols = {program.root_symbol}
    for child in program.children:
        symbols.update(program_symbol_ids(child))
    return frozenset(symbol for symbol in symbols if symbol)


def score_program(
    program: Program,
    model: FactorEvaluationModel,
) -> tuple[ScenarioScore, ...]:
    symbols = program_symbol_ids(program)
    scores: list[ScenarioScore] = []
    for scenario in model.scenarios:
        values = list(scenario.base)
        applied: list[str] = []
        evidence = set(scenario.evidence_refs)
        for factor in scenario.factors:
            if set(factor.requires).issubset(symbols):
                values = [
                    current + delta
                    for current, delta in zip(values, factor.delta, strict=True)
                ]
                applied.append(factor.factor_id)
                evidence.update(factor.evidence_refs)
        scores.append(ScenarioScore(
            scenario_id=scenario.scenario_id,
            values=tuple(values),
            applied_factor_ids=tuple(applied),
            evidence_refs=tuple(sorted(evidence)),
        ))
    return tuple(scores)


def _aggregate(
    scores: Sequence[ScenarioScore],
    model: FactorEvaluationModel,
) -> tuple[float, ...]:
    if model.aggregation == "scenario_vector":
        return tuple(value for score in scores for value in score.values)
    if model.aggregation == "worst_case":
        return tuple(
            min(score.values[index] for score in scores)
            for index in range(len(model.objective_names))
        )
    total_weight = sum(scenario.weight for scenario in model.scenarios)
    return tuple(
        sum(
            scenario.weight * score.values[index]
            for scenario, score in zip(model.scenarios, scores, strict=True)
        )
        / total_weight
        for index in range(len(model.objective_names))
    )


def compile_factor_evaluations(
    programs: Iterable[Program],
    model: FactorEvaluationModel,
) -> tuple[CandidateEvaluation, ...]:
    evaluations: list[CandidateEvaluation] = []
    for program in programs:
        scores = score_program(program, model)
        behavior_signature = tuple(
            f"{score.scenario_id}|"
            + ",".join(format(value, ".17g") for value in score.values)
            + "|"
            + ",".join(score.applied_factor_ids)
            for score in scores
        )
        evidence_refs = tuple(sorted({
            ref for score in scores for ref in score.evidence_refs
        }))
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id,
            objective_values=_aggregate(scores, model),
            behavior_signature=behavior_signature,
            evidence_refs=evidence_refs,
        ))
    return tuple(evaluations)
