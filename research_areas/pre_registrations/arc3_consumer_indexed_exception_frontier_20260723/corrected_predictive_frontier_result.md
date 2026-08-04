# Corrected predictive-frontier result

Date: 2026-07-26

Parent hypothesis: `corrected_predictive_frontier_hypothesis.md`

## Outcome

The no-worker probe executed `[0, 2]`.

- no level event;
- no new frame transition;
- task discharge remained open;
- a distinct ordered history slice was archived as
  `raw/episodes/eval_slices/eval_20260726T053829456027Z.jsonl`,
  SHA-256
  `850d3dd32632d32d6b8673c2760afcd366c5674f05ec8e370d6aabe0a7e37fbf`.

## Apparatus counterexample

The online receipt compiled 277 observations and retained one
boundary-contaminated ambiguity, whereas the preflight active-epoch audit had
zero. The sealed-evidence consumer admitted task-open slices from stale
epochs and origin seeds because it scoped only by carrier and task contract.

That violates the governing identity of a predictive state: lifecycle epoch
and origin seed own the lineage. The consumer now filters sealed evidence by
carrier, task contract, source epoch, and origin-seed identity. A regression
test proves stale sources cannot enter the active no-good relation.

## Recompiled consequence

With the ownership filter and the `[0, 2]` history admitted:

- 279 current-lineage observations;
- selected action suffix length one;
- zero boundary-contaminated non-commuting relations;
- 80 selected fibers;
- next safe frontier route `[0, 3]`;
- zero ambiguous traversal edges.

Evidence:
`boundary_segmented_predictive_quotient_audit_result.json`.
