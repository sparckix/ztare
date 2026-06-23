from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ztare.orchestrator.discriminator_queue import DiscriminatorProposal, append_discriminator
from ztare.orchestrator.promotion_guard import assess_promotion_readiness


def _proposal(*, severity: int, license_stage: str, status: str, evidence: bool = False) -> DiscriminatorProposal:
    return DiscriminatorProposal(
        project="tmp_project",
        trigger_artifact="workspace/source.json",
        claim_under_pressure="candidate claim",
        cheapest_discriminator="run hostile control",
        kill_condition="demote if hostile control fails",
        severity_level=severity,
        license_stage=license_stage,
        status=status,
        metadata={"status_evidence_artifacts": ["workspace/evidence.json"]} if evidence else {},
    )


def run_fixture_regression() -> dict[str, object]:
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "tmp_project"
        (project / "workspace").mkdir(parents=True)

        verdict = assess_promotion_readiness(project)
        cases.append({
            "case_id": "empty_queue_blocks_promotion",
            "passed": not verdict.promotion_ready and "no discriminator" in verdict.blocking_reason,
            "verdict": verdict.to_record(),
        })

        append_discriminator(project, _proposal(severity=3, license_stage="commit", status="closed_passed"))
        verdict = assess_promotion_readiness(project)
        cases.append({
            "case_id": "closed_l3_commit_is_too_weak",
            "passed": not verdict.promotion_ready and verdict.weak_or_scratchpad_count == 1,
            "verdict": verdict.to_record(),
        })

        (project / "workspace" / "next_discriminator_queue.jsonl").write_text("", encoding="utf-8")
        append_discriminator(project, _proposal(severity=5, license_stage="scratchpad", status="closed_passed"))
        verdict = assess_promotion_readiness(project)
        cases.append({
            "case_id": "closed_l5_scratchpad_is_not_promotion_grade",
            "passed": not verdict.promotion_ready and verdict.weak_or_scratchpad_count == 1,
            "verdict": verdict.to_record(),
        })

        (project / "workspace" / "next_discriminator_queue.jsonl").write_text("", encoding="utf-8")
        append_discriminator(project, _proposal(severity=5, license_stage="commit", status="proposed"))
        verdict = assess_promotion_readiness(project)
        cases.append({
            "case_id": "open_l5_commit_blocks_until_closed",
            "passed": not verdict.promotion_ready and verdict.eligible_open_count == 1,
            "verdict": verdict.to_record(),
        })

        (project / "workspace" / "next_discriminator_queue.jsonl").write_text("", encoding="utf-8")
        append_discriminator(project, _proposal(severity=5, license_stage="commit", status="closed_passed"))
        verdict = assess_promotion_readiness(project, claim_kind="INS")
        cases.append({
            "case_id": "closed_l5_commit_without_evidence_still_blocks",
            "passed": (
                not verdict.promotion_ready
                and verdict.eligible_closed_count == 1
                and verdict.eligible_closed_with_evidence_count == 0
            ),
            "verdict": verdict.to_record(),
        })

        (project / "workspace" / "next_discriminator_queue.jsonl").write_text("", encoding="utf-8")
        append_discriminator(project, _proposal(severity=5, license_stage="commit", status="closed_passed", evidence=True))
        verdict = assess_promotion_readiness(project, claim_kind="INS")
        cases.append({
            "case_id": "closed_l5_commit_with_evidence_allows_promotion_readiness",
            "passed": (
                verdict.promotion_ready
                and verdict.eligible_closed_count == 1
                and verdict.eligible_closed_with_evidence_count == 1
                and verdict.claim_kind == "INS"
            ),
            "verdict": verdict.to_record(),
        })

        (project / "workspace" / "next_discriminator_queue.jsonl").write_text("", encoding="utf-8")
        append_discriminator(project, _proposal(severity=5, license_stage="commit", status="closed_passed", evidence=True))
        append_discriminator(project, _proposal(severity=5, license_stage="commit", status="proposed"))
        verdict = assess_promotion_readiness(project)
        cases.append({
            "case_id": "open_l5_blocks_even_when_one_l5_closed",
            "passed": not verdict.promotion_ready and verdict.eligible_closed_with_evidence_count == 1 and verdict.eligible_open_count == 1,
            "verdict": verdict.to_record(),
        })

    return {
        "suite": "promotion_guard_fixture_regression",
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
