#!/usr/bin/env python3
"""Run H98's offline residual-fission and dual-criticality discriminator."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.constraint_isomorphism import SurfacedConjecture
from ztare.common.epistemic_autocatalysis import (
    MeasurementAxis,
    ResidualNicheCandidate,
    ResidualSettlementTrial,
    ResponseFissionAuthority,
    compile_residual_fission,
    settle_residual_fission,
    stable_sha256,
)
from ztare.common.wake_sleep_credit_router import MemoryScope
from ztare.research_director.research_isomorphism import (
    _prediction_cards,
    conjecture_between,
)


BASE = Path(__file__).resolve().parent
H97 = BASE / "h97_causal_response_derivative/manifest.json"
RUNTIME = (
    BASE
    / "h97_causal_response_derivative/live_attempt_01_runtime_receipt.json"
)
OUTPUT = BASE / "h98_epistemic_autocatalysis_result.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def conjecture_audit() -> dict:
    left = {
        "constraint_class": (
            "one settled response derivative produces at most one admissible "
            "descendant under full primitive cost"
        ),
        "abstract_form": (
            "typed causal operator has offspring cardinality bounded by one "
            "family and correlated descendants can amplify false edges"
        ),
        "home_field": "machine reasoning and ARC agents",
        "authority": "exact_task_context_controller_choice_set",
        "offspring_bound": "one_per_parent_family",
        "error_budget": "false_edges_must_not_reproduce",
        "cost": "primitive_environment_actions",
    }
    right = {
        "constraint_class": (
            "sparse predictive cortex expands one surprise into competing "
            "offline continuations and uses delayed outcome plus inhibition "
            "to settle them"
        ),
        "abstract_form": (
            "cheap replay opens latent niches; a later external signal gates "
            "tagged local changes; competition prevents runaway correlation"
        ),
        "home_field": "computational neuroscience",
        "expansion": "multiple_counterfactual_niches_per_surprise",
        "settlement": "delayed_external_prediction_error",
        "stability": "normalization_and_competition",
        "cost": "cheap_offline_replay_then_sparse_live_tests",
    }
    candidate = SurfacedConjecture(
        mother_structure=(
            "rank-quotiented counterfactual fission with multiplexed settlement"
        ),
        lowerings={
            "left": {
                "authority": (
                    "fission preserves the exact response authority tuple"
                ),
                "offspring_bound": (
                    "offspring is rank of distinguishable residual signatures"
                ),
                "error_budget": (
                    "a separate false-edge next-generation operator stays below one"
                ),
                "cost": (
                    "a measurement basis shares trajectories across residual tags"
                ),
            },
            "right": {
                "expansion": (
                    "offline residual simulations become candidate branches"
                ),
                "settlement": (
                    "pivot observables act as local eligibility tags"
                ),
                "stability": (
                    "rank quotient and error gate implement competition"
                ),
                "cost": (
                    "many replay candidates collapse before live contact"
                ),
            },
        },
        novel_predictions={
            "left": [{
                "prediction": (
                    "two non-collinear residual signatures yield effective "
                    "offspring two while proportional duplicates add zero"
                ),
                "measurement": (
                    "exact residual-signature rank and promoted child count"
                ),
                "intervention": (
                    "add orthogonal candidates plus proportional and linear "
                    "combination confusers"
                ),
                "horizon": "one offline fission and settlement generation",
                "expected_observation": (
                    "raw candidates four, independent offspring two"
                ),
                "novelty_reason": (
                    "family count cannot distinguish children from copies"
                ),
            }],
            "right": [{
                "prediction": (
                    "micro-randomized trajectories settle two pivot tags at "
                    "lower cost than isolated child trajectories"
                ),
                "measurement": (
                    "assignment rank, multiplexing gain, good and error radii"
                ),
                "intervention": (
                    "factorially vary both child offers inside shared trajectories"
                ),
                "horizon": "one four-trajectory factorial generation",
                "expected_observation": (
                    "rank two, good radius above one, error radius below one"
                ),
                "novelty_reason": (
                    "scalar reward without local tags creates correlated credit"
                ),
            }],
        },
        kill_conditions={
            "left": [{
                "refuter": (
                    "dependent candidates increase offspring above matrix rank"
                ),
                "gate": "exact residual-rank quotient",
                "receipt": "residual_fission_receipt",
            }],
            "right": [{
                "refuter": (
                    "rank-deficient settlement promotes two children, error "
                    "radius reaches one, or calibration exceeds tolerance"
                ),
                "gate": "multiplexed settlement and dual-criticality gate",
                "receipt": "epistemic_criticality_receipt",
            }],
        },
    )
    weak = SurfacedConjecture(
        mother_structure="unbounded brainstorming",
        lowerings={"left": {"authority": "ignore"}, "right": {}},
        novel_predictions={"left": ["more ideas help"]},
        kill_conditions={"left": ["none"]},
    )
    outcome = conjecture_between(
        left,
        right,
        query=lambda _left, _right, _n: [candidate, weak],
        ledger=None,
    )
    return {
        "query_receipt": outcome["query_receipt"],
        "kept": [row.mother_structure for row in outcome["conjectures"]],
        "rejected": [row.mother_structure for row in outcome["rejected"]],
        "specificity": [row.specificity for row in outcome["conjectures"]],
        "prediction_cards": _prediction_cards(outcome["conjectures"][0]),
    }


def candidate(
    authority: ResponseFissionAuthority,
    niche_ref: str,
    signature: tuple[int, ...],
    predicted: float,
) -> ResidualNicheCandidate:
    return ResidualNicheCandidate(
        authority=authority,
        niche_ref=niche_ref,
        response_signature=tuple(Fraction(value) for value in signature),
        predicted_information_yield=predicted,
        offline_replay_cost=0.1,
        evidence_refs=(f"h97-offline-derivative:{niche_ref}",),
    )


def trials(fission, *, false_edge=False, miscalibrated=False):
    assignments = (
        ("withhold", "withhold"),
        ("offer", "withhold"),
        ("withhold", "offer"),
        ("offer", "offer"),
    )
    predicted = {
        row.niche_ref: row.predicted_information_yield
        for row in fission.basis_niches
    }
    rows = []
    for trajectory_index, pattern in enumerate(assignments, start=1):
        for niche_index, (niche, assignment) in enumerate(
            zip(fission.basis_niches, pattern),
            start=1,
        ):
            offer = assignment == "offer"
            observed = (
                0.95
                if miscalibrated and offer
                else predicted[niche.niche_ref] + 0.1
                if offer
                else 0.1
            )
            rows.append(ResidualSettlementTrial(
                fission_sha256=fission.sha256,
                trajectory_ref=f"synthetic-trajectory-{trajectory_index}",
                niche_ref=niche.niche_ref,
                decision_index=2 + niche_index * 3,
                assignment=assignment,
                supported_transport=(
                    offer
                    or (false_edge and niche.niche_ref == "child-a")
                ),
                contradicted=False,
                pivot_axis_id=fission.pivot_axis(niche.niche_ref),
                local_external_value=0.8 if offer else 0.1,
                observed_information_yield=observed,
                trajectory_primitive_action_cost=20.0,
                settlement_observation_sha256=(
                    f"synthetic-observation-{trajectory_index}-{niche_index}"
                ),
            ))
    return tuple(rows)


def caught(label, fn) -> dict:
    try:
        fn()
    except (KeyError, TypeError, ValueError) as exc:
        return {"label": label, "rejected": True, "reason": str(exc)}
    return {"label": label, "rejected": False, "reason": "accepted"}


def main() -> int:
    h97 = json.loads(H97.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    if runtime["evidence_effect"] != "none" or runtime["environment_contact"]:
        raise RuntimeError("H97 runtime boundary changed")
    derivative = h97["live_response_derivative"]
    residual = derivative["residual_contract"]
    authority = ResponseFissionAuthority(
        scope=MemoryScope(**residual["scope"]),
        catalog_sha256=residual["catalog_sha256"],
        source_program_sha256=residual["source_program_sha256"],
        derivative_sha256=derivative["sha256"],
        intervention_revision_sha256=(
            residual["intervention_revision_sha256"]
        ),
        primitive_cost_unit="charged_environment_action",
    )
    axes = (
        MeasurementAxis("proposal_path_displacement", 0.5),
        MeasurementAxis("successor_event_partition", 0.5),
        MeasurementAxis("external_decision_yield", 2.0),
    )
    candidates = (
        candidate(authority, "child-a", (1, 0, 1), 0.6),
        candidate(authority, "child-b", (0, 1, 1), 0.7),
        candidate(authority, "child-a-copy", (2, 0, 2), 0.5),
        candidate(authority, "child-combination", (1, 1, 2), 0.1),
    )
    fission = compile_residual_fission(candidates, axes=axes)
    positive_trials = trials(fission)
    criticality = settle_residual_fission(fission, positive_trials)

    scalar = compile_residual_fission(
        (
            candidate(authority, "scalar-a", (1,), 0.6),
            candidate(authority, "scalar-copy", (2,), 0.5),
        ),
        axes=(MeasurementAxis("scalar", 1.0),),
    )
    false_receipt = settle_residual_fission(
        fission,
        trials(fission, false_edge=True),
    )
    miscalibrated_receipt = settle_residual_fission(
        fission,
        trials(fission, miscalibrated=True),
    )
    cross_authority = replace(
        candidates[1],
        authority=replace(
            authority,
            derivative_sha256="crossed-derivative",
        ),
    )
    negatives = [
        caught(
            "cross_authority",
            lambda: compile_residual_fission(
                (candidates[0], cross_authority),
                axes=axes,
            ),
        ),
        {
            "label": "scalar_correlation",
            "rejected": scalar.independent_offspring_capacity == 1,
            "reason": (
                "effective_offspring="
                f"{scalar.independent_offspring_capacity}"
            ),
        },
        caught(
            "incomplete_factorial",
            lambda: settle_residual_fission(
                fission,
                tuple(
                    row
                    for row in positive_trials
                    if row.trajectory_ref != "synthetic-trajectory-4"
                ),
            ),
        ),
        {
            "label": "false_edge_criticality",
            "rejected": (
                false_receipt.status == "subcritical_or_unresolved"
                and false_receipt.error_reproduction >= 1.0
            ),
            "reason": false_receipt.status,
        },
        {
            "label": "information_yield_miscalibration",
            "rejected": (
                miscalibrated_receipt.status
                == "subcritical_or_unresolved"
            ),
            "reason": miscalibrated_receipt.status,
        },
        caught(
            "declared_two_generations",
            lambda: settle_residual_fission(
                fission,
                positive_trials,
                observed_generations=2,
            ),
        ),
    ]
    conjecture = conjecture_audit()
    passed = bool(
        conjecture["kept"] == [
            "rank-quotiented counterfactual fission with multiplexed settlement"
        ]
        and conjecture["rejected"] == ["unbounded brainstorming"]
        and fission.independent_offspring_capacity == 2
        and set(fission.selected_measurement_axis_ids)
        == {"proposal_path_displacement", "successor_event_partition"}
        and criticality.knowledge_reproduction == 2.0
        and criticality.error_reproduction == 0.0
        and criticality.multiplexing_gain == 2.0
        and criticality.status == "supercritical_mechanism_candidate"
        and not criticality.to_receipt()["takeoff_supported"]
        and all(row["rejected"] for row in negatives)
    )
    core = {
        "schema": "ztare-h98-epistemic-autocatalysis-audit-v1",
        "kind": "offline_mechanism_result",
        "status": "offline_complete",
        "verdict": "supported" if passed else "rejected",
        "environment_contact": False,
        "controller_contact": False,
        "h97_runtime_boundary": {
            "receipt_ref": str(RUNTIME.relative_to(REPO)),
            "receipt_file_sha256": file_sha256(RUNTIME),
            "status": runtime["status"],
            "evidence_effect": runtime["evidence_effect"],
        },
        "h97_manifest_ref": str(H97.relative_to(REPO)),
        "h97_manifest_file_sha256": file_sha256(H97),
        "conjecture_mode": conjecture,
        "fission": fission.to_receipt(),
        "criticality": criticality.to_receipt(),
        "negative_fixtures": negatives,
        "claim_boundary": [
            "The synthetic mechanism reaches R_k=2 and R_e=0 for one generation.",
            "The result does not settle H97 or demonstrate live ARC offspring.",
            "The result does not authorize a capability-takeoff claim.",
            "The result does not establish literature novelty.",
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
        "raw_niche_count": len(fission.raw_niche_sha256s),
        "independent_offspring_capacity": (
            fission.independent_offspring_capacity
        ),
        "knowledge_reproduction": criticality.knowledge_reproduction,
        "error_reproduction": criticality.error_reproduction,
        "multiplexing_gain": criticality.multiplexing_gain,
        "criticality_status": criticality.status,
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
