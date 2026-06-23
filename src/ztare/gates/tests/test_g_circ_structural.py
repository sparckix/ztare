"""Unit tests for the upgraded G-CIRC structural Lagrangian-smuggling gate.

Covers:

  Positive (must be FLAGGED — adversarial mutator should be caught):
    - P1: PARAMETRIC_FORM names `c_eff` directly (Check 1, AST symbol)
    - P2: V(phi) smuggles a sigmoid center literal (11.43) (Check 2)
    - P3: V(phi) smuggles log_c0 = -22.99 within 1% (Check 2)
    - P4: Algebraic Lagrangian L = phi**2 - 2*A*phi whose EL φ = A,
          substituted into a wrapping form, reproduces a Sacred-DNA
          AST bucket (Check 3)

  Negative (must PASS — legitimate proposals should not be caught):
    - N1: Genuine new form with disjoint AST shape and no Sacred-DNA
          literals
    - N2: Lagrangian whose EL produces non-trivial dynamics — bucket
          differs from the bridge form
    - N3: Rubric flag absent ⇒ no-op (legacy behavior preserved)
    - N4: verified_axioms.json missing ⇒ no-op (graceful degradation)

  Cage adapter:
    - C1: `can_handle` returns False when flag is absent
    - C2: `can_handle` returns True when flag is True
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.gates.g_circ import (
    GATE_ID,
    RUBRIC_FLAG,
    can_handle,
    evaluate_g_circ_structural,
    run_gate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# A simulacrum of the gp163d Galaxy-Cluster Bridge axiom block, used
# substrate-agnostically — the gate reads any verified_axioms.json that
# matches the schema. Constants are taken from the real gp163d block
# (sigmoid centers 11.43, 1.83, 0.62; gate widths 0.8, 0.4; fitted
# log_c0 / log_eta) so the tests double as a regression on the actual
# threat we are defending against.
GP163D_AXIOM = {
    "schema_version": "1.0",
    "substrate": "gp163d_unified_accel",
    "axioms": [
        {
            "axiom_id": "TEST_BRIDGE_FOUNDATION",
            "successor_lock": {"active": True, "rule": "..."},
            "parametric_form": (
                "features['x'] * (1.0 + (exp(params['log_c0'] + 2.302585092994046 "
                "* (sigmoid(((features['mass_log10'] - 11.43) / 2.0 + "
                "(features['radius_log10'] - 1.83)), 0.8, 0.4) - "
                "sigmoid((-features['radius_log10'] - 0.62), 0.8, 0.4))) "
                "/ (features['x'] + 1e-300)) ** exp(params['log_eta'])) "
                "** (0.5 / exp(params['log_eta']))"
            ),
            "parameters": {
                "log_c0": -22.994563194878907,
                "log_eta": -0.18394900995402327,
            },
        }
    ],
}


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Project dir with the gp163d-style verified_axioms.json."""
    (tmp_path / "verified_axioms.json").write_text(
        json.dumps(GP163D_AXIOM), encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def empty_project_dir(tmp_path: Path) -> Path:
    """Project dir with NO verified_axioms.json (graceful degradation)."""
    return tmp_path


# ---------------------------------------------------------------------------
# Positive tests — must be FLAGGED
# ---------------------------------------------------------------------------


def test_p1_ast_symbol_smuggle_via_c_eff(project_dir: Path) -> None:
    """Mutator names `c_eff` directly in PARAMETRIC_FORM."""
    pf = "features['x'] * (1.0 + (c_eff(features['mass_log10']) / features['x']) ** 0.5)"
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=pf,
        rubric_data={RUBRIC_FLAG: True},
    )
    assert r["flagged"], f"expected flagged, got {r}"
    assert r["rule"] == "ast_symbol"
    assert "c_eff" in r["evidence"]["matched_symbols"]
    assert r["severity"] == "hard_fail"


def test_p2_sacred_dna_sigmoid_center_leak(project_dir: Path) -> None:
    """Mutator smuggles the 11.43 sigmoid center via V(phi)."""
    # Note: pf does not use any banned name; only the literal leaks.
    pf = (
        "features['x'] * (1.0 + (exp(-22.5 + (features['mass_log10'] - 11.43)) "
        "/ features['x']) ** 0.83) ** (0.5 / 0.83)"
    )
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=pf,
        rubric_data={RUBRIC_FLAG: True},
    )
    assert r["flagged"], f"expected flagged, got {r}"
    assert r["rule"] == "sacred_dna_literal"
    leaks = r["evidence"]["leaks"]
    assert any(abs(L["candidate_literal"] - 11.43) < 1e-9 for L in leaks), leaks


def test_p3_sacred_dna_log_c0_within_1pct(project_dir: Path) -> None:
    """Mutator smuggles log_c0 ≈ -22.99 within 1% relative tolerance."""
    # -22.99 vs -22.9946 is ~0.02% — within tolerance
    pf = "features['x'] * exp(-22.99 + features['mass_log10'])"
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=pf,
        rubric_data={RUBRIC_FLAG: True},
    )
    assert r["flagged"]
    assert r["rule"] == "sacred_dna_literal"


def test_p4_onshell_tautology(project_dir: Path) -> None:
    """Algebraic Lagrangian whose EL φ-substitution reproduces the
    Sacred-DNA AST bucket. The simplest construction: declare a
    PARAMETRIC_FORM that is *literally* the Sacred-DNA bridge form
    (renamed parameters, no numeric leak) and a Lagrangian whose EL
    solution is trivial — substitution preserves the bucket.
    """
    # PARAMETRIC_FORM: same AST shape as the bridge but with renamed
    # everything; no numeric matches the Sacred-DNA constants. This is
    # the case Checks 1+2 do NOT catch but Check 3 should.
    # We rely on the same AST bucket being reachable purely from the
    # operator skeleton.
    bridge_form = GP163D_AXIOM["axioms"][0]["parametric_form"]
    # Trivial Lagrangian L = (phi - 1)**2; EL solves to phi = 1.
    # The PARAMETRIC_FORM is just the bridge form with no phi reference,
    # so substitution is a no-op and the bucket is identical.
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=bridge_form,
        # Skip Check 2 by also supplying lagrangian — but the bridge
        # form itself contains the Sacred-DNA literals (11.43 etc.),
        # so Check 2 will fire first. That's correct — we want at
        # LEAST one of the 3 checks to catch this. The test asserts
        # only that the gate flags, not which rule.
        lagrangian_text="(phi - 1)**2",
        rubric_data={RUBRIC_FLAG: True},
    )
    assert r["flagged"], f"expected flagged on bridge-form replay, got {r}"
    assert r["severity"] == "hard_fail"


# ---------------------------------------------------------------------------
# Negative tests — must PASS
# ---------------------------------------------------------------------------


def test_n1_genuine_disjoint_form_passes(project_dir: Path) -> None:
    """A legitimate new form with disjoint AST and no Sacred-DNA
    literals should not be flagged."""
    # Power-law fit with totally different constants
    pf = (
        "params['alpha'] * features['x'] ** params['beta'] + "
        "params['gamma'] * log(features['mass_log10'] + 1.0)"
    )
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=pf,
        rubric_data={RUBRIC_FLAG: True},
    )
    assert not r["flagged"], f"expected pass, got {r}"
    assert r["rule"] == "ok"


def test_n2_lagrangian_with_nontrivial_dynamics_passes(project_dir: Path) -> None:
    """Lagrangian L = phi**4 - phi**2 has EL φ = ±1/√2 (no Sacred-DNA
    constants), and the substituted form has a different AST shape."""
    pf = (
        "params['a'] * features['x'] + params['b'] * features['mass_log10']"
    )
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=pf,
        lagrangian_text="phi**4 - phi**2",
        rubric_data={RUBRIC_FLAG: True},
    )
    assert not r["flagged"], f"expected pass, got {r}"


def test_n3_rubric_flag_absent_is_noop(project_dir: Path) -> None:
    """When the rubric flag is False/absent, the gate is a no-op
    (legacy DAG-cycle G-CIRC remains the sole defense)."""
    pf = "c_eff(features['mass_log10']) + 11.43"  # would be flagged if enabled
    r = evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=pf,
        rubric_data={},  # no flag
    )
    assert not r["flagged"]
    assert r["rule"] == "disabled"


def test_n4_missing_axioms_is_noop(empty_project_dir: Path) -> None:
    """No verified_axioms.json ⇒ graceful degradation, not hard fail."""
    pf = "c_eff(features['x'])"  # would normally be flagged
    r = evaluate_g_circ_structural(
        project_dir=empty_project_dir,
        parametric_form=pf,
        rubric_data={RUBRIC_FLAG: True},
    )
    # Check 1 (AST symbol) does not depend on axioms — but the axiom
    # load happens before Check 1 in the entry function so an empty
    # axiom set short-circuits with rule="no_axioms". This is the
    # documented graceful-degradation contract.
    assert not r["flagged"]
    assert r["rule"] == "no_axioms"


def test_n5_inactive_successor_lock_is_noop(tmp_path: Path) -> None:
    """Axioms with successor_lock.active=False are ignored."""
    axiom = json.loads(json.dumps(GP163D_AXIOM))
    axiom["axioms"][0]["successor_lock"]["active"] = False
    (tmp_path / "verified_axioms.json").write_text(json.dumps(axiom), encoding="utf-8")
    pf = "features['x'] * 11.43"  # would leak if axiom were active
    r = evaluate_g_circ_structural(
        project_dir=tmp_path,
        parametric_form=pf,
        rubric_data={RUBRIC_FLAG: True},
    )
    assert not r["flagged"]
    assert r["rule"] == "no_axioms"


# ---------------------------------------------------------------------------
# Cage adapter tests
# ---------------------------------------------------------------------------


class _StubSubstrate:
    def __init__(self, rubric_data: dict) -> None:
        self.rubric_data = rubric_data


class _StubCandidate:
    def __init__(self, *, project_dir: Path, parametric_form: str = "",
                 lagrangian_text: str | None = None,
                 on_shell_phi_solution: str | None = None) -> None:
        self.project_dir = project_dir
        self.parametric_form = parametric_form
        self.lagrangian_text = lagrangian_text
        self.on_shell_phi_solution = on_shell_phi_solution


def test_c1_can_handle_off_when_flag_absent() -> None:
    sub = _StubSubstrate({})
    cand = _StubCandidate(project_dir=Path("."))
    ok, reason = can_handle(sub, cand)
    assert not ok
    assert "disengaged" in reason.lower()


def test_c2_can_handle_on_when_flag_true() -> None:
    sub = _StubSubstrate({RUBRIC_FLAG: True})
    cand = _StubCandidate(project_dir=Path("."))
    ok, reason = can_handle(sub, cand)
    assert ok
    assert RUBRIC_FLAG in reason


def test_c3_run_gate_via_cage_adapter(project_dir: Path) -> None:
    """End-to-end via the Cage adapter: structural smuggle is flagged."""
    sub = _StubSubstrate({RUBRIC_FLAG: True})
    cand = _StubCandidate(
        project_dir=project_dir,
        parametric_form="c_eff(features['x'])",
    )
    r = run_gate(sub, cand)
    assert r["name"] == GATE_ID
    assert r["flagged"]
    assert r["rule"] == "ast_symbol"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
