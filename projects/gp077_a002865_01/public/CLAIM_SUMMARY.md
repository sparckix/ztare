# GP-077 A002865 (Partitions Without 1s) — Public Claim Summary

> **What this file is.** The public-evidence surface for a sealed
> sandbox whose full working directory is private. This summary is the
> canonical public artifact for the corresponding entry in
> [`docs/public_claim_register.md`](../../../docs/public_claim_register.md)
> under *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
> (`gp077_a002865_01`) and *Experimental Mathematics and Asymptotic
> Recoveries* (A002865 secondary).

## One-line claim

Presented with the OEIS A002865 sequence (number of partitions of `n` into
parts greater than 1, equivalently `p(n) − p(n−1)`) under cold variable
names, the engine retired the "algebraic asymptotic fitting" axiom and
converged on the **exact analytic Hardy-Ramanujan-Rademacher k=1
envelope** with constants `K = π√(2/3)` and `M = 1/(2π√2)` enforced as
rigid (not free-fitted), combined with discrete combinatorial recurrence
`p(n) − p(n−1)` for exact integer evaluation. Apparatus-internal
champion score: **96 / 100**.

## What was tested

The mutator was given evidence rows for a monotonic positive-integer
sequence with no domain labels. An early iteration attempted to *fit* the
leading exponential constant `A` against finite data. The judge demanded
derivation rather than empirical fit; the mutator regressed briefly to a
weaker over-claim (score 57 on the prior champion); the judge held; the
mutator then retired the empirical-fitting axiom and re-derived the
envelope with the exact analytic constants enforced. The final form is
asymptotically dominated by the `k=1` Hardy-Ramanujan-Rademacher term;
exact integer values are produced by the `p(n) − p(n−1)` recurrence.

## Recovered form (envelope + exact recurrence)

- Continuous leading envelope (k=1 Rademacher):
  `a(n) ~ M · n^{−5/4} · exp(K · √n)`  with
  `K = π√(2/3) ≈ 2.56509966`,
  `M = 1/(2π√2) ≈ 0.11253954`.
- Exact integer values: `a(n) = p(n) − p(n−1)` via combinatorial
  recurrence.

The leading constants are *not* fitted; they are enforced as the
analytic-number-theory result required by the Hardy-Ramanujan-Rademacher
expansion.

## Gate verdicts and residual structure

- Champion score: **96 / 100** (apparatus-internal).
- Retired axiom (judge-approved): "Algebraic Asymptotic Fitting" — the
  assumption that finite-window empirical fitting could replace the
  analytic asymptotic constants.
- Derived constraint (judge-introduced and held): no empirical fitting
  of the leading analytic envelope is permitted; analytic constants must
  be enforced.
- Residual structure: sub-exponential oscillations bounded by
  `O(exp(−(π/(2√6))·√n))` per the k ≥ 2 Rademacher tail.
- Score deduction (the four points to 100): no closed-form elementary
  expression for the infinite sum of k ≥ 2 Rademacher corrections —
  the residual is rigorously bounded but not algebraically distilled.

## Honest framing — what this is, and what it is not

This is the canonical **INS-015** instance — *judge correctly demoted
the over-claim, mutator regressed, judge held, mutator re-derived under
the corrected axiom*. The apparatus-discipline behavior is the reusable
artifact; the form itself is the analytic-number-theory result already
known to mathematics.

It is *not* a discovery of a new asymptotic for A002865. It is *not* a
closed-form elementary expression for the full Rademacher series. The
public-claim contribution is **the gate-verified retirement of empirical
asymptotic fitting under cold variable names** plus the exact integer
recovery via combinatorial recurrence.

## Retest tag and caveat

*Original-run only (n=1).* The apparatus-discipline pattern
(judge-demotion-then-recovery) is the canonical INS-015 reference and is
the reusable artifact here; the underlying mathematics was already known
when the engine was pointed at the substrate.

A separate apparatus run on the same OEIS sequence (`projects/oeis_a002865/`,
score 54) used a different methodology — fractional log-polynomial
fitting framework. Its parameters were never finalized and its claim
status is *incomplete*; do not confuse it with this `gp077_a002865_01`
result.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`, under
  *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp077_a002865_01`) and as the secondary calibration in the A002865
  bullet of the *Experimental Mathematics* section.
- Working directory (private): `projects/gp077_a002865_01/`.
- Related: the parallel `projects/oeis_a002865/` run (incomplete, and
  distinct from this one — do not confuse). The earlier synthesizing
  paper framing on these OEIS recoveries was retired; the public
  record is now per-substrate sandbox summaries like this one, not a
  unified paper claim.
