"""Point-in-time tournaments for investment world-model candidates.

The tournament evaluates already-frozen forecasts.  Candidate generation,
symbolic search, and portfolio authority remain outside this module.  Each
episode belongs to an explicit inference block so that multiple entities in
one market period do not masquerade as independent evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
from statistics import stdev
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import bootstrap_ci
from ztare.worldmodel.evaluation import (
    EvaluationScore,
    compile_evaluation_integrity_receipt,
    conservative_paired_survivor_set,
    validate_evaluation_matrix,
)

from .contracts import canonical_timestamp, require_finite, require_refs, require_text, timestamp_key


TOURNAMENT_PROFILE_SCHEMA = "jaggedthoughts-world-model-tournament-profile-v1"
TOURNAMENT_RESULT_SCHEMA = "jaggedthoughts-world-model-tournament-v1"
_LOSSES = {"absolute", "squared", "brier"}
_ROLES = {"primary", "linked"}
_MODES = {"historical_backtest", "prospective_shadow"}
_GENERATION_PROCESSES = {"deterministic", "subscription_llm", "unknown"}


def _rows(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a nonempty list")
    if not all(isinstance(row, Mapping) for row in value):
        raise ValueError(f"{label} rows must be mappings")
    return tuple(value)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _mean(values: Iterable[float]) -> float:
    rows = tuple(values)
    if not rows:
        raise ValueError("cannot take the mean of an empty sequence")
    return sum(rows) / len(rows)


@dataclass(frozen=True, slots=True)
class ObservableSpec:
    observable_id: str
    unit: str
    loss: str
    scale: float
    weight: float
    role: str = "primary"

    def __post_init__(self) -> None:
        for attr in ("observable_id", "unit"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"observable.{attr}"))
        if self.loss not in _LOSSES:
            raise ValueError(f"unsupported observable loss: {self.loss}")
        if self.role not in _ROLES:
            raise ValueError(f"unsupported observable role: {self.role}")
        scale = require_finite(self.scale, "observable.scale")
        weight = require_finite(self.weight, "observable.weight")
        if scale <= 0 or weight <= 0:
            raise ValueError("observable scale and weight must be positive")
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "weight", weight)

    def score(self, predicted: float, actual: float) -> float:
        predicted = require_finite(predicted, f"prediction.{self.observable_id}")
        actual = require_finite(actual, f"outcome.{self.observable_id}")
        if self.loss == "brier":
            if not 0 <= predicted <= 1 or actual not in {0.0, 1.0}:
                raise ValueError(f"Brier observable {self.observable_id} requires p in [0,1] and y in {{0,1}}")
            return (predicted - actual) ** 2
        normalized = (predicted - actual) / self.scale
        return abs(normalized) if self.loss == "absolute" else normalized**2

    def to_dict(self) -> dict[str, Any]:
        return {
            "observable_id": self.observable_id,
            "unit": self.unit,
            "loss": self.loss,
            "scale": self.scale,
            "weight": self.weight,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class WorldModelCandidate:
    model_id: str
    version: str
    model_family: str
    trial_family_id: str
    mechanism_ids: tuple[str, ...]
    linked_observable_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    generation_process: str = "unknown"
    model_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("model_id", "version", "model_family", "trial_family_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"model.{attr}"))
        mechanisms = tuple(sorted({require_text(row, "model mechanism") for row in self.mechanism_ids}))
        linked = tuple(sorted({require_text(row, "linked observable") for row in self.linked_observable_ids}))
        if not mechanisms:
            raise ValueError("world-model candidate must bind at least one mechanism")
        if self.model_family.lower() in {"lagrangian", "newton", "symbolic_dynamics"} and not linked:
            raise ValueError(f"{self.model_family} candidate must predict a linked observable")
        if self.generation_process not in _GENERATION_PROCESSES:
            raise ValueError(
                f"world-model generation_process must be one of {sorted(_GENERATION_PROCESSES)}"
            )
        object.__setattr__(self, "mechanism_ids", mechanisms)
        object.__setattr__(self, "linked_observable_ids", linked)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "model source ref"))
        object.__setattr__(self, "model_sha256", stable_sha256(self.to_dict(include_hash=False)))

    @property
    def model_key(self) -> str:
        return f"{self.model_id}@{self.version}"

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        body = {
            "model_id": self.model_id,
            "version": self.version,
            "model_key": self.model_key,
            "model_family": self.model_family,
            "trial_family_id": self.trial_family_id,
            "mechanism_ids": list(self.mechanism_ids),
            "linked_observable_ids": list(self.linked_observable_ids),
            "generation_process": self.generation_process,
            "source_refs": list(self.source_refs),
        }
        return {**body, "model_sha256": self.model_sha256} if include_hash else body


@dataclass(frozen=True, slots=True)
class BacktestEpisode:
    episode_id: str
    inference_block_id: str
    entity_id: str
    start_at: str
    end_at: str
    outcome_available_at: str
    starting_weight: float
    asset_return: float
    benchmark_return: float
    cash_return: float
    actual_values: Mapping[str, float]
    source_refs: tuple[str, ...]
    episode_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("episode_id", "inference_block_id", "entity_id"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"episode.{attr}"))
        start = canonical_timestamp(self.start_at, "episode.start_at")
        end = canonical_timestamp(self.end_at, "episode.end_at")
        available = canonical_timestamp(self.outcome_available_at, "episode.outcome_available_at")
        if timestamp_key(end) <= timestamp_key(start):
            raise ValueError("episode end_at must be after start_at")
        if timestamp_key(available) < timestamp_key(end):
            raise ValueError("episode outcome cannot be available before period end")
        weight = require_finite(self.starting_weight, "episode.starting_weight")
        if not 0 <= weight <= 1:
            raise ValueError("episode starting_weight must be in [0,1]")
        actual = {
            require_text(key, "actual observable id"): require_finite(value, f"episode.actual_values.{key}")
            for key, value in self.actual_values.items()
        }
        if not actual:
            raise ValueError("episode actual_values must be nonempty")
        object.__setattr__(self, "start_at", start)
        object.__setattr__(self, "end_at", end)
        object.__setattr__(self, "outcome_available_at", available)
        object.__setattr__(self, "starting_weight", weight)
        for attr in ("asset_return", "benchmark_return", "cash_return"):
            object.__setattr__(self, attr, require_finite(getattr(self, attr), f"episode.{attr}"))
        object.__setattr__(self, "actual_values", actual)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "episode source ref"))
        object.__setattr__(self, "episode_sha256", stable_sha256(self.to_dict(include_hash=False)))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        body = {
            "episode_id": self.episode_id,
            "inference_block_id": self.inference_block_id,
            "entity_id": self.entity_id,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "outcome_available_at": self.outcome_available_at,
            "starting_weight": self.starting_weight,
            "asset_return": self.asset_return,
            "benchmark_return": self.benchmark_return,
            "cash_return": self.cash_return,
            "actual_values": dict(sorted(self.actual_values.items())),
            "source_refs": list(self.source_refs),
        }
        return {**body, "episode_sha256": self.episode_sha256} if include_hash else body


@dataclass(frozen=True, slots=True)
class WorldModelForecast:
    model_id: str
    episode_id: str
    trained_through: str
    issued_at: str
    predicted_values: Mapping[str, float]
    target_weight: float
    source_refs: tuple[str, ...]
    forecast_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", require_text(self.model_id, "forecast.model_id"))
        object.__setattr__(self, "episode_id", require_text(self.episode_id, "forecast.episode_id"))
        trained = canonical_timestamp(self.trained_through, "forecast.trained_through")
        issued = canonical_timestamp(self.issued_at, "forecast.issued_at")
        if timestamp_key(issued) < timestamp_key(trained):
            raise ValueError("forecast issued_at cannot precede trained_through")
        predicted = {
            require_text(key, "predicted observable id"): require_finite(value, f"forecast.predicted_values.{key}")
            for key, value in self.predicted_values.items()
        }
        if not predicted:
            raise ValueError("forecast predicted_values must be nonempty")
        weight = require_finite(self.target_weight, "forecast.target_weight")
        if not 0 <= weight <= 1:
            raise ValueError("forecast target_weight must be in [0,1]")
        object.__setattr__(self, "trained_through", trained)
        object.__setattr__(self, "issued_at", issued)
        object.__setattr__(self, "predicted_values", predicted)
        object.__setattr__(self, "target_weight", weight)
        object.__setattr__(self, "source_refs", require_refs(self.source_refs, "forecast source ref"))
        object.__setattr__(self, "forecast_sha256", stable_sha256(self.to_dict(include_hash=False)))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        body = {
            "model_id": self.model_id,
            "episode_id": self.episode_id,
            "trained_through": self.trained_through,
            "issued_at": self.issued_at,
            "predicted_values": dict(sorted(self.predicted_values.items())),
            "target_weight": self.target_weight,
            "source_refs": list(self.source_refs),
        }
        return {**body, "forecast_sha256": self.forecast_sha256} if include_hash else body


def _block_means(rows: Iterable[Mapping[str, Any]], metric: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["inference_block_id"]), []).append(float(row[metric]))
    return {key: _mean(values) for key, values in sorted(grouped.items())}


def _ci(values: Iterable[float], *, seed: int) -> dict[str, float | None]:
    point, low, high = bootstrap_ci(tuple(values), seed=seed)
    return {"mean": point, "ci_low": low, "ci_high": high}


def _compound(returns: Iterable[float]) -> float:
    wealth = 1.0
    for value in returns:
        wealth *= 1 + value
    return wealth - 1


def _max_drawdown(returns: Iterable[float]) -> float:
    wealth = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in returns:
        wealth *= 1 + value
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1)
    return drawdown


def _economic_backtest(
    *,
    book_returns: tuple[float, ...],
    benchmark_returns: tuple[float, ...],
    periods_per_year: float,
) -> dict[str, float | None]:
    if len(book_returns) != len(benchmark_returns) or not book_returns:
        raise ValueError("economic backtest requires aligned nonempty return series")
    active = tuple(left - right for left, right in zip(book_returns, benchmark_returns))
    book_cumulative = _compound(book_returns)
    benchmark_cumulative = _compound(benchmark_returns)
    annualizer = periods_per_year / len(book_returns)
    book_wealth = 1 + book_cumulative
    benchmark_wealth = 1 + benchmark_cumulative
    annual_book = book_wealth**annualizer - 1 if book_wealth > 0 else None
    annual_benchmark = benchmark_wealth**annualizer - 1 if benchmark_wealth > 0 else None
    active_volatility = stdev(active) * math.sqrt(periods_per_year) if len(active) >= 2 else None
    information_ratio = (
        _mean(active) * periods_per_year / active_volatility
        if active_volatility is not None and active_volatility > 0 else None
    )
    return {
        "cumulative_book_return": book_cumulative,
        "cumulative_benchmark_return": benchmark_cumulative,
        "cumulative_active_return": book_cumulative - benchmark_cumulative,
        "annualized_book_return": annual_book,
        "annualized_benchmark_return": annual_benchmark,
        "annualized_active_return": (
            annual_book - annual_benchmark
            if annual_book is not None and annual_benchmark is not None else None
        ),
        "annualized_active_volatility": active_volatility,
        "information_ratio": information_ratio,
        "active_hit_rate": sum(value > 0 for value in active) / len(active),
        "max_book_drawdown": _max_drawdown(book_returns),
    }


def evaluate_world_model_tournament(
    *,
    tournament_id: str,
    owner: str,
    as_of: str,
    mode: str,
    baseline_model_id: str,
    observables: tuple[ObservableSpec, ...],
    models: tuple[WorldModelCandidate, ...],
    episodes: tuple[BacktestEpisode, ...],
    forecasts: tuple[WorldModelForecast, ...],
    transaction_cost_bps: float,
    declared_trial_family_ids: tuple[str, ...],
    source_refs: tuple[str, ...],
    alpha: float = 0.05,
    min_inference_blocks: int = 8,
    periods_per_year: float = 4,
    seed: int = 42,
    source_availability_rows: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    """Score a closed candidate set and return a conservative survivor committee."""
    tournament_id = require_text(tournament_id, "tournament_id")
    owner = require_text(owner, "tournament.owner")
    as_of = canonical_timestamp(as_of, "tournament.as_of")
    if mode not in _MODES:
        raise ValueError(f"unsupported tournament mode: {mode}")
    costs = require_finite(transaction_cost_bps, "transaction_cost_bps")
    alpha = require_finite(alpha, "alpha")
    periods_per_year = require_finite(periods_per_year, "periods_per_year")
    if costs < 0 or not 0 < alpha < 1 or min_inference_blocks < 5 or periods_per_year <= 0:
        raise ValueError("costs must be nonnegative, alpha in (0,1), and min blocks at least 5")
    if not observables or len({row.observable_id for row in observables}) != len(observables):
        raise ValueError("observable identities must be nonempty and unique")
    if not models or len({row.model_id for row in models}) != len(models):
        raise ValueError("model identities must be nonempty and unique")
    model_by_id = {row.model_id: row for row in models}
    if baseline_model_id not in model_by_id:
        raise ValueError("baseline_model_id must name a tournament model")
    observable_by_id = {row.observable_id: row for row in observables}
    observable_ids = set(observable_by_id)
    linked_ids = {row.observable_id for row in observables if row.role == "linked"}
    for model in models:
        if not set(model.linked_observable_ids) <= linked_ids:
            raise ValueError(f"model {model.model_id} names a non-linked observable")
    trials = tuple(sorted({require_text(row, "declared trial family") for row in declared_trial_family_ids}))
    if not trials or any(model.trial_family_id not in trials for model in models):
        raise ValueError("declared trial registry must cover every model trial family")
    episode_by_id = {row.episode_id: row for row in episodes}
    for episode in episodes:
        if min(episode.asset_return, episode.benchmark_return, episode.cash_return) < -1:
            raise ValueError(f"episode {episode.episode_id} contains a return below -100%")
    matrix = validate_evaluation_matrix(
        as_of=as_of,
        observable_ids=observable_ids,
        models=models,
        episodes=episodes,
        forecasts=forecasts,
    )
    integrity = compile_evaluation_integrity_receipt(
        temporal_design=(
            "prospective_sealed" if mode == "prospective_shadow" else "historical_replay"
        ),
        generation_processes=(row.generation_process for row in models),
        source_availability_rows=source_availability_rows,
        seal_rows=(
            {
                "episode_id": f"{row.episode_id}:{row.model_id}",
                "sealed_at": row.issued_at,
                "episode_start_at": episode_by_id[row.episode_id].start_at,
            }
            for row in forecasts
        ) if mode == "prospective_shadow" else (),
        maturity_rows=(
            {
                "episode_id": row.episode_id,
                "episode_end_at": row.end_at,
                "outcome_available_at": row.outcome_available_at,
                "evaluated_at": as_of,
            }
            for row in episodes
        ) if mode == "prospective_shadow" else (),
    )
    forecast_by_key = {(row.model_id, row.episode_id): row for row in forecasts}

    total_weight = sum(row.weight for row in observables)
    linked_weight = sum(observable_by_id[row].weight for row in linked_ids)
    scored_by_model: dict[str, list[dict[str, Any]]] = {row.model_id: [] for row in models}
    for model in models:
        for episode in sorted(episodes, key=lambda row: (row.start_at, row.episode_id)):
            forecast = forecast_by_key[(model.model_id, episode.episode_id)]
            losses = {
                spec.observable_id: spec.score(
                    forecast.predicted_values[spec.observable_id],
                    episode.actual_values[spec.observable_id],
                )
                for spec in observables
            }
            prediction_loss = sum(observable_by_id[key].weight * value for key, value in losses.items()) / total_weight
            linked_loss = (
                sum(observable_by_id[key].weight * losses[key] for key in linked_ids) / linked_weight
                if linked_ids else 0.0
            )
            turnover = abs(forecast.target_weight - episode.starting_weight)
            book_return = (
                forecast.target_weight * episode.asset_return
                + (1 - forecast.target_weight) * episode.cash_return
                - turnover * costs / 10_000
            )
            scored_by_model[model.model_id].append({
                "episode_id": episode.episode_id,
                "inference_block_id": episode.inference_block_id,
                "prediction_loss": prediction_loss,
                "linked_loss": linked_loss,
                "net_excess_return": book_return - episode.benchmark_return,
                "book_return": book_return,
                "benchmark_return": episode.benchmark_return,
                "turnover": turnover,
                "observable_losses": dict(sorted(losses.items())),
            })

    aggregate_rows: list[dict[str, Any]] = []
    evaluation_scores: list[EvaluationScore] = []
    block_start = {
        block_id: min(
            episode.start_at for episode in episodes if episode.inference_block_id == block_id
        )
        for block_id in {episode.inference_block_id for episode in episodes}
    }
    block_order = tuple(sorted(block_start, key=lambda key: (block_start[key], key)))
    for model in models:
        rows = scored_by_model[model.model_id]
        prediction = _block_means(rows, "prediction_loss")
        linked = _block_means(rows, "linked_loss")
        economic = {key: -value for key, value in _block_means(rows, "net_excess_return").items()}
        book = _block_means(rows, "book_return")
        benchmark = _block_means(rows, "benchmark_return")
        evaluation_scores.extend(
            EvaluationScore(
                model_id=model.model_id,
                episode_id=str(row["episode_id"]),
                inference_block_id=str(row["inference_block_id"]),
                losses={
                    "prediction_loss": float(row["prediction_loss"]),
                    "linked_loss": float(row["linked_loss"]),
                    "economic_loss": -float(row["net_excess_return"]),
                },
            )
            for row in rows
        )
        aggregate_rows.append({
            "model_id": model.model_id,
            "model_sha256": model.model_sha256,
            "episode_count": len(rows),
            "inference_block_count": len(prediction),
            "prediction_loss": _ci(prediction.values(), seed=seed),
            "linked_loss": _ci(linked.values(), seed=seed + 1),
            "net_excess_return": _ci((-value for value in economic.values()), seed=seed + 2),
            "mean_turnover": _mean(float(row["turnover"]) for row in rows),
            "economic_backtest": _economic_backtest(
                book_returns=tuple(book[key] for key in block_order),
                benchmark_returns=tuple(benchmark[key] for key in block_order),
                periods_per_year=periods_per_year,
            ),
            "observable_mean_losses": {
                spec.observable_id: _mean(float(row["observable_losses"][spec.observable_id]) for row in rows)
                for spec in observables
            },
        })

    model_ids = sorted(model_by_id)
    dimensions = ("prediction_loss", "linked_loss", "economic_loss")
    survivor = conservative_paired_survivor_set(
        scores=evaluation_scores,
        model_ids=model_ids,
        episode_ids=episode_by_id,
        dimensions=dimensions,
        alpha=alpha,
        min_inference_blocks=min_inference_blocks,
        seed=seed,
    )
    inference_blocks = len({row.inference_block_id for row in episodes})

    model_tracks = []
    for model in models:
        model_tracks.append({
            "model": model.to_dict(),
            "forecasts": [
                forecast_by_key[(model.model_id, episode.episode_id)].to_dict()
                for episode in sorted(episodes, key=lambda row: (row.start_at, row.episode_id))
            ],
        })
    body = {
        "schema": TOURNAMENT_RESULT_SCHEMA,
        "tournament_id": tournament_id,
        "owner": owner,
        "as_of": as_of,
        "mode": mode,
        "baseline_model_id": baseline_model_id,
        "evaluation_matrix": matrix.to_dict(),
        "evaluation_integrity": integrity,
        "observables": [row.to_dict() for row in observables],
        "model_tracks": model_tracks,
        "episodes": [row.to_dict() for row in sorted(episodes, key=lambda item: (item.start_at, item.episode_id))],
        "transaction_cost_bps": costs,
        "periods_per_year": periods_per_year,
        "declared_trial_family_ids": list(trials),
        "unmaterialized_trial_family_ids": sorted(set(trials) - {row.trial_family_id for row in models}),
        "source_refs": list(require_refs(source_refs, "tournament source ref")),
        "episode_count": len(episodes),
        "inference_block_count": inference_blocks,
        "min_inference_blocks": min_inference_blocks,
        "inference_sufficient": survivor["inference_sufficient"],
        "alpha": alpha,
        "multiple_testing": "Benjamini-Hochberg over all paired model/dimension comparisons",
        "resampling_unit": "declared inference block",
        "block_aggregation": "equal-weight mean across episodes in each inference block",
        "model_metrics": sorted(aggregate_rows, key=lambda row: row["model_id"]),
        "paired_comparisons": survivor["paired_comparisons"],
        "point_estimate_frontier_model_ids": survivor["point_estimate_frontier_model_ids"],
        "statistical_dominance": survivor["statistical_dominance"],
        "survivor_model_ids": survivor["survivor_model_ids"],
        "survivor_set_method": survivor["method"],
        "survivor_set_sha256": survivor["survivor_set_sha256"],
        "scope_closed": True,
        "paper_policy_authority": False,
        "capital_authority": False,
        "use_boundary": (
            f"Temporal authority: {integrity['evidence_authority']}. "
            "Historical reconstruction without point-in-time deterministic evidence remains diagnostic; "
            "only a separately approved portfolio policy may authorize capital."
        ),
        "limitations": [
            "The survivor set is not a formal Hansen-Lunde-Nason model confidence set.",
            "The declared trial registry exposes search breadth but does not implement White's Reality Check.",
            "Point forecasts support absolute, squared, and Brier losses; distributional CRPS is not implemented.",
            "Deflated Sharpe and probability-of-backtest-overfitting diagnostics are not implemented.",
        ],
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def compile_world_model_tournament_profile(path: str | Path) -> dict[str, Any]:
    """Load and evaluate one JSON/YAML tournament profile."""
    source = Path(path).expanduser().resolve()
    raw = source.read_text(encoding="utf-8")
    payload = json.loads(raw) if source.suffix.lower() == ".json" else yaml.safe_load(raw)
    payload = _mapping(payload, "tournament profile")
    if payload.get("schema") != TOURNAMENT_PROFILE_SCHEMA:
        raise ValueError(f"tournament profile schema must be {TOURNAMENT_PROFILE_SCHEMA}")
    tournament = _mapping(payload.get("tournament"), "tournament")
    observables = tuple(ObservableSpec(
        observable_id=str(row["observable_id"]),
        unit=str(row["unit"]),
        loss=str(row["loss"]),
        scale=float(row.get("scale", 1)),
        weight=float(row.get("weight", 1)),
        role=str(row.get("role", "primary")),
    ) for row in _rows(payload.get("observables"), "observables"))
    models = tuple(WorldModelCandidate(
        model_id=str(row["model_id"]),
        version=str(row["version"]),
        model_family=str(row["model_family"]),
        trial_family_id=str(row["trial_family_id"]),
        mechanism_ids=tuple(str(value) for value in row.get("mechanism_ids", [])),
        linked_observable_ids=tuple(str(value) for value in row.get("linked_observable_ids", [])),
        source_refs=tuple(str(value) for value in row.get("source_refs", [])),
        generation_process=str(row.get("generation_process", "unknown")),
    ) for row in _rows(payload.get("models"), "models"))
    episodes = tuple(BacktestEpisode(
        episode_id=str(row["episode_id"]),
        inference_block_id=str(row["inference_block_id"]),
        entity_id=str(row["entity_id"]),
        start_at=str(row["start_at"]),
        end_at=str(row["end_at"]),
        outcome_available_at=str(row["outcome_available_at"]),
        starting_weight=float(row["starting_weight"]),
        asset_return=float(row["asset_return"]),
        benchmark_return=float(row["benchmark_return"]),
        cash_return=float(row.get("cash_return", 0)),
        actual_values=_mapping(row.get("actual_values"), "episode.actual_values"),
        source_refs=tuple(str(value) for value in row.get("source_refs", [])),
    ) for row in _rows(payload.get("episodes"), "episodes"))
    forecasts = tuple(WorldModelForecast(
        model_id=str(row["model_id"]),
        episode_id=str(row["episode_id"]),
        trained_through=str(row["trained_through"]),
        issued_at=str(row["issued_at"]),
        predicted_values=_mapping(row.get("predicted_values"), "forecast.predicted_values"),
        target_weight=float(row["target_weight"]),
        source_refs=tuple(str(value) for value in row.get("source_refs", [])),
    ) for row in _rows(payload.get("forecasts"), "forecasts"))
    profile_ref = f"profile-sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    integrity_profile = payload.get("evaluation_integrity") or {}
    if not isinstance(integrity_profile, Mapping):
        raise ValueError("evaluation_integrity must be a mapping")
    availability_rows = integrity_profile.get("source_availability_rows") or []
    if not isinstance(availability_rows, list) or not all(
        isinstance(row, Mapping) for row in availability_rows
    ):
        raise ValueError("evaluation_integrity.source_availability_rows must be a list of mappings")
    return evaluate_world_model_tournament(
        tournament_id=str(tournament["tournament_id"]),
        owner=str(tournament["owner"]),
        as_of=str(tournament["as_of"]),
        mode=str(tournament["mode"]),
        baseline_model_id=str(tournament["baseline_model_id"]),
        observables=observables,
        models=models,
        episodes=episodes,
        forecasts=forecasts,
        transaction_cost_bps=float(tournament.get("transaction_cost_bps", 0)),
        declared_trial_family_ids=tuple(str(row) for row in tournament.get("declared_trial_family_ids", [])),
        source_refs=tuple(str(row) for row in tournament.get("source_refs", [])) + (profile_ref,),
        alpha=float(tournament.get("alpha", 0.05)),
        min_inference_blocks=int(tournament.get("min_inference_blocks", 8)),
        periods_per_year=float(tournament.get("periods_per_year", 4)),
        seed=int(tournament.get("seed", 42)),
        source_availability_rows=tuple(availability_rows),
    )


__all__ = [
    "BacktestEpisode",
    "ObservableSpec",
    "TOURNAMENT_PROFILE_SCHEMA",
    "TOURNAMENT_RESULT_SCHEMA",
    "WorldModelCandidate",
    "WorldModelForecast",
    "compile_world_model_tournament_profile",
    "evaluate_world_model_tournament",
]
