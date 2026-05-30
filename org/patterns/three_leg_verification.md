---
id: PATTERN-008
name: three_leg_verification
version: 1
status: active
discovered: 2026-05-07
triggers:
  lexical: [substrate-test, verify, ground-empirically]
  structural: [conditional_theorem_produced, claim_needs_grounding]
  problem_classes: [hard_mathematical_residual, pure_analysis_drift]
spawn:
  mode: numerical_verification
  subagents:
    - role: three_leg_verifier
      tools: [read, bash]  # SymPy / numpy / mpmath access
output_schema: three_leg_report_v1
fallback: PATTERN-009  # independent_cas_verification (lighter version)
preconditions:
  - claim_is_substrate_testable: numerical / symbolic / computational
chain_position: post
related_patterns:
  - PATTERN-001 (friction_debate, typical predecessor)
  - PATTERN-009 (independent_cas_verification, lighter variant)
falsifiable_test: |
  Over N>=10 conditional theorems that PASS all three legs, the rate of subsequent
  defect discovery (sign error, scope over-claim, trivially-fires bug) found after
  F-row recording must be <=20% AND must be LOWER than the post-recording defect
  rate for theorems recorded without 3-leg verification, by >=20 percentage points.
  If 3-leg-passed theorems fail downstream at a rate within 20 points of unverified
  theorems, the verification adds no grounding and demotes.
  metric_source: F-rows for conditional theorems (verification status) joined to
  the catch ledger for post-recording defect catches; PATTERN-008 dispatches tagged
  in pattern_deployment_ledger.jsonl.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 8, Three-Leg Analytical Verification

## Problem

Conditional theorems produced by Pattern 1 friction debates often
"float", true on paper but ungrounded in concrete substrate. Without
multi-substrate verification, an off-paper detail (sign error, scope
mismatch) can survive the debate and break only at first real use.

The Stub-Replay equivalent for math: verify on POSITIVE substrate
(theorem fires), ADVERSARIAL substrate (theorem doesn't over-fire),
EDGE-CASE substrate (theorem holds at boundary).

## Pattern

Three orthogonal substrate tests:

- **LEG 1 (positive substrate)**: a regime where the theorem CLEARLY
  applies and CLEARLY closes. Numerically verify the closure fires.
- **LEG 2 (adversarial substrate)**: a regime where the theorem
  SHOULD NOT close (e.g., hypothesis fails). Numerically verify the
  theorem branches DO NOT fire (residual is real).
- **LEG 3 (edge case)**: a regime at the boundary of the theorem's
  scope. Numerically verify CONSISTENT behavior with theorem prediction.

Each leg uses independent CAS (SymPy / mpmath / numpy) for
high-precision verification. Output: numerical results table per leg
+ aggregate verdict.

## Why it works

Catches:
- Sign errors (would surface in LEG 2 as wrong-direction prediction)
- Scope over-claim (would surface in LEG 3 as boundary failure)
- Trivially-fires-everywhere bugs (would surface in LEG 2 as false
  positive)

## When to deploy

- After Pattern 1 produces a conditional theorem
- Before adding the conditional theorem to a Mathlib-PR scaffold
- Before recording the conditional theorem in F-row

Per CHAIN A (`agent_orchestration_meta_patterns_2026_05_08.md`):
Pattern 1 → DARWIN → Three-Leg Verification.

## Anti-pattern

**SUBSTRATE GAMING**: choosing the 3 legs to bias toward easy
verification. The legs must be CHOSEN ADVERSARIALLY (positive ≠
trivial closure; adversarial = real failure mode).

**INSUFFICIENT PRECISION**: using float32 / standard numpy for
small-divisor or accumulation computations. Use mpmath dps≥50 for
delicate cases.

## Concrete example

2026-05-08 ~08:15, Pattern 1 #8 produced "Conditional Infinite-Σ
Bohr-Mean Enstrophy Extension" (under Diophantine OR ℓ¹ hypothesis).

3-leg verification:
- LEG 1 (Diophantine pair (1, √2), 112-mode): theorem fires ✓ (all
  amplitudes within machine precision of zero)
- LEG 2 (Liouville pair (1, L), |û_k|=1/k, 112-mode): residual REAL ✓
  (ℓ¹ partial sum diverges as log T, ℓ² converges to 1.636)
- LEG 3 (rank-1 ℤ·L Liouville, K∈{5,..,25}): unconditional firing ✓
  (‖p‖_∞ → 0.55293 Cauchy-convergent, bounded uniformly)

Aggregate: theorem moves from "floating" to "anchored on 3-substrate
empirical grounding." Conditional structure verified.

## Cross-references

- `verify_pattern1_8_3leg_2026_05_08.py`, concrete instance
- PATTERN-009 (independent_cas_verification), lighter version when
  3-leg overkill
- ZTARE pattern catalog #6 (ztare_patterns_to_backport_2026_05_07.md)
