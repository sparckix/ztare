from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.orchestrator.cold_shot_seed import (
    _build_cold_shot_prompt,
    _collect_cold_shot_anchors,
)


def run_cold_shot_seed_fixture_regression() -> dict[str, object]:
    rubric = {
        "research_director_literature_anchors": [
            {
                "label": "rd_anchor",
                "expected_y": 1.2,
                "tolerance_dex": 0.13,
                "rationale": "RD rationale should appear.",
            }
        ],
        "fit_anchors": [
            {
                "name": "fit_anchor",
                "y_expected": 2.4,
                "tolerance_dex": 0.05,
            }
        ],
    }
    anchors = _collect_cold_shot_anchors(rubric)
    prompt = _build_cold_shot_prompt(
        substrate_signature={"total_rows": 4, "class_counts": {"A": 3, "B": 1}, "feature_keys": ["x"]},
        falsification_gates=["G-LAGRANGIAN-NONTRIVIAL"],
        anchors=anchors,
        forbidden_domain=None,
        pareto_target={"description": "test target"},
    )
    cases = [
        {
            "case_id": "rd_and_fit_anchor_shapes_are_normalized",
            "passed": (
                len(anchors) == 2
                and anchors[0]["label"] == "rd_anchor"
                and anchors[1]["label"] == "fit_anchor"
                and anchors[1]["expected_y"] == 2.4
            ),
        },
        {
            "case_id": "prompt_renders_non_description_anchor_fields",
            "passed": (
                "RD rationale should appear." in prompt
                and "fit_anchor: expected_y=2.4 tolerance_dex=0.05" in prompt
            ),
        },
    ]
    all_passed = all(bool(case["passed"]) for case in cases)
    return {
        "suite": "cold_shot_seed_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GP-184 cold-shot seed fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    summary = run_cold_shot_seed_fixture_regression()
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Cold-shot seed fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
