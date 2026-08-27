# H106 persistent multichannel decision judgment

Date: 2026-08-07

Hypothesis:
`H-GPSA-PERSISTENT-MULTICHANNEL-DECISION-JUDGMENT-20260807-106`

Status: pre-registered; offline persistence and selector audit

## Eigenquestion

Can H105's graded external utility survive continual-memory persistence and
enter protocol selection while task credit, external utility, information
yield, and primitive cost retain separate authority?

## Hypothesis

Continual memory can persist H105 utility-arm evidence and rederive graded
judgments at query time. It must not persist a derived preference. A combined
decision judgment may use an exact-measure utility preference when immediate
and delayed terminal-task channels are neutral. Any nonzero disagreement
between task and utility channels must return a neutral conflict.

The planner may consult utility only when the caller declares the exact frozen
utility-measure hash. With no declared measure, a wrong measure, context,
controller, option set, or task, utility remains invisible. Information yield
continues to price the base protocol portfolio and cannot mint a utility or
task preference.

## Discriminating test

1. Start from a legacy v2 continual-memory payload and migrate it with no
   utility evidence.
2. Record the four H95 utility arms from H105, save, and reload.
3. Verify arm hashes and all component values, external values, task statuses,
   costs, measure identities, and evidence refs round-trip exactly.
4. Recompile the two H95 pairs from restored arms at support two.
5. Query the combined judgment under the exact H95 authority and measure.
6. Feed exact judgments into the existing guarded-protocol selector with the
   higher base information-yield score assigned to the H95 placebo option.
7. Repeat without a declared measure and with changed measure, context,
   controller, option set, and task.
8. Add immediate or temporal terminal-task evidence opposing the utility
   preference.
9. Attempt to record a conflicting arm for an existing pair/arm identity.

## Success criterion

1. v2 migration produces zero utility arms and zero utility preference.
2. Four utility arms round-trip byte-for-byte; no derived utility judgment is
   serialized.
3. Restored compilation reproduces two settled pairs, deltas `0.89` and
   `0.07`, and mean `0.48`.
4. Exact H95 causal/placebo judgments are `+1/-1` through the utility channel
   while both task channels remain neutral.
5. Exact utility reranking selects the causal protocol despite the placebo's
   higher base information-yield score.
6. No measure or any authority mismatch restores the baseline selection.
7. A nonzero task/utility disagreement returns neutral conflict.
8. Primitive and control costs are identical before and after reranking.
9. Conflicting pair/arm evidence refuses persistence.
10. Receipts identify each channel and deny authority transfer between them.

## Kill conditions

- a derived utility preference is persisted instead of arm evidence;
- v1 or v2 migration manufactures utility;
- utility is queried without an exact measure identity;
- information yield enters utility support counts;
- task and utility disagreement is resolved by silent precedence;
- a context, controller, task, or complete option-set mismatch receives value;
- selector reranking changes protocol costs; or
- conflicting arm evidence overwrites the earlier receipt.

## Claim boundary

Passing establishes persistent exact-scope multichannel judgment and offline
selector consumption. It does not establish a new ARC environment result,
automatic H104-to-utility settlement, cross-context transport, H97 support, or
benchmark improvement.
