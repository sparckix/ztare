"""Canonical escalation channel for the persistent-manager-agent (GP-128).

This module is the ONE place a manager-agent (Claude, a headless daemon,
or any other persistent supervisor) writes a gate escalation that the
principal should review. Escalations produced here:

1. Land in `ztare_workspace/gates/pending/*.json` with the exact schema
   `inbox_state.py` reads (so they SHOW UP in the Streamlit inbox —
   something the existing `orchestration/gate_escalation.py` does not do
   correctly because it writes a different field set).

2. Also fire an ntfy push notification (via src.ztare.notifications.push),
   so the principal is alerted on their phone for time-sensitive
   decisions without having to open the inbox.

Why a new module rather than extending the existing two writers?

- `supervisor_findings_runner.emit_gate_escalation()` is specialized for
  findings-runner debate escalations. Its required inputs
  (`seam_path`, `RunnerStopReason`, `RunnerCycleResult[]`) are meaningful
  only in that runner's context. A manager-agent escalating "Patent #4
  ready to file" has no seam path, no runner, no cycles.

- `orchestration/gate_escalation.write_gate_escalation()` produces a
  different schema that the Streamlit inbox does NOT render — a
  pre-existing mismatch. Fixing that would touch GP-070 directly; this
  module sidesteps it by providing a principal-facing escalation surface
  that is guaranteed to reach the inbox.

This module does NOT replace the two existing writers for their
own use cases. It is the principal-facing layer ABOVE them.

Usage:

    from src.ztare.supervisor.escalation_manager import escalate

    escalate(
        title="Patent #4 filing gate",
        reason="TDO-LR provisional draft revised after empirical "
               "survival; principal signature needed to file.",
        urgent=True,  # → also fires ntfy push
        notes=[
            "Empirical: Pythia-160M from-scratch, +19.9% best ppl vs baseline",
            "Draft: .ip_protected/provisional_4_telemetry_driven_optimizer.md",
            "Cost: $320 micro-entity rate",
        ],
        cost_usd=320.0,
        source_artifact=".ip_protected/provisional_4_telemetry_driven_optimizer.md",
    )

The returned dict tells the caller where the gate lives on disk and
whether the ntfy push succeeded.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


# Canonical inbox directory — matches inbox_state.py:GATE_PENDING_DIR
# resolution pattern so the written JSON is picked up by the Streamlit UI.
_DEFAULT_GATE_DIR = Path("ztare_workspace/gates/pending")

# Pattern shared with inbox_state.reconcile_pending_resolved — kebab-ish,
# predictable, and sortable by timestamp prefix so the inbox list orders
# naturally by age.
_SLUG_SAFE = re.compile(r"[^a-z0-9_.-]+")


def _slugify(text: str, max_len: int = 40) -> str:
    """Lowercase, hyphenate, restrict to safe filename chars."""
    slug = _SLUG_SAFE.sub("-", text.lower()).strip("-")
    if not slug:
        slug = "untitled"
    return slug[:max_len]


log = logging.getLogger(__name__)


def escalate(
    *,
    title: str,
    reason: str,
    urgent: bool = False,
    notes: Optional[Iterable[str]] = None,
    cost_usd: float = 0.0,
    cycle_count: int = 1,
    source_artifact: Optional[str] = None,
    equivalent_gate_reason: Optional[str] = None,
    advisory: bool = False,
    gate_dir: Optional[Path] = None,
    inbox_url: str = "http://localhost:8501",
    from_role: Optional[str] = None,
    to_role: Optional[str] = None,
    session_id: Optional[str] = None,
    member_id: Optional[str] = None,
) -> dict:
    """Write a principal-facing escalation to the inbox + optionally push.

    Parameters
    ----------
    title : str
        Short human-readable title ("Patent #4 filing gate"). This
        becomes the escalation filename stem AND the ntfy push title.

    reason : str
        Natural-language description of WHAT decision is being escalated
        and WHY the manager-agent could not resolve it autonomously.

    urgent : bool
        If True, fires an ntfy push notification in addition to the
        inbox file.  Default False — inbox-only (non-time-sensitive).

    notes : iterable[str], optional
        Additional context lines.  Rendered in the inbox detail view.

    cost_usd : float
        Accumulated cost of the work that led to this gate.  Surfaced
        to the principal to support "is this worth the next step" checks.

    cycle_count : int
        Number of manager-agent cycles (or analogous iterations)
        consumed.  Default 1.  The findings-runner uses this to signal
        "I've gone N rounds and can't resolve."

    source_artifact : str, optional
        Primary artifact path for the decision (e.g. a patent draft, a
        paper section, a seam file).  Populates `seam_path` field in
        the inbox JSON so the principal can jump straight to it.

    equivalent_gate_reason : str, optional
        A machine-readable gate reason (matches
        `supervisor_state.HumanGateReason` vocabulary where applicable).
        If omitted, defaults to "MANAGER_ESCALATION".

    advisory : bool
        If True, surfaces in the inbox as advisory-only (no hard stop).

    gate_dir : Path, optional
        Override for the inbox directory (testing / multi-tenant).

    inbox_url : str
        URL to include in push notification so the principal can tap
        through from phone to the inbox.  Default assumes local
        Streamlit at 8501; override when the inbox is hosted.

    Returns
    -------
    dict with keys:
        path : str — file path of the written gate JSON
        slug : str — file stem
        pushed : bool — whether the ntfy push succeeded (None if urgent=False)
    """
    # GP-128 debate item 4: session-id-forgery emitter.
    # Before writing a gate, verify any claimed session_id corresponds to
    # a live session. Lazy import to avoid circular dep.
    if session_id is not None:
        from src.ztare.signals import autoemit
        autoemit.check_session_id_authenticity(
            session_id=session_id,
            context=f"escalate call, title={title!r}, urgent={urgent}",
        )

    gate_directory = gate_dir or _DEFAULT_GATE_DIR
    gate_directory.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    ts_iso = now.isoformat()
    ts_epoch_ms = int(now.timestamp() * 1000)
    title_slug = _slugify(title)
    stem = f"mgr_{ts_epoch_ms}_{title_slug}"
    path = gate_directory / f"{stem}.json"

    notes_list = list(notes or [])

    # Inbox schema — matches inbox_state.GatePayload exactly so the
    # Streamlit UI renders it without special handling.
    payload = {
        "seam_path": source_artifact or f"manager-escalation:{title_slug}",
        "escalation_reason": reason,
        "equivalent_gate_reason": equivalent_gate_reason or "MANAGER_ESCALATION",
        "cycle_count": int(cycle_count),
        "total_cost_usd": float(cost_usd),
        "notes": notes_list,
        "timestamp_utc": ts_iso,
        "advisory": bool(advisory),
        # Extensions beyond the strict inbox_state schema — harmless,
        # inbox_state reads what it cares about and ignores the rest.
        # Role / member / session identity so the principal can
        # attribute the escalation across concurrent sessions.
        "title": title,
        "urgent": bool(urgent),
        "source": "escalation_manager.escalate",
        "from_role": from_role,
        "to_role": to_role,
        "from_member": member_id,
        "session_id": session_id,
    }

    # Atomic write: write to tmp, rename.  Prevents the Streamlit UI
    # from reading a half-written file on its periodic refresh.
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)

    log.info("manager escalation written: %s (urgent=%s)", path, urgent)

    # Optional ntfy push
    pushed: Optional[bool] = None
    if urgent:
        try:
            # Lazy import so the supervisor module doesn't take a hard
            # dependency on the notifications module (which itself is
            # optional — ntfy may be unreachable in some environments).
            from src.ztare.notifications.push import push_notification

            body_parts = [reason]
            if notes_list:
                body_parts.append("---")
                body_parts.extend(notes_list[:4])  # truncate on mobile
            if cost_usd > 0:
                body_parts.append(f"Cost so far: ${cost_usd:.2f}")
            body_parts.append(f"Inbox: {inbox_url}")

            pushed = push_notification(
                title=title,
                message="\n".join(body_parts),
                priority="high" if urgent else "default",
                tags=["escalation", "manager"],
                click_url=inbox_url,
            )
        except Exception as exc:  # noqa: BLE001
            # Push is best-effort; never fail the escalation if push
            # plumbing is broken.  The inbox file is authoritative.
            log.warning("ntfy push failed (inbox entry is authoritative): %s",
                        exc)
            pushed = False

    return {
        "path": str(path),
        "slug": stem,
        "pushed": pushed,
    }


def escalate_gate_file_also_push(
    gate_json_path: Path,
    urgent: bool = True,
    inbox_url: str = "http://localhost:8501",
) -> bool:
    """Retrofit escalation for gate files already written by another
    component (e.g. supervisor_findings_runner.emit_gate_escalation or
    orchestration.gate_escalation.write_gate_escalation): read the file,
    fire an ntfy push so the principal is alerted.

    Useful to wrap existing gate writes without editing their source.
    """
    if not gate_json_path.exists():
        log.warning("gate file does not exist, cannot push: %s", gate_json_path)
        return False
    try:
        from src.ztare.notifications.push import push_from_gate_json
    except ImportError:
        log.warning("notifications module not importable")
        return False
    return push_from_gate_json(gate_json_path, inbox_url=inbox_url)
