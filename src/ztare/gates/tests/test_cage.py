"""GP-157 v5.0 Phase 3 — Cage Orchestrator regression suite.

Verifies:
  - validate_substrate_meta enforces canonical schema (D1, N3, R9 docs)
  - check_feature_coverage_adequacy implements R8
  - check_target_convention_homogeneity implements R9 (gp154 Class K)
  - check_min_rows_per_category implements N4 (gp154 Class F)
  - Cage.topo_order produces deterministic dependency-respecting order
  - Cage.dispatch returns EngagementMatrix with diagnostics
  - D1 fix: missing canonical meta raises sharp ValueError (never silent)
"""
from __future__ import annotations

import pytest
from collections import ChainMap

from src.ztare.gates.cage import (
    Cage,
    EngagementMatrix,
    Gate,
    REQUIRED_SUBSTRATE_META_KEYS,
    check_feature_coverage_adequacy,
    check_min_rows_per_category,
    check_target_convention_homogeneity,
    validate_substrate_meta,
)


# ── Test fixtures ─────────────────────────────────────────────────────


def _good_meta(class_="nd_features", hom="homogeneous", min_rows=3) -> dict:
    return {
        "type": "scaling_law",
        "class": class_,
        "target_convention_homogeneity": hom,
        "min_rows_per_category": min_rows,
        "near_miss_factor": 1.5,
        "frame_invariant_y": True,
    }


class _Substrate:
    def __init__(self, meta: dict):
        self.meta = meta


# ── validate_substrate_meta ──────────────────────────────────────────


def test_validate_meta_accepts_canonical():
    ok, diag = validate_substrate_meta(_good_meta())
    assert ok, f"unexpected reject: {diag}"
    assert diag == []


def test_validate_meta_rejects_missing_keys():
    bad = {"type": "x"}  # missing class, homogeneity, min_rows, etc.
    ok, diag = validate_substrate_meta(bad)
    assert not ok
    # Each missing required key surfaces a diagnostic
    for key in REQUIRED_SUBSTRATE_META_KEYS:
        if key != "type":
            assert any(key in d for d in diag), f"missing diagnostic for {key}"


def test_validate_meta_rejects_invalid_class():
    meta = _good_meta(class_="bogus_class")
    ok, diag = validate_substrate_meta(meta)
    assert not ok
    assert any("bogus_class" in d for d in diag)


def test_validate_meta_rejects_invalid_homogeneity():
    meta = _good_meta(hom="kinda_mixed")
    ok, diag = validate_substrate_meta(meta)
    assert not ok
    assert any("homogeneity" in d.lower() or "kinda_mixed" in d for d in diag)


def test_validate_meta_rejects_chainmap_dict_subclass():
    """N3 nugget: ChainMap and dict subclasses can override __getitem__
    and break dispatcher routing. Must be rejected with diagnostic."""
    cm = ChainMap(_good_meta())
    ok, diag = validate_substrate_meta(cm)
    assert not ok
    # ChainMap is NOT isinstance(dict) so the early "must be a dict" fires.
    # Either way the diagnostic must mention dict.
    assert any("dict" in d.lower() for d in diag)


def test_validate_meta_rejects_dict_subclass():
    """Direct dict subclass also rejected (the pure N3 case)."""
    class _MyDict(dict):
        pass
    md = _MyDict(_good_meta())
    ok, diag = validate_substrate_meta(md)
    assert not ok
    assert any("plain dict" in d.lower() or "subclass" in d.lower() or "_MyDict" in d for d in diag)


def test_validate_meta_rejects_non_dict():
    ok, diag = validate_substrate_meta("not a dict")
    assert not ok
    assert any("dict" in d.lower() for d in diag)


# ── R8: feature-coverage adequacy ────────────────────────────────────


def test_r8_passes_with_full_coverage():
    rows = [(i, 0.5, {"x": 1.0, "y": 2.0}) for i in range(10)]
    ok, diag = check_feature_coverage_adequacy({"x", "y"}, rows)
    assert ok, diag
    assert "ok" in diag.lower()


def test_r8_fails_when_feature_is_none_on_majority():
    """gp154-replica: log10_N_params None on every row → R8 must fail."""
    rows = [(i, 0.5, {"x": 1.0, "log10_N_params": None}) for i in range(10)]
    ok, diag = check_feature_coverage_adequacy({"log10_N_params"}, rows)
    assert not ok
    assert "log10_N_params" in diag
    assert "0.0%" in diag or "0/10" in diag


def test_r8_passes_with_30_percent_coverage():
    """30% threshold: 3/10 populated → exactly at threshold."""
    rows = []
    for i in range(10):
        feats = {"x": 1.0, "log10_N_params": 7.0 if i < 3 else None}
        rows.append((i, 0.5, feats))
    ok, _ = check_feature_coverage_adequacy({"log10_N_params"}, rows)
    assert ok  # 30% inclusive


def test_r8_fails_below_30_percent():
    rows = []
    for i in range(10):
        feats = {"x": 1.0, "log10_N_params": 7.0 if i < 2 else None}
        rows.append((i, 0.5, feats))
    ok, _ = check_feature_coverage_adequacy({"log10_N_params"}, rows)
    assert not ok  # 20% < 30%


# ── R9: target-convention homogeneity ────────────────────────────────


def test_r9_homogeneous_passes_when_all_rows_share_convention():
    s = _Substrate(_good_meta(hom="homogeneous"))
    rows = [(i, 0.5, {"fit_convention": "kaplan_separable"}) for i in range(5)]
    ok, _ = check_target_convention_homogeneity(s, rows, "params['a']")
    assert ok


def test_r9_homogeneous_fails_when_rows_span_conventions():
    """gp154-class failure: rows span Kaplan + Chinchilla + Bahri."""
    s = _Substrate(_good_meta(hom="homogeneous"))
    rows = [
        (1, 0.34, {"fit_convention": "kaplan_separable"}),
        (2, 0.46, {"fit_convention": "chinchilla_isoflop"}),
        (3, 1.00, {"fit_convention": "loss_curve_power"}),
    ]
    ok, diag = check_target_convention_homogeneity(s, rows, "params['a']")
    assert not ok
    assert "homogeneous" in diag
    assert "fit_conventions" in diag


def test_r9_heterogeneous_fails_when_form_lacks_convention_reference():
    """Heterogeneous substrate; form must reference features['fit_convention']."""
    s = _Substrate(_good_meta(hom="heterogeneous"))
    rows = [(1, 0.5, {"fit_convention": "kaplan_separable"})]
    form = "params['a'] * features['x']"  # no fit_convention reference
    ok, diag = check_target_convention_homogeneity(s, rows, form)
    assert not ok
    assert "fit_convention" in diag


def test_r9_heterogeneous_passes_with_convention_reference():
    s = _Substrate(_good_meta(hom="heterogeneous"))
    rows = [(1, 0.5, {"fit_convention": "kaplan_separable"})]
    form = "params['a'] if features['fit_convention'] == 'kaplan_separable' else params['b']"
    ok, _ = check_target_convention_homogeneity(s, rows, form)
    assert ok


def test_r9_fails_if_meta_missing_homogeneity():
    """Substrate without target_convention_homogeneity declaration is rejected."""
    s = _Substrate({"type": "x"})  # missing homogeneity
    rows = [(1, 0.5, {})]
    ok, diag = check_target_convention_homogeneity(s, rows, "params['a']")
    assert not ok
    assert "target_convention_homogeneity" in diag


# ── N4: min_rows_per_category ────────────────────────────────────────


def test_n4_passes_when_all_categories_above_min():
    s = _Substrate(_good_meta(min_rows=3))
    rows = [(i, 0.5, {"mod": "lang"}) for i in range(5)]
    ok, _ = check_min_rows_per_category(s, rows)
    assert ok


def test_n4_advisory_warning_with_sparse_categories():
    """Default behavior: sparse categories produce advisory, not fail."""
    s = _Substrate(_good_meta(min_rows=3))
    rows = [
        (i, 0.5, {"mod": "lang"}) for i in range(5)
    ] + [(99, 0.5, {"mod": "rare"})]  # only 1 row
    ok, diag = check_min_rows_per_category(s, rows)
    assert ok  # advisory only
    assert "rare" in diag and "advisory" in diag


def test_n4_enforce_blocks_when_meta_sets_enforce():
    """When substrate.meta.enforce_min_rows=True, sparse categories
    block engagement."""
    meta = _good_meta(min_rows=3)
    meta["enforce_min_rows"] = True
    s = _Substrate(meta)
    rows = [(i, 0.5, {"mod": "lang"}) for i in range(5)] + [(99, 0.5, {"mod": "rare"})]
    ok, diag = check_min_rows_per_category(s, rows)
    assert not ok
    assert "ENFORCE FAILED" in diag


# ── Cage dispatcher ──────────────────────────────────────────────────


def _stub_can_handle_true(s, c): return True, "engaged"


def _stub_can_handle_false(s, c): return False, "stub_reason"


def _stub_run(s, c): return {"executed": True}


def test_cage_topo_order_respects_dependencies():
    """Gate B depends on A; A must run first."""
    cage = Cage([
        Gate("B", "POST_FIT", _stub_can_handle_true, _stub_run, dependencies=["A"]),
        Gate("A", "PRE_FIT", _stub_can_handle_true, _stub_run),
        Gate("C", "POST_JUDGE", _stub_can_handle_true, _stub_run, dependencies=["B"]),
    ])
    order = cage.topo_order()
    assert order.index("A") < order.index("B") < order.index("C")


def test_cage_detects_dependency_cycle():
    cage = Cage([
        Gate("A", "PRE_FIT", _stub_can_handle_true, _stub_run, dependencies=["B"]),
        Gate("B", "PRE_FIT", _stub_can_handle_true, _stub_run, dependencies=["A"]),
    ])
    with pytest.raises(ValueError, match="cycle"):
        cage.topo_order()


def test_cage_dispatch_runs_can_handle_in_topo_order():
    cage = Cage([
        Gate("first", "PRE_FIT", _stub_can_handle_true, _stub_run),
        Gate("second", "FIT", _stub_can_handle_false, _stub_run, dependencies=["first"]),
    ])
    s = _Substrate(_good_meta())
    em = cage.dispatch(s, "candidate")
    assert em.engagements["first"] == (True, "engaged")
    assert em.engagements["second"] == (False, "stub_reason")
    assert em.topo_order.index("first") < em.topo_order.index("second")


def test_cage_refuses_engagement_when_meta_invalid():
    """D1 fix: bad meta → all gates refuse, with full diagnostic."""
    cage = Cage([
        Gate("g1", "PRE_FIT", _stub_can_handle_true, _stub_run),
    ])
    s = _Substrate({"type": "x"})  # missing required keys
    em = cage.dispatch(s, "candidate")
    assert em.substrate_meta_valid is False
    assert len(em.substrate_meta_diagnostics) > 0
    # Every gate refuses with the meta-invalid reason
    assert em.engagements["g1"][0] is False
    assert "invalid" in em.engagements["g1"][1].lower()


def test_cage_can_handle_with_diagnostic_raises_on_missing_meta():
    """D1 fix part 2: never silently False; raises ValueError."""
    cage = Cage([
        Gate("g1", "PRE_FIT", _stub_can_handle_true, _stub_run),
    ])
    s = _Substrate({})  # no meta keys at all
    with pytest.raises(ValueError, match="schema validation"):
        cage.can_handle_with_diagnostic("g1", s, "candidate")


def test_cage_duplicate_gate_names_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        Cage([
            Gate("g1", "PRE_FIT", _stub_can_handle_true, _stub_run),
            Gate("g1", "FIT", _stub_can_handle_true, _stub_run),
        ])


def test_cage_invalid_phase_rejected():
    with pytest.raises(ValueError, match="phase"):
        Gate("g1", "BOGUS_PHASE", _stub_can_handle_true, _stub_run)


def test_cage_can_handle_exception_captured_not_propagated():
    """If a gate's can_handle raises, dispatch records it but continues."""
    def _raises(s, c):
        raise RuntimeError("synthetic")
    cage = Cage([
        Gate("g1", "PRE_FIT", _raises, _stub_run),
        Gate("g2", "FIT", _stub_can_handle_true, _stub_run),
    ])
    s = _Substrate(_good_meta())
    em = cage.dispatch(s, "candidate")
    # g1 captured the exception
    ok, reason = em.engagements["g1"]
    assert ok is False
    assert "RuntimeError" in reason
    # g2 still ran
    assert em.engagements["g2"] == (True, "engaged")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
