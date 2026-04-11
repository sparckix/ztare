from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from src.ztare.validator.mutation_suite_guard import (
    NO_SUITE_SENTINEL,
    validate_python_suite_candidate,
)


@dataclass(frozen=True)
class SuiteGuardCase:
    case_id: str
    python_code: str | None
    should_pass: bool


def build_suite_guard_cases() -> list[SuiteGuardCase]:
    return [
        SuiteGuardCase(
            case_id="valid_minimal_suite",
            python_code="def test_smoke():\n    assert True\n",
            should_pass=True,
        ),
        SuiteGuardCase(
            case_id="missing_suite_block",
            python_code=None,
            should_pass=False,
        ),
        SuiteGuardCase(
            case_id="empty_suite_block",
            python_code="   \n",
            should_pass=False,
        ),
        SuiteGuardCase(
            case_id="sentinel_suite_block",
            python_code=NO_SUITE_SENTINEL,
            should_pass=False,
        ),
    ]


def run_suite_guard_fixture_regression() -> dict[str, object]:
    cases = build_suite_guard_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        try:
            validate_python_suite_candidate(case.python_code)
            actual_pass = True
            error = ""
        except Exception as exc:
            actual_pass = False
            error = str(exc)
        passed = actual_pass == case.should_pass
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "should_pass": case.should_pass,
                "actual_pass": actual_pass,
                "passed": passed,
                "error": error,
            }
        )

    return {
        "suite": "runner_r1_suite_guard_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for r in results if r["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the R1 no-suite guard fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_suite_guard_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Runner R1 suite-guard regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        verdict = "accept" if result["actual_pass"] else "reject"
        print(f"  {status} {result['case_id']}: expected {result['should_pass']} -> {verdict}")
        if result["error"]:
            print(f"       error: {result['error']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
