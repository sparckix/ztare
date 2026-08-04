# Recoverable-zero target-search result

Date: 2026-07-26  
Hypothesis: `H-ARC3-RECOVERABLE-ZERO-TARGET-SEARCH-20260726-34`  
Result artifact: `recoverable_zero_target_search_audit_result.json`

## Verdict

Confirmed.

Changing only target-search admissibility from positive budget to projection
domain recovered the observed target:

```text
status: edge_found
route length: 23
generated: 187
expanded: 113
projection counterexamples: 0
```

Offline replay stayed inside the projection domain, reached budget zero at
depth 21, and renewed to 21 at depth 22. The final state had controlled base
`(45,54)`, configuration `293fb91a…`, and satisfied the inherited positive-
budget goal edge. The search found a shorter route than the 29-operation
evidence-graph route.

## Repair

`CompiledFiberSearchProblem.admissible` now checks only
`projection.in_domain(state)`. `goal_edge` still requires positive budget, so a
zero state cannot masquerade as completion; it can only remain available for
a subsequent mechanism transition. A regression test constructs a general
advance-to-zero, renew, finish system and requires that exact route.

## Claim boundary

This certifies and repairs the positive-control consumer defect. The
H30-selected target still requires a fresh search under the repaired consumer.
