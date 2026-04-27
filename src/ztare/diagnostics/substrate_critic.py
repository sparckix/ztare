"""GP-167 SubstrateCritic — what the substrate shows, doesn't show, and
cannot constrain.

Inspired by the compile_evidence pattern that produces evidence packets
with `immutable_ground_truth`, `identified_contradictions`,
`epistemic_voids`, and `candidate_claims_to_test`. The same discipline
("preserve unresolved tension; surface what no source resolves") applied
to the substrate's structural state instead of external evidence.

Why this exists. The gp163d session showed that the apparatus had been
running blind on substrate-level structural facts that a human reading
the data would notice immediately:

  * Class A's mass_log10 has zero variance, so no fit using mass can be
    constrained from visible data alone — yet the apparatus repeatedly
    fitted forms with a free k_m parameter and watched scipy place it
    at -1.2 million.
  * Class C's y/x ratio is systematically below 1, a signature of the
    deprojection artifact in the underlying instrument; using class C
    as a farther-tail validation set was poisoning the test.
  * The cluster-class jump in c is discontinuous, not smooth, but the
    apparatus searched only smooth-scaling forms.

A human looking at the raw data with five minutes and pandas would have
flagged each of these. The apparatus did not. This module gives the
apparatus the same eye, deterministically and per-substrate, before
iter one and after each fit.

The output is a JSON artifact at `workspace/substrate_critique.json`
with the following sections (deliberately mirroring compile_evidence's
schema, applied to substrate state):

  * `substrate_invariants` — facts the data definitively shows. Stable
    statistics per visible class. Range and dispersion of each numeric
    feature. Rank correlation between features. These are the
    apparatus's ground truth about the data.
  * `feature_dimensionality_collapses` — features that have so little
    variance within the visible class that no fit using them as a
    free parameter can be constrained. The substrate-level analog of
    "your form has unconstrainable parameters."
  * `cross_class_signal` — for substrates with a withheld farther-tail
    class, the range overlap and ratio gap between visible and
    withheld classes. Tells the mutator which features carry
    extrapolation power and which do not.
  * `regime_breaks_in_data` — discontinuities detected in the raw data
    when sorted by primary feature, before any fit is attempted. These
    are structural, not residual; they signal that the substrate
    contains regime breaks the form must accommodate.
  * `data_artifacts_suspected` — quantitative tests for known instrument
    artifacts (e.g., y/x systematically below 1 for a class, suggesting
    projection effects; categorical-feature subgroups that fail basic
    sign or range sanity).
  * `epistemic_voids` — what the substrate cannot decide. The honest
    statement of identification limits given the visible data alone.
    These are the priority items for the operator: substrate
    enrichment, not apparatus tuning, is what would resolve them.

The module is self-contained. Pre-flight runs once before iter one and
writes the critique. Per-iter runs after each fit and refreshes the
sections that depend on the latest residuals (so per-iter
identifiability warnings stay current). A briefing provider surfaces
the verdict to the mutator. An optional LLM summary (gated on a rubric
flag) compresses the JSON into prose for the operator-facing audit
log. The operator can override or supplement any section by editing
`workspace/substrate_critique_overrides.json`, which gets merged on
top of the deterministic output — the same discipline as compile_evidence's
manual overrides.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ── Verdict object ─────────────────────────────────────────────────────


@dataclass
class SubstrateCritique:
    """The substrate-side analog of compile_evidence's evidence packet.

    Each section is a list of structured items so operators and briefing
    providers can render selectively. Empty lists are valid — the absence
    of a regime break or data artifact is itself information.
    """
    project: str = ""
    primary_feature_key: str = "x"
    n_visible_rows: int = 0
    classes_visible: list[str] = field(default_factory=list)
    classes_withheld: list[str] = field(default_factory=list)

    substrate_invariants: list[dict] = field(default_factory=list)
    feature_dimensionality_collapses: list[dict] = field(default_factory=list)
    cross_class_signal: list[dict] = field(default_factory=list)
    # 2026-04-26: G-CROSS-CLASS-FEATURE-SUPPORT — within-withheld-class
    # feature-collapse detector. The pre-existing collapse detector only
    # checked VISIBLE classes; withheld-class collapses (e.g., gp163d
    # Class B mass=14.5 constant, Class C radius=-2.0 constant) were
    # invisible to the apparatus. This list flags those + the joint
    # condition where ≥2 withheld classes each have a different
    # collapsed feature (the gp163d failure mode that capped the run
    # at MRE 0.5 cross-class — see scripts/backtest_rar_extended.py).
    withheld_class_feature_collapses: list[dict] = field(default_factory=list)
    cross_class_joint_form_blockers: list[dict] = field(default_factory=list)
    regime_breaks_in_data: list[dict] = field(default_factory=list)
    data_artifacts_suspected: list[dict] = field(default_factory=list)
    epistemic_voids: list[dict] = field(default_factory=list)

    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "primary_feature_key": self.primary_feature_key,
            "n_visible_rows": self.n_visible_rows,
            "classes_visible": self.classes_visible,
            "classes_withheld": self.classes_withheld,
            "substrate_invariants": self.substrate_invariants,
            "feature_dimensionality_collapses": self.feature_dimensionality_collapses,
            "cross_class_signal": self.cross_class_signal,
            "withheld_class_feature_collapses": self.withheld_class_feature_collapses,
            "cross_class_joint_form_blockers": self.cross_class_joint_form_blockers,
            "regime_breaks_in_data": self.regime_breaks_in_data,
            "data_artifacts_suspected": self.data_artifacts_suspected,
            "epistemic_voids": self.epistemic_voids,
            "summary": self.summary,
        }


# ── Deterministic probes ───────────────────────────────────────────────


def _safe_numeric(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if math.isfinite(float(v)):
            return float(v)
    return None


def _per_class_feature_summary(
    rows: list[tuple[dict, float]],
    class_key: str,
    feature_keys: list[str],
) -> dict[str, dict[str, dict[str, float]]]:
    """Per-class, per-feature: count, min, max, std, range_log10."""
    by_cls: dict[str, list[dict]] = {}
    for feats, _ in rows:
        cls = str(feats.get(class_key, "_unknown"))
        by_cls.setdefault(cls, []).append(feats)
    out: dict[str, dict[str, dict[str, float]]] = {}
    for cls, group in by_cls.items():
        out[cls] = {}
        for fk in feature_keys:
            vals = [_safe_numeric(f.get(fk)) for f in group]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            out[cls][fk] = {
                "n": len(vals),
                "min": min(vals),
                "max": max(vals),
                "mean": sum(vals) / len(vals),
            }
            try:
                import numpy as np
                arr = np.asarray(vals)
                out[cls][fk]["std"] = float(arr.std())
            except Exception:
                pass
            if min(vals) > 0 and max(vals) > 0:
                out[cls][fk]["range_log10"] = round(
                    math.log10(max(vals) / min(vals)), 2
                )
    return out


def _detect_dimensionality_collapse(
    summary: dict[str, dict[str, dict[str, float]]],
    visible_classes: list[str],
    rel_threshold: float = 0.02,
) -> list[dict]:
    """Flag features whose within-visible-class relative range is below
    threshold — those features cannot be used to constrain free
    parameters from the visible class alone.
    """
    collapses: list[dict] = []
    for cls in visible_classes:
        per_feat = summary.get(cls, {})
        for fk, s in per_feat.items():
            mn, mx = s.get("min"), s.get("max")
            mean = s.get("mean")
            if mn is None or mx is None or mean is None:
                continue
            denom = max(abs(mean), 1e-30)
            rel_range = (mx - mn) / denom if denom > 0 else 0.0
            if rel_range < rel_threshold:
                collapses.append({
                    "feature_key": fk,
                    "class": cls,
                    "min": round(mn, 4),
                    "max": round(mx, 4),
                    "mean": round(mean, 4),
                    "relative_range": round(rel_range, 5),
                    "implication": (
                        f"feature {fk!r} has near-zero variance within "
                        f"visible class {cls!r} (relative range "
                        f"{rel_range:.2g} < {rel_threshold:g}); any "
                        f"free parameter coefficient on {fk!r} is "
                        f"unconstrainable from visible data alone."
                    ),
                })
    return collapses


def _detect_withheld_class_collapse(  # scope-linter: skip
    summary: dict[str, dict[str, dict[str, float]]],
    visible_classes: list[str],
    withheld_classes: list[str],
    rel_threshold: float = 0.02,
) -> tuple[list[dict], list[dict]]:
    # scope-linter rationale: this is the inverse-side twin of
    # _detect_dimensionality_collapse. visible_classes is accepted in the
    # signature for API symmetry but not iterated by design — visible
    # collapses are detected separately by _detect_dimensionality_collapse,
    # which is called immediately before this function in critique_substrate.
    # Both must run; neither subsumes the other.
    """G-CROSS-CLASS-FEATURE-SUPPORT (R26, 2026-04-26).

    The pre-existing _detect_dimensionality_collapse only checks visible
    classes. Withheld-class feature collapses (e.g., gp163d Class B
    mass_log10=14.5 constant across 84 cluster rows; Class C
    radius_log10=-2.0 constant across 12 binary rows) are invisible to
    the apparatus' substrate diagnostics.

    The gp163d 17-form backtest 2026-04-26 demonstrated that this is the
    real failure mode: when ≥2 different withheld classes each have a
    DIFFERENT collapsed feature, no joint(feature_a, feature_b) form has
    a within-class DoF for either class. The mutator can fit Class A
    fine but cannot discriminate Class B / Class C internally — every
    cluster gets the same mass-extrapolation correction; every binary
    gets the same radius-extrapolation correction.

    Returns (withheld_collapses, joint_form_blockers):
      - withheld_collapses: [{feature_key, class, ...}] for each
        (withheld-class, feature) pair where within-class span < threshold
      - joint_form_blockers: when ≥2 withheld classes are EACH collapsed
        on a DIFFERENT feature, surface as a structural blocker — joint
        forms using both features cannot bridge those classes
    """
    withheld_collapses: list[dict] = []
    for cls in withheld_classes:
        per_feat = summary.get(cls, {})
        for fk, s in per_feat.items():
            mn, mx = s.get("min"), s.get("max")
            mean = s.get("mean")
            n_unique = s.get("n_unique")
            if mn is None or mx is None or mean is None:
                continue
            denom = max(abs(mean), 1e-30)
            rel_range = (mx - mn) / denom if denom > 0 else 0.0
            if rel_range < rel_threshold:
                withheld_collapses.append({
                    "feature_key": fk,
                    "class": cls,
                    "n_rows": s.get("n_rows"),
                    "n_unique": n_unique,
                    "min": round(mn, 4),
                    "max": round(mx, 4),
                    "mean": round(mean, 4),
                    "relative_range": round(rel_range, 5),
                    "implication": (
                        f"feature {fk!r} is collapsed within withheld class "
                        f"{cls!r} (n_unique={n_unique}, relative range "
                        f"{rel_range:.2g} < {rel_threshold:g}). Any closed-form "
                        f"law using {fk!r} as a within-class discriminator on "
                        f"{cls!r} has zero degrees of freedom — every {cls!r} "
                        f"row receives the same {fk!r}-extrapolation correction. "
                        f"The mutator cannot fit class-internal structure for "
                        f"{cls!r} via {fk!r}."
                    ),
                })

    # Joint-blocker pattern: ≥2 withheld classes, each collapsed on a
    # different feature. The gp163d failure mode.
    joint_blockers: list[dict] = []
    by_class_feature: dict[str, set] = {}
    for c in withheld_collapses:
        by_class_feature.setdefault(c["class"], set()).add(c["feature_key"])
    if len(by_class_feature) >= 2:
        # Pairwise: which class-pair has DIFFERENT collapsed features?
        classes = sorted(by_class_feature.keys())
        for i, c1 in enumerate(classes):
            for c2 in classes[i + 1:]:
                feats1 = by_class_feature[c1]
                feats2 = by_class_feature[c2]
                # Each class collapses on a feature the OTHER class doesn't
                disjoint_collapse = (feats1 - feats2) and (feats2 - feats1)
                if disjoint_collapse:
                    joint_blockers.append({
                        "withheld_class_a": c1,
                        "collapsed_features_a": sorted(feats1),
                        "withheld_class_b": c2,
                        "collapsed_features_b": sorted(feats2),
                        "implication": (
                            f"Classes {c1!r} and {c2!r} are collapsed on "
                            f"disjoint feature sets ({sorted(feats1)} vs "
                            f"{sorted(feats2)}). No joint(feature) form using "
                            f"both axes can simultaneously discriminate within "
                            f"both classes — joint forms degenerate to constant "
                            f"per-class corrections. This is a SUBSTRATE-DATA "
                            f"ceiling, not a grammar ceiling: enriching the "
                            f"substrate with per-row variation on the collapsed "
                            f"features is the only path forward (or formally "
                            f"abstaining on one of the classes via "
                            f"r11_excluded_classes / honest_null_rows)."
                        ),
                    })
    return withheld_collapses, joint_blockers


def _detect_cross_class_signal(
    summary: dict[str, dict[str, dict[str, float]]],
    visible_classes: list[str],
    withheld_classes: list[str],
) -> list[dict]:
    """For each feature, compare visible vs withheld range overlap."""
    items: list[dict] = []
    feature_keys = set()
    for cls in visible_classes + withheld_classes:
        feature_keys.update((summary.get(cls) or {}).keys())
    for fk in sorted(feature_keys):
        vis_ranges = []
        with_ranges = []
        for cls in visible_classes:
            s = (summary.get(cls) or {}).get(fk)
            if s and "min" in s and "max" in s:
                vis_ranges.append((s["min"], s["max"]))
        for cls in withheld_classes:
            s = (summary.get(cls) or {}).get(fk)
            if s and "min" in s and "max" in s:
                with_ranges.append((s["min"], s["max"]))
        if not vis_ranges or not with_ranges:
            continue
        vis_min = min(r[0] for r in vis_ranges)
        vis_max = max(r[1] for r in vis_ranges)
        with_min = min(r[0] for r in with_ranges)
        with_max = max(r[1] for r in with_ranges)
        overlap_min = max(vis_min, with_min)
        overlap_max = min(vis_max, with_max)
        overlap = max(0.0, overlap_max - overlap_min)
        with_span = max(with_max - with_min, 1e-30)
        # Format ranges with log-aware precision so very small values
        # (e.g., gravitational accelerations ~1e-12) don't all round
        # to 0.0 in the operator-facing display.
        def _fmt(v: float) -> str:
            av = abs(v)
            if av == 0:
                return "0"
            if av < 1e-3 or av > 1e6:
                return f"{v:.3g}"
            return str(round(v, 3))
        items.append({
            "feature_key": fk,
            "visible_range": [_fmt(vis_min), _fmt(vis_max)],
            "withheld_range": [_fmt(with_min), _fmt(with_max)],
            "overlap_units": _fmt(overlap),
            "overlap_fraction_of_withheld": round(overlap / with_span, 3),
            "extrapolation_power": (
                "high" if overlap / with_span > 0.5
                else "low" if overlap / with_span > 0.1
                else "none"
            ),
        })
    return items


def _detect_regime_breaks(
    rows: list[tuple[dict, float]], primary_feature_key: str,
) -> list[dict]:
    """Detect discontinuities in y when sorted by primary feature."""
    pairs: list[tuple[float, float]] = []
    for feats, y in rows:
        x = _safe_numeric(feats.get(primary_feature_key))
        yv = _safe_numeric(y)
        if x is not None and yv is not None:
            pairs.append((x, yv))
    if len(pairs) < 30:
        return []
    pairs.sort()
    try:
        import numpy as np
        ys = np.asarray([p[1] for p in pairs])
        xs = np.asarray([p[0] for p in pairs])
        log_y = np.log10(np.abs(ys) + 1e-300)
        nw = max(4, min(8, len(pairs) // 12))
        windows_log = np.array([
            float(np.median(b)) for b in np.array_split(log_y, nw)
        ])
        adj_steps = np.abs(np.diff(windows_log))
        if len(adj_steps) >= 3 and adj_steps.std() > 0:
            largest = float(adj_steps.max())
            ratio = largest / max(float(adj_steps.median() if hasattr(adj_steps, "median") else np.median(adj_steps)), 1e-12)
            if ratio > 5.0 and largest > 0.5:
                # Find which window-pair the break is at
                idx = int(np.argmax(adj_steps))
                x_split = float(xs[int(len(xs) * (idx + 1) / nw)])
                return [{
                    "primary_feature": primary_feature_key,
                    "split_at_x": round(x_split, 3),
                    "log10_y_jump": round(largest, 3),
                    "step_ratio_to_median": round(ratio, 2),
                    "implication": (
                        f"data shows a discontinuous jump in log10|y| of "
                        f"{largest:.2f} dex near {primary_feature_key}={x_split:.3g}, "
                        f"{ratio:.0f}× larger than typical inter-window "
                        f"steps. A smooth-scaling form will not extrapolate "
                        f"across this break."
                    ),
                }]
    except Exception:
        pass
    return []


def _detect_data_artifacts(
    rows: list[tuple[dict, float]],
    class_key: str,
    primary_feature_key: str = "x",
    expected_y_over_x: Optional[str] = None,
) -> list[dict]:
    """Sanity tests for known instrument-artifact patterns.

    Args:
        rows: list of (features, y) pairs.
        class_key: categorical feature defining classes.
        primary_feature_key: the feature serving as the "x" axis;
            used as the denominator in the ratio sanity test.
        expected_y_over_x: optional operator declaration of expected
            y/x ratio direction. Accepted values: "ge_one" (y >= x
            expected, e.g., gravitational regimes where observed
            acceleration exceeds Newtonian); "le_one" (y <= x
            expected); None (skip the ratio sanity test). Without an
            operator declaration, the test does NOT fire — the y/x
            test is meaningful only when the operator has a prior
            on the expected ratio direction.
    """
    artifacts: list[dict] = []
    by_cls: dict[str, list[tuple[dict, float]]] = {}
    for feats, y in rows:
        cls = str(feats.get(class_key, "_unknown"))
        by_cls.setdefault(cls, []).append((feats, y))

    # Pattern A: y/x_proxy systematically violates the operator's
    # declared expected ratio direction. Skipped when no expectation
    # is declared, because "y < x most of the time" is not an
    # artifact for substrates where it is the expected behavior.
    if expected_y_over_x not in {"ge_one", "le_one"}:
        return artifacts

    for cls, group in by_cls.items():
        ratios = []
        for f, y in group:
            x = _safe_numeric(f.get(primary_feature_key))
            yv = _safe_numeric(y)
            if x is not None and yv is not None and x > 0 and yv > 0:
                ratios.append(yv / x)
        if len(ratios) >= 5:
            if expected_y_over_x == "ge_one":
                n_violations = sum(1 for r in ratios if r < 1.0)
                violation_label = "below 1"
                expected_label = "y >= x"
            else:  # le_one
                n_violations = sum(1 for r in ratios if r > 1.0)
                violation_label = "above 1"
                expected_label = "y <= x"
            frac_violation = n_violations / len(ratios)
            if frac_violation > 0.9:
                artifacts.append({
                    "kind": f"y_over_{primary_feature_key}_systematically_violates_{expected_y_over_x}",
                    "class": cls,
                    "primary_feature": primary_feature_key,
                    "expected": expected_label,
                    "n_rows": len(ratios),
                    "fraction_violating": round(frac_violation, 3),
                    "min_ratio": round(min(ratios), 3),
                    "max_ratio": round(max(ratios), 3),
                    "implication": (
                        f"y/{primary_feature_key} ratio for class {cls!r} is "
                        f"{violation_label} in {n_violations}/{len(ratios)} rows. "
                        f"Operator declared expected_y_over_x={expected_y_over_x!r} "
                        f"({expected_label}). If the relation is supposed to hold "
                        f"in this regime, the data may carry an instrument artifact "
                        f"(deprojection, undercounting, sign convention). Including "
                        f"this class in farther-tail validation may poison the test."
                    ),
                })
    return artifacts


def _build_epistemic_voids(
    collapses: list[dict],
    cross_class: list[dict],
    artifacts: list[dict],
    visible_classes: list[str],
    withheld_classes: list[str],
) -> list[dict]:
    """Synthesize the highest-priority unknowns from the deterministic
    findings. These are the items the operator should consider before
    the next iter — substrate-level fixes, not apparatus tuning."""
    voids: list[dict] = []
    for c in collapses:
        voids.append({
            "unknown": (
                f"how does y depend on {c['feature_key']} within visible "
                f"class {c['class']!r}?"
            ),
            "why_it_matters": (
                f"any free parameter on {c['feature_key']} is unconstrainable "
                f"from visible data; the apparatus will fit it to noise."
            ),
            "blocking": "substrate enrichment (more within-class variance) or feature exclusion",
        })
    for cc in cross_class:
        if cc.get("extrapolation_power") == "none":
            voids.append({
                "unknown": (
                    f"the cross-class transition in {cc['feature_key']!r} "
                    f"between visible and withheld classes"
                ),
                "why_it_matters": (
                    f"visible range {cc['visible_range']} does not overlap "
                    f"withheld range {cc['withheld_range']}; visible-only "
                    f"fitting cannot constrain the form's behavior in the "
                    f"withheld regime."
                ),
                "blocking": "either substrate rebalancing (visible class spanning the transition) or hypothesis reframing (publishable null on extrapolation)",
            })
    for a in artifacts:
        voids.append({
            "unknown": (
                f"whether the {a['kind']} pattern in class {a['class']!r} "
                f"is signal or instrument artifact"
            ),
            "why_it_matters": (
                "if it is an artifact, the class should be corrected or "
                "excluded from validation; if it is signal, the form must "
                "explain the asymmetry."
            ),
            "blocking": "operator decision on data-source treatment",
        })
    if not visible_classes or not withheld_classes:
        voids.append({
            "unknown": "no farther-tail withholding configured",
            "why_it_matters": (
                "without a withheld class, the apparatus cannot test "
                "whether the form generalizes outside the fitted regime; "
                "the score reflects only in-sample fit."
            ),
            "blocking": "substrate split design",
        })
    return voids


# ── Public entry point ────────────────────────────────────────────────


def critique_substrate(
    visible_data: list[tuple[dict, float]],
    *,
    farther_tail_data: Optional[list[tuple[dict, float]]] = None,
    primary_feature_key: str = "x",
    class_key: str = "system_class",
    project_name: str = "",
    expected_y_over_x: Optional[str] = None,
) -> SubstrateCritique:
    """Run the deterministic substrate critique.

    Args:
        visible_data: list of (features, y) — the rows the apparatus is
            allowed to fit on.
        farther_tail_data: optional list of (features, y) — withheld
            rows used only for extrapolation tests. Critique uses these
            to compute cross-class signal but never to "fit" anything.
        primary_feature_key: the feature serving as the substrate's
            primary axis (used for regime-break detection).
        class_key: the categorical feature whose values define system
            classes.
        project_name: identifier for audit logging.

    Returns:
        SubstrateCritique with all sections populated. Empty sections
        are valid signals (e.g., zero data artifacts is a clean bill
        of health, recorded as an empty list).
    """
    crit = SubstrateCritique(
        project=project_name,
        primary_feature_key=primary_feature_key,
        n_visible_rows=len(visible_data),
    )
    if not visible_data:
        crit.summary = "no visible data; substrate critique skipped"
        return crit

    # Discover visible feature keys from first row. Exclude identifiers
    # and provenance fields — those are not features in the modeling
    # sense and produce noise in cross-class signal analysis.
    _IDENTIFIER_KEYS = {"id", "system_id", "row_id", "sigma_source"}
    sample_keys = list(visible_data[0][0].keys()) if visible_data[0][0] else []
    feature_keys = [
        k for k in sample_keys
        if k != class_key and k not in _IDENTIFIER_KEYS
    ]

    # Per-class summary across both visible and withheld
    all_rows = list(visible_data) + list(farther_tail_data or [])
    summary = _per_class_feature_summary(all_rows, class_key, feature_keys)
    visible_classes = sorted({
        str(f.get(class_key, "_unknown")) for f, _ in visible_data
    })
    withheld_classes = sorted(
        {str(f.get(class_key, "_unknown")) for f, _ in (farther_tail_data or [])}
        - set(visible_classes)
    )
    crit.classes_visible = visible_classes
    crit.classes_withheld = withheld_classes

    # Substrate invariants — data ground truth
    for cls in visible_classes:
        per_feat = summary.get(cls, {})
        for fk, s in per_feat.items():
            crit.substrate_invariants.append({
                "class": cls,
                "feature_key": fk,
                "n": s.get("n"),
                "range": [s.get("min"), s.get("max")],
                "mean": s.get("mean"),
                "std": s.get("std"),
                "range_log10": s.get("range_log10"),
            })

    # Feature dimensionality collapses
    crit.feature_dimensionality_collapses = _detect_dimensionality_collapse(
        summary, visible_classes
    )

    # Cross-class signal (only if withheld classes present)
    if withheld_classes:
        crit.cross_class_signal = _detect_cross_class_signal(
            summary, visible_classes, withheld_classes
        )
        # G-CROSS-CLASS-FEATURE-SUPPORT (R26, 2026-04-26): within-withheld-class
        # feature-collapse detector + joint-form-blocker pattern. Catches
        # the gp163d failure mode (Class B mass-collapsed + Class C
        # radius-collapsed → joint(mass, radius) forms have zero DoF
        # within either class).
        crit.withheld_class_feature_collapses, crit.cross_class_joint_form_blockers = (
            _detect_withheld_class_collapse(summary, visible_classes, withheld_classes)
        )

    # Regime breaks in raw data
    crit.regime_breaks_in_data = _detect_regime_breaks(
        all_rows, primary_feature_key
    )

    # Data artifacts (only fires when operator declared an expected
    # ratio direction; otherwise the y/x test is skipped because
    # "y < x most of the time" is not an artifact for substrates where
    # it is the expected behavior).
    crit.data_artifacts_suspected = _detect_data_artifacts(
        all_rows, class_key,
        primary_feature_key=primary_feature_key,
        expected_y_over_x=expected_y_over_x,
    )

    # Epistemic voids — synthesized from the deterministic findings
    crit.epistemic_voids = _build_epistemic_voids(
        crit.feature_dimensionality_collapses,
        crit.cross_class_signal,
        crit.data_artifacts_suspected,
        visible_classes,
        withheld_classes,
    )

    # One-line summary
    n_v = len(crit.epistemic_voids)
    n_c = len(crit.feature_dimensionality_collapses)
    n_a = len(crit.data_artifacts_suspected)
    n_b = len(crit.regime_breaks_in_data)
    parts = []
    if n_c:
        parts.append(f"{n_c} feature dimensionality collapse(s)")
    if n_a:
        parts.append(f"{n_a} suspected data artifact(s)")
    if n_b:
        parts.append(f"{n_b} regime break(s)")
    if n_v:
        parts.append(f"{n_v} epistemic void(s)")
    if parts:
        crit.summary = (
            f"substrate critic: {' / '.join(parts)} surfaced; see sections "
            f"below for operator-actionable items."
        )
    else:
        crit.summary = (
            "substrate critic: no structural collapses, artifacts, or "
            "regime breaks detected; substrate is internally consistent."
        )
    return crit


def derive_operator_suggestions(critique: SubstrateCritique) -> list[dict]:
    """Synthesize concrete operator-actionable suggestions from the
    deterministic critique findings.

    The critic surfaces facts. Suggestions translate those facts into
    candidate substrate edits the operator may consider — but never
    auto-applies. Each suggestion carries an `operator_action_needed`
    flag and a `kind` so the operator can triage. Same discipline as
    the apparatus's derived-constraints layer: the apparatus proposes,
    the operator disposes.
    """
    suggestions: list[dict] = []

    # From dimensionality collapses → exclude or enrich
    for c in critique.feature_dimensionality_collapses:
        suggestions.append({
            "operator_action_needed": True,
            "kind": "feature_dimensionality_remediation",
            "feature_key": c.get("feature_key"),
            "class": c.get("class"),
            "options": [
                f"exclude {c.get('feature_key')!r} from PARAMETRIC_FORM (visible "
                f"data cannot constrain it; any free parameter on this "
                f"feature will absorb noise)",
                f"enrich the substrate by adding rows whose "
                f"{c.get('feature_key')!r} differs by at least 0.5 "
                f"(within-class variance is the binding constraint)",
                f"reframe the thesis as a publishable null on this "
                f"feature: 'visible data is consistent with both U and S '"
                f"on {c.get('feature_key')!r}; only farther-tail can decide.'",
            ],
            "evidence": c.get("implication"),
        })

    # From cross-class signal (none / low) → expose more features or accept null
    for cc in critique.cross_class_signal:
        if cc.get("extrapolation_power") == "none":
            suggestions.append({
                "operator_action_needed": True,
                "kind": "cross_class_extrapolation_gap",
                "feature_key": cc.get("feature_key"),
                "options": [
                    f"add a feature to features.py that DOES bridge the "
                    f"visible/withheld gap (e.g., a derived quantity, a "
                    f"property from the substrate's source catalog that "
                    f"is currently not exposed)",
                    f"accept the gap as a publishable null: visible "
                    f"{cc.get('feature_key')!r} range "
                    f"{cc.get('visible_range')} cannot predict withheld "
                    f"range {cc.get('withheld_range')}; the apparatus "
                    f"reports the failure with the gap as the caveat.",
                ],
                "evidence": (
                    f"visible range {cc.get('visible_range')} vs withheld "
                    f"{cc.get('withheld_range')}: overlap "
                    f"{cc.get('overlap_fraction_of_withheld', 0):.0%}"
                ),
            })

    # From data artifacts → correct or exclude
    for a in critique.data_artifacts_suspected:
        suggestions.append({
            "operator_action_needed": True,
            "kind": "data_artifact_remediation",
            "class": a.get("class"),
            "artifact_kind": a.get("kind"),
            "options": [
                f"apply a correction to class {a.get('class')!r} (e.g., for "
                f"a deprojection artifact, multiply y by sqrt(3) to recover "
                f"3D from sky-projected; for under-counting, scale by the "
                f"known efficiency)",
                f"exclude class {a.get('class')!r} from the farther-tail set "
                f"so the validation gate is not poisoned",
                f"add a correction column in features.py that the form can "
                f"consume explicitly",
            ],
            "evidence": a.get("implication"),
        })

    # From regime breaks → form must accommodate or split substrate
    for r in critique.regime_breaks_in_data:
        suggestions.append({
            "operator_action_needed": False,
            "kind": "regime_break_observation",
            "split_at_x": r.get("split_at_x"),
            "log10_y_jump": r.get("log10_y_jump"),
            "options": [
                "propose a piecewise / crossover form whose shape matches "
                "the discontinuity",
                "split the substrate into two subsets (pre-break / "
                "post-break) and fit each separately; report the per-subset "
                "fit + the cross-subset gap as the finding",
            ],
            "evidence": r.get("implication"),
        })

    # No farther-tail → no Newton-step possible
    if not critique.classes_withheld:
        suggestions.append({
            "operator_action_needed": True,
            "kind": "no_farther_tail",
            "options": [
                "configure features.farther_tail_rows() to withhold a class "
                "or a high-x slice; without withholding, the apparatus "
                "cannot run a Newton-step extrapolation test",
            ],
            "evidence": "classes_withheld is empty",
        })

    return suggestions


def refresh_critique_post_fit(
    base_critique: SubstrateCritique,
    fit_result_json: dict,
    visible_data: list[tuple[dict, float]],
    *,
    primary_feature_key: str = "x",
    iter_index: Optional[int] = None,
) -> SubstrateCritique:
    """Refresh the critique with post-fit observations.

    The pre-flight critique describes what the substrate's RAW data
    shows. After each iter's fit, the residuals reveal additional
    structure — features the form ignores that nonetheless correlate
    with residuals, regime breaks the form misses, etc. This refresh
    runs cheap deterministic probes on the latest residuals and
    APPENDS findings to the critique without overwriting pre-flight
    structural facts. The pre-flight sections (substrate_invariants,
    feature_dimensionality_collapses, cross_class_signal,
    regime_breaks_in_data, data_artifacts_suspected) remain stable
    because they describe the data, not the form. New findings get
    appended to a `post_fit_iter_N` section in epistemic_voids.

    No LLM call. Pure structural probes.
    """
    if not fit_result_json or not visible_data:
        return base_critique
    form = fit_result_json.get("form")
    fitted = fit_result_json.get("fitted_params") or {}
    if not form or not fitted:
        return base_critique

    try:
        from src.ztare.fit.fit_primitive_features import _safe_compile_form
        fn = _safe_compile_form(form)
    except Exception:
        return base_critique

    # Compute per-row residuals + collect feature keys not in the form
    referenced_keys: set[str] = set()
    try:
        # crude regex extraction of features['key'] references
        import re
        referenced_keys = set(re.findall(r"features\[['\"]([\w_]+)['\"]\]", form))
    except Exception:
        pass

    sample_keys = set(visible_data[0][0].keys()) if visible_data and visible_data[0][0] else set()
    unreferenced_features = sorted(sample_keys - referenced_keys - {"id", "system_id"})

    residuals: list[float] = []
    rows_kept: list[dict] = []
    for feats, y in visible_data:
        try:
            y_pred = fn(feats, fitted)
            if y_pred is None or (isinstance(y_pred, float) and (math.isnan(y_pred) or math.isinf(y_pred))):
                continue
            residuals.append(float(y) - float(y_pred))
            rows_kept.append(feats)
        except Exception:
            continue

    if len(residuals) < 20:
        return base_critique

    # For each unreferenced feature, compute Spearman rank correlation
    # between residuals and the feature. A non-trivial |rho| means the
    # form is missing structure that this feature carries.
    new_voids: list[dict] = []
    try:
        from scipy.stats import spearmanr
        import numpy as np
        res_arr = np.asarray(residuals)
        for fk in unreferenced_features:
            vals = []
            keep_idx = []
            for i, f in enumerate(rows_kept):
                v = _safe_numeric(f.get(fk))
                if v is not None:
                    vals.append(v)
                    keep_idx.append(i)
            if len(vals) < 20:
                continue
            try:
                rho, p = spearmanr(vals, res_arr[keep_idx])
                if rho is None or math.isnan(rho):
                    continue
                if abs(rho) > 0.25 and p < 0.01:
                    new_voids.append({
                        "unknown": (
                            f"residuals from iter {iter_index} correlate "
                            f"with unreferenced feature {fk!r} "
                            f"(spearman rho={rho:.3f}, p={p:.3g})"
                        ),
                        "why_it_matters": (
                            f"the form ignores {fk!r} but the residuals "
                            f"carry structure that {fk!r} predicts; the "
                            f"form is structurally incomplete on this feature."
                        ),
                        "blocking": (
                            f"either propose a form that uses {fk!r}, or "
                            f"explicitly justify why {fk!r} is not "
                            f"causally relevant despite the residual signal."
                        ),
                        "stage": f"post_fit_iter_{iter_index}",
                    })
            except Exception:
                continue
    except ImportError:
        pass  # scipy not available — skip post-fit probes silently

    # Append the new voids without overwriting pre-flight structural facts
    if new_voids:
        # Drop any prior post-fit voids from earlier iters (we only carry
        # the latest iter's findings to avoid stale signals dominating)
        base_critique.epistemic_voids = [
            v for v in base_critique.epistemic_voids
            if not str(v.get("stage", "")).startswith("post_fit_iter_")
        ]
        base_critique.epistemic_voids.extend(new_voids)
        base_critique.summary += (
            f" | post-fit iter {iter_index}: {len(new_voids)} new void(s) "
            f"from residual-feature correlation."
        )

    return base_critique


def write_critique(workspace_dir: Path, critique: SubstrateCritique) -> Path:
    """Persist the critique to workspace/substrate_critique.json. Merges
    operator overrides from substrate_critique_overrides.json if present
    (same discipline as compile_evidence's manual overrides). Also
    writes workspace/substrate_critique_suggestions.json with the
    operator-actionable suggestions derived from the critique.

    The split keeps facts (critique) separate from proposed actions
    (suggestions). The mutator briefing reads both; the operator
    decides whether to act on suggestions. No LLM call, no soft
    summary — same discipline as the rest of the apparatus's
    deterministic surfaces.
    """
    workspace_dir = Path(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    payload = critique.to_dict()

    overrides_path = workspace_dir / "substrate_critique_overrides.json"
    if overrides_path.exists():
        try:
            overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
            if isinstance(overrides, dict):
                # Shallow merge: operator's lists are appended; scalar
                # fields are overridden if explicitly set
                for k, v in overrides.items():
                    if isinstance(v, list) and isinstance(payload.get(k), list):
                        payload[k] = payload[k] + v
                    else:
                        payload[k] = v
        except Exception:
            pass

    out = workspace_dir / "substrate_critique.json"
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    # Suggestions sidecar — operator-actionable items, gated.
    suggestions = derive_operator_suggestions(critique)
    suggestions_payload = {
        "schema_version": "substrate-suggestions-v1",
        "n_suggestions": len(suggestions),
        "n_action_needed": sum(1 for s in suggestions if s.get("operator_action_needed")),
        "suggestions": suggestions,
    }
    sug_path = workspace_dir / "substrate_critique_suggestions.json"
    sug_path.write_text(
        json.dumps(suggestions_payload, indent=2, default=str), encoding="utf-8"
    )
    return out


# ── R13 Cage adapters (per GP-157 §3a) ────────────────────────────────


def _r13_load_substrate_data(project_dir: "Path") -> tuple[list, list]:  # type: ignore  # noqa: F821
    """Load (visible, farther-tail) (features, y) pairs from project_dir/features.py.

    Returns ([], []) on any failure — failure is non-fatal, gate degrades
    to a no-op rather than aborting the run.
    """
    from pathlib import Path as _Path
    visible: list = []
    farther: list = []
    try:
        import importlib.util as _ilu
        feat_path = _Path(project_dir) / "features.py"
        if not feat_path.exists():
            return visible, farther
        spec = _ilu.spec_from_file_location(
            "_r13_substrate_critic_features", str(feat_path)
        )
        if spec is None or spec.loader is None:
            return visible, farther
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "visible_rows"):
            for t in mod.visible_rows():
                if len(t) >= 3:
                    visible.append((t[2], t[1]))
        if hasattr(mod, "farther_tail_rows"):
            for t in mod.farther_tail_rows():
                if len(t) >= 3:
                    farther.append((t[2], t[1]))
    except Exception:
        return visible, farther
    return visible, farther


def r13_can_handle(substrate: "Any", candidate: "Any") -> tuple[bool, str]:  # type: ignore  # noqa: F821
    """R13 substrate_critic engagement predicate.

    Engages when:
      - cage_meta.class in {nd_features, time_series} (multi-row substrates
        where structural collapse / cross-class signal / regime breaks have
        meaning)
      - rubric does NOT explicitly disable via `disable_substrate_critic: true`

    Per GP-157 §3a, the rubric flag is opt-OUT, not opt-in: substrate-class
    routing decides default engagement.

    Backward-compat note: legacy rubrics that set `enable_substrate_critic:
    false` are also respected — flipping the flag from absent to false is a
    valid disable signal.
    """
    meta = getattr(substrate, "meta", {}) or {}
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    cage_class = str(meta.get("class", "") or "").strip().lower()
    if cage_class not in {"nd_features", "time_series"}:
        return False, (
            f"R13 refused: cage_meta.class={cage_class!r} not in "
            f"{{nd_features, time_series}}; substrate critic operates on "
            f"multi-feature substrates with categorical class structure."
        )
    if bool(rubric.get("disable_substrate_critic", False)):
        return False, "R13 refused: rubric.disable_substrate_critic is true"
    # Legacy compatibility: explicit enable_substrate_critic=False also disables.
    if "enable_substrate_critic" in rubric and not bool(
        rubric.get("enable_substrate_critic")
    ):
        return False, (
            "R13 refused: rubric.enable_substrate_critic is explicitly false "
            "(legacy opt-out)"
        )
    return True, "R13 engaged"


def r13_run_preflight(substrate: "Any", candidate: "Any") -> dict:  # type: ignore  # noqa: F821
    """PRE_FIT (preflight) adapter: build pre-iter-1 substrate critique
    and write workspace/substrate_critique.json + suggestions sidecar.

    Returns a summary dict the dispatcher logs.
    """
    from pathlib import Path as _Path
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    project_dir = _Path(getattr(candidate, "project_dir", "."))
    workspace_dir = _Path(
        getattr(candidate, "workspace_dir", project_dir / "workspace")
    )

    visible, farther = _r13_load_substrate_data(project_dir)
    if not visible:
        return {
            "engaged": True,
            "stage": "preflight",
            "skipped": True,
            "reason": "no visible data loadable from features.py",
        }
    primary = str(rubric.get("framer_primary_feature_key", "x"))
    class_key = str(rubric.get("substrate_class_key", "system_class"))
    expected_y_over_x = rubric.get("substrate_expected_y_over_x")
    project_name = str(getattr(candidate, "project", "") or "")

    crit = critique_substrate(
        visible,
        farther_tail_data=farther or None,
        primary_feature_key=primary,
        class_key=class_key,
        project_name=project_name,
        expected_y_over_x=expected_y_over_x,
    )
    write_critique(workspace_dir, crit)
    return {
        "engaged": True,
        "stage": "preflight",
        "summary": crit.summary,
        "n_voids": len(crit.epistemic_voids),
        "voids_preview": [
            v.get("unknown", "")[:120]
            for v in crit.epistemic_voids[:3]
        ],
    }


def r13_run_post_fit(substrate: "Any", candidate: "Any") -> dict:  # type: ignore  # noqa: F821
    """POST_FIT adapter: refresh per-iter substrate critique against the
    latest fit's residuals; appends post_fit_iter_N voids without
    overwriting pre-flight structural facts.
    """
    from pathlib import Path as _Path
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    project_dir = _Path(getattr(candidate, "project_dir", "."))
    workspace_dir = _Path(
        getattr(candidate, "workspace_dir", project_dir / "workspace")
    )
    iter_index = int(getattr(candidate, "iter_index", 0) or 0)

    # Use _vis (pre-loaded visible rows) when the dispatcher provides it,
    # otherwise re-load from features.py. The legacy direct-wire passed _vis
    # from the fit primitive's working set; we mirror that path.
    visible = getattr(candidate, "visible_pairs", None)
    farther: list = []
    if not visible:
        visible, farther = _r13_load_substrate_data(project_dir)
    else:
        _, farther = _r13_load_substrate_data(project_dir)
    if not visible:
        return {
            "engaged": True,
            "stage": "post_fit",
            "skipped": True,
            "reason": "no visible data available for post-fit refresh",
        }

    primary = str(rubric.get("framer_primary_feature_key", "x"))
    class_key = str(rubric.get("substrate_class_key", "system_class"))
    expected_y_over_x = rubric.get("substrate_expected_y_over_x")
    project_name = str(getattr(candidate, "project", "") or "")

    base = critique_substrate(
        visible,
        farther_tail_data=farther or None,
        primary_feature_key=primary,
        class_key=class_key,
        project_name=project_name,
        expected_y_over_x=expected_y_over_x,
    )
    fit_path = workspace_dir / "fit_features_result.json"
    if fit_path.exists():
        try:
            fit_json = json.loads(fit_path.read_text(encoding="utf-8"))
            refresh_critique_post_fit(
                base, fit_json, visible,
                primary_feature_key=primary,
                iter_index=iter_index,
            )
        except Exception:
            pass
    write_critique(workspace_dir, base)

    post_voids = [
        v for v in base.epistemic_voids
        if str(v.get("stage", "")).startswith(f"post_fit_iter_{iter_index}")
    ]
    return {
        "engaged": True,
        "stage": "post_fit",
        "n_post_voids": len(post_voids),
        "post_voids_preview": [
            v.get("unknown", "")[:120] for v in post_voids[:2]
        ],
    }


def register_r13_gate(cage: "Any") -> None:  # type: ignore  # noqa: F821
    """Register the R13 substrate_critic gate(s) with a Cage instance.

    R13 is dual-phase: PRE_FIT preflight and POST_FIT per-iter refresh.
    Each phase is its own Gate object so the Cage's phase routing engages
    them in the right slot. Both share the same can_handle predicate.
    """
    try:
        from src.ztare.gates.cage import Gate
    except ImportError:
        return
    pre_gate = Gate(
        name="R13_substrate_critic_preflight",
        phase="PRE_FIT",
        can_handle=r13_can_handle,
        run=r13_run_preflight,
        dependencies=[],
    )
    post_gate = Gate(
        name="R13_substrate_critic_post_fit",
        phase="POST_FIT",
        can_handle=r13_can_handle,
        run=r13_run_post_fit,
        dependencies=[],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[pre_gate.name] = pre_gate
        cage.gates[post_gate.name] = post_gate
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None


# ── Self-test ──────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Build a substrate that mirrors gp163d's known issues:
    #   - Class A mass_log10 fixed (dimensionality collapse)
    #   - Class C y/x systematically below 1 (artifact)
    #   - Class B in different regime (cross-class signal)
    import random
    random.seed(0)
    visible = []
    farther = []

    # Class A — disks: x in [1e-12, 1e-9], mass_log10 ≈ 10.5
    for _ in range(200):
        x = 10 ** random.uniform(-12, -9)
        y = x + 0.1 * random.gauss(0, 1) * x
        visible.append((
            {"x": x, "system_class": "A", "radius_log10": random.uniform(-1, 2),
             "mass_log10": 10.5 + 0.05 * random.gauss(0, 1)},
            y,
        ))

    # Class B — clusters: x in [1e-10, 1e-9], discontinuous c
    for _ in range(50):
        x = 10 ** random.uniform(-10, -9)
        y = 20 * x  # the regime jump
        farther.append((
            {"x": x, "system_class": "B", "radius_log10": random.uniform(2, 3),
             "mass_log10": 14.5 + 0.1 * random.gauss(0, 1)},
            y,
        ))

    # Class C — binaries with deprojection artifact (y/x < 1)
    for _ in range(20):
        x = 10 ** random.uniform(-12, -11)
        y = 0.5 * x
        farther.append((
            {"x": x, "system_class": "C", "radius_log10": random.uniform(-3, -2),
             "mass_log10": 8.0 + 0.1 * random.gauss(0, 1)},
            y,
        ))

    crit = critique_substrate(
        visible, farther_tail_data=farther,
        primary_feature_key="x", project_name="gp163d_self_test",
    )
    print("=" * 60)
    print("SubstrateCritic self-test on gp163d-like substrate")
    print("=" * 60)
    print(f"Summary: {crit.summary}")
    print(f"Visible classes: {crit.classes_visible}")
    print(f"Withheld classes: {crit.classes_withheld}")
    print()
    print(f"Dimensionality collapses ({len(crit.feature_dimensionality_collapses)}):")
    for c in crit.feature_dimensionality_collapses:
        print(f"  - {c['feature_key']} in class {c['class']}: rel_range={c['relative_range']}")
    print()
    print(f"Cross-class signal ({len(crit.cross_class_signal)}):")
    for cc in crit.cross_class_signal:
        print(f"  - {cc['feature_key']}: extrap={cc['extrapolation_power']} "
              f"overlap_frac={cc['overlap_fraction_of_withheld']}")
    print()
    print(f"Regime breaks ({len(crit.regime_breaks_in_data)}):")
    for rb in crit.regime_breaks_in_data:
        print(f"  - split at {rb['primary_feature']}={rb['split_at_x']}: "
              f"log10|y| jump = {rb['log10_y_jump']}")
    print()
    print(f"Data artifacts ({len(crit.data_artifacts_suspected)}):")
    for a in crit.data_artifacts_suspected:
        print(f"  - {a['kind']} in class {a['class']}: "
              f"fraction_below_1={a['fraction_below_1']}")
    print()
    print(f"Epistemic voids ({len(crit.epistemic_voids)}):")
    for v in crit.epistemic_voids:
        print(f"  - {v['unknown'][:80]}")
