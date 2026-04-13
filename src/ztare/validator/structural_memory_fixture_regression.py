from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from src.ztare.validator.fit_primitive import FitDeclaration, FitSuccess
from src.ztare.validator.structural_memory import (
    build_structural_family_signature,
    load_structural_memory,
    render_structural_memory_prompt_section,
    update_structural_memory,
)


def _fit_success(max_abs_residual: float) -> FitSuccess:
    return FitSuccess(
        fitted_params={"A": 1.0},
        max_abs_residual=max_abs_residual,
        mean_abs_residual=max_abs_residual / 2.0,
        rmse=max_abs_residual / 3.0,
        residual_map=[
            {"phi": 1.0, "psi": 0.5, "observed": 1.0, "predicted": 0.9, "residual": 0.1},
            {"phi": 2.0, "psi": 0.5, "observed": 2.0, "predicted": 1.7, "residual": 0.3},
        ],
    )


def run_structural_memory_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []
    all_passed = True

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir)

        decl_a = FitDeclaration(
            expression="A * phi**P * math.exp(-B * phi / psi) + O",
            independent_vars=["phi", "psi"],
            parameter_names=["A", "P", "B", "O"],
        )
        decl_a_same_family = FitDeclaration(
            expression="K * phi**Q * math.exp(-D * phi / psi) + C",
            independent_vars=["phi", "psi"],
            parameter_names=["K", "Q", "D", "C"],
        )
        decl_b = FitDeclaration(
            expression="A * phi**P / (1 + D * (phi / psi)**Q) + O",
            independent_vars=["phi", "psi"],
            parameter_names=["A", "P", "D", "Q", "O"],
        )

        same_family = (
            build_structural_family_signature(decl_a).fingerprint
            == build_structural_family_signature(decl_a_same_family).fingerprint
        )
        results.append(
            {
                "case_id": "fingerprint_normalizes_parameter_names",
                "passed": same_family,
                "detail": "Equivalent power-exp families should share a fingerprint.",
            }
        )
        all_passed = all_passed and same_family

        update_structural_memory(
            workspace_dir=workspace_dir,
            declaration=decl_a,
            fit_result=_fit_success(0.25),
            iteration_index=1,
            diagnostic_classification="structural_misfit",
        )
        memory_after_first = load_structural_memory(workspace_dir)
        first_passed = len(memory_after_first["families"]) == 1 and not memory_after_first["most_recent_structural_escape_fingerprint"]
        results.append(
            {
                "case_id": "first_family_no_escape",
                "passed": first_passed,
                "detail": "The first family should not count as an escape.",
            }
        )
        all_passed = all_passed and first_passed

        update_structural_memory(
            workspace_dir=workspace_dir,
            declaration=decl_a_same_family,
            fit_result=_fit_success(0.20),
            iteration_index=2,
            diagnostic_classification="structural_misfit",
        )
        memory_after_same = load_structural_memory(workspace_dir)
        same_update_passed = (
            len(memory_after_same["families"]) == 1
            and memory_after_same["families"][0]["seen_count"] == 2
            and abs(memory_after_same["families"][0]["best_visible_max_abs_residual"] - 0.20) < 1e-9
        )
        results.append(
            {
                "case_id": "same_family_updates_in_place",
                "passed": same_update_passed,
                "detail": "Equivalent families should update one record instead of branching.",
            }
        )
        all_passed = all_passed and same_update_passed

        update_structural_memory(
            workspace_dir=workspace_dir,
            declaration=decl_b,
            fit_result=_fit_success(1.40),
            iteration_index=3,
            diagnostic_classification="structural_misfit",
        )
        memory_after_escape = load_structural_memory(workspace_dir)
        prompt = render_structural_memory_prompt_section(workspace_dir)
        escape_passed = (
            len(memory_after_escape["families"]) == 2
            and bool(memory_after_escape["most_recent_structural_escape_fingerprint"])
            and "Known structural families:" in prompt
            and "Most recent structural escape is listed first below." in prompt
        )
        results.append(
            {
                "case_id": "new_family_sets_escape_and_renders_prompt",
                "passed": escape_passed,
                "detail": "A structurally distinct family should persist as an escape anchor.",
            }
        )
        all_passed = all_passed and escape_passed

    return {
        "suite": "structural_memory_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for r in results if r["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the structural memory fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_structural_memory_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Structural memory fixture regression: {summary['num_passed']}/{summary['num_cases']} "
        f"passed (all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}: {result['detail']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
