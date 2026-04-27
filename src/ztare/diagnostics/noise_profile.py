"""GP-166 Statistical Meta-Diagnostics — pre-flight noise-profile classifier.

The premise (per Gemini-Pro 2026-04-25 night, validating the operator's
recursive-self-improvement question): ZTARE has historically hardcoded
i.i.d.-Gaussian assumptions into its solver path. The wMDL update fixed
the "Identically Distributed" half (per-row σ allowed). Three more
silent assumptions remain:

  1. Independent variables (X) measured perfectly — fails on any real
     measurement (radii, masses, redshifts have errors).  → ODR.
  2. Gaussian residuals — fails on Poisson counts, heavy-tail noise,
     sensor spikes. → Huber / Cauchy robust loss.
  3. Independent residuals — fails on time series, spatial fields,
     anything autocorrelated. → covariance-matrix Mahalanobis.

The apparatus must MEASURE these properties on the data it actually
sees, not assume them. This module runs four cheap statistical tests
on a baseline-fit residual series and returns a NoiseProfile verdict
that the dispatch site uses to auto-route the solver.

The four tests:

  * Heteroscedasticity → Breusch-Pagan correlation of squared residuals
    with predictor; threshold p < 0.01.
  * Non-Gaussian → Shapiro-Wilk for n < 5000, else Jarque-Bera; flag
    when p < 0.01 OR |skew| > 1 OR kurtosis > 5 (heavy tail).
  * Autocorrelation → Durbin-Watson statistic; flag when DW < 1.5 or
    DW > 2.5 (significant lag-1 autocorrelation).
  * Errors-in-X → checks feature dict for `sigma_x_*` keys explicitly
    declared by the substrate; ALSO flags when the primary feature's
    inter-row spacing variance suggests measured-not-controlled values.

Public API:

    profile = classify_noise_profile(visible_data, primary_feature_key)
    rubric_updates = auto_route_solver(profile, rubric_data)

Both are pure functions: classify_noise_profile reads only data;
auto_route_solver returns a dict of rubric flag updates without
mutating the input. The dispatch hook applies updates only for flags
not already set explicitly by the operator (operator-set flags
always win).

Backward-compat: this module is opt-in via rubric flag
`enable_noise_profile_diagnostic=True`. Default off; existing
substrates unchanged.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import numpy as np


# ── Verdict object ────────────────────────────────────────────────────


@dataclass
class NoiseProfile:
    """Result of running the four meta-diagnostics on a substrate.

    Each `needs_*` flag is the apparatus's verdict that the standard
    OLS-Gaussian-i.i.d. assumption is broken in that axis. The
    `evidence` dict carries the raw test statistics and p-values so
    the operator (and the audit trail) can see WHY the apparatus
    routed the way it did.
    """
    needs_weighted: bool = False        # heteroscedasticity → weighted χ²
    needs_robust: bool = False          # non-Gaussian residuals → Huber/Cauchy
    needs_correlated: bool = False      # autocorrelation → covariance solver
    needs_odr: bool = False             # errors in X → ODR solver
    n_rows_tested: int = 0
    baseline_form: str = ""             # which baseline fit produced residuals
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable one-line summary for run-log printing."""
        flags = []
        if self.needs_weighted:
            flags.append("WEIGHTED")
        if self.needs_robust:
            flags.append("ROBUST")
        if self.needs_correlated:
            flags.append("CORRELATED")
        if self.needs_odr:
            flags.append("ODR")
        if not flags:
            return f"OLS-i.i.d.-Gaussian OK (n={self.n_rows_tested}, baseline={self.baseline_form})"
        return f"non-i.i.d. detected: {' + '.join(flags)} (n={self.n_rows_tested}, baseline={self.baseline_form})"


# ── Baseline fit (provides residuals for the four tests) ──────────────


def _fit_baseline(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, str]:
    """Return (residuals, form_label) from a cheap baseline fit.

    Strategy: try linear, log-linear, log-log, and degree-3 polynomial,
    pick the one with the SMALLEST mean absolute residual (relative to
    |y|). This matters because residual-based diagnostics (BP, SW, DW)
    confuse systematic-trend leftover with noise structure: a misfit
    baseline on linear data will show fan-out residuals that look
    heteroscedastic. Degree-3 polynomial in raw coords absorbs most
    realistic monotonic trends so the residuals reflect the noise
    profile, not the model misspecification.

    Returns residuals in raw y coordinates so the tests see the same
    units the downstream solver would.
    """
    if len(x) < 5:
        return np.array([]), "insufficient_rows"

    candidates: list[tuple[float, np.ndarray, str]] = []

    def _score(res: np.ndarray) -> float:
        """Lower is better: mean |residual| / mean |y|."""
        my = float(np.mean(np.abs(y))) if np.any(y) else 1.0
        return float(np.mean(np.abs(res))) / max(my, 1e-300)

    # Linear in raw coords
    try:
        a, b = np.polyfit(x, y, 1)
        res = y - (a * x + b)
        candidates.append((_score(res), res, "linear"))
    except (np.linalg.LinAlgError, ValueError, FloatingPointError):
        pass

    # Degree-3 polynomial in raw coords — absorbs monotonic curvature
    # so residuals reflect noise, not model shape. Critical for getting
    # clean signals on the four diagnostics. Need enough rows or the
    # poly itself overfits and produces artificially small residuals.
    if len(x) >= 12:
        try:
            coeffs = np.polyfit(x, y, 3)
            y_pred = np.polyval(coeffs, x)
            res = y - y_pred
            candidates.append((_score(res), res, "poly3"))
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            pass

    # Log-log (power-law-ish data)
    if (x > 0).all() and (y > 0).all():
        try:
            lx, ly = np.log(x), np.log(y)
            a, b = np.polyfit(lx, ly, 1)
            y_pred = np.exp(a * lx + b)
            res = y - y_pred
            candidates.append((_score(res), res, "loglog_linear"))
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            pass

    # Semi-log on y (exponential growth)
    if (y > 0).all():
        try:
            ly = np.log(y)
            a, b = np.polyfit(x, ly, 1)
            y_pred = np.exp(a * x + b)
            res = y - y_pred
            candidates.append((_score(res), res, "semilogy_linear"))
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            pass

    if not candidates:
        return np.array([]), "all_baselines_failed"

    candidates.sort(key=lambda t: t[0])
    _, best_res, best_form = candidates[0]
    return best_res, best_form


# ── Detector 1: heteroscedasticity (Breusch-Pagan) ────────────────────


def _detect_heteroscedasticity(
    residuals: np.ndarray, x: np.ndarray
) -> dict[str, Any]:
    """Breusch-Pagan-style: regress squared residuals on predictor.

    H0: residual variance is constant in x.
    H1: variance is a function of x (heteroscedastic).
    Flag when correlation p-value < 0.01.
    """
    if len(residuals) < 20:
        return {"verdict": False, "reason": "insufficient_n", "n": len(residuals)}
    sq_res = residuals ** 2
    try:
        from scipy.stats import pearsonr
        r, p = pearsonr(x, sq_res)
    except Exception as e:
        return {"verdict": False, "reason": f"pearsonr_failed:{e}"}
    return {
        "verdict": bool(p < 0.01 and abs(r) > 0.15),
        "test": "breusch_pagan_proxy_pearson_sq_residuals_vs_x",
        "r": float(r),
        "p": float(p),
        "n": len(residuals),
    }


# ── Detector 2: non-Gaussian residuals ────────────────────────────────


def _detect_non_gaussian(residuals: np.ndarray) -> dict[str, Any]:
    """Shapiro-Wilk for n<5000, Jarque-Bera otherwise. Also flag heavy
    tails via |skew| > 1 or excess kurtosis > 5 even when SW/JB pass —
    a clean Gaussian has skew≈0, kurt≈3.
    """
    n = len(residuals)
    if n < 8:
        return {"verdict": False, "reason": "insufficient_n", "n": n}
    from scipy.stats import shapiro, jarque_bera, skew, kurtosis
    try:
        if n <= 5000:
            stat, p = shapiro(residuals)
            test_name = "shapiro_wilk"
        else:
            stat, p = jarque_bera(residuals)
            test_name = "jarque_bera"
        sk = float(skew(residuals))
        kt = float(kurtosis(residuals, fisher=False))  # not excess
    except Exception as e:
        return {"verdict": False, "reason": f"test_failed:{e}"}
    heavy_tail = abs(sk) > 1.0 or kt > 5.0
    fails_normality = p < 0.01
    return {
        "verdict": bool(fails_normality or heavy_tail),
        "test": test_name,
        "stat": float(stat),
        "p": float(p),
        "skew": sk,
        "kurtosis_pearson": kt,
        "heavy_tail_flag": heavy_tail,
        "n": n,
    }


# ── Detector 3: autocorrelation (Durbin-Watson) ───────────────────────


def _detect_autocorrelation(
    residuals: np.ndarray, x: np.ndarray
) -> dict[str, Any]:
    """Durbin-Watson on residuals ordered by predictor. DW=2 → no
    autocorrelation; DW<1.5 or DW>2.5 → significant lag-1.
    """
    n = len(residuals)
    if n < 20:
        return {"verdict": False, "reason": "insufficient_n", "n": n}
    order = np.argsort(x)
    r_ord = residuals[order]
    diff = np.diff(r_ord)
    dw = float(np.sum(diff ** 2) / (np.sum(r_ord ** 2) + 1e-300))
    return {
        "verdict": bool(dw < 1.5 or dw > 2.5),
        "test": "durbin_watson",
        "dw": dw,
        "n": n,
        "interpretation": "DW<1.5: positive autocorr; DW>2.5: negative autocorr",
    }


# ── Detector 4: errors-in-X ───────────────────────────────────────────


def _detect_errors_in_x(
    visible_data: list[tuple[dict, float]],
    primary_feature_key: str,
) -> dict[str, Any]:
    """Two paths:
      (a) substrate explicitly declares per-row sigma_x_* keys → confirmed.
      (b) heuristic: spacing variance of primary x suggests measurement
          (irregular spacing) vs control (uniform spacing). Soft hint only.
    """
    if not visible_data:
        return {"verdict": False, "reason": "empty_data"}
    sample_keys = list(visible_data[0][0].keys())
    # Path (a): explicit sigma_x_* declaration
    sigma_x_keys = [
        k for k in sample_keys
        if k.startswith("sigma_x") or k.startswith("err_x")
        or k == f"sigma_{primary_feature_key}" or k == f"err_{primary_feature_key}"
    ]
    if sigma_x_keys:
        # Verify at least one row has a positive value
        has_positive = any(
            isinstance(f.get(k), (int, float)) and f.get(k, 0) > 0
            for f, _ in visible_data
            for k in sigma_x_keys
        )
        return {
            "verdict": bool(has_positive),
            "test": "explicit_sigma_x_declaration",
            "sigma_x_keys_found": sigma_x_keys,
            "n_with_positive": int(sum(
                1 for f, _ in visible_data
                if any(isinstance(f.get(k), (int, float)) and f.get(k, 0) > 0
                       for k in sigma_x_keys)
            )),
        }
    # Path (b): spacing-variance heuristic (soft, never returns True alone —
    # operator must explicitly opt into ODR via rubric flag).
    xs = []
    for feats, _ in visible_data:
        v = feats.get(primary_feature_key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            xs.append(float(v))
    if len(xs) < 20:
        return {"verdict": False, "reason": "insufficient_xs", "n": len(xs)}
    xs_sorted = sorted(xs)
    diffs = np.diff(xs_sorted)
    if len(diffs) < 2 or diffs.std() == 0:
        return {"verdict": False, "test": "spacing_uniform_no_signal"}
    cv = float(diffs.std() / (abs(diffs.mean()) + 1e-300))
    return {
        "verdict": False,  # heuristic only; never auto-routes ODR alone
        "test": "spacing_cv_heuristic",
        "spacing_cv": cv,
        "hint": (
            f"primary feature spacing CV={cv:.2f}; if >0.5 the substrate "
            f"may have measured (not controlled) X — consider ODR via "
            f"explicit `enable_odr=True` and per-row sigma_x_*."
        ),
    }


# ── Public: classify + auto-route ─────────────────────────────────────


def classify_noise_profile(
    visible_data: list[tuple[dict, float]],
    primary_feature_key: str = "x",
    *,
    min_rows: int = 20,
) -> NoiseProfile:
    """Run the four meta-diagnostics on visible_data and return verdict.

    Args:
        visible_data: list of (features_dict, y_observed). Must expose
            primary_feature_key in the features dict.
        primary_feature_key: which feature to use as the predictor for
            the baseline fit + heteroscedasticity / autocorrelation
            tests. Default 'x' matches substrate convention.
        min_rows: refuse to classify on fewer than this many rows
            (defaults to 20; below that all tests are too noisy).

    Returns:
        NoiseProfile with four verdict flags + evidence dict.
    """
    if len(visible_data) < min_rows:
        return NoiseProfile(
            n_rows_tested=len(visible_data),
            baseline_form="skipped_too_few_rows",
            warnings=[
                f"only {len(visible_data)} rows < min_rows={min_rows}; "
                f"diagnostics skipped, defaults retained"
            ],
        )

    # Project to 1D primary axis for the four scalar tests
    xs, ys = [], []
    for feats, y in visible_data:
        v = feats.get(primary_feature_key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            try:
                xs.append(float(v))
                ys.append(float(y))
            except (TypeError, ValueError):
                continue
    if len(xs) < min_rows:
        return NoiseProfile(
            n_rows_tested=len(xs),
            baseline_form=f"primary_key_{primary_feature_key!r}_not_numeric",
            warnings=[
                f"primary feature {primary_feature_key!r} produced "
                f"{len(xs)} numeric rows < {min_rows}"
            ],
        )

    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    residuals, baseline_form = _fit_baseline(x, y)

    profile = NoiseProfile(
        n_rows_tested=len(x),
        baseline_form=baseline_form,
    )

    if len(residuals) == 0:
        profile.warnings.append(f"baseline fit failed: {baseline_form}")
        return profile

    # Detector 1: heteroscedasticity
    h_evidence = _detect_heteroscedasticity(residuals, x)
    profile.evidence["heteroscedasticity"] = h_evidence
    profile.needs_weighted = bool(h_evidence.get("verdict", False))

    # Detector 2: non-Gaussian
    g_evidence = _detect_non_gaussian(residuals)
    profile.evidence["normality"] = g_evidence
    profile.needs_robust = bool(g_evidence.get("verdict", False))

    # Detector 3: autocorrelation
    a_evidence = _detect_autocorrelation(residuals, x)
    profile.evidence["autocorrelation"] = a_evidence
    profile.needs_correlated = bool(a_evidence.get("verdict", False))

    # Detector 4: errors-in-X
    x_evidence = _detect_errors_in_x(visible_data, primary_feature_key)
    profile.evidence["errors_in_x"] = x_evidence
    profile.needs_odr = bool(x_evidence.get("verdict", False))

    return profile


def classify_residuals(
    residuals: Iterable[float],
    x_values: Iterable[float],
    *,
    label: str = "post_fit",
) -> NoiseProfile:
    """Classify residuals from an *already fitted* model.

    Sibling to `classify_noise_profile`: skips the baseline-fit step
    and runs the four diagnostics directly on the supplied residuals.
    Use this for per-iter checks — it tells you whether the FITTED
    MODEL'S residuals are well-behaved (good fit, clean noise) or
    show structure (model misspecification, missing feature).

    Args:
        residuals: per-row residuals (y_obs - y_pred) from the fit.
        x_values: predictor used for heteroscedasticity / autocorr
            tests; must be aligned with residuals row-by-row.
        label: short tag stored in baseline_form for audit ("post_fit",
            "champion_iter_5", etc.)

    Returns:
        NoiseProfile with the four flags set by the same detectors as
        the pre-flight path.
    """
    res = np.asarray(list(residuals), dtype=float)
    x = np.asarray(list(x_values), dtype=float)
    if len(res) != len(x):
        raise ValueError(
            f"residuals and x_values must have same length "
            f"(got {len(res)} vs {len(x)})"
        )
    profile = NoiseProfile(
        n_rows_tested=len(res),
        baseline_form=label,
    )
    if len(res) < 20:
        profile.warnings.append(
            f"only {len(res)} rows < 20; per-iter diagnostics skipped"
        )
        return profile

    h_evidence = _detect_heteroscedasticity(res, x)
    profile.evidence["heteroscedasticity"] = h_evidence
    profile.needs_weighted = bool(h_evidence.get("verdict", False))

    g_evidence = _detect_non_gaussian(res)
    profile.evidence["normality"] = g_evidence
    profile.needs_robust = bool(g_evidence.get("verdict", False))

    a_evidence = _detect_autocorrelation(res, x)
    profile.evidence["autocorrelation"] = a_evidence
    profile.needs_correlated = bool(a_evidence.get("verdict", False))

    # Errors-in-X requires feature-dict access; not applicable for
    # residual-only classification. Leave needs_odr=False; pre-flight
    # is the canonical place to detect that.

    return profile


def auto_route_solver(
    profile: NoiseProfile,
    rubric_data: dict,
) -> dict[str, Any]:
    """Return rubric flag updates implied by the noise profile.

    Operator-set flags always win — this only proposes flags the
    operator did NOT explicitly set. Returns a dict of {key: value}
    pairs the dispatch site should merge IF the key is absent from
    rubric_data.

    Returned keys (when applicable):
      * fit_weighted_residuals: True (if needs_weighted)
      * fit_robust_loss: "huber" (if needs_robust; placeholder until
        the robust-loss path is implemented in fit_primitive_features)
      * fit_correlated_errors: True (if needs_correlated; placeholder
        until covariance solver is implemented)
      * fit_use_odr: True (if needs_odr; placeholder until ODR path
        is implemented)
      * framer_sigma_provided: True (mirrored when fit_weighted_residuals
        is auto-set, matching the existing dispatch-site logic)

    Each entry also gets a *_reason key carrying the test evidence so
    the run log shows WHY each flag flipped.
    """
    updates: dict[str, Any] = {}

    if profile.needs_weighted and "fit_weighted_residuals" not in rubric_data:
        updates["fit_weighted_residuals"] = True
        h = profile.evidence.get("heteroscedasticity", {})
        updates["fit_weighted_residuals_reason"] = (
            f"auto-routed by GP-166 noise profile diagnostic: "
            f"heteroscedasticity detected ({h.get('test', '?')} "
            f"r={h.get('r', 0):.3f} p={h.get('p', 1):.3g} on "
            f"n={profile.n_rows_tested}). Operator can override by "
            f"setting fit_weighted_residuals explicitly in rubric.json."
        )
        if "framer_sigma_provided" not in rubric_data:
            updates["framer_sigma_provided"] = True

    if profile.needs_robust and "fit_robust_loss" not in rubric_data:
        g = profile.evidence.get("normality", {})
        updates["fit_robust_loss"] = "huber"
        updates["fit_robust_loss_reason"] = (
            f"auto-routed by GP-166 noise profile diagnostic: "
            f"non-Gaussian residuals ({g.get('test', '?')} "
            f"p={g.get('p', 1):.3g}, skew={g.get('skew', 0):.2f}, "
            f"kurt={g.get('kurtosis_pearson', 3):.2f}). NOTE: robust "
            f"loss path is NOT YET WIRED in fit_primitive_features — "
            f"this flag currently telemetry-only until implementation."
        )

    if profile.needs_correlated and "fit_correlated_errors" not in rubric_data:
        a = profile.evidence.get("autocorrelation", {})
        updates["fit_correlated_errors"] = True
        updates["fit_correlated_errors_reason"] = (
            f"auto-routed by GP-166 noise profile diagnostic: "
            f"residual autocorrelation detected (DW={a.get('dw', 2):.2f}). "
            f"NOTE: covariance/Mahalanobis solver path is NOT YET WIRED "
            f"in fit_primitive_features — telemetry-only until "
            f"implementation."
        )

    if profile.needs_odr and "fit_use_odr" not in rubric_data:
        x = profile.evidence.get("errors_in_x", {})
        updates["fit_use_odr"] = True
        updates["fit_use_odr_reason"] = (
            f"auto-routed by GP-166 noise profile diagnostic: "
            f"explicit sigma_x declared ({x.get('sigma_x_keys_found', [])}). "
            f"NOTE: scipy.odr path is NOT YET WIRED in "
            f"fit_primitive_features — telemetry-only until "
            f"implementation."
        )

    return updates


# ── R14 Cage adapters (per GP-157 §3a) ────────────────────────────────


def _r14_load_visible_pairs(project_dir: "Path") -> list:  # type: ignore  # noqa: F821
    """Load (features, y) pairs for the visible rows from features.py.

    Returns [] on any failure — failure is non-fatal.
    """
    from pathlib import Path as _Path
    visible: list = []
    try:
        import importlib.util as _ilu
        feat_path = _Path(project_dir) / "features.py"
        if not feat_path.exists():
            return visible
        spec = _ilu.spec_from_file_location(
            "_r14_noise_profile_features", str(feat_path)
        )
        if spec is None or spec.loader is None:
            return visible
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "visible_rows"):
            for t in mod.visible_rows():
                if len(t) >= 3:
                    visible.append((t[2], t[1]))
    except Exception:
        return visible
    return visible


def r14_can_handle(substrate: "Any", candidate: "Any") -> tuple[bool, str]:  # type: ignore  # noqa: F821
    """R14 noise_profile engagement predicate.

    Engages when:
      - cage_meta.class in {nd_features, time_series, 1d_curve, 1d}
      - rubric does NOT explicitly disable via `disable_noise_profile: true`

    `1d` is included as the canonical class label; `1d_curve` retained
    for legacy rubrics. Visible row count check (≥20) happens at run-time
    inside classify_noise_profile so it is not duplicated here.

    Backward-compat: legacy rubrics with `enable_noise_profile: false`
    are also respected as an explicit disable signal.
    """
    meta = getattr(substrate, "meta", {}) or {}
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    cage_class = str(meta.get("class", "") or "").strip().lower()
    if cage_class not in {"nd_features", "time_series", "1d_curve", "1d"}:
        return False, (
            f"R14 refused: cage_meta.class={cage_class!r} not in "
            f"{{nd_features, time_series, 1d, 1d_curve}}; noise profile "
            f"detectors require numeric primary axis + scalar y."
        )
    if bool(rubric.get("disable_noise_profile", False)):
        return False, "R14 refused: rubric.disable_noise_profile is true"
    if "enable_noise_profile" in rubric and not bool(
        rubric.get("enable_noise_profile")
    ):
        return False, (
            "R14 refused: rubric.enable_noise_profile is explicitly false "
            "(legacy opt-out)"
        )
    return True, "R14 engaged"


def r14_run_preflight(substrate: "Any", candidate: "Any") -> dict:  # type: ignore  # noqa: F821
    """PRE_FIT (preflight) adapter: classify noise on the substrate's
    visible rows and persist workspace/noise_profile.json. Auto-routes
    rubric flags via auto_route_solver, mutating the rubric in-place
    only when keys are absent (operator-set flags always win).
    """
    from pathlib import Path as _Path
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    project_dir = _Path(getattr(candidate, "project_dir", "."))
    workspace_dir = _Path(
        getattr(candidate, "workspace_dir", project_dir / "workspace")
    )
    primary = str(rubric.get("framer_primary_feature_key", "x"))

    visible = _r14_load_visible_pairs(project_dir)
    if not visible:
        return {
            "engaged": True,
            "stage": "preflight",
            "skipped": True,
            "reason": "no visible data loadable from features.py",
        }

    profile = classify_noise_profile(visible, primary_feature_key=primary)
    updates = auto_route_solver(profile, rubric)
    # Apply auto-routing back to the rubric reference shared with the
    # caller. The caller passes the live rubric_data dict via candidate so
    # operator-set flags are preserved.
    live_rubric = getattr(candidate, "live_rubric_data", None)
    applied: list = []
    if isinstance(live_rubric, dict):
        for k, v in updates.items():
            if k not in live_rubric:
                live_rubric[k] = v
                if not k.endswith("_reason"):
                    applied.append(k)

    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": profile.summary(),
            "n_rows_tested": profile.n_rows_tested,
            "baseline_form": profile.baseline_form,
            "needs_weighted": profile.needs_weighted,
            "needs_robust": profile.needs_robust,
            "needs_correlated": profile.needs_correlated,
            "needs_odr": profile.needs_odr,
            "evidence": profile.evidence,
            "warnings": profile.warnings,
            "auto_route_updates_applied": applied,
            "stage": "pre_flight",
        }
        import json as _json
        (workspace_dir / "noise_profile.json").write_text(
            _json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
    except Exception:
        pass

    return {
        "engaged": True,
        "stage": "preflight",
        "summary": profile.summary(),
        "auto_route_applied": applied,
    }


def r14_run_post_fit(substrate: "Any", candidate: "Any") -> dict:  # type: ignore  # noqa: F821
    """POST_FIT adapter: classify the fitted model's residuals and append
    the verdict to the per-iter section of workspace/noise_profile.json.
    """
    from pathlib import Path as _Path
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    project_dir = _Path(getattr(candidate, "project_dir", "."))
    workspace_dir = _Path(
        getattr(candidate, "workspace_dir", project_dir / "workspace")
    )
    iter_index = int(getattr(candidate, "iter_index", 0) or 0)
    primary = str(rubric.get("framer_primary_feature_key", "x"))
    visible = getattr(candidate, "visible_pairs", None)
    fitted_params = getattr(candidate, "fitted_params", None)
    form = getattr(candidate, "fitted_form", None)

    if not visible or not form or not fitted_params:
        return {
            "engaged": True,
            "stage": "post_fit",
            "skipped": True,
            "reason": "missing visible_pairs / fitted_form / fitted_params on candidate",
        }

    try:
        from src.ztare.fit.fit_primitive_features import _safe_compile_form
        fn = _safe_compile_form(form)
    except Exception as exc:
        return {
            "engaged": True,
            "stage": "post_fit",
            "skipped": True,
            "reason": f"compile_form failed: {type(exc).__name__}: {exc}",
        }

    residuals: list[float] = []
    xs: list[float] = []
    for feats, y_obs in visible:
        try:
            y_pred = fn(feats, fitted_params)
            if y_pred is None or (
                isinstance(y_pred, float)
                and (math.isnan(y_pred) or math.isinf(y_pred))
            ):
                continue
            residuals.append(float(y_obs) - float(y_pred))
            v = feats.get(primary)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                xs.append(float(v))
            else:
                xs.append(0.0)
        except Exception:
            continue

    if len(residuals) < 20:
        return {
            "engaged": True,
            "stage": "post_fit",
            "skipped": True,
            "reason": f"only {len(residuals)} residual rows; need ≥20",
        }

    profile = classify_residuals(
        residuals, xs, label=f"post_fit_iter_{iter_index}"
    )
    # Append to noise_profile.json under per_iter (cap last 10)
    try:
        import json as _json
        existing: dict = {}
        np_path = workspace_dir / "noise_profile.json"
        if np_path.exists():
            try:
                existing = _json.loads(np_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        per_iter = existing.get("per_iter", []) or []
        per_iter.append({
            "iter_index": iter_index,
            "summary": profile.summary(),
            "needs_weighted": profile.needs_weighted,
            "needs_robust": profile.needs_robust,
            "needs_correlated": profile.needs_correlated,
            "evidence": profile.evidence,
        })
        existing["per_iter"] = per_iter[-10:]
        existing["latest_post_fit"] = per_iter[-1]
        # Distinct per-iter artifact for completeness (briefing providers
        # can also read the latest_post_fit pointer in the rolled-up file).
        np_path.write_text(_json.dumps(existing, indent=2, default=str), encoding="utf-8")
        per_iter_path = (
            workspace_dir / f"noise_profile_post_fit_iter_{iter_index:03d}.json"
        )
        per_iter_path.write_text(
            _json.dumps(per_iter[-1], indent=2, default=str), encoding="utf-8"
        )
    except Exception:
        pass

    return {
        "engaged": True,
        "stage": "post_fit",
        "summary": profile.summary(),
    }


def register_r14_gate(cage: "Any") -> None:  # type: ignore  # noqa: F821
    """Register the R14 noise_profile gate(s) with a Cage instance.

    R14 is dual-phase: PRE_FIT preflight + POST_FIT residual classifier.
    Each phase is its own Gate; they share can_handle.
    """
    try:
        from src.ztare.gates.cage import Gate
    except ImportError:
        return
    pre_gate = Gate(
        name="R14_noise_profile_preflight",
        phase="PRE_FIT",
        can_handle=r14_can_handle,
        run=r14_run_preflight,
        dependencies=[],
    )
    post_gate = Gate(
        name="R14_noise_profile_post_fit",
        phase="POST_FIT",
        can_handle=r14_can_handle,
        run=r14_run_post_fit,
        dependencies=[],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[pre_gate.name] = pre_gate
        cage.gates[post_gate.name] = post_gate
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None


# ── Self-test (run with `python -m src.ztare.diagnostics.noise_profile`) ─


if __name__ == "__main__":
    import random
    rng = random.Random(0)
    print("=" * 60)
    print("GP-166 noise_profile self-test")
    print("=" * 60)

    # Test A: clean Gaussian-i.i.d. data — all flags should stay False
    a_data = [
        ({"x": 0.1 * i}, 2 * 0.1 * i + 3 + rng.gauss(0, 0.05))
        for i in range(80)
    ]
    p_a = classify_noise_profile(a_data)
    print(f"\nA) clean Gaussian linear: {p_a.summary()}")
    print(f"   weighted={p_a.needs_weighted}, robust={p_a.needs_robust}, "
          f"correlated={p_a.needs_correlated}, odr={p_a.needs_odr}")

    # Test B: heteroscedastic — needs_weighted should fire
    b_data = []
    for i in range(80):
        x = 0.1 * i + 0.1
        sigma = x * 0.3  # variance grows with x
        y = 2 * x + 3 + rng.gauss(0, sigma)
        b_data.append(({"x": x}, y))
    p_b = classify_noise_profile(b_data)
    print(f"\nB) heteroscedastic σ∝x: {p_b.summary()}")

    # Test C: heavy-tail (Cauchy-ish residuals)
    c_data = []
    for i in range(80):
        x = 0.1 * i + 0.1
        # 95% Gaussian + 5% massive spikes
        if rng.random() < 0.05:
            noise = rng.gauss(0, 0.05) * 50
        else:
            noise = rng.gauss(0, 0.05)
        c_data.append(({"x": x}, 2 * x + 3 + noise))
    p_c = classify_noise_profile(c_data)
    print(f"\nC) heavy-tail spikes: {p_c.summary()}")

    # Test D: explicit sigma_x declared
    d_data = [
        ({"x": 0.1 * i, "sigma_x": 0.01}, 2 * 0.1 * i + 3 + rng.gauss(0, 0.05))
        for i in range(80)
    ]
    p_d = classify_noise_profile(d_data)
    print(f"\nD) explicit sigma_x: {p_d.summary()}")

    # Test E: auto-routing
    print(f"\nB rubric updates: {auto_route_solver(p_b, {})}")
