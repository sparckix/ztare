from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ztare.orchestrator.research_taste import (
    load_research_taste_profile,
    rank_candidates,
    write_ranking_report,
)


def run_research_taste_fixture_regression() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        prefs = tmp_path / "preferences.yaml"
        prefs.write_text(
            """
research_taste:
  axes:
    outstanding_problem_resolution:
      weight: 0.35
    prize_or_money_potential:
      weight: 0.25
    architecture_fit:
      weight: 0.25
    self_recursive_governance:
      weight: 0.15
  penalties:
    public_claim_risk:
      weight: 0.20
    infrastructure_fragility:
      weight: 0.10
  routing_thresholds:
    pursue_now: 3.75
    queue: 2.25
""".strip()
            + "\n",
            encoding="utf-8",
        )
        profile = load_research_taste_profile(prefs)
        high = {
            "id": "frontier_discriminator",
            "claim_under_pressure": "Resolve open problem eigenquestion with scaffold fixture and ledger closure.",
            "taste_axes": {
                "outstanding_problem_resolution": 5,
                "prize_or_money_potential": 4,
                "architecture_fit": 5,
                "self_recursive_governance": 5,
                "public_claim_risk": 0,
                "infrastructure_fragility": 1,
            },
        }
        low = {
            "id": "paper_polish",
            "claim_under_pressure": "Minor wording cleanup with no open problem or architecture change.",
            "taste_axes": {
                "outstanding_problem_resolution": 1,
                "prize_or_money_potential": 1,
                "architecture_fit": 2,
                "self_recursive_governance": 0,
                "public_claim_risk": 1,
                "infrastructure_fragility": 0,
            },
        }
        ranked = rank_candidates([low, high], profile)
        out_path = tmp_path / "ranking.json"
        report = write_ranking_report(candidates=[low, high], profile=profile, out_path=out_path)
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        cases = [
            {
                "case_id": "explicit_preferences_rank_frontier_move_first",
                "passed": ranked[0]["candidate"]["id"] == "frontier_discriminator",
            },
            {
                "case_id": "high_score_routes_to_pursue_now",
                "passed": ranked[0]["taste_score"]["attention_band"] == "pursue_now",
            },
            {
                "case_id": "low_score_defers",
                "passed": ranked[-1]["taste_score"]["attention_band"] == "defer",
            },
            {
                "case_id": "report_written_with_profile_and_ranked_rows",
                "passed": (
                    out_path.exists()
                    and loaded["profile"]["axes"]["outstanding_problem_resolution"]["weight"] == 0.35
                    and len(report["ranked"]) == 2
                    and report["ranked"][0]["opportunity_card"]["operator_decision"] == "unset"
                    and report["ranked"][0]["opportunity_card"]["anti_goodhart_checks"][
                        "preference_priority_cannot_promote_confidence"
                    ]
                    is True
                ),
            },
        ]
    all_passed = all(bool(case["passed"]) for case in cases)
    return {
        "suite": "research_taste_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run research taste fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    summary = run_research_taste_fixture_regression()
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Research taste fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
