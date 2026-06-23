"""Post-UNDERIDENTIFIED pipeline: what to try when the grammar exhausts.

Three automated strategies, tried in order:
  A. Cross-substrate gap accumulation (log the diagnostic for pattern detection)
  B. Observable rotation (try standard transforms of the data)
  C. Scale expansion (test if UNDERIDENTIFIED resolves at larger N)

Each strategy is lightweight and deterministic. No LLM. The results
feed back into the compression pipeline for a re-attempt.

Usage:
    from ztare.fit.post_underidentified import run_post_underidentified
    results = run_post_underidentified(project_dir)
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit


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


# ---------------------------------------------------------------
# Strategy A: Cross-substrate gap accumulation
# ---------------------------------------------------------------

def log_underidentified(project_dir: Path, diagnostic: dict) -> None:
    """Append an UNDERIDENTIFIED diagnostic to the cross-substrate log."""
    log_path = Path("workspace/underidentified_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "project": project_dir.name,
        "diagnostic": diagnostic,
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def check_recurring_gaps(min_occurrences: int = 3) -> list[dict]:
    """Check the cross-substrate log for recurring residual signatures."""
    log_path = Path("workspace/underidentified_log.jsonl")
    if not log_path.exists():
        return []

    entries = []
    for line in log_path.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))

    # Group by noise class
    from collections import Counter
    noise_classes = Counter()
    for e in entries:
        nc = e.get("diagnostic", {}).get("noise_class", "unknown")
        noise_classes[nc] += 1

    recurring = []
    for nc, count in noise_classes.items():
        if count >= min_occurrences:
            recurring.append({
                "gap": nc,
                "occurrences": count,
                "projects": [e["project"] for e in entries
                            if e.get("diagnostic", {}).get("noise_class") == nc],
            })

    return recurring


# ---------------------------------------------------------------
# Strategy B: Observable rotation
# ---------------------------------------------------------------

def try_observable_rotations(
    evidence: list[tuple[float, float]],
    project_dir: Path,
) -> list[dict]:
    """Try standard transforms of the observable and check if any
    produces a compressible signal.

    Transforms:
      1. log(z) — common for multiplicative processes
      2. 1/z — reciprocal
      3. z^2 — quadratic
      4. diff(z) — first differences (removes trend)
    """
    x = np.array([p[0] for p in evidence])
    z = np.array([p[1] for p in evidence])

    transforms = []

    # log(z) if z > 0
    if np.all(z > 0):
        log_z = np.log(z)
        transforms.append(("log(z)", list(zip(x.tolist(), log_z.tolist()))))

    # 1/z if z != 0
    if np.all(z != 0):
        inv_z = 1.0 / z
        transforms.append(("1/z", list(zip(x.tolist(), inv_z.tolist()))))

    # diff(z) — first differences (removes trend, reveals local structure)
    if len(z) > 1:
        dz = np.diff(z)
        transforms.append(("diff(z)", list(zip(x[1:].tolist(), dz.tolist()))))

    # GP-127: Extended representation transforms
    # log-difference — catches geometric/multiplicative growth rates
    if len(z) > 1 and np.all(z > 0):
        log_diff = np.diff(np.log(z))
        transforms.append(("diff(log(z))", list(zip(x[1:].tolist(), log_diff.tolist()))))

    # running average — smooths fluctuations, reveals underlying trend
    if len(z) > 2:
        cumavg = np.cumsum(z) / np.arange(1, len(z) + 1)
        transforms.append(("cumavg(z)", list(zip(x.tolist(), cumavg.tolist()))))

    # z * x — un-normalizes ratios (if z = count/x, then z*x = count)
    zx = z * x
    transforms.append(("z*x", list(zip(x.tolist(), zx.tolist()))))

    # z^2 — quadratic (reveals structure in variance)
    z2 = z ** 2
    transforms.append(("z^2", list(zip(x.tolist(), z2.tolist()))))

    # sqrt(|z|) — compresses large values
    sqrt_z = np.sqrt(np.abs(z))
    transforms.append(("sqrt(|z|)", list(zip(x.tolist(), sqrt_z.tolist()))))

    # ratio z(n)/z(n-1) — consecutive ratios (catches geometric sequences)
    if len(z) > 1 and np.all(z[:-1] != 0):
        ratios = z[1:] / z[:-1]
        if np.all(np.isfinite(ratios)):
            transforms.append(("z(n)/z(n-1)", list(zip(x[1:].tolist(), ratios.tolist()))))

    # continued fraction coefficients via mpmath
    try:
        from mpmath import mpf
        cf_coeffs = []
        for val in z[:min(len(z), 50)]:  # limit to 50 for speed
            cf = list(mpf(val).cf()[:5])  # first 5 CF coefficients
            cf_coeffs.append(float(cf[0]) if cf else 0.0)
        if len(cf_coeffs) > 5:
            transforms.append(("cf_floor(z)", list(zip(
                x[:len(cf_coeffs)].tolist(), cf_coeffs))))
    except Exception:
        pass

    # Fourier power spectrum — if z has periodic structure, the dominant
    # Fourier coefficients might compress even when z itself doesn't
    if len(z) > 10:
        try:
            fft_vals = np.fft.rfft(z - np.mean(z))
            fft_mag = np.abs(fft_vals)[1:]  # skip DC
            fft_freq_idx = np.arange(1, len(fft_mag) + 1, dtype=float)
            if len(fft_mag) > 5:
                transforms.append(("fft_magnitude", list(zip(
                    fft_freq_idx.tolist(), fft_mag.tolist()))))
        except Exception:
            pass

    results = []
    for name, transformed_data in transforms:
        # Quick check: does a simple template fit better on the transform?
        xt = np.array([p[0] for p in transformed_data])
        yt = np.array([p[1] for p in transformed_data])

        best_res = float("inf")
        best_template = None
        for tname, fn, p0 in [
            ("log", lambda n, a, b: a * np.log(n) + b, [1.0, 0.0]),
            ("sqrt", lambda n, a, b: a * np.sqrt(n) + b, [1.0, 0.0]),
            ("log+recip", lambda n, a, b, c: a * np.log(n) + b / n + c, [1.0, -5.0, 0.5]),
            ("sqrt+log", lambda n, a, b, c: a * np.sqrt(n) + b * np.log(n) + c, [0.01, 1.0, 0.5]),
            ("power", lambda n, a, b, c: a * n**b + c, [1.0, 0.5, 0.0]),
            ("power_decay", lambda n, a, b, c: a * n**(-b) + c, [1.0, 0.5, 0.0]),
            ("sqrt+log+recip", lambda n, a, b, c, d: a * np.sqrt(n) + b * np.log(n) + c / n + d, [0.01, 1.0, -5.0, 0.5]),
        ]:
            try:
                popt, _ = curve_fit(fn, xt, yt, p0=p0, maxfev=5000)
                pred = fn(xt, *popt)
                max_res = float(np.max(np.abs(yt - pred)))
                if max_res < best_res:
                    best_res = max_res
                    best_template = tname
            except Exception:
                pass

        results.append({
            "transform": name,
            "best_template": best_template,
            "best_residual": round(best_res, 6),
            "n_points": len(transformed_data),
        })

    return results


# ---------------------------------------------------------------
# Strategy C: Scale expansion check
# ---------------------------------------------------------------

def check_scale_resolution(
    evidence_visible: list[tuple[float, float]],
    evidence_holdout: list[tuple[float, float]],
) -> dict:
    """Check if combining visible + holdout as a larger visible window
    changes the UNDERIDENTIFIED verdict. If a template passes on the
    larger window, the form was discoverable at larger scale."""

    combined = evidence_visible + evidence_holdout
    x = np.array([p[0] for p in combined])
    y = np.array([p[1] for p in combined])

    # Try the top templates
    best_res = float("inf")
    best_name = None
    for name, fn, p0 in [
        ("log+recip", lambda n, a, b, c: a * np.log(n) + b / n + c, [1.0, -5.0, 0.5]),
        ("sqrt+log", lambda n, a, b, c: a * np.sqrt(n) + b * np.log(n) + c, [0.01, 1.0, 0.5]),
        ("power_decay", lambda n, a, b, c: a * n**(-b) + c, [1.0, 0.5, 0.5]),
    ]:
        try:
            popt, _ = curve_fit(fn, x, y, p0=p0, maxfev=5000)
            pred = fn(x, *popt)
            res = float(np.max(np.abs(y - pred)))
            if res < best_res:
                best_res = res
                best_name = name
        except Exception:
            pass

    return {
        "combined_points": len(combined),
        "best_template": best_name,
        "best_residual": round(best_res, 6),
        "improved_vs_visible": best_res < 0.05,  # rough gate threshold
    }


# ---------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------

def run_post_underidentified(project_dir: Path) -> dict:
    """Run the post-UNDERIDENTIFIED pipeline.

    Returns a dict with results from all three strategies.
    """
    visible = _load_evidence(project_dir / "evidence.txt")
    holdout = _load_evidence(project_dir / "evidence_holdout.txt") if \
        (project_dir / "evidence_holdout.txt").exists() else []

    # Read margin-of-safety results for the diagnostic
    ms_path = project_dir / "workspace" / "margin_of_safety.json"
    diagnostic = {}
    if ms_path.exists():
        ms = json.loads(ms_path.read_text())
        rc = ms.get("residual_characterization", {})
        diagnostic = {
            "noise_class": rc.get("noise_class", "unknown"),
            "spectral_slope": rc.get("spectral_slope"),
            "gp115_suggestions": rc.get("gp115_grammar_suggestions", []),
        }

    results = {"project": project_dir.name}

    # Strategy A: log the diagnostic
    print(f"  [A] Logging UNDERIDENTIFIED diagnostic...")
    log_underidentified(project_dir, diagnostic)
    recurring = check_recurring_gaps()
    results["recurring_gaps"] = recurring
    if recurring:
        print(f"    Recurring gaps found: {[g['gap'] for g in recurring]}")
    else:
        print(f"    No recurring gaps yet (need 3+ substrates)")

    # Strategy B: try observable rotations
    print(f"  [B] Trying observable rotations...")
    rotations = try_observable_rotations(visible, project_dir)
    results["rotations"] = rotations
    for r in rotations:
        print(f"    {r['transform']}: best={r['best_template']}, res={r['best_residual']:.4f}")

    # Strategy D: regime combinator (sigmoid-switched two-regime search)
    print(f"  [D] Regime combinator (two-regime grid search)...")
    try:
        from ztare.fit.regime_combinator import find_best_regime_split
        x_vis = np.array([p[0] for p in visible])
        y_vis = np.array([p[1] for p in visible])
        x_ho = np.array([p[0] for p in holdout]) if holdout else None
        y_ho = np.array([p[1] for p in holdout]) if holdout else None
        regime_result = find_best_regime_split(x_vis, y_vis, x_ho, y_ho, var="n")
        results["regime_split"] = regime_result
        if regime_result.get("status") == "found":
            print(f"    Breakpoint: {regime_result.get('breakpoint')}")
            print(f"    Left: {regime_result.get('left_expr','?')[:40]}")
            print(f"    Right: {regime_result.get('right_expr','?')[:40]}")
            print(f"    Visible max_res: {regime_result.get('visible_max_res')}")
            if regime_result.get("holdout_gate_pass"):
                print(f"    Holdout: PASS ({regime_result.get('holdout_max_res')})")
            elif "holdout_max_res" in regime_result:
                print(f"    Holdout: FAIL ({regime_result.get('holdout_max_res')})")
    except Exception as e:
        results["regime_split"] = {"error": str(e)}
        print(f"    Regime combinator failed: {e}")

    # Strategy C: check scale expansion
    if holdout:
        print(f"  [C] Checking scale expansion...")
        scale = check_scale_resolution(visible, holdout)
        results["scale_expansion"] = scale
        print(f"    Combined {scale['combined_points']} pts: "
              f"best={scale['best_template']}, res={scale['best_residual']:.4f}, "
              f"improved={scale['improved_vs_visible']}")
    else:
        results["scale_expansion"] = {"skipped": True, "reason": "no holdout"}

    # Strategy E: Rotation feedback loop (GP-121 Fix 1)
    # If a rotation produced residual below gate threshold, write rotated
    # evidence and rerun compression on it. The composed form (inverse
    # rotation of the compression) is validated on ORIGINAL holdout.
    gate_threshold = 0.05  # standard sequential gate
    actionable = [r for r in rotations if r["best_residual"] < gate_threshold]
    results["actionable_rotations"] = len(actionable)

    if actionable:
        print(f"  [E] Rotation feedback: {len(actionable)} actionable rotation(s)")
        for rot in actionable:
            transform = rot["transform"]
            print(f"    Closing loop on {transform} (res={rot['best_residual']:.4f})...")

            # Write rotated evidence
            rotated_vis = _apply_rotation(visible, transform)
            rotated_ho = _apply_rotation(holdout, transform) if holdout else []

            if not rotated_vis:
                print(f"      Rotation {transform} produced empty data, skipping")
                continue

            rot_ev_path = project_dir / f"evidence_rotated_{transform.replace('/', '_')}.txt"
            lines = [f"# Rotated evidence: {transform}", "# n\tz"]
            for x, y in rotated_vis:
                lines.append(f"{x}\t{y}")
            rot_ev_path.write_text("\n".join(lines) + "\n")

            rot_ho_path = project_dir / f"evidence_holdout_rotated_{transform.replace('/', '_')}.txt"
            if rotated_ho:
                lines = ["# holdout (rotated)"]
                for x, y in rotated_ho:
                    lines.append(f"{x}\t{y}")
                rot_ho_path.write_text("\n".join(lines) + "\n")

            # Run compression on rotated evidence
            try:
                from ztare.fit.compress_champion import compress_champion
                rot_result = compress_champion(
                    project_dir,
                    evidence_override_path=rot_ev_path,
                    holdout_override_path=rot_ho_path if rotated_ho else None,
                )
                # compress_champion returns list[CompressionResult]; pick best gate-passing
                gate_passing_rot = [r for r in rot_result if r.gates_passed] if rot_result else []
                if gate_passing_rot:
                    best_cr = gate_passing_rot[0]
                    print(f"      Rotated compression: {best_cr.name} k={best_cr.k} "
                          f"vis={best_cr.visible_max_res:.4f}")

                    # Compose: the original observable is inverse_rotation(compressed_form)
                    composed = _compose_with_inverse(transform, best_cr.expression, best_cr.params)
                    if composed:
                        print(f"      Composed form: z(n) = {composed['expression'][:60]}")

                        # Validate on ORIGINAL (unrotated) holdout
                        if holdout:
                            ho_res = _validate_composed(composed, holdout)
                            print(f"      Original holdout max_res: {ho_res:.4f}")
                            composed["holdout_max_res"] = ho_res
                            composed["holdout_pass"] = ho_res < gate_threshold

                        results[f"rotation_feedback_{transform}"] = composed
                    else:
                        print(f"      Could not compose inverse rotation")
                else:
                    print(f"      Rotated compression: no gate-passing form")
            except Exception as e:
                print(f"      Rotation feedback failed: {e}")
    else:
        print(f"  [E] No actionable rotations (none below gate threshold)")

    # Save
    out = project_dir / "workspace" / "post_underidentified.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"  Saved to {out}")

    return results


def _apply_rotation(
    evidence: list[tuple[float, float]], transform: str
) -> list[tuple[float, float]]:
    """Apply a rotation transform to evidence data."""
    result = []
    for x, z in evidence:
        try:
            if transform == "log(z)" and z > 0:
                result.append((x, math.log(z)))
            elif transform == "1/z" and z != 0:
                result.append((x, 1.0 / z))
            elif transform == "diff(z)":
                pass  # diff needs sequential processing, handled separately
            else:
                continue
        except (ValueError, ZeroDivisionError):
            continue

    # Handle diff(z) separately (needs pairs)
    if transform == "diff(z)" and len(evidence) > 1:
        for i in range(1, len(evidence)):
            x = evidence[i][0]
            dz = evidence[i][1] - evidence[i - 1][1]
            result.append((x, dz))

    return result


def _compose_with_inverse(
    transform: str, expression: str, params: dict
) -> dict | None:
    """Compose a compression result with the inverse of the rotation.

    If the rotation was z → 1/z and the compression found g(n),
    the original observable is z(n) = 1/g(n).
    """
    if transform == "1/z":
        composed_expr = f"1.0 / ({expression})"
    elif transform == "log(z)":
        composed_expr = f"math.exp({expression})"
    elif transform == "diff(z)":
        # diff inverse requires cumulative sum — not trivially composable
        return None
    else:
        return None

    return {
        "expression": composed_expr,
        "params": params,
        "rotation": transform,
        "inner_expression": expression,
    }


def _validate_composed(composed: dict, holdout: list[tuple[float, float]]) -> float:
    """Validate a composed form against original (unrotated) holdout."""
    expr = composed["expression"]
    params = composed["params"]
    param_names = list(params.keys())

    code = f"def _m(n, {', '.join(param_names)}):\n    return {expr}"
    ns = {"math": math, "np": np}
    exec(code, ns)
    fn = ns["_m"]

    max_res = 0.0
    for x, z_actual in holdout:
        try:
            z_pred = fn(x, *params.values())
            res = abs(z_actual - z_pred)
            max_res = max(max_res, res)
        except Exception:
            max_res = float("inf")
            break

    return max_res
