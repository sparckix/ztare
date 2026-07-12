"""Evidence-induced theory adapter for finite deterministic protocols.

Objects are a declared transition input universe; hypotheses are executable
transition programs. This is also the direct ARC-style instantiation of the
shared incidence interface: observation × program satisfaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Mapping, Sequence

from ztare.common.finite_incidence_context import FiniteIncidenceContext, build_context_from_adapter
from ztare.leanmill.theory_ir import OperationSymbol, SortDecl, TheorySignature, content_hash


@dataclass(frozen=True)
class ProtocolObservation:
    observation_id: str
    state: str
    action: str
    next_state: str


@dataclass(frozen=True)
class TransitionProgram:
    program_id: str
    rows: tuple[tuple[str, str, str], ...]

    @classmethod
    def from_rows(cls, rows: Sequence[tuple[str, str, str]]) -> "TransitionProgram":
        ordered = tuple(sorted(rows))
        return cls(
            program_id="program:" + content_hash({"transition_rows": [list(row) for row in ordered]}),
            rows=ordered,
        )

    @property
    def transition_map(self) -> dict[tuple[str, str], str]:
        return {(state, action): target for state, action, target in self.rows}


@dataclass(frozen=True)
class ProtocolAbstractState:
    states: tuple[str, ...]
    actions: tuple[str, ...]
    observations: tuple[ProtocolObservation, ...]
    programs: tuple[TransitionProgram, ...]
    complete_input_coverage: bool
    complete_program_language: bool


class FiniteProtocolTheoryAdapter:
    adapter_id = "finite_deterministic_protocol.v1"

    def __init__(self, *, states: Sequence[str], actions: Sequence[str]) -> None:
        self.states = tuple(sorted(set(map(str, states))))
        self.actions = tuple(sorted(set(map(str, actions))))
        if not self.states or not self.actions:
            raise ValueError("protocol adapter needs finite states and actions")

    def enumerate_programs(self) -> tuple[TransitionProgram, ...]:
        inputs = tuple(product(self.states, self.actions))
        return tuple(
            TransitionProgram.from_rows(
                tuple((state, action, target) for (state, action), target in zip(inputs, outputs, strict=True))
            )
            for outputs in product(self.states, repeat=len(inputs))
        )

    def abstract(self, raw_evidence: Any) -> ProtocolAbstractState:
        observations = tuple(raw_evidence)
        if not all(isinstance(row, ProtocolObservation) for row in observations):
            raise ValueError("raw protocol evidence must contain ProtocolObservation rows")
        keys = [(row.state, row.action) for row in observations]
        if len(set(keys)) != len(keys):
            raise ValueError("conflicting or duplicate protocol input observations")
        expected = set(product(self.states, self.actions))
        if not set(keys) <= expected:
            raise ValueError("observation lies outside the declared input universe")
        programs = self.enumerate_programs()
        return ProtocolAbstractState(
            states=self.states,
            actions=self.actions,
            observations=tuple(sorted(observations, key=lambda row: row.observation_id)),
            programs=programs,
            complete_input_coverage=set(keys) == expected,
            complete_program_language=True,
        )

    def signature(self, state: ProtocolAbstractState) -> TheorySignature:
        return TheorySignature(
            name="AnonymousFiniteProtocol",
            sorts=(SortDecl("State"),),
            operations=tuple(
                OperationSymbol(action, ("State",), "State") for action in state.actions
            ),
        )

    def base_axioms(self, _state: ProtocolAbstractState) -> tuple[Any, ...]:
        return ()

    @property
    def object_ids(self) -> tuple[str, ...]:
        if not hasattr(self, "_active"):
            raise RuntimeError("call build_context with an abstract state first")
        return tuple(row.observation_id for row in self._active.observations)

    @property
    def attribute_ids(self) -> tuple[str, ...]:
        if not hasattr(self, "_active"):
            raise RuntimeError("call build_context with an abstract state first")
        return tuple(row.program_id for row in self._active.programs)

    def satisfies(self, object_id: str, attribute_id: str) -> bool:
        observation = next(row for row in self._active.observations if row.observation_id == object_id)
        program = next(row for row in self._active.programs if row.program_id == attribute_id)
        return program.transition_map[(observation.state, observation.action)] == observation.next_state

    def build_context(self, state: ProtocolAbstractState) -> FiniteIncidenceContext:
        self._active = state
        exact = state.complete_input_coverage and state.complete_program_language
        completeness = ""
        if exact:
            completeness = "protocol-census:" + content_hash(
                {
                    "states": list(state.states),
                    "actions": list(state.actions),
                    "observation_ids": list(self.object_ids),
                    "program_ids": list(self.attribute_ids),
                }
            )
        return build_context_from_adapter(
            self,
            exact=exact,
            completeness_ref=completeness,
        )

    def lower(self, theory: TransitionProgram, raw_state: tuple[str, str]) -> str:
        return theory.transition_map[tuple(raw_state)]

    def check_raw(self, prediction: Any, observation: Any) -> dict[str, Any]:
        if not isinstance(observation, ProtocolObservation):
            raise ValueError("raw check requires a ProtocolObservation")
        ok = str(prediction) == observation.next_state
        core = {
            "schema": "ztare.finite_protocol_raw_check.v1",
            "observation_id": observation.observation_id,
            "prediction": str(prediction),
            "observed": observation.next_state,
            "ok": ok,
        }
        return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "FiniteProtocolTheoryAdapter", "ProtocolAbstractState", "ProtocolObservation",
    "TransitionProgram",
]
