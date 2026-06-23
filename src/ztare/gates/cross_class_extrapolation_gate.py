"""Cross-class extrapolation and per-class holdout gates (R10/R11).

Replaces the manual backtest workflow (load champion form, fit on visible,
evaluate on held-out, compute per-class Spearman residual-vs-feature,
identify in-range vs out-of-range subsets) with a deterministic gate
that runs every iter automatically.

Closes the gap we found analyzing gp163d iter 3 vs iter 5: iter 5's
score-100 form was a kernel hack disguised as a smooth function. Iter 3
was the real Hypothesis-S form. The combined-class farther-tail gate
let iter 5 win because Class B's 84 rows averaged Class C's failure.
The Spearman test on per-class residuals would have flagged iter 5's
flat residual structure (kernel hits Class B at one mass=14.5 point;
within-Class-B radius variance is uncorrelated with error) versus
iter 3's gradient structure (within-Class-B errors correlate with
radius, signature of a real bridge feature).

Two gates:

  R10 — Cross-Class Extrapolation Diagnostic (POST_FIT):
    For each held-out class, computes:
      - MRE
      - Spearman correlation between per-row error and primary feature
      - In-feature-range MRE (rows with feature within visible range)
      - Out-of-feature-range MRE (rows extrapolating)
    Flags MAGNITUDE_COINCIDENCE when in-range MRE > out-of-range MRE
    on a held-out class — that pattern indicates the form is doing
    magnitude-matching not feature-coupling. Does NOT auto-fail; surfaces
    the diagnostic to the briefing for the next iter.

  R11 — Per-Class MRE Ceiling (PRE_JUDGE):
    Replaces aggregated farther-tail MRE with per-class enforcement.
    Each held-out class must independently satisfy MRE < threshold.
    Default threshold inherited from rubric.farther_tail_threshold;
    can be overridden per-class via rubric.per_class_thresholds.
    Hard-fails the iter when any held-out class exceeds its ceiling.

Both gates are apparatus-general (not gp163d-specific). Any multi-class
substrate benefits.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# ── shared helpers ────────────────────────────────────────────────────


def _spearman_safe(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Spearman correlation + p-value. Returns (rho, p) or (nan, nan)
    when the input is degenerate. No scipy dependency at module top so the
    gate works in environments where scipy is unavailable."""
    if len(xs) != len(ys) or len(xs) < 4:
        return float("nan"), float("nan")
    try:
        from scipy.stats import spearmanr  # type: ignore
        res = spearmanr(xs, ys)
        return float(res.correlation), float(res.pvalue)
    except Exception:
        # Fallback: rank-based pearson without p-value
        rx = _ranks(xs)
        ry = _ranks(ys)
        n = len(rx)
        mx = sum(rx) / n
        my = sum(ry) / n
        cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / n
        sx = math.sqrt(sum((a - mx) ** 2 for a in rx) / n)
        sy = math.sqrt(sum((b - my) ** 2 for b in ry) / n)
        if sx == 0 or sy == 0:
            return 0.0, float("nan")
        return cov / (sx * sy), float("nan")


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    for rank, idx in enumerate(indexed, 1):
        out[idx] = float(rank)
    return out


def _safe_mre(yhat: list[float], y: list[float]) -> tuple[float, int]:
    pairs = [
        (h, t) for h, t in zip(yhat, y)
        if math.isfinite(h) and math.isfinite(t) and t != 0
    ]
    if not pairs:
        return float("nan"), 0
    return (
        sum(abs(h - t) / abs(t) for h, t in pairs) / len(pairs),
        len(pairs),
    )


# ── R10 — Cross-Class Extrapolation Diagnostic ────────────────────────


@dataclass
class CrossClassDiagnostic:
    per_class_mre: dict[str, float] = field(default_factory=dict)
    per_class_n: dict[str, int] = field(default_factory=dict)
    per_class_spearman: dict[str, dict[str, float]] = field(default_factory=dict)
    in_range_subset_mre: dict[str, Optional[float]] = field(default_factory=dict)
    out_of_range_subset_mre: dict[str, Optional[float]] = field(default_factory=dict)
    flags: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "per_class_mre": self.per_class_mre,
            "per_class_n": self.per_class_n,
            "per_class_spearman": self.per_class_spearman,
            "in_range_subset_mre": self.in_range_subset_mre,
            "out_of_range_subset_mre": self.out_of_range_subset_mre,
            "flags": self.flags,
        }


def run_cross_class_diagnostic(
    *,
    visible_features: list[dict],
    farther_features: list[dict],
    farther_y: list[float],
    farther_yhat: list[float],
    primary_feature_key: str,
    class_key: str,
) -> CrossClassDiagnostic:
    """Compute R10 diagnostic.

    Args:
        visible_features: feature dicts the form was fit on.
        farther_features: feature dicts of held-out (farther-tail) rows.
        farther_y: observed targets for held-out rows.
        farther_yhat: predictions on held-out rows.
        primary_feature_key: the feature key the form's bridge is supposed
            to act through (e.g. 'radius_log10' for gp163d).
        class_key: the categorical key partitioning rows into classes
            (e.g. 'system_class' for gp163d).

    Returns:
        CrossClassDiagnostic with per-class metrics and flags. Does not
        raise; this is a non-blocking diagnostic.
    """
    diag = CrossClassDiagnostic()
    if not farther_features or not farther_y or not farther_yhat:
        return diag
    if len({len(farther_features), len(farther_y), len(farther_yhat)}) != 1:
        return diag

    # Visible feature range (training support for the bridge)
    vis_feat = [
        f.get(primary_feature_key) for f in visible_features
        if isinstance(f.get(primary_feature_key), (int, float))
        and not (isinstance(f.get(primary_feature_key), float)
                 and math.isnan(f[primary_feature_key]))
    ]
    if not vis_feat:
        return diag
    vis_min, vis_max = min(vis_feat), max(vis_feat)

    # Per-class loop
    by_class: dict[str, list[int]] = {}
    for i, f in enumerate(farther_features):
        cls = f.get(class_key)
        if cls is None:
            continue
        by_class.setdefault(str(cls), []).append(i)

    for cls, idxs in by_class.items():
        yh = [farther_yhat[i] for i in idxs]
        y = [farther_y[i] for i in idxs]
        feat_vals = [farther_features[i].get(primary_feature_key) for i in idxs]
        feat_numeric = [
            v for v in feat_vals
            if isinstance(v, (int, float))
            and not (isinstance(v, float) and math.isnan(v))
        ]

        cls_mre, cls_n = _safe_mre(yh, y)
        diag.per_class_mre[cls] = cls_mre
        diag.per_class_n[cls] = cls_n

        # Spearman: per-row absolute error vs primary feature value
        if len(feat_numeric) == len(yh) >= 4:
            errs = [
                abs(h - t) / abs(t) if (math.isfinite(h) and math.isfinite(t) and t != 0) else float("nan")
                for h, t in zip(yh, y)
            ]
            valid = [
                (e, v) for e, v in zip(errs, feat_vals)
                if math.isfinite(e)
                and isinstance(v, (int, float))
                and not (isinstance(v, float) and math.isnan(v))
            ]
            if len(valid) >= 4:
                rho, p = _spearman_safe(
                    [e for e, _ in valid], [v for _, v in valid]
                )
                diag.per_class_spearman[cls] = {"rho": rho, "p": p, "n": len(valid)}

        # In-range vs out-of-range subset MRE
        in_range_yh, in_range_y = [], []
        out_yh, out_y = [], []
        for i, idx in enumerate(idxs):
            v = farther_features[idx].get(primary_feature_key)
            h = farther_yhat[idx]
            t = farther_y[idx]
            if not isinstance(v, (int, float)):
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            if vis_min <= v <= vis_max:
                in_range_yh.append(h); in_range_y.append(t)
            else:
                out_yh.append(h); out_y.append(t)

        if in_range_yh:
            mre_in, _ = _safe_mre(in_range_yh, in_range_y)
            diag.in_range_subset_mre[cls] = mre_in
        else:
            diag.in_range_subset_mre[cls] = None
        if out_yh:
            mre_out, _ = _safe_mre(out_yh, out_y)
            diag.out_of_range_subset_mre[cls] = mre_out
        else:
            diag.out_of_range_subset_mre[cls] = None

        # Flag MAGNITUDE_COINCIDENCE when in-range performs WORSE than out-of-range
        # on a held-out class. A real bridge would predict best on overlap and
        # degrade on extrapolation; the inverse pattern is the signature of
        # magnitude-coincidence (the form's exponent happens to land in the
        # right magnitude range but the within-class feature gradient is wrong).
        if (diag.in_range_subset_mre[cls] is not None
                and diag.out_of_range_subset_mre[cls] is not None
                and diag.in_range_subset_mre[cls]
                > diag.out_of_range_subset_mre[cls] * 1.10):
            diag.flags.append({
                "kind": "magnitude_coincidence",
                "class": cls,
                "in_range_mre": diag.in_range_subset_mre[cls],
                "out_of_range_mre": diag.out_of_range_subset_mre[cls],
                "implication": (
                    f"Held-out class {cls!r} has WORSE MRE within the visible "
                    f"feature range than outside it. A real bridge feature "
                    f"would predict best on overlap. The inverse pattern is "
                    f"the signature of magnitude-coincidence: the form's "
                    f"functional shape lands in the right magnitude range "
                    f"on this class but the within-class gradient is wrong. "
                    f"Treat the score on this class as a calibration coincidence "
                    f"rather than a discovered bridge."
                ),
            })

        # Flag KERNEL_CAMOUFLAGE_RH18 when per-class Spearman is near zero
        # AND the per-class MRE is good — that combination suggests the form
        # is hitting the class via a magnitude constant, not via the feature.
        sp = diag.per_class_spearman.get(cls)
        if (sp and sp["n"] >= 4 and abs(sp["rho"]) < 0.15
                and cls_mre < 0.5):
            diag.flags.append({
                "kind": "kernel_camouflage_rh18_candidate",
                "class": cls,
                "spearman_rho": sp["rho"],
                "spearman_n": sp["n"],
                "class_mre": cls_mre,
                "implication": (
                    f"Class {cls!r} has good MRE ({cls_mre:.3f}) but "
                    f"per-row error is uncorrelated with {primary_feature_key} "
                    f"(rho={sp['rho']:+.3f}, n={sp['n']}). RH-18 candidate: "
                    f"the form may be hitting this class via a constant offset "
                    f"or hardcoded kernel rather than via a feature-driven "
                    f"continuous law. Check PARAMETRIC_FORM for hardcoded "
                    f"constants matching this class's feature centroid."
                ),
            })

    return diag


# ── R11 — Per-Class MRE Ceiling ──────────────────────────────────────


@dataclass
class PerClassCeilingResult:
    per_class_mre: dict[str, float] = field(default_factory=dict)
    per_class_passed: dict[str, bool] = field(default_factory=dict)
    threshold_used: dict[str, float] = field(default_factory=dict)
    overall_passed: bool = True
    failed_classes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "per_class_mre": self.per_class_mre,
            "per_class_passed": self.per_class_passed,
            "threshold_used": self.threshold_used,
            "overall_passed": self.overall_passed,
            "failed_classes": self.failed_classes,
        }


# ── R10 + R11 Cage adapters (can_handle predicates + run() signatures) ──


def r10_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """R10 engages when the substrate has multi-class held-out rows AND
    declares a primary feature key for the bridge.

    Reads substrate.meta (cage_meta) and rubric_flags. Substrate-agnostic
    in the sense that it routes by data shape, not by substrate name.
    """
    meta = getattr(substrate, "meta", {}) or {}
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    cage_class = str(meta.get("class", "") or "").strip().lower()
    if cage_class not in {"nd_features", "time_series"}:
        return False, (
            f"Cross-class extrapolation diagnostic (R10) skipped: "
            f"cage_meta.class={cage_class!r} is not "
            f"in {{nd_features, time_series}}; cross-class diagnostic "
            f"only meaningful for multi-class substrates."
        )
    primary_key = rubric.get("framer_primary_feature_key")
    if not primary_key:
        return False, (
            "Cross-class extrapolation diagnostic (R10) skipped: "
            "rubric.framer_primary_feature_key not declared. "
            "The diagnostic needs a designated bridge feature to compute "
            "Spearman(per-row error, primary feature) within each class."
        )
    class_key = rubric.get("substrate_class_key")
    if not class_key:
        return False, (
            "Cross-class extrapolation diagnostic (R10) skipped: "
            "rubric.substrate_class_key not declared. "
            "The diagnostic needs a categorical key to partition held-out rows."
        )
    farther_count = int(getattr(candidate, "farther_tail_row_count", 0))
    if farther_count < 4:
        return False, (
            f"Cross-class extrapolation diagnostic (R10) skipped: "
            f"only {farther_count} held-out rows; "
            f"per-class diagnostic needs ≥4 rows per class for Spearman."
        )
    return True, "Cross-class extrapolation diagnostic (R10) engaged"


def r10_run(substrate: Any, candidate: Any) -> CrossClassDiagnostic:
    """Cage `run` adapter for R10. Pulls inputs from candidate context."""
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    return run_cross_class_diagnostic(
        visible_features=candidate.visible_features,
        farther_features=candidate.farther_features,
        farther_y=candidate.farther_y,
        farther_yhat=candidate.farther_yhat,
        primary_feature_key=str(rubric["framer_primary_feature_key"]),
        class_key=str(rubric["substrate_class_key"]),
    )


def r11_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """R11 engages when R10 conditions are met AND the rubric explicitly
    opts in via `enforce_per_class_farther_tail: true`. The opt-in flag
    is required during the validation window (R11 is hard-fail; default
    on would break existing runs)."""
    ok, reason = r10_can_handle(substrate, candidate)
    if not ok:
        return False, (
            "Per-class holdout ceiling (R11) skipped: "
            f"cross-class prerequisites failed — {reason}"
        )
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enforce_per_class_farther_tail", False)):
        return False, (
            "Per-class holdout ceiling (R11) skipped: "
            "rubric.enforce_per_class_farther_tail is not true. "
            "R11 is hard-fail; opt-in flag required during validation "
            "window. Cross-class diagnostic (R10) still runs."
        )
    return True, "Per-class holdout ceiling (R11) engaged"


def r11_run(substrate: Any, candidate: Any) -> PerClassCeilingResult:
    """Cage `run` adapter for R11."""
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    excluded = set(rubric.get("r11_excluded_classes", []) or [])
    overrides = rubric.get("per_class_thresholds")
    threshold = float(rubric.get("farther_tail_threshold", 0.5))
    return per_class_mre_ceiling(
        farther_features=candidate.farther_features,
        farther_y=candidate.farther_y,
        farther_yhat=candidate.farther_yhat,
        class_key=str(rubric["substrate_class_key"]),
        default_threshold=threshold,
        per_class_thresholds=overrides,
        excluded_classes=excluded,
    )


def dispatch_r10_r11_from_harness_json(
    project_dir: Path,
    rubric_data: dict,
    iter_index: int,
) -> dict:
    """One-call wire-in for autoresearch_loop. Reads workspace/gate_harness_result.json
    + features.py, runs R10 (non-blocking diagnostic) + R11 (hard-fail on per-class
    excess if rubric.enforce_per_class_farther_tail), writes diagnostic JSON, returns
    summary dict for embedding in eval payload + briefing.

    Returns dict with keys:
        - gate_aliases (legacy id -> human-readable gate name)
        - r10_engaged (bool)
        - r10_diagnostic (CrossClassDiagnostic.to_dict() or None)
        - r10_flags (list of flag dicts)
        - r11_engaged (bool)
        - r11_passed (bool)
        - r11_failed_classes (list)
        - r11_per_class_mre (dict)
        - error (str|None)
    """
    import json
    out: dict = {
        "gate_aliases": {
            "r10": "cross_class_extrapolation_diagnostic",
            "r11": "per_class_holdout_ceiling",
        },
        "r10_engaged": False, "r10_diagnostic": None, "r10_flags": [],
        "r11_engaged": False, "r11_passed": True, "r11_failed_classes": [],
        "r11_per_class_mre": {}, "error": None,
    }
    proj = Path(project_dir)
    cage_meta = rubric_data.get("cage_meta") or {}
    cage_class = str(cage_meta.get("class", "") if isinstance(cage_meta, dict) else "").strip().lower()
    if cage_class not in {"nd_features", "time_series"}:
        out["skipped_reason"] = (
            f"cage_meta.class={cage_class!r} is not a multi-class numeric substrate"
        )
        return out
    primary_key = rubric_data.get("framer_primary_feature_key")
    class_key = rubric_data.get("substrate_class_key")
    if not primary_key or not class_key:
        out["error"] = (
            "cross-class diagnostic requires framer_primary_feature_key "
            "and substrate_class_key in rubric"
        )
        return out
    harness_path = proj / "workspace" / "gate_harness_result.json"
    if not harness_path.exists():
        out["error"] = f"gate_harness_result.json not found at {harness_path}"
        return out
    try:
        harness_result = json.loads(harness_path.read_text(encoding="utf-8"))
    except Exception as exc:
        out["error"] = f"failed parsing gate_harness_result.json: {type(exc).__name__}: {exc}"
        return out

    # Pull farther_features + farther_y + farther_yhat from harness output.
    # The harness writes per-row records under farther_tail.records (with id, y_true,
    # y_pred). We need feature dicts; load via features.py at project_dir.
    import importlib.util as _ilu, sys as _sys
    feat_path = proj / "features.py"
    if not feat_path.exists():
        out["error"] = f"features.py not found at {feat_path}"
        return out
    spec = _ilu.spec_from_file_location("_r10_r11_features", str(feat_path))
    if spec is None or spec.loader is None:
        out["error"] = f"could not load spec from {feat_path}"
        return out
    if str(proj) not in _sys.path:
        _sys.path.insert(0, str(proj))
    try:
        feat_mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(feat_mod)
    except Exception as exc:
        out["error"] = f"failed importing features.py: {type(exc).__name__}: {exc}"
        return out

    visible = list(feat_mod.visible_rows()) if hasattr(feat_mod, "visible_rows") else []
    visible_features = [tup[2] for tup in visible if len(tup) >= 3]
    farther_records = (harness_result.get("farther_tail") or {}).get("records") or []
    farther_features: list = []
    farther_y: list = []
    farther_yhat: list = []
    FEATURES = getattr(feat_mod, "FEATURES", None)
    for rec in farther_records:
        rid = rec.get("id")
        y_true = rec.get("y_true")
        y_pred = rec.get("y_pred")
        if rid is None or y_true is None or y_pred is None:
            continue
        if FEATURES is not None and rid in FEATURES:
            f = FEATURES[rid]
        else:
            continue
        farther_features.append(f)
        farther_y.append(float(y_true))
        try:
            farther_yhat.append(float(y_pred))
        except (TypeError, ValueError):
            farther_yhat.append(float("nan"))

    # R10 always runs when held-out classes exist
    if farther_features and visible_features:
        try:
            diag = run_cross_class_diagnostic(
                visible_features=visible_features,
                farther_features=farther_features,
                farther_y=farther_y,
                farther_yhat=farther_yhat,
                primary_feature_key=str(primary_key),
                class_key=str(class_key),
            )
            out["r10_engaged"] = True
            out["r10_diagnostic"] = diag.to_dict()
            out["r10_flags"] = diag.flags
            r10_path = proj / "workspace" / f"cross_class_extrapolation_iter_{iter_index:03d}.json"
            r10_path.write_text(json.dumps(diag.to_dict(), indent=2), encoding="utf-8")
        except Exception as exc:
            out["error"] = (
                f"cross-class extrapolation diagnostic (R10) failed: "
                f"{type(exc).__name__}: {exc}"
            )

    # R11 runs only when rubric opts in
    if bool(rubric_data.get("enforce_per_class_farther_tail", False)) and farther_features:
        try:
            excluded = set(rubric_data.get("r11_excluded_classes") or [])
            overrides = rubric_data.get("per_class_thresholds")
            threshold = float(rubric_data.get("farther_tail_threshold", 0.5))
            res = per_class_mre_ceiling(
                farther_features=farther_features,
                farther_y=farther_y,
                farther_yhat=farther_yhat,
                class_key=str(class_key),
                default_threshold=threshold,
                per_class_thresholds=overrides,
                excluded_classes=excluded,
            )
            out["r11_engaged"] = True
            out["r11_passed"] = bool(res.overall_passed)
            out["r11_failed_classes"] = list(res.failed_classes)
            out["r11_per_class_mre"] = dict(res.per_class_mre)
            r11_path = proj / "workspace" / f"per_class_mre_ceiling_iter_{iter_index:03d}.json"
            r11_path.write_text(json.dumps(res.to_dict(), indent=2), encoding="utf-8")
        except Exception as exc:
            err_str = (
                f"per-class holdout ceiling (R11) failed: "
                f"{type(exc).__name__}: {exc}"
            )
            out["error"] = (out["error"] + "; " + err_str) if out["error"] else err_str
    return out


def register_cross_class_gates(cage: Any) -> None:
    """Register R10 + R11 with a Cage instance.

    Called at Cage construction (orchestrator/state.py::build_cage_runtime)
    so R10 and R11 are routed automatically based on substrate.meta and
    rubric flags rather than via autoresearch_loop direct-wire.

    Per GP-157 §3a (committed 2026-04-27): every new gate from R10
    onward MUST follow this pattern. Direct autoresearch_loop wire-in
    is forbidden for new gates.
    """
    try:
        from ztare.gates.cage import Gate
    except ImportError:
        return  # cage module unavailable; gates will be unreachable
    r10 = Gate(
        name="R10_cross_class_extrapolation",
        phase="POST_FIT",
        can_handle=r10_can_handle,
        run=r10_run,
        dependencies=[],
    )
    r11 = Gate(
        name="R11_per_class_mre_ceiling",
        phase="PRE_JUDGE",
        can_handle=r11_can_handle,
        run=r11_run,
        dependencies=["R10_cross_class_extrapolation"],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[r10.name] = r10
        cage.gates[r11.name] = r11
        # Invalidate topo cache so the new gates participate in dispatch
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None


def per_class_mre_ceiling(
    *,
    farther_features: list[dict],
    farther_y: list[float],
    farther_yhat: list[float],
    class_key: str,
    default_threshold: float = 0.5,
    per_class_thresholds: Optional[dict[str, float]] = None,
    excluded_classes: Optional[set[str]] = None,
) -> PerClassCeilingResult:
    """Compute per-class farther-tail MRE and check each independently.

    Replaces the combined-class MRE which lets a populous class average
    out a sparse class's blowup (gp163d Class B with 84 rows masking
    Class C's MRE=1.95 in iter 5).

    Args:
        farther_features: held-out feature dicts.
        farther_y: held-out targets.
        farther_yhat: predictions.
        class_key: categorical column for partitioning.
        default_threshold: MRE ceiling applied when no per-class override.
        per_class_thresholds: optional per-class overrides.
        excluded_classes: classes to omit entirely (e.g. classes flagged
            by substrate critic as poisoned by data artifacts; for
            gp163d this would include Class C deprojection).
    """
    res = PerClassCeilingResult()
    if not farther_features or not farther_y or not farther_yhat:
        return res
    excluded = excluded_classes or set()
    overrides = per_class_thresholds or {}

    by_class: dict[str, list[int]] = {}
    for i, f in enumerate(farther_features):
        cls = f.get(class_key)
        if cls is None:
            continue
        cls_str = str(cls)
        if cls_str in excluded:
            continue
        by_class.setdefault(cls_str, []).append(i)

    for cls, idxs in by_class.items():
        yh = [farther_yhat[i] for i in idxs]
        y = [farther_y[i] for i in idxs]
        mre, n = _safe_mre(yh, y)
        thr = float(overrides.get(cls, default_threshold))
        passed = math.isfinite(mre) and mre < thr
        res.per_class_mre[cls] = mre
        res.threshold_used[cls] = thr
        res.per_class_passed[cls] = passed
        if not passed:
            res.overall_passed = False
            res.failed_classes.append(cls)

    return res
