from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from src.ztare.supervisor.supervisor_proposal import (
    build_proposal_context,
    build_proposal_prompt,
    planning_debate_path,
    proposal_plan_markdown_path,
    proposed_manifest_path,
    run_proposal,
)


def run_supervisor_proposal_fixture_regression() -> dict[str, object]:
    results = []

    fixture_program_id = "systems_to_algorithms_exploration_fixture"
    context = build_proposal_context("systems_to_algorithms", fixture_program_id)
    results.append(
        {
            "case_id": "proposal_context_exposes_research_pipeline",
            "passed": (
                context["pipeline_type"] == "research"
                and context["seed_spec_path"] == "research_areas/seeds/deferred/systems_to_algorithms.md"
            ),
        }
    )

    with tempfile.TemporaryDirectory(prefix="supervisor_proposal_fixture_") as tmp:
        output_dir = Path(tmp)
        try:
            result = run_proposal(
                "systems_to_algorithms",
                fixture_program_id,
                output_dir=output_dir,
                execute=False,
            )
            prompt = Path(result.prompt_path).read_text()
            proposal = json.loads(Path(result.proposal_manifest_path).read_text())
            results.append(
                {
                    "case_id": "proposal_dry_run_creates_placeholder_proposal_and_prompt",
                    "passed": (
                        result.executed is False
                        and proposal["source_seed_id"] == "systems_to_algorithms"
                        and proposal["pipeline_type"] == "research"
                        and "do not create registry entries" in prompt
                        and "pipeline type is `research`" in prompt
                    ),
                }
            )
            results.append(
                {
                    "case_id": "proposal_validation_flags_empty_packets_until_agent_fills_proposal",
                    "passed": (
                        result.validation["passed"] is False
                        and "packets_missing" in result.validation["issues"]
                    ),
                }
            )
        finally:
            for path in (
                proposed_manifest_path(fixture_program_id),
                proposal_plan_markdown_path(fixture_program_id),
                planning_debate_path(fixture_program_id),
            ):
                if path.exists():
                    path.unlink()

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "supervisor_proposal_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor proposal fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_proposal_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor proposal fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
