from __future__ import annotations

from ztare.common.abstraction_functor import AbstractionFunctor
from ztare.common.finite_protocol_theory_adapter import (
    FiniteProtocolTheoryAdapter,
    ProtocolObservation,
)
from ztare.common.theory_substrate_adapter import TheorySubstrateAdapter


def test_complete_protocol_context_is_exact_and_recovers_program():
    adapter = FiniteProtocolTheoryAdapter(states=("s0", "s1"), actions=("step",))
    assert isinstance(adapter, AbstractionFunctor)
    assert isinstance(adapter, TheorySubstrateAdapter)
    state = adapter.abstract(
        (
            ProtocolObservation("obs-0", "s0", "step", "s1"),
            ProtocolObservation("obs-1", "s1", "step", "s0"),
        )
    )
    context = adapter.build_context(state)
    assert context.exact is True
    assert len(context.attribute_ids) == 4
    survivors = context.extent_object_ids(())
    assert survivors == ("obs-0", "obs-1")
    fully_consistent = [
        program_id for program_id in context.attribute_ids
        if context.extent_bits((program_id,)) == context.base_mask
    ]
    assert len(fully_consistent) == 1


def test_partial_observation_panel_cannot_claim_exact_closure():
    adapter = FiniteProtocolTheoryAdapter(states=("s0", "s1"), actions=("step",))
    state = adapter.abstract((ProtocolObservation("obs-0", "s0", "step", "s1"),))
    context = adapter.build_context(state)
    assert context.exact is False
    try:
        context.closure_ids(())
    except ValueError as exc:
        assert "exact closure" in str(exc)
    else:
        raise AssertionError("sampled panel emitted exact closure")
