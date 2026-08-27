#!/usr/bin/env python3
"""Settle H108's sealed prediction on a fresh H97-protocol acquisition."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
STAGE_A = BASE / "h108_epochal_interventional_nerode_stage_a_result.json"
STAGE_B_MANIFEST = (
    BASE / "h108_epochal_interventional_nerode_stage_b_manifest.json"
)
TRAINING_H97 = BASE / "h97_causal_response_derivative_app_server"
ACQUISITION_SCRIPT = (
    ROOT / "scripts/public/control/arc3_causal_response_derivative_probe.py"
)
SETTLEMENT_SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.causal_response_derivative import (  # noqa: E402
    ResidualResponseContract,
    residual_plan_basin_sha256,
    residual_plan_basin_signature,
)
from ztare.common.interventional_nerode_consolidation import (  # noqa: E402
    compile_exact_interventional_fiber,
    interventional_nerode_epoch_from_receipt,
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


def load_hashed_result(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    core = {key: value for key, value in receipt.items() if key != "sha256"}
    if receipt.get("sha256") != stable_sha256(core):
        raise ValueError(f"content identity drifted: {path}")
    return receipt


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
        raise ValueError("residual contract receipt drifted")
    return contract


def eligibility_rule(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule": manifest["matched_controller_fork"]["eligible_parent_rule"],
        "admission_phase": "before_branch_revision",
        "eligible_value": False,
        "predicate": "proposal_satisfies_residual_response",
    }


def intervention_set(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest["live_interventions"]
    return {
        "controller_transport": manifest["controller_transport"],
        "causal_intervention_revision_sha256": live[
            "causal_intervention_revision_sha256"
        ],
        "causal_rendered_sha256": live["causal_rendered_sha256"],
        "placebo_rendered_sha256": live["placebo_rendered_sha256"],
        "rendered_utf8_bytes_per_condition": live[
            "rendered_utf8_bytes_per_condition"
        ],
        "primitive_action_cost": canonical_value(live["primitive_action_cost"]),
    }


parser = argparse.ArgumentParser()
parser.add_argument("--holdout-dir", type=Path, required=True)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
holdout_dir = args.holdout_dir.resolve()
output = (args.output or (holdout_dir / "h108_settlement.json")).resolve()
try:
    holdout_rel = holdout_dir.relative_to(ROOT)
except ValueError as exc:
    raise SystemExit("holdout directory must be inside the repository") from exc

stage_a = load_hashed_result(STAGE_A)
stage_b_manifest = load_hashed_result(STAGE_B_MANIFEST)
if stage_a["verdict"] != "stage_a_passed_no_promotion":
    raise SystemExit("Stage A did not freeze a usable prediction")
if file_sha256(STAGE_A) != stage_b_manifest["stage_a_result_file_sha256"]:
    raise SystemExit("Stage-A file changed after Stage-B freeze")
if stage_a["sha256"] != stage_b_manifest["stage_a_result_sha256"]:
    raise SystemExit("Stage-A result changed after Stage-B freeze")
if file_sha256(ACQUISITION_SCRIPT) != stage_b_manifest[
    "acquisition_protocol"
]["script_file_sha256"]:
    raise SystemExit("acquisition protocol changed after Stage-B freeze")
if file_sha256(SETTLEMENT_SCRIPT) != stage_b_manifest[
    "acquisition_protocol"
]["settlement_script_file_sha256"]:
    raise SystemExit("settlement protocol changed after Stage-B freeze")
if str(holdout_rel) != stage_b_manifest["acquisition_protocol"]["output_dir"]:
    raise SystemExit("holdout output identity differs from Stage-B freeze")

epoch = interventional_nerode_epoch_from_receipt(stage_a["frozen_epoch"])
if epoch.sha256 != stage_b_manifest["frozen_epoch_sha256"]:
    raise SystemExit("sealed epoch identity drifted")
state = epoch.states[0]
sealed = stage_b_manifest["sealed_prediction"]
if (
    state.sha256 != sealed["state_sha256"]
    or state.predicted_sign != sealed["predicted_sign"]
    or (
        f"{state.predicted_value_delta.numerator}/"
        f"{state.predicted_value_delta.denominator}"
    ) != sealed["predicted_value_delta"]
):
    raise SystemExit("sealed prediction drifted")

training_manifest = json.loads(
    (TRAINING_H97 / "manifest.json").read_text(encoding="utf-8")
)
holdout_manifest_path = holdout_dir / "manifest.json"
holdout_result_path = holdout_dir / "result.json"
holdout_manifest = json.loads(
    holdout_manifest_path.read_text(encoding="utf-8")
)
holdout_result = load_hashed_result(holdout_result_path)
if holdout_result["status"] != "live_complete":
    raise SystemExit("holdout acquisition did not complete")
if not holdout_result["environment_contact"]:
    raise SystemExit("holdout acquisition has no environment contact")
if holdout_result["experiment_sha256"] != holdout_manifest["experiment_sha256"]:
    raise SystemExit("holdout manifest/result experiment identity drifted")

frozen_inputs = stage_a["frozen_inputs"]
authority_checks = {
    "acquisition_protocol_experiment_preserved": (
        holdout_manifest["experiment_sha256"]
        == stage_b_manifest["acquisition_protocol"][
            "source_h97_experiment_sha256"
        ]
    ),
    "controller_transport_preserved": (
        holdout_manifest["controller_transport"] == "codex_app_server"
    ),
    "scope_preserved": (
        holdout_manifest["live_controller_scope_transport"][
            "target_scope_sha256"
        ]
        == epoch.authority.scope_sha256
    ),
    "response_program_preserved": (
        holdout_manifest["source_program"]["sha256"]
        == epoch.authority.response_program_sha256
    ),
    "derivative_preserved": (
        holdout_manifest["live_response_derivative"]["sha256"]
        == epoch.authority.derivative_sha256
    ),
    "eligibility_rule_preserved": (
        stable_sha256(eligibility_rule(holdout_manifest))
        == epoch.authority.eligibility_rule_sha256
    ),
    "intervention_set_preserved": (
        stable_sha256(intervention_set(holdout_manifest))
        == epoch.authority.intervention_set_sha256
    ),
    "restored_prefix_preserved": (
        holdout_result["environment_source"]["source_prefix_sha256"]
        == epoch.authority.restored_prefix_sha256
    ),
    "primitive_action_cost_preserved": (
        Fraction(str(holdout_manifest["live_interventions"][
            "primitive_action_cost"
        ]))
        == epoch.authority.primitive_action_cost
    ),
    "pair_count_preserved": len(holdout_result["pairs"]) == 2,
    "arm_order_preserved": (
        [row["arm_order"] for row in holdout_result["pairs"]]
        == stage_b_manifest["acquisition_protocol"]["arm_order"]
    ),
    "training_frozen_input_receipts_preserved": (
        eligibility_rule(training_manifest) == frozen_inputs["eligibility_rule"]
        and intervention_set(training_manifest)
        == frozen_inputs["intervention_set"]
    ),
}
if not all(authority_checks.values()):
    failed = sorted(key for key, value in authority_checks.items() if not value)
    raise SystemExit(f"H108 holdout crossed authority: {failed}")

residual_receipt = holdout_manifest["live_response_derivative"][
    "residual_contract"
]
residual_contract = residual_contract_from_receipt(residual_receipt)


def compile_holdout_fiber(row: dict[str, Any]):
    pair_index = int(row["pair_index"])
    pair_path = holdout_dir / "pairs" / f"pair_{pair_index:02d}.json"
    pair_receipt = json.loads(pair_path.read_text(encoding="utf-8"))
    proposal = object_proposal_from_receipt(row["pre_proposal"])
    signature = residual_plan_basin_signature(proposal, residual_contract)
    if tuple(sorted(signature)) != epoch.authority.feature_catalog:
        raise ValueError("holdout pre-outcome feature catalog drifted")
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
        raise ValueError("holdout task delta is not integral")
    settlement_path = (
        holdout_dir / "settlements" / f"pair_{pair_index:02d}.json"
    )
    return compile_exact_interventional_fiber(
        authority_sha256=epoch.authority.sha256,
        parent_state_sha256=parent_state_sha256,
        pre_proposal_sha256=proposal.sha256,
        pre_observation_content_sha256=proposal.observation_sha256,
        exact_micro_basin_sha256=basin_sha256,
        feature_values=tuple(
            (key, canonical_value(signature[key]))
            for key in epoch.authority.feature_catalog
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
        phase="holdout",
    )


holdout_fibers = tuple(
    compile_holdout_fiber(row) for row in holdout_result["pairs"]
)
training_sets = {
    "parent_state": {row.parent_state_sha256 for row in epoch.training_fibers},
    "pre_proposal": {row.pre_proposal_sha256 for row in epoch.training_fibers},
    "pre_observation_occurrence": {
        row.pre_observation_occurrence_sha256 for row in epoch.training_fibers
    },
    "fork": {row.fork_authority_sha256 for row in epoch.training_fibers},
    "transition": {
        value
        for row in epoch.training_fibers
        for value in (
            row.offer_transition_sha256,
            row.withhold_transition_sha256,
        )
    },
    "outcome_evidence": {
        value
        for row in epoch.training_fibers
        for value in (
            row.offer_evidence_sha256,
            row.withhold_evidence_sha256,
        )
    },
}
holdout_sets = {
    "parent_state": {row.parent_state_sha256 for row in holdout_fibers},
    "pre_proposal": {row.pre_proposal_sha256 for row in holdout_fibers},
    "pre_observation_occurrence": {
        row.pre_observation_occurrence_sha256 for row in holdout_fibers
    },
    "fork": {row.fork_authority_sha256 for row in holdout_fibers},
    "transition": {
        value
        for row in holdout_fibers
        for value in (
            row.offer_transition_sha256,
            row.withhold_transition_sha256,
        )
    },
    "outcome_evidence": {
        value
        for row in holdout_fibers
        for value in (
            row.offer_evidence_sha256,
            row.withhold_evidence_sha256,
        )
    },
}
disjoint_checks = {
    f"training_holdout_{key}_disjoint": not training_sets[key].intersection(
        holdout_sets[key]
    )
    for key in sorted(training_sets)
}
if not all(disjoint_checks.values()):
    failed = sorted(key for key, value in disjoint_checks.items() if not value)
    raise SystemExit(f"H108 holdout reused training identity: {failed}")

settlement = settle_interventional_nerode_holdout(epoch, holdout_fibers)
settlement_receipt = settlement.to_receipt()
observed_total_task_delta = sum(row.task_delta for row in holdout_fibers)
observed_mean_value_delta = (
    sum((row.value_delta for row in holdout_fibers), Fraction(0))
    / len(holdout_fibers)
)
result = {
    "schema": "ztare-h108-epochal-interventional-nerode-stage-b-result-v1",
    "kind": "fresh_withheld_branch_settlement",
    "hypothesis_id": stage_b_manifest["hypothesis_id"],
    "status": "fresh_holdout_complete",
    "environment_contact": True,
    "stage_b_manifest_ref": str(STAGE_B_MANIFEST.relative_to(ROOT)),
    "stage_b_manifest_sha256": stage_b_manifest["sha256"],
    "stage_b_manifest_file_sha256": file_sha256(STAGE_B_MANIFEST),
    "stage_a_result_sha256": stage_a["sha256"],
    "frozen_epoch_sha256": epoch.sha256,
    "sealed_prediction": sealed,
    "acquisition": {
        "holdout_dir": str(holdout_rel),
        "manifest_ref": str(holdout_manifest_path.relative_to(ROOT)),
        "manifest_file_sha256": file_sha256(holdout_manifest_path),
        "result_ref": str(holdout_result_path.relative_to(ROOT)),
        "result_sha256": holdout_result["sha256"],
        "result_file_sha256": file_sha256(holdout_result_path),
        "acquisition_verdict": holdout_result["verdict"],
        "pair_count": len(holdout_fibers),
    },
    "authority_checks": dict(sorted(authority_checks.items())),
    "identity_disjointness_checks": dict(sorted(disjoint_checks.items())),
    "observation_identity": {
        "training_content_sha256s": sorted({
            row.pre_observation_content_sha256 for row in epoch.training_fibers
        }),
        "holdout_content_sha256s": sorted({
            row.pre_observation_content_sha256 for row in holdout_fibers
        }),
        "content_recurrence_allowed": True,
        "occurrence_identity_disjoint": disjoint_checks[
            "training_holdout_pre_observation_occurrence_disjoint"
        ],
    },
    "observed": {
        "total_task_delta": observed_total_task_delta,
        "mean_value_delta": (
            f"{observed_mean_value_delta.numerator}/"
            f"{observed_mean_value_delta.denominator}"
        ),
        "positive_pair_count": sum(
            row.value_delta > 0 for row in holdout_fibers
        ),
        "negative_pair_count": sum(
            row.value_delta < 0 for row in holdout_fibers
        ),
        "offer_supported_count": sum(
            row.offer_supported for row in holdout_fibers
        ),
        "withhold_supported_count": sum(
            row.withhold_supported for row in holdout_fibers
        ),
    },
    "settlement": settlement_receipt,
    "response_reproduction_before": 0,
    "response_reproduction_after": 1 if settlement.promoted else 0,
    "verdict": (
        "promoted_one_predictive_state"
        if settlement.promoted
        else "refinement_required"
    ),
    "claim_boundary": {
        "same_task_predictive_consolidation_supported": settlement.promoted,
        "one_response_child_supported": settlement.promoted,
        "supercriticality_supported": False,
        "compounding_supported": False,
        "cross_task_transfer_supported": False,
        "autonomous_question_generation_supported": False,
        "takeoff_supported": False,
        "literature_novelty_claimed": False,
    },
}
result["sha256"] = stable_sha256(result)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "output": str(output.relative_to(ROOT)),
    "result_sha256": result["sha256"],
    "file_sha256": file_sha256(output),
    "verdict": result["verdict"],
    "observed": result["observed"],
    "settlement_checks": settlement_receipt["checks"],
    "counterexamples": settlement_receipt["counterexamples"],
}, indent=2, sort_keys=True))
