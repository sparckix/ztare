"""Agent-CLI rotation resolver (gp168 v3 run-2 finding F3, 2026-05-02).

Resolves a role's `agent_rotation` policy to the primary member for a
given UTC date. Rotating the role's primary member across Claude /
Codex / Gemini-CLI on a fixed cadence forces role behavior to be
CLI-invariant; any CLI-specific gaming patterns surface as cross-CLI
inconsistency in role outputs.

Read by:
  - `scripts/public/control/agent_daemon.py` at tick time, to override the role's
    primary member assignment if `agent_rotation.enabled == true`.
  - The Orbit dashboard (via git-sync `/api/role/<id>/active_member`)
    to display the currently-rotated primary.

Schema (org/roles/<role>.yaml `agent_rotation` block):

  agent_rotation:
    enabled: true
    rotation_period_days: 7
    members: [member.claude, member.codex, member.gemini]
    strategy: round_robin           # round_robin | random | stratified
    fallback_member: member.claude

The schema is defined in schemas/role.v1.schema.json (v1.3, 2026-05-02).
This module ships the runtime resolver + a CLI-availability probe.

Reference seam: research_areas/private/seams/mission/GP-168_org_design_unfalsifiability_seam.md
v3 RUN-2 RESULTS §F3.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

ORG_ROLES_DIR = Path("org/roles")
EPOCH = date(2026, 1, 1)  # rotation epoch — period_days counts from here


def resolve_rotated_member(role_id: str,
                           today: Optional[date] = None,
                           role_yaml_dir: Optional[Path] = None
                           ) -> Optional[str]:
    """Return the rotated primary member for `role_id` on `today`.

    Returns:
        The member identifier (e.g., "member.claude") if rotation is
        enabled and a member can be selected. Returns None when:
          - rotation is disabled (caller should use legacy primary)
          - the role yaml lacks an agent_rotation block
          - the rotation members list is empty or unreadable

    Caller policy: if this returns None, the daemon falls back to the
    role's static primary assignment in `org/assignments.yaml`.
    """
    today = today or datetime.now(timezone.utc).date()
    yaml_dir = role_yaml_dir or ORG_ROLES_DIR
    role_path = yaml_dir / f"{role_id}.yaml"
    if not role_path.exists():
        return None
    try:
        data = yaml.safe_load(role_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("agent_rotation: cannot parse %s: %s", role_path, exc)
        return None

    rotation = data.get("agent_rotation")
    if not isinstance(rotation, dict):
        return None
    if not bool(rotation.get("enabled", False)):
        return None

    members = rotation.get("members") or []
    if not members:
        return None

    period_days = int(rotation.get("rotation_period_days", 7))
    if period_days < 1:
        period_days = 1

    strategy = str(rotation.get("strategy", "round_robin")).strip().lower()
    fallback = rotation.get("fallback_member")

    epoch_offset_days = (today - EPOCH).days
    period_index = epoch_offset_days // period_days

    if strategy == "round_robin":
        idx = period_index % len(members)
        return members[idx]
    elif strategy == "random":
        # Deterministic-by-date pseudorandom: SHA1(role_id || period_index)
        seed = f"{role_id}|{period_index}".encode()
        digest = hashlib.sha1(seed).hexdigest()
        idx = int(digest[:4], 16) % len(members)
        return members[idx]
    elif strategy == "stratified":
        # Weighted by inverse of past gaming-incident count per CLI.
        # Currently we don't track per-CLI incidents, so fall through
        # to round_robin until a stratification source is shipped.
        log.debug("agent_rotation: stratified strategy not yet wired; "
                  "falling back to round_robin")
        idx = period_index % len(members)
        return members[idx]
    else:
        log.warning("agent_rotation: unknown strategy %r for role %s; "
                    "using fallback %s", strategy, role_id, fallback)
        return fallback


def is_member_cli_available(member_id: str) -> bool:
    """Best-effort check whether the CLI bound to `member_id` is
    actually invokable on this host. Reads `org/members/<id>.yaml` to
    find the agent_cli, then probes shutil.which() for that binary.
    Returns True on success, False otherwise. Used by the daemon to
    skip rotated members whose CLI is unavailable on this host."""
    import shutil
    members_dir = Path("org/members")
    name = member_id.removeprefix("member.")
    member_path = members_dir / f"{name}.yaml"
    if not member_path.exists():
        return False
    try:
        data = yaml.safe_load(member_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return False
    cli = data.get("agent_cli") or data.get("agent") or ""
    if not cli:
        # No CLI binding — treat as available (e.g., human members).
        return True
    return shutil.which(str(cli)) is not None


def resolve_with_fallback(role_id: str,
                          today: Optional[date] = None,
                          role_yaml_dir: Optional[Path] = None
                          ) -> Optional[str]:
    """Same as resolve_rotated_member but skips members whose CLI is
    unavailable, falling back through the rotation list and ultimately
    to `fallback_member`. Returns None only when no member is
    available at all (caller should escalate)."""
    today = today or datetime.now(timezone.utc).date()
    yaml_dir = role_yaml_dir or ORG_ROLES_DIR
    role_path = yaml_dir / f"{role_id}.yaml"
    if not role_path.exists():
        return None
    try:
        data = yaml.safe_load(role_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    rotation = data.get("agent_rotation") or {}
    if not bool(rotation.get("enabled", False)):
        return None
    members = rotation.get("members") or []
    fallback = rotation.get("fallback_member")

    primary = resolve_rotated_member(role_id, today=today,
                                     role_yaml_dir=yaml_dir)
    if primary and is_member_cli_available(primary):
        return primary

    # Walk the rotation list looking for an available CLI
    for m in members:
        if m == primary:
            continue
        if is_member_cli_available(m):
            log.info("agent_rotation: primary %s unavailable; using %s",
                     primary, m)
            return m

    # All rotation members unavailable — try fallback
    if fallback and is_member_cli_available(fallback):
        log.warning("agent_rotation: all rotation members unavailable; "
                    "using fallback_member %s", fallback)
        return fallback

    log.error("agent_rotation: no available member for role %s "
              "(rotation=%s, fallback=%s)", role_id, members, fallback)
    return None
