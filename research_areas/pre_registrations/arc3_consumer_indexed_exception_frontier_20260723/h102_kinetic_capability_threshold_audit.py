#!/usr/bin/env python3
"""Run H102's exact state-dependent capability-kinetics discriminator."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

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
from ztare.common.epistemic_autocatalysis import stable_sha256
from ztare.common.wake_sleep_credit_router import MemoryScope


BASE = Path(__file__).resolve().parent
H101 = BASE / "h101_capability_autocatalytic_closure_result.json"
RUNTIME = (
    BASE
    / "h97_causal_response_derivative/live_attempt_02_runtime_receipt.json"
)
OUTPUT = BASE / "h102_kinetic_capability_threshold_result.json"


def source_authority(h101: dict) -> CapabilityAuthority:
    row = h101["sparse_core"]["authority"]
    return CapabilityAuthority(
        scope=MemoryScope(**row["scope"]),
        capability_catalog_sha256=row["capability_catalog_sha256"],
        evidence_epoch_sha256=row["evidence_epoch_sha256"],
        primitive_cost_unit=row["primitive_cost_unit"],
    )


def topology_from_h101(h101: dict, *, reproduction_cost: int):
    owner = source_authority(h101)
    species = tuple(
        CapabilitySpecies(
            owner,
            row["species_id"],
            row["role"],
            tuple(row["evidence_refs"]),
        )
        for row in h101["sparse_core"]["species"]
    )
    reactions = []
    for row in h101["sparse_core"]["reactions"]:
        cost = (
            reproduction_cost
            if row["reaction_id"] == "reproduce_judgment"
            else Fraction(row["primitive_cost"])
        )
        reactions.append(CatalyticCapabilityReaction(
            authority=owner,
            reaction_id=row["reaction_id"],
            reactants=tuple(
                (item["species_id"], item["count"])
                for item in row["reactants"]
            ),
            products=tuple(
                (item["species_id"], item["count"])
                for item in row["products"]
            ),
            catalyst_species_ids=tuple(row["catalyst_species_ids"]),
            primitive_cost=cost,
            bootstrap=bool(row["bootstrap"]),
            evidence_refs=tuple(row["evidence_refs"]),
        ))
    return compile_capability_autocatalysis(
        species,
        tuple(reactions),
        primitive_budget=200,
    )


def kinetic_model(topology) -> CapabilityKineticModel:
    constants = {
        "bootstrap_judgment": Fraction(0),
        "invert_measurement_wall": Fraction(2),
        "reproduce_judgment": Fraction(1, 4),
    }
    return CapabilityKineticModel(
        authority=topology.authority,
        autocatalysis_receipt_sha256=topology.sha256,
        reaction_rate_laws=tuple(
            CapabilityReactionRateLaw(
                topology.authority,
                reaction.reaction_id,
                reaction.sha256,
                constants[reaction.reaction_id],
                (f"h102-synthetic-rate:{reaction.reaction_id}",),
            )
            for reaction in topology.reactions
        ),
        depreciation_rates=(
            ("J_lineage_bound_judgment", Fraction(1)),
            ("D_sparse_settlement_design", Fraction(1)),
            ("E_false_edge_propagation", Fraction(1)),
        ),
        primitive_budget_rate=300,
        evidence_refs=("h102-preregistered-kinetic-fixture",),
    )


def stock_state(
    model: CapabilityKineticModel,
    scale: Fraction,
    *,
    state_id: str,
    base_amount: Fraction = Fraction(1),
    design_amount: Fraction | None = None,
) -> CapabilityStockState:
    design = (
        Fraction(3, 2) * scale
        if design_amount is None
        else design_amount
    )
    return CapabilityStockState(
        authority=model.authority,
        kinetic_model_sha256=model.sha256,
        state_id=state_id,
        scale_parameter=scale,
        species_amounts=(
            ("base_inference", base_amount),
            ("external_settlement", Fraction(1)),
            ("J_lineage_bound_judgment", scale),
            ("D_sparse_settlement_design", design),
            ("E_false_edge_propagation", Fraction(0)),
        ),
        evidence_refs=(f"h102-preregistered-state:{state_id}",),
    )


def topology_without_cost_sha256(topology) -> str:
    return stable_sha256({
        "kind": "h102_reaction_topology_without_cost",
        "reactions": [
            {
                "reaction_id": row.reaction_id,
                "reactants": row.reactants,
                "products": row.products,
                "catalysts": row.catalyst_species_ids,
                "bootstrap": row.bootstrap,
            }
            for row in topology.reactions
        ],
    })


def caught(label, fn) -> dict:
    try:
        fn()
    except (KeyError, TypeError, ValueError) as exc:
        return {"label": label, "rejected": True, "reason": str(exc)}
    return {"label": label, "rejected": False, "reason": "accepted"}


def error_unstable_fixture(owner: CapabilityAuthority):
    species = (
        CapabilitySpecies(owner, "x_food", "food", ("negative",)),
        CapabilitySpecies(owner, "x_j", "capability", ("negative",)),
        CapabilitySpecies(owner, "x_d", "capability", ("negative",)),
        CapabilitySpecies(owner, "x_e", "error", ("negative",)),
    )
    reactions = (
        CatalyticCapabilityReaction(
            owner, "x_bootstrap", (("x_food", 1),), (("x_j", 1),),
            ("x_food",), Fraction(0), True, ("negative",),
        ),
        CatalyticCapabilityReaction(
            owner, "x_design", (("x_j", 1),),
            (("x_j", 1), ("x_d", 1)), ("x_j",), Fraction(0), False,
            ("negative",),
        ),
        CatalyticCapabilityReaction(
            owner, "x_reproduce", (("x_j", 2), ("x_food", 1)),
            (("x_j", 3), ("x_e", 1)), ("x_d",), Fraction(0), False,
            ("negative",),
        ),
        CatalyticCapabilityReaction(
            owner, "x_cleanup", (("x_e", 1), ("x_j", 1)),
            (("x_j", 1),), ("x_d",), Fraction(0), False,
            ("negative",),
        ),
    )
    topology = compile_capability_autocatalysis(
        species, reactions, primitive_budget=200
    )
    constants = {
        "x_bootstrap": 0,
        "x_design": 2,
        "x_reproduce": "1/4",
        "x_cleanup": 1,
    }
    model = CapabilityKineticModel(
        owner,
        topology.sha256,
        tuple(
            CapabilityReactionRateLaw(
                owner,
                reaction.reaction_id,
                reaction.sha256,
                constants[reaction.reaction_id],
                ("negative",),
            )
            for reaction in topology.reactions
        ),
        (("x_j", 1), ("x_d", 1), ("x_e", 1)),
        300,
        ("negative",),
    )
    state = CapabilityStockState(
        owner,
        model.sha256,
        "error-unstable",
        Fraction(7, 4),
        (
            ("x_food", 1),
            ("x_j", Fraction(7, 4)),
            ("x_d", Fraction(21, 8)),
            ("x_e", 0),
        ),
        ("negative",),
    )
    return compile_capability_kinetic_drift(topology, model, state)


def main() -> int:
    h101 = json.loads(H101.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    if h101["verdict"] != "supported":
        raise RuntimeError("H101 prerequisite is not supported")
    if runtime["evidence_effect"] != "none" or runtime["environment_contact"]:
        raise RuntimeError("H97 runtime boundary changed")

    sparse_topology = topology_from_h101(h101, reproduction_cost=80)
    factorial_topology = topology_from_h101(h101, reproduction_cost=160)
    sparse_model = kinetic_model(sparse_topology)
    factorial_model = kinetic_model(factorial_topology)
    lower = compile_capability_kinetic_drift(
        sparse_topology,
        sparse_model,
        stock_state(
            sparse_model, Fraction(3, 2), state_id="lower-3-over-2"
        ),
    )
    upper = compile_capability_kinetic_drift(
        sparse_topology,
        sparse_model,
        stock_state(
            sparse_model, Fraction(7, 4), state_id="upper-7-over-4"
        ),
    )
    bracket = compile_capability_critical_bracket(
        sparse_topology, lower, upper
    )
    factorial_upper = compile_capability_kinetic_drift(
        factorial_topology,
        factorial_model,
        stock_state(
            factorial_model,
            Fraction(7, 4),
            state_id="factorial-upper-7-over-4",
        ),
    )
    zero_catalyst = compile_capability_kinetic_drift(
        sparse_topology,
        sparse_model,
        stock_state(
            sparse_model,
            Fraction(7, 4),
            state_id="zero-design-catalyst",
            design_amount=Fraction(0),
        ),
    )
    error_unstable = error_unstable_fixture(sparse_topology.authority)

    laws = list(sparse_model.reaction_rate_laws)
    laws[-1] = replace(laws[-1], reaction_sha256="wrong-reaction")
    wrong_reaction_model = replace(
        sparse_model,
        reaction_rate_laws=tuple(laws),
    )
    missing_law_model = replace(
        sparse_model,
        reaction_rate_laws=sparse_model.reaction_rate_laws[:-1],
    )
    changed_food_upper = compile_capability_kinetic_drift(
        sparse_topology,
        sparse_model,
        stock_state(
            sparse_model,
            Fraction(7, 4),
            state_id="changed-food-upper",
            base_amount=Fraction(2),
        ),
    )
    other_owner = replace(
        sparse_topology.authority,
        evidence_epoch_sha256="crossed-evidence-epoch",
    )
    crossed_state = replace(
        stock_state(
            sparse_model,
            Fraction(7, 4),
            state_id="crossed-authority",
        ),
        authority=other_owner,
    )
    negatives = (
        caught(
            "wrong_reaction_sha",
            lambda: compile_capability_kinetic_drift(
                sparse_topology,
                wrong_reaction_model,
                stock_state(
                    wrong_reaction_model,
                    Fraction(7, 4),
                    state_id="wrong-reaction",
                ),
            ),
        ),
        caught(
            "missing_reaction_law",
            lambda: compile_capability_kinetic_drift(
                sparse_topology,
                missing_law_model,
                stock_state(
                    missing_law_model,
                    Fraction(7, 4),
                    state_id="missing-law",
                ),
            ),
        ),
        caught(
            "float_rate_constant",
            lambda: replace(
                sparse_model.reaction_rate_laws[0],
                rate_constant=0.5,
            ),
        ),
        caught(
            "cross_authority_state",
            lambda: compile_capability_kinetic_drift(
                sparse_topology, sparse_model, crossed_state
            ),
        ),
        caught(
            "posthoc_food_bracket",
            lambda: compile_capability_critical_bracket(
                sparse_topology, lower, changed_food_upper
            ),
        ),
    )

    lower_rates = dict(lower.reaction_rates)
    lower_drift = dict(lower.internal_drift)
    upper_rates = dict(upper.reaction_rates)
    upper_drift = dict(upper.internal_drift)
    error_drift = dict(error_unstable.internal_drift)
    lower_surface = 3 * Fraction(3, 2) ** 2
    upper_surface = 3 * Fraction(7, 4) ** 2
    passed = bool(
        sparse_topology.status == "productive_autocatalytic_core"
        and factorial_topology.status == "productive_autocatalytic_core"
        and topology_without_cost_sha256(sparse_topology)
        == topology_without_cost_sha256(factorial_topology)
        and lower_rates["reproduce_judgment"] == Fraction(81, 64)
        and lower_drift["J_lineage_bound_judgment"]
        == Fraction(-15, 64)
        and lower_drift["D_sparse_settlement_design"] == Fraction(9, 4)
        and lower.primitive_cost_rate == Fraction(405, 4)
        and lower.status == "kinetically_subcritical"
        and upper_rates["reproduce_judgment"] == Fraction(1029, 512)
        and upper_drift["J_lineage_bound_judgment"]
        == Fraction(133, 512)
        and upper_drift["D_sparse_settlement_design"] == Fraction(7, 2)
        and upper.primitive_cost_rate == Fraction(5145, 32)
        and upper.status == "kinetically_supercritical_candidate"
        and bracket.status == "critical_stock_bracket"
        and lower_surface < 8 < upper_surface
        and factorial_upper.reaction_rates == upper.reaction_rates
        and factorial_upper.internal_drift == upper.internal_drift
        and factorial_upper.primitive_cost_rate == Fraction(5145, 16)
        and factorial_upper.status == "resource_rate_blocked"
        and dict(zero_catalyst.reaction_rates)["reproduce_judgment"] == 0
        and zero_catalyst.status == "kinetically_subcritical"
        and error_drift["x_e"] > 0
        and error_unstable.status == "error_rate_unstable"
        and all(row["rejected"] for row in negatives)
        and not upper.to_receipt()["takeoff_supported"]
    )

    core = {
        "schema": "ztare-h102-kinetic-capability-threshold-audit-v1",
        "kind": "offline_theory_discriminator_result",
        "status": "offline_complete",
        "verdict": "supported" if passed else "rejected",
        "environment_contact": False,
        "controller_contact": False,
        "h97_runtime_boundary": {
            "receipt_ref": str(RUNTIME.relative_to(REPO)),
            "status": runtime["status"],
            "error_code": runtime["error_code"],
            "evidence_effect": runtime["evidence_effect"],
        },
        "h101_source": {
            "result_ref": str(H101.relative_to(REPO)),
            "sha256": h101["sha256"],
            "verdict": h101["verdict"],
            "source_authority_replayed_exactly": (
                source_authority(h101).to_receipt()
                == h101["sparse_core"]["authority"]
            ),
        },
        "same_topology_without_cost_sha256": (
            topology_without_cost_sha256(sparse_topology)
        ),
        "lower_state": lower.to_receipt(),
        "upper_state": upper.to_receipt(),
        "critical_bracket": bracket.to_receipt(),
        "analytic_threshold_bracket": {
            "critical_surface": "3*J^2=8",
            "lower_J": "3/2",
            "lower_surface": f"{lower_surface.numerator}/{lower_surface.denominator}",
            "upper_J": "7/4",
            "upper_surface": f"{upper_surface.numerator}/{upper_surface.denominator}",
            "lower_below": lower_surface < 8,
            "upper_above": upper_surface > 8,
        },
        "factorial_cost_counterfactual": factorial_upper.to_receipt(),
        "negative_dynamic_fixtures": {
            "zero_catalyst": zero_catalyst.to_receipt(),
            "positive_error_drift": error_unstable.to_receipt(),
            "identity_and_exactness": list(negatives),
        },
        "nearest_prior_art": [
            {
                "component": "mass-action autocatalysis and persistence",
                "url": "https://arxiv.org/abs/1309.3957",
            },
            {
                "component": "RAF structure and reaction-rate extensions",
                "url": "https://doi.org/10.1098/rsif.2020.0488",
            },
            {
                "component": "concentration and flux regimes in mass-action autocatalytic networks",
                "url": "https://www.nature.com/articles/s42005-024-01704-8",
            },
            {
                "component": "autocatalytic cores with explicit catalysts",
                "url": "https://arxiv.org/abs/2603.02770",
            },
            {
                "component": "dynamic hysteresis in an autocatalytic network",
                "url": "https://arxiv.org/abs/2607.24163",
            },
        ],
        "claim_boundary": [
            "The same productive RAF is subcritical or supercritical according to exact capability stock and depreciation.",
            "Sparse assay cost permits the upper-state rate while factorial cost blocks the same reaction-rate vector.",
            "The kinetic constants and stock states are preregistered synthetic fixtures rather than measured agent dynamics.",
            "The result corrects the criticality criterion but does not demonstrate endogenous growth, live ARC compounding, or capability takeoff.",
            "Mass-action and Allee-threshold components are established; literature novelty of the compiled join is not established.",
        ],
    }
    result = {**core, "sha256": stable_sha256(core)}
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_ref": str(OUTPUT.relative_to(REPO)),
        "verdict": result["verdict"],
        "lower_status": lower.status,
        "lower_j_drift": str(lower_drift["J_lineage_bound_judgment"]),
        "upper_status": upper.status,
        "upper_j_drift": str(upper_drift["J_lineage_bound_judgment"]),
        "sparse_upper_cost_rate": str(upper.primitive_cost_rate),
        "factorial_upper_status": factorial_upper.status,
        "factorial_upper_cost_rate": str(
            factorial_upper.primitive_cost_rate
        ),
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
