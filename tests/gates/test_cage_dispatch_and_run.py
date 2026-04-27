"""Tests for Cage.dispatch_and_run (GP-157 v5.0 Phase 3c).

Pin down the authoritative-dispatch behavior:
  - dispatch_and_run returns (matrix, run_results)
  - only engaged gates have a run_results entry
  - run failures are caught per-gate and recorded as __error__
  - one failing gate does not abort the rest of the topo order
  - invalid substrate.meta produces empty run_results
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from src.ztare.gates.cage import Cage, Gate


@dataclass
class _SubstrateView:
    """Minimal stand-in for the validator's substrate proxy."""
    meta: dict


def _valid_meta(class_: str = "1d") -> dict:
    return {
        "type": "discovery",
        "class": class_,
        "target_convention_homogeneity": "homogeneous",
        "min_rows_per_category": 5,
        "near_miss_factor": 1.5,
        "frame_invariant_y": True,
    }


def _engages_universally():
    def can_handle(_s, _c):
        return True, "engaged"
    return can_handle


def _engages_only_on_class(target_class):
    def can_handle(s, _c):
        cls = (getattr(s, "meta", {}) or {}).get("class")
        if cls == target_class:
            return True, "engaged"
        return False, f"class={cls!r}, want {target_class!r}"
    return can_handle


class TestAuthoritativeDispatch:
    def test_runs_only_engaged_gates(self):
        engaged_gate = Gate(
            name="g_engage",
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=lambda s, c: {"ran": "engage"},
        )
        skipped_gate = Gate(
            name="g_skip",
            phase="POST_FIT",
            can_handle=_engages_only_on_class("nd_features"),
            run=lambda s, c: {"ran": "skip_should_not_appear"},
        )
        cage = Cage([engaged_gate, skipped_gate])
        sub = _SubstrateView(meta=_valid_meta(class_="1d"))

        em, run_results = cage.dispatch_and_run(sub, candidate=None)

        assert "g_engage" in run_results
        assert run_results["g_engage"] == {"ran": "engage"}
        assert "g_skip" not in run_results

    def test_run_exception_recorded_not_propagated(self):
        def bad_run(_s, _c):
            raise RuntimeError("boom")

        good = Gate(
            name="g_good",
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=lambda s, c: {"ok": True},
        )
        bad = Gate(
            name="g_bad",
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=bad_run,
        )
        cage = Cage([good, bad])
        sub = _SubstrateView(meta=_valid_meta())

        em, run_results = cage.dispatch_and_run(sub, candidate=None)

        # Both engaged
        assert em.engagements["g_good"][0] is True
        assert em.engagements["g_bad"][0] is True
        # Good ran, bad reported error — neither propagated
        assert run_results["g_good"] == {"ok": True}
        assert "__error__" in run_results["g_bad"]
        assert "RuntimeError" in run_results["g_bad"]["__error__"]
        assert "boom" in run_results["g_bad"]["__error__"]

    def test_invalid_meta_returns_empty_run_results(self):
        gate = Gate(
            name="g",
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=lambda s, c: {"should_not_run": True},
        )
        cage = Cage([gate])
        sub = _SubstrateView(meta={"class": "1d"})  # missing required keys

        em, run_results = cage.dispatch_and_run(sub, candidate=None)

        assert em.substrate_meta_valid is False
        assert run_results == {}

    def test_one_failing_gate_doesnt_abort_others(self):
        gates = [
            Gate(
                name="g_first",
                phase="POST_FIT",
                can_handle=_engages_universally(),
                run=lambda s, c: 1,
            ),
            Gate(
                name="g_middle_explodes",
                phase="POST_FIT",
                can_handle=_engages_universally(),
                run=lambda s, c: (_ for _ in ()).throw(ValueError("middle")),
            ),
            Gate(
                name="g_last",
                phase="POST_FIT",
                can_handle=_engages_universally(),
                run=lambda s, c: 3,
            ),
        ]
        cage = Cage(gates)
        sub = _SubstrateView(meta=_valid_meta())

        em, run_results = cage.dispatch_and_run(sub, candidate=None)

        # All three engaged
        assert all(em.engagements[g.name][0] for g in gates)
        # First and last produced their values; middle has __error__
        assert run_results["g_first"] == 1
        assert run_results["g_last"] == 3
        assert "__error__" in run_results["g_middle_explodes"]

    def test_default_dispatch_unchanged(self):
        """dispatch() must not execute gates — backwards compat."""
        ran = []
        gate = Gate(
            name="g",
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=lambda s, c: ran.append(1) or "ran",
        )
        cage = Cage([gate])
        sub = _SubstrateView(meta=_valid_meta())

        em = cage.dispatch(sub, candidate=None)
        assert ran == [], "dispatch() must not call gate.run"
        assert em.engagements["g"][0] is True
