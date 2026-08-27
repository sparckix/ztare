import json

from ztare.investment.newton_candidate_provenance import resolve_newton_candidate_provenance


def test_newton_candidate_provenance_distinguishes_subscription_and_unattributed(tmp_path):
    project = tmp_path / "project"
    submissions = project / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    candidate = project / "test_model.py"
    candidate.write_text("VALUE = 1\n", encoding="utf-8")
    (submissions / "iter_003_20260101.py").write_bytes(candidate.read_bytes())
    (project / "workspace" / "iteration_telemetry.jsonl").write_text(
        json.dumps({
            "record_type": "iteration", "iteration_index": 3, "run_id": 41,
            "mutator_model_id": "model", "mutator_effective_model_ids": ["subscription_cli:codex"],
        }) + "\n",
        encoding="utf-8",
    )

    resolved = resolve_newton_candidate_provenance(project, candidate)
    assert (resolved["status"], resolved["origin"], resolved["run_id"]) == (
        "resolved", "subscription_newton_submission", 41,
    )

    candidate.write_text("VALUE = 2\n", encoding="utf-8")
    unresolved = resolve_newton_candidate_provenance(project, candidate)
    assert unresolved["origin"] == "post_subscription_unattributed_candidate"
    assert unresolved["status"] == "unresolved"
