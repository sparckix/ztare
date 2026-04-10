from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from src.ztare.workspace.compile_evidence import (
    COMPILE_FAILURE_ARTIFACT,
    CompileEvidenceError,
    clear_compile_failure_artifact,
    compile_failure_payload,
    write_compile_failure_artifact,
)


def run_compile_evidence_fixture_regression() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / "workspace"
        project_dir = Path(tmpdir) / "project"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        error = CompileEvidenceError(
            "LLM call failed after 4 attempts: 503 UNAVAILABLE",
            phase="llm_call",
            model_family="gemini",
            model_id="gemini-2.5-flash",
            transient=True,
            status_code=503,
        )
        failure_path = write_compile_failure_artifact(
            workspace_dir=workspace_dir,
            project_dir=project_dir,
            mode="raw",
            model="gemini",
            error=error,
        )
        payload = json.loads(failure_path.read_text())
        payload_preview = compile_failure_payload(
            project_dir=project_dir,
            mode="raw",
            model="gemini",
            error=error,
        )

        clear_compile_failure_artifact(workspace_dir)

        cases = [
            {
                "case_id": "provider_outage_writes_fail_closed_artifact",
                "passed": (
                    failure_path.name == COMPILE_FAILURE_ARTIFACT
                    and payload.get("fail_closed") is True
                    and payload.get("transient") is True
                    and payload.get("status_code") == 503
                    and payload.get("phase") == "llm_call"
                    and payload.get("model_family") == "gemini"
                    and payload.get("model_id") == "gemini-2.5-flash"
                ),
            },
            {
                "case_id": "success_path_can_clear_stale_failure_artifact",
                "passed": (not failure_path.exists()),
            },
            {
                "case_id": "failure_payload_is_structured_without_traceback_dependency",
                "passed": (
                    payload_preview.get("error_type") == "CompileEvidenceError"
                    and "503 UNAVAILABLE" in payload_preview.get("message", "")
                ),
            },
        ]

    all_passed = all(case["passed"] for case in cases)
    return {
        "suite": "compile_evidence_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run compile evidence fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_compile_evidence_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Compile evidence fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
