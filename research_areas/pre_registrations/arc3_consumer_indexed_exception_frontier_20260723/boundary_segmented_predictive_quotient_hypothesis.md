# Boundary-segmented predictive quotient

Date: 2026-07-26

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

Research-isomorphism candidate:
`7e2af34fb4f8cf5bed52f0a3d071e7ccae8dedf0fdbc8f25ef16e5eafd36abfd`

## Eigenquestion

Is the canonical control state the coarsest boundary-segmented predictive
equivalence class of histories, rather than a hand-selected coordinate tuple
or bounded suffix?

## Mother object

An evidence prefix is a state of a partial Mealy system. For bounded test
depth `d`, histories `h` and `h'` are equivalent exactly when:

1. they belong to the same lifecycle chart;
2. for every admitted intervention word of length at most `d`, their observed
   mechanism-effect, boundary, and unknown signatures agree;
3. recursively, ordinary successors belong to the same equivalence class.

Unknown, boundary, ordinary effect, and ambiguous consequence are distinct
outcomes. Missing evidence cannot be treated as a negative transition.

The finite evidence compiler should refine this partition until stable. The
result is a boundary-segmented predictive quotient automaton.

## Explicit transport

Forward map:
ordered evidence prefix -> stable predictive equivalence class.

Backward section:
each quotient class retains at least one witnessed prefix, observation, and
evidence reference. Reprojecting that witness must recover the class.

Operation transport:
an admitted intervention maps a class to an effect-labelled target class only
when every represented witness agrees. Otherwise the relation remains
ambiguous or unknown.

Boundary transport:
an environment-owned boundary is an undefined operation in the source chart
and a lineage reset; it is never an ordinary target edge.

Failure transport:
non-commutation, unknown tests, stale-lifecycle evidence, and section failures
remain explicit and prevent open-loop traversal.

## Skill composition

A skill or option is a deterministic path in the predictive quotient with:

- an initiation class;
- an intervention word;
- effect-labelled intermediate transitions;
- a termination class or boundary;
- witnessed support and an inverse evidence section.

The option identity is invariant under presentation coordinates. Reuse is
permitted only when its initiation class is predictive-equivalent, not merely
visually similar.

## Discriminating checks

1. Compile the current sealed lineage into the quotient without live actions.
2. Prove the quotient section commutes.
3. Require fewer quotient classes than selected history fibers.
4. Preserve every boundary and non-commuting witness.
5. Compare frontier routing before and after quotienting; every traversed
   quotient edge must be single-valued for all represented witnesses.
6. Admit the `[0, 2]` slice and verify the previous query is no longer offered.
7. Mine deterministic paths used from more than one witnessed presentation as
   option candidates; no task label or substrate coordinate may enter.

## Kill conditions

Reject or refine the object if:

- partition refinement merges a pair that yields different admitted future
  tests;
- compression is achieved by dropping unknown or boundary outcomes;
- a quotient route lacks a concrete witness section;
- option reuse crosses an incompatible lifecycle chart;
- exact trace identity is required to restore commutation;
- the quotient does not change any consumer decision relative to suffix-only
  control.
