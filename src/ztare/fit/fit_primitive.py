"""GP-035 Post-LLM Fit Primitive.

After the LLM proposes a functional form, this module:
1. Parses the declared FIT_DECLARATION block from the LLM output
2. Validates the expression against a safe operation whitelist
3. Fits parameters via scipy.optimize.curve_fit against visible-slice evidence
4. Returns fitted parameters + residual map OR typed failure record

Constraints (GP-035 seam Turns 4-6, spec constraints 1-8):
1. Mutator-side only — never inside test_model.py
2. Visible-slice only — never touches hidden holdout
3. Form-first, fit-second — LLM proposes structure, fitter estimates params
4. Auditable return payload — fitted params + residual stats preserved
5. No evaluator weakening — GP-030 stays unchanged
6. Not unconditional — requires parseable FIT_DECLARATION + rubric opt-in
7. Typed failure artifact on fit failure
8. Typed fit declaration, not free-text inference
"""

from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass, field

from ztare.orchestrator.evidence_contract import EvidenceContractError, EvidenceSpec
from ztare.fit.parsers import parse_evidence_typed

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None

try:
    import numpy as np
    from scipy.optimize import curve_fit

    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FitDeclaration:
    """Typed fit declaration parsed from a ```fit_declaration block."""

    expression: str
    independent_vars: list[str]
    parameter_names: list[str]
    initial_guesses: dict[str, float] = field(default_factory=dict)
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class FitSuccess:
    fitted_params: dict[str, float]
    max_abs_residual: float
    mean_abs_residual: float
    rmse: float
    residual_map: list[dict[str, float]]
    # GP-069 / INS-011 complexity-penalty telemetry (added 2026-04-15).
    # Recorded but NOT used for candidate selection — selection logic
    # change is a separate commit so pre-registered runs remain unaffected.
    n_samples: int = 0
    k_params: int = 0
    sse: float = 0.0
    bic: float = 0.0
    aic: float = 0.0
    # GP-095: multi-start convergence metadata (added 2026-04-18).
    n_starts_attempted: int = 1
    n_starts_converged: int = 1
    residual_spread: float = 0.0
    convergence_classification: str = ""


@dataclass
class FitFailure:
    failure_class: str
    attempted_template: str
    solver_diagnostics: str


FitResult = FitSuccess | FitFailure


# ---------------------------------------------------------------------------
# Exponent-grid search (GP-088 overfitting fix)
# ---------------------------------------------------------------------------

# Discrete exponent values that cover physically meaningful power laws.
# A free continuous exponent overfits in finite windows — the correction terms
# bias the optimizer away from the true value (Hardy panel verdict, 2026-04-20).
EXPONENT_GRID = (0.25, 1 / 3, 0.5, 2 / 3, 1.0, 1.5, 2.0)


def detect_power_exponent_params(
    expression: str,
    independent_vars: list[str],
    parameter_names: list[str],
) -> list[str]:
    """Detect parameters used as power-law exponents: ``var ** param``.

    Walks the AST looking for ``BinOp(op=Pow)`` nodes where the base
    involves an independent variable and the exponent is a parameter name.
    Returns the list of parameter names that appear as exponents.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return []

    iv_set = frozenset(independent_vars)
    param_set = frozenset(parameter_names)
    exponent_params: list[str] = []

    def _mentions_var(node: ast.AST) -> bool:
        """True if the subtree contains any independent variable."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in iv_set:
                return True
        return False

    def _is_param(node: ast.AST) -> str | None:
        """Return param name if node is a bare parameter Name."""
        if isinstance(node, ast.Name) and node.id in param_set:
            return node.id
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if _mentions_var(node.left):
                pname = _is_param(node.right)
                if pname and pname not in exponent_params:
                    exponent_params.append(pname)
    return exponent_params


# ---------------------------------------------------------------------------
# Expression validation (AST whitelist)
# ---------------------------------------------------------------------------

_ALLOWED_MATH_ATTRS = frozenset(
    {
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
        "sqrt",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "atan2",
        "sinh",
        "cosh",
        "tanh",
        "pow",
        "fabs",
        "ceil",
        "floor",
        "pi",
        "e",
    }
)

_ALLOWED_DIRECT_CALLS = frozenset({
    "eml",
    "sin", "cos", "tan",
    "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh",
    "exp", "log", "log10", "log2", "log1p", "sqrt",
    "floor", "ceil", "fabs", "abs", "round",
    # Keep the older GP-035 fit_declaration path aligned with the newer
    # feature-dict fitter. These are pure scalar helpers, not imports.
    "sigmoid", "where", "erf", "Rational",
})

# Pure-constant math attributes permitted in ``eml_only`` fit expressions.
# These are attribute reads (not calls) and cannot introduce nonlinearity —
# they are required for the depth-1 Planck representation
# ``eml((gamma*phi/psi)**q, math.e)`` to be reachable under the EML grammar.
_EML_ONLY_CONSTANT_ATTRS = frozenset({"e", "pi"})

# ``math_exp_only`` grammar (GP-061 negative-space generalization target, sandbox_09
# RC step response): permits only the minimal set needed to express a
# first-order exponential with real-valued prefactors. Forbids direct ``eml``
# calls and all other ``math.*`` nonlinearities. Closes the charter contract
# that RC grammar is disjoint from sandbox_07/08's ``eml_only``.
_MATH_EXP_ONLY_ATTRS = frozenset({"e", "pi", "exp", "log", "sqrt"})

# ``math_exp_trig`` grammar: extends math_exp_only with sin/cos for substrates
# where periodicity is not excluded by pre-registration. General capability
# decision, not substrate-specific — see GP-081 grammar debate 2026-04-21.
_MATH_EXP_TRIG_ATTRS = frozenset({"e", "pi", "exp", "log", "sqrt", "sin", "cos"})

_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.FloorDiv,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.Call,
    ast.Attribute,
    ast.IfExp,
    ast.Compare,
    ast.Lt,
    ast.Gt,
    ast.LtE,
    ast.GtE,
    ast.Eq,
    ast.NotEq,
)


def _validate_expression(
    expr_str: str,
    allowed_names: frozenset[str],
    *,
    allowed_math_attrs: frozenset[str] = _ALLOWED_MATH_ATTRS,
    allowed_direct_calls: frozenset[str] = frozenset(),
) -> ast.Expression:
    """Parse expression and walk AST to enforce the safe-operation whitelist."""
    try:
        tree = ast.parse(expr_str, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Expression syntax error: {exc}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise ValueError(
                f"Disallowed AST node: {type(node).__name__}. "
                "Only arithmetic, math.* functions, and declared variables are allowed."
            )
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(
                f"Undeclared variable '{node.id}'. Allowed: {sorted(allowed_names)}"
            )
        if isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == "math"):
                raise ValueError("Attribute access only allowed on 'math' module.")
            if node.attr not in allowed_math_attrs:
                raise ValueError(f"math.{node.attr} not in allowed function list.")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                pass  # validated above
            elif isinstance(node.func, ast.Name):
                if node.func.id not in allowed_direct_calls:
                    raise ValueError(
                        f"Direct call '{node.func.id}()' not allowed here."
                    )
            else:
                raise ValueError("Complex call expressions not allowed.")
    return tree


def _safe_isprime(n: int) -> bool:
    """Trial-division primality test, no external deps."""
    n = int(n)
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    r = int(n ** 0.5)
    i = 3
    while i <= r:
        if n % i == 0:
            return False
        i += 2
    return True


def _safe_factorint(n: int) -> dict:
    """Trial-division integer factorization. Returns {prime: multiplicity}."""
    n = int(n)
    if n < 2:
        return {}
    factors: dict = {}
    while n % 2 == 0:
        factors[2] = factors.get(2, 0) + 1
        n //= 2
    i = 3
    while i * i <= n:
        while n % i == 0:
            factors[i] = factors.get(i, 0) + 1
            n //= i
        i += 2
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def _safe_primefactors(n: int) -> list:
    """Distinct prime factors (sorted)."""
    return sorted(_safe_factorint(n).keys())


def _safe_divisors(n: int) -> list:
    """All positive divisors of n (sorted)."""
    n = int(n)
    if n < 1:
        return []
    ds: list = []
    i = 1
    while i * i <= n:
        if n % i == 0:
            ds.append(i)
            if i != n // i:
                ds.append(n // i)
        i += 1
    return sorted(ds)


def _safe_gcd(a: int, b: int) -> int:
    """Greatest common divisor (Euclidean)."""
    a, b = abs(int(a)), abs(int(b))
    while b:
        a, b = b, a % b
    return a


def _safe_prime_vector(n: int) -> list:
    """Prime signature as sorted list of (prime, exponent) pairs.

    This is the canonical prime-space representation: every positive integer
    n > 1 maps to a unique finite vector over the lattice of primes via the
    fundamental theorem of arithmetic. Returns the same data as factorint(n)
    but in ordered list form for direct iteration.
    """
    return sorted(_safe_factorint(n).items())


def _safe_is_coprime(a: int, b: int) -> bool:
    """True iff gcd(a, b) == 1. Useful for multiplicative-structure testing."""
    return _safe_gcd(a, b) == 1


def _safe_sigmoid(x: float, center: float = 0.0, width: float = 1.0) -> float:
    if width == 0.0:
        return 1.0 if x > center else (0.0 if x < center else 0.5)
    z = (x - center) / width
    if z > 50:
        return 1.0
    if z < -50:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def _safe_where(cond: bool, a: float, b: float) -> float:
    return float(a) if bool(cond) else float(b)


def _safe_rational(a: float, b: float = 1.0) -> float:
    return float(a) / float(b)


_DIRECT_CALL_NS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "log1p": math.log1p,
    "sqrt": math.sqrt,
    "floor": math.floor,
    "ceil": math.ceil,
    "fabs": math.fabs,
    "abs": abs,
    "round": round,
    "sigmoid": _safe_sigmoid,
    "where": _safe_where,
    "erf": math.erf,
    "Rational": _safe_rational,
}


_PY_EXEC_BUILTINS: dict = {
    "range": range, "sum": sum, "len": len, "int": int, "round": round,
    "all": all, "any": any, "abs": abs, "min": min, "max": max,
    "list": list, "sorted": sorted, "enumerate": enumerate, "zip": zip,
    "bool": bool, "float": float, "str": str, "tuple": tuple, "set": set,
    "divmod": divmod, "pow": pow, "True": True, "False": False, "None": None,
    # GP-134 primitive-availability fix (2026-04-23): number-theoretic primitives
    # for discrete substrates. Without these, py_exec on substrates like sopfr
    # or Euler-phi forces the mutator to hand-roll primality inside a 300-byte
    # expression, making structural recovery effectively impossible. Hand-rolled
    # trial-division versions avoid a sympy runtime dependency.
    "isprime": _safe_isprime,
    "is_prime": _safe_isprime,
    "factorint": _safe_factorint,
    "primefactors": _safe_primefactors,
    "divisors": _safe_divisors,
    "gcd": _safe_gcd,
    # GP-134 prime-space standard library (2026-04-23): the mutator needs
    # these to be native cognitive primitives, not something it has to
    # re-derive every expression. prime_vector exposes the canonical
    # prime-space representation; is_coprime supports multiplicative
    # structure testing.
    "prime_vector": _safe_prime_vector,
    "is_coprime": _safe_is_coprime,
}


def _build_model_callable(
    declaration: FitDeclaration,
    *,
    expression_grammar: str | None = None,
):
    """Compile a validated expression into a callable for curve_fit."""
    grammar = (expression_grammar or "").strip().lower()

    # py_exec grammar: allow full Python expressions (list comprehensions,
    # generators, boolean operators) for discrete number-theoretic sequences.
    # Bypasses AST whitelist validation; still sandbox-restricted via builtins.
    if grammar == "py_exec":
        # GP-133 R4 sandbox hardening (2026-04-23): pre-compile AST walk that
        # rejects any attribute access to names starting with '_' (dunders
        # and private names). This closes the classic Python-sandbox escape
        # ().__class__.__base__.__subclasses__() which would otherwise reach
        # BuiltinImporter → arbitrary imports → arbitrary code execution.
        # See GP-133 (internal seam)
        try:
            _ast_tree = ast.parse(declaration.expression, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Expression syntax error: {exc}") from exc
        for _node in ast.walk(_ast_tree):
            if isinstance(_node, ast.Attribute) and _node.attr.startswith("_"):
                raise ValueError(
                    f"py_exec sandbox: dunder/private attribute access not allowed "
                    f"({_node.attr!r}). This closes the classic "
                    f"().__class__.__base__.__subclasses__() sandbox escape. "
                    f"Use only public attributes of whitelisted builtins."
                )
        try:
            code = compile(_ast_tree, "<py_exec>", "eval")
        except SyntaxError as exc:
            raise ValueError(f"Expression syntax error: {exc}") from exc

        def model_fn_exec(xdata, *params):
            param_dict = dict(zip(declaration.parameter_names, params))
            if xdata.ndim == 1:
                xdata = xdata.reshape(1, -1)
            n_pts = xdata.shape[1]
            out = np.empty(n_pts)
            for i in range(n_pts):
                ns: dict = {"math": math, **_PY_EXEC_BUILTINS}
                for j, vname in enumerate(declaration.independent_vars):
                    ns[vname] = int(xdata[j, i])
                ns.update(param_dict)
                try:
                    out[i] = float(eval(code, {"__builtins__": {}}, ns))  # noqa: S307
                except Exception:
                    out[i] = float("nan")
            return out

        return model_fn_exec

    allowed = (
        frozenset(declaration.independent_vars)
        | frozenset(declaration.parameter_names)
        | frozenset({"math"})
        | frozenset(_ALLOWED_DIRECT_CALLS)
    )
    allowed_math_attrs = _ALLOWED_MATH_ATTRS
    allowed_direct_calls = _ALLOWED_DIRECT_CALLS
    if grammar == "eml_only":
        allowed_math_attrs = _EML_ONLY_CONSTANT_ATTRS
        allowed_direct_calls = _ALLOWED_DIRECT_CALLS
        allowed = allowed | frozenset(_ALLOWED_DIRECT_CALLS)
    elif grammar == "math_exp_only":
        allowed_math_attrs = _MATH_EXP_ONLY_ATTRS
        allowed_direct_calls = frozenset()
    elif grammar == "math_exp_trig":
        allowed_math_attrs = _MATH_EXP_TRIG_ATTRS
        allowed_direct_calls = frozenset()
    tree = _validate_expression(
        declaration.expression,
        allowed,
        allowed_math_attrs=allowed_math_attrs,
        allowed_direct_calls=allowed_direct_calls,
    )
    code = compile(tree, "<fit_declaration>", "eval")

    def model_fn(xdata, *params):
        param_dict = dict(zip(declaration.parameter_names, params))
        # Ensure xdata is 2D: (n_vars, n_pts)
        if xdata.ndim == 1:
            xdata = xdata.reshape(1, -1)
        n_pts = xdata.shape[1]
        out = np.empty(n_pts)
        for i in range(n_pts):
            ns = {"math": math, **_DIRECT_CALL_NS}
            if grammar == "eml_only":
                ns["eml"] = lambda x, y: math.exp(x) - math.log(y)
            for j, vname in enumerate(declaration.independent_vars):
                ns[vname] = float(xdata[j, i])
            ns.update(param_dict)
            try:
                out[i] = float(eval(code, {"__builtins__": {}}, ns))  # noqa: S307
            except Exception:
                out[i] = float("nan")
        return out

    return model_fn


# ---------------------------------------------------------------------------
# FIT_DECLARATION parser
# ---------------------------------------------------------------------------


def _repair_json(raw: str) -> str:
    """Best-effort repair of common LLM JSON defects before strict parse.

    Handles: trailing commas, // line comments, single-quoted strings.
    Does not attempt to repair structural errors (mismatched brackets).
    """
    # Strip // line comments (outside string literals is good enough for fit_declaration)
    raw = re.sub(r"//[^\n]*", "", raw)
    # Replace single-quoted strings with double-quoted (simple: no escaped single quotes in values)
    raw = re.sub(r"'([^']*)'", r'"\1"', raw)
    # Remove trailing commas before ] or }
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return raw


def parse_fit_declaration(text: str) -> FitDeclaration | None:
    """Extract ```fit_declaration JSON block from LLM output.

    Returns None if no block found. Raises ValueError on malformed block.
    Attempts lightweight JSON repair before raising on parse failure.
    """
    match = re.search(r"```fit_declaration\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            data = json.loads(_repair_json(raw))
        except json.JSONDecodeError as exc:
            # Last resort: YAML (mutator sometimes emits key: value format)
            if _yaml is not None:
                try:
                    data = _yaml.safe_load(raw)
                    if not isinstance(data, dict):
                        raise ValueError("YAML parsed to non-dict")
                except Exception:
                    raise ValueError(f"FIT_DECLARATION JSON parse error: {exc}") from exc
            else:
                raise ValueError(f"FIT_DECLARATION JSON parse error: {exc}") from exc

    missing = {"expression", "independent_vars", "parameter_names"} - set(data)
    if missing:
        raise ValueError(f"FIT_DECLARATION missing required fields: {missing}")

    return FitDeclaration(
        expression=data["expression"],
        independent_vars=data["independent_vars"],
        parameter_names=data["parameter_names"],
        initial_guesses=data.get("initial_guesses", {}),
        bounds=data.get("bounds", {}),
    )


# ---------------------------------------------------------------------------
# Evidence parser (visible-slice only)
# ---------------------------------------------------------------------------


def parse_evidence_for_fitting(
    evidence_text: str,
    independent_vars: list[str],
) -> tuple[list[list[float]], list[float]] | None:
    """Parse evidence.txt into (xdata_lists, ydata).

    Supports one or two independent variables via two formats:

    **Tabular format (2D):** Three whitespace-separated columns per row:
    ``var1  var2  target``. Column headers (non-numeric first token) are
    skipped automatically. This is the preferred format for 2D inputs such
    as ODE rate-of-change data where both state variables vary per sample.

    **Sweep-block format (2D):** The second variable is read from
    ``=== <var2> = <val> ===`` section headers; the body rows have two
    columns ``var1  target``. Used for grid-sweep experiments.

    For 1D inputs either format reduces to two-column rows ``var1  target``.
    """
    if len(independent_vars) == 2:
        var1, var2 = independent_vars
    elif len(independent_vars) == 1:
        var1 = independent_vars[0]
        var2 = None
    else:
        return None

    xdata: list[list[float]] = [[] for _ in independent_vars]
    ydata: list[float] = []
    current_sweep_val: float | None = None

    # Markdown-table preprocessor (2026-04-25 night, gp159 fix):
    # accept rows like `| 1.3 | 1.6935 |` by stripping pipes, treating
    # `|` as a delimiter. Helps every substrate whose evidence.txt uses
    # markdown table format. No-op for plain whitespace-separated rows.
    def _split_data_row(raw_line: str) -> list[str]:
        line = raw_line.strip()
        if "|" in line:
            # Strip leading/trailing pipes and split on `|`
            inner = line.strip("|").strip()
            parts_md = [p.strip() for p in inner.split("|")]
            # Reject pure separator rows like `|----|----|`
            if all(set(p) <= set("-:= \t") for p in parts_md):
                return []
            return [p for p in parts_md if p]
        return line.split()

    # Detect tabular 2D format: scan for first data row with 3+ numeric columns
    tabular_2d = False
    if var2 is not None:
        for raw_line in evidence_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("==="):
                continue
            parts = _split_data_row(raw_line)
            if len(parts) >= 3:
                try:
                    float(parts[0]); float(parts[1]); float(parts[2])
                    tabular_2d = True
                except ValueError:
                    pass
            break

    for raw_line in evidence_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Sweep header (sweep-block format only)
        if line.startswith("==="):
            core = line.strip("= ").strip()
            _, _, val_str = core.partition("=")
            try:
                current_sweep_val = float(val_str.strip())
            except ValueError:
                current_sweep_val = None
            continue

        parts = _split_data_row(raw_line)

        if tabular_2d:
            # Tabular 2D: expect (var1, var2, target) columns; skip header rows
            if len(parts) < 3:
                continue
            try:
                x1 = float(parts[0])
                x2 = float(parts[1])
                y = float(parts[2])
            except ValueError:
                continue  # header or malformed row
            xdata[0].append(x1)
            xdata[1].append(x2)
            ydata.append(y)
        else:
            # Sweep-block or 1D format
            if len(parts) < 2:
                continue
            # Skip column headers
            try:
                x1 = float(parts[0])
            except ValueError:
                continue
            try:
                y = float(parts[1])
            except ValueError:
                continue
            xdata[0].append(x1)
            if var2 is not None:
                if current_sweep_val is None:
                    continue
                xdata[1].append(current_sweep_val)
            ydata.append(y)

    return (xdata, ydata) if ydata else None


# ---------------------------------------------------------------------------
# Core fitter
# ---------------------------------------------------------------------------

_MAX_FEVAL = 10_000


def _evaluate_discrete_exact(
    declaration: FitDeclaration,
    evidence_text: str,
    *,
    expression_grammar: str | None = None,
    evidence_spec: EvidenceSpec | None = None,
) -> FitResult:
    """Evaluate a fully-specified expression against integer-valued evidence.

    No parameter fitting (curve_fit is unsuitable for discrete/modular
    landscapes).  The LLM must propose concrete constants, not free
    parameters.  Score = exact-match fraction after rounding both sides
    to nearest integer.
    """
    try:
        parsed = (
            parse_evidence_typed(evidence_text, evidence_spec)
            if evidence_spec else parse_evidence_for_fitting(evidence_text, declaration.independent_vars)
        )
    except EvidenceContractError as error:
        return FitFailure(
            failure_class="evidence_contract_error",
            attempted_template=declaration.expression,
            solver_diagnostics=str(error),
        )
    if parsed is None:
        return FitFailure(
            failure_class="evidence_parse_error",
            attempted_template=declaration.expression,
            solver_diagnostics="Could not parse evidence for the declared independent variables.",
        )

    xdata_lists, ydata_list = parsed
    if not _SCIPY_AVAILABLE:
        return FitFailure(
            failure_class="no_scipy",
            attempted_template=declaration.expression,
            solver_diagnostics="scipy/numpy is not installed",
        )
    xdata = np.array(xdata_lists)
    ydata = np.array(ydata_list)

    try:
        model_fn = _build_model_callable(
            declaration,
            expression_grammar=expression_grammar,
        )
    except ValueError as exc:
        return FitFailure(
            failure_class="expression_validation_error",
            attempted_template=declaration.expression,
            solver_diagnostics=str(exc),
        )

    if declaration.parameter_names:
        params = [
            declaration.initial_guesses.get(name, 0.0)
            for name in declaration.parameter_names
        ]
        y_pred = model_fn(xdata, *params)
        fitted_params = dict(zip(declaration.parameter_names, params))
    else:
        y_pred = model_fn(xdata)
        fitted_params = {}

    y_pred_int = np.round(y_pred).astype(int)
    y_true_int = np.round(ydata).astype(int)
    matches = y_pred_int == y_true_int
    exact_match_fraction = float(np.mean(matches))
    mismatch_fraction = 1.0 - exact_match_fraction

    if xdata.ndim == 1:
        xdata = xdata.reshape(1, -1)

    residual_map: list[dict[str, float]] = []
    for i in range(len(ydata)):
        pt: dict[str, float] = {}
        for j, vname in enumerate(declaration.independent_vars):
            pt[vname] = float(xdata[j, i])
        pt["observed"] = float(ydata[i])
        pt["predicted"] = float(y_pred[i])
        pt["residual"] = 0.0 if matches[i] else 1.0
        residual_map.append(pt)

    n_samples = int(len(ydata))
    k_params = int(len(declaration.parameter_names))

    return FitSuccess(
        fitted_params=fitted_params,
        max_abs_residual=mismatch_fraction,
        mean_abs_residual=mismatch_fraction,
        rmse=mismatch_fraction,
        residual_map=residual_map,
        n_samples=n_samples,
        k_params=k_params,
        sse=float(np.sum(~matches)),
        bic=0.0,
        aic=0.0,
    )


def fit_parameters(
    declaration: FitDeclaration,
    evidence_text: str,
    *,
    required_dimensionality: int | None = None,
    expression_grammar: str | None = None,
    score_mode: str = "continuous_l2",
    n_starts: int = 1,
    gate_threshold: float = 0.05,
    evidence_spec: EvidenceSpec | None = None,
) -> FitResult:
    """Fit parameters for a declared functional form against visible-slice evidence.

    If required_dimensionality is set, reject declarations whose independent_vars
    count doesn't match (Finding 5: prevent 1-var fits on 2-var sandboxes).

    score_mode:
      - "continuous_l2" (default): scipy curve_fit, L2 residual
      - "discrete_exact": no fitting; count exact integer matches

    n_starts (GP-095):
      When > 1, run curve_fit from N random starting points within bounds.
      Classify the outcome:
        - "reachable_low_residual": best residual < gate_threshold, >= 60% of starts converge
        - "pathological_surface": best residual < gate_threshold but < 60% converge,
          OR residual_spread > 50% of best_residual (ill-conditioned surface)
        - "ceiling_candidate": all starts converge to similar high residual

    gate_threshold:
      Residual threshold for "reachable" classification. Must match the rubric's
      gate_residual_threshold so the classification is consistent with how the run scores.
    """
    if (
        required_dimensionality is not None
        and len(declaration.independent_vars) != required_dimensionality
    ):
        return FitFailure(
            failure_class="dimensionality_mismatch",
            attempted_template=declaration.expression,
            solver_diagnostics=(
                f"Declaration has {len(declaration.independent_vars)} independent var(s) "
                f"({declaration.independent_vars}) but project requires "
                f"{required_dimensionality}. Declare all required variables."
            ),
        )

    if evidence_spec and tuple(declaration.independent_vars) != evidence_spec.independent_vars:
        return FitFailure(
            failure_class="evidence_contract_mismatch",
            attempted_template=declaration.expression,
            solver_diagnostics=(
                f"Declaration variables {declaration.independent_vars!r} do not match "
                f"the typed evidence variables {list(evidence_spec.independent_vars)!r}."
            ),
        )

    if score_mode == "discrete_exact":
        return _evaluate_discrete_exact(
            declaration,
            evidence_text,
            expression_grammar=expression_grammar,
            evidence_spec=evidence_spec,
        )

    if not _SCIPY_AVAILABLE:
        return FitFailure(
            failure_class="no_scipy",
            attempted_template=declaration.expression,
            solver_diagnostics="scipy is not installed",
        )

    try:
        parsed = (
            parse_evidence_typed(evidence_text, evidence_spec)
            if evidence_spec else parse_evidence_for_fitting(evidence_text, declaration.independent_vars)
        )
    except EvidenceContractError as error:
        return FitFailure(
            failure_class="evidence_contract_error",
            attempted_template=declaration.expression,
            solver_diagnostics=str(error),
        )
    if parsed is None:
        return FitFailure(
            failure_class="evidence_parse_error",
            attempted_template=declaration.expression,
            solver_diagnostics="Could not parse evidence for the declared independent variables.",
        )

    xdata_lists, ydata_list = parsed
    xdata = np.array(xdata_lists)
    ydata = np.array(ydata_list)

    try:
        model_fn = _build_model_callable(
            declaration,
            expression_grammar=expression_grammar,
        )
    except ValueError as exc:
        return FitFailure(
            failure_class="expression_validation_error",
            attempted_template=declaration.expression,
            solver_diagnostics=str(exc),
        )

    lo = [
        declaration.bounds.get(name, (-np.inf, np.inf))[0]
        for name in declaration.parameter_names
    ]
    hi = [
        declaration.bounds.get(name, (-np.inf, np.inf))[1]
        for name in declaration.parameter_names
    ]
    # Clamp initial guess into declared bounds — prevents immediate solver
    # rejection when the mutator omits an initial_guess for a parameter whose
    # bounds exclude the default of 1.0. np.clip is a no-op for ±inf bounds.
    # GP-212: Use 0.1 as default for composite params (ch0_/ch1_ prefixed)
    # to avoid exp overflow. Standard params keep 1.0 default.
    def _default_p0(name: str) -> float:
        if name.startswith("ch0_") or name.startswith("ch1_") or name.startswith("tail_"):
            return 0.1
        return 1.0

    p0 = [
        float(np.clip(declaration.initial_guesses.get(name, _default_p0(name)), lo[i], hi[i]))
        for i, name in enumerate(declaration.parameter_names)
    ]

    # GP-095: multi-start fitting with convergence classification.
    # Run curve_fit from n_starts different starting points. The first
    # start uses the declared initial_guesses; additional starts use
    # random points within bounds (or perturbed from p0 if unbounded).
    import random as _rng
    _seed_gen = _rng.Random(42)  # deterministic seeds for reproducibility

    def _random_p0() -> list[float]:
        """Generate a random starting point within bounds.

        For fully unbounded parameters, we must not multiply by p0[i] when
        p0[i] == 0 — that collapses every start to the same point. Instead
        use a scale derived from max(abs(p0[i]), 1.0) so zero-centered params
        still get meaningful spread.
        """
        out = []
        for i, name in enumerate(declaration.parameter_names):
            lb, ub = lo[i], hi[i]
            if np.isfinite(lb) and np.isfinite(ub):
                out.append(_seed_gen.uniform(lb, ub))
            elif np.isfinite(lb):
                scale = max(1.0, abs(p0[i]))
                out.append(lb + abs(_seed_gen.gauss(0, scale)))
            elif np.isfinite(ub):
                scale = max(1.0, abs(p0[i]))
                out.append(ub - abs(_seed_gen.gauss(0, scale)))
            else:
                # Fully unbounded: use additive perturbation scaled to
                # max(|p0|, 1.0). Never multiply — zero stays zero otherwise.
                scale = max(1.0, abs(p0[i]))
                out.append(_seed_gen.gauss(p0[i], scale * 2.0))
        return out

    _start_points = [p0] + [_random_p0() for _ in range(max(0, n_starts - 1))]
    _results: list[tuple[np.ndarray, float]] = []  # (popt, ranking_residual)
    _last_exc: Exception | None = None

    # GP-096: When fit_score_mode is "continuous_rmse", align the SciPy
    # optimizer with the gate metric by using sigma=ydata (relative weighting).
    # This makes curve_fit minimise sum((pred-obs)^2 / obs^2), which is
    # identical to the normalised RMSE the gate harness measures. Without this,
    # curve_fit uses absolute squared residuals, which under-weights small
    # observed values (e.g. tail points) and produces low absolute residual but
    # high normalised residual — causing the gate to fail even when SciPy
    # reports a successful fit.
    # Guard: sigma weighting requires all ydata > 0. Fallback to unweighted L2
    # if any non-positive value is present (avoids ZeroDivisionError).
    _use_sigma_weights = (
        score_mode == "continuous_rmse"
        and bool(np.all(ydata > 0))
    )

    def _ranking_residual(y_obs: np.ndarray, y_pred: np.ndarray) -> float:
        """Scalar used to rank / compare candidate fits.

        For continuous_rmse mode: max normalised (relative) residual.
        For all other modes: max absolute residual (original behaviour).
        """
        if _use_sigma_weights:
            # normalised residuals: |(pred-obs)/obs|
            safe_obs = np.where(y_obs != 0, y_obs, 1.0)
            return float(np.max(np.abs((y_pred - y_obs) / safe_obs)))
        return float(np.max(np.abs(y_obs - y_pred)))

    for _sp in _start_points:
        try:
            _curve_fit_kwargs: dict = dict(
                p0=_sp,
                bounds=(lo, hi),
                maxfev=_MAX_FEVAL,
            )
            if _use_sigma_weights:
                _curve_fit_kwargs["sigma"] = ydata
                _curve_fit_kwargs["absolute_sigma"] = False
            _popt, _ = curve_fit(model_fn, xdata, ydata, **_curve_fit_kwargs)
            _y_pred = model_fn(xdata, *_popt)
            _res = _ranking_residual(ydata, _y_pred)
            _results.append((_popt, _res))
        except (RuntimeError, Exception) as exc:
            _last_exc = exc

    if not _results:
        _exc = _last_exc or RuntimeError("All starts failed")
        _fc = "divergence" if isinstance(_exc, RuntimeError) else "solver_error"
        return FitFailure(
            failure_class=_fc,
            attempted_template=declaration.expression,
            solver_diagnostics=str(_exc),
        )

    # Pick the best result (lowest ranking residual)
    _results.sort(key=lambda r: r[1])
    popt = _results[0][0]
    _best_residual = _results[0][1]

    # GP-095 convergence classification
    _n_attempted = len(_start_points)
    _n_converged = len(_results)
    _all_residuals = [r[1] for r in _results]
    _residual_spread = max(_all_residuals) - min(_all_residuals) if len(_all_residuals) > 1 else 0.0

    # Classification uses the caller-supplied gate threshold so the label is
    # consistent with how the run will score. Default 0.05 is a fallback only.
    _classification = ""
    if _n_converged > 0 and _n_attempted >= 2:
        _conv_rate = _n_converged / _n_attempted
        if _best_residual < gate_threshold:
            # At least one start found a low-residual solution.
            if _conv_rate >= 0.6:
                _classification = "reachable_low_residual"
            else:
                # Low residual achievable but hard to find: surface is navigable
                # but the basin is narrow. Still classifiable as pathological.
                _classification = "pathological_surface"
        elif _residual_spread > _best_residual * 0.5:
            # Starts converge to very different residuals: ill-conditioned loss.
            _classification = "pathological_surface"
        else:
            # All starts converge to similar high residual: grammar cannot fit.
            _classification = "ceiling_candidate"
    elif _n_converged == 0:
        _classification = ""  # all starts failed; FitFailure already returned above
    # n_attempts == 1: single start, no multi-start signal available.

    fitted_params = {
        name: float(val) for name, val in zip(declaration.parameter_names, popt)
    }

    y_pred = model_fn(xdata, *popt)
    residuals = np.abs(ydata - y_pred)

    if xdata.ndim == 1:
        xdata = xdata.reshape(1, -1)

    residual_map: list[dict[str, float]] = []
    for i in range(len(ydata)):
        pt: dict[str, float] = {}
        for j, vname in enumerate(declaration.independent_vars):
            pt[vname] = float(xdata[j, i])
        pt["observed"] = float(ydata[i])
        pt["predicted"] = float(y_pred[i])
        pt["residual"] = float(residuals[i])
        residual_map.append(pt)

    n_samples = int(len(ydata))
    k_params = int(len(declaration.parameter_names))
    sse = float(np.sum((ydata - y_pred) ** 2))
    sse_safe = sse if sse > 0 else 1e-300
    if n_samples > 0:
        log_term = math.log(sse_safe / n_samples)
        bic = n_samples * log_term + k_params * math.log(n_samples)
        aic = n_samples * log_term + 2.0 * k_params
    else:
        bic = 0.0
        aic = 0.0

    base_result = FitSuccess(
        fitted_params=fitted_params,
        max_abs_residual=float(np.max(residuals)),
        mean_abs_residual=float(np.mean(residuals)),
        rmse=float(np.sqrt(np.mean(residuals**2))),
        residual_map=residual_map,
        n_samples=n_samples,
        k_params=k_params,
        sse=sse,
        bic=bic,
        aic=aic,
        n_starts_attempted=_n_attempted,
        n_starts_converged=_n_converged,
        residual_spread=_residual_spread,
        convergence_classification=_classification,
    )

    # GP-088 exponent-grid refinement: if the expression contains free power-law
    # exponents (var**param), try fixing each to a discrete grid and compare by BIC.
    # A free continuous exponent overfits finite windows — the correction terms in
    # asymptotic expansions bias curve_fit away from the true rational exponent.
    _exp_params = detect_power_exponent_params(
        declaration.expression,
        declaration.independent_vars,
        declaration.parameter_names,
    )
    if _exp_params:
        base_result = _refine_exponent_grid(
            base_result=base_result,
            declaration=declaration,
            model_fn=model_fn,
            xdata=xdata,
            ydata=ydata,
            exponent_params=_exp_params,
            lo=lo,
            hi=hi,
            score_mode=score_mode,
        )

    return base_result


# ---------------------------------------------------------------------------
# Exponent-grid refinement (post-fit)
# ---------------------------------------------------------------------------


def _refine_exponent_grid(
    base_result: FitSuccess,
    declaration: FitDeclaration,
    model_fn,
    xdata: "np.ndarray",
    ydata: "np.ndarray",
    exponent_params: list[str],
    lo: list[float],
    hi: list[float],
    score_mode: str,
) -> FitSuccess:
    """Try fixing each power-law exponent to discrete grid values and refit.

    Compares all candidates (original free-exponent + each grid fix) by BIC.
    Returns the best. If the original is best, returns it unchanged.

    The grid search reduces the effective parameter count by 1 for each fixed
    exponent, which the BIC penalty rewards. This counteracts the overfitting
    tendency of curve_fit in finite windows (GP-088 Hardy-Ramanujan finding).
    """
    best = base_result
    best_bic = base_result.bic

    _use_sigma = (
        score_mode == "continuous_rmse"
        and bool(np.all(ydata > 0))
    )

    for exp_param in exponent_params:
        exp_idx = declaration.parameter_names.index(exp_param)

        for grid_val in EXPONENT_GRID:
            # Build a reduced declaration: remove the exponent param, substitute
            # its value as a constant in the expression.
            reduced_params = [
                p for p in declaration.parameter_names if p != exp_param
            ]
            if not reduced_params:
                continue  # nothing left to fit

            # Substitute the exponent param with the grid value in the expression
            # by creating a modified model_fn that fixes the exponent.
            fixed_vals = {exp_param: grid_val}

            def _make_constrained_fn(fixed: dict):
                def constrained_fn(xdata_inner, *free_params):
                    # Reassemble full param vector with fixed values inserted
                    full_params = []
                    free_idx = 0
                    for pname in declaration.parameter_names:
                        if pname in fixed:
                            full_params.append(fixed[pname])
                        else:
                            full_params.append(free_params[free_idx])
                            free_idx += 1
                    return model_fn(xdata_inner, *full_params)
                return constrained_fn

            constrained_fn = _make_constrained_fn(fixed_vals)

            # Reduced bounds and p0
            r_lo = [lo[i] for i, p in enumerate(declaration.parameter_names) if p != exp_param]
            r_hi = [hi[i] for i, p in enumerate(declaration.parameter_names) if p != exp_param]
            r_p0 = [
                float(np.clip(declaration.initial_guesses.get(p, 1.0), r_lo[j], r_hi[j]))
                for j, p in enumerate(reduced_params)
            ]

            try:
                kw: dict = dict(p0=r_p0, bounds=(r_lo, r_hi), maxfev=_MAX_FEVAL)
                if _use_sigma:
                    kw["sigma"] = ydata
                    kw["absolute_sigma"] = False
                popt, _ = curve_fit(constrained_fn, xdata, ydata, **kw)
                y_pred = constrained_fn(xdata, *popt)
                residuals = np.abs(ydata - y_pred)
                max_res = float(np.max(residuals))
                sse = float(np.sum((ydata - y_pred) ** 2))
                n = len(ydata)
                k = len(reduced_params)  # fewer params → BIC reward
                sse_safe = sse if sse > 0 else 1e-300
                bic = n * math.log(sse_safe / n) + k * math.log(n)

                if bic < best_bic:
                    # Reassemble full param dict
                    fitted = {}
                    free_idx = 0
                    for pname in declaration.parameter_names:
                        if pname in fixed_vals:
                            fitted[pname] = fixed_vals[pname]
                        else:
                            fitted[pname] = float(popt[free_idx])
                            free_idx += 1

                    residual_map: list[dict[str, float]] = []
                    xd = xdata if xdata.ndim == 2 else xdata.reshape(1, -1)
                    for i in range(n):
                        pt: dict[str, float] = {}
                        for j, vname in enumerate(declaration.independent_vars):
                            pt[vname] = float(xd[j, i])
                        pt["observed"] = float(ydata[i])
                        pt["predicted"] = float(y_pred[i])
                        pt["residual"] = float(residuals[i])
                        residual_map.append(pt)

                    aic = n * math.log(sse_safe / n) + 2.0 * k

                    best_bic = bic
                    best = FitSuccess(
                        fitted_params=fitted,
                        max_abs_residual=max_res,
                        mean_abs_residual=float(np.mean(residuals)),
                        rmse=float(np.sqrt(np.mean(residuals ** 2))),
                        residual_map=residual_map,
                        n_samples=n,
                        k_params=k,
                        sse=sse,
                        bic=bic,
                        aic=aic,
                        n_starts_attempted=base_result.n_starts_attempted,
                        n_starts_converged=base_result.n_starts_converged,
                        residual_spread=base_result.residual_spread,
                        convergence_classification=base_result.convergence_classification,
                    )
                    print(
                        f"    📐 Exponent grid: {exp_param}={grid_val} "
                        f"BIC={bic:.1f} < free BIC={base_result.bic:.1f} "
                        f"(max_res={max_res:.5f})"
                    )
            except Exception:
                continue  # grid value doesn't fit; skip

    return best


# ---------------------------------------------------------------------------
# Parameter substitution into test_model.py code
# ---------------------------------------------------------------------------


def substitute_fitted_params(
    python_code: str,
    fitted_params: dict[str, float],
) -> str:
    """Replace matching values in a MODEL_PARAMS dict literal.

    Falls back to returning code unchanged if MODEL_PARAMS cannot be found
    (the candidate then proceeds with the LLM's guessed parameters).
    Logs a warning for any fitted param name that doesn't match a MODEL_PARAMS key.
    """
    unmatched = []
    for name, value in fitted_params.items():
        # Match "name": <number> or 'name': <number>
        pattern = rf"""(["\']){re.escape(name)}\1\s*:\s*[-+]?[\d.eE+\-]+"""
        if not re.search(pattern, python_code):
            unmatched.append(name)
        python_code = re.sub(
            pattern,
            f'"{name}": {value}',
            python_code,
        )
    if unmatched:
        print(
            f"⚠️ GP-035 fit primitive: fitted param(s) {unmatched} not found in "
            f"MODEL_PARAMS — substitution skipped for these (case-sensitive match). "
            f"Ensure FIT_DECLARATION parameter_names match MODEL_PARAMS keys exactly."
        )
    return python_code


# ---------------------------------------------------------------------------
# Workspace artifact serialization
# ---------------------------------------------------------------------------


def fit_result_to_json(result: FitResult, declaration: FitDeclaration) -> str:
    """Serialize fit result for workspace/fit_result.json."""
    if isinstance(result, FitSuccess):
        diag = diagnose_residual_pattern(result, declaration.independent_vars)
        return json.dumps(
            {
                "status": "success",
                "expression": declaration.expression,
                "independent_vars": declaration.independent_vars,
                "parameter_names": declaration.parameter_names,
                "fitted_params": result.fitted_params,
                "max_abs_residual": result.max_abs_residual,
                "mean_abs_residual": result.mean_abs_residual,
                "rmse": result.rmse,
                "residual_diagnostic": {
                    "classification": diag.classification,
                    "variable_correlations": diag.variable_correlations,
                    "sign_bias_regions": diag.sign_bias_regions,
                    "worst_region": diag.worst_region,
                    "concentration_ratio": diag.concentration_ratio,
                },
                "residual_map": result.residual_map,
                "convergence": {
                    "n_starts_attempted": result.n_starts_attempted,
                    "n_starts_converged": result.n_starts_converged,
                    "residual_spread": result.residual_spread,
                    "convergence_classification": result.convergence_classification,
                },
            },
            indent=2,
        )
    return json.dumps(
        {
            "status": "failure",
            "failure_class": result.failure_class,
            "attempted_template": result.attempted_template,
            "solver_diagnostics": result.solver_diagnostics,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Residual pattern diagnostics (GP-037 finding: form-family escape)
# ---------------------------------------------------------------------------


@dataclass
class ResidualDiagnostic:
    """Domain-general structural diagnosis of fit residuals.

    When the fitter succeeds but residuals are too high, this tells the mutator
    WHERE the form breaks (which variables, which regions) without prescribing
    WHAT form to use.  The right level of abstraction: more informative than
    "your score is 0" but less prescriptive than "add a denominator term."
    """

    classification: str  # "parametric_noise" | "structural_misfit" | "outlier_dominated"
    variable_correlations: dict[str, float]  # var_name -> Pearson r with |residual|
    sign_bias_regions: list[str]  # e.g. "consistently_positive at phi > 3.0"
    worst_region: str  # e.g. "high phi, low psi"
    concentration_ratio: float  # fraction of total residual in worst 20% of points


def diagnose_residual_pattern(
    result: FitSuccess,
    independent_vars: list[str],
) -> ResidualDiagnostic:
    """Compute domain-general structural diagnostics from fit residuals.

    Uses only stdlib + numpy (already a dependency via scipy).
    """
    rmap = result.residual_map
    n = len(rmap)
    if n < 5:
        return ResidualDiagnostic(
            classification="insufficient_data",
            variable_correlations={},
            sign_bias_regions=[],
            worst_region="N/A",
            concentration_ratio=0.0,
        )

    abs_residuals = np.array([pt["residual"] for pt in rmap])
    signed_residuals = np.array(
        [pt["observed"] - pt["predicted"] for pt in rmap]
    )

    # --- Variable correlations ---
    var_correlations: dict[str, float] = {}
    for var in independent_vars:
        vals = np.array([pt[var] for pt in rmap])
        if np.std(vals) < 1e-12 or np.std(abs_residuals) < 1e-12:
            var_correlations[var] = 0.0
            continue
        r = float(np.corrcoef(vals, abs_residuals)[0, 1])
        var_correlations[var] = round(r, 3) if not np.isnan(r) else 0.0

    # --- Sign-bias regions ---
    sign_bias: list[str] = []
    for var in independent_vars:
        vals = np.array([pt[var] for pt in rmap])
        median_val = float(np.median(vals))

        hi_mask = vals > median_val
        lo_mask = vals <= median_val

        if np.sum(hi_mask) >= 3:
            hi_sign_frac = float(np.mean(signed_residuals[hi_mask] > 0))
            if hi_sign_frac > 0.80:
                sign_bias.append(
                    f"consistently positive (model underestimates) at {var} > {median_val:.3f}"
                )
            elif hi_sign_frac < 0.20:
                sign_bias.append(
                    f"consistently negative (model overestimates) at {var} > {median_val:.3f}"
                )

        if np.sum(lo_mask) >= 3:
            lo_sign_frac = float(np.mean(signed_residuals[lo_mask] > 0))
            if lo_sign_frac > 0.80:
                sign_bias.append(
                    f"consistently positive (model underestimates) at {var} <= {median_val:.3f}"
                )
            elif lo_sign_frac < 0.20:
                sign_bias.append(
                    f"consistently negative (model overestimates) at {var} <= {median_val:.3f}"
                )

    # --- Worst region ---
    top_k = max(1, n // 5)
    top_indices = np.argsort(abs_residuals)[-top_k:]
    region_parts = []
    for var in independent_vars:
        vals = np.array([pt[var] for pt in rmap])
        top_vals = vals[top_indices]
        all_median = float(np.median(vals))
        top_median = float(np.median(top_vals))
        if top_median > all_median:
            region_parts.append(f"high {var}")
        else:
            region_parts.append(f"low {var}")
    worst_region = ", ".join(region_parts) if region_parts else "uniform"

    # --- Concentration ratio ---
    total_residual = float(np.sum(abs_residuals))
    top_residual = float(np.sum(abs_residuals[top_indices]))
    concentration = round(top_residual / total_residual, 3) if total_residual > 0 else 0.0

    # --- Classification ---
    # Only classify as structural if the residual is above numerical noise.
    # The primary gating (inject only when max_abs >> gate threshold) lives
    # in autoresearch_loop.py.  This check prevents the classifier from
    # seeing structure in floating-point-level residuals.
    obs_values = np.array([pt.get("observed", 0.0) for pt in rmap])
    obs_range = float(np.ptp(obs_values)) if len(obs_values) > 1 else 1.0
    mean_abs = float(np.mean(abs_residuals))
    residual_is_material = (mean_abs > 1e-6 * max(obs_range, 1.0))

    has_strong_correlation = any(abs(r) > 0.4 for r in var_correlations.values())
    has_sign_bias = len(sign_bias) > 0
    is_concentrated = concentration > 0.40  # top 20% of points carry >40% of residual

    if residual_is_material and (has_strong_correlation or has_sign_bias):
        classification = "structural_misfit"
    elif residual_is_material and is_concentrated:
        classification = "outlier_dominated"
    else:
        classification = "parametric_noise"

    return ResidualDiagnostic(
        classification=classification,
        variable_correlations=var_correlations,
        sign_bias_regions=sign_bias,
        worst_region=worst_region,
        concentration_ratio=concentration,
    )


def format_diagnostic_for_prompt(diag: ResidualDiagnostic) -> str:
    """Format residual diagnostic for mutator prompt injection."""
    lines = ["RESIDUAL PATTERN DIAGNOSTIC:"]
    lines.append(f"  Classification: {diag.classification.upper()}")

    if diag.variable_correlations:
        corr_parts = [
            f"{var} (r={r:+.3f})"
            for var, r in diag.variable_correlations.items()
            if abs(r) > 0.15
        ]
        if corr_parts:
            lines.append(f"  Residual correlated with: {', '.join(corr_parts)}")

    if diag.sign_bias_regions:
        lines.append("  Sign bias detected:")
        for bias in diag.sign_bias_regions:
            lines.append(f"    - {bias}")

    lines.append(f"  Worst residuals concentrated at: {diag.worst_region}")
    lines.append(
        f"  Concentration: top 20% of points carry {diag.concentration_ratio:.0%} of total residual"
    )

    if diag.classification == "structural_misfit":
        lines.append(
            "  NOTE: The residual pattern is systematic, not random. "
            "Residual magnitude correlates with the variables and regions listed above."
        )
    elif diag.classification == "outlier_dominated":
        lines.append(
            "  NOTE: Residual is concentrated in a small number of points "
            "in the region listed above."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------


def format_residual_map_for_prompt(result: FitSuccess, max_rows: int = 30) -> str:
    """Format fit result as a compact table for injection into the next mutator prompt."""
    lines = [
        "PREVIOUS ITERATION FIT RESULT (GP-035 fit primitive):",
        f"  Fitted params: {result.fitted_params}",
        f"  Max |residual|: {result.max_abs_residual:.6f}",
        f"  Mean |residual|: {result.mean_abs_residual:.6f}",
        f"  RMSE: {result.rmse:.6f}",
        "",
        "  Per-point residuals (worst first):",
    ]
    sorted_map = sorted(result.residual_map, key=lambda p: p["residual"], reverse=True)
    for pt in sorted_map[:max_rows]:
        var_parts = " ".join(
            f"{k}={v:.4f}"
            for k, v in pt.items()
            if k not in ("observed", "predicted", "residual")
        )
        lines.append(
            f"    {var_parts}  obs={pt['observed']:.5f}  "
            f"pred={pt['predicted']:.5f}  |res|={pt['residual']:.5f}"
        )
    if len(sorted_map) > max_rows:
        lines.append(f"    ... ({len(sorted_map) - max_rows} more points omitted)")
    return "\n".join(lines)


def format_residual_surface_for_prompt(
    result: FitSuccess,
    *,
    include_observed: bool = False,
    include_predicted: bool = False,
) -> str:
    """Format the full residual surface in raw row order for cold successor runs."""
    lines = [
        "FULL VISIBLE-SLICE RESIDUAL SURFACE:",
        f"  Max |residual|: {result.max_abs_residual:.6f}",
        f"  Mean |residual|: {result.mean_abs_residual:.6f}",
        f"  RMSE: {result.rmse:.6f}",
        "",
        "  Rows:",
    ]
    for pt in result.residual_map:
        var_parts = " ".join(
            f"{k}={v:.4f}"
            for k, v in pt.items()
            if k not in ("observed", "predicted", "residual")
        )
        row = [f"    {var_parts}", f"residual={pt['residual']:+.5f}"]
        if include_observed:
            row.append(f"obs={pt['observed']:.5f}")
        if include_predicted:
            row.append(f"pred={pt['predicted']:.5f}")
        lines.append("  ".join(row))
    return "\n".join(lines)
