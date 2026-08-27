"""Persistent-company state transitions and their non-reversible current.

Companies retain identity while moving through a relative valuation x durable-
earnings grid.  The directed transition model and its reversible control use
the same prior rows; their held-out difference is the test for whether an
antisymmetric probability current carries incremental information.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
import csv
from datetime import date
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import spearman_rho

from .company_quality import (
    InsufficientCompanyHistoryError,
    compile_company_quality_from_observations,
    select_company_fundamentals,
)
from .contracts import MetricObservation, canonical_timestamp, require_finite, require_text


COMPANY_STATE_FLOW_PROFILE_SCHEMA = "jaggedthoughts-company-state-flow-profile-v1"
COMPANY_STATE_FLOW_EVIDENCE_SCHEMA = "jaggedthoughts-company-state-flow-evidence-v1"
STATE_IDS = ("low_value_low_durability", "low_value_high_durability",
             "high_value_low_durability", "high_value_high_durability")
_STATE_METRICS = {
    "revenue_fy", "operating_cash_flow_fy", "capital_expenditure_fy",
    "net_income_fy", "assets", "diluted_shares",
}


def _load_observations(path: Path) -> tuple[MetricObservation, ...]:
    rows: list[MetricObservation] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            try:
                rows.append(MetricObservation(
                    observation_id=str(raw["observation_id"]),
                    entity_id=str(raw["entity_id"]), metric_id=str(raw["metric_id"]),
                    value=float(raw["value"]), unit=str(raw["unit"]),
                    observed_at=str(raw["observed_at"]), available_at=str(raw["available_at"]),
                    source_ref=str(raw["source_ref"]),
                ))
            except (KeyError, TypeError, ValueError):
                continue
    return tuple(rows)


def _load_state_observations(
    path: Path, epochs: Sequence[str], *, source_as_of: str,
) -> tuple[MetricObservation, ...]:
    """Stream the observation store, retaining facts and one price per state epoch."""
    targets = tuple(sorted(str(epoch)[:10] for epoch in epochs))
    facts: dict[tuple[str, str, str], MetricObservation] = {}
    prices: dict[tuple[str, str], MetricObservation] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            try:
                metric = str(raw["metric_id"])
                available_at = str(raw["available_at"])
                observed_at = str(raw["observed_at"])
                if available_at > source_as_of or metric not in {*_STATE_METRICS, "price"}:
                    continue
                row = MetricObservation(
                    observation_id=str(raw["observation_id"]),
                    entity_id=str(raw["entity_id"]), metric_id=metric,
                    value=float(raw["value"]), unit=str(raw["unit"]),
                    observed_at=observed_at, available_at=available_at,
                    source_ref=str(raw["source_ref"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            if metric != "price":
                key = (row.entity_id, metric, observed_at)
                prior = facts.get(key)
                if prior is None or (available_at, row.observation_id) > (
                    prior.available_at, prior.observation_id,
                ):
                    facts[key] = row
                continue
            start = bisect_left(targets, observed_at[:10])
            for target in targets[start:]:
                if observed_at[:10] > target:
                    continue
                key = (row.entity_id, target)
                prior = prices.get(key)
                if prior is None or (observed_at, available_at, row.observation_id) > (
                    prior.observed_at, prior.available_at, prior.observation_id,
                ):
                    prices[key] = row
    retained = {row.observation_id: row for row in (*facts.values(), *prices.values())}
    return tuple(sorted(retained.values(), key=lambda row: (
        row.entity_id, row.metric_id, row.observed_at, row.available_at, row.observation_id,
    )))


def _quarter_ends(start: str, end: str) -> tuple[str, ...]:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or (first.month, first.day) not in {(3, 31), (6, 30), (9, 30), (12, 31)}:
        raise ValueError("company-state dates must be ordered quarter ends")
    rows, year, quarter = [], first.year, (first.month - 1) // 3 + 1
    while True:
        month = quarter * 3
        day = 31 if month in {3, 12} else 30
        current = date(year, month, day)
        if current > last:
            break
        rows.append(current.isoformat())
        quarter += 1
        if quarter == 5:
            year, quarter = year + 1, 1
    if not rows or rows[-1] != last.isoformat():
        raise ValueError("company-state end_date must be a reachable quarter end")
    return tuple(rows)


def _price_index(
    rows: Iterable[MetricObservation], *, source_as_of: str,
) -> dict[str, tuple[tuple[str, ...], dict[str, MetricObservation]]]:
    latest: dict[str, dict[str, MetricObservation]] = defaultdict(dict)
    for row in rows:
        if row.metric_id != "price" or row.available_at > source_as_of:
            continue
        key = row.observed_at[:10]
        current = latest[row.entity_id].get(key)
        if current is None or (row.available_at, row.observation_id) > (
            current.available_at, current.observation_id,
        ):
            latest[row.entity_id][key] = row
    return {entity: (tuple(sorted(series)), series) for entity, series in latest.items()}


def _price_at(
    index: Mapping[str, tuple[tuple[str, ...], Mapping[str, MetricObservation]]],
    entity_id: str, target: str,
) -> MetricObservation | None:
    dates, series = index.get(entity_id, ((), {}))
    offset = bisect_right(dates, target) - 1
    return series[dates[offset]] if offset >= 0 else None


def _stationary(matrix: Sequence[Sequence[float]]) -> tuple[float, ...]:
    size = len(matrix)
    vector = [1.0 / size] * size
    for _ in range(10_000):
        updated = [sum(vector[source] * matrix[source][target] for source in range(size))
                   for target in range(size)]
        if max(abs(left - right) for left, right in zip(vector, updated, strict=True)) < 1e-13:
            return tuple(updated)
        vector = updated
    raise ValueError("transition matrix stationary distribution did not converge")


def decompose_transition_counts(
    counts: Sequence[Sequence[int | float]], *, pseudocount: float = 1.0,
) -> dict[str, Any]:
    """Fit directed and directionless transition models from identical counts."""
    alpha = require_finite(pseudocount, "transition pseudocount")
    size = len(counts)
    if size < 2 or alpha <= 0 or any(len(row) != size for row in counts):
        raise ValueError("transition counts must be a square matrix with positive smoothing")
    clean = [[require_finite(value, "transition count") for value in row] for row in counts]
    if any(value < 0 for row in clean for value in row):
        raise ValueError("transition counts cannot be negative")
    directed = [
        [(clean[source][target] + alpha) / (sum(clean[source]) + alpha * size)
         for target in range(size)]
        for source in range(size)
    ]
    symmetric = [
        [((2.0 * clean[source][source] if source == target
           else clean[source][target] + clean[target][source]) + alpha)
         for target in range(size)]
        for source in range(size)
    ]
    reversible = [[value / sum(row) for value in row] for row in symmetric]
    stationary = _stationary(directed)
    current = [[
        stationary[source] * directed[source][target]
        - stationary[target] * directed[target][source]
        for target in range(size)
    ] for source in range(size)]
    conservation_residual = max(abs(sum(row)) for row in current)
    return {
        "directed_transition": directed,
        "reversible_transition": reversible,
        "stationary_mass": list(stationary),
        "probability_current": current,
        "circulation_strength": 0.5 * sum(abs(value) for row in current for value in row),
        "conservation_residual": conservation_residual,
    }


def _state(value_high: bool, durability_high: bool) -> str:
    return STATE_IDS[(2 if value_high else 0) + (1 if durability_high else 0)]


def _state_panel(
    observations: Sequence[MetricObservation], epochs: Sequence[str], *, source_as_of: str,
    min_years: int, min_cross_section: int, benchmark_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_entity: dict[str, list[MetricObservation]] = defaultdict(list)
    required = {"revenue_fy", "operating_cash_flow_fy", "capital_expenditure_fy",
                "net_income_fy", "diluted_shares"}
    metric_coverage: dict[str, set[str]] = defaultdict(set)
    for row in observations:
        if row.metric_id != "price":
            by_entity[row.entity_id].append(row)
        if row.metric_id in required:
            metric_coverage[row.entity_id].add(row.metric_id)
    prices = _price_index(observations, source_as_of=source_as_of)
    universe = tuple(sorted(entity for entity, metrics in metric_coverage.items()
                            if metrics == required and entity in prices and entity != benchmark_id))
    panels: list[dict[str, Any]] = []
    for epoch in epochs:
        cutoff = epoch + "T23:59:59Z"
        companies = []
        for entity in universe:
            try:
                quality = compile_company_quality_from_observations(
                    entity_id=entity, observations=by_entity[entity], as_of=cutoff,
                    min_years=min_years,
                )
            except (InsufficientCompanyHistoryError, ValueError):
                continue
            facts = select_company_fundamentals(by_entity[entity], entity_id=entity, as_of=cutoff)
            shares = max((row for row in facts if row.metric_id == "diluted_shares"),
                         key=lambda row: (row.observed_at, row.available_at, row.observation_id),
                         default=None)
            price = _price_at(prices, entity, epoch)
            if shares is None or shares.value <= 0 or price is None:
                continue
            latest_year = quality["history"][-1]
            owner_yield = float(latest_year["owner_earnings"]) / (shares.value * price.value)
            companies.append({
                "entity_id": entity,
                "owner_earnings_yield": owner_yield,
                "durable_earnings_score": float(quality["scores"]["durable_earnings_power"]),
                "aligned_annual_periods": int(quality["coverage"]["aligned_annual_periods"]),
                "price": price.value, "price_observed_at": price.observed_at,
                "price_available_at": price.available_at,
                "source_refs": sorted(set(quality["source_refs"]) | {price.source_ref}),
                "evidence_sha256": stable_sha256([
                    *quality["observation_ids"], shares.observation_id, price.observation_id,
                ]),
            })
        if len(companies) < min_cross_section:
            continue
        value_median = median(row["owner_earnings_yield"] for row in companies)
        durability_median = median(row["durable_earnings_score"] for row in companies)
        for row in companies:
            row["state_id"] = _state(
                row["owner_earnings_yield"] >= value_median,
                row["durable_earnings_score"] >= durability_median,
            )
        panels.append({
            "epoch": epoch, "entity_count": len(companies),
            "thresholds": {"owner_earnings_yield_median": value_median,
                           "durable_earnings_score_median": durability_median},
            "companies": sorted(companies, key=lambda row: row["entity_id"]),
        })
    return panels, {
        "selection_rule": "entities with price plus all required annual SEC fact families",
        "selected_entity_count": len(universe), "selected_entity_ids_sha256": stable_sha256(universe),
        "survivorship_safe": False,
    }


def _transition_blocks(
    panels: Sequence[Mapping[str, Any]], *, benchmark_id: str,
    prices: Mapping[str, tuple[tuple[str, ...], Mapping[str, MetricObservation]]],
) -> list[dict[str, Any]]:
    blocks = []
    for source, target in zip(panels, panels[1:]):
        left = {row["entity_id"]: row for row in source["companies"]}
        right = {row["entity_id"]: row for row in target["companies"]}
        benchmark_left = _price_at(prices, benchmark_id, str(source["epoch"]))
        benchmark_right = _price_at(prices, benchmark_id, str(target["epoch"]))
        if benchmark_left is None or benchmark_right is None:
            continue
        benchmark_return = benchmark_right.value / benchmark_left.value - 1.0
        rows = []
        for entity in sorted(set(left) & set(right)):
            active_return = right[entity]["price"] / left[entity]["price"] - 1.0 - benchmark_return
            rows.append({
                "entity_id": entity, "source_state": left[entity]["state_id"],
                "target_state": right[entity]["state_id"], "active_return": active_return,
                "source_evidence_sha256": left[entity]["evidence_sha256"],
                "target_evidence_sha256": right[entity]["evidence_sha256"],
                "source_refs": sorted(set(left[entity]["source_refs"]) | set(
                    right[entity]["source_refs"]
                )),
            })
        blocks.append({"source_epoch": source["epoch"], "target_epoch": target["epoch"],
                       "entity_count": len(rows), "rows": rows})
    return blocks


def _fit(rows: Sequence[Mapping[str, Any]], pseudocount: float) -> tuple[dict[str, Any], list[float]]:
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    counts = [[0] * len(STATE_IDS) for _ in STATE_IDS]
    payoffs: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        counts[index[row["source_state"]]][index[row["target_state"]]] += 1
        payoffs[row["target_state"]].append(float(row["active_return"]))
    model = decompose_transition_counts(counts, pseudocount=pseudocount)
    global_mean = mean(float(row["active_return"]) for row in rows)
    target_payoffs = [
        (sum(payoffs[state]) + 4.0 * global_mean) / (len(payoffs[state]) + 4.0)
        for state in STATE_IDS
    ]
    return model, target_payoffs


def _score_block(
    block: Mapping[str, Any], model: Mapping[str, Any], target_payoffs: Sequence[float],
    *, round_trip_cost: float,
) -> dict[str, Any]:
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    rows = list(block["rows"])
    result: dict[str, Any] = {"source_epoch": block["source_epoch"],
                              "target_epoch": block["target_epoch"], "entity_count": len(rows)}
    for name, key in (("directed", "directed_transition"), ("reversible", "reversible_transition")):
        probabilities, predictions, actuals, losses, briers = [], [], [], [], []
        for row in rows:
            distribution = model[key][index[row["source_state"]]]
            target = index[row["target_state"]]
            probabilities.append(distribution)
            predictions.append(sum(probability * payoff for probability, payoff in zip(
                distribution, target_payoffs, strict=True,
            )))
            actuals.append(float(row["active_return"]))
            losses.append(-math.log(max(1e-12, distribution[target])))
            briers.append(sum((probability - (1.0 if offset == target else 0.0)) ** 2
                              for offset, probability in enumerate(distribution)))
        high, low = max(predictions), min(predictions)
        best = [actual for prediction, actual in zip(predictions, actuals, strict=True) if prediction == high]
        worst = [actual for prediction, actual in zip(predictions, actuals, strict=True) if prediction == low]
        result[name] = {
            "state_cross_entropy": mean(losses), "state_brier": mean(briers),
            "active_return_mae": mean(abs(predicted - actual) for predicted, actual in zip(
                predictions, actuals, strict=True,
            )),
            "active_return_rank_ic": spearman_rho(predictions, actuals),
            "best_state_net_active_return": mean(best) - round_trip_cost,
            "best_minus_worst_net_spread": mean(best) - mean(worst) - 2.0 * round_trip_cost,
        }
    result["circulation_strength"] = model["circulation_strength"]
    result["current_conservation_residual"] = model["conservation_residual"]
    return result


def _partition_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"block_count": len(rows),
                              "entity_transition_count": sum(int(row["entity_count"]) for row in rows)}
    for model in ("directed", "reversible"):
        result[model] = {metric: mean(float(row[model][metric]) for row in rows) for metric in (
            "state_cross_entropy", "state_brier", "active_return_mae", "active_return_rank_ic",
            "best_state_net_active_return", "best_minus_worst_net_spread",
        )}
    result["directed_win_rate"] = {
        metric: mean(
            float(row["directed"][metric]) < float(row["reversible"][metric])
            for row in rows
        )
        for metric in ("state_cross_entropy", "state_brier", "active_return_mae")
    }
    result["mean_circulation_strength"] = mean(float(row["circulation_strength"]) for row in rows)
    result["maximum_current_conservation_residual"] = max(
        float(row["current_conservation_residual"]) for row in rows
    )
    return result


def compile_company_state_flow_evidence(
    profile_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Compile expanding-window company-state current controls and outcomes."""
    source = Path(profile_path).expanduser().resolve()
    profile = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(profile, Mapping) or profile.get("schema") != COMPANY_STATE_FLOW_PROFILE_SCHEMA:
        raise ValueError(f"company-state profile schema must be {COMPANY_STATE_FLOW_PROFILE_SCHEMA}")
    root = Path(workspace).expanduser().resolve()
    raw_as_of = profile.get("as_of")
    if raw_as_of == "latest_source_run":
        raw_as_of = json.loads((root / "data" / "latest_source_run.json").read_text(
            encoding="utf-8",
        ))["as_of"]
    as_of = canonical_timestamp(raw_as_of, "company-state source as_of")
    mode = require_text(profile.get("mode"), "company-state mode")
    if mode != "retrospective_retrieval_diagnostic":
        raise ValueError("company-state flow currently supports retrospective retrieval diagnostics only")
    benchmark_id = require_text(profile.get("benchmark_id"), "company-state benchmark_id")
    epochs = _quarter_ends(str(profile.get("start_date")), str(profile.get("end_date")))
    min_years, min_cross_section = int(profile.get("min_years", 3)), int(profile.get("min_cross_section", 20))
    min_history = int(profile.get("minimum_training_blocks", 4))
    pseudocount = require_finite(profile.get("pseudocount", 1.0), "company-state pseudocount")
    cost = require_finite(profile.get("round_trip_cost_bps", 10.0), "company-state cost") / 10_000.0
    observations = _load_state_observations(
        root / "data" / "observations.csv", epochs, source_as_of=as_of,
    )
    panels, universe = _state_panel(
        observations, epochs, source_as_of=as_of, min_years=min_years,
        min_cross_section=min_cross_section, benchmark_id=benchmark_id,
    )
    prices = _price_index(observations, source_as_of=as_of)
    blocks = _transition_blocks(panels, benchmark_id=benchmark_id, prices=prices)
    if len(blocks) < min_history + 9:
        raise ValueError("company-state flow requires training plus nine evaluation blocks")
    scored = []
    for offset in range(min_history, len(blocks)):
        history = [row for block in blocks[:offset] for row in block["rows"]]
        model, payoffs = _fit(history, pseudocount)
        scored.append(_score_block(blocks[offset], model, payoffs, round_trip_cost=cost))
    visible_end = max(3, len(scored) // 3)
    holdout_end = max(visible_end + 3, 2 * len(scored) // 3)
    partitions = {
        "visible": scored[:visible_end], "holdout": scored[visible_end:holdout_end],
        "farther_tail": scored[holdout_end:],
    }
    if any(len(rows) < 3 for rows in partitions.values()):
        raise ValueError("company-state partitions require at least three blocks each")
    summaries = {name: _partition_summary(rows) for name, rows in partitions.items()}
    gates = {}
    for name in ("holdout", "farther_tail"):
        directed, reversible = summaries[name]["directed"], summaries[name]["reversible"]
        wins = summaries[name]["directed_win_rate"]
        gates[f"{name}_state_forecast_pass"] = (
            directed["state_cross_entropy"] < reversible["state_cross_entropy"]
            and directed["state_brier"] < reversible["state_brier"]
            and wins["state_cross_entropy"] >= 0.75 and wins["state_brier"] >= 0.75
        )
        gates[f"{name}_economic_pass"] = (
            directed["active_return_mae"] < reversible["active_return_mae"]
            and directed["active_return_rank_ic"] > reversible["active_return_rank_ic"]
            and directed["best_state_net_active_return"] > reversible["best_state_net_active_return"]
            and wins["active_return_mae"] >= 0.75
        )
    gates["current_estimable"] = all(
        summaries[name]["mean_circulation_strength"] > 1e-9
        and summaries[name]["maximum_current_conservation_residual"] < 1e-10
        for name in ("holdout", "farther_tail")
    )
    final_model, final_payoffs = _fit(
        [row for block in blocks for row in block["rows"]], pseudocount,
    )
    source_refs = {ref for panel in panels for company in panel["companies"]
                   for ref in company["source_refs"]}
    source_refs.update(
        point.source_ref for epoch in epochs
        if (point := _price_at(prices, benchmark_id, epoch)) is not None
    )
    body: dict[str, Any] = {
        "schema": COMPANY_STATE_FLOW_EVIDENCE_SCHEMA,
        "experiment_id": require_text(profile.get("experiment_id"), "company-state experiment_id"),
        "as_of": as_of, "mode": mode, "authority": "experiment_only",
        "profile_sha256": stable_sha256({**profile, "as_of": as_of}),
        "state_axes": {
            "valuation": "cross-sectional median split of owner earnings / diluted-share market value",
            "durability": "cross-sectional median split of point-in-time durable earnings score",
            "state_ids": list(STATE_IDS),
        },
        "universe": universe, "benchmark_id": benchmark_id,
        "source_refs": sorted(source_refs),
        "panel_count": len(panels), "transition_block_count": len(blocks),
        "transition_blocks": blocks,
        "evaluation_block_count": len(scored), "partition_summaries": summaries,
        "latest_transition_decomposition": {
            **final_model,
            "target_state_active_return_means": dict(zip(STATE_IDS, final_payoffs, strict=True)),
            "axis_cycle_current": mean(final_model["probability_current"][left][right] for left, right in (
                (0, 2), (2, 3), (3, 1), (1, 0),
            )),
        },
        "gates": gates, "promotion_eligible": all(gates.values()), "capital_authority": False,
        "partitions": partitions,
        "use_boundary": (
            "Fundamental filing availability is enforced, but historical prices were retrieved in the current "
            "source epoch and the universe is current-store selected. This can reject or refine a state-transition "
            "family; it cannot establish investable historical or prospective alpha."
        ),
    }
    return {**body, "evidence_sha256": stable_sha256(body)}


__all__ = [
    "COMPANY_STATE_FLOW_EVIDENCE_SCHEMA", "COMPANY_STATE_FLOW_PROFILE_SCHEMA", "STATE_IDS",
    "compile_company_state_flow_evidence", "decompose_transition_counts",
]
