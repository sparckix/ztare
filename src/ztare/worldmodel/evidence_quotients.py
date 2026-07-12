"""Substrate-generic evidence quotients over episode logs.

Per-transition mismatch witnesses cannot see laws that live in cross-step or
cross-episode structure. These quotients make that structure queryable for any
grid substrate: ``event_timeline`` groups cell-change events across time
within one episode, and ``episode_contrast`` compares two episodes' states at
a matching step. No game-specific constants or assumptions.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable

from ztare.worldmodel.episode_log import EpisodeLog

_ALLOWED_SPEC_KEYS = frozenset({"changed", "before_in", "after_not_in"})

EVENT_ROW_CAP = 200

_EPISODE_REF_ALIASES = {
    "visible": "raw/episodes/episode_001.jsonl",
    "holdout": "raw/episodes/episode_002.jsonl",
}


def _compile_cell_predicate(spec: dict) -> Callable[[Any, Any], bool]:
    """Compile a declarative cell predicate over (before, after) values.

    Supported forms: ``{"changed": true}``, ``{"before_in": [...]}`` and
    ``{"before_in": [...], "after_not_in": [...]}``. The predicate is only
    ever evaluated on cells that changed; ``changed`` is the trivial form.
    """
    if not isinstance(spec, dict) or not spec:
        raise ValueError(
            "cell_predicate_spec must be a non-empty dict with keys from "
            f"{sorted(_ALLOWED_SPEC_KEYS)}"
        )
    unknown = sorted(set(map(str, spec)) - _ALLOWED_SPEC_KEYS)
    if unknown:
        raise ValueError(
            f"unknown cell_predicate_spec key(s) {unknown}; "
            f"allowed keys: {sorted(_ALLOWED_SPEC_KEYS)}"
        )
    if "changed" in spec and spec["changed"] is not True:
        raise ValueError(
            "cell_predicate_spec key 'changed' only supports true; the "
            "predicate is evaluated on changed cells only"
        )
    before = set(spec["before_in"]) if "before_in" in spec else None
    after_not = set(spec["after_not_in"]) if "after_not_in" in spec else None

    def predicate(before_value: Any, after_value: Any) -> bool:
        if before is not None and before_value not in before:
            return False
        if after_not is not None and after_value in after_not:
            return False
        return True

    return predicate


def event_timeline(log: EpisodeLog, *, cell_predicate_spec: dict) -> dict:
    """Group cell-change events across time within one episode.

    For each transition, collects the cells whose value changed and match
    ``cell_predicate_spec`` (see ``_compile_cell_predicate`` for the three
    supported forms). Returns::

        {"events": [{"t", "a", "cells": [{"row","col","before","after"}], "count"}],
         "counts_by_t": {t: matching-cell count},
         "distinct_cells": <number of distinct (row, col) cells ever matching>,
         "rate_series": [matching-cell count per consecutive transition]}
    """
    predicate = _compile_cell_predicate(cell_predicate_spec)
    events: list[dict] = []
    rate_series: list[int] = []
    counts_by_t: dict[int, int] = {}
    distinct: set[tuple[int, int]] = set()
    for tr in log:
        cells: list[dict] = []
        for r, (row_before, row_after) in enumerate(zip(tr.s, tr.s_next)):
            for c, (before, after) in enumerate(zip(row_before, row_after)):
                if before == after or not predicate(before, after):
                    continue
                cells.append({"row": r, "col": c, "before": before, "after": after})
                distinct.add((r, c))
        rate_series.append(len(cells))
        if cells:
            events.append({"t": tr.t, "a": tr.a, "cells": cells, "count": len(cells)})
            counts_by_t[tr.t] = counts_by_t.get(tr.t, 0) + len(cells)
    return {
        "events": events,
        "counts_by_t": counts_by_t,
        "distinct_cells": len(distinct),
        "rate_series": rate_series,
    }


def _state_at(log: EpisodeLog, at_t: "int | None") -> "tuple[Any, str]":
    rows = log.transitions()
    if not rows:
        return None, "log has no transitions"
    if at_t is None:
        return rows[0].s, ""
    for tr in rows:
        if tr.t == at_t:
            return tr.s, ""
    ts = sorted({tr.t for tr in rows})
    return None, (
        f"no state at t={at_t}; available t spans [{ts[0]}, {ts[-1]}] "
        f"over {len(ts)} recorded steps"
    )


def _color_census(grid) -> dict:
    return dict(Counter(value for row in grid for value in row))


def episode_contrast(
    log_a: EpisodeLog, log_b: EpisodeLog, *, at_t: "int | None" = None
) -> dict:
    """Contrast two episodes' states at a matching step.

    Picks the state at step ``at_t`` from each log (the first recorded state
    when ``at_t`` is None) and reports each state's value census, the census
    delta (b minus a, differing values only), differing row indices, and both
    shapes. When a log has no state at the requested step, the payload says
    which log is missing it and what steps exist — it never guesses.
    """
    state_a, error_a = _state_at(log_a, at_t)
    state_b, error_b = _state_at(log_b, at_t)
    if error_a or error_b:
        return {
            "status": "missing_t",
            "requested_t": at_t,
            "missing_in": [name for name, err in (("a", error_a), ("b", error_b)) if err],
            "errors": {name: err for name, err in (("a", error_a), ("b", error_b)) if err},
        }
    census_a = _color_census(state_a)
    census_b = _color_census(state_b)
    delta = {
        value: census_b.get(value, 0) - census_a.get(value, 0)
        for value in sorted(set(census_a) | set(census_b))
        if census_a.get(value, 0) != census_b.get(value, 0)
    }
    rows_differing = [
        i
        for i in range(max(len(state_a), len(state_b)))
        if (state_a[i] if i < len(state_a) else None)
        != (state_b[i] if i < len(state_b) else None)
    ]
    return {
        "status": "ok",
        "requested_t": at_t,
        "color_census_a": census_a,
        "color_census_b": census_b,
        "census_delta": delta,
        "rows_differing": rows_differing,
        "shape_a": [len(state_a), len(state_a[0]) if state_a else 0],
        "shape_b": [len(state_b), len(state_b[0]) if state_b else 0],
    }


def cap_events(payload: dict, *, cap: int = EVENT_ROW_CAP) -> dict:
    """Bound an event-timeline payload's events list with a loud marker."""
    events = payload.get("events") or []
    if len(events) <= cap:
        return payload
    out = dict(payload)
    out["events"] = events[:cap]
    out["events_truncated"] = (
        f"showing {cap} of {len(events)} event rows; {len(events) - cap} dropped"
    )
    return out


def resolve_episode_ref(project_dir: "Path | str", ref: str) -> Path:
    """Resolve an episode reference to an existing log file, or fail loud.

    Accepts the aliases ``visible``/``holdout`` or a path under the project's
    ``raw/episodes`` directory; an unknown ref raises a ValueError naming the
    valid refs.
    """
    project = Path(project_dir)
    episodes_dir = (project / "raw" / "episodes").resolve()
    valid = sorted(_EPISODE_REF_ALIASES)
    if episodes_dir.is_dir():
        valid += sorted(
            str(p.relative_to(project.resolve())) for p in episodes_dir.glob("*.jsonl")
        )
    text = str(ref or "").strip()
    if not text:
        raise ValueError(f"episode ref is required; valid refs: {valid}")
    path = (project / _EPISODE_REF_ALIASES.get(text, text)).resolve()
    try:
        path.relative_to(episodes_dir)
    except ValueError as exc:
        raise ValueError(
            f"episode ref {text!r} is not under raw/episodes; valid refs: {valid}"
        ) from exc
    if not path.is_file():
        raise ValueError(f"episode ref {text!r} does not exist; valid refs: {valid}")
    return path
