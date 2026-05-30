# GP-096 Langevin Sandbox 16 — Depth-1 Composition Ceiling — Public Claim Summary

> Public-evidence surface for the depth-1 composition-ceiling
> diagnosis. Working directory private; cited by
> `docs/public_claim_register.md` under *Sealed Apparatus Calibrations
> and Curve-Fit Sandboxes*.

## Claim

Presented with Langevin-function data `v(u) = A · (coth(B·u) − 1/(B·u)) + C`
under cold variable names, the apparatus's depth-1 composition layer
produced a near-miss champion `v(u) = a − b/(u + c · log(1 + d · exp(−e·u)))`
at apparatus-internal score **75 / 100**. The retired axiom — "Strict
Exclusivity of Polynomial Tail" — was demoted because over the
observed finite window `u ∈ [0.3, 32]`, both slow-exponential and
inverse-polynomial tails produce the same boundary marginal
increment (~0.006 at `u ≈ 32`), so a *uniqueness* claim cannot be
made without deeper asymptotic evidence. The Langevin form requires
a **depth-2 composition** (ratio of sums inside a transcendental
function) that the depth-1 search space cannot express.

## What this catalogues — depth-1 composition ceiling diagnosis

This is the canonical **depth-1 ceiling** diagnosis: the apparatus
did not fail to find the right form; it *correctly identified that
depth-1 cannot express it*. The retreat to a non-Langevin softplus
approximation is the apparatus's honest report that within its
composition depth, the true form is unreachable. Motivated the
H-GP103 compositional-hypothesis-generator extension (depth-2
templates with explicit ratio probes).

## Retest tag

*Diagnostic finding (no recovery to retest).* The depth-1 ceiling
*is* the durable artifact. The same target under a depth-2 grammar
(H-GP103) would be the falsifier — if depth-2 also caps below the
Langevin form, the diagnosis would need extending.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp096_langevin_sandbox_16`).
- Working directory (private): `projects/gp096_langevin_sandbox_16/`.
- Related: the KWW stretched-exponential recovery
  ([`projects/gp096_kww_sandbox_17/public/CLAIM_SUMMARY.md`](../../gp096_kww_sandbox_17/public/CLAIM_SUMMARY.md))
  is the *successful* depth-1 sibling on a different fractional-
  exponent target.
