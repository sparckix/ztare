# GP-152 — Framer Architecture Spec v1.2 (SUPERSEDED)

**SUPERSEDED 2026-04-24** by `GP-152_framer_architecture_spec_v2.md`. v1.2 retained the framed-coord MDL approach with patches; backtest at `scripts/public/backtest_framer_mdl_v2_vs_v1.py` showed v1.2 still drifts 664 bits under c-scaling. v2.0 evaluates MDL in raw coords (no Jacobian needed); frame-invariant by construction. v1.2 preserved here for diff history.

**Status:** SUPERSEDED — do not implement against this version
**Date:** 2026-04-24
**Supersedes:** `GP-152_framer_architecture_spec_v1_1.md` (v1.1)
**Sources:**
- gp152 iter-1 thesis (score 91, champion) — original architecture
- 4-panel human review (Newton, Einstein, Heisenberg, Munger) — v1.1 revisions
- gp152 run-2 iter 2 (score 50) — MDL ordering inversion finding
- gp152 run-2 iter 3 (score 58) — heteroscedasticity + finite-precision finding
- gp153 iter 0 (score 88, --dynamic=1 cross-LLM committee) — three MDL-formula errors

This spec is the cross-validated, implementation-ready version. v1.1 had three decisive MDL-formula errors and one scope-discipline gap that the recursive audit caught. v1.2 fixes them via depth (corrected formula + tighter scope), NOT width (no new gates).

---

## 1. Purpose & scope (revised)

The Framer is a **pre-solver representation-search phase** that wraps the existing fit-primitives (`fit_primitive.py`, `compress_champion.py`) so the solver receives data in MDL-minimal coordinates without the rest of the pipeline knowing.

### 1.1 In scope

- **Numerical-fit substrates** with single-curve or aligned-multi-dataset structure.
- **Axis-separable coordinate transformations** of the form `(x, y) → (h_in(x), h_out(y))` where `h_in, h_out` come from the primitive library `Σ = {identity, shift, scale, power_k, log, exp, reciprocal}` at composition depth ≤ 2.
- **Sample size N ≥ 80** per dataset (Heisenberg noise-floor minimum; see §3.4).
- **Reported noise scale σ_noise** in the rubric or evidence (Heisenberg bandwidth-derivation requirement; see §3.5).
- **Homoscedastic noise** (added in v1.2 per gp152 iter 3).
- **Effective data precision ≥ 8 bits** (added in v1.2 per gp152 iter 3).

### 1.2 Out of scope (revised, explicit)

These are excluded; if the input doesn't satisfy a precondition, the Framer auto-disables with `disabled_reason` logged.

**v1.0 → v1.1 exclusions (preserved):**
- Bivariate / mixing transformations (Lorentz-class) — `h: ℝ² → ℝ²` non-separable.
- Discrete number-theoretic substrates (gp077-class) — `fit_score_mode == "discrete_exact"`.
- Text-driven / qualitative-thesis substrates (gp150/gp145b-class) — `fit_score_mode == "none"`.
- Continuous chaotic ODE substrates (gp140-class) — `fit_score_mode == "dynamical_lattice"`.
- N < 80.

**v1.2 NEW exclusions (from gp152 iter 3 finding):**
- **Heteroscedastic noise.** σ_noise must be approximately constant across the y' range. Detection: Breusch-Pagan or White's heteroskedasticity test on the residuals from a depth-0 (identity) Framer pass. If rejected at p < 0.01, Framer auto-disables with `disabled_reason = "heteroscedastic_noise"`. The MDL formalism in v1.2 still assumes Gaussian-ish, ~constant-variance residuals; this is a known limitation.
- **Finite-precision regime.** Data effective precision < 8 bits triggers auto-disable. Detection: estimate the smallest non-zero increment in y values; if log₂(range / increment) < 8, Framer auto-disables with `disabled_reason = "low_effective_precision"`. Reason: the Jacobian's first-order cancellation (relied upon for frame-invariance) breaks when finite-precision coding rounds the perturbation away.

### 1.3 Pre-registered discriminator

- **Current observable** (GP-148 mining baseline): D = mean iters to first ≥85 score on benchmark = 28.
- **Forward observable**: D_thesis ≈ 10. Framed median ≤ 15 → thesis passes; ≥ 15 → rival ("reactive only") survives.
- **Falsifier (Munger):** if framed > unframed on the **`framer_helped_canary`** held-out test (§4.4), Framer auto-disables for that run regardless of MDL.

---

## 2. The three v1.2 changes (depth, not width)

### 2.1 MDL formula corrected (gp153 iter 0 finding)

v1.1 formula (THREE compound errors):
```
MDL_v1.1 = N · log(max(σ̂²_y', σ_noise² · 0.25))    # ❌ floor in raw-y units
         + N · ⟨log |∂h_out/∂y|⟩                    # ❌ wrong sign
         + K_fn · log(N)                             # ✓
```

**v1.2 formula (corrected):**
```
J̄  := (1/N) · Σ_i |h_out'(y_i)|²                                   # mean-square Jacobian
log_J  := clip(  (1/N) · Σ_i log |h_out'(y_i)|,  -10,  +10 )         # clipped log-Jacobian

MDL_v1.2 = N · log( max( σ̂²_y',  σ_noise² · J̄ · 0.25 ) )            # σ_noise floor TRANSFORMED by Jacobian
         - N · log_J                                                # SIGN FLIPPED to NLL convention
         + K_fn · log(N)                                            # unchanged
```

**Three fixes annotated:**

1. **σ_noise floor Jacobian-transformed.** The dispersion `σ̂²_y'` is in framed-y² units; under `y' = h_out(y)` the appropriate noise scale is `σ_noise² · |dy'/dy|² ≈ σ_noise² · J̄`. The 0.25 factor is preserved (allows for genuine variance reduction below the raw noise floor when the framing is real signal extraction).

2. **Jacobian sign flipped to NLL convention.** MDL aligns with negative-log-likelihood. For Gaussian residuals in framed coordinates, `-NLL ∝ -log p(data) = +log σ̂² + (constant) - log|J|`. The Jacobian term is therefore SUBTRACTED. v1.1's `+ N · ⟨log J⟩` was reward-direction-flipped: it favored compressing transforms when it should have favored expanding ones (or vice versa, depending on sign conventions). v1.2 uses minus.

3. **Log-Jacobian clipped to [-10, +10].** Prevents saturating transforms (`tanh`, `sigmoid`, etc. — which technically aren't in `Σ` but compositions can approach them) from driving log-Jacobian → -∞ and the MDL → -∞ artificially. The `±10` bound corresponds to ~14 bits per data point of information, which is generous for any real transformation in `Σ`. Concretely: identity has log_J = 0; a `scale_by_c` has log_J = log|c| (typically ±2-3 bits); `log` and `exp` have log_J ≈ -log y or +log y, within ±10 for any y ∈ [10⁻⁴, 10⁴]. Real-world data falls inside the clip; pathological transforms get clipped. The clip is a SAFETY NET, not the primary defense.

**Frame-invariance check (re-derived):**

Under `h_out → h_out ∘ φ` for monotone smooth φ with Jacobian `φ'`:
- Framed coord changes: `y'' = φ(y') = φ(h_out(y))`.
- Dispersion changes: `σ̂²_y''` ≈ `σ̂²_y' · ⟨φ'⟩²`.
- σ_noise floor changes: `σ_noise² · J̄_new ≈ σ_noise² · J̄ · ⟨φ'⟩²`.
- log_J changes: `log_J_new = log_J + ⟨log φ'⟩`.

The first two scale identically by `⟨φ'⟩²`, so the `max` ratio inside `log()` is preserved → first MDL term invariant. The third changes by `+⟨log φ'⟩`; the second MDL term changes by `−N·⟨log φ'⟩` (sign-flipped). These cancel.

**v1.2 MDL is invariant under composition with monotone smooth φ on h_out**, to leading order. (To second order it leaks under heteroscedasticity — hence the §1.2 scope exclusion.)

### 2.2 Pre-promotion canary in BranchAndBoundMDLSearch (gp152 iter 2 finding)

v1.1 had no defense against MDL ordering inverting under a wrong Jacobian rescaling. v1.2 adds an INTERNAL pre-promotion check inside the branch-and-bound search — NOT a new runtime gate.

**Mechanism.** After the BranchAndBoundMDLSearch identifies a top-K best transformation pairs (default K=5), before returning the best:

1. For each `(h_in, h_out)` in top-K, perturb the Jacobian by ε ∈ {-0.01, +0.01}: compute `h_out_eps(y) = h_out(y) · (1 + ε)`, recompute MDL.
2. Verify that the rank ordering of the top-K is stable across {-ε, 0, +ε}: same #1, same #2.
3. If rank inverts at ε perturbation: log warning, fall back to identity transform for this fit. (v1.1's BackoffController had no such check; v1.2 adds it.)

**Cost:** 3× the top-K MDL evaluations (15 evaluations at K=5). Negligible vs the search cost.

This is the v1.2 fix for the iter-2 finding. It's an INTERNAL CHECK in `src/ztare/framer/search.py:BranchAndBoundMDLSearch`, not a new module under `framer_gates/`.

### 2.3 Scope tightening (gp152 iter 3 finding)

Already documented in §1.2: heteroscedastic noise + low effective precision are now explicit out-of-scope. The auto-disable + `disabled_reason` reporting is the only enforcement; no new gate.

### 2.4 What v1.2 does NOT change

- **Architecture (Components A-F + solver wrapper)** — unchanged from v1.1 §3.
- **Three runtime gates** (G-LIB-COVER, G-FILTER-INDEP, G-SYM-FN) + `framer_helped_canary` — unchanged from v1.1 §4. **No new gates.** The recursive-audit findings are MDL-formalism repairs, not new failure-mode detectors.
- **Integration Option C** (wrap solver fits) — unchanged.
- **Test cases A and B** — unchanged. Numerical predictions revised per v1.2 MDL formula (§3.6).

---

## 3. Architecture (unchanged from v1.1, condensed)

**Module path:** `src/ztare/framer/active_framer.py`

**Hand-off contract:**
```python
def frame(
    data: NDArray[(N, 2), float],
    meta: Dict[str, Any],
    rubric_data: Dict[str, Any],
) -> Tuple[NDArray[(N, 2), float], Dict[str, Any]]:
    """Same signature as v1.1; returns transformed_data + framing_report."""
```

### 3.1 Components

Unchanged from v1.1. Five canonical modules + one report writer:

| # | Module | Path | Status |
|---|---|---|---|
| A | SymmetryScanner | `src/ztare/framer/symmetry.py` | unchanged |
| B | DimensionalFilter | `src/ztare/framer/units.py` | unchanged |
| C | TransformationEnumerator | `src/ztare/framer/enumerate.py` | unchanged |
| **D** | **BranchAndBoundMDLSearch** | `src/ztare/framer/search.py` | **§2.2 pre-promotion canary added** |
| E | UniversalityAligner | `src/ztare/framer/collapse.py` | unchanged |
| F | ReportWriter | `src/ztare/framer/report.py` | unchanged |

### 3.2 Solver wrapper (unchanged)

`src/ztare/framer/solver_wrapper.py`'s `fit_with_framer()` — sole public entry point. Signature unchanged from v1.1 §3.2.

### 3.3 MDL formula (revised — §2.1)

See §2.1 above. Replaces v1.1's three-error formula with a corrected, frame-invariant, sign-corrected, clip-bounded version.

### 3.4 Sample size precondition (unchanged)

N ≥ 80, else auto-disable.

### 3.5 Noise scale source (unchanged)

`σ_noise` from rubric → meta → auto-estimate (with warning).

### 3.6 Numerical predictions (re-validated under v1.2 MDL)

**Test case A** (single dataset): `y = exp(x²) / (1 + log x)`, `N=200`, `σ=0.01`, `x ∈ [1, 10]`.

Predictions under v1.2 corrected MDL:
- Native MDL: ≈ -1478 bits
- Framed MDL: ≈ -1530 bits (between v1.0's -1560 and v1.1's -1542 — the σ_noise floor transformation gives back ~12 bits the v1.1 over-counted)
- **Predicted gain ≈ 52 bits** (v1.0 said 82, v1.1 said 64, v1.2 says 52 — increasing honesty).
- Iteration savings: 28 → 9 (±2). Same as v1.1; the iter-savings prediction is dominated by the ordinal MDL ranking, not the absolute bit count.

**Test case B** (universality, two datasets): `y_i = A_i x^α + B_i`. Predictions unchanged from v1.1 (the Universality Aligner runs in framed coords; the MDL bug doesn't affect joint-collapse residual).

---

## 4. Runtime gate stack (unchanged from v1.1)

THREE GATES + ONE CANARY. **Same set as v1.1.** No additions in v1.2.

### 4.1 G-LIB-COVER — Library Coverage Gate

Threshold raised in v1.1 to 100 bits (preserved in v1.2). Detects when no in-library transform produces a real MDL improvement → ground truth likely outside Σ.

### 4.2 G-FILTER-INDEP — Filter Independence Gate

Bootstrap-correlation check on SymmetryScanner + DimensionalFilter pruning decisions. |corr| < 0.3 at bootstrap_n=300.

### 4.3 G-SYM-FN — SymmetryScanner False-Negative Gate

Canary substrate detection rate ≥ 0.95 at canary_count = 60.

### 4.4 framer_helped_canary — Iatrogenesis Detector

Same as v1.1. Compare framed vs raw solver iteration count + residual; auto-disable if framed loses.

---

## 5. Wiring into autoresearch_loop.py (unchanged from v1.1)

Same as v1.1 §5: `fit_with_framer` wraps every `fit_primitive.fit_parameters` and `compress_champion.run_compress` call site. Rubric flag `enable_framer: bool` (default false).

---

## 6. Implementation TODOs (paper-level rigor — updated)

From v1.1 §6:
1. ✓ Per-grammar inversion proof (still TODO).
2. ~ Sub-modularity proof — superseded by branch-and-bound (no longer needed).
3. ✓ Depth-2 sufficiency justification (still TODO).
4. ✓ Generative yield class statement (Newton — still TODO).
5. ✓ Frame-invariance proof (Einstein — formalize the cancellation argument).
6. ✓ Noise-floor characterization (Heisenberg — still TODO).

**v1.2 NEW paper TODOs (from cross-validation):**

7. **First-principles MDL derivation (deep TODO).** v1.2's MDL formula is corrected BIC-by-convention. The right v2.0 move is to derive MDL from a stated likelihood axiom (not retrofit BIC). Candidate frameworks: Normalized Maximum Likelihood (NML), Rissanen's stochastic complexity, or pre-quantized Bayesian model selection. **This is the v2.0 research project.** Expected outcome: an MDL formula that handles heteroscedasticity natively and doesn't need clip safety nets.

8. **Heteroscedasticity extension (v2.0 TODO).** Current scope excludes heteroscedastic noise. v2.0 should either include a per-region σ_noise estimator or admit the limit is fundamental.

9. **Finite-precision-aware coding (v2.0 TODO).** Replace `log σ̂²` with a quantization-aware code length (e.g., codelength of residuals at the data's actual precision). Expected to handle 4-bit and 8-bit data substrates without auto-disable.

---

## 7. Validation protocol (revised)

Before `enable_framer=True` is promoted to default-on:

1. **Test cases A and B pass under v1.2 MDL formula** (predicted gain 52 bits, not 64 or 82).
2. **Three gates self-test** + canary self-test (unchanged from v1.1).
3. **A/B benchmark** on GP-148 archive (unchanged from v1.1).
4. **GP-146-style validation substrate** (unchanged from v1.1).
5. **Lorentz negative-control** (unchanged from v1.1).
6. **NEW v1.2: Frame-invariance scaling test.** For test case A, evaluate MDL under `(h_in, h_out)` and `(h_in, c · h_out)` for c ∈ {0.1, 0.5, 1, 2, 10}. Verify MDL changes by < 2 bits across the c range (after the Jacobian-transformation fix). v1.1 fails this test (>70 bits drift per gp153 iter 0); v1.2 should pass.
7. **NEW v1.2: Heteroscedasticity guard test.** Generate synthetic data with `σ(y) = 0.01 + 0.1·|y|`; verify Framer auto-disables with `disabled_reason = "heteroscedastic_noise"`.
8. **NEW v1.2: Low-precision guard test.** Quantize test case A data to 4 bits; verify Framer auto-disables with `disabled_reason = "low_effective_precision"`.
9. **NEW v1.2: MDL ordering stability test.** For test case A, perturb top-K rank by ε ∈ {-0.01, +0.01}; verify ranking does not invert.

---

## 8. Out-of-scope reaffirmation (v1.2 explicit list)

The Framer engages only when ALL of these hold:
- `fit_score_mode in {"continuous_l2", "continuous_rmse"}` (scalar-kinematic substrate)
- `enable_fit_primitive == True`
- `N ≥ 80`
- `meta["units"]` does not require bivariate transformation (Lorentz-class auto-skip)
- Heteroscedasticity test passes (Breusch-Pagan p > 0.01)  ← **v1.2 NEW**
- Effective precision ≥ 8 bits  ← **v1.2 NEW**

All six checks at the top of `fit_with_framer`; pass-through with `disabled_reason` logged on any fail.

---

## 9. Provenance & full audit trail

- **Audit projects:**
  - `projects/gp152_framer_architecture_audit/` — original audit + run-2 (iter 2, iter 3 findings)
  - `projects/gp153_framer_spec_critique/` — recursive critique (iter 0 finding)
- **Champion theses (architectural sources):**
  - gp152 iter 1 (score 91): original architecture
  - gp153 iter 0 (score 88): MDL formula fixes
- **Critical iters (flaw-detecting):**
  - gp152 iter 2 (score 50): MDL ordering inversion → §2.2 fix
  - gp152 iter 3 (score 58): heteroscedasticity + finite precision → §1.2 fix
  - gp153 iter 0 (score 88): three MDL formula errors → §2.1 fix
- **Panel review (v1.1 source):** Newton, Einstein, Heisenberg, Munger.
- **F-rows:** F-GP152-FRAMER-BLUEPRINT-01, F-GP153-MDL-FORMULA-FIX-01 (TBD on run close).

## 10. Spec status

- v1.0 (superseded): iter-1 architecture; 5 panel-detected flaws.
- v1.1 (superseded): panel-revised; 3 cross-validated flaws.
- **v1.2 (this document): cross-validated, ready-for-implementation.**
- v1.3 (planned, post-implementation): post-mortem revisions based on actual benchmark performance.
- v2.0 (research project): first-principles MDL rebuild (NML / stochastic complexity); heteroscedasticity-native; pre-quantized coding for finite precision; non-separable transformations.

## 11. Key v1.2 changes summary (one page)

**MDL formula:**
- Before: `N·log(max(σ̂²_y', σ_noise²·0.25)) + N·⟨log|∂h_out/∂y|⟩ + K·log N`
- After:  `N·log(max(σ̂²_y', σ_noise²·J̄·0.25)) - N·clip(⟨log|∂h_out/∂y|⟩, -10, +10) + K·log N`
- Diffs: σ_noise floor transformed by `J̄`; Jacobian sign flipped; log-Jacobian clipped.

**Scope:**
- Added auto-disable on heteroscedastic noise (Breusch-Pagan p < 0.01).
- Added auto-disable on effective precision < 8 bits.

**Search:**
- BranchAndBoundMDLSearch adds pre-promotion ε-perturbation rank-stability check.

**Gate stack:**
- Unchanged — three gates + canary, NOT four-plus per finding. Resists Ptolemy-with-epicycles.

**Predictions:**
- Test case A MDL gain: 82 (v1.0) → 64 (v1.1) → **52 (v1.2)**. Increasing honesty.
- Iter savings: 28 → 9 (±2) unchanged.

**Implementation cost vs v1.1:**
- ~50 lines: MDL formula update, scope-precondition checks, ε-perturbation rank check.
- Architecture, gate stack, integration: unchanged.
- Cheap to apply.
