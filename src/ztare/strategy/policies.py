"""Recursive contingent policies evaluated across a strategic model committee."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Literal, Mapping

from ztare.common.equivariance import stable_sha256

from .jaggedthoughts import (
    CandidateEvaluation,
    EnumerationResult,
    FrontierScope,
    JaggedThoughtsFrontierCertificate,
    Neighborhood,
    OperatorGrammar,
    Program,
    RepresentationAudit,
    TypedOperator,
    TypedTerminal,
    compile_jaggedthoughts_frontier,
    enumerate_typed_programs,
)
from .mechanisms import StrategicMechanism, predict_transition
from .transitions import StrategicAction, StrategicState


ConditionOperator = Literal["eq", "ne", "gt", "ge", "lt", "le"]
ObjectiveDirection = Literal["maximize", "minimize"]


@dataclass(frozen=True, slots=True)
class PolicyCondition:
    condition_id: str
    path: str
    operator: ConditionOperator
    value: float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.condition_id.strip() or not self.path.strip():
            raise ValueError("policy conditions require identity and state path")
        if self.operator not in {"eq", "ne", "gt", "ge", "lt", "le"}:
            raise ValueError(f"unsupported policy condition: {self.operator}")
        if not math.isfinite(float(self.value)):
            raise ValueError("policy condition value must be finite")
        if not self.evidence_refs:
            raise ValueError("policy conditions require evidence refs")

    def matches(self, state: StrategicState) -> bool:
        observed = state.value(self.path)
        return {
            "eq": observed == self.value,
            "ne": observed != self.value,
            "gt": observed > self.value,
            "ge": observed >= self.value,
            "lt": observed < self.value,
            "le": observed <= self.value,
        }[self.operator]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "path": self.path,
            "operator": self.operator,
            "value": self.value,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class PolicyObjective:
    objective_id: str
    path: str
    direction: ObjectiveDirection

    def __post_init__(self) -> None:
        if not self.objective_id.strip() or not self.path.strip():
            raise ValueError("policy objectives require identity and state path")
        if self.direction not in {"maximize", "minimize"}:
            raise ValueError(f"unsupported objective direction: {self.direction}")

    def score(self, state: StrategicState) -> float:
        value = state.value(self.path)
        return value if self.direction == "maximize" else -value

    def to_dict(self) -> dict[str, str]:
        return {
            "objective_id": self.objective_id,
            "path": self.path,
            "direction": self.direction,
        }


@dataclass(frozen=True, slots=True)
class PolicyRollout:
    program_id: str
    mechanism_id: str
    initial_state_sha256: str
    terminal_state: StrategicState
    action_ids: tuple[str, ...]
    state_sha256s: tuple[str, ...]
    objective_values: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "mechanism_id": self.mechanism_id,
            "initial_state_sha256": self.initial_state_sha256,
            "terminal_state": self.terminal_state.to_dict(),
            "action_ids": list(self.action_ids),
            "state_sha256s": list(self.state_sha256s),
            "objective_values": list(self.objective_values),
        }


@dataclass(frozen=True, slots=True)
class PolicySynthesis:
    grammar: OperatorGrammar
    enumeration: EnumerationResult
    neighborhood: Neighborhood
    objectives: tuple[PolicyObjective, ...]
    rollouts: tuple[PolicyRollout, ...]
    evaluations: tuple[CandidateEvaluation, ...]
    certificate: JaggedThoughtsFrontierCertificate
    synthesis_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-policy-synthesis-v1",
            "synthesis_sha256": self.synthesis_sha256,
            "objectives": [row.to_dict() for row in self.objectives],
            "enumeration": self.enumeration.to_dict(),
            "neighborhood": {
                "neighborhood_id": self.neighborhood.neighborhood_id,
                "edges": [list(edge) for edge in self.neighborhood.edges],
            },
            "rollouts": [row.to_dict() for row in self.rollouts],
            "evaluations": [
                {
                    "program_id": row.program_id,
                    "objective_values": list(row.objective_values),
                    "behavior_signature": list(row.behavior_signature),
                    "evidence_refs": list(row.evidence_refs),
                }
                for row in self.evaluations
            ],
            "certificate": self.certificate.to_dict(),
        }


def build_policy_grammar(
    *,
    grammar_id: str,
    version: str,
    actions: Iterable[StrategicAction],
    conditions: Iterable[PolicyCondition],
) -> OperatorGrammar:
    action_rows = tuple(sorted(actions, key=lambda row: row.action_id))
    condition_rows = tuple(sorted(conditions, key=lambda row: row.condition_id))
    if not action_rows:
        raise ValueError("policy grammar requires actions")
    return OperatorGrammar(
        grammar_id=grammar_id,
        version=version,
        terminals=tuple(
            TypedTerminal(
                terminal_id=f"act::{action.action_id}",
                output_type="Policy",
                description=action.description,
            )
            for action in action_rows
        ) + tuple(
            TypedTerminal(
                terminal_id=f"when::{condition.condition_id}",
                output_type="Condition",
                description=f"{condition.path} {condition.operator} {condition.value}",
            )
            for condition in condition_rows
        ),
        operators=(
            TypedOperator(
                operator_id="then",
                input_types=("Policy", "Policy"),
                output_type="Policy",
                description="Execute the left policy and then the right policy.",
            ),
            TypedOperator(
                operator_id="branch",
                input_types=("Condition", "Policy", "Policy"),
                output_type="Policy",
                description="Select a policy from the current strategic state.",
            ),
        ),
    )


def _program_shape(program: Program) -> tuple[str, ...]:
    if program.terminal_id is not None:
        prefix = program.terminal_id.split("::", 1)[0]
        return (f"terminal:{prefix}",)
    return (
        f"operator:{program.operator_id}",
        *(token for child in program.children for token in _program_shape(child)),
    )


def _program_terminals(program: Program) -> tuple[str, ...]:
    if program.terminal_id is not None:
        return (program.terminal_id,)
    return tuple(
        terminal
        for child in program.children
        for terminal in _program_terminals(child)
    )


def build_policy_neighborhood(programs: Iterable[Program]) -> Neighborhood:
    """Connect policies that differ by one terminal in the same tree shape."""
    groups: dict[tuple[str, ...], list[Program]] = {}
    for program in programs:
        groups.setdefault(_program_shape(program), []).append(program)
    edges: list[tuple[str, str]] = []
    for group in groups.values():
        for index, left in enumerate(group):
            left_terminals = _program_terminals(left)
            for right in group[index + 1:]:
                right_terminals = _program_terminals(right)
                differences = sum(
                    a != b
                    for a, b in zip(left_terminals, right_terminals, strict=True)
                )
                if differences == 1:
                    edges.append((left.program_id, right.program_id))
    digest = stable_sha256(tuple(sorted(tuple(sorted(edge)) for edge in edges)))
    return Neighborhood(f"policy-single-terminal@{digest}", tuple(edges))


def execute_policy(
    program: Program,
    *,
    mechanism: StrategicMechanism,
    initial_state: StrategicState,
    actions: Mapping[str, StrategicAction],
    conditions: Mapping[str, PolicyCondition],
    max_action_steps: int,
) -> tuple[StrategicState, tuple[str, ...], tuple[str, ...]]:
    """Execute one program with conditions evaluated at their arrival state."""
    if max_action_steps < 1:
        raise ValueError("max_action_steps must be positive")
    action_ids: list[str] = []
    states = [initial_state.state_sha256]

    def run(node: Program, state: StrategicState) -> StrategicState:
        if node.terminal_id is not None:
            if node.terminal_id.startswith("when::"):
                raise TypeError("a condition terminal cannot execute as a policy")
            action_id = node.terminal_id.removeprefix("act::")
            if action_id not in actions:
                raise ValueError(f"policy references unknown action: {action_id}")
            if len(action_ids) >= max_action_steps:
                raise ValueError("policy exceeds the action-step bound")
            result = predict_transition(mechanism, state, action_id)
            action_ids.append(action_id)
            states.append(result.state_sha256)
            return result
        if node.operator_id == "then":
            return run(node.children[1], run(node.children[0], state))
        if node.operator_id == "branch":
            condition_terminal = node.children[0].terminal_id or ""
            condition_id = condition_terminal.removeprefix("when::")
            condition = conditions.get(condition_id)
            if condition is None:
                raise ValueError(f"policy references unknown condition: {condition_id}")
            selected = node.children[1] if condition.matches(state) else node.children[2]
            return run(selected, state)
        raise ValueError(f"unsupported policy operator: {node.operator_id}")

    final = run(program, initial_state)
    return final, tuple(action_ids), tuple(states)


def synthesize_policies(
    *,
    decision_id: str,
    evidence_epoch: str,
    grammar: OperatorGrammar,
    max_depth: int,
    max_programs: int,
    max_action_steps: int,
    initial_state: StrategicState,
    evaluation_states: Iterable[StrategicState] = (),
    actions: Iterable[StrategicAction],
    conditions: Iterable[PolicyCondition],
    mechanisms: Iterable[StrategicMechanism],
    objectives: Iterable[PolicyObjective],
    representation_audit: RepresentationAudit,
) -> PolicySynthesis:
    """Enumerate policies and compile their robust frontier over all models."""
    action_by_id = {row.action_id: row for row in actions}
    condition_by_id = {row.condition_id: row for row in conditions}
    models = tuple(sorted(mechanisms, key=lambda row: row.mechanism_id))
    objective_rows = tuple(objectives)
    if not models:
        raise ValueError("policy synthesis requires a surviving mechanism")
    if not objective_rows:
        raise ValueError("policy synthesis requires objectives")
    state_rows = tuple(evaluation_states) or (initial_state,)
    state_by_id = {row.state_sha256: row for row in (*state_rows, initial_state)}
    state_rows = tuple(sorted(state_by_id.values(), key=lambda row: row.state_sha256))
    if any(row.decision_id != initial_state.decision_id or row.paths != initial_state.paths for row in state_rows):
        raise ValueError("policy evaluation states must share decision identity and state paths")
    for path in (
        *(condition.path for condition in condition_by_id.values()),
        *(objective.path for objective in objective_rows),
    ):
        initial_state.value(path)
    enumeration = enumerate_typed_programs(
        grammar,
        max_depth=max_depth,
        max_programs=max_programs,
    )
    policies = enumeration.programs_of_type("Policy")
    neighborhood = build_policy_neighborhood(policies)
    rollouts: list[PolicyRollout] = []
    evaluations: list[CandidateEvaluation] = []
    for program in policies:
        program_rollouts: list[PolicyRollout] = []
        for evaluation_state in state_rows:
            for model in models:
                terminal, action_ids, states = execute_policy(
                    program,
                    mechanism=model,
                    initial_state=evaluation_state,
                    actions=action_by_id,
                    conditions=condition_by_id,
                    max_action_steps=max_action_steps,
                )
                program_rollouts.append(PolicyRollout(
                    program_id=program.program_id,
                    mechanism_id=model.mechanism_id,
                    initial_state_sha256=evaluation_state.state_sha256,
                    terminal_state=terminal,
                    action_ids=action_ids,
                    state_sha256s=states,
                    objective_values=tuple(
                        objective.score(terminal) for objective in objective_rows
                    ),
                ))
        rollouts.extend(program_rollouts)
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id,
            objective_values=tuple(
                min(row.objective_values[index] for row in program_rollouts)
                for index in range(len(objective_rows))
            ),
            behavior_signature=tuple(
                f"{row.initial_state_sha256}|{row.mechanism_id}|{','.join(row.action_ids)}|"
                f"{','.join(row.state_sha256s)}"
                for row in program_rollouts
            ),
            evidence_refs=tuple(sorted({
                ref
                for model in models
                for ref in model.evidence_refs
            })),
        ))
    scope = FrontierScope(
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type="Policy",
        max_depth=max_depth,
        max_programs=max_programs,
        evaluation_model_id=(
            "condition-partition-mechanism-committee@" + stable_sha256({
                "mechanisms": [model.mechanism_sha256 for model in models],
                "evaluation_states": [row.state_sha256 for row in state_rows],
            })
        ),
        landscape_mode="endogenous_transition",
        evidence_epoch=evidence_epoch,
        objective_names=tuple(
            f"robust::{objective.objective_id}" for objective in objective_rows
        ),
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope,
        enumeration=enumeration,
        evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=representation_audit,
    )
    payload = {
        "decision_id": decision_id,
        "scope_id": scope.scope_id,
        "certificate_sha256": certificate.certificate_sha256,
        "mechanisms": [model.mechanism_sha256 for model in models],
        "evaluation_states": [row.state_sha256 for row in state_rows],
    }
    return PolicySynthesis(
        grammar=grammar,
        enumeration=enumeration,
        neighborhood=neighborhood,
        objectives=objective_rows,
        rollouts=tuple(rollouts),
        evaluations=tuple(evaluations),
        certificate=certificate,
        synthesis_sha256=stable_sha256(payload),
    )


__all__ = [
    "PolicyCondition",
    "PolicyObjective",
    "PolicyRollout",
    "PolicySynthesis",
    "build_policy_grammar",
    "build_policy_neighborhood",
    "execute_policy",
    "synthesize_policies",
]
