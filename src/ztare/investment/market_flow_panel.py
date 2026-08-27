"""Cross-sectional probability-current evidence for market-flow challengers.

The earlier market-flow leaf treated a rolling single-security histogram as an
ensemble density.  This module owns a different object: the same-date
distribution of standardized returns across a declared public-price universe.
It exposes finite-volume flux, a same-information Markov rival, and frozen
chronological partitions for a Newton-mode candidate project.
"""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .factor_analysis import PricePoint, load_price_points


CROSS_SECTIONAL_FLOW_PROFILE_SCHEMA = "jaggedthoughts-cross-sectional-market-flow-profile-v1"
CROSS_SECTIONAL_FLOW_EVIDENCE_SCHEMA = "jaggedthoughts-cross-sectional-market-flow-evidence-v2"
CROSS_SECTIONAL_FLOW_SNAPSHOT_SCHEMA = "jaggedthoughts-cross-sectional-market-flow-snapshot-v1"
CROSS_SECTIONAL_FLOW_SETTLEMENT_SCHEMA = "jaggedthoughts-cross-sectional-market-flow-settlement-v1"


def _bin_index(value: float, *, clip: float, bin_count: int) -> int:
    width = 2.0 * clip / bin_count
    bounded = min(clip - 1e-12, max(-clip, value))
    return min(bin_count - 1, max(0, int((bounded + clip) / width)))


def conservative_density_step(
    current_mass: Iterable[float], face_flux: Iterable[float],
) -> tuple[float, ...]:
    """Apply one outward-flux-limited finite-volume step.

    A positive face flux moves probability from the bin on its left to the bin
    on its right.  All outward faces from a bin receive the same scale when
    their requested mass exceeds the bin's available mass.  The result is
    nonnegative and conserves the input mass without a renormalization patch.
    """
    mass = tuple(require_finite(value, "density mass") for value in current_mass)
    flux = [require_finite(value, "density face flux") for value in face_flux]
    if len(mass) < 2 or len(flux) != len(mass) - 1:
        raise ValueError("finite-volume step requires one fewer face than bins")
    if any(value < 0 for value in mass):
        raise ValueError("density mass cannot be negative")
    outgoing = [0.0] * len(mass)
    for face, value in enumerate(flux, start=1):
        outgoing[face - 1 if value >= 0 else face] += abs(value)
    scales = [
        min(1.0, mass[index] / demand) if demand > 0 else 1.0
        for index, demand in enumerate(outgoing)
    ]
    for face, value in enumerate(flux, start=1):
        flux[face - 1] = value * scales[face - 1 if value >= 0 else face]
    updated = list(mass)
    for face, value in enumerate(flux, start=1):
        updated[face - 1] -= value
        updated[face] += value
    if any(value < -1e-12 for value in updated):
        raise AssertionError("outward-flux limiting failed to preserve positivity")
    if abs(sum(updated) - sum(mass)) > 1e-10:
        raise AssertionError("finite-volume step failed to conserve mass")
    return tuple(max(0.0, value) for value in updated)


def _deduplicated_prices(points: Iterable[PricePoint]) -> dict[str, dict[str, PricePoint]]:
    panel: dict[str, dict[str, PricePoint]] = defaultdict(dict)
    for row in points:
        current = panel[row.entity_id].get(row.date_key)
        if current is None or (row.available_at, row.observation_id) > (
            current.available_at, current.observation_id,
        ):
            panel[row.entity_id][row.date_key] = row
    return dict(panel)


def _return_panel(
    prices: Mapping[str, Mapping[str, PricePoint]], dates: list[str],
) -> tuple[dict[str, dict[str, float]], dict[tuple[str, str], tuple[PricePoint, PricePoint]]]:
    returns: dict[str, dict[str, float]] = defaultdict(dict)
    evidence: dict[tuple[str, str], tuple[PricePoint, PricePoint]] = {}
    for previous_date, date in zip(dates, dates[1:]):
        for entity_id, series in prices.items():
            if previous_date not in series or date not in series:
                continue
            previous, current = series[previous_date], series[date]
            returns[date][entity_id] = math.log(current.value / previous.value)
            evidence[(date, entity_id)] = (previous, current)
    return dict(returns), evidence


def _mass(values: Iterable[float], *, clip: float, bin_count: int) -> tuple[float, ...]:
    rows = tuple(values)
    if not rows:
        raise ValueError("density requires at least one state")
    result = [0.0] * bin_count
    for value in rows:
        result[_bin_index(value, clip=clip, bin_count=bin_count)] += 1.0 / len(rows)
    return tuple(result)


def _face_current(
    mass: tuple[float, ...], drift: tuple[float, ...], diffusion: tuple[float, ...],
    *, width: float,
) -> tuple[float, ...]:
    density = tuple(value / width for value in mass)
    faces = []
    for face in range(1, len(mass)):
        velocity = 0.5 * (drift[face - 1] + drift[face])
        upwind = density[face - 1] if velocity >= 0 else density[face]
        diffusion_gradient = (
            diffusion[face] * density[face]
            - diffusion[face - 1] * density[face - 1]
        ) / width
        faces.append(velocity * upwind - diffusion_gradient)
    return tuple(faces)


def _transition_prediction(
    mass: tuple[float, ...], counts: list[list[int]],
) -> tuple[float, ...]:
    prediction = [0.0] * len(mass)
    for source, source_mass in enumerate(mass):
        total = sum(counts[source])
        if total == 0:
            prediction[source] += source_mass
            continue
        for target, count in enumerate(counts[source]):
            prediction[target] += source_mass * count / total
    return tuple(prediction)


def _vector_mae(left: Iterable[float], right: Iterable[float]) -> float:
    pairs = tuple(zip(left, right, strict=True))
    return mean(abs(a - b) for a, b in pairs)


def compile_cross_sectional_flow_evidence(
    profile_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Compile point-identified panel episodes without evaluating a candidate."""
    source = Path(profile_path).expanduser().resolve()
    profile = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(profile, Mapping) or profile.get("schema") != CROSS_SECTIONAL_FLOW_PROFILE_SCHEMA:
        raise ValueError(f"market-flow profile schema must be {CROSS_SECTIONAL_FLOW_PROFILE_SCHEMA}")
    root = Path(workspace).expanduser().resolve()
    raw_as_of = profile.get("as_of")
    if raw_as_of == "latest_source_run":
        import json
        try:
            raw_as_of = json.loads((root / "data" / "latest_source_run.json").read_text(
                encoding="utf-8",
            ))["as_of"]
        except (KeyError, OSError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("cross-sectional flow requires a completed source refresh") from error
    as_of = canonical_timestamp(raw_as_of, "cross-sectional flow as_of")
    mode = require_text(profile.get("mode"), "cross-sectional flow mode")
    if mode not in {"point_in_time", "retrospective_retrieval_diagnostic"}:
        raise ValueError("cross-sectional flow mode is unsupported")
    entities = tuple(require_text(value, "cross-sectional entity") for value in profile.get("entity_ids", []))
    if len(entities) < 5 or len(set(entities)) != len(entities):
        raise ValueError("cross-sectional flow requires at least five unique declared entities")
    lookback = int(profile.get("lookback", 252))
    bin_count = int(profile.get("bin_count", 9))
    clip = require_finite(profile.get("state_clip", 4.0), "cross-sectional state_clip")
    stride = int(profile.get("evaluation_stride", 5))
    min_cross_section = int(profile.get("min_cross_section", 25))
    min_history_fraction = require_finite(
        profile.get("min_history_fraction", 0.70), "cross-sectional min_history_fraction",
    )
    transaction_cost_bps = require_finite(
        profile.get("transaction_cost_bps", 5.0), "cross-sectional transaction_cost_bps",
    )
    visible_fraction = require_finite(profile.get("visible_fraction", 0.50), "visible_fraction")
    holdout_fraction = require_finite(profile.get("holdout_fraction", 0.25), "holdout_fraction")
    if (
        lookback < 60 or bin_count < 5 or clip <= 0 or stride < 1
        or min_cross_section < 5 or not 0.5 <= min_history_fraction <= 1.0
        or transaction_cost_bps < 0
        or not 0.3 <= visible_fraction <= 0.7
        or not 0.1 <= holdout_fraction <= 0.4
        or visible_fraction + holdout_fraction >= 0.9
    ):
        raise ValueError("cross-sectional flow bounds are invalid")

    points = load_price_points(
        root / "data" / "observations.csv", as_of=as_of,
        metric_id="adjusted_price",
    )
    prices = _deduplicated_prices(row for row in points if row.entity_id in set(entities))
    missing = sorted(set(entities) - set(prices))
    if missing:
        raise ValueError(f"cross-sectional flow entities lack prices: {missing}")
    dates = sorted({date for series in prices.values() for date in series})
    returns, return_evidence = _return_panel(prices, dates)
    width = 2.0 * clip / bin_count
    episodes: list[dict[str, Any]] = []
    source_availability: list[dict[str, str]] = []
    chronology_exclusions = 0
    for date_index in range(lookback + 1, len(dates) - 1, stride):
        issued_date, outcome_date = dates[date_index], dates[date_index + 1]
        history_dates = dates[date_index - lookback:date_index + 1]
        eligible = tuple(sorted(
            entity_id for entity_id in entities
            if entity_id in returns.get(issued_date, {})
            and entity_id in returns.get(outcome_date, {})
            and sum(entity_id in returns.get(date, {}) for date in history_dates)
            >= len(history_dates) * min_history_fraction
        ))
        if len(eligible) < min_cross_section:
            continue
        historical_values = [
            returns[date][entity_id]
            for date in history_dates for entity_id in eligible
            if entity_id in returns.get(date, {})
        ]
        center, scale = mean(historical_values), pstdev(historical_values)
        if scale <= 1e-12:
            continue

        def state(date: str, entity_id: str) -> float:
            return min(clip, max(-clip, (returns[date][entity_id] - center) / scale))

        current_states = tuple(state(issued_date, entity_id) for entity_id in eligible)
        outcome_states = tuple(state(outcome_date, entity_id) for entity_id in eligible)
        current_mass = _mass(current_states, clip=clip, bin_count=bin_count)
        actual_mass = _mass(outcome_states, clip=clip, bin_count=bin_count)
        increments: list[list[float]] = [[] for _ in range(bin_count)]
        transition_counts = [[0] * bin_count for _ in range(bin_count)]
        used_points: dict[str, PricePoint] = {}
        outcome_points: dict[str, PricePoint] = {}
        for left_date, right_date in zip(history_dates, history_dates[1:]):
            for entity_id in eligible:
                if entity_id not in returns.get(left_date, {}) or entity_id not in returns.get(right_date, {}):
                    continue
                left, right = state(left_date, entity_id), state(right_date, entity_id)
                source_bin = _bin_index(left, clip=clip, bin_count=bin_count)
                target_bin = _bin_index(right, clip=clip, bin_count=bin_count)
                increments[source_bin].append(right - left)
                transition_counts[source_bin][target_bin] += 1
                for evidence_date in (left_date, right_date):
                    for point in return_evidence[(evidence_date, entity_id)]:
                        used_points[point.observation_id] = point
        for entity_id in eligible:
            for point in return_evidence[(outcome_date, entity_id)]:
                outcome_points[point.observation_id] = point
        drift = tuple(mean(values) if values else 0.0 for values in increments)
        diffusion = tuple(
            0.5 * mean(value * value for value in values) if values else 0.0
            for values in increments
        )
        face_current = _face_current(current_mass, drift, diffusion, width=width)
        linear_prediction = conservative_density_step(current_mass, face_current)
        markov_prediction = _transition_prediction(current_mass, transition_counts)
        evidence_available = all(
            timestamp_key(row.available_at) <= timestamp_key(issued_date + "T23:59:59Z")
            for row in used_points.values()
        )
        if mode == "point_in_time" and not evidence_available:
            chronology_exclusions += 1
            continue
        source_refs = sorted({
            row.source_ref for row in (*used_points.values(), *outcome_points.values())
        })
        observation_ids = tuple(sorted(used_points))
        outcome_observation_ids = tuple(sorted(outcome_points))
        feature_observation_ids_sha256 = stable_sha256(observation_ids)
        feature_available_at = max(row.available_at for row in used_points.values())
        source_availability.append({
            "source_id": feature_observation_ids_sha256,
            "available_at": feature_available_at,
            "as_of": issued_date + "T23:59:59Z",
        })
        episodes.append({
            "episode_id": f"panel:{issued_date}:{outcome_date}",
            "issued_at": issued_date + "T23:59:59Z",
            "end_at": outcome_date + "T23:59:59Z",
            "chronology_ok": evidence_available,
            "entity_count": len(eligible),
            "entity_ids_sha256": stable_sha256(eligible),
            "center": center,
            "scale": scale,
            "current_mean_return": mean(returns[issued_date][entity_id] for entity_id in eligible),
            "actual_next_mean_return": mean(returns[outcome_date][entity_id] for entity_id in eligible),
            "current_mass": list(current_mass),
            "raw_face_current": list(face_current),
            "linear_current_mass": list(linear_prediction),
            "markov_mass": list(markov_prediction),
            "transition_counts": transition_counts,
            "actual_next_mass": list(actual_mass),
            "source_refs": source_refs,
            "observation_ids_sha256": feature_observation_ids_sha256,
            "feature_observation_ids_sha256": feature_observation_ids_sha256,
            "feature_available_at": feature_available_at,
            "outcome_observation_ids_sha256": stable_sha256(outcome_observation_ids),
        })
    if len(episodes) < 40:
        raise ValueError("cross-sectional flow produced fewer than 40 eligible episodes")
    visible_end = max(1, int(len(episodes) * visible_fraction))
    holdout_end = max(visible_end + 1, int(len(episodes) * (visible_fraction + holdout_fraction)))
    partitions = {
        "visible": episodes[:visible_end],
        "holdout": episodes[visible_end:holdout_end],
        "farther_tail": episodes[holdout_end:],
    }
    if any(len(rows) < 10 for rows in partitions.values()):
        raise ValueError("each cross-sectional flow partition requires at least ten episodes")
    control_metrics = {
        name: mean(
            _vector_mae(row[key], row["actual_next_mass"])
            for row in episodes
        )
        for name, key in (
            ("persistence", "current_mass"),
            ("linear_probability_current", "linear_current_mass"),
            ("empirical_markov", "markov_mass"),
        )
    }
    integrity = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay",
        # The price construction is deterministic, while present-day universe
        # membership cannot establish a historical membership information set.
        generation_processes=("unknown",),
        source_availability_rows=source_availability,
    )
    body: dict[str, Any] = {
        "schema": CROSS_SECTIONAL_FLOW_EVIDENCE_SCHEMA,
        "experiment_id": require_text(profile.get("experiment_id"), "cross-sectional experiment_id"),
        "as_of": as_of,
        "mode": mode,
        "authority": "experiment_only",
        "profile_sha256": stable_sha256({**profile, "as_of": as_of}),
        "universe": {
            "entity_ids": list(entities),
            "entity_ids_sha256": stable_sha256(entities),
            "selection_epoch": require_text(profile.get("universe_selection_epoch"), "universe selection epoch"),
            "survivorship_safe": False,
        },
        "bin_count": bin_count,
        "state_clip": clip,
        "bin_centers": [-clip + (index + 0.5) * width for index in range(bin_count)],
        "lookback": lookback,
        "evaluation_stride": stride,
        "transaction_cost_bps": transaction_cost_bps,
        "chronology_exclusion_count": chronology_exclusions,
        "episode_count": len(episodes),
        "partition_counts": {name: len(rows) for name, rows in partitions.items()},
        "feature_observation_ids_sha256": stable_sha256([
            row["feature_observation_ids_sha256"] for row in episodes
        ]),
        "outcome_observation_ids_sha256": stable_sha256([
            row["outcome_observation_ids_sha256"] for row in episodes
        ]),
        "source_refs": sorted({
            source_ref for row in episodes for source_ref in row["source_refs"]
        }),
        "control_mean_absolute_density_error": control_metrics,
        "evaluation_integrity": integrity,
        "partitions": partitions,
        "use_boundary": (
            "The panel is selected from the current public-price workspace and is survivorship-exposed. "
            "It can reject or refine a transition family, not establish historical or prospective alpha."
        ),
    }
    return {**body, "evidence_sha256": stable_sha256(body)}


def compile_cross_sectional_flow_snapshot(
    profile_path: str | Path, *, workspace: str | Path, sealed_at: str,
) -> dict[str, Any]:
    """Freeze the latest fully visible panel state before its next-session outcome."""
    source = Path(profile_path).expanduser().resolve()
    profile = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(profile, Mapping) or profile.get("schema") != CROSS_SECTIONAL_FLOW_PROFILE_SCHEMA:
        raise ValueError(f"market-flow profile schema must be {CROSS_SECTIONAL_FLOW_PROFILE_SCHEMA}")
    root = Path(workspace).expanduser().resolve()
    raw_as_of = profile.get("as_of")
    if raw_as_of == "latest_source_run":
        import json
        try:
            raw_as_of = json.loads((root / "data" / "latest_source_run.json").read_text(
                encoding="utf-8",
            ))["as_of"]
        except (KeyError, OSError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("cross-sectional flow requires a completed source refresh") from error
    as_of = canonical_timestamp(raw_as_of, "cross-sectional flow as_of")
    seal = canonical_timestamp(sealed_at, "cross-sectional flow sealed_at")
    if timestamp_key(seal) < timestamp_key(as_of):
        raise ValueError("cross-sectional flow seal cannot precede its source cutoff")
    entities = tuple(require_text(value, "cross-sectional entity") for value in profile.get("entity_ids", []))
    lookback = int(profile.get("lookback", 252))
    bin_count = int(profile.get("bin_count", 9))
    clip = require_finite(profile.get("state_clip", 4.0), "cross-sectional state_clip")
    min_cross_section = int(profile.get("min_cross_section", 25))
    min_history_fraction = require_finite(
        profile.get("min_history_fraction", 0.70), "cross-sectional min_history_fraction",
    )
    max_state_staleness_days = int(profile.get("max_state_staleness_days", 4))
    if len(entities) < 5 or len(set(entities)) != len(entities):
        raise ValueError("cross-sectional flow requires at least five unique declared entities")
    if (
        lookback < 60 or bin_count < 5 or clip <= 0 or min_cross_section < 5
        or max_state_staleness_days < 0
    ):
        raise ValueError("cross-sectional flow snapshot bounds are invalid")

    points = load_price_points(
        root / "data" / "observations.csv", as_of=as_of,
        metric_id="adjusted_price", entity_ids=entities,
    )
    prices = _deduplicated_prices(points)
    dates = sorted({date for series in prices.values() for date in series})
    returns, return_evidence = _return_panel(prices, dates)
    return_dates = sorted(returns)
    if len(return_dates) < lookback + 1:
        raise ValueError("cross-sectional flow snapshot lacks its declared history")
    skipped_state_dates: list[dict[str, Any]] = []
    state_date = ""
    history_dates: list[str] = []
    eligible: tuple[str, ...] = ()
    for state_index in range(len(return_dates) - 1, lookback - 1, -1):
        candidate_date = return_dates[state_index]
        candidate_history = return_dates[state_index - lookback:state_index + 1]
        candidate_eligible = tuple(sorted(
            entity_id for entity_id in entities
            if entity_id in returns[candidate_date]
            and sum(
                entity_id in returns.get(date, {}) for date in candidate_history
            ) >= len(candidate_history) * min_history_fraction
        ))
        if len(candidate_eligible) >= min_cross_section:
            state_date = candidate_date
            history_dates = candidate_history
            eligible = candidate_eligible
            break
        skipped_state_dates.append({
            "state_date": candidate_date,
            "eligible_entity_count": len(candidate_eligible),
        })
    if not state_date:
        raise ValueError("cross-sectional flow snapshot has too few eligible entities")
    state_staleness_days = (
        timestamp_key(as_of).date()
        - timestamp_key(f"{state_date}T23:59:59Z").date()
    ).days
    if state_staleness_days > max_state_staleness_days:
        raise ValueError("cross-sectional flow snapshot lacks a current complete state")
    historical_values = [
        returns[date][entity_id]
        for date in history_dates for entity_id in eligible
        if entity_id in returns.get(date, {})
    ]
    center, scale = mean(historical_values), pstdev(historical_values)
    if scale <= 1e-12:
        raise ValueError("cross-sectional flow snapshot has zero return dispersion")

    def state(date: str, entity_id: str) -> float:
        return min(clip, max(-clip, (returns[date][entity_id] - center) / scale))

    width = 2.0 * clip / bin_count
    current_mass = _mass(
        (state(state_date, entity_id) for entity_id in eligible),
        clip=clip, bin_count=bin_count,
    )
    increments: list[list[float]] = [[] for _ in range(bin_count)]
    transition_counts = [[0] * bin_count for _ in range(bin_count)]
    used_points: dict[str, PricePoint] = {}
    for left_date, right_date in zip(history_dates, history_dates[1:]):
        for entity_id in eligible:
            if entity_id not in returns.get(left_date, {}) or entity_id not in returns.get(right_date, {}):
                continue
            left, right = state(left_date, entity_id), state(right_date, entity_id)
            source_bin = _bin_index(left, clip=clip, bin_count=bin_count)
            target_bin = _bin_index(right, clip=clip, bin_count=bin_count)
            increments[source_bin].append(right - left)
            transition_counts[source_bin][target_bin] += 1
            for evidence_date in (left_date, right_date):
                for point in return_evidence[(evidence_date, entity_id)]:
                    used_points[point.observation_id] = point
    drift = tuple(mean(values) if values else 0.0 for values in increments)
    diffusion = tuple(
        0.5 * mean(value * value for value in values) if values else 0.0
        for values in increments
    )
    raw_face_current = _face_current(current_mass, drift, diffusion, width=width)
    feature_available_at = max(row.available_at for row in used_points.values())
    if timestamp_key(feature_available_at) > timestamp_key(seal):
        raise ValueError("cross-sectional flow snapshot includes post-seal evidence")
    body: dict[str, Any] = {
        "schema": CROSS_SECTIONAL_FLOW_SNAPSHOT_SCHEMA,
        "experiment_id": require_text(profile.get("experiment_id"), "cross-sectional experiment_id"),
        "as_of": as_of,
        "sealed_at": seal,
        "state_date": state_date,
        "state_date_selection": {
            "rule": "latest_visible_date_meeting_declared_cross_section",
            "latest_visible_date": return_dates[-1],
            "state_staleness_days": state_staleness_days,
            "max_state_staleness_days": max_state_staleness_days,
            "skipped_incomplete_dates": skipped_state_dates,
        },
        "authority": "experiment_only",
        "capital_authority": False,
        "estimand": (
            "next-session density of standardized one-session returns for the exact frozen cohort; "
            "linked observable is that cohort's equal-weight mean log return"
        ),
        "profile_sha256": stable_sha256({**profile, "as_of": as_of}),
        "entity_ids": list(eligible),
        "entity_ids_sha256": stable_sha256(eligible),
        "feature_available_at": feature_available_at,
        "feature_observation_ids_sha256": stable_sha256(tuple(sorted(used_points))),
        "source_refs": sorted({row.source_ref for row in used_points.values()}),
        "center": center,
        "scale": scale,
        "bin_count": bin_count,
        "state_clip": clip,
        "bin_centers": [-clip + (index + 0.5) * width for index in range(bin_count)],
        "current_mass": list(current_mass),
        "raw_face_current": list(raw_face_current),
        "markov_mass": list(_transition_prediction(current_mass, transition_counts)),
        "transition_counts": transition_counts,
    }
    return {**body, "snapshot_sha256": stable_sha256(body)}


def settle_cross_sectional_flow_snapshot(
    snapshot: Mapping[str, Any], *, workspace: str | Path, evaluated_at: str,
) -> dict[str, Any]:
    """Bind the first complete exact-cohort market session after a frozen snapshot."""
    frozen = dict(snapshot)
    declared = str(frozen.pop("snapshot_sha256", ""))
    if frozen.get("schema") != CROSS_SECTIONAL_FLOW_SNAPSHOT_SCHEMA or stable_sha256(frozen) != declared:
        raise ValueError("cross-sectional flow snapshot identity mismatch")
    as_of = canonical_timestamp(evaluated_at, "cross-sectional settlement evaluated_at")
    if timestamp_key(as_of) <= timestamp_key(str(snapshot["sealed_at"])):
        raise ValueError("cross-sectional flow settlement must follow its seal")
    entity_ids = tuple(str(value) for value in snapshot["entity_ids"])
    points = load_price_points(
        Path(workspace).expanduser().resolve() / "data" / "observations.csv",
        as_of=as_of, metric_id="adjusted_price", entity_ids=entity_ids,
    )
    prices = _deduplicated_prices(points)
    state_date = str(snapshot["state_date"])
    outcome_dates = sorted({
        date for series in prices.values() for date in series if date > state_date
    })
    outcome_date = next((
        date for date in outcome_dates
        if all(state_date in prices.get(entity_id, {}) and date in prices.get(entity_id, {})
               for entity_id in entity_ids)
    ), None)
    base = {
        "schema": CROSS_SECTIONAL_FLOW_SETTLEMENT_SCHEMA,
        "experiment_id": str(snapshot["experiment_id"]),
        "snapshot_sha256": declared,
        "evaluated_at": as_of,
        "authority": "experiment_only",
        "capital_authority": False,
    }
    if outcome_date is None:
        body = {**base, "status": "pending", "source_refs": []}
        return {**body, "settlement_sha256": stable_sha256(body)}
    outcome_points = [prices[entity_id][outcome_date] for entity_id in entity_ids]
    outcome_available_at = max(row.available_at for row in outcome_points)
    if timestamp_key(outcome_available_at) <= timestamp_key(str(snapshot["sealed_at"])):
        raise ValueError("cross-sectional flow outcome was already available at its seal")
    returns = [
        math.log(prices[entity_id][outcome_date].value / prices[entity_id][state_date].value)
        for entity_id in entity_ids
    ]
    clip, bin_count = float(snapshot["state_clip"]), int(snapshot["bin_count"])
    actual_mass = _mass(
        (min(clip, max(-clip, (value - float(snapshot["center"])) / float(snapshot["scale"])))
         for value in returns),
        clip=clip, bin_count=bin_count,
    )
    body = {
        **base,
        "status": "settled",
        "outcome_date": outcome_date,
        "outcome_observed_at": max(row.observed_at for row in outcome_points),
        "outcome_available_at": outcome_available_at,
        "actual_next_mass": list(actual_mass),
        "actual_next_mean_return": mean(returns),
        "outcome_observation_ids_sha256": stable_sha256(tuple(sorted(
            row.observation_id for row in outcome_points
        ))),
        "source_refs": sorted({row.source_ref for row in outcome_points}),
    }
    return {**body, "settlement_sha256": stable_sha256(body)}


__all__ = [
    "CROSS_SECTIONAL_FLOW_EVIDENCE_SCHEMA",
    "CROSS_SECTIONAL_FLOW_PROFILE_SCHEMA",
    "CROSS_SECTIONAL_FLOW_SETTLEMENT_SCHEMA",
    "CROSS_SECTIONAL_FLOW_SNAPSHOT_SCHEMA",
    "compile_cross_sectional_flow_evidence",
    "compile_cross_sectional_flow_snapshot",
    "conservative_density_step",
    "settle_cross_sectional_flow_snapshot",
]
