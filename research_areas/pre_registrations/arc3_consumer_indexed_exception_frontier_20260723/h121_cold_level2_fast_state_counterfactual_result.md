# H121 result — prior session state mattered in one matched pair

Status: **fast-state supported in one pair**.

The persistent H119 treatment and cold H121 control began from an exactly
equal 64x64 Level-2 grid carrier. The treatment completed in the 10-action
oracle minimum. The cold control completed zero levels.

The cold controller first selected left, spent another action identifying up,
then approached the directional obstacle from its marked side and reached
`GAME_OVER` at action 5. It subsequently inferred that the lower bypass was
needed, but the matched budget was exhausted. Exact deterministic replay
agreed with all ten environment checkpoints.

This pair supports value in prior session state. The likely carried content
includes the action-direction map and relational graph-navigation semantics;
the test does not yet isolate a minimal mediator. The successful treatment
still used no external ZTARE memory or planner, so the result does not supply
architecture lift.

The next discriminator is sparse representation surgery: derive the smallest
Level-1 causal capsule whose one-shot injection makes a fresh Level-2 actor
recover the persistent trajectory or its task result. Credit the capsule by
observed acquisition savings, not by summary plausibility.

Evidence:

- result: `h121_cold_level2_fast_state_counterfactual_result.json`
- raw trace: `h121_cold_level2_fast_state_counterfactual_trace.jsonl`,
  SHA-256
  `cb1247bef8e6d5d15efb7e231c73455b242e027815b37332e3dcaeb10036e71c`
- settlement: `h121_cold_level2_fast_state_counterfactual_settlement.py`

