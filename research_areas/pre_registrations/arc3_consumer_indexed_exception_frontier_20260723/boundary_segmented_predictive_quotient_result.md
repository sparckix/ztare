# Boundary-segmented predictive quotient result

Date: 2026-07-26

Parent hypothesis:
`boundary_segmented_predictive_quotient_hypothesis.md`

## Offline result

The current active-lineage partial system contains 80 selected history
fibers. Stable future-test refinement reaches 74 predictive classes in 19
rounds.

- inverse witness section: pass;
- operation/effect/boundary transport: pass;
- compression ratio: `0.925`;
- every boundary relation preserved;
- one non-commuting relation preserved;
- five deterministic option paths surfaced.

The quotient frontier and suffix frontier both choose `[0, 3]`, but the
quotient changes the experiment identity. It exposes one local predictive
target orbit:

- source class:
  `b6e27e05259baebdf1d94e4ea8bbb9059bf9ce89d8e9f92995936dd1792f7a18`;
- witnessed operations: `1`, `2`;
- their immediate mechanism effects differ;
- both terminate in predictive class
  `e99a101bf89a2462402300b6899ac5da13e55b191206b383b106bcac7f156482`;
- untested operation: `3`.

Thus `[0, 3]` is an orbit-completion discriminator rather than an arbitrary
frontier cell.

Evidence:
`boundary_segmented_predictive_quotient_audit_result.json`.

## Consumer consequence

The planner now consumes a commuting compressed quotient when available,
reports its option surface, and labels a matched unknown operation as
`predictive_quotient_orbit_completion`. It falls back to the witnessed
partial-action route when no valid compression exists.
