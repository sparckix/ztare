"""Agent-CLI utilization tracker — % capacity primitive (2026-05-02).

Companion to `spend_tracker.py`. Where spend_tracker.py answers "have we
spent more than the daily $-cap?", this module answers "have we used
more than X% of the daily Claude-Code / Codex / Gemini-CLI capacity?".

Why two trackers:
  USD spend is a public dollar dimension. Agent-CLI utilization is a
  capacity dimension — your Claude Code or Codex subscription has
  practical hourly/daily caps regardless of API cost (e.g., quota,
  context-window budget, time-of-attention budget). A long Claude-Code
  session at marginal cost still consumes capacity that other roles
  could have used. Tracking both prevents one role (e.g., a chatty
  Research Director) from quietly starving another (e.g., an overnight
  Manager).

What it tracks per session-window:
  - duration_seconds (wall-clock time the agent CLI was running)
  - output_tokens / input_tokens (when reported by the CLI's usage telemetry)
  - turn_count (number of agent steps; useful when token telemetry is missing)
  - role_id (which role's mandate authorized this work)
  - agent_cli ("claude" | "codex" | "gemini" | other)
  - session_id (typed audit trail)

Storage layout (mirrors spend_tracker for cron/Orbit symmetry):
  ztare_workspace/agent_utilization/<YYYY-MM-DD>.json
    {
      "date": "2026-05-02",
      "entries": [ {timestamp_utc, role_id, agent_cli, duration_seconds, ...}, ... ],
      "totals": {
        "by_role": {"manager": {"duration_seconds": 1234, "output_tokens": 56789, ...}, ...},
        "by_cli":  {"claude":  {"duration_seconds": 9876, ...}, ...},
        "by_role_cli": {"manager:claude": {...}, ...}
      }
    }

Cap configuration:
  Read from org/roles/<role>.yaml under the new `agent_utilization:` block,
  with fallback to the module-level defaults below. Same load-via-registry
  pattern as spend_tracker._role_budget.

Three primitives:
  - record_agent_session(...)  : append a session-end entry
  - check_utilization_allows(...) : pre-flight (would the next session exceed cap?)
  - get_utilization_pct(...)   : fraction-of-cap consumed (for warnings + UI)

Usage:

    from src.ztare.supervisor.agent_utilization_tracker import (
        record_agent_session, check_utilization_allows, get_utilization_pct,
    )

    # Before launching a new agent session:
    if not check_utilization_allows(
        role_id="research_director",
        agent_cli="claude",
        estimated_seconds=600,
    ):
        escalate("Agent-utilization gate triggered")
        return

    # After the session ends:
    record_agent_session(
        role_id="research_director",
        agent_cli="claude",
        duration_seconds=587.3,
        output_tokens=12450,
        input_tokens=4200,
        turn_count=14,
        session_id="rd-2026-05-02-1547",
    )

    # For monitoring:
    pct = get_utilization_pct(role_id="research_director", agent_cli="claude")
    # → 0.62  (62% of daily cap consumed)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


# ── Fallback caps (when role yaml has no agent_utilization block) ─────
# Per-role-per-day capacity defaults. Tuned so a single chatty role can
# spend ~3 hours of Claude-Code time per day without tripping the warn
# threshold; absolute ceiling at 5 hours/day to catch infinite-loop bugs.
DEFAULT_DAILY_DURATION_SECONDS = 3 * 3600       # 3 hours/day
DEFAULT_DAILY_OUTPUT_TOKENS = 500_000           # 500k output tokens/day
DEFAULT_DAILY_TURN_COUNT = 200                  # 200 agent steps/day
DEFAULT_SESSION_DURATION_SECONDS = 90 * 60      # 90 min single session
DEFAULT_ABSOLUTE_DURATION_SECONDS = 5 * 3600    # 5 hours/day hard ceiling
DEFAULT_WARN_THRESHOLD_FRAC = 0.80

UTIL_ROOT = Path("ztare_workspace/agent_utilization")

log = logging.getLogger(__name__)


# ── Data shape ────────────────────────────────────────────────────────

@dataclass
class AgentSessionEntry:
    """One agent-CLI session window. duration_seconds is required;
    token counts are best-effort (some CLIs do not emit usage)."""
    timestamp_utc: str
    role_id: str
    agent_cli: str
    duration_seconds: float
    output_tokens: Optional[int] = None
    input_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None
    turn_count: Optional[int] = None
    session_id: Optional[str] = None
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class UtilizationCaps:
    """Per-role capacity limits, loaded from role yaml or defaults."""
    daily_duration_seconds: float = DEFAULT_DAILY_DURATION_SECONDS
    daily_output_tokens: int = DEFAULT_DAILY_OUTPUT_TOKENS
    daily_turn_count: int = DEFAULT_DAILY_TURN_COUNT
    session_duration_seconds: float = DEFAULT_SESSION_DURATION_SECONDS
    absolute_duration_seconds: float = DEFAULT_ABSOLUTE_DURATION_SECONDS
    warn_threshold_frac: float = DEFAULT_WARN_THRESHOLD_FRAC


# ── Cap loader (mirrors spend_tracker._role_budget) ───────────────────

def _role_caps(role_id: Optional[str]) -> UtilizationCaps:
    """Load utilization caps from org/roles/<role>.yaml `agent_utilization`
    block; fall back to module defaults if absent or malformed.

    Schema expected in role yaml:
        agent_utilization:
          daily_cap_seconds: 10800
          daily_cap_output_tokens: 500000
          daily_cap_turn_count: 200
          session_cap_seconds: 5400
          absolute_ceiling_seconds: 18000
          warn_threshold_frac: 0.80
    """
    caps = UtilizationCaps()
    if not role_id:
        return caps
    try:
        # Roles registry (loaded the same way spend_tracker._role_budget does).
        # Fallback: parse yaml directly if registry doesn't expose util fields yet.
        role_path = Path("org/roles") / f"{role_id}.yaml"
        if not role_path.exists():
            return caps
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(role_path.read_text(encoding="utf-8")) or {}
        except ImportError:
            return caps  # PyYAML unavailable; honor defaults
        util = data.get("agent_utilization")
        if not isinstance(util, dict):
            return caps
        if "daily_cap_seconds" in util:
            caps.daily_duration_seconds = float(util["daily_cap_seconds"])
        if "daily_cap_output_tokens" in util:
            caps.daily_output_tokens = int(util["daily_cap_output_tokens"])
        if "daily_cap_turn_count" in util:
            caps.daily_turn_count = int(util["daily_cap_turn_count"])
        if "session_cap_seconds" in util:
            caps.session_duration_seconds = float(util["session_cap_seconds"])
        if "absolute_ceiling_seconds" in util:
            caps.absolute_duration_seconds = float(util["absolute_ceiling_seconds"])
        if "warn_threshold_frac" in util:
            caps.warn_threshold_frac = float(util["warn_threshold_frac"])
    except Exception as exc:  # noqa: BLE001
        log.debug("role %s utilization caps lookup failed, using defaults: %s",
                  role_id, exc)
    return caps


# ── IO helpers (parallel to spend_tracker for symmetry) ───────────────

def _daily_path(now: Optional[datetime] = None) -> Path:
    now = now or datetime.now(timezone.utc)
    return UTIL_ROOT / f"{now.date().isoformat()}.json"


def _load_daily(now: Optional[datetime] = None) -> list[dict]:
    p = _daily_path(now)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("entries", []))
    except Exception as exc:  # noqa: BLE001
        log.warning("agent utilization log unreadable (%s); treating as empty", exc)
        return []


def _aggregate_totals(entries: list[dict]) -> dict:
    """Roll up entries into by_role / by_cli / by_role_cli buckets."""
    def _zero():
        return {"duration_seconds": 0.0, "output_tokens": 0,
                "input_tokens": 0, "turn_count": 0, "session_count": 0}

    by_role: dict[str, dict] = {}
    by_cli: dict[str, dict] = {}
    by_role_cli: dict[str, dict] = {}
    for e in entries:
        role = str(e.get("role_id") or "unknown")
        cli = str(e.get("agent_cli") or "unknown")
        dur = float(e.get("duration_seconds") or 0.0)
        out = int(e.get("output_tokens") or 0)
        inp = int(e.get("input_tokens") or 0)
        turns = int(e.get("turn_count") or 0)
        for bucket, key in ((by_role, role), (by_cli, cli),
                             (by_role_cli, f"{role}:{cli}")):
            slot = bucket.setdefault(key, _zero())
            slot["duration_seconds"] += dur
            slot["output_tokens"] += out
            slot["input_tokens"] += inp
            slot["turn_count"] += turns
            slot["session_count"] += 1
    # Round durations to avoid float noise in JSON
    for bucket in (by_role, by_cli, by_role_cli):
        for slot in bucket.values():
            slot["duration_seconds"] = round(slot["duration_seconds"], 3)
    return {"by_role": by_role, "by_cli": by_cli, "by_role_cli": by_role_cli}


def _save_daily(entries: list[dict], now: Optional[datetime] = None) -> None:
    UTIL_ROOT.mkdir(parents=True, exist_ok=True)
    p = _daily_path(now)
    payload = {
        "date": (now or datetime.now(timezone.utc)).date().isoformat(),
        "entries": entries,
        "totals": _aggregate_totals(entries),
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, p)


# ── Public API ────────────────────────────────────────────────────────

def get_daily_totals(*, role_id: Optional[str] = None,
                     agent_cli: Optional[str] = None,
                     now: Optional[datetime] = None) -> dict:
    """Aggregate utilization for today (UTC), optionally filtered by
    role_id and/or agent_cli.

    Returns a dict {duration_seconds, output_tokens, input_tokens,
    turn_count, session_count}.
    """
    entries = _load_daily(now)

    def _zero():
        return {"duration_seconds": 0.0, "output_tokens": 0,
                "input_tokens": 0, "turn_count": 0, "session_count": 0}
    out = _zero()
    for e in entries:
        if role_id and str(e.get("role_id")) != role_id:
            continue
        if agent_cli and str(e.get("agent_cli")) != agent_cli:
            continue
        out["duration_seconds"] += float(e.get("duration_seconds") or 0.0)
        out["output_tokens"] += int(e.get("output_tokens") or 0)
        out["input_tokens"] += int(e.get("input_tokens") or 0)
        out["turn_count"] += int(e.get("turn_count") or 0)
        out["session_count"] += 1
    out["duration_seconds"] = round(out["duration_seconds"], 3)
    return out


def get_utilization_pct(*, role_id: Optional[str] = None,
                        agent_cli: Optional[str] = None,
                        dimension: str = "duration_seconds",
                        now: Optional[datetime] = None) -> float:
    """Fraction of daily cap consumed for the (role, cli) pair on the
    chosen dimension. Returns a float in [0.0, ∞) — values > 1.0 mean
    cap exceeded.

    dimension must be one of: 'duration_seconds', 'output_tokens',
    'turn_count'.

    If role_id is omitted, uses the union over all roles (effectively
    "what fraction of one role's cap has the whole org consumed", which
    is rarely what you want — pass role_id for the canonical reading).
    """
    if dimension not in ("duration_seconds", "output_tokens", "turn_count"):
        raise ValueError(f"unknown dimension: {dimension!r}")
    caps = _role_caps(role_id)
    cap_map = {
        "duration_seconds": caps.daily_duration_seconds,
        "output_tokens": caps.daily_output_tokens,
        "turn_count": caps.daily_turn_count,
    }
    cap = cap_map[dimension]
    if cap <= 0:
        return 0.0
    totals = get_daily_totals(role_id=role_id, agent_cli=agent_cli, now=now)
    used = float(totals.get(dimension, 0))
    return used / float(cap)


def check_utilization_allows(*, role_id: str, agent_cli: str,
                              estimated_seconds: float = 0.0,
                              estimated_output_tokens: int = 0,
                              estimated_turns: int = 1,
                              session_id: Optional[str] = None,
                              now: Optional[datetime] = None) -> tuple[bool, list[str]]:
    """Pre-flight: would the next session exceed any utilization cap?

    Checks all three dimensions against the role's daily caps PLUS the
    per-session duration cap PLUS the absolute hard ceiling. Returns
    (allowed, reasons) where reasons is empty when allowed=True and
    contains one diagnostic string per failed cap when allowed=False.

    Caller is responsible for honoring the verdict; this function does
    not raise. Pattern mirrors spend_tracker.check_budget_allows.
    """
    caps = _role_caps(role_id)
    totals = get_daily_totals(role_id=role_id, agent_cli=agent_cli, now=now)
    reasons: list[str] = []

    # 1) Single-session duration cap
    if estimated_seconds > caps.session_duration_seconds:
        reasons.append(
            f"single-session duration estimate {estimated_seconds:.0f}s exceeds "
            f"session cap {caps.session_duration_seconds:.0f}s for role {role_id!r}"
        )

    # 2) Daily duration cap
    proj_dur = float(totals["duration_seconds"]) + float(estimated_seconds)
    if proj_dur > caps.daily_duration_seconds:
        reasons.append(
            f"daily duration {totals['duration_seconds']:.0f}s + estimated "
            f"{estimated_seconds:.0f}s = {proj_dur:.0f}s exceeds daily cap "
            f"{caps.daily_duration_seconds:.0f}s for role {role_id!r}"
        )

    # 3) Absolute ceiling (hard wall)
    if proj_dur > caps.absolute_duration_seconds:
        reasons.append(
            f"projected duration {proj_dur:.0f}s would exceed ABSOLUTE ceiling "
            f"{caps.absolute_duration_seconds:.0f}s for role {role_id!r}"
        )

    # 4) Daily output-tokens cap
    proj_out = int(totals["output_tokens"]) + int(estimated_output_tokens)
    if proj_out > caps.daily_output_tokens:
        reasons.append(
            f"daily output tokens {totals['output_tokens']} + estimated "
            f"{estimated_output_tokens} = {proj_out} exceeds cap "
            f"{caps.daily_output_tokens} for role {role_id!r}"
        )

    # 5) Daily turn-count cap
    proj_turns = int(totals["turn_count"]) + int(estimated_turns)
    if proj_turns > caps.daily_turn_count:
        reasons.append(
            f"daily turn count {totals['turn_count']} + estimated "
            f"{estimated_turns} = {proj_turns} exceeds cap "
            f"{caps.daily_turn_count} for role {role_id!r}"
        )

    return (len(reasons) == 0, reasons)


def record_agent_session(*, role_id: str, agent_cli: str,
                          duration_seconds: float,
                          output_tokens: Optional[int] = None,
                          input_tokens: Optional[int] = None,
                          cache_read_tokens: Optional[int] = None,
                          cache_write_tokens: Optional[int] = None,
                          turn_count: Optional[int] = None,
                          session_id: Optional[str] = None,
                          notes: Optional[Iterable[str]] = None,
                          now: Optional[datetime] = None) -> AgentSessionEntry:
    """Append an agent-session entry to today's utilization log.

    Does NOT enforce caps by itself — call `check_utilization_allows`
    first. Does fire a warn-threshold log when the cumulative daily
    utilization on any dimension crosses caps.warn_threshold_frac. The
    push-notification side-effect that spend_tracker triggers is OUT OF
    SCOPE here (callers integrate with org/signals/ via their own glue
    if they want a notification channel).
    """
    now = now or datetime.now(timezone.utc)
    entry = AgentSessionEntry(
        timestamp_utc=now.isoformat().replace("+00:00", "Z"),
        role_id=role_id,
        agent_cli=agent_cli,
        duration_seconds=float(duration_seconds),
        output_tokens=int(output_tokens) if output_tokens is not None else None,
        input_tokens=int(input_tokens) if input_tokens is not None else None,
        cache_read_tokens=int(cache_read_tokens) if cache_read_tokens is not None else None,
        cache_write_tokens=int(cache_write_tokens) if cache_write_tokens is not None else None,
        turn_count=int(turn_count) if turn_count is not None else None,
        session_id=session_id,
        notes=tuple(notes or ()),
    )
    entries = _load_daily(now)
    entries.append({k: v for k, v in asdict(entry).items() if v is not None or k in ("notes",)})
    _save_daily(entries, now=now)

    # Warn-threshold detection: log + (optionally) push through the configured
    # notification provider. Push is best-effort: provider failure falls back
    # to log-only. The recorded entry is always
    # persisted regardless of notification success.
    caps = _role_caps(role_id)
    pct_dur = get_utilization_pct(role_id=role_id, dimension="duration_seconds", now=now)
    pct_tok = get_utilization_pct(role_id=role_id, dimension="output_tokens", now=now)
    pct_turn = get_utilization_pct(role_id=role_id, dimension="turn_count", now=now)

    # F2 (gp168 v3 run-2 finding 2026-05-02): randomized warn-threshold
    # jitter as a detection-independent gaming defense. Without jitter,
    # agents can game by staying just below the static warn fraction.
    # With jitter, the effective warn fraction is sampled from a uniform
    # distribution in [warn_threshold_frac - 0.10, warn_threshold_frac]
    # per (role, day) so that "just below 80%" gaming becomes "just below
    # an unknown threshold in [70%, 80%]" — same expected coverage,
    # gaming surface eliminated.
    # Seeded by (role, agent_cli, UTC date) so the jitter is deterministic
    # within a day (ops can reproduce) but unpredictable across days.
    effective_warn_frac = _jittered_warn_frac(
        role_id=role_id, agent_cli=agent_cli,
        base_frac=caps.warn_threshold_frac, now=now,
    )
    triggered: list[tuple[str, float]] = []
    if pct_dur >= effective_warn_frac:
        triggered.append(("duration_seconds", pct_dur))
    if pct_tok >= effective_warn_frac:
        triggered.append(("output_tokens", pct_tok))
    if pct_turn >= effective_warn_frac:
        triggered.append(("turn_count", pct_turn))
    if triggered:
        summary = ", ".join(f"{dim} @ {pct*100:.0f}%" for dim, pct in triggered)
        log.warning("agent_utilization warn-threshold tripped for role=%s: %s",
                    role_id, summary)
        _emit_warn_notification(
            role_id=role_id,
            agent_cli=agent_cli,
            triggered=triggered,
            warn_frac=caps.warn_threshold_frac,
            session_id=session_id,
        )
    return entry


def _emit_warn_notification(*, role_id: str, agent_cli: str,
                             triggered: list[tuple[str, float]],
                             warn_frac: float,
                             session_id: Optional[str]) -> None:
    """Best-effort warn-threshold notification to the principal.

    Channels (in priority order):
      1. Notification provider push (`src.ztare.notifications.push_notification`)
      2. Damage-signal emit to `org/signals/damage/` for the closure_daemon
         to pick up on its next tick (fallback path; lossless)
      3. Stderr log (always; final fallback)

    Idempotency: if the same (role, dimension, day) has already had a warn
    notification fired today, skip — preventing notification storms when
    the threshold is straddled by many small sessions. Tracked via a tiny
    marker file at ztare_workspace/agent_utilization/.warned/<date>.json.
    """
    # Idempotency: one warning per (role, agent_cli, dimension) per day.
    marker_dir = UTIL_ROOT / ".warned"
    today = datetime.now(timezone.utc).date().isoformat()
    marker_path = marker_dir / f"{today}.json"
    fired_set = set()
    if marker_path.exists():
        try:
            fired_set = set(json.loads(marker_path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            fired_set = set()

    fresh: list[tuple[str, float]] = []
    for dim, pct in triggered:
        key = f"{role_id}:{agent_cli}:{dim}"
        if key in fired_set:
            continue
        fresh.append((dim, pct))
        fired_set.add(key)

    if not fresh:
        return  # already warned for these dims today

    # Persist the marker so we don't spam.
    try:
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(json.dumps(sorted(fired_set), indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.debug("could not persist warn marker: %s", exc)

    summary = ", ".join(f"{dim} @ {pct*100:.0f}%" for dim, pct in fresh)
    title = f"Agent-CLI utilization warn ({role_id})"
    body = (
        f"Role `{role_id}` has crossed the {int(warn_frac*100)}% warn threshold "
        f"on agent-CLI `{agent_cli}`:\n\n"
        f"  {summary}\n\n"
        f"Session id: {session_id or '(none)'}\n"
        f"Daily caps from org/roles/{role_id}.yaml#agent_utilization. "
        f"Inspect ztare_workspace/agent_utilization/{today}.json for the "
        f"per-session breakdown."
    )

    # Channel 1: notification push
    push_ok = False
    try:
        from src.ztare.notifications import push_notification
        push_notification(
            title=title,
            message=body,
            priority="high",
            tags=["agent_utilization", role_id, agent_cli],
        )
        push_ok = True
    except Exception as exc:  # noqa: BLE001
        log.debug("agent_utilization notification push failed: %s", exc)

    # Channel 2: damage-signal emit (always, regardless of push success —
    # provides a durable artifact the closure_daemon can pick up).
    try:
        signals_dir = Path("org/signals/damage")
        signals_dir.mkdir(parents=True, exist_ok=True)
        signal_path = signals_dir / (
            f"agent_utilization_warn_{role_id}_{agent_cli}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        signal_path.write_text(json.dumps({
            "kind": "agent_utilization_warn",
            "severity": "warn",
            "role_id": role_id,
            "agent_cli": agent_cli,
            "warn_threshold_frac": warn_frac,
            "triggered": [{"dimension": d, "fraction_of_cap": p} for d, p in fresh],
            "session_id": session_id,
            "notification_push_emitted": push_ok,
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "summary": summary,
            "body": body,
        }, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.warning("agent_utilization damage-signal write failed: %s", exc)


# ── F1: override-event recording (gp168 v3 run-2 finding, 2026-05-02) ──
# Surfaces principal-side subversions of the exogenous-pressure clock as
# first-class audit artifacts. Without this, every cap extension /
# closure postponement / approval delay is silent — the closure
# mechanism becomes self-undermining without observable trace. The
# gp168 v3 run-2 iter-3 thesis (score 63) documented this failure mode
# across 5 substrate priors; this is the operational counter-measure.

OVERRIDE_KINDS = {
    "cap_extension",          # principal raised a daily/session/single-action cap
    "closure_postponement",   # principal extended an Objective deadline / KR cadence
    "approval_delay",         # principal sat on a pending gate past SLA
    "audit_skip",             # principal dismissed an audit cycle
    "absolute_ceiling_raise", # principal raised the runaway-loop hard ceiling
}


def record_override_event(*, kind: str,
                          role_id: Optional[str],
                          actor: str,
                          old_value: Optional[float] = None,
                          new_value: Optional[float] = None,
                          target: Optional[str] = None,
                          reason: str = "",
                          session_id: Optional[str] = None,
                          now: Optional[datetime] = None) -> Path:
    """Record a principal-side override of an exogenous-pressure clock.

    F1 of the gp168 v3 run-2 findings. Every cap extension, closure
    postponement, or approval delay performed by the principal is
    durably logged so subversion of the closure mechanism is auditable
    rather than silent. The artifact lands in three places (write-once
    each):

      1. `ztare_workspace/agent_utilization/overrides/<date>.jsonl`
         (per-day audit trail; appended one row per event)
      2. `ztare_workspace/transitions.jsonl` as a row with
         `event: override_event`
      3. (best-effort) notification push notifying the principal of their
         own override

    The friction is the point: an override that is loudly logged is
    still permitted, but the visibility raises the implicit cost.

    Args:
        kind: one of OVERRIDE_KINDS
        role_id: the role whose cap/closure was extended (None if global)
        actor: who performed the override (typically "principal" or a
            specific agent_cli)
        old_value: prior value (e.g., old daily_cap_seconds)
        new_value: new value
        target: free-form descriptor (e.g., "daily_cap_seconds",
            "objective_deadline_2026-05-15", "gate_pending_id_abc123")
        reason: principal-supplied reason (free-form)
        session_id: link to the session that triggered the override
        now: timestamp override for tests
    """
    if kind not in OVERRIDE_KINDS:
        raise ValueError(
            f"unknown override kind: {kind!r}; must be one of {sorted(OVERRIDE_KINDS)}"
        )
    now = now or datetime.now(timezone.utc)
    payload = {
        "event": "override_event",
        "kind": kind,
        "role_id": role_id,
        "actor": actor,
        "target": target,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "session_id": session_id,
        "timestamp_utc": now.isoformat().replace("+00:00", "Z"),
    }

    # Channel 1: per-day jsonl audit trail.
    overrides_dir = UTIL_ROOT / "overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    date_str = now.date().isoformat()
    audit_path = overrides_dir / f"{date_str}.jsonl"
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")

    # Channel 2: append to transitions.jsonl.
    try:
        transitions_path = Path("ztare_workspace/transitions.jsonl")
        transitions_path.parent.mkdir(parents=True, exist_ok=True)
        with transitions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception as exc:  # noqa: BLE001
        log.warning("override_event transitions.jsonl write failed: %s", exc)

    # Channel 3: best-effort notification push.
    try:
        from src.ztare.notifications import push_notification
        delta_str = ""
        if old_value is not None and new_value is not None:
            delta_str = f" ({old_value:g} → {new_value:g})"
        body = (
            f"🛎  Override: {kind} on {target or '(global)'}{delta_str} "
            f"by {actor}\n"
            f"role: {role_id or '(none)'}\n"
            f"reason: {reason or '(no reason given)'}\n"
            f"audit: ztare_workspace/agent_utilization/overrides/{date_str}.jsonl"
        )
        push_notification(
            title="ZTARE override event",
            message=body,
            tags=["override_event", kind, role_id or "global"],
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("override_event notification push failed: %s", exc)

    log.info("override_event recorded: kind=%s role=%s actor=%s target=%s",
             kind, role_id, actor, target)
    return audit_path


def get_override_count_today(*, role_id: Optional[str] = None,
                             kind: Optional[str] = None,
                             now: Optional[datetime] = None) -> int:
    """Count override events today, optionally filtered. Used by Orbit
    to display per-Objective override counters and per-role audit
    trails."""
    now = now or datetime.now(timezone.utc)
    overrides_dir = UTIL_ROOT / "overrides"
    audit_path = overrides_dir / f"{now.date().isoformat()}.jsonl"
    if not audit_path.exists():
        return 0
    count = 0
    try:
        with audit_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if role_id is not None and rec.get("role_id") != role_id:
                    continue
                if kind is not None and rec.get("kind") != kind:
                    continue
                count += 1
    except Exception as exc:  # noqa: BLE001
        log.warning("override count read failed: %s", exc)
    return count


# ── F2: jittered warn-threshold (gp168 v3 run-2 finding, 2026-05-02) ──
# Detection-independent gaming defense. Without jitter, agents game by
# staying just below the static warn fraction. With jitter, the
# effective warn fraction is sampled from a uniform distribution in
# [base_frac - 0.10, base_frac] per (role, agent_cli, UTC date) so the
# gaming surface (predictable threshold) is eliminated while expected
# coverage is preserved.

def _jittered_warn_frac(*, role_id: str, agent_cli: str,
                        base_frac: float,
                        now: Optional[datetime] = None,
                        jitter_window: float = 0.10) -> float:
    """Return a deterministic-within-day jittered warn fraction.

    Seeded by (role_id, agent_cli, UTC-date) so:
      - reproducible within a day (ops can debug deterministically)
      - unpredictable across days (no static threshold to game)
      - bounded: result is in [base_frac - jitter_window, base_frac]
        (we only jitter DOWN, never UP — preserves the contract that
         the warn threshold is at most base_frac).

    The jitter_window default of 0.10 means warn-threshold 0.80 →
    sampled in [0.70, 0.80] each day. To disable (deterministic 0.80),
    set jitter_window=0.0 (callers may set this via the rubric flag
    `agent_utilization_jitter_window`, defaults to 0.10).
    """
    if jitter_window <= 0.0:
        return base_frac
    import hashlib as _hashlib
    now = now or datetime.now(timezone.utc)
    seed_str = f"{role_id}|{agent_cli}|{now.date().isoformat()}"
    digest = _hashlib.sha1(seed_str.encode()).hexdigest()
    # Use 4 hex chars (16 bits) of digest for the random fraction
    rand_int = int(digest[:4], 16)
    rand_unit = rand_int / 0xFFFF  # in [0, 1]
    floor_frac = max(0.0, base_frac - jitter_window)
    jittered = floor_frac + rand_unit * (base_frac - floor_frac)
    return jittered
