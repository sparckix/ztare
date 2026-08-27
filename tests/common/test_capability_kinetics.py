from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from ztare.common.capability_autocatalysis import (
    CapabilityAuthority,
    CapabilitySpecies,
    CatalyticCapabilityReaction,
    compile_capability_autocatalysis,
)
from ztare.common.capability_kinetics import (
    CapabilityKineticModel,
    CapabilityReactionRateLaw,
    CapabilityStockState,
    compile_capability_critical_bracket,
    compile_capability_kinetic_drift,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


def _authority(suffix: str = "a") -> CapabilityAuthority:
    return CapabilityAuthority(
        scope=MemoryScope(
            task_sha256=f"task-{suffix}",
            controller_sha256=f"controller-{suffix}",
            context_sha256=f"context-{suffix}",
            choice_set_sha256=f"choices-{suffix}",
            action_vocabulary_sha256=f"actions-{suffix}",
        ),
        capability_catalog_sha256=f"catalog-{suffix}",
        evidence_epoch_sha256=f"epoch-{suffix}",
        primitive_cost_unit="charged_environment_action",
    )


def _topology(cost: int = 80, *, owner=None):
    authority = owner or _authority()
    species = (
        CapabilitySpecies(authority, "base", "food", ("h95",)),
        CapabilitySpecies(authority, "settlement", "food", ("h95",)),
        CapabilitySpecies(authority, "J", "capability", ("h99",)),
        CapabilitySpecies(authority, "D", "capability", ("h100",)),
        CapabilitySpecies(authority, "E", "error", ("h96",)),
    )
    reactions = (
        CatalyticCapabilityReaction(
            authority, "bootstrap", (("base", 1), ("settlement", 1)),
            (("J", 1),), ("base",), Fraction(0), True, ("h95",),
        ),
        CatalyticCapabilityReaction(
            authority, "design", (("J", 1),), (("J", 1), ("D", 1)),
            ("J",), Fraction(0), False, ("h100",),
        ),
        CatalyticCapabilityReaction(
            authority, "reproduce", (("J", 2), ("settlement", 1)),
            (("J", 3),), ("D",), Fraction(cost), False, ("h99",),
        ),
    )
    return compile_capability_autocatalysis(
        species,
        reactions,
        primitive_budget=200,
    )


def _model(topology, *, budget=300, owner=None):
    authority = owner or topology.authority
    constants = {
        "bootstrap": Fraction(0),
        "design": Fraction(2),
        "reproduce": Fraction(1, 4),
    }
    return CapabilityKineticModel(
        authority=authority,
        autocatalysis_receipt_sha256=topology.sha256,
        reaction_rate_laws=tuple(
            CapabilityReactionRateLaw(
                authority,
                reaction.reaction_id,
                reaction.sha256,
                constants[reaction.reaction_id],
                (f"synthetic-rate:{reaction.reaction_id}",),
            )
            for reaction in topology.reactions
        ),
        depreciation_rates=(
            ("J", Fraction(1)),
            ("D", Fraction(1)),
            ("E", Fraction(1)),
        ),
        primitive_budget_rate=budget,
        evidence_refs=("h102-kinetic-fixture",),
    )


def _state(model, scale, *, state_id="state", base=1, settlement=1, d=None):
    value = Fraction(scale)
    design = Fraction(3, 2) * value if d is None else Fraction(d)
    return CapabilityStockState(
        authority=model.authority,
        kinetic_model_sha256=model.sha256,
        state_id=state_id,
        scale_parameter=value,
        species_amounts=(
            ("base", Fraction(base)),
            ("settlement", Fraction(settlement)),
            ("J", value),
            ("D", design),
            ("E", Fraction(0)),
        ),
        evidence_refs=(f"h102-state:{state_id}",),
    )


def test_exact_low_high_states_cross_kinetic_threshold() -> None:
    topology = _topology()
    model = _model(topology)
    lower = compile_capability_kinetic_drift(
        topology,
        model,
        _state(model, Fraction(3, 2), state_id="lower"),
    )
    upper = compile_capability_kinetic_drift(
        topology,
        model,
        _state(model, Fraction(7, 4), state_id="upper"),
    )
    bracket = compile_capability_critical_bracket(topology, lower, upper)

    assert topology.status == "productive_autocatalytic_core"
    assert dict(lower.reaction_rates) == {
        "bootstrap": Fraction(0),
        "design": Fraction(9, 2),
        "reproduce": Fraction(81, 64),
    }
    assert dict(lower.internal_drift) == {
        "D": Fraction(9, 4),
        "E": Fraction(0),
        "J": Fraction(-15, 64),
    }
    assert lower.primitive_cost_rate == Fraction(405, 4)
    assert lower.status == "kinetically_subcritical"
    assert dict(upper.reaction_rates) == {
        "bootstrap": Fraction(0),
        "design": Fraction(49, 8),
        "reproduce": Fraction(1029, 512),
    }
    assert dict(upper.internal_drift) == {
        "D": Fraction(7, 2),
        "E": Fraction(0),
        "J": Fraction(133, 512),
    }
    assert upper.primitive_cost_rate == Fraction(5145, 32)
    assert upper.status == "kinetically_supercritical_candidate"
    assert bracket.status == "critical_stock_bracket"
    assert bracket.to_receipt()["takeoff_supported"] is False


def test_factorial_cost_blocks_same_upper_reaction_rates() -> None:
    sparse_topology = _topology(80)
    factorial_topology = _topology(160)
    sparse_model = _model(sparse_topology)
    factorial_model = _model(factorial_topology)
    sparse = compile_capability_kinetic_drift(
        sparse_topology,
        sparse_model,
        _state(sparse_model, Fraction(7, 4), state_id="sparse-upper"),
    )
    factorial = compile_capability_kinetic_drift(
        factorial_topology,
        factorial_model,
        _state(
            factorial_model,
            Fraction(7, 4),
            state_id="factorial-upper",
        ),
    )

    assert sparse_topology.status == factorial_topology.status
    assert sparse.reaction_rates == factorial.reaction_rates
    assert sparse.internal_drift == factorial.internal_drift
    assert sparse.status == "kinetically_supercritical_candidate"
    assert sparse.primitive_cost_rate == Fraction(5145, 32)
    assert factorial.primitive_cost_rate == Fraction(5145, 16)
    assert factorial.status == "resource_rate_blocked"


def test_zero_catalyst_amount_zeroes_reproduction_rate() -> None:
    topology = _topology()
    model = _model(topology)
    receipt = compile_capability_kinetic_drift(
        topology,
        model,
        _state(
            model,
            Fraction(7, 4),
            state_id="no-design-catalyst",
            d=0,
        ),
    )

    assert dict(receipt.reaction_rates)["reproduce"] == 0
    assert dict(receipt.internal_drift)["J"] == Fraction(-7, 4)
    assert receipt.status == "kinetically_subcritical"


def test_rate_law_reaction_identity_is_exact() -> None:
    topology = _topology()
    model = _model(topology)
    laws = list(model.reaction_rate_laws)
    laws[-1] = replace(laws[-1], reaction_sha256="wrong-reaction")
    drifted = replace(model, reaction_rate_laws=tuple(laws))

    with pytest.raises(ValueError, match="crossed reaction identity"):
        compile_capability_kinetic_drift(
            topology,
            drifted,
            _state(drifted, Fraction(7, 4)),
        )


def test_missing_and_extra_reaction_laws_are_rejected() -> None:
    topology = _topology()
    model = _model(topology)
    missing = replace(model, reaction_rate_laws=model.reaction_rate_laws[:-1])
    with pytest.raises(ValueError, match="bind every reaction"):
        compile_capability_kinetic_drift(
            topology, missing, _state(missing, Fraction(7, 4))
        )

    extra_law = CapabilityReactionRateLaw(
        topology.authority,
        "extra",
        "extra-sha",
        Fraction(1),
        ("negative",),
    )
    extra = replace(
        model,
        reaction_rate_laws=model.reaction_rate_laws + (extra_law,),
    )
    with pytest.raises(ValueError, match="bind every reaction"):
        compile_capability_kinetic_drift(
            topology, extra, _state(extra, Fraction(7, 4))
        )


def test_missing_amount_or_depreciation_is_rejected() -> None:
    topology = _topology()
    model = _model(topology)
    incomplete_state = replace(
        _state(model, Fraction(7, 4)),
        species_amounts=_state(model, Fraction(7, 4)).species_amounts[:-1],
    )
    with pytest.raises(ValueError, match="bind every topology species"):
        compile_capability_kinetic_drift(
            topology, model, incomplete_state
        )

    incomplete_model = replace(
        model,
        depreciation_rates=model.depreciation_rates[:-1],
    )
    with pytest.raises(ValueError, match="every capability/error"):
        compile_capability_kinetic_drift(
            topology,
            incomplete_model,
            _state(incomplete_model, Fraction(7, 4)),
        )


@pytest.mark.parametrize("field", ["rate", "budget", "amount", "scale"])
def test_float_kinetic_parameters_are_rejected(field: str) -> None:
    topology = _topology()
    model = _model(topology)
    if field == "rate":
        with pytest.raises(TypeError, match="exact rational"):
            replace(model.reaction_rate_laws[0], rate_constant=0.5)
    elif field == "budget":
        with pytest.raises(TypeError, match="exact rational"):
            replace(model, primitive_budget_rate=300.0)
    elif field == "amount":
        with pytest.raises(TypeError, match="exact rational"):
            CapabilityStockState(
                model.authority,
                model.sha256,
                "float-amount",
                Fraction(1),
                (("base", 1.0),),
                ("negative",),
            )
    else:
        with pytest.raises(TypeError, match="exact rational"):
            replace(_state(model, Fraction(1)), scale_parameter=1.0)


def test_cross_authority_model_and_state_are_rejected() -> None:
    topology = _topology()
    other_authority = _authority("other")
    other_topology = _topology(owner=other_authority)
    crossed_model = _model(other_topology)
    crossed_model = replace(
        crossed_model,
        autocatalysis_receipt_sha256=topology.sha256,
    )
    with pytest.raises(ValueError, match="crossed topology authority"):
        compile_capability_kinetic_drift(
            topology,
            crossed_model,
            _state(crossed_model, Fraction(7, 4)),
        )

    model = _model(topology)
    state = replace(
        _state(model, Fraction(7, 4)),
        authority=other_authority,
    )
    with pytest.raises(ValueError, match="state crossed kinetic authority"):
        compile_capability_kinetic_drift(topology, model, state)


def test_threshold_bracket_rejects_food_or_model_drift() -> None:
    topology = _topology()
    model = _model(topology)
    lower = compile_capability_kinetic_drift(
        topology,
        model,
        _state(model, Fraction(3, 2), state_id="lower"),
    )
    changed_food_upper = compile_capability_kinetic_drift(
        topology,
        model,
        _state(
            model,
            Fraction(7, 4),
            state_id="upper-changed-food",
            base=2,
        ),
    )
    with pytest.raises(ValueError, match="changed food stock"):
        compile_capability_critical_bracket(
            topology, lower, changed_food_upper
        )

    other_model = _model(topology, budget=301)
    other_upper = compile_capability_kinetic_drift(
        topology,
        other_model,
        _state(other_model, Fraction(7, 4), state_id="other-model"),
    )
    with pytest.raises(ValueError, match="crossed kinetic model"):
        compile_capability_critical_bracket(topology, lower, other_upper)


def test_positive_error_drift_blocks_kinetic_criticality() -> None:
    authority = _authority()
    species = (
        CapabilitySpecies(authority, "food", "food", ("fixture",)),
        CapabilitySpecies(authority, "J", "capability", ("fixture",)),
        CapabilitySpecies(authority, "D", "capability", ("fixture",)),
        CapabilitySpecies(authority, "E", "error", ("fixture",)),
    )
    reactions = (
        CatalyticCapabilityReaction(
            authority, "bootstrap", (("food", 1),), (("J", 1),),
            ("food",), Fraction(0), True, ("fixture",),
        ),
        CatalyticCapabilityReaction(
            authority, "design", (("J", 1),), (("J", 1), ("D", 1)),
            ("J",), Fraction(0), False, ("fixture",),
        ),
        CatalyticCapabilityReaction(
            authority, "reproduce", (("J", 2), ("food", 1)),
            (("J", 3), ("E", 1)), ("D",), Fraction(0), False,
            ("fixture",),
        ),
        CatalyticCapabilityReaction(
            authority, "cleanup", (("E", 1), ("J", 1)), (("J", 1),),
            ("D",), Fraction(0), False, ("fixture",),
        ),
    )
    topology = compile_capability_autocatalysis(
        species, reactions, primitive_budget=200
    )
    constants = {
        "bootstrap": 0,
        "design": 2,
        "reproduce": "1/4",
        "cleanup": 1,
    }
    model = CapabilityKineticModel(
        authority,
        topology.sha256,
        tuple(
            CapabilityReactionRateLaw(
                authority,
                reaction.reaction_id,
                reaction.sha256,
                constants[reaction.reaction_id],
                ("fixture",),
            )
            for reaction in topology.reactions
        ),
        (("J", 1), ("D", 1), ("E", 1)),
        300,
        ("fixture",),
    )
    state = CapabilityStockState(
        authority,
        model.sha256,
        "error-unstable",
        Fraction(7, 4),
        (
            ("food", 1),
            ("J", Fraction(7, 4)),
            ("D", Fraction(21, 8)),
            ("E", 0),
        ),
        ("fixture",),
    )
    receipt = compile_capability_kinetic_drift(topology, model, state)

    assert topology.status == "productive_autocatalytic_core"
    assert dict(receipt.internal_drift)["E"] > 0
    assert receipt.status == "error_rate_unstable"


def test_synthetic_kinetic_receipt_cannot_claim_takeoff() -> None:
    topology = _topology()
    model = _model(topology)
    receipt = compile_capability_kinetic_drift(
        topology,
        model,
        _state(model, Fraction(7, 4), state_id="upper"),
    )

    assert receipt.to_receipt()["takeoff_supported"] is False
    assert receipt.to_receipt()["measured_kinetic_parameters_required"] is True
