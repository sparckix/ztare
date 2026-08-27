"""Prospective market-state forecasts with source-time and outcome-time separation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import MetricObservation, PointInTimeSnapshot, canonical_timestamp, timestamp_key
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .observation_index import load_observation_rows, observation_source_sha256
from .tournament import (
    BacktestEpisode,
    ObservableSpec,
    WorldModelCandidate,
    WorldModelForecast,
    evaluate_world_model_tournament,
)


MARKET_STATE_RUN_SCHEMA = "jaggedthoughts-market-state-forecast-run-v1"
MARKET_STATE_SETTLEMENT_SCHEMA = "jaggedthoughts-market-state-settlement-v1"
MARKET_STATE_STATUS_SCHEMA = "jaggedthoughts-market-state-forecast-status-v1"
_SNAPSHOT_SCHEMA = "jaggedthoughts-market-state-snapshot-artifact-v2"
_COMPATIBILITY_KEY = "damodaran-current-erp__fred-nominal-real-curve__retrieval-epoch-v3"
_FORECAST_POLICY_VERSION = "5"
_OBSERVABLE_IDS = ("spy_total_return", "term_spread_change")
_REQUIRED_SOURCES = (
    "nyu_us_implied_erp",
    "fred_public_market_state",
    "yahoo_spy_adjusted_daily",
)
_OPTIONAL_SOURCES = ("public_sp500_yield_surface",)
MARKET_STATE_SOURCE_IDS = _REQUIRED_SOURCES


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _observations(
    root: Path, *, as_of: str, pairs: Iterable[tuple[str, str]],
) -> tuple[MetricObservation, ...]:
    selected = set(pairs)
    rows = load_observation_rows(
        root / "data" / "observations.csv", as_of=as_of,
        entity_ids={entity for entity, _metric in selected},
        metric_ids={metric for _entity, metric in selected},
        effective_per_observed=True,
    )
    return tuple(
        MetricObservation(
            observation_id=str(row["observation_id"]),
            entity_id=str(row["entity_id"]),
            metric_id=str(row["metric_id"]),
            value=float(row["value"]),
            unit=str(row["unit"]),
            observed_at=str(row["observed_at"]),
            available_at=str(row["available_at"]),
            source_ref=str(row["source_ref"]),
        )
        for row in rows
        if (str(row["entity_id"]), str(row["metric_id"])) in selected
    )


def _latest(
    rows: Iterable[MetricObservation], *, entity_id: str, metric_id: str, as_of: str,
) -> MetricObservation:
    cutoff = timestamp_key(as_of)
    eligible = [
        row for row in rows
        if row.entity_id == entity_id and row.metric_id == metric_id
        and timestamp_key(row.available_at) <= cutoff and timestamp_key(row.observed_at) <= cutoff
    ]
    if not eligible:
        raise ValueError(f"market-state source missing: {entity_id}.{metric_id}")
    return max(eligible, key=lambda row: (timestamp_key(row.observed_at), timestamp_key(row.available_at), row.observation_id))


def _receipt_index(root: Path, *, as_of: str) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in (root / "data" / "source_receipts.json", root / "market_state" / "source_receipts.json"):
        payload = _read_json(path) or {}
        for row in payload.get("receipts") or ():
            if isinstance(row, Mapping):
                receipts[str(row.get("source_id") or "")] = dict(row)
    missing = [source_id for source_id in _REQUIRED_SOURCES if source_id not in receipts]
    if missing:
        raise ValueError("market-state issue requires one current source run containing: " + ", ".join(missing))
    for source_id in _REQUIRED_SOURCES:
        if timestamp_key(str(receipts[source_id]["retrieved_at"])) > timestamp_key(as_of):
            raise ValueError(f"market-state source receipt is later than issue time: {source_id}")
    return receipts


def _latest_from_receipts(
    rows: Iterable[MetricObservation], *, entity_id: str, metric_id: str,
    as_of: str, receipts: Mapping[str, Mapping[str, Any]],
) -> MetricObservation:
    """Select an observation admissible under its cited receipt's availability mode."""

    cutoff = timestamp_key(as_of)
    def receipt_binds(row: MetricObservation) -> bool:
        receipt = receipts.get(row.source_ref)
        if receipt is None:
            return False
        retrieved_at = str(receipt.get("retrieved_at") or "")
        if str(receipt.get("availability_mode") or "") == "retrieval_only":
            return row.available_at == retrieved_at
        return timestamp_key(row.available_at) <= timestamp_key(retrieved_at)

    eligible = [
        row for row in rows
        if row.entity_id == entity_id and row.metric_id == metric_id
        and timestamp_key(row.available_at) <= cutoff
        and timestamp_key(row.observed_at) <= cutoff
        and receipt_binds(row)
    ]
    if not eligible:
        raise ValueError(f"market-state receipt-bound source missing: {entity_id}.{metric_id}")
    return max(eligible, key=lambda row: (timestamp_key(row.observed_at), row.observation_id))


def _age_days(observation: MetricObservation, as_of: str) -> float:
    return (timestamp_key(as_of) - timestamp_key(observation.observed_at)).total_seconds() / 86_400


def capture_market_state_snapshot(root: Path, *, as_of: str | None = None) -> dict[str, Any]:
    """Freeze the asynchronous information set used by every horizon issued now."""

    issued_at = canonical_timestamp(as_of or _utc_now(), "market-state issue time")
    coordinate_pairs = {
        ("US-MARKET", "implied_equity_risk_premium"),
        ("US-MARKET", "risk_free_rate"),
        ("US-MACRO", "term_spread_10y_3m"),
        ("US-MACRO", "treasury_3m_yield"),
        ("US-MACRO", "treasury_1y_yield"),
        ("US-MACRO", "treasury_10y_real_yield"),
        ("US-MACRO", "breakeven_inflation_10y"),
        ("SPY", "adjusted_price"),
        *(("US-MARKET", metric_id) for metric_id in (
            "sp500_trailing_earnings_yield", "sp500_forward_earnings_yield",
            "sp500_trailing_dividend_yield", "implied_erp_ttm_cash_yield",
            "implied_erp_10y_average_cash_flow_yield", "implied_erp_net_cash_yield",
            "implied_erp_normalized_earnings_payout",
        )),
    }
    rows = _observations(root, as_of=issued_at, pairs=coordinate_pairs)
    receipts = _receipt_index(root, as_of=issued_at)
    def current(entity_id: str, metric_id: str) -> MetricObservation:
        return _latest_from_receipts(
            rows, entity_id=entity_id, metric_id=metric_id,
            as_of=issued_at, receipts=receipts,
        )
    selected = {
        "implied_equity_risk_premium": current("US-MARKET", "implied_equity_risk_premium"),
        "valuation_treasury_rate": current("US-MARKET", "risk_free_rate"),
        "term_spread_10y_3m": current("US-MACRO", "term_spread_10y_3m"),
        "treasury_3m_yield": current("US-MACRO", "treasury_3m_yield"),
        "treasury_1y_yield": current("US-MACRO", "treasury_1y_yield"),
        "treasury_10y_real_yield": current("US-MACRO", "treasury_10y_real_yield"),
        "breakeven_inflation_10y": current("US-MACRO", "breakeven_inflation_10y"),
        "spy_adjusted_price_reference": current("SPY", "adjusted_price"),
    }
    optional_coordinates = {
        "sp500_trailing_earnings_yield": ("US-MARKET", "sp500_trailing_earnings_yield"),
        "sp500_forward_earnings_yield": ("US-MARKET", "sp500_forward_earnings_yield"),
        "sp500_trailing_dividend_yield": ("US-MARKET", "sp500_trailing_dividend_yield"),
        "implied_erp_ttm_cash_yield": ("US-MARKET", "implied_erp_ttm_cash_yield"),
        "implied_erp_10y_average_cash_flow_yield": ("US-MARKET", "implied_erp_10y_average_cash_flow_yield"),
        "implied_erp_net_cash_yield": ("US-MARKET", "implied_erp_net_cash_yield"),
        "implied_erp_normalized_earnings_payout": ("US-MARKET", "implied_erp_normalized_earnings_payout"),
    }
    for key, (entity_id, metric_id) in optional_coordinates.items():
        try:
            row = current(entity_id, metric_id)
        except ValueError:
            continue
        selected[key] = row
    freshness = {
        "implied_equity_risk_premium": 45,
        "valuation_treasury_rate": 45,
        "term_spread_10y_3m": 7,
        "treasury_3m_yield": 7,
        "treasury_1y_yield": 7,
        "treasury_10y_real_yield": 7,
        "breakeven_inflation_10y": 7,
        "spy_adjusted_price_reference": 7,
        "sp500_trailing_earnings_yield": 7,
        "sp500_forward_earnings_yield": 45,
        "sp500_trailing_dividend_yield": 7,
        "implied_erp_ttm_cash_yield": 45,
        "implied_erp_10y_average_cash_flow_yield": 45,
        "implied_erp_net_cash_yield": 45,
        "implied_erp_normalized_earnings_payout": 45,
    }
    stale = {
        key: round(_age_days(row, issued_at), 3)
        for key, row in selected.items() if _age_days(row, issued_at) > freshness[key]
    }
    required_keys = {
        "implied_equity_risk_premium", "valuation_treasury_rate", "term_spread_10y_3m",
        "treasury_3m_yield", "treasury_1y_yield", "treasury_10y_real_yield",
        "breakeven_inflation_10y", "spy_adjusted_price_reference",
    }
    required_stale = {key: value for key, value in stale.items() if key in required_keys}
    if required_stale:
        raise ValueError(f"market-state coordinates exceed issue-time staleness ceilings: {required_stale}")
    for key in set(stale) - required_keys:
        selected.pop(key, None)
    source_path = root / "data" / "observations.csv"
    source_sha = observation_source_sha256(source_path)
    observation_tuple = tuple(selected.values())
    snapshot_id = f"us-market-{issued_at[:10]}-{stable_sha256({'as_of': issued_at, 'observations': [row.observation_id for row in observation_tuple]})[:12]}"
    snapshot = PointInTimeSnapshot(
        snapshot_id=snapshot_id,
        as_of=issued_at,
        source_path="data/observations.csv",
        source_sha256=source_sha,
        observations=observation_tuple,
        excluded_future_count=sum(timestamp_key(row.available_at) > timestamp_key(issued_at) for row in rows),
    )
    methods = {
        "implied_equity_risk_premium": "damodaran_ttm_adjusted_payout_current_erp",
        "valuation_treasury_rate": "damodaran_displayed_treasury_valuation_rate",
        "term_spread_10y_3m": "fred_t10y3m_market_yield_spread",
        "treasury_3m_yield": "fred_dgs3mo_market_yield",
        "treasury_1y_yield": "fred_dgs1_market_yield",
        "treasury_10y_real_yield": "fred_dfii10_real_market_yield",
        "breakeven_inflation_10y": "fred_t10yie_market_breakeven",
        "spy_adjusted_price_reference": "yahoo_adjusted_close_reference_only",
        "sp500_trailing_earnings_yield": "multpl_trailing_as_reported_earnings_to_price",
        "sp500_forward_earnings_yield": "nyse_factset_forward_12m_pe_reciprocal",
        "sp500_trailing_dividend_yield": "multpl_trailing_dividend_to_price",
        "implied_erp_ttm_cash_yield": "damodaran_ttm_cash_yield_implied_erp",
        "implied_erp_10y_average_cash_flow_yield": "damodaran_10y_average_cash_flow_yield_implied_erp",
        "implied_erp_net_cash_yield": "damodaran_net_cash_yield_implied_erp",
        "implied_erp_normalized_earnings_payout": "damodaran_normalized_earnings_payout_implied_erp",
    }
    observation_records = {
        key: {
            **row.to_dict(),
            "methodology_id": methods[key],
            "age_at_issue_days": round(_age_days(row, issued_at), 3),
            "source_receipt_sha256": receipts[row.source_ref]["receipt_sha256"],
            "source_content_sha256": receipts[row.source_ref]["content_sha256"],
        }
        for key, row in selected.items()
    }
    state_coordinates = {
        key: value for key, value in observation_records.items()
        if key != "spy_adjusted_price_reference"
    }
    nominal_risk_free = selected["valuation_treasury_rate"].value
    nominal_erp = selected["implied_equity_risk_premium"].value
    real_risk_free = selected["treasury_10y_real_yield"].value
    breakeven = selected["breakeven_inflation_10y"].value
    nominal_equity_return = nominal_risk_free + nominal_erp
    real_equity_return = (1.0 + nominal_equity_return) / (1.0 + breakeven) - 1.0
    real_erp = (1.0 + real_equity_return) / (1.0 + real_risk_free) - 1.0
    recomposed_nominal_risk_free = (1.0 + real_risk_free) * (1.0 + breakeven) - 1.0
    erp_variants = [
        selected[key].value for key in (
            "implied_equity_risk_premium", "implied_erp_ttm_cash_yield",
            "implied_erp_10y_average_cash_flow_yield", "implied_erp_net_cash_yield",
            "implied_erp_normalized_earnings_payout",
        ) if key in selected
    ]
    valuation_spreads = {
        "forward_earnings_yield_minus_nominal_10y": (
            selected["sp500_forward_earnings_yield"].value - recomposed_nominal_risk_free
            if "sp500_forward_earnings_yield" in selected else None
        ),
        "trailing_earnings_yield_minus_tips_diagnostic": (
            selected["sp500_trailing_earnings_yield"].value - real_risk_free
            if "sp500_trailing_earnings_yield" in selected else None
        ),
        "dividend_yield_minus_tips_income_diagnostic": (
            selected["sp500_trailing_dividend_yield"].value - real_risk_free
            if "sp500_trailing_dividend_yield" in selected else None
        ),
    }
    body = {
        "schema": _SNAPSHOT_SCHEMA,
        "compatibility_key": _COMPATIBILITY_KEY,
        "point_in_time_snapshot": snapshot.to_dict(),
        "state": {
            "implied_equity_risk_premium": selected["implied_equity_risk_premium"].value,
            "nominal_implied_equity_risk_premium": nominal_erp,
            "implied_nominal_equity_return": nominal_equity_return,
            "implied_real_equity_return": real_equity_return,
            "implied_real_equity_risk_premium": real_erp,
            "treasury_10y_real_yield": real_risk_free,
            "breakeven_inflation_10y": breakeven,
            "nominal_real_risk_free_reconciliation_residual": (
                nominal_risk_free - recomposed_nominal_risk_free
            ),
            "sp500_trailing_earnings_yield": (
                selected.get("sp500_trailing_earnings_yield").value
                if selected.get("sp500_trailing_earnings_yield") else None
            ),
            "sp500_forward_earnings_yield": (
                selected.get("sp500_forward_earnings_yield").value
                if selected.get("sp500_forward_earnings_yield") else None
            ),
            "sp500_trailing_dividend_yield": (
                selected.get("sp500_trailing_dividend_yield").value
                if selected.get("sp500_trailing_dividend_yield") else None
            ),
            "valuation_spreads": valuation_spreads,
            "cash_flow_implied_erp_range": [min(erp_variants), max(erp_variants)],
            "term_spread_10y_3m": selected["term_spread_10y_3m"].value,
        },
        "valuation_context": {
            "displayed_nominal_treasury_rate": nominal_risk_free,
            "displayed_treasury_rate": nominal_risk_free,
            "method": "price-implied S&P cash-flow return in matched nominal and real numeraires",
        },
        "cash_yields": {
            "90": selected["treasury_3m_yield"].value,
            "365": selected["treasury_1y_yield"].value,
        },
        "outcome_anchor": {
            "entity_id": "SPY",
            "metric_id": "adjusted_price",
            "issue_reference": observation_records["spy_adjusted_price_reference"],
            "settlement_rule": "re-read issue and target adjusted closes from one later receipt",
        },
        "state_coordinates": state_coordinates,
        "source_receipts": {source_id: receipts[source_id] for source_id in _REQUIRED_SOURCES},
        "capital_authority": False,
    }
    artifact = {**body, "snapshot_artifact_sha256": stable_sha256(body)}
    path = root / "market_state" / "snapshots" / f"{snapshot_id}.json"
    _atomic_json(path, artifact)
    return {**artifact, "snapshot_path": path.relative_to(root).as_posix()}


def _prior_snapshot(root: Path, current: Mapping[str, Any]) -> dict[str, Any] | None:
    issued = str((current.get("point_in_time_snapshot") or {}).get("as_of") or "")
    candidates = []
    for path in (root / "market_state" / "snapshots").glob("*.json"):
        row = _read_json(path)
        if (
            row and row.get("compatibility_key") == _COMPATIBILITY_KEY
            and str((row.get("point_in_time_snapshot") or {}).get("as_of") or "") < issued
        ):
            candidates.append(row)
    return max(candidates, key=lambda row: str((row["point_in_time_snapshot"] or {}).get("as_of") or ""), default=None)


def _read_tsv(path: Path) -> list[dict[str, float]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, map(float, line.split("\t")))) for line in lines[1:] if line.strip()]


def _horizonize(annual_return: float, horizon_days: int) -> float:
    if annual_return <= -1:
        return -1.0
    return (1 + annual_return) ** (horizon_days / 365.25) - 1


def _probe_weight(predicted_return: float, cash_return: float, horizon_days: int) -> float:
    excess_scale = _horizonize(0.08, horizon_days)
    return min(0.25, max(0.0, 0.25 * (predicted_return - cash_return) / excess_scale))


def _forecast(
    model_id: str,
    family: str,
    predicted_return: float,
    term_spread_change: float,
    *,
    horizon_days: int,
    cash_return: float,
    mechanism_ids: tuple[str, ...],
    source_refs: tuple[str, ...],
    explanation: Mapping[str, Any],
    promotion_eligible: bool = True,
    implementation_refs: tuple[str, ...] = (),
) -> dict[str, Any]:
    identity = {
        "model_id": model_id,
        "version": _FORECAST_POLICY_VERSION,
        "model_family": family,
        "trial_family_id": f"{model_id}-v{_FORECAST_POLICY_VERSION}",
        "mechanism_ids": list(mechanism_ids),
        "promotion_eligible": bool(promotion_eligible),
        "implementation_refs": list(implementation_refs or (f"market-state-policy-v{_FORECAST_POLICY_VERSION}",)),
    }
    body = {
        **identity,
        "model_identity_sha256": stable_sha256(identity),
        "predicted_values": {
            "spy_total_return": float(predicted_return),
            "term_spread_change": float(term_spread_change),
        },
        "target_weight": _probe_weight(predicted_return, cash_return, horizon_days),
        "source_refs": list(source_refs),
        "explanation": dict(explanation),
        "capital_authority": False,
    }
    return {**body, "forecast_sha256": stable_sha256(body)}


def _newton_result_errors(
    result: Mapping[str, Any], *, project_path: Path, module_path: Path,
) -> list[str]:
    expected = {
        "candidate_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
        "evidence_receipt_sha256": hashlib.sha256(
            (project_path / "evidence_source_receipt.json").read_bytes()
        ).hexdigest(),
        "gate_result_sha256": hashlib.sha256(
            (project_path / "latest_gate_results.json").read_bytes()
        ).hexdigest(),
    }
    errors = []
    if result.get("status") != "screen_rejected" or result.get("promotion_eligible") is not False:
        errors.append("result_is_not_a_rejected_shadow")
    errors.extend(
        f"{key}_mismatch" for key, value in expected.items()
        if result.get(key) != value
    )
    body = {key: value for key, value in result.items() if key != "research_result_sha256"}
    if result.get("research_result_sha256") != stable_sha256(body):
        errors.append("research_result_hash_mismatch")
    return errors


def _challengers(
    root: Path, snapshot: Mapping[str, Any], *, horizon_days: int, project_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    state = dict(snapshot["state"])
    valuation = dict(snapshot["valuation_context"])
    cash_yield = float(snapshot["cash_yields"][str(horizon_days)])
    cash_return = _horizonize(cash_yield, horizon_days)
    visible = _read_tsv(project_path / "evidence_state.txt")
    annual_mean = sum(row["next_total_return"] for row in visible) / len(visible)
    source_refs = (str(snapshot["snapshot_artifact_sha256"]),)
    forecasts = [
        _forecast(
            "unconditional_no_change", "historical_control", _horizonize(annual_mean, horizon_days), 0.0,
            horizon_days=horizon_days, cash_return=cash_return, mechanism_ids=("historical_mean_return", "zero_state_change"),
            source_refs=source_refs + (hashlib.sha256((project_path / "evidence_state.txt").read_bytes()).hexdigest(),),
            explanation={"annual_historical_mean": annual_mean, "state_rule": "no change"},
        ),
        _forecast(
            "implied_required_return", "valuation_required_return",
            _horizonize(float(state["implied_nominal_equity_return"]), horizon_days), 0.0,
            horizon_days=horizon_days, cash_return=cash_return,
            mechanism_ids=("matched_valuation_treasury_rate", "implied_equity_risk_premium"),
            source_refs=source_refs,
            explanation={
                "identity": "required-return challenger, not a state price or risk-neutral forecast",
                "annual_to_horizon": "(1 + matched_valuation_treasury_rate + implied_erp) ** (days / 365.25) - 1",
                "matched_valuation_treasury_rate": valuation["displayed_nominal_treasury_rate"],
                "cash_return_role": "economic comparator and probe baseline only",
            },
        ),
        _forecast(
            "all_zero_diagnostic", "sanity_control", 0.0, 0.0,
            horizon_days=horizon_days, cash_return=cash_return, mechanism_ids=("zero_return", "zero_state_change"),
            source_refs=source_refs, explanation={"use": "diagnostic only; not the tournament baseline"},
            promotion_eligible=False,
        ),
    ]
    unavailable = [
        {"model_id": "ridge_var", "status": "unavailable_insufficient_compatible_prospective_history"},
        {"model_id": "discrete_transition", "status": "unavailable_insufficient_compatible_prospective_history", "minimum_settled_episodes": 18},
    ]
    if horizon_days != 365:
        unavailable.append({
            "model_id": "newton_rejected_shadow",
            "status": "unavailable_incompatible_horizon",
            "reason": "the archived Newton project was fit to annual targets",
        })
        return forecasts, unavailable
    prior = _prior_snapshot(root, snapshot)
    if not prior:
        unavailable.append({"model_id": "newton_rejected_shadow", "status": "unavailable_missing_compatible_lagged_snapshot"})
        return forecasts, unavailable
    module_path = project_path / "test_model.py"
    result = _read_json(root / "experiments" / "results" / "jaggedthoughts_market_state_newton.json") or {}
    result_errors = _newton_result_errors(
        result, project_path=project_path, module_path=module_path,
    )
    if result_errors:
        unavailable.append({
            "model_id": "newton_rejected_shadow",
            "status": "unavailable_unverified_project_result",
            "reason_codes": result_errors,
        })
        return forecasts, unavailable
    spec = importlib.util.spec_from_file_location("jaggedthoughts_market_state_newton_shadow", module_path)
    if spec is None or spec.loader is None:
        raise ValueError("Newton shadow module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prior_state = dict(prior["state"])
    features = {
        "erp": float(state["implied_equity_risk_premium"]),
        "term_spread": float(state["term_spread_10y_3m"]),
        "delta_erp": float(state["implied_equity_risk_premium"]) - float(prior_state["implied_equity_risk_premium"]),
        "delta_term_spread": float(state["term_spread_10y_3m"]) - float(prior_state["term_spread_10y_3m"]),
    }
    params = module.fit_model(visible)
    annual_prediction = float(module.I_model(features, params))
    _erp_diagnostic, annual_spread_change = map(float, module.predict_state_change(features, params))
    prior_result_hash = str(result["research_result_sha256"])
    module_hash = hashlib.sha256(module_path.read_bytes()).hexdigest()
    forecasts.append(_forecast(
        "newton_rejected_shadow", "newton", _horizonize(annual_prediction, horizon_days),
        annual_spread_change * horizon_days / 365.25,
        horizon_days=horizon_days, cash_return=cash_return,
        mechanism_ids=("coupled_erp_term_spread_action", "linked_term_spread_response"),
        source_refs=source_refs + (prior_result_hash, module_hash),
        explanation={
            "prior_status": result.get("status") or "screen_rejected",
            "prior_result_sha256": prior_result_hash,
            "methodology_transfer": "diagnostic_bootstrap_across_incompatible_erp_spread_epochs",
            "erp_innovation_prediction": _erp_diagnostic,
            "erp_innovation_credit": False,
        },
        promotion_eligible=False,
        implementation_refs=(prior_result_hash, module_hash),
    ))
    return forecasts, unavailable


def _append_leaf(
    store_path: Path, *, owner: str, kind: str, object_id: str, epoch: str,
    occurred_at: str, payload: Mapping[str, Any], source_refs: tuple[str, ...],
    edges: tuple[tuple[str, str], ...] = (),
) -> str:
    store = GoldenStore(store_path)
    existing = store.identity(owner, kind, object_id, epoch)
    if existing:
        if (
            existing["payload_sha256"] != stable_sha256(payload)
            or existing["occurred_at"] != canonical_timestamp(occurred_at, "leaf occurred_at")
            or tuple(existing["source_refs"]) != tuple(sorted(set(source_refs)))
        ):
            raise ValueError(f"market-state golden identity changed content: {kind}/{object_id}@{epoch}")
        store.append_bundle(
            (), tuple(GoldenEdge(existing["leaf_sha256"], target, relation) for target, relation in edges),
            make_heads=True,
        )
        return str(existing["leaf_sha256"])
    leaf = GoldenLeaf(
        owner=owner, object_kind=kind, object_id=object_id, epoch=epoch,
        occurred_at=occurred_at, available_at=occurred_at, payload=dict(payload), source_refs=source_refs,
    )
    store.append_bundle(
        (leaf,), tuple(GoldenEdge(leaf.leaf_sha256, target, relation) for target, relation in edges),
        make_heads=True,
    )
    return leaf.leaf_sha256


def _replay_market_state_run(
    root: Path, *, owner: str, store_path: Path,
    run: Mapping[str, Any], path: Path, replay_reason: str,
) -> dict[str, Any]:
    snapshot = dict(run["snapshot"])
    snapshot_leaf = _append_leaf(
        store_path, owner=owner, kind="market_state_snapshot",
        object_id=str(snapshot["point_in_time_snapshot"]["snapshot_id"]),
        epoch=str(snapshot["snapshot_artifact_sha256"]), occurred_at=str(run["opened_at"]),
        payload=snapshot,
        source_refs=tuple(
            str(snapshot["source_receipts"][source_id]["receipt_sha256"])
            for source_id in _REQUIRED_SOURCES
        ),
    )
    run_leaf = _append_leaf(
        store_path, owner=owner, kind="market_state_forecast_run",
        object_id=str(run["run_id"]), epoch=str(run["run_sha256"]),
        occurred_at=str(run["opened_at"]), payload=run,
        source_refs=(str(snapshot["snapshot_artifact_sha256"]),),
        edges=((snapshot_leaf, "derived_from"),),
    )
    return {
        **run, "replayed": True, "replay_reason": replay_reason,
        "run_path": path.relative_to(root).as_posix(), "golden_leaf_sha256": run_leaf,
    }


def _issuance_bucket_id(*, horizon_days: int, cadence_days: int, issued_at: str) -> str:
    if not 1 <= cadence_days <= horizon_days:
        raise ValueError("market-state issuance cadence must be in [1, horizon_days]")
    issued_date = datetime.fromisoformat(issued_at.replace("Z", "+00:00")).date()
    return f"{horizon_days}d::{cadence_days}d::{issued_date.toordinal() // cadence_days}"


def _issuance_bucket_run(
    root: Path, *, horizon_days: int, issuance_bucket_id: str,
) -> tuple[dict[str, Any], Path] | None:
    rows = []
    for path in (root / "market_state" / "runs").glob("*.json"):
        run = _read_json(path)
        if (
            run and run.get("schema") == MARKET_STATE_RUN_SCHEMA
            and int(run.get("horizon_days") or 0) == horizon_days
            and run.get("issuance_bucket_id") == issuance_bucket_id
        ):
            rows.append((run, path))
    return min(rows, key=lambda pair: (str(pair[0]["opened_at"]), str(pair[0]["run_id"])), default=None)


def open_market_state_forecast(
    root: Path, *, owner: str, store_path: Path, horizon_days: int,
    project_path: Path, issued_at: str | None = None, issuance_cadence_days: int = 1,
) -> dict[str, Any]:
    if horizon_days not in {90, 365}:
        raise ValueError("market-state horizon must be 90 or 365 days")
    issued = canonical_timestamp(issued_at or _utc_now(), "market-state issued_at")
    bucket_id = _issuance_bucket_id(
        horizon_days=horizon_days, cadence_days=issuance_cadence_days, issued_at=issued,
    )
    bucket = _issuance_bucket_run(
        root, horizon_days=horizon_days, issuance_bucket_id=bucket_id,
    )
    if bucket:
        run, path = bucket
        return _replay_market_state_run(
            root, owner=owner, store_path=store_path, run=run, path=path,
            replay_reason="existing_issuance_bucket",
        )
    snapshot = capture_market_state_snapshot(root, as_of=issued)
    identity = stable_sha256({
        "snapshot": snapshot["snapshot_artifact_sha256"],
        "horizon_days": horizon_days,
        "issuance_bucket_id": bucket_id,
        "forecast_policy_version": _FORECAST_POLICY_VERSION,
    })
    run_id = f"market-state-{horizon_days}d-{identity[:20]}"
    path = root / "market_state" / "runs" / f"{run_id}.json"
    prior = _read_json(path)
    if prior:
        return _replay_market_state_run(
            root, owner=owner, store_path=store_path, run=prior, path=path,
            replay_reason="identical_run_identity",
        )
    end_at = (datetime.fromisoformat(issued.replace("Z", "+00:00")) + timedelta(days=horizon_days)).isoformat(timespec="seconds").replace("+00:00", "Z")
    forecasts, unavailable = _challengers(root, snapshot, horizon_days=horizon_days, project_path=project_path)
    cash_yield = float(snapshot["cash_yields"][str(horizon_days)])
    observable_contract = {
        "spy_total_return": "same-receipt adjusted-close simple return",
        "term_spread_change": "first T10Y3M observation on or after target minus issue value",
        "erp_change": "settlement diagnostic only; no linked-mechanism credit",
    }
    shared_weight_policy = "clamp 0..25% of forecast excess over cash, reaching 25% at 8% annualized excess"
    inference_epoch_key = stable_sha256({
        "horizon_days": horizon_days,
        "issuance_cadence_days": issuance_cadence_days,
        "snapshot_compatibility_key": snapshot["compatibility_key"],
        "forecast_policy_version": _FORECAST_POLICY_VERSION,
        "observable_contract": observable_contract,
        "shared_weight_policy": shared_weight_policy,
    })
    body = {
        "schema": MARKET_STATE_RUN_SCHEMA,
        "run_id": run_id,
        "episode_id": f"us-market::{issued[:10]}::{horizon_days}d",
        "inference_epoch_key": inference_epoch_key,
        "inference_block_id": stable_sha256({"issue_date": issued[:10], "inference_epoch_key": inference_epoch_key}),
        "status": "pending_outcome",
        "mode": "prospective_shadow",
        "opened_at": issued,
        "end_at": end_at,
        "horizon_days": horizon_days,
        "issuance_cadence_days": issuance_cadence_days,
        "issuance_bucket_id": bucket_id,
        "snapshot": snapshot,
        "candidate_forecasts": forecasts,
        "unavailable_challengers": unavailable,
        "observable_contract": observable_contract,
        "cash_contract": {
            "yield_metric_id": "treasury_3m_yield" if horizon_days == 90 else "treasury_1y_yield",
            "issue_yield": cash_yield,
            "return_proxy": _horizonize(cash_yield, horizon_days),
        },
        "forecast_policy_version": _FORECAST_POLICY_VERSION,
        "shared_weight_policy": shared_weight_policy,
        "prior_rejection_preserved": True,
        "capital_authority": False,
    }
    run = {**body, "run_sha256": stable_sha256(body)}
    _validated_run_signature(run)
    _atomic_json(path, run)
    snapshot_leaf = _append_leaf(
        store_path, owner=owner, kind="market_state_snapshot",
        object_id=str(snapshot["point_in_time_snapshot"]["snapshot_id"]),
        epoch=str(snapshot["snapshot_artifact_sha256"]), occurred_at=issued, payload=snapshot,
        source_refs=tuple(str(snapshot["source_receipts"][source_id]["receipt_sha256"]) for source_id in _REQUIRED_SOURCES),
    )
    run_leaf = _append_leaf(
        store_path, owner=owner, kind="market_state_forecast_run", object_id=run_id,
        epoch=str(run["run_sha256"]), occurred_at=issued, payload=run,
        source_refs=(str(snapshot["snapshot_artifact_sha256"]),), edges=((snapshot_leaf, "derived_from"),),
    )
    return {**run, "replayed": False, "run_path": path.relative_to(root).as_posix(), "golden_leaf_sha256": run_leaf}


def due_market_state_horizons(
    root: Path, *, windows: Iterable[Mapping[str, Any]], as_of: str | None = None,
) -> tuple[int, ...]:
    evaluation_at = canonical_timestamp(as_of or _utc_now(), "market-state due time")
    latest: dict[int, str] = {}
    protected_until: dict[int, str] = {}
    for path in (root / "market_state" / "runs").glob("*.json"):
        row = _read_json(path)
        if row and row.get("schema") == MARKET_STATE_RUN_SCHEMA:
            horizon = int(row["horizon_days"])
            latest[horizon] = max(latest.get(horizon, ""), str(row["opened_at"]))
            protected_until[horizon] = max(
                protected_until.get(horizon, ""), str(row.get("end_at") or ""),
            )
    due = []
    for window in windows:
        horizon = int(window.get("horizon_days") or 0)
        cadence = int(window.get("cadence_days") or 0)
        if horizon not in {90, 365} or not 1 <= cadence <= horizon:
            raise ValueError("market-state windows require 90/365-day horizons and cadence in [1, horizon]")
        prior = latest.get(horizon)
        if (
            (not protected_until.get(horizon)
             or timestamp_key(evaluation_at) > timestamp_key(protected_until[horizon]))
            and (not prior or (timestamp_key(evaluation_at) - timestamp_key(prior)).total_seconds() / 86_400 >= cadence)
        ):
            due.append(horizon)
    return tuple(sorted(set(due)))


def market_state_cycle_due(
    root: Path, *, windows: Iterable[Mapping[str, Any]], as_of: str | None = None,
) -> dict[str, Any]:
    """Project the issuance and settlement events that require a fresh source bundle."""
    evaluation_at = canonical_timestamp(as_of or _utc_now(), "market-state due time")
    due_horizons = due_market_state_horizons(root, windows=windows, as_of=evaluation_at)
    settled_ids = {
        str((_read_json(path) or {}).get("run_id") or "")
        for path in (root / "market_state" / "settlements").glob("*.json")
    }
    matured = []
    for path in (root / "market_state" / "runs").glob("*.json"):
        run = _read_json(path)
        if (
            run and str(run.get("run_id") or "") not in settled_ids
            and timestamp_key(str(run.get("end_at") or "")) <= timestamp_key(evaluation_at)
        ):
            matured.append(str(run["run_id"]))
    return {
        "evaluated_at": evaluation_at,
        "due": bool(due_horizons or matured),
        "due_horizons": list(due_horizons),
        "matured_run_ids": sorted(matured),
        "source_refresh_required": bool(due_horizons or matured),
    }


def _first_after(
    rows: Iterable[MetricObservation], *, entity_id: str, metric_id: str,
    target_at: str, as_of: str,
) -> MetricObservation | None:
    eligible = [
        row for row in rows if row.entity_id == entity_id and row.metric_id == metric_id
        and timestamp_key(row.observed_at) >= timestamp_key(target_at)
        and timestamp_key(row.available_at) <= timestamp_key(as_of)
    ]
    return min(eligible, key=lambda row: (timestamp_key(row.observed_at), timestamp_key(row.available_at), row.observation_id), default=None)


def _same_receipt_spy_return(root: Path, receipt: Mapping[str, Any], *, start_at: str, end_at: str) -> dict[str, Any] | None:
    raw = root / str(receipt.get("raw_path") or "")
    payload = _read_json(raw)
    try:
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        values = result["indicators"]["adjclose"][0]["adjclose"]
    except (KeyError, IndexError, TypeError):
        return None
    points = sorted(
        (datetime.fromtimestamp(float(epoch), tz=timezone.utc), float(value))
        for epoch, value in zip(timestamps, values) if value is not None
    )
    start = next(((time, value) for time, value in points if time >= timestamp_key(start_at)), None)
    end = next(((time, value) for time, value in points if time >= timestamp_key(end_at)), None)
    if not start or not end:
        return None
    return {
        "start": {"observed_at": start[0].isoformat().replace("+00:00", "Z"), "value": start[1]},
        "end": {"observed_at": end[0].isoformat().replace("+00:00", "Z"), "value": end[1]},
        "return": end[1] / start[1] - 1.0,
        "source_receipt_sha256": receipt["receipt_sha256"],
        "source_content_sha256": receipt["content_sha256"],
        "raw_path": receipt["raw_path"],
    }


def settle_due_market_state_forecasts(
    root: Path, *, owner: str, store_path: Path, as_of: str | None = None,
) -> dict[str, Any]:
    evaluation_at = canonical_timestamp(as_of or _utc_now(), "market-state settlement time")
    rows = _observations(
        root, as_of=evaluation_at, pairs={
            ("US-MARKET", "implied_equity_risk_premium"),
            ("US-MACRO", "term_spread_10y_3m"),
        },
    )
    spy_receipt: Mapping[str, Any] | None = None
    settled, pending = [], []
    for path in sorted((root / "market_state" / "runs").glob("*.json")):
        run = _read_json(path)
        if not run or run.get("schema") != MARKET_STATE_RUN_SCHEMA:
            continue
        output = root / "market_state" / "settlements" / f"{run['run_id']}.json"
        prior = _read_json(output)
        if prior:
            settled.append(prior)
            continue
        if timestamp_key(str(run["end_at"])) > timestamp_key(evaluation_at):
            pending.append({"run_id": run["run_id"], "reason": "horizon_not_reached"})
            continue
        if spy_receipt is None:
            spy_receipt = _receipt_index(root, as_of=evaluation_at)["yahoo_spy_adjusted_daily"]
        spy = _same_receipt_spy_return(root, spy_receipt, start_at=str(run["opened_at"]), end_at=str(run["end_at"]))
        erp = _first_after(rows, entity_id="US-MARKET", metric_id="implied_equity_risk_premium", target_at=str(run["end_at"]), as_of=evaluation_at)
        spread = _first_after(rows, entity_id="US-MACRO", metric_id="term_spread_10y_3m", target_at=str(run["end_at"]), as_of=evaluation_at)
        if spy is None or erp is None or spread is None:
            pending.append({"run_id": run["run_id"], "reason": "complete_outcome_coordinates_unavailable"})
            continue
        start_state = dict(run["snapshot"]["state"])
        actual = {
            "spy_total_return": float(spy["return"]),
            "erp_change": erp.value - float(start_state["implied_equity_risk_premium"]),
            "term_spread_change": spread.value - float(start_state["term_spread_10y_3m"]),
        }
        cash_return = float(run["cash_contract"]["return_proxy"])
        scores = []
        for forecast in run.get("candidate_forecasts") or ():
            predicted = dict(forecast["predicted_values"])
            weight = float(forecast["target_weight"])
            book_return = weight * actual["spy_total_return"] + (1 - weight) * cash_return - abs(weight) * 0.001
            scores.append({
                "model_id": forecast["model_id"],
                "forecast_sha256": forecast["forecast_sha256"],
                "return_absolute_error": abs(float(predicted["spy_total_return"]) - actual["spy_total_return"]),
                "term_spread_absolute_error": abs(float(predicted["term_spread_change"]) - actual["term_spread_change"]),
                "book_return_after_cost": book_return,
                "cash_excess_return": book_return - cash_return,
                "promotion_eligible": bool(forecast.get("promotion_eligible")),
            })
        body = {
            "schema": MARKET_STATE_SETTLEMENT_SCHEMA,
            "settlement_id": f"{run['run_id']}::settlement",
            "run_id": run["run_id"],
            "run_sha256": run["run_sha256"],
            "episode_id": run["episode_id"],
            "inference_block_id": run["inference_block_id"],
            "evaluated_at": evaluation_at,
            "outcome_available_at": max(
                str(spy_receipt["retrieved_at"]), erp.available_at, spread.available_at,
            ),
            "spy_same_receipt_return": spy,
            "erp_outcome": erp.to_dict(),
            "term_spread_outcome": spread.to_dict(),
            "actual_values": actual,
            "cash_return": cash_return,
            "candidate_scores": scores,
            "erp_credit_boundary": "raw change is diagnostic; no independent linked-mechanism credit",
            "capital_authority": False,
        }
        settlement = {**body, "settlement_sha256": stable_sha256(body)}
        _atomic_json(output, settlement)
        run_head = GoldenStore(store_path).head(owner, "market_state_forecast_run", str(run["run_id"]))
        leaf = _append_leaf(
            store_path, owner=owner, kind="market_state_forecast_settlement",
            object_id=str(body["settlement_id"]), epoch=str(run["run_sha256"]),
            occurred_at=evaluation_at, payload=settlement,
            source_refs=(str(spy_receipt["receipt_sha256"]), erp.source_ref, spread.source_ref),
            edges=((str(run_head["leaf_sha256"]), "settles"),),
        )
        settled.append({**settlement, "golden_leaf_sha256": leaf})
    return {"evaluated_at": evaluation_at, "settled": settled, "pending": pending, "settled_count": len(settled), "pending_count": len(pending), "capital_authority": False}


def _non_overlapping(rows: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected, prior_end = [], None
    for pair in sorted(rows, key=lambda pair: (str(pair[0]["opened_at"]), str(pair[0]["run_id"]))):
        if prior_end is None or timestamp_key(str(pair[0]["opened_at"])) >= timestamp_key(prior_end):
            selected.append(pair)
            prior_end = str(pair[0]["end_at"])
    return selected


def _candidate_identity(candidate: Mapping[str, Any]) -> str:
    implementation_refs = list(candidate.get("implementation_refs") or ())
    if not implementation_refs:
        raise ValueError(f"model implementation refs missing: {candidate.get('model_id')}")
    body = {
        "model_id": str(candidate["model_id"]),
        "version": str(candidate.get("version") or "1"),
        "model_family": str(candidate["model_family"]),
        "trial_family_id": str(candidate["trial_family_id"]),
        "mechanism_ids": list(candidate["mechanism_ids"]),
        "promotion_eligible": bool(candidate.get("promotion_eligible")),
        "implementation_refs": implementation_refs,
    }
    identity = stable_sha256(body)
    frozen = candidate.get("model_identity_sha256")
    if not frozen:
        raise ValueError(f"model identity hash missing: {body['model_id']}")
    if frozen != identity:
        raise ValueError(f"model identity hash mismatch: {body['model_id']}")
    return identity


def _model_research_activations(tournaments: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    activations = []
    for tournament in tournaments:
        if not tournament.get("inference_sufficient"):
            continue
        survivors = set(tournament.get("survivor_model_ids") or ())
        identities = dict(tournament.get("candidate_model_identity_sha256") or {})
        for track in tournament.get("model_tracks") or ():
            model = dict(track.get("model") or {})
            model_id = str(model.get("model_id") or "")
            if not model_id.endswith("_rejected_shadow"):
                continue
            action = "successor_research_due" if model_id in survivors else "retire_research_due"
            body = {
                "schema": "jaggedthoughts-model-research-activation-v1",
                "tournament_id": tournament["tournament_id"],
                "tournament_sha256": tournament["tournament_sha256"],
                "model_id": model_id,
                "model_identity_sha256": identities[model_id],
                "action": action,
                "reason": (
                    "screen-rejected lineage survived the prospective paired tournament; "
                    "author a distinct evidence-bound successor project"
                    if action == "successor_research_due" else
                    "screen-rejected lineage was prospectively dominated; retire this exact identity"
                ),
                "agent_authority": "propose_evidence_bound_project_only",
                "automatic_model_mutation": False,
                "capital_authority": False,
            }
            activations.append({**body, "activation_sha256": stable_sha256(body)})
    return activations


def _validated_run_signature(run: Mapping[str, Any]) -> tuple[str, ...]:
    candidates = list(run.get("candidate_forecasts") or ())
    if not candidates:
        raise ValueError("candidate forecast set is empty")
    model_ids = [str(row.get("model_id") or "") for row in candidates]
    if any(not model_id for model_id in model_ids) or len(set(model_ids)) != len(model_ids):
        raise ValueError("candidate model ids must be nonempty and unique")
    signature = []
    for candidate in candidates:
        predicted = dict(candidate.get("predicted_values") or {})
        if set(predicted) != set(_OBSERVABLE_IDS):
            raise ValueError(
                f"{candidate['model_id']} observable vector must equal {_OBSERVABLE_IDS}"
            )
        if any(not math.isfinite(float(predicted[key])) for key in _OBSERVABLE_IDS):
            raise ValueError(f"{candidate['model_id']} observable vector is non-finite")
        frozen_forecast = str(candidate.get("forecast_sha256") or "")
        forecast_body = {
            key: value for key, value in candidate.items() if key != "forecast_sha256"
        }
        if not frozen_forecast or stable_sha256(forecast_body) != frozen_forecast:
            raise ValueError(f"{candidate['model_id']} forecast hash mismatch")
        identity = _candidate_identity(candidate)
        signature.append(
            f"{candidate['model_id']}@{candidate.get('version', '1')}:"
            f"{candidate.get('trial_family_id', '')}:{identity}"
        )
    return tuple(sorted(signature))


def _tournament(
    runs: list[dict[str, Any]], settlements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_run = {str(row["run_id"]): row for row in runs}
    results, invalid_runs = [], []
    for horizon in (90, 365):
        horizon_pairs = [
            (by_run[str(row["run_id"])], row) for row in settlements
            if str(row.get("run_id")) in by_run and int(by_run[str(row["run_id"])]["horizon_days"]) == horizon
        ]
        valid = []
        for pair in horizon_pairs:
            try:
                signature = (
                    f"inference_epoch:{pair[0]['inference_epoch_key']}",
                    *_validated_run_signature(pair[0]),
                )
            except (KeyError, TypeError, ValueError) as error:
                invalid_runs.append({
                    "run_id": pair[0].get("run_id"), "horizon_days": horizon,
                    "reason": str(error),
                })
                continue
            valid.append((pair, signature))
        selected_pairs = _non_overlapping([pair for pair, _signature in valid])
        selected_ids = {str(run["run_id"]) for run, _settlement in selected_pairs}
        excluded_overlap_ids = sorted(
            str(pair[0]["run_id"]) for pair, _signature in valid
            if str(pair[0]["run_id"]) not in selected_ids
        )
        cohorts: dict[tuple[str, ...], list[tuple[dict[str, Any], dict[str, Any]]]] = {}
        for pair, signature in valid:
            if str(pair[0]["run_id"]) in selected_ids:
                cohorts.setdefault(signature, []).append(pair)
        for signature, cohort_pairs in sorted(cohorts.items()):
            pairs = cohort_pairs
            candidate_ids = {str(row["model_id"]) for row in pairs[0][0]["candidate_forecasts"]}
            first = {str(row["model_id"]): row for row in pairs[0][0]["candidate_forecasts"]}
            models = tuple(WorldModelCandidate(
                model_id=model_id, version=str(first[model_id].get("version") or "1"),
                model_family=str(first[model_id]["model_family"]),
                trial_family_id=str(first[model_id]["trial_family_id"]),
                mechanism_ids=tuple(first[model_id]["mechanism_ids"]),
                linked_observable_ids=("term_spread_change",) if first[model_id]["model_family"] == "newton" else (),
                source_refs=tuple(first[model_id].get("implementation_refs") or (
                    f"model-identity:{_candidate_identity(first[model_id])}",
                )),
            ) for model_id in sorted(candidate_ids))
            episodes, forecasts = [], []
            for run, settlement in pairs:
                actual = dict(settlement["actual_values"])
                episodes.append(BacktestEpisode(
                    episode_id=str(run["episode_id"]), inference_block_id=str(run["inference_block_id"]),
                    entity_id="US-MARKET", start_at=str(run["opened_at"]), end_at=str(run["end_at"]),
                    outcome_available_at=str(settlement["outcome_available_at"]), starting_weight=0.0,
                    asset_return=float(actual["spy_total_return"]), benchmark_return=float(settlement["cash_return"]),
                    cash_return=float(settlement["cash_return"]),
                    actual_values={"spy_total_return": float(actual["spy_total_return"]), "term_spread_change": float(actual["term_spread_change"])},
                    source_refs=(str(settlement["settlement_sha256"]),),
                ))
                for candidate in run["candidate_forecasts"]:
                    forecasts.append(WorldModelForecast(
                        model_id=str(candidate["model_id"]), episode_id=str(run["episode_id"]),
                        trained_through=str(run["opened_at"]), issued_at=str(run["opened_at"]),
                        predicted_values=dict(candidate["predicted_values"]), target_weight=float(candidate["target_weight"]),
                        source_refs=tuple(dict.fromkeys((
                            str(run["run_sha256"]), str(candidate["forecast_sha256"]),
                            *(str(ref) for ref in candidate.get("source_refs") or ()),
                        ))),
                    ))
            cohort_id = stable_sha256(signature)[:12]
            result = evaluate_world_model_tournament(
                tournament_id=f"market-state::{horizon}d::{cohort_id}", owner="jaggedthoughts-market-state-ledger",
                as_of=max(str(row["evaluated_at"]) for _run, row in pairs), mode="prospective_shadow",
                baseline_model_id="unconditional_no_change",
                observables=(
                    ObservableSpec("spy_total_return", "decimal_return", "absolute", 0.10, 0.75, "primary"),
                    ObservableSpec("term_spread_change", "decimal", "absolute", 0.01, 0.25, "linked"),
                ),
                models=models, episodes=tuple(episodes), forecasts=tuple(forecasts),
                transaction_cost_bps=10.0,
                declared_trial_family_ids=tuple(model.trial_family_id for model in models),
                source_refs=tuple(str(row["settlement_sha256"]) for _run, row in pairs),
                min_inference_blocks=8, periods_per_year=4 if horizon == 90 else 1,
            )
            eligibility = {model_id: bool(first[model_id].get("promotion_eligible")) for model_id in candidate_ids}
            results.append({
                **result,
                "candidate_cohort_id": cohort_id,
                "selected_non_overlapping_episode_ids": [str(run["episode_id"]) for run, _row in pairs],
                "excluded_overlap_count": len(excluded_overlap_ids),
                "excluded_overlap_run_ids": excluded_overlap_ids,
                "promotion_eligibility": eligibility,
                "candidate_model_identity_sha256": {
                    model_id: _candidate_identity(first[model_id])
                    for model_id in sorted(candidate_ids)
                },
                "authority_eligible_survivor_model_ids": [model_id for model_id in result["survivor_model_ids"] if eligibility.get(model_id)],
                "economic_boundary": "episodic paper timing comparison; not a self-financing portfolio history",
            })
    return results, invalid_runs


def market_state_forecast_status(root: Path) -> dict[str, Any]:
    runs = [
        {**row, "run_path": path.relative_to(root).as_posix()}
        for path in (root / "market_state" / "runs").glob("*.json")
        if (row := _read_json(path)) and row.get("schema") == MARKET_STATE_RUN_SCHEMA
    ]
    settlements = [
        {**row, "settlement_path": path.relative_to(root).as_posix()}
        for path in (root / "market_state" / "settlements").glob("*.json")
        if (row := _read_json(path)) and row.get("schema") == MARKET_STATE_SETTLEMENT_SCHEMA
    ]
    runs.sort(key=lambda row: str(row["opened_at"]), reverse=True)
    settlements.sort(key=lambda row: str(row["evaluated_at"]), reverse=True)
    settled_ids = {str(row["run_id"]) for row in settlements}
    latest_by_horizon: dict[str, dict[str, Any]] = {}
    for run in runs:
        latest_by_horizon.setdefault(str(run["horizon_days"]), run)
    tournaments, invalid_runs = _tournament(runs, settlements)
    model_research_activations = _model_research_activations(tournaments)
    return {
        "schema": MARKET_STATE_STATUS_SCHEMA,
        "enabled": True,
        "run_count": len(runs),
        "pending_count": sum(str(row["run_id"]) not in settled_ids for row in runs),
        "settled_count": len(settlements),
        "latest_run": runs[0] if runs else None,
        "latest_by_horizon": latest_by_horizon,
        "latest_settlement": settlements[0] if settlements else None,
        "tournaments": tournaments,
        "model_research_activations": model_research_activations,
        "invalid_tournament_runs": invalid_runs,
        "source_ids": list(_REQUIRED_SOURCES),
        "authority": "paper_shadow",
        "capital_authority": False,
    }


__all__ = [
    "MARKET_STATE_RUN_SCHEMA", "MARKET_STATE_SETTLEMENT_SCHEMA", "MARKET_STATE_STATUS_SCHEMA",
    "MARKET_STATE_SOURCE_IDS", "capture_market_state_snapshot", "due_market_state_horizons", "market_state_cycle_due", "market_state_forecast_status",
    "open_market_state_forecast", "settle_due_market_state_forecasts",
]
