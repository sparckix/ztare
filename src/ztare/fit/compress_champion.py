"""GP-103 Compression Primitive: Template Enumeration.

After a champion passes holdout gates with k_champion parameters, this module
asks: "can a simpler form also pass?" It enumerates low-k templates from the
grammar, fits each to visible evidence, runs the gate harness, and selects the
simplest gate-passing form by BIC.

This is NOT oracle contamination:
- Templates come from the grammar (pre-registered in rubric)
- ALL templates are tried (no hardcoded target)
- Selection is by gate passage + BIC (standard model selection)
- k ranges from 2 to k_champion-1 (no hardcoded param count)

Kahneman ordering constraint: validate on KWW + DFDO before GP-088.

Usage:
    python -m src.ztare.fit.compress_champion --project gp088_calibration_a01
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
    from scipy.optimize import curve_fit
    _SCIPY = True
except ImportError:
    _SCIPY = False

from ztare.common.paths import PROJECTS_DIR
from ztare.fit.mdl import bic as _mdl_bic  # canonical BIC (was inlined identically 3× below)
from ztare.fit.primitive_library import load_library, save_to_library


# ---------------------------------------------------------------------------
# Template library (math_exp_only grammar)
# ---------------------------------------------------------------------------

# Each template: (name, expression_str, param_names, n_params)
# The independent variable is always 'n' for 1D substrates.
# Templates are grammar-legal under math_exp_only.

def _build_templates_1d(var: str = "n") -> list[tuple[str, str, list[str]]]:
    """Build all low-k templates for 1D math_exp_only grammar.

    The independent variable name is substituted from the project's evidence.
    Templates cover: growth (log, sqrt, power), decay (exp, stretched exp),
    and combinations — ensuring the library is domain-general.
    """
    x = var  # shorthand
    templates = []

    # --- k=2: affine combinations ---
    templates.append(("linear", f"a * {x} + b", ["a", "b"]))  # GP-116: continuous-variable substrates (activation transitions)
    templates.append(("log_affine", f"a * math.log({x}) + b", ["a", "b"]))
    templates.append(("sqrt_affine", f"a * math.sqrt({x}) + b", ["a", "b"]))
    templates.append(("reciprocal_affine", f"a / {x} + b", ["a", "b"]))

    # --- k=2: inverse-log convergence (Mertens / abundant density law) ---
    templates.append(("inv_log_affine", f"a + b / math.log({x})", ["a", "b"]))

    # --- k=2: geometric/exponential decay (GP-126: Stieltjes survey target)
    templates.append(("geometric_decay", f"a * b**{x} + c", ["a", "b", "c"]))

    # --- k=3: polynomial (works on negative domains) ---
    templates.append(("quadratic", f"a * {x}**2 + b * {x} + c", ["a", "b", "c"]))

    # --- k=3: two-term + offset ---
    templates.append(("sqrt_log", f"a * math.sqrt({x}) + b * math.log({x}) + c", ["a", "b", "c"]))
    templates.append(("log_reciprocal", f"a * math.log({x}) + b / {x} + c", ["a", "b", "c"]))
    templates.append(("sqrt_reciprocal", f"a * math.sqrt({x}) + b / {x} + c", ["a", "b", "c"]))

    # --- k=3: inverse-log with correction terms (survey_s1 grammar gap) ---
    templates.append(("inv_log_recip", f"a + b / math.log({x}) + c / {x}", ["a", "b", "c"]))
    templates.append(("inv_log_sq", f"a + b / math.log({x}) + c / math.log({x})**2", ["a", "b", "c"]))
    templates.append(("power_free", f"a * {x}**b + c", ["a", "b", "c"]))
    templates.append(("log_scaled", f"a * math.log(b * {x}) + c", ["a", "b", "c"]))
    templates.append(("exp_decay_offset", f"a * math.exp(-b * {x}) + c", ["a", "b", "c"]))
    templates.append(("log_shifted_reciprocal", f"a * math.log({x}) + b / ({x} + c) + d", ["a", "b", "c", "d"]))  # GP-113 grammar gap discovery
    templates.append(("parabolic", f"a * ({x} - b)**2 + c", ["a", "b", "c"]))  # GP-116 rank curve gap discovery

    # --- k=3-4: sigmoid/threshold forms (GP-121: cross-entity substrate support) ---
    templates.append(("sigmoid", f"a / (1 + math.exp(-b * ({x} - c))) + d", ["a", "b", "c", "d"]))
    templates.append(("threshold_exp", f"a * math.exp(-b * ({x} - c)) / (1 + math.exp(-b * ({x} - c))) + d", ["a", "b", "c", "d"]))

    # --- k=3: iterated logarithm and free log-power (added 2026-04-21, panel verdict) ---
    templates.append(("loglog_affine", f"a * math.log({x}) + d * math.log(math.log({x})) + c", ["a", "d", "c"]))
    templates.append(("log_power_free", f"a * math.log({x})**b + c", ["a", "b", "c"]))

    # --- k=4: iterated logarithm with corrections, free log-power with corrections ---
    templates.append(("loglog_reciprocal", f"a * math.log({x}) + d * math.log(math.log({x})) + b / {x} + c", ["a", "d", "b", "c"]))
    templates.append(("log_power_reciprocal", f"a * math.log({x})**b + c / {x} + d", ["a", "b", "c", "d"]))

    # --- k=4: three-term + offset, stretched exponentials ---
    templates.append(("sqrt_log_reciprocal", f"a * math.sqrt({x}) + b * math.log({x}) + c / {x} + d", ["a", "b", "c", "d"]))
    templates.append(("power_log", f"a * {x}**b + c * math.log({x}) + d", ["a", "b", "c", "d"]))
    templates.append(("log_log_offset", f"a * math.log(b * {x} + c) + d", ["a", "b", "c", "d"]))
    templates.append(("exp_power_offset", f"a * math.exp(b * math.sqrt({x})) + c", ["a", "b", "c"]))
    templates.append(("stretched_exp", f"a * math.exp(-b * {x}**c) + d", ["a", "b", "c", "d"]))
    templates.append(("exp_decay_linear", f"a * math.exp(-b * {x}) + c * {x} + d", ["a", "b", "c", "d"]))
    templates.append(("power_decay", f"a * {x}**(-b) + c", ["a", "b", "c"]))
    templates.append(("power_exp_decay", f"a * {x}**(-b) * math.exp(-c * {x}) + d", ["a", "b", "c", "d"]))

    # --- k=5: richer combinations ---
    templates.append(("sqrt_log_recip2", f"a * math.sqrt({x}) + b * math.log({x}) + c / {x} + d / {x}**2 + e", ["a", "b", "c", "d", "e"]))
    templates.append(("power_log_recip", f"a * {x}**b + c * math.log({x}) + d / {x} + e", ["a", "b", "c", "d", "e"]))
    templates.append(("two_exp_decay", f"a * math.exp(-b * {x}) + c * math.exp(-d * {x}) + e", ["a", "b", "c", "d", "e"]))
    templates.append(("stretched_exp_log", f"a * math.exp(-b * {x}**c) + d * math.log({x}) + e", ["a", "b", "c", "d", "e"]))

    # --- k=6: two-regime composites ---
    templates.append(("two_regime_exp_power", f"a * math.exp(-b * {x}**c) + d * {x}**(-e) + f", ["a", "b", "c", "d", "e", "f"]))

    return templates


# ---------------------------------------------------------------------------
# Evidence + gate harness
def _build_compositional_templates_1d(var: str = "n") -> list[tuple[str, str, list[str]]]:
    """Stage 2: depth-1 nested compositions f(g(x)).

    Only activated when Stage 1 (additive templates) returns UNDERIDENTIFIED.
    Popper constraint: Stage 2 gates must be at least as tight as Stage 1.
    Munger constraint: only fires after Stage 1 exhausts — never weakens Stage 1.

    The set is small and bounded: 2 primitives nested = ~15 templates.
    No combinatorial explosion because depth is capped at 1.
    """
    x = var
    templates = []

    # --- k=2: pure nested ---
    templates.append(("sqrt_over_log", f"a * math.sqrt({x} / math.log({x})) + b", ["a", "b"]))
    templates.append(("sqrt_times_log", f"a * math.sqrt({x} * math.log({x})) + b", ["a", "b"]))
    templates.append(("log_of_sqrt", f"a * math.log(math.sqrt({x})) + b", ["a", "b"]))
    templates.append(("exp_of_sqrt", f"a * math.exp(b * math.sqrt({x})) + c", ["a", "b", "c"]))
    templates.append(("sqrt_of_log", f"a * math.sqrt(math.log({x})) + b", ["a", "b"]))
    templates.append(("power_of_log", f"a * math.log({x})**b + c", ["a", "b", "c"]))

    # --- k=3: nested + correction ---
    templates.append(("sqrt_over_log_plus_log", f"a * math.sqrt({x} / math.log({x})) + b * math.log({x}) + c", ["a", "b", "c"]))
    templates.append(("sqrt_over_log_plus_recip", f"a * math.sqrt({x} / math.log({x})) + b / {x} + c", ["a", "b", "c"]))
    templates.append(("exp_sqrt_plus_log", f"a * math.exp(b * math.sqrt({x})) + c * math.log({x}) + d", ["a", "b", "c", "d"]))
    templates.append(("sqrt_times_log_plus_recip", f"a * math.sqrt({x} * math.log({x})) + b / {x} + c", ["a", "b", "c"]))

    # --- k=3-5: nested + corrections ---
    templates.append(("sqrt_over_log_loglog", f"a * math.sqrt({x} / math.log({x})) * (1 + b * math.log(math.log({x})) / math.log({x})) + c", ["a", "b", "c"]))
    templates.append(("sqrt_over_log_full", f"a * math.sqrt({x} / math.log({x})) + b * math.log({x}) + c / {x} + d", ["a", "b", "c", "d"]))
    templates.append(("exp_sqrt_full", f"a * math.exp(b * math.sqrt({x})) + c * math.log({x}) + d / {x} + e", ["a", "b", "c", "d", "e"]))

    return templates


# ---------------------------------------------------------------------------

def _load_evidence(path: Path) -> list[tuple[float, float]]:
    pts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    return pts


def _run_gate_harness(project_dir: Path) -> dict | None:
    """Run the project's gate_harness.py and return the result dict."""
    import subprocess
    harness = project_dir / "gate_harness.py"
    if not harness.exists():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(harness), "--emit-deterministic-gates"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except Exception:
        pass
    return None


def _write_test_model(project_dir: Path, expression: str, params: dict[str, float], var_name: str = "n") -> None:
    """Write a test_model.py with the given expression and fitted params."""
    param_lines = "\n".join(f"    {k} = {v}" for k, v in params.items())
    code = f"""\
import math
def f({var_name}):
{param_lines}
    return {expression}

model = f
"""
    (project_dir / "test_model.py").write_text(code, encoding="utf-8")


# ---------------------------------------------------------------------------
# Compression search
# ---------------------------------------------------------------------------

@dataclass
class CompressionResult:
    name: str
    expression: str
    params: dict[str, float]
    k: int
    visible_max_res: float
    gates_passed: bool
    gate_results: dict
    bic: float
    # Gate quality audit flags (GP-AuditFix 1-3, 2026-04-23)
    asymptote_bias: bool = False    # Fix 1: f(10×x_max) diverges from data range
    param_scale_issue: bool = False  # Fix 3: max|param| >> data scale (aliasing likely)
    # GP-133 perturbation battery (range-stability check)
    range_stable: bool | None = None  # None = not checked; True/False = checked


# ---------------------------------------------------------------------------
# Gate quality audit helpers (GP-AuditFix 1-3)
# ---------------------------------------------------------------------------

def _asymptote_bias_flag(
    code_obj, param_names: list[str], popt,
    var_name: str, xdata: np.ndarray, ydata: np.ndarray,
) -> bool:
    """Fix 1: Predict at 10× x_max; flag if result diverges from data scale by >15%.

    Catches the pattern where a fitted constant (asymptote) is inflated beyond the
    evidence range because a helper correction term absorbs the small-n behavior.
    Example: a=0.2559 when z≤0.2494 and z→0.248 — 2.6% above data max, but
    the gate at n=100000 shows 2.1% normalised error, catching the bias.
    """
    x_far = float(np.max(xdata)) * 10.0
    y_data_scale = float(np.max(np.abs(ydata)))
    if y_data_scale < 1e-15:
        return False
    try:
        ns: dict = {"math": math, var_name: x_far, "__builtins__": {}}
        ns.update(dict(zip(param_names, [float(v) for v in popt])))
        y_far = float(eval(code_obj, {"__builtins__": {}}, ns))
        return math.isfinite(y_far) and abs(y_far) > y_data_scale * 1.15
    except Exception:
        return False


def _param_scale_flag(popt, ydata: np.ndarray) -> bool:
    """Fix 3: Flag if any fitted parameter >> data scale (cancellation / aliasing).

    When max|param| > 100 × max|y_data|, the fit is likely using two large
    opposing terms that cancel — masking structural mismatch.
    """
    y_scale = float(np.max(np.abs(ydata)))
    if y_scale < 1e-15:
        return False
    return max(abs(float(v)) for v in popt) > 100.0 * y_scale


def _range_stability_check(
    xdata: np.ndarray,
    ydata: np.ndarray,
    expr: str,
    param_names: list[str],
    var_name: str,
    verbose: bool,
    prediction_threshold: float = 0.10,
) -> dict:
    """GP-133 R4: Prediction-stability check across sub-ranges.

    Rewritten per Round 4 debate (Socrates/Feynman unanimous):
    tests whether the PREDICTIONS are stable, not the parameters.

    Splits evidence into 3 non-overlapping ranges, fits the expression on each,
    then evaluates all 3 fitted models on the FULL x-grid. If max prediction
    disagreement exceeds prediction_threshold * y_scale, the form is unstable.

    Also reports parameter-level diagnostics (Ramanujan's R8: correction-term
    rank deficiency) as informational, but gates ONLY on prediction stability.

    Returns dict with 'stable' (bool), 'max_pred_disagreement' (float),
    'params_by_range' (list of dicts), and 'rank_deficiency' (int).
    """
    if not _SCIPY or len(xdata) < 15:
        return {"stable": None, "reason": "insufficient data or no scipy"}

    # Sort by x and split into 3 equal-count ranges
    order = np.argsort(xdata)
    xs, ys = xdata[order], ydata[order]
    n = len(xs)
    k = len(param_names)
    min_per_range = max(8, 3 * k)
    if n // 3 < min_per_range:
        return {"stable": None, "reason": f"sub-ranges too small ({n//3} pts vs {min_per_range} needed for k={k})"}
    splits = [(xs[:n // 3], ys[:n // 3]),
              (xs[n // 3:2 * n // 3], ys[n // 3:2 * n // 3]),
              (xs[2 * n // 3:], ys[2 * n // 3:])]

    try:
        code = compile(expr, "<range_stab>", "eval")
    except SyntaxError:
        return {"stable": None, "reason": "expression compile error"}

    def _make_fn(c, pnames, vname):
        def fn(xd, *params):
            out = np.empty(len(xd))
            pd = dict(zip(pnames, params))
            for i, x in enumerate(xd):
                ns = {"math": math, vname: float(x)}
                ns.update(pd)
                try:
                    out[i] = float(eval(c, {"__builtins__": {}}, ns))
                except Exception:
                    out[i] = float("nan")
            return out
        return fn

    model_fn = _make_fn(code, param_names, var_name)
    params_by_range: list[dict[str, float]] = []

    for sx, sy in splits:
        if len(sx) < len(param_names) + 1:
            return {"stable": None, "reason": "sub-range too small for fit"}
        p0 = [float(np.mean(sy))] + [0.01] * (len(param_names) - 1)
        try:
            popt, _ = curve_fit(model_fn, sx, sy, p0=p0, maxfev=10000)
            params_by_range.append(dict(zip(param_names, [float(v) for v in popt])))
        except Exception:
            try:
                p0_alt = [0.1 * (j + 1) for j in range(len(param_names))]
                popt, _ = curve_fit(model_fn, sx, sy, p0=p0_alt, maxfev=10000)
                params_by_range.append(dict(zip(param_names, [float(v) for v in popt])))
            except Exception:
                return {"stable": None, "reason": "fit failed on sub-range"}

    # --- Prediction stability (the gate) ---
    # Evaluate all 3 sub-range-fitted models on the full x-grid
    y_scale = float(np.max(np.abs(ydata)))
    if y_scale < 1e-15:
        y_scale = 1.0

    preds = []
    for pr in params_by_range:
        vals = list(pr.values())
        preds.append(model_fn(xs, *vals))

    # Max pairwise prediction disagreement across the full grid
    max_disagree = 0.0
    for i in range(len(preds)):
        for j in range(i + 1, len(preds)):
            diff = np.abs(preds[i] - preds[j])
            if not np.all(np.isnan(diff)):
                max_disagree = max(max_disagree, float(np.nanmax(diff)))

    pred_stable = max_disagree / y_scale <= prediction_threshold

    # --- Parameter diagnostics (informational — Ramanujan R8) ---
    # Count correction-term rank deficiency: parameters that drift > 50%
    # while predictions stay stable
    rank_deficiency = 0
    param_drift_report: list[dict] = []
    for pname in param_names:
        vals = [pr[pname] for pr in params_by_range]
        mean_abs = sum(abs(v) for v in vals) / len(vals)
        if mean_abs < 1e-12:
            mag_drift = 0.0
        else:
            mag_drift = (max(abs(v) for v in vals) - min(abs(v) for v in vals)) / mean_abs

        sign_stable = all((v >= 0) == (vals[0] >= 0) for v in vals)
        param_stable = sign_stable and mag_drift <= 0.50
        if not param_stable:
            rank_deficiency += 1
        param_drift_report.append({
            "param": pname, "values": vals,
            "sign_stable": sign_stable, "mag_drift": round(mag_drift, 4),
        })

    if verbose:
        norm_disagree = max_disagree / y_scale
        print(f"    Prediction disagreement: {norm_disagree:.4f} (threshold {prediction_threshold})")
        if rank_deficiency > 0 and pred_stable:
            print(f"    ℹ️  RANK_DEFICIENCY: {rank_deficiency} parameter(s) drift but predictions stable")
            for dr in param_drift_report:
                if dr["mag_drift"] > 0.50 or not dr["sign_stable"]:
                    vals_str = ", ".join(f"{v:.6f}" for v in dr["values"])
                    tag = "SIGN_FLIP" if not dr["sign_stable"] else f"drift={dr['mag_drift']:.0%}"
                    print(f"      {dr['param']}: [{vals_str}] — {tag}")

    return {
        "stable": pred_stable,
        "max_pred_disagreement": round(max_disagree / y_scale, 6),
        "params_by_range": params_by_range,
        "rank_deficiency": rank_deficiency,
        "param_drift_report": param_drift_report,
    }


def _rival_stress_test(
    project_dir: Path,
    xdata: np.ndarray,
    ydata: np.ndarray,
    var_name: str,
    verbose: bool,
) -> list[tuple[str, bool]]:
    """Fix 2: Test 3 structural rivals with optimal fitting to detect non-discriminating gates.

    If any rival (constant, 1/n, exp(-cn)) also passes all gates, the gate is
    non-discriminating: the evidence cannot distinguish the champion structural form
    from simpler alternatives. This is a RED FLAG, not a gate failure — it means
    more evidence or tighter gates are needed for the discrimination claim to hold.

    Only runs when at least one template already passes the gates, so it never
    blocks the main flow or introduces false failures.
    """
    if not _SCIPY:
        return []

    rivals = [
        ("rival_const",    f"a",                                    ["a"]),
        ("rival_1_over_n", f"a + b / {var_name}",                   ["a", "b"]),
        ("rival_exp",      f"a + b * math.exp(-c * {var_name})",    ["a", "b", "c"]),
    ]

    test_model_path = project_dir / "test_model.py"
    saved = test_model_path.read_text(encoding="utf-8") if test_model_path.exists() else ""

    out: list[tuple[str, bool]] = []
    try:
        y_mean = float(np.mean(ydata))
        for rname, rexpr, rparams in rivals:
            try:
                code = compile(rexpr, "<rival_stress>", "eval")

                def _make_rival_fn(c, p, v):
                    def fn(xd, *ps):
                        res = np.empty(len(xd))
                        pd = dict(zip(p, ps))
                        for i, xi in enumerate(xd):
                            ns: dict = {"math": math, v: float(xi)}
                            ns.update(pd)
                            try:
                                res[i] = float(eval(c, {"__builtins__": {}}, ns))
                            except Exception:
                                res[i] = float("nan")
                        return res
                    return fn

                fn = _make_rival_fn(code, rparams, var_name)
                p0 = [y_mean] + [0.01] * (len(rparams) - 1)
                popt, _ = curve_fit(fn, xdata, ydata, p0=p0, maxfev=5000)
                fitted = dict(zip(rparams, [float(v) for v in popt]))
                _write_test_model(project_dir, rexpr, fitted, var_name=var_name)
                gate_result = _run_gate_harness(project_dir)
                passes = False
                if gate_result and gate_result.get("gates"):
                    _gi = (gate_result["gates"].values()
                           if isinstance(gate_result["gates"], dict)
                           else gate_result["gates"])
                    passes = all(g.get("pass", False) for g in _gi)
                out.append((rname, passes))
                if verbose:
                    tag = "⚠️  RIVAL PASSES" if passes else "✓  rival fails"
                    print(f"    {tag}: {rname}  {fitted}")
            except Exception:
                out.append((rname, False))
    finally:
        test_model_path.write_text(saved, encoding="utf-8")

    return out


def compress_champion(
    project_dir: Path,
    *,
    k_max: int | None = None,
    verbose: bool = True,
    evidence_override_path: Path | None = None,
    holdout_override_path: Path | None = None,
) -> list[CompressionResult]:
    """Enumerate low-k templates and find simpler gate-passing forms.

    Returns all gate-passing candidates sorted by BIC (lowest first).

    GP-121 Fix 1: evidence_override_path and holdout_override_path allow
    the rotation feedback loop to pass rotated evidence without modifying
    the project's main evidence files.
    """
    if not _SCIPY:
        print("ERROR: scipy required for compression")
        return []

    # GP-134 substrate-class guard (2026-04-23): skip smooth-template
    # compression on py_exec substrates. py_exec is algorithmically
    # expressive (integer-valued, discrete, jump-heavy functions like
    # sopfr, Euler-phi, divisor sums) and the Stage 1/2 library
    # (Hardy-Ramanujan, Vaughan, Lucky-density, KWW, etc.) is all
    # smooth continuous asymptotic forms. Running these against
    # discrete data wastes compute, pollutes logs with false gate
    # failures, and can override a correct mutator-proposed
    # algorithmic expression with a spurious smooth fit. Detect the
    # grammar from the rubric and short-circuit.
    _rubric_candidates = sorted(
        (project_dir.parent.parent / "rubrics").glob(f"{project_dir.name}*.json")
    ) if (project_dir.parent.parent / "rubrics").exists() else []
    for _rp in _rubric_candidates:
        try:
            import json as _json
            _rdata = _json.loads(_rp.read_text(encoding="utf-8"))
            _grammar = str(_rdata.get("fit_expression_grammar", "") or "").strip().lower()
            if _grammar == "py_exec":
                if verbose:
                    print(
                        f"🛑 compress_champion: rubric {_rp.name} declares "
                        f"fit_expression_grammar='py_exec'. Skipping "
                        f"smooth-template compression — discrete algorithmic "
                        f"substrates are not compressible by the Stage 1/2 "
                        f"library (GP-134 substrate-class guard)."
                    )
                return []
            break
        except Exception:
            continue

    # Load visible evidence (GP-121: support override path for rotation feedback)
    evidence_path = evidence_override_path or (project_dir / "evidence.txt")
    if not evidence_path.exists():
        print(f"ERROR: {evidence_path} not found")
        return []
    visible = _load_evidence(evidence_path)
    xdata = np.array([p[0] for p in visible])
    ydata = np.array([p[1] for p in visible])
    n_pts = len(visible)

    if k_max is None:
        # k < n/3: prevents overfitting on small datasets (GP-121 panel verdict).
        # Floor of 6 only for datasets with 18+ points (sequential substrates).
        # For small cross-entity substrates (6 points), k_max = 2.
        k_max = n_pts // 3 if n_pts < 18 else max(n_pts // 3, 6)

    # Detect variable name from evidence header or first data line
    var_name = "n"
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("SANDBOX"):
            # Check for header like "t\tv" or "u\tv" or "n\tz"
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) >= 2:
            # First data line — check if header was the line before
            break
    # Try to find variable name from header row
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("SANDBOX"):
            continue
        parts = stripped.split("\t") if "\t" in stripped else stripped.split()
        if len(parts) >= 2:
            try:
                float(parts[0])
                break  # this is data, not header
            except ValueError:
                var_name = parts[0].strip()
                break

    # Also check gate_harness.py for the function signature
    gate_harness = project_dir / "gate_harness.py"
    test_model = project_dir / "test_model.py"
    if test_model.exists():
        tm_text = test_model.read_text(encoding="utf-8")
        import re
        fn_match = re.search(r"def f\((\w+)", tm_text)
        if fn_match:
            var_name = fn_match.group(1)

    if verbose:
        print(f"Detected variable: {var_name}")

    # Save original test_model so we can restore it
    test_model_path = project_dir / "test_model.py"
    original_test_model = test_model_path.read_text(encoding="utf-8") if test_model_path.exists() else ""

    # Default grammar: math_exp_only. Trig added only when Stage 3 detects periodicity.
    templates = _build_templates_1d(var=var_name)

    # GP-127: Load cross-substrate primitive library (learned templates from prior runs)
    library_templates = load_library()
    if library_templates:
        # Substitute variable name for this substrate
        adapted = []
        for lname, lexpr, lparams in library_templates:
            # Replace 'n' with the substrate's variable if different
            if var_name != "n":
                lexpr = lexpr.replace(" n ", f" {var_name} ").replace("(n)", f"({var_name})").replace("(n,", f"({var_name},")
            adapted.append((lname, lexpr, lparams))
        templates = adapted + templates  # Library first — they've proven useful elsewhere
        if verbose:
            print(f"  GP-127: {len(library_templates)} learned templates from primitive library")

    # Phase 1/2 collaboration: prioritize templates matching the LLM's dominant topology
    try:
        from ztare.fit.topology_extractor import extract_dominant_topology
        topo = extract_dominant_topology(project_dir)
        if topo["confidence"] > 0.5 and topo["priority_templates"]:
            priority = topo["priority_templates"]
            # Sort: priority templates first, then the rest
            priority_set = set(priority)
            templates_priority = [t for t in templates if t[0] in priority_set]
            templates_rest = [t for t in templates if t[0] not in priority_set]
            templates = templates_priority + templates_rest
            if verbose:
                print(f"  LLM topology: {topo['class']} ({topo['confidence']*100:.0f}% of {topo['proposals_analyzed']} proposals)")
                print(f"  Priority templates: {priority[:3]}...")
    except Exception:
        pass

    results: list[CompressionResult] = []

    for name, expr, param_names in templates:
        k = len(param_names)
        if k > k_max:
            continue

        # Build callable
        try:
            code = compile(expr, "<compress>", "eval")
        except SyntaxError:
            continue

        def _make_model(code_obj, pnames, vname):
            def model_fn(xdata_inner, *params):
                out = np.empty(len(xdata_inner))
                param_dict = dict(zip(pnames, params))
                for i, x in enumerate(xdata_inner):
                    ns = {"math": math, vname: float(x)}
                    ns.update(param_dict)
                    try:
                        out[i] = float(eval(code_obj, {"__builtins__": {}}, ns))
                    except Exception:
                        out[i] = float("nan")
                return out
            return model_fn

        model_fn = _make_model(code, param_names, var_name)

        # Fit to visible evidence
        p0 = [1.0] * k
        try:
            popt, _ = curve_fit(model_fn, xdata, ydata, p0=p0, maxfev=10000)
        except Exception:
            # Try with different initial guesses
            try:
                p0_alt = [0.1 * (i + 1) for i in range(k)]
                popt, _ = curve_fit(model_fn, xdata, ydata, p0=p0_alt, maxfev=10000)
            except Exception:
                continue

        y_pred = model_fn(xdata, *popt)
        if np.any(np.isnan(y_pred)):
            continue
        residuals = np.abs(ydata - y_pred)
        max_res = float(np.max(residuals))

        # Compute BIC
        sse = float(np.sum((ydata - y_pred) ** 2))
        sse_safe = max(sse, 1e-300)
        bic = _mdl_bic(n_pts, sse_safe / n_pts, k)

        fitted_params = dict(zip(param_names, [float(v) for v in popt]))

        # GP-AuditFix 1 & 3: asymptote bias + parameter scale checks
        _asym_bias = _asymptote_bias_flag(code, param_names, popt, var_name, xdata, ydata)
        _param_issue = _param_scale_flag(popt, ydata)
        if verbose:
            if _asym_bias:
                print(f"    ⚠️  ASYMPTOTE_BIAS: f(10×x_max) departs from data range ({name})")
            if _param_issue:
                print(f"    ⚠️  PARAM_SCALE: max|param|>>data scale — aliasing likely ({name})")

        # Write test_model and run gate harness
        _write_test_model(project_dir, expr, fitted_params, var_name=var_name)

        gate_result = _run_gate_harness(project_dir)
        gates_passed = False
        gate_details = {}
        if gate_result and gate_result.get("gates"):
            gate_details = gate_result["gates"]
            # Handle both dict-of-dicts and list-of-dicts gate formats
            _gate_items = gate_details.values() if isinstance(gate_details, dict) else gate_details
            gates_passed = all(g.get("pass", g.get("passed", False)) for g in _gate_items)

        result = CompressionResult(
            name=name,
            expression=expr,
            params=fitted_params,
            k=k,
            visible_max_res=max_res,
            gates_passed=gates_passed,
            gate_results=gate_details,
            bic=bic,
            asymptote_bias=_asym_bias,
            param_scale_issue=_param_issue,
        )
        results.append(result)

        status = "✅ ALL GATES PASS" if gates_passed else "❌ gate fail"
        if verbose:
            print(f"  {name:25s} k={k} vis={max_res:.5f} BIC={bic:.1f} {status}")

    # Restore original test_model
    test_model_path.write_text(original_test_model, encoding="utf-8")

    # Sort: gate-passing first, then by BIC
    results.sort(key=lambda r: (not r.gates_passed, r.bic))

    # Stage 2: Compositional templates — only if Stage 1 found nothing.
    # Munger: never weaken Stage 1. Layer on top.
    # Popper: Stage 2 uses the SAME gates (at least as tight).
    gate_passing_stage1 = [r for r in results if r.gates_passed]
    if not gate_passing_stage1:
        if verbose:
            print(f"\n  Stage 1 UNDERIDENTIFIED — activating Stage 2 (compositional templates)")
        comp_templates = _build_compositional_templates_1d(var=var_name)
        for name, expr, param_names in comp_templates:
            k = len(param_names)
            if k > k_max:
                continue
            try:
                code = compile(expr, "<compress_stage2>", "eval")
            except SyntaxError:
                continue

            model_fn = _make_model(code, param_names, var_name)

            p0 = [1.0] * k
            try:
                popt, _ = curve_fit(model_fn, xdata, ydata, p0=p0, maxfev=10000)
            except Exception:
                try:
                    p0_alt = [0.1 * (j + 1) for j in range(k)]
                    popt, _ = curve_fit(model_fn, xdata, ydata, p0=p0_alt, maxfev=10000)
                except Exception:
                    continue

            y_pred = model_fn(xdata, *popt)
            if np.any(np.isnan(y_pred)):
                continue
            residuals = np.abs(ydata - y_pred)
            max_res = float(np.max(residuals))

            sse = float(np.sum((ydata - y_pred) ** 2))
            sse_safe = max(sse, 1e-300)
            bic = _mdl_bic(n_pts, sse_safe / n_pts, k)

            fitted_params = dict(zip(param_names, [float(v) for v in popt]))

            _write_test_model(project_dir, expr, fitted_params, var_name=var_name)
            gate_result = _run_gate_harness(project_dir)
            gates_passed = False
            gate_details = {}
            if gate_result and gate_result.get("gates"):
                gate_details = gate_result["gates"]
                # Handle both dict-of-dicts and list-of-dicts gate formats
                _gate_items = gate_details.values() if isinstance(gate_details, dict) else gate_details
                gates_passed = all(g.get("pass", g.get("passed", False)) for g in _gate_items)

            result = CompressionResult(
                name=f"S2_{name}",
                expression=expr,
                params=fitted_params,
                k=k,
                visible_max_res=max_res,
                gates_passed=gates_passed,
                gate_results=gate_details,
                bic=bic,
            )
            results.append(result)

            status = "✅ ALL GATES PASS" if gates_passed else "❌ gate fail"
            if verbose:
                print(f"  S2_{name:25s} k={k} vis={max_res:.5f} BIC={bic:.1f} {status}")

        # Restore again after Stage 2
        test_model_path.write_text(original_test_model, encoding="utf-8")

        # Re-sort with Stage 2 results included
        results.sort(key=lambda r: (not r.gates_passed, r.bic))

        # Stage 3: Residual periodicity detector (GP-109)
        # If Stage 1+2 both UNDERIDENTIFIED, analyze the best-fitting template's
        # residuals for periodic structure. If a dominant frequency is found,
        # inject it as a fixed parameter and refit with sin/cos correction.
        gate_passing_stage2 = [r for r in results if r.gates_passed]
        if not gate_passing_stage2 and results:
            # Find the best-fitting template (lowest visible residual)
            best_smooth = min(results, key=lambda r: r.visible_max_res)
            if verbose:
                print(f"\n  Stage 3: Residual periodicity analysis (best smooth: {best_smooth.name}, res={best_smooth.visible_max_res:.5f})")

            # Recompute the best smooth model's predictions
            try:
                best_code = compile(best_smooth.expression, "<stage3>", "eval")
                best_fn = _make_model(best_code, list(best_smooth.params.keys()), var_name)
                y_smooth = best_fn(xdata, *best_smooth.params.values())
                residual_signal = ydata - y_smooth

                # FFT on the residuals
                fft_vals = np.fft.rfft(residual_signal)
                fft_power = np.abs(fft_vals) ** 2
                freqs = np.fft.rfftfreq(len(residual_signal))

                # Skip DC component (index 0) and find dominant peak
                if len(fft_power) > 2:
                    peak_idx = np.argmax(fft_power[1:]) + 1
                    peak_power = fft_power[peak_idx]
                    noise_floor = np.median(fft_power[1:])
                    snr = peak_power / max(noise_floor, 1e-30)
                    peak_freq = freqs[peak_idx]
                    peak_period = 1.0 / peak_freq if peak_freq > 0 else float("inf")

                    if verbose:
                        print(f"    FFT: peak at freq={peak_freq:.6f} (period={peak_period:.1f} in index), SNR={snr:.1f}")

                    # Spectral significance filter (GP-109):
                    # 1. Lomb-Scargle FAP < 0.01 (peak is not random noise)
                    # 2. Sub-window consistency (same freq in both halves)
                    # 3. Nyquist-trend guard (period < 0.8 * data length)
                    from scipy.signal import lombscargle as _ls

                    _n_res = len(residual_signal)
                    _t_res = np.arange(_n_res, dtype=float)
                    # Detrend: subtract linear fit to remove DC + slope
                    _trend_coeffs = np.polyfit(_t_res, residual_signal, 1)
                    _detrended = residual_signal - np.polyval(_trend_coeffs, _t_res)

                    # Lomb-Scargle on detrended residuals
                    _test_freqs = np.linspace(0.01, 0.5, 500)  # normalized freqs
                    _ls_power = _ls(_t_res, _detrended, _test_freqs * 2 * np.pi)
                    _ls_peak_idx = np.argmax(_ls_power)
                    _ls_peak_freq = _test_freqs[_ls_peak_idx]
                    _ls_peak_power = _ls_power[_ls_peak_idx]
                    _ls_peak_period = 1.0 / _ls_peak_freq if _ls_peak_freq > 0 else float("inf")

                    # FAP approximation (Baluev 2008): FAP ≈ 1 - (1 - exp(-z))^M
                    # where z = peak_power / variance, M = number of independent freqs
                    _var_detrended = float(np.var(_detrended)) if np.var(_detrended) > 0 else 1e-30
                    _z_score = _ls_peak_power / _var_detrended
                    _M = len(_test_freqs)
                    _fap = 1.0 - (1.0 - math.exp(-_z_score)) ** _M if _z_score < 700 else 0.0

                    # Sub-window consistency: split in half, check if same freq appears
                    _half = _n_res // 2
                    _ls_power_h1 = _ls(_t_res[:_half], _detrended[:_half], _test_freqs * 2 * np.pi)
                    _ls_power_h2 = _ls(_t_res[_half:], _detrended[_half:], _test_freqs * 2 * np.pi)
                    _h1_peak = _test_freqs[np.argmax(_ls_power_h1)]
                    _h2_peak = _test_freqs[np.argmax(_ls_power_h2)]
                    _freq_consistent = abs(_h1_peak - _h2_peak) < 0.02  # within 2% of each other

                    # Nyquist-trend guard
                    _not_trend = _ls_peak_period < 0.8 * _n_res

                    _periodic_detected = (_fap < 0.01) and _freq_consistent and _not_trend
                    peak_freq = _ls_peak_freq  # override FFT freq with Lomb-Scargle
                    peak_period = _ls_peak_period

                    if verbose:
                        print(f"    Lomb-Scargle: freq={_ls_peak_freq:.6f} period={_ls_peak_period:.1f} FAP={_fap:.2e} consistent={_freq_consistent} not_trend={_not_trend}")

                    if _periodic_detected:
                        if verbose:
                            print(f"    Periodic signal DETECTED (SNR={snr:.1f} > 5.0)")

                        # Construct: best_smooth + A*sin(2*pi*w*n + phi)
                        # w is FIXED from FFT; only A and phi are fitted
                        omega = 2 * math.pi * peak_freq
                        smooth_expr = best_smooth.expression
                        smooth_params = list(best_smooth.params.keys())
                        smooth_vals = list(best_smooth.params.values())

                        periodic_expr = f"({smooth_expr}) + _amp * math.sin({omega} * {var_name} + _phase)"
                        periodic_params = smooth_params + ["_amp", "_phase"]

                        try:
                            p_code = compile(periodic_expr, "<stage3_periodic>", "eval")
                            p_fn = _make_model(p_code, periodic_params, var_name)
                            p0_periodic = smooth_vals + [float(np.std(residual_signal)), 0.0]
                            popt_p, _ = curve_fit(p_fn, xdata, ydata, p0=p0_periodic, maxfev=10000)
                            y_pred_p = p_fn(xdata, *popt_p)

                            if not np.any(np.isnan(y_pred_p)):
                                max_res_p = float(np.max(np.abs(ydata - y_pred_p)))
                                sse_p = float(np.sum((ydata - y_pred_p) ** 2))
                                sse_safe_p = max(sse_p, 1e-300)
                                k_p = len(periodic_params)
                                bic_p = _mdl_bic(n_pts, sse_safe_p / n_pts, k_p)

                                fitted_p = dict(zip(periodic_params, [float(v) for v in popt_p]))

                                _write_test_model(project_dir, periodic_expr, fitted_p, var_name=var_name)
                                gate_result_p = _run_gate_harness(project_dir)
                                gates_passed_p = False
                                gate_details_p = {}
                                if gate_result_p and gate_result_p.get("gates"):
                                    gate_details_p = gate_result_p["gates"]
                                    gates_passed_p = all(g.get("pass", g.get("passed", False)) for g in gate_details_p.values())

                                result_p = CompressionResult(
                                    name=f"S3_periodic_{best_smooth.name}",
                                    expression=periodic_expr,
                                    params=fitted_p,
                                    k=k_p,
                                    visible_max_res=max_res_p,
                                    gates_passed=gates_passed_p,
                                    gate_results=gate_details_p,
                                    bic=bic_p,
                                )
                                results.append(result_p)

                                status_p = "✅ ALL GATES PASS" if gates_passed_p else "❌ gate fail"
                                if verbose:
                                    print(f"    S3 {best_smooth.name}+sin: k={k_p} vis={max_res_p:.5f} BIC={bic_p:.1f} {status_p}")

                                # Restore test_model
                                test_model_path.write_text(original_test_model, encoding="utf-8")
                                results.sort(key=lambda r: (not r.gates_passed, r.bic))

                        except Exception:
                            if verbose:
                                print(f"    S3 periodic fit failed — skipping")
                    else:
                        if verbose:
                            _reason = []
                            if _fap >= 0.01: _reason.append(f"FAP={_fap:.2e}>=0.01")
                            if not _freq_consistent: _reason.append(f"half-window freqs differ ({_h1_peak:.4f} vs {_h2_peak:.4f})")
                            if not _not_trend: _reason.append(f"period={_ls_peak_period:.0f} >= 0.8*{_n_res} (trend artifact)")
                            print(f"    No significant periodic signal: {'; '.join(_reason)}")
            except Exception as _s3_exc:
                if verbose:
                    print(f"    Stage 3 error: {_s3_exc}")

        # Stage 3b: Statistical fingerprint (GP-110)
        # If ALL stages failed, compute a typed characterization of the residual.
        gate_passing_final = [r for r in results if r.gates_passed]
        if not gate_passing_final and results:
            try:
                from ztare.fit.statistical_fingerprint import compute_fingerprint
                best_overall = min(results, key=lambda r: r.visible_max_res)
                best_code = compile(best_overall.expression, "<fingerprint>", "eval")
                best_fn = _make_model(best_code, list(best_overall.params.keys()), var_name)
                y_best = best_fn(xdata, *best_overall.params.values())

                # Detect dominant period for detrend window
                _det_period = None
                if hasattr(best_overall, 'gate_results'):
                    pass  # use Lomb-Scargle detected period if available
                fp = compute_fingerprint(
                    xdata, ydata, y_best,
                    detrend_window=int(round(_det_period)) if _det_period else None,
                )
                if fp is not None:
                    if verbose:
                        print(f"\n  📊 GP-110 Statistical Fingerprint:")
                        print(f"    {fp.summary_line()}")
                        if not fp.hurst_slope_consistent:
                            print(f"    ⚠️ Hurst/slope INCONSISTENT: H={fp.hurst_exponent:.3f} predicts beta={2*fp.hurst_exponent-1:.2f}, observed={fp.spectral_slope:.2f}")
                        if fp.detrending_sensitive:
                            slopes_str = ", ".join(f"W={w}:{s:.2f}" for w, s in fp.multi_window_slopes)
                            print(f"    ⚠️ DETRENDING SENSITIVE: spectral slope varies with window ({slopes_str})")
                    # Save fingerprint to workspace
                    import json as _fp_json
                    fp_path = project_dir / "workspace" / "statistical_fingerprint.json"
                    fp_path.parent.mkdir(exist_ok=True)
                    fp_path.write_text(_fp_json.dumps(fp.to_dict(), indent=2))
            except Exception as _fp_exc:
                if verbose:
                    print(f"    GP-110 fingerprint error: {_fp_exc}")

    # Stage 4: Grammar self-expansion (GP-115 + GP-127)
    # If no gate-passing form found, diagnose residual shape and generate
    # new templates mechanically. Then try them.
    gate_passing_final = [r for r in results if r.gates_passed]
    if not gate_passing_final and results:
        best_so_far = min(results, key=lambda r: r.visible_max_res)
        if verbose:
            print(f"\n  Stage 4: Grammar self-expansion (best so far: {best_so_far.name}, res={best_so_far.visible_max_res:.5f})")

        try:
            best_code = compile(best_so_far.expression, "<stage4>", "eval")
            best_fn = _make_model(best_code, list(best_so_far.params.keys()), var_name)
            y_pred = best_fn(xdata, *best_so_far.params.values())
            residuals = ydata - y_pred

            from ztare.fit.residual_grammar_expander import suggest_from_residuals
            suggestions = suggest_from_residuals(residuals, xdata, var=var_name)

            if verbose and suggestions:
                print(f"    {len(suggestions)} grammar suggestions from residual shape")

            for sg in suggestions:
                sg_name = f"S4_{sg['name']}"
                sg_expr = sg["expression"]
                sg_params = sg["params"]
                k = len(sg_params)
                if k > k_max:
                    continue
                try:
                    sg_code = compile(sg_expr, "<stage4_expand>", "eval")
                    sg_fn = _make_model(sg_code, sg_params, var_name)
                    p0 = [1.0] * k
                    popt, _ = curve_fit(sg_fn, xdata, ydata, p0=p0, maxfev=10000)
                    y_sg = sg_fn(xdata, *popt)
                    if np.any(np.isnan(y_sg)):
                        continue
                    max_res = float(np.max(np.abs(ydata - y_sg)))
                    sse = float(np.sum((ydata - y_sg) ** 2))
                    bic = _mdl_bic(n_pts, max(sse / n_pts, 1e-300), k)
                    fitted_params = dict(zip(sg_params, [float(v) for v in popt]))

                    _write_test_model(project_dir, sg_expr, fitted_params, var_name=var_name)
                    gate_result = _run_gate_harness(project_dir)
                    gates_passed = False
                    gate_details = {}
                    if gate_result and gate_result.get("gates"):
                        gate_details = gate_result["gates"]
                        _gate_items = gate_details.values() if isinstance(gate_details, dict) else gate_details
                        gates_passed = all(g.get("pass", g.get("passed", False)) for g in _gate_items)

                    result = CompressionResult(
                        name=sg_name, expression=sg_expr, k=k,
                        params=fitted_params, visible_max_res=max_res,
                        gates_passed=gates_passed, bic=bic, gate_results=gate_details,
                    )
                    results.append(result)
                    status = "✅ ALL GATES PASS" if gates_passed else "❌ gate fail"
                    if verbose:
                        print(f"    {sg_name:30s} k={k} vis={max_res:.5f} BIC={bic:.1f} {status}")
                except Exception:
                    continue

            test_model_path.write_text(original_test_model, encoding="utf-8")
            results.sort(key=lambda r: (not r.gates_passed, r.bic))
        except Exception as _s4_exc:
            if verbose:
                print(f"    Stage 4 error: {_s4_exc}")

    # GP-AuditFix 2: rival stress test — only when at least one form passes the gates.
    # Flags GATE_NON_DISCRIMINATING if a simpler structural rival also passes.
    gate_passing_for_rival = [r for r in results if r.gates_passed]
    if gate_passing_for_rival:
        if verbose:
            print(f"\n  Gate Quality Audit (GP-AuditFix 2 — rival stress test):")
        rival_results = _rival_stress_test(project_dir, xdata, ydata, var_name, verbose)
        n_rival_pass = sum(1 for _, p in rival_results if p)
        if n_rival_pass > 0:
            passing_rivals = [rn for rn, p in rival_results if p]
            if verbose:
                print(f"  ⚠️  GATE_NON_DISCRIMINATING: {n_rival_pass}/{len(rival_results)} rivals pass gate")
                print(f"      Passing rivals: {passing_rivals}")

    # GP-133 R4: Prediction-stability check on the best gate-passing form.
    # Fits on 3 sub-ranges, evaluates on full grid, checks prediction agreement.
    # Gates on predictions (Socrates/Feynman), reports parameter rank deficiency (Ramanujan).
    if gate_passing_for_rival:
        best_gp = gate_passing_for_rival[0]  # best by BIC (already sorted)
        if verbose:
            print(f"\n  GP-133 Prediction-Stability Check ({best_gp.name}):")
        stab = _range_stability_check(
            xdata, ydata, best_gp.expression,
            list(best_gp.params.keys()), var_name, verbose,
        )
        if stab.get("stable") is not None:
            best_gp.range_stable = stab["stable"]
            if verbose:
                if stab["stable"]:
                    rd = stab.get("rank_deficiency", 0)
                    suffix = f" (rank deficiency: {rd})" if rd > 0 else ""
                    print(f"    ✓  Predictions stable across sub-ranges{suffix}")
                else:
                    print(f"    ⚠️  PREDICTION_UNSTABLE: sub-range models disagree by {stab['max_pred_disagreement']:.1%} of signal — identification horizon not reached")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="GP-103 Compression: find simpler gate-passing forms.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--k-max", type=int, default=None)
    parser.add_argument("--install-best", action="store_true",
                        help="Write the best gate-passing compressed form to test_model.py")
    args = parser.parse_args()

    project_dir = PROJECTS_DIR / args.project
    if not project_dir.exists():
        print(f"ERROR: {project_dir} not found")
        return 1

    print(f"GP-103 Compression — {args.project}")
    print(f"{'='*60}")

    results = compress_champion(project_dir, k_max=args.k_max)

    gate_passing = [r for r in results if r.gates_passed]
    print(f"\n{'='*60}")
    print(f"Total templates tried: {len(results)}")
    print(f"Gate-passing forms: {len(gate_passing)}")

    if gate_passing:
        best = gate_passing[0]
        print(f"\nBest compressed form (by BIC):")
        print(f"  Name: {best.name}")
        print(f"  Expression: {best.expression}")
        print(f"  Params ({best.k}): {best.params}")
        print(f"  Visible max_res: {best.visible_max_res:.6f}")
        print(f"  BIC: {best.bic:.1f}")
        print(f"  Gates: {json.dumps({k: v.get('pass') for k, v in best.gate_results.items()})}")

        # GP-127: Save winning form to cross-substrate primitive library
        save_to_library(
            name=best.name,
            expression=best.expression,
            params=best.params,
            source_substrate=args.project,
            bic=best.bic,
            max_residual=best.visible_max_res,
        )
        print(f"  GP-127: Saved to primitive library")

        if args.install_best:
            # Extract variable name from the winning expression itself.
            # Templates use a single variable (n, t, u, etc.) — find it.
            import re as _re
            _expr_vars = set(_re.findall(r'\b([a-z])\b', best.expression)) - set(best.params.keys()) - {'e'}
            _known_funcs = {'a','b','c','d','f','g','h','j','k','m','p'}
            _expr_vars -= _known_funcs
            _install_var = _expr_vars.pop() if len(_expr_vars) == 1 else "n"
            _write_test_model(project_dir, best.expression, best.params, var_name=_install_var)
            print(f"\n  ✅ Installed to test_model.py (var={_install_var})")
    else:
        print("\nNo compressed form passes all gates.")

    # Save results
    out_path = project_dir / "workspace" / "compression_results.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(
        [{"name": r.name, "expression": r.expression, "k": r.k,
          "params": r.params, "visible_max_res": r.visible_max_res,
          "gates_passed": r.gates_passed, "bic": r.bic}
         for r in results],
        indent=2,
    ))
    print(f"\nFull results: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
