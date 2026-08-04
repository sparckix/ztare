#!/usr/bin/env python3
"""Compare two evidence-selected memory interventions on matched ARC runs.

Condition membership lives in an external experiment spec.  The harness owns
no game solution constants.  Both conditions receive exactly one recalled
bundle at the restored prefix, their rendered canonical JSON has identical
UTF-8 byte length, and both spend the same primitive action budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sys
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[3]
CONTROL = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(CONTROL))

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
    _resolve_game_id,
    _sha_payload,
    _sleep_memory_scope,
    run_subscription_probe,
)
from ztare.common.decision_intervention_market import (  # noqa: E402
    DecisionInterventionArmOutcome,
    DecisionInterventionProposal,
    allocate_decision_interventions,
    settle_pairwise_intervention_trial,
)
from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    MemoryAcquisitionProvenance,
    MemoryScope,
    RecallExperimentStratum,
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    select_sparse_memories,
    wake_sleep_credit_state_from_receipt,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402


SCHEMA = "ztare-arc3-pairwise-memory-content-probe-v1"


def _sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    )


def _equalize_rendered_bytes(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Pad one inert presentation field until canonical UTF-8 bytes match."""

    rows = []
    for source in (left, right):
        row = {**dict(source), "presentation_padding": ""}
        rows.append(row)
    lengths = [
        len(_canonical_json(row).encode("utf-8")) for row in rows
    ]
    target = max(lengths)
    for index, length in enumerate(lengths):
        rows[index]["presentation_padding"] = " " * (target - length)
    final_lengths = [
        len(_canonical_json(row).encode("utf-8")) for row in rows
    ]
    if final_lengths != [target, target]:
        raise RuntimeError("canonical presentation byte matching failed")
    return rows[0], rows[1], target


def _load_source(
    source_path: Path,
    spec_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    cycles = source.get("sleep_cycles") or []
    if len(cycles) != 1:
        raise ValueError("source must contain one H86 sleep cycle")
    raw_digest = cycles[0].get("digest")
    if not isinstance(raw_digest, dict):
        raise ValueError("source sleep cycle omitted its raw digest")
    memory_by_id = {
        str(row["memory_id"]): dict(row)
        for row in raw_digest.get("memories") or []
    }
    conditions: dict[str, dict[str, Any]] = {}
    all_requested: set[str] = set()
    for side in ("left", "right"):
        row = dict(spec[side])
        requested = tuple(str(value) for value in row["memory_ids"])
        overlap = all_requested & set(requested)
        if overlap:
            raise ValueError(
                f"condition memories overlap across arms: {sorted(overlap)}"
            )
        all_requested.update(requested)
        missing = [value for value in requested if value not in memory_by_id]
        if missing:
            raise ValueError(f"unknown source memory IDs: {missing}")
        row["memories"] = [memory_by_id[value] for value in requested]
        conditions[side] = row
    turns = {
        int(row["action_count"]): dict(row)
        for row in source.get("turns") or []
    }
    sessions = {
        str(row.get("session_id") or "")
        for row in turns.values()
        if str(row.get("session_id") or "")
    }
    if len(sessions) != 1:
        raise ValueError("source must use one runtime controller")
    source_meta = {
        "source_path": _relative_ref(source_path),
        "source_sha256": _file_sha256(source_path),
        "spec_path": _relative_ref(spec_path),
        "spec_sha256": _file_sha256(spec_path),
        "source_boundary_observation_sha256": str(
            cycles[0]["boundary_observation_sha256"]
        ),
        "source_runtime_session": next(iter(sessions)),
        "boundary_action_count": int(cycles[0]["after_action_count"]),
    }
    return source_meta, conditions["left"], conditions["right"], turns


def _condition_provenance(
    *,
    source_meta: Mapping[str, Any],
    condition: Mapping[str, Any],
    turns: Mapping[int, Mapping[str, Any]],
) -> MemoryAcquisitionProvenance:
    support_counts = sorted({
        int(count)
        for memory in condition["memories"]
        for count in memory.get("support_action_counts") or []
    })
    missing = [count for count in support_counts if count not in turns]
    if missing:
        raise ValueError(f"condition cites absent source turns: {missing}")
    support_sha256s = tuple(_sha(turns[count]) for count in support_counts)
    boundary_count = int(source_meta["boundary_action_count"])
    boundary_sha = _sha(turns[boundary_count])
    boundary_support = (
        (boundary_sha,) if boundary_sha in support_sha256s else ()
    )
    return MemoryAcquisitionProvenance(
        episode_sha256=_sha({
            "source_sha256": source_meta["source_sha256"],
            "through_action_count": boundary_count,
        }),
        observation_sha256=str(
            source_meta["source_boundary_observation_sha256"]
        ),
        controller_instance_sha256=_sha({
            "runtime_session": source_meta["source_runtime_session"],
        }),
        support_sha256s=support_sha256s,
        boundary_support_sha256s=boundary_support,
    )


def _condition_bundle_base(
    *,
    condition: Mapping[str, Any],
    provenance: MemoryAcquisitionProvenance,
    scope,
    source_meta: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "ztare-arc3-one-shot-memory-content-condition-v1",
        "condition_id": str(condition["condition_id"]),
        "source_result_sha256": str(source_meta["source_sha256"]),
        "acquisition_provenance": provenance.to_receipt(),
        "consumption_scope": scope.to_receipt(),
        "consumption_scope_sha256": scope.sha256,
        "memories": list(condition["memories"]),
    }


def _proposal(
    *,
    condition: Mapping[str, Any],
    digest: Mapping[str, Any],
    provenance: MemoryAcquisitionProvenance,
    scope,
    budget: int,
    rendered_bytes: int,
) -> DecisionInterventionProposal:
    guard_features = tuple(sorted({
        str(feature)
        for memory in condition["memories"]
        for feature in memory.get("guard_features") or []
    }))
    support_refs = tuple(
        f"sha256:{value}" for value in provenance.support_sha256s
    )
    boundary_refs = tuple(
        f"sha256:{value}"
        for value in provenance.boundary_support_sha256s
    )
    return DecisionInterventionProposal(
        intervention_kind="episodic_memory_bundle",
        provider_id=str(condition["condition_id"]),
        provider_revision_sha256=_sha({
            "memory_ids": list(condition["memory_ids"]),
            "source_episode": provenance.episode_sha256,
        }),
        rendered_content_sha256=_sha_payload(dict(digest)),
        # The subscription runtime does not expose its tokenizer.  UTF-8 bytes
        # are the exact presentation-cost unit used by this experiment.
        rendered_token_count=rendered_bytes,
        tokenizer_sha256=_sha({"cost_unit": "canonical_json_utf8_byte-v1"}),
        scope=scope,
        acquisition_provenance=provenance,
        predicted_decision_delta=float(
            condition["producer_predicted_decision_delta"]
        ),
        prompt_cost_per_token=0.0,
        primitive_action_cost=float(budget),
        authority_score=50.0,
        actionability_score=1.0,
        recency_score=1.0,
        guard_features=guard_features,
        semantic_features=tuple(sorted({
            token
            for memory in condition["memories"]
            for token in str(memory.get("claim") or "").lower().split()
        })),
        support_refs=support_refs,
        boundary_support_refs=boundary_refs,
        content_ref=f"memory_condition:{condition['condition_id']}",
    )


def _pair_orders(
    pair_count: int,
    seed: str,
    *,
    order_mode: str = "random",
) -> list[list[str]]:
    if order_mode == "left-first":
        return [["left", "right"] for _ in range(pair_count)]
    if order_mode == "right-first":
        return [["right", "left"] for _ in range(pair_count)]
    if order_mode == "alternating":
        return [
            ["left", "right"] if index % 2 == 0 else ["right", "left"]
            for index in range(pair_count)
        ]
    if order_mode != "random":
        raise ValueError(f"unsupported order mode: {order_mode}")
    rng = random.Random(str(seed))
    rows: list[list[str]] = []
    for _ in range(pair_count):
        row = ["left", "right"]
        rng.shuffle(row)
        rows.append(row)
    return rows


def _selector_assignments(
    *,
    credit_result_path: Path,
    condition_rows: tuple[
        tuple[
            dict[str, Any],
            dict[str, Any],
            DecisionInterventionProposal,
        ],
        ...,
    ],
    scope,
    rendered_bytes: int,
) -> tuple[
    tuple[
        dict[str, Any],
        dict[str, Any],
        DecisionInterventionProposal,
    ],
    tuple[
        dict[str, Any],
        dict[str, Any],
        DecisionInterventionProposal,
    ],
    dict[str, Any],
]:
    """Assign learned and producer-prior selectors to held-out duel arms."""

    source = json.loads(credit_result_path.read_text(encoding="utf-8"))
    source_core = dict(source)
    claimed_sha256 = str(source_core.pop("sha256", ""))
    if not claimed_sha256 or _sha(source_core) != claimed_sha256:
        raise ValueError("selector credit result hash mismatch")
    trained_state = wake_sleep_credit_state_from_receipt(
        source["final_credit_state"]
    )
    proposals = tuple(row[2] for row in condition_rows)
    learned = allocate_decision_interventions(
        trained_state,
        proposals,
        scope=scope,
        max_items=1,
        max_prompt_tokens=rendered_bytes,
        minimum_score=-2.0,
    )
    producer_prior = allocate_decision_interventions(
        WakeSleepCreditState(),
        proposals,
        scope=scope,
        max_items=1,
        max_prompt_tokens=rendered_bytes,
        minimum_score=-2.0,
    )
    if len(learned.selected_proposal_revision_sha256s) != 1:
        raise ValueError("trained selector did not choose exactly one proposal")
    if len(producer_prior.selected_proposal_revision_sha256s) != 1:
        raise ValueError(
            "producer-prior selector did not choose exactly one proposal"
        )
    learned_revision = learned.selected_proposal_revision_sha256s[0]
    producer_revision = (
        producer_prior.selected_proposal_revision_sha256s[0]
    )
    if learned_revision == producer_revision:
        raise ValueError(
            "trained and producer-prior selectors chose the same proposal"
        )
    by_revision = {
        row[2].intervention_revision_sha256: row
        for row in condition_rows
    }
    if learned_revision not in by_revision:
        raise ValueError("trained selector chose an unknown proposal")
    if producer_revision not in by_revision:
        raise ValueError("producer-prior selector chose an unknown proposal")
    receipt = {
        "kind": "heldout_selector_assignment",
        "source_result_ref": _relative_ref(credit_result_path),
        "source_result_sha256": claimed_sha256,
        "source_credit_state_sha256": str(
            source["final_credit_state"]["sha256"]
        ),
        "left_role": "outcome_trained_selector",
        "right_role": "producer_prior_selector",
        "learned_allocation": learned.to_receipt(),
        "producer_prior_allocation": producer_prior.to_receipt(),
    }
    return (
        by_revision[learned_revision],
        by_revision[producer_revision],
        {**receipt, "sha256": _sha(receipt)},
    )


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
    output_dir: Path,
    experiment_sha256: str,
    pair_index: int,
    side: str,
    condition_id: str,
    game_id: str,
    budget: int,
    model_id: str,
    reasoning_effort: str,
    timeout_seconds: float,
    expected_observation_sha256: str,
    digest: Mapping[str, Any],
    consumption_decision,
    consumption_receipt,
) -> dict[str, Any]:
    stem = f"pair_{pair_index:02d}_{side}_{condition_id}"
    arm_path = output_dir / "arms" / f"{stem}.json"
    if arm_path.exists():
        payload = json.loads(arm_path.read_text(encoding="utf-8"))
        if payload.get("experiment_sha256") != experiment_sha256:
            raise RuntimeError(f"arm checkpoint identity drift: {arm_path}")
        return payload
    turn_log = output_dir / "turns" / f"{stem}.jsonl"

    def observe(turn: Mapping[str, Any]) -> None:
        _append_jsonl(turn_log, {
            "schema": SCHEMA,
            "kind": "arm_turn_checkpoint",
            "experiment_sha256": experiment_sha256,
            "pair_index": pair_index,
            "side": side,
            "condition_id": condition_id,
            "turn": dict(turn),
        })

    probe = run_subscription_probe(
        adapter=ArcAgi3Adapter(game_id),
        game_id=game_id,
        budget=budget,
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
        resume_session=True,
        turn_observer=observe,
        initial_recall_digest=digest,
        initial_recall_consumption_receipt=(
            consumption_receipt.to_receipt()
        ),
    )
    if int(probe["actions_executed"]) != budget:
        raise RuntimeError("arm did not spend the fixed action budget")
    if (
        str(probe["observations"][0]["sha256"])
        != expected_observation_sha256
    ):
        raise RuntimeError("arm restored a different observation")
    sessions = {
        str(turn.get("session_id") or "")
        for turn in probe["turns"]
    }
    if len(sessions) != 1 or "" in sessions:
        raise RuntimeError("arm did not preserve one runtime session")
    injections = [
        turn["recall_injection"]
        for turn in probe["turns"]
        if turn.get("recall_injection") is not None
    ]
    if len(injections) != 1 or probe["turns"][0].get(
        "recall_injection"
    ) is None:
        raise RuntimeError("arm must inject once at decision zero")
    if (
        str(injections[0]["consumption_receipt_sha256"])
        != consumption_receipt.sha256
    ):
        raise RuntimeError("arm consumed the wrong recall receipt")
    runtime_session = next(iter(sessions))
    controller_instance = _controller_instance_sha256(
        experiment_sha256=experiment_sha256,
        pair_index=pair_index,
        assignment=condition_id,
    )
    payload = {
        "schema": SCHEMA,
        "kind": "pairwise_memory_content_arm",
        "experiment_sha256": experiment_sha256,
        "pair_index": pair_index,
        "side": side,
        "condition_id": condition_id,
        "controller_instance_sha256": controller_instance,
        "runtime_controller_instance_ref": runtime_session,
        "trajectory_sha256": _sha({
            "observations": probe["observations"],
            "turns": probe["turns"],
        }),
        "consumption_decision": consumption_decision.to_receipt(),
        "consumption_receipt": consumption_receipt.to_receipt(),
        "metrics": _outcome_metrics(probe),
        "probe": probe,
    }
    _atomic_json(arm_path, payload)
    print(json.dumps({
        "event": "pairwise_memory_content_arm_complete",
        "pair_index": pair_index,
        "side": side,
        "condition_id": condition_id,
        "levels_gained": probe["levels_gained"],
        "first_level_action": probe["first_level_action"],
        "runtime_session": runtime_session,
        "arm_path": _relative_ref(arm_path),
    }, sort_keys=True), flush=True)
    return payload


def _outcome(
    arm: Mapping[str, Any],
    *,
    proposal: DecisionInterventionProposal,
    stratum: RecallExperimentStratum,
    arm_path: Path,
) -> DecisionInterventionArmOutcome:
    metrics = arm["metrics"]
    return DecisionInterventionArmOutcome(
        stratum_sha256=stratum.sha256,
        proposal_revision_sha256=(
            proposal.intervention_revision_sha256
        ),
        arm_id=(
            f"pair-{int(arm['pair_index']):02d}-"
            f"{arm['condition_id']}"
        ),
        controller_instance_sha256=str(
            arm["controller_instance_sha256"]
        ),
        runtime_controller_instance_ref=str(
            arm["runtime_controller_instance_ref"]
        ),
        trajectory_sha256=str(arm["trajectory_sha256"]),
        external_outcome_ref=(
            f"{_relative_ref(arm_path)}#sha256={_file_sha256(arm_path)}"
        ),
        primitive_action_cost=stratum.primitive_action_cost,
        task_score=float(metrics["task_score"]),
        efficiency_score=float(metrics["efficiency_score"]),
        information_yield=float(metrics["information_yield"]),
        consumption_receipt_sha256=str(
            arm["consumption_receipt"]["sha256"]
        ),
    )


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    source_path = Path(args.source_result).resolve()
    spec_path = Path(args.spec).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_meta, left_condition, right_condition, turns = _load_source(
        source_path,
        spec_path,
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    scope = None
    if args.selector_credit_result:
        credit_result_path = Path(
            args.selector_credit_result
        ).resolve()
        credit_result = json.loads(
            credit_result_path.read_text(encoding="utf-8")
        )
        credit_core = dict(credit_result)
        claimed_credit_sha256 = str(credit_core.pop("sha256", ""))
        if (
            not claimed_credit_sha256
            or _sha(credit_core) != claimed_credit_sha256
        ):
            raise ValueError("selector credit result hash mismatch")
        wake_sleep_credit_state_from_receipt(
            credit_result["final_credit_state"]
        )
        scope_row = credit_result["pairs"][0]["stratum"]["scope"]
        scope = MemoryScope(
            task_sha256=str(scope_row["task_sha256"]),
            controller_sha256=str(scope_row["controller_sha256"]),
            context_sha256=str(scope_row["context_sha256"]),
            choice_set_sha256=str(scope_row["choice_set_sha256"]),
            action_vocabulary_sha256=str(
                scope_row["action_vocabulary_sha256"]
            ),
        )
    game_id = _resolve_game_id(args.game)
    initial_observation, action_arity = _initial_observation(
        game_id=game_id
    )
    current_scope = _sleep_memory_scope(
        game_id=game_id,
        model_id=args.model,
        reasoning_effort=args.reasoning_effort,
        boundary_observation=initial_observation,
        action_arity=action_arity,
    )
    if scope is not None and scope != current_scope:
        raise ValueError(
            "selector credit scope does not match the live decision scope"
        )
    scope = current_scope
    left_provenance = _condition_provenance(
        source_meta=source_meta,
        condition=left_condition,
        turns=turns,
    )
    right_provenance = _condition_provenance(
        source_meta=source_meta,
        condition=right_condition,
        turns=turns,
    )
    left_base = _condition_bundle_base(
        condition=left_condition,
        provenance=left_provenance,
        scope=scope,
        source_meta=source_meta,
    )
    right_base = _condition_bundle_base(
        condition=right_condition,
        provenance=right_provenance,
        scope=scope,
        source_meta=source_meta,
    )
    left_digest, right_digest, rendered_bytes = (
        _equalize_rendered_bytes(left_base, right_base)
    )
    left_proposal = _proposal(
        condition=left_condition,
        digest=left_digest,
        provenance=left_provenance,
        scope=scope,
        budget=args.budget,
        rendered_bytes=rendered_bytes,
    )
    right_proposal = _proposal(
        condition=right_condition,
        digest=right_digest,
        provenance=right_provenance,
        scope=scope,
        budget=args.budget,
        rendered_bytes=rendered_bytes,
    )
    selector_assignment = None
    if args.selector_credit_result:
        (
            learned_row,
            producer_prior_row,
            selector_assignment,
        ) = _selector_assignments(
            credit_result_path=Path(
                args.selector_credit_result
            ).resolve(),
            condition_rows=(
                (left_condition, left_digest, left_proposal),
                (right_condition, right_digest, right_proposal),
            ),
            scope=scope,
            rendered_bytes=rendered_bytes,
        )
        left_condition, left_digest, left_proposal = learned_row
        (
            right_condition,
            right_digest,
            right_proposal,
        ) = producer_prior_row
    orders = _pair_orders(
        args.pairs,
        args.seed,
        order_mode=args.order_mode,
    )
    manifest_core = {
        "schema": SCHEMA,
        "kind": "experiment_manifest",
        "game_id": game_id,
        "pairs": args.pairs,
        "budget_per_arm": args.budget,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "seed": args.seed,
        "order_mode": args.order_mode,
        "arm_orders": orders,
        "initial_observation": initial_observation,
        "scope": scope.to_receipt(),
        "source": source_meta,
        "spec": spec,
        "rendered_utf8_bytes_per_condition": rendered_bytes,
        "left_digest_sha256": _sha_payload(left_digest),
        "right_digest_sha256": _sha_payload(right_digest),
        "left_proposal": left_proposal.to_receipt(),
        "right_proposal": right_proposal.to_receipt(),
        "primary_score": {
            "task_weight": 0.8,
            "efficiency_weight": 0.2,
        },
        "success_criterion": (
            "left has greater total task score and positive composite delta "
            "in at least two of three pairs"
        ),
    }
    if selector_assignment is not None:
        manifest_core["selector_assignment"] = selector_assignment
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

    state = WakeSleepCreditState()
    pair_rows: list[dict[str, Any]] = []
    conditions = {
        "left": (
            left_condition,
            left_digest,
            left_proposal,
        ),
        "right": (
            right_condition,
            right_digest,
            right_proposal,
        ),
    }
    for pair_index, order in enumerate(orders, start=1):
        stratum = _stratum(
            scope=scope,
            game_id=game_id,
            observation_sha256=initial_observation["sha256"],
            budget=args.budget,
            seed=args.seed,
            pair_index=pair_index,
        )
        arm_rows: dict[str, dict[str, Any]] = {}
        recall_rows = {}
        decision_rows = {}
        consumption_rows = {}
        for side in ("left", "right"):
            condition, digest, proposal = conditions[side]
            candidate = proposal.to_memory_candidate()
            recall = select_sparse_memories(
                state,
                (candidate,),
                scope=scope,
                max_items=1,
                minimum_score=-2.0,
                max_prompt_tokens=rendered_bytes,
            )
            instance = _controller_instance_sha256(
                experiment_sha256=experiment_sha256,
                pair_index=pair_index,
                assignment=str(condition["condition_id"]),
            )
            decision = authorize_recall_consumption(
                recall,
                (candidate,),
                controller_instance_sha256=instance,
                observation_sha256=initial_observation["sha256"],
                decision_ref=(
                    f"pair-{pair_index:02d}:"
                    f"{condition['condition_id']}:decision-0"
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
                controller_instance_sha256=instance,
                observation_sha256=initial_observation["sha256"],
            )
            recall_rows[side] = recall
            decision_rows[side] = decision
            consumption_rows[side] = consumption
        for side in order:
            condition, digest, _proposal_row = conditions[side]
            arm_rows[side] = _run_arm(
                output_dir=output_dir,
                experiment_sha256=experiment_sha256,
                pair_index=pair_index,
                side=side,
                condition_id=str(condition["condition_id"]),
                game_id=game_id,
                budget=args.budget,
                model_id=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
                expected_observation_sha256=(
                    initial_observation["sha256"]
                ),
                digest=digest,
                consumption_decision=decision_rows[side],
                consumption_receipt=consumption_rows[side],
            )
        paths = {
            side: (
                output_dir
                / "arms"
                / (
                    f"pair_{pair_index:02d}_{side}_"
                    f"{conditions[side][0]['condition_id']}.json"
                )
            )
            for side in ("left", "right")
        }
        left_outcome = _outcome(
            arm_rows["left"],
            proposal=left_proposal,
            stratum=stratum,
            arm_path=paths["left"],
        )
        right_outcome = _outcome(
            arm_rows["right"],
            proposal=right_proposal,
            stratum=stratum,
            arm_path=paths["right"],
        )
        state, settlement = settle_pairwise_intervention_trial(
            state,
            stratum=stratum,
            left_proposal=left_proposal,
            right_proposal=right_proposal,
            left_recall=recall_rows["left"],
            right_recall=recall_rows["right"],
            left_decision=decision_rows["left"],
            right_decision=decision_rows["right"],
            left_consumption=consumption_rows["left"],
            right_consumption=consumption_rows["right"],
            left_outcome=left_outcome,
            right_outcome=right_outcome,
        )
        if settlement.status != "settled":
            raise RuntimeError(
                f"pair {pair_index} rejected: {settlement.reason}"
            )
        row = {
            "pair_index": pair_index,
            "arm_order": order,
            "stratum": stratum.to_receipt(),
            "left_recall": recall_rows["left"].to_receipt(),
            "right_recall": recall_rows["right"].to_receipt(),
            "left_consumption": consumption_rows["left"].to_receipt(),
            "right_consumption": consumption_rows["right"].to_receipt(),
            "left_outcome": left_outcome.to_receipt(stratum=stratum),
            "right_outcome": right_outcome.to_receipt(stratum=stratum),
            "settlement": settlement.to_receipt(),
        }
        pair_rows.append(row)
        _atomic_json(
            output_dir / "settlements" / f"pair_{pair_index:02d}.json",
            row,
        )

    task_delta = sum(
        float(row["settlement"]["observed_task_delta"])
        for row in pair_rows
    )
    decision_deltas = [
        float(row["settlement"]["observed_decision_delta"])
        for row in pair_rows
    ]
    information_deltas = [
        float(row["settlement"]["observed_information_yield_delta"])
        for row in pair_rows
    ]
    wins = sum(delta > 0.0 for delta in decision_deltas)
    mean_delta = sum(decision_deltas) / len(decision_deltas)
    predicted = (
        float(args.predicted_left_minus_right)
        if args.predicted_left_minus_right is not None
        else float(spec["pairwise_predicted_left_minus_right"])
    )
    if task_delta > 0 and wins >= 2:
        verdict = "supported"
    elif task_delta <= 0 and mean_delta <= 0:
        verdict = "rejected"
    else:
        verdict = "inconclusive"
    learned = allocate_decision_interventions(
        state,
        (left_proposal, right_proposal),
        scope=scope,
        max_items=1,
        max_prompt_tokens=rendered_bytes,
        minimum_score=-2.0,
    )
    result_core = {
        "schema": SCHEMA,
        "kind": "experiment_result",
        "status": "live_complete",
        "verdict": verdict,
        "experiment_sha256": experiment_sha256,
        "manifest_ref": _relative_ref(manifest_path),
        "pairs": pair_rows,
        "aggregate": {
            "pair_count": len(pair_rows),
            "left_total_task_score_minus_right": task_delta,
            "left_decision_score_wins": wins,
            "mean_observed_left_minus_right": mean_delta,
            "mean_information_yield_delta": (
                sum(information_deltas) / len(information_deltas)
            ),
            "predicted_left_minus_right": predicted,
            "prediction_squared_error": (predicted - mean_delta) ** 2,
            "primitive_action_cost_per_arm": float(args.budget),
            "rendered_utf8_bytes_per_condition": rendered_bytes,
        },
        "learned_allocation": learned.to_receipt(),
        "final_credit_state": state.to_receipt(),
        "claim_boundary": [
            "same public game and restored initial observation only",
            "conditions are evidence-selected memory bundles",
            "canonical JSON byte length is exact but model token count is unavailable",
            "three stochastic pairs are exploratory",
            *(
                [
                    "left condition was selected from a prior hash-bound "
                    "outcome-credit state; right used producer priors"
                ]
                if selector_assignment is not None
                else []
            ),
            "no cross-game or benchmark-wide claim",
        ],
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
    parser.add_argument("--pairs", type=int, default=3)
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
        default="h88-pairwise-memory-content-20260730",
    )
    parser.add_argument(
        "--order-mode",
        choices=("random", "left-first", "right-first", "alternating"),
        default="random",
    )
    parser.add_argument(
        "--selector-credit-result",
        default="",
    )
    parser.add_argument(
        "--predicted-left-minus-right",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--source-result",
        default=str(base / "h86_level_boundary_microsleep_result.json"),
    )
    parser.add_argument(
        "--spec",
        default=str(base / "h88_pairwise_memory_content_spec.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(base / "h88_pairwise_memory_content"),
    )
    args = parser.parse_args()
    if args.pairs <= 0:
        raise SystemExit("--pairs must be positive")
    if args.budget <= 0:
        raise SystemExit("--budget must be positive")
    bootstrap_dotenv_from_repo_root()
    result = run_experiment(args)
    print(json.dumps({
        "result_path": _relative_ref(
            Path(args.output_dir).resolve() / "result.json"
        ),
        "verdict": result["verdict"],
        "aggregate": result["aggregate"],
        "learned_selected": (
            result["learned_allocation"][
                "selected_proposal_revision_sha256s"
            ]
        ),
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
