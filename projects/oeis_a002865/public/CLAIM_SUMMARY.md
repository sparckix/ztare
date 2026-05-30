# OEIS A002865 (Hardy-Ramanujan Derivative, Direct Run) — Public Claim Summary (Partial)

> **What this file is.** The public-evidence surface for a sealed
> direct-run investigation of OEIS A002865 (partitions of `n` into
> parts greater than 1). The working directory is private. This summary
> records a **partial recovery** that did not converge to a clean
> result under this protocol. **Distinct from the cleaner
> dynamic-programming recovery in
> `projects/gp077_a002865_01/`** — do not conflate the two.

## One-line claim

Presented blind with A002865 under cold variable names, the engine
identified the structural shape `z(n) ≈ a · √n + b · log n + c` —
locally almost linear in `√n` — but did not converge to a clean
gate-passing closure at this scale. Apparatus-internal champion score:
**54 / 100**.

## What was tested

The mutator was given evidence rows on `n ∈ [10, 2000]` for a strictly
monotone sequence growing faster than logarithmic but slower than any
positive power of `n`. The framework distinguishes a `√n + log n`
candidate from a single-correction rival (`√n` alone, `log^d` alone,
or `log · log log`), with the constraint that any sub-log or super-log
correction must be **explicitly** distinguished against its proper
rival.

## Result — partial

The `√n + log n + c` form is identified as the strongest candidate
under the gate battery; final parameters did not finalize cleanly and
the score capped at 54.

## Honest framing — partial, and not the canonical A002865 result

The canonical sealed A002865 result is the
**`gp077_a002865_01`** run (apparatus-internal score 96), which retired
the empirical-asymptotic-fitting axiom and enforced the analytic
Hardy-Ramanujan-Rademacher k=1 constants
(`K = π√(2/3)`, `M = 1/(2π√2)`) as rigid. This project (`oeis_a002865`)
is a **separate, weaker run** using direct empirical fitting on the
same sequence; it is preserved as the discipline-baseline against
which the gp077 run's stronger framework was promoted.

The contrast between these two runs is the discipline lesson — fitting
the analytic envelope empirically caps at score 54; enforcing the
analytic constants reaches score 96. Both are sealed and on the public
record.

## Retest tag

*Original-run only (n=1); partial recovery under empirical-fitting
framework; superseded as the canonical A002865 result by
`gp077_a002865_01`.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Asymptotic-Law Sandbox Recoveries (Per-Substrate)*
  (A002865 bullet — alongside the canonical `gp077_a002865_01`).
- Working directory (private): `projects/oeis_a002865/`.
- Canonical A002865 result:
  [`projects/gp077_a002865_01/public/CLAIM_SUMMARY.md`](../../gp077_a002865_01/public/CLAIM_SUMMARY.md).
