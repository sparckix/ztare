# Second epoch-boundary source operation-1 hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-SECOND-EPOCH-SOURCE-OP1-20260726-23`

## Eigenquestion

Does operation 1 at the second reachable epoch-boundary source expose a
different local mechanism or external task event than the completed
four-boundary basin?

## Hypothesis

The exact route

`[0] * 20 + [2, 0] + [0] * 20 + [2, 1] + [0] * 21 + [1]`

crosses two known context transitions, reaches source
`b59ad0723828b9a9246b9682bef318112dadbbc7901475e228e1874d9bb56e6d`,
and executes operation 1. The source already has an operation-0 epoch boundary
but is a distinct control node; operation 1 may yield a deterministic image,
another typed boundary, or an external task event.

## Discriminating test

Run one Codex-only `ls20` probe with budget 66 and worker routes disabled.
Require the compact chart, exact plan/source/operation, two known-transition
replans, sealed target lineage, and post-run recompilation.

## Success criterion

No worker action, history inflation, or known-transition exclusion; exact
target execution or adapter boundary; zero ambiguity; external level increment
required for task completion.

## Kill condition

Inflated selection, plan/source drift, exclusion, history carry, premature
stop, missing lineage, ambiguity, or worker action.

## Claim boundary

This tests one sibling at a distinct lifecycle source. It does not infer that
all boundary sources share the completed basin's operation table.

