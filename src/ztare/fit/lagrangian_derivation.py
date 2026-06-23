"""GP-180 Lagrangian Derivation Primitive.

The architectural pivot from curve-fitter to derivator. The mutator no
longer guesses a closed-form; it declares an action principle. The
apparatus uses sympy to:

  1. Compute Euler-Lagrange equations from the declared Lagrangian.
  2. Solve those equations in steady state for the dynamical fields.
  3. Substitute the steady-state solution into the prediction expression
     to obtain a closed-form g_obs(features).
  4. Apply Noether's theorem to each declared continuous symmetry to
     extract conserved quantities.

The closed-form is the OUTPUT of derivation. The fit only adjusts the
declared dimensionful constants. The Noether invariants enter the loss
as variance terms — a real conservation law has zero variance across
the substrate.

Mutator output contract for invariant_search rubric mode:

    LAGRANGIAN = "T - V"                    # sympy expression in q, q_dot, t, features, params
    Q_VARIABLES = ["q"]                      # dynamical fields
    BACKGROUND = ["x", "radius_log10", ...]  # background features used in L
    PREDICTION = "g_obs_expr_in_q_and_features"  # how y_pred is read off the fields
    SYMMETRIES = ["time_translation", "rotation"]  # declared continuous symmetries

Apparatus derives:
  - eom: list of E-L equations
  - steady_state: dict q -> expression in features+params
  - closed_form: g_obs_expr after substituting steady_state
  - noether: dict symmetry -> conserved-quantity expression

If any step fails, the primitive returns success=False with a structural
error message. The caller (autoresearch_loop dispatch) falls back to
PARAMETRIC_FORM mode so the existing pipeline continues to operate.

Limitations
-----------
- Steady-state solving uses sympy's `solve` and `dsolve` which are
  reliable for algebraic and first-order ODEs but can return
  unevaluated `RootOf` for high-degree polynomials.
- Noether invariant extraction is implemented for common symmetries
  (time-translation → energy, spatial-translation → momentum,
  rotation → angular momentum, scale-invariance → dilatation current).
  Custom symmetries are treated as named-only (no automatic derivation).
- Only single-field, single-spatial-dim Lagrangians are robustly
  supported in this MVP. Multi-field is best-effort.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import sympy as sp
    from sympy import symbols, Function, Symbol, diff, solve, simplify, Eq
    _SYMPY_OK = True
except ImportError:
    _SYMPY_OK = False

logger = logging.getLogger("gp180")


@dataclass
class DerivationResult:
    success: bool
    closed_form: Optional[str] = None        # sympy expr → str of g_obs(features, params)
    closed_form_callable_src: Optional[str] = None  # python source of f(features, params) -> y
    eom: list[str] = field(default_factory=list)
    steady_state: dict[str, str] = field(default_factory=dict)
    noether: dict[str, str] = field(default_factory=dict)
    declared_symmetries: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    # GP-183 C3: classification of the derivation's structural content.
    # "non_trivial"     — steady state references ≥2 background symbols
    #                     OR a non-identity transformation of one.
    # "single_substitution" — steady state is `q = bare_background_var`
    #                         (the iter-2 false-positive class).
    # "params_only"     — steady state references only declared params,
    #                     no substrate features (informational).
    # None              — derivation failed or no steady state.
    triviality_kind: Optional[str] = None


# Names recognized as continuous symmetries → conserved-quantity recipe.
# The recipes assume Lagrangian L = L(q, q̇, t).
_NOETHER_RECIPES: dict[str, dict[str, str]] = {
    "time_translation":   {"current": "q_dot * dL/dq_dot - L",   "name": "energy"},
    "spatial_translation":{"current": "dL/dq_dot",                 "name": "momentum"},
    "rotation":           {"current": "q * dL/dq_dot - q_dot * dL/dq", "name": "angular_momentum"},
    "scale_invariance":   {"current": "q * dL/dq_dot - lambda * t * (q_dot * dL/dq_dot - L)", "name": "dilatation_current"},
}


def _euler_lagrange(lagrangian: sp.Expr, q: sp.Function, t: sp.Symbol) -> sp.Expr:
    """Compute E-L equation for a single dynamical field q(t).

    EL: ∂L/∂q − d/dt(∂L/∂q̇) = 0
    """
    q_t = q(t)
    q_dot = q_t.diff(t)
    dL_dq = sp.diff(lagrangian, q_t)
    dL_dqd = sp.diff(lagrangian, q_dot)
    eom = sp.simplify(dL_dq - sp.diff(dL_dqd, t))
    return eom


def _solve_steady_state(eom: sp.Expr, q: sp.Function, t: sp.Symbol) -> Optional[sp.Expr]:
    """Solve E-L equation in steady state: q̇ = q̈ = 0.

    Replaces all time-derivatives of q with 0 and solves for q.
    Returns None if no algebraic solution.
    """
    q_t = q(t)
    q_dot = q_t.diff(t)
    q_ddot = q_dot.diff(t)
    static_eom = eom.subs([(q_ddot, 0), (q_dot, 0)])
    if static_eom == 0:
        return None
    # Replace q(t) by a plain symbol for solving
    q_sym = sp.Symbol(f"_{q.__name__}_steady")
    eq_for_solve = static_eom.subs(q_t, q_sym)
    try:
        sols = sp.solve(eq_for_solve, q_sym, dict=False)
        if not sols:
            return None
        # Pick first real-looking solution
        for s in sols:
            if not s.has(sp.I):
                return s
        return sols[0]
    except (NotImplementedError, sp.SolveError) as exc:
        logger.warning(f"steady-state solve failed: {exc}")
        return None


def _noether_invariant(
    symmetry: str,
    lagrangian: sp.Expr,
    q: sp.Function,
    t: sp.Symbol,
) -> Optional[sp.Expr]:
    """Compute conserved current from declared symmetry.

    Returns None if the symmetry isn't in the known recipe table or the
    derivation hits a sympy limitation.
    """
    recipe = _NOETHER_RECIPES.get(symmetry)
    if recipe is None:
        return None
    q_t = q(t)
    q_dot = q_t.diff(t)
    dL_dqd = sp.diff(lagrangian, q_dot)
    dL_dq = sp.diff(lagrangian, q_t)
    if symmetry == "time_translation":
        # H = q̇ ∂L/∂q̇ − L (energy)
        return sp.simplify(q_dot * dL_dqd - lagrangian)
    if symmetry == "spatial_translation":
        return sp.simplify(dL_dqd)
    if symmetry == "rotation":
        return sp.simplify(q_t * dL_dqd - q_dot * dL_dq)
    if symmetry == "scale_invariance":
        # Approximate: q ∂L/∂q̇ − λ·t·H, λ scaling weight (default 1).
        H = q_dot * dL_dqd - lagrangian
        return sp.simplify(q_t * dL_dqd - sp.Symbol("lambda_scale") * t * H)
    return None


def derive_from_action(
    lagrangian_expr: str,
    q_variables: list[str],
    background: list[str],
    prediction_expr: str,
    symmetries: Optional[list[str]] = None,
    param_names: Optional[list[str]] = None,
) -> DerivationResult:
    """Run the full derivation pipeline.

    Parameters
    ----------
    lagrangian_expr : str
        sympy-parseable expression. May reference q (single field) and q_dot,
        a time symbol t, background symbols (`features['x']` style ALSO
        accepted via symbol named `feat_x` etc.), and param symbols.
    q_variables : list[str]
        Names of dynamical fields. MVP supports exactly one.
    background : list[str]
        Feature keys the Lagrangian depends on (passed as background
        symbols, not differentiated).
    prediction_expr : str
        sympy expression for g_obs in terms of q, background, params.
        After steady-state q is solved, this is reduced to g_obs(background, params).
    symmetries : list[str]
        Declared continuous symmetries; each is mapped via _NOETHER_RECIPES.
    param_names : list[str]
        Free parameters that survive into the closed form (these are the
        ONLY things SciPy fits).

    Returns
    -------
    DerivationResult.
    """
    if not _SYMPY_OK:
        return DerivationResult(success=False, error_message="sympy not importable")
    if len(q_variables) != 1:
        return DerivationResult(
            success=False,
            error_message=f"MVP supports exactly one dynamical field; got {q_variables}",
        )

    q_name = q_variables[0]
    symmetries = list(symmetries or [])
    param_names = list(param_names or [])

    # Build the symbol table.
    t = sp.Symbol("t", real=True)
    q = sp.Function(q_name)
    locals_ns: dict[str, Any] = {q_name: q, "t": t}
    # Background as plain symbols. We allow either "x" or "feat_x" naming.
    for b in background:
        sym = sp.Symbol(b, real=True)
        locals_ns[b] = sym
    for p in param_names:
        sym = sp.Symbol(p, real=True)
        locals_ns[p] = sym
    # Convenience: q(t) and q_dot are also addressable directly.
    locals_ns["q_dot"] = q(t).diff(t)
    # Allow features['<key>'] style by translating to `feat_<key>`.
    # The mutator can use either bare `<key>` or `features['<key>']`.
    def _normalize(expr_str: str) -> str:
        out = expr_str
        # Map features['key'] -> feat_key (using the bare name 'key' if it's in background; else feat_key).
        import re as _re
        for m in _re.finditer(r"features\[['\"]([\w]+)['\"]\]", expr_str):
            key = m.group(1)
            replacement = key if key in locals_ns else f"feat_{key}"
            if replacement not in locals_ns:
                # Auto-register as background symbol
                sym = sp.Symbol(replacement, real=True)
                locals_ns[replacement] = sym
            out = out.replace(m.group(0), replacement)
        # Map params['p'] -> p
        for m in _re.finditer(r"params\[['\"]([\w]+)['\"]\]", expr_str):
            pname = m.group(1)
            if pname not in locals_ns:
                sym = sp.Symbol(pname, real=True)
                locals_ns[pname] = sym
            out = out.replace(m.group(0), pname)
        return out

    try:
        L_str_normalized = _normalize(lagrangian_expr)
        pred_str_normalized = _normalize(prediction_expr)
        L = sp.sympify(L_str_normalized, locals=locals_ns)
        pred = sp.sympify(pred_str_normalized, locals=locals_ns)
    except (sp.SympifyError, SyntaxError, TypeError) as exc:
        return DerivationResult(
            success=False,
            error_message=f"sympify failure: {type(exc).__name__}: {exc}",
        )

    # Euler-Lagrange
    try:
        eom = _euler_lagrange(L, q, t)
    except Exception as exc:                                            # noqa: BLE001
        return DerivationResult(
            success=False,
            error_message=f"E-L derivation failed: {type(exc).__name__}: {exc}",
        )
    eom_strs = [str(eom)]

    # Steady-state solution
    try:
        ss = _solve_steady_state(eom, q, t)
    except Exception as exc:                                            # noqa: BLE001
        return DerivationResult(
            success=False,
            error_message=f"steady-state solve failed: {type(exc).__name__}: {exc}",
            eom=eom_strs,
        )
    if ss is None:
        return DerivationResult(
            success=False,
            error_message="steady-state E-L is identically zero or unsolvable; declare nontrivial L",
            eom=eom_strs,
        )

    steady_state = {q_name: str(ss)}

    # Substitute steady-state into prediction
    try:
        q_t_sym = q(t)
        closed_form_expr = pred.subs([(q_t_sym.diff(t), 0), (q_t_sym, ss)])
        closed_form_expr = sp.simplify(closed_form_expr)
    except Exception as exc:                                            # noqa: BLE001
        return DerivationResult(
            success=False,
            error_message=f"closed-form reduction failed: {type(exc).__name__}: {exc}",
            eom=eom_strs, steady_state=steady_state,
        )

    # Build python source for the closed form. Audit-fix B2 (2026-04-28):
    # SINGLE-PASS substitution. The two-pass approach (B1) had a bug: after
    # the first pass replaced `M` with `features['M']`, the second pass
    # over `param_names` re-matched the bare `M` INSIDE `features['M']`
    # and produced `features['params['M']']` (nested subscript, syntax
    # error). Fix: build one combined regex that matches every known
    # identifier exactly once and substitutes via a callback that picks
    # the right prefix. Param wins over background when a name is in both.
    import re as _re

    def _build_repl_table() -> dict[str, str]:
        repl: dict[str, str] = {}
        for b in background:
            repl[b] = f"features['{b}']"
        for p in param_names:
            repl[p] = f"params['{p}']"  # param overrides background on duplicate
        for ln in list(locals_ns):
            if ln.startswith("feat_") and ln not in repl:
                key = ln[len("feat_"):]
                repl[ln] = f"features['{key}']"
        return repl

    _repl_table = _build_repl_table()
    if _repl_table:
        # Sort keys longest-first so e.g. `M_Pl` matches before `M`.
        _keys_sorted = sorted(_repl_table.keys(), key=len, reverse=True)
        _identifier_pattern = _re.compile(
            r"\b(" + "|".join(_re.escape(k) for k in _keys_sorted) + r")\b"
        )
        def _substitute_callable(s: str) -> str:
            return _identifier_pattern.sub(lambda m: _repl_table[m.group(1)], s)
    else:
        def _substitute_callable(s: str) -> str:
            return s

    # Audit-fix B3 (2026-04-28): sympy serializes its absolute-value
    # symbol as `Abs(x)` (capital A). The downstream `_safe_compile_form`
    # in fit_primitive_features whitelists `abs` (lowercase, Python
    # builtin) and rejects `Abs` as a disallowed function. Rewrite
    # sympy-isms to their lowercase Python-builtin equivalents before
    # callable_src serialization. Add new mappings as new sympy
    # capitalizations surface in derived forms.
    _SYMPY_TO_PY: dict[str, str] = {
        "Abs": "abs",                 # |x|
        "Min": "min", "Max": "max",
        "Pow": "pow",
        "Piecewise": "where",         # NB: arity differs; only safe for 2-arm forms
        "sign": "sign",               # already lowercase but keep explicit
        "Heaviside": "heaviside",     # step function — needs whitelist add downstream
        "DiracDelta": "dirac_delta",  # delta — needs whitelist add downstream
        "re": "re", "im": "im",       # already lowercase; pinned for safety
    }
    # Sympy literal-symbol replacements (numeric, not function-call form).
    # `oo` → `inf`, `zoo` → `complex_inf`, `nan` → `nan`, `I` → `1j`, etc.
    # These are bare identifiers, not function calls, so a separate
    # word-boundary substitution pass catches them.
    _SYMPY_SYMBOL_TO_PY: dict[str, str] = {
        "oo": "float('inf')",
        "zoo": "float('inf')",  # complex inf collapsed to float inf
        "I": "1j",
        # `pi` and `E` stay as-is — `_safe_compile_form` already maps them
        # to math.pi / math.e via the safe namespace.
    }

    def _rewrite_sympy_isms(src: str) -> str:
        if not src:
            return src
        out = src
        for sympy_name, py_name in _SYMPY_TO_PY.items():
            # Word-boundary match to avoid clobbering substrings.
            out = _re.sub(r"\b" + _re.escape(sympy_name) + r"\b", py_name, out)
        return out

    try:
        _intermediate = _substitute_callable(str(closed_form_expr))
        callable_src = _rewrite_sympy_isms(_intermediate)
    except Exception as exc:                                            # noqa: BLE001
        callable_src = None

    # Noether invariants. Store them in the SAME callable-source format as
    # closed_form_callable_src (`features['k']` / `params['p']` subscripts)
    # so fit_primitive_features can compile and evaluate them per-row
    # without further translation.
    noether = {}
    for sym_name in symmetries:
        try:
            inv = _noether_invariant(sym_name, L, q, t)
            if inv is not None:
                # Express the invariant in steady state too (q̇=0)
                inv_static = inv.subs([(q(t).diff(t), 0), (q(t), ss)])
                inv_static = sp.simplify(inv_static)
                noether[sym_name] = _rewrite_sympy_isms(_substitute_callable(str(inv_static)))
        except Exception as exc:                                        # noqa: BLE001
            logger.warning(f"noether for {sym_name} failed: {exc}")

    # GP-183 C3: classify the steady-state structure for downstream
    # consumers (cleaner than re-parsing it via the gate). Reuses the
    # G-LAGRANGIAN-NONTRIVIAL gate's logic so verdict semantics align.
    triviality_kind = None
    try:
        from ztare.gates.lagrangian_nontrivial_gate import (
            evaluate_lagrangian_nontriviality,
        )
        _lnt = evaluate_lagrangian_nontriviality(
            steady_state, background_symbols=background, param_symbols=param_names,
        )
        _v = _lnt.get("verdict")
        if _v == "ok":
            triviality_kind = "non_trivial"
        elif _v == "trivial":
            triviality_kind = "single_substitution"
        elif _v == "params_only":
            triviality_kind = "params_only"
    except Exception:                                                   # noqa: BLE001
        triviality_kind = None

    return DerivationResult(
        success=True,
        closed_form=str(closed_form_expr),
        closed_form_callable_src=callable_src,
        eom=eom_strs,
        steady_state=steady_state,
        noether=noether,
        declared_symmetries=symmetries,
        triviality_kind=triviality_kind,
    )


def to_jsonable(result: DerivationResult) -> dict[str, Any]:
    """Serialize derivation result for telemetry."""
    return {
        "success": result.success,
        "closed_form": result.closed_form,
        "closed_form_callable_src": result.closed_form_callable_src,
        "eom": result.eom,
        "steady_state": result.steady_state,
        "noether": result.noether,
        "declared_symmetries": result.declared_symmetries,
        "error_message": result.error_message,
        "warnings": result.warnings,
    }


def substitute_derived_parametric_form(
    python_code: str, derived_callable_src: str
) -> str:
    """Audit-fix B2 (2026-04-28): write the derived closed-form back into
    `python_code` so the gate harness scores the SAME form scipy fitted.

    Without this substitution, scipy fits params on `derived_callable_src`
    but the gate harness eval-loop reads `PARAMETRIC_FORM` from the
    mutator's submission — a different expression. The fitted MODEL_PARAMS
    are then evaluated against the wrong form and predictions are
    nonsense.

    Strategy: parse the source, find the `PARAMETRIC_FORM = "..."`
    assignment, replace its right-hand side with the derived expression
    as a Python string literal. AST-based to avoid regex pitfalls on
    multi-line string concatenation patterns.
    """
    import ast as _ast
    try:
        tree = _ast.parse(python_code)
    except SyntaxError:
        return python_code  # caller already validated; defensive only.

    lines = python_code.splitlines(keepends=True)
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, _ast.Name) or tgt.id != "PARAMETRIC_FORM":
            continue
        # Replace the assignment value with a single-line string literal.
        # We use the AST node's line range to locate the segment.
        start_line = node.lineno - 1
        end_line = (node.end_lineno or node.lineno) - 1
        # Construct the replacement line, preserving indentation of the original.
        original_indent = lines[start_line][: len(lines[start_line]) - len(lines[start_line].lstrip())]
        # Repr-escape the derived source so quotes/backslashes survive
        replacement_value = repr(derived_callable_src)
        new_line = f"{original_indent}PARAMETRIC_FORM = {replacement_value}\n"
        # Splice: replace lines [start_line:end_line+1] with new_line
        before = "".join(lines[:start_line])
        after = "".join(lines[end_line + 1:])
        return before + new_line + after
    # PARAMETRIC_FORM not found — append a new declaration at end.
    return python_code + (
        f"\n# GP-180 derived (auto-injected) — overrides any mutator PARAMETRIC_FORM\n"
        f"PARAMETRIC_FORM = {repr(derived_callable_src)}\n"
    )


def extract_lagrangian_declaration(test_model_text: str) -> Optional[dict[str, Any]]:
    """Parse the GP-180 Lagrangian-mode contract from a test_model.py text.

    Expected declarations:
        LAGRANGIAN = "..."             # str, sympy-parseable
        Q_VARIABLES = ["q"]              # list[str]
        BACKGROUND = ["x", "radius_log10", ...]   # list[str]
        PREDICTION = "..."               # str, sympy expression for y_pred(q, features, params)
        SYMMETRIES = ["time_translation", "rotation"]   # list[str]

    Returns dict with all five fields when complete, None otherwise.
    PARAMETER_NAMES is read from the same file via the existing extractor.
    """
    import ast as _ast
    try:
        tree = _ast.parse(test_model_text)
    except SyntaxError:
        return None

    out: dict[str, Any] = {}
    needed = {"LAGRANGIAN", "Q_VARIABLES", "BACKGROUND", "PREDICTION"}
    optional = {"SYMMETRIES"}

    def _resolve_string(node) -> Optional[str]:
        if isinstance(node, _ast.Constant) and isinstance(node.value, str):
            return node.value
        # Joined string literals: ("a" "b") or implicit concat handled here
        if isinstance(node, _ast.Constant):
            return None
        if isinstance(node, _ast.JoinedStr) or isinstance(node, _ast.BinOp):
            try:
                # Try to compile + eval simple constant expressions
                code = compile(_ast.Expression(body=node), "<form>", "eval")
                v = eval(code, {"__builtins__": {}})
                return v if isinstance(v, str) else None
            except Exception:
                return None
        return None

    def _resolve_list_of_strs(node) -> Optional[list[str]]:
        if not isinstance(node, (_ast.List, _ast.Tuple)):
            return None
        result = []
        for elt in node.elts:
            s = _resolve_string(elt)
            if s is None:
                return None
            result.append(s)
        return result

    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, _ast.Name):
            continue
        name = tgt.id
        if name == "LAGRANGIAN":
            s = _resolve_string(node.value)
            if s:
                out["LAGRANGIAN"] = s
        elif name == "PREDICTION":
            s = _resolve_string(node.value)
            if s:
                out["PREDICTION"] = s
        elif name in ("Q_VARIABLES", "BACKGROUND", "SYMMETRIES"):
            lst = _resolve_list_of_strs(node.value)
            if lst is not None:
                out[name] = lst

    if not needed.issubset(set(out.keys())):
        return None
    out.setdefault("SYMMETRIES", [])
    return out


def derive_from_submission(
    test_model_text: str,
    parameter_names: list[str],
) -> Optional[DerivationResult]:
    """Convenience wrapper: extract Lagrangian declaration + derive.

    Returns None when the submission lacks a Lagrangian declaration (fall
    back to PARAMETRIC_FORM mode at the call site). Returns
    DerivationResult(success=False, error_message=...) when the
    declaration exists but derivation fails — caller surfaces the error
    as structural feedback.
    """
    decl = extract_lagrangian_declaration(test_model_text)
    if decl is None:
        return None
    return derive_from_action(
        lagrangian_expr=decl["LAGRANGIAN"],
        q_variables=decl["Q_VARIABLES"],
        background=decl["BACKGROUND"],
        prediction_expr=decl["PREDICTION"],
        symmetries=decl.get("SYMMETRIES") or [],
        param_names=parameter_names,
    )
