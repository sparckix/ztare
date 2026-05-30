# GP-025 Operator Patching vs. Mutation Discipline Spec

## Status

Draft

## Scope

- define the policy boundary between legitimate operator setup and self-defeating thesis patching
- clarify which project surfaces may be manually edited during active work
- propose lightweight enforcement or logging options for later implementation

Does not cover:

- full supervisor enforcement of the policy
- retroactive cleanup of old projects
- banning manual evidence authoring or charter work

## Decision

ZTARE should adopt a phase-bounded policy:

- manual thesis authoring is allowed during seed/setup
- manual thesis rewriting is allowed only at explicit phase resets or decontamination boundaries
- once a project is in active scored iteration, thesis improvement should come through mutation, not operator patching

This should initially be adopted as a workflow rule and documented discipline. Later, if needed, it can become a logged or enforced contract in the validator.

## Problem

Without a boundary here, the operator can unintentionally launder artisanal rewriting into an engine result.

That breaks the interpretability of:

- improvement traces
- mutation efficacy
- paper claims about recursive gain

At the same time, a total ban on manual edits is too rigid, because projects require:

- seed drafting
- object definition
- evidence curation
- falsification-environment construction

The system therefore needs a narrower distinction: not “manual vs automated,” but “which layer is being manually changed, and in which phase?”

## Why It Matters

If this stays ambiguous:

- live projects become hard to interpret
- score gains can no longer be attributed clearly
- operator intervention can silently substitute for mutation search
- paper-level claims about the engine become weaker

If this is clarified:

- project traces stay more auditable
- operator work remains legitimate where it belongs
- mutation results become easier to trust and compare

## Constraints

- do not forbid manual work on `raw/`, charter, rubric, or suite definition
- do not assume all thesis edits are bad; seed-phase drafting is necessary
- do not create a rigid enforcement surface before the workflow rule is understood
- keep the first version lightweight and operator-usable

## Options

### Option A — No Policy

**Description**

Leave manual patching entirely to operator judgment.

**Pros**

- flexible
- zero engineering work

**Cons**

- weak auditability
- hidden artisanal rescue remains easy
- blurs mutation efficacy

**Verdict**

Rejected.

### Option B — Total Ban On Manual Thesis Editing

**Description**

Forbid manual edits to `thesis.md` once a project exists.

**Pros**

- very clean experimental boundary

**Cons**

- too rigid
- blocks legitimate seed drafting and reset events
- creates awkward workarounds

**Verdict**

Rejected.

### Option C — Phase-Bounded Thesis Discipline

**Description**

Allow manual thesis edits:

- before first scored run
- at explicit phase resets
- for decontamination of obviously invalid setup artifacts

Otherwise treat post-score thesis improvement as mutator territory.

**Pros**

- preserves auditability without freezing setup work
- matches real operator workflow
- keeps the experiment interpretable

**Cons**

- requires clear reset semantics
- still depends on operator honesty until enforcement exists

**Verdict**

Recommended.

## Recommendation

Adopt Option C as workflow policy now.

Immediate rule:

- manual edits are encouraged for:
  - `raw/`
  - `project_charter.md`
  - rubric
  - `test_model.py`
  - seed thesis before first scored run
- manual edits to `thesis.md` / `current_iteration.md` after scored iteration begins should be treated as exceptional and explicitly phase-changing

If the operator wants to restart from a manually rewritten thesis, that should be treated as:

- a new seed
- or a declared regime / phase reset

not as a seamless continuation of the same mutation trace.

## Implementation Sketch

### Step 1 — Document The Workflow Rule

Add the rule to the operator manual and project workflow docs:

- seed phase: manual thesis drafting allowed
- active mutation phase: thesis changes come from mutator
- reset phase: manual rewrite requires explicit declaration

### Step 2 — Add Lightweight Trace Metadata

Introduce optional metadata such as:

- `last_manual_thesis_edit_at`
- `phase_reset_declared`
- `operator_seed_reset_reason`

This can begin as provenance in project artifacts before any enforcement is added.

### Step 3 — Consider Soft Guardrails

Future validator/operator UX could:

- warn if `thesis.md` changed outside mutation output after scoring started
- ask whether this is a reset event
- stamp the next run as a fresh baseline instead of a continuous iteration

### Step 4 — Leave Hard Enforcement For Later

Do not hard-block the operator yet.

First verify that the workflow rule is actually useful in live projects across the current private and forecasting runs.

## Open Questions

- what exactly counts as “decontamination” versus ordinary answer improvement?
- should `current_iteration.md` be treated more strictly than `thesis.md`?
- should a post-score manual thesis edit automatically trigger a new baseline / regime fingerprint?
- should this eventually become part of GP-020 supervisor closure discipline instead of a separate policy lane?
