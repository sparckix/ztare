# GP-152 — Framer Architecture Spec v2.0

**Status:** spec / READY-FOR-IMPLEMENTATION
**Date:** 2026-04-24
**Supersedes:** `GP-152_framer_architecture_spec_v1_2.md` (v1.2)
**Backtest:** `scripts/public/backtest_framer_mdl_v2_vs_v1.py` — frame-invariance drift 0.000 bits/point.

The Jacobian patch cycle (v1.0 → v1.1 → v1.2 → v1.3) only existed because we kept computing NLL in **framed** coordinates and trying to convert back. v2.0 sidesteps the entire cycle by computing MDL directly in **raw** coordinates throughout. Frame-invariance becomes a property of construction, not a property requiring derived correction.

---

## 1. The v2.0 insight in one sentence

**Fit the law in framed coords; evaluate the residual in raw coords.** No Jacobian needed.

The framing helps the solver find a parsimonious law. The MDL evaluation lives in the data's native units, where it is automatically commensurable across all candidate `(h_in, h_out)` pairs.

---

## 2. The MDL formula

```
σ̂²_raw   :=  (1/N) · Σ_i ( y_i − h_out⁻¹( f̂( h_in(x_i) ) ) )²
K_total  :=  K_law + K_h_in + K_h_out

MDL_v2 = N · log( σ̂²_raw ) + K_total · log(N)
```

**Components:**
- `f̂` = MLE-fit law in framed coords. The solver runs as before; only the loss evaluation changes.
- `h_out⁻¹` = inverse of the output transform. Trivial for monotone primitives in `Σ = {identity, shift, scale, power_k, log, exp, reciprocal}`. The Framer rejects non-monotone or non-invertible candidates upstream.
- `K_law` = parameter count of the fitted law (e.g., 2 for `a·exp(z) + b`).
- `K_h_in`, `K_h_out` = parameter count of the transformations themselves (each primitive contributes 1; `identity = 0`, `log = 0`, `exp = 0`, `scale_by_c = 1`, `shift_by_a = 1`, `power_k = 1`, `reciprocal = 0`).

**No σ_noise floor needed** in v2.0. Floors were a v1.x patch to prevent `σ̂² → 0` collapse during framed-coord NLL evaluation. In raw coords, `σ̂²_raw` cannot collapse below the actual measurement noise of the data.

**No Jacobian, no log-J clip, no ε-perturbation rank-stability check** needed. Frame-invariance is constructive (see §3); the patches v1.x added are obsolete.

---

## 3. Frame-invariance proof

**Claim:** under `h_out → c·h_out` for any positive constant c, MDL_v2 is invariant.

**Proof:**

The framed law fit absorbs the c-scaling: if `f̂(z)` minimizes `Σ(c·y − f̂(z))²`, then `f̂_c(z) = c·f̂_original(z)` minimizes the same objective scaled by c². The MLE coefficients re-scale; the minimum-residual structure is preserved.

For the prediction in raw coords:
```
ŷ_raw  =  h_out⁻¹ ( f̂(h_in(x)) )
ŷ_raw_c = (c·h_out)⁻¹ ( f̂_c(h_in(x)) )
        = h_out⁻¹ ( f̂_c(h_in(x)) / c )
        = h_out⁻¹ ( f̂_original(h_in(x)) )
        = ŷ_raw
```

The raw-coords prediction is identical. Therefore `σ̂²_raw` is unchanged. Therefore MDL is unchanged. ∎

**Backtest confirmation** (run 2026-04-24, `scripts/public/backtest_framer_mdl_v2_vs_v1.py`):
- v1.0 drift under c ∈ {0.1, ..., 10}: ±1993 bits (catastrophic)
- v1.2 drift: ±664 bits (still broken)
- v1.3 drift: 0.000 bits (BIC −2 coefficient also works)
- **v2.0 drift: 0.000 bits ✓**

v1.3 and v2.0 are both math-correct. v2.0 is simpler (no Jacobian computation) and has fewer implementation surfaces to introduce bugs.

---

## 4. Architecture

**Module path:** `src/ztare/framer/active_framer.py`

**Hand-off contract** (unchanged from v1.x):
```python
def frame(
    data: NDArray[(N, 2), float],
    meta: Dict[str, Any],
    rubric_data: Dict[str, Any],
) -> Tuple[NDArray[(N, 2), float], Dict[str, Any]]:
    """
    Returns:
        transformed_data : (h_in(x), h_out(y))
        framing_report   : {
            "h_in":          SymbolicExpr,
            "h_out":         SymbolicExpr,
            "h_out_inv":     SymbolicExpr,        # NEW in v2.0 — needed for raw-coord eval
            "MDL_v2":        float,
            "MDL_v2_baseline": float,             # MDL for identity-identity
            "MDL_gain_bits": float,
            "scores":        List[Tuple[Expr, Expr, float]],
            "gates":         Dict[str, Any],
            "canary":        Dict[str, Any],
            "framer_engaged": bool,
            "disabled_reason": str | None,
        }
    """
```

**Components** (carried over from v1.2 — the architecture is unchanged; only the MDL function changes):

| # | Module | Path | Status vs v1.2 |
|---|---|---|---|
| A | SymmetryScanner | `src/ztare/framer/symmetry.py` | unchanged |
| B | DimensionalFilter | `src/ztare/framer/units.py` | unchanged |
| C | TransformationEnumerator | `src/ztare/framer/enumerate.py` | **adds h_out_inv field** to each candidate |
| D | BranchAndBoundMDLSearch | `src/ztare/framer/search.py` | **MDL function replaced; ε-perturbation check removed** (no longer needed) |
| E | UniversalityAligner | `src/ztare/framer/collapse.py` | unchanged |
| F | ReportWriter | `src/ztare/framer/report.py` | adds `h_out_inv` to report |

**Solver wrapper** at `src/ztare/framer/solver_wrapper.py` — `fit_with_framer()` signature unchanged.

---

## 5. Scope (revised)

### 5.1 In scope

- **Numerical-fit substrates** with `fit_score_mode in {"continuous_l2", "continuous_rmse"}`.
- **Axis-separable monotone-invertible transforms**: `(h_in, h_out)` from `Σ = {identity, shift, scale, power_k, log, exp, reciprocal}` at composition depth ≤ 2. **Each primitive must have an explicit closed-form inverse** (all primitives in Σ do; non-monotone compositions are rejected by TransformationEnumerator).
- `N ≥ 80` (Heisenberg noise-floor minimum).
- `meta["units"]` does not require bivariate / mixing transformation.

### 5.2 Out of scope (with auto-disable)

- **Heteroscedastic noise IN THE CHOSEN FRAME** — bin-std-ratio > 5× on residuals computed in the FRAMED coords (i.e., after the Framer picks `(h_in, h_out)`) → auto-disable with `disabled_reason = "heteroscedastic_in_chosen_frame"`. **v2.0.1 fix (Gemini-Pro 2026-04-24):** the check is POST-framing, not pre-framing. Pre-framing in raw coords misfired on wide-dynamic-range substrates (e.g., `y = 1/x`) because `Δy ≈ f'(x)·Δx` fans residuals out near singularities of `f'`. The fan-out is a coordinate-frame illusion that disappears in the correct frame (e.g., `h_out = reciprocal` flattens 1/x → identity). The post-framing test only fires when the chosen frame STILL has residual fan-out — the only case where v2.0's BIC-Gaussian-homoscedastic assumption genuinely breaks. Implementation: `src/ztare/framer/active_framer.py:_check_post_frame_heteroscedasticity`. Per-region variance estimation for fully-heteroscedastic noise is v3.0 territory.
- **Effective precision < 8 bits** — auto-disable.
- **Non-invertible composite transforms** — TransformationEnumerator rejects upstream.
- **Discrete/qualitative/dynamical/FOM substrates** (gp077/gp150/gp140/FOM-class) — fit_score_mode-gated.
- **Bivariate/mixing transforms** (Lorentz-class) — meta["units"]-gated.

### 5.3 Removed from v1.2 (no longer needed)

- σ_noise floor scaling.
- Jacobian computation.
- log-Jacobian clip.
- ε-perturbation rank-stability check.

These were patches for a problem v2.0 doesn't have.

---

## 6. Numerical predictions (re-validated under v2.0)

**Test case A**: `y = exp(x²) / (1 + log x)`, `N=200`, `σ=0.01`, `x ∈ [1, 10]`.

Under v2.0:
- Native (identity-identity): `σ̂²_raw` ≈ data's residual under polynomial fit.
- Framed (h_in=x², h_out=identity): `σ̂²_raw` slightly lower because the polynomial in `z = x²` better captures `exp(z)`.
- **Predicted MDL gain: 20-60 bits** (less than v1.x's claimed 50-80 bits — v2.0 is more honest about parsimony).

The exact numerical prediction depends on the solver's polynomial degree and the law's compressibility. Test case A is qualitatively easier than B because the structural transformation `h_in=x²` has a known win.

**Test case B** (universality, two datasets): `y_i = A_i · x^α + B_i` with shared α.

UniversalityAligner runs in framed coords with the v2.0 MDL evaluating residuals in raw coords for each dataset independently, then summing. Predicted post-collapse residual dispersion ≤ 1.25·σ_noise (unchanged from v1.x — collapse phase doesn't depend on MDL formula bug).

**Iteration savings:** 28 → 9 (±2). Same prediction as v1.x; this depends on the ordinal MDL ranking, which is correct under any frame-invariant formula.

---

## 7. Validation protocol

Before `enable_framer=True` is promoted to default-on:

1. **Frame-invariance backtest passes** (already verified by `scripts/public/backtest_framer_mdl_v2_vs_v1.py`): drift < 0.5 bit per data point across c ∈ {0.1, 10}.
2. **Test case A passes**: framed solution found within ≤ 9 (±2) iters; MDL gain ≥ 20 bits.
3. **Test case B passes**: universality collapse residual ≤ 1.25·σ_noise on master curve.
4. **Three runtime gates self-test** (G-LIB-COVER, G-FILTER-INDEP, G-SYM-FN) on canary substrates.
5. **`framer_helped_canary` self-test** — Framer auto-disables on a pathological transform.
6. **A/B benchmark on GP-148 archive**: framed median iters ≤ 15 (vs 28 baseline). Out-of-scope substrates auto-skipped.
7. **GP-146-style Arnold-Cat-Map cross-validation** with synthetic coordinate-transformed evidence: feed `y = log(λ_1 · x)` instead of `λ_1`; Framer must recover `h_out = exp` and Phase 2 must then recover `λ_1`.
8. **Lorentz negative-control**: Framer auto-disables on `s² = c²t² - x²` data.
9. **Heteroscedasticity guard test**: `σ(y) = 0.01 + 0.1·|y|` triggers auto-disable.
10. **Low-precision guard test**: 4-bit-quantized data triggers auto-disable.

Steps 1 and 2 can be done immediately on the spec-validation level; steps 3-10 require implementation.

---

## 8. Runtime gate stack (revised)

THREE GATES + ONE CANARY. Same as v1.2. The recursive-audit findings during v1.x cycle were MDL-formula bugs, not new failure-mode candidates.

### 8.1 G-LIB-COVER — Library Coverage Gate

Threshold: MDL gain ≥ 100 bits (same as v1.2). Detects when no in-library transform produces a real improvement.

### 8.2 G-FILTER-INDEP — Filter Independence Gate

Bootstrap-correlation of SymmetryScanner + DimensionalFilter pruning decisions. |corr| < 0.3 at bootstrap_n=300 (same as v1.2).

### 8.3 G-SYM-FN — SymmetryScanner False-Negative Gate

Detection rate ≥ 0.95 across 60 canary substrates (same as v1.2).

### 8.4 framer_helped_canary

Compare framed-solver iters + residual to raw-solver iters + residual (run on first iter, cache decision). Same as v1.2.

---

## 9. Wiring into autoresearch_loop.py

Same as v1.x §5: `fit_with_framer` wraps `fit_primitive.fit_parameters` and `compress_champion.run_compress` call sites. Rubric flag `enable_framer: bool` (default false).

---

## 10. Implementation TODOs (paper-level rigor)

Carried over from v1.x:
1. Per-grammar inversion proof.
2. Depth-2 sufficiency justification.
3. Generative yield class statement.
4. Frame-invariance proof — **DONE in §3**; backtest at `scripts/public/backtest_framer_mdl_v2_vs_v1.py`.
5. Noise-floor characterization — moot for v2.0 (no σ_noise floor).
6. First-principles MDL derivation — **DONE in §1-2**; raw-coord BIC IS the first-principles answer for Gaussian-homoscedastic.

**v2.0 NEW paper TODOs:**
7. **v3.0 heteroscedasticity extension**: per-region σ̂²_raw, or weighted residuals, or NML for the heteroscedastic case. Current v2.0 auto-disables; v3.0 should engage.
8. **v3.0 finite-precision extension**: pre-quantized coding. Current v2.0 auto-disables at <8 bits; v3.0 should engage.

---

## 11. Provenance & changelog

- v1.0 (superseded): iter-1 blueprint; 5 panel-detected flaws.
- v1.1 (superseded): panel-revised; 3 cross-validated flaws.
- v1.2 (superseded): patches; backtest showed 664-bit residual drift.
- v1.3 (subsumed by v2.0): first-principles BIC with −2 coefficient; passes frame-invariance but more complex than v2.0.
- **v2.0 (this document): raw-coord MDL; frame-invariance by construction; SIMPLEST FORMULATION.**
- v3.0 (planned, research): heteroscedasticity-native + pre-quantized coding (NML / stochastic complexity).

**Backtest provenance:** `scripts/public/backtest_framer_mdl_v2_vs_v1.py` (2026-04-24) — v1.0 1993 bits, v1.2 664 bits, v1.3 0.000 bits, v2.0 0.000 bits. v2.0 also correctly prefers `h_in=x²` over identity by 26.24 bits on test case A.

**Audit provenance:**
- `projects/gp152_framer_architecture_audit/` — original audit (iter 1 score 91; iters 2-3 surfaced MDL formula bugs).
- `projects/gp153_framer_spec_critique/` — recursive critique (iter 0 score 88: three v1.1 errors; iter 1 score 62: v1.2 patch insufficient).
- 4-panel review (Newton, Einstein, Heisenberg, Munger) — informed v1.1 → v1.2 revisions.

**F-rows:**
- F-GP152-FRAMER-BLUEPRINT-01 (architecture concept)
- F-GP153-MDL-FORMULA-FIX-01 (MDL formula correction; references v2.0)

---

## 12. The one-page summary

| | v1.x (framed-coord NLL with Jacobian patches) | **v2.0 (raw-coord BIC)** |
|---|---|---|
| MDL formula | `N·log σ̂²_y' + (Jacobian patch) + K·log N` | `N·log σ̂²_raw + K·log N` |
| Jacobian needed? | Yes (with three sequential patch attempts) | **No** |
| σ_noise floor needed? | Yes (with unit-mismatch bug in v1.0/v1.1) | **No** |
| Frame-invariance | Patched to first order (v1.3 OK) | **Constructive** |
| ε-perturbation rank check | Yes (v1.2 added) | **No** (not needed) |
| Implementation surfaces for bugs | ~3 (Jacobian, floor, clip) | **~1 (h_out_inv)** |
| Lines of code change vs v1.1 | ~70 | **~30** |
| Patch-cycle history | v1.0 → v1.1 → v1.2 → v1.3 (each had a math error) | **Stable from first principles** |

Ship v2.0.
