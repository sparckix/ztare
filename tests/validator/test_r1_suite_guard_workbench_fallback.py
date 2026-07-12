"""Tests for the R1 missing-block workbench fallback and retry-prompt fix.

Three properties under test:
  1. retry prompt contains the violated requirement text + example when the
     R1 reason is the missing inline ```python block
  2. workbench test_model.py is accepted when valid (source: workbench_file)
  3. workbench test_model.py is still rejected when invalid
  4. inline block path still works unchanged
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ztare.fit.mutation_suite_guard import (
    extract_python_suite_from_workbench,
    is_missing_block_error,
    validate_python_suite_candidate,
)
from ztare.orchestrator.submission_path_helpers import format_r1_retry_skeleton


_MISSING_ERROR = (
    "Missing required Python falsification suite block; reject candidate before evaluation."
)


# ---------------------------------------------------------------------------
# is_missing_block_error
# ---------------------------------------------------------------------------

def test_is_missing_block_error_true_for_exact_message():
    assert is_missing_block_error(_MISSING_ERROR) is True


def test_is_missing_block_error_true_when_embedded():
    assert is_missing_block_error("R1: " + _MISSING_ERROR) is True


def test_is_missing_block_error_false_for_other_errors():
    assert is_missing_block_error("adherence reject: missing_imodel_def") is False
    assert is_missing_block_error("") is False
    assert is_missing_block_error(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Retry prompt: missing-block error must quote the requirement + example
# ---------------------------------------------------------------------------

def _qualitative_rubric():
    return {
        "rubric_mode": "calibration",
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": False,
        "enable_fit_primitive_features": False,
        "fit_score_mode": "none",
        "holdout_hard_gate": False,
        "holdout_budget": 0,
        "disable_evidence_fit_gate": True,
        "disable_uniqueness_gap_gate": True,
    }


def _numeric_rubric():
    return {"require_i_model_in_submission": True}


def test_retry_prompt_contains_requirement_text_for_qualitative_missing_block():
    prompt = format_r1_retry_skeleton(
        _MISSING_ERROR,
        "## Thesis\nA bounded mechanism claim.",
        rubric_data=_qualitative_rubric(),
    )
    assert "Missing required Python falsification suite block" in prompt
    assert "fenced" in prompt
    assert "```python" in prompt
    assert "def test_smoke" in prompt or "def test_mechanism_is_bounded" in prompt


def test_retry_prompt_contains_requirement_text_for_numeric_missing_block():
    prompt = format_r1_retry_skeleton(
        _MISSING_ERROR,
        "## Thesis\nA numeric hypothesis.",
        rubric_data=_numeric_rubric(),
    )
    assert "Missing required Python falsification suite block" in prompt
    assert "fenced" in prompt
    assert "```python" in prompt
    # minimal example block must be present
    assert "def test_smoke" in prompt


def test_retry_prompt_for_other_errors_does_not_inject_block_requirement(
):
    """Non-missing-block errors must not get the block requirement note injected."""
    prompt = format_r1_retry_skeleton(
        "PARAMETRIC_FORM AST/whitelist pre-flight FAILED",
        "```python\nPARAMETER_NAMES = ['a']\ndef I_model(features, params=None): return 0.0\n```",
        rubric_data=_numeric_rubric(),
    )
    # VIOLATED REQUIREMENT note should not appear for unrelated errors
    assert "VIOLATED REQUIREMENT" not in prompt


# ---------------------------------------------------------------------------
# Workbench-file fallback: extract_python_suite_from_workbench
# ---------------------------------------------------------------------------

_VALID_SUITE = "def test_smoke():\n    assert True\n"
_INVALID_SUITE_EMPTY = ""
_SENTINEL_SUITE = "assert False, 'AI failed to provide a testable falsification suite.'"


def test_workbench_fallback_accepts_valid_suite(tmp_path: Path):
    (tmp_path / "test_model.py").write_text(_VALID_SUITE, encoding="utf-8")
    result = extract_python_suite_from_workbench(
        str(tmp_path),
        require_i_model=False,
    )
    assert result == _VALID_SUITE


def test_workbench_fallback_rejects_empty_suite(tmp_path: Path):
    (tmp_path / "test_model.py").write_text(_INVALID_SUITE_EMPTY, encoding="utf-8")
    result = extract_python_suite_from_workbench(
        str(tmp_path),
        require_i_model=False,
    )
    assert result is None


def test_workbench_fallback_rejects_sentinel_suite(tmp_path: Path):
    (tmp_path / "test_model.py").write_text(_SENTINEL_SUITE, encoding="utf-8")
    result = extract_python_suite_from_workbench(
        str(tmp_path),
        require_i_model=False,
    )
    assert result is None


def test_workbench_fallback_returns_none_when_no_test_model(tmp_path: Path):
    result = extract_python_suite_from_workbench(str(tmp_path), require_i_model=False)
    assert result is None


def test_workbench_fallback_returns_none_when_project_dir_is_none():
    result = extract_python_suite_from_workbench(None, require_i_model=False)
    assert result is None


def test_workbench_fallback_rejects_syntax_error_suite(tmp_path: Path):
    (tmp_path / "test_model.py").write_text(
        "def broken(\n    assert True\n", encoding="utf-8"
    )
    result = extract_python_suite_from_workbench(str(tmp_path), require_i_model=False)
    assert result is None


def test_workbench_fallback_rejects_suite_that_fails_import_check(tmp_path: Path):
    # Module-level I_model() call at import time will fail the import dry-run
    code = (
        "MODEL_PARAMS = {'a': 1.0}\n"
        "def I_model(features, params=None):\n"
        "    p = params if params is not None else MODEL_PARAMS\n"
        "    return float(p['a'])\n"
        "I_model({'x': 1.0})  # module-level call — rejected\n"
    )
    (tmp_path / "test_model.py").write_text(code, encoding="utf-8")
    result = extract_python_suite_from_workbench(str(tmp_path), require_i_model=False)
    assert result is None


# ---------------------------------------------------------------------------
# Inline block path: validate_python_suite_candidate still works unchanged
# ---------------------------------------------------------------------------

def test_inline_valid_block_passes():
    validate_python_suite_candidate(_VALID_SUITE)  # must not raise


def test_inline_none_raises():
    with pytest.raises(ValueError, match="Missing required Python falsification suite block"):
        validate_python_suite_candidate(None)


def test_inline_empty_raises():
    with pytest.raises(ValueError, match="Missing required Python falsification suite block"):
        validate_python_suite_candidate("   ")


def test_inline_sentinel_raises():
    with pytest.raises(ValueError, match="Mutator emitted the no-suite sentinel"):
        validate_python_suite_candidate(_SENTINEL_SUITE)


# ---------------------------------------------------------------------------
# Static guard: autoresearch_loop.py has the right code structure
# ---------------------------------------------------------------------------

def test_autoresearch_loop_has_workbench_fallback_structure():
    """Guard that the loop's _r1_receipt_only block is present and wired correctly."""
    from pathlib import Path as P
    repo_root = P(__file__).resolve().parents[2]
    src = (repo_root / "src" / "ztare" / "validator" / "autoresearch_loop.py").read_text(
        encoding="utf-8"
    )
    assert "is_missing_block_error" in src
    assert "extract_python_suite_from_workbench" in src
    assert "_r1_receipt_only = is_missing_block_error(_r1_last_error)" in src
    assert "source: workbench_file" in src
    assert "if _r1_receipt_only:" in src

    # ordering: workbench check before retry prompt
    receipt_pos = src.index("if _r1_receipt_only:")
    retry_prompt_pos = src.index("_retry_prompt = format_r1_retry_skeleton(", receipt_pos)
    retry_call_pos = src.index("new_content = safe_mutate(", retry_prompt_pos)
    assert receipt_pos < retry_prompt_pos < retry_call_pos


def test_worldmodel_retry_skeleton_surfaces_missing_block_requirement():
    from ztare.worldmodel.retry_surface import format_worldmodel_retry_skeleton

    out = format_worldmodel_retry_skeleton(
        "Missing required Python falsification suite block; reject candidate before evaluation.",
        prior_content="",
        max_prior_chars=1000,
    )
    assert "VIOLATED REQUIREMENT (verbatim)" in out
    assert "test_model_py" in out

    unrelated = format_worldmodel_retry_skeleton(
        "PATCH_BASE_REGRESSION_PRECHECK: regression detected",
        prior_content="",
        max_prior_chars=1000,
    )
    assert "VIOLATED REQUIREMENT (verbatim)" not in unrelated


def test_typed_payload_regression_the_three_bounced_responses(tmp_path):
    """The exact failure of 2026-07-10: a lawful worldmodel JSON payload
    (no fences, per the payload contract) must yield its test_model_py
    through the typed parser instead of bouncing at the fence scanner."""
    import json as _json
    from ztare.validator.worldmodel_typed_payload import (
        parse_worldmodel_typed_payload_text,
    )
    from ztare.fit.mutation_suite_guard import validate_python_suite_candidate

    payload = _json.dumps({
        "control_receipts": [],
        "thesis_markdown": "DISCOVERY update: boundary carrier.",
        "test_model_py": 'PATCH_BASE = {"source_ref": "workspace/submissions/x.py", "sha256": "ab"}\n'
                         "def step(grid, action, t):\n    return grid\n",
    })
    parsed = parse_worldmodel_typed_payload_text(payload)
    code = str(parsed.get("test_model_py") or "")
    assert code.strip()
    validate_python_suite_candidate(code)  # must NOT raise
