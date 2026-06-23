# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Persistent Autonomous Agent Daemon — GP-128 Level 2.

The "sleepless agent." Runs continuously on a VPS (or locally),
performing a tick-based loop:

    discover work → propose to principal (gate rail) → wait for
    approval → execute via configured agent CLI → record → repeat

Architecture:
    ┌─────────────────────────────────┐
    │  PRINCIPAL (human, on phone)    │
    │  Approves/rejects via gate rail │
    └──────────────┬──────────────────┘
                   │ filesystem / Orbit / tenant notification
    ┌──────────────▼──────────────────┐
    │  THIS SCRIPT (governance loop)  │
    │  Discovers work, proposes,      │
    │  dispatches, records            │
    └──────────────┬──────────────────┘
                   │ agent CLI subprocess
    ┌──────────────▼──────────────────┐
    │  AGENT RUNTIME (execution)      │
    │  Runs in print/task mode        │
    └─────────────────────────────────┘

The daemon does NOT call LLMs directly. It orchestrates a configured
role-bearing agent runtime, which handles its own context, tool use, and
session management. The daemon is a GOVERNANCE LAYER, not an execution
engine.

Prerequisites:
    1. Configure a notification provider if you want push/mobile approval.
    2. Agent CLI installed and authenticated (`ZTARE_AGENT_CLI`, default: claude)
    3. ANTHROPIC_API_KEY / OPENAI_API_KEY in environment

Usage:
    python scripts/public/control/agent_daemon.py                    # run forever
    python scripts/public/control/agent_daemon.py --role research_director
    python scripts/public/control/agent_daemon.py --tick-once        # single tick (for testing)
    python scripts/public/control/agent_daemon.py --dry-run          # discover + propose, don't execute
    python scripts/public/control/agent_daemon.py --unattended       # execute in-scope work without approval
    python scripts/public/control/agent_daemon.py --interval 300     # tick every 5 min (default: 10 min)

Deployment (VPS):
    # systemd unit at deploy/agent-daemon.service
    # Or: screen -dmS agent python scripts/public/control/agent_daemon.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make repo imports work
REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_SRC = REPO_ROOT / "src"
sys.path.insert(0, str(REPO_SRC))
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from ztare.orchestration.work_discovery import discover_all as discover_candidates, Candidate
from ztare.orchestration.command_surface import command_surface_hint
from ztare.orchestration.execution_routing import infer_execution_route, render_route_contract
from ztare.orchestration.task_authorization import authorize_dispatch
from ztare.orchestration.transition_log import append_transition
from ztare.orchestration.daemon_continuity import (
    get_or_create_claude_session_id,
    note_tick as continuity_note_tick,
    write_task_checkpoint,
    read_task_checkpoint,
)
from ztare.signals.damage import emit as emit_damage, list_recent as recent_damage
from ztare.sessions.enforce import ensure_session, require_no_conflict
from ztare.signals.autoemit import check_mandate_drift

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [daemon] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent_daemon")

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_INTERVAL = 600  # 10 minutes (legacy default; kept for back-compat)
# Variable tick cadence: tighter when work is in flight (stays inside Claude's
# 5-min cache TTL = 300s), wider when idle (no point burning cache 12× per
# hour for nothing). The daemon switches based on whether the prior tick
# claimed work — see compute_next_interval().
ACTIVE_TICK_INTERVAL = 270   # under 5-min cache TTL; ~13 ticks/hr
IDLE_TICK_INTERVAL = 1200    # 20 min; ~3 ticks/hr
MANDATE_PATH = REPO_ROOT / "org" / "mandates" / "manager_mandate.md"
MAX_TASK_DURATION = 3600  # 1 hour max per task
PROPOSAL_TIMEOUT = 1800  # 30 min to wait for principal approval
GATES_PENDING_DIR = REPO_ROOT / "ztare_workspace" / "gates" / "pending"
GATES_RESOLVED_DIR = REPO_ROOT / "ztare_workspace" / "gates" / "resolved"
GATE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
AGENT_ADAPTERS = ("claude_print", "codex_exec")
RD_TICK_BRIEF = REPO_ROOT / "scripts" / "public" / "control" / "rd_tick_brief.py"
RD_TICK_BRIEF_RECEIPT = REPO_ROOT / "analytics" / "public" / "queries" / "rd" / "rd_tick_brief_latest.txt"
ROLE_TICK_SURFACES = {
    "research_director": {
        "label": "Research Director tick brief",
        "receipt": RD_TICK_BRIEF_RECEIPT,
        "excerpt_markers": ("## §7.", "## §9."),
        "failure_message": (
            "RD tick brief failed; inspect "
            "analytics/public/queries/rd/rd_tick_brief_latest.txt before dispatch"
        ),
    },
}


# ── Optional notification helpers ─────────────────────────────────────

def notification_provider_available() -> bool:
    provider = os.environ.get("ZTARE_NOTIFICATION_PROVIDER", "filesystem").strip().lower()
    if provider in {"", "none", "off", "disabled"}:
        return False
    if provider == "filesystem":
        return True
    if provider == "telegram":
        try:
            from ztare.notifications.telegram import _load_creds
            _load_creds()
            return True
        except Exception:
            return False
    return True


def telegram_available() -> bool:
    return notification_provider_available()


def send_notification(message: str, priority: str = "normal", gate_id: Optional[str] = None) -> bool:
    """Push through the configured notification provider when available.

    If a provider supports gate buttons, ``gate_id`` can be rendered as
    APPROVE/SKIP/STOP. Filesystem gates remain authoritative either way.
    """
    if not notification_provider_available():
        return False
    try:
        from ztare.notifications import push_notification
        if gate_id:
            # Compact callback_data: action:gate_id_short (≤64 bytes total).
            short = gate_id[-32:] if len(gate_id) > 32 else gate_id
            message = (
                f"{message}\n\n"
                f"Gate actions: APPROVE {short} / SKIP {short} / STOP {short}"
            )
        push_notification(
            title="Agent Daemon",
            message=message,
            priority=priority,
        )
        return True
    except Exception as e:
        log.warning(f"notification send failed: {e}")
        return False


def send_telegram(message: str, priority: str = "normal", gate_id: Optional[str] = None) -> bool:
    return send_notification(message, priority=priority, gate_id=gate_id)


def poll_telegram() -> list[dict]:
    try:
        from ztare.notifications.telegram import authorized_messages, poll_inbound
        messages = poll_inbound(consume=True)
        for msg in messages:
            if not getattr(msg, "authorized", False):
                emit_damage(
                    source="agent_daemon.notification",
                    kind="unauthorized_notification_message",
                    detail=f"Rejected unauthorized notification message command={getattr(msg, 'command', 'unknown')}",
                    severity="warn",
                )
        return [msg.__dict__ if hasattr(msg, '__dict__') else msg
                for msg in authorized_messages(messages)]
    except Exception:
        return []


# ── Work discovery ────────────────────────────────────────────────────

def _scope_norm(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _candidate_in_tick_scope(candidate: Candidate, tick_scope: str | None) -> bool:
    scope = _scope_norm(tick_scope)
    if not scope or scope in {"all", "global"}:
        return True
    parts: list[str] = []
    for key in ("project_slug", "substrate", "goal_id", "source", "kind"):
        value = (candidate.metadata or {}).get(key)
        if isinstance(value, str):
            parts.append(value)
    fm = (candidate.metadata or {}).get("frontmatter")
    if isinstance(fm, dict):
        for key in ("project", "project_slug", "substrate", "goal_slug"):
            value = fm.get(key)
            if isinstance(value, str):
                parts.append(value)
    if candidate.origin_path is not None:
        parts.append(str(candidate.origin_path))
    parts.extend([candidate.source, candidate.intent, candidate.raw_text])
    return any(scope in _scope_norm(part) for part in parts if part)


def discover_work(role_id: str = "manager", *, tick_scope: str | None = None) -> list[Candidate]:
    """Find work worth doing. Returns ranked candidates.

    For research_director (RD-1.12, 2026-05-02): if no explicit tasks
    exist in the inbox AND no candidates surfaced from the standard
    discoverer, generate PROACTIVE PROBE CANDIDATES from active project
    state. The principal explicitly does not want the agent to sit idle
    when there are unresolved scientific questions in the priority axes
    (org/preferences/principal.yaml). Sources for proactive probes:

      - frontier_state.pending_actions: actions queued by the policy
        dispatcher that the agent should drain.
      - verified_axioms.json without external_consistency_checks: RD's
        canonical trigger (skeptic dossier generation).
      - recent project workspace activity: if a project's iter loop has
        run in the last 24h and frontier_state shows non-trivial state,
        propose a "live co-drive review" candidate.
    """
    try:
        candidates = list(discover_candidates(assigned_to=f"role.{role_id}"))
        log.info(f"Discovered {len(candidates)} candidate(s) from inbox")
    except Exception as e:
        log.error(f"Work discovery failed: {e}")
        candidates = []

    # RD-1.12 proactive probe discovery
    if role_id == "research_director":
        try:
            proactive = _proactive_rd_candidates()
            if proactive:
                log.info(f"RD-1.12 proactive: {len(proactive)} probe candidate(s) "
                         f"from active project state")
            candidates.extend(proactive)
        except Exception as e:
            log.warning(f"RD-1.12 proactive discovery failed (non-fatal): {e}")

    scope = _scope_norm(tick_scope)
    if scope and scope not in {"all", "global"}:
        before = len(candidates)
        candidates = [c for c in candidates if _candidate_in_tick_scope(c, tick_scope)]
        log.info(
            f"Tick scope `{tick_scope}` retained {len(candidates)}/{before} "
            "candidate(s)"
        )

    return candidates


def _verify_post_tick_engagement(*, start_ts: float,
                                   project_slug: str | None) -> bool:
    """RD-1.12 post-tick verification (2026-05-02).

    True iff at least one of these advanced after start_ts:
      - ztare_workspace/transitions.jsonl gained a new row (any new audit)
      - frontier_state.<slug>.json updated_utc is past start_ts
      - frontier_state.<slug>.json history gained a new row

    Used by the daemon to detect the "debrief halt" failure mode where the
    agent returns successfully but actually did nothing.
    """
    advanced = False
    transitions_path = REPO_ROOT / "ztare_workspace" / "transitions.jsonl"
    if transitions_path.exists():
        try:
            mtime = transitions_path.stat().st_mtime
            if mtime > start_ts:
                advanced = True
        except Exception:
            pass
    if not advanced and project_slug:
        try:
            state_path = REPO_ROOT / "ztare_workspace" / "frontier_state" / f"{project_slug}.json"
            if state_path.exists():
                if state_path.stat().st_mtime > start_ts:
                    advanced = True
        except Exception:
            pass
    return advanced


def _proactive_rd_candidates() -> list[Candidate]:
    """Surface RD work from active project state when the inbox is empty.

    Three sources, ordered by signal strength:
      1. frontier_state.pending_actions queues (highest: policy says do this NOW)
      2. unreviewed verified axioms (RD's canonical trigger)
      3. recent iter activity (live co-drive context)
    """
    proactive: list[Candidate] = []
    projects_root = REPO_ROOT / "projects"
    if not projects_root.exists():
        return proactive

    def autonomous_project_dirs() -> list[Path]:
        return [
            p for p in sorted(projects_root.iterdir())
            if p.is_dir() and not p.is_symlink()
        ]

    # Source 1: pending_actions queues
    try:
        from ztare.role_extensions.frontier_state import (
            STATE_ROOT, load_state, _validate_slug,
        )
        if STATE_ROOT.exists():
            for f in STATE_ROOT.glob("*.json"):
                slug = f.stem
                try:
                    _validate_slug(slug)
                except ValueError:
                    continue
                try:
                    state = load_state(slug)
                except Exception:
                    continue
                n_pending = len(state.pending_actions or [])
                if n_pending > 0:
                    proactive.append(Candidate(
                        source=f"frontier_state:{slug}",
                        intent=(
                            f"Drain {n_pending} pending action(s) for "
                            f"`{slug}` per iter_action_policy. Run: "
                            f"`python -m src.ztare.role_extensions.iter_action_executor "
                            f"--project {slug} --drain`. "
                            f"After draining, advance the frontier or escalate."
                        ),
                        origin_path=f,
                        scarcity_signal="policy_actions_queued",
                        raw_text=f"{n_pending} actions queued",
                        severity="warn" if n_pending >= 3 else "info",
                        age_days=None,
                        metadata={"project_slug": slug, "n_pending": n_pending},
                    ))
    except Exception as exc:  # noqa: BLE001
        log.debug(f"frontier_state probe scan failed: {exc}")

    # Source 2: unreviewed verified axioms
    try:
        for proj in autonomous_project_dirs():
            axiom_file = proj / "verified_axioms.json"
            if not axiom_file.exists():
                continue
            try:
                data = json.loads(axiom_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            axioms = data.get("axioms") if isinstance(data, dict) else data
            if not isinstance(axioms, list):
                continue
            unreviewed = [
                a for a in axioms
                if isinstance(a, dict)
                and not a.get("external_consistency_checks")
                and a.get("status") in (None, "verified_axiom")
            ]
            if unreviewed:
                proactive.append(Candidate(
                    source=f"verified_axioms:{proj.name}",
                    intent=(
                        f"Generate skeptic dossier for {len(unreviewed)} "
                        f"unreviewed verified axiom(s) in `{proj.name}`. "
                        f"Per research_director_mandate Phase 1: read each "
                        f"axiom + evidence + substrate context and write "
                        f"3-5 likely reviewer attacks per axiom to "
                        f"`projects/{proj.name}/workspace/skeptic_dossier.md`."
                    ),
                    origin_path=axiom_file,
                    scarcity_signal="unreviewed_axioms",
                    raw_text=f"{len(unreviewed)} axioms without external_consistency_checks",
                    severity="warn",
                    age_days=None,
                    metadata={"project_slug": proj.name, "n_axioms": len(unreviewed)},
                ))
    except Exception as exc:  # noqa: BLE001
        log.debug(f"verified_axioms scan failed: {exc}")

    # Source 3: recent iter activity (only if we have nothing else)
    if not proactive:
        try:
            from datetime import datetime as _dt, timezone as _tz
            now = _dt.now(_tz.utc)
            for proj in autonomous_project_dirs():
                eval_file = proj / "workspace" / "eval_history.jsonl"
                if not eval_file.exists():
                    continue
                mtime = _dt.fromtimestamp(eval_file.stat().st_mtime, tz=_tz.utc)
                age_h = (now - mtime).total_seconds() / 3600.0
                if age_h <= 24:
                    proactive.append(Candidate(
                        source=f"recent_iter_activity:{proj.name}",
                        intent=(
                            f"Live co-drive review of `{proj.name}` "
                            f"(eval_history.jsonl modified {age_h:.1f}h ago). "
                            f"Run: `python -m src.ztare.role_extensions.frontier_runner` "
                            f"to scan for new events; then drain queued actions; "
                            f"if no actions queued, write a co-drive note to "
                            f"`projects/{proj.name}/workspace/frontier_co_drive_log.md` "
                            f"summarizing what changed and what to probe next."
                        ),
                        origin_path=eval_file,
                        scarcity_signal="recent_iter_activity",
                        raw_text=f"eval_history modified {age_h:.1f}h ago",
                        severity="info",
                        age_days=age_h / 24.0,
                        metadata={"project_slug": proj.name, "age_hours": round(age_h, 2)},
                    ))
        except Exception as exc:  # noqa: BLE001
            log.debug(f"recent_iter_activity scan failed: {exc}")

    # Sort by severity (warn > info), then by signal strength
    severity_rank = {"critical": 0, "warn": 1, "info": 2}
    proactive.sort(key=lambda c: (severity_rank.get(c.severity, 3),
                                    c.source))
    return proactive


# ── Task execution via configured agent CLI ───────────────────────────

def infer_agent_adapter(agent_cli: str, requested: str = "auto") -> str:
    """Resolve the runtime adapter for a CLI command."""
    if requested != "auto":
        if requested not in AGENT_ADAPTERS:
            raise ValueError(f"unsupported agent adapter: {requested}")
        return requested
    name = Path(agent_cli).name.lower()
    if name == "codex":
        return "codex_exec"
    return "claude_print"


def build_agent_command(
    *,
    agent_cli: str,
    adapter: str,
    prompt: str,
    project: str | None = None,
    claude_session_id: str | None = None,
    claude_session_is_new: bool = False,
) -> list[str]:
    """Build a noninteractive command for the configured role runtime.

    Autonomous-mode discipline (RD-1.12, 2026-05-02): the daemon is the
    principal-authorized layer. The agent CLI inside a tick must NOT ask
    for human approval on tool calls — if it does, the tick hangs or
    returns early, breaking the cron-style cadence the daemon depends on.
    Codex: `--ask-for-approval never` (already set). Claude Code:
    `--permission-mode acceptEdits` (auto-accepts file edits; risky ops
    still escalate via the org/signals/damage/ channel rather than via the
    CLI's permission prompt). Override via env ZTARE_CLAUDE_PERMISSION_MODE.

    Cross-tick continuity (2026-05-05): when `claude_session_id` is provided
    and the adapter is claude_print, the command uses `--session-id` on
    first use of the id and `--resume` on subsequent uses. This preserves
    Claude Code's conversation memory across ticks so the agent doesn't
    rebuild context every 5–20 minutes. Codex's `codex exec` does not
    support resume; the codex_exec branch ignores the session params.
    """
    if adapter == "claude_print":
        permission_mode = os.environ.get("ZTARE_CLAUDE_PERMISSION_MODE", "acceptEdits")
        cmd = [agent_cli, "--print", "--permission-mode", permission_mode]
        if claude_session_id:
            if claude_session_is_new:
                cmd.extend(["--session-id", claude_session_id])
            else:
                cmd.extend(["--resume", claude_session_id])
        if project:
            cmd.extend(["--project", str(REPO_ROOT)])
        cmd.extend(["-p", prompt])
        return cmd
    if adapter == "codex_exec":
        cmd = [
            agent_cli,
            "exec",
            "--cd",
            str(REPO_ROOT),
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "never",
        ]
        cmd.append(prompt)
        return cmd
    raise ValueError(f"unsupported agent adapter: {adapter}")


def _format_bootstrap_chain_for_prompt(*, role_id: str) -> str:
    """Format the bootstrap-chain reads from `org/bootstrap_manifest.yaml`.

    Falls back to the historical hardcoded list if the manifest is missing
    or unparseable, so a stale checkout still produces a working prompt.

    Returns multi-line markdown with required and conditional reads, with
    `{role_id}` placeholders substituted.
    """
    manifest_path = REPO_ROOT / "org" / "bootstrap_manifest.yaml"
    fallback = (
        "First read AGENTS.md (start with §0–§5b — the MUST-READ subset).\n"
        f"Read org/roles/{role_id}.yaml for your durable role contract.\n"
        f"Read org/mandates/{role_id}_mandate.md for your scope and authorization.\n"
        "Read org/preferences/principal.yaml for the principal's current research-taste routing preferences.\n"
        "Read docs/guides/org_runtime_quickstart.md if you need the role-daemon boot model.\n"
        "Read docs/internal/agent_workflow/agent_task_discipline_map.md for procedural requirements."
    )
    if not manifest_path.exists():
        return fallback
    try:
        import yaml  # type: ignore
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception:                                                       # noqa: BLE001
        return fallback
    if not isinstance(manifest, dict):
        return fallback

    lines: list[str] = []
    required = manifest.get("required_reads") or []
    if required:
        lines.append("Required reads (in order):")
        for entry in required:
            if not isinstance(entry, dict):
                continue
            path = (entry.get("path") or "").format(role_id=role_id)
            purpose = entry.get("purpose") or ""
            optional_for = entry.get("optional_for_roles") or []
            if role_id in optional_for:
                fb = entry.get("fallback_when_absent") or "if absent, fall back to role yaml + AGENTS.md"
                lines.append(f"- {path} — {purpose} (optional for `{role_id}`: {fb})")
            else:
                lines.append(f"- {path} — {purpose}")
    conditional = manifest.get("conditional_reads") or []
    if conditional:
        lines.append("")
        lines.append("Conditional reads (consult when relevant to the task):")
        for entry in conditional:
            if not isinstance(entry, dict):
                continue
            path = (entry.get("path") or "").format(role_id=role_id)
            purpose = entry.get("purpose") or ""
            lines.append(f"- {path} — {purpose}")
    return "\n".join(lines) if lines else fallback


def _role_tick_surface_command(role_id: str, tick_scope: str | None) -> list[str] | None:
    """Return the registered pre-tick surface command for a role, if any."""
    if role_id == "research_director":
        return [
            sys.executable,
            str(RD_TICK_BRIEF),
            "--short",
            "--vps",
            "--last-n-catches",
            "3",
            "--last-n-pls",
            "3",
            "--blocking-substrate",
            tick_scope or "global",
        ]
    return None


def _format_role_tick_surface_for_prompt(*, role_id: str, max_chars: int = 8000) -> str:
    """Return the action-relevant registered pre-tick receipt excerpt."""
    config = ROLE_TICK_SURFACES.get(role_id)
    if not config:
        return ""
    receipt_path = config.get("receipt")
    if not isinstance(receipt_path, Path) or not receipt_path.exists():
        return ""
    try:
        text = receipt_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""

    start = -1
    for marker in config.get("excerpt_markers", ()):
        if not isinstance(marker, str):
            continue
        start = text.find(marker)
        if start >= 0:
            break
    if start < 0:
        excerpt = text
    else:
        excerpt = text[start:]

    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "\n... [role pre-tick surface truncated]"
    label = str(config.get("label") or f"{role_id} tick surface")
    return (
        f"\nROLE PRE-TICK SURFACE: {label} "
        "(generated this daemon tick; use this before dispatch):\n"
        f"Receipt: {receipt_path.relative_to(REPO_ROOT)}\n"
        f"{excerpt}\n"
    )


def execute_task(
    task_description: str,
    project: str | None = None,
    *,
    role_id: str = "manager",
    mandate_path: Path | None = None,
    agent_cli: str = "claude",
    agent_adapter: str = "auto",
    use_resume: bool = True,
    org_session_id: str | None = None,
) -> dict:
    """Execute a task by spawning the configured agent CLI.

    The CLI manages its own context, tools, and session. We pass the task
    description and collect output; governance remains in this daemon.

    When `use_resume` is True (default) and the adapter is claude_print,
    the spawned process uses `--session-id` (first use) / `--resume` so
    the agent's conversation memory persists across ticks. Pass
    `use_resume=False` to force fresh session per call. `org_session_id`
    is the org/sessions/ id and is only used to write the per-tick
    checkpoint at org/sessions/<id>/state.json.
    """
    try:
        adapter = infer_agent_adapter(agent_cli, agent_adapter)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "stdout": "", "stderr": ""}

    role_path = REPO_ROOT / "org" / "roles" / f"{role_id}.yaml"
    if mandate_path is None:
        mandate_path = REPO_ROOT / "org" / "mandates" / f"{role_id}_mandate.md"

    # Cross-tick continuity: get-or-create the persistent Claude session
    # id for this role. Stale sessions (tick_count >= 100 OR age >= 24h)
    # are auto-rotated to keep conversation length bounded.
    claude_session_id: str | None = None
    claude_session_is_new = False
    if use_resume and adapter == "claude_print":
        try:
            sess = get_or_create_claude_session_id(role_id=role_id)
            claude_session_id = sess.claude_session_id
            claude_session_is_new = sess.is_new
            log.info(
                f"Claude session: {claude_session_id[:8]}… "
                f"({'new' if claude_session_is_new else 'resume'}; tick {sess.tick_count})"
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(f"continuity: get_or_create failed; running fresh: {exc}")

    # Build the prompt with governance context. Reads from the canonical
    # bootstrap manifest at org/bootstrap_manifest.yaml so adding a 7th
    # required-read file is a YAML edit not a Python source edit.
    bootstrap_lines = _format_bootstrap_chain_for_prompt(role_id=role_id)
    role_tick_surface = _format_role_tick_surface_for_prompt(role_id=role_id)

    # Per-task checkpoint: surface prior-tick conclusion to the agent.
    prior_checkpoint_hint = ""
    if org_session_id:
        prior = read_task_checkpoint(org_session_id)
        if prior and prior.get("status") not in (None, "no_work"):
            prior_summary = prior.get("last_summary") or ""
            prior_status = prior.get("status") or ""
            prior_intent = prior.get("task_intent") or ""
            prior_checkpoint_hint = (
                "\nPRIOR TICK CHECKPOINT (read first, decide if it's still decision-critical):\n"
                f"- last status: {prior_status}\n"
                f"- last task: {prior_intent[:200]}\n"
                f"- last summary: {prior_summary[:400]}\n"
            )

    prompt = f"""You are the autonomous {role_id} role for this repository.

{bootstrap_lines}

{role_tick_surface}

TASK: {task_description}

IMPORTANT:
- Command-first rule: if the repo already has a stable `make` target,
  script, or Python entrypoint for this action, use it. Do not invent a
  throwaway ad hoc script when a reusable command already exists.
- If you author new Python, make it a reusable mechanized primitive in
  `scripts/public/` or `src/`; do not hide one-off logic in an unrelated shell
  wrapper.
- Obey the EXECUTION ROUTE CONTRACT inside the task. Before executing, write the required_first_artifact named there.
- If the route is `route_only`, decide the route and create the next task; do not execute a live run.
- If the route is `artifact_build` and you are a director/reviewer role, write the artifact_build_spec.md and a handoff task for an authorized builder role; do not silently edit implementation artifacts.
- If the route is `experiment_loop`, run the implementation-specific preflight substrate audit first; do not launch if the contract/gates are unstable.
- If the ROLE PRE-TICK SURFACE contains "PATTERN ACTIVATION GUARD FIRING", use the named pattern chain before dispatch OR record the deviation reason in the F-row / closure artifact. Treat this as a role-tick gate, not a reminder.
- If the ROLE PRE-TICK SURFACE contains "Structural vocabulary fingerprint", include a structural_language_fingerprint in closure/F-rows/advisor artifacts: universal v5 ops + TB/PS culture, and GP-219 PDE ops when the substrate is PDE/analysis leaning.
- Conflict resolution: see `docs/internal/agent_workflow/agent_conflict_resolution_table.md` (canonical priority is in `org/bootstrap_manifest.yaml` under `conflict_resolution_priority`). When in doubt, the role yaml `forbidden_paths` typed contract wins; AGENTS.md §0–§5b decision-critical rules win over §6+ reference sections; role mandate wins over task description for SCOPE; task description wins for SUBJECT MATTER.
- Follow the experiment cookbook (docs/guides/experiment_cookbook.md)
- Stay within the role's authorized paths and forbidden paths
- Run validate_agent_task_discipline.py post <task_type> before declaring done
- Record all findings in EXPERIMENT_TRACK_RECORD.md
- Push-notify through the configured provider on completion or if you need a decision
"""
    prompt += "\nCOMMAND SURFACE:\n" + command_surface_hint(task_description) + "\n"
    if prior_checkpoint_hint:
        prompt += prior_checkpoint_hint
    cmd = build_agent_command(
        agent_cli=agent_cli,
        adapter=adapter,
        prompt=prompt,
        project=project,
        claude_session_id=claude_session_id,
        claude_session_is_new=claude_session_is_new,
    )

    log.info(f"Executing via {adapter}: {task_description[:80]}...")
    # Subscription-auth split (per principal directive 2026-05-07):
    # When invoking the agent CLI (claude/codex), strip ANTHROPIC_API_KEY +
    # OPENAI_API_KEY from the subprocess env so the CLI falls through to
    # subscription auth (claude setup-token / codex login). The substrate-
    # layer LLMRuntime calls retain the keys via os.environ in the parent
    # process — this scrub only affects subprocess invocations.
    subprocess_env = {k: v for k, v in os.environ.items()
                      if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_TASK_DURATION,
            cwd=str(REPO_ROOT),
            env=subprocess_env,
        )
        out = {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "returncode": result.returncode,
            "claude_session_id": claude_session_id,
        }
    except subprocess.TimeoutExpired:
        out = {"success": False, "error": "timeout", "stdout": "", "stderr": "", "claude_session_id": claude_session_id}
    except FileNotFoundError:
        out = {"success": False, "error": f"{agent_cli} CLI not found", "stdout": "", "stderr": "", "claude_session_id": claude_session_id}

    # Continuity bookkeeping: update the per-role tick counter so the
    # session can be auto-rotated when stale.
    if use_resume and adapter == "claude_print" and claude_session_id:
        try:
            continuity_note_tick(
                role_id=role_id,
                success=out["success"],
                summary=task_description[:200],
            )
        except Exception as exc:  # noqa: BLE001
            log.debug(f"continuity: note_tick failed (non-fatal): {exc}")

    return out


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


def read_directives(role_id: str, *, consume: bool = True) -> list[str]:
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
                    if consume:
                        data["consumed"] = True
                        data["consumed_utc"] = datetime.now(timezone.utc).isoformat()
                        f.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
    return results


def pre_tick_checks(
    session,
    role_id: str = "manager",
    *,
    tick_scope: str | None = None,
    consume_directives: bool = True,
    poll_inbound: bool = True,
) -> list[str]:
    """Run governance checks before each tick. Returns warnings."""
    warnings = []

    # Check control signals (STOP/PAUSE/RESUME from dashboard)
    control = check_control_signal(role_id)
    if control == "STOP":
        warnings.append("STOP directive received from dashboard")
    elif control == "PAUSE":
        warnings.append("PAUSE directive received from dashboard")

    # Check directives
    directives = read_directives(role_id, consume=consume_directives)
    for d in directives:
        warnings.append(f"Inbound directive: {d[:200]}")

    # Check mandate drift
    try:
        if getattr(session, "directory", None) is not None:
            check_mandate_drift(
                session_dir=session.directory,
                mandate_path=REPO_ROOT / "org" / "mandates" / f"{role_id}_mandate.md",
                role_id=role_id,
            )
    except Exception as e:
        warnings.append(f"Mandate drift check failed: {e}")

    # Check unresolved damage signals
    try:
        signals = recent_damage()
        if signals:
            warnings.append(f"{len(signals)} unresolved damage signal(s)")
    except Exception:
        pass

    # Role tick-surface enforcement: run the registered role precheck, persist
    # its receipt, and fail closed if the brief does not pass. The same receipt
    # is injected into the spawned agent prompt.
    surface_config = ROLE_TICK_SURFACES.get(role_id)
    surface_cmd = _role_tick_surface_command(role_id, tick_scope)
    if surface_config and surface_cmd:
        try:
            proc = subprocess.run(
                surface_cmd,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=600,
            )
            receipt_path = surface_config.get("receipt")
            if not isinstance(receipt_path, Path):
                raise ValueError(f"invalid tick-surface receipt path for role {role_id}")
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt = proc.stdout
            if proc.stderr.strip():
                receipt += "\n\n[stderr]\n" + proc.stderr
            receipt_path.write_text(receipt, encoding="utf-8")
            if proc.returncode != 0:
                warnings.append(f"HARD_STOP: {surface_config.get('failure_message')}")
            else:
                warnings.append(
                    f"{surface_config.get('label') or role_id + ' tick surface'} ok: "
                    f"receipt written to {receipt_path.relative_to(REPO_ROOT)}"
                )
        except Exception as e:
            warnings.append(f"HARD_STOP: {role_id} tick surface error: {e}")

    # ── Orbit chat — process pending principal messages for THIS role ──
    # Cheap-tier subscription LLM, idempotent (no reply if no pending).
    try:
        from ztare.orchestration.chat_handler import generate_and_store_reply
        reply = generate_and_store_reply(role_id)
        if reply:
            warnings.append(
                f"chat: replied to principal in {role_id} chat ({len(reply.get('text', ''))} chars)"
            )
    except Exception as exc:  # noqa: BLE001
        log.debug(f"chat_handler reply failed (non-fatal): {exc}")

    # Check for pending inbound directives
    if poll_inbound:
        messages = poll_telegram()
        recognized_verbs = {"STOP", "PAUSE", "RESUME", "STATUS",
                            "APPROVE", "YES", "RUN",
                            "SKIP", "NO", "DEFER"}
        for msg in messages:
            text = msg.get("text", "") if isinstance(msg, dict) else str(msg)
            stripped = text.strip()
            upper = stripped.upper()
            first_token = (stripped.split() or [""])[0].upper().rstrip(":").rstrip(".")
            if upper == "STOP":
                warnings.append("STOP directive received from principal")
            elif upper == "PAUSE":
                warnings.append("PAUSE directive received from principal")
            elif upper == "STATUS":
                send_notification(f"Daemon running. Last tick: {datetime.now(timezone.utc).isoformat()}")
            elif first_token in recognized_verbs:
                # APPROVE/SKIP/RESUME/etc. — handled elsewhere; no reply needed here
                pass
            elif stripped.startswith("@"):
                # Future: route to specific role (e.g. "@manager run X").
                # Today: log as directive + acknowledge so user knows it was received.
                send_notification(
                    f"Got directive '{stripped[:80]}'. Per-role routing (@<role> ...) "
                    f"is not wired yet — directive logged for next tick context. "
                    f"For role-specific work, use Orbit chat pane (when available)."
                )
                warnings.append(f"Inbound directive: {stripped[:100]}")
            elif stripped:
                # Unrecognized free text — acknowledge so it doesn't feel silent
                send_notification(
                    f"Unknown command. Try: APPROVE / SKIP / STOP / PAUSE / STATUS, "
                    f"or @<role> <directive> for routing. Got: '{stripped[:60]}'"
                )
                warnings.append(f"Inbound directive: {stripped[:100]}")

    return warnings


# ── Main tick ─────────────────────────────────────────────────────────

def _session_id(session) -> str:
    return str(getattr(session, "session_id", "") or "unknown_session")


def _execution_prompt(candidate: Candidate) -> str:
    origin = str(candidate.origin_path.relative_to(REPO_ROOT)) if candidate.origin_path else "n/a"
    frontmatter = candidate.metadata.get("frontmatter")
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    route = infer_execution_route(
        frontmatter=frontmatter,
        body=candidate.raw_text,
        role_id=str(candidate.metadata.get("assigned_to") or "").replace("role.", "", 1) or "manager",
    )
    return (
        f"{candidate.intent}\n\n"
        f"Source: {candidate.source}\n"
        f"Origin: {origin}\n"
        f"Scarcity signal: {candidate.scarcity_signal}\n"
        f"Metadata: {json.dumps(candidate.metadata, sort_keys=True, default=str)}\n\n"
        f"{render_route_contract(route)}\n"
        f"Task body / excerpt:\n{candidate.raw_text[:4000]}"
    )


def _candidate_subject(candidate: Candidate) -> str:
    return str(candidate.metadata.get("goal_id") or candidate.intent[:80])


def _proposal_card(candidate: Candidate, role_id: str, auth_reason: str) -> str:
    origin = str(candidate.origin_path.relative_to(REPO_ROOT)) if candidate.origin_path else "n/a"
    route = candidate.metadata.get("execution_route")
    route_name = route.get("route", "unclassified") if isinstance(route, dict) else "unclassified"
    return (
        f"Role: {role_id}\n"
        f"Decision: execute candidate task\n"
        f"Task: {candidate.intent}\n"
        f"Execution route: {route_name}\n"
        f"Why now: {candidate.scarcity_signal}\n"
        f"Source: {candidate.source}\n"
        f"Origin: {origin}\n"
        f"Authorization: {auth_reason}\n"
        f"Approve: daemon claims task and runs the configured agent runtime.\n"
        f"Skip: no work is executed this tick.\n"
        f"Stop: daemon exits.\n"
        f"Expected artifact: workspace/agent_daemon_log.jsonl plus task/result artifacts."
    )


def _find_existing_pending_gate(role_id: str, candidate: Candidate) -> Optional[str]:
    """Dedup helper: return existing pending gate_id with the same role + subject,
    so rapid daemon restarts don't open duplicate gates for the same candidate.

    Comparison key is (role_id, candidate_subject). If found, the caller should
    reuse that gate_id instead of writing a new one. Notification providers
    should not refire either.
    """
    if not GATES_PENDING_DIR.exists():
        return None
    target_subject = _candidate_subject(candidate)
    for gate_path in GATES_PENDING_DIR.glob("proposal_*.json"):
        try:
            data = json.loads(gate_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if data.get("status") != "pending":
            continue
        if data.get("owner") != role_id:
            continue
        if data.get("subject") == target_subject:
            return data.get("gate_id")
    return None


def _write_proposal_gate(
    *,
    candidate: Candidate,
    role_id: str,
    session,
    auth_reason: str,
) -> tuple[str, bool]:
    """Returns (gate_id, was_freshly_opened).

    Dedup: if an open gate already exists for the same (role, subject), reuses
    it (returns is_fresh=False) to prevent duplicate notification proposals on
    rapid daemon restarts.
    """
    existing = _find_existing_pending_gate(role_id, candidate)
    if existing:
        log.info(f"Reusing existing pending gate: {existing} (dedup)")
        return existing, False
    gate_id = f"proposal_{role_id}_{uuid.uuid4().hex[:12]}"
    gate = {
        "gate_id": gate_id,
        "kind": "daemon_proposal",
        "subject": _candidate_subject(candidate),
        "summary": _proposal_card(candidate, role_id, auth_reason),
        "options": [
            {"id": "approve", "consequence": "Claim the task and execute the configured role agent."},
            {"id": "skip", "consequence": "Do not execute this candidate on this tick."},
            {"id": "stop", "consequence": "Stop this daemon."},
        ],
        "owner": role_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "candidate": {
            "source": candidate.source,
            "intent": candidate.intent,
            "scarcity_signal": candidate.scarcity_signal,
            "metadata": candidate.metadata,
        },
        "session_id": _session_id(session),
    }
    GATES_PENDING_DIR.mkdir(parents=True, exist_ok=True)
    # default=str handles datetime.date / datetime.datetime objects that
    # arrive via YAML frontmatter parsing (when authors don't quote dates).
    # Coerces to ISO string instead of raising TypeError.
    (GATES_PENDING_DIR / f"{gate_id}.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    append_transition(
        event="daemon.proposal_gate.opened",
        actor="agent_daemon",
        role_id=role_id,
        surface="daemon",
        subject=gate_id,
        payload={"candidate": gate["candidate"], "session_id": _session_id(session)},
        causality_id=gate_id,
    )
    return gate_id, True


def _read_resolved_gate(gate_id: str) -> dict | None:
    path = GATES_RESOLVED_DIR / f"{gate_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if str(data.get("gate_id") or "") != gate_id:
            return None
        if str(data.get("status") or "").lower() != "resolved":
            return None
        resolution = data.get("resolution") if isinstance(data.get("resolution"), dict) else {}
        chosen = str(resolution.get("chosen_option") or data.get("verdict") or "").lower()
        if chosen not in {"approve", "skip", "stop"}:
            return None
        return data
    except Exception:
        return None


def _valid_gate_id(gate_id: str) -> bool:
    return bool(gate_id and GATE_ID_RE.fullmatch(gate_id))


def _write_resolved_gate_from_surface(
    gate_id: str,
    *,
    chosen_option: str,
    surface: str,
    role_id: str,
) -> None:
    """Resolve a proposal gate through the canonical gate artifact path.

    Idempotent on double-click — `_mark_gate_resolved_in_memory` returns
    False on the second call for the same gate_id within the process,
    AND the on-disk resolved file existence check guards across processes.
    """
    if not _valid_gate_id(gate_id):
        raise ValueError(f"invalid gate_id: {gate_id!r}")
    chosen_option = chosen_option.lower().strip()
    if chosen_option not in {"approve", "skip", "stop"}:
        raise ValueError(f"invalid gate option: {chosen_option!r}")
    # In-memory dedup — defends against rapid double-clicks within one
    # poll window. Disk dedup (next check) defends across processes/restarts.
    if not _mark_gate_resolved_in_memory(gate_id):
        log.info(f"Gate {gate_id} already resolved this session — ignoring duplicate {chosen_option}")
        return
    GATES_RESOLVED_DIR.mkdir(parents=True, exist_ok=True)
    resolved_path = GATES_RESOLVED_DIR / f"{gate_id}.json"
    if resolved_path.exists():
        return
    pending_path = GATES_PENDING_DIR / f"{gate_id}.json"
    if not pending_path.exists():
        raise FileNotFoundError(f"pending gate does not exist: {gate_id}")
    try:
        loaded = json.loads(pending_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"pending gate is not valid JSON: {gate_id}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"pending gate is not an object: {gate_id}")
    pending_gate: dict = loaded
    if str(pending_gate.get("gate_id") or gate_id) != gate_id:
        raise ValueError(f"pending gate id mismatch: {gate_id}")
    allowed_options = {
        str(option.get("id") or "").lower()
        for option in pending_gate.get("options", [])
        if isinstance(option, dict)
    }
    if allowed_options and chosen_option not in allowed_options:
        raise ValueError(f"gate option {chosen_option!r} not allowed for {gate_id}")
    resolved = {
        **pending_gate,
        "gate_id": gate_id,
        "status": "resolved",
        "resolved_utc": datetime.now(timezone.utc).isoformat(),
        "resolved_by": "principal",
        "surface": surface,
        "resolution": {
            "chosen_option": chosen_option,
            "reason": f"resolved via {surface}",
        },
    }
    tmp_path = resolved_path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(resolved, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    tmp_path.replace(resolved_path)
    handled_path = pending_path.with_suffix(".json.handled")
    pending_path.replace(handled_path)
    append_transition(
        event="gate.resolved",
        actor="principal",
        role_id=role_id,
        surface=surface,
        subject=gate_id,
        payload=resolved,
        causality_id=gate_id,
    )


# Module-level cache: gate_ids resolved within the current process.
# Defends against double-click bursts where two callback_queries with the
# same callback_data arrive in the same poll window. The on-disk
# `_write_resolved_gate_from_surface` already short-circuits on existing
# resolved file, but in-memory dedup avoids the rename-race + duplicate
# transition log entries.
_RECENTLY_RESOLVED_GATE_IDS: set[str] = set()


def _mark_gate_resolved_in_memory(gate_id: str) -> bool:
    """Returns True if gate was unseen + just marked; False if already seen.

    Caller should no-op (skip duplicate dispatch / duplicate transition write)
    when this returns False.
    """
    if gate_id in _RECENTLY_RESOLVED_GATE_IDS:
        return False
    _RECENTLY_RESOLVED_GATE_IDS.add(gate_id)
    # Soft cap: don't grow unbounded across days. Flush at 500.
    if len(_RECENTLY_RESOLVED_GATE_IDS) > 500:
        _RECENTLY_RESOLVED_GATE_IDS.clear()
    return True


def _resolve_gate_from_telegram(gate_id: str, role_id: str) -> None:
    """Convert authorized tenant notification commands into the same resolved gate.

    Callback-data routing fix (2026-05-07): inline-keyboard taps carry
    callback_data="approve:<gate_id_short>" — the suffix matches the LAST 32
    chars of the originating gate_id (per `send_notification` in this file).
    If a callback message specifies a different gate_id, ignore it for the
    currently-waited gate (it'll be picked up when its true target gate is
    waited on, OR processed via a separate resolve-pending-execution scan
    in discover_all). Plain-text APPROVE/SKIP/STOP messages without a
    callback gate_id apply to whatever gate is currently being waited on
    (legacy behavior).
    """
    target_short = gate_id[-32:] if len(gate_id) > 32 else gate_id
    for msg in poll_telegram():
        text = (msg.get("raw_text") or msg.get("text") or "").strip()
        command = (msg.get("command") or "").upper()
        cb_gate_id = msg.get("callback_gate_id")
        # Callback originating from inline button: only honor if it points at
        # this gate (or one that ends with our target_short).
        if cb_gate_id and cb_gate_id != target_short and not gate_id.endswith(cb_gate_id):
            log.info(f"Ignoring callback for gate '{cb_gate_id}' while waiting on '{gate_id}'")
            continue
        token = (text.split() or [""])[0].upper().rstrip(":").rstrip(".")
        chosen = ""
        if command == "STOP" or token == "STOP":
            chosen = "stop"
        elif token in {"APPROVE", "YES", "RUN"}:
            chosen = "approve"
        elif token in {"SKIP", "NO", "DEFER"}:
            chosen = "skip"
        if chosen:
            _write_resolved_gate_from_surface(
                gate_id,
                chosen_option=chosen,
                surface="telegram",
                role_id=role_id,
            )
            return


def _wait_for_gate_resolution(gate_id: str, *, role_id: str) -> str | None:
    deadline = time.time() + PROPOSAL_TIMEOUT
    while time.time() < deadline:
        data = _read_resolved_gate(gate_id)
        if data:
            resolution = data.get("resolution") if isinstance(data.get("resolution"), dict) else {}
            chosen = str(resolution.get("chosen_option") or data.get("verdict") or "").lower()
            return chosen or None
        if telegram_available():
            _resolve_gate_from_telegram(gate_id, role_id)
        time.sleep(5)
    return None


def _claim_candidate_task(
    candidate: Candidate,
    session,
    role_id: str,
    *,
    member_id: str,
) -> str | None:
    if candidate.source != "principal-goal":
        return None
    goal_id = str(candidate.metadata.get("goal_id") or "")
    if not goal_id:
        return None
    from ztare.orchestration.goals_inbox import claim_goal

    claimed = claim_goal(
        goal_id=goal_id,
        session_id=_session_id(session),
        member_id=member_id,
        role_id=role_id,
    )
    if claimed is None:
        raise RuntimeError(f"task {goal_id} could not be claimed; another session may own it")
    return goal_id


# ── Break-only adversary (GP-5.5 spec; the depth-forcing piece the
# brief/membrane lacked). Per the operator's own RCA: an obligation
# is a HARD rule only when the AUTHORITY OWNER refuses to let work
# count until it is satisfied — never when it is prose handed to the
# agent. This runs AFTER execute, BEFORE record. It can ONLY break
# (never approve/bless/certify); ONE valid break flips success→False
# so the existing record path writes `daemon.task.failed` + does not
# close the candidate ⇒ the tick does not count and is re-discovered.
# "No break" is NOT certification. It catches GROSS satisficing
# (named-not-run / laundering / menu-bypass / mechanism-deflection /
# prior-alias relapse / no-discriminating-test); it does NOT certify
# deep correctness — that residual stays with the human + forecast
# market (panel's irreducible ~45%). Acceptance of THIS code is the
# GP-5.5 kill-test suite run by the operator/break agent, NOT a
# self-report.
BREAK_CLASSES = (
    "named_not_run", "generic_pattern_laundering",
    "orchestration_menu_bypass", "anti_pattern_not_operationalized",
    "mechanism_as_deflection", "prior_alias_relapse",
    "no_discriminating_test", "receipt_missing",
)


def _break_only_adversary(*, result: dict, role_tick_surface: str,
                          agent_cli: str, agent_adapter: str
                          ) -> dict | None:
    """Return a break record {break_class,evidence,reason} or None.

    Independent (fresh, read-only, no executor session/mandate). The
    BREAK is HARD; the adversary's OWN infra errors fail-OPEN (logged)
    so a broken adversary cannot brick the loop (resilience-over-
    correctness for the adversary's plumbing only — same rule as the
    judge worker)."""
    out = (result.get("stdout") or "")[:24000]
    if not out.strip():
        return {"break_class": "named_not_run",
                "evidence": "(empty agent output)",
                "reason": "executor produced no output; nothing was run"}
    prompt = (
        "You are a BREAK-ONLY adversary. You CANNOT approve, bless, "
        "certify, or say the work is good. You may ONLY emit a break "
        "from this exact set if the executor NAMED an obligation "
        "without running it, laundered a pattern as prose, bypassed "
        "the orchestration menu, failed to OPERATIONALIZE a declared "
        "anti-pattern, deflected the goal into building mechanism, "
        "relapsed to a prior-alias atom, produced NO discriminating "
        "test, or is missing a required receipt.\n"
        f"ALLOWED break_class values: {list(BREAK_CLASSES)}\n\n"
        "=== OBLIGATIONS THE BRIEF REQUIRED THIS TICK (role pre-tick "
        "surface) ===\n" + (role_tick_surface or "(none surfaced)")
        + "\n\n=== WHAT THE EXECUTOR ACTUALLY PRODUCED (stdout) ===\n"
        + out + "\n\n"
        "Output EXACTLY one line of JSON "
        '{"break_class":"<one of the allowed values>",'
        '"evidence":"<short quote from the executor output>",'
        '"reason":"<why this is that break, concretely>"} '
        "IF AND ONLY IF you find such a break. Otherwise output "
        "EXACTLY: NO_BREAK_FOUND  (this is NOT approval and NOT "
        "certification; it only means no listed break was found).")
    try:
        adapter = infer_agent_adapter(agent_cli, agent_adapter)
        if adapter == "claude_print":
            cmd = [agent_cli, "--print", "--permission-mode", "plan",
                   "-p", prompt]
        elif adapter == "codex_exec":
            cmd = [agent_cli, "exec", "--cd", str(REPO_ROOT),
                   "--sandbox", "read-only", "--ask-for-approval",
                   "never", prompt]
        else:
            log.warning(f"break-only: unknown adapter {adapter} "
                        f"(fail-open, logged)")
            return None
        r = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=300)
        txt = (r.stdout or "") + (r.stderr or "")
    except Exception as exc:  # noqa: BLE001
        log.warning(f"break-only adversary infra error "
                    f"(fail-open, logged): {exc}")
        return None
    if "NO_BREAK_FOUND" in txt:
        return None
    depth = 0
    start = -1
    best = None
    for i, c in enumerate(txt):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                best = txt[start:i + 1]
    if not best:
        return None
    try:
        b = json.loads(best)
    except Exception:
        return None
    if str(b.get("break_class")) in BREAK_CLASSES:
        return {"break_class": str(b["break_class"]),
                "evidence": str(b.get("evidence", ""))[:400],
                "reason": str(b.get("reason", ""))[:400]}
    return None


def _close_candidate_task(
    candidate: Candidate,
    session,
    *,
    role_id: str,
    success: bool,
    result: dict,
) -> None:
    if candidate.source != "principal-goal":
        if candidate.source == "agent-channel":
            message_id = str(candidate.metadata.get("message_id") or "")
            to_role = str(candidate.metadata.get("to_role") or "")
            if message_id and to_role:
                from ztare.orchestration.agent_channels import update_agent_message_status

                update_agent_message_status(
                    role_id=to_role,
                    message_id=message_id,
                    status="closed" if success else "acknowledged",
                    actor=role_id,
                    note="executed by daemon" if success else "daemon execution failed; see workspace/agent_daemon_log.jsonl",
                )
        return
    goal_id = str(candidate.metadata.get("goal_id") or "")
    if not goal_id:
        return
    from ztare.orchestration.goals_inbox import mark_goal_blocked, mark_goal_done

    summary = (
        result.get("stdout")
        or result.get("error")
        or result.get("stderr")
        or "no output captured"
    )
    summary = str(summary).strip()[:1000]
    if success:
        mark_goal_done(
            goal_id=goal_id,
            session_id=_session_id(session),
            result_summary=summary,
            artifacts=["workspace/agent_daemon_log.jsonl"],
        )
    else:
        mark_goal_blocked(
            goal_id=goal_id,
            session_id=_session_id(session),
            blocker=summary,
            escalation_path="workspace/agent_daemon_log.jsonl",
        )


def tick(
    session,
    role_id: str = "manager",
    dry_run: bool = False,
    unattended: bool = False,
    agent_cli: str = "claude",
    agent_adapter: str = "auto",
    member_id: str = "claude",
    tick_scope: str | None = None,
) -> bool:
    """One governance tick: discover → propose → (approve) → execute → record.

    Returns True if the daemon dispatched real work to an agent CLI this
    tick, False otherwise (no_work / refused / dry_run / queued_for_principal /
    gate_not_approved / claim_failed). Used by the main loop to switch
    between ACTIVE and IDLE tick intervals."""

    log.info(f"─── tick start ({role_id}) ───")

    # 1. Pre-tick governance checks
    warnings = pre_tick_checks(
        session,
        role_id=role_id,
        tick_scope=tick_scope,
        consume_directives=not dry_run,
        poll_inbound=not dry_run,
    )
    for w in warnings:
        log.warning(w)
        if "STOP" in w:
            log.info("STOP received. Exiting.")
            send_notification("Daemon stopped by principal STOP directive.")
            sys.exit(0)
        if "PAUSE" in w:
            log.info("PAUSE received. Sleeping 30 min.")
            send_notification("Daemon paused for 30 min. Send RESUME to wake.")
            time.sleep(1800)
            return
        if w.startswith("HARD_STOP:"):
            log.warning("Pre-tick hard stop. Refusing dispatch this tick.")
            if notification_provider_available():
                send_notification(w, priority="high")
            return False

    # 1.5 RD-1.12 live co-drive (2026-05-02): for role=research_director,
    # run the deterministic frontier-detection pass BEFORE work-discovery.
    # This populates per-project frontier_state.pending_actions queues
    # which the agent session below will drain. Cheap; idempotent; cursors
    # advance via frontier_state.last_iter_observed so events are not
    # re-emitted on the next tick. The agent retains full agency within
    # the tick — it can drain the queue, add new actions, dissent in prose,
    # or do nothing — but the daemon ensures detection runs every tick
    # even if the agent is busy on a different project.
    if role_id == "research_director":
        try:
            from ztare.role_extensions.frontier_runner import scan_all_active_projects
            from ztare.role_extensions.iter_action_policy import dispatch_event
            scope = _scope_norm(tick_scope)
            project_slugs = None
            if scope and scope not in {"all", "global"}:
                project_slugs = [tick_scope]
            events_by_project = scan_all_active_projects(project_slugs=project_slugs)
            n_events = sum(len(v) for v in events_by_project.values())
            n_queued = 0
            for slug, events in events_by_project.items():
                for ev in events:
                    queued = dispatch_event(ev)
                    n_queued += len(queued)
            if n_events:
                log.info(f"RD-1.12 frontier scan: {n_events} events across "
                         f"{len(events_by_project)} projects → {n_queued} actions queued")
                append_transition(
                    event="rd.frontier.scan",
                    actor="agent_daemon",
                    role_id=role_id,
                    surface="daemon",
                    subject="frontier_runner",
                    payload={
                        "projects": list(events_by_project.keys()),
                        "n_events": n_events,
                        "n_actions_queued": n_queued,
                    },
                )
        except Exception as exc:  # noqa: BLE001
            log.warning(f"RD-1.12 frontier scan failed (non-fatal): {exc}")

    # 2. Discover work
    candidates = discover_work(role_id=role_id, tick_scope=tick_scope)
    if not candidates:
        log.info("No work discovered. Idle tick.")
        try:
            write_task_checkpoint(
                session_id=_session_id(session),
                claimed_id=None,
                task_intent=None,
                status="no_work",
                last_summary="no candidates discovered this tick",
            )
        except Exception as exc:  # noqa: BLE001
            log.debug(f"checkpoint: write failed (non-fatal): {exc}")
        return False

    # 3. Rank and propose top candidate
    top = candidates[0]
    proposal = f"Proposed task: {top.intent}\nSource: {top.source}\nSignal: {top.scarcity_signal}"
    log.info(f"Top candidate: {top.intent[:80]}")
    append_transition(
        event="daemon.work.discovered",
        actor="agent_daemon",
        role_id=role_id,
        surface="daemon",
        subject=_candidate_subject(top),
        payload={"source": top.source, "intent": top.intent, "metadata": top.metadata},
    )
    auth = authorize_dispatch(
        role_id=role_id,
        candidate_source=top.source,
        candidate_text=_execution_prompt(top),
        metadata=top.metadata,
        unattended=unattended,
    )
    approval_required = (
        not auth.allowed
        and auth.required_approval == "principal"
        and not auth.terminal
    )
    if not auth.allowed and not approval_required:
        log.warning(f"Refusing candidate before approval: {auth.reason}")
        emit_damage(
            source="agent_daemon.authorization",
            kind="autonomous_scope_refused",
            detail=f"{top.intent}: {auth.reason}",
            severity="warn",
        )
        append_transition(
            event="daemon.dispatch.refused",
            actor="agent_daemon",
            role_id=role_id,
            surface="daemon",
            subject=_candidate_subject(top),
            payload={"reason": auth.reason, "required_approval": auth.required_approval},
        )
        return False

    if dry_run:
        log.info(f"DRY RUN — would propose: {proposal}\nAuthorization: {auth.reason}")
        return False

    # 4. Approval path: unattended in-mandate pass OR proposal gate resolution.
    if unattended and not approval_required:
        log.info("Unattended mode enabled. Executing without approval wait.")
        append_transition(
            event="daemon.dispatch.auto_approved",
            actor="agent_daemon",
            role_id=role_id,
            surface="daemon",
            subject=_candidate_subject(top),
            payload={"reason": auth.reason},
        )
    else:
        gate_id, was_fresh = _write_proposal_gate(
            candidate=top,
            role_id=role_id,
            session=session,
            auth_reason=auth.reason,
        )
        if not was_fresh:
            log.info(f"Proposal gate (reused): {gate_id} — notification NOT re-fired")
            # Don't re-fire push for a reused gate; principal already saw it.
        else:
            log.info(f"Proposal gate opened: {gate_id}")
            if notification_provider_available():
                # Plain-language summary of what each button does, so the
                # principal can decide without consulting the source code.
                friendly = (
                    f"Decision needed for: {top.intent[:140]}\n\n"
                    f"What each option does:\n"
                    f"  ✅ APPROVE — daemon claims the task and dispatches "
                    f"the {role_id} agent to execute it. Costs whatever the "
                    f"task costs (substrate runs use API; agent-only work "
                    f"uses Max subscription).\n"
                    f"  ⏭ SKIP — daemon does NOT execute this candidate this "
                    f"tick. The task stays in the inbox; daemon may surface "
                    f"it again next tick or pick something else.\n"
                    f"  🛑 STOP — daemon exits cleanly. Resume later via "
                    f"`sudo systemctl start agent-daemon`. No marginal cost "
                    f"while stopped.\n\n"
                    f"Gate id: {gate_id}\n"
                    f"Tap a button below, or type APPROVE / SKIP / STOP."
                )
                send_notification(friendly, priority="high", gate_id=gate_id)
            else:
                log.warning("No notification provider configured. Waiting for Orbit/filesystem gate resolution.")
        if unattended and approval_required:
            log.info("Approval-required candidate queued as gate; unattended daemon will not wait or execute.")
            append_transition(
                event="daemon.proposal_gate.queued_for_principal",
                actor="agent_daemon",
                role_id=role_id,
                surface="daemon",
                subject=gate_id,
                payload={"reason": auth.reason},
                causality_id=gate_id,
            )
            return False
        chosen = _wait_for_gate_resolution(gate_id, role_id=role_id)
        if chosen != "approve":
            log.info(f"Proposal gate did not approve execution: {chosen or 'timeout'}")
            append_transition(
                event="daemon.proposal_gate.closed_without_execution",
                actor="agent_daemon",
                role_id=role_id,
                surface="daemon",
                subject=gate_id,
                payload={"chosen_option": chosen or "timeout"},
                causality_id=gate_id,
            )
            if chosen == "stop":
                send_notification("Daemon stopped by resolved gate.")
                sys.exit(0)
            return False
        append_transition(
            event="daemon.proposal_gate.approved",
            actor="agent_daemon",
            role_id=role_id,
            surface="daemon",
            subject=gate_id,
            payload={"candidate": top.metadata},
            causality_id=gate_id,
        )

    # 5. Execute
    start_ts = time.time()
    mandate_path = REPO_ROOT / "org" / "mandates" / f"{role_id}_mandate.md"
    if role_id == "manager":
        mandate_path = MANDATE_PATH
    try:
        claimed_id = _claim_candidate_task(top, session, role_id, member_id=member_id)
        if claimed_id:
            append_transition(
                event="daemon.task.claimed",
                actor="agent_daemon",
                role_id=role_id,
                surface="daemon",
                subject=_candidate_subject(top),
                payload={
                    "candidate": top.metadata,
                    "session_id": _session_id(session),
                    "claimed_id": claimed_id,
                },
            )
        else:
            append_transition(
                event="daemon.execution.approved_without_task_claim",
                actor="agent_daemon",
                role_id=role_id,
                surface="daemon",
                subject=_candidate_subject(top),
                payload={
                    "candidate": top.metadata,
                    "session_id": _session_id(session),
                    "reason": "source has no task-claim primitive",
                },
            )
    except Exception as e:  # noqa: BLE001
        log.warning(f"Task claim failed: {e}")
        append_transition(
            event="daemon.task.claim_failed",
            actor="agent_daemon",
            role_id=role_id,
            surface="daemon",
            subject=_candidate_subject(top),
            payload={"error": str(e)},
        )
        return False
    result = execute_task(
        _execution_prompt(top),
        role_id=role_id,
        mandate_path=mandate_path,
        agent_cli=agent_cli,
        agent_adapter=agent_adapter,
        org_session_id=_session_id(session),
    )
    duration_s = time.time() - start_ts

    # RD-1.12 (2026-05-02): post-tick verification. The daemon spawned the
    # agent with a queued action / proactive probe; verify the agent
    # actually engaged. Detection: did transitions.jsonl get a new row
    # since start_ts AND/OR did the project's frontier_state advance?
    # If neither, the agent returned without doing anything → emit damage
    # signal `rd_agent_no_engagement` so the principal sees the silent
    # failure on the closure_daemon's next tick.
    if role_id == "research_director" and result.get("success"):
        try:
            engaged = _verify_post_tick_engagement(
                start_ts=start_ts,
                project_slug=(top.metadata or {}).get("project_slug"),
            )
            if not engaged:
                log.warning("RD-1.12 post-tick: agent returned success but produced no audit/state advance")
                emit_damage(
                    source="agent_daemon.post_tick",
                    kind="rd_agent_no_engagement",
                    detail=(
                        f"agent session for `{top.intent[:80]}` returned "
                        f"success but no transitions.jsonl row was added "
                        f"and no frontier_state advanced. Likely the agent "
                        f"hit a debrief halt or skipped the queued actions."
                    ),
                    severity="warn",
                )
        except Exception as exc:  # noqa: BLE001
            log.debug(f"post-tick verification failed (non-fatal): {exc}")

    # HARD break-only gate (operator RCA: enforced by the authority
    # owner, not prose to the agent). Runs AFTER execute, BEFORE
    # record/close. A valid break flips success→False so the existing
    # path records `daemon.task.failed` and does NOT close the
    # candidate ⇒ the tick does not count and is re-discovered. Only
    # break, never bless. Gross-satisficing catcher, not a depth oracle.
    if result.get("success"):
        try:
            _brk = _break_only_adversary(
                result=result,
                role_tick_surface=_format_role_tick_surface_for_prompt(
                    role_id=role_id),
                agent_cli=agent_cli,
                agent_adapter=agent_adapter,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(f"break-only gate infra error "
                        f"(fail-open, logged): {exc}")
            _brk = None
        if _brk:
            log.warning(
                f"BREAK-ONLY BLOCK [{_brk['break_class']}]: "
                f"{_brk['reason']} | ev: {_brk['evidence'][:160]}")
            result["success"] = False
            result["break"] = _brk
            try:
                emit_damage(
                    source="agent_daemon.break_only",
                    kind="rd_break_only_block",
                    detail=(f"{_brk['break_class']}: {_brk['reason']} "
                            f"| evidence: {_brk['evidence'][:200]}"),
                    severity="warn",
                )
            except Exception:  # noqa: BLE001
                pass

    _close_candidate_task(
        top,
        session,
        role_id=role_id,
        success=result["success"],
        result=result,
    )

    # If this candidate came from a resolved-pending-execution gate, mark
    # the gate as dispatched so we don't re-discover + re-execute it.
    if top.source == "resolved-pending-execution":
        gate_path_str = top.metadata.get("resolved_gate_path") if top.metadata else None
        if gate_path_str:
            try:
                Path(f"{gate_path_str}.dispatched").write_text(
                    f"dispatched_utc={datetime.now(timezone.utc).isoformat()}\n"
                    f"success={result['success']}\n",
                    encoding="utf-8",
                )
            except Exception as exc:  # noqa: BLE001
                log.debug(f"failed to mark gate dispatched: {exc}")

    # 6. Record
    log.info(f"Task complete. Success: {result['success']}")
    append_transition(
        event="daemon.task.completed" if result["success"] else "daemon.task.failed",
        actor="agent_daemon",
        role_id=role_id,
        surface="daemon",
        subject=_candidate_subject(top),
        payload={
            "success": result["success"],
            "duration_s": round(duration_s, 3),
            "returncode": result.get("returncode"),
            "session_id": _session_id(session),
        },
    )
    if notification_provider_available():
        status = "✅" if result["success"] else "❌"
        send_notification(
            f"{status} Task finished: {top.intent[:80]}\n"
            "Details: workspace/agent_daemon_log.jsonl and the task artifacts."
        )

    # 7. Write to session log
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": top.intent,
        "source": top.source,
        "success": result["success"],
        "duration_s": round(duration_s, 3),
        "session_id": _session_id(session),
        "returncode": result.get("returncode"),
        "metadata": top.metadata,
    }
    log_path = REPO_ROOT / "workspace" / "agent_daemon_log.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Per-task checkpoint: record what just executed so the next tick (or
    # a recovering process after a crash) can resume from a known state.
    try:
        write_task_checkpoint(
            session_id=_session_id(session),
            claimed_id=str(top.metadata) if top.metadata else None,
            task_intent=top.intent,
            status="executed_success" if result["success"] else "executed_failed",
            last_summary=(result.get("stdout") or result.get("error") or "")[:400],
            extra={
                "duration_s": round(duration_s, 3),
                "returncode": result.get("returncode"),
                "claude_session_id": result.get("claude_session_id"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.debug(f"checkpoint: write failed (non-fatal): {exc}")

    log.info("─── tick end ───")
    return True


# ── Entry point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Persistent Autonomous Agent Daemon")
    parser.add_argument("--role", type=str, default="manager",
                        choices=["manager", "research_director", "self_recursive_orchestrator"],
                        help="Which role this daemon instance fills (default: manager)")
    parser.add_argument("--tick-once", action="store_true", help="Run one tick and exit")
    parser.add_argument("--dry-run", action="store_true", help="Discover and propose, don't execute")
    parser.add_argument("--unattended", action="store_true",
                        help="Execute in-scope discovered work without gate-rail approval")
    # Honor principal.yaml's preferred_agent_cli when no explicit env/CLI override.
    # principal.yaml > ZTARE_AGENT_CLI env > 'claude' fallback.
    def _principal_pref_agent_cli() -> str:
        try:
            import yaml
            for d in [REPO_ROOT, *REPO_ROOT.parents]:
                p = d / "org" / "preferences" / "principal.yaml"
                if p.is_file():
                    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                    pref = (data.get("preferences") or {}).get("preferred_agent_cli")
                    if pref in ("claude", "codex"):
                        return pref
                    break  # found the file but no preference; fall through
        except Exception:
            pass
        return "claude"

    parser.add_argument(
        "--member-id",
        default=os.environ.get("ZTARE_MEMBER_ID", "claude"),
        help="Persistent member/runtime identity recorded in sessions (default: ZTARE_MEMBER_ID or claude)",
    )
    parser.add_argument(
        "--agent-cli",
        default=os.environ.get("ZTARE_AGENT_CLI", _principal_pref_agent_cli()),
        help="Agent runtime command (default: ZTARE_AGENT_CLI > org/preferences/principal.yaml::preferences.preferred_agent_cli > claude)",
    )
    parser.add_argument(
        "--agent-adapter",
        default=os.environ.get("ZTARE_AGENT_ADAPTER", "auto"),
        choices=["auto", *AGENT_ADAPTERS],
        help="Runtime adapter: auto, claude_print, or codex_exec",
    )
    parser.add_argument(
        "--tick-scope",
        default=os.environ.get("ZTARE_TICK_SCOPE", "global"),
        help=(
            "Substrate/project identifier used to decide which Tier-1 "
            "prediction-closure debt is blocking for this daemon tick. "
            "Rows outside the scope are warning-only. Use global for the "
            "legacy whole-RD gate."
        ),
    )
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="Fixed seconds between ticks. Default 600. If --variable-interval is set, this is ignored.")
    parser.add_argument("--variable-interval", action="store_true",
                        help=f"Use variable cadence: {ACTIVE_TICK_INTERVAL}s after a tick that dispatched work, "
                             f"{IDLE_TICK_INTERVAL}s after an idle tick. Stays inside Claude's 5-min cache TTL "
                             f"when active; saves cost when idle.")
    parser.add_argument("--active-interval", type=int, default=ACTIVE_TICK_INTERVAL,
                        help=f"Seconds between ticks when prior tick dispatched work (default: {ACTIVE_TICK_INTERVAL})")
    parser.add_argument("--idle-interval", type=int, default=IDLE_TICK_INTERVAL,
                        help=f"Seconds between ticks when prior tick was idle (default: {IDLE_TICK_INTERVAL})")
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
    log.info(f"  Notification provider: {'available' if notification_provider_available() else 'not configured'}")
    log.info(f"  Mandate: {mandate_path}")
    log.info(f"  Dry run: {args.dry_run}")
    log.info(f"  Unattended: {args.unattended}")
    log.info(f"  Member id: {args.member_id}")
    log.info(f"  Agent CLI: {args.agent_cli}")
    log.info(f"  Agent adapter: {infer_agent_adapter(args.agent_cli, args.agent_adapter)}")
    log.info(f"  Tick scope: {args.tick_scope}")
    log.info("")

    # Open session
    session = ensure_session(
        role_id=role_id,
        member_id=args.member_id,
        substrate="daemon",
        mandate_path=mandate_path,
    )
    log.info(f"Session: {session.session_id if hasattr(session, 'session_id') else 'opened'}")

    if args.tick_once:
        tick(
            session,
            role_id=role_id,
            dry_run=args.dry_run,
            unattended=args.unattended,
            agent_cli=args.agent_cli,
            agent_adapter=args.agent_adapter,
            member_id=args.member_id,
            tick_scope=args.tick_scope,
        )
        return

    # Main loop
    if args.variable_interval:
        log.info(
            f"Entering main loop (variable cadence: {args.active_interval}s active / "
            f"{args.idle_interval}s idle). Send STOP via the configured notification provider or dashboard to halt."
        )
        if notification_provider_available():
            send_notification(
                f"🟢 Agent daemon started. Variable cadence: {args.active_interval}s active / "
                f"{args.idle_interval}s idle. Send STOP to halt."
            )
    else:
        log.info(f"Entering main loop (tick every {args.interval}s). Send STOP via the configured notification provider or dashboard to halt.")
        if notification_provider_available():
            send_notification(f"🟢 Agent daemon started. Tick interval: {args.interval}s. Send STOP to halt.")

    while True:
        did_work = False
        try:
            did_work = bool(tick(
                session,
                role_id=role_id,
                dry_run=args.dry_run,
                unattended=args.unattended,
                agent_cli=args.agent_cli,
                agent_adapter=args.agent_adapter,
                member_id=args.member_id,
                tick_scope=args.tick_scope,
            ))
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt. Shutting down.")
            if notification_provider_available():
                send_notification("🔴 Agent daemon stopped (keyboard interrupt).")
            break
        except Exception as e:
            log.error(f"Tick failed: {e}")
            emit_damage(
                source="agent_daemon",
                kind="daemon_tick_failure",
                severity="high",
                detail=str(e)[:500],
            )
            if notification_provider_available():
                send_notification(f"⚠️ Daemon tick failed: {e}", priority="high")

        if args.variable_interval:
            sleep_s = args.active_interval if did_work else args.idle_interval
            mode = "ACTIVE" if did_work else "IDLE"
            log.info(f"Sleeping {sleep_s}s until next tick ({mode})...")
        else:
            sleep_s = args.interval
            log.info(f"Sleeping {sleep_s}s until next tick...")
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
