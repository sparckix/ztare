from ztare.validator.core.meta_judge_schema import (
    coerce_raw_meta_judge_score,
    raw_meta_judge_shape_errors,
)


def _valid_verdict(score=93):
    return {
        "score": score,
        "weakest_point": "remaining bridge",
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": [],
        "debate_summary": "substantive verdict",
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {"label": "survives", "probability": 0.65},
            "nodes": [],
            "edges": [],
        },
    }


def test_raw_meta_judge_rejects_top_level_evidence_gap_payload():
    payload = {
        "gap_type": "Unresolved Constructive Bridge",
        "target": "finite-stencil full-nonlinear LP/cycle certificate",
        "description": "Missing verdict fields despite valid JSON.",
        "severity": "critical",
        "producer": "Meta-Judge",
    }

    errors = raw_meta_judge_shape_errors(payload)

    assert "missing:score" in errors
    assert "missing:weakest_point" in errors
    assert "wrong_top_level:evidence_gap_payload" in errors


def test_raw_meta_judge_accepts_full_verdict_and_coerces_numeric_score():
    payload = _valid_verdict(score="93")

    assert raw_meta_judge_shape_errors(payload) == []
    assert coerce_raw_meta_judge_score(payload)["score"] == 93


def test_raw_meta_judge_rejects_wrong_string_and_probability_dag_shapes():
    payload = _valid_verdict()
    payload["debate_summary"] = []
    payload["adversarial_alignment"] = []
    payload["probability_dag"] = {"outcome": "canary", "nodes": {}, "edges": []}

    errors = raw_meta_judge_shape_errors(payload)

    assert "invalid:debate_summary_not_string" in errors
    assert "invalid:adversarial_alignment_not_string" in errors
    assert "invalid:probability_dag.outcome_not_object" in errors
    assert "invalid:probability_dag.nodes_not_array" in errors
