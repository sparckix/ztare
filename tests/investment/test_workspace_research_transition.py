from ztare.investment.workspace import _active_research_transition


def test_next_transition_uses_the_full_subscription_queue_and_budget_reset():
    transition = _active_research_transition({
        "daily_dispatch_budget": {
            "utc_day": "2026-08-23", "remaining": 0, "exhausted": True,
        },
        "service": {"status": "running"},
        "persistence": {"starter": "forensic_workbench_server_or_investment_cli"},
        "next_job": {
            "work_id": "event:1",
            "kind": "jaggedthoughts_strategy_event_refinement_research",
            "fresh_dispatch_budget_units": 1,
            "payload": {"entity_id": "SARO"},
        },
    })

    assert transition == {
        "enabled": True, "active": False,
        "transition": "jaggedthoughts_strategy_event_refinement_research",
        "work_id": "event:1",
        "job_kind": "jaggedthoughts_strategy_event_refinement_research",
        "dispatch_selection_basis": None,
        "subject_id": "SARO", "research_rank": None, "potential_rank": None,
        "status": "blocked", "not_before": "2026-08-24T00:00:00Z",
        "due_next_claim": True, "waiting_count": 0,
        "starter": "forensic_workbench_server_or_investment_cli",
        "blocked_reasons": ["daily_subscription_dispatch_budget_insufficient"],
        "capital_authority": False,
    }
