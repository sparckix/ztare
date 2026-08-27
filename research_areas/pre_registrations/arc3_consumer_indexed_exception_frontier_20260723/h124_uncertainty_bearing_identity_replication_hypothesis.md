# H124 uncertainty-bearing identity replication

**Status:** Settled 2026-08-08 as refuted (`treatment=0/3`, `control=0/3`).
Pre-registered before any H124 controller session was created.

## Eigenquestion

Did H123 select a reusable behavioral mediator—the D4 mover identity with
actuator uncertainty preserved—or did its successful placebo reflect one
session draw?

## Frozen evidence

- H123 result SHA-256:
  `2ceb8612a292aa66af7a7c7a5a0c07d608fda8936764ce1a07cc8f5497d4c966`.
- H123 audit SHA-256:
  `e9a681df3d1aae8bf34d14f5427525bece3081d4199f218e3d8bacb6d629bf33`.
- Exact Level-2 grid-carrier SHA-256:
  `dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24`.
- Exact local-dynamics oracle minimum: 10 charged actions.
- The H123 `pose_action_map` revision is quarantined for this test. It cannot
  be included in either arm.

## Intervention

Run three independent matched pairs. Every arm receives a fresh Sol-max
session, a fresh local game module, the same exact Level-2 start grid, a
10-action budget, and one turn-0 capsule.

`uncertainty_bearing_identity` reuses the H123 successful fragment:

- one D4 orbit identifies the controlled 3x3 color-9 component with its
  color-4 pose marker;
- four actuator indices were observed, but their directional assignment is
  withheld and must be inferred locally;
- no source coordinate, target route, hazard rule, or target action sequence
  is supplied.

`neutral_uncertainty_control` supplies the same source provenance, schema,
uncertainty directive, refusal surface, and target start evidence, but no
source-to-target object-role compatibility claim and no action assignment.
It requires both the controlled component and action directions to be inferred
locally.

Within every pair, rendered capsule bytes must be exactly equal. The capsule
pair hash chooses the order of replication 1 and replication parity alternates
that order, giving deterministic counterbalancing before any session starts.
Sessions, modules, reports, and traces cannot cross arms.

**Pre-contact order amendment:** the first implementation hashed each
replication independently and preflight produced treatment-first in all three
pairs. With no output directory, report, trace, or controller session yet
created, the rule was replaced by the counterbalanced rule above. Capsule
content, byte matching, endpoints, and dispositions did not change.

**Post-failure replacement rule:** replication 3 control returned transport
code 124 on its second call, after one recorded action and before an endpoint.
The registered trace-failure rule invalidates the whole pair; its treatment
and partial control are excluded. One complete replacement pair, replication
4, will run both arms fresh in the next alternating order (`control`, then
`treatment`). The original three-pair thresholds remain unchanged and are
applied to complete pairs 1, 2, and 4. The failed trace is retained as evidence
and no partial observation enters the endpoint.

**Post-audit carrier correction:** replication 4 deserialized capsules from a
`sort_keys=True` manifest before compact rendering. Content and arm lengths
remained matched at 1,431 bytes, but the rendered treatment/control hashes
became `8f71cc...`/`a0ca89...` instead of the frozen
`d4ba28...`/`e02880...`. The registered mismatch rule invalidates pair 4.
Its provisional result (`d05600...`) is withdrawn and retained only through
the pair-4 traces. One final complete replacement pair, replication 5, will
rebuild the capsules from code, verify their frozen hashes before contact, and
run in the continuing alternating order (`treatment`, then `control`). Fixed
thresholds apply to complete pairs 1, 2, and 5. No pair-4 outcome enters the
endpoint.

## Prediction and disposition

Primary endpoint: binary level completion within 10 charged actions.

- **Supported:** treatment completes at least two of three arms and exceeds
  control completions by at least two.
- **Refuted:** control completions are greater than or equal to treatment
  completions.
- **Inconclusive:** every other valid outcome.

Secondary readouts are first action, lower-branch choice by action 4,
`GAME_OVER` incidence, and exact action cost. They explain the endpoint but do
not change the registered disposition.

H123 and H121 are contextual observations and are excluded from the H124
primary count. A capsule mismatch, start-grid mismatch, repeated recall,
unstable session, trace failure, or module reuse invalidates the affected pair.

## Claim boundary

Success would establish a repeated within-game cross-level acquisition effect
for one selected uncertainty-bearing identity fragment. It would not establish
cross-game transfer, multi-generation compounding, population calibration,
broad capability gain, or literature novelty.
