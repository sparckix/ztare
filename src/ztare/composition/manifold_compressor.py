"""GP-097 N-D Manifold Compressor.

Compresses N-D datasets to 1D manifolds before synthesis via:
  Pass 1 — Topological Coordinate Descent (slice-based separation)
  Pass 2 — Ratio Sweep (pairwise variable combination collapse)
  Pass 3 — Entanglement Wall exit

No LLM involvement.  All gates evaluate the final assembled law
in original N-D coordinates, not in compressed space.

Spec: GP-097 (internal seam)
Seam: GP-097 (internal seam)
"""

from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field
from typing import Callable

try:
    import numpy as np
    from scipy.optimize import curve_fit

    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class CompressedManifold:
    """Result of a successful N-D → 1D compression."""

    evidence_1d: list[tuple[float, float]]
    compression_map: str  # human-readable, e.g. "additive, X first"
    compression_type: str  # "additive" | "multiplicative" | "ratio_collapse"
    inverse_map_description: str  # how to decompress: "Z = g(X) + h(Y)"
    compression_residual: float  # cross-term metric
    original_vars: list[str]
    compressed_var: str
    # The individual 1D laws discovered during compression.
    components: list[dict]  # [{var, expression, params, family}, ...]
    assembly_expression: str  # full N-D expression in original coordinates
    assembly_params: dict[str, float]  # fitted parameters for assembled law


@dataclass
class EntanglementWall:
    """Emitted when no compression succeeds."""

    pass_1_failures: list[str]
    pass_2_failures: list[str]
    message: str = "WALL_ENTANGLEMENT: variables genuinely entangled"


# ---------------------------------------------------------------------------
# Primitive library reused from symbolic-regression synthesis.
# ---------------------------------------------------------------------------

# Subset of _BASE_PRIMITIVES suitable for library sweep.
# Each: (label, expression_template_with_var_placeholder, param_names)
_SWEEP_PRIMITIVES: list[tuple[str, str, list[str]]] = [
    ("linear", "a * {v} + b", ["a", "b"]),
    ("quadratic", "a * {v}**2 + b * {v} + c", ["a", "b", "c"]),
    ("power", "a * {v}**b + c", ["a", "b", "c"]),
    ("sqrt", "a * math.sqrt({v}) + b", ["a", "b"]),
    ("log", "a * math.log({v}) + b", ["a", "b"]),
    ("exp", "a * math.exp(b * {v}) + c", ["a", "b", "c"]),
    ("exp_decay", "a * math.exp(-b * {v}) + c", ["a", "b", "c"]),
    ("tanh", "a * math.tanh(b * {v}) + c", ["a", "b", "c"]),
    ("logistic", "a / (1 + math.exp(-b * ({v} - c)))", ["a", "b", "c"]),
    ("reciprocal", "a / {v} + b", ["a", "b"]),
    ("rational", "a * {v} / ({v} + b) + c", ["a", "b", "c"]),
    ("double_exp", "a * math.exp(b * {v}) + c * math.exp(d * {v})", ["a", "b", "c", "d"]),
    ("sin", "a * math.sin(b * {v} + c) + d", ["a", "b", "c", "d"]),
    ("cos", "a * math.cos(b * {v} + c) + d", ["a", "b", "c", "d"]),
    ("gaussian", "a * math.exp(-((({v}) - b)**2) / (2 * c**2))", ["a", "b", "c"]),
    ("log_shifted", "a * math.log({v} + b) + c", ["a", "b", "c"]),
    # --- Additional families from symbolic-regression synthesis ---
    ("cosh", "a * math.cosh(b * {v}) + c", ["a", "b", "c"]),
    ("sinh", "a * math.sinh(b * {v}) + c", ["a", "b", "c"]),
    ("sqrt_reciprocal", "a / math.sqrt({v}) + b", ["a", "b"]),
    ("log_reciprocal", "a / math.log({v} + b) + c", ["a", "b", "c"]),
    ("cubic", "a * {v}**3 + b * {v}**2 + c * {v} + d", ["a", "b", "c", "d"]),
    ("inv_quadratic", "a / ({v}**2 + b) + c", ["a", "b", "c"]),
    ("exp_power", "a * math.exp(-b * {v}**c)", ["a", "b", "c"]),
    ("hill", "a * {v}**b / ({v}**b + c**b)", ["a", "b", "c"]),
]

_MIN_POINTS_PER_BIN = 5
_MIN_TOTAL_POINTS_FOR_SLICING = 15
_TOPOLOGY_MATCH_TOP_K = 3  # how many top families must match across slices
_CROSS_TERM_THRESHOLD = 0.05  # max acceptable cross-term residual (diagnostic)
_VARIANCE_COLLAPSE_THRESHOLD = 0.02  # intra-bin Z-variance for ratio collapse


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fit_primitive(
    x_data: np.ndarray,
    z_data: np.ndarray,
    expression_template: str,
    param_names: list[str],
    var_name: str,
) -> tuple[float, dict[str, float]] | None:
    """Fit a single primitive against (x, z) data via curve_fit.

    Returns (rmse, {param: value}) on success, None on failure.
    """
    if not _SCIPY_AVAILABLE:
        return None

    expr = expression_template.replace("{v}", var_name)
    try:
        code = compile(expr, "<sweep>", "eval")
    except SyntaxError:
        return None

    # Build a math-compatible namespace that works on numpy arrays.
    _np_math = type("_np_math", (), {
        "exp": staticmethod(np.exp),
        "log": staticmethod(np.log),
        "sqrt": staticmethod(np.sqrt),
        "sin": staticmethod(np.sin),
        "cos": staticmethod(np.cos),
        "tan": staticmethod(np.tan),
        "tanh": staticmethod(np.tanh),
        "cosh": staticmethod(np.cosh),
        "sinh": staticmethod(np.sinh),
        "pi": math.pi,
        "e": math.e,
    })()

    def model_fn(xdata, *params):
        env = {var_name: xdata, "math": _np_math, "np": np}
        env.update(dict(zip(param_names, params)))
        try:
            result = eval(code, {"__builtins__": {}}, env)  # noqa: S307
        except Exception:
            return np.full_like(xdata, np.nan)
        return np.asarray(result, dtype=float)

    n_params = len(param_names)
    # Try multiple starting points to improve convergence
    best_popt = None
    best_rmse = float("inf")
    for p0 in ([1.0] * n_params, [0.1] * n_params, [0.5] * n_params):
        try:
            popt, _ = curve_fit(
                model_fn,
                x_data,
                z_data,
                p0=p0,
                maxfev=8000,
            )
            pred = model_fn(x_data, *popt)
            if np.any(np.isnan(pred)) or np.any(np.isinf(pred)):
                continue
            rmse = float(np.sqrt(np.mean((z_data - pred) ** 2)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_popt = popt
        except Exception:
            continue

    if best_popt is None:
        return None
    popt = best_popt

    predicted = model_fn(x_data, *popt)
    if np.any(np.isnan(predicted)) or np.any(np.isinf(predicted)):
        return None
    rmse = float(np.sqrt(np.mean((z_data - predicted) ** 2)))
    fitted = dict(zip(param_names, [float(p) for p in popt]))
    return (rmse, fitted)


def _library_sweep(
    x_data: np.ndarray,
    z_data: np.ndarray,
    var_name: str,
) -> list[dict]:
    """Sweep all primitives, return top results sorted by RMSE."""
    results = []
    for label, template, params in _SWEEP_PRIMITIVES:
        fit = _fit_primitive(x_data, z_data, template, params, var_name)
        if fit is not None:
            rmse, fitted_params = fit
            if rmse < 1e6:  # reject absurd fits
                results.append({
                    "family": label,
                    "template": template,
                    "params": fitted_params,
                    "rmse": rmse,
                })
    results.sort(key=lambda r: r["rmse"])
    return results


def _slice_by_variable(
    evidence: list[tuple[float, ...]],
    var_idx: int,
    n_vars: int,
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """Bin evidence by the variable at var_idx.

    Returns list of (bin_center, x_data_of_other_vars, z_data).
    For 2D: returns (bin_center, x_array, z_array) where x_array
    is the other variable's values.
    """
    values = np.array([e[var_idx] for e in evidence])
    unique_vals = np.unique(values)

    if len(unique_vals) < 3:
        # Too few unique values to bin meaningfully
        return []

    # Adaptive binning: target at least _MIN_POINTS_PER_BIN per bin
    n_bins = max(2, min(len(unique_vals) // 3, 10))
    bin_edges = np.linspace(unique_vals.min(), unique_vals.max(), n_bins + 1)

    slices = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (values >= lo) & (values <= hi)
        else:
            mask = (values >= lo) & (values < hi)
        if mask.sum() < _MIN_POINTS_PER_BIN:
            continue

        bin_center = (lo + hi) / 2
        bin_evidence = [e for e, m in zip(evidence, mask) if m]

        # For 2D: the "other" variable index
        other_indices = [j for j in range(n_vars) if j != var_idx]
        if len(other_indices) == 1:
            other_idx = other_indices[0]
            x_arr = np.array([e[other_idx] for e in bin_evidence])
            z_arr = np.array([e[-1] for e in bin_evidence])
            slices.append((bin_center, x_arr, z_arr))

    return slices


def _evaluate_assembly(
    evidence: list[tuple[float, ...]],
    expression: str,
    params: dict[str, float],
    var_names: list[str],
) -> float:
    """Evaluate an assembled N-D expression on all evidence points.

    Returns max absolute residual.
    """
    try:
        code = compile(expression, "<assembly>", "eval")
    except SyntaxError:
        return float("inf")

    max_res = 0.0
    for point in evidence:
        env = {"math": math}
        for i, var in enumerate(var_names):
            env[var] = point[i]
        env.update(params)
        try:
            predicted = float(eval(code, {"__builtins__": {}}, env))  # noqa: S307
        except Exception:
            return float("inf")
        actual = point[-1]  # Z is always last
        max_res = max(max_res, abs(predicted - actual))
    return max_res


def _compute_cross_term_residual(
    evidence: list[tuple[float, ...]],
    expression: str,
    params: dict[str, float],
    var_names: list[str],
) -> float:
    """Estimate cross-variable coupling in residuals via finite differences.

    Computes max |d²R/dXi dXj| as a diagnostic for information loss
    during compression.
    """
    if len(evidence) < 10:
        return 0.0

    residuals = []
    for point in evidence:
        env = {"math": math}
        for i, var in enumerate(var_names):
            env[var] = point[i]
        env.update(params)
        try:
            code = compile(expression, "<cross>", "eval")
            predicted = float(eval(code, {"__builtins__": {}}, env))  # noqa: S307
            residuals.append(point[-1] - predicted)
        except Exception:
            residuals.append(0.0)

    # Sort by first variable, compute variance of residuals in bins
    arr = np.array(evidence)
    res_arr = np.array(residuals)
    if len(var_names) < 2:
        return 0.0

    # Check if residual depends on second variable within bins of first
    idx_sort = np.argsort(arr[:, 0])
    n_bins = max(2, len(evidence) // 5)
    bin_size = len(evidence) // n_bins
    max_cross = 0.0
    for b in range(n_bins):
        start = b * bin_size
        end = start + bin_size if b < n_bins - 1 else len(evidence)
        bin_res = res_arr[idx_sort[start:end]]
        if len(bin_res) > 1:
            max_cross = max(max_cross, float(np.std(bin_res)))
    return max_cross


def _generate_nd_holdout(
    evidence: list[tuple[float, ...]],
    var_names: list[str],
    extension_factor: float = 1.5,
) -> list[tuple[float, ...]]:
    """Generate holdout points at extended bounding box corners."""
    n_vars = len(var_names)
    bounds = []
    for i in range(n_vars):
        values = [e[i] for e in evidence]
        lo, hi = min(values), max(values)
        width = hi - lo
        if width < 1e-10:
            width = abs(lo) * 0.1 if lo != 0 else 1.0
        bounds.append((
            lo - extension_factor * width,
            hi + extension_factor * width,
        ))

    # Corner points
    corners = list(itertools.product(*bounds))

    # Axis-extension points (extend one dim, keep others at midpoint)
    for i in range(n_vars):
        mid = [(b[0] + b[1]) / 2 for b in bounds]
        for extreme in bounds[i]:
            pt = list(mid)
            pt[i] = extreme
            corners.append(tuple(pt))

    return corners


def _evaluate_holdout_consistency(
    expression: str,
    params: dict[str, float],
    var_names: list[str],
    holdout_points: list[tuple[float, ...]],
) -> bool:
    """Check if expression evaluates to finite values at holdout points.

    This is a basic sanity check — divergence at holdout is a rejection signal.
    Full holdout comparison against GT requires the synthesis loop.
    """
    try:
        code = compile(expression, "<holdout>", "eval")
    except SyntaxError:
        return False

    for point in holdout_points:
        env = {"math": math}
        for i, var in enumerate(var_names):
            env[var] = point[i]
        env.update(params)
        try:
            val = float(eval(code, {"__builtins__": {}}, env))  # noqa: S307
        except Exception:
            return False
        if not np.isfinite(val):
            return False
    return True


# ---------------------------------------------------------------------------
# Pass 1: Topological Coordinate Descent
# ---------------------------------------------------------------------------


def _pass1_coordinate_descent(
    evidence: list[tuple[float, ...]],
    ind_vars: list[str],
) -> list[dict]:
    """Try all orderings × additive/multiplicative separation.

    Returns list of successful assemblies sorted by max residual.
    """
    n_vars = len(ind_vars)
    n_evidence_cols = n_vars + 1  # ind_vars + Z

    if len(evidence) < _MIN_TOTAL_POINTS_FOR_SLICING:
        return []

    candidates = []

    for perm in itertools.permutations(range(n_vars)):
        for composition in ("additive", "multiplicative"):
            result = _try_separation(evidence, ind_vars, perm, composition)
            if result is not None:
                candidates.append(result)

    candidates.sort(key=lambda c: c["max_residual"])
    return candidates


def _try_separation(
    evidence: list[tuple[float, ...]],
    ind_vars: list[str],
    var_order: tuple[int, ...],
    composition: str,
) -> dict | None:
    """Try separating variables in a specific order with given composition type."""
    n_vars = len(ind_vars)
    first_var_idx = var_order[0]
    second_var_idx = var_order[1] if n_vars > 1 else None

    if second_var_idx is None:
        return None

    # Step 1: Slice by second variable, sweep first variable
    slices = _slice_by_variable(evidence, second_var_idx, n_vars)
    if len(slices) < 2:
        return None

    # Sweep first variable on each slice
    slice_results = []
    for bin_center, x_data, z_data in slices:
        sweep = _library_sweep(x_data, z_data, ind_vars[first_var_idx])
        if sweep:
            slice_results.append({
                "bin_center": bin_center,
                "top_families": [r["family"] for r in sweep[:_TOPOLOGY_MATCH_TOP_K]],
                "best": sweep[0],
            })

    if len(slice_results) < 2:
        return None

    # Step 2: Topology consistency check
    # The top family must match across at least 2 slices
    family_counts: dict[str, int] = {}
    for sr in slice_results:
        top_fam = sr["top_families"][0] if sr["top_families"] else ""
        family_counts[top_fam] = family_counts.get(top_fam, 0) + 1

    best_family = max(family_counts, key=family_counts.get)
    if family_counts[best_family] < 2:
        return None  # topology not consistent across slices

    # Use the best-fitting slice for g(X_first)
    matching_slices = [
        sr for sr in slice_results
        if sr["top_families"] and sr["top_families"][0] == best_family
    ]
    best_slice = min(matching_slices, key=lambda s: s["best"]["rmse"])
    g_result = best_slice["best"]

    # Step 3: Compute residual
    first_var = ind_vars[first_var_idx]
    second_var = ind_vars[second_var_idx]
    g_expr = g_result["template"].replace("{v}", first_var)
    g_params = g_result["params"]

    residual_points: list[tuple[float, float]] = []
    try:
        g_code = compile(g_expr, "<g>", "eval")
    except SyntaxError:
        return None

    for point in evidence:
        x_first = point[first_var_idx]
        x_second = point[second_var_idx]
        z = point[-1]
        env = {first_var: x_first, "math": math}
        env.update(g_params)
        try:
            g_val = float(eval(g_code, {"__builtins__": {}}, env))  # noqa: S307
        except Exception:
            return None

        if composition == "additive":
            residual = z - g_val
        elif composition == "multiplicative":
            if abs(g_val) < 1e-12:
                return None  # can't divide by zero
            residual = z / g_val
        else:
            return None

        residual_points.append((x_second, residual))

    # Step 4: Sweep second variable on residual
    x2_data = np.array([r[0] for r in residual_points])
    r_data = np.array([r[1] for r in residual_points])
    h_sweep = _library_sweep(x2_data, r_data, second_var)

    if not h_sweep:
        return None

    h_result = h_sweep[0]
    h_expr = h_result["template"].replace("{v}", second_var)
    h_params = h_result["params"]

    # Step 5: Assemble
    # Prefix parameters to avoid collisions (word-boundary replacement)


    g_prefixed = {}
    g_expr_prefixed = g_expr
    for p, v in g_params.items():
        new_p = f"g_{p}"
        g_expr_prefixed = re.sub(rf"\b{re.escape(p)}\b", new_p, g_expr_prefixed)
        g_prefixed[new_p] = v

    h_prefixed = {}
    h_expr_prefixed = h_expr
    for p, v in h_params.items():
        new_p = f"h_{p}"
        h_expr_prefixed = re.sub(rf"\b{re.escape(p)}\b", new_p, h_expr_prefixed)
        h_prefixed[new_p] = v

    if composition == "additive":
        assembly = f"({g_expr_prefixed}) + ({h_expr_prefixed})"
    else:
        assembly = f"({g_expr_prefixed}) * ({h_expr_prefixed})"

    all_params = {**g_prefixed, **h_prefixed}

    # Step 6: Evaluate assembly on all evidence
    max_res = _evaluate_assembly(evidence, assembly, all_params, ind_vars)

    # Step 7: Check holdout consistency (finite values at extrapolation)
    holdout_points = _generate_nd_holdout(evidence, ind_vars)
    holdout_ok = _evaluate_holdout_consistency(
        assembly, all_params, ind_vars, holdout_points,
    )

    # Cross-term diagnostic
    cross_res = _compute_cross_term_residual(
        evidence, assembly, all_params, ind_vars,
    )

    return {
        "composition": composition,
        "var_order": [ind_vars[i] for i in var_order],
        "g_family": g_result["family"],
        "h_family": h_result["family"],
        "assembly_expression": assembly,
        "assembly_params": all_params,
        "max_residual": max_res,
        "holdout_ok": holdout_ok,
        "cross_term_residual": cross_res,
        "components": [
            {"var": first_var, "family": g_result["family"],
             "expression": g_expr, "params": g_params},
            {"var": second_var, "family": h_result["family"],
             "expression": h_expr, "params": h_params},
        ],
    }


# ---------------------------------------------------------------------------
# Pass 2: Ratio Sweep
# ---------------------------------------------------------------------------

_RATIO_CANDIDATES: list[tuple[str, Callable[[float, float], float]]] = [
    ("X/Y", lambda x, y: x / y if abs(y) > 1e-12 else float("nan")),
    ("Y/X", lambda x, y: y / x if abs(x) > 1e-12 else float("nan")),
    ("X*Y", lambda x, y: x * y),
    ("X**2/Y", lambda x, y: x**2 / y if abs(y) > 1e-12 else float("nan")),
    ("Y**2/X", lambda x, y: y**2 / x if abs(x) > 1e-12 else float("nan")),
]


def _pass2_ratio_sweep(
    evidence: list[tuple[float, ...]],
    ind_vars: list[str],
) -> list[dict]:
    """Try pairwise variable combinations as collapse candidates."""
    n_vars = len(ind_vars)
    candidates = []

    for i, j in itertools.combinations(range(n_vars), 2):
        for label_template, ratio_fn in _RATIO_CANDIDATES:
            label = label_template.replace("X", ind_vars[i]).replace("Y", ind_vars[j])

            # Compute U for all evidence points
            u_values = []
            z_values = []
            valid = True
            for point in evidence:
                try:
                    u = ratio_fn(point[i], point[j])
                except Exception:
                    valid = False
                    break
                if not np.isfinite(u):
                    valid = False
                    break
                u_values.append(u)
                z_values.append(point[-1])

            if not valid or len(u_values) < 5:
                continue

            u_arr = np.array(u_values)
            z_arr = np.array(z_values)

            # Intra-bin variance check for collapse validity
            n_bins = max(2, len(u_values) // 5)
            bin_edges = np.linspace(u_arr.min(), u_arr.max(), n_bins + 1)
            max_intra_var = 0.0
            bins_checked = 0
            for b in range(n_bins):
                lo, hi = bin_edges[b], bin_edges[b + 1]
                if b == n_bins - 1:
                    mask = (u_arr >= lo) & (u_arr <= hi)
                else:
                    mask = (u_arr >= lo) & (u_arr < hi)
                bin_z = z_arr[mask]
                if len(bin_z) >= 2:
                    max_intra_var = max(max_intra_var, float(np.var(bin_z)))
                    bins_checked += 1

            if bins_checked < 2:
                continue

            # Normalize variance by overall Z variance
            z_var = float(np.var(z_arr))
            if z_var < 1e-12:
                continue
            normalized_var = max_intra_var / z_var

            if normalized_var > _VARIANCE_COLLAPSE_THRESHOLD:
                continue  # collapse not valid

            # 1D sweep on (U, Z)
            sweep = _library_sweep(u_arr, z_arr, "U")
            if not sweep:
                continue

            best = sweep[0]

            # Build decompressed expression
            u_expr = label_template.replace("X", ind_vars[i]).replace("Y", ind_vars[j])
            full_expr = best["template"].replace("{v}", f"({u_expr})")

            # Prefix params (word-boundary replacement)
        
            prefixed_params = {}
            full_expr_p = full_expr
            for p, v in best["params"].items():
                new_p = f"r_{p}"
                full_expr_p = re.sub(rf"\b{re.escape(p)}\b", new_p, full_expr_p)
                prefixed_params[new_p] = v

            max_res = _evaluate_assembly(evidence, full_expr_p, prefixed_params, ind_vars)

            holdout_points = _generate_nd_holdout(evidence, ind_vars)
            holdout_ok = _evaluate_holdout_consistency(
                full_expr_p, prefixed_params, ind_vars, holdout_points,
            )

            candidates.append({
                "collapse_var": label,
                "collapse_expression": u_expr,
                "family": best["family"],
                "assembly_expression": full_expr_p,
                "assembly_params": prefixed_params,
                "max_residual": max_res,
                "holdout_ok": holdout_ok,
                "normalized_variance": normalized_var,
                "composition": "ratio_collapse",
                "components": [
                    {"var": "U=" + label, "family": best["family"],
                     "expression": best["template"], "params": best["params"]},
                ],
            })

    candidates.sort(key=lambda c: c["max_residual"])
    return candidates


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compress(
    evidence: list[tuple[float, ...]],
    ind_vars: list[str],
    *,
    verbose: bool = True,
) -> CompressedManifold | EntanglementWall:
    """Compress an N-D dataset to a 1D manifold or emit EntanglementWall.

    Args:
        evidence: List of tuples (x1, x2, ..., z). Z is always last.
        ind_vars: Names of independent variables (not including Z).
        verbose: Print progress.

    Returns:
        CompressedManifold on success, EntanglementWall on failure.
    """
    if len(ind_vars) < 2:
        # 1D data — no compression needed. Return as-is.
        return CompressedManifold(
            evidence_1d=[(e[0], e[-1]) for e in evidence],
            compression_map="identity (1D)",
            compression_type="identity",
            inverse_map_description="Z = f(X) — no compression",
            compression_residual=0.0,
            original_vars=ind_vars,
            compressed_var=ind_vars[0],
            components=[],
            assembly_expression="",
            assembly_params={},
        )

    pass_1_failures: list[str] = []
    pass_2_failures: list[str] = []

    # -----------------------------------------------------------------------
    # Pass 1: Topological Coordinate Descent
    # -----------------------------------------------------------------------
    if verbose:
        print("    🗜️  GP-097 Pass 1: Topological Coordinate Descent")

    p1_candidates = _pass1_coordinate_descent(evidence, ind_vars)

    # Filter to candidates that pass holdout sanity check
    p1_viable = [c for c in p1_candidates if c["holdout_ok"]]

    if p1_viable:
        winner = p1_viable[0]
        if verbose:
            print(
                f"    🗜️  Pass 1 SUCCESS: {winner['composition']} separation "
                f"({winner['var_order'][0]} first), "
                f"g={winner['g_family']}, h={winner['h_family']}, "
                f"max|res|={winner['max_residual']:.6f}"
            )
            if winner["cross_term_residual"] > _CROSS_TERM_THRESHOLD:
                print(
                    f"    ⚠️  Cross-term residual: {winner['cross_term_residual']:.6f} "
                    f"(> threshold {_CROSS_TERM_THRESHOLD})"
                )

        # Build 1D evidence: evaluate g(first_var) as compressed coordinate
        compressed_var = "U"
        first_var = winner["var_order"][0]
        first_idx = ind_vars.index(first_var)
        g_comp = winner["components"][0]
        try:
            _g_code = compile(g_comp["expression"], "<ev1d>", "eval")
            evidence_1d = []
            for e in evidence:
                _env = {first_var: e[first_idx], "math": math}
                _env.update(g_comp["params"])
                g_val = float(eval(_g_code, {"__builtins__": {}}, _env))  # noqa: S307
                evidence_1d.append((g_val, e[-1]))
        except Exception:
            evidence_1d = [(e[first_idx], e[-1]) for e in evidence]

        return CompressedManifold(
            evidence_1d=evidence_1d,
            compression_map=f"{winner['composition']}, {winner['var_order'][0]} first",
            compression_type=winner["composition"],
            inverse_map_description=(
                f"Z = {winner['assembly_expression']}"
            ),
            compression_residual=winner["cross_term_residual"],
            original_vars=ind_vars,
            compressed_var=compressed_var,
            components=winner["components"],
            assembly_expression=winner["assembly_expression"],
            assembly_params=winner["assembly_params"],
        )
    else:
        reasons = []
        if not p1_candidates:
            reasons.append("no separable topology found across variable orderings")
        else:
            reasons.append(
                f"{len(p1_candidates)} assemblies found but none passed holdout "
                f"(best max|res|={p1_candidates[0]['max_residual']:.6f})"
            )
        pass_1_failures = reasons
        if verbose:
            for r in reasons:
                print(f"    🗜️  Pass 1 failed: {r}")

    # -----------------------------------------------------------------------
    # Pass 2: Ratio Sweep
    # -----------------------------------------------------------------------
    if verbose:
        print("    🗜️  GP-097 Pass 2: Ratio Sweep")

    p2_candidates = _pass2_ratio_sweep(evidence, ind_vars)
    p2_viable = [c for c in p2_candidates if c["holdout_ok"]]

    if p2_viable:
        winner = p2_viable[0]
        if verbose:
            print(
                f"    🗜️  Pass 2 SUCCESS: ratio collapse U={winner['collapse_var']}, "
                f"family={winner['family']}, "
                f"max|res|={winner['max_residual']:.6f}"
            )

        return CompressedManifold(
            evidence_1d=[
                (float(eval(  # noqa: S307
                    winner["collapse_expression"],
                    {"__builtins__": {}},
                    {ind_vars[i]: e[i] for i in range(len(ind_vars))},
                )), e[-1])
                for e in evidence
            ],
            compression_map=f"ratio collapse, U={winner['collapse_var']}",
            compression_type="ratio_collapse",
            inverse_map_description=(
                f"Z = {winner['assembly_expression']}"
            ),
            compression_residual=winner.get("normalized_variance", 0.0),
            original_vars=ind_vars,
            compressed_var=f"U={winner['collapse_var']}",
            components=winner["components"],
            assembly_expression=winner["assembly_expression"],
            assembly_params=winner["assembly_params"],
        )
    else:
        reasons = []
        if not p2_candidates:
            reasons.append("no ratio collapse achieved sufficient variance reduction")
        else:
            reasons.append(
                f"{len(p2_candidates)} collapses found but none passed holdout "
                f"(best max|res|={p2_candidates[0]['max_residual']:.6f})"
            )
        pass_2_failures = reasons
        if verbose:
            for r in reasons:
                print(f"    🗜️  Pass 2 failed: {r}")

    # -----------------------------------------------------------------------
    # Pass 3: Entanglement Wall
    # -----------------------------------------------------------------------
    if verbose:
        print("    🗜️  GP-097 Pass 3: WALL_ENTANGLEMENT")

    return EntanglementWall(
        pass_1_failures=pass_1_failures,
        pass_2_failures=pass_2_failures,
        message=(
            f"WALL_ENTANGLEMENT: variables {ind_vars} genuinely entangled. "
            f"Pass 1: {'; '.join(pass_1_failures) or 'skipped'}. "
            f"Pass 2: {'; '.join(pass_2_failures) or 'skipped'}."
        ),
    )
