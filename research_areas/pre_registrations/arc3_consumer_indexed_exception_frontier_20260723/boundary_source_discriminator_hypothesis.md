# Boundary-source discriminator

Date: 2026-07-26

Parent result: `boundary_reachability_fiber_result.md`

## Eigenquestion

At a control source where operation `3` has twice caused an externally typed
non-discharge boundary, what does the previously untested operation `0` do?

## Discriminating transaction

Execute one no-worker acquisition probe with exact budget `12`. Require:

- policy `boundary_reachability_frontier`;
- consumer action `execute_boundary_source_discriminator`;
- target source
  `943c3bdc3d7736f8e4ac3d5b0ef3ebf642c27e845ac8f672270524de8812369e`;
- target operation `0`;
- route `[0,0,0,0,0,0,0,0,2,1,1,0]`;
- source-boundary distance `0`;
- no model worker proposing or judging an action.

## Predictions

Safe alternative:
operation `0` remains inside the lifecycle and supplies a new witnessed
effect. This distinguishes an operation-specific exclusion from a dead
control region.

Boundary contraction:
operation `0` also crosses a typed non-discharge boundary. The source then
has a multi-operation exclusion surface and should be treated as a
degeneration, not a generic support gap.

Task event:
the external adapter reports a level increment. That event alone changes
task status.

## Kill conditions

- the online policy or route differs from the preregistration;
- the target source no longer has the sealed operation-`3` exclusion
  witnesses;
- a pairwise support gap outranks the boundary source;
- an unwitnessed route edge is borrowed;
- the transaction stops before operation `0`;
- no sealed ordered lineage is written.

