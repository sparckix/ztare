---
id: PATTERN-028
name: recursive_tool_depth_loop
version: 2
status: active
discovered: 2026-05-20
discovered_reason: |
  Hard residual ticks repeatedly produced a shallow sequence: pencil sketch,
  single formal edit, then close pressure.  TICK663/TICK664 showed the better
  sequence: pencil work exposed the candidate interface, the domain workbench
  and reusable primitives caught declaration-only or under-separated fields,
  Lean encoded the corrected surface, and a second tool pass checked the patch.
triggers:
  lexical:
    - depth-n
    - recursive work
    - workbench
    - primitives
    - tool underuse
    - formal frontier
    - proof frontier
  structural:
    - hard_residual_has_domain_tools_available
    - formal_edit_planned_after_single_pencil_pass
    - workbench_or_primitives_exist_but_are_not_consumed
    - tool_output_names_missing_discriminator
    - close_pressure_before_second_stress_pass
  problem_classes:
    - hard_mathematical_residual
    - hard_research_residual
    - proof_frontier
    - formal_frontier
composition:
  complements:
    - PATTERN-011
    - PATTERN-025
  mitigates:
    - ANTI-PATTERN-018
spawn:
  mode: recursive_research_loop
  output_schema: research_depth_receipt_loop_v1
chain_position: in_tick
related_patterns:
  - id: PATTERN-011
    relation: swarm breadth; one or more lanes can each run this loop
  - id: PATTERN-025
    relation: pencil-first supplies the first orientation artifact
references:
  - AGENTS.md §0a2 2d1/2e1/2e2
  - org/mandates/research_director_mandate.md v1.66/v1.69
  - org/anti-patterns/tool_underuse_formal_satisficing.md
falsifiable_test: |
  Once wired as an in-tick loop, over N>=15 hard-residual ticks with available
  domain tools, ticks running >=2 explicit research loops (per the five-leg
  structure) must close with a checked artifact that changed the residual graph OR
  a named-primitive kill in >=70% of cases, versus a matched baseline of
  single-pencil-pass / single-compile ticks on comparable residuals; the deep-loop
  graph-change rate must exceed the shallow baseline by >=25 percentage points.
  Additionally, class-matched tools skipped without a logged why_not must be 0
  across the N. If the deep-loop graph-change rate is within 25 points of the
  shallow baseline, the second loop surfaces no new information and the pattern
  demotes.
  metric_source: research_depth_receipt_loop_v1 outputs (loop count, tool why_not
  lines, stop-rule classification) joined to F-rows / architecture graph deltas;
  PATTERN-028 ticks tagged in pattern_deployment_ledger.jsonl.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-028 — Recursive Tool-Depth Loop

## Problem

For hard research residuals, agents drift toward the nearest executable
feedback.  If closure and compilation have stronger feedback than research
depth, the agent will often stop after one pencil pass and one formal edit.
That creates polished surfaces while leaving available domain tools idle.

## Pattern

Run hard residuals through at least two explicit research loops before close,
unless the first loop produces a decisive kill.

Each loop has five legs:

1. **Orientation:** pencil artifact or prior-lane synthesis. State the
   eigenquestion, candidate theorem or obstruction, kill condition, and the
   planned formal/tool surface.
2. **Tool pass:** consume the best available domain workbench, deterministic
   gate, graph query, dimensional/asymptotic check, primitive catalog entry,
   or substrate-specific scout. Record a one-line `why_not` for each
   class-matched tool skipped.
3. **Estimate/witness pass:** if the tool pass returns a candidate route rather
   than a hard failure, attempt the actual estimate, construction, or sharp
   hostile witness before closing. A workbench pack is a prompt to act, not a
   substitute for the mathematical attempt.
4. **Artifact pass:** produce or revise the formal surface, code primitive,
   falsifier, graph query, or typed interface.
5. **Stress pass:** rerun the tool or an adversarial lane against the artifact.
   Classify the result as `promote`, `boundary`, `kill`, or `needs_tool`.

If the tool pass exposes a reusable missing discriminator, improve the
reusable primitive layer with structured input/output and a small test before
continuing.  Keep substrate vocabulary at the caller/profile layer unless the
concept is genuinely substrate-invariant.

## Stop Rule

Enough work for the tick means one of:

- a compiled or otherwise checked artifact changed the residual graph;
- an adversarial stress pass killed the route with a named missing primitive;
- the second loop found no new information and the remaining live vector is
  explicitly named for the next tick;
- a tool gap was promoted into reusable machinery and rerun against the
  current artifact.

## Anti-pattern

ANTI-PATTERN-018 fires when a hard residual has available tools/primitives,
but the agent edits the formal/code surface after one pencil pass, or closes
after one compile, without consuming those tools or explaining non-use.
