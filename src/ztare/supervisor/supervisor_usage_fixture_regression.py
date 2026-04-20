from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.supervisor.supervisor_usage import extract_usage_telemetry


def run_supervisor_usage_fixture_regression() -> dict[str, object]:
    cases = []

    pretty_json_usage = extract_usage_telemetry(
        stdout_text='{\n  "usage": {\n    "model_name": "fixture-pretty",\n    "input_tokens": 900,\n    "output_tokens": 100\n  }\n}\n',
        stderr_text="",
        pricing_path=Path("/tmp/nonexistent_pricing.json"),
    )
    cases.append(
        {
            "case_id": "pretty_json_usage_is_extracted",
            "passed": (
                pretty_json_usage.telemetry_captured is True
                and pretty_json_usage.model_name == "fixture-pretty"
                and pretty_json_usage.input_tokens == 900
                and pretty_json_usage.output_tokens == 100
            ),
        }
    )

    json_usage = extract_usage_telemetry(
        stdout_text='{"usage":{"model_name":"fixture-model","input_tokens":1500,"output_tokens":250,"cache_creation_input_tokens":100,"cache_read_input_tokens":50}}\n',
        stderr_text="",
        pricing_path=Path("/tmp/nonexistent_pricing.json"),
    )
    cases.append(
        {
            "case_id": "json_usage_is_extracted_without_pricing",
            "passed": (
                json_usage.telemetry_captured is True
                and json_usage.model_name == "fixture-model"
                and json_usage.input_tokens == 1500
                and json_usage.output_tokens == 250
                and json_usage.estimated_cost_usd == 0.0
            ),
        }
    )

    claude_result_usage = extract_usage_telemetry(
        stdout_text=(
            '{"type":"result","total_cost_usd":0.76691955,'
            '"usage":{"input_tokens":23,"cache_creation_input_tokens":55127,'
            '"cache_read_input_tokens":1064781,"output_tokens":16046},'
            '"modelUsage":{"claude-sonnet-4-6":{"costUSD":0.76691955}}}'
        ),
        stderr_text="",
        pricing_path=Path("/tmp/nonexistent_pricing.json"),
    )
    cases.append(
        {
            "case_id": "claude_result_json_cost_is_extracted_directly",
            "passed": (
                claude_result_usage.telemetry_captured is True
                and claude_result_usage.model_name == "claude-sonnet-4-6"
                and claude_result_usage.input_tokens == 23
                and claude_result_usage.output_tokens == 16046
                and claude_result_usage.cache_creation_input_tokens == 55127
                and claude_result_usage.cache_read_input_tokens == 1064781
                and claude_result_usage.estimated_cost_usd == 0.76691955
            ),
        }
    )

    text_usage = extract_usage_telemetry(
        stdout_text="Model: fixture-model\nInput tokens: 4200\nOutput tokens: 800\n",
        stderr_text="",
        pricing_path=Path("/tmp/nonexistent_pricing.json"),
    )
    cases.append(
        {
            "case_id": "text_usage_fallback_is_extracted",
            "passed": (
                text_usage.telemetry_captured is True
                and text_usage.input_tokens == 4200
                and text_usage.output_tokens == 800
                and text_usage.model_name == "fixture-model"
            ),
        }
    )

    missing_usage = extract_usage_telemetry(
        stdout_text="normal prose only",
        stderr_text="",
        default_model_name="unknown-model",
        pricing_path=Path("/tmp/nonexistent_pricing.json"),
    )
    cases.append(
        {
            "case_id": "missing_usage_stays_disabled",
            "passed": (
                missing_usage.telemetry_captured is False
                and missing_usage.model_name == "unknown-model"
                and missing_usage.estimated_cost_usd == 0.0
            ),
        }
    )

    all_passed = all(case["passed"] for case in cases)
    return {
        "suite": "supervisor_usage_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor usage fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_usage_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor usage fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
