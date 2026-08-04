# Context-refined frontier operation-0 hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-CONTEXT-REFINED-FRONTIER-OP0-20260726-16`

## Eigenquestion

Can the controller traverse both known reservoir-context transitions and
execute operation 0 at the first boundary-relevant source in the compressed
130-node chart?

## Hypothesis

The exact 44-action route

`[0] * 20 + [2] + [0] * 21 + [2, 0]`

reaches source `2fb837ceaed2a7e114c4ed53bd39e4519aca9304900ed07d56da8d3623f006db`
and executes operation 0. The known transitions at action indices 20 and 42
will be retained as environment-context transitions. Each will reset finite
histories and trigger replanning, decomposing the route into legs of 21, 22,
and one action without consuming a control no-good.

## Discriminating test

Run one Codex-only acquisition probe on `ls20` with total budget 44, strategy
office and engine router disabled. Require the first plan to name the registered
source, operation, route, boundary flag, and context-transition flag. At each
known context transition, require successor retention and replanning. Seal all
new evidence and recompile the partial action system.

## Success criterion

- no worker-selected actions;
- the two known context transitions produce no control exclusion;
- the registered operation 0 executes, or an adapter-owned task boundary stops
  it at that exact source;
- admitted evidence retains source-operation lineage;
- recompilation has zero ambiguity;
- only an external adapter increment counts as Level 3 completion.

## Kill condition

Plan or source drift before acting, a no-good on either known transition,
history carry across a transition, budget exhaustion before the target,
untyped early stop, missing sealed lineage, renewed ambiguity, or any
model-worker action.

## Claim boundary

This is one active intervention over a learned partial action system. It says
nothing about Level 3 completion unless the external adjudicator increments the
completed-level counter.
