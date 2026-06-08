from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.ztare.common.paths import PROJECTS_DIR
# Shared sandboxed-python execution (the ONE canonical home; leanmill uses its guarded-script path, autoresearch
# the trusted-file/module path) — stop re-implementing the subprocess wrapper. Behaviour-identical to the prior
# inline calls (same cwd, capture_output, text, no timeout).
from src.ztare.common.sandboxed_python import (run_python_file as _shared_run_python_file,
                                               run_python_module as _shared_run_python_module)
from src.ztare.gates.bridge_scope_contract import BridgeScopeMismatchCode, evaluate_bridge_scope
from src.ztare.validator.core.mutation_contract import MutationDeclaration, parse_mutation_declaration


def _run_python_file(path: Path) -> subprocess.CompletedProcess[str]:
    return _shared_run_python_file(path, cwd=path.parents[2])


def _run_python_module(module_name: str) -> subprocess.CompletedProcess[str]:
    return _shared_run_python_module(module_name, cwd=Path(__file__).resolve().parents[3])


def evaluate_bridge_discovery(project: str) -> dict[str, object]:
    base = PROJECTS_DIR / project
    thesis_text = (base / "current_iteration.md").read_text()
    test_model_text = (base / "test_model.py").read_text()
    workspace_dir = base / "workspace"

    declaration: MutationDeclaration | None = None
    declaration_path = workspace_dir / "latest_mutation_declaration.json"
    if declaration_path.exists():
        declaration = parse_mutation_declaration(json.loads(declaration_path.read_text()))

    reasons: list[str] = []
    if declaration is not None:
        scope_result = evaluate_bridge_scope(
            declaration,
            thesis_text=thesis_text,
            python_code=test_model_text,
        )
        if scope_result.mismatch_code != BridgeScopeMismatchCode.CLEAN:
            reasons.append(
                f"Bridge scope contract failed: {scope_result.mismatch_code.value} — {scope_result.rationale}"
            )
            return {
                "score": 0,
                "weakest_point": reasons[0],
                "scope_result": {
                    "mismatch_code": scope_result.mismatch_code.value,
                    "scope_signals": list(scope_result.scope_signals),
                },
            }

    compile_proc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(base / "test_model.py")],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        return {
            "score": 0,
            "weakest_point": f"Bridge test_model failed to compile: {compile_proc.stderr.strip()}",
        }

    test_proc = _run_python_file(base / "test_model.py")
    if test_proc.returncode != 0:
        return {
            "score": 0,
            "weakest_point": f"Bridge test_model failed at runtime: {(test_proc.stderr or test_proc.stdout).strip()}",
        }

    fixture_proc = _run_python_module("src.ztare.validator.core.stage24_bridge_fixture_regression")
    if fixture_proc.returncode != 0:
        return {
            "score": 0,
            "weakest_point": "Bridge fixture regression failed.",
        }

    return {
        "score": 100,
        "weakest_point": "Bridge discovery evaluator found no contract-local failure.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the current bridge project under the bridge-local discovery contract.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    result = evaluate_bridge_discovery(args.project)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n")

    print(json.dumps(result, indent=2))
    return 0 if result["score"] == 100 else 1


if __name__ == "__main__":
    raise SystemExit(main())
