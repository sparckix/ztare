"""Substrate-general world-model evaluation and tournament contracts.

World-model generators may use programs, equations, statistical estimators, or
domain simulators.  This module sees only their immutable identity, frozen
forecasts, settled episodes, and loss coordinates.  Domain adapters own state,
actions, observables, costs, and the interpretation of each loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import bh_fdr, paired_permutation_test


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be nonempty")
    return result


def _time(value: str, label: str) -> datetime:
    text = _text(value, label)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError(f"{label} must be ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def _mean(values: Iterable[float]) -> float:
    rows = tuple(float(row) for row in values)
    if not rows:
        raise ValueError("cannot average an empty score sequence")
    return sum(rows) / len(rows)


@runtime_checkable
class WorldModelCandidateView(Protocol):
    """Identity surface shared by executable and forecast-only candidates."""

    model_id: str
    version: str
    model_family: str
    trial_family_id: str
    mechanism_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    model_sha256: str


@runtime_checkable
class WorldModelForecastView(Protocol):
    """One candidate's immutable prediction for one evaluation episode."""

    model_id: str
    episode_id: str
    trained_through: str
    issued_at: str
    predicted_values: Mapping[str, float]
    source_refs: tuple[str, ...]
    forecast_sha256: str


@runtime_checkable
class WorldModelEpisodeView(Protocol):
    """One externally settled comparison episode."""

    episode_id: str
    inference_block_id: str
    start_at: str
    end_at: str
    outcome_available_at: str
    actual_values: Mapping[str, float]
    source_refs: tuple[str, ...]
    episode_sha256: str


@dataclass(frozen=True, slots=True)
class EvaluationMatrixReceipt:
    """Chronology and coverage receipt for a closed comparison population."""

    as_of: str
    model_ids: tuple[str, ...]
    episode_ids: tuple[str, ...]
    inference_block_ids: tuple[str, ...]
    observable_ids: tuple[str, ...]
    forecast_sha256s: tuple[str, ...]
    matrix_sha256: str = field(init=False)
    schema: str = "ztare-worldmodel-evaluation-matrix-v1"

    def __post_init__(self) -> None:
        body = self.to_dict(include_hash=False)
        object.__setattr__(self, "matrix_sha256", stable_sha256(body))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        body = {
            "schema": self.schema,
            "as_of": self.as_of,
            "model_ids": list(self.model_ids),
            "episode_ids": list(self.episode_ids),
            "inference_block_ids": list(self.inference_block_ids),
            "observable_ids": list(self.observable_ids),
            "forecast_sha256s": list(self.forecast_sha256s),
            "complete_matrix": True,
        }
        return {**body, "matrix_sha256": self.matrix_sha256} if include_hash else body


def validate_evaluation_matrix(
    *,
    as_of: str,
    observable_ids: Iterable[str],
    models: Iterable[WorldModelCandidateView],
    episodes: Iterable[WorldModelEpisodeView],
    forecasts: Iterable[WorldModelForecastView],
) -> EvaluationMatrixReceipt:
    """Validate chronology and the exact candidate-by-episode product."""
    as_of_key = _time(as_of, "evaluation as_of")
    observable_set = {_text(row, "observable id") for row in observable_ids}
    model_rows = tuple(models)
    episode_rows = tuple(episodes)
    forecast_rows = tuple(forecasts)
    model_by_id = {row.model_id: row for row in model_rows}
    episode_by_id = {row.episode_id: row for row in episode_rows}
    if not observable_set:
        raise ValueError("evaluation observable set must be nonempty")
    if not model_rows or len(model_by_id) != len(model_rows):
        raise ValueError("evaluation model identities must be nonempty and unique")
    if not episode_rows or len(episode_by_id) != len(episode_rows):
        raise ValueError("evaluation episode identities must be nonempty and unique")
    for model in model_rows:
        for value, label in (
            (model.model_id, "model_id"),
            (model.version, "version"),
            (model.model_family, "model_family"),
            (model.trial_family_id, "trial_family_id"),
            (model.model_sha256, "model_sha256"),
        ):
            _text(value, f"world model {label}")
        if not model.mechanism_ids or not model.source_refs:
            raise ValueError(f"world model {model.model_id} needs mechanisms and sources")
    for episode in episode_rows:
        start = _time(episode.start_at, f"episode {episode.episode_id} start_at")
        end = _time(episode.end_at, f"episode {episode.episode_id} end_at")
        available = _time(
            episode.outcome_available_at,
            f"episode {episode.episode_id} outcome_available_at",
        )
        if end <= start or available < end:
            raise ValueError(f"episode {episode.episode_id} has invalid chronology")
        if available > as_of_key:
            raise ValueError(f"episode {episode.episode_id} outcome was unavailable at evaluation as_of")
        if set(episode.actual_values) != observable_set:
            raise ValueError(f"episode {episode.episode_id} does not match the observable contract")
        if not episode.source_refs:
            raise ValueError(f"episode {episode.episode_id} needs sources")
    forecast_by_key: dict[tuple[str, str], WorldModelForecastView] = {}
    for forecast in forecast_rows:
        key = (forecast.model_id, forecast.episode_id)
        if key in forecast_by_key:
            raise ValueError(f"duplicate world-model forecast identity: {key}")
        if forecast.model_id not in model_by_id or forecast.episode_id not in episode_by_id:
            raise ValueError(f"forecast names an unknown model or episode: {key}")
        episode = episode_by_id[forecast.episode_id]
        trained = _time(forecast.trained_through, f"forecast {key} trained_through")
        issued = _time(forecast.issued_at, f"forecast {key} issued_at")
        start = _time(episode.start_at, f"episode {episode.episode_id} start_at")
        if issued < trained:
            raise ValueError(f"forecast {key} was issued before its training cutoff")
        if issued > start:
            raise ValueError(f"forecast {key} was issued after its episode began")
        if trained > start:
            raise ValueError(f"forecast {key} trains through its evaluation period")
        if set(forecast.predicted_values) != observable_set:
            raise ValueError(f"forecast {key} does not match the observable contract")
        if not forecast.source_refs:
            raise ValueError(f"forecast {key} needs sources")
        forecast_by_key[key] = forecast
    expected = {
        (model.model_id, episode.episode_id)
        for model in model_rows
        for episode in episode_rows
    }
    if set(forecast_by_key) != expected:
        raise ValueError("evaluation requires the complete model-by-episode forecast matrix")
    return EvaluationMatrixReceipt(
        as_of=as_of,
        model_ids=tuple(sorted(model_by_id)),
        episode_ids=tuple(sorted(episode_by_id)),
        inference_block_ids=tuple(sorted({row.inference_block_id for row in episode_rows})),
        observable_ids=tuple(sorted(observable_set)),
        forecast_sha256s=tuple(sorted(row.forecast_sha256 for row in forecast_rows)),
    )


def compile_evaluation_integrity_receipt(
    *,
    temporal_design: str,
    generation_processes: Iterable[str],
    source_availability_rows: Iterable[Mapping[str, Any]] = (),
    seal_rows: Iterable[Mapping[str, Any]] = (),
    maturity_rows: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Classify temporal authority without re-scoring an evaluation.

    Recorded chronology cannot reveal whether a historical answer came from a
    deterministic program or from a model whose parameters may contain later
    events.  This receipt makes that producer boundary explicit and separately
    verifies point-in-time sources, prospective seals, and outcome maturity.
    """
    design = _text(temporal_design, "evaluation temporal_design")
    if design not in {"historical_replay", "prospective_sealed"}:
        raise ValueError(f"unsupported evaluation temporal design: {design}")
    processes = tuple(sorted({_text(row, "generation process") for row in generation_processes}))
    allowed_processes = {"deterministic", "subscription_llm", "unknown"}
    if not processes or not set(processes) <= allowed_processes:
        raise ValueError(f"generation processes must be drawn from {sorted(allowed_processes)}")

    sources = []
    for index, row in enumerate(source_availability_rows):
        source_id = _text(row.get("source_id"), f"source row {index} source_id")
        available_at = _text(row.get("available_at"), f"source row {source_id} available_at")
        source_as_of = _text(
            row.get("as_of") or row.get("information_cutoff"),
            f"source row {source_id} as_of",
        )
        compliant = _time(available_at, "source available_at") <= _time(
            source_as_of, "source as_of",
        )
        source = {
            "source_id": source_id,
            "available_at": available_at,
            "as_of": source_as_of,
            "available_by_as_of": compliant,
        }
        for optional in (
            "field_path", "observed_at", "source_sha256", "availability_basis",
        ):
            if row.get(optional) is not None:
                source[optional] = row[optional]
        sources.append(source)
    sources.sort(key=lambda row: (
        str(row.get("field_path") or ""), row["source_id"],
        row["as_of"], row["available_at"],
    ))

    seals = []
    for index, row in enumerate(seal_rows):
        episode_id = _text(row.get("episode_id"), f"seal row {index} episode_id")
        sealed_at = _text(row.get("sealed_at"), f"seal row {episode_id} sealed_at")
        episode_start_at = _text(
            row.get("episode_start_at"), f"seal row {episode_id} episode_start_at",
        )
        compliant = _time(sealed_at, "forecast sealed_at") <= _time(
            episode_start_at, "episode start_at",
        )
        seals.append({
            "episode_id": episode_id,
            "sealed_at": sealed_at,
            "episode_start_at": episode_start_at,
            "sealed_before_episode": compliant,
        })
    seals.sort(key=lambda row: (row["episode_id"], row["sealed_at"]))

    maturities = []
    for index, row in enumerate(maturity_rows):
        episode_id = _text(row.get("episode_id"), f"maturity row {index} episode_id")
        episode_end_at = _text(
            row.get("episode_end_at"), f"maturity row {episode_id} episode_end_at",
        )
        outcome_available_at = _text(
            row.get("outcome_available_at"),
            f"maturity row {episode_id} outcome_available_at",
        )
        evaluated_at = _text(
            row.get("evaluated_at"), f"maturity row {episode_id} evaluated_at",
        )
        compliant = (
            _time(episode_end_at, "episode end_at")
            <= _time(outcome_available_at, "outcome available_at")
            <= _time(evaluated_at, "evaluation time")
        )
        maturities.append({
            "episode_id": episode_id,
            "episode_end_at": episode_end_at,
            "outcome_available_at": outcome_available_at,
            "evaluated_at": evaluated_at,
            "matured_before_evaluation": compliant,
        })
    maturities.sort(key=lambda row: (row["episode_id"], row["evaluated_at"]))

    source_complete = bool(sources) and all(row["available_by_as_of"] for row in sources)
    seal_complete = bool(seals) and all(row["sealed_before_episode"] for row in seals)
    maturity_complete = bool(maturities) and all(
        row["matured_before_evaluation"] for row in maturities
    )
    contains_llm = "subscription_llm" in processes
    deterministic_only = processes == ("deterministic",)

    if design == "historical_replay" and contains_llm:
        evaluation_class = "llm_assisted_historical_reconstruction"
        evidence_authority = "diagnostic_only"
        authority_rank = 0
        reason = (
            "Historical source timestamps cannot exclude later target history embedded "
            "in subscription-model parameters."
        )
    elif design == "historical_replay" and deterministic_only and source_complete:
        evaluation_class = "deterministic_point_in_time_mechanical_replay"
        evidence_authority = "point_in_time_backtest_evidence"
        authority_rank = 1
        reason = "Every declared source row was available by its mechanical replay cutoff."
    elif design == "historical_replay":
        evaluation_class = "historical_reconstruction_unverified"
        evidence_authority = "diagnostic_only"
        authority_rank = 0
        reason = "Historical producer identity or complete point-in-time source availability is unverified."
    elif not seal_complete:
        evaluation_class = "prospective_seal_invalid"
        evidence_authority = "diagnostic_only"
        authority_rank = 0
        reason = "The episode lacks a complete forecast-before-start seal receipt."
    elif not maturities:
        evaluation_class = "prospective_sealed_episode"
        evidence_authority = "prospective_pending"
        authority_rank = 0
        reason = "The forecast is sealed; the outcome has not matured."
    elif maturity_complete:
        evaluation_class = "prospective_sealed_episode"
        evidence_authority = "matured_prospective_evidence"
        authority_rank = 2
        reason = "The forecast was sealed before the episode and evaluated only after outcome availability."
    else:
        evaluation_class = "prospective_outcome_invalid"
        evidence_authority = "diagnostic_only"
        authority_rank = 0
        reason = "The outcome maturity chronology is incomplete or invalid."

    backtest_eligible = evidence_authority == "point_in_time_backtest_evidence"
    prospective_eligible = evidence_authority == "matured_prospective_evidence"
    body = {
        "schema": "ztare-worldmodel-evaluation-integrity-v1",
        "temporal_design": design,
        "evaluation_class": evaluation_class,
        "generation_processes": list(processes),
        "source_availability_rows": sources,
        "seal_rows": seals,
        "maturity_rows": maturities,
        "point_in_time_sources_complete": source_complete,
        "prospective_seal_complete": seal_complete,
        "outcome_maturity_complete": maturity_complete,
        "latent_knowledge_contaminated": design == "historical_replay" and contains_llm,
        "backtest_evidence_eligible": backtest_eligible,
        "prospective_evidence_eligible": prospective_eligible,
        "alpha_evidence_eligible": backtest_eligible or prospective_eligible,
        "evidence_authority": evidence_authority,
        "authority_rank": authority_rank,
        "sufficient_for_alpha_claim": False,
        "paper_policy_authority": False,
        "capital_authority": False,
        "reason": reason,
    }
    return {**body, "evaluation_integrity_sha256": stable_sha256(body)}


@dataclass(frozen=True, slots=True)
class EvaluationScore:
    """Domain-lowered losses for one model and settled episode."""

    model_id: str
    episode_id: str
    inference_block_id: str
    losses: Mapping[str, float]

    def __post_init__(self) -> None:
        for attr in ("model_id", "episode_id", "inference_block_id"):
            object.__setattr__(self, attr, _text(getattr(self, attr), f"score.{attr}"))
        losses = {str(key): float(value) for key, value in self.losses.items()}
        if not losses or any(value != value or value in {float("inf"), float("-inf")} for value in losses.values()):
            raise ValueError("evaluation losses must be nonempty and finite")
        object.__setattr__(self, "losses", losses)


def _block_vectors(
    scores: tuple[EvaluationScore, ...],
    *,
    model_ids: tuple[str, ...],
    dimensions: tuple[str, ...],
) -> dict[str, dict[str, dict[str, float]]]:
    vectors: dict[str, dict[str, dict[str, float]]] = {}
    for model_id in model_ids:
        model_rows = tuple(row for row in scores if row.model_id == model_id)
        vectors[model_id] = {}
        for dimension in dimensions:
            grouped: dict[str, list[float]] = {}
            for row in model_rows:
                grouped.setdefault(row.inference_block_id, []).append(row.losses[dimension])
            vectors[model_id][dimension] = {
                key: _mean(values) for key, values in sorted(grouped.items())
            }
    return vectors


def _frontier(points: Mapping[str, Mapping[str, float]]) -> list[str]:
    survivors = []
    for candidate_id, candidate in points.items():
        dominated = any(
            other_id != candidate_id
            and all(other[key] <= candidate[key] + 1e-12 for key in candidate)
            and any(other[key] < candidate[key] - 1e-12 for key in candidate)
            for other_id, other in points.items()
        )
        if not dominated:
            survivors.append(candidate_id)
    return sorted(survivors)


def conservative_paired_survivor_set(
    *,
    scores: Iterable[EvaluationScore],
    model_ids: Iterable[str],
    episode_ids: Iterable[str],
    dimensions: Iterable[str],
    alpha: float = 0.05,
    min_inference_blocks: int = 8,
    seed: int = 42,
) -> dict[str, Any]:
    """Return FDR-corrected nondomination over domain-lowered loss vectors."""
    score_rows = tuple(scores)
    models = tuple(sorted({_text(row, "model id") for row in model_ids}))
    episodes = tuple(sorted({_text(row, "episode id") for row in episode_ids}))
    dims = tuple(sorted({_text(row, "loss dimension") for row in dimensions}))
    if not models or not episodes or not dims:
        raise ValueError("survivor evaluation requires models, episodes, and dimensions")
    if not 0 < alpha < 1 or min_inference_blocks < 5:
        raise ValueError("survivor alpha must be in (0,1) and min blocks at least 5")
    score_by_key = {(row.model_id, row.episode_id): row for row in score_rows}
    if len(score_by_key) != len(score_rows):
        raise ValueError("evaluation score identities must be unique")
    expected = {(model, episode) for model in models for episode in episodes}
    if set(score_by_key) != expected:
        raise ValueError("survivor evaluation requires a complete model-by-episode score matrix")
    if any(set(row.losses) != set(dims) for row in score_rows):
        raise ValueError("every evaluation score must carry the exact loss dimensions")
    vectors = _block_vectors(score_rows, model_ids=models, dimensions=dims)
    block_sets = {
        tuple(sorted(vectors[model][dimension]))
        for model in models for dimension in dims
    }
    if len(block_sets) != 1:
        raise ValueError("all models and dimensions must share inference blocks")
    blocks = next(iter(block_sets))
    points = {
        model: {dimension: _mean(vectors[model][dimension].values()) for dimension in dims}
        for model in models
    }
    raw_tests = []
    for left_index, left_id in enumerate(models):
        for right_id in models[left_index + 1:]:
            for dimension in dims:
                result = paired_permutation_test(
                    tuple(vectors[left_id][dimension][key] for key in blocks),
                    tuple(vectors[right_id][dimension][key] for key in blocks),
                    seed=seed,
                )
                raw_tests.append({
                    "label": f"{left_id}::{right_id}::{dimension}",
                    "left_model_id": left_id,
                    "right_model_id": right_id,
                    "dimension": dimension,
                    **result,
                })
    correction = {
        row["label"]: row
        for row in bh_fdr(
            ((row["label"], row["p_value"]) for row in raw_tests if row.get("p_value") is not None),
            alpha=alpha,
        )
    }
    comparisons = [{**row, "fdr": correction.get(row["label"])} for row in raw_tests]
    directions = {
        (row["left_model_id"], row["right_model_id"], row["dimension"]): (
            -1 if float(row["observed_delta"]) < 0 else 1 if float(row["observed_delta"]) > 0 else 0
        )
        for row in comparisons
        if row.get("fdr") and row["fdr"]["rejected_at_alpha"]
    }
    dominance = []
    for left_index, left_id in enumerate(models):
        for right_id in models[left_index + 1:]:
            for better_id, worse_id, sign in ((left_id, right_id, -1), (right_id, left_id, 1)):
                better, worse = points[better_id], points[worse_id]
                witnessed = [
                    key for key in dims
                    if directions.get((left_id, right_id, key)) == sign
                ]
                if all(better[key] <= worse[key] + 1e-12 for key in dims) and witnessed:
                    dominance.append({
                        "dominator_model_id": better_id,
                        "dominated_model_id": worse_id,
                        "significant_dimensions": witnessed,
                    })
    enough = len(blocks) >= min_inference_blocks
    if not enough:
        dominance = []
    dominated = {row["dominated_model_id"] for row in dominance}
    body = {
        "schema": "ztare-worldmodel-paired-survivor-set-v1",
        "dimensions": list(dims),
        "inference_block_ids": list(blocks),
        "inference_block_count": len(blocks),
        "min_inference_blocks": min_inference_blocks,
        "inference_sufficient": enough,
        "alpha": alpha,
        "multiple_testing": "Benjamini-Hochberg over all paired model/dimension comparisons",
        "paired_comparisons": comparisons,
        "point_estimate_frontier_model_ids": _frontier(points),
        "statistical_dominance": dominance,
        "survivor_model_ids": sorted(set(models) - dominated),
        "method": "conservative_paired_fdr_nondomination",
    }
    return {**body, "survivor_set_sha256": stable_sha256(body)}


__all__ = [
    "EvaluationMatrixReceipt",
    "EvaluationScore",
    "WorldModelCandidateView",
    "WorldModelEpisodeView",
    "WorldModelForecastView",
    "compile_evaluation_integrity_receipt",
    "conservative_paired_survivor_set",
    "validate_evaluation_matrix",
]
