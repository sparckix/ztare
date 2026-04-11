# GP-026 Runner No-Suite Rejection Spec

## Status

Draft

## Scope

- reject malformed mutation candidates that omit a usable Python falsification suite
- reject explicit sentinel fallback suites before evaluation
- add a regression surface for this specific runner failure mode

Does not cover:

- broader semantic quality checks on the Python suite
- mutation-declaration enforcement for all non-V4 projects
- reclassifying all unit-test failures as runner rejections

## Decision

Candidates without a usable Python falsification suite should be rejected at Runner R1 before `test_thesis.py` runs.

This includes:

- no Python block at all
- empty Python block
- explicit sentinel no-suite block

## Problem

The current fallback writes:

```python
assert False, 'AI failed to provide a testable falsification suite.'
```

to `test_model.py` and then evaluates the candidate normally.

That preserves rigor but at the wrong layer. It causes malformed candidates to:

- consume loop budget as scored iterations
- overwrite latest artifacts
- add noise to long hardening runs

## Why It Matters

Long runs should explore bad theses, not malformed runner artifacts.

If this is left unchanged:

- oscillation traces become harder to interpret
- malformed candidates are mixed with genuine adversarial failures
- latest artifacts can be temporarily overwritten by infrastructure failures

If fixed:

- fail-closed behavior remains intact
- malformed candidates are cleanly separated as runner rejections
- champion/latest artifacts better reflect meaningful thesis search

## Constraints

- preserve fail-closed rigor
- do not silently accept missing suites
- keep the guard narrow and deterministic
- keep the first patch lightweight

## Recommendation

Introduce a small pure helper that validates the Python suite candidate before evaluation.

Validation rules:

- `None` or empty -> reject
- exact sentinel string -> reject

Wire this into `_prepare_mutation_candidate()` so the existing Runner R1 rejection path handles it.

## Implementation Sketch

### Step 1 — Add pure suite guard helper

- new module: `src/ztare/validator/mutation_suite_guard.py`
- expose:
  - `NO_SUITE_SENTINEL`
  - `validate_python_suite_candidate(python_code)`

### Step 2 — Call guard during mutation preparation

- in `_prepare_mutation_candidate()`
- raise `ValueError` before candidate write/eval if suite is missing or sentinel

### Step 3 — Remove sentinel fallback write

- delete the branch that writes sentinel `assert False` to `test_model.py`
- rely on Runner R1 rejection instead

### Step 4 — Add regression

- new fixture regression:
  - `src/ztare/validator/runner_r1_suite_guard_fixture_regression.py`
- cases:
  - valid suite passes
  - missing suite rejects
  - empty suite rejects
  - sentinel suite rejects

## Open Questions

- should obviously trivial but non-sentinel suites also be rejected here, or is that for a later seam?
- should malformed suite rejections be written into a dedicated runner-events artifact?
- should the loop summary count Runner R1 malformed-suite rejections explicitly?
