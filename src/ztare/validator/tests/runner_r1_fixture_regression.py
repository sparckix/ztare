from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from ztare.validator.core.mutation_contract import (
    ClaimDeltaType,
    MutationArtifact,
    MutationDeclaration,
    MutationMismatchCode,
    MutationScopeDelta,
    ThesisControlMode,
    evaluate_mutation_declaration,
    parse_mutation_declaration,
)


APPROVED_PRIMITIVE_KEYS = (
    "self_referential_falsification",
    "cooked_books",
    "float_masking",
    "perfect_mirroring_simulation",
    "unidirectional_decay",
    "missing_falsification_suite",
    "domain_leakage",
    "dimensional_error",
)


@dataclass(frozen=True)
class RunnerR1FixtureCase:
    case_id: str
    description: str
    declaration: MutationDeclaration
    changed_paths: tuple[str, ...]
    before_text: str
    after_text: str
    expected_mismatch: MutationMismatchCode


def build_runner_r1_fixture_cases() -> list[RunnerR1FixtureCase]:
    return [
        RunnerR1FixtureCase(
            case_id="clean_thesis_only_narrowing",
            description="A thesis-only narrowing should pass when only thesis/current files changed and breadth decreases.",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.THESIS_ONLY,
                claim_delta_type=ClaimDeltaType.NARROWING,
                primitive_invoked=None,
                touched_artifacts=(
                    MutationArtifact.THESIS_MD,
                    MutationArtifact.CURRENT_ITERATION_MD,
                ),
            ),
            changed_paths=("projects/sample/thesis.md", "projects/sample/current_iteration.md"),
            before_text="This ensures whole-system stability and end-to-end protection.",
            after_text="This is a bounded local component and does not claim whole-system protection.",
            expected_mismatch=MutationMismatchCode.CLEAN,
        ),
        RunnerR1FixtureCase(
            case_id="undeclared_harness_touch",
            description="A mutator that declares thesis-only scope but edits the harness should be flagged.",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.THESIS_ONLY,
                claim_delta_type=ClaimDeltaType.REFRAMING,
                primitive_invoked=None,
                touched_artifacts=(MutationArtifact.THESIS_MD,),
            ),
            changed_paths=("projects/sample/thesis.md", "projects/sample/test_model.py"),
            before_text="Bounded local parser.",
            after_text="Bounded local parser with clearer wording.",
            expected_mismatch=MutationMismatchCode.UNDECLARED_ARTIFACT_BREADTH,
        ),
        RunnerR1FixtureCase(
            case_id="invalid_primitive_key",
            description="A primitive declaration outside the approved index should be rejected.",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.TEST_HARNESS,
                claim_delta_type=ClaimDeltaType.REFRAMING,
                primitive_invoked="invented_magic_primitive",
                touched_artifacts=(MutationArtifact.TEST_MODEL_PY,),
            ),
            changed_paths=("projects/sample/test_model.py",),
            before_text="Bounded local parser.",
            after_text="Bounded local parser with one extra check.",
            expected_mismatch=MutationMismatchCode.INVALID_PRIMITIVE_DECLARATION,
        ),
        RunnerR1FixtureCase(
            case_id="claim_delta_scope_conflict",
            description="Declaring narrowing while adding broad whole-system language should be flagged.",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.THESIS_ONLY,
                claim_delta_type=ClaimDeltaType.NARROWING,
                primitive_invoked=None,
                touched_artifacts=(MutationArtifact.THESIS_MD,),
            ),
            changed_paths=("projects/sample/thesis.md",),
            before_text="This component routes one local token to one local action.",
            after_text="This component ensures whole-system stability, guarantees completeness, and provides end-to-end protection.",
            expected_mismatch=MutationMismatchCode.CLAIM_DELTA_SCOPE_CONFLICT,
        ),
        RunnerR1FixtureCase(
            case_id="clean_multi_artifact_widening",
            description="A declared multi-artifact widening should remain allowed if breadth and touches match.",
            declaration=MutationDeclaration(
                scope_delta=MutationScopeDelta.MULTI_ARTIFACT,
                claim_delta_type=ClaimDeltaType.WIDENING,
                thesis_control_mode=ThesisControlMode.ROTATE_ORTHOGONAL_THESIS,
                primitive_invoked="domain_leakage",
                touched_artifacts=(
                    MutationArtifact.THESIS_MD,
                    MutationArtifact.TEST_MODEL_PY,
                    MutationArtifact.EVIDENCE_TXT,
                ),
            ),
            changed_paths=(
                "projects/sample/thesis.md",
                "projects/sample/test_model.py",
                "projects/sample/evidence.txt",
            ),
            before_text="This is a bounded local component.",
            after_text="This is a bounded local component with a broader whole-system guarantee.",
            expected_mismatch=MutationMismatchCode.CLEAN,
        ),
    ]


def run_runner_r1_fixture_regression() -> dict[str, object]:
    cases = build_runner_r1_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = evaluate_mutation_declaration(
            case.declaration,
            case.changed_paths,
            before_text=case.before_text,
            after_text=case.after_text,
            approved_primitive_keys=APPROVED_PRIMITIVE_KEYS,
        )
        second = evaluate_mutation_declaration(
            case.declaration,
            case.changed_paths,
            before_text=case.before_text,
            after_text=case.after_text,
            approved_primitive_keys=APPROVED_PRIMITIVE_KEYS,
        )
        passed = first.mismatch_code == case.expected_mismatch and first == second
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_mismatch": case.expected_mismatch.value,
                "actual_mismatch": first.mismatch_code.value,
                "breadth_delta": first.breadth_delta,
                "declared_scope_delta": first.declared_scope_delta.value,
                "actual_touched_artifacts": [item.value for item in first.actual_touched_artifacts],
                "deterministic_repeat_match": first == second,
                "passed": passed,
            }
        )

    return {
        "suite": "runner_r1_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def _selftest_parse_thesis_control_mode() -> None:
    legacy = parse_mutation_declaration(
        {
            "scope_delta": "THESIS_ONLY",
            "claim_delta_type": "REFRAMING",
            "primitive_invoked": None,
            "touched_artifacts": ["thesis.md"],
        }
    )
    assert legacy.thesis_control_mode == ThesisControlMode.EXPLOIT_CURRENT_THESIS

    explicit = parse_mutation_declaration(
        {
            "scope_delta": "TEST_HARNESS",
            "claim_delta_type": "REFRAMING",
            "thesis_control_mode": "TRANSFER_MECHANISM",
            "primitive_invoked": None,
            "touched_artifacts": ["test_model.py"],
        }
    )
    assert explicit.thesis_control_mode == ThesisControlMode.TRANSFER_MECHANISM

    mismatch = evaluate_mutation_declaration(
        explicit,
        ("projects/sample/test_model.py",),
        before_text="Bounded local parser.",
        after_text="Bounded local parser with one extra check.",
        approved_primitive_keys=APPROVED_PRIMITIVE_KEYS,
        expected_thesis_control_mode=ThesisControlMode.ROTATE_ORTHOGONAL_THESIS,
    )
    assert mismatch.mismatch_code == MutationMismatchCode.THESIS_CONTROL_MODE_MISMATCH


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated runner R1 mutation-contract fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    _selftest_parse_thesis_control_mode()
    summary = run_runner_r1_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Runner R1 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
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
