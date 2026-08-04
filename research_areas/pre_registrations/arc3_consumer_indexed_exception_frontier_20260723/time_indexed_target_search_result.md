# Time-indexed target-search result

Date: 2026-07-26  
Hypothesis: `H-ARC3-TIME-INDEXED-TARGET-SEARCH-20260726-33`  
Result artifact: `time_indexed_target_search_audit_result.json`

## Verdict

Refuted.

Adding time as the sole extra equality coordinate made no difference. The
search again exhausted exactly 457 generated / 458 expanded states at depth
20 with no route and no projection counterexample.

Forced replay of the H29 route explains the invariant cutoff:

```text
depth 20: ordered_budget = 1
depth 21: ordered_budget = 0
depth 22: ordered_budget = 21
```

The depth-21 state remains inside the projection domain and its next operation
produces an evidence-aligned renewal. `CompiledFiberSearchProblem.admissible`
nevertheless requires `ordered_budget > 0`, so search discards the recoverable
zero state before it can take the renewal edge. Its heuristic already contains
renewal landmarks, making the hard exclusion internally inconsistent with the
consumer's intended lifecycle.

## Claim boundary

Clock merging does not explain H31. The next discriminator changes only the
audit-local feasibility predicate to retain in-domain zero-resource states;
core behavior remains untouched until that ablation passes.
