# H108 pre-live observation-occurrence authority amendment

Date: 2026-08-06

Status: frozen after the Stage-A construction audit and before any H108
controller or environment contact

Applies to:
`H-GPSA-EPOCHAL-INTERVENTIONAL-NERODE-CONSOLIDATION-20260808-108`

## Category correction

The Stage-B wording required fresh observations to be disjoint from H97
training observations. In a deterministic environment restored to the same
prefix, an observation's content hash can recur across independent episodes.
Content equality identifies the environment state; it does not identify the
evidence occurrence that witnessed that state.

H108 therefore binds both identities:

- `pre_observation_content_sha256` may repeat when the restored state repeats;
- `pre_observation_occurrence_sha256` is the hash of the exact parent-state
  identity, pre-proposal identity, and observation-content identity, and must
  be disjoint between training and holdout;
- parent state, proposal, fork, transition, and outcome-evidence identities
  remain disjoint between training and holdout.

This amendment does not relax H108's evidence-separation criterion, feature
catalog, projection library, prediction, support threshold, utility, action
cost, controller, environment, or success threshold. It removes an impossible
cross-episode content-disjointness requirement while strengthening explicit
occurrence authority.

No H108 Stage-B controller or environment contact occurred before this
amendment.
