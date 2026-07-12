"""Named campaign shapes shared by LeanMill formalization and AxiomPack."""
from __future__ import annotations

import os
from typing import Mapping


AUTOFORMALIZE_CAMPAIGN_PROFILES: dict[str, dict[str, str]] = {
    "default": {},
    "smoke": {
        "ZTARE_LEANMILL_DISPATCH_S": "300",
        "ZTARE_LEANMILL_AGENT_IDLE_S": "300",
        "ZTARE_LEANMILL_NOTES_LEMMA_S": "600",
        "ZTARE_LEANMILL_NOTES_TARGET_S": "600",
        "ZTARE_LEANMILL_CAMPAIGN_WALL_S": "1200",
    },
    "hard": {
        "ZTARE_LEANMILL_DISPATCH_S": "1800",
        "ZTARE_LEANMILL_AGENT_IDLE_S": "1800",
        "ZTARE_LEANMILL_NOTES_LEMMA_S": "3600",
        "ZTARE_LEANMILL_NOTES_TARGET_S": "3600",
        "ZTARE_LEANMILL_CAMPAIGN_WALL_S": "21600",
    },
}

FRONTIER_BUDGET_PROFILE_TO_PRESET: dict[str, str] = {
    "default": "standard",
    "smoke": "smoke_20m",
    "hard": "deep",
    "overnight": "overnight",
    "local_only": "local_only",
    "quick": "quick",
    "standard": "standard",
    "deep": "deep",
    "smoke_20m": "smoke_20m",
}


def apply_autoformalize_campaign_profile(
    name: str,
    *,
    environment: dict[str, str] | None = None,
) -> Mapping[str, str]:
    try:
        values = AUTOFORMALIZE_CAMPAIGN_PROFILES[str(name)]
    except KeyError as exc:
        raise ValueError(f"unknown LeanMill campaign profile: {name!r}") from exc
    target = os.environ if environment is None else environment
    for key, value in values.items():
        target.setdefault(key, value)
    return values


def frontier_budget_preset_for_profile(name: str) -> str:
    try:
        return FRONTIER_BUDGET_PROFILE_TO_PRESET[str(name)]
    except KeyError as exc:
        raise ValueError(f"unknown frontier campaign profile: {name!r}") from exc


__all__ = [
    "AUTOFORMALIZE_CAMPAIGN_PROFILES", "FRONTIER_BUDGET_PROFILE_TO_PRESET",
    "apply_autoformalize_campaign_profile", "frontier_budget_preset_for_profile",
]
