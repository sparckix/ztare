"""Daemon-safe frontier-state persistence for the Research Director live
co-drive loop (RD-1.12, 2026-05-02).

Tracks per-project:
  - route_ranking : list[dict]   — currently-considered routes ordered by
                                    posterior viability; mutated by demote/promote.
  - active_escapes : list[dict]   — alien-math / cold-shot reframes the RD
                                    has authorized as live falsification surfaces.
  - champion_meaning : str | None — the current champion's interpretive label
                                    (e.g. "β=1/2 Brownian", "α·ln(d) VC-class").
                                    Updated when champion shifts.
  - obstruction_counters : dict   — {route_id: int_consecutive_obstructions}
                                    used for "obstruction repeated 2x → fork" rule.
  - last_iter_observed : int | None — highest iter index the runner has consumed.
  - pending_actions : list[dict]  — actions the policy module has queued but
                                    the daemon hasn't executed yet (audit trail).
  - history : list[dict]          — append-only log of state transitions.

Storage: ztare_workspace/frontier_state/<project_slug>.json (atomic
write via .tmp + rename). Mirrors spend_tracker + agent_utilization_tracker
patterns so the existing rsync ownership rules apply (Tree-B, VPS-owned,
laptop pulls read-only).

This module owns the schema + IO; it does NOT make policy decisions.
The runner (frontier_runner.py) and the policy dispatcher
(iter_action_policy.py) read/write through these primitives.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STATE_ROOT = Path("ztare_workspace/frontier_state")
log = logging.getLogger(__name__)

_VALID_SLUG_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")


@dataclass
class RouteEntry:
    """One candidate route in the current frontier ranking."""
    route_id: str
    label: str
    rank: int                    # 1 is the most-promising; ascending
    posterior: float = 0.0       # 0..1 viability estimate
    obstruction_count: int = 0   # consecutive obstructions on this route
    last_event_utc: Optional[str] = None
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class EscapeEntry:
    """An alien-math reframe / cold-shot escape route the RD authorized."""
    escape_id: str
    label: str
    proposed_by: str             # "cold_shot:gpt5.5" / "operator" / "rd_runner"
    status: str                  # "open" | "tested" | "refuted" | "promoted"
    discriminator: Optional[str] = None
    proposed_utc: Optional[str] = None
    resolved_utc: Optional[str] = None


@dataclass
class FrontierState:
    """Full per-project frontier state."""
    project_slug: str
    schema_version: int = 1
    route_ranking: list[dict] = field(default_factory=list)
    active_escapes: list[dict] = field(default_factory=list)
    champion_meaning: Optional[str] = None
    obstruction_counters: dict = field(default_factory=dict)
    last_iter_observed: Optional[int] = None
    pending_actions: list[dict] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    updated_utc: Optional[str] = None


def _validate_slug(project_slug: str) -> None:
    if not _VALID_SLUG_RE.match(project_slug):
        raise ValueError(
            f"invalid project_slug {project_slug!r}: must match "
            f"{_VALID_SLUG_RE.pattern}"
        )


def _state_path(project_slug: str) -> Path:
    _validate_slug(project_slug)
    return STATE_ROOT / f"{project_slug}.json"


def load_state(project_slug: str) -> FrontierState:
    """Return the persisted frontier state, or a fresh empty state if none."""
    path = _state_path(project_slug)
    if not path.exists():
        return FrontierState(project_slug=project_slug)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return FrontierState(
            project_slug=data.get("project_slug", project_slug),
            schema_version=int(data.get("schema_version", 1)),
            route_ranking=list(data.get("route_ranking", [])),
            active_escapes=list(data.get("active_escapes", [])),
            champion_meaning=data.get("champion_meaning"),
            obstruction_counters=dict(data.get("obstruction_counters", {})),
            last_iter_observed=data.get("last_iter_observed"),
            pending_actions=list(data.get("pending_actions", [])),
            history=list(data.get("history", [])),
            updated_utc=data.get("updated_utc"),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("frontier state %s unreadable (%s); starting fresh",
                    path, exc)
        return FrontierState(project_slug=project_slug)


def save_state(state: FrontierState, *, history_append: Optional[dict] = None) -> Path:
    """Persist state atomically. Optionally append a history row capturing
    what just changed (caller supplies the dict; minimum: {ts, event, ...})."""
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    state.updated_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if history_append is not None:
        history_row = dict(history_append)
        history_row.setdefault("ts", state.updated_utc)
        state.history.append(history_row)
        # Cap history at 500 rows to bound the file; oldest dropped first.
        if len(state.history) > 500:
            state.history = state.history[-500:]
    payload = asdict(state)
    path = _state_path(state.project_slug)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


# ── Policy-side mutation helpers ─────────────────────────────────────

def update_route_ranking(state: FrontierState,
                         routes: list[RouteEntry],
                         reason: str = "") -> FrontierState:
    """Replace the route_ranking with a new ordered list. Reason logged."""
    state.route_ranking = [asdict(r) for r in sorted(routes, key=lambda r: r.rank)]
    save_state(state, history_append={
        "event": "route_ranking_updated",
        "n_routes": len(routes),
        "top_route": routes[0].route_id if routes else None,
        "reason": reason,
    })
    return state


def increment_obstruction(state: FrontierState, route_id: str,
                          reason: str = "") -> int:
    """Increment the consecutive-obstruction counter for a route. Returns
    the new count. Used by the policy "obstruction repeated 2x → fork" rule."""
    counters = state.obstruction_counters
    new_count = int(counters.get(route_id, 0)) + 1
    counters[route_id] = new_count
    state.obstruction_counters = counters
    # Also tick the route entry if it's in the ranking.
    for r in state.route_ranking:
        if r.get("route_id") == route_id:
            r["obstruction_count"] = new_count
            r["last_event_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    save_state(state, history_append={
        "event": "obstruction_incremented",
        "route_id": route_id,
        "new_count": new_count,
        "reason": reason,
    })
    return new_count


def reset_obstruction(state: FrontierState, route_id: str,
                      reason: str = "") -> FrontierState:
    """Zero the obstruction counter for a route (e.g. after a successful
    iter on that route)."""
    if route_id in state.obstruction_counters:
        del state.obstruction_counters[route_id]
    for r in state.route_ranking:
        if r.get("route_id") == route_id:
            r["obstruction_count"] = 0
    save_state(state, history_append={
        "event": "obstruction_reset",
        "route_id": route_id,
        "reason": reason,
    })
    return state


def set_champion_meaning(state: FrontierState, label: str,
                         reason: str = "") -> FrontierState:
    """Update the champion's interpretive label. Used when champion shifts
    (e.g. when a new form passes more gates than the prior champion)."""
    prior = state.champion_meaning
    state.champion_meaning = label
    save_state(state, history_append={
        "event": "champion_meaning_updated",
        "from": prior,
        "to": label,
        "reason": reason,
    })
    return state


def add_escape(state: FrontierState, escape: EscapeEntry,
               reason: str = "") -> FrontierState:
    """Register an alien-math reframe / cold-shot escape as an active
    falsification surface."""
    state.active_escapes.append(asdict(escape))
    save_state(state, history_append={
        "event": "escape_added",
        "escape_id": escape.escape_id,
        "proposed_by": escape.proposed_by,
        "reason": reason,
    })
    return state


def resolve_escape(state: FrontierState, escape_id: str,
                   verdict: str, reason: str = "") -> FrontierState:
    """Mark an escape as tested/refuted/promoted. verdict ∈ {tested,
    refuted, promoted}."""
    if verdict not in ("tested", "refuted", "promoted"):
        raise ValueError(f"unknown verdict: {verdict!r}")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    found = False
    for e in state.active_escapes:
        if e.get("escape_id") == escape_id:
            e["status"] = verdict
            e["resolved_utc"] = now
            found = True
            break
    if not found:
        log.warning("resolve_escape: escape_id %r not found in state for %s",
                    escape_id, state.project_slug)
    save_state(state, history_append={
        "event": "escape_resolved",
        "escape_id": escape_id,
        "verdict": verdict,
        "reason": reason,
    })
    return state


def set_last_iter(state: FrontierState, iter_index: int) -> FrontierState:
    """Mark the highest iter index the runner has consumed (idempotency
    cursor for the watch loop)."""
    state.last_iter_observed = int(iter_index)
    save_state(state, history_append={
        "event": "iter_cursor_advanced",
        "iter": iter_index,
    })
    return state


def queue_action(state: FrontierState, action: dict) -> FrontierState:
    """Append a pending action the daemon will execute on its next tick.
    Action shape: {action_kind, params, reason, ts (auto)}."""
    row = dict(action)
    row.setdefault("ts", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    state.pending_actions.append(row)
    save_state(state, history_append={
        "event": "action_queued",
        "kind": row.get("action_kind"),
        "reason": row.get("reason"),
    })
    return state


def pop_pending_actions(state: FrontierState) -> list[dict]:
    """Return + clear the pending action queue. Caller is responsible for
    executing the actions and recording outcomes via history."""
    actions = list(state.pending_actions)
    state.pending_actions = []
    save_state(state, history_append={
        "event": "actions_dequeued",
        "n": len(actions),
    })
    return actions
