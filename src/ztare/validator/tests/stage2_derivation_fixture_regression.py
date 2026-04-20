from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from src.ztare.validator.core.stage2_derivation import (
    DerivationMismatchClass,
    evaluate_derivation_seam,
)


@dataclass(frozen=True)
class Stage2DerivationFixtureCase:
    case_id: str
    description: str
    thesis_text: str
    evidence_text: str
    test_model_text: str
    expected_mismatch: DerivationMismatchClass
    expected_passed: bool


def build_stage2_derivation_fixture_cases() -> list[Stage2DerivationFixtureCase]:
    return [
        Stage2DerivationFixtureCase(
            case_id="fabricated_safe_harbor_anchor",
            description="A mutator-authored local disclaimer without evidence support must fail closed even if a code pointer exists.",
            thesis_text=(
                "This is a bounded local component with safe harbor discipline. "
                "It only affects one local scope and does not affect upstream truthfulness."
            ),
            evidence_text="This note only lists TODO items and contains no support for a local-scope disclaimer.",
            test_model_text=(
                "def some_func(value: int) -> int:\n"
                "    return value + 1\n"
            ),
            expected_mismatch=DerivationMismatchClass.FABRICATED_SAFE_HARBOR_ANCHOR,
            expected_passed=False,
        ),
        Stage2DerivationFixtureCase(
            case_id="contradicted_scope_disclaimer",
            description="A local-scope disclaimer contradicted by whole-system evidence must fail closed.",
            thesis_text=(
                "This is a safe harbor local scope component. "
                "It only affects one bounded component and does not affect the wider system."
            ),
            evidence_text=(
                "Observed behavior propagates across all layers and changes whole system routing decisions."
            ),
            test_model_text="",
            expected_mismatch=DerivationMismatchClass.CONTRADICTED_SCOPE_DISCLAIMER,
            expected_passed=False,
        ),
        Stage2DerivationFixtureCase(
            case_id="genuinely_grounded_safe_harbor",
            description="A supported local-scope disclaimer with an executable harness should pass cleanly.",
            thesis_text=(
                "This is a safe harbor bounded local component. "
                "It only affects one local scope and does not affect upstream truthfulness."
            ),
            evidence_text=(
                "Evidence confirms the safe harbor claim: this bounded local path only affects one local scope."
            ),
            test_model_text=(
                "def route_label(token: str) -> str:\n"
                "    return 'allow' if token == 'ok' else 'review'\n\n"
                "assert route_label('ok') == 'allow'\n"
            ),
            expected_mismatch=DerivationMismatchClass.CLEAN,
            expected_passed=True,
        ),
        Stage2DerivationFixtureCase(
            case_id="unresolved_generic_no_disclaimer",
            description="A generic weakest-point claim with no disclaimer and no grounding pointer must fail closed.",
            thesis_text=(
                "This is a generic weakest-point note about a possible issue in the architecture."
            ),
            evidence_text="",
            test_model_text="",
            expected_mismatch=DerivationMismatchClass.UNRESOLVED_GENERIC,
            expected_passed=False,
        ),
    ]


def run_stage2_derivation_fixture_regression() -> dict[str, object]:
    cases = build_stage2_derivation_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = evaluate_derivation_seam(
            thesis_text=case.thesis_text,
            evidence_text=case.evidence_text,
            test_model_text=case.test_model_text,
        )
        second = evaluate_derivation_seam(
            thesis_text=case.thesis_text,
            evidence_text=case.evidence_text,
            test_model_text=case.test_model_text,
        )
        passed = (
            first.mismatch_class == case.expected_mismatch
            and first.passed == case.expected_passed
            and first == second
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_mismatch": case.expected_mismatch.value,
                "actual_mismatch": first.mismatch_class.value,
                "expected_passed": case.expected_passed,
                "actual_passed": first.passed,
                "alignment_status": first.alignment_status.value,
                "grounding_pointer_source": first.grounding_pointer_source,
                "deterministic_repeat_match": first == second,
                "passed": passed,
            }
        )

    return {
        "suite": "stage2_derivation_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the stage-2 derivation seam fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_stage2_derivation_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Stage 2 derivation fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_mismatch']} / "
            f"{result['expected_passed']} -> {result['actual_mismatch']} / {result['actual_passed']}"
        )

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
