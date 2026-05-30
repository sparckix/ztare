# GP-023 Crucial 02 — Public Claim Summary

> Public-evidence surface for the topological-pivot follow-up to
> `gp023_crucial_01`. Working directory private; cited by
> `docs/public_claim_register.md` under *Sealed Apparatus Calibrations
> and Curve-Fit Sandboxes*.

## Claim

The structural invariants identified in `gp023_crucial_01`
(`x1_peak / x2` constant; `x2³` amplitude scaling — both initially
hardcoded) are converted into **free parameters** so the model
derives them from data rather than assuming them. The pivot adds two
named structural terms: a power-law growth `x1^P_growth_exponent` and
an exponential-decay term `exp(−K · (x1/x2)^P_decay_exponent)`,
keeping `x1/x2` as the central ratio. Apparatus-internal
champion score: **88 / 100**.

## What this calibrates

The follow-up *tests whether the structural invariants discovered
under fixed-constant exploration survive when those constants are
freed*. The pivot demotes a brittle pre-commit (`peak ratio ≈ 3` and
`x2³` amplitude) into named free parameters; the score drop from 97
to 88 reflects the parameter-identifiability cost of generalising,
not a falsification.

## Retest tag

*Original-run only (n=1); successor calibration to
`gp023_crucial_01` testing parameter-freedom robustness.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp023_crucial_02`).
- Working directory (private): `projects/gp023_crucial_02/`.
- Parent calibration:
  [`projects/gp023_crucial_01/public/CLAIM_SUMMARY.md`](../../gp023_crucial_01/public/CLAIM_SUMMARY.md).
- Cross-grammar sibling:
  [`projects/gp023_crucial_03/public/CLAIM_SUMMARY.md`](../../gp023_crucial_03/public/CLAIM_SUMMARY.md).
