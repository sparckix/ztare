import json
from pathlib import Path

from ztare.common.equivariance import stable_sha256
from ztare.investment.closed_book import (
    CLOSED_BOOK_RUN_SCHEMA,
    closed_book_price_refresh_entity_ids,
)
from ztare.investment import portfolio_policy as portfolio


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _signed(payload: dict, field: str) -> dict:
    return {**payload, field: stable_sha256(payload)}


def test_pending_policy_windows_request_only_entry_or_due_exit_prices(tmp_path: Path) -> None:
    closed = {
        "schema": CLOSED_BOOK_RUN_SCHEMA,
        "run_id": "closed-1",
        "evidence_packet": {
            "entity": {"entity_id": "AAA"},
            "benchmark": {"entity_id": "SPY"},
        },
    }
    _write(tmp_path / "closed_book/runs/closed-1.json", closed)
    assert closed_book_price_refresh_entity_ids(
        tmp_path, as_of="2026-08-22T00:00:00Z",
    ) == ["AAA", "SPY"]

    risk = _signed({
        "schema": "jaggedthoughts-portfolio-risk-evaluation-contract-v1",
    }, "risk_evaluation_contract_sha256")
    policy_body = {
        "schema": portfolio.PORTFOLIO_POLICY_RUN_SCHEMA,
        "run_id": "policy-1",
        "horizon_days": portfolio.PRIMARY_HORIZON_DAYS,
        "estimand_role": "primary_patient_capital_policy_evidence",
        "trial_family": {"policy_versions": {"equity_equal_weight": portfolio._POLICY_VERSION}},
        "benchmark": {"entity_id": "SPY"},
        "universe": [{"entity_id": "AAA"}],
        "fund_program_universe": [{"entity_id": "FUND"}],
        "settlement_contract": {
            "transaction_cost_bps": 5.0,
            "score_contract_version": portfolio._SCORE_CONTRACT_VERSION,
            "cost_application": portfolio._COST_APPLICATION,
            "risk_challenger_evaluation": risk,
            "prospective_return_window": {
                "schema": portfolio.RETURN_WINDOW_SCHEMA,
                "price_identity": portfolio._RETURN_PRICE_IDENTITY,
                "transaction_cost_bps": 5.0,
            },
        },
    }
    _write(
        tmp_path / "portfolio_policy/runs/policy-1.json",
        _signed(policy_body, "run_sha256"),
    )
    assert portfolio.portfolio_policy_price_refresh_entity_ids(
        tmp_path, as_of="2026-08-22T00:00:00Z",
    ) == ["AAA", "FUND", "SPY"]

    binding = {"binding": {
        "status": "bound", "scheduled_exit_at": "2026-09-01T00:00:00Z",
    }}
    _write(tmp_path / "closed_book/return_windows/closed-1.json", binding)
    _write(tmp_path / "portfolio_policy/return_windows/policy-1.json", binding)
    assert closed_book_price_refresh_entity_ids(
        tmp_path, as_of="2026-08-31T00:00:00Z",
    ) == []
    assert portfolio.portfolio_policy_price_refresh_entity_ids(
        tmp_path, as_of="2026-09-01T00:00:00Z",
    ) == ["AAA", "FUND", "SPY"]
