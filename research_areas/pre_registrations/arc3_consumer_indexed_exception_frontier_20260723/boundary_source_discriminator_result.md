# Boundary-source discriminator result

Date: 2026-07-26

Parent hypothesis: `boundary_source_discriminator_hypothesis.md`

## Transaction

The no-worker probe matched every registered identity:

- policy `boundary_reachability_frontier`;
- consumer action `execute_boundary_source_discriminator`;
- source
  `943c3bdc3d7736f8e4ac3d5b0ef3ebf642c27e845ac8f672270524de8812369e`;
- operation `0`;
- route `[0,0,0,0,0,0,0,0,2,1,1,0]`;
- boundary distance `0`.

It executed all 12 operations, added one persistent row, and sealed
`raw/episodes/eval_slices/eval_20260726T175642003529Z.jsonl` with SHA-256
`ca398a423afd7f6ea3cb355e87ba1e3e34d3c9c9b17718747b89e8712b920c04`.
The external task counter remained at two completed levels.

## Discriminator

Operation `0` stayed inside the lifecycle. Its factor effect is:

`controlled_base translate (-5,0); ordered feasibility -1; ordered budget -1`

with effect SHA-256
`0dcb2fbc994b2b7ff3eff81fa35f668ee454b423625314bdadc003fadacf86e6`.
The acquisition context key remained unchanged.

The source is therefore an operation-specific hazard: operation `3` exits
control, while operation `0` supplies a witnessed safe continuation.

## Next frontier

After admission, the graph has `84` nodes, `87` relations, and `81`
deterministic edges. The next boundary-relevant query is operation `1` at the
same source, reached by:

`[0,0,0,0,0,0,0,0,2,1,1,1]`

Evidence:
`boundary_source_discriminator_audit_result.json`.

