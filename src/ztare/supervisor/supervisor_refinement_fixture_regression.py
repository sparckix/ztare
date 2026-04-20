from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.supervisor.supervisor_state import (
    Actor,
    HandoffStatus,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    TurnUsageTelemetry,
    TransitionInput,
)
from src.ztare.supervisor.supervisor_transitions import apply_transition


def _a2_status(*, rounds: int, budget_cap: float | None = None, refinement_cost_usd: float = 0.0) -> HandoffStatus:
    return HandoffStatus(
        run_id="refinement_fixture",
        revision=2,
        state=SupervisorState.A2,
        active_program="stage2_derivation_seam_hardening",
        active_target="derivation_boundary",
        last_actor=Actor.CLAUDE,
        next_actor=Actor.CLAUDE,
        status_reason=StatusReason.AWAITING_DRAFT,
        spec_refinement_rounds=rounds,
        refinement_cost_usd=refinement_cost_usd,
        max_refinement_cost_usd=budget_cap,
    )


def run_supervisor_refinement_fixture_regression() -> dict[str, object]:
    cases = []

    first_refinement = apply_transition(
        _a2_status(rounds=0),
        TransitionInput(
            actor=Actor.CLAUDE,
            expected_revision=2,
            target_state=SupervisorState.A1,
            spec_refinement_requested=True,
            note="Need one more spec correction round.",
        ),
    )
    cases.append(
        {
            "case_id": "a2_to_a1_first_refinement",
            "passed": (
                first_refinement.status.state == SupervisorState.A1
                and first_refinement.status.spec_refinement_rounds == 1
                and not first_refinement.fail_closed
            ),
        }
    )

    second_refinement = apply_transition(
        _a2_status(rounds=1),
        TransitionInput(
            actor=Actor.CLAUDE,
            expected_revision=2,
            target_state=SupervisorState.A1,
            spec_refinement_requested=True,
            note="Need the final spec correction round.",
        ),
    )
    cases.append(
        {
            "case_id": "a2_to_a1_second_refinement",
            "passed": (
                second_refinement.status.state == SupervisorState.A1
                and second_refinement.status.spec_refinement_rounds == 2
                and not second_refinement.fail_closed
            ),
        }
    )

    capped_refinement = apply_transition(
        _a2_status(rounds=2),
        TransitionInput(
            actor=Actor.CLAUDE,
            expected_revision=2,
            target_state=SupervisorState.A1,
            spec_refinement_requested=True,
            note="Trying to overrun the refinement cap.",
        ),
    )
    cases.append(
        {
            "case_id": "a2_to_d_refinement_cap",
            "passed": (
                capped_refinement.status.state == SupervisorState.D
                and capped_refinement.fail_closed
                and capped_refinement.status.human_gate_reason == HumanGateReason.SPEC_REFINEMENT_CAP_REACHED
            ),
        }
    )

    budget_capped_refinement = apply_transition(
        _a2_status(rounds=1, budget_cap=1.25, refinement_cost_usd=1.0),
        TransitionInput(
            actor=Actor.CLAUDE,
            expected_revision=2,
            target_state=SupervisorState.A1,
            spec_refinement_requested=True,
            turn_usage=TurnUsageTelemetry(
                model_name="fixture-model",
                estimated_cost_usd=0.3,
                telemetry_captured=True,
            ),
            note="Trying to exceed the refinement budget.",
        ),
    )
    cases.append(
        {
            "case_id": "a2_to_d_refinement_budget_cap",
            "passed": (
                budget_capped_refinement.status.state == SupervisorState.D
                and budget_capped_refinement.fail_closed
                and budget_capped_refinement.status.human_gate_reason
                == HumanGateReason.SPEC_REFINEMENT_BUDGET_REACHED
            ),
        }
    )

    missing_flag = apply_transition(
        _a2_status(rounds=0),
        TransitionInput(
            actor=Actor.CLAUDE,
            expected_revision=2,
            target_state=SupervisorState.A1,
            spec_refinement_requested=False,
            note="Missing explicit refinement flag.",
        ),
    )
    cases.append(
        {
            "case_id": "a2_to_d_missing_refinement_flag",
            "passed": (
                missing_flag.status.state == SupervisorState.D
                and missing_flag.fail_closed
                and missing_flag.status.human_gate_reason == HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH
            ),
        }
    )

    all_passed = all(case["passed"] for case in cases)
    return {
        "suite": "supervisor_refinement_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor bounded refinement fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_refinement_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor refinement fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
