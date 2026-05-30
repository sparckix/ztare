#!/usr/bin/env python3
"""Harvest zero-spend typed endpoint agent-panel results.

`typed_endpoint_agent_panel.py` creates read-only audit prompts. This companion
script records or harvests the structured JSON blocks returned by Codex agents,
updates the panel manifest, and emits a small decision metric:

  * >=3 useful results out of 5 -> promote the opt-in panel pattern,
  * 0-1 useful results out of 5 -> hold,
  * 2 useful results out of 5 -> ambiguous.

It deliberately does not call external LLM APIs or run Lean. Lean snippets are
saved as candidates for Codex review, not treated as verified proof.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
VALID_VERDICTS = {
    "compile_safe_projection",
    "missing_primitive",
    "no_useful_move",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_job_id(value: str) -> str:
    return value.strip().replace("/", "_")


def extract_fenced_json(text: str) -> dict[str, Any] | None:
    for match in re.finditer(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE):
        block = match.group(1).strip()
        if not block.startswith("{"):
            continue
        try:
            raw = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            return raw
    return None


def load_result(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return read_json(path)
    raw = path.read_text(encoding="utf-8")
    result = extract_fenced_json(raw)
    if result is None:
        raise ValueError(f"no fenced JSON block found in {path}")
    result["_source_markdown"] = str(path)
    return result


def validate_result(result: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
    target = str(result.get("target") or "").strip()
    verdict = str(result.get("verdict") or "").strip()
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f"invalid verdict {verdict!r}; expected one of {sorted(VALID_VERDICTS)}")
    useful = result.get("useful")
    if not isinstance(useful, bool):
        useful = verdict in {"compile_safe_projection", "missing_primitive"}
    normalized = {
        "target": target,
        "verdict": verdict,
        "useful": useful,
        "summary": str(result.get("summary") or "").strip(),
        "patch_kind": str(result.get("patch_kind") or "none").strip(),
        "insertion_point": str(result.get("insertion_point") or "").strip(),
        "lean_code": str(result.get("lean_code") or "").strip(),
        "missing_primitive": str(result.get("missing_primitive") or "").strip(),
        "downstream_adapter": str(result.get("downstream_adapter") or "").strip(),
        "references": [
            str(ref).strip() for ref in result.get("references", [])
            if str(ref).strip()
        ],
        "risk": str(result.get("risk") or "").strip(),
        "source_agent": str(result.get("source_agent") or "").strip(),
        "recorded_utc": str(result.get("recorded_utc") or utc_now()),
    }
    if job_id:
        normalized["job_id"] = normalize_job_id(job_id)
    elif result.get("job_id"):
        normalized["job_id"] = normalize_job_id(str(result["job_id"]))
    return normalized


def find_job(manifest: dict[str, Any], job_id: str | None, result: dict[str, Any]) -> dict[str, Any]:
    jobs = manifest.get("jobs") or []
    if job_id:
        normalized = normalize_job_id(job_id)
        for job in jobs:
            if job.get("job_id") == normalized:
                return job
        raise ValueError(f"job_id not in manifest: {normalized}")
    target = result.get("target")
    matches = [job for job in jobs if job.get("target") == target]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"no manifest job for target: {target!r}")
    raise ValueError(f"ambiguous manifest jobs for target: {target!r}")


def record_result(panel_dir: Path, args: argparse.Namespace) -> Path:
    manifest = read_json(panel_dir / "manifest.json")
    job = find_job(manifest, args.record_job, {"target": args.record_target})
    result = validate_result({
        "job_id": job["job_id"],
        "target": args.record_target or job.get("target"),
        "verdict": args.record_verdict,
        "useful": args.record_useful,
        "summary": args.record_summary,
        "patch_kind": args.record_patch_kind,
        "insertion_point": args.record_insertion_point,
        "lean_code": args.record_lean_code,
        "missing_primitive": args.record_missing_primitive,
        "downstream_adapter": args.record_downstream_adapter,
        "references": args.record_reference or [],
        "risk": args.record_risk,
        "source_agent": args.record_source_agent,
    }, job_id=job["job_id"])
    result_path = panel_dir / "results" / f"{job['job_id']}.json"
    write_json(result_path, result)
    return result_path


def collect_results(panel_dir: Path, results_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not results_dir.exists():
        return []
    paths = sorted(
        p for p in results_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".markdown"}
    )
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        loaded.append((path, validate_result(load_result(path))))
    return loaded


def decision_label(completed: int, useful: int) -> str:
    if completed == 0:
        return "not_tested"
    if useful >= 3 and completed >= 5:
        return "promote_opt_in_panel"
    if useful <= 1 and completed >= 5:
        return "hold"
    if useful == 2 and completed >= 5:
        return "ambiguous"
    if useful >= 3:
        return "provisionally_promote"
    return "insufficient_n"


def harvest(panel_dir: Path, results_dir: Path) -> dict[str, Any]:
    manifest_path = panel_dir / "manifest.json"
    manifest = read_json(manifest_path)
    result_records = collect_results(panel_dir, results_dir)
    snippet_dir = panel_dir / "candidate_snippets"
    snippet_dir.mkdir(parents=True, exist_ok=True)

    jobs_by_id = {job["job_id"]: job for job in manifest.get("jobs", [])}
    for result_path, result in result_records:
        job = find_job(manifest, result.get("job_id"), result)
        job_id = job["job_id"]
        result["job_id"] = job_id
        job.update({
            "status": "completed",
            "agent_verdict": result["verdict"],
            "useful": result["useful"],
            "patch_kind": result["patch_kind"],
            "result_summary": result["summary"],
            "missing_primitive": result["missing_primitive"],
            "risk": result["risk"],
            "result_path": str(result_path.relative_to(REPO)),
        })
        if result["lean_code"]:
            snippet_path = snippet_dir / f"{job_id}.lean"
            snippet_path.write_text(result["lean_code"] + "\n", encoding="utf-8")
            job["lean_snippet_path"] = str(snippet_path.relative_to(REPO))
        jobs_by_id[job_id] = job

    completed_jobs = [
        job for job in manifest.get("jobs", [])
        if job.get("status") == "completed"
    ]
    useful_jobs = [job for job in completed_jobs if job.get("useful")]
    verdict_counts = Counter(str(job.get("agent_verdict") or "") for job in completed_jobs)
    patch_kind_counts = Counter(str(job.get("patch_kind") or "") for job in completed_jobs)
    metrics = {
        "panel_slug": manifest.get("panel_slug"),
        "harvested_utc": utc_now(),
        "n_jobs": len(manifest.get("jobs", [])),
        "n_completed": len(completed_jobs),
        "n_useful": len(useful_jobs),
        "useful_rate": (len(useful_jobs) / len(completed_jobs)) if completed_jobs else 0.0,
        "verdict_counts": dict(verdict_counts),
        "patch_kind_counts": dict(patch_kind_counts),
        "decision": decision_label(len(completed_jobs), len(useful_jobs)),
        "results_dir": str(results_dir.relative_to(REPO)) if results_dir.is_relative_to(REPO) else str(results_dir),
    }
    manifest["last_harvest_utc"] = metrics["harvested_utc"]
    manifest["metrics_path"] = str((panel_dir / "metrics.json").relative_to(REPO))
    write_json(manifest_path, manifest)
    write_json(panel_dir / "metrics.json", metrics)
    write_summary(panel_dir, manifest, metrics)
    return metrics


def write_summary(panel_dir: Path, manifest: dict[str, Any], metrics: dict[str, Any]) -> None:
    lines = [
        "# Typed Endpoint Agent Panel Summary",
        "",
        f"- Panel: `{manifest.get('panel_slug')}`",
        f"- Jobs completed: {metrics['n_completed']} / {metrics['n_jobs']}",
        f"- Useful results: {metrics['n_useful']} ({metrics['useful_rate']:.0%})",
        f"- Decision: `{metrics['decision']}`",
        "",
        "## Results",
        "",
    ]
    for job in manifest.get("jobs", []):
        status = job.get("status", "not_started")
        lines.extend([
            f"### `{job.get('job_id')}`",
            "",
            f"- Status: `{status}`",
            f"- Verdict: `{job.get('agent_verdict', '')}`",
            f"- Useful: `{job.get('useful', '')}`",
            f"- Summary: {job.get('result_summary', '')}",
            f"- Missing primitive: `{job.get('missing_primitive', '')}`",
            f"- Risk: {job.get('risk', '')}",
            "",
        ])
    (panel_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Record and harvest zero-spend typed endpoint agent-panel results")
    ap.add_argument("--panel-dir", type=Path, required=True)
    ap.add_argument("--results-dir", type=Path)
    ap.add_argument("--record-job", help="manifest job_id to record")
    ap.add_argument("--record-target", help="target name when recording without job_id")
    ap.add_argument("--record-verdict", choices=sorted(VALID_VERDICTS))
    ap.add_argument("--record-useful", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--record-summary", default="")
    ap.add_argument("--record-patch-kind", default="none")
    ap.add_argument("--record-insertion-point", default="")
    ap.add_argument("--record-lean-code", default="")
    ap.add_argument("--record-missing-primitive", default="")
    ap.add_argument("--record-downstream-adapter", default="")
    ap.add_argument("--record-reference", action="append", default=[])
    ap.add_argument("--record-risk", default="")
    ap.add_argument("--record-source-agent", default="")
    args = ap.parse_args()

    panel_dir = args.panel_dir.resolve()
    results_dir = (args.results_dir.resolve() if args.results_dir
                   else panel_dir / "results")
    if args.record_job or args.record_target:
        if not args.record_verdict:
            raise SystemExit("--record-verdict is required when recording a result")
        result_path = record_result(panel_dir, args)
        print(f"recorded: {result_path.relative_to(REPO)}")
    metrics = harvest(panel_dir, results_dir)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
