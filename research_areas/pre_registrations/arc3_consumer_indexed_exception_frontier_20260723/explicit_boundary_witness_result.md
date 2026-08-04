# Explicit boundary witness probe result

Date: 2026-07-25

Parent hypothesis: `explicit_boundary_witness_hypothesis.md`

## Outcome

The explicit witness mechanism passed its named test:

- the previously refuted `0aa941… / operation 3` pair was not targeted;
- the planner selected the preregistered distinct
  `40c8b3… / operation 1` pair;
- the route contained 17 actions and zero compiled ambiguous edges;
- mutator and judge usage remained zero.

Level 3 did not advance. The selected pair supplied another projection
counterexample: action 16 reached a task-open boundary, then the same projected
source/operation produced a law-owned successor after reset. One new evidence
row entered the bank.

Evidence:

- report:
  `projects/arc3_ls20_gov/workspace/arc3_play_loop_report.json`
- sealed slice:
  `projects/arc3_ls20_gov/raw/episodes/eval_slices/eval_20260725T192020752309Z.jsonl`
- sealed slice SHA-256:
  `7bf1c830c86a17a2b8b92116cc26d9d42c5abf8321a17e07136bf95fb9557e7d`
- boundary index: `15`
- carrier score after admission: 15,909 / 16,345 exact rows.

## Verdict

Explicit witnesses repair boundary provenance and prevent repeated targeting
of an admitted non-commuting pair. They do not identify the missing coordinate.
The engine is currently enumerating quotient counterexamples one frontier at a
time. The next lever is to compare the paired presentations and promote the
smallest factor that separates their operation consequences.
