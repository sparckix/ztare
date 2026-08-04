# Explicit boundary witness transport

Date: 2026-07-25

Parent tick: `tick-arc3-consumer-indexed-exception-frontier-20260723`

## Eigenquestion

Does carrying sealed task-open boundary edges as first-class partial-action
observations expose the non-commuting source-operation fiber before planning
and prevent its reuse as either a traversal edge or an unsupported frontier?

## Hypothesis

The controller already owns evidence-backed no-good edges. Attaching those
edges to the partial-action compilation, separately from law-scored
transitions, will produce a boundary effect with no target. When a law
successor shares its projected source and operation, the relation will contain
multiple effects and become ineligible for open-loop traversal or frontier
selection.

The implementation must preserve:

1. sealed evidence provenance for every boundary observation;
2. separate authority for law transition, control no-good, and task discharge;
3. current-run boundary feedback on the next lifecycle leg;
4. cross-run boundary replay through the verified sealed-slice lineage;
5. substrate-neutral state and operation values.

## Discriminating checks

1. A boundary edge absent from the law transition iterable still appears in
   the compiled relation.
2. A law successor and boundary witness with the same projected
   source-operation identity emit a non-commutation receipt.
3. The fixed-action frontier planner neither traverses nor targets that pair.
4. The multi-life controller passes newly observed boundary edges into the
   next planning leg.
5. The next no-worker governed probe does not target source digest
   `0aa941c92983b390b8dceaf7c60ed536d70f5482107d4e349fb57f4331f2cebb`
   with operation `3`.

## Kill conditions

Reject or refine the route if:

- an explicit boundary loses its sealed evidence reference;
- the relation reports the pair as single-valued;
- the planner targets the pair again;
- carrying the witness requires inserting it into the law-scored bank;
- task discharge authority moves away from the environment adapter.

## Preflight result

The active-only audit compiles one non-commuting relation from the explicit
boundary witness and the law-owned successor. The old
`0aa941… / operation 3` frontier is no longer selected. The next candidate is
a 17-action single-valued route to source digest `40c8b3… / operation 1`.

Preflight artifact:
`explicit_boundary_active_audit_result.json`.
