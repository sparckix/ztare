"""Tests for scripts/validate_evidence.py (GP-162 + GP-157 Phase 7).

Pin down the class-aware lint set + STRICT mode toggle. The cross-substrate
checks (#1-7) have been load-bearing since GP-162 and are tested via the
existing make-seal smoke run; this file focuses on Phase 7 additions:

    - cage_meta.class drives per-class lints (no double-firing across classes)
    - STRICT mode promotes class-aware warnings to errors
    - SOFT mode keeps them advisory
    - Generic TODO/FIXME/XXX detection
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Resolve the script under test as an importable module. scripts/ is not
# a package, so load via importlib spec from absolute path.
_REPO = Path(__file__).resolve().parent.parent.parent
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location(
    "validate_evidence_under_test",
    str(_REPO / "scripts" / "validate_evidence.py"),
)
assert _spec is not None and _spec.loader is not None
_module = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_module)

_class_aware_lints = _module._class_aware_lints
_read_rubric = _module._read_rubric
validate_evidence = _module.validate_evidence


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_minimal_evidence(
    project_dir: Path,
    *,
    extra_text: str = "",
) -> Path:
    """Write a minimal-but-passing evidence.txt + a placeholder gate_harness."""
    project_dir.mkdir(parents=True, exist_ok=True)
    inline_table = "\n".join(
        f"| {i}.{i} | {i*10}.{i} |" for i in range(1, 8)
    )
    evidence = f"""# Evidence

## Visible data table

| x   | y   |
|-----|-----|
{inline_table}

## Constraints
- bound: positive
- rule: monotonic

## How to submit
Define `def I_model(features): return ...` in test_model.py.

```python
def I_model(features):
    return features.get('x', 0.0)
```

{extra_text}
"""
    p = project_dir / "evidence.txt"
    p.write_text(evidence, encoding="utf-8")
    return p


def _make_rubric(rubric_path: Path, **fields) -> Path:
    rubric_path.parent.mkdir(parents=True, exist_ok=True)
    rubric_path.write_text(json.dumps(fields), encoding="utf-8")
    return rubric_path


# ── _read_rubric ─────────────────────────────────────────────────────────


class TestReadRubric:
    def test_none_returns_empty(self):
        assert _read_rubric(None) == {}

    def test_missing_file_returns_empty(self, tmp_path):
        assert _read_rubric(tmp_path / "nonexistent.json") == {}

    def test_malformed_json_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{ not json", encoding="utf-8")
        assert _read_rubric(p) == {}

    def test_valid_json(self, tmp_path):
        p = tmp_path / "ok.json"
        p.write_text(json.dumps({"k": 1}), encoding="utf-8")
        assert _read_rubric(p) == {"k": 1}


# ── _class_aware_lints ───────────────────────────────────────────────────


class TestClassAwareLints:
    def test_unknown_class_no_lints(self):
        # Plus generic TODO check returns 0 when no markers.
        diags = _class_aware_lints("plain text", "tensor_target")
        assert diags == []

    def test_nd_features_missing_imodel_warns(self):
        diags = _class_aware_lints("data tables and constraints only", "nd_features")
        assert any("I_model" in d for d in diags)
        assert any("features" in d for d in diags)

    def test_nd_features_with_imodel_and_features_passes(self):
        text = "Define `I_model(features)` to access `features['x']`."
        diags = _class_aware_lints(text, "nd_features")
        # No nd_features-specific warning when both terms present.
        assert not any("does not mention `I_model`" in d for d in diags)
        assert not any("does not mention `features`" in d for d in diags)

    def test_audit_substrate_with_big_table_warns(self):
        # 10 numeric rows → audit substrate should warn (audit is critique, not fitting).
        rows = "\n".join(f"| {i}.{i} | {i*10}.{i} |" for i in range(1, 11))
        diags = _class_aware_lints(rows, "audit")
        assert any("audit substrate" in d.lower() for d in diags)

    def test_audit_substrate_with_few_tables_no_warn(self):
        rows = "\n".join(f"| {i}.{i} | {i*10}.{i} |" for i in range(1, 4))
        diags = _class_aware_lints(rows, "audit")
        # 3 rows < threshold 8 → no audit-table warning
        assert not any("audit substrate" in d.lower() for d in diags)

    def test_proof_target_missing_lean_warns(self):
        diags = _class_aware_lints("just data", "proof_target")
        assert any("Lean" in d or "theorem" in d for d in diags)

    def test_proof_target_mentions_lean_passes(self):
        diags = _class_aware_lints("Submit a Lean theorem proof", "proof_target")
        assert not any("does not reference Lean" in d for d in diags)

    def test_closed_form_constant_missing_pslq_warns(self):
        diags = _class_aware_lints("just data", "closed_form_constant")
        assert any("PSLQ" in d for d in diags)

    def test_class_case_insensitive(self):
        diags = _class_aware_lints("data only", "ND_FEATURES")
        # Same lints fire regardless of case
        assert any("I_model" in d for d in diags)

    def test_todo_marker_warns(self):
        diags = _class_aware_lints("All good. TODO: write better example.", "nd_features")
        assert any("TODO" in d for d in diags)

    def test_fixme_marker_warns(self):
        diags = _class_aware_lints(
            "All good. FIXME this is a placeholder. I_model(features) is canonical.",
            "nd_features",
        )
        assert any("FIXME" in d.upper() or "TODO/FIXME/XXX" in d for d in diags)


# ── validate_evidence integration: STRICT vs SOFT ────────────────────────


class TestStrictModeToggle:
    def _setup(self, tmp_path, *, strict: bool):
        """Build a valid evidence.txt under projects/<slug>/, plus a rubric.

        Includes a features.py so the GP-157 v5 class-consistency check
        passes (this test focuses on the soft/strict TODO-marker toggle,
        not consistency-check semantics).
        """
        slug = "gp_test_substrate"
        project_dir = tmp_path / "projects" / slug
        _make_minimal_evidence(project_dir, extra_text="TODO: improve later. Use I_model with `features` dict.")
        # nd_features substrate must author features.py to pass consistency.
        (project_dir / "features.py").write_text("def visible_rows(): return []\n")
        rubric_path = tmp_path / "rubrics" / f"{slug}.json"
        _make_rubric(
            rubric_path,
            cage_meta={"class": "nd_features"},
            evidence_strict_lint=strict,
        )
        return slug, rubric_path, project_dir

    def test_soft_mode_warning_does_not_fail(self, tmp_path, monkeypatch):
        slug, rubric_path, _ = self._setup(tmp_path, strict=False)
        monkeypatch.chdir(tmp_path)
        passed, diags = validate_evidence(slug, rubric_path=rubric_path)
        assert passed is True, f"soft mode should pass; diags: {diags}"
        # The TODO warning should still appear.
        assert any("TODO" in d for d in diags)
        # Should be marked as warning (⚠️) not error (❌).
        assert any(d.startswith("  ⚠️") for d in diags)

    def test_strict_mode_promotes_class_warning_to_error(self, tmp_path, monkeypatch):
        slug, rubric_path, _ = self._setup(tmp_path, strict=True)
        monkeypatch.chdir(tmp_path)
        passed, diags = validate_evidence(slug, rubric_path=rubric_path)
        assert passed is False, f"strict mode should fail on TODO marker; diags: {diags}"
        # In strict mode the TODO warning is emitted as an error (❌).
        assert any("TODO" in d and d.startswith("  ❌") for d in diags)

    def test_no_rubric_no_class_lints(self, tmp_path, monkeypatch):
        slug = "gp_test_no_rubric"
        project_dir = tmp_path / "projects" / slug
        _make_minimal_evidence(project_dir, extra_text="TODO: improve later.")
        monkeypatch.chdir(tmp_path)
        passed, diags = validate_evidence(slug, rubric_path=None)
        # Without rubric, class-aware lints don't fire — TODO not flagged.
        assert passed is True
        assert not any("TODO" in d for d in diags)

    def test_strict_mode_label_in_diagnostics(self, tmp_path, monkeypatch):
        slug, rubric_path, _ = self._setup(tmp_path, strict=True)
        monkeypatch.chdir(tmp_path)
        _, diags = validate_evidence(slug, rubric_path=rubric_path)
        assert any("STRICT" in d for d in diags)

    def test_soft_mode_label_in_diagnostics(self, tmp_path, monkeypatch):
        slug, rubric_path, _ = self._setup(tmp_path, strict=False)
        monkeypatch.chdir(tmp_path)
        _, diags = validate_evidence(slug, rubric_path=rubric_path)
        assert any("mode=soft" in d for d in diags)
