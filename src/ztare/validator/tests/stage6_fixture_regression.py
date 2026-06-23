from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ztare.validator.core.cross_domain_transfer import (
    TransferDecision,
    TransferDecisionRecord,
    TransferReasonCode,
    TransferRequest,
    evaluate_transfer_request,
)


@dataclass(frozen=True)
class Stage6FixtureCase:
    case_id: str
    description: str
    request: TransferRequest
    expected_decision: TransferDecision
    expected_reason_code: TransferReasonCode


def build_stage6_fixture_cases() -> list[Stage6FixtureCase]:
    return [
        Stage6FixtureCase(
            case_id="allow_fully_grounded_transfer",
            description="Fully grounded target-domain transfer should be allowed.",
            request=TransferRequest(
                source_domain="finance",
                target_domain="oncology",
                mechanism_restated_in_target_language=True,
                target_domain_variables_identified=True,
                explicit_break_case_provided=True,
                target_domain_falsification_check_present=True,
            ),
            expected_decision=TransferDecision.ALLOW,
            expected_reason_code=TransferReasonCode.ALLOW_ALL_REQUIREMENTS_MET,
        ),
        Stage6FixtureCase(
            case_id="suppress_missing_restatement",
            description="Missing target-language restatement should suppress transfer.",
            request=TransferRequest(
                source_domain="finance",
                target_domain="oncology",
                mechanism_restated_in_target_language=False,
                target_domain_variables_identified=True,
                explicit_break_case_provided=True,
                target_domain_falsification_check_present=True,
            ),
            expected_decision=TransferDecision.SUPPRESS,
            expected_reason_code=TransferReasonCode.SUPPRESS_MISSING_REQUIREMENTS,
        ),
        Stage6FixtureCase(
            case_id="suppress_missing_target_variables",
            description="Missing target-domain variable mapping should suppress transfer.",
            request=TransferRequest(
                source_domain="finance",
                target_domain="oncology",
                mechanism_restated_in_target_language=True,
                target_domain_variables_identified=False,
                explicit_break_case_provided=True,
                target_domain_falsification_check_present=True,
            ),
            expected_decision=TransferDecision.SUPPRESS,
            expected_reason_code=TransferReasonCode.SUPPRESS_MISSING_REQUIREMENTS,
        ),
        Stage6FixtureCase(
            case_id="suppress_missing_break_case",
            description="Missing break case should suppress transfer.",
            request=TransferRequest(
                source_domain="finance",
                target_domain="oncology",
                mechanism_restated_in_target_language=True,
                target_domain_variables_identified=True,
                explicit_break_case_provided=False,
                target_domain_falsification_check_present=True,
            ),
            expected_decision=TransferDecision.SUPPRESS,
            expected_reason_code=TransferReasonCode.SUPPRESS_MISSING_REQUIREMENTS,
        ),
        Stage6FixtureCase(
            case_id="suppress_missing_falsification",
            description="Missing target-domain falsification should suppress transfer.",
            request=TransferRequest(
                source_domain="finance",
                target_domain="oncology",
                mechanism_restated_in_target_language=True,
                target_domain_variables_identified=True,
                explicit_break_case_provided=True,
                target_domain_falsification_check_present=False,
            ),
            expected_decision=TransferDecision.SUPPRESS,
            expected_reason_code=TransferReasonCode.SUPPRESS_MISSING_REQUIREMENTS,
        ),
        Stage6FixtureCase(
            case_id="manual_review_unresolved_stage24_bridge",
            description="Unresolved Stage 2->4 bridge dependency should route to manual review.",
            request=TransferRequest(
                source_domain="finance",
                target_domain="oncology",
                mechanism_restated_in_target_language=True,
                target_domain_variables_identified=True,
                explicit_break_case_provided=True,
                target_domain_falsification_check_present=True,
                requires_stage24_bridge=True,
                stage24_bridge_hardened=False,
            ),
            expected_decision=TransferDecision.MANUAL_REVIEW,
            expected_reason_code=TransferReasonCode.MANUAL_REVIEW_STAGE24_BRIDGE,
        ),
    ]


def _serialize_record(record: TransferDecisionRecord) -> dict[str, object]:
    return {
        "decision": record.decision.value,
        "reason_code": record.reason_code.value,
        "source_domain": record.source_domain,
        "target_domain": record.target_domain,
        "missing_requirements": [item.value for item in record.missing_requirements],
        "requires_stage24_bridge": record.requires_stage24_bridge,
        "stage24_bridge_hardened": record.stage24_bridge_hardened,
    }


def run_stage6_fixture_regression() -> dict[str, object]:
    cases = build_stage6_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = evaluate_transfer_request(case.request)
        second = evaluate_transfer_request(case.request)
        passed = (
            first.decision == case.expected_decision
            and first.reason_code == case.expected_reason_code
            and first == second
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_decision": case.expected_decision.value,
                "expected_reason_code": case.expected_reason_code.value,
                "actual": _serialize_record(first),
                "deterministic_repeat_match": first == second,
                "passed": passed,
                "request": asdict(case.request),
            }
        )

    return {
        "suite": "stage6_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated stage-6 cross-domain transfer fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_stage6_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Stage 6 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_decision']} / "
            f"{result['expected_reason_code']} -> {result['actual']['decision']} / "
            f"{result['actual']['reason_code']}"
        )

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
