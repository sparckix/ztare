from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ztare.common.paths import PROJECTS_DIR
from ztare.common.sandboxed_python import (run_python_file as _shared_run_python_file,
                                               run_python_module as _shared_run_python_module)

ContractVerdict = Literal["pass", "fail", "blocked"]


@dataclass
class ContractResult:
    verdict: ContractVerdict
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeMetaState:
    last_verdict: ContractVerdict | None = None
    last_report: list[str] = field(default_factory=list)


def project_dir(project: str) -> Path:
    return PROJECTS_DIR / project


def state_path(project: str) -> Path:
    return project_dir(project) / "bridge_meta_runner_state.json"


def plan_path(project: str) -> Path:
    return project_dir(project) / "bridge_meta_runner_plan.json"


def _run_python_module(module_name: str, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    # Shared sandboxed-python exec (the ONE home); behaviour-identical to the prior inline calls.
    return _shared_run_python_module(module_name, cwd=cwd)


def _run_python_file(path: Path) -> subprocess.CompletedProcess[str]:
    return _shared_run_python_file(path, cwd=path.parents[2])


def _bridge_contract(project: str) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "bridge_mismatch_vocabulary.md",
        base / "bridge_benchmark_evidence.json",
        base / "frozen_bridge_candidate.md",
        base / "frozen_bridge_candidate_test_model.py",
        base / "frozen_bridge_candidate_vocabulary.md",
        base / "frozen_bridge_candidate_meta.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required bridge artifact(s): {', '.join(missing)}"])

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    vocab_text = (base / "bridge_mismatch_vocabulary.md").read_text()

    frozen_thesis = (base / "frozen_bridge_candidate.md").read_text()
    frozen_test_model = (base / "frozen_bridge_candidate_test_model.py").read_text()
    frozen_vocab = (base / "frozen_bridge_candidate_vocabulary.md").read_text()

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen bridge candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the audited bridge candidate.")

    if not current_text.startswith(frozen_thesis):
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen bridge candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen bridge candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen bridge candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the audited bridge fixture harness.")

    if vocab_text != frozen_vocab:
        fail_reasons.append("`bridge_mismatch_vocabulary.md` no longer matches the frozen bridge vocabulary.")
    else:
        pass_reasons.append("`bridge_mismatch_vocabulary.md` is frozen to the audited mismatch vocabulary.")

    compile_proc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(base / "test_model.py")],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        fail_reasons.append(f"`test_model.py` failed to compile: {compile_proc.stderr.strip()}")
    else:
        pass_reasons.append("`test_model.py` compiles successfully.")

    test_proc = _run_python_file(base / "test_model.py")
    if test_proc.returncode != 0:
        fail_reasons.append(f"`test_model.py` failed at runtime: {(test_proc.stderr or test_proc.stdout).strip()}")
    else:
        pass_reasons.append("`test_model.py` executes successfully.")

    fixture_proc = _run_python_module(
        "src.ztare.validator.core.stage24_bridge_fixture_regression",
        cwd=Path(__file__).resolve().parents[3],
    )
    if fixture_proc.returncode != 0:
        fail_reasons.append(
            "Bridge fixture regression failed: "
            + (fixture_proc.stderr.strip() or fixture_proc.stdout.strip())
        )
    else:
        pass_reasons.append("Bridge fixture regression passes.")

    evidence_path = base / "bridge_benchmark_evidence.json"
    try:
        evidence = json.loads(evidence_path.read_text())
    except json.JSONDecodeError as exc:
        fail_reasons.append(f"`bridge_benchmark_evidence.json` is invalid JSON: {exc}")
        evidence = {}

    required_keys = [
        "implementation_applied",
        "fixture_regression_passed",
        "bounded_adversarial_support",
        "promotion_recommendation",
        "evidence_runs",
    ]
    missing_keys = [key for key in required_keys if key not in evidence]
    if missing_keys:
        fail_reasons.append(
            "`bridge_benchmark_evidence.json` is missing required keys: "
            + ", ".join(missing_keys)
        )
    else:
        if evidence["implementation_applied"] is not True:
            blocked_reasons.append("Bridge evidence exists but implementation is not marked as applied.")
        elif evidence["fixture_regression_passed"] is not True:
            blocked_reasons.append("Bridge evidence exists but fixture regression is not yet marked as passing.")
        elif evidence["bounded_adversarial_support"] is not True:
            blocked_reasons.append("Bridge evidence exists but bounded adversarial support is not yet recorded.")
        elif evidence["promotion_recommendation"] is not True:
            blocked_reasons.append("Bridge evidence exists but does not yet recommend promotion.")
        else:
            pass_reasons.append("Bridge evidence supports promotion on the audited bridge contract.")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


def load_state(project: str) -> BridgeMetaState:
    s_path = state_path(project)
    if not s_path.exists():
        return BridgeMetaState()
    data = json.loads(s_path.read_text())
    return BridgeMetaState(
        last_verdict=data.get("last_verdict"),
        last_report=data.get("last_report", []),
    )


def save_state(project: str, state: BridgeMetaState) -> None:
    state_path(project).write_text(
        json.dumps(
            {
                "last_verdict": state.last_verdict,
                "last_report": state.last_report,
            },
            indent=2,
        )
        + "\n"
    )


def print_status(project: str, result: ContractResult | None = None) -> None:
    plan = json.loads(plan_path(project).read_text()) if plan_path(project).exists() else {}
    print(f"Bridge Project: {project}")
    if plan:
        print(f"Contract: {plan.get('contract_name', 'unknown')}")
    if result is not None:
        print(f"Verdict: {result.verdict}")
        for reason in result.reasons:
            print(f"- {reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bridge-family meta-runner.")
    parser.add_argument("--project", required=True)
    parser.add_argument("command", choices=["show", "run-current", "reset"])
    args = parser.parse_args()

    if args.command == "reset":
        save_state(args.project, BridgeMetaState())
        print("Bridge meta-runner state reset.")
        return 0

    if args.command == "show":
        state = load_state(args.project)
        result = ContractResult(
            verdict=state.last_verdict or "blocked",
            reasons=state.last_report,
        )
        print_status(args.project, result)
        return 0

    result = _bridge_contract(args.project)
    save_state(args.project, BridgeMetaState(last_verdict=result.verdict, last_report=result.reasons))
    print_status(args.project, result)
    return 0 if result.verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
