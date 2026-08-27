from ztare.investment.historical_strategy_bulk_effects import _ready_at
from ztare.investment.historical_strategy_bulk_learning import (
    _select_law_trial_holdout,
    _semantic_resolution_priority,
)
from ztare.investment.historical_strategy_bulk_outcomes import (
    _coadoption_audit,
    compile_strategy_group_time_support,
    strategy_history_ready_at,
)


def _history(cik: str, event_year: int, *, control_id: str | None = None) -> dict:
    row = {
        "cik": cik,
        "event_year": event_year,
        "annual_history": [
            {"observed_at": f"{year}-12-31T00:00:00Z"}
            for year in (2017, 2018, 2019, 2021)
        ],
    }
    if control_id:
        row.update(control_id=control_id, control_through_year=2021)
    return row


def test_bounded_non_adopter_fills_only_its_source_proven_control_window() -> None:
    treated = [_history(f"T{index}", 2020) for index in range(4)]
    future = [_history(f"F{index}", 2023) for index in range(3)]
    bounded = _history("N0", 10_000, control_id="n" * 64)

    before = compile_strategy_group_time_support(treated, future, 2020)
    after = compile_strategy_group_time_support(treated, future, 2020, [bounded])
    assert not before["joint_support_ready"]
    assert after["joint_support_ready"]
    assert after["post_bounded_control_ids"] == ["n" * 64]

    bounded["control_through_year"] = 2020
    assert not compile_strategy_group_time_support(
        treated, future, 2020, [bounded],
    )["joint_support_ready"]


def test_coadoption_never_enters_strategy_history_support() -> None:
    def event(sha: str, cik: str, eligibility: str = "operating_strategy_event") -> dict:
        return {
            "event_sha256": sha * 64, "cik": cik,
            "occurred_at": "2020-06-01T00:00:00Z",
            "strategy_event_eligibility": eligibility,
        }

    isolated = event("a", "1")
    concurrent = [event("b", "2"), event("c", "2")]
    bundle = event("d", "3", "operating_strategy_bundle_event")
    audit = _coadoption_audit([isolated, *concurrent, bundle])

    assert audit[isolated["event_sha256"]]["coadoption_status"] == "isolated_strategy_event"
    assert audit[concurrent[0]["event_sha256"]]["coadoption_status"] == "excluded_concurrent_event"
    assert audit[bundle["event_sha256"]]["coadoption_status"] == "excluded_bundle_event"
    history = {
        **_history("2", 2020), "phenotype_history_closed": True,
        **audit[concurrent[0]["event_sha256"]],
    }
    assert not strategy_history_ready_at(history, 2020)
    assert not _ready_at(history, 2020)


def test_sealed_law_trial_routes_one_unseen_treated_and_future_adopter() -> None:
    def event(cik, year):
        return {
            "accession_number": f"A-{cik}", "cik": cik, "sic": "2810",
            "occurred_at": f"{year}-06-01T00:00:00Z",
            "available_at": f"{year}-06-02T00:00:00Z",
        }

    trial = {
        "trial_id": "trial", "trial_sha256": "f" * 64,
        "candidates": [{
            "candidate_identity_sha256": "c" * 64,
            "candidate_identity": {
                "parent": {"sic2": "28", "adoption_year": 2020},
                "moderators": {"transaction_form": "asset_purchase"},
            },
            "training_treated_entity_ids": ["OLD"],
            "training_future_adopter_entity_ids": [],
        }],
    }
    rows = _select_law_trial_holdout(
        [event("OLD", 2020), event("NEW", 2020), event("FUTURE", 2023)],
        set(), trial,
        {cik: [f"{year}-12-31" for year in (2017, 2018, 2019, 2021, 2024)]
         for cik in ("OLD", "NEW", "FUTURE")},
        2,
    )
    assert [(row["cik"], row["selection_basis"]["candidate_relation"]) for row in rows] == [
        ("NEW", "treated"), ("FUTURE", "future_adopter"),
    ]
    treated_deficit_only = _select_law_trial_holdout(
        [event("NEW", 2020), event("FUTURE", 2023)], set(), trial,
        {cik: [f"{year}-12-31" for year in (2017, 2018, 2019, 2021, 2024)]
         for cik in ("NEW", "FUTURE")},
        2, support_by_candidate={"c" * 64: {
            "treated_entity_count": 0, "future_adopter_entity_count": 4,
        }},
    )
    assert [(row["cik"], row["selection_basis"]["candidate_relation"])
            for row in treated_deficit_only] == [("NEW", "treated")]
    globally_excluded = _select_law_trial_holdout(
        [event("NEW", 2020), event("FUTURE", 2023)], set(), trial,
        {cik: [f"{year}-12-31" for year in (2017, 2018, 2019, 2021, 2024)]
         for cik in ("NEW", "FUTURE")},
        2, {"NEW", "FUTURE"},
    )
    assert globally_excluded == []
    assert _semantic_resolution_priority({
        "accession_number": "trial", "acquisition_selection_receipt": {
            "selection_mode": "sealed_law_trial_holdout", "selection_rank": 7,
            "selection_basis": {"trial_sha256": "current"},
        },
    }, "current") < _semantic_resolution_priority({"accession_number": "general"}, "current")
    assert _semantic_resolution_priority({
        "accession_number": "old-trial", "acquisition_selection_receipt": {
            "selection_mode": "sealed_law_trial_holdout", "selection_rank": 1,
            "selection_basis": {"trial_sha256": "superseded"},
        },
    }, "current") > _semantic_resolution_priority({
        "accession_number": "frontier", "acquisition_selection_receipt": {
            "selection_mode": "causal_panel_frontier", "selection_rank": 9,
        },
    }, "current")
