"""A4 — per_class_fit_audit_iter_NNN.json artifact writer.

Companion to A1 (lagrangian_derivation_iter), A2 (noether_nondegeneracy_iter),
A3 (gp180_telemetry_iter), A5 (cap_kind_iter). Produces a per-iter JSON
summarizing per-class fit quality from `fit_features_result.json`'s
`residual_by_category.system_class` block, plus a drift comparison vs the
prior iter's audit.

Why this exists separately from per_class_breakdown briefing:
  * The briefing provider renders Markdown FOR the mutator at iter N+1.
    A4 is structured JSON FOR audit, paper-7 §11.15.10 dark-dataset
    style cross-iter comparison, and post-run mining.
  * Per-iter persistence lets the operator answer "which iter shifted
    cluster B's residual structure?" without re-parsing fit_features.
  * Drift columns surface class-conditional residual instability before
    the operator notices it on a multi-iter time series.

Output schema (one row per class found in fit_features_result):

    {
        "class": "B",
        "n": 84,
        "mean_abs_residual": 1.23e-9,
        "max_abs_residual": 9.5e-9,
        "mean_relative_error": 0.216,
        "previous_iter": {
            "iter_index": 0,
            "mean_relative_error": 0.292,
            "mean_relative_error_drift": -0.076,
        } | null,
        "drift_severity": "improved" | "stable" | "regressed" | "first_iter",
    }

Top-level wrapper records iter_index, fit_features_result_hash, timestamp.

Mirrors the GP-180 dispatch's writeout pattern (write iter NNN file +
overwrite _latest.json so downstream tools have one stable handle).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Optional

ARTIFACT_PREFIX = "per_class_fit_audit_iter_"
LATEST_FILE = "per_class_fit_audit_latest.json"

# Drift thresholds for severity classification. These are heuristic; the
# rubric can override via `per_class_fit_audit.drift_threshold_*` keys.
_DEFAULT_IMPROVE_THRESHOLD = -0.02   # MRE drop ≥ 0.02 → improved
_DEFAULT_REGRESS_THRESHOLD = +0.02   # MRE rise ≥ 0.02 → regressed


def _safe_get(d: dict, key: str, default=None):
    """Dict.get with non-finite filtering for floats."""
    v = d.get(key, default)
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _stable_class_order(class_keys) -> list[str]:
    """Deterministic ordering: A, B, C, D, N, S, then anything else
    alphabetically. Matches paper 7 §11.15 reporting convention."""
    canonical = ["A", "B", "C", "D", "N", "S"]
    in_canon = [k for k in canonical if k in class_keys]
    extras = sorted(k for k in class_keys if k not in canonical)
    return in_canon + extras


def _hash_fit_result(fit_features_result: dict) -> str:
    """Stable hash of the fit result for cross-iter audit linkage."""
    canon = json.dumps(fit_features_result, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def _classify_drift(
    delta: Optional[float],
    improve_threshold: float = _DEFAULT_IMPROVE_THRESHOLD,
    regress_threshold: float = _DEFAULT_REGRESS_THRESHOLD,
) -> str:
    if delta is None:
        return "first_iter"
    if delta <= improve_threshold:
        return "improved"
    if delta >= regress_threshold:
        return "regressed"
    return "stable"


def build_per_class_fit_audit(
    fit_features_result: dict,
    *,
    iter_index_one_based: int,
    workspace_dir: Path,
    rubric_data: Optional[dict] = None,
) -> dict:
    """Construct the per-class fit audit dict from a fit_features_result.

    Reads `residual_by_category.system_class` for the per-class residual
    block, computes per-class MRE if not already present (uses
    mean_abs_residual / mean_y as a stand-in when the result didn't
    record per-class MRE directly), loads the prior iter's audit (if any)
    for drift comparison, returns the dict that will be persisted.

    The function does NOT touch the filesystem unless write_artifacts()
    is also called. This split lets callers test the data construction
    in isolation.
    """
    rubric_data = rubric_data or {}
    cfg = (rubric_data.get("per_class_fit_audit") or {}) if isinstance(rubric_data.get("per_class_fit_audit"), dict) else {}
    improve_threshold = float(cfg.get("drift_threshold_improve", _DEFAULT_IMPROVE_THRESHOLD))
    regress_threshold = float(cfg.get("drift_threshold_regress", _DEFAULT_REGRESS_THRESHOLD))

    rbc = (fit_features_result or {}).get("residual_by_category") or {}
    class_block = rbc.get("system_class") or {}

    # Prior iter for drift comparison (if it exists)
    prior_path = workspace_dir / LATEST_FILE
    prior_per_class: dict[str, Any] = {}
    prior_iter_index: Optional[int] = None
    if prior_path.exists():
        try:
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_iter_index = prior_data.get("iter_index")
            for entry in prior_data.get("per_class") or []:
                if "class" in entry:
                    prior_per_class[entry["class"]] = entry
        except Exception:                                                  # noqa: BLE001
            prior_per_class = {}

    per_class_entries: list[dict[str, Any]] = []
    for cls in _stable_class_order(list(class_block.keys())):
        block = class_block.get(cls) or {}
        n = int(block.get("n", 0)) if isinstance(block.get("n", 0), (int, float)) else 0
        mar = _safe_get(block, "mean_abs_residual")
        max_ar = _safe_get(block, "max_abs_residual")
        # Per-class MRE: prefer block-supplied, else derive from mean_abs_residual / mean_|y|.
        # fit_features_result may carry per-class MRE under various keys;
        # be tolerant of multiple shapes.
        mre = _safe_get(block, "mean_relative_error")
        if mre is None:
            mre = _safe_get(block, "mre")
        # Drift vs prior iter
        prior_entry = prior_per_class.get(cls) or {}
        prior_mre = _safe_get(prior_entry, "mean_relative_error")
        delta_mre: Optional[float] = None
        if mre is not None and prior_mre is not None:
            delta_mre = float(mre) - float(prior_mre)
        previous_block: Optional[dict[str, Any]] = None
        if prior_iter_index is not None:
            previous_block = {
                "iter_index": prior_iter_index,
                "mean_relative_error": prior_mre,
                "mean_relative_error_drift": delta_mre,
            }
        entry: dict[str, Any] = {
            "class": cls,
            "n": n,
            "mean_abs_residual": mar,
            "max_abs_residual": max_ar,
            "mean_relative_error": mre,
            "previous_iter": previous_block,
            "drift_severity": _classify_drift(
                delta_mre, improve_threshold, regress_threshold
            ),
        }
        per_class_entries.append(entry)

    # Top-level summary
    audit: dict[str, Any] = {
        "iter_index": iter_index_one_based,
        "fit_features_result_hash": _hash_fit_result(fit_features_result),
        "n_classes": len(per_class_entries),
        "per_class": per_class_entries,
        "fit_classification": _safe_get(fit_features_result, "classification"),
        "fit_pathological": bool(fit_features_result.get("pathological", False)),
        "fit_pathology_reason": _safe_get(fit_features_result, "pathology_reason"),
        "drift_thresholds": {
            "improve": improve_threshold,
            "regress": regress_threshold,
        },
    }

    # Aggregate drift counts for quick scanning
    drift_counts = {"improved": 0, "stable": 0, "regressed": 0, "first_iter": 0}
    for e in per_class_entries:
        drift_counts[e["drift_severity"]] = drift_counts.get(e["drift_severity"], 0) + 1
    audit["drift_summary"] = drift_counts

    return audit


def write_artifacts(audit: dict, workspace_dir: Path) -> dict[str, str]:
    """Persist iter NNN file + overwrite _latest.json. Returns paths."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    iter_index = int(audit["iter_index"])
    iter_path = workspace_dir / f"{ARTIFACT_PREFIX}{iter_index:03d}.json"
    latest_path = workspace_dir / LATEST_FILE
    payload = json.dumps(audit, indent=2, default=str)
    iter_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    return {"iter_path": str(iter_path), "latest_path": str(latest_path)}


def emit_per_class_fit_audit(
    fit_features_result: dict,
    *,
    iter_index_one_based: int,
    workspace_dir: Path,
    rubric_data: Optional[dict] = None,
) -> dict[str, Any]:
    """Build + persist in one call. Caller-friendly entry point."""
    audit = build_per_class_fit_audit(
        fit_features_result,
        iter_index_one_based=iter_index_one_based,
        workspace_dir=workspace_dir,
        rubric_data=rubric_data,
    )
    paths = write_artifacts(audit, workspace_dir)
    return {"audit": audit, "paths": paths}
