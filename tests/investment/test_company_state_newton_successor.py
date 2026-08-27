import hashlib
import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.company_state_newton_successor import _screen_passing_result


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_only_exact_current_diagnostic_survivor_can_freeze(tmp_path):
    project = tmp_path / "newton_project"
    project.mkdir()
    for name in ("evidence.txt", "evidence_holdout.txt", "evidence_farther_tail.txt"):
        (project / name).write_text(name, encoding="utf-8")
    receipt = {
        "point_in_time_authority": "retrospective_current_universe_diagnostic_only",
        "source_run_sha256": "s" * 64,
    }
    _write(project / "evidence_source_receipt.json", receipt)
    receipt_sha = hashlib.sha256(
        (project / "evidence_source_receipt.json").read_bytes()
    ).hexdigest()
    partition_hashes = {
        name: hashlib.sha256((project / filename).read_bytes()).hexdigest()
        for name, filename in (
            ("visible", "evidence.txt"),
            ("holdout", "evidence_holdout.txt"),
            ("farther_tail", "evidence_farther_tail.txt"),
        )
    }
    candidate_sha = "c" * 64
    provenance = {
        "status": "resolved", "origin": "subscription_newton_submission",
        "candidate_sha256": candidate_sha,
        "submission_path": "workspace/submissions/iter_002.py",
    }
    gate = {
        "harness_ok": True, "screen_pass": True,
        "candidate_sha256": candidate_sha, "candidate_provenance": provenance,
        "evidence_receipt_sha256": receipt_sha,
        "partition_file_sha256s": partition_hashes,
        "signal_authority": False, "capital_authority": False,
    }
    admission = {
        "status": "complete", "candidate_sha256": candidate_sha,
        "candidate_provenance": provenance, "evidence_receipt_sha256": receipt_sha,
        "gate_result": gate, "capital_authority": False,
    }
    _write(project / "workspace" / "historical_gate_results.json", gate)
    _write(project / "workspace" / "historical_admission.json", admission)
    lineage_body = {
        "current_candidate_sha256": candidate_sha,
        "current_candidate_source": "submission",
        "matching_submission_paths": [provenance["submission_path"]],
    }
    lineage = {
        **lineage_body, "search_lineage_sha256": stable_sha256(lineage_body),
    }
    result_body = {
        "schema": "jaggedthoughts-mechanism-research-result-v1",
        "project_id": project.name, "project_path": str(project),
        "authority": "experiment_only", "capital_authority": False,
        "harness_ok": True, "screen_pass": True, "status": "diagnostic_survivor",
        "candidate_sha256": candidate_sha,
        "evidence_receipt_sha256": receipt_sha,
        "gate_result_sha256": hashlib.sha256(
            (project / "workspace" / "historical_gate_results.json").read_bytes()
        ).hexdigest(),
        "partition_file_sha256s": partition_hashes,
        "point_in_time_authority": receipt["point_in_time_authority"],
        "search_lineage": lineage,
        "historical_admission": {
            "status": "complete", "screen_pass": True,
            "candidate_sha256": candidate_sha, "candidate_provenance": provenance,
        },
    }
    result = {
        **result_body, "research_result_sha256": stable_sha256(result_body),
    }

    assert _screen_passing_result(
        result, project=project, candidate_sha=candidate_sha, provenance=provenance,
    ) == result

    (project / "evidence_holdout.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="exact screen-passing candidate result"):
        _screen_passing_result(
            result, project=project, candidate_sha=candidate_sha, provenance=provenance,
        )
