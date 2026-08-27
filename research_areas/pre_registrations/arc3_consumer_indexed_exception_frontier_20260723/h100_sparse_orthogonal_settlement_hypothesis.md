# H100: sparse orthogonal settlement removes the factorial contact wall

Date: 2026-08-04

Status: pre-registered, offline scaling test not yet run

## Correction to H98/H99

H98 and H99 require every offer/withhold assignment in the full factorial.
For residual rank `r`, that costs `2^r` shared trajectories. Positive
knowledge reproduction under that schedule does not define a scalable regime:
measurement contact grows exponentially with the number of independent
children. The reported multiplexing gain compares shared versus separately
repeated factorial trajectories, but does not remove the factorial wall.

## Eigenquestion

Can independent residual children be settled with an exact sparse orthogonal
intervention code whose trajectory count grows near-linearly in the number of
modeled response terms, while preserving causal first-stage identification,
authority, calibration, false-edge accounting, and primitive cost?

## Hypothesis

Each niche-local offer/withhold assignment is a signed factor. A complete
factorial estimates every possible interaction, although the residual compiler
usually asserts a sparse response model before outcome. If the pre-outcome
model contains `r` main effects and `s` named interactions, assign every niche
a nonzero Walsh character. Main effects and declared interactions are
identifiable when their character masks are nonzero and pairwise distinct.

The schedule compiler will search the smallest power-of-two row count `m` for
such a mask assignment. It will then emit the `m` Walsh rows. Exact character
orthogonality gives a full-rank design for the intercept plus every modeled
term. Additive settlement therefore needs

`m = 2^ceil(log2(r + 1))`

for the tested range when a collision-free mask assignment exists. Sparse
interactions may increase `m`, but the cost follows modeled term count rather
than the `2^r` complete-interaction lattice.

This is a compiled settlement authority, not an assumption hidden in the
analyzer. Interaction terms must be declared before outcomes. An unmodeled
interaction cannot receive a causal claim from this receipt.

## Discriminating offline test

1. For additive residual ranks `r = 2..12`, compile the minimum Walsh schedule
   and verify exact orthogonality and rank `r + 1` including the intercept.
2. Compare schedule rows with `2^r`; require strict savings for every `r >= 3`
   and increasing compression over the range.
3. Re-run H99's rank-three second generation with four Walsh trajectories
   rather than eight factorial trajectories. Require three promoted children,
   `R_k = 3/2`, `R_e = 0`, unchanged calibration, shared cost `80` rather than
   `160`, and no takeoff claim.
4. Declare one pairwise interaction before outcome; require a collision-free
   exact design and full modeled-term rank.

## Negative fixtures

- Repeated or zero factor masks are rejected.
- Main-effect and declared-interaction mask aliasing is rejected.
- A trial schedule omitting or repeating a compiled row is rejected.
- A trial whose niche assignment differs from the compiled row is rejected.
- A post-outcome interaction declaration changes schedule identity and cannot
  reuse earlier settlement evidence.
- A rank-deficient schedule cannot promote children even when marginal means
  appear positive.

## Success criterion

All additive schedules through rank twelve are exact and deterministic;
trajectory count follows the power-of-two envelope above `r+1`; the H99
rank-three settlement uses four trajectories and retains the same causal,
error, and calibration verdict; the declared-interaction fixture receives a
collision-free full-rank design; every negative fixture is rejected.

## Kill conditions

Kill the sparse-settlement route if exact main-effect identification requires
the complete factorial, if character collisions are silently accepted, if a
schedule can be changed after outcome without changing identity, if cost is
still counted per child rather than per shared trajectory, or if a sparse
synthetic design is promoted as live capability takeoff.

## Claim boundary

A pass removes one algorithmic scaling wall in the synthetic settlement
kernel. Walsh characters, Hadamard designs, fractional factorial experiments,
and sparse interaction models are established. The candidate contribution is
their authority-bound compilation with rank-quotiented residual fission,
lineage reproduction, evidence non-reuse, calibrated information yield, and a
separate false-edge operator. Literature novelty and live effect remain open.

