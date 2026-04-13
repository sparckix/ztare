"""GP-048 Math AST Analyzer — unit tests."""

from __future__ import annotations

import pytest

from src.ztare.validator.structural_memory import (
    ExpressionParseError,
    PRIMITIVE_LABELS,
    extract_primitives,
    normalize_expression,
    tree_edit_distance,
)


VARS = ["phi", "psi"]


def _norm(expr: str, params: list[str]):
    return normalize_expression(expr, VARS, params)


# --- primitive extraction ---------------------------------------------------


def test_primitives_pure_polynomial():
    tree = _norm("a * phi**2 + b * phi + c", ["a", "b", "c"])
    prims = extract_primitives(tree)
    assert "power" in prims
    assert "polynomial" in prims
    assert "additive_composition" in prims
    assert "multiplicative_composition" in prims
    assert "exp_neg" not in prims
    assert "exp_pos" not in prims


def test_primitives_exp_decay():
    tree = _norm("a * math.exp(-k * phi)", ["a", "k"])
    prims = extract_primitives(tree)
    assert "exp_neg" in prims
    assert "exp_pos" not in prims
    assert "polynomial" not in prims  # transcendentals present


def test_primitives_exp_positive():
    tree = _norm("a * math.exp(k * phi)", ["a", "k"])
    prims = extract_primitives(tree)
    assert "exp_pos" in prims
    assert "exp_neg" not in prims


def test_primitives_rational_simple():
    tree = _norm("a / phi", ["a"])
    prims = extract_primitives(tree)
    assert "rational_simple" in prims
    assert "rational_with_additive_offset" not in prims


def test_primitives_rational_with_offset():
    tree = _norm("a / (phi + c)", ["a", "c"])
    prims = extract_primitives(tree)
    assert "rational_with_additive_offset" in prims


def test_primitives_sigmoid():
    tree = _norm("1 / (1 + math.exp(-k * phi))", ["k"])
    prims = extract_primitives(tree)
    assert "sigmoid" in prims
    assert "exp_neg" in prims


def test_primitives_log():
    tree = _norm("a * math.log(phi) + c", ["a", "c"])
    prims = extract_primitives(tree)
    assert "log" in prims


def test_primitives_trig():
    tree = _norm("math.sin(phi) + math.cos(psi)", [])
    prims = extract_primitives(tree)
    assert "trig" in prims


def test_primitives_all_in_vocabulary():
    tree = _norm(
        "(A * psi**p) * phi**n * math.exp(-(K * psi**q) * phi**m) + (F * psi**r)",
        ["A", "p", "n", "K", "q", "m", "F", "r"],
    )
    prims = extract_primitives(tree)
    assert prims.issubset(PRIMITIVE_LABELS)
    assert "power" in prims
    assert "exp_neg" in prims
    assert "multiplicative_composition" in prims
    assert "additive_composition" in prims


def test_primitives_constant_detected():
    tree = _norm("a * phi + 0.5", ["a"])
    prims = extract_primitives(tree)
    assert "constant" in prims


# --- tree edit distance -----------------------------------------------------


def test_ted_identical_trees():
    t = _norm("a * phi**2 + b", ["a", "b"])
    assert tree_edit_distance(t, t) == 0


def test_ted_structurally_identical_rename_params():
    t1 = _norm("a * phi**2 + b", ["a", "b"])
    t2 = _norm("x * phi**2 + y", ["x", "y"])
    # normalization collapses a,b → P0,P1 and x,y → P0,P1 -> distance 0
    assert tree_edit_distance(t1, t2) == 0


def test_ted_different_constants_collapse_to_zero():
    t1 = _norm("a * phi + 1.5", ["a"])
    t2 = _norm("a * phi + 3.7", ["a"])
    # both constants collapse to CONST
    assert tree_edit_distance(t1, t2) == 0


def test_ted_small_edit_additive_term():
    t1 = _norm("a * phi**2", ["a"])
    t2 = _norm("a * phi**2 + b", ["a", "b"])
    d = tree_edit_distance(t1, t2)
    assert 1 <= d <= 6


def test_ted_structurally_different_large():
    t1 = _norm("a * phi + b", ["a", "b"])
    t2 = _norm("a * math.exp(-k * phi**2) / (1 + psi)", ["a", "k"])
    assert tree_edit_distance(t1, t2) >= 6


def test_ted_sandbox03_score50_champions_cluster_tight():
    """The three score-50 champions from sandbox_03 iters 13/20/26 should
    cluster tight — they are the basin the GP-023 seam claims exists."""
    iter13 = _norm(
        "(A_amp * (psi**p_A)) * (phi**n_phi) * math.exp(-(k_decay * (psi**p_k)) * (phi**m_decay)) + (I_floor_base * (psi**p_floor))",
        ["A_amp", "p_A", "n_phi", "k_decay", "p_k", "m_decay", "I_floor_base", "p_floor"],
    )
    iter20 = _norm(
        "(A_base * psi**p_A) * phi**(N_base * psi**p_N) * math.exp(-(K_base * psi**p_K) * phi**M_exp) + (F_base * psi**p_F)",
        ["A_base", "p_A", "N_base", "p_N", "K_base", "p_K", "M_exp", "F_base", "p_F"],
    )
    iter26 = _norm(
        "(A_coeff * psi**p_A) * phi**N_exp * math.exp(-(K_coeff * psi**p_K) * phi**M_exp) + (F_coeff * psi**p_F)",
        ["A_coeff", "p_A", "N_exp", "K_coeff", "p_K", "M_exp", "F_coeff", "p_F"],
    )
    d_13_26 = tree_edit_distance(iter13, iter26)
    d_20_26 = tree_edit_distance(iter20, iter26)
    # 13 and 26 have the same structural form modulo renames -> zero
    assert d_13_26 == 0
    # 20 has an extra BinOp in the phi exponent (N_base * psi**p_N)
    # should be small but non-zero
    assert 0 < d_20_26 <= 10


# --- parse errors -----------------------------------------------------------


def test_parse_error_raised():
    with pytest.raises(ExpressionParseError):
        normalize_expression("a + * b", VARS, ["a", "b"])
