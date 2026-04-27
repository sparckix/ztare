#!/usr/bin/env python3
"""GP-154 OFFLINE VERIFICATION — does a K≤10 unified law exist?

Per Gemini Pro / agent epistemic-airgap protocol (2026-04-25 night):
this script tests, OFFLINE and never visible to the autonomous loop,
whether a hand-coded candidate convention-bridging law passes the
0.25 HOLDOUT MRE gate. The result tells us whether to invest more
compute in gp154 (Step 2-4 of the breakthrough plan) or pivot to
the bounded-null Nature MI submission.

USAGE:
    python scripts/gp154_offline_verify.py

EPISTEMIC AIRGAP PROTOCOL:
    1. The script prints ONLY the final HOLDOUT MRE per candidate
       and a binary verdict (PASS / FAIL of the 0.25 threshold).
    2. It does NOT print fitted parameters, per-row residuals, or
       any holdout truth values.
    3. The operator should NOT paste this script's output into any
       chat with an AI. Tell the agent ONLY:
         "MRE < 0.25" (proceed to Step 2)
       or "MRE > 0.25" (bounded null, pivot to Nature MI write-up)

WHAT IS BEING TESTED:
    Three candidate forms with K=4-7 parameters, all hypothesizing
    that the load-bearing axis is `fit_convention` (the gp158-audit
    hypothesis). The forms are MULTIPLICATIVE (not the additive-
    categorical family that has failed all autonomous iters), and
    they treat the convention as a 2-3-level discriminator on the
    overall slope. If ANY of these passes HOLDOUT MRE < 0.25, a
    K≤7 unified law exists in the data and the autonomous loop's
    failure is a search-pathology problem, not an existence problem.

    The forms are intentionally chosen as STRUCTURAL HYPOTHESES, not
    perfect physics. If one passes, the autonomous mutator (with the
    cleaned apparatus + claude-opus or o1) has a reachable target.
    If NONE passes, the bounded-null result is empirically supported.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure src.ztare imports resolve
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

PROJECT_DIR = _REPO / "projects" / "gp154_scaling_law_exponents"
EVIDENCE_HOLDOUT = PROJECT_DIR / "evidence_holdout.txt"
HOLDOUT_THRESHOLD = 0.25  # gp154 rubric: HOLDOUT_SET MRE < 0.25 to pass


# ── Candidate forms (hand-authored hypotheses; NOT injected into the loop) ──
#
# Strategy: bridge fit_convention as a multiplicative factor on the slope of
# a simple base law. If gp158's audit is right (Class K, no unified law),
# none of these will pass. If it's wrong, at least one should.
#
# All forms use d_eff = intrinsic_dim_d if not None else intrinsic_dim_estimate
# else a default — consolidating Sharma's d-anchor with Bahri's d-estimate
# into a single continuous variable.
#
# Convention buckets (3-level discriminator):
#   "kaplan_separable", "loss_curve_power", "loss_curve_power_const"  → Kaplan-family
#   "chinchilla_joint", "chinchilla_isoflop", "chinchilla_parametric",
#     "compute_optimal", "joint_bivariate"                            → Chinchilla-family
#   default                                                            → other

CANDIDATES: list[tuple[str, str, list[str]]] = [
    # (name, PARAMETRIC_FORM, parameter_names)
    # ── ROUND 2 (post-feature-inventory): log10_N_params is on 110/110
    # rows; intrinsic_dim_d is only 14/110. Round-1 forms used d-fallbacks
    # for ~80% of rows. These new candidates put log10_N_params as primary.
    # ─────────────────────────────────────────────────────────────────────
    (
        "R2_power_law_in_N_alone_K=3",
        # α = a + b × log10_N_params^c   (pure scaling-law in model size)
        "params['a'] + params['b'] * (features['log10_N_params'] ** params['c'])",
        ["a", "b", "c"],
    ),
    (
        "R2_N_with_convention_multiplicative_K=5",
        # α = (a + b × log10_N_params) × convention_factor
        "(params['a'] + params['b'] * features['log10_N_params']) "
        "* (1.0 + params['c_chin'] * "
        "    (1.0 if features['fit_convention'] in "
        "      ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "       'compute_optimal','joint_bivariate') else 0.0) "
        "  + params['c_kap'] * "
        "    (1.0 if features['fit_convention'] in "
        "      ('kaplan_separable','loss_curve_power','loss_curve_power_const') else 0.0))",
        ["a", "b", "c_chin", "c_kap"],
    ),
    (
        "R2_sigmoid_crossover_in_N_K=4",
        # α = a + b × sigmoid(log10_N_params, c, w)   (smooth regime in N)
        "params['a'] + params['b'] * sigmoid("
        "  features['log10_N_params'], params['c'], params['w'])",
        ["a", "b", "c", "w"],
    ),
    (
        "R2_per_convention_slope_K=6",
        # α = (a + b × log10_N_params) where (a, b) depend on convention
        # — true per-convention scaling (not just additive offset)
        "(params['a_chin'] + params['b_chin'] * features['log10_N_params']) "
        "  if features['fit_convention'] in "
        "    ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "     'compute_optimal','joint_bivariate') "
        "  else "
        "((params['a_kap'] + params['b_kap'] * features['log10_N_params']) "
        "  if features['fit_convention'] in "
        "    ('kaplan_separable','loss_curve_power','loss_curve_power_const') "
        "  else (params['a_other'] + params['b_other'] * features['log10_N_params']))",
        ["a_chin", "b_chin", "a_kap", "b_kap", "a_other", "b_other"],
    ),
    (
        "R2_N_plus_d_continuous_K=5",
        # α = a + b × log10_N + c × log10(d_eff)
        # uses BOTH continuous variables when d is available
        "params['a'] + params['b'] * features['log10_N_params'] "
        "+ params['c'] * "
        "  (math.log10(features['intrinsic_dim_d']) "
        "    if features['intrinsic_dim_d'] is not None and features['intrinsic_dim_d'] > 0 "
        "    else (math.log10(features['intrinsic_dim_estimate']) "
        "          if features['intrinsic_dim_estimate'] is not None and features['intrinsic_dim_estimate'] > 0 "
        "          else params['d_default']))",
        ["a", "b", "c", "d_default"],
    ),
    (
        "R2_regime_anchored_with_N_K=5",
        # variance_limited → 1.0; resolution_limited → 2/d (Sharma)
        # else → continuous in log10_N_params with convention multiplier
        "(1.0 if features['regime_hint'] == 'variance_limited' else "
        "  ((2.0 / features['intrinsic_dim_d']) "
        "    if (features['regime_hint'] == 'resolution_limited' "
        "        and features['intrinsic_dim_d'] is not None) "
        "    else "
        "    ((params['a'] + params['b'] * features['log10_N_params']) "
        "     * (1.0 + params['c'] * "
        "        (1.0 if features['fit_convention'] in "
        "          ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "           'compute_optimal','joint_bivariate') else 0.0)))))",
        ["a", "b", "c"],
    ),
    (
        "R2_chinchilla_style_inverse_K=5",
        # α = a + b / N^p   (the published Chinchilla form, sans D-term)
        # log10_N → 10^log10_N for the actual N scale
        "params['a'] + params['b'] / "
        "  ((10.0 ** features['log10_N_params']) ** params['p'])",
        ["a", "b", "p"],
    ),
    # ── ROUND 4 — scaling_var as PRIMARY axis (PDF "Empirical Exponents in
    # Neural Scaling Laws" insight: α distributions differ 5-40× between
    # scaling_var values N/D/C/C_OPT). Earlier rounds used scaling_var as
    # additive offset; here it's the primary partition.
    # ─────────────────────────────────────────────────────────────────────
    (
        "R4_per_scaling_var_constants_K=4",
        # α = c_N if scaling_var=='N' else c_D if =='D' else c_C if =='C' else c_other
        # — pure 4-bucket lookup based on scaling_var. If THIS works,
        # convention bridging was never the issue.
        "params['c_N'] if features['scaling_var']=='N' else "
        "(params['c_D'] if features['scaling_var']=='D' else "
        "(params['c_C'] if features['scaling_var']=='C' else params['c_other']))",
        ["c_N", "c_D", "c_C", "c_other"],
    ),
    (
        "R4_scaling_var_x_convention_K=6",
        # Per-scaling-var × per-convention-family lookup
        # 4 buckets × {Kaplan, Chinchilla} → 6 params (collapse where one is degenerate)
        "(params['n_kap'] if (features['scaling_var']=='N' and features['fit_convention'] in "
        "  ('kaplan_separable','loss_curve_power','loss_curve_power_const')) else "
        "(params['n_chin'] if (features['scaling_var']=='N' and features['fit_convention'] in "
        "  ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "   'compute_optimal','joint_bivariate')) else "
        "(params['d_any'] if features['scaling_var']=='D' else "
        "(params['c_any'] if features['scaling_var']=='C' else "
        "(params['copt'] if features['scaling_var']=='C_OPT' else params['other'])))))",
        ["n_kap", "n_chin", "d_any", "c_any", "copt", "other"],
    ),
    (
        "R4_scaling_var_x_log_N_K=7",
        # Per-scaling-var (intercept + slope on log10_N) — 4 buckets × 2 = 7
        "(params['a_N'] + params['b_N'] * features['log10_N_params']) "
        "  if features['scaling_var']=='N' else "
        "((params['a_D'] + params['b_D'] * features['log10_N_params']) "
        "   if features['scaling_var']=='D' else "
        "((params['a_C'] + params['b_C'] * features['log10_N_params']) "
        "    if features['scaling_var']=='C' else params['a_other']))",
        ["a_N", "b_N", "a_D", "b_D", "a_C", "b_C", "a_other"],
    ),

    # ── ROUND 3 — non-linear scale × convention coupling (per Gemini Pro) ─
    # Hypothesis: Kaplan and Chinchilla aren't separated by a constant
    # multiplicative bump; they have STRUCTURALLY DIFFERENT EXPONENTS that
    # interact non-linearly with model size. Forms below test that.
    (
        "R3_convention_modulated_exponent_K=4",
        # α = a × N^(b + c × is_chinchilla)
        # → Kaplan and Chinchilla have different exponents, not different slopes
        "params['a'] * "
        "  ((10.0 ** features['log10_N_params']) ** "
        "    (params['b'] + params['c'] * "
        "      (1.0 if features['fit_convention'] in "
        "        ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "         'compute_optimal','joint_bivariate') else 0.0)))",
        ["a", "b", "c"],
    ),
    (
        "R3_bilinear_log_N_x_convention_K=5",
        # log(α) = a + b × log_N + c × is_chinchilla × log_N + d × is_chinchilla
        # → multiplicative interaction between scale and convention
        "exp(params['a'] + params['b'] * features['log10_N_params'] "
        "    + params['c'] * features['log10_N_params'] * "
        "      (1.0 if features['fit_convention'] in "
        "        ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "         'compute_optimal','joint_bivariate') else 0.0) "
        "    + params['d'] * "
        "      (1.0 if features['fit_convention'] in "
        "        ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "         'compute_optimal','joint_bivariate') else 0.0))",
        ["a", "b", "c", "d"],
    ),
    (
        "R3_compute_optimal_anchored_K=5",
        # Chinchilla isoFLOP: α=0.5 in compute-optimal regime by theorem
        # else: standard scaling
        "(0.5 if features['fit_convention'] in ('compute_optimal','joint_bivariate') "
        " else (1.0 if features['regime_hint']=='variance_limited' "
        "       else (params['a'] + params['b'] * features['log10_N_params'] "
        "             + params['c'] * "
        "               (1.0 if features['fit_convention'] in "
        "                 ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric') else 0.0))))",
        ["a", "b", "c"],
    ),
    (
        "R3_per_convention_full_K=7",
        # Full per-convention (a, b, c) tuple — most flexible at K=7
        # α = (a + b × log_N) for the matching convention
        "(params['a_chin'] + params['b_chin'] * features['log10_N_params']) "
        "  if features['fit_convention'] in "
        "    ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "     'compute_optimal','joint_bivariate') "
        "  else "
        "((params['a_kap'] + params['b_kap'] * features['log10_N_params']) "
        "  if features['fit_convention'] in "
        "    ('kaplan_separable','loss_curve_power','loss_curve_power_const') "
        "  else "
        "(params['a_oth'] + params['b_oth'] * features['log10_N_params'] "
        " + params['off_oth']))",
        ["a_chin", "b_chin", "a_kap", "b_kap", "a_oth", "b_oth", "off_oth"],
    ),

    # ── SANITY BASELINES — locks the diagnosis ────────────────────────────
    (
        "S1_constant_predictor_K=1",
        # α = c   (just predict the same number for every row — what's the
        # noise floor? If this gets ~0.30 visible / ~3.5 holdout, our K≤7
        # forms aren't fitting anything; they're collapsing to constants.)
        "params['c']",
        ["c"],
    ),
    (
        "S2_log_link_K=4",
        # log(α) = a + b × log10_N + c × is_chinchilla
        # → α = exp(a + b*log_N + c*is_chinchilla)
        # multiplicative log-link is the standard scaling-law parameterization
        # — this is what Kaplan/Chinchilla papers actually publish
        "exp(params['a'] + params['b'] * features['log10_N_params'] "
        "    + params['c'] * "
        "      (1.0 if features['fit_convention'] in "
        "        ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "         'compute_optimal','joint_bivariate') else 0.0))",
        ["a", "b", "c"],
    ),
    # ── ROUND 1 candidates kept for comparison ────────────────────────────
    (
        "C1_multiplicative_convention_bridge_K=4",
        # α = (k1/d_eff) × (1 + c_chin × is_chinchilla_family)
        "(params['k1'] / "
        "  ( features['intrinsic_dim_d'] if features['intrinsic_dim_d'] is not None "
        "    else (features['intrinsic_dim_estimate'] if features['intrinsic_dim_estimate'] is not None "
        "          else params['d_default']) )) "
        "* (1.0 + params['c_chin'] * "
        "    (1.0 if features['fit_convention'] in "
        "      ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "       'compute_optimal','joint_bivariate') else 0.0))",
        ["k1", "c_chin", "d_default"],  # K=3 free + constant 1.0
    ),
    (
        "C2_regime_anchored_with_convention_K=6",
        # variance_limited → 1.0 (Bahri anchor)
        # else → (k1/d_eff) × (1 + c_chin × is_chinchilla + c_kaplan × is_kaplan)
        "(1.0 if features['regime_hint'] == 'variance_limited' else "
        "  ((params['k1'] / "
        "    ( features['intrinsic_dim_d'] if features['intrinsic_dim_d'] is not None "
        "      else (features['intrinsic_dim_estimate'] if features['intrinsic_dim_estimate'] is not None "
        "            else params['d_default']) )) "
        "  * (1.0 + params['c_chin'] * "
        "      (1.0 if features['fit_convention'] in "
        "        ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "         'compute_optimal','joint_bivariate') else 0.0) "
        "    + params['c_kap'] * "
        "      (1.0 if features['fit_convention'] in "
        "        ('kaplan_separable','loss_curve_power','loss_curve_power_const') else 0.0)) "
        "  + params['offset']))",
        ["k1", "c_chin", "c_kap", "d_default", "offset"],
    ),
    (
        "C3_convention_factor_on_exponent_K=5",
        # α = (k1/d_eff) raised to a convention-dependent exponent
        # (the convention modulates the slope's curvature, not just magnitude)
        "params['amp'] * "
        "  ( ( params['k1'] / "
        "      ( features['intrinsic_dim_d'] if features['intrinsic_dim_d'] is not None "
        "        else (features['intrinsic_dim_estimate'] if features['intrinsic_dim_estimate'] is not None "
        "              else params['d_default']) )) "
        "    ** (1.0 + params['e_chin'] * "
        "        (1.0 if features['fit_convention'] in "
        "          ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
        "           'compute_optimal','joint_bivariate') else 0.0)))",
        ["amp", "k1", "e_chin", "d_default"],
    ),
    (
        "C4_anchor_plus_continuous_log_N_K=5",
        # variance_limited → 1.0
        # else: continuous in log10(model size proxy)
        # using only intrinsic_dim_d as a continuous variable (no convention)
        # — sanity baseline: does a non-convention-aware continuous form work?
        "(1.0 if features['regime_hint'] == 'variance_limited' else "
        "  (params['a'] + params['b'] / "
        "    ( features['intrinsic_dim_d'] if features['intrinsic_dim_d'] is not None "
        "      else (features['intrinsic_dim_estimate'] if features['intrinsic_dim_estimate'] is not None "
        "            else params['d_default']) ) "
        "  + params['c'] * "
        "    (math.log10(features['intrinsic_dim_d']) if features['intrinsic_dim_d'] is not None and features['intrinsic_dim_d'] > 0 else 0.0)))",
        ["a", "b", "c", "d_default"],
    ),
]


# ── Holdout truth parser ─────────────────────────────────────────────────


def parse_holdout_truth() -> dict[int, float]:
    """Parse evidence_holdout.txt's HOLDOUT_SET section into {id: y_true}."""
    truth: dict[int, float] = {}
    section = None
    for raw in EVIDENCE_HOLDOUT.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.startswith("# ===") and "===" in line[5:]:
                upper = line.upper()
                if "HOLDOUT_SET" in upper and "FARTHER" not in upper:
                    section = "HOLDOUT"
                else:
                    section = None
            continue
        if section != "HOLDOUT":
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            truth[int(parts[0])] = float(parts[1])
        except ValueError:
            continue
    return truth


# ── MRE computation (matches gate_harness exactly) ───────────────────────


def compute_mre(predictions: dict[int, float], truth: dict[int, float]) -> tuple[float, int, int]:
    """Returns (mre, n_finite, n_total). MRE = mean(|y_pred - y_true|/|y_true|).
    Non-finite predictions count as residual = 1.0 (penalty), matching the
    gate_harness convention."""
    errors = []
    n_finite = 0
    for row_id, y_true in truth.items():
        y_pred = predictions.get(row_id)
        if y_pred is None or not math.isfinite(y_pred):
            errors.append(1.0)
            continue
        n_finite += 1
        denom = abs(y_true) if y_true != 0 else 1e-12
        errors.append(abs(y_pred - y_true) / denom)
    if not errors:
        return float("inf"), 0, 0
    return sum(errors) / len(errors), n_finite, len(errors)


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    print("=" * 64)
    print("GP-154 OFFLINE VERIFICATION — convention-bridging hypothesis test")
    print("=" * 64)
    print()
    print("Per Gemini Pro epistemic-airgap protocol: DO NOT paste this")
    print("output into any AI chat. Report ONLY the binary verdict to the agent.")
    print()

    # Apparatus imports — same scipy logic as the Cage
    from src.ztare.fit.fit_primitive_features import (
        fit_features,
        load_visible_from_substrate,
    )

    # Load visible — same path the apparatus uses
    visible, err = load_visible_from_substrate(PROJECT_DIR)
    if visible is None:
        print(f"ERROR: could not load visible data: {err}")
        return 2
    print(f"Loaded {len(visible)} visible rows.")

    # Load holdout truth + holdout features
    if not EVIDENCE_HOLDOUT.exists():
        print(f"ERROR: missing holdout truth at {EVIDENCE_HOLDOUT}")
        return 2
    truth = parse_holdout_truth()
    print(f"Loaded {len(truth)} holdout truth rows.")

    # Load features.py to get FEATURES dict for holdout row lookup
    sys.path.insert(0, str(PROJECT_DIR))
    import features as _features_mod  # type: ignore[import-not-found]
    FEATURES = _features_mod.FEATURES

    print()
    print(f"Testing {len(CANDIDATES)} hand-authored candidate forms.")
    print(f"Threshold: HOLDOUT MRE < {HOLDOUT_THRESHOLD} to claim a K≤7 law exists.")
    print()

    best_mre = float("inf")
    any_passed = False
    n_candidates_pass = 0

    for name, form, param_names in CANDIDATES:
        print(f"── {name} (K={len(param_names)}) ──")
        result = fit_features(
            form, param_names, visible,
            n_starts=5, seed=2026, k_law_max=15,
            disable_sparse_indicator_reject=True,  # offline test, not the run
        )
        if not result.success:
            # Truncate any error message to avoid leaking visible-fit details.
            err_short = (result.error_message or "fit failed")[:80]
            print(f"  fit failed: {err_short}")
            print()
            continue

        # Build I_model from the fitted form + apply to holdout features
        from src.ztare.fit.fit_primitive_features import _safe_compile_form
        fn = _safe_compile_form(form)
        predictions: dict[int, float] = {}
        for row_id in truth:
            features_dict = FEATURES.get(row_id)
            if features_dict is None:
                continue
            try:
                y_pred = float(fn(features_dict, result.fitted_params))
            except Exception:
                y_pred = float("nan")
            predictions[row_id] = y_pred

        mre, n_finite, n_total = compute_mre(predictions, truth)
        print(f"  visible mean|res|: {result.mean_abs_residual:.4f}")
        print(f"  HOLDOUT MRE: {mre:.4f}  (n_finite={n_finite}/{n_total})")
        print(f"  Verdict: {'PASS' if mre < HOLDOUT_THRESHOLD else 'FAIL'} threshold={HOLDOUT_THRESHOLD}")
        print()

        if mre < best_mre:
            best_mre = mre
        if mre < HOLDOUT_THRESHOLD:
            any_passed = True
            n_candidates_pass += 1

    print("=" * 64)
    print("AGGREGATE VERDICT")
    print("=" * 64)
    print(f"Candidates tested: {len(CANDIDATES)}")
    print(f"Candidates passing HOLDOUT MRE < {HOLDOUT_THRESHOLD}: {n_candidates_pass}")
    print(f"Best HOLDOUT MRE across candidates: {best_mre:.4f}")
    print()
    if any_passed:
        print(">>> RESULT: A K≤7 unified law EXISTS in the data.")
        print("    The autonomous loop's failure is a SEARCH PATHOLOGY, not")
        print("    a structural impossibility. Proceed to Step 2 (rubric")
        print("    cleanup) and Step 3 (claude-opus dispatch).")
        print()
        print("    Tell the agent ONLY: 'MRE < 0.25'")
    else:
        print(">>> RESULT: No tested K≤7 form passes HOLDOUT.")
        print("    The bounded-null result is empirically supported by these")
        print("    hand-authored candidates. (Caveat: 4 candidates is a small")
        print("    sample — a more thorough search may still find a law.)")
        print(f"    Best MRE: {best_mre:.4f} vs threshold {HOLDOUT_THRESHOLD}.")
        print()
        print("    Tell the agent ONLY: 'MRE > 0.25, best = <ratio>'")
        print("    where <ratio> = best/threshold rounded to 1 decimal.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
