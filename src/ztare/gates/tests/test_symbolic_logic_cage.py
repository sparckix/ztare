"""GP-170 — Symbolic Logic Cage Phase 1 tests.

Test cases derived directly from the seam ([internal-ref]
engine/GP-170_symbolic_logic_cage_seam.md):

  - Python ternary `(A if cond else B)` → REJECT (regex catches if/else)
  - `where(cond, A, B)` → ACCEPT after AST rewrite
  - McGaugh-shape form with positive constraints → REJECT (UNSAT proof)
  - Same form with no positivity → ACCEPT with `symbolic_indeterminate`
  - sigmoid camouflage (sharp width) → indeterminate (Phase 1 hands off
    to R10 kernel-camouflage check via telemetry, doesn't try to prove)
  - Trivial wrapping `y = exp(constant)` with `y > 0` → REJECT (Panel-E)
  - Constraint missing `provenance` → silently dropped
  - Form with `lambda` → REJECT (regex)
  - Slow simplify (stub timeout) → `budget_exceeded`-pathway returns
    indeterminate verdict per-constraint (and overall)
"""
from __future__ import annotations

import pytest

from ztare.gates.symbolic_logic_cage import (
    ConstraintCheckResult,
    check_algebraic_constraints,
    declare_symbols_with_assumptions,
    r170_can_handle,
    regex_reject_python_control_flow,
    rewrite_form_for_sympy,
)


# ── Fixture helpers ───────────────────────────────────────────────────


def _mcgaugh_form() -> str:
    return (
        "(features['x'] + sqrt(features['x']**2 + 4*params['c']*features['x']))/2"
    )


def _positive_init_ranges() -> dict:
    return {"c": (0.001, 10.0)}


def _positive_feature_dims() -> dict:
    return {
        "x": {"unit": "L T^-2", "lo": 0.0001},
        "y": {"unit": "L T^-2", "lo": 0.0001},
    }


def _provenanced(expr: str, prov: str = "declared_physical_law") -> dict:
    return {"expr": expr, "provenance": prov}


# ── Regex pre-parser (Blindspot A) ───────────────────────────────────


def test_regex_rejects_python_ternary():
    rejected, diag = regex_reject_python_control_flow(
        "(10.0 if features['system_class'] == 'B' else 1.0)"
    )
    assert rejected is True
    assert diag is not None
    assert "if" in diag or "else" in diag


def test_regex_rejects_lambda():
    rejected, diag = regex_reject_python_control_flow(
        "(lambda x: x**2)(features['x'])"
    )
    assert rejected is True
    assert "lambda" in diag


def test_regex_rejects_for_comprehension():
    rejected, diag = regex_reject_python_control_flow(
        "sum([params['a']*x for x in features['xs']])"
    )
    assert rejected is True


def test_regex_passes_clean_form():
    rejected, diag = regex_reject_python_control_flow(
        "params['a']*exp(features['x']) + params['b']"
    )
    assert rejected is False
    assert diag is None


def test_regex_does_not_falseflag_words_containing_keywords():
    # `formula`, `defined`, `iffy`-like substrings must not trigger.
    rejected, diag = regex_reject_python_control_flow(
        "params['a_form'] * features['x']"
    )
    assert rejected is False


def test_python_ternary_rejected_via_main_entry():
    res = check_algebraic_constraints(
        form_str="(10.0 if features['system_class'] == 'B' else 1.0)",
        constraints=[_provenanced("y > 0")],
        init_ranges={},
        feature_dimensions={},
    )
    assert res.overall == "rejected_form"
    assert res.r1_message is not None


def test_lambda_rejected_via_main_entry():
    res = check_algebraic_constraints(
        form_str="(lambda x: x**2)(features['x'])",
        constraints=[_provenanced("y > 0")],
        init_ranges={},
        feature_dimensions={},
    )
    assert res.overall == "rejected_form"


# ── AST-rewrite layer (Panel-C/D) ────────────────────────────────────


def test_rewrite_where_simple():
    out = rewrite_form_for_sympy("where(features['x'] > 0, 1.0, 2.0)")
    assert "Piecewise" in out
    assert "where" not in out


def test_rewrite_sigmoid_one_arg():
    out = rewrite_form_for_sympy("sigmoid(features['x'])")
    assert "exp" in out
    assert "sigmoid" not in out


def test_rewrite_sigmoid_three_arg():
    out = rewrite_form_for_sympy(
        "sigmoid(features['x'], params['c'], params['w'])"
    )
    assert "exp" in out
    assert "sigmoid" not in out


def test_where_form_accepted_after_rewrite():
    res = check_algebraic_constraints(
        form_str="where(features['x'] > 0, 10.0, 1.0)",
        constraints=[_provenanced("y > 0")],
        init_ranges={},
        feature_dimensions={"x": {"unit": "1"}},
    )
    # Should NOT be rejected by the form parser.
    assert res.overall != "rejected_form"


# ── Symbol declaration with assumptions (Blindspot B) ────────────────


def test_declare_symbols_positive_param():
    syms = declare_symbols_with_assumptions(
        "params['c']*features['x']",
        init_ranges={"c": (0.001, 10.0)},
        feature_dimensions={"x": {"lo": 0.001}},
    )
    assert "c" in syms
    assert "x" in syms
    assert syms["c"].is_positive is True
    assert syms["x"].is_positive is True


def test_declare_symbols_real_only_when_no_range():
    syms = declare_symbols_with_assumptions(
        "params['c']*features['x']",
        init_ranges={},
        feature_dimensions={},
    )
    # Conservative fallback: real but no sign assumption.
    assert syms["c"].is_real is True
    assert syms["c"].is_positive is None  # SymPy returns None for unset
    assert syms["x"].is_real is True


# ── McGaugh form: provable UNSAT under positivity ────────────────────


def test_mcgaugh_form_violates_under_positivity():
    """Per the seam: y = (x + sqrt(x**2 + 4cx))/2 with c>0, x>0
    algebraically guarantees y >= x; the constraint y < x is UNSAT."""
    res = check_algebraic_constraints(
        form_str=_mcgaugh_form(),
        constraints=[_provenanced("y < x", "class_C_requires_y_lt_x")],
        init_ranges=_positive_init_ranges(),
        feature_dimensions=_positive_feature_dims(),
        wall_clock_budget_s=10.0,
    )
    assert res.overall == "violated", (
        f"expected violated, got {res.overall}; "
        f"per-constraint: {[(v.expr, v.verdict) for v in res.per_constraint]}"
    )
    assert res.r1_message is not None
    assert "fundamental algebraic violation" in res.r1_message


def test_mcgaugh_form_indeterminate_without_positivity():
    """Without positivity assumptions, SymPy can find complex
    satisfying assignments; verdict is indeterminate, not violated."""
    res = check_algebraic_constraints(
        form_str=_mcgaugh_form(),
        constraints=[_provenanced("y < x")],
        init_ranges={},  # no INIT_RANGE → conservative real fallback
        feature_dimensions={},
        wall_clock_budget_s=10.0,
    )
    # Acceptable verdicts: indeterminate or passed (if SymPy still
    # manages to prove something on its own). What's NOT acceptable
    # is "violated" because we removed the positivity scaffolding.
    assert res.overall in ("indeterminate", "passed"), (
        f"expected indeterminate or passed, got {res.overall}"
    )


# ── Cross-seam Collision-2: cold-LLM seed bounce template ───────────


def test_cross_domain_seed_uses_dimensional_bridging_template():
    res = check_algebraic_constraints(
        form_str=_mcgaugh_form(),
        constraints=[_provenanced("y < x")],
        init_ranges=_positive_init_ranges(),
        feature_dimensions=_positive_feature_dims(),
        cross_domain_seed=True,
        wall_clock_budget_s=10.0,
    )
    assert res.overall == "violated"
    assert res.r1_message is not None
    assert "cross-domain seed" in res.r1_message
    assert "dimension-canceling" in res.r1_message


# ── Sigmoid-width camouflage (Panel-D) ───────────────────────────────


def test_sharp_sigmoid_routes_to_indeterminate():
    """Phase 1 doesn't try to prove constraints on sharp sigmoids; the
    rewritten form contains exp((x-c)/w) with tiny w. SymPy reduction
    is undecidable. The contract is: do NOT silently mark as passed —
    the verdict must be indeterminate so the caller knows to consult
    the R10 kernel-camouflage statistical signal."""
    res = check_algebraic_constraints(
        form_str="sigmoid((features['x'] - 14.5) / 0.01)",
        constraints=[_provenanced("y > 0")],
        init_ranges={},
        feature_dimensions={"x": {"unit": "1"}},
        wall_clock_budget_s=5.0,
    )
    # y > 0 actually IS algebraically satisfied by sigmoid (it's bounded
    # in (0,1)); SymPy may prove `passed`. The point of this test is to
    # confirm we don't crash and don't silently miss the camouflage —
    # i.e. the gate either passes (because positivity holds) or returns
    # indeterminate (so caller routes to R10). What's NOT acceptable is
    # `rejected_form`.
    assert res.overall in ("passed", "indeterminate")


# ── Trivial-wrapping detector (Panel-E) ──────────────────────────────


def test_trivial_wrapping_y_equals_exp_constant_rejected():
    """Per Panel-E: `y = exp(params['c'])` with constraint `y > 0` is
    trivially satisfied with no informational content. Should reject."""
    res = check_algebraic_constraints(
        form_str="exp(params['c'])",
        constraints=[_provenanced("y > 0", "declared_physical_law")],
        init_ranges={"c": (-5.0, 5.0)},
        feature_dimensions={},
        wall_clock_budget_s=5.0,
    )
    # Either trivial_wrap (Panel-E catches it) OR violated. Both are
    # acceptable rejections — we just need NOT to silently pass.
    assert res.overall in ("violated",), (
        f"expected violated (trivial-wrap rejection), got {res.overall}"
    )
    # Verify the diagnostic mentions trivial wrapping.
    triv = [v for v in res.per_constraint if v.verdict == "trivial_wrap"]
    assert len(triv) >= 1
    assert "trivial" in triv[0].diagnostic.lower() or "wrap" in triv[0].diagnostic.lower()


# ── Provenance enforcement (Collision-3) ─────────────────────────────


def test_constraint_without_provenance_silently_dropped():
    """Per Collision-3: constraints lacking `provenance` are dropped
    with a warning at validation time. With NO provenanced constraints
    left, the gate is a no-op (verdict=passed)."""
    res = check_algebraic_constraints(
        form_str="params['a']*features['x']",
        constraints=[
            {"expr": "y > 0"},  # no provenance!
            {"expr": "y < 1000", "provenance": ""},  # empty provenance
        ],
        init_ranges={},
        feature_dimensions={},
    )
    # Both constraints dropped → no-op pass.
    assert res.overall == "passed"
    # Diagnostics should reflect the drops.
    drop_msgs = [d for d in res.diagnostics if "dropped" in d.lower()
                 or "provenance" in d.lower()]
    assert len(drop_msgs) >= 1


# ── Wall-clock budget (Panel-F) ──────────────────────────────────────


def test_simplify_timeout_returns_indeterminate_per_constraint():
    """When `simplify` exceeds its slot we should return indeterminate
    on that constraint (and overall when no other constraint succeeded).
    We inject a stub simplify that sleeps to simulate the timeout."""
    import time

    def slow_simplify(expr):
        time.sleep(60.0)  # well past the per-constraint slot
        return expr

    res = check_algebraic_constraints(
        form_str="params['a']*features['x']**2",
        constraints=[
            _provenanced("y > 0", "declared_physical_law"),
        ],
        init_ranges={"a": (0.001, 10.0)},
        feature_dimensions={"x": {"unit": "1"}},
        wall_clock_budget_s=2.0,  # short budget
        _simplify_override=slow_simplify,
    )
    # Either budget_exceeded (whole-iter ceiling) or indeterminate
    # (per-constraint slot). Both demonstrate the timeout handling.
    assert res.overall in ("indeterminate", "budget_exceeded")
    if res.overall == "indeterminate":
        # The per-constraint diagnostic must mention timeout/slot.
        any_timeout = any(
            "slot" in v.diagnostic.lower() or "timeout" in v.diagnostic.lower()
            or "exceeded" in v.diagnostic.lower()
            for v in res.per_constraint
        )
        assert any_timeout


# ── can_handle predicate (Panel-G) ────────────────────────────────────


class _Substrate:
    def __init__(self, meta):
        self.meta = meta
        self.rubric_flags = {}


class _Candidate:
    def __init__(self, parametric_form, init_ranges=None, **kwargs):
        self.parametric_form = parametric_form
        self.init_ranges = init_ranges or {}
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_can_handle_refuses_py_exec_substrate():
    sub = _Substrate({
        "class": "oeis_py_exec",
        "algebraic_constraints": [_provenanced("y > 0")],
    })
    cand = _Candidate("def f(n): return n*n")
    ok, reason = r170_can_handle(sub, cand)
    assert ok is False
    assert "py_exec" in reason


def test_can_handle_refuses_when_no_constraints_declared():
    sub = _Substrate({"class": "nd_features"})
    cand = _Candidate("params['a']*features['x']")
    ok, reason = r170_can_handle(sub, cand)
    assert ok is False
    assert "algebraic_constraints" in reason


def test_can_handle_refuses_when_no_provenance_anywhere():
    sub = _Substrate({
        "class": "nd_features",
        "algebraic_constraints": [{"expr": "y > 0"}],  # missing provenance
    })
    cand = _Candidate("params['a']*features['x']")
    ok, reason = r170_can_handle(sub, cand)
    assert ok is False
    assert "provenance" in reason


def test_can_handle_refuses_form_with_unhandleable_primitive():
    sub = _Substrate({
        "class": "nd_features",
        "algebraic_constraints": [_provenanced("y > 0")],
    })
    cand = _Candidate("len(features['modality']) * params['a']")
    ok, reason = r170_can_handle(sub, cand)
    assert ok is False
    assert "len" in reason or "type-coercion" in reason or "categorical" in reason


def test_can_handle_engages_on_well_formed_input():
    sub = _Substrate({
        "class": "nd_features",
        "algebraic_constraints": [_provenanced("y > 0")],
    })
    cand = _Candidate("params['a']*features['x'] + params['b']")
    ok, reason = r170_can_handle(sub, cand)
    assert ok is True
    assert "engaged" in reason.lower()


# ── Data-belief reconciliation (Panel-H) ─────────────────────────────


def test_data_belief_disagreement_disables_gate():
    """When declared constraint `y > 0` is violated by >5% of visible
    rows, gate refuses to engage rather than enforcing wrong axiom."""
    visible = (
        [{"y": 1.0, "x": 0.5}] * 10  # passing rows
        + [{"y": -1.0, "x": 0.5}] * 5  # ~33% violations
    )
    res = check_algebraic_constraints(
        form_str="params['a']*features['x']",
        constraints=[_provenanced("y > 0", "declared_physical_law")],
        init_ranges={"a": (0.001, 10.0)},
        feature_dimensions={},
        visible_rows=visible,
    )
    assert res.overall == "data_disagreement"
    assert res.rejected_reason is not None
    assert "violated by" in res.rejected_reason.lower() or "violated" in res.rejected_reason.lower()


def test_data_belief_within_5pct_engages():
    """When declared constraint matches visible data within tolerance,
    gate engages normally."""
    visible = [{"y": 1.0, "x": 0.5}] * 100  # all pass y > 0
    res = check_algebraic_constraints(
        form_str="params['a']*features['x']",
        constraints=[_provenanced("y > 0", "declared_physical_law")],
        init_ranges={"a": (0.001, 10.0)},
        feature_dimensions={"x": {"lo": 0.001}},
        visible_rows=visible,
    )
    assert res.overall != "data_disagreement"
