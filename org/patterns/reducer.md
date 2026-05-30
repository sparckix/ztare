---
id: PATTERN-003
name: reducer
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [2150, 2226, future-math, paradigm-shift, novel-vocabulary, unifier, topos, derived-stack, postnikov, sheaf, gerbe, cohomology, infty-category]
  structural: [elite_noun_used, future_vocabulary_proposed, naming_sprint_in_progress]
  problem_classes: [pre_category_emergence, apparatus_self_audit]
spawn:
  mode: single_audit
  subagents:
    - role: reducer
      description: Strip future-facing rhetoric. Reduce concept to its 2026 equivalent. Output 'LAUNDERED' if tautological renaming.
      tools: [read]
output_schema: reducer_verdict_v1  # {LAUNDERED, GENUINE-BUT-VACUOUS, GENUINE-AND-PREDICTIVE}
fallback: null
preconditions:
  - claim_uses_future_vocabulary: at least one elite noun present
chain_position: terminal  # final filter before promoting future-vocab claims
related_patterns:
  - PATTERN-004 (vocabulary_quarantine, prompt-time guardrail)
  - PATTERN-005 (falsifiable_asymmetry, output-time guardrail)
references:
  - https://github.com/anthropics/skills (SKILL.md format precedent)
  - tonight's catch #12-14 (OCCT/FDOS/VBNS-PT all LAUNDERED)
falsifiable_test: |
  Over N>=15 reducer audits of future-vocabulary candidates, the reducer's
  LAUNDERED verdicts must agree with an independent cross-family re-audit
  (PATTERN-014) on >=80% of cases, AND the reducer must return at least one
  non-LAUNDERED verdict (GENUINE-BUT-VACUOUS or GENUINE-AND-PREDICTIVE) across any
  15-dispatch window. If cross-family agreement drops below 80%, or the reducer
  outputs LAUNDERED on 15/15 (its own DEFAULT-TO-LAUNDERED anti-pattern), demote.
  metric_source: reducer_verdict_v1 outputs vs cross-family re-audit verdicts; both
  tagged in pattern_deployment_ledger.jsonl (primary_pattern=PATTERN-003) and
  external_prover_ledger.jsonl.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 3, Reducer (P13 from operator-directed mitigations)

## Problem

When agents are asked to project "2150 vocabulary" or "paradigm-shift
unifier" for an open problem, they tend to produce sophisticated-sounding
candidates dressed in elite nouns (topos, derived stack, ∞-category,
Postnikov tower, sheaf, gerbe) that, when stripped, REDUCE TO existing
2026 constraints under different names.

This is the laundering pattern that wastes review hours on theatrical
"unifiers" that name nothing new.

## Pattern

Single-agent audit applied AFTER any future-vocabulary projection:

1. Receive proposed concept + its definition
2. STRIP all future-facing rhetoric, every elite noun (∞-category,
   topos, derived stack, Postnikov tower, gerbe, etc.)
3. ASK: what concrete 2026 statement REMAINS after stripping?
   - Banach-space inclusion / non-inclusion claim?
   - Fourier / harmonic-analysis estimate?
   - Bohr-AP / function-class inequality?
   - Stationary NS / Leray-Hopf statement?
4. COMPARE the stripped statement against KNOWN constraints in the
   architecture (existing wall list, prior closures, prior dichotomies)
5. VERDICT one of:
   - **LAUNDERED**: stripped concept is tautological renaming
   - **GENUINE-BUT-VACUOUS**: non-tautological but provides no new
     prediction
   - **GENUINE-AND-PREDICTIVE**: makes a falsifiable prediction beyond
     known 2026 facts. Identify the specific prediction.

## Why it works

Pits LLM pattern-matching against its own text-generation tendencies.
Physically catches circular logic before review hours wasted.

The reducer agent doesn't need to KNOW the substrate; it needs to apply
strip-and-compare. This makes it cheap and reusable.

## When to deploy

- After any future-vocabulary candidate is proposed (naming sprint,
  alien-math projection, 2150-unifier articulation)
- BEFORE adding the concept as a foundational primitive in any Lean file
- BEFORE writing it into a paper

## Anti-pattern

**TYPE-MIXING**: confusing "this is a LAUNDERED relabel" with "this
concept is wrong." A LAUNDERED concept might be a useful renaming for
PEDAGOGY, but should NOT be treated as foundational primitive. Document
as scaffold, not closure.

**DEFAULT-TO-LAUNDERED**: reducer that outputs LAUNDERED on every input
to look thorough. Track precision; require occasional GENUINE verdicts
(if substrate produces real novelty).

## Concrete example

2026-05-08 ~09:30, applied to OCCT (Obstruction-Coherent Compactness
Topos), FDOS (Filtered Derived Obstruction Stack), VBNS-PT (Viscous-
Bilinear-NS Postnikov Tower).

Reducer verdict: 3/3 LAUNDERED.

- OCCT stripped of {topos, sheaves, DSymp, pseudospectral, universal
  property} → "every quasi-compact factorization of B(u,u) fails through
  a common mechanism" = UCC W1-W5 already in architecture
- FDOS stripped of {filtered cotangent complex, D^[-6,0], graded pieces,
  derived intersection, gerbe, sheaf} → "ℳ_NS = {u : W_k(u)=0 for k=1..6}"
  = the existing 5+1-wall T15 characterization, listed in an order
- VBNS-PT stripped of {Postnikov tower, top class, Massey-Toda triple
  bracket, Ext¹, k-invariant} → "viscous bilinear NS on flat ℝ³ has W6
  Liouvillian-Bohr-non-closure as residual obstruction" = existing
  T15-localization restated

Falsifiable Asymmetry test on each: all 3 vanish in solved regimes
(2D Ladyzhenskaya, axisymmetric KNSŠ, Kato small-data) for the SAME
reason their 2026 substrates vanish. No new predictions.

3 Lean files downgraded with LAUNDERED docstring; not deleted (retained
as vocabulary scaffolds for ZTARE substrate consumers).

## Cross-references

- `mitigations_11_12_13_2026_05_08.md`, full P11/P12/P13 set
- `naming_sprint_deliverable_2026_05_08.md`, VBNS-PT instance
- `anti_laundering_catches_9_10_2026_05_08.md`, adjacent catches
