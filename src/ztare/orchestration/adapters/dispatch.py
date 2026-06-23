"""GP-070 Dispatch Engine — Slice B (C-1, C-3, C-10, C-19).

Routes stage `dispatch` targets to executors. Each adapter is a pure
callable that returns StageResult (C-1, C-3). The orchestrator applies
all transitions — adapters never mutate goal_state directly.

Adapters:
  operator_manual  — no-op, operator advances via CLI/UI
  agent            — prints instruction for Claude Code / Codex
  autoresearch     — builds launch command for autoresearch_loop
  findings_runner  — builds launch command for findings_runner
  program_autoloop — builds launch command for program_autoloop
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

from ztare.orchestration.core import GoalConfig, GoalState, StageDefinition, StageResult

Adapter = Callable[[GoalState, StageDefinition, GoalConfig], StageResult]


# ---------------------------------------------------------------------------
# Adapters — pure callables returning StageResult (C-1, C-3)
# ---------------------------------------------------------------------------

def operator_manual(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> StageResult:
    return StageResult(success=True)


def agent(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> StageResult:
    return StageResult(success=True)


def autoresearch(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> StageResult:
    project_dir = _find_project_dir(state)
    if project_dir is None:
        return StageResult(success=False)
    rubric = _find_rubric(state, project_dir)
    if rubric is None:
        return StageResult(success=False)
    return StageResult(success=True, artifacts=[str(project_dir), str(rubric)])


def findings_runner(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> StageResult:
    return StageResult(success=True)


def program_autoloop(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> StageResult:
    return StageResult(success=True)


# ---------------------------------------------------------------------------
# Registry (C-10)
# ---------------------------------------------------------------------------

ADAPTER_REGISTRY: dict[str, Adapter] = {
    "operator_manual": operator_manual,
    "agent": agent,
    "autoresearch": autoresearch,
    "findings_runner": findings_runner,
    "program_autoloop": program_autoloop,
}


def dispatch(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> StageResult:
    adapter = ADAPTER_REGISTRY.get(stage.dispatch)
    if adapter is None:
        return StageResult(success=False)
    return adapter(state, stage, config)


def stage_guidance(
    state: GoalState, stage: StageDefinition, config: GoalConfig,
) -> str:
    """Return human-readable guidance for what to do at this stage."""
    target = stage.dispatch
    slug = state.slug
    name = stage.name
    desc = stage.description.strip()[:200]

    if target == "operator_manual":
        if stage.is_gate:
            return (
                f"GATE: {name}\n"
                f"  {stage.gate_description.strip()[:200]}\n"
                f"  Action: review, then resume:\n"
                f"    python -m src.ztare.orchestration.cli resume {slug}"
            )
        return (
            f"OPERATOR: {name}\n"
            f"  {desc}\n"
            f"  Action: complete the work, then advance:\n"
            f"    python -m src.ztare.orchestration.cli advance {slug}"
        )

    if target == "agent":
        return (
            f"AGENT: {name}\n"
            f"  {desc}\n"
            f"  Action: Claude Code / Codex completes this stage, then:\n"
            f"    python -m src.ztare.orchestration.cli advance {slug}"
        )

    if target == "autoresearch":
        project_dir = _find_project_dir(state)
        rubric = _find_rubric(state, project_dir) if project_dir else None
        if project_dir and rubric:
            cmd = (
                f"python -m src.ztare.validator.autoresearch_loop "
                f"--project {project_dir} --rubric {rubric} "
                f"--iters 10 --disable_attacker_tools"
            )
            return (
                f"AUTORESEARCH: {name}\n"
                f"  {desc}\n"
                f"  Launch:\n    {cmd}\n"
                f"  When complete, advance:\n"
                f"    python -m src.ztare.orchestration.cli advance {slug}"
            )
        return (
            f"AUTORESEARCH: {name}\n"
            f"  {desc}\n"
            f"  ERROR: project dir or rubric not found for {slug}"
        )

    if target == "findings_runner":
        return (
            f"FINDINGS RUNNER: {name}\n"
            f"  {desc}\n"
            f"  Action: run the debate via findings_runner, then advance:\n"
            f"    python -m src.ztare.orchestration.cli advance {slug}"
        )

    if target == "program_autoloop":
        return (
            f"PROGRAM AUTOLOOP: {name}\n"
            f"  {desc}\n"
            f"  Action: run the program loop, then advance:\n"
            f"    python -m src.ztare.orchestration.cli advance {slug}"
        )

    return f"{name}: unknown dispatch target '{target}'"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_project_dir(state: GoalState) -> Optional[Path]:
    slug = state.slug
    candidates = [
        Path(f"projects/{slug}"),
        Path(f"projects/{slug.replace('_blind_path_b', '')}"),
    ]
    import re
    gp_match = re.search(r"gp[_-]?(\d+)", slug, re.IGNORECASE)
    if gp_match:
        gp_num = gp_match.group(1)
        for p in sorted(Path("projects").iterdir()):
            if p.is_dir() and gp_num in p.name:
                candidates.append(p)
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


def _find_rubric(state: GoalState, project_dir: Optional[Path]) -> Optional[Path]:
    if project_dir is None:
        return None
    name = project_dir.name
    for candidate in [
        Path(f"rubrics/{name}.json"),
        Path(f"rubrics/{state.slug}.json"),
    ]:
        if candidate.exists():
            return candidate
    for r in Path("rubrics").glob("*.json"):
        if name in r.stem:
            return r
    return None
