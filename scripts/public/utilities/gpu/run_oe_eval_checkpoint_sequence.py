#!/usr/bin/env python3
"""Run oe-eval checkpoint command sheets with restart markers.

This wrapper treats a generated oe-eval command sheet as a sequence of
checkpoint jobs. A job is complete only after the oe-eval process exits 0 and a
`.ztare_done.json` marker is written inside that job's output directory.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STEP_RE = re.compile(r"step_(\d+)$")


@dataclass(frozen=True)
class Job:
    name: str
    step: int
    argv: list[str]
    output_dir: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_jobs(command_sheet: Path) -> list[Job]:
    jobs: list[Job] = []
    current_name: str | None = None
    for raw_line in command_sheet.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            candidate = line[2:].strip()
            if candidate.startswith("official_"):
                current_name = candidate
            continue
        if not line.startswith("oe-eval "):
            continue
        if not current_name:
            raise ValueError(f"Command without preceding checkpoint name: {line[:120]}")
        argv = shlex.split(line)
        try:
            out_i = argv.index("--output-dir") + 1
            output_dir = Path(argv[out_i])
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Missing --output-dir for {current_name}") from exc
        match = STEP_RE.search(current_name)
        if not match:
            raise ValueError(f"Cannot parse step from checkpoint name: {current_name}")
        jobs.append(Job(name=current_name, step=int(match.group(1)), argv=argv, output_dir=output_dir))
        current_name = None
    if not jobs:
        raise ValueError(f"No oe-eval jobs found in {command_sheet}")
    return jobs


def append_status(status_path: Path, row: dict) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with status_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def has_contents(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def prepare_output_dir(job: Job, partial_policy: str) -> None:
    marker = job.output_dir / ".ztare_done.json"
    if marker.exists():
        return
    if not has_contents(job.output_dir):
        job.output_dir.mkdir(parents=True, exist_ok=True)
        return
    if partial_policy == "fail":
        raise RuntimeError(
            f"{job.output_dir} has partial contents and no .ztare_done.json; "
            "rerun with --partial-policy archive or skip"
        )
    if partial_policy == "skip":
        return
    if partial_policy == "archive":
        archived = job.output_dir.with_name(f"{job.output_dir.name}.partial_{utc_now().replace(':', '').replace('-', '')}")
        shutil.move(str(job.output_dir), str(archived))
        job.output_dir.mkdir(parents=True, exist_ok=True)
        return
    raise ValueError(f"Unknown partial policy: {partial_policy}")


def run_job(job: Job, logs_dir: Path, status_path: Path, dry_run: bool, partial_policy: str) -> int:
    marker = job.output_dir / ".ztare_done.json"
    if marker.exists():
        append_status(status_path, {"ts": utc_now(), "event": "skip_done", "job": job.name, "step": job.step})
        return 0

    prepare_output_dir(job, partial_policy)
    if partial_policy == "skip" and has_contents(job.output_dir) and not marker.exists():
        append_status(status_path, {"ts": utc_now(), "event": "skip_partial", "job": job.name, "step": job.step})
        return 0

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{job.name}.log"
    append_status(status_path, {"ts": utc_now(), "event": "start", "job": job.name, "step": job.step, "output_dir": str(job.output_dir)})
    if dry_run:
        append_status(status_path, {"ts": utc_now(), "event": "dry_run", "job": job.name, "argv": job.argv})
        return 0

    with log_path.open("ab") as log_fh:
        log_fh.write(f"[ztare] start {utc_now()} {job.name}\n".encode("utf-8"))
        proc = subprocess.run(job.argv, stdout=log_fh, stderr=subprocess.STDOUT, check=False)
        log_fh.write(f"[ztare] exit {utc_now()} {job.name} code={proc.returncode}\n".encode("utf-8"))

    if proc.returncode != 0:
        append_status(status_path, {"ts": utc_now(), "event": "fail", "job": job.name, "step": job.step, "returncode": proc.returncode, "log": str(log_path)})
        return proc.returncode

    marker.write_text(
        json.dumps(
            {"job": job.name, "step": job.step, "completed_at": utc_now(), "log": str(log_path)},
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    append_status(status_path, {"ts": utc_now(), "event": "done", "job": job.name, "step": job.step, "log": str(log_path), "marker": str(marker)})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-sheet", required=True, type=Path)
    parser.add_argument("--from-step", type=int)
    parser.add_argument("--to-step", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--logs-dir", type=Path, default=Path("oe_eval_checkpoint_logs"))
    parser.add_argument("--status-path", type=Path, default=Path("oe_eval_checkpoint_status.jsonl"))
    parser.add_argument("--partial-policy", choices=["fail", "archive", "skip"], default="fail")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    jobs = parse_jobs(args.command_sheet)
    if args.from_step is not None:
        jobs = [j for j in jobs if j.step >= args.from_step]
    if args.to_step is not None:
        jobs = [j for j in jobs if j.step <= args.to_step]
    if args.limit is not None:
        jobs = jobs[: args.limit]

    append_status(args.status_path, {"ts": utc_now(), "event": "sequence_start", "jobs": [j.name for j in jobs], "dry_run": args.dry_run})
    for job in jobs:
        code = run_job(job, args.logs_dir, args.status_path, args.dry_run, args.partial_policy)
        if code != 0:
            append_status(args.status_path, {"ts": utc_now(), "event": "sequence_stop", "failed_job": job.name, "returncode": code})
            return code
    append_status(args.status_path, {"ts": utc_now(), "event": "sequence_done", "jobs": [j.name for j in jobs]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
