#!/usr/bin/env python3
"""Measure how a memory offer changes a controller's blind proposal.

The target and placebo bundles come from an external experiment spec.  Both
arms receive a blind proposal call, an exact-byte-matched revision call, and
the same primitive action budget.  The harness lowers proposal text through a
frozen adapter, compiles a proposal-response signature, and estimates target
offer value without equating delivery with uptake.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[3]
CONTROL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(CONTROL))

from arc3_pairwise_memory_content_probe import (  # noqa: E402
    _condition_bundle_base,
    _condition_provenance,
    _equalize_rendered_bytes,
    _load_source,
    _proposal,
)
from arc3_paired_recall_probe import (  # noqa: E402
    _append_jsonl,
    _atomic_json,
    _controller_instance_sha256,
    _file_sha256,
    _initial_observation,
    _outcome_metrics,
    _prefix_sha256,
    _relative_ref,
)
from arc3_responses_agent_probe import (  # noqa: E402
    CodexSubscriptionArcThread,
    _resolve_game_id,
    _sha_payload,
    _sleep_memory_scope,
    run_subscription_probe,
    subscription_arc_instructions,
)
from ztare.common.decision_use_gate import (  # noqa: E402
    ControllerDecisionProposal,
    DecisionUseContract,
)
from ztare.common.instrumented_proposal_plasticity import (  # noqa: E402
    InstrumentedProposalOutcome,
    compile_admission_decision,
    compile_instrumented_transition,
    estimate_instrumented_plasticity,
)
from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.object_linked_judgment import (  # noqa: E402
    ObjectLinkedControllerProposal,
    ObjectReferenceAuthority,
    ObjectRolePathContract,
    compile_object_linked_transition,
)
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    RecallExperimentStratum,
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    select_sparse_memories,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.observation_object_catalog import (  # noqa: E402
    GridObjectCatalog,
    GridObjectCatalogPresentation,
    compile_catalog_presentation,
    compile_catalog_from_observation,
    selector_refs,
)


SCHEMA = "ztare-arc3-instrumented-proposal-plasticity-v1"
OBJECT_LINKED_SCHEMA = "ztare-arc3-object-linked-judgment-quotient-v1"
CATALOG_POINTER_SCHEMA = "ztare-arc3-catalog-scoped-pointer-judgment-v1"


def _sha(payload: Mapping[str, Any]) -> str:
    import hashlib

    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _feature_adapter_sha256(adapter: Mapping[str, Any]) -> str:
    return _sha({"proposal_feature_adapter": dict(adapter)})


def _proposal_text(
    row: Mapping[str, Any],
    *,
    fields: tuple[str, ...],
) -> str:
    return "\n".join(str(row.get(field) or "") for field in fields)


def extract_proposal_features(
    proposal: Mapping[str, Any],
    adapter: Mapping[str, Any],
) -> tuple[str, ...]:
    """Apply one frozen, inspectable feature-lowering adapter."""

    if adapter.get("schema") != "ztare-regex-proposal-feature-adapter-v1":
        raise ValueError("unknown proposal feature adapter schema")
    fields = tuple(str(value) for value in adapter.get("text_fields") or ())
    allowed_fields = {"prediction", "plan_summary", "uncertainty"}
    if not fields or not set(fields).issubset(allowed_fields):
        raise ValueError("proposal adapter has invalid text fields")
    text = _proposal_text(proposal, fields=fields)
    found: list[str] = []
    for rule in adapter.get("rules") or []:
        feature = str(rule.get("feature_id") or "").strip()
        include = tuple(
            str(value) for value in rule.get("include_any_regex") or ()
        )
        exclude = tuple(
            str(value) for value in rule.get("exclude_any_regex") or ()
        )
        if not feature or not include:
            raise ValueError("proposal feature rule is incomplete")
        try:
            included = any(re.search(pattern, text, re.I) for pattern in include)
            excluded = any(re.search(pattern, text, re.I) for pattern in exclude)
        except re.error as exc:
            raise ValueError("proposal feature rule has invalid regex") from exc
        if included and not excluded:
            found.append(feature)
    return tuple(sorted(set(found)))


def _typed_proposal(
    row: Mapping[str, Any],
    *,
    scope,
    controller_instance_sha256: str,
    feature_adapter: Mapping[str, Any],
    parent_proposal_sha256: str = "",
    consumed_intervention_revision_sha256: str = "",
) -> ControllerDecisionProposal:
    prediction_payload = {
        "prediction": str(row.get("prediction") or ""),
        "plan_summary": str(row.get("plan_summary") or ""),
        "uncertainty": str(row.get("uncertainty") or ""),
    }
    return ControllerDecisionProposal(
        scope=scope,
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=str(row.get("observation_sha256") or ""),
        proposal_ref=f"sha256:{_sha(dict(row))}",
        action_ref=str(row.get("action")),
        predicted_consequence_ref=(
            f"sha256:{_sha(prediction_payload)}"
        ),
        asserted_features=extract_proposal_features(
            row,
            feature_adapter,
        ),
        parent_proposal_sha256=parent_proposal_sha256,
        consumed_intervention_revision_sha256=(
            consumed_intervention_revision_sha256
        ),
    )


def _object_linked_proposal(
    row: Mapping[str, Any],
    *,
    scope,
    controller_instance_sha256: str,
    catalog: GridObjectCatalog,
    presentation: GridObjectCatalogPresentation | None = None,
    parent_proposal_sha256: str = "",
    consumed_intervention_revision_sha256: str = "",
) -> ObjectLinkedControllerProposal:
    if str(row.get("catalog_sha256") or "") != catalog.sha256:
        raise ValueError("actor proposal crossed object catalog authority")
    if presentation is not None:
        if str(row.get("presentation_sha256") or "") != (
            presentation.sha256
        ):
            raise ValueError(
                "actor proposal crossed catalog presentation authority"
            )
        controlled_object_ref = presentation.resolve_handle(
            str(row.get("controlled_object_handle") or "")
        )
        ordered_waypoint_refs = tuple(
            presentation.resolve_handle(str(value))
            for value in row.get("ordered_waypoint_handles") or ()
        )
    else:
        controlled_object_ref = str(
            row.get("controlled_object_ref") or ""
        )
        ordered_waypoint_refs = tuple(
            str(value)
            for value in row.get("ordered_waypoint_refs") or ()
        )
    prediction_payload = {
        "prediction": str(row.get("prediction") or ""),
        "plan_summary": str(row.get("plan_summary") or ""),
        "uncertainty": str(row.get("uncertainty") or ""),
    }
    return ObjectLinkedControllerProposal(
        scope=scope,
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=str(row.get("observation_sha256") or ""),
        catalog_sha256=str(row.get("catalog_sha256") or ""),
        proposal_ref=f"sha256:{_sha(dict(row))}",
        action_ref=str(row.get("action")),
        predicted_consequence_ref=(
            f"sha256:{_sha(prediction_payload)}"
        ),
        controlled_object_ref=controlled_object_ref,
        ordered_waypoint_refs=ordered_waypoint_refs,
        parent_proposal_sha256=parent_proposal_sha256,
        consumed_intervention_revision_sha256=(
            consumed_intervention_revision_sha256
        ),
    )


class InstrumentedFirstDecisionThread:
    """Wrap one actor with a blind-proposal/revision first decision."""

    def __init__(
        self,
        *,
        actor: CodexSubscriptionArcThread,
        assignment: str,
        digest: Mapping[str, Any],
        consumption_receipt: Mapping[str, Any],
        target_contract: DecisionUseContract,
        controller_instance_sha256: str,
        stratum_sha256: str,
        feature_adapter: Mapping[str, Any],
    ) -> None:
        self.actor = actor
        self.assignment = assignment
        self.digest = dict(digest)
        self.consumption_receipt = dict(consumption_receipt)
        self.target_contract = target_contract
        self.controller_instance_sha256 = controller_instance_sha256
        self.stratum_sha256 = stratum_sha256
        self.feature_adapter = dict(feature_adapter)
        self.transition = None
        self._first_complete = False

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        if self._first_complete:
            return self.actor.decide(observation)
        pre_row = self.actor.propose(observation)
        self.actor.queue_recall_digest(
            self.digest,
            consumption_receipt=self.consumption_receipt,
        )
        post_row = self.actor.revise(
            observation,
            pre_proposal=pre_row,
        )
        pre = _typed_proposal(
            pre_row,
            scope=self.target_contract.scope,
            controller_instance_sha256=(
                self.controller_instance_sha256
            ),
            feature_adapter=self.feature_adapter,
        )
        post_row = {
            **post_row,
            "observation_sha256": str(observation["sha256"]),
        }
        post = _typed_proposal(
            post_row,
            scope=self.target_contract.scope,
            controller_instance_sha256=(
                self.controller_instance_sha256
            ),
            feature_adapter=self.feature_adapter,
            parent_proposal_sha256=pre.sha256,
            consumed_intervention_revision_sha256=(
                self.target_contract.intervention_revision_sha256
                if self.assignment == "offer"
                else ""
            ),
        )
        self.transition = compile_instrumented_transition(
            trial_ref=(
                f"{self.stratum_sha256}:{self.assignment}:decision-0"
            ),
            stratum_sha256=self.stratum_sha256,
            assignment=self.assignment,
            pre_proposal=pre,
            post_proposal=post,
            contract=self.target_contract,
        )
        self._first_complete = True
        return {
            **post_row,
            "instrumented_proposal": {
                "assignment": self.assignment,
                "feature_adapter_sha256": _feature_adapter_sha256(
                    self.feature_adapter
                ),
                "pre_actor_proposal": pre_row,
                "pre_proposal": pre.to_receipt(),
                "post_proposal": post.to_receipt(),
                "transition": self.transition.to_receipt(),
                "delivered_digest_sha256": _sha_payload(self.digest),
                "delivered_consumption_receipt_sha256": str(
                    self.consumption_receipt.get("sha256") or ""
                ),
            },
        }


class ObjectLinkedFirstDecisionThread:
    """Bind the first decision to an exact same-observation object catalog."""

    def __init__(
        self,
        *,
        actor: CodexSubscriptionArcThread,
        assignment: str,
        digest: Mapping[str, Any],
        consumption_receipt: Mapping[str, Any],
        target_contract: ObjectRolePathContract,
        object_catalog: GridObjectCatalog,
        object_authority: ObjectReferenceAuthority,
        object_presentation: (
            GridObjectCatalogPresentation | None
        ) = None,
        proposal_observer=None,
        admission_selector=None,
        admission_observer=None,
        controller_instance_sha256: str,
        stratum_sha256: str,
    ) -> None:
        self.actor = actor
        self.assignment = assignment
        self.digest = dict(digest)
        self.consumption_receipt = dict(consumption_receipt)
        self.target_contract = target_contract
        self.object_catalog = object_catalog
        self.object_authority = object_authority
        self.object_presentation = object_presentation
        self.proposal_observer = proposal_observer
        self.admission_selector = admission_selector
        self.admission_observer = admission_observer
        self.controller_instance_sha256 = controller_instance_sha256
        self.stratum_sha256 = stratum_sha256
        self.transition = None
        self.admission_decision = None
        self._first_complete = False

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        if self._first_complete:
            return self.actor.decide(observation)
        prompt_catalog = (
            self.object_presentation.prompt_receipt()
            if self.object_presentation is not None
            else self.object_catalog.prompt_receipt()
        )
        pre_row = self.actor.propose(
            observation,
            object_catalog=prompt_catalog,
        )
        if self.proposal_observer is not None:
            self.proposal_observer("blind_pre_proposal", pre_row)
        pre = _object_linked_proposal(
            pre_row,
            scope=self.target_contract.scope,
            controller_instance_sha256=(
                self.controller_instance_sha256
            ),
            catalog=self.object_catalog,
            presentation=self.object_presentation,
        )
        if self.admission_selector is not None:
            admission = self.admission_selector(pre)
            receipt = (
                admission.to_receipt()
                if hasattr(admission, "to_receipt")
                else dict(admission)
            )
            action = str(receipt.get("action") or "")
            expected_actions = (
                {"offer", "explore_lineage", "explore_transport"}
                if self.assignment == "offer"
                else {"withhold", "silence"}
            )
            if action not in expected_actions:
                raise RuntimeError(
                    "prospective admission disagreed with the frozen arm"
                )
            self.admission_decision = receipt
            if self.admission_observer is not None:
                self.admission_observer(receipt)
        self.actor.queue_recall_digest(
            self.digest,
            consumption_receipt=self.consumption_receipt,
        )
        post_row = self.actor.revise(
            observation,
            pre_proposal=pre_row,
            object_catalog=prompt_catalog,
        )
        if self.proposal_observer is not None:
            self.proposal_observer(
                "post_proposal_commitment",
                post_row,
            )
        post_row = {
            **post_row,
            "observation_sha256": str(observation["sha256"]),
        }
        post = _object_linked_proposal(
            post_row,
            scope=self.target_contract.scope,
            controller_instance_sha256=(
                self.controller_instance_sha256
            ),
            catalog=self.object_catalog,
            presentation=self.object_presentation,
            parent_proposal_sha256=pre.sha256,
            consumed_intervention_revision_sha256=(
                self.target_contract.intervention_revision_sha256
                if self.assignment == "offer"
                else ""
            ),
        )
        self.transition = compile_object_linked_transition(
            trial_ref=(
                f"{self.stratum_sha256}:{self.assignment}:decision-0"
            ),
            stratum_sha256=self.stratum_sha256,
            assignment=self.assignment,
            pre_proposal=pre,
            post_proposal=post,
            contract=self.target_contract,
            authority=self.object_authority,
        )
        self._first_complete = True
        return {
            **post_row,
            "instrumented_proposal": {
                "assignment": self.assignment,
                "quotient_kind": (
                    "catalog_scoped_pointer"
                    if self.object_presentation is not None
                    else "object_linked"
                ),
                "object_catalog_sha256": self.object_catalog.sha256,
                "object_presentation_sha256": (
                    self.object_presentation.sha256
                    if self.object_presentation is not None
                    else ""
                ),
                "pre_actor_proposal": pre_row,
                "pre_proposal": pre.to_receipt(),
                "admission_decision": self.admission_decision,
                "post_proposal": post.to_receipt(),
                "transition": self.transition.to_receipt(),
                "delivered_digest_sha256": _sha_payload(self.digest),
                "delivered_consumption_receipt_sha256": str(
                    self.consumption_receipt.get("sha256") or ""
                ),
            },
        }


def _pair_orders(pair_count: int) -> list[list[str]]:
    return [
        ["offer", "withhold"] if index % 2 == 0 else ["withhold", "offer"]
        for index in range(pair_count)
    ]


def _stratum(
    *,
    scope,
    game_id: str,
    observation_sha256: str,
    budget: int,
    seed: str,
    pair_index: int,
) -> RecallExperimentStratum:
    return RecallExperimentStratum(
        scope=scope,
        restored_prefix_sha256=_prefix_sha256(
            game_id=game_id,
            observation_sha256=observation_sha256,
        ),
        restored_observation_sha256=observation_sha256,
        action_budget=budget,
        primitive_action_cost=float(budget),
        randomization_seed_sha256=_sha({
            "seed": seed,
            "pair_index": pair_index,
        }),
    )


def _run_arm(
    *,
    receipt_schema: str,
    output_dir: Path,
    experiment_sha256: str,
    pair_index: int,
    assignment: str,
    condition_id: str,
    game_id: str,
    budget: int,
    model_id: str,
    reasoning_effort: str,
    timeout_seconds: float,
    expected_observation_sha256: str,
    action_arity: int,
    digest: Mapping[str, Any],
    consumption_decision,
    consumption_receipt,
    target_contract: DecisionUseContract | ObjectRolePathContract,
    controller_instance_sha256: str,
    stratum_sha256: str,
    feature_adapter: Mapping[str, Any] | None,
    object_catalog: GridObjectCatalog | None = None,
    object_authority: ObjectReferenceAuthority | None = None,
    object_presentation: (
        GridObjectCatalogPresentation | None
    ) = None,
    admission_selector=None,
    restored_prefix_actions: tuple[int, ...] = (),
) -> dict[str, Any]:
    stem = f"pair_{pair_index:02d}_{assignment}_{condition_id}"
    arm_path = output_dir / "arms" / f"{stem}.json"
    if arm_path.exists():
        payload = json.loads(arm_path.read_text(encoding="utf-8"))
        if payload.get("experiment_sha256") != experiment_sha256:
            raise RuntimeError(f"arm checkpoint identity drift: {arm_path}")
        return payload
    turn_log = output_dir / "turns" / f"{stem}.jsonl"
    proposal_log = output_dir / "proposals" / f"{stem}.jsonl"
    admission_log = output_dir / "admissions" / f"{stem}.jsonl"

    def observe(turn: Mapping[str, Any]) -> None:
        _append_jsonl(turn_log, {
            "schema": receipt_schema,
            "kind": "arm_turn_checkpoint",
            "experiment_sha256": experiment_sha256,
            "pair_index": pair_index,
            "assignment": assignment,
            "condition_id": condition_id,
            "turn": dict(turn),
        })

    base_actor = CodexSubscriptionArcThread(
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        instructions=subscription_arc_instructions(
            budget=budget,
            action_arity=action_arity,
        ),
        timeout_seconds=timeout_seconds,
        resume_session=True,
    )
    if isinstance(target_contract, ObjectRolePathContract):
        if object_catalog is None or object_authority is None:
            raise RuntimeError(
                "object-linked arm omitted catalog authority"
            )
        proposal_events: list[dict[str, Any]] = []
        admission_events: list[dict[str, Any]] = []

        def observe_proposal(
            phase: str,
            proposal: Mapping[str, Any],
        ) -> None:
            event = {
                "schema": receipt_schema,
                "kind": "raw_proposal_checkpoint",
                "experiment_sha256": experiment_sha256,
                "pair_index": pair_index,
                "assignment": assignment,
                "condition_id": condition_id,
                "phase": phase,
                "proposal": dict(proposal),
            }
            proposal_events.append(event)
            _append_jsonl(proposal_log, event)

        def observe_admission(
            decision: Mapping[str, Any],
        ) -> None:
            event = {
                "schema": receipt_schema,
                "kind": "admission_decision_checkpoint",
                "experiment_sha256": experiment_sha256,
                "pair_index": pair_index,
                "assignment": assignment,
                "condition_id": condition_id,
                "decision": dict(decision),
            }
            admission_events.append(event)
            _append_jsonl(admission_log, event)

        actor = ObjectLinkedFirstDecisionThread(
            actor=base_actor,
            assignment=assignment,
            digest=digest,
            consumption_receipt=consumption_receipt.to_receipt(),
            target_contract=target_contract,
            object_catalog=object_catalog,
            object_authority=object_authority,
            object_presentation=object_presentation,
            proposal_observer=observe_proposal,
            admission_selector=admission_selector,
            admission_observer=observe_admission,
            controller_instance_sha256=controller_instance_sha256,
            stratum_sha256=stratum_sha256,
        )
    else:
        if feature_adapter is None:
            raise RuntimeError("lexical arm omitted feature adapter")
        actor = InstrumentedFirstDecisionThread(
            actor=base_actor,
            assignment=assignment,
            digest=digest,
            consumption_receipt=consumption_receipt.to_receipt(),
            target_contract=target_contract,
            controller_instance_sha256=controller_instance_sha256,
            stratum_sha256=stratum_sha256,
            feature_adapter=feature_adapter,
        )
    probe = run_subscription_probe(
        adapter=ArcAgi3Adapter(game_id),
        game_id=game_id,
        budget=budget,
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
        resume_session=True,
        thread=actor,
        turn_observer=observe,
        restored_prefix_actions=restored_prefix_actions,
    )
    if int(probe["actions_executed"]) != budget:
        raise RuntimeError("arm did not spend the fixed action budget")
    if int(probe["total_actions_executed"]) != (
        budget + len(restored_prefix_actions)
    ):
        raise RuntimeError("arm total prefix plus controller cost drifted")
    if int(probe["inference_tick_count"]) != budget + 1:
        raise RuntimeError("arm did not use the two-stage first decision")
    if (
        str(probe["observations"][0]["sha256"])
        != expected_observation_sha256
    ):
        raise RuntimeError("arm restored a different observation")
    if (
        object_presentation is not None
        and len(proposal_events) != 2
    ):
        raise RuntimeError(
            "catalog-scoped arm did not checkpoint both raw proposals"
        )
    if admission_selector is not None and len(admission_events) != 1:
        raise RuntimeError(
            "prospective arm did not checkpoint one admission decision"
        )
    sessions = {
        str(turn.get("session_id") or "")
        for turn in probe["turns"]
    }
    if len(sessions) != 1 or "" in sessions:
        raise RuntimeError("arm did not preserve one runtime session")
    first = probe["turns"][0]
    instrumented = first.get("instrumented_proposal")
    if not isinstance(instrumented, dict):
        raise RuntimeError("first turn omitted proposal instrumentation")
    if actor.transition is None:
        raise RuntimeError("proposal transition was not compiled")
    injections = [
        turn["recall_injection"]
        for turn in probe["turns"]
        if turn.get("recall_injection") is not None
    ]
    if len(injections) != 1 or first.get("recall_injection") is None:
        raise RuntimeError("arm must inject one target or placebo bundle")
    if (
        str(injections[0]["consumption_receipt_sha256"])
        != consumption_receipt.sha256
    ):
        raise RuntimeError("arm consumed the wrong intervention receipt")
    runtime_session = next(iter(sessions))
    payload = {
        "schema": receipt_schema,
        "kind": "instrumented_proposal_arm",
        "experiment_sha256": experiment_sha256,
        "pair_index": pair_index,
        "assignment": assignment,
        "condition_id": condition_id,
        "controller_instance_sha256": controller_instance_sha256,
        "runtime_controller_instance_ref": runtime_session,
        "trajectory_sha256": _sha({
            "observations": probe["observations"],
            "turns": probe["turns"],
        }),
        "consumption_decision": consumption_decision.to_receipt(),
        "consumption_receipt": consumption_receipt.to_receipt(),
        "target_contract": target_contract.to_receipt(),
        "transition": actor.transition.to_receipt(),
        "admission_decision_checkpoint": (
            {
                "ref": _relative_ref(admission_log),
                "sha256": _file_sha256(admission_log),
                "count": len(admission_events),
                "decision": actor.admission_decision,
            }
            if admission_selector is not None
            else None
        ),
        "raw_proposal_checkpoint": (
            {
                "ref": _relative_ref(proposal_log),
                "sha256": _file_sha256(proposal_log),
                "count": len(proposal_events),
            }
            if isinstance(
                target_contract,
                ObjectRolePathContract,
            )
            else None
        ),
        "metrics": _outcome_metrics(probe),
        "probe": probe,
    }
    _atomic_json(arm_path, payload)
    print(json.dumps({
        "event": "instrumented_proposal_arm_complete",
        "pair_index": pair_index,
        "assignment": assignment,
        "condition_id": condition_id,
        "relation": actor.transition.relation,
        "supported_transport": actor.transition.supported_transport,
        "levels_gained": probe["levels_gained"],
        "first_level_action": probe["first_level_action"],
        "runtime_session": runtime_session,
        "arm_path": _relative_ref(arm_path),
    }, sort_keys=True), flush=True)
    return payload


def _external_value(metrics: Mapping[str, Any]) -> float:
    return (
        0.8 * float(metrics["task_score"])
        + 0.2 * float(metrics["efficiency_score"])
    )


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
        external_value=_external_value(arm["metrics"]),
        # Both target and placebo have equal presentation and inference cost.
        # This is the differential target-offer cost, not total prompt cost.
        offer_cost=0.0,
        primitive_action_cost=float(arm["probe"]["budget"]),
    )


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    source_path = Path(args.source_result).resolve()
    loader_spec_path = Path(args.spec).resolve()
    spec_path = Path(
        getattr(args, "original_spec", args.spec)
    ).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    pointer_mode = spec.get("schema") == (
        "ztare-arc3-catalog-scoped-pointer-judgment-spec-v1"
    )
    object_mode = pointer_mode or spec.get("schema") == (
        "ztare-arc3-object-linked-judgment-quotient-spec-v1"
    )
    receipt_schema = (
        CATALOG_POINTER_SCHEMA
        if pointer_mode
        else OBJECT_LINKED_SCHEMA
        if object_mode
        else SCHEMA
    )
    source_meta, target_condition, placebo_condition, turns = _load_source(
        source_path,
        loader_spec_path,
    )
    source_meta["spec_path"] = _relative_ref(spec_path)
    source_meta["spec_sha256"] = _file_sha256(spec_path)
    # _load_source expects left/right condition names.
    target_condition["condition_id"] = str(
        spec["target_intervention"]["condition_id"]
    )
    placebo_condition["condition_id"] = str(
        spec["placebo_intervention"]["condition_id"]
    )
    game_id = _resolve_game_id(args.game)
    initial_observation, action_arity = _initial_observation(game_id=game_id)
    object_catalog = (
        compile_catalog_from_observation(initial_observation)
        if object_mode
        else None
    )
    object_presentation = (
        compile_catalog_presentation(object_catalog)
        if pointer_mode and object_catalog is not None
        else None
    )
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
    object_authority = None
    resolved_object_contract = None
    if object_mode:
        if object_catalog is None:
            raise RuntimeError("object catalog was not compiled")
        contract_spec = dict(spec["object_role_contract"])
        controlled = object_catalog.resolve_selector(
            contract_spec["controlled_object_selector"]
        )
        required_waypoints = selector_refs(
            object_catalog,
            contract_spec["required_waypoint_selectors"],
        )
        forbidden_controlled = selector_refs(
            object_catalog,
            contract_spec["forbidden_control_selectors"],
        )
        object_authority = ObjectReferenceAuthority(
            observation_sha256=initial_observation["sha256"],
            catalog_sha256=object_catalog.sha256,
            object_refs=object_catalog.object_refs,
        )
        target_contract = ObjectRolePathContract(
            scope=scope,
            catalog_sha256=object_catalog.sha256,
            intervention_revision_sha256=(
                target_proposal.intervention_revision_sha256
            ),
            required_controlled_object_ref=controlled.object_ref,
            required_waypoint_refs=required_waypoints,
            forbidden_controlled_object_refs=forbidden_controlled,
            evidence_refs=tuple(contract_spec["evidence_refs"]),
        )
        resolved_object_contract = {
            "required_controlled_object": controlled.to_receipt(),
            "required_waypoints": [
                object_catalog.resolve_selector(selector).to_receipt()
                for selector in contract_spec[
                    "required_waypoint_selectors"
                ]
            ],
            "forbidden_controlled_objects": [
                object_catalog.resolve_selector(selector).to_receipt()
                for selector in contract_spec[
                    "forbidden_control_selectors"
                ]
            ],
        }
        feature_adapter = None
    else:
        contract_spec = spec["decision_use_contract"]
        target_contract = DecisionUseContract(
            scope=scope,
            intervention_revision_sha256=(
                target_proposal.intervention_revision_sha256
            ),
            required_features=tuple(
                contract_spec["required_features"]
            ),
            forbidden_features=tuple(
                contract_spec["forbidden_features"]
            ),
            evidence_refs=tuple(
                f"memory:{value}"
                for value in contract_spec["evidence_memory_ids"]
            ),
        )
        feature_adapter = dict(spec["proposal_feature_adapter"])
    pair_count = int(args.pairs)
    orders = _pair_orders(pair_count)
    manifest_core = {
        "schema": receipt_schema,
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
        "target_contract": target_contract.to_receipt(),
        "primary_score": {
            "task_weight": 0.8,
            "efficiency_weight": 0.2,
        },
        "success_criterion": dict(spec["success_criterion"]),
    }
    if object_mode:
        if object_catalog is None or object_authority is None:
            raise RuntimeError("object quotient authority is incomplete")
        manifest_core["proposal_quotient"] = {
            "kind": (
                "catalog_scoped_pointer"
                if pointer_mode
                else "object_linked"
            ),
            "object_catalog": object_catalog.to_receipt(),
            "object_authority_sha256": object_authority.sha256,
            "resolved_object_contract": resolved_object_contract,
        }
        if object_presentation is not None:
            manifest_core["proposal_quotient"][
                "object_presentation"
            ] = object_presentation.to_receipt()
    else:
        manifest_core["feature_adapter_sha256"] = (
            _feature_adapter_sha256(feature_adapter or {})
        )
    experiment_sha256 = _sha(manifest_core)
    manifest = {
        **manifest_core,
        "experiment_sha256": experiment_sha256,
    }
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing != manifest:
            raise RuntimeError("existing manifest drifted")
    else:
        _atomic_json(manifest_path, manifest)

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
    pair_rows: list[dict[str, Any]] = []
    all_outcomes: list[InstrumentedProposalOutcome] = []
    for pair_index, order in enumerate(orders, start=1):
        stratum = _stratum(
            scope=scope,
            game_id=game_id,
            observation_sha256=initial_observation["sha256"],
            budget=args.budget,
            seed=args.seed,
            pair_index=pair_index,
        )
        authorizations = {}
        for assignment in ("offer", "withhold"):
            condition, _digest, proposal = conditions[assignment]
            candidate = proposal.to_memory_candidate()
            recall = select_sparse_memories(
                WakeSleepCreditState(),
                (candidate,),
                scope=scope,
                max_items=1,
                minimum_score=-2.0,
                max_prompt_tokens=rendered_bytes,
            )
            controller_instance = _controller_instance_sha256(
                experiment_sha256=experiment_sha256,
                pair_index=pair_index,
                assignment=assignment,
            )
            decision = authorize_recall_consumption(
                recall,
                (candidate,),
                controller_instance_sha256=controller_instance,
                observation_sha256=initial_observation["sha256"],
                decision_ref=(
                    f"pair-{pair_index:02d}:{assignment}:decision-0"
                ),
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
                controller_instance_sha256=controller_instance,
                observation_sha256=initial_observation["sha256"],
            )
            authorizations[assignment] = {
                "recall": recall,
                "decision": decision,
                "consumption": consumption,
                "controller_instance": controller_instance,
            }
        arm_rows = {}
        for assignment in order:
            condition, digest, _proposal_row = conditions[assignment]
            auth = authorizations[assignment]
            arm_rows[assignment] = _run_arm(
                receipt_schema=receipt_schema,
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
                target_contract=target_contract,
                controller_instance_sha256=(
                    auth["controller_instance"]
                ),
                stratum_sha256=stratum.sha256,
                feature_adapter=feature_adapter,
                object_catalog=object_catalog,
                object_authority=object_authority,
                object_presentation=object_presentation,
            )
        arm_paths = {
            assignment: (
                output_dir
                / "arms"
                / (
                    f"pair_{pair_index:02d}_{assignment}_"
                    f"{conditions[assignment][0]['condition_id']}.json"
                )
            )
            for assignment in ("offer", "withhold")
        }
        # Recompile from the actor-bound proposal receipts so restart paths
        # and fresh paths share the same deterministic transition object.
        compiled = {}
        for assignment in ("offer", "withhold"):
            first = arm_rows[assignment]["probe"]["turns"][0][
                "instrumented_proposal"
            ]
            pre_receipt = first["pre_proposal"]
            post_receipt = first["post_proposal"]
            if object_mode:
                if (
                    object_catalog is None
                    or object_authority is None
                    or not isinstance(
                        target_contract,
                        ObjectRolePathContract,
                    )
                ):
                    raise RuntimeError(
                        "object replay authority is incomplete"
                    )
                pre = ObjectLinkedControllerProposal(
                    scope=scope,
                    controller_instance_sha256=str(
                        pre_receipt[
                            "controller_instance_sha256"
                        ]
                    ),
                    observation_sha256=str(
                        pre_receipt["observation_sha256"]
                    ),
                    catalog_sha256=str(
                        pre_receipt["catalog_sha256"]
                    ),
                    proposal_ref=str(pre_receipt["proposal_ref"]),
                    action_ref=str(pre_receipt["action_ref"]),
                    predicted_consequence_ref=str(
                        pre_receipt["predicted_consequence_ref"]
                    ),
                    controlled_object_ref=str(
                        pre_receipt["controlled_object_ref"]
                    ),
                    ordered_waypoint_refs=tuple(
                        pre_receipt["ordered_waypoint_refs"]
                    ),
                )
                post = ObjectLinkedControllerProposal(
                    scope=scope,
                    controller_instance_sha256=str(
                        post_receipt[
                            "controller_instance_sha256"
                        ]
                    ),
                    observation_sha256=str(
                        post_receipt["observation_sha256"]
                    ),
                    catalog_sha256=str(
                        post_receipt["catalog_sha256"]
                    ),
                    proposal_ref=str(post_receipt["proposal_ref"]),
                    action_ref=str(post_receipt["action_ref"]),
                    predicted_consequence_ref=str(
                        post_receipt["predicted_consequence_ref"]
                    ),
                    controlled_object_ref=str(
                        post_receipt["controlled_object_ref"]
                    ),
                    ordered_waypoint_refs=tuple(
                        post_receipt["ordered_waypoint_refs"]
                    ),
                    parent_proposal_sha256=str(
                        post_receipt["parent_proposal_sha256"]
                    ),
                    consumed_intervention_revision_sha256=str(
                        post_receipt[
                            "consumed_intervention_revision_sha256"
                        ]
                    ),
                )
                compiled[assignment] = (
                    compile_object_linked_transition(
                        trial_ref=(
                            f"{stratum.sha256}:{assignment}:decision-0"
                        ),
                        stratum_sha256=stratum.sha256,
                        assignment=assignment,
                        pre_proposal=pre,
                        post_proposal=post,
                        contract=target_contract,
                        authority=object_authority,
                    )
                )
            else:
                if not isinstance(
                    target_contract,
                    DecisionUseContract,
                ):
                    raise RuntimeError(
                        "lexical replay contract changed type"
                    )
                pre = ControllerDecisionProposal(
                    scope=scope,
                    controller_instance_sha256=str(
                        pre_receipt[
                            "controller_instance_sha256"
                        ]
                    ),
                    observation_sha256=str(
                        pre_receipt["observation_sha256"]
                    ),
                    proposal_ref=str(pre_receipt["proposal_ref"]),
                    action_ref=str(pre_receipt["action_ref"]),
                    predicted_consequence_ref=str(
                        pre_receipt["predicted_consequence_ref"]
                    ),
                    asserted_features=tuple(
                        pre_receipt["asserted_features"]
                    ),
                    uncertainty_features=tuple(
                        pre_receipt["uncertainty_features"]
                    ),
                )
                post = ControllerDecisionProposal(
                    scope=scope,
                    controller_instance_sha256=str(
                        post_receipt[
                            "controller_instance_sha256"
                        ]
                    ),
                    observation_sha256=str(
                        post_receipt["observation_sha256"]
                    ),
                    proposal_ref=str(post_receipt["proposal_ref"]),
                    action_ref=str(post_receipt["action_ref"]),
                    predicted_consequence_ref=str(
                        post_receipt["predicted_consequence_ref"]
                    ),
                    asserted_features=tuple(
                        post_receipt["asserted_features"]
                    ),
                    uncertainty_features=tuple(
                        post_receipt["uncertainty_features"]
                    ),
                    parent_proposal_sha256=str(
                        post_receipt["parent_proposal_sha256"]
                    ),
                    consumed_intervention_revision_sha256=str(
                        post_receipt[
                            "consumed_intervention_revision_sha256"
                        ]
                    ),
                )
                compiled[assignment] = (
                    compile_instrumented_transition(
                        trial_ref=(
                            f"{stratum.sha256}:{assignment}:decision-0"
                        ),
                        stratum_sha256=stratum.sha256,
                        assignment=assignment,
                        pre_proposal=pre,
                        post_proposal=post,
                        contract=target_contract,
                    )
                )
            if (
                compiled[assignment].to_receipt()
                != arm_rows[assignment]["transition"]
            ):
                raise RuntimeError(
                    "checkpointed proposal transition failed replay"
                )
        outcomes = {
            assignment: _instrumented_outcome(
                arm_rows[assignment],
                transition=compiled[assignment],
                arm_path=arm_paths[assignment],
            )
            for assignment in ("offer", "withhold")
        }
        all_outcomes.extend(outcomes.values())
        offer_value = outcomes["offer"].net_external_value
        withhold_value = outcomes["withhold"].net_external_value
        pair_row = {
            "pair_index": pair_index,
            "arm_order": order,
            "stratum": stratum.to_receipt(),
            "offer_transition": compiled["offer"].to_receipt(),
            "withhold_transition": compiled["withhold"].to_receipt(),
            "offer_outcome": outcomes["offer"].to_receipt(),
            "withhold_outcome": outcomes["withhold"].to_receipt(),
            "offer_task_minus_withhold": (
                float(arm_rows["offer"]["metrics"]["task_score"])
                - float(arm_rows["withhold"]["metrics"]["task_score"])
            ),
            "offer_composite_minus_withhold": (
                offer_value - withhold_value
            ),
        }
        pair_rows.append(pair_row)
        _atomic_json(
            output_dir / "settlements" / f"pair_{pair_index:02d}.json",
            pair_row,
        )

    prediction_spec = (
        spec["predictions"] if object_mode else spec["prediction"]
    )
    minimum_first_stage = float(
        prediction_spec["minimum_first_stage_transport_delta"]
    )
    estimate = estimate_instrumented_plasticity(
        all_outcomes,
        minimum_first_stage=minimum_first_stage,
    )
    task_delta = sum(
        float(row["offer_task_minus_withhold"])
        for row in pair_rows
    )
    composite_deltas = [
        float(row["offer_composite_minus_withhold"])
        for row in pair_rows
    ]
    mean_delta = sum(composite_deltas) / len(composite_deltas)
    criterion = (
        estimate.status == "identified"
        and estimate.first_stage_transport_delta
        >= minimum_first_stage
        and task_delta >= 0.0
        and mean_delta > 0.0
    )
    if object_mode:
        criterion = bool(
            criterion
            and estimate.offer_supported_transport_rate
            >= float(
                prediction_spec[
                    "minimum_offer_supported_transport_rate"
                ]
            )
            and estimate.withhold_supported_transport_rate
            <= float(
                prediction_spec[
                    "maximum_withhold_spontaneous_transport_rate"
                ]
            )
        )
    verdict = "supported" if criterion else "rejected"
    relation_values: dict[str, list[float]] = {}
    for outcome in all_outcomes:
        relation_values.setdefault(
            outcome.transition.relation,
            [],
        ).append(outcome.net_external_value)
    result_core = {
        "schema": receipt_schema,
        "kind": "experiment_result",
        "status": "live_complete",
        "verdict": verdict,
        "experiment_sha256": experiment_sha256,
        "manifest_ref": _relative_ref(manifest_path),
        "pairs": pair_rows,
        "instrumented_estimate": estimate.to_receipt(),
        "compiled_next_admission": compile_admission_decision(
            estimate
        ).to_receipt(),
        "aggregate": {
            "pair_count": len(pair_rows),
            "offer_total_task_score_minus_withhold": task_delta,
            "offer_composite_wins": sum(
                value > 0.0 for value in composite_deltas
            ),
            "mean_offer_minus_withhold_composite": mean_delta,
            "offer_supported_transport_rate_minus_withhold": (
                estimate.first_stage_transport_delta
            ),
            "rendered_utf8_bytes_per_condition": rendered_bytes,
            "proposal_inferences_before_first_action": 2,
            "primitive_action_cost_per_arm": float(args.budget),
            "relation_mean_external_values": {
                relation: sum(values) / len(values)
                for relation, values in sorted(relation_values.items())
            },
        },
        "claim_boundary": list(spec["claim_boundary"]),
    }
    if object_mode:
        result_core["aggregate"].update({
            "proposal_quotient_kind": (
                "catalog_scoped_pointer"
                if pointer_mode
                else "object_linked"
            ),
            "catalog_reference_resolution_rate": 1.0,
            "cross_observation_or_unknown_reference_count": 0,
        })
        if pointer_mode:
            result_core["aggregate"].update({
                "raw_proposal_checkpoint_rate": 1.0,
                "catalog_handle_resolution_rate": 1.0,
                "unknown_or_cross_presentation_handle_count": 0,
            })
    result = {**result_core, "sha256": _sha(result_core)}
    _atomic_json(output_dir / "result.json", result)
    return result


def _adapt_spec_for_pairwise_loader(
    spec_path: Path,
) -> Path:
    """Expose target/placebo under the generic pairwise loader's side names."""

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    adapted = {
        "schema": spec["schema"],
        "left": spec["target_intervention"],
        "right": spec["placebo_intervention"],
    }
    path = Path("/private/tmp/ztare_h91_pairwise_loader_spec.json")
    path.write_text(
        json.dumps(adapted, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    base = (
        REPO
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="ls20")
    parser.add_argument("--pairs", type=int, default=4)
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
        default="h91-instrumented-proposal-plasticity-20260730",
    )
    parser.add_argument(
        "--source-result",
        default=str(base / "h86_level_boundary_microsleep_result.json"),
    )
    parser.add_argument(
        "--spec",
        default=str(base / "h91_instrumented_proposal_plasticity_spec.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(base / "h91_instrumented_proposal_plasticity"),
    )
    args = parser.parse_args()
    if args.pairs <= 0:
        raise SystemExit("--pairs must be positive")
    if args.budget <= 0:
        raise SystemExit("--budget must be positive")
    bootstrap_dotenv_from_repo_root()
    original_spec = Path(args.spec).resolve()
    adapted_spec = _adapt_spec_for_pairwise_loader(original_spec)
    args.spec = str(adapted_spec)
    # Keep the frozen original spec available to run_experiment.
    result = run_experiment_with_original_spec(args, original_spec)
    print(json.dumps({
        "result_path": _relative_ref(
            Path(args.output_dir).resolve() / "result.json"
        ),
        "verdict": result["verdict"],
        "aggregate": result["aggregate"],
        "instrumented_estimate": result["instrumented_estimate"],
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0


def run_experiment_with_original_spec(
    args: argparse.Namespace,
    original_spec: Path,
) -> dict[str, Any]:
    """Use an adapted loader spec while freezing the original experiment spec."""

    adapted_path = Path(args.spec)
    adapted = json.loads(adapted_path.read_text(encoding="utf-8"))
    original = json.loads(original_spec.read_text(encoding="utf-8"))
    # The loader reads the adapted path.  The experiment reads the complete
    # fields, so materialize a merged private copy with both side aliases.
    merged = {
        **original,
        "left": adapted["left"],
        "right": adapted["right"],
    }
    merged_path = Path("/private/tmp/ztare_h91_complete_spec.json")
    merged_path.write_text(
        json.dumps(merged, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    previous = args.spec
    args.original_spec = str(original_spec)
    args.spec = str(merged_path)
    try:
        return run_experiment(args)
    finally:
        args.spec = previous
        delattr(args, "original_spec")


if __name__ == "__main__":
    raise SystemExit(main())
