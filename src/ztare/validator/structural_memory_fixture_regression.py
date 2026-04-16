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


def _fit_success(
    max_abs_residual: float,
    *,
    bic: float = 0.0,
    k_params: int = 1,
    n_samples: int = 20,
    sse: float = 0.0,
) -> FitSuccess:
    return FitSuccess(
        fitted_params={"A": 1.0},
        max_abs_residual=max_abs_residual,
        mean_abs_residual=max_abs_residual / 2.0,
        rmse=max_abs_residual / 3.0,
        residual_map=[
            {"phi": 1.0, "psi": 0.5, "observed": 1.0, "predicted": 0.9, "residual": 0.1},
            {"phi": 2.0, "psi": 0.5, "observed": 2.0, "predicted": 1.7, "residual": 0.3},
        ],
        n_samples=n_samples,
        k_params=k_params,
        sse=sse,
        bic=bic,
        aic=0.0,
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

    # GP-069 complexity-penalty wiring regression. Two structurally distinct
    # families at near-identical L2 residual but different parameter counts:
    # a simple "hinge-like" family with k=3 and a smooth "sigmoid-like"
    # family with k=4. Under unregularized L2, sigmoid wins by 0.001; under
    # BIC, hinge wins because the extra smoothing parameter is charged.
    # Flag off = legacy L2 ordering. Flag on = BIC ordering flips.
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir)
        decl_hinge = FitDeclaration(
            expression="A * math.fabs(phi - C) + B",
            independent_vars=["phi"],
            parameter_names=["A", "B", "C"],
        )
        decl_sigmoid = FitDeclaration(
            expression="A / (1 + math.exp(-(phi - C) / T)) + B",
            independent_vars=["phi"],
            parameter_names=["A", "B", "C", "T"],
        )
        update_structural_memory(
            workspace_dir=workspace_dir,
            declaration=decl_hinge,
            fit_result=_fit_success(
                0.020,
                bic=-150.0,
                k_params=3,
                n_samples=30,
                sse=0.01,
            ),
            iteration_index=1,
            diagnostic_classification="structural_misfit",
        )
        update_structural_memory(
            workspace_dir=workspace_dir,
            declaration=decl_sigmoid,
            fit_result=_fit_success(
                0.019,
                bic=-146.7,
                k_params=4,
                n_samples=30,
                sse=0.0099,
            ),
            iteration_index=2,
            diagnostic_classification="structural_misfit",
        )

        prompt_off = render_structural_memory_prompt_section(
            workspace_dir, complexity_penalty_enabled=False
        )
        prompt_on = render_structural_memory_prompt_section(
            workspace_dir, complexity_penalty_enabled=True
        )

        # The family just-added (sigmoid) is set as the escape anchor and
        # therefore renders first regardless of sort order. We verify sort
        # behavior by checking the *non-escape* family's position: under L2,
        # sigmoid wins and would appear first if escape logic didn't pin it;
        # under BIC, hinge wins. To isolate the ordering test from the
        # escape-anchor rule, we add a third family so the escape anchor is
        # not the one being ordered.
        decl_third = FitDeclaration(
            expression="A * phi**P + B",
            independent_vars=["phi"],
            parameter_names=["A", "B", "P"],
        )
        update_structural_memory(
            workspace_dir=workspace_dir,
            declaration=decl_third,
            fit_result=_fit_success(
                0.500,
                bic=-40.0,
                k_params=3,
                n_samples=30,
                sse=0.25,
            ),
            iteration_index=3,
            diagnostic_classification="structural_misfit",
        )

        prompt_off_three = render_structural_memory_prompt_section(
            workspace_dir, complexity_penalty_enabled=False, max_families=4
        )
        prompt_on_three = render_structural_memory_prompt_section(
            workspace_dir, complexity_penalty_enabled=True, max_families=4
        )

        hinge_snippet = "math.fabs(phi - C)"
        sigmoid_snippet = "math.exp(-(phi - C) / T)"

        # Among the non-escape families (hinge, sigmoid), under L2 sigmoid has
        # lower residual so sigmoid should come before hinge. Under BIC,
        # hinge has lower bic so hinge should come before sigmoid.
        def _first_of(prompt: str, a: str, b: str) -> str:
            ia = prompt.find(a)
            ib = prompt.find(b)
            if ia == -1 or ib == -1:
                return ""
            return "a" if ia < ib else "b"

        off_order = _first_of(prompt_off_three, sigmoid_snippet, hinge_snippet)
        on_order = _first_of(prompt_on_three, hinge_snippet, sigmoid_snippet)

        # Under L2 (flag off), sigmoid (lower residual) sorts ahead of hinge.
        # But the most-recently-added family (decl_third) is the escape
        # anchor and is pinned to the top. We verify the relative order
        # between hinge and sigmoid within the sort by checking that under
        # flag-off, sigmoid appears before hinge; under flag-on, hinge
        # appears before sigmoid.
        flag_off_correct = off_order == "a"
        flag_on_correct = on_order == "a"
        bic_rendered = "best_bic:" in prompt_on_three and "best_bic:" not in prompt_off_three
        bic_flip_passed = flag_off_correct and flag_on_correct and bic_rendered

        results.append(
            {
                "case_id": "gp069_bic_flag_flips_hinge_vs_sigmoid_ordering",
                "passed": bic_flip_passed,
                "detail": (
                    "With hinge (k=3, bic=-150) and sigmoid (k=4, bic=-146.7) at "
                    "near-identical L2, flag-off must rank sigmoid ahead (lower "
                    "residual) and flag-on must rank hinge ahead (lower BIC). "
                    f"off_order={off_order} on_order={on_order} "
                    f"bic_rendered={bic_rendered}"
                ),
            }
        )
        all_passed = all_passed and bic_flip_passed

        memory_end = load_structural_memory(workspace_dir)
        best_bic_present = all(
            "best_bic" in fam and "latest_bic" in fam
            for fam in memory_end.get("families", [])
        )
        results.append(
            {
                "case_id": "gp069_bic_fields_persisted_on_every_family",
                "passed": best_bic_present,
                "detail": "Every family record must carry best_bic and latest_bic telemetry fields.",
            }
        )
        all_passed = all_passed and best_bic_present

    # Regression for P1 (None-crash on legacy memory files). Observed in
    # gp023_sandbox_10/workspace/structural_memory.json: numeric fields
    # stored as null. Must not take down render or update.
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir)
        memory_path = workspace_dir / "structural_memory.json"
        legacy_payload = {
            "schema_version": 1,
            "updated_at_utc": "2026-04-15T00:00:00+00:00",
            "most_recent_family_fingerprint": "sfam:aaaaaaaaaaaaaaaa",
            "most_recent_structural_escape_fingerprint": "",
            "families": [
                {
                    "fingerprint": "sfam:aaaaaaaaaaaaaaaa",
                    "family_label": "P0 * X0 + P1",
                    "example_expression": "A * phi + B",
                    "independent_vars": ["phi"],
                    "first_seen_iteration": 1,
                    "last_seen_iteration": 1,
                    "seen_count": 1,
                    "best_visible_max_abs_residual": None,
                    "latest_visible_max_abs_residual": None,
                    "best_rmse": None,
                    "latest_diagnostic_classification": "structural_misfit",
                },
                {
                    "fingerprint": "sfam:bbbbbbbbbbbbbbbb",
                    "family_label": "P0 * math.exp(P1 * X0) + P2",
                    "example_expression": "A * math.exp(B * phi) + C",
                    "independent_vars": ["phi"],
                    "first_seen_iteration": 2,
                    "last_seen_iteration": 2,
                    "seen_count": 1,
                    "best_visible_max_abs_residual": 0.1,
                    "latest_visible_max_abs_residual": 0.1,
                    "best_rmse": 0.05,
                    "latest_diagnostic_classification": "parametric_noise",
                },
            ],
        }
        memory_path.write_text(json.dumps(legacy_payload) + "\n")

        render_off_ok = True
        render_on_ok = True
        try:
            _ = render_structural_memory_prompt_section(
                workspace_dir, complexity_penalty_enabled=False
            )
        except Exception:
            render_off_ok = False
        try:
            _ = render_structural_memory_prompt_section(
                workspace_dir, complexity_penalty_enabled=True
            )
        except Exception:
            render_on_ok = False

        update_ok = True
        try:
            update_structural_memory(
                workspace_dir=workspace_dir,
                declaration=FitDeclaration(
                    expression="A * phi + B",
                    independent_vars=["phi"],
                    parameter_names=["A", "B"],
                ),
                fit_result=_fit_success(0.05, bic=-10.0, k_params=2, n_samples=20, sse=0.005),
                iteration_index=3,
                diagnostic_classification="structural_misfit",
            )
        except Exception:
            update_ok = False

        p1_passed = render_off_ok and render_on_ok and update_ok
        results.append(
            {
                "case_id": "p1_none_valued_legacy_memory_does_not_crash",
                "passed": p1_passed,
                "detail": (
                    "Legacy memory files can store residual fields as null; "
                    "render and update must degrade gracefully. "
                    f"render_off={render_off_ok} render_on={render_on_ok} update={update_ok}"
                ),
            }
        )
        all_passed = all_passed and p1_passed

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
