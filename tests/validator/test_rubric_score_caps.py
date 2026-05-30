from src.ztare.validator.core.rubric_score_caps import apply_evidence_gap_score_caps


def test_evidence_gap_score_cap_clamps_proof_grade_gap() -> None:
    evaluation = {
        "score": 94,
        "weakest_point": "No global PSD/state-pricing kernel is constructed.",
        "evidence_gaps": [
            {
                "severity": "degrading",
                "gap_type": "other",
                "target": "N-stable matrix-block ledger certificate",
                "description": "No construction or analytic proof of a cutoff-stable PSD state-pricing kernel is given.",
            }
        ],
        "score_contract": {"mode": "raw_llm_score"},
    }
    rubric = {
        "evidence_gap_score_caps": [
            {
                "name": "requires_receipt",
                "cap": 89,
                "when_score_at_least": 90,
                "severity_any": ["blocking", "degrading"],
                "text_contains_any": ["state-pricing kernel", "matrix-block"],
                "reason": "Proof-grade score requires the exact receipt.",
            }
        ]
    }

    capped = apply_evidence_gap_score_caps(evaluation, rubric)

    assert capped["score"] == 89
    assert capped["score_cap_applied"]["original_judge_score"] == 94
    assert capped["score_cap_applied"]["capped_score"] == 89
    assert capped["score_contract"]["cap_reason"] == "soft_cap"
    assert capped["score_contract"]["rubric_evidence_gap_score_caps_applied"][0]["name"] == "requires_receipt"


def test_evidence_gap_score_cap_does_not_fire_without_matching_gap() -> None:
    evaluation = {
        "score": 94,
        "weakest_point": "The receipt is supplied.",
        "evidence_gaps": [
            {
                "severity": "enriching",
                "gap_type": "other",
                "target": "minor notation cleanup",
                "description": "Polish only.",
            }
        ],
    }
    rubric = {
        "evidence_gap_score_caps": [
            {
                "cap": 89,
                "severity_any": ["blocking", "degrading"],
                "text_contains_any": ["state-pricing kernel"],
                "reason": "Proof-grade score requires the exact receipt.",
            }
        ]
    }

    uncapped = apply_evidence_gap_score_caps(evaluation, rubric)

    assert uncapped["score"] == 94
    assert "score_cap_applied" not in uncapped
