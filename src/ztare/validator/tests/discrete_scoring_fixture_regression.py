"""Fixture regression tests for discrete_exact scoring mode in fit_primitive.

Tests the _evaluate_discrete_exact path: no curve_fit, exact integer match,
modular arithmetic expressions.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

from src.ztare.fit.fit_primitive import (
    FitDeclaration,
    FitFailure,
    FitSuccess,
    fit_parameters,
)


@dataclass(frozen=True)
class DiscreteFixtureCase:
    case_id: str
    description: str
    expression: str
    independent_vars: tuple[str, ...]
    parameter_names: tuple[str, ...]
    initial_guesses: dict[str, float]
    evidence_text: str
    score_mode: str
    expected_class: str  # "FitSuccess" or "FitFailure"
    expected_match_fraction: float | None
    expected_failure_class: str | None


EVIDENCE_MODULAR = """\
MEASURED RESPONSE f(x) [VISIBLE SLICE]

x\ty
0\t7
1\t2
2\t3
5\t3
6\t2
7\t7
13\t7
14\t2
"""

EVIDENCE_LINEAR = """\
MEASURED RESPONSE f(x) [VISIBLE SLICE]

x\ty
0\t3
1\t5
2\t7
3\t9
4\t11
"""


def build_fixture_cases() -> list[DiscreteFixtureCase]:
    return [
        DiscreteFixtureCase(
            case_id="perfect_modular_match",
            description="Correct GT expression matches all visible points exactly.",
            expression="(3 * x**2 + 5 * x + 7) % 13",
            independent_vars=("x",),
            parameter_names=(),
            initial_guesses={},
            evidence_text=EVIDENCE_MODULAR,
            score_mode="discrete_exact",
            expected_class="FitSuccess",
            expected_match_fraction=1.0,
            expected_failure_class=None,
        ),
        DiscreteFixtureCase(
            case_id="wrong_modulus",
            description="Wrong modulus (11 instead of 13) should miss some points.",
            expression="(3 * x**2 + 5 * x + 7) % 11",
            independent_vars=("x",),
            parameter_names=(),
            initial_guesses={},
            evidence_text=EVIDENCE_MODULAR,
            score_mode="discrete_exact",
            expected_class="FitSuccess",
            expected_match_fraction=0.375,  # 3/8
            expected_failure_class=None,
        ),
        DiscreteFixtureCase(
            case_id="linear_perfect",
            description="Simple linear expression on linear data — all match.",
            expression="2 * x + 3",
            independent_vars=("x",),
            parameter_names=(),
            initial_guesses={},
            evidence_text=EVIDENCE_LINEAR,
            score_mode="discrete_exact",
            expected_class="FitSuccess",
            expected_match_fraction=1.0,
            expected_failure_class=None,
        ),
        DiscreteFixtureCase(
            case_id="constant_wrong",
            description="Constant expression on varying data — mostly mismatches.",
            expression="7",
            independent_vars=("x",),
            parameter_names=(),
            initial_guesses={},
            evidence_text=EVIDENCE_MODULAR,
            score_mode="discrete_exact",
            expected_class="FitSuccess",
            expected_match_fraction=0.375,  # x=0, x=7, x=13 give y=7 → 3/8
            expected_failure_class=None,
        ),
        DiscreteFixtureCase(
            case_id="empty_evidence_fails",
            description="Empty evidence text should produce a parse error.",
            expression="x + 1",
            independent_vars=("x",),
            parameter_names=(),
            initial_guesses={},
            evidence_text="nothing parseable here",
            score_mode="discrete_exact",
            expected_class="FitFailure",
            expected_match_fraction=None,
            expected_failure_class="evidence_parse_error",
        ),
        DiscreteFixtureCase(
            case_id="continuous_mode_no_params_is_solver_error",
            description="continuous_l2 with zero free params hits solver_error (curve_fit needs params).",
            expression="2 * x + 3",
            independent_vars=("x",),
            parameter_names=(),
            initial_guesses={},
            evidence_text=EVIDENCE_LINEAR,
            score_mode="continuous_l2",
            expected_class="FitFailure",
            expected_match_fraction=None,
            expected_failure_class="solver_error",
        ),
    ]


def run_fixture_cases(
    cases: list[DiscreteFixtureCase],
) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []

    for case in cases:
        decl = FitDeclaration(
            expression=case.expression,
            independent_vars=list(case.independent_vars),
            parameter_names=list(case.parameter_names),
            initial_guesses=case.initial_guesses,
        )

        result = fit_parameters(
            decl,
            case.evidence_text,
            score_mode=case.score_mode,
        )

        actual_class = type(result).__name__
        if actual_class != case.expected_class:
            failed.append(
                f"{case.case_id}: expected {case.expected_class}, got {actual_class}"
                f" ({getattr(result, 'failure_class', '')})"
            )
            continue

        if isinstance(result, FitFailure) and case.expected_failure_class:
            if result.failure_class != case.expected_failure_class:
                failed.append(
                    f"{case.case_id}: expected failure_class={case.expected_failure_class}, "
                    f"got {result.failure_class}"
                )
                continue

        if isinstance(result, FitSuccess) and case.expected_match_fraction is not None:
            actual_fraction = 1.0 - result.max_abs_residual
            if abs(actual_fraction - case.expected_match_fraction) > 0.01:
                failed.append(
                    f"{case.case_id}: expected match_fraction={case.expected_match_fraction:.3f}, "
                    f"got {actual_fraction:.3f}"
                )
                continue

        passed.append(case.case_id)

    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = build_fixture_cases()
    passed, failed = run_fixture_cases(cases)

    if args.json:
        print(json.dumps({"passed": passed, "failed": failed}, indent=2))
    else:
        for p in passed:
            print(f"  PASS  {p}")
        for f in failed:
            print(f"  FAIL  {f}")
        print(f"\n{len(passed)}/{len(cases)} passed")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
