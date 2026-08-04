# Boundary-complete transport probe result

Date: 2026-07-25

Parent hypothesis: `boundary_transport_hypothesis.md`

## Outcome

Level 3 did not advance. Mutator and judge usage remained zero.

The first planning leg executed the proposed 15-action route and reached an
environment degeneration on action 14. After reset, the next planning leg
selected the same abstract source digest and operation as a one-action
frontier and acquired a normal transition.

This is a direct non-commutation witness:

- abstract source digest:
  `0aa941c92983b390b8dceaf7c60ed536d70f5482107d4e349fb57f4331f2cebb`
- operation: `3`
- presentation A consequence: task-open boundary;
- presentation B consequence: law-owned successor.

The run acquired three rows. The carrier remained refuted on current evidence
at 15,908 / 16,344 exact rows.

Evidence:

- report:
  `projects/arc3_ls20_gov/workspace/arc3_play_loop_report.json`
- sealed slice:
  `projects/arc3_ls20_gov/raw/episodes/eval_slices/eval_20260725T185747154114Z.jsonl`
- sealed slice SHA-256:
  `d32307a124ece41dc6a99cd56531fd2ae825fdd9f226649b2b00160b2349ad7e`
- boundary index: `13`

## Verdict

The preregistered kill condition fired. Passing a boolean exclusion predicate
into the law-scored transition compiler is insufficient because boundary rows
are intentionally outside that law-owned view. The relation therefore cannot
represent the very witness that should make the quotient non-commuting.

The boundary witness has a distinct identity and lifecycle. It must be carried
alongside law transitions as an explicit partial-operation observation, with
its sealed evidence reference, rather than recovered by relabeling or by a
predicate over rows that remain in the law bank.
