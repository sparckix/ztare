from ztare.investment.strategy_program_representation_ablation import (
    compile_strategy_program_representation_tournament,
)
from ztare.common.equivariance import stable_sha256


LEAF_A, LEAF_B, INTERACTION = "a" * 64, "b" * 64, "c" * 64


def _row(entity: str, interaction: bool, path: int, *, future: bool = False) -> dict:
    target = (
        "high_value_high_durability"
        if interaction else "low_value_low_durability"
    )
    epochs = (
        ("2025-03-31", "2025-06-30", "2025-09-30")
        if future else ("2024-03-31", "2024-06-30", "2024-09-30")
    )
    definition = {
        "program_id": f"program:{interaction}",
        "mechanism_phenotype_sha256s": [LEAF_A, LEAF_B],
        "interaction_phenotype_sha256s": [INTERACTION] if interaction else [],
    }
    row = {
        "entity_id": entity,
        "source_epoch": epochs[0], "intermediate_epoch": epochs[1],
        "terminal_epoch": epochs[2],
        "source_state": "low_value_low_durability",
        "intermediate_state": target, "terminal_state": target,
        "path_variant": path,
        **definition,
        "program_definition_sha256": stable_sha256(definition),
        "program_adoption_result_sha256": "e" * 64,
        "program_available_at": "2023-01-01T00:00:00Z",
    }
    return {**row, "model_row_sha256": stable_sha256(row)}


def test_integrated_interaction_must_beat_the_identical_leaf_bag():
    def cohort(prefix: str, count: int, *, future: bool = False) -> list[dict]:
        return [
            _row(
                f"{prefix}-{index:02d}",
                int(stable_sha256(f"{prefix}-{index:02d}")[0], 16) < 8,
                path,
                future=future,
            )
            for index in range(count) for path in range(4)
        ]

    result = compile_strategy_program_representation_tournament(
        {
            "visible": cohort("fit", 20),
            "future_time": cohort("fit", 20, future=True),
            "unseen_issuer": cohort("hold", 20),
        },
        state_representation_sha256="f" * 64,
    )

    assert result["candidate_control_pass"] is True
    assert result["scores"]["unseen_issuer"]["integrated_choice_system"][
        "cross_entropy"
    ] < result["scores"]["unseen_issuer"]["bag_of_identical_leaves"][
        "cross_entropy"
    ]
