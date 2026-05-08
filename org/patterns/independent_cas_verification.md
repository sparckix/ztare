---
id: PATTERN-009
name: independent_cas_verification
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [trivial, elementary, by-computation, by-direct-calculation]
  structural: [agent_uses_handwave_words, algebra_critical_to_argument]
  problem_classes: [pure_analysis_drift, apparatus_self_audit]
spawn:
  mode: cas_run
  subagents: []  # not an LLM agent; runs SymPy/numpy directly
output_schema: cas_result_v1
fallback: null
preconditions:
  - algebra_is_substrate_for_argument: yes
chain_position: post
related_patterns:
  - PATTERN-008 (three_leg_verification — fuller version)
---

# Pattern 9 — Independent CAS Verification

## Problem

When LLM agents present mathematical arguments, they use words like
"trivial", "elementary", "by computation", or "direct calculation" to
gloss over algebra. These are tells that the algebra MIGHT be wrong
and the agent didn't actually do it.

Independent CAS (SymPy / numpy / mpmath) is a third-party arbitrator.
Don't trust any single agent's algebra; verify with CAS.

## Pattern

For any non-trivial algebraic claim by an agent:
1. Translate the claim to a SymPy expression
2. Run it
3. Compare result to agent's stated value
4. If discrepancy → flag agent's argument

Especially deploy when the agent says: "trivial", "elementary",
"by computation", "after some manipulation", "it is easy to see",
"clearly", "evidently", "by direct calculation."

## Why it works

CAS is deterministic and doesn't share the agent's frame bias. Catches:
- Sign errors
- Off-by-one in indices
- Confused sub vs sup
- Wrong-multiplicity counting
- Boundary-IBP mistakes

## When to deploy

- Anytime an agent claims an algebraic identity is "trivial"
- When two agents disagree on an algebraic step
- When a formula's correctness gates a downstream theorem

## Anti-pattern

**CAS-AS-ORACLE**: trusting CAS output blindly. CAS computes what
you ask; if you transcribed the claim incorrectly into SymPy, the
CAS result is wrong-input. Verify the SymPy translation before
trusting the result.

## Concrete example

2026-05-08 ~01:30 — agent claimed `∫ ω · curl ω = ∫ |∇u|²` for
divergence-free `u` "by IBP." SymPy verification on ABC flow showed:
- ∫ ω · curl ω = 8π³(A² + B² + C²)
- ∫ |∇u|² = 8π³(A² + B² + C²)
- ∫ |ω|² = 8π³(A² + B² + C²)

All three EQUAL on ABC (which is Beltrami: curl u = u, so
ω · curl ω = |ω|² automatically). But on NON-Beltrami, the identity
fails. The agent had over-claimed.

Catch #1: Helicity-IBP-Beltrami-only correction. Architecture downgraded
the helicity-stationarity terminal lemma to BELTRAMI-ONLY scope.

## Cross-references

- `scripts/verify_helicity_IBP_factor.py` — instance
- `scripts/verify_4mode_stationary_NS_collapse.py` — another instance
- PATTERN-008 (three_leg_verification) — fuller version
