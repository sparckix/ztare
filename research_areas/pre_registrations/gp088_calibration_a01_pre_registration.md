# Pre-Registration — GP-088 Calibration A01 (Division A, SEALED)

**Status**: Division A sealed artifact. Division B agents must not read this file.
**Date**: 2026-04-20
**Protocol**: GP-072 M-form information isolation

---

## 1. Ground Truth System

### Observable and Law

```
v(n) = log(p(n))
```

where `p(n)` is the integer partition function — the number of additive decompositions of `n`.

**System class**: Log of number-theoretic counting function; sub-linear monotone increasing over positive integer index.

### Hardy-Ramanujan Asymptotic Formula (pre-registered comparator)

```
v(n) ≈ π·√(2n/3) − log(4n·√3)
```

In Python (using math_exp_only grammar):

```python
import math
def hr(n):
    return math.pi * math.sqrt(2 * n / 3) - math.log(4 * n * math.sqrt(3))
```

This is the theoretically derived asymptotic expression; the GT observable is the exact `log(p(n))` from the DP recurrence.

### Exact GT Generation

```python
# DP recurrence for p(n)
dp = [0] * (max_n + 1); dp[0] = 1
for k in range(1, max_n + 1):
    for j in range(k, max_n + 1):
        dp[j] += dp[j - k]
v(n) = math.log(dp[n])
```

---

## 2. Evidence Plan

| File | n range | v range | Visibility |
|------|---------|---------|------------|
| `evidence.txt` | 5–34 | [1.946, 9.418] | Division B visible |
| `evidence_holdout.txt` | 35–54 | [9.608, 14.024] | Hidden (Division A only) |
| `evidence_farther_tail.txt` | 55–74 | [14.191, 18.326] | Hidden (Division A only) |

---

## 3. Feasibility Assessment (Phase 0.2)

**Can the GT class produce evidence uninformative about the GT class?**

Partially. The observable is a smooth sub-linear monotone curve over integer n — consistent with many functional forms (e.g., a·√n, a·n^b, a·log(n) + b·√n). The dominant `√n` scaling is recoverable from ratio analysis of the visible slice without knowing the partition-function origin. The `log(n)` correction term is visible as a slight below-√n bend but does not uniquely fingerprint the partition function. Verdict: **PASS** — domain retrieval from curve shape alone is implausible.

**Known leak risk**: The denylist blocks "partition", "Hardy", "Ramanujan", "A000041", "p(n)", "sqrt(2n/3)", "log(p", "integer partition", "number of ways". An LLM that has memorized the H-R formula may independently write `math.sqrt(2*n/3)` in a fit_declaration without triggering the string-level sentinel (the sentinel blocks "sqrt(2n/3)" but not the Python expression `math.sqrt(2 * n / 3)`). This is a Layer-b coverage gap, acknowledged as permanent architectural constraint (GP-072 §1.6). The math_exp_only grammar combined with the DP recurrence is the only available mitigation.

---

## 4. Identifiability Check (Phase 0.3)

The H-R formula has two effective parameters after fixing π and √(2/3):

```
v(n) ≈ A·√n + B·log(n) + C
```

where A = π·√(2/3) ≈ 2.565, B = −1, C = −log(4·√3) ≈ −1.985.

Under the fit primitive (GP-035), the fitter will optimize A, B, C freely — these are non-degenerate over n ∈ [5, 34]. No rank collapse. **PASS**.

---

## 5. Gate Thresholds (Division A rationale)

**Key calibration finding**: the theoretical H-R formula uses fixed constants (π, √(2/3), √3) and FAILS the holdout gates at n=35..54 (max error 0.076 vs gate 0.05). The fit primitive optimizes coefficients A, B, C over the visible range (n=5..34), which substantially improves holdout generalization.

| Configuration | Holdout max (gate 0.05) | Holdout upper max (gate 0.04) | FT max (gate 0.08) | FT upper max (gate 0.06) |
|---|---|---|---|---|
| H-R theoretical | **0.076 FAIL** | **0.067 FAIL** | 0.061 ✅ | 0.055 ✅ |
| H-R structure, optimized A,B,C | 0.021 ✅ | 0.021 ✅ | 0.042 ✅ | 0.042 ✅ |

**What the engine must do**: propose the correct structural form `A·√n + B·log(n) + C` (or equivalent); the fit primitive then finds A≈2.51, B≈−0.83, C≈−2.30 which pass all 4 gates.

**Expected outcome for a correct structural recovery**: all 4 gates pass, score 98.

---

## 6. Rubric Compliance Check

| Flag | Value | Rationale |
|------|-------|-----------|
| `enable_component_c` | `false` | Discovery mode — Component C is calibration-mode accelerator only (GP-075 §56) |
| `enable_fit_primitive` | `true` | Correct — H-R is a closed-form expression in math_exp_only grammar |
| `holdout_hard_gate` | `true` | Correct — holdout is the primary falsification surface |
| `farther_tail_contract` | `true` | Correct — farther-tail gate must bind |
| `asymptotic_claim` | `false` | Safe: farther_tail_contract=true makes GP-046 downgrade inert |
| `fit_expression_grammar` | `math_exp_only` | H-R uses math.sqrt, math.log, math.pi, arithmetic only |
| `gp103_stagnation_threshold` | `1` | Aggressive but acceptable; H-R is single-regime so composites are not needed, but early firing does not harm |

---

## 7. Division A / Division B Boundary Attestation

Division A artifacts (sealed, never shown to mutator):
- `raw/gt_partition.py` — GT generation script
- `evidence_holdout.txt` — holdout evidence (n=35–54)
- `evidence_farther_tail.txt` — farther-tail evidence (n=55–74)
- `.denylist` — GT vocabulary list
- This pre-registration document

Division B artifacts (mutator-visible):
- `evidence.txt` — visible evidence (n=5–34)
- `project_charter.md` — neutral problem description
- `thesis.md` — thesis seed (no GT vocabulary)
- `test_model.py` — stub baseline
- `gate_harness.py` — frozen harness (reads holdout/farther-tail, does not expose GT values)
- `rubrics/gp088_calibration_a01.json` — rubric

Sentinel gate run required before sealing (Phase 4 — `make seal`).
