from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ztare.common.paths import PROJECTS_DIR, REPO_ROOT


@dataclass
class BundleArtifact:
    kind: str
    path: str
    exists: bool
    note: str | None = None


@dataclass
class DebateBundle:
    task_id: str
    project: str
    run_id: str | None
    stage: str | None
    stage_verdict: str | None
    summary: str
    artifacts: list[BundleArtifact]
    context: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except Exception:
        return None


def _artifact(path: Path, note: str | None = None) -> BundleArtifact:
    try:
        rel = path.relative_to(REPO_ROOT)
        path_str = str(rel)
    except ValueError:
        path_str = str(path)
    return BundleArtifact(
        kind=path.suffix.lstrip(".") or "file",
        path=path_str,
        exists=path.exists(),
        note=note,
    )


def infer_stage1_run_id(project: str) -> str | None:
    evidence_path = PROJECTS_DIR / project / "stage1_benchmark_evidence.json"
    data = _maybe_json(evidence_path)
    if not data:
        return None
    runs = data.get("evidence_runs") or []
    if not runs:
        return None
    latest = runs[-1]
    return latest.get("run_id")


def build_stage1_fail_bundle(project: str, run_id: str | None = None) -> DebateBundle:
    project_dir = PROJECTS_DIR / project
    run_id = run_id or infer_stage1_run_id(project)

    state_data = _maybe_json(project_dir / "meta_runner_state.json") or {}
    evidence_data = _maybe_json(project_dir / "stage1_benchmark_evidence.json") or {}
    forensic_data = _maybe_json(project_dir / "forensic_report.json") or {}

    artifacts = [
        _artifact(project_dir / "thesis.md", "Active stage-1 thesis"),
        _artifact(project_dir / "current_iteration.md", "Current iteration snapshot"),
        _artifact(project_dir / "test_model.py", "Stage-1 local harness"),
        _artifact(project_dir / "stage1_benchmark_evidence.json", "Promotion evidence"),
        _artifact(project_dir / "forensic_report.json", "Auto-generated fail triage"),
        _artifact(project_dir / "meta_runner_plan.json", "Stage queue"),
        _artifact(project_dir / "meta_runner_state.json", "Current stage verdict"),
    ]

    if run_id:
        run_root = REPO_ROOT / "benchmarks" / "constraint_memory" / "runs" / run_id
        artifacts.extend(
            [
                _artifact(run_root / "metrics_summary.json", "Benchmark summary"),
                _artifact(
                    run_root / "t2_ai_inference" / "B_deterministic_gates" / "eval_results.json",
                    "Target case under B",
                ),
                _artifact(
                    run_root / "t2_ai_inference" / "C_gates_plus_primitives" / "eval_results.json",
                    "Target case under C",
                ),
                _artifact(
                    run_root / "deterministic_score_contract" / "B_deterministic_gates" / "eval_results.json",
                    "Failed good control under B",
                ),
                _artifact(
                    run_root / "fail_closed_test_status" / "C_gates_plus_primitives" / "eval_results.json",
                    "Failed good control under C",
                ),
            ]
        )

    stage = None
    current_stage_idx = state_data.get("current_stage")
    plan = _maybe_json(project_dir / "meta_runner_plan.json") or {}
    queue = plan.get("queue") or []
    if isinstance(current_stage_idx, int) and 0 <= current_stage_idx < len(queue):
        stage = queue[current_stage_idx].get("name")

    summary = (
        "Stage-1 benchmark failed promotion: target case improved, but good controls regressed. "
        "Use this bundle to separate gate overreach from legitimate thesis falsification."
    )

    context = {
        "run_id": run_id,
        "meta_runner_state": state_data,
        "stage1_benchmark_evidence": evidence_data,
        "forensic_report": forensic_data,
        "required_outputs": {
            "finding_fields": ["id", "severity", "claim", "evidence", "proposed_fix", "confidence"],
            "decision_fields": ["do_not_change", "next_action", "requires_human_review"],
        },
    }

    task_id = f"{project}_{stage or 'stage'}_{run_id or 'no_run'}"
    return DebateBundle(
        task_id=task_id,
        project=project,
        run_id=run_id,
        stage=stage,
        stage_verdict=state_data.get("last_verdict"),
        summary=summary,
        artifacts=artifacts,
        context=context,
    )


def bundle_to_dict(bundle: DebateBundle) -> dict[str, Any]:
    return {
        "task_id": bundle.task_id,
        "project": bundle.project,
        "run_id": bundle.run_id,
        "stage": bundle.stage,
        "stage_verdict": bundle.stage_verdict,
        "summary": bundle.summary,
        "artifacts": [asdict(item) for item in bundle.artifacts],
        "context": bundle.context,
    }

