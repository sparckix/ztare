# History-lift selector short-circuit result

Date: 2026-07-26

Parent hypothesis: `history_lift_short_circuit_hypothesis.md`

## Result

Pruned and exhaustive selection on identical current evidence both selected:

- history family `action`;
- suffix length `1`;
- action-system SHA-256
  `c2613b4dd789c564c35af5184b768e577cd83cb0b64551dc9aceb0e5ca759e10`;
- zero boundary-noncommuting relations;
- the same 86-node, 89-relation control graph and exact next frontier.

Pruned mode evaluated four candidates and eliminated 62 candidates that
could not win the selector ordering. Exhaustive mode evaluated all 66.

Evidence:

- `second_boundary_source_audit_result.json`;
- `history_lift_exhaustive_audit_result.json`.

The fixture suite also includes a case where action histories remain
ambiguous and the operation-effect family wins at suffix length one. The
short circuit preserves that choice.

