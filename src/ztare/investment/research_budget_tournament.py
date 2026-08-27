"""Shadow tournament for learning how to spend research dispatch capacity.

The tournament freezes counterfactual selections from an already-admissible
learning schedule.  It never changes that schedule, the work queue, or capital.
Later outcomes are scored per dispatch-cost unit; only repeated independent
blocks with multiplicity-controlled decision impact can recommend a scheduler
policy for review.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.information_yield_pricing import YieldComponents
from ztare.experiment_stats import paired_permutation_test

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .learning_scheduler import LEARNING_SCHEDULE_SCHEMA
from .research_decision_impact import (
    RESEARCH_DECISION_IMPACT_RECEIPT_SCHEMA,
    compile_candidate_proposal_decision_snapshot,
    compile_research_decision_impact_receipt,
    verify_research_decision_impact_receipt,
)


FREEZE_SCHEMA = "jaggedthoughts-research-budget-freeze-v1"
SETTLEMENT_SCHEMA = "jaggedthoughts-research-budget-settlement-v1"
REVIEW_SCHEMA = "jaggedthoughts-research-budget-review-v1"
MINIMUM_INDEPENDENT_BLOCKS = 8
PRIMARY_METRIC = "decision_impact_per_cost"
_METRICS = ("research_yield_per_cost", PRIMARY_METRIC)
_NO_YIELD_STAGES = {
    "awaiting_source_reassessment", "covered_by_prior_classification",
    "covered_by_prior_dossier", "failed", "research_blocked_invalid_evidence_time",
    "retry_queued", "superseded",
}


def _signed(payload: Mapping[str, Any], field: str, schema: str) -> dict[str, Any]:
    body = dict(payload)
    declared = require_text(body.pop(field, ""), field)
    if body.get("schema") != schema or stable_sha256(body) != declared:
        raise ValueError(f"invalid {schema} identity")
    return body


def _costs(actions: Sequence[Mapping[str, Any]], expected: Mapping[str, float]) -> dict[str, float]:
    result = {}
    for action in actions:
        work_id = require_text(action.get("work_id"), "research work_id")
        if work_id in result:
            raise ValueError(f"duplicate research work_id: {work_id}")
        cost = require_finite(expected.get(work_id, 1.0), f"expected cost for {work_id}")
        if cost <= 0:
            raise ValueError("expected dispatch cost must be positive")
        result[work_id] = cost
    return result


def _information_value(action: Mapping[str, Any], cost: float) -> float:
    components = action.get("components") if isinstance(action.get("components"), Mapping) else {}
    priced = YieldComponents(
        identification=float(components.get("law_scope_separation_upper_bound") or 0.0),
        compression_gain=float(components.get("law_scope_compression_upper_bound") or 0.0),
        novelty=float(components.get("unseen_entity_context") or 0.0),
    ).score(1 / 3, 1 / 3, 1 / 3)
    sampling_gap = float(components.get("cohort_sampling_gap_upper_bound") or 0.0)
    world_model_value = (
        float(components.get("world_model_control_disagreement_upper_bound") or 0.0)
        + float(components.get("world_model_cross_dimension_upper_bound") or 0.0)
        + float(components.get("prospective_evidence_strength") or 0.0)
    ) / 3.0
    constraint_value = (
        float(components.get("constraint_discrimination_upper_bound") or 0.0)
        + float(components.get("constraint_falsification_surface_upper_bound") or 0.0)
        + float(components.get("source_disjoint_replay_readiness") or 0.0)
    ) / 3.0
    redundancy = float(action.get("redundancy_penalty") or 0.0)
    value = max(
        0.5 * priced + 0.5 * sampling_gap, world_model_value, constraint_value,
    )
    return max(0.0, value - redundancy) / cost


def freeze_research_budget_tournament(
    schedule: Mapping[str, Any],
    *,
    frozen_at: str,
    inference_block_id: str,
    capacity: int = 1,
    expected_dispatch_cost_units: Mapping[str, float] | None = None,
    decision_before_by_work: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Freeze four policy selections without mutating the source schedule."""

    source = _signed(schedule, "schedule_sha256", LEARNING_SCHEDULE_SCHEMA)
    frozen = canonical_timestamp(frozen_at, "research budget frozen_at")
    generated = canonical_timestamp(source.get("generated_at"), "source schedule generated_at")
    if timestamp_key(generated) > timestamp_key(frozen):
        raise ValueError("research budget freeze cannot precede its source schedule")
    if isinstance(capacity, bool) or capacity < 1:
        raise ValueError("research budget capacity must be a positive integer")
    block_id = require_text(inference_block_id, "research budget inference_block_id")
    actions = [dict(row) for row in source.get("actions") or () if isinstance(row, Mapping)]
    if capacity > len(actions):
        raise ValueError("research budget capacity exceeds eligible work")
    costs = _costs(actions, expected_dispatch_cost_units or {})

    def decision_proximity(row: Mapping[str, Any]) -> float:
        components = row.get("components") if isinstance(row.get("components"), Mapping) else {}
        return float(components.get("decision_proximity_prior") or 0.0) / costs[str(row["work_id"])]

    def mandate_relevance(row: Mapping[str, Any]) -> float:
        relevance = row.get("mandate_decision_relevance")
        relevance = relevance if isinstance(relevance, Mapping) else {}
        if relevance.get("scoreable") is not True:
            return 0.0
        return float(relevance.get("maximum_planning_weight_upper_bound") or 0.0) / costs[str(row["work_id"])]

    def mandate_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        relevance = row.get("mandate_decision_relevance")
        relevance = relevance if isinstance(relevance, Mapping) else {}
        return (
            relevance.get("scoreable") is not True,
            -mandate_relevance(row),
            -float(relevance.get("decision_class_coverage_fraction") or 0.0),
            int(row.get("queue_created_at_epoch") or 0),
            str(row["work_id"]),
        )

    policies = [
        ("current_priority", "current", lambda row: (int(row.get("rank") or 10**9), str(row["work_id"])), lambda row: float(row.get("ranking_score") or 0.0)),
        ("fifo", "cheap_baseline", lambda row: (int(row.get("queue_created_at_epoch") or 0), str(row["work_id"])), lambda row: -float(row.get("queue_created_at_epoch") or 0)),
        ("decision_proximity", "cheap_baseline", lambda row: (-decision_proximity(row), int(row.get("queue_created_at_epoch") or 0), str(row["work_id"])), decision_proximity),
        ("information_value_per_cost", "challenger", lambda row: (-_information_value(row, costs[str(row["work_id"])]), int(row.get("queue_created_at_epoch") or 0), str(row["work_id"])), lambda row: _information_value(row, costs[str(row["work_id"])])),
    ]
    if any(
        isinstance(row.get("mandate_decision_relevance"), Mapping)
        and row["mandate_decision_relevance"].get("scoreable") is True
        for row in actions
    ):
        policies.append((
            "mandate_decision_relevance_per_cost", "challenger",
            mandate_key, mandate_relevance,
        ))
    arms = []
    for policy_id, policy_class, key, score in policies:
        ranked = sorted(actions, key=key)
        selected = []
        for rank, row in enumerate(ranked[:capacity], start=1):
            work_id = str(row["work_id"])
            item = {
                "work_id": work_id,
                "source_rank": row.get("rank"),
                "policy_rank": rank,
                "policy_score": round(score(row), 8),
                "expected_dispatch_cost_units": costs[work_id],
            }
            if work_id in (decision_before_by_work or {}):
                item["decision_before"] = dict(decision_before_by_work[work_id])
            selected.append(item)
        arms.append({
            "policy_id": policy_id,
            "policy_class": policy_class,
            "selected": selected,
            "selected_work_ids": [row["work_id"] for row in selected],
        })
    body = {
        "schema": FREEZE_SCHEMA,
        "status": "frozen_awaiting_outcomes",
        "frozen_at": frozen,
        "inference_block_id": block_id,
        "source_schedule_sha256": schedule["schedule_sha256"],
        "eligible_snapshot_sha256": stable_sha256(actions),
        "eligible_work_count": len(actions),
        "capacity_per_policy": capacity,
        "expected_cost_contract": (
            "caller-supplied positive units; unspecified subscription dispatches equal one unit"
        ),
        "arms": arms,
        "future_policy_gate": {
            "primary_metric": PRIMARY_METRIC,
            "minimum_independent_blocks": MINIMUM_INDEPENDENT_BLOCKS,
            "multiplicity": "holm_fwer_over_all_policy_metric_comparisons",
            "alpha": 0.05,
            "decision_impact_evidence_schema": RESEARCH_DECISION_IMPACT_RECEIPT_SCHEMA,
        },
        "authority": "shadow_research_scheduler_evaluation_only",
        "queue_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "freeze_sha256": stable_sha256(body)}


def settle_research_budget_block(
    freeze: Mapping[str, Any],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    settled_at: str,
) -> dict[str, Any]:
    """Settle one frozen block; missing outcomes remain censored."""

    source = _signed(freeze, "freeze_sha256", FREEZE_SCHEMA)
    settled = canonical_timestamp(settled_at, "research budget settled_at")
    frozen = timestamp_key(str(source["frozen_at"]))
    settlement_time = timestamp_key(settled)
    if settlement_time < frozen:
        raise ValueError("research budget settlement cannot precede its freeze")
    eligible = {
        str(item["work_id"])
        for arm in source["arms"]
        for item in arm.get("selected") or ()
    }
    indexed: dict[str, dict[str, Any]] = {}
    for raw in outcomes:
        row = dict(raw)
        work_id = require_text(row.get("work_id"), "research outcome work_id")
        if work_id not in eligible or work_id in indexed:
            raise ValueError(f"unknown or duplicate research outcome: {work_id}")
        observed_at = canonical_timestamp(row.get("observed_at"), "research outcome observed_at")
        observed_time = timestamp_key(observed_at)
        if observed_time < frozen or observed_time > settlement_time:
            raise ValueError("research outcome must fall between freeze and settlement")
        cost = require_finite(row.get("dispatch_cost_units"), "dispatch_cost_units")
        research_yield = row.get("research_yield_observed")
        decision_changed_claimed = row.get("decision_changed")
        if cost <= 0 or not isinstance(research_yield, bool) or not isinstance(decision_changed_claimed, bool):
            raise ValueError("outcomes require positive cost and boolean yield/decision observations")
        evidence_ref = require_text(row.get("evidence_ref"), "research outcome evidence_ref")
        evidence_sha256 = row.get("evidence_sha256")
        decision_ref = row.get("decision_ref")
        impact_receipt = row.get("decision_impact_receipt")
        verified_impact = None
        impact_status = "no_verified_decision_impact"
        if impact_receipt is not None:
            try:
                verified_impact = verify_research_decision_impact_receipt(
                    impact_receipt, research_budget_freeze=freeze,
                    work_id=work_id, evidence_ref=evidence_ref,
                    evidence_sha256=str(evidence_sha256 or ""),
                )
            except (KeyError, TypeError, ValueError):
                impact_receipt = None
                impact_status = "invalid_decision_impact_receipt"
        decision_changed = bool(
            research_yield and verified_impact is not None
            and verified_impact.get("decision_changed") is True
        )
        if verified_impact is not None:
            impact_status = (
                "verified_changed_decision" if decision_changed
                else "verified_unchanged_decision"
            )
        elif decision_changed_claimed and impact_status == "no_verified_decision_impact":
            impact_status = "unverified_decision_claim_ignored"
        indexed[work_id] = {
            "work_id": work_id,
            "observed_at": observed_at,
            "dispatch_cost_units": cost,
            "research_yield_observed": research_yield,
            "decision_changed": decision_changed,
            "decision_changed_claimed": decision_changed_claimed,
            "evidence_ref": evidence_ref,
            "evidence_sha256": evidence_sha256,
            "decision_ref": decision_ref,
            "decision_impact_receipt": impact_receipt,
            "decision_impact_status": impact_status,
        }
    arm_results = []
    for arm in source["arms"]:
        work_ids = list(arm["selected_work_ids"])
        observed = [indexed[work_id] for work_id in work_ids if work_id in indexed]
        complete = len(observed) == len(work_ids)
        cost = sum(row["dispatch_cost_units"] for row in observed)
        arm_results.append({
            "policy_id": arm["policy_id"],
            "selected_count": len(work_ids),
            "observed_count": len(observed),
            "complete": complete,
            "research_yield_per_cost": (
                round(sum(row["research_yield_observed"] for row in observed) / cost, 8)
                if complete and cost else None
            ),
            "decision_impact_per_cost": (
                round(sum(row["decision_changed"] for row in observed) / cost, 8)
                if complete and cost else None
            ),
            "dispatch_cost_units": round(cost, 8),
            "missing_work_ids": [work_id for work_id in work_ids if work_id not in indexed],
        })
    body = {
        "schema": SETTLEMENT_SCHEMA,
        "status": "complete_block" if all(row["complete"] for row in arm_results) else "censored_pending_outcomes",
        "settled_at": settled,
        "inference_block_id": source["inference_block_id"],
        "source_schedule_sha256": source["source_schedule_sha256"],
        "freeze_sha256": freeze["freeze_sha256"],
        "outcomes": sorted(indexed.values(), key=lambda row: row["work_id"]),
        "arm_results": arm_results,
        "outcome_contract": (
            "research yield means a source-bound result resolved, falsified, or materially narrowed "
            "the frozen question; completion and source counts alone do not qualify"
        ),
        "decision_impact_contract": (
            "A decision reference or asserted boolean earns no credit. Positive impact requires "
            "a freeze-bound receipt joining the exact evidence digest to a changed typed decision."
        ),
        "boundary": "Missing work is censored; research yield cannot substitute for decision impact.",
        "authority": "shadow_research_scheduler_evaluation_only",
        "queue_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "settlement_sha256": stable_sha256(body)}


def compile_research_budget_review(
    settlements: Sequence[Mapping[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Compare policies by independent block and enforce the promotion gate."""

    generated = canonical_timestamp(generated_at, "research budget review generated_at")
    review_time = timestamp_key(generated)
    complete: dict[str, dict[str, Any]] = {}
    seen_blocks: set[str] = set()
    seen_schedules: set[str] = set()
    for raw in settlements:
        row = _signed(raw, "settlement_sha256", SETTLEMENT_SCHEMA)
        if timestamp_key(str(row["settled_at"])) > review_time:
            raise ValueError("research budget review cannot consume a future settlement")
        block_id = require_text(row.get("inference_block_id"), "inference_block_id")
        schedule_id = require_text(row.get("source_schedule_sha256"), "source_schedule_sha256")
        if block_id in seen_blocks or schedule_id in seen_schedules:
            raise ValueError(f"duplicate inference block or schedule: {block_id}")
        seen_blocks.add(block_id)
        seen_schedules.add(schedule_id)
        if row.get("status") == "complete_block":
            complete[block_id] = row
    policy_ids = sorted({
        str(result["policy_id"])
        for row in complete.values() for result in row.get("arm_results") or ()
    })
    comparisons = []
    for policy_id in policy_ids:
        if policy_id == "current_priority":
            continue
        for metric in _METRICS:
            challenger, current = [], []
            for row in complete.values():
                results = {str(result["policy_id"]): result for result in row["arm_results"]}
                if policy_id in results and "current_priority" in results:
                    challenger.append(float(results[policy_id][metric]))
                    current.append(float(results["current_priority"][metric]))
            inference = paired_permutation_test(
                challenger, current,
                seed=int(stable_sha256([policy_id, metric, challenger, current])[:8], 16),
            )
            comparisons.append({
                "comparison_id": f"{policy_id}__vs__current_priority__{metric}",
                "policy_id": policy_id,
                "metric": metric,
                "independent_block_count": len(challenger),
                "paired_inference": inference,
            })
    p_values = sorted(
        (float(comparison["paired_inference"]["p_value"]), comparison["comparison_id"])
        for comparison in comparisons
        if comparison["paired_inference"].get("p_value") is not None
    )
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (raw_p, comparison_id) in enumerate(p_values):
        running = max(running, min(1.0, raw_p * (len(p_values) - rank)))
        adjusted[comparison_id] = running
    eligible = []
    for comparison in comparisons:
        inference = comparison["paired_inference"]
        adjusted_p = adjusted.get(comparison["comparison_id"])
        comparison["multiplicity"] = {
            "method": "holm_fwer", "family_size": len(p_values),
            "adjusted_p_value": round(adjusted_p, 8) if adjusted_p is not None else None,
            "rejected_at_alpha": adjusted_p is not None and adjusted_p <= 0.05,
        }
        comparison["future_policy_review_eligible"] = bool(
            comparison["metric"] == PRIMARY_METRIC
            and comparison["independent_block_count"] >= MINIMUM_INDEPENDENT_BLOCKS
            and comparison["multiplicity"]["rejected_at_alpha"]
            and float(inference.get("observed_delta") or 0) > 0
            and inference.get("ci_lo") is not None and float(inference["ci_lo"]) > 0
        )
        if comparison["future_policy_review_eligible"]:
            eligible.append(comparison)
    recommended = max(
        eligible, key=lambda row: float(row["paired_inference"]["observed_delta"]),
        default=None,
    )
    body = {
        "schema": REVIEW_SCHEMA,
        "generated_at": generated,
        "complete_independent_block_count": len(complete),
        "minimum_independent_blocks": MINIMUM_INDEPENDENT_BLOCKS,
        "primary_metric": PRIMARY_METRIC,
        "comparisons": comparisons,
        "status": (
            "future_scheduler_policy_review_eligible" if recommended
            else "no_scheduler_change_authorized"
        ),
        "recommended_policy_id": recommended["policy_id"] if recommended else None,
        "exact_blocker": (
            None if recommended else
            "requires at least eight complete independent blocks and a positive decision-impact-per-cost contrast surviving multiplicity control"
        ),
        "authority": "future_scheduler_policy_review_recommendation_only",
        "queue_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "review_sha256": stable_sha256(body)}


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _proposal_snapshot(
    root: Path, row: Mapping[str, Any], *, captured_at: str,
    required_dossier_sha256: str | None = None,
) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    kind = str(row.get("kind") or "")
    entity_kind = str(payload.get("entity_kind") or "")
    if kind != "jaggedthoughts_subscription_research" or entity_kind not in {
        "public_equity", "public_fund",
    }:
        raise ValueError("work has no candidate paper-proposal decision surface")
    directory = "equities" if entity_kind == "public_equity" else "funds"
    relative = Path("paper_proposals") / directory / "latest.json"
    audit = json.loads((root / relative).read_text(encoding="utf-8"))
    return compile_candidate_proposal_decision_snapshot(
        audit,
        candidate_leaf=require_text(payload.get("candidate_leaf"), "research candidate leaf"),
        source_artifact_ref=f"{relative.as_posix()}#{audit['audit_sha256']}",
        captured_at=captured_at,
        required_dossier_sha256=required_dossier_sha256,
    )


def _terminal_outcome(
    root: Path, row: Mapping[str, Any], *, freeze: Mapping[str, Any], settled_at: str,
) -> dict[str, Any] | None:
    """Turn one terminal queue row into a conservative, inspectable outcome."""

    status = str(row.get("status") or "")
    if status not in {"done", "dead_letter"}:
        return None
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    completed = payload.get("completed_at")
    if not completed and row.get("updated_at"):
        completed = datetime.fromtimestamp(
            int(row["updated_at"]), timezone.utc,
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
    observed_at = canonical_timestamp(
        completed or settled_at, "research budget outcome observed_at",
    )
    if timestamp_key(observed_at) < timestamp_key(str(freeze["frozen_at"])):
        return None

    stage = str(payload.get("stage") or "")
    artifact_pairs = (
        ("result_path", "result_sha256"),
        ("reassessment_path", "reassessment_sha256"),
        ("dossier_path", "dossier_sha256"),
        ("output_path", "output_sha256"),
    )
    evidence_ref = next((
        f"{payload[path_key]}#{payload[sha_key]}"
        for path_key, sha_key in artifact_pairs
        if payload.get(path_key) and payload.get(sha_key)
    ), None)
    evidence_sha256 = next((
        str(payload[sha_key]) for path_key, sha_key in artifact_pairs
        if payload.get(path_key) and payload.get(sha_key)
    ), None)
    leaf = next((
        str(payload[key]) for key in (
            "accepted_reassessment_leaf", "reassessment_leaf", "coverage_leaf",
            "result_leaf", "dossier_leaf",
        ) if payload.get(key)
    ), None)
    if evidence_ref is None and leaf:
        evidence_ref = f"golden-store:{leaf}"
        evidence_sha256 = leaf if len(leaf) == 64 else None
    research_yield = bool(
        status == "done" and stage not in _NO_YIELD_STAGES and evidence_ref
    )
    if evidence_ref is None:
        evidence_ref = (
            f"work-queue:{row.get('work_id')}:{status}:"
            f"{stable_sha256({'stage': stage, 'payload': payload})}"
        )

    decision_ref = next((str(payload[key]) for key in (
        "decision_ref", "paper_watch_decision_sha256", "decision_record_sha256",
        "decision_sha256", "decision_id",
    ) if payload.get(key)), None)
    impact_receipt = payload.get("research_decision_impact_receipt")
    selected_item = next((
        item for arm in freeze.get("arms") or () for item in arm.get("selected") or ()
        if item.get("work_id") == row.get("work_id") and item.get("decision_before")
    ), None)
    if (
        impact_receipt is None and research_yield and evidence_sha256
        and selected_item is not None
    ):
        try:
            after = _proposal_snapshot(
                root, row, captured_at=settled_at,
                required_dossier_sha256=str(evidence_sha256),
            )
            impact_receipt = compile_research_decision_impact_receipt(
                research_budget_freeze=freeze,
                work_id=str(row.get("work_id") or ""),
                evidence_ref=evidence_ref,
                evidence_sha256=str(evidence_sha256),
                evidence_available_at=observed_at,
                decision_before=selected_item["decision_before"],
                decision_after=after,
                consumed_at=after["captured_at"],
            )
            decision_ref = after["source_artifact_ref"]
        except (KeyError, OSError, TypeError, ValueError):
            impact_receipt = None
    impact_status = "no_verified_decision_impact"
    decision_changed = False
    if isinstance(impact_receipt, Mapping):
        try:
            verified = verify_research_decision_impact_receipt(
                impact_receipt, research_budget_freeze=freeze,
                work_id=str(row.get("work_id") or ""), evidence_ref=evidence_ref,
                evidence_sha256=str(evidence_sha256 or ""),
            )
            decision_changed = bool(research_yield and verified["decision_changed"])
            impact_status = (
                "verified_changed_decision" if decision_changed
                else "verified_unchanged_decision"
            )
        except (KeyError, TypeError, ValueError):
            impact_receipt = None
            impact_status = "invalid_decision_impact_receipt"
    return {
        "work_id": require_text(row.get("work_id"), "research work_id"),
        "observed_at": observed_at,
        "dispatch_cost_units": next((
            float(item.get("expected_dispatch_cost_units") or 1.0)
            for arm in freeze.get("arms") or () for item in arm.get("selected") or ()
            if item.get("work_id") == row.get("work_id")
        ), 1.0),
        "research_yield_observed": research_yield,
        "decision_changed": decision_changed,
        "evidence_ref": evidence_ref,
        "evidence_sha256": evidence_sha256,
        "decision_ref": decision_ref if research_yield else None,
        "decision_impact_receipt": impact_receipt,
        "decision_impact_status": impact_status,
    }


def advance_research_budget_tournament(
    workspace: str | Path,
    schedule: Mapping[str, Any],
    queue_rows: Sequence[Mapping[str, Any]],
    *,
    advanced_at: str,
    capacity: int = 1,
) -> dict[str, Any]:
    """Settle the current shadow block and freeze the next eligible queue epoch."""

    root = Path(workspace).expanduser().resolve()
    current = root / "institutional_learning" / "research_budget_tournament" / "current"
    runs = root / "institutional_learning" / "research_budget_tournament" / "runs"
    epoch = canonical_timestamp(advanced_at, "research budget advanced_at")
    by_id = {str(row.get("work_id") or ""): row for row in queue_rows}
    freeze_path = current / "freeze.json"
    settlement_path = current / "settlement.json"
    current_freeze = (
        json.loads(freeze_path.read_text(encoding="utf-8"))
        if freeze_path.is_file() else None
    )
    current_settlement = None
    if current_freeze is not None:
        freeze_body = _signed(current_freeze, "freeze_sha256", FREEZE_SCHEMA)
        selected_ids = sorted({
            str(item["work_id"])
            for arm in freeze_body["arms"] for item in arm.get("selected") or ()
        })
        outcomes = [
            outcome for work_id in selected_ids
            if (row := by_id.get(work_id)) is not None
            if (outcome := _terminal_outcome(root, row, freeze=current_freeze, settled_at=epoch))
            is not None
        ]
        current_settlement = settle_research_budget_block(
            current_freeze, outcomes, settled_at=epoch,
        )
        run_dir = runs / str(freeze_body["source_schedule_sha256"])
        for base in (current, run_dir):
            _write(base / "freeze.json", current_freeze)
            _write(base / "settlement.json", current_settlement)

    settlements = []
    for path in sorted(runs.glob("*/settlement.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") == SETTLEMENT_SCHEMA:
            settlements.append(payload)
    review = compile_research_budget_review(settlements, generated_at=epoch)

    should_freeze = current_freeze is None or (
        current_settlement is not None
        and current_settlement.get("status") == "complete_block"
        and current_freeze.get("source_schedule_sha256") != schedule.get("schedule_sha256")
    )
    if should_freeze and schedule.get("actions"):
        decision_before = {}
        for row in queue_rows:
            try:
                decision_before[str(row.get("work_id") or "")] = _proposal_snapshot(
                    root, row, captured_at=epoch,
                )
            except (KeyError, OSError, TypeError, ValueError):
                continue
        candidate = freeze_research_budget_tournament(
            schedule, frozen_at=epoch,
            inference_block_id=f"scheduler-{str(schedule['schedule_sha256'])}",
            capacity=capacity,
            decision_before_by_work=decision_before,
        )
        selected = {
            str(item["work_id"])
            for arm in candidate["arms"] for item in arm.get("selected") or ()
        }
        if all((by_id.get(work_id) or {}).get("status") in {"queued", "claimed"} for work_id in selected):
            current_freeze = candidate
            current_settlement = settle_research_budget_block(
                candidate, (), settled_at=epoch,
            )
            run_dir = runs / str(candidate["source_schedule_sha256"])
            for base in (current, run_dir):
                _write(base / "freeze.json", candidate)
                _write(base / "settlement.json", current_settlement)

    if current_freeze is not None:
        run_dir = runs / str(current_freeze["source_schedule_sha256"])
        _write(run_dir / "latest.json", review)
    _write(current / "latest.json", review)
    return research_budget_tournament_status(root)


def research_budget_tournament_status(workspace: str | Path) -> dict[str, Any]:
    """Project the current signed shadow block without changing its queue."""

    root = Path(workspace).expanduser().resolve()
    current = root / "institutional_learning" / "research_budget_tournament" / "current"
    paths = {
        "freeze": current / "freeze.json",
        "settlement": current / "settlement.json",
        "review": current / "latest.json",
    }
    if not all(path.is_file() for path in paths.values()):
        return {
            "schema": "jaggedthoughts-research-budget-tournament-status-v1",
            "enabled": False,
            "status": "awaiting_first_frozen_schedule",
            "capital_authority": False,
            "queue_mutation_authority": False,
        }
    freeze = json.loads(paths["freeze"].read_text(encoding="utf-8"))
    settlement = json.loads(paths["settlement"].read_text(encoding="utf-8"))
    review = json.loads(paths["review"].read_text(encoding="utf-8"))
    freeze_body = _signed(freeze, "freeze_sha256", FREEZE_SCHEMA)
    settlement_body = _signed(settlement, "settlement_sha256", SETTLEMENT_SCHEMA)
    review_body = _signed(review, "review_sha256", REVIEW_SCHEMA)
    if settlement_body["freeze_sha256"] != freeze["freeze_sha256"]:
        raise ValueError("research budget settlement does not bind the current freeze")
    if settlement_body["source_schedule_sha256"] != freeze_body["source_schedule_sha256"]:
        raise ValueError("research budget settlement changed source schedule identity")
    return {
        "schema": "jaggedthoughts-research-budget-tournament-status-v1",
        "enabled": True,
        "status": review_body["status"],
        "frozen_at": freeze_body["frozen_at"],
        "source_schedule_sha256": freeze_body["source_schedule_sha256"],
        "eligible_work_count": freeze_body["eligible_work_count"],
        "capacity_per_policy": freeze_body["capacity_per_policy"],
        "arms": freeze_body["arms"],
        "settlement_status": settlement_body["status"],
        "complete_independent_block_count": review_body["complete_independent_block_count"],
        "minimum_independent_blocks": review_body["minimum_independent_blocks"],
        "primary_metric": review_body["primary_metric"],
        "recommended_policy_id": review_body["recommended_policy_id"],
        "exact_blocker": review_body["exact_blocker"],
        "paths": {name: path.relative_to(root).as_posix() for name, path in paths.items()},
        "capital_authority": False,
        "queue_mutation_authority": False,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("schedule", type=Path)
    snapshot.add_argument("output", type=Path)
    snapshot.add_argument("--at", required=True)
    snapshot.add_argument("--block-id", required=True)
    snapshot.add_argument("--capacity", type=int, default=1)
    settle = commands.add_parser("settle")
    settle.add_argument("freeze", type=Path)
    settle.add_argument("outcomes", type=Path)
    settle.add_argument("output", type=Path)
    settle.add_argument("--at", required=True)
    review = commands.add_parser("review")
    review.add_argument("output", type=Path)
    review.add_argument("settlements", type=Path, nargs="+")
    review.add_argument("--at", required=True)
    args = parser.parse_args()
    if args.command == "settle":
        result = settle_research_budget_block(
            json.loads(args.freeze.read_text(encoding="utf-8")),
            json.loads(args.outcomes.read_text(encoding="utf-8")),
            settled_at=args.at,
        )
        _write(args.output, result)
        print(json.dumps({"status": result["status"]}, sort_keys=True))
        return
    if args.command == "review":
        result = compile_research_budget_review(
            [json.loads(path.read_text(encoding="utf-8")) for path in args.settlements],
            generated_at=args.at,
        )
        _write(args.output, result)
        print(json.dumps({
            "status": result["status"],
            "recommended_policy_id": result["recommended_policy_id"],
        }, sort_keys=True))
        return
    schedule = json.loads(args.schedule.read_text(encoding="utf-8"))
    freeze = freeze_research_budget_tournament(
        schedule, frozen_at=args.at, inference_block_id=args.block_id,
        capacity=args.capacity,
    )
    settlement = settle_research_budget_block(freeze, (), settled_at=args.at)
    review = compile_research_budget_review((settlement,), generated_at=args.at)
    _write(args.output / "freeze.json", freeze)
    _write(args.output / "settlement.json", settlement)
    _write(args.output / "latest.json", review)
    print(json.dumps({
        "eligible_work_count": freeze["eligible_work_count"],
        "status": review["status"],
        "exact_blocker": review["exact_blocker"],
    }, sort_keys=True))


if __name__ == "__main__":
    _main()


__all__ = [
    "FREEZE_SCHEMA", "MINIMUM_INDEPENDENT_BLOCKS", "PRIMARY_METRIC", "REVIEW_SCHEMA",
    "SETTLEMENT_SCHEMA", "advance_research_budget_tournament",
    "compile_research_budget_review",
    "freeze_research_budget_tournament", "research_budget_tournament_status",
    "settle_research_budget_block",
]
