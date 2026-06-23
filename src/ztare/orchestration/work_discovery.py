"""GP-131 Work-Discovery Loop — two-source prototype.

The Level 2 daemon (GP-128 § Future Work) needs to identify work
worth doing without being told. This module implements the two
cheapest + highest-signal-density discovery sources from GP-131:

1. TODO-scan   — open TODO boxes in seam files (self-authored, pre-filtered)
2. Damage-scan — unresolved signals from src.ztare.signals.damage
3. Agent-channel — durable messages sent from one persistent role office
   to another

Each source produces Candidate objects with a scarcity signal and an
"intent" field (not "procedure" — GP-129 Godfrey-Smith pull-forward).
Candidates are NOT executed; they are returned to a ranker that picks
one for inbox escalation, human-in-loop.

This is the prototype. The full ranker + proposal-envelope writer
live in a separate module once the first 30 proposals have calibrated
the source weights.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from ztare.common.paths import REPO_ROOT
from ztare.orchestration.execution_routing import infer_execution_route
from ztare.research_director.primitive_class_rotation import (
    cross_substrate_primitive_class_ledger_path_for_repo,
)
from ztare.signals import damage


SEAMS_ROOT = REPO_ROOT / "research_areas" / "seams" / "mission"
TODO_PATTERN = re.compile(r"^\s*-\s*\[\s*\]\s+(.+)$", re.MULTILINE)


@dataclass
class Candidate:
    """A discovered work item, not yet proposed to the principal."""
    source: str                     # TODO-scan | damage-scan | closure-map | ...
    intent: str                     # one-sentence, what-for (not how)
    origin_path: Optional[Path]     # seam file, signal file, etc.
    scarcity_signal: str            # why this surfaced now
    raw_text: str                   # verbatim excerpt for triage
    age_days: Optional[float] = None
    severity: str = "info"          # info | warn | critical
    metadata: dict = field(default_factory=dict)


def discover_open_todos(
    *,
    root: Path = SEAMS_ROOT,
    max_per_source: int = 10,
) -> list[Candidate]:
    """Scan seam files for open `- [ ]` TODO boxes.

    Returns candidates ranked by file-mtime-desc then position-in-file.
    Stale seams (mtime > 60 days) are skipped — the GP-131 trail-lock-in
    defense says stale TODOs are a separate signal class and should not
    crowd out fresh items.
    """
    if not root.exists():
        return []

    now = time.time()
    stale_cutoff = now - 60 * 24 * 3600  # 60 days

    candidates: list[Candidate] = []
    seam_files = sorted(
        (p for p in root.glob("*.md") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for seam in seam_files:
        mtime = seam.stat().st_mtime
        if mtime < stale_cutoff:
            continue
        age_days = (now - mtime) / 86400.0
        try:
            text = seam.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in TODO_PATTERN.finditer(text):
            todo = match.group(1).strip()
            if not todo or len(todo) < 10:
                continue
            candidates.append(Candidate(
                source="TODO-scan",
                intent=todo[:200],
                origin_path=seam,
                scarcity_signal=(
                    f"open TODO in seam last touched {age_days:.1f} days ago; "
                    "self-authored commitment not yet closed"
                ),
                raw_text=todo,
                age_days=age_days,
                severity="info",
                metadata={"seam": seam.name},
            ))

    # Cap + stable ordering: freshest seams first, then order of TODOs
    # within file preserved.
    return candidates[:max_per_source]


def discover_damage_signals(
    *,
    max_per_source: int = 10,
) -> list[Candidate]:
    """Scan unresolved damage signals.

    Every damage signal is already a scarcity-filtered event — someone
    or something wrote it because an invariant was violated. Critical
    signals jump to the top regardless of age.
    """
    signals = damage.list_recent(limit=max_per_source * 3)
    now = datetime.now(timezone.utc)

    candidates: list[Candidate] = []
    for s in signals:
        try:
            ts = datetime.fromisoformat(s.timestamp_utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (now - ts).total_seconds() / 86400.0
        except ValueError:
            age = None

        intent = (
            f"resolve {s.kind} signal from {s.source}"
            if s.severity != "critical"
            else f"HARD STOP: critical {s.kind} signal from {s.source}"
        )
        candidates.append(Candidate(
            source="damage-scan",
            intent=intent,
            origin_path=None,
            scarcity_signal=(
                f"{s.severity}-severity signal, age {age:.2f} days"
                if age is not None else f"{s.severity}-severity signal"
            ),
            raw_text=s.detail,
            age_days=age,
            severity=s.severity,
            metadata={
                "source": s.source,
                "kind": s.kind,
                "timestamp_utc": s.timestamp_utc,
                "session_id": s.session_id,
            },
        ))

    # Critical first, then by age ascending (newer first).
    def sort_key(c: Candidate) -> tuple:
        sev_rank = {"critical": 0, "warn": 1, "info": 2}.get(c.severity, 3)
        return (sev_rank, c.age_days if c.age_days is not None else 1e9)

    candidates.sort(key=sort_key)
    return candidates[:max_per_source]


def discover_principal_goals(
    *,
    assigned_to: Optional[str] = None,
    max_per_source: int = 10,
) -> list[Candidate]:
    """GP-132 source: pending tasks the principal wrote to org/tasks/pending/.

    These are the HIGHEST-priority discovery source because they carry
    explicit principal intent — not inferred from artifacts, but stated.
    """
    from ztare.orchestration.goals_inbox import list_pending_goals
    goals = list_pending_goals(assigned_to=assigned_to)
    out: list[Candidate] = []
    for g in goals[:max_per_source]:
        route = infer_execution_route(
            frontmatter=g.raw_frontmatter,
            body=g.body,
            role_id=(assigned_to or g.assigned_to).replace("role.", "", 1),
        )
        severity = (
            "critical" if g.priority.lower() == "urgent" else
            "warn" if g.priority.lower() == "high" else
            "info"
        )
        out.append(Candidate(
            source="principal-goal",
            intent=(
                f"[{g.priority}] execute principal goal: {g.goal_id}"
                + (f" (deadline {g.deadline})" if g.deadline else "")
            ),
            origin_path=g.path,
            scarcity_signal=(
                "explicit principal directive in org/tasks/pending/ — "
                f"autonomous_scope_ok={g.autonomous_scope_ok}, "
                f"estimated_cost=${g.estimated_cost_usd:.2f}"
            ),
            raw_text=g.body[:500],
            age_days=None,
            severity=severity,
            metadata={
                "goal_id": g.goal_id,
                "priority": g.priority,
                "deadline": g.deadline,
                "estimated_cost_usd": g.estimated_cost_usd,
                "assigned_to": g.assigned_to,
                "autonomous_scope_ok": g.autonomous_scope_ok,
                "execution_route": route.as_dict(),
                "frontmatter": g.raw_frontmatter,
            },
        ))
    return out


def discover_agent_channel_messages(
    *,
    assigned_to: Optional[str] = None,
    max_per_source: int = 10,
) -> list[Candidate]:
    """Surface open messages in a persistent role's A2A inbox."""
    if not assigned_to or not assigned_to.startswith("role."):
        return []
    role_id = assigned_to.split(".", 1)[1]
    from ztare.orchestration.agent_channels import list_agent_messages

    out: list[Candidate] = []
    for msg in list_agent_messages(role_id=role_id, status="open", limit=max_per_source):
        severity = "warn" if msg.expects_response or msg.kind in {"request", "handoff"} else "info"
        out.append(Candidate(
            source="agent-channel",
            intent=f"respond to {msg.kind} from {msg.from_role}: {msg.subject}",
            origin_path=None,
            scarcity_signal=(
                "open persistent-agent message"
                + (" requiring response" if msg.expects_response else "")
            ),
            raw_text=msg.body[:1000],
            age_days=None,
            severity=severity,
            metadata={
                "message_id": msg.message_id,
                "thread_id": msg.thread_id,
                "from_role": msg.from_role,
                "to_role": msg.to_role,
                "kind": msg.kind,
                "expects_response": msg.expects_response,
                "references": msg.references,
                "artifacts": msg.artifacts,
            },
        ))
    return out


def discover_resolved_pending_execution(
    *,
    assigned_to: Optional[str] = None,
    max_per_source: int = 10,
) -> list[Candidate]:
    """Pick up gates that were resolved (approve) but never executed.

    Use case: a nested gate (claude wrote a gate during dispatch and exited)
    OR an orbit-side resolve via /api/gate/resolve. The daemon's normal
    `_wait_for_gate_resolution` flow only watches for resolution of gates
    IT opened in the same tick. Out-of-band resolutions need rediscovery.

    Returns Candidate objects whose intent describes the action to dispatch
    (typically a `make` command extracted from the gate's summary). The
    daemon's main flow will then dispatch claude/codex to run it.

    Idempotency: once dispatched, the daemon writes a sibling `.dispatched`
    file next to the resolved gate and skips it on later discovery passes.
    """
    out: list[Candidate] = []
    if assigned_to and assigned_to.startswith("role."):
        owner_match = assigned_to.split(".", 1)[1]
    else:
        owner_match = None

    resolved_dir = REPO_ROOT / "ztare_workspace" / "gates" / "resolved"
    if not resolved_dir.exists():
        return out

    import json as _json
    for path in sorted(resolved_dir.glob("proposal_*.json"), key=lambda p: -p.stat().st_mtime)[:max_per_source]:
        # Skip if dispatched already
        if path.with_suffix(".dispatched").exists():
            continue
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if data.get("status") != "resolved":
            continue
        chosen = data.get("resolution", {}).get("chosen_option")
        if chosen != "approve":
            # mark non-approve as "dispatched" so we don't re-scan
            try:
                path.with_suffix(".dispatched").write_text("non-approve\n")
            except Exception:  # noqa: BLE001
                pass
            continue
        owner = data.get("owner")
        if owner_match and owner != owner_match:
            continue
        # Build a Candidate the daemon will dispatch
        intent = data.get("candidate", {}).get("intent") or data.get("subject", "")
        out.append(Candidate(
            source="resolved-pending-execution",
            intent=f"execute resolved gate: {intent[:140]}",
            origin_path=path,
            scarcity_signal=(
                f"gate {data.get('gate_id', '?')} approved at "
                f"{data.get('resolution', {}).get('resolved_utc', '?')[:19]}; "
                f"awaiting dispatch"
            ),
            raw_text=data.get("summary", ""),
            severity="warn",  # approved + pending execution should rank above TODO scans
            metadata={
                "resolved_gate_id": data.get("gate_id"),
                "resolved_gate_path": str(path),
                "owner": owner,
                "kind": "execute-resolved-gate",
                # Preserve original candidate metadata for downstream auth
                **{k: v for k, v in (data.get("candidate", {}).get("metadata") or {}).items()
                   if k in ("assigned_to", "estimated_cost_usd", "execution_route", "frontmatter", "priority")},
            },
        ))
    return out


def discover_open_debates(
    *,
    assigned_to: Optional[str] = "debate_runner",
    idle_threshold_hours: float = 6.0,
    max_per_source: int = 5,
) -> list[Candidate]:
    """GP-195 — surface seam-debate work for the debate_runner role.

    Scans [internal-ref] for *.md files that are tagged as
    active debates, have not had a turn appended in the last
    `idle_threshold_hours`, and have not reached CONVERGED or
    ESCALATED_CAP per supervisor_findings_debate.read_debate_state.

    Returns a list of Candidate objects with kind="debate_turn". The
    daemon dispatches these as resolved-pending-execution candidates;
    the actual debate-turn machinery lives in supervisor_findings_runner.

    Discovery heuristic:
      - File contains a `<!-- debate_state:` comment OR the file ends
        with a turn marker (e.g., "## Turn N — <speaker>") AND
      - Last modification time exceeds idle_threshold_hours AND
      - File path is under [internal-ref]

    Soft-fails: if supervisor_findings_debate is not importable (legacy
    layout), this discoverer returns []. The role can be reactivated
    once #195 implementation completes the wiring.
    """
    import time
    from datetime import datetime, timedelta, timezone

    out: list[Candidate] = []
    seams_root = REPO_ROOT / "research_areas" / "private" / "seams"
    if not seams_root.exists():
        return out

    cutoff = datetime.now(timezone.utc) - timedelta(hours=idle_threshold_hours)

    try:
        from ztare.supervisor.supervisor_findings_debate import read_debate_state  # type: ignore
    except Exception:  # noqa: BLE001
        # Legacy layout missing — return empty rather than crash; the role
        # remains scaffolded and the daemon discovers nothing for it.
        return out

    for seam_path in seams_root.rglob("*.md"):
        try:
            mtime = datetime.fromtimestamp(seam_path.stat().st_mtime, tz=timezone.utc)
            if mtime > cutoff:
                continue
            text = seam_path.read_text(encoding="utf-8", errors="ignore")
            if "debate_state:" not in text and "## Turn " not in text:
                continue
            try:
                state = read_debate_state(str(seam_path))
            except Exception:  # noqa: BLE001
                continue
            verdict = getattr(state, "verdict", None) or state.get("verdict") if isinstance(state, dict) else None
            if verdict in ("CONVERGED", "ESCALATED_CAP"):
                continue
            out.append(Candidate(
                source="open_debate",
                kind="debate_turn",
                ref=str(seam_path.relative_to(REPO_ROOT)),
                title=f"Append turn to stagnant debate: {seam_path.name}",
                metadata={
                    "assigned_to": assigned_to or "debate_runner",
                    "idle_hours": (datetime.now(timezone.utc) - mtime).total_seconds() / 3600,
                    "execution_route": "supervisor_findings_runner",
                    "priority": "P1",
                },
            ))
            if len(out) >= max_per_source:
                break
        except Exception:  # noqa: BLE001
            continue

    return out


def discover_substrate_portfolio_opportunities(
    *,
    assigned_to: Optional[str] = None,
    max_per_source: int = 10,
) -> list[Candidate]:
    """GP-228 — surface portfolio-level work for the research_director role.

    Scans `org/runtime/substrate_portfolio.yaml` and proposes:
      (a) scaffold any registry member with `scaffolded: false`
      (b) rotate-eigenquestion for members where the cross-substrate
          ledger shows the substrate's recent runs anchored in one class
      (c) run-portfolio when no member has run in the active window

    Fires for the self_recursive_orchestrator (primary consumer; per
    GP-228 + the SRO mandate's 5 triggers), the research_director
    (cross-substrate findings consumer), and the principal (override).
    """
    if assigned_to:
        if not (
            assigned_to.endswith("self_recursive_orchestrator")
            or assigned_to.endswith("research_director")
            or assigned_to.endswith("principal")
        ):
            return []

    registry_path = REPO_ROOT / "org" / "runtime" / "substrate_portfolio.yaml"
    if not registry_path.exists():
        return []

    try:
        import yaml
        members = (yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}).get("members") or []
    except Exception:  # noqa: BLE001
        return []

    out: list[Candidate] = []
    for m in members[:max_per_source]:
        if not m.get("scaffolded"):
            out.append(Candidate(
                source="substrate-portfolio",
                intent=(
                    f"scaffold portfolio member '{m['slug']}' (charter stub + "
                    f"rubric authoring) per GP-228 portfolio registry"
                ),
                origin_path=registry_path,
                scarcity_signal="portfolio member registered but not authored",
                raw_text=f"slug={m['slug']} eigenquestion={m.get('eigenquestion_summary')}",
                severity="info",
                metadata={
                    "slug": m["slug"],
                    "kind": "scaffold",
                    "command": "python -m src.ztare.research_director.substrate_portfolio scaffold",
                },
            ))

    # Eigenquestion-rotation candidate: any scaffolded substrate whose
    # cross-substrate ledger shows ≥3 recent runs in the same class.
    ledger_path = cross_substrate_primitive_class_ledger_path_for_repo(REPO_ROOT)
    if ledger_path.exists():
        try:
            anchored: dict[str, dict[str, int]] = {}
            for line in ledger_path.read_text(encoding="utf-8").splitlines()[-200:]:
                line = line.strip()
                if not line:
                    continue
                import json as _json
                try:
                    rec = _json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                slug = rec.get("substrate_slug")
                cls = rec.get("class_name")
                if not slug or not cls:
                    continue
                anchored.setdefault(slug, {}).setdefault(cls, 0)
                anchored[slug][cls] += 1
            for slug, by_class in anchored.items():
                top_cls, top_count = max(by_class.items(), key=lambda kv: kv[1])
                if top_count >= 3:
                    out.append(Candidate(
                        source="substrate-portfolio",
                        intent=(
                            f"rotate eigenquestion for '{slug}' — "
                            f"anchored on class '{top_cls}' across {top_count} runs"
                        ),
                        origin_path=ledger_path,
                        scarcity_signal=f"family-attractor: {top_count}× '{top_cls}'",
                        raw_text=f"slug={slug} top_class={top_cls} count={top_count}",
                        severity="warn",
                        metadata={
                            "slug": slug,
                            "kind": "rotate-eigenquestion",
                            "command": (
                                f"python -m src.ztare.research_director."
                                f"eigenquestion_generator --project {slug}"
                            ),
                        },
                    ))
        except Exception:  # noqa: BLE001
            pass

    return out


def _is_in_role_scope(candidate: Candidate, assigned_to: Optional[str]) -> bool:
    """GP-228 / SRO scope filter — keep candidates that match the role's mandate.

    For self_recursive_orchestrator, only ztare_on_ztare_* work passes. For
    other roles, falls through (no filtering — the role's existing logic owns
    its scope). Role-scope mandates live in tenants/<id>/mandates/; this
    function encodes the predicate for the SRO mandate's "OUT-OF-SCOPE
    EXAMPLES" section without requiring the daemon to load the mandate text.
    """
    if not assigned_to or not assigned_to.endswith("self_recursive_orchestrator"):
        return True

    # SRO scope predicates (any one passes):
    # 1. GP-228 portfolio source — scoped by construction
    if candidate.source == "substrate-portfolio":
        return True
    # 2. Principal goals explicitly assigned to this role — explicit
    #    assignment beats text-match heuristic
    if candidate.source == "principal-goal":
        return True
    # 3. Agent-channel messages addressed to this role
    if candidate.source == "agent-channel":
        return True
    # 4. Resolved-pending-execution gates — owner field is checked at source
    if candidate.source == "resolved-pending-execution":
        return True
    # 4. Damage signals emitted by SRO-related components
    if candidate.source == "damage-scan":
        text = (candidate.intent or "").lower() + " " + (candidate.raw_text or "").lower()
        if "ztare_on_ztare" in text or "self_recursive_orchestrator" in text or "sro" in text:
            return True
    # 5. Text corpus mentions ztare_on_ztare_* (TODO-scan + others)
    text_corpus = " ".join((
        candidate.intent or "",
        candidate.scarcity_signal or "",
        str(candidate.origin_path or ""),
        candidate.raw_text or "",
    )).lower()
    if "ztare_on_ztare" in text_corpus:
        return True
    return False


def discover_all(
    *,
    max_per_source: int = 10,
    assigned_to: Optional[str] = None,
) -> list[Candidate]:
    """Run all implemented discovery sources and return combined list.

    Ordering: critical damage signals first, then principal goals, then
    agent-channel obligations, then non-critical damage, then TODO-scan,
    then substrate-portfolio (GP-228 — director-level work). The ranker
    downstream decides which to propose; this function keeps host damage
    ahead of routine work.

    Role-scope filtering: candidates outside the calling role's mandate
    are dropped via `_is_in_role_scope`. For self_recursive_orchestrator,
    only ztare_on_ztare_* work passes; for other roles, no filter applied.
    """
    out: list[Candidate] = []
    damage_candidates = discover_damage_signals(max_per_source=max_per_source)
    out.extend([c for c in damage_candidates if c.severity == "critical"])
    # Resolved-but-unexecuted approved gates rank ABOVE most other sources
    # because the principal already approved them — they're decision-critical.
    out.extend(discover_resolved_pending_execution(
        assigned_to=assigned_to, max_per_source=max_per_source))
    out.extend(discover_principal_goals(
        assigned_to=assigned_to, max_per_source=max_per_source))
    out.extend(discover_agent_channel_messages(
        assigned_to=assigned_to, max_per_source=max_per_source))
    out.extend([c for c in damage_candidates if c.severity != "critical"])
    out.extend(discover_open_todos(max_per_source=max_per_source))
    out.extend(discover_substrate_portfolio_opportunities(
        assigned_to=assigned_to, max_per_source=max_per_source))
    # GP-195 — debate-runner role surfaces stagnant seams as work
    if assigned_to in (None, "debate_runner"):
        out.extend(discover_open_debates(
            assigned_to=assigned_to or "debate_runner", max_per_source=max_per_source))

    # Apply per-role scope filter (SRO is the only role with a tight scope today)
    return [c for c in out if _is_in_role_scope(c, assigned_to)]


def format_candidate_for_inbox(c: Candidate) -> str:
    """Render a candidate as the GP-131 proposal envelope."""
    origin = str(c.origin_path.relative_to(REPO_ROOT)) if c.origin_path else "n/a"
    meta_str = ", ".join(f"{k}={v}" for k, v in c.metadata.items() if v)
    return (
        f"Source:           {c.source}\n"
        f"Intent:           {c.intent}\n"
        f"Candidate action: <propose a bounded next move to the principal>\n"
        f"Origin:           {origin}\n"
        f"Scarcity signal:  {c.scarcity_signal}\n"
        f"Age:              {c.age_days:.2f} days" if c.age_days is not None
        else f"Age:              unknown"
    ) + (f"\nSeverity:         {c.severity}\n"
         f"Metadata:         {meta_str}\n"
         f"Raw excerpt:      {c.raw_text[:300]}")
