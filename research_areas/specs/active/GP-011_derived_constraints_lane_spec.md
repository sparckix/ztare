# GP-011 Derived Constraints Lane Spec

## Status

Verify

## Scope

- preserve run-discovered structural limits as a first-class typed object
- keep derived constraints provenance-separated from source evidence
- feed only confirmed constraints back into the mutator as read-only context

Does not cover:

- automated librarian/source-hunting from constraints
- cross-project constraint mining
- hard scorer penalties for violating a confirmed constraint

## Decision

Adopt a distinct derived-constraints lane with three artifacts:

- latest proposals from the newest run
- cumulative ledger across runs
- human-readable brief

Do not inline derived constraints into `evidence.txt`.

## Problem

ZTARE could discover structural limits through adversarial evaluation, but had no durable typed lane for preserving them.

That created a false choice:

- lose them in logs and prose
- or contaminate primary evidence with run-derived structure

Both were wrong.

## Why It Matters

The system is now good enough at surfacing real structural constraints that losing them is a real capability failure.

Without a typed lane:

- the mutator re-discovers the same limits repeatedly
- operators manually carry structural lessons across runs
- future librarian workflows have no structured research object downstream of evaluation

## Constraints

- must preserve provenance separation from `evidence.txt`
- must avoid same-run duplicate proposals becoming “confirmed”
- must keep first slice lightweight and auditable
- only confirmed constraints should influence future mutation

## Options

### Option A — Inline Into `evidence.txt`

**Description**

Append run-derived constraints into the main evidence corpus.

**Pros**

- no new artifact types
- immediately visible everywhere

**Cons**

- collapses provenance
- makes run-derived structure look externally verified
- pollutes the evidence boundary and score regime

**Verdict**

Rejected.

### Option B — Separate Typed Lane

**Description**

Store derived constraints in dedicated workspace artifacts and feed confirmed constraints back to the mutator as labeled, read-only context.

**Pros**

- clean provenance
- machine-readable accumulation across runs
- supports future research/librarian tooling
- keeps evidence and structure distinct

**Cons**

- adds another artifact family
- still needs live verification against gaming / overfreezing risk

**Verdict**

Recommended.

## Recommendation

Use a separate typed derived-constraints lane.

Current implementation:

- evaluator emits `derived_constraints`
- latest proposals persist to:
  - `projects/<project>/workspace/latest_constraint_proposals.json`
- cumulative ledger persists to:
  - `projects/<project>/workspace/derived_constraints.json`
- summary persists to:
  - `projects/<project>/workspace/derived_constraints_brief.md`
- confirmed constraints are injected into the mutator prompt as:
  - `CONFIRMED DERIVED CONSTRAINTS (READ-ONLY)`

Confirmation rule:

- proposals must recur across at least `2` distinct runs before promotion to confirmed

## Implementation Sketch

Phase 1:

- add typed proposal schema to evaluator output
- persist latest proposals
- build cumulative ledger with distinct-run confirmation
- render confirmed constraints into the mutator prompt
- write a brief for operator inspection

Phase 2:

- live-verify on an active project
- confirm recurring constraints promote correctly
- inspect whether confirmed constraints discipline mutation without collapsing exploration

Phase 3:

- if valuable later, expose constraint objects downstream to librarian / source-hunting workflows

## Open Questions

- should violating a confirmed constraint eventually trigger a scorer penalty?
- should confirmation threshold remain `2` distinct runs or become project-configurable?
- when should derived constraints become a cross-project mining asset rather than a per-project lane?

