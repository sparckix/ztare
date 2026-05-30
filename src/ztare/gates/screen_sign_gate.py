"""G-SCREEN-SIGN — falsify wrong-sign chameleon claims.

A real chameleon-screening law fits dense (inner-cluster, high
rho_local) regions BETTER than diffuse (outer-cluster, low rho_local)
regions, because the screening mechanism's defining property is
Newton recovery in dense environments.

The iter-2 false positive (gp163d_unified_accel run 1777381378) had
the OPPOSITE pattern: inner-cluster mean MRE 0.61, outer-cluster mean
MRE 0.43. The form fit OUTER clusters better than INNER — empirical
signature of an UNSCREENED modification, not a chameleon. This is
what falsified the "real chameleon" claim under Research Director
audit.

This gate mechanizes that test. Activated only when the rubric
declares `enable_screen_sign_check: true` (since the test is only
meaningful for substrates where chameleon screening is the proposed
mechanism). The apparatus caps at `cap_for_wrong_sign_screen` (default
70) with reason `screen_sign_inverted` when the gate fires.

GP-183 Phase B2.

Output schema:
  {
    "gate_id": "G-SCREEN-SIGN",
    "verdict": "ok" | "wrong_sign" | "insufficient_rows" | "not_enabled",
    "reason": <human-readable diagnosis>,
    "inner_n": int,
    "inner_mean_mre": float | None,
    "outer_n": int,
    "outer_mean_mre": float | None,
    "split_class": str,
    "split_feature": str,
    "split_threshold": float,
  }
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Optional

GATE_ID = "G-SCREEN-SIGN"


def _safe_eval(form_src: str, features: dict, params: dict) -> Optional[float]:
    """Evaluate a PARAMETRIC_FORM expression. Returns None on any
    error or non-finite result."""
    try:
        code = compile(form_src, "<screen_sign_form>", "eval")
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
    except Exception:                                                   # noqa: BLE001
        return None
    if v is None: return None
    try: vf = float(v)
    except (TypeError, ValueError): return None
    if math.isnan(vf) or math.isinf(vf): return None
    return vf


def evaluate_screen_sign(
    form_src: str,
    fitted_params: dict,
    *,
    project_dir: Path,
    rubric_data: dict,
    split_class: str = "cluster",
    split_feature: str = "radius_log10",
    split_threshold: Optional[float] = None,
    min_rows_per_half: int = 5,
) -> dict:
    """Evaluate the screen-sign test on the fitted form.

    Loads the substrate CSV, filters to `split_class` rows, splits by
    `split_feature` at `split_threshold` (or the class-median if
    threshold is None), evaluates the form on each half, computes mean
    MRE per half, returns the inner-vs-outer comparison.

    Verdict:
      "wrong_sign"   — inner_mean > outer_mean: form fits diffuse
                       outer regions better than dense inner regions.
                       Wrong direction for chameleon screening.
      "ok"           — inner_mean <= outer_mean: form fits dense inner
                       regions at least as well as diffuse outer
                       regions. Direction-consistent with chameleon.
      "insufficient_rows" — fewer than min_rows_per_half on either side.
      "not_enabled"  — rubric did not enable the check.
    """
    if not bool(rubric_data.get("enable_screen_sign_check", False)):
        return {
            "gate_id": GATE_ID, "verdict": "not_enabled",
            "reason": "rubric.enable_screen_sign_check is false; gate skipped",
            "inner_n": 0, "outer_n": 0,
            "inner_mean_mre": None, "outer_mean_mre": None,
            "split_class": split_class, "split_feature": split_feature,
            "split_threshold": split_threshold,
        }

    # Load substrate via the project's features.py (same surface the
    # apparatus's fit_features sees). Fall back to direct CSV read if
    # features.py is missing or unimportable. The features.py output
    # carries the apparatus-canonical aliases (e.g., `radius_log10`),
    # so forms written against those names evaluate correctly here.
    class_key = rubric_data.get("substrate_class_key", "system_class")
    # Substrate class normalization: features.py outputs single-letter
    # codes (A/B/C/D/N/S) per the substrate convention; readable names
    # ("cluster", "wide_binary_banik2024", ...) appear in raw CSVs.
    # Accept both forms.
    _CLASS_ALIASES = {
        "cluster": ("B", "cluster"),
        "B": ("B", "cluster"),
        "binary": ("C", "binary"),
        "C": ("C", "binary"),
        "wide_binary_banik2024": ("N", "wide_binary_banik2024"),
        "N": ("N", "wide_binary_banik2024"),
        "dwarf_spheroidal": ("D", "dwarf_spheroidal"),
        "D": ("D", "dwarf_spheroidal"),
        "solar_system": ("S", "solar_system"),
        "S": ("S", "solar_system"),
        "disk": ("A", "disk"),
        "A": ("A", "disk"),
    }
    accepted_class_values = set(_CLASS_ALIASES.get(split_class, (split_class,)))
    rows = []
    feat_path = project_dir / "features.py"
    used_features_module = False
    if feat_path.exists():
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location("_screen_sign_features", str(feat_path))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Aggregate over visible + holdout + farther-tail rows.
            # Class B (cluster), C, D, N typically live in
            # farther_tail_rows; Class A in visible. Different
            # substrates may shape these differently — we union all
            # accessors and filter by class_key.
            all_entries = []
            for accessor_name in ("visible_rows", "holdout_rows", "farther_tail_rows", "audit_rows"):
                fn = getattr(mod, accessor_name, None)
                if callable(fn):
                    try:
                        all_entries.extend(fn())
                    except Exception:                                   # noqa: BLE001
                        continue
            for entry in all_entries:
                if not (isinstance(entry, tuple) and len(entry) == 3):
                    continue
                _id, y_obs, feats = entry
                if not isinstance(feats, dict):
                    continue
                if feats.get(class_key) not in accepted_class_values:
                    continue
                row = dict(feats)
                if y_obs is not None:
                    row["y_true"] = float(y_obs)
                if split_feature not in row:
                    continue
                rows.append(row)
            used_features_module = True
        except Exception:                                               # noqa: BLE001
            rows = []  # fall through to CSV path
    if not used_features_module:
        # CSV fallback
        raw_dir = project_dir / "raw"
        csv_files = list(raw_dir.glob("unified_*.csv")) if raw_dir.exists() else []
        if not csv_files:
            csv_files = list(raw_dir.glob("*.csv")) if raw_dir.exists() else []
        if not csv_files:
            return {
                "gate_id": GATE_ID, "verdict": "insufficient_rows",
                "reason": f"no features.py and no substrate CSV found under {project_dir}",
                "inner_n": 0, "outer_n": 0,
                "inner_mean_mre": None, "outer_mean_mre": None,
                "split_class": split_class, "split_feature": split_feature,
                "split_threshold": split_threshold,
            }
        csv_path = max(csv_files, key=lambda p: p.stat().st_mtime)
        with csv_path.open() as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                if r.get(class_key) not in accepted_class_values:
                    continue
                row: dict[str, Any] = {}
                for k, v in r.items():
                    if v in (None, ""):
                        continue
                    try:
                        row[k] = float(v)
                    except (ValueError, TypeError):
                        continue
                if "g_bar" in row: row["x"] = row["g_bar"]
                if "g_obs" in row: row["y_true"] = row["g_obs"]
                if split_feature not in row:
                    continue
                rows.append(row)
    if len(rows) < 2 * min_rows_per_half:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_rows",
            "reason": f"only {len(rows)} {split_class} rows; need ≥{2*min_rows_per_half}",
            "inner_n": 0, "outer_n": 0,
            "inner_mean_mre": None, "outer_mean_mre": None,
            "split_class": split_class, "split_feature": split_feature,
            "split_threshold": split_threshold,
        }

    # Split threshold: use class median if not explicit
    if split_threshold is None:
        vals = sorted(r[split_feature] for r in rows)
        split_threshold = vals[len(vals) // 2]

    inner = [r for r in rows if r[split_feature] < split_threshold]
    outer = [r for r in rows if r[split_feature] >= split_threshold]
    if len(inner) < min_rows_per_half or len(outer) < min_rows_per_half:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_rows",
            "reason": f"split produced inner={len(inner)} outer={len(outer)}; need ≥{min_rows_per_half} each",
            "inner_n": len(inner), "outer_n": len(outer),
            "inner_mean_mre": None, "outer_mean_mre": None,
            "split_class": split_class, "split_feature": split_feature,
            "split_threshold": split_threshold,
        }

    def _mre_mean(subset):
        mres = []
        for r in subset:
            v = _safe_eval(form_src, r, fitted_params)
            if v is None or v <= 0: continue
            y = r.get("y_true") or r.get("g_obs")
            if y is None or y <= 0: continue
            mres.append(abs(v - y) / max(abs(y), 1e-30))
        return (sum(mres) / len(mres) if mres else None, len(mres))

    inner_mean, inner_n = _mre_mean(inner)
    outer_mean, outer_n = _mre_mean(outer)
    if inner_mean is None or outer_mean is None:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_rows",
            "reason": "form did not produce evaluable predictions on enough rows",
            "inner_n": inner_n, "outer_n": outer_n,
            "inner_mean_mre": inner_mean, "outer_mean_mre": outer_mean,
            "split_class": split_class, "split_feature": split_feature,
            "split_threshold": split_threshold,
        }

    # Wrong-sign: inner (dense) MRE > outer (diffuse) MRE
    if inner_mean > outer_mean:
        return {
            "gate_id": GATE_ID, "verdict": "wrong_sign",
            "reason": (
                f"chameleon-screening claim falsified: inner-{split_class} "
                f"mean MRE {inner_mean:.3f} > outer-{split_class} mean MRE "
                f"{outer_mean:.3f} (split: {split_feature} ≷ {split_threshold:.2f}). "
                f"A real chameleon should fit dense regions better than "
                f"diffuse regions; this form does the opposite."
            ),
            "inner_n": inner_n, "outer_n": outer_n,
            "inner_mean_mre": inner_mean, "outer_mean_mre": outer_mean,
            "split_class": split_class, "split_feature": split_feature,
            "split_threshold": split_threshold,
        }
    return {
        "gate_id": GATE_ID, "verdict": "ok",
        "reason": (
            f"screen-sign direction-consistent: inner-{split_class} "
            f"mean MRE {inner_mean:.3f} ≤ outer-{split_class} mean MRE "
            f"{outer_mean:.3f}"
        ),
        "inner_n": inner_n, "outer_n": outer_n,
        "inner_mean_mre": inner_mean, "outer_mean_mre": outer_mean,
        "split_class": split_class, "split_feature": split_feature,
        "split_threshold": split_threshold,
    }
