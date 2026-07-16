from __future__ import annotations

import pytest

from ztare.leanmill.exploration_budget import budget_preset
from ztare.leanmill.frontier_campaign_definition import (
    FrontierCampaignDefinition,
    load_frontier_campaign_definition,
)


def test_campaign_yaml_roundtrips_direction_budget_stop_and_runtime():
    definition = FrontierCampaignDefinition(
        direction="Explore compact anonymous theories of reversible finite updates.",
        source_mode="human_directed",
        requested_mode="anonymous_signature_census",
        budget=budget_preset("smoke"),
        delegated_stop_instruction="two structurally distinct finalists survive size five",
        runtime={
            "transport": "subscription_agent_runtime",
            "profile": "smoke",
            "role_overrides": {
                "navigator": {
                    "runtime": "codex",
                    "model": "gpt-5.5",
                    "reasoning_effort": "low",
                    "timeout_seconds": 1200,
                }
            },
        },
        frozen_context_ref={
            "path": "/tmp/context.json",
            "context_hash": "sha256:context",
            "snapshot_sha256": "sha256:snapshot",
        },
    )
    loaded = load_frontier_campaign_definition(definition.to_yaml())
    assert loaded.definition_id == definition.definition_id
    assert loaded.budget.wall_clock_s == 1200
    assert loaded.delegated_stop_instruction == definition.delegated_stop_instruction
    assert loaded.runtime["transport"] == "subscription_agent_runtime"
    assert loaded.frozen_context_ref == definition.frozen_context_ref
    assert loaded.to_brief().resource_envelope["campaign_definition_id"] == definition.definition_id


def test_campaign_yaml_rejects_a_parallel_model_transport():
    with pytest.raises(ValueError, match="subscription_agent_runtime"):
        FrontierCampaignDefinition(
            direction="Explore.",
            source_mode="human_directed",
            budget=budget_preset("quick"),
            runtime={
                "transport": "new_custom_transport",
                "profile": "default",
                "role_overrides": {},
            },
        )


def test_campaign_yaml_rejects_stringly_typed_runtime_flags():
    with pytest.raises(ValueError, match="requires boolean governed_pool"):
        FrontierCampaignDefinition(
            direction="Explore.",
            source_mode="human_directed",
            budget=budget_preset("quick"),
            runtime={
                "transport": "subscription_agent_runtime",
                "profile": "default",
                "role_overrides": {
                    "lean_solver": {"governed_pool": "false"},
                },
            },
        )


def test_axiompack_formal_task_roles_are_valid_runtime_overrides():
    definition = FrontierCampaignDefinition(
        direction="Adjudicate an agent-authored theory task.",
        source_mode="human_directed",
        budget=budget_preset("quick"),
        runtime={
            "transport": "subscription_agent_runtime",
            "profile": "frontier",
            "role_overrides": {
                "formalizer": {
                    "runtime": "codex",
                    "model": "gpt-5.5",
                    "reasoning_effort": "high",
                },
                "faithfulness_reviewer": {
                    "runtime": "codex",
                    "model": "gpt-5.4-mini",
                    "reasoning_effort": "medium",
                },
            },
        },
    )
    assert set(definition.runtime["role_overrides"]) == {
        "formalizer", "faithfulness_reviewer"
    }


def test_minimal_mathematician_campaign_expands_named_profile():
    loaded = load_frontier_campaign_definition(
        """\
schema: leanmill.frontier_campaign_definition.v1
direction: Explore anonymous finite reversible update theories.
source_mode: human_directed
profile: smoke
"""
    )
    assert loaded.budget.wall_clock_s == 1200
    assert loaded.budget.preset == "smoke_20m+yaml"
    assert loaded.runtime == {
        "transport": "subscription_agent_runtime",
        "profile": "default",
        "role_overrides": {},
    }
    materialized = loaded.to_yaml()
    assert "wall_clock: 20m" in materialized
    assert "provider_calls:" in materialized
    assert "allocation_policy: roll_forward_protected_future" in materialized
