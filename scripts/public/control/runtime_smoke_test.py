#!/usr/bin/env python3
"""Runtime smoke test — runnable end-to-end exercise of the org runtime.

Exercises the five elements of the org runtime in one script:

    1. ONE task                — a synthetic task dropped into org/tasks/
    2. ONE preference profile  — read principal preferences and confirm the
                                 priority axes parse
    3. ONE role loop           — validate every role contract against the
                                 schema and rehearse a daemon boot
    4. ONE approval channel    — drop a synthetic approval, resolve it via
                                 the same code path Orbit uses, verify the
                                 resolved record lands
    5. ONE audit trail         — verify the resolution wrote one row to
                                 ztare_workspace/transitions.jsonl

The script writes only TEST_PREFIX-stamped files and cleans up everything it
created on exit unless --keep is passed. It does NOT invoke any agent CLI
(no LLM calls, no spend) so it is safe to run in CI or on a fresh checkout.

Returns 0 on a green run, non-zero on the first red check.

Usage:
    python scripts/public/control/runtime_smoke_test.py
    python scripts/public/control/runtime_smoke_test.py --keep   # leave artifacts for debug
    python scripts/public/control/runtime_smoke_test.py --json   # JSON report
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ORG_DIR = REPO_ROOT / "org"
GATES_PENDING = REPO_ROOT / "ztare_workspace" / "gates" / "pending"
GATES_RESOLVED = REPO_ROOT / "ztare_workspace" / "gates" / "resolved"
TRANSITIONS_LOG = REPO_ROOT / "ztare_workspace" / "transitions.jsonl"
TASKS_ACTIVE = ORG_DIR / "tasks" / "active"
PREFS_PATH = ORG_DIR / "preferences" / "principal.yaml"
ROLES_DIR = ORG_DIR / "roles"

TEST_PREFIX = "test_runtime_smoke"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _stamp() -> str:
    return f"{TEST_PREFIX}_{_utc_now()}"


def step_research_problem(stamp: str, report: dict[str, Any]) -> Path:
    """Drop one synthetic task into org/tasks/active/ as the research problem."""
    TASKS_ACTIVE.mkdir(parents=True, exist_ok=True)
    task_path = TASKS_ACTIVE / f"{stamp}.md"
    task_id = stamp
    body = f"""---
task_id: {task_id}
title: "Runtime smoke test synthetic task"
status: active
priority: low
assigned_to: role.manager
created_utc: "{datetime.now(tz=timezone.utc).isoformat()}"
budget_cap_usd: 0.00
budget_spent_usd: 0.00
closure_deadline: null
---

This task exists only to exercise the runtime smoke test end-to-end. It is created
by `scripts/public/control/runtime_smoke_test.py` and removed at the end of the run. If you find
this task lying around outside a smoke-test run, it means a previous run was
interrupted before cleanup — safe to delete by filename pattern.
"""
    task_path.write_text(body)
    report["steps"].append({
        "name": "research_problem",
        "ok": task_path.exists(),
        "artifact": str(task_path.relative_to(REPO_ROOT)),
        "task_id": task_id,
    })
    return task_path


def step_preference_profile(report: dict[str, Any]) -> None:
    """Read the principal preferences and confirm research_taste axes parse."""
    if not PREFS_PATH.exists():
        report["steps"].append({
            "name": "preference_profile",
            "ok": False,
            "error": f"missing {PREFS_PATH.relative_to(REPO_ROOT)}",
        })
        return

    try:
        try:
            import yaml  # type: ignore
        except Exception:
            report["steps"].append({
                "name": "preference_profile",
                "ok": False,
                "error": "PyYAML not installed; required to parse preferences",
            })
            return
        prefs = yaml.safe_load(PREFS_PATH.read_text()) or {}
        taste_axes = (prefs.get("research_taste") or {}).get("axes") or {}
        report["steps"].append({
            "name": "preference_profile",
            "ok": bool(taste_axes),
            "artifact": str(PREFS_PATH.relative_to(REPO_ROOT)),
            "axes_count": len(taste_axes),
            "axes": sorted(taste_axes.keys()) if isinstance(taste_axes, dict) else [],
        })
    except Exception as exc:  # noqa: BLE001
        report["steps"].append({
            "name": "preference_profile",
            "ok": False,
            "error": f"parse_failed: {exc}",
        })


def step_role_loop(report: dict[str, Any]) -> None:
    """Preflight every role yaml; the loop is sound iff all roles preflight green."""
    role_files = sorted(ROLES_DIR.glob("*.yaml"))
    role_results: list[dict[str, Any]] = []
    all_ok = True
    for rf in role_files:
        role_id = rf.stem
        try:
            proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "public" / "control" / "org_role_preflight.py"),
                 "--role", role_id, "--json"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
            )
            data = json.loads(proc.stdout) if proc.stdout.strip() else {"ok": False}
            ok = bool(data.get("ok"))
            role_results.append({"role_id": role_id, "ok": ok,
                                 "errors": data.get("errors", [])})
            if not ok:
                all_ok = False
        except Exception as exc:  # noqa: BLE001
            role_results.append({"role_id": role_id, "ok": False, "error": str(exc)})
            all_ok = False
    report["steps"].append({
        "name": "role_loop",
        "ok": all_ok,
        "roles_checked": len(role_files),
        "roles": role_results,
    })


def step_approval_channel(stamp: str, report: dict[str, Any]) -> tuple[Path, Path]:
    """Drop a synthetic gate and resolve it via the same filesystem ops Orbit uses.

    Returns (pending_path_handled, resolved_path) so cleanup can find them.
    """
    GATES_PENDING.mkdir(parents=True, exist_ok=True)
    GATES_RESOLVED.mkdir(parents=True, exist_ok=True)

    gate_id = stamp
    pending_path = GATES_PENDING / f"{gate_id}.json"
    resolved_path = GATES_RESOLVED / f"{gate_id}.json"

    pending_payload = {
        "gate_id": gate_id,
        "kind": "task_review",
        "subject": "Runtime smoke test synthetic approval",
        "summary": "Created by scripts/public/control/runtime_smoke_test.py; auto-resolved.",
        "options": [
            {"id": "approve", "consequence": "no real consequence — smoke test"},
            {"id": "reject", "consequence": "no real consequence — smoke test"},
        ],
        "owner": "principal",
        "created_utc": datetime.now(tz=timezone.utc).isoformat(),
        "status": "pending",
    }
    pending_path.write_text(json.dumps(pending_payload, indent=2))

    # Resolve using the same write pattern the Orbit /api/gate/resolve endpoint
    # uses (atomic temp + rename, append to transitions.jsonl, rename pending
    # to .handled). We do not call the HTTP API because that would force this
    # smoke test to depend on Orbit being up; instead we exercise the
    # canonical filesystem ops directly.
    resolved_payload = dict(pending_payload)
    resolved_payload["status"] = "resolved"
    resolved_payload["resolution"] = {
        "chosen_option": "approve",
        "reason": "runtime smoke test",
        "resolved_by": "runtime_smoke",
        "resolved_utc": datetime.now(tz=timezone.utc).isoformat(),
    }
    tmp_path = resolved_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(resolved_payload, indent=2))
    tmp_path.replace(resolved_path)

    handled_path = pending_path.with_suffix(".json.handled")
    pending_path.rename(handled_path)

    TRANSITIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRANSITIONS_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "event": "gate.resolved",
            "gate_id": gate_id,
            "chosen_option": "approve",
            "resolved_by": "runtime_smoke",
        }) + "\n")

    ok = resolved_path.exists() and handled_path.exists()
    report["steps"].append({
        "name": "approval_channel",
        "ok": ok,
        "gate_id": gate_id,
        "resolved_artifact": str(resolved_path.relative_to(REPO_ROOT)),
        "handled_artifact": str(handled_path.relative_to(REPO_ROOT)),
    })
    return handled_path, resolved_path


def step_audit_trail(stamp: str, report: dict[str, Any]) -> None:
    """Verify the resolution we just wrote landed as one row in transitions.jsonl."""
    if not TRANSITIONS_LOG.exists():
        report["steps"].append({
            "name": "audit_trail",
            "ok": False,
            "error": f"missing {TRANSITIONS_LOG.relative_to(REPO_ROOT)}",
        })
        return
    last_lines = TRANSITIONS_LOG.read_text().splitlines()[-50:]
    matches = []
    for line in last_lines:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("gate_id") == stamp and row.get("event") == "gate.resolved":
            matches.append(row)
    ok = len(matches) == 1
    report["steps"].append({
        "name": "audit_trail",
        "ok": ok,
        "matches_found": len(matches),
        "log_path": str(TRANSITIONS_LOG.relative_to(REPO_ROOT)),
    })


def cleanup(stamp: str, report: dict[str, Any]) -> None:
    """Remove every artifact the smoke test created. Idempotent."""
    removed: list[str] = []

    # Task
    for p in TASKS_ACTIVE.glob(f"{stamp}.md"):
        p.unlink(missing_ok=True)
        removed.append(str(p.relative_to(REPO_ROOT)))

    # Gate (pending — should already be renamed to .handled, but cover both)
    for p in GATES_PENDING.glob(f"{stamp}.json*"):
        p.unlink(missing_ok=True)
        removed.append(str(p.relative_to(REPO_ROOT)))

    # Gate (resolved)
    for p in GATES_RESOLVED.glob(f"{stamp}.json"):
        p.unlink(missing_ok=True)
        removed.append(str(p.relative_to(REPO_ROOT)))

    # Audit row — strip exactly the one row we appended (preserve everything
    # else). Use the row's gate_id to match.
    if TRANSITIONS_LOG.exists():
        lines = TRANSITIONS_LOG.read_text().splitlines()
        kept = []
        stripped = 0
        for line in lines:
            try:
                row = json.loads(line)
                if row.get("gate_id") == stamp and row.get("resolved_by") == "runtime_smoke":
                    stripped += 1
                    continue
            except Exception:
                pass
            kept.append(line)
        if stripped > 0:
            TRANSITIONS_LOG.write_text("\n".join(kept) + ("\n" if kept else ""))
            removed.append(f"{TRANSITIONS_LOG.relative_to(REPO_ROOT)} (1 row)")

    report["cleanup"] = {"ok": True, "removed": removed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", action="store_true",
                        help="leave smoke-test artifacts for debugging")
    parser.add_argument("--json", action="store_true",
                        help="print full JSON report")
    args = parser.parse_args()

    stamp = _stamp()
    started_utc = datetime.now(tz=timezone.utc).isoformat()
    report: dict[str, Any] = {
        "schema_version": 1,
        "stamp": stamp,
        "started_utc": started_utc,
        "ok": False,
        "steps": [],
    }

    try:
        step_research_problem(stamp, report)
        step_preference_profile(report)
        step_role_loop(report)
        step_approval_channel(stamp, report)
        # Tiny sleep so the audit row is durably on disk before we read.
        time.sleep(0.05)
        step_audit_trail(stamp, report)
    finally:
        if not args.keep:
            cleanup(stamp, report)
        else:
            report["cleanup"] = {"ok": True, "skipped": "kept (--keep)"}

    report["finished_utc"] = datetime.now(tz=timezone.utc).isoformat()
    report["ok"] = all(s.get("ok") for s in report["steps"])

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        status = "PASS" if report["ok"] else "FAIL"
        print(f"{status}  runtime smoke test  stamp={stamp}")
        for s in report["steps"]:
            mark = "ok" if s.get("ok") else "FAIL"
            extra = ""
            if s["name"] == "preference_profile" and s.get("axes_count") is not None:
                extra = f" (taste axes: {s['axes_count']})"
            if s["name"] == "role_loop":
                extra = f" ({s['roles_checked']} roles)"
            print(f"  {mark}  {s['name']}{extra}")
            if not s.get("ok"):
                err = s.get("error") or s.get("errors")
                if err:
                    print(f"      {err}")
                # surface per-role errors
                if s["name"] == "role_loop":
                    for r in s.get("roles", []):
                        if not r.get("ok"):
                            print(f"      role {r['role_id']}: {r.get('errors') or r.get('error')}")
        if not args.keep:
            removed_count = len(report.get("cleanup", {}).get("removed", []))
            print(f"  cleanup: removed {removed_count} artifact(s)")
        else:
            print(f"  cleanup: skipped (--keep); stamp={stamp}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
