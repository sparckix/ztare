# H122 pose-quotiented mover identity

**Status:** Pre-registered 2026-08-08 before changing component-orbit identity.

## Eigenquestion

Does the exact colored-shape equality in `object_roles` split one oriented
mover into pose-specific objects, preventing the abstraction functor from
recovering the action semantics that H121 showed were valuable?

## Frozen baseline

On the 21 within-Level-1 H119 transitions, current `induce_roles` returns two
`colored_component_orbit_v1` members. One supports only action `3 -> (0,+6)`
and one supports only action `1 -> (+6,0)`. The 3x3 player changes its marker
position under rotation, so actions `0` and `2` fall outside those exact-shape
identities even though the environment preserves the player.

## Hypothesis

Component identity should be the canonical D4 orbit of its colored shape;
pose should remain a state coordinate. Lowering this quotient into the
existing component-orbit role will yield one mover identity with the complete
cardinal intervention map:

- action `0 -> (-6,0)`;
- action `1 -> (+6,0)`;
- action `2 -> (0,-6)`;
- action `3 -> (0,+6)`.

## Discriminating test

1. Add D4 canonicalization inside the existing component-orbit induction; do
   not create another tracker or role family.
2. Recompile the frozen H119 Level-1 log. Require one mover orbit and all four
   action displacements with support at least two.
3. Require `object_signature` to locate the same member identity in every
   pre-boundary player pose.
4. Preserve the existing palette-confuser test: static same-palette components
   must not enter the controlled orbit.
5. Add a synthetic rotating-marker regression whose exact shape changes on
   every move but whose D4 object identity and displacement map are complete.

## Kill conditions

- More than one mover identity remains for the H119 player.
- Any cardinal action is absent or has the wrong displacement.
- Pose quotienting merges a static palette confuser into the mover.
- Object signatures lose the mover at any observed pose.
- Existing object-role tests regress.

## Claim boundary

A pass repairs the object-identity quotient and compiles a complete action map
from H119. It does not establish task transfer, goal inference, hazard
semantics, a sufficient memory capsule, or performance lift.

