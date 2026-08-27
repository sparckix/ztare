import csv
from pathlib import Path

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment import closed_book
from ztare.investment.golden_store import GoldenLeaf, GoldenStore


def test_authored_payoff_interval_opens_without_provider_and_settles(
    tmp_path: Path, monkeypatch,
) -> None:
    opened_at = "2026-01-01T00:00:00Z"
    candidate_body = {
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "equity:ACME",
        "entity_id": "ACME",
        "entity_kind": "public_equity",
        "screen_status": "qualified",
    }
    candidate_sha = stable_sha256(candidate_body)
    candidate = {**candidate_body, "candidate_sha256": candidate_sha}
    store_path = tmp_path / "state" / "golden.sqlite3"
    candidate_leaf = GoldenStore(store_path).append_leaf(GoldenLeaf(
        owner="paper", object_kind="discovery_candidate", object_id="equity:ACME",
        epoch=candidate_sha, occurred_at=opened_at, available_at=opened_at,
        payload=candidate, source_refs=("discovery:ACME",),
    ))

    def packet(*_args, opened_at: str, horizon_days: int, **_kwargs) -> dict:
        body = {
            "schema": "jaggedthoughts-closed-book-evidence-packet-v1",
            "opened_at": opened_at,
            "end_at": "2026-01-31T00:00:00Z",
            "horizon_days": horizon_days,
            "subject": {
                "kind": "discovery_candidate", "subject_id": "equity:ACME",
                "subject_sha256": candidate_sha,
            },
            "entity": {"entity_id": "ACME", "entity_kind": "public_equity"},
            "benchmark": {"entity_id": "SPY"},
            "valuation_summary": {}, "decision_summary": {}, "starting_market": {},
            "discovery_summary": {}, "field_availability": {"rows": []},
            "evidence_archive": {},
        }
        return {**body, "packet_sha256": stable_sha256(body)}

    monkeypatch.setattr(closed_book, "_utc_now", lambda: opened_at)
    monkeypatch.setattr(closed_book, "_discovery_evidence_packet", packet)
    monkeypatch.setattr(closed_book, "_deterministic_candidates", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(closed_book, "compile_underwriting_ablation_arms", lambda _packet: {})
    monkeypatch.setattr(closed_book, "subscription_runtime_version", lambda _runtime: "test")
    monkeypatch.setattr(
        closed_book, "SubscriptionJSONRole",
        lambda **_kwargs: pytest.fail("sealed payoff forecasts must not call a provider"),
    )
    result_body = {
        "schema": "jaggedthoughts-candidate-payoff-forecast-result-v1",
        "contract_id": "payoff:ACME:20260101", "contract_sha256": "c" * 64,
        "entity_id": "ACME", "candidate_leaf": candidate_leaf,
        "candidate_sha256": candidate_sha, "instrument_admission_sha256": "a" * 64,
        "valuation_envelope_sha256": "v" * 64, "dossier_sha256": "d" * 64,
        "information_cutoff": opened_at, "horizon_at": "2026-01-31T00:00:00Z",
        "horizon_days": 30, "comparator_entity_id": "SPY",
        "state_active_return_intervals": [],
        "expected_active_return_interval": {"low": 0.05, "high": 0.15},
        "underperformance_probability_interval": {"low": 0.2, "high": 0.4},
        "worst_case_active_return": -0.2, "probability_witnesses": {},
        "expected_return_identity": "forecast_interval_conditional_on_authored_worlds",
        "physical_probability_identity": "authored_forecast_intervals_not_observed_frequencies",
        "market_state_prices_identified": False, "rank_authority": False,
        "portfolio_authority": False, "capital_authority": False,
    }
    result = {**result_body, "forecast_result_sha256": stable_sha256(result_body)}
    run = closed_book.open_closed_book_forecast(
        tmp_path, owner="paper", store_path=store_path, candidate_leaf=candidate_leaf,
        horizon_days=30, payoff_forecast_result=result,
    )

    assert run["provider"]["called"] is False
    forecast = run["candidate_forecasts"][0]
    assert forecast["candidate_id"] == "candidate_payoff_forecast"
    assert forecast["target_weight"] == 0.0
    assert run["evidence_packet"]["candidate_payoff_forecast"] == result

    observations = tmp_path / "data" / "observations.csv"
    observations.parent.mkdir(parents=True)
    with observations.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "observation_id", "entity_id", "metric_id", "value", "observed_at",
            "available_at", "source_ref",
        ))
        writer.writeheader()
        for entity, entry, exit_ in (("ACME", 100, 110), ("SPY", 100, 100)):
            for suffix, value, instant in (
                ("entry", entry, "2026-01-02T00:00:00Z"),
                ("exit", exit_, "2026-02-01T00:00:00Z"),
            ):
                writer.writerow({
                    "observation_id": f"{entity}:{suffix}", "entity_id": entity,
                    "metric_id": "adjusted_price", "value": value,
                    "observed_at": instant, "available_at": instant,
                    "source_ref": f"test:{entity}:{suffix}",
                })
    monkeypatch.setattr(closed_book, "_utc_now", lambda: "2026-02-02T00:00:00Z")
    settled = closed_book.settle_due_closed_book_forecasts(
        tmp_path, owner="paper", store_path=store_path, as_of="2026-02-02T00:00:00Z",
    )["settlements"][0]
    score = settled["candidate_scores"][0]
    assert score["active_return_interval"]["contains_actual"] is True
    assert score["active_return_interval"]["miss_distance"] == 0.0
    assert score["underperformance_brier_interval"] == pytest.approx({
        "low": 0.04, "high": 0.16,
    })
