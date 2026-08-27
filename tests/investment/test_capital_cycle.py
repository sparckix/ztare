import json
from pathlib import Path

import yaml

from ztare.common.equivariance import stable_sha256

from ztare.investment.capital_cycle import (
    capital_cycle_status,
    compile_opportunity_book,
    default_capital_cycle_policy,
    due_forecast_windows,
    load_capital_cycle_policy,
    settlement_readiness,
)
from ztare.investment.market_state_forecast import _challengers, due_market_state_horizons


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _policy(tmp_path: Path) -> dict:
    path = tmp_path / "capital_cycle.yaml"
    path.write_text(yaml.safe_dump(default_capital_cycle_policy()), encoding="utf-8")
    return load_capital_cycle_policy(path)


def _decision(entity_id: str, stage: str, weight: float) -> dict:
    return {
        "schema": "jaggedthoughts-investment-decision-v1",
        "decision_id": f"{entity_id.lower()}-decision",
        "decision_record_sha256": entity_id.lower().ljust(64, "d")[:64],
        "as_of": "2026-08-09T00:00:00Z",
        "profile_lifecycle": {"data_class": "operator", "stage": stage},
        "entity": {"entity_id": entity_id, "name": entity_id},
        "summary": {"selected_action_id": "buy-small", "target_weight": weight},
    }


def test_opportunity_book_separates_research_priority_from_paper_authority(
    tmp_path: Path,
) -> None:
    policy = _policy(tmp_path)
    assert policy["portfolio_policy_diagnostic_risk_aversion"] == 3.0
    assert policy["paper_watch_auto_enrollment"] == {
        "enabled": False,
        "actor_id": "capital-cycle-paper-watch-policy-v1",
        "max_new_per_cycle": 4,
        "scope": "current_eligible_zero_weight_only",
    }
    _write_json(tmp_path / "decisions" / "acme.json", _decision("ACME", "active", 0.08))
    _write_json(tmp_path / "decisions" / "beta.json", _decision("BETA", "draft", 0.10))
    _write_json(tmp_path / "discovery" / "latest.json", {
        "schema": "jaggedthoughts-discovery-run-v1",
        "run_id": "discovery-1",
        "run_sha256": "a" * 64,
        "candidates": [
            {"candidate_id": "beta", "candidate_sha256": "b" * 64, "rank": 1,
             "research_rank": 1,
             "rank_score": 0.9, "entity_id": "BETA", "name": "Beta",
             "entity_kind": "public_equity", "screen_status": "qualified",
             "metrics": {"price_implied_excess_return": 0.08}, "source_refs": ["beta:source"]},
            {"candidate_id": "acme", "candidate_sha256": "c" * 64, "rank": 2,
             "rank_score": 0.6, "entity_id": "ACME", "name": "Acme",
             "entity_kind": "public_equity", "screen_status": "monitor",
             "metrics": {"quality": 0.8}, "source_refs": ["acme:source"]},
            {"candidate_id": "stale", "candidate_sha256": "s" * 64, "rank": 3,
             "rank_score": 0.4, "entity_id": "STALE", "name": "Stale",
             "entity_kind": "public_fund", "screen_status": "stale_evidence",
             "metrics": {}, "source_refs": ["stale:source"]},
        ],
    })

    book = compile_opportunity_book(
        tmp_path, policy=policy, generated_at="2026-08-10T00:00:00Z",
    )

    assert [book[key] for key in ("qualified_count", "research_count", "repair_count")] == [1, 1, 1]
    assert book["candidates"][0]["research_rank"] == 1
    assert book["candidates"][0]["learned_research_rank"] == 1
    assert book["candidates"][0]["learned_potential_rank"]["law_adjustment_applied"] is False
    assert book["candidates"][0]["research_priority_is_expected_return"] is False
    assert book["active_positions"] == [{
        "entity_id": "ACME", "decision_id": "acme-decision",
        "target_weight": 0.08, "selected_action_id": "buy-small",
    }]
    assert book["paper_posture"]["cash_weight"] == 0.92
    assert book["paper_posture"]["admissible"] is True
    assert book["capital_authority"] is False


def test_opportunity_book_preserves_fund_peer_lane_order(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    _write_json(tmp_path / "discovery" / "latest.json", {
        "schema": "jaggedthoughts-discovery-run-v1", "run_id": "fund-lanes",
        "run_sha256": "f" * 64, "candidates": [
            {"candidate_id": "fund:us:A", "candidate_sha256": "a" * 64,
             "rank": 2, "rank_score": .2, "entity_id": "A", "name": "A",
             "entity_kind": "public_fund", "screen_status": "monitor", "metrics": {},
             "potential_rank": {"scope": "public_fund", "rank": 1,
                                "comparison_scope": "implementation_sleeve:us"}},
            {"candidate_id": "fund:intl:B", "candidate_sha256": "b" * 64,
             "rank": 4, "rank_score": .9, "entity_id": "B", "name": "B",
             "entity_kind": "public_fund", "screen_status": "monitor", "metrics": {},
             "potential_rank": {"scope": "public_fund", "rank": 2,
                                "comparison_scope": "implementation_sleeve:intl"}},
            {"candidate_id": "fund:unbound:C", "candidate_sha256": "c" * 64,
             "rank": 6, "rank_score": None, "entity_id": "C", "name": "C",
             "entity_kind": "public_fund", "screen_status": "needs_valuation_evidence",
             "metrics": {}},
        ],
    })

    book = compile_opportunity_book(
        tmp_path, policy=policy, generated_at="2026-08-10T00:00:00Z",
    )

    assert [row["entity_id"] for row in book["candidates"]] == ["A", "B", "C"]
    assert book["candidates"][2]["learned_potential_rank"] is None


def test_eligible_law_outcome_reorders_only_paper_research(tmp_path: Path, monkeypatch) -> None:
    policy = _policy(tmp_path)
    _write_json(tmp_path / "discovery/latest.json", {
        "schema": "jaggedthoughts-discovery-run-v1", "run_id": "learned",
        "run_sha256": "d" * 64, "candidates": [
            {
                "candidate_id": "equity:A", "candidate_sha256": "a" * 64,
                "entity_id": "A", "entity_kind": "public_equity",
                "screen_status": "qualified", "research_rank": 1,
                "potential_rank": {"scope": "public_equity", "rank": 1},
                "rank_score": .5, "metrics": {},
            },
            {
                "candidate_id": "equity:B", "candidate_sha256": "b" * 64,
                "entity_id": "B", "entity_kind": "public_equity",
                "screen_status": "qualified", "research_rank": 2,
                "potential_rank": {"scope": "public_equity", "rank": 2},
                "rank_score": .5, "metrics": {},
            },
        ],
    })

    monkeypatch.setattr(
        "ztare.investment.capital_cycle.compile_law_policy_influence",
        lambda candidates, state, generated_at: {
            "learning_state_sha256": "l" * 64, "active_law_count": 1,
            "active_laws": [{"law_key": "settled-law"}], "suppressed_laws": [],
            "candidates": [
                {"candidate_identity": "equity:A", "adjustment": -.05,
                 "active_law_count": 1, "contributions": [{"law_key": "settled-law"}]},
                {"candidate_identity": "equity:B", "adjustment": .05,
                 "active_law_count": 1, "contributions": [{"law_key": "settled-law"}]},
            ],
            "influence_sha256": "i" * 64,
        },
    )

    book = compile_opportunity_book(
        tmp_path, policy=policy, generated_at="2026-08-10T00:00:00Z",
    )

    assert [row["entity_id"] for row in book["underwriting_ready"]] == ["B", "A"]
    assert [row["learned_research_rank"] for row in book["underwriting_ready"]] == [1, 2]
    assert all(row["screen_status"] == "qualified" for row in book["underwriting_ready"])
    assert book["capital_authority"] is False


def test_only_settleable_forecast_suppresses_nonoverlapping_cadence(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    _write_json(tmp_path / "decisions" / "acme.json", _decision("ACME", "draft", 0.05))
    _write_json(tmp_path / "discovery" / "latest.json", {
        "schema": "jaggedthoughts-discovery-run-v1",
        "candidates": [{
            "candidate_id": "equity:GAMMA", "entity_id": "GAMMA",
            "entity_kind": "public_equity", "screen_status": "qualified", "rank": 1,
        }],
    })
    _write_json(tmp_path / "discovery" / "latest_record.json", {
        "candidate_leaves": {"equity:GAMMA": "g" * 64},
    })
    _write_json(tmp_path / "closed_book" / "runs" / "prior.json", {
        "schema": "jaggedthoughts-closed-book-forecast-run-v1",
        "run_id": "prior-acme-21d",
        "opened_at": "2026-08-01T00:00:00Z",
        "horizon_days": 21,
        "evidence_packet": {
            "decision_id": "older-acme-decision",
            "entity": {"entity_id": "ACME"},
        },
    })

    due = due_forecast_windows(tmp_path, policy=policy, as_of="2026-08-10T00:00:00Z")

    assert [(row["entity_id"], row["horizon_days"]) for row in due] == [
        ("ACME", 21), ("ACME", 90), ("ACME", 365),
        ("GAMMA", 21), ("GAMMA", 90), ("GAMMA", 365),
    ]
    prior = json.loads((tmp_path / "closed_book" / "runs" / "prior.json").read_text())
    prior["end_at"] = "2026-08-22T00:00:00Z"
    prior["settlement_contract"] = {"prospective_return_window": {"return_window_sha256": "x"}}
    _write_json(tmp_path / "closed_book" / "runs" / "prior.json", prior)
    due = due_forecast_windows(tmp_path, policy=policy, as_of="2026-08-10T00:00:00Z")

    assert [(row["entity_id"], row["horizon_days"]) for row in due] == [
        ("ACME", 90), ("ACME", 365), ("GAMMA", 90), ("GAMMA", 365),
    ]
    due = due_forecast_windows(tmp_path, policy=policy, as_of="2026-08-23T00:00:00Z")
    assert len(due) == 6
    assert [row["subject_kind"] for row in due] == [
        "paper_decision", "paper_decision", "paper_decision",
        "discovery_candidate", "discovery_candidate", "discovery_candidate",
    ]


def test_researched_watch_replaces_raw_discovery_forecast_subject(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    candidate_leaf = "c" * 64
    candidate_sha = "a" * 64
    _write_json(tmp_path / "discovery/latest.json", {
        "candidates": [{
            "candidate_id": "equity:ACME", "entity_id": "ACME",
            "entity_kind": "public_equity", "screen_status": "qualified", "rank": 1,
            "candidate_sha256": candidate_sha,
        }],
    })
    _write_json(tmp_path / "discovery/latest_record.json", {
        "candidate_leaves": {"equity:ACME": candidate_leaf},
    })
    body = {
        "schema": "jaggedthoughts-public-equity-paper-decision-v1",
        "decision_id": "equity-paper-decision:ACME:1",
        "activated_at": "2026-08-09T00:00:00Z",
        "lifecycle": {"data_class": "operator", "stage": "active"},
        "entity": {"entity_id": "ACME", "entity_kind": "public_equity"},
        "candidate_identity": {"rank": 1},
        "evidence": {
            "candidate_leaf": candidate_leaf, "candidate_sha256": candidate_sha,
            "dossier_leaf": "e" * 64,
        },
        "paper_policy": {
            "target_weight": 0.0, "cash_default": True,
            "allocation_allowed": False, "order_routing_allowed": False,
        },
        "capital_authority": False, "brokerage_authority": False,
    }
    _write_json(tmp_path / "paper_decisions/equities/acme.json", {
        **body, "decision_sha256": stable_sha256(body),
    })

    due = due_forecast_windows(tmp_path, policy=policy, as_of="2026-08-10T00:00:00Z")

    assert len(due) == 3
    assert {row["subject_kind"] for row in due} == {"paper_watch_decision"}
    assert {row["candidate_leaf"] for row in due} == {candidate_leaf}

    _write_json(tmp_path / "closed_book/runs/prior-watch.json", {
        "run_id": "prior-watch", "opened_at": "2026-08-09T12:00:00Z",
        "horizon_days": 21, "end_at": "2026-08-30T12:00:00Z",
        "settlement_contract": {"prospective_return_window": {"return_window_sha256": "x"}},
        "subject": {
            "kind": "paper_watch_decision", "subject_sha256": "d" * 64,
            "candidate_leaf": candidate_leaf,
        },
        "evidence_packet": {
            "entity": {"entity_id": "ACME"},
            "research_snapshot": {"evidence": {"dossier_leaf": "e" * 64}},
        },
    })
    due = due_forecast_windows(tmp_path, policy=policy, as_of="2026-08-10T00:00:00Z")
    assert [(row["entity_id"], row["horizon_days"]) for row in due] == [
        ("ACME", 90), ("ACME", 365),
    ]


def test_market_state_maturity_activates_the_recurring_capital_cycle(tmp_path: Path) -> None:
    _policy(tmp_path)
    _write_json(tmp_path / "market_state" / "runs" / "state.json", {
        "schema": "jaggedthoughts-market-state-forecast-run-v1",
        "run_id": "state-90d", "opened_at": "2026-01-01T00:00:00Z",
        "end_at": "2026-04-01T00:00:00Z", "horizon_days": 90,
    })

    status = capital_cycle_status(tmp_path, as_of="2026-04-02T00:00:00Z")

    assert "market_state_settlement_due" in status["due_reasons"]
    assert status["market_state_due"]["source_refresh_required"] is True


def test_eligible_unenrolled_paper_watch_activates_the_capital_cycle(tmp_path: Path) -> None:
    policy = default_capital_cycle_policy()
    policy["paper_watch_auto_enrollment"]["enabled"] = True
    (tmp_path / "capital_cycle.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    proposal = {
        "proposal_sha256": "p" * 64,
        "entity": {"entity_kind": "public_equity", "entity_id": "ACME"},
        "evidence": {"candidate_leaf": "c" * 64, "dossier_leaf": "d" * 64},
        "paper_policy": {"target_weight": 0.0},
        "activation_eligible": True, "activation_blockers": [],
    }
    _write_json(tmp_path / "paper_proposals/equities/latest.json", {
        "rows": [{
            "entity_id": "ACME", "activation_eligible": True,
            "blockers": [], "proposal": proposal,
        }],
    })

    status = capital_cycle_status(tmp_path, as_of="2026-08-10T00:00:00Z")

    assert "paper_watch_enrollment_due" in status["due_reasons"]
    assert status["due_paper_watch_enrollments"] == [{
        "entity_kind": "public_equity", "entity_id": "ACME",
        "candidate_leaf": "c" * 64, "dossier_leaf": "d" * 64,
        "proposal_sha256": "p" * 64,
    }]
    watch = {
        "schema": "jaggedthoughts-public-equity-paper-decision-v1",
        "decision_id": "watch:ACME", "activated_at": "2026-08-10T00:00:01Z",
        "entity": proposal["entity"],
        "evidence": {**proposal["evidence"], "candidate_sha256": "s" * 64},
        "lifecycle": {"data_class": "operator", "stage": "active"},
        "paper_policy": {
            "target_weight": 0.0, "cash_default": True,
            "allocation_allowed": False, "order_routing_allowed": False,
        },
        "capital_authority": False, "brokerage_authority": False,
    }
    _write_json(tmp_path / "paper_decisions/equities/acme.json", {
        **watch, "decision_sha256": stable_sha256(watch),
    })

    enrolled = capital_cycle_status(tmp_path, as_of="2026-08-10T00:00:02Z")
    assert "paper_watch_enrollment_due" not in enrolled["due_reasons"]
    assert enrolled["due_paper_watch_enrollments"] == []


def test_market_state_cadence_waits_for_the_active_horizon(tmp_path: Path) -> None:
    _write_json(tmp_path / "market_state" / "runs" / "state.json", {
        "schema": "jaggedthoughts-market-state-forecast-run-v1",
        "run_id": "state-90d", "opened_at": "2026-08-01T00:00:00Z",
        "end_at": "2026-10-30T00:00:00Z", "horizon_days": 90,
    })
    windows = [{"horizon_days": 90, "cadence_days": 7}]

    assert due_market_state_horizons(
        tmp_path, windows=windows, as_of="2026-08-10T00:00:00Z",
    ) == ()
    assert due_market_state_horizons(
        tmp_path, windows=windows, as_of="2026-10-31T00:00:00Z",
    ) == (90,)


def test_market_state_implied_return_reuses_the_erp_valuation_treasury(tmp_path: Path) -> None:
    (tmp_path / "evidence_state.txt").write_text("next_total_return\n0.08\n", encoding="utf-8")
    forecasts, _ = _challengers(tmp_path, {
        "state": {"implied_equity_risk_premium": 0.05, "implied_nominal_equity_return": 0.09},
        "valuation_context": {"displayed_nominal_treasury_rate": 0.04},
        "cash_yields": {"90": 0.03}, "snapshot_artifact_sha256": "s" * 64,
    }, horizon_days=90, project_path=tmp_path)
    implied = next(row for row in forecasts if row["model_id"] == "implied_required_return")
    assert implied["predicted_values"]["spy_total_return"] == (1.09 ** (90 / 365.25)) - 1
    assert implied["explanation"]["matched_valuation_treasury_rate"] == 0.04


def test_new_institutional_learning_epoch_activates_the_capital_cycle(tmp_path: Path) -> None:
    _policy(tmp_path)
    _write_json(tmp_path / "capital_cycles" / "latest.json", {
        "institutional_learning": {"state": {"state_sha256": "a" * 64}},
    })
    _write_json(tmp_path / "institutional_learning" / "latest.json", {
        "state_sha256": "b" * 64,
    })

    status = capital_cycle_status(tmp_path, as_of="2026-08-13T00:00:00Z")

    assert "new_institutional_learning_epoch" in status["due_reasons"]
    assert status["capital_authority"] is False


def test_settlement_readiness_distinguishes_future_horizons_from_missing_dual_contracts(
    tmp_path: Path,
) -> None:
    _write_json(tmp_path / "closed_book/runs/forecast.json", {
        "schema": "jaggedthoughts-closed-book-forecast-run-v1", "run_id": "forecast",
        "end_at": "2026-09-01T00:00:00Z",
    })
    _write_json(tmp_path / "portfolio_policy/runs/policy.json", {
        "schema": "jaggedthoughts-portfolio-policy-run-v1", "run_id": "policy",
        "end_at": "2026-11-01T00:00:00Z",
    })
    _write_json(tmp_path / "institutional_learning/strategy_moves/latest.json", {
        "moves": [{
            "implementation_event": {
                "treatment_timing_status": "exact_adoption_event",
                "available_at": "2026-08-01T00:00:00Z",
            },
            "outcome_contracts": [],
        }],
    })

    readiness = settlement_readiness(tmp_path, as_of="2026-08-13T00:00:00Z")

    assert readiness["closed_book"]["next_due_at"] is None
    assert readiness["closed_book"]["quarantined_count"] == 1
    assert readiness["portfolio_policy"]["quarantined_count"] == 1
    assert readiness["portfolio_policy"]["due_count"] == 0
    assert readiness["strategy_dual"]["issuance_status"] == "blocked_missing_operating_outcome_contract"
    assert readiness["capital_authority"] is False
