# GP-080 01 — Underdetermination Boundary, First Instance — Public Claim Summary

> Public-evidence surface for the canonical INS-018 instance of the
> *underdetermination boundary*. Working directory private; cited by
> `docs/public_claim_register.md` under *Sealed Apparatus Calibrations
> and Curve-Fit Sandboxes*.

## Claim

The two-state transition `z ∝ x₂ · (e^{−k₁ x₁} − e^{−k₂ x₁})` is the
*minimal-complexity structural form* that achieves exact zero-residual
fit within `x₁ ∈ [0.5, 24]` on the apparatus's holdout battery, while
explicitly **rejecting** the catastrophic assumption that exact finite
fit constitutes a global mathematical proof of uniqueness against
higher-order hybrids. The named discriminator is the *Tail Scaling
Asymptote* `R_{12,24} = z(24, x₂) / z(12, x₂)`: a pure inverse
power-law `z ∝ x₁^{−m}` predicts a constant scaling ratio over any
doubling of `x₁`; the dual-exponential thesis predicts that as the
fast transient `e^{−k₂ x₁}` decays, the terminal scaling ratio
transitions to an *absolute* exponential drop tied to `Δx₁`, breaking
scale-free invariance. Apparatus-internal champion score: **98 / 100**.

## What this calibrates — INS-018, the underdetermination boundary

A clean holdout pass is *not* sufficient evidence of structural
uniqueness. The judge layer independently named the
exponential-exclusion gap *without ground-truth access* at score 94
(see `gp080_02`); a post-close farther-tail evaluation confirmed a
structural-class mismatch with the true bi-exponential ground truth
(3754% error at `x₁ = 96`). This is the canonical instance for the
register's discipline: **the holdout hard-gate is not sufficient;
farther-tail discrimination is necessary to detect
underdetermination**.

## Retest tag

*Original-run only (n=1); the post-hoc farther-tail demotion is the
sealed underdetermination-boundary record.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp080_01`).
- Working directory (private): `projects/gp080_01/`.
- Sibling:
  [`projects/gp080_02/public/CLAIM_SUMMARY.md`](../../gp080_02/public/CLAIM_SUMMARY.md)
  — the algebraic-saturation rival that the judge promoted as the
  cleaner discriminator at score 94.
