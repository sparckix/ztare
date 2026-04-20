from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import src.ztare.supervisor.supervisor_backlog as supervisor_backlog_module
import src.ztare.supervisor.supervisor_manifest as supervisor_manifest_module
from src.ztare.supervisor.supervisor_gate_resolution import (
    _close_or_freeze_program,
    _resume_program,
)
from src.ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    HandoffStatus,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    status_to_dict,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run_supervisor_gate_resolution_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="supervisor_gate_resolution_fixture_") as tmp:
        root = Path(tmp)
        debate_path = root / "debate.md"
        debate_path.write_text("## Turn 14 — Verifier\n\n<done>\n")
        status_path = root / "status.json"
        events_path = root / "events.jsonl"
        registry_path = root / "program_registry.json"
        manifest_dir = root / "manifests"
        plans_dir = root / "plans"
        manifest_dir.mkdir()
        plans_dir.mkdir()

        registry_payload = {
            "programs": {
                "fixture_program": {
                    "debate_file": str(debate_path),
                    "status": "active",
                    "last_turn": 14,
                    "reopen_condition": None,
                    "owner_mode": "debate",
                }
            }
        }
        _write_json(registry_path, registry_payload)

        manifest_path = manifest_dir / "fixture_program.json"
        _write_json(
            manifest_path,
            {
                "program_id": "fixture_program",
                "completion_policy": "manifest_exhausted_to_D",
                "packets": [
                    {
                        "packet_id": "p1",
                        "title": "Packet 1",
                        "status": "complete",
                        "target": "alpha",
                        "summary": "alpha",
                    },
                    {
                        "packet_id": "p2",
                        "title": "Promotion Packet",
                        "status": "pending",
                        "target": "alpha",
                        "summary": "promotion",
                        "depends_on": ["p1"],
                    },
                ],
            },
        )

        status = HandoffStatus(
            run_id="fixture_run",
            revision=4,
            state=SupervisorState.D,
            active_program="fixture_program",
            active_target="alpha",
            last_actor=Actor.VERIFIER,
            next_actor=Actor.HUMAN,
            status_reason=StatusReason.AWAITING_HUMAN_GATE,
            debate_file=str(debate_path),
            debate_last_turn=14,
            owner_mode="debate",
            artifact_paths=ArtifactPaths(spec="spec.md"),
            human_gate_reason=HumanGateReason.CONTRACT_PROMOTION,
        )
        _write_json(status_path, status_to_dict(status))

        original_manifest_directory = supervisor_manifest_module.manifest_directory
        original_plan_directory = supervisor_backlog_module.program_plan_directory
        supervisor_manifest_module.manifest_directory = lambda: manifest_dir
        supervisor_backlog_module.program_plan_directory = lambda: plans_dir
        try:
            close_args = argparse.Namespace(
                status_path=status_path,
                events_path=events_path,
                decision="close",
                note="",
                registry_path=registry_path,
            )
            close_code = _close_or_freeze_program(close_args)
            closed_status = json.loads(status_path.read_text())
            closed_registry = json.loads(registry_path.read_text())
            closed_manifest = json.loads(manifest_path.read_text())
            plan_text = (plans_dir / "fixture_program.md").read_text()

            results.append(
                {
                    "case_id": "close_resolution_marks_program_closed_and_manifest_complete",
                    "passed": close_code == 0
                    and closed_status["status_reason"] == "program_closed"
                    and closed_status["human_gate_resolved"] is True
                    and closed_registry["programs"]["fixture_program"]["status"] == "closed"
                    and closed_manifest["packets"][1]["status"] == "complete"
                    and "status: `complete`" in plan_text,
                }
            )
            debate_text = debate_path.read_text()
            results.append(
                {
                    "case_id": "close_resolution_appends_human_turn",
                    "passed": "## Turn 15 — Human" in debate_text
                    and "Program closed at the human gate" in debate_text,
                }
            )

            resume_status_path = root / "resume_status.json"
            resume_events_path = root / "resume_events.jsonl"
            resume_debate_path = root / "resume_debate.md"
            resume_debate_path.write_text("## Turn 3 — Verifier\n\n<done>\n")
            resume_status = HandoffStatus(
                run_id="resume_run",
                revision=2,
                state=SupervisorState.D,
                active_program="fixture_program",
                active_target="alpha",
                last_actor=Actor.VERIFIER,
                next_actor=Actor.HUMAN,
                status_reason=StatusReason.AWAITING_HUMAN_GATE,
                debate_file=str(resume_debate_path),
                debate_last_turn=3,
                owner_mode="debate",
                artifact_paths=ArtifactPaths(spec="spec.md"),
                human_gate_reason=HumanGateReason.SCOPE_MISMATCH,
            )
            _write_json(resume_status_path, status_to_dict(resume_status))
            resume_args = argparse.Namespace(
                status_path=resume_status_path,
                events_path=resume_events_path,
                decision="resume",
                note="Resume after clarification.",
                registry_path=registry_path,
            )
            resume_code = _resume_program(resume_args)
            resumed_status = json.loads(resume_status_path.read_text())
            results.append(
                {
                    "case_id": "resume_resolution_returns_loop_to_a1",
                    "passed": resume_code == 0
                    and resumed_status["state"] == "A1"
                    and resumed_status["next_actor"] == "claude"
                    and resumed_status["human_gate_resolved"] is True
                    and resumed_status["owner_mode"] == "debate"
                    and "fixture_program" not in resumed_status["closed_programs"],
                }
            )
        finally:
            supervisor_manifest_module.manifest_directory = original_manifest_directory
            supervisor_backlog_module.program_plan_directory = original_plan_directory

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "supervisor_gate_resolution_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor gate resolution fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_gate_resolution_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor gate resolution fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
