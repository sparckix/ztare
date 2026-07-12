# Bayesian screening — a positive result is governed by the base rate, not the test's accuracy

Opens a new domain for the library: **probabilistic decision logic** — the reasoning institutions run on when
they act on a noisy test. A screening or classification test (a diagnostic assay, a fraud flag, a criminal-risk
score, an automated content classifier) is applied to a population, and a decision is taken on a positive result.
The consequential question is never the test's accuracy in isolation but what a positive *means*: the probability
that a flagged case truly has the condition — the positive predictive value — which the base rate governs and the
advertised accuracy does not. Conflating the two — reading a 99%-accurate test's positive as 99% likely true — is
the base-rate fallacy in medicine and the prosecutor's fallacy in court, and it decides who is screened, detained,
or denied. This is the library's first result over a Bayesian base-rate structure rather than an algebraic
invariant, and it is a mechanism institutions run on, contested the way a covenant is: the numbers are agreed, the
interpretation is fought. It is a theorem EconCSLib and the finance-pricing libraries do not hold.

Assumption-accounting note: the results depend on (1) **rate ranges** — prevalence `π` strictly between 0 and 1,
sensitivity `se` and specificity `sp` in `(0,1]`; (2) the **positive-result mass is positive**, so the predictive
value is well-defined (guaranteed by `π > 0` and `se > 0`) — this is the load-bearing well-definedness hypothesis;
(3) **imperfect specificity** `sp < 1` for the base-rate-dominance result — a perfectly specific test has no false
positives and the fallacy cannot bite, so dropping it is exactly how the interesting case is lost. Surface where
each is used. Keep the rates over an ordered field of real-valued quantities; do **not** collapse to a fixed
decidable integer or rational instance, and keep the more-likely-than-not gate **cross-multiplied**
(`se·π ≥ (1−sp)·(1−π)`) so there is no division and no nonzero-denominator side condition on the comparisons — the
predictive-value ratio appears only where a numeric value is itself compared. A non-closure is an honest gap,
never a fake closure.

## Domain
formalization-nonmath

## Theory file
bayesian_screening_theory.lean

## Vocabulary (build these as definitions — do not prove them)
- **Screening**: a prevalence `π`, a sensitivity `se`, and a specificity `sp`, with `0 < π < 1`, `0 < se ≤ 1`, and
  `0 < sp ≤ 1`.
- **truePositiveMass**: `se · π` — the population fraction that both has the condition and tests positive.
- **falsePositiveMass**: `(1 − sp) · (1 − π)` — the fraction that lacks the condition yet tests positive.
- **positiveMass**: `truePositiveMass + falsePositiveMass` — the fraction testing positive.
- **PositivePredictiveValue**: `truePositiveMass / positiveMass` — the probability a positive case truly has the
  condition (the posterior probability of the condition given a positive result), well-defined when
  `positiveMass > 0`.

## Target
Consider a screening test — a sensitivity and a specificity in `(0,1]` — applied to a population with prevalence
`π` in `(0,1)`, and a decision taken on a positive result. The claim is that the meaning of a positive result is
governed by the base rate. First, a positive result is more likely a true positive than a false one — the positive
predictive value is at least one half — exactly when the true-positive mass meets the false-positive mass,
`se · π ≥ (1 − sp) · (1 − π)`: a sharp threshold set by the test's error rates and the prevalence, not by its
accuracy. Second, the base rate is load-bearing, not cosmetic: for any test with imperfect specificity — however
sensitive, even with perfect sensitivity `se = 1` — there is a low enough prevalence at which the predictive value
falls below one half, so most positives are false and a positive does not make the condition more likely than not.
Surface that the conclusion uses the rate ranges and imperfect specificity, and that the base rate is the missing
premise whose omission is the base-rate fallacy.

## Lemmas
- The predictive value clears one half exactly at the true-versus-false-positive-mass threshold: the positive
  predictive value is at least one half if and only if `se · π ≥ (1 − sp) · (1 − π)`. The sharp, division-free
  base-rate threshold.
- The predictive value is monotone in the base rate: raising the prevalence, holding sensitivity and specificity
  fixed, weakly raises the true-positive share of positives — a higher base rate can only make a positive more
  trustworthy.
- The predictive value is monotone in specificity: raising the specificity, holding prevalence and sensitivity
  fixed, weakly raises the predictive value — fewer false positives can only help.
- Base-rate dominance witness: for a test with imperfect specificity `sp < 1`, there is a prevalence `π` in `(0,1)`
  — even with perfect sensitivity `se = 1` — at which the true-positive mass is strictly below the false-positive
  mass, so the predictive value is strictly below one half.

## Idea
Everything is arithmetic over an ordered field. Keep the "at least one half" comparison in its cross-multiplied
form `truePositiveMass ≥ falsePositiveMass`, i.e. `se·π ≥ (1−sp)·(1−π)`, so no division and no positivity-of-
denominator side condition is needed and the threshold stays exact; the predictive-value ratio itself is only
touched when a numeric value is compared, and there the positive-mass hypothesis (`π>0`, `se>0`) discharges the
denominator. The threshold lemma is unfolding the definitions plus one `nlinarith`/`linarith` using
`positiveMass > 0`. Monotonicity in prevalence and in specificity are one `nlinarith` each on the cross-multiplied
predictive-value comparison (`TP₂·pos₁ ≥ TP₁·pos₂` with both positive masses positive). The base-rate-dominance
witness wants an explicit instance: with `se = 1`, `sp = 1/2`, and `π = 1/10`, the true-positive mass `1/10` is
below the false-positive mass `(1/2)·(9/10) = 9/20`, so the predictive value is below one half — state it generally
in the error rates where the theorem is general and instantiate only the witness. Keep `se`, `sp`, `π` as
parameters, carry `0 < π < 1` and the rate ranges as hypotheses, and do not fix a decidable carrier or drop the
imperfect-specificity assumption that makes the fallacy real.
