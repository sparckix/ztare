# Track A: Lean 4 Tactic Hint Schema from GP-088 Frozen Logs

Status: draft
Date: 2026-04-20
Source: GP-088 calibration_a01 frozen logs (sandbox_freeze.json)

## Motivation

GP-088 produced a clean negative result with rich iteration logs: 19+5 iterations
of expressions, residuals, gate failures, exponent grid firings, and topology
classifications. This data encodes the search trajectory through function space.

The question: can we translate these logs into Lean 4 tactic hints that would
allow a formal proof assistant to reproduce the discovery (or rule out candidates)
more efficiently?

## What the Logs Contain

Each iteration produces:
```
{
  "expression": "a * n ** d + b * math.log(n) + c",
  "parameter_names": ["a", "d", "b", "c"],
  "fitted_params": {"a": 1.68, "d": 0.562, "b": -0.31, "c": -1.69},
  "visible_max_abs_residual": 0.0395,
  "farther_tail_residual": 0.095,       // from gate_harness
  "gate_pass": false,
  "gate_failures": ["farther_tail_global_residual: 0.095 >= 0.08"],
  "exponent_grid_fired": true,          // if applicable
  "exponent_grid_selected": 0.5,        // if applicable
  "topology_class": "power_law",        // from classifier
  "bic": -261.7
}
```

## Schema: Log Entry → Lean 4 Tactic Hint

### 1. Gate Failure → Exclusion Lemma

When a candidate fails a gate, it provides a proof obligation:

```
Gate failure: farther_tail_global_residual: 0.095 >= 0.08
Expression: a * n^d + b * log(n) + c  with d = 0.562
```

Translates to:
```lean
-- For all parameter choices where d ∈ (0.55, 0.58), the form
-- a * n^d + b * log(n) + c has farther-tail residual > 0.08
-- on the evidence grid n ∈ [55, 74].
lemma exclude_power_log_d_near_056 :
  ∀ (a b c : ℝ) (d : ℝ),
    d ∈ Set.Icc 0.55 0.58 →
    ∃ n ∈ Finset.range' 55 20,
      |a * n^d + b * Real.log n + c - v_true n| > 0.08 := by
  -- tactic hint: witnesses from GP-088 iter 2 fit_result
  sorry
```

### 2. Exponent Grid Selection → Constraint Narrowing

When the exponent grid fires and selects d=0.5 over d=0.562:

```lean
-- BIC criterion prefers d=0.5 over d=0.562 on the visible grid
-- This constrains the search to d ∈ {0.25, 0.33, 0.5, 0.67, 1.0, 1.5, 2.0}
lemma bic_prefers_half_exponent :
  ∀ (a b c : ℝ),
    bic (fun n => a * n^(0.5:ℝ) + b * Real.log n + c) visible_grid <
    bic (fun n => a * n^(0.562:ℝ) + b * Real.log n + c) visible_grid := by
  -- tactic hint: numerical witness from GP-088 exponent grid
  -- BIC(d=0.5) = -261.7 < BIC(d=0.562) = -261.5
  sorry
```

### 3. Topology Class Exclusion → Search Space Pruning

When an entire topology class (e.g., log-polynomial) fails across multiple iterations:

```lean
-- No polynomial in log(n) of degree ≤ 3 with correction terms 1/n + 1/n^2
-- passes the farther-tail gate on this evidence grid
lemma log_polynomial_class_excluded :
  ∀ (coeffs : Fin 8 → ℝ),
    let f := fun n => coeffs 0 * (Real.log n)^2 + coeffs 1 * Real.log n +
                      coeffs 2 + coeffs 3 / n + coeffs 4 / n^2 + coeffs 5
    ∃ n ∈ farther_tail_grid,
      |f n - v_true n| > 0.08 := by
  -- tactic hint: all 12 log-polynomial iterations in GP-088 failed this gate
  -- witnesses: iter 8-19 fit results
  sorry
```

### 4. Gate Pass → Existence Witness

When a candidate passes all gates:

```lean
-- There exist parameters (a, b, c) such that a*sqrt(n) + b*log(n) + c
-- passes all four holdout gates
lemma sqrt_log_passes_all_gates :
  ∃ (a b c : ℝ),
    a ∈ Set.Icc 2.0 3.0 ∧
    b ∈ Set.Icc (-1.5) 0.0 ∧
    c ∈ Set.Icc (-3.0) (-1.0) ∧
    (∀ n ∈ holdout_grid, |a * n^(0.5:ℝ) + b * Real.log n + c - v_true n| < 0.05) ∧
    (∀ n ∈ farther_tail_grid, |a * n^(0.5:ℝ) + b * Real.log n + c - v_true n| < 0.08) := by
  -- tactic hint: numerical witness a=2.513, b=-0.832, c=-2.305
  -- from GP-088 exponent grid retroactive proof
  exact ⟨2.513, -0.832, -2.305, ...⟩
```

## Schema Summary

| Log Event | Lean 4 Translation | Proof Strategy |
|-----------|-------------------|----------------|
| Gate failure | Exclusion lemma (∃ witness of violation) | Numerical witness from fit_result |
| Exponent grid selection | Constraint narrowing (BIC ordering) | Numerical comparison |
| Topology class exhaustion | Search space pruning (∀ in class, ∃ failure) | Induction over iterations |
| Gate pass | Existence witness (∃ params, ∀ grid, bound holds) | Direct computation |
| Stagnation (n consecutive failures) | Exhaustion lemma | Aggregate over iteration logs |

## Implementation Path

1. **GP-088 log parser** → extracts structured events from `fit_result_iter_*.json` + `iteration_telemetry.jsonl`
2. **Hint generator** → maps each event type to a Lean 4 `sorry`-stub with numerical witnesses
3. **Lean 4 library** → defines `visible_grid`, `holdout_grid`, `farther_tail_grid`, `v_true`, `bic` as computable functions
4. **Proof automation** → `native_decide` or `norm_num` to discharge numerical bounds

## Open Questions

- Can the gate failure witnesses be machine-checked (native_decide on Float vs. Real arithmetic)?
- Should the topology class exclusion be stated per-iteration or as a class-level universal?
- How does the Lean proof handle the O(1/sqrt(n)) correction terms that cause exponent bias?

## Next Step: Symbolic Bridging via PSLQ (Track A milestone)

The current compiler embeds Float witnesses (e.g., a=2.513). Lean cannot prove
theorems about Floats in the mathematical sense. The upgrade path:

1. **PSLQ / Integer Relation Algorithm**: Map empirical floats to exact constants.
   `mpmath.identify(2.513)` → `π * sqrt(2/3)` (= 2.5651...).
   `mpmath.identify(-0.832)` → candidate `-1` (with O(1/sqrt(n)) correction).
   Library: `mpmath.identify()` or custom LLL lattice reduction.

2. **Symbolic rewrite**: Replace `2.513 * sqrt(n)` with `π * sqrt(2*n/3)`.
   The empirical law becomes the Hardy-Ramanujan leading term.

3. **Lean Real theorem**: Instead of Float arithmetic, emit:
   ```lean
   theorem hardy_ramanujan_leading :
     ∀ n : ℕ, n ≥ 5 →
       |Real.log (partition n) - π * Real.sqrt (2*n/3) + Real.log (4*n*Real.sqrt 3)|
       < C / Real.sqrt n
   ```

4. **Tactic generation**: Because ZTARE proved sqrt is the dominant term and log
   is sublinear correction, the compiler can instruct Lean to prioritize
   `asymptotics` and `filter` tactics over generic algebraic rewriting.

This bridges the gap between "the computer evaluated this and it's true" (current)
and "this is provably the Hardy-Ramanujan asymptotic limit" (target).

Implementation: `mpmath` is pip-installable. The PSLQ step adds ~10 lines to
lean_compiler.py. The hard part is the Lean Mathlib API for Real.log, partition
function definition, and asymptotic bounds — that requires Lean expertise.

Cross-substrate applicability:
- GP-088: 2.513 → π√(2/3), law identified as Hardy-Ramanujan
- KWW: 0.630 → fractional exponent (no known exact constant — empirical)
- Sandbox_20: 0.433 → between Rouse (0.5) and Zimm (0.67) — empirical, material-specific
- PSLQ identifies theoretical constants where they exist and flags empirical parameters where they don't
