"""Nested evidence packets for measuring the economic value of underwriting research."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key


UNDERWRITING_ABLATION_ACTION_SCHEMA = (
    "jaggedthoughts-underwriting-information-ablation-action-v1"
)
UNDERWRITING_ABLATION_ARM_SCHEMA = "jaggedthoughts-underwriting-information-arm-v1"
UNDERWRITING_ABLATION_STATUS_SCHEMA = (
    "jaggedthoughts-underwriting-information-ablation-status-v1"
)
UNDERWRITING_ABLATION_ARMS = (
    "typed_quantitative",
    "typed_plus_fingerprint",
    "typed_plus_full_research",
)

_COMPARISONS = (
    ("fingerprint_increment", "typed_quantitative", "typed_plus_fingerprint"),
    ("full_research_increment", "typed_plus_fingerprint", "typed_plus_full_research"),
    ("total_research_increment", "typed_quantitative", "typed_plus_full_research"),
)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _hashed_identity(
    raw: Mapping[str, Any], *, schema: str, hash_field: str,
) -> bool:
    body = dict(raw)
    claimed = str(body.pop(hash_field, ""))
    return (
        body.get("schema") == schema
        and len(claimed) == 64
        and stable_sha256(body) == claimed
    )


def compile_underwriting_ablation_status(
    runs: tuple[Mapping[str, Any], ...],
    settlements: tuple[Mapping[str, Any], ...],
    *,
    inference_block_ids: Mapping[str, str],
) -> dict[str, Any]:
    """Score settled nested-information experiments by independent market window."""

    settlement_by_run = {
        str(row.get("run_id") or ""): row for row in settlements if row.get("run_id")
    }
    declared_count = sealed_count = pending_count = incomplete_count = 0
    episodes: list[dict[str, Any]] = []
    for run in runs:
        action = run.get("underwriting_information_ablation") or {}
        if action.get("schema") != UNDERWRITING_ABLATION_ACTION_SCHEMA:
            continue
        declared_count += 1
        arm_rows = tuple(
            row for row in action.get("arms") or () if isinstance(row, Mapping)
        )
        arms = {
            str(row.get("role") or ""): str(row.get("forecast_candidate_id") or "")
            for row in arm_rows
        }
        run_id = str(run.get("run_id") or "")
        process_sha = str(action.get("same_model_process_sha256") or "")
        process = dict((run.get("provider") or {}).get("process_bundle") or {})
        process_identity_complete = (
            process.get("model_identity_complete") is True
            and process_sha == process.get("process_bundle_sha256")
            and _hashed_identity(
                process,
                schema="jaggedthoughts-forecast-process-bundle-v1",
                hash_field="process_bundle_sha256",
            )
        )
        availability = dict(
            (run.get("evidence_packet") or {}).get("field_availability") or {}
        )
        availability_identity_complete = (
            availability.get("complete") is True
            and not availability.get("unverified_field_paths")
            and _hashed_identity(
                availability,
                schema="jaggedthoughts-field-availability-certificate-v1",
                hash_field="certificate_sha256",
            )
        )
        if (
            action.get("status") != "sealed_three_arm_forecast"
            or not run.get("sealed_at")
            or len(arm_rows) != len(UNDERWRITING_ABLATION_ARMS)
            or set(arms) != set(UNDERWRITING_ABLATION_ARMS)
            or not all(arms.values())
            or len(set(arms.values())) != len(UNDERWRITING_ABLATION_ARMS)
            or len(process_sha) != 64
        ):
            incomplete_count += 1
            continue
        sealed_count += 1
        settlement = settlement_by_run.get(run_id)
        if settlement is None:
            pending_count += 1
            continue
        try:
            settled_at = canonical_timestamp(
                settlement.get("evaluated_at"), "underwriting settlement evaluated_at",
            )
        except ValueError:
            incomplete_count += 1
            continue
        block_id = inference_block_ids.get(run_id)
        scores = {
            str(row.get("candidate_id") or ""): row
            for row in settlement.get("candidate_scores") or ()
            if isinstance(row, Mapping)
        }
        required_metrics = {
            "active_return_absolute_error", "underperformance_brier",
            "active_return_contribution_after_cost",
        }
        if (
            not block_id
            or any(candidate_id not in scores for candidate_id in arms.values())
            or any(
                not required_metrics <= set(scores[candidate_id])
                for candidate_id in arms.values() if candidate_id in scores
            )
        ):
            incomplete_count += 1
            continue
        episodes.append({
            "run_id": run_id,
            "inference_block_id": block_id,
            "same_model_process_sha256": process_sha,
            "settled_at": settled_at,
            "process_identity_complete": process_identity_complete,
            "availability_identity_complete": availability_identity_complete,
            "scores": {role: scores[candidate_id] for role, candidate_id in arms.items()},
        })

    comparisons = []
    for comparison_id, lower_arm, higher_arm in _COMPARISONS:
        by_block: dict[str, list[dict[str, float]]] = {}
        for episode in episodes:
            lower = episode["scores"][lower_arm]
            higher = episode["scores"][higher_arm]
            by_block.setdefault(str(episode["inference_block_id"]), []).append({
                "absolute_error_reduction": (
                    float(lower["active_return_absolute_error"])
                    - float(higher["active_return_absolute_error"])
                ),
                "brier_reduction": (
                    float(lower["underperformance_brier"])
                    - float(higher["underperformance_brier"])
                ),
                "paper_active_return_contribution_gain": (
                    float(higher["active_return_contribution_after_cost"])
                    - float(lower["active_return_contribution_after_cost"])
                ),
            })
        block_rows = [{
            "inference_block_id": block_id,
            **{
                metric: _mean([row[metric] for row in rows])
                for metric in rows[0]
            },
            "episode_count": len(rows),
        } for block_id, rows in sorted(by_block.items())]
        comparisons.append({
            "comparison_id": comparison_id,
            "lower_information_arm": lower_arm,
            "higher_information_arm": higher_arm,
            "settled_episode_count": sum(row["episode_count"] for row in block_rows),
            "inference_block_count": len(block_rows),
            "comparison_ready": len(block_rows) >= 8,
            "block_weighted_mean": {
                metric: _mean([row[metric] for row in block_rows]) if block_rows else None
                for metric in (
                    "absolute_error_reduction", "brier_reduction",
                    "paper_active_return_contribution_gain",
                )
            },
            "block_scores": block_rows,
        })

    independent_blocks = len({row["inference_block_id"] for row in episodes})
    process_identity_complete = bool(episodes) and all(
        row["process_identity_complete"] for row in episodes
    )
    availability_identity_complete = bool(episodes) and all(
        row["availability_identity_complete"] for row in episodes
    )
    latest_settled_at = max(
        (row["settled_at"] for row in episodes), key=timestamp_key, default=None,
    )
    comparison_ready = (
        process_identity_complete
        and availability_identity_complete
        and bool(comparisons)
        and all(row["comparison_ready"] for row in comparisons)
    )
    promotion_blockers = []
    if episodes and not process_identity_complete:
        promotion_blockers.append("subscription_resolved_model_identity_unavailable")
    if episodes and not availability_identity_complete:
        promotion_blockers.append("forecast_input_availability_identity_incomplete")
    body = {
        "schema": UNDERWRITING_ABLATION_STATUS_SCHEMA,
        "declared_run_count": declared_count,
        "sealed_run_count": sealed_count,
        "settled_episode_count": len(episodes),
        "latest_settled_at": latest_settled_at,
        "pending_settlement_count": pending_count,
        "incomplete_episode_count": incomplete_count,
        "inference_block_count": independent_blocks,
        "minimum_inference_blocks": 8,
        "process_identity_complete": process_identity_complete,
        "availability_identity_complete": availability_identity_complete,
        "comparison_ready": comparison_ready,
        "status": (
            "comparison_ready" if comparison_ready else
            "collecting_independent_blocks" if episodes else
            "awaiting_settlements" if pending_count else
            "incomplete_settlements" if incomplete_count else
            "awaiting_sealed_runs"
        ),
        "comparisons": comparisons,
        "score_orientation": "positive_values_favor_the_higher_information_arm",
        "block_identity": "connected_components_of_overlapping_tradable_return_windows",
        "promotion_blockers": promotion_blockers,
        "authority": "paper_underwriting_research_only",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def _verified_packet(raw: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(raw)
    claimed = str(packet.pop("packet_sha256", ""))
    if (
        packet.get("schema") != "jaggedthoughts-closed-book-evidence-packet-v1"
        or len(claimed) != 64
        or stable_sha256(packet) != claimed
    ):
        raise ValueError("underwriting ablation requires a valid closed-book packet")
    packet["packet_sha256"] = claimed
    return packet


def compile_underwriting_ablation_arms(
    evidence_packet: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Create strictly nested tool-visible packets for one researched watch."""
    packet = _verified_packet(evidence_packet)
    subject = dict(packet.get("subject") or {})
    if subject.get("kind") != "paper_watch_decision":
        return {}
    research = dict(packet.get("research_snapshot") or {})
    common = {
        "subject": subject,
        "opened_at": packet.get("opened_at"),
        "end_at": packet.get("end_at"),
        "horizon_days": packet.get("horizon_days"),
        "entity": packet.get("entity"),
        "benchmark": packet.get("benchmark"),
        "starting_market": packet.get("starting_market"),
        "observable_contract": packet.get("observable_contract"),
        "valuation_summary": packet.get("valuation_summary"),
        "decision_summary": packet.get("decision_summary"),
        "discovery_summary": packet.get("discovery_summary"),
        "fund_characteristics": packet.get("fund_characteristics"),
        "underwriting": research.get("underwriting"),
    }
    common_sha = stable_sha256(common)
    visible: dict[str, dict[str, Any]] = {
        "typed_quantitative": {},
        "typed_plus_fingerprint": {
            "company_quality": packet.get("company_quality"),
            "business_fingerprint": research.get("business_fingerprint"),
        },
        "typed_plus_full_research": {
            "company_quality": packet.get("company_quality"),
            "business_fingerprint": research.get("business_fingerprint"),
            "research": research.get("research"),
            "strategy_frontier": research.get("strategy_frontier"),
            "strategy_snapshot": packet.get("strategy_snapshot"),
            "research_program": research.get("research_program"),
        },
    }
    arms = {}
    for role in UNDERWRITING_ABLATION_ARMS:
        body = {
            "schema": UNDERWRITING_ABLATION_ARM_SCHEMA,
            "role": role,
            "common_episode_core_sha256": common_sha,
            "common": common,
            "incremental_evidence": visible[role],
            "visible_evidence_classes": {
                "typed_quantitative": ["quantitative"],
                "typed_plus_fingerprint": ["quantitative", "fingerprint"],
                "typed_plus_full_research": [
                    "quantitative", "fingerprint", "thesis_rival_strategy",
                ],
            }[role],
            "capital_authority": False,
        }
        arms[role] = {**body, "packet_sha256": stable_sha256(body)}
    return arms


def compile_underwriting_ablation_action(
    evidence_packet: Mapping[str, Any],
    *,
    arm_packets: Mapping[str, Mapping[str, Any]],
    forecast_candidate_ids: Mapping[str, str],
    process_bundle_sha256: str,
    compiled_at: str,
) -> dict[str, Any]:
    """Bind three separately generated forecasts to one nested-information experiment."""
    packet = _verified_packet(evidence_packet)
    if set(arm_packets) != set(UNDERWRITING_ABLATION_ARMS):
        raise ValueError("underwriting ablation requires exactly three nested arms")
    if set(forecast_candidate_ids) - set(UNDERWRITING_ABLATION_ARMS):
        raise ValueError("underwriting ablation forecast roles are invalid")
    arm_rows = []
    common_hashes = set()
    for role in UNDERWRITING_ABLATION_ARMS:
        arm = dict(arm_packets[role])
        claimed = str(arm.pop("packet_sha256", ""))
        if (
            arm.get("schema") != UNDERWRITING_ABLATION_ARM_SCHEMA
            or arm.get("role") != role
            or len(claimed) != 64
            or stable_sha256(arm) != claimed
        ):
            raise ValueError(f"underwriting ablation arm is invalid: {role}")
        common_hashes.add(str(arm.get("common_episode_core_sha256") or ""))
        arm_rows.append({
            "role": role,
            "packet_sha256": claimed,
            "forecast_candidate_id": forecast_candidate_ids.get(role),
            "visible_evidence_classes": arm.get("visible_evidence_classes"),
        })
    if len(common_hashes) != 1 or "" in common_hashes:
        raise ValueError("underwriting ablation arms do not share one episode core")
    research = dict(packet.get("research_snapshot") or {})
    evidence = dict(research.get("evidence") or {})
    program = dict(research.get("research_program") or {})
    subject = dict(packet.get("subject") or {})
    body = {
        "schema": UNDERWRITING_ABLATION_ACTION_SCHEMA,
        "action_id": f"underwriting-ablation:{packet['packet_sha256'][:24]}",
        "compiled_at": compiled_at,
        "subject": subject,
        "lineage": {
            "paper_watch_decision_sha256": subject.get("subject_sha256"),
            "candidate_leaf": subject.get("candidate_leaf"),
            "candidate_sha256": subject.get("candidate_sha256"),
            "dossier_leaf": evidence.get("dossier_leaf"),
            "dossier_sha256": evidence.get("dossier_sha256"),
            "research_coverage_sha256": evidence.get("research_coverage_sha256"),
            "research_request_sha256": program.get("request_sha256"),
            "research_assignment_sha256": program.get("assignment_sha256"),
            "research_pair_identity_sha256": program.get("pair_identity_sha256"),
            "research_question_program_id": program.get("question_program_id"),
            "research_question_program_sha256": program.get("question_program_sha256"),
        },
        "common_episode_core_sha256": next(iter(common_hashes)),
        "full_evidence_packet_sha256": packet["packet_sha256"],
        "arms": arm_rows,
        "same_model_process_sha256": process_bundle_sha256,
        "forecast_contract": {
            "target": "entity price return minus benchmark price return",
            "horizon_days": packet.get("horizon_days"),
            "benchmark_id": (packet.get("benchmark") or {}).get("entity_id"),
            "transaction_cost_bps": 10.0,
            "minimum_independent_blocks": 8,
        },
        "status": (
            "sealed_three_arm_forecast"
            if set(forecast_candidate_ids) == set(UNDERWRITING_ABLATION_ARMS)
            else "incomplete_arm_generation"
        ),
        "authority": "prospective_research_credit_experiment_only",
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "action_sha256": stable_sha256(body)}


__all__ = [
    "UNDERWRITING_ABLATION_ACTION_SCHEMA", "UNDERWRITING_ABLATION_ARMS",
    "UNDERWRITING_ABLATION_ARM_SCHEMA", "UNDERWRITING_ABLATION_STATUS_SCHEMA",
    "compile_underwriting_ablation_action", "compile_underwriting_ablation_arms",
    "compile_underwriting_ablation_status",
]
