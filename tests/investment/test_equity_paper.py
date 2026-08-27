from copy import deepcopy

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.equity_paper import (
    activate_equity_proposal,
    compile_inactive_equity_proposal,
)


def _sealed(body, field):
    return {**body, field: stable_sha256(body)}


def test_equity_proposal_separates_watch_activation_from_position_admission() -> None:
    candidate = _sealed({
        "schema": "jaggedthoughts-discovery-candidate-v1", "candidate_id": "equity:ACME",
        "entity_id": "ACME", "entity_kind": "public_equity", "name": "Acme",
        "as_of": "2026-01-01T00:00:00Z", "screen_status": "qualified", "rank": 1,
        "valuation": {"envelope_sha256": "a" * 64},
    }, "candidate_sha256")
    discovery = _sealed({
        "schema": "jaggedthoughts-discovery-run-v1", "run_id": "run", "as_of": candidate["as_of"],
        "completed_at": candidate["as_of"], "candidates": [candidate],
    }, "run_sha256")
    leaf = "b" * 64
    dossier_body = {
        "schema": "jaggedthoughts-candidate-research-dossier-v1",
        "request_id": "request", "request_sha256": "c" * 64,
        "candidate_leaf": leaf, "candidate_sha256": candidate["candidate_sha256"],
        "entity_id": "ACME", "as_of": candidate["as_of"],
        "generated_at": "2026-01-02T00:00:00Z",
        "thesis": {"claim": "Claim", "mechanism": "Mechanism", "confidence": 0.5},
        "rival_view": {"claim": "Rival"}, "decisive_observation": {"claim": "Observe"},
        "strategy": {"choices": [], "reinforcing_edges": [], "representation_residuals": []},
        "industry": {"boundary": "Industry"},
        "durable_earnings_bridge": {"revenue_durability": "Source bound"},
        "valuation_assumptions": {"base_growth": 0.0}, "falsifiers": ["Falsifier"],
        "catalysts": [],
        "sources": [
            {"id": "s1", "title": "Filing", "url": "https://example.com/1",
             "publisher": "SEC", "published_at": "2025-12-31", "accessed_at": "2026-01-02T00:00:00Z",
             "source_kind": "filing", "supports": ["claim"]},
            {"id": "s2", "title": "Research", "url": "https://example.com/2",
             "publisher": "Publisher", "published_at": "2025-12-31", "accessed_at": "2026-01-02T00:00:00Z",
             "source_kind": "research", "supports": ["rival"]},
        ],
    }
    dossier = _sealed(dossier_body, "dossier_sha256")
    underwriting_row = _sealed({
        "candidate_id": "equity:ACME", "candidate_sha256": candidate["candidate_sha256"],
        "entity_id": "ACME", "entity_kind": "public_equity", "as_of": candidate["as_of"],
        "valuation": {}, "factor": {}, "market_context_sha256": "d" * 64,
        "ranking": {"eligible": True, "research_priority_is_expected_return": False},
        "state_price_aware": True, "gaps": [], "source_refs": [], "capital_authority": False,
    }, "underwriting_row_sha256")
    underwriting = _sealed({
        "schema": "jaggedthoughts-underwriting-opportunity-index-v1",
        "generated_at": candidate["as_of"], "discovery_run_sha256": discovery["run_sha256"],
        "market_context": {}, "candidate_count": 1, "ranking_eligible_count": 1,
        "state_price_aware_count": 1, "candidates": [underwriting_row],
        "authority": "research", "capital_authority": False,
    }, "underwriting_index_sha256")
    valuation = _sealed({
        "schema": "jaggedthoughts-valuation-envelope-v1", "entity_id": "ACME",
        "evidence_epoch": candidate["as_of"], "summary": {},
        "enumeration": {"grammar_id": "grammar", "grammar_version": "1",
                        "grammar_digest": "e" * 64, "enumeration_digest": "f" * 64,
                        "exhausted_within_scope": True, "residuals": []},
    }, "envelope_sha256")
    candidate["valuation"]["envelope_sha256"] = valuation["envelope_sha256"]
    candidate_body = dict(candidate); candidate_body.pop("candidate_sha256")
    candidate["candidate_sha256"] = stable_sha256(candidate_body)
    discovery_body = dict(discovery); discovery_body.pop("run_sha256"); discovery_body["candidates"] = [candidate]
    discovery = _sealed(discovery_body, "run_sha256")
    dossier["candidate_sha256"] = candidate["candidate_sha256"]
    dossier_body = dict(dossier); dossier_body.pop("dossier_sha256"); dossier = _sealed(dossier_body, "dossier_sha256")
    underwriting_row["candidate_sha256"] = candidate["candidate_sha256"]
    row_body = dict(underwriting_row); row_body.pop("underwriting_row_sha256"); underwriting_row = _sealed(row_body, "underwriting_row_sha256")
    underwriting_body = dict(underwriting); underwriting_body.pop("underwriting_index_sha256")
    underwriting_body.update(discovery_run_sha256=discovery["run_sha256"], candidates=[underwriting_row])
    underwriting = _sealed(underwriting_body, "underwriting_index_sha256")
    fingerprint = _sealed({
        "schema": "jaggedthoughts-business-fingerprint-v1", "entity_id": "ACME",
        "component_identity": {"research_dossier": {"candidate_leaf": leaf, "sha256": dossier["dossier_sha256"]}},
        "axis_coverage": {}, "unknowns": [], "cross_industry_comparability": {},
    }, "business_fingerprint_sha256")
    grid_row = {"entity_id": "ACME", "candidate_sha256": candidate["candidate_sha256"],
                "modeled_grid_sha256": "1" * 64, "result_sha256": "2" * 64,
                "no_arbitrage_certificate": True, "market_complete": True}
    grid = _sealed({
        "schema": "jaggedthoughts-modeled-payoff-grid-audit-v1", "as_of": candidate["as_of"],
        "discovery_run_sha256": discovery["run_sha256"], "rows": [grid_row],
        "scope_boundary": "conditional", "physical_probability_claim": False,
        "expected_return_claim": False, "capital_authority": False,
    }, "audit_sha256")
    inputs = dict(
        discovery_run=discovery, candidate_leaf=leaf, dossier=dossier, dossier_leaf="3" * 64,
        underwriting_index=underwriting, valuation_artifact=valuation,
        business_fingerprint=fingerprint, modeled_grid_audit=grid,
        compiled_at="2026-01-03T00:00:00Z",
    )

    eligible = compile_inactive_equity_proposal(**inputs)
    blocked_underwriting = deepcopy(underwriting)
    blocked_underwriting["candidates"][0]["gaps"] = ["missing_coordinate"]
    row = blocked_underwriting["candidates"][0]; row_body = dict(row); row_body.pop("underwriting_row_sha256")
    blocked_underwriting["candidates"][0] = _sealed(row_body, "underwriting_row_sha256")
    body = dict(blocked_underwriting); body.pop("underwriting_index_sha256")
    blocked = compile_inactive_equity_proposal(**{**inputs, "underwriting_index": _sealed(body, "underwriting_index_sha256")})

    assert eligible["activation_eligible"] is True
    assert blocked["activation_eligible"] is True
    assert blocked["watch_activation"]["eligible"] is True
    assert blocked["position_admission"]["eligible"] is False
    assert "underwriting:missing_coordinate" in blocked["position_admission"]["blockers"]
    assert blocked["paper_policy"]["target_weight"] == 0.0
    assert blocked["paper_policy"]["cash_default"] is True
    assert blocked["paper_policy"]["book"]["positions"] == []
    assert blocked["capital_authority"] is blocked["portfolio_authority"] is blocked["brokerage_authority"] is False

    prior = deepcopy(dossier)
    prior.update(candidate_leaf="4" * 64, candidate_sha256="5" * 64)
    prior_body = dict(prior); prior_body.pop("dossier_sha256")
    prior = _sealed(prior_body, "dossier_sha256")
    prior_fingerprint = deepcopy(fingerprint)
    prior_fingerprint["component_identity"]["research_dossier"] = {
        "candidate_leaf": prior["candidate_leaf"], "sha256": prior["dossier_sha256"],
    }
    fingerprint_body = dict(prior_fingerprint); fingerprint_body.pop("business_fingerprint_sha256")
    prior_fingerprint = _sealed(fingerprint_body, "business_fingerprint_sha256")
    coverage = _sealed({
        "schema": "jaggedthoughts-research-evidence-coverage-v1",
        "status": "covered_by_monitored_dossier", "covered": True,
        "entity_id": "ACME", "candidate_leaf": leaf,
        "candidate_sha256": candidate["candidate_sha256"],
        "prior_dossier_leaf": "3" * 64, "subscription_leaf": None,
        "accepted_reassessment_leaves": [], "source_checks": [],
        "missing_required_source_ids": [], "max_age_days": 45, "expires_at": None,
        "deep_research_activation": "reuse", "available_at": candidate["as_of"],
        "scope": "qualitative_strategy_industry_and_durable_earnings_only",
        "excluded_scope": ["current_candidate_metrics", "valuation", "rank", "factor_estimates",
                           "portfolio_or_capital_action"],
        "capital_authority": False,
    }, "coverage_sha256")
    bridged_inputs = {
        **inputs, "dossier": prior, "business_fingerprint": prior_fingerprint,
        "research_coverage": coverage, "research_coverage_leaf": "6" * 64,
    }
    bridged = compile_inactive_equity_proposal(**bridged_inputs)
    assert bridged["evidence"]["candidate_sha256"] == candidate["candidate_sha256"]
    assert bridged["evidence"]["dossier_sha256"] == prior["dossier_sha256"]
    assert bridged["evidence"]["research_coverage_sha256"] == coverage["coverage_sha256"]
    with pytest.raises(ValueError, match="requires covered"):
        compile_inactive_equity_proposal(**{
            key: value for key, value in bridged_inputs.items()
            if key not in {"research_coverage", "research_coverage_leaf"}
        })

    decision = activate_equity_proposal(
        eligible, confirmation=eligible["required_operator_confirmation"],
        operator_id="operator", activated_at="2026-01-04T00:00:00Z",
    )
    assert decision["paper_policy"]["target_weight"] == 0.0
    assert decision["watch_registry"]["eligible"] is True
    assert decision["watch_registry"]["position_admission_allowed"] is False
    assert decision["capital_authority"] is decision["portfolio_authority"] is decision["brokerage_authority"] is False
