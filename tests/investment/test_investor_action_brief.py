from copy import deepcopy

from ztare.investment.investor_action_brief import compile_investor_action_brief


def test_high_score_without_evidence_cannot_enter_investable_now():
    candidate = {
        "candidate_id": "equity:A", "candidate_sha256": "a" * 64,
        "entity_id": "A", "entity_kind": "public_equity",
        "rank": 1, "research_priority_score": 0.7,
        "research_priority_is_expected_return": False,
    }
    discovery = {"candidates": [candidate]}
    book = {
        "generated_at": "2026-01-01T00:00:00Z", "candidates": [candidate],
        "research_queue": [candidate], "paper_posture": {"state": "cash", "cash_weight": 1.0},
    }
    underwriting = {"candidates": [{**candidate, "ranking": {}, "valuation": {}, "factor": {}}]}
    readiness = {"capital_authority": False, "candidates": [{
        **candidate, "allocation_ready": True, "activation_gaps": [],
        "paper": {"state": "portfolio_candidate"}, "capital_authority": False,
    }]}
    proposal_audit = {"rows": [{
        **candidate, "activation_eligible": True, "blockers": [],
        "proposal": {"proposal_id": "paper:A", "activation_eligible": True,
                     "capital_authority": False, "brokerage_authority": False},
    }]}
    inputs = dict(
        breadth_audit={
            "source_universe": {"eligible_count": 100},
            "active_scout_scope": [
                {"intent_id": "broad", "mode": "broad_equity", "entity_kinds": ["public_equity"], "eligible_count": 100, "returned_count": 10},
                {"intent_id": "value", "mode": "language", "entity_kinds": ["public_fund"], "eligible_count": 8, "returned_count": 8, "styles": ["value"]},
            ],
            "funnel": {"branches": {"public_equity": {"discovery_candidates": 1}, "public_fund": {"discovery_candidates": 0}}},
        }, discovery_run=discovery, opportunity_book=book,
        underwriting_index=underwriting, allocation_readiness=readiness,
        equity_proposal_audit=proposal_audit,
        sleeve_implementation_frontier={"sleeves": [{
            "sleeve_id": "us_equity", "eligible_instruments": [{
                "basis_proxy": True, "identity": {"subject_id": "SPY"},
            }],
        }]},
        fund_sleeve_comparison={
            "implementation_review_admitted_count": 0,
            "sleeves": [{"sleeve_id": "us_equity", "programs": [{
                "program_id": "fund-sleeve:us_equity:FNK:test",
                "identity": {"subject_id": "FNK"}, "comparison_eligible": True,
                "comparison_metrics": {
                    "expense_ratio": 0.003, "annualized_volatility": 0.18,
                },
                "blockers": ["portfolio_turnover_absent"],
                "portfolio_evidence": {"portfolio_policy_evidence_complete": False},
            }]}],
            "invest_vs_cash_activation": {
                "required_next_transition": "research_candidate_and_compile_inactive_fund_proposal",
                "ranked_research_candidates": [{
                    "entity_id": "FNK", "sleeve_id": "us_equity",
                    "program_id": "fund-sleeve:us_equity:FNK:test",
                    "research_priority_rank_within_sleeve": 1,
                    "required_excess_return_vs_cash": 0.03,
                    "ranking_semantics": "factor_assumption_spread_research_priority",
                }],
            },
        },
        research_service={
            "enabled": True,
            "next_due_at": "2026-01-02T00:00:00Z",
            "next_transition": "subscription_research",
            "work_id": "research:A",
            "job_kind": "jaggedthoughts_autoresearch_project",
            "dispatch_selection_basis": "frozen_chain_successor",
            "status": "blocked",
            "blocked_reasons": ["daily_subscription_dispatch_budget_exhausted"],
        },
        portfolio_policy={
            "pending_count": 1, "settled_count": 0,
            "scoreboard": {"minimum_inference_blocks": 8,
                           "next_activation": "settle_the_first_complete_policy_block"},
            "latest_run": {
                "schema": "jaggedthoughts-portfolio-policy-run-v1",
                "run_id": "policy:test", "run_sha256": "p" * 64,
                "opened_at": "2026-01-01T00:00:00Z",
                "end_at": "2027-01-01T00:00:00Z", "horizon_days": 365,
                "status": "pending_outcome", "policies": [{
                    "policy_id": "ranked", "policy_sha256": "q" * 64,
                    "method": "discovery_priority", "gross_weight": 0.5,
                    "cash_weight": 0.5, "weights": {"A": 0.3, "B": 0.2},
                    "capital_authority": False,
                }],
            },
        },
        planning_scenario={
            "schema": "jaggedthoughts-household-allocation-scenario-v1",
            "scenario_sha256": "s" * 64,
            "selected_policy": {
                "program_id": "household:test", "weights": {"us_equity": 0.7},
            },
            "operator_policy_blockers": ["tax_residence"],
        },
        household_policy_tournament={
            "pending_count": 1, "settled_count": 0, "minimum_inference_blocks": 8,
            "next_activation": "settle_the_first_household_policy_block",
            "latest_run": {
                "schema": "jaggedthoughts-household-policy-tournament-run-v1",
                "run_id": "household:test", "run_sha256": "h" * 64,
                "opened_at": "2026-01-01T00:00:00Z", "end_at": "2026-01-22T00:00:00Z",
                "horizon_days": 21, "status": "pending_outcome",
                "control_policy_id": "broad_sleeve_control", "policies": [{
                    "policy_id": "broad_sleeve_control", "method": "broad_proxy",
                    "policy_sha256": "c" * 64, "decision_equivalence_id": "d" * 64,
                    "weights": {"SPY": 0.7, "TIP": 0.2, "VXUS": 0.1},
                }],
            },
        },
    )
    baseline = compile_investor_action_brief(**inputs)

    unsupported = {
        "candidate_id": "equity:X", "candidate_sha256": "x" * 64,
        "entity_id": "X", "entity_kind": "public_equity", "rank": 0,
        "research_priority_score": 999.0, "research_priority_is_expected_return": False,
    }
    changed = deepcopy(inputs)
    changed["discovery_run"]["candidates"].append(unsupported)
    changed["opportunity_book"]["candidates"].append(unsupported)
    changed["opportunity_book"]["research_queue"].append(unsupported)
    changed["underwriting_index"]["candidates"].append({
        **unsupported, "ranking": {}, "valuation": {}, "factor": {},
    })
    stale = deepcopy(proposal_audit["rows"][0])
    stale["candidate_sha256"] = "b" * 64
    stale["proposal"].update(proposal_id="paper:A-old", proposal_sha256="history:A-old")
    changed["equity_proposal_audit"]["rows"].append(stale)
    changed["fund_proposal_audit"] = {"rows": [{
        **stale, "candidate_sha256": "f" * 64, "entity_id": "F",
    }]}
    changed["paper_watch_decisions"] = [{
        "decision_id": "history:A-old", "proposal_sha256": "history:A-old",
        "paper_policy": {"target_weight": 0.0},
    }]
    result = compile_investor_action_brief(**changed)

    assert [row["entity_id"] for row in baseline["investable_now"]["paper"]] == ["A"]
    assert result["investable_now"] == baseline["investable_now"]
    assert [row["entity_id"] for row in result["review_now"]] == ["A"]
    assert result["active_paper_watches"][0]["target_weight"] == 0.0
    assert result["active_paper_watches"][0]["capital_authority"] is False
    summary = baseline["decision_summary"]
    assert [row["scope_class"] for row in summary["scan"]["scopes"]] == [
        "broad_periodic_scout", "explicit_challenger_cohort",
    ]
    assert summary["fund_identity_boundary"] == {
        "text": "Broad asset-class sleeves are portfolio basis objects; the value-fund challenger cohort is a separate within-sleeve research tournament.",
        "broad_sleeves": [{"sleeve_id": "us_equity", "entity_id": "SPY"}],
        "challenger_program_count": 1,
        "comparison_eligible_count": 1,
    }
    assert summary["attention"]["fund_sleeve_candidate_count"] == 1
    assert summary["attention"]["fund_sleeve_candidates"][0] == {
        "entity_id": "FNK", "sleeve_id": "us_equity", "rank_within_sleeve": 1,
        "factor_assumption_spread_vs_cash": 0.03,
        "ranking_semantics": "factor_assumption_spread_research_priority",
        "comparison_metrics": {"expense_ratio": 0.003, "annualized_volatility": 0.18},
        "evidence_gaps": ["portfolio_turnover_absent"],
        "portfolio_policy_evidence_complete": False,
        "next_transition": "research_candidate_and_compile_inactive_fund_proposal",
        "capital_authority": False,
    }
    assert summary["next"] == {
        "text": "At 2026-01-02T00:00:00Z, the owning subscription worker subscription research (research:A). It goes first because it closes an already-open evidence chain.",
        "due_epoch": "2026-01-02T00:00:00Z",
    }
    assert baseline["next_automatic_transition"]["job_kind"] == "jaggedthoughts_autoresearch_project"
    assert baseline["next_automatic_transition"]["dispatch_selection_basis"] == "frozen_chain_successor"
    assert baseline["automated_shadow_book"]["policies"][0]["positions"] == [
        {"entity_id": "A", "weight": 0.3}, {"entity_id": "B", "weight": 0.2},
    ]
    assert "1 sealed shadow portfolio policies" in summary["decision"]["text"]
    assert baseline["automated_shadow_book"]["capital_authority"] is False
    assert baseline["planning_book"]["positions"] == [{
        "sleeve_id": "us_equity", "entity_id": "SPY", "weight": 0.7,
        "implementation_role": "broad_sleeve_proxy",
    }]
    assert baseline["planning_book"]["paper_policy_authority"] is False
    assert baseline["household_shadow_book"]["policy_count"] == 1
    assert baseline["household_shadow_book"]["policies"][0]["positions"][0] == {
        "entity_id": "SPY", "weight": 0.7,
    }

    candidate_bound = deepcopy(inputs)
    candidate_bound["equity_proposal_audit"]["rows"][0]["proposal"]["proposal_sha256"] = "new-proposal"
    candidate_bound["paper_watch_decisions"] = [{
        "decision_id": "watch:A", "proposal_sha256": "old-proposal",
        "entity": {"entity_id": "A", "entity_kind": "public_equity"},
        "evidence": {"candidate_sha256": "a" * 64},
        "paper_policy": {"target_weight": 0.0},
    }]
    current = compile_investor_action_brief(**candidate_bound)
    assert current["review_now"][0]["review_state"] == "active_paper_watch"
    assert current["review_now"][0]["activation_eligible"] is False
