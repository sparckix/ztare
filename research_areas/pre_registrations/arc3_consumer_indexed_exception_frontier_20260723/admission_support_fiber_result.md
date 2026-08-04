# Admission-support fiber result

Date: 2026-07-26

Parent hypothesis: `admission_support_fiber_hypothesis.md`

## Result

The current graph contains `85` history-sensitive control nodes and `82`
exact rendered-source support identities. Aggregating operation support over
those 82 identities did not add an edge, effect, or successor. The graph
retains `88` witnessed relations, `82` deterministic edges, one ambiguous
edge, and five typed boundaries.

The redundant operation-`1` query at source
`943c3bdc3d7736f8e4ac3d5b0ef3ebf642c27e845ac8f672270524de8812369e`
disappeared from the acquisition frontier. Its history-specific edge remains
evidence-owned in the sealed transaction; other history nodes receive only
the support fact.

Evidence: `admission_support_fiber_audit_result.json`.

## Next frontier

The corrected graph selects a different typed-exclusion source:

- source
  `c1ad28cdb3c2eee116b05251c406bbf6fe5a730bad3aeb3cc8374723a7484807`;
- operation `0`;
- route
  `[0,0,0,0,0,0,0,0,0,0,2,1,1,0]`;
- boundary distance `0`.

This is an admission-novel query rather than a history-only duplicate.

