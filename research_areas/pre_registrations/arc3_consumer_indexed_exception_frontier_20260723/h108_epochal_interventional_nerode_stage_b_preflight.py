#!/usr/bin/env python3
"""Seal H108 Stage B before fresh controller or environment contact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
STAGE_A = BASE / "h108_epochal_interventional_nerode_stage_a_result.json"
H97_MANIFEST = BASE / "h97_causal_response_derivative_app_server/manifest.json"
ACQUISITION_SCRIPT = (
    ROOT / "scripts/public/control/arc3_causal_response_derivative_probe.py"
)
SETTLEMENT_SCRIPT = (
    BASE / "h108_epochal_interventional_nerode_stage_b_settlement.py"
)
HOLDOUT = BASE / "h108_epochal_interventional_nerode_holdout"
OUTPUT = BASE / "h108_epochal_interventional_nerode_stage_b_manifest.json"
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.interventional_nerode_consolidation import (  # noqa: E402
    stable_sha256,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


stage_a = json.loads(STAGE_A.read_text(encoding="utf-8"))
stage_a_core = {key: value for key, value in stage_a.items() if key != "sha256"}
if stage_a["sha256"] != stable_sha256(stage_a_core):
    raise SystemExit("H108 Stage-A result content identity drifted")
if stage_a["verdict"] != "stage_a_passed_no_promotion":
    raise SystemExit("H108 Stage A has not earned a frozen prediction")
if HOLDOUT.exists() and any(HOLDOUT.iterdir()):
    raise SystemExit("H108 holdout directory already contains contact artifacts")

h97_manifest = json.loads(H97_MANIFEST.read_text(encoding="utf-8"))
state = stage_a["frozen_epoch"]["states"][0]
manifest = {
    "schema": "ztare-h108-epochal-interventional-nerode-stage-b-manifest-v1",
    "kind": "prospective_withheld_branch_prediction",
    "hypothesis_id": (
        "H-GPSA-EPOCHAL-INTERVENTIONAL-NERODE-CONSOLIDATION-20260808-108"
    ),
    "status": "frozen_before_holdout_contact",
    "environment_contact": False,
    "stage_a_result_ref": str(STAGE_A.relative_to(ROOT)),
    "stage_a_result_sha256": stage_a["sha256"],
    "stage_a_result_file_sha256": file_sha256(STAGE_A),
    "frozen_epoch_sha256": stage_a["frozen_epoch"]["sha256"],
    "sealed_prediction": {
        "state_sha256": state["sha256"],
        "projection": state["projection"],
        "quotient_key": state["quotient_key"],
        "predicted_value_delta": state["predicted_value_delta"],
        "predicted_sign": state["predicted_sign"],
    },
    "acquisition_protocol": {
        "source_h97_experiment_sha256": h97_manifest["experiment_sha256"],
        "script_ref": str(ACQUISITION_SCRIPT.relative_to(ROOT)),
        "script_file_sha256": file_sha256(ACQUISITION_SCRIPT),
        "settlement_script_ref": str(SETTLEMENT_SCRIPT.relative_to(ROOT)),
        "settlement_script_file_sha256": file_sha256(SETTLEMENT_SCRIPT),
        "controller_transport": "codex_app_server",
        "output_dir": str(HOLDOUT.relative_to(ROOT)),
        "timeout_seconds": 900.0,
        "pair_count": 2,
        "arm_order": [
            ["offer", "withhold"],
            ["withhold", "offer"],
        ],
        "primitive_action_cost_per_arm": "20/1",
    },
    "authority_correction_refs": [
        (
            "research_areas/pre_registrations/"
            "arc3_consumer_indexed_exception_frontier_20260723/"
            "h108_pre_live_observation_occurrence_authority_amendment.md"
        ),
        (
            "research_areas/pre_registrations/"
            "arc3_consumer_indexed_exception_frontier_20260723/"
            "h97_pre_live_subscription_fork_transport_amendment.md"
        ),
    ],
    "success_criterion": {
        "fresh_exact_fibers": 2,
        "single_frozen_state": True,
        "offer_supported_transport_rate": "2/2",
        "withhold_supported_transport_rate": "0/2",
        "nonnegative_total_task_delta": True,
        "positive_mean_value_delta": True,
        "minimum_positive_pairs": 1,
        "negative_pairs": 0,
        "positive_sign_predictions_correct": "2/2",
        "promoted_child_count": 1,
        "response_reproduction_change": "0->1",
    },
    "claim_boundary": {
        "supercriticality_supported": False,
        "compounding_supported": False,
        "takeoff_supported": False,
        "literature_novelty_claimed": False,
    },
}
manifest["sha256"] = stable_sha256(manifest)
OUTPUT.write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "output": str(OUTPUT.relative_to(ROOT)),
    "manifest_sha256": manifest["sha256"],
    "file_sha256": file_sha256(OUTPUT),
    "frozen_epoch_sha256": manifest["frozen_epoch_sha256"],
    "sealed_prediction": manifest["sealed_prediction"],
    "environment_contact": False,
}, indent=2, sort_keys=True))
