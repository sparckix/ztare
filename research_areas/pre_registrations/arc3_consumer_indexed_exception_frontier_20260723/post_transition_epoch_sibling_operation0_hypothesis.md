# Post-transition epoch-sibling operation-0 hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-POST-TRANSITION-EPOCH-SIBLING-OP0-20260726-18`

## Eigenquestion

What is the operation-0 image at the first reachable source that already has an
adapter-owned epoch boundary under sibling operation 1?

## Hypothesis

The exact 66-action route

`[0] * 20 + [2, 0] + [0] * 20 + [2, 1] + [0] * 20 + [2, 0]`

crosses the two known predictive-context transitions after its first and second
22-action legs, then reaches source
`495dd39e5a541d6dd6f91ecfbc9eae6f545a318209bc22aa45e9d2e0d6074cc1`
and executes operation 0. Because sibling operation 1 already has an
`epoch_boundary` image there, operation 0 is a concentrated exceptional-set
test: it will expose a distinct law image, a second partial boundary, or an
external task event.

## Discriminating test

Run one Codex-only `ls20` acquisition probe with budget 66 and model-worker
routes disabled. Require the registered initial plan, source, operation, route,
context-crossing flag, and source boundary flag. Require exact-law successor
retention and replanning after both known transitions; seal and recompile the
target operation.

## Success criterion

- no worker-selected actions;
- neither known context transition creates an exclusion;
- operation 0 executes at the registered source or its exact adapter boundary
  stops it;
- lineage is sealed and recompilation has zero ambiguity;
- only an external adapter increment establishes Level 3 completion.

## Kill condition

Identity drift, exclusion of a known transition, history carry, budget
exhaustion before the target, off-target untyped stop, missing lineage,
ambiguity, or worker action.

## Claim boundary

This interrogates one sibling operation at an epoch-boundary source. It does
not establish task completion without the external adjudicator.

