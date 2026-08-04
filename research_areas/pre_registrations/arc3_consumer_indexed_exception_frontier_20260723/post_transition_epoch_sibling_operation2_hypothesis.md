# Post-transition epoch-sibling operation-2 hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-POST-TRANSITION-EPOCH-SIBLING-OP2-20260726-19`

## Eigenquestion

What is the operation-2 image at the source where operation 1 is an epoch
boundary and operation 0 changes predictive context?

## Hypothesis

The exact route

`[0] * 20 + [2, 0] + [0] * 20 + [2, 1] + [0] * 20 + [2, 2]`

crosses the two known context transitions, reaches source
`495dd39e5a541d6dd6f91ecfbc9eae6f545a318209bc22aa45e9d2e0d6074cc1`,
and executes operation 2. Its image will complete another branch of the local
partial-action table as a deterministic transition, typed boundary, or
external task event.

## Discriminating test

Run one Codex-only `ls20` acquisition probe with budget 66 and model-worker
routes disabled. Require the registered plan identity and two known-transition
replans, then seal and recompile operation 2 at the exact source.

## Success criterion

No worker actions or exclusions on known transitions; exact target execution
or adapter boundary; sealed lineage; zero graph ambiguity; external increment
required for Level 3 completion.

## Kill condition

Identity drift, exclusion, history carry, premature exhaustion or stop,
lineage loss, ambiguity, or worker action.

## Claim boundary

This fills one sibling image in a learned partial action table. Task completion
remains external.

