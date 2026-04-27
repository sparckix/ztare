"""GP-156 Proposal 3 — feature-vector fit primitive.

Sibling to fit_primitive.py. Where fit_primitive consumes 1D paired
(x, y) numeric data and fits a parametric form `y = f(x; params)`, this
primitive consumes (features_dict, y_observed) pairs and fits a
parametric form `y = f(features; params)`.

Motivation: gp154/gp155 substrates expose feature-DICT predictors
(I_model(features: dict)). LLM mutators are bad at numerical constant
optimization — they propose the right structural form (regime crossover,
sigmoidal blend) but ship the wrong constants. ZTARE's existing
fit_primitive doesn't engage on these substrates because the data shape
isn't 1D.

This primitive bridges the gap. The mutator declares:
    PARAMETRIC_FORM = "a + b*sigmoid((c - features['log10_N_params']) / s)"
    PARAMETER_NAMES = ["a", "b", "c", "s"]
    FEATURE_KEYS = ("log10_N_params",)  # optional; allows static check

The apparatus:
  1. Parses the form via restricted AST whitelist (eval-injection safe)
  2. Compiles to a callable taking (features_dict, params_dict)
  3. Runs scipy.optimize.minimize multi-start over visible (features, y)
  4. Returns FeatureFitResult with fitted params + residuals

Scope (v1):
  - Real-valued parameters only (no integer/categorical mixing)
  - Restricted function whitelist: sigmoid, exp, log, sin, cos, tan,
    sqrt, abs, max, min, tanh
  - Restricted AST: BinOp / UnaryOp / Call / Name / Constant / Subscript
    / Attribute (math, numpy)
  - Subscript on `features` only (e.g. features['intrinsic_dim_d'])
  - Multi-start (default 3 starts, escalates to 5 on stagnation)
  - K_law budget enforced via parameter_names length

Validated 2026-04-25 by scripts/gp156_integration_smoke_test.py:
  * On gp155 ground-truth law (5 params, 72 visible rows): all params
    recovered within 0.3 of truth, max residual 0.048
  * AST safety: 4/4 injection attempts blocked
  * Negative control: 5/5 non-feature-vector substrates correctly
    no-op via should_engage predicate
"""
from __future__ import annotations

import ast
import math
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence


# ── Public types ──────────────────────────────────────────────────────


@dataclass
class FeatureFitResult:
    success: bool
    fitted_params: dict[str, float] = field(default_factory=dict)
    max_abs_residual: float = float("nan")
    mean_abs_residual: float = float("nan")
    sse: float = float("nan")
    n_starts_attempted: int = 0
    n_starts_converged: int = 0
    convergence_classification: str = "unknown"
    error_message: Optional[str] = None
    # GP-156 v2 BIC fields (2026-04-25): per GP-152 framer spec v2,
    # the principled K budget is BIC = N·log(σ̂²) + K·log(N), not a flat
    # K_law cap. Compute on visible-row residuals so the judge can see
    # whether K parameters earned their bits via residual reduction.
    bic: float = float("nan")          # N · log(σ̂²) + K · log(N)
    sigma_sq: float = float("nan")     # σ̂² = SSE / N
    n_fit_rows: int = 0                # N (rows used in fit)
    k_params: int = 0                  # K (parameter count)
    # GP-156 v3 fit-pathology fields (Bug #26, 2026-04-25 evening).
    # gp154 iter 1 fit "converged_clean" with delta_audio=128 (visible y
    # range is [-0.21, 4.0]), then catastrophic on holdout (MRE=3.71).
    # Detect pathological category effects from sparse-row underdetermined
    # params. See Class F bugs in gp158 evidence.txt.
    pathological: bool = False                                       # |any param| > pathology_threshold
    pathology_reason: str = ""                                       # human-readable diagnostic
    extreme_params: dict[str, float] = field(default_factory=dict)   # offenders
    feature_value_counts: dict[str, dict[str, int]] = field(default_factory=dict)  # {feature_key: {value: count}}
    # Bug #31 (2026-04-25 evening): residual-feedback loop closure.
    # Per-categorical-value residual stats so the mutator can see
    # WHICH category is dragging the fit. Closes the open-loop gap
    # vs the 1D fit_primitive's diagnose_residual_pattern.
    # Schema: {feature_key: {value: {n: int, mean_abs_res: float,
    # max_abs_res: float}}}
    residual_by_category: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    residual_diagnostic: str = ""  # formatted block for mutator-prompt injection


# ── AST whitelist & safe compilation ──────────────────────────────────

_ALLOWED_AST_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name,
    ast.Constant, ast.Load, ast.Subscript, ast.Attribute,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
    ast.Mod, ast.FloorDiv,
    # GP-156 v2 (2026-04-25): conditional + comparison nodes for
    # categorical-conditional forms (gp154 needs piecewise-by-modality
    # / by-regime_hint predictors). All side-effect-free.
    ast.IfExp,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.BoolOp, ast.And, ast.Or,
    ast.Tuple, ast.List,  # for `in (...)` / `in [...]` patterns
    # Bug #28 (2026-04-25 evening, proactive Gemini-WAWNS expansion):
    # universal categorical-handling idioms. All are inert data
    # structures or pure expressions; none introduces eval-injection
    # under the locked `{"__builtins__": {}}` namespace.
    ast.Dict,    # `{'lang': m_lang, 'vis': m_vis}.get(features['modality'], 0.0)`
    ast.Set,     # `features['arch'] in {'transformer', 'cnn', 'resnet'}`
    ast.Slice,   # `features['arch'][:3]` — substring matching
)

_ALLOWED_FUNCTIONS = frozenset({
    "sigmoid", "exp", "log", "sin", "cos", "tan",
    "sqrt", "abs", "max", "min", "tanh", "log10",
    # Bug #28 (2026-04-25 evening, proactive): len + str builtins.
    # `len(features['modality'])` and `str(...)` are pure functions used
    # for categorical feature handling. No side effects, no exec.
    "len", "str",
    # GP-156 Bug #22 (2026-04-25): allow type coercion. Mutators
    # naturally write `a * float(features['x'] == 'foo')` for one-hot
    # indicator encoding; rejecting it forced unnecessary retries.
    # All three are safe — pure type coercion, no eval-injection surface.
    "float", "int", "bool",
    # GP-157 Bug #30 (2026-04-25 night) per Gemini Pro panel: continuous-
    # transition primitives. Without these, mutators trying to express
    # smooth regime crossovers fall back to nested ternaries and
    # consistently produce SyntaxError stubs (gp154 iters 5/6/7/9).
    # All three are pure scalar functions, no eval-injection surface,
    # generalizable across every fit_primitive_features substrate.
    "where", "erf",
})


def _sigmoid(x: float, center: float = 0.0, width: float = 1.0) -> float:
    """Logistic sigmoid with optional center+width for regime-crossover use.

    Default `sigmoid(x)` is the standard logistic 1/(1+exp(-x)) — backward-
    compatible with single-arg callers. Three-arg form `sigmoid(x, center,
    width)` produces a smooth crossover at `x = center` with transition
    sharpness `1/width`. Mutators can express continuous regime transitions
    in a SINGLE expression without nested ternaries.
    """
    if width == 0.0:
        # Degenerate: degrade gracefully to a step at `center`.
        return 1.0 if x > center else (0.0 if x < center else 0.5)
    z = (x - center) / width
    if z > 50:
        return 1.0
    if z < -50:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def _where(cond: bool, a: float, b: float) -> float:
    """Single-expression branching primitive — `np.where` for scalar use.

    `where(cond, a, b)` returns `a` if `cond` is truthy else `b`. Equivalent
    to the Python ternary `a if cond else b`, but in function-call syntax
    that LLM mutators reliably emit without hallucinating syntax errors
    (nested ternaries are a known LLM failure mode). Mutator can chain:
    `where(c1, A, where(c2, B, C))` rather than `A if c1 else (B if c2 else C)`.
    """
    return float(a) if bool(cond) else float(b)


_SAFE_NS_BASE = {
    "sigmoid": _sigmoid,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "tanh": math.tanh,
    "sqrt": math.sqrt,
    "abs": abs,
    "max": max,
    "min": min,
    # GP-156 Bug #22 (2026-04-25): match _ALLOWED_FUNCTIONS whitelist so
    # `float(features['x'] == 'foo')` resolves at eval time.
    "float": float,
    "int": int,
    "bool": bool,
    # Bug #28 (2026-04-25 evening, proactive): pure builtins for
    # categorical handling. len() returns int, str() returns str.
    # Both are side-effect-free under `__builtins__: {}` lockdown.
    "len": len,
    "str": str,
    # GP-157 Bug #30 (2026-04-25 night): continuous-transition primitives
    # so mutators can express smooth regime crossovers in single expressions
    # without nested ternaries.
    "where": _where,
    "erf": math.erf,
}


# GP-157 Bug #37 (2026-04-25 night): the safe namespace above is only
# available DURING fit-time scipy.optimize. At gate-time, gate_harness.py
# imports the substrate's test_model.py and the mutator's I_model body
# typically does `eval(PARAMETRIC_FORM, {}, local_env)` where local_env
# only contains `features` and `params`. Continuous-transition primitives
# like `where`, `sigmoid(x, c, w)`, and `erf` were missing from gate-time
# scope, causing TypeError on every row when the form used them. (gp154
# iter 5: o3 wrote `where(...)` form, fit succeeded with K=8 BIC=-81.7,
# then crashed on 10/12 holdout rows at gate import.) Fix: inject the
# canonical primitive definitions at module scope of test_model.py after
# fit-time substitution, so gate_harness.py's `import test_model` picks
# them up and `eval(PARAMETRIC_FORM)` resolves them in either local or
# global scope. Generalizable: every fit_primitive_features substrate
# benefits.

GATE_TIME_PRIMITIVE_SENTINEL = "# === ZTARE-GP157-Bug37 gate-time primitives ==="

GATE_TIME_PRIMITIVE_PRELUDE = '''
# === ZTARE-GP157-Bug37 gate-time primitives ===
# Auto-injected by fit_primitive_features after MODEL_PARAMS substitution
# so the substrate's I_model `eval(PARAMETRIC_FORM, ...)` resolves the
# continuous-transition primitives at gate-harness import time. These
# match the fit-time safe namespace exactly — same closed-form scalar
# semantics, no eval-injection surface.
import math as _ztare_math


def sigmoid(x, center=0.0, width=1.0):
    """Logistic sigmoid with optional center/width for regime crossovers.
    1-arg form is backward-compatible 1/(1+exp(-x)). 3-arg form is a
    smooth crossover at x=center with sharpness 1/width."""
    if width == 0.0:
        return 1.0 if x > center else (0.0 if x < center else 0.5)
    z = (x - center) / width
    if z > 50:
        return 1.0
    if z < -50:
        return 0.0
    return 1.0 / (1.0 + _ztare_math.exp(-z))


def where(cond, a, b):
    """np.where for scalars: a if cond else b. Function-call branching
    that LLMs reliably emit without nested-ternary syntax errors."""
    return float(a) if bool(cond) else float(b)


erf = _ztare_math.erf
# === end ZTARE-GP157-Bug37 gate-time primitives ===

'''


def inject_gate_time_primitives(python_code: str) -> str:
    """Prepend continuous-transition primitive definitions to the
    substrate's test_model.py so they're available in gate-time eval scope.

    Idempotent: detects sentinel and skips if already injected. Generalizable:
    same fix for every fit_primitive_features substrate. Safe: pure scalar
    closures, no I/O, no globals mutation, no eval-injection surface.

    Pattern: prepend AFTER any leading docstring/shebang to keep module
    docstring semantics intact, but BEFORE any user import / declaration.
    """
    if not isinstance(python_code, str) or not python_code:
        return python_code
    if GATE_TIME_PRIMITIVE_SENTINEL in python_code:
        return python_code  # already injected, idempotent

    # Walk past any leading docstring (triple-quoted at file head) so we
    # don't break `__doc__`. Common case: no leading docstring → prepend.
    stripped = python_code.lstrip()
    leading_ws = python_code[: len(python_code) - len(stripped)]

    if stripped.startswith(('"""', "'''")):
        quote = stripped[:3]
        end = stripped.find(quote, 3)
        if end != -1:
            # Insert AFTER the docstring (and its trailing newline)
            split_at = len(leading_ws) + end + 3
            # Skip past the newline after the closing quote, if present
            while split_at < len(python_code) and python_code[split_at] in "\r\n":
                split_at += 1
            return python_code[:split_at] + GATE_TIME_PRIMITIVE_PRELUDE + python_code[split_at:]

    # No leading docstring — prepend at top
    return GATE_TIME_PRIMITIVE_PRELUDE + python_code


class _SafeMathNS:
    """Minimal math/numpy-like namespace that exposes ONLY the whitelisted
    functions. Allows the mutator to write `math.exp(x)` or `np.log10(x)`
    in PARAMETRIC_FORM without giving eval access to the full math/numpy
    surface."""
    sigmoid = staticmethod(_sigmoid)
    exp = staticmethod(math.exp)
    log = staticmethod(math.log)
    log10 = staticmethod(math.log10)
    sin = staticmethod(math.sin)
    cos = staticmethod(math.cos)
    tan = staticmethod(math.tan)
    tanh = staticmethod(math.tanh)
    sqrt = staticmethod(math.sqrt)
    abs = staticmethod(abs)
    max = staticmethod(max)
    min = staticmethod(min)
    float = staticmethod(float)
    int = staticmethod(int)
    bool = staticmethod(bool)
    len = staticmethod(len)
    str = staticmethod(str)
    where = staticmethod(_where)
    erf = staticmethod(math.erf)


_SAFE_NS_BASE["math"] = _SafeMathNS
_SAFE_NS_BASE["np"] = _SafeMathNS
_SAFE_NS_BASE["numpy"] = _SafeMathNS


def extract_referenced_feature_keys(form: str) -> set[str]:
    """Extract every `features['KEY']` literal key referenced in the form.

    Used by the GP-156 champion's recommended pre-fit static check:
    if any referenced key isn't present in the substrate's visible data,
    the form is structurally broken (typo / hallucinated key) and the fit
    should be rejected BEFORE scipy spins. This is stronger than the
    post-hoc Flat-Desert penalty detection because it catches the
    failure at form-validation time with a precise diagnostic instead
    of letting scipy chew on a flat error surface for thousands of
    function evaluations.

    Returns the set of literal string keys. Non-literal subscripts
    (e.g. `features[some_var]`) are silently ignored — they cannot be
    statically resolved.
    """
    keys: set[str] = set()
    try:
        tree = ast.parse(form, mode="eval")
    except SyntaxError:
        return keys
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not (isinstance(node.value, ast.Name) and node.value.id == "features"):
            continue
        # Subscript value (the key)
        idx = node.slice
        if isinstance(idx, ast.Constant) and isinstance(idx.value, str):
            keys.add(idx.value)
    return keys


def _safe_compile_form(form: str) -> Callable[[dict, dict], float]:
    """Compile a parametric form string into a callable, with strict AST checks.

    Raises ValueError on disallowed syntax (eval injection attempts).
    """
    try:
        tree = ast.parse(form, mode="eval")
    except SyntaxError as exc:
        # GP-156 Bug #25 (2026-04-25): mutator may write a multi-line
        # expression with indentation across lines (e.g., chained ternary
        # formatted for readability). Without enclosing parens, Python
        # treats line-2's indent as "unexpected indent". Auto-wrap in
        # parens and retry — this is a universal Python rule (parens
        # allow expressions to span lines), not a mutator-specific fix.
        _retry_form = "(" + form + ")"
        try:
            tree = ast.parse(_retry_form, mode="eval")
            form = _retry_form  # use the wrapped version downstream
        except SyntaxError:
            # GP-156 Bug #24 (2026-04-25): if the form parses as a
            # STATEMENT block (mode='exec') but not as an expression,
            # the mutator wrote if/elif statements or assignments.
            _is_statement_block = False
            try:
                ast.parse(form, mode="exec")
                _is_statement_block = True
            except SyntaxError:
                pass
            if _is_statement_block:
                raise ValueError(
                    "PARAMETRIC_FORM must be a single Python expression, not "
                    "a statement block. You wrote what looks like `if/elif` "
                    "statements or assignments (e.g. `result = ...`). Rewrite "
                    "as a chained ternary expression:\n"
                    "  WRONG: 'if cond_a: result = X\\nelif cond_b: result = Y\\nelse: result = Z'\n"
                    "  RIGHT: 'X if cond_a else (Y if cond_b else Z)'\n"
                    "All branches must be in a single expression — no `=` "
                    "assignments, no newline-separated statements."
                ) from exc
            # Bug #29 (2026-04-25 evening, post-Gemini): enrich the
            # generic SyntaxError diagnostic. Gemini's structural argument:
            # don't write a regex pseudocode detector (Whac-A-Mole); enrich
            # the existing exception so the LLM mutator gets a high-S/N
            # map from "your syntax is invalid" → "use this specific
            # Python grammar instead". Catches infinite long-tail of
            # pseudocode patterns (when/where/given/(N parameters)/Greek
            # symbols/inline annotations) without per-pattern rules.
            raise ValueError(
                f"PARAMETRIC_FORM has SyntaxError: {exc.msg}. "
                f"CRITICAL: PARAMETRIC_FORM must be strictly valid Python "
                f"code, NOT math pseudo-code or prose. Common mistakes:\n"
                f"  - Words like 'when', 'where', 'given' (use Python "
                f"`if/else` ternary instead)\n"
                f"  - Inline annotations like `(8 parameters)` or `K=5` "
                f"(remove them — those belong in PARAMETER_NAMES list "
                f"or thesis prose)\n"
                f"  - Greek symbols (α, β, γ, π) — replace with ASCII "
                f"identifiers (alpha, beta, gamma, pi)\n"
                f"  - Bare identifiers like `d` or `variance_limited` "
                f"(use `features['intrinsic_dim_d']` and "
                f"`features['regime_hint']=='variance_limited'`)\n"
                f"  - Unicode arrows like → (use Python operators: "
                f"`if/else`, `==`, `=`)\n"
                f"  - Statement blocks with `=` assignments or `return` "
                f"(only expressions allowed; use ternary `A if cond else B`)\n"
                f"You MUST use Python ternary `(A if cond else B)`, "
                f"strict dict subscripts `features['key']` / `params['name']`, "
                f"and `.lower()`/`.startswith()` for case-tolerant string "
                f"matching. Extract any prose into thesis.md, not "
                f"PARAMETRIC_FORM.\n"
                f"\n"
                f"CONCRETE EXAMPLE — convert this WRONG form to the RIGHT "
                f"form by chaining ternaries (no domain meaning, just "
                f"grammar):\n"
                f"  WRONG (pseudo-code, statement-blocks, prose mix):\n"
                f"    IF regime_hint == 'A' THEN alpha = 1.0\n"
                f"    ELSE IF regime_hint == 'B' AND foo is given:\n"
                f"        alpha = 2.0 / foo\n"
                f"    ELSE:\n"
                f"        alpha = bias + cat_offset\n"
                f"  RIGHT (single Python expression with chained ternaries):\n"
                f"    \"1.0 if features['regime_hint']=='A' else (\"\n"
                f"    \"  2.0/features['foo'] if (features['regime_hint']=='B' \"\n"
                f"    \"                          and features['foo'] is not None) else (\"\n"
                f"    \"    params['bias'] + params['cat_offset']\"\n"
                f"    \"  )\"\n"
                f"    \")\"\n"
                f"Note: every branch produces an expression (a value), no `=` "
                f"assignment, no `return`, no line continuation tricks needed "
                f"because Python adjacent-string-literals concatenate. The "
                f"result is ONE expression evaluable by python eval()."
            ) from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_AST_NODES):
            raise ValueError(
                f"PARAMETRIC_FORM contains disallowed AST node "
                f"{type(node).__name__}. Only arithmetic, function calls "
                f"(whitelisted), and subscript on `features` are allowed."
            )
        if isinstance(node, ast.Call):
            # Three call shapes allowed:
            #   1. Bare-name (sigmoid(x), exp(x))
            #   2. math.X / np.X attribute access (Bug #20)
            #   3. Safe-method calls on features/params subscripts:
            #      features['x'].lower(), params.get('a', 0.0) etc. (Bug #27)
            #
            # Bug #27 (2026-04-25 evening, Munger inversion):
            # gp154 has 13 modality categories with inconsistent case
            # ('language' vs 'Language' vs 'lang'). LLM mutators naturally
            # write features['modality'].lower() == 'language' for
            # case-tolerant matching, OR features.get('modality', 'other')
            # for missing-key tolerance. Banning these forced unnatural
            # code and burned iters. NEITHER .lower() NOR .get() can
            # introduce arbitrary code execution — they're pure str/dict
            # operations with no side effects.
            _SAFE_METHODS = frozenset({
                "lower", "upper", "strip", "get",
                "startswith", "endswith",
                # Bug #28 (proactive expansion): pure string/dict
                # manipulators. None has side effects, none accesses
                # external state. All return new objects.
                "replace", "split", "find", "index", "count",
                "rfind", "rindex", "rsplit", "lstrip", "rstrip",
                "items", "keys", "values",  # safe dict iteration (no mutation)
            })
            if isinstance(node.func, ast.Name):
                if node.func.id not in _ALLOWED_FUNCTIONS:
                    raise ValueError(
                        f"PARAMETRIC_FORM calls disallowed function "
                        f"`{node.func.id}`. Allowed: {sorted(_ALLOWED_FUNCTIONS)}."
                    )
            elif isinstance(node.func, ast.Attribute):
                # math.X / np.X / numpy.X (whitelisted math fn)
                if (isinstance(node.func.value, ast.Name)
                        and node.func.value.id in ("math", "np", "numpy")):
                    if node.func.attr not in _ALLOWED_FUNCTIONS:
                        raise ValueError(
                            f"PARAMETRIC_FORM calls disallowed math function "
                            f"`{node.func.attr}`. Allowed: {sorted(_ALLOWED_FUNCTIONS)}."
                        )
                elif node.func.attr in _SAFE_METHODS:
                    # Safe str/dict method on any expression (typically a
                    # features[...] subscript or params.get(...)).
                    pass
                else:
                    raise ValueError(
                        f"PARAMETRIC_FORM uses disallowed method "
                        f"`.{node.func.attr}()`. Allowed safe methods: "
                        f"{sorted(_SAFE_METHODS)}; allowed math functions: "
                        f"{sorted(_ALLOWED_FUNCTIONS)} (as math.X / np.X)."
                    )
            else:
                raise ValueError(
                    "PARAMETRIC_FORM call expression must be a bare function "
                    "name (sigmoid(x)), a math.*/np.* attribute (math.exp(x)), "
                    "or a safe str/dict method (features['m'].lower(), "
                    f"params.get('a', 0.0)). Got: {ast.unparse(node.func)!r}."
                )
        if isinstance(node, ast.Attribute):
            # Standalone Attribute access (not inside a Call we already
            # whitelisted). Reject dunder access and disallow direct
            # attribute access on `features`/`params` Name (use subscript
            # `features['key']`, not `features.key`). Allow math/np/numpy
            # attribute as a callable target (handled by Call check above).
            attr = node.attr
            if attr.startswith("__") or attr.endswith("__"):
                raise ValueError(
                    f"PARAMETRIC_FORM uses disallowed dunder attribute "
                    f"`.{attr}`. Defense-in-depth: dunder access can leak "
                    f"the Python object model and is forbidden in eval'd forms."
                )
            # If the attribute's value is a bare Name `features` or `params`,
            # it must be a known method (otherwise use subscript).
            if (isinstance(node.value, ast.Name)
                    and node.value.id in ("features", "params")
                    and attr not in ("get", "lower", "upper", "strip",
                                     "startswith", "endswith")):
                raise ValueError(
                    f"PARAMETRIC_FORM uses disallowed attribute "
                    f"`{node.value.id}.{attr}`. Use subscript "
                    f"`{node.value.id}['{attr}']` for dict access. Allowed "
                    f"methods on the dict itself: get/lower/upper/strip/"
                    f"startswith/endswith."
                )

        if isinstance(node, ast.Subscript):
            # Bug #28 (proactive subscript loosening, 2026-04-25 evening):
            # Only enforce features/params constraint when the BASE is a
            # bare Name. Allow chained subscripts on already-validated
            # expressions (Subscript, Call, Dict literals) — e.g.
            # `features['arch'][:3]`, `{'a': 1, 'b': 2}.get(features['m'])`,
            # `features['m'].split('_')[0]`. The descendant nodes are
            # validated by the rest of the AST walker; the namespace
            # lockdown (`__builtins__: {}`) handles any residual risk.
            value = node.value
            if isinstance(value, ast.Name) and value.id not in ("features", "params"):
                got = value.id
                hint = ""
                if got in ("row", "x", "data", "feats", "f", "r", "d", "p", "P", "pa", "param", "pms"):
                    hint = (
                        f" Common confusion: rename `{got}[...]` to `features[...]`. "
                        f"Inside PARAMETRIC_FORM, the row's feature dict is ALWAYS "
                        f"named `features` (not `{got}`); the parameter dict is "
                        f"ALWAYS named `params`. DO NOT respond by removing "
                        f"PARAMETRIC_FORM/PARAMETER_NAMES — that opts out of "
                        f"the fit primitive entirely and guarantees score=0. "
                        f"Just substitute the variable name."
                    )
                raise ValueError(
                    f"PARAMETRIC_FORM bare-Name subscript must be on `features` "
                    f"or `params` (got: {got!r}). Chained subscripts on "
                    f"already-validated expressions (e.g. features['m'][:3], "
                    f"{{'a': 1}}.get(features['m'])) are allowed.{hint}"
                )

    code = compile(tree, "<parametric_form>", "eval")

    def _fn(features: dict, params: dict) -> float:
        local_ns = dict(_SAFE_NS_BASE)
        local_ns.update(params)          # bare-name access: a, b, c, s
        local_ns["features"] = features
        local_ns["params"] = params      # subscript access: params['a']
        return float(eval(code, {"__builtins__": {}}, local_ns))

    return _fn


# ── Engagement predicate ──────────────────────────────────────────────


def should_engage(
    project_dir: Path | str,
    python_code_override: Optional[str] = None,
) -> tuple[bool, str]:
    """Return (engage, reason) — apparatus calls this before invoking
    the fit primitive.

    Engagement requires three conditions:
      1. features.py exists in project_dir
      2. PARAMETRIC_FORM is declared at module level
      3. PARAMETER_NAMES is declared at module level

    GP-156 critical bug fix (2026-04-25): the mutator's submitted
    python_code is IN MEMORY when this is called from autoresearch_loop;
    test_model.py on disk is the PREVIOUS iter's content. Reading from
    disk to check PARAMETRIC_FORM was the bug that prevented fit
    primitive engagement across all gp154/gp155 iters today (0
    fit_features_result.json files written across 30+ iters).

    Pass python_code_override to check the in-memory submission. When
    None, falls back to disk read (preserves back-compat for callers
    without an in-memory copy, like CLI tools).
    """
    pdir = Path(project_dir)
    if not (pdir / "features.py").exists():
        return False, "no features.py in project_dir (substrate not feature-vector shaped)"
    if python_code_override is not None:
        text = python_code_override
        source = "in-memory submission"
    else:
        test_model_path = pdir / "test_model.py"
        if not test_model_path.exists():
            return False, "no test_model.py"
        text = test_model_path.read_text(errors="ignore")
        source = "test_model.py on disk"
    if "PARAMETRIC_FORM" not in text:
        return False, f"PARAMETRIC_FORM not declared in {source} (mutator opt-in absent)"
    if "PARAMETER_NAMES" not in text:
        return False, f"PARAMETER_NAMES not declared in {source}"
    return True, "engaged"


# ── Multi-start fit ───────────────────────────────────────────────────


# GP-157 Bug #38 (2026-04-25 night) per Gemini Pro panel: sparse-indicator
# hard reject. The mutator's path of least resistance on nd_features
# substrates is to declare one free parameter per categorical value
# (`+ params['delta_X'] * (features['F'] == 'X')`). When category X has
# fewer than ~3 rows in visible_data, that parameter is statistically
# underdetermined — scipy will absorb noise into it (gp154 iter 5:
# `m_audio = 203.66` on 1 audio row). The form fits visible perfectly
# but generalization fails because the param has no statistical mass.
#
# This detector AST-walks PARAMETRIC_FORM looking for the canonical
# bindings (`params['p'] * (features['F'] == 'V')` and `params['p'] *
# (features['F'] in (V1, V2, ...))`) and counts how many visible rows
# satisfy the predicate. Forms with any binding firing on < min_rows
# rows are rejected pre-fit with a structurally clear diagnostic.
#
# Pure statistical protocol — no domain knowledge, no oracle leak. The
# diagnostic NEVER mentions specific feature names that would reveal
# substrate physics; it gives the mutator three escapes (merge / drop /
# continuous variable) and lets it choose. Generalizable: every
# fit_primitive_features substrate benefits.

_SPARSE_INDICATOR_MIN_ROWS_DEFAULT = 3


def _extract_indicator_bindings(form: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """AST-walk PARAMETRIC_FORM for `params['p'] * indicator` patterns.

    Returns a list of (param_name, feature_key, allowed_values) tuples.
    Detects three syntactic shapes (commutative-aware on multiplication):

      A. params['p'] * (features['F'] == 'V')       → ('p', 'F', ('V',))
      B. params['p'] * (features['F'] in ('V1','V2')) → ('p', 'F', ('V1','V2'))
      C. (features['F'] == 'V') * params['p']       → same as A
      D. params['p'] * float(features['F'] == 'V')  → ('p', 'F', ('V',))

    Returns empty list on parse failure or no matches — the caller
    proceeds with the fit (no false-positive rejections).
    """
    try:
        tree = ast.parse(form, mode="eval")
    except SyntaxError:
        return []

    out: list[tuple[str, str, tuple[str, ...]]] = []

    def _is_subscript_on(node, target_name: str) -> Optional[str]:
        """If `node` is `target['key']` with key being a string constant,
        return the key. Else return None."""
        if not isinstance(node, ast.Subscript):
            return None
        if not isinstance(node.value, ast.Name) or node.value.id != target_name:
            return None
        # Python 3.9+: subscript.slice is the index node directly
        idx = node.slice
        if isinstance(idx, ast.Constant) and isinstance(idx.value, str):
            return idx.value
        return None

    def _strip_float_call(node):
        """Unwrap `float(x)` / `int(x)` / `bool(x)` so we can see the
        inner indicator predicate."""
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in ("float", "int", "bool")
            and len(node.args) == 1
        ):
            return node.args[0]
        return node

    def _is_string_constant(node) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _extract_indicator_predicate(
        node,
    ) -> Optional[tuple[str, tuple[str, ...]]]:
        """If `node` is an indicator predicate `features['F'] == 'V'` or
        `features['F'] in (V1, V2, ...)`, return (feature_key, allowed_vals)."""
        node = _strip_float_call(node)
        if not isinstance(node, ast.Compare):
            return None
        if len(node.ops) != 1 or len(node.comparators) != 1:
            return None
        op = node.ops[0]
        feature_key = _is_subscript_on(node.left, "features")
        if feature_key is None:
            return None
        comp = node.comparators[0]
        if isinstance(op, ast.Eq):
            val = _is_string_constant(comp)
            if val is not None:
                return (feature_key, (val,))
        elif isinstance(op, ast.In):
            if isinstance(comp, (ast.Tuple, ast.List, ast.Set)):
                vals = []
                for el in comp.elts:
                    sv = _is_string_constant(el)
                    if sv is None:
                        return None
                    vals.append(sv)
                return (feature_key, tuple(vals))
        return None

    for sub in ast.walk(tree):
        if not isinstance(sub, ast.BinOp) or not isinstance(sub.op, ast.Mult):
            continue
        # Commutative: try both (left=param, right=indicator) and reversed.
        for param_node, indicator_node in (
            (sub.left, sub.right),
            (sub.right, sub.left),
        ):
            param_key = _is_subscript_on(param_node, "params")
            if param_key is None:
                continue
            pred = _extract_indicator_predicate(indicator_node)
            if pred is None:
                continue
            out.append((param_key, pred[0], pred[1]))
            break  # found a match for this BinOp; don't double-count
    return out


def detect_sparse_indicator_overfit(
    parametric_form: str,
    parameter_names: Sequence[str],
    visible_data: Sequence[tuple[dict, float]],
    *,
    min_rows: int = _SPARSE_INDICATOR_MIN_ROWS_DEFAULT,
) -> Optional[str]:
    """Return a diagnostic string if any indicator-bound parameter fires
    on fewer than `min_rows` rows in visible_data. Else return None.

    Pure statistical protocol: no substrate-specific physics, no oracle
    leak. The diagnostic gives the mutator three valid escapes (merge,
    drop, continuous) and never names which feature axis to explore.
    """
    bindings = _extract_indicator_bindings(parametric_form)
    if not bindings:
        return None

    visible_list = list(visible_data)
    if not visible_list:
        return None

    declared_names = set(parameter_names)
    sparse_violations: list[str] = []
    for param_key, feature_key, allowed_vals in bindings:
        if param_key not in declared_names:
            continue  # silent: handled by other AST checks
        # Count rows where features[feature_key] in allowed_vals.
        n_match = 0
        for features_dict, _y in visible_list:
            try:
                fv = features_dict.get(feature_key)
            except AttributeError:
                continue
            if fv in allowed_vals:
                n_match += 1
        if n_match < min_rows:
            allowed_repr = ", ".join(repr(v) for v in allowed_vals)
            sparse_violations.append(
                f"  - params[{param_key!r}] is bound to indicator "
                f"`features[{feature_key!r}] {'==' if len(allowed_vals)==1 else 'in'} "
                f"{allowed_repr if len(allowed_vals)==1 else '(' + allowed_repr + ')'}"
                f"`, which fires on {n_match} visible row(s) (minimum {min_rows} required)."
            )

    if not sparse_violations:
        return None

    return (
        "Sparse-indicator overfitting detected. The following parameters are bound "
        "to one-hot indicators that fire on too few visible rows for statistical "
        "validity:\n"
        + "\n".join(sparse_violations)
        + "\n\nA parameter bound to a sparse indicator is statistically "
          "underdetermined: scipy will absorb noise into it during fit, "
          "producing a form that matches visible perfectly but fails on holdout. "
          "Choose ONE of three structural escapes:\n"
          "  (a) MERGE — combine the sparse category with related dense ones "
          "(e.g., 'audio' + 'speech' → 'audio_speech') so the indicator fires "
          "on more rows;\n"
          "  (b) DROP — remove the term entirely if the rare category is "
          "out-of-distribution and you cannot justify it;\n"
          "  (c) CONTINUOUS — replace the categorical indicator with a "
          "continuous feature that varies across rows (the visible substrate "
          "exposes both categorical strings and numeric values; choose what "
          "the data actually supports).\n"
          "Do not respond by removing PARAMETRIC_FORM/PARAMETER_NAMES — that "
          "opts out of the fit primitive entirely. Refactor the form's structure."
    )


def fit_features(
    parametric_form: str,
    parameter_names: Sequence[str],
    visible_data: Iterable[tuple[dict, float]],
    *,
    n_starts: int = 3,
    seed: int = 1729,
    init_range: tuple[float, float] | dict[str, tuple[float, float]] = (-2.0, 2.0),
    max_iter: int = 2000,
    k_law_max: int = 8,
    auto_escalate: bool = True,
    sparse_indicator_min_rows: int = _SPARSE_INDICATOR_MIN_ROWS_DEFAULT,
    disable_sparse_indicator_reject: bool = False,
    relative_residuals: bool = False,
    weighted_residuals: bool = False,
    sigma_key: str = "sigma",
) -> FeatureFitResult:
    """Fit free parameters of `parametric_form` to (features_dict, y_obs) pairs.

    Parameters
    ----------
    parametric_form : str
        Python expression using `features['key']` for feature access and
        bare names for free parameters. Example:
            "a + b*sigmoid((c - features['log10_N_params']) / s)"
    parameter_names : sequence of str
        Free parameter names appearing in the form. Order is preserved
        in the returned fitted_params dict and in optimizer x0.
    visible_data : iterable of (features_dict, y_observed)
        The mutator's training data. Each features_dict should expose
        all keys the form references.
    n_starts : int
        Multi-start count (default 3). Escalate to 5 on stagnation.
    seed : int
        RNG seed for start-point sampling. Reproducibility-critical.
    init_range : (low, high)
        Uniform sampling range for each start point per parameter.
    max_iter : int
        Per-start optimizer iteration cap.
    k_law_max : int
        Hard ceiling on parameter count (default 8 per GP-152 framer
        spec v2.0 BIC philosophy: replace flat 5-cap with BIC-justified
        budget. The fit returns BIC = N·log(σ̂²) + K·log(N) so the
        judge can see whether each extra parameter earned its bits.
        Hard ceiling preserved at 8 to defend against memorization
        on small visible sets, but real budget is BIC-comparison.

    Returns
    -------
    FeatureFitResult
        success=False with error_message on parse failure, K_law
        overflow, or optimizer failure across all starts.
    """
    parameter_names = list(parameter_names)
    # GP-157 Bug #33 (2026-04-25 night) per Gemini Pro: lift the hard pre-fit
    # K_max cap to a BIC-soft-admit ceiling. The rubric says "BIC is the real
    # budget" but a static integer cap was rejecting K=12 forms before BIC
    # could adjudicate. Now: admit forms with K up to 2x k_law_max (capped at
    # K_HARD_CEILING=20 to prevent ill-conditioned matrix math), fit them,
    # then let BIC's K·log(N) penalty do its job. If BIC doesn't justify the
    # extra parameters, the judge dimensions catch it. Pure protocol fix —
    # no domain knowledge added; the apparatus stops lying about which budget
    # is binding. Generalizable to every fit_primitive_features substrate.
    K_HARD_CEILING = 20
    k_soft_max = min(2 * k_law_max, K_HARD_CEILING)
    if len(parameter_names) > K_HARD_CEILING:
        return FeatureFitResult(
            success=False,
            error_message=(
                f"K_law absolute ceiling exceeded: declared {len(parameter_names)} "
                f"parameters, hard ceiling is {K_HARD_CEILING} (above this, "
                f"matrix conditioning becomes unreliable). Reduce parameter "
                f"count. Note: forms with K up to {k_soft_max} are now "
                f"BIC-adjudicated (the rubric's K={k_law_max} budget is the "
                f"BIC-preferred soft target, not a pre-fit kill-switch)."
            ),
        )
    # Track whether this form is in the soft-admit zone so BIC can flag it
    # in the result; used by the judge / next-iter prompt as a "BIC must
    # justify the extra parameters" signal.
    _bic_soft_admit = len(parameter_names) > k_law_max
    if len(parameter_names) == 0:
        return FeatureFitResult(
            success=False,
            error_message="PARAMETER_NAMES is empty; nothing to fit.",
        )

    try:
        fn = _safe_compile_form(parametric_form)
    except ValueError as exc:
        return FeatureFitResult(success=False, error_message=str(exc))

    visible_list = list(visible_data)
    if not visible_list:
        return FeatureFitResult(
            success=False,
            error_message="No visible data provided; cannot fit.",
        )

    # GP-164 wMDL (2026-04-25 night): weighted χ² mode. When the substrate
    # exposes per-row measurement error via `sigma_key` in the feature dict
    # (e.g., gp163d's `errV_frac`), the objective becomes
    # χ² = Σ((y_pred - y_obs)/σ_i)², not raw SSE. This is the framer-side
    # half of the v2.0 architecture: heteroscedastic substrates need a
    # weighted solver before REFRAME's frame-choice can be trusted.
    # Backward compat: weighted_residuals=False (default) → unchanged
    # behavior; relative_residuals takes precedence over weighted only if
    # weighted_residuals is False. σ=1 fallback applies per row when the
    # key is missing on a row (avoids hard failure on partial schemas).
    sigma_list: list[float] = []
    if weighted_residuals:
        for feats, _ in visible_list:
            try:
                _s = float(feats.get(sigma_key, 1.0))
            except (TypeError, ValueError):
                _s = 1.0
            if not math.isfinite(_s) or _s <= 0:
                _s = 1.0
            sigma_list.append(_s)
    else:
        sigma_list = [1.0] * len(visible_list)

    # GP-157 Bug #38 (2026-04-25 night): sparse-indicator hard reject.
    # AST-walk PARAMETRIC_FORM for `params['p'] * (features['F'] == 'V')`
    # and `params['p'] * (features['F'] in (...))` patterns; reject pre-fit
    # when any binding fires on fewer than min_rows visible rows.
    # Pure statistical protocol, no domain knowledge. See detector docstring
    # for the three valid escapes (merge / drop / continuous).
    if not disable_sparse_indicator_reject:
        sparse_diag = detect_sparse_indicator_overfit(
            parametric_form,
            parameter_names,
            visible_list,
            min_rows=sparse_indicator_min_rows,
        )
        if sparse_diag is not None:
            return FeatureFitResult(
                success=False,
                error_message=sparse_diag,
            )

    # GP-156 champion recommendation (2026-04-25 iter 1, score 98):
    # PRE-FIT static cross-check between PARAMETRIC_FORM referenced keys
    # and actual feature keys present in visible_list. Catches the
    # Flat-Desert / misspelled-key bypass at form-validation time
    # instead of after scipy chews on a flat error surface. This is
    # stronger than the post-hoc penalty detection (which still runs
    # as defense-in-depth).
    referenced_keys = extract_referenced_feature_keys(parametric_form)
    if referenced_keys:
        # Sample first row's actual keys (assumes substrate has consistent schema)
        actual_keys = set(visible_list[0][0].keys())
        missing = referenced_keys - actual_keys
        if missing:
            return FeatureFitResult(
                success=False,
                error_message=(
                    f"PARAMETRIC_FORM references feature keys that don't exist "
                    f"in the visible data: {sorted(missing)}. "
                    f"Available keys: {sorted(actual_keys)}. "
                    f"This is the GP-156 Flat-Desert bypass class — likely a "
                    f"typo or hallucinated key. Fix the form before resubmission. "
                    f"(Pre-fit static cross-check; would have produced a vacuous "
                    f"fit with success=true under the post-hoc detector alone.)"
                ),
            )

    try:
        from scipy.optimize import minimize
    except ImportError:
        return FeatureFitResult(
            success=False,
            error_message="scipy not available; fit primitive requires scipy.optimize.",
        )

    rng = random.Random(seed)

    # GP-156 flat-desert bypass fix (2026-04-25): track per-row exception
    # rates so we can detect when the form universally fails on every row
    # (e.g., misspelled feature key → KeyError on every visible row →
    # objective returns 1e9 for all params → scipy converges to arbitrary
    # starting point and reports success=True). This was the real
    # apparatus bypass found by gp156 iter 4.
    PENALTY = 1e9
    _row_exception_count = [0]   # mutable counter accessible from closure
    _evals = [0]

    def objective(params_vec):
        params = dict(zip(parameter_names, params_vec))
        sse = 0.0
        n_row_exc = 0
        n_rows = 0
        for idx, (feats, y_obs) in enumerate(visible_list):
            n_rows += 1
            try:
                y_pred = fn(feats, params)
            except (ZeroDivisionError, ValueError, OverflowError, KeyError, TypeError):
                n_row_exc += 1
                continue
            if math.isnan(y_pred) or math.isinf(y_pred):
                n_row_exc += 1
                continue
            # GP-164 wMDL (2026-04-25 night): weighted χ² takes precedence
            # when σ is provided. Otherwise fall back to relative-residuals
            # (F6, gp163d) or raw SSE.
            if weighted_residuals:
                _s = sigma_list[idx]
                sse += ((y_pred - y_obs) / _s) ** 2
            elif relative_residuals:
                # F6 fix (gp163d-class loss-landscape, 2026-04-26): divide
                # each residual by max(|y_obs|, eps) before squaring so
                # high-y rows do not dominate. Default unchanged for
                # backward compatibility.
                _denom = abs(y_obs) if abs(y_obs) > 1e-300 else 1e-300
                sse += ((y_pred - y_obs) / _denom) ** 2
            else:
                sse += (y_pred - y_obs) ** 2
        _evals[0] += 1
        # If every row failed, this params_vec is uninformative — return
        # the penalty AND record that we hit the flat-desert state.
        if n_row_exc >= n_rows:
            _row_exception_count[0] += 1
            return PENALTY
        # Partial failure: penalize but keep gradient signal from successful rows
        if n_row_exc > 0:
            sse += PENALTY * (n_row_exc / n_rows)
        return sse

    # GP-156 Bug #5 fix (2026-04-25): per-parameter init_range for
    # convergence on physical-scale parameters. Uniform [-2, 2] was
    # landing in the flat sigmoid-saturated region for parameters like
    # `b` (intercept ~3-10) → no gradient signal → scipy returned
    # arbitrary start point with success=True. Per-parameter ranges
    # let the mutator hint plausible ranges per param.
    def _range_for(pname: str) -> tuple[float, float]:
        if isinstance(init_range, dict):
            return init_range.get(pname, (-2.0, 2.0))
        return init_range

    best: Optional[dict] = None
    converged = 0
    # auto_escalate: F3 fix (deep audit, 2026-04-26) — replace arithmetic
    # widening with LOGARITHMIC widening. The old code multiplied the
    # symmetric half-width by 5× then 25×, which kept exploration within
    # ~2 decades of the default midpoint. For dimensional constants
    # whose physical optimum is OOM-distant from the default range
    # (e.g. acceleration constant ~1e-10 with default (-2, 2)),
    # arithmetic widening cannot escape — even at 25× the range becomes
    # only (-50, 50). Logarithmic widening probes each escalation step
    # at a different *order of magnitude*, guaranteeing decade-spanning
    # exploration. Each escalation samples from a log-uniform distribution
    # with sign chosen randomly per start. This recovers the gp163d-class
    # init-range trap automatically when the user did not supply
    # INIT_RANGE explicitly.
    #
    # Pass 0 (default user range): n_starts uniform samples from [lo, hi]
    # Pass 1 (escalation, +3 decades): log-uniform across |x| ∈ [hw·1e-1, hw·1e3]
    # Pass 2 (escalation, +6 decades): log-uniform across |x| ∈ [hw·1e-3, hw·1e6]
    # where hw = max(1.0, |hi-lo|/2) is the original half-width.
    _escalation_attempts = [("default", None)]
    if auto_escalate:
        # Decade bands chosen to span both very small (1e-12) and very
        # large (1e6) physical scales when default hw is order(1).
        # gp163d's c≈1.2e-10 is reachable in pass 1; coupling-style
        # constants ≈1e-15 need pass 2; pass 3 covers absurd cases.
        _escalation_attempts.append(("log_decades", (1e-6, 1e3)))    # 1e-6 to 1e3
        _escalation_attempts.append(("log_decades", (1e-12, 1e6)))   # full physical span
        _escalation_attempts.append(("log_decades", (1e-18, 1e9)))   # last resort

    import math as _math

    # F4 fix (deep audit, 2026-04-26): y-scale-relative convergence
    # check. The old check `res.success or res.fun < 1e-3` was scale-
    # blind: substrates with y ~ 1e-11 had sse ~1e-22 trivially below
    # 1e-3, so the FIRST pass always "converged" even on catastrophically
    # bad fits, blocking the auto_escalate widening loop from ever
    # running. Compute a relative SSE threshold from the visible y scale:
    # threshold = (mean|y|)² × 0.01  (sse below 1% of y² is a good fit).
    _y_abs = [abs(y) for _, y in visible_list if y != 0]
    if _y_abs:
        _mean_y = sum(_y_abs) / len(_y_abs)
    else:
        _mean_y = 1.0
    _sse_relative_threshold = max((_mean_y ** 2) * 0.01, 1e-300)

    for _mode, _decade_band in _escalation_attempts:
        for _ in range(n_starts):
            x0 = []
            for pname in parameter_names:
                lo, hi = _range_for(pname)
                if _mode == "default":
                    x0.append(rng.uniform(lo, hi))
                else:
                    # Logarithmic widening. Use the original half-width
                    # as the magnitude anchor; sample log-uniformly across
                    # the requested decade band; pick sign uniformly so
                    # both polarities are explored.
                    hw = max(1.0, abs(hi - lo) / 2.0) if hi != lo else 1.0
                    band_lo, band_hi = _decade_band
                    log_lo = _math.log10(hw * band_lo)
                    log_hi = _math.log10(hw * band_hi)
                    log_x = rng.uniform(log_lo, log_hi)
                    sign = 1.0 if rng.random() > 0.5 else -1.0
                    x0.append(sign * (10.0 ** log_x))
            try:
                res = minimize(objective, x0, method="Nelder-Mead",
                               options={"maxiter": max_iter, "xatol": 1e-8})
            except Exception:
                continue
            # F4: y-scale-relative success criterion. A start "converged"
            # only if scipy reports success AND sse is below the data's
            # natural scale. Otherwise, keep escalating. This is the
            # signal that gates whether F3 logarithmic widening fires.
            if res.success and res.fun < _sse_relative_threshold:
                converged += 1
            if best is None or res.fun < best["sse"]:
                best = {"sse": float(res.fun),
                        "params": dict(zip(parameter_names, [float(v) for v in res.x]))}
        # Stop escalating if we already converged at least once
        if converged > 0:
            break

    if best is None:
        return FeatureFitResult(
            success=False,
            n_starts_attempted=n_starts,
            n_starts_converged=0,
            error_message="All starts failed; optimizer raised exceptions on every attempt.",
        )

    # GP-156 flat-desert bypass fix: detect when scipy "converged" on the
    # PENALTY surface — i.e., the form fails on every row at every params
    # point, so scipy stops at an arbitrary starting point with sse=PENALTY
    # and reports success. Reject as fit failure with diagnostic.
    if best["sse"] >= PENALTY * 0.99:
        return FeatureFitResult(
            success=False,
            fitted_params=best["params"],
            sse=best["sse"],
            n_starts_attempted=n_starts,
            n_starts_converged=converged,
            error_message=(
                "Flat-desert detected: every params_vec evaluated produced "
                f"the penalty value {PENALTY:.0e} on at least one starting "
                f"point. The PARAMETRIC_FORM likely references a feature "
                f"key that doesn't exist in the visible data (typo / "
                f"misspelling) OR fails on every row for some other "
                f"reason. Reported objective best={best['sse']:.2e}; "
                f"row-exception evaluation count={_row_exception_count[0]} "
                f"of {_evals[0]} total evals. Reject as uninformative fit."
            ),
        )

    fitted = best["params"]
    residuals = []
    # GP-164 wMDL: track weighted χ² contributions when σ provided so the
    # post-fit BIC uses the proper χ² + K·log(N) form. Falls back to
    # squared raw residual when not weighted (sigma_list[idx] = 1.0).
    weighted_sq_residuals: list[float] = []
    # Bug #31 (2026-04-25): track (features, |residual|) pairs for the
    # residual-feedback breakdown injected into the next mutator prompt.
    per_row_residuals: list[tuple[dict, float]] = []
    for idx, (feats, y_obs) in enumerate(visible_list):
        try:
            y_pred = fn(feats, fitted)
            r_val = abs(y_pred - y_obs)
            residuals.append(r_val)
            _s = sigma_list[idx]
            weighted_sq_residuals.append(((y_pred - y_obs) / _s) ** 2)
            per_row_residuals.append((feats, r_val))
        except Exception:
            residuals.append(float("inf"))
            weighted_sq_residuals.append(float("inf"))
            per_row_residuals.append((feats, float("inf")))

    finite_residuals = [r for r in residuals if math.isfinite(r)]
    if not finite_residuals:
        return FeatureFitResult(
            success=False,
            fitted_params=fitted,
            n_starts_attempted=n_starts,
            n_starts_converged=converged,
            error_message="Fitted parameters produce non-finite residuals on visible data.",
        )

    classification = "converged_clean" if converged >= 2 else (
        "converged_marginal" if converged >= 1 else "no_convergence"
    )

    # GP-156 v2 BIC (2026-04-25): per GP-152 framer spec v2.0,
    # MDL_v2 = N · log(σ̂²_raw) + K_total · log(N).
    # For feature-vector fits there's no h_in/h_out framing, so K_total = K_law.
    # σ̂² = SSE / N. Compute on FINITE residuals only (skips rows where the
    # form blew up; counts toward n_fit_rows after filtering).
    #
    # GP-164 wMDL extension (2026-04-25 night): when weighted_residuals=True
    # and per-row σ is supplied, the principled MDL becomes
    #     BIC_χ² = χ² + K · log(N)
    # because σ is given (not estimated from the residuals themselves), so
    # there is no N·log(σ̂²) free-parameter equivalent. χ²/dof ≈ 1 indicates
    # a good fit; large χ² flags model misspecification independent of how
    # large the y values themselves are. Reports `sigma_sq` as χ²/N for
    # weighted runs so downstream consumers see a comparable goodness-of-fit
    # number; raw σ̂² is kept for unweighted runs.
    n_fit = len(finite_residuals)
    sse_finite = sum(r * r for r in finite_residuals)
    k = len(parameter_names)
    if weighted_residuals:
        finite_chi_sq_terms = [
            t for t in weighted_sq_residuals if math.isfinite(t)
        ]
        chi_sq = sum(finite_chi_sq_terms) if finite_chi_sq_terms else float("nan")
        sigma_sq = (chi_sq / n_fit) if (n_fit > 0 and math.isfinite(chi_sq)) else float("nan")
        if n_fit > 0 and math.isfinite(chi_sq):
            bic = chi_sq + k * math.log(n_fit)
        else:
            bic = float("nan")
    else:
        sigma_sq = sse_finite / n_fit if n_fit > 0 else float("nan")
        if n_fit > 0 and sigma_sq > 0:
            bic = n_fit * math.log(sigma_sq) + k * math.log(n_fit)
        else:
            bic = float("nan")

    # GP-156 Bug #26 (2026-04-25 evening): post-fit pathology check.
    # gp154 iter 1 fit "converged_clean" with delta_audio=128 on a substrate
    # whose visible y range is [-0.21, 4.0]. BIC was negative (looked good)
    # but holdout MRE = 3.71 because scipy moved slack into a sparse-category
    # parameter that absorbed visible noise. Detect via:
    #   1. |param| > 10× max(|y_observed|)  → magnitude pathology
    #   2. per-categorical-feature row count → underdetermined warning
    # Pathology does NOT fail the fit (let downstream gate decide); just tags
    # the result so the judge can see WHY a converged fit produced bad
    # holdout predictions.
    # GP-167 fix (2026-04-25 night): log-space parameter awareness.
    # Parameters named log_*, log10_*, ln_*, or log2_* live in
    # log-space; their magnitudes are NOT comparable to y's magnitude.
    # A parameter `log10_c0 = -10` corresponds to c0 = 1e-10 — perfectly
    # physical for substrates with y at acceleration scales — but the
    # naive |pval| > 10*max(|y|) check flags it as pathological. The
    # correct threshold for log-space params is to check whether the
    # fitted value escapes the operator-declared init_range (with a
    # generous 2x widening to allow bounded escalation) rather than
    # comparing to y magnitude.
    def _is_log_space_param(name: str) -> bool:
        nl = name.lower()
        return any(
            nl == p or nl.startswith(p + "_")
            for p in ("log", "log10", "log2", "ln")
        )

    # 2026-04-26 fix: feature-anchor parameters live in feature space,
    # NOT y space. A parameter named `m0`, `M0`, `r0`, `x0`, `center`,
    # `mu`, `mass`, `radius`, etc. that appears in `(features[k] - param)`
    # or `(features[k] / param)` patterns is a feature-axis anchor — its
    # magnitude is comparable to the FEATURE's magnitude, not y's.
    # gp163d iter-8 false-fired the linear-threshold check on m0=11.46
    # (mass_log10 anchor, perfectly reasonable) because the rule treated
    # it as a y-scaled param.
    def _is_feature_anchor_param(name: str, form_str: str) -> bool:
        nl = name.lower()
        # Detect by form context: param appears in `(features[k] - param)`
        # or `(features[k] / param)` patterns. This is the structural test.
        if form_str:
            anchor_patterns = [
                rf"features\[['\"][\w]+['\"]\]\s*[-+]\s*params\[['\"]" + re.escape(name) + r"['\"]\]",
                rf"features\[['\"][\w]+['\"]\]\s*/\s*params\[['\"]" + re.escape(name) + r"['\"]\]",
                rf"params\[['\"]" + re.escape(name) + r"['\"]\]\s*[-+]\s*features\[['\"][\w]+['\"]\]",
            ]
            for pat in anchor_patterns:
                if re.search(pat, form_str):
                    return True
        # Heuristic by name (fallback): common feature-anchor naming.
        anchor_name_prefixes = (
            "m0", "x0", "r0", "n0", "d0", "g0", "c_star", "g_star",
            "center", "mu", "mass_", "radius_", "anchor_", "offset_",
        )
        anchor_name_suffixes = ("_0", "_anchor", "_center", "_offset", "_mu", "_star")
        for p in anchor_name_prefixes:
            if nl == p or nl.startswith(p):
                return True
        for s in anchor_name_suffixes:
            if nl.endswith(s):
                return True
        return False

    y_max = max((abs(y) for _, y in visible_list), default=1.0)
    linear_threshold = max(10.0 * y_max, 10.0)  # default threshold for linear params
    extreme: dict[str, float] = {}
    extreme_reasons: dict[str, str] = {}
    for pname, pval in fitted.items():
        if _is_log_space_param(pname):
            # Log-space param: check against init_range with 2x widening
            r = (
                init_range.get(pname, (-15.0, 15.0))
                if isinstance(init_range, dict)
                else init_range
            )
            try:
                lo, hi = float(r[0]), float(r[1])
            except Exception:
                lo, hi = -15.0, 15.0
            half_width = (hi - lo) / 2.0
            mid = (hi + lo) / 2.0
            if abs(pval - mid) > 2.0 * half_width:
                extreme[pname] = pval
                extreme_reasons[pname] = (
                    f"log-space param {pname}={pval:.3f} escaped 2× declared "
                    f"init_range [{lo:.2f}, {hi:.2f}]"
                )
        elif _is_feature_anchor_param(pname, parametric_form):
            # Feature-anchor param (`m0`, `x0`, `g_star`, etc. used as
            # `features[k] - param` offset or `features[k] / param`
            # scale): bounded by FEATURE range, not y. Check fitted
            # value against init_range with 2x widening, like log-space.
            r = (
                init_range.get(pname, None)
                if isinstance(init_range, dict)
                else None
            )
            if r is None:
                # No init range declared — accept the fit; pathology
                # detection here is too risky without the operator's
                # declared range to compare against.
                continue
            try:
                lo, hi = float(r[0]), float(r[1])
            except Exception:
                continue
            half_width = (hi - lo) / 2.0
            mid = (hi + lo) / 2.0
            if abs(pval - mid) > 2.0 * half_width:
                extreme[pname] = pval
                extreme_reasons[pname] = (
                    f"feature-anchor param {pname}={pval:.3g} escaped 2× declared "
                    f"init_range [{lo:.3g}, {hi:.3g}]"
                )
        else:
            # Linear param (multiplier / amplitude / coefficient): bound
            # by y magnitude. Skip if param name suggests y-scale (c, A,
            # etc.) AND it appears multiplied by a feature — those are
            # legitimately y-magnitude.
            if abs(pval) > linear_threshold:
                extreme[pname] = pval
                extreme_reasons[pname] = (
                    f"linear param {pname}={pval:.3g} exceeds {linear_threshold:.2f} "
                    f"(10× max|y|)"
                )
    pathological = bool(extreme)
    pathology_reason = ""
    if pathological:
        reasons_str = "; ".join(extreme_reasons.values())
        pathology_reason = (
            f"{len(extreme)} parameter(s) flagged as pathological: {reasons_str}. "
            f"This is the Bug #26 sparse-category-overfitting signature: "
            f"scipy moved slack into params that absorbed visible noise; "
            f"holdout will likely fail catastrophically. Suspect "
            f"underdetermined category effects."
        )

    # Bug A (gp163d postmortem, 2026-04-25 night): SUB-PHYSICAL-SCALE detection.
    # Inverse of the Bug #26 magnitude-pathology check. gp163d ran 11 iters with
    # the canonical MOND simple-form fitting c=1.33e-15 when the physical scale
    # was c≈1.2e-10. With INIT_RANGE = (-2, 2) and physical optimum 5+ orders
    # of magnitude smaller, scipy's gradient descent cannot traverse the gap;
    # it converges to a degenerate near-zero basin where high-x rows dominate
    # the objective (y ≈ x for any c) and low-x rows' residuals match the
    # tiny y-scale poorly but produce locally-flat gradients.
    #
    # Signal: positive parameter whose magnitude is more than 5 orders of
    # magnitude SMALLER than max(|y|) suggests the init range cannot reach
    # the physical optimum. Emits an actionable hint pointing at INIT_RANGE.
    y_min_nonzero = min(
        (abs(y) for _, y in visible_list if y != 0),
        default=1.0,
    )
    y_max_obs = max(
        (abs(y) for _, y in visible_list if y != 0),
        default=1.0,
    )
    sub_physical: dict[str, float] = {}
    # B3 fix (deep audit follow-up, 2026-04-26): false-positive risk on
    # substrates where y values are large but params are legitimately
    # order(1) (e.g. linear coefficient + large constant offset). The
    # detector now requires THREE conditions before flagging:
    #   (a) param magnitude is 5+ decades below min|y| (original signal)
    #   (b) param's |fitted value| is inside default (-2, 2) (init-range
    #       trap fingerprint — user did NOT escape with custom INIT_RANGE)
    #   (c) the FIT IS EMPIRICALLY BAD: mean|residual| / max|y| > 0.05
    #       (residual is at least 5% of y scale — a structurally bad fit
    #       that converged anyway). A good fit on large-y data has tiny
    #       residuals regardless of param scale, so this gates out the
    #       legitimate-large-y false positive.
    # All three conditions must hold to flag.
    # B3 guard: use y_min_nonzero as the relative-residual denominator
    # because for substrates spanning many decades (gp163d-class), high-y
    # rows dominate mean|res| while low-y rows can be catastrophically
    # off — yet mean|res|/max|y| stays small. Dividing by min|y| gives a
    # CONSERVATIVE relative-error metric that fires when low-y rows are
    # mis-fit even if high-y rows are perfect.
    _mean_abs_res = (
        sum(finite_residuals) / len(finite_residuals)
        if finite_residuals
        else 0.0
    )
    rel_residual_quality = (
        _mean_abs_res / y_min_nonzero if y_min_nonzero > 0 else 0.0
    )
    fit_empirically_bad = rel_residual_quality > 0.05
    if y_min_nonzero > 0 and fit_empirically_bad:
        for pname, pval in fitted.items():
            if pval == 0 or abs(pval) <= 0:
                continue
            decades_below_min = y_min_nonzero / abs(pval)
            within_default = abs(pval) < 2.0
            if decades_below_min > 1e5 and within_default:
                sub_physical[pname] = pval
    if sub_physical and not pathological:
        pathological = True
        # B2 fix (deep audit, 2026-04-25): the prior hint suggested
        # `(1e-10*1e-3, 1e-10*1e3)` syntax — but the INIT_RANGE parser
        # at _to_num only accepts ast.Constant + UnaryOp(USub), NOT
        # BinOp(Mult). Mutators following that hint got silently
        # re-trapped at default (-2, 2). Use plain numeric literals.
        _y_scale_lo = y_min_nonzero * 1e-3
        _y_scale_hi = y_min_nonzero * 1e3
        pathology_reason = (
            f"SUB-PHYSICAL-SCALE init-range trap (Bug A from gp163d postmortem): "
            f"{len(sub_physical)} parameter(s) {sub_physical} are 5+ orders of "
            f"magnitude smaller than min(|y|)={y_min_nonzero:.2e}. With default "
            f"INIT_RANGE = (-2, 2), scipy cannot traverse to the physical scale; "
            f"the fit converged in a degenerate near-zero basin (high-x rows "
            f"dominate objective, low-x rows are effectively unfit). "
            f"REMEDY: declare INIT_RANGE at module level with PLAIN NUMERIC "
            f"LITERALS (parser does NOT accept arithmetic expressions like "
            f"`1e-10*1e-3`). Example for a parameter near the y-scale: "
            f"INIT_RANGE = {{'<param>': ({_y_scale_lo:.2e}, {_y_scale_hi:.2e})}}. "
            f"Span ~3 decades around the expected physical value. Negative "
            f"values are allowed (use `-1e-8`), but no `*`, `/`, or function "
            f"calls inside the bounds tuple."
        )

    # Per-categorical-feature value counts in visible (Class F evidence).
    # Helps the judge + mutator see WHICH categories have <3 rows and are
    # therefore underdetermined for any param tied to them.
    feature_value_counts: dict[str, dict[str, int]] = {}
    for feats, _y in visible_list:
        for fk, fv in feats.items():
            if isinstance(fv, str):  # categorical only
                feature_value_counts.setdefault(fk, {})
                feature_value_counts[fk][fv] = feature_value_counts[fk].get(fv, 0) + 1

    # Bug #31 residual-feedback loop closure (2026-04-25 evening).
    # Compute per-categorical-value residual stats so the mutator can
    # see WHICH categories drag the fit. Closes the open-loop gap vs
    # the 1D fit_primitive's diagnose_residual_pattern.
    overall_mean = sum(finite_residuals) / len(finite_residuals) if finite_residuals else 0.0
    residual_by_category: dict[str, dict[str, dict[str, float]]] = {}
    for fk in feature_value_counts:
        residual_by_category[fk] = {}
        for fv in feature_value_counts[fk]:
            group_res = [
                r for f, r in per_row_residuals
                if f.get(fk) == fv and math.isfinite(r)
            ]
            if not group_res:
                continue
            residual_by_category[fk][fv] = {
                "n": len(group_res),
                "mean_abs_res": sum(group_res) / len(group_res),
                "max_abs_res": max(group_res),
            }

    # Build the formatted diagnostic block that gets injected into the
    # NEXT mutator prompt. Highlights worst-fitting categorical groups
    # (mean residual >= 1.5× overall) so the mutator sees where to refine.
    diag_lines: list[str] = []
    if overall_mean > 0:
        threshold = max(1.5 * overall_mean, overall_mean + 0.05)
        worst_groups = []
        for fk, vc in residual_by_category.items():
            for fv, stats in vc.items():
                if stats["mean_abs_res"] >= threshold:
                    worst_groups.append((fk, fv, stats))
        if worst_groups:
            diag_lines.append(
                f"RESIDUAL DIAGNOSTIC: overall mean|res|={overall_mean:.4f}; "
                f"the following categorical groups have mean|res| >= "
                f"{threshold:.4f} (1.5× overall, suggesting the form does "
                f"not capture their structure):"
            )
            worst_groups.sort(key=lambda t: -t[2]["mean_abs_res"])
            for fk, fv, stats in worst_groups[:8]:
                diag_lines.append(
                    f"  - {fk}='{fv}' (n={stats['n']}): "
                    f"mean|res|={stats['mean_abs_res']:.4f}, "
                    f"max|res|={stats['max_abs_res']:.4f}"
                )
            diag_lines.append(
                "Refine the form to incorporate these features differently "
                "(e.g., add a continuous transition, group sparse categories, "
                "or use the underlying physical variable rather than the "
                "categorical label)."
            )
    # GP-157 Bug #33 (2026-04-25 night): when the form was soft-admitted past
    # the rubric's k_law_max via the new BIC-adjudication path, surface the
    # signal to the mutator + judge. BIC may already justify the extra
    # parameters (lower BIC than the K=k_law_max alternative), or may not;
    # we report the fact, the residual diagnostic shows the categorical
    # geometry, the judge weighs both. Pure protocol signal — no domain
    # knowledge added.
    if _bic_soft_admit:
        soft_admit_warning = (
            f"⚠️  BIC SOFT-ADMIT: K={k} > rubric's k_law_max={k_law_max} but "
            f"under hard ceiling {K_HARD_CEILING}. BIC={bic:.3f} must justify "
            f"the extra parameters vs a K≤{k_law_max} alternative. If a simpler "
            f"form achieves comparable σ̂², BIC penalizes K·log(N) and the "
            f"judge will reject this thesis on parsimony grounds. Recommend: "
            f"submit a K≤{k_law_max} rival form alongside; let the lower-BIC "
            f"form win."
        )
        diag_lines.insert(0, soft_admit_warning)
    residual_diagnostic = "\n".join(diag_lines)

    return FeatureFitResult(
        success=True,
        fitted_params=fitted,
        max_abs_residual=max(finite_residuals),
        mean_abs_residual=sum(finite_residuals) / len(finite_residuals),
        sse=best["sse"],
        n_starts_attempted=n_starts,
        n_starts_converged=converged,
        convergence_classification=classification,
        bic=bic,
        sigma_sq=sigma_sq,
        n_fit_rows=n_fit,
        k_params=k,
        pathological=pathological,
        pathology_reason=pathology_reason,
        extreme_params=extreme,
        feature_value_counts=feature_value_counts,
        residual_by_category=residual_by_category,
        residual_diagnostic=residual_diagnostic,
    )


# ── Substrate-loader convenience (used by autoresearch_loop integration) ─


def load_visible_from_substrate(project_dir: Path | str) -> tuple[Optional[list[tuple[dict, float]]], Optional[str]]:
    """Load (features_dict, y_observed) pairs from a substrate's
    canonical visible rows.

    GP-156 critical bug fix (2026-04-25): we used to read VISIBLE_SET
    from test_model.py, but the mutator OVERWRITES test_model.py every
    iter and frequently drops the VISIBLE_SET attribute. Result:
    fit_features always silently no-op'd via "no_visible_set" reason.

    Now we load from features.py — which is part of the SUBSTRATE
    scaffolding the mutator should not touch. features.py exposes
    visible_rows() returning the canonical (id, y, features) triples.

    Fallback path for substrates whose features.py lacks visible_rows():
    re-construct from FEATURES + an explicit y mapping (whatever the
    substrate canonically uses). For now we only support features.py
    with visible_rows(); other shapes return a clear diagnostic.

    Returns (visible_data, error_message):
      - On success: (list of (features_dict, y_observed) pairs, None)
      - On failure: (None, diagnostic message)
    """
    pdir = Path(project_dir)
    features_path = pdir / "features.py"
    if not features_path.exists():
        return None, "no_features_py"

    import importlib.util
    import sys as _sys
    spec = importlib.util.spec_from_file_location(
        "_substrate_features_for_fit", str(features_path)
    )
    if spec is None or spec.loader is None:
        return None, "features_py_spec_unbuildable"

    saved_path = list(_sys.path)
    try:
        if str(pdir) not in _sys.path:
            _sys.path.insert(0, str(pdir))
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            return None, f"features_py_load_failed: {type(exc).__name__}: {exc!s}"[:200]

        # Preferred path: features.py defines visible_rows()
        visible_rows_fn = getattr(module, "visible_rows", None)
        if callable(visible_rows_fn):
            try:
                rows = visible_rows_fn()
            except Exception as exc:  # noqa: BLE001
                return None, f"visible_rows_call_failed: {type(exc).__name__}: {exc!s}"[:200]
            # GP-156 R8 mitigation (2026-04-25): enforce deterministic
            # row order for fit reproducibility. Spec §R8 required
            # canonical feature_keys() ordering; the equivalent at the
            # row level is sorting by id so different runs of the same
            # mutator submission produce identical scipy seeds.
            try:
                rows = sorted(rows, key=lambda e: e[0])
            except Exception:  # noqa: BLE001
                pass  # ids may not be sortable; preserve insertion order
            out: list[tuple[dict, float]] = []
            for entry in rows:
                if len(entry) != 3:
                    continue
                _id, y_obs, feats = entry
                out.append((feats, float(y_obs)))
            if not out:
                return None, "empty_visible_rows"
            return out, None

        # Fallback: features.py has FEATURES dict but no visible_rows()
        # — try test_model.py as a last resort (legacy substrates may
        # still expose VISIBLE_SET there).
        test_model_path = pdir / "test_model.py"
        if not test_model_path.exists():
            return None, "features_py_has_no_visible_rows_and_no_test_model"
        spec2 = importlib.util.spec_from_file_location(
            "_substrate_test_model_for_fit_fallback", str(test_model_path)
        )
        if spec2 is None or spec2.loader is None:
            return None, "test_model_spec_unbuildable_fallback"
        module2 = importlib.util.module_from_spec(spec2)
        try:
            spec2.loader.exec_module(module2)
        except Exception as exc:  # noqa: BLE001
            return None, f"fallback_test_model_load_failed: {type(exc).__name__}"[:200]
        visible_set = getattr(module2, "VISIBLE_SET", None)
        if not visible_set:
            return None, "no_visible_rows_fn_in_features_and_no_VISIBLE_SET_in_test_model"
        out: list[tuple[dict, float]] = []
        for entry in visible_set:
            if len(entry) != 3:
                continue
            _id, y_obs, feats = entry
            out.append((feats, float(y_obs)))
        if not out:
            return None, "fallback_visible_set_empty"
        return out, None
    finally:
        _sys.path[:] = saved_path


def substitute_fitted_model_params(python_code: str, fitted_params: dict[str, float]) -> str:
    """Replace `MODEL_PARAMS = ...` assignment in python_code with the
    fitted-params dict literal. Returns the updated source.

    Tolerant of common annotation patterns:
        MODEL_PARAMS = {}
        MODEL_PARAMS: dict = {}
        MODEL_PARAMS: Dict[str, float] = {}
        MODEL_PARAMS: typing.Dict[str, float] = {}
        MODEL_PARAMS = {'a': 0.5, 'b': 1.0}

    Implementation note (GP-156 reviewer revert, 2026-04-25):
    Previously used AST-based source rewriting which had column-offset
    fragility on Python 3.8-3.10 for empty/single-element dicts (the
    `MODEL_PARAMS = {}` line could vanish entirely after substitution
    when end_lineno/end_col_offset arithmetic took the wrong branch).
    Reverted to regex-only — simpler, smaller surface area, no AST
    line/col arithmetic.

    Pattern intentionally non-greedy over `{...}` content: matches the
    first balanced-by-content single-line dict literal. Multi-line dict
    literals are not supported (the mutator should write MODEL_PARAMS
    on one line per the GP-156 prompt).
    """
    rhs = repr(fitted_params)
    import re as _re
    # Match: optional leading whitespace, MODEL_PARAMS, optional type
    # annotation, =, then a single-line {...} value.
    pattern = _re.compile(
        r"^(\s*MODEL_PARAMS\s*(?::\s*[\w\.\[\], ]*)?\s*=\s*)\{[^{}]*\}",
        _re.MULTILINE,
    )
    new_code, n = pattern.subn(
        lambda m: f"{m.group(1)}{rhs}",
        python_code,
        count=1,
    )
    return new_code if n > 0 else python_code


def _resolve_string_constant(
    node, scope: Optional[dict] = None
) -> Optional[str]:
    """Resolve a string-valued AST node, including BinOp string concatenation,
    JoinedStr (f-string) with Constant parts, and (when ``scope`` is supplied)
    variable references and ``repr(...)`` / ``str(...)`` calls whose arguments
    are constants.

    Returns the string value or None if the node cannot be resolved to a
    plain string at parse time. Handles common LLM emission patterns:
      - "..." (Constant)
      - "a" + "b" + "c" (BinOp(Add))
      - f"a {{x}}" with no actual interpolation (JoinedStr of Constants)
      - "a" + _NAME + "b" where _NAME = "x" appears earlier in the file
      - "a" + repr(0.30) + "b"  (LLM idiom for embedding numeric literals
        into form strings without f-string syntax)

    GP-167 fix (2026-04-25 night): gpt-5.5 emitted PARAMETRIC_FORM as a
    parenthesized string-concatenation block referencing intermediate
    variables (`_BETA_EXPR`) and `repr(float(R_REF))` calls. The previous
    resolver returned None for any node that wasn't a Constant or a pure
    string-only BinOp, so the form was treated as undeclared and the fit
    primitive skipped. The extended resolver walks the file's earlier
    assignments to resolve variable references.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_string_constant(node.left, scope=scope)
        right = _resolve_string_constant(node.right, scope=scope)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.JoinedStr):
        # f-string — resolve when all parts are Constants OR resolvable via scope
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                # f"...{var}..." — resolve the inner expression via scope
                inner = _resolve_string_constant(v.value, scope=scope)
                if inner is None:
                    return None
                parts.append(inner)
            else:
                return None
        return "".join(parts)
    # Variable reference: look up in caller-supplied scope
    if isinstance(node, ast.Name) and scope is not None:
        resolved_node = scope.get(node.id)
        if resolved_node is not None:
            return _resolve_string_constant(resolved_node, scope=scope)
        return None
    # Numeric Constant coerced via repr(...) / str(...) inside a form:
    # `"... " + repr(0.30) + " ..."` is the LLM idiom for stamping a
    # numeric literal into a form string.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in {"repr", "str"} and len(node.args) == 1:
            arg = node.args[0]
            # Direct numeric constant
            if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                return repr(arg.value) if node.func.id == "repr" else str(arg.value)
            # Negative numeric: UnaryOp(USub, Constant)
            if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, ast.USub):
                if isinstance(arg.operand, ast.Constant) and isinstance(arg.operand.value, (int, float)):
                    val = -arg.operand.value
                    return repr(val) if node.func.id == "repr" else str(val)
            # repr(float(NAME)) where NAME resolves to a numeric constant in scope
            if (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Name)
                and arg.func.id in {"float", "int"}
                and len(arg.args) == 1
                and scope is not None
            ):
                inner_arg = arg.args[0]
                if isinstance(inner_arg, ast.Name):
                    inner_node = scope.get(inner_arg.id)
                    if isinstance(inner_node, ast.Constant) and isinstance(inner_node.value, (int, float)):
                        coerced = float(inner_node.value) if arg.func.id == "float" else int(inner_node.value)
                        return repr(coerced) if node.func.id == "repr" else str(coerced)
    return None


def _build_module_scope(tree: ast.AST) -> dict:
    """Walk a parsed module and collect top-level scalar assignments
    (Name -> ast value-node) so `_resolve_string_constant` can resolve
    variable references inside PARAMETRIC_FORM expressions.
    """
    scope: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name):
                scope[t.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                scope[node.target.id] = node.value
    return scope


def extract_form_declaration(
    test_model_text: str,
) -> Optional[tuple[str, list[str], Optional[dict]]]:
    """Parse PARAMETRIC_FORM, PARAMETER_NAMES, and (optional) INIT_RANGE
    from a test_model.py text.

    Returns (form_str, parameter_names, init_range_or_None) or None if
    PARAMETRIC_FORM/PARAMETER_NAMES not declared.

    INIT_RANGE — if declared — should be a dict literal like
        INIT_RANGE = {"a": (0.5, 5.0), "b": (-1.0, 1.0)}
    Used by fit_features to seed scipy multi-start within physical
    parameter ranges (defends against the flat-sigmoid-saturation
    bug that produces success=True with garbage params).
    """
    try:
        tree = ast.parse(test_model_text)
    except SyntaxError:
        return None
    form_value: Optional[str] = None
    names_value: Optional[list[str]] = None
    init_range_value: Optional[dict] = None

    def _target_name(node) -> Optional[str]:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            return t.id if isinstance(t, ast.Name) else None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return node.target.id
        return None

    def _resolve_init_range(value_node) -> Optional[dict]:
        """Resolve INIT_RANGE = {"a": (lo, hi), ...} dict literal."""
        if not isinstance(value_node, ast.Dict):
            return None
        out: dict = {}
        for k_node, v_node in zip(value_node.keys, value_node.values):
            if not (isinstance(k_node, ast.Constant) and isinstance(k_node.value, str)):
                continue
            if not isinstance(v_node, (ast.Tuple, ast.List)):
                continue
            if len(v_node.elts) != 2:
                continue
            try:
                lo = v_node.elts[0]
                hi = v_node.elts[1]
                # Support negative numbers (UnaryOp(USub, Constant))
                def _to_num(n):
                    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                        return float(n.value)
                    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
                        if isinstance(n.operand, ast.Constant) and isinstance(n.operand.value, (int, float)):
                            return -float(n.operand.value)
                    return None
                lo_v = _to_num(lo)
                hi_v = _to_num(hi)
                if lo_v is None or hi_v is None:
                    continue
                out[k_node.value] = (lo_v, hi_v)
            except Exception:
                continue
        return out if out else None

    for node in ast.walk(tree):
        name = _target_name(node)
        if name is None:
            continue
        value_node = node.value if hasattr(node, "value") else None
        if value_node is None:
            continue
        if name == "PARAMETRIC_FORM":
            resolved = _resolve_string_constant(value_node)
            if resolved:
                form_value = resolved
        elif name == "PARAMETER_NAMES":
            if isinstance(value_node, (ast.List, ast.Tuple)):
                extracted = []
                for elt in value_node.elts:
                    s = _resolve_string_constant(elt)
                    if s is not None:
                        extracted.append(s)
                if extracted:
                    names_value = extracted
        elif name == "INIT_RANGE":
            init_range_value = _resolve_init_range(value_node)

    if form_value and names_value:
        return form_value, names_value, init_range_value
    return None
