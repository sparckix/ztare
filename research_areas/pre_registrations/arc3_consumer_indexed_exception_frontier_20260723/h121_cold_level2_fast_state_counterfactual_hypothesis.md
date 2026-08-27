# H121 cold Level-2 fast-state counterfactual

**Status:** Pre-registered 2026-08-08 before the fresh controller was created.

## Eigenquestion

Was H119's oracle-optimal 10-action `tu93` Level-2 trajectory enabled by the
session state acquired on Level 1, or can a fresh identical model produce the
same behavior from the Level-2 observation alone?

## Frozen treatment and control

- Treatment evidence: H119 actions 23--32, one persistent
  `gpt-5.6-sol` max-effort session after Level 1, exact Level-2 start
  observation SHA-256
  `c654ced9fcd15bcc9937e6748e64c4d55b5fe15b21547acbb982068947f7eae4`,
  completion in the 10-action oracle minimum.
- Control: a newly created `gpt-5.6-sol` max-effort session receives the exact
  same Level-2 start observation but no Level-1 prompt, action, prediction,
  memory, or solution trace. It owns 10 primitive actions on the locally
  cached full game dynamics.
- The local reset must reproduce the frozen 64x64 start grid byte-for-byte.
- Every control inference exchange and turn is durably persisted.

## Prediction and discriminator

Prediction: the cold control will not complete Level 2 within 10 actions,
because it lacks the learned action-direction map and graph-navigation state.

- Fast-state supported: cold control gains zero levels while the frozen
  treatment completed in 10.
- Observation-sufficient: cold control also completes in exactly 10 actions;
  Level-1 history is unnecessary for the observed H120 efficiency.
- Ambiguous: cold control completes but uses fewer than 10 actions (oracle
  contradiction), trace integrity fails, or start observations differ.

## Claim boundary

A treatment-control difference identifies value in the model's persistent
session state for this Level-2 start. It does not identify which internal
representation carried the value and does not credit ZTARE's external memory,
skill compiler, or planner.

## Pre-disposition observation-identity correction — 2026-08-08

The controller run completed, but settlement stopped before writing an
aggregate because the frozen H119 SHA-256 names a settled-observation receipt.
That receipt intentionally includes action count, level count, observation
index, and adapter epoch. Those lifecycle fields differ in a cold Level-2
control even when the rendered 64x64 grid is byte-identical.

The governing object for the matched treatment surface is the grid carrier,
defined before disposition as exact equality of `grid_shape` and
`grid_rle_rows`. Its canonical SHA-256 is
`dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24`.
The original receipt SHA remains recorded as treatment provenance. No model
inference will be rerun; settlement must use the already persisted ten-exchange
trace and deterministic environment replay. The behavioral discriminator is
unchanged.

