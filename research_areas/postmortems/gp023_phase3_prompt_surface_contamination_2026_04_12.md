# GP-023 Phase 3 Prompt-Surface Contamination Post-Mortem

**Timestamp:** 2026-04-12 22:04:40 EDT
**Project:** `gp023_planck_sandbox_03`
**Classification:** pre-run seal contamination failure
**Author:** Codex

## Summary

Phase 3 did not suffer from a single leak. It suffered from a sequence of prompt-surface audit failures caused by sealing too early and auditing the scoring surface more carefully than the mutator-visible surface.

The initial seal was premature because mutator-visible files still exposed:

1. hidden-generator constants in `thesis.md` / `current_iteration.md`
2. the same hidden-generator constant in `test_model.py`
3. direct ontology leakage in `project_charter.md`
4. residual hidden-basin tokens inside HTML comments in `thesis.md` / `current_iteration.md`

No live Phase 3 run had started when this post-mortem was written. The sandbox was corrected before launch and then validly resealed.

## Leak Sequence

### Leak 1: Prose seed leak

Files:

- `projects/gp023_planck_sandbox_03/thesis.md`
- `projects/gp023_planck_sandbox_03/current_iteration.md`

What leaked:

- hidden-generator `p = 2.7`
- explicit `~0.08` floor anchor

Why it mattered:

- both files are injected verbatim into the mutator prompt
- those values were stronger than the visible evidence alone justified

### Leak 2: Seed code leak

File:

- `projects/gp023_planck_sandbox_03/test_model.py`

What leaked:

- `MODEL_PARAMS["p"] = 2.7`

Why it mattered:

- `test_model.py` is prompt-visible even though the frozen harness owns deterministic scoring
- the packet became internally inconsistent after the prose fix (`p = 1.5` in prose, `p = 2.7` in code)

### Leak 3: Charter ontology/path leak

File:

- `projects/gp023_planck_sandbox_03/project_charter.md`

What leaked:

- `Planck` in title
- `Planck` in program line
- operator-side paths containing `gp023_planck_sandbox_03`

Why it mattered:

- the charter is injected verbatim into the mutator prompt
- this was a direct hidden-basin ontology leak in the exact file that forbids named imports

### Leak 4: Comment metadata leak

Files:

- `projects/gp023_planck_sandbox_03/thesis.md`
- `projects/gp023_planck_sandbox_03/current_iteration.md`

What leaked:

- `<!-- seed_iteration: gp023_planck_sandbox_03_iter0 -->`

Why it mattered:

- comments are still prompt tokens if the mutator can read them
- the string carried the hidden-basin token even after the visible prose body was cleaned

## Corrections Applied

At 2026-04-12 21:49:19 EDT:

- patched `thesis.md` / `current_iteration.md`
- `p = 2.7 -> 1.5`
- explicit floor anchor replaced with provisional language

At 2026-04-12 21:54:36 EDT:

- patched `test_model.py`
- `MODEL_PARAMS["p"]: 2.7 -> 1.5`

At 2026-04-12 21:59:40 EDT:

- scrubbed `project_charter.md`
- removed `Planck` from header/program
- removed operator-side pre-registration path
- reduced binding artifact reference to bare filename

At 2026-04-12 22:04:40 EDT:

- removed residual HTML comment metadata from `thesis.md` / `current_iteration.md`

These were prompt-surface decontamination fixes only.

Nothing changed in:

- visible evidence
- hidden evidence
- frozen harness logic
- rubric logic
- charter gate block semantics

## Verification After Final Correction

After the final correction set:

- `python projects/gp023_planck_sandbox_03/harness_smoke_gate.py` -> PASS
- seed still fails visible assertions as intended
- 9/9 deterministic gates still emit finite `actual` values and fail as expected on the naive seed
- charter parser still extracts all 9 declared gates
- asymptotic-contract parser still extracts `asymptotic_claim: true` and `farther_tail_contract: true`
- no remaining `Planck` or `gp023_planck_sandbox_03` string remains anywhere in the full mutator-visible packet:
  - `evidence.txt`
  - `thesis.md`
  - `current_iteration.md`
  - `test_model.py`
  - `project_charter.md`
- no remaining prompt-facing `p = 2.7` or explicit `~0.08` floor anchor remains anywhere outside hidden generator artifacts

## Root Cause

This was a Codex process failure.

The concrete mistakes:

1. I fixed leaks incrementally instead of doing a literal full-packet mutator-visible sweep before sealing.
2. I audited the scoring surface more carefully than the prompt surface.
3. I treated `test_model.py` as "safe enough" because the frozen harness owns deterministic scoring.
4. I treated `project_charter.md` primarily as a parser contract rather than as prompt text.
5. I treated comments/metadata as non-semantic even though the mutator still reads them as tokens.

Compactly:

> I audited what the machine executes more carefully than what the mutator sees.

## Meta Lessons

1. For contamination review, the unit of audit is the **entire mutator-visible packet**, not only the files that own scoring.
2. Frozen-harness preference does not reduce prompt-contamination obligations.
3. Charter files are prompt surface first and parser contracts second for leak-audit purposes.
4. Comments, markdown metadata, and operator breadcrumbs count as prompt tokens if they are in a mutator-visible file.
5. Pre-seal review must end with a literal grep sweep over all mutator-visible files for:
   - hidden-basin names
   - operator-side path strings
   - suspicious copied generator constants
6. A seal is not valid until that packet-level sweep has passed on the exact files to be run.

## Seal Consequence

The 2026-04-12 21:50:02 EDT seal, the 2026-04-12 21:54:36 EDT reseal, and the 2026-04-12 21:59:40 EDT reseal are all superseded.

The valid seal is the post-comment-scrub reseal recorded at 2026-04-12 22:04:40 EDT in:

- `research_areas/private/seams/GP-023_planck_sandbox_03_pre_registration.md`
- `projects/gp023_planck_sandbox_03/project_charter.md`
