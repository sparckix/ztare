# H97 pre-live staged-spending amendment

Date: 2026-08-04

Applies to:
`H-GPSA-CAUSAL-RESPONSE-DERIVATIVE-20260803-97`

Frozen experiment:
`8f9ae209831786c58ec83cea87e54a33caba821d0f0096d56cee7ba43210a4a6`

## Evidence state before this amendment

One live invocation reached the Responses API and received
`credit_balance_exhausted` before a response was created. It produced no
controller proposal, no eligible parent, no branch revision, and no ARC
environment action. The original H97 success criterion therefore remains
unobserved.

## Amendment

Treat the matched branch revision as a sequential first-stage gate. After each
eligible blind parent has been forked into byte-matched offer and withhold
revisions, stop and seal H97 as rejected before environment contact if any of
these already-frozen kill conditions occurs:

1. the two revisions do not cite the same parent response;
2. the offer revision does not satisfy the frozen residual response;
3. the withhold revision satisfies the frozen residual response
   spontaneously.

Only a pair that passes all three checks may enter its charged environment
rollouts. Because H97 requires offer support `2/2`, withhold support `0/2`, and
shared-parent identity `1.0`, failure in either pair makes the registered
success criterion unreachable. Later environment outcomes cannot repair that
first-stage failure.

This amendment changes spending order only. It does not change the derivative,
interventions, parent eligibility rule, pair order, action budget, outcome
metric, success threshold, or claim boundary.

## Structural source

Codex/Sol conjecture mode produced the candidate `Budgeted Eligibility Packet
with Replay Checksum`, candidate
`02e3c41bd1657d3c01b738cdbabfb2f099794e925861fc5da8a6354c22027293`.
The transported constraint is that a delayed settlement is permitted to
update only a compatible, surviving eligibility packet. It does not justify
credit after the packet-level first stage has failed.

## Conditional next discriminator

If H97 passes, the next experiment should not promote the complete 3,849-byte
causal packet as an indivisible skill. It should preregister progressive,
byte-matched component ablations and identify the minimum packet whose
offer-versus-withhold fork still changes the descendant proposal and settled
outcome. That conditional experiment is not opened by this amendment.
