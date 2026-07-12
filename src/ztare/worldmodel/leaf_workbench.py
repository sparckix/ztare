from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.leaf_workbench_contract import (
    LeafWorkbenchCapability,
    LeafWorkbenchContract,
    leaf_workbench_action_request_object,
    render_leaf_workbench_mutator_surface,
    render_leaf_workbench_capability_proposal_shape,
    render_leaf_workbench_control_rules,
    render_leaf_workbench_contract_prompt,
    validate_leaf_workbench_registry_parity,
)
from ztare.common.science_output_policy import (
    INVESTIGATED_STAGNATION_K as SCIENCE_INVESTIGATED_STAGNATION_K,
)
from ztare.worldmodel.patch_carrier_contract import patch_carrier_brief_line


WORLD_MODEL_LEAF_WORKBENCH_CONTRACT = LeafWorkbenchContract(
    capabilities=(
        LeafWorkbenchCapability(
            capability_id="run_visible_json_probe",
            purpose=(
                "Run bounded pure Python over explicitly named visible JSON "
                "artifacts; the program receives ARTIFACTS and must assign "
                "JSON-serializable RESULT."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["probe_py", "artifact_refs"],
            output_contract=["result_summary", "artifact_hashes", "probe_sha256"],
        ),
        LeafWorkbenchCapability(
            capability_id="check_receipt_compatibility",
            purpose=(
                "Check visible receipt or typed-payload shape before final "
                "submission; reports missing fields and repair hints without "
                "running replay, holdout, terminal, or promotion gates."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["source_ref_or_stdin", "receipt_kind"],
            output_contract=["errors", "repair_hints", "normalized_summary"],
        ),
        LeafWorkbenchCapability(
            capability_id="inspect_worldmodel_patch_base",
            purpose=(
                "Read the current authoritative patch base or candidate-memory "
                "near-miss that a repair must preserve."
            ),
            authority="reader",
            secret_policy="public_only",
            input_contract=["patch_base_ref", "patch_base_sha"],
            output_contract=["carrier_ref_or_excerpt", "score_tuple", "first_mismatch"],
        ),
        LeafWorkbenchCapability(
            capability_id="inspect_replay_residual_quotient",
            purpose=(
                "Read persisted replay diagnostics and name the current mismatch "
                "quotient targeted by a repair."
            ),
            authority="reader",
            secret_policy="derived_no_raw_secret",
            input_contract=["diagnostics_ref", "diagnostics_sha"],
            output_contract=["class_count", "bbox_or_support", "pair_counts", "representative_row"],
        ),
        LeafWorkbenchCapability(
            capability_id="run_worldmodel_replay_probe",
            purpose=(
                "Run or consume a frozen replay/holdout diagnostic over visible "
                "evidence without spending live environment actions."
            ),
            authority="pure_diagnostic",
            secret_policy="sealed_aggregate_only",
            input_contract=["candidate_ref", "incumbent_ref", "gate_harness_ref"],
            output_contract=["visible_exact_rows", "holdout_depth", "wrong_cells", "first_mismatch"],
        ),
        LeafWorkbenchCapability(
            capability_id="run_strategy_required_gate",
            purpose=(
                "Run the bounded gate command declared by an open Strategy "
                "card through the registered substrate capability adapter."
            ),
            authority="bounded_world_probe",
            secret_policy="sealed_aggregate_only",
            input_contract=["failure_family_sha", "command", "candidate_path", "gate_params"],
            output_contract=["command", "status", "receipt_ref", "receipt_sha256", "output_summary"],
        ),
        LeafWorkbenchCapability(
            capability_id="run_structural_isomorphism",
            purpose=(
                "Run or retrieve a typed research-isomorphism/deanchoring "
                "receipt for a declared operator-neutral seam."
            ),
            authority="proposal_only",
            secret_policy="public_only",
            input_contract=[
                "mode",
                "failure_state_or_left_state",
                "right_state_for_conjecture",
                "model",
                "allow_live_query",
            ],
            output_contract=[
                "receipt_ref",
                "receipt_sha256",
                "candidate_count",
                "prescription_or_prediction_cards",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="validate_worldmodel_strategy_receipts",
            purpose=(
                "Check Strategy Office card receipts against exact current "
                "failure_family_sha values."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["strategy_ledger_ref", "candidate_receipts_ref"],
            output_contract=["matched_shas", "missing_shas", "malformed_receipts"],
        ),
        LeafWorkbenchCapability(
            capability_id="score_worldmodel_candidate_delta",
            purpose=(
                "Compare a candidate against the best cached worldmodel near-miss "
                "on the verifier tuple before spending judge tokens."
            ),
            authority="scorer",
            secret_policy="sealed_aggregate_only",
            input_contract=["candidate_ref", "patch_base_ref", "latest_eval_ref"],
            output_contract=["exact_rows_delta", "wrong_cells_delta", "holdout_depth_delta", "regressions"],
        ),
        LeafWorkbenchCapability(
            capability_id="check_worldmodel_carrier_contract",
            purpose=(
                "Check a candidate carrier for pure transition behavior and "
                "replay-index admissibility before replay scoring."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["candidate_ref_or_source"],
            output_contract=["status", "source_sha256", "contract_error"],
        ),
        LeafWorkbenchCapability(
            capability_id="inspect_worldmodel_counterexample_context",
            purpose=(
                "Compare representative regression counterexamples and surface "
                "state-context features that separate candidate and prior quotients."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["latest_eval_ref", "episode_log_ref", "quotient_comparison_ref"],
            output_contract=["relation", "representative_rows", "support_bbox", "context_feature_delta"],
        ),
        LeafWorkbenchCapability(
            capability_id="mine_worldmodel_separating_features",
            purpose=(
                "Mine simple visible alpha-refinement predicates that separate "
                "a counterexample support transition from non-transition cases "
                "over the frozen episode log."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["latest_regression_ref", "episode_log_ref", "feature_budget"],
            output_contract=[
                "support_bbox",
                "target_label_counts",
                "candidate_predicates",
                "support_scoped_predicates",
                "lowerability_note",
                "confusion_matrix",
                "diagnostic_only_fields",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="mine_worldmodel_lowerable_selectors",
            purpose=(
                "Mine observable local-window/action predicates that lower a "
                "counterexample support chart into executable carrier selectors "
                "without row, time, support identity, quotient labels, or hidden fields."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["latest_regression_ref", "episode_log_ref", "feature_budget"],
            output_contract=[
                "window_shape",
                "source_window_values",
                "target_window_values",
                "lowerability_status",
                "candidate_predicates",
                "near_miss_predicates",
                "confusion_matrix",
                "executable_delta_hint",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="mine_worldmodel_global_carrier_selectors_from_observable_context",
            purpose=(
                "Mine carrier-visible selectors from Strategy-gate before/"
                "predicted/observed local-patch witnesses, excluding absolute "
                "row/time/support identity."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["strategy_gate_receipt_ref", "episode_log_ref", "feature_budget"],
            output_contract=[
                "lowerability_status",
                "candidate_delta_admissible",
                "candidate_predicates",
                "near_miss_predicates",
                "missing_fields",
                "forbidden_feature_classes",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="cell_local_lowerable_carrier_selector_miner",
            purpose=(
                "Refine Strategy-gate local-patch witnesses with per-cell "
                "component topology features, then report only selectors "
                "lowerable to carrier-visible state/base_next scans."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=[
                "strategy_gate_receipt_ref",
                "prior_miner_receipt_ref",
                "feature_budget",
            ],
            output_contract=[
                "lowerability_status",
                "candidate_delta_admissible",
                "candidate_predicates",
                "near_miss_predicates",
                "candidate_label_coverage",
                "forbidden_feature_classes",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="join_lowerable_selectors",
            purpose=(
                "Compose two partial selector receipts by partial-function coproduct "
                "over disjoint domains; report a conflict-bound inadmissible receipt "
                "when the same key is assigned incompatible values."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=[
                "selector_a_ref",
                "selector_b_ref",
            ],
            output_contract=[
                "join_status",
                "candidate_delta_admissible",
                "joined_predicates",
                "conflicting_keys",
                "inadmissibility_reason",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="inspect_worldmodel_event_timeline",
            purpose=(
                "Group cell-change events across time within one episode log "
                "using a declarative cell predicate; reports per-step matching "
                "cells, counts by step, distinct cells, and a rate series."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["episode_ref", "cell_predicate_spec"],
            output_contract=["events", "counts_by_t", "distinct_cells", "rate_series"],
        ),
        LeafWorkbenchCapability(
            capability_id="contrast_worldmodel_episodes",
            purpose=(
                "Contrast two episodes' states at a matching step: per-state "
                "value censuses, census delta, differing row indices, shapes."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["episode_ref_a", "episode_ref_b", "at_t"],
            output_contract=[
                "color_census_a",
                "color_census_b",
                "census_delta",
                "rows_differing",
                "shape_a",
                "shape_b",
            ],
        ),
        LeafWorkbenchCapability(
            capability_id="run_worldmodel_evidence_probe",
            purpose=(
                "Execute self-contained `def probe(episodes) -> dict` observation "
                "code in a kernel sandbox over the typed episode evidence "
                "(visible + holdout transition dicts) and return the receipt. "
                "Zero-credit: executing a probe never completes a science turn — "
                "an observation neither survives nor is killed."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["probe_source"],
            output_contract=["probe_sha", "status", "payload"],
        ),
    )
)

WORLD_MODEL_LEAF_WORKBENCH_FACT_MARKERS = (
    "residual quotient",
    "replay quotient",
    "latest_replay_diagnostics",
    "inspect_worldmodel_",
    "score_worldmodel_",
)

WORLD_MODEL_LEAF_WORKBENCH_SOURCE_FIBERS = (
    (
        "src/ztare/worldmodel/leaf_workbench.py",
        "worldmodel workbench lowering and action handlers",
    ),
    (
        "src/ztare/common/leaf_workbench_contract.py",
        "substrate-general workbench receipt/proposal validator",
    ),
    (
        "src/ztare/common/projection_owner_registry.py",
        "machine-readable owner/projection/test blast-radius map for meta-hardening",
    ),
    (
        "src/ztare/orchestrator/submission_path_helpers.py",
        "R1 retry prompt projection for typed payload repair",
    ),
    (
        "src/ztare/validator/worldmodel_typed_payload.py",
        "worldmodel JSON payload compiler and control receipt renderer",
    ),
    (
        "src/ztare/common/leaf_workbench_python.py",
        "bounded visible JSON probe runtime",
    ),
    (
        "src/ztare/common/visible_workbench_cli.py",
        "same-turn visible workbench CLI for bounded local probes",
    ),
    (
        "src/ztare/common/worldmodel_carrier_purity.py",
        "carrier purity and temporal admissibility contract",
    ),
    (
        "src/ztare/common/harness_weakness.py",
        "weakness classification and workbench task routing",
    ),
    (
        "src/ztare/validator/core/repair_preflight.py",
        "retry-time workbench execution and repair preflight",
    ),
    (
        "src/ztare/common/dispatch_model.py",
        "visible workbench staging and agent execution boundary",
    ),
    (
        "src/ztare/common/tool_synthesis_contract.py",
        "mutable-sensor versus immutable-axiom boundary classifier",
    ),
)


def render_worldmodel_leaf_workbench_prompt() -> str:
    return render_leaf_workbench_contract_prompt(WORLD_MODEL_LEAF_WORKBENCH_CONTRACT)


def worldmodel_leaf_workbench_action_environment() -> dict[str, Any]:
    """Return the substrate adapter for generic leaf-workbench action dispatch."""
    return {
        "contract": WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
        "records_fn": worldmodel_leaf_workbench_records,
        "local_cli_actions": {
            "inspect_worldmodel_counterexample_context",
            "inspect_worldmodel_event_timeline",
            "contrast_worldmodel_episodes",
            "run_worldmodel_evidence_probe",
            "mine_worldmodel_separating_features",
            "mine_worldmodel_lowerable_selectors",
            "mine_worldmodel_global_carrier_selectors_from_observable_context",
            "cell_local_lowerable_carrier_selector_miner",
            "join_lowerable_selectors",
            "score_worldmodel_candidate_delta",
        },
        "record_only_capabilities": {
            "inspect_worldmodel_patch_base",
            "inspect_replay_residual_quotient",
            "run_worldmodel_replay_probe",
            "validate_worldmodel_strategy_receipts",
        },
        "candidate_bound_actions": {
            "check_worldmodel_carrier_contract",
            "run_strategy_required_gate",
            "score_worldmodel_candidate_delta",
        },
        "action_handlers": {
            "run_visible_json_probe": _handle_visible_json_probe_action,
            "inspect_worldmodel_counterexample_context": _handle_counterexample_context_action,
            "inspect_worldmodel_event_timeline": _handle_event_timeline_action,
            "contrast_worldmodel_episodes": _handle_episode_contrast_action,
            "run_worldmodel_evidence_probe": _handle_evidence_probe_action,
            "run_structural_isomorphism": _handle_structural_isomorphism_action,
            "run_strategy_required_gate": _handle_strategy_required_gate_action,
            "score_worldmodel_candidate_delta": _handle_score_worldmodel_candidate_delta_action,
            "check_worldmodel_carrier_contract": _handle_worldmodel_carrier_contract_action,
            "mine_worldmodel_separating_features": _handle_separating_features_action,
            "mine_worldmodel_lowerable_selectors": _handle_lowerable_selector_action,
            "mine_worldmodel_global_carrier_selectors_from_observable_context": (
                _handle_global_carrier_selector_action
            ),
            "cell_local_lowerable_carrier_selector_miner": (
                _handle_cell_local_carrier_selector_action
            ),
            "join_lowerable_selectors": _handle_join_lowerable_selectors_action,
        },
        "stateless_actions": {
            "run_visible_json_probe",
            "inspect_worldmodel_event_timeline",
            "contrast_worldmodel_episodes",
            "run_worldmodel_evidence_probe",
            "run_strategy_required_gate",
            "run_structural_isomorphism",
            "score_worldmodel_candidate_delta",
            "check_worldmodel_carrier_contract",
            "mine_worldmodel_separating_features",
            "mine_worldmodel_lowerable_selectors",
            "mine_worldmodel_global_carrier_selectors_from_observable_context",
            "cell_local_lowerable_carrier_selector_miner",
            "join_lowerable_selectors",
        },
    }


def validate_worldmodel_leaf_workbench_registry() -> None:
    from ztare.common.visible_workbench_actions import (
        visible_workbench_local_action_ids,
        visible_workbench_local_adapter_action_ids,
    )

    env = worldmodel_leaf_workbench_action_environment()
    parity = validate_leaf_workbench_registry_parity(
        contract=env["contract"],
        action_handlers=env.get("action_handlers") or {},
        local_action_ids=visible_workbench_local_action_ids()
        | visible_workbench_local_adapter_action_ids(),
        record_only_capability_ids=env.get("record_only_capabilities") or (),
        stateless_action_ids=env.get("stateless_actions") or (),
    )
    parity.raise_for_errors()


def worldmodel_workbench_input_refs_for_capability(
    capability_id: str,
    artifact_refs: list[str] | tuple[str, ...] = (),
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return adapter-owned default input refs for a registered capability."""

    refs = [str(ref) for ref in artifact_refs if str(ref).strip()]
    episode_ref = _default_episode_log_ref(project_dir)
    if capability_id == "inspect_worldmodel_counterexample_context":
        return {
            "latest_eval_ref": "latest_eval_results.json",
            "quotient_comparison_ref": "latest_eval_results.json:candidate_regression_receipt",
            "episode_log_ref": episode_ref,
        }
    if capability_id == "run_visible_json_probe":
        return {
            "artifact_refs": refs or ["workspace/latest_patch_base_regression.json"],
        }
    if capability_id in {
        "mine_worldmodel_separating_features",
        "mine_worldmodel_lowerable_selectors",
    }:
        return {
            "latest_regression_ref": (
                refs[0] if refs else "workspace/latest_patch_base_regression.json"
            ),
            "episode_log_ref": episode_ref,
        }
    if capability_id == "mine_worldmodel_global_carrier_selectors_from_observable_context":
        return {
            "strategy_gate_receipt_ref": (
                refs[0] if refs else "workspace/latest_level_transfer_probe.json"
            ),
        }
    if capability_id == "cell_local_lowerable_carrier_selector_miner":
        return {
            "strategy_gate_receipt_ref": (
                refs[0] if refs else "workspace/latest_level_transfer_probe.json"
            ),
        }
    if capability_id == "inspect_worldmodel_event_timeline":
        return {
            "episode_ref": refs[0] if refs else "visible",
            "cell_predicate_spec": {"changed": True},
        }
    if capability_id == "contrast_worldmodel_episodes":
        return {
            "episode_ref_a": refs[0] if len(refs) > 0 else "visible",
            "episode_ref_b": refs[1] if len(refs) > 1 else "holdout",
        }
    if capability_id == "inspect_replay_residual_quotient":
        return {
            "diagnostics_ref": "workspace/latest_replay_diagnostics_after_abduce.json",
        }
    if capability_id == "run_strategy_required_gate":
        return {
            "task_ref": "workspace/latest_harness_weakness.json:workbench_task",
            "candidate_path": "test_model.py",
        }
    if capability_id in {
        "check_worldmodel_carrier_contract",
        "score_worldmodel_candidate_delta",
    }:
        return {
            "candidate_path": "test_model.py",
        }
    return {
        "task_ref": "workspace/latest_harness_weakness.json:workbench_task",
    }


def _default_episode_log_ref(project_dir: str | Path | None = None) -> str:
    if project_dir is None:
        return "raw/episodes/episode_001.jsonl"
    episodes = Path(project_dir) / "raw" / "episodes"
    try:
        hits = sorted(episodes.glob("episode_*.jsonl"))
    except Exception:
        hits = []
    if hits:
        return f"raw/episodes/{hits[-1].name}"
    return "raw/episodes/episode_001.jsonl"


def _handle_visible_json_probe_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.common.leaf_workbench_python import run_visible_json_probe

    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    artifact_refs = [str(ref) for ref in (input_refs.get("artifact_refs") or []) if str(ref)]
    if not artifact_refs:
        for key, value in input_refs.items():
            if str(key).endswith("_ref") and isinstance(value, str) and value.startswith("workspace/"):
                artifact_refs.append(value)
    probe_error = ""
    try:
        probe_result = run_visible_json_probe(
            project_dir=project_dir,
            artifact_refs=artifact_refs,
            probe_py=str(input_refs.get("probe_py") or ""),
        )
    except Exception as exc:  # noqa: BLE001
        if not str(input_refs.get("probe_py") or "").strip():
            raise
        probe_error = f"{type(exc).__name__}: {exc}"
        probe_result = run_visible_json_probe(
            project_dir=project_dir,
            artifact_refs=artifact_refs,
            probe_py="",
        )
    return {
        "input_hashes": {
            "artifact_hashes": probe_result.get("artifact_hashes") or {},
            "probe_sha256": probe_result.get("probe_sha256") or "",
        },
        "output_summary": (
            f"probe_error={probe_error}; fallback_default_summary="
            f"{probe_result.get('result_summary')}"
            if probe_error
            else str(probe_result.get("result_summary") or "")
        ),
    }


def _handle_counterexample_context_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    regression_ref = _regression_ref_from_input_refs(project, input_refs)
    return {
        "input_hashes": {
            "source_ref": f"{regression_ref}:candidate_regression_receipt",
            "latest_regression_ref": regression_ref,
            "latest_regression_sha256": _shaish(project / regression_ref),
            "request": _short_receipt_json(req),
        },
        "output_summary": run_worldmodel_counterexample_context_probe(
            project_dir,
            regression_ref=regression_ref,
        ),
    }


def _handle_event_timeline_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.evidence_quotients import (
        cap_events,
        event_timeline,
        resolve_episode_ref,
    )

    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    episode_ref = str(input_refs.get("episode_ref") or "visible")
    spec = input_refs.get("cell_predicate_spec")
    if isinstance(spec, str) and spec.strip():
        spec = json.loads(spec)
    if spec is None:
        spec = {"changed": True}
    path = resolve_episode_ref(project, episode_ref)
    payload = cap_events(
        event_timeline(EpisodeLog.read_jsonl(path), cell_predicate_spec=spec)
    )
    return {
        "input_hashes": {
            "episode_ref": _rel(project, path),
            "episode_sha256": _shaish(path),
            "request": _short_receipt_json(req),
        },
        "output_summary": json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ),
    }


def _handle_episode_contrast_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.evidence_quotients import episode_contrast, resolve_episode_ref

    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    path_a = resolve_episode_ref(project, str(input_refs.get("episode_ref_a") or "visible"))
    path_b = resolve_episode_ref(project, str(input_refs.get("episode_ref_b") or "holdout"))
    at_t = input_refs.get("at_t")
    at_t = None if at_t in (None, "") else int(at_t)
    payload = episode_contrast(
        EpisodeLog.read_jsonl(path_a),
        EpisodeLog.read_jsonl(path_b),
        at_t=at_t,
    )
    return {
        "input_hashes": {
            "episode_ref_a": _rel(project, path_a),
            "episode_a_sha256": _shaish(path_a),
            "episode_ref_b": _rel(project, path_b),
            "episode_b_sha256": _shaish(path_b),
            "request": _short_receipt_json(req),
        },
        "output_summary": json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ),
    }


def _handle_evidence_probe_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.worldmodel.evidence_probe import run_evidence_probe

    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    receipt = run_evidence_probe(project_dir, str(input_refs.get("probe_source") or ""))
    return {
        "input_hashes": {
            "probe_sha": str(receipt.get("probe_sha") or ""),
            "request": _short_receipt_json(req),
        },
        "output_summary": json.dumps(
            receipt, sort_keys=True, separators=(",", ":"), default=str
        ),
    }


def _handle_separating_features_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    regression_ref = _regression_ref_from_input_refs(project, input_refs)
    episode_ref = str(input_refs.get("episode_log_ref") or _default_episode_log_ref(project))
    summary = run_worldmodel_separating_feature_miner(
        project,
        regression_ref=regression_ref,
        episode_ref=episode_ref,
    )
    return {
        "input_hashes": {
            "latest_regression_ref": regression_ref,
            "latest_regression_sha256": _shaish(project / regression_ref),
            "episode_log_ref": episode_ref,
            "episode_log_sha256": _shaish(project / episode_ref),
            "request": _short_receipt_json(req),
        },
        "output_summary": summary,
    }


def _handle_lowerable_selector_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    regression_ref = _regression_ref_from_input_refs(project, input_refs)
    episode_ref = str(input_refs.get("episode_log_ref") or _default_episode_log_ref(project))
    summary = run_worldmodel_lowerable_selector_miner(
        project,
        regression_ref=regression_ref,
        episode_ref=episode_ref,
    )
    return {
        "input_hashes": {
            "latest_regression_ref": regression_ref,
            "latest_regression_sha256": _shaish(project / regression_ref),
            "episode_log_ref": episode_ref,
            "episode_log_sha256": _shaish(project / episode_ref),
            "request": _short_receipt_json(req),
        },
        "output_summary": summary,
    }


def _handle_global_carrier_selector_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    transfer_ref = str(
        input_refs.get("strategy_gate_receipt_ref")
        or input_refs.get("transfer_receipt_ref")
        or input_refs.get("latest_level_transfer_ref")
        or "workspace/latest_level_transfer_probe.json"
    )
    summary = run_worldmodel_global_carrier_selector_miner(
        project,
        transfer_ref=transfer_ref,
    )
    return {
        "input_hashes": {
            "strategy_gate_receipt_ref": transfer_ref,
            "strategy_gate_receipt_sha256": _shaish(project / transfer_ref),
            "request": _short_receipt_json(req),
        },
        "output_summary": summary,
    }


def _handle_cell_local_carrier_selector_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    transfer_ref = str(
        input_refs.get("strategy_gate_receipt_ref")
        or input_refs.get("transfer_receipt_ref")
        or input_refs.get("latest_level_transfer_ref")
        or "workspace/latest_level_transfer_probe.json"
    )
    prior_ref = str(input_refs.get("prior_miner_receipt_ref") or "")
    summary = run_worldmodel_cell_local_carrier_selector_miner(
        project,
        transfer_ref=transfer_ref,
    )
    input_hashes = {
        "strategy_gate_receipt_ref": transfer_ref,
        "strategy_gate_receipt_sha256": _shaish(project / transfer_ref),
        "request": _short_receipt_json(req),
    }
    if prior_ref:
        input_hashes["prior_miner_receipt_ref"] = prior_ref
        input_hashes["prior_miner_receipt_sha256"] = _shaish(project / prior_ref)
    return {
        "input_hashes": input_hashes,
        "output_summary": summary,
    }


def _handle_join_lowerable_selectors_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    selector_a_ref = str(input_refs.get("selector_a_ref") or input_refs.get("left_ref") or "").strip()
    selector_b_ref = str(input_refs.get("selector_b_ref") or input_refs.get("right_ref") or "").strip()
    if not selector_a_ref or not selector_b_ref:
        raise ValueError("join_lowerable_selectors requires selector_a_ref and selector_b_ref")
    summary = join_lowerable_selectors(
        project,
        selector_a_ref=selector_a_ref,
        selector_b_ref=selector_b_ref,
    )
    return {
        "input_hashes": {
            "selector_a_ref": selector_a_ref,
            "selector_a_sha256": _shaish(project / selector_a_ref),
            "selector_b_ref": selector_b_ref,
            "selector_b_sha256": _shaish(project / selector_b_ref),
            "request": _short_receipt_json(req),
        },
        "output_summary": summary,
    }


def _handle_structural_isomorphism_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.common.leaf_workbench_isomorphism import run_structural_isomorphism_action

    iso_result = run_structural_isomorphism_action(
        project_dir,
        req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {},
    )
    return {
        "input_hashes": {
            "receipt_ref": iso_result.get("receipt_ref") or "",
            "receipt_sha256": iso_result.get("receipt_sha256") or "",
            "input_fingerprint": iso_result.get("input_fingerprint") or "",
            "request": _short_receipt_json(req),
        },
        "output_ref": iso_result.get("receipt_ref") or "",
        "output_summary": _structural_isomorphism_receipt_summary(iso_result),
    }


def _handle_strategy_required_gate_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.worldmodel.strategy_gate_actions import run_strategy_required_gate_action

    probe_result = run_strategy_required_gate_action(
        project_dir,
        req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {},
    )
    return {
        "input_hashes": {
            "receipt_ref": probe_result.get("receipt_ref") or "",
            "receipt_sha256": probe_result.get("receipt_sha256") or "",
            "request": _short_receipt_json(req),
        },
        "output_ref": probe_result.get("receipt_ref") or "",
        "output_summary": _strategy_gate_receipt_summary(probe_result),
    }


def _handle_score_worldmodel_candidate_delta_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.validator.core.pre_judge_gate import detect_patch_base_regression_preflight

    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    candidate_ref = str(
        input_refs.get("candidate_path")
        or input_refs.get("candidate_ref")
        or input_refs.get("source_ref")
        or ""
    ).strip()
    candidate_source = str(input_refs.get("candidate_source") or "")
    if candidate_source.strip():
        digest = hashlib.sha256(candidate_source.strip().encode("utf-8")).hexdigest()
        rel = Path("workspace") / "leaf_workbench_action_candidates" / f"{digest}.py"
        candidate_path = (project / rel).resolve()
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(candidate_source.strip(), encoding="utf-8")
        candidate_ref = str(rel)
    else:
        if not candidate_ref:
            raise ValueError("score_worldmodel_candidate_delta requires candidate_path or candidate_source")
        candidate_path = (project / candidate_ref).resolve()
        try:
            candidate_path.relative_to(project.resolve())
        except ValueError as exc:
            raise ValueError(f"candidate_ref escapes project: {candidate_ref}") from exc
        if not candidate_path.is_file():
            raise ValueError(f"candidate_ref does not exist: {candidate_ref}")

    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project,
        candidate_path=candidate_path,
    )
    candidate_sha = _shaish(candidate_path)
    if result is None:
        summary = {
            "schema": "ztare-worldmodel-candidate-delta-score-v1",
            "status": "candidate_preflight_unavailable",
            "candidate_relation": "verifier_unavailable",
            "candidate_delta_admissible": False,
            "promotion_authority": "replay_holdout_gate_only",
        }
        return {
            "input_hashes": {
                "candidate_ref": _rel(project, candidate_path),
                "candidate_sha256": candidate_sha,
                "gate_harness_ref": "gate_harness.py",
                "gate_harness_sha256": _shaish(project / "gate_harness.py"),
                "request": _short_receipt_json(req),
            },
            "output_summary": json.dumps(summary, sort_keys=True, separators=(",", ":"), default=str),
        }

    receipt = result.regression_receipt
    trace = result.counterexample_trace
    payload = {
        "schema": "ztare-worldmodel-candidate-delta-score-v1",
        "status": "candidate_preflight_failed",
        "candidate_relation": receipt.get("candidate_relation"),
        "candidate_exact_rows": receipt.get("candidate_exact_rows"),
        "candidate_wrong_cells": receipt.get("candidate_wrong_cells"),
        "candidate_holdout_depth": receipt.get("candidate_holdout_depth"),
        "best_prior_exact_rows": receipt.get("best_prior_exact_rows"),
        "best_prior_wrong_cells": receipt.get("best_prior_wrong_cells"),
        "best_prior_holdout_depth": receipt.get("best_prior_holdout_depth"),
        "exact_rows_delta": receipt.get("exact_rows_delta"),
        "wrong_cells_delta": receipt.get("wrong_cells_delta"),
        "holdout_depth_delta": receipt.get("holdout_depth_delta"),
        "failed_gates": result.failed_gates,
        "first_mismatch": trace.get("first_mismatch") if isinstance(trace, dict) else "",
        "holdout_witness": (
            trace.get("holdout_witness") if isinstance(trace, dict) and isinstance(trace.get("holdout_witness"), dict) else {}
        ),
        "quotient_relation": (
            receipt.get("quotient_comparison", {}).get("relation")
            if isinstance(receipt.get("quotient_comparison"), dict)
            else ""
        ),
        "candidate_delta_admissible": False,
        "promotion_authority": "replay_holdout_gate_only",
    }
    return {
        "input_hashes": {
            "candidate_ref": _rel(project, candidate_path),
            "candidate_sha256": candidate_sha,
            "gate_harness_ref": "gate_harness.py",
            "gate_harness_sha256": _shaish(project / "gate_harness.py"),
            "request": _short_receipt_json(req),
        },
        "output_summary": json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str),
    }


def _handle_worldmodel_carrier_contract_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
    from ztare.common.worldmodel_carrier_purity import carrier_contract_error

    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    candidate_ref = str(
        input_refs.get("candidate_path")
        or input_refs.get("candidate_ref")
        or input_refs.get("source_ref")
        or ""
    ).strip()
    if not candidate_ref:
        raise ValueError("check_worldmodel_carrier_contract requires candidate_path or candidate_ref")
    path = (project / candidate_ref).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(f"candidate_ref escapes project: {candidate_ref}") from exc
    if not path.is_file():
        raise ValueError(f"candidate_ref does not exist: {candidate_ref}")
    source = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    error = carrier_contract_error(source)
    return {
        "input_hashes": {
            "source_ref": candidate_ref,
            "source_sha256": digest,
            "request": _short_receipt_json(req),
        },
        "output_summary": "carrier contract passed" if error is None else error,
    }


def _short_receipt_json(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return text if len(text) <= 1200 else text[:1197] + "..."


def _strategy_gate_receipt_summary(payload: object) -> str:
    if not isinstance(payload, dict):
        return _short_receipt_json(payload)
    nested = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    keys = (
        "status",
        "command",
        "receipt_ref",
        "receipt_sha256",
        "exact_actions",
        "exact_steps",
        "steps_tested",
        "first_mismatch",
    )
    bits = [
        f"{key}={payload.get(key)}"
        for key in keys
        if key in payload and payload.get(key) is not None
    ]
    nested_keys = (
        "exact_steps",
        "steps_tested",
        "first_failed",
        "first_failed_after_first_step_repair",
        "local_residue_class_count",
        "top_local_residue_class",
    )
    for key in nested_keys:
        if key in nested and nested.get(key) is not None:
            bits.append(f"{key}={nested.get(key)}")
    return "; ".join(bits)


def _structural_isomorphism_receipt_summary(payload: object) -> str:
    if not isinstance(payload, dict):
        return _short_receipt_json(payload)
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    bits = [
        f"mode={payload.get('mode')}",
        f"status={payload.get('status')}",
        f"receipt_ref={payload.get('receipt_ref')}",
    ]
    if "candidate_count" in result:
        bits.append(f"candidate_count={result.get('candidate_count')}")
    prescription = result.get("prescription") if isinstance(result.get("prescription"), dict) else {}
    if prescription:
        bits.append(f"source_field={prescription.get('source_field')}")
        bits.append(f"source_theorem={prescription.get('source_theorem')}")
    conjectures = result.get("conjectures") if isinstance(result.get("conjectures"), list) else []
    if conjectures:
        first = conjectures[0] if isinstance(conjectures[0], dict) else {}
        bits.append(f"mother_structure={first.get('mother_structure')}")
        cards = first.get("prediction_cards")
        if isinstance(cards, list):
            bits.append(f"prediction_cards={len(cards)}")
    return "; ".join(str(bit) for bit in bits if str(bit))


def worldmodel_leaf_workbench_records(project_dir: str | Path) -> list[dict[str, Any]]:
    project = Path(project_dir)
    workspace = project / "workspace"
    records: list[dict[str, Any]] = []
    surface = _read_active_surface_audit(workspace / "stale_surface_audit.json")
    weakness_payload = _read_json(workspace / "latest_harness_weakness.json")
    workbench_task = (
        weakness_payload.get("workbench_task")
        if isinstance(weakness_payload, dict) and isinstance(weakness_payload.get("workbench_task"), dict)
        else None
    )
    if workbench_task:
        caps = workbench_task.get("admissible_capability_ids")
        caps = [str(cap) for cap in caps] if isinstance(caps, list) else []
        cap = caps[0] if caps else "run_visible_json_probe"
        artifacts = workbench_task.get("visible_artifact_refs")
        artifacts = [str(ref) for ref in artifacts] if isinstance(artifacts, list) else []
        records.append(
            {
                "source_type": "leaf_workbench_task",
                "capability_id": cap,
                "source_ref": "workspace/latest_harness_weakness.json:workbench_task",
                "source_sha": _shaish(workspace / "latest_harness_weakness.json"),
                "summary": (
                    f"active_task={workbench_task.get('task_id')}; "
                    f"failure_class={workbench_task.get('failure_class')}; "
                    f"admissible={caps}; visible_artifacts={artifacts}; "
                    f"objective={workbench_task.get('objective')}"
                ),
            }
        )

    candidate = _best_candidate_memory_record(workspace / "candidate_memory.json")
    if candidate:
        surface_note = ""
        active = surface.get("active_carrier") if isinstance(surface.get("active_carrier"), dict) else {}
        if active.get("source") == "candidate_memory":
            surface_note = "; active_surface=candidate_memory"
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "inspect_worldmodel_patch_base",
                "source_ref": candidate.get("submission") or "workspace/candidate_memory.json",
                "source_sha": candidate.get("sha") or "",
                "summary": (
                    f"best patch base exact_rows={candidate.get('visible_exact_rows')}/"
                    f"{candidate.get('visible_checked_rows')} wrong_cells="
                    f"{candidate.get('visible_wrong_cells')} holdout_depth="
                    f"{candidate.get('holdout_depth')}{surface_note}"
                ),
            }
        )

    surface_summary = _surface_replay_quotient_summary(surface)
    if surface_summary:
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "inspect_replay_residual_quotient",
                "source_ref": "workspace/stale_surface_audit.json:current_replay",
                "source_sha": _shaish(workspace / "stale_surface_audit.json"),
                "summary": surface_summary,
            }
        )
    elif not _surface_current_replay_exact(surface):
        diag_path = _first_existing(
            workspace / "latest_replay_diagnostics_after_abduce.json",
            project / "latest_eval_results.json",
        )
        diag = _read_json(diag_path) if diag_path else None
        quotient = _extract_residual_quotient(diag)
        if diag_path and quotient:
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "inspect_replay_residual_quotient",
                    "source_ref": _rel(project, diag_path),
                    "source_sha": _shaish(diag_path),
                    "summary": quotient,
                }
            )
    else:
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "inspect_replay_residual_quotient",
                "source_ref": "workspace/stale_surface_audit.json:current_replay",
                "source_sha": _shaish(workspace / "stale_surface_audit.json"),
                "summary": (
                    "current active replay exact; stale root replay residual is "
                    "not an active repair surface"
                ),
            }
        )

    if (project / "latest_eval_results.json").exists() or (project / "gate_harness.py").exists():
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "run_worldmodel_replay_probe",
                "source_ref": "gate_harness.py/latest_eval_results.json",
                "summary": "frozen replay/holdout gate; aggregate outputs only",
            }
        )

    try:
        from ztare.worldmodel.strategy_gate_actions import strategy_gate_action_summaries

        for gate_row in strategy_gate_action_summaries(project):
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "run_strategy_required_gate",
                    "failure_family_sha": gate_row.get("failure_family_sha") or "",
                    "command": gate_row.get("command") or "",
                    "source_ref": gate_row.get("source_ref") or "workspace/strategy_experiments.jsonl",
                    "source_sha": gate_row.get("source_sha") or "",
                    "summary": gate_row.get("summary") or "",
                }
            )
    except Exception:  # noqa: BLE001
        pass

    if (workspace / "strategy_experiments.jsonl").exists():
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "validate_worldmodel_strategy_receipts",
                "source_ref": "workspace/strategy_experiments.jsonl",
                "summary": "exact failure_family_sha receipt validation",
            }
        )

    regression, regression_ref = _current_regression_receipt(project)
    if regression:
        comparison = regression.get("quotient_comparison")
        active = surface.get("active_carrier") if isinstance(surface.get("active_carrier"), dict) else {}
        active_sha = str(active.get("candidate_sha") or "").strip()
        best_prior_sha = str(regression.get("best_prior_sha") or "").strip()
        regression_role = (
            "latest_failed_candidate_vs_active_carrier"
            if active_sha and best_prior_sha.startswith(active_sha)
            else "candidate_regression_receipt"
        )
        suffix = ""
        if isinstance(comparison, dict):
            suffix = (
                f"; quotient_relation={comparison.get('relation')}; "
                f"candidate_top={comparison.get('candidate_top_quotient')}; "
                f"best_prior_top={comparison.get('best_prior_top_quotient')}"
            )
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "score_worldmodel_candidate_delta",
                "source_ref": f"{regression_ref}:candidate_regression_receipt",
                "summary": (
                    f"role={regression_role}; "
                    f"candidate_relation={regression.get('candidate_relation')}; "
                    f"exact_rows_delta={regression.get('exact_rows_delta')}; "
                    f"wrong_cells_delta={regression.get('wrong_cells_delta')}; "
                    f"holdout_depth_delta={regression.get('holdout_depth_delta')}"
                    f"{suffix}"
                ),
            }
        )
        comparison = regression.get("quotient_comparison")
        if _counterexample_context_probe_available(comparison):
            context_summary = _counterexample_context_summary(project, regression)
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "inspect_worldmodel_counterexample_context",
                    "source_ref": f"{regression_ref}:candidate_regression_receipt",
                    "summary": context_summary or (
                        "available on request: compares representative regression "
                        "counterexamples and returns differing visible state-context "
                        "features"
                    ),
                }
            )
        if _latest_counterexample_trace(project):
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "mine_worldmodel_separating_features",
                    "source_ref": "workspace/latest_patch_base_regression.json",
                    "summary": (
                        "available on request: mines visible alpha predicates "
                        "over the episode log and reports coverage/error counts"
                    ),
                }
            )
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "mine_worldmodel_lowerable_selectors",
                    "source_ref": "workspace/latest_patch_base_regression.json",
                    "summary": (
                        "available on request: scans same-shaped visible windows "
                        "for local/action predicates that lower a support chart "
                        "into executable carrier selectors"
                    ),
                }
            )
    if (workspace / "latest_level_transfer_probe.json").exists():
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
                "source_ref": "workspace/latest_level_transfer_probe.json",
                "source_sha": _shaish(workspace / "latest_level_transfer_probe.json"),
                "summary": (
                    "available on request: mines carrier-visible selectors from "
                    "Strategy-gate local patch witnesses; reports missing witness "
                    "fields if the producer receipt is too compressed"
                ),
            }
        )
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "cell_local_lowerable_carrier_selector_miner",
                "source_ref": "workspace/latest_level_transfer_probe.json",
                "source_sha": _shaish(workspace / "latest_level_transfer_probe.json"),
                "summary": (
                    "available on request: refines local transfer witnesses "
                    "with carrier-visible component topology features and "
                    "reports only gamma-lowerable selector candidates"
                ),
            }
        )
    episode_refs = sorted(
        f"raw/episodes/{path.name}" for path in (project / "raw" / "episodes").glob("episode_*.jsonl")
    )
    if episode_refs:
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "inspect_worldmodel_event_timeline",
                "source_ref": episode_refs[0],
                "source_sha": _shaish(project / episode_refs[0]),
                "summary": (
                    "available on request: groups cell-change events across time "
                    "within one episode log (declarative before/after cell "
                    "predicate; per-step counts and rate series); episode_ref "
                    "accepts visible|holdout or a raw/episodes path"
                ),
            }
        )
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "contrast_worldmodel_episodes",
                "source_ref": ",".join(episode_refs[:2]),
                "summary": (
                    "available on request: contrasts two episodes' states at a "
                    "matching step (value census delta, differing rows, shapes); "
                    "episode refs accept visible|holdout or raw/episodes paths"
                ),
            }
        )
    if not regression and candidate:
        records.append(
            {
                "source_type": "leaf_workbench_capability",
                "capability_id": "score_worldmodel_candidate_delta",
                "source_ref": "workspace/candidate_memory.json",
                "summary": "compare verifier tuple against best cached near-miss",
            }
        )
    return records


def _load_leaf_scratchpad_for_fragment(project_dir: str | Path) -> str:
    """Read the persisted leaf scratchpad (bounded to last 2000 chars) for cross-iter carry."""
    path = Path(project_dir) / "workspace" / "leaf_scratchpad.md"
    if not path.exists():
        return "(scratchpad is owned by the leaf turn that receives it)"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(scratchpad is owned by the leaf turn that receives it)"
    text = text.strip()
    if not text:
        return "(scratchpad is owned by the leaf turn that receives it)"
    # ponytail: bounded tail to keep briefing budget; full file in workspace
    return text[-2000:] if len(text) > 2000 else text


def _load_eliminated_hypotheses_for_fragment(project_dir: str | Path) -> list[str]:
    """Read credited eliminations from spec_visible_nogoods.jsonl (bounded, last 8)."""
    path = Path(project_dir) / "workspace" / "spec_visible_nogoods.jsonl"
    if not path.exists():
        return []
    try:
        import json as _json
        lines_raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    elims: list[str] = []
    for line in lines_raw:
        if not line.strip():
            continue
        try:
            row = _json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        prov = row.get("provenance") or {}
        if isinstance(prov, dict) and prov.get("source") == "investigated_science_turn":
            elim = prov.get("eliminated_hypothesis")
            if elim:
                import json as _json2
                summary = _json2.dumps(elim, sort_keys=True, default=str)[:160]
                elims.append(summary)
    return elims[-8:]  # ponytail: bounded; full ledger in workspace


def render_worldmodel_leaf_workbench_fragment(project_dir: str | Path) -> str:
    records = worldmodel_leaf_workbench_records(project_dir)
    task_rows = [row for row in records if row.get("source_type") == "leaf_workbench_task"]
    other_rows = [row for row in records if row.get("source_type") != "leaf_workbench_task"]
    candidate_bound_requests = _candidate_bound_action_requests(records)
    diagnostic_requests = _diagnostic_action_requests(records, project_dir)
    _da = None
    try:
        import json as _json
        from pathlib import Path as _P
        _proj = _P(project_dir)
        _da = _json.loads((_proj.parents[1] / "rubrics" / f"{_proj.name}.json").read_text()).get("dynamics_assumption")
    except Exception:  # noqa: BLE001
        _da = None
    _dyn_line = (
        "- PHYSICS DECLARATION: this substrate declares lawful time-dependence "
        "(dynamics_assumption: lawful_time). The `t` argument of step(grid, action, t) "
        "is admissible physics — laws may use t in lawful, compressible form "
        "(arithmetic relations with state), never as a per-step lookup; held-out "
        "rollout still kills memorization. AMNESTY: any submission previously "
        "rejected under the temporal-admissibility rule is now admissible under "
        "this declaration — do not avoid t-shaped forms on account of those past "
        "rejections; they are superseded."
        if str(_da or "").strip().lower() == "lawful_time" else None
    )
    _elims = _load_eliminated_hypotheses_for_fragment(project_dir)
    lines = [
        "## Leaf workbench capabilities",
        *([_dyn_line] if _dyn_line else []),
        *(
            [f"- already eliminated (do not revisit): {'; '.join(_elims)}"]
            if _elims else []
        ),
        "- Think freely. Receipts are required only for new workbench actions, "
        "probe outputs, score/source claims, or capability proposals. Visible "
        "briefing summaries are context, not a receipt obligation.",
        "- In visible-workbench mode, the Python carrier is sovereign; inspect "
        "`WORKBENCH_TOOLS.md` for conveniences, then use "
        "`PYTHONPATH=src python3 -m ztare.common.visible_workbench_cli ...` "
        "for same-turn probes over staged artifacts or stdin before final submission.",
        "- grid coordinates are `(row, col)`; bbox is `[row_min, col_min, row_max, col_max]`.",
        "- Direct carriers may define `step(grid, action, t)`, `PROGRAM`, or a "
        "lowerable `WORLD_MODEL_SPEC`.",
        f"- {patch_carrier_brief_line()} Never invent patch-base identity; "
        "candidate code must not import workspace/submissions because the gate "
        "loads any supplied `PATCH_BASE`.",
        "- coordinate-only deltas are diagnostic charts unless the thesis states "
        "a transport invariant that replay/holdout can test.",
        f"- contract_sha256: {WORLD_MODEL_LEAF_WORKBENCH_CONTRACT.fingerprint()}",
        # Head-anchored so middle-elision (provider max_fragment_chars) keeps the
        # INVESTIGATED close and the raw-episode analysis tools; the full surface
        # follows in the tail.
        "- INVESTIGATED is a first-class positive close: a turn may close without "
        "a carrier when your probes eliminate a hypothesis class from visible "
        "evidence (eliminated_hypothesis + witness + evidence_refs); credited when "
        "new and the witness checks out.",
        "- LOWERABILITY_BLOCKED: an impossibility claim about a missing state feature "
        "or selector is a verdict — include search_receipts (workspace/visible_cli_receipts/* "
        "probe refs) showing the feature was examined before declaring it absent; "
        "unexamined impossibility claims are R1 rejected.",
        "- Raw-episode analysis runs via `run-action` (LEAF_WORKBENCH_ACTION_REQUEST): "
        "`inspect_worldmodel_event_timeline` (group cell-change events across time), "
        "`contrast_worldmodel_episodes` (compare two episodes' states), and "
        "`run_worldmodel_evidence_probe` (author an arbitrary read-only "
        "`probe(episodes)->dict` over the raw transitions). Leaf-authored scratch "
        "analysis code over the raw jsonl is allowed.",
    ]
    if task_rows:
        lines.append("- active workbench task:")
        for row in task_rows:
            lines.append(
                f"  - `{row['capability_id']}`: source={row.get('source_ref','?')}; "
                f"{row.get('summary','')}"
            )
    if candidate_bound_requests:
        lines.append("- current candidate-bound action request(s):")
        for request in candidate_bound_requests:
            lines.append(
                "  - "
                + json.dumps(
                    request,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
    if diagnostic_requests:
        lines.append("- current diagnostic action request(s):")
        for request in diagnostic_requests:
            lines.append(
                "  - "
                + json.dumps(
                    request,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
    if other_rows:
        lines.append("- available actions:")
        for row in other_rows:
            lines.append(
                f"  - `{row['capability_id']}`: source={row.get('source_ref','?')}; "
                    f"{row.get('summary','')}"
                )
    else:
        lines.append("- available actions: no visible-artifact actions are currently registered.")
    lines.append("- read-only source fibers for tool/capability proposals:")
    for ref, purpose in WORLD_MODEL_LEAF_WORKBENCH_SOURCE_FIBERS:
        lines.append(f"  - `{ref}`: {purpose}")
    lines.append(
        "- source fibers are visible workbench context only. To change a mutable "
        "sensor in science mode, report the tool gap inside LOWERABILITY_BLOCKED; "
        "capability proposals are cold meta evidence and hard-kernel gates remain "
        "outside this surface."
    )
    lines.append(
        render_leaf_workbench_mutator_surface(
            query_rounds_left=2,
            query_menu="- no bounded query menu is exposed on this surface",
            query_menu_json="[]",
            scratchpad_text=_load_leaf_scratchpad_for_fragment(project_dir),
            investigated_rounds_left=SCIENCE_INVESTIGATED_STAGNATION_K,
        )
    )
    lines.append(
        render_leaf_workbench_control_rules()
    )
    lines.append(render_leaf_workbench_capability_proposal_shape())
    return "\n".join(lines) + "\n"


def _candidate_bound_action_requests(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in records:
        capability_id = str(row.get("capability_id") or "").strip()
        if capability_id != "run_strategy_required_gate":
            continue
        input_refs = {
            "task_ref": row.get("source_ref") or "workspace/strategy_experiments.jsonl",
            "candidate_path": "test_model.py",
        }
        failure_family_sha = str(row.get("failure_family_sha") or "").strip()
        command = str(row.get("command") or "").strip()
        if failure_family_sha:
            input_refs["failure_family_sha"] = failure_family_sha
        if command:
            input_refs["command"] = command
        request = leaf_workbench_action_request_object(
            capability_id=capability_id,
            input_refs=input_refs,
            claim_bindings=[
                "run declared Strategy gate against the current candidate carrier",
            ],
        )
        key = json.dumps(request, sort_keys=True, separators=(",", ":"), default=str)
        if key in seen:
            continue
        seen.add(key)
        requests.append(request)
    return requests[:3]


def _diagnostic_action_requests(
    records: list[dict[str, Any]],
    project_dir: str | Path,
) -> list[dict[str, Any]]:
    """Return current pure-diagnostic morphisms selected by open card receipts."""

    has_global_selector = any(
        str(row.get("capability_id") or "")
        == "mine_worldmodel_global_carrier_selectors_from_observable_context"
        and str(row.get("source_ref") or "") == "workspace/latest_level_transfer_probe.json"
        for row in records
    )
    if not has_global_selector:
        return []
    try:
        from ztare.common.operator_proposal_contract import open_cards

        cards = open_cards(Path(project_dir) / "workspace" / "strategy_experiments.jsonl")
    except Exception:  # noqa: BLE001
        return []
    requests: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        if str(plan.get("source_receipt") or "") != "workspace/latest_level_transfer_probe.json":
            continue
        request = leaf_workbench_action_request_object(
            capability_id="mine_worldmodel_global_carrier_selectors_from_observable_context",
            input_refs={
                "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
                "source_card_sha": str(card.get("failure_family_sha") or ""),
            },
            claim_bindings=[
                "mine lowerable carrier selectors for the open Strategy repair residue",
            ],
        )
        key = json.dumps(request, sort_keys=True, separators=(",", ":"), default=str)
        if key in seen:
            continue
        seen.add(key)
        requests.append(request)
    return requests[:3]


def _read_json(path: Path | None) -> Any:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _read_regression_payload(project: Path, regression_ref: str) -> tuple[dict[str, Any], Path]:
    path = (project / regression_ref).resolve()
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}, path
    if isinstance(payload.get("candidate_regression_receipt"), dict) or isinstance(
        payload.get("counterexample_trace"), dict
    ):
        return payload, path
    nested = payload.get("candidate_regression_receipt")
    if not isinstance(nested, dict):
        summary = payload.get("output_summary")
        if isinstance(summary, str) and summary.strip():
            try:
                parsed = json.loads(summary)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(parsed, dict):
                nested = parsed.get("candidate_regression_receipt")
                trace = parsed.get("counterexample_trace")
                if isinstance(nested, dict):
                    return {
                        "candidate_regression_receipt": nested,
                        "counterexample_trace": trace if isinstance(trace, dict) else {},
                    }, path
    if isinstance(nested, dict):
        return {
            "candidate_regression_receipt": nested,
            "counterexample_trace": payload.get("counterexample_trace")
            if isinstance(payload.get("counterexample_trace"), dict)
            else {},
        }, path
    return payload, path


def _regression_ref_from_input_refs(project: Path, input_refs: Mapping[str, Any]) -> str:
    for key in (
        "score_receipt_ref",
        "candidate_score_ref",
        "latest_score_ref",
        "latest_regression_ref",
        "regression_ref",
        "latest_eval_ref",
        "transfer_receipt_ref",
        "strategy_gate_receipt_ref",
    ):
        ref = str(input_refs.get(key) or "").strip()
        if ref and _ref_has_regression_payload(project, ref):
            return ref
    return _latest_visible_candidate_score_ref(project) or "workspace/latest_patch_base_regression.json"


def _ref_has_regression_payload(project: Path, ref: str) -> bool:
    payload, _path = _read_regression_payload(project, ref)
    return isinstance(payload.get("candidate_regression_receipt"), dict) or isinstance(
        payload.get("counterexample_trace"), dict
    )


def _latest_visible_candidate_score_ref(project: Path) -> str:
    root = project / "workspace" / "visible_cli_receipts"
    if not root.is_dir():
        return ""
    candidates = sorted(
        root.glob("score_worldmodel_candidate_delta_*.json"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
        reverse=True,
    )
    for path in candidates:
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        summary = payload.get("output_summary")
        if not isinstance(summary, str) or "candidate_regression_receipt" not in summary:
            continue
        try:
            return _rel(project, path)
        except Exception:  # noqa: BLE001
            return str(path)
    return ""


def _read_active_surface_audit(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}
    if payload.get("schema") != "ztare-worldmodel-stale-surface-audit-v1":
        return {}
    return payload


def _surface_current_replay_exact(surface: dict[str, Any]) -> bool:
    replay = surface.get("current_replay") if isinstance(surface.get("current_replay"), dict) else {}
    checked = _as_int(replay.get("checked_rows"))
    exact = _as_int(replay.get("exact_rows"))
    wrong = _as_int(replay.get("wrong_cell_count"))
    return bool(checked and exact == checked and wrong == 0)


def _surface_replay_quotient_summary(surface: dict[str, Any]) -> str:
    replay = surface.get("current_replay") if isinstance(surface.get("current_replay"), dict) else {}
    top = replay.get("top_mismatch_class") if isinstance(replay.get("top_mismatch_class"), dict) else {}
    if not top:
        return ""
    sig = top.get("signature") if isinstance(top.get("signature"), dict) else {}
    pairs = sig.get("pair_counts") if isinstance(sig.get("pair_counts"), list) else []
    pair_text = ",".join(
        f"{row.get('predicted')}->{row.get('real')}x{row.get('count')}"
        for row in pairs
        if isinstance(row, dict)
    )
    return (
        f"class_count={top.get('count')}; t={top.get('t')}; "
        f"action={top.get('action')}; bbox={sig.get('bbox') or top.get('bbox')}; "
        f"pairs={pair_text}; source=active_surface_audit"
    )


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _best_candidate_memory_record(path: Path) -> dict[str, Any] | None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    project = path.parent.parent
    records = admissible_candidate_memory_records(
        project,
        [row for row in payload.get("records") or [] if isinstance(row, dict)],
    )
    records = [
        row
        for row in records
        if str(row.get("submission") or "").strip().startswith(
            "workspace/submissions/"
        )
    ]
    if not records:
        return None

    def rank(row: dict[str, Any]) -> tuple[int, int, float, int]:
        return (
            int(row.get("visible_exact_rows") or 0),
            int(row.get("holdout_depth") or 0),
            float(row.get("gate_score") or 0.0),
            -int(row.get("visible_wrong_cells") or 999999),
        )

    return max(records, key=rank)


def _extract_residual_quotient(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    trace = payload.get("counterexample_trace") if isinstance(payload.get("counterexample_trace"), dict) else payload
    classes = trace.get("mismatch_classes") if isinstance(trace, dict) else None
    if not isinstance(classes, list) or not classes:
        return ""
    top = classes[0]
    if not isinstance(top, dict):
        return ""
    sig = top.get("signature") if isinstance(top.get("signature"), dict) else {}
    pairs = sig.get("pair_counts") if isinstance(sig.get("pair_counts"), list) else []
    pair_text = ",".join(
        f"{row.get('predicted')}->{row.get('real')}x{row.get('count')}"
        for row in pairs
        if isinstance(row, dict)
    )
    return (
        f"class_count={top.get('count') or top.get('class_count')}; "
        f"t={top.get('t')}; action={top.get('action')}; "
        f"bbox={sig.get('bbox') or top.get('bbox')}; pairs={pair_text}"
    )


def _latest_regression_receipt(path: Path) -> dict[str, Any] | None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    receipt = payload.get("candidate_regression_receipt")
    return receipt if isinstance(receipt, dict) else None


def _current_regression_receipt(project: Path) -> tuple[dict[str, Any] | None, str]:
    for rel in (
        "workspace/latest_patch_base_regression.json",
        "latest_eval_results.json",
    ):
        receipt = _latest_regression_receipt(project / rel)
        if receipt:
            return receipt, rel
    return None, "latest_eval_results.json"


def run_worldmodel_counterexample_context_probe(
    project_dir: str | Path,
    *,
    regression_ref: str = "",
) -> str:
    """Compute the visible counterexample-context probe on explicit request."""
    project = Path(project_dir)
    if regression_ref:
        payload, _path = _read_regression_payload(project, regression_ref)
        regression = (
            payload.get("candidate_regression_receipt")
            if isinstance(payload.get("candidate_regression_receipt"), dict)
            else None
        )
    else:
        regression, regression_ref = _current_regression_receipt(project)
    if not regression:
        raise ValueError(f"{regression_ref} has no candidate_regression_receipt")
    summary = _counterexample_context_summary(project, regression)
    if not summary:
        raise ValueError("no regression counterexample context is available")
    return summary


def run_worldmodel_separating_feature_miner(
    project_dir: str | Path,
    *,
    regression_ref: str = "workspace/latest_patch_base_regression.json",
    episode_ref: str = "raw/episodes/episode_001.jsonl",
    max_predicates: int = 8,
) -> str:
    """Mine visible alpha-refinement predicates for the latest counterexample.

    This does not score or promote a candidate. It only compresses frozen
    transition evidence into small predicates with confusion matrices, so a
    leaf can propose a candidate from a receipt instead of from one coordinate.
    """
    project = Path(project_dir)
    payload, regression_path = _read_regression_payload(project, regression_ref)
    trace = (
        payload.get("counterexample_trace")
        if isinstance(payload, dict) and isinstance(payload.get("counterexample_trace"), dict)
        else {}
    )
    bbox = _trace_bbox(trace)
    first_row = _trace_first_row(trace)
    if len(bbox) != 4 or first_row is None:
        raise ValueError("latest regression has no counterexample bbox/row to mine")
    try:
        from ztare.worldmodel.episode_log import EpisodeLog

        transitions = EpisodeLog.read_jsonl(project / episode_ref).transitions()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"could not read episode log for feature mining: {episode_ref}") from exc
    if first_row < 0 or first_row >= len(transitions):
        raise ValueError("counterexample representative row is outside the episode log")
    target_label = _support_values(transitions[first_row].s_next, bbox)
    source_label = _support_values(transitions[first_row].s, bbox)
    rows: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    for idx, tr in enumerate(transitions):
        try:
            next_label = _support_values(tr.s_next, bbox)
            state_label = _support_values(tr.s, bbox)
        except Exception:
            continue
        positive = next_label == target_label
        label_counts[_compact_tuple(next_label)] += 1
        rows.append(
            {
                "idx": idx,
                "t": tr.t,
                "action": tr.a,
                "positive": positive,
                "features": _transition_alpha_features(tr.s, bbox, action=tr.a),
                "state_support": state_label,
            }
        )
    if not rows:
        raise ValueError("episode log produced no rows for counterexample support")
    positive_rows = [row for row in rows if row["positive"]]
    if not positive_rows:
        raise ValueError("target support label never appears in episode log")
    predicates = [
        _annotate_predicate_lowering_scope(row)
        for row in _rank_separating_predicates(
            rows,
            positive_rows,
            max_predicates=max_predicates,
        )
    ]
    candidate_predicates = [
        row for row in predicates if row.get("lowering_scope") == "global_carrier_input"
    ]
    support_scoped_predicates = [
        row for row in predicates if row.get("lowering_scope") != "global_carrier_input"
    ]
    payload_out = {
        "schema": "ztare-worldmodel-separating-feature-miner-v1",
        "authority": "diagnostic_only",
        "regression_ref": _rel(project, regression_path),
        "support_bbox": bbox,
        "representative_row": first_row,
        "representative_t": transitions[first_row].t,
        "representative_action": transitions[first_row].a,
        "source_support_label": source_label,
        "target_support_label": target_label,
        "target_label_counts": dict(label_counts),
        "positive_rows": len(positive_rows),
        "total_rows": len(rows),
        "candidate_predicates": candidate_predicates,
        "support_scoped_predicates": support_scoped_predicates,
        "diagnostic_only_fields": ["representative_row", "representative_t"],
        "admissibility_note": (
            "Use predicates over observable state/action features as candidate "
            "guards; row/t values are diagnostics only and are not admissible "
            "carrier guards."
        ),
        "lowerability_note": (
            "Predicates over support_values/local_band_counts/support_row_counts/"
            "support_row_sections are quotient-chart separators for this support_bbox. "
            "They are not global carrier selectors unless another admissible predicate "
            "selects the same support without row/t or support identity."
        ),
    }
    return json.dumps(payload_out, sort_keys=True, separators=(",", ":"), default=str)


def run_worldmodel_lowerable_selector_miner(
    project_dir: str | Path,
    *,
    regression_ref: str = "workspace/latest_patch_base_regression.json",
    episode_ref: str = "raw/episodes/episode_001.jsonl",
    max_predicates: int = 8,
) -> str:
    """Mine executable selectors by scanning local windows across visible logs.

    The first separating-feature miner works on one counterexample chart. This
    pass tries to lower that chart into a carrier predicate by quantifying over
    every same-shaped window in the visible transition log. Absolute row/time
    and the original support identity never enter the predicate language.
    """
    project = Path(project_dir)
    payload, regression_path = _read_regression_payload(project, regression_ref)
    trace = (
        payload.get("counterexample_trace")
        if isinstance(payload, dict) and isinstance(payload.get("counterexample_trace"), dict)
        else {}
    )
    bbox = _trace_bbox(trace)
    first_row = _trace_first_row(trace)
    if len(bbox) != 4 or first_row is None:
        raise ValueError("latest regression has no counterexample bbox/row to lower")
    try:
        from ztare.worldmodel.episode_log import EpisodeLog

        transitions = EpisodeLog.read_jsonl(project / episode_ref).transitions()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"could not read episode log for selector mining: {episode_ref}") from exc
    if first_row < 0 or first_row >= len(transitions):
        raise ValueError("counterexample representative row is outside the episode log")
    rep = transitions[first_row]
    source_label = _support_values(rep.s, bbox)
    target_label = _support_values(rep.s_next, bbox)
    r0, c0, r1, c1 = bbox
    win_h = max(0, r1 - r0 + 1)
    win_w = max(0, c1 - c0 + 1)
    if win_h <= 0 or win_w <= 0:
        raise ValueError("counterexample bbox has invalid shape")

    rows: list[dict[str, Any]] = []
    total_windows = 0
    same_source_windows = 0
    for idx, tr in enumerate(transitions):
        h = len(tr.s)
        w = len(tr.s[0]) if h else 0
        if h < win_h or w < win_w:
            continue
        for rr in range(0, h - win_h + 1):
            for cc in range(0, w - win_w + 1):
                total_windows += 1
                box = [rr, cc, rr + win_h - 1, cc + win_w - 1]
                if not _window_matches_label(
                    tr.s,
                    rr,
                    cc,
                    win_h,
                    win_w,
                    source_label,
                ):
                    continue
                same_source_windows += 1
                rows.append(
                    {
                        "idx": idx,
                        "t": tr.t,
                        "action": tr.a,
                        "bbox": box,
                        "positive": _window_matches_label(
                            tr.s_next,
                            rr,
                            cc,
                            win_h,
                            win_w,
                            target_label,
                        ),
                        "features": _lowerable_window_alpha_features(
                            tr.s,
                            box,
                            action=tr.a,
                            source_label=source_label,
                        ),
                    }
                )
    if not rows:
        raise ValueError("no visible same-source windows found for selector mining")
    positive_rows = [row for row in rows if row["positive"]]
    tn_extra = max(0, total_windows - same_source_windows)
    ranked = _rank_lowerable_window_predicates(
        rows,
        positive_rows,
        source_label=source_label,
        tn_extra=tn_extra,
        max_predicates=max_predicates,
    )
    candidate_predicates = [
        row for row in ranked if row.get("perfect_on_visible_log") is True
    ]
    near_misses = [
        row for row in ranked if row.get("perfect_on_visible_log") is not True
    ]
    if candidate_predicates:
        lowerability_status = "candidate_selectors_found"
    elif positive_rows and len(positive_rows) == same_source_windows:
        lowerability_status = "underdetermined_no_negative_same_source_windows"
    else:
        lowerability_status = "no_zero_error_selector_found"
    payload_out = {
        "schema": "ztare-worldmodel-lowerable-selector-miner-v1",
        "authority": "diagnostic_only",
        "regression_ref": _rel(project, regression_path),
        "window_shape": [win_h, win_w],
        "source_window_values": source_label,
        "target_window_values": target_label,
        "representative_action": rep.a,
        "same_source_windows": same_source_windows,
        "positive_windows": len(positive_rows),
        "total_windows": total_windows,
        "lowerability_status": lowerability_status,
        "candidate_delta_admissible": bool(candidate_predicates),
        "candidate_predicates": candidate_predicates,
        "near_miss_predicates": near_misses[:max_predicates],
        "diagnostic_only_fields": ["representative_action"],
        "forbidden_feature_classes": [
            "absolute_row",
            "absolute_time",
            "support_identity",
            "quotient_label",
            "hidden_evaluator_field",
        ],
        "executable_delta_hint": (
            "Scan same-shaped windows over state; when window_values plus the "
            "listed predicate features hold, replace source_window_values with "
            "target_window_values at that window. Replay/holdout remains the "
            "promotion authority."
            if candidate_predicates
            else ""
        ),
    }
    return json.dumps(payload_out, sort_keys=True, separators=(",", ":"), default=str)


def run_worldmodel_global_carrier_selector_miner(
    project_dir: str | Path,
    *,
    transfer_ref: str = "workspace/latest_level_transfer_probe.json",
    max_predicates: int = 8,
    include_component_features: bool = False,
    schema: str = "ztare-worldmodel-global-carrier-selector-miner-v1",
) -> str:
    """Mine carrier-visible selectors from level-transfer diff witnesses.

    This consumes a Strategy-gate receipt, not hidden environment state. The
    observed value is used only as the rewrite target; selector features are
    limited to inputs available to PATCH_DELTA: current state, base_next, and
    action.
    """
    project = Path(project_dir)
    receipt = _read_json(project / transfer_ref)
    if not isinstance(receipt, dict):
        raise ValueError(f"transfer receipt is not JSON object: {transfer_ref}")
    local_rows = receipt.get("local_rows") if isinstance(receipt.get("local_rows"), list) else []
    examples: list[dict[str, Any]] = []
    missing_patch_witness = 0
    for local_row in local_rows:
        if not isinstance(local_row, dict):
            continue
        primary_witness = (
            local_row.get("local_patch_witness")
            if isinstance(local_row.get("local_patch_witness"), dict)
            else {}
        )
        component_witnesses = (
            local_row.get("component_patch_witnesses")
            if isinstance(local_row.get("component_patch_witnesses"), list)
            else []
        )
        witnesses: list[dict[str, Any]] = []
        if include_component_features:
            witnesses.extend(w for w in component_witnesses if isinstance(w, dict))
        if primary_witness:
            witnesses.append(primary_witness)
        if not witnesses:
            missing_patch_witness += 1
            continue
        for witness in witnesses:
            before_patch = witness.get("before_patch")
            predicted_patch = witness.get("predicted_patch")
            diff_cells = witness.get("diff_cells") if isinstance(witness.get("diff_cells"), list) else []
            if not isinstance(before_patch, list) or not isinstance(predicted_patch, list):
                missing_patch_witness += 1
                continue
            observed_patch = witness.get("observed_patch")
            if not isinstance(observed_patch, list):
                observed_patch = predicted_patch
            bbox = witness.get("bbox") if isinstance(witness.get("bbox"), list) else []
            diff_positions: set[tuple[int, int]] = set()
            for diff in diff_cells:
                if not isinstance(diff, dict):
                    continue
                rel = _patch_relative_position(diff, bbox)
                if rel is not None:
                    diff_positions.add(rel)
            for rr, before_row in enumerate(before_patch):
                if not isinstance(before_row, list):
                    continue
                pred_row = predicted_patch[rr] if rr < len(predicted_patch) else []
                obs_row = observed_patch[rr] if rr < len(observed_patch) else []
                if not isinstance(pred_row, list) or not isinstance(obs_row, list):
                    continue
                for cc, before_cell in enumerate(before_row):
                    before = _as_int(before_cell)
                    predicted = _as_int(pred_row[cc] if cc < len(pred_row) else None)
                    observed = _as_int(obs_row[cc] if cc < len(obs_row) else predicted)
                    if before is None or predicted is None or observed is None:
                        continue
                    if before == predicted == observed and (rr, cc) not in diff_positions:
                        # Still include unchanged cells below as negatives for each
                        # rewrite label; this branch documents the intentional fall-through.
                        pass
                    examples.append(
                        {
                            "positive": False,
                            "rewrite_label": predicted != observed,
                            "label": (before, predicted, observed),
                            "features": _global_selector_features(
                                before_patch,
                                predicted_patch,
                                action=_as_int(local_row.get("action")),
                                before=before,
                                predicted=predicted,
                                patch_row=rr,
                                patch_col=cc,
                                include_component_features=include_component_features,
                            ),
                            "rewrite": {
                                "before": before,
                                "predicted": predicted,
                                "observed": observed,
                            },
                        }
                    )
            for diff in diff_cells:
                if not isinstance(diff, dict):
                    continue
                before = _as_int(diff.get("before"))
                predicted = _as_int(diff.get("predicted"))
                observed = _as_int(diff.get("observed"))
                if before is None or predicted is None or observed is None:
                    continue
                if any(row["label"] == (before, predicted, observed) for row in examples):
                    continue
                rel = _patch_relative_position(diff, bbox)
                examples.append(
                    {
                        "positive": False,
                        "rewrite_label": predicted != observed,
                        "label": (before, predicted, observed),
                        "features": _global_selector_features(
                            before_patch,
                            predicted_patch,
                            action=_as_int(local_row.get("action")),
                            before=before,
                            predicted=predicted,
                            patch_row=rel[0] if rel else None,
                            patch_col=rel[1] if rel else None,
                            include_component_features=include_component_features,
                        ),
                        "rewrite": {
                            "before": before,
                            "predicted": predicted,
                            "observed": observed,
                        },
                    }
                )
    rewrite_labels = sorted(
        {row["label"] for row in examples if row.get("rewrite_label")},
        key=str,
    )
    label_counts: Counter[str] = Counter(
        _compact_tuple(row["label"])
        for row in examples
        if row.get("rewrite_label")
    )
    ranked: list[dict[str, Any]] = []
    for label in rewrite_labels:
        rows = []
        for row in examples:
            cloned = dict(row)
            cloned["positive"] = row["label"] == label
            rows.append(cloned)
        positives = [row for row in rows if row["positive"]]
        ranked.extend(
            _rank_global_selector_predicates(
                rows,
                positives,
                rewrite=positives[0]["rewrite"] if positives else {},
                max_predicates=max_predicates,
            )
        )
    ranked.sort(
        key=lambda row: (
            not row["perfect_on_visible_receipt"],
            row["confusion_matrix"]["fp"],
            row["confusion_matrix"]["fn"],
            row["complexity"],
            -row["confusion_matrix"]["tp"],
        )
    )
    candidate_predicates = [
        row
        for row in ranked
        if row.get("perfect_on_visible_receipt") is True
        and row.get("lowering_scope") == "global_carrier_input"
    ][:max_predicates]
    near_misses = [
        row for row in ranked if row not in candidate_predicates
    ][:max_predicates]
    covered_labels = {
        (
            pred.get("rewrite", {}).get("before"),
            pred.get("rewrite", {}).get("predicted"),
            pred.get("rewrite", {}).get("observed"),
        )
        for pred in candidate_predicates
    }
    if candidate_predicates and all(label in covered_labels for label in rewrite_labels):
        status = "candidate_selectors_found"
    elif candidate_predicates:
        status = "partial_candidate_selectors_found"
    elif examples:
        status = "no_zero_error_selector_found"
    else:
        status = "missing_local_patch_witness"
    payload_out = {
        "schema": schema,
        "authority": "diagnostic_only",
        "source_receipt": transfer_ref,
        "example_count": len(examples),
        "label_counts": dict(label_counts),
        "candidate_label_coverage": {
            "covered": [_compact_tuple(label) for label in sorted(covered_labels, key=str)],
            "required": [_compact_tuple(label) for label in rewrite_labels],
        },
        "missing_patch_witness_rows": missing_patch_witness,
        "lowerability_status": status,
        "candidate_delta_admissible": status == "candidate_selectors_found",
        "candidate_predicates": candidate_predicates,
        "near_miss_predicates": near_misses,
        "missing_fields": (
            ["local_rows[].local_patch_witness"]
            if not examples
            else []
        ),
        "forbidden_feature_classes": [
            "absolute_row",
            "absolute_time",
            "support_identity",
            "quotient_label",
            "hidden_evaluator_field",
        ],
        "executable_delta_hint": (
            "For each carrier-visible cell/window satisfying the listed selector "
            "features over state/base_next/action, rewrite predicted to observed; "
            "candidate replay and holdout remain the promotion authority."
            if candidate_predicates
            else ""
        ),
    }
    return json.dumps(payload_out, sort_keys=True, separators=(",", ":"), default=str)


def run_worldmodel_cell_local_carrier_selector_miner(
    project_dir: str | Path,
    *,
    transfer_ref: str = "workspace/latest_level_transfer_probe.json",
    max_predicates: int = 12,
) -> str:
    return run_worldmodel_global_carrier_selector_miner(
        project_dir,
        transfer_ref=transfer_ref,
        max_predicates=max_predicates,
        include_component_features=True,
        schema="ztare-worldmodel-cell-local-carrier-selector-miner-v1",
    )


def _selector_record_key(record: Mapping[str, Any]) -> str:
    for key in ("key", "selector_key", "field", "domain_key", "label"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _selector_record_value(record: Mapping[str, Any]) -> Any:
    for key in ("value", "selector_value", "payload", "predicted", "assigned_value"):
        if key in record:
            value = record.get(key)
            if isinstance(value, Mapping):
                if "value" in value and len(value) <= 2:
                    return value.get("value")
                for nested_key in ("value", "selector_value", "predicted", "assigned_value"):
                    if nested_key in value:
                        return value.get(nested_key)
            return value
    return None


def _selector_record_guard(record: Mapping[str, Any]) -> dict[str, Any]:
    guard: dict[str, Any] = {}
    for key in ("guard", "guards", "domain_guard"):
        value = record.get(key)
        if isinstance(value, Mapping):
            for guard_key, guard_value in value.items():
                if guard_value is not None:
                    guard[str(guard_key)] = guard_value
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, Mapping):
                    continue
                for guard_key, guard_value in item.items():
                    if guard_value is not None:
                        guard[str(guard_key)] = guard_value
    for guard_key in ("when_phase", "when_action", "when_region", "when_dest", "when_count"):
        if guard_key in record and record.get(guard_key) is not None:
            guard[guard_key] = record.get(guard_key)
    return guard


def _guard_domain_descriptor(guard: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): guard[key] for key in sorted(guard) if guard.get(key) is not None}


def _guards_provably_disjoint(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    shared_families = set(left) & set(right)
    if not shared_families:
        return False
    disjoint_seen = False
    for family in shared_families:
        lval = left.get(family)
        rval = right.get(family)
        if lval is None or rval is None:
            continue
        if family in {"when_action", "when_count"} and lval != rval:
            disjoint_seen = True
            continue
        if family == "when_phase" and isinstance(lval, list) and isinstance(rval, list):
            if len(lval) == 2 and len(rval) == 2 and lval[0] == rval[0] and lval[1] != rval[1]:
                disjoint_seen = True
                continue
        return False
    return disjoint_seen


def _selector_entries_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("selector_map", "selectors", "partial_selector", "partial_selectors", "candidate_predicates"):
            value = payload.get(key)
            if isinstance(value, list):
                coverage = payload.get("candidate_label_coverage")
                covered = []
                if isinstance(coverage, dict) and isinstance(coverage.get("covered"), list):
                    covered = [str(item) for item in coverage.get("covered") if str(item)]
                entries = []
                for idx, row in enumerate(value):
                    if not isinstance(row, dict):
                        continue
                    key_value = row.get("key")
                    if key_value is None:
                        if len(covered) == 1:
                            key_value = covered[0]
                        elif idx < len(covered):
                            key_value = covered[idx]
                    if key_value is None:
                        rewrite = row.get("rewrite") if isinstance(row.get("rewrite"), dict) else {}
                        label = rewrite.get("before")
                        predicted = rewrite.get("predicted")
                        observed = rewrite.get("observed")
                        if label is not None:
                            key_value = _compact_tuple((label, predicted, observed))
                    if key_value is None:
                        continue
                    entry = {"key": key_value, "value": row}
                    guard = _selector_record_guard(row)
                    if guard:
                        entry["guard"] = guard
                    entries.append(entry)
                if entries:
                    return entries
            if isinstance(value, dict):
                entries = []
                for k, v in value.items():
                    entry = {"key": str(k), "value": v}
                    if isinstance(v, Mapping):
                        guard = _selector_record_guard(v)
                        if guard:
                            entry["guard"] = guard
                    entries.append(entry)
                if entries:
                    return entries
        summary = payload.get("output_summary")
        if isinstance(summary, str):
            try:
                parsed = json.loads(summary)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                entries = _selector_entries_from_payload(parsed)
                if entries:
                    return entries
    return []


def join_lowerable_selectors(
    project_dir: str | Path,
    *,
    selector_a_ref: str,
    selector_b_ref: str,
) -> str:
    """Join two partial selector receipts by coproduct over disjoint domains."""

    project = Path(project_dir)
    left = _read_json(project / selector_a_ref)
    right = _read_json(project / selector_b_ref)
    left_entries = _selector_entries_from_payload(left)
    right_entries = _selector_entries_from_payload(right)
    if not left_entries or not right_entries:
        raise ValueError("join_lowerable_selectors requires selector receipts with partial selector entries")

    joined: list[dict[str, Any]] = []
    conflicts: list[str] = []
    conflict_pairs: list[dict[str, Any]] = []
    left_joined = [
        {
            "key": _selector_record_key(entry),
            "value": _selector_record_value(entry),
            "guard": _guard_domain_descriptor(_selector_record_guard(entry)),
            "source": "selector_a_ref",
        }
        for entry in left_entries
        if _selector_record_key(entry)
    ]
    right_joined = [
        {
            "key": _selector_record_key(entry),
            "value": _selector_record_value(entry),
            "guard": _guard_domain_descriptor(_selector_record_guard(entry)),
            "source": "selector_b_ref",
        }
        for entry in right_entries
        if _selector_record_key(entry)
    ]
    joined.extend(left_joined)
    for right_item in right_joined:
        for left_item in left_joined:
            if left_item["key"] != right_item["key"]:
                continue
            if left_item["value"] == right_item["value"]:
                if not left_item["guard"] or not right_item["guard"]:
                    conflicts.append(right_item["key"])
                    conflict_pairs.append(
                        {
                            "selector_key": right_item["key"],
                            "overlap_kind": "unguarded_duplicate_selector",
                            "left_guard": left_item["guard"],
                            "right_guard": right_item["guard"],
                        }
                    )
                    break
                if not _guards_provably_disjoint(left_item["guard"], right_item["guard"]):
                    conflicts.append(right_item["key"])
                    overlap = _guard_pair_conflict(left_item["guard"], right_item["guard"]) or {}
                    conflict_pairs.append({"selector_key": right_item["key"], **overlap})
                    break
            else:
                if not left_item["guard"] or not right_item["guard"]:
                    conflicts.append(right_item["key"])
                    conflict_pairs.append(
                        {
                            "selector_key": right_item["key"],
                            "overlap_kind": "unguarded_incompatible_selector",
                            "left_guard": left_item["guard"],
                            "right_guard": right_item["guard"],
                        }
                    )
                    break
                if not _guards_provably_disjoint(left_item["guard"], right_item["guard"]):
                    conflicts.append(right_item["key"])
                    overlap = _guard_pair_conflict(left_item["guard"], right_item["guard"]) or {}
                    conflict_pairs.append({"selector_key": right_item["key"], **overlap})
                    break
        else:
            joined.append(right_item)

    if conflicts:
        payload_out = {
            "schema": "ztare-worldmodel-joined-selector-miner-v1",
            "authority": "diagnostic_only",
            "join_status": "conflict",
            "candidate_delta_admissible": False,
            "conflicting_keys": sorted(set(conflicts)),
            "inadmissibility_reason": (
                "guarded coproduct conflict on keys: "
                + ",".join(sorted(set(conflicts)))
            ),
            "conflicting_guard_pairs": conflict_pairs,
            "joined_predicates": [],
        }
    else:
        payload_out = {
            "schema": "ztare-worldmodel-joined-selector-miner-v1",
            "authority": "diagnostic_only",
            "join_status": "candidate_selectors_found",
            "candidate_delta_admissible": True,
            "conflicting_keys": [],
            "inadmissibility_reason": "",
            "joined_predicates": [
                {
                    "key": item["key"],
                    "value": item["value"],
                    "guard": item["guard"],
                    "source": item["source"],
                    "lowering_scope": "guarded_partial_function_coproduct",
                }
                for item in sorted(joined, key=lambda row: (row["key"], row["source"], str(row["guard"])))
            ],
        }
    payload_out["selector_a_ref"] = selector_a_ref
    payload_out["selector_b_ref"] = selector_b_ref
    return json.dumps(payload_out, sort_keys=True, separators=(",", ":"), default=str)


def _counterexample_context_probe_available(comparison: Any) -> bool:
    if not isinstance(comparison, dict):
        return False
    if comparison.get("relation") not in {
        "changed_support",
        "same_support_changed_pairs",
        "same_quotient_worse_frequency",
    }:
        return False
    cand = comparison.get("candidate_top_quotient")
    best = comparison.get("best_prior_top_quotient")
    if not isinstance(cand, dict) or not isinstance(best, dict):
        return False
    bbox = cand.get("bbox") if isinstance(cand.get("bbox"), list) else []
    return (
        _as_int(cand.get("first_row")) is not None
        and _as_int(best.get("first_row")) is not None
        and len(bbox) == 4
    )


def _counterexample_context_summary(project: Path, regression: dict[str, Any]) -> str:
    comparison = regression.get("quotient_comparison")
    if not isinstance(comparison, dict):
        return ""
    if comparison.get("relation") not in {
        "changed_support",
        "same_support_changed_pairs",
        "same_quotient_worse_frequency",
    }:
        return ""
    cand = comparison.get("candidate_top_quotient")
    best = comparison.get("best_prior_top_quotient")
    if not isinstance(cand, dict) or not isinstance(best, dict):
        return ""
    c_row = _as_int(cand.get("first_row"))
    b_row = _as_int(best.get("first_row"))
    bbox = cand.get("bbox") if isinstance(cand.get("bbox"), list) else []
    if c_row is None or b_row is None or len(bbox) != 4:
        return ""
    try:
        from ztare.worldmodel.episode_log import EpisodeLog

        transitions = EpisodeLog.read_jsonl(
            project / "raw" / "episodes" / "episode_001.jsonl"
        ).transitions()
        c_tr = transitions[c_row]
        b_tr = transitions[b_row]
    except Exception:  # noqa: BLE001
        return ""
    c_ctx = _state_context_features(c_tr.s, bbox)
    b_ctx = _state_context_features(b_tr.s, bbox)
    deltas = []
    for key in sorted(set(c_ctx) | set(b_ctx)):
        if c_ctx.get(key) != b_ctx.get(key):
            deltas.append(f"{key}:candidate={c_ctx.get(key)} best_prior={b_ctx.get(key)}")
    if not deltas:
        return ""
    return (
        f"relation={comparison.get('relation')}; rows=candidate:{c_row},best_prior:{b_row}; "
        f"support_bbox={bbox}; candidate_ta=({cand.get('t')},{cand.get('action')}); "
        f"best_prior_ta=({best.get('t')},{best.get('action')}); "
        f"context_delta={' | '.join(deltas[:6])}"
    )


def _state_context_features(grid: Any, bbox: list[Any]) -> dict[str, Any]:
    r0, c0, r1, c1 = [int(x) for x in bbox]
    h = len(grid)
    w = len(grid[0]) if h else 0
    band_rows = range(max(0, r0 - 1), min(h, r1 + 2))
    band_cols = range(max(0, c0 - 4), min(w, c1 + 5))
    support_vals = []
    band_counts: dict[Any, int] = {}
    row_counts: dict[Any, int] = {}
    for r in range(max(0, r0), min(h, r1 + 1)):
        for c in range(max(0, c0), min(w, c1 + 1)):
            support_vals.append(grid[r][c])
    for r in band_rows:
        for c in band_cols:
            v = grid[r][c]
            band_counts[v] = band_counts.get(v, 0) + 1
    for r in range(max(0, r0), min(h, r1 + 1)):
        for c in range(w):
            v = grid[r][c]
            row_counts[v] = row_counts.get(v, 0) + 1
    return {
        "support_values": _sorted_counts(support_vals),
        "local_band_counts": _sorted_dict_counts(band_counts),
        "support_row_counts": _sorted_dict_counts(row_counts),
        "support_row_sections": [
            tuple(grid[r][min(band_cols):max(band_cols) + 1])
            for r in range(max(0, r0), min(h, r1 + 1))
        ] if band_cols else [],
    }


def _latest_counterexample_trace(project: Path) -> dict[str, Any]:
    payload = _read_json(project / "workspace" / "latest_patch_base_regression.json")
    trace = (
        payload.get("counterexample_trace")
        if isinstance(payload, dict) and isinstance(payload.get("counterexample_trace"), dict)
        else {}
    )
    return trace


def _trace_bbox(trace: dict[str, Any]) -> list[int]:
    sig = trace.get("first_mismatch_signature") if isinstance(trace.get("first_mismatch_signature"), dict) else {}
    bbox = sig.get("bbox") if isinstance(sig.get("bbox"), list) else []
    if len(bbox) != 4:
        classes = trace.get("mismatch_classes") if isinstance(trace.get("mismatch_classes"), list) else []
        if classes and isinstance(classes[0], dict):
            cls_sig = classes[0].get("signature") if isinstance(classes[0].get("signature"), dict) else {}
            bbox = cls_sig.get("bbox") if isinstance(cls_sig.get("bbox"), list) else []
    if len(bbox) != 4:
        return []
    try:
        return [int(v) for v in bbox]
    except Exception:
        return []


def _trace_first_row(trace: dict[str, Any]) -> int | None:
    classes = trace.get("mismatch_classes") if isinstance(trace.get("mismatch_classes"), list) else []
    if classes and isinstance(classes[0], dict):
        row = _as_int(classes[0].get("first_row"))
        if row is not None:
            return row
    return None


def _support_values(grid: Any, bbox: list[int]) -> tuple[Any, ...]:
    r0, c0, r1, c1 = [int(x) for x in bbox]
    return tuple(
        grid[r][c]
        for r in range(max(0, r0), min(len(grid), r1 + 1))
        for c in range(max(0, c0), min(len(grid[r]), c1 + 1))
    )


def _window_matches_label(
    grid: Any,
    row: int,
    col: int,
    height: int,
    width: int,
    label: tuple[Any, ...],
) -> bool:
    if len(label) != height * width:
        return False
    idx = 0
    for rr in range(row, row + height):
        row_vals = grid[rr]
        for cc in range(col, col + width):
            if row_vals[cc] != label[idx]:
                return False
            idx += 1
    return True


def _transition_alpha_features(grid: Any, bbox: list[int], *, action: int) -> dict[str, Any]:
    ctx = _state_context_features(grid, bbox)
    return {
        "action": action,
        "support_values": tuple(ctx.get("support_values") or ()),
        "local_band_counts": tuple(tuple(row) for row in (ctx.get("local_band_counts") or ())),
        "support_row_counts": tuple(tuple(row) for row in (ctx.get("support_row_counts") or ())),
        "support_row_sections": tuple(tuple(row) for row in (ctx.get("support_row_sections") or ())),
    }


def _lowerable_window_alpha_features(
    grid: Any,
    bbox: list[int],
    *,
    action: int,
    source_label: tuple[Any, ...],
) -> dict[str, Any]:
    ctx = _state_context_features(grid, bbox)
    return {
        "window_values": tuple(source_label),
        "action": action,
        "window_local_band_counts": tuple(
            tuple(row) for row in (ctx.get("local_band_counts") or ())
        ),
        "window_row_counts": tuple(
            tuple(row) for row in (ctx.get("support_row_counts") or ())
        ),
        "window_row_sections": tuple(
            tuple(row) for row in (ctx.get("support_row_sections") or ())
        ),
    }


def _global_selector_features(
    before_patch: Any,
    predicted_patch: Any,
    *,
    action: int | None,
    before: int,
    predicted: int,
    patch_row: int | None = None,
    patch_col: int | None = None,
    include_component_features: bool = False,
) -> dict[str, Any]:
    before_window = _patch_cell_window(before_patch, patch_row, patch_col)
    predicted_window = _patch_cell_window(predicted_patch, patch_row, patch_col)
    features = {
        "before_value": before,
        "predicted_value": predicted,
        "before_predicted_pair": (before, predicted),
        "action": action,
        "local_before_counts": tuple(tuple(row) for row in _patch_value_counts(before_patch)),
        "local_predicted_counts": tuple(tuple(row) for row in _patch_value_counts(predicted_patch)),
        "local_before_predicted_counts": (
            tuple(tuple(row) for row in _patch_value_counts(before_patch)),
            tuple(tuple(row) for row in _patch_value_counts(predicted_patch)),
        ),
    }
    if before_window is not None:
        features["cell_before_window"] = before_window
        features["cell_before_window_counts"] = tuple(
            tuple(row) for row in _patch_value_counts(before_window)
        )
    if predicted_window is not None:
        features["cell_predicted_window"] = predicted_window
        features["cell_predicted_window_counts"] = tuple(
            tuple(row) for row in _patch_value_counts(predicted_window)
        )
    if before_window is not None and predicted_window is not None:
        features["cell_before_predicted_window"] = (before_window, predicted_window)
    if include_component_features:
        for prefix, component in (
            ("before_component", _patch_component_features(before_patch, patch_row, patch_col)),
            ("predicted_component", _patch_component_features(predicted_patch, patch_row, patch_col)),
        ):
            if not component:
                continue
            for key, value in component.items():
                features[f"{prefix}_{key}"] = value
    return features


def _patch_relative_position(diff: dict[str, Any], bbox: list[Any]) -> tuple[int, int] | None:
    row = _as_int(diff.get("row", diff.get("y")))
    col = _as_int(diff.get("col", diff.get("x")))
    if row is None or col is None:
        return None
    if len(bbox) == 4:
        r0 = _as_int(bbox[0])
        c0 = _as_int(bbox[1])
        if r0 is not None and c0 is not None:
            return row - r0, col - c0
    return row, col


def _patch_cell_window(
    patch: Any,
    row: int | None,
    col: int | None,
    *,
    radius: int = 1,
) -> tuple[tuple[Any, ...], ...] | None:
    if row is None or col is None or not isinstance(patch, list):
        return None
    if row - radius < 0 or col - radius < 0:
        return None
    out: list[tuple[Any, ...]] = []
    for rr in range(row - radius, row + radius + 1):
        if rr < 0 or rr >= len(patch) or not isinstance(patch[rr], list):
            return None
        cells: list[Any] = []
        for cc in range(col - radius, col + radius + 1):
            if cc < 0 or cc >= len(patch[rr]):
                return None
            cells.append(patch[rr][cc])
        out.append(tuple(cells))
    return tuple(out)


def _patch_component_features(
    patch: Any,
    row: int | None,
    col: int | None,
) -> dict[str, Any]:
    if row is None or col is None or not isinstance(patch, list):
        return {}
    if row < 0 or row >= len(patch) or not isinstance(patch[row], list):
        return {}
    if col < 0 or col >= len(patch[row]):
        return {}
    value = patch[row][col]
    stack = [(row, col)]
    seen: set[tuple[int, int]] = set()
    while stack:
        rr, cc = stack.pop()
        if (rr, cc) in seen:
            continue
        if rr < 0 or rr >= len(patch) or not isinstance(patch[rr], list):
            continue
        if cc < 0 or cc >= len(patch[rr]) or patch[rr][cc] != value:
            continue
        seen.add((rr, cc))
        stack.extend(((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)))
    if not seen:
        return {}
    rows = [rr for rr, _ in seen]
    cols = [cc for _, cc in seen]
    r0, r1 = min(rows), max(rows)
    c0, c1 = min(cols), max(cols)
    return {
        "value": value,
        "size": len(seen),
        "bbox_shape": (r1 - r0 + 1, c1 - c0 + 1),
        "on_min_row": row == r0,
        "on_max_row": row == r1,
        "on_min_col": col == c0,
        "on_max_col": col == c1,
        "row_edge_pair": (row == r0, row == r1),
        "col_edge_pair": (col == c0, col == c1),
        "edge_count": int(row == r0) + int(row == r1) + int(col == c0) + int(col == c1),
    }


def _patch_value_counts(patch: Any) -> list[tuple[Any, int]]:
    values: list[Any] = []
    if isinstance(patch, (list, tuple)):
        for row in patch:
            if isinstance(row, (list, tuple)):
                values.extend(row)
    return _sorted_counts(values)


def _rank_global_selector_predicates(
    rows: list[dict[str, Any]],
    positive_rows: list[dict[str, Any]],
    *,
    rewrite: dict[str, Any],
    max_predicates: int,
) -> list[dict[str, Any]]:
    if not positive_rows:
        return []
    common: dict[str, set[Any]] = {}
    for key in positive_rows[0]["features"]:
        values = {row["features"].get(key) for row in positive_rows}
        if len(values) == 1:
            common[key] = values
    candidates: list[tuple[tuple[str, Any], ...]] = []
    preferred = (
        "before_predicted_pair",
        "before_value",
        "predicted_value",
        "cell_before_predicted_window",
        "cell_before_window",
        "cell_predicted_window",
        "cell_before_window_counts",
        "cell_predicted_window_counts",
        "before_component_col_edge_pair",
        "before_component_row_edge_pair",
        "before_component_on_min_col",
        "before_component_on_max_col",
        "predicted_component_col_edge_pair",
        "predicted_component_row_edge_pair",
        "predicted_component_on_min_col",
        "predicted_component_on_max_col",
        "predicted_component_edge_count",
        "local_before_counts",
        "local_predicted_counts",
    )
    for key in preferred:
        if key in common:
            candidates.append(((key, next(iter(common[key]))),))
    for keys in (
        ("before_predicted_pair", "cell_before_predicted_window"),
        ("before_predicted_pair", "cell_before_window"),
        ("before_predicted_pair", "cell_predicted_window"),
        ("before_predicted_pair", "cell_before_window_counts", "cell_predicted_window_counts"),
        ("before_predicted_pair", "predicted_component_on_min_col"),
        ("before_predicted_pair", "predicted_component_on_max_col"),
        ("before_predicted_pair", "predicted_component_col_edge_pair"),
        ("before_predicted_pair", "before_component_col_edge_pair"),
        ("before_value", "predicted_value", "predicted_component_on_min_col"),
        ("before_value", "predicted_value", "predicted_component_col_edge_pair"),
        ("before_predicted_pair", "local_before_counts"),
        ("before_predicted_pair", "local_predicted_counts"),
        ("before_value", "predicted_value", "local_before_counts"),
        ("action", "before_predicted_pair"),
    ):
        if all(key in common for key in keys):
            candidates.append(tuple((key, next(iter(common[key]))) for key in keys))
    seen: set[str] = set()
    scored: list[dict[str, Any]] = []
    for predicate in candidates:
        identity = json.dumps(predicate, sort_keys=True, default=str)
        if identity in seen:
            continue
        seen.add(identity)
        cm = _predicate_confusion(rows, predicate)
        lowering_scope, lowering_obligation = _global_selector_lowering_scope(predicate)
        scored.append(
            {
                "features": [
                    {"name": key, "value": value}
                    for key, value in predicate
                ],
                "rewrite": dict(rewrite),
                "confusion_matrix": cm,
                "complexity": len(predicate),
                "perfect_on_visible_receipt": cm["fp"] == 0 and cm["fn"] == 0,
                "lowering_scope": lowering_scope,
                "lowering_obligation": lowering_obligation,
            }
        )
    scored.sort(
        key=lambda row: (
            not row["perfect_on_visible_receipt"],
            row.get("lowering_scope") != "global_carrier_input",
            row["confusion_matrix"]["fp"],
            row["confusion_matrix"]["fn"],
            row["complexity"],
            -row["confusion_matrix"]["tp"],
        )
    )
    return scored


_GLOBAL_VALUE_FEATURES = frozenset(
    {"before_value", "predicted_value", "before_predicted_pair"}
)
_GLOBAL_CELL_CONTEXT_FEATURES = frozenset(
    {
        "cell_before_window",
        "cell_predicted_window",
        "cell_before_predicted_window",
        "cell_before_window_counts",
        "cell_predicted_window_counts",
    }
)
_GLOBAL_COMPONENT_CONTEXT_FEATURES = frozenset(
    {
        "before_component_value",
        "before_component_size",
        "before_component_bbox_shape",
        "before_component_on_min_row",
        "before_component_on_max_row",
        "before_component_on_min_col",
        "before_component_on_max_col",
        "before_component_row_edge_pair",
        "before_component_col_edge_pair",
        "before_component_edge_count",
        "predicted_component_value",
        "predicted_component_size",
        "predicted_component_bbox_shape",
        "predicted_component_on_min_row",
        "predicted_component_on_max_row",
        "predicted_component_on_min_col",
        "predicted_component_on_max_col",
        "predicted_component_row_edge_pair",
        "predicted_component_col_edge_pair",
        "predicted_component_edge_count",
    }
)
_GLOBAL_PATCH_CHART_FEATURES = frozenset(
    {
        "local_before_counts",
        "local_predicted_counts",
        "local_before_predicted_counts",
    }
)


def _global_selector_lowering_scope(
    predicate: tuple[tuple[str, Any], ...],
) -> tuple[str, str]:
    names = {key for key, _ in predicate}
    if (names & (_GLOBAL_CELL_CONTEXT_FEATURES | _GLOBAL_COMPONENT_CONTEXT_FEATURES)) and (
        names & _GLOBAL_VALUE_FEATURES
    ):
        return (
            "global_carrier_input",
            "lowerable by scanning carrier-visible per-cell context/component features; full "
            "replay/holdout must still validate adoption",
        )
    if names <= _GLOBAL_VALUE_FEATURES or not (
        names & (_GLOBAL_CELL_CONTEXT_FEATURES | _GLOBAL_COMPONENT_CONTEXT_FEATURES)
    ):
        if names & _GLOBAL_PATCH_CHART_FEATURES:
            return (
                "patch_chart_context_only",
                "patch-level counts separate this local chart but are not a "
                "per-cell carrier selector; request/refine a cell-local selector",
            )
        return (
            "value_class_only",
            "raw before/predicted values are rewrite labels, not sufficient "
            "global carrier selectors",
        )
    return (
        "context_without_value_class",
        "context must be paired with a value/rewrite class before lowering",
    )


def _rank_lowerable_window_predicates(
    rows: list[dict[str, Any]],
    positive_rows: list[dict[str, Any]],
    *,
    source_label: tuple[Any, ...],
    tn_extra: int,
    max_predicates: int,
) -> list[dict[str, Any]]:
    if not positive_rows:
        return []
    common: dict[str, set[Any]] = {}
    for key in positive_rows[0]["features"]:
        if key == "window_values":
            continue
        values = {row["features"].get(key) for row in positive_rows}
        if len(values) == 1:
            common[key] = values
    candidates: list[tuple[tuple[str, Any], ...]] = []
    for key, values in common.items():
        candidates.append(((key, next(iter(values))),))
    for keys in (
        ("action", "window_local_band_counts"),
        ("action", "window_row_counts"),
        ("action", "window_row_sections"),
        ("window_local_band_counts", "window_row_sections"),
        ("action", "window_local_band_counts", "window_row_sections"),
    ):
        if all(key in common for key in keys):
            candidates.append(tuple((key, next(iter(common[key]))) for key in keys))
    seen: set[str] = set()
    scored: list[dict[str, Any]] = []
    for predicate in candidates:
        identity = json.dumps(predicate, sort_keys=True, default=str)
        if identity in seen:
            continue
        seen.add(identity)
        cm = _predicate_confusion_same_source(rows, predicate, tn_extra=tn_extra)
        features = [{"name": "window_values", "value": source_label}]
        features.extend({"name": key, "value": value} for key, value in predicate)
        scored.append(
            {
                "features": features,
                "confusion_matrix": cm,
                "complexity": len(features),
                "perfect_on_visible_log": cm["fp"] == 0 and cm["fn"] == 0,
                "lowering_scope": "global_carrier_input",
                "lowering_obligation": "lowerable by scanning same-shaped visible windows",
            }
        )
    scored.sort(
        key=lambda row: (
            not row["perfect_on_visible_log"],
            row["confusion_matrix"]["fp"],
            row["confusion_matrix"]["fn"],
            row["complexity"],
            -row["confusion_matrix"]["tp"],
        )
    )
    return scored[:max_predicates]


def _rank_separating_predicates(
    rows: list[dict[str, Any]],
    positive_rows: list[dict[str, Any]],
    *,
    max_predicates: int,
) -> list[dict[str, Any]]:
    common: dict[str, set[Any]] = {}
    for key in positive_rows[0]["features"]:
        values = {row["features"].get(key) for row in positive_rows}
        if len(values) == 1:
            common[key] = values
    candidates: list[tuple[tuple[str, Any], ...]] = []
    for key, values in common.items():
        value = next(iter(values))
        candidates.append(((key, value),))
    for keys in (
        ("support_values", "local_band_counts"),
        ("support_values", "support_row_counts"),
        ("support_values", "support_row_sections"),
        ("action", "local_band_counts"),
        ("action", "support_values"),
    ):
        if all(key in common for key in keys):
            candidates.append(tuple((key, next(iter(common[key]))) for key in keys))
    seen: set[str] = set()
    scored: list[dict[str, Any]] = []
    for predicate in candidates:
        identity = json.dumps(predicate, sort_keys=True, default=str)
        if identity in seen:
            continue
        seen.add(identity)
        cm = _predicate_confusion(rows, predicate)
        scored.append(
            {
                "features": [
                    {"name": key, "value": value}
                    for key, value in predicate
                ],
                "confusion_matrix": cm,
                "complexity": len(predicate),
                "perfect_on_visible_log": cm["fp"] == 0 and cm["fn"] == 0,
            }
        )
    scored.sort(
        key=lambda row: (
            not row["perfect_on_visible_log"],
            row["confusion_matrix"]["fp"],
            row["confusion_matrix"]["fn"],
            row["complexity"],
            -row["confusion_matrix"]["tp"],
        )
    )
    return scored[:max_predicates]


_SUPPORT_CHART_FEATURES = frozenset(
    {
        "support_values",
        "local_band_counts",
        "support_row_counts",
        "support_row_sections",
    }
)


def _annotate_predicate_lowering_scope(row: dict[str, Any]) -> dict[str, Any]:
    features = row.get("features") if isinstance(row.get("features"), list) else []
    names = {
        str(feature.get("name") or "")
        for feature in features
        if isinstance(feature, dict)
    }
    annotated = dict(row)
    if names & _SUPPORT_CHART_FEATURES:
        annotated["lowering_scope"] = "quotient_chart_only"
        annotated["lowering_obligation"] = (
            "needs an independent selector for the support chart before it can "
            "be lowered to a global carrier guard"
        )
    else:
        annotated["lowering_scope"] = "global_carrier_input"
        annotated["lowering_obligation"] = "lowerable from carrier inputs"
    return annotated


def _predicate_confusion(
    rows: list[dict[str, Any]],
    predicate: tuple[tuple[str, Any], ...],
) -> dict[str, int]:
    tp = fp = fn = tn = 0
    for row in rows:
        pred = all(row["features"].get(key) == value for key, value in predicate)
        pos = bool(row["positive"])
        if pred and pos:
            tp += 1
        elif pred and not pos:
            fp += 1
        elif not pred and pos:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _predicate_confusion_same_source(
    rows: list[dict[str, Any]],
    predicate: tuple[tuple[str, Any], ...],
    *,
    tn_extra: int,
) -> dict[str, int]:
    cm = _predicate_confusion(rows, predicate)
    cm["tn"] += tn_extra
    return cm


def _compact_tuple(values: Any) -> str:
    if isinstance(values, tuple):
        return "(" + ",".join(str(v) for v in values) + ")"
    return str(values)


def _sorted_counts(values: list[Any]) -> list[tuple[Any, int]]:
    counts: dict[Any, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return _sorted_dict_counts(counts)


def _sorted_dict_counts(counts: dict[Any, int]) -> list[tuple[Any, int]]:
    return sorted(counts.items(), key=lambda item: (str(item[0]), item[1]))


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def _shaish(path: Path) -> str:
    try:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001
        return ""
