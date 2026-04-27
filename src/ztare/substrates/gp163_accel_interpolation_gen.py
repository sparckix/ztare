#!/usr/bin/env python3
"""GP-163 substrate generator — Acceleration Interpolation.

Division A artifact (GT-aware). Produces:
  - evidence.txt (visible data, cold-framed)
  - evidence_holdout.txt (hidden holdout + farther-tail)
  - gate_harness.py (deterministic holdout gates)
  - test_model.py (NaN-returning baseline stub)
  - .denylist (GT leak sentinel)
  - project_charter.md
  - rubric JSON

Data source: SPARC (Lelli et al. 2016), 175 galaxies, 3391 (g_bar, g_obs) points.
The RAR functional form is OPEN — multiple rival forms exist (McGaugh 2016,
simple interpolation, MOND, ΛCDM emergent). This is a genuine discovery target.

Asymptotic constraints (hard gates):
  - High g_bar: g_obs → g_bar (Newtonian limit)
  - Low g_bar: g_obs → sqrt(a_0 * g_bar) (deep MOND limit)
  - a_0 ≈ 1.2e-10 m/s^2 (Milgrom's constant)

Holdout design:
  - 70% visible (random galaxy-level split — entire galaxies held out, not individual points)
  - 20% holdout (withheld galaxies)
  - 10% farther-tail (lowest-acceleration galaxies, g_bar < 1e-12 — deep MOND regime)

Cold framing:
  - Variables: x (input acceleration), y (output acceleration)
  - No "galaxy", "MOND", "dark matter", "baryonic" in mutator-visible artifacts
  - Asymptotic constraints stated as math, not physics
"""
import csv
import hashlib
import json
import math
import os
import random
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent
RAW_CSV = PROJ_DIR / "raw" / "sparc_rar.csv"
SEED = 163

# ── Load data ─────────────────────────────────────────────────────────
def load_rar():
    rows = []
    with open(RAW_CSV) as f:
        for r in csv.DictReader(f):
            rows.append({
                "galaxy": r["galaxy"],
                "g_bar": float(r["g_bar"]),
                "g_obs": float(r["g_obs"]),
                "log_g_bar": float(r["log_g_bar"]),
                "log_g_obs": float(r["log_g_obs"]),
                "errV_frac": float(r["errV_frac"]),
            })
    return rows


# ── Split by galaxy (not by point) ────────────────────────────────────
def split_galaxies(rows):
    galaxies = sorted(set(r["galaxy"] for r in rows))
    rng = random.Random(SEED)
    rng.shuffle(galaxies)

    # Farther-tail: galaxies where median g_bar < 1e-12 (deep MOND)
    galaxy_median_gbar = {}
    for g in galaxies:
        gvals = sorted(r["g_bar"] for r in rows if r["galaxy"] == g)
        galaxy_median_gbar[g] = gvals[len(gvals)//2]

    farther_tail_galaxies = {g for g in galaxies if galaxy_median_gbar[g] < 4e-12}
    remaining = [g for g in galaxies if g not in farther_tail_galaxies]

    # 70/20 split on remaining
    n_holdout = max(5, int(len(remaining) * 0.20))
    holdout_galaxies = set(remaining[:n_holdout])
    visible_galaxies = set(remaining[n_holdout:])

    visible = [r for r in rows if r["galaxy"] in visible_galaxies]
    holdout = [r for r in rows if r["galaxy"] in holdout_galaxies]
    farther_tail = [r for r in rows if r["galaxy"] in farther_tail_galaxies]

    return visible, holdout, farther_tail, visible_galaxies, holdout_galaxies, farther_tail_galaxies


# ── Write evidence.txt (visible only, cold-framed) ────────────────────
def write_evidence(visible):
    # Subsample for readability — include ~200 representative points
    rng = random.Random(SEED + 1)
    if len(visible) > 200:
        sample = sorted(rng.sample(visible, 200), key=lambda r: r["g_bar"])
    else:
        sample = sorted(visible, key=lambda r: r["g_bar"])

    lines = [
        "# Evidence Surface — GP-163 Acceleration Interpolation",
        "",
        "## Evidence Set A — Visible Data (200 representative points from full visible set)",
        "",
        "You are given (x, y) pairs where x and y are both positive accelerations.",
        "x is the acceleration predicted by visible matter alone.",
        "y is the total observed acceleration (including any unseen component).",
        "",
        "The full visible set has {} points from {} sources.".format(
            len(visible), len(set(r["galaxy"] for r in visible))
        ),
        "The 200 points below are a representative subsample spanning the full range.",
        "",
        "| x (input acceleration, m/s^2) | y (observed acceleration, m/s^2) |",
        "|------|------|",
    ]
    for r in sample:
        lines.append(f"| {r['g_bar']:.4e} | {r['g_obs']:.4e} |")

    lines.extend([
        "",
        "## Evidence Set B — Asymptotic Constraints (hard gates)",
        "",
        "1. **High-x limit:** as x → large, y → x. The observed acceleration equals",
        "   the predicted acceleration when the predicted value is large.",
        "2. **Low-x limit:** as x → small, y → sqrt(a_0 * x) where a_0 ≈ 1.2e-10 m/s^2.",
        "   The observed acceleration exceeds the prediction, following a square-root law.",
        "3. **Monotonicity:** y is monotonically increasing with x.",
        "4. **y > x** for all x below the crossover point (y = x intersect).",
        "",
        "## Evidence Set C — Constraints",
        "",
        "1. K_law ≤ 5 parameters.",
        "2. The law must interpolate between the two asymptotic regimes.",
        "3. y > 0 for all x > 0.",
        "4. The crossover between regimes occurs near x ≈ a_0 ≈ 1.2e-10 m/s^2.",
        "",
        "## Evidence Set D — MANDATORY Python Contract",
        "",
        "Your ```python block for test_model.py MUST contain:",
        "1. An I_model(x) function that returns predicted y for input x",
        "2. Assert statements verifying your model",
        "",
        "```python",
        "import math",
        "",
        "MODEL_PARAMS = {'a': 1.0, 'b': 1.2e-10}",
        "",
        "def I_model(x, params=None):",
        "    p = params if params is not None else MODEL_PARAMS",
        "    # EXAMPLE ONLY — this form is WRONG, will fail holdout.",
        "    # Discover the right interpolation function.",
        "    return x + p['b']  # placeholder",
        "",
        "assert not math.isnan(I_model(1e-11)), 'I_model must return a number'",
        "assert I_model(1e-11) > 1e-11, 'y > x in low-acceleration regime'",
        "assert abs(I_model(1e-8) - 1e-8) / 1e-8 < 0.1, 'y ≈ x in high-acceleration regime'",
        "```",
        "",
        "If I_model returns NaN or is not overridden, score = 0.",
        "FIT CONSTANTS FROM THE DATA.",
    ])

    (PROJ_DIR / "evidence.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Write evidence_holdout.txt ────────────────────────────────────────
def write_holdout(holdout, farther_tail):
    lines = [
        "# GP-163 Holdout — withheld acceleration data",
        "# Format: g_bar<TAB>g_obs",
        "# This file is read ONLY by gate_harness.py.",
        "# === HOLDOUT_SET (target MRE < 0.20) ===",
    ]
    for r in holdout:
        lines.append(f"{r['g_bar']:.6e}\t{r['g_obs']:.6e}")
    lines.append("# === FARTHER_TAIL_SET (deep low-x regime, target MRE < 0.30) ===")
    for r in farther_tail:
        lines.append(f"{r['g_bar']:.6e}\t{r['g_obs']:.6e}")

    (PROJ_DIR / "evidence_holdout.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Write gate_harness.py ─────────────────────────────────────────────
def write_gate_harness(visible, holdout, farther_tail):
    code = '''"""GP-163 gate harness — Acceleration interpolation holdout evaluation.

Loads test_model.py dynamically, calls I_model(g_bar) on holdout and
farther-tail sets, reports MRE + asymptotic constraint checks.
"""
import importlib.util as _ilu
import json
import math
import os
import sys

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_HOLDOUT_PATH = os.path.join(_PROJECT_DIR, "evidence_holdout.txt")
_HOLDOUT_THRESHOLD = 0.20
_FARTHER_TAIL_THRESHOLD = 0.30
_A0 = 1.2e-10  # crossover constant


def _parse_holdout():
    holdout, farther = [], []
    in_farther = False
    with open(_HOLDOUT_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                if "FARTHER_TAIL_SET" in line:
                    in_farther = True
                continue
            parts = line.split("\\t")
            if len(parts) < 2:
                continue
            try:
                g_bar, g_obs = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            if in_farther:
                farther.append((g_bar, g_obs))
            else:
                holdout.append((g_bar, g_obs))
    return holdout, farther


def _load_model():
    test_model_path = os.path.join(_PROJECT_DIR, "test_model.py")
    spec = _ilu.spec_from_file_location("_gp163_test_model", test_model_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load test_model.py at {test_model_path}")
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "I_model") or not callable(module.I_model):
        raise AttributeError("test_model.py must define I_model(x)")
    return module


def _relative_error(pred, actual):
    if actual == 0:
        return abs(pred)
    return abs(pred - actual) / abs(actual)


def _evaluate_set(data, I_model, threshold):
    errors = []
    for g_bar, g_obs in data:
        try:
            y = float(I_model(g_bar))
        except Exception:
            y = float("nan")
        if math.isnan(y) or math.isinf(y):
            errors.append(1.0)
        else:
            errors.append(_relative_error(y, g_obs))
    n = len(errors) or 1
    mre = sum(errors) / n
    return {
        "n": len(errors),
        "mean_relative_error": mre,
        "max_relative_error": max(errors) if errors else 1.0,
        "passed": mre < threshold,
        "threshold": threshold,
    }


def main():
    holdout, farther = _parse_holdout()
    model = _load_model()
    I_model = model.I_model

    results = {}
    results["holdout"] = _evaluate_set(holdout, I_model, _HOLDOUT_THRESHOLD)
    results["farther_tail"] = _evaluate_set(farther, I_model, _FARTHER_TAIL_THRESHOLD)

    # Asymptotic constraint checks
    asymptotic = {"violations": [], "passed": True}
    # High-x: g_obs ≈ g_bar at g_bar = 1e-8
    try:
        y_high = float(I_model(1e-8))
        if abs(y_high - 1e-8) / 1e-8 > 0.15:
            asymptotic["violations"].append({"test": "high_x_newtonian", "g_bar": 1e-8, "y": y_high, "expected": 1e-8})
            asymptotic["passed"] = False
    except Exception:
        asymptotic["violations"].append({"test": "high_x_newtonian", "error": "exception"})
        asymptotic["passed"] = False

    # Low-x: g_obs ≈ sqrt(a0 * g_bar) at g_bar = 1e-12
    try:
        y_low = float(I_model(1e-12))
        expected_low = math.sqrt(_A0 * 1e-12)
        if abs(y_low - expected_low) / expected_low > 0.30:
            asymptotic["violations"].append({"test": "low_x_deep", "g_bar": 1e-12, "y": y_low, "expected": expected_low})
            asymptotic["passed"] = False
    except Exception:
        asymptotic["violations"].append({"test": "low_x_deep", "error": "exception"})
        asymptotic["passed"] = False

    results["asymptotic"] = asymptotic
    results["all_gates_pass"] = (
        results["holdout"]["passed"]
        and results["farther_tail"]["passed"]
        and results["asymptotic"]["passed"]
    )

    print(json.dumps(results, indent=2))
    return 0 if results["all_gates_pass"] else 1


if __name__ == "__main__":
    if "--emit-deterministic-gates" in sys.argv:
        sys.exit(main())
    elif "--run-smoke-test" in sys.argv:
        sys.exit(main())
    else:
        sys.exit(main())
'''
    (PROJ_DIR / "gate_harness.py").write_text(code, encoding="utf-8")


# ── Write test_model.py (baseline stub) ───────────────────────────────
def write_test_model():
    code = '''import math

MODEL_PARAMS = {}

def I_model(x, params=None):
    """Predict y (observed acceleration) given x (input acceleration).
    Mutator MUST override this."""
    return float("nan")

def test_model_grammar_contract():
    any_valid = False
    for x in [1e-12, 1e-10, 1e-8]:
        v = I_model(x)
        if not math.isnan(v):
            any_valid = True
            break
    assert any_valid, "I_model returns NaN for all test points — no model defined"

if __name__ == "__main__":
    test_model_grammar_contract()
'''
    (PROJ_DIR / "test_model.py").write_text(code, encoding="utf-8")


# ── Write .denylist ───────────────────────────────────────────────────
def write_denylist():
    # Terms that should NOT appear in mutator-visible files
    terms = [
        "McGaugh",
        "MOND",
        "Milgrom",
        "dark matter",
        "baryonic",
        "SPARC",
        "galaxy",
        "rotation curve",
        "Radial Acceleration",
    ]
    (PROJ_DIR / ".denylist").write_text("\n".join(terms) + "\n", encoding="utf-8")


# ── Write project_charter.md ─────────────────────────────────────────
def write_charter(n_visible, n_holdout, n_farther, n_gal_vis, n_gal_ho, n_gal_ft):
    text = f"""# Project Charter — gp163_accel_interpolation

## Core Question

Given ~{n_visible} (x, y) pairs where x is a predicted acceleration and y is the
observed total acceleration, discover the functional form y = f(x) that
interpolates between two known asymptotic regimes:

- High x: y → x (predicted acceleration is sufficient)
- Low x: y → sqrt(a_0 * x) where a_0 ≈ 1.2e-10 m/s^2

The data spans 4+ decades in x. The interpolation function between
these two limits is unknown — multiple rival forms exist.

## Observable

1. **Holdout gate (MRE < 20%):** {n_holdout} points from {n_gal_ho} withheld sources.
2. **Farther-tail gate (MRE < 30%):** {n_farther} points from {n_gal_ft} sources in the
   deep low-x regime (x < 1e-12), where the two asymptotic regimes are
   most separated and rival forms disagree most.
3. **Asymptotic gates:** y ≈ x at x=1e-8 (within 15%). y ≈ sqrt(a_0*x) at x=1e-12 (within 30%).

## Secondary Observable (Newton-mode requirement)

1. Predict the crossover point: at what x does y/x = 2? (the acceleration where
   the unseen component equals the predicted component). Pre-commit a value.
2. Predict y at x = 5e-13 (below the farther-tail range). Pre-commit with tolerance.

## Constraints

- Cold variable names: (x, y) not (g_bar, g_obs)
- Do not reference any astrophysical theory or author
- The law has K_law ≤ 5 parameters
- The two asymptotic limits are HARD CONSTRAINTS, not suggestions
"""
    (PROJ_DIR / "project_charter.md").write_text(text, encoding="utf-8")


# ── Write rubric ──────────────────────────────────────────────────────
def write_rubric():
    rubric = {
        "name": "gp163_accel_interpolation",
        "project": "gp163_accel_interpolation",
        "description": "Newton-mode rubric for acceleration interpolation function discovery. 1D substrate, 2 known asymptotic limits, unknown interpolation.",
        "rubric_mode": "newton",
        "rubric_mode_reason": "Discovery substrate: interpolation function between two asymptotic regimes is unknown. Generative yield required.",
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": True,
        "fit_expression_grammar": "math_exp_only",
        "fit_score_mode": "continuous_mre",
        "fit_required_dimensionality": 1,
        "fit_required_vars": ["x"],
        "expression_byte_budget": 300,
        "holdout_hard_gate": True,
        "target_convention_homogeneity": "homogeneous",
        "inject_antipattern_catalog": "hardkill",
        "structural_blocker_enforcement": "gate",
        "underidentified_after": 15,
        "farther_tail_region": None,
        "farther_tail_region_disable_reason": "Custom gate_harness.py defines farther-tail set (deep low-x regime). Standard ZTARE farther-tail detection does not apply.",
        "disable_evidence_fit_gate": True,
        "disable_evidence_fit_gate_reason": "Custom gate_harness.py with holdout + asymptotic gates replaces heuristic.",
        "disable_uniqueness_gap_gate": True,
        "disable_uniqueness_gap_gate_reason": "Rival forms scored by rubric dimension.",
        "persona": "You are an adversarial epistemic auditor. The data shows a monotonic relationship between two accelerations with known asymptotic behavior at both extremes. You REJECT: (a) forms that violate the asymptotic constraints (y must approach x at high x and sqrt(a_0*x) at low x); (b) forms with more than 5 parameters; (c) forms without holdout validation; (d) forms that are purely polynomial (will fail asymptotic gates). You REWARD: parsimonious interpolation functions that pass both holdout and farther-tail gates.",
        "cage_observe_mode": True,
        "cage_observe_mode_reason": "GP-157 v5.0 Phase 3b observe-mode.",
        "cage_meta": {
            "type": "radial_acceleration_relation",
            "class": "1d",
            "target_convention_homogeneity": "homogeneous",
            "min_rows_per_category": 3,
            "near_miss_factor": 1.5,
            "frame_invariant_y": True,
            "enforce_min_rows": False,
        },
        "dimensions": [
            {"name": "Fit Quality", "weight": 35, "description": "Does the formula fit visible data, holdout (MRE<20%), and farther-tail (MRE<30%)? Does it satisfy both asymptotic constraints?"},
            {"name": "Structural Derivation", "weight": 25, "description": "Does the thesis derive the interpolation function step-by-step from data behavior? Each term motivated by an observed regime."},
            {"name": "Generative Yield", "weight": 20, "description": "Does the thesis predict at least one secondary observable (crossover point, extrapolation) with declared tolerance?"},
            {"name": "Generalization Quality", "weight": 20, "description": "Is the formula structurally justified? Does it interpolate smoothly between regimes? Penalize ad-hoc piecewise constructions."},
        ],
        "criteria": {
            "Fit_Quality": "Holdout MRE < 20%, farther-tail MRE < 30%, both asymptotic constraints within tolerance.",
            "Structural_Derivation": "At least three explicit steps citing specific data tuples.",
            "Generative_Yield": "Pre-commit at least one numerical prediction beyond the holdout.",
            "Generalization_Quality": "Smooth interpolation, no piecewise branches, structurally motivated form.",
        },
    }
    rubric_path = Path("rubrics") / "gp163_accel_interpolation.json"
    rubric_path.write_text(json.dumps(rubric, indent=2) + "\n", encoding="utf-8")


# ── Write thesis.md (placeholder) ─────────────────────────────────────
def write_thesis():
    (PROJ_DIR / "thesis.md").write_text("# Thesis — gp163_accel_interpolation\n\n(Awaiting first iteration.)\n", encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rows = load_rar()
    visible, holdout, farther_tail, vg, hg, fg = split_galaxies(rows)

    print(f"Visible: {len(visible)} points from {len(vg)} galaxies")
    print(f"Holdout: {len(holdout)} points from {len(hg)} galaxies")
    print(f"Farther-tail: {len(farther_tail)} points from {len(fg)} galaxies")
    print(f"Total: {len(visible) + len(holdout) + len(farther_tail)}")

    write_evidence(visible)
    write_holdout(holdout, farther_tail)
    write_gate_harness(visible, holdout, farther_tail)
    write_test_model()
    write_denylist()
    write_charter(len(visible), len(holdout), len(farther_tail), len(vg), len(hg), len(fg))
    write_rubric()
    write_thesis()

    print("\nAll substrate artifacts generated.")
    print("Next: make seal PROJECT=gp163_accel_interpolation RUBRIC=gp163_accel_interpolation")
