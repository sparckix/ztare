"""Score a deterministic historical forecast from sealed public-evidence snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import inspect
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .closed_book import (
    _trailing_return, _underperformance_probability, overlap_cluster_ids,
)
from .contracts import (
    MetricObservation, canonical_timestamp, require_finite, require_text, timestamp_key,
)
from .evidence_vault import evidence_vault_status, reconstruct_evidence_as_of
from .golden_store import (
    GoldenEdge, GoldenLeaf, GoldenStore, record_world_model_tournament,
)
from .institutional_learning import compile_historical_accounting_replay
from .prospective_return_window import (
    bind_prospective_return_window,
    compile_prospective_return_window,
    settle_prospective_return_window,
)
from .search_trial_census import (
    compile_closed_book_trial_count_selection_gate,
    register_prospective_search_surface,
)
from .tournament import (
    BacktestEpisode, ObservableSpec, WorldModelCandidate, WorldModelForecast,
    evaluate_world_model_tournament,
)


POINT_IN_TIME_REPLAY_PROFILE_SCHEMA = "jaggedthoughts-point-in-time-replay-profile-v1"
POINT_IN_TIME_REPLAY_SCHEMA = "jaggedthoughts-point-in-time-forecast-replay-v1"
ARCHIVED_ACCOUNTING_REPLAY_SCHEMA = "jaggedthoughts-archived-accounting-replay-v1"
SEALED_WALK_FORWARD_PROFILE_SCHEMA = "jaggedthoughts-sealed-walk-forward-profile-v1"
SEALED_WALK_FORWARD_READINESS_SCHEMA = "jaggedthoughts-sealed-walk-forward-readiness-v1"
SEALED_WALK_FORWARD_PLAN_SCHEMA = "jaggedthoughts-sealed-walk-forward-plan-v1"
SEALED_WALK_FORWARD_ISSUANCE_SCHEMA = (
    "jaggedthoughts-sealed-walk-forward-issuance-v1"
)
SEALED_WALK_FORWARD_SETTLEMENT_REF_SCHEMA = (
    "jaggedthoughts-sealed-walk-forward-settlement-ref-v1"
)
SEALED_WALK_FORWARD_CYCLE_SCHEMA = "jaggedthoughts-sealed-walk-forward-cycle-v1"
SEALED_WALK_FORWARD_STATUS_SCHEMA = "jaggedthoughts-sealed-walk-forward-status-v1"
SEALED_WALK_FORWARD_TOURNAMENT_SCHEMA = "jaggedthoughts-sealed-walk-forward-tournament-v1"
_PROGRAM_IMPLEMENTATIONS = {
    "no_active_edge_control": "zero-active-control-v1",
    "six_month_active_momentum_control": "six-month-active-momentum-v1",
}
_PROGRAMS = set(_PROGRAM_IMPLEMENTATIONS)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any], *, immutable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    if immutable and path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"content-addressed replay changed: {path.name}")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _signed_json(
    path: Path, *, schema: str, hash_field: str,
) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    body = dict(payload)
    declared = str(body.pop(hash_field, ""))
    if body.get("schema") != schema or stable_sha256(body) != declared:
        raise ValueError(f"{path.name} has an invalid content identity")
    return payload


def _profile(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    payload = json.loads(Path(value).expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("point-in-time replay profile must be a JSON object")
    return payload


def _prices(
    packet: Mapping[str, Any], entity_ids: tuple[str, str], *, metric_id: str,
) -> dict[str, list[dict[str, Any]]]:
    result = {entity_id: [] for entity_id in entity_ids}
    for row in packet.get("observations") or ():
        entity_id = str(row.get("entity_id") or "").upper()
        if entity_id in result and row.get("metric_id") == metric_id:
            result[entity_id].append({
                "observation_id": str(row["observation_id"]),
                "entity_id": entity_id,
                "price": float(row["value"]),
                "observed_at": str(row["observed_at"]),
                "available_at": str(row["available_at"]),
                "source_ref": str(row["source_ref"]),
            })
    for rows in result.values():
        rows.sort(key=lambda row: (row["observed_at"], row["available_at"], row["observation_id"]))
    if any(not rows for rows in result.values()):
        raise ValueError(
            f"point-in-time replay requires archived entity and benchmark {metric_id} rows"
        )
    return result


def _require_archive(packet: Mapping[str, Any], label: str) -> None:
    if (
        packet.get("status") != "complete"
        or (packet.get("authority") or {}).get("evidence_replay") != "point_in_time_archive"
    ):
        raise ValueError(f"{label} lacks complete system-clock point-in-time archive coverage")


def _deterministic_forecast(
    *, replay_id: str, program_id: str, issued_at: str,
    issue_packet: Mapping[str, Any], issue_prices: Mapping[str, list[dict[str, Any]]],
    entity_id: str, benchmark_id: str, horizon_days: int,
) -> dict[str, Any]:
    if program_id == "no_active_edge_control":
        expected_active_return, underperformance_probability, target_weight = 0.0, 0.5, 0.0
    else:
        entity_trailing = _trailing_return(
            tuple(issue_prices[entity_id]), as_of=issued_at, days=182,
        )
        benchmark_trailing = _trailing_return(
            tuple(issue_prices[benchmark_id]), as_of=issued_at, days=182,
        )
        expected_active_return = entity_trailing - benchmark_trailing
        underperformance_probability = _underperformance_probability(
            expected_active_return, horizon_days,
        )
        target_weight = 0.25 if expected_active_return > 0.025 else (
            0.10 if expected_active_return > 0 else 0.0
        )
    body = {
        "schema": "jaggedthoughts-point-in-time-deterministic-forecast-v1",
        "forecast_id": f"{replay_id}:{program_id}",
        "program_id": program_id,
        "implementation": _PROGRAM_IMPLEMENTATIONS[program_id],
        "issued_at": issued_at,
        "issue_reconstruction_sha256": issue_packet["reconstruction_sha256"],
        "predicted_values": {
            "active_return": expected_active_return,
            "underperformance_event": underperformance_probability,
        },
        "target_weight": target_weight,
        "generation_process": "deterministic",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "forecast_sha256": stable_sha256(body)}


def compile_point_in_time_forecast_replay(
    workspace: str | Path,
    profile: Mapping[str, Any] | str | Path,
    *,
    _issue_packet: Mapping[str, Any] | None = None,
    _outcome_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct the issue packet, execute one fixed program, and score its later outcome."""

    config = _profile(profile)
    if config.get("schema") != POINT_IN_TIME_REPLAY_PROFILE_SCHEMA:
        raise ValueError(f"replay profile schema must be {POINT_IN_TIME_REPLAY_PROFILE_SCHEMA}")
    if config.get("capital_authority") is not False:
        raise ValueError("point-in-time replay profile must explicitly deny capital authority")
    replay_id = require_text(config.get("replay_id"), "replay_id")
    program_id = require_text(config.get("program_id"), "program_id")
    if program_id not in _PROGRAMS:
        raise ValueError(f"program_id must be one of {sorted(_PROGRAMS)}")
    entity_id = require_text(config.get("entity_id"), "entity_id").upper()
    benchmark_id = require_text(config.get("benchmark_id"), "benchmark_id").upper()
    if entity_id == benchmark_id:
        raise ValueError("replay entity and benchmark must differ")
    issued_at = canonical_timestamp(config.get("issued_at"), "replay issued_at")
    start_at = canonical_timestamp(config.get("start_at"), "replay start_at")
    evaluated_at = canonical_timestamp(config.get("evaluated_at"), "replay evaluated_at")
    if not timestamp_key(issued_at) <= timestamp_key(start_at) < timestamp_key(evaluated_at):
        raise ValueError("replay chronology must be issued_at <= start_at < evaluated_at")
    source_ids = tuple(sorted({
        require_text(value, "replay source_id") for value in config.get("source_ids") or ()
    }))
    if not source_ids:
        raise ValueError("point-in-time replay requires explicit source_ids")
    horizon_days = int(config.get("horizon_days", 0))
    cost_bps = require_finite(config.get("transaction_cost_bps", 10.0), "transaction_cost_bps")
    price_metric_id = require_text(
        config.get("price_metric_id", "adjusted_price"), "replay price_metric_id",
    )
    if price_metric_id not in {"adjusted_price", "price"}:
        raise ValueError("replay price_metric_id must be adjusted_price or price")

    if (_issue_packet is None) != (_outcome_packet is None):
        raise ValueError("replay packet override requires both issue and outcome packets")
    issue_packet = dict(_issue_packet) if _issue_packet is not None else reconstruct_evidence_as_of(
        workspace, as_of=issued_at, source_ids=source_ids,
    )
    outcome_packet = dict(_outcome_packet) if _outcome_packet is not None else reconstruct_evidence_as_of(
        workspace, as_of=evaluated_at, source_ids=source_ids,
    )
    _require_archive(issue_packet, "issue packet")
    _require_archive(outcome_packet, "outcome packet")
    issue_prices = _prices(
        issue_packet, (entity_id, benchmark_id), metric_id=price_metric_id,
    )
    outcome_prices = _prices(
        outcome_packet, (entity_id, benchmark_id), metric_id=price_metric_id,
    )

    if program_id == "no_active_edge_control":
        expected_active_return, underperformance_probability, target_weight = 0.0, 0.5, 0.0
    else:
        entity_trailing = _trailing_return(tuple(issue_prices[entity_id]), as_of=issued_at, days=182)
        benchmark_trailing = _trailing_return(
            tuple(issue_prices[benchmark_id]), as_of=issued_at, days=182,
        )
        expected_active_return = entity_trailing - benchmark_trailing
        underperformance_probability = _underperformance_probability(
            expected_active_return, horizon_days,
        )
        target_weight = 0.25 if expected_active_return > 0.025 else (
            0.10 if expected_active_return > 0 else 0.0
        )
    forecast_body = {
        "schema": "jaggedthoughts-point-in-time-deterministic-forecast-v1",
        "forecast_id": f"{replay_id}:{program_id}",
        "program_id": program_id,
        "implementation": (
            _PROGRAM_IMPLEMENTATIONS[program_id]
        ),
        "issued_at": issued_at,
        "issue_reconstruction_sha256": issue_packet["reconstruction_sha256"],
        "predicted_values": {
            "active_return": expected_active_return,
            "underperformance_event": underperformance_probability,
        },
        "target_weight": target_weight,
        "generation_process": "deterministic",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    forecast = {**forecast_body, "forecast_sha256": stable_sha256(forecast_body)}

    contract = compile_prospective_return_window(
        sealed_at=start_at, horizon_days=horizon_days,
        entity_ids=(entity_id, benchmark_id), transaction_cost_bps=cost_bps,
    )
    binding = bind_prospective_return_window(
        contract, points=outcome_prices, as_of=evaluated_at,
    )
    if binding["status"] != "bound":
        raise ValueError("historical replay has no synchronized entry observation")
    window = settle_prospective_return_window(
        contract, binding, points=outcome_prices, as_of=evaluated_at,
    )
    if window["status"] != "settled":
        raise ValueError("historical replay outcome has not reached its synchronized horizon")

    issue_observation_ids = {
        str(row["observation_id"]) for row in issue_packet["observations"]
    }
    outcome_points = [
        *binding["entry_points"].values(), *window["exit_points"].values(),
    ]
    leakage_pass = all(
        row["observation_id"] not in issue_observation_ids
        and timestamp_key(str(row["available_at"])) > timestamp_key(issued_at)
        for row in outcome_points
    )
    if not leakage_pass:
        raise ValueError("historical replay entry or exit was already available at forecast issue")

    entity_return = float(window["returns"][entity_id])
    benchmark_return = float(window["returns"][benchmark_id])
    active_return = entity_return - benchmark_return
    underperformed = float(active_return < 0.0)
    transaction_cost = target_weight * cost_bps / 10_000.0
    scores = {
        "active_return_absolute_error": ObservableSpec(
            "active_return", "decimal_return", "absolute", 1.0, 1.0,
        ).score(expected_active_return, active_return),
        "underperformance_brier": ObservableSpec(
            "underperformance_event", "probability", "brier", 1.0, 1.0,
        ).score(underperformance_probability, underperformed),
        "book_return_after_cost": target_weight * entity_return - transaction_cost,
        "active_return_contribution_after_cost": target_weight * active_return - transaction_cost,
    }
    integrity = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay",
        generation_processes=("deterministic",),
        source_availability_rows=tuple({
            "source_id": row["source_id"],
            "available_at": row["ingested_at"],
            "as_of": issued_at,
        } for row in issue_packet["sources"]),
    )
    body = {
        "schema": POINT_IN_TIME_REPLAY_SCHEMA,
        "replay_id": replay_id,
        "profile_sha256": stable_sha256(config),
        "issued_at": issued_at,
        "start_at": start_at,
        "evaluated_at": evaluated_at,
        "entity_id": entity_id,
        "benchmark_id": benchmark_id,
        "price_metric_id": price_metric_id,
        "source_ids": list(source_ids),
        "issue_packet": issue_packet,
        "outcome_reconstruction_sha256": outcome_packet["reconstruction_sha256"],
        "forecast": forecast,
        "return_window": contract,
        "return_window_binding": binding,
        "return_window_settlement": window,
        "actual_values": {
            "entity_return": entity_return,
            "benchmark_return": benchmark_return,
            "active_return": active_return,
            "underperformance_event": underperformed,
        },
        "scores": scores,
        "temporal_integrity": {
            "issue_packet_content_verified": True,
            "outcome_packet_content_verified": True,
            "forecast_inputs_from_issue_packet_only": True,
            "entry_and_exit_absent_at_issue": leakage_pass,
            "issue_observation_count": len(issue_observation_ids),
            "outcome_point_ids_sha256": stable_sha256(sorted(
                str(row["observation_id"]) for row in outcome_points
            )),
        },
        "evaluation_integrity": integrity,
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "model_fit_authority": False,
        "capital_authority": False,
        "use_boundary": (
            "Deterministic point-in-time backtest evidence; the program family was selected "
            "retrospectively and cannot authorize a portfolio policy."
        ),
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def _walk_forward_subject(raw: Mapping[str, Any], index: int) -> dict[str, str]:
    entity_kind = require_text(raw.get("entity_kind"), f"subject {index} entity_kind")
    if entity_kind not in {"public_equity", "public_fund"}:
        raise ValueError("walk-forward subjects must be public_equity or public_fund")
    entity_id = require_text(raw.get("entity_id"), f"subject {index} entity_id").upper()
    benchmark_id = require_text(
        raw.get("benchmark_id"), f"subject {index} benchmark_id",
    ).upper()
    if entity_id == benchmark_id:
        raise ValueError("walk-forward subject and benchmark must differ")
    return {
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "price_source_id": require_text(
            raw.get("price_source_id"), f"subject {index} price_source_id",
        ),
        "benchmark_id": benchmark_id,
        "benchmark_source_id": require_text(
            raw.get("benchmark_source_id"), f"subject {index} benchmark_source_id",
        ),
    }


def _walk_forward_window(raw: Mapping[str, Any], index: int) -> dict[str, Any]:
    issued_at = canonical_timestamp(raw.get("issued_at"), f"window {index} issued_at")
    start_at = canonical_timestamp(raw.get("start_at"), f"window {index} start_at")
    evaluated_at = canonical_timestamp(
        raw.get("evaluated_at"), f"window {index} evaluated_at",
    )
    horizon_days = int(raw.get("horizon_days", 0))
    if horizon_days <= 0:
        raise ValueError("walk-forward horizon_days must be positive")
    if not timestamp_key(issued_at) <= timestamp_key(start_at) < timestamp_key(evaluated_at):
        raise ValueError("walk-forward chronology must be issued_at <= start_at < evaluated_at")
    required_outcome_at = canonical_timestamp(
        (timestamp_key(start_at) + timedelta(days=horizon_days)).isoformat(),
        f"window {index} required outcome time",
    )
    if timestamp_key(required_outcome_at) > timestamp_key(evaluated_at):
        raise ValueError("walk-forward evaluated_at must follow the complete horizon")
    return {
        "window_id": require_text(raw.get("window_id"), f"window {index} window_id"),
        "issued_at": issued_at,
        "start_at": start_at,
        "required_outcome_at": required_outcome_at,
        "evaluated_at": evaluated_at,
        "horizon_days": horizon_days,
    }


def _independent_window_count(windows: tuple[Mapping[str, Any], ...]) -> int:
    """Count connected components of overlapping return windows."""

    intervals = sorted(
        (timestamp_key(str(row["start_at"])), timestamp_key(str(row["required_outcome_at"])))
        for row in windows
    )
    count = 0
    group_end = None
    for start, end in intervals:
        if group_end is None or start > group_end:
            count += 1
            group_end = end
        else:
            group_end = max(group_end, end)
    return count


def _program_bundle(programs: tuple[str, ...]) -> dict[str, Any]:
    source_sha = stable_sha256({
        "compile_point_in_time_forecast_replay": inspect.getsource(
            compile_point_in_time_forecast_replay
        ),
        "bind_prospective_return_window": inspect.getsource(
            bind_prospective_return_window
        ),
        "settle_prospective_return_window": inspect.getsource(
            settle_prospective_return_window
        ),
        "trailing_return": inspect.getsource(_trailing_return),
        "underperformance_probability": inspect.getsource(
            _underperformance_probability
        ),
    })
    body = {
        "implementations": {
            program_id: _PROGRAM_IMPLEMENTATIONS[program_id]
            for program_id in programs
        },
        "implementation_source_sha256": source_sha,
    }
    return {**body, "program_bundle_sha256": stable_sha256(body)}


def compile_sealed_walk_forward_readiness(
    workspace: str | Path, profile: Mapping[str, Any] | str | Path,
    *, as_of: str | None = None,
) -> dict[str, Any]:
    """Prove whether a cross-kind rolling replay has enough system-clock archive.

    This deliberately stops before model execution.  A historical cutoff that
    predates the first immutable capture cannot be repaired by downloading old
    rows today.
    """

    config = _profile(profile)
    archive_cutoff = canonical_timestamp(as_of or _utc_now(), "walk-forward archive cutoff")
    if config.get("schema") != SEALED_WALK_FORWARD_PROFILE_SCHEMA:
        raise ValueError(
            f"walk-forward profile schema must be {SEALED_WALK_FORWARD_PROFILE_SCHEMA}"
        )
    if config.get("capital_authority") is not False:
        raise ValueError("walk-forward profile must explicitly deny capital authority")
    evaluation_id = require_text(config.get("evaluation_id"), "walk-forward evaluation_id")
    programs = tuple(sorted({
        require_text(value, "walk-forward program_id")
        for value in config.get("program_ids") or ()
    }))
    if not programs or not set(programs) <= _PROGRAMS:
        raise ValueError(f"program_ids must be a nonempty subset of {sorted(_PROGRAMS)}")
    subject_rows = config.get("subjects") or ()
    window_rows = config.get("windows") or ()
    if (
        not isinstance(subject_rows, list) or not subject_rows
        or not all(isinstance(row, Mapping) for row in subject_rows)
        or not isinstance(window_rows, list) or not window_rows
        or not all(isinstance(row, Mapping) for row in window_rows)
    ):
        raise ValueError("walk-forward profile requires subjects and windows")
    subjects = tuple(
        _walk_forward_subject(row, index) for index, row in enumerate(subject_rows)
    )
    windows = tuple(
        _walk_forward_window(row, index) for index, row in enumerate(window_rows)
    )
    subject_ids = [row["entity_id"] for row in subjects]
    window_ids = [str(row["window_id"]) for row in windows]
    if len(subject_ids) != len(set(subject_ids)) or len(window_ids) != len(set(window_ids)):
        raise ValueError("walk-forward subject and window identities must be unique")
    minimum_blocks = int(config.get("minimum_inference_blocks", 8))
    if minimum_blocks < 5:
        raise ValueError("walk-forward minimum_inference_blocks must be at least 5")

    root = Path(workspace).expanduser().resolve()
    store = GoldenStore(root / "state" / "golden_store.sqlite3")
    required_sources = {
        source_id
        for row in subjects
        for source_id in (row["price_source_id"], row["benchmark_source_id"])
    }
    captures: dict[str, list[str]] = {source_id: [] for source_id in required_sources}
    declared_clock_capture_count = 0
    for leaf in store.list_leaves(
        owner="jaggedthoughts-evidence-vault",
        object_kind="point_in_time_evidence_snapshot",
        object_ids=required_sources,
        limit=10_000,
    ):
        source_id = str(leaf["object_id"])
        if source_id in captures:
            payload = dict(store.get_leaf(str(leaf["leaf_sha256"])).get("payload") or {})
            if (payload.get("epochs") or {}).get("ingestion_clock_authority") == "system_clock":
                captures[source_id].append(str(leaf["available_at"]))
            else:
                declared_clock_capture_count += 1
    for values in captures.values():
        values.sort(key=timestamp_key)
    all_capture_times = [value for values in captures.values() for value in values]
    first_capture = min(all_capture_times, key=timestamp_key) if all_capture_times else None
    latest_capture = max(all_capture_times, key=timestamp_key) if all_capture_times else None

    cells = []
    for window in windows:
        for subject in subjects:
            source_ids = (subject["price_source_id"], subject["benchmark_source_id"])
            issue_heads = {
                source_id: max(
                    (value for value in captures[source_id]
                     if timestamp_key(value) <= timestamp_key(str(window["issued_at"]))),
                    key=timestamp_key, default=None,
                )
                for source_id in source_ids
            }
            outcome_heads = {
                source_id: min(
                    (value for value in captures[source_id]
                     if timestamp_key(str(window["required_outcome_at"])) <= timestamp_key(value)
                     <= timestamp_key(archive_cutoff)),
                    key=timestamp_key, default=None,
                )
                for source_id in source_ids
            }
            blockers = []
            if any(value is None for value in issue_heads.values()):
                blockers.append("issue_capture_missing")
            if any(value is None for value in outcome_heads.values()):
                blockers.append("matured_outcome_capture_missing")
            unrecoverable_sources = sorted(
                source_id for source_id in source_ids
                if (
                    captures[source_id]
                    and timestamp_key(str(window["issued_at"]))
                    < timestamp_key(captures[source_id][0])
                ) or (
                    not captures[source_id] and latest_capture
                    and timestamp_key(str(window["issued_at"])) < timestamp_key(latest_capture)
                )
            )
            historical_unrecoverable = bool(unrecoverable_sources)
            if historical_unrecoverable:
                blockers.append("historical_issue_cutoff_predates_archive")
            cells.append({
                "cell_id": f"{window['window_id']}:{subject['entity_id']}",
                "window_id": window["window_id"],
                "entity_id": subject["entity_id"],
                "entity_kind": subject["entity_kind"],
                "source_ids": list(source_ids),
                "issue_snapshot_available_at": issue_heads,
                "outcome_snapshot_available_at": outcome_heads,
                "archive_ready": not blockers,
                "blockers": blockers,
                "historical_backfill_forbidden": historical_unrecoverable,
                "historical_backfill_forbidden_source_ids": unrecoverable_sources,
            })
    archive_ready = all(row["archive_ready"] for row in cells)
    block_count = _independent_window_count(windows)
    inference_ready = block_count >= minimum_blocks
    if not archive_ready:
        status = "archive_not_ready"
    elif not inference_ready:
        status = "inference_not_ready"
    else:
        status = "ready_for_deterministic_walk_forward"
    body = {
        "schema": SEALED_WALK_FORWARD_READINESS_SCHEMA,
        "evaluation_id": evaluation_id,
        "profile_sha256": stable_sha256(config),
        "archive_checked_at": archive_cutoff,
        "status": status,
        "generation_process": "deterministic",
        "price_metric_id": "adjusted_price",
        "program_ids": list(programs),
        "program_bundle": _program_bundle(programs),
        "subject_count": len(subjects),
        "entity_kinds": sorted({row["entity_kind"] for row in subjects}),
        "window_count": len(windows),
        "first_window_evaluated_at": min(
            str(row["evaluated_at"]) for row in windows
        ),
        "last_window_evaluated_at": max(
            str(row["evaluated_at"]) for row in windows
        ),
        "evaluation_cell_count": len(cells),
        "first_required_source_capture_at": first_capture,
        "latest_required_source_capture_at": latest_capture,
        "required_source_count": len(required_sources),
        "excluded_declared_clock_capture_count": declared_clock_capture_count,
        "independent_window_count": block_count,
        "minimum_inference_blocks": minimum_blocks,
        "archive_ready": archive_ready,
        "inference_ready": inference_ready,
        "cells": cells,
        "next_activation": (
            "execute_complete_deterministic_matrix"
            if status == "ready_for_deterministic_walk_forward"
            else "continue_system_clock_capture_without_backfill"
        ),
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
        "use_boundary": (
            "Readiness only. evaluated_at is a no-earlier-than boundary; a later market-day "
            "capture may settle the unchanged issue packet. Current-universe selection, "
            "program-family selection, and fewer "
            "than the declared independent blocks cannot support a policy or alpha claim."
        ),
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def _walk_forward_cell_id(
    evaluation_id: str, profile_sha256: str, window_id: str,
    entity_id: str, program_id: str,
) -> str:
    return ":".join((
        evaluation_id, profile_sha256[:16], window_id, entity_id, program_id,
    ))


def _walk_forward_trial_family_id(evaluation_id: str, profile_sha256: str) -> str:
    return f"sealed-walk-forward:{evaluation_id}:{profile_sha256[:16]}"


def _walk_forward_models(
    *, evaluation_id: str, profile_sha256: str, plan_leaf_sha256: str,
    program_bundle: Mapping[str, Any], program_ids: tuple[str, ...],
) -> tuple[WorldModelCandidate, ...]:
    family_id = _walk_forward_trial_family_id(evaluation_id, profile_sha256)
    source_sha = require_text(
        program_bundle.get("implementation_source_sha256"),
        "walk-forward implementation source hash",
    )
    return tuple(WorldModelCandidate(
        model_id=program_id,
        version=str((program_bundle.get("implementations") or {})[program_id]),
        model_family="sealed_walk_forward_deterministic_program",
        trial_family_id=family_id,
        mechanism_ids=(f"deterministic_forecast_rule:{program_id}",),
        linked_observable_ids=(),
        source_refs=(
            f"plan:{plan_leaf_sha256}", f"implementation-source:{source_sha}",
        ),
        generation_process="deterministic",
    ) for program_id in program_ids)


def sealed_walk_forward_status(
    workspace: str | Path,
    profile: Mapping[str, Any] | str | Path,
    *,
    as_of: str | None = None,
    owner: str = "operator-paper-book",
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Project the next deterministic matrix transition without mutating state."""

    root = Path(workspace).expanduser().resolve()
    evaluated_at = canonical_timestamp(as_of or _utc_now(), "walk-forward status as_of")
    config = _profile(profile)
    readiness = compile_sealed_walk_forward_readiness(root, config, as_of=evaluated_at)
    evaluation_id = str(readiness["evaluation_id"])
    profile_sha = str(readiness["profile_sha256"])
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    plan = store.identity(
        owner, "sealed_walk_forward_plan", evaluation_id, profile_sha,
    )
    plan_sha = str((plan or {}).get("leaf_sha256") or "")
    sealed_at = str((plan or {}).get("available_at") or "")
    planned_bundle_sha = str(
        ((((plan or {}).get("payload") or {}).get("program_bundle") or {}).get(
            "program_bundle_sha256"
        )) or ""
    )
    current_bundle_sha = str(readiness["program_bundle"]["program_bundle_sha256"])
    implementation_drift = bool(
        plan_sha and planned_bundle_sha != current_bundle_sha
    )
    subjects = tuple(
        _walk_forward_subject(row, index)
        for index, row in enumerate(config.get("subjects") or ())
    )
    windows = tuple(
        _walk_forward_window(row, index)
        for index, row in enumerate(config.get("windows") or ())
    )
    programs = tuple(readiness["program_ids"])
    object_ids = tuple(
        _walk_forward_cell_id(
            evaluation_id, profile_sha, str(window["window_id"]),
            str(subject["entity_id"]), program_id,
        )
        for window in windows for subject in subjects for program_id in programs
    )
    issued_heads = {
        str(row["object_id"]): row
        for row in store.heads_as_of(
            owner, "sealed_walk_forward_issuance", evaluated_at,
            object_ids=object_ids,
        )
        if (row.get("payload") or {}).get("plan_leaf_sha256") == plan_sha
    } if plan_sha else {}
    settled_heads = {
        str(row["object_id"]): row
        for row in store.heads_as_of(
            owner, "sealed_walk_forward_settlement", evaluated_at,
            object_ids=object_ids,
        )
        if (row.get("payload") or {}).get("plan_leaf_sha256") == plan_sha
    } if plan_sha else {}
    readiness_by_cell = {
        str(row["cell_id"]): row for row in readiness.get("cells") or ()
    }
    rows = []
    for window in windows:
        for subject in subjects:
            base_id = f"{window['window_id']}:{subject['entity_id']}"
            archive = readiness_by_cell[base_id]
            for program_id in programs:
                object_id = _walk_forward_cell_id(
                    evaluation_id, profile_sha, str(window["window_id"]),
                    str(subject["entity_id"]), program_id,
                )
                issuance = issued_heads.get(object_id)
                issuance_payload = dict((issuance or {}).get("payload") or {})
                settlement = settled_heads.get(object_id)
                settlement_payload = dict((settlement or {}).get("payload") or {})
                issue_archive_ready = all(
                    archive["issue_snapshot_available_at"].get(source_id)
                    for source_id in archive["source_ids"]
                )
                if settlement:
                    state = "settled"
                    blockers: list[str] = []
                elif not plan_sha:
                    state = "awaiting_plan_seal"
                    blockers = ["plan_not_system_clock_sealed"]
                elif implementation_drift:
                    state = "implementation_drift"
                    blockers = ["sealed_program_bundle_changed"]
                elif timestamp_key(sealed_at) > timestamp_key(str(window["issued_at"])):
                    state = "invalid_late_plan_seal"
                    blockers = ["plan_sealed_after_issue"]
                elif timestamp_key(evaluated_at) < timestamp_key(str(window["issued_at"])):
                    state = "awaiting_issue_time"
                    blockers = ["forecast_issue_time_not_due"]
                elif not issuance and timestamp_key(evaluated_at) >= timestamp_key(
                    str(window["start_at"])
                ):
                    state = "missed_issue_window"
                    blockers = ["forecast_not_materialized_before_entry"]
                elif not issuance and not issue_archive_ready:
                    state = "awaiting_issue_archive"
                    blockers = ["issue_capture_missing"]
                elif not issuance:
                    state = "issuance_due"
                    blockers = []
                elif timestamp_key(evaluated_at) < timestamp_key(str(window["evaluated_at"])):
                    state = "awaiting_evaluation_time"
                    blockers = ["outcome_window_not_due"]
                elif not archive["archive_ready"]:
                    state = "awaiting_archive"
                    blockers = list(archive["blockers"])
                else:
                    state = "activation_due"
                    blockers = []
                rows.append({
                    "cell_id": object_id,
                    "base_cell_id": base_id,
                    "window_id": window["window_id"],
                    "entity_id": subject["entity_id"],
                    "entity_kind": subject["entity_kind"],
                    "program_id": program_id,
                    "issued_at": window["issued_at"],
                    "start_at": window["start_at"],
                    "evaluated_at": window["evaluated_at"],
                    "state": state,
                    "blockers": blockers,
                    "issue_snapshot_available_at": archive["issue_snapshot_available_at"],
                    "outcome_snapshot_available_at": archive["outcome_snapshot_available_at"],
                    "issue_archive_ready": issue_archive_ready,
                    "archive_ready": archive["archive_ready"],
                    "historical_backfill_forbidden": archive[
                        "historical_backfill_forbidden"
                    ],
                    "issuance_leaf_sha256": (
                        issuance.get("leaf_sha256") if issuance else None
                    ),
                    "forecast_sha256": (
                        (issuance_payload.get("forecast") or {}).get("forecast_sha256")
                        if issuance else None
                    ),
                    "materialized_at": (
                        issuance_payload.get("materialized_at") if issuance else None
                    ),
                    "settlement_leaf_sha256": (
                        settlement.get("leaf_sha256") if settlement else None
                    ),
                    "replay_sha256": (
                        settlement_payload.get("replay_sha256")
                        if settlement else None
                    ),
                    "outcome_evaluated_at": (
                        settlement_payload.get("evaluated_at") if settlement else None
                    ),
                })
    counts = {
        state: sum(row["state"] == state for row in rows)
        for state in (
            "issuance_due", "activation_due", "awaiting_plan_seal",
            "awaiting_issue_time", "awaiting_issue_archive",
            "awaiting_evaluation_time", "awaiting_archive", "missed_issue_window",
            "invalid_late_plan_seal", "implementation_drift", "settled",
        )
    }
    rows_by_base: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_base.setdefault(str(row["base_cell_id"]), []).append(row)
    complete_bases = tuple(sorted(
        base_id for base_id, base_rows in rows_by_base.items()
        if len(base_rows) == len(programs)
        and all(row["state"] == "settled" for row in base_rows)
    ))
    tournament_input_sha = (
        stable_sha256(sorted(
            str(row["replay_sha256"])
            for base_id in complete_bases for row in rows_by_base[base_id]
        ))
        if complete_bases else None
    )
    latest_tournament = _signed_json(
        root / "point_in_time_replay" / "tournaments" / "latest.json",
        schema="jaggedthoughts-world-model-tournament-v1",
        hash_field="tournament_sha256",
    )
    if latest_tournament and (
        latest_tournament.get("walk_forward_evaluation_id") != evaluation_id
        or latest_tournament.get("walk_forward_profile_sha256") != profile_sha
    ):
        latest_tournament = None
    tournament_refresh_due = bool(
        tournament_input_sha
        and (
            not latest_tournament
            or latest_tournament.get("walk_forward_input_sha256")
            != tournament_input_sha
        )
    )
    latest_cycle_rows = store.heads_as_of(
        owner, "sealed_walk_forward_cycle", evaluated_at,
        object_ids=(evaluation_id,),
    )
    latest_cycle = None
    if latest_cycle_rows:
        cycle = latest_cycle_rows[0]
        payload = dict(cycle.get("payload") or {})
        if payload.get("profile_sha256") == profile_sha:
            latest_cycle = {
                "cycle_id": payload.get("cycle_id"),
                "run_sha256": payload.get("run_sha256"),
                "activated_at": payload.get("activated_at"),
                "leaf_sha256": cycle.get("leaf_sha256"),
            }
    if not plan_sha:
        status = "plan_seal_due"
        next_activation = "seal_profile_before_future_issue_cutoffs"
    elif implementation_drift:
        status = "program_implementation_changed"
        next_activation = "open_a_new_evaluation_epoch_before_future_issue_cutoffs"
    elif counts["issuance_due"]:
        status = "matrix_issuance_due"
        next_activation = "materialize_due_forecasts_before_market_entry"
    elif counts["activation_due"]:
        status = "matrix_execution_due"
        next_activation = "execute_due_deterministic_cells"
    elif tournament_refresh_due:
        status = "tournament_refresh_due"
        next_activation = "compile_block_aware_program_tournament"
    elif counts["settled"] == len(rows):
        status = "matrix_settled"
        next_activation = "compile_or_refresh_deterministic_tournament"
    else:
        status = "collecting_system_clock_evidence"
        next_activation = "wait_for_due_horizon_and_system_clock_capture"
    body = {
        "schema": SEALED_WALK_FORWARD_STATUS_SCHEMA,
        "evaluation_id": evaluation_id,
        "profile_sha256": profile_sha,
        "evaluated_at": evaluated_at,
        "status": status,
        "subject_count": readiness["subject_count"],
        "entity_kinds": readiness["entity_kinds"],
        "window_count": readiness["window_count"],
        "evaluation_cell_count": readiness["evaluation_cell_count"],
        "first_window_evaluated_at": readiness["first_window_evaluated_at"],
        "last_window_evaluated_at": readiness["last_window_evaluated_at"],
        "independent_window_count": readiness["independent_window_count"],
        "minimum_inference_blocks": readiness["minimum_inference_blocks"],
        "archive_ready": readiness["archive_ready"],
        "inference_ready": readiness["inference_ready"],
        "plan": {
            "sealed": bool(plan_sha),
            "plan_leaf_sha256": plan_sha or None,
            "sealed_at": sealed_at or None,
            "seal_due": not bool(plan_sha),
            "program_bundle_sha256": planned_bundle_sha or None,
            "implementation_matches": bool(plan_sha and not implementation_drift),
        },
        "readiness": readiness,
        "program_cell_count": len(rows),
        "counts": counts,
        "issuance_due_count": counts["issuance_due"],
        "issued_count": sum(bool(row["issuance_leaf_sha256"]) for row in rows),
        "activation_due_count": counts["activation_due"],
        "complete_tournament_episode_count": len(complete_bases),
        "walk_forward_input_sha256": tournament_input_sha,
        "tournament_refresh_due": tournament_refresh_due,
        "periodic_activation_due": bool(
            not implementation_drift
            and (
                not plan_sha or counts["issuance_due"]
                or counts["activation_due"] or tournament_refresh_due
            )
        ),
        "latest_cycle": latest_cycle,
        "tournament": ({
            "tournament_sha256": latest_tournament.get("tournament_sha256"),
            "as_of": latest_tournament.get("as_of"),
            "inference_block_count": latest_tournament.get("inference_block_count"),
            "inference_sufficient": latest_tournament.get("inference_sufficient"),
            "survivor_model_ids": latest_tournament.get("survivor_model_ids"),
            "selection_gate": latest_tournament.get("selection_gate"),
            "research_priority_evidence_eligible": latest_tournament.get(
                "research_priority_evidence_eligible"
            ),
        } if latest_tournament else None),
        "cells": rows,
        "next_activation": next_activation,
        "generation_process": "deterministic",
        "historical_repair_allowed": False,
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def compile_sealed_walk_forward_tournament(
    workspace: str | Path,
    profile: Mapping[str, Any] | str | Path,
    *,
    as_of: str | None = None,
    owner: str = "operator-paper-book",
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Lower complete sealed cells into the shared block-aware tournament."""

    root = Path(workspace).expanduser().resolve()
    config = _profile(profile)
    status = sealed_walk_forward_status(
        root, config, as_of=as_of, owner=owner, store_path=store_path,
    )
    plan_sha = str((status.get("plan") or {}).get("plan_leaf_sha256") or "")
    if not plan_sha or not int(status.get("complete_tournament_episode_count") or 0):
        raise ValueError("walk-forward tournament requires a sealed complete episode")
    if status["status"] == "program_implementation_changed":
        raise ValueError("walk-forward program implementation no longer matches its seal")
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    plan = store.get_leaf(plan_sha)
    plan_payload = dict(plan["payload"])
    programs = tuple(status["readiness"]["program_ids"])
    models = _walk_forward_models(
        evaluation_id=str(status["evaluation_id"]),
        profile_sha256=str(status["profile_sha256"]),
        plan_leaf_sha256=plan_sha,
        program_bundle=dict(plan_payload["program_bundle"]),
        program_ids=programs,
    )
    family_id = _walk_forward_trial_family_id(
        str(status["evaluation_id"]), str(status["profile_sha256"]),
    )
    try:
        family_leaf = store.head(owner, "search_trial_family", family_id)
    except KeyError as error:
        raise ValueError("walk-forward exact search-trial family is not registered") from error
    family = dict(family_leaf["payload"])

    complete: dict[str, list[Mapping[str, Any]]] = {}
    for row in status["cells"]:
        if row["state"] == "settled":
            complete.setdefault(str(row["base_cell_id"]), []).append(row)
    complete = {
        key: rows for key, rows in complete.items()
        if len(rows) == len(programs)
    }
    replay_rows: dict[str, dict[str, dict[str, Any]]] = {}
    settlement_leaf_shas = []
    for base_id, cells in sorted(complete.items()):
        replay_rows[base_id] = {}
        for cell in cells:
            settlement = store.get_leaf(str(cell["settlement_leaf_sha256"]))
            reference = dict(settlement["payload"])
            replay = _signed_json(
                root / str(reference["replay_path"]),
                schema=POINT_IN_TIME_REPLAY_SCHEMA,
                hash_field="replay_sha256",
            )
            if replay is None or replay["replay_sha256"] != reference["replay_sha256"]:
                raise ValueError(f"walk-forward replay identity mismatch: {cell['cell_id']}")
            replay_rows[base_id][str(cell["program_id"])] = replay
            settlement_leaf_shas.append(str(settlement["leaf_sha256"]))

    interval_rows = []
    for base_id, by_program in replay_rows.items():
        baseline = by_program["no_active_edge_control"]
        outcomes = {
            stable_sha256({
                "actual_values": replay["actual_values"],
                "outcome_reconstruction_sha256": replay["outcome_reconstruction_sha256"],
                "return_window_binding": replay["return_window_binding"],
                "return_window_settlement": replay["return_window_settlement"],
            })
            for replay in by_program.values()
        }
        if len(outcomes) != 1:
            raise ValueError(f"walk-forward program arms disagree on outcome: {base_id}")
        interval_rows.append({
            "run_id": base_id,
            "return_window_binding": baseline["return_window_binding"],
            "return_window_settlement": baseline["return_window_settlement"],
        })
    block_ids = overlap_cluster_ids(interval_rows)
    horizon_days = {
        int(replay["return_window"]["horizon_days"])
        for by_program in replay_rows.values() for replay in by_program.values()
    }
    if len(horizon_days) != 1:
        raise ValueError("one walk-forward tournament requires a common return horizon")

    episodes = []
    forecasts = []
    for base_id, by_program in sorted(replay_rows.items()):
        baseline = by_program["no_active_edge_control"]
        actual = dict(baseline["actual_values"])
        episodes.append(BacktestEpisode(
            episode_id=base_id,
            inference_block_id=block_ids[base_id],
            entity_id=str(baseline["entity_id"]),
            start_at=str(baseline["return_window_binding"]["entry_observed_at"]),
            end_at=str(
                baseline["return_window_settlement"]["exit_observed_at"]
            ),
            outcome_available_at=str(baseline["evaluated_at"]),
            starting_weight=0.0,
            asset_return=float(actual["entity_return"]),
            benchmark_return=float(actual["benchmark_return"]),
            cash_return=0.0,
            actual_values={
                "active_return": float(actual["active_return"]),
                "underperformance_event": float(actual["underperformance_event"]),
            },
            source_refs=tuple(sorted({
                *(f"source:{value}" for value in baseline["source_ids"]),
                *(f"replay:{row['replay_sha256']}" for row in by_program.values()),
            })),
        ))
        for program_id, replay in sorted(by_program.items()):
            forecast = dict(replay["forecast"])
            forecasts.append(WorldModelForecast(
                model_id=program_id,
                episode_id=base_id,
                trained_through=str(replay["issued_at"]),
                issued_at=str(replay["issued_at"]),
                predicted_values={
                    "active_return": float(forecast["predicted_values"]["active_return"]),
                    "underperformance_event": float(
                        forecast["predicted_values"]["underperformance_event"]
                    ),
                },
                target_weight=float(forecast["target_weight"]),
                source_refs=(
                    f"plan:{plan_sha}",
                    f"forecast:{forecast['forecast_sha256']}",
                    f"issue:{forecast['issue_reconstruction_sha256']}",
                ),
            ))

    tournament_as_of = max(row.outcome_available_at for row in episodes)
    horizon = next(iter(horizon_days))
    result = evaluate_world_model_tournament(
        tournament_id=(
            f"sealed-walk-forward::{status['evaluation_id']}::"
            f"{str(status['profile_sha256'])[:12]}"
        ),
        owner=owner,
        as_of=tournament_as_of,
        mode="prospective_shadow",
        baseline_model_id="no_active_edge_control",
        observables=(
            ObservableSpec("active_return", "decimal_return", "absolute", 0.10, 0.70),
            ObservableSpec(
                "underperformance_event", "probability", "brier", 1.0, 0.30,
            ),
        ),
        models=models,
        episodes=tuple(episodes),
        forecasts=tuple(forecasts),
        transaction_cost_bps=float(config.get("transaction_cost_bps", 10.0)),
        declared_trial_family_ids=(family_id,),
        source_refs=tuple(sorted({
            f"plan:{plan_sha}", f"trial-family:{family_leaf['leaf_sha256']}",
            *(f"settlement:{value}" for value in settlement_leaf_shas),
        })),
        min_inference_blocks=int(config.get("minimum_inference_blocks", 8)),
        periods_per_year=365.25 / horizon,
    )
    selection_gate = compile_closed_book_trial_count_selection_gate(
        family=family, tournament=result,
    )
    body = dict(result)
    body.pop("tournament_sha256")
    body.update({
        "walk_forward_adapter_schema": SEALED_WALK_FORWARD_TOURNAMENT_SCHEMA,
        "walk_forward_evaluation_id": status["evaluation_id"],
        "walk_forward_profile_sha256": status["profile_sha256"],
        "walk_forward_input_sha256": status["walk_forward_input_sha256"],
        "exact_search_trial_family_sha256": family["trial_family_sha256"],
        "selection_gate": selection_gate,
        "research_priority_evidence_eligible": bool(
            selection_gate.get("selection_adjusted_candidate_evidence")
        ),
        "research_priority_candidate_program_ids": (
            [selection_gate["selected_candidate_id"]]
            if selection_gate.get("selection_adjusted_candidate_evidence") else []
        ),
        "research_priority_authority": "review_only",
        "queue_mutation_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    })
    return {**body, "tournament_sha256": stable_sha256(body)}


def run_sealed_walk_forward_cycle(
    workspace: str | Path,
    profile: Mapping[str, Any] | str | Path,
    *,
    as_of: str | None = None,
    owner: str = "operator-paper-book",
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Seal the plan and execute each newly mature deterministic matrix cell once."""

    root = Path(workspace).expanduser().resolve()
    activated_at = canonical_timestamp(as_of or _utc_now(), "walk-forward activation time")
    config = _profile(profile)
    readiness = compile_sealed_walk_forward_readiness(root, config, as_of=activated_at)
    evaluation_id = str(readiness["evaluation_id"])
    profile_sha = str(readiness["profile_sha256"])
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    plan = store.identity(owner, "sealed_walk_forward_plan", evaluation_id, profile_sha)
    plan_created = plan is None
    if plan is None:
        plan_payload = {
            "schema": SEALED_WALK_FORWARD_PLAN_SCHEMA,
            "evaluation_id": evaluation_id,
            "profile_sha256": profile_sha,
            "sealed_at": activated_at,
            "profile": config,
            "program_bundle": readiness["program_bundle"],
            "generation_process": "deterministic",
            "historical_repair_allowed": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        }
        plan_leaf = GoldenLeaf(
            owner=owner,
            object_kind="sealed_walk_forward_plan",
            object_id=evaluation_id,
            epoch=profile_sha,
            occurred_at=activated_at,
            available_at=activated_at,
            payload=plan_payload,
            source_refs=(f"walk-forward-profile:{profile_sha}",),
        )
        store.append_bundle((plan_leaf,), make_heads=True)
        plan = store.get_leaf(plan_leaf.leaf_sha256)
    plan_sha = str(plan["leaf_sha256"])
    plan_payload = dict(plan["payload"])
    trial_models = _walk_forward_models(
        evaluation_id=evaluation_id,
        profile_sha256=profile_sha,
        plan_leaf_sha256=plan_sha,
        program_bundle=dict(plan_payload["program_bundle"]),
        program_ids=tuple(readiness["program_ids"]),
    )
    trial_family = register_prospective_search_surface(
        root,
        owner=owner,
        trial_family_id=_walk_forward_trial_family_id(evaluation_id, profile_sha),
        research_question=(
            "Which sealed deterministic control program improves future prediction loss "
            "and after-cost benchmark-relative return across independent market windows?"
        ),
        model_family="world_model_tournament",
        selection_unit="sealed_deterministic_program",
        candidate_ids=tuple(model.model_sha256 for model in trial_models),
        declared_at=activated_at,
        outcome_access_after=max(
            str(_walk_forward_window(row, index)["evaluated_at"])
            for index, row in enumerate(config.get("windows") or ())
        ),
        generator_receipts=(
            f"walk-forward-plan:{plan_sha}",
            f"program-bundle:{readiness['program_bundle']['program_bundle_sha256']}",
        ),
        source_refs=(f"walk-forward-profile:{profile_sha}",),
        store_path=store_path or root / "state" / "golden_store.sqlite3",
    )
    before = sealed_walk_forward_status(
        root, config, as_of=activated_at, owner=owner, store_path=store_path,
    )
    if (
        not plan_created
        and not int(before.get("issuance_due_count") or 0)
        and not int(before.get("activation_due_count") or 0)
        and not before.get("tournament_refresh_due")
    ):
        return {
            "ok": True, "status": "not_due", "run": None,
            "trial_family": trial_family,
            "matrix_status": before, "capital_authority": False,
        }
    subject_by_id = {
        row["entity_id"]: row
        for index, raw in enumerate(config.get("subjects") or ())
        for row in (_walk_forward_subject(raw, index),)
    }
    window_by_id = {
        row["window_id"]: row
        for index, raw in enumerate(config.get("windows") or ())
        for row in (_walk_forward_window(raw, index),)
    }
    issuance_actions = []
    issuance_leaf_shas = []
    issue_packet_cache: dict[str, dict[str, Any]] = {}
    for cell in before["cells"]:
        if cell["state"] != "issuance_due":
            continue
        try:
            subject = subject_by_id[str(cell["entity_id"])]
            window = window_by_id[str(cell["window_id"])]
            base_id = str(cell["base_cell_id"])
            source_ids = tuple(sorted({
                subject["price_source_id"], subject["benchmark_source_id"],
            }))
            if base_id not in issue_packet_cache:
                issue_packet_cache[base_id] = reconstruct_evidence_as_of(
                    root, as_of=str(window["issued_at"]), source_ids=source_ids,
                    store_path=store_path,
                )
            issue_packet = issue_packet_cache[base_id]
            _require_archive(issue_packet, "walk-forward issue packet")
            issue_prices = _prices(
                issue_packet, (subject["entity_id"], subject["benchmark_id"]),
                metric_id="adjusted_price",
            )
            forecast = _deterministic_forecast(
                replay_id=str(cell["cell_id"]), program_id=str(cell["program_id"]),
                issued_at=str(window["issued_at"]), issue_packet=issue_packet,
                issue_prices=issue_prices, entity_id=subject["entity_id"],
                benchmark_id=subject["benchmark_id"],
                horizon_days=int(window["horizon_days"]),
            )
            issuance_body = {
                "schema": SEALED_WALK_FORWARD_ISSUANCE_SCHEMA,
                "evaluation_id": evaluation_id,
                "profile_sha256": profile_sha,
                "plan_leaf_sha256": plan_sha,
                "cell_id": cell["cell_id"],
                "window_id": cell["window_id"],
                "entity_id": cell["entity_id"],
                "entity_kind": cell["entity_kind"],
                "benchmark_id": subject["benchmark_id"],
                "program_id": cell["program_id"],
                "information_cutoff": window["issued_at"],
                "materialized_at": activated_at,
                "entry_not_before": window["start_at"],
                "evaluation_not_before": window["evaluated_at"],
                "source_ids": list(source_ids),
                "issue_reconstruction_sha256": issue_packet["reconstruction_sha256"],
                "forecast": forecast,
                "transaction_cost_bps": float(config.get("transaction_cost_bps", 10.0)),
                "generation_process": "sealed_deterministic_program",
                "historical_repair_allowed": False,
                "promotion_eligible": False,
                "paper_policy_authority": False,
                "capital_authority": False,
            }
            issuance = {
                **issuance_body, "issuance_sha256": stable_sha256(issuance_body),
            }
            issuance_path = root / "point_in_time_replay" / "issuances" / (
                f"{issuance['issuance_sha256']}.json"
            )
            _atomic_json(issuance_path, issuance, immutable=True)
            issuance_leaf = GoldenLeaf(
                owner=owner,
                object_kind="sealed_walk_forward_issuance",
                object_id=str(cell["cell_id"]),
                epoch=str(issuance["issuance_sha256"]),
                occurred_at=activated_at,
                available_at=activated_at,
                payload={
                    **issuance,
                    "issuance_path": issuance_path.relative_to(root).as_posix(),
                },
                source_refs=(
                    f"plan:{plan_sha}",
                    f"issue:{issue_packet['reconstruction_sha256']}",
                ),
            )
            store.append_bundle(
                (issuance_leaf,),
                (GoldenEdge(issuance_leaf.leaf_sha256, plan_sha, "derived_from"),),
                make_heads=True,
            )
            issuance_leaf_shas.append(issuance_leaf.leaf_sha256)
            issuance_actions.append({
                "cell_id": cell["cell_id"], "status": "issued", "ok": True,
                "forecast_sha256": forecast["forecast_sha256"],
                "issuance_leaf_sha256": issuance_leaf.leaf_sha256,
            })
        except (KeyError, OSError, TypeError, ValueError) as error:
            issuance_actions.append({
                "cell_id": cell["cell_id"], "status": "error", "ok": False,
                "error": f"{type(error).__name__}: {error}"[:1_000],
            })
    before = sealed_walk_forward_status(
        root, config, as_of=activated_at, owner=owner, store_path=store_path,
    )
    packet_cache: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    fixed_outcome_as_of = {
        str(row["base_cell_id"]): str(row["outcome_evaluated_at"])
        for row in before["cells"]
        if row.get("outcome_evaluated_at")
    }
    actions = []
    settlement_leaf_shas = []
    for cell in before["cells"]:
        if cell["state"] != "activation_due":
            continue
        try:
            subject = subject_by_id[str(cell["entity_id"])]
            window = window_by_id[str(cell["window_id"])]
            base_id = str(cell["base_cell_id"])
            issuance_leaf_sha = require_text(
                cell.get("issuance_leaf_sha256"), "walk-forward issuance leaf",
            )
            issuance_leaf = store.get_leaf(issuance_leaf_sha)
            issuance_payload = dict(issuance_leaf["payload"])
            if (
                issuance_payload.get("schema") != SEALED_WALK_FORWARD_ISSUANCE_SCHEMA
                or issuance_payload.get("plan_leaf_sha256") != plan_sha
                or issuance_payload.get("cell_id") != cell["cell_id"]
            ):
                raise ValueError("walk-forward settlement requires its exact issuance")
            outcome_as_of = fixed_outcome_as_of.get(base_id, activated_at)
            if base_id not in packet_cache:
                source_ids = tuple(sorted({
                    subject["price_source_id"], subject["benchmark_source_id"],
                }))
                issue_packet = reconstruct_evidence_as_of(
                    root, as_of=str(window["issued_at"]), source_ids=source_ids,
                    store_path=store_path,
                )
                outcome_packet = reconstruct_evidence_as_of(
                    root, as_of=outcome_as_of, source_ids=source_ids,
                    store_path=store_path,
                )
                packet_cache[base_id] = (issue_packet, outcome_packet)
            issue_packet, outcome_packet = packet_cache[base_id]
            replay = compile_point_in_time_forecast_replay(root, {
                "schema": POINT_IN_TIME_REPLAY_PROFILE_SCHEMA,
                "replay_id": str(cell["cell_id"]),
                "program_id": str(cell["program_id"]),
                "entity_id": subject["entity_id"],
                "benchmark_id": subject["benchmark_id"],
                "issued_at": window["issued_at"],
                "start_at": window["start_at"],
                "evaluated_at": outcome_as_of,
                "horizon_days": window["horizon_days"],
                "price_metric_id": "adjusted_price",
                "source_ids": sorted({
                    subject["price_source_id"], subject["benchmark_source_id"],
                }),
                "transaction_cost_bps": float(config.get("transaction_cost_bps", 10.0)),
                "capital_authority": False,
            }, _issue_packet=issue_packet, _outcome_packet=outcome_packet)
            if replay["forecast"] != issuance_payload.get("forecast"):
                raise ValueError(
                    "issued walk-forward forecast differs from its sealed deterministic program"
                )
            replay_path = root / "point_in_time_replay" / "settlements" / (
                f"{replay['replay_sha256']}.json"
            )
            _atomic_json(replay_path, replay, immutable=True)
            reference_payload = {
                "schema": SEALED_WALK_FORWARD_SETTLEMENT_REF_SCHEMA,
                "evaluation_id": evaluation_id,
                "profile_sha256": profile_sha,
                "plan_leaf_sha256": plan_sha,
                "issuance_leaf_sha256": issuance_leaf_sha,
                "cell_id": cell["cell_id"],
                "window_id": cell["window_id"],
                "entity_id": cell["entity_id"],
                "entity_kind": cell["entity_kind"],
                "program_id": cell["program_id"],
                "issued_at": cell["issued_at"],
                "forecast_sha256": replay["forecast"]["forecast_sha256"],
                "evaluation_not_before": cell["evaluated_at"],
                "evaluated_at": outcome_as_of,
                "replay_sha256": replay["replay_sha256"],
                "replay_path": replay_path.relative_to(root).as_posix(),
                "issue_reconstruction_sha256": replay["issue_packet"]["reconstruction_sha256"],
                "outcome_reconstruction_sha256": replay["outcome_reconstruction_sha256"],
                "scores": replay["scores"],
                "actual_values": replay["actual_values"],
                "generation_process": "deterministic",
                "promotion_eligible": False,
                "paper_policy_authority": False,
                "capital_authority": False,
            }
            settlement_leaf = GoldenLeaf(
                owner=owner,
                object_kind="sealed_walk_forward_settlement",
                object_id=str(cell["cell_id"]),
                epoch=str(replay["replay_sha256"]),
                occurred_at=activated_at,
                available_at=activated_at,
                payload=reference_payload,
                source_refs=(
                    f"plan:{plan_sha}",
                    f"issuance:{issuance_leaf_sha}",
                    f"outcome:{reference_payload['outcome_reconstruction_sha256']}",
                ),
            )
            store.append_bundle(
                (settlement_leaf,),
                (
                    GoldenEdge(settlement_leaf.leaf_sha256, plan_sha, "derived_from"),
                    GoldenEdge(
                        settlement_leaf.leaf_sha256, issuance_leaf_sha, "settles",
                    ),
                ),
                make_heads=True,
            )
            settlement_leaf_shas.append(settlement_leaf.leaf_sha256)
            actions.append({
                "cell_id": cell["cell_id"], "status": "settled", "ok": True,
                "replay_sha256": replay["replay_sha256"],
                "settlement_leaf_sha256": settlement_leaf.leaf_sha256,
            })
        except (KeyError, OSError, TypeError, ValueError) as error:
            actions.append({
                "cell_id": cell["cell_id"], "status": "error", "ok": False,
                "error": f"{type(error).__name__}: {error}"[:1_000],
            })
    after = sealed_walk_forward_status(
        root, config, as_of=activated_at, owner=owner, store_path=store_path,
    )
    tournament_action: dict[str, Any] = {
        "ok": True, "status": "not_due", "capital_authority": False,
    }
    tournament_leaf_sha = None
    if after.get("tournament_refresh_due"):
        try:
            tournament = compile_sealed_walk_forward_tournament(
                root, config, as_of=activated_at, owner=owner, store_path=store_path,
            )
            tournament_path = root / "point_in_time_replay" / "tournaments" / (
                f"{tournament['tournament_sha256']}.json"
            )
            _atomic_json(tournament_path, tournament, immutable=True)
            tournament_record = record_world_model_tournament(store, tournament)
            tournament_leaf_sha = str(tournament_record["tournament"])
            _atomic_json(
                root / "point_in_time_replay" / "tournaments" / "latest.json",
                tournament,
            )
            tournament_action = {
                "ok": True,
                "status": "compiled",
                "tournament_sha256": tournament["tournament_sha256"],
                "tournament_path": tournament_path.relative_to(root).as_posix(),
                "golden_leaf_sha256": tournament_leaf_sha,
                "inference_block_count": tournament["inference_block_count"],
                "inference_sufficient": tournament["inference_sufficient"],
                "research_priority_evidence_eligible": tournament[
                    "research_priority_evidence_eligible"
                ],
                "capital_authority": False,
            }
        except (KeyError, OSError, TypeError, ValueError) as error:
            tournament_action = {
                "ok": False,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:1_000],
                "capital_authority": False,
            }
    after = sealed_walk_forward_status(
        root, config, as_of=activated_at, owner=owner, store_path=store_path,
    )
    run_identity = {
        "evaluation_id": evaluation_id,
        "profile_sha256": profile_sha,
        "plan_leaf_sha256": plan_sha,
        "activated_at": activated_at,
        "plan_created": plan_created,
        "issuance_actions": issuance_actions,
        "actions": actions,
        "trial_family_sha256": trial_family["trial_family_sha256"],
        "tournament_sha256": tournament_action.get("tournament_sha256"),
        "tournament_error": tournament_action.get("error"),
        "status_sha256": after["status_sha256"],
    }
    cycle_id = f"sealed-walk-forward-{stable_sha256(run_identity)[:20]}"
    run_body = {
        "schema": SEALED_WALK_FORWARD_CYCLE_SCHEMA,
        "cycle_id": cycle_id,
        **run_identity,
        "issued_count": sum(bool(row.get("ok")) for row in issuance_actions),
        "settled_count": sum(bool(row.get("ok")) for row in actions),
        "error_count": (
            sum(not bool(row.get("ok")) for row in issuance_actions)
            +
            sum(not bool(row.get("ok")) for row in actions)
            + int(not bool(tournament_action.get("ok")))
        ),
        "trial_family": trial_family,
        "tournament": tournament_action,
        "status": after["status"],
        "next_activation": after["next_activation"],
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}
    run_path = root / "point_in_time_replay" / "cycles" / f"{run['run_sha256']}.json"
    _atomic_json(run_path, run, immutable=True)
    cycle_leaf = GoldenLeaf(
        owner=owner,
        object_kind="sealed_walk_forward_cycle",
        object_id=evaluation_id,
        epoch=str(run["run_sha256"]),
        occurred_at=activated_at,
        available_at=activated_at,
        payload={**run, "run_path": run_path.relative_to(root).as_posix()},
        source_refs=(f"plan:{plan_sha}",),
    )
    store.append_bundle(
        (cycle_leaf,),
        (
            GoldenEdge(cycle_leaf.leaf_sha256, plan_sha, "derived_from"),
            *(GoldenEdge(cycle_leaf.leaf_sha256, sha, "contains")
              for sha in issuance_leaf_shas),
            *(GoldenEdge(cycle_leaf.leaf_sha256, sha, "contains")
              for sha in settlement_leaf_shas),
            *((GoldenEdge(
                cycle_leaf.leaf_sha256, tournament_leaf_sha, "contains",
            ),) if tournament_leaf_sha else ()),
        ),
        make_heads=True,
    )
    status = sealed_walk_forward_status(
        root, config, as_of=activated_at, owner=owner, store_path=store_path,
    )
    _atomic_json(
        root / "point_in_time_replay" / "sealed_walk_forward_status.json", status,
    )
    return {
        "ok": (
            not any(not bool(row.get("ok")) for row in issuance_actions)
            and
            not any(not bool(row.get("ok")) for row in actions)
            and bool(tournament_action.get("ok"))
        ),
        "status": (
            "completed" if issuance_actions or actions or plan_created else "not_due"
        ),
        "run": run,
        "run_path": run_path.relative_to(root).as_posix(),
        "golden_leaf_sha256": cycle_leaf.leaf_sha256,
        "trial_family": trial_family,
        "tournament": tournament_action,
        "matrix_status": status,
        "capital_authority": False,
    }


def _packet_manifest(
    *, packet_kind: str, cutoff: str, rows: tuple[MetricObservation, ...],
    sources: tuple[Mapping[str, Any], ...], archive_as_of: str,
) -> dict[str, Any]:
    body = {
        "schema": "jaggedthoughts-provider-date-evidence-packet-v1",
        "packet_kind": packet_kind,
        "information_cutoff": cutoff,
        "archive_as_of": archive_as_of,
        "observation_count": len(rows),
        "observation_ids_sha256": stable_sha256(sorted(row.observation_id for row in rows)),
        "source_snapshots": [{
            key: source[key] for key in (
                "source_id", "snapshot_leaf_sha256", "observation_set_sha256",
                "ingested_at", "leakage_classification",
            )
        } for source in sources],
        "capital_authority": False,
    }
    return {**body, "packet_sha256": stable_sha256(body)}


def compile_archived_accounting_replay(
    workspace: str | Path, *, as_of: str | None = None,
    source_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Score filing-time accounting forecasts from verified archive blobs.

    The provider filing dates bound each forecast packet.  When the archive was
    captured after a historical cutoff, the result remains a retrospective
    mechanism diagnostic rather than a system-clock historical archive claim.
    """
    root = Path(workspace).expanduser().resolve()
    if as_of is None:
        status = evidence_vault_status(root)
        if not status.get("enabled"):
            raise ValueError("evidence vault has no captured public-source run")
        archive_as_of = str(status["ingested_at"])
    else:
        archive_as_of = canonical_timestamp(as_of, "archived accounting replay as_of")
    requested = tuple(sorted({require_text(value, "source_id") for value in source_ids}))
    archive = reconstruct_evidence_as_of(
        root, as_of=archive_as_of, source_ids=requested or None,
    )
    if archive["status"] != "complete":
        raise ValueError(f"archive sources unavailable: {archive['missing_source_ids']}")
    eligible = {
        str(row["source_id"]): row for row in archive["sources"]
        if row["leakage_classification"] == "provider_filed_date_with_capture_floor"
    }
    if requested and set(requested) != set(eligible):
        rejected = sorted(set(requested) - set(eligible))
        raise ValueError(f"filing replay rejects non-provider-date sources: {rejected}")
    if not eligible:
        raise ValueError("archive contains no provider-filed-date evidence")
    rows = tuple(
        MetricObservation(**raw) for raw in archive["observations"]
        if raw["source_ref"] in eligible
    )
    entities = tuple(sorted({row.entity_id for row in rows}))
    replay = compile_historical_accounting_replay(
        root, as_of=archive_as_of, entity_ids=entities, observations=rows,
    )
    by_entity: dict[str, tuple[MetricObservation, ...]] = {
        entity: tuple(row for row in rows if row.entity_id == entity)
        for entity in entities
    }
    episodes = []
    for raw_episode in replay["episodes"]:
        episode = dict(raw_episode)
        opened_at = str(episode["opened_at"])
        outcome_at = str(episode["outcome_available_at"])
        episode_sources = tuple(
            eligible[source_id] for source_id in sorted(
                set(episode["source_refs"]) & set(eligible)
            )
        )
        source_set = {str(source["source_id"]) for source in episode_sources}
        candidates = tuple(
            row for row in by_entity[str(episode["entity_id"])]
            if row.source_ref in source_set
        )
        issue_rows = tuple(
            row for row in candidates
            if timestamp_key(row.available_at) <= timestamp_key(opened_at)
        )
        outcome_rows = tuple(
            row for row in candidates
            if timestamp_key(opened_at) < timestamp_key(row.available_at)
            <= timestamp_key(outcome_at)
        )
        membership_pass = bool(issue_rows and outcome_rows) and all(
            timestamp_key(row.available_at) <= timestamp_key(opened_at)
            for row in issue_rows
        ) and all(
            timestamp_key(opened_at) < timestamp_key(row.available_at)
            <= timestamp_key(outcome_at)
            for row in outcome_rows
        )
        if not membership_pass:
            raise ValueError(f"episode packet chronology failed: {episode['episode_id']}")
        issue_packet = _packet_manifest(
            packet_kind="forecast_input", cutoff=opened_at, rows=issue_rows,
            sources=episode_sources, archive_as_of=archive_as_of,
        )
        outcome_packet = _packet_manifest(
            packet_kind="settlement_delta", cutoff=outcome_at, rows=outcome_rows,
            sources=episode_sources, archive_as_of=archive_as_of,
        )
        predicted = float(episode["metrics"]["current_owner_earnings_margin"])
        actual = float(episode["metrics"]["next_owner_earnings_margin"])
        archive_existed_at_issue = all(
            timestamp_key(str(source["ingested_at"])) <= timestamp_key(opened_at)
            for source in episode_sources
        )
        episode.update({
            "point_in_time": archive_existed_at_issue,
            "provider_date_reconstructed": True,
            "forecast": {
                "program_id": "owner_earnings_margin_persistence_control",
                "predicted_next_owner_earnings_margin": predicted,
                "issue_packet_sha256": issue_packet["packet_sha256"],
                "generation_process": "deterministic",
            },
            "score": {
                "actual_next_owner_earnings_margin": actual,
                "absolute_error": abs(predicted - actual),
                "squared_error": (predicted - actual) ** 2,
            },
            "evidence_packets": {"issue": issue_packet, "outcome": outcome_packet},
            "temporal_integrity": {
                "provider_available_at_membership_pass": membership_pass,
                "outcome_rows_absent_from_issue": not {
                    row.observation_id for row in issue_rows
                } & {row.observation_id for row in outcome_rows},
                "archive_existed_at_issue": archive_existed_at_issue,
            },
        })
        episodes.append(episode)
    leakage_pass = bool(episodes) and all(
        row["temporal_integrity"]["provider_available_at_membership_pass"]
        and row["temporal_integrity"]["outcome_rows_absent_from_issue"]
        for row in episodes
    )
    system_clock_at_issue = bool(episodes) and all(
        row["temporal_integrity"]["archive_existed_at_issue"] for row in episodes
    )
    body = {
        "schema": ARCHIVED_ACCOUNTING_REPLAY_SCHEMA,
        "status": "settled_mechanism_diagnostic" if episodes else "insufficient_history",
        "archive_as_of": archive_as_of,
        "archive_reconstruction_sha256": archive["reconstruction_sha256"],
        "source_count": len(eligible),
        "entity_count": len({row["entity_id"] for row in episodes}),
        "episode_count": len(episodes),
        "evidence_packet_count": 2 * len(episodes),
        "program_id": "owner_earnings_margin_persistence_control",
        "mean_absolute_error": (
            sum(row["score"]["absolute_error"] for row in episodes) / len(episodes)
            if episodes else None
        ),
        "mechanism_comparison": {
            "durability_model": replay["durability_model"],
            "persistence_control": replay["persistence_control"],
            "paired_block_comparison": replay["paired_block_comparison"],
            "incremental_out_of_time_comparison": replay["incremental_out_of_time_comparison"],
        },
        "temporal_integrity": {
            "future_provider_row_leakage_pass": leakage_pass,
            "all_archives_existed_at_issue": system_clock_at_issue,
            "source_availability_boundary": "SEC provider filing date",
            "archive_capture_boundary": "system clock capture floor",
        },
        "evaluation_authority": (
            "point_in_time_backtest_evidence" if system_clock_at_issue
            else "retrospective_provider_date_mechanism_diagnostic"
        ),
        "alpha_evidence_eligible": system_clock_at_issue,
        "promotion_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
        "episodes": episodes,
        "boundaries": [
            "Forecast inputs exclude observations filed after the episode issue cutoff.",
            "Current archive capture postdates historical episodes; source revision and current-universe selection remain retrospective boundaries.",
            "The formula family was selected after the sample and the outcome is accounting, not a security return.",
        ],
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("profile")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = compile_point_in_time_forecast_replay(args.workspace, args.profile)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARCHIVED_ACCOUNTING_REPLAY_SCHEMA",
    "POINT_IN_TIME_REPLAY_PROFILE_SCHEMA", "POINT_IN_TIME_REPLAY_SCHEMA",
    "SEALED_WALK_FORWARD_PROFILE_SCHEMA", "SEALED_WALK_FORWARD_READINESS_SCHEMA",
    "SEALED_WALK_FORWARD_PLAN_SCHEMA", "SEALED_WALK_FORWARD_ISSUANCE_SCHEMA",
    "SEALED_WALK_FORWARD_SETTLEMENT_REF_SCHEMA",
    "SEALED_WALK_FORWARD_CYCLE_SCHEMA", "SEALED_WALK_FORWARD_STATUS_SCHEMA",
    "SEALED_WALK_FORWARD_TOURNAMENT_SCHEMA",
    "compile_archived_accounting_replay",
    "compile_point_in_time_forecast_replay",
    "compile_sealed_walk_forward_readiness",
    "compile_sealed_walk_forward_tournament",
    "run_sealed_walk_forward_cycle",
    "sealed_walk_forward_status",
]
