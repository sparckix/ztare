"""Fixture regression for the GP-031 findings-debate primitive.

Covers the parser, the convergence rule, and the append helper end to
end against a tempfile-backed seam. Matches the ``run_*()`` + CLI
shape used by the other ``supervisor_*_fixture_regression`` modules in
this package.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from src.ztare.supervisor.supervisor_findings_debate import (
    DebateStatus,
    HARD_TURN_CAP,
    SENTINEL_NO_NEW_CLAIM,
    append_turn,
    check_convergence,
    parse_debate_log,
    read_debate_state,
)


_SEAM_HEADER = """# Test Findings Seam

## Status

`active` (findings track, test fixture)

## Debate Log
"""


def _write_seed_seam(tmp: Path) -> Path:
    seam = tmp / "GP-test_fixture_seam.md"
    seam.write_text(_SEAM_HEADER, encoding="utf-8")
    return seam


def run_supervisor_findings_debate_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # --- Case 1: empty debate log parses to no turns, status PENDING.
        seam = _write_seed_seam(tmp)
        state = read_debate_state(seam)
        results.append(
            {
                "case_id": "empty_debate_log_is_pending",
                "passed": state.turns == () and state.status == DebateStatus.PENDING,
            }
        )

        # --- Case 2: one turn from Claude, still pending.
        append_turn(
            seam,
            agent="Claude",
            date="2026-04-11",
            title="Opening",
            body="First turn body with a load-bearing claim.",
            no_new_load_bearing=False,
        )
        state = read_debate_state(seam)
        results.append(
            {
                "case_id": "one_turn_is_pending",
                "passed": state.turn_count == 1 and state.status == DebateStatus.PENDING,
            }
        )

        # --- Case 3: one turn per agent, still pending (min is 2 per agent).
        append_turn(
            seam,
            agent="Codex",
            date="2026-04-11",
            title="Counterproposal",
            body="Counter body with its own load-bearing claim.",
            no_new_load_bearing=False,
        )
        state = read_debate_state(seam)
        results.append(
            {
                "case_id": "one_turn_per_agent_is_pending",
                "passed": state.turn_count == 2 and state.status == DebateStatus.PENDING,
            }
        )

        # --- Case 4: two turns per agent but last turns lack the sentinel.
        append_turn(
            seam,
            agent="Claude",
            date="2026-04-11",
            title="Response",
            body="Response body introducing a new load-bearing claim.",
            no_new_load_bearing=False,
        )
        append_turn(
            seam,
            agent="Codex",
            date="2026-04-11",
            title="Response",
            body="Response body also introducing a new claim.",
            no_new_load_bearing=False,
        )
        state = read_debate_state(seam)
        results.append(
            {
                "case_id": "two_turns_per_agent_without_sentinel_is_pending",
                "passed": state.turn_count == 4 and state.status == DebateStatus.PENDING,
            }
        )

        # --- Case 5: one agent raises sentinel, other does not → pending.
        append_turn(
            seam,
            agent="Claude",
            date="2026-04-11",
            title="Agreement",
            body="I accept the counterproposal; nothing new from me.",
            no_new_load_bearing=True,
        )
        state = read_debate_state(seam)
        results.append(
            {
                "case_id": "asymmetric_sentinel_is_pending",
                "passed": state.status == DebateStatus.PENDING,
            }
        )

        # --- Case 6: both agents' most-recent turn carries sentinel → converged.
        append_turn(
            seam,
            agent="Codex",
            date="2026-04-11",
            title="Agreement",
            body="Accepting. No new load-bearing claim.",
            no_new_load_bearing=True,
        )
        state = read_debate_state(seam)
        results.append(
            {
                "case_id": "bilateral_sentinel_converges",
                "passed": state.status == DebateStatus.CONVERGED and state.turn_count == 6,
            }
        )

        # --- Case 7: parser recovers sentinel flag via plain substring.
        turns = parse_debate_log(seam)
        last_claude = [t for t in turns if t.agent == "Claude"][-1]
        last_codex = [t for t in turns if t.agent == "Codex"][-1]
        results.append(
            {
                "case_id": "sentinel_recovered_from_parsed_body",
                "passed": (
                    last_claude.no_new_load_bearing
                    and last_codex.no_new_load_bearing
                    and SENTINEL_NO_NEW_CLAIM in last_claude.body
                ),
            }
        )

        # --- Case 8: hard-cap escalation. Build a fresh seam and drive it
        # past HARD_TURN_CAP without any sentinel, then confirm the rule
        # escalates rather than staying pending.
        cap_seam = tmp / "GP-test_cap_seam.md"
        cap_seam.write_text(_SEAM_HEADER, encoding="utf-8")
        for i in range(HARD_TURN_CAP + 1):
            agent = "Claude" if i % 2 == 0 else "Codex"
            append_turn(
                cap_seam,
                agent=agent,
                date="2026-04-11",
                title=f"Turn {i}",
                body=f"Body for turn {i} with ongoing disagreement.",
                no_new_load_bearing=False,
            )
        cap_state = read_debate_state(cap_seam)
        results.append(
            {
                "case_id": "hard_cap_escalates",
                "passed": cap_state.status == DebateStatus.ESCALATED_CAP,
            }
        )

        # --- Case 9: append_turn refuses if the seam file lacks a Debate Log.
        broken = tmp / "no_debate_log.md"
        broken.write_text("# No debate section here\n", encoding="utf-8")
        refused = False
        try:
            append_turn(
                broken,
                agent="Claude",
                date="2026-04-11",
                title="Attempted",
                body="body",
                no_new_load_bearing=False,
            )
        except ValueError:
            refused = True
        results.append(
            {
                "case_id": "append_refuses_seam_without_debate_log",
                "passed": refused,
            }
        )

        # --- Case 10: check_convergence on a synthetic empty tuple is pending.
        results.append(
            {
                "case_id": "empty_tuple_is_pending",
                "passed": check_convergence(()) == DebateStatus.PENDING,
            }
        )

    all_passed = all(bool(item["passed"]) for item in results)
    return {
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fixture regression for GP-031 findings-debate primitive."
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_findings_debate_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor findings-debate fixture regression: "
        f"{summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
