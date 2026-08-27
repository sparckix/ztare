# H124 result — identity improved the first decision but did not compose

Status: **refuted**.

Across three canonical-byte matched pairs (replications 1, 2, and 5), both the
uncertainty-bearing D4 identity arm and the neutral control completed zero of
three Level-2 runs. Every arm used one fresh Sol-max session, one fresh game
module, a 10-action budget, and one turn-0 capsule. Deterministic replay matched
all observations.

The treatment did affect a subordinate decision: all three treatment sessions
chose the correct first action (`up`), while only one of three controls did.
That effect did not reach the task endpoint. Treatment sessions either spent
extra actions resolving actuator direction or chose the fatal direct approach
at the branch. No treatment selected the lower flank by action 4.

This rejects pose-quotiented mover identity as the sufficient compounding unit
and shows why terminal-only or semantic-only credit is too coarse. The identity
fragment can improve self-localization and the first intervention while still
failing to compose with the missing relational-affordance judgment. The next
architecture step must represent the relation among agent bearing, another
object's pose, contact direction, terminal risk, and a viability-preserving
alternative route.

Replication 3 was excluded after control transport code 124 before an endpoint.
Replication 4 was excluded because manifest deserialization changed compact
prompt key order and therefore violated frozen capsule hashes. Both traces are
retained. Replication 5 used code-rebuilt capsules whose prompt hashes matched
the frozen receipt.

Evidence:

- `h124_uncertainty_bearing_identity_replication_result.json`
  (`86a72142e1e47f4ad521bc283b27ac95d4262b854ace8f3ac84f085522b16457`)
- `h124_uncertainty_bearing_identity_replication_audit_result.json`
  (`cfde30df1e2241dc46eeefd4f9b4377df0955a9402c843645aea5e1c970841a6`)
- `h124_uncertainty_bearing_identity_replication_audit.py`
- `h124_uncertainty_bearing_identity_replication/`
