from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ztare.rubrics.review_rubric import (
    build_evidence_gaps_payload,
    build_patch_payload,
    evidence_surface_ready,
    load_workspace_evidence_surface,
    normalize_review_payload,
    resolve_rubric_path,
    review_exit_code,
)


def run_review_rubric_fixture_regression() -> dict[str, object]:
    cases: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="rubric_review_fixture_") as tmp:
        project_dir = Path(tmp) / "project"
        workspace_dir = project_dir / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        (workspace_dir / "facts.md").write_text("# Facts\n\n- Fact A\n", encoding="utf-8")
        (workspace_dir / "candidate_claims.md").write_text(
            "# Candidate Claims\n\n- Claim A\n", encoding="utf-8"
        )
        summary_surface = load_workspace_evidence_surface(project_dir)
        cases.append(
            {
                "case_id": "workspace_summary_is_preferred_when_present",
                "passed": (
                    summary_surface["mode"] == "workspace_summary"
                    and "workspace/facts.md" in summary_surface["files"]
                    and "workspace/candidate_claims.md" in summary_surface["files"]
                    and evidence_surface_ready(summary_surface) is False
                ),
            }
        )

        empty_project_dir = Path(tmp) / "empty_project"
        empty_workspace_dir = empty_project_dir / "workspace"
        empty_workspace_dir.mkdir(parents=True, exist_ok=True)
        (empty_workspace_dir / "facts.md").write_text("\n", encoding="utf-8")
        (empty_workspace_dir / "candidate_claims.md").write_text(" \n", encoding="utf-8")
        (empty_project_dir / "evidence.txt").write_text("fallback evidence", encoding="utf-8")
        empty_surface = load_workspace_evidence_surface(empty_project_dir)
        cases.append(
            {
                "case_id": "empty_workspace_summary_files_fall_back_to_evidence_surface",
                "passed": (
                    empty_surface["mode"] == "evidence_fallback"
                    and empty_surface["text"] == "fallback evidence"
                    and evidence_surface_ready(empty_surface) is False
                ),
            }
        )

    with tempfile.TemporaryDirectory(prefix="rubric_review_fixture_") as tmp:
        project_dir = Path(tmp) / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "evidence.txt").write_text("X" * 5000, encoding="utf-8")
        fallback_surface = load_workspace_evidence_surface(project_dir)
        cases.append(
            {
                "case_id": "evidence_fallback_uses_first_3kb_when_workspace_summary_missing",
                "passed": (
                    fallback_surface["mode"] == "evidence_fallback"
                    and len(fallback_surface["text"]) == 3000
                    and evidence_surface_ready(fallback_surface) is True
                ),
            }
        )

    with tempfile.TemporaryDirectory(prefix="rubric_review_fixture_") as tmp:
        tmp_path = Path(tmp)
        rubrics_dir = tmp_path / "rubrics"
        rubrics_dir.mkdir(parents=True, exist_ok=True)
        rubric_path = rubrics_dir / "sample.json"
        rubric_path.write_text('{"name":"sample"}\n', encoding="utf-8")
        cases.append(
            {
                "case_id": "resolve_rubric_path_accepts_bare_name_and_json_suffix",
                "passed": (
                    resolve_rubric_path(str(rubric_path)) == rubric_path.resolve()
                    and resolve_rubric_path(str(rubric_path.with_suffix(""))) == rubric_path.resolve()
                ),
            }
        )

    normalized = normalize_review_payload(
        {
            "scenario_validity": {
                "status": "fail",
                "issue": "Operative frame contradicted.",
                "evidence_ref": ["evidence.txt:12"],
                "suggested_revision": "Rewrite the project around the live frame.",
            },
            "checks": [
                {
                    "check_name": "criterion_independence",
                    "status": "fail",
                    "issue": "Two criteria collapse.",
                    "proposed_fix": "Split them.",
                }
            ],
            "overall_summary": "Needs revision.",
        }
    )
    cases.append(
        {
            "case_id": "normalization_backfills_missing_required_checks_as_failures",
            "passed": (
                normalized["scenario_validity"]["status"] == "fail"
                and len(normalized["checks"]) == 5
                and any(
                    item["check_name"] == "criterion_independence" and item["status"] == "fail"
                    for item in normalized["checks"]
                )
                and any(
                    item["check_name"] == "gaming_surface_coverage"
                    and item["issue"] == "Check missing from model output."
                    for item in normalized["checks"]
                )
            ),
        }
    )

    thin_surface_review = normalize_review_payload(
        {
            "scenario_validity": {
                "status": "pass",
                "issue": "",
                "evidence_ref": [],
                "suggested_revision": "",
            },
            "checks": [
                {
                    "check_name": "evidence_anchor_requirement",
                    "status": "fail",
                    "issue": "No evidence support visible.",
                    "proposed_fix": "Compile evidence.",
                },
                {
                    "check_name": "score_ceiling_reachability_without_evidence",
                    "status": "fail",
                    "issue": "Ceiling unreachable.",
                    "proposed_fix": "Compile evidence.",
                },
            ],
            "evidence_gaps": [
                {
                    "target": "discontinuation rates",
                    "severity": "degrading",
                    "fetch_query": "GLP-1 discontinuation rates 12 month persistence payer type",
                    "source_hint": "claims studies",
                }
            ],
            "overall_summary": "",
        }
    )
    for item in thin_surface_review["checks"]:
        if item["check_name"] in {
            "evidence_anchor_requirement",
            "score_ceiling_reachability_without_evidence",
        } and item["status"] == "fail":
            item["cause"] = "evidence_surface_empty"
    cases.append(
        {
            "case_id": "evidence_dependent_failures_can_be_tagged_with_surface_cause",
            "passed": (
                all(
                    item.get("cause") == "evidence_surface_empty"
                    for item in thin_surface_review["checks"]
                    if item["check_name"]
                    in {
                        "evidence_anchor_requirement",
                        "score_ceiling_reachability_without_evidence",
                    }
                )
            ),
        }
    )

    evidence_gaps_payload = build_evidence_gaps_payload(
        project_name="test_project",
        model_family="gemini",
        evidence_surface_ready_flag=False,
        normalized_review=thin_surface_review,
    )
    cases.append(
        {
            "case_id": "thin_surface_with_proposed_gaps_can_emit_fetch_compatible_payload",
            "passed": (
                evidence_gaps_payload is not None
                and evidence_gaps_payload["artifact_role"] == "pre_run_rubric_review"
                and evidence_gaps_payload["evidence_surface_ready"] is False
                and evidence_gaps_payload["evidence_gaps"][0]["target"] == "discontinuation rates"
                and evidence_gaps_payload["evidence_gaps"][0]["fetch_query"]
                == "GLP-1 discontinuation rates 12 month persistence payer type"
            ),
        }
    )

    patch_payload = build_patch_payload(
        rubric_path=Path("rubrics/test.json"),
        normalized_review=normalized,
    )
    cases.append(
        {
            "case_id": "patch_payload_uses_minimum_machine_readable_schema",
            "passed": (
                patch_payload is not None
                and patch_payload["rubric_file"] == "rubrics/test.json"
                and patch_payload["scenario_validity"]["status"] == "fail"
                and any(
                    item["check_name"] == "gaming_surface_coverage"
                    for item in patch_payload["checks_failed"]
                )
            ),
        }
    )

    clean_patch = build_patch_payload(
        rubric_path=Path("rubrics/test.json"),
        normalized_review={
            "scenario_validity": {
                "status": "pass",
                "issue": "",
                "evidence_ref": [],
                "suggested_revision": "",
            },
            "checks": [
                {
                    "check_name": name,
                    "status": "pass",
                    "issue": "",
                    "proposed_fix": "",
                }
                for name in (
                    "gaming_surface_coverage",
                    "evidence_anchor_requirement",
                    "score_ceiling_reachability_without_evidence",
                    "criterion_independence",
                    "persona_blind_spot_coverage",
                )
            ],
            "overall_summary": "",
        },
    )
    cases.append(
        {
            "case_id": "clean_review_does_not_emit_patch_payload",
            "passed": clean_patch is None,
        }
    )

    cases.append(
        {
            "case_id": "review_exit_code_distinguishes_full_pass_structural_fail_and_scenario_fail",
            "passed": (
                review_exit_code(
                    {
                        "scenario_validity": {"status": "pass"},
                        "checks_failed": [],
                    }
                )
                == 0
                and review_exit_code(
                    {
                        "scenario_validity": {"status": "pass"},
                        "checks_failed": [{"check_name": "criterion_independence"}],
                    }
                )
                == 1
                and review_exit_code(
                    {
                        "scenario_validity": {"status": "fail"},
                        "checks_failed": [],
                    }
                )
                == 2
            ),
        }
    )

    return {
        "suite": "review_rubric_fixture_regression",
        "all_passed": all(case["passed"] for case in cases),
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run rubric review fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_review_rubric_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(
        f"Rubric review fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
