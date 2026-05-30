# OEIS A000009 (Partitions Into Distinct Parts) — Public Claim Summary (Partial)

> **What this file is.** The public-evidence surface for a sealed
> investigation of OEIS A000009 (partitions of `n` into distinct
> parts). The working directory is private. This summary records a
> **partial structural identification** that did not converge to a
> closed apparatus result.

## One-line claim

Presented blind with A000009 under cold variable names, the engine
identified the structural shape — *super-logarithmic, sub-polynomial,
led by `√n` with a slow-varying fractional-log correction* — but did
not produce final parameters that pass the full gate battery.
Apparatus-internal champion score: **67 / 100**.

## What was tested

The mutator was given evidence rows on `n ∈ [10, 2000]` for a strictly
monotone, sub-linear sequence. The pre-committed framework: a leading
`√n` term plus a slow-varying additive correction of the form
`(log n)^γ` with `0 < γ < 1`, against a `√n + log n` rival.

## Result — partial

The structural framework converged on `f(n) = p₁ · √n + p₂ · (log n)^γ + p₃`
with γ in the fractional range (0 < γ < 1), differentiating it from
the integer-log rival. Final parameters were not finalized in the
current sealed state; the gates did not clear at the required margin.

## Honest framing

The Hardy-Ramanujan asymptotic for partitions into distinct parts is a
known result in analytic number theory; this project did not aim to
"discover" it. The aim was to test whether the apparatus could
*recover* a super-log / sub-polynomial structural shape from blind
data, and to distinguish it cleanly from the closest classical rival
under the gate battery. The structural identification succeeded; the
numerical closure did not.

This is therefore a **partial structural recovery** — not a closed
asymptotic claim, and not a discovery. Do not cite it as the
apparatus's clean A000009 result; cite it as the partial structural
identification it is.

## Retest tag

*Original-run only (n=1); structural framework identified but final
parameters not finalized.* A clean closure would require either an
extended `n` range, a relative-residual gate, or a finer
fractional-exponent grid.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Asymptotic-Law Sandbox Recoveries (Per-Substrate)*
  (A000009 bullet).
- Working directory (private): `projects/oeis_a000009/`.
- Related: the cleaner sealed Hardy-Ramanujan-Rademacher result is in
  [`projects/gp077_a002865_01/public/CLAIM_SUMMARY.md`](../../gp077_a002865_01/public/CLAIM_SUMMARY.md)
  (a different but adjacent partition sequence, A002865, recovered
  under enforced-analytic-constants discipline).
