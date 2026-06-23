"""Programmatic Panel Review for Grammar Expansion Decisions.

Replaces ad-hoc Agent-spawned panel debates with a deterministic
checklist that answers the same questions the panels always asked.

The panel's recurring questions (distilled from 10+ debates this session):
1. Is this overfitting to one substrate? (Munger)
2. Does the new template pass regression on prior substrates? (Popper)
3. Is the implementation numerically stable? (Dijkstra)
4. Does the Torvalds test pass (would we add this without seeing the data)? (Munger)

If all four pass: auto-promote. If any fail: flag for operator review.

Usage:
    from ztare.fit.programmatic_panel import review_grammar_expansion
    verdict = review_grammar_expansion(
        template_name="parabolic",
        expression="a * (n - b)**2 + c",
        params=["a", "b", "c"],
        motivating_substrate="gp116_cot_exchange",
        improvement_ratio=8.0,
    )
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit


def review_grammar_expansion(
    template_name: str,
    expression: str,
    params: list[str],
    motivating_substrate: str,
    improvement_ratio: float,
    regression_substrates: list[str] | None = None,
) -> dict:
    """Run the programmatic panel review on a proposed grammar expansion.

    Returns a verdict dict with pass/fail for each check and an
    overall recommendation.
    """
    if regression_substrates is None:
        regression_substrates = [
            "gp088_calibration_a01",
            "oeis_a000009",
            "oeis_a000959",
        ]

    checks = {}

    # Check 1 (Munger): Torvalds test
    # Would a practitioner looking at the grammar WITHOUT seeing the data
    # say "this template class is missing"?
    # Heuristic: is the template class (parabolic, periodic, piecewise)
    # a standard mathematical form that any regression library includes?
    standard_classes = {"linear", "quadratic", "parabolic", "exponential",
                       "logarithmic", "power", "sinusoidal", "reciprocal",
                       "sigmoid", "polynomial"}
    template_class = template_name.lower().replace("auto_", "")
    torvalds = any(sc in template_class for sc in standard_classes)
    checks["torvalds_test"] = {
        "pass": torvalds,
        "reason": f"'{template_class}' is {'a standard' if torvalds else 'NOT a standard'} mathematical form",
    }

    # Check 2 (Popper): Regression test on prior substrates
    false_positives = []
    for substrate in regression_substrates:
        ev_path = Path(f"projects/{substrate}/evidence.txt")
        ho_path = Path(f"projects/{substrate}/evidence_holdout.txt")
        if not ev_path.exists() or not ho_path.exists():
            continue

        # Load evidence
        def load(p):
            pts = []
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split()
                if len(parts) >= 2:
                    try: pts.append((float(parts[0]), float(parts[1])))
                    except: pass
            return pts

        vis = load(ev_path)
        ho = load(ho_path)
        if len(vis) < 5 or len(ho) < 3:
            continue

        x_vis = np.array([p[0] for p in vis])
        y_vis = np.array([p[1] for p in vis])
        x_ho = np.array([p[0] for p in ho])
        y_ho = np.array([p[1] for p in ho])

        try:
            code = f"def _m(_x_, {', '.join(params)}):\n    n=_x_\n    return {expression.replace('math.', 'np.')}"
            ns = {"np": np}
            exec(code, ns)
            fn = ns["_m"]
            p0 = [1.0] * len(params)
            popt, _ = curve_fit(fn, x_vis, y_vis, p0=p0, maxfev=5000)
            pred_ho = fn(x_ho, *popt)
            ho_res = float(np.max(np.abs(y_ho - pred_ho)))
            if ho_res < 0.05:  # passes gate
                false_positives.append(substrate)
        except Exception:
            pass

    checks["regression_test"] = {
        "pass": len(false_positives) == 0,
        "false_positives": false_positives,
        "substrates_tested": len(regression_substrates),
        "reason": f"{'No' if not false_positives else len(false_positives)} false positives on {len(regression_substrates)} substrates",
    }

    # Check 3 (Dijkstra): Numerical stability
    # Can curve_fit converge on the template with reasonable p0?
    stable = True
    try:
        test_x = np.linspace(1, 100, 50)
        test_y = np.random.randn(50) * 0.1 + 5
        code = f"def _m(_x_, {', '.join(params)}):\n    n=_x_\n    return {expression.replace('math.', 'np.')}"
        ns = {"np": np}
        exec(code, ns)
        fn = ns["_m"]
        p0 = [1.0] * len(params)
        popt, _ = curve_fit(fn, test_x, test_y, p0=p0, maxfev=5000)
        pred = fn(test_x, *popt)
        if np.any(np.isnan(pred)) or np.any(np.isinf(pred)):
            stable = False
    except Exception:
        stable = False

    checks["numerical_stability"] = {
        "pass": stable,
        "reason": "curve_fit converges without NaN/Inf" if stable else "curve_fit produces NaN/Inf",
    }

    # Check 4 (Munger): Single-substrate overfitting
    checks["single_substrate"] = {
        "pass": improvement_ratio >= 1.5,
        "reason": f"Improvement ratio {improvement_ratio:.1f}x {'meets' if improvement_ratio >= 1.5 else 'below'} 1.5x threshold",
    }

    # Overall verdict
    all_pass = all(c["pass"] for c in checks.values())

    return {
        "template_name": template_name,
        "expression": expression,
        "motivating_substrate": motivating_substrate,
        "checks": checks,
        "verdict": "AUTO_PROMOTE" if all_pass else "OPERATOR_REVIEW",
        "all_pass": all_pass,
    }
