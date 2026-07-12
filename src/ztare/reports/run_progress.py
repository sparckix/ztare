"""Live run progress from telemetry + durable Workbench jobs — file-based, not process-grepping.

The autoresearch loop appends to `iteration_telemetry.jsonl` as it runs (run_start → iteration ×N →
run_end). Reading that file tells us, reliably and without scanning processes, whether a run is in
flight and which iteration it's on. A Workbench job is the liveness fallback while telemetry is quiet
or before the first run record exists. The workbench shells out to `ztare autoresearch run-progress`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ACTIVE_WINDOW_SECONDS = 180  # last telemetry write within this ⇒ a run is in flight


def build_run_progress(project: str, repo_root: Path) -> dict[str, Any]:
    tel = repo_root / "projects" / project / "workspace" / "iteration_telemetry.jsonl"
    # Telemetry is the rich progress source, but a model/committee call can be
    # quiet longer than ACTIVE_WINDOW_SECONDS. The durable Workbench job is the
    # liveness source in that interval (and also covers the queued-before-start
    # window), so a long run never disappears just because it is thinking.
    active_job: dict[str, Any] | None = None
    try:
        from ztare.workspace.jobs import list_jobs

        rows = list_jobs(repo_root / ".workbench" / "jobs", project=project, limit=20)
        active_job = next(
            (
                row for row in rows
                if row.get("kind") == "autoresearch_run"
                and row.get("status") in {"queued", "running"}
            ),
            None,
        )
    except Exception:
        # Direct CLI runs do not have a Workbench job; telemetry remains the
        # authoritative fallback and this read surface must never fail closed.
        active_job = None

    base = {
        "ok": True,
        "schema": "ztare-run-progress-v1",
        "project": project,
        "active": bool(active_job),
        "has_telemetry": False,
        "progress_source": "job" if active_job else "none",
        "job_id": active_job.get("id") if active_job else None,
        "job_status": active_job.get("status") if active_job else None,
        "job_created_at": active_job.get("created_at") if active_job else None,
        "job_started_at": active_job.get("started_at") if active_job else None,
        "last_update_age_seconds": None,
        "heartbeat_stale": False,
    }
    if not tel.exists():
        return base
    records: list[dict[str, Any]] = []
    for line in tel.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    if not records:
        return base

    last = records[-1]
    run_id = last.get("run_id")
    run_recs = [r for r in records if r.get("run_id") == run_id]
    start = next((r for r in run_recs if r.get("record_type") == "run_start"), {})
    iters = [r for r in run_recs if r.get("record_type") == "iteration"]
    finished = last.get("record_type") == "run_end"
    try:
        age = int(time.time() - tel.stat().st_mtime)
    except Exception:
        age = 10 ** 9
    telemetry_active = (not finished) and age < ACTIVE_WINDOW_SECONDS
    active = bool(active_job) or telemetry_active

    def _num(v: Any) -> Any:
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    cur_iter = max((r.get("iteration_index") or 0 for r in iters), default=0)
    latest_score = _num(iters[-1].get("score")) if iters else None
    return {
        "ok": True,
        "schema": "ztare-run-progress-v1",
        "project": project,
        "has_telemetry": True,
        "active": active,
        "finished": finished,
        "run_id": run_id,
        "iteration": cur_iter,
        "iteration_budget": start.get("iteration_budget"),
        "iteration_count": len(iters),
        "latest_score": latest_score,
        "mutator_model": start.get("mutator_model"),
        "judge_model": start.get("judge_model"),
        "rubric": start.get("rubric"),
        "run_mode": start.get("run_mode") or last.get("run_mode"),
        "last_update_age_seconds": age,
        # A previous run may have a terminal run_end while a newly queued job is
        # still before its run_start. That is waiting, not a stale heartbeat.
        "heartbeat_stale": bool(active_job and not telemetry_active and not finished),
        "progress_source": "job+telemetry" if active_job and telemetry_active else ("job" if active_job else "telemetry"),
        "job_id": active_job.get("id") if active_job else None,
        "job_status": active_job.get("status") if active_job else None,
        "job_created_at": active_job.get("created_at") if active_job else None,
        "job_started_at": active_job.get("started_at") if active_job else None,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare autoresearch run-progress")
    parser.add_argument("--project", required=True, help="Project slug.")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default and only format).")
    args = parser.parse_args(argv)
    print(json.dumps(build_run_progress(args.project, _repo_root()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
