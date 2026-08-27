import json
import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.discovery import discovery_schedule_status, load_discovery_policy


def test_new_quality_head_invalidates_bound_discovery_epoch(tmp_path) -> None:
    candidate_body = {
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "equity:ACME", "entity_id": "ACME",
        "entity_kind": "public_equity", "as_of": "2026-08-10T00:00:00Z",
        "quality_report_sha256": "b" * 64,
    }
    candidate = {**candidate_body, "candidate_sha256": stable_sha256(candidate_body)}
    run_body = {
        "schema": "jaggedthoughts-discovery-run-v1",
        "completed_at": "2026-08-10T01:00:00Z",
        "candidates": [candidate],
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}
    quality_body = {
        "schema": "jaggedthoughts-company-quality-report-v1",
        "entity_id": "ACME", "as_of": "2026-08-10T02:00:00Z",
        "available_at": "2026-08-10T02:00:00Z",
    }
    quality = {**quality_body, "quality_report_sha256": stable_sha256(quality_body)}
    path = tmp_path / "quality" / "acme.json"
    path.parent.mkdir()
    path.write_text(json.dumps(quality), encoding="utf-8")
    policy_path = tmp_path / "discovery.yaml"
    policy_path.write_text(yaml.safe_dump({
        "schema": "jaggedthoughts-discovery-policy-v1",
        "enabled": True, "cadence_hours": 24,
    }), encoding="utf-8")

    status = discovery_schedule_status(
        policy=load_discovery_policy(policy_path),
        latest_run=run,
        now="2026-08-10T03:00:00Z",
    )

    invalidation = status["quality_freshness"]["invalidations"][0]
    assert status["due"] is True
    assert status["due_reasons"] == ["candidate_quality_epoch_changed"]
    assert invalidation["bound_quality_report_sha256"] == "b" * 64
    assert invalidation["current_quality_report_sha256"] == quality["quality_report_sha256"]
    assert status["quality_freshness"]["fetches_sources"] is False
