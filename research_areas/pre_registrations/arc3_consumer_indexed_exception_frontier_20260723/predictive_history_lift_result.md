# Predictive action-history lift result

Date: 2026-07-25

Parent hypothesis: `predictive_history_lift_hypothesis.md`

## Outcome

The no-worker acquisition probe executed the selected witnessed route
`[0, 1]` from the verified Level 3 seed. It gained no level and added no new
frame transition:

- `levels_gained = 0`;
- `evidence_grown_by = 0`;
- task discharge remained open;
- the ordered two-transition slice was archived as
  `raw/episodes/eval_slices/eval_20260725T194809829605Z.jsonl`,
  SHA-256
  `33dd32572b5526f354959559f2657f079fb69cd44697867216248abd430657b1`.

The planner did not traverse an ambiguous relation. The observed partial
action route reported zero ambiguous edges on its path.

## Discriminator

The live-equivalent sealed lineage does not support the preflight claim that
an action suffix eliminates every boundary-contaminated non-commutation:

- frame-only state: two boundary-contaminated non-commuting relations;
- suffix length one: one such relation;
- every tested suffix through length 32: the same one relation remains.

The shortest minimum-ambiguity action suffix is length one, but its minimum is
nonzero. The probe therefore falsifies action-only history as a sufficient
predictive state for the admitted evidence.

## Consequence

The missing state cannot be recovered from the operation sequence alone.
The next discriminating lift must retain the observed mechanism effect of
prior operations. That is a recursively updated, substrate-neutral state:
`history' = suffix(history + (operation, observed_effect))`.

Evidence:
`projects/arc3_ls20_gov/workspace/arc3_acquisition_probe_report.json`.

## Supersession after section-identity repair

The nonzero minimum above was produced by compiling each sealed boundary
twice: once inside its ordered trajectory and once as an explicit edge whose
history field was incomplete. Those are two presentations of one evidence
witness, not independent observations. Deduplicating them by evidence
reference and applying the lifecycle reset makes action suffix length one
boundary-commuting on the current sealed lineage.

The no-growth outcome of the `[0, 1]` probe remains valid. The inference that
action-only history is insufficient is superseded by
`operation_effect_history_result.md`.
