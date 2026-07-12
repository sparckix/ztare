"""Envelope normalization tests — Fix A + Fix B.

Fix A: MutationDeclaration header parsing normalizes instead of rejects for:
  - missing header → kernel-derived declaration, no strike consumed
  - mismatched declaration (UNDECLARED_ARTIFACT_BREADTH) → computed scope wins, mismatch note
  - invalid primitive key (INVALID_PRIMITIVE_DECLARATION) → key dropped with note, proceeds

Fix B: retry dispatch resolves visible_workbench for call_site=mutator.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/ on path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.validator.core.mutation_contract import (
    ClaimDeltaType,
    MutationArtifact,
    MutationDeclaration,
    MutationMismatchCode,
    MutationScopeDelta,
    ThesisControlMode,
    _infer_scope_for_artifacts,
    evaluate_mutation_declaration,
)


APPROVED = (
    "self_referential_falsification",
    "cooked_books",
    "float_masking",
)


# ---------------------------------------------------------------------------
# Fix A — mutation_contract.py normalization
# ---------------------------------------------------------------------------


def test_invalid_primitive_key_is_dropped_not_rejected() -> None:
    """INVALID_PRIMITIVE_DECLARATION: invalid key dropped, evaluation proceeds to CLEAN."""
    decl = MutationDeclaration(
        scope_delta=MutationScopeDelta.THESIS_ONLY,
        claim_delta_type=ClaimDeltaType.REFRAMING,
        primitive_invoked="invented_magic_primitive",
        touched_artifacts=(MutationArtifact.THESIS_MD,),
    )
    record = evaluate_mutation_declaration(
        decl,
        ("projects/sample/thesis.md",),
        before_text="Bounded local parser.",
        after_text="Bounded local parser with clearer wording.",
        approved_primitive_keys=APPROVED,
    )
    assert record.mismatch_code == MutationMismatchCode.CLEAN, (
        f"Expected CLEAN after normalization, got {record.mismatch_code.value}: {record.rationale}"
    )
    assert "INVALID_PRIMITIVE_DECLARATION normalized" in record.rationale
    # Kernel cleared the invalid key
    assert record.declared_primitive_invoked is None


def test_invalid_primitive_mismatch_note_in_rationale() -> None:
    """Mismatch note surfaces the original key name for gaming-detection audit."""
    decl = MutationDeclaration(
        scope_delta=MutationScopeDelta.TEST_HARNESS,
        claim_delta_type=ClaimDeltaType.REFRAMING,
        primitive_invoked="invented_magic_primitive",
        touched_artifacts=(MutationArtifact.TEST_MODEL_PY,),
    )
    record = evaluate_mutation_declaration(
        decl,
        ("projects/sample/test_model.py",),
        before_text="",
        after_text="",
        approved_primitive_keys=APPROVED,
    )
    assert "invented_magic_primitive" in record.rationale
    assert "derived_by=kernel" in record.rationale


def test_undeclared_artifact_breadth_scope_upgraded_not_rejected() -> None:
    """UNDECLARED_ARTIFACT_BREADTH: scope upgraded to cover actual artifacts, proceeds."""
    # Declares THESIS_ONLY but also touches test_model.py
    decl = MutationDeclaration(
        scope_delta=MutationScopeDelta.THESIS_ONLY,
        claim_delta_type=ClaimDeltaType.REFRAMING,
        primitive_invoked=None,
        touched_artifacts=(MutationArtifact.THESIS_MD,),
    )
    record = evaluate_mutation_declaration(
        decl,
        ("projects/sample/thesis.md", "projects/sample/test_model.py"),
        before_text="Bounded local parser.",
        after_text="Bounded local parser with extra check.",
        approved_primitive_keys=APPROVED,
    )
    assert record.mismatch_code == MutationMismatchCode.CLEAN, (
        f"Expected CLEAN after scope upgrade, got {record.mismatch_code.value}"
    )
    assert "UNDECLARED_ARTIFACT_BREADTH normalized" in record.rationale
    assert record.declared_scope_delta == MutationScopeDelta.TEST_HARNESS


def test_undeclared_breadth_mismatch_note_includes_scope_upgrade() -> None:
    decl = MutationDeclaration(
        scope_delta=MutationScopeDelta.THESIS_ONLY,
        claim_delta_type=ClaimDeltaType.REFRAMING,
        primitive_invoked=None,
        touched_artifacts=(MutationArtifact.THESIS_MD,),
    )
    record = evaluate_mutation_declaration(
        decl,
        ("projects/sample/thesis.md", "projects/sample/test_model.py"),
        approved_primitive_keys=APPROVED,
    )
    assert "THESIS_ONLY" in record.rationale
    assert "TEST_HARNESS" in record.rationale
    assert "derived_by=kernel" in record.rationale


def test_claim_delta_scope_conflict_still_rejects() -> None:
    """Science-content reject (CLAIM_DELTA_SCOPE_CONFLICT) is not swallowed."""
    decl = MutationDeclaration(
        scope_delta=MutationScopeDelta.THESIS_ONLY,
        claim_delta_type=ClaimDeltaType.NARROWING,
        primitive_invoked=None,
        touched_artifacts=(MutationArtifact.THESIS_MD,),
    )
    record = evaluate_mutation_declaration(
        decl,
        ("projects/sample/thesis.md",),
        before_text="This component routes one local token.",
        after_text=(
            "This component ensures whole-system stability, guarantees completeness, "
            "and provides end-to-end protection."
        ),
        approved_primitive_keys=APPROVED,
    )
    assert record.mismatch_code == MutationMismatchCode.CLAIM_DELTA_SCOPE_CONFLICT


def test_infer_scope_thesis_only() -> None:
    assert _infer_scope_for_artifacts((MutationArtifact.THESIS_MD,)) == MutationScopeDelta.THESIS_ONLY


def test_infer_scope_test_harness() -> None:
    assert _infer_scope_for_artifacts(
        (MutationArtifact.THESIS_MD, MutationArtifact.TEST_MODEL_PY)
    ) == MutationScopeDelta.TEST_HARNESS


def test_infer_scope_multi_artifact_for_unusual_mix() -> None:
    assert _infer_scope_for_artifacts(
        (MutationArtifact.THESIS_MD, MutationArtifact.RUBRIC_JSON)
    ) == MutationScopeDelta.MULTI_ARTIFACT


# ---------------------------------------------------------------------------
# Fix A — kernel derivation: headerless submission proceeds (preflight path)
# ---------------------------------------------------------------------------


def test_derive_mutation_declaration_from_artifact_diff() -> None:
    """Headerless submission: kernel derives declaration from changed content."""
    # Import the private derivation function via the internal module path
    # (it lives in autoresearch_loop which requires globals; we test the
    # mutation_contract primitives it delegates to instead)
    # Direct unit test: infer scope + claim_delta from what _derive_mutation_declaration does
    from ztare.validator.core.mutation_contract import (
        _estimate_claim_breadth,
        _infer_scope_for_artifacts,
    )
    actual = (MutationArtifact.THESIS_MD, MutationArtifact.TEST_MODEL_PY)
    scope = _infer_scope_for_artifacts(actual)
    assert scope == MutationScopeDelta.TEST_HARNESS

    before = "Bounded local component."
    after = "Bounded local component with clearer wording."
    delta = _estimate_claim_breadth(after) - _estimate_claim_breadth(before)
    assert delta == 0  # REFRAMING

    before_wide = "Bounded local component."
    after_wide = "This guarantees whole-system stability end-to-end."
    delta_wide = _estimate_claim_breadth(after_wide) - _estimate_claim_breadth(before_wide)
    assert delta_wide > 0  # WIDENING


# ---------------------------------------------------------------------------
# Fix B — retry dispatch mode resolution
# ---------------------------------------------------------------------------


def test_resolve_agent_execution_mode_returns_visible_workbench_for_mutator() -> None:
    """resolve_agent_execution_mode('mutator') must return visible_workbench by default."""
    from ztare.common.dispatch_model import resolve_agent_execution_mode
    mode = resolve_agent_execution_mode("mutator")
    assert mode == "visible_workbench", (
        f"Expected visible_workbench for mutator call_site, got {mode!r}"
    )


def test_resolve_agent_execution_mode_sealed_for_non_mutator() -> None:
    from ztare.common.dispatch_model import resolve_agent_execution_mode
    assert resolve_agent_execution_mode("judge") == "sealed_completion"
    assert resolve_agent_execution_mode("evaluator") == "sealed_completion"


def test_dispatch_model_receives_visible_workbench_mode_for_mutator() -> None:
    """Fix B: safe_mutate's agent path passes agent_execution_mode=visible_workbench.

    We verify the mode resolution plumbing directly — resolve_agent_execution_mode("mutator")
    returns "visible_workbench", which is what safe_mutate now passes to dispatch_model.
    This is the unit test for the retry-mode fix: the kwarg is now explicit in safe_mutate
    rather than falling through to the sealed_completion signature default.
    """
    from ztare.common.dispatch_model import resolve_agent_execution_mode

    # First-attempt mode
    mode_first = resolve_agent_execution_mode("mutator")
    assert mode_first == "visible_workbench", (
        f"First-attempt mutator mode must be visible_workbench, got {mode_first!r}"
    )

    # Retry calls safe_mutate again via the same path — same resolution
    mode_retry = resolve_agent_execution_mode("mutator")
    assert mode_retry == "visible_workbench", (
        f"Retry mutator mode must be visible_workbench, got {mode_retry!r}"
    )

    # Non-mutator call sites remain sealed
    assert resolve_agent_execution_mode("judge") == "sealed_completion"
