"""Past-only selection of a constrained minimum-variance risk model."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite


PORTFOLIO_RISK_CHALLENGER_SCHEMA = "jaggedthoughts-portfolio-risk-challenger-v1"
DEFAULT_RIDGE_GRID = (0.0, 0.01, 0.05, 0.25, 1.0, 4.0)


def minimum_variance_weights(
    covariance: Sequence[Sequence[float]], entity_ids: Sequence[str], *,
    gross_weight: float, maximum_weight: float,
) -> dict[str, float]:
    """Solve the existing long-only, capped minimum-variance decision."""
    identities = tuple(map(str, entity_ids))
    matrix = np.asarray(covariance, dtype=float)
    if matrix.shape != (len(identities), len(identities)) or not np.isfinite(matrix).all():
        raise ValueError("minimum-variance covariance shape or values are invalid")
    gross = require_finite(gross_weight, "gross_weight")
    maximum = require_finite(maximum_weight, "maximum_weight")
    target = min(gross, len(identities) * maximum)
    if not identities or target <= 0 or maximum <= 0:
        raise ValueError("minimum-variance allocation requires a positive feasible universe")
    initial = np.full(len(identities), target / len(identities))
    result = minimize(
        lambda weights: float(weights @ matrix @ weights),
        initial,
        jac=lambda weights: 2.0 * matrix @ weights,
        bounds=[(0.0, maximum)] * len(identities),
        constraints={"type": "eq", "fun": lambda weights: float(weights.sum() - target)},
        method="SLSQP",
        options={"ftol": 1e-12, "maxiter": 500},
    )
    if not result.success or abs(float(result.x.sum()) - target) > 1e-8:
        raise ValueError(f"minimum-variance optimizer failed: {result.message}")
    return {
        entity_id: max(0.0, float(weight))
        for entity_id, weight in zip(identities, result.x)
    }


def _ridge_covariance(returns: np.ndarray, penalty_ratio: float) -> np.ndarray:
    sample = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1))
    scale = float(np.trace(sample) / sample.shape[0])
    return sample + penalty_ratio * scale * np.eye(sample.shape[0])


def compile_walk_forward_ridge_risk_challenger(
    *,
    price_series: Mapping[str, Mapping[str, float]],
    as_of: str,
    source_risk_model_sha256: str,
    gross_weight: float,
    maximum_weight: float,
    ridge_grid: Sequence[float] = DEFAULT_RIDGE_GRID,
    minimum_training_returns: int = 252,
    validation_returns: int = 63,
    lookback_returns: int = 756,
) -> dict[str, Any]:
    """Select ridge strength on chronological portfolio risk, then refit once."""
    epoch = canonical_timestamp(as_of, "risk challenger as_of")
    identities = tuple(sorted(map(str, price_series)))
    if len(identities) < 2:
        raise ValueError("risk challenger requires at least two assets")
    if len(source_risk_model_sha256) != 64:
        raise ValueError("risk challenger requires a source risk-model hash")
    if minimum_training_returns < 2 or validation_returns < 2:
        raise ValueError("risk challenger train and validation windows are too short")
    penalties = tuple(sorted({
        require_finite(value, "ridge penalty") for value in ridge_grid
    }))
    if not penalties or penalties[0] < 0:
        raise ValueError("risk challenger ridge penalties must be nonnegative")

    clean = {
        entity_id: {
            str(day): require_finite(value, f"{entity_id} price")
            for day, value in price_series[entity_id].items()
            if str(day) <= epoch[:10]
        }
        for entity_id in identities
    }
    if any(value <= 0 for rows in clean.values() for value in rows.values()):
        raise ValueError("risk challenger prices must be positive")
    common_days = sorted(set.intersection(*(set(clean[row]) for row in identities)))
    common_days = common_days[-(lookback_returns + 1):]
    if len(common_days) - 1 < minimum_training_returns + validation_returns:
        raise ValueError(
            "risk challenger requires enough aligned returns for a past-only train/validation split"
        )
    returns = np.asarray([
        [clean[entity_id][right] / clean[entity_id][left] - 1.0 for entity_id in identities]
        for left, right in zip(common_days, common_days[1:])
    ], dtype=float)

    fold_ends = list(range(
        minimum_training_returns + validation_returns,
        len(returns) + 1,
        validation_returns,
    ))
    scores = []
    for penalty in penalties:
        fold_scores = []
        for end in fold_ends:
            start = end - validation_returns
            train = returns[:start]
            validation = returns[start:end]
            covariance = _ridge_covariance(train, penalty)
            weights = minimum_variance_weights(
                covariance, identities, gross_weight=gross_weight,
                maximum_weight=maximum_weight,
            )
            vector = np.asarray([weights[row] for row in identities])
            fold_scores.append(float(np.var(validation @ vector, ddof=1)))
        scores.append({
            "ridge_penalty_ratio": penalty,
            "mean_validation_variance": float(np.mean(fold_scores)),
            "fold_validation_variances": fold_scores,
        })
    selected = min(scores, key=lambda row: (
        row["mean_validation_variance"], row["ridge_penalty_ratio"],
    ))
    final_covariance = _ridge_covariance(returns, selected["ridge_penalty_ratio"])
    weights = minimum_variance_weights(
        final_covariance, identities, gross_weight=gross_weight,
        maximum_weight=maximum_weight,
    )
    body = {
        "schema": PORTFOLIO_RISK_CHALLENGER_SCHEMA,
        "as_of": epoch,
        "method": "chronological_validation_selected_ridge_minimum_variance",
        "entity_ids": list(identities),
        "input_window": {
            "start": common_days[0], "end": common_days[-1],
            "return_count": len(returns),
            "minimum_training_returns": minimum_training_returns,
            "validation_returns": validation_returns,
            "fold_count": len(fold_ends),
        },
        "price_matrix_sha256": stable_sha256([
            (day, *(clean[entity_id][day] for entity_id in identities))
            for day in common_days
        ]),
        "source_risk_model_sha256": source_risk_model_sha256,
        "selection_objective": "mean_chronological_holdout_portfolio_variance",
        "ridge_grid": list(penalties),
        "validation_scores": scores,
        "selected_ridge_penalty_ratio": selected["ridge_penalty_ratio"],
        "weights": weights,
        "constraints": {
            "long_only": True,
            "gross_weight": require_finite(gross_weight, "gross_weight"),
            "maximum_weight": require_finite(maximum_weight, "maximum_weight"),
        },
        "method_lineage": {
            "research_anchors": ["doi:10.3386/w34861", "doi:10.3386/w32004"],
            "implemented_scope": "decision-objective selection of one ridge risk model",
            "excluded_scopes": [
                "end_to_end_return_forecasting", "universal_portfolio_shrinkage",
                "expected_return_or_alpha_estimation",
            ],
        },
        "expected_return_claim": False,
        "historical_mean_used_as_forecast": False,
        "evaluation_role": "diagnostic_risk_comparator",
        "promotion_eligible_under_current_score_contract": False,
        "capital_authority": False,
    }
    return {**body, "risk_challenger_sha256": stable_sha256(body)}
