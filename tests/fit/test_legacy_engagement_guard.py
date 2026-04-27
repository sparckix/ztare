"""Tests for the legacy 1D fit primitive engagement guard.

Pin down the regression: gp159 nd_features run had legacy
enable_fit_primitive=true and the loud-fail stub overwrote test_model.py
with a crash stub. These tests prevent that class of bug from returning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ztare.fit.legacy_engagement_guard import (
    resolve_layer3_stub_target,
    should_engage_legacy_1d_fit_primitive,
)


class TestEngagementGate:
    def test_disabled_flag_never_engages(self):
        engage, _reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=False, cage_meta=None
        )
        assert engage is False

    def test_disabled_flag_even_with_class_1d(self):
        engage, _reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=False,
            cage_meta={"class": "1d"},
        )
        assert engage is False

    def test_no_cage_meta_legacy_default_engages(self):
        engage, reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=True, cage_meta=None
        )
        assert engage is True
        assert "OK" in reason

    def test_class_1d_engages(self):
        engage, _reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=True,
            cage_meta={"class": "1d"},
        )
        assert engage is True

    def test_class_1d_case_insensitive(self):
        engage, _reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=True,
            cage_meta={"class": "1D"},
        )
        assert engage is True

    @pytest.mark.parametrize(
        "non_1d_class",
        [
            "nd_features",
            "time_series",
            "time_series_chaotic",
            "audit",
            "literature",
            "proof_target",
            "closed_form_constant",
        ],
    )
    def test_non_1d_classes_refuse_engagement(self, non_1d_class):
        engage, reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=True,
            cage_meta={"class": non_1d_class},
        )
        assert engage is False, (
            f"Class {non_1d_class!r} must NOT engage the legacy 1D path — "
            f"would overwrite authored test_model.py."
        )
        assert non_1d_class in reason

    def test_unknown_class_refuses_engagement(self):
        # Defense-in-depth: unknown classes go to refuse, not engage.
        engage, _reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=True,
            cage_meta={"class": "tensor_target"},
        )
        assert engage is False

    def test_empty_class_string_engages_as_legacy(self):
        # Empty string ≡ unset → legacy 1d default.
        engage, _reason = should_engage_legacy_1d_fit_primitive(
            enable_fit_primitive_flag=True,
            cage_meta={"class": ""},
        )
        assert engage is True


class TestStubWriteTarget:
    def test_sidecar_always_no_features_py(self, tmp_path):
        # SIDECAR ALWAYS (2026-04-25 night): even without features.py,
        # the stub diverts to _fit_stub.py. Was features.py-conditional
        # before; gp159/160/161/145/146 (no features.py) had test_model.py
        # at risk of clobbering on FIT_DECLARATION-missing iters.
        tm = tmp_path / "test_model.py"
        tm.write_text("# legacy")
        target, clobbers = resolve_layer3_stub_target(tm)
        assert target == tmp_path / "_fit_stub.py"
        assert clobbers is True

    def test_sidecar_with_features_py(self, tmp_path):
        tm = tmp_path / "test_model.py"
        tm.write_text("# authored substrate")
        (tmp_path / "features.py").write_text("def visible_rows(): return []")
        target, clobbers = resolve_layer3_stub_target(tm)
        assert target == tmp_path / "_fit_stub.py"
        assert clobbers is True

    def test_authored_test_model_preserved_no_features_py(self, tmp_path):
        # Regression: without features.py, the stub still diverts.
        # gp159 had this exact pattern.
        tm = tmp_path / "test_model.py"
        original = "# AUTHORED\nVISIBLE_SET = [(0, 1.3, 1.69)]\n"
        tm.write_text(original)
        target, _ = resolve_layer3_stub_target(tm)
        target.write_text("def f(*args): raise RuntimeError('stub')")
        assert tm.read_text() == original
        assert (tmp_path / "_fit_stub.py").exists()
