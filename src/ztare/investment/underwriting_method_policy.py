"""Future-only routing policy learned from nested underwriting ablations."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import paired_permutation_test

from .contracts import canonical_timestamp, require_finite, timestamp_key
from .underwriting_ablation import UNDERWRITING_ABLATION_STATUS_SCHEMA


UNDERWRITING_METHOD_POLICY_SCHEMA = "jaggedthoughts-underwriting-method-policy-v1"
UNDERWRITING_METHOD_ROUTE_SCHEMA = "jaggedthoughts-underwriting-method-route-v1"
MINIMUM_INDEPENDENT_BLOCKS = 8
_METRICS = (
    "absolute_error_reduction",
    "brier_reduction",
    "paper_active_return_contribution_gain",
)


def _verified_status(raw: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(raw)
    claimed = str(body.pop("status_sha256", ""))
    if (
        body.get("schema") != UNDERWRITING_ABLATION_STATUS_SCHEMA
        or len(claimed) != 64
        or stable_sha256(body) != claimed
    ):
        raise ValueError("underwriting method policy requires a valid ablation status")
    return {**body, "status_sha256": claimed}


def _holm_fwer(comparisons: list[dict[str, Any]]) -> None:
    """Apply the same Holm step-down correction as the research-budget review."""
    values = sorted(
        (float(row["paired_inference"]["p_value"]), row["comparison_metric_id"])
        for row in comparisons if row["paired_inference"].get("p_value") is not None
    )
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (raw_p, comparison_id) in enumerate(values):
        running = max(running, min(1.0, raw_p * (len(values) - rank)))
        adjusted[comparison_id] = running
    for row in comparisons:
        value = adjusted.get(row["comparison_metric_id"])
        row["multiplicity"] = {
            "method": "holm_fwer",
            "family_size": len(values),
            "adjusted_p_value": round(value, 8) if value is not None else None,
            "rejected_at_alpha": value is not None and value <= 0.05,
        }


def compile_underwriting_method_policy(
    ablation_status: Mapping[str, Any],
    *,
    compiled_at: str,
    exploration_quota: float = 0.20,
) -> dict[str, Any]:
    """Compile future research routing without relabeling settled episodes."""

    source = _verified_status(ablation_status)
    effective_from = canonical_timestamp(compiled_at, "underwriting policy compiled_at")
    latest_settled_at = source.get("latest_settled_at")
    if latest_settled_at and timestamp_key(effective_from) < timestamp_key(
        canonical_timestamp(latest_settled_at, "underwriting latest_settled_at")
    ):
        raise ValueError("underwriting method policy cannot precede its source settlements")
    quota = require_finite(exploration_quota, "underwriting exploration_quota")
    if not 0 < quota < 1:
        raise ValueError("underwriting exploration_quota must be between zero and one")

    comparisons: list[dict[str, Any]] = []
    source_comparisons = {
        str(row.get("comparison_id") or ""): row
        for row in source.get("comparisons") or () if isinstance(row, Mapping)
    }
    required_comparisons = (
        "fingerprint_increment", "full_research_increment", "total_research_increment",
    )
    if set(source_comparisons) != set(required_comparisons):
        raise ValueError("underwriting method policy requires all three nested comparisons")
    shared_block_ids: set[str] | None = None
    for comparison_id in required_comparisons:
        comparison = dict(source_comparisons[comparison_id])
        block_rows = [
            dict(row) for row in comparison.get("block_scores") or ()
            if isinstance(row, Mapping)
        ]
        block_ids = [str(row.get("inference_block_id") or "") for row in block_rows]
        if len(block_ids) != len(set(block_ids)) or "" in block_ids:
            raise ValueError("underwriting method policy requires unique inference blocks")
        if shared_block_ids is None:
            shared_block_ids = set(block_ids)
        elif set(block_ids) != shared_block_ids:
            raise ValueError("underwriting method policy requires one shared block population")
        for metric in _METRICS:
            values = [require_finite(row.get(metric), metric) for row in block_rows]
            inference = paired_permutation_test(
                values,
                [0.0] * len(values),
                seed=int(stable_sha256([comparison_id, metric, values])[:8], 16),
            )
            comparisons.append({
                "comparison_metric_id": f"{comparison_id}:{metric}",
                "comparison_id": comparison_id,
                "metric": metric,
                "independent_block_count": len(values),
                "paired_inference": inference,
            })
    _holm_fwer(comparisons)

    identity_ready = bool(
        source.get("comparison_ready")
        and source.get("process_identity_complete") is True
        and source.get("availability_identity_complete") is True
        and int(source.get("inference_block_count") or 0) >= MINIMUM_INDEPENDENT_BLOCKS
        and source.get("block_identity")
        == "connected_components_of_overlapping_tradable_return_windows"
    )
    passing_metrics = {
        (str(row["comparison_id"]), str(row["metric"]))
        for row in comparisons
        if row["independent_block_count"] >= MINIMUM_INDEPENDENT_BLOCKS
        and row["multiplicity"]["rejected_at_alpha"]
        and float(row["paired_inference"].get("observed_delta") or 0.0) > 0
        and row["paired_inference"].get("ci_lo") is not None
        and float(row["paired_inference"]["ci_lo"]) > 0
    } if identity_ready else set()
    survivors = {
        comparison_id for comparison_id in required_comparisons
        if all((comparison_id, metric) in passing_metrics for metric in _METRICS)
    }
    if {"full_research_increment", "total_research_increment"} <= survivors:
        decision, preferred = "prefer_full_research", "typed_plus_full_research"
    elif "fingerprint_increment" in survivors:
        decision, preferred = "prefer_fingerprint", "typed_plus_fingerprint"
    else:
        decision, preferred = "continue_balanced", None

    arms = (
        "typed_quantitative", "typed_plus_fingerprint", "typed_plus_full_research",
    )
    allocation = (
        {arm: round(1 / 3, 8) for arm in arms}
        if preferred is None else
        {arm: round(1 - quota if arm == preferred else quota / 2, 8) for arm in arms}
    )
    future_episode_routing = (
        {"balanced_ablation": 1.0, "preferred_method": 0.0}
        if preferred is None else
        {"balanced_ablation": quota, "preferred_method": round(1 - quota, 8)}
    )
    blockers = []
    if not identity_ready:
        blockers.extend(source.get("promotion_blockers") or ())
        if int(source.get("inference_block_count") or 0) < MINIMUM_INDEPENDENT_BLOCKS:
            blockers.append("minimum_independent_blocks_not_met")
    elif not survivors:
        blockers.append("no_information_increment_passed_all_three_holm_fwer_metrics")
    body = {
        "schema": UNDERWRITING_METHOD_POLICY_SCHEMA,
        "compiled_at": effective_from,
        "effective_for_runs_opened_at_or_after": effective_from,
        "source_ablation_status_sha256": source["status_sha256"],
        "learned_through": latest_settled_at,
        "routing_decision": decision,
        "exploration_quota": quota,
        "future_arm_allocation": allocation,
        "future_episode_routing": future_episode_routing,
        "comparisons": comparisons,
        "promotion_blockers": sorted(set(blockers)),
        "historical_relabeling_forbidden": True,
        "weights_authority": False,
        "capital_authority": False,
    }
    return {**body, "policy_sha256": stable_sha256(body)}


def select_underwriting_method_route(
    policy: Mapping[str, Any], *, episode_identity: str, opened_at: str,
    learning_credit_assignment: Mapping[str, Any] | None = None,
    current_ablation_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply a learned policy to one future episode and preserve drift checks."""

    body = dict(policy)
    claimed = str(body.pop("policy_sha256", ""))
    if (
        body.get("schema") != UNDERWRITING_METHOD_POLICY_SCHEMA
        or len(claimed) != 64
        or stable_sha256(body) != claimed
    ):
        raise ValueError("underwriting method route requires a valid method policy")
    opened = canonical_timestamp(opened_at, "underwriting episode opened_at")
    effective = canonical_timestamp(
        body.get("effective_for_runs_opened_at_or_after"),
        "underwriting policy effective time",
    )
    decision = str(body.get("routing_decision") or "continue_balanced")
    preferred = {
        "prefer_fingerprint": "typed_plus_fingerprint",
        "prefer_full_research": "typed_plus_full_research",
    }.get(decision)
    draw = int(stable_sha256([claimed, str(episode_identity)])[:16], 16) / float(16**16)
    current_status_sha = ""
    try:
        current_status = _verified_status(current_ablation_status or {})
        current_status_sha = str(current_status["status_sha256"])
        from .learning_credit import learning_credit_allows

        admitted = learning_credit_allows(
            learning_credit_assignment or {},
            component_id="underwriting_information_method",
            use="future_underwriting_method_routing",
            source_ref=current_status_sha,
        ) and body.get("source_ablation_status_sha256") == current_status_sha
    except ValueError:
        admitted = False
    policy_active = bool(
        admitted and preferred is not None
        and timestamp_key(opened) >= timestamp_key(effective)
    )
    exploration = policy_active and draw < float(body["exploration_quota"])
    all_arms = (
        "typed_quantitative", "typed_plus_fingerprint", "typed_plus_full_research",
    )
    selected = all_arms if not policy_active or exploration else (preferred,)
    route_body = {
        "schema": UNDERWRITING_METHOD_ROUTE_SCHEMA,
        "policy_sha256": claimed,
        "source_ablation_status_sha256": body.get("source_ablation_status_sha256"),
        "current_ablation_status_sha256": current_status_sha or None,
        "episode_identity": str(episode_identity),
        "opened_at": opened,
        "routing_decision": decision,
        "learning_credit_admitted": admitted,
        "route_mode": (
            "balanced_ablation" if not policy_active else
            "exploration_ablation" if exploration else "preferred_method"
        ),
        "selected_arms": list(selected),
        "exploration_draw": round(draw, 12),
        "research_routing_authority": True,
        "weights_authority": False,
        "capital_authority": False,
    }
    return {**route_body, "route_sha256": stable_sha256(route_body)}


__all__ = [
    "MINIMUM_INDEPENDENT_BLOCKS",
    "UNDERWRITING_METHOD_POLICY_SCHEMA",
    "UNDERWRITING_METHOD_ROUTE_SCHEMA",
    "compile_underwriting_method_policy",
    "select_underwriting_method_route",
]
