"""LeanMill campaign binding for the shared finite-protocol adapter."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.common.finite_protocol_theory_adapter import (
    FiniteProtocolTheoryAdapter,
    ProtocolObservation,
)
from ztare.leanmill.evidence_theory_context import (
    EvidenceHypothesisProfile,
    EvidenceObjectRecord,
    EvidenceTheoryContext,
)
from ztare.leanmill.theory_ir import TheorySignature


ADAPTER_ID = "finite_deterministic_protocol.v1"


def _adapter_and_state(config: Mapping[str, Any]):
    states = tuple(str(row) for row in config.get("states") or ())
    actions = tuple(str(row) for row in config.get("actions") or ())
    adapter = FiniteProtocolTheoryAdapter(states=states, actions=actions)
    observations = tuple(
        ProtocolObservation(
            observation_id=str(row["observation_id"]),
            state=str(row["state"]),
            action=str(row["action"]),
            next_state=str(row["next_state"]),
        )
        for row in config.get("observations") or ()
    )
    return adapter, adapter.abstract(observations)


def preflight_blueprint(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    del formula_grammar
    del strata
    adapter, state = _adapter_and_state(adapter_config)
    if adapter.signature(state).content_hash != signature.content_hash:
        raise ValueError("finite protocol signature differs from the executable adapter")
    if not state.complete_input_coverage or not state.complete_program_language:
        raise ValueError("exact protocol campaign requires complete declared observations and program language")
    return {
        "formula_count": len(state.programs),
        "labeled_model_count": len(state.observations),
        "truth_cell_count": len(state.programs) * len(state.observations),
        "complete_census_available": True,
        "context_kind": "evidence_incidence",
    }


def build_evidence_context(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> EvidenceTheoryContext:
    del strata
    adapter, state = _adapter_and_state(adapter_config)
    if adapter.signature(state).content_hash != signature.content_hash:
        raise ValueError("finite protocol signature differs from the executable adapter")
    incidence = adapter.build_context(state)
    programs = {row.program_id: row for row in state.programs}
    observations = {row.observation_id: row for row in state.observations}
    profiles = tuple(
        EvidenceHypothesisProfile(
            formula_id=profile.attribute_id,
            truth_bits=profile.truth_bits,
            anonymous_shape={
                "kind": "total_deterministic_transition_program",
                "input_count": len(state.states) * len(state.actions),
                "state_count": len(state.states),
                "action_count": len(state.actions),
            },
            payload={"rows": [list(row) for row in programs[profile.attribute_id].rows]},
        )
        for profile in incidence.profiles
    )
    objects = tuple(
        EvidenceObjectRecord(
            model_id=object_id,
            stratum_id="declared_transition_observation",
            payload={
                "state": observations[object_id].state,
                "action": observations[object_id].action,
                "next_state": observations[object_id].next_state,
            },
        )
        for object_id in incidence.object_ids
    )
    return EvidenceTheoryContext(
        signature=signature,
        adapter_id=ADAPTER_ID,
        incidence=incidence,
        formula_profiles=profiles,
        object_records=objects,
        completeness_receipt_digest=incidence.completeness_ref,
    )


__all__ = ["ADAPTER_ID", "build_evidence_context", "preflight_blueprint"]
