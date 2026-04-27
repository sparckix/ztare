"""Tests for orchestrator/state.py (GP-157 v5.0 Phase 4c)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.ztare.orchestrator import (
    CageRuntime,
    build_cage_runtime,
    cage_init_banner,
    resolve_cage_mode,
)


class TestResolveCageMode:
    def test_off_when_no_flags(self):
        assert resolve_cage_mode({}) == "off"

    def test_off_when_both_false(self):
        assert resolve_cage_mode({
            "cage_observe_mode": False,
            "cage_authoritative_mode": False,
        }) == "off"

    def test_observe_when_only_observe_flag(self):
        assert resolve_cage_mode({"cage_observe_mode": True}) == "observe"

    def test_authoritative_takes_precedence(self):
        assert resolve_cage_mode({
            "cage_observe_mode": True,
            "cage_authoritative_mode": True,
        }) == "authoritative"

    def test_authoritative_alone_resolves(self):
        # cage_authoritative_mode implies observe; do not require observe flag
        assert resolve_cage_mode({"cage_authoritative_mode": True}) == "authoritative"


class TestBuildCageRuntime:
    def _factory(self, n_gates: int = 3):
        cage = SimpleNamespace(gates={f"g{i}": object() for i in range(n_gates)})
        return lambda: cage

    def test_off_returns_inactive_runtime(self):
        rt = build_cage_runtime({}, cage_factory=self._factory(), cage_available=True)
        assert rt.is_active is False
        assert rt.mode == "off"
        assert rt.instance is None
        assert rt.substrate_view is None

    def test_unavailable_cage_returns_inactive(self):
        rt = build_cage_runtime(
            {"cage_observe_mode": True},
            cage_factory=self._factory(),
            cage_available=False,
        )
        assert rt.is_active is False
        assert rt.mode == "observe"
        assert rt.instance is None

    def test_observe_mode_constructs_runtime(self):
        meta = {"class": "1d", "target_convention_homogeneity": "homogeneous"}
        rt = build_cage_runtime(
            {"cage_observe_mode": True, "cage_meta": meta},
            cage_factory=self._factory(n_gates=4),
            cage_available=True,
        )
        assert rt.is_active is True
        assert rt.mode == "observe"
        assert rt.is_observe is True
        assert rt.is_authoritative is False
        assert rt.cage_meta == meta
        assert rt.substrate_view.meta == meta

    def test_authoritative_mode_marks_runtime(self):
        rt = build_cage_runtime(
            {"cage_authoritative_mode": True, "cage_meta": {"class": "nd_features"}},
            cage_factory=self._factory(),
            cage_available=True,
        )
        assert rt.is_authoritative is True
        assert rt.is_observe is True  # authoritative implies observe

    def test_factory_failure_returns_inactive_not_raises(self):
        def bad_factory():
            raise RuntimeError("registry import failed")
        rt = build_cage_runtime(
            {"cage_observe_mode": True},
            cage_factory=bad_factory,
            cage_available=True,
        )
        assert rt.is_active is False
        # Mode preserved so caller can log diagnostics
        assert rt.mode == "observe"


class TestCageInitBanner:
    def test_inactive_returns_none(self):
        rt = CageRuntime(instance=None, substrate_view=None, mode="off", cage_meta={})
        assert cage_init_banner(rt) is None

    def test_observe_banner(self):
        cage = SimpleNamespace(gates={"a": 1, "b": 2, "c": 3})
        rt = CageRuntime(
            instance=cage,
            substrate_view=SimpleNamespace(meta={"class": "1d"}),
            mode="observe",
            cage_meta={"class": "1d", "target_convention_homogeneity": "homogeneous"},
        )
        s = cage_init_banner(rt)
        assert s is not None
        assert "observe-mode ACTIVE" in s
        assert "3 gates" in s
        assert "class=1d" in s
        assert "homogeneous" in s

    def test_authoritative_banner_label(self):
        cage = SimpleNamespace(gates={"a": 1})
        rt = CageRuntime(
            instance=cage,
            substrate_view=SimpleNamespace(meta={"class": "nd_features"}),
            mode="authoritative",
            cage_meta={"class": "nd_features", "target_convention_homogeneity": "homogeneous"},
        )
        s = cage_init_banner(rt)
        assert "AUTHORITATIVE ACTIVE" in s
        assert "observe-mode" not in s
