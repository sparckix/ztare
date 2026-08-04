# Partial-action transport probe result

Date: 2026-07-25

Parent hypothesis: `mechanism_transport_hypothesis.md`

## Outcome

The no-worker governed probe did not advance Level 3. Model usage was zero for
mutator and judge. The environment remained at two completed levels.

The probe produced the preregistered commuting-projection counterexample:

- the active-epoch relation proposed a 13-action witnessed route with zero
  bank-visible ambiguous edges;
- live execution reached an environment degeneration on action 12;
- the sealed slice records that predecessor at
  `non_discharge_edge_indices=[11]`;
- after replanning, a budget-exhausted simulated mechanism search displaced
  the witnessed relation and executed a 46-action continuation;
- the run acquired 44 new evidence rows and the carrier was refuted on current
  evidence at 15,905 / 16,341 exact rows.

Evidence:

- report:
  `projects/arc3_ls20_gov/workspace/arc3_play_loop_report.json`
- sealed slice:
  `projects/arc3_ls20_gov/raw/episodes/eval_slices/eval_20260725T180904835221Z.jsonl`
- sealed slice SHA-256:
  `476dfcc907ed37dd26b17e84a5b08dbfce92524ed0e9558503ac3738c947af69`
- source carrier SHA-256:
  `7d0aa2cd08173b33ce4911e3633e16120440aff9dfe1d0242921d5cae0cde95d`

## Verdict

The partial-action object is useful, but the first control compilation failed
its own transport criterion in two places.

First, control no-goods were owned by a separate predicate and were absent
from the partial-action relation. A source-operation class could therefore
appear single-valued in the graph while having a boundary consequence under
live execution.

Second, the allocator allowed a budget-exhausted carrier simulation to replace
the evidence relation. Its 46-action continuation carried less support than
the witnessed frontier route.

The counterexample changes the next implementation target from adding more
state coordinates to transporting boundary partiality and control precedence
through the same object.
