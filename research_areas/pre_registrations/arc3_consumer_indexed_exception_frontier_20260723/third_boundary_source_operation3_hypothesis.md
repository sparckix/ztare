# Third boundary-source operation-3 discriminator

Date: 2026-07-26

Parent result: `third_boundary_source_result.md`

## Eigenquestion

At the source where operations `0` and `2` are excluded, does operation `3`
provide a safe exit, join the exclusion surface, or trigger an external task
event?

## Discriminating transaction

Execute one no-worker acquisition probe with exact budget `22`. Require:

- policy `boundary_reachability_frontier`;
- consumer action `execute_boundary_source_discriminator`;
- source
  `4ab929993a22db595db68125a854b6e5c70ac5791623119cbddea473b29225c5`;
- operation `3`;
- route
  `[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,3]`;
- boundary distance `0`;
- no model worker.

## Predictions

- Safe exit: operation `3` remains in-lifecycle and supplies a traversable
  edge away from the two-operation exclusion surface.
- Degeneration: operation `3` is also excluded, leaving operation `1` as the
  only admitted local direction.
- Task event: only an external level increment changes task status.

## Kill conditions

Any registered identity changes, the route borrows an edge, admission novelty
is absent for a non-boundary result, execution stops early, a worker selects
an action, or no sealed lineage is written.

