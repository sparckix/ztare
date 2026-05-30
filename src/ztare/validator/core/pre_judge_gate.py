from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PreJudgeGateResult:
    enabled: bool
    ran: bool
    should_skip_judge: bool
    message: str | None = None
    score_cap_reason: str | None = None
    payload: dict[str, Any] | None = None


def _gate_passed(gate: Any) -> bool:
    if not isinstance(gate, dict):
        return False
    return bool(gate.get("passed", gate.get("pass", False)))


def _normalize_gate_iter(payload: dict[str, Any]) -> list[dict[str, Any]]:
    gate_iter = payload.get("gates", [])
    if isinstance(gate_iter, dict):
        gate_iter = list(gate_iter.values())
    if not isinstance(gate_iter, list):
        return []
    return [g for g in gate_iter if isinstance(g, dict)]


def _failed_gate_labels(gates: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for gate in gates:
        if not _gate_passed(gate):
            labels.append(f"{gate.get('name', '?')}: {gate.get('value', '?')}")
    if not labels and not gates:
        labels.append("?: no gates emitted")
    return labels


def _write_eval(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _blocked_eval(gate_payload: dict[str, Any], failed_gates: list[str]) -> dict[str, Any]:
    return {
        "score": 0,
        "weakest_point": (
            "PRE_JUDGE_HARD_GATE: candidate failed deterministic "
            f"gate before judge call. failed_gates={failed_gates}"
        ),
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": [
            "Candidate failed project-local deterministic gate before judge evaluation."
        ],
        "debate_summary": (
            "Pre-judge deterministic gate blocked evaluation to avoid spending "
            "judge tokens on a known invalid pattern."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {
                "label": "pre_judge_hard_gate_failed",
                "probability": 0.0,
            },
            "nodes": [],
            "edges": [],
        },
        "holdout_hard_gate_fired": True,
        "holdout_hard_gate_detail": (
            "Pre-judge gate harness failed before test_thesis/judge. "
            f"failed_gates={failed_gates}"
        ),
        "score_cap_reason": "pre_judge_gate_harness_failed",
        "pre_judge_gate_payload": gate_payload,
    }


def _error_eval(exc: Exception) -> dict[str, Any]:
    return {
        "score": 0,
        "weakest_point": (
            "PRE_JUDGE_HARD_GATE_ERROR: gate harness errored before judge call: "
            f"{type(exc).__name__}: {exc}"
        ),
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": ["Pre-judge gate harness error."],
        "debate_summary": (
            "Pre-judge deterministic gate failed closed to avoid spending judge tokens."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {
                "label": "pre_judge_hard_gate_error",
                "probability": 0.0,
            },
            "nodes": [],
            "edges": [],
        },
        "holdout_hard_gate_fired": True,
        "holdout_hard_gate_detail": str(exc),
        "score_cap_reason": "pre_judge_gate_harness_error",
    }


def run_pre_judge_gate_harness(
    *,
    enabled: bool,
    project_dir: str | Path,
    latest_eval_results_path: str | Path,
    python_executable: str = sys.executable,
    timeout_seconds: int = 30,
    candidate_path: str | Path | None = None,
) -> PreJudgeGateResult:
    """Run an opt-in project-local gate before paid judge evaluation.

    This is intentionally domain-agnostic. The kernel only requires a
    project-local `gate_harness.py --emit-deterministic-gates` JSON payload
    with `harness_ok` and at least one passing gate. Domain-specific gate
    semantics live in each project's harness.
    """
    project_path = Path(project_dir)
    latest_path = Path(latest_eval_results_path)
    if not enabled:
        return PreJudgeGateResult(enabled=False, ran=False, should_skip_judge=False)

    gate_harness_path = project_path / "gate_harness.py"
    if not gate_harness_path.exists():
        return PreJudgeGateResult(enabled=True, ran=False, should_skip_judge=False)

    try:
        gate_cmd = [python_executable, str(gate_harness_path), "--emit-deterministic-gates"]
        if candidate_path is not None:
            gate_cmd.extend(["--candidate-path", str(Path(candidate_path).resolve())])
        gate_res = subprocess.run(
            gate_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=project_path,
        )
        gate_payload = json.loads(gate_res.stdout or "{}")
        if not isinstance(gate_payload, dict):
            raise TypeError("gate_harness.py emitted non-object JSON")
        gate_iter = _normalize_gate_iter(gate_payload)
        all_gates_passed = (
            bool(gate_payload.get("harness_ok"))
            and bool(gate_iter)
            and all(_gate_passed(g) for g in gate_iter)
        )
        if all_gates_passed:
            return PreJudgeGateResult(
                enabled=True,
                ran=True,
                should_skip_judge=False,
                message="✅ Pre-judge gate harness passed.",
                payload=gate_payload,
            )

        failed_gates = _failed_gate_labels(gate_iter)
        pre_judge_eval = _blocked_eval(gate_payload, failed_gates)
        _write_eval(latest_path, pre_judge_eval)
        return PreJudgeGateResult(
            enabled=True,
            ran=True,
            should_skip_judge=True,
            message=(
                "🚫 Pre-judge gate harness blocked candidate before judge call: "
                f"{failed_gates}"
            ),
            score_cap_reason="pre_judge_gate_harness_failed",
            payload=gate_payload,
        )
    except Exception as exc:  # noqa: BLE001
        pre_judge_eval = _error_eval(exc)
        _write_eval(latest_path, pre_judge_eval)
        return PreJudgeGateResult(
            enabled=True,
            ran=True,
            should_skip_judge=True,
            message=(
                "🚫 Pre-judge gate harness errored; failing closed before judge call: "
                f"{type(exc).__name__}: {exc}"
            ),
            score_cap_reason="pre_judge_gate_harness_error",
        )
