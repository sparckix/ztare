"""Discover + load Scenario manifests from `scenarios/*.yaml`. The directory IS the registry (a new scenario
is a dropped file, no core edit) — the same filesystem-scan pattern the repo already uses for roles (YAML),
personas (MD) and primitives (JSON)."""
from __future__ import annotations

from pathlib import Path

from ztare.common.paths import SCENARIOS_DIR
from ztare.scenarios.config import ScenarioConfig


def scenario_path(name: str) -> Path:
    return SCENARIOS_DIR / f"{name}.yaml"


def list_scenarios() -> "list[str]":
    if not SCENARIOS_DIR.exists():
        return []
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.yaml"))


def load_scenario(name: str) -> ScenarioConfig:
    """Load + validate `scenarios/<name>.yaml` into a typed ScenarioConfig.

    Raises FileNotFoundError if the named scenario isn't on disk — a named selection that doesn't exist is a
    caller error (unlike an optional tuning file), and failing loud beats silently running an empty scenario.
    A malformed field raises pydantic ValidationError (fail loud). Backfills `.name` from the filename when the
    YAML omits it."""
    p = scenario_path(name)
    if not p.exists():
        avail = ", ".join(list_scenarios()) or "(none)"
        raise FileNotFoundError(f"scenario '{name}' not found at {p} — available: {avail}")
    sc = ScenarioConfig.load(p)
    if not sc.name:
        sc.name = name
    return sc
