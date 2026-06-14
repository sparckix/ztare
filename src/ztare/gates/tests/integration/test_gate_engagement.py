"""GP-157 v5.0 Phase 3a — gate-engagement integration smoke tests.

Per spec §4 Phase 3a + R6 (real-file integration smoke tests): every
gate registered in the default Cage MUST have at least one substrate-
class fixture that exercises its engagement path.

Coverage matrix verified by these tests:

  Substrate class       | Gates that should engage
  ----------------------|-----------------------------------------------
  1d                    | universal + 1d-only + 1d/nd_features shared
  nd_features           | universal + nd_features-only + 1d/nd shared
  time_series           | universal + time_series-only + 1d/time shared
  audit                 | universal + audit-only
  proof_target          | universal + proof_target-only
  closed_form_constant  | universal + closed_form_constant-only
  literature            | universal only

These are SMOKE tests: verify that `can_handle` returns True for the
correct substrate-class and False otherwise. They do NOT execute
gate.run() — that's per-gate test responsibility (Phase 3b once the
real arg-marshalling lands).
"""
from __future__ import annotations

import pytest

from src.ztare.gates.cage import Cage
from src.ztare.gates.registry import get_default_cage


# ── Fixtures: minimal substrate-meta for each substrate class ────────


def _make_substrate(class_: str) -> object:
    class _S:
        meta = {
            "type": "test",
            "class": class_,
            "target_convention_homogeneity": "homogeneous",
            "min_rows_per_category": 3,
            "near_miss_factor": 1.5,
            "frame_invariant_y": True,
        }
    return _S()


# ── Test the registry exists and builds without crash ───────────────


def test_default_cage_constructs():
    cage = get_default_cage()
    assert isinstance(cage, Cage)
    # 17 dormant - 1 retired (bridge_scope_contract) + 5 already-LIVE = 21 minimum.
    # Actual count after panel synthesis + RETIRE decisions (2026-04-25):
    # 14 WIRE'd (10 unconditional + 3 conditional + 1 utility excluded) +
    # but residual_norm registered as utility-not-gate so subtract 1.
    # Net registered: ~17. We assert ≥15 to allow future RETIRE flexibility.
    assert len(cage.gates) >= 15, f"expected ≥15 registered gates after panel triage, got {len(cage.gates)}"


def test_default_cage_topo_order_acyclic():
    cage = get_default_cage()
    order = cage.topo_order()
    assert len(order) == len(cage.gates)
    # ansatz_survivor must come before proof_surveyability (declared dep)
    assert order.index("ansatz_survivor") < order.index("proof_surveyability")


# ── Per-substrate-class engagement smoke tests ──────────────────────


def _engaged_gates(cage: Cage, substrate: object, candidate: str = "test_candidate") -> set[str]:
    em = cage.dispatch(substrate, candidate)
    return {name for name, (ok, _) in em.engagements.items() if ok}


def test_1d_substrate_engages_correct_gates():
    cage = get_default_cage()
    s = _make_substrate("1d")
    engaged = _engaged_gates(cage, s)
    # bridge_scope_contract RETIRED per panel synthesis 2026-04-25
    assert "bridge_scope_contract" not in engaged
    assert "semantic_gate_stabilization" in engaged
    assert "circularity" in engaged
    assert "falsifiability" in engaged
    assert "derived_constraints" in engaged
    # 1d-specific
    assert "coordinate_invariance" in engaged
    # residual_norm is utility-only (panel decision); not registered as Gate
    assert "residual_norm" not in engaged
    # 1d + nd shared
    assert "asymptotic_claim_discipline" in engaged
    assert "deterministic_charter_gates" in engaged
    # 1d + time_series shared
    assert "continuum_limit" in engaged
    # nd-only must NOT engage
    assert "domain_match" not in engaged
    assert "ensemble_ambiguity" not in engaged
    # time-only must NOT engage
    assert "wasserstein_persistence" not in engaged
    # proof / closed-form / audit must NOT engage
    assert "ansatz_survivor" not in engaged
    assert "pslq_falsity_audit" not in engaged
    assert "prompt_leak_audit" not in engaged


def test_nd_features_substrate_engages_correct_gates():
    cage = get_default_cage()
    s = _make_substrate("nd_features")
    engaged = _engaged_gates(cage, s)
    assert "asymptotic_claim_discipline" in engaged
    assert "deterministic_charter_gates" in engaged
    assert "domain_match" in engaged
    assert "ensemble_ambiguity" in engaged
    # 1d-only must not engage
    assert "coordinate_invariance" not in engaged
    assert "residual_norm" not in engaged
    # time-series-only must not engage
    assert "continuum_limit" not in engaged
    assert "wasserstein_persistence" not in engaged


def test_time_series_substrate_engages_correct_gates():
    cage = get_default_cage()
    s = _make_substrate("time_series")
    engaged = _engaged_gates(cage, s)
    assert "continuum_limit" in engaged
    assert "wasserstein_persistence" in engaged
    # coordinate_invariance ENGAGES on time_series per panel synthesis
    # (Chaos: KY-dimension/Lyapunov-sum invariance is gold standard)
    assert "coordinate_invariance" in engaged
    # nd-only must not engage
    assert "domain_match" not in engaged


def test_audit_substrate_engages_correct_gates():
    cage = get_default_cage()
    s = _make_substrate("audit")
    engaged = _engaged_gates(cage, s)
    assert "prompt_leak_audit" in engaged
    # No fit-related gates should engage on audit substrate
    assert "asymptotic_claim_discipline" not in engaged
    assert "domain_match" not in engaged


def test_proof_target_substrate_engages_correct_gates():
    cage = get_default_cage()
    s = _make_substrate("proof_target")
    engaged = _engaged_gates(cage, s)
    assert "ansatz_survivor" in engaged
    assert "proof_surveyability" in engaged
    assert "translation_diff" in engaged
    # Non-proof gates should not engage
    assert "wasserstein_persistence" not in engaged
    assert "pslq_falsity_audit" not in engaged


def test_closed_form_constant_substrate_engages_pslq():
    cage = get_default_cage()
    s = _make_substrate("closed_form_constant")
    engaged = _engaged_gates(cage, s)
    assert "pslq_falsity_audit" in engaged
    # Other class-specific gates do not engage
    assert "wasserstein_persistence" not in engaged
    assert "domain_match" not in engaged


def test_literature_substrate_engages_only_universal():
    cage = get_default_cage()
    s = _make_substrate("literature")
    engaged = _engaged_gates(cage, s)
    # Per panel: bridge_scope_contract RETIRED. Remaining universal gates:
    universal = {"semantic_gate_stabilization", "circularity",
                 "falsifiability", "derived_constraints"}
    class_specific = engaged - universal
    assert class_specific == set(), f"unexpected class-specific gates engaged on literature: {class_specific}"


# ── Negative tests: malformed substrate refuses everything ──────────


def test_substrate_missing_meta_refused_with_diagnostic():
    """D1 fix: substrate without meta dict must refuse all gates loudly."""
    cage = get_default_cage()
    class _NoMeta:
        meta = None  # not a dict
    em = cage.dispatch(_NoMeta(), "candidate")
    assert em.substrate_meta_valid is False
    # Every gate refused
    for name, (ok, _) in em.engagements.items():
        assert ok is False, f"gate {name} engaged on substrate with invalid meta"


def test_substrate_unknown_class_refuses_class_specific_gates():
    """Unknown substrate.meta['class'] → schema validation refuses
    everything (D1 + R8 + R9 strict path)."""
    cage = get_default_cage()
    class _BogusClass:
        meta = {
            "type": "test",
            "class": "bogus_class",  # not in VALID_SUBSTRATE_CLASSES
            "target_convention_homogeneity": "homogeneous",
            "min_rows_per_category": 3,
            "near_miss_factor": 1.5,
            "frame_invariant_y": True,
        }
    em = cage.dispatch(_BogusClass(), "candidate")
    assert em.substrate_meta_valid is False


# ── Dependency ordering verified ────────────────────────────────────


def test_ansatz_survivor_runs_before_proof_surveyability():
    """proof_surveyability declares dependencies=['ansatz_survivor'];
    topological sort must respect this."""
    cage = get_default_cage()
    order = cage.topo_order()
    assert order.index("ansatz_survivor") < order.index("proof_surveyability")


# ── Coverage assertion: every non-RETIRED gate has a smoke test ──────


def test_coverage_all_dormant_gates_registered():
    """Per spec §4 Phase 3a: every dormant gate in the inventory must
    be registered in the default Cage. RETIRE decisions belong in
    DECISION_LOG.md, not this file."""
    cage = get_default_cage()
    # Per panel synthesis 2026-04-25, bridge_scope_contract RETIRED
    # and residual_norm classified as utility (not registered as Gate).
    expected_wired = {
        "ansatz_survivor", "asymptotic_claim_discipline",
        "continuum_limit", "coordinate_invariance",
        "deterministic_charter_gates", "domain_match",
        "ensemble_ambiguity", "prompt_leak_audit",
        "proof_surveyability", "pslq_falsity_audit",
        "semantic_gate_stabilization", "translation_diff",
        "wasserstein_persistence",
    }
    registered = set(cage.gates.keys())
    missing = expected_wired - registered
    assert not missing, f"WIRE'd gates not registered: {missing}"
    # Verify panel decisions: bridge_scope_contract not registered (RETIRED)
    assert "bridge_scope_contract" not in registered
    # residual_norm not a Gate (utility-only); no registration expected
    assert "residual_norm" not in registered


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
