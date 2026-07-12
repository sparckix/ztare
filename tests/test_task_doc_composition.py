"""Tests for task-doc / briefing-pack composition defects (5 fixes).

FIX 1: FORMATTING section must not solicit PARAMETRIC_FORM for worldmodel substrates.
FIX 2: OPERATIVE FAILURE block + champion directive appear before axioms in TASK.md.
FIX 3: Prior-thesis section carries the stale-warning header.
FIX 4: Evidence digest appears exactly once across TASK.md + CONTEXT.md combined.
FIX 5: Axiom scope — not tested (no structured range data available; skip noted).
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_worldmodel_task(evidence: str = "ev_data") -> str:
    """Return a base_prompt-style task string as produced by mutate_thesis for a
    worldmodel substrate with bounded_discriminator falsification mode."""
    from ztare.common.briefing_pack import _EVIDENCE_DIGEST_START, _EVIDENCE_DIGEST_END

    return textwrap.dedent(f"""\
        Persona: researcher.

        ---

        ### TASK: Resolve the following Systemic Inconsistency:

        "THIS IS THE WEAKEST LINK: the timer rule is ambiguous"

        ### ⚠️ RECENT FAILURE ANALYSIS
        Gate failed: replay mismatch. Do NOT repeat.

        ## Mutator Briefing
        ## Live Champion
        champion_ref: projects/arc3_ls20_gov/test_model.py
        sha: abc123

        ---

        AXIOMS (PREVIOUSLY VERIFIED TRUTHS):
        - Replay is exact over 48 visible transitions.

        {_EVIDENCE_DIGEST_START}
        GROUNDING DATA (IMMUTABLE CONSTANTS):
        {evidence}
        {_EVIDENCE_DIGEST_END}

        ### PRIOR THESIS (previous iteration — may be stale; the OPERATIVE FAILURE above is authoritative where they conflict)
        [note: substrate declares lawful_time — t-dependence is admissible regardless of prior confirmation]
        Prior thesis content here.

        FORMATTING:
        - MANDATORY: You must provide exactly one Python code block.
        - SUBMISSION FORM: this is a worldmodel/interactive substrate.
          The accepted carriers are:
            step(grid, action, t)
            PROGRAM = [...]
            WORLD_MODEL_SPEC = ...
          PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS, PARAMETER_NAMES, and INIT_RANGE do NOT
          apply here and will be rejected by the R1 gate. Do not declare them.
    """)


def _make_non_worldmodel_task(evidence: str = "ev_data") -> str:
    """Return a base_prompt-style task string for a non-worldmodel substrate."""
    from ztare.common.briefing_pack import _EVIDENCE_DIGEST_START, _EVIDENCE_DIGEST_END

    return textwrap.dedent(f"""\
        Persona: researcher.

        ---

        ### TASK: Resolve the following Systemic Inconsistency:

        "THIS IS THE WEAKEST LINK: variance unexplained"

        ---

        AXIOMS (PREVIOUSLY VERIFIED TRUTHS):
        - Economy obeys conservation laws.

        {_EVIDENCE_DIGEST_START}
        GROUNDING DATA (IMMUTABLE CONSTANTS):
        {evidence}
        {_EVIDENCE_DIGEST_END}

        FORMATTING:
        - MANDATORY: You must provide exactly one Python code block.
        - SUBMISSION FORM: choose one accepted numeric declaration.
          Parametric model declaration:
              declare PARAMETRIC_FORM = "<closed expression in features+params>"
          Variational/Lagrangian declaration:
              declare LAGRANGIAN = "<sympy expression>"
    """)


def _build_pack(tmp_path: Path, task: str, context: str | None = None) -> object:
    """Build a minimal briefing pack. Returns the BriefingPack."""
    from ztare.common.briefing_pack import BriefingPackRequest, build_briefing_pack

    repo = tmp_path / "repo"
    (repo / "projects" / "arc3_ls20_gov" / "workspace").mkdir(parents=True)

    os.environ["ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT"] = str(tmp_path / "workbench")
    try:
        pack = build_briefing_pack(BriefingPackRequest(
            repo=repo,
            agent_id="autoresearch_mutator_arc3_ls20_gov",
            task=task,
            context=context or ("preamble\n\n=== TASK ===\n" + task),
        ))
    finally:
        os.environ.pop("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", None)
    return pack


# ---------------------------------------------------------------------------
# FIX 1: FORMATTING must not solicit PARAMETRIC_FORM for worldmodel substrates
# ---------------------------------------------------------------------------

def test_worldmodel_formatting_excludes_parametric_form(tmp_path: Path) -> None:
    """For a worldmodel task, FORMATTING must NOT solicit PARAMETRIC_FORM or LAGRANGIAN."""
    task = _make_worldmodel_task()
    pack = _build_pack(tmp_path, task)
    task_md = (pack.workbench / "TASK.md").read_text()

    # Worldmodel FORMATTING block should explicitly list step/PROGRAM/WORLD_MODEL_SPEC
    assert "step(grid, action, t)" in task_md or "WORLD_MODEL_SPEC" in task_md

    # The banned parametric solicitation must not appear
    assert "declare PARAMETRIC_FORM" not in task_md, (
        "TASK.md solicits PARAMETRIC_FORM for a worldmodel substrate — "
        "self-contradiction with BANNED:PARAMETRIC_FORM (FIX 1 violated)"
    )
    assert "declare LAGRANGIAN" not in task_md, (
        "TASK.md solicits LAGRANGIAN for a worldmodel substrate — "
        "self-contradiction with BANNED list (FIX 1 violated)"
    )


def test_non_worldmodel_formatting_still_has_parametric_form(tmp_path: Path) -> None:
    """For a non-worldmodel task, PARAMETRIC_FORM solicitation must still be present."""
    task = _make_non_worldmodel_task()
    pack = _build_pack(tmp_path, task)
    task_md = (pack.workbench / "TASK.md").read_text()

    assert "PARAMETRIC_FORM" in task_md, (
        "Non-worldmodel TASK.md should still solicit PARAMETRIC_FORM (FIX 1 must not over-strip)"
    )


# ---------------------------------------------------------------------------
# FIX 2: Operative failure block appears before axioms
# ---------------------------------------------------------------------------

def test_operative_failure_before_axioms(tmp_path: Path) -> None:
    """OPERATIVE FAILURE block (task header + failure) must appear before AXIOMS in TASK.md."""
    task = _make_worldmodel_task()
    pack = _build_pack(tmp_path, task)
    task_md = (pack.workbench / "TASK.md").read_text()

    # Positions of key sections
    failure_pos = task_md.find("RECENT FAILURE ANALYSIS")
    axioms_pos = task_md.find("AXIOMS (PREVIOUSLY VERIFIED TRUTHS)")

    assert failure_pos >= 0, "RECENT FAILURE ANALYSIS block not found in TASK.md"
    assert axioms_pos >= 0, "AXIOMS section not found in TASK.md"
    assert failure_pos < axioms_pos, (
        f"OPERATIVE FAILURE ({failure_pos}) must appear before AXIOMS ({axioms_pos}) "
        "in TASK.md (FIX 2)"
    )


def test_champion_directive_within_first_2500_chars(tmp_path: Path) -> None:
    """Live champion directive must appear within the first ~2500 chars of TASK.md."""
    task = _make_worldmodel_task()
    pack = _build_pack(tmp_path, task)
    task_md = (pack.workbench / "TASK.md").read_text()

    champion_pos = task_md.find("champion_ref")
    assert champion_pos >= 0, "champion_ref not found in TASK.md"
    assert champion_pos < 2500, (
        f"champion_ref appears at char {champion_pos}, expected within first 2500 chars (FIX 2)"
    )


# ---------------------------------------------------------------------------
# FIX 3: Prior-thesis section carries the stale-warning header
# ---------------------------------------------------------------------------

def test_prior_thesis_section_has_stale_warning(tmp_path: Path) -> None:
    """PRIOR THESIS section must carry the stale-warning annotation."""
    task = _make_worldmodel_task()
    pack = _build_pack(tmp_path, task)
    task_md = (pack.workbench / "TASK.md").read_text()

    assert "PRIOR THESIS" in task_md, "PRIOR THESIS heading not found in TASK.md (FIX 3)"
    assert "may be stale" in task_md, (
        "Stale-warning annotation not found in PRIOR THESIS section (FIX 3)"
    )
    assert "OPERATIVE FAILURE above is authoritative" in task_md, (
        "Conflict-resolution note not found in PRIOR THESIS header (FIX 3)"
    )


def test_prior_thesis_has_lawful_time_note(tmp_path: Path) -> None:
    """When substrate declares lawful_time, the prior-thesis header includes the t-note."""
    task = _make_worldmodel_task()
    pack = _build_pack(tmp_path, task)
    task_md = (pack.workbench / "TASK.md").read_text()

    assert "lawful_time" in task_md, (
        "lawful_time note missing from TASK.md for lawful_time substrate (FIX 3)"
    )
    assert "t-dependence is admissible" in task_md, (
        "t-dependence admission note missing from lawful_time substrate TASK.md (FIX 3)"
    )


# ---------------------------------------------------------------------------
# FIX 4: Evidence digest appears exactly once across TASK.md + CONTEXT.md
# ---------------------------------------------------------------------------

def test_evidence_digest_not_duplicated(tmp_path: Path) -> None:
    """The evidence digest content must appear in CONTEXT.md but be replaced by a pointer in TASK.md."""
    evidence_marker = "GROUNDING DATA (IMMUTABLE CONSTANTS):"
    task = _make_worldmodel_task(evidence="unique_evidence_sentinel_xyz")
    context = "preamble\n\n=== TASK ===\n" + task

    pack = _build_pack(tmp_path, task, context=context)

    task_md = (pack.workbench / "TASK.md").read_text()
    context_md = (pack.workbench / "CONTEXT.md").read_text()

    # Evidence digest sentinel must NOT appear verbatim in TASK.md
    assert "unique_evidence_sentinel_xyz" not in task_md, (
        "Evidence content found in TASK.md — digest must be in CONTEXT.md only (FIX 4)"
    )

    # CONTEXT.md must retain the full evidence
    assert "unique_evidence_sentinel_xyz" in context_md, (
        "Evidence content missing from CONTEXT.md (FIX 4 — must be kept in background)"
    )

    # TASK.md must have the pointer
    assert "CONTEXT.md" in task_md, (
        "TASK.md must contain a pointer to CONTEXT.md for the evidence digest (FIX 4)"
    )

    # RECORDS.json must still carry structured records (unchanged)
    records = json.loads((pack.workbench / "RECORDS.json").read_text())
    assert "structured_records" in records, (
        "RECORDS.json must still carry structured_records (FIX 4 — must not be affected)"
    )


def test_evidence_digest_appears_once_combined(tmp_path: Path) -> None:
    """Count occurrences of the evidence heading across TASK.md + CONTEXT.md: should be exactly 1."""
    evidence_marker = "GROUNDING DATA (IMMUTABLE CONSTANTS):"
    task = _make_worldmodel_task()
    context = "preamble\n\n=== TASK ===\n" + task

    pack = _build_pack(tmp_path, task, context=context)

    task_md = (pack.workbench / "TASK.md").read_text()
    context_md = (pack.workbench / "CONTEXT.md").read_text()

    combined_count = (task_md + context_md).count(evidence_marker)
    # Should appear exactly once: in CONTEXT.md, not in TASK.md
    assert combined_count == 1, (
        f"Evidence marker '{evidence_marker}' appears {combined_count} times across "
        f"TASK.md + CONTEXT.md (expected 1 — FIX 4)"
    )
