# Probability — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of probabilistic decision logic — the reasoning institutions run
on when they act on a noisy signal — produced end-to-end by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints (through the
faithfulness firewall; each proof independently kernel-ratified with an axiom audit). Every file is self-contained
(`import Mathlib`) and carries a GENERATED provenance header emitted by `promote_campaign_artifact.py` — not
hand-authored. The rates are kept over an ordered field and the gates cross-multiplied, so the results are exact
and carry no measure-theoretic machinery.

## Contents

### `BayesianScreeningPredictiveValue.lean` — a positive result is governed by the base rate, not the test's accuracy
`base_rate_governs_positive_predictive_value`. A screening or classification test — sensitivity `se`, specificity
`sp` — applied to a population with prevalence `π`, and a decision taken on a positive result. What a positive
*means* is the positive predictive value: the probability a flagged case truly has the condition. The theorem has
two parts. First, a positive is more likely a true positive than a false one — the predictive value is at least one
half — **exactly** when the true-positive mass meets the false-positive mass, `se·π ≥ (1−sp)·(1−π)`: a sharp
threshold set by the error rates and the prevalence, not by the test's advertised accuracy. Second, the base rate
is load-bearing: for any test with imperfect specificity, **even with perfect sensitivity `se = 1`**, there is a
low enough prevalence at which the predictive value falls below one half — most positives are false. Reading a
highly accurate test's positive as likely-true, dropping the prevalence, is the base-rate fallacy in medicine and
the prosecutor's fallacy in court. Axiom-clean `[propext, Classical.choice, Quot.sound]`.

### Definitions

The vocabulary the theorem is stated over — read them to check the faithfulness boundary; each is documented at
the top of the file.

- `RateOpenUnit x := 0 < x ∧ x < 1` — a strict probability rate (used for the prevalence).
- `RatePositiveUnit x := 0 < x ∧ x ≤ 1` — a positive rate that may be perfect (sensitivity, specificity).
- `truePositiveMass se π := se · π` — the fraction that has the condition and tests positive.
- `falsePositiveMass sp π := (1 − sp) · (1 − π)` — the fraction without the condition that still tests positive.
- `positiveMass se sp π := truePositiveMass se π + falsePositiveMass sp π` — the fraction testing positive.
- `PositivePredictiveValue se sp π := truePositiveMass se π / positiveMass se sp π` — the posterior probability a
  positive case truly has the condition (well-defined when the positive mass is positive).
