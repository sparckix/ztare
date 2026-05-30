#!/usr/bin/env python3
"""Reflexive Primitive 6: Agent Procedural Self-Audit validator.

Mirrors the autoresearch_arch_map validator pattern but applied to
agent task discipline instead of code structure.

Usage:
    python scripts/public/validators/validate_agent_task_discipline.py pre <task_type>
        → prints required pre-checks for the task type
    python scripts/public/validators/validate_agent_task_discipline.py post <task_type> [--log <path>]
        → checks session log for incomplete post-checks
    python scripts/public/validators/validate_agent_task_discipline.py show
        → prints all task types and their requirements
    python scripts/public/validators/validate_agent_task_discipline.py audit
        → scans workspace/agent_session_log.jsonl for incomplete tasks

Exit codes:
    0 — all checks pass (or pre/show mode)
    1 — incomplete post-checks found
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DISCIPLINE_MAP = REPO / "docs" / "internal" / "agent_task_discipline_map.md"
DEFAULT_LOG = REPO / "workspace" / "agent_session_log.jsonl"

# ── Task type definitions (parsed from the map, but hardcoded here
#    for deterministic validation without markdown parsing) ──────────

TASK_TYPES = {
    "experiment_run": {
        "pre": [
            ("hypothesis_registered", "H-row in hypothesis ledger BEFORE run"),
            ("rubric_validated", "make validate-rubric passed"),
            ("substrate_sealed", "make seal passed or justification"),
            ("evidence_validated", "scripts/public/validators/validate_evidence.py passed"),
        ],
        "post": [
            ("e_row_written", "E-row in EXPERIMENT_TRACK_RECORD.md"),
            ("f_row_evaluated", "F-row written or explicit skip"),
            ("ins_row_evaluated", "INS-row if paper-grade or explicit skip"),
            ("thesis_updated", "best-iteration marker or null-result note"),
            ("workspace_frozen", "no post-hoc edits to workspace"),
        ],
    },
    "substrate_build": {
        "pre": [
            ("runbook_consulted", "experiment_cookbook.md read"),
            ("division_ab_separation", "GT-aware vs mutator-visible separated"),
        ],
        "post": [
            ("evidence_validated", "scripts/public/validators/validate_evidence.py passed"),
            ("rubric_validated", "scripts/public/validators/validate_rubric.py passed"),
            ("gate_harness_smoke", "gate_harness.py --run-smoke-test exit 0"),
            ("leak_sentinel", "make seal passed or leaks fixed"),
            ("triumvirate_aligned", "I_model signature consistent across files"),
            ("denylist_present", ".denylist file with domain terms"),
        ],
    },
    "paper_edit": {
        "pre": [
            ("ledger_read", "paper5_epistemic_ledger.md read"),
            ("invariants_checked", "§5 invariants reviewed"),
        ],
        "post": [
            ("ledger_updated", "epistemic ledger updated if structure changed"),
            ("both_formats", "both draft.md AND main.tex updated"),
            ("invariants_preserved", "no invariant violated"),
        ],
    },
    "seam_update": {
        "pre": [
            ("board_checked", "ZTARE_BOARD.md checked"),
            ("no_duplicate", "no existing seam covers same finding"),
        ],
        "post": [
            ("board_row", "row added/updated on ZTARE_BOARD.md"),
            ("visibility_correct", "open→private, closed→public"),
            ("debate_log", "at least one debate turn"),
        ],
    },
    "recording": {
        "pre": [
            ("source_verified", "claims verified against run artifacts"),
        ],
        "post": [
            ("track_record_updated", "E/F-row in EXPERIMENT_TRACK_RECORD.md"),
            ("public_board_current", "ZTARE_BOARD.md not stale"),
            ("memory_updated", "MEMORY.md updated if cross-session"),
        ],
    },
    "infrastructure": {
        "pre": [
            ("arch_map_read", "architectural map read for affected region"),
            ("no_parallel_conflict", "no other agent on same files"),
        ],
        "post": [
            ("arch_map_updated", "map updated if regions changed"),
            ("tests_pass", "existing tests still pass"),
            ("validate_arch_map", "validate_autoresearch_arch_map.py ex-post"),
        ],
    },
}


def cmd_show():
    """Print all task types and requirements."""
    for tt, checks in TASK_TYPES.items():
        print(f"\n{'='*60}")
        print(f"  {tt}")
        print(f"{'='*60}")
        print("  PRE-CHECKS:")
        for key, desc in checks["pre"]:
            print(f"    [ ] {key}: {desc}")
        print("  POST-CHECKS:")
        for key, desc in checks["post"]:
            print(f"    [ ] {key}: {desc}")


def cmd_pre(task_type: str):
    """Print pre-checks for a task type."""
    if task_type not in TASK_TYPES:
        print(f"Unknown task type: {task_type}")
        print(f"Valid types: {', '.join(TASK_TYPES)}")
        return 1
    checks = TASK_TYPES[task_type]
    print(f"PRE-CHECKS for {task_type}:")
    for key, desc in checks["pre"]:
        print(f"  [ ] {key}: {desc}")
    return 0


def cmd_post(task_type: str, log_path: Path | None = None):
    """Check post-checks for a task type against session log."""
    if task_type not in TASK_TYPES:
        print(f"Unknown task type: {task_type}")
        return 1

    checks = TASK_TYPES[task_type]
    required = {key: desc for key, desc in checks["post"]}

    # Try to read log
    completed = set()
    if log_path and log_path.exists():
        for line in log_path.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("task_type") == task_type:
                    for key, val in entry.get("post_checks", {}).items():
                        if val:
                            completed.add(key)
            except json.JSONDecodeError:
                continue

    # Report
    all_done = True
    print(f"POST-CHECKS for {task_type}:")
    for key, desc in required.items():
        done = key in completed
        mark = "✅" if done else "❌"
        if not done:
            all_done = False
        print(f"  {mark} {key}: {desc}")

    if all_done:
        print(f"\n  RESULT: ALL POST-CHECKS COMPLETE")
    else:
        missing = [k for k in required if k not in completed]
        print(f"\n  RESULT: {len(missing)} INCOMPLETE — {', '.join(missing)}")

    return 0 if all_done else 1


def cmd_audit(log_path: Path):
    """Scan session log for incomplete tasks."""
    if not log_path.exists():
        print(f"No session log at {log_path}")
        return 0

    incomplete = []
    for line in log_path.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("status") == "in_progress":
                incomplete.append(entry)
            elif entry.get("status") == "completed":
                tt = entry.get("task_type", "")
                if tt in TASK_TYPES:
                    post = entry.get("post_checks", {})
                    missing = [
                        k for k, _ in TASK_TYPES[tt]["post"]
                        if not post.get(k, False)
                    ]
                    if missing:
                        incomplete.append({**entry, "_missing": missing})
        except json.JSONDecodeError:
            continue

    if not incomplete:
        print("All logged tasks complete.")
        return 0

    print(f"{len(incomplete)} task(s) with incomplete checks:")
    for entry in incomplete:
        print(f"  {entry.get('task', '?')} ({entry.get('task_type', '?')})")
        if "_missing" in entry:
            print(f"    missing: {entry['_missing']}")
        elif entry.get("status") == "in_progress":
            print(f"    status: still in_progress")

    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent task discipline validator")
    parser.add_argument("command", choices=["pre", "post", "show", "audit"])
    parser.add_argument("task_type", nargs="?", default=None)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()

    if args.command == "show":
        cmd_show()
    elif args.command == "pre":
        if not args.task_type:
            print("Usage: validate_agent_task_discipline.py pre <task_type>")
            sys.exit(1)
        sys.exit(cmd_pre(args.task_type))
    elif args.command == "post":
        if not args.task_type:
            print("Usage: validate_agent_task_discipline.py post <task_type>")
            sys.exit(1)
        sys.exit(cmd_post(args.task_type, args.log))
    elif args.command == "audit":
        sys.exit(cmd_audit(args.log))
