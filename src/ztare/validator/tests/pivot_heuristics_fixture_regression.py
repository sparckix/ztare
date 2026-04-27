from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ztare.validator.utilities.pivot_heuristics import (
    get_pivot_thresholds,
    resolve_stagnation_pivot_state,
)


@dataclass(frozen=True)
class PivotFixtureCase:
    case_id: str
    description: str
    is_v4_project: bool
    falsification_mode: str | None
    rubric_mode: str | None
    stagnation_count: int
    expected_loop_control_action: str
    expected_event_type: str | None
    expected_profile_name: str | None
    expected_pivot_threshold: int
    expected_emergency_threshold: int | None


def build_pivot_fixture_cases() -> list[PivotFixtureCase]:
    return [
        PivotFixtureCase(
            case_id="legacy_below_threshold",
            description="Legacy mode stays normal below stagnation 3.",
            is_v4_project=False,
            falsification_mode="bounded_discriminator",
            rubric_mode=None,
            stagnation_count=2,
            expected_loop_control_action="normal",
            expected_event_type=None,
            expected_profile_name=None,
            expected_pivot_threshold=3,
            expected_emergency_threshold=4,
        ),
        PivotFixtureCase(
            case_id="legacy_stagnation_pivot",
            description="Legacy bounded-discriminator pivots at stagnation 3.",
            is_v4_project=False,
            falsification_mode="bounded_discriminator",
            rubric_mode=None,
            stagnation_count=3,
            expected_loop_control_action="stagnation_pivot",
            expected_event_type="topological_pivot_profile_injected",
            expected_profile_name="bounded_discriminator",
            expected_pivot_threshold=3,
            expected_emergency_threshold=4,
        ),
        PivotFixtureCase(
            case_id="legacy_emergency_pivot",
            description="Legacy bounded-discriminator escalates to emergency at stagnation 4.",
            is_v4_project=False,
            falsification_mode="bounded_discriminator",
            rubric_mode=None,
            stagnation_count=4,
            expected_loop_control_action="emergency_pivot",
            expected_event_type="topological_pivot_emergency",
            expected_profile_name="bounded_discriminator",
            expected_pivot_threshold=3,
            expected_emergency_threshold=4,
        ),
        PivotFixtureCase(
            case_id="newton_below_threshold",
            description="Newton mode stays normal below stagnation 2.",
            is_v4_project=False,
            falsification_mode="bounded_discriminator",
            rubric_mode="newton",
            stagnation_count=1,
            expected_loop_control_action="normal",
            expected_event_type=None,
            expected_profile_name=None,
            expected_pivot_threshold=2,
            expected_emergency_threshold=3,
        ),
        PivotFixtureCase(
            case_id="newton_stagnation_pivot",
            description="Newton mode injects the newton_discovery profile at stagnation 2.",
            is_v4_project=False,
            falsification_mode="bounded_discriminator",
            rubric_mode="newton",
            stagnation_count=2,
            expected_loop_control_action="stagnation_pivot",
            expected_event_type="topological_pivot_profile_injected",
            expected_profile_name="newton_discovery",
            expected_pivot_threshold=2,
            expected_emergency_threshold=3,
        ),
        PivotFixtureCase(
            case_id="newton_emergency_pivot",
            description="Newton mode escalates one step later, at stagnation 3.",
            is_v4_project=False,
            falsification_mode="bounded_discriminator",
            rubric_mode="newton",
            stagnation_count=3,
            expected_loop_control_action="emergency_pivot",
            expected_event_type="topological_pivot_emergency",
            expected_profile_name="newton_discovery",
            expected_pivot_threshold=2,
            expected_emergency_threshold=3,
        ),
        PivotFixtureCase(
            case_id="v4_bounded_override",
            description="V4 projects stay on bounded override and never enter generic emergency pivot.",
            is_v4_project=True,
            falsification_mode="bounded_discriminator",
            rubric_mode="newton",
            stagnation_count=3,
            expected_loop_control_action="stagnation_pivot",
            expected_event_type="v4_bounded_mutation_override",
            expected_profile_name="kernel_bounded",
            expected_pivot_threshold=3,
            expected_emergency_threshold=None,
        ),
    ]


def run_pivot_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []
    all_passed = True

    for case in build_pivot_fixture_cases():
        pivot_threshold, emergency_threshold = get_pivot_thresholds(
            is_v4_project=case.is_v4_project,
            rubric_mode=case.rubric_mode,
        )
        state = resolve_stagnation_pivot_state(
            is_v4_project=case.is_v4_project,
            falsification_mode=case.falsification_mode,
            stagnation_count=case.stagnation_count,
            rubric_mode=case.rubric_mode,
        )
        actual_profile_name = state.profile.name if state.profile is not None else None
        passed = (
            state.loop_control_action == case.expected_loop_control_action
            and state.event_type == case.expected_event_type
            and actual_profile_name == case.expected_profile_name
            and pivot_threshold == case.expected_pivot_threshold
            and emergency_threshold == case.expected_emergency_threshold
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case": asdict(case),
                "actual": {
                    "loop_control_action": state.loop_control_action,
                    "event_type": state.event_type,
                    "profile_name": actual_profile_name,
                    "pivot_threshold": pivot_threshold,
                    "emergency_threshold": emergency_threshold,
                },
                "passed": passed,
            }
        )

    return {
        "suite": "pivot_heuristics_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the pivot-heuristics fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_pivot_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Pivot heuristics fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        case_id = result["case"]["case_id"]
        expected = result["case"]["expected_loop_control_action"]
        actual = result["actual"]["loop_control_action"]
        print(f"- {status} {case_id}: expected {expected} -> {actual}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
