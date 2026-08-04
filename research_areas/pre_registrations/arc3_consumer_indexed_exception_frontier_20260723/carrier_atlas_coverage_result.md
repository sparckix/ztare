# Carrier-atlas coverage result

H68 is refuted.

- Candidate sources discovered: 43
- Compiled projections loaded: 11
- Load failures: 0
- Authoritative completion rows: 14209 and 14254
- Completion rows covered by the union: 14254 only
- Task-open comparison states covered in completed epochs: 0
- Pairwise overlaps: 55

The 11 projection hashes induce the same observed domain-size vector:
`epoch 0 = 0`, `epoch 1 = 6`, `epoch 2 = 1024`. Each projection covers the
same later completion and misses the earlier completion. Pairwise overlap is
therefore duplication within one lifecycle-local chart, not transport between
charts.

The result kills the proposed carrier atlas and identifies a stricter equality
requirement: source-code or projection hashes do not establish distinct
representations when their admitted domains and task-relevant behavior are
extensionally identical.

Evidence:
`carrier_atlas_coverage_audit_result.json`.
