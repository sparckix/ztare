# GP-020 Supervising-Agent Closure Discipline Spec

## Status

Blocked

## Scope

- turn supervising-agent stop/close recommendations into a typed, reviewable surface
- define the handoff boundary between artisanal and supervisor work
- prepare the project-type contract for future supervisor-mediated self-review

Does not cover:

- full autonomous self-review implementation
- model training or fine-tuning
- replacing operator review on frontier research immediately

## Decision

Do not treat GP-020 as a vague humility reminder.

Treat it as a missing contract surface:

- closure judgment must become typed and reviewable
- artisanal-to-supervisor handoff needs explicit rules
- recursive self-review requires a project type, not just better prose advice

## Problem

The current supervising agent can still make strong stop/close recommendations based on narrative interpretation rather than measured evidence.

That creates three risks:

- premature shutdown of viable search
- endless artisanal drift when a project is already contract-ready
- overclaiming what the supervisor architecture is currently capable of doing

## Why It Matters

This seam is load-bearing for both:

- paper 4's claim about recursive epistemic gain
- the future supervisor project class for self-review

Without GP-020, the operator remains the hidden closure mechanism.

## Constraints

- must distinguish local exhaustion from global exhaustion
- must not let “unknown topology” justify indefinite looping
- must preserve operator involvement where the catch taxonomy is not yet explicit
- should build on existing typed surfaces rather than invent an entirely new parallel system

## Options

### Option A — Leave Closure As Narrative Guidance

**Description**

Keep closure/stop recommendations in philosophy notes and operator judgment.

**Pros**

- low effort
- flexible

**Cons**

- not auditable
- not replayable
- cannot scale into supervisor project typing

**Verdict**

Not enough.

### Option B — Typed Closure Signals + Project-Type Boundary

**Description**

Introduce typed closure/handoff signals and use them to define when work stays artisanal versus when it becomes supervisor-ready.

**Pros**

- auditable
- compatible with current artifacts
- creates the bridge toward supervisor self-review projects

**Cons**

- still needs live examples and a verifier
- depends on nearby items closing first

**Verdict**

Recommended.

## Recommendation

Sequence GP-020 after the nearby verifier items close enough:

- GP-017
- GP-021
- GP-022

Use the recent operator / Claude / Codex thread as the seed dataset.

First slice should likely define:

- typed closure recommendation categories
- typed reason classes
- artisanal vs supervisor handoff criteria
- a minimal verifier using known historical catches

## Implementation Sketch

Phase 1:

- freeze the labeled failure families from recent artisanal threads
- define closure recommendation categories and reason classes
- define the project-type boundary for:
  - exploratory/artisanal
  - execution/supervisor
  - self-review/supervisor

Phase 2:

- add typed closure fields to the relevant evaluation / orchestration surfaces
- test against historical known misses

Phase 3:

- open the first supervisor self-review project type

## Open Questions

- which existing artifact should own closure signals?
- should GP-020 live in validator output, supervisor output, or both?
- what is the minimal verifier that proves real gain without overbuilding?
