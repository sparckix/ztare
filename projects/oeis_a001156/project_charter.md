# Project Charter — oeis_a001156

**Program:** oeis_a001156
**Status:** Sealed 2026-04-20. Apparatus cleared. Ready to run.
**Domain:** Sub-linear monotone increasing function of a positive integer index
**Convergence structure:** Not known in advance.

---

## Observable

For each positive integer index n, the observable is a smooth, slowly growing scalar quantity:

```
y(n) — a sub-linear, monotone increasing function of n
```

Evidence surfaces in `evidence.txt` report y(n) for n = 50 to 2000 (step 10). The mutator observes only this visible range.

---

## Core Question

Given the visible trajectory of y(n) for n in [50, 2000], what functional form f(n) best describes this sub-linear monotone growth and correctly predicts y(n) far beyond the visible range?

The sub-linear growth rate — whether it follows a power law, a logarithm, or a more complex composition — is not disclosed in this charter. The mutator must derive the functional form from the observable curve alone.

---

## Interface Contract (MANDATORY)

`test_model.py` MUST expose exactly:

1. `f(n)` — a callable taking a single positive integer `n` and returning a float (the predicted value of y at index n)

The function must use only `math` module functions (`math.log`, `math.exp`, `math.sqrt`), arithmetic operators, and numeric literals. No trigonometric functions needed. No external library imports permitted.

---

## Deterministic Gates

```yaml
deterministic_gates:
  - name: visible_global_residual
    metric: max_abs_residual_visible
    threshold: 0.05
    operator: lt
    evidence_source: evidence.txt
    scope: all_n

  - name: hidden_global_residual
    metric: max_abs_residual_holdout
    threshold: 0.04
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: all_n

  - name: farther_tail_global_residual
    metric: max_abs_residual_farther_tail
    threshold: 0.08
    operator: lt
    evidence_source: evidence_farther_tail.txt
    scope: all_n

  - name: farther_tail_terminal
    metric: terminal_abs_error_farther_tail
    threshold: 0.06
    operator: lt
    evidence_source: evidence_farther_tail.txt
    scope: terminal_n
```

---

## Farther-Tail Contract

```yaml
asymptotic_claim: true
farther_tail_contract: true
```

Evidence surfaces:
- `evidence.txt` — visible (n = 50..2000, step 10)
- `evidence_holdout.txt` — hidden in-range (n = 2001..10000, step 10)
- `evidence_farther_tail.txt` — hidden farther-tail (n = 10001..50000, step 25)

A model that fits the visible range but fails to extrapolate correctly to the farther tail is penalized by the gate battery regardless of visible-range performance.

---

## Grammar Constraint

`test_model.py` body of `f(n)` may use only:
- `math.log`, `math.exp`, `math.sqrt`
- Arithmetic operators (`+`, `-`, `*`, `/`, `**`)
- Numeric literals
- The variable `n`

No imports of `numpy`, `scipy`, `sympy`, or any other package. No named constants from external domains. No trigonometric functions. The fitter estimates numeric parameters; the mutator proposes functional structure.

---

## Grading Protocol

Gate grading is automated via `gate_harness.py`. All four gates must pass for the champion to be accepted. A model that passes only the visible gate but fails the holdout or farther-tail gates is not a champion.

Post-run, the operator reviews the champion's functional form for:
1. Whether the asymptotic behavior is structurally correct
2. Whether the derivation over n is mathematically coherent
3. Whether any external named result was smuggled in (criterion 7 cap applies)
