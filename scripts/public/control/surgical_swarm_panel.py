#!/usr/bin/env python3
"""Run a bounded multi-job typed-endpoint swarm panel.

This is a thin orchestration layer over `batched_candidate_generator.py`.
It is deliberately outside `autoresearch_loop`: the Research Director uses it
to fan out across independent closure endpoints, then promotes only compiled,
non-self-referential patches or concrete missing primitives.

The important distinction from a single batched candidate run:

* batched_candidate_generator = one endpoint, K candidates, one model call
* surgical_swarm_panel = many independent endpoint jobs, each with its own
  patch class and candidate batch, under one total budget gate

Default behavior is budget-estimate only.  Paid dispatch requires
`--allow-paid`, a `--max-total-cost-usd` cap, and a configured provider key.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import concurrent.futures
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
RUN_ROOT = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "swarm_panels"
)
BATCHED = REPO / "scripts" / "batched_candidate_generator.py"


@dataclass(frozen=True)
class SwarmJob:
    name: str
    target: str
    field: str
    patch_class: str
    k: int = 3
    require_source_witness: bool = False


NS_TRACKB_10X_PILOT = [
    SwarmJob(
        name="amplitude_observable_source_constructor",
        target="TrackBProfileLipschitzControlObligation",
        field="generated_quartic_survival_amplitude_observable_source",
        patch_class="source_provenance_bridge",
        k=3,
    ),
    SwarmJob(
        name="gp216_branch_self_tax_threshold",
        target="GP216BridgeCompositionReceipt",
        field="branchSelfTaxThresholdCoordinateIdentities",
        patch_class="source_provenance_bridge",
        k=3,
    ),
    SwarmJob(
        name="flat_torus_reserve_source",
        target="GP216BridgeCompositionReceipt",
        field="lowHighReservePDESource",
        patch_class="instance_with_evidence",
        k=2,
    ),
]


def load_jobs(path: Path | None, preset: str) -> list[SwarmJob]:
    if path is None:
        if preset != "ns-trackb-10x-pilot":
            raise SystemExit(f"unknown preset: {preset}")
        return NS_TRACKB_10X_PILOT
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("jobs JSON must be a list")
    return [SwarmJob(**item) for item in raw]


def read_budget(path: Path) -> float:
    data = json.loads(path.read_text(encoding="utf-8"))
    return float(data["estimate"]["estimated_cost_usd"])


def run_cmd(cmd: list[str], *, cwd: Path = REPO) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout


def run_job_paid(
    job: SwarmJob,
    *,
    model: str,
    out_dir: Path,
    max_total_cost_usd: float | None,
) -> dict[str, Any]:
    cmd = base_job_cmd(
        job,
        model=model,
        out_dir=out_dir,
        max_total_cost_usd=max_total_cost_usd,
    )
    cmd.append("--allow-paid")
    rc, output = run_cmd(cmd)
    (out_dir / f"{job.name}_run.stdout").write_text(
        output,
        encoding="utf-8",
    )
    summary = summarize_result(job_result_path(out_dir, job))
    summary.update({"job": asdict(job), "returncode": rc})
    return summary


def job_budget_path(out_dir: Path, job: SwarmJob) -> Path:
    return out_dir / f"{job.target}_{job.field}_{job.patch_class}_budget.json"


def job_result_path(out_dir: Path, job: SwarmJob) -> Path:
    return out_dir / f"{job.target}_{job.field}_{job.patch_class}.json"


def base_job_cmd(
    job: SwarmJob,
    *,
    model: str,
    out_dir: Path,
    max_total_cost_usd: float | None,
) -> list[str]:
    cmd = [
        sys.executable,
        str(BATCHED),
        "--target", job.target,
        "--field", job.field,
        "--patch-class", job.patch_class,
        "--k", str(job.k),
        "--model", model,
        "--session-id", f"swarm-{out_dir.name}-{job.name}",
        "--out-dir", str(out_dir),
    ]
    if max_total_cost_usd is not None:
        cmd.extend(["--max-total-cost-usd", str(max_total_cost_usd)])
    if job.require_source_witness:
        cmd.append("--require-source-witness")
    return cmd


def summarize_result(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "n_verified": 0, "degenerate": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("results", [])
    return {
        "exists": True,
        "n_blocks": data.get("n_blocks", 0),
        "n_verified": data.get("n_verified", 0),
        "degenerate": sum(1 for r in results if r.get("degenerate")),
        "degenerate_reasons": sorted({
            r.get("degenerate_reason")
            for r in results
            if r.get("degenerate_reason")
        }),
        "compiled_raw": sum(1 for r in results if r.get("exit_code") == 0),
        "lean_paths": [
            r.get("lean_path")
            for r in results
            if r.get("compiled") and r.get("lean_path")
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="ns-trackb-10x-pilot")
    ap.add_argument("--jobs-json", type=Path)
    ap.add_argument("--model", default="gemini-pro")
    ap.add_argument("--parallel-jobs", type=int, default=1,
                    help="number of endpoint jobs to run concurrently after budget gating")
    ap.add_argument("--allow-paid", action="store_true")
    ap.add_argument("--budget-estimate-only", action="store_true")
    ap.add_argument("--max-total-cost-usd", type=float)
    ap.add_argument("--run-id",
                    default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = ap.parse_args()

    jobs = load_jobs(args.jobs_json, args.preset)
    out_dir = RUN_ROOT / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "preset": args.preset,
        "model": args.model,
        "allow_paid": args.allow_paid,
        "max_total_cost_usd": args.max_total_cost_usd,
        "jobs": [asdict(j) for j in jobs],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"=== surgical swarm panel ===")
    print(f"  jobs: {len(jobs)}")
    print(f"  model: {args.model}")
    print(f"  out: {out_dir}")

    estimates: list[dict[str, Any]] = []
    total_est = 0.0
    for job in jobs:
        cmd = base_job_cmd(
            job,
            model=args.model,
            out_dir=out_dir,
            max_total_cost_usd=args.max_total_cost_usd,
        )
        cmd.append("--budget-estimate-only")
        rc, output = run_cmd(cmd)
        (out_dir / f"{job.name}_estimate.stdout").write_text(
            output,
            encoding="utf-8",
        )
        if rc != 0:
            print(f"  estimate failed: {job.name} rc={rc}")
            print(output[-800:])
            return rc
        cost = read_budget(job_budget_path(out_dir, job))
        total_est += cost
        estimates.append({"job": asdict(job), "estimated_cost_usd": cost})
        print(f"  estimate {job.name}: ${cost:.4f}")

    estimate_report = {
        "total_estimated_cost_usd": total_est,
        "max_total_cost_usd": args.max_total_cost_usd,
        "estimates": estimates,
    }
    (out_dir / "budget_estimate.json").write_text(
        json.dumps(estimate_report, indent=2),
        encoding="utf-8",
    )
    print(f"  total estimate: ${total_est:.4f}")

    if args.max_total_cost_usd is not None and total_est > args.max_total_cost_usd:
        print(
            f"  blocked: estimate ${total_est:.4f} exceeds cap "
            f"${args.max_total_cost_usd:.4f}"
        )
        return 2
    if args.budget_estimate_only or not args.allow_paid:
        print("  estimate-only; skipping paid dispatch")
        return 0

    results: list[dict[str, Any]] = []
    max_workers = max(1, min(args.parallel_jobs, len(jobs)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_job = {
            pool.submit(
                run_job_paid,
                job,
                model=args.model,
                out_dir=out_dir,
                max_total_cost_usd=args.max_total_cost_usd,
            ): job
            for job in jobs
        }
        for future in concurrent.futures.as_completed(future_to_job):
            job = future_to_job[future]
            try:
                summary = future.result()
            except Exception as exc:  # noqa: BLE001
                summary = {
                    "job": asdict(job),
                    "returncode": 99,
                    "n_verified": 0,
                    "degenerate": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            results.append(summary)
            print(
                f"  run {job.name}: rc={summary.get('returncode')} "
                f"verified={summary.get('n_verified')} "
                f"degenerate={summary.get('degenerate')}"
            )

    final = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "total_estimated_cost_usd": total_est,
        "jobs": results,
        "useful_jobs": sum(1 for r in results if r.get("n_verified", 0) > 0),
        "raw_compiling_jobs": sum(1 for r in results if r.get("compiled_raw", 0) > 0),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(final, indent=2),
        encoding="utf-8",
    )
    print(f"  summary: {out_dir / 'summary.json'}")
    return 0 if final["useful_jobs"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
