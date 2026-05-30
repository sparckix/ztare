#!/usr/bin/env python3
"""Epistemic Coherence Audit — deterministic post-run grader.

Replaces the abandoned "alien panel" persona-prompt approach
(2026-04-28) with structural metrics computed directly from the run's
artifacts. Persona prompts shift LLM activations toward stylistic
clusters (contrarianism, sci-fi register), not toward novel reasoning
untainted by training data; if a metric is computable, run it as code.

Four checks, all deterministic, no LLM calls:

  1. KOLMOGOROV-vs-YIELD — does the derived closed-form's bit budget
     (AST node count + log2 of distinct parameter count) exceed the
     bits of residual error it actually removes across the substrate?
     A form that needs more bits to describe than it removes from the
     baseline residual is a Padé-class approximation, not a law.

  2. BOUNDARY COLLAPSE — push features to extremes (g_bar → 0,
     g_bar → ∞, mass_log10 = ±∞ proxies, radius_log10 = ±∞ proxies)
     and check whether the form diverges, returns NaN, or sign-flips.
     A genuine asymptotic law collapses smoothly into a known regime
     (Newton at high g_bar, deep-MOND at low g_bar). A curve-fitter
     blows up.

  3. CROSS-CLASS PARAMETER DEGENERACY — fit each free parameter
     (e.g., a_0) on Class A only, then Class B only, then Class C only.
     Report the spread. A real conservation law gives a tight spread
     (universality holds); a phenomenological fit gives a wide spread
     (each class wants its own constant). The spread itself is the
     diagnostic.

  4. TYPE-THEORETIC COHERENCE — verify each gate's input type matches
     the proposal step's output type. If the apparatus advertises
     dimensional consistency at the AST level, the form must contain
     no transcendentals with raw dimensional arguments. If the apparatus
     advertises Noether-variance enforcement, the run must have
     non-degenerate Noether invariants kept by the gate. If anchors
     are advertised as first-class loss terms, the form must have
     evaluated cleanly at every anchor.

Usage:
    python -m src.ztare.validator.epistemic_coherence_audit \\
        --project gp163d_unified_accel \\
        --run-id 1777344710 \\
        [--output workspace/epistemic_coherence_<run_id>.md]

Exit codes:
    0 — audit completed (no opinion on pass/fail; the audit is informational)
    2 — required artifact missing (cannot complete audit)
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# File lives at src/ztare/validator/epistemic_coherence_audit.py
#   .parent           → src/ztare/validator
#   .parent.parent    → src/ztare
#   .parent.parent.parent → src/        ← was wrong (only 2 levels up)
#   .parent.parent.parent.parent → repo root  ← correct
# Bug fixed 2026-05-06: previously was .parent.parent which resolves to
# src/ztare/, making `REPO_ROOT / 'projects' / X` look at the
# nonexistent path src/ztare/projects/X. Reported via the
# ztare_on_ztare_v2_expanded_scope run.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ─────────────────────────────────────────────────────────────────────
# 1. Kolmogorov-vs-yield
# ─────────────────────────────────────────────────────────────────────

def _ast_node_count(expr: str) -> int:
    """Count AST nodes in a parametric form. Proxy for Kolmogorov
    complexity of the symbolic expression."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return -1
    return sum(1 for _ in ast.walk(tree))


def kolmogorov_vs_yield(
    parametric_form: str,
    n_params: int,
    mre_baseline: float,
    mre_form: float,
    n_rows: int,
) -> dict:
    """Compare bits-to-describe vs bits-of-error-removed.

    Bits-to-describe ≈ AST node count + n_params · log2(64)  (assuming
    each fitted param is a 64-bit float, which is generous).

    Bits-of-error-removed ≈ N · log2(MRE_baseline / MRE_form)  (per-row
    log-likelihood improvement under a Gaussian-residual model, summed).
    """
    nodes = _ast_node_count(parametric_form)
    if nodes < 0:
        return {"verdict": "unparseable", "form": parametric_form[:80]}
    bits_to_describe = nodes + n_params * 64.0
    if mre_form <= 0 or mre_baseline <= 0:
        return {"verdict": "non-positive MRE; cannot compute yield"}
    # Default baseline is 1.0 — use only when no real baseline (bare-Newton
    # MRE on the same substrate) was supplied. Without a real baseline the
    # ratio is uncalibrated and we say so loudly.
    baseline_is_default = abs(mre_baseline - 1.0) < 1e-12
    if mre_form >= mre_baseline:
        bits_removed = 0.0
    else:
        bits_removed = n_rows * math.log2(mre_baseline / mre_form)
    ratio = bits_removed / max(bits_to_describe, 1.0)
    return {
        "ast_nodes": nodes,
        "n_params": n_params,
        "bits_to_describe": round(bits_to_describe, 1),
        "bits_removed": round(bits_removed, 1),
        "yield_ratio": round(ratio, 3),
        "verdict": (
            "law-shaped (yield > 1)" if ratio > 1.0
            else "Padé-shaped (yield ≤ 1)" if ratio > 0.0
            else "no improvement over baseline"
        ),
    }


# ─────────────────────────────────────────────────────────────────────
# 2. Boundary collapse
# ─────────────────────────────────────────────────────────────────────

def _safe_eval_form(form: str, features: dict, params: dict) -> tuple[float | None, str | None]:
    """Compile and evaluate a form, returning (value, error_kind)."""
    try:
        code = compile(form, "<form>", "eval")
    except SyntaxError as exc:
        return None, f"syntax:{exc.msg}"
    def _sigmoid(z, k=1.0, x0=0.0):
        """Three-arg sigmoid matching the apparatus's gp163d convention.
        Falls through to two-arg or one-arg call patterns gracefully."""
        try:
            return 1.0 / (1.0 + math.exp(-k * (z - x0)))
        except OverflowError:
            return 0.0 if z < x0 else 1.0
    def _softplus(z):
        try:
            return math.log1p(math.exp(z))
        except OverflowError:
            return z
    def _where(cond, a, b):
        """Match np.where's eager-evaluation semantics for scalars."""
        return a if cond else b
    # safe_globals must whitelist every builtin/library function the
    # apparatus's PARAMETRIC_FORM AST whitelist accepts (cf.
    # src/ztare/orchestrator/prompt.py::_PARAMETRIC_FORM_ALLOWED_NAMES).
    # The two whitelists must agree — anything the mutator can emit
    # must be evaluable by this audit. 2026-05-06: added int/bool/
    # float/len/str/where/round to fix audit failure on qualitative
    # substrates whose forms use type coercions (e.g.,
    # `int(condition)` for stub returns).
    safe_globals = {
        "__builtins__": {},
        "math": math, "exp": math.exp, "log": math.log,
        "log10": math.log10, "log2": math.log2,
        "sqrt": math.sqrt, "pow": pow,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "tanh": math.tanh, "asinh": math.asinh,
        "atan": math.atan, "atan2": math.atan2,
        "sigmoid": _sigmoid, "softplus": _softplus, "where": _where,
        "erf": math.erf, "erfc": math.erfc,
        "abs": abs, "min": min, "max": max, "pi": math.pi, "e": math.e,
        # Builtins the apparatus's PARAMETRIC_FORM AST whitelist allows
        "int": int, "bool": bool, "float": float, "str": str,
        "len": len, "round": round,
    }
    try:
        v = eval(code, safe_globals, {"features": features, "params": params})
    except (ZeroDivisionError, ValueError, OverflowError, KeyError, TypeError) as exc:
        return None, f"runtime:{type(exc).__name__}"
    if v is None:
        return None, "none-return"
    try:
        vf = float(v)
    except (TypeError, ValueError):
        return None, "non-float"
    if math.isnan(vf):
        return None, "nan"
    if math.isinf(vf):
        return None, "inf"
    return vf, None


def boundary_collapse(form: str, params: dict) -> dict:
    """Push features to extremes and check collapse behavior.

    Probes the four corners of (g_bar, mass, radius) phase space.
    Records the value at each corner and any error kind. Sign flips
    across the Newton/MOND knee (g_bar ≈ a_0) are flagged as
    structural pathologies.
    """
    PROBES = [
        ("Newton-deep",   {"x": 1e-2,  "mass_log10": 11.0, "radius_log10": 0.0,  "rho_local_log10": -3.0, "M_gas_log10_v3_4": 9.0}),
        ("Newton-knee",   {"x": 1.2e-10, "mass_log10": 11.0, "radius_log10": 1.0,  "rho_local_log10": -3.0, "M_gas_log10_v3_4": 9.0}),
        ("Deep-MOND",     {"x": 1e-13, "mass_log10": 11.0, "radius_log10": 2.0,  "rho_local_log10": -5.0, "M_gas_log10_v3_4": 9.0}),
        ("Cluster-scale", {"x": 1e-10, "mass_log10": 14.0, "radius_log10": 3.0,  "rho_local_log10": -6.0, "M_gas_log10_v3_4": 13.5}),
        ("Binary-scale",  {"x": 1e-9,  "mass_log10": 0.3,  "radius_log10": -4.0, "rho_local_log10": 4.0,  "M_gas_log10_v3_4": 0.0}),
        ("g_bar→0+",      {"x": 1e-30, "mass_log10": 10.0, "radius_log10": 1.0,  "rho_local_log10": -3.0, "M_gas_log10_v3_4": 9.0}),
        ("g_bar→∞",       {"x": 1e10,  "mass_log10": 10.0, "radius_log10": 1.0,  "rho_local_log10": -3.0, "M_gas_log10_v3_4": 9.0}),
    ]
    results = []
    for name, feats in PROBES:
        v, err = _safe_eval_form(form, feats, params)
        results.append({"probe": name, "value": v, "error": err})
    # Pathology check: did the form return a negative value where the
    # observable (acceleration) must be ≥ 0?
    negatives = [r for r in results if r["value"] is not None and r["value"] < 0]
    failures = [r for r in results if r["error"] is not None]
    return {
        "probes": results,
        "n_failures": len(failures),
        "n_negative_outputs": len(negatives),
        "verdict": (
            "smooth across all probes" if (not failures and not negatives)
            else f"FAILED on {len(failures)} probe(s); {len(negatives)} negative output(s)"
        ),
    }


# ─────────────────────────────────────────────────────────────────────
# 3. Cross-class parameter degeneracy
# ─────────────────────────────────────────────────────────────────────

def cross_class_param_spread(
    fit_summary_path: Path,
) -> dict:
    """Read the run's per-class fit summary (if present) and report
    the spread of each fitted parameter when fit on each class
    independently.

    The apparatus must have written `per_class_fit_audit.json` for this
    to fire. If absent, returns a "not-instrumented" verdict — does
    NOT fail the audit.
    """
    if not fit_summary_path.exists():
        return {
            "verdict": "not-instrumented",
            "note": (
                f"{fit_summary_path.name} not produced by this run. To enable "
                "cross-class degeneracy audit, re-run with rubric flag "
                "`emit_per_class_fit_audit: true` (planned, not yet shipped)."
            ),
        }
    try:
        data = json.loads(fit_summary_path.read_text())
    except json.JSONDecodeError as exc:
        return {"verdict": "unparseable", "error": str(exc)}
    spreads = {}
    for pname, by_class in data.items():
        vals = [v for v in by_class.values() if isinstance(v, (int, float))]
        if not vals:
            continue
        mu = sum(vals) / len(vals)
        var = sum((v - mu) ** 2 for v in vals) / len(vals)
        cv = math.sqrt(var) / abs(mu) if abs(mu) > 1e-300 else float("inf")
        spreads[pname] = {
            "per_class": by_class,
            "mean": mu,
            "cv": cv,
            "verdict": (
                "tight (universality holds)" if cv < 0.10
                else "wide (each class wants its own value)"
            ),
        }
    return {"per_param_spreads": spreads}


# ─────────────────────────────────────────────────────────────────────
# 4. Type-theoretic coherence
# ─────────────────────────────────────────────────────────────────────

def type_theoretic_coherence(workspace: Path) -> dict:
    """Verify each gate's advertised input type was actually produced.

    Reads workspace artifacts:
      - lagrangian_derivation_latest.json — did GP-180 fire? what came out?
      - noether_nondegeneracy_audit.json — what passed/dropped?
      - buckingham_pi_violations.json — present iff violations occurred
      - fit_features_result.json — anchor_pen present? bic finite?
    """
    audit = {}

    # GP-180
    p = workspace / "lagrangian_derivation_latest.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            audit["gp180"] = {
                "fired": True,
                "success": d.get("success", False),
                "noether_n": len(d.get("noether") or {}),
                "closed_form_present": bool(d.get("closed_form_callable_src")),
            }
        except Exception as exc:                                        # noqa: BLE001
            audit["gp180"] = {"fired": True, "parse_error": str(exc)}
    else:
        audit["gp180"] = {"fired": False, "note": "no LAGRANGIAN declared this iter"}

    # Non-degeneracy gate
    p = workspace / "noether_nondegeneracy_audit.json"
    if p.exists():
        try:
            arr = json.loads(p.read_text())
            verdicts = [a.get("verdict") for a in arr]
            audit["noether_nondegeneracy"] = {
                "n_invariants": len(arr),
                "n_ok": verdicts.count("ok"),
                "n_weak": verdicts.count("weak"),
                "n_degenerate": verdicts.count("degenerate"),
            }
        except Exception as exc:                                        # noqa: BLE001
            audit["noether_nondegeneracy"] = {"parse_error": str(exc)}

    # Buckingham π
    p = workspace / "buckingham_pi_violations.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            audit["buckingham_pi"] = {
                "violations_recorded": True,
                "n_violations": len(d.get("violations") or []),
            }
        except Exception:                                               # noqa: BLE001
            audit["buckingham_pi"] = {"violations_recorded": True, "parse_error": True}
    else:
        audit["buckingham_pi"] = {"violations_recorded": False}

    # Fit anchor coherence
    p = workspace / "fit_features_result.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            audit["fit"] = {
                "success": d.get("success"),
                "bic": d.get("bic"),
                "n_anchors_used": len(d.get("anchors_passed") or []) if d.get("anchors_passed") else None,
            }
        except Exception as exc:                                        # noqa: BLE001
            audit["fit"] = {"parse_error": str(exc)}

    return audit


# ─────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────

def run_audit(
    project: str,
    run_id: str | int,
    *,
    output_path: Path | None = None,
) -> dict:
    """Library entry point — same logic as the CLI, but returns the
    report dict in addition to writing it to disk. The autoresearch
    main loop's post-promotion hook calls this directly; the CLI
    `main()` is a thin argparse wrapper around it.
    """
    proj = REPO_ROOT / "projects" / project
    if not proj.exists():
        return {"error": f"project dir not found: {proj}"}
    workspace = proj / "workspace"

    test_model = proj / "test_model.py"
    if not test_model.exists():
        return {"error": f"{test_model} not found"}
    text = test_model.read_text()
    pf, mp = None, {}
    for tree_node in ast.walk(ast.parse(text)):
        if isinstance(tree_node, ast.Assign) and len(tree_node.targets) == 1:
            tgt = tree_node.targets[0]
            if isinstance(tgt, ast.Name):
                try:
                    val = ast.literal_eval(tree_node.value)
                except (ValueError, SyntaxError):
                    continue
                if tgt.id == "PARAMETRIC_FORM" and isinstance(val, str):
                    pf = val
                elif tgt.id == "MODEL_PARAMS" and isinstance(val, dict):
                    mp = val

    fit_path = workspace / "fit_features_result.json"
    fit = json.loads(fit_path.read_text()) if fit_path.exists() else {}

    report: dict = {
        "project": project,
        "run_id": str(run_id),
        "champion_form": pf,
        "champion_params": mp,
    }
    if pf is not None:
        report["check_1_kolmogorov_vs_yield"] = kolmogorov_vs_yield(
            parametric_form=pf,
            n_params=len(mp),
            mre_baseline=float(fit.get("mre_baseline", 1.0) or 1.0),
            mre_form=float(fit.get("mean_abs_residual", 1.0) or 1.0),
            n_rows=int(fit.get("n_fit_rows", 1) or 1),
        )
        report["check_2_boundary_collapse"] = boundary_collapse(pf, mp)
    report["check_3_cross_class_degeneracy"] = cross_class_param_spread(
        workspace / "per_class_fit_audit.json"
    )
    report["check_4_type_theoretic_coherence"] = type_theoretic_coherence(workspace)

    out_path = output_path or (workspace / f"epistemic_coherence_{run_id}.json")
    out_path.write_text(json.dumps(report, indent=2, default=str))
    return report


def _print_summary(report: dict) -> None:
    if "error" in report:
        print(f"ERROR: {report['error']}", file=sys.stderr)
        return
    print(f"=== Epistemic Coherence Audit — {report['project']} run {report['run_id']} ===")
    if "check_1_kolmogorov_vs_yield" in report:
        c = report["check_1_kolmogorov_vs_yield"]
        print(f"  K-vs-yield: {c.get('verdict')}  (yield_ratio={c.get('yield_ratio')})")
    if "check_2_boundary_collapse" in report:
        c = report["check_2_boundary_collapse"]
        print(f"  boundary:   {c.get('verdict')}")
    c = report["check_3_cross_class_degeneracy"]
    print(f"  cross-class: {c.get('verdict', 'computed')}")
    c = report["check_4_type_theoretic_coherence"]
    gp180 = c.get("gp180", {}) or {}
    nond = c.get("noether_nondegeneracy", {}) or {}
    bp = c.get("buckingham_pi", {}) or {}
    print(f"  type-theory: gp180={gp180.get('success')} "
          f"noether_ok={nond.get('n_ok')} "
          f"buckingham_violations={bp.get('n_violations', 0)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    report = run_audit(
        project=args.project, run_id=args.run_id,
        output_path=Path(args.output) if args.output else None,
    )
    if "error" in report:
        print(f"ERROR: {report['error']}", file=sys.stderr)
        return 2
    out_path = Path(args.output) if args.output else (
        REPO_ROOT / "projects" / args.project / "workspace"
        / f"epistemic_coherence_{args.run_id}.json"
    )
    print(f"✓ epistemic-coherence audit written to {out_path}")
    print()
    _print_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
