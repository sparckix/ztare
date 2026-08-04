# Operation-effect predictive-state lift

Date: 2026-07-25

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

## Eigenquestion

Does replacing action history with a bounded suffix of observed
`(operation, mechanism effect)` tokens separate the remaining boundary/law
counterexample while preserving a compressed, recursively updated state?

## Governing object

The candidate state is a Mealy-style predictive state:

`(current fiber factors, bounded prior operation-effect suffix)`.

For an admitted law transition, the token is computed from the same accepted
factor projection used by the partial-action relation:

`token = (operation, fiber_mechanism_effect(source, successor))`.

The token belongs to the completed transition and is available before the
next intervention. A boundary intervention does not invent a successor
effect; it terminates the current trajectory.

## Transport obligations

1. Forward map: each ordered observed trajectory maps to fiber factors plus a
   recursively accumulated operation-effect suffix.
2. Backward section: every compiled relation retains source observations,
   transition observations, and evidence references sufficient to recover
   the represented witness.
3. Operation transport: applying an intervention advances the suffix only
   after its observed successor is available.
4. Boundary transport: sealed control exclusions remain explicit undefined
   operations and reset lineage; they are never converted into ordinary
   effects.
5. Failure transport: any source/operation with more than one admitted
   consequence under the lifted key remains non-commuting and cannot be a
   traversal edge.

## Discriminating test

Compile the same sealed ordered trajectories under:

- frame-only state;
- bounded action suffixes;
- bounded operation-effect suffixes.

Select the shortest operation-effect suffix attaining the minimum
boundary-contaminated non-commutation while retaining at least one repeated
fiber when possible.

Success requires all of:

- zero boundary-contaminated non-commuting relations;
- fewer fibers than admitted observations;
- recursive live start-key construction from the verified seed replay;
- a frontier route containing no non-commuting traversal edge.

Only after those offline conditions hold may a no-worker acquisition probe
execute the route.

## Kill conditions

Reject or refine the lift if:

- the remaining ambiguity persists at every observed suffix length;
- separation depends on an exact trace index, cumulative count, game label,
  cell coordinate, or manually named phase;
- seed replay and sealed trajectory evidence use incompatible token updates;
- boundary effects are fabricated from post-boundary observations;
- compression vanishes;
- the backward witness section or failure-mode transport is missing.
