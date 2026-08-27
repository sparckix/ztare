import pytest

from ztare.investment.strategy_path_lagrangian import compile_strategy_path_tournament


SHA = "a" * 64


def _row(entity: str, exposed: bool, high: bool, *, future: bool = False) -> dict:
    state = "high_value_high_durability" if high else "low_value_low_durability"
    epochs = (
        ("2025-03-31", "2025-06-30", "2025-09-30")
        if future else ("2024-03-31", "2024-06-30", "2024-09-30")
    )
    return {
        "entity_id": entity,
        "source_epoch": epochs[0],
        "intermediate_epoch": epochs[1],
        "terminal_epoch": epochs[2],
        "source_state": "low_value_low_durability",
        "intermediate_state": state,
        "terminal_state": state,
        "strategy_exposure": "exposed" if exposed else "unexposed",
        "mechanism_phenotype_sha256": SHA,
        **({
            "event_available_at": "2024-01-01T00:00:00Z",
            "implementation_event_sha256": "f" * 64,
        } if exposed else {"monitoring_coverage_sha256": "b" * 64}),
    }


def test_strategy_tilt_transfers_only_when_exposure_predicts_paths():
    def cohort(prefix: str, repeats: int, *, future: bool = False) -> list[dict]:
        return [
            _row(
                f"{prefix}-{offset}-{kind}", kind == "exposed", kind == "exposed",
                future=future,
            )
            for offset in range(repeats) for kind in ("exposed", "unexposed")
        ]

    result = compile_strategy_path_tournament(
        {
            "visible": cohort("fit", 20),
            "future_time": cohort("fit", 8, future=True),
            "unseen_issuer": cohort("hold", 8),
        },
        phenotype_sha256=SHA, state_representation_sha256="c" * 64,
    )

    assert result["fitted_theta"] > 0
    assert result["candidate_control_pass"] is True
    assert result["same_feature_offset_logit"]["numerically_equivalent"] is True
    assert result["capital_authority"] is False


def test_unexposed_path_requires_no_event_coverage():
    row = _row("fit", False, False)
    row.pop("monitoring_coverage_sha256")
    with pytest.raises(ValueError, match="monitored no-event coverage"):
        compile_strategy_path_tournament(
            {
                "visible": [row],
                "future_time": [{**row, "source_epoch": "2025-03-31", "intermediate_epoch": "2025-06-30", "terminal_epoch": "2025-09-30"}],
                "unseen_issuer": [{**row, "entity_id": "hold"}],
            },
            phenotype_sha256=SHA, state_representation_sha256="c" * 64,
        )
