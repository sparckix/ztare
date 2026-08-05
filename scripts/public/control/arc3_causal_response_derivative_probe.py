#!/usr/bin/env python3
"""Compile and test H97's response derivative on an exact Responses fork."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence


REPO = Path(__file__).resolve().parents[3]
CONTROL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(CONTROL))

from arc3_paired_recall_probe import (  # noqa: E402
    _append_jsonl,
    _atomic_json,
    _file_sha256,
    _outcome_metrics,
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
    responses_tool_decision_from_receipt,
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


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _exchange_observer(
    path: Path,
    *,
    pair_index: int,
    role: str,
) -> Callable[[Mapping[str, Any]], None]:
    def observe(row: Mapping[str, Any]) -> None:
        _append_jsonl(path, {
            "schema": LIVE_SCHEMA,
            "kind": "responses_exchange",
            "pair_index": int(pair_index),
            "role": str(role),
            **dict(row),
        })

    return observe


def _catalog_input(
    grid: Sequence[Sequence[int]],
    *,
    action_count: int,
    levels_completed: int,
    action_arity: int,
    presentation: GridObjectCatalogPresentation,
    phase: str,
) -> list[dict[str, Any]]:
    content = observation_content(
        grid,
        action_count=action_count,
        levels_completed=levels_completed,
        available_action_indices=tuple(range(action_arity)),
    )
    content.append({
        "type": "input_text",
        "text": json.dumps({
            "phase": str(phase),
            "catalog_scoped_object_presentation": (
                presentation.prompt_receipt()
            ),
            "binding_rule": (
                "Use only current short handles. controlled_object_handle "
                "names the expected controlled object; "
                "ordered_waypoint_handles are distinct and ordered."
            ),
        }, sort_keys=True, separators=(",", ":")),
    })
    return content


def _initial_parent_input(
    grid: Sequence[Sequence[int]],
    *,
    levels_completed: int,
    action_arity: int,
    presentation: GridObjectCatalogPresentation,
    prefix_action_count: int,
) -> list[dict[str, Any]]:
    return [{
        "role": "user",
        "content": _catalog_input(
            grid,
            action_count=prefix_action_count,
            levels_completed=levels_completed,
            action_arity=action_arity,
            presentation=presentation,
            phase="blind_matched_parent_proposal",
        ),
    }]


def _branch_revision_input(
    parent_call_id: str,
    intervention_text: str,
    *,
    assignment: str,
) -> list[dict[str, Any]]:
    return [
        {
            "type": "function_call_output",
            "call_id": str(parent_call_id),
            "output": json.dumps({
                "status": "proposal_checkpoint_only",
                "environment_action_executed": False,
                "assignment_blinded": True,
            }, sort_keys=True, separators=(",", ":")),
        },
        {
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": str(intervention_text),
            }],
        },
    ]


def _settled_tool_output(
    call_id: str,
    grid: Sequence[Sequence[int]],
    *,
    action_count: int,
    levels_completed: int,
    action_arity: int,
    presentation: GridObjectCatalogPresentation,
) -> list[dict[str, Any]]:
    return [{
        "type": "function_call_output",
        "call_id": str(call_id),
        "output": _catalog_input(
            grid,
            action_count=action_count,
            levels_completed=levels_completed,
            action_arity=action_arity,
            presentation=presentation,
            phase="settled_environment_successor",
        ),
    }]


def _validate_decision(
    decision,
    *,
    observation_sha256: str,
    catalog: GridObjectCatalog,
    presentation: GridObjectCatalogPresentation,
    action_arity: int,
    phase: str,
) -> dict[str, Any]:
    arguments = dict(decision.arguments)
    action = arguments.get("action")
    if (
        isinstance(action, bool)
        or not isinstance(action, int)
        or not 0 <= action < int(action_arity)
    ):
        raise ValueError(
            f"model action must be an integer in [0, {action_arity - 1}]"
        )
    controlled_handle = str(
        arguments.get("controlled_object_handle") or ""
    )
    presentation.resolve_handle(controlled_handle)
    waypoint_handles = tuple(
        str(value)
        for value in arguments.get("ordered_waypoint_handles") or ()
    )
    if len(waypoint_handles) != len(set(waypoint_handles)):
        raise ValueError("model repeated a waypoint handle")
    for handle in waypoint_handles:
        presentation.resolve_handle(handle)
    return {
        "schema": LIVE_SCHEMA,
        "kind": "catalog_scoped_model_decision",
        "phase": str(phase),
        "action": int(action),
        "prediction": str(arguments.get("prediction") or ""),
        "plan_summary": str(arguments.get("plan_summary") or ""),
        "uncertainty": str(arguments.get("uncertainty") or ""),
        "controlled_object_handle": controlled_handle,
        "ordered_waypoint_handles": list(waypoint_handles),
        "observation_sha256": str(observation_sha256),
        "catalog_sha256": catalog.sha256,
        "presentation_sha256": presentation.sha256,
        "response_decision": decision.to_receipt(),
    }


def _object_proposal(
    row: Mapping[str, Any],
    *,
    scope: MemoryScope,
    controller_instance_sha256: str,
    catalog: GridObjectCatalog,
    presentation: GridObjectCatalogPresentation,
    parent_proposal_sha256: str = "",
    consumed_intervention_revision_sha256: str = "",
) -> ObjectLinkedControllerProposal:
    return proposal_probe._object_linked_proposal(
        row,
        scope=scope,
        controller_instance_sha256=controller_instance_sha256,
        catalog=catalog,
        presentation=presentation,
        parent_proposal_sha256=parent_proposal_sha256,
        consumed_intervention_revision_sha256=(
            consumed_intervention_revision_sha256
        ),
    )


def _controller_instance_sha256(
    *,
    experiment_sha256: str,
    pair_index: int,
    parent_response_id: str,
    scope_sha256: str,
) -> str:
    return _sha({
        "kind": "exact_responses_parent_fork_controller_instance",
        "experiment_sha256": str(experiment_sha256),
        "pair_index": int(pair_index),
        "parent_response_id": str(parent_response_id),
        "scope_sha256": str(scope_sha256),
    })


def _compile_live_context(
    args: argparse.Namespace,
) -> dict[str, Any]:
    preflight = run_preflight(args)
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    manifest_path = Path(args.output_dir).resolve() / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["experiment_sha256"] != preflight["experiment_sha256"]:
        raise RuntimeError("H97 live manifest diverged from preflight")
    h96_manifest_path = (
        base / str(spec["derivative_source"]["h96_manifest_ref"])
    ).resolve()
    h96_manifest = _load_checked(
        h96_manifest_path,
        str(
            spec["derivative_source"]["h96_manifest_file_sha256"]
        ),
    )
    family, _response, source_contract, program = _source_program(
        spec=spec,
        base=base,
        h96_manifest=h96_manifest,
    )
    lineage = causal_object_lineage_transport_from_receipt(
        h96_manifest["lineage_transport"]
    )
    binding = response_derivative_event_family_binding_receipt(
        program,
        lineage,
    )
    scope = MemoryScope(
        **manifest["live_controller_scope_transport"]["target_scope"]
    )
    interventions = dict(manifest["live_interventions"])
    live_derivative = compile_causal_response_derivative(
        program,
        lineage,
        target_scope=scope,
        target_intervention_revision_sha256=str(
            interventions["causal_intervention_revision_sha256"]
        ),
        source_forbidden_controlled_object_refs=(
            source_contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt=binding,
        event_selection_phase="pre_outcome",
        evidence_refs=(
            "construction_derivative:"
            f"{manifest['response_derivative']['sha256']}",
            "controller_scope_transport:"
            f"{manifest['live_controller_scope_transport']['sha256']}",
        ),
    )
    if (
        live_derivative.to_receipt()
        != manifest["live_response_derivative"]
    ):
        raise RuntimeError("H97 live derivative reconstruction drifted")
    prefix = dict(h96_manifest["descendant_prefix"])
    observation = dict(prefix["final_observation"])
    grid = decode_grid_rle_rows(
        tuple(str(row) for row in observation["grid_rle_rows"])
    )
    catalog = compile_catalog_from_observation(observation)
    presentation = compile_catalog_presentation(catalog)
    if (
        catalog.to_receipt() != h96_manifest["target_catalog"]
        or presentation.to_receipt()
        != h96_manifest["target_presentation"]
    ):
        raise RuntimeError("H97 target catalog reconstruction drifted")
    authority = ObjectReferenceAuthority(
        observation_sha256=observation["sha256"],
        catalog_sha256=catalog.sha256,
        object_refs=catalog.object_refs,
    )
    return {
        "preflight": preflight,
        "spec": spec,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "h96_manifest": h96_manifest,
        "family": family,
        "program": program,
        "live_derivative": live_derivative,
        "live_residual": live_derivative.residual_contract,
        "scope": scope,
        "interventions": interventions,
        "prefix": prefix,
        "observation": observation,
        "grid": grid,
        "catalog": catalog,
        "presentation": presentation,
        "authority": authority,
    }


def _new_thread(
    client: Any,
    context: Mapping[str, Any],
    args: argparse.Namespace,
    *,
    observer: Callable[[Mapping[str, Any]], None] | None = None,
) -> PersistentResponsesToolThread:
    manifest = context["manifest"]
    fork = manifest["matched_controller_fork"]
    return PersistentResponsesToolThread(
        client,
        model_id=str(fork["model"]),
        instructions=str(manifest["live_controller_instructions"]),
        tool=dict(manifest["live_controller_tool"]),
        reasoning_effort=str(fork["reasoning_effort"]),
        reasoning_context=str(fork["reasoning_context"]),
        max_output_tokens=int(args.max_output_tokens),
        timeout_seconds=float(args.timeout_seconds),
        exchange_observer=observer,
    )


def _restore_prefix(
    context: Mapping[str, Any],
) -> tuple[ArcAgi3Adapter, tuple[tuple[int, ...], ...]]:
    prefix = context["prefix"]
    game = str(context["spec"]["live_test"]["game"])
    adapter = ArcAgi3Adapter(game)
    grid = adapter.reset()
    if int(adapter.action_arity) != int(prefix["action_arity"]):
        raise RuntimeError("H97 live action arity drifted")
    for action in prefix["actions"]:
        grid = adapter.step(int(action))
    receipt = settled_observation_receipt(
        grid,
        observation_index=len(prefix["actions"]),
        action_count=len(prefix["actions"]),
        levels_completed=int(adapter.levels_completed),
        adapter_epoch=int(adapter.current_epoch),
        available_action_indices=tuple(range(adapter.action_arity)),
    )
    if receipt != context["observation"]:
        raise RuntimeError("H97 live prefix failed exact restoration")
    catalog = compile_catalog_from_observation(receipt)
    presentation = compile_catalog_presentation(catalog)
    if (
        catalog.sha256 != context["catalog"].sha256
        or presentation.sha256 != context["presentation"].sha256
    ):
        raise RuntimeError("H97 live prefix crossed catalog authority")
    return adapter, grid


def _existing_eligible_parent(
    path: Path,
) -> dict[str, Any] | None:
    rows = _jsonl_rows(path)
    eligible = [row for row in rows if row.get("eligible") is True]
    if len(eligible) > 1:
        raise RuntimeError("H97 pair admitted multiple blind parents")
    return eligible[0] if eligible else None


def _obtain_eligible_parent(
    *,
    client: Any,
    context: Mapping[str, Any],
    args: argparse.Namespace,
    pair_index: int,
) -> tuple[
    PersistentResponsesToolThread,
    Any,
    ObjectLinkedControllerProposal,
    dict[str, Any],
] | None:
    output_dir = Path(args.output_dir).resolve()
    attempts_path = (
        output_dir / "parent_attempts" / f"pair_{pair_index:02d}.jsonl"
    )
    existing = _existing_eligible_parent(attempts_path)
    if existing is not None:
        decision = responses_tool_decision_from_receipt(
            existing["response_decision"]
        )
        proposal = object_proposal_from_receipt(
            existing["pre_proposal"]
        )
        thread = _new_thread(client, context, args)
        thread.previous_response_id = decision.response_id
        return thread, decision, proposal, existing

    rows = _jsonl_rows(attempts_path)
    maximum = int(
        context["manifest"]["matched_controller_fork"][
            "maximum_blind_parent_attempts_per_pair"
        ]
    )
    for attempt_index in range(len(rows) + 1, maximum + 1):
        exchanges_path = (
            output_dir
            / "exchanges"
            / f"pair_{pair_index:02d}_parent_{attempt_index:02d}.jsonl"
        )
        thread = _new_thread(
            client,
            context,
            args,
            observer=_exchange_observer(
                exchanges_path,
                pair_index=pair_index,
                role=f"blind_parent_attempt_{attempt_index:02d}",
            ),
        )
        decision = thread.decide(_initial_parent_input(
            context["grid"],
            levels_completed=int(
                context["observation"]["levels_completed"]
            ),
            action_arity=int(context["prefix"]["action_arity"]),
            presentation=context["presentation"],
            prefix_action_count=len(context["prefix"]["actions"]),
        ))
        controller_instance = _controller_instance_sha256(
            experiment_sha256=context["manifest"]["experiment_sha256"],
            pair_index=pair_index,
            parent_response_id=decision.response_id,
            scope_sha256=context["scope"].sha256,
        )
        refusal = ""
        try:
            decision_row = _validate_decision(
                decision,
                observation_sha256=context["observation"]["sha256"],
                catalog=context["catalog"],
                presentation=context["presentation"],
                action_arity=int(context["prefix"]["action_arity"]),
                phase="blind_matched_parent_proposal",
            )
            proposal = _object_proposal(
                decision_row,
                scope=context["scope"],
                controller_instance_sha256=controller_instance,
                catalog=context["catalog"],
                presentation=context["presentation"],
            )
            eligible = not proposal_satisfies_residual_response(
                proposal,
                context["live_residual"],
            )
        except ValueError as exc:
            decision_row = {}
            proposal = None
            eligible = False
            refusal = f"invalid_catalog_scoped_proposal:{exc}"
        row = {
            "schema": LIVE_SCHEMA,
            "kind": "blind_parent_attempt",
            "experiment_sha256": context["manifest"]["experiment_sha256"],
            "pair_index": int(pair_index),
            "attempt_index": int(attempt_index),
            "response_decision": decision.to_receipt(),
            "catalog_scoped_decision": decision_row,
            "controller_instance_sha256": controller_instance,
            "pre_proposal": (
                proposal.to_receipt() if proposal is not None else None
            ),
            "eligible": bool(eligible),
            "eligibility_rule": (
                "blind_proposal_does_not_satisfy_target_residual_program"
            ),
            "refusal": refusal,
            "environment_contact": False,
        }
        _append_jsonl(attempts_path, row)
        if eligible and proposal is not None:
            return thread, decision, proposal, row
    return None


def _residual_admission_receipt(
    *,
    context: Mapping[str, Any],
    pair_index: int,
    pre_proposal: ObjectLinkedControllerProposal,
) -> dict[str, Any]:
    core = {
        "schema": LIVE_SCHEMA,
        "kind": "pre_revision_derivative_admission",
        "experiment_sha256": context["manifest"]["experiment_sha256"],
        "pair_index": int(pair_index),
        "action": "explore_derivative",
        "pre_proposal_sha256": pre_proposal.sha256,
        "pre_basin_rule": "residual_plan_basin_sha256",
        "source_program_sha256": context["program"].sha256,
        "derivative_sha256": context["live_derivative"].sha256,
        "residual_contract_sha256": context["live_residual"].sha256,
        "eligible": True,
        "reason": "blind_parent_did_not_satisfy_frozen_residual",
        "environment_contact_before_admission": False,
    }
    return {**core, "sha256": _sha(core)}


def _prepare_pair(
    *,
    client: Any,
    context: Mapping[str, Any],
    args: argparse.Namespace,
    pair_index: int,
    order: Sequence[str],
) -> dict[str, Any] | None:
    output_dir = Path(args.output_dir).resolve()
    setup_path = output_dir / "pairs" / f"pair_{pair_index:02d}.json"
    if setup_path.exists():
        setup = json.loads(setup_path.read_text(encoding="utf-8"))
        parent = responses_tool_decision_from_receipt(
            setup["parent_response_decision"]
        )
        pre = object_proposal_from_receipt(setup["pre_proposal"])
        branches = {}
        for assignment in ("offer", "withhold"):
            row = setup["branches"][assignment]
            post = object_proposal_from_receipt(row["post_proposal"])
            transition = compile_residual_proposal_transition(
                trial_ref=f"h97:pair-{pair_index:02d}:{assignment}",
                stratum_sha256=str(setup["stratum_sha256"]),
                assignment=assignment,
                pre_proposal=pre,
                post_proposal=post,
                derivative=context["live_derivative"],
                authority=context["authority"],
            )
            if transition.to_receipt() != row["transition"]:
                raise RuntimeError("H97 saved branch transition drifted")
            branches[assignment] = {
                "decision": responses_tool_decision_from_receipt(
                    row["response_decision"]
                ),
                "proposal": post,
                "transition": transition,
                "receipt": row,
            }
        authority = compile_responses_fork_authority(
            parent,
            tuple(branches[value]["decision"] for value in order),
        )
        if authority.to_receipt() != setup["fork_authority"]:
            raise RuntimeError("H97 saved fork authority drifted")
        return {
            "setup": setup,
            "parent": parent,
            "pre_proposal": pre,
            "branches": branches,
        }

    parent_bundle = _obtain_eligible_parent(
        client=client,
        context=context,
        args=args,
        pair_index=pair_index,
    )
    if parent_bundle is None:
        return None
    parent_thread, parent, pre_proposal, parent_row = parent_bundle
    admission = _residual_admission_receipt(
        context=context,
        pair_index=pair_index,
        pre_proposal=pre_proposal,
    )
    admission_path = (
        output_dir / "admissions" / f"pair_{pair_index:02d}.json"
    )
    if admission_path.exists():
        existing = json.loads(admission_path.read_text(encoding="utf-8"))
        if existing != admission:
            raise RuntimeError("H97 admission checkpoint drifted")
    else:
        _atomic_json(admission_path, admission)

    stratum_sha256 = _sha({
        "kind": "matched_residual_proposal_basin",
        "experiment_sha256": context["manifest"]["experiment_sha256"],
        "pair_index": int(pair_index),
        "pre_proposal_sha256": pre_proposal.sha256,
        "residual_contract_sha256": context["live_residual"].sha256,
    })
    branches = {}
    for assignment in order:
        branch_path = (
            output_dir
            / "branch_revisions"
            / f"pair_{pair_index:02d}_{assignment}.json"
        )
        if branch_path.exists():
            row = json.loads(branch_path.read_text(encoding="utf-8"))
            decision = responses_tool_decision_from_receipt(
                row["response_decision"]
            )
            post = object_proposal_from_receipt(row["post_proposal"])
        else:
            thread = parent_thread.fork_from_current()
            thread.set_exchange_observer(_exchange_observer(
                output_dir
                / "exchanges"
                / f"pair_{pair_index:02d}_{assignment}_revision.jsonl",
                pair_index=pair_index,
                role=f"{assignment}_branch_revision",
            ))
            intervention_text = str(
                context["interventions"][
                    "causal_text"
                    if assignment == "offer"
                    else "placebo_text"
                ]
            )
            decision = thread.decide(_branch_revision_input(
                parent.call_id,
                intervention_text,
                assignment=assignment,
            ))
            decision_row = _validate_decision(
                decision,
                observation_sha256=context["observation"]["sha256"],
                catalog=context["catalog"],
                presentation=context["presentation"],
                action_arity=int(context["prefix"]["action_arity"]),
                phase=f"{assignment}_branch_revision",
            )
            post = _object_proposal(
                decision_row,
                scope=context["scope"],
                controller_instance_sha256=(
                    pre_proposal.controller_instance_sha256
                ),
                catalog=context["catalog"],
                presentation=context["presentation"],
                parent_proposal_sha256=pre_proposal.sha256,
                consumed_intervention_revision_sha256=(
                    context["live_residual"].intervention_revision_sha256
                ) if assignment == "offer" else "",
            )
            transition = compile_residual_proposal_transition(
                trial_ref=f"h97:pair-{pair_index:02d}:{assignment}",
                stratum_sha256=stratum_sha256,
                assignment=assignment,
                pre_proposal=pre_proposal,
                post_proposal=post,
                derivative=context["live_derivative"],
                authority=context["authority"],
            )
            row = {
                "schema": LIVE_SCHEMA,
                "kind": "matched_branch_revision",
                "experiment_sha256": (
                    context["manifest"]["experiment_sha256"]
                ),
                "pair_index": int(pair_index),
                "assignment": assignment,
                "parent_response_id": parent.response_id,
                "response_decision": decision.to_receipt(),
                "catalog_scoped_decision": decision_row,
                "post_proposal": post.to_receipt(),
                "transition": transition.to_receipt(),
                "presented_intervention_sha256": (
                    context["interventions"][
                        "causal_rendered_sha256"
                        if assignment == "offer"
                        else "placebo_rendered_sha256"
                    ]
                ),
                "presented_utf8_bytes": len(
                    intervention_text.encode("utf-8")
                ),
                "environment_contact": False,
            }
            _atomic_json(branch_path, row)
        transition = compile_residual_proposal_transition(
            trial_ref=f"h97:pair-{pair_index:02d}:{assignment}",
            stratum_sha256=stratum_sha256,
            assignment=assignment,
            pre_proposal=pre_proposal,
            post_proposal=post,
            derivative=context["live_derivative"],
            authority=context["authority"],
        )
        if transition.to_receipt() != row["transition"]:
            raise RuntimeError("H97 branch revision receipt drifted")
        branches[assignment] = {
            "decision": decision,
            "proposal": post,
            "transition": transition,
            "receipt": row,
        }
    fork_authority = compile_responses_fork_authority(
        parent,
        tuple(branches[value]["decision"] for value in order),
    )
    setup = {
        "schema": LIVE_SCHEMA,
        "kind": "matched_parent_fork",
        "experiment_sha256": context["manifest"]["experiment_sha256"],
        "pair_index": int(pair_index),
        "arm_order": list(order),
        "parent_attempt": parent_row,
        "parent_response_decision": parent.to_receipt(),
        "pre_proposal": pre_proposal.to_receipt(),
        "admission": admission,
        "stratum_sha256": stratum_sha256,
        "fork_authority": fork_authority.to_receipt(),
        "branches": {
            key: value["receipt"] for key, value in branches.items()
        },
        "environment_contact": False,
    }
    _atomic_json(setup_path, setup)
    return {
        "setup": setup,
        "parent": parent,
        "pre_proposal": pre_proposal,
        "branches": branches,
    }


def _run_arm(
    *,
    client: Any,
    context: Mapping[str, Any],
    args: argparse.Namespace,
    pair_index: int,
    assignment: str,
    branch: Mapping[str, Any],
) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    arm_path = (
        output_dir
        / "arms"
        / f"pair_{pair_index:02d}_{assignment}.json"
    )
    if arm_path.exists():
        return json.loads(arm_path.read_text(encoding="utf-8"))

    adapter, grid = _restore_prefix(context)
    prefix_count = len(context["prefix"]["actions"])
    budget = int(context["manifest"]["live_test"][
        "post_prefix_actions_per_arm"
    ])
    action_arity = int(context["prefix"]["action_arity"])
    start_levels = int(adapter.levels_completed)
    turns_path = (
        output_dir
        / "turns"
        / f"pair_{pair_index:02d}_{assignment}.jsonl"
    )
    turns = _jsonl_rows(turns_path)
    if len(turns) > budget:
        raise RuntimeError("H97 arm recorded more turns than its budget")
    observations = [dict(context["observation"])]
    for relative_count, turn in enumerate(turns, start=1):
        if int(turn["action_count"]) != relative_count:
            raise RuntimeError("H97 resumed turn order drifted")
        if (
            str(turn["source_observation_sha256"])
            != str(observations[-1]["sha256"])
        ):
            raise RuntimeError("H97 resumed source observation drifted")
        grid = adapter.step(int(turn["action"]))
        successor = settled_observation_receipt(
            grid,
            observation_index=prefix_count + relative_count,
            action_count=prefix_count + relative_count,
            levels_completed=int(adapter.levels_completed),
            adapter_epoch=int(adapter.current_epoch),
            available_action_indices=tuple(range(action_arity)),
        )
        if (
            successor["sha256"]
            != str(turn["successor_observation_sha256"])
        ):
            raise RuntimeError("H97 resumed successor observation drifted")
        observations.append(successor)

    thread = _new_thread(
        client,
        context,
        args,
        observer=_exchange_observer(
            output_dir
            / "exchanges"
            / f"pair_{pair_index:02d}_{assignment}_rollout.jsonl",
            pair_index=pair_index,
            role=f"{assignment}_environment_rollout",
        ),
    )
    child_decision = branch["decision"]
    if turns:
        prior_decision = responses_tool_decision_from_receipt(
            turns[-1]["response_decision"]
        )
        thread.previous_response_id = prior_decision.response_id
    else:
        prior_decision = child_decision
        thread.previous_response_id = child_decision.response_id

    for relative_count in range(len(turns) + 1, budget + 1):
        source_observation = observations[-1]
        source_catalog = compile_catalog_from_observation(
            source_observation
        )
        source_presentation = compile_catalog_presentation(
            source_catalog
        )
        if relative_count == 1:
            decision = child_decision
        else:
            decision = thread.decide(_settled_tool_output(
                prior_decision.call_id,
                grid,
                action_count=prefix_count + relative_count - 1,
                levels_completed=int(adapter.levels_completed),
                action_arity=action_arity,
                presentation=source_presentation,
            ))
        decision_row = _validate_decision(
            decision,
            observation_sha256=source_observation["sha256"],
            catalog=source_catalog,
            presentation=source_presentation,
            action_arity=action_arity,
            phase=f"{assignment}_charged_action_{relative_count:02d}",
        )
        action = int(decision_row["action"])
        grid = adapter.step(action)
        successor_observation = settled_observation_receipt(
            grid,
            observation_index=prefix_count + relative_count,
            action_count=prefix_count + relative_count,
            levels_completed=int(adapter.levels_completed),
            adapter_epoch=int(adapter.current_epoch),
            available_action_indices=tuple(range(action_arity)),
        )
        turn = {
            "schema": LIVE_SCHEMA,
            "kind": "charged_environment_turn",
            "experiment_sha256": context["manifest"]["experiment_sha256"],
            "pair_index": int(pair_index),
            "assignment": assignment,
            "action_count": int(relative_count),
            "global_action_count": prefix_count + relative_count,
            "action": action,
            "prediction": decision_row["prediction"],
            "plan_summary": decision_row["plan_summary"],
            "uncertainty": decision_row["uncertainty"],
            "catalog_scoped_decision": decision_row,
            "response_decision": decision.to_receipt(),
            "levels_completed": int(adapter.levels_completed),
            "adapter_epoch": int(adapter.current_epoch),
            "source_observation_sha256": source_observation["sha256"],
            "successor_observation_sha256": (
                successor_observation["sha256"]
            ),
            "transition_identity": _transition_identity_receipt(adapter),
        }
        _append_jsonl(turns_path, turn)
        turns.append(turn)
        observations.append(successor_observation)
        prior_decision = decision

    level_boundary_actions = []
    previous_levels = start_levels
    for turn in turns:
        observed = int(turn["levels_completed"])
        if observed > previous_levels:
            level_boundary_actions.append({
                "action_count": int(turn["action_count"]),
                "levels_before": previous_levels,
                "levels_after": observed,
                "transition_identity": turn["transition_identity"],
            })
        previous_levels = observed
    probe = {
        "schema": LIVE_SCHEMA,
        "kind": "matched_branch_environment_probe",
        "status": (
            "level_gained"
            if int(adapter.levels_completed) > start_levels
            else "budget_exhausted"
        ),
        "game": str(context["manifest"]["live_test"]["game"]),
        "assignment": assignment,
        "budget": budget,
        "actions_executed": len(turns),
        "prefix_action_count": prefix_count,
        "start_levels_completed": start_levels,
        "end_levels_completed": int(adapter.levels_completed),
        "levels_gained": int(adapter.levels_completed) - start_levels,
        "first_level_action": (
            level_boundary_actions[0]["action_count"]
            if level_boundary_actions
            else None
        ),
        "level_boundary_actions": level_boundary_actions,
        "input_tokens": sum(
            int(row["response_decision"]["input_tokens"])
            for row in turns
        ),
        "output_tokens": sum(
            int(row["response_decision"]["output_tokens"])
            for row in turns
        ),
        "cached_input_tokens": sum(
            int(row["response_decision"]["cached_input_tokens"])
            for row in turns
        ),
        "observations": observations,
        "turns": turns,
    }
    metrics = _outcome_metrics(probe)
    payload = {
        "schema": LIVE_SCHEMA,
        "kind": "matched_branch_arm",
        "status": "live_complete",
        "experiment_sha256": context["manifest"]["experiment_sha256"],
        "pair_index": int(pair_index),
        "assignment": assignment,
        "parent_response_id": (
            branch["decision"].previous_response_id
        ),
        "branch_response_id": branch["decision"].response_id,
        "transition": branch["transition"].to_receipt(),
        "probe": probe,
        "metrics": metrics,
    }
    _atomic_json(arm_path, payload)
    return payload


def _instrumented_outcome(
    arm: Mapping[str, Any],
    *,
    transition,
    arm_path: Path,
) -> InstrumentedProposalOutcome:
    return InstrumentedProposalOutcome(
        transition=transition,
        external_outcome_ref=(
            f"{_relative_ref(arm_path)}#sha256={_file_sha256(arm_path)}"
        ),
        external_value=proposal_probe._external_value(arm["metrics"]),
        offer_cost=0.0,
        primitive_action_cost=float(arm["probe"]["budget"]),
    )


def _seal_parent_admission_failure(
    context: Mapping[str, Any],
    args: argparse.Namespace,
    *,
    failed_pair_index: int,
) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    result_core = {
        "schema": LIVE_SCHEMA,
        "kind": "experiment_result",
        "status": "live_complete",
        "verdict": "rejected",
        "experiment_sha256": context["manifest"]["experiment_sha256"],
        "manifest_ref": _relative_ref(context["manifest_path"]),
        "failed_checks": [
            "eligible_matched_parent_not_found_within_frozen_attempt_budget"
        ],
        "failed_pair_index": int(failed_pair_index),
        "environment_contact": False,
        "response_reproduction_before": (
            context["manifest"]["reproduction_before_h97"]
        ),
        "response_reproduction_after": (
            context["manifest"]["reproduction_before_h97"]
        ),
        "claim_boundary": list(context["manifest"]["claim_boundary"]),
    }
    result = {**result_core, "sha256": _sha(result_core)}
    _atomic_json(output_dir / "result.json", result)
    return result


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    context = _compile_live_context(args)
    output_dir = Path(args.output_dir).resolve()
    result_path = output_dir / "result.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    bootstrap_dotenv_from_repo_root()
    from openai import OpenAI

    client = OpenAI()
    orders = tuple(
        tuple(str(value) for value in row)
        for row in context["manifest"]["matched_controller_fork"][
            "arm_order"
        ]
    )
    expected_pairs = int(
        context["manifest"]["matched_controller_fork"]["pair_count"]
    )
    if len(orders) != expected_pairs:
        raise RuntimeError("H97 arm-order schedule drifted")

    pair_setups = []
    for pair_index, order in enumerate(orders, start=1):
        pair = _prepare_pair(
            client=client,
            context=context,
            args=args,
            pair_index=pair_index,
            order=order,
        )
        if pair is None:
            return _seal_parent_admission_failure(
                context,
                args,
                failed_pair_index=pair_index,
            )
        pair_setups.append(pair)

    all_outcomes: list[InstrumentedProposalOutcome] = []
    pair_rows = []
    for pair_index, (order, pair) in enumerate(
        zip(orders, pair_setups),
        start=1,
    ):
        arms = {}
        outcomes = {}
        for assignment in order:
            branch = pair["branches"][assignment]
            arm = _run_arm(
                client=client,
                context=context,
                args=args,
                pair_index=pair_index,
                assignment=assignment,
                branch=branch,
            )
            arms[assignment] = arm
            arm_path = (
                output_dir
                / "arms"
                / f"pair_{pair_index:02d}_{assignment}.json"
            )
            outcome = _instrumented_outcome(
                arm,
                transition=branch["transition"],
                arm_path=arm_path,
            )
            outcomes[assignment] = outcome
            all_outcomes.append(outcome)
        offer_value = outcomes["offer"].net_external_value
        withhold_value = outcomes["withhold"].net_external_value
        pair_row = {
            "schema": LIVE_SCHEMA,
            "kind": "matched_pair_settlement",
            "experiment_sha256": context["manifest"]["experiment_sha256"],
            "pair_index": int(pair_index),
            "arm_order": list(order),
            "shared_parent_response_id": pair["parent"].response_id,
            "fork_authority": pair["setup"]["fork_authority"],
            "pre_proposal": pair["pre_proposal"].to_receipt(),
            "offer_transition": (
                pair["branches"]["offer"]["transition"].to_receipt()
            ),
            "withhold_transition": (
                pair["branches"]["withhold"]["transition"].to_receipt()
            ),
            "offer_outcome": outcomes["offer"].to_receipt(),
            "withhold_outcome": outcomes["withhold"].to_receipt(),
            "offer_metrics": arms["offer"]["metrics"],
            "withhold_metrics": arms["withhold"]["metrics"],
            "offer_task_minus_withhold": (
                float(arms["offer"]["metrics"]["task_score"])
                - float(arms["withhold"]["metrics"]["task_score"])
            ),
            "offer_composite_minus_withhold": (
                offer_value - withhold_value
            ),
        }
        pair_rows.append(pair_row)
        _atomic_json(
            output_dir
            / "settlements"
            / f"pair_{pair_index:02d}.json",
            pair_row,
        )

    estimate = estimate_instrumented_plasticity(
        all_outcomes,
        minimum_first_stage=1.0,
    )
    settlement_set_sha256 = _sha({
        "outcome_sha256s": sorted(
            outcome.sha256 for outcome in all_outcomes
        ),
    })
    child_family = compile_residual_response_family(
        all_outcomes,
        derivative=context["live_derivative"],
        source_settlement_ref=(
            f"{_relative_ref(output_dir)}/settlements"
        ),
        source_settlement_sha256=settlement_set_sha256,
        minimum_offer_count=2,
        minimum_withhold_count=2,
        minimum_first_stage_transport_delta=1.0,
        minimum_intent_to_treat_net_delta=0.0,
    )
    task_delta = sum(
        float(row["offer_task_minus_withhold"]) for row in pair_rows
    )
    composite_deltas = tuple(
        float(row["offer_composite_minus_withhold"])
        for row in pair_rows
    )
    mean_composite_delta = (
        sum(composite_deltas) / len(composite_deltas)
    )
    composite_wins = sum(value > 0.0 for value in composite_deltas)
    shared_parent_rate = sum(
        bool(row["fork_authority"]["shared_parent"])
        for row in pair_rows
    ) / len(pair_rows)
    criterion_spec = context["manifest"]["success_criterion"]
    checks = {
        "eligible_matched_pair_count": (
            len(pair_rows)
            == int(criterion_spec["eligible_matched_pair_count"])
        ),
        "shared_parent_identity_rate": (
            shared_parent_rate
            == float(criterion_spec["shared_parent_identity_rate"])
        ),
        "offer_supported_derivative_rate": (
            estimate.offer_supported_transport_rate
            == float(
                criterion_spec["offer_supported_derivative_rate"]
            )
        ),
        "withhold_spontaneous_derivative_rate": (
            estimate.withhold_supported_transport_rate
            == float(
                criterion_spec[
                    "withhold_spontaneous_derivative_rate"
                ]
            )
        ),
        "first_stage_derivative_delta": (
            estimate.first_stage_transport_delta
            == float(criterion_spec["first_stage_derivative_delta"])
        ),
        "minimum_task_delta": (
            task_delta >= float(criterion_spec["minimum_task_delta"])
        ),
        "minimum_mean_composite_delta_exclusive": (
            mean_composite_delta
            > float(
                criterion_spec[
                    "minimum_mean_composite_delta_exclusive"
                ]
            )
        ),
        "minimum_offer_composite_wins": (
            composite_wins
            >= int(criterion_spec["minimum_offer_composite_wins"])
        ),
        "promoted_child_count": (
            child_family.admissible_response_count
            == int(criterion_spec["promoted_child_count"])
        ),
    }
    supported = all(checks.values())
    promoted_children = (
        (child_family.sha256,) if child_family.promoted else ()
    )
    total_primitive_cost = float(
        len(context["prefix"]["actions"]) + int(
            context["manifest"]["live_test"][
                "post_prefix_actions_per_arm"
            ]
        )
    ) * len(all_outcomes)
    reproduction_after = compile_response_reproduction_estimate(
        response_schema_sha256=context["program"].sha256,
        parent_family_sha256s=(context["family"].sha256,),
        promoted_child_family_sha256s=promoted_children,
        false_edge_count=sum(
            row.transition.assignment == "withhold"
            and row.transition.supported_transport
            for row in all_outcomes
        ),
        primitive_action_cost=total_primitive_cost,
        evidence_refs=(
            f"{_relative_ref(output_dir)}/settlements"
            f"#sha256={settlement_set_sha256}",
        ),
    )
    result_core = {
        "schema": LIVE_SCHEMA,
        "kind": "experiment_result",
        "status": "live_complete",
        "verdict": "supported" if supported else "rejected",
        "experiment_sha256": context["manifest"]["experiment_sha256"],
        "manifest_ref": _relative_ref(context["manifest_path"]),
        "pairs": pair_rows,
        "target_residual_estimate": estimate.to_receipt(),
        "promoted_child_response_family": child_family.to_receipt(),
        "response_reproduction_before": (
            context["manifest"]["reproduction_before_h97"]
        ),
        "response_reproduction_after": reproduction_after.to_receipt(),
        "checks": checks,
        "failed_checks": [
            name for name, passed in checks.items() if not passed
        ],
        "aggregate": {
            "pair_count": len(pair_rows),
            "shared_parent_identity_rate": shared_parent_rate,
            "offer_total_task_score_minus_withhold": task_delta,
            "mean_offer_minus_withhold_composite": (
                mean_composite_delta
            ),
            "offer_composite_wins": composite_wins,
            "prefix_primitive_action_cost_per_arm": len(
                context["prefix"]["actions"]
            ),
            "post_prefix_primitive_action_cost_per_arm": int(
                context["manifest"]["live_test"][
                    "post_prefix_actions_per_arm"
                ]
            ),
            "total_primitive_action_cost": total_primitive_cost,
            "rendered_utf8_bytes_per_intervention": (
                context["interventions"][
                    "rendered_utf8_bytes_per_condition"
                ]
            ),
            "promoted_child_count": (
                child_family.admissible_response_count
            ),
            "response_reproduction_number": (
                reproduction_after.response_reproduction_number
            ),
            "response_reproduction_regime": reproduction_after.regime,
        },
        "criticality_interpretation": {
            "subcritical": "R_response < 1",
            "critical": "R_response = 1",
            "supercritical": "R_response > 1",
            "h97_can_establish_at_most": "critical",
            "supercritical_claim_authorized": False,
        },
        "claim_boundary": list(context["manifest"]["claim_boundary"]),
    }
    result = {**result_core, "sha256": _sha(result_core)}
    _atomic_json(result_path, result)
    return result


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
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    args = parser.parse_args()
    if args.max_output_tokens <= 0 or args.timeout_seconds <= 0:
        raise SystemExit("output-token and timeout limits must be positive")
    result = (
        run_preflight(args)
        if args.preflight_only
        else run_live(args)
    )
    if not args.preflight_only:
        print(json.dumps({
            "result_path": _relative_ref(
                Path(args.output_dir).resolve() / "result.json"
            ),
            "status": result["status"],
            "verdict": result["verdict"],
            "failed_checks": result.get("failed_checks", []),
            "aggregate": result.get("aggregate"),
            "response_reproduction_after": (
                result.get("response_reproduction_after")
            ),
            "sha256": result["sha256"],
        }, indent=2, sort_keys=True))
        return 0
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
