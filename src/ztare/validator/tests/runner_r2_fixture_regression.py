from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from src.ztare.validator.committees.committee_instantiation import instantiate_fixed_committee


ROLE_DEFINITIONS = {
    "SELF_REFERENCE_AUDITOR": {
        "role": "SELF_REFERENCE_AUDITOR",
        "persona": "Attacks self-certifying future-state reasoning.",
        "focus_area": "Detect thesis-authored thresholds and non-independent falsification.",
    },
    "MANUAL_REVIEW_ARBITER": {
        "role": "MANUAL_REVIEW_ARBITER",
        "persona": "Fails closed on ambiguity.",
        "focus_area": "Surface ambiguity rather than invent confidence.",
    },
    "SAFE_HARBOR_AUDITOR": {
        "role": "SAFE_HARBOR_AUDITOR",
        "persona": "Audits bounded local contracts.",
        "focus_area": "Verify local mapping scope and local fail-closed behavior.",
    },
}


@dataclass(frozen=True)
class RunnerR2FixtureCase:
    case_id: str
    role_keys: tuple[str, ...]
    expected_roles: tuple[str, ...]


def build_runner_r2_fixture_cases() -> list[RunnerR2FixtureCase]:
    return [
        RunnerR2FixtureCase(
            case_id="self_reference_with_reserve",
            role_keys=("SELF_REFERENCE_AUDITOR", "MANUAL_REVIEW_ARBITER"),
            expected_roles=("SELF_REFERENCE_AUDITOR", "MANUAL_REVIEW_ARBITER"),
        ),
        RunnerR2FixtureCase(
            case_id="safe_harbor_with_reserve",
            role_keys=("SAFE_HARBOR_AUDITOR", "MANUAL_REVIEW_ARBITER"),
            expected_roles=("SAFE_HARBOR_AUDITOR", "MANUAL_REVIEW_ARBITER"),
        ),
        RunnerR2FixtureCase(
            case_id="arbiter_only",
            role_keys=("MANUAL_REVIEW_ARBITER",),
            expected_roles=("MANUAL_REVIEW_ARBITER",),
        ),
    ]


def run_runner_r2_fixture_regression() -> dict[str, object]:
    cases = build_runner_r2_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first_committee, first_record = instantiate_fixed_committee(
            profile_source="fixed_catalog_test",
            role_keys=case.role_keys,
            role_definitions=ROLE_DEFINITIONS,
        )
        second_committee, second_record = instantiate_fixed_committee(
            profile_source="fixed_catalog_test",
            role_keys=case.role_keys,
            role_definitions=ROLE_DEFINITIONS,
        )
        actual_roles = tuple(item["role"] for item in first_committee)
        passed = (
            actual_roles == case.expected_roles
            and first_committee == second_committee
            and first_record == second_record
            and first_record.num_roles == len(case.role_keys)
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "expected_roles": list(case.expected_roles),
                "actual_roles": list(actual_roles),
                "committee_digest": first_record.committee_digest,
                "passed": passed,
            }
        )

    return {
        "suite": "runner_r2_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated runner R2 committee-instantiation fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_runner_r2_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Runner R2 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_roles']} -> "
            f"{result['actual_roles']}"
        )
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
