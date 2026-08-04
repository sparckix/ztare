#!/usr/bin/env python3
"""Prospectively spend an object-basin response family on fresh controllers.

H93 supplied randomized, externally settled evidence for one typed blind-plan
basin.  This probe freezes that response family and compares its prospective
admission action with H90's scalar outcome-trained allocator.  Each controller
commits a blind catalog-handle plan before either policy selects or delivers an
intervention.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[3]
CONTROL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(CONTROL))

import arc3_instrumented_proposal_probe as proposal_probe  # noqa: E402
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
    _initial_observation,
    _relative_ref,
)
from arc3_responses_agent_probe import (  # noqa: E402
    _resolve_game_id,
    _sha_payload,
    _sleep_memory_scope,
)
from ztare.common.decision_intervention_market import (  # noqa: E402
    allocate_decision_interventions,
)
from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.object_basin_response import (  # noqa: E402
    ObjectResponseFamily,
    compile_object_admission,
    compile_object_response_family,
    object_outcome_from_receipt,
    object_transition_from_receipt,
)
from ztare.common.object_linked_judgment import (  # noqa: E402
    ObjectReferenceAuthority,
    ObjectRolePathContract,
)
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    select_sparse_memories,
    wake_sleep_credit_state_from_receipt,
)
from ztare.worldmodel.observation_object_catalog import (  # noqa: E402
    compile_catalog_from_observation,
    compile_catalog_presentation,
    selector_refs,
)


SCHEMA = "ztare-arc3-prospective-response-family-admission-v1"


def _sha(payload: Mapping[str, Any]) -> str:
    return proposal_probe._sha(payload)


def _verify_receipt_sha(receipt: Mapping[str, Any], name: str) -> None:
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


def _verify_result(
    path: Path,
    *,
    expected_file_sha256: str,
    expected_embedded_sha256: str,
) -> dict[str, Any]:
    if _file_sha256(path) != expected_file_sha256:
        raise ValueError(f"source result file drifted: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    core = dict(result)
    claimed = str(core.pop("sha256", ""))
    if (
        not claimed
        or claimed != expected_embedded_sha256
        or _sha(core) != claimed
    ):
        raise ValueError(f"source result receipt drifted: {path}")
    return result


def verify_saved_result(result_path: Path) -> dict[str, Any]:
    """Replay H94's saved identity, transition, and settlement receipts."""

    path = result_path.resolve()
    result = json.loads(path.read_text(encoding="utf-8"))
    _verify_receipt_sha(result, "H94 result")
    if result.get("schema") != SCHEMA:
        raise ValueError("saved result has the wrong schema")
    manifest_path = _repo_ref_path(str(result["manifest_ref"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        str(manifest["experiment_sha256"])
        != str(result["experiment_sha256"])
    ):
        raise ValueError("result crossed experiment manifest identity")
    if manifest["response_family"] != result["response_family"]:
        raise ValueError("result response family drifted from manifest")
    _verify_receipt_sha(result["response_family"], "response family")
    for index, response in enumerate(
        result["response_family"]["responses"]
    ):
        _verify_receipt_sha(response, f"response family row {index}")
    for name in (
        "training_verification",
        "scalar_comparator_verification",
    ):
        _verify_receipt_sha(result[name], name)
        if result[name] != manifest[name]:
            raise ValueError(f"{name} drifted from manifest")

    training = result["training_verification"]
    training_result_path = _repo_ref_path(training["result_ref"])
    training_manifest_path = _repo_ref_path(training["manifest_ref"])
    if _file_sha256(training_result_path) != str(
        training["result_file_sha256"]
    ):
        raise ValueError("training result file drifted")
    if _file_sha256(training_manifest_path) != str(
        training["manifest_file_sha256"]
    ):
        raise ValueError("training manifest file drifted")
    scalar = result["scalar_comparator_verification"]
    scalar_result_path = _repo_ref_path(scalar["result_ref"])
    if _file_sha256(scalar_result_path) != str(
        scalar["result_file_sha256"]
    ):
        raise ValueError("scalar comparator result file drifted")

    task_deltas = []
    composite_deltas = []
    response_admissions = 0
    scalar_admissions = 0
    trained_basin = str(
        result["response_family"]["responses"][0][
            "pre_basin_sha256"
        ]
    )
    for pair in result["pairs"]:
        pair_index = int(pair["pair_index"])
        policies = (
            ("response_policy", "offer"),
            ("scalar_policy", "withhold"),
        )
        policy_values = {}
        for policy_name, assignment in policies:
            policy = pair[policy_name]
            transition = object_transition_from_receipt(
                policy["transition"]
            )
            outcome = object_outcome_from_receipt(
                policy["outcome"],
                transition=transition,
            )
            metrics = policy["metrics"]
            expected_external = (
                0.8 * float(metrics["task_score"])
                + 0.2 * float(metrics["efficiency_score"])
            )
            if outcome.external_value != expected_external:
                raise ValueError("saved external value drifted")
            condition_id = str(policy["condition_id"])
            arm_path = (
                path.parent
                / "arms"
                / (
                    f"pair_{pair_index:02d}_{assignment}_"
                    f"{condition_id}.json"
                )
            )
            arm = json.loads(arm_path.read_text(encoding="utf-8"))
            if arm["transition"] != policy["transition"]:
                raise ValueError("arm transition drifted from result")
            checkpoint = arm["admission_decision_checkpoint"]
            if checkpoint["decision"] != policy["admission"]:
                raise ValueError("admission checkpoint drifted")
            checkpoint_path = _repo_ref_path(checkpoint["ref"])
            if (
                int(checkpoint["count"]) != 1
                or _file_sha256(checkpoint_path)
                != str(checkpoint["sha256"])
            ):
                raise ValueError("admission checkpoint file drifted")
            raw = arm["raw_proposal_checkpoint"]
            raw_path = _repo_ref_path(raw["ref"])
            if (
                int(raw["count"]) != 2
                or _file_sha256(raw_path) != str(raw["sha256"])
            ):
                raise ValueError("raw proposal checkpoint file drifted")
            _verify_receipt_sha(
                policy["admission"],
                f"{policy_name} admission",
            )
            if assignment == "offer":
                if (
                    policy["admission"]["action"] != "offer"
                    or policy["admission"]["pre_basin_sha256"]
                    != trained_basin
                ):
                    raise ValueError("response admission replay failed")
                response_admissions += 1
            else:
                if (
                    policy["admission"]["action"] != "withhold"
                    or policy["admission"][
                        "selected_intervention_revision_sha256"
                    ]
                    != manifest["placebo_proposal"][
                        "intervention_revision_sha256"
                    ]
                ):
                    raise ValueError("scalar admission replay failed")
                scalar_admissions += 1
            policy_values[assignment] = outcome.net_external_value
        task_delta = (
            float(
                pair["response_policy"]["metrics"]["task_score"]
            )
            - float(pair["scalar_policy"]["metrics"]["task_score"])
        )
        composite_delta = (
            policy_values["offer"] - policy_values["withhold"]
        )
        if task_delta != float(pair["response_task_minus_scalar"]):
            raise ValueError("pair task delta drifted")
        if composite_delta != float(
            pair["response_composite_minus_scalar"]
        ):
            raise ValueError("pair composite delta drifted")
        task_deltas.append(task_delta)
        composite_deltas.append(composite_delta)

    aggregate = result["aggregate"]
    if sum(task_deltas) != float(
        aggregate["response_total_task_score_minus_scalar"]
    ):
        raise ValueError("aggregate task delta drifted")
    if (
        sum(composite_deltas) / len(composite_deltas)
        != float(aggregate["mean_response_minus_scalar_composite"])
    ):
        raise ValueError("aggregate composite mean drifted")
    if sum(value > 0.0 for value in composite_deltas) != int(
        aggregate["response_composite_wins"]
    ):
        raise ValueError("aggregate win count drifted")
    return {
        "status": "offline_replay_verified",
        "result_ref": _relative_ref(path),
        "result_file_sha256": _file_sha256(path),
        "result_sha256": result["sha256"],
        "manifest_file_sha256": _file_sha256(manifest_path),
        "pair_count": len(result["pairs"]),
        "response_admission_count": response_admissions,
        "scalar_admission_count": scalar_admissions,
        "mean_response_minus_scalar_composite": (
            aggregate["mean_response_minus_scalar_composite"]
        ),
    }


def _training_family(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
) -> tuple[ObjectResponseFamily, dict[str, Any]]:
    source = dict(spec["training_source"])
    result_path = (spec_path.parent / str(source["ref"])).resolve()
    result = _verify_result(
        result_path,
        expected_file_sha256=str(source["file_sha256"]),
        expected_embedded_sha256=str(source["embedded_sha256"]),
    )
    manifest_path = result_path.parent / "manifest.json"
    if _file_sha256(manifest_path) != str(
        source["manifest_file_sha256"]
    ):
        raise ValueError("H93 source manifest drifted")
    allowed_pairs = tuple(
        int(value) for value in source["allowed_training_pairs"]
    )
    pairs = tuple(
        row for row in result["pairs"]
        if int(row["pair_index"]) in allowed_pairs
    )
    if (
        len(pairs) != len(allowed_pairs)
        or tuple(int(row["pair_index"]) for row in pairs)
        != allowed_pairs
    ):
        raise ValueError("H93 training-pair membership drifted")
    outcomes = []
    for pair in pairs:
        for assignment in ("offer", "withhold"):
            transition = object_transition_from_receipt(
                pair[f"{assignment}_transition"]
            )
            outcome = object_outcome_from_receipt(
                pair[f"{assignment}_outcome"],
                transition=transition,
            )
            outcomes.append(outcome)
    compiler = dict(spec["response_family_compiler"])
    family = compile_object_response_family(
        outcomes,
        source_result_ref=_relative_ref(result_path),
        source_result_sha256=str(result["sha256"]),
        minimum_offer_count=int(compiler["minimum_offer_count"]),
        minimum_withhold_count=int(
            compiler["minimum_withhold_count"]
        ),
        minimum_first_stage_transport_delta=float(
            compiler["minimum_first_stage_transport_delta"]
        ),
        minimum_intent_to_treat_net_delta=float(
            compiler["minimum_intent_to_treat_net_delta"]
        ),
    )
    receipt = {
        "kind": "h93_training_source_verification",
        "result_ref": _relative_ref(result_path),
        "result_file_sha256": _file_sha256(result_path),
        "result_sha256": result["sha256"],
        "manifest_ref": _relative_ref(manifest_path),
        "manifest_file_sha256": _file_sha256(manifest_path),
        "training_pair_indices": list(allowed_pairs),
        "training_outcome_sha256s": sorted(
            outcome.sha256 for outcome in outcomes
        ),
        "response_family_sha256": family.sha256,
    }
    return family, {**receipt, "sha256": _sha(receipt)}


def _scalar_comparator(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
    scope,
    proposals,
    rendered_bytes: int,
) -> tuple[Any, dict[str, Any]]:
    source = dict(spec["scalar_comparator_source"])
    result_path = (spec_path.parent / str(source["ref"])).resolve()
    result = _verify_result(
        result_path,
        expected_file_sha256=str(source["file_sha256"]),
        expected_embedded_sha256=str(source["sha256"]),
    )
    state = wake_sleep_credit_state_from_receipt(
        result["final_credit_state"]
    )
    state_receipt = state.to_receipt()
    if str(state_receipt["sha256"]) != str(
        source["final_credit_state_sha256"]
    ):
        raise ValueError("H90 final scalar credit state drifted")
    allocation = allocate_decision_interventions(
        state,
        tuple(proposals),
        scope=scope,
        max_items=1,
        max_prompt_tokens=rendered_bytes,
        minimum_score=-2.0,
    )
    selected = allocation.selected_proposal_revision_sha256s
    if len(selected) != 1:
        raise ValueError(
            "H90 comparator did not select one intervention"
        )
    receipt = {
        "kind": "h90_scalar_comparator_verification",
        "result_ref": _relative_ref(result_path),
        "result_file_sha256": _file_sha256(result_path),
        "result_sha256": result["sha256"],
        "final_credit_state_sha256": state_receipt["sha256"],
        "allocation": allocation.to_receipt(),
        "selected_intervention_revision_sha256": selected[0],
    }
    return allocation, {**receipt, "sha256": _sha(receipt)}


def _authorization(
    *,
    proposal,
    scope,
    rendered_bytes: int,
    controller_instance_sha256: str,
    observation_sha256: str,
    decision_ref: str,
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
        compatibility_transport_sha256=_sha({
            "source_observation": (
                proposal.acquisition_provenance.observation_sha256
            ),
            "target_scope": scope.sha256,
            "preserved": [
                "task",
                "controller_class",
                "choice_set",
                "action_vocabulary",
            ],
        }),
    )
    _, consumption = consume_recall_once(
        decision,
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=observation_sha256,
    )
    return {
        "recall": recall,
        "decision": decision,
        "consumption": consumption,
    }


def _scalar_admission_receipt(
    *,
    pre_proposal,
    allocation,
    comparator_receipt: Mapping[str, Any],
    target_revision_sha256: str,
) -> dict[str, Any]:
    selected = allocation.selected_proposal_revision_sha256s
    if len(selected) != 1:
        raise ValueError("scalar allocation is not singular")
    payload = {
        "schema": SCHEMA,
        "kind": "scalar_comparator_admission_decision",
        "comparator_verification_sha256": comparator_receipt["sha256"],
        "allocation_sha256": allocation.to_receipt()["sha256"],
        "blind_proposal_sha256": pre_proposal.sha256,
        "selected_intervention_revision_sha256": selected[0],
        "target_intervention_revision_sha256": target_revision_sha256,
        "action": (
            "offer"
            if selected[0] == target_revision_sha256
            else "withhold"
        ),
        "reason": "rehydrated_scalar_outcome_allocator",
    }
    return {**payload, "sha256": _sha(payload)}


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    source_path = Path(args.source_result).resolve()
    spec_path = Path(args.spec).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema") != (
        "ztare-arc3-prospective-response-family-admission-spec-v1"
    ):
        raise ValueError("wrong prospective response-family spec")

    loader_path = Path(
        "/private/tmp/ztare_h94_pairwise_loader_spec.json"
    )
    _atomic_json(loader_path, {
        "schema": spec["schema"],
        "left": spec["target_intervention"],
        "right": spec["placebo_intervention"],
    })
    source_meta, target_condition, placebo_condition, turns = _load_source(
        source_path,
        loader_path,
    )
    source_meta["spec_path"] = _relative_ref(spec_path)
    source_meta["spec_sha256"] = _file_sha256(spec_path)
    target_condition["condition_id"] = str(
        spec["target_intervention"]["condition_id"]
    )
    placebo_condition["condition_id"] = str(
        spec["placebo_intervention"]["condition_id"]
    )

    game_id = _resolve_game_id(args.game)
    initial_observation, action_arity = _initial_observation(game_id=game_id)
    catalog = compile_catalog_from_observation(initial_observation)
    presentation = compile_catalog_presentation(catalog)
    scope = _sleep_memory_scope(
        game_id=game_id,
        model_id=args.model,
        reasoning_effort=args.reasoning_effort,
        boundary_observation=initial_observation,
        action_arity=action_arity,
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
    if rendered_bytes != int(
        spec["costs"]["presented_bytes_per_selected_intervention"]
    ):
        raise ValueError("H94 rendered intervention cost drifted")
    if args.budget != int(spec["costs"]["primitive_actions_per_arm"]):
        raise ValueError("H94 primitive action cost drifted")
    target_proposal = _proposal(
        condition=target_condition,
        digest=target_digest,
        provenance=target_provenance,
        scope=scope,
        budget=args.budget,
        rendered_bytes=rendered_bytes,
    )
    placebo_proposal = _proposal(
        condition=placebo_condition,
        digest=placebo_digest,
        provenance=placebo_provenance,
        scope=scope,
        budget=args.budget,
        rendered_bytes=rendered_bytes,
    )
    if target_proposal.intervention_revision_sha256 == (
        placebo_proposal.intervention_revision_sha256
    ):
        raise ValueError("target and placebo intervention identities merged")

    contract_spec = dict(spec["object_role_contract"])
    controlled = catalog.resolve_selector(
        contract_spec["controlled_object_selector"]
    )
    required_waypoints = selector_refs(
        catalog,
        contract_spec["required_waypoint_selectors"],
    )
    forbidden_controlled = selector_refs(
        catalog,
        contract_spec["forbidden_control_selectors"],
    )
    authority = ObjectReferenceAuthority(
        observation_sha256=initial_observation["sha256"],
        catalog_sha256=catalog.sha256,
        object_refs=catalog.object_refs,
    )
    contract = ObjectRolePathContract(
        scope=scope,
        catalog_sha256=catalog.sha256,
        intervention_revision_sha256=(
            target_proposal.intervention_revision_sha256
        ),
        required_controlled_object_ref=controlled.object_ref,
        required_waypoint_refs=required_waypoints,
        forbidden_controlled_object_refs=forbidden_controlled,
        evidence_refs=tuple(contract_spec["evidence_refs"]),
    )

    family, training_verification = _training_family(
        spec=spec,
        spec_path=spec_path,
    )
    if (
        family.scope_sha256 != scope.sha256
        or family.contract_sha256 != contract.sha256
        or family.intervention_revision_sha256
        != target_proposal.intervention_revision_sha256
        or family.catalog_sha256 != catalog.sha256
    ):
        raise ValueError(
            "H93 family cannot govern the current decision identity"
        )
    if (
        len(family.responses) != 1
        or not family.responses[0].admissible
    ):
        raise ValueError("H93 did not compile one admissible response")

    scalar_allocation, scalar_verification = _scalar_comparator(
        spec=spec,
        spec_path=spec_path,
        scope=scope,
        proposals=(target_proposal, placebo_proposal),
        rendered_bytes=rendered_bytes,
    )
    selected_scalar = (
        scalar_allocation.selected_proposal_revision_sha256s[0]
    )
    if selected_scalar != (
        placebo_proposal.intervention_revision_sha256
    ):
        raise ValueError("H90 scalar comparator no longer selects placebo")

    pair_count = int(args.pairs)
    if pair_count != int(
        spec["prospective_policies"]["pair_count"]
    ):
        raise ValueError("H94 pair count drifted")
    orders = [
        ["offer", "withhold"] if index % 2 == 0
        else ["withhold", "offer"]
        for index in range(pair_count)
    ]
    manifest_core = {
        "schema": SCHEMA,
        "kind": "experiment_manifest",
        "game_id": game_id,
        "pairs": pair_count,
        "budget_per_arm": args.budget,
        "proposal_inferences_before_first_action": 2,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "seed": args.seed,
        "order_mode": "alternating",
        "arm_orders": orders,
        "initial_observation": initial_observation,
        "scope": scope.to_receipt(),
        "source": source_meta,
        "spec_ref": _relative_ref(spec_path),
        "spec_sha256": _file_sha256(spec_path),
        "rendered_utf8_bytes_per_condition": rendered_bytes,
        "target_digest_sha256": _sha_payload(target_digest),
        "placebo_digest_sha256": _sha_payload(placebo_digest),
        "target_proposal": target_proposal.to_receipt(),
        "placebo_proposal": placebo_proposal.to_receipt(),
        "object_catalog": catalog.to_receipt(),
        "object_presentation": presentation.to_receipt(),
        "object_authority_sha256": authority.sha256,
        "target_contract": contract.to_receipt(),
        "response_family": family.to_receipt(),
        "training_verification": training_verification,
        "scalar_comparator_verification": scalar_verification,
        "policy_assignment": {
            "offer": "h93_response_family_admission",
            "withhold": "h90_final_scalar_credit_selector",
        },
        "primary_score": {
            "task_weight": 0.8,
            "efficiency_weight": 0.2,
        },
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
            raise RuntimeError("existing H94 manifest drifted")
    else:
        _atomic_json(manifest_path, manifest)
    if getattr(args, "preflight_only", False):
        return {
            "status": "preflight_complete",
            "manifest_ref": _relative_ref(manifest_path),
            "experiment_sha256": experiment_sha256,
            "response_family_sha256": family.sha256,
            "scalar_selected_intervention_revision_sha256": (
                selected_scalar
            ),
        }

    conditions = {
        "offer": (
            target_condition,
            target_digest,
            target_proposal,
        ),
        "withhold": (
            placebo_condition,
            placebo_digest,
            placebo_proposal,
        ),
    }
    pair_rows = []
    for pair_index, order in enumerate(orders, start=1):
        stratum = proposal_probe._stratum(
            scope=scope,
            game_id=game_id,
            observation_sha256=initial_observation["sha256"],
            budget=args.budget,
            seed=args.seed,
            pair_index=pair_index,
        )
        authorizations = {}
        for assignment in ("offer", "withhold"):
            _condition, _digest, intervention = conditions[assignment]
            controller_instance = _controller_instance_sha256(
                experiment_sha256=experiment_sha256,
                pair_index=pair_index,
                assignment=assignment,
            )
            authorizations[assignment] = {
                **_authorization(
                    proposal=intervention,
                    scope=scope,
                    rendered_bytes=rendered_bytes,
                    controller_instance_sha256=controller_instance,
                    observation_sha256=initial_observation["sha256"],
                    decision_ref=(
                        f"pair-{pair_index:02d}:"
                        f"{assignment}:decision-0"
                    ),
                ),
                "controller_instance": controller_instance,
            }

        def response_selector(pre_proposal):
            return compile_object_admission(
                pre_proposal,
                contract=contract,
                authority=authority,
                family=family,
            )

        def scalar_selector(pre_proposal):
            return _scalar_admission_receipt(
                pre_proposal=pre_proposal,
                allocation=scalar_allocation,
                comparator_receipt=scalar_verification,
                target_revision_sha256=(
                    target_proposal.intervention_revision_sha256
                ),
            )

        selectors = {
            "offer": response_selector,
            "withhold": scalar_selector,
        }
        arms = {}
        for assignment in order:
            condition, digest, _intervention = conditions[assignment]
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
                    initial_observation["sha256"]
                ),
                action_arity=action_arity,
                digest=digest,
                consumption_decision=auth["decision"],
                consumption_receipt=auth["consumption"],
                target_contract=contract,
                controller_instance_sha256=(
                    auth["controller_instance"]
                ),
                stratum_sha256=stratum.sha256,
                feature_adapter=None,
                object_catalog=catalog,
                object_authority=authority,
                object_presentation=presentation,
                admission_selector=selectors[assignment],
            )

        outcomes = {}
        transition_rows = {}
        for assignment in ("offer", "withhold"):
            condition = conditions[assignment][0]
            arm_path = (
                output_dir
                / "arms"
                / (
                    f"pair_{pair_index:02d}_{assignment}_"
                    f"{condition['condition_id']}.json"
                )
            )
            transition = object_transition_from_receipt(
                arms[assignment]["transition"]
            )
            transition_rows[assignment] = transition
            outcomes[assignment] = (
                proposal_probe._instrumented_outcome(
                    arms[assignment],
                    transition=transition,
                    arm_path=arm_path,
                )
            )

        response_admission = arms["offer"][
            "admission_decision_checkpoint"
        ]["decision"]
        scalar_admission = arms["withhold"][
            "admission_decision_checkpoint"
        ]["decision"]
        trained_basin = family.responses[0].pre_basin_sha256
        if (
            response_admission["action"] != "offer"
            or response_admission["family_sha256"] != family.sha256
            or response_admission["pre_basin_sha256"] != trained_basin
        ):
            raise RuntimeError(
                "response policy did not offer through the trained basin"
            )
        if (
            scalar_admission["action"] != "withhold"
            or scalar_admission[
                "selected_intervention_revision_sha256"
            ] != placebo_proposal.intervention_revision_sha256
        ):
            raise RuntimeError(
                "scalar comparator did not select the frozen placebo"
            )
        response_value = outcomes["offer"].net_external_value
        scalar_value = outcomes["withhold"].net_external_value
        pair_row = {
            "pair_index": pair_index,
            "arm_order": order,
            "stratum": stratum.to_receipt(),
            "response_policy": {
                "assignment": "offer",
                "condition_id": target_condition["condition_id"],
                "admission": response_admission,
                "transition": transition_rows["offer"].to_receipt(),
                "outcome": outcomes["offer"].to_receipt(),
                "metrics": arms["offer"]["metrics"],
            },
            "scalar_policy": {
                "assignment": "withhold",
                "condition_id": placebo_condition["condition_id"],
                "admission": scalar_admission,
                "transition": transition_rows["withhold"].to_receipt(),
                "outcome": outcomes["withhold"].to_receipt(),
                "metrics": arms["withhold"]["metrics"],
            },
            "response_task_minus_scalar": (
                float(arms["offer"]["metrics"]["task_score"])
                - float(arms["withhold"]["metrics"]["task_score"])
            ),
            "response_composite_minus_scalar": (
                response_value - scalar_value
            ),
        }
        pair_rows.append(pair_row)
        _atomic_json(
            output_dir
            / "settlements"
            / f"pair_{pair_index:02d}.json",
            pair_row,
        )

    task_delta = sum(
        float(row["response_task_minus_scalar"])
        for row in pair_rows
    )
    composite_deltas = tuple(
        float(row["response_composite_minus_scalar"])
        for row in pair_rows
    )
    mean_delta = sum(composite_deltas) / len(composite_deltas)
    wins = sum(value > 0.0 for value in composite_deltas)
    criterion = bool(
        task_delta >= float(
            spec["predictions"][
                "minimum_response_policy_task_delta"
            ]
        )
        and mean_delta > float(
            spec["predictions"][
                "minimum_mean_response_policy_composite_delta"
            ]
        )
        and wins >= int(
            spec["predictions"][
                "minimum_response_policy_composite_wins"
            ]
        )
    )
    result_core = {
        "schema": SCHEMA,
        "kind": "experiment_result",
        "status": "live_complete",
        "verdict": "supported" if criterion else "rejected",
        "experiment_sha256": experiment_sha256,
        "manifest_ref": _relative_ref(manifest_path),
        "training_verification": training_verification,
        "response_family": family.to_receipt(),
        "scalar_comparator_verification": scalar_verification,
        "pairs": pair_rows,
        "aggregate": {
            "pair_count": len(pair_rows),
            "response_policy_target_selection_rate": 1.0,
            "scalar_policy_placebo_selection_rate": 1.0,
            "response_policy_exact_trained_basin_rate": 1.0,
            "admission_before_intervention_checkpoint_rate": 1.0,
            "response_total_task_score_minus_scalar": task_delta,
            "response_composite_wins": wins,
            "mean_response_minus_scalar_composite": mean_delta,
            "rendered_utf8_bytes_per_selected_intervention": (
                rendered_bytes
            ),
            "proposal_inferences_before_first_action": 2,
            "primitive_action_cost_per_arm": float(args.budget),
            "h94_outcomes_consumed_by_selector_count": 0,
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
        default="h94-prospective-response-family-admission-20260730",
    )
    parser.add_argument(
        "--source-result",
        default=str(base / "h86_level_boundary_microsleep_result.json"),
    )
    parser.add_argument(
        "--spec",
        default=str(
            base / "h94_prospective_response_family_admission_spec.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            base / "h94_prospective_response_family_admission"
        ),
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--verify-result-only", action="store_true")
    args = parser.parse_args()
    if args.pairs <= 0:
        raise SystemExit("--pairs must be positive")
    if args.budget <= 0:
        raise SystemExit("--budget must be positive")
    if args.verify_result_only:
        print(json.dumps(
            verify_saved_result(
                Path(args.output_dir).resolve() / "result.json"
            ),
            indent=2,
            sort_keys=True,
        ))
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
        "response_family_sha256": (
            result["response_family"]["sha256"]
        ),
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
