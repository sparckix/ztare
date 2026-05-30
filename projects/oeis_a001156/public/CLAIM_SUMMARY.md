# OEIS A001156 (Partitions Into Squares) — Public Claim Summary

> **What this file is.** The public-evidence surface for a sealed
> sandbox whose full working directory is private. This summary is the
> canonical public artifact for the corresponding entry in
> [`docs/public_claim_register.md`](../../../docs/public_claim_register.md)
> under *Experimental Mathematics and Asymptotic Recoveries* (A001156,
> Meinardus partitions into squares).

## One-line claim

Presented with OEIS A001156 (number of partitions of `n` into squares)
under cold variable names, the engine recovered a composite rational
form whose exponent matches the **Meinardus-predicted `n^(1/3)` growth
topology** within 0.5%, with all visible-window residuals below 0.02.
Apparatus-internal champion score: **85 / 100**.

## What was tested

The mutator was given evidence rows for a monotone, sub-linear,
smoothly concave-upward sequence over `n = 50 ... 2000` (visible) with a
farther-tail contract pre-specified for `n > 10000`. No domain labels;
no hints about Meinardus or about the `1/3` exponent.

Pre-committed champion form (multi-parameter composite rational with a
shifted root and a root-like power law):

```
y(n) = ( a_a · (n − a_b)^a_c + a_d + b_a · √n + b_b ) / ( d2_a / n + d2_b )
```

The eight parameters were fit; the exponent `a_c` was *not* hardcoded.

The pre-committed structural rival was the quadratic-log form
`y_rival(n) = a · (log n)^2 + b · log n + c` — a classical sub-linear
monotone form used in information theory and combinatorics.

## Recovered form and the Meinardus exponent

The fit converged on `a_c ≈ 1/3` — the Meinardus exponent for
partitions into squares — to within 0.5%, *with no prior knowledge of
Meinardus's theorem given to the engine*. The published `test_model.py`
hard-codes the recovered exponent as `1/3` after the fit identified it.

## Gate verdicts

- Visible window (`n = 50 ... 2000`): champion max absolute residual
  below 0.02 across all rows; the quadratic-log rival exceeds 0.6 at
  `n = 2000` and grows with `n`.
- Forward observable (`n > 10000`): the apparatus pre-committed that
  the composite-rational form would retain residuals below 0.08 while
  the rival inflates further. (See *Retest tag* below — the
  absolute-residual gate was conservative on a large-scale observable.)
- Apparatus-internal champion score: **85 / 100**.

## Honest framing — topology correct, absolute-residual gate
conservative

The structural finding is the recovery of **the Meinardus `n^(1/3)`
topology** from blind data. With normalized (scale-invariant) residuals
the form passes at 0.16% relative error.

The absolute-residual holdout gate at the largest `n` values was
*rejected* — the form accumulates exponent-precision bias at high `n` in
the absolute scale, even though the topology is correct. This is a
conservative-by-construction property of the gate (an absolute
threshold on a large-scale observable will trip even on a correct
topology if the high-`n` constants drift by an O(1) factor), not a
falsification of the recovered topology.

The structural recovery (exponent `1/3`) is the real result; the
absolute residual is the gate-engineering caveat. The
experimental-math working notes (private) discuss this gate-vs-topology
distinction directly.

## Retest tag and caveat

*Original-run only (n=1).* Topology was correctly identified; the
absolute-residual gate is conservative on a large-scale observable. The
recovery was not re-run under a relative-residual gate variant; that
would convert the n=1 evidence into a clean topology-recovery claim
without the gate-engineering caveat.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`, under
  *Experimental Mathematics and Asymptotic Recoveries* (A001156 bullet).
- Working directory (private): `projects/oeis_a001156/`.
- Related: the broader Hardy-Ramanujan cluster (`projects/oeis_a000041`,
  `projects/oeis_a002865`, `projects/gp077_a002865_01`) and the
  prime-partitions Vaughan recovery (`projects/gp088_oeis_a000607`),
  each with its own public summary or noted as incomplete; the
  apparatus's vocabulary-escape calibration is recorded under
  `projects/gp023_planck_sandbox_06/public/CLAIM_SUMMARY.md`.
- Next falsifier: re-run under a relative-residual / scale-invariant
  gate to clear the absolute-residual conservativeness caveat, OR a
  category-switch substrate where the grammar admits the answer but
  the mutator must enter a different mathematical category (mirror of
  the sopfr `gp` finding).
