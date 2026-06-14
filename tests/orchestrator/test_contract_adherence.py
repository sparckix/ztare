"""Tests for orchestrator/contract_adherence.py.

Pin down telemetry detection logic. Empirical signal that future runs
will use to decide whether the substrate-contract hint is effective.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ztare.orchestrator.contract_adherence import (
    AdherenceReport,
    VIOLATION_CODES,
    _resolve_active_contract,
    check_contract_adherence,
    emit_adherence,
    format_adherence_summary,
    runtime_check_imodel,
)
from src.ztare.orchestrator.iter_context import IterContext


# ── Active-contract resolution ───────────────────────────────────────────


class TestResolveActiveContract:
    def test_no_class_returns_none(self, tmp_path):
        assert _resolve_active_contract({}, tmp_path) == "none"

    def test_class_1d_no_test_model_returns_a(self, tmp_path):
        rubric = {"cage_meta": {"class": "1d"}}
        # No test_model.py → Contract C does not fire → fall through to A.
        assert _resolve_active_contract(rubric, tmp_path) == "A"

    def test_class_1d_with_test_model_returns_c(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(d): return 0.0")
        rubric = {"cage_meta": {"class": "1d"}}
        assert _resolve_active_contract(rubric, tmp_path) == "C"

    def test_class_nd_features_returns_b(self, tmp_path):
        rubric = {"cage_meta": {"class": "nd_features"}}
        assert _resolve_active_contract(rubric, tmp_path) == "B"

    def test_fit_primitive_overrides(self, tmp_path):
        # When fit primitive is engaged, neither B nor C contract hint
        # fires; for nd_features that means contract resolves to "none".
        rubric = {"enable_fit_primitive_features": True, "cage_meta": {"class": "nd_features"}}
        assert _resolve_active_contract(rubric, tmp_path) == "none"


# ── check_contract_adherence ─────────────────────────────────────────────


class TestAdherenceContractC:
    """Pin down detection on the gp159 iter-3 failure mode."""

    def _ctx(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(d): return 0.0")
        rubric = {"cage_meta": {"class": "1d"}}
        return rubric, tmp_path

    def test_clean_contract_c_no_violations(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        text = """
MODEL_PARAMS = {}

def I_model(d, params=MODEL_PARAMS):
    a = params.get('a', 1.0)
    return a * d
"""
        violations = check_contract_adherence(text, rubric, project)
        assert violations == []

    def test_module_level_imodel_call_caught(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        text = """
MODEL_PARAMS = {}

def I_model(d, params=MODEL_PARAMS):
    return d

I_model(1.0)
"""
        violations = check_contract_adherence(text, rubric, project)
        assert "module_level_imodel_call" in violations

    def test_wrong_signature_b_for_c_caught(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        # Mutator emits Contract B shape (`features`) when contract is C
        text = """
MODEL_PARAMS = {}

def I_model(features, params=MODEL_PARAMS):
    return features['d']
"""
        violations = check_contract_adherence(text, rubric, project)
        assert "wrong_signature_b_for_c" in violations

    def test_deferred_assert_helper_caught(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        # gp159 iter 3 pattern: asserts moved to a non-called helper
        text = """
MODEL_PARAMS = {}

def _post_fit_sanity():
    assert MODEL_PARAMS  # never runs because nothing calls _post_fit_sanity

def I_model(d, params=MODEL_PARAMS):
    return float('nan')
"""
        violations = check_contract_adherence(text, rubric, project)
        assert "deferred_assert_helper" in violations

    def test_nan_return_caught(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        text = """
def I_model(d, params=None):
    return float('nan')
"""
        violations = check_contract_adherence(text, rubric, project)
        assert "nan_return_literal" in violations


class TestAdherenceContractB:
    def _ctx(self, tmp_path):
        (tmp_path / "features.py").write_text("def visible_rows(): return []")
        rubric = {"cage_meta": {"class": "nd_features"}}
        return rubric, tmp_path

    def test_clean_contract_b_no_violations(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        text = """
def I_model(features):
    return features.get('x', 0.0)
"""
        violations = check_contract_adherence(text, rubric, project)
        assert violations == []

    def test_wrong_signature_c_for_b_caught(self, tmp_path):
        rubric, project = self._ctx(tmp_path)
        text = """
def I_model(d, params=None):
    return d * 2
"""
        violations = check_contract_adherence(text, rubric, project)
        assert "wrong_signature_c_for_b" in violations


class TestAdherenceMisc:
    def test_missing_def_imodel(self, tmp_path):
        rubric = {"cage_meta": {"class": "1d"}}
        violations = check_contract_adherence("# nothing", rubric, tmp_path)
        assert "missing_imodel_def" in violations

    def test_empty_test_model(self, tmp_path):
        rubric = {"cage_meta": {"class": "1d"}}
        violations = check_contract_adherence("", rubric, tmp_path)
        assert "missing_imodel_def" in violations

    def test_violation_codes_referenced_have_descriptions(self):
        # Sanity: any violation a checker emits must be in VIOLATION_CODES.
        emitted = {
            "module_level_imodel_call",
            "wrong_signature_b_for_c",
            "wrong_signature_c_for_b",
            "missing_imodel_def",
            "deferred_assert_helper",
            "nan_return_literal",
            # Runtime checks added 2026-04-25 per gp159 o3 evidence.
            "runtime_nan_return",
            "runtime_import_failure",
            "runtime_imodel_raises",
        }
        assert emitted == set(VIOLATION_CODES.keys())


# ── emit_adherence + format_adherence_summary ────────────────────────────


class TestRuntimeCheckImodel:
    """Runtime adherence — catches NaN-returning I_model that
    static analysis misses (gp159 o3 case)."""

    def test_clean_imodel_no_violations(self, tmp_path):
        tm = tmp_path / "test_model.py"
        tm.write_text(
            "MODEL_PARAMS = {}\n"
            "VISIBLE_SET = [(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]\n"
            "def I_model(d, params=None):\n"
            "    return 2.0 * d\n"
        )
        from src.ztare.orchestrator.contract_adherence import runtime_check_imodel
        assert runtime_check_imodel(tm) == []

    def test_nan_return_caught_at_runtime(self, tmp_path):
        tm = tmp_path / "test_model.py"
        tm.write_text(
            "MODEL_PARAMS = {}\n"
            "VISIBLE_SET = [(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]\n"
            "def I_model(d, params=None):\n"
            "    return float('nan')\n"
        )
        from src.ztare.orchestrator.contract_adherence import runtime_check_imodel
        violations = runtime_check_imodel(tm)
        assert "runtime_nan_return" in violations

    def test_inf_return_caught_at_runtime(self, tmp_path):
        tm = tmp_path / "test_model.py"
        tm.write_text(
            "MODEL_PARAMS = {}\n"
            "VISIBLE_SET = [(1.0, 2.0)]\n"
            "def I_model(d, params=None):\n"
            "    return float('inf')\n"
        )
        from src.ztare.orchestrator.contract_adherence import runtime_check_imodel
        assert "runtime_nan_return" in runtime_check_imodel(tm)

    def test_imodel_raises_caught(self, tmp_path):
        tm = tmp_path / "test_model.py"
        tm.write_text(
            "MODEL_PARAMS = {}\n"
            "VISIBLE_SET = [(1.0, 2.0)]\n"
            "def I_model(d, params=None):\n"
            "    raise ValueError('nope')\n"
        )
        from src.ztare.orchestrator.contract_adherence import runtime_check_imodel
        assert "runtime_imodel_raises" in runtime_check_imodel(tm)

    def test_module_import_failure_caught(self, tmp_path):
        tm = tmp_path / "test_model.py"
        tm.write_text("syntax error\n")
        from src.ztare.orchestrator.contract_adherence import runtime_check_imodel
        assert "runtime_import_failure" in runtime_check_imodel(tm)

    def test_nonexistent_path_returns_empty(self, tmp_path):
        from src.ztare.orchestrator.contract_adherence import runtime_check_imodel
        assert runtime_check_imodel(tmp_path / "missing.py") == []


class TestEmitAndFormat:
    def test_emit_writes_jsonl(self, tmp_path):
        # workspace_dir lives under project_dir (parent provides project)
        project = tmp_path / "proj"
        project.mkdir()
        (project / "test_model.py").write_text("def I_model(d): return 0.0")
        ws = project / "workspace"
        ws.mkdir()
        ctx = IterContext(
            iteration_index=2,
            run_id=1,
            project="test",
            workspace_dir=ws,
            rubric_data={"cage_meta": {"class": "1d"}},
        )
        text = "def I_model(d, params=None): return d"
        report = emit_adherence(ctx, text)

        assert isinstance(report, AdherenceReport)
        assert report.iter == 3  # iteration_index 2 → iter 3
        assert report.active_contract == "C"
        assert report.adheres is True

        log_path = ws / "contract_violations.jsonl"
        assert log_path.exists()
        line = log_path.read_text().strip()
        payload = json.loads(line)
        assert payload["iter"] == 3
        assert payload["adheres"] is True

    def test_format_silent_on_adherence(self):
        rep = AdherenceReport(iter=1, active_contract="C", violations=[])
        assert format_adherence_summary(rep) is None

    def test_format_emits_codes_on_violation(self):
        rep = AdherenceReport(
            iter=2,
            active_contract="C",
            violations=["module_level_imodel_call", "nan_return_literal"],
        )
        s = format_adherence_summary(rep)
        assert s is not None
        assert "module_level_imodel_call" in s
        assert "nan_return_literal" in s
