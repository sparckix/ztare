# Second boundary-source result

Date: 2026-07-26

Parent hypothesis: `second_boundary_source_hypothesis.md`

## Transaction

The no-worker budget-14 probe matched the registered route, source,
operation, policy, consumer action, and boundary distance. It executed all
actions, admitted one row, and sealed
`raw/episodes/eval_slices/eval_20260726T181704475477Z.jsonl` with SHA-256
`66bba69252e75f9cce28c81fbfa4393b6d73b1155ce230bc448f03ab3f3ee0c3`.
The task counter did not change.

Operation `0` stayed in-lifecycle with the same factor effect observed at the
first exclusion source:

`controlled_base translate (-5,0); ordered feasibility -1; ordered budget -1`

This supplies a second context witness for the safe relative translation
program.

## Next frontier

The corrected graph now has `86` control nodes, `83` admission-support
identities, `89` relations, and `83` deterministic edges. Its next
boundary-relevant query is:

- source
  `4ab929993a22db595db68125a854b6e5c70ac5791623119cbddea473b29225c5`;
- known exclusion operation `2`;
- query operation `0`;
- route containing twenty `0`s followed by `[2,0]`;
- exact action count `22`.

Evidence: `second_boundary_source_audit_result.json`.

