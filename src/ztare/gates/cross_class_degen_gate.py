"""G-CROSS-CLASS-DEGEN — falsify universality claims when 'constant'
parameters disagree across classes by more than a stated dex threshold.

A real universal law has the same value of every named constant
(a₀, M_Pl, M⁵, β, etc.) across all system classes. If the apparatus's
fitter produces wildly different best-fit values for the same parameter
when refit on class A vs class B vs class D, the form is class-conditional
in disguise — its "constants" are absorbing class-dependent residual
structure that the form's algebraic shape does not encode honestly.

Companion to G-LAGRANGIAN-NONTRIVIAL (B1), G-SCREEN-SIGN (B2), and
G-FEATURE-CONTRIB (B3). Where B1 audits Lagrangian derivation content,
B2 audits empirical screening direction, and B3 audits per-feature
empirical load-bearingness, B4 audits per-class parameter consistency.

GP-183 Phase B4.

Verdict:
  "ok"                    — every parameter's per-class spread is
                            ≤ threshold (default 1 dex).
  "cross_class_degenerate" — at least one parameter's spread > threshold.
  "not_enabled"           — rubric.enable_cross_class_degen_check=false.
  "insufficient_data"     — fewer than 2 classes had enough rows for a
                            stable per-class refit.

Output schema:
  {
    "gate_id": "G-CROSS-CLASS-DEGEN",
    "verdict": "ok" | "cross_class_degenerate" | "not_enabled" | "insufficient_data",
    "reason": str,
    "threshold_dex": float,
    "per_parameter_spread": [
        {"parameter": "log_a0", "min_value": -23.1, "max_value": -22.4,
         "spread_dex": 0.30, "per_class_values": {"A": -22.8, "B": -23.1, ...},
         "degenerate": False}, ...
    ] | [],
    "classes_evaluated": ["A", "B", "D", "N"],
    "min_rows_per_class": 5,
  }

Activated only when rubric.enable_cross_class_degen_check=true. The
apparatus caps at rubric.cap_for_cross_class_degen (default 50) with
reason `cross_class_degenerate_parameters` when the gate fires.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Optional

GATE_ID = "G-CROSS-CLASS-DEGEN"


# ── Safe-eval (mirrors B2/B3 environment) ───────────────────────────


def _safe_eval(form_src: str, features: dict, params: dict) -> Optional[float]:
    """Evaluate a PARAMETRIC_FORM expression. Returns None on any error."""
    try:
        code = compile(form_src, "<cross_class_degen_form>", "eval")
    except SyntaxError:
        return None
    safe_globals = {
        "__builtins__": {},
        "math": math, "exp": math.exp, "log": math.log,
        "log10": math.log10, "log2": math.log2,
        "sqrt": math.sqrt, "pow": pow,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "tanh": math.tanh, "asinh": math.asinh,
        "atan": math.atan, "atan2": math.atan2,
        "sigmoid": lambda z, k=1.0, x0=0.0: 1.0 / (1.0 + math.exp(-k * (z - x0)))
                   if abs(k * (z - x0)) < 60 else (0.0 if z < x0 else 1.0),
        "erf": math.erf, "erfc": math.erfc,
        "abs": abs, "min": min, "max": max,
        "where": lambda c, a, b: float(a) if bool(c) else float(b),
        "pi": math.pi, "e": math.e,
    }
    try:
        v = eval(code, safe_globals, {"features": features, "params": params})
    except Exception:                                                       # noqa: BLE001
        return None
    if v is None: return None
    try: vf = float(v)
    except (TypeError, ValueError): return None
    if math.isnan(vf) or math.isinf(vf): return None
    return vf


def _load_substrate_rows(project_dir: Path) -> list[dict]:
    """Aggregate rows from features.py with class labels intact."""
    feat_path = project_dir / "features.py"
    rows: list[dict] = []
    if feat_path.exists():
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location("_cross_class_features", str(feat_path))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for accessor in ("visible_rows", "holdout_rows", "farther_tail_rows", "audit_rows"):
                fn = getattr(mod, accessor, None)
                if callable(fn):
                    try:
                        for entry in fn():
                            if isinstance(entry, tuple) and len(entry) == 3:
                                _id, y_obs, feats = entry
                                if isinstance(feats, dict):
                                    row = dict(feats)
                                    if y_obs is not None:
                                        row["y_true"] = float(y_obs)
                                    rows.append(row)
                    except Exception:                                       # noqa: BLE001
                        continue
            return rows
        except Exception:                                                   # noqa: BLE001
            rows = []
    raw_dir = project_dir / "raw"
    csv_files = list(raw_dir.glob("unified_*.csv")) if raw_dir.exists() else []
    if not csv_files and raw_dir.exists():
        csv_files = list(raw_dir.glob("*.csv"))
    if not csv_files:
        return []
    csv_path = max(csv_files, key=lambda p: p.stat().st_mtime)
    with csv_path.open() as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            row: dict[str, Any] = {}
            for k, v in r.items():
                if v in (None, ""):
                    continue
                try:
                    row[k] = float(v)
                except (ValueError, TypeError):
                    row[k] = v
            if "g_obs" in row:
                row["y_true"] = float(row["g_obs"])
            rows.append(row)
    return rows


def _per_row_relative_error(
    form_src: str, params: dict, rows: list[dict],
) -> float:
    """Mean relative error over rows. NaN if no valid rows."""
    rel = []
    for row in rows:
        y_true = row.get("y_true")
        if y_true is None or not isinstance(y_true, (int, float)) or y_true <= 0:
            continue
        feats = {k: v for k, v in row.items() if k != "y_true"}
        y_pred = _safe_eval(form_src, feats, params)
        if y_pred is None:
            continue
        rel.append(abs(y_pred - float(y_true)) / abs(float(y_true)))
    if not rel:
        return float("nan")
    return sum(rel) / len(rel)


def _refit_on_rows(
    form_src: str, parameter_names: list[str], initial_params: dict,
    rows: list[dict], n_starts: int = 8, max_iter: int = 1500,
) -> Optional[dict]:
    """Refit the form's parameters on a class-restricted row subset using
    scipy.optimize.minimize Nelder-Mead. Returns the best-fit params
    dict or None if the fit fails.

    Uses log-space drift on each starting point so parameters span the
    correct numerical scale; small n_starts because per-class refits
    are an audit step, not a primary fit.
    """
    try:
        import numpy as np
        from scipy.optimize import minimize
    except ImportError:
        return None

    # Initial vector in log-space (use the supplied values directly;
    # the form's MODEL_PARAMS already encode log-space convention via
    # log_<name> naming — we pass values as-is and let scipy explore).
    x0 = [float(initial_params.get(name, 1.0)) for name in parameter_names]
    if not x0:
        return None

    def loss(x):
        params = {name: float(x[i]) for i, name in enumerate(parameter_names)}
        mre = _per_row_relative_error(form_src, params, rows)
        if not math.isfinite(mre):
            return 1e9
        return float(mre)

    rng = np.random.default_rng(seed=12345)
    best = None
    for trial in range(n_starts):
        pert = np.array(x0) + 0.5 * rng.standard_normal(len(x0))
        try:
            res = minimize(
                loss, pert, method="Nelder-Mead",
                options={"maxiter": max_iter, "xatol": 1e-5, "fatol": 1e-5},
            )
            if (best is None or res.fun < best.fun) and math.isfinite(res.fun):
                best = res
        except Exception:                                                    # noqa: BLE001
            continue
    if best is None:
        return None
    return {name: float(best.x[i]) for i, name in enumerate(parameter_names)}


def _stable_class_order(class_keys) -> list[str]:
    """Match the apparatus convention used in per_class_fit_audit / B2."""
    canonical = ["A", "B", "C", "D", "N", "S"]
    in_canon = [k for k in canonical if k in class_keys]
    extras = sorted(k for k in class_keys if k not in canonical)
    return in_canon + extras


def evaluate_cross_class_degen(
    form_src: str,
    parameter_names: list[str],
    initial_params: dict,
    *,
    project_dir: Path,
    rubric_data: dict,
    threshold_dex: Optional[float] = None,
    min_rows_per_class: int = 5,
    classes_to_test: Optional[list[str]] = None,
) -> dict:
    """Refit `parameter_names` per-class and check whether any
    parameter's range across classes exceeds `threshold_dex` (default 1).

    Class restriction is on `system_class` (or rubric.substrate_class_key
    if overridden). Solar (S) and Banik (N) classes are excluded by
    default because their row counts are too small for stable refit;
    operators can override via classes_to_test.
    """
    if not bool(rubric_data.get("enable_cross_class_degen_check", False)):
        return {
            "gate_id": GATE_ID, "verdict": "not_enabled",
            "reason": "rubric.enable_cross_class_degen_check is false; gate skipped",
            "threshold_dex": threshold_dex or 1.0,
            "per_parameter_spread": [],
            "classes_evaluated": [], "min_rows_per_class": min_rows_per_class,
        }

    if threshold_dex is None:
        threshold_dex = float(rubric_data.get("cross_class_degen_threshold_dex", 1.0))

    if not form_src or not parameter_names:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": "no PARAMETRIC_FORM or PARAMETER_NAMES supplied",
            "threshold_dex": threshold_dex,
            "per_parameter_spread": [],
            "classes_evaluated": [], "min_rows_per_class": min_rows_per_class,
        }

    rows = _load_substrate_rows(project_dir)
    if not rows:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": f"no substrate rows loaded from {project_dir}",
            "threshold_dex": threshold_dex,
            "per_parameter_spread": [],
            "classes_evaluated": [], "min_rows_per_class": min_rows_per_class,
        }

    class_key = rubric_data.get("substrate_class_key", "system_class")
    # Group by class
    class_rows: dict[str, list[dict]] = {}
    for row in rows:
        cls = row.get(class_key)
        if cls is None:
            continue
        class_rows.setdefault(str(cls), []).append(row)

    # Default: test classes with >= min_rows_per_class rows. Default
    # excludes the smallest classes unless explicitly requested.
    if classes_to_test is None:
        classes_to_test = [cls for cls, rs in class_rows.items()
                           if len(rs) >= min_rows_per_class]
    classes_to_test = _stable_class_order(classes_to_test)
    classes_to_test = [c for c in classes_to_test
                       if len(class_rows.get(c, [])) >= min_rows_per_class]

    if len(classes_to_test) < 2:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": (
                f"fewer than 2 classes have >= {min_rows_per_class} rows "
                f"(found {len(classes_to_test)}: {classes_to_test}). "
                f"Cannot compute cross-class spread."
            ),
            "threshold_dex": threshold_dex,
            "per_parameter_spread": [],
            "classes_evaluated": classes_to_test, "min_rows_per_class": min_rows_per_class,
        }

    # Per-class refits
    per_class_fitted: dict[str, dict] = {}
    refit_failures: list[str] = []
    for cls in classes_to_test:
        rs = class_rows[cls]
        fitted = _refit_on_rows(
            form_src, parameter_names, initial_params, rs,
            n_starts=int(rubric_data.get("cross_class_degen_n_starts", 8)),
        )
        if fitted is None:
            refit_failures.append(cls)
            continue
        per_class_fitted[cls] = fitted

    if len(per_class_fitted) < 2:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": (
                f"per-class refit succeeded on fewer than 2 classes "
                f"(success: {list(per_class_fitted.keys())}, "
                f"failed: {refit_failures}). Cannot compute spread."
            ),
            "threshold_dex": threshold_dex,
            "per_parameter_spread": [],
            "classes_evaluated": list(per_class_fitted.keys()),
            "min_rows_per_class": min_rows_per_class,
        }

    # Compute per-parameter spread in dex. We assume parameter_names
    # follow the apparatus convention (log-space params named log_<x>);
    # for log-space parameters the spread is directly the dex value
    # (max - min in natural-log space, which we convert to log10 by
    # dividing by ln(10)). For non-log parameters, we still report
    # max - min and label spread_dex with a note.
    per_parameter: list[dict] = []
    degen_count = 0
    for name in parameter_names:
        vals = [per_class_fitted[c].get(name) for c in per_class_fitted
                if isinstance(per_class_fitted[c].get(name), (int, float))]
        if len(vals) < 2:
            per_parameter.append({
                "parameter": name,
                "min_value": None, "max_value": None,
                "spread_dex": None,
                "per_class_values": {c: per_class_fitted[c].get(name) for c in per_class_fitted},
                "degenerate": False,
                "note": "insufficient per-class fits for this parameter",
            })
            continue
        vmin, vmax = min(vals), max(vals)
        spread_natural = vmax - vmin
        # Convention: parameter name with `log_` prefix means natural-log space
        # → dex = spread / ln(10). Other names: report raw spread, do NOT
        # apply dex conversion (they are linear-space), and use threshold
        # on absolute spread instead.
        is_log_space = name.startswith("log_") or name.startswith("ln_")
        if is_log_space:
            spread_dex = spread_natural / math.log(10.0)
        else:
            # Linear-space parameter — convert to dex via |max/min| if both
            # have the same sign and are nonzero; otherwise keep the linear
            # spread as the "spread_dex" surrogate.
            if vmin > 0 and vmax > 0:
                spread_dex = math.log10(vmax / vmin)
            elif vmin < 0 and vmax < 0:
                spread_dex = math.log10(abs(vmin) / abs(vmax))
            else:
                # Sign-crossing or zero — fall back to raw spread
                spread_dex = float(spread_natural)
        is_degen = bool(spread_dex > threshold_dex)
        if is_degen:
            degen_count += 1
        per_parameter.append({
            "parameter": name,
            "min_value": float(vmin), "max_value": float(vmax),
            "spread_dex": float(spread_dex),
            "per_class_values": {c: float(per_class_fitted[c][name])
                                 for c in per_class_fitted
                                 if isinstance(per_class_fitted[c].get(name), (int, float))},
            "degenerate": is_degen,
            "is_log_space_param": is_log_space,
        })

    if degen_count > 0:
        names = [e["parameter"] for e in per_parameter if e.get("degenerate")]
        reason = (
            f"{degen_count} of {len(per_parameter)} parameter(s) span > "
            f"{threshold_dex:.2f} dex across classes {list(per_class_fitted.keys())}: "
            f"{names}. The form's 'constants' are absorbing class-conditional "
            f"residual structure rather than supplying universal values. A real "
            f"universal law's named constants must hold the same value when "
            f"refit on disjoint class subsets."
        )
        verdict = "cross_class_degenerate"
    else:
        reason = (
            f"all {len(per_parameter)} parameter(s) hold values within "
            f"{threshold_dex:.2f} dex across classes "
            f"{list(per_class_fitted.keys())}; the form's named constants "
            f"are class-consistent at the audit threshold."
        )
        verdict = "ok"

    return {
        "gate_id": GATE_ID, "verdict": verdict,
        "reason": reason,
        "threshold_dex": float(threshold_dex),
        "per_parameter_spread": per_parameter,
        "classes_evaluated": list(per_class_fitted.keys()),
        "min_rows_per_class": min_rows_per_class,
    }
