# Mutable-world object inventory result

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-MUTABLE-WORLD-OBJECT-INVENTORY-20260726-40`  
Verdict: refuted

The inventory separated both H38 and H39. Search advanced to 486 generated /
301 expanded states before another same-time counterexample. The two source
states had equal actor, configuration, budget, world-object inventory, and
clock. They differed only at interface cells `(61,56),(62,56)` (`3` versus
`8`); operation 2 then produced equal world states but different H35 marker
values.

The remaining strip is not an object-identity failure. Across 16,578 evidence
rows, rows 61–62 after the primary budget rendering contain exactly four
states. Three two-column payload groups move through a deterministic
`3 → 2 → 1 → 0 → 3` live-group cycle; separator columns are constant and the
twelve payload cells are binary. This is a second finite resource rendering.

The object inventory is retained. The next test replaces the point marker with
the complete evidence-derived secondary resource configuration and composes
both coordinates under clock identity.

Evidence:

- `mutable_world_object_inventory_audit_result.json`
- `mutable_world_object_inventory_audit.py`
