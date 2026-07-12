from __future__ import annotations

from pathlib import Path

import pytest

from ztare.leanmill.campaign_manifest import load_campaign_manifest


def test_legacy_blueprint_is_a_formalization_campaign(tmp_path: Path):
    path = tmp_path / "theorem.md"
    path.write_text("## Target\nProve the target.\n", encoding="utf-8")
    campaign = load_campaign_manifest(path)
    assert campaign.lane == "formalize"
    assert campaign.body.startswith("## Target")
    assert campaign.budget.allocation_policy == "global_cap"
    assert campaign.budget.wall_clock_s == 7200
    assert campaign.source_path == path
    assert campaign.explicit_envelope is False


def test_frontmatter_gives_both_lanes_the_same_budget_envelope(tmp_path: Path):
    path = tmp_path / "frontier.md"
    path.write_text(
        """---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke
source_mode: human_directed
budget:
  metered_api_usd: "0"
stop:
  low_yield_patience: 4
runtime:
  transport: subscription_agent_runtime
  profile: smoke
  role_overrides: {}
---
Explore anonymous reversible finite updates without named axiom lists.
""",
        encoding="utf-8",
    )
    campaign = load_campaign_manifest(path)
    assert campaign.lane == "axiompack"
    assert campaign.explicit_envelope is True
    assert campaign.budget.wall_clock_s == 1200
    assert campaign.budget.hard_caps["metered_usd_micros"] == 0
    assert campaign.budget.stop_rule.low_yield_patience == 4
    assert campaign.budget.allocation_policy == "roll_forward_protected_future"
    definition = campaign.to_frontier_definition()
    assert definition.direction.startswith("Explore anonymous")
    assert definition.budget.digest == campaign.budget.digest


def test_structure_first_typed_blueprint_path_is_relative_to_campaign(tmp_path: Path):
    typed = tmp_path / "typed.json"
    typed.write_text("{}", encoding="utf-8")
    path = tmp_path / "frontier.md"
    path.write_text(
        """---
schema: leanmill.campaign.v1
lane: axiompack
source_mode: structure_first
typed_blueprint: typed.json
---
Explore the frozen structure.
""",
        encoding="utf-8",
    )
    assert load_campaign_manifest(path).typed_blueprint_path == typed


def test_lane_specific_unknown_frontmatter_fails_closed(tmp_path: Path):
    path = tmp_path / "bad.md"
    path.write_text(
        """---
schema: leanmill.campaign.v1
lane: formalize
typed_blueprint: should-not-apply.json
---
## Target
Something.
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown formalize campaign fields"):
        load_campaign_manifest(path)
