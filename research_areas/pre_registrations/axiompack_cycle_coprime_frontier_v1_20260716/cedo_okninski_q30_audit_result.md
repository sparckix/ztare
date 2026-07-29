# Cedó--Okniński Question-30 audit result

## Verdict

The 49-point construction is valid, but the decomposition question is already
resolved in the literature. This campaign branch is a recovery/calibration
result, not a frontier-novel theorem.

## Exact witness

For `X = (Z/7Z)^2`, use

`j = (1, 0, 6, 4, 4, 6, 0)`

and the cycle-set left translations

`L_(a,b)(u,v) = (4(u-b), 4v + j_(u-a)) mod 7`.

Every left translation has cycle profile `(1, 3, 3, 21, 21)`. In particular,

`(0,0) -> (0,1) -> (0,5) -> (0,0)`

is a 3-cycle of `L_(0,0)`, and `gcd(3, 49) = 1`. The deterministic audit also
checks the paper's YBE identity, the cycle-set identity, bijectivity,
bijectivity of the diagonal squaring map, left-action transitivity, and
displacement transitivity.

The Lean certificate
`ZtareProofs.AxiomPackCycleCoprimeCounterexample.question30CounterexampleCertificate`
compiled cleanly. It checks the finite operation directly and supplies a
uniform two-left-translation path between every ordered pair of carrier
points.

## Literature chronology

- Castelli records the Ramírez--Vendramin decomposition question and describes
  it as unresolved in the manuscript accepted on 2024-05-10.
- Cedó--Okniński's 2024 Theorem 4.2 supplies the singular simple construction
  from which the 49-point instance was reconstructed.
- Kanrar--Rump published a family of counterexamples in 2024.
- Bonatto--Castelli v3 (2026-05-07) explicitly records the Kanrar--Rump result
  and gives smaller simple counterexamples of size `p^p`; `p=3` gives size 27.

The exact 49-point connection may be unstated, but it has no priority as the
resolution of the question and is mathematically weaker than the later size-27
family.

## Apparatus lesson

The failed novelty classification came from temporal source coverage, not from
the finite solver or Lean encoding. An older primary source that labels a
question open must be treated as a dated anchor. A novelty audit must traverse
forward citations and inspect the latest revisions of directly relevant
papers before it can return an unmapped assessment.
