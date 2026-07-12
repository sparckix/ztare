from __future__ import annotations

import pytest

from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.frontier_campaign_actions import retire_frontier_campaign
from ztare.leanmill.frontier_campaign_runner import (
    FrontierAttemptLeaseBusy,
    attempt_lease_status,
    execute_frontier_campaign_verification,
    frontier_attempt_lease,
    frontier_attempt_work_id,
    materialize_frontier_navigation_from_journal,
    resume_frontier_campaign_navigation,
    continue_frontier_campaign_epoch,
    run_post_freeze_literature_review,
)


def _campaign(*, context_hash: str, packet_digest: str) -> dict[str, object]:
    return {
        "packet": {
            "campaign_id": "campaign:stable-frontier",
            "context_hash": context_hash,
        },
        "packet_digest": packet_digest,
    }


def _frozen_attempt(tmp_path):
    attempt = tmp_path / "attempt-stable"
    attempt.mkdir()
    write_json_atomic(
        attempt / "campaign.json",
        _campaign(context_hash="context:root", packet_digest="packet:root"),
    )
    return attempt


def test_attempt_lease_is_root_packet_stable_across_successor_epochs(tmp_path):
    attempt = _frozen_attempt(tmp_path)
    before = frontier_attempt_work_id(attempt)
    write_json_atomic(
        attempt / "campaign.epoch-000.json",
        _campaign(context_hash="context:root", packet_digest="packet:root"),
    )
    write_json_atomic(
        attempt / "campaign.json",
        _campaign(context_hash="context:successor", packet_digest="packet:successor"),
    )
    assert frontier_attempt_work_id(attempt) == before


def test_attempt_lease_serializes_mutable_continuations_and_releases(tmp_path, monkeypatch):
    attempt = _frozen_attempt(tmp_path)
    queue_db = tmp_path / "work_queue.sqlite"
    monkeypatch.setenv("ZTARE_LEANMILL_QUEUE_DB", str(queue_db))

    with frontier_attempt_lease(
        attempt,
        action="owner_navigation",
        worker_id="node-a:invocation-1",
        lease_s=60,
        heartbeat_s=60,
    ) as owner:
        owner.bind_epoch(epoch=3, context_hash="context:successor")
        status = attempt_lease_status(attempt)
        assert status["active"] is True
        assert status["owner"] == "node-a:invocation-1"
        assert status["epoch"] == 3
        assert status["heartbeat_at"] is not None
        view = read_json(attempt / "lease.json", {})
        assert view["work_id"] == status["work_id"]
        assert view["owner"] == status["owner"]
        assert view["heartbeat_at"] == status["heartbeat_at"]
        assert view["lease_until"] == status["lease_until"]

        for continuation in (
            lambda: resume_frontier_campaign_navigation(attempt),
            lambda: continue_frontier_campaign_epoch(attempt),
            lambda: materialize_frontier_navigation_from_journal(attempt),
            lambda: execute_frontier_campaign_verification(attempt),
            lambda: run_post_freeze_literature_review(attempt),
        ):
            with pytest.raises(FrontierAttemptLeaseBusy):
                continuation()
        with pytest.raises(ValueError, match="attempt owner is active"):
            retire_frontier_campaign(
                attempt,
                authority_ref="test-authority",
                reason="test retirement",
            )

    released = attempt_lease_status(attempt)
    assert released["active"] is False
    released_view = read_json(attempt / "lease.json", {})
    assert released_view["active"] is False
    assert released_view["status"] == "queued"
    with frontier_attempt_lease(
        attempt,
        action="recovery_navigation",
        worker_id="node-b:invocation-2",
        lease_s=60,
        heartbeat_s=60,
    ):
        assert attempt_lease_status(attempt)["owner"] == "node-b:invocation-2"
