# GP-011 Derived Constraints Lane Seam

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

### Turn 1 — Codex

The core seam was clarified:

- evidence should stay externally grounded
- run-discovered structure should not disappear into prose
- but it also should not be promoted into `evidence.txt`

This established the lane boundary:

- evidence
- derived constraints
- thesis

### Turn 2 — Codex

The main design risk was identified as second-order Goodhart pressure:

- if constraints become prompt-visible, can the mutator steer runs toward favorable constraints?

The architecture answer stabilized around three defenses:

- extract from evaluator-side artifacts, not thesis prose
- require multi-run confirmation before promotion
- keep constraints provenance-separated from source evidence

### Turn 3 — Codex

Implementation boundary stabilized:

- latest run proposals should be preserved separately from the cumulative ledger
- only confirmed constraints should re-enter the mutator prompt
- confirmation should require distinct runs, not duplicate proposals inside one run

### Turn 4 — Codex

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

### Turn 5 — Codex

Local verification passed:

- `py_compile`
- dedicated derived-constraints fixture regression
- existing runtime / compile-evidence regressions

So the seam is no longer “should we build this lane?”

It is now:

- does the lane behave correctly in a real project under repeated runs?
- and does confirmed-constraint feedback help without freezing useful search?
