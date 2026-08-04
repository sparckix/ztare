# Context-refined frontier operation-3 hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-CONTEXT-REFINED-FRONTIER-OP3-20260726-17`

## Eigenquestion

What is the image of operation 3 at the boundary-and-context-transition source
where operation 0 is now known partial?

## Hypothesis

The exact route

`[0] * 20 + [2, 0] + [0] * 20 + [2, 3]`

crosses one known environment-context transition after its first 22 actions,
then reaches source
`2fb837ceaed2a7e114c4ed53bd39e4519aca9304900ed07d56da8d3623f006db`
and executes operation 3. Its image will be an admitted law transition, a typed
partial boundary, or an external task event.

## Discriminating test

Run one Codex-only `ls20` acquisition probe with total budget 44 and both model
worker routes disabled. Require the registered initial source, operation,
route, and context/boundary flags; require successor retention and replanning
after the known first-leg transition; then seal and recompile the target edge.

## Success criterion

- no worker-selected actions;
- the known transition creates no control exclusion;
- operation 3 executes at the registered source or its exact adapter boundary
  stops execution;
- source-operation lineage is sealed and recompilation has zero ambiguity;
- only an external adapter increment counts as Level 3 completion.

## Kill condition

Plan/source drift, known-transition exclusion, history carry, budget exhaustion
before operation 3, untyped early stop away from the target, missing lineage,
renewed ambiguity, or worker action.

## Claim boundary

This maps one remaining operation at a boundary-relevant source. Task
completion remains owned by the external adjudicator.

