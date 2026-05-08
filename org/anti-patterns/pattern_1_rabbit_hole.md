---
id: ANTI-PATTERN-004
name: pattern_1_rabbit_hole
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["clean theorem", "5/5 genuine", "Round 5 verdict", "tactic failed, trying alternative"]
  structural:
    - n_consecutive_pattern_1_deployments_on_same_problem_class
    - same_main_thread_attempt_n_plus_2_on_one_lean_unification
    - generative_pattern_applied_recursively_to_its_own_residual_without_orthogonal_pressure
    - residual_class_renamed_each_iteration_but_not_strictly_smaller
  problem_classes: [hard_mathematical_residual, apparatus_self_audit]
detection_protocol:
  primary: PATTERN-001  # friction_debate's own deployment-rule audit (recursion-depth cap)
  secondary: PATTERN-011  # swarm_dispatch (escalate to fresh-context agent)
  rule:
    - "When the same generative pattern is applied N≥2 times consecutively to the same problem class and each application produces 'clean theorem' output, audit whether each output is STRICTLY SMALLER residual or just RENAMED."
    - "When a Lean tactic / elaborator fails on attempt #1, attempt one alternative; on attempt #2 failure, spawn a focused Lean-fix agent. Do NOT exceed 2 main-thread attempts on a single unification issue."
    - "10x criteria gate: every Pattern-1 output must meet ≥1 of {compiled_constructor, compiled_falsifier, residual_split, executable_test, promotion_gate} or downgrade to review-note."
mitigation:
  - "STOP the recursive deployment. Pivot to orthogonal pressure: explicit construction agent, literature sweep, or honest 'open in 2026' call."
  - "Spawn a fresh agent with NO accumulated context (no anchoring on prior attempts). Operator-prescribed escalation was 6x more compute-efficient than continued main-thread fumbling."
  - "Apply 10x criteria check BEFORE spawning the next iteration."
  - "Recursion-depth cap: ≤2 consecutive Pattern-1 deployments on the same residual; mandatory orthogonal-pressure pattern between iterations."
examples:
  - id: catch_5
    summary: "Pattern 1 produced 5 consecutive 'clean theorems' (Bohr-mean enstrophy, conditional infinite-Σ, Pressure-AP dichotomy, L^∞-pressure, CZ-on-Liouvillian). Real score ~1.5/5: theorems 3-5 were synonymous-vocabulary unwrappings of the same harmonic-analysis question. Operator's tautology suspicion broke the loop."
    file: pattern1_rabbit_hole_catch_2026_05_08.md
  - id: catch_25
    summary: "Lean elaborator unification failure (q_matches_selected_prefix := fun _ => rfl). Six main-thread build attempts trying rfl variants, unfold, show, @[reducible], structure-literal indirection. Operator forced escalation. Fresh agent with no anchoring solved it in one shot via def → abbrev. 6x cost ratio."
    file: anti_laundering_catch_25_lean_elaborator_rabbithole_2026_05_08.md
falsifiable_test:
  description: "After N≥2 consecutive deployments of the same generative pattern (Pattern-1, tactic-debug, etc.) on the same residual, run a strip-and-compare on each output's residual class. The anti-pattern fires iff each output is RENAMED (synonymous-vocabulary unwrapping), not strictly smaller."
  binary_check: "residual_class_strictly_smaller(output_n) compared with residual_class(output_{n-1}) — firing iff False for any n ≥ 2."
  not_trivial: "Returns 'not firing' when the pattern produces genuine residual splits (Pattern-1 #2 produced Conditional Infinite-Σ Extension Theorem; Pattern-1 #6 produced Rank Dichotomy — both strictly smaller residual). The test discriminates between generative use and rabbit-hole use. NOT True := by trivial."
chain_position: pre  # runs BEFORE the N+1th deployment of the same pattern
references:
  - "PATTERN-001 friction_debate (deployment-rule rule_3_recursion_depth + rule_4_10x_criteria)"
  - "PATTERN-011 swarm_dispatch (escalation to fresh-context agent)"
  - "pattern1_rabbit_hole_catch_2026_05_08.md"
  - "anti_laundering_catch_25_lean_elaborator_rabbithole_2026_05_08.md"
---

# ANTI-PATTERN-004 — Pattern-1 Rabbit Hole

## What it is

A generative pattern (Pattern-1 friction debate, or any iterative
debug loop) applied recursively to its own residual without
orthogonal pressure between iterations. Two granularities observed
tonight:

1. **Theorem-level** (catch #5): Pattern-1 deployed 5 times on the
   same residual class produces 5 "clean theorems" that, on audit,
   are synonymous-vocabulary unwrappings of the same harmonic-
   analysis question. Real score ~1.5/5 vs apparent 5/5.
2. **IDE-level** (catch #25): a Lean elaborator unification failure
   debugged in main-thread for 6 attempts (rfl, unfold, show,
   reducible, structure-literal-indirection) — fresh agent with no
   anchoring solved it in one shot.

## Why it appears

Generative tools that produce verbose intermediate output (debate
rounds, alternative tactics) feel like progress. The rabbit-hole
emerges because each iteration's output anchors the next: the
agent already has a partial frame, and the frame is the suspect
not the code.

## Why it matters

Anchoring is invisible. Operator attention is spent on theatrical
"5/5 clean theorems" or "I'll try one more rfl variant", and the
real cost is opportunity (a fresh agent with construction freedom
or a swarm dispatch would have produced a strictly smaller
residual or a green build).

## Detection protocol

Apply PATTERN-001's own deployment-rule audit before each deployment
on the same residual:

1. **Construction-Freedom**: at least one champion has freedom to
   attempt construction.
2. **Orthogonal-Pressure**: at least one orthogonal pattern between
   Pattern-1 iterations.
3. **Recursion-Depth-Cap**: ≤2 consecutive on same residual.
4. **10x-Criteria**: output must meet ≥1 of compiled_constructor /
   compiled_falsifier / residual_split / executable_test /
   promotion_gate.
5. **Top-of-Funnel**: question must be FRESH, not residual-grinding.

For tactic-debug at IDE granularity: 2-attempt rule.

## Mitigation when detected

- STOP the recursive deployment.
- Pivot to orthogonal pressure (explicit construction, literature
  sweep, or honest "open in 2026").
- Spawn fresh-context agent with NO anchoring on prior attempts.
- Apply 10x criteria check before next deployment.

## Falsifiable test (catalog-level)

`residual_class_strictly_smaller(output_n)`. Firing iff False for
any n ≥ 2.

NOT trivially True: Pattern-1 #2 (Conditional Infinite-Σ Extension)
and Pattern-1 #6 (Rank Dichotomy) genuinely produced strictly
smaller residuals. Pattern-1 #3-5 did not. The test discriminates.

## Cross-references

- PATTERN-001 (`org/patterns/pattern_1_friction_debate.md`) — the
  pattern's own anti-pattern section names this; the catalog file
  formalizes detection.
- PATTERN-011 (`org/patterns/swarm_dispatch.md`) — escalation
  primitive.
- `projects/ns_millennium_hunt/workspace/research_notes/pattern1_rabbit_hole_catch_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/anti_laundering_catch_25_lean_elaborator_rabbithole_2026_05_08.md`
