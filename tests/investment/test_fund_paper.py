import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment import workspace as investment_workspace
from ztare.investment.fund_paper import (
    activate_fund_proposal,
    activate_workspace_fund_paper_watch,
    compile_inactive_fund_proposal,
)
from ztare.investment.workspace import _auto_enroll_eligible_paper_watches


def _hashed(body, field):
    return {**body, field: stable_sha256(body)}


def _inputs():
    watch_leaf, candidate_leaf, dossier_leaf = "a" * 64, "b" * 64, "c" * 64
    as_of = "2026-01-02T00:00:00Z"
    analysis = _hashed({
        "schema": "jaggedthoughts-factor-analysis-v1", "as_of": as_of,
        "fit": {"r2": 0.8}, "historical": {"residual_alpha_annualized": 0.01},
        "assumption_implied": {"return_without_residual_alpha": 0.09},
        "source_refs": ["prices"],
    }, "analysis_sha256")
    valuation = {"valuation_kind": "aggregate_expectations_proxy", "required_return": 0.09,
                 "source_refs": ["issuer"]}
    fund_evidence = {"metrics": {"expense_ratio": 0.002}, "source_refs": ["issuer"]}
    fund = {
        "candidate_id": "catalog-fund", "entity_id": "FUND", "screen_status": "qualified",
        "analysis": analysis, "valuation": valuation, "fund_evidence": fund_evidence,
    }
    graph = _hashed({
        "schema": "jaggedthoughts-fund-holdings-graph-v1", "as_of": as_of,
        "target_entity_id": "FUND", "scope_closed": False,
        "target_coverage": {"uncovered_weight": 0.75},
        "missing_fund_entity_ids": ["PEER"], "acquisition_frontier_entity_ids": ["ACME"],
    }, "fund_holdings_graph_sha256")
    watchlist = _hashed({
        "schema": "jaggedthoughts-opportunity-watchlist-result-v1",
        "watchlist_id": "funds", "as_of": as_of, "candidates": [fund],
        "fund_holdings_graph": graph,
    }, "watchlist_sha256")
    candidate = _hashed({
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "fund:funds:FUND", "entity_id": "FUND", "entity_kind": "public_fund",
        "name": "Fund", "as_of": as_of, "screen_status": "qualified", "rank": 1,
        "watchlist_id": "funds", "watchlist_candidate_id": "catalog-fund",
        "input_golden_leaves": [watch_leaf], "factor_analysis_sha256": analysis["analysis_sha256"],
        "valuation": valuation, "fund_evidence": fund_evidence,
    }, "candidate_sha256")
    sources = [
        {"id": key, "title": key, "url": f"https://example.com/{key}", "publisher": key,
         "published_at": "2025-01-01", "accessed_at": "2026-01-03T00:00:00Z",
         "source_kind": kind, "supports": ["thesis"]}
        for key, kind in (("issuer", "issuer"), ("study", "research"))
    ]
    dossier = _hashed({
        "schema": "jaggedthoughts-candidate-research-dossier-v1",
        "candidate_leaf": candidate_leaf, "candidate_sha256": candidate["candidate_sha256"],
        "entity_id": "FUND", "as_of": as_of, "generated_at": "2026-01-03T00:00:00Z",
        "thesis": {"claim": "candidate", "mechanism": "mechanism", "confidence": 0.6},
        "rival_view": {"claim": "rival"}, "decisive_observation": {"observation": "outcome"},
        "falsifiers": ["fails"], "catalysts": [], "industry": {"structure": "fund"},
        "durable_earnings_bridge": {"quality": "open"},
        "valuation_assumptions": {"kind": "aggregate"},
        "strategy": {"choices": [{"id": "screen", "description": "screen", "evidence_refs": ["issuer"]}],
                     "reinforcing_edges": []},
        "sources": sources,
    }, "dossier_sha256")
    return (
        {"object_kind": "discovery_candidate", "leaf_sha256": candidate_leaf, "payload": candidate},
        {"object_kind": "opportunity_watchlist", "leaf_sha256": watch_leaf, "payload": watchlist},
        {"object_kind": "candidate_research_dossier", "leaf_sha256": dossier_leaf,
         "epoch": dossier["dossier_sha256"], "payload": dossier},
        watchlist,
    )


def test_fund_proposal_preserves_cash_evidence_gaps_and_operator_boundary():
    candidate, watchlist, dossier, latest = _inputs()
    proposal = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist, dossier_record=dossier,
        compiled_at="2026-01-04T00:00:00Z",
    )
    assert proposal["paper_policy"]["target_weight"] == 0
    assert proposal["paper_policy"]["book"]["positions"] == []
    assert "underlying_company_quality_lookthrough_incomplete" in proposal["review_gaps"]
    decision = activate_fund_proposal(
        proposal, confirmation=proposal["required_operator_confirmation"],
        operator_id="operator", activated_at="2026-01-04T01:00:00Z",
    )
    assert decision["lifecycle"]["stage"] == "active"
    assert decision["transition"]["to_state"] == "active_paper"
    assert decision["portfolio_eligibility"] == {
        "eligible": False, "implementation_review_allowed": True,
        "data_class": "operator", "reference_fixture": False,
        "current_target_weight": 0.0, "allocation_allowed": False,
        "required_next_transition": "fund_specific_portfolio_admission_review",
    }
    assert decision["paper_policy"]["implementation_review_allowed"] is True
    assert decision["paper_policy"]["portfolio_admission_allowed"] is False
    assert decision["paper_policy"]["allocation_allowed"] is False
    assert decision["capital_authority"] is decision["brokerage_authority"] is False

    changed_graph = _hashed({
        **{k: v for k, v in latest["fund_holdings_graph"].items()
           if k != "fund_holdings_graph_sha256"},
        "acquisition_frontier_entity_ids": ["OTHER"],
    }, "fund_holdings_graph_sha256")
    same_candidate = _hashed({
        **{k: v for k, v in latest.items() if k != "watchlist_sha256"},
        "fund_holdings_graph": changed_graph,
    }, "watchlist_sha256")
    current = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist, dossier_record=dossier,
        compiled_at="2026-01-04T02:00:00Z", latest_watchlist=same_candidate,
    )
    assert current["activation_eligible"] is True

    newer = _hashed({**{k: v for k, v in latest.items() if k != "watchlist_sha256"},
                     "as_of": "2026-01-05T00:00:00Z"}, "watchlist_sha256")
    stale = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist, dossier_record=dossier,
        compiled_at="2026-01-05T01:00:00Z", latest_watchlist=newer,
    )
    with pytest.raises(ValueError, match="activation blockers"):
        activate_fund_proposal(
            stale, confirmation=stale["required_operator_confirmation"],
            operator_id="operator", activated_at="2026-01-05T02:00:00Z",
        )


def test_fund_proposal_accepts_candidate_bound_coverage_of_prior_review():
    candidate, watchlist, dossier, latest = _inputs()
    candidate_body = {
        **{key: value for key, value in candidate["payload"].items()
           if key != "candidate_sha256"},
        "input_golden_leaves": [],
    }
    candidate["payload"] = _hashed(candidate_body, "candidate_sha256")
    old_leaf = "d" * 64
    old_candidate_sha = "e" * 64
    dossier_body = {
        **{key: value for key, value in dossier["payload"].items()
           if key != "dossier_sha256"},
        "candidate_leaf": old_leaf, "candidate_sha256": old_candidate_sha,
    }
    dossier["payload"] = _hashed(dossier_body, "dossier_sha256")
    dossier["epoch"] = dossier["payload"]["dossier_sha256"]
    coverage_leaf = "f" * 64
    coverage = _hashed({
        "schema": "jaggedthoughts-research-evidence-coverage-v1",
        "status": "covered_by_monitored_dossier", "covered": True,
        "entity_id": "FUND", "candidate_leaf": candidate["leaf_sha256"],
        "candidate_sha256": candidate["payload"]["candidate_sha256"],
        "prior_dossier_leaf": dossier["leaf_sha256"],
    }, "coverage_sha256")
    proposal = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist,
        dossier_record=dossier, research_coverage_record={
            "object_kind": "research_evidence_coverage",
            "leaf_sha256": coverage_leaf, "payload": coverage,
        },
        compiled_at="2026-01-04T00:00:00Z", latest_watchlist=latest,
    )
    assert proposal["evidence_binding"] == {
        "watchlist": "verified_candidate_projection",
        "research": "candidate_coverage_to_prior_dossier",
    }
    assert proposal["evidence"]["research_coverage_leaf"] == coverage_leaf
    assert proposal["activation_eligible"] is True


def test_auto_enrollment_spends_budget_in_current_learned_order(tmp_path, monkeypatch):
    def audit(entity, candidate_sha, proposal_sha):
        proposal = {
            "proposal_sha256": proposal_sha, "activation_eligible": True,
            "activation_blockers": [], "paper_policy": {"target_weight": 0},
            "required_operator_confirmation": "confirm",
        }
        return {"rows": [{
            "entity_id": entity, "candidate_sha256": candidate_sha,
            "activation_eligible": True, "blockers": [], "proposal": proposal,
        }]}

    monkeypatch.setattr(
        investment_workspace, "activate_workspace_fund_paper_watch",
        lambda *_args, **_kwargs: {"status": "activated_paper_watch"},
    )
    enrollment = _auto_enroll_eligible_paper_watches(
        tmp_path,
        policy={"paper_watch_auto_enrollment": {
            "enabled": True, "max_new_per_cycle": 1, "actor_id": "operator",
        }},
        equity_audit=audit("EQUITY", "e" * 64, "1" * 64),
        fund_audit=audit("FUND", "f" * 64, "2" * 64),
        opportunity_book={"book_sha256": "b" * 64, "candidates": [
            {"entity_kind": "public_fund", "entity_id": "FUND",
             "candidate_sha256": "f" * 64, "learned_research_rank": 1},
            {"entity_kind": "public_equity", "entity_id": "EQUITY",
             "candidate_sha256": "e" * 64, "learned_research_rank": 2},
        ]},
        activated_at="2026-01-04T00:00:00Z",
    )

    assert [(row["entity_id"], row["learned_research_rank"]) for row in enrollment["actions"]] == [
        ("FUND", 1), ("EQUITY", 2),
    ]
    assert [row["status"] for row in enrollment["actions"]] == [
        "activated_paper_watch", "budget_deferred",
    ]
    assert enrollment["capital_authority"] is False


def test_workspace_fund_activation_requires_current_hash_and_stays_zero_weight(tmp_path):
    candidate, watchlist, dossier, _latest = _inputs()
    proposal = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist, dossier_record=dossier,
        compiled_at="2026-01-04T00:00:00Z",
    )
    run_sha = "d" * 64
    audit_body = {
        "schema": "jaggedthoughts-public-fund-paper-proposal-audit-v1",
        "compiled_at": "2026-01-04T00:00:00Z", "discovery_run_sha256": run_sha,
        "qualified_candidate_count": 1, "proposal_count": 1, "eligible_count": 1,
        "blocked_count": 0,
        "rows": [{
            "entity_id": "FUND", "candidate_leaf": "b" * 64,
            "candidate_sha256": candidate["payload"]["candidate_sha256"],
            "status": "eligible_proposal", "activation_eligible": True,
            "blockers": [], "proposal": proposal,
        }],
        "authority": "paper_research_proposal_audit_only", "capital_authority": False,
        "portfolio_authority": False, "brokerage_authority": False,
    }
    audit = {**audit_body, "audit_sha256": stable_sha256(audit_body)}
    (tmp_path / "paper_proposals" / "funds").mkdir(parents=True)
    (tmp_path / "discovery").mkdir()
    (tmp_path / "workspace.yaml").write_text(
        "owner: operator-paper-book\ngolden_store: state/golden_store.sqlite3\n",
        encoding="utf-8",
    )
    (tmp_path / "paper_proposals" / "funds" / "latest.json").write_text(
        json.dumps(audit), encoding="utf-8",
    )
    (tmp_path / "discovery" / "latest.json").write_text(
        json.dumps({"run_sha256": run_sha}), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not current"):
        activate_workspace_fund_paper_watch(
            tmp_path, "FUND", proposal_sha256="e" * 64,
            confirmation=proposal["required_operator_confirmation"], operator_id="operator",
        )
    refreshed = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist, dossier_record=dossier,
        compiled_at="2026-01-04T00:30:00Z",
    )
    refreshed_body = {**audit_body, "compiled_at": "2026-01-04T00:30:00Z", "rows": [
        {**audit_body["rows"][0], "proposal": refreshed},
    ]}
    refreshed_audit = {**refreshed_body, "audit_sha256": stable_sha256(refreshed_body)}
    (tmp_path / "paper_proposals" / "funds" / "latest.json").write_text(
        json.dumps(refreshed_audit), encoding="utf-8",
    )
    enrollment = _auto_enroll_eligible_paper_watches(
        tmp_path,
        policy={"paper_watch_auto_enrollment": {
            "enabled": True,
            "actor_id": "operator-paper-book:auto-paper-watch-policy-v1",
            "max_new_per_cycle": 1,
            "scope": "current_eligible_zero_weight_only",
        }},
        equity_audit={"rows": []}, fund_audit=audit,
        opportunity_book={"book_sha256": "f" * 64, "candidates": []},
        activated_at="2026-01-04T01:00:00Z",
    )
    assert enrollment["new_activation_count"] == 1
    assert enrollment["actions"][0]["status"] == "activated_paper_watch"
    assert enrollment["actions"][0]["proposal_sha256"] == refreshed["proposal_sha256"]
    decision_path = tmp_path / enrollment["actions"][0]["artifact_path"]
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["portfolio_eligibility"]["eligible"] is False
    assert decision["portfolio_eligibility"]["implementation_review_allowed"] is True
    assert decision["paper_policy"]["target_weight"] == 0
    assert decision["paper_policy"]["book"]["positions"] == []

    # A later compiler pass over the same candidate and dossier is the same
    # watch even though compiled_at changes the proposal digest.
    recompiled = compile_inactive_fund_proposal(
        candidate_record=candidate, watchlist_record=watchlist, dossier_record=dossier,
        compiled_at="2026-01-04T01:30:00Z",
    )
    replay_audit = {**audit, "rows": [{**audit["rows"][0], "proposal": recompiled}]}
    replay = _auto_enroll_eligible_paper_watches(
        tmp_path,
        policy={"paper_watch_auto_enrollment": {
            "enabled": True,
            "actor_id": "operator-paper-book:auto-paper-watch-policy-v1",
            "max_new_per_cycle": 1,
            "scope": "current_eligible_zero_weight_only",
        }},
        equity_audit={"rows": []}, fund_audit=replay_audit,
        opportunity_book={"book_sha256": "f" * 64, "candidates": []},
        activated_at="2026-01-04T02:00:00Z",
    )
    assert replay["new_activation_count"] == 0
    assert replay["already_enrolled_count"] == 1
