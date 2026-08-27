from ztare.common.equivariance import stable_sha256
from ztare.investment.allocation_readiness import _activation, compile_allocation_readiness


def _sealed(body, field):
    return {**body, field: stable_sha256(body)}


def _rank_input(candidates, eligible=True):
    body = {
        "schema": "jaggedthoughts-rank-program-input-v1",
        "discovery_run_id": "discovery-test",
        "lanes": [{
            "candidates": [
                {"candidate_id": row["candidate_id"], "rank_program_eligible": eligible}
                for row in candidates
            ],
        }],
    }
    return _sealed(body, "rank_program_input_sha256")


def test_fund_proposal_blocker_precedes_generic_review_gap():
    _state, gaps, next_activation = _activation(
        entity_kind="public_fund", screen="qualified", rank_eligible=True,
        dossier=False, decision=None, lineage_exact=False,
        portfolio_candidate=False, allocated=False,
        fund_proposal={
            "blockers": ["candidate_bound_opportunity_watchlist_absent"],
            "activation_eligible": False,
        },
    )

    assert gaps == [
        "fund_paper_proposal:candidate_bound_opportunity_watchlist_absent",
        "fund_paper_proposal:candidate_bound_inactive_proposal_absent",
    ]
    assert next_activation == "repair_fund_proposal_evidence"


def test_current_researched_watch_owns_the_position_admission_boundary():
    state, gaps, next_activation = _activation(
        entity_kind="public_equity", screen="qualified", rank_eligible=True,
        dossier=True, decision=None, lineage_exact=False,
        portfolio_candidate=False, allocated=False,
        paper_watch={
            "position_admission": {
                "eligible": False, "blockers": ["return_basis_unidentified"],
            },
        },
        paper_watch_lineage_exact=True,
    )

    assert state == "active_paper"
    assert gaps == [
        "instrument_admission:return_basis_unidentified",
        "instrument_portfolio_admission_absent",
    ]
    assert next_activation == "compile_instrument_portfolio_admission_contract"

    instrument = {
        "eligibility": {"research_paper_portfolio_candidate": True, "blockers": []},
    }
    state, gaps, next_activation = _activation(
        entity_kind="public_equity", screen="qualified", rank_eligible=True,
        dossier=True, decision=None, lineage_exact=False,
        portfolio_candidate=False, allocated=False,
        paper_watch={"position_admission": {"eligible": False}},
        paper_watch_lineage_exact=True, instrument_admission=instrument,
    )
    assert (state, gaps, next_activation) == (
        "portfolio_candidate", ["household_policy_rival_not_selected"],
        "review_household_policy_rivals",
    )


def test_allocation_readiness_requires_exact_candidate_lineage_before_paper_state():
    candidates = [
        {
            "candidate_id": "equity:A", "candidate_sha256": "a" * 64,
            "entity_id": "A", "entity_kind": "public_equity", "screen_status": "qualified",
            "activation_class": "underwriting_ready", "research": {"dossier_available": True},
        },
        {
            "candidate_id": "equity:B", "candidate_sha256": "b" * 64,
            "entity_id": "B", "entity_kind": "public_equity", "screen_status": "qualified",
            "activation_class": "underwriting_ready", "research": {"dossier_available": True},
        },
    ]
    book = _sealed({
        "schema": "jaggedthoughts-opportunity-book-v1", "generated_at": "2026-01-02T00:00:00Z",
        "discovery_run_id": "discovery-test", "discovery_run_sha256": "d" * 64,
        "candidates": candidates,
    }, "book_sha256")
    underwriting = _sealed({
        "schema": "jaggedthoughts-underwriting-opportunity-index-v1",
        "discovery_run_sha256": "d" * 64,
        "candidates": [
            {"candidate_sha256": candidate["candidate_sha256"], "entity_id": candidate["entity_id"],
             "ranking": {"eligible": True, "rank": rank, "research_priority_score": 1 / rank,
                         "research_priority_is_expected_return": False}}
            for rank, candidate in enumerate(candidates, 1)
        ],
    }, "underwriting_index_sha256")

    def decision(entity, candidate_sha, stage):
        return _sealed({
            "schema": "jaggedthoughts-investment-decision-v1", "decision_id": f"decision-{entity}",
            "as_of": "2026-01-02T00:00:00Z", "entity": {"entity_id": entity},
            "profile_lifecycle": {"data_class": "operator", "stage": stage},
            "discovery_origin": {"candidate_sha256": candidate_sha},
        }, "decision_record_sha256")

    decisions = [decision("A", "a" * 64, "active"), decision("B", "stale", "draft")]
    portfolio = _sealed({
        "schema": "jaggedthoughts-portfolio-assembly-v1",
        "candidates": [{"decision_id": "decision-A"}], "selected_target_weights": {"A": 0.1},
    }, "portfolio_assembly_sha256")
    result = compile_allocation_readiness(
        opportunity_book=book, underwriting_index=underwriting,
        rank_program_input=_rank_input(candidates),
        decisions=decisions, portfolio_assembly=portfolio,
    )
    by_entity = {row["entity_id"]: row for row in result["candidates"]}

    assert by_entity["A"]["paper"]["state"] == "allocated_paper"
    assert by_entity["A"]["allocation_ready"] is True
    assert by_entity["A"]["research_priority"]["is_expected_return"] is False
    assert by_entity["B"]["paper"]["state"] == "screened"
    assert by_entity["B"]["activation_gaps"] == ["operator_decision_not_bound_to_current_candidate"]
    assert result["capital_authority"] is False


def test_fund_draft_binds_exact_candidate_independent_of_audit_order():
    candidate = {
        "candidate_id": "fund:F", "candidate_sha256": "f" * 64,
        "entity_id": "F", "entity_kind": "public_fund", "screen_status": "qualified",
        "activation_class": "fund_review_ready", "research": {"dossier_available": True},
    }
    book = _sealed({
        "schema": "jaggedthoughts-opportunity-book-v1",
        "generated_at": "2026-01-02T00:00:00Z", "discovery_run_id": "discovery-test",
        "discovery_run_sha256": "d" * 64,
        "candidates": [candidate],
    }, "book_sha256")
    underwriting = _sealed({
        "schema": "jaggedthoughts-underwriting-opportunity-index-v1",
        "discovery_run_sha256": "d" * 64,
        "candidates": [{
            "candidate_sha256": "f" * 64, "entity_id": "F",
            "ranking": {"eligible": True, "rank": 1, "research_priority_score": 1.0,
                        "research_priority_is_expected_return": False},
        }],
    }, "underwriting_index_sha256")

    def row(entity, digest):
        proposal = _sealed({
            "schema": "jaggedthoughts-public-fund-paper-proposal-v1",
            "proposal_id": f"fund-paper:{entity}", "entity": {"entity_id": entity},
            "evidence": {"candidate_sha256": digest}, "activation_blockers": [],
        }, "proposal_sha256")
        return {"entity_id": entity, "candidate_sha256": digest,
                "activation_eligible": True, "blockers": [], "proposal": proposal}

    rows = [row("X", "x" * 64), row("F", "f" * 64)]
    results = []
    for ordered in (rows, list(reversed(rows))):
        audit = _sealed({
            "schema": "jaggedthoughts-public-fund-paper-proposal-audit-v1",
            "rows": ordered,
        }, "audit_sha256")
        results.append(compile_allocation_readiness(
            opportunity_book=book, underwriting_index=underwriting,
            rank_program_input=_rank_input([candidate]),
            fund_proposal_audit=audit,
        ))

    fund = results[0]["candidates"][0]
    assert fund["paper"]["state"] == "draft"
    assert fund["paper"]["proposal_id"] == "fund-paper:F"
    assert fund["activation_gaps"] == ["paper_watch_activation_required"]
    assert results[0]["candidates"] == results[1]["candidates"]
