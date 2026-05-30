"""iter-to-action policy dispatcher (RD-1.12, 2026-05-02).

Reads `iter_action_policy.yaml` and matches incoming events against rules.
For each matching rule, queues an action onto the project's frontier_state
pending_actions queue. The daemon's tick loop then drains the queue and
executes the actions through `iter_action_executor.py` (separate module).

This split keeps the policy DECLARATIVE (what to do when X happens) and
the execution IMPERATIVE (how to actually mutate the substrate). Hot-
reloadable: edit yaml, next tick picks it up.

Event shape (emitted by frontier_runner.py):
    {
        "kind": str,                  # e.g. "obstruction_detected"
        "project_slug": str,
        "iter_index": int | None,
        "ts": str (ISO-8601 UTC),
        ...kind-specific payload (e.g. "route_id", "consecutive_count")
    }

Rule match semantics:
    - Each `when` key is matched as equality, EXCEPT:
      * "*" matches any value (wildcard)
      * ">=N" / "<=N" / ">N" / "<N" do numeric comparison
    - All when-keys must match for the rule to fire.
    - cooldown_seconds prevents the same rule from firing for the same
      project more than once per N seconds (tracked in frontier_state.history).

Returns:
    list of (rule_id, queued_action_dict) tuples for caller logging.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.ztare.role_extensions import frontier_state as fs

log = logging.getLogger(__name__)

POLICY_PATH = Path("src/ztare/role_extensions/iter_action_policy.yaml")

_NUMERIC_PATTERN_RE = re.compile(r"^(>=|<=|>|<|==)?\s*(-?\d+(?:\.\d+)?)$")


def _load_policy(path: Path = POLICY_PATH) -> dict:
    """Load + parse the policy yaml. Returns {} if missing or unparseable."""
    if not path.exists():
        log.warning("policy file %s missing; no rules loaded", path)
        return {"rules": []}
    try:
        import yaml  # type: ignore
    except ImportError:
        log.warning("PyYAML unavailable; cannot load policy")
        return {"rules": []}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {"rules": []}
    except Exception as exc:  # noqa: BLE001
        log.error("failed to parse %s: %s", path, exc)
        return {"rules": []}


def _value_matches(rule_value: Any, event_value: Any) -> bool:
    """One-key match: rule_value can be:
      - "*"        → wildcard, always matches
      - ">=N" etc  → numeric comparison
      - other      → equality
    """
    if rule_value == "*":
        return True
    if isinstance(rule_value, str):
        m = _NUMERIC_PATTERN_RE.match(rule_value.strip())
        if m and event_value is not None:
            op, num_str = m.group(1) or "==", m.group(2)
            try:
                num = float(num_str)
                ev = float(event_value)
            except (TypeError, ValueError):
                return False
            return {
                "==": ev == num,
                ">=": ev >= num,
                "<=": ev <= num,
                ">":  ev >  num,
                "<":  ev <  num,
            }[op]
    return rule_value == event_value


def _rule_matches_event(rule: dict, event: dict) -> bool:
    """All keys in rule['when'] must match the corresponding event field."""
    when = rule.get("when") or {}
    if not isinstance(when, dict) or not when:
        return False
    for key, rule_val in when.items():
        ev_val = event.get(key)
        if not _value_matches(rule_val, ev_val):
            return False
    return True


def _rule_in_cooldown(rule: dict, state: fs.FrontierState) -> bool:
    """True iff this rule has fired recently within its cooldown window."""
    cooldown = int(rule.get("cooldown_seconds") or 0)
    if cooldown <= 0:
        return False
    rule_id = rule.get("id")
    if not rule_id:
        return False
    now = datetime.now(timezone.utc)
    for h in reversed(state.history):
        if h.get("event") == "policy_rule_fired" and h.get("rule_id") == rule_id:
            try:
                ts = datetime.fromisoformat((h["ts"] or "").rstrip("Z") + "+00:00")
            except Exception:  # noqa: BLE001
                continue
            if (now - ts).total_seconds() < cooldown:
                return True
            break
    return False


def dispatch_event(event: dict, *,
                   policy_path: Optional[Path] = None) -> list[tuple[str, dict]]:
    """Match a single event against all loaded policy rules. For each
    matching rule (subject to cooldown), queue an action onto the
    project's frontier_state.pending_actions.

    Returns list of (rule_id, action_dict) for what was queued.
    """
    project_slug = event.get("project_slug")
    if not project_slug:
        log.warning("dispatch_event: event missing project_slug; skipping")
        return []

    policy = _load_policy(policy_path or POLICY_PATH)
    rules = policy.get("rules") or []
    state = fs.load_state(project_slug)

    queued: list[tuple[str, dict]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rule_id = rule.get("id") or "<unnamed>"
        if not _rule_matches_event(rule, event):
            continue
        if _rule_in_cooldown(rule, state):
            log.debug("rule %s in cooldown; skipping for %s",
                      rule_id, project_slug)
            continue
        do_block = rule.get("do") or {}
        action = {
            "action_kind": do_block.get("action_kind"),
            "params": dict(do_block.get("params") or {}),
            "reason": rule.get("reason", ""),
            "rule_id": rule_id,
            "from_event": dict(event),
        }
        if not action["action_kind"]:
            log.warning("rule %s has no action_kind; skipping", rule_id)
            continue
        # Inject event payload into params where the action needs it.
        if "route_id" in event and "route_id" not in action["params"]:
            action["params"]["route_id"] = event["route_id"]
        if "iter_index" in event:
            action["params"]["from_iter"] = event["iter_index"]
        action["params"]["project_slug"] = project_slug

        # Queue + audit
        fs.queue_action(state, action)
        # Re-load to pick up the freshly persisted state and append the
        # cooldown-tracking history row in the same write.
        state = fs.load_state(project_slug)
        fs.save_state(state, history_append={
            "event": "policy_rule_fired",
            "rule_id": rule_id,
            "action_kind": action["action_kind"],
            "from_event_kind": event.get("kind"),
        })
        state = fs.load_state(project_slug)
        queued.append((rule_id, action))

    return queued
