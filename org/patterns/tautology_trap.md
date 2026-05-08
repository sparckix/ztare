---
id: PATTERN-006
name: tautology_trap_detector
version: 1
status: active
discovered: 2026-05-06
specializes: PATTERN-002  # tautology trap is a sub-mode of darwin_idea_killer
triggers:
  lexical: [predicts, equals, by-definition, reduces-to]
  structural: [test_quantity_X_uses_named_conjecture_terms, predicted_value_in_proposition]
  problem_classes: [apparatus_self_audit]
spawn:
  mode: single_audit_specialization  # invoke PATTERN-002 with --mode=tautology
  subagents:
    - role: tautology_detector
      tools: [read]
output_schema: tautology_verdict_v1  # {tautological, non_tautological}
fallback: null
preconditions:
  - claim_makes_a_prediction: yes
chain_position: post
specializes_pattern: PATTERN-002
related_patterns:
  - id: PATTERN-002
    relation: parent  # this pattern is a specialization of darwin_idea_killer
    note: "tautology trap is one of darwin_idea_killer's failure-mode buckets"
---

**HONESTY (DARWIN catch H3, 2026-05-08)**: this pattern was originally
declared as a peer of PATTERN-002 darwin_idea_killer but DARWIN audit
confirmed it is a SPECIALIZATION (sub-mode) — bullet 3 of darwin's
"Pattern" section explicitly lists "Tautological reduction" as a
DARWIN failure-mode bucket. Counting tautology_trap_detector as a
distinct peer pattern was laundering: the count "10 patterns" overstates
the catalog's true cardinality of ~7-8 peers + 2-3 specializations.

This file is RETAINED for vocabulary + invocation convenience (Director
may ask for a TAUTOLOGY-FOCUSED audit specifically), but the architecture
should treat this as `PATTERN-002 --mode=tautology`, not as an
independent primitive.

# Pattern 6 — Tautology-Trap Detector

## Problem

When an agent proposes a "test" or "falsifiable prediction" for a
conjecture, the predicted value of the test quantity sometimes uses the
named labels of the conjecture being tested — making the prediction
TAUTOLOGICAL by construction (both sides of the predicted equation are
the same object dressed differently).

Tonight's catch #3 was the canonical example: agent proposed Massey-Toda
bracket prediction `⟨α,β,γ⟩ = κ_4` to test VBNS-PT, where κ_4 is
DEFINED as the Postnikov k-invariant of VBNS-PT. The "test" is
"predicts the structure equals itself."

## Pattern

Diagnostic rule: strip all named-after-the-conjecture quantities from
the prediction. If the prediction collapses or becomes vacuous, it was
tautological.

Operationally:
1. Identify the conjecture's named labels (e.g., W6, OCCT, VBNS-PT,
   κ_4)
2. Strip those labels from the proposed prediction's RHS
3. Ask: does the prediction still make a SUBSTANTIVE claim (something
   testable that doesn't reference back to the conjecture)?
4. If no → TAUTOLOGICAL → REJECT

## Why it works

Catches circular reasoning at the type level. A prediction that uses
conjecture-named quantities in its RHS is testing nothing — it's
asserting "X = X" with extra steps.

## When to deploy

- Anytime an agent proposes a "falsifiable test" for a conjecture
- Anytime a prediction's RHS contains conjecture-specific labels
- Especially when the prediction looks rigorous (uses Greek letters,
  brackets, technical names)

## Anti-pattern

**OVER-STRIPPING**: removing all variables from a real prediction.
The detector strips NAMED-AFTER-CONJECTURE quantities, not all
variables. A prediction like `‖p‖_∞ ≤ C` for some `C` is fine; a
prediction `bracket(VBNS-PT) = k-invariant(VBNS-PT)` is the trap.

## Concrete example

2026-05-08 ~07:30 — Massey-Toda agent proposed:
> "If VBNS-PT is real, the bracket ⟨α,β,γ⟩ = κ_4 ∈ H²(W_{≤3}; π_1(W_4))"

Tautology detector: κ_4 is the Postnikov k-invariant of VBNS-PT's
tower. Stripping that — "bracket = (the thing VBNS-PT defines)" — is
not a test of VBNS-PT.

REJECTED as tautological. Real test would require an EXTERNAL
observable not named-after VBNS-PT.

## Cross-references

- `agent_orchestration_meta_patterns_2026_05_08.md` Pattern 3 — origin
- PATTERN-002 (darwin_idea_killer) — generalized version
