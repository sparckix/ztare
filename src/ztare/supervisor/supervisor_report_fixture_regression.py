from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ztare.supervisor.supervisor_report import (
    build_supervisor_report,
    render_supervisor_report_markdown,
)
from ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    HandoffStatus,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    TurnUsageTelemetry,
    status_to_dict,
)


def run_supervisor_report_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="supervisor_report_fixture_") as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "status.json"
        events_path = tmp_path / "events.jsonl"
        status = HandoffStatus(
            run_id="fixture_run",
            revision=4,
            state=SupervisorState.D,
            active_program="stage2_derivation_seam_hardening",
            active_target="derivation_boundary",
            last_actor=Actor.VERIFIER,
            next_actor=Actor.HUMAN,
            status_reason=StatusReason.AWAITING_HUMAN_GATE,
            debate_file="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
            debate_last_turn=14,
            artifact_paths=ArtifactPaths(
                spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
                implementation=(
                    "src/ztare/validator/hinge_handoff.py",
                    "src/ztare/validator/stage2_derivation.py",
                ),
                verification_report="/tmp/stage2_derivation_009/verification_report.txt",
            ),
            last_turn_usage=TurnUsageTelemetry(
                model_name="local_verifier",
                telemetry_captured=False,
            ),
            program_cost_usd=0.64631685,
            human_gate_reason=HumanGateReason.CONTRACT_PROMOTION,
        )
        status_path.write_text(json.dumps(status_to_dict(status), indent=2) + "\n")
        events = [
            {
                "revision": 3,
                "actor": "codex",
                "prior_state": "B",
                "new_state": "C",
                "reason": "Implementation verified.",
                "timestamp": "2026-04-07T03:09:21.056603+00:00",
                "artifact_paths": {"spec": None, "implementation": [], "verification_report": None, "error_report": None},
                "human_gate_reason": None,
            },
            {
                "revision": 4,
                "actor": "verifier",
                "prior_state": "C",
                "new_state": "D",
                "reason": "Verifier passed and routed to promotion gate.",
                "timestamp": "2026-04-07T03:09:54.164920+00:00",
                "artifact_paths": {"spec": None, "implementation": [], "verification_report": "/tmp/report.txt", "error_report": None},
                "human_gate_reason": "contract_promotion",
            },
        ]
        events_path.write_text("".join(json.dumps(item) + "\n" for item in events))

        report = build_supervisor_report(status_path, events_path=events_path)
        markdown = render_supervisor_report_markdown(report)

        results.append(
            {
                "case_id": "report_exposes_human_gate_and_next_action",
                "passed": report["human_gate_reason"] == "contract_promotion"
                and report["next_action"] == "resolve_human_gate",
            }
        )
        results.append(
            {
                "case_id": "report_tracks_recent_events",
                "passed": report["event_count"] == 2
                and report["last_event"] is not None
                and report["last_event"]["new_state"] == "D",
            }
        )
        results.append(
            {
                "case_id": "markdown_render_mentions_costs_and_gate",
                "passed": "program_cost_usd" in markdown
                and "contract_promotion" in markdown
                and "resolve_human_gate" in markdown,
            }
        )

        closed_status_path = tmp_path / "closed_status.json"
        closed_status = HandoffStatus(
            run_id="closed_run",
            revision=5,
            state=SupervisorState.D,
            active_program="fixture_program_closed",
            active_target="derivation_boundary",
            last_actor=Actor.HUMAN,
            next_actor=Actor.HUMAN,
            status_reason=StatusReason.PROGRAM_CLOSED,
            debate_file="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
            debate_last_turn=15,
            artifact_paths=ArtifactPaths(
                spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
            ),
            last_turn_usage=TurnUsageTelemetry(
                model_name="human_gate",
                telemetry_captured=False,
            ),
            program_cost_usd=0.64631685,
            human_gate_reason=HumanGateReason.CONTRACT_PROMOTION,
            human_gate_resolved=True,
        )
        closed_status_path.write_text(json.dumps(status_to_dict(closed_status), indent=2) + "\n")
        closed_report = build_supervisor_report(closed_status_path, events_path=events_path)
        closed_markdown = render_supervisor_report_markdown(closed_report)
        results.append(
            {
                "case_id": "closed_report_does_not_suggest_resolving_gate_again",
                "passed": closed_report["next_action"] == "program_closed"
                and "program_closed" in closed_markdown
                and "resolve_human_gate" not in closed_markdown,
            }
        )

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "supervisor_report_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor report fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_report_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor report fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
