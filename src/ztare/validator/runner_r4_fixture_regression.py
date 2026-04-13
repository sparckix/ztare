from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ztare.validator.information_yield import (
    IterationSignal,
    LoopControlAction,
    InformationYieldDecision,
    apply_latent_motion_veto,
    evaluate_information_yield,
)


@dataclass(frozen=True)
class R4FixtureCase:
    case_id: str
    description: str
    history: tuple[IterationSignal, ...]
    expected_action: LoopControlAction


@dataclass(frozen=True)
class LatentVetoFixtureCase:
    case_id: str
    description: str
    base_decision: InformationYieldDecision
    records_considered: int
    mean_max_set_distance: float | None
    threshold: float
    expected_action: LoopControlAction


def build_r4_fixture_cases() -> list[R4FixtureCase]:
    DIGEST_A = "aaa111"
    DIGEST_B = "bbb222"

    return [
        # --- R1 mismatch cases ---
        R4FixtureCase(
            case_id="r1_mismatch_single_refresh",
            description="A single R1 declaration mismatch should trigger specialist refresh.",
            history=(
                IterationSignal(
                    iteration_index=1, score=70, weakest_point="scope drift",
                    mutation_r1_mismatch=True,
                ),
            ),
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        R4FixtureCase(
            case_id="r1_mismatch_repeated_pivot",
            description="Two consecutive R1 mismatches should trigger pivot, same as crash tail.",
            history=(
                IterationSignal(
                    iteration_index=1, score=70, weakest_point="scope drift",
                    mutation_r1_mismatch=True,
                ),
                IterationSignal(
                    iteration_index=2, score=70, weakest_point="scope drift",
                    mutation_r1_mismatch=True,
                ),
            ),
            expected_action=LoopControlAction.PIVOT_REQUIRED,
        ),
        # --- Reframing novelty cases ---
        R4FixtureCase(
            case_id="reframing_new_committee_continue",
            description="A REFRAMING mutation with a changed committee digest is structural novelty — continue.",
            history=(
                IterationSignal(
                    iteration_index=1, score=75, weakest_point="same flaw",
                    claim_delta_type="REFRAMING",
                    committee_digest=DIGEST_B,
                    prior_committee_digest=DIGEST_A,
                ),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        R4FixtureCase(
            case_id="reframing_same_committee_no_novelty",
            description="A REFRAMING with unchanged committee digest is NOT structural novelty.",
            history=(
                IterationSignal(
                    iteration_index=1, score=75, weakest_point="same flaw",
                    claim_delta_type="REFRAMING",
                    committee_digest=DIGEST_A,
                    prior_committee_digest=DIGEST_A,
                ),
                IterationSignal(
                    iteration_index=2, score=75, weakest_point="same flaw",
                    claim_delta_type="REFRAMING",
                    committee_digest=DIGEST_A,
                    prior_committee_digest=DIGEST_A,
                ),
            ),
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        R4FixtureCase(
            case_id="narrowing_same_committee_no_novelty",
            description="A NARROWING mutation with unchanged committee gets no novelty credit.",
            history=(
                IterationSignal(
                    iteration_index=1, score=75, weakest_point="same flaw",
                    claim_delta_type="NARROWING",
                    committee_digest=DIGEST_A,
                    prior_committee_digest=DIGEST_A,
                ),
                IterationSignal(
                    iteration_index=2, score=75, weakest_point="same flaw",
                    claim_delta_type="NARROWING",
                    committee_digest=DIGEST_A,
                    prior_committee_digest=DIGEST_A,
                ),
            ),
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        # --- Backward compatibility: existing Stage 5 signals unchanged ---
        R4FixtureCase(
            case_id="score_improvement_still_continues",
            description="Score improvement still produces CONTINUE regardless of R4 fields.",
            history=(
                IterationSignal(
                    iteration_index=1, score=80, weakest_point="edge case",
                    score_improved=True,
                    claim_delta_type="NARROWING",
                    committee_digest=DIGEST_A,
                    prior_committee_digest=DIGEST_A,
                ),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
        R4FixtureCase(
            case_id="novel_primitive_still_continues",
            description="Novel primitive still produces CONTINUE regardless of R4 fields.",
            history=(
                IterationSignal(
                    iteration_index=1, score=75, weakest_point="edge case",
                    novel_primitive_ids=("new_primitive_key",),
                    claim_delta_type="NARROWING",
                    committee_digest=DIGEST_A,
                    prior_committee_digest=DIGEST_A,
                ),
            ),
            expected_action=LoopControlAction.CONTINUE,
        ),
    ]


def build_latent_veto_fixture_cases() -> list[LatentVetoFixtureCase]:
    return [
        LatentVetoFixtureCase(
            case_id="refresh_vetoed_by_structural_motion",
            description="High recent latent motion should veto REFRESH_SPECIALISTS.",
            base_decision=InformationYieldDecision(
                action=LoopControlAction.REFRESH_SPECIALISTS,
                stagnant_window=5,
                rationale="Information yield is low; refresh specialists before attempting a broader pivot.",
            ),
            records_considered=5,
            mean_max_set_distance=0.9,
            threshold=0.3,
            expected_action=LoopControlAction.CONTINUE,
        ),
        LatentVetoFixtureCase(
            case_id="refresh_not_vetoed_with_too_few_records",
            description="The veto should stay off until enough latent-motion records exist.",
            base_decision=InformationYieldDecision(
                action=LoopControlAction.REFRESH_SPECIALISTS,
                stagnant_window=2,
                rationale="Information yield is low; refresh specialists before attempting a broader pivot.",
            ),
            records_considered=2,
            mean_max_set_distance=1.0,
            threshold=0.3,
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        LatentVetoFixtureCase(
            case_id="refresh_not_vetoed_when_motion_is_low",
            description="Low latent motion should not block REFRESH_SPECIALISTS.",
            base_decision=InformationYieldDecision(
                action=LoopControlAction.REFRESH_SPECIALISTS,
                stagnant_window=4,
                rationale="Information yield is low; refresh specialists before attempting a broader pivot.",
            ),
            records_considered=5,
            mean_max_set_distance=0.1,
            threshold=0.3,
            expected_action=LoopControlAction.REFRESH_SPECIALISTS,
        ),
        LatentVetoFixtureCase(
            case_id="pivot_not_touched_by_veto",
            description="The latent-motion veto should not override pivot decisions.",
            base_decision=InformationYieldDecision(
                action=LoopControlAction.PIVOT_REQUIRED,
                stagnant_window=3,
                rationale="No new evidence across the pivot window; the same weakest point keeps repeating.",
            ),
            records_considered=5,
            mean_max_set_distance=1.0,
            threshold=0.3,
            expected_action=LoopControlAction.PIVOT_REQUIRED,
        ),
    ]


def run_r4_fixture_regression() -> dict[str, object]:
    cases = build_r4_fixture_cases()
    latent_veto_cases = build_latent_veto_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = evaluate_information_yield(list(case.history))
        second = evaluate_information_yield(list(case.history))
        passed = first.action == case.expected_action and first == second
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_action": case.expected_action.value,
                "actual_action": first.action.value,
                "deterministic_repeat_match": first == second,
                "passed": passed,
                "decision": {
                    "action": first.action.value,
                    "stagnant_window": first.stagnant_window,
                    "rationale": first.rationale,
                },
            }
        )

    for case in latent_veto_cases:
        first = apply_latent_motion_veto(
            case.base_decision,
            records_considered=case.records_considered,
            mean_max_set_distance=case.mean_max_set_distance,
            threshold=case.threshold,
        )
        second = apply_latent_motion_veto(
            case.base_decision,
            records_considered=case.records_considered,
            mean_max_set_distance=case.mean_max_set_distance,
            threshold=case.threshold,
        )
        passed = first.action == case.expected_action and first == second
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_action": case.expected_action.value,
                "actual_action": first.action.value,
                "deterministic_repeat_match": first == second,
                "passed": passed,
                "decision": {
                    "action": first.action.value,
                    "stagnant_window": first.stagnant_window,
                    "rationale": first.rationale,
                },
            }
        )

    return {
        "suite": "runner_r4_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases) + len(latent_veto_cases),
        "num_passed": sum(1 for r in results if r["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the R4 loop-control wire fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_r4_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Runner R4 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}: expected {result['expected_action']} -> {result['actual_action']}")
        if not result["passed"]:
            print(f"       rationale: {result['decision']['rationale']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
