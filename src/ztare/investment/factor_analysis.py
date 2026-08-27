"""Public-price factor decomposition for funds and portfolio sleeves.

The analyzer estimates a conditional benchmark, historical residual return,
tracking error, and assumption-implied return from aligned point-in-time price
observations.  It reuses ZTARE's multichannel OLS primitive, including its
leave-one-out fit check.  Historical residual return remains descriptive unless
an explicit persistence weight is supplied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable, Mapping

import numpy as np

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import ols_multichannel_r2

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .observation_index import load_observation_rows


FACTOR_ANALYSIS_SCHEMA = "jaggedthoughts-factor-analysis-v1"
RETURN_COVARIANCE_SCHEMA = "jaggedthoughts-return-covariance-v1"
HISTORICAL_FACTOR_CONTROL_SCHEMA = "jaggedthoughts-historical-factor-control-v1"


class InsufficientFactorHistoryError(ValueError):
    """The declared factor model is valid but its aligned history is incomplete."""


@dataclass(frozen=True, slots=True)
class FactorDefinition:
    factor_id: str
    long_entity_id: str
    short_entity_id: str = ""
    expected_annual_premium: float = 0.0

    def __post_init__(self) -> None:
        for attr in ("factor_id", "long_entity_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"factor.{attr}"))
        object.__setattr__(self, "short_entity_id", str(self.short_entity_id or "").strip())
        object.__setattr__(self, "expected_annual_premium", require_finite(
            self.expected_annual_premium, f"factor {self.factor_id} expected premium"
        ))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FactorDefinition":
        return cls(
            factor_id=str(payload.get("id") or payload.get("factor_id") or ""),
            long_entity_id=str(payload.get("long_entity_id") or ""),
            short_entity_id=str(payload.get("short_entity_id") or ""),
            expected_annual_premium=float(payload.get("expected_annual_premium", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id, "long_entity_id": self.long_entity_id,
            "short_entity_id": self.short_entity_id,
            "expected_annual_premium": self.expected_annual_premium,
        }


@dataclass(frozen=True, slots=True)
class PricePoint:
    entity_id: str
    observed_at: str
    available_at: str
    value: float
    observation_id: str
    source_ref: str

    def __post_init__(self) -> None:
        for attr in ("entity_id", "observation_id", "source_ref"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"price point {attr}"))
        object.__setattr__(self, "observed_at", canonical_timestamp(self.observed_at, "price observed_at"))
        object.__setattr__(self, "available_at", canonical_timestamp(self.available_at, "price available_at"))
        value = require_finite(self.value, "price value")
        if value <= 0:
            raise ValueError("price must be positive")
        object.__setattr__(self, "value", value)

    @property
    def date_key(self) -> str:
        return self.observed_at[:10]


@lru_cache(maxsize=8)
def _load_price_points_cached(
    observations_path: str, modified_ns: int, size: int, cutoff: str,
    metric_id: str, entity_ids: tuple[str, ...],
) -> tuple[PricePoint, ...]:
    del modified_ns, size
    wanted = set(entity_ids)
    rows: list[PricePoint] = []
    for row in load_observation_rows(
        observations_path, as_of=cutoff, entity_ids=wanted,
        metric_ids=(metric_id,), effective_per_observed=True,
    ):
        value = float(row["value"])
        if not math.isfinite(value) or value <= 0:
            continue
        rows.append(PricePoint(
            entity_id=str(row["entity_id"]),
            observed_at=str(row["observed_at"]),
            available_at=str(row["available_at"]),
            value=value,
            observation_id=str(row["observation_id"]),
            source_ref=str(row["source_ref"]),
        ))
    return tuple(rows)


def load_price_points(
    observations_path: str | Path,
    *,
    as_of: str,
    metric_id: str = "price",
    entity_ids: Iterable[str] | None = None,
) -> tuple[PricePoint, ...]:
    source = Path(observations_path).expanduser().resolve()
    stat = source.stat()
    return _load_price_points_cached(
        str(source), stat.st_mtime_ns, stat.st_size,
        canonical_timestamp(as_of, "factor as_of"), metric_id,
        tuple(sorted({entity_id.upper() for entity_id in entity_ids or ()})),
    )


def _series(points: Iterable[PricePoint], entity_id: str) -> dict[str, PricePoint]:
    by_date: dict[str, PricePoint] = {}
    for row in points:
        if row.entity_id != entity_id:
            continue
        current = by_date.get(row.date_key)
        if current is None or (row.available_at, row.observed_at, row.observation_id) > (
            current.available_at, current.observed_at, current.observation_id,
        ):
            by_date[row.date_key] = row
    if len(by_date) < 3:
        raise ValueError(f"factor analysis needs at least three prices for {entity_id}")
    return by_date


def _returns(
    series: Mapping[str, PricePoint],
) -> dict[tuple[str, str], tuple[float, tuple[PricePoint, PricePoint]]]:
    dates = sorted(series)
    rows: dict[tuple[str, str], tuple[float, tuple[PricePoint, PricePoint]]] = {}
    for previous_date, current_date in zip(dates, dates[1:]):
        previous, current = series[previous_date], series[current_date]
        rows[(previous_date, current_date)] = (
            current.value / previous.value - 1.0, (previous, current),
        )
    return rows


def _annualized_growth(values: list[float], periods_per_year: int) -> float:
    if not values:
        return 0.0
    compounded = math.prod(1.0 + value for value in values)
    return compounded ** (periods_per_year / len(values)) - 1.0 if compounded > 0 else -1.0


def _max_drawdown(values: list[float]) -> float:
    wealth = 1.0
    peak = 1.0
    worst = 0.0
    for value in values:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        worst = min(worst, wealth / peak - 1.0)
    return worst


def _alpha_uncertainty(
    xs: list[list[float]], residuals: list[float], daily_alpha: float,
    periods_per_year: int,
) -> dict[str, Any]:
    """Newey-West uncertainty for the intercept of the fitted daily-return model."""
    design = np.column_stack((np.ones(len(residuals)), np.asarray(xs, dtype=float).T))
    scores = design * np.asarray(residuals, dtype=float)[:, None]
    bread = np.linalg.inv(design.T @ design)
    lag_count = min(len(residuals) - 1, max(1, int(4 * (len(residuals) / 100) ** (2 / 9))))
    meat = scores.T @ scores
    for lag in range(1, lag_count + 1):
        covariance = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (lag_count + 1)) * (covariance + covariance.T)
    parameter_count = design.shape[1]
    estimate = bread @ meat @ bread * len(residuals) / (len(residuals) - parameter_count)
    daily_standard_error = math.sqrt(max(0.0, float(estimate[0, 0])))
    lower_daily, upper_daily = (
        daily_alpha - 1.96 * daily_standard_error,
        daily_alpha + 1.96 * daily_standard_error,
    )

    def annualize(value: float) -> float:
        return (1.0 + value) ** periods_per_year - 1.0 if value > -1 else -1.0

    interval = [annualize(lower_daily), annualize(upper_daily)]
    return {
        "method": "newey_west_hac_bartlett",
        "lag_count": lag_count,
        "confidence_level": 0.95,
        "daily_standard_error": daily_standard_error,
        "annualized_standard_error_delta": (
            periods_per_year * (1.0 + daily_alpha) ** (periods_per_year - 1)
            * daily_standard_error
        ),
        "annualized_interval": interval,
        "t_statistic": daily_alpha / daily_standard_error if daily_standard_error else None,
        "interval_includes_zero": interval[0] <= 0 <= interval[1],
    }


def compile_return_covariance(
    *,
    price_series: Mapping[str, Mapping[str, float]],
    as_of: str,
    min_returns: int = 120,
    lookback_returns: int = 756,
    annualization_factor: int = 252,
    diagonal_shrinkage: float = 0.25,
) -> dict[str, Any]:
    """Compile one point-in-time covariance contract from aligned prices."""
    epoch = canonical_timestamp(as_of, "return covariance as_of")
    entity_ids = tuple(map(str, price_series))
    if not entity_ids:
        raise ValueError("return covariance requires at least one entity")
    if min_returns < 2 or lookback_returns < min_returns:
        raise ValueError("return covariance lookback must cover min_returns >= 2")
    if annualization_factor < 1:
        raise ValueError("return covariance annualization_factor must be positive")
    shrinkage = require_finite(diagonal_shrinkage, "diagonal_shrinkage")
    if not 0 <= shrinkage <= 1:
        raise ValueError("diagonal_shrinkage must be in [0, 1]")
    clean: dict[str, dict[str, float]] = {}
    for entity_id in entity_ids:
        rows = {
            str(day): require_finite(value, f"{entity_id} price")
            for day, value in price_series[entity_id].items()
        }
        if any(value <= 0 for value in rows.values()):
            raise ValueError(f"{entity_id} prices must be positive")
        clean[entity_id] = rows
    common_days = sorted(set.intersection(*(set(clean[row]) for row in entity_ids)))
    if len(common_days) < min_returns + 1:
        raise ValueError(
            f"return covariance has {max(0, len(common_days) - 1)} aligned returns; "
            f"requires {min_returns}"
        )
    common_days = common_days[-(lookback_returns + 1):]
    returns = np.array([
        [clean[entity_id][right] / clean[entity_id][left] - 1.0
         for left, right in zip(common_days, common_days[1:])]
        for entity_id in entity_ids
    ], dtype=float)
    sample = np.atleast_2d(np.cov(returns, ddof=1))
    covariance = annualization_factor * (
        (1.0 - shrinkage) * sample + shrinkage * np.diag(np.diag(sample))
    )
    if not np.isfinite(covariance).all():
        raise ValueError("return covariance contains a non-finite value")
    volatilities = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    denominator = np.outer(volatilities, volatilities)
    correlations = np.divide(
        covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0,
    )
    np.fill_diagonal(correlations, 1.0)
    min_eigenvalue = float(np.linalg.eigvalsh(covariance).min())
    if min_eigenvalue < -1e-12:
        raise ValueError("shrunk return covariance is not positive semidefinite")
    body = {
        "schema": RETURN_COVARIANCE_SCHEMA,
        "as_of": epoch,
        "entity_ids": list(entity_ids),
        "estimator": "sample_daily_simple_return_covariance_with_fixed_diagonal_shrinkage",
        "annualization_factor": annualization_factor,
        "diagonal_shrinkage": shrinkage,
        "return_count": returns.shape[1],
        "window_start": common_days[0],
        "window_end": common_days[-1],
        "annualized_volatility": {
            entity_id: float(volatilities[index])
            for index, entity_id in enumerate(entity_ids)
        },
        "correlations": {
            left: {
                right: float(correlations[i, j])
                for j, right in enumerate(entity_ids) if i != j
            }
            for i, left in enumerate(entity_ids)
        },
        "covariance_matrix": covariance.tolist(),
        "covariance_min_eigenvalue": min_eigenvalue,
        "historical_mean_used_as_forecast": False,
        "expected_return_claim": False,
    }
    return {**body, "return_covariance_sha256": stable_sha256(body)}


def analyze_factor_exposure(
    *,
    analysis_id: str,
    candidate_entity_id: str,
    factors: Iterable[FactorDefinition],
    price_points: Iterable[PricePoint],
    as_of: str,
    risk_free_rate: float = 0.0,
    alpha_persistence_weight: float = 0.0,
    periods_per_year: int = 252,
    min_observations: int = 120,
) -> dict[str, Any]:
    """Estimate one candidate against a declared factor benchmark."""
    candidate = require_text(candidate_entity_id, "candidate_entity_id")
    factor_rows = tuple(factors)
    if not factor_rows or len({row.factor_id for row in factor_rows}) != len(factor_rows):
        raise ValueError("factor definitions must be nonempty and unique")
    persistence = require_finite(alpha_persistence_weight, "alpha_persistence_weight")
    if not 0 <= persistence <= 1:
        raise ValueError("alpha_persistence_weight must be in [0, 1]")
    epoch = canonical_timestamp(as_of, "factor as_of")
    cutoff = timestamp_key(epoch)
    points = tuple(
        row for row in price_points
        if timestamp_key(row.available_at) <= cutoff and timestamp_key(row.observed_at) <= cutoff
    )
    candidate_returns = _returns(_series(points, candidate))
    factor_returns: dict[str, dict[tuple[str, str], float]] = {}
    used_points: dict[str, PricePoint] = {}
    for factor in factor_rows:
        long_returns = _returns(_series(points, factor.long_entity_id))
        if factor.short_entity_id:
            short_returns = _returns(_series(points, factor.short_entity_id))
            dates = set(long_returns) & set(short_returns)
            factor_returns[factor.factor_id] = {
                day: long_returns[day][0] - short_returns[day][0] for day in dates
            }
            for day in dates:
                for point in (*long_returns[day][1], *short_returns[day][1]):
                    used_points[point.observation_id] = point
        else:
            factor_returns[factor.factor_id] = {day: value[0] for day, value in long_returns.items()}
            for _day, (_value, pair) in long_returns.items():
                for point in pair:
                    used_points[point.observation_id] = point
    dates = sorted(set(candidate_returns).intersection(*(set(rows) for rows in factor_returns.values())))
    if len(dates) < max(min_observations, len(factor_rows) + 3):
        raise InsufficientFactorHistoryError(
            f"factor analysis has {len(dates)} aligned returns; requires at least {max(min_observations, len(factor_rows) + 3)}"
        )
    ys = [candidate_returns[day][0] for day in dates]
    xs = [[factor_returns[factor.factor_id][day] for day in dates] for factor in factor_rows]
    fit = ols_multichannel_r2(xs, ys, [factor.factor_id for factor in factor_rows])
    if fit.get("error"):
        raise ValueError(f"factor regression failed: {fit['error']}")
    coefficients = [float(value) for value in fit["beta_exact"]]
    fitted = [coefficients[0] + sum(coefficients[index + 1] * xs[index][row] for index in range(len(xs))) for row in range(len(ys))]
    residuals = [actual - predicted for actual, predicted in zip(ys, fitted)]
    daily_alpha = coefficients[0]
    historical_alpha = (1.0 + daily_alpha) ** periods_per_year - 1.0 if daily_alpha > -1 else -1.0
    alpha_uncertainty = _alpha_uncertainty(xs, residuals, daily_alpha, periods_per_year)
    tracking_error = stdev(residuals) * math.sqrt(periods_per_year) if len(residuals) > 1 else 0.0
    information_ratio = historical_alpha / tracking_error if tracking_error else None
    expected_contributions = {
        factor.factor_id: coefficients[index + 1] * factor.expected_annual_premium
        for index, factor in enumerate(factor_rows)
    }
    expected_without_alpha = require_finite(risk_free_rate, "risk_free_rate") + sum(expected_contributions.values())
    expected_with_shrunk_alpha = expected_without_alpha + persistence * historical_alpha
    for day in dates:
        for point in candidate_returns[day][1]:
            used_points[point.observation_id] = point
    observed_start = min(used_points.values(), key=lambda row: row.observed_at).observed_at
    observed_end = max(used_points.values(), key=lambda row: row.observed_at).observed_at
    available_at = max(used_points.values(), key=lambda row: timestamp_key(row.available_at)).available_at
    body: dict[str, Any] = {
        "schema": FACTOR_ANALYSIS_SCHEMA,
        "analysis_id": require_text(analysis_id, "analysis_id"),
        "candidate_entity_id": candidate,
        "as_of": epoch,
        "observed_period": {"start": observed_start, "end": observed_end},
        "available_at": available_at,
        "observation_count": len(dates),
        "sample_adequacy": {
            "minimum_observations": max(min_observations, len(factor_rows) + 3),
            "observations_per_parameter": len(dates) / (len(factor_rows) + 1),
            "full_trading_year": len(dates) >= periods_per_year,
            "status": "full_year" if len(dates) >= periods_per_year else "partial_year",
        },
        "temporal_alignment": {
            "join_identity": "exact_period_start_and_end",
            "candidate_return_count": len(candidate_returns),
            "factor_return_counts": {
                factor.factor_id: len(factor_returns[factor.factor_id]) for factor in factor_rows
            },
            "aligned_return_count": len(dates),
            "candidate_coverage": len(dates) / len(candidate_returns),
            "factor_coverage": {
                factor.factor_id: len(dates) / len(factor_returns[factor.factor_id])
                for factor in factor_rows
            },
        },
        "periods_per_year": periods_per_year,
        "factors": [row.to_dict() for row in factor_rows],
        "factor_basis_sha256": stable_sha256([row.to_dict() for row in factor_rows]),
        "coefficients": {
            "daily_intercept": daily_alpha,
            "betas": {factor.factor_id: coefficients[index + 1] for index, factor in enumerate(factor_rows)},
        },
        "fit": {
            "r2": fit["r2"], "adjusted_r2": fit["r2_adj"],
            "leave_one_out_r2": fit["r2_loo"], "residual_rmse_daily": fit["residual_rmse"],
        },
        "historical": {
            "candidate_annualized_return": _annualized_growth(ys, periods_per_year),
            "candidate_annualized_volatility": stdev(ys) * math.sqrt(periods_per_year),
            "maximum_drawdown": _max_drawdown(ys),
            "residual_alpha_annualized": historical_alpha,
            "residual_alpha_uncertainty": alpha_uncertainty,
            "residual_tracking_error": tracking_error,
            "information_ratio": information_ratio,
        },
        "assumption_implied": {
            "risk_free_rate": risk_free_rate,
            "factor_contributions": expected_contributions,
            "return_without_residual_alpha": expected_without_alpha,
            "alpha_persistence_weight": persistence,
            "return_with_shrunk_residual_alpha": expected_with_shrunk_alpha,
        },
        "source_observation_ids": sorted(used_points),
        "source_refs": sorted({row.source_ref for row in used_points.values()}),
        "use_boundary": (
            "Residual alpha is conditional on benchmark choice and the observed sample. "
            "A fund valuation claim additionally requires holdings or aggregate fundamental valuation evidence."
        ),
    }
    return {**body, "analysis_sha256": stable_sha256(body)}


def compile_historical_factor_control(
    *, analysis_id: str, candidate_entity_id: str,
    factors: Iterable[FactorDefinition], price_points: Iterable[PricePoint],
    evidence_as_of: str, calibration_end: str,
    settlement_start: str, settlement_end: str,
    min_observations: int = 120, lookback_observations: int = 252,
    round_trip_cost_bps: float = 0.0,
) -> dict[str, Any]:
    """Fit pre-event betas and settle one later return against the frozen model."""

    candidate = require_text(candidate_entity_id, "candidate_entity_id")
    factor_rows = tuple(factors)
    if not factor_rows or len({row.factor_id for row in factor_rows}) != len(factor_rows):
        raise ValueError("historical factor control requires unique factors")
    if lookback_observations < min_observations or min_observations < len(factor_rows) + 3:
        raise ValueError("historical factor-control lookback is too short")
    cost = require_finite(round_trip_cost_bps, "round_trip_cost_bps") / 10_000.0
    if cost < 0:
        raise ValueError("round_trip_cost_bps cannot be negative")
    evidence_epoch = canonical_timestamp(evidence_as_of, "factor-control evidence_as_of")
    calibration_epoch = canonical_timestamp(calibration_end, "factor-control calibration_end")
    start_epoch = canonical_timestamp(settlement_start, "factor-control settlement_start")
    end_epoch = canonical_timestamp(settlement_end, "factor-control settlement_end")
    if not calibration_epoch < start_epoch < end_epoch:
        raise ValueError("factor-control epochs must be calibration < start < end")
    points = tuple(
        row for row in price_points
        if timestamp_key(row.available_at) <= timestamp_key(evidence_epoch)
    )
    candidate_returns = _returns(_series(points, candidate))
    factor_returns: dict[str, dict[tuple[str, str], float]] = {}
    factor_pairs: dict[str, dict[tuple[str, str], tuple[PricePoint, ...]]] = {}
    for factor in factor_rows:
        long_returns = _returns(_series(points, factor.long_entity_id))
        short_returns = (
            _returns(_series(points, factor.short_entity_id))
            if factor.short_entity_id else {}
        )
        dates = set(long_returns) & set(short_returns) if short_returns else set(long_returns)
        factor_returns[factor.factor_id] = {
            day: long_returns[day][0] - (short_returns[day][0] if short_returns else 0.0)
            for day in dates
        }
        factor_pairs[factor.factor_id] = {
            day: (*long_returns[day][1], *(short_returns[day][1] if short_returns else ()))
            for day in dates
        }
    aligned = sorted(
        set(candidate_returns).intersection(*(set(rows) for rows in factor_returns.values()))
    )
    calibration = [
        day for day in aligned
        if timestamp_key(candidate_returns[day][1][1].observed_at)
        < timestamp_key(calibration_epoch)
    ][-lookback_observations:]
    if len(calibration) < min_observations:
        raise InsufficientFactorHistoryError(
            f"historical factor control has {len(calibration)} pre-event returns; "
            f"requires {min_observations}"
        )
    ys = [candidate_returns[day][0] for day in calibration]
    xs = [[factor_returns[factor.factor_id][day] for day in calibration] for factor in factor_rows]
    fit = ols_multichannel_r2(xs, ys, [factor.factor_id for factor in factor_rows])
    if fit.get("error"):
        raise ValueError(f"historical factor regression failed: {fit['error']}")
    coefficients = [float(value) for value in fit["beta_exact"]]
    settlement = [
        day for day in aligned
        if timestamp_key(candidate_returns[day][1][0].observed_at) >= timestamp_key(start_epoch)
        and timestamp_key(candidate_returns[day][1][1].observed_at) <= timestamp_key(end_epoch)
    ]
    if (
        not settlement
        or candidate_returns[settlement[0]][1][0].observed_at[:10] != start_epoch[:10]
        or candidate_returns[settlement[-1]][1][1].observed_at[:10] != end_epoch[:10]
        or any(left[1] != right[0] for left, right in zip(settlement, settlement[1:]))
    ):
        raise InsufficientFactorHistoryError(
            "factor-control settlement window is not continuously aligned"
        )
    expected_daily = [
        coefficients[0] + sum(
            coefficients[index + 1] * factor_returns[factor.factor_id][day]
            for index, factor in enumerate(factor_rows)
        )
        for day in settlement
    ]
    if any(value <= -1 for value in expected_daily):
        raise ValueError("factor-control expected daily wealth is nonpositive")
    actual_wealth = math.prod(1.0 + candidate_returns[day][0] for day in settlement)
    expected_wealth = math.prod(1.0 + value for value in expected_daily)
    used_points: dict[str, PricePoint] = {}
    for day in (*calibration, *settlement):
        for point in candidate_returns[day][1]:
            used_points[point.observation_id] = point
        for factor in factor_rows:
            for point in factor_pairs[factor.factor_id][day]:
                used_points[point.observation_id] = point
    factor_window_returns = {
        factor.factor_id: math.prod(
            1.0 + factor_returns[factor.factor_id][day] for day in settlement
        ) - 1.0
        for factor in factor_rows
    }
    body = {
        "schema": HISTORICAL_FACTOR_CONTROL_SCHEMA,
        "analysis_id": require_text(analysis_id, "analysis_id"),
        "candidate_entity_id": candidate,
        "evidence_as_of": evidence_epoch,
        "calibration": {
            "end_exclusive": calibration_epoch,
            "lookback_observations": lookback_observations,
            "observation_count": len(calibration),
            "window_start": calibration[0][0],
            "window_end": calibration[-1][1],
        },
        "settlement": {
            "start": start_epoch,
            "end": end_epoch,
            "return_count": len(settlement),
        },
        "factors": [factor.to_dict() for factor in factor_rows],
        "coefficients": {
            "daily_intercept": coefficients[0],
            "betas": {
                factor.factor_id: coefficients[index + 1]
                for index, factor in enumerate(factor_rows)
            },
        },
        "fit": {
            "r2": fit["r2"], "adjusted_r2": fit["r2_adj"],
            "leave_one_out_r2": fit["r2_loo"],
            "residual_rmse_daily": fit["residual_rmse"],
        },
        "realized": {
            "candidate_return": actual_wealth - 1.0,
            "factor_window_returns": factor_window_returns,
            "model_expected_return": expected_wealth - 1.0,
            "factor_controlled_simple_return_after_cost": actual_wealth - expected_wealth - cost,
            "factor_controlled_log_return_after_cost": math.log(actual_wealth) - math.log(expected_wealth) - cost,
        },
        "source_observation_count": len(used_points),
        "source_observation_ids_sha256": stable_sha256(sorted(used_points)),
        "source_refs": sorted({point.source_ref for point in used_points.values()}),
        "use_boundary": (
            "Betas use only observations before the event cutoff, while the cached price history "
            "was retrieved later and therefore supports retrospective diagnostics only."
        ),
    }
    return {**body, "factor_control_sha256": stable_sha256(body)}


__all__ = [
    "FACTOR_ANALYSIS_SCHEMA", "HISTORICAL_FACTOR_CONTROL_SCHEMA",
    "RETURN_COVARIANCE_SCHEMA", "FactorDefinition", "PricePoint",
    "analyze_factor_exposure", "compile_historical_factor_control",
    "compile_return_covariance", "load_price_points",
]
