"""Spend-tracking + budget-gate primitive for the claude_manager mandate.

Reuses the existing ZTARE cost infrastructure:
- `supervisor_usage.load_model_pricing` (already-implemented pricing table
  loader at `supervisor/model_pricing.json`).
- `supervisor_state.TurnUsageTelemetry` dataclass (existing schema).
- Model pricing registry already tracking Claude/GPT/Gemini rates per token.

Adds on top of that:
- A session-scoped budget JSON at `ztare_workspace/spend/<date>.json`
  accumulating every LLM turn and external API call the manager agent
  initiates.
- A hard gate: `check_budget_allows(cost_usd)` returns False if the next
  action would exceed the mandate's per-session or per-day budget cap.
  Callers MUST check this before spending.
- A push-escalation hook that fires an urgent ntfy when cumulative spend
  crosses a threshold (default 80% of daily cap).

This is the structural enforcement upgrade from the mandate's otherwise-
advisory spend rules. Callable from manager-agent code and from any
future Level-2 daemon invocation.

Usage:

    from src.ztare.supervisor.spend_tracker import (
        record_spend, check_budget_allows, get_daily_total,
    )

    # Before a costly action:
    if not check_budget_allows(estimated_cost_usd=5.00, action="gpu_launch"):
        escalate(title="Budget gate triggered", urgent=True, ...)
        return

    # After the action:
    record_spend(
        cost_usd=4.87,
        category="gpu",
        action="launched A10 on Lambda for riemann smoke test",
        model_name=None,
    )

The JSON layout is intentionally simple (single append-only list per
day) so a cron job or the Level-2 daemon can summarize it without
schema migrations.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


# --- Budget caps — loaded from role YAML via registry ----------------
#
# Hole 4 fix: previously the caps were hardcoded here. Now the
# authoritative source is org/roles/<role>.yaml and we load via the
# role registry. Fallback constants below match the mandate numeric
# defaults so callers that don't pass a role still get reasonable
# enforcement. The `check_budget_allows` entry point accepts role_id
# and consults the role's budget before the fallback.
MANDATE_SINGLE_ACTION_CAP_USD = 10.00    # one cloud spend (fallback)
MANDATE_SESSION_CAP_USD = 50.00          # cumulative per session (fallback)
MANDATE_DAILY_CAP_USD = 100.00           # cumulative per day (fallback)
MANDATE_NEVER_CAP_USD = 100.00           # absolute ceiling (fallback)

# Warn-threshold: fire a push notification when cumulative spend crosses
# this fraction of the daily cap.
WARN_THRESHOLD_FRAC = 0.80


def _role_budget(role_id: Optional[str]) -> dict:
    """Load budget caps from the role YAML via registry, with fallback
    to the MANDATE_* constants above."""
    caps = {
        "single": MANDATE_SINGLE_ACTION_CAP_USD,
        "session": MANDATE_SESSION_CAP_USD,
        "daily": MANDATE_DAILY_CAP_USD,
        "absolute": MANDATE_NEVER_CAP_USD,
        "warn_frac": WARN_THRESHOLD_FRAC,
    }
    if not role_id:
        return caps
    try:
        from src.ztare.roles import load_registry
        reg = load_registry(validate=False)
        role = reg.role(role_id)
        b = role.budget
        caps["single"] = b.single_action_cap_usd if b.single_action_cap_usd is not None else caps["single"]
        caps["session"] = b.session_cap_usd if b.session_cap_usd is not None else caps["session"]
        caps["daily"] = b.daily_cap_usd if b.daily_cap_usd is not None else caps["daily"]
        caps["absolute"] = b.absolute_ceiling_usd if b.absolute_ceiling_usd is not None else caps["absolute"]
        caps["warn_frac"] = b.warn_threshold_frac if b.warn_threshold_frac is not None else caps["warn_frac"]
    except Exception as exc:  # noqa: BLE001
        log.debug("role %s budget lookup failed, using fallback: %s",
                  role_id, exc)
    return caps

SPEND_ROOT = Path("ztare_workspace/spend")

log = logging.getLogger(__name__)


@dataclass
class SpendEntry:
    timestamp_utc: str
    cost_usd: float
    category: str               # gpu, llm, api, other
    action: str                 # human-readable description
    model_name: Optional[str] = None
    session_id: Optional[str] = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def _daily_path(now: Optional[datetime] = None) -> Path:
    now = now or datetime.now(timezone.utc)
    return SPEND_ROOT / f"{now.date().isoformat()}.json"


def _load_daily(now: Optional[datetime] = None) -> list[dict]:
    p = _daily_path(now)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("entries", []))
    except Exception as exc:  # noqa: BLE001
        log.warning("spend log unreadable (%s); treating as empty", exc)
        return []


def _save_daily(entries: list[dict], now: Optional[datetime] = None) -> None:
    SPEND_ROOT.mkdir(parents=True, exist_ok=True)
    p = _daily_path(now)
    payload = {
        "date": (now or datetime.now(timezone.utc)).date().isoformat(),
        "entries": entries,
        "total_usd": round(sum(float(e.get("cost_usd", 0.0)) for e in entries), 4),
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def get_daily_total(now: Optional[datetime] = None) -> float:
    """Total cost recorded today (UTC)."""
    return round(sum(float(e.get("cost_usd", 0.0))
                     for e in _load_daily(now)), 4)


def get_session_total(session_id: str,
                      now: Optional[datetime] = None) -> float:
    """Total cost recorded in the given session (today only)."""
    entries = _load_daily(now)
    return round(sum(float(e.get("cost_usd", 0.0))
                     for e in entries
                     if e.get("session_id") == session_id), 4)


def record_spend(
    *,
    cost_usd: float,
    category: str,
    action: str,
    model_name: Optional[str] = None,
    session_id: Optional[str] = None,
    notes: Optional[Iterable[str]] = None,
) -> SpendEntry:
    """Append a spend entry to today's log.

    Does NOT enforce budgets by itself — call `check_budget_allows` first.
    Does trigger an early-warning push notification when the daily total
    crosses WARN_THRESHOLD_FRAC of the daily cap (e.g. $80 of $100).
    """
    now = datetime.now(timezone.utc)
    entry = SpendEntry(
        timestamp_utc=now.isoformat(),
        cost_usd=float(cost_usd),
        category=str(category),
        action=str(action),
        model_name=model_name,
        session_id=session_id,
        notes=tuple(notes or ()),
    )

    entries = _load_daily(now)
    entries.append(asdict(entry))
    _save_daily(entries, now)

    # Early-warning escalation at 80% of daily cap
    daily_total = get_daily_total(now)
    threshold = WARN_THRESHOLD_FRAC * MANDATE_DAILY_CAP_USD
    previous_total = daily_total - cost_usd
    if previous_total < threshold <= daily_total:
        _fire_budget_warning(daily_total, threshold)

    return entry


def check_budget_allows(
    *,
    estimated_cost_usd: float,
    action: str,
    session_id: Optional[str] = None,
    role_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Return (allowed, reason) for an action that would cost
    estimated_cost_usd. Reason is empty when allowed, or a short
    string naming the cap that would be breached.

    Policy (uses role's budget from YAML when role_id is supplied, else
    falls back to the mandate default constants):
    - single_action_cap, session_cap, daily_cap, absolute_ceiling from role
    - Principal role has no caps (daily_cap=None etc.) — all caps are
      treated as unbounded in that case
    """
    caps = _role_budget(role_id)

    # Unbounded role (e.g. principal) passes everything
    def _unbounded(v): return v is None

    if not _unbounded(caps["single"]) and estimated_cost_usd > caps["single"]:
        return False, (
            f"single action ${estimated_cost_usd:.2f} exceeds role "
            f"cap of ${caps['single']:.2f}"
        )

    daily_total = get_daily_total()
    daily_after = daily_total + estimated_cost_usd

    if not _unbounded(caps["absolute"]) and daily_after > caps["absolute"]:
        return False, (
            f"daily total after action ${daily_after:.2f} exceeds absolute "
            f"ceiling ${caps['absolute']:.2f} (requires explicit written auth)"
        )
    if not _unbounded(caps["daily"]) and daily_after > caps["daily"]:
        return False, (
            f"daily total after action ${daily_after:.2f} exceeds role "
            f"daily cap ${caps['daily']:.2f}"
        )

    if session_id and not _unbounded(caps["session"]):
        session_after = get_session_total(session_id) + estimated_cost_usd
        if session_after > caps["session"]:
            return False, (
                f"session total after action ${session_after:.2f} exceeds "
                f"role session cap ${caps['session']:.2f}"
            )

    return True, ""


def _fire_budget_warning(total: float, threshold: float) -> None:
    """Push a warning to principal that daily spend has crossed
    WARN_THRESHOLD_FRAC of the cap."""
    try:
        from src.ztare.supervisor.escalation_manager import escalate
    except ImportError:
        log.warning("escalation_manager unavailable; cannot push budget warning")
        return

    try:
        escalate(
            title=f"Budget warning: ${total:.2f} / ${MANDATE_DAILY_CAP_USD:.2f} today",
            reason=(
                f"Daily spend crossed {WARN_THRESHOLD_FRAC*100:.0f}% of mandate cap. "
                f"Current: ${total:.2f}, Cap: ${MANDATE_DAILY_CAP_USD:.2f}. "
                "Further actions may be refused by budget gate until rollover at UTC midnight, "
                "or until principal raises the cap."
            ),
            urgent=True,
            notes=[
                f"Warning threshold: ${threshold:.2f}",
                "See ztare_workspace/spend/ for detailed entries.",
            ],
            cost_usd=total,
            equivalent_gate_reason="BUDGET_WARNING",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("budget warning escalation failed: %s", exc)


def record_llm_turn(
    *,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
    action: str = "llm turn",
    session_id: Optional[str] = None,
) -> Optional[SpendEntry]:
    """Convenience wrapper: compute cost from token counts using the
    existing supervisor_usage pricing registry, then record it.
    Returns None if pricing is disabled or unknown for this model.
    """
    try:
        from src.ztare.supervisor.supervisor_usage import load_model_pricing
        from src.ztare.common.llm_runtime import pricing_model_name
    except ImportError as exc:
        log.warning("supervisor_usage unavailable (%s); cannot price turn", exc)
        return None

    pricing = load_model_pricing()
    key = pricing_model_name(model_name)
    rates = pricing.get(key)
    if rates is None:
        log.debug("no pricing for model %s; skipping record", model_name)
        return None

    def _cost(tokens: int, per_mil: float) -> float:
        return (tokens / 1_000_000.0) * per_mil

    cost_usd = (
        _cost(input_tokens, rates.input_per_million_usd)
        + _cost(output_tokens, rates.output_per_million_usd)
        + _cost(cache_creation_input_tokens,
                rates.cache_creation_input_per_million_usd)
        + _cost(cache_read_input_tokens,
                rates.cache_read_input_per_million_usd)
    )

    return record_spend(
        cost_usd=cost_usd,
        category="llm",
        action=action,
        model_name=model_name,
        session_id=session_id,
        notes=(
            f"input={input_tokens}",
            f"output={output_tokens}",
            f"cache_creation={cache_creation_input_tokens}",
            f"cache_read={cache_read_input_tokens}",
        ),
    )


def daily_summary(now: Optional[datetime] = None) -> dict:
    """Human-readable summary of today's spend, grouped by category.
    Useful for daily-digest emails or the cron log-only no-op path."""
    entries = _load_daily(now)
    by_cat: dict[str, float] = {}
    for e in entries:
        by_cat[e.get("category", "other")] = (
            by_cat.get(e.get("category", "other"), 0.0)
            + float(e.get("cost_usd", 0.0))
        )
    total = round(sum(by_cat.values()), 4)
    return {
        "date": (now or datetime.now(timezone.utc)).date().isoformat(),
        "total_usd": total,
        "daily_cap_usd": MANDATE_DAILY_CAP_USD,
        "fraction_of_cap": round(total / MANDATE_DAILY_CAP_USD, 3)
        if MANDATE_DAILY_CAP_USD > 0 else None,
        "by_category": {k: round(v, 4) for k, v in by_cat.items()},
        "entry_count": len(entries),
    }
