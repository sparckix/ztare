import csv
import hashlib
import json

import pytest
import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.contracts import MetricObservation
from ztare.investment.discovery import _select_share_basis
from ztare.investment.observation_index import (
    build_observation_index,
    load_observation_rows,
)
from ztare.investment.sources import (
    SourceReceipt,
    _parse_yahoo_chart_observations,
    compact_legacy_yahoo_price_identities,
    compile_latest_observation_projection,
    consume_public_sources,
    project_cached_yahoo_adjusted_prices,
)
from ztare.investment.source_epoch import (
    compile_source_epoch,
    derivation_identity,
    validate_source_epoch,
)
from ztare.investment.workspace import _current_source_run, _latest_observations


def test_latest_projection_is_point_in_time_and_order_invariant() -> None:
    rows = (
        MetricObservation("old", "ACME", "price", 10, "USD", "2026-08-10T00:00:00Z", "2026-08-10T01:00:00Z", "feed"),
        MetricObservation("new", "ACME", "price", 11, "USD", "2026-08-11T00:00:00Z", "2026-08-11T01:00:00Z", "feed"),
        MetricObservation("future", "ACME", "price", 99, "USD", "2026-08-13T00:00:00Z", "2026-08-13T01:00:00Z", "feed"),
    )
    forward = compile_latest_observation_projection(rows, as_of="2026-08-12T00:00:00Z")
    reverse = compile_latest_observation_projection(reversed(rows), as_of="2026-08-12T00:00:00Z")

    assert forward == reverse
    assert forward["observation_count"] == 3
    assert [row["observation_id"] for row in forward["observations"]] == ["new"]


def test_observation_index_matches_csv_point_in_time_projection(tmp_path) -> None:
    path = tmp_path / "observations.csv"
    rows = (
        MetricObservation("old", "ACME", "adjusted_price", 10, "USD", "2026-08-10T00:00:00Z", "2026-08-10T01:00:00Z", "feed"),
        MetricObservation("revision", "ACME", "adjusted_price", 11, "USD", "2026-08-10T00:00:00Z", "2026-08-11T01:00:00Z", "feed"),
        MetricObservation("next", "ACME", "adjusted_price", 12, "USD", "2026-08-12T00:00:00Z", "2026-08-12T01:00:00Z", "feed"),
        MetricObservation("other", "OTHER", "adjusted_price", 20, "USD", "2026-08-10T00:00:00Z", "2026-08-10T01:00:00Z", "feed"),
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].to_dict())
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)
    receipt = build_observation_index(path, rows, as_of="2026-08-12T12:00:00Z")
    indexed = load_observation_rows(
        path, as_of="2026-08-11T12:00:00Z", entity_ids=("ACME",),
        metric_ids=("adjusted_price",), effective_per_observed=True,
    )
    (tmp_path / "observation_index.sqlite3").unlink()
    fallback = load_observation_rows(
        path, as_of="2026-08-11T12:00:00Z", entity_ids=("ACME",),
        metric_ids=("adjusted_price",), effective_per_observed=True,
    )

    assert receipt["observation_count"] == 4
    assert indexed == fallback
    assert [row["observation_id"] for row in indexed] == ["revision"]


def test_cached_yahoo_projection_is_verified_and_idempotent(tmp_path) -> None:
    source_id = "yahoo_acme_daily"
    retrieved_at = "2026-08-10T12:00:00Z"
    payload = {"chart": {"error": None, "result": [{
        "timestamp": [1_786_291_200],
        "meta": {"currency": "USD"},
        "indicators": {
            "quote": [{"close": [10.0]}],
            "adjclose": [{"adjclose": [9.5]}],
        },
    }]}}
    content = json.dumps(payload).encode()
    raw = tmp_path / "sources" / "raw" / source_id / "yahoo-chart.json"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(content)
    source = {
        "id": source_id, "adapter": "yahoo_chart_daily", "enabled": True,
        "symbol": "ACME", "entity_id": "ACME", "metric_id": "price", "unit": "USD",
    }
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump({
        "schema": "jaggedthoughts-public-source-manifest-v1", "as_of": "now",
        "sources": [source],
    }), encoding="utf-8")
    receipt = SourceReceipt(
        source_id=source_id, adapter="yahoo_chart_daily",
        canonical_url="https://query1.finance.yahoo.com/v8/finance/chart/ACME",
        retrieved_at=retrieved_at, content_sha256=hashlib.sha256(content).hexdigest(),
        raw_path=raw.relative_to(tmp_path).as_posix(), media_type="application/json",
        availability_mode="retrieval_only", observation_count=1, provider_note="fixture",
    ).to_dict()
    data = tmp_path / "data"
    data.mkdir()
    (data / "source_receipt_heads.json").write_text(json.dumps({
        "schema": "jaggedthoughts-public-source-receipt-heads-v1",
        "as_of": retrieved_at, "receipts": [receipt],
    }), encoding="utf-8")
    (data / "latest_observations.json").write_text(json.dumps({
        "schema": "jaggedthoughts-latest-observation-projection-v1",
        "as_of": retrieved_at, "observation_count": 0, "latest_count": 0,
        "observations": [],
    }), encoding="utf-8")

    first = project_cached_yahoo_adjusted_prices(manifest, workspace=tmp_path)
    second = project_cached_yahoo_adjusted_prices(manifest, workspace=tmp_path)

    assert first["provider_call_count"] == 0
    assert first["added_observation_count"] == 1
    assert second["status"] == "up_to_date"
    with (data / "observations.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["metric_id"], row["available_at"]) for row in rows] == [
        ("adjusted_price", retrieved_at),
    ]


def test_yahoo_history_identity_is_stable_across_retrievals() -> None:
    payload = json.dumps({"chart": {"error": None, "result": [{
        "timestamp": [1_786_291_200], "meta": {"currency": "USD"},
        "indicators": {
            "quote": [{"close": [10.0]}],
            "adjclose": [{"adjclose": [9.5]}],
        },
    }]}}).encode()
    source = {
        "id": "yahoo_acme_daily", "symbol": "ACME", "entity_id": "ACME",
        "metric_id": "price", "unit": "USD",
    }

    first = _parse_yahoo_chart_observations(
        payload, source, "2026-08-10T12:00:00Z",
    )
    later = _parse_yahoo_chart_observations(
        payload, source, "2026-08-11T12:00:00Z",
    )

    assert [row.observation_id for row in first] == [row.observation_id for row in later]
    assert first[0].available_at != later[0].available_at


def test_yahoo_split_event_is_typed_and_retrieval_bound() -> None:
    payload = json.dumps({"chart": {"error": None, "result": [{
        "timestamp": [1_786_291_200], "meta": {"currency": "USD"},
        "indicators": {"quote": [{"close": [10.0]}]},
        "events": {"splits": {"event": {
            "date": 1_775_482_200, "numerator": 25.0,
            "denominator": 1.0, "splitRatio": "25:1",
        }}},
    }]}}).encode()
    rows = _parse_yahoo_chart_observations(payload, {
        "id": "yahoo_acme_daily", "symbol": "ACME", "entity_id": "ACME",
        "metric_id": "price", "unit": "USD",
    }, "2026-08-14T23:00:00Z")

    split = next(row for row in rows if row.metric_id == "stock_split_ratio")
    assert (split.value, split.unit, split.available_at) == (
        25.0, "new_shares/old_share", "2026-08-14T23:00:00Z",
    )


def test_yahoo_omits_nonpositive_price_coordinates() -> None:
    payload = json.dumps({"chart": {"error": None, "result": [{
        "timestamp": [1_786_291_200], "meta": {"currency": "USD"},
        "indicators": {
            "quote": [{"close": [10.0]}],
            "adjclose": [{"adjclose": [0.0]}],
        },
    }]}}).encode()

    rows = _parse_yahoo_chart_observations(payload, {
        "id": "yahoo_acme_daily", "symbol": "ACME", "entity_id": "ACME",
        "metric_id": "price", "unit": "USD",
    }, "2026-08-14T23:00:00Z")

    assert [(row.metric_id, row.value) for row in rows] == [("price", 10.0)]


def test_yahoo_daily_source_rejects_provider_granularity_drift() -> None:
    payload = json.dumps({"chart": {"error": None, "result": [{
        "timestamp": [1_786_291_200],
        "meta": {"symbol": "ACME", "dataGranularity": "1mo"},
        "indicators": {"quote": [{"close": [10.0]}]},
    }]}}).encode()

    with pytest.raises(ValueError, match="granularity 1mo"):
        _parse_yahoo_chart_observations(payload, {
            "id": "yahoo_acme_daily", "symbol": "ACME", "entity_id": "ACME",
            "metric_id": "price", "unit": "USD", "interval": "1d",
        }, "2026-08-14T23:00:00Z")


def test_legacy_yahoo_price_ids_collapse_without_touching_other_adapters() -> None:
    source = {
        "id": "yahoo_acme_daily", "adapter": "yahoo_chart_daily",
        "symbol": "ACME", "entity_id": "ACME", "metric_id": "price",
    }
    current = _parse_yahoo_chart_observations(json.dumps({"chart": {
        "error": None, "result": [{"timestamp": [1_786_291_200],
        "meta": {"currency": "USD"}, "indicators": {"quote": [{"close": [10.0]}]}}],
    }}).encode(), source, "2026-08-14T23:00:00Z")[0]
    legacy = MetricObservation(
        "legacy-retrieval-bound-id", current.entity_id, current.metric_id,
        current.value, current.unit, current.observed_at,
        "2026-08-13T23:00:00Z", current.source_ref,
    )
    other = MetricObservation(
        "other-id", "ACME", "price", 10.0, "USD", current.observed_at,
        "2026-08-12T23:00:00Z", "sec_acme_companyfacts",
    )

    rows, receipt = compact_legacy_yahoo_price_identities(
        (current, legacy, other), {"sources": [source]},
    )

    collapsed = next(row for row in rows if row.source_ref == source["id"])
    assert (collapsed.observation_id, collapsed.available_at) == (
        current.observation_id, legacy.available_at,
    )
    assert (receipt["before_count"], receipt["after_count"], receipt["collapsed_count"]) == (2, 1, 1)
    assert any(row.observation_id == "other-id" for row in rows)


def test_yahoo_canonical_identity_rejects_content_drift() -> None:
    source = {"id": "yahoo_acme_daily", "adapter": "yahoo_chart_daily", "symbol": "ACME"}
    rows = tuple(
        MetricObservation(
            f"legacy-{entity}", entity, "price", 10.0, "USD",
            "2026-08-14T13:30:00Z", "2026-08-14T23:00:00Z", source["id"],
        )
        for entity in ("ACME", "OTHER")
    )
    with pytest.raises(ValueError, match="identity changed content"):
        compact_legacy_yahoo_price_identities(rows, {"sources": [source]})


def test_share_basis_fails_closed_until_a_post_split_fact_exists() -> None:
    def row(metric, value, observed):
        return {
            "observation_id": metric, "entity_id": "ACME", "metric_id": metric,
            "value": value, "observed_at": observed,
            "available_at": "2026-08-14T23:00:00Z", "source_ref": metric,
        }

    price = row("price", 10.0, "2026-08-14T00:00:00Z")
    latest = {
        ("ACME", "diluted_shares"): row(
            "diluted_shares", 10.0, "2025-12-31T23:59:59Z",
        ),
        ("ACME", "stock_split_ratio"): row(
            "stock_split_ratio", 25.0, "2026-04-06T13:30:00Z",
        ),
    }
    with pytest.raises(ValueError, match="corporate_action_share_basis_incompatible"):
        _select_share_basis(
            latest, "ACME", price=price, as_of="2026-08-15T00:00:00Z",
            max_age_days=550,
        )

    latest[("ACME", "diluted_shares_current")] = row(
        "diluted_shares_current", 250.0, "2026-06-30T23:59:59Z",
    )
    shares, receipt, _ = _select_share_basis(
        latest, "ACME", price=price, as_of="2026-08-15T00:00:00Z",
        max_age_days=550,
    )
    assert shares["value"] == 250.0
    assert receipt["status"] == "post_split_share_basis"


def test_source_epoch_rejects_mixed_or_mutated_current_artifacts(tmp_path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    observation = MetricObservation(
        "one", "ACME", "price", 10, "USD", "2026-08-10T00:00:00Z",
        "2026-08-10T01:00:00Z", "feed",
    )
    with (data / "observations.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=observation.to_dict())
        writer.writeheader()
        writer.writerow(observation.to_dict())
    projection = compile_latest_observation_projection(
        (observation,), as_of="2026-08-10T02:00:00Z",
    )
    (data / "latest_observations.json").write_text(json.dumps(projection), encoding="utf-8")
    heads = {"schema": "heads-v1", "receipts": []}
    (data / "source_receipt_heads.json").write_text(json.dumps(heads), encoding="utf-8")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text("schema: jaggedthoughts-public-source-manifest-v1\nsources: []\n")
    run_body = {
        "schema": "jaggedthoughts-public-source-run-v1", "ok": True,
        "as_of": projection["as_of"], "retrieved_at": projection["as_of"],
        "observation_count": 1,
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}
    (data / "latest_source_run.json").write_text(json.dumps(run), encoding="utf-8")
    epoch = compile_source_epoch(
        tmp_path,
        source_run_path=data / "latest_source_run.json",
        projection_path=data / "latest_observations.json",
        observations_path=data / "observations.csv",
        receipt_heads_path=data / "source_receipt_heads.json",
        source_manifest_path=manifest,
        derivation=derivation_identity(
            [], derive_metrics=True, metric_universe_sha256="a" * 64,
        ),
    )
    epoch_path = data / "latest_source_epoch.json"
    epoch_path.write_text(json.dumps(epoch), encoding="utf-8")

    assert validate_source_epoch(tmp_path, epoch_path)["projection"] == projection
    stream = data / "observations.csv"
    published = stream.read_bytes()
    stream.write_bytes(published + b"append-in-progress")
    with pytest.raises(ValueError, match="observation-store binding"):
        validate_source_epoch(tmp_path, epoch_path)
    stream.write_bytes(published)
    (data / "latest_observations.json").write_text(
        json.dumps({**projection, "latest_count": 99}), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="projection binding"):
        validate_source_epoch(tmp_path, epoch_path)


def test_alternate_receipt_lane_advances_one_canonical_source_head(tmp_path) -> None:
    (tmp_path / "input.csv").write_text(
        "entity,value,observed,available\nACME,11,2026-08-10,2026-08-11\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump({
        "schema": "jaggedthoughts-public-source-manifest-v1", "as_of": "now",
        "sources": [{
            "id": "local-price", "adapter": "local_csv", "path": "input.csv",
            "mappings": [{
                "entity_id": "ACME", "metric_id": "price", "unit": "USD",
                "value_column": "value", "observed_at_column": "observed",
                "available_at_column": "available",
            }],
        }],
    }), encoding="utf-8")
    run = consume_public_sources(
        manifest, workspace=tmp_path, receipt_dir=tmp_path / "market_state",
        retrieved_at="2026-08-12T00:00:00Z", derive_metrics=False, strict=True,
    )

    validated = validate_source_epoch(
        tmp_path, tmp_path / "data" / "latest_source_epoch.json",
    )
    current = _current_source_run(tmp_path)
    canonical_run = json.loads(
        (tmp_path / "data" / "latest_source_run.json").read_text(encoding="utf-8")
    )
    assert validated["manifest"]["latest_projection"]["path"].startswith("market_state/")
    assert validated["source_run"]["run_sha256"] == run["run_sha256"]
    assert canonical_run["run_sha256"] == current["run_sha256"] == run["run_sha256"]
    assert [row["value"] for row in _latest_observations(tmp_path, current)] == [11.0]
