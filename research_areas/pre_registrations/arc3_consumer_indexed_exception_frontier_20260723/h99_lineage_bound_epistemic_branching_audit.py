#!/usr/bin/env python3
"""Run H99's two-generation lineage and evidence-reuse discriminator."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.epistemic_autocatalysis import (
    MeasurementAxis,
    ResidualNicheCandidate,
    ResidualSettlementTrial,
    ResponseFissionAuthority,
    canonical_descendant_program_sha256,
    compile_epistemic_generation,
    compile_epistemic_lineage,
    compile_residual_fission,
    settle_residual_fission,
    stable_sha256,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


BASE = Path(__file__).resolve().parent
H97 = BASE / "h97_causal_response_derivative/manifest.json"
RUNTIME = (
    BASE
    / "h97_causal_response_derivative/live_attempt_01_runtime_receipt.json"
)
H98 = BASE / "h98_epistemic_autocatalysis_result.json"
OUTPUT = BASE / "h99_lineage_bound_epistemic_branching_result.json"


def candidate(
    authority: ResponseFissionAuthority,
    niche_ref: str,
    signature: tuple[int, ...],
    predicted: float,
    parents: tuple[str, ...],
) -> ResidualNicheCandidate:
    return ResidualNicheCandidate(
        authority=authority,
        niche_ref=niche_ref,
        response_signature=tuple(Fraction(value) for value in signature),
        predicted_information_yield=predicted,
        offline_replay_cost=0.1,
        evidence_refs=(f"h99-synthetic-replay:{niche_ref}",),
        parent_child_sha256s=parents,
    )


def factorial_trials(
    fission,
    *,
    prefix: str,
    false_niches: frozenset[str] = frozenset(),
):
    niches = tuple(row.niche_ref for row in fission.basis_niches)
    predicted = {
        row.niche_ref: row.predicted_information_yield
        for row in fission.basis_niches
    }
    rows = []
    for trajectory_index, pattern in enumerate(
        itertools.product(("withhold", "offer"), repeat=len(niches)),
        start=1,
    ):
        for niche_index, (niche_ref, assignment) in enumerate(
            zip(niches, pattern),
            start=1,
        ):
            offer = assignment == "offer"
            rows.append(ResidualSettlementTrial(
                fission_sha256=fission.sha256,
                trajectory_ref=f"{prefix}-trajectory-{trajectory_index}",
                niche_ref=niche_ref,
                decision_index=3 + niche_index * 4,
                assignment=assignment,
                supported_transport=(
                    offer or (not offer and niche_ref in false_niches)
                ),
                contradicted=False,
                pivot_axis_id=fission.pivot_axis(niche_ref),
                local_external_value=0.8 if offer else 0.1,
                observed_information_yield=(
                    predicted[niche_ref] + 0.1 if offer else 0.1
                ),
                trajectory_primitive_action_cost=20.0,
                settlement_observation_sha256=(
                    f"{prefix}-observation-{trajectory_index}-{niche_index}"
                ),
            ))
    return tuple(rows)


def inherited_authority() -> ResponseFissionAuthority:
    manifest = json.loads(H97.read_text(encoding="utf-8"))
    derivative = manifest["live_response_derivative"]
    residual = derivative["residual_contract"]
    return ResponseFissionAuthority(
        scope=MemoryScope(**residual["scope"]),
        catalog_sha256=residual["catalog_sha256"],
        source_program_sha256=residual["source_program_sha256"],
        derivative_sha256=derivative["sha256"],
        intervention_revision_sha256=(
            residual["intervention_revision_sha256"]
        ),
        primitive_cost_unit="charged_environment_action",
    )


def first_generation():
    authority = inherited_authority()
    root = (stable_sha256({
        "kind": "h99_synthetic_root",
        "h97_derivative_sha256": authority.derivative_sha256,
    }),)
    axes = (
        MeasurementAxis("proposal_path_displacement", 0.5),
        MeasurementAxis("successor_event_partition", 0.5),
        MeasurementAxis("external_decision_yield", 2.0),
    )
    fission = compile_residual_fission(
        (
            candidate(authority, "g1-a", (1, 0, 1), 0.6, root),
            candidate(authority, "g1-b", (0, 1, 1), 0.7, root),
            candidate(authority, "g1-a-copy", (2, 0, 2), 0.5, root),
            candidate(
                authority,
                "g1-combination",
                (1, 1, 2),
                0.1,
                root,
            ),
        ),
        axes=axes,
    )
    criticality = settle_residual_fission(
        fission,
        factorial_trials(fission, prefix="h99-g1"),
        parent_count=1,
    )
    generation = compile_epistemic_generation(
        fission,
        criticality,
        generation_index=1,
    )
    return fission, criticality, generation


def next_authority(first) -> ResponseFissionAuthority:
    parent = first.authority
    return ResponseFissionAuthority(
        scope=parent.scope,
        catalog_sha256=parent.catalog_sha256,
        source_program_sha256=canonical_descendant_program_sha256(
            first.promoted_child_sha256s
        ),
        derivative_sha256=stable_sha256({
            "kind": "h99_synthetic_second_derivative",
            "parent_child_sha256s": list(first.promoted_child_sha256s),
        }),
        intervention_revision_sha256=(
            parent.intervention_revision_sha256
        ),
        primitive_cost_unit=parent.primitive_cost_unit,
    )


def second_generation(
    first,
    *,
    child_count: int = 3,
    prefix: str = "h99-g2",
    false_niches: frozenset[str] = frozenset(),
):
    authority = next_authority(first)
    axes = tuple(
        MeasurementAxis(f"second_axis_{index}", 0.5)
        for index in range(child_count)
    )
    candidates = tuple(
        candidate(
            authority,
            f"g2-{index}",
            tuple(
                1 if index == column else 0
                for column in range(child_count)
            ),
            0.6,
            first.promoted_child_sha256s,
        )
        for index in range(child_count)
    )
    fission = compile_residual_fission(candidates, axes=axes)
    criticality = settle_residual_fission(
        fission,
        factorial_trials(
            fission,
            prefix=prefix,
            false_niches=false_niches,
        ),
        parent_count=len(first.promoted_child_sha256s),
    )
    generation = compile_epistemic_generation(
        fission,
        criticality,
        generation_index=2,
    )
    return fission, criticality, generation


def caught(label, fn) -> dict:
    try:
        fn()
    except (KeyError, TypeError, ValueError) as exc:
        return {"label": label, "rejected": True, "reason": str(exc)}
    return {"label": label, "rejected": False, "reason": "accepted"}


def main() -> int:
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    if runtime["evidence_effect"] != "none" or runtime["environment_contact"]:
        raise RuntimeError("H97 runtime boundary changed")
    h98 = json.loads(H98.read_text(encoding="utf-8"))
    if h98["verdict"] != "supported":
        raise RuntimeError("H98 prerequisite is not supported")

    first_fission, first_criticality, first = first_generation()
    second_fission, second_criticality, second = second_generation(first)
    lineage = compile_epistemic_lineage((first, second))

    parent_relabel = replace(
        second,
        parent_child_sha256s=("unrelated-parent",),
    )
    program_relabel = replace(
        second,
        authority=replace(
            second.authority,
            source_program_sha256="unrelated-program",
        ),
    )
    derivative_reuse = replace(
        second,
        authority=replace(
            second.authority,
            derivative_sha256=first.authority.derivative_sha256,
        ),
    )
    reused_trajectory = replace(
        second,
        trajectory_refs=(
            first.trajectory_refs[0],
            *second.trajectory_refs[1:],
        ),
    )
    reused_trial = replace(
        second,
        trial_sha256s=(first.trial_sha256s[0], *second.trial_sha256s[1:]),
    )
    reused_observation = replace(
        second,
        settlement_observation_sha256s=(
            first.settlement_observation_sha256s[0],
            *second.settlement_observation_sha256s[1:],
        ),
    )
    _, critical_criticality, critical_second = second_generation(
        first,
        child_count=2,
        prefix="h99-critical-g2",
    )
    critical_lineage = compile_epistemic_lineage(
        (first, critical_second)
    )
    _, false_criticality, false_second = second_generation(
        first,
        prefix="h99-false-g2",
        false_niches=frozenset({"g2-0", "g2-1"}),
    )
    false_lineage = compile_epistemic_lineage((first, false_second))

    negatives = (
        caught(
            "parent_relabel",
            lambda: compile_epistemic_lineage((first, parent_relabel)),
        ),
        caught(
            "program_family_relabel",
            lambda: compile_epistemic_lineage((first, program_relabel)),
        ),
        caught(
            "derivative_reuse",
            lambda: compile_epistemic_lineage((first, derivative_reuse)),
        ),
        caught(
            "trajectory_reuse",
            lambda: compile_epistemic_lineage((first, reused_trajectory)),
        ),
        caught(
            "trial_reuse",
            lambda: compile_epistemic_lineage((first, reused_trial)),
        ),
        caught(
            "observation_reuse",
            lambda: compile_epistemic_lineage((first, reused_observation)),
        ),
        {
            "label": "critical_second_generation",
            "rejected": (
                critical_criticality.knowledge_reproduction == 1.0
                and critical_lineage.status == "subcritical_or_unresolved"
            ),
            "reason": critical_lineage.status,
        },
        {
            "label": "false_edge_criticality",
            "rejected": (
                false_criticality.error_reproduction >= 1.0
                and false_lineage.status == "subcritical_or_unresolved"
            ),
            "reason": false_lineage.status,
        },
    )
    passed = bool(
        first_criticality.knowledge_reproduction == 2.0
        and first_criticality.error_reproduction == 0.0
        and second_criticality.knowledge_reproduction == 1.5
        and second_criticality.error_reproduction == 0.0
        and math.isclose(
            lineage.knowledge_geometric_growth,
            math.sqrt(3.0),
        )
        and lineage.error_geometric_growth == 0.0
        and lineage.validated_descendant_multiplier == 3.0
        and lineage.status == "multigeneration_mechanism_candidate"
        and lineage.to_receipt()["takeoff_supported"] is False
        and all(row["rejected"] for row in negatives)
    )
    core = {
        "schema": "ztare-h99-lineage-bound-epistemic-branching-audit-v1",
        "kind": "offline_mechanism_result",
        "status": "offline_complete",
        "verdict": "supported" if passed else "rejected",
        "environment_contact": False,
        "controller_contact": False,
        "h97_runtime_boundary": {
            "receipt_ref": str(RUNTIME.relative_to(REPO)),
            "status": runtime["status"],
            "evidence_effect": runtime["evidence_effect"],
        },
        "h98_result": {
            "result_ref": str(H98.relative_to(REPO)),
            "sha256": h98["sha256"],
            "verdict": h98["verdict"],
        },
        "first_generation": {
            "fission": first_fission.to_receipt(),
            "criticality": first_criticality.to_receipt(),
            "lineage_binding": first.to_receipt(),
        },
        "second_generation": {
            "fission": second_fission.to_receipt(),
            "criticality": second_criticality.to_receipt(),
            "lineage_binding": second.to_receipt(),
        },
        "lineage": lineage.to_receipt(),
        "negative_fixtures": list(negatives),
        "nearest_prior_art": [
            {
                "component": "micro-randomized causal excursion effects",
                "url": "https://arxiv.org/abs/2107.03544",
            },
            {
                "component": "three-factor eligibility traces",
                "url": "https://arxiv.org/abs/1801.05219",
            },
            {
                "component": "criticality measurement failure modes",
                "url": "https://arxiv.org/abs/1908.08163",
            },
            {
                "component": "Bayesian-surprise discovery trees",
                "url": "https://arxiv.org/abs/2507.00310",
            },
            {
                "component": "recursive two-timescale skill evolution",
                "url": "https://arxiv.org/abs/2607.05297",
            },
        ],
        "claim_boundary": [
            "Two synthetic generations are causally chained without evidence reuse.",
            "The finite-lineage knowledge growth factor is sqrt(3) and the error factor is zero.",
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
        "knowledge_growth_factors": [
            first.knowledge_reproduction,
            second.knowledge_reproduction,
        ],
        "knowledge_geometric_growth": (
            lineage.knowledge_geometric_growth
        ),
        "error_geometric_growth": lineage.error_geometric_growth,
        "validated_descendant_multiplier": (
            lineage.validated_descendant_multiplier
        ),
        "multiplexing_gain": lineage.multiplexing_gain,
        "lineage_status": lineage.status,
        "takeoff_supported": lineage.to_receipt()["takeoff_supported"],
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

