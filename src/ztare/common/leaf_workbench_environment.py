"""Static resolver for substrate-specific leaf workbench environments."""
from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib
from typing import Any


EnvironmentFactory = Callable[..., Mapping[str, Any]]

_STATIC_ENVIRONMENTS = {
    "worldmodel": (
        "ztare.worldmodel.leaf_workbench",
        "worldmodel_leaf_workbench_action_environment",
    ),
    "axiompack": (
        "ztare.leanmill.axiompack_leaf_workbench",
        "axiompack_leaf_workbench_action_environment",
    ),
}


def leaf_workbench_environment_ids() -> tuple[str, ...]:
    return tuple(sorted(_STATIC_ENVIRONMENTS))


def resolve_leaf_workbench_environment(adapter_id: str, **kwargs: Any) -> Mapping[str, Any]:
    """Resolve only a code-registered adapter; no import path comes from input."""
    try:
        module_name, factory_name = _STATIC_ENVIRONMENTS[str(adapter_id)]
    except KeyError as exc:
        raise ValueError(f"unknown leaf workbench adapter: {adapter_id!r}") from exc
    factory = getattr(importlib.import_module(module_name), factory_name)
    environment = factory(**kwargs)
    required = {"contract", "records_fn", "action_handlers", "stateless_actions"}
    missing = required - set(environment)
    if missing:
        raise ValueError(f"leaf workbench environment missing fields: {sorted(missing)}")
    return environment


__all__ = ["leaf_workbench_environment_ids", "resolve_leaf_workbench_environment"]
