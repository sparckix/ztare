# Reservoir trajectory-order ownership hypothesis

Date: 2026-07-26

Hypothesis ID: `H-ARC3-RESERVOIR-TRAJECTORY-ORDER-20260726-21`

## Eigenquestion

Does evaluating monotonic depletion within each evidence trajectory, rather
than across global archive order, restore the canonical reservoir chart after
the operation-2 boundary?

## Hypothesis

The active component count is nonincreasing within every sealed trajectory
that contains two or more relevant witnesses. Global append order has no
temporal authority across trajectories. Adding explicit sequence identity and
position to reservoir witnesses will restore suffix-zero refinement, eliminate
all four boundary collisions, and return the graph below 160 nodes without
changing any relation or evidence reference.

## Discriminating test

Add optional sequence identity/position to `ReservoirWitness`. Require
monotonicity and at least one strict decrease inside an individual sequence;
retain legacy tuple order only when no sequence metadata exists. Populate the
metadata from `HistoryTrajectoryEvidence`, add an interleaved-trajectories
fixture, and compare pruned/exhaustive selection on the latest sealed evidence.

## Success criterion

- the interleaved fixture rediscovers the same coordinate as each ordered
  trajectory;
- suffix-zero refinement returns zero ambiguity;
- selected graph has fewer than 160 nodes;
- relation/evidence lineage, boundary count, and support identities persist;
- pruned and exhaustive system/context digests match.

## Kill condition

Within-trajectory monotonicity fails, ambiguity remains, node count is at least
160, relation/evidence lineage changes, a boundary crosses sequence identity,
or exhaustive selection disagrees.

## Claim boundary

This repairs evidence-order ownership in a general monotone-coordinate learner.
It supplies no environmental law and does not change the external level
counter.

