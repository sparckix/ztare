"""Structural anti-pattern gates — apparatus-general Cage-routed gates.

Bundles four gates that share a structural-pattern-detection design:

    R20 — G-WITHHELD-VALUE-LEAKAGE
        Scans PARAMETRIC_FORM for hardcoded numeric constants that match
        a withheld-class feature value to within tolerance. Catches RH-18
        kernel-camouflage where the mutator pulls withheld-class numeric
        values from the briefing and pins kernel centers/widths/amplitudes
        at exactly those values.

    R21 — G-EFFECTIVE-PARAMETER-COUNT
        Perturbs each numeric constant in PARAMETRIC_FORM by ±10% and
        measures the resulting farther-tail MRE delta. Constants whose
        perturbation changes MRE by more than a threshold count as
        effectively-fitted; the form's declared K (PARAMETER_NAMES count)
        must match the effective K. Catches forms that declare K=1 but
        have 5+ decision-critical hardcoded constants.

    R22 — APPARATUS-META-RUNNER
        Treats the form + thesis prose + judge weakest-points as input
        to a deterministic pattern-match against the apparatus's
        anti_pattern_catalog.md. If the form structurally matches a
        catalogued failure mode (RH-13 categorical-as-continuous,
        RH-17 lookup table, RH-18 kernel camouflage, etc.), the gate
        demotes the form's score and surfaces the matched pattern.

    R23 — G-SPARSE-CELL-EXCLUSION
        Detects categorical cells in the holdout/farther-tail that have
        fewer than N rows AND no continuous-feature pathway to the
        free-parameter portion of the form. Moves those rows to the
        honest_null bucket (telemetry-only, not gate-enforced). Prevents
        the mutator from being forced to RH-17 hardcode values on cells
        the substrate cannot constrain.

All four gates ship Cage-routed per GP-157 §3a (can_handle predicate +
run adapter, registration via build_cage_runtime). No autoresearch_loop
direct-wire.
"""
from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ── Shared helpers ────────────────────────────────────────────────────


def _extract_numeric_constants(form_str: str) -> list[float]:
    """Return all numeric literals in the form's AST."""
    out: list[float] = []
    if not form_str:
        return out
    try:
        tree = ast.parse(form_str, mode="eval")
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if not isinstance(node.value, bool):  # bool is a subclass of int
                out.append(float(node.value))
    return out


def _gather_withheld_feature_values(
    farther_features: list[dict],
    feature_keys: set[str],
) -> dict[str, set[float]]:
    """Collect numeric values appearing on the withheld classes for each
    primary feature key. Returns {feature_key: set_of_values}."""
    out: dict[str, set[float]] = {}
    for f in farther_features:
        for k in feature_keys:
            v = f.get(k) if isinstance(f, dict) else None
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if not (isinstance(v, float) and math.isnan(v)):
                    out.setdefault(k, set()).add(float(v))
    return out


def _gather_calibration_anchors(rubric_data: Optional[dict]) -> list[dict]:
    """Read structured calibration anchors from rubric (cage_meta) AND
    extract numeric mentions from persona/charter prose. Prose extraction
    catches operator-curated anchors that haven't migrated to the
    structured `cage_meta.calibration_anchors` list yet.

    Returned shape: ``[{"value": float, "name": str, "source": str,
    "feature_key": Optional[str]}, ...]``. Generalizable across substrates.
    """
    out: list[dict] = []
    if not isinstance(rubric_data, dict):
        return out

    # 1. Structured anchors (preferred path, post clean-C migration)
    cage_meta = rubric_data.get("cage_meta") or {}
    for a in (cage_meta.get("calibration_anchors") or []):
        if not isinstance(a, dict):
            continue
        try:
            v = float(a.get("expected_value"))
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        out.append({
            "value": v,
            "name": str(a.get("name", "anchor"))[:60],
            "source": "cage_meta.calibration_anchors",
            "feature_key": a.get("applies_to_feature"),
            "tolerance_rel": float(a.get("tolerance_rel", 0.05)),
        })

    # 2. Persona/criteria prose scan — DISABLED 2026-04-26.
    # The naive `(?:[≈~=≃≅])\s*\d+` regex over-matched on threshold
    # phrases like "K = 5-10" and "C = 6·N·D" producing false-positive
    # anchors at 2.0 / 10.0 / 5.0 / 6.0. Migrate substrate anchors to
    # the structured `cage_meta.calibration_anchors` list (option C);
    # operators keeping anchor values in persona prose lose the R20
    # leak-detection but other gates still apply.
    return out


def _gather_substrate_anchor_statistics(
    visible_features: list[dict],
    farther_features: list[dict],
    feature_keys: set[str],
) -> dict[str, dict[str, float]]:
    """Return per-feature anchor statistics that a mutator could
    coincide with. A 'kernel-camouflage' literal in a parametric form
    typically anchors on one of these — visible boundary, withheld
    centroid, span, etc. Generalizable: works on any substrate with
    visible/withheld split.

    Returned shape: ``{feature_key: {"vis_min": .., "vis_max": ..,
    "vis_median": .., "vis_mean": .., "vis_span": ..,
    "wh_min": .., "wh_max": .., "wh_median": .., "wh_mean": ..,
    "wh_span": ..}}``. Statistics that cannot be computed are omitted.
    """
    out: dict[str, dict[str, float]] = {}
    for k in feature_keys:
        vis = [f[k] for f in visible_features
               if isinstance(f, dict) and isinstance(f.get(k), (int, float))
               and not isinstance(f.get(k), bool)
               and not math.isnan(f[k])]
        wh = [f[k] for f in farther_features
              if isinstance(f, dict) and isinstance(f.get(k), (int, float))
              and not isinstance(f.get(k), bool)
              and not math.isnan(f[k])]
        stats: dict[str, float] = {}
        if vis:
            vis_sorted = sorted(vis)
            stats["vis_min"] = float(vis_sorted[0])
            stats["vis_max"] = float(vis_sorted[-1])
            stats["vis_median"] = float(vis_sorted[len(vis_sorted) // 2])
            stats["vis_mean"] = float(sum(vis) / len(vis))
            stats["vis_span"] = float(stats["vis_max"] - stats["vis_min"])
        if wh:
            wh_sorted = sorted(wh)
            stats["wh_min"] = float(wh_sorted[0])
            stats["wh_max"] = float(wh_sorted[-1])
            stats["wh_median"] = float(wh_sorted[len(wh_sorted) // 2])
            stats["wh_mean"] = float(sum(wh) / len(wh))
            stats["wh_span"] = float(stats["wh_max"] - stats["wh_min"])
        if stats:
            out[k] = stats
    return out


# ── Trivial-constant whitelist (shared by R20 and R21) ───────────────


_TRIVIAL_INTEGERS = set(range(-12, 13))  # small structural integers
_TRIVIAL_HALF_INTEGERS = {0.5, -0.5, 1.5, -1.5, 2.5, -2.5}
_TRIVIAL_MATH_CONSTANTS = (
    math.pi, 2 * math.pi, math.pi / 2, math.pi / 4,
    math.e, 1 / math.e,
    math.log(2), math.log(10), 4 * math.log(2),  # 4*ln2 = 2.7725... — McGaugh-style
    math.sqrt(2), 1 / math.sqrt(2), math.sqrt(3),
)
# Tiny safety floors that show up in `max(x, 1e-9)` style guards.
_TRIVIAL_SAFETY_FLOORS = (1e-3, 1e-6, 1e-9, 1e-12)

# 2026-04-27: Published physical constants whitelist. Forms that derive
# their structure from physics need to use {G, c, ℏ, M_sun, ...}
# without those numerical values being flagged as "decision-critical magnitude
# literals" by R20/R21. Without this whitelist the cage falsely caps
# every legitimate Lagrangian-derivation form.
#
# Whitelist criterion: a constant is "published" if it appears in CODATA
# or other authoritative reference tables and the mutator could justify
# its use by citing physics (NOT by fitting to substrate data).
# IMPORTANT: a_0 (MOND) is deliberately EXCLUDED — it's the canonical
# answer this apparatus is supposed to derive, not an input. The .denylist
# enforces this on the prose side; the cage enforces it on the form side.
#
# Tolerance: 1e-3 relative (looser than _TRIVIAL_MATH_CONSTANTS at 1e-4)
# because the mutator may quote constants to fewer digits (e.g. 6.674e-11
# vs 6.67430e-11). The 1e-3 tolerance covers 4 sig figs.
_PUBLISHED_PHYSICAL_CONSTANTS = (
    # SI fundamental constants
    6.67430e-11,        # G (Newton)
    2.99792458e8,       # c (speed of light, exact)
    1.054571817e-34,    # ℏ (reduced Planck)
    6.62607015e-34,     # h (Planck, exact since 2019 SI)
    1.602176634e-19,    # e (elementary charge, exact)
    1.380649e-23,       # k_B (Boltzmann, exact)
    8.8541878128e-12,   # ε₀ (vacuum permittivity)
    1.25663706212e-6,   # μ₀ (vacuum permeability)
    9.1093837015e-31,   # m_e (electron mass)
    1.67262192369e-27,  # m_p (proton mass)
    1.6749274980e-27,   # m_n (neutron mass)
    # Cosmology / astronomy
    1.98847e30,         # M_sun (solar mass)
    1.989e30,           # M_sun (looser quote)
    1.989e+30,          # M_sun (e+ quote)
    5.972e24,           # M_earth
    6.371e6,            # R_earth (m)
    6.957e8,            # R_sun (m)
    3.0856775814913673e19,  # kpc → m (full precision)
    3.0857e19,          # kpc → m (5-digit quote)
    3.086e19,           # kpc → m (4-digit quote)
    3.0857e16,          # pc → m
    3.0857e22,          # Mpc → m
    1.495978707e11,     # AU → m
    9.4607e15,          # ly → m
    3.1557e7,           # year → s
    # Planck units
    2.176434e-8,        # M_Planck (kg)
    2.176e-8,           # M_Planck (loose)
    1.220910e19,        # M_Planck (GeV/c²)
    1.616255e-35,       # ℓ_Planck (m)
    5.391247e-44,       # t_Planck (s)
)


def _is_published_physical_constant(c: float, *, tol_rel: float = 1e-3) -> bool:
    """Return True if `c` matches a published physical constant within
    `tol_rel` (default 1e-3 = 4 sig figs). Sign-agnostic — both +M_sun
    and -M_sun (rare but possible in coupling expressions) match."""
    if not isinstance(c, (int, float)) or isinstance(c, bool):
        return False
    if math.isnan(c) or math.isinf(c):
        return False
    abs_c = abs(c)
    if abs_c < 1e-300:
        return False
    for k in _PUBLISHED_PHYSICAL_CONSTANTS:
        denom = max(abs(k), 1e-15)
        if abs(abs_c - abs(k)) / denom < tol_rel:
            return True
    return False


def _is_trivial_constant(c: float, *, tol_rel: float = 1e-4) -> bool:
    """Return True if `c` is a structural / mathematical constant the
    mutator did not 'choose' as a fitted degree of freedom. Generous
    on the math side (we'd rather under-count than over-flag) so the
    rule remains principled across substrates.

    A constant counts as trivial if ANY of:
      - it's exactly 0 (or numerically negligible vs floor) — neutral identity
      - it's a small integer in [-12, 12] AND |c| ≥ 0.5 (the |c|≥0.5
        guard is critical: 9e-11 rounds to 0 but it's a coupling
        constant, NOT integer zero)
      - it's a half-integer in {±0.5, ±1.5, ±2.5}
      - it's within 1e-4 relative of a canonical math constant
        (π, e, ln2, √2, 4·ln2, etc.)
      - it matches a tiny safety-floor value (1e-3, 1e-6, 1e-9, 1e-12)
        within 1% — only an EXPLICIT safety-floor literal counts; a
        chosen physical constant of similar magnitude does not
    """
    if not isinstance(c, (int, float)):
        return False
    if isinstance(c, bool):
        return False
    if math.isnan(c) or math.isinf(c):
        return False
    if abs(c) < 1e-15:
        return True  # numerical zero — algebraic identity
    # Small-integer match — but require |c| >= 0.5 so we don't fold
    # tiny physical constants (like 9e-11) into the integer-zero bucket.
    if abs(c) >= 0.5 and abs(c - round(c)) < 1e-9 and round(c) in _TRIVIAL_INTEGERS:
        return True
    for h in _TRIVIAL_HALF_INTEGERS:
        if abs(c - h) < 1e-9:
            return True
    for k in _TRIVIAL_MATH_CONSTANTS:
        denom = max(abs(k), 1e-9)
        if abs(c - k) / denom < tol_rel:
            return True
    # Safety-floor literals: tighten to within 1% relative AND require
    # the explicit literal magnitude (so 9e-11 doesn't match 1e-9 floor).
    for f in _TRIVIAL_SAFETY_FLOORS:
        if abs(c - f) / max(abs(f), 1e-12) < 1e-2:
            return True
    # 2026-04-27: Published physical constants (G, c, ℏ, M_sun, etc.) are
    # not "decision-critical magnitude literals" the mutator chose to absorb
    # substrate noise — they're inputs to the form derived from physics.
    # Without this whitelist, R20/R21 cap legitimate Lagrangian-derived
    # forms along with parameter-laundering bridge variants. See
    # _PUBLISHED_PHYSICAL_CONSTANTS for the full list.
    if _is_published_physical_constant(c):
        return True
    return False


# ── R20 — G-WITHHELD-VALUE-LEAKAGE ────────────────────────────────────


@dataclass
class WithheldValueLeakageVerdict:
    flagged: bool = False
    matches: list[dict] = field(default_factory=list)
    n_constants_scanned: int = 0
    n_withheld_values: int = 0

    def to_dict(self) -> dict:
        return {
            "flagged": self.flagged, "matches": self.matches,
            "n_constants_scanned": self.n_constants_scanned,
            "n_withheld_values": self.n_withheld_values,
        }


def check_withheld_value_leakage(
    form_str: str,
    farther_features: list[dict],
    monitored_feature_keys: set[str],
    *,
    visible_features: Optional[list[dict]] = None,
    declared_anchors: Optional[list[dict]] = None,
    relative_tolerance: float = 0.05,
    absolute_tolerance: float = 1e-6,
    log_tolerance_dex: float = 0.15,
) -> WithheldValueLeakageVerdict:
    """Detect form's hardcoded numeric constants that coincide with
    substrate-anchor statistics — withheld feature values, but ALSO
    visible-class boundaries (max, span, median) since a kernel can
    camouflage by anchoring on the cliff between visible and withheld.

    Two distance metrics applied (a match on either flags):
      - **Relative**: ``|c - v| / max(|v|, 1e-9) < relative_tolerance``
      - **Log-space**: ``|log10(|c|) - log10(|v|)| < log_tolerance_dex``
        (catches order-of-magnitude proximity across log-scaled features)

    Generalizable: works on any substrate with a visible/withheld split.
    The visible_features argument is optional — if not supplied the gate
    reverts to the prior withheld-only behavior.
    """
    verdict = WithheldValueLeakageVerdict()
    constants = [c for c in _extract_numeric_constants(form_str)
                 if not _is_trivial_constant(c)]
    verdict.n_constants_scanned = len(constants)
    if not constants:
        return verdict
    # 1. Per-row withheld values (legacy behavior — kept)
    withheld_vals = _gather_withheld_feature_values(
        farther_features or [], monitored_feature_keys
    )
    verdict.n_withheld_values = sum(len(s) for s in withheld_vals.values())
    # 2. Anchor statistics across visible + withheld (generalization)
    anchor_stats = _gather_substrate_anchor_statistics(
        visible_features or [], farther_features or [], monitored_feature_keys
    )

    def _check(c: float, v: float, fkey: str, label: str) -> bool:
        if abs(v) < absolute_tolerance and abs(c) < absolute_tolerance:
            return False  # both ~0; uninformative
        rel_tol = max(absolute_tolerance, relative_tolerance * max(abs(v), abs(c)))
        rel_match = abs(c - v) <= rel_tol
        log_match = False
        if c > 0 and v > 0:
            log_match = abs(math.log10(c) - math.log10(v)) < log_tolerance_dex
        if rel_match or log_match:
            verdict.matches.append({
                "constant_in_form": c,
                "matching_feature_key": fkey,
                "matching_anchor": label,
                "anchor_value": v,
                "abs_diff": abs(c - v),
                "rel_diff": abs(c - v) / max(abs(v), 1e-9),
                "log_diff_dex": (
                    abs(math.log10(c) - math.log10(v))
                    if (c > 0 and v > 0) else None
                ),
                "metric_hit": "relative" if rel_match else "log_space",
            })
            return True
        return False

    for c in constants:
        # Per-row withheld values
        for fkey, vals in withheld_vals.items():
            for v in vals:
                if _check(c, v, fkey, "wh_per_row"):
                    verdict.flagged = True
                    break
        # Anchor statistics (vis_min/max/median/mean/span + wh_*)
        for fkey, stats in anchor_stats.items():
            for stat_name, v in stats.items():
                if _check(c, v, fkey, stat_name):
                    verdict.flagged = True
        # 2026-04-26 (option B): declared calibration anchors from rubric.
        # Catches the persona-leaked / literature-memorized anchor pattern
        # where the mutator hardcodes E ≈ 1.69, α = 0.34, etc. as literals
        # and earns "anchor recovery" credit without actually fitting them.
        for a in (declared_anchors or []):
            v = a.get("value")
            if v is None:
                continue
            tol_rel = float(a.get("tolerance_rel") or relative_tolerance)
            rel_tol = max(absolute_tolerance, tol_rel * max(abs(v), abs(c)))
            rel_match = abs(c - v) <= rel_tol
            log_match = (
                c > 0 and v > 0
                and abs(math.log10(c) - math.log10(v)) < log_tolerance_dex
            )
            if rel_match or log_match:
                verdict.matches.append({
                    "constant_in_form": c,
                    "matching_feature_key": a.get("feature_key") or "<declared-anchor>",
                    "matching_anchor": f"declared:{a.get('name','anchor')}",
                    "anchor_value": v,
                    "abs_diff": abs(c - v),
                    "rel_diff": abs(c - v) / max(abs(v), 1e-9),
                    "log_diff_dex": (
                        abs(math.log10(c) - math.log10(v))
                        if (c > 0 and v > 0) else None
                    ),
                    "metric_hit": "relative" if rel_match else "log_space",
                    "source": a.get("source", "rubric"),
                })
                verdict.flagged = True
    return verdict


def r20_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_withheld_value_leakage_gate", True)):
        return False, "R20 refused: rubric.enable_withheld_value_leakage_gate is false"
    if not getattr(candidate, "form_str", None):
        return False, "R20 refused: no parametric form on candidate"
    return True, "R20 engaged"


def r20_run(substrate: Any, candidate: Any) -> WithheldValueLeakageVerdict:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    monitored = set(rubric.get("withheld_value_leakage_monitored_keys") or [])
    primary = rubric.get("framer_primary_feature_key")
    if primary:
        monitored.add(primary)
    # Default behavior: include EVERY feature key referenced by the form
    # itself — generalizes per-rubric monitored lists. The mutator can
    # only anchor a literal on a feature that appears in the form.
    if getattr(candidate, "form_str", None):
        try:
            for m in re.finditer(
                r"features\[['\"](\w+)['\"]\]", candidate.form_str
            ):
                monitored.add(m.group(1))
        except re.error:
            pass
    if not monitored:
        return WithheldValueLeakageVerdict()
    declared_anchors = _gather_calibration_anchors(rubric)
    return check_withheld_value_leakage(
        form_str=candidate.form_str,
        farther_features=candidate.farther_features or [],
        visible_features=getattr(candidate, "visible_features", None) or [],
        declared_anchors=declared_anchors,
        monitored_feature_keys=monitored,
    )


# ── R21 — G-EFFECTIVE-PARAMETER-COUNT ─────────────────────────────────


@dataclass
class EffectiveParameterCountVerdict:
    declared_k: int = 0
    effective_k: int = 0
    constants_scanned: int = 0
    load_bearing_constants: list[dict] = field(default_factory=list)
    flagged: bool = False

    def to_dict(self) -> dict:
        return {
            "declared_k": self.declared_k, "effective_k": self.effective_k,
            "constants_scanned": self.constants_scanned,
            "load_bearing_constants": self.load_bearing_constants,
            "flagged": self.flagged,
        }


def _find_feature_anchor_literals(form_str: str) -> list[dict]:
    """Walk the form's AST and return every numeric literal that
    appears in a ``(features['k'] - C)`` or ``(features['k'] - C) / C2``
    or ``features['k'] / C`` pattern. These are anchor literals — they
    embed a feature-relative location into the form, which is the
    structural fingerprint of kernel/window camouflage.

    Returned shape: ``[{"value": float, "feature_key": str, "role":
    "offset" | "scale"}, ...]``. Generalizable: any feature, any kind
    of bump.
    """
    out: list[dict] = []
    if not form_str:
        return out
    try:
        tree = ast.parse(form_str, mode="eval")
    except SyntaxError:
        return out

    def _is_feature_subscript(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == "features":
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    return node.slice.value
                # Older AST shapes
                idx = getattr(node.slice, "value", None)
                if isinstance(idx, ast.Constant) and isinstance(idx.value, str):
                    return idx.value
        return None

    def _extract_constant(node: ast.AST) -> Optional[float]:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = _extract_constant(node.operand)
            return -inner if inner is not None else None
        return None

    for node in ast.walk(tree):
        # Pattern: (features['k'] - C) or (features['k'] + C)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Sub, ast.Add)):
            fkey = _is_feature_subscript(node.left)
            const = _extract_constant(node.right)
            if fkey and const is not None:
                out.append({"value": const, "feature_key": fkey, "role": "offset"})
                continue
            # Reversed: (C - features['k']) — also an offset
            fkey_r = _is_feature_subscript(node.right)
            const_l = _extract_constant(node.left)
            if fkey_r and const_l is not None:
                out.append({"value": const_l, "feature_key": fkey_r, "role": "offset"})
                continue
        # Pattern: (... features['k'] ...) / C  — scale literal
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            const = _extract_constant(node.right)
            if const is None:
                continue
            # Only count if the numerator references a feature subscript
            num_features = [
                n for n in ast.walk(node.left)
                if _is_feature_subscript(n) is not None
            ]
            if num_features:
                fkey = _is_feature_subscript(num_features[0]) or "?"
                out.append({"value": const, "feature_key": fkey, "role": "scale"})
    return out


def estimate_effective_parameter_count(
    form_str: str,
    declared_parameter_names: list[str],
    *,
    slack: int = 0,
) -> EffectiveParameterCountVerdict:
    """Count effective parameters in a closed-form expression.

    A constant counts as an effective parameter when:
      1. It is NOT on the trivial-constant whitelist (small integer,
         half-integer, π/e/ln2/√2, tiny safety floor) — those are
         structural, not chosen degrees of freedom.
      2. OR it appears as a feature anchor (``feature - C``,
         ``feature / C``) regardless of magnitude — the choice of
         where to center / how to scale a feature IS a fitted
         degree of freedom.

    Effective K = declared K + (#non-trivial literals not already
    counted as feature anchors) + (#feature-anchor literals). Flag
    fires when ``effective_k - declared_k > slack``.

    Default ``slack=0``: declared K must match. The mutator can opt
    into slack via ``rubric.effective_parameter_count_slack`` but the
    apparatus default is zero — every chosen literal is a parameter.
    """
    verdict = EffectiveParameterCountVerdict()
    verdict.declared_k = len(declared_parameter_names)
    constants = _extract_numeric_constants(form_str)
    verdict.constants_scanned = len(constants)

    # 1. Feature-anchor literals (always count, even if "trivial" magnitude
    #    — the choice of WHERE to center is a degree of freedom).
    anchor_literals = _find_feature_anchor_literals(form_str)
    anchor_values_seen: list[float] = []
    structural_constants: list[dict] = []
    for a in anchor_literals:
        if _is_trivial_constant(a["value"]):
            # Even trivial-magnitude anchors (e.g. (feature - 1)) count
            # as a chosen offset IF the feature has nontrivial scale —
            # but we conservatively allow trivial anchors not to inflate.
            # A feature offset of 1 might be a unit-shift (legitimate);
            # an offset of 11.43 is not. Use the trivial filter.
            continue
        structural_constants.append({
            "value": a["value"], "feature_key": a["feature_key"],
            "role": f"feature_anchor_{a['role']}",
            "reason": "feature-relative literal (offset/scale)",
        })
        anchor_values_seen.append(a["value"])

    # 2. Non-anchor non-trivial constants (multipliers, exponents, etc.)
    for c in constants:
        if _is_trivial_constant(c):
            continue
        # Skip if already counted as a feature-anchor literal
        if any(abs(c - v) < 1e-12 for v in anchor_values_seen):
            continue
        structural_constants.append({
            "value": c, "feature_key": None,
            "role": "magnitude",
            "reason": "non-trivial magnitude literal",
        })

    verdict.load_bearing_constants = structural_constants
    verdict.effective_k = verdict.declared_k + len(structural_constants)
    verdict.flagged = (verdict.effective_k - verdict.declared_k) > slack
    return verdict


def r21_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_effective_parameter_count_gate", True)):
        return False, "R21 refused: rubric.enable_effective_parameter_count_gate is false"
    if not getattr(candidate, "form_str", None):
        return False, "R21 refused: no parametric form on candidate"
    return True, "R21 engaged"


def r21_run(substrate: Any, candidate: Any) -> EffectiveParameterCountVerdict:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    slack = int(rubric.get("effective_parameter_count_slack", 0))
    return estimate_effective_parameter_count(
        form_str=candidate.form_str,
        declared_parameter_names=candidate.parameter_names or [],
        slack=slack,
    )


# ── R22 — APPARATUS-META-RUNNER ───────────────────────────────────────


# R22 catalog patterns — kept ONLY for anti-patterns not covered by the
# structural detectors R20/R21/R24. The 2026-04-26 refactor removed the
# RH-18 regex (now handled by R24's AST detector, which catches the
# Gaussian-bump and sigmoid-window variants the regex missed). RH-13 and
# RH-17 remain regex-based because they detect patterns that aren't
# structurally characterized by literal-anchor or effective-K count.
_RH_PATTERNS = [
    {
        "code": "RH-13",
        "name": "Categorical-as-Continuous Smuggle",
        "regex": re.compile(r"hash\s*\(.*?(modality|study|architecture)", re.IGNORECASE),
        "description": (
            "form hashes a categorical string into an integer and applies "
            "continuous math; substrate's categorical features must be "
            "compared via equality, not arithmetic"
        ),
    },
    {
        "code": "RH-17",
        "name": "Lookup-Table Fallacy",
        "regex": re.compile(
            r"if\s+features\[['\"]\w+['\"]\]\s*==\s*['\"]\w+['\"]\s*else\s+(\d|\-\d|0\.|\.\d)"
        ),
        "description": (
            "explicit class-conditional branch returning a hardcoded numeric "
            "constant; the constant is memorized from the briefing's per-class "
            "diagnostic rather than derived from features"
        ),
    },
]


_RH17_BRANCH_RE = re.compile(
    r"(?P<then>[^()\n?:]+?)\s+if\s+features\[['\"](?P<feature>\w+)['\"]\]\s*==\s*['\"](?P<value>\w+)['\"]\s*else\s+(?P<else>-?(?:\d+(?:\.\d*)?|\.\d+))"
)


def _rh17_is_literal_lookup(match_text: str) -> bool:
    """Return true only for literal categorical lookup branches.

    RH-17 is meant to catch forms like ``1.23 if features['study'] == 'x'
    else 0.98``: the category itself returns a memorized numeric answer.
    It should not catch a declared, optimizer-visible offset such as
    ``params['pC'] if features['fit_convention'] == 'x' else 0.0``. The
    latter is still a categorical branch, but its complexity is counted by
    R21/R24 and its admissibility belongs to the substrate/rubric contract.
    """
    if "params[" in match_text or "params.get" in match_text:
        return False
    return True


@dataclass
class MetaRunnerVerdict:
    flagged: bool = False
    matches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"flagged": self.flagged, "matches": self.matches}


def _rh_codes_from_structural_verdicts(
    r20_verdict: Optional[dict],
    r21_verdict: Optional[dict],
    r24_verdict: Optional[dict],
) -> list[dict]:
    """Translate structural detector verdicts into named RH codes.

    Refactor (2026-04-26): R22 used to run its own RH-18 regex which
    matched only one specific Gaussian-kernel shape and missed the
    iter-4 sigmoid-window escalation. The structural detectors are
    catch-all (any (feature - C) / (feature / C) pattern flips R24)
    so R22 now consumes their verdicts and assigns RH labels.

    Mapping (apparatus-general — not gp163d-specific):

      R24.kernel_window_structure (≥2 anchors on same feature)
        → RH-18 Kernel-Camouflage Lookup Table

      R24.anchor_coincidence (anchor literal == substrate stat)
        → RH-18-ANCHOR Substrate-Anchor Coincidence

      R20.flagged AND R20.matches contain `wh_per_row` or `wh_*` hits
        → RH-18-LITERAL Withheld-Value Literal Match

      R21.flagged with large slack (effective_k - declared_k >= 3)
        → RH-EFFK-LAUNDER Hidden-Parameter Laundering
    """
    codes: list[dict] = []
    r24 = r24_verdict or {}
    r20 = r20_verdict or {}
    r21 = r21_verdict or {}

    # R24 → RH-18 variants
    for m in (r24.get("matches") or []):
        kind = m.get("kind")
        if kind == "kernel_window_structure":
            codes.append({
                "code": "RH-18",
                "name": "Kernel-Camouflage Lookup Table",
                "description": (
                    "form embeds a feature-relative bump or window with hardcoded "
                    "center and width; functionally equivalent to a class-conditional "
                    "lookup table dressed as a smooth function"
                ),
                "evidence_excerpt": str(m.get("rationale", ""))[:300],
                "source_gate": "R24",
            })
        elif kind == "anchor_coincidence":
            codes.append({
                "code": "RH-18-ANCHOR",
                "name": "Substrate-Anchor Coincidence",
                "description": (
                    "feature-relative literal coincides with a substrate-derived "
                    "statistic (visible-class boundary, withheld-class centroid, "
                    "etc.); the form's structure was tuned to substrate prose"
                ),
                "evidence_excerpt": str(m.get("rationale", ""))[:300],
                "source_gate": "R24",
            })

    # R20 → RH-18-LITERAL when withheld-row literals coincide
    if r20.get("flagged"):
        wh_hits = [
            m for m in (r20.get("matches") or [])
            if "wh" in str(m.get("matching_anchor", ""))
        ]
        if wh_hits and not any(c["code"].startswith("RH-18") for c in codes):
            codes.append({
                "code": "RH-18-LITERAL",
                "name": "Withheld-Value Literal Match",
                "description": (
                    "hardcoded literal in form matches a value that appears "
                    "only in the withheld classes; the literal was sourced from "
                    "the briefing rather than from visible-class data"
                ),
                "evidence_excerpt": (
                    f"{len(wh_hits)} literal(s) coincide with withheld-class "
                    f"values across {len(set(m.get('matching_feature_key') for m in wh_hits))} "
                    f"feature(s)"
                )[:300],
                "source_gate": "R20",
            })

    # R21 → RH-EFFK-LAUNDER when many literals are hiding as constants
    if r21.get("flagged"):
        declared = int(r21.get("declared_k") or 0)
        effective = int(r21.get("effective_k") or 0)
        if (effective - declared) >= 3:
            codes.append({
                "code": "RH-EFFK-LAUNDER",
                "name": "Hidden-Parameter Laundering",
                "description": (
                    "form declares K parameters but contains K + N hardcoded "
                    "literals that are structural degrees of freedom (offsets, "
                    "scales, bump amplitudes); declared K hides the model's "
                    "true complexity from BIC and from the optimizer"
                ),
                "evidence_excerpt": (
                    f"declared K={declared}, effective K={effective}, "
                    f"hidden DoF={effective - declared}"
                )[:300],
                "source_gate": "R21",
            })

    return codes


def run_apparatus_meta_match(
    form_str: str,
    thesis_text: Optional[str] = None,
    *,
    r20_verdict: Optional[dict] = None,
    r21_verdict: Optional[dict] = None,
    r24_verdict: Optional[dict] = None,
) -> MetaRunnerVerdict:
    """Map structural detector verdicts to named RH codes; supplement with
    the regex catalog for patterns the structural detectors don't cover
    (RH-13 categorical-as-continuous, RH-17 explicit lookup table).

    Apparatus-general design: R22 is now a translation layer. New
    structural detectors get RH codes for free by extending
    _rh_codes_from_structural_verdicts; new regex-only patterns get
    added to _RH_PATTERNS without touching the structural side.
    """
    verdict = MetaRunnerVerdict()
    if not form_str:
        return verdict
    # 1. Structural-detector-derived codes (primary path)
    structural_codes = _rh_codes_from_structural_verdicts(
        r20_verdict, r21_verdict, r24_verdict,
    )
    for c in structural_codes:
        verdict.matches.append(c)
        verdict.flagged = True

    # 2. Regex-only catalog (orthogonal patterns)
    haystack = form_str + ("\n" + (thesis_text or ""))
    for pat in _RH_PATTERNS:
        if pat["code"] == "RH-17":
            for m in _RH17_BRANCH_RE.finditer(haystack):
                evidence = m.group(0)[:200]
                if not _rh17_is_literal_lookup(evidence):
                    continue
                verdict.matches.append({
                    "code": pat["code"], "name": pat["name"],
                    "description": pat["description"],
                    "evidence_excerpt": evidence,
                })
                verdict.flagged = True
            continue
        m = pat["regex"].search(haystack)
        if m:
            verdict.matches.append({
                "code": pat["code"], "name": pat["name"],
                "description": pat["description"],
                "evidence_excerpt": m.group(0)[:200],
            })
            verdict.flagged = True
    return verdict


def r22_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_apparatus_meta_runner_gate", True)):
        return False, "R22 refused: rubric.enable_apparatus_meta_runner_gate is false"
    if not getattr(candidate, "form_str", None):
        return False, "R22 refused: no parametric form on candidate"
    return True, "R22 engaged"


def r22_run(substrate: Any, candidate: Any) -> MetaRunnerVerdict:
    """R22 as Cage-routed gate. When called via Cage dispatch (no
    pre-computed structural verdicts available), the candidate may
    carry r20/r21/r24 verdicts as attributes from prior gate runs.
    """
    return run_apparatus_meta_match(
        form_str=candidate.form_str,
        thesis_text=getattr(candidate, "thesis_text", None),
        r20_verdict=getattr(candidate, "r20_verdict", None),
        r21_verdict=getattr(candidate, "r21_verdict", None),
        r24_verdict=getattr(candidate, "r24_verdict", None),
    )


# ── R23 — G-SPARSE-CELL-EXCLUSION ─────────────────────────────────────


@dataclass
class SparseCellExclusionVerdict:
    excluded_cells: list[dict] = field(default_factory=list)
    excluded_row_ids: list[int] = field(default_factory=list)
    n_total_farther: int = 0

    def to_dict(self) -> dict:
        return {
            "excluded_cells": self.excluded_cells,
            "excluded_row_ids": self.excluded_row_ids,
            "n_total_farther": self.n_total_farther,
        }


def detect_sparse_cells_for_exclusion(
    farther_features: list[dict],
    farther_row_ids: list[int],
    monitored_categorical_keys: list[str],
    *,
    min_rows_per_cell: int = 2,
) -> SparseCellExclusionVerdict:
    """Find categorical cells with fewer than N rows in farther-tail.
    Those cells get excluded from gate enforcement and surfaced as
    honest_null. The form cannot be R1-struck for failing on substrate
    cells the data cannot constrain.
    """
    verdict = SparseCellExclusionVerdict()
    verdict.n_total_farther = len(farther_features)
    if not farther_features:
        return verdict
    # Group by cell signature across monitored categorical keys
    by_cell: dict[tuple, list[int]] = {}
    for i, f in enumerate(farther_features):
        sig = tuple((k, str(f.get(k, ""))) for k in sorted(monitored_categorical_keys))
        by_cell.setdefault(sig, []).append(i)
    excluded_indices: set[int] = set()
    for sig, idxs in by_cell.items():
        if len(idxs) < min_rows_per_cell:
            verdict.excluded_cells.append({
                "cell_signature": dict(sig),
                "n_rows": len(idxs),
                "row_indices": idxs,
            })
            excluded_indices.update(idxs)
    verdict.excluded_row_ids = [
        farther_row_ids[i] for i in sorted(excluded_indices)
        if i < len(farther_row_ids)
    ]
    return verdict


def r23_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_sparse_cell_exclusion_gate", False)):
        # Default off: opt-in because it changes gate enforcement semantics
        return False, "R23 refused: rubric.enable_sparse_cell_exclusion_gate is false (opt-in)"
    if not getattr(candidate, "farther_features", None):
        return False, "R23 refused: no farther_features on candidate"
    return True, "R23 engaged"


def r23_run(substrate: Any, candidate: Any) -> SparseCellExclusionVerdict:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    monitored = list(rubric.get("sparse_cell_monitored_keys") or [
        "modality", "architecture_class", "distractor_class",
    ])
    min_rows = int(rubric.get("sparse_cell_min_rows", 2))
    return detect_sparse_cells_for_exclusion(
        farther_features=candidate.farther_features,
        farther_row_ids=candidate.farther_row_ids or [],
        monitored_categorical_keys=monitored,
        min_rows_per_cell=min_rows,
    )


# ── R24 — G-FEATURE-BUMP-PATTERN ──────────────────────────────────────


@dataclass
class FeatureBumpPatternVerdict:
    flagged: bool = False
    matches: list[dict] = field(default_factory=list)
    n_anchor_literals: int = 0

    def to_dict(self) -> dict:
        return {
            "flagged": self.flagged, "matches": self.matches,
            "n_anchor_literals": self.n_anchor_literals,
        }


def detect_feature_bump_patterns(
    form_str: str,
    *,
    visible_features: Optional[list[dict]] = None,
    farther_features: Optional[list[dict]] = None,
    monitored_feature_keys: Optional[set[str]] = None,
) -> FeatureBumpPatternVerdict:
    """Detect ``smooth-bump-on-feature`` patterns: any closed-form
    sub-expression where a feature is wrapped in ``(feature - C) / C2``
    (or analogous Gaussian / sigmoid window), with the offset/scale
    constants embedded as literals.

    Two flag conditions, EITHER triggers:
      A. A feature-anchor literal coincides (within 5% relative or
         0.15 dex log-space) with a substrate-anchor statistic
         (visible_max, withheld_mean, etc.) — this is RH-18 kernel
         camouflage with smooth wrapper.
      B. The form contains ≥2 feature-anchor literals on the same
         feature — that's a kernel/window structure (center + width)
         which is a degree of freedom the form should declare as
         parameters, not bake in as constants.

    Generalizable: works on any substrate; the AST walk doesn't
    depend on feature names or substrate class.
    """
    verdict = FeatureBumpPatternVerdict()
    if not form_str:
        return verdict
    anchor_literals = _find_feature_anchor_literals(form_str)
    # Drop trivial anchors (offset by 0/1, scale by 1) — those are
    # unit shifts, not bumps.
    anchor_literals = [a for a in anchor_literals if not _is_trivial_constant(a["value"])]
    verdict.n_anchor_literals = len(anchor_literals)

    # Group anchors by feature to detect kernel/window structure
    by_feature: dict[str, list[dict]] = {}
    for a in anchor_literals:
        by_feature.setdefault(a["feature_key"], []).append(a)

    # Condition B: ≥2 anchor literals on the same feature ⇒ bump structure
    for fkey, anchors in by_feature.items():
        if len(anchors) >= 2:
            verdict.flagged = True
            verdict.matches.append({
                "kind": "kernel_window_structure",
                "feature_key": fkey,
                "anchor_literals": [
                    {"value": a["value"], "role": a["role"]} for a in anchors
                ],
                "rationale": (
                    f"feature {fkey!r} is wrapped in {len(anchors)} "
                    "literal-anchor expressions (offset/scale); this is "
                    "a smooth-bump or sigmoid-window structure with "
                    "hardcoded center and width — declare these as "
                    "fitted parameters or remove the bump"
                ),
            })

    # Condition A: any anchor literal coincides with a substrate-anchor stat
    if monitored_feature_keys:
        anchor_stats = _gather_substrate_anchor_statistics(
            visible_features or [], farther_features or [], monitored_feature_keys
        )
        for a in anchor_literals:
            stats = anchor_stats.get(a["feature_key"], {})
            for stat_name, v in stats.items():
                rel_match = abs(a["value"] - v) / max(abs(v), 1e-9) < 0.05
                log_match = (
                    a["value"] > 0 and v > 0
                    and abs(math.log10(a["value"]) - math.log10(v)) < 0.15
                )
                if rel_match or log_match:
                    verdict.flagged = True
                    verdict.matches.append({
                        "kind": "anchor_coincidence",
                        "feature_key": a["feature_key"],
                        "anchor_literal": a["value"],
                        "anchor_role": a["role"],
                        "matching_substrate_stat": stat_name,
                        "stat_value": v,
                        "rationale": (
                            f"feature-anchor literal {a['value']} on "
                            f"{a['feature_key']!r} coincides with substrate "
                            f"statistic {stat_name}={v}; structurally "
                            "equivalent to RH-18 kernel-camouflage with a "
                            "smooth wrapper"
                        ),
                    })
                    break
    return verdict


def r24_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_feature_bump_pattern_gate", True)):
        return False, "R24 refused: rubric.enable_feature_bump_pattern_gate is false"
    if not getattr(candidate, "form_str", None):
        return False, "R24 refused: no parametric form on candidate"
    return True, "R24 engaged"


def r24_run(substrate: Any, candidate: Any) -> FeatureBumpPatternVerdict:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    monitored = set(rubric.get("withheld_value_leakage_monitored_keys") or [])
    primary = rubric.get("framer_primary_feature_key")
    if primary:
        monitored.add(primary)
    if getattr(candidate, "form_str", None):
        try:
            for m in re.finditer(
                r"features\[['\"](\w+)['\"]\]", candidate.form_str
            ):
                monitored.add(m.group(1))
        except re.error:
            pass
    return detect_feature_bump_patterns(
        form_str=candidate.form_str,
        visible_features=getattr(candidate, "visible_features", None) or [],
        farther_features=candidate.farther_features or [],
        monitored_feature_keys=monitored,
    )


# ── Cage registration ────────────────────────────────────────────────


def register_structural_anti_pattern_gates(cage: Any) -> None:
    """Register R20-R23 with a Cage instance. Called from build_cage_runtime."""
    try:
        from src.ztare.gates.cage import Gate
    except ImportError:
        return
    gates = [
        Gate(name="R20_withheld_value_leakage", phase="POST_FIT",
             can_handle=r20_can_handle, run=r20_run, dependencies=[]),
        Gate(name="R21_effective_parameter_count", phase="POST_FIT",
             can_handle=r21_can_handle, run=r21_run, dependencies=[]),
        Gate(name="R22_apparatus_meta_runner", phase="POST_JUDGE",
             can_handle=r22_can_handle, run=r22_run, dependencies=[]),
        Gate(name="R23_sparse_cell_exclusion", phase="PRE_JUDGE",
             can_handle=r23_can_handle, run=r23_run, dependencies=[]),
        Gate(name="R24_feature_bump_pattern", phase="POST_FIT",
             can_handle=r24_can_handle, run=r24_run, dependencies=[]),
    ]
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        for g in gates:
            cage.gates[g.name] = g
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None


def dispatch_structural_anti_pattern_gates(
    *,
    project_dir: Path,
    rubric_data: dict,
    iter_index: int,
) -> dict:
    """One-call orchestrator entry point. Reads workspace artifacts +
    current iter's PARAMETRIC_FORM, runs R20-R23, writes JSON, returns
    summary for embedding in eval payload + briefing.
    """
    out: dict = {
        "r20_withheld_value_leakage": None,
        "r21_effective_parameter_count": None,
        "r22_apparatus_meta_runner": None,
        "r23_sparse_cell_exclusion": None,
        "r24_feature_bump_pattern": None,
        "any_flag": False,
        "log_lines": [],
    }
    workspace = project_dir / "workspace"

    # Read fit_features_result.json for the current iter's form + params
    fit_path = workspace / "fit_features_result.json"
    form_str = ""
    declared_names: list[str] = []
    if fit_path.exists():
        try:
            fit = json.loads(fit_path.read_text(encoding="utf-8"))
            # 2026-04-26 fix: the actual key in fit_features_result.json is
            # "form" (set by GP-156 fit_primitive_features). Earlier reads
            # for "parametric_form_substituted" / "parametric_form" returned
            # empty for every iter, silently disabling R20/R21/R22/R24.
            # Try the modern "form" key first; fall back to legacy names
            # so older fit primitives still work.
            form_str = str(
                fit.get("form")
                or fit.get("parametric_form_substituted")
                or fit.get("parametric_form")
                or ""
            )
            declared_names = list(fit.get("parameter_names") or [])
        except Exception:
            pass

    # Read gate_harness_result.json for farther_features (via FEATURES dict)
    # AND visible_rows() for visible_features (R20 anchor-stats need both).
    harness_path = workspace / "gate_harness_result.json"
    farther_features: list[dict] = []
    farther_row_ids: list[int] = []
    visible_features: list[dict] = []
    if harness_path.exists():
        try:
            harness = json.loads(harness_path.read_text(encoding="utf-8"))
            for rec in (harness.get("farther_tail") or {}).get("records", []) or []:
                rid = rec.get("id")
                if rid is not None:
                    farther_row_ids.append(int(rid))
            # Load feature dicts via features.py
            import importlib.util as _ilu
            import sys as _sys
            feat_path = project_dir / "features.py"
            if feat_path.exists():
                spec = _ilu.spec_from_file_location("_sapg_features", str(feat_path))
                if spec and spec.loader:
                    if str(project_dir) not in _sys.path:
                        _sys.path.insert(0, str(project_dir))
                    feat_mod = _ilu.module_from_spec(spec)
                    spec.loader.exec_module(feat_mod)
                    FEATURES = getattr(feat_mod, "FEATURES", {})
                    farther_features = [FEATURES[r] for r in farther_row_ids if r in FEATURES]
                    # visible_features for substrate-anchor statistics
                    if hasattr(feat_mod, "visible_rows"):
                        try:
                            visible_features = [
                                tup[2] for tup in feat_mod.visible_rows()
                                if len(tup) >= 3 and isinstance(tup[2], dict)
                            ]
                        except Exception:
                            pass
        except Exception:
            pass

    # Read thesis prose for R22
    thesis_text = None
    thesis_path = project_dir / "thesis.md"
    if thesis_path.exists():
        try:
            thesis_text = thesis_path.read_text(encoding="utf-8")[:5000]
        except Exception:
            pass

    monitored_keys: set = set(rubric_data.get("withheld_value_leakage_monitored_keys") or [])
    primary = rubric_data.get("framer_primary_feature_key")
    if primary:
        monitored_keys.add(primary)
    # Auto-include every feature key referenced by the form. Generalizable:
    # the mutator can only anchor a literal on a feature that's IN the form.
    if form_str:
        try:
            for m in re.finditer(r"features\[['\"](\w+)['\"]\]", form_str):
                monitored_keys.add(m.group(1))
        except re.error:
            pass

    # R20 — withheld-value leakage (tightened: anchors on substrate stats
    # AND declared calibration anchors from rubric — option B 2026-04-26)
    declared_anchors = _gather_calibration_anchors(rubric_data)
    if form_str and (farther_features or visible_features or declared_anchors) and (monitored_keys or declared_anchors):
        v20 = check_withheld_value_leakage(
            form_str=form_str,
            farther_features=farther_features,
            visible_features=visible_features,
            declared_anchors=declared_anchors,
            monitored_feature_keys=monitored_keys,
        )
        out["r20_withheld_value_leakage"] = v20.to_dict()
        if v20.flagged:
            out["any_flag"] = True
            out["log_lines"].append(
                f"🦴 R20 FLAGGED: {len(v20.matches)} hardcoded constant(s) coincide "
                f"with substrate-anchor statistics (RH-18 candidate)"
            )

    # R21 — effective parameter count (tightened: counts feature-anchor literals)
    if form_str:
        slack = int(rubric_data.get("effective_parameter_count_slack", 0))
        v21 = estimate_effective_parameter_count(form_str, declared_names, slack=slack)
        out["r21_effective_parameter_count"] = v21.to_dict()
        if v21.flagged:
            out["any_flag"] = True
            out["log_lines"].append(
                f"🦴 R21 FLAGGED: declared K={v21.declared_k} but effective K={v21.effective_k} "
                f"(decision-critical hardcoded constants: {len(v21.load_bearing_constants)})"
            )

    # R24 — feature-bump pattern detector (NEW, 2026-04-26)
    if form_str:
        v24 = detect_feature_bump_patterns(
            form_str=form_str,
            visible_features=visible_features,
            farther_features=farther_features,
            monitored_feature_keys=monitored_keys,
        )
        out["r24_feature_bump_pattern"] = v24.to_dict()
        if v24.flagged:
            out["any_flag"] = True
            out["log_lines"].append(
                f"🦴 R24 FLAGGED: feature-bump structure detected "
                f"({v24.n_anchor_literals} anchor literal(s); {len(v24.matches)} match(es))"
            )

    # R22 — apparatus meta-runner (refactored: consumes R20/R21/R24 verdicts
    # to assign RH codes, plus orthogonal regex catalog for RH-13/RH-17)
    if form_str:
        v22 = run_apparatus_meta_match(
            form_str, thesis_text,
            r20_verdict=out.get("r20_withheld_value_leakage"),
            r21_verdict=out.get("r21_effective_parameter_count"),
            r24_verdict=out.get("r24_feature_bump_pattern"),
        )
        out["r22_apparatus_meta_runner"] = v22.to_dict()
        if v22.flagged:
            out["any_flag"] = True
            for m in v22.matches:
                src = m.get("source_gate", "regex")
                out["log_lines"].append(
                    f"🦴 R22 FLAGGED [{m['code']}]: {m['name']} (source={src})"
                )

    # R23 — sparse cell exclusion (only if rubric opted in)
    if bool(rubric_data.get("enable_sparse_cell_exclusion_gate", False)) and farther_features:
        monitored_cat = list(rubric_data.get("sparse_cell_monitored_keys") or [
            "modality", "architecture_class", "distractor_class",
        ])
        v23 = detect_sparse_cells_for_exclusion(
            farther_features=farther_features,
            farther_row_ids=farther_row_ids,
            monitored_categorical_keys=monitored_cat,
            min_rows_per_cell=int(rubric_data.get("sparse_cell_min_rows", 2)),
        )
        out["r23_sparse_cell_exclusion"] = v23.to_dict()
        if v23.excluded_cells:
            out["log_lines"].append(
                f"🦴 R23: {len(v23.excluded_cells)} sparse cell(s) excluded "
                f"({len(v23.excluded_row_ids)} rows moved to honest_null)"
            )

    # Persist — but only if the gates actually had data to evaluate.
    # 2026-04-26 fix: when form_str is missing or farther_features is
    # absent, the gate dispatchers refuse upstream and we'd otherwise
    # write a vacuum JSON (flagged=false, n_constants_scanned=0,
    # matches=[]). The audit-gate-effectiveness linter (2B) flags those
    # vacuum verdicts as SUSPICIOUS / HIGH-RISK because they're
    # indistinguishable from the legacy form_str-key-bug fingerprint.
    # Two-state output:
    #   (a) at least one gate ran with real input → write the verdict file
    #   (b) every gate refused upstream → write a refusal stub instead so
    #       the audit can distinguish "gates ran clean" from "gates couldn't run"
    sapg_path = workspace / f"structural_anti_pattern_iter_{iter_index:03d}.json"
    real_run = bool(form_str) and bool(declared_names is not None)
    if not real_run:
        out = {
            "refusal": True,
            "refusal_reason": (
                "no parametric form available at dispatch time — "
                "fit_features_result.json missing or empty"
                if not form_str
                else "no declared parameter names"
            ),
            "any_flag": False,
            "log_lines": ["🦴 R20-R24: refused upstream (no form to scan)"],
        }
    try:
        sapg_path.parent.mkdir(parents=True, exist_ok=True)
        sapg_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    except Exception:
        pass

    return out
