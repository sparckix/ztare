from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

from ztare.common.cegis_membrane import assess_cegis_membrane


SCHEMA = "ztare-arc3-run-observability-v1"


def build_arc3_run_observability(
    project: str | Path,
    *,
    top_candidates: int = 3,
    candidate_timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Join ARC run receipts into one RCA-oriented read model.

    This is observability only. It does not promote candidates, mutate memory,
    or decide gates. Its main job is to make stale-memory and cognitive-parity
    failures visible without manually grepping several ledgers.
    """

    project = _resolve_project_path(project)
    ws = project / "workspace"
    latest_eval = _read_json(project / "latest_eval_results.json")
    latest_gaps = _read_json(ws / "latest_evidence_gaps.json")
    p0 = _read_json(ws / "p0_metrics.json")
    abduced = _read_json(ws / "abduced_core.json")
    transfer = _read_json(ws / "latest_level_transfer_probe.json")
    play = _read_json(ws / "arc3_play_loop_report.json")
    telemetry = _read_jsonl(ws / "iteration_telemetry.jsonl")
    last_run = _latest_run_records(telemetry)
    candidate_rows = _candidate_memory_top_rows(ws / "candidate_memory.json", top_candidates)
    current_candidate_status = [
        _revalidate_candidate_row(
            project,
            row,
            timeout_seconds=candidate_timeout_seconds,
        )
        for row in candidate_rows
    ]
    workbenches = _visible_workbench_summaries(project)
    return {
        "schema": SCHEMA,
        "project": str(project),
        "written_at_unix": time.time(),
        "source_refs": _existing_refs(
            project,
            [
                "latest_eval_results.json",
                "workspace/latest_evidence_gaps.json",
                "workspace/p0_metrics.json",
                "workspace/abduced_core.json",
                "workspace/latest_level_transfer_probe.json",
                "workspace/arc3_play_loop_report.json",
                "workspace/candidate_memory.json",
                "workspace/iteration_telemetry.jsonl",
            ],
        ),
        "latest_run": _latest_run_summary(last_run),
        "latest_eval": _latest_eval_summary(latest_eval),
        "abduction": _abduction_summary(abduced),
        "transfer": _transfer_summary(transfer),
        "play": _play_summary(play),
        "p0": _p0_summary(p0),
        "candidate_memory_current_contract": current_candidate_status,
        "stale_memory_alerts": _stale_memory_alerts(current_candidate_status),
        "cegis_membrane": _cegis_membrane_summary(project, current_candidate_status),
        "visible_workbenches": workbenches,
        "cognitive_parity": _cognitive_parity_summary(workbenches, latest_eval),
        "interpretation": (
            "read-only observability; replay, holdout, terminal, and proof gates "
            "remain candidate authority"
        ),
    }


def _resolve_project_path(project: str | Path) -> Path:
    path = Path(project)
    candidates = [path]
    if not path.is_absolute():
        candidates.append(Path("projects") / path)
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "workspace").is_dir() or (resolved / "latest_eval_results.json").exists():
            return resolved
    return path.resolve()


def _cegis_membrane_summary(
    project: Path,
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    withheld = tuple(
        ref
        for ref in (
            "raw/episodes/episode_002.jsonl",
            "evidence_holdout.txt",
            "evidence_farther_tail.txt",
        )
        if (project / ref).exists()
    )
    gate_passed = any(row.get("current_status") == "current_contract_passed" for row in candidate_rows)
    return {
        "evaluation": assess_cegis_membrane(
            role="EVALUATION",
            withheld_refs=withheld,
            candidate_gate_passed=gate_passed,
        ).to_dict(),
        "discovery": assess_cegis_membrane(
            role="DISCOVERY",
            withheld_refs=withheld,
            exposed_refs=withheld,
            candidate_gate_passed=gate_passed,
        ).to_dict(),
        "harness_debug": assess_cegis_membrane(
            role="HARNESS_DEBUG",
            withheld_refs=withheld,
            exposed_refs=withheld,
            candidate_gate_passed=gate_passed,
        ).to_dict(),
        "policy": (
            "Discovery may inspect withheld slices; inspected slices become "
            "counterexample evidence. Candidate transport claims need an "
            "uninspected or refreshed membrane."
        ),
    }


def write_arc3_run_observability(
    project: str | Path,
    *,
    top_candidates: int = 3,
    candidate_timeout_seconds: int = 60,
) -> Path:
    project = _resolve_project_path(project)
    out = project / "workspace" / "arc3_run_observability.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_arc3_run_observability(
        project,
        top_candidates=top_candidates,
        candidate_timeout_seconds=candidate_timeout_seconds,
    )
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _existing_refs(project: Path, refs: list[str]) -> list[str]:
    return [ref for ref in refs if (project / ref).exists()]


def _latest_run_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    run_id = rows[-1].get("run_id")
    if run_id is None:
        return rows[-10:]
    return [row for row in rows if row.get("run_id") == run_id]


def _latest_run_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    iterations = [row for row in rows if row.get("record_type") == "iteration"]
    start = next((row for row in rows if row.get("record_type") == "run_start"), {})
    end = next((row for row in reversed(rows) if row.get("record_type") == "run_end"), {})
    return {
        "run_id": start.get("run_id") or end.get("run_id"),
        "iteration_budget": start.get("iteration_budget"),
        "iteration_count": len(iterations),
        "final_score": end.get("final_score"),
        "exit_reason": end.get("run_exit_reason"),
        "wall_clock_seconds_total": round(
            sum(float(row.get("wall_clock_seconds") or 0.0) for row in iterations),
            3,
        ),
        "pending_loop_actions": [
            row.get("pending_loop_action")
            for row in iterations
            if row.get("pending_loop_action")
        ],
        "information_yield_rationales": [
            row.get("information_yield_rationale")
            for row in iterations[-3:]
            if row.get("information_yield_rationale")
        ],
    }


def _latest_eval_summary(payload: dict[str, Any]) -> dict[str, Any]:
    receipts = payload.get("control_receipts") if isinstance(payload.get("control_receipts"), list) else []
    blockers = payload.get("lowerability_blockers") if isinstance(payload.get("lowerability_blockers"), list) else []
    return {
        "score": payload.get("score"),
        "raw_judge_score": payload.get("raw_judge_score"),
        "score_cap_reason": payload.get("score_cap_reason"),
        "weakest_point": payload.get("weakest_point"),
        "control_receipt_count": len(receipts),
        "lowerability_blocker_count": len(blockers),
        "evidence_gap_count": len(payload.get("evidence_gaps") or []),
        "visible_capabilities_attempted": sorted(
            {
                str(cap)
                for blocker in blockers
                if isinstance(blocker, dict)
                for cap in (blocker.get("visible_capabilities_attempted") or [])
            }
        ),
    }


def _abduction_summary(payload: dict[str, Any]) -> dict[str, Any]:
    transitions = int(payload.get("transitions") or 0)
    matched = int(payload.get("matched_transitions") or 0)
    return {
        "status": "available" if payload else "absent",
        "transitions": transitions,
        "matched_transitions": matched,
        "unmatched_transitions": max(0, transitions - matched),
        "matched_fraction": round(matched / transitions, 6) if transitions else None,
        "residual_class_count": payload.get("residual_class_count"),
        "top_residuals": (payload.get("residuals") or [])[:3],
    }


def _transfer_summary(payload: dict[str, Any]) -> dict[str, Any]:
    local = payload.get("local_transfer") if isinstance(payload.get("local_transfer"), dict) else {}
    return {
        "status": payload.get("status"),
        "post_depth": payload.get("post_depth"),
        "exact_actions": payload.get("exact_actions"),
        "local_exact_steps": local.get("exact_steps"),
        "exact_steps_after_first_step_repair": local.get("exact_steps_after_first_step_repair"),
        "first_failed": local.get("first_failed"),
        "first_failed_after_first_step_repair": local.get("first_failed_after_first_step_repair"),
    }


def _play_summary(payload: dict[str, Any]) -> dict[str, Any]:
    cycles = payload.get("cycles") if isinstance(payload.get("cycles"), list) else []
    return {
        "mode": payload.get("mode"),
        "result": payload.get("result"),
        "cycle_count": len(cycles),
        "last_cycle": cycles[-1] if cycles else {},
    }


def _p0_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "scoreboard": payload.get("scoreboard") or {},
        "transfer": payload.get("transfer") or {},
        "kernel_pressure": payload.get("kernel_pressure") or {},
        "compression": payload.get("compression") or {},
    }


def _candidate_memory_top_rows(path: Path, limit: int) -> list[dict[str, Any]]:
    payload = _read_json(path)
    rows = payload.get("records") if isinstance(payload.get("records"), list) else []
    rows = [row for row in rows if isinstance(row, dict)]
    rows.sort(key=_candidate_rank, reverse=True)
    return rows[: max(0, int(limit))]


def _candidate_rank(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row.get("visible_exact_rows") or 0),
        -int(row.get("visible_wrong_cells") or 10**12),
        int(row.get("holdout_depth") or 0),
        float(row.get("gate_score") or 0.0),
        str(row.get("observed_at_utc") or ""),
    )


def _revalidate_candidate_row(
    project: Path,
    row: dict[str, Any],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    ref = str(row.get("submission") or row.get("path") or "").strip()
    out = {
        "sha": row.get("sha"),
        "submission": ref,
        "stored_visible_exact_rows": row.get("visible_exact_rows"),
        "stored_visible_wrong_cells": row.get("visible_wrong_cells"),
        "stored_holdout_depth": row.get("holdout_depth"),
        "stored_gate_score": row.get("gate_score"),
        "current_status": "not_checked",
    }
    if not ref:
        out["current_status"] = "missing_ref"
        return out
    rel = Path(ref)
    if rel.is_absolute() or ".." in rel.parts:
        out["current_status"] = "unsafe_ref"
        return out
    candidate = project / rel
    gate = project / "gate_harness.py"
    if not candidate.is_file() or not gate.is_file():
        out["current_status"] = "missing_candidate_or_gate"
        return out
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(gate),
                "--emit-deterministic-gates",
                "--candidate-path",
                str(candidate),
            ],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds)),
        )
        if proc.returncode != 0:
            out["current_status"] = "gate_error"
            out["stderr"] = proc.stderr[-500:]
            return out
        payload = json.loads(proc.stdout or "{}")
    except Exception as exc:  # noqa: BLE001
        out["current_status"] = "gate_exception"
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    out["current_gate_score"] = payload.get("score")
    out["current_harness_ok"] = bool(payload.get("harness_ok"))
    out["current_import_error"] = payload.get("import_error", "")
    gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
    visible = gates.get("visible_replay_exact") if isinstance(gates.get("visible_replay_exact"), dict) else {}
    holdout = gates.get("holdout_rollout_exact") if isinstance(gates.get("holdout_rollout_exact"), dict) else {}
    diag = visible.get("diagnostics") if isinstance(visible.get("diagnostics"), dict) else {}
    out["current_visible_exact_rows"] = diag.get("exact_rows")
    out["current_visible_wrong_cells"] = diag.get("wrong_cell_count")
    out["current_holdout_depth"] = holdout.get("value")
    out["current_status"] = (
        "current_contract_passed"
        if bool(payload.get("harness_ok"))
        and all(
            isinstance(g, dict) and bool(g.get("pass"))
            for g in gates.values()
        )
        else "current_contract_rejected"
    )
    return out


def _stale_memory_alerts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts = []
    for row in rows:
        stored_exact = row.get("stored_visible_exact_rows")
        current_exact = row.get("current_visible_exact_rows")
        status = str(row.get("current_status") or "")
        rejected = status in {
            "current_contract_rejected",
            "gate_error",
            "gate_exception",
        }
        detail = (
            str(row.get("current_import_error") or "")
            or str(row.get("stderr") or "")
            or str(row.get("error") or "")
        )
        score_drifted = (
            isinstance(stored_exact, int)
            and isinstance(current_exact, int)
            and current_exact < stored_exact
        )
        if (rejected or score_drifted) and (stored_exact or 0) > 0:
            alerts.append(
                {
                    "kind": "stored_candidate_score_not_current_contract",
                    "submission": row.get("submission"),
                    "stored_visible_exact_rows": stored_exact,
                    "current_status": status,
                    "current_visible_exact_rows": current_exact,
                    "detail": detail[:500],
                }
            )
    return alerts


def _visible_workbench_summaries(project: Path) -> list[dict[str, Any]]:
    roots = [
        Path(__import__("os").environ.get("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT") or ""),
        Path(tempfile.gettempdir()) / "ztare_visible_workbench",
    ]
    seen: set[Path] = set()
    rows: list[dict[str, Any]] = []
    for root in roots:
        if not str(root) or not root.exists():
            continue
        for manifest_path in root.glob("*/MANIFEST.json"):
            workbench = manifest_path.parent
            if workbench in seen:
                continue
            seen.add(workbench)
            row = _visible_workbench_summary(project, workbench, manifest_path)
            if row:
                rows.append(row)
    project_receipts = _project_workbench_receipt_summary(project)
    if project_receipts:
        rows.append(project_receipts)
    rows.sort(
        key=lambda row: (
            int(row.get("receipt_count") or 0) > 0,
            float(row.get("mtime") or 0.0),
        ),
        reverse=True,
    )
    return rows[:5]


def _visible_workbench_summary(project: Path, workbench: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    authority = str(manifest.get("authority_project_path") or "")
    project_ref = str(manifest.get("authority_project_ref") or "")
    if authority:
        try:
            if Path(authority).resolve() != project.resolve():
                return {}
        except OSError:
            return {}
    elif project_ref and project_ref != str(project.relative_to(project.parents[1])):
        return {}
    receipts_dir = workbench / "workspace" / "visible_cli_receipts"
    receipts = []
    for path in receipts_dir.glob("*.json"):
        payload = _read_json(path)
        receipts.append(
            {
                "command": str(payload.get("command") or payload.get("capability_id") or ""),
                "status": str(payload.get("status") or ""),
                "duration_ms": payload.get("duration_ms"),
                "output_summary": str(payload.get("output_summary") or "")[:240],
            }
        )
    manifest_mtime = manifest_path.stat().st_mtime
    scratch = _scratch_analysis_summary(workbench, since_mtime=manifest_mtime)
    return {
        "workbench": str(workbench),
        "mtime": manifest_path.stat().st_mtime,
        "task_bytes": _size(workbench / "TASK.md"),
        "attention_bytes": _size(workbench / "ATTENTION.md"),
        "records_bytes": _size(workbench / "RECORDS.json"),
        "context_bytes": _size(workbench / "CONTEXT.md"),
        "tool_doc_bytes": _size(workbench / "WORKBENCH_TOOLS.md"),
        "receipt_count": len(receipts),
        "receipt_commands": dict(Counter(row["command"] or "unknown" for row in receipts)),
        "receipt_statuses": dict(Counter(row["status"] or "unknown" for row in receipts)),
        "scratch_analysis": scratch,
        "duration_ms_total": round(
            sum(float(row["duration_ms"]) for row in receipts if isinstance(row.get("duration_ms"), (int, float))),
            3,
        ),
        "recent_receipts": receipts[-8:],
    }


def _scratch_analysis_summary(workbench: Path, *, since_mtime: float) -> dict[str, Any]:
    excluded_dirs = {
        workbench / "workspace" / "visible_cli_receipts",
        workbench / "workspace" / "leaf_workbench_action_receipts",
        workbench / "workspace" / "submissions",
        workbench / "raw",
        workbench / "src",
    }
    excluded_names = {
        "ASKS.json",
        "ATTENTION.md",
        "CONTEXT.md",
        "MANIFEST.json",
        "README.md",
        "RECORDS.json",
        "TASK.md",
        "WORKBENCH_TOOLS.md",
        "candidate_repair.py",
        "evidence_holdout.txt",
        "final_payload.json",
        "visible_manifest.json",
    }
    refs: list[str] = []
    for path in workbench.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime <= since_mtime:
                continue
        except OSError:
            continue
        if any(parent in path.parents for parent in excluded_dirs):
            continue
        if path.name in excluded_names:
            continue
        if not path.name.lower().endswith((".json", ".jsonl", ".py", ".txt", ".md")):
            continue
        rel = path.relative_to(workbench).as_posix()
        lower = rel.lower()
        if any(token in lower for token in ("analysis", "scratch", "candidate", "abduc", "probe", "mine")):
            refs.append(rel)
    return {
        "artifact_count": len(refs),
        "artifact_refs": sorted(refs)[:12],
    }


def _project_workbench_receipt_summary(project: Path) -> dict[str, Any]:
    receipts_root = project / "workspace" / "leaf_workbench_action_receipts"
    if not receipts_root.exists():
        return {}
    paths = sorted(
        receipts_root.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:32]
    if not paths:
        return {}
    receipts = []
    for path in paths:
        payload = _read_json(path)
        receipt = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else payload
        receipts.append(
            {
                "command": str(
                    receipt.get("capability_id")
                    or payload.get("capability_id")
                    or "unknown"
                ),
                "status": str(
                    receipt.get("status")
                    or payload.get("status")
                    or _status_from_output_summary(receipt.get("output_summary"))
                    or ""
                ),
                "duration_ms": receipt.get("duration_ms") or payload.get("duration_ms"),
                "output_summary": str(receipt.get("output_summary") or "")[:240],
            }
        )
    return {
        "workbench": str(receipts_root),
        "source": "project_leaf_workbench_action_receipts",
        "mtime": max(path.stat().st_mtime for path in paths),
        "task_bytes": 0,
        "attention_bytes": 0,
        "records_bytes": 0,
        "context_bytes": 0,
        "tool_doc_bytes": 0,
        "receipt_count": len(receipts),
        "receipt_commands": dict(Counter(row["command"] or "unknown" for row in receipts)),
        "receipt_statuses": dict(Counter(row["status"] or "unknown" for row in receipts)),
        "duration_ms_total": round(
            sum(float(row["duration_ms"]) for row in receipts if isinstance(row.get("duration_ms"), (int, float))),
            3,
        ),
        "recent_receipts": list(reversed(receipts[-8:])),
    }


def _status_from_output_summary(summary: object) -> str:
    text = str(summary or "")
    for marker in (
        "candidate_preflight_passed",
        "candidate_preflight_failed",
        "candidate_delta_admissible=true",
        "candidate_delta_admissible=false",
    ):
        if marker in text:
            return marker
    return ""


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _cognitive_parity_summary(
    workbenches: list[dict[str, Any]],
    latest_eval: dict[str, Any],
) -> dict[str, Any]:
    latest = next(
        (row for row in workbenches if int(row.get("receipt_count") or 0) > 0),
        workbenches[0] if workbenches else {},
    )
    commands = latest.get("receipt_commands") if isinstance(latest.get("receipt_commands"), dict) else {}
    blockers = latest_eval.get("lowerability_blockers")
    blockers = blockers if isinstance(blockers, list) else []
    return {
        "latest_workbench_receipts": latest.get("receipt_count", 0),
        "latest_workbench_commands": commands,
        "scratch_analysis_artifacts": (
            latest.get("scratch_analysis", {}).get("artifact_count")
            if isinstance(latest.get("scratch_analysis"), dict)
            else 0
        ),
        "candidate_scorer_used": any(
            int(commands.get(key, 0) or 0) > 0
            for key in ("score-worldmodel-candidate", "score_worldmodel_candidate_delta")
        ),
        "local_probe_used": any(
            key in commands
            for key in (
                "probe-json",
                "mine-worldmodel-lowerable-selectors",
                "mine-worldmodel-separating-features",
                "cell-local-lowerable-carrier-selector-miner",
                "run_visible_json_probe",
                "mine_worldmodel_lowerable_selectors",
                "mine_worldmodel_separating_features",
                "cell_local_lowerable_carrier_selector_miner",
                "inspect_worldmodel_counterexample_context",
                "rank_next_morphisms",
            )
        ),
        "ended_with_lowerability_blocker": bool(blockers),
        "parity_gap": (
            "current run reached visible probes and candidate scoring; surviving gap is science/lowerability"
            if commands and blockers
            else "insufficient workbench telemetry to classify parity"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--top-candidates", type=int, default=3)
    args = parser.parse_args(argv)
    if args.write:
        path = write_arc3_run_observability(args.project, top_candidates=args.top_candidates)
        print(path)
    else:
        print(json.dumps(build_arc3_run_observability(args.project, top_candidates=args.top_candidates), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
