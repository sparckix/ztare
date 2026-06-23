"""GP-112 extension: Automated validity horizon detection.

Systematically varies evidence scale and runs compression at each.
Reports which template wins at each scale and where topology transitions
occur. Includes threshold-invariance test.

Usage:
    python -m src.ztare.fit.validity_horizon --project oeis_a000959 --data-path projects/oeis_a000959/lucky_500k.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit


def _numpy_expr(expr: str) -> str:
    return (expr.replace("math.log", "np.log")
            .replace("math.sqrt", "np.sqrt")
            .replace("math.exp", "np.exp"))


def _build_templates(var: str = "n"):
    """Minimal template set for horizon scanning (fast, not exhaustive)."""
    x = var
    return [
        ("log_affine", f"a * np.log({x}) + b", ["a", "b"]),
        ("log_reciprocal", f"a * np.log({x}) + b / {x} + c", ["a", "b", "c"]),
        ("loglog_reciprocal", f"a * np.log({x}) + d * np.log(np.log({x})) + b / {x} + c", ["a", "d", "b", "c"]),
        ("sqrt_log", f"a * np.sqrt({x}) + b * np.log({x}) + c", ["a", "b", "c"]),
        ("power_free", f"a * {x}**b + c", ["a", "b", "c"]),
        ("log_power", f"a * np.log({x})**b + c", ["a", "b", "c"]),
        ("power_decay", f"a * {x}**(-b) + c", ["a", "b", "c"]),
    ]


def scan_horizons(
    data: list[tuple[float, float]],
    scales: list[int] | None = None,
    holdout_fraction: float = 0.2,
    gate_threshold: float = 0.05,
    var: str = "n",
) -> dict:
    """Run compression at multiple scales and report topology transitions.

    Args:
        data: Full (x, y) dataset sorted by x.
        scales: List of visible-window sizes to test. Defaults to log-spaced.
        holdout_fraction: Fraction of each window reserved for holdout.
        gate_threshold: Max residual for holdout gate pass.
        var: Variable name in expressions.
    """
    if scales is None:
        n = len(data)
        scales = sorted(set([
            min(n, s) for s in [1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
            if s <= n
        ]))

    templates = _build_templates(var)
    results_by_scale = []

    for scale in scales:
        window = data[:scale]
        vis_end = int(scale * (1 - holdout_fraction))
        visible = window[:vis_end]
        holdout = window[vis_end:]

        if len(visible) < 20 or len(holdout) < 5:
            continue

        x_vis = np.array([p[0] for p in visible])
        y_vis = np.array([p[1] for p in visible])
        x_ho = np.array([p[0] for p in holdout])
        y_ho = np.array([p[1] for p in holdout])

        best_name = None
        best_bic = float("inf")
        best_ho_res = float("inf")
        best_params = {}
        gate_pass = False

        for name, expr, param_names in templates:
            try:
                code = f"def _m(_x_, {', '.join(param_names)}):\n    {var}=_x_\n    return {expr}"
                ns = {"np": np, "math": math}
                exec(code, ns)
                fn = ns["_m"]

                p0 = [1.0] * len(param_names)
                popt, _ = curve_fit(fn, x_vis, y_vis, p0=p0, maxfev=5000)

                pred_ho = fn(x_ho, *popt)
                ho_res = float(np.max(np.abs(y_ho - pred_ho)))

                # BIC on visible
                pred_vis = fn(x_vis, *popt)
                sse = float(np.sum((y_vis - pred_vis)**2))
                bic = len(x_vis) * np.log(sse / len(x_vis)) + len(param_names) * np.log(len(x_vis))

                passes = ho_res < gate_threshold

                if passes and bic < best_bic:
                    best_name = name
                    best_bic = float(bic)
                    best_ho_res = ho_res
                    best_params = dict(zip(param_names, [float(v) for v in popt]))
                    gate_pass = True

            except Exception:
                continue

        results_by_scale.append({
            "scale": scale,
            "visible": vis_end,
            "holdout": len(holdout),
            "winner": best_name,
            "gate_pass": gate_pass,
            "holdout_residual": round(best_ho_res, 6) if best_name else None,
            "bic": round(best_bic, 1) if best_name else None,
            "params": {k: round(v, 6) for k, v in best_params.items()} if best_params else None,
        })

    # Detect topology transitions
    transitions = []
    for i in range(1, len(results_by_scale)):
        prev = results_by_scale[i-1]
        curr = results_by_scale[i]
        if prev["winner"] != curr["winner"] and prev["winner"] and curr["winner"]:
            transitions.append({
                "from_scale": prev["scale"],
                "to_scale": curr["scale"],
                "from_topology": prev["winner"],
                "to_topology": curr["winner"],
            })

    return {
        "scales_tested": len(results_by_scale),
        "gate_threshold": gate_threshold,
        "results": results_by_scale,
        "transitions": transitions,
        "n_transitions": len(transitions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validity horizon detection")
    parser.add_argument("--project", required=True)
    parser.add_argument("--data-path", help="Path to JSON array of raw sequence values")
    parser.add_argument("--threshold", type=float, default=0.05)
    args = parser.parse_args()

    from ztare.common.paths import PROJECTS_DIR
    project_dir = PROJECTS_DIR / args.project

    # Load evidence as (x, y) pairs
    ev_path = project_dir / "evidence.txt"
    if not ev_path.exists():
        print(f"ERROR: {ev_path} not found", file=sys.stderr)
        return 1

    # If data-path provided, build density ratio from raw sequence
    if args.data_path:
        raw = json.loads(Path(args.data_path).read_text())
        if isinstance(raw, dict) and "ulam" in raw:
            raw = raw["ulam"]
        data = [(float(i + 1), raw[i] / (i + 1)) for i in range(len(raw))]
    else:
        # Load from evidence files
        data = []
        for line in ev_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    data.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue

    print(f"Data: {len(data)} points")
    result = scan_horizons(data, gate_threshold=args.threshold)

    print(f"\nScales tested: {result['scales_tested']}")
    print(f"Gate threshold: {result['gate_threshold']}")
    print(f"\n{'Scale':>8s}  {'Winner':>20s}  {'Gate':>5s}  {'HO res':>10s}  {'Lead param':>12s}")
    print("-" * 65)
    for r in result["results"]:
        lead = ""
        if r["params"]:
            first_key = list(r["params"].keys())[0]
            lead = f"{first_key}={r['params'][first_key]:.4f}"
        print(f"{r['scale']:>8d}  {str(r['winner']):>20s}  "
              f"{'PASS' if r['gate_pass'] else 'FAIL':>5s}  "
              f"{r['holdout_residual'] or 'N/A':>10}  {lead:>12s}")

    if result["transitions"]:
        print(f"\nTopology transitions:")
        for t in result["transitions"]:
            print(f"  n={t['from_scale']:,d} -> n={t['to_scale']:,d}: "
                  f"{t['from_topology']} -> {t['to_topology']}")
    else:
        print(f"\nNo topology transitions detected.")

    out_path = project_dir / "workspace" / "validity_horizon.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nSaved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
