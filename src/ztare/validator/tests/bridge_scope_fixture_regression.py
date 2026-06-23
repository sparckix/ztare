from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from ztare.gates.bridge_scope_contract import (
    BridgeScopeMismatchCode,
    evaluate_bridge_scope,
)
from ztare.validator.core.mutation_contract import (
    ClaimDeltaType,
    MutationArtifact,
    MutationDeclaration,
    MutationScopeDelta,
)


@dataclass(frozen=True)
class BridgeScopeFixtureCase:
    case_id: str
    declaration: MutationDeclaration
    thesis_text: str
    python_code: str
    expected_mismatch: BridgeScopeMismatchCode


def build_bridge_scope_fixture_cases() -> list[BridgeScopeFixtureCase]:
    return [
        BridgeScopeFixtureCase(
            case_id="clean_bridge_harness_narrowing",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.TEST_HARNESS,
                claim_delta_type=ClaimDeltaType.NARROWING,
                primitive_invoked=None,
                touched_artifacts=(MutationArtifact.THESIS_MD, MutationArtifact.TEST_MODEL_PY),
            ),
            thesis_text="Keep the bridge as an audited pre-check over BridgeRecord.",
            python_code="print('bridge fixture only')",
            expected_mismatch=BridgeScopeMismatchCode.CLEAN,
        ),
        BridgeScopeFixtureCase(
            case_id="invalid_runner_runtime_touch",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.MULTI_ARTIFACT,
                claim_delta_type=ClaimDeltaType.REFRAMING,
                primitive_invoked=None,
                touched_artifacts=(MutationArtifact.THESIS_MD, MutationArtifact.RUNNER_RUNTIME),
            ),
            thesis_text="Bridge remains local.",
            python_code="print('bridge only')",
            expected_mismatch=BridgeScopeMismatchCode.INVALID_ARTIFACT_SET,
        ),
        BridgeScopeFixtureCase(
            case_id="invalid_scope_delta_rubric_interface",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.RUBRIC_INTERFACE,
                claim_delta_type=ClaimDeltaType.REFRAMING,
                primitive_invoked=None,
                touched_artifacts=(MutationArtifact.RUBRIC_JSON,),
            ),
            thesis_text="Bridge remains local.",
            python_code="print('bridge only')",
            expected_mismatch=BridgeScopeMismatchCode.INVALID_SCOPE_DELTA,
        ),
        BridgeScopeFixtureCase(
            case_id="non_bridge_mechanism_falsification_contract",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.TEST_HARNESS,
                claim_delta_type=ClaimDeltaType.REFRAMING,
                primitive_invoked=None,
                touched_artifacts=(MutationArtifact.THESIS_MD, MutationArtifact.TEST_MODEL_PY),
            ),
            thesis_text="Introduce FalsificationContract for bridge scoring.",
            python_code="class FalsificationContract: pass",
            expected_mismatch=BridgeScopeMismatchCode.NON_BRIDGE_MECHANISM,
        ),
    ]


def run_bridge_scope_fixture_regression() -> dict[str, object]:
    cases = build_bridge_scope_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True
    for case in cases:
        first = evaluate_bridge_scope(
            case.declaration,
            thesis_text=case.thesis_text,
            python_code=case.python_code,
        )
        second = evaluate_bridge_scope(
            case.declaration,
            thesis_text=case.thesis_text,
            python_code=case.python_code,
        )
        passed = first.mismatch_code == case.expected_mismatch and first == second
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "expected_mismatch": case.expected_mismatch.value,
                "actual_mismatch": first.mismatch_code.value,
                "scope_signals": list(first.scope_signals),
                "passed": passed,
            }
        )
    return {
        "suite": "bridge_scope_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated bridge scope fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_bridge_scope_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Bridge scope fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_mismatch']} -> "
            f"{result['actual_mismatch']}"
        )
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
