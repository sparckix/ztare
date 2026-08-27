import csv
import hashlib
import json
from pathlib import Path

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.evidence_vault import (
    capture_public_source_run,
    evidence_manifest_ref,
    evidence_vault_status,
    reconstruct_evidence_as_of,
)
from ztare.investment.golden_store import GoldenStore
from ztare.investment.point_in_time_replay import (
    compile_archived_accounting_replay,
    compile_point_in_time_forecast_replay,
    compile_sealed_walk_forward_readiness,
    run_sealed_walk_forward_cycle,
)
from ztare.investment.sources import consume_public_sources


def _sealed(body, key):
    return {**body, key: stable_sha256(body)}


def _receipt(
    root: Path, source_id: str, content: bytes, retrieved_at: str,
    availability_mode: str = "retrieval_only",
):
    relative = Path("sources/raw") / source_id / f"local-{hashlib.sha256(content).hexdigest()[:20]}.csv"
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_bytes(content)
    return _sealed({
        "schema": "jaggedthoughts-public-source-receipt-v1",
        "source_id": source_id, "adapter": "local_csv",
        "canonical_url": f"workspace:{source_id}.csv", "retrieved_at": retrieved_at,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "raw_path": relative.as_posix(), "media_type": "text/csv",
        "availability_mode": availability_mode, "observation_count": 1,
        "provider_note": "test",
    }, "receipt_sha256")


def _observations(root: Path, rows):
    path = root / "data/observations.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "observation_id", "entity_id", "metric_id", "value", "unit",
            "observed_at", "available_at", "source_ref",
        ))
        writer.writeheader(); writer.writerows(rows)


def test_vault_deduplicates_and_reconstructs_only_captured_information(tmp_path: Path):
    at1, at2 = "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"
    receipt1 = _receipt(tmp_path, "public-a", b"v1", at1)
    rows = [{
        "observation_id": "a:1", "entity_id": "A", "metric_id": "price",
        "value": 10, "unit": "USD", "observed_at": "2026-01-01T00:00:00Z",
        "available_at": at1, "source_ref": "public-a",
    }]
    _observations(tmp_path, rows)
    run1 = _sealed({"schema": "jaggedthoughts-public-source-run-v1", "as_of": at1,
                    "retrieved_at": at1, "source_receipts": [receipt1]}, "run_sha256")
    first = capture_public_source_run(tmp_path, run1, ingested_at="2026-01-02T00:01:00Z")
    again = capture_public_source_run(tmp_path, run1, ingested_at="2026-01-02T00:01:00Z")
    assert first["manifest_leaf_sha256"] == again["manifest_leaf_sha256"]
    assert reconstruct_evidence_as_of(tmp_path, as_of=at1)["observations"] == []

    receipt2 = _receipt(tmp_path, "public-a", b"v2", at2)
    rows.append({**rows[0], "observation_id": "a:2", "value": 11, "observed_at": at2,
                 "available_at": at2})
    _observations(tmp_path, rows)
    run2 = _sealed({"schema": "jaggedthoughts-public-source-run-v1", "as_of": at2,
                    "retrieved_at": at2, "source_receipts": [receipt2]}, "run_sha256")
    second = capture_public_source_run(tmp_path, run2, ingested_at="2026-01-03T00:01:00Z")
    old = reconstruct_evidence_as_of(tmp_path, as_of="2026-01-02T12:00:00Z")
    new = reconstruct_evidence_as_of(tmp_path, as_of="2026-01-03T12:00:00Z")
    assert [row["value"] for row in old["observations"]] == [10.0]
    assert [row["value"] for row in new["observations"]] == [10.0, 11.0]
    assert new["sources"][0]["leakage_classification"] == "retrieval_floor"
    assert new["authority"]["capital_authority"] is False
    old_ref = evidence_manifest_ref(
        tmp_path, as_of="2026-01-02T12:00:00Z", required_source_ids=("public-a",),
    )
    new_ref = evidence_manifest_ref(
        tmp_path, as_of="2026-01-03T12:00:00Z", required_source_ids=("public-a",),
    )
    missing_ref = evidence_manifest_ref(
        tmp_path, as_of="2026-01-03T12:00:00Z", required_source_ids=("public-b",),
    )
    assert old_ref["manifest_leaf_sha256"] == first["manifest_leaf_sha256"]
    assert new_ref["manifest_leaf_sha256"] == second["manifest_leaf_sha256"]
    assert missing_ref["status"] == "required_sources_unarchived"
    status = evidence_vault_status(tmp_path)
    assert status["integrity_verified"] and status["observation_count"] == 2
    store = GoldenStore(tmp_path / "state/golden_store.sqlite3")
    assert len(store.list_leaves(limit=20)) == 4
    manifest = store.get_leaf(second["manifest_leaf_sha256"])["payload"]
    snapshot = store.get_leaf(manifest["snapshots"][0]["snapshot_leaf_sha256"])["payload"]
    assert snapshot["observation_set"]["upsert_count"] == 1

    at3 = "2026-01-04T00:00:00Z"
    receipt3 = _receipt(tmp_path, "public-a", b"v3", at3)
    _observations(tmp_path, rows[1:])
    run3 = _sealed({"schema": "jaggedthoughts-public-source-run-v1", "as_of": at3,
                    "retrieved_at": at3, "source_receipts": [receipt3]}, "run_sha256")
    capture_public_source_run(tmp_path, run3, ingested_at="2026-01-04T00:01:00Z")
    latest = reconstruct_evidence_as_of(tmp_path, as_of="2026-01-04T12:00:00Z")
    assert [row["observation_id"] for row in latest["observations"]] == ["a:2"]


def test_source_consumer_activates_vault_without_provider_credentials(tmp_path: Path):
    (tmp_path / "input.csv").write_text(
        "entity,metric,value,unit,observed,available\nA,price,10,USD,2026-01-01,2026-01-02\n"
    )
    manifest = {"schema": "jaggedthoughts-public-source-manifest-v1", "as_of": "now", "sources": [{
        "id": "local-public", "adapter": "local_csv", "path": "input.csv",
        "mappings": [{"entity_id": "A", "metric_id": "price",
                      "value_column": "value", "unit": "USD",
                      "observed_at_column": "observed", "available_at_column": "available"}],
    }]}
    manifest_path = tmp_path / "sources.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))
    run = consume_public_sources(
        manifest_path, workspace=tmp_path, retrieved_at="2026-01-04T00:00:00Z",
        derive_metrics=False, strict=True,
    )
    capture = json.loads((tmp_path / "evidence_vault/latest_capture.json").read_text())
    rebuilt = reconstruct_evidence_as_of(tmp_path, as_of=capture["ingested_at"])
    assert run["evidence_vault"]["activation"] == "automatic_after_source_ingestion"
    assert [row["observation_id"] for row in rebuilt["observations"]]


def test_sealed_replay_scores_only_post_issue_archived_prices(tmp_path: Path, monkeypatch):
    from ztare.investment import evidence_vault

    def price(observation_id, entity_id, value, observed_at, source_ref):
        return {
            "observation_id": observation_id, "entity_id": entity_id,
            "metric_id": "adjusted_price", "value": value, "unit": "USD",
            "observed_at": observed_at, "available_at": observed_at,
            "source_ref": source_ref,
        }

    issue_rows = [
        price("a0", "A", 100, "2025-06-30T00:00:00Z", "prices-a"),
        price("a1", "A", 110, "2025-12-31T00:00:00Z", "prices-a"),
        price("b0", "SPY", 100, "2025-06-30T00:00:00Z", "prices-b"),
        price("b1", "SPY", 105, "2025-12-31T00:00:00Z", "prices-b"),
    ]
    _observations(tmp_path, issue_rows)
    receipts = [
        _receipt(tmp_path, source, f"{source}-v1".encode(), "2025-12-31T23:00:00Z")
        for source in ("prices-a", "prices-b")
    ]
    run = _sealed({
        "schema": "jaggedthoughts-public-source-run-v1",
        "as_of": "2025-12-31T23:00:00Z", "retrieved_at": "2025-12-31T23:00:00Z",
        "source_receipts": receipts,
    }, "run_sha256")
    monkeypatch.setattr(evidence_vault, "_utc_now", lambda: "2026-01-01T00:00:00Z")
    capture_public_source_run(tmp_path, run)

    outcome_rows = issue_rows + [
        price("a2", "A", 112, "2026-01-02T00:00:00Z", "prices-a"),
        price("a3", "A", 120, "2026-01-09T00:00:00Z", "prices-a"),
        price("b2", "SPY", 106, "2026-01-02T00:00:00Z", "prices-b"),
        price("b3", "SPY", 108, "2026-01-09T00:00:00Z", "prices-b"),
    ]
    _observations(tmp_path, outcome_rows)
    receipts = [
        _receipt(tmp_path, source, f"{source}-v2".encode(), "2026-01-09T23:00:00Z")
        for source in ("prices-a", "prices-b")
    ]
    run = _sealed({
        "schema": "jaggedthoughts-public-source-run-v1",
        "as_of": "2026-01-09T23:00:00Z", "retrieved_at": "2026-01-09T23:00:00Z",
        "source_receipts": receipts,
    }, "run_sha256")
    monkeypatch.setattr(evidence_vault, "_utc_now", lambda: "2026-01-10T00:00:00Z")
    capture_public_source_run(tmp_path, run)

    replay = compile_point_in_time_forecast_replay(tmp_path, {
        "schema": "jaggedthoughts-point-in-time-replay-profile-v1",
        "replay_id": "a-vs-spy", "program_id": "six_month_active_momentum_control",
        "entity_id": "A", "benchmark_id": "SPY",
        "issued_at": "2026-01-01T01:00:00Z", "start_at": "2026-01-02T00:00:00Z",
        "evaluated_at": "2026-01-10T01:00:00Z", "horizon_days": 7,
        "price_metric_id": "adjusted_price",
        "source_ids": ["prices-a", "prices-b"], "capital_authority": False,
    })
    assert replay["evaluation_integrity"]["backtest_evidence_eligible"] is True
    assert replay["temporal_integrity"]["entry_and_exit_absent_at_issue"] is True
    assert replay["return_window_binding"]["entry_points"]["A"]["observation_id"] == "a2"
    assert replay["return_window_settlement"]["exit_points"]["A"]["observation_id"] == "a3"
    assert replay["price_metric_id"] == "adjusted_price"
    assert replay["capital_authority"] is False


def test_walk_forward_readiness_refuses_backfill_and_unmatured_windows(
    tmp_path: Path, monkeypatch,
):
    captured_at = "2026-01-01T00:01:00Z"
    rows = [{
        "observation_id": f"{entity}:p0", "entity_id": entity,
        "metric_id": "adjusted_price", "value": 100, "unit": "USD",
        "observed_at": "2025-12-31T21:00:00Z",
        "available_at": "2026-01-01T00:00:00Z", "source_ref": source,
    } for entity, source in (
        ("A", "prices-a"), ("F", "prices-f"), ("SPY", "prices-spy"),
    )]
    _observations(tmp_path, rows)
    receipts = [
        _receipt(tmp_path, source, source.encode(), "2026-01-01T00:00:00Z")
        for source in ("prices-a", "prices-f", "prices-spy")
    ]
    run = _sealed({
        "schema": "jaggedthoughts-public-source-run-v1",
        "as_of": "2026-01-01T00:00:00Z",
        "retrieved_at": "2026-01-01T00:00:00Z", "source_receipts": receipts,
    }, "run_sha256")
    monkeypatch.setattr("ztare.investment.evidence_vault._utc_now", lambda: captured_at)
    capture_public_source_run(tmp_path, run)

    readiness = compile_sealed_walk_forward_readiness(tmp_path, {
        "schema": "jaggedthoughts-sealed-walk-forward-profile-v1",
        "evaluation_id": "cross-kind-seed",
        "program_ids": ["no_active_edge_control", "six_month_active_momentum_control"],
        "minimum_inference_blocks": 5,
        "subjects": [
            {"entity_id": "A", "entity_kind": "public_equity",
             "price_source_id": "prices-a", "benchmark_id": "SPY",
             "benchmark_source_id": "prices-spy"},
            {"entity_id": "F", "entity_kind": "public_fund",
             "price_source_id": "prices-f", "benchmark_id": "SPY",
             "benchmark_source_id": "prices-spy"},
        ],
        "windows": [
            {"window_id": "unrecoverable", "issued_at": "2025-12-31T00:00:00Z",
             "start_at": "2026-01-01T00:00:00Z",
             "evaluated_at": "2026-01-10T00:00:00Z", "horizon_days": 7},
            {"window_id": "prospective", "issued_at": "2026-01-01T01:00:00Z",
             "start_at": "2026-01-02T00:00:00Z",
             "evaluated_at": "2026-01-10T00:00:00Z", "horizon_days": 7},
        ],
        "capital_authority": False,
    })
    cells = {row["cell_id"]: row for row in readiness["cells"]}
    assert readiness["status"] == "archive_not_ready"
    assert readiness["entity_kinds"] == ["public_equity", "public_fund"]
    assert cells["unrecoverable:A"]["historical_backfill_forbidden"] is True
    assert cells["prospective:F"]["issue_snapshot_available_at"]["prices-f"] == captured_at
    assert "matured_outcome_capture_missing" in cells["prospective:F"]["blockers"]
    assert readiness["capital_authority"] is False


def test_walk_forward_cycle_seals_then_settles_on_later_market_capture(
    tmp_path: Path, monkeypatch,
):
    def price(observation_id, entity_id, value, observed_at, source_ref):
        return {
            "observation_id": observation_id, "entity_id": entity_id,
            "metric_id": "adjusted_price", "value": value, "unit": "USD",
            "observed_at": observed_at, "available_at": observed_at,
            "source_ref": source_ref,
        }

    sources = ("prices-a", "prices-spy")
    issue_rows = [
        price("a0", "A", 100, "2025-06-30T00:00:00Z", sources[0]),
        price("a1", "A", 110, "2025-12-31T00:00:00Z", sources[0]),
        price("s0", "SPY", 100, "2025-06-30T00:00:00Z", sources[1]),
        price("s1", "SPY", 105, "2025-12-31T00:00:00Z", sources[1]),
    ]

    def capture(rows, at, version):
        _observations(tmp_path, rows)
        receipts = [
            _receipt(tmp_path, source, f"{source}-{version}".encode(), at)
            for source in sources
        ]
        run = _sealed({
            "schema": "jaggedthoughts-public-source-run-v1",
            "as_of": at, "retrieved_at": at, "source_receipts": receipts,
        }, "run_sha256")
        monkeypatch.setattr("ztare.investment.evidence_vault._utc_now", lambda: at)
        capture_public_source_run(tmp_path, run)

    capture(issue_rows, "2026-01-01T00:01:00Z", "issue")
    profile = {
        "schema": "jaggedthoughts-sealed-walk-forward-profile-v1",
        "evaluation_id": "walk-forward-cycle",
        "program_ids": ["no_active_edge_control", "six_month_active_momentum_control"],
        "minimum_inference_blocks": 5,
        "subjects": [{
            "entity_id": "A", "entity_kind": "public_equity",
            "price_source_id": sources[0], "benchmark_id": "SPY",
            "benchmark_source_id": sources[1],
        }],
        "windows": [{
            "window_id": "jan", "issued_at": "2026-01-02T00:00:00Z",
            "start_at": "2026-01-03T00:00:00Z",
            "evaluated_at": "2026-01-10T00:00:00Z", "horizon_days": 7,
        }],
        "capital_authority": False,
    }
    sealed = run_sealed_walk_forward_cycle(
        tmp_path, profile, as_of="2026-01-01T01:00:00Z",
    )
    assert sealed["run"]["plan_created"] is True
    assert sealed["run"]["issued_count"] == 0
    assert sealed["run"]["settled_count"] == 0

    issued = run_sealed_walk_forward_cycle(
        tmp_path, profile, as_of="2026-01-02T00:01:00Z",
    )
    assert issued["run"]["issued_count"] == 2
    assert issued["run"]["settled_count"] == 0
    assert issued["matrix_status"]["counts"]["awaiting_evaluation_time"] == 2
    assert all(
        row["materialized_at"] == "2026-01-02T00:01:00Z"
        for row in issued["matrix_status"]["cells"]
    )

    outcome_rows = issue_rows + [
        price("a2", "A", 111, "2026-01-03T00:00:00Z", sources[0]),
        price("a3", "A", 120, "2026-01-10T00:00:00Z", sources[0]),
        price("s2", "SPY", 106, "2026-01-03T00:00:00Z", sources[1]),
        price("s3", "SPY", 108, "2026-01-10T00:00:00Z", sources[1]),
    ]
    capture(outcome_rows, "2026-01-11T00:01:00Z", "outcome")
    settled = run_sealed_walk_forward_cycle(
        tmp_path, profile, as_of="2026-01-11T00:02:00Z",
    )
    assert settled["run"]["settled_count"] == 2
    assert settled["run"]["issued_count"] == 0
    assert settled["matrix_status"]["status"] == "matrix_settled"
    assert settled["tournament"]["status"] == "compiled"
    assert settled["tournament"]["inference_block_count"] == 1
    assert settled["tournament"]["research_priority_evidence_eligible"] is False
    assert settled["matrix_status"]["tournament"][
        "research_priority_evidence_eligible"
    ] is False
    assert {
        row["outcome_evaluated_at"] for row in settled["matrix_status"]["cells"]
    } == {"2026-01-11T00:02:00Z"}
    assert run_sealed_walk_forward_cycle(
        tmp_path, profile, as_of="2026-01-12T00:00:00Z",
    )["status"] == "not_due"


def test_archived_filing_replay_separates_provider_dates_from_capture_floor(
    tmp_path: Path, monkeypatch,
):
    rows = []
    for year in range(2020, 2024):
        for metric, value in (
            ("revenue_fy", 100 + 10 * year), ("operating_cash_flow_fy", 25 + year),
            ("capital_expenditure_fy", 5 + year / 10), ("net_income_fy", 18 + year),
        ):
            rows.append({
                "observation_id": f"x:{metric}:{year}", "entity_id": "X",
                "metric_id": metric, "value": value, "unit": "USD/year",
                "observed_at": f"{year}-12-31T23:59:59Z",
                "available_at": f"{year + 1}-03-01T23:59:59Z",
                "source_ref": "sec_x_companyfacts",
            })
    _observations(tmp_path, rows)
    retrieved = "2025-04-01T00:00:00Z"
    receipt = _receipt(
        tmp_path, "sec_x_companyfacts", b"companyfacts", retrieved,
        "provider_filed_date",
    )
    run = _sealed({
        "schema": "jaggedthoughts-public-source-run-v1", "as_of": retrieved,
        "retrieved_at": retrieved, "source_receipts": [receipt],
    }, "run_sha256")
    monkeypatch.setattr(
        "ztare.investment.evidence_vault._utc_now", lambda: "2025-04-01T00:01:00Z",
    )
    capture_public_source_run(tmp_path, run)

    replay = compile_archived_accounting_replay(tmp_path)
    assert replay["episode_count"] > 0
    assert replay["evidence_packet_count"] == 2 * replay["episode_count"]
    assert replay["temporal_integrity"]["future_provider_row_leakage_pass"] is True
    assert replay["evaluation_authority"] == "retrospective_provider_date_mechanism_diagnostic"
    assert replay["episodes"][0]["temporal_integrity"]["archive_existed_at_issue"] is False
