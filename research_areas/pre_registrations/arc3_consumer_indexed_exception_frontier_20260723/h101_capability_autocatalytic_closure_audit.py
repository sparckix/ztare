#!/usr/bin/env python3
"""Run H101's authority-typed catalytic-closure discriminator."""

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
from ztare.common.epistemic_autocatalysis import stable_sha256
from ztare.common.wake_sleep_credit_router import MemoryScope


BASE = Path(__file__).resolve().parent
H97 = BASE / "h97_causal_response_derivative/manifest.json"
RUNTIME = (
    BASE
    / "h97_causal_response_derivative/live_attempt_01_runtime_receipt.json"
)
H99 = BASE / "h99_lineage_bound_epistemic_branching_result.json"
H100 = BASE / "h100_sparse_orthogonal_settlement_result.json"
OUTPUT = BASE / "h101_capability_autocatalytic_closure_result.json"


def authority(
    h99: dict,
    h100: dict,
    *,
    suffix: str = "a",
) -> CapabilityAuthority:
    manifest = json.loads(H97.read_text(encoding="utf-8"))
    residual = manifest["live_response_derivative"]["residual_contract"]
    scope_payload = dict(residual["scope"])
    if suffix != "a":
        scope_payload["context_sha256"] = stable_sha256({
            "kind": "h101_cross_authority_context",
            "suffix": suffix,
            "source_context_sha256": scope_payload["context_sha256"],
        })
    return CapabilityAuthority(
        scope=MemoryScope(**scope_payload),
        capability_catalog_sha256=stable_sha256({
            "kind": "h101_capability_catalog",
            "h99_sha256": h99["sha256"],
            "h100_sha256": h100["sha256"],
        }),
        evidence_epoch_sha256=stable_sha256({
            "kind": "h101_evidence_epoch",
            "h99_sha256": h99["sha256"],
            "h100_sha256": h100["sha256"],
        }),
        primitive_cost_unit="charged_environment_action",
    )


def species(owner: CapabilityAuthority):
    return (
        CapabilitySpecies(
            owner,
            "base_inference",
            "food",
            ("h95-live-causal-transport",),
        ),
        CapabilitySpecies(
            owner,
            "external_settlement",
            "food",
            ("h95-external-outcomes",),
        ),
        CapabilitySpecies(
            owner,
            "J_lineage_bound_judgment",
            "capability",
            ("h99-lineage-bound-branching",),
        ),
        CapabilitySpecies(
            owner,
            "D_sparse_settlement_design",
            "capability",
            ("h100-sparse-settlement",),
        ),
        CapabilitySpecies(
            owner,
            "E_false_edge_propagation",
            "error",
            ("h96-contract-failure",),
        ),
    )


def reactions(
    owner: CapabilityAuthority,
    *,
    reproduction_cost: int = 80,
    error_product: bool = False,
):
    judgment = "J_lineage_bound_judgment"
    design = "D_sparse_settlement_design"
    products = [(judgment, 3)]
    if error_product:
        products.append(("E_false_edge_propagation", 1))
    return (
        CatalyticCapabilityReaction(
            authority=owner,
            reaction_id="bootstrap_judgment",
            reactants=(
                ("base_inference", 1),
                ("external_settlement", 1),
            ),
            products=((judgment, 1),),
            catalyst_species_ids=("base_inference",),
            primitive_cost=0,
            bootstrap=True,
            evidence_refs=("h95-live-causal-transport",),
        ),
        CatalyticCapabilityReaction(
            authority=owner,
            reaction_id="invert_measurement_wall",
            reactants=((judgment, 1),),
            products=((judgment, 1), (design, 1)),
            catalyst_species_ids=(judgment,),
            primitive_cost=0,
            bootstrap=False,
            evidence_refs=("h99-to-h100-bottleneck-inversion",),
        ),
        CatalyticCapabilityReaction(
            authority=owner,
            reaction_id="reproduce_judgment",
            reactants=((judgment, 2), ("external_settlement", 1)),
            products=tuple(products),
            catalyst_species_ids=(design,),
            primitive_cost=reproduction_cost,
            bootstrap=False,
            evidence_refs=("h99-lineage", "h100-sparse-cost"),
        ),
    )


def topology_sha256(rows) -> str:
    return stable_sha256({
        "kind": "capability_reaction_topology_without_cost",
        "reactions": [
            {
                "reaction_id": row.reaction_id,
                "reactants": row.reactants,
                "products": row.products,
                "catalysts": row.catalyst_species_ids,
                "bootstrap": row.bootstrap,
            }
            for row in rows
        ],
    })


def caught(label, fn) -> dict:
    try:
        fn()
    except (KeyError, TypeError, ValueError) as exc:
        return {"label": label, "rejected": True, "reason": str(exc)}
    return {"label": label, "rejected": False, "reason": "accepted"}


def main() -> int:
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    h99 = json.loads(H99.read_text(encoding="utf-8"))
    h100 = json.loads(H100.read_text(encoding="utf-8"))
    if runtime["evidence_effect"] != "none" or runtime["environment_contact"]:
        raise RuntimeError("H97 runtime boundary changed")
    if h99["verdict"] != "supported" or h100["verdict"] != "supported":
        raise RuntimeError("H99/H100 prerequisites are not supported")

    owner = authority(h99, h100)
    capability_species = species(owner)
    sparse_reactions = reactions(owner, reproduction_cost=80)
    factorial_reactions = reactions(owner, reproduction_cost=160)
    sparse = compile_capability_autocatalysis(
        capability_species,
        sparse_reactions,
        primitive_budget=100,
    )
    factorial = compile_capability_autocatalysis(
        capability_species,
        factorial_reactions,
        primitive_budget=100,
    )

    # A directed cycle without a path from food is topological recurrence only.
    cycle_species = (
        CapabilitySpecies(owner, "cycle_food", "food", ("negative",)),
        CapabilitySpecies(owner, "cycle_j", "capability", ("negative",)),
        CapabilitySpecies(owner, "cycle_d", "capability", ("negative",)),
    )
    cycle_reactions = (
        CatalyticCapabilityReaction(
            owner, "cycle_j_to_d", (("cycle_j", 1),),
            (("cycle_d", 2),), ("cycle_d",), Fraction(0), False,
            ("negative",),
        ),
        CatalyticCapabilityReaction(
            owner, "cycle_d_to_j", (("cycle_d", 1),),
            (("cycle_j", 2),), ("cycle_j",), Fraction(0), False,
            ("negative",),
        ),
    )
    cycle = compile_capability_autocatalysis(
        cycle_species,
        cycle_reactions,
        primitive_budget=100,
    )

    # A food-generated product with a catalyst that is never available.
    uncatalyzed_species = (
        CapabilitySpecies(owner, "u_food", "food", ("negative",)),
        CapabilitySpecies(owner, "u_j", "capability", ("negative",)),
        CapabilitySpecies(owner, "u_missing", "error", ("negative",)),
    )
    uncatalyzed = compile_capability_autocatalysis(
        uncatalyzed_species,
        (
            CatalyticCapabilityReaction(
                owner, "uncatalyzed_route", (("u_food", 1),),
                (("u_j", 2),), ("u_missing",), Fraction(0), False,
                ("negative",),
            ),
        ),
        primitive_budget=100,
    )

    bootstrap_only = compile_capability_autocatalysis(
        (
            CapabilitySpecies(owner, "b_food", "food", ("negative",)),
            CapabilitySpecies(owner, "b_j", "capability", ("negative",)),
        ),
        (
            CatalyticCapabilityReaction(
                owner, "bootstrap_only", (("b_food", 1),),
                (("b_j", 1),), ("b_food",), Fraction(0), True,
                ("negative",),
            ),
        ),
        primitive_budget=100,
    )
    error_growth = compile_capability_autocatalysis(
        capability_species,
        reactions(owner, reproduction_cost=80, error_product=True),
        primitive_budget=100,
    )

    other = authority(h99, h100, suffix="crossed")
    crossed_species = list(capability_species)
    crossed_species[-1] = replace(crossed_species[-1], authority=other)
    crossed_reactions = list(sparse_reactions)
    crossed_reactions[-1] = replace(
        crossed_reactions[-1],
        authority=other,
    )
    identity_negatives = (
        caught(
            "cross_authority_species",
            lambda: compile_capability_autocatalysis(
                crossed_species, sparse_reactions, primitive_budget=100
            ),
        ),
        caught(
            "cross_authority_reaction",
            lambda: compile_capability_autocatalysis(
                capability_species, crossed_reactions, primitive_budget=100
            ),
        ),
        caught(
            "unknown_species_reference",
            lambda: compile_capability_autocatalysis(
                capability_species,
                (
                    replace(
                        sparse_reactions[0],
                        catalyst_species_ids=("undeclared",),
                    ),
                ),
                primitive_budget=100,
            ),
        ),
    )

    sparse_flux = sparse.growth_flux
    passed = bool(
        sparse.status == "productive_autocatalytic_core"
        and sparse_flux is not None
        and sparse_flux.total_primitive_cost == Fraction(80)
        and dict(sparse_flux.internal_net_production)[
            "J_lineage_bound_judgment"
        ] > 0
        and dict(sparse_flux.internal_net_production)[
            "D_sparse_settlement_design"
        ] > 0
        and dict(sparse_flux.net_production)[
            "E_false_edge_propagation"
        ] <= 0
        and factorial.status == "nonproductive_or_resource_blocked"
        and factorial.growth_flux is None
        and sparse.maximal_raf_reaction_ids
        == factorial.maximal_raf_reaction_ids
        and sparse.food_closure_species_ids
        == factorial.food_closure_species_ids
        and topology_sha256(sparse_reactions)
        == topology_sha256(factorial_reactions)
        and cycle.status
        == "no_reflexively_autocatalytic_food_generated_set"
        and uncatalyzed.status
        == "no_reflexively_autocatalytic_food_generated_set"
        and bootstrap_only.status == "nonproductive_or_resource_blocked"
        and error_growth.status == "nonproductive_or_resource_blocked"
        and all(row["rejected"] for row in identity_negatives)
        and not sparse.to_receipt()["takeoff_supported"]
    )

    core = {
        "schema": "ztare-h101-capability-autocatalytic-closure-audit-v1",
        "kind": "offline_theory_discriminator_result",
        "status": "offline_complete",
        "verdict": "supported" if passed else "rejected",
        "environment_contact": False,
        "controller_contact": False,
        "h97_runtime_boundary": {
            "receipt_ref": str(RUNTIME.relative_to(REPO)),
            "status": runtime["status"],
            "evidence_effect": runtime["evidence_effect"],
        },
        "prerequisites": {
            "h99": {
                "result_ref": str(H99.relative_to(REPO)),
                "sha256": h99["sha256"],
                "verdict": h99["verdict"],
            },
            "h100": {
                "result_ref": str(H100.relative_to(REPO)),
                "sha256": h100["sha256"],
                "verdict": h100["verdict"],
            },
        },
        "sparse_core": sparse.to_receipt(),
        "factorial_cost_counterfactual": factorial.to_receipt(),
        "same_topology_without_cost_sha256": topology_sha256(
            sparse_reactions
        ),
        "negative_fixtures": {
            "food_generation": cycle.to_receipt(),
            "catalysis": uncatalyzed.to_receipt(),
            "internal_production": bootstrap_only.to_receipt(),
            "error_growth": error_growth.to_receipt(),
            "identity": list(identity_negatives),
        },
        "nearest_prior_art": [
            {
                "component": "reflexively autocatalytic food-generated sets",
                "url": "https://arxiv.org/abs/2303.01809",
            },
            {
                "component": "RAF and stoichiometric autocatalysis relation",
                "url": "https://arxiv.org/abs/2605.25523",
            },
            {
                "component": "self-referential agent improvement",
                "url": "https://arxiv.org/abs/2410.04444",
            },
        ],
        "claim_boundary": [
            "The compiler distinguishes a cycle, a RAF, and a budget-feasible internally productive capability flux.",
            "On the preregistered synthetic topology, sparse settlement cost changes feasibility while topology and food closure remain fixed.",
            "The positive reaction set was constructed from prior H99/H100 outcomes rather than discovered in held-out behavior.",
            "The result is an algorithm and theory discriminator, not evidence of endogenous self-improvement or capability takeoff.",
            "RAF and stoichiometric components are established; literature novelty of the compiled join is not established.",
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
        "sparse_status": sparse.status,
        "sparse_cost": (
            str(sparse_flux.total_primitive_cost)
            if sparse_flux is not None
            else None
        ),
        "factorial_status": factorial.status,
        "negative_statuses": {
            "cycle": cycle.status,
            "uncatalyzed": uncatalyzed.status,
            "bootstrap_only": bootstrap_only.status,
            "error_growth": error_growth.status,
        },
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
