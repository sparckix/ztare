# Reservoir trajectory-order ownership result

Date: 2026-07-26

Status: confirmed

`ReservoirWitness` now carries optional sequence identity and position.
Monotonicity is checked within each sequence, with at least one witnessed
strict decrease. Global tuple order remains the fallback only for legacy
unsequenced evidence. An interleaved-two-trajectory fixture rediscovers the
same component coordinate as an ordered trajectory.

The coordinate's structural digest now identifies its executable projection:
normalized component shape, direction, and area cap. Witness counts and the
outcome-specific threshold remain evidence properties in the receipt rather
than changing coordinate identity.

On the latest sealed evidence, pruned selection evaluated two candidates and
the exhaustive oracle evaluated 66. Both selected:

- action suffix zero;
- context SHA-256
  `2a8fc092a881ad13f137cc465e6fe7ab50afc6e3f62b2d160bb3588a9147b25b`;
- action-system SHA-256
  `71e3d516e97b87d80e0014d03e92e1328a25b5ae65f84dfa09da0d6d78acf99e`.

Their graph and frontier receipts are identical: 130 nodes, 143 relations, 135
deterministic edges, eight typed boundaries, six context transitions, four
contexts, 130 support identities, and zero ambiguity. The prior 240-node graph
was entirely caused by cross-trajectory ordering.

The focused suite passed: 100 tests, 41 deprecation warnings. No environment
action occurred. The external completed-level counter remains two.

