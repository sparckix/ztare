# Post-transition epoch-sibling operation-3 hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-POST-TRANSITION-EPOCH-SIBLING-OP3-20260726-22`

## Eigenquestion

What is the final unmapped operation at the source where operations 0, 1, and 2
all have adapter-owned epoch-boundary images?

## Hypothesis

The exact route

`[0] * 20 + [2, 0] + [0] * 20 + [2, 1] + [0] * 20 + [2, 3]`

crosses the two known context transitions, reaches source
`495dd39e5a541d6dd6f91ecfbc9eae6f545a318209bc22aa45e9d2e0d6074cc1`,
and executes operation 3. The result will close the four-operation local table
as a fourth epoch boundary, a distinct law image, or an external task event.

## Discriminating test

Run one Codex-only `ls20` acquisition probe with budget 66 and both worker
routes disabled. Require the compact 130-node system, registered plan identity,
two known-transition replans, exact target execution, sealed lineage, and
post-run recompilation.

## Success criterion

No worker action or known-transition exclusion; operation 3 executes at the
exact source or its adapter boundary fires; all four sibling operations become
typed; graph ambiguity stays zero; Level 3 requires an external increment.

## Kill condition

Inflated-history selection, plan/source drift, exclusion, history carry,
premature stop, missing lineage, ambiguity, or worker action.

## Claim boundary

This closes one local partial-action table. It does not establish task
completion without the external adjudicator.

