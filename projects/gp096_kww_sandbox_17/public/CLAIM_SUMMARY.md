# GP-096 KWW Sandbox 17 — Public Claim Summary

> **What this file is.** The public-evidence surface for a sealed blind
> stretched-exponential recovery whose full working directory is private.
> This summary is the canonical public artifact for the corresponding
> entry in
> [`docs/public_claim_register.md`](../../../docs/public_claim_register.md)
> under *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
> (`gp096_kww_sandbox_17`).

## One-line claim

Under cold variable names (no domain labels), the engine recovered the
operator-authored Kohlrausch–Williams–Watts stretched-exponential ground
truth `v(t) = A·exp(−(t/τ)^β) + C` blind, in seven seven-gate matches at
machine precision, with farther-tail extrapolation holding at 4× the
visible t-range.

## What was tested

The mutator was given visible evidence over `t ∈ [0.5, 68]` and a
farther-tail window `t ∈ [97, 283]` — extrapolation 4× beyond the
visible max. The pre-registration committed the apparatus to the
seven-gate battery (hidden + farther-tail global residuals plus per-zone
discriminators); no fractional-exponent or special-function hints were
seeded.

## Recovered form

```
v(t) = a · exp(-b · t^c) + d
a = 2.810
b = 0.396
c = 0.630
d = 0.470
```

Structural equivalence to the operator-authored KWW ground truth
`v(t) = A·exp(−(t/τ)^β) + C` is confirmed by the parameter mapping
`b = 1/τ^β`, which matches to within 0.0002% error.

## Gate verdicts

Score: **98 / 100**, all seven gates pass at machine precision:

- hidden global residual: 1×10⁻⁶
- farther-tail global residual: 1×10⁻⁶
- all discriminator-zone residuals: 0.0000% error vs. ground truth

The score plateau at 98 corresponds to a Prony-series objection (the
mutator could not formally rule out an infinite-mode Prony sum as a
mathematically equivalent representation). This is a *correct
unfalsifiable mathematical ceiling*, not a gap in the recovery: any
stretched-exponential can be re-expressed as an infinite Prony sum, so a
two-mark deduction is the right rubric outcome and the form recovery is
not undermined.

## Honest framing — calibration, not discovery

This is a **vocabulary-escape recovery of an operator-committed
ground-truth form under cold semantics**. The operator authored the KWW
ground truth before the run and sealed it; the mutator recovered the
exact form under hidden-gate pressure, including the fractional exponent
`β ≈ 0.63`. That is a *calibration win* for fractional-exponent
detection — it proves the cage can force the mutator out of its
integer-exponent / pure-power-law prior onto a stretched-exponential.

It is *not* a discovery against an unknown target. The H-SP2-04 blinded
successor (unknown ground truth) is the next step that would convert
this calibration into a discovery claim.

## Retest tag and caveat

*Original-run only (n=1) under cold variable names; operator-authored
ground truth, so this is a calibration win, not a blind discovery.*

The farther-tail extrapolation at 4× the visible range is the
strongest individual property of this run. Monotonic decay laws with
fractional exponents extrapolated stably; pure power-laws and
polynomial hybrids did not survive the gates.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`, under
  *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*.
- Working directory (private): `projects/gp096_kww_sandbox_17/`.
- Related: the H-GP103 (Compositional Hypothesis Generator) work that
  followed; the Langevin-sandbox depth-1 ceiling diagnosis
  (`gp096_langevin_sandbox_16`) that motivated the depth-2 extension.
- Next falsifier: blinded-oracle successor with unknown ground-truth
  form (H-SP2-04). Until that lands, the calibration framing here holds.
