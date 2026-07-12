from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ztare.leanmill.exploration_budget import budget_preset
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition


_PATH = Path(__file__).parents[1] / "scripts/public/control/leanmill/frontier_axiom_campaign.py"
_SPEC = importlib.util.spec_from_file_location("frontier_axiom_campaign", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
campaign = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(campaign)


def test_small_campaign_build_and_replay_are_provider_free(tmp_path):
    directory = campaign.build_campaign(
        output_root=tmp_path,
        max_order=2,
        carrier_sizes=(2,),
        max_finalists=3,
    )
    result = campaign.read_json(directory / "result.json", {})
    assert result["provider_calls"] == 0
    assert result["formula_count"] == 46
    assert result["navigation"]["finalist_node_ids"]
    replay = campaign.replay_campaign(directory)
    assert replay["ok"] is True
    assert replay["provider_calls"] == 0


def test_prepare_cli_normalizes_one_campaign_yaml_without_provider(tmp_path, capsys):
    source = tmp_path / "campaign.yaml"
    prepared = tmp_path / "prepared.yaml"
    source.write_text(
        FrontierCampaignDefinition(
            direction="Explore anonymous short laws.",
            source_mode="human_directed",
            budget=budget_preset("smoke"),
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
        ).to_yaml(),
        encoding="utf-8",
    )
    assert campaign.main([
        "prepare",
        "--campaign-yaml", str(source),
        "--output", str(prepared),
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "campaign_definition_prepared_awaiting_run_approval"
    assert prepared.is_file()
    assert "subscription_agent_runtime" in prepared.read_text(encoding="utf-8")
