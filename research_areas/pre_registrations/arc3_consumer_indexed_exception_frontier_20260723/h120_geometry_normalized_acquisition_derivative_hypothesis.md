# H120 geometry-normalized acquisition derivative

**Status:** Pre-registered 2026-08-08 before computing any oracle path length.

## Eigenquestion

Does H119's apparent acceleration from 22 actions on `tu93` Level 1 to 10
actions on Level 2 reflect lower excess acquisition cost, or only a shorter
level geometry?

## Frozen evidence

- H119 report SHA-256:
  `e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3`.
- Observed segment costs: 22 primitive actions to Level 1 and 10 additional
  primitive actions to Level 2.
- Actor identity: one persistent `gpt-5.6-sol` max-effort session, no injected
  memory or carrier.

## Discriminating test

Use the locally cached MIT-licensed `tu93` environment as an evaluation oracle,
never as actor input. Compute the exact minimum task-completing primitive
action count for Levels 1 and 2 under full game dynamics. For level `i`, define

`excess_i = observed_actions_i - oracle_minimum_i`.

The calculation must preserve enemy dynamics, invalid actions, level identity,
and primitive action cost. It must return a completing witness for each oracle
minimum and replay both witnesses successfully in a fresh local game instance.

## Prediction and dispositions

- Compounding signal: `excess_2 < excess_1` with `excess_1 > 0`.
- Ceiling-limited: `excess_1 = excess_2 = 0`; the observed 22-to-10 decline is
  fully explained by level geometry and supplies no measurable acquisition
  derivative.
- No acceleration: `excess_2 >= excess_1` outside the ceiling case.
- Invalid: the oracle cannot preserve full dynamics or either witness fails
  replay.

## Claim boundary

This retrospective normalization can adjudicate only the two H119 levels. It
does not compare architectures, estimate cross-task transfer, or expose oracle
knowledge to a future actor.
