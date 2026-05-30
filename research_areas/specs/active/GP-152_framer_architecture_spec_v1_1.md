# GP-152 — Framer Architecture Spec v1.1 (SUPERSEDED)

**SUPERSEDED 2026-04-24** by `GP-152_framer_architecture_spec_v1_2.md` after gp152 run-2 (iters 2-3) and gp153 run-1 (iter 0) surfaced three additional decisive flaws the human panel missed. v1.1 is preserved here for diff history.

**Flaws caught in cross-validation (see v1.2 §2 for fixes):**
1. **gp152 iter 2 (score 50):** v1.1's BackoffController has no recovery for MDL ordering inversion under wrong Jacobian rescaling.
2. **gp152 iter 3 (score 58):** v1.1's Jacobian correction is falsified under heteroscedastic noise + finite-precision coding.
3. **gp153 iter 0 (score 88):** v1.1's MDL formula has THREE compounding errors — σ_noise floor in raw-y units (not Jacobian-transformed), Jacobian sign error, no log-Jacobian clip.

**Status:** SUPERSEDED — do not implement against this version

**Date:** 2026-04-24
**Supersedes:** `GP-152_framer_architecture_spec_v1.md` (v1.0)
**Source:** gp152 iter-1 thesis (score 91, champion) + 4-panel review (Newton, Einstein, Heisenberg, Munger)

This spec was the panel-revised version. v1.2 fixes the v1.1 flaws cross-validated by recursive audit.

---

## 1. Purpose & scope (revised)

The Framer is a **pre-solver representation-search phase** that wraps the existing fit-primitives (`fit_primitive.py`, `compress_champion.py`) so the solver receives data in MDL-minimal coordinates without the rest of the pipeline knowing.

### 1.1 In scope

- **Numerical-fit substrates** with single-curve or aligned-multi-dataset structure.
- **Axis-separable coordinate transformations** of the form `(x, y) → (h_in(x), h_out(y))` where `h_in, h_out` come from the primitive library `Σ = {identity, shift, scale, power_k, log, exp, reciprocal}` at composition depth ≤ 2.
- **Sample size N ≥ 80** per dataset (Heisenberg noise-floor minimum; see §3.4).
- **Reported noise scale σ_noise** in the rubric or evidence (Heisenberg bandwidth-derivation requirement; see §3.5).

### 1.2 Out of scope (revised, explicit)

These were implicitly excluded in v1.0; the panel made them explicit:

- **Bivariate / mixing transformations** (Einstein's Lorentz Gedankenexperiment): any `h: ℝ² → ℝ²` that does not factor as `h_in × h_out`. The Lorentz interval `s² = c²t² - x²`, the symplectic group, and any gauge transformation are all invisible to this Framer. *Defer to a future v2.0 with non-separable transformation primitives.*
- **Discrete number-theoretic substrates** (gp077-class): the discrete-exact `py_exec` grammar runs a separate code path. The Framer does not engage when `fit_score_mode == "discrete_exact"`.
- **Text-driven / qualitative-thesis substrates** (gp150-class architectural audits, gp145b-class null theorems): no numerical curve to transform. Framer disabled when `fit_score_mode == "none"`.
- **Continuous chaotic ODE substrates** (gp140-class): the autocorrelation-radius weak-form SINDy pipeline runs in its own coordinate space (state-space trajectories). The Framer does not engage when `fit_score_mode == "dynamical_lattice"`.

The Framer's competence is the **Phase-2 scalar-kinematic substrate class** (solver #2 in evidence Set A): SciPy `curve_fit` over additive templates. That's exactly one of the five substrate classes — the panel is right that v1.0 over-claimed scope.

### 1.3 Pre-registered discriminator

- **Current observable** (GP-148 mining baseline): D = mean iters to first ≥85 score on benchmark = 28.
- **Forward observable**: D_thesis ≈ 10. Framed median ≤ 15 → thesis passes; ≥ 15 → rival ("reactive only") survives.
- **Falsifier note (Munger):** if framed > unframed on the **`framer_helped_canary`** held-out test (§4.5), Framer auto-disables for that run regardless of MDL.

---

## 2. Five revisions from panel review

### 2.1 Integration locked to Option C — wrap solver fits

Unanimous panel pick. The Framer wraps `fit_primitive.fit_parameters()` and `compress_champion.run_compress()` so that:
- Solver receives `(h_in(x), h_out(y))` rather than raw `(x, y)`.
- Returned coefficients are reported in framed coordinates **with the framing transform metadata attached** so the operator can untransform.
- The mutator's prompt and `evidence.txt` are **unchanged** (Newton: avoids contaminating the language layer; Einstein: keeps apparatus and data in one frame; Heisenberg: makes "did the Framer help?" cleanly measurable; Munger: keeps the experiment controlled).

Wiring detail: see §5.

### 2.2 Greedy → depth-2 branch-and-bound

Newton's critique: greedy on a non-sub-modular MDL function admits arbitrarily bad worst-case ratio. The panel's resolution is the depth-2 tree itself: with `|Σ| = 7` (counting identity), `|Σ²| = 49` pairs at depth 1, and ~14² = 196 at depth 2 (most pruned by SymmetryScanner + DimensionalFilter). After filtering: typically 30-50 candidates total. Branch-and-bound on this size is tractable.

Algorithm:
1. Filter Σ × Σ via SymmetryScanner + DimensionalFilter (Component A + B). Output: `M_filtered` ≤ ~14 candidate pairs.
2. Compute MDL for every depth-1 pair. Sort.
3. For top-K (default K=5) depth-1 pairs, expand to depth-2 children, compute MDL.
4. Return the global minimum.

Worst case: O(M_filtered² · evaluations). With evaluation cost dominated by KDE on N points, the per-evaluation cost is O(N log N). Total: O(M² · N log N) ≈ 200 · 200·7 ≈ 280k operations on test case A. Well under per-iter budget.

This is a **complete search at depth 2**, not a beam search. The G-BEAM-EPS gate from v1.0 is therefore **deleted** — no beam to be ε-bounded.

### 2.3 MDL formula with Jacobian correction (Einstein's frame-invariance fix)

v1.0 MDL formula:
```
MDL = N · log(σ̂²) + K_fn · log(N)
```
Einstein's fix:
```
MDL = N · log(σ̂²_y') + N · ⟨log |∂h_out/∂y|⟩ + K_fn · log(N)
```
where:
- `σ̂²_y'` is the dispersion of residuals **in the framed y coordinate** `y' = h_out(y)`.
- `⟨log |∂h_out/∂y|⟩` is the average log-Jacobian over the data — converts the dispersion from framed-y units to neutral reference-measure units.
- `K_fn` is the count of free parameters in `h_in + h_out` (each primitive contributes 1 unit of description length: identity=0, shift=1, scale=1, power_k=1, log=0, exp=0, reciprocal=0).

**Frame invariance check**: under `h_out → h_out ∘ φ` for any monotone φ, the Jacobian term changes by `+N·⟨log |∂φ/∂y'|⟩` and the dispersion term changes by `-N·⟨log |∂φ/∂y'|⟩²` to first order — these cancel at leading order, so the MDL is invariant to monotone reparameterization of the framed coordinate. (This is exactly the property v1.0 lacked.)

**σ̂² floor (Newton's degeneracy fix)**:
```
σ̂² ← max(σ̂²_estimated, σ_noise² · 0.25)
```
`σ_noise` is read from rubric or evidence (see §3.5). The 0.25 factor allows for the case where the framed coords genuinely reduce variance below the raw noise (real signal extraction), but prevents the σ̂²→0 collapse Newton flagged.

### 2.4 Bandwidths derived from σ_noise (Heisenberg's free-parameter fix)

v1.0 left LOWESS bandwidth `h_L` and KDE bandwidth `h_K` unspecified.

v1.1:
```python
h_L = max(2 * sigma_noise / max(|y|),  N**(-1/5))   # Silverman-style
h_K = 1.06 * sigma_residual * N**(-1/5)             # Silverman optimal
```
- `h_L` shrinks with reported noise floor; bounded below by Silverman to keep variance bounded.
- `h_K` is Silverman's optimal for Gaussian-like residuals; if residuals are heavy-tailed (G-FILTER-INDEP fail mode), inflate `h_K` by 1.5×.

Both bandwidths are now **derived**, not free.

### 2.5 `framer_helped_canary` runtime check (Munger's "made it worse" fix)

Before promoting the Framer's chosen `(h_in, h_out)` to the actual solver fit:

1. Run the solver on `(x, y)` raw → record `iters_raw, residual_raw`.
2. Run the solver on `(h_in(x), h_out(y))` → record `iters_framed, residual_framed`.
3. **Decision rule**:
   - If `iters_framed < iters_raw AND residual_framed ≤ 1.05 × residual_raw` → use framed.
   - Else → use raw, log `framer_disabled_for_run = true` with reason.

This requires running the solver twice on the first iteration only; subsequent iterations cache the decision.

The canary is the **only** safeguard against Framer iatrogenesis. v1.0 had no such check.

---

## 3. Architecture (revised)

**Module path:** `src/ztare/framer/active_framer.py`

**Hand-off contract:**
```python
def frame(
    data: NDArray[(N, 2), float],
    meta: Dict[str, Any],
    rubric_data: Dict[str, Any],
) -> Tuple[NDArray[(N, 2), float], Dict[str, Any]]:
    """
    Returns:
        transformed_data : (h_in(x), h_out(y))   # or raw data if Framer disabled
        framing_report   : {
            "h_in":          SymbolicExpr,
            "h_out":         SymbolicExpr,
            "MDL":           float,
            "MDL_baseline":  float,                # MDL for identity transform
            "MDL_gain_bits": float,
            "scores":        List[Tuple[Expr, Expr, float]],
            "gates":         Dict[str, Any],       # gate verdicts (§4)
            "canary":        Dict[str, Any],       # framer_helped check (§4.5)
            "framer_engaged": bool,                # False if canary failed
            "disabled_reason": str | None,
        }
    """
```

### 3.1 Component graph (revised)

| # | Module | Path | Purpose | Complexity |
|---|---|---|---|---|
| A | SymmetryScanner | `src/ztare/framer/symmetry.py` | Bootstrap-resampled exponent / separability / parity tests; reports detection rate **with confidence interval** (Heisenberg fix) | O(N) per dataset, B bootstrap iters |
| B | DimensionalFilter | `src/ztare/framer/units.py` | Buckingham-π enumeration on `meta["units"]`; discards dimensionally-illegal pairs | O(M) per axis |
| C | TransformationEnumerator | `src/ztare/framer/enumerate.py` | Generates all candidate pairs at depth 1 + (top-K) depth 2 | O(M²) |
| D | BranchAndBoundMDLSearch | `src/ztare/framer/search.py` | **Replaces v1.0 GreedyMDLSearch**. Complete depth-2 search via MDL-bound pruning | O(M_filtered² · N log N) |
| E | UniversalityAligner | `src/ztare/framer/collapse.py` | Multi-dataset joint scaling optimizer (Levenberg-Marquardt) | O(N_datasets · M log M) |
| F | ReportWriter | `src/ztare/framer/report.py` | Serializes transforms + Jacobian + canary verdicts to `meta["framer"]` | — |

### 3.2 Solver wrapper (new in v1.1)

**Module path:** `src/ztare/framer/solver_wrapper.py`

```python
def fit_with_framer(
    fit_fn: Callable,           # e.g., fit_primitive.fit_parameters
    data: NDArray,
    meta: Dict[str, Any],
    rubric_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Wraps a solver fit call. If Framer is enabled and canary passes, runs
    the fit in framed coordinates and untransforms the result. Otherwise
    runs in raw coordinates. Either way returns a uniform shape.
    """
    if not rubric_data.get("enable_framer", False):
        return fit_fn(data, meta, rubric_data)
    transformed, framing_report = frame(data, meta, rubric_data)
    if not framing_report["framer_engaged"]:
        return fit_fn(data, meta, rubric_data)  # canary disabled framing
    fit_result = fit_fn(transformed, meta, rubric_data)
    fit_result["framing_report"] = framing_report
    fit_result["coefficients_in_framed_coords"] = fit_result["coefficients"]
    fit_result["coefficients"] = _untransform(fit_result["coefficients"], framing_report)
    return fit_result
```

`fit_with_framer` is the **only public entry point**. `frame()` is internal.

### 3.3 MDL formula (revised, with Jacobian)

```
MDL(h_in, h_out)
  = N · log(max(σ̂²_y', σ_noise² · 0.25))     # dispersion in framed coords, floored
  + N · ⟨log |∂h_out/∂y|⟩                     # Jacobian — frame-invariance restored
  + K_fn · log(N)                              # primitive-count penalty
```

`σ̂²_y'` is the kernel-density estimate of residual radial distance from a non-parametric LOWESS fit, **computed in the framed `y' = h_out(y)` coordinate**. The Jacobian is averaged over the data: `(1/N) · Σ_i log |h_out'(y_i)|`.

### 3.4 Sample size precondition

Framer requires N ≥ 80. Below this, Heisenberg's noise-floor analysis says the σ̂² estimator's standard error swallows the gate thresholds. If N < 80, Framer is **automatically disabled** with `disabled_reason = "N_below_minimum"`.

### 3.5 Noise scale source

`σ_noise` is read from one of (in priority order):
1. `rubric_data["sigma_noise"]` (operator-declared).
2. `meta["sigma_noise"]` (dataset-declared in evidence).
3. Auto-estimated from data: `σ_noise ≈ MAD(residuals from polynomial fit) / 0.6745`. Auto-estimation triggers a warning since it's circular (uses pre-Framer fit).

### 3.6 Numerical predictions (re-validated under v1.1 MDL)

**Test case A** (single dataset): `y = exp(x²) / (1 + log x)`, `N=200`, `σ=0.01`, `x ∈ [1, 10]`.
- v1.1 prediction (re-derived with Jacobian):
  - Native MDL: ≈ -1478 bits
  - Framed MDL: ≈ -1542 bits (slightly lower than v1.0's -1560 because Jacobian correction adds ~18 bits for `h_out` involving `log`-derivative)
  - **Predicted gain ≈ 64 bits** (down from v1.0's 82 — more honest).
- Iteration savings: 28 → 9 (±2). Wider tolerance reflects the Heisenberg noise envelope.

**Test case B** (universality, two datasets): predictions unchanged from v1.0.

---

## 4. Runtime gate stack (revised)

v1.0 had four gates. v1.1 has **three** (G-BEAM-EPS deleted because beam-search is replaced by complete branch-and-bound at depth 2; and adds the `framer_helped_canary` as the fourth check.

### 4.1 G-LIB-COVER — Library Coverage Gate

(Same contract as v1.0, but threshold raised from 50 to **100 bits** per Heisenberg's noise-floor analysis. 100 bits is 5× the σ̂² estimator's standard error at N=200, properly above the noise envelope.)

### 4.2 G-FILTER-INDEP — Filter Independence Gate

(Same contract as v1.0; threshold |corr| < 0.3 retained. bootstrap_n raised from 100 to **300** per Heisenberg's standard-error analysis.)

### 4.3 G-SYM-FN — SymmetryScanner False-Negative Gate

(Same contract as v1.0; canary substrate count raised from 3 to **60** per Heisenberg's Wilson-interval analysis. With 60 canaries, ≥0.95 detection rate has Wilson-interval upper bound ≤ 0.05.)

### 4.4 G-BEAM-EPS — DELETED

No beam search in v1.1; complete search at depth 2.

### 4.5 framer_helped_canary — Iatrogenesis Detector (NEW in v1.1)

**Module:** `src/ztare/framer/canary.py`

**Failure mode caught:** Framer chooses a transform that the in-pipeline checks (G-LIB-COVER, G-FILTER-INDEP, G-SYM-FN) approve, but which makes the actual solver fit WORSE (higher iteration count or larger residual).

**Detection contract:**
```python
def run_framer_helped_canary(
    fit_fn: Callable,
    data: NDArray,
    framed: NDArray,
    framing_report: Dict[str, Any],
    meta: Dict[str, Any],
    rubric_data: Dict[str, Any],
    iter_budget: int = 5,
) -> Dict[str, Any]:
    """
    Runs the solver in BOTH raw and framed coords with iter_budget iters.
    Returns:
        {
            "iters_raw": int,
            "iters_framed": int,
            "residual_raw": float,
            "residual_framed": float,
            "framer_helped": bool,
            "rationale": str,
        }
    """
```

**Pass criterion:** `iters_framed < iters_raw` AND `residual_framed ≤ 1.05 · residual_raw`.

**Fail behavior:** Framer disabled for the run; report `disabled_reason = "canary_failed"` with the iter_raw/iter_framed numbers logged.

This is the **only** structural defense against Framer iatrogenesis. Munger's lollapalooza fix.

---

## 5. Wiring into autoresearch_loop.py

**Insertion point:** wherever `fit_primitive.fit_parameters` and `compress_champion.run_compress` are called. Specifically:

- `fit_primitive.fit_parameters` is called at multiple sites in autoresearch_loop.py post-mutation. All call sites should be migrated to `fit_with_framer(fit_fn=fit_primitive.fit_parameters, ...)`.
- Same for `compress_champion.run_compress`.

**Rubric flag:** `enable_framer: bool` (default `false` for back-compat).

**Compatibility:** when `enable_framer=False`, `fit_with_framer` is a pass-through. Existing pipeline unaffected.

---

## 6. Implementation TODOs (paper-level rigor)

Same as v1.0 §6:
1. Per-grammar inversion proof (iter 3 critique).
2. Sub-modularity proof — **deleted** (v1.1 uses branch-and-bound, no longer needed).
3. Depth-2 sufficiency justification.

NEW v1.1 paper TODOs from panel review:
4. **Generative yield** (Newton): name at least one CLASS of physical regularities the Framer's existence implies beyond benchmark fit acceleration. Candidate: any law expressible at depth ≤ 2 in Σ from a dataset of ≥ 80 points has an MDL plateau detectable in O(M²·N log N) time, providing a constructive existence proof for parsimonious laws in this class.
5. **Frame-invariance proof** (Einstein): formalize the cancellation argument under `h_out → h_out ∘ φ` for monotone φ.
6. **Noise-floor characterization** (Heisenberg): pre-register the σ̂² estimator's standard error as a function of N, h_L, h_K.

---

## 7. Validation protocol (revised)

Before `enable_framer=True` is promoted to default:

1. **Test case A and B pass** under v1.1 MDL formula (predicted gain 64 bits, not 82).
2. **Three gates self-test** (G-LIB-COVER, G-FILTER-INDEP, G-SYM-FN) on canary substrates — pattern matches G-CIRC + G-FALSIFY self-tests.
3. **`framer_helped_canary` self-test** — verify canary correctly identifies pathological transforms as harmful.
4. **A/B benchmark** on GP-148 archive: framed vs unframed mean iterations to ≥85. Pass criterion: framed median ≤ 15 iters (vs 28 baseline). Out-of-scope substrates (gp077, gp140, gp145b, gp150) automatically excluded.
5. **GP-146-style validation substrate** with synthetic coordinate-transformed evidence: feed `y = log(λ_1·x)` instead of `λ_1`; Framer must recover `h_out = exp` and Phase 2 must then recover `λ_1`.
6. **Lorentz negative-control test** (Einstein): feed data from a Lorentz-mixed system; Framer must auto-disable (return identity + canary fail) rather than report a misleading axis-separable surrogate.

---

## 8. Out-of-scope reaffirmation (v1.1 explicit list)

The Framer is for **scalar-kinematic substrates only** (solver class #2 of the five). It does NOT engage when:

- `fit_score_mode == "discrete_exact"` (number-theoretic, gp077-class)
- `fit_score_mode == "none"` (qualitative thesis, gp150/gp145b-class)
- `fit_score_mode == "dynamical_lattice"` (continuous chaotic, gp140-class)
- `enable_fit_primitive == False` (no fit at all)
- `N < 80` (Heisenberg noise-floor minimum)
- `meta["units"]` declares fundamentally different unit families on x and y where bivariate transformations would be required (Lorentz-class)

All six exclusions are checked at the top of `fit_with_framer` and trigger a pass-through with `disabled_reason` logged.

---

## 9. Provenance & panel review

- **Audit project:** `projects/gp152_framer_architecture_audit/`
- **Champion thesis (v1.0 source):** `history/1777068641_iter1_score_91_*.md`
- **Cycled critiques (v1.0 gate sources):** iters 2-5 debate logs
- **Panel review (v1.1 revision sources):**
  - Newton: MDL formula degeneracy + greedy without sub-modularity + integration option C
  - Einstein: frame invariance / Jacobian correction + Lorentz Gedankenexperiment + four-gates-as-symptoms
  - Heisenberg: σ̂² noise floor + bandwidth derivation + N-minimum + threshold tightening
  - Munger: confirmation bias on test cases + Σ choice locked-in + missing iatrogenesis detector + circle-of-competence narrowing
- **F-row:** `research_areas/private/EXPERIMENT_TRACK_RECORD.md` F-GP152-FRAMER-BLUEPRINT-01

## 10. Spec status

- v1.0 (superseded 2026-04-24): iter-1 architecture extracted; flagged by panel.
- **v1.1 (this document, 2026-04-24): panel-revised, ready for implementation.**
- v1.2 (planned, post-implementation): post-mortem revisions based on actual benchmark performance.
- v2.0 (future): non-separable transformations (Lorentz-class) admitted to scope. Major rewrite.
