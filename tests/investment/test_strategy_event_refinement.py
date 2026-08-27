import pytest

from ztare.investment.strategy_event_refinement import (
    STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA,
    apply_strategy_event_refinements,
    compile_strategy_event_refinement_request,
    compile_strategy_event_refinement_result,
    compile_interval_treatment_period_frontier,
    due_strategy_event_refinement_requests,
)


def _move():
    return {
        "claim_status": "supported", "causal_panel_status": "treatment_timing_interval_censored",
        "evidence_epoch": "2025-01-01T00:00:00Z", "move_sha256": "a" * 64,
        "strategy_frontier_sha256": "b" * 64, "entity_id": "ACME",
        "option_id": "integrate_repairs", "description": "Internalize repairs.",
        "mechanism_signature": {"action": "integrate_value_chain", "economic_bridge": "earnings_durability"},
        "mechanism_phenotype": {"strategy_form": "vertical_capability"},
        "implementation_event": {"treatment_timing_status": "interval_censored_adoption_event"},
    }


def test_exact_event_receipt_refines_timing_without_rewriting_move_identity():
    request = compile_strategy_event_refinement_request(
        _move(), library_sha256="c" * 64, search_end_at="2026-01-01T00:00:00Z",
    )
    raw = {
        "schema": STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA,
        "request_sha256": request["request_sha256"], "move_sha256": "a" * 64,
        "entity_id": "ACME", "classification": "exact_implementation_event_found",
        "assessed_at": "2026-01-02T00:00:00Z",
        "coverage": {"sec_filings_searched": True, "issuer_materials_searched": True,
                     "search_start_at": request["search_start_at"], "search_end_at": request["search_end_at"]},
        "exact_event": {"event_id": "repair-close", "description": "Repair acquisition closed.",
                        "occurred_at": "2025-06-01T00:00:00Z", "available_at": "2025-06-02T00:00:00Z",
                        "implementation_mode": "acquisition", "implementation_state": "completed",
                        "source_urls": ["https://www.sec.gov/filing"]},
        "sources": [{"url": "https://www.sec.gov/filing", "source_kind": "filing",
                     "published_at": "2025-06-02T00:00:00Z", "supports": ["closing date"]}],
        "rationale": "The filed closing date resolves the interval.", "residuals": [],
    }
    result = compile_strategy_event_refinement_result(raw, request)
    move = _move()

    assert apply_strategy_event_refinements([move], requests=[request], results=[result]) == 1
    assert move["move_sha256"] == "a" * 64
    assert move["causal_panel_status"] == "treatment_event_ready"
    assert move["timing_refinement"]["exact_event"]["occurred_at"] == "2025-06-01T00:00:00Z"

    commitment = {
        **raw,
        "exact_event": {
            **raw["exact_event"], "implementation_mode": "supply_commitment",
            "mechanism_effective_until": "2025-12-31T23:59:59Z",
        },
        "sources": [{
            **raw["sources"][0],
            "supports": ["closing date", "mechanism_effective_until"],
        }],
    }
    refined = compile_strategy_event_refinement_result(commitment, request)
    assert refined["exact_event"]["mechanism_effective_until"] == "2025-12-31T23:59:59Z"
    with pytest.raises(ValueError, match="source-bound effective_until"):
        compile_strategy_event_refinement_result({**commitment, "sources": raw["sources"]}, request)

    with pytest.raises(ValueError, match="classification and evidence differ"):
        compile_strategy_event_refinement_result(
            {**raw, "classification": "interval_remains_censored"}, request,
        )


def test_censored_event_is_researched_again_only_after_its_cooldown():
    move = _move()
    library = {"library_sha256": "c" * 64, "moves": [move], "move_families": []}
    request = compile_strategy_event_refinement_request(
        move, library_sha256=library["library_sha256"],
        search_end_at="2026-01-01T00:00:00Z",
    )
    result = compile_strategy_event_refinement_result({
        "schema": STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA,
        "request_sha256": request["request_sha256"], "move_sha256": "a" * 64,
        "entity_id": "ACME", "classification": "interval_remains_censored",
        "assessed_at": "2026-01-02T00:00:00Z",
        "coverage": {"sec_filings_searched": True, "issuer_materials_searched": True,
                     "search_start_at": request["search_start_at"],
                     "search_end_at": request["search_end_at"]},
        "exact_event": None,
        "censored_interval": {
            "earliest_possible_at": "2025-01-01T00:00:00Z",
            "latest_possible_at": "2025-06-01T00:00:00Z",
            "source_urls": ["https://www.sec.gov/filing"],
        },
        "sources": [{"url": "https://www.sec.gov/filing", "source_kind": "filing",
                     "published_at": "2025-06-02T00:00:00Z", "supports": ["interval only"]}],
        "rationale": "The filing preserves an interval.", "residuals": ["Exact date absent."],
    }, request)
    assert result["interval_timing_eligible"] is True
    assert result["censored_interval"]["latest_possible_at"] == "2025-06-01T00:00:00Z"
    move["timing_refinement"] = {
        "result_sha256": result["result_sha256"],
        "censored_interval": result["censored_interval"],
    }
    timing = compile_interval_treatment_period_frontier(
        move, fiscal_period_ends=["2024-12-31T00:00:00Z", "2025-12-31T00:00:00Z"],
    )
    assert timing["admissible_first_full_treatment_periods"] == [2026]
    assert timing["coarse_period_identified"] is True

    assert due_strategy_event_refinement_requests(
        library, as_of="2026-04-01T00:00:00Z",
        prior_requests=[request], results=[result],
    ) == []
    refreshed = due_strategy_event_refinement_requests(
        library, as_of="2026-04-03T00:00:00Z",
        prior_requests=[request], results=[result],
    )
    assert len(refreshed) == 1
    assert refreshed[0]["move_sha256"] == request["move_sha256"]
    assert refreshed[0]["request_sha256"] != request["request_sha256"]

    successor_library = {**library, "library_sha256": "d" * 64}
    successor = due_strategy_event_refinement_requests(
        successor_library, as_of="2026-01-03T00:00:00Z",
        prior_requests=[request], results=[],
    )
    assert successor[0]["library_sha256"] == "d" * 64
    assert successor[0]["request_sha256"] != request["request_sha256"]

    older = {
        **move, "move_sha256": "e" * 64,
        "evidence_epoch": "2024-01-01T00:00:00Z",
    }
    current_only = due_strategy_event_refinement_requests(
        {**library, "moves": [older, move]}, as_of="2026-01-01T00:00:00Z",
    )
    assert [row["move_sha256"] for row in current_only] == [move["move_sha256"]]
