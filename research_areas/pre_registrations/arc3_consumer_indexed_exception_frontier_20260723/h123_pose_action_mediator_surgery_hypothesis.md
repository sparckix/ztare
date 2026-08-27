# H123 pose/action mediator surgery

**Status:** Settled 2026-08-08 as inverted/refuted (`causal=0`,
`placebo=1`). Pre-registered before either fresh arm was created.

## Eigenquestion

Is the pose-quotiented action map recovered by H122 a sufficient behavioral
mediator for the Level-1 session-state advantage measured by H121?

## Frozen source and target

- Source receipt: H122 result SHA-256
  `60dbf8f66377625a28f08a1252c07f11f99f17673848cd16dab535ae712f0dd7`.
- Source abstraction: one D4 mover identity, four observed poses, mappings
  `0=(-6,0)`, `1=(+6,0)`, `2=(0,-6)`, `3=(0,+6)`.
- Target: the exact H121/H119 Level-2 initial grid carrier at SHA-256
  `dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24`.
- Target compatibility must be checked before inference by locating exactly one
  source mover identity in the target grid under the D4 quotient.
- Oracle minimum and arm budget: 10 primitive actions.

## Arms

Two newly created `gpt-5.6-sol` max-effort sessions receive one one-shot capsule
at their first decision. Capsules share schema, mover identity, source/target
authority, compatibility witness, refusals, and exact canonical prompt bytes.

1. `pose_action_map`: includes the four H122 action-to-displacement mappings.
2. `pose_only_placebo`: states only that four stable action indices were
   witnessed and deliberately withholds their direction assignment. It carries
   no false map, target route, coordinates, hazard rule, or Level-2 action.

The shorter canonical capsule is padded in an inert field to exact UTF-8 byte
equality. Arm order is determined from the pre-inference capsule-pair hash.
Every raw exchange and environment turn is persisted. Recall is burned after
the first decision.

## Prediction and dispositions

Prediction: `pose_action_map` completes Level 2 within 10 actions and
`pose_only_placebo` completes zero levels.

- Supported single pair: causal `1`, placebo `0`.
- Map insufficient: causal `0`, placebo `0`.
- Content not isolated: causal `1`, placebo `1`.
- Inverted/refuted: causal `0`, placebo `1`.
- Invalid: unequal capsule bytes, target mover mismatch, start-grid mismatch,
  repeated recall, trace failure, or a completion below the exact oracle.

H121's no-injection cold control (`0/10`, terminal at action 5) is contextual
evidence but is not substituted for the length-matched H123 placebo.

## Claim boundary

A supported pair shows that an automatically induced source action map can
restore task value in one fresh target-level controller. It does not establish
cross-game transfer, population effect, minimality among all capsules,
parameter distillation, broad ARC capability, compounding across generations,
or literature novelty.
