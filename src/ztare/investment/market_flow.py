"""Lagrangian/probability-current market-flow experiment adapter.

This is an isolated world-model leaf.  It estimates a one-dimensional
Fokker--Planck current from trailing returns, passes that current through a
field-response action derived by the shared ZTARE Lagrangian primitive, and
compares the frozen family with cheap controls.  Retrieval-time price history
may be used for retrospective diagnostics, but only provider-vintage or
prospectively collected episodes can earn a promotion-eligible result.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import paired_permutation_test
from ztare.fit.lagrangian_derivation import derive_from_action, to_jsonable
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .factor_analysis import PricePoint, load_price_points


MARKET_FLOW_PROFILE_SCHEMA = "jaggedthoughts-market-flow-experiment-profile-v1"
MARKET_FLOW_RESULT_SCHEMA = "jaggedthoughts-market-flow-backtest-v1"
MARKET_FLOW_IMPLEMENTATION_ID = "probability-current-lagrangian-1.2"
_MODES = {"point_in_time", "retrospective_retrieval_diagnostic"}


@dataclass(frozen=True, slots=True)
class FlowEstimate:
    state: float
    current_velocity: float
    density: float
    predicted_density_change: float
    actual_density_change: float
    mean_return: float
    return_scale: float
    source_refs: tuple[str, ...]
    observation_ids: tuple[str, ...]


def _load_profile(path: str | Path) -> Mapping[str, Any]:
    source = Path(path).expanduser().resolve()
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != MARKET_FLOW_PROFILE_SCHEMA:
        raise ValueError(f"market-flow profile schema must be {MARKET_FLOW_PROFILE_SCHEMA}")
    return payload


def _series(points: Iterable[PricePoint], entity_id: str) -> list[PricePoint]:
    by_date: dict[str, PricePoint] = {}
    for row in points:
        if row.entity_id != entity_id:
            continue
        current = by_date.get(row.date_key)
        if current is None or (row.available_at, row.observation_id) > (
            current.available_at, current.observation_id,
        ):
            by_date[row.date_key] = row
    return [by_date[key] for key in sorted(by_date)]


def _returns(prices: list[PricePoint]) -> list[float]:
    return [math.log(current.value / previous.value) for previous, current in zip(prices, prices[1:])]


def _bin_index(value: float, *, lower: float, upper: float, bin_count: int) -> int:
    width = (upper - lower) / bin_count
    return min(bin_count - 1, max(0, int((min(upper - 1e-12, max(lower, value)) - lower) / width)))


def _density(values: list[float], *, lower: float, upper: float, bin_count: int) -> list[float]:
    width = (upper - lower) / bin_count
    counts = [0] * bin_count
    for value in values:
        counts[_bin_index(value, lower=lower, upper=upper, bin_count=bin_count)] += 1
    return [count / (len(values) * width) for count in counts]


def _derivative(values: list[float], width: float) -> list[float]:
    if len(values) < 3:
        raise ValueError("probability-current derivative needs at least three bins")
    return [
        (values[1] - values[0]) / width if index == 0
        else (values[-1] - values[-2]) / width if index == len(values) - 1
        else (values[index + 1] - values[index - 1]) / (2 * width)
        for index in range(len(values))
    ]


def estimate_probability_current(
    trailing_returns: list[float],
    next_return: float,
    *,
    price_points: list[PricePoint],
    bin_count: int,
    state_clip: float,
) -> FlowEstimate:
    """Estimate J=mu*p-d(Dp)/dx and the local continuity-equation residual."""
    if len(trailing_returns) < max(40, bin_count * 4):
        raise ValueError("market-flow estimation window is too short")
    center = mean(trailing_returns)
    scale = pstdev(trailing_returns)
    if scale <= 1e-12:
        raise ValueError("market-flow return window has zero dispersion")
    states = [min(state_clip, max(-state_clip, (value - center) / scale)) for value in trailing_returns]
    lower, upper = -state_clip, state_clip
    width = (upper - lower) / bin_count
    density = _density(states, lower=lower, upper=upper, bin_count=bin_count)
    drift_bins: list[list[float]] = [[] for _ in range(bin_count)]
    for left, right in zip(states, states[1:]):
        drift_bins[_bin_index(left, lower=lower, upper=upper, bin_count=bin_count)].append(right - left)
    drift = [mean(rows) if rows else 0.0 for rows in drift_bins]
    diffusion = [0.5 * mean(value * value for value in rows) if rows else 0.0 for rows in drift_bins]
    dp = [diffusion[index] * density[index] for index in range(bin_count)]
    current = [drift[index] * density[index] - value for index, value in enumerate(_derivative(dp, width))]
    divergence = _derivative(current, width)
    state = states[-1]
    index = _bin_index(state, lower=lower, upper=upper, bin_count=bin_count)
    velocity = current[index] / max(density[index], 1.0 / (len(states) * width))
    velocity = min(3.0, max(-3.0, velocity))
    next_state = min(state_clip, max(-state_clip, (next_return - center) / scale))
    shifted = [*states[1:], next_state]
    density_after = _density(shifted, lower=lower, upper=upper, bin_count=bin_count)
    return FlowEstimate(
        state=state,
        current_velocity=velocity,
        density=density[index],
        # The observed target is a one-row update to an n-row empirical
        # density window, so its continuity prediction has the same 1/n scale.
        predicted_density_change=-divergence[index] / len(states),
        actual_density_change=density_after[index] - density[index],
        mean_return=center,
        return_scale=scale,
        source_refs=tuple(sorted({row.source_ref for row in price_points})),
        observation_ids=tuple(row.observation_id for row in price_points),
    )


def _field_response(current: float, *, mass_squared: float, quartic: float) -> float:
    """Unique real minimizer of lam*q^3 + m2*q - current = 0 for m2>0, lam>=0."""
    m2 = require_finite(mass_squared, "market-flow mass_squared")
    lam = require_finite(quartic, "market-flow quartic")
    if m2 <= 0 or lam < 0:
        raise ValueError("market-flow response requires mass_squared>0 and quartic>=0")
    if lam == 0:
        return current / m2
    q = current / m2
    for _ in range(30):
        residual = lam * q ** 3 + m2 * q - current
        derivative = 3 * lam * q * q + m2
        updated = q - residual / derivative
        if abs(updated - q) < 1e-12:
            return updated
        q = updated
    return q


def _episode_feature(
    prices: list[PricePoint], returns: list[float], index: int, *,
    lookback: int, bin_count: int, state_clip: float,
) -> FlowEstimate:
    trailing = returns[index - lookback:index]
    # The feature window ends at issuance; the next price is outcome-only.
    evidence_prices = prices[index - lookback:index + 1]
    return estimate_probability_current(
        trailing, returns[index], price_points=evidence_prices,
        bin_count=bin_count, state_clip=state_clip,
    )


def _fit_response_parameters(
    examples: Iterable[tuple[FlowEstimate, float]], *,
    mass_grid: Iterable[float], quartic_grid: Iterable[float],
) -> tuple[float, float, float]:
    rows = tuple(examples)
    if not rows:
        raise ValueError("market-flow parameter fit requires training examples")
    candidates: list[tuple[float, float, float]] = []
    for m2 in mass_grid:
        for lam in quartic_grid:
            errors = []
            for flow, actual_return in rows:
                predicted_state = _field_response(flow.current_velocity, mass_squared=m2, quartic=lam)
                prediction = flow.mean_return + flow.return_scale * predicted_state
                errors.append(abs(prediction - actual_return))
            candidates.append((mean(errors), float(m2), float(lam)))
    return min(candidates, key=lambda row: (row[0], row[1], row[2]))


def _model_metrics(rows: list[dict[str, Any]], model_id: str, transaction_cost_bps: float) -> dict[str, Any]:
    errors: list[float] = []
    directions: list[float] = []
    net_returns: list[float] = []
    for row in rows:
        prediction = float(row["predictions"][model_id])
        actual = float(row["actual_return"])
        sign = 1 if prediction > 0 else -1 if prediction < 0 else 0
        errors.append(abs(prediction - actual))
        directions.append(float((prediction > 0) == (actual > 0)) if prediction != 0 and actual != 0 else float(prediction == actual))
        net_returns.append(sign * actual - abs(sign) * transaction_cost_bps / 10_000)
    return {
        "model_id": model_id,
        "episode_count": len(rows),
        "mean_absolute_return_error": mean(errors),
        "directional_accuracy": mean(directions),
        "mean_net_directional_return": mean(net_returns),
        "absolute_return_errors": errors,
        "net_directional_returns": net_returns,
    }


def compile_market_flow_backtest(
    profile_path: str | Path, *, workspace: str | Path
) -> dict[str, Any]:
    """Compile one frozen-family backtest with chronology and control receipts."""
    profile = _load_profile(profile_path)
    root = Path(workspace).expanduser().resolve()
    raw_as_of = profile.get("as_of")
    if raw_as_of == "latest_source_run":
        run_path = root / "data" / "latest_source_run.json"
        try:
            latest_run = json.loads(run_path.read_text(encoding="utf-8"))
            raw_as_of = latest_run["as_of"]
        except (KeyError, OSError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("market-flow latest_source_run requires a completed source refresh") from error
    as_of = canonical_timestamp(raw_as_of, "market-flow as_of")
    mode = require_text(profile.get("mode"), "market-flow mode")
    if mode not in _MODES:
        raise ValueError(f"market-flow mode must be one of {sorted(_MODES)}")
    entity_ids = tuple(require_text(value, "market-flow entity") for value in profile.get("entity_ids", []))
    if not entity_ids:
        raise ValueError("market-flow profile requires entity_ids")
    lookback = int(profile.get("lookback", 252))
    bin_count = int(profile.get("bin_count", 9))
    state_clip = float(profile.get("state_clip", 4.0))
    evaluation_stride = int(profile.get("evaluation_stride", 5))
    training_fraction = float(profile.get("training_fraction", 0.60))
    transaction_cost_bps = float(profile.get("transaction_cost_bps", 5.0))
    if lookback < 60 or bin_count < 5 or evaluation_stride < 1 or not 0.4 <= training_fraction <= 0.8:
        raise ValueError("market-flow window, bins, stride, or training fraction is outside its bounded contract")
    points = load_price_points(
        root / "data" / "observations.csv", as_of=as_of,
        metric_id="adjusted_price",
    )
    mass_grid = tuple(float(value) for value in profile.get("mass_squared_grid", [0.5, 1.0, 2.0]))
    quartic_grid = tuple(float(value) for value in profile.get("quartic_grid", [0.0, 0.25, 1.0, 4.0]))
    if not mass_grid or not quartic_grid or any(value <= 0 for value in mass_grid) or any(value < 0 for value in quartic_grid):
        raise ValueError("market-flow parameter grids require positive mass values and nonnegative quartic values")
    episodes: list[dict[str, Any]] = []
    parameter_receipts: list[dict[str, Any]] = []
    source_availability: dict[tuple[str, str], dict[str, str]] = {}
    chronology_exclusions = 0
    for entity_id in entity_ids:
        prices = _series(points, entity_id)
        returns = _returns(prices)
        if len(returns) <= lookback + 20:
            continue
        split = max(lookback + 10, int(len(returns) * training_fraction))
        training_examples: list[tuple[FlowEstimate, float]] = []
        for index in range(lookback, split, evaluation_stride):
            issue_at = prices[index].observed_at
            used = prices[index - lookback:index + 1]
            if mode == "point_in_time" and any(timestamp_key(row.available_at) > timestamp_key(issue_at) for row in used):
                chronology_exclusions += 1
                continue
            if mode == "point_in_time":
                for row in used:
                    source_availability[(row.observation_id, issue_at)] = {
                        "source_id": row.observation_id,
                        "available_at": row.available_at,
                        "as_of": issue_at,
                    }
            flow = _episode_feature(
                prices, returns, index, lookback=lookback,
                bin_count=bin_count, state_clip=state_clip,
            )
            training_examples.append((flow, returns[index]))
        if not training_examples:
            continue
        fit_mae, mass_squared, quartic = _fit_response_parameters(
            training_examples, mass_grid=mass_grid, quartic_grid=quartic_grid,
        )
        parameter_receipts.append({
            "entity_id": entity_id, "trained_through": prices[split].observed_at,
            "training_example_count": len(training_examples), "training_mae": fit_mae,
            "mass_squared": mass_squared, "quartic": quartic,
        })
        for index in range(split, len(returns), evaluation_stride):
            issue_at = prices[index].observed_at
            end_at = prices[index + 1].observed_at
            used = prices[index - lookback:index + 2]
            chronology_ok = all(timestamp_key(row.available_at) <= timestamp_key(issue_at) for row in used[:-1])
            if mode == "point_in_time" and not chronology_ok:
                chronology_exclusions += 1
                continue
            if mode == "point_in_time":
                for row in used[:-1]:
                    source_availability[(row.observation_id, issue_at)] = {
                        "source_id": row.observation_id,
                        "available_at": row.available_at,
                        "as_of": issue_at,
                    }
            flow = _episode_feature(
                prices, returns, index, lookback=lookback,
                bin_count=bin_count, state_clip=state_clip,
            )
            lagrangian_state = _field_response(
                flow.current_velocity, mass_squared=mass_squared, quartic=quartic,
            )
            lagrangian_prediction = flow.mean_return + flow.return_scale * lagrangian_state
            episodes.append({
                "episode_id": f"{entity_id}:{issue_at[:10]}:{end_at[:10]}",
                "entity_id": entity_id, "issued_at": issue_at, "end_at": end_at,
                "chronology_ok": chronology_ok,
                "state": flow.state, "probability_current_velocity": flow.current_velocity,
                "predicted_density_change": flow.predicted_density_change,
                "actual_density_change": flow.actual_density_change,
                "actual_return": returns[index],
                "predictions": {
                    "lagrangian_probability_current": lagrangian_prediction,
                    "linear_probability_current": flow.mean_return + flow.return_scale * flow.current_velocity,
                    "momentum": returns[index - 1],
                    "mean_reversion": -returns[index - 1],
                    "unconditional_drift": flow.mean_return,
                    "zero_return": 0.0,
                },
                "source_refs": list(flow.source_refs),
                "observation_window": {
                    "count": len(flow.observation_ids),
                    "first_observation_id": flow.observation_ids[0],
                    "last_observation_id": flow.observation_ids[-1],
                    "observation_ids_sha256": stable_sha256(flow.observation_ids),
                },
            })
    if not episodes:
        raise ValueError(
            "market-flow profile produced no eligible evaluation episodes; point-in-time mode requires prospectively available prices"
        )
    model_ids = tuple(episodes[0]["predictions"])
    metrics = [_model_metrics(episodes, model_id, transaction_cost_bps) for model_id in model_ids]
    candidate = next(row for row in metrics if row["model_id"] == "lagrangian_probability_current")
    controls = [row for row in metrics if row["model_id"] != candidate["model_id"]]
    best_error = min(controls, key=lambda row: row["mean_absolute_return_error"])
    best_economic = max(controls, key=lambda row: row["mean_net_directional_return"])
    linked_current_errors = [
        abs(float(row["predicted_density_change"]) - float(row["actual_density_change"]))
        for row in episodes
    ]
    linked_zero_errors = [abs(float(row["actual_density_change"])) for row in episodes]
    error_test = {
        **paired_permutation_test(
            candidate["absolute_return_errors"], best_error["absolute_return_errors"],
            n_perm=5000, seed=42,
        ),
        "delta_definition": (
            f"lagrangian_probability_current_absolute_return_error_minus_"
            f"{best_error['model_id']}_absolute_return_error"
        ),
        "lower_is_better": True,
    }
    economic_test = {
        **paired_permutation_test(
            candidate["net_directional_returns"], best_economic["net_directional_returns"],
            n_perm=5000, seed=43,
        ),
        "delta_definition": (
            f"lagrangian_probability_current_net_return_minus_"
            f"{best_economic['model_id']}_net_return"
        ),
        "lower_is_better": False,
    }
    linked_test = {
        **paired_permutation_test(
            linked_current_errors, linked_zero_errors, n_perm=5000, seed=44,
        ),
        "delta_definition": "probability_current_density_error_minus_zero_change_density_error",
        "lower_is_better": True,
    }
    derivation = derive_from_action(
        "q_dot**2/2 - (m2*q(t)**2/2 + lam*q(t)**4/4 - current*q(t))",
        ["q"], ["current"], "q(t)", symmetries=["time_translation"],
        param_names=["m2", "lam"],
    )
    derivation_receipt = {**to_jsonable(derivation), "triviality_kind": derivation.triviality_kind}
    beats_error = candidate["mean_absolute_return_error"] < best_error["mean_absolute_return_error"]
    beats_economic = candidate["mean_net_directional_return"] > best_economic["mean_net_directional_return"]
    beats_linked = mean(linked_current_errors) < mean(linked_zero_errors)
    integrity = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay",
        generation_processes=("deterministic",),
        source_availability_rows=tuple(source_availability.values()),
    )
    promotion_eligible = bool(integrity["backtest_evidence_eligible"])
    summary_metrics = [{key: value for key, value in row.items() if key not in {"absolute_return_errors", "net_directional_returns"}} for row in metrics]
    source_refs = sorted({ref for row in episodes for ref in row["source_refs"]})
    body: dict[str, Any] = {
        "schema": MARKET_FLOW_RESULT_SCHEMA,
        "implementation_id": MARKET_FLOW_IMPLEMENTATION_ID,
        "experiment_id": require_text(profile.get("experiment_id"), "market-flow experiment_id"),
        "as_of": as_of, "mode": mode, "authority": "experiment_only",
        "hypothesis": require_text(profile.get("hypothesis"), "market-flow hypothesis"),
        "kill_condition": require_text(profile.get("kill_condition"), "market-flow kill_condition"),
        "information_question": require_text(profile.get("information_question"), "market-flow information question"),
        "profile_template_sha256": stable_sha256(profile),
        "profile_sha256": stable_sha256({**profile, "as_of": as_of}),
        "episode_count": len(episodes), "chronology_exclusion_count": chronology_exclusions,
        "parameter_receipts": parameter_receipts,
        "lagrangian_derivation": derivation_receipt,
        "evaluation_integrity": integrity,
        "model_metrics": summary_metrics,
        "best_return_error_control": best_error["model_id"],
        "best_economic_control": best_economic["model_id"],
        "linked_observable": {
            "model_id": "probability_current_continuity",
            "control_id": "zero_density_change",
            "mean_absolute_density_error": mean(linked_current_errors),
            "control_mean_absolute_density_error": mean(linked_zero_errors),
            "paired_test": linked_test,
        },
        "paired_error_test": error_test, "paired_economic_test": economic_test,
        "beats_return_error_control": beats_error,
        "beats_economic_control": beats_economic,
        "beats_linked_observable_control": beats_linked,
        "diagnostic_edge": beats_error and beats_economic and beats_linked,
        "promotion_eligible": promotion_eligible,
        "screen_pass": promotion_eligible and beats_error and beats_economic and beats_linked,
        "paper_policy_authority": False,
        "source_refs": source_refs,
        "episodes_sha256": stable_sha256(episodes),
        "episodes": episodes,
        "use_boundary": (
            "Retrospective retrieval diagnostics can kill or refine the model family but cannot support a historical alpha claim. "
            "Promotion requires prospectively available episodes, linked-observable advantage, control advantage after costs, and later tournament settlement."
        ),
    }
    return {**body, "market_flow_backtest_sha256": stable_sha256(body)}


__all__ = [
    "MARKET_FLOW_PROFILE_SCHEMA",
    "MARKET_FLOW_RESULT_SCHEMA",
    "MARKET_FLOW_IMPLEMENTATION_ID",
    "FlowEstimate",
    "compile_market_flow_backtest",
    "estimate_probability_current",
]
