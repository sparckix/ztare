# GP-025 Operator Patching vs. Mutation Discipline Seam

> **Seam metadata** · `seam_id:` GP-025 · `track:` engine · `status:` Closed, 2026-04-14. Operator patching discipline rule is now · `last_updated:` 2026-05-17


## Problem Snapshot

ZTARE is built to mutate and stress-test theses under adversarial pressure. But in live use, the operator and assisting models can also manually patch the thesis file after a score arrives.

That creates a real methodological question:

- when is manual thesis patching legitimate project setup or decontamination?
- when does it become self-defeating interference with the mutation loop?

The FIGS rerun surfaced the issue sharply. A manual rewrite improved audience fit and removed obvious overclaim, but doing that after a scored run risks collapsing the distinction between:

- operator-authored rescue
- engine-driven mutation and search

## Current State

ZTARE currently has no explicit policy here.

In practice, several kinds of manual editing are mixed together:

- seed-thesis creation before first run
- charter and rubric refinement
- raw evidence authoring
- emergency removal of an obviously unearned numeric bridge
- ordinary post-score thesis rewriting

Some of these are clearly compatible with ZTARE. Some are much closer to overriding the experiment.

## Debate Log

### Turn 1, Operator position

The operator surfaced the core objection directly:

- patching the thesis is self-defeating versus ZTARE mutation
- if the operator keeps repairing the thesis after every score, the loop becomes partly artisanal again
- that undermines what the engine is supposed to demonstrate

### Turn 2, Why this is not trivial

There is a real boundary problem here.

Not all manual edits are equal:

- editing `raw/` is evidence curation
- editing the charter is object definition
- editing the rubric is scoring-contract definition
- editing `test_model.py` can be falsification-environment definition
- editing the live thesis after a score is much more dangerous, because it can directly substitute operator judgment for mutator search

So “never edit anything manually” is too broad, but “manual patching is always fine” is clearly wrong.

### Turn 3, The FIGS lesson

The FIGS rerun clarifies the line:

- a case-method audience framing rewrite before serious live iteration is plausibly a seed-phase audience alignment step
- once the project is live and scored, repeated manual thesis patching would blur whether the project is being improved by the engine or by operator intervention

That means the real seam is phase discipline, not a total ban.

### Turn 4, Candidate policy shapes

Three plausible policies exist:

1. **Allow Manual Thesis Patching Freely**
   - simple
   - but collapses the experiment into assisted rewriting

2. **Ban Manual Thesis Patching Entirely**
   - maximally clean
   - but too rigid because seed-phase drafting and occasional decontamination are real needs

3. **Phase-Bounded Manual Patching**
   - allow manual thesis creation and major reframing only:
     - before first scored run
     - or after an explicit phase reset / new regime declaration
   - once a project is in active scored iteration, improvements should come through the mutator, not artisanal rewriting

### Turn 5, Current conclusion

Option 3 is the right discipline.

The likely future policy is:

- operator may manually edit:
  - `raw/`
  - `project_charter.md`
  - rubric
  - `test_model.py`
  - seed thesis before first scored run
- operator should not keep manually patching `thesis.md` / `current_iteration.md` after scores start arriving unless:
  - declaring a new project phase
  - resetting the seed explicitly
  - or removing a clearly invalid artifact of setup rather than “improving the answer”

That keeps ZTARE from becoming a hidden co-writing loop while preserving legitimate project construction.

## Status

Closed, 2026-04-14. Operator patching discipline rule is now in AGENTS.md §7 (do not artisanally patch a running loop; improvements come through the mutator). Standing rule covers the original problem. Stale-active status corrected on visibility audit.
