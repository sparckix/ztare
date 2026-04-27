"""GP-152 Framer orchestrator — `frame()` entry point (v2.0).

Public API:
  frame(x, y, meta, rubric_data) -> (framed_x, framed_y, framing_report)

Pipeline:
  1. Scope preconditions: N≥80, fit_score_mode in scope, heteroscedasticity guard,
     low-precision guard. Auto-disable on any fail.
  2. SymmetryScanner → hints.
  3. TransformationEnumerator → admissible (h_in, h_out) pairs.
  4. BranchAndBoundMDLSearch → MDL_v2 over all admissible pairs.
  5. Pick best by lowest MDL.
  6. framer_helped_canary check (caller-provided fit_fn) — if Framer worsens
     the actual solver fit, fall back to identity.
  7. Build framing_report.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from .enumerate import enumerate_pairs, filtration_summary
from .primitives import SIGMA, Primitive
from .report import build_framing_report
from .search import (
    DEFAULT_FIT_DEGREE,
    CandidatePair,
    MDLResult,
    branch_and_bound_search,
    evaluate_pair,
)
from .symmetry import scan_symmetries

MIN_N = 80
HETEROSCEDASTICITY_CORR_THRESHOLD = 0.3
MIN_EFFECTIVE_PRECISION_BITS = 8


def _heteroscedastic_in_frame(
    x_framed: np.ndarray,
    y_framed_residuals: np.ndarray,
    bin_count: int = 5,
    threshold_ratio: float = 5.0,
) -> bool:
    """Bin framed residuals by framed-x; flag heteroscedastic if std-per-bin
    varies > threshold_ratio.

    Per Gemini-Pro v2.1 diagnosis (2026-04-24): the heteroscedasticity check
    must be evaluated in the FRAMED frame, not the raw frame. Wide-dynamic-
    range substrates like y=1/x have residuals that fan out in raw coords by
    derivative geometry (Δy ≈ f'(x)·Δx, and f'(x) explodes near
    singularities), even when the underlying noise is genuinely homoscedastic.
    The fan-out is a coordinate-frame illusion, not real heteroscedasticity.

    In the framed frame (after the Framer chooses the right h_out), a
    well-chosen frame flattens the dynamic range: y_framed = h_out(y) puts
    the data in coords where f' is approximately constant, and the residuals
    are evaluated against the frame's actual dynamic range.
    """
    n = len(x_framed)
    if n < 50:
        return False
    sorted_idx = np.argsort(x_framed)
    bins = np.array_split(y_framed_residuals[sorted_idx], bin_count)
    bin_stds = [float(np.std(b)) if len(b) > 2 else 0.0 for b in bins]
    bin_stds = [s for s in bin_stds if s > 0]
    if len(bin_stds) < 3:
        return False
    ratio = max(bin_stds) / max(min(bin_stds), 1e-30)
    return ratio > threshold_ratio


def _raw_residuals_under_chosen_frame(
    x: np.ndarray, y: np.ndarray, best, deg: int
) -> tuple[np.ndarray, np.ndarray]:
    """Compute (x_raw, residuals_raw) under the Framer's chosen pair.

    Consistent with MDL_v2's σ̂²_raw definition: fit in framed coords, predict
    via h_out⁻¹, compare to raw y. The heteroscedasticity check uses these
    raw-coord residuals — this matches the BIC's raw-coord likelihood
    evaluation. Earlier version checked framed-coord residuals which
    over-fired on h_out=exp-class transforms (multiplicative noise in
    framed coords ≠ heteroscedastic in raw coords).
    """
    pair = best.pair
    x_framed = pair.h_in.h(x)
    y_framed = pair.h_out.h(y)
    x_mean, x_std = float(np.mean(x_framed)), float(np.std(x_framed)) or 1.0
    xn = (x_framed - x_mean) / x_std
    coeffs = np.polyfit(xn, y_framed, deg)
    y_framed_pred = np.polyval(coeffs, xn)
    y_raw_pred = pair.h_out.h_inv(y_framed_pred)
    return x, y - y_raw_pred


def _low_precision(y: np.ndarray) -> bool:
    """Effective precision = log2(range / smallest non-zero increment).
    Below 8 bits → low-precision per spec §1.2.
    """
    y_sorted = np.sort(np.unique(y))
    if len(y_sorted) < 2:
        return True
    diffs = np.diff(y_sorted)
    diffs = diffs[diffs > 0]
    if len(diffs) == 0:
        return True
    smallest = float(np.min(diffs))
    rng = float(np.max(y) - np.min(y))
    if smallest == 0 or rng == 0:
        return True
    bits = np.log2(rng / smallest)
    return bool(bits < MIN_EFFECTIVE_PRECISION_BITS)


def _check_scope(x: np.ndarray, y: np.ndarray, rubric_data: Dict[str, Any]) -> Optional[str]:
    """Return disabled_reason if any precondition fails, else None."""
    n = len(x)
    if n < MIN_N:
        return "N_below_minimum"
    fit_mode = (rubric_data.get("fit_score_mode") or "").lower()
    if fit_mode in ("none", "discrete_exact", "dynamical_lattice"):
        return "fit_score_mode_out_of_scope"
    # GP-166 Fix (2026-04-25 night): also accept enable_fit_primitive_features
    # for N-D substrates. gp163d's rubric explicitly sets enable_fit_primitive=False
    # (because the 1D solver doesn't apply) but enable_fit_primitive_features=True;
    # the framer should still run on the N-D path.
    _fit_1d_on = rubric_data.get("enable_fit_primitive", True)
    _fit_nd_on = rubric_data.get("enable_fit_primitive_features", False)
    if not (_fit_1d_on or _fit_nd_on):
        return "fit_primitive_disabled"
    # Heteroscedasticity check is now POST-framing, not pre — see Gemini-Pro
    # 2026-04-24 diagnosis: raw-coord fan-out is coordinate illusion on
    # wide-dynamic-range data like y=1/x. Pre-framing check moved to
    # _check_post_frame_heteroscedasticity() below.
    if _low_precision(y):
        return "low_effective_precision"
    return None


def _check_post_frame_heteroscedasticity(
    x: np.ndarray, y: np.ndarray, best, deg: int
) -> bool:
    """True if residuals in the FRAMED frame are heteroscedastic.

    Run AFTER the Framer picks (h_in, h_out). If the chosen frame still has
    fan-out in residuals, the heteroscedasticity is genuine (not a
    derivative-geometry illusion). In that case, the v2.0 BIC assumption
    of Gaussian-homoscedastic likelihood breaks and the Framer should
    auto-disable.
    """
    try:
        x_raw, residuals_raw = _raw_residuals_under_chosen_frame(x, y, best, deg)
        return _heteroscedastic_in_frame(x_raw, residuals_raw)
    except Exception:
        return False


def _baseline_result(x: np.ndarray, y: np.ndarray, deg: int) -> Optional[MDLResult]:
    """MDL of (identity, identity) — the no-framing baseline."""
    pair = CandidatePair(h_in=SIGMA["identity"], h_out=SIGMA["identity"])
    return evaluate_pair(x, y, pair, deg=deg)


def frame(
    x: np.ndarray,
    y: np.ndarray,
    meta: Optional[Dict[str, Any]] = None,
    rubric_data: Optional[Dict[str, Any]] = None,
    fit_fn: Optional[Callable] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Run v2.0 Framer; return (transformed_data, framing_report).

    transformed_data is `(h_in(x), h_out(y))`, OR raw `(x, y)` if Framer
    auto-disables.
    """
    meta = meta or {}
    rubric_data = rubric_data or {}
    deg = int(rubric_data.get("framer_fit_degree", DEFAULT_FIT_DEGREE))

    # Step 1: scope check
    disabled = _check_scope(x, y, rubric_data)
    if disabled is not None:
        report = build_framing_report(
            best=None, baseline=None, all_results=[],
            sym_report=scan_symmetries(x, y),
            enumeration_summary=filtration_summary(0, 0, 0),
            framer_engaged=False,
            disabled_reason=disabled,
        )
        return x, y, report

    # Step 2: symmetry scan
    sym_report = scan_symmetries(x, y, sigma_noise=float(rubric_data.get("sigma_noise") or 0))

    # Step 3 + 4: enumerate + search
    pairs = enumerate_pairs(x, y, meta, sym_report)
    n_in = len({p[0] for p in pairs})
    n_out = len({p[2] for p in pairs})
    enum_summary = filtration_summary(n_in, n_out, len(pairs))

    all_results = branch_and_bound_search(x, y, deg=deg)
    if not all_results:
        report = build_framing_report(
            best=None, baseline=None, all_results=[],
            sym_report=sym_report, enumeration_summary=enum_summary,
            framer_engaged=False, disabled_reason="no_admissible_pairs",
        )
        return x, y, report

    best = all_results[0]
    baseline = _baseline_result(x, y, deg=deg)

    # Step 4b: post-framing heteroscedasticity verification (Gemini-Pro
    # v2.1 diagnosis). The check is on residuals in the CHOSEN frame; if
    # they're still heteroscedastic, the underlying noise really isn't
    # Gaussian-homoscedastic and v2.0's BIC assumption breaks.
    #
    # GP-164 wMDL relaxation (2026-04-25 night): when the substrate
    # supplies per-row σ (rubric `framer_sigma_provided=True`), the
    # heteroscedasticity is being explicitly modelled via the weighted
    # χ² loss — auto-disabling on it would suppress framing that the
    # weighted solver can actually exploit. NOTE: the inner MDL search
    # still uses unweighted polyfit; this is acknowledged as F7 in the
    # gp165 audit (weighted-MDL gap inside branch_and_bound_search).
    sigma_provided = bool(rubric_data.get("framer_sigma_provided", False))
    if not sigma_provided and _check_post_frame_heteroscedasticity(x, y, best, deg=deg):
        report = build_framing_report(
            best=baseline, baseline=baseline, all_results=all_results,
            sym_report=sym_report, enumeration_summary=enum_summary,
            framer_engaged=False,
            disabled_reason="heteroscedastic_in_chosen_frame",
        )
        return x, y, report

    # Step 5: pick best, but require positive MDL gain over baseline
    if baseline is not None and best.mdl >= baseline.mdl - 1e-9:
        # No improvement → use identity (baseline)
        report = build_framing_report(
            best=baseline, baseline=baseline, all_results=all_results,
            sym_report=sym_report, enumeration_summary=enum_summary,
            framer_engaged=False, disabled_reason="no_mdl_improvement",
        )
        return x, y, report

    # Apply chosen framing
    framed_x = best.pair.h_in.h(x)
    framed_y = best.pair.h_out.h(y)

    # Step 6: framer_helped_canary (if fit_fn provided)
    canary_payload: Optional[Dict[str, Any]] = None
    if fit_fn is not None:
        try:
            from src.ztare.framer_gates.framer_helped_canary import run_framer_helped_canary
            canary_payload = run_framer_helped_canary(fit_fn, x, y, framed_x, framed_y, best)
            if canary_payload and not canary_payload.get("framer_helped", True):
                report = build_framing_report(
                    best=baseline, baseline=baseline, all_results=all_results,
                    sym_report=sym_report, enumeration_summary=enum_summary,
                    framer_engaged=False, disabled_reason="canary_failed",
                    canary=canary_payload,
                )
                return x, y, report
        except Exception:
            pass

    report = build_framing_report(
        best=best, baseline=baseline, all_results=all_results,
        sym_report=sym_report, enumeration_summary=enum_summary,
        framer_engaged=True, disabled_reason=None,
        canary=canary_payload,
    )
    return framed_x, framed_y, report


# ── R16 Cage adapter (per GP-157 §3a) ─────────────────────────────────


def _r16_parse_evidence_xy(evidence_text: str, independent_vars):
    """Parse (xdata, ydata) from evidence_text using fit_primitive's parser."""
    try:
        from src.ztare.fit.fit_primitive import parse_evidence_for_fitting
        return parse_evidence_for_fitting(evidence_text, independent_vars)
    except Exception:
        return None


def r16_can_handle(substrate, candidate) -> tuple[bool, str]:
    """R16 framer engagement predicate.

    Engages when:
      - rubric.enable_framer is true (framer is opt-IN; observe-mode
        telemetry by default; live-mode behind a separate flag)
      - cage_meta.class in {nd_features, 1d_curve, 1d}
      - candidate exposes a 1D fit_decl (independent_vars length 1)
        AND parsed (x, y) array of length ≥ 80 (the framer's MIN_N
        precondition; below this the MDL search is unreliable)

    The 1D framer is the canonical R16 PRE_FIT path. The N-D framer
    invocation that runs after fit_primitive_features is left direct-
    wired pending a follow-up migration; the data-flow there depends
    on the per-iter fitted-features context and conceptually belongs
    in POST_FIT despite being framer-shaped.
    """
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    meta = getattr(substrate, "meta", {}) or {}
    if not bool(rubric.get("enable_framer", False)):
        return False, "R16 refused: rubric.enable_framer is False"
    cage_class = str(meta.get("class", "") or "").strip().lower()
    if cage_class not in {"nd_features", "1d_curve", "1d"}:
        return False, (
            f"R16 refused: cage_meta.class={cage_class!r} not in "
            f"{{nd_features, 1d, 1d_curve}}"
        )
    fit_decl = getattr(candidate, "fit_decl", None)
    if fit_decl is None:
        return False, "R16 refused: candidate.fit_decl missing (no 1D fit declared)"
    fit_dim = getattr(candidate, "fit_required_dimensionality", None)
    if fit_dim not in (None, 1):
        return False, (
            f"R16 refused: 1D framer engaged only when fit_required_dimensionality "
            f"in (None, 1); got {fit_dim!r}"
        )
    indep = getattr(fit_decl, "independent_vars", None) or []
    if len(indep) != 1:
        return False, (
            f"R16 refused: 1D framer requires single independent var; got "
            f"{len(indep)}"
        )
    return True, "R16 engaged"


def r16_run(substrate, candidate) -> dict:
    """PRE_FIT adapter: parse evidence, run frame() in observe-mode, write
    workspace/framing_report.json. Returns summary dict.
    """
    from pathlib import Path as _Path
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    workspace_dir = _Path(
        getattr(candidate, "workspace_dir", _Path(".") / "workspace")
    )
    fit_decl = getattr(candidate, "fit_decl", None)
    evidence_text = getattr(candidate, "evidence_text", "") or ""
    if fit_decl is None or not evidence_text:
        return {
            "engaged": True,
            "skipped": True,
            "reason": "missing fit_decl or evidence_text on candidate",
        }
    parsed = _r16_parse_evidence_xy(evidence_text, fit_decl.independent_vars)
    if parsed is None:
        return {
            "engaged": True,
            "skipped": True,
            "reason": "evidence parse failed",
        }
    try:
        import numpy as _np
        xdata, ydata = parsed
        x = _np.array(xdata).flatten() if _np.array(xdata).ndim > 1 else _np.array(xdata)
        y = _np.array(ydata)
    except Exception as exc:
        return {
            "engaged": True,
            "skipped": True,
            "reason": f"x/y array build failed: {type(exc).__name__}: {exc}",
        }
    if x.shape[0] != y.shape[0] or x.shape[0] < MIN_N:
        return {
            "engaged": True,
            "skipped": True,
            "reason": f"insufficient rows: x={x.shape[0]} y={y.shape[0]} (need ≥{MIN_N})",
        }
    try:
        _, _, framing_report = frame(
            x=x, y=y,
            meta=rubric.get("framer_meta") or {},
            rubric_data=dict(rubric),
        )
    except Exception as exc:
        return {
            "engaged": True,
            "skipped": True,
            "reason": f"frame() raised: {type(exc).__name__}: {exc}",
        }
    try:
        import json as _json
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / "framing_report.json").write_text(
            _json.dumps(framing_report, indent=2, default=str), encoding="utf-8"
        )
    except Exception:
        pass
    return {
        "engaged": True,
        "framer_engaged": framing_report.get("framer_engaged"),
        "h_in": framing_report.get("h_in"),
        "h_out": framing_report.get("h_out"),
        "MDL_gain_bits": framing_report.get("MDL_gain_bits", 0),
        "disabled_reason": framing_report.get("disabled_reason"),
    }


def register_r16_gate(cage) -> None:
    """Register R16 framer gate (1D PRE_FIT) with a Cage instance.

    Note: the N-D framer invocation that fires after fit_primitive_features
    in autoresearch_loop is not migrated in this commit. It is conceptually
    POST_FIT in the loop's data-flow even though it is framer-shaped, and
    its inputs depend on _vis (per-iter visible pairs) loaded inside the
    fit primitive block. Migrating it requires the dispatcher to be wired
    through that context. Tracked as follow-up.
    """
    try:
        from src.ztare.gates.cage import Gate
    except ImportError:
        return
    g = Gate(
        name="R16_framer_pre_fit",
        phase="PRE_FIT",
        can_handle=r16_can_handle,
        run=r16_run,
        dependencies=[],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[g.name] = g
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None
