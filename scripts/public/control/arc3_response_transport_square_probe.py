#!/usr/bin/env python3
"""Test one-hop object-response transport and structural refusal on ARC."""

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

import arc3_instrumented_proposal_probe as proposal_probe  # noqa: E402
import arc3_prospective_response_family_probe as h94_probe  # noqa: E402
from arc3_pairwise_memory_content_probe import (  # noqa: E402
    _condition_bundle_base,
    _condition_provenance,
    _equalize_rendered_bytes,
    _load_source,
    _proposal,
)
from arc3_paired_recall_probe import (  # noqa: E402
    _atomic_json,
    _controller_instance_sha256,
    _file_sha256,
    _relative_ref,
)
from arc3_responses_agent_probe import (  # noqa: E402
    _resolve_game_id,
    _sha_payload,
    _sleep_memory_scope,
    settled_observation_receipt,
)
from ztare.common.instrumented_proposal_plasticity import (  # noqa: E402
    InstrumentedProposalOutcome,
    estimate_instrumented_plasticity,
)
from ztare.common.decision_intervention_market import (  # noqa: E402
    decision_intervention_proposal_from_receipt,
)
from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.object_basin_response import (  # noqa: E402
    compile_object_response_family,
    object_contract_from_receipt,
    object_outcome_from_receipt,
    object_proposal_from_receipt,
    object_response_family_from_receipt,
    object_transition_from_receipt,
)
from ztare.common.object_linked_judgment import (  # noqa: E402
    ObjectLinkedControllerProposal,
    ObjectReferenceAuthority,
)
from ztare.common.object_response_transport import (  # noqa: E402
    compile_intervention_revision_transport,
    compile_response_transport_candidate,
    compile_unique_type_object_transport,
    transport_object_role_contract,
)
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    select_sparse_memories,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.observation_object_catalog import (  # noqa: E402
    compile_catalog_from_observation,
    compile_catalog_presentation,
)


SCHEMA = "ztare-arc3-response-transport-square-v1"


def _sha(payload: Mapping[str, Any]) -> str:
    return proposal_probe._sha(payload)


def _verify_receipt_sha(
    receipt: Mapping[str, Any],
    name: str,
) -> None:
    core = dict(receipt)
    claimed = str(core.pop("sha256", ""))
    if not claimed or _sha(core) != claimed:
        raise ValueError(f"{name} receipt hash drifted")


def _repo_ref_path(ref: str) -> Path:
    value = str(ref).split("#", 1)[0]
    path = (REPO / value).resolve()
    if REPO not in path.parents:
        raise ValueError("receipt ref escaped the repository")
    return path


def _payload_invariant_sha256(
    digest: Mapping[str, Any],
) -> str:
    """Hash intervention content after removing its context envelope."""

    payload = dict(digest)
    for key in (
        "consumption_scope",
        "consumption_scope_sha256",
        "presentation_padding",
    ):
        payload.pop(key, None)
    return _sha_payload(payload)


def _replay_prefix(
    *,
    game_id: str,
    actions: Sequence[int],
) -> dict[str, Any]:
    adapter = ArcAgi3Adapter(game_id)
    grid = adapter.reset()
    arity = int(adapter.action_arity)
    observations = [settled_observation_receipt(
        grid,
        observation_index=0,
        action_count=0,
        levels_completed=int(adapter.levels_completed),
        adapter_epoch=int(adapter.current_epoch),
        available_action_indices=tuple(range(arity)),
    )]
    transitions = []
    start_levels = int(adapter.levels_completed)
    for index, action in enumerate(actions, start=1):
        source = observations[-1]
        grid = adapter.step(int(action))
        successor = settled_observation_receipt(
            grid,
            observation_index=index,
            action_count=index,
            levels_completed=int(adapter.levels_completed),
            adapter_epoch=int(adapter.current_epoch),
            available_action_indices=tuple(range(arity)),
        )
        observations.append(successor)
        identity = adapter.last_transition_identity
        transitions.append({
            "prefix_action_count": index,
            "action": int(action),
            "source_observation_sha256": source["sha256"],
            "successor_observation_sha256": successor["sha256"],
            "transition_kind": (
                identity.kind if identity is not None else ""
            ),
            "transition_authority": (
                identity.authority if identity is not None else ""
            ),
            "boundary_kind": (
                identity.boundary_kind if identity is not None else None
            ),
        })
    if int(adapter.levels_completed) != start_levels:
        raise RuntimeError("H95 prefix crossed a level boundary")
    return {
        "actions": [int(value) for value in actions],
        "action_arity": arity,
        "observations": observations,
        "transitions": transitions,
        "final_observation": observations[-1],
        "sha256": _sha({
            "actions": [int(value) for value in actions],
            "observations": observations,
            "transitions": transitions,
        }),
    }


def _source_evidence(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
) -> dict[str, Any]:
    source_spec = dict(spec["source_response"])
    result_path = (
        spec_path.parent / str(source_spec["result_ref"])
    ).resolve()
    source_result = h94_probe._verify_result(
        result_path,
        expected_file_sha256=str(
            source_spec["result_file_sha256"]
        ),
        expected_embedded_sha256=str(
            source_spec["result_embedded_sha256"]
        ),
    )
    replay = h94_probe.verify_saved_result(result_path)
    family = object_response_family_from_receipt(
        source_result["response_family"]
    )
    if family.sha256 != str(source_spec["family_sha256"]):
        raise ValueError("H94 source family drifted")
    matches = [
        row for row in family.responses
        if row.sha256 == str(source_spec["response_sha256"])
    ]
    if len(matches) != 1:
        raise ValueError("H94 source response drifted")
    source_response = matches[0]
    if (
        source_response.pre_basin_sha256
        != str(source_spec["pre_basin_sha256"])
    ):
        raise ValueError("H94 source basin drifted")
    source_manifest_path = (
        REPO / str(source_result["manifest_ref"])
    ).resolve()
    source_manifest = json.loads(
        source_manifest_path.read_text(encoding="utf-8")
    )
    source_contract = object_contract_from_receipt(
        source_manifest["target_contract"]
    )
    source_intervention = decision_intervention_proposal_from_receipt(
        source_manifest["target_proposal"]
    )
    source_placebo_intervention = (
        decision_intervention_proposal_from_receipt(
            source_manifest["placebo_proposal"]
        )
    )
    if (
        source_contract.sha256 != str(source_spec["contract_sha256"])
        or source_contract.scope.sha256
        != str(source_spec["scope_sha256"])
        or source_contract.catalog_sha256
        != str(source_spec["catalog_sha256"])
    ):
        raise ValueError("H94 source contract authority drifted")

    witness_spec = dict(spec["source_response_witness"])
    witness_path = (
        spec_path.parent / str(witness_spec["arm_ref"])
    ).resolve()
    if _file_sha256(witness_path) != str(
        witness_spec["arm_file_sha256"]
    ):
        raise ValueError("H93 source response witness file drifted")
    witness_arm = json.loads(witness_path.read_text(encoding="utf-8"))
    instrumented = witness_arm["probe"]["turns"][0][
        "instrumented_proposal"
    ]
    source_pre = object_proposal_from_receipt(
        instrumented["pre_proposal"]
    )
    source_post = object_proposal_from_receipt(
        instrumented["post_proposal"]
    )
    if (
        source_pre.sha256
        != str(witness_spec["pre_proposal_sha256"])
        or source_post.sha256
        != str(witness_spec["post_proposal_sha256"])
    ):
        raise ValueError("H93 source proposal witness drifted")
    return {
        "result_path": result_path,
        "result": source_result,
        "result_replay": replay,
        "family": family,
        "response": source_response,
        "manifest_path": source_manifest_path,
        "contract": source_contract,
        "intervention": source_intervention,
        "placebo_intervention": source_placebo_intervention,
        "witness_path": witness_path,
        "pre_proposal": source_pre,
        "post_proposal": source_post,
    }


def _condition_setup(
    *,
    source_result_path: Path,
    spec: Mapping[str, Any],
    spec_path: Path,
    scope,
    budget: int,
) -> dict[str, Any]:
    loader_path = Path("/private/tmp/ztare_h95_loader_spec.json")
    _atomic_json(loader_path, {
        "schema": spec["schema"],
        "left": spec["live_test"]["target_assignment"],
        "right": spec["live_test"]["placebo_assignment"],
    })
    source_meta, target_condition, placebo_condition, turns = _load_source(
        source_result_path,
        loader_path,
    )
    source_meta["spec_path"] = _relative_ref(spec_path)
    source_meta["spec_sha256"] = _file_sha256(spec_path)
    target_condition["condition_id"] = str(
        spec["live_test"]["target_assignment"]["condition_id"]
    )
    placebo_condition["condition_id"] = str(
        spec["live_test"]["placebo_assignment"]["condition_id"]
    )
    target_provenance = _condition_provenance(
        source_meta=source_meta,
        condition=target_condition,
        turns=turns,
    )
    placebo_provenance = _condition_provenance(
        source_meta=source_meta,
        condition=placebo_condition,
        turns=turns,
    )
    target_base = _condition_bundle_base(
        condition=target_condition,
        provenance=target_provenance,
        scope=scope,
        source_meta=source_meta,
    )
    placebo_base = _condition_bundle_base(
        condition=placebo_condition,
        provenance=placebo_provenance,
        scope=scope,
        source_meta=source_meta,
    )
    target_digest, placebo_digest, rendered_bytes = (
        _equalize_rendered_bytes(target_base, placebo_base)
    )
    target_proposal = _proposal(
        condition=target_condition,
        digest=target_digest,
        provenance=target_provenance,
        scope=scope,
        budget=budget,
        rendered_bytes=rendered_bytes,
    )
    placebo_proposal = _proposal(
        condition=placebo_condition,
        digest=placebo_digest,
        provenance=placebo_provenance,
        scope=scope,
        budget=budget,
        rendered_bytes=rendered_bytes,
    )
    return {
        "source_meta": source_meta,
        "target_condition": target_condition,
        "placebo_condition": placebo_condition,
        "target_digest": target_digest,
        "placebo_digest": placebo_digest,
        "target_proposal": target_proposal,
        "placebo_proposal": placebo_proposal,
        "rendered_bytes": rendered_bytes,
    }


def _authorization(
    *,
    proposal,
    scope,
    rendered_bytes: int,
    controller_instance_sha256: str,
    observation_sha256: str,
    decision_ref: str,
    intervention_transport_sha256: str,
) -> dict[str, Any]:
    candidate = proposal.to_memory_candidate()
    recall = select_sparse_memories(
        WakeSleepCreditState(),
        (candidate,),
        scope=scope,
        max_items=1,
        minimum_score=-2.0,
        max_prompt_tokens=rendered_bytes,
    )
    decision = authorize_recall_consumption(
        recall,
        (candidate,),
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=observation_sha256,
        decision_ref=decision_ref,
        compatibility_transport_sha256=intervention_transport_sha256,
    )
    _, consumption = consume_recall_once(
        decision,
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=observation_sha256,
    )
    return {
        "decision": decision,
        "consumption": consumption,
    }


def _mapped_witness_proposal(
    source: ObjectLinkedControllerProposal,
    *,
    target_scope,
    target_catalog_sha256: str,
    transport,
) -> ObjectLinkedControllerProposal:
    return ObjectLinkedControllerProposal(
        scope=target_scope,
        controller_instance_sha256="h95-preflight-witness",
        observation_sha256=target_scope.context_sha256,
        catalog_sha256=target_catalog_sha256,
        proposal_ref=f"transported:{source.sha256}",
        action_ref=source.action_ref,
        predicted_consequence_ref=(
            f"transported:{source.predicted_consequence_ref}"
        ),
        controlled_object_ref=transport.map_ref(
            source.controlled_object_ref
        ),
        ordered_waypoint_refs=transport.map_path(
            source.ordered_waypoint_refs
        ),
    )


def verify_saved_result(result_path: Path) -> dict[str, Any]:
    """Replay H95 identities, checkpoints, settlements, and promotion."""

    path = result_path.resolve()
    result = json.loads(path.read_text(encoding="utf-8"))
    _verify_receipt_sha(result, "H95 result")
    if result.get("schema") != SCHEMA:
        raise ValueError("saved H95 result has the wrong schema")
    manifest_path = _repo_ref_path(str(result["manifest_ref"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest["experiment_sha256"]) != str(
        result["experiment_sha256"]
    ):
        raise ValueError("H95 result crossed manifest identity")

    for name in (
        "positive_object_transport",
        "intervention_revision_transport",
        "placebo_intervention_revision_transport",
        "negative_object_transport",
        "preflight_transport_candidate",
    ):
        _verify_receipt_sha(result[name], name)
        if result[name] != manifest[name]:
            raise ValueError(f"{name} drifted from manifest")
    if result["negative_object_transport"]["status"] != "refused":
        raise ValueError("negative transport no longer refuses")
    if result["negative_branch_controller_contact"] is not False:
        raise ValueError("negative branch contacted a controller")

    spec_path = _repo_ref_path(str(manifest["spec_ref"]))
    if _file_sha256(spec_path) != str(manifest["spec_sha256"]):
        raise ValueError("H95 spec file drifted")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_spec = dict(spec["source_response"])
    source_result_path = (
        spec_path.parent / str(source_spec["result_ref"])
    ).resolve()
    h94_probe._verify_result(
        source_result_path,
        expected_file_sha256=str(source_spec["result_file_sha256"]),
        expected_embedded_sha256=str(
            source_spec["result_embedded_sha256"]
        ),
    )
    h94_probe.verify_saved_result(source_result_path)
    witness_spec = dict(spec["source_response_witness"])
    witness_path = (
        spec_path.parent / str(witness_spec["arm_ref"])
    ).resolve()
    if _file_sha256(witness_path) != str(
        witness_spec["arm_file_sha256"]
    ):
        raise ValueError("H93 witness file drifted")

    source_family = object_response_family_from_receipt(
        manifest["source_response_family"]
    )
    source_contract = object_contract_from_receipt(
        manifest["source_contract"]
    )
    target_contract = object_contract_from_receipt(
        manifest["target_contract"]
    )
    for name in (
        "source_intervention",
        "source_placebo_intervention",
        "target_proposal",
        "placebo_proposal",
    ):
        decision_intervention_proposal_from_receipt(manifest[name])
    if source_family.sha256 != str(
        spec["source_response"]["family_sha256"]
    ):
        raise ValueError("source response family drifted")
    if source_contract.sha256 != str(
        spec["source_response"]["contract_sha256"]
    ):
        raise ValueError("source response contract drifted")
    if target_contract.intervention_revision_sha256 != str(
        manifest["target_proposal"]["intervention_revision_sha256"]
    ):
        raise ValueError("target contract crossed intervention revision")

    all_outcomes: list[InstrumentedProposalOutcome] = []
    task_deltas = []
    composite_deltas = []
    candidate_count = 0
    for pair in result["pairs"]:
        pair_index = int(pair["pair_index"])
        _verify_receipt_sha(pair["stratum"], "H95 stratum")
        values = {}
        for assignment, condition_key, candidate_key in (
            (
                "offer",
                "target_proposal",
                "offer_transport_candidate",
            ),
            (
                "withhold",
                "placebo_proposal",
                "withhold_basin_transport_check",
            ),
        ):
            candidate = pair[candidate_key]
            _verify_receipt_sha(
                candidate,
                f"H95 pair {pair_index} {assignment} candidate",
            )
            if (
                candidate["status"] != "candidate_commuting"
                or candidate["object_transport_sha256"]
                != result["positive_object_transport"]["sha256"]
                or candidate["intervention_transport_sha256"]
                != result["intervention_revision_transport"]["sha256"]
            ):
                raise ValueError("saved target response square drifted")
            candidate_count += 1
            transition = object_transition_from_receipt(
                pair[f"{assignment}_transition"]
            )
            outcome = object_outcome_from_receipt(
                pair[f"{assignment}_outcome"],
                transition=transition,
            )
            all_outcomes.append(outcome)
            metrics = pair[f"{assignment}_metrics"]
            expected_external = (
                0.8 * float(metrics["task_score"])
                + 0.2 * float(metrics["efficiency_score"])
            )
            if outcome.external_value != expected_external:
                raise ValueError("saved H95 external value drifted")
            condition_id = str(
                manifest[condition_key]["provider_id"]
            )
            arm_path = (
                path.parent
                / "arms"
                / (
                    f"pair_{pair_index:02d}_{assignment}_"
                    f"{condition_id}.json"
                )
            )
            arm = json.loads(arm_path.read_text(encoding="utf-8"))
            if arm["transition"] != pair[f"{assignment}_transition"]:
                raise ValueError("H95 arm transition drifted")
            if arm["metrics"] != metrics:
                raise ValueError("H95 arm metrics drifted")
            external_ref, claimed_file_sha = (
                str(outcome.external_outcome_ref).split("#sha256=", 1)
            )
            if (
                _repo_ref_path(external_ref) != arm_path.resolve()
                or _file_sha256(arm_path) != claimed_file_sha
            ):
                raise ValueError("H95 outcome arm file drifted")
            probe = arm["probe"]
            if (
                int(probe["actions_executed"])
                != int(manifest["post_prefix_budget_per_arm"])
                or int(probe["total_actions_executed"])
                != int(manifest["total_primitive_actions_per_arm"])
                or probe["restored_prefix"]["actions"]
                != manifest["positive_prefix"]["actions"]
            ):
                raise ValueError("H95 primitive action cost drifted")
            raw = arm["raw_proposal_checkpoint"]
            raw_path = _repo_ref_path(str(raw["ref"]))
            if (
                int(raw["count"]) != 2
                or _file_sha256(raw_path) != str(raw["sha256"])
            ):
                raise ValueError("H95 raw proposal checkpoint drifted")
            if assignment == "offer":
                checkpoint = arm["admission_decision_checkpoint"]
                if (
                    checkpoint["decision"] != candidate
                    or int(checkpoint["count"]) != 1
                    or _file_sha256(_repo_ref_path(checkpoint["ref"]))
                    != str(checkpoint["sha256"])
                ):
                    raise ValueError("H95 admission checkpoint drifted")
            elif arm["admission_decision_checkpoint"] is not None:
                raise ValueError("H95 placebo unexpectedly had admission")
            values[assignment] = outcome.net_external_value

        task_delta = (
            float(pair["offer_metrics"]["task_score"])
            - float(pair["withhold_metrics"]["task_score"])
        )
        composite_delta = values["offer"] - values["withhold"]
        if task_delta != float(pair["offer_task_minus_withhold"]):
            raise ValueError("H95 pair task delta drifted")
        if composite_delta != float(
            pair["offer_composite_minus_withhold"]
        ):
            raise ValueError("H95 pair composite delta drifted")
        task_deltas.append(task_delta)
        composite_deltas.append(composite_delta)

    estimate = estimate_instrumented_plasticity(
        all_outcomes,
        minimum_first_stage=float(
            spec["success_criterion"][
                "minimum_first_stage_transport_delta"
            ]
        ),
    )
    if estimate.to_receipt() != result["target_fiber_estimate"]:
        raise ValueError("H95 target-fiber estimate replay drifted")
    settlement_set_sha256 = _sha({
        "outcome_sha256s": sorted(
            outcome.sha256 for outcome in all_outcomes
        ),
    })
    promoted = compile_object_response_family(
        all_outcomes,
        source_result_ref=(
            f"{_relative_ref(path.parent)}/settlements"
        ),
        source_result_sha256=settlement_set_sha256,
        minimum_offer_count=2,
        minimum_withhold_count=2,
        minimum_first_stage_transport_delta=1.0,
        minimum_intent_to_treat_net_delta=0.0,
    )
    if promoted.to_receipt() != result[
        "promoted_target_response_family"
    ]:
        raise ValueError("H95 promoted response family replay drifted")
    aggregate = result["aggregate"]
    if sum(task_deltas) != float(
        aggregate["offer_total_task_score_minus_withhold"]
    ):
        raise ValueError("H95 aggregate task delta drifted")
    if (
        sum(composite_deltas) / len(composite_deltas)
        != float(aggregate["mean_offer_minus_withhold_composite"])
    ):
        raise ValueError("H95 aggregate composite mean drifted")
    if sum(value > 0.0 for value in composite_deltas) != int(
        aggregate["offer_composite_wins"]
    ):
        raise ValueError("H95 aggregate win count drifted")
    return {
        "status": "offline_replay_verified",
        "result_ref": _relative_ref(path),
        "result_file_sha256": _file_sha256(path),
        "result_sha256": result["sha256"],
        "manifest_file_sha256": _file_sha256(manifest_path),
        "pair_count": len(result["pairs"]),
        "candidate_count": candidate_count,
        "mean_offer_minus_withhold_composite": (
            aggregate["mean_offer_minus_withhold_composite"]
        ),
        "promoted_target_response_family_sha256": promoted.sha256,
    }


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema") != "ztare-arc3-response-transport-square-spec-v1":
        raise ValueError("wrong H95 experiment spec")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_result_path = Path(args.source_result).resolve()

    source = _source_evidence(spec=spec, spec_path=spec_path)
    prefix_evidence = dict(spec["prefix_evidence"])
    prefix_arm_path = (
        spec_path.parent / str(prefix_evidence["arm_ref"])
    ).resolve()
    if _file_sha256(prefix_arm_path) != str(
        prefix_evidence["arm_file_sha256"]
    ):
        raise ValueError("H94 prefix evidence file drifted")

    game_id = _resolve_game_id(args.game)
    positive_spec = dict(prefix_evidence["positive_prefix"])
    negative_spec = dict(prefix_evidence["negative_prefix"])
    positive_prefix = _replay_prefix(
        game_id=game_id,
        actions=positive_spec["actions"],
    )
    negative_prefix = _replay_prefix(
        game_id=game_id,
        actions=negative_spec["actions"],
    )
    positive_observation = positive_prefix["final_observation"]
    negative_observation = negative_prefix["final_observation"]
    if (
        positive_observation["sha256"]
        != str(positive_spec["expected_observation_sha256"])
    ):
        raise ValueError("positive prefix observation drifted")
    if (
        negative_observation["sha256"]
        != str(negative_spec["expected_observation_sha256"])
    ):
        raise ValueError("negative prefix observation drifted")
    source_observation = positive_prefix["observations"][0]
    source_catalog = compile_catalog_from_observation(source_observation)
    positive_catalog = compile_catalog_from_observation(
        positive_observation
    )
    negative_catalog = compile_catalog_from_observation(
        negative_observation
    )
    if positive_catalog.sha256 != str(
        positive_spec["expected_catalog_sha256"]
    ):
        raise ValueError("positive prefix catalog drifted")
    if negative_catalog.sha256 != str(
        negative_spec["expected_catalog_sha256"]
    ):
        raise ValueError("negative prefix catalog drifted")

    source_contract = source["contract"]
    source_pre = source["pre_proposal"]
    source_post = source["post_proposal"]
    required_refs = tuple(sorted({
        source_contract.required_controlled_object_ref,
        *source_contract.required_waypoint_refs,
        *source_contract.forbidden_controlled_object_refs,
        *source_pre.path,
        *source_post.path,
    }))
    positive_transport = compile_unique_type_object_transport(
        source_catalog,
        positive_catalog,
        required_source_object_refs=required_refs,
        evidence_refs=(
            f"{_relative_ref(prefix_arm_path)}"
            f"#sha256={_file_sha256(prefix_arm_path)}",
            f"positive_prefix:{positive_prefix['sha256']}",
        ),
    )
    negative_transport = compile_unique_type_object_transport(
        source_catalog,
        negative_catalog,
        required_source_object_refs=required_refs,
        evidence_refs=(
            f"{_relative_ref(prefix_arm_path)}"
            f"#sha256={_file_sha256(prefix_arm_path)}",
            f"negative_prefix:{negative_prefix['sha256']}",
        ),
    )
    if positive_transport.status != "transportable":
        raise ValueError("positive H95 object transport refused")
    if (
        negative_transport.status != "refused"
        or negative_transport.reason
        != str(negative_spec["expected_refusal_reason"])
    ):
        raise ValueError("negative H95 transport did not refuse")

    target_scope = _sleep_memory_scope(
        game_id=game_id,
        model_id=args.model,
        reasoning_effort=args.reasoning_effort,
        boundary_observation=positive_observation,
        action_arity=int(positive_prefix["action_arity"]),
    )
    source_conditions = _condition_setup(
        source_result_path=source_result_path,
        spec=spec,
        spec_path=spec_path,
        scope=source_contract.scope,
        budget=args.budget,
    )
    conditions = _condition_setup(
        source_result_path=source_result_path,
        spec=spec,
        spec_path=spec_path,
        scope=target_scope,
        budget=args.budget,
    )
    source_intervention = source["intervention"]
    source_placebo_intervention = source["placebo_intervention"]
    reconstructed_source = source_conditions["target_proposal"]
    if reconstructed_source.to_receipt() != (
        source_intervention.to_receipt()
    ):
        raise ValueError(
            "H95 could not reconstruct the frozen source intervention"
        )
    if source_conditions["placebo_proposal"].to_receipt() != (
        source_placebo_intervention.to_receipt()
    ):
        raise ValueError(
            "H95 could not reconstruct the frozen source placebo"
        )
    source_payload_invariant = _payload_invariant_sha256(
        source_conditions["target_digest"]
    )
    target_payload_invariant = _payload_invariant_sha256(
        conditions["target_digest"]
    )
    intervention_transport = compile_intervention_revision_transport(
        source_intervention,
        conditions["target_proposal"],
        source_payload_invariant_sha256=source_payload_invariant,
        target_payload_invariant_sha256=target_payload_invariant,
        evidence_refs=(
            f"source_manifest:{_relative_ref(source['manifest_path'])}",
            f"source_intervention:{source_intervention.to_receipt()['sha256']}",
            f"positive_prefix:{positive_prefix['sha256']}",
        ),
    )
    placebo_intervention_transport = (
        compile_intervention_revision_transport(
            source_placebo_intervention,
            conditions["placebo_proposal"],
            source_payload_invariant_sha256=(
                _payload_invariant_sha256(
                    source_conditions["placebo_digest"]
                )
            ),
            target_payload_invariant_sha256=(
                _payload_invariant_sha256(
                    conditions["placebo_digest"]
                )
            ),
            evidence_refs=(
                f"source_manifest:{_relative_ref(source['manifest_path'])}",
                "source_intervention:"
                f"{source_placebo_intervention.to_receipt()['sha256']}",
                f"positive_prefix:{positive_prefix['sha256']}",
            ),
        )
    )
    if intervention_transport.status != "transportable":
        raise ValueError(
            "H95 intervention re-rendering refused: "
            f"{intervention_transport.reason}"
        )
    if placebo_intervention_transport.status != "transportable":
        raise ValueError(
            "H95 placebo re-rendering refused: "
            f"{placebo_intervention_transport.reason}"
        )
    target_contract = transport_object_role_contract(
        source_contract,
        target_scope=target_scope,
        target_catalog=positive_catalog,
        transport=positive_transport,
        intervention_transport=intervention_transport,
        evidence_refs=(
            *source_contract.evidence_refs,
            f"object_transport:{positive_transport.sha256}",
            f"intervention_transport:{intervention_transport.sha256}",
            f"prefix_evidence:{positive_prefix['sha256']}",
        ),
    )
    rendered_bytes = int(conditions["rendered_bytes"])
    if rendered_bytes != int(
        spec["costs"]["presented_bytes_per_intervention"]
    ):
        raise ValueError("H95 intervention-byte cost drifted")
    if args.budget != int(
        spec["costs"]["post_prefix_actions_per_arm"]
    ):
        raise ValueError("H95 post-prefix action budget drifted")
    if (
        conditions["target_proposal"].intervention_revision_sha256
        != target_contract.intervention_revision_sha256
    ):
        raise ValueError("H95 target intervention transport drifted")
    if (
        conditions["target_proposal"].intervention_revision_sha256
        == source_contract.intervention_revision_sha256
    ):
        raise ValueError("H95 target re-rendering did not mint a revision")
    mapped_pre = _mapped_witness_proposal(
        source_pre,
        target_scope=target_scope,
        target_catalog_sha256=positive_catalog.sha256,
        transport=positive_transport,
    )
    preflight_candidate = compile_response_transport_candidate(
        source_family=source["family"],
        source_response=source["response"],
        object_transport=positive_transport,
        intervention_transport=intervention_transport,
        source_contract=source_contract,
        target_contract=target_contract,
        source_pre_proposal=source_pre,
        source_post_proposal=source_post,
        target_pre_proposal=mapped_pre,
    )
    if preflight_candidate.status != "candidate_commuting":
        raise ValueError("H95 preflight response square did not commute")

    pair_count = int(args.pairs)
    if pair_count != int(spec["live_test"]["pair_count"]):
        raise ValueError("H95 pair count drifted")
    orders = [
        ["offer", "withhold"] if index % 2 == 0
        else ["withhold", "offer"]
        for index in range(pair_count)
    ]
    presentation = compile_catalog_presentation(positive_catalog)
    target_authority = ObjectReferenceAuthority(
        observation_sha256=positive_observation["sha256"],
        catalog_sha256=positive_catalog.sha256,
        object_refs=positive_catalog.object_refs,
    )
    manifest_core = {
        "schema": SCHEMA,
        "kind": "experiment_manifest",
        "game_id": game_id,
        "pairs": pair_count,
        "post_prefix_budget_per_arm": args.budget,
        "prefix_actions_per_arm": len(positive_spec["actions"]),
        "total_primitive_actions_per_arm": (
            args.budget + len(positive_spec["actions"])
        ),
        "proposal_inferences_before_post_prefix_action": 2,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "seed": args.seed,
        "arm_orders": orders,
        "source_verification": {
            "h94_result_replay": source["result_replay"],
            "h94_result_ref": _relative_ref(source["result_path"]),
            "h94_result_sha256": source["result"]["sha256"],
            "h93_witness_ref": _relative_ref(source["witness_path"]),
            "h93_witness_file_sha256": _file_sha256(
                source["witness_path"]
            ),
        },
        "source_response_family": source["family"].to_receipt(),
        "source_response": source["response"].to_receipt(),
        "source_contract": source_contract.to_receipt(),
        "source_intervention": source_intervention.to_receipt(),
        "source_placebo_intervention": (
            source_placebo_intervention.to_receipt()
        ),
        "source_pre_proposal": source_pre.to_receipt(),
        "source_post_proposal": source_post.to_receipt(),
        "positive_prefix": positive_prefix,
        "negative_prefix": negative_prefix,
        "positive_object_transport": positive_transport.to_receipt(),
        "intervention_revision_transport": (
            intervention_transport.to_receipt()
        ),
        "placebo_intervention_revision_transport": (
            placebo_intervention_transport.to_receipt()
        ),
        "negative_object_transport": negative_transport.to_receipt(),
        "negative_branch_controller_contact": False,
        "target_scope": target_scope.to_receipt(),
        "target_catalog": positive_catalog.to_receipt(),
        "target_presentation": presentation.to_receipt(),
        "target_contract": target_contract.to_receipt(),
        "preflight_transport_candidate": (
            preflight_candidate.to_receipt()
        ),
        "source": conditions["source_meta"],
        "target_digest_sha256": _sha_payload(
            conditions["target_digest"]
        ),
        "placebo_digest_sha256": _sha_payload(
            conditions["placebo_digest"]
        ),
        "target_proposal": (
            conditions["target_proposal"].to_receipt()
        ),
        "placebo_proposal": (
            conditions["placebo_proposal"].to_receipt()
        ),
        "rendered_utf8_bytes_per_intervention": rendered_bytes,
        "spec_ref": _relative_ref(spec_path),
        "spec_sha256": _file_sha256(spec_path),
        "success_criterion": dict(spec["success_criterion"]),
    }
    experiment_sha256 = _sha(manifest_core)
    manifest = {
        **manifest_core,
        "experiment_sha256": experiment_sha256,
    }
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing != manifest:
            raise RuntimeError("existing H95 manifest drifted")
    else:
        _atomic_json(manifest_path, manifest)
    if args.preflight_only:
        return {
            "status": "preflight_complete",
            "manifest_ref": _relative_ref(manifest_path),
            "experiment_sha256": experiment_sha256,
            "positive_transport": positive_transport.to_receipt(),
            "intervention_transport": (
                intervention_transport.to_receipt()
            ),
            "placebo_intervention_transport": (
                placebo_intervention_transport.to_receipt()
            ),
            "negative_transport": negative_transport.to_receipt(),
            "preflight_candidate": preflight_candidate.to_receipt(),
        }

    arm_conditions = {
        "offer": (
            conditions["target_condition"],
            conditions["target_digest"],
            conditions["target_proposal"],
            intervention_transport,
        ),
        "withhold": (
            conditions["placebo_condition"],
            conditions["placebo_digest"],
            conditions["placebo_proposal"],
            placebo_intervention_transport,
        ),
    }
    all_outcomes: list[InstrumentedProposalOutcome] = []
    pair_rows = []
    for pair_index, order in enumerate(orders, start=1):
        stratum = proposal_probe._stratum(
            scope=target_scope,
            game_id=game_id,
            observation_sha256=positive_observation["sha256"],
            budget=args.budget,
            seed=args.seed,
            pair_index=pair_index,
        )
        authorizations = {}
        for assignment in ("offer", "withhold"):
            _condition, _digest, intervention, revision_transport = (
                arm_conditions[assignment]
            )
            instance = _controller_instance_sha256(
                experiment_sha256=experiment_sha256,
                pair_index=pair_index,
                assignment=assignment,
            )
            authorizations[assignment] = {
                **_authorization(
                    proposal=intervention,
                    scope=target_scope,
                    rendered_bytes=rendered_bytes,
                    controller_instance_sha256=instance,
                    observation_sha256=positive_observation["sha256"],
                    decision_ref=(
                        f"pair-{pair_index:02d}:"
                        f"{assignment}:decision-0"
                    ),
                    intervention_transport_sha256=(
                        revision_transport.sha256
                    ),
                ),
                "controller_instance": instance,
            }

        def transport_selector(target_pre):
            return compile_response_transport_candidate(
                source_family=source["family"],
                source_response=source["response"],
                object_transport=positive_transport,
                intervention_transport=intervention_transport,
                source_contract=source_contract,
                target_contract=target_contract,
                source_pre_proposal=source_pre,
                source_post_proposal=source_post,
                target_pre_proposal=target_pre,
            )

        arms = {}
        for assignment in order:
            condition, digest, _intervention, _revision_transport = (
                arm_conditions[assignment]
            )
            auth = authorizations[assignment]
            arms[assignment] = proposal_probe._run_arm(
                receipt_schema=SCHEMA,
                output_dir=output_dir,
                experiment_sha256=experiment_sha256,
                pair_index=pair_index,
                assignment=assignment,
                condition_id=str(condition["condition_id"]),
                game_id=game_id,
                budget=args.budget,
                model_id=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
                expected_observation_sha256=(
                    positive_observation["sha256"]
                ),
                action_arity=int(positive_prefix["action_arity"]),
                digest=digest,
                consumption_decision=auth["decision"],
                consumption_receipt=auth["consumption"],
                target_contract=target_contract,
                controller_instance_sha256=(
                    auth["controller_instance"]
                ),
                stratum_sha256=stratum.sha256,
                feature_adapter=None,
                object_catalog=positive_catalog,
                object_authority=target_authority,
                object_presentation=presentation,
                admission_selector=(
                    transport_selector
                    if assignment == "offer"
                    else None
                ),
                restored_prefix_actions=tuple(
                    int(value) for value in positive_spec["actions"]
                ),
            )

        outcomes = {}
        transitions = {}
        candidates = {}
        for assignment in ("offer", "withhold"):
            condition = arm_conditions[assignment][0]
            arm_path = (
                output_dir
                / "arms"
                / (
                    f"pair_{pair_index:02d}_{assignment}_"
                    f"{condition['condition_id']}.json"
                )
            )
            transitions[assignment] = object_transition_from_receipt(
                arms[assignment]["transition"]
            )
            outcomes[assignment] = (
                proposal_probe._instrumented_outcome(
                    arms[assignment],
                    transition=transitions[assignment],
                    arm_path=arm_path,
                )
            )
            all_outcomes.append(outcomes[assignment])
            instrumented = arms[assignment]["probe"]["turns"][0][
                "instrumented_proposal"
            ]
            blind = object_proposal_from_receipt(
                instrumented["pre_proposal"]
            )
            candidates[assignment] = (
                compile_response_transport_candidate(
                    source_family=source["family"],
                    source_response=source["response"],
                    object_transport=positive_transport,
                    intervention_transport=intervention_transport,
                    source_contract=source_contract,
                    target_contract=target_contract,
                    source_pre_proposal=source_pre,
                    source_post_proposal=source_post,
                    target_pre_proposal=blind,
                )
            )
            if candidates[assignment].status != "candidate_commuting":
                raise RuntimeError(
                    "H95 blind proposal left transported basin"
                )
        target_admission = arms["offer"][
            "admission_decision_checkpoint"
        ]["decision"]
        if target_admission != candidates["offer"].to_receipt():
            raise RuntimeError("H95 admission checkpoint drifted")
        offer_value = outcomes["offer"].net_external_value
        withhold_value = outcomes["withhold"].net_external_value
        pair_row = {
            "pair_index": pair_index,
            "arm_order": order,
            "stratum": stratum.to_receipt(),
            "offer_transport_candidate": (
                candidates["offer"].to_receipt()
            ),
            "withhold_basin_transport_check": (
                candidates["withhold"].to_receipt()
            ),
            "offer_transition": transitions["offer"].to_receipt(),
            "withhold_transition": (
                transitions["withhold"].to_receipt()
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
        minimum_first_stage=float(
            spec["success_criterion"][
                "minimum_first_stage_transport_delta"
            ]
        ),
    )
    settlement_set_sha256 = _sha({
        "outcome_sha256s": sorted(
            outcome.sha256 for outcome in all_outcomes
        ),
    })
    promoted_family = compile_object_response_family(
        all_outcomes,
        source_result_ref=(
            f"{_relative_ref(output_dir)}/settlements"
        ),
        source_result_sha256=settlement_set_sha256,
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
    mean_delta = sum(composite_deltas) / len(composite_deltas)
    wins = sum(value > 0.0 for value in composite_deltas)
    criterion = bool(
        estimate.status == "identified"
        and estimate.first_stage_transport_delta >= 1.0
        and estimate.offer_supported_transport_rate == 1.0
        and estimate.withhold_supported_transport_rate == 0.0
        and task_delta >= 0.0
        and mean_delta > 0.0
        and wins >= 1
        and len(promoted_family.responses) == 1
        and promoted_family.responses[0].admissible
    )
    result_core = {
        "schema": SCHEMA,
        "kind": "experiment_result",
        "status": "live_complete",
        "verdict": "supported" if criterion else "rejected",
        "experiment_sha256": experiment_sha256,
        "manifest_ref": _relative_ref(manifest_path),
        "positive_object_transport": positive_transport.to_receipt(),
        "intervention_revision_transport": (
            intervention_transport.to_receipt()
        ),
        "placebo_intervention_revision_transport": (
            placebo_intervention_transport.to_receipt()
        ),
        "negative_object_transport": negative_transport.to_receipt(),
        "negative_branch_controller_contact": False,
        "preflight_transport_candidate": (
            preflight_candidate.to_receipt()
        ),
        "pairs": pair_rows,
        "target_fiber_estimate": estimate.to_receipt(),
        "promoted_target_response_family": (
            promoted_family.to_receipt()
        ),
        "aggregate": {
            "pair_count": len(pair_rows),
            "positive_candidate_commuting_rate": 1.0,
            "negative_transport_refusal_rate": 1.0,
            "all_blind_basin_transport_rate": 1.0,
            "offer_total_task_score_minus_withhold": task_delta,
            "offer_composite_wins": wins,
            "mean_offer_minus_withhold_composite": mean_delta,
            "prefix_primitive_action_cost_per_arm": len(
                positive_spec["actions"]
            ),
            "post_prefix_primitive_action_cost_per_arm": float(
                args.budget
            ),
            "total_primitive_action_cost_per_arm": (
                len(positive_spec["actions"]) + args.budget
            ),
            "rendered_utf8_bytes_per_intervention": rendered_bytes,
            "proposal_inferences_before_post_prefix_action": 2,
        },
        "claim_boundary": list(spec["claim_boundary"]),
    }
    result = {**result_core, "sha256": _sha(result_core)}
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
    base = (
        REPO
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="ls20")
    parser.add_argument("--pairs", type=int, default=2)
    parser.add_argument("--budget", type=int, default=20)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument(
        "--reasoning-effort",
        choices=("high", "xhigh", "max"),
        default="xhigh",
    )
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument(
        "--seed",
        default="h95-response-transport-square-20260730",
    )
    parser.add_argument(
        "--source-result",
        default=str(base / "h86_level_boundary_microsleep_result.json"),
    )
    parser.add_argument(
        "--spec",
        default=str(base / "h95_response_transport_square_spec.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(base / "h95_response_transport_square"),
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--verify-result-only", action="store_true")
    args = parser.parse_args()
    if args.pairs <= 0 or args.budget <= 0:
        raise SystemExit("pair count and budget must be positive")
    if args.verify_result_only:
        replay = verify_saved_result(
            Path(args.output_dir).resolve() / "result.json"
        )
        print(json.dumps(replay, indent=2, sort_keys=True))
        return 0
    bootstrap_dotenv_from_repo_root()
    result = run_experiment(args)
    if args.preflight_only:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    print(json.dumps({
        "result_path": _relative_ref(
            Path(args.output_dir).resolve() / "result.json"
        ),
        "verdict": result["verdict"],
        "aggregate": result["aggregate"],
        "target_fiber_estimate": result["target_fiber_estimate"],
        "promoted_target_response_family_sha256": (
            result["promoted_target_response_family"]["sha256"]
        ),
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
