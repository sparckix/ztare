# OEIS A000959 (Lucky Numbers, 500K terms) — Public Claim Summary

> **What this file is.** The public-evidence surface for a sealed Lucky-
> number density-ratio recovery whose working directory is private.
> This summary is the canonical public artifact for the corresponding
> entry in
> [`docs/public_claim_register.md`](../../../docs/public_claim_register.md)
> under *Asymptotic-Law Sandbox Recoveries (Per-Substrate)* (A000959).

## One-line claim

Presented blind with the density ratio `L(n)/n` for OEIS A000959 (Lucky
numbers) over an expanded `n` range to 500K terms, the engine
identified the logarithmic-leading structure
`a + b · log(n) + c/(n+d) + e · (log(n))^2` with all eight visible-window
gates clearing. The structure is consistent with the conjectured
Prime-Number-Theorem analog for lucky numbers. Apparatus-internal
champion score: **77 / 100**.

## What was tested

The mutator was given the density-ratio observable `L(n)/n` over a
significantly larger `n` range than the original A000959 run, with the
hypothesis that finite-size corrections would resolve cleanly under
more evidence. The pre-committed form is logarithmic-leading with
inverse-power and squared-log corrections — no fixed coefficient values
were seeded.

## Recovered structure

The fit converged on the structural form (with numerically determined
parameters):

```
L(n)/n ≈ a + b · log(n) + c / (n + d) + e · (log(n))^2
```

The logarithmic leading term `b · log(n)` is the central structural
feature; the inverse-power and squared-log terms are sub-leading
corrections.

## Gate verdicts

- Champion score: **77 / 100** (apparatus-internal).
- The logarithmic leading structure passes the gates; finer numerical
  closure on `b` against the conjectured Prime-Number-Theorem-analog
  coefficient is sensitive to the gate's residual threshold and the
  finite-`n` extrapolation envelope.

## Honest framing — partial, not closed

This is a **partial recovery**: the structural topology is identified
and the gates clear at score 77, but the run did not achieve a
clean machine-precision closure. The conjectured constant `b` is
consistent with a Prime-Number-Theorem analog for lucky numbers but
this project alone does not pin it.

Related variants exist as separate sealed sandboxes:
`projects/oeis_a000959/` (the original lower-`n` run, score 29 —
incomplete) and `projects/oeis_a000959_newton/` (a Newton-step
validation attempt that returned a *negative result* at score 12 —
the Newton-step claim was falsified there). The 500K variant here is
the strongest of the three; it does not by itself convert the
Lucky-number conjectured constant into a closed apparatus result.

## Retest tag and caveat

*Enlarged-data confirmed* relative to the earlier
`projects/oeis_a000959/` run (score 29 → 77) — the larger `n` range
improved the structural identification. *Original-run only (n=1)* at
this scale; the result has not been re-executed under the current
apparatus version. A finer recovery would require either an even
larger `n` range, a relative-residual gate, or a cross-tool baseline
under matched conditions.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Asymptotic-Law Sandbox Recoveries (Per-Substrate)* (A000959
  bullet).
- Working directory (private): `projects/oeis_a000959_500k/`.
- Related public summaries:
  [`projects/oeis_a000959/public/CLAIM_SUMMARY.md`](../../oeis_a000959/public/CLAIM_SUMMARY.md)
  (earlier, lower-`n` variant — incomplete),
  [`projects/oeis_a000959_newton/public/CLAIM_SUMMARY.md`](../../oeis_a000959_newton/public/CLAIM_SUMMARY.md)
  (Newton-step variant — negative result).
- Next falsifier: re-run under a relative-residual gate to test
  whether the absolute-residual conservativeness at large `n` is what
  caps the score; or extend further to `n = 5M` and re-evaluate.
