from __future__ import annotations

import json
import math

import numpy as np

from src.ztare.fit.fit_primitive import FitDeclaration, _build_model_callable


def run_fixture_regression() -> dict[str, object]:
    cases = []

    decl = FitDeclaration(
        expression="sigmoid(x, c, w) + where(x > 0, Rational(2, 3), erf(0.0))",
        independent_vars=["x"],
        parameter_names=["c", "w"],
    )
    fn = _build_model_callable(decl)
    got = float(fn(np.array([[1.0]]), 0.0, 1.0)[0])
    expected = 1.0 / (1.0 + math.exp(-1.0)) + (2.0 / 3.0)
    cases.append({
        "case_id": "gp035_accepts_safe_direct_helpers",
        "passed": abs(got - expected) < 1e-12,
        "got": got,
        "expected": expected,
    })

    decl = FitDeclaration(
        expression="math.log1p(abs(x)) + sqrt(4.0)",
        independent_vars=["x"],
        parameter_names=[],
    )
    fn = _build_model_callable(decl)
    got = float(fn(np.array([[1.0]]))[0])
    expected = math.log1p(1.0) + 2.0
    cases.append({
        "case_id": "gp035_keeps_math_and_direct_names_aligned",
        "passed": abs(got - expected) < 1e-12,
        "got": got,
        "expected": expected,
    })

    return {
        "suite": "fit_primitive_direct_calls_fixture_regression",
        "all_passed": all(bool(c["passed"]) for c in cases),
        "num_cases": len(cases),
        "num_passed": sum(1 for c in cases if c["passed"]),
        "results": cases,
    }


def main() -> int:
    summary = run_fixture_regression()
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
