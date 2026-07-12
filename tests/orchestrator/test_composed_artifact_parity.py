"""Composed-artifact regression net for briefing composition.

Builds the REAL composed prompt/workbench for 4 mode×substrate combos and
asserts structural guarantees. No mocking, no component-level unit checks —
this is the end-to-end artifact the worker actually receives.

Combos:
  1. worldmodel × sealed_completion
  2. worldmodel × visible_workbench
  3. prose-thesis × sealed_completion
  4. prose-thesis × visible_workbench

Tier-0 directives that must survive in every worldmodel briefing:
  - Live Champion mandate (patch base identity)
  - Apparatus Contract Rules (R1 compliance)

Cross-substrate neutrality invariants:
  - prose path: no worldmodel terms in any prompt surface
  - worldmodel path: episode-analysis tools present in DISCOVERY visible_workbench

Visible_workbench parity invariants:
  - live_champion record appears in ATTENTION.md (front-door), not just CONTEXT.md
  - budget trim never drops Tier-0 content
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ztare.common.briefing_pack import (
    BriefingPackRequest,
    _attention_priority,
    _tools_doc,
    build_briefing_pack,
)
from ztare.common.cegis_membrane import DISCOVERY, EVALUATION
from ztare.common.dispatch_model import _compose_agent_prompt
from ztare.orchestrator.mutator_briefing import BriefingContext, MutatorBriefing, BriefingProvider


# ── Worldmodel task sentinel (must trigger worldmodel path) ──────────────────

_WM_TASK = (
    "WORLDMODEL TYPED PAYLOAD CONTRACT: propose a new candidate for test_model.py. "
    "RESUBMIT ONLY ONE RAW JSON OBJECT. Keys: test_model_py, thesis_markdown, "
    "control_receipts. SEALED BOUNDARY-CEGAR. LEAF_WORKBENCH active. "
    "CARRIED RECEIPT FACTS: none. `test_model_py` key required."
)
_PROSE_TASK = "Write a qualitative thesis. Return JSON with thesis_markdown and test_model_py."

# Tier-0 markers that must survive in worldmodel briefings regardless of path/budget
_WM_TIER0 = [
    "## Live Champion",  # live_champion provider
    "## Apparatus Contract Rules",  # contract_rules provider
]

# Terms that must NEVER appear in prose briefings (neutrality invariants)
_WM_BANNED_IN_PROSE = [
    "grid_dsl",
    "WORLD_MODEL_SPEC",
    "step(grid, action, t)",
    "worldmodel_committee",
    "GRAMMAR CEILING",
    "grammar_ceiling",
    "inspect_worldmodel",
    "contrast_worldmodel",
    "run_worldmodel",
    "fit_expression_grammar",
]


# ── Fixtures ─────────────────────────────────────────────────────────────────

class _StaticTier0Provider(BriefingProvider):
    """Injects both Tier-0 headers unconditionally — seeds the briefing body."""
    name = "static_tier0"
    priority = 10
    tier = 0

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return (
            "\n## Live Champion (Patch Base)\n"
            "- MANDATORY: `test_model.py` sha=abc123 is the LIVE CHAMPION.\n"
            "  Preserve its behavior. Modify ONLY where held-out evidence diverges.\n"
            "\n## Apparatus Contract Rules — iter-1 baseline (R1 enforcement)\n"
            "- contract_class: worldmodel\n"
            "- required_carrier: one of WORLD_MODEL_SPEC | PROGRAM | step(grid, action, t)\n"
            "- BANNED: PARAMETRIC_FORM, LAGRANGIAN\n"
        )

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        return [{
            "provider": "live_champion",
            "source_type": "live_champion_receipt",
            "from_ref": "test_model.py",
            "promoted_sha": "abc123",
            "result": "promoted",
            "ts": "20260710T180000",
            "gate_summary_after": {"harness_ok": True, "score": 0.9},
        }]


def _wm_briefing_body(tmp_path: Path) -> str:
    b = MutatorBriefing()
    b.register(_StaticTier0Provider())
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={"fit_expression_grammar": "grid_dsl", "briefing_attention_agenda": False},
    )
    (tmp_path / "workspace").mkdir(exist_ok=True)
    return b.render(ctx)


def _prose_briefing_body(tmp_path: Path) -> str:
    b = MutatorBriefing()
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={"fit_score_mode": "none", "enable_fit_primitive": False, "briefing_attention_agenda": False},
    )
    (tmp_path / "workspace").mkdir(exist_ok=True)
    return b.render(ctx)


# ── Combo 1: worldmodel × sealed_completion ──────────────────────────────────

def test_worldmodel_sealed_tier0_directives_present(tmp_path: Path) -> None:
    """Sealed prompt must carry live champion + contract rules at the front."""
    briefing = _wm_briefing_body(tmp_path)
    sealed = _compose_agent_prompt(_WM_TASK, briefing, execution_mode="sealed_completion")

    for directive in _WM_TIER0:
        assert directive in sealed, (
            f"Tier-0 directive {directive!r} missing from sealed_completion prompt"
        )


def test_worldmodel_sealed_ordering_persona_before_champion(tmp_path: Path) -> None:
    """Persona preamble must appear before the live champion directive."""
    briefing = _wm_briefing_body(tmp_path)
    sealed = _compose_agent_prompt(_WM_TASK, briefing, execution_mode="sealed_completion")

    persona_pos = sealed.find("bounded worker")
    champion_pos = sealed.find("## Live Champion")
    assert persona_pos >= 0, "persona preamble missing from sealed prompt"
    assert champion_pos >= 0, "## Live Champion missing from sealed prompt"
    assert persona_pos < champion_pos, (
        f"persona must precede champion (persona={persona_pos}, champion={champion_pos})"
    )


def test_worldmodel_sealed_no_worldmodel_leaks_in_prose(tmp_path: Path) -> None:
    """Cross-substrate: prose sealed prompt must be clean of worldmodel terms."""
    briefing = _prose_briefing_body(tmp_path)
    sealed = _compose_agent_prompt(_PROSE_TASK, briefing, execution_mode="sealed_completion")

    for banned in _WM_BANNED_IN_PROSE:
        assert banned not in sealed, (
            f"Worldmodel term {banned!r} leaked into prose sealed_completion prompt"
        )


# ── Combo 2: worldmodel × visible_workbench ──────────────────────────────────

def test_worldmodel_visible_workbench_live_champion_in_attention(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Live champion must appear in ATTENTION.md (front door), not only CONTEXT.md."""
    monkeypatch.setenv("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", str(tmp_path / "wb"))
    briefing = _wm_briefing_body(tmp_path)
    ctx_prompt = _compose_agent_prompt(_WM_TASK, briefing, execution_mode="visible_workbench")

    pack = build_briefing_pack(BriefingPackRequest(
        repo=tmp_path,
        agent_id="autoresearch_mutator_test_wm",
        task=_WM_TASK,
        briefing=briefing,
        context=ctx_prompt,
        sealed_boundary_present=False,
        run_role=DISCOVERY,
    ))
    attention = (pack.workbench / "ATTENTION.md").read_text()
    context = (pack.workbench / "CONTEXT.md").read_text()

    # Champion must be surfaced in the front-door file the worker reads FIRST
    assert "live_champion" in attention, (
        "live_champion record missing from ATTENTION.md front door — "
        "surviving_candidates flood may have displaced it"
    )
    # CONTEXT.md is background; it carries the full briefing text
    assert "## Live Champion" in context, "## Live Champion missing from CONTEXT.md"


def test_worldmodel_visible_workbench_tier0_in_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tier-0 content must survive in CONTEXT.md (the full briefing is staged there)."""
    monkeypatch.setenv("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", str(tmp_path / "wb"))
    briefing = _wm_briefing_body(tmp_path)
    ctx_prompt = _compose_agent_prompt(_WM_TASK, briefing, execution_mode="visible_workbench")

    pack = build_briefing_pack(BriefingPackRequest(
        repo=tmp_path,
        agent_id="autoresearch_mutator_test_wm2",
        task=_WM_TASK,
        briefing=briefing,
        context=ctx_prompt,
        sealed_boundary_present=False,
        run_role=DISCOVERY,
    ))
    context = (pack.workbench / "CONTEXT.md").read_text()

    for directive in _WM_TIER0:
        assert directive in context, (
            f"Tier-0 directive {directive!r} missing from CONTEXT.md (budget trim may have dropped it)"
        )


def test_worldmodel_visible_workbench_episode_tools_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Worldmodel DISCOVERY workbench must include episode-analysis tools."""
    monkeypatch.setenv("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", str(tmp_path / "wb"))
    briefing = _wm_briefing_body(tmp_path)
    ctx_prompt = _compose_agent_prompt(_WM_TASK, briefing, execution_mode="visible_workbench")

    pack = build_briefing_pack(BriefingPackRequest(
        repo=tmp_path,
        agent_id="autoresearch_mutator_test_wm3",
        task=_WM_TASK,
        briefing=briefing,
        context=ctx_prompt,
        sealed_boundary_present=False,
        run_role=DISCOVERY,
    ))
    tools = (pack.workbench / "WORKBENCH_TOOLS.md").read_text()

    assert "inspect_worldmodel_event_timeline" in tools, (
        "episode-analysis tool missing from worldmodel DISCOVERY workbench"
    )


# ── Combo 3: prose-thesis × sealed_completion ────────────────────────────────

def test_prose_sealed_no_worldmodel_directives(tmp_path: Path) -> None:
    """Prose sealed prompt must contain no worldmodel directives."""
    briefing = _prose_briefing_body(tmp_path)
    sealed = _compose_agent_prompt(_PROSE_TASK, briefing, execution_mode="sealed_completion")

    for banned in _WM_BANNED_IN_PROSE:
        assert banned not in sealed, (
            f"Worldmodel term {banned!r} leaked into prose sealed_completion prompt"
        )


# ── Combo 4: prose-thesis × visible_workbench ────────────────────────────────

def test_prose_visible_workbench_no_worldmodel_tool_leaks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prose visible_workbench must not expose worldmodel episode-analysis tools."""
    monkeypatch.setenv("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", str(tmp_path / "wb"))
    briefing = _prose_briefing_body(tmp_path)
    ctx_prompt = _compose_agent_prompt(_PROSE_TASK, briefing, execution_mode="visible_workbench")

    pack = build_briefing_pack(BriefingPackRequest(
        repo=tmp_path,
        agent_id="autoresearch_mutator_test_prose",
        task=_PROSE_TASK,
        briefing=briefing,
        context=ctx_prompt,
        sealed_boundary_present=False,
        run_role=DISCOVERY,
    ))
    tools = (pack.workbench / "WORKBENCH_TOOLS.md").read_text()
    context = (pack.workbench / "CONTEXT.md").read_text()
    attention = (pack.workbench / "ATTENTION.md").read_text()

    for banned in _WM_BANNED_IN_PROSE:
        assert banned not in tools, (
            f"Worldmodel term {banned!r} leaked into prose WORKBENCH_TOOLS.md"
        )
        assert banned not in context, (
            f"Worldmodel term {banned!r} leaked into prose CONTEXT.md"
        )
        assert banned not in attention, (
            f"Worldmodel term {banned!r} leaked into prose ATTENTION.md"
        )


def test_prose_visible_workbench_no_episode_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_tools_doc with is_worldmodel=False must omit episode-analysis tools even in DISCOVERY."""
    tools = _tools_doc(run_role=DISCOVERY, is_worldmodel=False)

    assert "inspect_worldmodel" not in tools
    assert "contrast_worldmodel" not in tools
    assert "run_worldmodel" not in tools
    assert "episode jsonl files" not in tools


# ── Attention priority invariants ─────────────────────────────────────────────

def test_live_champion_attention_priority_beats_surviving_candidates() -> None:
    """live_champion record must have lower (=higher-priority) sort key than surviving_candidates."""
    champion_record = {
        "provider": "live_champion",
        "source_type": "live_champion_receipt",
        "from_ref": "test_model.py",
        "promoted_sha": "abc",
    }
    near_miss_record = {
        "provider": "surviving_candidates",
        "source_type": "deterministic_near_miss",
        "record_role": None,
    }
    rejected_record = {
        "provider": "surviving_candidates",
        "source_type": "deterministic_near_miss",
        "record_role": "diagnostic_rejected_witness",
    }
    assert _attention_priority(champion_record) <= _attention_priority(near_miss_record), (
        "live_champion must outrank surviving_candidates near-miss in attention ordering"
    )
    assert _attention_priority(champion_record) <= _attention_priority(rejected_record), (
        "live_champion must outrank diagnostic_rejected_witness in attention ordering"
    )


def test_budget_trim_never_drops_tier0_content(tmp_path: Path) -> None:
    """Tier-0 providers must render even when budget is tight."""

    class HugeTier2Provider(BriefingProvider):
        name = "huge_tier2"
        priority = 50
        tier = 2

        def applies(self, ctx: BriefingContext) -> bool:
            return True

        def fragment(self, ctx: BriefingContext) -> str:
            return "X" * 15000

    b = MutatorBriefing()
    b.register(_StaticTier0Provider())
    b.register(HugeTier2Provider())

    (tmp_path / "workspace").mkdir(exist_ok=True)
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={
            "briefing_budget_chars": 5000,
            "briefing_attention_agenda": False,
        },
    )
    body = b.render(ctx)

    # Tier-0 provider is never gated by budget (tier < 3)
    assert "## Live Champion" in body, "budget trim dropped Tier-0 content"
    assert "## Apparatus Contract Rules" in body, "budget trim dropped Tier-0 content"
