from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ztare.supervisor.supervisor_backlog import (
    build_backlog_context,
    build_backlog_prompt,
    render_program_plan_markdown,
    run_backlog,
)
from ztare.supervisor.supervisor_manifest import load_optional_program_manifest


def run_supervisor_backlog_fixture_regression() -> dict[str, object]:
    manifest = load_optional_program_manifest("stage2_derivation_seam_hardening")
    markdown = render_program_plan_markdown("stage2_derivation_seam_hardening", manifest)
    context = build_backlog_context("stage2_derivation_seam_hardening")

    results = [
        {
            "case_id": "rendered_program_plan_mentions_live_stage2_packet",
            "passed": (
                manifest is not None
                and "stage2_live_handoff_integration" in markdown
                and "`derivation_evaluator_v1`" in markdown
            ),
        },
        {
            "case_id": "backlog_context_exposes_seed_debate_and_manifest",
            "passed": (
                context["seed_spec_path"] == "research_areas/seeds/active/stage2_derivation_seam.md"
                and context["debate_file"] == "research_areas/debates/kernel/stage2_derivation_seam_hardening.md"
                and str(context["manifest_path"]).endswith(
                    "supervisor/program_manifests/stage2_derivation_seam_hardening.json"
                )
            ),
        },
    ]

    with tempfile.TemporaryDirectory(prefix="supervisor_backlog_fixture_") as tmp:
        output_dir = Path(tmp)
        context_path = output_dir / "context.json"
        context_path.write_text(json.dumps(context, indent=2) + "\n")
        prompt = build_backlog_prompt("stage2_derivation_seam_hardening", context_path)
        results.append(
            {
                "case_id": "backlog_prompt_constrains_to_manifest_and_debate",
                "passed": (
                    "Do not edit code." in prompt
                    and "stage2_derivation_seam_hardening.json" in prompt
                    and "`research_areas/debates/kernel/stage2_derivation_seam_hardening.md`" in prompt
                ),
            }
        )

        dry_result = run_backlog(
            "stage2_derivation_seam_hardening",
            output_dir=output_dir,
            execute=False,
        )
        results.append(
            {
                "case_id": "backlog_dry_run_writes_paths_and_validates_manifest",
                "passed": (
                    dry_result.executed is False
                    and dry_result.validation["passed"] is True
                    and Path(dry_result.prompt_path).exists()
                ),
            }
        )

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "supervisor_backlog_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor backlog fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_backlog_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor backlog fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
