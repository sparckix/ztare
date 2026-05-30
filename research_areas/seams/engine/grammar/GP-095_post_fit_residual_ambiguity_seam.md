# GP-095 — Post-Fit Residual Ambiguity: Distinguish Convergence Failure, Ill-Conditioning, and Grammar Ceiling

> **Seam metadata** · `seam_id:` GP-095 · `track:` engine · `status:` Active - opened 2026-04-18 · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

## Status

Active — opened 2026-04-18

## ID

GP-095

## Eigenquestion

After GP-035 removes parameter-guess noise and Layer 3 mandatory removes LLM syntax noise, can the engine distinguish between SciPy convergence failure, ill-conditioned loss surface, and genuine grammar ceiling (GCH)?

## Problem Statement

GP-035 solved ambiguity class 1: LLM guessed bad params vs. science failed. Layer 3 mandatory (GP-035 extension, 2026-04-18) solved ambiguity class 2: LLM syntax error vs. science failed.

Neither solved ambiguity class 3: **optimizer pathology vs. grammar ceiling.**

When `residual=1.0` arrives at the gates, three distinct causes remain indistinguishable:

1. **Convergence failure (A''):** SciPy's optimizer got stuck in a local minimum. The form IS expressible but the solver didn't find the global optimum. Intervention: multi-start with different initializations.
2. **Ill-conditioned surface:** The loss landscape is pathological (flat, ridge-like, or degenerate). The form may be expressible but the solver can't navigate the surface. Intervention: reparameterize, change optimizer, or add regularization.
3. **Grammar ceiling (true GCH):** No parameterization of the proposed form can fit the data, regardless of initialization. The grammar genuinely cannot express the ground truth. Intervention: Component D primitive injection.

These three require opposite interventions. Conflating them wastes iterations (injecting primitives when the solver just needed a restart) or misses ceilings (restarting the solver when the grammar is genuinely insufficient).

## Origin

- Codex review (2026-04-18): "GP-035 solved ambiguity class 1. It did not solve ambiguity class 2 [now: class 3]. If you rewrite GP-035 as 'conditionally accepted with convergence gate,' you blur two eigenquestions."
- Epistemologist agent review (2026-04-18): "To confirm GCH, you need positive evidence that (a) the LLM chose a defensible family, (b) SciPy converged from multiple starts, and (c) nothing in the grammar can do better."
- GP-089 (A000009) Feynman Wall: unresolved whether `WALL_LIBRARY_INSUFFICIENT` was true GCH or solver artifact.

## Scope

**Covers:**
- Multi-start fitting with bounded seeds (N≥3 random initializations within parameter bounds)
- Surfacing solver metadata: `OptimizeResult.success`, `nfev`, Jacobian condition number, basin spread
- Explicit per-iteration classification: `reachable_low_residual`, `pathological_surface`, `ceiling_candidate`
- Integration with `fit_primitive.py` — where solver metadata is currently discarded

**Does not cover:**
- Layer 3 mandatory (already implemented as GP-035 extension)
- Component D primitive injection (GP-078/080 scope)
- Named import check or cognitive camouflage (GP-086 scope)
- Evidence_fit gate metric (already fixed, self-calibrating)

## Option Analysis

### Option A — Multi-Start Fitting with Classification

Run `curve_fit` from N≥3 random starting points within parameter bounds. Classify the outcome:

- **`reachable_low_residual`**: Best residual is below `gate_threshold` AND ≥60% of starts converged. The form is viable and the basin is findable. Initialization bias is the explanation if a single-start previously failed.
- **`pathological_surface`**: Two distinct cases: (a) best residual is below `gate_threshold` but <60% of starts converged — the solution exists but the basin is narrow and hard to navigate; (b) best residual is above threshold but `residual_spread > 0.5 * best_residual` — the loss surface is ill-conditioned, starts land in very different local minima. Intervention: reparameterize or flag for operator review.
- **`ceiling_candidate`**: Best residual is above `gate_threshold` AND residual spread is small — all starts converge to similar high residual. The grammar cannot fit this data regardless of initialization. This is the only outcome that supports GCH declaration.
- **`""` (empty)**: Fewer than 2 starts attempted; no multi-start signal available. Single-start runs never produce a classification.

**Verdict: Leading candidate.** Clean separation. Deterministic. Auditable. Compatible with existing `fit_primitive.py` by extending `fit_parameters()` to accept `n_starts` parameter.

### Option B — Jacobian Condition Number Only

Compute the condition number of the Jacobian at the solution. High condition number → ill-conditioned; low → well-conditioned.

**Verdict: Insufficient alone.** Condition number tells you about the local neighborhood of the solution, not whether other basins exist. A well-conditioned local minimum can still miss the global optimum. Must be combined with multi-start.

### Option C — Basin-Hopping or Differential Evolution

Replace `curve_fit` with a global optimizer (`scipy.optimize.differential_evolution` or `basin_hopping`).

**Verdict: Deferred.** These are compute-expensive (100x+ more function evaluations). Multi-start with N=3-5 provides sufficient discrimination at minimal cost. Global optimization is a future extension if multi-start proves insufficient.

## Required Deliverables

1. **Extend `fit_parameters()` in `fit_primitive.py`:** Accept `n_starts: int = 1` parameter. When `n_starts > 1`, run `curve_fit` from N random starting points. Return a `FitSuccess` with additional metadata: `n_starts_attempted`, `n_starts_converged`, `residual_spread`, `classification`.
2. **Surface solver metadata:** Capture `OptimizeResult.success`, `nfev`, and optionally Jacobian condition number from `curve_fit`'s `pcov` return value.
3. **Emit classification in `fit_result.json`:** Add `convergence_classification` field with values `reachable_low_residual | pathological_surface | ceiling_candidate`.
4. **Gate integration:** When stagnation_count ≥ 3, automatically increase `n_starts` to N≥3 for the stagnation detection loop. Classification feeds into Component D's decision to inject or declare GCH.

## Constraint Check

1. *Fix sits upstream of charter gates:* ✓. Multi-start runs inside `fit_parameters()`, before gates evaluate.
2. *Does not weaken the gates:* ✓. Gates still evaluate the best fit from all starts.
3. *Enforcement floor stays deterministic:* ✓. Multi-start + classification is fully deterministic given seeds.
4. *Closes a named failure class:* ✓. The class is `ambiguous_residual_1.0` — convergence failure vs. grammar ceiling.

## Closure Criterion

The seam returns to `closed` when:
- Multi-start fitting is implemented and unit-tested
- At least one run shows `ceiling_candidate` classification correctly distinguishing from `reachable_low_residual`
- GP-089 (A000009) Feynman Wall is retrospectively classified using the new discriminant
- No new ambiguity class is introduced

## Implementation Turn (2026-04-18)

**Delivered:**
1. `FitSuccess` dataclass extended with `n_starts_attempted`, `n_starts_converged`, `residual_spread`, `convergence_classification` fields (`fit_primitive.py`).
2. `fit_parameters()` accepts `n_starts: int = 1`. When > 1, runs `curve_fit` from N starting points (first = declared `initial_guesses`, rest = random within bounds, deterministic seed=42). Picks best result by lowest max residual.
3. Classification logic: `reachable_low_residual` (best residual < threshold), `pathological_surface` (spread > 0.5 * best), `ceiling_candidate` (all starts converge to similar high residual).
4. `fit_result_to_json()` emits `convergence` block in `fit_result.json` with all multi-start metadata.
5. `autoresearch_loop.py`: auto-escalates to `n_starts=3` when `stagnation_count >= 3`. Log line shows starts converged/attempted and classification.

**Tested:** synthetic `A * exp(-k * x) + C` target, 5 starts all converge to same basin with spread < 1e-12, classified `reachable_low_residual`. Implementation is functional.

**GP-089 Retrospective (2026-04-18):**

GP-089 uses `fit_score_mode: discrete_exact` — the fitter counts exact integer matches, no `curve_fit` is called. Every iteration returned `residual = 1.0` (0/N exact matches). Multi-start is inapplicable in this mode.

Retrospective classification: **`ceiling_candidate` by construction.** The grammar (sqrt, log, polynomial) cannot produce the exact integers A000009 requires. There is no optimizer pathology to distinguish from — the wall was always a pure grammar ceiling. This confirms INS-025: GCH was the right call, not a convergence artifact.

Implication for the seam: GP-095 multi-start applies only to `continuous_l2` substrates. For `discrete_exact`, `residual = 1.0` maps directly to `ceiling_candidate` without needing restart diversity. The seam should clarify this mode boundary.

**Remaining closure criteria:**
- Live continuous_l2 run showing `ceiling_candidate` distinguishing from `reachable_low_residual` (gp096_langevin_sandbox_16 is the candidate)
- No new ambiguity class introduced

## Links

- **GP-035:** Solved ambiguity class 1 (parameter-guess noise). Layer 3 mandatory (extension) solved ambiguity class 2 (LLM syntax noise). This seam solves ambiguity class 3 (optimizer pathology vs. grammar ceiling).
- **GP-074 Component C:** Residual fingerprinting provides shape hints. GP-095 provides convergence diagnostics. Different signals, complementary.
- **GP-085 GCH:** Grammar Ceiling Hypothesis. GP-095 provides the empirical discrimination gate that makes GCH confirmation rigorous.
