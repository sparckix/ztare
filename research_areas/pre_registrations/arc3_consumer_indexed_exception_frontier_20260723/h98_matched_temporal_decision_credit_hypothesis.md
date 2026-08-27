# H98 matched temporal-decision credit

Date: 2026-08-04

Hypothesis:
`H-GPSA-MATCHED-TEMPORAL-DECISION-CREDIT-20260804-98`

Status: pre-registered; controller-neutral and offline

## Eigenquestion

Can an eventual external task discharge assign credit to an earlier
nonterminal controller decision without confusing evidence growth, motor
compression, or predicted information yield with task value?

## Hypothesis

A finite eligibility chain can carry distal task credit when two chains begin
at the same exact controller choice surface, choose different option families,
retain the same downstream controller identity, and end in externally
contrasted task outcomes. The attained chain's first option should become
task-credited and the matched open chain's first option task-hazardous even
though both first decisions were immediately nonterminal.

Predicted and observed information yield should produce a separate
variant-scoped calibration receipt. Information gain alone must not create
task credit.

## Discriminating test

Construct two anonymous matched chain pairs. In every arm:

- the task contract, decision namespace, source choice context, continuation
  controller, and complete available option-family set are identical;
- the first decision has immediate status `open`;
- the eligibility delay is one later decision;
- primitive costs and information-yield measure identities are explicit.

In both pairs, option `advance` leads through a witnessed successor decision
state to external attainment, while option `detour` leads to an externally
open terminal receipt. Compile temporal judgments with minimum support two,
then pass their preferences to the existing guarded-protocol selector.

Run negative controls that change the controller context, choice set, or
eligibility lifetime; add an open/open pair with high observed information
gain; and verify that none creates task credit. Compile predicted-versus-
observed yield calibration independently.

## Success criterion

1. `advance` receives distal `task_credited` status with enable support two.
2. `detour` receives distal `task_hazard` status with hazard support two.
3. Both credited first decisions remain immediately `open`.
4. Controller, choice-set, or lifetime mismatch refuses or separates credit.
5. An open/open high-information pair creates no task credit.
6. Yield calibration reports exact variant/measure scope and the registered
   prediction errors without changing task status.
7. Distal preferences flip a synthetic protocol selection from the
   higher-predicted-yield hazardous option to the credited option while every
   primitive and control cost remains unchanged.

## Kill conditions

- terminal outcome is copied backward without a matched alternative;
- evidence growth alone earns task credit;
- credit crosses task, controller, source-context, continuation-context, or
  choice-set authority;
- an expired eligibility trace is accepted;
- prediction calibration and task credit share one status or authority;
- selection ranking does not change; or
- calibration changes protocol cost.

## Claim boundary

Passing establishes a controller-neutral compiler for one-step delayed credit
and yield-error receipts on anonymous synthetic chains. It does not establish
ARC improvement, H97 support, cross-context transport, multi-generation
compounding, or a learned value function.
