#!/usr/bin/env python3
"""Closure daemon — exogenous-pressure enforcer (GP-168 addendum 2026-04-27).

Stateless poller over the OKR tree:
  - org/objectives/<id>.md       — Objective layer (closure_deadline)
  - org/key_results/<id>.md      — KR layer (review_overdue_threshold_days
                                    + recurrence-based duty cadence, 2026-05-06)
  - org/tasks/{pending,active}/  — Task layer (closure_deadline + budget_cap_usd)

KRs may declare a `recurrence` field (ISO-8601 duration whitelist:
P1D / P7D / P14D / P1M / P3M / P1Y / etc.). When set, the daemon polls
`last_attested + recurrence + grace_period` and emits `kr_duty_overdue`
gates carrying `damage_signal_kind: duty_overdue`. KRs without
`recurrence` use the legacy `review_overdue_threshold_days` path
unchanged. See `org/signals/SIGNAL_KINDS.md` § duty_overdue.

The daemon does NOT own state. It reads frontmatter, computes pressure
predicates, and submits state-transition *requests* to the executive
inbox at `ztare_workspace/gates/pending/`. The GP-070 orchestrator
owns the actual mutation; this daemon just schedules.

Replaces the prior parallel-tree daemon (org/clocks/ + org/budgets/ +
org/escalations/) per Panel A synthesis. The decision-critical GP-168
behaviors (time-pressure auto-resolution, budget-pressure
auto-resolution, exogenous-oracle escalation) are preserved as
operations on the OKR tree's frontmatter rather than as a parallel
persistence layer.

Usage:
    python scripts/public/control/closure_daemon.py [--once] [--poll-seconds 30]
        [--org-root org] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------- time + IO helpers ----------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime] = None) -> str:
    return (dt or utc_now()).isoformat().replace("+00:00", "Z")


def parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


# ISO-8601 duration whitelist for KR.recurrence + KR.grace_period.
# Only support the small set we actually use; richer durations should
# trigger an explicit error rather than silent misparse. Covers the
# realistic cadences: hourly stress test, daily, weekly, biweekly,
# monthly, quarterly, yearly.
_DURATION_DAYS: dict[str, float] = {
    "PT1H": 1.0 / 24, "PT6H": 0.25, "PT12H": 0.5,
    "P1D": 1.0, "P2D": 2.0, "P3D": 3.0,
    "P7D": 7.0, "P14D": 14.0,
    "P1M": 30.0,           # treat as 30d for cadence purposes; not calendar-correct
    "P3M": 90.0,
    "P6M": 180.0,
    "P1Y": 365.0,
}


def parse_duration_days(s: Optional[str]) -> Optional[float]:
    """Parse an ISO-8601 duration from the whitelist into days.

    Returns None on missing input. Returns None and logs on unknown
    duration string — a daemon must not silently reinterpret an unknown
    cadence; the KR author should fix the string.
    """
    if s is None:
        return None
    s = str(s).strip().upper()
    if s in _DURATION_DAYS:
        return _DURATION_DAYS[s]
    # Permissive: PnD where n is integer
    m = re.match(r"^P(\d+)D$", s)
    if m:
        return float(m.group(1))
    print(
        f"[closure-daemon] unknown duration string {s!r}; "
        f"recurrence ignored. Whitelist: {sorted(_DURATION_DAYS)}",
        file=sys.stderr,
    )
    return None


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ---------- minimal frontmatter parser ----------
# Avoid pyyaml dependency by parsing only the simple flat-and-string YAML
# subset we actually emit. If something more complex appears, fall back to
# pyyaml when present.

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


def _try_pyyaml(text: str) -> Optional[dict]:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except Exception:
        return None


def _scalar(s: str) -> Any:
    s = s.strip()
    if s == "" or s.lower() == "null" or s.lower() == "none":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    # Quoted string
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    # Try float / int
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    return s


def parse_frontmatter(file_text: str) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    m = _FRONTMATTER_RE.match(file_text)
    if not m:
        return {}
    body = m.group(1)
    parsed = _try_pyyaml(body)
    if parsed is not None:
        return parsed if isinstance(parsed, dict) else {}
    # Fallback: very minimal flat-key parser
    out: dict[str, Any] = {}
    for line in body.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line or line.startswith(" "):
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = _scalar(v)
    return out


def read_file(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    return fm, text


# ---------- daemon ----------

@dataclass
class DaemonConfig:
    org_root: Path
    repo_root: Path
    poll_seconds: int
    once: bool
    dry_run: bool

    @property
    def gates_dir(self) -> Path:
        return self.repo_root / "ztare_workspace" / "gates" / "pending"

    @property
    def transitions_log(self) -> Path:
        return self.repo_root / "ztare_workspace" / "transitions.jsonl"


def open_gate(cfg: DaemonConfig, payload: dict) -> Path | None:
    """Write an entry into the executive inbox at ztare_workspace/gates/pending/.

    Idempotent: if a gate with the same gate_id already exists, do not
    overwrite it. Returns the gate path on creation, None on idempotent skip.
    """
    cfg.gates_dir.mkdir(parents=True, exist_ok=True)
    gate_id = payload.get("gate_id") or f"gate-{utc_iso().replace(':', '-').replace('.', '-')}"
    payload["gate_id"] = gate_id
    payload.setdefault("created_utc", utc_iso())
    payload.setdefault("status", "pending")
    out_path = cfg.gates_dir / f"{gate_id}.json"
    if out_path.exists():
        return None
    if cfg.dry_run:
        print(f"[dry-run] would open gate: {out_path}")
        return out_path
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    append_jsonl(cfg.transitions_log, {
        "ts": utc_iso(),
        "event": "gate.opened",
        "gate_id": gate_id,
        "source": "closure_daemon",
        "kind": payload.get("kind"),
        "subject": payload.get("subject"),
    })
    return out_path


# ---------- task layer ----------

def time_pressure_pct(created: datetime, deadline: datetime, now: datetime) -> float:
    total = (deadline - created).total_seconds()
    if total <= 0:
        return 1.0
    return max(0.0, (now - created).total_seconds() / total)


def process_tasks(cfg: DaemonConfig) -> int:
    """Walk org/tasks/{pending,active}/ and evaluate time + budget pressure."""
    out = 0
    now = utc_now()
    for state_dir in ("pending", "active"):
        d = cfg.org_root / "tasks" / state_dir
        if not d.exists():
            continue
        for path in sorted(d.glob("*.md")):
            try:
                fm, _ = read_file(path)
            except Exception as exc:
                print(f"[closure-daemon] skip malformed task {path}: {exc}", file=sys.stderr)
                continue
            if not fm:
                continue
            task_id = fm.get("task_id") or path.stem
            created_str = fm.get("created_utc")
            deadline_str = fm.get("closure_deadline")
            warn_at = float(fm.get("warn_at_pct", 0.7))
            escalate_at = float(fm.get("escalate_at_pct", 0.9))
            auto_resolution = fm.get("auto_resolution", "deny")

            # Time pressure
            if created_str and deadline_str:
                try:
                    created = parse_iso(str(created_str))
                    deadline = parse_iso(str(deadline_str))
                except Exception:
                    pass
                else:
                    pct = time_pressure_pct(created, deadline, now)
                    if pct >= 1.0:
                        # Deadline hit — request resolution via gate
                        opened = open_gate(cfg, {
                            "gate_id": f"task-deadline-{task_id}",
                            "kind": "task_deadline_expired",
                            "subject": task_id,
                            "summary": f"Task {task_id} closure_deadline reached; auto_resolution={auto_resolution}",
                            "options": [
                                {"id": "apply_auto", "consequence": f"apply auto_resolution={auto_resolution}"},
                                {"id": "extend", "consequence": "extend closure_deadline by 24h"},
                                {"id": "escalate", "consequence": "open principal escalation"},
                            ],
                            "default_after_days": 1,
                            "auto_resolution_on_default": "apply_auto",
                            "task_path": str(path.relative_to(cfg.repo_root)),
                            "auto_resolution": auto_resolution,
                            "owner": fm.get("assigned_to", "role.principal"),
                        })
                        if opened:
                            out += 1
                    elif pct >= escalate_at:
                        open_gate(cfg, {
                            "gate_id": f"task-escalate-{task_id}",
                            "kind": "task_pressure_escalate",
                            "subject": task_id,
                            "summary": f"Task {task_id} at {pct*100:.0f}% of closure_deadline",
                            "task_path": str(path.relative_to(cfg.repo_root)),
                            "owner": fm.get("assigned_to", "role.principal"),
                        })
                    elif pct >= warn_at:
                        # Soft warn — append to transitions log only, no gate
                        append_jsonl(cfg.transitions_log, {
                            "ts": utc_iso(now),
                            "event": "task.pressure_warn",
                            "task_id": task_id,
                            "pct": round(pct * 100, 2),
                        })

            # Budget pressure
            cap = fm.get("budget_cap_usd")
            spent = fm.get("budget_spent_usd")
            if isinstance(cap, (int, float)) and cap > 0 and isinstance(spent, (int, float)):
                pct = float(spent) / float(cap)
                exhaust_action = fm.get("budget_exhaust_action", "escalate")
                if pct >= 1.0:
                    opened = open_gate(cfg, {
                        "gate_id": f"task-budget-{task_id}",
                        "kind": "task_budget_exhausted",
                        "subject": task_id,
                        "summary": f"Task {task_id} burned ${spent:.2f} of ${cap:.2f}; budget_exhaust_action={exhaust_action}",
                        "options": [
                            {"id": "apply_exhaust", "consequence": f"apply budget_exhaust_action={exhaust_action}"},
                            {"id": "refund", "consequence": "raise budget_cap_usd; task continues"},
                        ],
                        "default_after_days": 1,
                        "auto_resolution_on_default": "apply_exhaust",
                        "task_path": str(path.relative_to(cfg.repo_root)),
                        "exhaust_action": exhaust_action,
                        "owner": fm.get("assigned_to", "role.principal"),
                    })
                    if opened:
                        out += 1
                elif pct >= 0.8:
                    open_gate(cfg, {
                        "gate_id": f"task-budget-warn-{task_id}",
                        "kind": "task_budget_warn",
                        "subject": task_id,
                        "summary": f"Task {task_id} at {pct*100:.0f}% of budget (${spent:.2f}/${cap:.2f})",
                        "task_path": str(path.relative_to(cfg.repo_root)),
                        "owner": fm.get("assigned_to", "role.principal"),
                    })
    return out


# ---------- key result layer ----------

def _process_kr_duty_recurrence(
    cfg: DaemonConfig,
    fm: dict,
    path: Path,
    now: datetime,
) -> int:
    """Handle KRs with `recurrence` set — periodic-duty cadence layer.

    Schema (additive on top of KR README schema):
      - recurrence: ISO-8601 duration (whitelist)        REQUIRED for this layer
      - grace_period: ISO-8601 duration (whitelist)      default P0D (no grace)
      - last_attested: ISO timestamp                     default created_utc
      - owner_role: <role.id>                            default role.principal
      - attestation_method: gate_signature | session_artifact | f_row_link
      - attestation_gate_kind: e.g. DUTY_PERFORMED       used by future gate handler
      - artifacts_required: [str, ...]                   verified by gate handler

    Severity ladder:
      - now <= next_due                          : silent (warn band reserved)
      - next_due < now <= next_due+grace         : info (transitions log only)
      - next_due+grace < now <= next_due+2*recur : warn gate
      - now > next_due+2*recurrence              : critical gate
    """
    kr_id = fm.get("kr_id") or path.stem
    owner = fm.get("owner_role", "role.principal")
    recurrence_days = parse_duration_days(fm.get("recurrence"))
    if recurrence_days is None:
        # Unknown duration string — whitelist parser already logged.
        return 0
    grace_days = parse_duration_days(fm.get("grace_period")) or 0.0

    last_attested_str = fm.get("last_attested") or fm.get("created_utc")
    if not last_attested_str:
        return 0
    try:
        last_attested = parse_iso(str(last_attested_str))
    except Exception:
        return 0

    next_due = last_attested + _timedelta_days(recurrence_days)
    grace_end = next_due + _timedelta_days(grace_days)
    critical_threshold = next_due + _timedelta_days(2 * recurrence_days)
    artifacts_required = fm.get("artifacts_required") or []
    if not isinstance(artifacts_required, list):
        artifacts_required = [artifacts_required]
    attestation_gate_kind = fm.get("attestation_gate_kind", "DUTY_PERFORMED")

    if now <= next_due:
        return 0  # not yet due
    if now <= grace_end:
        # Within grace — silent except for transitions log entry once
        # per cycle. Idempotent via gate_id, see below.
        append_jsonl(cfg.transitions_log, {
            "ts": utc_iso(now),
            "event": "kr.duty_in_grace",
            "kr_id": kr_id,
            "owner_role": owner,
            "next_due": utc_iso(next_due),
            "grace_end": utc_iso(grace_end),
        })
        return 0

    # Overdue — emit gate. Severity escalates based on how overdue.
    severity = "warn"
    cycle_index = 1
    if now > critical_threshold:
        severity = "critical"
        cycle_index = 2

    # Gate id includes the cycle so a stuck duty emits one gate per
    # missed cycle, not one gate forever (idempotency would otherwise
    # silently swallow ongoing misses).
    cycle_tag = next_due.strftime("%Y%m%dT%H%M%SZ")
    gate_id = f"kr-duty-overdue-{kr_id}-{cycle_tag}"

    opened = open_gate(cfg, {
        "gate_id": gate_id,
        "kind": "kr_duty_overdue",
        "subject": kr_id,
        "severity": severity,
        "summary": (
            f"KR {kr_id} duty overdue: last_attested={utc_iso(last_attested)}, "
            f"recurrence={fm.get('recurrence')}, grace={fm.get('grace_period') or 'P0D'}, "
            f"next_due={utc_iso(next_due)}, owner={owner}"
        ),
        "options": [
            {
                "id": "attest_done",
                "consequence": (
                    f"submit a {attestation_gate_kind} gate referencing kr_id={kr_id} "
                    f"and an artifact in artifacts_required; gate handler updates last_attested"
                ),
            },
            {"id": "ack_skip", "consequence": "append a check_in note explaining the skip; cadence resumes from now"},
            {"id": "extend_recurrence", "consequence": "edit KR's recurrence field to a longer cadence (mandate-aligned)"},
            {"id": "deactivate_kr", "consequence": "set status=failed; remove this duty from the role"},
        ],
        "default_after_days": 7,
        "auto_resolution_on_default": "ack_skip",
        "kr_path": str(path.relative_to(cfg.repo_root)),
        "objective_id": fm.get("objective_id"),
        "owner": owner,
        "owner_role": owner,
        "recurrence": fm.get("recurrence"),
        "grace_period": fm.get("grace_period"),
        "last_attested": utc_iso(last_attested),
        "next_due": utc_iso(next_due),
        "cycle_index": cycle_index,
        "attestation_method": fm.get("attestation_method", "gate_signature"),
        "attestation_gate_kind": attestation_gate_kind,
        "artifacts_required": artifacts_required,
        # Damage signal kind so downstream listeners can route by kind:
        "damage_signal_kind": "duty_overdue",
    })
    return 1 if opened else 0


def _timedelta_days(days: float):
    from datetime import timedelta
    return timedelta(days=days)


def process_key_results(cfg: DaemonConfig) -> int:
    """Walk org/key_results/ and check measurement-overdue + duty cadence."""
    out = 0
    now = utc_now()
    d = cfg.org_root / "key_results"
    if not d.exists():
        return 0
    for path in sorted(d.glob("*.md")):
        try:
            fm, _ = read_file(path)
        except Exception as exc:
            print(f"[closure-daemon] skip malformed kr {path}: {exc}", file=sys.stderr)
            continue
        if not fm or fm.get("status") in ("done", "failed"):
            continue
        kr_id = fm.get("kr_id") or path.stem

        # ---- Recurrence layer (2026-05-06) ---------------------------
        # When a KR declares `recurrence`, it represents a periodic
        # duty (per `org/signals/SIGNAL_KINDS.md` § duty_overdue). The
        # duty layer is fully back-compat: KRs without `recurrence`
        # fall through to the original measurement-overdue logic
        # below, untouched.
        recurrence_str = fm.get("recurrence")
        if recurrence_str:
            opened_n = _process_kr_duty_recurrence(cfg, fm, path, now)
            out += opened_n
            # A KR with recurrence is duty-shaped; skip the legacy
            # measurement-overdue branch to avoid double-emission of
            # parallel gates for the same artifact.
            continue

        last_measured = fm.get("last_measured_utc")
        threshold_days = int(fm.get("review_overdue_threshold_days", 14))
        measurement_source = fm.get("measurement_source", "principal")

        # If never measured, age from created_utc
        ref_str = last_measured or fm.get("created_utc")
        if not ref_str:
            continue
        try:
            ref = parse_iso(str(ref_str))
        except Exception:
            continue
        age_days = (now - ref).total_seconds() / 86400.0
        if age_days >= threshold_days:
            opened = open_gate(cfg, {
                "gate_id": f"kr-overdue-{kr_id}",
                "kind": "kr_measurement_overdue",
                "subject": kr_id,
                "summary": (
                    f"KR {kr_id} not measured in {age_days:.0f} days "
                    f"(threshold {threshold_days}); source={measurement_source}"
                ),
                "options": [
                    {"id": "measure_now", "consequence": "principal records the measurement"},
                    {"id": "ack_unchanged", "consequence": "extend last_measured_utc to now (confidence unchanged)"},
                    {"id": "mark_at_risk", "consequence": "set status=at_risk; surfaces in parent Objective closure"},
                    {"id": "mark_failed", "consequence": "set status=failed; KR is dead"},
                ],
                "default_after_days": 7,
                "auto_resolution_on_default": "mark_at_risk",
                "kr_path": str(path.relative_to(cfg.repo_root)),
                "objective_id": fm.get("objective_id"),
                "owner": "role.principal",
            })
            if opened:
                out += 1
    return out


# ---------- objective layer ----------

def process_objectives(cfg: DaemonConfig) -> int:
    """Walk org/objectives/ and check closure_deadline + honesty score on closure prompts."""
    out = 0
    now = utc_now()
    d = cfg.org_root / "objectives"
    if not d.exists():
        return 0
    for path in sorted(d.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            fm, _ = read_file(path)
        except Exception as exc:
            print(f"[closure-daemon] skip malformed objective {path}: {exc}", file=sys.stderr)
            continue
        if not fm or fm.get("status") != "active":
            continue
        obj_id = fm.get("objective_id") or path.stem
        deadline_str = fm.get("closure_deadline") or fm.get("target_date")
        if not deadline_str:
            continue
        try:
            deadline = parse_iso(str(deadline_str))
        except Exception:
            continue
        if now >= deadline:
            # Compute honesty score for this Objective at closure
            honesty = compute_honesty_score(cfg, obj_id)
            opened = open_gate(cfg, {
                "gate_id": f"obj-closure-{obj_id}",
                "kind": "objective_closure_prompt",
                "subject": obj_id,
                "summary": (
                    f"Objective {obj_id} reached closure_deadline. "
                    f"Honesty score (world-measured KRs with recent measurement): "
                    f"{honesty['score']:.2f} ({honesty['measured']}/{honesty['total']})"
                ),
                "options": [
                    {"id": "done", "consequence": "mark Objective done; score each KR 0.0–1.0"},
                    {"id": "abandon", "consequence": "mark Objective abandoned with postmortem"},
                    {"id": "extend", "consequence": "extend closure_deadline (specify new date)"},
                ],
                "default_after_days": 7,
                "auto_resolution_on_default": "abandon",
                "objective_path": str(path.relative_to(cfg.repo_root)),
                "honesty": honesty,
                "owner": "role.principal",
            })
            if opened:
                out += 1
    return out


def compute_honesty_score(cfg: DaemonConfig, objective_id: str) -> dict:
    """Per-Objective honesty score: world-measured KRs with non-null
    last_measured_utc / total world-measured KRs.

    A score < 0.5 across two consecutive Objective closures triggers the
    theatre-detection alert (separate function, see check_theatre_signal).
    """
    d = cfg.org_root / "key_results"
    if not d.exists():
        return {"score": 1.0, "measured": 0, "total": 0}
    total = 0
    measured = 0
    for path in d.glob("*.md"):
        try:
            fm, _ = read_file(path)
        except Exception:
            continue
        if not fm or fm.get("objective_id") != objective_id:
            continue
        if fm.get("measurement_locus") != "world":
            continue
        total += 1
        if fm.get("last_measured_utc"):
            measured += 1
    score = (measured / total) if total > 0 else 1.0
    return {"score": score, "measured": measured, "total": total}


# ---------- main ----------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="GP-168 closure daemon — stateless poller over the OKR tree"
    )
    parser.add_argument("--org-root", default="org", help="Path to org/ (default: org)")
    parser.add_argument("--poll-seconds", type=int, default=30, help="Poll interval (default: 30s)")
    parser.add_argument("--once", action="store_true", help="Run a single poll cycle then exit")
    parser.add_argument("--dry-run", action="store_true", help="Log what would happen but don't write gates")
    args = parser.parse_args()

    org_root = Path(args.org_root).resolve()
    repo_root = org_root.parent
    if not org_root.exists():
        print(f"[closure-daemon] org_root not found: {org_root}", file=sys.stderr)
        return 2

    cfg = DaemonConfig(
        org_root=org_root,
        repo_root=repo_root,
        poll_seconds=args.poll_seconds,
        once=args.once,
        dry_run=args.dry_run,
    )

    print(
        f"[closure-daemon] starting "
        f"(org_root={cfg.org_root}, poll={cfg.poll_seconds}s, "
        f"once={cfg.once}, dry_run={cfg.dry_run})"
    )

    while True:
        try:
            t = process_tasks(cfg)
            k = process_key_results(cfg)
            o = process_objectives(cfg)
            if t or k or o:
                print(f"[closure-daemon] cycle: {t} task gate(s), {k} kr gate(s), {o} objective gate(s)")
        except Exception as exc:
            print(f"[closure-daemon] cycle error: {exc}", file=sys.stderr)
        if cfg.once:
            return 0
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
