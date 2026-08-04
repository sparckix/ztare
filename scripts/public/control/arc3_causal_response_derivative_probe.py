#!/usr/bin/env python3
"""Compile H97's response derivative before any controller contact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


REPO = Path(__file__).resolve().parents[3]
CONTROL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(CONTROL))

from arc3_paired_recall_probe import (  # noqa: E402
    _atomic_json,
    _file_sha256,
    _relative_ref,
)
import arc3_instrumented_proposal_probe as proposal_probe  # noqa: E402
from ztare.common.causal_response_derivative import (  # noqa: E402
    compile_causal_response_derivative,
    compile_causal_response_program,
    compile_residual_proposal_transition,
    compile_residual_response_family,
    compile_response_reproduction_estimate,
    proposal_satisfies_residual_response,
    response_derivative_event_family_binding_receipt,
)
from ztare.common.instrumented_proposal_plasticity import (  # noqa: E402
    InstrumentedProposalOutcome,
    estimate_instrumented_plasticity,
)
from ztare.common.llm_runtime import (  # noqa: E402
    bootstrap_dotenv_from_repo_root,
)
from ztare.common.object_basin_response import (  # noqa: E402
    object_contract_from_receipt,
    object_proposal_from_receipt,
    object_response_family_from_receipt,
    object_transition_from_receipt,
)
from ztare.common.object_lineage_transport import (  # noqa: E402
    CausalObjectLineageTransport,
    causal_object_lineage_transport_from_receipt,
)
from ztare.common.object_linked_judgment import (  # noqa: E402
    ObjectLinkedControllerProposal,
    ObjectReferenceAuthority,
)
from ztare.common.persistent_reasoning_controller import (  # noqa: E402
    PersistentResponsesToolThread,
    compile_responses_fork_authority,
)
from ztare.common.wake_sleep_credit_router import MemoryScope  # noqa: E402
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.observation_object_catalog import (  # noqa: E402
    GridObjectCatalog,
    GridObjectCatalogPresentation,
    compile_catalog_from_observation,
    compile_catalog_presentation,
    decode_grid_rle_rows,
)
from arc3_responses_agent_probe import (  # noqa: E402
    _outcome_metrics,
    _transition_identity_receipt,
    grid_png_data_url,
    observation_content,
    settled_observation_receipt,
)


SCHEMA = "ztare-arc3-causal-response-derivative-v1"
LIVE_SCHEMA = "ztare-arc3-causal-response-derivative-live-v1"


def _plan_tool(action_arity: int) -> dict[str, Any]:
    return {
        "type": "function",
        "name": "commit_arc_plan",
        "description": (
            "Commit one charged environment action and the object path that "
            "currently justifies it."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "integer",
                    "enum": list(range(int(action_arity))),
                },
                "prediction": {"type": "string"},
                "plan_summary": {"type": "string"},
                "uncertainty": {"type": "string"},
                "controlled_object_handle": {"type": "string"},
                "ordered_waypoint_handles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 16,
                },
            },
            "required": [
                "action",
                "prediction",
                "plan_summary",
                "uncertainty",
                "controlled_object_handle",
                "ordered_waypoint_handles",
            ],
            "additionalProperties": False,
        },
    }


def _controller_instructions(
    *,
    budget: int,
    action_arity: int,
) -> str:
    return (
        "You are controlling an unknown interactive 2D grid game. Infer its "
        "rules only from the supplied observation/action chronology. Complete "
        "as many levels as possible within the fixed budget of "
        f"{int(budget)} charged actions after the restored prefix. On every "
        "turn call commit_arc_plan exactly once. Action indices are stable "
        f"integers 0 through {int(action_arity) - 1}. The current object "
        "catalog uses observation-local handles. controlled_object_handle is "
        "the object you expect the action to move or manipulate; "
        "ordered_waypoint_handles are the distinct objects you expect it to "
        "contact or use, in order. Use only handles in the current catalog. "
        "Treat experimental evidence as revisable evidence, not a command. "
        "Preserve discoveries across turns, test uncertain hypotheses with "
        "discriminating actions, and do not assume puzzle-specific knowledge."
    )


def _response_controller_scope(
    source_scope: MemoryScope,
    *,
    model: str,
    reasoning_effort: str,
    reasoning_context: str,
    instructions: str,
    tool: Mapping[str, Any],
) -> tuple[MemoryScope, dict[str, Any]]:
    controller_identity = {
        "kind": "persistent_responses_reasoner",
        "model": str(model),
        "reasoning_effort": str(reasoning_effort),
        "reasoning_context": str(reasoning_context),
        "store": True,
        "instructions_sha256": _sha({"instructions": instructions}),
        "tool_sha256": _sha(dict(tool)),
    }
    target = MemoryScope(
        task_sha256=source_scope.task_sha256,
        controller_sha256=_sha(controller_identity),
        context_sha256=source_scope.context_sha256,
        choice_set_sha256=source_scope.choice_set_sha256,
        action_vocabulary_sha256=(
            source_scope.action_vocabulary_sha256
        ),
    )
    receipt = {
        "schema": LIVE_SCHEMA,
        "kind": "controller_scope_transport",
        "source_scope_sha256": source_scope.sha256,
        "target_scope": target.to_receipt(),
        "target_scope_sha256": target.sha256,
        "preserved_coordinates": [
            "task_sha256",
            "context_sha256",
            "choice_set_sha256",
            "action_vocabulary_sha256",
        ],
        "changed_coordinates": ["controller_sha256"],
        "controller_identity": controller_identity,
    }
    return target, {**receipt, "sha256": _sha(receipt)}


def _handle_map(
    presentation_receipt: Mapping[str, Any],
) -> dict[str, str]:
    pairs = {
        str(row["object_ref"]): str(row["handle"])
        for row in presentation_receipt.get("handle_bindings") or ()
    }
    if len(pairs) != len(
        presentation_receipt.get("handle_bindings") or ()
    ):
        raise ValueError("presentation receipt has ambiguous object handles")
    return pairs


def _pad_utf8(text: str, target_bytes: int) -> str:
    current = len(text.encode("utf-8"))
    if current > int(target_bytes):
        raise ValueError("intervention core exceeds frozen byte budget")
    padded = text + (" " * (int(target_bytes) - current))
    if len(padded.encode("utf-8")) != int(target_bytes):
        raise AssertionError("UTF-8 padding drifted")
    return padded


def _compile_interventions(
    *,
    derivative,
    presentation_receipt: Mapping[str, Any],
    target_scope: MemoryScope,
    target_bytes: int,
    primitive_action_cost: float,
) -> dict[str, Any]:
    residual = derivative.residual_contract
    if derivative.status != "derived" or residual is None:
        raise ValueError("intervention compiler needs a derived response")
    handles = _handle_map(presentation_receipt)
    causal_core = {
        "schema": LIVE_SCHEMA,
        "kind": "causal_response_derivative_intervention",
        "evidence_status": (
            "two_randomized_externally_settled_parent_responses"
        ),
        "source_program_sha256": residual.source_program_sha256,
        "lineage_transport_sha256": residual.lineage_transport_sha256,
        "residual_program": {
            "controlled_object_handle": handles[
                residual.required_controlled_object_ref
            ],
            "ordered_waypoint_handles": [
                handles[value] for value in residual.pending_waypoint_refs
            ],
        },
        "completed_subgoals": [
            {
                "object_handle": handles[value],
                "status": "discharged_before_current_decision",
            }
            for value in residual.discharged_waypoint_refs
        ],
        "use_rule": (
            "Revise the current action and object path only if this settled "
            "residual changes the best plan. Do not reinsert discharged "
            "subgoals."
        ),
    }
    placebo_core = {
        "schema": LIVE_SCHEMA,
        "kind": "byte_matched_context_control",
        "evidence_status": "true_non_target_observation_facts",
        "facts": [
            "Object handles are local to the current exact observation.",
            "Action meanings must be inferred from settled transitions.",
            "Visible overlap can temporarily occlude an object occurrence.",
            "An unchanged visible frame does not establish task completion.",
        ],
        "use_rule": (
            "Revise the current action and object path only if these general "
            "facts change the best plan."
        ),
    }
    causal_core_text = json.dumps(
        causal_core,
        sort_keys=True,
        separators=(",", ":"),
    )
    placebo_core_text = json.dumps(
        placebo_core,
        sort_keys=True,
        separators=(",", ":"),
    )
    causal_text = _pad_utf8(causal_core_text, target_bytes)
    placebo_text = _pad_utf8(placebo_core_text, target_bytes)
    causal_rendered_sha = _sha({"rendered_text": causal_text})
    placebo_rendered_sha = _sha({"rendered_text": placebo_text})
    revision_core = {
        "kind": "causal_response_derivative_intervention_revision",
        "scope_sha256": target_scope.sha256,
        "source_program_sha256": residual.source_program_sha256,
        "lineage_transport_sha256": residual.lineage_transport_sha256,
        "rendered_content_sha256": causal_rendered_sha,
        "primitive_action_cost": float(primitive_action_cost),
    }
    return {
        "causal_core": causal_core,
        "placebo_core": placebo_core,
        "causal_text": causal_text,
        "placebo_text": placebo_text,
        "causal_rendered_sha256": causal_rendered_sha,
        "placebo_rendered_sha256": placebo_rendered_sha,
        "causal_intervention_revision_sha256": _sha(revision_core),
        "rendered_utf8_bytes_per_condition": int(target_bytes),
        "primitive_action_cost": float(primitive_action_cost),
    }


def _sha(payload: Mapping[str, Any]) -> str:
    return proposal_probe._sha(payload)


def _load_checked(
    path: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    if _file_sha256(path) != str(expected_sha256):
        raise ValueError(f"H97 source drifted: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _source_program(
    *,
    spec: Mapping[str, Any],
    base: Path,
    h96_manifest: Mapping[str, Any],
):
    source_spec = dict(spec["source_response"])
    family = object_response_family_from_receipt(
        h96_manifest["source_response_family"]
    )
    if family.sha256 != str(source_spec["family_sha256"]):
        raise ValueError("H97 source family drifted")
    responses = [
        row for row in family.responses
        if row.sha256 == str(source_spec["response_sha256"])
    ]
    if len(responses) != 1:
        raise ValueError("H97 source response drifted")
    response = responses[0]
    contract = object_contract_from_receipt(
        h96_manifest["source_contract"]
    )
    if contract.sha256 != str(source_spec["contract_sha256"]):
        raise ValueError("H97 source contract drifted")
    witnesses = []
    evidence = []
    for row in source_spec["supported_offer_witnesses"]:
        arm_path = (base / str(row["arm_ref"])).resolve()
        arm = _load_checked(
            arm_path,
            str(row["arm_file_sha256"]),
        )
        instrumented = arm["probe"]["turns"][0][
            "instrumented_proposal"
        ]
        witnesses.append((
            object_transition_from_receipt(
                instrumented["transition"]
            ),
            object_proposal_from_receipt(
                instrumented["pre_proposal"]
            ),
            object_proposal_from_receipt(
                instrumented["post_proposal"]
            ),
        ))
        evidence.append(
            f"{_relative_ref(arm_path)}#sha256="
            f"{row['arm_file_sha256']}"
        )
    program = compile_causal_response_program(
        family,
        response,
        contract,
        tuple(witnesses),
        evidence_refs=tuple(evidence),
    )
    compiler = dict(spec["response_program_compiler"])
    if (
        program.status != "compiled"
        or program.support_count
        != int(compiler["minimum_supported_offer_witnesses"])
        or program.controlled_object_ref
        != str(compiler["expected_source_controlled_object_ref"])
        or list(program.ordered_waypoint_refs)
        != list(compiler["expected_source_waypoint_refs"])
    ):
        raise ValueError("H97 source response program discriminator failed")
    return family, response, contract, program


def _missing_coevent_lineage(
    *,
    program,
    lineage,
    forbidden_refs,
) -> CausalObjectLineageTransport:
    roots = {
        program.controlled_object_ref,
        *program.ordered_waypoint_refs,
        *tuple(forbidden_refs),
    }
    return CausalObjectLineageTransport(
        source_observation_sha256=(
            lineage.source_observation_sha256
        ),
        source_catalog_sha256=lineage.source_catalog_sha256,
        target_observation_sha256=(
            lineage.target_observation_sha256
        ),
        target_catalog_sha256=lineage.target_catalog_sha256,
        required_source_object_refs=tuple(roots),
        traces=tuple(
            row for row in lineage.traces
            if row.source_object_ref in roots
        ),
        status="transportable",
        reason="projection_without_revision_coevent",
        evidence_refs=(
            f"source_lineage:{lineage.sha256}",
            "negative_control:coevent_removed",
        ),
    )


def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema") != (
        "ztare-arc3-causal-response-derivative-spec-v1"
    ):
        raise ValueError("wrong H97 experiment spec")
    base = spec_path.parent
    derivative_source = dict(spec["derivative_source"])
    h96_manifest_path = (
        base / str(derivative_source["h96_manifest_ref"])
    ).resolve()
    h96_result_path = (
        base / str(derivative_source["h96_result_ref"])
    ).resolve()
    h96_manifest = _load_checked(
        h96_manifest_path,
        str(derivative_source["h96_manifest_file_sha256"]),
    )
    h96_result = _load_checked(
        h96_result_path,
        str(derivative_source["h96_result_file_sha256"]),
    )
    if h96_result.get("verdict") != "rejected":
        raise ValueError("H97 requires the rejected H96 counterexample")
    family, response, source_contract, program = _source_program(
        spec=spec,
        base=base,
        h96_manifest=h96_manifest,
    )
    lineage = causal_object_lineage_transport_from_receipt(
        h96_manifest["lineage_transport"]
    )
    if lineage.sha256 != str(
        derivative_source["lineage_transport_sha256"]
    ):
        raise ValueError("H97 lineage receipt drifted")
    target_scope = MemoryScope(**h96_manifest["target_scope"])
    binding = response_derivative_event_family_binding_receipt(
        program,
        lineage,
    )
    derivative = compile_causal_response_derivative(
        program,
        lineage,
        target_scope=target_scope,
        target_intervention_revision_sha256=(
            h96_manifest["target_contract"][
                "intervention_revision_sha256"
            ]
        ),
        source_forbidden_controlled_object_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt=binding,
        event_selection_phase="pre_outcome",
        evidence_refs=(
            f"{_relative_ref(h96_manifest_path)}#sha256="
            f"{derivative_source['h96_manifest_file_sha256']}",
        ),
    )
    rule = dict(spec["derivative_rule"])
    residual = derivative.residual_contract
    if (
        derivative.status != "derived"
        or residual is None
        or [
            row.source_waypoint_ref for row in derivative.discharges
        ]
        != list(rule["expected_discharged_source_waypoint_refs"])
        or list(residual.pending_waypoint_refs)
        != list(rule["expected_target_pending_waypoint_refs"])
        or residual.required_controlled_object_ref
        != str(rule["expected_target_controlled_object_ref"])
    ):
        raise ValueError("H97 response derivative discriminator failed")

    fork_spec = dict(spec["matched_controller_fork"])
    live_spec = dict(spec["live_test"])
    tool = _plan_tool(int(h96_manifest["descendant_prefix"]["action_arity"]))
    instructions = _controller_instructions(
        budget=int(live_spec["post_prefix_actions_per_arm"]),
        action_arity=int(
            h96_manifest["descendant_prefix"]["action_arity"]
        ),
    )
    live_scope, scope_transport = _response_controller_scope(
        target_scope,
        model=str(fork_spec["model"]),
        reasoning_effort=str(fork_spec["reasoning_effort"]),
        reasoning_context=str(fork_spec["reasoning_context"]),
        instructions=instructions,
        tool=tool,
    )
    interventions = _compile_interventions(
        derivative=derivative,
        presentation_receipt=h96_manifest["target_presentation"],
        target_scope=live_scope,
        target_bytes=int(
            live_spec["presented_bytes_per_intervention"]
        ),
        primitive_action_cost=float(
            live_spec["post_prefix_actions_per_arm"]
        ),
    )
    live_derivative = compile_causal_response_derivative(
        program,
        lineage,
        target_scope=live_scope,
        target_intervention_revision_sha256=str(
            interventions["causal_intervention_revision_sha256"]
        ),
        source_forbidden_controlled_object_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt=binding,
        event_selection_phase="pre_outcome",
        evidence_refs=(
            f"construction_derivative:{derivative.sha256}",
            f"controller_scope_transport:{scope_transport['sha256']}",
        ),
    )
    live_residual = live_derivative.residual_contract
    if (
        live_derivative.status != "derived"
        or live_residual is None
        or live_residual.required_controlled_object_ref
        != residual.required_controlled_object_ref
        or live_residual.pending_waypoint_refs
        != residual.pending_waypoint_refs
        or live_residual.discharged_waypoint_refs
        != residual.discharged_waypoint_refs
        or live_residual.scope != live_scope
        or live_residual.intervention_revision_sha256
        != interventions["causal_intervention_revision_sha256"]
    ):
        raise ValueError("H97 live controller-scope derivative drifted")

    post_outcome = compile_causal_response_derivative(
        program,
        lineage,
        target_scope=target_scope,
        target_intervention_revision_sha256=(
            residual.intervention_revision_sha256
        ),
        source_forbidden_controlled_object_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt=binding,
        event_selection_phase="post_outcome",
        evidence_refs=("negative:post-outcome-selection",),
    )
    proxy = compile_causal_response_derivative(
        program,
        lineage,
        target_scope=target_scope,
        target_intervention_revision_sha256=(
            residual.intervention_revision_sha256
        ),
        source_forbidden_controlled_object_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt={
            **binding,
            "known_proxy_family_confuser": (
                "outcome-matched endpoint"
            ),
        },
        event_selection_phase="pre_outcome",
        evidence_refs=("negative:proxy-event-family",),
    )
    no_coevent_lineage = _missing_coevent_lineage(
        program=program,
        lineage=lineage,
        forbidden_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
    )
    no_coevent = compile_causal_response_derivative(
        program,
        no_coevent_lineage,
        target_scope=target_scope,
        target_intervention_revision_sha256=(
            residual.intervention_revision_sha256
        ),
        source_forbidden_controlled_object_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt=(
            response_derivative_event_family_binding_receipt(
                program,
                no_coevent_lineage,
            )
        ),
        event_selection_phase="pre_outcome",
        evidence_refs=("negative:coevent-removed",),
    )
    negative_derivatives = (
        post_outcome,
        proxy,
        no_coevent,
    )
    if (
        sum(row.status == "refused" for row in negative_derivatives)
        < int(
            spec["success_criterion"][
                "negative_derivative_refusal_count_minimum"
            ]
        )
    ):
        raise ValueError("H97 negative derivative controls failed")

    construction = dict(spec["construction_replay"])
    authority = ObjectReferenceAuthority(
        observation_sha256=lineage.target_observation_sha256,
        catalog_sha256=lineage.target_catalog_sha256,
        object_refs=tuple(
            row["object_ref"]
            for row in h96_manifest["target_catalog"]["objects"]
        ),
    )
    replay_rows = {}
    for assignment, ref_key, sha_key in (
        ("offer", "offer_arm_ref", "offer_arm_file_sha256"),
        (
            "withhold",
            "placebo_arm_ref",
            "placebo_arm_file_sha256",
        ),
    ):
        arm_path = (base / str(construction[ref_key])).resolve()
        arm = _load_checked(arm_path, str(construction[sha_key]))
        instrumented = arm["probe"]["turns"][0][
            "instrumented_proposal"
        ]
        replay_rows[assignment] = (
            compile_residual_proposal_transition(
                trial_ref=f"h96-construction:{assignment}",
                stratum_sha256="h96-construction-stratum",
                assignment=assignment,
                pre_proposal=object_proposal_from_receipt(
                    instrumented["pre_proposal"]
                ),
                post_proposal=object_proposal_from_receipt(
                    instrumented["post_proposal"]
                ),
                derivative=derivative,
                authority=authority,
            )
        )
    if (
        replay_rows["offer"].relation
        != str(construction["expected_derivative_offer_relation"])
        or replay_rows["withhold"].relation
        != str(
            construction["expected_derivative_placebo_relation"]
        )
    ):
        raise ValueError("H97 construction replay did not reclassify H96")

    reproduction_before = compile_response_reproduction_estimate(
        response_schema_sha256=program.sha256,
        parent_family_sha256s=(family.sha256,),
        promoted_child_family_sha256s=(),
        false_edge_count=0,
        primitive_action_cost=54.0,
        evidence_refs=(
            f"{_relative_ref(h96_result_path)}#sha256="
            f"{derivative_source['h96_result_file_sha256']}",
        ),
    )
    manifest_core = {
        "schema": SCHEMA,
        "kind": "experiment_manifest",
        "hypothesis_id": spec["hypothesis_id"],
        "spec_ref": _relative_ref(spec_path),
        "spec_sha256": _file_sha256(spec_path),
        "source_h96_manifest_ref": _relative_ref(h96_manifest_path),
        "source_h96_manifest_file_sha256": _file_sha256(
            h96_manifest_path
        ),
        "source_h96_result_ref": _relative_ref(h96_result_path),
        "source_h96_result_file_sha256": _file_sha256(
            h96_result_path
        ),
        "source_family": family.to_receipt(),
        "source_response": response.to_receipt(),
        "source_contract": source_contract.to_receipt(),
        "source_program": program.to_receipt(),
        "lineage_transport": lineage.to_receipt(),
        "event_family_binding": binding,
        "event_family_binding_sha256": _sha(binding),
        "response_derivative": derivative.to_receipt(),
        "live_controller_scope_transport": scope_transport,
        "live_controller_instructions": instructions,
        "live_controller_tool": tool,
        "live_interventions": interventions,
        "live_response_derivative": live_derivative.to_receipt(),
        "negative_derivatives": [
            row.to_receipt() for row in negative_derivatives
        ],
        "construction_replay": {
            key: value.to_receipt()
            for key, value in replay_rows.items()
        },
        "reproduction_before_h97": (
            reproduction_before.to_receipt()
        ),
        "matched_controller_fork": fork_spec,
        "live_test": live_spec,
        "success_criterion": dict(spec["success_criterion"]),
        "claim_boundary": list(spec["claim_boundary"]),
    }
    experiment_sha = _sha(manifest_core)
    manifest = {
        **manifest_core,
        "experiment_sha256": experiment_sha,
    }
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing != manifest:
            raise RuntimeError("existing H97 manifest drifted")
    else:
        _atomic_json(manifest_path, manifest)
    return {
        "status": "preflight_complete",
        "manifest_ref": _relative_ref(manifest_path),
        "experiment_sha256": experiment_sha,
        "source_program": program.to_receipt(),
        "response_derivative": derivative.to_receipt(),
        "live_response_derivative": live_derivative.to_receipt(),
        "live_controller_scope_transport": scope_transport,
        "live_intervention_summary": {
            "causal_rendered_sha256": interventions[
                "causal_rendered_sha256"
            ],
            "placebo_rendered_sha256": interventions[
                "placebo_rendered_sha256"
            ],
            "causal_intervention_revision_sha256": interventions[
                "causal_intervention_revision_sha256"
            ],
            "rendered_utf8_bytes_per_condition": interventions[
                "rendered_utf8_bytes_per_condition"
            ],
        },
        "negative_statuses": [
            {
                "status": row.status,
                "reason": row.reason,
                "sha256": row.sha256,
            }
            for row in negative_derivatives
        ],
        "construction_replay": {
            key: {
                "relation": value.relation,
                "supported_transport": value.supported_transport,
                "sha256": value.sha256,
            }
            for key, value in replay_rows.items()
        },
        "reproduction_before_h97": (
            reproduction_before.to_receipt()
        ),
    }


def main() -> int:
    base = (
        REPO
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        default=str(base / "h97_causal_response_derivative_spec.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(base / "h97_causal_response_derivative"),
    )
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not args.preflight_only:
        raise SystemExit(
            "H97 live fork is unavailable until preflight is verified"
        )
    result = run_preflight(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
