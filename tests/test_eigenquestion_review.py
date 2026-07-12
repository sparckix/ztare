from __future__ import annotations

from ztare.leanmill.eigenquestion_review import run_eigenquestion_review
from ztare.leanmill.common import read_json


def test_fable_eigenreview_is_advisory_and_ranks_each_candidate(monkeypatch, tmp_path):
    seen = {}

    class Role:
        def __init__(self, **kwargs):
            seen["kwargs"] = kwargs

        def __call__(self, prompt):
            seen["prompt"] = prompt
            return {
                "ranked_questions": [
                    {
                        "question_id": question_id,
                        "rank": rank,
                        "information_yield": "High because the test separates two causes.",
                        "novelty_headroom": "Unknown until source review.",
                        "harness_readiness": "Medium; one fixture is missing.",
                        "fatal_confounder": "known-result saturation",
                        "discriminating_test": "run the frozen control",
                        "kill_condition": "the control cannot distinguish the arms",
                        "minimum_artifact": "one executable substrate receipt",
                        "apparatus_vs_scarcity": "The control distinguishes them.",
                    }
                    for rank, question_id in enumerate(("q2", "q1"), 1)
                ],
                "portfolio_sequence": ["q2", "q1"],
                "portfolio_rationale": "Run the controlled question first.",
                "scope_notes": "Keep review outside proof authority.",
            }

    monkeypatch.setattr(
        "ztare.leanmill.eigenquestion_review.SubscriptionJSONRole", Role
    )
    receipt = run_eigenquestion_review(
        [
            {"question_id": "q1", "question": "first"},
            {"question_id": "q2", "question": "second"},
        ],
        context={"known": "fact"},
        artifact_dir=tmp_path / "calls",
        repo=tmp_path,
        model="fable",
    )

    assert receipt["authority"] == "advisory_only"
    assert receipt["runtime"] == "claude"
    assert receipt["model"] == "claude-fable-5"
    assert receipt["recommended_question_id"] == "q2"
    assert seen["kwargs"]["config"].runtime == "claude"
    assert "apparatus weakness" in seen["prompt"]
    assert read_json(tmp_path / "calls/review.json", {})["receipt_sha256"] == (
        receipt["receipt_sha256"]
    )
