from ztare.common.finite_structure_belief import (
    compile_finite_structure_belief,
    rank_finite_structure_questions,
    update_finite_structure_belief,
)


def test_question_value_is_model_label_invariant_and_updates_from_later_evidence():
    predictions = {
        "sharp": {
            "a": {"up": 0.9, "down": 0.1},
            "b": {"up": 0.1, "down": 0.9},
        },
        "flat": {
            "a": {"up": 0.55, "down": 0.45},
            "b": {"up": 0.45, "down": 0.55},
        },
    }
    belief = compile_finite_structure_belief(
        evidence_epoch="e1", model_ids=("a", "b"),
        question_predictives=predictions,
    )
    relabeled = compile_finite_structure_belief(
        evidence_epoch="e1", model_ids=("x", "y"),
        question_predictives={
            question: {"x": rows["a"], "y": rows["b"]}
            for question, rows in predictions.items()
        },
    )
    assert [row["question_id"] for row in rank_finite_structure_questions(belief)] == [
        row["question_id"] for row in rank_finite_structure_questions(relabeled)
    ] == ["sharp", "flat"]
    updated = update_finite_structure_belief(
        belief, question_id="sharp", observed_outcome="up",
        observed_at="later", evidence_refs=("source:later",),
    )
    assert updated["weights"]["a"] > updated["weights"]["b"]
    assert [row["question_id"] for row in rank_finite_structure_questions(updated)] == ["flat"]


def test_canonical_identity_collisions_and_refuted_epochs_fail_closed():
    with pytest.raises(ValueError, match="collide"):
        compile_finite_structure_belief(
            evidence_epoch="e1", model_ids=("a", "b"),
            question_predictives={
                1: {"a": {"up": 1}, "b": {"up": 1}},
                "1": {"a": {"up": 1}, "b": {"up": 1}},
            },
        )
    belief = compile_finite_structure_belief(
        evidence_epoch="e1", model_ids=("a", "b"),
        question_predictives={
            "q": {"a": {"seen": 0, "miss": 1}, "b": {"seen": 0, "miss": 1}},
        },
    )
    refuted = update_finite_structure_belief(
        belief, question_id="q", observed_outcome="seen",
        observed_at="later", evidence_refs=("source:later",),
    )
    with pytest.raises(ValueError, match="terminal"):
        rank_finite_structure_questions(refuted)
import pytest
