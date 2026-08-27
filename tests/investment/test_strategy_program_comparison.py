from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_program_comparison import (
    compile_strategy_program_operating_comparison,
)


def _hashed(body, field):
    return {**body, field: stable_sha256(body)}


def test_program_comparison_matches_exact_environments_and_is_order_invariant():
    phenotype_sha = stable_sha256(["a", "b"])
    source_definition_sha = stable_sha256({
        "metric_locator": None,
        "measurement_source_catalog": None,
    })

    plans, treated = [], []
    for index in range(4):
        entity, environment = f"T{index}", ["software" if index < 2 else "industrial"]
        readout_sha = stable_sha256([entity, "readout"])
        plan = _hashed({
            "schema": "jaggedthoughts-strategy-program-outcome-plan-v1",
            "entity_id": entity, "program_phenotype_sha256": phenotype_sha,
            "program_roles": ["global_frontier"],
            "environment_boundaries": environment,
            "readouts": [{
                "readout_sha256": readout_sha, "metric_id": "margin", "unit": "ratio",
                "direction": "increase", "minimum_effect": 0.05, "horizon_days": 365,
                "outcome_role": "terminal_operating",
                "acquisition_mode": "subscription_primary_document",
                "source_definition_sha256": source_definition_sha,
            }],
        }, "plan_sha256")
        plans.append(plan)
        treated.append(_hashed({
            "schema": "jaggedthoughts-strategy-program-outcome-v1",
            "plan_sha256": plan["plan_sha256"], "readout_sha256": readout_sha,
            "entity_id": entity, "metric_id": "margin", "unit": "ratio",
            "direction": "increase", "minimum_effect": 0.05, "horizon_days": 365,
            "outcome_role": "terminal_operating",
            "acquisition_mode": "subscription_primary_document",
            "source_definition_sha256": source_definition_sha,
            "observed_effect": 0.20, "available_at": "2026-06-01T00:00:00Z",
        }, "episode_sha256"))

    transfer_card = {
        "program_phenotype_sha256": phenotype_sha,
        "metric_id": "margin", "unit": "ratio", "direction": "increase",
        "minimum_effect": 0.05, "horizon_days": 365,
        "outcome_role": "terminal_operating",
        "acquisition_mode": "subscription_primary_document",
        "source_definition_sha256": source_definition_sha,
        "settled_episode_count": 4,
        "episode_sha256s": sorted(row["episode_sha256"] for row in treated),
    }
    transfer_card = {
        **transfer_card, "card_sha256": stable_sha256(transfer_card),
    }
    transfer = _hashed({
        "schema": "jaggedthoughts-strategy-program-transfer-index-v1",
        "cards": [transfer_card],
    }, "index_sha256")
    acquisition_card = _hashed({
        "transfer_card_sha256": transfer_card["card_sha256"],
        "admitted_source_controls": [],
    }, "acquisition_card_sha256")
    acquisition = _hashed({
        "schema": "jaggedthoughts-strategy-program-control-acquisition-v1",
        "program_transfer_sha256": transfer["index_sha256"],
        "cards": [acquisition_card],
    }, "acquisition_sha256")

    controls = []
    for identity, effect, prefix in (
        ("same_constituents_without_joint_evidence", 0.10, "F"),
        ("one_choice_base_program", 0.08, "B"),
        ("same_size_local_peak", 0.05, "L"),
    ):
        for index in range(4):
            entity = f"{prefix}{index}"
            controls.append(_hashed({
                "schema": "jaggedthoughts-strategy-program-control-outcome-v1",
                "program_control_acquisition_sha256": acquisition["acquisition_sha256"],
                "acquisition_card_sha256": acquisition_card["acquisition_card_sha256"],
                "transfer_card_sha256": transfer_card["card_sha256"],
                "control_plan_sha256": stable_sha256([entity, "control"]),
                "entity_id": entity, "control_identity": identity,
                "environment_boundaries": ["software" if index < 2 else "industrial"],
                "metric_id": "margin", "unit": "ratio", "direction": "increase",
                "minimum_effect": 0.05, "horizon_days": 365,
                "outcome_role": "terminal_operating",
                "acquisition_mode": "subscription_primary_document",
                "source_definition_sha256": source_definition_sha,
                "observed_effect": effect,
                "available_at": "2026-06-01T00:00:00Z",
            }, "episode_sha256"))
    controls.append(_hashed({
        **{key: value for key, value in controls[0].items() if key != "episode_sha256"},
        "control_plan_sha256": stable_sha256(["wrong-environment", "control"]),
        "entity_id": "WRONG", "environment_boundaries": ["utilities"],
    }, "episode_sha256"))

    extra_readout_sha = stable_sha256(["EXTRA", "readout"])
    extra_plan = _hashed({
        **{key: value for key, value in plans[0].items() if key != "plan_sha256"},
        "entity_id": "EXTRA",
        "readouts": [{**plans[0]["readouts"][0], "readout_sha256": extra_readout_sha}],
    }, "plan_sha256")
    plans.append(extra_plan)
    treated.append(_hashed({
        **{key: value for key, value in treated[0].items() if key != "episode_sha256"},
        "plan_sha256": extra_plan["plan_sha256"], "readout_sha256": extra_readout_sha,
        "entity_id": "EXTRA", "observed_effect": 0.99,
    }, "episode_sha256"))

    kwargs = dict(
        program_transfer=transfer, control_acquisition=acquisition,
        program_plans=plans, program_episodes=treated,
        control_episodes=controls, generated_at="2026-07-01T00:00:00Z",
    )
    result = compile_strategy_program_operating_comparison(**kwargs)
    comparison = {
        row["control_identity"]: row for row in result["cards"][0]["comparisons"]
    }
    composition = comparison["same_constituents_without_joint_evidence"]
    edge = comparison["one_choice_base_program"]
    frontier = comparison["same_size_local_peak"]
    assert composition["operating_association_reviewable"] is True
    assert composition["equal_weight_environment_association"] == 0.10
    assert round(frontier["equal_weight_environment_association"], 8) == 0.15
    assert round(edge["equal_weight_environment_association"], 8) == 0.12
    assert result["reviewable_one_choice_card_count"] == 1
    assert result["treated_episode_count"] == 4
    assert composition["control_entity_count"] == 4
    assert result["causal_program_credit"] is False
    assert result["security_return_credit"] is False
    assert result["capital_authority"] is False

    reordered = compile_strategy_program_operating_comparison(**{
        **kwargs, "program_plans": list(reversed(plans)),
        "program_episodes": list(reversed(treated)),
        "control_episodes": list(reversed(controls)),
    })
    assert reordered["comparison_sha256"] == result["comparison_sha256"]
