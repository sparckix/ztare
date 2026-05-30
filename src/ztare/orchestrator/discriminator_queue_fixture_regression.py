from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from src.ztare.orchestrator.discriminator_queue import (
    DebtRatioPoint,
    DiscriminatorProposal,
    append_discriminator,
    infer_narrative_shortcut,
    proposals_from_inverter_result,
    queue_path,
    update_discriminator_status,
    write_background_debt_ladder,
)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_discriminator_queue_fixture_regression() -> dict[str, object]:
    cases: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "projects" / "gp_test"
        project_dir.mkdir(parents=True)

        proposal = DiscriminatorProposal(
            project="gp_test",
            trigger_artifact="workspace/champion_eval_results.json",
            claim_under_pressure="A local positive result is being promoted into a universal law.",
            rival_explanations=["finite-box instrument artifact"],
            cheapest_discriminator="Run a larger-box control.",
            kill_condition="If the ratio collapses under box growth, kill the claim.",
            required_artifacts=["workspace/large_box_summary.json"],
            source="fixture",
        )
        path = append_discriminator(project_dir, proposal)
        records = _read_jsonl(path)
        cases.append(
            {
                "case_id": "manual_proposal_appends_valid_jsonl",
                "passed": (
                    path == queue_path(project_dir)
                    and len(records) == 1
                    and records[0]["schema_version"] == 2
                    and records[0]["project"] == "gp_test"
                    and records[0]["narrative_shortcut"] == "instrument_null_to_physics_null"
                    and records[0]["can_support_promotion"] is False
                ),
            }
        )

        inv = {
            "tests": [
                {
                    "category": "measurement_artifact",
                    "munger_inversion": "The scalar proxy is hiding tensor shear.",
                    "popper_test": "Run an orientation ladder.",
                    "procedure": "Sweep 0, 45, 90 degrees.",
                    "pass_criterion": "Symmetry recovers at 90 degrees.",
                    "fail_criterion": "The hot region remains grid-locked.",
                    "auto_testable": False,
                    "estimated_cost": "moderate",
                }
            ]
        }
        proposals = proposals_from_inverter_result(
            project="gp_test",
            trigger_artifact="workspace/inverter_review.json",
            claim_under_pressure="A scalar external-field result is being treated as tensor physics.",
            inverter_result=inv,
        )
        cases.append(
            {
                "case_id": "inverter_tests_translate_to_typed_proposals",
                "passed": (
                    len(proposals) == 1
                    and proposals[0].to_record()["narrative_shortcut"] == "scalar_proxy_to_tensor_claim"
                    and proposals[0].to_record()["source"] == "gp119_inverter"
                    and proposals[0].to_record()["needs_human"] is True
                    and proposals[0].to_record()["severity_level"] == 3
                    and proposals[0].to_record()["can_support_promotion"] is False
                ),
            }
        )

        ladder_path = write_background_debt_ladder(
            project_dir,
            label="box_control",
            claim_under_pressure="UDG gain survives repaired solve.",
            debt_proxy="off-core field load",
            points=[
                DebtRatioPoint("L3", 1.5, 0.75, axis="box_size"),
                DebtRatioPoint("L4", 1.2, 0.60, axis="box_size"),
            ],
            source="fixture",
        )
        ladder = json.loads(ladder_path.read_text(encoding="utf-8"))
        cases.append(
            {
                "case_id": "background_debt_ladder_writes_ratios",
                "passed": (
                    ladder["schema_version"] == 1
                    and ladder["points"][0]["gain_debt_ratio"] == 2.0
                    and ladder["promotion_rule"].startswith("A local gain is not promotable")
                ),
            }
        )

        cases.append(
            {
                "case_id": "shortcut_inference_is_conservative",
                "passed": infer_narrative_shortcut("") == "unspecified_promotion_shortcut",
            }
        )

        high = DiscriminatorProposal(
            project="gp_test",
            trigger_artifact="workspace/hard_control.json",
            claim_under_pressure="A local positive result is being promoted into a universal law.",
            cheapest_discriminator="Run a dark-domain hostile control.",
            kill_condition="If dark-domain transfer fails, demote the finding.",
            severity_level=5,
            license_stage="commit",
        ).to_record()
        scratch = DiscriminatorProposal(
            project="gp_test",
            trigger_artifact="workspace/analogy.md",
            claim_under_pressure="A cross-domain analogy might be useful.",
            cheapest_discriminator="Explore the analogy in scratchpad.",
            kill_condition="No kill condition yet because this is not a commit-stage claim.",
            severity_level=5,
            license_stage="scratchpad",
        ).to_record()
        cases.append(
            {
                "case_id": "promotion_requires_high_severity_commit_stage",
                "passed": high["can_support_promotion"] is True and scratch["can_support_promotion"] is False,
            }
        )

        replay_path = project_dir / "workspace" / "next_discriminator_queue.replay.jsonl"
        replay_path.parent.mkdir(parents=True, exist_ok=True)
        replay_row = DiscriminatorProposal(
            project="gp_test",
            trigger_artifact="paper.md",
            claim_under_pressure="A tensor claim needs a rotation control.",
            cheapest_discriminator="Run the rotation control.",
            kill_condition="If hot sector stays grid-locked, demote.",
            severity_level=5,
            license_stage="commit",
            metadata={"replay_template": "gravity_tensor_rotation_gate"},
        ).to_record()
        replay_path.write_text(json.dumps(replay_row, sort_keys=True) + "\n", encoding="utf-8")
        updated = update_discriminator_status(
            replay_path,
            status="closed_passed",
            template="gravity_tensor_rotation_gate",
            evidence_artifacts=["workspace/orientation_ladder_summary.json"],
            note="fixture closure",
        )
        closed = _read_jsonl(replay_path)[0]
        cases.append(
            {
                "case_id": "status_update_closes_matching_template_only",
                "passed": (
                    updated == 1
                    and closed["status"] == "closed_passed"
                    and closed["metadata"]["status_evidence_artifacts"] == ["workspace/orientation_ladder_summary.json"]
                    and closed["metadata"]["status_note"] == "fixture closure"
                ),
            }
        )

    all_passed = all(bool(case["passed"]) for case in cases)
    return {
        "suite": "discriminator_queue_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GP-190 discriminator queue fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    summary = run_discriminator_queue_fixture_regression()
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Discriminator queue fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
