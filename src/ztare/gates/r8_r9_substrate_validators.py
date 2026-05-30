"""R8 + R9 Cage-routed gate wrappers.

The deterministic check functions for both reflexive primitives have
existed in ``src/ztare/gates/cage.py`` since v5.0 Phase 3a (gp154-grounded)
but were never wired into a running Cage instance. The 2026-05-06 PM
cross-audit dashboard surfaced this as dead code via two-source
convergence (primitive_roi engagement_rate=0% + gate_telemetry rename
candidates absent from logs).

This module provides the missing wiring layer: ``Gate`` adapters that
route ``check_feature_coverage_adequacy`` (R8) and
``check_target_convention_homogeneity`` (R9) through the Cage's
engagement matrix so they emit to ``cage_engagement.jsonl`` and show
up in the GP-220 ROI scorecard.

Design choice — OPT-IN BY DEFAULT
=================================
Both gates are strict validators that REJECT candidates failing their
checks. To eliminate regression risk on the 156 historical projects
whose substrates may not declare every required field, both gates
refuse to engage unless the rubric explicitly opts in:

  - R8 engages when ``rubric.enable_r8_feature_coverage = True``
  - R9 engages when ``rubric.enable_r9_target_convention_homogeneity = True``

Without the opt-in, the gate's ``can_handle`` returns
``(False, "R8 refused: opt-in flag absent")`` and the candidate is
unaffected. Once the operator flips the default in a particular
rubric, R8/R9 begin policing that project's candidates.

This mirrors the R10/R11/R20-R24 pattern (every Cage-routed gate added
since GP-157 §3a uses opt-in flags).
"""
from __future__ import annotations

import re
from typing import Any

from src.ztare.gates.cage import (
    Gate,
    check_feature_coverage_adequacy,
    check_target_convention_homogeneity,
)

# Regex pulls keys out of ``features['key_name']`` and ``features["key_name"]``
# references in a parametric form. Conservative — only matches the
# canonical Python access syntax. py_exec / function-body forms that
# use other access patterns will produce an empty referenced-key set
# and cause R8 to no-op (returns "nothing to check").
_FEATURES_KEY_RE = re.compile(r"features\[['\"]([^'\"]+)['\"]\]")


def _extract_referenced_keys(parametric_form: str) -> set[str]:
    return set(_FEATURES_KEY_RE.findall(parametric_form or ""))


def _candidate_visible_rows(candidate: Any) -> list[tuple[Any, ...]]:
    """Convert ``candidate.visible_features`` (list of feature dicts)
    into the (id, y, features_dict) row shape that the R8/R9 checks
    expect. Returns empty list if visible_features is missing or
    malformed."""
    raw = getattr(candidate, "visible_features", None) or []
    rows: list[tuple[Any, ...]] = []
    for i, feats in enumerate(raw):
        if isinstance(feats, dict):
            rows.append((i, None, feats))
    return rows


# ── R8 ────────────────────────────────────────────────────────────────


def r8_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """R8 engages when:
      - rubric opts in via ``enable_r8_feature_coverage``
      - candidate has a non-empty parametric_form
      - candidate has visible_features (rows to check coverage against)
      - the form references at least one ``features['x']`` key
    """
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_r8_feature_coverage", False)):
        return False, "R8 refused: rubric.enable_r8_feature_coverage is false"
    form = str(getattr(candidate, "parametric_form", "") or "").strip()
    if not form:
        return False, "R8 refused: candidate.parametric_form is missing or empty"
    rows = _candidate_visible_rows(candidate)
    if not rows:
        return False, "R8 refused: candidate.visible_features is missing or empty"
    referenced = _extract_referenced_keys(form)
    if not referenced:
        return False, (
            "R8 refused: parametric_form references no features[] keys "
            "(form may use a non-canonical access pattern)"
        )
    return True, "R8 engaged"


def r8_run(substrate: Any, candidate: Any) -> dict[str, Any]:
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    threshold = float(rubric.get("r8_min_coverage_fraction", 0.30))
    form = str(getattr(candidate, "parametric_form", "") or "")
    referenced = _extract_referenced_keys(form)
    rows = _candidate_visible_rows(candidate)
    ok, diag = check_feature_coverage_adequacy(
        referenced, rows, min_coverage_fraction=threshold
    )
    return {
        "ok": bool(ok),
        "diagnostic": diag,
        "min_coverage_fraction": threshold,
        "referenced_keys": sorted(referenced),
    }


# ── R9 ────────────────────────────────────────────────────────────────


def r9_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """R9 engages when:
      - rubric opts in via ``enable_r9_target_convention_homogeneity``
      - substrate.meta declares ``target_convention_homogeneity`` (one
        of "homogeneous" | "heterogeneous")
      - candidate has a parametric_form (heterogeneous case requires
        the form to check for fit_convention reference)
      - candidate has visible_features (homogeneous case checks rows
        share fit_convention)
    """
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_r9_target_convention_homogeneity", False)):
        return False, "R9 refused: rubric.enable_r9_target_convention_homogeneity is false"
    meta = getattr(substrate, "meta", {}) or {}
    hom = meta.get("target_convention_homogeneity")
    if hom not in ("homogeneous", "heterogeneous"):
        return False, (
            f"R9 refused: substrate.meta.target_convention_homogeneity={hom!r} "
            f"is not declared as 'homogeneous' or 'heterogeneous'"
        )
    rows = _candidate_visible_rows(candidate)
    if not rows:
        return False, "R9 refused: candidate.visible_features is missing or empty"
    if hom == "heterogeneous":
        form = str(getattr(candidate, "parametric_form", "") or "").strip()
        if not form:
            return False, (
                "R9 refused: heterogeneous substrate but candidate.parametric_form "
                "is missing — nothing to check for fit_convention reference"
            )
    return True, "R9 engaged"


def r9_run(substrate: Any, candidate: Any) -> dict[str, Any]:
    rows = _candidate_visible_rows(candidate)
    form = getattr(candidate, "parametric_form", None)
    ok, diag = check_target_convention_homogeneity(substrate, rows, form)
    return {"ok": bool(ok), "diagnostic": diag}


# ── Registration ──────────────────────────────────────────────────────


def register_r8_r9_gates(cage: Any) -> None:
    """Register R8 + R9 with a Cage instance.

    Called from ``build_cage_runtime`` in
    ``src/ztare/orchestrator/state.py`` after R10/R11 + R170 + R13/R14/R15/R16
    + R20-R23. Per GP-157 §3a, gate auto-loads based on cage_meta and
    rubric flags rather than autoresearch_loop direct-wire.

    Both gates are PRE_FIT (run before scipy fit; reject candidates
    that reference missing-coverage features or violate convention
    homogeneity declarations). No ordering dependencies on other gates.
    """
    r8 = Gate(
        name="R8_feature_coverage_adequacy",
        phase="PRE_FIT",
        can_handle=r8_can_handle,
        run=r8_run,
        dependencies=[],
    )
    r9 = Gate(
        name="R9_target_convention_homogeneity",
        phase="PRE_FIT",
        can_handle=r9_can_handle,
        run=r9_run,
        dependencies=[],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[r8.name] = r8
        cage.gates[r9.name] = r9
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None
