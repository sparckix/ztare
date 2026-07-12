"""Inspectable YAML definition for one frontier AxiomPack campaign."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.llm_runtime import NORMALIZED_REASONING_EFFORTS
from ztare.leanmill.exploration_budget import (
    USER_BUDGET_SCHEMA,
    ExplorationBudget,
    budget_from_user_mapping,
    budget_to_user_mapping,
)
from ztare.leanmill.frontier_blueprint import CAMPAIGN_MODES, SOURCE_MODES, FrontierExplorationBrief
from ztare.leanmill.theory_ir import content_hash


CAMPAIGN_DEFINITION_SCHEMA = "leanmill.frontier_campaign_definition.v1"
_RUNTIME_ROLES = frozenset(
    {
        "budget_compiler",
        "blueprint_compiler",
        "semantic_reviewer",
        "navigator",
        "lineage_synthesizer",
        "adapter_forge",
        "adapter_reviewer",
        "lean_solver",
        "post_freeze_interpreter",
    }
)


@dataclass(frozen=True)
class FrontierCampaignDefinition:
    direction: str
    source_mode: str
    budget: ExplorationBudget
    delegated_stop_instruction: str = ""
    requested_mode: str = ""
    evidence_refs: tuple[str, ...] = ()
    deanchoring_intent: str = "cold_after_signature_compilation"
    forbidden_shortcuts: tuple[str, ...] = ()
    created_by: str = "user"
    runtime: Mapping[str, Any] = field(
        default_factory=lambda: {
            "transport": "subscription_agent_runtime",
            "profile": "default",
            "role_overrides": {},
        }
    )
    frozen_context_ref: Mapping[str, str] | None = None
    predecessor_synthesis_ref: Mapping[str, str] | None = None
    schema: str = CAMPAIGN_DEFINITION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CAMPAIGN_DEFINITION_SCHEMA:
            raise ValueError("unsupported frontier campaign definition schema")
        if not self.direction.strip() or self.source_mode not in SOURCE_MODES:
            raise ValueError("campaign direction and source mode are required")
        if self.requested_mode and self.requested_mode not in CAMPAIGN_MODES:
            raise ValueError("unsupported requested campaign mode")
        if self.runtime.get("transport") != "subscription_agent_runtime":
            raise ValueError("frontier campaign model work must use subscription_agent_runtime")
        overrides = self.runtime.get("role_overrides") or {}
        if not isinstance(overrides, Mapping) or set(overrides) - _RUNTIME_ROLES:
            raise ValueError("campaign runtime contains unknown role overrides")
        for role, config in overrides.items():
            if not isinstance(config, Mapping):
                raise ValueError(f"runtime override for {role} must be a mapping")
            if "runtime" in config and config["runtime"] not in {"codex", "claude"}:
                raise ValueError(f"runtime override for {role} has unsupported runtime")
            if "model" in config and not str(config["model"]).strip():
                raise ValueError(f"runtime override for {role} has empty model")
            if (
                "reasoning_effort" in config
                and config["reasoning_effort"] not in NORMALIZED_REASONING_EFFORTS
            ):
                raise ValueError(f"runtime override for {role} has invalid reasoning effort")
            if "timeout_seconds" in config and (
                type(config["timeout_seconds"]) is not int or config["timeout_seconds"] < 1
            ):
                raise ValueError(f"runtime override for {role} has invalid timeout")
            for flag in (
                "visible_workbench",
                "governed_pool",
                "allow_subscription_failover",
            ):
                if flag in config and type(config[flag]) is not bool:
                    raise ValueError(
                        f"runtime override for {role} requires boolean {flag}"
                    )
        if self.frozen_context_ref is not None:
            required = {"path", "context_hash", "snapshot_sha256"}
            if required - set(self.frozen_context_ref):
                raise ValueError("frozen context reference is incomplete")
            if any(not str(self.frozen_context_ref[key]).strip() for key in required):
                raise ValueError("frozen context reference values must be non-empty")
        if self.predecessor_synthesis_ref is not None:
            required = {"path", "input_sha256"}
            if required - set(self.predecessor_synthesis_ref):
                raise ValueError("predecessor synthesis reference is incomplete")
            if any(
                not str(self.predecessor_synthesis_ref[key]).strip()
                for key in required
            ):
                raise ValueError("predecessor synthesis reference values must be non-empty")

    @property
    def definition_id(self) -> str:
        return "frontier-campaign-definition:" + content_hash(self.to_json(include_id=False))

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        budget_doc = budget_to_user_mapping(
            self.budget,
            delegated_stop_instruction=self.delegated_stop_instruction,
        )
        core = {
            "schema": self.schema,
            "direction": self.direction,
            "source_mode": self.source_mode,
            "requested_mode": self.requested_mode,
            "evidence_refs": list(self.evidence_refs),
            "deanchoring_intent": self.deanchoring_intent,
            "forbidden_shortcuts": list(self.forbidden_shortcuts),
            "created_by": self.created_by,
            "profile": budget_doc["preset"],
            "allocation_policy": budget_doc["allocation_policy"],
            "budget": budget_doc["budget"],
            "stop": budget_doc["stop"],
            "runtime": dict(self.runtime),
            "frozen_context_ref": (
                dict(self.frozen_context_ref)
                if self.frozen_context_ref is not None else None
            ),
            "predecessor_synthesis_ref": (
                dict(self.predecessor_synthesis_ref)
                if self.predecessor_synthesis_ref is not None else None
            ),
        }
        return {**core, "definition_id": self.definition_id} if include_id else core

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            self.to_json(include_id=True),
            sort_keys=False,
            default_flow_style=False,
        )

    def to_brief(self) -> FrontierExplorationBrief:
        return FrontierExplorationBrief(
            direction=self.direction,
            source_mode=self.source_mode,
            evidence_refs=self.evidence_refs,
            requested_mode=self.requested_mode,
            deanchoring_intent=self.deanchoring_intent,
            resource_envelope={
                "budget_contract": self.budget.to_json(),
                "delegated_stop_instruction": self.delegated_stop_instruction,
                "campaign_definition_id": self.definition_id,
            },
            forbidden_shortcuts=self.forbidden_shortcuts,
            created_by=self.created_by,
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FrontierCampaignDefinition":
        budget, delegated = budget_from_user_mapping(
            {
                "schema": USER_BUDGET_SCHEMA,
                "preset": value.get("profile", "default"),
                "allocation_policy": value.get("allocation_policy"),
                "budget": value.get("budget"),
                "stop": value.get("stop") or {},
                "model_transport": (value.get("runtime") or {}).get("transport"),
            }
        )
        definition = cls(
            direction=str(value.get("direction") or ""),
            source_mode=str(value.get("source_mode") or "human_directed"),
            requested_mode=str(value.get("requested_mode") or ""),
            evidence_refs=tuple(str(row) for row in value.get("evidence_refs") or ()),
            deanchoring_intent=str(
                value.get("deanchoring_intent") or "cold_after_signature_compilation"
            ),
            forbidden_shortcuts=tuple(
                str(row) for row in value.get("forbidden_shortcuts") or ()
            ),
            created_by=str(value.get("created_by") or "user"),
            budget=budget,
            delegated_stop_instruction=delegated,
            runtime=dict(
                value.get("runtime")
                or {
                    "transport": "subscription_agent_runtime",
                    "profile": "default",
                    "role_overrides": {},
                }
            ),
            frozen_context_ref=(
                {
                    str(key): str(item)
                    for key, item in dict(value.get("frozen_context_ref") or {}).items()
                }
                if value.get("frozen_context_ref") is not None else None
            ),
            predecessor_synthesis_ref=(
                {
                    str(key): str(item)
                    for key, item in dict(
                        value.get("predecessor_synthesis_ref") or {}
                    ).items()
                }
                if value.get("predecessor_synthesis_ref") is not None else None
            ),
            schema=str(value.get("schema") or CAMPAIGN_DEFINITION_SCHEMA),
        )
        supplied = value.get("definition_id")
        if supplied is not None and supplied != definition.definition_id:
            raise ValueError("frontier campaign definition digest mismatch")
        return definition


def load_frontier_campaign_definition(source: str | Path) -> FrontierCampaignDefinition:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    else:
        candidate = Path(source)
        text = (
            candidate.read_text(encoding="utf-8")
            if "\n" not in source and candidate.is_file()
            else source
        )
    parsed = yaml.safe_load(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("frontier campaign YAML must contain one mapping")
    return FrontierCampaignDefinition.from_mapping(parsed)


__all__ = [
    "CAMPAIGN_DEFINITION_SCHEMA", "FrontierCampaignDefinition",
    "load_frontier_campaign_definition",
]
