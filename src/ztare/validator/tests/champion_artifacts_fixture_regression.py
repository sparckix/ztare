from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.validator.utilities.champion_artifacts import (
    build_champion_eval_from_saved_best,
    build_champion_gap_payload_from_saved_best,
    champion_artifacts_out_of_sync_with_saved_best,
)


def _fingerprint_from_score_contract(score_contract: dict | None) -> str | None:
    if not isinstance(score_contract, dict):
        return None
    fingerprint = score_contract.get("regime_fingerprint")
    return fingerprint if isinstance(fingerprint, str) and fingerprint else None


def _fingerprint_from_meta(meta: dict | None) -> str | None:
    if not isinstance(meta, dict):
        return None
    fingerprint = meta.get("score_regime_fingerprint")
    if isinstance(fingerprint, str) and fingerprint:
        return fingerprint
    return _fingerprint_from_score_contract(meta.get("score_contract"))


def _saved_best_meta() -> dict:
    return {
        "score": 83,
        "weakest_point": "Threshold grounding for material fiscal capacity is still missing.",
        "timestamp": "2026-04-09T13:37:00Z",
        "judge_model": "gemini-2.5-flash",
        "mutator_model": "gemini-2.5-flash",
        "score_regime_fingerprint": "fp-83",
        "score_contract": {
            "regime_fingerprint": "fp-83",
            "cap_reason": "deterministic_evidence_gap",
            "cap_reason_detail": "Missing threshold grounding for fiscal capacity.",
            "evidence_gap_types": [
                "missing_scope_boundary_evidence",
                "missing_threshold_grounding",
            ],
            "evidence_gap_targets": [
                "Comparator for mature durable-equilibrium unions",
                "Quantitative threshold for material central fiscal capacity",
            ],
            "degrading_evidence_gap_count": 2,
        },
    }


def run_champion_artifacts_fixture_regression() -> dict[str, object]:
    saved_meta = _saved_best_meta()
    history_stem = "saved_best_iter1_score_83"
    stale_champion_eval = {
        "score": 67,
        "history_stem": "latest_iter0_score_67",
        "score_regime_fingerprint": "fp-83",
    }

    mismatch_detected = champion_artifacts_out_of_sync_with_saved_best(
        stale_champion_eval,
        history_stem=history_stem,
        saved_meta=saved_meta,
        score_regime_fingerprint_from_meta=_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_fingerprint_from_score_contract,
    )

    rebuilt_eval = build_champion_eval_from_saved_best(
        saved_meta,
        history_stem,
        project_rubric="eu_union_load_bearing_pillars",
        project_dynamic=False,
        project_mutator_model_id="gemini-2.5-flash",
        project_judge_model_id="gemini-2.5-flash",
        score_regime_fingerprint_from_meta=_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_fingerprint_from_score_contract,
    )
    rebuilt_gap_payload = build_champion_gap_payload_from_saved_best(
        saved_meta,
        project_name="eu_union_load_bearing_pillars",
        score_regime_fingerprint_from_meta=_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_fingerprint_from_score_contract,
    )
    rebuilt_is_clean = not champion_artifacts_out_of_sync_with_saved_best(
        rebuilt_eval,
        history_stem=history_stem,
        saved_meta=saved_meta,
        score_regime_fingerprint_from_meta=_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_fingerprint_from_score_contract,
    )

    cases = [
        {
            "case_id": "stale_champion_is_detected_and_rebuilt_from_saved_best",
            "passed": (
                mismatch_detected is True
                and rebuilt_eval.get("score") == 83
                and rebuilt_eval.get("history_stem") == history_stem
                and rebuilt_eval.get("artifact_role") == "champion"
                and rebuilt_eval.get("describes_baseline") == "champion"
                and len(rebuilt_eval.get("evidence_gaps", [])) == 2
                and rebuilt_gap_payload.get("artifact_role") == "champion"
                and rebuilt_gap_payload.get("describes_baseline") == "champion"
                and rebuilt_gap_payload.get("score") == 83
                and len(rebuilt_gap_payload.get("evidence_gaps", [])) == 2
            ),
        },
        {
            "case_id": "rebuilt_champion_is_treated_as_in_sync",
            "passed": rebuilt_is_clean is True,
        },
    ]

    all_passed = all(case["passed"] for case in cases)
    return {
        "suite": "champion_artifacts_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run champion artifact fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_champion_artifacts_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Champion artifacts fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
