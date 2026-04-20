from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from src.ztare.common.paths import PROJECTS_DIR
from src.ztare.reports.forensic_reporter import build_report, write_report

ContractVerdict = Literal["pass", "fail", "blocked"]
Priority = Literal["P0", "P1"]


@dataclass
class ContractResult:
    verdict: ContractVerdict
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageSpec:
    name: str
    item_number: int
    priority: Priority
    contract_name: str
    active: bool = False


@dataclass
class MetaRunnerState:
    current_stage: int = 0
    last_verdict: ContractVerdict | None = None
    last_report: list[str] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)


@dataclass
class MetaRunner:
    project: str
    queue: list[StageSpec]
    state: MetaRunnerState
    state_path: Path
    contracts: dict[str, Callable[[str, Any], ContractResult]]

    def current(self) -> StageSpec:
        if not self.queue:
            raise RuntimeError("Meta-runner queue is empty.")
        if self.state.current_stage >= len(self.queue):
            raise RuntimeError("Meta-runner has no remaining active stage.")
        return self.queue[self.state.current_stage]

    def run_stage(self, benchmark_results: Any = None) -> ContractResult:
        stage = self.current()
        contract = self.contracts[stage.contract_name]
        result = contract(self.project, benchmark_results)
        verdict = result.verdict
        self.state.last_verdict = verdict
        self.state.last_report = result.reasons
        if verdict == "pass" and stage.name not in self.state.completed_stages:
            self.state.completed_stages.append(stage.name)
        self.save_state()
        return result

    def advance(self) -> None:
        if self.state.last_verdict != "pass":
            raise RuntimeError("Cannot advance: current stage has not passed its contract.")
        if self.state.current_stage >= len(self.queue) - 1:
            raise RuntimeError("Cannot advance: already at the final stage.")
        self.state.current_stage += 1
        self.state.last_verdict = None
        self.save_state()

    def reset(self) -> None:
        self.state = MetaRunnerState()
        self.save_state()

    def save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(
                {
                    "current_stage": self.state.current_stage,
                    "last_verdict": self.state.last_verdict,
                    "last_report": self.state.last_report,
                    "completed_stages": self.state.completed_stages,
                },
                indent=2,
            )
            + "\n"
        )


def _run_python_file(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path)],
        cwd=path.parent.parent.parent,
        capture_output=True,
        text=True,
    )


def _semantic_gate_stabilization_contract(project: str, _: Any) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "probability_dag.json",
        base / "frozen_stage1_candidate.md",
        base / "frozen_stage1_candidate_test_model.py",
        base / "frozen_stage1_candidate_dag.json",
        base / "frozen_stage1_candidate_meta.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required stage-1 artifact(s): {', '.join(missing)}"])

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    frozen_thesis = (base / "frozen_stage1_candidate.md").read_text()
    frozen_test_model = (base / "frozen_stage1_candidate_test_model.py").read_text()
    autoresearch_text = (
        Path(__file__).resolve().parent / "autoresearch_loop.py"
    ).read_text()

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen stage-1 candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the current stage-1 candidate.")

    if not current_text.startswith(frozen_thesis):
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen stage-1 candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen stage-1 candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen stage-1 candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the current stage-1 candidate harness.")

    required_symbols = [
        "DiagnosticSummary",
        "aggregate_unresolved_diagnoses",
        "UnresolvedDiagnosis",
        "HingeObject",
        "ExploitFamilyTag",
    ]
    missing_symbols = [symbol for symbol in required_symbols if symbol not in test_model_text]
    if missing_symbols:
        fail_reasons.append(
            "Stage-1 harness is missing required typed interfaces/mechanisms: "
            + ", ".join(missing_symbols)
        )
    else:
        pass_reasons.append("Stage-1 harness contains the required typed interfaces and exogenous aggregator.")

    thesis_lower = thesis_text.lower()
    if "exogenously" not in thesis_lower or "aggregate_unresolved_diagnoses" not in thesis_text:
        fail_reasons.append("Stage-1 thesis no longer states that aggregation is exogenous to the gate kernel.")
    else:
        pass_reasons.append("Stage-1 thesis keeps diagnostic aggregation exogenous to `derive_gate_status`.")

    deterministic_gate_markers = [
        'args.project == "epistemic_engine_v4" and not args.deterministic_score_gates',
        "is_v4_family_project(args.project) and not args.deterministic_score_gates",
    ]
    if not any(marker in autoresearch_text for marker in deterministic_gate_markers):
        fail_reasons.append("V4 deterministic score-gate enforcement is missing from `autoresearch_loop.py`.")
    else:
        pass_reasons.append("V4 deterministic score-gate enforcement is present in `autoresearch_loop.py`.")

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

    benchmark_evidence_path = base / "stage1_benchmark_evidence.json"
    if not benchmark_evidence_path.exists():
        blocked_reasons.append(
            "Local stage-1 architecture checks pass, but no `stage1_benchmark_evidence.json` exists yet."
        )
        blocked_reasons.append(
            "Stage 1 cannot promote until benchmark evidence shows no `CLEAR/FATAL` regression and documents the semantic-gate outcome on the target cases."
        )
    else:
        try:
            benchmark_data = json.loads(benchmark_evidence_path.read_text())
        except json.JSONDecodeError as exc:
            fail_reasons.append(f"`stage1_benchmark_evidence.json` is invalid JSON: {exc}")
        else:
            required_benchmark_keys = [
                "implementation_applied",
                "clear_fatal_regression",
                "good_controls_preserved",
                "target_case_assessed",
                "ood_probe_support",
                "contract_boundary_approved",
                "promotion_recommendation",
            ]
            missing_keys = [key for key in required_benchmark_keys if key not in benchmark_data]
            if missing_keys:
                fail_reasons.append(
                    "`stage1_benchmark_evidence.json` is missing required keys: "
                    + ", ".join(missing_keys)
                )
            elif benchmark_data["implementation_applied"] is not True:
                blocked_reasons.append(
                    "Benchmark evidence file exists, but the stage-1 design is not yet marked as implemented in the live evaluator."
                )
            elif benchmark_data["clear_fatal_regression"] is None:
                blocked_reasons.append("Benchmark evidence exists, but `clear_fatal_regression` is still unset.")
            elif benchmark_data["clear_fatal_regression"] is True:
                fail_reasons.append("Benchmark evidence reports `CLEAR/FATAL` regression.")
            elif benchmark_data["good_controls_preserved"] is None:
                blocked_reasons.append("Benchmark evidence exists, but `good_controls_preserved` is still unset.")
            elif benchmark_data["good_controls_preserved"] is not True:
                fail_reasons.append("Benchmark evidence does not preserve good controls.")
            elif benchmark_data["target_case_assessed"] is not True:
                blocked_reasons.append("Benchmark evidence exists but the target semantic-variance case has not been assessed.")
            elif benchmark_data["ood_probe_support"] is not True:
                blocked_reasons.append("Benchmark evidence exists but OOD probe support is not yet recorded.")
            elif benchmark_data["contract_boundary_approved"] is not True:
                blocked_reasons.append("Benchmark evidence exists but the narrowed stage-1 contract boundary is not yet approved.")
            elif benchmark_data["promotion_recommendation"] is not True:
                blocked_reasons.append("Benchmark evidence exists but does not yet recommend promotion.")
            else:
                pass_reasons.append("Benchmark evidence supports stage-1 promotion.")

    if fail_reasons:
        benchmark_data = {}
        if benchmark_evidence_path.exists():
            try:
                benchmark_data = json.loads(benchmark_evidence_path.read_text())
            except Exception:
                benchmark_data = {}
        run_id = None
        evidence_runs = benchmark_data.get("evidence_runs", [])
        if evidence_runs:
            run_id = evidence_runs[-1].get("run_id")
        if run_id:
            try:
                from src.ztare.common.paths import PROJECTS_DIR
                report = build_report(
                    Path(__file__).resolve().parents[3]
                    / "benchmarks"
                    / "constraint_memory"
                    / "runs"
                    / run_id,
                    benchmark_data.get("target_case", "t2_ai_inference"),
                )
                write_report(report, PROJECTS_DIR / project / "forensic_report.json")
                pass_reasons.append(
                    f"Automatic forensic report written to `projects/{project}/forensic_report.json`."
                )
            except Exception as exc:
                pass_reasons.append(f"Forensic report generation failed: {exc}")
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


def _blocked_contract(_: str, __: Any) -> ContractResult:
    return ContractResult("blocked", ["Contract not implemented yet."])


def _load_bearing_hinge_extraction_contract(project: str, _: Any) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "probability_dag.json",
        base / "frozen_stage2_candidate.md",
        base / "frozen_stage2_candidate_test_model.py",
        base / "frozen_stage2_candidate_dag.json",
        base / "frozen_stage2_candidate_meta.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required stage-2 artifact(s): {', '.join(missing)}"])

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    frozen_thesis = (base / "frozen_stage2_candidate.md").read_text()
    frozen_test_model = (base / "frozen_stage2_candidate_test_model.py").read_text()

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen stage-2 candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the current stage-2 candidate.")

    if current_text.strip() not in frozen_thesis:
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen stage-2 candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen stage-2 candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen stage-2 candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the current stage-2 candidate harness.")

    required_symbols = [
        "HingeObject",
        "HingeScopeLevel",
        "HingeAlignmentStatus",
        "evaluate_hinge_grounding",
        "HingeGroundingPointer",
    ]
    missing_symbols = [symbol for symbol in required_symbols if symbol not in test_model_text]
    if missing_symbols:
        fail_reasons.append(
            "Stage-2 harness is missing required typed interfaces/mechanisms: "
            + ", ".join(missing_symbols)
        )
    else:
        pass_reasons.append("Stage-2 harness contains the required hinge interfaces and validator.")

    thesis_lower = thesis_text.lower()
    if "strictly exogenous" not in thesis_lower and "operates exogenously" not in thesis_lower:
        fail_reasons.append("Stage-2 thesis no longer states that hinge alignment is exogenous to stage 1.")
    else:
        pass_reasons.append("Stage-2 thesis keeps hinge alignment exogenous to stage 1.")

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

    benchmark_evidence_path = base / "stage2_benchmark_evidence.json"
    if not benchmark_evidence_path.exists():
        blocked_reasons.append(
            "Local stage-2 architecture checks pass, but no `stage2_benchmark_evidence.json` exists yet."
        )
        blocked_reasons.append(
            "Stage 2 cannot promote until targeted hinge-alignment benchmark evidence is recorded."
        )
    else:
        try:
            benchmark_data = json.loads(benchmark_evidence_path.read_text())
        except json.JSONDecodeError as exc:
            fail_reasons.append(f"`stage2_benchmark_evidence.json` is invalid JSON: {exc}")
        else:
            required_benchmark_keys = [
                "implementation_applied",
                "stage2_regression_support",
                "stage2_contract_boundary_approved",
                "promotion_recommendation",
            ]
            missing_keys = [key for key in required_benchmark_keys if key not in benchmark_data]
            if missing_keys:
                fail_reasons.append(
                    "`stage2_benchmark_evidence.json` is missing required keys: "
                    + ", ".join(missing_keys)
                )
            elif benchmark_data["implementation_applied"] is not True:
                blocked_reasons.append(
                    "Stage-2 benchmark evidence exists, but the hinge-alignment design is not yet marked as implemented."
                )
            elif benchmark_data["stage2_regression_support"] is not True:
                blocked_reasons.append(
                    "Stage-2 benchmark evidence exists, but the targeted regression suite does not yet support promotion."
                )
            elif benchmark_data["stage2_contract_boundary_approved"] is not True:
                blocked_reasons.append(
                    "Stage-2 benchmark evidence exists, but the contract boundary is not yet approved."
                )
            elif benchmark_data["promotion_recommendation"] is not True:
                blocked_reasons.append(
                    "Stage-2 benchmark evidence exists but does not yet recommend promotion."
                )
            else:
                pass_reasons.append("Benchmark evidence supports stage-2 promotion.")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


def _primitive_routing_by_exploit_family_contract(project: str, _: Any) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "probability_dag.json",
        base / "frozen_stage3_candidate.md",
        base / "frozen_stage3_candidate_test_model.py",
        base / "frozen_stage3_candidate_dag.json",
        base / "frozen_stage3_candidate_meta.json",
        base / "stage3_benchmark_evidence.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required stage-3 artifact(s): {', '.join(missing)}"])

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    frozen_thesis = (base / "frozen_stage3_candidate.md").read_text()
    frozen_test_model = (base / "frozen_stage3_candidate_test_model.py").read_text()

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen stage-3 candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the current stage-3 candidate.")

    if not current_text.startswith(frozen_thesis):
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen stage-3 candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen stage-3 candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen stage-3 candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the current stage-3 candidate harness.")

    required_symbols = [
        "ExploitFamilyTag",
        "PrimitiveRoutingPolicy",
        "PrimitiveRoutingDecision",
        "POLICY_TO_PRIMITIVE_KEYS",
        "route_primitives_by_family",
        "MANUAL_REVIEW",
    ]
    missing_symbols = [symbol for symbol in required_symbols if symbol not in test_model_text]
    if missing_symbols:
        fail_reasons.append(
            "Stage-3 harness is missing required typed routing interfaces/mechanisms: "
            + ", ".join(missing_symbols)
        )
    else:
        pass_reasons.append("Stage-3 harness contains the required routing interfaces and static key map.")

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

    benchmark_evidence_path = base / "stage3_benchmark_evidence.json"
    try:
        benchmark_data = json.loads(benchmark_evidence_path.read_text())
    except json.JSONDecodeError as exc:
        fail_reasons.append(f"`stage3_benchmark_evidence.json` is invalid JSON: {exc}")
        benchmark_data = {}

    required_benchmark_keys = [
        "implementation_applied",
        "stage3_regression_support",
        "stage3_contract_boundary_approved",
        "promotion_recommendation",
        "promotion_path",
        "evidence_runs",
    ]
    missing_keys = [key for key in required_benchmark_keys if key not in benchmark_data]
    if missing_keys:
        fail_reasons.append(
            "`stage3_benchmark_evidence.json` is missing required keys: "
            + ", ".join(missing_keys)
        )
    elif benchmark_data["implementation_applied"] is not True:
        blocked_reasons.append("Stage-3 benchmark evidence exists, but routing is not yet marked as implemented.")
    elif benchmark_data["promotion_path"] != "C_gates_plus_primitives":
        fail_reasons.append("Stage 3 must promote on `C_gates_plus_primitives` because routing only affects primitive-enabled evaluation.")
    elif benchmark_data["stage3_regression_support"] is not True:
        blocked_reasons.append("Stage-3 regression evidence does not yet support promotion.")
    elif benchmark_data["stage3_contract_boundary_approved"] is not True:
        blocked_reasons.append("Stage-3 contract boundary is not yet approved.")
    elif benchmark_data["promotion_recommendation"] is not True:
        blocked_reasons.append("Stage-3 benchmark evidence does not yet recommend promotion.")
    elif not benchmark_data["evidence_runs"]:
        blocked_reasons.append("Stage-3 benchmark evidence has no recorded run.")
    else:
        pass_reasons.append("Benchmark evidence supports stage-3 promotion.")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


def _shadow_board_taxonomy_contract(project: str, _: Any) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "probability_dag.json",
        base / "frozen_stage4_candidate.md",
        base / "frozen_stage4_candidate_test_model.py",
        base / "frozen_stage4_candidate_dag.json",
        base / "frozen_stage4_candidate_meta.json",
        base / "stage4_benchmark_evidence.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required stage-4 artifact(s): {', '.join(missing)}"])

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    frozen_thesis = (base / "frozen_stage4_candidate.md").read_text()
    frozen_test_model = (base / "frozen_stage4_candidate_test_model.py").read_text()

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen stage-4 candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the current stage-4 candidate.")

    if not current_text.startswith(frozen_thesis):
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen stage-4 candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen stage-4 candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen stage-4 candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the current stage-4 candidate harness.")

    fixture_module_text = (
        Path(__file__).resolve().parent / "stage4_fixture_regression.py"
    ).read_text()
    shadow_board_text = (Path(__file__).resolve().parent / "shadow_board.py").read_text()

    harness_symbols = ["run_stage4_fixture_regression"]
    missing_harness_symbols = [symbol for symbol in harness_symbols if symbol not in test_model_text]
    if missing_harness_symbols:
        fail_reasons.append(
            "Stage-4 harness is missing required fixture regression interface(s): "
            + ", ".join(missing_harness_symbols)
        )
    else:
        pass_reasons.append("Stage-4 harness delegates to the fixture regression interface.")

    required_runtime_symbols = ["Stage2Handoff", "assign_shadow_board", "ShadowBoardRole"]
    missing_runtime_symbols = [
        symbol
        for symbol in required_runtime_symbols
        if symbol not in fixture_module_text and symbol not in shadow_board_text
    ]
    if missing_runtime_symbols:
        fail_reasons.append(
            "Stage-4 runtime is missing required typed handoff / board routing symbols: "
            + ", ".join(missing_runtime_symbols)
        )
    else:
        pass_reasons.append("Stage-4 runtime exposes the required typed handoff and board routing symbols.")

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

    summary_path = base / "stage4_fixture_regression_summary.json"
    fixture_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.ztare.validator.stage4_fixture_regression",
            "--json-out",
            str(summary_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    if fixture_proc.returncode != 0:
        fail_reasons.append(
            "Stage-4 typed-handoff fixture regression failed: "
            + (fixture_proc.stderr or fixture_proc.stdout).strip()
        )
    else:
        try:
            fixture_summary = json.loads(summary_path.read_text())
        except json.JSONDecodeError as exc:
            fail_reasons.append(f"`stage4_fixture_regression_summary.json` is invalid JSON: {exc}")
            fixture_summary = {}
        else:
            if fixture_summary.get("all_passed") is not True:
                fail_reasons.append("Stage-4 fixture regression did not pass all typed handoff cases.")
            else:
                pass_reasons.append("Stage-4 fixture regression supports promotion.")

    benchmark_evidence_path = base / "stage4_benchmark_evidence.json"
    try:
        benchmark_data = json.loads(benchmark_evidence_path.read_text())
    except json.JSONDecodeError as exc:
        fail_reasons.append(f"`stage4_benchmark_evidence.json` is invalid JSON: {exc}")
        benchmark_data = {}

    required_benchmark_keys = [
        "implementation_applied",
        "typed_handoff_wire_applied",
        "stage4_regression_support",
        "stage4_contract_boundary_approved",
        "promotion_recommendation",
        "promotion_path",
        "evidence_runs",
    ]
    missing_keys = [key for key in required_benchmark_keys if key not in benchmark_data]
    if missing_keys:
        fail_reasons.append(
            "`stage4_benchmark_evidence.json` is missing required keys: "
            + ", ".join(missing_keys)
        )
    elif benchmark_data["implementation_applied"] is not True:
        blocked_reasons.append("Stage-4 implementation is not yet marked as applied.")
    elif benchmark_data["typed_handoff_wire_applied"] is not True:
        blocked_reasons.append("Typed stage-2 handoff wiring is not yet marked as applied.")
    elif benchmark_data["promotion_path"] != "typed_handoff_fixture_contract":
        fail_reasons.append("Stage 4 must promote on the isolated `typed_handoff_fixture_contract` path.")
    elif benchmark_data["stage4_regression_support"] is not True:
        blocked_reasons.append("Stage-4 typed-handoff fixture evidence does not yet support promotion.")
    elif benchmark_data["stage4_contract_boundary_approved"] is not True:
        blocked_reasons.append("Stage-4 contract boundary is not yet approved.")
    elif benchmark_data["promotion_recommendation"] is not True:
        blocked_reasons.append("Stage-4 evidence does not yet recommend promotion.")
    elif not benchmark_data["evidence_runs"]:
        blocked_reasons.append("Stage-4 evidence has no recorded fixture run.")
    else:
        pass_reasons.append("Benchmark evidence supports stage-4 promotion.")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


def _information_yield_loop_break_contract(project: str, _: Any) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "probability_dag.json",
        base / "frozen_stage5_candidate.md",
        base / "frozen_stage5_candidate_test_model.py",
        base / "frozen_stage5_candidate_dag.json",
        base / "frozen_stage5_candidate_meta.json",
        base / "stage5_benchmark_evidence.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required stage-5 artifact(s): {', '.join(missing)}"])

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    frozen_thesis = (base / "frozen_stage5_candidate.md").read_text()
    frozen_test_model = (base / "frozen_stage5_candidate_test_model.py").read_text()

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen stage-5 candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the current stage-5 candidate.")

    if not current_text.startswith(frozen_thesis):
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen stage-5 candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen stage-5 candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen stage-5 candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the current stage-5 candidate harness.")

    fixture_module_text = (
        Path(__file__).resolve().parent / "stage5_fixture_regression.py"
    ).read_text()
    control_module_text = (
        Path(__file__).resolve().parent / "information_yield.py"
    ).read_text()

    harness_symbols = ["run_stage5_fixture_regression"]
    missing_harness_symbols = [symbol for symbol in harness_symbols if symbol not in test_model_text]
    if missing_harness_symbols:
        fail_reasons.append(
            "Stage-5 harness is missing required fixture regression interface(s): "
            + ", ".join(missing_harness_symbols)
        )
    else:
        pass_reasons.append("Stage-5 harness delegates to the fixture regression interface.")

    required_runtime_symbols = ["IterationSignal", "LoopControlAction", "evaluate_information_yield"]
    missing_runtime_symbols = [
        symbol
        for symbol in required_runtime_symbols
        if symbol not in fixture_module_text and symbol not in control_module_text
    ]
    if missing_runtime_symbols:
        fail_reasons.append(
            "Stage-5 runtime is missing required information-yield symbols: "
            + ", ".join(missing_runtime_symbols)
        )
    else:
        pass_reasons.append("Stage-5 runtime exposes the required information-yield symbols.")

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

    summary_path = base / "stage5_fixture_regression_summary.json"
    fixture_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.ztare.validator.stage5_fixture_regression",
            "--json-out",
            str(summary_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    if fixture_proc.returncode != 0:
        fail_reasons.append(
            "Stage-5 information-yield fixture regression failed: "
            + (fixture_proc.stderr or fixture_proc.stdout).strip()
        )
    else:
        try:
            fixture_summary = json.loads(summary_path.read_text())
        except json.JSONDecodeError as exc:
            fail_reasons.append(f"`stage5_fixture_regression_summary.json` is invalid JSON: {exc}")
            fixture_summary = {}
        else:
            if fixture_summary.get("all_passed") is not True:
                fail_reasons.append("Stage-5 fixture regression did not pass all loop-control cases.")
            else:
                pass_reasons.append("Stage-5 fixture regression supports promotion.")

    benchmark_evidence_path = base / "stage5_benchmark_evidence.json"
    try:
        benchmark_data = json.loads(benchmark_evidence_path.read_text())
    except json.JSONDecodeError as exc:
        fail_reasons.append(f"`stage5_benchmark_evidence.json` is invalid JSON: {exc}")
        benchmark_data = {}

    required_benchmark_keys = [
        "implementation_applied",
        "stage5_regression_support",
        "stage5_contract_boundary_approved",
        "promotion_recommendation",
        "promotion_path",
        "evidence_runs",
    ]
    missing_keys = [key for key in required_benchmark_keys if key not in benchmark_data]
    if missing_keys:
        fail_reasons.append(
            "`stage5_benchmark_evidence.json` is missing required keys: "
            + ", ".join(missing_keys)
        )
    elif benchmark_data["implementation_applied"] is not True:
        blocked_reasons.append("Stage-5 implementation is not yet marked as applied.")
    elif benchmark_data["promotion_path"] != "loop_control_fixture_contract":
        fail_reasons.append("Stage 5 must promote on the isolated `loop_control_fixture_contract` path.")
    elif benchmark_data["stage5_regression_support"] is not True:
        blocked_reasons.append("Stage-5 fixture evidence does not yet support promotion.")
    elif benchmark_data["stage5_contract_boundary_approved"] is not True:
        blocked_reasons.append("Stage-5 contract boundary is not yet approved.")
    elif benchmark_data["promotion_recommendation"] is not True:
        blocked_reasons.append("Stage-5 evidence does not yet recommend promotion.")
    elif not benchmark_data["evidence_runs"]:
        blocked_reasons.append("Stage-5 evidence has no recorded fixture run.")
    else:
        pass_reasons.append("Benchmark evidence supports stage-5 promotion.")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


def _cross_domain_transfer_enforcement_contract(project: str, _: Any) -> ContractResult:
    base = project_dir(project)
    required_paths = [
        base / "thesis.md",
        base / "current_iteration.md",
        base / "test_model.py",
        base / "probability_dag.json",
        base / "frozen_stage6_candidate.md",
        base / "frozen_stage6_candidate_test_model.py",
        base / "frozen_stage6_candidate_dag.json",
        base / "frozen_stage6_candidate_meta.json",
        base / "stage6_benchmark_evidence.json",
    ]
    missing = [str(path.relative_to(base)) for path in required_paths if not path.exists()]
    if missing:
        return ContractResult("fail", [f"Missing required stage-6 artifact(s): {', '.join(missing)}"])

    thesis_text = (base / "thesis.md").read_text()
    current_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    frozen_thesis = (base / "frozen_stage6_candidate.md").read_text()
    frozen_test_model = (base / "frozen_stage6_candidate_test_model.py").read_text()

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if thesis_text != frozen_thesis:
        fail_reasons.append("`thesis.md` no longer matches the frozen stage-6 candidate.")
    else:
        pass_reasons.append("`thesis.md` is frozen to the current stage-6 candidate.")

    if not current_text.startswith(frozen_thesis):
        fail_reasons.append("`current_iteration.md` has drifted away from the frozen stage-6 candidate.")
    else:
        pass_reasons.append("`current_iteration.md` is aligned with the frozen stage-6 candidate.")

    if test_model_text != frozen_test_model:
        fail_reasons.append("`test_model.py` no longer matches the frozen stage-6 candidate harness.")
    else:
        pass_reasons.append("`test_model.py` is frozen to the current stage-6 candidate harness.")

    fixture_module_text = (
        Path(__file__).resolve().parent / "stage6_fixture_regression.py"
    ).read_text()
    control_module_text = (
        Path(__file__).resolve().parent / "cross_domain_transfer.py"
    ).read_text()

    harness_symbols = ["run_stage6_fixture_regression"]
    missing_harness_symbols = [symbol for symbol in harness_symbols if symbol not in test_model_text]
    if missing_harness_symbols:
        fail_reasons.append(
            "Stage-6 harness is missing required fixture regression interface(s): "
            + ", ".join(missing_harness_symbols)
        )
    else:
        pass_reasons.append("Stage-6 harness delegates to the fixture regression interface.")

    required_runtime_symbols = [
        "TransferRequest",
        "TransferDecision",
        "TransferDecisionRecord",
        "TransferRequirement",
        "TransferReasonCode",
        "evaluate_transfer_request",
    ]
    missing_runtime_symbols = [
        symbol
        for symbol in required_runtime_symbols
        if symbol not in fixture_module_text and symbol not in control_module_text
    ]
    if missing_runtime_symbols:
        fail_reasons.append(
            "Stage-6 runtime is missing required transfer-enforcement symbols: "
            + ", ".join(missing_runtime_symbols)
        )
    else:
        pass_reasons.append("Stage-6 runtime exposes the required transfer-enforcement symbols.")

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

    summary_path = base / "stage6_fixture_regression_summary.json"
    fixture_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.ztare.validator.stage6_fixture_regression",
            "--json-out",
            str(summary_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    if fixture_proc.returncode != 0:
        fail_reasons.append(
            "Stage-6 cross-domain transfer fixture regression failed: "
            + (fixture_proc.stderr or fixture_proc.stdout).strip()
        )
    else:
        try:
            fixture_summary = json.loads(summary_path.read_text())
        except json.JSONDecodeError as exc:
            fail_reasons.append(f"`stage6_fixture_regression_summary.json` is invalid JSON: {exc}")
            fixture_summary = {}
        else:
            if fixture_summary.get("all_passed") is not True:
                fail_reasons.append("Stage-6 fixture regression did not pass all transfer-enforcement cases.")
            else:
                pass_reasons.append("Stage-6 fixture regression supports promotion.")

    benchmark_evidence_path = base / "stage6_benchmark_evidence.json"
    try:
        benchmark_data = json.loads(benchmark_evidence_path.read_text())
    except json.JSONDecodeError as exc:
        fail_reasons.append(f"`stage6_benchmark_evidence.json` is invalid JSON: {exc}")
        benchmark_data = {}

    required_benchmark_keys = [
        "implementation_applied",
        "stage6_regression_support",
        "stage6_contract_boundary_approved",
        "promotion_recommendation",
        "promotion_path",
        "evidence_runs",
    ]
    missing_keys = [key for key in required_benchmark_keys if key not in benchmark_data]
    if missing_keys:
        fail_reasons.append(
            "`stage6_benchmark_evidence.json` is missing required keys: "
            + ", ".join(missing_keys)
        )
    elif benchmark_data["implementation_applied"] is not True:
        blocked_reasons.append("Stage-6 implementation is not yet marked as applied.")
    elif benchmark_data["promotion_path"] != "cross_domain_transfer_fixture_contract":
        fail_reasons.append("Stage 6 must promote on the isolated `cross_domain_transfer_fixture_contract` path.")
    elif benchmark_data["stage6_regression_support"] is not True:
        blocked_reasons.append("Stage-6 fixture evidence does not yet support promotion.")
    elif benchmark_data["stage6_contract_boundary_approved"] is not True:
        blocked_reasons.append("Stage-6 contract boundary is not yet approved.")
    elif benchmark_data["promotion_recommendation"] is not True:
        blocked_reasons.append("Stage-6 evidence does not yet recommend promotion.")
    elif not benchmark_data["evidence_runs"]:
        blocked_reasons.append("Stage-6 evidence has no recorded fixture run.")
    else:
        pass_reasons.append("Benchmark evidence supports stage-6 promotion.")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons)
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons)
    return ContractResult("pass", pass_reasons)


CONTRACT_REGISTRY: dict[str, Callable[[str, Any], ContractResult]] = {
    "semantic_gate_stabilization_contract_v1": _semantic_gate_stabilization_contract,
    "load_bearing_hinge_extraction_contract_v1": _load_bearing_hinge_extraction_contract,
    "load_bearing_hinge_extraction_contract_stub": _load_bearing_hinge_extraction_contract,
    "primitive_routing_by_exploit_family_contract_v1": _primitive_routing_by_exploit_family_contract,
    "primitive_routing_by_exploit_family_contract_stub": _primitive_routing_by_exploit_family_contract,
    "shadow_board_taxonomy_contract_stub": _shadow_board_taxonomy_contract,
    "shadow_board_taxonomy_contract_v1": _shadow_board_taxonomy_contract,
    "information_yield_loop_break_contract_stub": _information_yield_loop_break_contract,
    "information_yield_loop_break_contract_v1": _information_yield_loop_break_contract,
    "cross_domain_transfer_enforcement_contract_stub": _cross_domain_transfer_enforcement_contract,
    "cross_domain_transfer_enforcement_contract_v1": _cross_domain_transfer_enforcement_contract,
}


DEFAULT_QUEUE = [
    {
        "name": "semantic_gate_stabilization",
        "item_number": 1,
        "priority": "P0",
        "contract_name": "semantic_gate_stabilization_contract_v1",
    },
    {
        "name": "load_bearing_hinge_extraction",
        "item_number": 2,
        "priority": "P0",
        "contract_name": "load_bearing_hinge_extraction_contract_stub",
    },
    {
        "name": "primitive_routing_by_exploit_family",
        "item_number": 3,
        "priority": "P0",
        "contract_name": "primitive_routing_by_exploit_family_contract_stub",
    },
    {
        "name": "shadow_board_fixed_taxonomy",
        "item_number": 4,
        "priority": "P1",
        "contract_name": "shadow_board_taxonomy_contract_v1",
    },
    {
        "name": "information_yield_loop_break",
        "item_number": 5,
        "priority": "P1",
        "contract_name": "information_yield_loop_break_contract_v1",
    },
    {
        "name": "cross_domain_transfer_enforcement",
        "item_number": 6,
        "priority": "P1",
        "contract_name": "cross_domain_transfer_enforcement_contract_v1",
    },
]


def project_dir(project: str) -> Path:
    return PROJECTS_DIR / project


def plan_path(project: str) -> Path:
    return project_dir(project) / "meta_runner_plan.json"


def state_path(project: str) -> Path:
    return project_dir(project) / "meta_runner_state.json"


def ensure_plan_exists(project: str) -> Path:
    path = plan_path(project)
    if not path.exists():
        path.write_text(json.dumps({"queue": DEFAULT_QUEUE}, indent=2) + "\n")
    return path


def ensure_state_exists(project: str) -> Path:
    path = state_path(project)
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "current_stage": 0,
                    "last_verdict": None,
                    "last_report": [],
                    "completed_stages": [],
                },
                indent=2,
            )
            + "\n"
        )
    return path


def load_runner(project: str) -> MetaRunner:
    p_path = ensure_plan_exists(project)
    s_path = ensure_state_exists(project)

    plan_data = json.loads(p_path.read_text())
    state_data = json.loads(s_path.read_text())

    current_stage = state_data.get("current_stage", 0)
    queue = [
        StageSpec(
            name=item["name"],
            item_number=item["item_number"],
            priority=item["priority"],
            contract_name=item["contract_name"],
            active=(idx == current_stage),
        )
        for idx, item in enumerate(plan_data.get("queue", []))
    ]
    state = MetaRunnerState(
        current_stage=current_stage,
        last_verdict=state_data.get("last_verdict"),
        last_report=state_data.get("last_report", []),
        completed_stages=state_data.get("completed_stages", []),
    )
    return MetaRunner(project=project, queue=queue, state=state, state_path=s_path, contracts=CONTRACT_REGISTRY)


def print_status(runner: MetaRunner) -> None:
    print("V4 Meta-Runner")
    print(f"Current stage index: {runner.state.current_stage}")
    print(f"Last verdict: {runner.state.last_verdict}")
    if runner.state.last_report:
        print("Last report:")
        for line in runner.state.last_report:
            print(f"- {line}")
    print(f"Completed stages: {', '.join(runner.state.completed_stages) if runner.state.completed_stages else 'none'}")
    print("")
    for idx, stage in enumerate(runner.queue):
        marker = "*" if idx == runner.state.current_stage else " "
        print(
            f"{marker} stage {stage.item_number}: {stage.name} "
            f"[{stage.priority}] contract={stage.contract_name}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V4 stage-gated meta-runner with real stage-1 contract checks."
    )
    parser.add_argument("--project", default="epistemic_engine_v4")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Show current queue and state.")
    subparsers.add_parser("run-current", help="Evaluate the current stage contract.")
    subparsers.add_parser("advance", help="Advance to the next stage after a pass verdict.")
    subparsers.add_parser("reset", help="Reset meta-runner state to stage 0.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    runner = load_runner(args.project)

    if args.command == "show":
        print_status(runner)
        return 0
    if args.command == "run-current":
        result = runner.run_stage()
        print(f"Current stage verdict: {result.verdict}")
        if result.reasons:
            for reason in result.reasons:
                print(f"- {reason}")
        return 0
    if args.command == "advance":
        runner.advance()
        print(f"Advanced to stage index {runner.state.current_stage}: {runner.current().name}")
        return 0
    if args.command == "reset":
        runner.reset()
        print("Meta-runner state reset to stage 0.")
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
