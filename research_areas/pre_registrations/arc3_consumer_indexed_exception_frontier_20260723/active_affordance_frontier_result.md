# Active affordance frontier result

Date: 2026-07-26  
Hypothesis: `H-ARC3-ACTIVE-AFFORDANCE-FRONTIER-20260726-29`  
Result artifact: `active_affordance_frontier_audit_result.json`

## Verdict

Refuted.

The active quotient compiled to 130 nodes, 145 deterministic relations, ten
typed boundaries, six context transitions, 127 reachable nodes, 366 reachable
unsupported source-operation pairs, and zero ambiguous relations. All four
ordinary operation displacements were admitted with a unique supported mode.

Exactly one reachable pair matched the frozen prior-success destination
footprint. It was not unsupported. It was the already observed operation `1`
law at source `26bcf98b…`, reached by the 29-operation route recorded in the
JSON result. The source representative is
`raw/episodes/eval_slices/eval_20260725T180904835221Z.jsonl#27`; its controlled
origin is `(45, 54)` and its attempted destination is `(50, 54)`. Twenty-eight
observations support the law. The external task receipt remained open.

## Information gained

The prior-success footprint does identify the active target geometry, but
geometry alone does not identify a productive edge. The matched active edge
has finite-configuration digest `293fb91a…`, the same digest carried by the
epoch-0 completion and all five epoch-1 terminal failures. The held-out
epoch-1 completion instead has digest `64766534…`.

Those two configuration partitions are dihedral images:

```text
293fb91a…                 64766534…
000000                    000000
000000                    000000
111100                    001111
111100                    001111
001100                    001100
001100                    001100
```

The H28 descriptor rotated the destination footprint to a canonical frame but
left the configuration in its original frame. That erased their relative
orientation. The next test therefore treats destination and configuration as
one object under a single shared dihedral action.

## Claim boundary

This result localizes a target geometry and rejects an unconditioned footprint
frontier. It does not establish a productive Level 3 configuration, route, or
task completion.
