from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue
from ztare.investment.research_jobs import (
    ResearchEvidenceTimestampError,
    latest_discovery_candidate_index,
    research_rank_priority,
    research_request_currency,
)
from ztare.investment.research_agent import (
    _finish_timestamp_research_block,
    _strategy_alpha_lineage_repair_priority,
)


def test_budgeted_claim_is_atomic_across_workers(tmp_path):
    database = str(tmp_path / "queue.sqlite3")
    setup = work_queue.connect(database)
    for index in range(2):
        work_queue.enqueue(
            setup, kind="research", priority=1, payload={"work_id": f"job:{index}"},
        )
    setup.close()
    barrier = Barrier(2)

    def compete(worker_id):
        connection = work_queue.connect(database)
        barrier.wait()
        row = work_queue.claim(
            connection, worker_id=worker_id, kinds=["research"], lease_s=60,
            budget_key="subscription", budget_window="2026-08-13", budget_limit=1,
        )
        connection.close()
        return row

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(compete, ("one", "two")))

    assert [row is not None for row in rows].count(True) == 1
    connection = work_queue.connect(database)
    assert work_queue.budget_used(
        connection, budget_key="subscription", budget_window="2026-08-13",
    ) == 1


def test_invalid_publication_time_is_a_terminal_research_block(tmp_path):
    root = tmp_path / "investment"
    database = root / "state" / "research_jobs.sqlite3"
    database.parent.mkdir(parents=True)
    connection = work_queue.connect(str(database))
    work_queue.enqueue(connection, kind="research", priority=1, payload={
        "work_id": "research:ALPHA", "request_sha256": "a" * 64,
        "entity_id": "ALPHA", "capital_authority": False,
    })
    job = work_queue.claim(
        connection, worker_id="worker", kinds=["research"], lease_s=60,
    )
    connection.close()
    error = ResearchEvidenceTimestampError(
        label="candidate dossier sources[0].published_at", value="undated",
        source={"id": "issuer", "url": "https://example.test/release"},
    )

    result = _finish_timestamp_research_block(
        root, job=job, worker_id="worker", error=error, provider_called=True,
        lease_seconds=60, raw_output={"sources": [{"published_at": "undated"}]},
    )

    connection = work_queue.connect(str(database))
    row = work_queue.list_items(connection, limit=1)[0]
    connection.close()
    block = json.loads((root / result["result_path"]).read_text(encoding="utf-8"))
    assert (row["status"], row["payload"]["stage"], row["payload"]["retryable"]) == (
        "done", "research_blocked_invalid_evidence_time", False,
    )
    assert block["validation"]["raw_value"] == "undated"
    assert block["evidence_admitted"] is block["capital_authority"] is False


def test_strategy_alpha_lineage_gap_raises_research_priority():
    readiness = {
        "lineage_repair_entity_ids": ["HRMY"],
        "rows": [{
            "entity_id": "MRVL", "eligible_source": False,
            "gaps": ["current_or_compatible_business_lineage_missing"],
        }],
    }
    assert _strategy_alpha_lineage_repair_priority(
        837_000, readiness=readiness, entity_id="HRMY", floor=1_050_000,
    ) == 1_050_000


def test_budgeted_claim_skips_a_two_unit_job_when_one_unit_remains(tmp_path):
    connection = work_queue.connect(str(tmp_path / "queue.sqlite3"))
    work_queue.enqueue(connection, kind="autoresearch", priority=2, payload={"work_id": "two"})
    work_queue.enqueue(connection, kind="research", priority=1, payload={"work_id": "one"})

    job = work_queue.claim(
        connection, worker_id="worker", kinds=["autoresearch", "research"], lease_s=60,
        budget_key="subscription", budget_window="2026-08-13", budget_limit=8,
        observed_budget_used=7, budget_units_by_kind={"autoresearch": 2},
    )

    assert job["work_id"] == "one"
    assert work_queue.budget_used(
        connection, budget_key="subscription", budget_window="2026-08-13",
    ) == 8


def test_idle_budget_reconciles_claims_without_dispatch_receipts(tmp_path):
    connection = work_queue.connect(str(tmp_path / "queue.sqlite3"))
    assert work_queue.reserve_budget(
        connection, budget_key="subscription", budget_window="2026-08-13",
        budget_limit=10, units=4,
    ) == (True, 4)

    assert work_queue.reconcile_idle_budget(
        connection, budget_key="subscription", budget_window="2026-08-13",
        observed_used=2, kinds=["research"],
    ) == (2, True)


def test_direct_reservation_blocks_a_restarted_queue_worker(tmp_path):
    database = str(tmp_path / "queue.sqlite3")
    direct = work_queue.connect(database)
    work_queue.enqueue(direct, kind="research", priority=1, payload={"work_id": "job"})
    assert work_queue.reserve_budget(
        direct, budget_key="subscription:owner:codex", budget_window="2026-08-13",
        budget_limit=1,
    ) == (True, 1)
    direct.close()

    restarted = work_queue.connect(database)
    assert work_queue.claim(
        restarted, worker_id="restarted", kinds=["research"], lease_s=60,
        budget_key="subscription:owner:codex", budget_window="2026-08-13",
        budget_limit=1,
    ) is None


def test_candidate_lane_is_forced_after_three_other_claims(tmp_path):
    connection = work_queue.connect(str(tmp_path / "queue.sqlite3"))
    for index in range(4):
        work_queue.enqueue(
            connection, kind="learning", priority=10,
            payload={"work_id": f"learning:{index}"},
        )
    work_queue.enqueue(
        connection, kind="candidate", priority=1,
        payload={"work_id": "candidate", "required_capability": "web"},
    )
    assert next(
        row for row in work_queue.list_items(connection) if row["work_id"] == "candidate"
    )["required_capability"] == "web"
    claimed = [work_queue.claim(
        connection, worker_id=f"worker:{index}", kinds=["learning", "candidate"],
        capabilities=["web"], lease_s=60, budget_key="subscription",
        budget_window="2026-08-13", budget_limit=10,
        reserved_kind="candidate", reserve_after_other_claims=3,
    )["kind"] for index in range(4)]

    assert claimed == ["learning", "learning", "learning", "candidate"]
    assert work_queue.reserved_kind_streak(
        connection, budget_key="subscription", reserved_kind="candidate",
    ) == 0


def test_candidate_lane_can_reserve_web_and_strategy_job_kinds(tmp_path):
    connection = work_queue.connect(str(tmp_path / "queue.sqlite3"))
    for index in range(2):
        work_queue.enqueue(connection, kind="learning", priority=10, payload={"work_id": f"learning:{index}"})
    work_queue.enqueue(connection, kind="activation", priority=1, payload={"work_id": "activation"})
    work_queue.enqueue(
        connection, kind="strategy", priority=2,
        payload={"work_id": "strategy", "required_capability": "strategy"},
    )
    claimed = [work_queue.claim(
        connection, worker_id=f"worker:{index}", kinds=["learning", "candidate", "activation", "strategy"],
        capabilities=["strategy"],
        lease_s=60, budget_key="subscription", budget_window="2026-08-13", budget_limit=10,
        reserved_kind=("candidate", "activation", "strategy"), reserve_after_other_claims=2,
    )["kind"] for index in range(3)]
    assert claimed == ["learning", "learning", "strategy"]


def test_reserved_work_ids_exclude_unmarked_jobs_of_the_same_reserved_kinds(tmp_path):
    connection = work_queue.connect(str(tmp_path / "queue.sqlite3"))
    work_queue.enqueue(
        connection, kind="outcome", priority=100,
        payload={"work_id": "unmarked-outcome"},
    )
    work_queue.enqueue(
        connection, kind="measurement", priority=1,
        payload={"work_id": "frozen-measurement", "frozen_chain_priority": 1},
    )

    claimed = work_queue.claim(
        connection, worker_id="worker", kinds=["measurement", "outcome"],
        lease_s=60, budget_key="subscription", budget_window="2026-08-13",
        budget_limit=10, reserved_kind=("measurement", "outcome"),
        reserved_work_ids=("frozen-measurement",), reserve_after_other_claims=0,
    )

    assert claimed["work_id"] == "frozen-measurement"


def test_qualitative_research_survives_only_content_compatible_candidate_refreshes():
    basis = {
        "schema": "jaggedthoughts-qualitative-research-basis-v1",
        "candidate_id": "equity:HRMY", "entity_id": "HRMY",
        "entity_kind": "public_equity", "material_sources": ["issuer:HRMY"],
    }
    request_body = {
        "schema": "jaggedthoughts-agent-research-request-v1",
        "candidate_id": "equity:HRMY", "candidate_sha256": "a" * 64,
        "candidate_leaf": "b" * 64,
        "entity_id": "HRMY", "entity_kind": "public_equity",
        "qualitative_research_basis": basis,
        "qualitative_research_basis_sha256": stable_sha256(basis),
    }
    request = {**request_body, "request_sha256": stable_sha256(request_body)}
    current = {
        "equity:HRMY": {
            "candidate_sha256": "d" * 64, "candidate_leaf": "e" * 64,
            "qualitative_research_basis_sha256": stable_sha256(basis),
            "discovery_run_id": "current-run", "rank": 4,
            "potential_rank": {"rank": 2, "scope": "public_equity"},
        }
    }

    currency = research_request_currency(request, current)
    assert currency["currency"] == "compatible_successor"
    assert currency["current_discovery_run_id"] == "current-run"
    assert currency["current_rank"] == 4
    assert currency["current_potential_rank"]["rank"] == 2
    current["equity:HRMY"]["qualitative_research_basis_sha256"] = "f" * 64
    assert research_request_currency(request, current)["currency"] == "superseded"


def test_candidate_index_refuses_a_discovery_epoch_until_queue_handoff_completes(tmp_path):
    (tmp_path / "discovery").mkdir()
    (tmp_path / "state").mkdir()
    run = {
        "run_id": "run-1", "run_sha256": "a" * 64,
        "candidates": [{
            "candidate_id": "equity:ZD", "candidate_sha256": "b" * 64,
            "entity_id": "ZD", "entity_kind": "public_equity",
            "screen_status": "qualified", "potential_rank": {"rank": 1},
        }],
    }
    record = {
        "run_id": "run-1", "run_sha256": "a" * 64,
        "candidate_leaves": {"equity:ZD": "c" * 64},
    }
    (tmp_path / "discovery/latest.json").write_text(json.dumps(run))
    (tmp_path / "discovery/latest_record.json").write_text(json.dumps(record))
    handoff_path = tmp_path / "state/discovery_research_handoff.json"
    def handoff(status):
        body = {
            "schema": "jaggedthoughts-discovery-research-handoff-v1",
            "status": status, "discovery_run_id": "run-1",
            "discovery_run_sha256": "a" * 64,
        }
        return {**body, "handoff_sha256": stable_sha256(body)}

    assert latest_discovery_candidate_index(tmp_path) == {}
    handoff_path.write_text(json.dumps(handoff("preparing")))
    assert latest_discovery_candidate_index(tmp_path) == {}
    assert latest_discovery_candidate_index(
        tmp_path, allow_pending_handoff=True,
    )["equity:ZD"]["potential_rank"] == {"rank": 1}
    handoff_path.write_text(json.dumps(handoff("complete")))
    assert latest_discovery_candidate_index(tmp_path)["equity:ZD"]["entity_id"] == "ZD"

    book_body = {
        "schema": "jaggedthoughts-opportunity-book-v1",
        "discovery_run_id": "run-1", "discovery_run_sha256": "a" * 64,
        "candidates": [{
            "candidate_id": "equity:ZD", "candidate_sha256": "b" * 64,
            "learned_research_rank": 7,
            "learned_potential_rank": {"scope": "public_equity", "rank": 4},
            "learned_research_priority_score": 0.72,
        }],
        "law_policy_influence": {"influence_sha256": "d" * 64},
        "causal_law_target_influence": {"influence_set_sha256": "e" * 64},
        "capital_authority": False,
    }
    book = {**book_body, "book_sha256": stable_sha256(book_body)}
    (tmp_path / "opportunity_books").mkdir()
    (tmp_path / "opportunity_books/latest.json").write_text(json.dumps(book))

    learned = latest_discovery_candidate_index(tmp_path)["equity:ZD"]
    assert learned["learned_research_rank"] == 7
    assert research_rank_priority(learned) == 993_000
    assert learned["research_priority_routing_source"] == {
        "opportunity_book_sha256": book["book_sha256"],
        "law_policy_influence_sha256": "d" * 64,
        "causal_law_influence_set_sha256": "e" * 64,
        "authority": "paper_research_priority_only", "capital_authority": False,
    }
