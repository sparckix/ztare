# Boundary-source operation-1 discriminator

Date: 2026-07-26

Parent result: `boundary_source_discriminator_result.md`

## Eigenquestion

At the same exceptional source, does operation `1` join the safe translation
branch, join operation `3`'s exclusion branch, or expose a third mechanism?

## Discriminating transaction

Execute one no-worker acquisition probe with exact budget `12`. Require:

- policy `boundary_reachability_frontier`;
- consumer action `execute_boundary_source_discriminator`;
- target source
  `943c3bdc3d7736f8e4ac3d5b0ef3ebf642c27e845ac8f672270524de8812369e`;
- target operation `1`;
- route `[0,0,0,0,0,0,0,0,2,1,1,1]`;
- source-boundary distance `0`;
- no model worker.

## Predictions

- Safe symmetry: operation `1` remains in-lifecycle and has the same factor
  effect as operation `0`.
- Directional branch: operation `1` remains in-lifecycle with a different
  effect, identifying a local controllability basis.
- Exclusion: operation `1` crosses a typed non-discharge boundary, expanding
  the source's exclusion set.
- Task event: only an external level increment changes task status.

## Kill conditions

Any preregistered identity changes, a route edge is borrowed, execution stops
early, a model worker selects an action, or no sealed ordered lineage is
written.

