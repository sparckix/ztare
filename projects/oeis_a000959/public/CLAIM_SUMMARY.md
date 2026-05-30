# OEIS A000959 (Lucky Numbers, Base Run) — Public Claim Summary

> **What this file is.** The public-evidence surface for the original
> lower-`n` Lucky-number recovery whose working directory is private.
> This summary records the project's actual sealed state — **incomplete
> at apparatus-internal score 29 / 100** — not a synthesized paper claim.

## One-line claim

Presented blind with the density ratio `L(n)/n` for OEIS A000959 (Lucky
numbers) over a moderate `n` range, the engine identified the
logarithmic-leading structure `a + b · log(n) + c/n + d/n²` but did not
converge to a clean gate-passing closure at this scale; the original
run is best read as a **partial-structure identification, not a
closed recovery**. Apparatus-internal champion score: **29 / 100**.

## What was tested

The mutator was given the density ratio under cold variable names with
the pre-committed fit form
`a + b · log(n) + c/n + d/n²`. No coefficients were seeded.

## Result

The structural topology (log-leading with inverse-power corrections)
was identified; the apparatus-internal gates did not clear at the
required margin. The result is preserved as an early-state sealed
sandbox.

## Honest framing

This run is **not the primary Lucky-number evidence in the public
record**. The stronger sealed result on this substrate is
`projects/oeis_a000959_500k/`, where the larger `n` range improved the
recovery to score 77. A Newton-step variant
(`projects/oeis_a000959_newton/`) returned a *negative result* at
score 12.

The earlier synthesizing paper framing of these three variants as a
single clean recovery was retired; the public record is the
per-variant sealed sandbox state, of which *this is the weakest*.

## Retest tag

*Original-run only (n=1); apparatus-internal score 29 — partial
structure identification, not a closed gate-passing result.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Asymptotic-Law Sandbox Recoveries (Per-Substrate)* (A000959
  bullet — the family entry).
- Working directory (private): `projects/oeis_a000959/`.
- Stronger variant:
  [`projects/oeis_a000959_500k/public/CLAIM_SUMMARY.md`](../../oeis_a000959_500k/public/CLAIM_SUMMARY.md).
- Negative-result variant:
  [`projects/oeis_a000959_newton/public/CLAIM_SUMMARY.md`](../../oeis_a000959_newton/public/CLAIM_SUMMARY.md).
