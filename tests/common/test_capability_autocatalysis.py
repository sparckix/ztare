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


def _species(authority: CapabilityAuthority):
    return (
        CapabilitySpecies(authority, "base_inference", "food", ("h95",)),
        CapabilitySpecies(authority, "external_settlement", "food", ("h95",)),
        CapabilitySpecies(authority, "J", "capability", ("h99",)),
        CapabilitySpecies(authority, "D", "capability", ("h100",)),
        CapabilitySpecies(authority, "E", "error", ("h96",)),
    )


def _reactions(
    authority: CapabilityAuthority,
    *,
    reproduction_cost: int = 80,
    reproduction_products: tuple[tuple[str, int], ...] = (("J", 3),),
):
    return (
        CatalyticCapabilityReaction(
            authority=authority,
            reaction_id="bootstrap_judgment",
            reactants=(("base_inference", 1), ("external_settlement", 1)),
            products=(("J", 1),),
            catalyst_species_ids=("base_inference",),
            primitive_cost=0,
            bootstrap=True,
            evidence_refs=("h95-live-causal-transport",),
        ),
        CatalyticCapabilityReaction(
            authority=authority,
            reaction_id="invert_measurement_wall",
            reactants=(("J", 1),),
            products=(("J", 1), ("D", 1)),
            catalyst_species_ids=("J",),
            primitive_cost=0,
            bootstrap=False,
            evidence_refs=("h100-sparse-settlement",),
        ),
        CatalyticCapabilityReaction(
            authority=authority,
            reaction_id="reproduce_judgment",
            reactants=(("J", 2), ("external_settlement", 1)),
            products=reproduction_products,
            catalyst_species_ids=("D",),
            primitive_cost=reproduction_cost,
            bootstrap=False,
            evidence_refs=("h99-lineage", "h100-cost"),
        ),
    )


def _compile(*, cost: int = 80, products=(("J", 3),)):
    authority = _authority()
    return compile_capability_autocatalysis(
        _species(authority),
        _reactions(
            authority,
            reproduction_cost=cost,
            reproduction_products=products,
        ),
        primitive_budget=100,
    )


def test_sparse_cost_changes_same_topology_to_productive_core() -> None:
    sparse = _compile(cost=80)
    factorial = _compile(cost=160)

    assert sparse.status == "productive_autocatalytic_core"
    assert sparse.maximal_raf_reaction_ids == factorial.maximal_raf_reaction_ids
    assert sparse.growth_flux is not None
    assert sparse.growth_flux.total_primitive_cost == Fraction(80)
    assert dict(sparse.growth_flux.reaction_fluxes) == {
        "bootstrap_judgment": 1,
        "invert_measurement_wall": 1,
        "reproduce_judgment": 1,
    }
    assert dict(sparse.growth_flux.internal_net_production)["J"] == 1
    assert dict(sparse.growth_flux.internal_net_production)["D"] == 1
    assert dict(sparse.growth_flux.net_production)["E"] == 0
    assert factorial.status == "nonproductive_or_resource_blocked"
    assert factorial.growth_flux is None


def test_cross_authority_species_and_reactions_are_rejected() -> None:
    authority = _authority("a")
    other = _authority("b")

    crossed_species = list(_species(authority))
    crossed_species[-1] = replace(crossed_species[-1], authority=other)
    with pytest.raises(ValueError, match="species crossed authority"):
        compile_capability_autocatalysis(
            crossed_species,
            _reactions(authority),
            primitive_budget=100,
        )

    crossed_reactions = list(_reactions(authority))
    crossed_reactions[-1] = replace(crossed_reactions[-1], authority=other)
    with pytest.raises(ValueError, match="reaction crossed authority"):
        compile_capability_autocatalysis(
            _species(authority),
            crossed_reactions,
            primitive_budget=100,
        )


def test_cycle_without_food_generated_reactants_is_not_a_raf() -> None:
    authority = _authority()
    species = (
        CapabilitySpecies(authority, "food", "food", ("fixture",)),
        CapabilitySpecies(authority, "J", "capability", ("fixture",)),
        CapabilitySpecies(authority, "D", "capability", ("fixture",)),
    )
    reactions = (
        CatalyticCapabilityReaction(
            authority, "j_to_d", (("J", 1),), (("D", 2),), ("D",),
            Fraction(0), False, ("fixture",),
        ),
        CatalyticCapabilityReaction(
            authority, "d_to_j", (("D", 1),), (("J", 2),), ("J",),
            Fraction(0), False, ("fixture",),
        ),
    )

    receipt = compile_capability_autocatalysis(
        species, reactions, primitive_budget=100
    )

    assert receipt.status == "no_reflexively_autocatalytic_food_generated_set"
    assert receipt.maximal_raf_reaction_ids == ()


def test_uncatalyzed_productive_route_is_excluded() -> None:
    authority = _authority()
    species = (
        CapabilitySpecies(authority, "food", "food", ("fixture",)),
        CapabilitySpecies(authority, "J", "capability", ("fixture",)),
        CapabilitySpecies(authority, "absent_catalyst", "error", ("fixture",)),
    )
    reaction = CatalyticCapabilityReaction(
        authority,
        "apparently_productive",
        (("food", 1),),
        (("J", 2),),
        ("absent_catalyst",),
        Fraction(0),
        False,
        ("fixture",),
    )

    receipt = compile_capability_autocatalysis(
        species, (reaction,), primitive_budget=100
    )

    assert receipt.status == "no_reflexively_autocatalytic_food_generated_set"


def test_bootstrap_only_raf_is_not_internal_capability_growth() -> None:
    authority = _authority()
    species = (
        CapabilitySpecies(authority, "food", "food", ("fixture",)),
        CapabilitySpecies(authority, "J", "capability", ("fixture",)),
    )
    reaction = CatalyticCapabilityReaction(
        authority,
        "bootstrap_only",
        (("food", 1),),
        (("J", 1),),
        ("food",),
        Fraction(0),
        True,
        ("fixture",),
    )

    receipt = compile_capability_autocatalysis(
        species, (reaction,), primitive_budget=100
    )

    assert receipt.maximal_raf_reaction_ids == ("bootstrap_only",)
    assert receipt.status == "nonproductive_or_resource_blocked"
    assert receipt.growth_flux is None


def test_error_amplification_blocks_otherwise_productive_flux() -> None:
    receipt = _compile(products=(("J", 3), ("E", 1)))

    assert receipt.maximal_raf_reaction_ids
    assert receipt.status == "nonproductive_or_resource_blocked"
    assert receipt.growth_flux is None


def test_unknown_species_and_repeated_identities_are_rejected() -> None:
    authority = _authority()
    reaction = replace(
        _reactions(authority)[0],
        catalyst_species_ids=("unknown",),
    )
    with pytest.raises(ValueError, match="unknown species"):
        compile_capability_autocatalysis(
            _species(authority), (reaction,), primitive_budget=100
        )

    species = _species(authority)
    with pytest.raises(ValueError, match="repeat an identity"):
        compile_capability_autocatalysis(
            species + (species[-1],),
            _reactions(authority),
            primitive_budget=100,
        )


def test_receipt_cannot_claim_takeoff_from_synthetic_reactions() -> None:
    receipt = _compile()

    assert receipt.to_receipt()["takeoff_supported"] is False
    assert receipt.to_receipt()["live_reaction_evidence_required"] is True


@pytest.mark.parametrize("value", [True, 0, 1.5])
def test_flux_bound_must_be_a_positive_integer(value) -> None:
    authority = _authority()
    with pytest.raises(ValueError, match="must be positive"):
        compile_capability_autocatalysis(
            _species(authority),
            _reactions(authority),
            primitive_budget=100,
            max_flux_per_reaction=value,
        )
