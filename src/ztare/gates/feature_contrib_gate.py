"""G-FEATURE-CONTRIB — flag cosmetic features whose ablation contributes
< threshold (default 5%) to the fit's mean relative error.

Companion to G-LAGRANGIAN-NONTRIVIAL (B1) and G-SCREEN-SIGN (B2). Where
B1 catches Lagrangians that collapse to single-symbol substitution, this
gate catches PARAMETRIC_FORMs that NAME a substrate feature (e.g.,
`sigma`, `gas_fraction`, `g_external`) but use it cosmetically — the
fit MRE barely degrades when the feature is replaced by its class-median
value (effectively ablating it from the form).

Why a separate gate from B1:
  * B1 audits the Lagrangian's symbolic content
  * B3 audits the fitted form's *empirical* dependence on each declared
    feature. A form can declare `sigma` in BACKGROUND and use it in the
    Lagrangian, yet still have negligible empirical contribution because
    the fitted parameter coefficient is near zero or because sigma is
    multiplied by a vanishing factor in the relevant regime.

GP-183 Phase B3.

Verdict:
  "ok"               — every declared feature contributes ≥ threshold
                       (default 0.05 = 5%) ΔMRE under ablation.
  "cosmetic_features" — at least one feature contributes < threshold;
                       payload includes the per-feature ΔMRE list.
  "not_enabled"      — rubric did not enable the check.
  "insufficient_data" — substrate could not be loaded or the form failed
                       to evaluate.

Output schema:
  {
    "gate_id": "G-FEATURE-CONTRIB",
    "verdict": "ok" | "cosmetic_features" | "not_enabled" | "insufficient_data",
    "reason": str,
    "baseline_mre": float | None,
    "threshold": float,
    "per_feature_contrib": [
        {"feature": "sigma", "ablation_mre": 0.219, "delta_mre": 0.003,
         "contribution_fraction": 0.014, "cosmetic": True}, ...
    ] | [],
    "n_rows_evaluated": int,
  }

Activated only when rubric.enable_feature_contrib_check=true. The
apparatus caps at rubric.cap_for_cosmetic_features (default 60) with
reason `cosmetic_features_detected` when the gate fires.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Any, Optional

GATE_ID = "G-FEATURE-CONTRIB"


# ── Safe-eval (mirrors B2 screen_sign_gate's environment) ──────────


def _safe_eval(form_src: str, features: dict, params: dict) -> Optional[float]:
    """Evaluate a PARAMETRIC_FORM expression; return None on any error
    or non-finite result. Mirrors the screen_sign_gate environment for
    consistency across the apparatus's gate stack."""
    try:
        code = compile(form_src, "<feature_contrib_form>", "eval")
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


# ── Substrate row loading (mirrors B2 helper) ──────────────────────


def _load_substrate_rows(project_dir: Path, class_key: str = "system_class") -> list[dict]:
    """Aggregate (id, y_true, features) rows from features.py. Falls back
    to the most recent CSV under raw/ if features.py is unavailable."""
    feat_path = project_dir / "features.py"
    rows: list[dict] = []
    if feat_path.exists():
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location("_feat_contrib_features", str(feat_path))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            all_entries = []
            for accessor in ("visible_rows", "holdout_rows", "farther_tail_rows", "audit_rows"):
                fn = getattr(mod, accessor, None)
                if callable(fn):
                    try:
                        all_entries.extend(fn())
                    except Exception:                                       # noqa: BLE001
                        continue
            for entry in all_entries:
                if not (isinstance(entry, tuple) and len(entry) == 3):
                    continue
                _id, y_obs, feats = entry
                if not isinstance(feats, dict):
                    continue
                row = dict(feats)
                if y_obs is not None:
                    row["y_true"] = float(y_obs)
                rows.append(row)
            return rows
        except Exception:                                                   # noqa: BLE001
            rows = []
    # CSV fallback
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


# ── Feature extraction from PARAMETRIC_FORM ────────────────────────


_FEATURE_RE = re.compile(r"features\s*\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]")


def _extract_referenced_features(form_src: str) -> list[str]:
    """Extract the set of features['<name>'] references in the form,
    deduplicated and stable-ordered. We only ablate features the form
    EXPLICITLY references; declared-but-unreferenced features in
    BACKGROUND are not testable here (they are caught by R10/R11)."""
    if not form_src:
        return []
    names: list[str] = []
    seen: set[str] = set()
    for m in _FEATURE_RE.finditer(form_src):
        n = m.group(1)
        if n not in seen and n != "x":  # 'x' is the primary fitting axis; never ablate
            seen.add(n)
            names.append(n)
    return names


# ── Core evaluation ────────────────────────────────────────────────


def _per_row_relative_error(
    form_src: str, fitted_params: dict, rows: list[dict],
) -> tuple[float, int]:
    """Mean relative error of the form on rows, and number of valid rows."""
    rel_errs: list[float] = []
    for row in rows:
        y_true = row.get("y_true")
        if y_true is None or not isinstance(y_true, (int, float)) or y_true <= 0:
            continue
        # Build features dict expected by the form
        feats = {k: v for k, v in row.items() if k != "y_true"}
        y_pred = _safe_eval(form_src, feats, fitted_params)
        if y_pred is None:
            continue
        rel_errs.append(abs(y_pred - float(y_true)) / abs(float(y_true)))
    if not rel_errs:
        return float("nan"), 0
    return sum(rel_errs) / len(rel_errs), len(rel_errs)


def _ablate_feature(rows: list[dict], feature_name: str) -> list[dict]:
    """Return a copy of rows where `feature_name` is replaced by its
    finite-row median across the substrate. Median (not mean) because
    several substrate columns are heavy-tailed; median ablation is a
    cleaner null than mean ablation."""
    vals = [row[feature_name] for row in rows
            if isinstance(row.get(feature_name), (int, float))
            and math.isfinite(row[feature_name])]
    if not vals:
        # Cannot ablate — feature is missing or all non-finite
        return rows
    sorted_vals = sorted(vals)
    median = sorted_vals[len(sorted_vals) // 2]
    out: list[dict] = []
    for row in rows:
        new_row = dict(row)
        new_row[feature_name] = median
        out.append(new_row)
    return out


def evaluate_feature_contrib(
    form_src: str,
    fitted_params: dict,
    *,
    project_dir: Path,
    rubric_data: dict,
    threshold: Optional[float] = None,
) -> dict:
    """Run the feature-contribution audit on the fitted form.

    For each feature explicitly referenced by `features['<name>']` in
    PARAMETRIC_FORM, replace that feature with its substrate-wide median
    and recompute the form's mean relative error. The ΔMRE = ablated -
    baseline measures how much that feature contributes to the fit.

    Features with ΔMRE < threshold (default 0.05) are flagged cosmetic.
    """
    if not bool(rubric_data.get("enable_feature_contrib_check", False)):
        return {
            "gate_id": GATE_ID, "verdict": "not_enabled",
            "reason": "rubric.enable_feature_contrib_check is false; gate skipped",
            "baseline_mre": None, "threshold": threshold or 0.05,
            "per_feature_contrib": [], "n_rows_evaluated": 0,
        }

    if threshold is None:
        threshold = float(rubric_data.get("feature_contrib_threshold", 0.05))

    if not form_src:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": "no PARAMETRIC_FORM string supplied",
            "baseline_mre": None, "threshold": threshold,
            "per_feature_contrib": [], "n_rows_evaluated": 0,
        }

    referenced = _extract_referenced_features(form_src)
    if not referenced:
        # Form references no features beyond `x`; nothing to ablate.
        # That's "ok" by definition — the form's feature footprint is
        # already minimal.
        return {
            "gate_id": GATE_ID, "verdict": "ok",
            "reason": (
                "PARAMETRIC_FORM references only the primary fitting axis "
                "`features['x']`; no auxiliary features to ablate."
            ),
            "baseline_mre": None, "threshold": threshold,
            "per_feature_contrib": [], "n_rows_evaluated": 0,
        }

    rows = _load_substrate_rows(project_dir, rubric_data.get("substrate_class_key", "system_class"))
    if not rows:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": f"no substrate rows loaded from {project_dir}",
            "baseline_mre": None, "threshold": threshold,
            "per_feature_contrib": [], "n_rows_evaluated": 0,
        }

    baseline_mre, n_rows = _per_row_relative_error(form_src, fitted_params, rows)
    if not math.isfinite(baseline_mre) or n_rows < 10:
        return {
            "gate_id": GATE_ID, "verdict": "insufficient_data",
            "reason": f"baseline MRE could not be computed reliably (n={n_rows})",
            "baseline_mre": None, "threshold": threshold,
            "per_feature_contrib": [], "n_rows_evaluated": n_rows,
        }

    per_feature: list[dict] = []
    cosmetic_count = 0
    for feature in referenced:
        ablated_rows = _ablate_feature(rows, feature)
        ablated_mre, _ = _per_row_relative_error(form_src, fitted_params, ablated_rows)
        if not math.isfinite(ablated_mre):
            per_feature.append({
                "feature": feature,
                "ablation_mre": None,
                "delta_mre": None,
                "contribution_fraction": None,
                "cosmetic": False,  # cannot judge → not flagged
                "note": "ablation produced non-finite MRE; gate cannot judge contribution",
            })
            continue
        delta = ablated_mre - baseline_mre
        contrib_fraction = delta / max(abs(baseline_mre), 1e-30)
        is_cosmetic = bool(delta < threshold)
        if is_cosmetic:
            cosmetic_count += 1
        per_feature.append({
            "feature": feature,
            "ablation_mre": float(ablated_mre),
            "delta_mre": float(delta),
            "contribution_fraction": float(contrib_fraction),
            "cosmetic": is_cosmetic,
        })

    if cosmetic_count > 0:
        cosmetic_names = [e["feature"] for e in per_feature if e.get("cosmetic")]
        reason = (
            f"{cosmetic_count} of {len(per_feature)} declared feature(s) "
            f"contribute < {threshold:.3f} ΔMRE under median-ablation: "
            f"{cosmetic_names}. The form names these features but its "
            f"empirical fit barely changes when they are replaced by "
            f"their class-median value, indicating cosmetic dependence "
            f"rather than decision-critical structural use. A real Lagrangian "
            f"derivation should produce a form where every named feature "
            f"has measurable empirical content."
        )
        verdict = "cosmetic_features"
    else:
        reason = (
            f"all {len(per_feature)} referenced feature(s) contribute "
            f"≥ {threshold:.3f} ΔMRE under median-ablation; the form's "
            f"feature footprint is empirically decision-critical."
        )
        verdict = "ok"

    return {
        "gate_id": GATE_ID, "verdict": verdict,
        "reason": reason,
        "baseline_mre": float(baseline_mre),
        "threshold": float(threshold),
        "per_feature_contrib": per_feature,
        "n_rows_evaluated": n_rows,
    }
