import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.fund_implementation_review import (
    compile_fund_implementation_gap_evidence,
    compile_fund_implementation_research_evidence,
    compile_workspace_fund_implementation_review,
    current_fund_implementation_gap_targets,
)
from ztare.investment.research_agent import (
    FUND_IMPLEMENTATION_GAP_JOB_KIND,
    _enqueue_fund_implementation_gap_jobs,
)
from ztare.leanmill import work_queue


def _sealed(body, field):
    return {**body, field: stable_sha256(body)}


def test_current_fund_gaps_enqueue_once_and_merge_only_requested_fields(tmp_path):
    as_of = "2026-08-22T12:00:00Z"
    candidate = _sealed({
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "fund:test:AAA", "entity_id": "AAA",
        "entity_kind": "public_fund", "screen_status": "monitor", "as_of": as_of,
    }, "candidate_sha256")
    program = _sealed({
        "program_id": "fund-program:AAA",
        "identity": {
            "subject_id": "AAA", "entity_kind": "public_fund",
            "implementation_epoch": as_of,
        },
        "comparison_eligible": True,
    }, "program_sha256")
    comparison = _sealed({
        "schema": "jaggedthoughts-fund-sleeve-comparison-v1",
        "authority": "normalized_paper_comparison_only",
        "sleeves": [{"sleeve_id": "us_equity", "programs": [program]}],
    }, "fund_sleeve_comparison_sha256")
    (tmp_path / "discovery").mkdir()
    (tmp_path / "portfolio/fund_sleeve_comparison").mkdir(parents=True)
    (tmp_path / "discovery/latest.json").write_text(json.dumps({
        "run_sha256": "d" * 64, "candidates": [candidate],
    }))
    (tmp_path / "discovery/latest_record.json").write_text(json.dumps({
        "run_sha256": "d" * 64,
        "candidate_leaves": {"fund:test:AAA": "c" * 64},
    }))
    (tmp_path / "portfolio/fund_sleeve_comparison/latest.json").write_text(
        json.dumps(comparison)
    )
    status = compile_workspace_fund_implementation_review(
        tmp_path, comparison=comparison, compiled_at=as_of,
    )
    request = json.loads(
        (tmp_path / status["requests"][0]["artifact_path"]).read_text()
    )
    prior = compile_fund_implementation_research_evidence(
        request=request, completed_at=as_of, findings={
            "fees": {"status": "observed", "values": {"expense_ratio": 0.001},
                     "source_refs": ["comparison:fees"]},
            "holdings": {"status": "observed", "values": {"portfolio_holdings_count": 300},
                         "source_refs": ["comparison:holdings"]},
            "liquidity": {"status": "observed", "values": {
                "median_bid_ask_spread": 0.0002,
                "average_daily_volume_30d": 2_000_000,
                "fund_net_assets": 5_000_000_000,
            }, "source_refs": ["comparison:liquidity"]},
            "mechanics": {"status": "source_gap", "missing_fields": ["portfolio_turnover"],
                          "observed_values": {}, "source_refs": []},
            "tax_fit": {"status": "source_gap", "missing_fields": [
                "distribution_tax_character", "foreign_withholding_tax_rate",
                "trading_currency", "underlying_currency_exposure",
            ], "observed_values": {}, "source_refs": []},
        },
    )
    evidence_path = next((tmp_path / "research_jobs/fund_implementation/evidence").glob("*.json"))
    evidence_path.write_text(json.dumps(prior))
    compile_workspace_fund_implementation_review(
        tmp_path, comparison=comparison, compiled_at=as_of,
    )

    # A downstream review projection may change the enclosing comparison hash
    # without changing the comparison program's stable id or evidence epoch.
    projected = json.loads(json.dumps(comparison))
    projected.pop("fund_sleeve_comparison_sha256")
    projected_program = projected["sleeves"][0]["programs"][0]
    projected_program.pop("program_sha256")
    projected_program["implementation_review_admitted"] = False
    projected_program["program_sha256"] = stable_sha256(projected_program)
    projected["fund_sleeve_comparison_sha256"] = stable_sha256(projected)
    (tmp_path / "portfolio/fund_sleeve_comparison/latest.json").write_text(
        json.dumps(projected)
    )

    target = current_fund_implementation_gap_targets(tmp_path)[0]
    assert target["requested_coordinates"] == ["mechanics", "tax_fit"]
    connection = work_queue.connect(str(tmp_path / "state/research_jobs.sqlite3"))
    try:
        stale_id = work_queue.enqueue(
            connection, kind=FUND_IMPLEMENTATION_GAP_JOB_KIND, priority=999_999,
            payload={"work_id": "stale-fund-gap", "stage": "queued"},
        )
        work_ids = _enqueue_fund_implementation_gap_jobs(
            tmp_path, connection=connection,
            rows=work_queue.list_items(connection, limit=10), max_attempts=3,
        )
        rows = work_queue.list_items(connection, limit=10)
        assert _enqueue_fund_implementation_gap_jobs(
            tmp_path, connection=connection, rows=rows, max_attempts=3,
        ) == []
    finally:
        connection.close()
    assert len(work_ids) == 1
    stale = next(row for row in rows if row["work_id"] == stale_id)
    current = next(row for row in rows if row["work_id"] == work_ids[0])
    assert stale["status"] == "retired"
    assert stale["payload"]["superseded_reason"] == "fund_implementation_identity_advanced"
    assert current["kind"] == FUND_IMPLEMENTATION_GAP_JOB_KIND
    assert current["payload"]["requested_fields"] == {
        "mechanics": ["portfolio_turnover"],
        "tax_fit": [
            "distribution_tax_character", "foreign_withholding_tax_rate",
            "trading_currency", "underlying_currency_exposure",
        ],
    }

    source = {
        "id": "issuer-aaa-report", "title": "AAA Annual Shareholder Report",
        "url": "https://issuer.example/aaa-report", "publisher": "AAA Issuer",
        "published_at": "2026-08-22T12:10:00Z",
        "accessed_at": "2026-08-22T12:20:00Z", "source_kind": "issuer",
        "supports": [
            "mechanics.portfolio_turnover", "tax_fit.distribution_tax_character",
            "tax_fit.foreign_withholding_tax_rate", "tax_fit.trading_currency",
            "tax_fit.underlying_currency_exposure",
        ],
    }
    acquisition = {
        "schema": "jaggedthoughts-fund-implementation-gap-evidence-v1",
        "request_sha256": request["request_sha256"],
        "prior_evidence_sha256": prior["evidence_sha256"],
        "candidate_leaf": request["candidate_leaf"],
        "candidate_sha256": request["candidate_sha256"],
        "comparison_program_sha256": request["comparison_program_sha256"],
        "entity_id": "AAA", "researched_at": "2026-08-22T12:25:00Z",
        "requested_coordinates": ["mechanics", "tax_fit"],
        "findings": {
            "mechanics": {"status": "observed", "values": {"portfolio_turnover": 0.15},
                          "source_refs": ["issuer-aaa-report"]},
            "tax_fit": {"status": "source_gap", "observed_values": {
                "trading_currency": "USD",
            }, "missing_fields": [
                "distribution_tax_character", "foreign_withholding_tax_rate",
                "underlying_currency_exposure",
            ], "source_refs": ["issuer-aaa-report"]},
        },
        "sources": [source], "capital_authority": False,
    }
    merged = compile_fund_implementation_gap_evidence(
        request=request, prior_evidence=prior, acquisition=acquisition,
        accepted_at="2026-08-22T12:30:00Z",
    )
    assert merged["findings"]["fees"] == prior["findings"]["fees"]
    assert merged["findings"]["holdings"] == prior["findings"]["holdings"]
    assert merged["findings"]["liquidity"] == prior["findings"]["liquidity"]
    assert merged["evidence_sha256"] != prior["evidence_sha256"]
    assert merged["prior_evidence_sha256"] == prior["evidence_sha256"]
    assert merged["capital_authority"] is False
    evidence_path.write_text(json.dumps(merged))
    assert current_fund_implementation_gap_targets(tmp_path) == []

    bad = json.loads(json.dumps(acquisition))
    bad["findings"]["mechanics"]["source_refs"] = ["undeclared"]
    with pytest.raises(ValueError, match="undeclared sources"):
        compile_fund_implementation_gap_evidence(
            request=request, prior_evidence=prior, acquisition=bad,
            accepted_at="2026-08-22T12:30:00Z",
        )
