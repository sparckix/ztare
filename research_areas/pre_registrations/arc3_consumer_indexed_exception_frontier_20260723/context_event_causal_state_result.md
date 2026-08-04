# Context-event causal-state result

Date: 2026-07-26

Status: falsified before planner implementation

The four suffix-zero collision groups do not share the same reservoir
coordinate. Resolving their evidence refs shows active 2×2 component counts
`3`, `2`, `1`, and `0` across distinct outcomes. In the first three relations,
counts three, two, and one distinguish ordinary, alternate, and epoch-boundary
images. The fourth relation distinguishes consecutive count-one and count-zero
lifecycle rows.

The 22-action suffix is therefore not needed as a persistent entering-event
state. It only isolates a subset on which the existing reservoir learner's
ordering check happens to pass.

The apparatus defect is sequence identity. `ReservoirWitness` currently treats
the tuple's global append order as one temporal trajectory. After several
sealed runs, witnesses from independent trajectories interleave: a count-one
row from an earlier slice may precede count-three rows from later slices. The
coordinate is monotone within each trajectory but not in the concatenated
archive. The learner rejects it and falls back to raw history.

No planner or live-key change was made. H21 tests explicit trajectory-owned
ordering.

