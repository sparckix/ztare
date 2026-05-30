# GP-011 Derived Constraints Lane Seam

> **Seam metadata** · `seam_id:` GP-011 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-17


## Problem Snapshot

ZTARE had a clean boundary between:

- primary evidence in `evidence.txt`
- the active thesis in `thesis.md` / `current_iteration.md`

but no proper home for run-discovered structural limits.

Those limits were leaking across three weak surfaces:

- weakest-point strings in logs
- debate prose
- operator memory

That meant the system could discover a structural rule in one run, but had no typed way to preserve it for later runs without polluting source evidence.

## Current State

First implementation slice is now shipped:

- evaluator emits typed `derived_constraints`
- latest proposals persist to:
  - `workspace/latest_constraint_proposals.json`
- cross-run ledger persists to:
  - `workspace/derived_constraints.json`
- human-readable summary persists to:
  - `workspace/derived_constraints_brief.md`
- the mutator receives confirmed constraints as read-only context

What remains is live verification that:

- repeated constraints confirm across distinct runs
- confirmed constraints improve search discipline without becoming a new gaming surface

## Debate Log

### Turn 1, Codex

The core seam was clarified:

- evidence should stay externally grounded
- run-discovered structure should not disappear into prose
- but it also should not be promoted into `evidence.txt`

This established the lane boundary:

- evidence
- derived constraints
- thesis

### Turn 2, Codex

The main design risk was identified as second-order Goodhart pressure:

- if constraints become prompt-visible, can the mutator steer runs toward favorable constraints?

The architecture answer stabilized around three defenses:

- extract from evaluator-side artifacts, not thesis prose
- require multi-run confirmation before promotion
- keep constraints provenance-separated from source evidence

### Turn 3, Codex

Implementation boundary stabilized:

- latest run proposals should be preserved separately from the cumulative ledger
- only confirmed constraints should re-enter the mutator prompt
- confirmation should require distinct runs, not duplicate proposals inside one run

### Turn 4, Codex

First slice implemented in code:

- `src/ztare/validator/derived_constraints.py`
- `src/ztare/validator/derived_constraints_fixture_regression.py`
- prompt/schema wiring in:
  - `src/ztare/validator/test_thesis.py`
  - `src/ztare/validator/autoresearch_loop.py`

Artifacts now exist:

- `latest_constraint_proposals.json`
- `derived_constraints.json`
- `derived_constraints_brief.md`

### Turn 5, Codex

Local verification passed:

- `py_compile`
- dedicated derived-constraints fixture regression
- existing runtime / compile-evidence regressions

So the seam is no longer “should we build this lane?”

It is now:

- does the lane behave correctly in a real project under repeated runs?
- and does confirmed-constraint feedback help without freezing useful search?

### Turn 6, Claude (2026-04-21)

Two bugs found in live qualitative project (seattle_tech_housing, ~40 iterations):

**Bug 1: Confirmation never fires on qualitative projects.**
The signature hash uses exact-text match on `constraint + applies_to + failure_family`. For math/deterministic projects, the judge is stable enough that the same constraint recurs with identical text. For qualitative/policy projects, the judge rephrases naturally each iteration, same failure family, different surface text → different hash → constraint stays provisional forever. Result: 87 provisional constraints, 0 confirmed, zero injection into mutator prompt. The “never repeat this failure” memory was completely inert for the entire run.

Fix: expose `confirmation_threshold_runs` as a rubric flag (default 2, unchanged for existing projects). Qualitative project rubrics can set it to 1 to confirm on first appearance. `_refresh_derived_constraints_from_eval` now reads `rubric_data.get(“confirmation_threshold_runs”, 2)` and passes it through.

**Bug 2: Prompt injection uncapped.**
`render_confirmed_constraints_prompt_section` dumped all confirmed constraints into the prompt with no limit. At 87 confirmed, this would be massive context overhead.

Fix: sorted by `seen_count_runs` descending, capped at top 20. High-repetition constraints (the ones the judge actually keeps returning to) get priority.

**Live evidence for qualitative projects:** seattle_tech_housing top constraints after 40+ iterations are all variants of the aggregate fallacy family, `distributional_inference_from_aggregates`, `false_positive_negative_on_distributional_harm`, `aggregate_fallacy`. These represent a genuine structural constraint: the thesis cannot earn causal attribution points without stratum-level peer comparison data. The constraint lane correctly identified this as the binding constraint across all iterations.
