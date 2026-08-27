"""Compile point-in-time candidate payoff forecasts over authored world states."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .contracts import (
    canonical_timestamp,
    require_finite,
    require_refs,
    require_text,
    timestamp_key,
)
from .instrument_portfolio_admission import INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA
from .strategy_valuation_bridge import extreme_interval_mixture


FORECAST_SCHEMA = "jaggedthoughts-candidate-payoff-forecast-v1"
RESULT_SCHEMA = "jaggedthoughts-candidate-payoff-forecast-result-v1"
REQUEST_SCHEMA = "jaggedthoughts-candidate-payoff-forecast-request-v1"
JOB_SCHEMA = "jaggedthoughts-candidate-payoff-forecast-job-v1"
JOB_KIND = "jaggedthoughts_candidate_payoff_forecast"


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _sealed(raw: Mapping[str, Any], *, schema: str, digest_field: str, label: str) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != schema:
        raise ValueError(f"{label} schema must be {schema}")
    digest = require_text(row.pop(digest_field, None), f"{label} {digest_field}")
    if stable_sha256(row) != digest:
        raise ValueError(f"{label} content hash mismatch")
    return {**row, digest_field: digest}


def _interval(
    raw: Mapping[str, Any], label: str, *, unit: str, low_floor: float, high_ceiling: float,
) -> tuple[float, float]:
    if raw.get("unit") != unit:
        raise ValueError(f"{label} unit must be {unit}")
    low = require_finite(raw.get("low"), f"{label} low")
    high = require_finite(raw.get("high"), f"{label} high")
    if not low_floor <= low <= high <= high_ceiling:
        raise ValueError(
            f"{label} must satisfy {low_floor} <= low <= high <= {high_ceiling}"
        )
    return low, high


def _bounded_simplex_center(states: list[Mapping[str, Any]]) -> dict[str, float]:
    """Project interval midpoints onto their bounded probability simplex."""
    bounds = [
        (
            str(row["state_id"]),
            float(row["probability"]["low"]),
            float(row["probability"]["high"]),
        )
        for row in states
    ]
    targets = [(low + high) / 2 for _, low, high in bounds]
    left, right = -1.0, 1.0
    for _ in range(80):
        shift = (left + right) / 2
        total = sum(
            min(high, max(low, target + shift))
            for target, (_, low, high) in zip(targets, bounds, strict=True)
        )
        if total < 1:
            left = shift
        else:
            right = shift
    shift = (left + right) / 2
    center = {
        state_id: min(high, max(low, target + shift))
        for target, (state_id, low, high) in zip(targets, bounds, strict=True)
    }
    residual = 1 - sum(center.values())
    if abs(residual) > 1e-12:
        for state_id, low, high in bounds:
            room = high - center[state_id] if residual > 0 else center[state_id] - low
            delta = math.copysign(min(abs(residual), room), residual)
            center[state_id] += delta
            residual -= delta
            if abs(residual) <= 1e-12:
                break
    return center


def _mixture_width(rows: list[dict[str, Any]]) -> float:
    low, _ = extreme_interval_mixture(rows, payoff_field="active_low", maximize=False)
    high, _ = extreme_interval_mixture(rows, payoff_field="active_high", maximize=True)
    return high - low


def _uncertainty_diagnostics(
    states: list[Mapping[str, Any]], *, comparator_low: float, comparator_high: float,
    total_width: float,
) -> dict[str, Any]:
    """Rank which authored interval family most widens the decision range."""
    center = _bounded_simplex_center(states)
    comparator_midpoint = (comparator_low + comparator_high) / 2

    def rows(*, fix_probabilities: bool = False, fix_candidate: bool = False,
             fix_comparator: bool = False) -> list[dict[str, Any]]:
        result = []
        for state in states:
            probability = dict(state["probability"])
            candidate = dict(state["candidate_horizon_total_return"])
            probability_low = probability_high = center[str(state["state_id"])] \
                if fix_probabilities else None
            if not fix_probabilities:
                probability_low = float(probability["low"])
                probability_high = float(probability["high"])
            candidate_low = float(candidate["low"])
            candidate_high = float(candidate["high"])
            if fix_candidate:
                candidate_low = candidate_high = (candidate_low + candidate_high) / 2
            benchmark_low = benchmark_high = comparator_midpoint
            if not fix_comparator:
                benchmark_low, benchmark_high = comparator_low, comparator_high
            result.append({
                "region_sha256": str(state["state_id"]),
                "probability_low": probability_low,
                "probability_high": probability_high,
                "active_low": candidate_low - benchmark_high,
                "active_high": candidate_high - benchmark_low,
            })
        return result

    targets = {
        "probability_intervals": "state_occurrence_discriminators",
        "candidate_return_intervals": "valuation_and_operating_payoff_bounds",
        "comparator_return_interval": "benchmark_horizon_return_bounds",
    }
    diagnostics = []
    for component, kwargs in (
        ("probability_intervals", {"fix_probabilities": True}),
        ("candidate_return_intervals", {"fix_candidate": True}),
        ("comparator_return_interval", {"fix_comparator": True}),
    ):
        counterfactual_width = _mixture_width(rows(**kwargs))
        diagnostics.append({
            "component": component,
            "counterfactual_width_if_resolved": counterfactual_width,
            "marginal_width_reduction_if_resolved": max(0.0, total_width - counterfactual_width),
            "next_evidence_target": targets[component],
        })
    diagnostics.sort(key=lambda row: (
        -row["marginal_width_reduction_if_resolved"], row["component"],
    ))
    return {
        "method": "one_component_midpoint_resolution_with_other_intervals_preserved",
        "total_expected_active_return_width": total_width,
        "reference_probability_distribution": center,
        "ranked_components": diagnostics,
        "dominant_component": diagnostics[0]["component"],
        "next_evidence_target": diagnostics[0]["next_evidence_target"],
        "additivity_claim": False,
        "decision_authority": False,
    }


def compile_candidate_payoff_forecast(
    *,
    candidate: Mapping[str, Any],
    admission: Mapping[str, Any],
    valuation: Mapping[str, Any],
    forecast: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one authored world partition and bound its active-return mixture."""
    candidate_row = _sealed(
        candidate,
        schema="jaggedthoughts-discovery-candidate-v1",
        digest_field="candidate_sha256",
        label="candidate",
    )
    admission_row = _sealed(
        admission,
        schema=INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA,
        digest_field="admission_sha256",
        label="instrument admission",
    )
    valuation_row = _sealed(
        valuation,
        schema="jaggedthoughts-valuation-envelope-v1",
        digest_field="envelope_sha256",
        label="valuation envelope",
    )
    payload = dict(forecast)
    if payload.get("schema") != FORECAST_SCHEMA:
        raise ValueError(f"candidate payoff forecast schema must be {FORECAST_SCHEMA}")

    entity_id = require_text(payload.get("entity_id"), "forecast entity_id").upper()
    candidate_leaf = require_text(payload.get("candidate_leaf"), "forecast candidate_leaf")
    research = dict(admission_row.get("research_identity") or {})
    subject = dict(admission_row.get("subject") or {})
    if (
        candidate_row.get("entity_kind") != "public_equity"
        or str(candidate_row.get("entity_id") or "").upper() != entity_id
        or str(valuation_row.get("entity_id") or "").upper() != entity_id
        or str(subject.get("subject_id") or "").upper() != entity_id
        or payload.get("candidate_sha256") != candidate_row["candidate_sha256"]
        or payload.get("instrument_admission_sha256") != admission_row["admission_sha256"]
        or payload.get("valuation_envelope_sha256") != valuation_row["envelope_sha256"]
        or payload.get("dossier_sha256") != research.get("dossier_sha256")
        or candidate_leaf != research.get("candidate_leaf")
        or candidate_row["candidate_sha256"] != research.get("candidate_sha256")
        or valuation_row["envelope_sha256"] != research.get("valuation_envelope_sha256")
        or (candidate_row.get("valuation") or {}).get("envelope_sha256")
        != valuation_row["envelope_sha256"]
        or (admission_row.get("eligibility") or {}).get("status")
        != "admitted_to_research_paper_portfolio"
    ):
        raise ValueError("candidate payoff forecast crossed admitted underwriting identity")

    cutoff = canonical_timestamp(payload.get("information_cutoff"), "forecast information_cutoff")
    horizon_at = canonical_timestamp(payload.get("horizon_at"), "forecast horizon_at")
    horizon_number = require_finite(payload.get("horizon_days"), "forecast horizon_days")
    if not horizon_number.is_integer():
        raise ValueError("forecast horizon_days must be an integer")
    horizon_days = int(horizon_number)
    if not 30 <= horizon_days <= 3650 or timestamp_key(horizon_at) <= timestamp_key(cutoff):
        raise ValueError("candidate payoff horizon must be 30..3650 days after the cutoff")
    actual_days = (timestamp_key(horizon_at) - timestamp_key(cutoff)).total_seconds() / 86_400
    if abs(actual_days - horizon_days) > 1:
        raise ValueError("horizon_at and horizon_days disagree")
    if timestamp_key(canonical_timestamp(
        admission_row.get("compiled_at"), "instrument admission compiled_at",
    )) > timestamp_key(cutoff):
        raise ValueError("instrument admission was unavailable at the forecast cutoff")

    spot = dict(payload.get("spot_price_observation") or {})
    spot_observed = canonical_timestamp(spot.get("observed_at"), "spot observed_at")
    spot_available = canonical_timestamp(spot.get("available_at"), "spot available_at")
    market_price = next((
        row for row in valuation_row.get("assumptions") or ()
        if row.get("assumption_type") == "MarketPrice"
    ), None)
    if (
        not market_price
        or timestamp_key(spot_observed) > timestamp_key(spot_available)
        or timestamp_key(spot_available) > timestamp_key(cutoff)
        or spot.get("unit") != "currency/share"
        or not math.isclose(
            require_finite(spot.get("value"), "spot value"),
            float(market_price["value"]), rel_tol=1e-12, abs_tol=1e-12,
        )
        or require_text(spot.get("source_ref"), "spot source_ref")
        not in set(map(str, market_price.get("source_refs") or ()))
    ):
        raise ValueError("spot observation does not match the point-in-time valuation")

    comparator = dict(payload.get("comparator") or {})
    if comparator.get("kind") != "benchmark_total_return":
        raise ValueError("forecast comparator must be benchmark_total_return")
    comparator_entity_id = require_text(
        comparator.get("entity_id"), "forecast comparator entity_id",
    ).upper()
    comparator_low, comparator_high = _interval(
        dict(comparator.get("horizon_return") or {}),
        "comparator horizon return", unit="decimal", low_floor=-1.0, high_ceiling=10.0,
    )
    comparator_refs = require_refs(comparator.get("source_refs") or (), "comparator source ref")

    scope = dict(payload.get("scope") or {})
    residual_id = require_text(scope.get("residual_state_id"), "residual state_id")
    if (
        scope.get("kind") != "ordered_thesis_rival_residual_partition"
        or scope.get("exhaustive_within_authored_scope") is not True
    ):
        raise ValueError("forecast must declare an exhaustive authored thesis/rival/residual scope")

    valuation_scenario_ids = {
        str(row.get("scenario_id") or "") for row in valuation_row.get("scenarios") or ()
        if row.get("scenario_id")
    }
    states = []
    seen: set[str] = set()
    for raw in payload.get("states") or ():
        state = dict(raw)
        state_id = require_text(state.get("state_id"), "forecast state_id")
        if state_id in seen:
            raise ValueError("forecast state ids must be unique")
        seen.add(state_id)
        predicate = dict(state.get("outcome_predicate") or {})
        metric_ids = sorted({require_text(value, "outcome metric_id") for value in predicate.get("metric_ids") or ()})
        settlement_rule = require_text(predicate.get("settlement_rule"), "outcome settlement_rule")
        probability = dict(state.get("probability") or {})
        probability_low, probability_high = _interval(
            probability, f"{state_id} probability", unit="probability_decimal",
            low_floor=0.0, high_ceiling=1.0,
        )
        if probability.get("identity") != "authored_forecast_interval":
            raise ValueError("state probability identity must be authored_forecast_interval")
        probability_refs = require_refs(
            probability.get("source_refs") or (), f"{state_id} probability source ref",
        )
        probability_body = {
            "low": probability_low, "high": probability_high,
            "unit": "probability_decimal", "identity": "authored_forecast_interval",
            "source_refs": list(probability_refs),
        }
        forecast_sha256 = stable_sha256(probability_body)
        declared_forecast_sha = probability.get("forecast_sha256")
        if declared_forecast_sha is not None and _digest(
            declared_forecast_sha, f"{state_id} probability forecast_sha256",
        ) != forecast_sha256:
            raise ValueError(f"{state_id} probability forecast content hash mismatch")
        payoff = dict(state.get("candidate_horizon_total_return") or {})
        payoff_low, payoff_high = _interval(
            payoff, f"{state_id} candidate return", unit="decimal",
            low_floor=-1.0, high_ceiling=10.0,
        )
        payoff_refs = require_refs(payoff.get("source_refs") or (), f"{state_id} payoff source ref")
        scenario_ids = sorted({
            require_text(value, f"{state_id} valuation scenario id")
            for value in payoff.get("valuation_scenario_ids") or ()
        })
        if not metric_ids or not scenario_ids:
            raise ValueError("every forecast state needs outcome metrics and valuation scenarios")
        unknown_scenarios = set(scenario_ids) - valuation_scenario_ids
        if unknown_scenarios:
            raise ValueError(f"forecast cites unknown valuation scenarios: {sorted(unknown_scenarios)}")
        active_low = payoff_low - comparator_high
        active_high = payoff_high - comparator_low
        states.append({
            "state_id": state_id,
            "outcome_predicate": {
                "metric_ids": metric_ids, "settlement_rule": settlement_rule,
                "is_residual_catch_all": bool(predicate.get("is_residual_catch_all")),
            },
            "probability": {
                **probability_body, "forecast_sha256": forecast_sha256,
            },
            "candidate_horizon_total_return": {
                "low": payoff_low, "high": payoff_high, "unit": "decimal",
                "valuation_scenario_ids": scenario_ids, "source_refs": list(payoff_refs),
            },
            "active_return_interval": {"low": active_low, "high": active_high},
        })
    if len(states) < 2 or residual_id not in seen:
        raise ValueError("forecast requires at least two states and its residual state")
    residual = next(row for row in states if row["state_id"] == residual_id)
    if residual["outcome_predicate"]["is_residual_catch_all"] is not True:
        raise ValueError("declared residual state must be the catch-all outcome")
    if sum(row["probability"]["low"] for row in states) > 1 + 1e-12 or sum(
        row["probability"]["high"] for row in states
    ) < 1 - 1e-12:
        raise ValueError("state probability intervals do not contain a distribution")

    mixture_rows = [{
        "region_sha256": row["state_id"],
        "probability_low": row["probability"]["low"],
        "probability_high": row["probability"]["high"],
        "active_low": row["active_return_interval"]["low"],
        "active_high": row["active_return_interval"]["high"],
        "certain_underperformance": float(row["active_return_interval"]["high"] < 0),
        "possible_underperformance": float(row["active_return_interval"]["low"] < 0),
    } for row in states]
    expected_low, expected_low_witness = extreme_interval_mixture(
        mixture_rows, payoff_field="active_low", maximize=False,
    )
    expected_high, expected_high_witness = extreme_interval_mixture(
        mixture_rows, payoff_field="active_high", maximize=True,
    )
    underperformance_low, underperformance_low_witness = extreme_interval_mixture(
        mixture_rows, payoff_field="certain_underperformance", maximize=False,
    )
    underperformance_high, underperformance_high_witness = extreme_interval_mixture(
        mixture_rows, payoff_field="possible_underperformance", maximize=True,
    )
    contract_body = {
        **{key: value for key, value in payload.items() if key not in {"contract_sha256"}},
        "contract_id": require_text(payload.get("contract_id"), "forecast contract_id"),
        "entity_id": entity_id, "candidate_leaf": candidate_leaf,
        "information_cutoff": cutoff, "horizon_at": horizon_at, "horizon_days": horizon_days,
        "spot_price_observation": {
            **spot, "observed_at": spot_observed, "available_at": spot_available,
        },
        "comparator": {
            "kind": "benchmark_total_return", "entity_id": comparator_entity_id,
            "horizon_return": {"low": comparator_low, "high": comparator_high, "unit": "decimal"},
            "source_refs": list(comparator_refs),
        },
        "scope": {
            "kind": "ordered_thesis_rival_residual_partition",
            "residual_state_id": residual_id, "exhaustive_within_authored_scope": True,
        },
        "states": states,
        "state_price_identity": "not_requested",
        "market_state_prices_identified": False,
        "risk_neutral_probability_claim": False,
        "capital_authority": False,
    }
    contract = {**contract_body, "contract_sha256": stable_sha256(contract_body)}
    total_width = expected_high - expected_low
    result_body = {
        "schema": RESULT_SCHEMA, "contract_id": contract["contract_id"],
        "contract_sha256": contract["contract_sha256"], "entity_id": entity_id,
        "candidate_leaf": candidate_leaf, "candidate_sha256": candidate_row["candidate_sha256"],
        "instrument_admission_sha256": admission_row["admission_sha256"],
        "valuation_envelope_sha256": valuation_row["envelope_sha256"],
        "dossier_sha256": research["dossier_sha256"],
        "information_cutoff": cutoff, "horizon_at": horizon_at, "horizon_days": horizon_days,
        "comparator_entity_id": comparator_entity_id,
        "state_active_return_intervals": [{
            "state_id": row["state_id"], **row["active_return_interval"],
        } for row in states],
        "expected_active_return_interval": {"low": expected_low, "high": expected_high},
        "underperformance_probability_interval": {
            "low": underperformance_low, "high": underperformance_high,
        },
        "uncertainty_diagnostics": _uncertainty_diagnostics(
            states, comparator_low=comparator_low, comparator_high=comparator_high,
            total_width=total_width,
        ),
        "worst_case_active_return": min(row["active_return_interval"]["low"] for row in states),
        "probability_witnesses": {
            "expected_active_return_low": expected_low_witness,
            "expected_active_return_high": expected_high_witness,
            "underperformance_probability_low": underperformance_low_witness,
            "underperformance_probability_high": underperformance_high_witness,
        },
        "expected_return_identity": "forecast_interval_conditional_on_authored_worlds",
        "physical_probability_identity": "authored_forecast_intervals_not_observed_frequencies",
        "market_state_prices_identified": False, "rank_authority": False,
        "portfolio_authority": False, "capital_authority": False,
    }
    return {
        "forecast_contract": contract,
        "forecast_result": {**result_body, "forecast_result_sha256": stable_sha256(result_body)},
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def due_candidate_payoff_forecast_requests(
    workspace: str | Path, *, requested_at: str | None = None,
) -> list[dict[str, Any]]:
    """Return current admitted equities lacking a current payoff forecast."""
    root = Path(workspace).expanduser().resolve()
    created_at = canonical_timestamp(
        requested_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate payoff request time",
    )
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    admissions = json.loads(
        (root / "portfolio" / "instrument_admissions" / "latest.json").read_text(
            encoding="utf-8"
        )
    )
    admitted = {
        str((row.get("subject") or {}).get("subject_id") or "").upper(): row
        for row in admissions.get("admissions") or ()
        if (row.get("eligibility") or {}).get("status")
        == "admitted_to_research_paper_portfolio"
    }
    completed = {
        (
            str(row.get("candidate_sha256") or ""),
            str(row.get("valuation_envelope_sha256") or ""),
            str(row.get("dossier_sha256") or ""),
        )
        for path in sorted((root / "underwriting" / "payoff_forecasts" / "results").glob("*.json"))
        if (row := json.loads(path.read_text(encoding="utf-8"))).get("schema")
        == RESULT_SCHEMA
    }
    requests = []
    for candidate in discovery.get("candidates") or ():
        entity = str(candidate.get("entity_id") or "").upper()
        admission = admitted.get(entity)
        research = dict((admission or {}).get("research_identity") or {})
        valuation_sha = str((candidate.get("valuation") or {}).get("envelope_sha256") or "")
        identity = (
            str(candidate.get("candidate_sha256") or ""),
            valuation_sha,
            str(research.get("dossier_sha256") or ""),
        )
        if (
            candidate.get("entity_kind") != "public_equity"
            or candidate.get("screen_status") != "qualified"
            or not admission
            or identity in completed
            or identity[0] != research.get("candidate_sha256")
            or identity[1] != research.get("valuation_envelope_sha256")
            or not research.get("dossier_sha256")
        ):
            continue
        body = {
            "schema": REQUEST_SCHEMA,
            "request_id": f"candidate-payoff:{entity}:{identity[0][:16]}",
            "entity_id": entity,
            "entity_kind": "public_equity",
            "candidate_id": str(candidate.get("candidate_id") or f"equity:{entity}"),
            "candidate_leaf": str(research.get("candidate_leaf") or ""),
            "candidate_sha256": identity[0],
            "instrument_admission_sha256": str(admission.get("admission_sha256") or ""),
            "valuation_envelope_sha256": identity[1],
            "dossier_sha256": str(research["dossier_sha256"]),
            "research_rank": int(candidate.get("research_rank") or candidate.get("rank") or 10**9),
            "created_at": created_at,
            "expected_exit": "compiled_source_bound_payoff_forecast_or_typed_failure",
            "rank_authority": False,
            "portfolio_authority": False,
            "capital_authority": False,
        }
        requests.append({**body, "request_sha256": stable_sha256(body)})
    return sorted(requests, key=lambda row: (row["research_rank"], row["entity_id"]))


def enqueue_next_candidate_payoff_forecast(
    workspace: str | Path, *, connection: Any, max_attempts: int,
) -> dict[str, Any]:
    """Keep at most one subscription payoff-authoring request in flight."""
    root = Path(workspace).expanduser().resolve()
    active = connection.execute(
        "SELECT work_id FROM work_items WHERE kind=? AND status IN ('queued', 'claimed') "
        "AND attempts < max_attempts ORDER BY created_at LIMIT 1",
        (JOB_KIND,),
    ).fetchone()
    if active:
        return {"status": "already_pending", "work_id": str(active["work_id"])}
    due = due_candidate_payoff_forecast_requests(root)
    if not due:
        return {"status": "complete", "work_id": None}
    request = due[0]
    request_path = root / "research_jobs" / "candidate_payoff_forecasts" / "requests" / (
        f"{request['request_sha256']}.json"
    )
    _write_json(request_path, request)
    work_id = f"investment-candidate-payoff:{request['request_sha256'][:24]}"
    body = {
        "schema": JOB_SCHEMA,
        "work_id": work_id,
        "request_sha256": request["request_sha256"],
        "request_path": request_path.relative_to(root).as_posix(),
        "entity_id": request["entity_id"],
        "entity_kind": request["entity_kind"],
        "research_rank": request["research_rank"],
        "stage": "queued",
        "required_capability": "subscription_payoff_forecast",
        "expected_exit": request["expected_exit"],
        "capital_authority": False,
    }
    job = {**body, "job_sha256": stable_sha256(body)}
    work_queue.enqueue(
        connection, kind=JOB_KIND,
        priority=max(1, 997_000 - int(request["research_rank"])),
        max_attempts=max_attempts, payload=job,
    )
    return {
        "status": "enqueued", "work_id": work_id,
        "entity_id": request["entity_id"], "request_sha256": request["request_sha256"],
    }


def _workspace_inputs(root: Path, payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    candidate = next((
        row for row in discovery.get("candidates") or ()
        if row.get("candidate_sha256") == payload.get("candidate_sha256")
        and str(row.get("entity_id") or "").upper()
        == str(payload.get("entity_id") or "").upper()
    ), None)
    if candidate is None:
        raise ValueError("forecast candidate is not in the current discovery run")
    valuation_path = root / require_text(
        (candidate.get("valuation") or {}).get("artifact_path"), "valuation artifact_path",
    )
    valuation = json.loads(valuation_path.read_text(encoding="utf-8"))
    admissions = json.loads(
        (root / "portfolio" / "instrument_admissions" / "latest.json").read_text(encoding="utf-8")
    )
    admission = next((
        row for row in admissions.get("admissions") or ()
        if row.get("admission_sha256") == payload.get("instrument_admission_sha256")
    ), None)
    if admission is None:
        raise ValueError("forecast admission is not current")
    return dict(candidate), dict(admission), dict(valuation)


def compile_workspace_candidate_payoff_forecast(
    workspace: str | Path, forecast_path: str | Path,
) -> dict[str, Any]:
    """Compile, publish, and project one current admitted-candidate forecast."""
    root = Path(workspace).expanduser().resolve()
    source = Path(forecast_path).expanduser()
    if not source.is_absolute():
        source = (root / source).resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    candidate, admission, valuation = _workspace_inputs(root, payload)
    dossier_sha = str((admission.get("research_identity") or {}).get("dossier_sha256") or "")
    dossier = next((
        row for path in sorted((root / "research" / "dossiers").glob("*.json"))
        if (row := json.loads(path.read_text(encoding="utf-8"))).get("dossier_sha256")
        == dossier_sha
    ), None)
    if dossier is None:
        raise ValueError("forecast admission dossier artifact is absent")
    allowed_refs = {
        str(row.get("id")) for row in dossier.get("sources") or () if row.get("id")
    } | {
        str(ref) for row in (
            *(valuation.get("assumptions") or ()), *(valuation.get("scenarios") or ()),
        ) for ref in row.get("source_refs") or ()
    }
    used_refs = {
        str(ref) for ref in (payload.get("comparator") or {}).get("source_refs") or ()
    } | {
        str(ref) for state in payload.get("states") or ()
        for block in (state.get("probability") or {}, state.get("candidate_horizon_total_return") or {})
        for ref in block.get("source_refs") or ()
    } | {str((payload.get("spot_price_observation") or {}).get("source_ref") or "")}
    unknown_refs = sorted(used_refs - allowed_refs)
    if unknown_refs:
        raise ValueError(f"forecast cites evidence outside the admitted dossier and valuation: {unknown_refs}")
    compiled = compile_candidate_payoff_forecast(
        candidate=candidate, admission=admission, valuation=valuation, forecast=payload,
    )
    contract = compiled["forecast_contract"]
    result = compiled["forecast_result"]
    contract_path = root / "underwriting" / "payoff_forecasts" / "contracts" / (
        f"{str(payload['entity_id']).lower()}-{contract['contract_sha256'][:16]}.json"
    )
    result_path = root / "underwriting" / "payoff_forecasts" / "results" / (
        f"{str(payload['entity_id']).lower()}-{result['forecast_result_sha256'][:16]}.json"
    )
    _write_json(contract_path, contract)
    _write_json(result_path, result)
    from .closed_book import open_closed_book_forecast
    from .underwriting_adapter import compile_workspace_underwriting_index

    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8")) or {}
    closed_book = open_closed_book_forecast(
        root,
        owner=str(config.get("owner") or "operator-paper-book"),
        store_path=(root / str(config.get("golden_store") or "state/golden_store.sqlite3")).resolve(),
        candidate_leaf=contract["candidate_leaf"],
        benchmark_id=result["comparator_entity_id"],
        horizon_days=result["horizon_days"],
        payoff_forecast_result=result,
    )
    underwriting = compile_workspace_underwriting_index(root)
    _write_json(root / "underwriting" / "latest.json", underwriting)
    return {
        "forecast_contract": contract, "forecast_result": result,
        "contract_path": contract_path.relative_to(root).as_posix(),
        "result_path": result_path.relative_to(root).as_posix(),
        "closed_book_run_id": closed_book["run_id"],
        "closed_book_run_path": closed_book["run_path"],
        "underwriting_index_sha256": underwriting["underwriting_index_sha256"],
    }


def run_workspace_candidate_payoff_forecast_agent(
    workspace: str | Path, entity_id: str, *, timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """Ask the signed-in Codex subscription for one bounded forecast, then compile it."""
    from ztare.common.subscription_agent_runtime import (
        CODEX_SANDBOX_SEALED_COMPLETION,
        run_subscription_agent_with_recovery,
    )

    root = Path(workspace).expanduser().resolve()
    entity = require_text(entity_id, "entity_id").upper()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    candidate = next((
        dict(row) for row in discovery.get("candidates") or ()
        if str(row.get("entity_id") or "").upper() == entity
    ), None)
    admissions = json.loads(
        (root / "portfolio" / "instrument_admissions" / "latest.json").read_text(encoding="utf-8")
    )
    admission = next((
        dict(row) for row in admissions.get("admissions") or ()
        if str((row.get("subject") or {}).get("subject_id") or "").upper() == entity
        and (row.get("eligibility") or {}).get("status")
        == "admitted_to_research_paper_portfolio"
    ), None)
    if candidate is None or admission is None:
        raise ValueError("forecast authoring requires one current admitted discovery candidate")
    research = dict(admission.get("research_identity") or {})
    if candidate.get("candidate_sha256") != research.get("candidate_sha256"):
        raise ValueError("current candidate and admission lineage disagree")
    valuation_relative = require_text(
        (candidate.get("valuation") or {}).get("artifact_path"), "valuation artifact_path",
    )
    valuation = json.loads((root / valuation_relative).read_text(encoding="utf-8"))
    dossier_path = next((
        path for path in sorted((root / "research" / "dossiers").glob(f"{entity}-*.json"))
        if json.loads(path.read_text(encoding="utf-8")).get("dossier_sha256")
        == research.get("dossier_sha256")
    ), None)
    if dossier_path is None:
        raise ValueError("admission dossier artifact is absent")
    market_price = next(
        row for row in valuation.get("assumptions") or ()
        if row.get("assumption_type") == "MarketPrice"
    )
    share_basis = dict((candidate.get("valuation") or {}).get("share_basis") or {})
    cutoff = canonical_timestamp(admission.get("compiled_at"), "admission compiled_at")
    horizon_at = (timestamp_key(cutoff) + timedelta(days=365)).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    spot = {
        "observation_id": require_text(
            share_basis.get("price_observation_id"), "price observation_id",
        ),
        "value": float(market_price["value"]), "unit": "currency/share",
        "observed_at": canonical_timestamp(
            share_basis.get("price_observed_at"), "price observed_at",
        ),
        "available_at": canonical_timestamp(candidate.get("as_of"), "candidate as_of"),
        "source_ref": require_text(market_price["source_refs"][0], "price source ref"),
    }
    repo = Path(__file__).resolve().parents[3]
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    underwriting = json.loads((root / "underwriting" / "latest.json").read_text(encoding="utf-8"))
    evidence_packet = {
        "dossier": {
            key: dossier.get(key) for key in (
                "thesis", "rival_view", "decisive_observation", "falsifiers",
                "durable_earnings_bridge", "valuation_assumptions", "sources",
            )
        },
        "valuation": {
            "summary": valuation.get("summary"),
            "assumptions": [{
                key: row.get(key) for key in (
                    "assumption_id", "assumption_type", "value", "source_refs",
                )
            } for row in valuation.get("assumptions") or ()],
            "scenarios": valuation.get("scenarios"),
        },
        "market_context": underwriting.get("market_context"),
    }
    run_root = root / "underwriting" / "payoff_forecasts" / "agent_runs" / (
        f"{entity.lower()}-{str(candidate['candidate_sha256'])[:16]}"
    )
    run_root.mkdir(parents=True, exist_ok=True)
    output_path = run_root / "last-message.json"
    prompt = f"""You are the forecast-authoring leaf for JaggedThoughts Capital.
The immutable evidence packet is embedded below because this sealed role has no tools:
{json.dumps(evidence_packet, sort_keys=True)}

Return exactly one JSON object matching the supplied schema. Use only information
available by {cutoff}; do not browse, edit files, recommend a trade, or infer
probabilities from state prices. This is a research forecast for later scoring.

Freeze these fields exactly:
- schema: {FORECAST_SCHEMA}
- contract_id: candidate-payoff:{entity}:{str(candidate['candidate_sha256'])[:16]}
- entity_id: {entity}
- candidate_leaf: {research['candidate_leaf']}
- candidate_sha256: {candidate['candidate_sha256']}
- instrument_admission_sha256: {admission['admission_sha256']}
- valuation_envelope_sha256: {research['valuation_envelope_sha256']}
- dossier_sha256: {research['dossier_sha256']}
- strategy_valuation_bridge_sha256: null
- information_cutoff: {cutoff}
- horizon_at: {horizon_at}
- horizon_days: 365
- spot_price_observation: {json.dumps(spot, sort_keys=True)}
- comparator kind/entity: benchmark_total_return / SPY
- scope kind: ordered_thesis_rival_residual_partition

Author 3-5 mutually exclusive worlds: at least thesis, rival, and an explicit
residual catch-all. Every outcome predicate must be decidable at the horizon.
Probability intervals are your conservative forecast judgments, not dossier
confidence values, frequencies, or risk-neutral probabilities; their box must
intersect the simplex. Candidate and SPY total-return intervals must be broad
enough to include model and mark-to-market uncertainty. Use only exact source ids
from the dossier or valuation artifact in source_refs and exact valuation scenario
ids from the valuation artifact. Set each probability forecast_sha256 to null; the
kernel computes and replaces it from the normalized probability interval.
"""
    schema_path = repo / "schemas" / "investment" / "candidate_payoff_forecast.schema.json"
    dispatch_path = run_root / "dispatch.json"
    run = run_subscription_agent_with_recovery(
        runtime="codex", prompt=prompt,
        agent_id=f"jaggedthoughts-candidate-payoff::{entity}::{candidate['candidate_sha256'][:16]}",
        repo=repo, session_state=None, timeout_seconds=timeout_seconds,
        default_codex_model="account-default", codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
        output_schema=schema_path, output_last_message_path=output_path,
        dispatch_receipt_path=dispatch_path,
        stdout_path=str(run_root / "stdout.log"), stderr_path=str(run_root / "stderr.log"),
    )
    if run.result.returncode != 0 or not output_path.is_file():
        raise RuntimeError(f"Codex subscription payoff leaf failed: {run.result.returncode}")
    compiled = compile_workspace_candidate_payoff_forecast(root, output_path)
    return {
        **compiled, "transport": "codex_subscription_cli",
        "agent_id": f"jaggedthoughts-candidate-payoff::{entity}",
        "dispatch_receipt_path": dispatch_path.relative_to(root).as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--forecast")
    actions.add_argument("--author")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args(argv)
    result = (
        run_workspace_candidate_payoff_forecast_agent(
            args.workspace, args.author, timeout_seconds=args.timeout_seconds,
        )
        if args.author else
        compile_workspace_candidate_payoff_forecast(args.workspace, args.forecast)
    )
    print(json.dumps(
        result, indent=2, sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FORECAST_SCHEMA", "RESULT_SCHEMA", "REQUEST_SCHEMA", "JOB_SCHEMA", "JOB_KIND",
    "compile_candidate_payoff_forecast", "compile_workspace_candidate_payoff_forecast",
    "due_candidate_payoff_forecast_requests", "enqueue_next_candidate_payoff_forecast",
    "run_workspace_candidate_payoff_forecast_agent",
]
