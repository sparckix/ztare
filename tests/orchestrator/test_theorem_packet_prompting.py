import hashlib
import json
from pathlib import Path

from ztare.common.operator_proposal_contract import write_proposal_cards
from ztare.orchestrator.briefing_providers.contract_rules import ContractRulesProvider
from ztare.orchestrator.mutator_briefing import BriefingContext
from ztare.orchestrator.submission_path_helpers import (
    detect_submission_contract,
    format_r1_retry_skeleton,
    requires_i_model_submission,
    submission_contract_kind,
)


def _rubric() -> dict:
    return {
        "fit_score_mode": "none",
        "require_i_model_in_submission": False,
        "theorem_packet_contract": {
            "required_top_level_functions": [
                "vector_ledger_terms",
                "trackb_convexity_theorem",
            ]
        },
    }


def _qualitative_rubric() -> dict:
    return {
        "rubric_mode": "calibration",
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": False,
        "enable_fit_primitive_features": False,
        "fit_score_mode": "none",
        "holdout_hard_gate": False,
        "holdout_budget": 0,
        "disable_evidence_fit_gate": True,
        "disable_uniqueness_gap_gate": True,
    }


def _worldmodel_rubric() -> dict:
    return {
        "rubric_mode": "calibration",
        "substrate_class": "interactive_environment",
        "fit_expression_grammar": "grid_dsl",
        "fit_score_mode": "discrete_exact",
        "require_i_model_in_submission": False,
        "enable_fit_primitive": False,
        "disable_evidence_fit_gate": True,
        "disable_uniqueness_gap_gate": True,
    }


def test_theorem_packet_retry_preserves_packet_api_not_scalar_paths():
    prompt = format_r1_retry_skeleton(
        "Python suite executed but does not define `I_model`.",
        "def vector_ledger_terms():\n    return {}",
        rubric_data=_rubric(),
    )

    assert "theorem-packet" in prompt
    assert "def vector_ledger_terms()" in prompt
    assert "def trackb_convexity_theorem()" in prompt
    assert "Do not switch to the generic numeric-declaration template" in prompt
    assert "PARAMETRIC MODEL DECLARATION" not in prompt
    assert "VARIATIONAL/LAGRANGIAN DECLARATION" not in prompt


def test_qualitative_retry_uses_assertion_suite_not_scalar_paths():
    prompt = format_r1_retry_skeleton(
        "Missing required Python falsification suite block.",
        "## Thesis\nA bounded mechanism claim.",
        rubric_data=_qualitative_rubric(),
    )

    assert "assertion suite" in prompt
    assert "PARAMETRIC MODEL DECLARATION" not in prompt
    assert "VARIATIONAL/LAGRANGIAN DECLARATION" not in prompt
    assert "def test_mechanism_is_bounded()" in prompt
    assert "no I_model" in prompt


def test_worldmodel_retry_allows_control_moves_without_dummy_carrier():
    prompt = format_r1_retry_skeleton(
        "no PROGRAM (grid_dsl AST as nested lists) in submission",
        "def test_mechanism_is_bounded():\n    assert True",
        rubric_data=_worldmodel_rubric(),
    )

    assert "Return only one raw JSON object" in prompt
    assert "`control_receipts`" in prompt
    assert "`test_model_py`" in prompt
    assert "Candidate submissions need an executable transition carrier" in prompt
    assert "registered workbench action request" in prompt
    assert "PATCH_BASE" in prompt
    assert "PATCH_DELTA" in prompt
    assert "executable transition carrier" in prompt
    assert "WORLD_MODEL_SPEC" in prompt
    assert "PROGRAM" in prompt
    assert "identity fallback" in prompt
    assert "return tuple(tuple(row) for row in grid)" not in prompt
    assert "assertion suite" not in prompt
    assert "thesis prose plus test_model.py" not in prompt
    assert "PARAMETRIC MODEL DECLARATION" not in prompt


def test_worldmodel_patch_base_regression_retry_attaches_authoritative_source(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    submissions = workspace / "submissions"
    workspace.mkdir()
    submissions.mkdir()
    patch_base = submissions / "base.py"
    patch_base.write_text(
        "# patch base\n"
        "def helper():\n"
        "    return 41\n\n"
        "def step(grid, action, t):\n"
        "    return tuple(tuple(row) for row in grid)\n",
        encoding="utf-8",
    )
    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                            "source_type": "deterministic_near_miss",
                            "submission": "workspace/submissions/base.py",
                        "sha": "abc123",
                        "visible_exact_rows": 99,
                        "visible_checked_rows": 100,
                        "visible_wrong_cells": 4,
                        "holdout_depth": 0,
                        "gate_score": 0.3333,
                        "source_excerpt": "# truncated excerpt only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        "PATCH_BASE_IMPROVEMENT_PRECHECK: candidate loses the best deterministic near-miss",
        "def step(grid, action, t): return grid",
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )
    base_digest = hashlib.sha256((workspace / "submissions" / "base.py").read_bytes()).hexdigest()

    assert "AUTHORITATIVE PATCH BASE REFERENCE" in prompt
    assert "patch_base_ref: workspace/submissions/base.py" in prompt
    assert f"patch_base_sha: {base_digest}" in prompt
    assert "visible_exact_rows: 99/100" in prompt
    assert "PATCH_BASE" in prompt
    assert "def helper()" not in prompt
    assert "# truncated excerpt only" not in prompt


def test_worldmodel_patch_base_retry_attaches_fresh_counterexample_context(
    tmp_path: Path,
):
    from ztare.worldmodel.episode_log import EpisodeLog

    workspace = tmp_path / "workspace"
    episodes = tmp_path / "raw" / "episodes"
    workspace.mkdir()
    episodes.mkdir(parents=True)
    log = EpisodeLog()
    log.append(
        ((7, 8, 8), (7, 8, 8), (0, 0, 0)),
        1,
        ((7, 3, 8), (7, 3, 8), (0, 0, 0)),
        t=5,
    )
    log.append(
        ((0, 8, 8), (0, 8, 8), (0, 0, 0)),
        1,
        ((0, 8, 8), (0, 8, 8), (0, 0, 0)),
        t=5,
    )
    log.write_jsonl(episodes / "episode_001.jsonl")
    (workspace / "latest_patch_base_regression.json").write_text(
        json.dumps(
            {
                "schema": "ztare-latest-patch-base-regression-v1",
                "candidate_regression_receipt": {
                    "schema": "ztare-candidate-regression-receipt-v1",
                    "candidate_relation": "regression",
                    "exact_rows_delta": -3,
                    "wrong_cells_delta": 15,
                    "holdout_depth_delta": 0,
                    "quotient_comparison": {
                        "schema": "ztare-regression-quotient-comparison-v1",
                        "relation": "same_support_changed_pairs",
                        "candidate_top_quotient": {
                            "bbox": [0, 1, 1, 1],
                            "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                            "first_row": 0,
                            "t": 5,
                            "action": 1,
                            "count": 1,
                        },
                        "best_prior_top_quotient": {
                            "bbox": [0, 1, 1, 1],
                            "pair_counts": [{"predicted": 3, "real": 8, "count": 2}],
                            "first_row": 1,
                            "t": 5,
                            "action": 1,
                            "count": 1,
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        "PATCH_BASE_IMPROVEMENT_PRECHECK: candidate regressed",
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "FRESH COUNTEREXAMPLE CONTEXT" in prompt
    assert "same_support_changed_pairs" in prompt
    assert "support_row_sections" in prompt


def test_worldmodel_no_delta_patch_base_retry_suppresses_patch_dump(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    write_proposal_cards(
        workspace / "strategy_experiments.jsonl",
        [
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "residue-family",
                "rationale": "open repair card",
                "falsifiable_prediction": "next gate must pass",
                "action_plan": {
                    "residue_quotient": {"residue_class": "boundary_update"},
                    "required_next_gate": {
                        "command": "level_transfer_probe",
                        "success_status": "exact_depth",
                    },
                },
                "kill_condition": "gate fails",
                "disposition": "open",
            }
        ],
    )
    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "test_model.py",
                        "sha": "abc123",
                        "visible_exact_rows": 10,
                        "visible_checked_rows": 10,
                        "visible_wrong_cells": 0,
                        "source_excerpt": "def should_not_surface(): pass",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        "PATCH_BASE_IMPROVEMENT_PRECHECK: candidate must strictly improve "
        "the best deterministic near-miss before spending an iteration "
        "(relation=no_strict_improvement). exact_rows 10 vs 10; "
        "wrong_cells 0 vs 0; holdout 0 vs 0; first=; "
        "quotient_relation=unclassified; candidate_top={'bbox': [], "
        "'pair_counts': [], 'first_row': None}; best_prior_top={'bbox': [], "
        "'pair_counts': [], 'first_row': None}",
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "OPEN STRATEGY CARD REFS" in prompt
    assert "optional action_request skeleton" in prompt
    assert "AUTHORITATIVE PATCH BASE SOURCE" not in prompt
    assert "FRESH COUNTEREXAMPLE CONTEXT" not in prompt
    assert "should_not_surface" not in prompt


def test_worldmodel_retry_selected_diagnostic_suppresses_optional_strategy_gate(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    write_proposal_cards(
        workspace / "strategy_experiments.jsonl",
        [
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "residue-family",
                "failure_family_sha": "abc",
                "rationale": "open repair card",
                "falsifiable_prediction": "next gate must pass",
                "action_plan": {
                    "residue_quotient": {"residue_class": "boundary_update"},
                    "required_next_gate": {
                        "command": "level_transfer_probe",
                        "success_status": "exact_depth",
                    },
                },
                "kill_condition": "gate fails",
                "disposition": "open",
            }
        ],
    )
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "recommended_capability_id": "inspect_worldmodel_counterexample_context",
                "workbench_task": {
                    "admissible_capability_ids": [
                        "inspect_worldmodel_counterexample_context"
                    ],
                    "objective": "separate the current quotient",
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        (
            "LEAF_WORKBENCH_RECEIPT_PRECHECK: candidate uses "
            "workbench-backed facts ['replay quotient'] but includes no "
            "LEAF_WORKBENCH_RECEIPT."
        ),
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "OPEN STRATEGY CARD REFS" in prompt
    assert '"capability_id":"inspect_worldmodel_counterexample_context"' in prompt
    assert "optional action_request skeleton" not in prompt
    assert '"capability_id":"run_strategy_required_gate"' not in prompt


def test_worldmodel_patch_base_retry_skips_impure_authoritative_source(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/impure.py",
                        "sha": "impure",
                        "visible_exact_rows": 99,
                        "visible_checked_rows": 100,
                        "visible_wrong_cells": 1,
                        "holdout_depth": 0,
                        "gate_score": 0.6667,
                        "source_excerpt": (
                            "_COUNT = 0\n"
                            "def PATCH_DELTA(base_next, state, action, t):\n"
                            "    global _COUNT\n"
                            "    _COUNT += 1\n"
                            "    return base_next\n"
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        "PATCH_BASE_REGRESSION_PRECHECK: candidate loses the best deterministic near-miss",
        "def step(grid, action, t): return grid",
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "AUTHORITATIVE PATCH BASE SOURCE" not in prompt
    assert "impure" not in prompt


def test_worldmodel_retry_preserves_open_strategy_obligations_on_unrelated_error(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    written = write_proposal_cards(
        workspace / "strategy_experiments.jsonl",
        [
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "residue-family",
                "rationale": "open repair card",
                "falsifiable_prediction": "next gate must pass",
                "action_plan": {
                    "residue_quotient": {"residue_class": "boundary_update"},
                    "required_next_gate": {
                        "command": "level_transfer_probe",
                        "success_status": "exact_depth",
                    },
                    "seed_prerequisite": {"seed_path": "workspace/seed.json"},
                },
                "kill_condition": "gate fails",
                "disposition": "open",
            }
        ],
    )

    prompt = format_r1_retry_skeleton(
        "LEAF_WORKBENCH_CAPABILITY_PROPOSAL missing required fields",
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "OPEN STRATEGY CARD REFS" in prompt
    assert "STRATEGY_CARD_DISCHARGE" in prompt
    assert written[0]["failure_family_sha"] in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt
    assert "run_strategy_required_gate" in prompt
    assert '"command":"level_transfer_probe"' in prompt
    assert "requires_live_actions" not in prompt
    assert "requires_external_actions" not in prompt
    assert '"admissible_no_attempt_blockers":["missing_seed","missing_evidence","verifier_defect","underdetermined_by_current_log"]' in prompt


def test_worldmodel_retry_does_not_teach_hand_authored_workbench_receipts(
    tmp_path: Path,
):
    prompt = format_r1_retry_skeleton(
        "LEAF_WORKBENCH_RECEIPT_PRECHECK: candidate uses workbench-backed facts ['residual quotient'] but includes no LEAF_WORKBENCH_RECEIPT.",
        '{"control_receipts":[],"thesis_markdown":"uses residual quotient","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "LEAF WORKBENCH CONTROL RULES" in prompt
    assert "kernel executor only" in prompt
    assert "Typed receipt example" not in prompt
    assert '"type":"LEAF_WORKBENCH_RECEIPT"' not in prompt
    assert "diagnostics_ref" not in prompt


def test_worldmodel_retry_surfaces_latest_weakness_action_before_any_prior_action(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "recommended_capability_id": "inspect_worldmodel_counterexample_context",
                "recommended_route": "request_counterexample_context_then_factor_delta_by_residual_quotient",
                "workbench_task": {
                    "admissible_capability_ids": ["inspect_worldmodel_counterexample_context"],
                    "objective": "separate the failed quotient before another candidate",
                    "visible_artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        "LEAF_WORKBENCH_RECEIPT_PRECHECK: candidate uses workbench-backed facts ['residual quotient'] but includes no LEAF_WORKBENCH_RECEIPT.",
        '{"control_receipts":[],"thesis_markdown":"uses residual quotient","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "WORKBENCH STATE" in prompt
    assert '"type":"LEAF_WORKBENCH_ACTION_REQUEST"' in prompt
    assert '"capability_id":"inspect_worldmodel_counterexample_context"' in prompt
    assert '"latest_eval_ref":"latest_eval_results.json"' in prompt
    assert "Typed receipt example" not in prompt


def test_worldmodel_retry_observation_request_keeps_candidate_carrier_surface(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "recommended_capability_id": "inspect_worldmodel_counterexample_context",
                "recommended_route": "request_counterexample_context_then_separate_cases",
                "workbench_task": {
                    "admissible_capability_ids": ["inspect_worldmodel_counterexample_context"],
                    "objective": "separate the failed quotient before lowering",
                    "visible_artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        "PATCH_BASE_IMPROVEMENT_PRECHECK: relation=regression; quotient_context_missing",
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert '"capability_id":"inspect_worldmodel_counterexample_context"' in prompt
    assert "Candidate carrier surfaces are suppressed" not in prompt
    assert "If this retry submits a candidate delta, choose the narrowest carrier" in prompt
    assert "AUTHORITATIVE PATCH BASE REFERENCE" not in prompt


def test_worldmodel_retry_consumes_workbench_receipt_without_re_requesting(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    written = write_proposal_cards(
        workspace / "strategy_experiments.jsonl",
        [
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "residue-family",
                "rationale": "open repair card",
                "falsifiable_prediction": "next gate must pass",
                "action_plan": {
                    "residue_quotient": {"residue_class": "boundary_update"},
                    "required_next_gate": {
                        "command": "level_transfer_probe",
                        "success_status": "exact_depth",
                    },
                    "seed_prerequisite": {"seed_path": "workspace/seed.json"},
                },
                "kill_condition": "gate fails",
                "disposition": "open",
            }
        ],
    )
    receipt_error = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested registered "
        "workbench action(s). Free retry with these receipt(s) in typed "
        "`control_receipts`; do not re-request the same action unless the "
        "candidate/evidence changed.\n"
        'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_strategy_required_gate",'
        '"output_summary":"status=bounded_mismatch"}'
    )

    prompt = format_r1_retry_skeleton(
        receipt_error,
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "CARRIED RECEIPT FACTS" in prompt
    assert "Ready-to-use receipt object(s) for `control_receipts`" not in prompt
    assert '"type":"LEAF_WORKBENCH_RECEIPT"' not in prompt
    assert '"capability_id":"run_strategy_required_gate"' in prompt
    assert written[0]["failure_family_sha"] in prompt
    assert "STRATEGY_CARD_DISCHARGE" in prompt
    assert "optional action_request skeleton" not in prompt
    assert "Typed action-request example" not in prompt


def test_worldmodel_retry_routes_chart_only_receipt_to_lowerable_selector_miner(
    tmp_path: Path,
):
    (tmp_path / "workspace").mkdir()
    output_summary = json.dumps(
        {
            "schema": "ztare-worldmodel-separating-feature-miner-v1",
            "candidate_predicates": [],
            "support_scoped_predicates": [
                {"lowering_scope": "quotient_chart_only"}
            ],
        },
        separators=(",", ":"),
    )
    receipt = json.dumps(
        {
            "capability_id": "mine_worldmodel_separating_features",
            "output_summary": output_summary,
        },
        separators=(",", ":"),
    )
    receipt_error = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested registered "
        "workbench action(s). Free retry with these receipt(s) in typed "
        "`control_receipts`; do not re-request the same action unless the "
        "candidate/evidence changed.\n"
        f"LEAF_WORKBENCH_RECEIPT: {receipt}"
    )

    prompt = format_r1_retry_skeleton(
        receipt_error,
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert "copy it into `control_receipts`" not in prompt
    assert '"capability_id":"mine_worldmodel_lowerable_selectors"' in prompt
    assert "no_lowerable_receipt_witness" in prompt
    assert '"admissible_events":["request_typed_observation","submit_candidate_delta","report_tool_gap"]' in prompt


def test_worldmodel_retry_routes_context_only_receipt_to_feature_miner(
    tmp_path: Path,
):
    (tmp_path / "workspace").mkdir()
    receipt = json.dumps(
        {
            "capability_id": "inspect_worldmodel_counterexample_context",
            "output_summary": (
                "relation=changed_support; support_bbox=[61, 51, 62, 63]; "
                "context_delta=local_band_counts:candidate=... best_prior=..."
            ),
        },
        separators=(",", ":"),
    )
    receipt_error = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested registered "
        "workbench action(s). Free retry with these receipt(s) in typed "
        "`control_receipts`; do not re-request the same action unless the "
        "candidate/evidence changed.\n"
        f"LEAF_WORKBENCH_RECEIPT: {receipt}"
    )

    prompt = format_r1_retry_skeleton(
        receipt_error,
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert '"capability_id":"mine_worldmodel_separating_features"' in prompt
    assert "no_lowerable_receipt_witness" in prompt
    assert "Candidate carrier surfaces are suppressed" not in prompt
    assert "A failed carrier refutes that carrier" in prompt


def test_worldmodel_retry_consumes_commuting_transport_before_selector_ladder(
    tmp_path: Path,
):
    (tmp_path / "workspace").mkdir()
    output_summary = json.dumps(
        {
            "schema": "ztare-counterexample-context-observation-v1",
            "diagnostic_summary": "finite square",
            "commuting_transports": [
                {
                    "schema": "ztare-observed-commuting-transport-v1",
                    "authority": "diagnostic_finite_witness",
                    "observed_commutation": True,
                    "operation": {
                        "op": "consume_extremal",
                        "color": 8,
                        "replacement": 3,
                        "axis": "row",
                        "extreme": "max",
                        "count": 2,
                    },
                    "component_identity_status": (
                        "property_witness_only_requires_recurrence_or_object_identity"
                    ),
                    "global_equivariance_authorized": False,
                    "quotient_authorized": False,
                    "carrier_promotion_authorized": False,
                }
            ],
        },
        separators=(",", ":"),
    )
    receipt = json.dumps(
        {
            "capability_id": "inspect_worldmodel_counterexample_context",
            "output_summary": output_summary,
        },
        separators=(",", ":"),
    )
    receipt_error = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested registered "
        "workbench action(s). Free retry with these receipt(s).\n"
        f"LEAF_WORKBENCH_RECEIPT: {receipt}"
    )

    prompt = format_r1_retry_skeleton(
        receipt_error,
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert '"observed_commutation":true' in prompt
    assert "A finite commuting transport through a registered adapter operation" in prompt
    assert '"capability_id":"mine_worldmodel_separating_features"' not in prompt
    assert '"capability_id":"mine_worldmodel_lowerable_selectors"' not in prompt
    assert "grants no global equivariance, quotient, or promotion authority" in prompt


def test_worldmodel_retry_suppresses_stale_probe_but_keeps_other_candidate_families(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "recommended_capability_id": "run_visible_json_probe",
                "workbench_task": {
                    "admissible_capability_ids": ["run_visible_json_probe"],
                    "objective": "stale visible probe from an older boundary",
                    "visible_artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
            }
        ),
        encoding="utf-8",
    )
    output_summary = json.dumps(
        {
            "schema": "ztare-worldmodel-lowerable-selector-miner-v1",
            "admissibility_scope": "candidate_family",
            "candidate_family_id": "same-shaped-window-selector-v1",
            "candidate_family_admissible": False,
            "candidate_predicates": [],
            "lowerability_status": "no_zero_error_selector_found",
            "forbidden_feature_classes": [
                "absolute_row",
                "absolute_time",
                "support_identity",
            ],
        },
        separators=(",", ":"),
    )
    receipt = json.dumps(
        {
            "capability_id": "mine_worldmodel_lowerable_selectors",
            "output_summary": output_summary,
        },
        separators=(",", ":"),
    )
    receipt_error = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested registered "
        "workbench action(s). Free retry with these receipt(s) in typed "
        "`control_receipts`; do not re-request the same action unless the "
        "candidate/evidence changed.\n"
        f"LEAF_WORKBENCH_RECEIPT: {receipt}"
    )

    prompt = format_r1_retry_skeleton(
        receipt_error,
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
    )

    assert '"capability_id":"run_visible_json_probe"' not in prompt
    assert "LOWERABILITY_BLOCKED" in prompt
    assert "Candidate carrier surfaces are suppressed" not in prompt
    assert "A failed carrier refutes that carrier" in prompt
    assert "AUTHORITATIVE PATCH BASE REFERENCE" not in prompt
    assert "choose the narrowest carrier" in prompt
    assert '"admissible_events":["request_typed_observation","submit_candidate_delta","report_tool_gap"]' in prompt


def test_worldmodel_retry_history_suppresses_re_request_after_receipt(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    write_proposal_cards(
        workspace / "strategy_experiments.jsonl",
        [
            {
                "schema": "strategy-experiment-v1",
                "kind": "compressed_counterexample_repair",
                "failure_family": "residue-family",
                "rationale": "open repair card",
                "falsifiable_prediction": "next gate must pass",
                "action_plan": {
                    "residue_quotient": {"residue_class": "boundary_update"},
                    "required_next_gate": {
                        "command": "level_transfer_probe",
                        "success_status": "exact_depth",
                    },
                    "seed_prerequisite": {"seed_path": "workspace/seed.json"},
                },
                "kill_condition": "gate fails",
                "disposition": "open",
            }
        ],
    )

    prompt = format_r1_retry_skeleton(
        "Worldmodel typed payload contract reject: missing executable carrier",
        '{"control_receipts":[],"thesis_markdown":"x"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
        retry_error_history=[
            "PATCH_BASE_IMPROVEMENT_PRECHECK: regression",
            (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s).\n"
                'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_strategy_required_gate"}'
            ),
            "Worldmodel typed payload contract reject: missing executable carrier",
        ],
    )

    assert "copy it into `control_receipts`" not in prompt
    assert "optional action_request skeleton" not in prompt
    assert "Typed action-request example" not in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK" in prompt


def test_worldmodel_retry_allows_candidate_bound_gate_reissue_after_unbound_receipt(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "recommended_capability_id": "run_strategy_required_gate",
                "workbench_task": {
                    "admissible_capability_ids": ["run_strategy_required_gate"],
                    "objective": "bind the boundary gate to the current candidate",
                    "visible_artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        (
            "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK: candidate-bearing "
            "receipt `run_strategy_required_gate` predates content-addressed "
            "candidate binding."
        ),
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
        retry_error_history=[
            (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s).\n"
                'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_strategy_required_gate"}'
            )
        ],
    )

    assert "Ready-to-use receipt object(s) for `control_receipts`" not in prompt
    assert '"capability_id":"run_strategy_required_gate"' in prompt
    assert '"candidate_path":"test_model.py"' in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt


def test_worldmodel_retry_current_candidate_binding_failure_beats_stale_weakness(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "recommended_capability_id": "run_visible_json_probe",
                "workbench_task": {
                    "admissible_capability_ids": ["run_visible_json_probe"],
                    "objective": "stale visible probe from a prior boundary",
                    "visible_artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        (
            "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK: candidate-bearing "
            "receipt `check_worldmodel_carrier_contract` must include the "
            "kernel request with a content-addressed candidate identity. "
            "Re-request the action under the current workbench contract."
        ),
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
        retry_error_history=[
            (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s).\n"
                'LEAF_WORKBENCH_RECEIPT: {"capability_id":"check_worldmodel_carrier_contract"}'
            )
        ],
    )

    assert "WORKBENCH STATE" in prompt
    assert '"capability_id":"check_worldmodel_carrier_contract"' in prompt
    assert '"candidate_path":"test_model.py"' in prompt
    assert '"capability_id":"run_visible_json_probe"' not in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt


def test_worldmodel_retry_allows_distinct_visible_probe_after_prior_receipt(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    prompt = format_r1_retry_skeleton(
        (
            "PATCH_BASE_IMPROVEMENT_PRECHECK: hard gate failed; request "
            "`run_visible_json_probe` over `workspace/latest_patch_base_regression.json`."
        ),
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
        retry_error_history=[
            (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s).\n"
                'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_strategy_required_gate"}'
            )
        ],
    )

    assert "WORKBENCH STATE" in prompt
    assert "copy it into `control_receipts`" not in prompt
    assert '"capability_id":"run_strategy_required_gate"' in prompt
    assert '"capability_id":"run_visible_json_probe"' in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt
    assert "LEAF_WORKBENCH_ACTION_CONTRACT" not in prompt
    assert "workspace/latest_patch_base_regression.json" in prompt
    assert "RESULT = ..." not in prompt
    assert "Typed action-request example" not in prompt


def test_worldmodel_retry_allows_visible_probe_reissue_when_artifact_changed(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    regression_path = workspace / "latest_patch_base_regression.json"
    regression_path.write_text(
        json.dumps({"version": 2, "counterexample_trace": {"first_mismatch": "new"}}),
        encoding="utf-8",
    )
    assert hashlib.sha256(regression_path.read_bytes()).hexdigest() != "oldhash"
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(
            {
                "schema": "ztare-harness-weakness-receipt-v1",
                "recommended_capability_id": "run_visible_json_probe",
                "recommended_route": "inspect_visible_regression_trace_then_refine_or_propose_capability",
                "workbench_task": {
                    "admissible_capability_ids": ["run_visible_json_probe"],
                    "objective": "inspect changed visible counterexample",
                    "visible_artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
            }
        ),
        encoding="utf-8",
    )

    prompt = format_r1_retry_skeleton(
        (
            "PATCH_BASE_IMPROVEMENT_PRECHECK: hard gate failed; request "
            "`run_visible_json_probe` over the visible regression artifact."
        ),
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
        retry_error_history=[
            (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s).\n"
                'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_visible_json_probe",'
                '"input_hashes":{"artifact_hashes":{"workspace/latest_patch_base_regression.json":"oldhash"}},'
                '"claim_bindings":["old visible probe"],"output_summary":"old"}'
            )
        ],
    )

    assert "WORKBENCH STATE" in prompt
    assert "old visible probe" not in prompt
    assert '"capability_id":"run_visible_json_probe"' in prompt
    assert '"artifact_refs":["workspace/latest_patch_base_regression.json"]' in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt


def test_worldmodel_retry_surfaces_counterexample_context_morphism_after_prior_receipt(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    prompt = format_r1_retry_skeleton(
        (
            "PATCH_BASE_IMPROVEMENT_PRECHECK: hard gate failed; request "
            "`inspect_worldmodel_counterexample_context` for the latest regression."
        ),
        '{"control_receipts":[],"thesis_markdown":"x","test_model_py":"def step(grid, action, t): return grid"}',
        rubric_data=_worldmodel_rubric(),
        project_dir=tmp_path,
        retry_error_history=[
            (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s).\n"
                'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_strategy_required_gate"}'
            )
        ],
    )

    assert "WORKBENCH STATE" in prompt
    assert '"capability_id":"inspect_worldmodel_counterexample_context"' in prompt
    assert '"latest_eval_ref":"latest_eval_results.json"' in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt
    assert "LEAF_WORKBENCH_ACTION_CONTRACT" not in prompt


def test_qualitative_contract_inferred_without_explicit_imodel_flag():
    rubric = _qualitative_rubric()

    assert requires_i_model_submission(rubric) is False
    assert submission_contract_kind(rubric) == "assertion_suite"


def test_worldmodel_contract_overrides_explicit_no_imodel_flag():
    rubric = _worldmodel_rubric()

    assert requires_i_model_submission(rubric) is False
    assert submission_contract_kind(rubric) == "worldmodel"


def test_qualitative_contract_inferred_without_rubric_mode():
    rubric = _qualitative_rubric()
    rubric.pop("rubric_mode")

    assert requires_i_model_submission(rubric) is False
    assert submission_contract_kind(rubric) == "assertion_suite"


def test_qualitative_newton_contract_inferred_as_assertion_suite():
    rubric = _qualitative_rubric()
    rubric["rubric_mode"] = "newton"
    rubric.pop("require_i_model_in_submission", None)

    assert requires_i_model_submission(rubric) is False
    assert submission_contract_kind(rubric) == "assertion_suite"


def test_numeric_retry_uses_scientific_contract_names_not_path_labels():
    prompt = format_r1_retry_skeleton(
        "PARAMETRIC_FORM AST/whitelist pre-flight FAILED",
        "```python\nPARAMETER_NAMES = ['a']\ndef I_model(features, params=None): return 0.0\n```",
        rubric_data={"require_i_model_in_submission": True},
    )

    assert "PARAMETRIC MODEL DECLARATION" in prompt
    assert "VARIATIONAL/LAGRANGIAN DECLARATION" in prompt
    assert ("PATH " + "A") not in prompt
    assert ("PATH " + "B") not in prompt


def test_retry_contract_envelope_is_single_across_submission_kinds():
    cases = [
        (_rubric(), "def vector_ledger_terms():\n    return {}"),
        (_qualitative_rubric(), "def test_mechanism_is_bounded():\n    assert True"),
        (_worldmodel_rubric(), '{"control_receipts":[],"thesis_markdown":"x","test_model_py":""}'),
        ({"require_i_model_in_submission": True}, "PARAMETER_NAMES = ['a']\nPARAMETRIC_FORM = 'a*x'"),
    ]

    for rubric, prior in cases:
        prompt = format_r1_retry_skeleton(
            "contract failure",
            prior,
            rubric_data=rubric,
        )
        assert prompt.count("The iteration counter has NOT advanced; this is a free retry.") == 1
        assert prompt.count("Your prior submission was:") + prompt.count("Prior submission summary:") == 1


def test_retry_prompt_carries_same_iteration_strike_history():
    prompt = format_r1_retry_skeleton(
        "PARAMETRIC_FORM calls helper function",
        "```python\nPARAMETRIC_FORM = '_helper(features)'\n```",
        rubric_data={"require_i_model_in_submission": True},
        retry_error_history=[
            "PARAMETER_NAMES placed inside __main__",
            "PARAMETRIC_FORM calls helper function",
        ],
    )

    assert "Same-iteration R1 strike history" in prompt
    assert "PARAMETER_NAMES placed inside __main__" in prompt
    assert "PARAMETRIC_FORM calls helper function" in prompt
    assert "without reintroducing" in prompt


def test_retry_history_is_available_for_qualitative_contracts():
    prompt = format_r1_retry_skeleton(
        "module-level execution detected",
        "```python\nprint('debug')\n```",
        rubric_data=_qualitative_rubric(),
        retry_error_history=[
            "imported project feature table",
            "module-level execution detected",
        ],
    )

    assert "Same-iteration R1 strike history" in prompt
    assert "imported project feature table" in prompt
    assert "module-level execution detected" in prompt


def test_retry_history_is_available_for_theorem_packet_contracts():
    prompt = format_r1_retry_skeleton(
        "missing top-level theorem function",
        "```python\ndef vector_ledger_terms(): return {}\n```",
        rubric_data=_rubric(),
        retry_error_history=[
            "non-stdlib import at module scope",
            "missing top-level theorem function",
        ],
    )

    assert "Same-iteration R1 strike history" in prompt
    assert "non-stdlib import at module scope" in prompt
    assert "missing top-level theorem function" in prompt
    assert "Do not switch to the generic numeric-declaration template" in prompt


def test_submission_contract_detection_uses_named_contract_ids():
    assert detect_submission_contract("PARAMETER_NAMES=[]\nPARAMETRIC_FORM='x'")["contract"] == "parametric_model"
    assert detect_submission_contract("PARAMETER_NAMES=[]\nLAGRANGIAN='q**2'\nPREDICTION='q'")["contract"] == "variational_lagrangian"
    assert detect_submission_contract("MODEL_PARAMS={'a': 1.0}")["contract"] == "fixed_parameter_model"


def test_theorem_packet_contract_rules_do_not_emit_scalar_fit_grammar(tmp_path: Path):
    ctx = BriefingContext(
        project_dir=tmp_path,
        iter_index=1,
        rubric=_rubric(),
    )

    fragment = ContractRulesProvider().fragment(ctx)

    assert "theorem-packet substrate" in fragment
    assert "def vector_ledger_terms()" in fragment
    assert "I_model: optional compatibility scaffold only" in fragment
    assert "PARAMETRIC_FORM grammar" not in fragment


def test_contract_rules_do_not_default_unspecified_rubric_to_newton(tmp_path: Path):
    rubric = {"require_i_model_in_submission": True}
    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "Mode: newton" not in iter1
    assert "secondary observable + falsifying observation required" not in iter1
    assert "Mode: legacy_unspecified" in recap
    assert "secondary observable + falsifying observation required" not in recap


def test_contract_rules_infer_qualitative_assertion_contract(tmp_path: Path):
    rubric = _qualitative_rubric()
    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "REQUIRED:    none (qualitative substrate)" in iter1
    assert "BANNED:      DO NOT define or call I_model()" in iter1
    assert "PARAMETRIC_FORM grammar" not in iter1
    assert "suite_shape" in recap
    assert "PARAMETRIC_FORM grammar" not in recap


def test_contract_rules_surface_worldmodel_carrier_contract(tmp_path: Path):
    rubric = _worldmodel_rubric()
    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "CONTRACT:    executable world model" in iter1
    assert "WORLD_MODEL_SPEC" in iter1
    assert "PROGRAM" in iter1
    assert "step(grid, action, t)" in iter1
    assert "REQUIRED:    none (qualitative substrate)" not in iter1
    assert "contract_class     : worldmodel" in recap
    assert "plain Python assertions" not in recap


def test_contract_rules_hydrate_worldmodel_contract_from_project_rubric():
    project = Path("projects/arc3_ls20_gov")
    sparse_ui_rubric = {"briefing_attention_agenda": True}

    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=project, iter_index=1003, rubric=sparse_ui_rubric)
    )

    assert "contract_class     : worldmodel" in recap
    assert "WORLD_MODEL_SPEC" in recap
    assert "step(grid, action, t)" in recap
    assert "required_signature : def I_model" not in recap


def test_contract_rules_surface_newton_obligations_only_when_declared(tmp_path: Path):
    rubric = {
        "rubric_mode": "newton",
        "require_i_model_in_submission": True,
    }

    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "### Mode: newton" in iter1
    assert "secondary observable" in iter1
    assert "Mode: newton" in recap
    assert "secondary observable + falsifying observation required" in recap


def test_trackb_rubric_disables_scalar_imodel_requirement():
    rubric = json.loads(Path("rubrics/ns_proofsearch_leray_convexity_trackb.json").read_text())

    assert rubric["require_i_model_in_submission"] is False
    assert rubric["theorem_packet_contract"]["required_top_level_functions"]
