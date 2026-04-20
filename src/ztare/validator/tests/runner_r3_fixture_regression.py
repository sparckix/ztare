from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from src.ztare.validator.core.mutation_contract import (
    ClaimDeltaType,
    MutationArtifact,
    MutationDeclaration,
    MutationMismatchCode,
    MutationScopeDelta,
    MutationValidationRecord,
)
from src.ztare.validator.core.runner_selection import (
    CandidateScopeVerdict,
    evaluate_candidate_selection,
)


@dataclass(frozen=True)
class RunnerR3FixtureCase:
    case_id: str
    description: str
    candidate_score: int
    best_score_before: int
    mutation_validation: MutationValidationRecord | None
    scope_verdict: CandidateScopeVerdict
    scope_signals: tuple[str, ...]
    dynamic: bool
    debate_log_text: str
    expected_scope: CandidateScopeVerdict
    expected_admissible: bool
    expected_keep_best: bool
    expected_selected_as_best: bool


def build_runner_r3_fixture_cases() -> list[RunnerR3FixtureCase]:
    clean_validation = MutationValidationRecord(
        mismatch_code=MutationMismatchCode.CLEAN,
        declared_scope_delta=MutationScopeDelta.TEST_HARNESS,
        declared_claim_delta_type=ClaimDeltaType.NARROWING,
        declared_primitive_invoked=None,
        declared_touched_artifacts=(MutationArtifact.TEST_MODEL_PY,),
        actual_touched_artifacts=(MutationArtifact.TEST_MODEL_PY,),
        breadth_delta=-2,
        rationale="Clean declaration.",
    )
    return [
        RunnerR3FixtureCase(
            case_id="bridge_in_scope_improvement",
            description="An in-scope bridge candidate with both attacker logs and a higher score should be selected.",
            candidate_score=100,
            best_score_before=40,
            mutation_validation=clean_validation,
            scope_verdict=CandidateScopeVerdict.IN_SCOPE,
            scope_signals=(),
            dynamic=True,
            debate_log_text="## Attacker: SELF_REFERENCE_AUDITOR\nx\n## Attacker: MANUAL_REVIEW_ARBITER\ny\n",
            expected_scope=CandidateScopeVerdict.IN_SCOPE,
            expected_admissible=True,
            expected_keep_best=False,
            expected_selected_as_best=True,
        ),
        RunnerR3FixtureCase(
            case_id="bridge_out_of_scope_grounding_signal_report",
            description="A bridge mutation that introduces GroundingSignalReport should be rejected as out of scope.",
            candidate_score=100,
            best_score_before=40,
            mutation_validation=clean_validation,
            scope_verdict=CandidateScopeVerdict.OUT_OF_SCOPE,
            scope_signals=("forbidden stage-specific mechanism introduced",),
            dynamic=True,
            debate_log_text="## Attacker: SELF_REFERENCE_AUDITOR\nx\n## Attacker: MANUAL_REVIEW_ARBITER\ny\n",
            expected_scope=CandidateScopeVerdict.OUT_OF_SCOPE,
            expected_admissible=False,
            expected_keep_best=True,
            expected_selected_as_best=False,
        ),
        RunnerR3FixtureCase(
            case_id="bridge_out_of_scope_falsification_contract",
            description="A bridge mutation that pivots to FalsificationContract should be rejected as out of scope.",
            candidate_score=90,
            best_score_before=80,
            mutation_validation=clean_validation,
            scope_verdict=CandidateScopeVerdict.OUT_OF_SCOPE,
            scope_signals=("forbidden stage-specific mechanism introduced",),
            dynamic=True,
            debate_log_text="## Attacker: SELF_REFERENCE_AUDITOR\nx\n## Attacker: MANUAL_REVIEW_ARBITER\ny\n",
            expected_scope=CandidateScopeVerdict.OUT_OF_SCOPE,
            expected_admissible=False,
            expected_keep_best=True,
            expected_selected_as_best=False,
        ),
        RunnerR3FixtureCase(
            case_id="in_scope_but_not_better",
            description="An admissible in-scope candidate that does not improve score should keep the current best.",
            candidate_score=70,
            best_score_before=85,
            mutation_validation=clean_validation,
            scope_verdict=CandidateScopeVerdict.IN_SCOPE,
            scope_signals=(),
            dynamic=True,
            debate_log_text="## Attacker: SELF_REFERENCE_AUDITOR\nx\n## Attacker: MANUAL_REVIEW_ARBITER\ny\n",
            expected_scope=CandidateScopeVerdict.IN_SCOPE,
            expected_admissible=True,
            expected_keep_best=True,
            expected_selected_as_best=False,
        ),
        RunnerR3FixtureCase(
            case_id="dynamic_log_missing_second_attacker",
            description="A dynamic run that loses one attacker record should be inadmissible.",
            candidate_score=100,
            best_score_before=40,
            mutation_validation=clean_validation,
            scope_verdict=CandidateScopeVerdict.IN_SCOPE,
            scope_signals=(),
            dynamic=True,
            debate_log_text="## Attacker: SELF_REFERENCE_AUDITOR\nx\n",
            expected_scope=CandidateScopeVerdict.IN_SCOPE,
            expected_admissible=False,
            expected_keep_best=True,
            expected_selected_as_best=False,
        ),
    ]


def run_runner_r3_fixture_regression() -> dict[str, object]:
    cases = build_runner_r3_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = evaluate_candidate_selection(
            candidate_score=case.candidate_score,
            best_score_before=case.best_score_before,
            mutation_validation=case.mutation_validation,
            scope_verdict=case.scope_verdict,
            scope_signals=case.scope_signals,
            dynamic=case.dynamic,
            debate_log_text=case.debate_log_text,
        )
        second = evaluate_candidate_selection(
            candidate_score=case.candidate_score,
            best_score_before=case.best_score_before,
            mutation_validation=case.mutation_validation,
            scope_verdict=case.scope_verdict,
            scope_signals=case.scope_signals,
            dynamic=case.dynamic,
            debate_log_text=case.debate_log_text,
        )
        passed = (
            first.scope_verdict == case.expected_scope
            and first.candidate_admissible == case.expected_admissible
            and first.keep_best_in_scope == case.expected_keep_best
            and first.selected_as_best == case.expected_selected_as_best
            and first == second
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "expected_scope": case.expected_scope.value,
                "actual_scope": first.scope_verdict.value,
                "expected_admissible": case.expected_admissible,
                "actual_admissible": first.candidate_admissible,
                "expected_keep_best": case.expected_keep_best,
                "actual_keep_best": first.keep_best_in_scope,
                "expected_selected_as_best": case.expected_selected_as_best,
                "actual_selected_as_best": first.selected_as_best,
                "minority_attack_preserved": first.minority_attack_preserved,
                "passed": passed,
            }
        )

    return {
        "suite": "runner_r3_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated runner R3 selection-contract fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_runner_r3_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Runner R3 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_scope']} / "
            f"keep_best={result['expected_keep_best']} -> {result['actual_scope']} / "
            f"keep_best={result['actual_keep_best']}"
        )
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
