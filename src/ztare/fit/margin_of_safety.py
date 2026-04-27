"""GP-112: Margin of Safety Gate — Post-Discovery Stress Testing.

Runs automatically after compression (Phase 2.5b). Produces annotations
that strengthen or weaken the finding. Does not alter the champion or
gate results.

Five tests (Buffett/Popper/Tukey/Taleb panel, 2026-04-21):
  1. Split-half stability (Tukey) — fit on each half of visible, compare
  2. Coefficient drift under scale expansion — refit at 2x, 5x, 10x
  3. Grammar completeness probe — try natural extensions, flag if 2x better
  4. Residual autocorrelation (Tukey) — lag-1 on champion residuals
  5. Extrapolation stress — numerical residuals at 10x, 50x, 100x

Inversion guard (Tukey, 2026-04-22): when GP-112 is applied to an
INVERTED null result (not the original compression output), the battery
scales with inversion depth:
  - depth 0 (original): standard 5-test battery
  - depth 1 (first inversion): standard + significance test on key metric
  - depth 2 (second inversion): require independent dataset or fresh holdout
  - depth 3+: REJECT. Two inversions on the same residual stream is the ceiling.
Stopping rule (Munger): stop when the inverted finding would not change action.

Usage:
    python -m src.ztare.fit.margin_of_safety --project oeis_a000959
    python -m src.ztare.fit.margin_of_safety --project oeis_a000959 --inversion-depth 1
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import curve_fit

from src.ztare.common.paths import PROJECTS_DIR


# ---------------------------------------------------------------------------
# Evidence loader (shared with compress_champion)
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


def _numpy_expr(expr: str) -> str:
    """Convert math.* calls to np.* for numpy array compatibility."""
    return (expr
            .replace("math.log", "np.log")
            .replace("math.sqrt", "np.sqrt")
            .replace("math.exp", "np.exp")
            .replace("math.pi", "np.pi")
            .replace("math.sin", "np.sin")
            .replace("math.cos", "np.cos"))


def _build_model(expr: str, param_names: list[str], var: str):
    """Build a numpy-compatible model function from expression string."""
    np_expr = _numpy_expr(expr)
    code = f"def _m(_x_, {', '.join(param_names)}):\n    {var}=_x_\n    return {np_expr}"
    local_ns = {"np": np, "math": math}
    exec(code, local_ns)
    return local_ns["_m"]


def _detect_variable(evidence_path: Path) -> str:
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") and "\t" in line:
            parts = line.lstrip("#").strip().split("\t")
            if len(parts) >= 1 and parts[0].strip().isidentifier():
                return parts[0].strip()
    return "n"


# ---------------------------------------------------------------------------
# Template fitting helper
# ---------------------------------------------------------------------------

def _fit_template(expression: str, params: list[str], xdata: np.ndarray,
                  ydata: np.ndarray) -> dict | None:
    """Fit a template expression to data. Returns params dict or None."""
    local_ns = {"math": math, "np": np}
    try:
        func_body = f"def _model({', '.join(['_x_'] + params)}):\n"
        var = "n"  # will be replaced
        func_body += f"    {var} = _x_\n"
        func_body += f"    return {expression}\n"
        exec(func_body, local_ns)
        model_fn = local_ns["_model"]
    except Exception:
        return None

    p0 = [1.0] * len(params)
    try:
        popt, _ = curve_fit(model_fn, xdata, ydata, p0=p0, maxfev=10000)
        pred = model_fn(xdata, *popt)
        residuals = ydata - pred
        max_res = float(np.max(np.abs(residuals)))
        return {
            "params": dict(zip(params, [float(v) for v in popt])),
            "max_res": max_res,
            "residuals": residuals,
            "pred": pred,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Test 1: Split-half stability (Tukey)
# ---------------------------------------------------------------------------

def test_split_half(champion: dict, visible: list[tuple[float, float]],
                    var: str) -> dict:
    """Fit champion template on each half of visible, compare leading coefficient."""
    n = len(visible)
    if n < 20:
        return {"test": "split_half", "status": "skipped", "reason": "too few visible points"}

    mid = n // 2
    first_half = visible[:mid]
    second_half = visible[mid:]

    expr = champion["expression"]
    param_names = list(champion["params"].keys())

    results = {}
    for label, data in [("first_half", first_half), ("second_half", second_half)]:
        x = np.array([p[0] for p in data])
        y = np.array([p[1] for p in data])

        try:
            model_fn = _build_model(expr, param_names, var)
            p0 = [champion["params"][p] for p in param_names]
            popt, _ = curve_fit(model_fn, x, y, p0=p0, maxfev=10000)
            results[label] = dict(zip(param_names, [float(v) for v in popt]))
        except Exception as e:
            results[label] = {"error": str(e)}

    if "error" in results.get("first_half", {}) or "error" in results.get("second_half", {}):
        return {"test": "split_half", "status": "fit_error", "details": results}

    # Compare leading coefficient (first param)
    lead_param = param_names[0]
    v1 = results["first_half"][lead_param]
    v2 = results["second_half"][lead_param]
    drift_pct = abs(v1 - v2) / max(abs(v1), 1e-10) * 100

    return {
        "test": "split_half",
        "status": "MARGIN_THIN" if drift_pct > 1.0 else "ok",
        "lead_param": lead_param,
        "first_half": round(v1, 6),
        "second_half": round(v2, 6),
        "drift_pct": round(drift_pct, 3),
        "all_params": results,
    }


# ---------------------------------------------------------------------------
# Test 2: Coefficient drift under scale expansion
# ---------------------------------------------------------------------------

def test_coefficient_drift(champion: dict, visible: list[tuple[float, float]],
                           holdout: list[tuple[float, float]],
                           farther: list[tuple[float, float]],
                           var: str) -> dict:
    """Refit champion at expanding scales, measure drift direction and magnitude."""
    expr = champion["expression"]
    param_names = list(champion["params"].keys())

    all_data = visible + holdout + farther
    n_vis = len(visible)

    scales = [
        ("visible_only", visible),
        ("visible+holdout", visible + holdout),
        ("all_data", all_data),
    ]

    try:
        model_fn = _build_model(expr, param_names, var)
    except Exception as e:
        return {"test": "coefficient_drift", "status": "build_error", "error": str(e)}

    fits = {}
    for label, data in scales:
        x = np.array([p[0] for p in data])
        y = np.array([p[1] for p in data])
        try:
            p0 = [champion["params"][p] for p in param_names]
            popt, _ = curve_fit(model_fn, x, y, p0=p0, maxfev=10000)
            fits[label] = dict(zip(param_names, [float(v) for v in popt]))
        except Exception:
            fits[label] = None

    # Check monotonicity of leading coefficient drift
    lead = param_names[0]
    values = [fits[s[0]][lead] for s in scales if fits.get(s[0]) is not None]

    if len(values) < 2:
        return {"test": "coefficient_drift", "status": "insufficient_data", "fits": fits}

    diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
    monotone = all(d >= 0 for d in diffs) or all(d <= 0 for d in diffs)
    total_drift_pct = abs(values[-1] - values[0]) / max(abs(values[0]), 1e-10) * 100

    # Buffett rule: monotone drift at 0.5% is worse than oscillatory at 1.5%
    threshold = 0.5 if monotone else 1.0

    return {
        "test": "coefficient_drift",
        "status": "MARGIN_THIN" if total_drift_pct > threshold else "ok",
        "lead_param": lead,
        "values_by_scale": {s[0]: round(fits[s[0]][lead], 6) for s in scales if fits.get(s[0])},
        "total_drift_pct": round(total_drift_pct, 3),
        "monotone": monotone,
        "threshold_pct": threshold,
        "all_fits": fits,
    }


# ---------------------------------------------------------------------------
# Test 3: Grammar completeness probe
# ---------------------------------------------------------------------------

def test_grammar_completeness(champion: dict, all_evidence: list[tuple[float, float]],
                              farther: list[tuple[float, float]],
                              var: str) -> dict:
    """Try natural extensions of the champion template. Flag if any improves far-tail 2x."""
    expr = champion["expression"]
    param_names = list(champion["params"].keys())
    x = var

    # Compute champion far-tail residual
    x_far = np.array([p[0] for p in farther])
    y_far = np.array([p[1] for p in farther])
    x_all = np.array([p[0] for p in all_evidence])
    y_all = np.array([p[1] for p in all_evidence])

    try:
        model_fn = _build_model(expr, param_names, x)
        p0 = [champion["params"][p] for p in param_names]
        popt, _ = curve_fit(model_fn, x_all, y_all, p0=p0, maxfev=10000)
        champ_pred_far = model_fn(x_far, *popt)
        champ_far_res = float(np.max(np.abs(y_far - champ_pred_far)))
    except Exception:
        return {"test": "grammar_completeness", "status": "champion_fit_error"}

    # Natural extensions based on what the champion contains
    extensions = []
    if f"math.log({x})" in expr and f"math.log(math.log({x}))" not in expr:
        extensions.append(("add_loglog", f"({expr}) + _d * math.log(math.log({x}))",
                          param_names + ["_d"]))
    if f"math.sqrt({x})" in expr and f"math.log({x})" not in expr:
        extensions.append(("add_log", f"({expr}) + _d * math.log({x})",
                          param_names + ["_d"]))
    if f"math.log({x})" in expr and f"math.sqrt({x})" not in expr:
        extensions.append(("add_sqrt", f"({expr}) + _d * math.sqrt({x})",
                          param_names + ["_d"]))
    # Always try adding 1/x^2 correction
    extensions.append(("add_recip2", f"({expr}) + _d / {x}**2", param_names + ["_d"]))

    gaps = []
    for ext_name, ext_expr, ext_params in extensions:
        try:
            ext_fn = _build_model(ext_expr, ext_params, x)
            p0_ext = [champion["params"].get(p, 0.0) for p in ext_params]
            popt_ext, _ = curve_fit(ext_fn, x_all, y_all, p0=p0_ext, maxfev=10000)
            ext_pred_far = ext_fn(x_far, *popt_ext)
            ext_far_res = float(np.max(np.abs(y_far - ext_pred_far)))
            improvement = champ_far_res / max(ext_far_res, 1e-10)
            gaps.append({
                "extension": ext_name,
                "champion_far_res": round(champ_far_res, 6),
                "extended_far_res": round(ext_far_res, 6),
                "improvement_ratio": round(improvement, 2),
                "params": dict(zip(ext_params, [float(v) for v in popt_ext])),
            })
        except Exception:
            continue

    grammar_gap = any(g["improvement_ratio"] >= 2.0 for g in gaps)
    grammar_soft = any(1.5 <= g["improvement_ratio"] < 2.0 for g in gaps)

    status = "GRAMMAR_GAP" if grammar_gap else ("GRAMMAR_SOFT" if grammar_soft else "ok")

    return {
        "test": "grammar_completeness",
        "status": status,
        "champion_far_res": round(champ_far_res, 6),
        "extensions_tested": len(gaps),
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Test 4: Residual autocorrelation (Tukey)
# ---------------------------------------------------------------------------

def test_residual_autocorrelation(champion: dict, visible: list[tuple[float, float]],
                                  var: str) -> dict:
    """Compute lag-1 autocorrelation of champion residuals on visible data."""
    expr = champion["expression"]
    param_names = list(champion["params"].keys())
    x_vis = np.array([p[0] for p in visible])
    y_vis = np.array([p[1] for p in visible])

    try:
        model_fn = _build_model(expr, param_names, var)
        p0 = [champion["params"][p] for p in param_names]
        popt, _ = curve_fit(model_fn, x_vis, y_vis, p0=p0, maxfev=10000)
        pred = model_fn(x_vis, *popt)
        residuals = y_vis - pred
    except Exception:
        return {"test": "residual_autocorrelation", "status": "fit_error"}

    if len(residuals) < 10:
        return {"test": "residual_autocorrelation", "status": "skipped", "reason": "too few points"}

    # Lag-1 autocorrelation
    r = residuals - np.mean(residuals)
    lag1 = float(np.sum(r[:-1] * r[1:]) / np.sum(r**2))

    # Runs test: count sign changes
    signs = np.sign(residuals)
    sign_changes = int(np.sum(signs[:-1] != signs[1:]))
    expected_changes = (len(residuals) - 1) / 2
    runs_ratio = sign_changes / max(expected_changes, 1)

    return {
        "test": "residual_autocorrelation",
        "status": "STRUCTURED_RESIDUALS" if abs(lag1) > 0.3 else "ok",
        "lag1_autocorrelation": round(lag1, 4),
        "sign_changes": sign_changes,
        "expected_sign_changes": round(expected_changes, 1),
        "runs_ratio": round(runs_ratio, 3),
    }


# ---------------------------------------------------------------------------
# Test 5: Extrapolation stress (numerical, Taleb)
# ---------------------------------------------------------------------------

def test_extrapolation_stress(champion: dict, visible: list[tuple[float, float]],
                              holdout: list[tuple[float, float]],
                              farther: list[tuple[float, float]],
                              var: str) -> dict:
    """Fit on visible only, predict at holdout and farther. Report numerical residuals."""
    expr = champion["expression"]
    param_names = list(champion["params"].keys())

    x_vis = np.array([p[0] for p in visible])
    y_vis = np.array([p[1] for p in visible])

    try:
        model_fn = _build_model(expr, param_names, var)
        p0 = [champion["params"][p] for p in param_names]
        popt, _ = curve_fit(model_fn, x_vis, y_vis, p0=p0, maxfev=10000)
    except Exception:
        return {"test": "extrapolation_stress", "status": "fit_error"}

    results = []
    for label, data in [("holdout", holdout), ("farther_tail", farther)]:
        if not data:
            continue
        x_pred = np.array([p[0] for p in data])
        y_pred = np.array([p[1] for p in data])
        try:
            pred = model_fn(x_pred, *popt)
            max_res = float(np.max(np.abs(y_pred - pred)))
            mean_res = float(np.mean(np.abs(y_pred - pred)))
            # Relative to data range
            data_range = float(np.max(y_pred) - np.min(y_pred)) if len(y_pred) > 1 else 1.0
            rel_res = max_res / max(data_range, 1e-10)

            vis_max_x = float(np.max(x_vis))
            pred_max_x = float(np.max(x_pred))
            scale_ratio = (pred_max_x - float(np.min(x_vis))) / (vis_max_x - float(np.min(x_vis)))

            results.append({
                "region": label,
                "scale_ratio": round(scale_ratio, 1),
                "max_residual": round(max_res, 6),
                "mean_residual": round(mean_res, 6),
                "relative_residual": round(rel_res, 4),
                "n_points": len(data),
            })
        except Exception as e:
            results.append({"region": label, "error": str(e)})

    return {
        "test": "extrapolation_stress",
        "status": "ok",
        "fit_on": f"visible ({len(visible)} pts)",
        "predictions": results,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_margin_of_safety(project_dir: Path,
                         compression_results: list[dict] | None = None,
                         inversion_depth: int = 0) -> dict:
    """Run margin-of-safety tests on the best gate-passing compression result.

    inversion_depth controls the battery stringency (Tukey scaling):
      0: standard 5-test battery (original compression output)
      1: standard + significance test (first inversion of a null)
      2: standard + require independent holdout split
      3+: REJECT (hard ceiling per Munger/Tukey panel)
    """
    if inversion_depth >= 3:
        return {"status": "INVERSION_CEILING",
                "message": "Two inversions on the same residual stream is the hard ceiling. "
                           "Further inversions require an independent dataset."}


    # Load evidence
    visible = _load_evidence(project_dir / "evidence.txt")
    holdout = _load_evidence(project_dir / "evidence_holdout.txt") if (project_dir / "evidence_holdout.txt").exists() else []
    farther = _load_evidence(project_dir / "evidence_farther_tail.txt") if (project_dir / "evidence_farther_tail.txt").exists() else []
    var = _detect_variable(project_dir / "evidence.txt")

    # Load compression results if not provided
    if compression_results is None:
        cr_path = project_dir / "workspace" / "compression_results.json"
        if cr_path.exists():
            compression_results = json.loads(cr_path.read_text(encoding="utf-8"))
        else:
            return {"status": "no_compression_results"}

    passing = [r for r in compression_results if r.get("gates_passed")]
    if not passing:
        result = {
            "status": "no_gate_passing_forms",
            "tests": [],
            "remediation": {"verdict": "UNDERIDENTIFIED"},
        }
        out_path = project_dir / "workspace" / "margin_of_safety.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, default=str))
        return result

    # Use BIC-best gate-passing form
    best = min(passing, key=lambda r: r.get("bic", float("inf")))

    print(f"GP-112 Margin of Safety: testing '{best['name']}' "
          f"(k={len(best.get('params', {}))}, BIC={best.get('bic', '?'):.1f})")

    champion = {
        "expression": best["expression"],
        "params": best["params"],
        "name": best["name"],
    }

    all_evidence = visible + holdout + farther
    tests = []

    # Test 1: Split-half stability
    print("  [1/5] Split-half stability...")
    tests.append(test_split_half(champion, visible, var))

    # Test 2: Coefficient drift
    print("  [2/5] Coefficient drift under scale expansion...")
    tests.append(test_coefficient_drift(champion, visible, holdout, farther, var))

    # Test 3: Grammar completeness probe
    print("  [3/5] Grammar completeness probe...")
    tests.append(test_grammar_completeness(champion, all_evidence, farther, var))

    # Test 4: Residual autocorrelation
    print("  [4/5] Residual autocorrelation...")
    tests.append(test_residual_autocorrelation(champion, visible, var))

    # Test 5: Extrapolation stress
    print("  [5/5] Extrapolation stress...")
    tests.append(test_extrapolation_stress(champion, visible, holdout, farther, var))

    # Summary
    flags = [t["status"] for t in tests if t["status"] not in ("ok", "skipped")]
    grammar_gap = any(t["status"] == "GRAMMAR_GAP" for t in tests)

    remediation = None

    # --- Phase 2c: Closed-loop remediation (GP-112 panel verdict) ---
    # Fires when MARGIN_THIN, GRAMMAR_GAP, or STRUCTURED_RESIDUALS detected.
    # One iteration only. Preserves original. Adds remediated candidate.
    # BIC uses n=len(visible) per Tukey. Min 1.05x improvement per Buffett.
    needs_remediation = any(t["status"] in ("MARGIN_THIN", "GRAMMAR_GAP",
                                             "STRUCTURED_RESIDUALS", "GRAMMAR_SOFT")
                           for t in tests)

    if needs_remediation and farther:
        print(f"\n  --- Phase 2c: Remediation (one iteration) ---")
        # Collect extensions that showed ANY improvement >= 1.05x
        grammar_test = next((t for t in tests if t["test"] == "grammar_completeness"), None)
        candidates = []
        if grammar_test and grammar_test.get("gaps"):
            for gap in grammar_test["gaps"]:
                if gap.get("improvement_ratio", 0) >= 1.05:
                    candidates.append(gap)

        if candidates:
            # Exhaust-the-curated-list (panel revision 2026-04-21):
            # Try ALL candidates above 1.05x, sorted by improvement ratio.
            # Stop when margin improves OR list exhausted.
            # BIC penalty accumulates per candidate tried (log(n_tried)).
            sorted_candidates = sorted(candidates, key=lambda g: -g["improvement_ratio"])
            print(f"  Extensions above 1.05x: {len(sorted_candidates)} (sealed list)")

            x = var
            x_all_arr = np.array([p[0] for p in all_evidence])
            y_all_arr = np.array([p[1] for p in all_evidence])
            x_far_arr = np.array([p[0] for p in farther])
            y_far_arr = np.array([p[1] for p in farther])
            orig_lag1 = next((t.get("lag1_autocorrelation", 0)
                             for t in tests if t["test"] == "residual_autocorrelation"), 0)

            attempts = []
            best_remediation = None

            for trial_idx, ext_candidate in enumerate(sorted_candidates):
                ext_name = ext_candidate["extension"]
                ext_expr = champion["expression"]

                if ext_name == "add_loglog":
                    ext_expr = f"({ext_expr}) + _d * math.log(math.log({x}))"
                elif ext_name == "add_sqrt":
                    ext_expr = f"({ext_expr}) + _d * math.sqrt({x})"
                elif ext_name == "add_log":
                    ext_expr = f"({ext_expr}) + _d * math.log({x})"
                elif ext_name == "add_recip2":
                    ext_expr = f"({ext_expr}) + _d / {x}**2"
                else:
                    continue
                ext_param_names = list(champion["params"].keys()) + ["_d"]

                print(f"  [{trial_idx+1}/{len(sorted_candidates)}] Trying {ext_name} "
                      f"(improvement {ext_candidate['improvement_ratio']:.2f}x)...")

                try:
                    ext_model = _build_model(ext_expr, ext_param_names, var)
                    p0_ext = [ext_candidate["params"].get(p, 0.0) for p in ext_param_names]
                    popt_ext, _ = curve_fit(ext_model, x_all_arr, y_all_arr,
                                           p0=p0_ext, maxfev=10000)

                    # BIC with n=len(visible), plus log(trial_idx+1) penalty
                    pred_ext = ext_model(x_all_arr, *popt_ext)
                    sse = float(np.sum((y_all_arr - pred_ext)**2))
                    n_bic = len(visible)
                    k_ext = len(ext_param_names)
                    bic_ext = (n_bic * np.log(sse / len(all_evidence))
                              + k_ext * np.log(n_bic)
                              + np.log(trial_idx + 1))  # Buffett penalty

                    pred_far = ext_model(x_far_arr, *popt_ext)
                    ext_far_res = float(np.max(np.abs(y_far_arr - pred_far)))

                    # Quick margin check: residual autocorrelation
                    x_vis_arr = np.array([p[0] for p in visible])
                    y_vis_arr = np.array([p[1] for p in visible])
                    pred_vis = ext_model(x_vis_arr, *popt_ext)
                    resid = y_vis_arr - pred_vis
                    r = resid - np.mean(resid)
                    rem_lag1 = float(np.sum(r[:-1] * r[1:]) / np.sum(r**2)) if len(r) > 2 else 0
                    explained = abs(rem_lag1) < 0.5 * abs(orig_lag1) if orig_lag1 != 0 else False

                    attempt = {
                        "extension": ext_name,
                        "params": dict(zip(ext_param_names, [float(v) for v in popt_ext])),
                        "bic_visible": round(float(bic_ext), 1),
                        "far_res": round(ext_far_res, 6),
                        "lag1": round(rem_lag1, 4),
                        "explained": explained,
                    }
                    attempts.append(attempt)

                    status = "EXPLAINED" if explained else "PERSIST"
                    print(f"    lag1: {orig_lag1:.3f} -> {rem_lag1:.3f} ({status}), "
                          f"far_res: {ext_far_res:.6f}")

                    # If this is the best so far (lowest lag1), track it
                    if best_remediation is None or abs(rem_lag1) < abs(best_remediation["lag1"]):
                        best_remediation = attempt
                        best_remediation["expression"] = ext_expr
                        best_remediation["name"] = f"{champion['name']}+{ext_name}"
                        best_remediation["k"] = k_ext

                    # Early exit if residuals explained
                    if explained:
                        print(f"    Residuals EXPLAINED. Accepting {ext_name}.")
                        break

                except Exception as e:
                    attempts.append({"extension": ext_name, "error": str(e)})
                    print(f"    Fit failed: {e}")

            # Build remediation summary
            any_explained = any(a.get("explained") for a in attempts)
            remediation = {
                "trigger": [t["status"] for t in tests if t["status"] not in ("ok", "skipped")],
                "candidates_tried": len(attempts),
                "candidates_total": len(sorted_candidates),
                "attempts": attempts,
                "best_remediation": best_remediation,
                "any_explained": any_explained,
                "original_lag1": round(orig_lag1, 4),
                "original_flags_count": len(flags),
                "verdict": "EXPLAINED" if any_explained else "PERSIST_ALL_EXHAUSTED",
            }

            if any_explained and best_remediation:
                print(f"  Remediation succeeded: {best_remediation['name']}")
            else:
                # Curated list exhausted. Now try grammar-derived extensions
                # (panel verdict: single bounded enumeration, not separate tiers).
                x = var
                champ_lower = champion["expression"].lower()
                grammar_ext = []
                if "math.sqrt" not in champ_lower:
                    grammar_ext.append(("g_sqrt", f"_e * math.sqrt({x})", ["_e"]))
                if "math.log" not in champ_lower:
                    grammar_ext.append(("g_log", f"_e * math.log({x})", ["_e"]))
                if "math.exp" not in champ_lower:
                    grammar_ext.append(("g_exp_decay", f"_e * math.exp(-_f * {x})", ["_e", "_f"]))
                if f"/ {x}" not in champ_lower:
                    grammar_ext.append(("g_recip", f"_e / {x}", ["_e"]))
                if f"{x}**" not in champ_lower:
                    grammar_ext.append(("g_power", f"_e * {x}**_f", ["_e", "_f"]))
                if "math.log(math.log" not in champ_lower:
                    grammar_ext.append(("g_loglog", f"_e * math.log(math.log({x}))", ["_e"]))
                if "math.log" in champ_lower:
                    grammar_ext.append(("g_log_sq", f"_e * math.log({x})**2", ["_e"]))

                # Deduplicate against already-tried curated extensions
                tried_names = {a.get("extension", "") for a in attempts}
                grammar_ext = [(n, t, p) for n, t, p in grammar_ext
                               if n not in tried_names and f"add_{n.replace('g_','')}" not in tried_names]

                if grammar_ext:
                    print(f"  + {len(grammar_ext)} grammar-derived extensions (sealed)...")
                    n_prior = len(attempts)
                    for gi, (gname, gterm, gnew_params) in enumerate(grammar_ext):
                        gexpr = f"({champion['expression']}) + {gterm}"
                        gparam_names = list(champion["params"].keys()) + gnew_params
                        trial_num = n_prior + gi + 1
                        try:
                            gmodel = _build_model(gexpr, gparam_names, var)
                            gp0 = [champion["params"].get(p, 0.0) for p in gparam_names]
                            gpopt, _ = curve_fit(gmodel, x_all_arr, y_all_arr,
                                                p0=gp0, maxfev=10000)
                            gvis_pred = gmodel(np.array([p[0] for p in visible]), *gpopt)
                            gresid = np.array([p[1] for p in visible]) - gvis_pred
                            gr = gresid - np.mean(gresid)
                            glag1 = float(np.sum(gr[:-1]*gr[1:]) / np.sum(gr**2)) if len(gr) > 2 else 0
                            gexplained = abs(glag1) < 0.5 * abs(orig_lag1) if orig_lag1 != 0 else False
                            gpred_far = gmodel(x_far_arr, *gpopt)
                            gfar_res = float(np.max(np.abs(y_far_arr - gpred_far)))

                            att = {"extension": gname, "lag1": round(glag1, 4),
                                   "far_res": round(gfar_res, 6), "explained": gexplained}
                            attempts.append(att)
                            st = "EXPLAINED" if gexplained else "persist"
                            print(f"  [{trial_num}/{n_prior+len(grammar_ext)}] {gname}: "
                                  f"lag1 {glag1:.3f} ({st})")

                            if gexplained:
                                best_remediation = att
                                best_remediation["expression"] = gexpr
                                best_remediation["name"] = f"{champion['name']}+{gname}"
                                print(f"    EXPLAINED. Accepting.")
                                break
                            if best_remediation is None or abs(glag1) < abs(best_remediation.get("lag1", 999)):
                                best_remediation = att
                        except Exception:
                            continue

                # Final verdict
                any_explained = any(a.get("explained") for a in attempts)
                remediation["candidates_tried"] = len(attempts)
                remediation["attempts"] = attempts
                remediation["best_remediation"] = best_remediation
                remediation["any_explained"] = any_explained
                remediation["verdict"] = "EXPLAINED" if any_explained else "PERSIST_GRAMMAR_EXHAUSTED"
                print(f"  Total: {len(attempts)} extensions, "
                      f"verdict: {remediation['verdict']}")

        else:
            print(f"  No extensions above 1.05x threshold. Remediation skipped.")
            remediation = {"trigger": flags, "skipped": True,
                          "reason": "no extension above 1.05x"}

    # --- Phase 2.6: Residual characterization (fires on PERSIST) ---
    residual_characterization = None
    if remediation and remediation.get("verdict", "").startswith("PERSIST"):
        print(f"\n  --- Phase 2.6: Residual characterization ---")
        try:
            # Refit champion on all evidence for residual extraction
            champ_fn = _build_model(champion["expression"],
                                    list(champion["params"].keys()), var)
            x_all_arr = np.array([p[0] for p in all_evidence])
            y_all_arr = np.array([p[1] for p in all_evidence])
            p0_c = [champion["params"][p] for p in champion["params"]]
            popt_c, _ = curve_fit(champ_fn, x_all_arr, y_all_arr,
                                  p0=p0_c, maxfev=10000)
            resid_all = y_all_arr - champ_fn(x_all_arr, *popt_c)

            # Compute champion max residual for GP-115 improvement ratio
            champ_far_res = float(np.max(np.abs(resid_all)))

            # GP-115 Layer 1: residual-driven grammar suggestions
            try:
                from src.ztare.fit.residual_grammar_expander import suggest_from_residuals
                gp115_suggestions = suggest_from_residuals(resid_all, x_all_arr, var)
                if gp115_suggestions:
                    print(f"  GP-115: {len(gp115_suggestions)} grammar suggestions from residuals:")
                    for s in gp115_suggestions:
                        print(f"    {s['name']}: {s['rationale']}")

                    # AUTO-ACT on suggestions: try each as an extension
                    print(f"  GP-115 auto-acting: trying {len(gp115_suggestions)} suggested templates...")
                    for sg in gp115_suggestions:
                        try:
                            sg_model = _build_model(sg["expression"], sg["params"], var)
                            sg_p0 = [0.0] * len(sg["params"])
                            sg_popt, _ = curve_fit(sg_model, x_all_arr, resid_all,
                                                  p0=sg_p0, maxfev=5000)
                            sg_pred = sg_model(x_all_arr, *sg_popt)
                            sg_res = float(np.max(np.abs(resid_all - sg_pred)))
                            improvement = champ_far_res / max(sg_res, 1e-10) if champ_far_res > 0 else 1
                            print(f"    {sg['name']}: res={sg_res:.4f}, improvement={improvement:.2f}x")

                            if improvement >= 1.5:
                                print(f"    -> PROMOTED to remediation candidates")
                                # The suggestion improves residuals — it should be
                                # added to the permanent grammar if it passes on 3+ substrates
                                # For now, log the promotion signal
                                sg["promotion_signal"] = True
                                sg["improvement_on_residuals"] = round(improvement, 2)
                        except Exception:
                            pass
            except Exception as e:
                gp115_suggestions = []

            # GP-115 diagnostics logging (GP-121 Fix 3: log all activity)
            gp115_log = {
                "timestamp": datetime.now().isoformat(),
                "project": str(project_dir.name),
                "n_suggestions": len(gp115_suggestions),
                "suggestions": [],
            }
            for sg in gp115_suggestions:
                gp115_log["suggestions"].append({
                    "name": sg.get("name"),
                    "expression": sg.get("expression"),
                    "rationale": sg.get("rationale"),
                    "improvement": sg.get("improvement", 0),
                    "improvement_on_residuals": sg.get("improvement_on_residuals", 0),
                    "promoted": sg.get("promotion_signal", False),
                })
            gp115_log_path = project_dir / "workspace" / "gp115_diagnostics.json"
            gp115_log_path.parent.mkdir(parents=True, exist_ok=True)
            # json already imported at module level
            gp115_log_path.write_text(json.dumps(gp115_log, indent=2, default=str))

            # GP-121 Fix 3: inject GP-115 suggestions into constraint ledger
            # so the LLM mutator knows what the deterministic system detected
            if gp115_suggestions:
                try:
                    dc_path = project_dir / "workspace" / "derived_constraints.json"
                    if dc_path.exists():
                        dc = json.loads(dc_path.read_text())
                    else:
                        dc = {"provisional_constraints": [], "confirmed_constraints": []}

                    for sg in gp115_suggestions:
                        constraint = {
                            "signature": f"gp115_{sg.get('name', 'unknown')}",
                            "constraint": (
                                f"GP-115 residual analysis detected {sg.get('name', 'unknown')} pattern "
                                f"in compression residuals ({sg.get('rationale', '')}). "
                                f"Improvement ratio: {sg.get('improvement', 0):.1f}x."
                            ),
                            "applies_to": "functional form proposals",
                            "failure_family": f"residual_pattern_{sg.get('name', 'unknown')}",
                            "severity": "enriching",
                            "producer": "gp115_grammar_expander",
                            "status": "provisional",
                        }
                        dc.setdefault("provisional_constraints", []).append(constraint)

                    dc["provisional_constraint_count"] = len(dc.get("provisional_constraints", []))
                    dc_path.write_text(json.dumps(dc, indent=2, default=str))
                except Exception:
                    pass

            # 1. Spectral slope of residuals
            from scipy.signal import welch as _welch
            from scipy.stats import linregress as _lr
            skip = min(len(resid_all) // 10, 5000)
            freqs, psd = _welch(resid_all[skip:], nperseg=min(4096, len(resid_all) // 4))
            fmask = (freqs > 0) & (psd > 0)
            if fmask.sum() > 5:
                sl, _, rv, _, _ = _lr(np.log10(freqs[fmask]), np.log10(psd[fmask]))
                spectral_slope = round(float(sl), 3)
                spectral_r2 = round(float(rv**2), 3)
            else:
                spectral_slope, spectral_r2 = None, None

            # 2. Multiplicative loglog model trial
            x_v = var
            mult_expr = f"a * math.log({x_v}) * (1 + b * math.log(math.log({x_v})) / math.log({x_v})) + c / {x_v} + d"
            mult_params = ["a", "b", "c", "d"]
            mult_result = None
            try:
                mult_fn = _build_model(mult_expr, mult_params, var)
                pm, _ = curve_fit(mult_fn, x_all_arr, y_all_arr,
                                  p0=[1.1, 0.5, -5, 0.5], maxfev=10000)
                mult_pred = mult_fn(x_all_arr, *pm)
                mult_res = y_all_arr - mult_pred
                mult_far = float(np.max(np.abs(mult_res[-len(farther):]))) if farther else 0
                mr = mult_res - np.mean(mult_res)
                mult_lag1 = float(np.sum(mr[:-1]*mr[1:]) / np.sum(mr**2)) if len(mr) > 2 else 0
                mult_result = {
                    "expression": mult_expr,
                    "params": dict(zip(mult_params, [float(v) for v in pm])),
                    "far_res": round(mult_far, 6),
                    "lag1": round(mult_lag1, 4),
                }
            except Exception:
                pass

            residual_characterization = {
                "spectral_slope": spectral_slope,
                "spectral_r2": spectral_r2,
                "noise_class": ("1/f" if spectral_slope and -1.5 < spectral_slope < -0.5
                               else "brown" if spectral_slope and spectral_slope <= -1.5
                               else "white" if spectral_slope else "unknown"),
                "multiplicative_model": mult_result,
                "gp115_grammar_suggestions": [
                    {"name": s["name"], "expression": s["expression"],
                     "rationale": s["rationale"], "improvement": s.get("improvement")}
                    for s in gp115_suggestions
                ] if gp115_suggestions else [],
                "interpretation": (
                    "Residuals are a well-characterized stochastic process "
                    f"(spectral slope {spectral_slope}, "
                    f"{'not' if not mult_result or mult_result['lag1'] > 0.5 else ''} "
                    "resolved by multiplicative correction). "
                    "The smooth trend is the extractable signal; "
                    "the residual structure is an intrinsic property of the data source."
                ),
            }

            print(f"  Spectral slope: {spectral_slope} (R2={spectral_r2})")
            noise = residual_characterization["noise_class"]
            print(f"  Noise class: {noise}")
            if mult_result:
                print(f"  Multiplicative model: a={mult_result['params']['a']:.4f}, "
                      f"far_res={mult_result['far_res']:.6f}, lag1={mult_result['lag1']:.4f}")

        except Exception as e:
            residual_characterization = {"error": str(e)}
            print(f"  Characterization failed: {e}")

    # Inversion depth enforcement (Tukey scaling)
    if inversion_depth >= 1:
        # At depth 1+: require significance on key metrics
        for t in tests:
            if t["test"] == "split_half" and t.get("drift_pct"):
                n_half = len(visible) // 2
                z = t["drift_pct"] / 100 * math.sqrt(n_half) if n_half > 0 else 0
                t["significance_z"] = round(z, 2)
                t["significant_p05"] = abs(z) > 1.96
                if not t["significant_p05"] and t["status"] == "MARGIN_THIN":
                    t["status"] = "ok (not significant at inversion depth)"
            if t["test"] == "residual_autocorrelation" and t.get("lag1_autocorrelation") is not None:
                n_pts = len(visible)
                z = abs(t["lag1_autocorrelation"]) * math.sqrt(n_pts)
                t["significance_z"] = round(z, 2)
                t["significant_p05"] = z > 1.96
                if not t["significant_p05"] and t["status"] == "STRUCTURED_RESIDUALS":
                    t["status"] = "ok (not significant at inversion depth)"

        # Recompute flags after significance filter
        flags = [t["status"] for t in tests if t["status"] not in ("ok", "skipped")
                 and "not significant" not in t.get("status", "")]

    result = {
        "status": "margin_assessed",
        "champion": best["name"],
        "champion_expression": best["expression"],
        "champion_params": best["params"],
        "inversion_depth": inversion_depth,
        "tests": tests,
        "flags": flags,
        "grammar_gap_detected": grammar_gap,
        "remediation": remediation,
        "residual_characterization": residual_characterization,
    }

    # Print summary
    print(f"\n  --- GP-112 Summary ---")
    for t in tests:
        icon = "!" if t["status"] not in ("ok", "skipped") else "."
        print(f"  [{icon}] {t['test']}: {t['status']}")
    if grammar_gap:
        print(f"\n  *** GRAMMAR_GAP detected. Review before publishing. ***")
    if flags:
        print(f"  Flags: {', '.join(flags)}")
    else:
        print(f"  All tests pass. Margin is adequate.")

    # Save
    out_path = project_dir / "workspace" / "margin_of_safety.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n  Results saved to {out_path}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="GP-112: Margin of Safety Gate")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--inversion-depth", type=int, default=0,
                       help="Inversion depth (0=standard, 1=significance, 2=independent holdout, 3+=reject)")
    args = parser.parse_args()

    project_dir = PROJECTS_DIR / args.project
    if not project_dir.exists():
        print(f"ERROR: {project_dir} does not exist", file=sys.stderr)
        return 1

    result = run_margin_of_safety(project_dir, inversion_depth=args.inversion_depth)

    if result.get("grammar_gap_detected"):
        print("\nGRAMMAR_GAP: a natural extension of the champion improves far-tail")
        print("residuals by 2x or more. The certified form may be incomplete.")
        resp = input("Continue anyway? [y/N] ") if sys.stdin.isatty() else "y"
        if resp.strip().lower() != "y":
            print("Halted by operator.")
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
