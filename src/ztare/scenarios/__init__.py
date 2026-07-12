"""ZTARE Scenarios — the composable use-case layer.

A **Scenario** is a declarative, named bundle (`scenarios/<name>.yaml`) that binds the reasoning kernel to a
use-case: which rubric drives the judge, run config, an optional gate-package, and the declared extension
surface (goal-type / solvers / evidence / renderer). Scenarios COMPOSE existing kernel capabilities; they are
the modular "plug new things" seam over the (already data-pluggable) rubrics/roles/personas/primitives.

Public API:
  * `load_scenario(name)` / `list_scenarios()` — discover + load manifests (filesystem is the registry).
  * `apply_scenario_to_args(name, args)` — the one engine-side binding call (CLI flags win over the scenario).
  * `build_cage_factory(package, base)` — append a scenario's gate-package to the Cage (opt-in).
"""
from ztare.scenarios.config import ScenarioConfig
from ztare.scenarios.loader import list_scenarios, load_scenario, scenario_path
from ztare.scenarios.protocols import EvidenceProvider, Renderer, Solver
from ztare.scenarios.resolver import (
    ScenarioResolution,
    apply_scenario_to_args,
    build_cage_factory,
    resolve_capabilities,
)
from ztare.scenarios import registry

__all__ = [
    # composition
    "ScenarioConfig",
    "load_scenario",
    "list_scenarios",
    "scenario_path",
    "apply_scenario_to_args",
    "resolve_capabilities",
    "build_cage_factory",
    "ScenarioResolution",
    # typed capability contracts + registry
    "EvidenceProvider",
    "Renderer",
    "Solver",
    "registry",
]
