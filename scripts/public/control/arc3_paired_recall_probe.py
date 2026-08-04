#!/usr/bin/env python3
"""Paired ARC recall/no-recall probe over restored initial prefixes.

Each pair creates two fresh resumed subscription controllers from the same
settled initial observation.  The inject arm receives one evidence-derived
memory bundle on its first decision only; the ablate arm does not.  Arm order
is sealed by a deterministic seed, both arms spend the same charged-action
budget, and every completed arm is checkpointed before the next begins.
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
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arc3_responses_agent_probe import (  # noqa: E402
    _resolve_game_id,
    _sleep_memory_scope,
    run_subscription_probe,
    settled_observation_receipt,
)
from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    MemoryAcquisitionProvenance,
    MemoryCandidate,
    RecallExperimentStratum,
    RecallTrialArmOutcome,
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    select_sparse_memories,
    settle_matched_recall_trial,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402


SCHEMA = "ztare-arc3-paired-one-shot-recall-probe-v1"


def _sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())


def _relative_ref(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def _pair_orders(pair_count: int, seed: str) -> list[list[str]]:
    rng = random.Random(str(seed))
    rows: list[list[str]] = []
    for _ in range(pair_count):
        order = ["inject", "ablate"]
        rng.shuffle(order)
        rows.append(order)
    return rows


def _initial_observation(
    *,
    game_id: str,
) -> tuple[dict[str, Any], int]:
    adapter = ArcAgi3Adapter(game_id)
    grid = adapter.reset()
    arity = int(adapter.action_arity)
    receipt = settled_observation_receipt(
        grid,
        observation_index=0,
        action_count=0,
        levels_completed=int(adapter.levels_completed),
        adapter_epoch=int(adapter.current_epoch),
        available_action_indices=tuple(range(arity)),
    )
    return receipt, arity


def _source_bundle(
    source_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    cycles = source.get("sleep_cycles") or []
    if len(cycles) != 1:
        raise ValueError("source result must contain exactly one sleep cycle")
    selected = cycles[0].get("selected_digest")
    if not isinstance(selected, dict):
        raise ValueError("source sleep cycle has no selected digest")
    memories = selected.get("memories") or []
    if not isinstance(memories, list) or not memories:
        raise ValueError("source selected digest has no memories")
    turns = source.get("turns") or []
    turn_by_count = {
        int(turn["action_count"]): dict(turn)
        for turn in turns
        if isinstance(turn, dict) and "action_count" in turn
    }
    support_counts = sorted({
        int(count)
        for memory in memories
        for count in memory.get("support_action_counts") or []
    })
    missing = [
        count for count in support_counts if count not in turn_by_count
    ]
    if missing:
        raise ValueError(f"source digest cites absent turns: {missing}")
    support_sha256s = tuple(
        _sha(turn_by_count[count]) for count in support_counts
    )
    boundary_count = int(cycles[0]["after_action_count"])
    boundary_support = (
        (_sha(turn_by_count[boundary_count]),)
        if boundary_count in turn_by_count
        else ()
    )
    session_ids = {
        str(turn.get("session_id") or "")
        for turn in turns
        if str(turn.get("session_id") or "")
    }
    if len(session_ids) != 1:
        raise ValueError(
            "source acquisition must have one controller runtime instance"
        )
    source_sha = _file_sha256(source_path)
    acquisition = MemoryAcquisitionProvenance(
        episode_sha256=_sha({
            "source_result_sha256": source_sha,
            "turn_sha256s": [
                _sha(turn_by_count[count])
                for count in sorted(turn_by_count)
                if count <= boundary_count
            ],
        }),
        observation_sha256=str(selected["scope"]["context_sha256"]),
        controller_instance_sha256=_sha({
            "runtime": "codex_subscription",
            "session_id": next(iter(session_ids)),
        }),
        support_sha256s=support_sha256s,
        boundary_support_sha256s=boundary_support,
    )
    bundle_content = {
        "source_digest_sha256": str(selected["source_digest_sha256"]),
        "memories": memories,
        "active_uncertainties": list(
            selected.get("active_uncertainties") or []
        ),
        "next_decision_questions": list(
            selected.get("next_decision_questions") or []
        ),
    }
    source_receipt = {
        "source_path": _relative_ref(source_path),
        "source_result_sha256": source_sha,
        "source_selected_digest_sha256": _sha(selected),
        "source_scope": dict(selected["scope"]),
        "acquisition": acquisition.to_receipt(),
        "bundle_revision_sha256": _sha(bundle_content),
        "bundle_content": bundle_content,
    }
    return source_receipt, selected


def _candidate_and_digest(
    *,
    source_receipt: Mapping[str, Any],
    selected_source_digest: Mapping[str, Any],
    scope,
    primitive_action_cost: float,
    predicted_decision_delta: float,
) -> tuple[MemoryCandidate, dict[str, Any], dict[str, Any]]:
    source_scope = dict(source_receipt["source_scope"])
    consumption_scope = scope.to_receipt()
    invariant_fields = (
        "task_sha256",
        "controller_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    )
    drift = [
        name
        for name in invariant_fields
        if source_scope.get(name) != consumption_scope.get(name)
    ]
    if drift:
        raise ValueError(
            "source-to-consumption transport drifted on invariants: "
            + ",".join(drift)
        )
    transport = {
        "schema": "ztare-recall-compatibility-transport-claim-v1",
        "source_scope_sha256": str(
            selected_source_digest["scope_sha256"]
        ),
        "target_scope_sha256": scope.sha256,
        "preserved_fields": list(invariant_fields),
        "transported_axes": [
            "episode",
            "controller_instance",
            "observation_context",
        ],
        "claim": (
            "supported game mechanics transport to the same task, controller "
            "class, choice set, and action vocabulary at a fresh initial "
            "observation; the paired trial prices this claim"
        ),
    }
    transport = {**transport, "sha256": _sha(transport)}
    acquisition_row = dict(source_receipt["acquisition"])
    acquisition = MemoryAcquisitionProvenance(
        episode_sha256=str(acquisition_row["episode_sha256"]),
        observation_sha256=str(acquisition_row["observation_sha256"]),
        controller_instance_sha256=str(
            acquisition_row["controller_instance_sha256"]
        ),
        support_sha256s=tuple(acquisition_row["support_sha256s"]),
        boundary_support_sha256s=tuple(
            acquisition_row["boundary_support_sha256s"]
        ),
    )
    memories = list(source_receipt["bundle_content"]["memories"])
    guard_features = tuple(sorted({
        str(feature)
        for memory in memories
        for feature in memory.get("guard_features") or []
    }))
    support_refs = tuple(
        f"sha256:{value}" for value in acquisition.support_sha256s
    )
    boundary_refs = tuple(
        f"sha256:{value}"
        for value in acquisition.boundary_support_sha256s
    )
    candidate = MemoryCandidate(
        provider_id="cross-episode-level-boundary-sleep",
        memory_revision_sha256=str(
            source_receipt["bundle_revision_sha256"]
        ),
        scope=scope,
        predicted_decision_delta=predicted_decision_delta,
        retrieval_cost=0.02,
        primitive_action_cost=primitive_action_cost,
        authority_score=50.0,
        actionability_score=1.0,
        recency_score=1.0,
        guard_features=guard_features,
        semantic_features=tuple(sorted({
            token
            for memory in memories
            for token in str(memory.get("claim") or "").lower().split()
        })),
        support_refs=support_refs,
        boundary_support_refs=boundary_refs,
        content_ref=(
            f"{source_receipt['source_path']}"
            "#sleep_cycles[0].selected_digest"
        ),
        acquisition_provenance=acquisition,
    )
    digest = {
        "schema": "ztare-arc3-one-shot-recall-bundle-v1",
        "memory_revision_sha256": candidate.memory_revision_sha256,
        "acquisition_provenance": acquisition.to_receipt(),
        "consumption_scope": consumption_scope,
        "consumption_scope_sha256": scope.sha256,
        "compatibility_transport": transport,
        **dict(source_receipt["bundle_content"]),
    }
    return candidate, digest, transport


def _prefix_sha256(
    *,
    game_id: str,
    observation_sha256: str,
) -> str:
    return _sha({
        "game_id": game_id,
        "history": [],
        "settled_observation_sha256": observation_sha256,
    })


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


def _controller_instance_sha256(
    *,
    experiment_sha256: str,
    pair_index: int,
    assignment: str,
) -> str:
    return _sha({
        "experiment_sha256": experiment_sha256,
        "pair_index": pair_index,
        "assignment": assignment,
        "kind": "fresh_resumed_subscription_controller",
    })


def _outcome_metrics(probe: Mapping[str, Any]) -> dict[str, Any]:
    budget = int(probe["budget"])
    first_level_action = probe.get("first_level_action")
    task_score = 1.0 if first_level_action is not None else 0.0
    efficiency_score = (
        (budget - int(first_level_action) + 1) / budget
        if first_level_action is not None
        else 0.0
    )
    unique_successors = {
        str(turn["successor_observation_sha256"])
        for turn in probe["turns"]
    }
    observation_novelty_yield = min(
        1.0,
        len(unique_successors) / budget,
    )
    return {
        "task_score": task_score,
        "efficiency_score": efficiency_score,
        "information_yield": observation_novelty_yield,
        "information_yield_measure": (
            "unique_settled_successor_observation_sha256s/action_budget"
        ),
        "unique_settled_successor_count": len(unique_successors),
    }


def _validate_probe(
    probe: Mapping[str, Any],
    *,
    assignment: str,
    expected_observation_sha256: str,
    budget: int,
    consumption_receipt_sha256: str,
) -> str:
    if int(probe["actions_executed"]) != budget:
        raise RuntimeError("arm did not spend the fixed primitive budget")
    if (
        str(probe["observations"][0]["sha256"])
        != expected_observation_sha256
    ):
        raise RuntimeError("arm restored a different initial observation")
    sessions = {
        str(turn.get("session_id") or "")
        for turn in probe["turns"]
    }
    if len(sessions) != 1 or "" in sessions:
        raise RuntimeError("arm did not use one exact resumed runtime session")
    recall_rows = [
        turn.get("recall_injection")
        for turn in probe["turns"]
        if turn.get("recall_injection") is not None
    ]
    if assignment == "inject":
        if len(recall_rows) != 1:
            raise RuntimeError(
                "inject arm must consume exactly one direct recall"
            )
        if (
            str(recall_rows[0]["consumption_receipt_sha256"])
            != consumption_receipt_sha256
        ):
            raise RuntimeError("inject arm consumed the wrong recall receipt")
        if probe["turns"][0].get("recall_injection") is None:
            raise RuntimeError("inject recall was not used at the prefix")
    elif recall_rows:
        raise RuntimeError("ablate arm received a recall injection")
    return next(iter(sessions))


def _run_arm(
    *,
    output_dir: Path,
    experiment_sha256: str,
    pair_index: int,
    assignment: str,
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
    arm_stem = f"pair_{pair_index:02d}_{assignment}"
    arm_path = output_dir / "arms" / f"{arm_stem}.json"
    if arm_path.exists():
        payload = json.loads(arm_path.read_text(encoding="utf-8"))
        if (
            payload.get("experiment_sha256") != experiment_sha256
            or payload.get("assignment") != assignment
        ):
            raise RuntimeError(f"checkpoint identity drift at {arm_path}")
        return payload
    turn_log = output_dir / "turns" / f"{arm_stem}.jsonl"

    def observe(turn: Mapping[str, Any]) -> None:
        _append_jsonl(
            turn_log,
            {
                "schema": SCHEMA,
                "kind": "arm_turn_checkpoint",
                "experiment_sha256": experiment_sha256,
                "pair_index": pair_index,
                "assignment": assignment,
                "turn": dict(turn),
            },
        )

    probe = run_subscription_probe(
        adapter=ArcAgi3Adapter(game_id),
        game_id=game_id,
        budget=budget,
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
        resume_session=True,
        turn_observer=observe,
        initial_recall_digest=(
            digest if assignment == "inject" else None
        ),
        initial_recall_consumption_receipt=(
            consumption_receipt.to_receipt()
            if assignment == "inject"
            else None
        ),
    )
    runtime_session = _validate_probe(
        probe,
        assignment=assignment,
        expected_observation_sha256=expected_observation_sha256,
        budget=budget,
        consumption_receipt_sha256=(
            consumption_receipt.sha256
            if assignment == "inject"
            else ""
        ),
    )
    controller_instance = _controller_instance_sha256(
        experiment_sha256=experiment_sha256,
        pair_index=pair_index,
        assignment=assignment,
    )
    trajectory = {
        "observations": probe["observations"],
        "turns": probe["turns"],
    }
    payload = {
        "schema": SCHEMA,
        "kind": "paired_recall_arm",
        "experiment_sha256": experiment_sha256,
        "pair_index": pair_index,
        "assignment": assignment,
        "controller_instance_sha256": controller_instance,
        "runtime_controller_instance_ref": runtime_session,
        "trajectory_sha256": _sha(trajectory),
        "consumption_decision": (
            consumption_decision.to_receipt()
            if assignment == "inject"
            else None
        ),
        "consumption_receipt": (
            consumption_receipt.to_receipt()
            if assignment == "inject"
            else None
        ),
        "metrics": _outcome_metrics(probe),
        "probe": probe,
    }
    _atomic_json(arm_path, payload)
    print(
        json.dumps({
            "event": "paired_recall_arm_complete",
            "pair_index": pair_index,
            "assignment": assignment,
            "levels_gained": probe["levels_gained"],
            "first_level_action": probe["first_level_action"],
            "runtime_session": runtime_session,
            "arm_path": _relative_ref(arm_path),
        }, sort_keys=True),
        flush=True,
    )
    return payload


def _arm_outcome(
    arm: Mapping[str, Any],
    *,
    stratum: RecallExperimentStratum,
    arm_path: Path,
) -> RecallTrialArmOutcome:
    metrics = arm["metrics"]
    receipt = arm.get("consumption_receipt") or {}
    return RecallTrialArmOutcome(
        stratum_sha256=stratum.sha256,
        arm_id=f"pair-{int(arm['pair_index']):02d}-{arm['assignment']}",
        assignment=str(arm["assignment"]),
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
        recall_consumption_sha256=str(receipt.get("sha256") or ""),
    )


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    game_id = _resolve_game_id(args.game)
    source_path = Path(args.source_result).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_receipt, selected_source_digest = _source_bundle(source_path)
    initial_observation, action_arity = _initial_observation(
        game_id=game_id
    )
    scope = _sleep_memory_scope(
        game_id=game_id,
        model_id=args.model,
        reasoning_effort=args.reasoning_effort,
        boundary_observation=initial_observation,
        action_arity=action_arity,
    )
    candidate, digest, transport = _candidate_and_digest(
        source_receipt=source_receipt,
        selected_source_digest=selected_source_digest,
        scope=scope,
        primitive_action_cost=float(args.budget),
        predicted_decision_delta=args.predicted_decision_delta,
    )
    orders = _pair_orders(args.pairs, args.seed)
    manifest_core = {
        "schema": SCHEMA,
        "kind": "experiment_manifest",
        "game_id": game_id,
        "pairs": args.pairs,
        "budget_per_arm": args.budget,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "seed": args.seed,
        "arm_orders": orders,
        "predicted_decision_delta": args.predicted_decision_delta,
        "primary_score": {
            "task_score_weight": 0.8,
            "efficiency_score_weight": 0.2,
            "task_score": "1 iff at least one level is gained",
            "efficiency_score": (
                "(budget-first_level_action+1)/budget, else 0"
            ),
        },
        "secondary_information_yield": (
            "unique settled successor observations / fixed action budget"
        ),
        "success_criterion": (
            "inject has greater total task score and wins the composite "
            "decision score in at least two of three pairs"
        ),
        "initial_observation": initial_observation,
        "initial_prefix_sha256": _prefix_sha256(
            game_id=game_id,
            observation_sha256=initial_observation["sha256"],
        ),
        "scope": scope.to_receipt(),
        "scope_sha256": scope.sha256,
        "source": source_receipt,
        "memory_candidate": candidate.to_receipt(),
        "compatibility_transport": transport,
        "one_shot_digest_sha256": _sha(digest),
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
            raise RuntimeError(
                "existing experiment manifest differs; use a new output dir"
            )
    else:
        _atomic_json(manifest_path, manifest)

    state = WakeSleepCreditState()
    pair_rows: list[dict[str, Any]] = []
    for pair_offset, order in enumerate(orders, start=1):
        stratum = _stratum(
            scope=scope,
            game_id=game_id,
            observation_sha256=initial_observation["sha256"],
            budget=args.budget,
            seed=args.seed,
            pair_index=pair_offset,
        )
        recall = select_sparse_memories(
            state,
            (candidate,),
            scope=scope,
            max_items=1,
            minimum_score=-2.0,
        )
        inject_instance = _controller_instance_sha256(
            experiment_sha256=experiment_sha256,
            pair_index=pair_offset,
            assignment="inject",
        )
        decision = authorize_recall_consumption(
            recall,
            (candidate,),
            controller_instance_sha256=inject_instance,
            observation_sha256=initial_observation["sha256"],
            decision_ref=f"pair-{pair_offset:02d}:inject:decision-0",
            compatibility_transport_sha256=str(transport["sha256"]),
        )
        _, consumption = consume_recall_once(
            decision,
            controller_instance_sha256=inject_instance,
            observation_sha256=initial_observation["sha256"],
        )
        arms: dict[str, dict[str, Any]] = {}
        for assignment in order:
            arms[assignment] = _run_arm(
                output_dir=output_dir,
                experiment_sha256=experiment_sha256,
                pair_index=pair_offset,
                assignment=assignment,
                game_id=game_id,
                budget=args.budget,
                model_id=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=args.timeout_seconds,
                expected_observation_sha256=(
                    initial_observation["sha256"]
                ),
                digest=digest,
                consumption_decision=decision,
                consumption_receipt=consumption,
            )
        inject_path = (
            output_dir / "arms" / f"pair_{pair_offset:02d}_inject.json"
        )
        ablate_path = (
            output_dir / "arms" / f"pair_{pair_offset:02d}_ablate.json"
        )
        inject = _arm_outcome(
            arms["inject"],
            stratum=stratum,
            arm_path=inject_path,
        )
        ablate = _arm_outcome(
            arms["ablate"],
            stratum=stratum,
            arm_path=ablate_path,
        )
        state, matched = settle_matched_recall_trial(
            state,
            (candidate,),
            recall=recall,
            consumption_decision=decision,
            consumption_receipt=consumption,
            stratum=stratum,
            inject=inject,
            ablate=ablate,
            memory_revision_sha256=candidate.memory_revision_sha256,
        )
        if matched.status != "settled":
            raise RuntimeError(
                f"pair {pair_offset} settlement rejected: {matched.reason}"
            )
        pair_row = {
            "pair_index": pair_offset,
            "arm_order": order,
            "stratum": stratum.to_receipt(),
            "recall": recall.to_receipt(),
            "consumption_decision": decision.to_receipt(),
            "consumption": consumption.to_receipt(),
            "inject": inject.to_receipt(stratum=stratum),
            "ablate": ablate.to_receipt(stratum=stratum),
            "matched_settlement": matched.to_receipt(),
        }
        pair_rows.append(pair_row)
        _atomic_json(
            output_dir / "settlements" / f"pair_{pair_offset:02d}.json",
            pair_row,
        )

    task_delta = sum(
        float(row["matched_settlement"]["observed_task_delta"])
        for row in pair_rows
    )
    decision_deltas = [
        float(row["matched_settlement"]["observed_decision_delta"])
        for row in pair_rows
    ]
    information_deltas = [
        float(
            row["matched_settlement"][
                "observed_information_yield_delta"
            ]
        )
        for row in pair_rows
    ]
    decision_wins = sum(delta > 0 for delta in decision_deltas)
    mean_decision_delta = sum(decision_deltas) / len(decision_deltas)
    mean_information_delta = (
        sum(information_deltas) / len(information_deltas)
    )
    if task_delta > 0 and decision_wins >= 2:
        verdict = "supported"
    elif task_delta <= 0 and mean_decision_delta <= 0:
        verdict = "rejected"
    else:
        verdict = "inconclusive"
    calibration_error = (
        args.predicted_decision_delta - mean_decision_delta
    ) ** 2
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
            "primitive_action_cost_per_arm": float(args.budget),
            "inject_total_task_score_minus_ablate": task_delta,
            "decision_score_wins": decision_wins,
            "mean_observed_decision_delta": mean_decision_delta,
            "mean_observed_information_yield_delta": (
                mean_information_delta
            ),
            "predicted_decision_delta": (
                args.predicted_decision_delta
            ),
            "prediction_squared_error": calibration_error,
        },
        "final_credit_state": state.to_receipt(),
        "claim_boundary": [
            "same public game and fresh initial observation only",
            "memory intervention is the three-item H86 bundle",
            "treatment includes extra prompt tokens",
            "three stochastic pairs are an exploratory discriminator",
            "no cross-game or benchmark-wide claim",
            "bundle test does not identify individual memory effects",
        ],
    }
    result = {**result_core, "sha256": _sha(result_core)}
    _atomic_json(output_dir / "result.json", result)
    return result


def main() -> int:
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
        "--predicted-decision-delta",
        type=float,
        default=0.20,
    )
    parser.add_argument(
        "--seed",
        default="h87-paired-one-shot-recall-20260730",
    )
    parser.add_argument(
        "--source-result",
        default=str(
            REPO
            / "research_areas/pre_registrations"
            / "arc3_consumer_indexed_exception_frontier_20260723"
            / "h86_level_boundary_microsleep_result.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            REPO
            / "research_areas/pre_registrations"
            / "arc3_consumer_indexed_exception_frontier_20260723"
            / "h87_paired_one_shot_recall"
        ),
    )
    args = parser.parse_args()
    if args.pairs <= 0:
        raise SystemExit("--pairs must be positive")
    if args.budget <= 0:
        raise SystemExit("--budget must be positive")
    if not -1.0 <= args.predicted_decision_delta <= 1.0:
        raise SystemExit("--predicted-decision-delta must be in [-1, 1]")
    bootstrap_dotenv_from_repo_root()
    result = run_experiment(args)
    print(json.dumps({
        "result_path": _relative_ref(
            Path(args.output_dir).resolve() / "result.json"
        ),
        "verdict": result["verdict"],
        "aggregate": result["aggregate"],
        "sha256": result["sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
