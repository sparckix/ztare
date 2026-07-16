from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ztare.common.candidate_memory import (
    admissible_candidate_memory_records,
    candidate_memory_source,
)
from ztare.common.patch_base_identity import (
    repair_frontier_fields,
    resolve_repair_frontier,
)
from ztare.common.projection_owner_registry import VISIBLE_WORKBENCH_SOURCE_FIBERS
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
            output_contract=[
                "candidate_evaluation_admissible",
                "repair_frontier_admissible",
                "candidate_promotion_authorized",
                "exact_rows_delta",
                "wrong_cells_delta",
                "holdout_depth_delta",
                "regressions",
            ],
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
                "Expose the full finite one-step behavior class around a regression, "
                "plus commuting transports through registered adapter operations, "
                "before falling back to state-context feature separation."
            ),
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["latest_eval_ref", "episode_log_ref", "quotient_comparison_ref"],
            output_contract=[
                "observation_sha256",
                "counterexample_observation",
                "diagnostic_summary",
                "behavioral_fiber",
                "patch_base_chain_effects",
                "commuting_transports",
            ],
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
                "admissibility_scope",
                "candidate_family_id",
                "candidate_family_admissible",
                "lowerability_status",
                "candidate_predicates",
                "conjecture_predicates",
                "identity_support",
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
                "admissibility_scope",
                "candidate_family_id",
                "candidate_family_admissible",
                "lowerability_status",
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

def render_worldmodel_leaf_workbench_prompt() -> str:
    return render_leaf_workbench_contract_prompt(WORLD_MODEL_LEAF_WORKBENCH_CONTRACT)


def worldmodel_workbench_task_identity_status(
    project_dir: str | Path,
    weakness_payload: Mapping[str, Any],
    task: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify a repair task by carrier ancestry and promotion authority.

    A visible retry frontier can lead the mutable project root before
    promotion, so root inequality cannot make the task stale.  Conversely, a
    promoted root that transitively contains that frontier has consumed the
    task's scientific obligation.  The conjunction prevents both errors:
    ancestry supplies composition identity; the champion gate receipt supplies
    acceptance authority.
    """

    project = Path(project_dir)
    bound_epoch = str(task.get("evidence_epoch_sha256") or "").strip().lower()
    if bound_epoch:
        try:
            from ztare.common.observation_chart import capture_project_evidence_epoch

            current_epoch = capture_project_evidence_epoch(project).epoch_sha256
        except (OSError, TypeError, ValueError):
            return {
                "active": False,
                "relation": "task_evidence_epoch_unavailable",
            }
        if current_epoch != bound_epoch:
            return {
                "active": False,
                "relation": "task_evidence_epoch_superseded",
                "task_evidence_epoch_sha256": bound_epoch,
                "current_evidence_epoch_sha256": current_epoch,
            }
    frontier = weakness_payload.get("active_frontier")
    frontier = frontier if isinstance(frontier, Mapping) else {}
    source_ref = str(
        task.get("source_ref") or frontier.get("source_ref") or ""
    ).strip()
    bound_sha = str(
        task.get("source_sha256")
        or frontier.get("candidate_sha")
        or weakness_payload.get("candidate_sha")
        or ""
    ).strip().lower()
    if not source_ref:
        return {"active": True, "relation": "task_source_unspecified"}

    try:
        from ztare.common.artifact_refs import resolve_project_artifact_ref

        task_path = resolve_project_artifact_ref(project, source_ref)
        if task_path is None or not task_path.is_file():
            return {"active": True, "relation": "task_source_unavailable"}
        task_sha = hashlib.sha256(task_path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return {"active": True, "relation": "task_source_unavailable"}

    if bound_sha and task_sha != bound_sha:
        return {"active": True, "relation": "task_source_identity_mismatch"}

    root_path = project / "test_model.py"
    try:
        root_sha = hashlib.sha256(root_path.read_bytes()).hexdigest()
    except OSError:
        return {"active": True, "relation": "project_root_unavailable"}
    if root_sha == task_sha:
        return {"active": True, "relation": "task_frontier_is_project_root"}

    try:
        from ztare.worldmodel.patch_base_carrier import resolved_patch_base_paths

        ancestors = resolved_patch_base_paths(
            root_path.resolve(),
            project_dir=project,
        )
        frontier_is_ancestor = task_path.resolve() in {
            path.resolve() for path in ancestors
        }
    except (OSError, TypeError, ValueError):
        frontier_is_ancestor = False
    if not frontier_is_ancestor:
        return {"active": True, "relation": "task_frontier_not_consumed"}

    champion = _read_json(project / "champion_eval_results.json")
    champion = champion if isinstance(champion, Mapping) else {}
    gate = champion.get("pre_judge_gate_payload")
    gate = gate if isinstance(gate, Mapping) else {}
    decision = gate.get("pre_judge_decision")
    decision = decision if isinstance(decision, Mapping) else {}
    gated_sha = str(gate.get("gated_sha256") or "").strip().lower()
    decision_sha = str(decision.get("candidate_sha") or "").strip().lower()
    root_is_promoted = bool(
        champion.get("artifact_role") == "champion"
        and decision.get("candidate_promotion_authorized") is True
        and decision.get("gate_contract_closed") is True
        and gated_sha
        and root_sha == gated_sha
        and (not decision_sha or root_sha == decision_sha)
    )
    if not root_is_promoted:
        return {"active": True, "relation": "successor_not_promotion_bound"}
    return {
        "active": False,
        "relation": "promoted_successor_contains_task_frontier",
        "task_sha256": task_sha,
        "successor_sha256": root_sha,
    }


def worldmodel_leaf_workbench_action_environment() -> dict[str, Any]:
    """Return the substrate adapter for generic leaf-workbench action dispatch."""
    # The visible workbench stages the route registry but deliberately omits
    # authority-only Strategy executors.  Optional parameter-domain metadata
    # must therefore not decide whether the adapter's action identities exist.
    # The parent-kernel handler validates the command again before execution.
    try:
        from ztare.worldmodel.strategy_gate_actions import registered_strategy_gate_actions

        strategy_gate_commands = tuple(sorted(registered_strategy_gate_actions()))
    except ModuleNotFoundError:
        strategy_gate_commands = ()

    return {
        "contract": WORLD_MODEL_LEAF_WORKBENCH_CONTRACT,
        "records_fn": worldmodel_leaf_workbench_records,
        "task_identity_status_fn": worldmodel_workbench_task_identity_status,
        "action_parameter_domains": (
            {
                "run_strategy_required_gate": {
                    "input_refs.command": strategy_gate_commands,
                },
            }
            if strategy_gate_commands
            else {}
        ),
        "local_cli_actions": {
            "inspect_worldmodel_event_timeline",
            "contrast_worldmodel_episodes",
            "run_worldmodel_evidence_probe",
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
    # The observation identity is the canonical visible bank, not whichever
    # episode filename sorts last.  Evaluation/holdout episodes are different
    # evidence roles and may not silently replace the bank that owns a residual.
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
    output_summary = run_worldmodel_counterexample_context_probe(
        project_dir,
        regression_ref=regression_ref,
    )
    try:
        summary_payload = json.loads(output_summary)
    except (TypeError, ValueError):
        summary_payload = {}
    observation_sha = str(summary_payload.get("observation_sha256") or "").strip()
    return {
        "input_hashes": {
            "source_ref": f"{regression_ref}:candidate_regression_receipt",
            "latest_regression_ref": regression_ref,
            "latest_regression_sha256": _shaish(project / regression_ref),
            "request": _short_receipt_json(req),
        },
        "output_summary": output_summary,
        # The adapter describes a possible operational production; only the
        # common parent executor may admit it after stamping the immutable
        # kernel receipt and verifying an active task identity.  Out-of-loop
        # probes therefore remain diagnostic.
        **(
            {
                "_route_production": {
                    "schema_id": "ztare-counterexample-observation-triple-v1",
                    "event": "materialized",
                    "join_values": {"observation_sha256": observation_sha},
                    "payload": {
                        "observation_ref": (
                            summary_payload.get("counterexample_observation", {}).get(
                                "observation_ref"
                            )
                            if isinstance(
                                summary_payload.get("counterexample_observation"), dict
                            )
                            else ""
                        ),
                        "regression_ref": regression_ref,
                    },
                }
            }
            if observation_sha
            else {}
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
            "upstream_receipt_refs": list(
                input_refs.get("upstream_receipt_refs") or ()
            ),
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
        upstream_receipt_refs=tuple(
            str(ref)
            for ref in (input_refs.get("upstream_receipt_refs") or ())
            if str(ref).strip()
        ),
    )
    return {
        "input_hashes": {
            "latest_regression_ref": regression_ref,
            "latest_regression_sha256": _shaish(project / regression_ref),
            "episode_log_ref": episode_ref,
            "episode_log_sha256": _shaish(project / episode_ref),
            "upstream_receipt_refs": list(
                input_refs.get("upstream_receipt_refs") or ()
            ),
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


def score_worldmodel_candidate_delta(
    project_dir: str | Path,
    candidate_path: str | Path,
    *,
    candidate_sha256: str = "",
    include_diagnostics: bool = False,
    workspace_cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Score one candidate through the registered project verifier.

    This is the single semantic door used by both the parent workbench action
    and the staged CLI.  A passing preflight establishes that the candidate is
    evaluable and may occupy the repair frontier; it does not mint promotion
    authority.  That later edge belongs to the governed pre-judge consumer.
    """
    from ztare.validator.core.pre_judge_gate import detect_patch_base_regression_preflight

    project = Path(project_dir)
    path = Path(candidate_path)
    candidate_sha = candidate_sha256 or _shaish(path)
    result = detect_patch_base_regression_preflight(
        enabled=True,
        project_dir=project,
        candidate_path=path,
        workspace_cache_dir=workspace_cache_dir,
    )
    authority = {
        "admissibility_scope": "candidate",
        "candidate_sha256": candidate_sha,
        "candidate_promotion_authorized": False,
        "promotion_authority": "parent_pre_judge_only",
    }
    if result is None:
        return {
            "schema": "ztare-worldmodel-candidate-delta-score-v1",
            "status": "candidate_preflight_passed",
            "candidate_relation": "no_regression_detected",
            "candidate_evaluation_admissible": True,
            "repair_frontier_admissible": True,
            # Compatibility projection: this means that at least one executable
            # delta exists, not that the parent may promote it.
            "candidate_delta_admissible": True,
            **authority,
        }

    receipt = result.regression_receipt
    trace = result.counterexample_trace
    summary: dict[str, Any] = {
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
            trace.get("holdout_witness")
            if isinstance(trace, dict) and isinstance(trace.get("holdout_witness"), dict)
            else {}
        ),
        "quotient_relation": (
            receipt.get("quotient_comparison", {}).get("relation")
            if isinstance(receipt.get("quotient_comparison"), dict)
            else ""
        ),
        "candidate_evaluation_admissible": False,
        "repair_frontier_admissible": False,
        "candidate_delta_admissible": False,
        **authority,
    }
    if include_diagnostics:
        summary["candidate_regression_receipt"] = receipt
        summary["counterexample_trace"] = trace
    return summary


def _handle_score_worldmodel_candidate_delta_action(
    project_dir: str | Path,
    req: dict[str, Any],
    _row: dict[str, Any] | None,
    _contract: LeafWorkbenchContract,
) -> dict[str, Any]:
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

    candidate_sha = _shaish(candidate_path)
    payload = score_worldmodel_candidate_delta(
        project,
        candidate_path,
        candidate_sha256=candidate_sha,
    )
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


def _active_task_first_fire_payload(
    project_dir: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_first_fire_receipt,
    )

    receipt = active_workbench_task_first_fire_receipt(project_dir)
    if not isinstance(receipt, dict):
        return {}, {}
    summary: object = receipt.get("output_summary")
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except json.JSONDecodeError:
            summary = {"diagnostic_summary": summary}
    return receipt, summary if isinstance(summary, dict) else {}


def _render_active_task_first_fire_fragment(project_dir: str | Path) -> str:
    """Render the selected task's consumed receipt before the broad menu."""

    receipt, summary = _active_task_first_fire_payload(project_dir)
    if not receipt:
        return ""
    weakness = _read_json(Path(project_dir) / "workspace" / "latest_harness_weakness.json")
    task = weakness.get("workbench_task") if isinstance(weakness, dict) else {}
    task = task if isinstance(task, dict) else {}
    input_hashes = receipt.get("input_hashes")
    input_hashes = input_hashes if isinstance(input_hashes, dict) else {}
    lines = [
        "## Active workbench task — parent first-fire receipt",
        f"- task identity: {task.get('task_id')}; failure class: {task.get('failure_class')}",
        f"- selected capability already executed by kernel: {receipt.get('capability_id')}",
        f"- receipt ref: {input_hashes.get('kernel_receipt_ref')}; observation identity: {summary.get('observation_sha256')}",
    ]
    candidates = summary.get("catalog_residual_event_candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict) else {}
    if candidate:
        from ztare.worldmodel.retry_surface import (
            compact_catalog_residual_event_candidate,
        )

        compact = compact_catalog_residual_event_candidate(candidate)
        identity = compact.get("operation_identity")
        identity = identity if isinstance(identity, dict) else {}
        role = compact.get("role_evidence")
        role = role if isinstance(role, dict) else {}
        lowering = compact.get("lowering")
        lowering = lowering if isinstance(lowering, dict) else {}
        displacements = ", ".join(
            f"dr={row[0]},dc={row[1]}"
            for row in (role.get("displacements") or [])
            if isinstance(row, (list, tuple)) and len(row) == 2
        )
        interventions = ",".join(str(row) for row in (role.get("interventions") or []))
        write_runs = ", ".join(
            f"value={write.get('value')} "
            + ";".join(
                f"r{run[0]}:c{run[1]}-{run[2]}"
                for run in (write.get("row_col_runs") or [])
                if isinstance(run, (list, tuple)) and len(run) == 3
            )
            for write in (lowering.get("writes") or [])
            if isinstance(write, dict)
        )
        rect = lowering.get("rect") or []
        rect_text = ",".join(str(value) for value in rect)
        mover = ",".join(str(value) for value in (lowering.get("mover_colors") or []))
        from ztare.worldmodel.spec_catalog import render_region_event_contract

        identity_text = json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        lines.extend(
            [
                "- catalog operation identity: "
                f"{identity_text}; identity sha={compact.get('operation_identity_sha256')}; "
                f"status={compact.get('identity_status')}",
                f"- role evidence: support={role.get('support_count')}; interventions={interventions}; displacements={displacements}",
                f"- adapter lowering: mover values={mover}; trigger rect={rect_text}; edge={lowering.get('edge')}; writes={write_runs}",
                f"- catalog edge contract: {render_region_event_contract()}",
                "- authority: diagnostic candidate only. Coordinates and palette values lower the operation identity; replay, holdout, and promotion gates retain authority.",
            ]
        )
    else:
        lines.append(
            "- diagnostic consequence: "
            + str(summary.get("diagnostic_summary") or "receipt contains no compact event candidate")[:900]
        )
    source_ref = str(task.get("source_ref") or "").strip()
    source_sha = _shaish(Path(project_dir) / source_ref) if source_ref else ""
    lines.extend(
        [
            f"- active patch-base identity: source_ref={source_ref}; sha256={source_sha}",
            f"- {patch_carrier_brief_line()} Preserve the referenced carrier identity while proposing the smallest relation-level delta.",
            "- Full action registry and submission shapes remain in WORKBENCH_TOOLS.md; do not spend a turn re-requesting the receipt above.",
        ]
    )
    return "\n".join(lines) + "\n"


def worldmodel_leaf_workbench_records(project_dir: str | Path) -> list[dict[str, Any]]:
    project = Path(project_dir)
    workspace = project / "workspace"
    records: list[dict[str, Any]] = []
    surface = _read_active_surface_audit(workspace / "stale_surface_audit.json")
    candidate = _best_candidate_memory_record(workspace / "candidate_memory.json")
    # Task applicability has one identity owner.  In particular, a dominating
    # retry frontier may be active before it is promoted to test_model.py or
    # ranked first in candidate memory.  Re-checking the task against either
    # of those projections here used to erase its structured receipt while the
    # prose fragment still rendered it, leaving the route ledger open.
    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
    )

    task_scope, scoped_task = active_workbench_task_capability_scope(project)
    workbench_task = scoped_task if task_scope else None
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
        first_fire, first_fire_summary = _active_task_first_fire_payload(project)
        if first_fire:
            hashes = first_fire.get("input_hashes")
            hashes = hashes if isinstance(hashes, dict) else {}
            event_rows = first_fire_summary.get("catalog_residual_event_candidates")
            event = (
                event_rows[0]
                if isinstance(event_rows, list)
                and event_rows
                and isinstance(event_rows[0], dict)
                else {}
            )
            consumer_projection: dict[str, Any] = {
                "task_id": str(workbench_task.get("task_id") or ""),
                "observation_sha256": str(
                    first_fire_summary.get("observation_sha256") or ""
                ),
            }
            if event:
                from ztare.worldmodel.retry_surface import (
                    compact_catalog_residual_event_candidate,
                )

                compact_event = compact_catalog_residual_event_candidate(event)
                role_evidence = compact_event.get("role_evidence")
                role_evidence = (
                    role_evidence if isinstance(role_evidence, dict) else {}
                )
                consumer_projection.update(
                    {
                        "operation_identity": compact_event.get(
                            "operation_identity"
                        ),
                        "operation_identity_sha256": compact_event.get(
                            "operation_identity_sha256"
                        ),
                        "role_evidence": {
                            key: role_evidence.get(key)
                            for key in (
                                "role",
                                "source_operation",
                                "support_count",
                                "interventions",
                                "displacements",
                            )
                            if role_evidence.get(key) is not None
                        },
                        "lowering": compact_event.get("lowering"),
                        "authority": compact_event.get("authority"),
                        "promotion_authorized": bool(
                            compact_event.get("promotion_authorized")
                        ),
                    }
                )
            records.append(
                {
                    "source_type": "leaf_workbench_kernel_receipt",
                    "record_role": "active_task_first_fire",
                    "capability_id": str(first_fire.get("capability_id") or ""),
                    "source_ref": str(hashes.get("kernel_receipt_ref") or ""),
                    "source_sha": str(hashes.get("kernel_receipt_sha256") or ""),
                    # Canonical decision-sufficient projection.  The common
                    # workbench renderer transports this object opaquely; the
                    # adapter owns its vocabulary and lowering semantics.
                    "consumer_projection": consumer_projection,
                    # Generic synthesis-admission envelope.  Rendering only
                    # transports it; the invoked synthesis endpoint emits the
                    # downstream first-fire event.
                    **(
                        {
                            "route_delivery": {
                                "schema_id": "ztare-counterexample-observation-triple-v1",
                                "event": "delivered_to_synthesis_prompt",
                                "join_values": {
                                    "observation_sha256": str(
                                        consumer_projection.get("observation_sha256")
                                    ),
                                    "task_id": str(
                                        consumer_projection.get("task_id")
                                    ),
                                },
                                "render_anchors": [
                                    str(consumer_projection.get("observation_sha256"))
                                ],
                            }
                        }
                        if consumer_projection.get("observation_sha256")
                        else {}
                    ),
                    "summary": (
                        "parent-executed active-task receipt; "
                        "consume the typed projection before proposing a delta"
                    ),
                }
            )

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
        # Candidate memory is already filtered to one admissible carrier on the
        # strongest evidence epoch.  Prefer that bound consequence over any
        # filename-latest projection left by a prior carrier.
        quotient = _extract_residual_quotient(
            candidate.get("counterexample_trace") if candidate else None
        )
        if candidate and quotient:
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "inspect_replay_residual_quotient",
                    "source_ref": "workspace/candidate_memory.json:active_evidence_view",
                    "source_sha": str(candidate.get("sha") or ""),
                    "summary": quotient,
                }
            )
        else:
            diag_path = project / "latest_eval_results.json"
            diag = _read_json(diag_path)
            quotient = (
                _extract_residual_quotient(diag)
                if _payload_matches_active_candidate(project, diag, candidate)
                else ""
            )
            # A project with no selected carrier may still expose an explicit
            # diagnostics artifact for inspection.  Once a carrier identity
            # exists, unbound filename-latest diagnostics are ineligible.
            if not quotient and candidate is None:
                fallback_path = workspace / "latest_replay_diagnostics_after_abduce.json"
                fallback = _read_json(fallback_path)
                fallback_quotient = _extract_residual_quotient(fallback)
                if fallback_quotient:
                    diag_path, quotient = fallback_path, fallback_quotient
            if quotient:
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
        active_sha = str((candidate or {}).get("sha") or "").strip()
        candidate_sha = str(regression.get("candidate_sha") or "").strip()
        best_prior_sha = str(regression.get("best_prior_sha") or "").strip()
        regression_role = (
            "active_carrier_vs_prior"
            if active_sha and _sha_prefix_matches(active_sha, candidate_sha)
            else (
                "latest_failed_candidate_vs_active_carrier"
                if active_sha and _sha_prefix_matches(active_sha, best_prior_sha)
                else "historical_candidate_comparison"
            )
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
            records.append(
                {
                    "source_type": "leaf_workbench_capability",
                    "capability_id": "inspect_worldmodel_counterexample_context",
                    "source_ref": f"{regression_ref}:candidate_regression_receipt",
                    "summary": (
                        "available on request: joins the active counterexample "
                        "observation, its observed behavior class, registered "
                        "transports, and PATCH_BASE layer effects"
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
    active_fragment = _render_active_task_first_fire_fragment(project_dir)
    if active_fragment:
        return active_fragment
    records = worldmodel_leaf_workbench_records(project_dir)
    task_rows = [row for row in records if row.get("source_type") == "leaf_workbench_task"]
    other_rows = [
        row
        for row in records
        if row.get("source_type") != "leaf_workbench_task"
    ]
    candidate_bound_requests = _candidate_bound_action_requests(records)
    diagnostic_requests = _strategy_diagnostic_action_requests(records, project_dir)
    from ztare.common.worldmodel_carrier_purity import project_dynamics_assumption

    _da = project_dynamics_assumption(project_dir)
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
        *(
            [
                "- current diagnostic action request(s):",
                *[
                    "  - "
                    + json.dumps(
                        request,
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    )
                    for request in diagnostic_requests
                ],
            ]
            if diagnostic_requests
            else []
        ),
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
    for ref, purpose in VISIBLE_WORKBENCH_SOURCE_FIBERS:
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


def _strategy_diagnostic_action_requests(
    records: list[dict[str, Any]],
    project_dir: str | Path,
) -> list[dict[str, Any]]:
    """Return diagnostic morphisms selected by open Strategy-card receipts."""

    requests: list[dict[str, Any]] = []
    seen: set[str] = set()
    has_global_selector = any(
        str(row.get("capability_id") or "")
        == "mine_worldmodel_global_carrier_selectors_from_observable_context"
        and str(row.get("source_ref") or "") == "workspace/latest_level_transfer_probe.json"
        for row in records
    )
    if not has_global_selector:
        return requests[:3]
    try:
        from ztare.common.strategy_card_roles import active_strategy_cards

        cards = active_strategy_cards(
            Path(project_dir) / "workspace" / "strategy_experiments.jsonl"
        )
    except Exception:  # noqa: BLE001
        return requests[:3]
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
    _current, current_ref = _current_regression_receipt(project)
    if _current is not None:
        return current_ref
    return _latest_visible_candidate_score_ref(project) or "workspace/latest_patch_base_regression.json"


def _ref_has_regression_payload(project: Path, ref: str) -> bool:
    payload, _path = _read_regression_payload(project, ref)
    receipt = _regression_receipt_from_payload(project, payload)
    if not isinstance(receipt, dict):
        return False
    comparison = receipt.get("quotient_comparison")
    if not isinstance(comparison, dict):
        return False
    frontier = repair_frontier_fields(receipt)
    quotient_key = (
        "best_prior_top_quotient"
        if frontier["role"] == "best_admissible_prior"
        else "candidate_top_quotient"
    )
    quotient = comparison.get(quotient_key)
    bbox = quotient.get("bbox") if isinstance(quotient, dict) else None
    if (
        not isinstance(quotient, dict)
        or _as_int(quotient.get("first_row")) is None
        or not isinstance(bbox, list)
        or len(bbox) != 4
    ):
        return False
    try:
        resolve_repair_frontier(project, receipt)
    except (OSError, TypeError, ValueError):
        return False
    return True


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
    from ztare.worldmodel.stale_surface_audit import (
        stale_surface_receipt_is_current,
    )

    project = path.parent.parent
    if not stale_surface_receipt_is_current(project, payload):
        return {}
    return payload


def _sha_prefix_matches(left: str, right: str) -> bool:
    left = str(left or "").strip()
    right = str(right or "").strip()
    return bool(left and right and (left.startswith(right) or right.startswith(left)))


def _payload_matches_active_candidate(
    project: Path,
    payload: object,
    candidate: dict[str, Any] | None,
) -> bool:
    if not isinstance(payload, dict):
        return False
    trace = (
        payload.get("counterexample_trace")
        if isinstance(payload.get("counterexample_trace"), dict)
        else payload
    )
    gated_sha = str(trace.get("gated_sha256") or payload.get("gated_sha256") or "")
    try:
        root_sha = hashlib.sha256((project / "test_model.py").read_bytes()).hexdigest()
    except OSError:
        root_sha = ""
    candidate_sha = str((candidate or {}).get("sha") or "")
    active_sha = root_sha or candidate_sha
    return _sha_prefix_matches(active_sha, gated_sha)


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


def _regression_payload_is_current(project: Path, payload: object) -> bool:
    """Reject a pinned repair receipt after the active evidence epoch moves."""
    if not isinstance(payload, dict):
        return False
    epoch = payload.get("evidence_epoch")
    if not isinstance(epoch, dict):
        return True  # legacy unpinned diagnostics retain diagnostic authority
    expected = str(epoch.get("epoch_sha256") or "").strip()
    if not expected:
        return True
    try:
        from ztare.common.observation_chart import capture_project_evidence_epoch

        current = capture_project_evidence_epoch(project)
    except Exception:  # noqa: BLE001 - unavailable epoch checks fail closed
        return False
    return current.epoch_sha256 == expected


def _candidate_outcome_from_counterexample_trace(
    project: Path,
    payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Lower a gate counterexample into the existing candidate-observation input.

    A prior-carrier comparison is optional.  The evaluated carrier, transition
    witness, and observed consequence are sufficient to construct the
    chart-bound observation consumed by candidate synthesis.
    """

    trace = payload.get("counterexample_trace")
    if not isinstance(trace, dict):
        return None
    classes = trace.get("mismatch_classes")
    top = classes[0] if isinstance(classes, list) and classes else None
    if not isinstance(top, dict):
        return None
    signature = top.get("signature") if isinstance(top.get("signature"), dict) else {}
    bbox = signature.get("bbox") if isinstance(signature.get("bbox"), list) else []
    if _as_int(top.get("first_row")) is None or len(bbox) != 4:
        return None
    candidate_sha = str(trace.get("gated_sha256") or "").strip()
    candidate_ref = str(trace.get("gated_file") or "").strip()
    if candidate_ref:
        try:
            candidate_ref = str(Path(candidate_ref).resolve().relative_to(project.resolve()))
        except (OSError, ValueError):
            pass
    if not candidate_sha and not candidate_ref:
        return None
    quotient = {
        "count": top.get("count"),
        "first_row": top.get("first_row"),
        "t": top.get("t"),
        "action": top.get("action"),
        "bbox": bbox,
        "pair_counts": signature.get("pair_counts") or [],
        "coordinate_contract": trace.get("coordinate_contract") or {},
    }
    return {
        "schema": "ztare-candidate-gate-observation-v1",
        "candidate_relation": "hard_gate_failure",
        "candidate_sha": candidate_sha,
        "candidate_submission": candidate_ref,
        "candidate_exact_rows": trace.get("exact_rows"),
        "candidate_wrong_cells": trace.get("wrong_cell_count"),
        "first_mismatch": trace.get("first_mismatch"),
        "counterexample_trace": dict(trace),
        "quotient_comparison": {
            "schema": "ztare-regression-quotient-comparison-v1",
            "relation": "candidate_residual_only",
            "candidate_top_quotient": quotient,
            "best_prior_top_quotient": {},
        },
    }


def _regression_receipt_from_payload(
    project: Path,
    payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Normalize every supported gate payload through one consumer door."""
    if not _regression_payload_is_current(project, payload):
        return None
    receipt = payload.get("candidate_regression_receipt")
    if isinstance(receipt, dict):
        carried = dict(receipt)
        trace = payload.get("counterexample_trace")
        if isinstance(trace, dict):
            carried.setdefault("counterexample_trace", dict(trace))
            # Some scorers can compare the candidate only to itself.  They
            # still emit a complete typed counterexample trace, but leave the
            # comparison quotient empty.  Treating the empty comparison as
            # authoritative erases the witness at this normalization door.
            comparison = carried.get("quotient_comparison")
            comparison = comparison if isinstance(comparison, dict) else {}
            candidate_quotient = comparison.get("candidate_top_quotient")
            if not isinstance(candidate_quotient, dict) or not candidate_quotient:
                trace_outcome = _candidate_outcome_from_counterexample_trace(
                    project,
                    {"counterexample_trace": trace},
                )
                if trace_outcome is not None:
                    carried["quotient_comparison"] = trace_outcome[
                        "quotient_comparison"
                    ]
                    for key in (
                        "candidate_sha",
                        "candidate_submission",
                        "candidate_exact_rows",
                        "candidate_wrong_cells",
                        "first_mismatch",
                    ):
                        if carried.get(key) in (None, ""):
                            carried[key] = trace_outcome.get(key)
        return carried
    return _candidate_outcome_from_counterexample_trace(project, payload)


def _current_regression_receipt(project: Path) -> tuple[dict[str, Any] | None, str]:
    for rel in (
        "workspace/latest_patch_base_regression.json",
        "latest_eval_results.json",
    ):
        payload, _path = _read_regression_payload(project, rel)
        receipt = _regression_receipt_from_payload(project, payload)
        if receipt:
            return receipt, rel
    return None, "latest_eval_results.json"


def run_worldmodel_counterexample_context_probe(
    project_dir: str | Path,
    *,
    regression_ref: str = "",
) -> str:
    """Compute a typed counterexample observation on explicit request."""
    project = Path(project_dir)
    if regression_ref:
        payload, _path = _read_regression_payload(project, regression_ref)
        regression = _regression_receipt_from_payload(project, payload)
    else:
        regression, regression_ref = _current_regression_receipt(project)
    if not regression:
        raise ValueError(
            f"{regression_ref} has no candidate comparison or gate counterexample identity"
        )
    pair = _counterexample_comparison_pair(project, regression)
    summary = _counterexample_context_summary(project, regression, pair=pair)
    behavioral_fiber = (
        pair.get("behavioral_fiber")
        if isinstance(pair, dict) and isinstance(pair.get("behavioral_fiber"), dict)
        else {}
    )
    commuting_transports = _observed_commuting_catalog_transports(
        project,
        regression,
        pair=pair,
    )
    patch_base_chain_effects = (
        _patch_base_chain_effects(
            project,
            regression,
            pair=pair,
        )
        if pair
        else {}
    )
    if patch_base_chain_effects:
        summary += (
            f"; patch_base_chain_layers={patch_base_chain_effects.get('layer_count')}; "
            "chain_relation="
            f"{patch_base_chain_effects.get('observed_chain_relation')}"
        )
    observation = _active_frontier_observation_triple(project, regression)
    if not summary and observation:
        proposal = observation.get("proposal_identity")
        proposal = proposal if isinstance(proposal, dict) else {}
        summary = (
            "relation=candidate_residual_only; "
            f"observation_ref={observation.get('observation_ref')}; "
            f"carrier_sha={proposal.get('carrier_sha')}; "
            f"intervention={observation.get('intervention')}; "
            f"chart={observation.get('observation_chart', {}).get('chart_id') if isinstance(observation.get('observation_chart'), dict) else ''}"
        )
    if not summary and commuting_transports:
        summary = (
            "relation=observed_commuting_transport; "
            f"transport_count={len(commuting_transports)}; "
            "authority=diagnostic_finite_witness"
        )
    if not summary:
        raise ValueError("no candidate counterexample context is available")
    payload = {
        "schema": "ztare-counterexample-context-observation-v1",
        "diagnostic_summary": summary,
        "commuting_transports": commuting_transports,
    }
    if behavioral_fiber:
        payload["behavioral_fiber"] = behavioral_fiber
    if patch_base_chain_effects:
        payload["patch_base_chain_effects"] = patch_base_chain_effects
    if observation:
        payload.update(
            {
                "observation_sha256": observation["observation_sha256"],
                "counterexample_observation": observation,
            }
        )
        event_candidates = observation.get("catalog_residual_event_candidates")
        if isinstance(event_candidates, list) and event_candidates:
            payload["catalog_residual_event_candidates"] = event_candidates
            summary += (
                "; catalog_event_candidates="
                f"{len(event_candidates)}; relation=role_entry_to_remote_consequence"
            )
            payload["diagnostic_summary"] = summary
    else:
        payload["observation_status"] = "proposal_identity_unavailable"
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


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
        from ztare.worldmodel.episode_log import (
            EpisodeIdentityBindingError,
            EpisodeLog,
            declared_episode_observation_chart,
        )

        from ztare.worldmodel.evidence_quotients import resolve_episode_ref

        log = EpisodeLog.read_jsonl(resolve_episode_ref(project, episode_ref))
        transitions = log.transitions()
        from ztare.worldmodel.gates import env_frame_indices

        excluded_transition_indices = env_frame_indices(log)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"could not read episode log for feature mining: {episode_ref}") from exc
    if first_row < 0 or first_row >= len(transitions):
        raise ValueError("counterexample representative row is outside the episode log")
    target_label = _support_values(transitions[first_row].s_next, bbox)
    source_label = _support_values(transitions[first_row].s, bbox)
    rows: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    for idx, tr in enumerate(transitions):
        if idx in excluded_transition_indices:
            continue
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
        "excluded_transition_count": len(excluded_transition_indices),
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


def _task_bound_upstream_receipts(
    project: Path,
    refs: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    """Read prior kernel receipts without falling through to mutable "latest".

    The common executor owns morphism ordering.  This adapter door verifies
    that every carried receipt belongs to one task before exposing its typed
    output to an adapter-specific consumer.  A path existing is insufficient:
    the downstream consumer must be able to parse the kernel envelope and its
    output summary.
    """

    if not refs:
        return {}
    from ztare.common.artifact_refs import resolve_project_artifact_ref

    expected_task_id = ""
    outputs: dict[str, dict[str, Any]] = {}
    for raw_ref in refs:
        ref = str(raw_ref or "").strip()
        if not ref:
            continue
        path = resolve_project_artifact_ref(project, ref)
        if path is None or not path.is_file():
            raise ValueError(f"upstream kernel receipt is unavailable: {ref}")
        try:
            raw = path.read_bytes()
            artifact = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"upstream kernel receipt is not readable JSON: {ref}") from exc
        if not isinstance(artifact, dict) or artifact.get("schema") != (
            "ztare-leaf-workbench-kernel-receipt-v1"
        ):
            raise ValueError(f"upstream ref is not a kernel receipt: {ref}")
        request = artifact.get("request")
        input_refs = (
            request.get("input_refs") if isinstance(request, dict) else None
        )
        task_id = str(
            input_refs.get("task_id") if isinstance(input_refs, dict) else ""
        ).strip()
        if not task_id:
            raise ValueError(f"upstream kernel receipt has no task identity: {ref}")
        if expected_task_id and task_id != expected_task_id:
            raise ValueError("upstream kernel receipts cross task identities")
        expected_task_id = task_id
        receipt = artifact.get("receipt")
        if not isinstance(receipt, dict):
            raise ValueError(f"upstream kernel receipt has no typed payload: {ref}")
        capability_id = str(
            artifact.get("capability_id") or receipt.get("capability_id") or ""
        ).strip()
        summary = receipt.get("output_summary")
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"upstream output is not consumer-readable JSON: {ref}"
                ) from exc
        if not capability_id or not isinstance(summary, dict):
            raise ValueError(f"upstream kernel receipt has no typed output: {ref}")
        outputs[capability_id] = {
            "task_id": task_id,
            "ref": str(path.relative_to(project.resolve())),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "summary": summary,
        }
    return outputs


def _mine_task_operation_domain_selector(
    project: Path,
    *,
    context: Mapping[str, Any],
    episode_ref: str,
    max_margin: int,
) -> dict[str, Any] | None:
    """Refine a task-carried operation by its visible observation domain.

    This is an interactive-grid adapter lowering.  The common workbench sees
    only task, operation, and receipt identities.  Coordinates and exact local
    windows stay here and are emitted as a presentation guard, never folded
    into the operation identity.
    """

    summary = context.get("summary")
    if not isinstance(summary, Mapping):
        return None
    events = summary.get("catalog_residual_event_candidates")
    event = next(
        (
            row
            for row in (events if isinstance(events, list) else [])
            if isinstance(row, Mapping)
            and row.get("identity_status")
            in {
                "catalog_operation_reuse_candidate",
                "operation_recurrence_required",
                "boundary_recurrence_required",
            }
        ),
        None,
    )
    if event is None:
        return None
    operation_identity = event.get("operation_identity")
    operation_sha = str(event.get("operation_identity_sha256") or "").strip()
    lowering = event.get("lowering")
    boundary = event.get("boundary_evidence")
    boundary = boundary if isinstance(boundary, Mapping) else {}
    if (
        not isinstance(operation_identity, Mapping)
        or not operation_sha
        or not isinstance(lowering, Mapping)
    ):
        return None
    if _stable_json_sha256(operation_identity) != operation_sha:
        raise ValueError("task-carried operation identity digest does not match")
    # Departure events may carry a separately witnessed source boundary.  A
    # remote arrival event already carries its adapter-local trigger chart in
    # the catalog lowering.  Requiring the departure-only field here erased
    # that producer output and silently sent the consumer through the older
    # residual-window fallback.
    source_rect = boundary.get("source_rect") or lowering.get("rect")
    if not isinstance(source_rect, (list, tuple)) or len(source_rect) != 4:
        return None
    source_rect = [int(value) for value in source_rect]

    task_id = str(context.get("task_id") or "").strip()
    weakness = _read_json(project / "workspace" / "latest_harness_weakness.json")
    task = weakness.get("workbench_task") if isinstance(weakness, dict) else None
    if (
        not isinstance(task, Mapping)
        or str(task.get("task_id") or "").strip() != task_id
    ):
        raise ValueError("operation-domain refinement no longer names the active task")
    source_ref = str(task.get("source_ref") or "").strip()
    source_sha = str(task.get("source_sha256") or "").strip().lower()
    if not source_ref or len(source_sha) != 64:
        raise ValueError("operation-domain refinement task has no carrier identity")
    from ztare.common.artifact_refs import resolve_project_artifact_ref

    source_path = resolve_project_artifact_ref(project, source_ref)
    if source_path is None or not source_path.is_file():
        raise ValueError("operation-domain refinement carrier is unavailable")
    source_bytes = source_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source_sha:
        raise ValueError("operation-domain refinement carrier identity changed")
    source_ref = _rel(project, source_path)

    from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
    from ztare.worldmodel.evidence_quotients import resolve_episode_ref
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import as_predictor, env_frame_indices
    from ztare.worldmodel.spec_catalog import lower_patch_delta_spec

    program = _load_carrier_from_source(
        source_bytes.decode("utf-8"),
        str(source_path),
        project,
    )
    predictor = as_predictor(program)
    episode_path = resolve_episode_ref(project, episode_ref)
    log = EpisodeLog.read_jsonl(episode_path)
    transitions = log.transitions()
    excluded = env_frame_indices(log)
    patch_delta, lowering_error = lower_patch_delta_spec(
        {"actions": {}, "always": [dict(lowering)]}
    )
    if patch_delta is None:
        raise ValueError(f"task-carried operation is not lowerable: {lowering_error}")

    def canonical_grid(value: Any) -> Any:
        if not isinstance(value, (list, tuple)) or not value:
            return None
        if not all(isinstance(row, (list, tuple)) for row in value):
            return None
        return tuple(tuple(row) for row in value)

    evaluated: list[dict[str, Any]] = []
    failed_predictions = 0
    for index, transition in enumerate(transitions):
        if index in excluded:
            continue
        observed = canonical_grid(transition.s_next)
        base = canonical_grid(predictor(transition.s, transition.a, transition.t))
        if base is None or observed is None:
            failed_predictions += 1
            continue
        proposed = canonical_grid(
            patch_delta(base, transition.s, transition.a, transition.t)
        )
        if proposed is None:
            failed_predictions += 1
            continue
        evaluated.append(
            {
                "index": index,
                "transition": transition,
                "changed": proposed != base,
                "base_exact": base == observed,
                "proposed_exact": proposed == observed,
            }
        )
    repair_positive = [
        row
        for row in evaluated
        if row["changed"] and not row["base_exact"] and row["proposed_exact"]
    ]
    harmful = [
        row
        for row in evaluated
        if row["changed"] and row["base_exact"] and not row["proposed_exact"]
    ]
    ambiguous = [
        row
        for row in evaluated
        if row["changed"] and not row["base_exact"] and not row["proposed_exact"]
    ]
    base_wrong = sum(not row["base_exact"] for row in evaluated)
    unguarded_wrong = sum(not row["proposed_exact"] for row in evaluated)
    evaluated_by_index = {int(row["index"]): row for row in evaluated}
    domain_support_indices = {
        int(value)
        for value in (boundary.get("prior_support_rows") or [])
        if isinstance(value, int) or str(value).lstrip("-").isdigit()
    }
    domain_support_indices.update(
        int(value)
        for value in (event.get("operation_support_rows") or [])
        if isinstance(value, int) or str(value).lstrip("-").isdigit()
    )
    domain_support_indices.update(int(row["index"]) for row in repair_positive)
    domain_positive = [
        evaluated_by_index[index]
        for index in sorted(domain_support_indices)
        if index in evaluated_by_index
    ]
    # Row coordinates are evidence locators, not observation identities.  A
    # copied/replayed row must not manufacture recurrence authority.  Reuse the
    # episode packet's content binding so identity support counts distinct
    # observed transitions while retaining every row for diagnostics.
    distinct_domain_positive: list[dict[str, Any]] = []
    domain_observation_sha256s: list[str] = []
    seen_observations: set[str] = set()
    for row in domain_positive:
        observation_sha = row["transition"].observation_hash()
        if observation_sha in seen_observations:
            continue
        seen_observations.add(observation_sha)
        domain_observation_sha256s.append(observation_sha)
        distinct_domain_positive.append(row)
    interventions = sorted(
        {int(row["transition"].a) for row in distinct_domain_positive}
    )
    boundary_recurrence = bool(
        len(distinct_domain_positive) >= 2 and len(interventions) >= 2
    )
    # The governing identity is recurrence of the operation on law-owned
    # transitions.  Intervention diversity is useful equivariance evidence,
    # but it is not the identity itself: a lawful operation may recur under one
    # intervention.  Boundary-composite rows remain excluded by
    # env_frame_indices and cannot manufacture recurrence.
    law_owned_recurrence = len(distinct_domain_positive) >= 2
    identity_support = boundary_recurrence or law_owned_recurrence

    selected: dict[str, Any] | None = None
    if not harmful and unguarded_wrong == 0:
        selected = {
            "kind": "unrestricted_operation_domain",
            "lowering": {},
            "margin": None,
            "bbox": None,
            "pattern": None,
            "guarded_wrong": 0,
        }
    elif distinct_domain_positive and harmful:
        # A conditioned operation has two identity-bearing ends: the subject
        # boundary and the consequence object whose state may enable it.  The
        # old miner searched only expanding rectangles around the subject,
        # erasing a remote target precondition already named by ``writes`` (or
        # ``region`` for a state-machine lowering).  Enumerate those factored
        # charts through the same exact-pattern gate and choose the smallest
        # separating presentation.  This remains adapter-local lowering; the
        # operation identity above is unchanged.
        chart_candidates: list[tuple[str, int, list[int]]] = []
        r0, c0, r1, c1 = source_rect
        for margin in range(max(0, int(max_margin)) + 1):
            chart_candidates.append(
                (
                    "subject_neighborhood",
                    margin,
                    [r0 - margin, c0 - margin, r1 + margin, c1 + margin],
                )
            )
        target_rect: list[int] | None = None
        region = lowering.get("region")
        if isinstance(region, (list, tuple)) and len(region) == 4:
            target_rect = [int(value) for value in region]
        else:
            write_cells = [
                (int(cell[0]), int(cell[1]))
                for write in (lowering.get("writes") or [])
                if isinstance(write, (list, tuple)) and len(write) == 2
                for cell in (write[1] or [])
                if isinstance(cell, (list, tuple)) and len(cell) == 2
            ]
            if write_cells:
                target_rect = [
                    min(row for row, _col in write_cells),
                    min(col for _row, col in write_cells),
                    max(row for row, _col in write_cells),
                    max(col for _row, col in write_cells),
                ]
        if target_rect is not None:
            tr0, tc0, tr1, tc1 = target_rect
            for margin in range(max(0, int(max_margin)) + 1):
                chart_candidates.append(
                    (
                        "consequence_precondition",
                        margin,
                        [
                            tr0 - margin,
                            tc0 - margin,
                            tr1 + margin,
                            tc1 + margin,
                        ],
                    )
                )

        separating_charts: list[dict[str, Any]] = []
        seen_charts: set[tuple[int, int, int, int]] = set()
        for chart_role, margin, bbox in chart_candidates:
            bbox_key = tuple(bbox)
            if bbox_key in seen_charts:
                continue
            seen_charts.add(bbox_key)
            expected_area = (bbox[2] - bbox[0] + 1) * (bbox[3] - bbox[1] + 1)
            if expected_area <= 0:
                continue

            def label(row: Mapping[str, Any]) -> tuple[Any, ...] | None:
                values = _support_values(row["transition"].s, bbox)
                return values if len(values) == expected_area else None

            positive_labels = {label(row) for row in distinct_domain_positive}
            if None in positive_labels or len(positive_labels) != 1:
                continue
            pattern = next(iter(positive_labels))
            if any(label(row) == pattern for row in harmful):
                continue
            guarded_wrong = sum(
                not (
                    row["proposed_exact"]
                    if label(row) == pattern
                    else row["base_exact"]
                )
                for row in evaluated
            )
            separating_charts.append({
                "kind": "adapter_local_exact_chart",
                "lowering": {
                    "when_region": [*bbox, list(pattern)],
                },
                "margin": margin,
                "bbox": bbox,
                "pattern": list(pattern),
                "chart_role": chart_role,
                "guarded_wrong": guarded_wrong,
            })
        if separating_charts:
            separating_charts.sort(
                key=lambda row: (
                    row["guarded_wrong"],
                    (row["bbox"][2] - row["bbox"][0] + 1)
                    * (row["bbox"][3] - row["bbox"][1] + 1),
                    row["margin"],
                    row["chart_role"],
                )
            )
            selected = separating_charts[0]

    candidate_admissible = bool(
        selected is not None
        and selected["guarded_wrong"] == 0
        and identity_support
        and not ambiguous
        and failed_predictions == 0
    )
    if candidate_admissible:
        status = "operation_domain_selector_found"
    elif selected is not None and not identity_support:
        status = "operation_domain_requires_recurrence"
    elif ambiguous:
        status = "operation_domain_has_ambiguous_triggers"
    elif failed_predictions:
        status = "operation_domain_evaluation_incomplete"
    else:
        status = "no_operation_domain_selector_found"

    repair_positive_rows = [int(row["index"]) for row in repair_positive]
    domain_positive_rows = [int(row["index"]) for row in domain_positive]
    harmful_rows = [int(row["index"]) for row in harmful]
    selector_lowering = selected["lowering"] if selected is not None else {}
    acquisition_obligation: dict[str, Any] | None = None
    if not identity_support and distinct_domain_positive:
        witness = distinct_domain_positive[0]
        witness_index = int(witness["index"])
        witness_identity = getattr(witness["transition"], "identity", None)
        if (
            witness_identity is not None
            and getattr(witness_identity, "is_authoritative", False)
            and not getattr(witness_identity, "is_boundary", True)
            and witness_identity.source_epoch == witness_identity.target_epoch
        ):
            obligation_identity = {
                "kind": "operation_recurrence",
                "operation_identity_sha256": operation_sha,
                "task_id": task_id,
                "source_epoch": witness_identity.source_epoch,
            }
            witness_ref = (
                f"{episode_path.relative_to(project.resolve())}"
                f"#transition:{witness_index}"
            )
            acquisition_obligation = {
                "schema": "ztare-worldmodel-edge-acquisition-obligation-v1",
                "obligation_identity": obligation_identity,
                "obligation_sha256": _stable_json_sha256(obligation_identity),
                "source_observation_ref": witness_ref,
                "minimum_law_owned_observations": 2,
                "current_law_owned_observations": len(
                    distinct_domain_positive
                ),
                "authority": "experiment_routing_only",
            }
    return {
        "schema": "ztare-worldmodel-operation-domain-selector-v1",
        "authority": "diagnostic_only",
        "admissibility_scope": "candidate_family",
        "candidate_family_id": "task-bound-operation-domain-refinement-v1",
        "task_id": task_id,
        "task_source_ref": source_ref,
        "task_source_sha256": source_sha,
        "source_receipt_ref": str(context.get("ref") or ""),
        "source_receipt_sha256": str(context.get("sha256") or ""),
        "operation_identity": dict(operation_identity),
        "operation_identity_sha256": operation_sha,
        "operation_lowering_sha256": _stable_json_sha256(lowering),
        "operation_guard": {
            "kind": selected["kind"] if selected is not None else "undefined",
            "lowering": selector_lowering,
            "coordinate_contract": (
                {
                    "authority": "interactive_grid_adapter",
                    "axes": ["row", "column"],
                    "basis": "step_start_local_chart",
                }
                if selector_lowering
                else {}
            ),
        },
        "domain_evidence": {
            "episode_ref": str(episode_path.relative_to(project.resolve())),
            "evaluated_rows": len(evaluated),
            "env_rows_excluded": len(excluded),
            "failed_predictions": failed_predictions,
            "base_wrong_rows": base_wrong,
            "unguarded_wrong_rows": unguarded_wrong,
            "guarded_wrong_rows": (
                selected["guarded_wrong"] if selected is not None else None
            ),
            "repair_trigger_count": len(repair_positive_rows),
            "repair_trigger_rows": repair_positive_rows[:64],
            "repair_trigger_rows_sha256": _stable_json_sha256(
                repair_positive_rows
            ),
            "operation_domain_support_count": len(domain_positive_rows),
            "operation_domain_support_rows": domain_positive_rows[:64],
            "operation_domain_support_rows_sha256": _stable_json_sha256(
                domain_positive_rows
            ),
            "distinct_operation_domain_observations": len(
                distinct_domain_positive
            ),
            "operation_domain_observation_sha256s": (
                domain_observation_sha256s[:64]
            ),
            "operation_domain_observation_set_sha256": _stable_json_sha256(
                sorted(domain_observation_sha256s)
            ),
            "harmful_trigger_count": len(harmful_rows),
            "harmful_trigger_rows": harmful_rows[:64],
            "harmful_trigger_rows_sha256": _stable_json_sha256(harmful_rows),
            "ambiguous_trigger_count": len(ambiguous),
            "interventions": interventions,
            "distinct_interventions": len(interventions),
            "source_rect": source_rect,
            "selected_margin": selected["margin"] if selected is not None else None,
            "selected_chart_role": (
                selected.get("chart_role", "unrestricted")
                if selected is not None
                else None
            ),
        },
        "identity_support": {
            "distinct_positive_observations": len(distinct_domain_positive),
            "distinct_interventions": len(interventions),
            "minimum_observations": 2,
            "scope": "law_owned_transition",
            "boundary_recurrence": boundary_recurrence,
            "authority_granted": identity_support,
        },
        "lowerability_status": status,
        "candidate_family_admissible": candidate_admissible,
        "candidate_delta_admissible": candidate_admissible,
        "candidate_predicates": [selector_lowering] if candidate_admissible else [],
        "conjecture_predicates": [dict(lowering)],
        **(
            {"acquisition_obligation": acquisition_obligation}
            if acquisition_obligation is not None
            else {}
        ),
        "forbidden_feature_classes": [
            "absolute_evidence_row",
            "absolute_time",
            "intervention_identity",
            "hidden_evaluator_field",
        ],
        "presentation_note": (
            "operation_guard is an adapter lowering of the certified domain; "
            "its coordinates and observed values are not operation identity"
        ),
        "next_required_evidence": (
            "acquire another law-owned observation of the same operation identity"
            if not identity_support
            else (
                "acquire a context that separates beneficial from harmful firings, "
                "or propose a different adapter observation chart"
                if not candidate_admissible
                else ""
            )
        ),
    }


def run_worldmodel_lowerable_selector_miner(
    project_dir: str | Path,
    *,
    regression_ref: str = "workspace/latest_patch_base_regression.json",
    episode_ref: str = "raw/episodes/episode_001.jsonl",
    max_predicates: int = 8,
    upstream_receipt_refs: tuple[str, ...] = (),
) -> str:
    """Mine executable selectors by scanning local windows across visible logs.

    The first separating-feature miner works on one counterexample chart. This
    pass tries to lower that chart into a carrier predicate by quantifying over
    every same-shaped window in the visible transition log. Absolute row/time
    and the original support identity never enter the predicate language.
    """
    project = Path(project_dir)
    upstream = _task_bound_upstream_receipts(
        project,
        upstream_receipt_refs,
    )
    context = upstream.get("inspect_worldmodel_counterexample_context")
    if context is not None:
        task_domain_result = _mine_task_operation_domain_selector(
            project,
            context=context,
            episode_ref=episode_ref,
            max_margin=8,
        )
        if task_domain_result is not None:
            observation_sha = str(
                (context.get("summary") or {}).get("observation_sha256")
                if isinstance(context.get("summary"), Mapping)
                else ""
            ).strip()
            task_id = str(task_domain_result.get("task_id") or "").strip()
            if observation_sha and task_id:
                from ztare.common.schema_routes import append_schema_route_event

                append_schema_route_event(
                    project,
                    schema_id="ztare-counterexample-observation-triple-v1",
                    event="first_fire",
                    join_values={
                        "observation_sha256": observation_sha,
                        "task_id": task_id,
                    },
                    payload={
                        "consumer": "worldmodel_operation_domain_refinement",
                        "outcome": task_domain_result.get("lowerability_status"),
                    },
                )
            return json.dumps(
                task_domain_result,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
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

        from ztare.worldmodel.evidence_quotients import resolve_episode_ref

        log = EpisodeLog.read_jsonl(resolve_episode_ref(project, episode_ref))
        transitions = log.transitions()
        from ztare.worldmodel.gates import env_frame_indices

        excluded_transition_indices = env_frame_indices(log)
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
        if idx in excluded_transition_indices:
            continue
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
    zero_error_predicates = [
        row for row in ranked if row.get("perfect_on_visible_log") is True
    ]
    near_misses = [
        row for row in ranked if row.get("perfect_on_visible_log") is not True
    ]
    # A zero-error selector over one observed transition is a presentation
    # fingerprint, not evidence for a recurring transition identity.  The same
    # recurrence boundary is used by spec abduction: deterministic authority
    # starts only after the law has fired on distinct observations.  Multiple
    # matching windows inside one frame still count as one observation unless
    # a separately certified symmetry supplies the missing transport witness.
    positive_observation_rows = sorted(
        {int(row["idx"]) for row in positive_rows if row.get("idx") is not None}
    )
    minimum_identity_witnesses = 2
    has_identity_support = (
        len(positive_observation_rows) >= minimum_identity_witnesses
    )
    candidate_predicates = zero_error_predicates if has_identity_support else []
    conjecture_predicates = zero_error_predicates if not has_identity_support else []
    if candidate_predicates:
        lowerability_status = "candidate_selectors_found"
    elif conjecture_predicates:
        lowerability_status = "conjecture_singleton_support"
    elif positive_rows and len(positive_rows) == same_source_windows:
        lowerability_status = "underdetermined_no_negative_same_source_windows"
    else:
        lowerability_status = "no_zero_error_selector_found"
    representative_cells = sum(
        len(row) for row in rep.s if isinstance(row, (list, tuple))
    )
    window_cells = win_h * win_w
    payload_out = {
        "schema": "ztare-worldmodel-lowerable-selector-miner-v1",
        "authority": "diagnostic_only",
        "admissibility_scope": "candidate_family",
        "candidate_family_id": "same-shaped-window-selector-v1",
        "regression_ref": _rel(project, regression_path),
        "window_shape": [win_h, win_w],
        "source_window_values": source_label,
        "target_window_values": target_label,
        "representative_action": rep.a,
        "same_source_windows": same_source_windows,
        "positive_windows": len(positive_rows),
        "total_windows": total_windows,
        "excluded_transition_count": len(excluded_transition_indices),
        "identity_support": {
            "distinct_positive_observations": len(positive_observation_rows),
            "minimum_required": minimum_identity_witnesses,
            "observation_rows": positive_observation_rows[:32],
            "scope": "law_owned_transition",
            "authority_granted": has_identity_support,
            "rule": (
                "recurrence across distinct observations, or a separately "
                "certified transport witness"
            ),
        },
        "presentation_compression": {
            "selector_window_cells": window_cells,
            "representative_state_cells": representative_cells,
            "window_cell_fraction": (
                window_cells / representative_cells if representative_cells else None
            ),
            "source_match_fraction": (
                same_source_windows / total_windows if total_windows else None
            ),
        },
        "lowerability_status": lowerability_status,
        # None means underdetermined.  False is reserved for a refuted family;
        # coercing a singleton conjecture to False would be the dual category
        # error and could wrongly close the surrounding search space.
        "candidate_family_admissible": (
            True if candidate_predicates else None if conjecture_predicates else False
        ),
        "candidate_predicates": candidate_predicates,
        "conjecture_predicates": conjecture_predicates,
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
        "next_required_evidence": (
            "observe the same proposed transition identity in another transition, "
            "or certify a transformation carrying this witness to another context"
            if conjecture_predicates
            else (
                "refine the adapter observation family or acquire a law-owned "
                "transition that separates this candidate family"
                if not candidate_predicates
                else ""
            )
        ),
    }
    if candidate_predicates:
        payload_out["candidate_delta_admissible"] = True
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
        "admissibility_scope": "candidate_family",
        "candidate_family_id": (
            "component-local-selector-v1"
            if include_component_features
            else "global-observable-context-selector-v1"
        ),
        "source_receipt": transfer_ref,
        "example_count": len(examples),
        "label_counts": dict(label_counts),
        "candidate_label_coverage": {
            "covered": [_compact_tuple(label) for label in sorted(covered_labels, key=str)],
            "required": [_compact_tuple(label) for label in rewrite_labels],
        },
        "missing_patch_witness_rows": missing_patch_witness,
        "lowerability_status": status,
        "candidate_family_admissible": status == "candidate_selectors_found",
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
    if status == "candidate_selectors_found":
        payload_out["candidate_delta_admissible"] = True
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


def _guard_pair_conflict(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe the conservative conflict when guard disjointness is unproved."""

    left_guard = _guard_domain_descriptor(left)
    right_guard = _guard_domain_descriptor(right)
    return {
        "overlap_kind": "guard_disjointness_not_proven",
        "left_guard": left_guard,
        "right_guard": right_guard,
        "shared_guard_families": sorted(set(left_guard) & set(right_guard)),
    }


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
            "admissibility_scope": "candidate_family",
            "candidate_family_id": "guarded-selector-coproduct-v1",
            "join_status": "conflict",
            "candidate_family_admissible": False,
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
            "admissibility_scope": "candidate_family",
            "candidate_family_id": "guarded-selector-coproduct-v1",
            "join_status": "candidate_selectors_found",
            "candidate_family_admissible": True,
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
        "candidate_residual_only",
        "changed_support",
        "observed_behavioral_sibling",
        "same_support_changed_pairs",
        "same_quotient_worse_frequency",
    }:
        return False
    cand = comparison.get("candidate_top_quotient")
    if not isinstance(cand, dict):
        return False
    bbox = cand.get("bbox") if isinstance(cand.get("bbox"), list) else []
    return (
        _as_int(cand.get("first_row")) is not None
        and len(bbox) == 4
    )


def _observed_behavioral_fiber(
    project: Path,
    *,
    candidate_row: int,
    candidate_transition: Any,
) -> dict[str, Any]:
    """Return the finite one-step behavior class containing a witness.

    Equality is consumer-indexed: same law coordinate and observed
    consequence, and compatible lifecycle.  Intervention and source relation
    remain typed member coordinates so repeated consequences under varied
    inputs become visible without claiming that the inputs are globally
    equivalent.  Catalogued source morphisms annotate the fiber; they do not
    decide membership in the inverse image.  This is a banked observational
    fiber, not a global quotient or an equivariance certificate.
    """
    evidence = project / "raw" / "episodes" / "episode_001.jsonl"
    successor = [list(row) for row in candidate_transition.s_next]
    state = [list(row) for row in candidate_transition.s]
    candidate_indices: list[int] = [candidate_row]
    try:
        physical_index = -1
        with evidence.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                physical_index += 1
                if physical_index == candidate_row:
                    continue
                row = json.loads(line)
                if (
                    _as_int(row.get("t")) != int(candidate_transition.t)
                    or row.get("s_next") != successor
                ):
                    continue
                candidate_indices.append(physical_index)
    except Exception:  # noqa: BLE001
        return {}
    candidate_indices = sorted(set(candidate_indices))
    try:
        from ztare.worldmodel.episode_log import EpisodeLog
        from ztare.worldmodel.spec_abduction import catalog_state_morphisms

        transitions = EpisodeLog.read_jsonl_indices(evidence, set(candidate_indices))
    except Exception:  # noqa: BLE001
        return {}

    members: list[dict[str, Any]] = []
    transition_by_row: dict[int, Any] = {}
    operation_families: dict[str, dict[str, Any]] = {}
    for row_index in candidate_indices:
        transition = transitions.get(row_index)
        if transition is None:
            continue
        if row_index == candidate_row:
            exact_operations = [{"op": "identity"}]
        else:
            exact_operations = catalog_state_morphisms(transition.s, state)
        pair = {
            "best_prior_row": row_index,
            "candidate_row": candidate_row,
            "best_prior_transition": transition,
            "candidate_transition": candidate_transition,
            "evidence_ref": "raw/episodes/episode_001.jsonl",
        }
        lifecycle = _observed_segment_compatibility(project, pair)
        if not lifecycle.get("compatible"):
            continue
        operations: list[dict[str, Any]] = []
        selector_presentations: list[dict[str, Any]] = []
        for exact in exact_operations:
            operation = _catalog_operation_identity(exact)
            if operation not in operations:
                operations.append(operation)
            scope = exact.get("component_scope")
            if isinstance(scope, dict) and scope not in selector_presentations:
                selector_presentations.append(scope)
            key = json.dumps(operation, sort_keys=True, separators=(",", ":"))
            family = operation_families.setdefault(
                key,
                {"operation": operation, "member_rows": []},
            )
            family["member_rows"].append(row_index)
        transition_by_row[row_index] = transition
        members.append(
            {
                "row": row_index,
                "representative": row_index == candidate_row,
                "intervention": int(transition.a),
                "source_state_sha256": _stable_json_sha256(transition.s),
                "observed_consequence_sha256": _stable_json_sha256(
                    transition.s_next
                ),
                "source_operations_to_representative": operations,
                "source_exact_lowering_variants": exact_operations,
                "source_relation_status": (
                    "catalog_morphism_to_representative"
                    if exact_operations
                    else "not_connected_by_current_catalog"
                ),
                "component_selector_presentations": selector_presentations,
                "lifecycle_compatibility": lifecycle,
            }
        )
    if len(members) < 2:
        return {}
    members.sort(key=lambda row: int(row["row"]))
    payload = {
        "schema": "ztare-observed-one-step-behavioral-fiber-v1",
        "authority": "diagnostic_finite_witness",
        "representative_row": candidate_row,
        "representative_intervention": int(candidate_transition.a),
        "interventions": sorted(
            {int(row["intervention"]) for row in members}
        ),
        "distinct_interventions": len(
            {int(row["intervention"]) for row in members}
        ),
        "law_coordinate": int(candidate_transition.t),
        "member_count": len(members),
        "member_rows": [int(row["row"]) for row in members],
        "distinct_source_states": len(
            {str(row["source_state_sha256"]) for row in members}
        ),
        "direct_catalog_morphism_members": sum(
            1
            for row in members
            if row["source_relation_status"]
            == "catalog_morphism_to_representative"
        ),
        "unresolved_source_relation_rows": [
            int(row["row"])
            for row in members
            if row["source_relation_status"]
            == "not_connected_by_current_catalog"
        ],
        "shared_observed_consequence_sha256": _stable_json_sha256(
            candidate_transition.s_next
        ),
        "observed_relation": "many_presentations_one_consequence",
        "intervention_relation": (
            "varied_interventions_one_consequence"
            if len({int(row["intervention"]) for row in members}) > 1
            else "single_intervention_observed"
        ),
        "equality_contract": (
            "same lifecycle chart, law coordinate, and observed consequence; "
            "source and intervention coordinates retained on members; catalog "
            "morphisms are annotations rather than membership authority"
        ),
        "operation_families": list(operation_families.values()),
        "members": members,
        "global_equivariance_authorized": False,
        "quotient_authorized": False,
        "carrier_promotion_authorized": False,
        "distinguishing_obligation": (
            "seek a compatible source/intervention member with a different "
            "consequence, or a same-consequence source outside the observed orbit"
        ),
    }
    payload["fiber_identity_sha256"] = _stable_json_sha256(payload)
    payload["_transition_by_row"] = transition_by_row
    return payload


def _counterexample_comparison_pair(
    project: Path,
    regression: dict[str, Any],
) -> dict[str, Any]:
    """Load the two quotient representatives once for every context consumer."""
    comparison = regression.get("quotient_comparison")
    if not isinstance(comparison, dict):
        return {}
    if comparison.get("relation") not in {
        "candidate_residual_only",
        "changed_support",
        "observed_behavioral_sibling",
        "same_support_changed_pairs",
        "same_quotient_worse_frequency",
    }:
        return {}
    cand = comparison.get("candidate_top_quotient")
    best = comparison.get("best_prior_top_quotient")
    if not isinstance(cand, dict):
        return {}
    c_row = _as_int(cand.get("first_row"))
    if c_row is None:
        return {}
    b_row = _as_int(best.get("first_row")) if isinstance(best, dict) else None
    try:
        from ztare.worldmodel.episode_log import EpisodeLog

        candidate_transition = EpisodeLog.read_jsonl_indices(
            project / "raw" / "episodes" / "episode_001.jsonl",
            {c_row},
        )[c_row]
    except Exception:  # noqa: BLE001
        return {}
    behavioral_fiber = _observed_behavioral_fiber(
        project,
        candidate_row=c_row,
        candidate_transition=candidate_transition,
    )
    fiber_transitions = behavioral_fiber.pop("_transition_by_row", {})
    if b_row is None:
        sibling_rows = [
            int(row)
            for row in fiber_transitions
            if int(row) != c_row
        ]
        if not sibling_rows:
            return {}
        b_row = min(sibling_rows, key=lambda row: (abs(c_row - row), row))
        best_transition = fiber_transitions[b_row]
        best = {
            "first_row": b_row,
            "t": int(best_transition.t),
            "action": int(best_transition.a),
            "bbox": cand.get("bbox"),
            "pair_counts": [],
            "source": "observed_same_consequence_sibling",
        }
        comparison = {
            **comparison,
            "relation": "observed_behavioral_sibling",
            "best_prior_top_quotient": best,
        }
    else:
        best_transition = fiber_transitions.get(b_row)
        if best_transition is None:
            try:
                best_transition = EpisodeLog.read_jsonl_indices(
                    project / "raw" / "episodes" / "episode_001.jsonl",
                    {b_row},
                )[b_row]
            except Exception:  # noqa: BLE001
                return {}
    return {
        "comparison": comparison,
        "candidate_quotient": cand,
        "best_prior_quotient": best,
        "candidate_row": c_row,
        "best_prior_row": b_row,
        "candidate_transition": candidate_transition,
        "best_prior_transition": best_transition,
        "behavioral_fiber": behavioral_fiber,
        "_fiber_transitions": fiber_transitions,
        "evidence_ref": "raw/episodes/episode_001.jsonl",
    }


def _patch_base_chain_effects(
    project: Path,
    regression: dict[str, Any],
    *,
    pair: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate carrier ancestors on one observed behavioral fiber.

    PATCH_BASE is an identity-bearing composition edge.  A flat latest-versus-
    residual view discards whether successive deltas repaired different members
    of one behavior class.  This bounded join restores that evidence without
    replaying the bank or granting promotion authority.
    """

    fiber = pair.get("behavioral_fiber")
    transitions = pair.get("_fiber_transitions")
    if not isinstance(fiber, dict) or not isinstance(transitions, dict):
        return {}
    member_rows = [
        int(row)
        for row in fiber.get("member_rows", [])
        if _as_int(row) is not None and int(row) in transitions
    ]
    if len(member_rows) < 2:
        return {}
    try:
        from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
        from ztare.worldmodel.patch_base_carrier import resolved_patch_base_paths

        observed_frontier = _observed_frontier_source(project, regression)
        frontier = observed_frontier["frontier"]
        frontier_path = Path(observed_frontier["path"])
        chain_paths = tuple(reversed(resolved_patch_base_paths(
            frontier_path,
            project_dir=project,
        ))) + (frontier_path,)
    except (OSError, TypeError, ValueError):
        return {}
    if len(chain_paths) < 2:
        return {}

    layers: list[dict[str, Any]] = []
    prior_correct: set[int] = set()
    for depth, path in enumerate(chain_paths):
        try:
            source = path.read_text(encoding="utf-8")
            model = _load_carrier_from_source(source, str(path), project)
            predictions: dict[int, str] = {}
            correct: set[int] = set()
            evaluation_errors: list[int] = []
            for row in member_rows:
                transition = transitions[row]
                try:
                    prediction = model(
                        transition.s,
                        transition.a,
                        transition.t,
                    )
                    prediction_sha = _stable_json_sha256(prediction)
                    predictions[row] = prediction_sha
                    if prediction_sha == _stable_json_sha256(transition.s_next):
                        correct.add(row)
                except Exception:  # noqa: BLE001 - diagnostic layer remains partial
                    evaluation_errors.append(row)
            source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
            try:
                source_ref = str(path.resolve().relative_to(project.resolve()))
            except ValueError:
                source_ref = path.name
            added = sorted(correct - prior_correct)
            lost = sorted(prior_correct - correct)
            layers.append(
                {
                    "depth_from_root": depth,
                    "carrier_ref": source_ref,
                    "carrier_sha256": source_sha,
                    "correct_member_rows": sorted(correct),
                    "wrong_member_rows": sorted(set(member_rows) - correct),
                    "added_correct_member_rows": added,
                    "lost_correct_member_rows": lost,
                    "evaluation_error_rows": evaluation_errors,
                    "fiber_behavior_sha256": _stable_json_sha256(predictions),
                    "observed_delta_relation": (
                        "adds_members_of_same_behavioral_fiber"
                        if added and not lost
                        else "mixed_fiber_effect"
                        if added or lost
                        else "no_observed_fiber_change"
                    ),
                }
            )
            prior_correct = correct
        except Exception:  # noqa: BLE001 - one unreadable ancestor does not erase the chain
            continue
    if len(layers) < 2:
        return {}

    additive_layers = [
        layer
        for layer in layers[1:]
        if layer["added_correct_member_rows"]
        and not layer["lost_correct_member_rows"]
    ]
    distinct_added_rows = sorted({
        row
        for layer in additive_layers
        for row in layer["added_correct_member_rows"]
    })
    payload = {
        "schema": "ztare-patch-base-behavioral-fiber-effects-v1",
        "authority": "diagnostic_finite_witness",
        "frontier_role": str(frontier.get("role") or ""),
        "frontier_sha256": str(frontier.get("sha256") or ""),
        "behavioral_fiber_identity_sha256": str(
            fiber.get("fiber_identity_sha256") or ""
        ),
        "member_rows": member_rows,
        "chain_order": "root_to_frontier",
        "layer_count": len(layers),
        "additive_layer_count": len(additive_layers),
        "distinct_rows_added_across_layers": distinct_added_rows,
        "observed_chain_relation": (
            "distinct_layers_add_members_of_one_observed_behavioral_fiber"
            if len(additive_layers) >= 2
            else "no_repeated_same_fiber_addition_observed"
        ),
        "layers": layers,
        "global_operation_identity_authorized": False,
        "carrier_promotion_authorized": False,
    }
    payload["chain_effect_identity_sha256"] = _stable_json_sha256(payload)
    return payload


def _counterexample_context_summary(
    project: Path,
    regression: dict[str, Any],
    *,
    pair: dict[str, Any] | None = None,
) -> str:
    pair = pair or _counterexample_comparison_pair(project, regression)
    if not pair:
        return ""
    comparison = pair["comparison"]
    cand = pair["candidate_quotient"]
    best = pair["best_prior_quotient"]
    c_row = pair["candidate_row"]
    b_row = pair["best_prior_row"]
    c_tr = pair["candidate_transition"]
    b_tr = pair["best_prior_transition"]
    bbox = cand.get("bbox") if isinstance(cand.get("bbox"), list) else []
    if len(bbox) != 4:
        return ""
    c_ctx = _state_context_features(c_tr.s, bbox)
    b_ctx = _state_context_features(b_tr.s, bbox)
    deltas = []
    for key in sorted(set(c_ctx) | set(b_ctx)):
        if c_ctx.get(key) != b_ctx.get(key):
            if key == "support_row_sections":
                candidate_rows = c_ctx.get(key) or []
                prior_rows = b_ctx.get(key) or []
                changed_rows = [
                    index
                    for index in range(max(len(candidate_rows), len(prior_rows)))
                    if (
                        candidate_rows[index] if index < len(candidate_rows) else None
                    ) != (
                        prior_rows[index] if index < len(prior_rows) else None
                    )
                ]
                deltas.append(
                    f"{key}:changed_relative_rows={changed_rows[:16]}; "
                    f"row_counts=({len(candidate_rows)},{len(prior_rows)})"
                )
                continue
            candidate_value = json.dumps(
                c_ctx.get(key), sort_keys=True, separators=(",", ":"), default=str
            )
            prior_value = json.dumps(
                b_ctx.get(key), sort_keys=True, separators=(",", ":"), default=str
            )
            deltas.append(
                f"{key}:candidate={candidate_value[:320]} "
                f"best_prior={prior_value[:320]}"
            )
    if not deltas:
        return ""
    summary = (
        f"relation={comparison.get('relation')}; rows=candidate:{c_row},best_prior:{b_row}; "
        f"support_bbox={bbox}; candidate_ta=({cand.get('t')},{cand.get('action')}); "
        f"best_prior_ta=({best.get('t')},{best.get('action')}); "
        f"context_delta={' | '.join(deltas[:6])}"
    )
    fiber = pair.get("behavioral_fiber")
    if isinstance(fiber, dict) and int(fiber.get("member_count") or 0) > 1:
        summary += (
            f"; behavioral_fiber_members={fiber.get('member_rows')}; "
            f"fiber_relation={fiber.get('observed_relation')}"
        )
    return summary


def _stable_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _observed_segment_compatibility(
    project: Path,
    pair: dict[str, Any],
    *,
    max_legacy_span: int = 256,
) -> dict[str, Any]:
    """Bound lifecycle compatibility without manufacturing epoch identity."""
    b_row = int(pair["best_prior_row"])
    c_row = int(pair["candidate_row"])
    b_tr = pair["best_prior_transition"]
    c_tr = pair["candidate_transition"]
    identities = [b_tr.identity, c_tr.identity]
    if all(identity is not None and identity.is_authoritative for identity in identities):
        if any(identity.is_boundary for identity in identities):
            return {
                "compatible": False,
                "basis": "adapter_attested_boundary",
            }
        epochs = {
            (identity.source_epoch, identity.target_epoch)
            for identity in identities
        }
        if len(epochs) == 1:
            return {
                "compatible": True,
                "basis": "adapter_attested_same_dynamics_epoch",
                "epoch": list(next(iter(epochs))),
            }

    lo, hi = sorted((b_row, c_row))
    if hi - lo > max_legacy_span:
        return {
            "compatible": False,
            "basis": "legacy_segment_span_unverified",
            "span": hi - lo,
        }
    try:
        from ztare.worldmodel.episode_log import EpisodeLog

        rows = EpisodeLog.read_jsonl_indices(
            project / pair["evidence_ref"],
            set(range(lo, hi + 1)),
        )
    except Exception:  # noqa: BLE001
        return {"compatible": False, "basis": "segment_evidence_unavailable"}
    ordered = [rows[index] for index in range(lo, hi + 1)]
    if any(
        row.identity is not None
        and row.identity.is_authoritative
        and row.identity.is_boundary
        for row in ordered
    ):
        return {"compatible": False, "basis": "adapter_attested_boundary_in_span"}
    monotone_unit_clock = all(
        right.t == left.t + 1
        for left, right in zip(ordered, ordered[1:])
    )
    return {
        "compatible": monotone_unit_clock,
        "basis": (
            "legacy_monotone_unit_clock_no_attested_boundary"
            if monotone_unit_clock
            else "legacy_clock_discontinuity"
        ),
        "span": hi - lo,
    }


def _catalog_operation_identity(rule: dict[str, Any]) -> dict[str, Any]:
    """Separate the operation class from property-based lowering selectors."""
    return {
        key: value
        for key, value in rule.items()
        if key != "component_scope"
    }


def _catalog_operation_fibers(
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group exact lowerings by operation identity and retain selector fibers."""
    grouped: dict[str, dict[str, Any]] = {}
    for rule in rules:
        operation = _catalog_operation_identity(rule)
        key = json.dumps(operation, sort_keys=True, separators=(",", ":"))
        fiber = grouped.setdefault(
            key,
            {
                "operation": operation,
                "exact_lowering_variants": [],
                "component_selector_presentations": [],
            },
        )
        fiber["exact_lowering_variants"].append(rule)
        scope = rule.get("component_scope")
        if isinstance(scope, dict) and scope not in fiber["component_selector_presentations"]:
            fiber["component_selector_presentations"].append(scope)
    return list(grouped.values())


def _observed_commuting_catalog_transports(
    project: Path,
    regression: dict[str, Any],
    *,
    pair: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Find finite arrow-morphism witnesses across observed transitions.

    The result grants no global equivariance, quotient, or carrier-promotion
    authority.  The two vertical edges may differ: requiring one endomorphism
    on both sides discards absorption, canonicalization, genesis, and
    annihilation witnesses.  Candidate synthesis therefore sees the observed
    source and consequence operations separately, while retaining ambiguity
    about which object identity a property-based selector denotes.
    """
    pair = pair or _counterexample_comparison_pair(project, regression)
    if not pair:
        return []
    prior = pair["best_prior_transition"]
    candidate = pair["candidate_transition"]
    if int(prior.a) != int(candidate.a):
        return []
    lifecycle = _observed_segment_compatibility(project, pair)
    if not lifecycle.get("compatible"):
        return []
    from ztare.worldmodel.spec_abduction import catalog_state_morphisms

    source_rules = catalog_state_morphisms(prior.s, candidate.s)
    consequence_rules = catalog_state_morphisms(
        prior.s_next,
        candidate.s_next,
    )
    source_fibers = _catalog_operation_fibers(source_rules)
    consequence_fibers = _catalog_operation_fibers(consequence_rules)

    transports = []
    for source_fiber in source_fibers:
        for consequence_fiber in consequence_fibers:
            source_operation = source_fiber["operation"]
            consequence_operation = consequence_fiber["operation"]
            endomorphism = source_operation == consequence_operation
            operation_pair = {
                "source_operation": source_operation,
                "consequence_operation": consequence_operation,
            }
            source_scopes = source_fiber["component_selector_presentations"]
            consequence_scopes = consequence_fiber["component_selector_presentations"]
            selector_scopes = (
                source_scopes
                if endomorphism
                else [
                    {"edge": "source", "selector": scope}
                    for scope in source_scopes
                ] + [
                    {"edge": "consequence", "selector": scope}
                    for scope in consequence_scopes
                ]
            )
            observed_relation = (
                "one_step_behavioral_merge"
                if source_operation.get("op") != "identity"
                and consequence_operation.get("op") == "identity"
                else "transported_consequence"
            )
            payload = {
                "schema": "ztare-observed-arrow-transport-v1",
                "authority": "diagnostic_finite_witness",
                "source_row": pair["best_prior_row"],
                "target_row": pair["candidate_row"],
                "intervention": int(candidate.a),
                "time_translation": int(candidate.t) - int(prior.t),
                "lifecycle_compatibility": lifecycle,
                # Compatibility projection for existing consumers.  The typed
                # operation identity is the ordered source/consequence pair.
                "operation": source_operation if endomorphism else operation_pair,
                "source_operation": source_operation,
                "consequence_operation": consequence_operation,
                "transport_kind": "endomorphism" if endomorphism else "arrow_morphism",
                "observed_relation": observed_relation,
                "operation_identity_sha256": _stable_json_sha256(operation_pair),
                "source_exact_lowering_variants": source_fiber[
                    "exact_lowering_variants"
                ],
                "consequence_exact_lowering_variants": consequence_fiber[
                    "exact_lowering_variants"
                ],
                "exact_lowering_variants": (
                    source_fiber["exact_lowering_variants"] if endomorphism else []
                ),
                "component_selector_presentations": selector_scopes,
                "component_identity_status": (
                    "property_witness_only_requires_recurrence_or_object_identity"
                    if selector_scopes
                    else "no_component_selector_required"
                ),
                "observed_commutation": True,
                "global_equivariance_authorized": False,
                "quotient_authorized": False,
                "carrier_promotion_authorized": False,
                "square_edges": {
                    "source_state_sha256": _stable_json_sha256(prior.s),
                    "target_state_sha256": _stable_json_sha256(candidate.s),
                    "source_consequence_sha256": _stable_json_sha256(prior.s_next),
                    "target_consequence_sha256": _stable_json_sha256(candidate.s_next),
                },
            }
            payload["square_identity_sha256"] = _stable_json_sha256(payload)
            transports.append(payload)
    return transports


def _observed_frontier_source(
    project: Path,
    regression: dict[str, Any],
) -> dict[str, Any]:
    """Join a current regression identity to its evaluable carrier bytes."""

    project = project.resolve()
    frontier = repair_frontier_fields(regression)
    target_sha = frontier["sha256"]
    target_ref = frontier["source_ref"]
    if target_ref and target_sha:
        try:
            resolved = resolve_repair_frontier(project, regression)
            path = Path(resolved["path"])
            source = path.read_text(encoding="utf-8", errors="ignore")
            return {
                "frontier": resolved,
                "path": path,
                "source": source,
                "record": {
                    "submission": resolved["source_ref"],
                    "sha": resolved["sha256"],
                },
            }
        except (OSError, ValueError):
            pass

    # An evaluated candidate can be newer than candidate memory and need not
    # yet own the durable repair-frontier role.  The mutable project entrypoint
    # is admissible here only after its bytes match the current receipt digest;
    # the join confers diagnostic access, not PATCH_BASE or promotion authority.
    root = project / "test_model.py"
    try:
        root_sha = hashlib.sha256(root.read_bytes()).hexdigest()
        if target_sha and _sha_prefix_matches(root_sha, target_sha):
            return {
                "frontier": {**frontier, "sha256": root_sha},
                "path": root,
                "source": root.read_text(encoding="utf-8", errors="ignore"),
                "record": {"submission": "test_model.py", "sha": root_sha},
            }
    except OSError:
        pass

    records = admissible_candidate_memory_records(project)
    candidates = [
        row for row in records
        if (
            target_ref and str(row.get("submission") or "") == target_ref
        ) or (
            target_sha and _sha_prefix_matches(str(row.get("sha") or ""), target_sha)
        )
    ]
    if not candidates:
        raise ValueError("regression carrier identity has no visible source")
    record = max(
        candidates,
        key=lambda row: (
            int(row.get("visible_checked_rows") or 0),
            str(row.get("observed_at_utc") or ""),
        ),
    )
    source = candidate_memory_source(project, record)
    if not source.strip():
        raise ValueError("regression carrier source is empty")
    submission = str(record.get("submission") or "")
    path = project / submission if submission else None
    if path is not None:
        try:
            path = path.resolve()
            path.relative_to(project.resolve())
        except (OSError, ValueError):
            path = None
    return {
        "frontier": frontier,
        "path": path,
        "source": source,
        "record": record,
    }


def _active_frontier_observation_triple(
    project: Path,
    regression: dict[str, Any],
    *,
    margin: int = 2,
) -> dict[str, Any]:
    """Return a chart-bound source/prediction/consequence observation triple.

    The triple is the identity.  The axis-aligned window is only this adapter's
    bounded presentation of it; other adapters may lower the same contract to
    token spans, tensors, graphs, volumes, or another local chart.
    """
    comparison = regression.get("quotient_comparison")
    if not isinstance(comparison, dict):
        return {}
    frontier = repair_frontier_fields(regression)
    use_best = frontier["role"] == "best_admissible_prior"
    quotient_key = (
        "best_prior_top_quotient" if use_best else "candidate_top_quotient"
    )
    quotient = comparison.get(quotient_key)
    if not isinstance(quotient, dict):
        return {}
    row_index = _as_int(quotient.get("first_row"))
    bbox = quotient.get("bbox") if isinstance(quotient.get("bbox"), list) else []
    if row_index is None or len(bbox) != 4:
        return {}

    try:
        observed_frontier = _observed_frontier_source(project, regression)
    except (OSError, TypeError, ValueError):
        return {}
    record = observed_frontier["record"]
    source = observed_frontier["source"]
    try:
        from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
        from ztare.worldmodel.episode_log import EpisodeLog
        from ztare.worldmodel.evidence_quotients import resolve_episode_ref

        model = _load_carrier_from_source(
            source,
            Path(str(record.get("submission") or "frontier.py")).name,
            project,
        )
        trace = regression.get("counterexample_trace")
        if not isinstance(trace, dict):
            trace = record.get("counterexample_trace")
        evidence_ref = (
            str(trace.get("evidence_ref") or "")
            if isinstance(trace, dict)
            else ""
        ) or "raw/episodes/episode_001.jsonl"
        episode_path = resolve_episode_ref(project, evidence_ref)
        # The counterexample inspector owns one chart-bound observation.  It
        # may propose an operation from that row, but row proximity in an
        # append-only bank cannot grant recurrence authority.  The downstream
        # operation-domain selector already quantifies the conjecture over the
        # complete evidence snapshot and owns recurrence/admissibility.
        context_indices = {row_index}
        transitions = EpisodeLog.read_jsonl_indices(
            episode_path,
            context_indices,
        )
        transition = transitions[row_index]
        predicted = model(transition.s, transition.a, transition.t)
    except Exception:
        return {}
    actual = transition.s_next
    if not isinstance(predicted, (list, tuple)) or not predicted:
        return {}
    try:
        r0, c0, r1, c1 = [int(value) for value in bbox]
    except Exception:
        return {}
    component_windows = _triple_component_windows(
        transition.s,
        predicted,
        actual,
        margin=margin,
    )
    if not component_windows:
        height = min(len(transition.s), len(predicted), len(actual))
        width = min(
            len(transition.s[0]) if transition.s else 0,
            len(predicted[0]) if predicted else 0,
            len(actual[0]) if actual else 0,
        )
        component_windows = [[
            max(0, r0 - margin),
            max(0, c0 - margin),
            min(height - 1, r1 + margin),
            min(width - 1, c1 + margin),
        ]]

    sidecar_path = episode_path.with_name(episode_path.stem + ".identity.json")
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        sidecar = {}
    from ztare.common.observation_chart import (
        CounterexampleObservationTriple,
        ObservationChart,
    )
    from ztare.worldmodel.episode_log import (
        EpisodeIdentityBindingError,
        declared_episode_observation_chart,
    )

    try:
        source_chart = declared_episode_observation_chart(sidecar)
    except EpisodeIdentityBindingError:
        return {}
    if source_chart is None:
        source_chart = ObservationChart(
            chart_id="adapter_transition_packet",
            chart_version="v1",
            packet_schema_id="ztare-transition-observation-v1",
            coordinate_axes=("state", "intervention", "successor"),
            authority="episode_collector",
            parameters={},
        )
    local_chart = ObservationChart(
        chart_id="adapter_local_counterexample_view",
        chart_version="v1",
        packet_schema_id="ztare-counterexample-observation-triple-v1",
        coordinate_axes=("region", "row", "column"),
        authority="interactive_grid_adapter",
        parameters={
            "source_chart_sha256": source_chart.sha256,
            "localization": {
                "presentation_kind": "triple_relation_component_windows",
                "windows": component_windows,
                "residual_region": [r0, c0, r1, c1],
                "authority": "diagnostic_presentation_only",
            },
        },
    )
    transition_identity = getattr(transition, "identity", None)
    evidence_epoch_sha256 = str(sidecar.get("episode_sha256") or "").strip()
    if not evidence_epoch_sha256:
        try:
            evidence_epoch_sha256 = hashlib.sha256(episode_path.read_bytes()).hexdigest()
        except OSError:
            return {}
    triple_object = CounterexampleObservationTriple(
        chart=local_chart,
        evidence_epoch_sha256=evidence_epoch_sha256,
        evidence_ref=evidence_ref,
        observation_ref=f"{evidence_ref}#transition:{row_index}",
        proposal_identity={
            "carrier_sha": str(record.get("sha") or ""),
        },
        intervention=int(transition.a),
        source_observation=_project_grid_windows(transition.s, component_windows),
        proposed_consequence=_project_grid_windows(predicted, component_windows),
        observed_consequence=_project_grid_windows(actual, component_windows),
        transition_identity=(
            transition_identity.to_dict()
            if hasattr(transition_identity, "to_dict")
            else {}
        ),
    )
    triple = triple_object.to_dict()
    event_candidates = _catalog_residual_event_candidates(
        [],
        transition,
        predicted,
        actual,
    )
    return {
        **triple,
        "observation_sha256": triple_object.sha256,
        "proposal_provenance": {
            "carrier_ref": str(record.get("submission") or ""),
            "frontier_role": "best_admissible_prior" if use_best else "evaluated_candidate",
        },
        "frontier_role": "best_admissible_prior" if use_best else "evaluated_candidate",
        "source_observation_chart": source_chart.to_dict(),
        "catalog_residual_event_candidates": event_candidates,
    }


def _catalog_residual_event_candidates(
    prior_transitions: list[tuple[int, Any]],
    transition: Any,
    proposed: Any,
    observed: Any,
    *,
    min_role_support: int = 2,
    max_candidates: int = 2,
) -> list[dict[str, Any]]:
    """Reuse catalog operations to factor a residual into cause and consequence.

    The current row alone exposes coordinate/value properties.  Recent rows in
    the same adapter-attested lifecycle establish both the moving-object role
    and, when a residual sits under a vacated component, recurrence of the
    departure boundary across interventions.  The result is proposal evidence
    only: replay still decides whether the lowering is a law.
    """
    if not isinstance(proposed, (list, tuple)) or not proposed:
        return []
    wrong = [
        (row, col)
        for row in range(min(len(proposed), len(observed)))
        for col in range(min(len(proposed[row]), len(observed[row])))
        if proposed[row][col] != observed[row][col]
    ]
    if not wrong:
        return []

    from ztare.worldmodel.spec_abduction import (
        _abduce_translate_block,
        _diff,
        _display_event_candidates,
    )

    current_identity = getattr(transition, "identity", None)

    def compatible_law_observation(prior: Any) -> bool:
        """Whether two rows may witness recurrence of a dynamics operation.

        Recurrence inside one epoch may support an operation hypothesis.
        A row from another epoch requires an explicit chart/object transport
        certificate; matching dimensions cannot supply that authority.
        """
        prior_identity = getattr(prior, "identity", None)
        if (
            current_identity is not None
            and prior_identity is not None
            and getattr(current_identity, "is_authoritative", False)
            and getattr(prior_identity, "is_authoritative", False)
        ):
            if (
                getattr(current_identity, "is_boundary", False)
                or getattr(prior_identity, "is_boundary", False)
                or current_identity.source_epoch != current_identity.target_epoch
                or prior_identity.source_epoch != prior_identity.target_epoch
            ):
                return False
            return (
                current_identity.source_epoch == prior_identity.source_epoch
                and len(prior.s) == len(transition.s)
                and bool(prior.s)
                and bool(transition.s)
                and len(prior.s[0]) == len(transition.s[0])
            )
        return (
            len(prior.s) == len(transition.s)
            and bool(prior.s)
            and bool(transition.s)
            and len(prior.s[0]) == len(transition.s[0])
        )

    def compress_stateful_consequence(candidate: Mapping[str, Any]):
        """Lift repeated fixed effects into one whole-content transition law.

        The current residual anchors the consequence object.  Earlier firings
        of the same boundary contribute additional presentations; a bounded
        component join recovers the object's full support.  The shared spec
        miner then decides whether those observations form a functional,
        non-cell-wise machine.  This keeps state count, coordinates, and values
        in the adapter lowering rather than operation identity.
        """
        from ztare.worldmodel.spec_abduction import (
            _gap_tolerant_components,
            _mine_content_state_machine,
        )
        from ztare.worldmodel.spec_catalog import region_event_triggered

        trigger = {
            key: candidate[key]
            for key in ("mover_colors", "rect", "edge")
            if key in candidate
        }
        if set(trigger) != {"mover_colors", "rect", "edge"}:
            return None
        observations = [
            (row_index, prior)
            for row_index, prior in prior_transitions
            if compatible_law_observation(prior)
        ] + [(None, transition)]
        fired = [
            (row_index, item)
            for row_index, item in observations
            if region_event_triggered(item.s, item.s_next, trigger)
        ]
        if len(fired) < 2:
            return None
        changed = {
            (row, col)
            for _row_index, item in fired
            for row in range(min(len(item.s), len(item.s_next)))
            for col in range(min(len(item.s[row]), len(item.s_next[row])))
            if item.s[row][col] != item.s_next[row][col]
        }
        anchor = {(int(row), int(col)) for row, col in wrong}
        components = [
            component
            for component in _gap_tolerant_components(changed)
            if anchor.issubset(component)
        ]
        if len(components) != 1:
            return None
        component = components[0]
        rect = [int(value) for value in trigger["rect"]]
        if any(rect[0] <= row <= rect[2] and rect[1] <= col <= rect[3]
               for row, col in component):
            return None
        region = [
            min(row for row, _col in component),
            min(col for _row, col in component),
            max(row for row, _col in component),
            max(col for _row, col in component),
        ]
        def content(grid: Any) -> tuple[Any, ...]:
            return tuple(
                grid[row][col]
                for row in range(region[0], region[2] + 1)
                for col in range(region[1], region[3] + 1)
            )

        transition_observations = []
        support_rows = []
        for row_index, item in fired:
            before, after = content(item.s), content(item.s_next)
            if before == after:
                continue
            transition_observations.append((before, after))
            if row_index is not None:
                support_rows.append(int(row_index))
        machine = _mine_content_state_machine(transition_observations)
        if machine is None:
            return None
        state_transition, states = machine
        lowering = {
            key: value
            for key, value in candidate.items()
            if key not in {"writes", "toggle", "cycle", "when_region"}
        }
        lowering.update({
            "region": region,
            "content_states": [list(state) for state in states],
            "state_transition": state_transition,
        })
        return {
            "lowering": lowering,
            "support_rows": sorted(set(support_rows)),
            "state_count": len(states),
            "transition_observation_count": len(transition_observations),
            "region": region,
        }

    role_support: dict[tuple[int, ...], dict[str, Any]] = {}
    role_observations = [*prior_transitions, (None, transition)]
    for row_index, prior in role_observations:
        if not compatible_law_observation(prior):
            continue
        proposals = _abduce_translate_block(
            prior.s,
            prior.s_next,
            _diff(prior.s, prior.s_next),
        )
        seen_on_row: set[tuple[int, ...]] = set()
        for proposal in proposals:
            palette = tuple(sorted(int(v) for v in proposal.get("match_colors", [])))
            if len(palette) < 2 or palette in seen_on_row:
                continue
            seen_on_row.add(palette)
            support = role_support.setdefault(
                palette,
                {
                    "rows": [],
                    "current_observation": False,
                    "interventions": set(),
                    "displacements": set(),
                },
            )
            if row_index is None:
                support["current_observation"] = True
            else:
                support["rows"].append(int(row_index))
            support["interventions"].add(int(prior.a))
            support["displacements"].add(
                (int(proposal.get("dy", 0)), int(proposal.get("dx", 0)))
            )

    supported_roles = [
        (palette, support)
        for palette, support in role_support.items()
        if (
            support["current_observation"]
            or len(set(support["rows"])) >= min_role_support
        )
    ]
    supported_roles.sort(
        key=lambda item: (-len(set(item[1]["rows"])), -len(item[0]), item[0])
    )
    if not supported_roles:
        return []

    results: list[dict[str, Any]] = []
    for palette, support in supported_roles:
        # A residual supported inside the mover's step-start component denotes
        # a candidate departure relation, not the coordinate at which this one
        # intervention happened to place the mover.  Require another witnessed
        # departure from the same object/site under a distinct intervention
        # before giving that boundary the reusable-operation status consumed by
        # the deterministic compiler.  This is adapter geometry; the common
        # task/route/compiler layers see only the typed operation and authority.
        boundary_evidence: dict[str, Any] = {}
        try:
            from ztare.worldmodel.spec_catalog import _qualifying_components

            wrong_set = {(int(row), int(col)) for row, col in wrong}
            seen_boundaries: set[tuple[Any, ...]] = set()
            for proposal in _abduce_translate_block(
                transition.s,
                proposed,
                _diff(transition.s, proposed),
            ):
                proposal_palette = tuple(
                    sorted(int(value) for value in proposal.get("match_colors", []))
                )
                if proposal_palette != palette:
                    continue
                dy = int(proposal.get("dy", 0))
                dx = int(proposal.get("dx", 0))
                for component in _qualifying_components(transition.s, proposal):
                    component_set = {(int(row), int(col)) for row, col in component}
                    if not wrong_set or not wrong_set.issubset(component_set):
                        continue
                    destination = {(row + dy, col + dx) for row, col in component_set}
                    height = len(proposed)
                    width = len(proposed[0]) if proposed else 0
                    if not destination or any(
                        not (0 <= row < height and 0 <= col < width)
                        for row, col in destination
                    ):
                        continue
                    if not all(
                        proposed[row + dy][col + dx] == transition.s[row][col]
                        for row, col in component_set
                    ):
                        continue
                    source_rect = [
                        min(row for row, _col in component_set),
                        min(col for _row, col in component_set),
                        max(row for row, _col in component_set),
                        max(col for _row, col in component_set),
                    ]
                    key = (*source_rect, dy, dx)
                    if key in seen_boundaries:
                        continue
                    seen_boundaries.add(key)
                    prior_rows: list[int] = []
                    interventions = {int(transition.a)}
                    for row_index, prior in prior_transitions:
                        if not compatible_law_observation(prior):
                            continue
                        if not all(
                            prior.s[row][col] == transition.s[row][col]
                            for row, col in component_set
                        ):
                            continue
                        # Palette membership is a property: revealed substrate
                        # may reuse mover values.  Departure means the component
                        # presentation itself no longer occupies its source
                        # support, so compare the identity-bearing cell map.
                        if all(
                            prior.s_next[row][col] == transition.s[row][col]
                            for row, col in component_set
                        ):
                            continue
                        if not all(
                            prior.s_next[row][col] == observed[row][col]
                            for row, col in wrong_set
                        ):
                            continue
                        prior_rows.append(int(row_index))
                        interventions.add(int(prior.a))
                    boundary_evidence = {
                        "relation": "residual_on_vacated_mover_component",
                        "source_rect": source_rect,
                        "current_displacement": [dy, dx],
                        "prior_support_rows": sorted(set(prior_rows)),
                        "support_count": 1 + len(set(prior_rows)),
                        "interventions": sorted(interventions),
                        "distinct_interventions": len(interventions),
                    }
                    break
                if boundary_evidence:
                    break
        except (IndexError, TypeError, ValueError):
            boundary_evidence = {}

        candidates = _display_event_candidates(
            [(0, transition, proposed, wrong)],
            list(palette),
            [],
            [],
        )
        candidates = [
            candidate
            for candidate in candidates
            if tuple(candidate.get("mover_colors", ())) == palette
        ]
        for candidate in candidates[:1]:
            if boundary_evidence:
                candidate = {
                    **candidate,
                    "rect": list(boundary_evidence["source_rect"]),
                    "edge": "exit",
                }

            from ztare.worldmodel.spec_catalog import region_event_triggered

            consequence_support_rows: list[int] = []
            consequence_observations: set[str] = set()
            support_observations = [
                (row_index, prior)
                for row_index, prior in prior_transitions
                if compatible_law_observation(prior)
            ] + [(None, transition)]
            for support_row, item in support_observations:
                if not region_event_triggered(item.s, item.s_next, candidate):
                    continue
                writes_hold = all(
                    0 <= int(cell[0]) < len(item.s_next)
                    and 0 <= int(cell[1]) < len(item.s_next[int(cell[0])])
                    and int(item.s_next[int(cell[0])][int(cell[1])]) == int(color)
                    for color, cells in (candidate.get("writes") or [])
                    for cell in cells
                )
                if not writes_hold:
                    continue
                observation_identity = _stable_json_sha256({
                    "state": item.s,
                    "intervention": item.a,
                    "consequence": item.s_next,
                })
                consequence_observations.add(observation_identity)
                if support_row is not None:
                    consequence_support_rows.append(int(support_row))
            operation_recurrent = len(consequence_observations) >= 2
            boundary_recurrent = bool(
                boundary_evidence
                and int(boundary_evidence.get("support_count") or 0) >= 2
            )
            state_machine = compress_stateful_consequence(candidate)
            if state_machine is not None:
                candidate = state_machine["lowering"]
            edge = str(candidate.get("edge") or "")
            if state_machine is not None:
                operation_identity = {
                    "relation": "boundary_conditioned_state_transition",
                    "subject_role": "moves_under_actions",
                    "boundary": "departure" if edge == "exit" else "arrival",
                    "consequence_role": "finite_state_object",
                }
            elif boundary_evidence and edge == "exit":
                operation_identity = {
                    "relation": "covered_uncovered",
                    "subject_role": "moves_under_actions",
                    "boundary": "departure",
                    "consequence_role": "revealed_substrate",
                }
            else:
                operation_identity = {
                    "relation": "boundary_conditioned_consequence",
                    "subject_role": "moves_under_actions",
                    "boundary": "departure" if edge == "exit" else "arrival",
                    "consequence_role": "remote_effect",
                }
            result = {
                "schema": "ztare-catalog-residual-event-candidate-v1",
                "authority": "diagnostic_candidate_only",
                "operation_identity": operation_identity,
                "operation_identity_sha256": _stable_json_sha256(operation_identity),
                "lowering_kind": str(candidate.get("op") or ""),
                "role_evidence": {
                    "role": "moves_under_actions",
                    "source_operation": "translate_block",
                    "support_rows": sorted(set(support["rows"])),
                    "support_count": len(set(support["rows"])),
                    "interventions": sorted(support["interventions"]),
                    "displacements": [
                        list(value) for value in sorted(support["displacements"])
                    ],
                },
                "boundary_evidence": boundary_evidence,
                "consequence_object_evidence": {
                    "operation_support_rows": sorted(
                        set(consequence_support_rows)
                    ),
                    "distinct_operation_observations": len(
                        consequence_observations
                    ),
                    "cross_epoch_recurrence_is_evidence_not_transport": True,
                },
                **(
                    {
                        "operation_support_rows": state_machine["support_rows"],
                        "state_machine_evidence": {
                            "region": state_machine["region"],
                            "state_count": state_machine["state_count"],
                            "transition_observation_count": state_machine[
                                "transition_observation_count"
                            ],
                            "authority": "finite_banked_witness",
                        },
                    }
                    if state_machine is not None
                    else {}
                ),
                **(
                    {
                        "operation_support_rows": sorted(
                            set(consequence_support_rows)
                        )
                    }
                    if state_machine is None and consequence_support_rows
                    else {}
                ),
                "lowering": candidate,
                "lowering_sha256": _stable_json_sha256(candidate),
                "identity_status": (
                    "catalog_operation_reuse_candidate"
                    if (
                        boundary_recurrent
                        or operation_recurrent
                        or state_machine is not None
                    )
                    else (
                        "boundary_recurrence_required"
                        if boundary_evidence
                        else "operation_recurrence_required"
                    )
                ),
                "promotion_authorized": False,
            }
            results.append(result)
            if len(results) >= max_candidates:
                return results
    return results


def _triple_component_windows(
    source: Any,
    predicted: Any,
    actual: Any,
    *,
    margin: int,
) -> list[list[int]]:
    """Localize every changed cell in the source/proposal/observation triple."""

    height = min(len(source), len(predicted), len(actual))
    width = min(
        len(source[0]) if source else 0,
        len(predicted[0]) if predicted else 0,
        len(actual[0]) if actual else 0,
    )
    mismatches = {
        (row, col)
        for row in range(height)
        for col in range(width)
        if (
            predicted[row][col] != actual[row][col]
            or source[row][col] != actual[row][col]
        )
    }
    boxes: list[list[int]] = []
    while mismatches:
        stack = [mismatches.pop()]
        component: list[tuple[int, int]] = []
        while stack:
            row, col = stack.pop()
            component.append((row, col))
            for neighbor in (
                (row - 1, col),
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
            ):
                if neighbor in mismatches:
                    mismatches.remove(neighbor)
                    stack.append(neighbor)
        rows = [row for row, _col in component]
        cols = [col for _row, col in component]
        boxes.append([
            max(0, min(rows) - margin),
            max(0, min(cols) - margin),
            min(height - 1, max(rows) + margin),
            min(width - 1, max(cols) + margin),
        ])
    return sorted(boxes)


def _project_grid_windows(grid: Any, windows: list[list[int]]) -> dict[str, Any]:
    return {
        "grid_shape": [len(grid), len(grid[0]) if grid else 0],
        "windows": [
            {
                "bbox": box,
                "values": [
                    list(grid[row][box[1]:box[3] + 1])
                    for row in range(box[0], box[2] + 1)
                ],
            }
            for box in windows
        ],
    }


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
    if not _regression_payload_is_current(project, payload):
        return {}
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
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path)


def _shaish(path: Path) -> str:
    try:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001
        return ""
