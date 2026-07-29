"""One human-authored campaign envelope for every LeanMill lane."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from ztare.common.llm_runtime import NORMALIZED_REASONING_EFFORTS
from ztare.leanmill.exploration_budget import (
    USER_BUDGET_SCHEMA,
    ExplorationBudget,
    budget_from_user_mapping,
)
from ztare.leanmill.frontier_campaign_definition import (
    FRONTIER_RUNTIME_ROLES,
    FrontierCampaignDefinition,
)
from ztare.leanmill.theory_ir import content_hash


CAMPAIGN_MANIFEST_SCHEMA = "leanmill.campaign.v1"
CAMPAIGN_LANES = frozenset({"formalize", "axiompack"})
_COMMON_FIELDS = {
    "schema",
    "lane",
    "profile",
    "budget",
    "stop",
    "runtime",
    "created_by",
}
_AXIOMPACK_FIELDS = {
    "source_mode",
    "requested_mode",
    "evidence_refs",
    "deanchoring_intent",
    "forbidden_shortcuts",
    "frozen_context_ref",
    "typed_blueprint",
    "predecessor_synthesis_ref",
}
_FORMALIZE_ROLES = {"formalizer", "faithfulness_reviewer", "lean_solver"}
_AXIOMPACK_ROLES = set(FRONTIER_RUNTIME_ROLES)
_RUNTIME_FIELDS = {
    "runtime",
    "model",
    "reasoning_effort",
    "timeout_seconds",
    "visible_workbench",
    "governed_pool",
    "allow_subscription_failover",
}


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("LeanMill campaign frontmatter is not closed") from exc
    parsed = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(parsed, Mapping):
        raise ValueError("LeanMill campaign frontmatter must be a mapping")
    return dict(parsed), "\n".join(lines[end + 1 :]).strip() + "\n"


def _validate_runtime(runtime: Mapping[str, Any], lane: str) -> None:
    if set(runtime) - {"transport", "profile", "defaults", "role_overrides"}:
        raise ValueError("campaign runtime contains unknown fields")
    roles = _FORMALIZE_ROLES if lane == "formalize" else _AXIOMPACK_ROLES
    overrides = runtime.get("role_overrides") or {}
    if not isinstance(overrides, Mapping) or set(overrides) - roles:
        raise ValueError(f"campaign runtime contains unknown {lane} roles")
    rows = [runtime.get("defaults") or {}, *overrides.values()]
    for row in rows:
        if not isinstance(row, Mapping) or set(row) - _RUNTIME_FIELDS:
            raise ValueError("campaign runtime role config contains unknown fields")
        if "runtime" in row and row["runtime"] not in {"codex", "claude"}:
            raise ValueError("campaign runtime must be codex or claude")
        if (
            "reasoning_effort" in row
            and row["reasoning_effort"] not in NORMALIZED_REASONING_EFFORTS
        ):
            raise ValueError("campaign runtime has invalid reasoning effort")
        for flag in (
            "visible_workbench",
            "governed_pool",
            "allow_subscription_failover",
        ):
            if flag in row and type(row[flag]) is not bool:
                raise ValueError(f"campaign runtime requires boolean {flag}")


@dataclass(frozen=True)
class LeanMillCampaignManifest:
    source_path: Path
    source_sha256: str
    body: str
    lane: str
    budget: ExplorationBudget
    delegated_stop_instruction: str
    runtime: Mapping[str, Any]
    metadata: Mapping[str, Any]
    explicit_envelope: bool = False
    schema: str = CAMPAIGN_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CAMPAIGN_MANIFEST_SCHEMA or self.lane not in CAMPAIGN_LANES:
            raise ValueError("invalid LeanMill campaign manifest")
        if not self.body.strip():
            raise ValueError("LeanMill campaign body is empty")
        if self.runtime.get("transport") != "subscription_agent_runtime":
            raise ValueError("LeanMill campaign model work must use subscription_agent_runtime")

    @property
    def campaign_id(self) -> str:
        return "leanmill-campaign:" + content_hash(self.to_json(include_id=False))

    @property
    def typed_blueprint_path(self) -> Path | None:
        value = str(self.metadata.get("typed_blueprint") or "").strip()
        if not value:
            return None
        path = Path(value)
        return path if path.is_absolute() else self.source_path.parent / path

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "lane": self.lane,
            "body_sha256": content_hash({"body": self.body}),
            "budget": self.budget.to_json(),
            "delegated_stop_instruction": self.delegated_stop_instruction,
            "runtime": dict(self.runtime),
            "metadata": dict(self.metadata),
            "explicit_envelope": self.explicit_envelope,
        }
        return {**core, "campaign_id": self.campaign_id} if include_id else core

    def to_frontier_definition(self) -> FrontierCampaignDefinition:
        if self.lane != "axiompack":
            raise ValueError("only an AxiomPack campaign has a frontier definition")
        return FrontierCampaignDefinition(
            direction=self.body.strip(),
            source_mode=str(self.metadata.get("source_mode") or "human_directed"),
            requested_mode=str(self.metadata.get("requested_mode") or ""),
            evidence_refs=tuple(str(row) for row in self.metadata.get("evidence_refs") or ()),
            deanchoring_intent=str(
                self.metadata.get("deanchoring_intent")
                or "cold_after_signature_compilation"
            ),
            forbidden_shortcuts=tuple(
                str(row) for row in self.metadata.get("forbidden_shortcuts") or ()
            ),
            created_by=str(self.metadata.get("created_by") or "user"),
            budget=self.budget,
            delegated_stop_instruction=self.delegated_stop_instruction,
            runtime=dict(self.runtime),
            frozen_context_ref=(
                {str(key): str(value) for key, value in dict(
                    self.metadata.get("frozen_context_ref") or {}
                ).items()}
                if self.metadata.get("frozen_context_ref") is not None
                else None
            ),
            predecessor_synthesis_ref=(
                {str(key): str(value) for key, value in dict(
                    self.metadata.get("predecessor_synthesis_ref") or {}
                ).items()}
                if self.metadata.get("predecessor_synthesis_ref") is not None
                else None
            ),
        )


def formalize_campaign_admission(manifest: LeanMillCampaignManifest) -> dict[str, Any]:
    """Check that a formalization blueprint's input mode matches its body.

    The notes lane is either human-decomposed (an explicit Lemmas section) or
    planner-decomposed. A document that says the planner owns the split while
    also supplying a hand split is an identity conflict: it silently changes
    the campaign from discovery to replay. Reject that before any provider
    reservation; other lint findings remain advisory.
    """
    if manifest.lane != "formalize":
        return {"status": "not_applicable", "blocking": [], "warnings": []}
    body = manifest.body
    has_lemmas = bool(re.search(r"(?mi)^##\s*Lemmas\s*$", body))
    planner_claim = bool(re.search(
        r"(?is)(?:agent|planner).{0,180}(?:decompos|generat(?:e|es|ing)|owns?\s+the\s+(?:formalization|breakdown|split))"
        r"|(?:do\s+not|don't)\s+(?:hand[- ]?write|write|seed).{0,100}(?:lemma|decompos|breakdown)",
        body,
    ))
    blocking: list[str] = []
    if has_lemmas and planner_claim:
        blocking.append(
            "blueprint_identity_conflict: body delegates decomposition to the planner "
            "but also supplies an explicit Lemmas section"
        )
    warnings: list[str] = []
    if not re.search(r"(?mi)^##\s*Target\s*$", body):
        warnings.append("missing_target_section: notes-only lemma campaigns are allowed")
    return {
        "status": "rejected" if blocking else "admissible",
        "blocking": blocking,
        "warnings": warnings,
        "has_target": bool(re.search(r"(?mi)^##\s*Target\s*$", body)),
        "has_lemmas": has_lemmas,
        "planner_claim": planner_claim,
    }


def load_campaign_manifest(
    path: str | Path,
    *,
    profile_override: str = "",
) -> LeanMillCampaignManifest:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    metadata, body = _frontmatter(text)
    if metadata and metadata.get("schema") not in {None, CAMPAIGN_MANIFEST_SCHEMA}:
        raise ValueError("unsupported LeanMill campaign frontmatter schema")
    lane = str(metadata.get("lane") or "formalize")
    if lane not in CAMPAIGN_LANES:
        raise ValueError(f"unknown LeanMill campaign lane: {lane!r}")
    allowed = _COMMON_FIELDS | (_AXIOMPACK_FIELDS if lane == "axiompack" else set())
    unknown = set(metadata) - allowed
    if unknown:
        raise ValueError(f"unknown {lane} campaign fields: {sorted(unknown)}")
    runtime = dict(
        metadata.get("runtime")
        or {
            "transport": "subscription_agent_runtime",
            "profile": "default",
            "role_overrides": {},
        }
    )
    if runtime.get("transport") != "subscription_agent_runtime":
        raise ValueError("LeanMill campaign model work must use subscription_agent_runtime")
    _validate_runtime(runtime, lane)
    profile = str(profile_override or metadata.get("profile") or "default")
    budget, delegated = budget_from_user_mapping(
        {
            "schema": USER_BUDGET_SCHEMA,
            "preset": profile,
            "allocation_policy": "roll_forward_protected_future",
            "budget": metadata.get("budget"),
            "stop": metadata.get("stop") or {},
        }
    )
    if lane == "formalize":
        # Formalization has no AdapterForge job.  Removing that unreachable
        # allocation lets statement/review work roll forward while the
        # existing policy still protects the declared Lean boundary slice.
        hard_caps = dict(budget.hard_caps)
        phase_caps = {phase: dict(caps) for phase, caps in budget.phase_caps.items()}
        hard_caps["adapter_forge_attempts"] = 0
        phase_caps["expansion"]["adapter_forge_attempts"] = 0
        budget = replace(budget, hard_caps=hard_caps, phase_caps=phase_caps)
    return LeanMillCampaignManifest(
        source_path=source,
        source_sha256=content_hash({"source": text}),
        body=body,
        lane=lane,
        budget=budget,
        delegated_stop_instruction=delegated,
        runtime=runtime,
        metadata={**metadata, "profile": profile},
        explicit_envelope=bool(metadata),
    )


__all__ = [
    "CAMPAIGN_LANES",
    "CAMPAIGN_MANIFEST_SCHEMA",
    "LeanMillCampaignManifest",
    "formalize_campaign_admission",
    "load_campaign_manifest",
]
