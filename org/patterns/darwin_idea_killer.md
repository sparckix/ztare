---
id: PATTERN-002
name: darwin_idea_killer
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [audit, kill, refute, falsify, obstruction]
  structural: [theorem_proposed, claim_made, prior_pattern_output_present]
  problem_classes: [hard_mathematical_residual, apparatus_self_audit]
spawn:
  mode: single_audit
  subagents:
    - role: idea_killer
      description: Mungerian inversion — assume the claim is WRONG, find the failure mode
      tools: [read]
output_schema: kill_report_v1
fallback: null  # terminal node, no fallback
preconditions:
  - input_is_a_specific_claim: not "audit my work" but "audit theorem X"
  - claim_has_structure: hypothesis + conclusion identifiable
chain_position: secondary  # always chained AFTER another pattern's output
related_patterns:
  - PATTERN-001 (friction_debate — typical predecessor)
  - PATTERN-003 (reducer — sometimes chained after)
references:
  - https://arxiv.org/html/2604.00478 (Silicon Mirror — anti-sycophancy 2026)
  - existing src/ztare/orchestrator/post_run_meta_audit.py — apparatus-side analog
---

# Pattern 2 — DARWIN-IDEA-KILLER

## Problem

LLMs producing "clean theorem" verdicts via Pattern 1 or other adversarial
methods can still ship subtle laundering: hidden hypotheses, scope-overclaim,
weak-strong-uniqueness gaps, vacuous predicates. A SINGLE-PERSPECTIVE
verification cycle (e.g., reading the proof to "check it") doesn't catch
these because the verifier shares the producer's frame.

DARWIN-IDEA-KILLER applies Mungerian inversion: assume the claim is
WRONG, hunt for the failure mode aggressively. The kill agent is rewarded
for catching laundering, not for endorsing.

## Pattern

Single-agent audit run AFTER another pattern produces a claim:

1. Receive claim + claim's proof/argument
2. List load-bearing steps (the inversion target)
3. For each step: identify what could break it
   - Hidden hypothesis (what's silently assumed?)
   - Tautological reduction (does this rename the problem?)
   - Scope over-claim (does the proof only cover a sub-class?)
   - Smuggling (does an "inversion" reintroduce the original problem?)
4. Output: kill report with severity-ranked findings + EXACT line of
   the file where each break occurs

Kill report includes a 'survives ✓' / 'kill candidate ⚠' / 'kill
confirmed ✗' verdict per finding.

## Why it works

- Mungerian inversion priorizes what the producer wants to NOT see
- Single-agent audit is cheap (one prompt, no friction loop)
- Severity ranking lets the chain-runner decide what to escalate
- File:line references make the kill ACTIONABLE

Empirically validated 2026-05-08: 12+ catches generated tonight including
helicity-IBP-Beltrami-only, de-Giorgi-exact-zero-too-strong,
Carleman-empty-box, Pattern-1-rabbit-hole, Liouville-orbit-collapse-
signature-mismatch, T13-GIMS-collapse, time-dependent-rank-1-weak-strong-fix,
3 LAUNDERED 2150-vocab catches (OCCT/FDOS/VBNS-PT), pressure-term-skipped,
Mungerian-fallback-smuggling, Bohr-Wiener-sparsity-fails.

## When to deploy

- After Pattern 1 produces a "clean theorem"
- After a candidate construction is proposed
- Before a Lean file is added to the umbrella build
- Before a result is recorded in F-row

ALWAYS chain DARWIN after Pattern 1 or any claim-producing primitive.
The chain Pattern-1 → DARWIN is the canonical recursive-friction loop.

## Anti-pattern

**SELF-GRADING**: the same agent that produced the claim should NOT run
DARWIN on it. Use cross-family LLM (Claude vs GPT vs Gemini) per existing
`post_run_meta_audit.py` conventions.

**THEATRICAL KILLS**: agent fakes catching issues to appear thorough. The
catches must be SPECIFIC (file:line, hypothesis name, exact failure).

**KILL-EVERYTHING**: agent kills every claim including correct ones. Track
catch precision via subsequent audit; reject killer agents below 70%
true-positive rate.

## Concrete example

2026-05-08 ~07:30 — Pattern 1 #5 produced "Conditional Infinite-Σ
Extension Theorem". DARWIN-KILLER applied to its output identified:

- Target A (mixed-class IBP): SURVIVES with caveat
- Target B (OR is = in disguise): partial kill — (a) and (b) cover overlapping classes
- Target C (Bourgain-Wang ℓ¹): confirmed
- Target D (ℓ¹ vs ℓ² is Diophantine vs Liouvillian in disguise): KILLED — Bourgain GAFA 1995 §3 documents the small-divisor wall

VERDICT: theorem stays conditional, residual is structural-not-laundered.

## Cross-references

- `src/ztare/orchestrator/post_run_meta_audit.py` — apparatus-side analog
  (cross-family LLM diagnostic). Extend, don't duplicate.
- `mitigations_11_12_13_2026_05_08.md` — Reducer (P13) is a specialized
  DARWIN variant for 2150-vocab projections.
