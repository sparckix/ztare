# GP-152 — Framer Architecture Spec v1.0 (SUPERSEDED)

**SUPERSEDED 2026-04-24** by `GP-152_framer_architecture_spec_v1_1.md` after a 4-panel review (Newton, Einstein, Heisenberg, Munger). v1.0 had five decisive flaws caught by the panel; v1.1 corrects them. v1.0 is preserved here for diff history.

**Panel-detected flaws (see v1.1 §2 for fixes):**
1. Integration option not locked → v1.1 commits to Option C (wrap solver fits).
2. Greedy MDL search lacks sub-modularity guarantee → v1.1 uses depth-2 branch-and-bound on 36-pair tree.
3. MDL formula not frame-invariant (Einstein) → v1.1 adds Jacobian correction.
4. Bandwidths free parameters (Heisenberg) → v1.1 ties to data σ_noise.
5. No "Framer made it worse" detector (Munger) → v1.1 adds `framer_helped_canary` runtime check.

**Source:** gp152_framer_architecture_audit, run-1, iter-1 thesis (score 91, champion). 4 cycled critique classes (iters 2, 4, 5 — iter 3 is rigor-only) become 4 runtime gates that protect the Framer pipeline.

**Status:** SUPERSEDED — do not implement against this version
**Date:** 2026-04-24
**Audit run:** `projects/gp152_framer_architecture_audit/`
**Iter-1 thesis:** `history/1777068641_iter1_score_91_*.md`

**Authoritative source for design decisions:** the iter-1 thesis verbatim. This document is a structured extraction with implementation contracts; if it disagrees with the thesis, the thesis wins and this document should be corrected.

---

## 1. Purpose & scope

The Framer is a **pre-solver representation-search phase** inserted between data ingestion and Phase C of `autoresearch_loop.py`. For any invariant of the form `f(h_in(x), h_out(y)) = C` where `(h_in, h_out)` are coordinate transformations from a bounded primitive library Σ, the Framer transforms data into the MDL-minimal coordinate frame BEFORE the existing solvers fit `f`.

**Scope (what the Framer covers):**
- Single-curve fits where the optimal coordinate transformation lies in `Σ = {shift, scale, power, log, exp, reciprocal}`.
- Multi-dataset universality collapse with ≤ 4 non-universal scaling parameters per dataset.

**Out of scope:**
- Invariants requiring transcendentals outside Σ (e.g., `y = erf(log x)`).
- Piecewise / branching coordinate definitions.
- Neural-network-based representation learning (no deterministic-gate paradigm available).

**Pre-registered discriminator** (from iter-1 thesis):
- Current observable: D = mean iterations to first ≥ 85 score on benchmark = 28 (GP-148 mining).
- Forward observable with Framer: D_thesis ≈ 10. If D_measured < 15 → thesis passes; ≥ 15 → rival ("reactive only") survives.

---

## 2. Architecture (iter-1 verbatim, condensed)

**Module path:** `src/ztare/framer/active_framer.py`

**Hand-off contract:**
```python
def frame(
    data: NDArray[(N, 2), float],
    meta: Dict[str, Any],
) -> Tuple[NDArray[(N, 2), float], Dict[str, Any]]:
    """
    Returns:
        transformed_data : (h_in(x), h_out(y))
        framing_report   : {
            "h_in":   SymbolicExpr,
            "h_out":  SymbolicExpr,
            "MDL":    float,
            "scores": List[Tuple[Expr, Expr, float]],
            "gates":  Dict[str, Any],     # framer-gate verdicts (§4)
        }
    """
```

**Component graph (one paragraph each):**

| Module | Path | Purpose | Complexity |
|---|---|---|---|
| **A. SymmetryScanner** | `src/ztare/framer/symmetry.py` | Empirical exponent detection (`y ∝ x^α`), additive-vs-multiplicative separability, parity, translation invariance. Eliminates 60-90% of `Σ × Σ` pairs. | O(N) per dataset |
| **B. DimensionalFilter** | `src/ztare/framer/units.py` | Buckingham-π enumeration on `meta["units"]` (pint tags); discards dimensionally-illegal transforms. | O(M) per axis |
| **C. TransformationEnumerator** | `src/ztare/framer/enumerate.py` | Lazy depth-1 tree of `M_filtered² ≤ R` candidates; depth-2 spill-over generated on demand. Amortized O(1) per next(). | — |
| **D. GreedyMDLSearch** | `src/ztare/framer/search.py` | Starts at identity; evaluates neighbors by `MDL = L_dispersion + K_fn · log N`; accepts neighbor if `ΔMDL < -τ` (τ=0 pure greedy at depth 1, τ>0 at depth 2). | O(M log M) per axis |
| **E. UniversalityAligner** | `src/ztare/framer/collapse.py` | For multi-dataset: jointly optimizes `(A_i, B_i, C_i)` per dataset by combined-dispersion minimization (Levenberg-Marquardt inside each MDL evaluation). | O(N_datasets · M log M) |
| **F. ReportWriter** | `src/ztare/framer/report.py` | Serializes winning transforms to `dataset.meta["framer"]` for provenance. | — |

**Total worst-case evaluations** (single dataset): `2 · M · log M + depth-2 spill-over ≈ O(M log M)`. With `M_filtered ≈ 7` (empirical), ~14 calls.

**MDL formula (decisive):**
```
MDL(h_in, h_out) = L_dispersion + K_fn · log N
  L_dispersion  =  N · log(σ̂²)   where σ̂² is kernel-density estimate of residual
                                  radial distance from non-parametric LOWESS fit
                                  (no law assumption — Phase 1 doesn't know f)
  K_fn          =  #free parameters of h_in + h_out (each primitive contributes 1)
```

This is the iter-1 thesis's commitment. `L_dispersion` is the Phase-1 collapse loss; `K_fn` is the transformation description-length penalty. The Phase-2 law description length is folded into the downstream solvers' BIC (no separate term needed at the Framer layer).

---

## 3. Numerical predictions (iter-1 thesis — pre-registered)

**Test case A** (single dataset): `y = exp(x²) / (1 + log x)`, `N=200`, `σ=0.01`, `x ∈ [1, 10]`.
- Framer chosen transforms: `h_in(x) = x²`, `h_out(y) = y - 1/log(x)`.
- Phase-2 fit: `y' = a·exp(z) + b`, k=2 parameters.
- Predicted MDL gain: **≈ 82 bits** (native: −1478 bits, framed: −1560 bits).
- Predicted iteration savings: **28 → 9 (±1)**.

**Test case B** (two datasets, universality): `y_i = A_i · x^α + B_i` with shared α.
- Predicted: UniversalityAligner finds `(A₁, A₂, B₁, B₂)` in ≤ 50 inner iterations.
- Predicted post-collapse dispersion: `std ≤ 1.25 · σ_noise`.
- Predicted BIC gain: **≥ log N_total − 3·log N_ds ≈ 225 bits**.

**Implementation validation:** the implemented Framer must pass these predictions to within stated tolerances on the same generated data. Failure on either prediction triggers spec revision before promotion.

---

## 4. Runtime gate stack (the four detected by gp152 cycling)

These gates fire at `frame()` exit, before returning to the main loop. Each catches a specific failure mode of the Framer pipeline. Gate verdicts are written to `framing_report["gates"]`.

### 4.1 G-LIB-COVER — Library Coverage Gate (from iter 1 weakest-point)

**Module:** `src/ztare/framer_gates/library_coverage_gate.py`

**Failure mode caught:** the ground-truth transform is OUTSIDE `Σ`, the Framer cannot recover it, but the Framer reports a sub-optimal in-library result with apparent MDL improvement.

**Detection contract:**
```python
def run_library_coverage_gate(
    framing_report: Dict[str, Any],
    data: NDArray,
    threshold_mdl_floor: float = 50.0,    # bits
) -> Dict[str, Any]:
    """
    Pass: best in-library MDL improvement >= threshold_mdl_floor AND
          best-in-library residual entropy decreases under increasing depth.
    Fail: MDL improvement saturates below threshold (signal that no Σ-combo
          is genuinely capturing the structure → ground truth likely outside Σ).
    """
```

**Pass criterion:** `framing_report["MDL"]_improvement >= threshold_mdl_floor` AND depth-1 vs depth-2 MDL improvement ratio is non-degenerate.

**Fail behavior:** Framer returns `(identity, identity)` — explicit "no improvement found" signal — rather than a misleadingly-best in-library transform.

### 4.2 G-FILTER-INDEP — Filter Independence Gate (from iter 2 weakest-point)

**Module:** `src/ztare/framer_gates/filter_independence_gate.py`

**Failure mode caught:** SymmetryScanner + DimensionalFilter assumed to fail independently with rate ≤ ε each → joint false-prune rate ≤ ε². Under correlated numerical noise, the joint rate could be Ω(ε), wrongly pruning the ground-truth transform.

**Detection contract:**
```python
def run_filter_independence_gate(
    sym_report: Dict[str, Any],
    dim_report: Dict[str, Any],
    bootstrap_n: int = 100,
) -> Dict[str, Any]:
    """
    Bootstrap-resamples data with noise injection; measures correlation
    coefficient between SymmetryScanner pruning decisions and
    DimensionalFilter pruning decisions across resamples.

    Pass: |corr(sym_pruned, dim_pruned)| < 0.3 (filters approximately independent)
    Fail: |corr| >= 0.3 → joint false-prune probability inflated; gate emits
          warning + downgrades the iter-1 thesis's ≥0.95 survival guarantee
          to a pessimistic Ω(ε) bound; Framer may still proceed but tags
          the result with reduced-confidence flag.
    """
```

**Pass criterion:** filters empirically independent under noise bootstrap.

**Fail behavior:** Framer flags `framing_report["confidence"] = "reduced"` and recommends operator manually verify the surviving transforms.

### 4.3 G-SYM-FN — SymmetryScanner False-Negative Gate (from iter 4 weakest-point)

**Module:** `src/ztare/framer_gates/symmetry_false_negative_gate.py`

**Failure mode caught:** SymmetryScanner's empirical exponent / separability tests have a false-negative rate `> 0`; missing a true symmetry causes the Framer to enumerate over a restricted space that excludes the right transform.

**Detection contract:**
```python
def run_symmetry_false_negative_gate(
    data: NDArray,
    sym_report: Dict[str, Any],
    canary_substrates: List[str] = ["power_law", "log_law", "additive_separable"],
) -> Dict[str, Any]:
    """
    For a small set of canary substrates with KNOWN symmetries, run
    SymmetryScanner against synthetic instances. Measure detection rate.

    Pass: detection rate >= 0.95 across canaries.
    Fail: any canary's symmetry missed → Framer cannot trust SymmetryScanner
          to prune; falls back to wider enumeration (no symmetry-based
          elimination, ~2-5x more candidates).
    """
```

**Pass criterion:** known-GT canary substrates pass at ≥ 95% rate.

**Fail behavior:** SymmetryScanner is bypassed for the current run; downstream MDL search runs over the full unfiltered Σ². Framer flags `framing_report["symmetry_filter_engaged"] = False`.

### 4.4 G-BEAM-EPS — Beam-Search ε-Approximation Gate (from iter 5 weakest-point)

**Module:** `src/ztare/framer_gates/beam_search_epsilon_gate.py`

**Failure mode caught:** GreedyMDLSearch's beam width (default 3, per iter-1) is empirical, not derived. If the global MDL optimum requires a wider beam, the search misses it → suboptimal transformation reported as champion.

**Detection contract:**
```python
def run_beam_search_epsilon_gate(
    search_history: List[Tuple[Expr, Expr, float]],
    width_used: int = 3,
    width_test: int = 6,
) -> Dict[str, Any]:
    """
    Re-run GreedyMDLSearch at width_test (>= 2 * width_used). If a better
    MDL is found at the wider width, the gate reports the gap.

    Pass: best-MDL at width_test - best-MDL at width_used <= 2 bits
          (within noise of the original search).
    Fail: gap >= 2 bits → reported beam was insufficient; Framer re-issues
          the search at width_test and reports the corrected transform.
    """
```

**Pass criterion:** wider-beam re-run does not find materially better MDL.

**Fail behavior:** Framer adopts the wider-beam result and tags `framing_report["beam_widening_applied"] = True` with the gap recorded.

---

## 5. Wiring into autoresearch_loop.py

**Insertion point:** PHASE_C dispatch, BEFORE `compress_champion` call. Approximate location: ~line 3300, immediately after the GP-143 continuous-chaotic post-champion hook.

**Rubric flag:** `enable_framer: bool` (default `false` for back-compat).

**Pseudo-code:**
```python
if rubric_data.get("enable_framer"):
    try:
        from src.ztare.framer.active_framer import frame
        transformed_data, framing_report = frame(data, meta)
        # Persist for downstream solvers
        write_json(workspace_dir / "framer_report.json", framing_report)
        # Replace data passed to Phase C
        data = transformed_data
    except Exception as exc:
        print(f"  🪞 Framer error (non-fatal): {exc}; using raw data")
```

**Compatibility:** when `enable_framer=False`, the existing pipeline is unaffected. Opt-in per-rubric.

---

## 6. Implementation TODO list (paper-level rigor gaps from iter 3)

These are NOT runtime gates — they are paper-level rigor items the implementation must address before publication:

1. **Per-grammar inversion proof** (iter 3 critique): for each of the 5 ZTARE solver grammars, show explicit parameter-cost gap on `f(log x, 1/y)=C`. The iter-1 inversion proof did this generically; the implementation paper must do it specifically.
2. **Sub-modularity proof** (iter 3 critique): GreedyMDLSearch's optimality assumes MDL is sub-modular over Σ. Either prove this for the chosen MDL formula or downgrade the optimality claim to "empirical-best on benchmark."
3. **Depth-2 sufficiency** (iter 3 critique): justify why depth-2 composition suffices for the claimed scope. Either argue from a coverage theorem or pre-register the falsifier class (depth-3+ invariants).

---

## 7. Validation protocol

Before `enable_framer=True` becomes default-on:

1. **Test case A and B pass** (per §3 numerical predictions).
2. **All 4 framer-gates pass** on canary substrates (similar to G-CIRC + G-FALSIFY self-tests).
3. **A/B benchmark run** on the existing GP-148 trajectory archive: framed vs unframed mean iterations to ≥ 85. Pass criterion: framed median ≤ 15 iterations (vs 28 baseline).
4. **GP-146-style validation substrate**: Arnold Cat Map with synthetic coordinate-transformed evidence (e.g., feed `y = log(λ_1 · x)` instead of `λ_1`). Framer must recover `h_out = exp` and Phase 2 must then recover `λ_1`.

---

## 8. Open questions (carry-overs for follow-up audits)

These are NOT in scope for v1; they are flagged for gp152b or later:

- **Multi-modal coordinate spaces:** what if the optimal transform is piecewise (different `h_in` on different regions of `x`)?
- **Adversarial Σ extension:** can the Framer suggest new primitives to add to Σ when G-LIB-COVER fails persistently?
- **Cost-of-Framer overhead:** what is the wall-clock cost of running the Framer per iteration vs the savings? Pre-register and measure.

---

## 9. Provenance

- **Audit project:** `projects/gp152_framer_architecture_audit/`
- **Charter:** `projects/gp152_framer_architecture_audit/project_charter.md`
- **Rubric:** `rubrics/gp152_framer_architecture_audit.json` v1.0
- **Champion thesis:** `history/1777068641_iter1_score_91_*.md`
- **Cycled critiques:** iters 2-5 debate logs
- **F-row:** `research_areas/private/EXPERIMENT_TRACK_RECORD.md` F-GP152-FRAMER-BLUEPRINT-01

## 10. Spec status

- v1.0 (this document, 2026-04-24): iter-1 architecture + 4 runtime gates extracted. Implementation-ready.
- v1.1 (planned): incorporate gp152b run results if launched (more critique classes → more gates).
- v2.0 (planned, post-implementation): post-mortem revisions based on actual benchmark performance.
