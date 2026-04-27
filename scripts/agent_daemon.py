# Licensed under Business Source License 1.1 — see LICENSE-BSL
#!/usr/bin/env python3
"""Persistent Autonomous Agent Daemon — GP-128 Level 2.

The "sleepless agent." Runs continuously on a VPS (or locally),
performing a tick-based loop:

    discover work → propose to principal (telegram) → wait for
    approval → execute via Claude Code CLI → record → repeat

Architecture:
    ┌─────────────────────────────────┐
    │  PRINCIPAL (human, on phone)    │
    │  Approves/rejects via telegram  │
    └──────────────┬──────────────────┘
                   │ telegram bidirectional
    ┌──────────────▼──────────────────┐
    │  THIS SCRIPT (governance loop)  │
    │  Discovers work, proposes,      │
    │  dispatches, records            │
    └──────────────┬──────────────────┘
                   │ claude --print / subprocess
    ┌──────────────▼──────────────────┐
    │  CLAUDE CODE CLI (execution)    │
    │  Runs in --print mode per task  │
    └─────────────────────────────────┘

The daemon does NOT call LLMs directly. It orchestrates Claude Code
CLI invocations, which handle their own context, tool use, and
session management. The daemon is a GOVERNANCE LAYER, not an
execution engine.

Prerequisites:
    1. python scripts/telegram_setup.py  (one-time)
    2. Claude Code CLI installed and authenticated
    3. ANTHROPIC_API_KEY / OPENAI_API_KEY in environment

Usage:
    python scripts/agent_daemon.py                    # run forever
    python scripts/agent_daemon.py --tick-once        # single tick (for testing)
    python scripts/agent_daemon.py --dry-run          # discover + propose, don't execute
    python scripts/agent_daemon.py --interval 300     # tick every 5 min (default: 10 min)

Deployment (VPS):
    # systemd unit at deploy/agent-daemon.service
    # Or: screen -dmS agent python scripts/agent_daemon.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make repo imports work
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from src.ztare.orchestration.work_discovery import discover_all as discover_candidates, Candidate
from src.ztare.signals.damage import emit as emit_damage, list_recent as recent_damage
from src.ztare.sessions.enforce import ensure_session, require_no_conflict
from src.ztare.signals.autoemit import check_mandate_drift

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [daemon] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent_daemon")

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_INTERVAL = 600  # 10 minutes
MANDATE_PATH = REPO_ROOT / "org" / "mandates" / "manager_mandate.md"
MAX_TASK_DURATION = 3600  # 1 hour max per task
PROPOSAL_TIMEOUT = 1800  # 30 min to wait for principal approval


# ── Telegram helpers ──────────────────────────────────────────────────

def telegram_available() -> bool:
    try:
        from src.ztare.notifications.telegram import _load_creds
        _load_creds()
        return True
    except Exception:
        return False


def send_telegram(message: str, priority: str = "normal") -> bool:
    try:
        from src.ztare.notifications.telegram import push_notification
        push_notification(
            title="Agent Daemon",
            message=message,
            priority=priority,
        )
        return True
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")
        return False


def poll_telegram() -> list[dict]:
    try:
        from src.ztare.notifications.telegram import poll_inbound
        return [msg.__dict__ if hasattr(msg, '__dict__') else msg
                for msg in poll_inbound(consume=True)]
    except Exception:
        return []


# ── Work discovery ────────────────────────────────────────────────────

def discover_work() -> list[Candidate]:
    """Find work worth doing. Returns ranked candidates."""
    try:
        candidates = list(discover_candidates())
        log.info(f"Discovered {len(candidates)} candidate(s)")
        return candidates
    except Exception as e:
        log.error(f"Work discovery failed: {e}")
        return []


# ── Task execution via Claude Code CLI ────────────────────────────────

def execute_task(task_description: str, project: str | None = None) -> dict:
    """Execute a task by spawning Claude Code CLI.

    Uses `claude --print` for non-interactive execution. The CLI
    manages its own context, tools, and session. We just pass the
    task description and collect the output.
    """
    cmd = ["claude", "--print"]
    if project:
        cmd.extend(["--project", str(REPO_ROOT)])

    # Build the prompt with governance context
    prompt = f"""You are the autonomous manager agent for this repository.
Read org/mandates/manager_mandate.md for your scope and authorization.
Read docs/internal/agent_task_discipline_map.md for procedural requirements.

TASK: {task_description}

IMPORTANT:
- Follow the experiment cookbook (docs/guides/experiment_cookbook.md)
- Run validate_agent_task_discipline.py post <task_type> before declaring done
- Record all findings in EXPERIMENT_TRACK_RECORD.md
- Push-notify via telegram on completion or if you need a decision
"""
    cmd.extend(["-p", prompt])

    log.info(f"Executing: {task_description[:80]}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_TASK_DURATION,
            cwd=str(REPO_ROOT),
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "stdout": "", "stderr": ""}
    except FileNotFoundError:
        return {"success": False, "error": "claude CLI not found", "stdout": "", "stderr": ""}


# ── Governance checks ─────────────────────────────────────────────────

def check_control_signal(role_id: str) -> str | None:
    """Check org/controls/{role_id}.json for STOP/PAUSE/RESUME."""
    control_path = REPO_ROOT / "org" / "controls" / f"{role_id}.json"
    if control_path.exists():
        try:
            data = json.loads(control_path.read_text())
            return data.get("action")
        except Exception:
            pass
    return None


def read_directives(role_id: str) -> list[str]:
    """Read and consume pending directives for this role."""
    directives_dir = REPO_ROOT / "org" / "directives"
    results = []
    if not directives_dir.exists():
        return results
    for f in sorted(directives_dir.iterdir()):
        if f.suffix == '.json' and role_id in f.name:
            try:
                data = json.loads(f.read_text())
                if not data.get("consumed"):
                    results.append(data.get("message", ""))
                    # Mark as consumed
                    data["consumed"] = True
                    data["consumed_utc"] = datetime.now(timezone.utc).isoformat()
                    f.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
    return results


def pre_tick_checks(session, role_id: str = "manager") -> list[str]:
    """Run governance checks before each tick. Returns warnings."""
    warnings = []

    # Check control signals (STOP/PAUSE/RESUME from dashboard)
    control = check_control_signal(role_id)
    if control == "STOP":
        warnings.append("STOP directive received from dashboard")
    elif control == "PAUSE":
        warnings.append("PAUSE directive received from dashboard")

    # Check directives
    directives = read_directives(role_id)
    for d in directives:
        warnings.append(f"Inbound directive: {d[:200]}")

    # Check mandate drift
    try:
        check_mandate_drift()
    except Exception as e:
        warnings.append(f"Mandate drift check failed: {e}")

    # Check unresolved damage signals
    try:
        signals = recent_damage()
        if signals:
            warnings.append(f"{len(signals)} unresolved damage signal(s)")
    except Exception:
        pass

    # Check for pending inbound directives
    messages = poll_telegram()
    for msg in messages:
        text = msg.get("text", "") if isinstance(msg, dict) else str(msg)
        upper = text.strip().upper()
        if upper == "STOP":
            warnings.append("STOP directive received from principal")
        elif upper == "PAUSE":
            warnings.append("PAUSE directive received from principal")
        elif upper == "STATUS":
            send_telegram(f"Daemon running. Last tick: {datetime.now(timezone.utc).isoformat()}")
        elif text.strip():
            warnings.append(f"Inbound directive: {text[:100]}")

    return warnings


# ── Main tick ─────────────────────────────────────────────────────────

def tick(session, role_id: str = "manager", dry_run: bool = False) -> None:
    """One governance tick: discover → propose → (approve) → execute → record."""

    log.info(f"─── tick start ({role_id}) ───")

    # 1. Pre-tick governance checks
    warnings = pre_tick_checks(session, role_id=role_id)
    for w in warnings:
        log.warning(w)
        if "STOP" in w:
            log.info("STOP received. Exiting.")
            send_telegram("Daemon stopped by principal STOP directive.")
            sys.exit(0)
        if "PAUSE" in w:
            log.info("PAUSE received. Sleeping 30 min.")
            send_telegram("Daemon paused for 30 min. Send RESUME to wake.")
            time.sleep(1800)
            return

    # 2. Discover work
    candidates = discover_work()
    if not candidates:
        log.info("No work discovered. Idle tick.")
        return

    # 3. Rank and propose top candidate
    top = candidates[0]
    proposal = f"Proposed task: {top.intent}\nSource: {top.source}\nSignal: {top.scarcity_signal}"
    log.info(f"Top candidate: {top.intent[:80]}")

    if dry_run:
        log.info(f"DRY RUN — would propose: {proposal}")
        return

    # 4. Notify principal and wait for approval (if telegram available)
    if telegram_available():
        send_telegram(
            f"🔍 Work discovered:\n{proposal}\n\nReply APPROVE to execute, SKIP to defer, STOP to halt daemon.",
            priority="high",
        )

        # Wait for approval
        log.info("Waiting for principal approval via telegram...")
        deadline = time.time() + PROPOSAL_TIMEOUT
        approved = False
        while time.time() < deadline:
            time.sleep(30)  # poll every 30s
            messages = poll_telegram()
            for msg in messages:
                text = (msg.get("text", "") if isinstance(msg, dict) else str(msg)).strip().upper()
                if text == "APPROVE":
                    approved = True
                    break
                elif text == "SKIP":
                    log.info("Principal skipped this task.")
                    return
                elif text == "STOP":
                    log.info("STOP received during approval wait.")
                    send_telegram("Daemon stopped.")
                    sys.exit(0)
            if approved:
                break

        if not approved:
            log.info("Approval timeout. Deferring task.")
            send_telegram("⏰ Approval timeout. Task deferred to next tick.")
            return

        log.info("Principal approved. Executing...")
    else:
        # No telegram — auto-execute (local mode)
        log.info("No telegram configured. Auto-executing...")

    # 5. Execute
    result = execute_task(top.intent)

    # 6. Record
    log.info(f"Task complete. Success: {result['success']}")
    if telegram_available():
        status = "✅" if result["success"] else "❌"
        summary = result.get("stdout", "")[-500:] or result.get("error", "unknown")
        send_telegram(f"{status} Task finished: {top.intent[:60]}\n\n{summary[:300]}")

    # 7. Write to session log
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": top.intent,
        "source": top.source,
        "success": result["success"],
        "duration_s": MAX_TASK_DURATION,  # approximate
    }
    log_path = REPO_ROOT / "workspace" / "agent_daemon_log.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    log.info("─── tick end ───")


# ── Entry point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Persistent Autonomous Agent Daemon")
    parser.add_argument("--role", type=str, default="manager",
                        choices=["manager", "research_director"],
                        help="Which role this daemon instance fills (default: manager)")
    parser.add_argument("--tick-once", action="store_true", help="Run one tick and exit")
    parser.add_argument("--dry-run", action="store_true", help="Discover and propose, don't execute")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Seconds between ticks (default: 600)")
    args = parser.parse_args()

    log.info("═══════════════════════════════════════")
    log.info("  Agent Daemon — GP-128 Level 2")
    log.info("═══════════════════════════════════════")
    role_id = args.role
    mandate_path = REPO_ROOT / "org" / "mandates" / f"{role_id}_mandate.md"
    if role_id == "manager":
        mandate_path = MANDATE_PATH  # legacy path

    log.info(f"  Role: {role_id}")
    log.info(f"  Interval: {args.interval}s")
    log.info(f"  Telegram: {'available' if telegram_available() else 'NOT configured (run scripts/telegram_setup.py)'}")
    log.info(f"  Mandate: {mandate_path}")
    log.info(f"  Dry run: {args.dry_run}")
    log.info("")

    # Open session
    session = ensure_session(
        role_id=role_id,
        member_id="claude",
        substrate="daemon",
        mandate_path=mandate_path,
    )
    log.info(f"Session: {session.session_id if hasattr(session, 'session_id') else 'opened'}")

    if args.tick_once:
        tick(session, role_id=role_id, dry_run=args.dry_run)
        return

    # Main loop
    log.info(f"Entering main loop (tick every {args.interval}s). Send STOP via telegram or dashboard to halt.")
    if telegram_available():
        send_telegram(f"🟢 Agent daemon started. Tick interval: {args.interval}s. Send STOP to halt.")

    while True:
        try:
            tick(session, role_id=role_id, dry_run=args.dry_run)
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt. Shutting down.")
            if telegram_available():
                send_telegram("🔴 Agent daemon stopped (keyboard interrupt).")
            break
        except Exception as e:
            log.error(f"Tick failed: {e}")
            emit_damage(
                kind="daemon_tick_failure",
                severity="high",
                detail=str(e)[:500],
            )
            if telegram_available():
                send_telegram(f"⚠️ Daemon tick failed: {e}", priority="high")

        log.info(f"Sleeping {args.interval}s until next tick...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
