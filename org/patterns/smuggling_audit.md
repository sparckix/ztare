---
id: PATTERN-007
name: smuggling_audit
version: 1
status: active
discovered: 2026-05-08
specializes: PATTERN-002  # smuggling-audit is darwin_idea_killer scoped to Mungerian-inversion failure mode
triggers:
  lexical: [inversion, mungerian, fallback, bypass, alternative-route]
  structural: [inversion_proposed, fallback_path_invoked]
  problem_classes: [apparatus_self_audit, pure_analysis_drift]
spawn:
  mode: single_audit_specialization  # invoke PATTERN-002 with --mode=smuggling
  subagents:
    - role: smuggling_detector
      tools: [read]
output_schema: smuggling_verdict_v1
fallback: null
preconditions:
  - inversion_or_fallback_path_proposed: yes
chain_position: post
specializes_pattern: PATTERN-002
related_patterns:
  - id: PATTERN-002
    relation: parent
    note: "smuggling audit is darwin_idea_killer scoped to inversion-fallback failure mode"
falsifiable_test: |
  Over N>=12 Mungerian-inversion fallback paths audited, every INVERSION-SMUGGLES
  verdict must name a specific central step, and >=80% of those named steps
  must be confirmed (by cross-family re-audit or a solved-regime counterexample) to
  actually require the bypassed obstruction. If confirmation falls below 80%, or
  any 12-dispatch window contains zero named central steps (over-paranoia
  anti-pattern), demote.
  metric_source: smuggling_verdict_v1 outputs (named step + confirmation status) in
  pattern_deployment_ledger.jsonl (primary_pattern=PATTERN-007), cross-checked
  against external_prover_ledger.jsonl re-audits.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

**HONESTY (DARWIN catch H2/H3, 2026-05-08)**: this pattern is a
SPECIALIZATION of PATTERN-002 darwin_idea_killer scoped to Mungerian-
inversion failures. Catalog should treat this as `PATTERN-002 --mode=smuggling`,
not as independent peer.

# Pattern 7, Smuggling Audit (Mungerian Inversion Failure Detector)

## Problem

When stuck on a hard problem, agents propose Mungerian-inversion
fallbacks: "instead of trying to prove X, prove ¬¬X" or "instead of
attacking residual R, prove R is generically empty via measure theory."

These inversions sometimes look like they bypass the original
obstruction, but secretly REINTRODUCE the same obstruction through a
central implicit step. The agent claims to have found a shortcut
but the shortcut requires the very thing it was trying to bypass.

Tonight's catch #15 was the canonical example: Mungerian fallback
"rank-generation impossibility" for W6 closure relied on analytic
continuation of stationary set across Diophantine stratum, which
requires the small-divisor estimates that the inversion was supposed
to bypass.

## Pattern

When a Mungerian inversion is proposed as a fallback path:

1. Identify each CENTRAL step in the inversion's argument
2. For each step: what fact does it require?
3. Is that fact the ORIGINAL obstruction the inversion was trying
   to bypass?
4. If yes → INVERSION FAILS; the original problem appears in disguise

Detection technique: apply the falsifiable-asymmetry test (P12) on
a solved adjacent regime. If the inversion's prediction contradicts
the solved regime's known facts, the inversion is wrong and likely
has smuggling somewhere.

## Why it works

Inversions are seductive because they FEEL like they bypass hardness.
Forcing the CENTRAL step audit reveals where the hardness
re-enters.

## When to deploy

- Any time a "Mungerian fallback" is proposed
- Any time an alternative-route argument claims to bypass a known wall
- Especially when the proposed bypass uses measure theory, generic
  emptiness, or analytic continuation arguments

## Anti-pattern

**OVER-PARANOIA**: marking every inversion as "smuggling suspect"
without identifying the specific central step. The audit must
NAME the step that smuggles.

## Concrete example

2026-05-08 ~09:50, Mungerian-fallback agent proposed:
> "Bypass small divisors via measure-zero rank-generation impossibility:
> Liouvillian numbers have measure 0 (Khinchin), Picard preserves rank,
> so rank-r-Liouvillian stratum has measure 0 in NS solutions."

Smuggling audit:
- Step 1 (Khinchin measure-zero): clean ✓
- Step 2 (Picard rank-preservation): clean ✓ (already proved tonight)
- Step 3 (analytic continuation of stationary set across Diophantine
  stratum): REQUIRES resolvent estimate `‖(Δ + linearization)^{-1}‖`
  which IS the W6 small-divisor estimate the inversion was bypassing
- Step 4 (measure-zero ⟹ no construction): FALSE in general, 
  Anosov-Katok, Fayad constructions live in measure-zero sets

VERDICT: INVERSION SMUGGLES. Plus 2D counterexample (rank-2 Liouvillian
stationary AP solutions DO exist in 2D NS per Marchioro-Pulvirenti)
falsified the inversion's main claim.

## Cross-references

- `catch_15_mungerian_smuggling_2026_05_08.md`, origin
- PATTERN-002 (darwin_idea_killer), generalized
- PATTERN-005 (falsifiable_asymmetry), solved-regime test used here
