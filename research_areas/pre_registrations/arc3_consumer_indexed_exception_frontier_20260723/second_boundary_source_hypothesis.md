# Second boundary-source discriminator

Date: 2026-07-26

Parent result: `admission_support_fiber_result.md`

## Eigenquestion

At the second reachable source with a typed `control_exclusion` edge, does
operation `0` provide a safe continuation, another exclusion, or a distinct
exceptional mechanism?

## Discriminating transaction

Execute one no-worker acquisition probe with exact budget `14`. Require:

- policy `boundary_reachability_frontier`;
- consumer action `execute_boundary_source_discriminator`;
- target source
  `c1ad28cdb3c2eee116b05251c406bbf6fe5a730bad3aeb3cc8374723a7484807`;
- target operation `0`;
- route `[0,0,0,0,0,0,0,0,0,0,2,1,1,0]`;
- source-boundary distance `0`;
- separate control-node and admission-support identities;
- no model worker.

## Predictions

- Safe continuation adds one admission-novel row and exposes a traversable
  edge beyond this exclusion source.
- Typed exclusion expands the source's forbidden action set.
- A different factor effect identifies another exceptional branch.
- Only an external level increment changes task status.

## Kill conditions

Any registered identity changes, support aggregation copies an edge, the
transaction is admission-duplicate, execution stops early, a worker selects
an action, or no sealed ordered lineage is produced.

