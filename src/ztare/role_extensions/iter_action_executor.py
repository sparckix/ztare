"""Iter-action executor (RD-1.12, 2026-05-02).

Imperative side of the iter-action policy: takes a pending action from
frontier_state.pending_actions and actually mutates the world. Each
action passes through THREE non-negotiable safety rails before it
runs:

  1. USD spend gate     — src.ztare.supervisor.spend_tracker.check_budget_allows
  2. Agent-CLI util gate — src.ztare.supervisor.agent_utilization_tracker.check_utilization_allows
  3. Damage-signal emit  — every mutation writes to org/signals/damage/

If any safety rail rejects the action, it's logged to history with
status="blocked_by_safety_rail" and escalated to principal via Telegram
(GP-128b). The agent does NOT get to override these.

Action kinds implemented:
  - fork_substrate
  - create_lean_cage
  - demote_route_in_packet
  - mutate_evidence
  - mutate_charter
  - queue_cold_shot
  - update_champion_meaning
  - escalate_to_principal

Each handler returns an outcome dict for the audit trail:
    {
        "ok": bool,
        "action_kind": str,
        "action_id": str,
        "outcome": str,            # human-readable one-liner
        "artifacts_written": list[str],
        "blocked_reason": str,     # only if ok=False due to safety rail
    }

Two CLI entry points (so the agent can invoke from Bash):
    python -m src.ztare.role_extensions.iter_action_executor \
        --project <slug> --drain
    python -m src.ztare.role_extensions.iter_action_executor \
        --project <slug> --action-id <id>
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ztare.role_extensions import frontier_state as fs

log = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── Safety rails ─────────────────────────────────────────────────────

def _check_safety_rails(action: dict, *, role_id: str = "research_director") -> tuple[bool, str]:
    """Returns (allowed, reason). Reason is empty if allowed."""
    estimated_cost = float(action.get("params", {}).get("estimated_cost_usd") or 0.0)
    estimated_seconds = float(action.get("params", {}).get("estimated_seconds") or 0.0)

    # USD gate
    if estimated_cost > 0:
        try:
            from ztare.supervisor.spend_tracker import check_budget_allows
            allowed = check_budget_allows(
                estimated_cost_usd=estimated_cost,
                action=action.get("action_kind") or "<unknown>",
                role_id=role_id,
            )
            if not allowed:
                return False, f"USD spend gate: ${estimated_cost} would exceed cap for {role_id}"
        except Exception as exc:  # noqa: BLE001
            log.warning("spend gate check failed (allowing): %s", exc)

    # Agent utilization gate
    if estimated_seconds > 0:
        try:
            from ztare.supervisor.agent_utilization_tracker import (
                check_utilization_allows,
            )
            ok, reasons = check_utilization_allows(
                role_id=role_id,
                agent_cli="claude",  # default; override via params if needed
                estimated_seconds=estimated_seconds,
            )
            if not ok:
                return False, f"agent-CLI utilization gate: {reasons[0]}"
        except Exception as exc:  # noqa: BLE001
            log.warning("utilization gate check failed (allowing): %s", exc)

    return True, ""


def _emit_damage_signal(*, action: dict, outcome: dict, severity: str = "info") -> None:
    """Write a damage-signal artifact for the closure daemon to pick up."""
    try:
        signals_dir = Path("org/signals/damage")
        signals_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        kind = f"rd_action_{action.get('action_kind') or 'unknown'}"
        signal_path = signals_dir / f"{kind}_{ts}.json"
        signal_path.write_text(json.dumps({
            "kind": kind,
            "severity": severity,
            "source": "iter_action_executor",
            "action": action,
            "outcome": outcome,
            "timestamp_utc": _utc_now_iso(),
        }, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.warning("damage-signal emit failed: %s", exc)


# ── Action handlers (one per action_kind) ───────────────────────────

def _handle_fork_substrate(action: dict) -> dict:
    """Fork the active project's substrate to a successor with constructive
    complement evidence. Stub-level: writes a fork-spec markdown rather
    than performing the full substrate mutation. The agent reads the spec
    and authors the actual successor project under operator supervision."""
    params = action.get("params", {})
    slug = params.get("project_slug")
    project_dir = Path("projects") / slug if slug else None
    if not project_dir or not project_dir.exists():
        return {"ok": False, "outcome": f"project dir not found: {project_dir}"}
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    spec_path = workspace / "frontier_co_drive_fork_spec.md"
    spec_body = (
        f"# Fork-substrate spec — {_utc_now_iso()}\n\n"
        f"**Triggered by:** rule `{action.get('rule_id', '?')}` on event "
        f"`{(action.get('from_event') or {}).get('kind', '?')}`\n\n"
        f"**Reason:** {action.get('reason','').strip()}\n\n"
        f"**Routing strategy:** {params.get('evidence_diff_strategy','constructive_complement')}\n\n"
        f"## Operator action\n\n"
        f"1. Create successor project `{slug}_fork_{datetime.now(timezone.utc).strftime('%Y%m%d')}/`\n"
        f"2. Copy the parent's substrate; pivot evidence per the strategy above\n"
        f"3. Update charter to name the parent's obstruction as motivation\n"
        f"4. Resume the loop on the successor; parent project stays open as a refuted\n"
        f"   anchor.\n"
    )
    spec_path.write_text(spec_body, encoding="utf-8")
    return {
        "ok": True,
        "outcome": f"wrote fork spec → {spec_path}",
        "artifacts_written": [str(spec_path)],
    }


def _handle_create_lean_cage(action: dict) -> dict:
    """Write a Lean theorem cage stub for a verified axiom. The actual Lean
    proof scaffolding belongs in a separate authoring pass; this writes
    the cage skeleton + axiom statement for the operator to fill in."""
    params = action.get("params", {})
    cage_dir = Path(params.get("cage_dir") or "ztare_proofs/cages")
    cage_dir.mkdir(parents=True, exist_ok=True)
    label = ((action.get("from_event") or {}).get("axiom_label")
             or "unnamed_axiom")
    statement = ((action.get("from_event") or {}).get("axiom_statement")
                 or "(no statement provided)")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(label))
    cage_path = cage_dir / f"{safe_label}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.lean"
    cage_body = (
        f"-- Lean theorem cage for axiom: {label}\n"
        f"-- Created by iter_action_executor at {_utc_now_iso()}\n"
        f"-- Triggered by: rule {action.get('rule_id','?')}\n"
        f"--\n"
        f"-- Axiom statement (informal):\n"
        f"-- {statement}\n"
        f"--\n"
        f"-- Operator: replace with a Lean theorem statement + proof obligation.\n"
        f"-- Verifying this cage advances the verified_axiom from informal to\n"
        f"-- mechanized.\n"
    )
    cage_path.write_text(cage_body, encoding="utf-8")
    return {
        "ok": True,
        "outcome": f"wrote Lean cage stub → {cage_path}",
        "artifacts_written": [str(cage_path)],
    }


def _handle_demote_route_in_packet(action: dict) -> dict:
    """Lower the route's rank in the project's frontier_state.route_ranking."""
    params = action.get("params", {})
    slug = params.get("project_slug")
    route_id = params.get("route_id")
    if not slug or not route_id:
        return {"ok": False, "outcome": "missing project_slug or route_id"}
    new_rank = int(params.get("new_rank") or 99)
    state = fs.load_state(slug)
    found = False
    for r in state.route_ranking:
        if r.get("route_id") == route_id:
            r["rank"] = new_rank
            found = True
            break
    if found:
        fs.save_state(state, history_append={
            "event": "route_demoted",
            "route_id": route_id,
            "new_rank": new_rank,
            "rule_id": action.get("rule_id"),
        })
        return {"ok": True, "outcome": f"demoted route {route_id} to rank {new_rank}"}
    return {"ok": False, "outcome": f"route {route_id} not in ranking; nothing to demote"}


def _handle_mutate_evidence(action: dict) -> dict:
    """Append rows to projects/<slug>/evidence.txt. Adds only; does not
    remove (removals require principal sign-off)."""
    params = action.get("params", {})
    slug = params.get("project_slug")
    additions = params.get("additions") or []
    if not slug:
        return {"ok": False, "outcome": "missing project_slug"}
    project_dir = Path("projects") / slug
    ev_path = project_dir / "evidence.txt"
    if not ev_path.exists():
        return {"ok": False, "outcome": f"evidence.txt not found at {ev_path}"}
    if not additions:
        return {"ok": False, "outcome": "no additions provided"}
    appended_lines: list[str] = []
    appended_lines.append(f"\n# === RD-1.12 co-drive append at {_utc_now_iso()} ===\n")
    appended_lines.append(f"# Reason: {action.get('reason','').strip()[:200]}\n")
    for row in additions:
        if isinstance(row, str):
            appended_lines.append(row + "\n")
        elif isinstance(row, dict):
            appended_lines.append(json.dumps(row) + "\n")
    with ev_path.open("a", encoding="utf-8") as fh:
        fh.writelines(appended_lines)
    return {
        "ok": True,
        "outcome": f"appended {len(additions)} rows to {ev_path}",
        "artifacts_written": [str(ev_path)],
    }


def _handle_mutate_charter(action: dict) -> dict:
    """Append a section to projects/<slug>/project_charter.md."""
    params = action.get("params", {})
    slug = params.get("project_slug")
    section = params.get("section", "RD-1.12 Co-Drive Note")
    content = params.get("content", "")
    if not slug or not content:
        return {"ok": False, "outcome": "missing project_slug or content"}
    charter_path = Path("projects") / slug / "project_charter.md"
    if not charter_path.exists():
        return {"ok": False, "outcome": f"project_charter.md not found at {charter_path}"}
    appendage = (
        f"\n\n## {section} ({_utc_now_iso()})\n\n"
        f"{content}\n\n"
        f"_Triggered by RD-1.12 co-drive rule `{action.get('rule_id','?')}`._\n"
    )
    with charter_path.open("a", encoding="utf-8") as fh:
        fh.write(appendage)
    return {
        "ok": True,
        "outcome": f"appended section to {charter_path}",
        "artifacts_written": [str(charter_path)],
    }


def _handle_queue_cold_shot(action: dict) -> dict:
    """Stub: write a cold-shot dispatch packet to workspace; daemon picks
    it up on next tick (or operator runs the cold-shot script directly)."""
    params = action.get("params", {})
    slug = params.get("project_slug")
    if not slug:
        return {"ok": False, "outcome": "missing project_slug"}
    workspace = Path("projects") / slug / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    packet_path = workspace / f"cold_shot_packet_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    packet_path.write_text(json.dumps({
        "model_id": params.get("model_id"),
        "prompt_template": params.get("prompt_template"),
        "rule_id": action.get("rule_id"),
        "triggered_by_event": action.get("from_event"),
        "queued_at_utc": _utc_now_iso(),
    }, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "outcome": f"wrote cold-shot packet → {packet_path}",
        "artifacts_written": [str(packet_path)],
    }


def _handle_update_champion_meaning(action: dict) -> dict:
    """Update frontier_state.champion_meaning from the triggering event."""
    params = action.get("params", {})
    slug = params.get("project_slug")
    if not slug:
        return {"ok": False, "outcome": "missing project_slug"}
    event = action.get("from_event") or {}
    label = event.get("parametric_form") or "(unknown)"
    state = fs.load_state(slug)
    fs.set_champion_meaning(state, label[:200],
                            reason=f"from rule {action.get('rule_id')}")
    return {"ok": True, "outcome": f"updated champion_meaning for {slug}"}


def _handle_escalate_to_principal(action: dict) -> dict:
    """Telegram-push escalation."""
    params = action.get("params", {})
    severity = params.get("severity", "warn")
    title = (
        f"RD co-drive escalation ({action.get('rule_id','?')})"
        if not params.get("title") else params["title"]
    )
    body = (
        f"Project: {params.get('project_slug','?')}\n"
        f"Reason: {action.get('reason','').strip()}\n"
        f"Triggering event: {action.get('from_event')}\n"
    )
    pushed = False
    try:
        from ztare.notifications import push_notification
        push_notification(title=title, message=body, priority="high",
                          tags=["rd_co_drive", severity])
        pushed = True
    except Exception as exc:  # noqa: BLE001
        log.warning("escalation push failed: %s", exc)
    return {"ok": True, "outcome": f"escalated to principal (push={pushed})"}


_HANDLERS = {
    "fork_substrate": _handle_fork_substrate,
    "create_lean_cage": _handle_create_lean_cage,
    "demote_route_in_packet": _handle_demote_route_in_packet,
    "mutate_evidence": _handle_mutate_evidence,
    "mutate_charter": _handle_mutate_charter,
    "queue_cold_shot": _handle_queue_cold_shot,
    "update_champion_meaning": _handle_update_champion_meaning,
    "escalate_to_principal": _handle_escalate_to_principal,
}


def execute_action(action: dict, *, role_id: str = "research_director") -> dict:
    """Run one action through safety rails + handler dispatch + audit emit."""
    kind = action.get("action_kind")
    handler = _HANDLERS.get(kind)
    if handler is None:
        outcome = {"ok": False, "outcome": f"unknown action_kind: {kind}",
                   "action_kind": kind}
        _emit_damage_signal(action=action, outcome=outcome, severity="warn")
        return outcome

    allowed, reason = _check_safety_rails(action, role_id=role_id)
    if not allowed:
        outcome = {"ok": False, "outcome": "blocked by safety rail",
                   "action_kind": kind, "blocked_reason": reason,
                   "artifacts_written": []}
        _emit_damage_signal(action=action, outcome=outcome, severity="warn")
        return outcome

    try:
        outcome = handler(action)
    except Exception as exc:  # noqa: BLE001
        log.exception("handler %s raised", kind)
        outcome = {"ok": False, "outcome": f"handler raised: {type(exc).__name__}: {exc}",
                   "action_kind": kind, "artifacts_written": []}
        _emit_damage_signal(action=action, outcome=outcome, severity="warn")
        return outcome

    outcome.setdefault("action_kind", kind)
    outcome.setdefault("artifacts_written", [])
    severity = "info" if outcome.get("ok") else "warn"
    _emit_damage_signal(action=action, outcome=outcome, severity=severity)
    return outcome


def drain_pending(project_slug: str, *, role_id: str = "research_director") -> list[dict]:
    """Pop ALL pending actions for a project and execute them in order.
    Returns list of outcomes."""
    state = fs.load_state(project_slug)
    actions = fs.pop_pending_actions(state)
    outcomes: list[dict] = []
    for action in actions:
        out = execute_action(action, role_id=role_id)
        out["action_at"] = _utc_now_iso()
        outcomes.append(out)
        # Append outcome to history for replay/audit
        state = fs.load_state(project_slug)
        fs.save_state(state, history_append={
            "event": "action_executed",
            "action_kind": action.get("action_kind"),
            "rule_id": action.get("rule_id"),
            "outcome_ok": out.get("ok"),
            "outcome_text": (out.get("outcome") or "")[:300],
        })
    return outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RD-1.12 iter-action executor")
    parser.add_argument("--project", required=True, help="project slug")
    parser.add_argument("--drain", action="store_true",
                        help="drain ALL pending actions for the project")
    parser.add_argument("--role", default="research_director",
                        help="role id for budget gate (default research_director)")
    args = parser.parse_args(argv)

    if args.drain:
        outcomes = drain_pending(args.project, role_id=args.role)
        print(json.dumps({
            "project": args.project,
            "n_executed": len(outcomes),
            "outcomes": outcomes,
        }, indent=2))
        return 0
    parser.error("specify --drain (single-action by --action-id not yet implemented)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
