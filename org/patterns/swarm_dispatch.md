---
id: PATTERN-011
name: swarm_dispatch
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [parallel, swarm, divide-and-conquer, cross-family, multiple-LLMs]
  structural: [N_independent_subtasks, cross_family_validation_needed, exploration_value_high]
  problem_classes: [hard_mathematical_residual, pre_category_emergence, too_complex_direct_attack]
spawn:
  mode: parallel_dispatch
  variants:
    - mode: agent_based
      description: Claude Code Agent tool spawns N parallel subagents (single-family Claude). Free within session quota. Best for breadth/orchestration.
      tools: [Agent]
    - mode: py_llm_based
      description: Direct API dispatch across cross-family LLMs (Claude + GPT + Gemini) via Python script. Real-dollar cost; budget-cap required. Best for cross-family validation.
      tools: [bash]
      scripts:
        - scripts/openmath_novel_ideas_swarm.py  # cross-family creativity, $5 cap default
        - scripts/surgical_swarm_panel.py        # multi-job typed-endpoint Lean closure dispatch
        - scripts/swarm_vitali_to_integral.py    # specific math task
  subagents:
    - role: parallel_worker
      tools: [varies by variant]
output_schema: swarm_aggregate_v1
fallback: PATTERN-001  # if swarm output is conflicting, fall through to friction_debate
preconditions:
  - subtasks_are_independent: yes  # otherwise serialize, don't swarm
  - aggregator_strategy_named: at least one of [union, vote, friction_debate, reducer]
chain_position: primary
related_patterns:
  - id: PATTERN-001
    relation: child  # friction_debate aggregates conflicting swarm outputs
  - id: PATTERN-002
    relation: child  # darwin_idea_killer audits swarm outputs
references:
  - https://arxiv.org/abs/2411.04468 (Magentic-One Lead-Orchestrator)
  - https://arxiv.org/html/2603.13327 (DOVA deliberation-first orchestration)
  - existing scripts/openmath_novel_ideas_swarm.py (PY LLM-based instance)
  - existing scripts/surgical_swarm_panel.py (PY LLM-based instance)
---

# Pattern 11 — Swarm Dispatch

## Problem

Many architecture tasks decompose into **N independent subtasks** that
benefit from parallel execution: 3+ candidate constructions to test,
4+ alien-math angles to explore, K+ Mathlib-PR design reviews. Serial
execution wastes wallclock; serial-with-aggregation wastes operator
attention.

Two variants of the swarm primitive serve different needs:

* **Agent-based swarm**: spawn Claude Code subagents via the Agent tool.
  Single-family (Claude only). Free within session quota. Best for
  parallelism + orchestration.
* **PY LLM-based swarm**: direct-API dispatch across cross-family LLMs
  (Claude + GPT + Gemini). Real-dollar cost. Best for cross-family
  validation when single-family agreement is suspect.

## Pattern

1. Decompose task into N independent subtasks
2. Pick variant:
   - subtasks need cross-family validation → PY LLM-based
   - subtasks need parallelism only → Agent-based
   - mixed → both layers (Agent-based for breadth, PY for cross-family
     validation of K representatives)
3. Run BUDGET-ESTIMATE first if PY LLM-based ($5+ caps typical)
4. Dispatch
5. Aggregate via named strategy (union / vote / friction_debate /
   reducer)
6. Audit aggregate via PATTERN-002 darwin_idea_killer

## Why it works

Parallelism reduces wallclock 3-10x. Cross-family detects single-LLM
hallucinations (especially novelty claims). Budget caps prevent
runaway spend.

## When to deploy

- N≥3 truly independent subtasks
- Single-family verdict suspected of bias
- Wallclock matters
- Exploration value > determinism value

## When NOT to use

- Subtasks have dependencies (serialize instead)
- Single-LLM verdict is sufficient (don't burn cross-family budget)
- The aggregator strategy isn't pre-decided (chaos)

## Anti-pattern

**SCRIPT-RUN-WITHOUT-BUDGET-ESTIMATE**: PY LLM-based swarms have $5+
caps. Always run with `--budget-estimate-only` first; show estimate to
operator; then dispatch with `--allow-paid` once authorized.

**SWARM-ON-DEPENDENT-TASKS**: forcing parallelism on serial-by-nature
tasks just produces output that needs re-serialization. Verify
independence first.

**AGENT-FAMILY-LAUNDERING**: claiming "cross-family validation" using
3 Claude Code Agent subagents (all Claude). True cross-family requires
the PY LLM-based variant.

## Concrete examples

### 2026-05-08 morning iteration
Used **agent-based** swarm extensively for 7+ hours: friction-debate
champions, DARWIN-IDEA-KILLER, Reducer (P13), explicit constructions,
literature scans. All Claude Code Agent invocations.

### 2026-05-07 evening
Existing `openmath_novel_ideas_swarm.py` ran with $5 budget cap across
Claude Opus 4.7 + GPT-5.5 + Gemini 3.1 Pro for cross-family creativity
on NS regularity novel ideas. Output at
`projects/ns_millennium_hunt/workspace/research_notes/openmath_novel_ideas_2026_05_07.md`.

### When to escalate from agent-based → PY LLM-based
- After 3+ rounds of Pattern-1 friction debate within Claude (single-
  family) produce convergent verdict
- Before claiming a primitive is "novel above the published frontier"
  (cross-family check per AGENTS.md §6e.0)
- When a paid budget is authorized AND the cross-family signal is
  load-bearing for the next decision

## Cross-references

- `scripts/openmath_novel_ideas_swarm.py` — PY LLM-based instance
- `scripts/surgical_swarm_panel.py` — PY LLM-based for Lean closure
- `scripts/swarm_vitali_to_integral.py` — specific math instance
- `feedback_typed_companion_swarm_decomposition.md` — ZTARE swarm
  superpattern memory
- `agentic_engineering_patterns.md` — sister catalog
