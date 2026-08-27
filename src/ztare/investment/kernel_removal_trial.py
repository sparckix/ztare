"""Prospective deletion contest for the JaggedThoughts investment machinery."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp
from .tournament import (
    BacktestEpisode,
    ObservableSpec,
    WorldModelCandidate,
    WorldModelForecast,
    evaluate_world_model_tournament,
)


ARM_SCHEMA = "jaggedthoughts-investment-kernel-removal-arm-v1"
ACTION_SCHEMA = "jaggedthoughts-investment-kernel-removal-trial-v1"
STATUS_SCHEMA = "jaggedthoughts-investment-kernel-removal-status-v1"
EXECUTION_SCHEMA = "jaggedthoughts-investment-kernel-removal-execution-v1"
DESIGN_ID = "jaggedthoughts-kernel-removal-llm-decomposition-v2"
ARMS = (
    "direct_public_packet",
    "fixed_memo_checklist",
    "typed_kernel",
    "full_investment_os",
)


def _verified_packet(raw: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(raw)
    claimed = str(packet.pop("packet_sha256", ""))
    if (
        packet.get("schema") != "jaggedthoughts-closed-book-evidence-packet-v1"
        or len(claimed) != 64
        or stable_sha256(packet) != claimed
    ):
        raise ValueError("kernel removal trial requires a valid closed-book packet")
    availability = dict(packet.get("field_availability") or {})
    availability_body = dict(availability)
    availability_sha = str(availability_body.pop("certificate_sha256", ""))
    if (
        availability.get("complete") is not True
        or availability.get("unverified_field_paths")
        or availability_sha != stable_sha256(availability_body)
    ):
        raise ValueError("kernel removal trial requires complete point-in-time fields")
    packet["packet_sha256"] = claimed
    return packet


def compile_kernel_removal_arms(
    evidence_packet: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Compile four nested packets that differ only in admitted machinery."""
    packet = _verified_packet(evidence_packet)
    if (packet.get("subject") or {}).get("kind") != "paper_watch_decision":
        return {}
    research = dict(packet.get("research_snapshot") or {})
    common = {
        "subject": packet.get("subject"),
        "opened_at": packet.get("opened_at"),
        "end_at": packet.get("end_at"),
        "horizon_days": packet.get("horizon_days"),
        "entity": packet.get("entity"),
        "benchmark": packet.get("benchmark"),
        "starting_market": packet.get("starting_market"),
        "observable_contract": packet.get("observable_contract"),
        "public_source_material": {
            "sources": research.get("public_sources"),
            "source_grounded_research": research.get("research"),
            "evidence_lineage": research.get("evidence"),
            "evidence_archive": packet.get("evidence_archive"),
        },
    }
    common_sha = stable_sha256(common)
    memo_method = {
        "sections": [
            "thesis", "strongest_rival", "decisive_observation", "falsifiers",
            "valuation_bridge", "expected_active_return",
        ],
        "llm_owned_decomposition": {
            "root": "benchmark-relative return over the declared horizon",
            "node_types": [
                "premise", "mechanism", "rival", "falsifier", "observable",
            ],
            "requirements": [
                "recursively expand material alternative explanations",
                "identify contradictions and omitted evidence without a supplied grammar",
                "freeze the decisive path and its falsifiers before forecasting",
            ],
        },
        "rule": (
            "use every section, build the decomposition yourself, search rival paths, "
            "and preserve unresolved disagreement"
        ),
    }
    overlays = {
        "direct_public_packet": {},
        "fixed_memo_checklist": {"fixed_method": memo_method},
        "typed_kernel": {
            "fixed_method": memo_method,
            "typed_kernel": {
                "field_availability": packet.get("field_availability"),
                "valuation_summary": packet.get("valuation_summary"),
                "company_quality": packet.get("company_quality"),
                "discovery_summary": packet.get("discovery_summary"),
                "decision_summary": packet.get("decision_summary"),
                "underwriting": research.get("underwriting"),
            },
        },
        "full_investment_os": {
            "fixed_method": memo_method,
            "typed_kernel": {
                "field_availability": packet.get("field_availability"),
                "valuation_summary": packet.get("valuation_summary"),
                "company_quality": packet.get("company_quality"),
                "discovery_summary": packet.get("discovery_summary"),
                "decision_summary": packet.get("decision_summary"),
                "underwriting": research.get("underwriting"),
            },
            "investment_os": {
                "business_fingerprint": research.get("business_fingerprint"),
                "strategy_frontier": research.get("strategy_frontier"),
                "strategy_snapshot": packet.get("strategy_snapshot"),
                "research_program": research.get("research_program"),
                "position_admission": research.get("position_admission"),
                "institutional_memory": research.get("institutional_memory"),
                "portfolio_context": research.get("portfolio_context"),
            },
        },
    }
    packets = {}
    for role in ARMS:
        body = {
            "schema": ARM_SCHEMA,
            "experiment_design_id": DESIGN_ID,
            "role": role,
            "common_source_snapshot_sha256": common_sha,
            "common_source_snapshot": common,
            "admitted_machinery": overlays[role],
            "paper_position_rule": {
                "positive_expected_active_return_weight": 0.05,
                "otherwise_weight": 0.0,
            },
            "capital_authority": False,
        }
        packets[role] = {**body, "packet_sha256": stable_sha256(body)}
    return packets


def compile_kernel_removal_execution_receipt(
    *,
    arm_packets: Mapping[str, Mapping[str, Any]],
    process_bundle: Mapping[str, Any],
    calls: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove the four arms used distinct one-call sessions under one process."""
    process = dict(process_bundle)
    process_sha = str(process.pop("process_bundle_sha256", ""))
    if (
        process.get("schema") != "jaggedthoughts-forecast-process-bundle-v1"
        or process_sha != stable_sha256(process)
        or process.get("model_identity_complete") is not True
        or process.get("provider_call_budget_per_role") != 1
        or process.get("cross_role_session_reuse") is not False
    ):
        raise ValueError("kernel removal trial requires one complete process identity")
    if set(arm_packets) != set(ARMS) or set(calls) != set(ARMS):
        raise ValueError("kernel removal execution requires exactly four arm calls")

    rows = []
    for role in ARMS:
        packet_sha = str((arm_packets[role] or {}).get("packet_sha256") or "")
        row = dict(calls[role])
        call = dict(row.get("call_receipt") or {})
        if (
            row.get("packet_sha256") != packet_sha
            or row.get("provider_call_charge") != 1
            or call.get("schema") != "leanmill.frontier_subscription_role_call.v1"
            or call.get("role") != f"jaggedthoughts_kernel_removal_{role}"
            or call.get("runtime") != process.get("runtime")
            or call.get("model") != process.get("resolved_model")
            or call.get("returncode") != 0
            or call.get("provider_call_charge") != 1
            or call.get("output_schema_digest") != process.get("output_schema_sha256")
        ):
            raise ValueError(f"kernel removal call changed process identity: {role}")
        if any(len(str(call.get(field) or "")) != 64 for field in (
            "prompt_digest", "result_digest", "output_schema_digest",
        )):
            raise ValueError(f"kernel removal call lacks durable digests: {role}")
        rows.append({
            "role": role,
            "packet_sha256": packet_sha,
            "agent_id": call.get("agent_id"),
            "prompt_digest": call.get("prompt_digest"),
            "result_digest": call.get("result_digest"),
            "call_receipt_sha256": stable_sha256(call),
            "artifact_ref": row.get("artifact_ref"),
        })
    if len({row["agent_id"] for row in rows}) != len(ARMS):
        raise ValueError("kernel removal arms must use independent agent sessions")
    if len({row["prompt_digest"] for row in rows}) != len(ARMS):
        raise ValueError("kernel removal arm prompts did not preserve arm identity")
    body = {
        "schema": EXECUTION_SCHEMA,
        "same_model_process_sha256": process_sha,
        "arm_calls": rows,
        "provider_call_count": len(rows),
        "execution_complete": True,
    }
    return {**body, "execution_sha256": stable_sha256(body)}


def compile_kernel_removal_action(
    evidence_packet: Mapping[str, Any], *,
    arm_packets: Mapping[str, Mapping[str, Any]],
    forecast_candidate_ids: Mapping[str, str],
    process_bundle_sha256: str,
    compiled_at: str,
    execution_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze the arm identities before the common outcome exists."""
    packet = _verified_packet(evidence_packet)
    if set(arm_packets) != set(ARMS):
        raise ValueError("kernel removal trial requires exactly four arms")
    source_hashes = set()
    design_ids = set()
    arms = []
    for role in ARMS:
        arm = dict(arm_packets[role])
        claimed = str(arm.pop("packet_sha256", ""))
        if (
            arm.get("schema") != ARM_SCHEMA
            or arm.get("role") != role
            or claimed != stable_sha256(arm)
        ):
            raise ValueError(f"invalid kernel removal arm: {role}")
        source_hashes.add(str(arm.get("common_source_snapshot_sha256") or ""))
        design_ids.add(str(arm.get("experiment_design_id") or ""))
        arms.append({
            "role": role,
            "packet_sha256": claimed,
            "forecast_candidate_id": forecast_candidate_ids.get(role),
        })
    if len(source_hashes) != 1 or "" in source_hashes:
        raise ValueError("kernel removal arms do not share one source snapshot")
    if design_ids != {DESIGN_ID}:
        raise ValueError("kernel removal arms do not share one experiment design")
    execution_envelope = dict(execution_receipt or {})
    execution = dict(execution_envelope)
    execution_sha = str(execution.pop("execution_sha256", ""))
    execution_complete = (
        execution.get("schema") == EXECUTION_SCHEMA
        and execution_sha == stable_sha256(execution)
        and execution.get("execution_complete") is True
        and execution.get("same_model_process_sha256") == process_bundle_sha256
        and {row.get("role") for row in execution.get("arm_calls") or ()} == set(ARMS)
        and {row.get("packet_sha256") for row in execution.get("arm_calls") or ()}
        == {row["packet_sha256"] for row in arms}
    )
    availability = dict(packet.get("field_availability") or {})
    body = {
        "schema": ACTION_SCHEMA,
        "trial_id": f"kernel-removal:{packet['packet_sha256'][:24]}",
        "opened_at": canonical_timestamp(compiled_at, "kernel removal opened_at"),
        "episode_core_sha256": stable_sha256({
            "subject": packet.get("subject"),
            "opened_at": packet.get("opened_at"),
            "end_at": packet.get("end_at"),
            "horizon_days": packet.get("horizon_days"),
        }),
        "source_snapshot_sha256": next(iter(source_hashes)),
        "experiment_design_id": DESIGN_ID,
        "field_availability_certificate_sha256": availability.get("certificate_sha256"),
        "full_evidence_packet_sha256": packet["packet_sha256"],
        "same_model_process_sha256": process_bundle_sha256,
        "execution_receipt_sha256": execution_sha or None,
        "execution_receipt": execution_envelope or None,
        "arms": arms,
        "settlement": {
            "target": "entity price return minus benchmark price return",
            "observable_ids": ["active_return", "underperformance_event"],
            "transaction_cost_bps": 10.0,
            "minimum_inference_blocks": 8,
            "baseline_arm": "direct_public_packet",
        },
        "status": (
            "sealed_four_arm_forecast"
            if set(forecast_candidate_ids) == set(ARMS) and execution_complete
            else "incomplete_arm_generation"
        ),
        "deletion_rule": (
            "delete any machinery layer that does not improve prospective forecast loss, "
            "calibration, or after-cost paper outcomes"
        ),
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "action_sha256": stable_sha256(body)}


def compile_kernel_removal_status(
    runs: tuple[Mapping[str, Any], ...],
    settlements: tuple[Mapping[str, Any], ...], *,
    inference_block_ids: Mapping[str, str],
) -> dict[str, Any]:
    """Score complete four-arm cohorts with the shared world-model tournament."""
    settlement_by_run = {
        str(row.get("run_id") or ""): row for row in settlements if row.get("run_id")
    }
    trials = [
        (run, dict(run.get("kernel_removal_trial") or {}))
        for run in runs
        if (run.get("kernel_removal_trial") or {}).get("schema") == ACTION_SCHEMA
    ]
    def eligible(run: Mapping[str, Any], trial: Mapping[str, Any]) -> bool:
        action = dict(trial)
        action_sha = str(action.pop("action_sha256", ""))
        execution = dict(trial.get("execution_receipt") or {})
        execution_sha = str(execution.pop("execution_sha256", ""))
        process = dict((run.get("provider") or {}).get("process_bundle") or {})
        process_sha = str(process.pop("process_bundle_sha256", ""))
        arms = tuple(trial.get("arms") or ())
        return (
            action_sha == stable_sha256(action)
            and trial.get("status") == "sealed_four_arm_forecast"
            and len(arms) == len(ARMS)
            and {row.get("role") for row in arms} == set(ARMS)
            and len({row.get("forecast_candidate_id") for row in arms}) == len(ARMS)
            and execution_sha == trial.get("execution_receipt_sha256")
            and execution_sha == stable_sha256(execution)
            and execution.get("execution_complete") is True
            and process_sha == trial.get("same_model_process_sha256")
            and process_sha == stable_sha256(process)
            and process.get("model_identity_complete") is True
        )
    sealed = [
        (run, trial) for run, trial in trials
        if eligible(run, trial)
    ]
    settled = [
        (run, trial) for run, trial in sealed
        if str(run.get("run_id") or "") in settlement_by_run
        and str(run.get("run_id") or "") in inference_block_ids
    ]
    blocks: set[str] = set()
    tournament = None
    if settled:
        cohorts: dict[
            tuple[int, str, str],
            list[tuple[Mapping[str, Any], Mapping[str, Any]]],
        ] = {}
        for run, trial in settled:
            process_sha = str(trial.get("same_model_process_sha256") or "")
            cohorts.setdefault(
                (
                    int(run.get("horizon_days") or 0), process_sha,
                    str(trial.get("experiment_design_id") or "legacy"),
                ), [],
            ).append((run, settlement_by_run[str(run["run_id"])]))
        (horizon_days, process_sha, design_id), cohort = max(
            cohorts.items(), key=lambda item: (len(item[1]), item[0]),
        )
        blocks = {
            inference_block_ids[str(run["run_id"])] for run, _ in cohort
        }
        first_run, _ = cohort[0]
        first_trial = dict(first_run["kernel_removal_trial"])
        candidate_id_by_role = {
            str(row["role"]): str(row["forecast_candidate_id"])
            for row in first_trial["arms"]
        }
        first_candidates = {
            str(row["candidate_id"]): row
            for row in first_run.get("candidate_forecasts") or ()
            if row.get("candidate_id") in set(candidate_id_by_role.values())
        }
        if set(first_candidates) != set(candidate_id_by_role.values()):
            raise ValueError("kernel removal cohort misses a frozen arm candidate")
        models = tuple(WorldModelCandidate(
            model_id=candidate_id_by_role[role],
            version=str(first_candidates[candidate_id_by_role[role]].get("version") or "1"),
            model_family="investment_kernel_removal_trial",
            trial_family_id=f"investment_kernel_removal:{role}",
            mechanism_ids=tuple(map(
                str,
                first_candidates[candidate_id_by_role[role]].get("mechanism_ids") or (),
            )),
            linked_observable_ids=(),
            source_refs=(f"kernel-removal-arm:{role}", process_sha),
            generation_process="subscription_llm",
        ) for role in ARMS)
        episodes = []
        forecasts = []
        availability_rows = []
        for run, settlement in cohort:
            run_id = str(run["run_id"])
            packet = dict(run["evidence_packet"])
            actual = dict(settlement["actual_values"])
            episodes.append(BacktestEpisode(
                episode_id=str(run["episode_id"]),
                inference_block_id=inference_block_ids[run_id],
                entity_id=str((packet.get("entity") or {}).get("entity_id") or ""),
                start_at=str(settlement["return_window_binding"]["entry_observed_at"]),
                end_at=str(settlement["return_window_settlement"]["exit_observed_at"]),
                outcome_available_at=str(settlement["evaluated_at"]),
                starting_weight=0.0,
                asset_return=float(actual["entity_return"]),
                benchmark_return=float(actual["benchmark_return"]),
                cash_return=float(run["settlement_contract"].get("cash_return") or 0.0),
                actual_values={
                    "active_return": float(actual["active_return"]),
                    "underperformance_event": float(actual["underperformance_event"]),
                },
                source_refs=(
                    str(settlement["entity_end_price"]["source_ref"]),
                    str(settlement["benchmark_end_price"]["source_ref"]),
                    run_id,
                ),
            ))
            candidates = {
                str(row["candidate_id"]): row
                for row in run.get("candidate_forecasts") or ()
            }
            for role in ARMS:
                candidate = candidates[candidate_id_by_role[role]]
                forecasts.append(WorldModelForecast(
                    model_id=candidate_id_by_role[role],
                    episode_id=str(run["episode_id"]),
                    trained_through=str(run["opened_at"]),
                    issued_at=str(run.get("sealed_at") or run["opened_at"]),
                    predicted_values={
                        "active_return": float(candidate["predicted_values"]["active_return"]),
                        "underperformance_event": float(
                            candidate["predicted_values"]["underperformance_event"]
                        ),
                    },
                    target_weight=float(candidate.get("target_weight") or 0.0),
                    source_refs=(str(packet["packet_sha256"]), str(candidate["forecast_sha256"])),
                ))
            availability_rows.extend(
                (packet.get("field_availability") or {}).get("rows") or ()
            )
        tournament = evaluate_world_model_tournament(
            tournament_id=(
                f"kernel-removal::{horizon_days}d::{process_sha[:12]}::{design_id}"
            ),
            owner="jaggedthoughts-kernel-removal-ledger",
            as_of=max(str(settlement["evaluated_at"]) for _, settlement in cohort),
            mode="prospective_shadow",
            baseline_model_id=candidate_id_by_role["direct_public_packet"],
            observables=(
                ObservableSpec("active_return", "decimal_return", "absolute", 0.10, 0.70),
                ObservableSpec(
                    "underperformance_event", "probability", "brier", 1.0, 0.30,
                ),
            ),
            models=models,
            episodes=tuple(episodes),
            forecasts=tuple(forecasts),
            transaction_cost_bps=10.0,
            declared_trial_family_ids=tuple(model.trial_family_id for model in models),
            source_refs=tuple(str(run["run_id"]) for run, _ in cohort),
            min_inference_blocks=8,
            periods_per_year=365.25 / max(1, horizon_days),
            source_availability_rows=tuple(availability_rows),
        )
    body = {
        "schema": STATUS_SCHEMA,
        "declared_run_count": len(trials),
        "sealed_run_count": len(sealed),
        "unbound_execution_receipt_diagnostic_run_count": len(trials) - len(sealed),
        "settled_episode_count": len(settled),
        "inference_block_count": len(blocks),
        "minimum_inference_blocks": 8,
        "status": (
            "ready_for_world_model_verdict" if len(blocks) >= 8 else
            "collecting_independent_blocks" if settled else
            "awaiting_settlements" if sealed else
            "awaiting_execution_bound_trial" if trials else
            "awaiting_sealed_trial"
        ),
        "scorer": "closed_book.world_model_tournament",
        "baseline_arm": "kernel_removal_direct_public_packet",
        "tournament": tournament,
        "survivor_arm_ids": (
            list(tournament.get("survivor_model_ids") or ()) if tournament else []
        ),
        "historical_llm_replay_authority": "diagnostic_only",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


__all__ = [
    "ACTION_SCHEMA", "ARMS", "ARM_SCHEMA", "DESIGN_ID", "EXECUTION_SCHEMA",
    "STATUS_SCHEMA",
    "compile_kernel_removal_action", "compile_kernel_removal_arms",
    "compile_kernel_removal_execution_receipt", "compile_kernel_removal_status",
]
