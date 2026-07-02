"""Advisory compression-progress signal for research loops.

Herrmann and Schmidhuber's useful idea is prospective: after a recent
compression improvement, more progress is more plausible; after a long flat
stretch, less so. Their full object is a complexity/runtime profile. Exact
Kolmogorov complexity is not computable for arbitrary project artifacts, so
this module uses values ZTARE can measure: BIC, MDL, compressed size, proof
length, or another lower-is-better description-length proxy, plus optional
effort fields such as wall time, token cost, or search budget.

This does not replace score, novelty, source checks, or loop control. It gives
callers a small read-model primitive they can replay on past runs before using
it to steer new work.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CompressionObservation:
    """One iteration's computable compression proxy.

    ``complexity`` should be a lower-is-better value such as BIC, MDL, or a
    domain-specific description length. ``novelty`` says a move was different,
    but different is not counted as compression unless complexity improves.
    """

    iteration_index: int
    complexity: float | None
    novelty: bool = False
    family: str = ""
    label: str = ""
    effort: float | None = None
    effort_unit: str = ""


@dataclass(frozen=True)
class CompressionProgressDecision:
    usable_observations: int
    family: str
    best_complexity: float | None
    latest_complexity: float | None
    last_drop_iteration: int | None
    stagnation_length: int | None
    compression_drop_count: int
    future_progress_weight: float | None
    recommendation: str
    rationale: str
    best_effort: float | None = None
    latest_effort: float | None = None
    effort_unit: str = ""


DEFAULT_COMPLEXITY_KEYS = (
    "bic",
    "best_bic",
    "latest_bic",
    "mdl",
    "MDL",
    "description_length",
)


def dag_description_length(dag: dict[str, Any]) -> float | None:
    """Two-part MDL (Rissanen) of a probability DAG — a UNIVERSAL lower-is-better complexity proxy every
    project has, so compression progress works beyond the fit/framer domains. L = L(model) + L(data|model):
    the structure costs ``(|nodes|+|edges|)·log2(|nodes|+1)`` bits to describe, and the data cost is the
    outcome's surprisal ``-log2(P(outcome))`` — which drops as the model explains the target better. Adding
    structure only lowers the total when it buys enough explanatory power to pay for its own bits: exactly the
    compression-progress signal. Returns None if the DAG has no usable outcome probability."""
    if not isinstance(dag, dict):
        return None
    nodes = dag.get("nodes") or []
    edges = dag.get("edges") or []
    n = len(nodes)
    if not n:
        return None
    outcome = dag.get("outcome") if isinstance(dag.get("outcome"), dict) else {}
    p = _finite_number(outcome.get("probability"))
    if p is None:
        return None
    p = min(max(p, 1e-6), 1.0 - 1e-9)
    structure_bits = (n + len(edges)) * math.log2(n + 1)
    data_bits = -math.log2(p)
    return round(structure_bits + data_bits, 4)


def observations_from_rows(
    rows: Iterable[dict[str, Any]],
    *,
    complexity_keys: tuple[str, ...] = DEFAULT_COMPLEXITY_KEYS,
) -> list[CompressionObservation]:
    """Convert existing iteration rows into compression observations.

    Callers may pass a narrower ``complexity_keys`` tuple when a project has a
    known field. The default is intentionally conservative: it only looks for
    lower-is-better complexity fields, not ordinary scores.
    """

    observations: list[CompressionObservation] = []
    for offset, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        iteration_index = _row_iteration_index(row, fallback=offset)
        complexity = _first_finite_number(row, complexity_keys)
        observations.append(
            CompressionObservation(
                iteration_index=iteration_index,
                complexity=complexity,
                novelty=_row_has_novelty(row),
                family=_row_complexity_family(row),
                label=str(row.get("label") or row.get("project") or ""),
                effort=_row_effort(row),
                effort_unit=_row_effort_unit(row),
            )
        )
    observations.sort(key=lambda item: item.iteration_index)
    return observations


def evaluate_compression_progress(
    observations: list[CompressionObservation],
    *,
    min_abs_drop: float = 1e-9,
    min_rel_drop: float = 0.0,
    fresh_window: int = 1,
    pivot_after: int = 3,
) -> CompressionProgressDecision:
    """Summarize whether recent iterations are still compressing.

    The returned ``future_progress_weight`` is the paper-inspired proxy
    ``2 ** -stagnation_length``. It is deliberately advisory, not a probability
    claim. It should be used to rank or explain next actions only after replay
    on historical projects.
    """

    usable = [
        item
        for item in sorted(observations, key=lambda row: row.iteration_index)
        if item.complexity is not None and math.isfinite(float(item.complexity))
    ]
    latest_family = ""
    families = {item.family for item in usable if item.family}
    if families:
        latest_family = next((item.family for item in reversed(usable) if item.family), "")
        usable = [item for item in usable if item.family == latest_family]
    if len(usable) < 2:
        return CompressionProgressDecision(
            usable_observations=len(usable),
            family=latest_family,
            best_complexity=float(usable[0].complexity) if usable else None,
            latest_complexity=float(usable[-1].complexity) if usable else None,
            last_drop_iteration=usable[0].iteration_index if usable else None,
            stagnation_length=None,
            compression_drop_count=0,
            future_progress_weight=None,
            recommendation="no_signal",
            rationale="Need at least two finite BIC/MDL-style observations.",
            best_effort=float(usable[0].effort) if usable and usable[0].effort is not None else None,
            latest_effort=float(usable[-1].effort) if usable and usable[-1].effort is not None else None,
            effort_unit=usable[-1].effort_unit if usable else "",
        )

    best = float(usable[0].complexity)
    best_effort = float(usable[0].effort) if usable[0].effort is not None else None
    last_drop_iteration = usable[0].iteration_index
    drop_count = 0

    for item in usable[1:]:
        value = float(item.complexity)
        threshold = max(float(min_abs_drop), abs(best) * float(min_rel_drop))
        if value < best - threshold:
            best = value
            best_effort = float(item.effort) if item.effort is not None else None
            last_drop_iteration = item.iteration_index
            drop_count += 1

    latest = usable[-1]
    latest_complexity = float(latest.complexity)
    latest_effort = float(latest.effort) if latest.effort is not None else None
    stagnation_length = max(0, latest.iteration_index - last_drop_iteration)
    future_progress_weight = 2.0 ** (-stagnation_length)

    tail = [item for item in usable if item.iteration_index > last_drop_iteration]
    tail_has_novelty = any(item.novelty for item in tail)

    if stagnation_length <= fresh_window:
        recommendation = "continue"
        rationale = "Recent iteration improved the compression proxy."
    elif stagnation_length >= pivot_after:
        recommendation = "narrow_or_pivot"
        rationale = (
            f"No compression improvement for {stagnation_length} iterations; "
            "new attempts should narrow the evidence boundary or change route."
        )
    elif tail_has_novelty:
        recommendation = "measure_before_continuing"
        rationale = (
            "Recent moves were different, but did not improve the compression "
            "proxy; measure whether the novelty is useful before continuing."
        )
    else:
        recommendation = "watch"
        rationale = (
            f"No compression improvement for {stagnation_length} iterations, "
            "but the advisory threshold has not been crossed."
        )

    return CompressionProgressDecision(
        usable_observations=len(usable),
        family=latest_family,
        best_complexity=best,
        latest_complexity=latest_complexity,
        last_drop_iteration=last_drop_iteration,
        stagnation_length=stagnation_length,
        compression_drop_count=drop_count,
        future_progress_weight=future_progress_weight,
        recommendation=recommendation,
        rationale=rationale,
        best_effort=best_effort,
        latest_effort=latest_effort,
        effort_unit=latest.effort_unit,
    )


def _row_iteration_index(row: dict[str, Any], *, fallback: int) -> int:
    for key in ("iteration_index", "iteration", "iter", "i"):
        value = row.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value)
    return fallback


def _first_finite_number(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    compression = row.get("compression_progress")
    if isinstance(compression, dict):
        value = compression.get("complexity")
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            candidate = float(value)
            return candidate if math.isfinite(candidate) else None
        if isinstance(value, str):
            try:
                candidate = float(value.strip())
            except ValueError:
                return None
            return candidate if math.isfinite(candidate) else None
    for key in keys:
        value = row.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            candidate = float(value)
        elif isinstance(value, str):
            try:
                candidate = float(value.strip())
            except ValueError:
                continue
        else:
            continue
        if math.isfinite(candidate):
            return candidate
    return None


def _row_complexity_family(row: dict[str, Any]) -> str:
    compression = row.get("compression_progress")
    if isinstance(compression, dict):
        return str(compression.get("family") or "")
    for key in DEFAULT_COMPLEXITY_KEYS:
        if row.get(key) is not None:
            return key
    return ""


def _row_effort(row: dict[str, Any]) -> float | None:
    compression = row.get("compression_progress")
    if isinstance(compression, dict):
        for key in ("effort", "runtime", "wall_clock_seconds", "estimated_cost_usd"):
            value = _finite_number(compression.get(key))
            if value is not None:
                return value
    for key in ("wall_clock_seconds", "runtime_seconds", "estimated_cost_usd", "cost_usd"):
        value = _finite_number(row.get(key))
        if value is not None:
            return value
    return None


def _row_effort_unit(row: dict[str, Any]) -> str:
    compression = row.get("compression_progress")
    if isinstance(compression, dict):
        unit = str(compression.get("effort_unit") or "").strip()
        if unit:
            return unit
    if _finite_number(row.get("wall_clock_seconds")) is not None or _finite_number(row.get("runtime_seconds")) is not None:
        return "seconds"
    if _finite_number(row.get("estimated_cost_usd")) is not None or _finite_number(row.get("cost_usd")) is not None:
        return "usd"
    return ""


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
    elif isinstance(value, str):
        try:
            candidate = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return candidate if math.isfinite(candidate) else None


def _row_has_novelty(row: dict[str, Any]) -> bool:
    for key in ("novelty", "has_novelty", "score_improved", "champion_promoted"):
        if bool(row.get(key)):
            return True
    for key in ("novel_attack_ids", "novel_hinge_ids", "novel_primitive_ids"):
        value = row.get(key)
        if isinstance(value, (list, tuple, set)) and value:
            return True
    return bool(row.get("verified_axioms_added") or 0)
