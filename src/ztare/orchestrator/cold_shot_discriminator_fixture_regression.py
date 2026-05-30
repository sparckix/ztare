from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.orchestrator.cold_shot_discriminator import (
    build_cold_shot_discriminator_prompt,
    parse_cold_shot_discriminator_json,
)
from src.ztare.orchestrator.discriminator_queue import proposals_from_cold_shot_result


def run_cold_shot_discriminator_fixture_regression() -> dict[str, object]:
    prompt = build_cold_shot_discriminator_prompt(
        context="A local positive result improved after a solver repair.",
        question="What should be tested next?",
        artifact_manifest=["workspace/summary.json"],
        forbidden_claims=["Do not claim autonomous theory discovery."],
    )
    payload = {
        "answer": "LOCAL_POSITIVE_NEEDS_CONTROL",
        "data_says": ["The repaired instrument changed the result."],
        "data_does_not_say": ["It does not establish a universal law."],
        "narrative_shortcut": "local_positive_to_universal_claim",
        "tightened_eigenquestion": "Does the effect survive a larger-box control?",
        "single_best_next_discriminator": "Run the larger-box control.",
        "kill_condition": "If the gain collapses, demote the claim.",
        "severity_level": 5,
        "license_stage": "commit",
        "weak_test_risk": "",
        "required_artifacts": ["workspace/large_box_summary.json"],
        "if_more_compute_what_exact_run": "L=4 control",
        "if_not_more_compute_what_exact_handoff": "",
        "main_risk": "Finite-box artifact.",
        "do_not_do_next": ["Do not publish the local positive as a law."],
        "confidence": "medium",
    }
    parsed = parse_cold_shot_discriminator_json(json.dumps(payload))
    proposals = proposals_from_cold_shot_result(
        project="gp_test",
        trigger_artifact="workspace/cold_shot.json",
        claim_under_pressure="",
        cold_shot_result=parsed,
    )
    cases = [
        {
            "case_id": "prompt_demands_queue_ready_json",
            "passed": (
                "Return ONLY strict JSON" in prompt
                and "Allowed narrative_shortcut labels" in prompt
                and "Findings may not be promoted on severity < 4" in prompt
                and "Do not claim autonomous theory discovery." in prompt
            ),
        },
        {
            "case_id": "parser_accepts_valid_strict_json",
            "passed": (
                parsed["narrative_shortcut"] == "local_positive_to_universal_claim"
                and parsed["severity_level"] == 5
                and parsed["license_stage"] == "commit"
            ),
        },
        {
            "case_id": "cold_shot_result_translates_to_queue_proposal",
            "passed": (
                len(proposals) == 1
                and proposals[0].to_record()["source"] == "cold_shot_discriminator"
                and proposals[0].to_record()["required_artifacts"] == ["workspace/large_box_summary.json"]
                and proposals[0].to_record()["can_support_promotion"] is True
            ),
        },
        {
            "case_id": "parser_rejects_weak_unstaged_json",
            "passed": False,
        },
    ]
    weak_payload = dict(payload)
    weak_payload["severity_level"] = 0
    weak_payload["license_stage"] = "commit"
    try:
        parse_cold_shot_discriminator_json(json.dumps(weak_payload))
    except ValueError:
        cases[-1]["passed"] = True
    all_passed = all(bool(case["passed"]) for case in cases)
    return {
        "suite": "cold_shot_discriminator_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cold-shot discriminator fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    summary = run_cold_shot_discriminator_fixture_regression()
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Cold-shot discriminator fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
