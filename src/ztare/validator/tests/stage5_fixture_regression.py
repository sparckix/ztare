from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ztare.validator.core.information_yield import (
    IterationSignal,
    LoopControlAction,
    evaluate_information_yield,
)


@dataclass(frozen=True)
class Stage5FixtureCase:
    case_id: str
    description: str
    history: tuple[IterationSignal, ...]
    expected_action: LoopControlAction


def build_stage5_fixture_cases() -> list[Stage5FixtureCase]:
    return [
        Stage5FixtureCase(
            case_id="score_improvement_continue",
            description="A high-water score improvement should continue the search.",
            history=(
                IterationSignal(iteration_index=1, score=65, weakest_point="safe harbor edge case", score_improved=True),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        Stage5FixtureCase(
            case_id="new_attack_continue",
            description="A flat-score iteration with a new attack should continue.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="same flaw", novel_attack_ids=("new_family_counterexample",)),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        Stage5FixtureCase(
            case_id="new_hinge_continue",
            description="A flat-score iteration with a new hinge should continue.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="same flaw", novel_hinge_ids=("fresh_hinge_candidate",)),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        Stage5FixtureCase(
            case_id="new_primitive_continue",
            description="A flat-score iteration with a new primitive-worthy pattern should continue.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="same flaw", novel_primitive_ids=("new_primitive_pattern",)),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        Stage5FixtureCase(
            case_id="verified_axiom_continue",
            description="A verified axiom addition should continue even if score is flat.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="same flaw", verified_axioms_added=1),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        Stage5FixtureCase(
            case_id="catastrophic_axiom_refresh",
            description="A catastrophic failure should not get novelty credit merely for adding verified axioms.",
            history=(
                IterationSignal(
                    iteration_index=1,
                    score=0,
                    weakest_point="same catastrophic flaw",
                    catastrophic_failure=True,
                    verified_axioms_added=3,
                ),
                IterationSignal(
                    iteration_index=2,
                    score=0,
                    weakest_point="same catastrophic flaw",
                    catastrophic_failure=True,
                    verified_axioms_added=2,
                ),
            ),
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        Stage5FixtureCase(
            case_id="catastrophic_axiom_pivot",
            description="Three catastrophic failures with the same weakest point should pivot once novelty credit is removed.",
            history=(
                IterationSignal(
                    iteration_index=1,
                    score=0,
                    weakest_point="same catastrophic flaw",
                    catastrophic_failure=True,
                    verified_axioms_added=3,
                ),
                IterationSignal(
                    iteration_index=2,
                    score=0,
                    weakest_point="same catastrophic flaw",
                    catastrophic_failure=True,
                    verified_axioms_added=2,
                ),
                IterationSignal(
                    iteration_index=3,
                    score=0,
                    weakest_point="same catastrophic flaw",
                    catastrophic_failure=True,
                    verified_axioms_added=1,
                ),
            ),
            expected_action=LoopControlAction.PIVOT_REQUIRED,
        ),
        Stage5FixtureCase(
            case_id="bounded_discriminator_underidentified",
            description="Bounded-discriminator catastrophic streaks should escalate to UNDERIDENTIFIED even when weakest points change.",
            history=(
                IterationSignal(
                    iteration_index=1,
                    score=0,
                    weakest_point="non-exclusive discriminator",
                    catastrophic_failure=True,
                    falsification_mode="bounded_discriminator",
                ),
                IterationSignal(
                    iteration_index=2,
                    score=0,
                    weakest_point="latent decisive variable",
                    catastrophic_failure=True,
                    falsification_mode="bounded_discriminator",
                ),
                IterationSignal(
                    iteration_index=3,
                    score=0,
                    weakest_point="hybrid category boundary unresolved",
                    catastrophic_failure=True,
                    falsification_mode="bounded_discriminator",
                ),
            ),
            expected_action=LoopControlAction.UNDERIDENTIFIED,
        ),
        Stage5FixtureCase(
            case_id="two_step_refresh",
            description="Two low-yield iterations should refresh specialists.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="same flaw repeats"),
                IterationSignal(iteration_index=2, score=80, weakest_point="same flaw repeats"),
            ),
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        Stage5FixtureCase(
            case_id="three_step_pivot",
            description="Three low-yield iterations with the same weakest point should require a pivot.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="same flaw repeats"),
                IterationSignal(iteration_index=2, score=80, weakest_point="same flaw repeats"),
                IterationSignal(iteration_index=3, score=80, weakest_point="same flaw repeats"),
            ),
            expected_action=LoopControlAction.PIVOT_REQUIRED,
        ),
        Stage5FixtureCase(
            case_id="crash_tail_pivot",
            description="Repeated crash-only iterations should require a pivot.",
            history=(
                IterationSignal(iteration_index=1, score=0, weakest_point="auditor subprocess crashed", runtime_failure=True),
                IterationSignal(iteration_index=2, score=0, weakest_point="auditor subprocess crashed", runtime_failure=True),
            ),
            expected_action=LoopControlAction.PIVOT_REQUIRED,
        ),
        Stage5FixtureCase(
            case_id="weakest_point_churn_no_credit",
            description="Weakest-point churn without novelty should still count as low-yield repetition.",
            history=(
                IterationSignal(iteration_index=1, score=80, weakest_point="flaw_a"),
                IterationSignal(iteration_index=2, score=80, weakest_point="flaw_b"),
                IterationSignal(iteration_index=3, score=80, weakest_point="flaw_a"),
            ),
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
    ]


def run_stage5_fixture_regression() -> dict[str, object]:
    cases = build_stage5_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = evaluate_information_yield(list(case.history))
        second = evaluate_information_yield(list(case.history))
        passed = first.action == case.expected_action and first == second
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_action": case.expected_action.value,
                "actual_action": first.action.value,
                "deterministic_repeat_match": first == second,
                "passed": passed,
                "decision": {
                    "action": first.action.value,
                    "stagnant_window": first.stagnant_window,
                    "rationale": first.rationale,
                },
                "history": [asdict(item) for item in case.history],
            }
        )

    return {
        "suite": "stage5_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated stage-5 information-yield fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_stage5_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Stage 5 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"- {status} {result['case_id']}: expected {result['expected_action']} -> {result['actual_action']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
