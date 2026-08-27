# H100 two-stage eligibility ledger

Date: 2026-08-07

Hypothesis:
`H-GPSA-TWO-STAGE-ELIGIBILITY-LEDGER-20260807-100`

Status: pre-registered; controller-neutral and offline

Research-isomorphism forecast:
`8c61f401aeb4fc808257690939e516f024a5c5867489a28b4a8de7e57e15fed8`
(`Two-Stage Eligibility Ledger`)

## Eigenquestion

Can successive decision windows become a replayable episode without granting
task value at collection time, and can a separate sealed replay contract bind
two exact-source arms strongly enough for delayed terminal contrast?

## Hypothesis

Online collection and terminal strengthening are separate state transitions.
An episode draft may collect successive decision windows only when each window
carries exact choice authority, selected option identity, primitive cost,
predicted information yield, observed information yield, a shared yield
measure identity, an observed-yield evidence reference, and an explicit
successor decision state. The draft carries no task-credit authority.

A sealed replay contract separately owns pair identity. It freezes the task,
first-choice authority, continuation policy, environment source, replay
prefix, yield measure, finite lifetime, and one distinct first-option family
for each of exactly two arms. Only a draft matching that contract may become a
`DecisionEligibilityChain`. Similarity or equal terminal reward cannot replace
the contract.

## Discriminating test

1. Build two complete anonymous episode drafts from the same frozen replay
   source. Both first decisions are immediately open; one later attains and one
   remains open.
2. Verify that neither unbound draft produces a continual-memory chain or task
   preference.
3. Freeze one two-arm replay contract and bind each draft to its declared arm.
4. Settle and persist the resulting chains through the H98/H99 compiler.
5. Attempt binding after independently changing task, source context,
   continuation controller, complete choice set, environment source, replay
   prefix, yield measure, arm option, and eligibility lifetime.
6. Attempt to bind a decision window whose observed-yield evidence reference
   is absent.
7. Compare primitive costs before and after terminal strengthening.

## Success criterion

1. Complete drafts are admitted but explicitly deny task-credit authority.
2. Unbound drafts produce zero option preference.
3. The sealed exact-source arm pair binds and reconstructs `+1/-1` distal
   preference after the frozen minimum support is met.
4. Every authority, source, arm, measure, or lifetime edit is refused.
5. Missing observed-yield evidence prevents draft admission.
6. Equal outcomes without a sealed contract cannot be paired.
7. Primitive costs are unchanged by binding, settlement, persistence, or
   reranking.
8. Yield calibration remains a separate receipt with task-credit authority
   disabled.

## Kill conditions

- collection itself grants task value;
- a contract is inferred from episode similarity;
- a draft can bind to an undeclared arm or option;
- any frozen source/authority edit crosses the replay boundary;
- information yield substitutes for terminal task adjudication;
- missing observed-yield evidence is accepted; or
- later value edits primitive cost.

## Claim boundary

Passing establishes the controller-neutral two-stage episode/replay carrier.
It does not establish an ARC observed-yield instrument, automatic ARC play-loop
collection, live counterfactual forks, H97 support, or score gain.
