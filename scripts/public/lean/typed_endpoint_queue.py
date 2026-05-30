#!/usr/bin/env python3
"""GP-224 Option B scaffold — typed-endpoint pack work queue (opt-in).

**Status:** scaffold-only. NOT the default execution path. The seam at
``research_areas/private/seams/engine/GP-224_ns_closure_swarm_decision_seam.md``
documented the empirical tripwires under which Option B becomes
load-bearing (≥50 typed endpoint events accumulated AND ≥10 are
scheduler-bound, not generation-bound). Today's empirical data has 9
events concentrated on a single family + single patch class — we are
not yet throughput-bound. This queue exists so the infrastructure is
ready when evidence tips, NOT to flip the default path today.

**What this queue does:**
  - ``--enqueue --target X --field Y --patch-class Z``: append one
    job to ``analytics/public/queues/typed_endpoint_pending.jsonl``
    instead of executing immediately
  - ``--worker``: drain pending jobs one at a time through the
    existing ``typed_endpoint_pack`` flow; persist results to
    ``analytics/public/queues/typed_endpoint_completed.jsonl``
  - ``--list``: print pending + completed counts
  - ``--clear-pending``: drop the pending queue (manual reset)

**What this queue intentionally does NOT do:**
  - Spin up multiple workers. Single-worker today. Multi-worker is a
    flag flip away (``--n-workers N``) but stays at 1 until the
    seam's tripwires fire.
  - Bypass any of typed_endpoint_pack's existing gates (SymPy
    dimensional, no-new-axiom audit, etc.). Each job runs through the
    same pipeline as the manual invocation.
  - Make swarm-level architectural changes. This is a scheduling
    layer, not a swarm controller.

**Honest scope (re GP-224 + 2026-05-06 cold-LLM debate):**
The cold LLM argued the bottleneck has flipped from PDE-identification
to throughput. Today's failure log refutes that: 9 events / 28 days,
8/9 on TrackBProfileLipschitz* family, 5/9 llm_refused. Those are not
throughput failures; they are generation-quality failures. Multiplying
schedule capacity won't fix llm_refused. **However**, the cold LLM has
one legitimate point: a queue enables breadth-of-attack across the 6
remaining source constructors without the operator having to manually
re-target each round. This scaffold makes that breadth available
opt-in.

When the seam's tripwires fire (≥50 events; ≥10 scheduler-bound),
promote this from opt-in to default by editing the typed_endpoint_pack
mainline flow. Until then: opt-in only.

Usage:
    # Enqueue 5 jobs across distinct constructors (operator-batched)
    python scripts/public/lean/typed_endpoint_queue.py --enqueue \\
        --target TrackBProfileLipschitzClayObligation --field continuation \\
        --patch-class instance_with_evidence
    python scripts/public/lean/typed_endpoint_queue.py --enqueue \\
        --target FlatTorusKillingModePDEAdapter \\
        --field positive_deformation_charged_by_reserve_loss \\
        --patch-class instance_with_evidence
    # ... etc

    # Drain
    python scripts/public/lean/typed_endpoint_queue.py --worker

    # Status
    python scripts/public/lean/typed_endpoint_queue.py --list
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
QUEUE_DIR = REPO / "analytics" / "queues"
PENDING_PATH = QUEUE_DIR / "typed_endpoint_pending.jsonl"
COMPLETED_PATH = QUEUE_DIR / "typed_endpoint_completed.jsonl"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def cmd_enqueue(args) -> int:
    if not args.target or not args.field:
        print("ERROR: --enqueue requires --target and --field")
        return 1
    job = {
        "job_id": f"job-{utc_iso()}",
        "ts_enqueued": utc_iso(),
        "target": args.target,
        "field": args.field,
        "patch_class": args.patch_class,
        "max_revisions": args.max_revisions,
        "status": "pending",
    }
    append_jsonl(PENDING_PATH, job)
    print(f"  enqueued {job['job_id']}: {args.target}::{args.field} ({args.patch_class})")
    pending = read_jsonl(PENDING_PATH)
    print(f"  pending now: {len(pending)}")
    return 0


def cmd_list(args) -> int:
    pending = read_jsonl(PENDING_PATH)
    completed = read_jsonl(COMPLETED_PATH)
    print(f"=== typed endpoint queue ===")
    print(f"  pending:   {len(pending)}")
    print(f"  completed: {len(completed)}")
    if pending:
        print()
        print("  next 5 pending:")
        for j in pending[:5]:
            print(
                f"    {j['job_id']}  {j['target']}::{j['field']}  ({j['patch_class']})"
            )
    if completed:
        recent = completed[-5:]
        print()
        print("  last 5 completed:")
        for j in recent:
            verdict = j.get("verdict", "?")
            print(
                f"    {j.get('job_id', '?')}  verdict={verdict}  "
                f"{j['target']}::{j['field']}"
            )
    return 0


def cmd_clear_pending(args) -> int:
    pending = read_jsonl(PENDING_PATH)
    if not pending:
        print("  pending queue already empty")
        return 0
    if not args.yes:
        print(f"  WOULD drop {len(pending)} pending jobs (rerun with --yes to confirm)")
        return 0
    write_jsonl(PENDING_PATH, [])
    print(f"  dropped {len(pending)} pending jobs")
    return 0


def cmd_worker(args) -> int:
    pending = read_jsonl(PENDING_PATH)
    if not pending:
        print("  pending queue empty; nothing to do")
        return 0

    # SAFETY: at most one job per worker invocation by default. The
    # rationale (GP-224): we are not in a throughput-bound regime today.
    # Running the queue means giving the operator breadth-of-attack via
    # batched invocation, NOT autonomous burn-down.
    n_to_run = min(args.max_jobs, len(pending))
    print(f"=== typed endpoint queue worker ===")
    print(f"  pending: {len(pending)};  running: {n_to_run}")

    completed_results = []
    for i in range(n_to_run):
        job = pending[i]
        print(
            f"\n  [{i + 1}/{n_to_run}] dispatching {job['job_id']}: "
            f"{job['target']}::{job['field']} ({job['patch_class']})"
        )
        cmd = [
            sys.executable,
            str(REPO / "scripts" / "typed_endpoint_pack.py"),
            "--target", job["target"],
            "--field", job["field"],
            "--patch-class", job["patch_class"],
            "--max-revisions", str(job.get("max_revisions", 2)),
            "--session-id", args.session_id,
            "--role-id", args.role_id,
        ]
        if args.allow_paid:
            cmd.append("--allow-paid")
        if args.budget_estimate_only:
            cmd.append("--budget-estimate-only")
        if args.max_total_cost_usd is not None:
            cmd.extend(["--max-total-cost-usd", str(args.max_total_cost_usd)])
        if args.write_approval_gate:
            cmd.append("--write-approval-gate")
        ts_started = utc_iso()
        try:
            result = subprocess.run(
                cmd,
                cwd=REPO,
                capture_output=True,
                text=True,
                timeout=args.per_job_timeout_seconds,
            )
            stdout_tail = result.stdout[-2000:] if result.stdout else ""
            stderr_tail = result.stderr[-1000:] if result.stderr else ""
            verdict = "completed" if result.returncode == 0 else f"exit_{result.returncode}"
        except subprocess.TimeoutExpired:
            stdout_tail = ""
            stderr_tail = "TimeoutExpired"
            verdict = "timeout"
        except Exception as exc:  # noqa: BLE001
            stdout_tail = ""
            stderr_tail = f"{type(exc).__name__}: {exc}"
            verdict = "error"

        completed_record = {
            **job,
            "ts_started": ts_started,
            "ts_completed": utc_iso(),
            "verdict": verdict,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
        completed_results.append(completed_record)
        append_jsonl(COMPLETED_PATH, completed_record)
        print(f"     verdict: {verdict}")

    # Remove the just-completed jobs from pending
    remaining = pending[n_to_run:]
    write_jsonl(PENDING_PATH, remaining)
    print(f"\n  drained {n_to_run} job(s); {len(remaining)} pending remain")

    n_completed_ok = sum(1 for r in completed_results if r["verdict"] == "completed")
    print(f"  this batch: {n_completed_ok}/{n_to_run} completed cleanly")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="GP-224 Option B scaffold — typed-endpoint pack work queue"
    )
    ap.add_argument("--enqueue", action="store_true",
                    help="add a job to the pending queue")
    ap.add_argument("--worker", action="store_true",
                    help="drain pending jobs one at a time")
    ap.add_argument("--list", action="store_true",
                    help="show pending + completed counts")
    ap.add_argument("--clear-pending", action="store_true",
                    help="drop the pending queue (requires --yes)")
    ap.add_argument("--yes", action="store_true",
                    help="confirm a destructive action (e.g. clear-pending)")

    # Job fields (used with --enqueue)
    ap.add_argument("--target", help="workmap target name")
    ap.add_argument("--field", help="field of the target to discharge")
    ap.add_argument("--patch-class",
                    default="instance_with_evidence",
                    choices=[
                        "transitivity_adapter",
                        "branch_wise_falsifier",
                        "source_provenance_bridge",
                        "instance_with_evidence",
                    ])
    ap.add_argument("--max-revisions", type=int, default=2)

    # Worker controls (kept tight today; loosen when seam tripwires fire)
    ap.add_argument("--max-jobs", type=int, default=1,
                    help="max jobs to run per worker invocation (default 1)")
    ap.add_argument("--per-job-timeout-seconds", type=int, default=900,
                    help="hard timeout per typed_endpoint_pack invocation")
    ap.add_argument("--allow-paid", action="store_true",
                    help="authorize typed_endpoint_pack paid LLM calls")
    ap.add_argument("--budget-estimate-only", action="store_true",
                    help="drain jobs through prompt/budget construction only; no paid LLM call")
    ap.add_argument("--max-total-cost-usd", type=float,
                    help="hard per-worker spend cap passed to typed_endpoint_pack")
    ap.add_argument("--role-id", default="research_director",
                    help="role budget to enforce via spend_tracker")
    ap.add_argument("--session-id",
                    default=f"typed-endpoint-queue-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                    help="spend-tracker session id")
    ap.add_argument("--write-approval-gate", action="store_true",
                    help="write pending org approval gates instead of calling paid LLMs")

    args = ap.parse_args()
    n_modes = sum(
        1 for x in (args.enqueue, args.worker, args.list, args.clear_pending) if x
    )
    if n_modes == 0:
        ap.print_help()
        return 1
    if n_modes > 1:
        print("ERROR: pass exactly one of --enqueue / --worker / --list / --clear-pending")
        return 1

    if args.enqueue:
        return cmd_enqueue(args)
    if args.worker:
        return cmd_worker(args)
    if args.list:
        return cmd_list(args)
    if args.clear_pending:
        return cmd_clear_pending(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
