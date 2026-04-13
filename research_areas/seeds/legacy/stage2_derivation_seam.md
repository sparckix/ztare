# Stage 2 Derivation Seam Hardening

## Purpose

This seed defines the next critical-path program to improve V4 after:

- V4 stages 1-6 were promoted as typed unit contracts
- bridge hardening was frozen on the audited bridge contract
- runner hardening was closed with `R1`-`R4`
- supervisor routing/genesis infrastructure was completed

The remaining integrity risk is upstream:

**a fabricated or weakly grounded safe-harbor anchor can be derived from thesis text, then carried cleanly through hardened downstream layers.**

That means the next live seam is:

```text
TextInput -> derive_hinge_object(...) -> Stage2Handoff
```

## Core Thesis

The next program should harden the text-to-hinge derivation seam, not reopen:

- the V4 unit-contract stages
- bridge hardening
- runner hardening
- supervisor_loop

The seam must produce typed derivation records that either:

- independently ground a safe-harbor disclaimer from source text, or
- fail closed to an unresolved / ungrounded status

This program is allowed to tighten what counts as a valid Stage 2 derivation pass at this seam.

## Problem Statement

The current architecture can now:

- route deterministically
- retain the best in-scope candidate
- reject undeclared scope drift
- freeze bridge behavior under audited contract conditions

But it can still carry a bad upstream derivation faithfully.

The specific failure mode already observed is:

- fabricated `LOCAL_SAFE_HARBOR` anchoring

This is cumulative risk because downstream layers can behave correctly while still inheriting a wrong typed object.

## Proposed Contract Boundary

The program should harden:

```text
TextInput -> HingeObject / derivation record
```

Not:

```text
full V4 live loop
```

The program should introduce:

- typed derivation mismatch vocabulary
- typed derivation record
- fail-closed reconciliation rules
- fixture regression on real fabricated-anchor and contradicted-scope cases
- dedicated evaluator matched to this seam

## Success Condition

The seam is promotable when:

1. safe-harbor disclaimers are independently grounded from the text, not accepted by mutator assertion alone
2. contradicted, fabricated, or weakly grounded disclaimers fail closed
3. mismatch classes are frozen and covered by fixture regression
4. the seam is evaluated by a seam-local contract, not by a generic recursive-thesis loop

## Out Of Scope

- reopening `epistemic_engine_v4`
- reopening `epistemic_engine_v4_bridge_hardening`
- reopening `runner_hardening`
- reopening `supervisor_loop`
- adding new fields to `HingeObject`
- changing the `R1` `MutationDeclaration` wire format
- changing Stages 3-6 contracts
- generic digression detection
- automated portfolio management

## Expected Artifacts

- `DerivationMismatchClass`
- `DerivationRecord`
- fixture regression for real failure classes
- dedicated seam meta-runner / evaluator
- genesis artifact if the program is formally opened
