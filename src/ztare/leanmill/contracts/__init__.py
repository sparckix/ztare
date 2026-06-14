"""LeanMill typed contract surfaces.

`kernel` is the pydantic foundation (the world-class convention — typed/validated models + a YAML config
base) that the solver/autoformalizer/governance axes adopt, replacing stringly-typed `dict.get` surfaces
and the older `REQUIRED_*_FIELDS`-tuple validation in the sibling modules. New contracts go here as
pydantic models; the older modules migrate incrementally."""

from ztare.leanmill.contracts.kernel import MoveOutcome, ProofTarget, YamlConfig, primary_result

__all__ = [
    "action_card", "handoff", "learning_feedback", "source_family_match", "source_query",
    "kernel", "ProofTarget", "MoveOutcome", "YamlConfig", "primary_result",
]
