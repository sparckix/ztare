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


@dataclass
class FitFailure:
    failure_class: str
    attempted_template: str
    solver_diagnostics: str


FitResult = FitSuccess | FitFailure


# ---------------------------------------------------------------------------
# Expression validation (AST whitelist)
# ---------------------------------------------------------------------------

_ALLOWED_MATH_ATTRS = frozenset(
    {
        "exp",
        "log",
        "log10",
        "log2",
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

_ALLOWED_DIRECT_CALLS = frozenset({"eml"})

# Pure-constant math attributes permitted in ``eml_only`` fit expressions.
# These are attribute reads (not calls) and cannot introduce nonlinearity —
# they are required for the depth-1 Planck representation
# ``eml((gamma*phi/psi)**q, math.e)`` to be reachable under the EML grammar.
_EML_ONLY_CONSTANT_ATTRS = frozenset({"e", "pi"})

# ``math_exp_only`` grammar (GP-061 Component B generalization target, sandbox_09
# RC step response): permits only the minimal set needed to express a
# first-order exponential with real-valued prefactors. Forbids direct ``eml``
# calls and all other ``math.*`` nonlinearities. Closes the charter contract
# that RC grammar is disjoint from sandbox_07/08's ``eml_only``.
_MATH_EXP_ONLY_ATTRS = frozenset({"e", "pi", "exp", "log", "sqrt"})

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


def _build_model_callable(
    declaration: FitDeclaration,
    *,
    expression_grammar: str | None = None,
):
    """Compile a validated expression into a callable for curve_fit."""
    grammar = (expression_grammar or "").strip().lower()
    allowed = (
        frozenset(declaration.independent_vars)
        | frozenset(declaration.parameter_names)
        | frozenset({"math"})
    )
    allowed_math_attrs = _ALLOWED_MATH_ATTRS
    allowed_direct_calls = frozenset()
    if grammar == "eml_only":
        allowed_math_attrs = _EML_ONLY_CONSTANT_ATTRS
        allowed_direct_calls = _ALLOWED_DIRECT_CALLS
        allowed = allowed | frozenset(_ALLOWED_DIRECT_CALLS)
    elif grammar == "math_exp_only":
        allowed_math_attrs = _MATH_EXP_ONLY_ATTRS
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
            ns = {"math": math}
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


def parse_fit_declaration(text: str) -> FitDeclaration | None:
    """Extract ```fit_declaration JSON block from LLM output.

    Returns None if no block found. Raises ValueError on malformed block.
    """
    match = re.search(r"```fit_declaration\s*\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
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
    """Parse evidence.txt sweep blocks into (xdata_lists, ydata).

    Supports one or two independent variables.  For two variables the
    second is read from ``=== <var2> = <val> ===`` sweep headers.
    """
    if len(independent_vars) == 2:
        var1, _ = independent_vars
    elif len(independent_vars) == 1:
        var1 = independent_vars[0]
    else:
        return None

    xdata: list[list[float]] = [[] for _ in independent_vars]
    ydata: list[float] = []
    current_sweep_val: float | None = None

    for raw_line in evidence_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Sweep header
        if line.startswith("==="):
            core = line.strip("= ").strip()
            _, _, val_str = core.partition("=")
            try:
                current_sweep_val = float(val_str.strip())
            except ValueError:
                current_sweep_val = None
            continue

        # Skip column headers
        if line.lower().startswith(var1) or line.lower().startswith("phi"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            x1 = float(parts[0])
            y = float(parts[1])
        except ValueError:
            continue

        xdata[0].append(x1)
        if len(independent_vars) == 2:
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
) -> FitResult:
    """Evaluate a fully-specified expression against integer-valued evidence.

    No parameter fitting (curve_fit is unsuitable for discrete/modular
    landscapes).  The LLM must propose concrete constants, not free
    parameters.  Score = exact-match fraction after rounding both sides
    to nearest integer.
    """
    parsed = parse_evidence_for_fitting(evidence_text, declaration.independent_vars)
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
) -> FitResult:
    """Fit parameters for a declared functional form against visible-slice evidence.

    If required_dimensionality is set, reject declarations whose independent_vars
    count doesn't match (Finding 5: prevent 1-var fits on 2-var sandboxes).

    score_mode:
      - "continuous_l2" (default): scipy curve_fit, L2 residual
      - "discrete_exact": no fitting; count exact integer matches
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

    if score_mode == "discrete_exact":
        return _evaluate_discrete_exact(
            declaration,
            evidence_text,
            expression_grammar=expression_grammar,
        )

    if not _SCIPY_AVAILABLE:
        return FitFailure(
            failure_class="no_scipy",
            attempted_template=declaration.expression,
            solver_diagnostics="scipy is not installed",
        )

    parsed = parse_evidence_for_fitting(evidence_text, declaration.independent_vars)
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

    p0 = [
        declaration.initial_guesses.get(name, 1.0)
        for name in declaration.parameter_names
    ]
    lo = [
        declaration.bounds.get(name, (-np.inf, np.inf))[0]
        for name in declaration.parameter_names
    ]
    hi = [
        declaration.bounds.get(name, (-np.inf, np.inf))[1]
        for name in declaration.parameter_names
    ]

    try:
        popt, _ = curve_fit(
            model_fn,
            xdata,
            ydata,
            p0=p0,
            bounds=(lo, hi),
            maxfev=_MAX_FEVAL,
        )
    except RuntimeError as exc:
        return FitFailure(
            failure_class="divergence",
            attempted_template=declaration.expression,
            solver_diagnostics=str(exc),
        )
    except Exception as exc:
        return FitFailure(
            failure_class="solver_error",
            attempted_template=declaration.expression,
            solver_diagnostics=f"{type(exc).__name__}: {exc}",
        )

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

    return FitSuccess(
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
    )


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
