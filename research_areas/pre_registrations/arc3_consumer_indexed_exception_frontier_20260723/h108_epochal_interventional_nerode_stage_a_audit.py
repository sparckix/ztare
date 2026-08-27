#!/usr/bin/env python3
"""Compile H108's sealed retrospective model from the rejected H97 run.

H97 outcomes are construction data only.  This audit preserves their exact
episode identities, compiles the coarsest frozen pre-outcome projection, and
checks the refusal boundary before any H108 holdout contact.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
H97 = BASE / "h97_causal_response_derivative_app_server"
OUTPUT = BASE / "h108_epochal_interventional_nerode_stage_a_result.json"
OCCURRENCE_AMENDMENT = (
    BASE / "h108_pre_live_observation_occurrence_authority_amendment.md"
)
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.causal_response_derivative import (  # noqa: E402
    ResidualResponseContract,
    residual_plan_basin_sha256,
    residual_plan_basin_signature,
)
from ztare.common.interventional_nerode_consolidation import (  # noqa: E402
    InterventionalNerodeAuthority,
    canonical_projection_library,
    compile_exact_interventional_fiber,
    compile_interventional_nerode_epoch,
    settle_interventional_nerode_holdout,
    stable_sha256,
)
from ztare.common.object_basin_response import (  # noqa: E402
    object_proposal_from_receipt,
)
from ztare.common.wake_sleep_credit_router import MemoryScope  # noqa: E402


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_value(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def residual_contract_from_receipt(
    receipt: dict[str, Any],
) -> ResidualResponseContract:
    contract = ResidualResponseContract(
        scope=MemoryScope(**receipt["scope"]),
        catalog_sha256=str(receipt["catalog_sha256"]),
        intervention_revision_sha256=str(
            receipt["intervention_revision_sha256"]
        ),
        source_program_sha256=str(receipt["source_program_sha256"]),
        lineage_transport_sha256=str(receipt["lineage_transport_sha256"]),
        required_controlled_object_ref=str(
            receipt["required_controlled_object_ref"]
        ),
        pending_waypoint_refs=tuple(receipt["pending_waypoint_refs"]),
        discharged_waypoint_refs=tuple(receipt["discharged_waypoint_refs"]),
        forbidden_controlled_object_refs=tuple(
            receipt["forbidden_controlled_object_refs"]
        ),
        discharge_receipt_sha256s=tuple(
            receipt["discharge_receipt_sha256s"]
        ),
        evidence_refs=tuple(receipt["evidence_refs"]),
    )
    if contract.to_receipt() != receipt:
        raise ValueError("H97 residual contract receipt drifted")
    return contract


manifest_path = H97 / "manifest.json"
result_path = H97 / "result.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
h97_result = json.loads(result_path.read_text(encoding="utf-8"))
h97_result_core = {
    key: value for key, value in h97_result.items() if key != "sha256"
}
if h97_result["sha256"] != stable_sha256(h97_result_core):
    raise SystemExit("H97 result content identity drifted")
if h97_result["experiment_sha256"] != manifest["experiment_sha256"]:
    raise SystemExit("H97 manifest/result experiment identity drifted")
if h97_result["verdict"] != "rejected":
    raise SystemExit("H108 construction requires H97 to remain rejected")

residual_receipt = manifest["live_response_derivative"]["residual_contract"]
residual_contract = residual_contract_from_receipt(residual_receipt)
features = tuple(sorted(
    residual_plan_basin_signature(
        object_proposal_from_receipt(h97_result["pairs"][0]["pre_proposal"]),
        residual_contract,
    )
))

eligibility_rule = {
    "rule": manifest["matched_controller_fork"]["eligible_parent_rule"],
    "admission_phase": "before_branch_revision",
    "eligible_value": False,
    "predicate": "proposal_satisfies_residual_response",
}
live_interventions = manifest["live_interventions"]
intervention_set = {
    "controller_transport": manifest["controller_transport"],
    "causal_intervention_revision_sha256": live_interventions[
        "causal_intervention_revision_sha256"
    ],
    "causal_rendered_sha256": live_interventions["causal_rendered_sha256"],
    "placebo_rendered_sha256": live_interventions["placebo_rendered_sha256"],
    "rendered_utf8_bytes_per_condition": live_interventions[
        "rendered_utf8_bytes_per_condition"
    ],
    "primitive_action_cost": canonical_value(
        live_interventions["primitive_action_cost"]
    ),
}
utility_measure = {
    "task_score_weight": "4/5",
    "efficiency_score_weight": "1/5",
    "information_yield_in_utility": False,
    "matched_value_field": "offer_composite_minus_withhold",
    "matched_task_field": "offer_task_minus_withhold",
}
training_set = {
    "source_experiment_sha256": h97_result["experiment_sha256"],
    "source_result_sha256": h97_result["sha256"],
    "pair_evidence": [
        {
            "pair_index": row["pair_index"],
            "offer_outcome_sha256": row["offer_outcome"]["sha256"],
            "withhold_outcome_sha256": row["withhold_outcome"]["sha256"],
        }
        for row in h97_result["pairs"]
    ],
}
authority = InterventionalNerodeAuthority(
    scope_sha256=manifest["live_controller_scope_transport"][
        "target_scope_sha256"
    ],
    response_program_sha256=manifest["source_program"]["sha256"],
    derivative_sha256=manifest["live_response_derivative"]["sha256"],
    eligibility_rule_sha256=stable_sha256(eligibility_rule),
    intervention_set_sha256=stable_sha256(intervention_set),
    utility_measure_sha256=stable_sha256(utility_measure),
    restored_prefix_sha256=h97_result["environment_source"][
        "source_prefix_sha256"
    ],
    feature_catalog=features,
    candidate_projections=canonical_projection_library(features),
    training_set_sha256=stable_sha256(training_set),
    primitive_action_cost=Fraction(
        str(live_interventions["primitive_action_cost"])
    ),
    epoch=1,
)


def compile_h97_fiber(row: dict[str, Any]):
    pair_index = int(row["pair_index"])
    pair_receipt = json.loads(
        (H97 / "pairs" / f"pair_{pair_index:02d}.json").read_text(
            encoding="utf-8"
        )
    )
    proposal = object_proposal_from_receipt(row["pre_proposal"])
    signature = residual_plan_basin_signature(proposal, residual_contract)
    basin_sha256 = residual_plan_basin_sha256(proposal, residual_contract)
    if row["offer_transition"]["pre_basin_sha256"] != basin_sha256:
        raise ValueError(f"pair {pair_index} offer basin identity drifted")
    if row["withhold_transition"]["pre_basin_sha256"] != basin_sha256:
        raise ValueError(f"pair {pair_index} withhold basin identity drifted")
    parent_thread = pair_receipt["parent_attempt"]["controller_transport"]
    parent_state_sha256 = stable_sha256({
        "controller_transport_receipt_sha256": parent_thread["sha256"],
        "thread_id": parent_thread["thread_id"],
        "last_turn_id": parent_thread["last_turn_id"],
        "pre_proposal_sha256": proposal.sha256,
    })
    task_delta = Fraction(str(row["offer_task_minus_withhold"]))
    if task_delta.denominator != 1:
        raise ValueError("H97 task delta is not integral")
    settlement_path = H97 / "settlements" / f"pair_{pair_index:02d}.json"
    return compile_exact_interventional_fiber(
        authority_sha256=authority.sha256,
        parent_state_sha256=parent_state_sha256,
        pre_proposal_sha256=proposal.sha256,
        pre_observation_content_sha256=proposal.observation_sha256,
        exact_micro_basin_sha256=basin_sha256,
        feature_values=tuple(
            (key, canonical_value(signature[key])) for key in features
        ),
        fork_authority_sha256=row["fork_authority"]["sha256"],
        offer_transition_sha256=row["offer_transition"]["sha256"],
        withhold_transition_sha256=row["withhold_transition"]["sha256"],
        offer_evidence_sha256=row["offer_outcome"]["sha256"],
        withhold_evidence_sha256=row["withhold_outcome"]["sha256"],
        offer_supported=row["offer_transition"]["supported_transport"],
        withhold_supported=row["withhold_transition"]["supported_transport"],
        task_delta=int(task_delta),
        value_delta=Fraction(str(row["offer_composite_minus_withhold"])),
        offer_primitive_action_cost=Fraction(
            str(row["offer_outcome"]["primitive_action_cost"])
        ),
        withhold_primitive_action_cost=Fraction(
            str(row["withhold_outcome"]["primitive_action_cost"])
        ),
        evidence_refs=(
            row["offer_outcome"]["external_outcome_ref"],
            row["withhold_outcome"]["external_outcome_ref"],
            (
                f"{settlement_path.relative_to(ROOT)}"
                f"#sha256={file_sha256(settlement_path)}"
            ),
        ),
        phase="training",
    )


training_fibers = tuple(compile_h97_fiber(row) for row in h97_result["pairs"])
epoch = compile_interventional_nerode_epoch(authority, training_fibers)


def variant_fiber(
    base,
    label: str,
    *,
    phase: str = "training",
    authority_sha256: str | None = None,
    feature_values=None,
    offer_supported: bool | None = None,
    withhold_supported: bool | None = None,
    value_delta: Fraction | None = None,
    offer_evidence_sha256: str | None = None,
):
    return compile_exact_interventional_fiber(
        authority_sha256=authority_sha256 or base.authority_sha256,
        parent_state_sha256=f"variant-parent:{label}",
        pre_proposal_sha256=f"variant-proposal:{label}",
        pre_observation_content_sha256=(
            base.pre_observation_content_sha256
        ),
        exact_micro_basin_sha256=f"variant-basin:{label}",
        feature_values=feature_values or base.feature_values,
        fork_authority_sha256=f"variant-fork:{label}",
        offer_transition_sha256=f"variant-offer-transition:{label}",
        withhold_transition_sha256=f"variant-withhold-transition:{label}",
        offer_evidence_sha256=(
            offer_evidence_sha256 or f"variant-offer-evidence:{label}"
        ),
        withhold_evidence_sha256=f"variant-withhold-evidence:{label}",
        offer_supported=(
            base.offer_supported if offer_supported is None else offer_supported
        ),
        withhold_supported=(
            base.withhold_supported
            if withhold_supported is None
            else withhold_supported
        ),
        task_delta=base.task_delta,
        value_delta=base.value_delta if value_delta is None else value_delta,
        offer_primitive_action_cost=base.offer_primitive_action_cost,
        withhold_primitive_action_cost=base.withhold_primitive_action_cost,
        evidence_refs=(f"variant-evidence:{label}",),
        phase=phase,
    )


def expect_refusal(
    name: str,
    operation: Callable[[], object],
    expected_fragment: str,
) -> dict[str, Any]:
    try:
        operation()
    except ValueError as exc:
        message = str(exc)
        return {
            "name": name,
            "refused": expected_fragment in message,
            "reason": message,
            "expected_reason_fragment": expected_fragment,
        }
    return {
        "name": name,
        "refused": False,
        "reason": "operation unexpectedly accepted",
        "expected_reason_fragment": expected_fragment,
    }


negative_fiber = variant_fiber(
    training_fibers[1],
    "sign-opposite",
    value_delta=Fraction(-1, 100),
)
first_stage_fiber = variant_fiber(
    training_fibers[1],
    "first-stage-drift",
    offer_supported=False,
)
authority_drift_fiber = variant_fiber(
    training_fibers[0],
    "authority-drift",
    authority_sha256="crossed-authority",
)
post_outcome_fiber = variant_fiber(
    training_fibers[0],
    "post-outcome-feature",
    feature_values=(
        ("control_relation", canonical_value("forbidden")),
        ("pending_waypoint_order_satisfied", canonical_value(False)),
        ("post_outcome_win", canonical_value(True)),
    ),
)
reused_holdout = variant_fiber(
    training_fibers[0],
    "reused-holdout",
    phase="holdout",
    offer_evidence_sha256=training_fibers[0].offer_evidence_sha256,
)
other_holdout = variant_fiber(
    training_fibers[1],
    "other-holdout",
    phase="holdout",
    value_delta=Fraction(1, 100),
)

negative_controls = (
    expect_refusal(
        "sign_opposite_effect",
        lambda: compile_interventional_nerode_epoch(
            authority,
            (training_fibers[0], negative_fiber),
        ),
        "no candidate projection",
    ),
    expect_refusal(
        "first_stage_drift",
        lambda: compile_interventional_nerode_epoch(
            authority,
            (training_fibers[0], first_stage_fiber),
        ),
        "no candidate projection",
    ),
    expect_refusal(
        "authority_drift",
        lambda: compile_interventional_nerode_epoch(
            authority,
            (authority_drift_fiber,),
        ),
        "crossed consolidation authority",
    ),
    expect_refusal(
        "post_outcome_feature_insertion",
        lambda: compile_interventional_nerode_epoch(
            authority,
            (post_outcome_fiber,),
        ),
        "feature catalog drifted",
    ),
    expect_refusal(
        "training_evidence_reuse",
        lambda: settle_interventional_nerode_holdout(
            epoch,
            (reused_holdout, other_holdout),
        ),
        "reused training evidence",
    ),
    expect_refusal(
        "exact_fiber_duplication",
        lambda: compile_interventional_nerode_epoch(
            authority,
            (training_fibers[0], training_fibers[0]),
        ),
        "exact fiber identity was reused",
    ),
    expect_refusal(
        "candidate_library_mutation",
        lambda: replace(authority, candidate_projections=((),)),
        "projection library",
    ),
)

state = epoch.states[0]
checks = {
    "h97_remains_rejected": h97_result["verdict"] == "rejected",
    "two_exact_training_fibers": len(training_fibers) == 2,
    "exact_micro_basins_recoverable": (
        len({row.exact_micro_basin_sha256 for row in training_fibers}) == 2
    ),
    "coarsest_empty_projection_selected": epoch.selected_projection == (),
    "one_provisional_state": len(epoch.states) == 1,
    "sealed_positive_prediction": state.predicted_sign == "positive",
    "exact_prediction_mean_89_over_200": (
        state.predicted_value_delta == Fraction(89, 200)
    ),
    "promotion_denied_before_holdout": (
        epoch.to_receipt()["promotion_authorized"] is False
    ),
    "all_negative_controls_refused": all(
        row["refused"] for row in negative_controls
    ),
}
result = {
    "schema": "ztare-h108-epochal-interventional-nerode-stage-a-v1",
    "kind": "retrospective_construction_audit",
    "hypothesis_id": (
        "H-GPSA-EPOCHAL-INTERVENTIONAL-NERODE-CONSOLIDATION-20260808-108"
    ),
    "status": "retrospective_construction_complete",
    "environment_contact": False,
    "source": {
        "h97_manifest_ref": str(manifest_path.relative_to(ROOT)),
        "h97_manifest_file_sha256": file_sha256(manifest_path),
        "h97_experiment_sha256": h97_result["experiment_sha256"],
        "h97_result_ref": str(result_path.relative_to(ROOT)),
        "h97_result_sha256": h97_result["sha256"],
        "h97_result_file_sha256": file_sha256(result_path),
        "h97_verdict": h97_result["verdict"],
        "observation_occurrence_authority_amendment_ref": str(
            OCCURRENCE_AMENDMENT.relative_to(ROOT)
        ),
        "observation_occurrence_authority_amendment_file_sha256": (
            file_sha256(OCCURRENCE_AMENDMENT)
        ),
    },
    "frozen_inputs": {
        "eligibility_rule": eligibility_rule,
        "intervention_set": intervention_set,
        "utility_measure": utility_measure,
        "training_set": training_set,
    },
    "authority": authority.to_receipt(),
    "frozen_epoch": epoch.to_receipt(),
    "stage_a_observations": {
        "training_fiber_count": len(training_fibers),
        "exact_micro_basin_sha256s": sorted(
            row.exact_micro_basin_sha256 for row in training_fibers
        ),
        "selected_projection": list(epoch.selected_projection),
        "state_count": len(epoch.states),
        "predicted_value_delta": (
            f"{state.predicted_value_delta.numerator}/"
            f"{state.predicted_value_delta.denominator}"
        ),
        "predicted_sign": state.predicted_sign,
        "promoted_child_count": 0,
    },
    "checks": dict(sorted(checks.items())),
    "negative_controls": list(negative_controls),
    "verdict": (
        "stage_a_passed_no_promotion"
        if all(checks.values())
        else "stage_a_rejected"
    ),
    "claim_boundary": {
        "retrospective_compiler_construction_only": True,
        "predictive_validation_supported": False,
        "child_reproduction_supported": False,
        "compounding_supported": False,
        "supercriticality_supported": False,
        "takeoff_supported": False,
        "literature_novelty_claimed": False,
    },
}
result["sha256"] = stable_sha256(result)
OUTPUT.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "output": str(OUTPUT.relative_to(ROOT)),
    "result_sha256": result["sha256"],
    "file_sha256": file_sha256(OUTPUT),
    "verdict": result["verdict"],
    "selected_projection": result["stage_a_observations"][
        "selected_projection"
    ],
    "predicted_value_delta": result["stage_a_observations"][
        "predicted_value_delta"
    ],
    "negative_controls": {
        row["name"]: row["refused"] for row in negative_controls
    },
}, indent=2, sort_keys=True))
