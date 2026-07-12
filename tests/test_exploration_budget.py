from __future__ import annotations

import pytest

from ztare.leanmill.exploration_budget import (
    BudgetExceeded,
    ExplorationBudget,
    ExplorationBudgetLedger,
    budget_preset,
    budget_to_user_mapping,
    compile_budget_preference,
    load_budget_yaml,
    parse_exploration_budget,
    render_budget_yaml,
)
from ztare.leanmill.theory_ir import content_hash


def test_yaml_budget_is_frozen_and_roundtrips():
    mapping = budget_to_user_mapping(budget_preset("quick"))
    mapping["budget"]["wall_clock"] = "2h"
    mapping["budget"]["agent_turns"] = 12
    mapping["budget"]["boundary"]["queries"] = 4
    mapping["budget"]["metered_api_usd"] = "5"
    budget = parse_exploration_budget(mapping)
    assert budget.wall_clock_s == 7200
    assert budget.hard_caps["agent_turns"] == 12
    assert budget.hard_caps["boundary_queries"] == 4
    assert budget.hard_caps["metered_usd_micros"] == 5_000_000
    assert budget.allocation_policy == "roll_forward_protected_future"
    assert ExplorationBudget.from_json(budget.to_json()) == budget


def test_legacy_budget_json_retains_strict_phase_semantics():
    row = budget_preset("smoke_20m").to_json()
    row.pop("allocation_policy")
    row.pop("budget_digest")
    assert ExplorationBudget.from_json(row).allocation_policy == "strict_phase_caps"


def test_pre_formal_peer_budget_digest_reopens_without_policy_drift(tmp_path):
    row = budget_preset("smoke_20m").to_json()
    for resource in ("formal_peer_attempts", "formal_peer_millis"):
        row["hard_caps"].pop(resource)
        for caps in row["phase_caps"].values():
            caps.pop(resource)
    core = {key: value for key, value in row.items() if key != "budget_digest"}
    row["budget_digest"] = "budget:" + content_hash(core)

    loaded = ExplorationBudget.from_json(row)
    assert loaded.digest == row["budget_digest"]
    assert loaded.hard_caps["formal_peer_attempts"] == 0
    assert loaded.to_json() == row

    ledger = ExplorationBudgetLedger(
        tmp_path / "legacy.events.jsonl",
        loaded,
        attempt_id="legacy-attempt",
    )
    reopened = ExplorationBudgetLedger(
        tmp_path / "legacy.events.jsonl",
        ExplorationBudget.from_json(row),
        attempt_id="legacy-attempt",
    )
    assert reopened.budget.digest == ledger.budget.digest


def test_no_paid_budget_keeps_deterministic_resources():
    mapping = budget_to_user_mapping(budget_preset("smoke"))
    mapping["budget"]["metered_api_usd"] = "0"
    budget = parse_exploration_budget(mapping)
    assert budget.wall_clock_s == 1200
    assert budget.hard_caps["provider_calls"] > 0
    assert budget.hard_caps["metered_usd_micros"] == 0
    assert budget.hard_caps["context_models"] > 0


def test_natural_language_budget_maps_common_preferences_and_delegates_math_stop():
    compiled = budget_to_user_mapping(
        budget_preset("standard"),
        delegated_stop_instruction="three structurally distinct theories survive size five",
    )
    compiled["budget"]["wall_clock"] = "20m"
    compiled["budget"]["metered_api_usd"] = "0"
    compiled["budget"]["agent_turns"] = 12
    budget, receipt = compile_budget_preference(
        "Work for at most 20 minutes with no paid APIs and 12 agent turns; "
        "stop when three structurally distinct theories survive size five.",
        compiler_fn=lambda _text: compiled,
    )
    assert budget.wall_clock_s == 1200
    assert budget.hard_caps["metered_usd_micros"] == 0
    assert budget.hard_caps["agent_turns"] == 12
    assert receipt.source_mode == "compiled_campaign_yaml"
    assert receipt.delegated_stop_instruction == (
        "three structurally distinct theories survive size five"
    )


def test_natural_language_low_yield_stop_is_directly_executable():
    compiled = budget_to_user_mapping(budget_preset("standard"))
    compiled["stop"]["low_yield_patience"] = 3
    budget, receipt = compile_budget_preference(
        "Explore for 2 hours and stop after three consecutive low-yield probes.",
        compiler_fn=lambda _text: compiled,
    )
    assert budget.wall_clock_s == 7200
    assert budget.stop_rule.low_yield_patience == 3
    assert receipt.delegated_stop_instruction == ""


def test_campaign_budget_yaml_is_the_inspectable_roundtrip():
    original = budget_preset("smoke_20m")
    text = render_budget_yaml(
        original,
        delegated_stop_instruction="two finalists survive the declared boundary",
    )
    loaded, delegated = load_budget_yaml(text)
    assert loaded.wall_clock_s == original.wall_clock_s
    assert loaded.hard_caps == original.hard_caps
    assert loaded.stop_rule == original.stop_rule
    assert delegated == "two finalists survive the declared boundary"


def test_natural_language_requires_the_injected_campaign_compiler():
    with pytest.raises(ValueError, match="injected budget compiler"):
        compile_budget_preference("work until the theory committee stabilizes")


def test_ledger_reserves_before_commit_and_preserves_boundary_allocation(tmp_path):
    budget = parse_exploration_budget("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl", budget, attempt_id="attempt-1"
    )
    navigation_cap = sum(
        budget.phase_caps[phase]["provider_calls"]
        for phase in ("compilation", "context", "navigation")
    )
    reservation = ledger.reserve(
        "navigator:0", "navigation", {"provider_calls": navigation_cap}
    )
    ledger.commit(reservation)
    with pytest.raises(BudgetExceeded, match="navigation:provider_calls"):
        ledger.reserve("navigator:1", "navigation", {"provider_calls": 1})
    boundary_cap = budget.phase_caps["boundary"]["provider_calls"]
    if boundary_cap:
        boundary = ledger.reserve(
            "boundary:0", "boundary", {"provider_calls": boundary_cap}
        )
        ledger.commit(boundary)
    assert ledger.state()["usage"]["provider_calls"] == navigation_cap + boundary_cap


def test_unused_earlier_capacity_rolls_forward_but_future_boundary_is_protected(tmp_path):
    budget = parse_exploration_budget("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "roll-forward.events.jsonl",
        budget,
        attempt_id="attempt-roll-forward",
    )
    through_navigation = sum(
        budget.phase_caps[phase]["provider_calls"]
        for phase in ("compilation", "context", "navigation")
    )
    reservation = ledger.reserve(
        "navigator:borrow-unused-compilation",
        "navigation",
        {"provider_calls": through_navigation},
    )
    ledger.commit(reservation)
    with pytest.raises(BudgetExceeded, match="navigation:provider_calls"):
        ledger.reserve("navigator:cannot-borrow-future", "navigation", {"provider_calls": 1})
    boundary = ledger.reserve(
        "boundary:protected",
        "boundary",
        {"provider_calls": budget.phase_caps["boundary"]["provider_calls"]},
    )
    ledger.commit(boundary)


def test_authorized_resource_extension_preserves_original_budget_identity(tmp_path):
    budget = parse_exploration_budget("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "extended.events.jsonl", budget, attempt_id="attempt-extended"
    )
    original_digest = budget.digest

    caps = ledger.extend_resources(
        phase="navigation",
        resources={"provider_calls": 3, "agent_turns": 3},
        authority_ref="user:finish-campaign",
        reason="complete the admitted-coordinate discriminator",
    )

    assert budget.digest == original_digest
    assert caps["provider_calls"] == budget.hard_caps["provider_calls"] + 3
    assert ledger.phase_cap("navigation", "provider_calls") == (
        budget.phase_caps["navigation"]["provider_calls"] + 3
    )


def test_disabled_adapter_forge_releases_unreachable_expansion_calls(tmp_path):
    mapping = budget_to_user_mapping(budget_preset("smoke"))
    mapping["budget"]["provider_calls"] = 16
    mapping["budget"]["agent_turns"] = 16
    mapping["budget"]["adapter_forge_attempts"] = 0
    budget = parse_exploration_budget(mapping)
    ledger = ExplorationBudgetLedger(
        tmp_path / "no-forge.events.jsonl",
        budget,
        attempt_id="attempt-no-forge",
    )
    available_navigation = sum(
        budget.phase_caps[phase]["provider_calls"]
        for phase in ("compilation", "context", "navigation", "expansion")
    )
    available_navigation += max(
        0,
        budget.phase_caps["boundary"]["provider_calls"]
        - budget.hard_caps["lean_attempts"],
    )
    reservation = ledger.reserve(
        "navigator:reclaim-disabled-expansion",
        "navigation",
        {"provider_calls": available_navigation},
    )
    ledger.commit(reservation)
    with pytest.raises(BudgetExceeded, match="navigation:provider_calls"):
        ledger.reserve(
            "navigator:boundary-remains-protected",
            "navigation",
            {"provider_calls": 1},
        )
    assert ledger.remaining_capacity("navigation", "provider_calls") == 0


def test_elapsed_cap_blocks_before_action_and_emits_bound_receipt(tmp_path):
    now = [1_000_000]
    mapping = budget_to_user_mapping(budget_preset("smoke"))
    mapping["budget"]["wall_clock"] = "1s"
    budget = parse_exploration_budget(mapping)
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id="attempt-time",
        clock_ms=lambda: now[0],
    )
    now[0] += 1_001
    with pytest.raises(BudgetExceeded, match="wall_clock_s"):
        ledger.reserve("late", "context", {"context_models": 1})
    receipt = ledger.stop_receipt("hard_cap_reached:wall_clock_s")
    assert receipt.elapsed_ms == 1_001
    assert receipt.budget_digest == budget.digest


def test_wall_clock_charges_owned_runtime_not_offline_resume_delay(tmp_path):
    now = [1_000_000]
    budget = budget_preset("smoke")
    ledger = ExplorationBudgetLedger(
        tmp_path / "resume.events.jsonl",
        budget,
        attempt_id="attempt-resume",
        clock_ms=lambda: now[0],
    )
    now[0] += 2_000
    reservation = ledger.reserve("turn:0", "navigation", {"provider_calls": 1})
    now[0] += 3_000
    ledger.commit(reservation)
    ledger.freeze_wall_clock(reason="runner_exit")
    assert ledger.elapsed_ms() == 5_000

    now[0] += 60_000
    assert ledger.elapsed_ms() == 5_000
    ledger.resume_wall_clock()
    now[0] += 4_000
    assert ledger.elapsed_ms() == 9_000
    ledger.freeze_wall_clock(reason="resume_exit")


def test_wall_clock_extension_is_receipted_and_keeps_resource_caps_frozen(tmp_path):
    now = [1_000_000]
    mapping = budget_to_user_mapping(budget_preset("quick"))
    mapping["budget"]["wall_clock"] = "1s"
    budget = parse_exploration_budget(mapping)
    ledger = ExplorationBudgetLedger(
        tmp_path / "extension.events.jsonl",
        budget,
        attempt_id="attempt-extension",
        clock_ms=lambda: now[0],
    )
    now[0] += 2_000
    with pytest.raises(BudgetExceeded, match="wall_clock_s"):
        ledger.reserve("late", "interpretation", {"provider_calls": 1})

    assert ledger.extend_wall_clock(
        extra_s=5,
        authority_ref="user:test",
        reason="finish the frozen post-freeze review",
    ) == budget.wall_clock_s + 5
    reservation = ledger.reserve(
        "review", "interpretation", {"provider_calls": 1}
    )
    ledger.commit(reservation)
    assert ledger.state()["wall_clock_cap_s"] == budget.wall_clock_s + 5
    assert ledger.state()["usage"]["provider_calls"] == 1


def test_interrupted_legacy_clock_recovers_at_last_durable_event(tmp_path):
    now = [1_000_000]
    budget = budget_preset("smoke")
    ledger = ExplorationBudgetLedger(
        tmp_path / "interrupted.events.jsonl",
        budget,
        attempt_id="attempt-interrupted",
        clock_ms=lambda: now[0],
    )
    now[0] += 2_000
    reservation = ledger.reserve("turn:0", "navigation", {"provider_calls": 1})
    now[0] += 3_000
    ledger.commit(reservation)
    now[0] += 60_000

    assert ledger.recover_interrupted_wall_clock() == 5_000
    assert ledger.elapsed_ms() == 5_000


def test_repeated_low_yield_and_coverage_have_distinct_stop_reasons(tmp_path):
    mapping = budget_to_user_mapping(budget_preset("quick"))
    mapping["stop"]["low_yield_patience"] = 2
    mapping["stop"]["min_marginal_information_per_cost"] = "0.1"
    budget = parse_exploration_budget(mapping)
    ledger = ExplorationBudgetLedger(
        tmp_path / "low.events.jsonl", budget, attempt_id="attempt-low"
    )
    for index in range(2):
        ledger.observe_information(
            action_id=f"query:{index}",
            marginal_information_per_cost_ppm=50_000,
            coverage_ppm=100_000,
        )
    assert ledger.soft_stop_reason() == "marginal_yield_below_threshold"

    target = ExplorationBudgetLedger(
        tmp_path / "target.events.jsonl", budget, attempt_id="attempt-target"
    )
    target.observe_information(
        action_id="query:target",
        marginal_information_per_cost_ppm=500_000,
        coverage_ppm=budget.stop_rule.coverage_target_ppm,
    )
    assert target.soft_stop_reason() == "target_reached"
