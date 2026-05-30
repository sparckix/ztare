# GP-023 Crucial 01 — Public Claim Summary

> Public-evidence surface for a sealed multi-variable structural-discovery
> calibration. Working directory private; cited by
> `docs/public_claim_register.md` under *Sealed Apparatus Calibrations
> and Curve-Fit Sandboxes*.

## Claim

Under cold variable names, the apparatus identified the structural
invariant `x1_peak / x2 ≈ 3.0` (the peak of `z` in the `x1` direction
scales **linearly** with `x2`, not as `x2²` as initially assumed). The
retired axiom — "`x1_peak ~ x2²` as a structural truth" — was demoted
when direct analysis of the grounding data showed `x1_peak ≈ 1.5` at
`x2 = 0.5` and `x1_peak ≈ 3.0` at `x2 = 1.0`. The retirement is
recorded next to the original claim. Apparatus-internal champion
score: **97 / 100**.

## What this calibrates

The result is a *judge-correctly-demoted-then-recovered* instance on a
multi-variable target: the apparatus's prior structural assumption was
mathematically false on the data, the judge layer caught it, the axiom
was retired explicitly, and the corrected structural invariant
(`x1_peak / x2` constant) was sealed. The cap at 97 reflects a small
amount of residual structural ambiguity in the rate-of-decay term —
the leading invariant is sealed; the secondary decay structure has a
named uncertainty that the next iteration would tighten.

## Retest tag

*Original-run only (n=1); apparatus-discipline calibration.* The
retired-axiom + recovered-invariant pattern is the reusable artifact.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp023_crucial_01`).
- Working directory (private): `projects/gp023_crucial_01/`.
- Sibling calibrations:
  [`projects/gp023_crucial_02/public/CLAIM_SUMMARY.md`](../../gp023_crucial_02/public/CLAIM_SUMMARY.md)
  and
  [`projects/gp023_crucial_03/public/CLAIM_SUMMARY.md`](../../gp023_crucial_03/public/CLAIM_SUMMARY.md).
