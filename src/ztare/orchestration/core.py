"""GP-070 Goal Orchestrator — Core state machine.

Implements constraints C-1 through C-4 from the converged spec:
- StageResult return contract (C-1)
- DAG validation with gate-skip prevention (C-2)
- Pure callable contract on adapters (C-3)
- gate_artifacts as pure callable (C-4)
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class GoalStatus(str, Enum):
    ACTIVE = "active"
    GATE_PENDING = "gate_pending"
    CLOSED = "closed"
    CLOSED_NULL = "closed_null"
    CLOSED_ABANDONED = "closed_abandoned"


@dataclass
class StageResult:
    success: bool
    next_stage: Optional[str] = None
    gate_reason: Optional[str] = None
    artifacts: list[str] = field(default_factory=list)


@dataclass
class StageDefinition:
    name: str
    description: str
    is_gate: bool = False
    gate_description: str = ""
    dispatch: str = "agent"
    idempotent: bool = True
    closure_predicate: Optional[dict[str, Any]] = None
    strict_gate_mode: bool = False


@dataclass
class GoalConfig:
    target_type: str
    schema_version: int
    stages: list[StageDefinition]
    entry_stage: str
    terminal_stages: list[str]
    description: str = ""

    def stage_names(self) -> list[str]:
        return [s.name for s in self.stages]

    def stage_by_name(self, name: str) -> Optional[StageDefinition]:
        for s in self.stages:
            if s.name == name:
                return s
        return None

    def stage_index(self, name: str) -> int:
        for i, s in enumerate(self.stages):
            if s.name == name:
                return i
        return -1

    def is_terminal(self, stage: str) -> bool:
        return stage in self.terminal_stages

    def next_stage_default(self, current: str) -> Optional[str]:
        idx = self.stage_index(current)
        if idx < 0 or idx >= len(self.stages) - 1:
            return None
        return self.stages[idx + 1].name


@dataclass
class GoalState:
    name: str
    slug: str
    description: str
    target_type: str
    current_stage: str
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: str = ""
    owner: str = ""
    schema_version: int = 1
    gate_pending_reason: Optional[str] = None
    gate_escalation_hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "target_type": self.target_type,
            "current_stage": self.current_stage,
            "status": self.status.value,
            "created_at": self.created_at,
            "owner": self.owner,
            "schema_version": self.schema_version,
            "gate_pending_reason": self.gate_pending_reason,
            "gate_escalation_hashes": self.gate_escalation_hashes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GoalState:
        return cls(
            name=d["name"],
            slug=d["slug"],
            description=d["description"],
            target_type=d["target_type"],
            current_stage=d["current_stage"],
            status=GoalStatus(d.get("status", "active")),
            created_at=d.get("created_at", ""),
            owner=d.get("owner", ""),
            schema_version=d.get("schema_version", 1),
            gate_pending_reason=d.get("gate_pending_reason"),
            gate_escalation_hashes=d.get("gate_escalation_hashes", {}),
        )

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        config: GoalConfig,
        owner: str = "",
    ) -> GoalState:
        import re as _re
        slug = _re.sub(r"[^a-z0-9_]", "_", name.lower())
        slug = _re.sub(r"_+", "_", slug).strip("_")
        return cls(
            name=name,
            slug=slug,
            description=description,
            target_type=config.target_type,
            current_stage=config.entry_stage,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            owner=owner,
        )


def validate_stage_graph(config: GoalConfig) -> list[str]:
    """Validate the stage DAG at registration time (C-2).

    Returns a list of error strings. Empty list = valid.
    """
    errors: list[str] = []
    names = config.stage_names()

    if not names:
        errors.append("No stages defined.")
        return errors

    if len(names) != len(set(names)):
        errors.append("Duplicate stage names.")

    if config.entry_stage not in names:
        errors.append(f"Entry stage '{config.entry_stage}' not in stage list.")

    if not config.terminal_stages:
        errors.append("No terminal stages defined.")

    for t in config.terminal_stages:
        if t not in names:
            errors.append(f"Terminal stage '{t}' not in stage list.")

    for s in config.stages:
        if s.is_gate and not s.gate_description:
            errors.append(f"Gate stage '{s.name}' has no gate_description.")

    # Acyclicity: stages are an ordered list (linear DAG).
    # next_stage overrides can only move forward, never backward.
    # This is enforced at transition time, not here.

    return errors


def validate_transition(
    config: GoalConfig,
    current_stage: str,
    proposed_next: str,
) -> Optional[str]:
    """Validate a proposed transition against the stage graph (C-2).

    Returns an error string if invalid, None if valid.
    Gate-skip detection: if any gate stage lies between current and
    proposed_next in the ordered stage list, the transition is rejected.
    """
    names = config.stage_names()
    current_idx = config.stage_index(current_stage)
    next_idx = config.stage_index(proposed_next)

    if current_idx < 0:
        return f"Current stage '{current_stage}' not in config."
    if next_idx < 0:
        return f"Proposed stage '{proposed_next}' not in config."
    if next_idx <= current_idx:
        return f"Cannot move backward: '{current_stage}' -> '{proposed_next}'."

    for i in range(current_idx + 1, next_idx):
        if config.stages[i].is_gate:
            return (
                f"Transition skips gate stage '{config.stages[i].name}' "
                f"between '{current_stage}' and '{proposed_next}'."
            )

    return None
