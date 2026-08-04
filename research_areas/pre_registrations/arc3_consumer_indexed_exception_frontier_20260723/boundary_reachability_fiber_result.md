# Boundary-reachability fiber result

Date: 2026-07-26

Parent hypothesis: `boundary_reachability_fiber_hypothesis.md`

## Result

The representation prediction passed and the context-transition prediction
did not.

The current witnessed system compiled to:

- `83` control nodes;
- `86` witnessed source-operation relations;
- `246` graph source-operation gaps;
- `3,590` pairwise compatibility gaps;
- `80` deterministic edges, `1` ambiguous edge, and `5` typed
  `control_exclusion` boundaries;
- `38` nodes and `109` graph gaps reachable from the active source.

All six programs imported from the pre-refinement receipt reindexed as
`stable`. Each retained its two concrete initiation witnesses and transported
through witnessed edges to one effect-trace variant. The current predictive
quotient reported zero options because its class IDs split; the program
objects did not disappear.

Evidence:
`boundary_reachability_fiber_audit_result.json`.

## Boundary concentration

The five typed exclusion edges reduce the reachable frontier from `109` to
`35` boundary-relevant source-operation pairs. The highest-ranked executable
test is:

`[0,0,0,0,0,0,0,0,2,1,1,0]`

It queries operation `0` at source
`943c3bdc3d7736f8e4ac3d5b0ef3ebf642c27e845ac8f672270524de8812369e`,
where operation `3` already has two sealed `control_exclusion` witnesses.
That boundary is explicitly non-discharge evidence; it supplies an
exceptional source, not task authority.

## Apparatus findings

The projection's admitted acquisition key has only one value across the
active graph. It therefore does not represent the claimed one-shot mode
change in this evidence slice. Mode-transition steering remains unavailable
until a context factor is evidenced and admitted.

While wiring the new frontier, the planner's orbit-completion selector was
also found to read `selected_frontier` before assigning it in the current
replan. Python could retain a prior loop value, coupling a new decision to a
stale frontier. The selector now reads the current predictive frontier
directly.

## Consequence

Use the boundary-source query as the next discriminating transaction. Keep
pairwise compatibility as a local diagnostic. Separately investigate the
missing context factor; do not label any graph region “post-mode” while the
admitted acquisition key is constant.

