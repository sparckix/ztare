#!/usr/bin/env python3
"""Test descendant response transport through appearance lineage on ARC."""

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
import arc3_response_transport_square_probe as h95  # noqa: E402
from arc3_paired_recall_probe import (  # noqa: E402
    _atomic_json,
    _controller_instance_sha256,
    _file_sha256,
    _relative_ref,
)
from arc3_responses_agent_probe import (  # noqa: E402
    _resolve_game_id,
    _sleep_memory_scope,
)
from ztare.common.decision_intervention_market import (  # noqa: E402
    decision_intervention_proposal_from_receipt,
)
from ztare.common.instrumented_proposal_plasticity import (  # noqa: E402
    InstrumentedProposalOutcome,
    estimate_instrumented_plasticity,
)
from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.object_basin_response import (  # noqa: E402
    compile_object_response_family,
    object_contract_from_receipt,
    object_proposal_from_receipt,
    object_response_family_from_receipt,
    object_transition_from_receipt,
)
from ztare.common.object_lineage_transport import (  # noqa: E402
    compile_causal_object_lineage_transport,
)
from ztare.common.object_linked_judgment import (  # noqa: E402
    ObjectReferenceAuthority,
)
from ztare.common.object_response_transport import (  # noqa: E402
    compile_intervention_revision_transport,
    compile_response_transport_candidate,
    compile_unique_type_object_transport,
    transport_object_role_contract,
)
from ztare.worldmodel.observation_object_catalog import (  # noqa: E402
    compile_catalog_from_observation,
    compile_catalog_presentation,
)


SCHEMA = "ztare-arc3-causal-object-lineage-v1"


def _sha(payload: Mapping[str, Any]) -> str:
    return proposal_probe._sha(payload)


def _load_result(
    path: Path,
    *,
    expected_file_sha256: str,
    expected_embedded_sha256: str,
) -> dict[str, Any]:
    if _file_sha256(path) != expected_file_sha256:
        raise ValueError("H96 source result file drifted")
    result = json.loads(path.read_text(encoding="utf-8"))
    core = dict(result)
    claimed = str(core.pop("sha256", ""))
    if (
        claimed != expected_embedded_sha256
        or _sha(core) != claimed
    ):
        raise ValueError("H96 source result receipt drifted")
    return result


def _source_evidence(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
) -> dict[str, Any]:
    source_spec = dict(spec["source_response"])
    result_path = (
        spec_path.parent / str(source_spec["result_ref"])
    ).resolve()
    result = _load_result(
        result_path,
        expected_file_sha256=str(
            source_spec["result_file_sha256"]
        ),
        expected_embedded_sha256=str(
            source_spec["result_embedded_sha256"]
        ),
    )
    replay = h95.verify_saved_result(result_path)
    manifest_path = h95._repo_ref_path(str(result["manifest_ref"]))
    if _file_sha256(manifest_path) != str(
        source_spec["manifest_file_sha256"]
    ):
        raise ValueError("H96 source manifest drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    family = object_response_family_from_receipt(
        result["promoted_target_response_family"]
    )
    if family.sha256 != str(source_spec["family_sha256"]):
        raise ValueError("H96 source family drifted")
    matches = [
        row for row in family.responses
        if row.sha256 == str(source_spec["response_sha256"])
    ]
    if len(matches) != 1:
        raise ValueError("H96 source response drifted")
    response = matches[0]
    contract = object_contract_from_receipt(
        manifest["target_contract"]
    )
    if (
        contract.sha256 != str(source_spec["contract_sha256"])
        or contract.scope.sha256 != str(source_spec["scope_sha256"])
        or contract.catalog_sha256
        != str(source_spec["catalog_sha256"])
        or contract.intervention_revision_sha256
        != str(source_spec["intervention_revision_sha256"])
    ):
        raise ValueError("H96 source contract authority drifted")

    witness_spec = dict(spec["source_response_witness"])
    witness_path = (
        spec_path.parent / str(witness_spec["arm_ref"])
    ).resolve()
    if _file_sha256(witness_path) != str(
        witness_spec["arm_file_sha256"]
    ):
        raise ValueError("H96 source witness file drifted")
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    instrumented = witness["probe"]["turns"][0][
        "instrumented_proposal"
    ]
    pre = object_proposal_from_receipt(
        instrumented["pre_proposal"]
    )
    post = object_proposal_from_receipt(
        instrumented["post_proposal"]
    )
    if (
        pre.sha256 != str(witness_spec["pre_proposal_sha256"])
        or post.sha256
        != str(witness_spec["post_proposal_sha256"])
    ):
        raise ValueError("H96 source proposal witness drifted")
    return {
        "result_path": result_path,
        "result": result,
        "result_replay": replay,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "family": family,
        "response": response,
        "contract": contract,
        "pre_proposal": pre,
        "post_proposal": post,
        "witness_path": witness_path,
        "intervention": (
            decision_intervention_proposal_from_receipt(
                manifest["target_proposal"]
            )
        ),
        "placebo_intervention": (
            decision_intervention_proposal_from_receipt(
                manifest["placebo_proposal"]
            )
        ),
    }


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema") != "ztare-arc3-causal-object-lineage-spec-v1":
        raise ValueError("wrong H96 experiment spec")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    memory_source_path = Path(args.memory_source_result).resolve()
    source = _source_evidence(spec=spec, spec_path=spec_path)
    source_contract = source["contract"]
    source_pre = source["pre_proposal"]
    source_post = source["post_proposal"]

    path_spec = dict(spec["descendant_path"])
    game_id = _resolve_game_id(args.game)
    prefix = h95._replay_prefix(
        game_id=game_id,
        actions=path_spec["actions_from_reset"],
    )
    catalogs = tuple(
        compile_catalog_from_observation(observation)
        for observation in prefix["observations"]
    )
    source_index = int(path_spec["source_observation_index"])
    source_observation = prefix["observations"][source_index]
    endpoint_observation = prefix["final_observation"]
    source_catalog = catalogs[source_index]
    endpoint_catalog = catalogs[-1]
    for observed, expected, name in (
        (
            source_observation["sha256"],
            path_spec["expected_source_observation_sha256"],
            "source observation",
        ),
        (
            source_catalog.sha256,
            path_spec["expected_source_catalog_sha256"],
            "source catalog",
        ),
        (
            endpoint_observation["sha256"],
            path_spec["expected_endpoint_observation_sha256"],
            "endpoint observation",
        ),
        (
            endpoint_catalog.sha256,
            path_spec["expected_endpoint_catalog_sha256"],
            "endpoint catalog",
        ),
    ):
        if str(observed) != str(expected):
            raise ValueError(f"H96 {name} drifted")
    if (
        source_contract.scope.context_sha256
        != source_observation["sha256"]
        or source_contract.catalog_sha256 != source_catalog.sha256
    ):
        raise ValueError("H96 source response crossed replay authority")

    required_refs = tuple(sorted({
        source_contract.required_controlled_object_ref,
        *source_contract.required_waypoint_refs,
        *source_contract.forbidden_controlled_object_refs,
        *source_pre.path,
        *source_post.path,
    }))
    static_transport = compile_unique_type_object_transport(
        source_catalog,
        endpoint_catalog,
        required_source_object_refs=required_refs,
        evidence_refs=(f"prefix:{prefix['sha256']}",),
    )
    if (
        static_transport.status != path_spec["static_direct_status"]
        or len(static_transport.object_ref_bindings)
        != int(path_spec["static_direct_binding_count"])
    ):
        raise ValueError("H96 static transport discriminator drifted")
    lineage = compile_causal_object_lineage_transport(
        catalogs[source_index:],
        prefix["transitions"][source_index:],
        required_source_object_refs=required_refs,
        evidence_refs=(
            f"prefix:{prefix['sha256']}",
            f"source_family:{source['family'].sha256}",
            f"source_witness:{_file_sha256(source['witness_path'])}",
        ),
        maximum_occlusion_frames=int(
            spec["lineage_compiler"]["maximum_occlusion_frames"]
        ),
    )
    if (
        lineage.status != "transportable"
        or len(lineage.traces)
        != int(
            spec["success_criterion"]["required_lineage_count"]
        )
        or lineage.appearance_revision_count < 1
        or lineage.bracketed_occlusion_count < 1
    ):
        raise ValueError("H96 causal lineage did not resolve")

    target_scope = _sleep_memory_scope(
        game_id=game_id,
        model_id=args.model,
        reasoning_effort=args.reasoning_effort,
        boundary_observation=endpoint_observation,
        action_arity=int(prefix["action_arity"]),
    )
    source_conditions = h95._condition_setup(
        source_result_path=memory_source_path,
        spec=spec,
        spec_path=spec_path,
        scope=source_contract.scope,
        budget=args.budget,
    )
    conditions = h95._condition_setup(
        source_result_path=memory_source_path,
        spec=spec,
        spec_path=spec_path,
        scope=target_scope,
        budget=args.budget,
    )
    if (
        source_conditions["target_proposal"].to_receipt()
        != source["intervention"].to_receipt()
        or source_conditions["placebo_proposal"].to_receipt()
        != source["placebo_intervention"].to_receipt()
    ):
        raise ValueError("H96 could not reconstruct source interventions")
    target_transport = compile_intervention_revision_transport(
        source["intervention"],
        conditions["target_proposal"],
        source_payload_invariant_sha256=(
            h95._payload_invariant_sha256(
                source_conditions["target_digest"]
            )
        ),
        target_payload_invariant_sha256=(
            h95._payload_invariant_sha256(
                conditions["target_digest"]
            )
        ),
        evidence_refs=(
            f"source_manifest:{_relative_ref(source['manifest_path'])}",
            f"lineage:{lineage.sha256}",
        ),
    )
    placebo_transport = compile_intervention_revision_transport(
        source["placebo_intervention"],
        conditions["placebo_proposal"],
        source_payload_invariant_sha256=(
            h95._payload_invariant_sha256(
                source_conditions["placebo_digest"]
            )
        ),
        target_payload_invariant_sha256=(
            h95._payload_invariant_sha256(
                conditions["placebo_digest"]
            )
        ),
        evidence_refs=(
            f"source_manifest:{_relative_ref(source['manifest_path'])}",
            f"lineage:{lineage.sha256}",
        ),
    )
    if (
        target_transport.status != "transportable"
        or placebo_transport.status != "transportable"
    ):
        raise ValueError("H96 intervention revision transport refused")
    target_contract = transport_object_role_contract(
        source_contract,
        target_scope=target_scope,
        target_catalog=endpoint_catalog,
        transport=lineage,
        intervention_transport=target_transport,
        evidence_refs=(
            *source_contract.evidence_refs,
            f"lineage:{lineage.sha256}",
            f"intervention_transport:{target_transport.sha256}",
        ),
    )
    mapped_pre = h95._mapped_witness_proposal(
        source_pre,
        target_scope=target_scope,
        target_catalog_sha256=endpoint_catalog.sha256,
        transport=lineage,
    )
    preflight_candidate = compile_response_transport_candidate(
        source_family=source["family"],
        source_response=source["response"],
        object_transport=lineage,
        intervention_transport=target_transport,
        source_contract=source_contract,
        target_contract=target_contract,
        source_pre_proposal=source_pre,
        source_post_proposal=source_post,
        target_pre_proposal=mapped_pre,
    )
    if (
        preflight_candidate.status != "candidate_commuting"
        or preflight_candidate.action != "explore_lineage"
    ):
        raise ValueError("H96 preflight lineage square did not commute")

    rendered_bytes = int(conditions["rendered_bytes"])
    costs = dict(spec["costs"])
    if (
        rendered_bytes
        != int(costs["presented_bytes_per_intervention"])
        or args.budget
        != int(costs["post_prefix_actions_per_arm"])
        or len(prefix["actions"])
        != int(costs["prefix_actions_per_arm"])
    ):
        raise ValueError("H96 frozen cost drifted")
    pair_count = int(args.pairs)
    if pair_count != int(spec["live_test"]["pair_count"]):
        raise ValueError("H96 pair count drifted")
    orders = [
        ["offer", "withhold"] if index % 2 == 0
        else ["withhold", "offer"]
        for index in range(pair_count)
    ]
    presentation = compile_catalog_presentation(endpoint_catalog)
    authority = ObjectReferenceAuthority(
        observation_sha256=endpoint_observation["sha256"],
        catalog_sha256=endpoint_catalog.sha256,
        object_refs=endpoint_catalog.object_refs,
    )
    manifest_core = {
        "schema": SCHEMA,
        "kind": "experiment_manifest",
        "game_id": game_id,
        "pairs": pair_count,
        "post_prefix_budget_per_arm": args.budget,
        "prefix_actions_per_arm": len(prefix["actions"]),
        "total_primitive_actions_per_arm": (
            args.budget + len(prefix["actions"])
        ),
        "proposal_inferences_before_post_prefix_action": 2,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "seed": args.seed,
        "arm_orders": orders,
        "source_verification": {
            "h95_result_replay": source["result_replay"],
            "h95_result_ref": _relative_ref(source["result_path"]),
            "h95_result_sha256": source["result"]["sha256"],
            "h95_witness_ref": _relative_ref(source["witness_path"]),
            "h95_witness_file_sha256": _file_sha256(
                source["witness_path"]
            ),
        },
        "source_response_family": source["family"].to_receipt(),
        "source_response": source["response"].to_receipt(),
        "source_contract": source_contract.to_receipt(),
        "source_intervention": source["intervention"].to_receipt(),
        "source_placebo_intervention": (
            source["placebo_intervention"].to_receipt()
        ),
        "source_pre_proposal": source_pre.to_receipt(),
        "source_post_proposal": source_post.to_receipt(),
        "descendant_prefix": prefix,
        "static_type_transport": static_transport.to_receipt(),
        "lineage_transport": lineage.to_receipt(),
        "intervention_revision_transport": (
            target_transport.to_receipt()
        ),
        "placebo_intervention_revision_transport": (
            placebo_transport.to_receipt()
        ),
        "target_scope": target_scope.to_receipt(),
        "target_catalog": endpoint_catalog.to_receipt(),
        "target_presentation": presentation.to_receipt(),
        "target_contract": target_contract.to_receipt(),
        "preflight_lineage_candidate": (
            preflight_candidate.to_receipt()
        ),
        "target_digest_sha256": h95._sha_payload(
            conditions["target_digest"]
        ),
        "placebo_digest_sha256": h95._sha_payload(
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
            raise RuntimeError("existing H96 manifest drifted")
    else:
        _atomic_json(manifest_path, manifest)
    if args.preflight_only:
        return {
            "status": "preflight_complete",
            "manifest_ref": _relative_ref(manifest_path),
            "experiment_sha256": experiment_sha256,
            "static_type_transport": static_transport.to_receipt(),
            "lineage_transport": lineage.to_receipt(),
            "preflight_candidate": preflight_candidate.to_receipt(),
        }

    arm_conditions = {
        "offer": (
            conditions["target_condition"],
            conditions["target_digest"],
            conditions["target_proposal"],
            target_transport,
        ),
        "withhold": (
            conditions["placebo_condition"],
            conditions["placebo_digest"],
            conditions["placebo_proposal"],
            placebo_transport,
        ),
    }
    if args.audit_interrupted:
        pair_index = 1
        audited_arms: dict[str, Any] = {}
        audited_candidates = {}
        audited_outcomes: list[InstrumentedProposalOutcome] = []
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
            if not arm_path.exists():
                raise FileNotFoundError(
                    f"missing interrupted H96 arm: {arm_path}"
                )
            arm = json.loads(arm_path.read_text(encoding="utf-8"))
            transition = object_transition_from_receipt(
                arm["transition"]
            )
            outcome = proposal_probe._instrumented_outcome(
                arm,
                transition=transition,
                arm_path=arm_path,
            )
            instrumented = arm["probe"]["turns"][0][
                "instrumented_proposal"
            ]
            blind = object_proposal_from_receipt(
                instrumented["pre_proposal"]
            )
            candidate = compile_response_transport_candidate(
                source_family=source["family"],
                source_response=source["response"],
                object_transport=lineage,
                intervention_transport=target_transport,
                source_contract=source_contract,
                target_contract=target_contract,
                source_pre_proposal=source_pre,
                source_post_proposal=source_post,
                target_pre_proposal=blind,
            )
            audited_candidates[assignment] = candidate
            audited_outcomes.append(outcome)
            audited_arms[assignment] = {
                "arm_ref": _relative_ref(arm_path),
                "arm_file_sha256": _file_sha256(arm_path),
                "metrics": dict(arm["metrics"]),
                "transition": transition.to_receipt(),
                "outcome": outcome.to_receipt(),
                "blind_proposal": blind.to_receipt(),
                "lineage_candidate": candidate.to_receipt(),
            }
        estimate = estimate_instrumented_plasticity(
            audited_outcomes,
            minimum_first_stage=float(
                spec["success_criterion"][
                    "minimum_first_stage_transport_delta"
                ]
            ),
        )
        offer = audited_arms["offer"]
        withhold = audited_arms["withhold"]
        task_delta = (
            float(offer["metrics"]["task_score"])
            - float(withhold["metrics"]["task_score"])
        )
        composite_delta = (
            audited_outcomes[0].net_external_value
            - audited_outcomes[1].net_external_value
        )
        failed_checks = []
        for assignment in ("offer", "withhold"):
            candidate = audited_candidates[assignment]
            if candidate.status != "candidate_commuting":
                failed_checks.append(
                    f"{assignment}_blind_proposal_left_"
                    "lineage_transported_basin"
                )
        if not audited_outcomes[0].transition.supported_transport:
            failed_checks.append(
                "offer_response_failed_transported_contract"
            )
        if not failed_checks:
            raise RuntimeError(
                "interrupted H96 audit found no preregistered kill"
            )
        result_core = {
            "schema": SCHEMA,
            "kind": "experiment_result",
            "status": "live_stopped_at_preregistered_kill",
            "verdict": "rejected",
            "experiment_sha256": experiment_sha256,
            "manifest_ref": _relative_ref(manifest_path),
            "completed_pair_count": 1,
            "requested_pair_count": pair_count,
            "failed_checks": failed_checks,
            "pair_01": audited_arms,
            "target_fiber_estimate": estimate.to_receipt(),
            "aggregate": {
                "offer_total_task_score_minus_withhold": task_delta,
                "offer_composite_minus_withhold": composite_delta,
                "offer_levels_gained": int(
                    offer["metrics"]["task_score"]
                ),
                "withhold_levels_gained": int(
                    withhold["metrics"]["task_score"]
                ),
                "offer_first_level_action": (
                    json.loads(
                        (
                            output_dir
                            / "arms"
                            / "pair_01_offer_causal_mechanics.json"
                        ).read_text(encoding="utf-8")
                    )["probe"]["first_level_action"]
                ),
                "static_transport_binding_count": len(
                    static_transport.object_ref_bindings
                ),
                "lineage_transport_binding_count": len(
                    lineage.traces
                ),
                "appearance_revision_count": (
                    lineage.appearance_revision_count
                ),
                "bracketed_occlusion_count": (
                    lineage.bracketed_occlusion_count
                ),
            },
            "claim_boundary": [
                *spec["claim_boundary"],
                (
                    "The completed pair does not identify a promoted "
                    "descendant response family."
                ),
                (
                    "The positive task delta cannot repair the failed "
                    "blind-basin and transported-contract checks."
                ),
            ],
        }
        result = {**result_core, "sha256": _sha(result_core)}
        _atomic_json(output_dir / "result.json", result)
        return result

    all_outcomes: list[InstrumentedProposalOutcome] = []
    pair_rows = []
    for pair_index, order in enumerate(orders, start=1):
        stratum = proposal_probe._stratum(
            scope=target_scope,
            game_id=game_id,
            observation_sha256=endpoint_observation["sha256"],
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
                **h95._authorization(
                    proposal=intervention,
                    scope=target_scope,
                    rendered_bytes=rendered_bytes,
                    controller_instance_sha256=instance,
                    observation_sha256=endpoint_observation["sha256"],
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

        def lineage_selector(target_pre):
            return compile_response_transport_candidate(
                source_family=source["family"],
                source_response=source["response"],
                object_transport=lineage,
                intervention_transport=target_transport,
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
                    endpoint_observation["sha256"]
                ),
                action_arity=int(prefix["action_arity"]),
                digest=digest,
                consumption_decision=auth["decision"],
                consumption_receipt=auth["consumption"],
                target_contract=target_contract,
                controller_instance_sha256=(
                    auth["controller_instance"]
                ),
                stratum_sha256=stratum.sha256,
                feature_adapter=None,
                object_catalog=endpoint_catalog,
                object_authority=authority,
                object_presentation=presentation,
                admission_selector=(
                    lineage_selector
                    if assignment == "offer"
                    else None
                ),
                restored_prefix_actions=tuple(prefix["actions"]),
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
            outcomes[assignment] = proposal_probe._instrumented_outcome(
                arms[assignment],
                transition=transitions[assignment],
                arm_path=arm_path,
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
                    object_transport=lineage,
                    intervention_transport=target_transport,
                    source_contract=source_contract,
                    target_contract=target_contract,
                    source_pre_proposal=source_pre,
                    source_post_proposal=source_post,
                    target_pre_proposal=blind,
                )
            )
            if candidates[assignment].status != "candidate_commuting":
                raise RuntimeError(
                    "H96 blind proposal left lineage-transported basin"
                )
        if arms["offer"]["admission_decision_checkpoint"][
            "decision"
        ] != candidates["offer"].to_receipt():
            raise RuntimeError("H96 lineage admission checkpoint drifted")
        offer_value = outcomes["offer"].net_external_value
        withhold_value = outcomes["withhold"].net_external_value
        pair_row = {
            "pair_index": pair_index,
            "arm_order": order,
            "stratum": stratum.to_receipt(),
            "offer_lineage_candidate": (
                candidates["offer"].to_receipt()
            ),
            "withhold_lineage_basin_check": (
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
        "static_type_transport": static_transport.to_receipt(),
        "lineage_transport": lineage.to_receipt(),
        "intervention_revision_transport": (
            target_transport.to_receipt()
        ),
        "placebo_intervention_revision_transport": (
            placebo_transport.to_receipt()
        ),
        "preflight_lineage_candidate": (
            preflight_candidate.to_receipt()
        ),
        "pairs": pair_rows,
        "target_fiber_estimate": estimate.to_receipt(),
        "promoted_target_response_family": (
            promoted_family.to_receipt()
        ),
        "aggregate": {
            "pair_count": len(pair_rows),
            "lineage_count": len(lineage.traces),
            "appearance_revision_count": (
                lineage.appearance_revision_count
            ),
            "bracketed_occlusion_count": (
                lineage.bracketed_occlusion_count
            ),
            "all_blind_lineage_basin_rate": 1.0,
            "offer_total_task_score_minus_withhold": task_delta,
            "offer_composite_wins": wins,
            "mean_offer_minus_withhold_composite": mean_delta,
            "prefix_primitive_action_cost_per_arm": len(
                prefix["actions"]
            ),
            "post_prefix_primitive_action_cost_per_arm": float(
                args.budget
            ),
            "total_primitive_action_cost_per_arm": (
                len(prefix["actions"]) + args.budget
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
        default="h96-causal-object-lineage-20260802",
    )
    parser.add_argument(
        "--memory-source-result",
        default=str(base / "h86_level_boundary_microsleep_result.json"),
    )
    parser.add_argument(
        "--spec",
        default=str(base / "h96_causal_object_lineage_spec.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(base / "h96_causal_object_lineage"),
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--audit-interrupted", action="store_true")
    args = parser.parse_args()
    if args.pairs <= 0 or args.budget <= 0:
        raise SystemExit("pair count and budget must be positive")
    bootstrap_dotenv_from_repo_root()
    result = run_experiment(args)
    if args.preflight_only:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.audit_interrupted:
        print(json.dumps({
            "result_path": _relative_ref(
                Path(args.output_dir).resolve() / "result.json"
            ),
            "status": result["status"],
            "verdict": result["verdict"],
            "failed_checks": result["failed_checks"],
            "aggregate": result["aggregate"],
            "target_fiber_estimate": result["target_fiber_estimate"],
            "sha256": result["sha256"],
        }, indent=2, sort_keys=True))
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
