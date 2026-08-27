"""Frontier-sensitive next-question selection for JaggedThoughts.

The agenda is possibilistic: declared factor alternatives are treated as a
committee of possible decision surfaces, not as probabilistic forecasts. Each
single or joint probe recompiles global and local frontiers. Ranking is
lexicographic and inspectable: decision-pivotal probes first, then distinct
information per declared cost, maximum membership displacement, distinct
frontier outcomes, declared cost, and stable identity.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations, product
import math
from typing import Any, TYPE_CHECKING

from ztare.common.information_yield_pricing import identification_bits

from .evaluation import (
    FactorEvaluationModel,
    StrategicFactor,
    compile_factor_evaluations,
)
from .jaggedthoughts import Neighborhood, Program

if TYPE_CHECKING:
    from .profile import CompiledJaggedThoughtsProfile


@dataclass(frozen=True, slots=True)
class FactorLocator:
    scenario_index: int
    factor_index: int
    scenario_id: str
    factor: StrategicFactor

    @property
    def locator_id(self) -> str:
        return f"{self.scenario_id}::{self.factor.factor_id}"


@dataclass(frozen=True, slots=True)
class FrontierProbe:
    probe_id: str
    factor_ids: tuple[str, ...]
    questions: tuple[str, ...]
    tests: tuple[str, ...]
    cost: float
    world_count: int
    frontier_outcome_count: int
    identification_bits: float
    max_frontier_membership_change: int
    max_local_peak_membership_change: int
    decision_pivotal: bool
    frontier_outcomes: tuple[tuple[str, ...], ...]

    @property
    def information_per_cost(self) -> float:
        return self.identification_bits / self.cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "factor_ids": list(self.factor_ids),
            "questions": list(self.questions),
            "tests": list(self.tests),
            "cost": self.cost,
            "world_count": self.world_count,
            "frontier_outcome_count": self.frontier_outcome_count,
            "identification_bits": round(self.identification_bits, 8),
            "information_per_cost": round(self.information_per_cost, 8),
            "max_frontier_membership_change": (
                self.max_frontier_membership_change
            ),
            "max_local_peak_membership_change": (
                self.max_local_peak_membership_change
            ),
            "decision_pivotal": self.decision_pivotal,
            "frontier_outcomes": [list(row) for row in self.frontier_outcomes],
        }


@dataclass(frozen=True, slots=True)
class ExplorationAgenda:
    max_joint_size: int
    max_worlds_per_probe: int
    baseline_frontier_program_ids: tuple[str, ...]
    probes: tuple[FrontierProbe, ...]
    skipped_probe_ids: tuple[str, ...]
    next_action: str
    boundary: str

    @property
    def pivotal_probe_count(self) -> int:
        return sum(probe.decision_pivotal for probe in self.probes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-exploration-agenda-v1",
            "max_joint_size": self.max_joint_size,
            "max_worlds_per_probe": self.max_worlds_per_probe,
            "baseline_frontier_program_ids": list(
                self.baseline_frontier_program_ids
            ),
            "probe_count": len(self.probes),
            "pivotal_probe_count": self.pivotal_probe_count,
            "probes": [probe.to_dict() for probe in self.probes],
            "skipped_probe_ids": list(self.skipped_probe_ids),
            "next_action": self.next_action,
            "boundary": self.boundary,
        }


def _dominates(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return all(a >= b for a, b in zip(left, right, strict=True)) and any(
        a > b for a, b in zip(left, right, strict=True)
    )


def _frontier_and_peaks(
    programs: tuple[Program, ...],
    model: FactorEvaluationModel,
    neighborhood: Neighborhood,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    evaluations = {
        evaluation.program_id: evaluation
        for evaluation in compile_factor_evaluations(programs, model)
    }
    frontier = tuple(sorted(
        program.program_id
        for program in programs
        if not any(
            other.program_id != program.program_id
            and _dominates(
                evaluations[other.program_id].objective_values,
                evaluations[program.program_id].objective_values,
            )
            for other in programs
        )
    ))
    neighbors: dict[str, set[str]] = {
        program.program_id: set() for program in programs
    }
    for left, right in neighborhood.edges:
        if left in neighbors and right in neighbors:
            neighbors[left].add(right)
            neighbors[right].add(left)
    peaks = tuple(sorted(
        program.program_id
        for program in programs
        if not any(
            _dominates(
                evaluations[neighbor].objective_values,
                evaluations[program.program_id].objective_values,
            )
            for neighbor in neighbors[program.program_id]
        )
    ))
    return frontier, peaks


def _uncertain_factors(model: FactorEvaluationModel) -> tuple[FactorLocator, ...]:
    return tuple(
        FactorLocator(
            scenario_index=scenario_index,
            factor_index=factor_index,
            scenario_id=scenario.scenario_id,
            factor=factor,
        )
        for scenario_index, scenario in enumerate(model.scenarios)
        for factor_index, factor in enumerate(scenario.factors)
        if factor.alternatives
    )


def _model_with_values(
    model: FactorEvaluationModel,
    assignments: tuple[tuple[FactorLocator, tuple[float, ...]], ...],
) -> FactorEvaluationModel:
    scenarios = list(model.scenarios)
    by_scenario: dict[int, list[tuple[FactorLocator, tuple[float, ...]]]] = {}
    for locator, values in assignments:
        by_scenario.setdefault(locator.scenario_index, []).append((locator, values))
    for scenario_index, changes in by_scenario.items():
        scenario = scenarios[scenario_index]
        factors = list(scenario.factors)
        for locator, values in changes:
            factors[locator.factor_index] = replace(
                factors[locator.factor_index],
                delta=values,
            )
        scenarios[scenario_index] = replace(scenario, factors=tuple(factors))
    return replace(model, scenarios=tuple(scenarios))


def _probe(
    locators: tuple[FactorLocator, ...],
    *,
    model: FactorEvaluationModel,
    programs: tuple[Program, ...],
    neighborhood: Neighborhood,
    baseline_frontier: tuple[str, ...],
    baseline_peaks: tuple[str, ...],
) -> FrontierProbe:
    choices = tuple(
        (locator.factor.delta, *locator.factor.alternatives)
        for locator in locators
    )
    outcomes: list[tuple[str, ...]] = []
    peak_outcomes: list[tuple[str, ...]] = []
    for values in product(*choices):
        world = _model_with_values(
            model,
            tuple(zip(locators, values, strict=True)),
        )
        frontier, peaks = _frontier_and_peaks(programs, world, neighborhood)
        outcomes.append(frontier)
        peak_outcomes.append(peaks)
    cells: dict[tuple[str, ...], list[int]] = {}
    for index, outcome in enumerate(outcomes):
        cells.setdefault(outcome, []).append(index)
    baseline_frontier_set = set(baseline_frontier)
    baseline_peak_set = set(baseline_peaks)
    max_frontier_change = max(
        len(baseline_frontier_set.symmetric_difference(outcome))
        for outcome in map(set, outcomes)
    )
    max_peak_change = max(
        len(baseline_peak_set.symmetric_difference(outcome))
        for outcome in map(set, peak_outcomes)
    )
    factor_ids = tuple(locator.locator_id for locator in locators)
    return FrontierProbe(
        probe_id=" + ".join(factor_ids),
        factor_ids=factor_ids,
        questions=tuple(locator.factor.question for locator in locators),
        tests=tuple(locator.factor.test for locator in locators),
        cost=sum(locator.factor.cost for locator in locators),
        world_count=len(outcomes),
        frontier_outcome_count=len(cells),
        identification_bits=identification_bits(cells, len(outcomes)),
        max_frontier_membership_change=max_frontier_change,
        max_local_peak_membership_change=max_peak_change,
        decision_pivotal=len(cells) > 1,
        frontier_outcomes=tuple(sorted(cells)),
    )


def build_exploration_agenda(
    compiled: CompiledJaggedThoughtsProfile,
    *,
    max_joint_size: int = 2,
    max_worlds_per_probe: int = 64,
) -> ExplorationAgenda:
    """Rank declared evidence tests by their ability to alter the frontier."""
    if max_joint_size < 1 or max_worlds_per_probe < 2:
        raise ValueError("exploration bounds are invalid")
    boundary = (
        "This agenda selects among declared uncertainties and tests. It does "
        "not invent source facts, certify causal effects, or pass a "
        "representation audit."
    )
    model = compiled.evaluation_model
    if model is None:
        return ExplorationAgenda(
            max_joint_size,
            max_worlds_per_probe,
            compiled.certificate.frontier_program_ids,
            (),
            (),
            "Use a factor_graph evaluation model to compile a test agenda.",
            boundary,
        )
    blocked_ids = {
        witness.program_id for witness in compiled.certificate.infeasible
    } | set(compiled.certificate.residual_program_ids)
    target_ids = set(compiled.certificate.target_program_ids) - blocked_ids
    programs = tuple(
        program
        for program in compiled.enumeration.programs
        if program.program_id in target_ids
    )
    baseline_frontier, baseline_peaks = _frontier_and_peaks(
        programs,
        model,
        compiled.neighborhood,
    )
    uncertain = _uncertain_factors(model)
    probes: list[FrontierProbe] = []
    skipped: list[str] = []
    for size in range(1, min(max_joint_size, len(uncertain)) + 1):
        for locator_group in combinations(uncertain, size):
            probe_id = " + ".join(
                locator.locator_id for locator in locator_group
            )
            world_count = math.prod(
                1 + len(locator.factor.alternatives)
                for locator in locator_group
            )
            if world_count > max_worlds_per_probe:
                skipped.append(probe_id)
                continue
            probes.append(_probe(
                locator_group,
                model=model,
                programs=programs,
                neighborhood=compiled.neighborhood,
                baseline_frontier=baseline_frontier,
                baseline_peaks=baseline_peaks,
            ))
    probes.sort(key=lambda probe: (
        not probe.decision_pivotal,
        -probe.information_per_cost,
        -probe.max_frontier_membership_change,
        -probe.frontier_outcome_count,
        probe.cost,
        probe.probe_id,
    ))
    if probes and probes[0].decision_pivotal:
        next_action = (
            f"Run `{probes[0].tests[0]}` to resolve "
            f"`{probes[0].factor_ids[0]}`"
        )
        if len(probes[0].factor_ids) > 1:
            next_action = (
                "Resolve the joint probe `"
                + " + ".join(probes[0].factor_ids)
                + "` using its declared tests."
            )
    elif uncertain:
        next_action = (
            "Declared factor alternatives do not change the frontier within "
            "the probe bound; run an independent grammar challenge."
        )
    else:
        next_action = (
            "Declare plausible factor alternatives and executable evidence "
            "tests, then recompile the agenda."
        )
    return ExplorationAgenda(
        max_joint_size=max_joint_size,
        max_worlds_per_probe=max_worlds_per_probe,
        baseline_frontier_program_ids=baseline_frontier,
        probes=tuple(probes),
        skipped_probe_ids=tuple(sorted(skipped)),
        next_action=next_action,
        boundary=boundary,
    )
