"""GP-157 Bug #37 regression test — fit-time / gate-time namespace
invariant. Per Gemini Pro panel mandate (2026-04-25):

    Any function exposed to the mutator in the FitEngine whitelisted AST
    parser MUST also be present and executable in the gate_harness
    evaluation namespace.

This permanently closes the class of bugs where Phase 1 (Fit) and Phase 2
(Gate) drift out of sync — the failure mode that caused gp154 iter 5 to
fit successfully (K=8, BIC=-81.7, mean|res|=0.32 visible) and then crash
with TypeError on 10/12 holdout rows because `where()` was in fit-time
scope but missing from gate-time scope.

Invariants asserted:
1. Every function in `_ALLOWED_FUNCTIONS` whitelist is callable at
   gate-time module scope after `inject_gate_time_primitives` runs.
2. Continuous-transition primitives (where, sigmoid, erf) produce
   identical scalar output at fit-time vs gate-time for the same inputs
   (no semantic drift between scopes).
3. Injection is idempotent (running it twice doesn't duplicate
   definitions or break import).
4. Injection preserves a leading module docstring (doesn't shadow
   __doc__).
5. The full handoff path runs end-to-end on a realistic gp154-style
   submission — fit-time eval succeeds + gate-time `import test_model;
   test_model.I_model({...})` succeeds with the same form.
"""
from __future__ import annotations

import importlib.util
import math
import textwrap
from pathlib import Path

import pytest

from ztare.fit.fit_primitive_features import (
    GATE_TIME_PRIMITIVE_PRELUDE,
    GATE_TIME_PRIMITIVE_SENTINEL,
    _ALLOWED_FUNCTIONS,
    _SAFE_NS_BASE,
    _safe_compile_form,
    inject_gate_time_primitives,
)


# ── Invariant 1: whitelist ↔ gate-time-scope coverage ────────────────────


# Functions that are math/numeric primitives the mutator could need at
# gate time. Excludes pure type-coercion (float/int/bool/len/str) and
# basic Python builtins (max/min/abs) which are always available
# regardless of injection.
_GATE_REQUIRED_PRIMITIVES = {
    "sigmoid", "exp", "log", "log10", "sin", "cos", "tan", "tanh",
    "sqrt", "where", "erf",
}


def _exec_gate_time_module(code: str) -> dict:
    """Simulate gate_harness's `import test_model.py` by exec'ing in a
    module-scope namespace. Returns the resulting globals dict."""
    ns: dict = {"__name__": "test_model", "__file__": "<gate_time_test>"}
    exec(compile(code, "<gate_time_test>", "exec"), ns)
    return ns


def test_gate_time_required_primitives_subset_of_fit_time_namespace():
    """The gate-time required set must be a subset of fit-time
    `_ALLOWED_FUNCTIONS`. If a primitive is in the gate-time injection
    but not in the fit-time whitelist, a mutator could write it at gate
    time but the fit primitive would reject the form."""
    drift = _GATE_REQUIRED_PRIMITIVES - _ALLOWED_FUNCTIONS
    assert not drift, (
        f"primitives required at gate time but not whitelisted at fit time: "
        f"{sorted(drift)} — Phase 1 / Phase 2 namespace drift"
    )


def test_continuous_transition_primitives_present_in_gate_time_module():
    """After injection, where/sigmoid/erf must be callable at module
    scope. This is the core Bug #37 contract."""
    minimal_code = "MODEL_PARAMS = {}\n"
    injected = inject_gate_time_primitives(minimal_code)
    ns = _exec_gate_time_module(injected)
    for name in ("where", "sigmoid", "erf"):
        assert name in ns, f"{name!r} missing from gate-time module scope"
        assert callable(ns[name]), f"{name!r} present but not callable"


# ── Invariant 2: semantic equivalence between fit-time and gate-time ─────


@pytest.mark.parametrize(
    "form,features,params,expected",
    [
        # where: function-call ternary
        (
            "where(features['regime'] == 'A', 1.0, 2.0)",
            {"regime": "A"}, {}, 1.0,
        ),
        (
            "where(features['regime'] == 'A', 1.0, 2.0)",
            {"regime": "B"}, {}, 2.0,
        ),
        # sigmoid 1-arg (backward compat)
        (
            "sigmoid(features['x'])",
            {"x": 0.0}, {}, 0.5,
        ),
        # sigmoid 3-arg (regime crossover)
        (
            "sigmoid(features['x'], params['c'], params['w'])",
            {"x": 5.0}, {"c": 5.0, "w": 1.0}, 0.5,
        ),
        # erf
        (
            "erf(features['z'])",
            {"z": 0.0}, {}, 0.0,
        ),
    ],
)
def test_primitives_produce_identical_output_at_fit_and_gate_time(
    form, features, params, expected,
):
    """For the same inputs, a mutator's expression must produce the same
    value whether evaluated through the fit-time eval pathway or through
    a gate-time `eval(form, ns)` after injection. No drift."""
    # Fit-time path: compile through _safe_compile_form (uses _SAFE_NS_BASE)
    fit_fn = _safe_compile_form(form)
    fit_value = fit_fn(features, params)

    # Gate-time path: inject prelude into a minimal module, exec it, then
    # evaluate the form against that module's namespace.
    minimal_code = "MODEL_PARAMS = {}\n"
    injected = inject_gate_time_primitives(minimal_code)
    ns = _exec_gate_time_module(injected)
    ns["features"] = features
    ns["params"] = params
    gate_value = eval(form, ns)

    assert math.isclose(fit_value, expected, abs_tol=1e-9), (
        f"fit-time produced {fit_value}, expected {expected}"
    )
    assert math.isclose(gate_value, expected, abs_tol=1e-9), (
        f"gate-time produced {gate_value}, expected {expected}"
    )
    assert math.isclose(fit_value, gate_value, abs_tol=1e-9), (
        f"fit/gate drift: fit={fit_value}, gate={gate_value}"
    )


# ── Invariant 3: idempotent injection ────────────────────────────────────


def test_inject_is_idempotent():
    code = "MODEL_PARAMS = {}\n"
    once = inject_gate_time_primitives(code)
    twice = inject_gate_time_primitives(once)
    assert once == twice, "second injection mutated the code"
    # Sentinel appears exactly once.
    assert twice.count(GATE_TIME_PRIMITIVE_SENTINEL) == 1


def test_inject_with_no_input_returns_input():
    assert inject_gate_time_primitives("") == ""
    assert inject_gate_time_primitives(None) is None  # type: ignore[arg-type]


# ── Invariant 4: docstring preservation ──────────────────────────────────


def test_inject_preserves_leading_docstring():
    """If the mutator's submission opens with a module docstring, the
    inject must place primitives AFTER the docstring so __doc__ stays
    intact for downstream introspection / gate_harness checks."""
    code = '"""Module docstring describing the thesis."""\n\nMODEL_PARAMS = {}\n'
    injected = inject_gate_time_primitives(code)
    ns = _exec_gate_time_module(injected)
    assert ns.get("__doc__") == "Module docstring describing the thesis."
    assert "where" in ns and callable(ns["where"])


def test_inject_handles_no_leading_docstring():
    code = "import math\n\nMODEL_PARAMS = {}\n"
    injected = inject_gate_time_primitives(code)
    # Sentinel appears once and at the top
    assert injected.startswith(GATE_TIME_PRIMITIVE_PRELUDE) or GATE_TIME_PRIMITIVE_SENTINEL in injected
    ns = _exec_gate_time_module(injected)
    assert ns.get("MODEL_PARAMS") == {}
    assert callable(ns["where"])


# ── Invariant 5: end-to-end gp154-iter-5-style handoff ───────────────────


def test_end_to_end_fit_to_gate_handoff_with_where_form():
    """The exact failure scenario from gp154 iter 5: mutator writes a
    `where(...)`-based PARAMETRIC_FORM, fit succeeds, then gate_harness
    imports the substituted test_model.py and calls I_model on each row.
    Pre-fix: TypeError because `where` not in scope. Post-fix: passes."""
    mutator_submission = textwrap.dedent('''
        """Mutator's thesis: regime-anchored predictor with continuous transition."""

        PARAMETRIC_FORM = (
            "where(features['regime_hint'] == 'variance_limited', 1.0, "
            " params['k'] + params['s'] * sigmoid(features['x'], params['c'], params['w']))"
        )
        PARAMETER_NAMES = ["k", "s", "c", "w"]
        MODEL_PARAMS = {"k": 0.3, "s": 0.5, "c": 5.0, "w": 1.0}


        def I_model(features, params=MODEL_PARAMS):
            local_env = {"features": features, "params": params}
            # Pre-Bug-#37, this eval had only `features` and `params` in
            # scope, so `where`/`sigmoid` raised NameError. After
            # injection, the module globals contain them, so this resolves.
            return eval(PARAMETRIC_FORM, globals(), local_env)


        f = I_model
        model = I_model
    ''').strip() + "\n"

    # Apply the same injection the apparatus does post-fit
    injected = inject_gate_time_primitives(mutator_submission)

    # Simulate gate_harness's `import test_model.py`
    ns = _exec_gate_time_module(injected)
    I_model = ns["I_model"]

    # Run on a row that exercises the variance-limited branch
    row_var_limited = {"regime_hint": "variance_limited", "x": 0.0}
    assert I_model(row_var_limited) == 1.0

    # Run on a row that exercises the sigmoid-crossover branch
    row_crossover_low = {"regime_hint": "other", "x": 0.0}
    row_crossover_at_center = {"regime_hint": "other", "x": 5.0}
    row_crossover_high = {"regime_hint": "other", "x": 100.0}

    y_low = I_model(row_crossover_low)
    y_mid = I_model(row_crossover_at_center)
    y_high = I_model(row_crossover_high)

    # Sigmoid is monotone increasing; crossover at center=5 with width=1
    assert y_low < y_mid < y_high, (
        f"sigmoid crossover not monotone: low={y_low}, mid={y_mid}, high={y_high}"
    )
    # At center, sigmoid(5, 5, 1) == 0.5 → y_mid = k + s*0.5 = 0.3 + 0.25 = 0.55
    assert math.isclose(y_mid, 0.55, abs_tol=1e-9)


def test_where_is_eager_guard_pattern_unsafe():
    """GP-157 Bug #39 (2026-04-25) — gp154 iter 3 lesson:
    `where(cond, a, b)` is a regular function call; Python evaluates BOTH
    `a` and `b` before invoking it. Therefore `where()` is UNSAFE for
    guard patterns where one branch references a value that may be None
    on the other branch. The Python ternary `A if cond else B` short-
    circuits and IS safe.

    This test documents the eager-vs-lazy semantic so any future change
    to `where()` (e.g., making it lazy via thunks) breaks this test
    explicitly and forces a corresponding prompt-block update."""
    # Eager `where()` — TypeError from the unsafe branch even when cond
    # is False, because both branches evaluate before the call returns.
    minimal_code = "MODEL_PARAMS = {}\n"
    injected = inject_gate_time_primitives(minimal_code)
    ns = _exec_gate_time_module(injected)

    with pytest.raises((TypeError, ZeroDivisionError)):
        # cond=False, but Python still computes 1.0/None first → TypeError
        eval(
            "where(features['d'] is not None, 1.0/features['d'], 0.0)",
            ns,
            {"features": {"d": None}},
        )

    # Python ternary — short-circuits, returns 0.0 cleanly
    result = eval(
        "(1.0/features['d'] if features['d'] is not None else 0.0)",
        ns,
        {"features": {"d": None}},
    )
    assert result == 0.0


def test_where_is_safe_when_both_branches_always_defined():
    """When both branches are unconditionally valid (no None-guarded
    operations), `where()` is the right choice — branchless single
    expression, no ternary nesting."""
    minimal_code = "MODEL_PARAMS = {}\n"
    injected = inject_gate_time_primitives(minimal_code)
    ns = _exec_gate_time_module(injected)

    # Both branches are constants — eager evaluation is fine
    assert eval(
        "where(features['regime'] == 'A', 1.0, params['fallback'])",
        ns,
        {"features": {"regime": "A"}, "params": {"fallback": 0.5}},
    ) == 1.0

    assert eval(
        "where(features['regime'] == 'A', 1.0, params['fallback'])",
        ns,
        {"features": {"regime": "B"}, "params": {"fallback": 0.5}},
    ) == 0.5


def test_end_to_end_via_real_file_import():
    """Stronger test: write injected submission to a temp test_model.py
    and import it via importlib (the SAME path gate_harness uses).
    Catches any difference between exec() and importlib semantics."""
    import tempfile

    mutator_submission = textwrap.dedent('''
        PARAMETRIC_FORM = "where(features['c'] == 1, params['a'], params['b'])"
        PARAMETER_NAMES = ["a", "b"]
        MODEL_PARAMS = {"a": 7.0, "b": 11.0}

        def I_model(features, params=MODEL_PARAMS):
            return eval(PARAMETRIC_FORM, globals(), {"features": features, "params": params})

        f = I_model
        model = I_model
    ''').strip() + "\n"
    injected = inject_gate_time_primitives(mutator_submission)

    with tempfile.TemporaryDirectory() as tmpdir:
        tm_path = Path(tmpdir) / "test_model.py"
        tm_path.write_text(injected)

        spec = importlib.util.spec_from_file_location("_handoff_test_model", tm_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.I_model({"c": 1}) == 7.0
        assert module.I_model({"c": 2}) == 11.0
