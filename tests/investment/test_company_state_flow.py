from ztare.investment.company_state_flow import (
    _load_state_observations,
    decompose_transition_counts,
)


def test_probability_current_distinguishes_direction_from_symmetric_traffic():
    clockwise = decompose_transition_counts([
        [4, 12, 0, 0], [0, 4, 0, 12], [12, 0, 4, 0], [0, 0, 12, 4],
    ])
    symmetric = decompose_transition_counts([
        [4, 6, 0, 6], [6, 4, 6, 0], [0, 6, 4, 6], [6, 0, 6, 4],
    ])

    assert clockwise["circulation_strength"] > symmetric["circulation_strength"] + 0.1
    assert clockwise["conservation_residual"] < 1e-10
    assert all(
        abs(clockwise["probability_current"][left][right]
            + clockwise["probability_current"][right][left]) < 1e-12
        for left in range(4) for right in range(4)
    )


def test_state_loader_retains_only_effective_facts_and_epoch_prices(tmp_path):
    source = tmp_path / "observations.csv"
    source.write_text(
        "observation_id,entity_id,metric_id,value,unit,observed_at,available_at,source_ref\n"
        "old,A,revenue_fy,10,USD,2025-12-31T23:59:59Z,2026-01-10T00:00:00Z,filing\n"
        "new,A,revenue_fy,11,USD,2025-12-31T23:59:59Z,2026-02-10T00:00:00Z,filing\n"
        "p1,A,price,8,USD,2026-01-31T00:00:00Z,2026-01-31T00:00:00Z,prices\n"
        "p2,A,price,9,USD,2026-03-30T00:00:00Z,2026-03-30T00:00:00Z,prices\n"
        "late,A,price,12,USD,2026-07-01T00:00:00Z,2026-07-01T00:00:00Z,prices\n"
        "noise,A,adjusted_price,9,USD,2026-03-30T00:00:00Z,2026-03-30T00:00:00Z,prices\n"
    )
    rows = _load_state_observations(
        source, ("2026-03-31", "2026-06-30"), source_as_of="2026-06-30T23:59:59Z",
    )
    assert {row.observation_id for row in rows} == {"new", "p2"}
