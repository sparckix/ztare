"""Cross-grammar representation challenges for JaggedThoughts.

A frozen grammar may be exhausted while omitting a decision-relevant program.
This module compares a baseline profile with a challenger grammar under the
same evaluation surface.  Program hashes cannot cross grammar epochs, so exact
behavior signatures own comparison.  A novel challenger behavior creates
representation debt only when it survives the Pareto frontier of the combined
baseline and challenger population.

One challenger can expose debt.  Absence of debt in one challenge remains an
unassessed representation state; it cannot mint a pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .jaggedthoughts import RepresentationAudit
from .profile import CompiledJaggedThoughtsProfile


@dataclass(frozen=True, slots=True)
class FrontierBehavior:
    behavior_signature: tuple[str, ...]
    objective_values: tuple[float, ...]
    program_id: str
    profile_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "behavior_signature": list(self.behavior_signature),
            "objective_values": list(self.objective_values),
            "program_id": self.program_id,
            "profile_id": self.profile_id,
        }


@dataclass(frozen=True, slots=True)
class GrammarDelta:
    added_terminal_ids: tuple[str, ...]
    removed_terminal_ids: tuple[str, ...]
    added_operator_ids: tuple[str, ...]
    removed_operator_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_terminal_ids": list(self.added_terminal_ids),
            "removed_terminal_ids": list(self.removed_terminal_ids),
            "added_operator_ids": list(self.added_operator_ids),
            "removed_operator_ids": list(self.removed_operator_ids),
        }


@dataclass(frozen=True, slots=True)
class RepresentationChallenge:
    challenge_id: str
    baseline_profile_id: str
    challenger_profile_id: str
    baseline_scope_id: str
    challenger_scope_id: str
    grammar_delta: GrammarDelta
    shared_behavior_signatures: tuple[tuple[str, ...], ...]
    novel_challenger_behaviors: tuple[FrontierBehavior, ...]
    material_frontier_behaviors: tuple[FrontierBehavior, ...]
    dominated_novel_behaviors: tuple[FrontierBehavior, ...]
    retained_baseline_frontier_signatures: tuple[tuple[str, ...], ...]
    representation_status: str

    def __post_init__(self) -> None:
        if self.representation_status not in {"unassessed", "residual"}:
            raise ValueError("one grammar challenge can only expose debt or remain open")

    def to_representation_audit(self) -> RepresentationAudit:
        evidence_ref = (
            "jaggedthoughts-challenge://"
            f"{self.challenge_id}/{self.baseline_scope_id}/{self.challenger_scope_id}"
        )
        if self.representation_status == "residual":
            residuals = tuple(
                "novel combined-frontier behavior: " + " | ".join(
                    behavior.behavior_signature
                )
                for behavior in self.material_frontier_behaviors
            )
            return RepresentationAudit(
                audit_id=self.challenge_id,
                status="residual",
                residuals=residuals,
                evidence_refs=(evidence_ref,),
            )
        return RepresentationAudit(
            audit_id=self.challenge_id,
            status="unassessed",
            evidence_refs=(evidence_ref,),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "baseline_profile_id": self.baseline_profile_id,
            "challenger_profile_id": self.challenger_profile_id,
            "novel_behavior_count": len(self.novel_challenger_behaviors),
            "material_frontier_behavior_count": len(
                self.material_frontier_behaviors
            ),
            "dominated_novel_behavior_count": len(
                self.dominated_novel_behaviors
            ),
            "representation_status": self.representation_status,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "challenge_id": self.challenge_id,
            "baseline_profile_id": self.baseline_profile_id,
            "challenger_profile_id": self.challenger_profile_id,
            "baseline_scope_id": self.baseline_scope_id,
            "challenger_scope_id": self.challenger_scope_id,
            "grammar_delta": self.grammar_delta.to_dict(),
            "shared_behavior_signatures": [
                list(signature) for signature in self.shared_behavior_signatures
            ],
            "novel_challenger_behaviors": [
                behavior.to_dict() for behavior in self.novel_challenger_behaviors
            ],
            "material_frontier_behaviors": [
                behavior.to_dict() for behavior in self.material_frontier_behaviors
            ],
            "dominated_novel_behaviors": [
                behavior.to_dict() for behavior in self.dominated_novel_behaviors
            ],
            "retained_baseline_frontier_signatures": [
                list(signature)
                for signature in self.retained_baseline_frontier_signatures
            ],
            "representation_status": self.representation_status,
        }


def _dominates(left: Sequence[float], right: Sequence[float]) -> bool:
    return all(a >= b for a, b in zip(left, right, strict=True)) and any(
        a > b for a, b in zip(left, right, strict=True)
    )


def _behaviors(
    profile: CompiledJaggedThoughtsProfile,
) -> dict[tuple[str, ...], FrontierBehavior]:
    result: dict[tuple[str, ...], FrontierBehavior] = {}
    for evaluation in profile.evaluations:
        behavior = FrontierBehavior(
            behavior_signature=evaluation.behavior_signature,
            objective_values=evaluation.objective_values,
            program_id=evaluation.program_id,
            profile_id=profile.profile_id,
        )
        existing = result.get(behavior.behavior_signature)
        if existing is not None and existing.objective_values != behavior.objective_values:
            raise ValueError(
                "one profile assigns conflicting values to one behavior signature"
            )
        if existing is None or behavior.program_id < existing.program_id:
            result[behavior.behavior_signature] = behavior
    return result


def _frontier(
    behaviors: Iterable[FrontierBehavior],
) -> tuple[FrontierBehavior, ...]:
    population = tuple(behaviors)
    return tuple(sorted(
        (
            behavior
            for behavior in population
            if not any(
                other.behavior_signature != behavior.behavior_signature
                and _dominates(other.objective_values, behavior.objective_values)
                for other in population
            )
        ),
        key=lambda behavior: behavior.behavior_signature,
    ))


def _assert_comparable(
    baseline: CompiledJaggedThoughtsProfile,
    challenger: CompiledJaggedThoughtsProfile,
) -> None:
    left = baseline.certificate.scope
    right = challenger.certificate.scope
    left_model_family = left.evaluation_model_id.split("@sha256:", 1)[0]
    right_model_family = right.evaluation_model_id.split("@sha256:", 1)[0]
    comparable = (
        left.target_type,
        left_model_family,
        left.landscape_mode,
        left.evidence_epoch,
        left.objective_names,
    ) == (
        right.target_type,
        right_model_family,
        right.landscape_mode,
        right.evidence_epoch,
        right.objective_names,
    )
    if not comparable:
        raise ValueError(
            "grammar challenge requires the same target and evaluation surface"
        )


def challenge_representation(
    *,
    challenge_id: str,
    baseline: CompiledJaggedThoughtsProfile,
    challenger: CompiledJaggedThoughtsProfile,
) -> RepresentationChallenge:
    """Compare two grammar epochs and expose decision-relevant new behaviors."""
    if not challenge_id.strip():
        raise ValueError("challenge_id must be non-empty")
    _assert_comparable(baseline, challenger)
    baseline_behaviors = _behaviors(baseline)
    challenger_behaviors = _behaviors(challenger)
    shared = set(baseline_behaviors) & set(challenger_behaviors)
    for signature in shared:
        if (
            baseline_behaviors[signature].objective_values
            != challenger_behaviors[signature].objective_values
        ):
            raise ValueError(
                "shared behavior changed value inside one evaluation surface"
            )

    novel_signatures = set(challenger_behaviors) - set(baseline_behaviors)
    novel = tuple(
        challenger_behaviors[signature] for signature in sorted(novel_signatures)
    )
    union = dict(baseline_behaviors)
    union.update(challenger_behaviors)
    union_frontier = _frontier(union.values())
    union_frontier_signatures = {
        behavior.behavior_signature for behavior in union_frontier
    }
    material = tuple(
        behavior
        for behavior in novel
        if behavior.behavior_signature in union_frontier_signatures
    )
    dominated = tuple(
        behavior
        for behavior in novel
        if behavior.behavior_signature not in union_frontier_signatures
    )
    baseline_frontier_signatures = {
        baseline_behaviors[program_signature].behavior_signature
        for program_signature in baseline_behaviors
        if baseline_behaviors[program_signature].program_id
        in baseline.certificate.frontier_program_ids
    }
    retained = tuple(sorted(
        baseline_frontier_signatures & union_frontier_signatures
    ))

    baseline_terminals = {
        terminal.terminal_id for terminal in baseline.grammar.terminals
    }
    challenger_terminals = {
        terminal.terminal_id for terminal in challenger.grammar.terminals
    }
    baseline_operators = {
        operator.operator_id for operator in baseline.grammar.operators
    }
    challenger_operators = {
        operator.operator_id for operator in challenger.grammar.operators
    }
    return RepresentationChallenge(
        challenge_id=challenge_id,
        baseline_profile_id=baseline.profile_id,
        challenger_profile_id=challenger.profile_id,
        baseline_scope_id=baseline.certificate.scope.scope_id,
        challenger_scope_id=challenger.certificate.scope.scope_id,
        grammar_delta=GrammarDelta(
            added_terminal_ids=tuple(sorted(
                challenger_terminals - baseline_terminals
            )),
            removed_terminal_ids=tuple(sorted(
                baseline_terminals - challenger_terminals
            )),
            added_operator_ids=tuple(sorted(
                challenger_operators - baseline_operators
            )),
            removed_operator_ids=tuple(sorted(
                baseline_operators - challenger_operators
            )),
        ),
        shared_behavior_signatures=tuple(sorted(shared)),
        novel_challenger_behaviors=novel,
        material_frontier_behaviors=material,
        dominated_novel_behaviors=dominated,
        retained_baseline_frontier_signatures=retained,
        representation_status="residual" if material else "unassessed",
    )
