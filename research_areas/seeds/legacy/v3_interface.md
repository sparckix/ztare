# V3 Interface Spec

## Purpose

This note defines the boundary between:

- a **stateful knowledge compiler** that accumulates sources, summaries, and candidate claims over time
- a **stateless ZTARE validator** that adversarially tests a bounded claim packet with zero privileged memory

This is an interface spec, not a full architecture. It preserves the paper's core contribution while leaving the external knowledge layer free to evolve.

## Core Thesis

A stateful knowledge compiler is the right model for **knowledge accumulation**.

ZTARE's adversarial loop is the right model for **epistemic validation**.

They should interoperate through a strict packet boundary. They should not share privileged internal state.

## Non-Goals

- This is **not** a proposal to turn ZTARE into a wiki engine.
- This is **not** part of the v3 architectural proof.
- This is **not** a commitment to any embedding, vector DB, or RAG stack.

## Invariants

1. ZTARE remains stateless across validation runs.
2. ZTARE never reads a persistent wiki as trusted ground truth.
3. Every validation run is reproducible from a bounded input packet.
4. Filing accepted outputs back into a knowledge base happens **outside** ZTARE.
5. The knowledge compiler may accumulate state; the validator may not inherit that state as authority.

## Boundary

### 1. Knowledge Compiler

Responsibilities:

- ingest raw sources
- maintain a markdown knowledge base or equivalent structured store
- track provenance, contradictions, open questions, and candidate claims
- select the minimal context required to test one claim
- emit a bounded `claim_packet`

The compiler is allowed to be stateful and accumulative.

### 2. ZTARE Validator

Responsibilities:

- consume a `claim_packet`
- run adversarial thesis refinement and executable falsification
- return hardened claims, failures, unresolved assumptions, and artifacts

The validator is not allowed to:

- trust prior accepted claims
- browse the full knowledge store as authoritative memory
- silently inherit cross-run consensus

### 3. Knowledge Store Update

Responsibilities:

- read `validation_packet`
- decide what becomes an accepted note, rejected note, open question, or unresolved contradiction
- update the external knowledge base

This update step is outside the validator.

## Packet Contracts

### `claim_packet/`

Minimal bounded input to the validator:

```text
claim_packet/
  claim.md
  evidence_snapshot/
    source_01.md
    source_02.md
    source_03.md
  provenance.json
  assumptions.md
  open_questions.md
  task_config.json
```

Required semantics:

- `claim.md`: one claim or thesis to validate
- `evidence_snapshot/`: immutable subset of source material used for this run
- `provenance.json`: source ids, timestamps, compiler decisions, and packet hash
- `assumptions.md`: explicit assumptions the compiler could not resolve
- `open_questions.md`: unresolved areas worth adversarial attention
- `task_config.json`: validator settings such as rubric, iteration budget, models

### `validation_packet/`

Bounded output from the validator:

```text
validation_packet/
  hardened_claim.md
  failure_log.md
  counterevidence.md
  validated_subclaims.json
  unresolved_assumptions.md
  execution_artifacts/
    test_model.py
    scores.json
    qa.json
```

Required semantics:

- `hardened_claim.md`: best surviving claim after adversarial pressure
- `failure_log.md`: what broke, why, and under which test
- `counterevidence.md`: strongest surviving objections
- `validated_subclaims.json`: structured claims that survived with confidence labels
- `unresolved_assumptions.md`: what remains central but unproven
- `execution_artifacts/`: reproducibility and audit trail

## Lifecycle

1. Knowledge compiler ingests sources into a persistent store.
2. Compiler identifies one candidate claim worth testing.
3. Compiler packages a bounded `claim_packet`.
4. ZTARE runs statelessly on that packet.
5. ZTARE emits a `validation_packet`.
6. External update logic files results back into the knowledge base.
7. Future claims may reference prior outputs, but only by repackaging them as explicit evidence in a new packet.

## Why This Boundary Matters

Without this boundary, the system accumulates epistemic debt:

- accepted outputs become privileged inputs
- historical consensus softens adversarial pressure
- the validator drifts from zero-trust execution toward self-referential coherence

The packet boundary prevents that. Prior knowledge can be reused, but only by being reintroduced as explicit evidence subject to attack.

## Relationship To The Paper

For the paper:

- keep the v3 proof minimal and domain-agnostic
- do not claim a knowledge engine as the research contribution
- describe this only as future system architecture, if at all

For engineering:

- this interface is the cleanest way to extend ZTARE without corrupting the core falsification mechanism

## Product Implication

Yes, this can inform the product. But the product should not be:

- "ZTARE with a wiki glued inside it"

The product should be one of these:

1. **Validator-first**
   ZTARE is the core service. Clients bring their own research substrate and submit `claim_packet`s.

2. **Workspace + validator**
   A separate knowledge workspace manages sources and claim packaging, then calls ZTARE as a validation service.

The second is probably the better product eventually. The first is the cleaner way to preserve optionality right now.

## Recommended Next Build Step

Do not build the whole knowledge layer yet.

Build only:

1. a `package_claim.py` script that turns a selected project state into a `claim_packet`
2. a `validate_claim.py` wrapper that runs ZTARE on that packet
3. a `file_result.py` script that stores the resulting `validation_packet`

That is enough to test the interface without prematurely freezing the product architecture.
