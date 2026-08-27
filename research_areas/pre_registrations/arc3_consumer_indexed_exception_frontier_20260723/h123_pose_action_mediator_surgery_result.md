# H123 result — a correct action map suppressed the useful probe

Status: **inverted/refuted**.

The exact-byte `pose_only_placebo` arm completed Level 2 in the oracle-minimal
10 actions. The `pose_action_map` arm gained no level and entered `GAME_OVER`
at action 5. The registered outcome is therefore `(causal=0, placebo=1)`.

Both capsules were 1,173 rendered bytes, were injected only on turn 0, matched
the same target grid and single D4 mover, and ran in fresh Sol-max sessions
against fresh local game modules. The audit deterministically replayed every
observation and verified ten successful controller exchanges per arm.

The useful difference was epistemic control. The placebo said the actuator
mapping remained unknown, so the controller chose action 0 as a discriminating
north probe. That probe was also the first move of the optimal route. It then
recognized the left-facing cyan entity as a directional hazard and selected
the lower flank. The map arm received correct actuator semantics, misread the
upper connector as blocked, shifted immediately to route execution, and
approached the hazard head-on.

H123 rejects the recovered action map as a sufficient behavioral mediator. It
also shows why descriptive correctness cannot be the consolidation criterion:
a correct recalled fact can change uncertainty allocation and make the policy
worse. One stochastic pair does not establish that action-map recall is
harmful in the population.

The next discriminating question is whether the shared uncertainty-bearing
D4 mover identity improves fresh acquisition against a neutral, equal-byte
control across repeated matched pairs. That tests the fragment selected by
H123 instead of adding more descriptive state.

Evidence:

- `h123_pose_action_mediator_surgery_result.json` (`2ceb8612a292aa66af7a7c7a5a0c07d608fda8936764ce1a07cc8f5497d4c966`)
- `h123_pose_action_mediator_surgery_audit_result.json` (`e9a681df3d1aae8bf34d14f5427525bece3081d4199f218e3d8bacb6d629bf33`)
- `h123_pose_action_mediator_surgery/pose_action_map_trace.jsonl`
- `h123_pose_action_mediator_surgery/pose_only_placebo_trace.jsonl`
