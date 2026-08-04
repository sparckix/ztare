#!/usr/bin/env python3
"""Sealed synthetic falsifier for the Wake-Sleep Credit Router."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from typing import Any


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    CreditObservation,
    MemoryCandidate,
    MemoryScope,
    WakeSleepCreditState,
    feature_overlap,
    select_sparse_memories,
    select_static_authority_baseline,
    settle_recall_credit,
)


SEEDS = (7, 17, 29, 43, 71)
TRAINING_SETTLEMENTS = 80
HOLDOUT_DECISIONS = 400


def _scope(context: str = "sealed-compatible-context") -> MemoryScope:
    return MemoryScope(
        task_sha256="sealed-task-v1",
        controller_sha256="sealed-controller-v1",
        context_sha256=context,
        choice_set_sha256="sealed-choice-set-v1",
        action_vocabulary_sha256="sealed-actions-v1",
    )


def _candidates() -> tuple[MemoryCandidate, ...]:
    common = {
        "scope": _scope(),
        "retrieval_cost": 0.05,
        "primitive_action_cost": 11.0,
        "actionability_score": 1.0,
        "recency_score": 1.0,
    }
    return (
        MemoryCandidate(
            provider_id="lower-authority-causal",
            memory_revision_sha256="memory-causal-v1",
            predicted_decision_delta=0.20,
            authority_score=60,
            guard_features=("choice:two-way", "regime:alpha"),
            semantic_features=("route", "switch"),
            support_refs=("episode-1", "episode-2", "boundary-episode"),
            boundary_support_refs=("boundary-episode",),
            content_ref="sealed://causal",
            **common,
        ),
        MemoryCandidate(
            provider_id="high-authority-overlap-confuser",
            memory_revision_sha256="memory-authority-confuser-v1",
            predicted_decision_delta=0.80,
            authority_score=100,
            guard_features=("choice:two-way", "regime:alpha"),
            semantic_features=("surface-dissimilar",),
            support_refs=("episode-3", "episode-4"),
            content_ref="sealed://authority-confuser",
            **common,
        ),
        MemoryCandidate(
            provider_id="semantic-twin-disjoint-guard",
            memory_revision_sha256="memory-semantic-twin-v1",
            predicted_decision_delta=0.42,
            authority_score=80,
            guard_features=("choice:two-way", "regime:beta"),
            semantic_features=("route", "switch"),
            support_refs=("episode-5", "episode-6"),
            content_ref="sealed://semantic-twin",
            **common,
        ),
    )


def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _settle_training(
    state: WakeSleepCreditState,
    candidates: tuple[MemoryCandidate, ...],
    *,
    rng: random.Random,
    seed: int,
) -> WakeSleepCreditState:
    means = {
        "memory-causal-v1": 0.75,
        "memory-authority-confuser-v1": 0.48,
        "memory-semantic-twin-v1": 0.42,
    }
    for index in range(TRAINING_SETTLEMENTS):
        recall = select_sparse_memories(
            state,
            candidates,
            scope=_scope(),
            max_items=3,
            guard_overlap_weight=0.0,
            exploration_weight=0.05,
            minimum_score=-2.0,
        )
        for candidate in candidates:
            observed = _clip(
                rng.gauss(
                    means[candidate.memory_revision_sha256],
                    0.18,
                )
            )
            state, receipt = settle_recall_credit(
                state,
                candidates,
                recall=recall,
                observation=CreditObservation(
                    scope=_scope(),
                    memory_revision_sha256=(
                        candidate.memory_revision_sha256
                    ),
                    observed_decision_delta=observed,
                    external_outcome_ref=(
                        f"sealed:train:{seed}:{index}:"
                        f"{candidate.memory_revision_sha256}"
                    ),
                    matched_control_ref=(
                        f"sealed:ablation:{seed}:{index}:"
                        f"{candidate.memory_revision_sha256}"
                    ),
                    primitive_action_cost_before=(
                        candidate.primitive_action_cost
                    ),
                    primitive_action_cost_after=(
                        candidate.primitive_action_cost
                    ),
                ),
            )
            if receipt.status != "settled":
                raise RuntimeError(receipt.to_receipt())
    return state


def _heldout_regret(
    *,
    rng: random.Random,
    selected_revision: str,
) -> int:
    success_probability = {
        "memory-causal-v1": 0.82,
        "memory-authority-confuser-v1": 0.48,
        "memory-semantic-twin-v1": 0.43,
    }[selected_revision]
    return sum(
        rng.random() >= success_probability
        for _ in range(HOLDOUT_DECISIONS)
    )


def _seed_run(seed: int) -> dict[str, Any]:
    candidates = _candidates()
    causal, confuser, semantic_twin = candidates
    initial_state = WakeSleepCreditState()
    initial = select_sparse_memories(
        initial_state,
        candidates,
        scope=_scope(),
        max_items=1,
    )
    static = select_static_authority_baseline(
        candidates,
        scope=_scope(),
        max_items=1,
    )
    rng = random.Random(seed)
    state = _settle_training(
        initial_state,
        candidates,
        rng=rng,
        seed=seed,
    )
    learned = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=1,
        guard_overlap_weight=0.20,
    )
    without_guard_cost = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=2,
        guard_overlap_weight=0.0,
    )
    guarded_top2 = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=2,
        guard_overlap_weight=0.20,
    )
    router_revision = learned.selections[0].memory_revision_sha256
    static_revision = static[0].memory_revision_sha256
    heldout_seed = seed * 1009 + 3
    router_regret = _heldout_regret(
        rng=random.Random(heldout_seed),
        selected_revision=router_revision,
    )
    static_regret = _heldout_regret(
        rng=random.Random(heldout_seed),
        selected_revision=static_revision,
    )
    return {
        "seed": seed,
        "initial_top1": (
            initial.selections[0].memory_revision_sha256
        ),
        "static_top1": static_revision,
        "learned_top1": router_revision,
        "router_regret": router_regret,
        "static_regret": static_regret,
        "strict_regret_improvement": router_regret < static_regret,
        "top2_without_guard_overlap_cost": [
            row.memory_revision_sha256
            for row in without_guard_cost.selections
        ],
        "top2_with_guard_overlap_cost": [
            row.memory_revision_sha256
            for row in guarded_top2.selections
        ],
        "guard_overlap_causal_confuser": feature_overlap(
            causal.guard_features,
            confuser.guard_features,
        ),
        "semantic_overlap_causal_confuser": feature_overlap(
            causal.semantic_features,
            confuser.semantic_features,
        ),
        "guard_overlap_causal_semantic_twin": feature_overlap(
            causal.guard_features,
            semantic_twin.guard_features,
        ),
        "semantic_overlap_causal_semantic_twin": feature_overlap(
            causal.semantic_features,
            semantic_twin.semantic_features,
        ),
        "primitive_action_costs": {
            candidate.memory_revision_sha256: (
                candidate.primitive_action_cost
            )
            for candidate in candidates
        },
        "state": state.to_receipt(),
    }


def _boundary_checks(seed_row: dict[str, Any]) -> dict[str, Any]:
    candidates = _candidates()
    causal = candidates[0]
    state = WakeSleepCreditState(credits=tuple(
        _credit_from_receipt(row)
        for row in seed_row["state"]["credits"]
    ))
    recall = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=1,
        minimum_score=-2.0,
    )
    before_scope_sha = state.to_receipt()["sha256"]
    unchanged, mismatch = settle_recall_credit(
        state,
        candidates,
        recall=recall,
        observation=CreditObservation(
            scope=_scope("outside-context"),
            memory_revision_sha256=causal.memory_revision_sha256,
            observed_decision_delta=1.0,
            external_outcome_ref="sealed:outside-scope",
            matched_control_ref="sealed:outside-scope-control",
            primitive_action_cost_before=causal.primitive_action_cost,
            primitive_action_cost_after=causal.primitive_action_cost,
        ),
    )
    lifecycle_rows = []
    for index in range(1, 4):
        recall = select_sparse_memories(
            state,
            candidates,
            scope=_scope(),
            max_items=1,
            minimum_score=-2.0,
        )
        state, receipt = settle_recall_credit(
            state,
            candidates,
            recall=recall,
            observation=CreditObservation(
                scope=_scope(),
                memory_revision_sha256=causal.memory_revision_sha256,
                observed_decision_delta=-1.0,
                external_outcome_ref=f"sealed:contradiction:{index}",
                matched_control_ref=f"sealed:contradiction-control:{index}",
                primitive_action_cost_before=causal.primitive_action_cost,
                primitive_action_cost_after=causal.primitive_action_cost,
                authoritative_contradiction=True,
            ),
        )
        lifecycle_rows.append({
            "index": index,
            "lifecycle": state.credit_for(causal).lifecycle,
            "reopened_support_refs": list(
                state.credit_for(causal).reopened_support_refs
            ),
            "primitive_action_cost_before": (
                receipt.primitive_action_cost_before
            ),
            "primitive_action_cost_after": (
                receipt.primitive_action_cost_after
            ),
        })
    return {
        "outside_scope_status": mismatch.status,
        "outside_scope_reason": mismatch.reason,
        "outside_scope_state_unchanged": (
            unchanged.to_receipt()["sha256"] == before_scope_sha
        ),
        "lifecycle_rows": lifecycle_rows,
        "first_contradiction_reopened_only_boundary": (
            lifecycle_rows[0]["lifecycle"] == "probation"
            and lifecycle_rows[0]["reopened_support_refs"]
            == ["boundary-episode"]
        ),
        "third_contradiction_demoted": (
            lifecycle_rows[-1]["lifecycle"] == "demoted"
            and lifecycle_rows[-1]["reopened_support_refs"] == []
        ),
        "primitive_action_cost_invariant": all(
            row["primitive_action_cost_before"]
            == row["primitive_action_cost_after"]
            == causal.primitive_action_cost
            for row in lifecycle_rows
        ),
    }


def _credit_from_receipt(row: dict[str, Any]):
    from ztare.common.wake_sleep_credit_router import MemoryCredit

    return MemoryCredit(
        memory_key=row["memory_key"],
        settlement_count=row["settlement_count"],
        sum_observed_delta=row["sum_observed_delta"],
        sum_squared_prediction_error=(
            row["sum_squared_prediction_error"]
        ),
        compatible_contradictions=row["compatible_contradictions"],
        lifecycle=row["lifecycle"],
        reopened_support_refs=tuple(row["reopened_support_refs"]),
        last_external_outcome_ref=row["last_external_outcome_ref"],
    )


def run_audit() -> dict[str, Any]:
    rows = [_seed_run(seed) for seed in SEEDS]
    boundaries = _boundary_checks(rows[0])
    passed = (
        all(row["initial_top1"] == "memory-authority-confuser-v1" for row in rows)
        and all(row["static_top1"] == "memory-authority-confuser-v1" for row in rows)
        and all(row["learned_top1"] == "memory-causal-v1" for row in rows)
        and all(row["strict_regret_improvement"] for row in rows)
        and all(
            row["top2_without_guard_overlap_cost"][:2]
            == [
                "memory-causal-v1",
                "memory-authority-confuser-v1",
            ]
            for row in rows
        )
        and all(
            row["top2_with_guard_overlap_cost"][:2]
            == [
                "memory-causal-v1",
                "memory-semantic-twin-v1",
            ]
            for row in rows
        )
        and boundaries["outside_scope_state_unchanged"]
        and boundaries["first_contradiction_reopened_only_boundary"]
        and boundaries["third_contradiction_demoted"]
        and boundaries["primitive_action_cost_invariant"]
    )
    return {
        "schema": "ztare-wake-sleep-credit-router-audit-v1",
        "status": "pass" if passed else "fail",
        "environment_contact": False,
        "seeds": list(SEEDS),
        "training_settlements_per_memory": TRAINING_SETTLEMENTS,
        "holdout_decisions_per_seed": HOLDOUT_DECISIONS,
        "rows": rows,
        "boundary_checks": boundaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_audit()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
