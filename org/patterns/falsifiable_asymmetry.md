---
id: PATTERN-005
name: falsifiable_asymmetry
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [paradigm-shift, unifier, predicts, asymmetry]
  structural: [future_vocabulary_candidate_proposed, naming_sprint_output]
  problem_classes: [pre_category_emergence]
spawn:
  mode: output_gate  # post-output enforcement gate
  subagents: []
output_schema: asymmetry_verdict_v1  # {predicts_asymmetry, no_asymmetry_so_LAUNDERED}
fallback: PATTERN-003  # reducer
preconditions:
  - candidate_claims_to_be_a_paradigm_shift: yes
chain_position: post  # runs AFTER projector, BEFORE reducer
related_patterns:
  - PATTERN-004 (vocabulary_quarantine, prompt-time guardrail)
  - PATTERN-003 (reducer, terminal filter)
falsifiable_test: |
  Over N>=15 paradigm-shift candidates passed through the asymmetry gate,
  candidates that PASS (produce a concrete solved-system prediction) must survive
  downstream PATTERN-003 reducer audit at a rate >=30 percentage points higher
  than candidates that FAIL the gate. If PASS and FAIL candidates are demolished
  by the reducer at statistically indistinguishable rates (margin <30 points), the
  asymmetry gate is not discriminating and demotes.
  metric_source: asymmetry_verdict_v1 outputs joined to downstream
  reducer_verdict_v1 outcomes via pattern_deployment_ledger.jsonl dispatch_id
  chains.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 5, Falsifiable Asymmetry Requirement (P12 from operator-directed mitigations)

## Problem

A real paradigm shift doesn't just solve the hard problem; it predicts
something NEW about the EASY problems too. Wiles' modularity bridge
made testable claims about elliptic curves; Connes' noncommutative
geometry made testable claims about classical operators.

Future-vocabulary candidates that ONLY explain the hard problem (and
say nothing new about solved ones) are usually rebrandings, not
paradigm shifts.

The fix: demand a falsifiable prediction about a SOLVED CLASSICAL
SYSTEM at output-review time.

## Pattern

After a future-vocabulary candidate is proposed, BEFORE accepting it,
demand:

> "If your proposed [future] meta-pattern is true, it must make a
> falsifiable prediction about a KNOWN 2026 system. Identify a specific
> edge case or residual in a fully solved classical system (e.g., 2D
> Ladyzhenskaya NS, axisymmetric KNSŠ 2009, Kato small-data) that your
> new pattern predicts something about, which 2026 math currently treats
> as random noise."

If the candidate cannot produce a concrete falsifiable asymmetry,
DOWNGRADE to LAUNDERED (chain to Reducer P13).

## Why it works

Real paradigm shifts predict NEW things about EASY problems. No
asymmetry → not a paradigm shift, just a rebrand.

The test is cheap: ask the candidate to produce ONE specific edge
case in ONE solved system. If it can't, the candidate has no
predictive content.

## When to deploy

- Every output of a naming sprint
- Every "unifier" proposal
- Every "alien math from the future" candidate
- Before adding any future-vocabulary file as foundational primitive

## Anti-pattern

**FAKE ASYMMETRIES**: candidate produces a vague asymmetry like
"my framework predicts 2D NS has additional structure" without
specifying what structure or how to test. Demand SPECIFICITY: which
edge case? what observable? how to verify in 2026?

**SOLVED-CASE GAMING**: candidate predicts the EXISTING known result
in solved case ("predicts 2D NS is globally regular" = known). The
prediction must be NEW relative to current literature.

## Concrete example

2026-05-08 ~09:30, applied to OCCT, FDOS, VBNS-PT.

Each candidate was asked: what does this predict about 2D Ladyzhenskaya
NS that 2026 math doesn't already see?

- OCCT: stripped → 4 shadows (UCC + Galley + pseudospectral +
  cohomological). In 2D NS, all 4 vanish for the SAME reason their
  2026 substrates vanish (UCC vacuous in 2D bilinear; Galley
  degenerates; pseudospectral bypassed; H¹(ℝ²)=0 trivially). NO
  asymmetry → LAUNDERED.

- FDOS: stripped → 6-wall list. In 2D, walls W1/W3/W5/W6 vacuous,
  W2/W4 dominated by enstrophy identity. Predicts ℳ_NS^{2D} is full
  vanishing locus = Ladyzhenskaya already proves. NO new prediction →
  LAUNDERED.

- VBNS-PT: stripped → "W6 is the residual obstruction." In 2D, W6 is
  structurally absent. NO asymmetry → LAUNDERED.

Verdict: 3/3 failed Falsifiable Asymmetry test. All chained to Reducer
P13 which confirmed LAUNDERED.

## Cross-references

- `mitigations_11_12_13_2026_05_08.md`, full P11/P12/P13 set
- PATTERN-004 (vocabulary_quarantine), pre-output guardrail
- PATTERN-003 (reducer), post-output terminal filter
