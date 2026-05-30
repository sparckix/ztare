---
id: PATTERN-011
name: swarm_dispatch
version: 2
status: active
discovered: 2026-05-08
triggers:
  lexical: [parallel, swarm, divide-and-conquer, cross-family, multiple-LLMs]
  structural: [N_independent_subtasks, cross_family_validation_needed, exploration_value_high, queueable_residual_stream, station_bottleneck_visible]
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
factory_overlay:
  mode: flow_line
  trigger: hard_residual_with_repeated_rows_or_candidates
  stations: [source_or_candidate_generation, execution_or_compile, governance_or_ratification, residual_to_lever, synthesis]
  required_metrics: [lead_time, cycle_time_per_station, throughput_per_station, WIP, rework_rate, bottleneck_station]
  queue_contract: durable_append_only_events_plus_claimed_work_queue
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
falsifiable_test: |
  Over N>=8 swarm deployments using the factory overlay, measured throughput at the
  bottleneck station after adding a worker must increase by >=1.5x relative to the
  pre-add bottleneck throughput on the same queue; AND wallclock for the swarmed
  task must be <=0.5x a matched serial baseline. If bottleneck throughput rises by
  <1.5x after worker-add (WIP inflation without throughput, the
  WORKER-BEFORE-BOTTLENECK anti-pattern) or wallclock is not at least halved,
  demote.
  metric_source: swarm factory-overlay telemetry (throughput_per_station,
  bottleneck_station, lead_time, cycle_time) recorded per the required_metrics
  contract; swarm dispatches tagged PATTERN-011 in pattern_deployment_ledger.jsonl.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 11, Swarm Dispatch

## Problem

Many architecture tasks decompose into **N independent subtasks** that
benefit from parallel execution: 3+ candidate constructions to test,
4+ alien-math angles to explore, K+ Mathlib-PR design reviews. Serial
execution wastes wallclock; serial-with-aggregation wastes operator
attention.

For repeated proof/research residuals, the failure mode is subtler:
the agent recognizes “parallelism” but still operates artisanal row by
row. That wastes the principal's attention and hides the bottleneck.
The correct primitive is a flow line: define stations, let work move
through queues, measure lead/cycle time at each station, and only then
add workers where the bottleneck actually is.

Two variants of the swarm primitive serve different needs:

* **Agent-based swarm**: spawn Claude Code subagents via the Agent tool.
  Single-family (Claude only). Free within session quota. Best for
  parallelism + orchestration.
* **PY LLM-based swarm**: direct-API dispatch across cross-family LLMs
  (Claude + GPT + Gemini). Real-dollar cost. Best for cross-family
  validation when single-family agreement is suspect.

## Pattern

1. Decompose task into N independent subtasks.
2. If the work is repeated/row-like/candidate-like, first design the
   **factory overlay**:
   - define stations, e.g. source acquisition → compile/action attempt
     → governance/ratification → residual-to-lever → synthesis;
   - define the event types moving between stations;
   - enforce single-consumer pickup for shared queues with an atomic
     claim/lease mechanism;
   - set WIP limits per station before adding workers;
   - log lead time, cycle time, throughput, rework, and bottleneck
     station.
3. Pick variant:
   - subtasks need cross-family validation → PY LLM-based
   - subtasks need parallelism only → Agent-based
   - mixed → both layers (Agent-based for breadth, PY for cross-family
     validation of K representatives)
4. Run BUDGET-ESTIMATE first if PY LLM-based ($5+ caps typical)
5. Dispatch
6. Aggregate via named strategy (union / vote / friction_debate /
   reducer)
7. Audit aggregate via PATTERN-002 darwin_idea_killer
8. Report the bottleneck and the next throughput lever; do not merely
   report that “parallelism was used.”

## Factory Overlay, Scientific Management Lens

Use this overlay whenever the residual is a stream rather than a single
bespoke theorem or decision.

**Stations.** Name each step that transforms the work item:

- source/candidate generation;
- execution/compile/probe;
- governance/ratification;
- residual classification;
- synthesis or new-lane construction.

**Queues.** Each station hands off via explicit event types. For proof
work, examples are `to_govern`, `closed`, and `path_c_residual`.
Queues must be durable enough to resume after interruption. Shared
queues need atomic claim/lease semantics; index-based sharding is
acceptable only for one-off controlled batches.

**WIP limits.** Add workers only where there is a measured bottleneck.
Do not flood a downstream verifier with unbounded compile closures.
Prefer a small buffer that keeps the bottleneck station fed.

**Telemetry.** Record:

- lead time: queue start to routed event;
- cycle time: station processing time;
- throughput: completed events per hour per station;
- rework rate: fallback/retry/residualized fraction;
- utilization: busy wall time divided by available station wall time;
- bottleneck station: the station with the lowest sustainable
  throughput.

**Learning loop.** Anything that does not close goes to the residual
station immediately. The agent's job is not to hand-triage every row
forever; it is to turn repeated residual classes into new station logic
or new lanes, then let governance test them.

## Why it works

Parallelism reduces wallclock 3-10x. Cross-family detects single-LLM
hallucinations (especially novelty claims). Budget caps prevent
runaway spend.

The factory overlay reduces operator touch-rate. It also prevents a
false throughput story: the measured bottleneck may be governance,
candidate sourcing, residual interpretation, or synthesis. The next
worker is added only at the bottleneck.

## When to deploy

- N≥3 truly independent subtasks
- repeated rows/candidates/residuals can be streamed through stations
- Single-family verdict suspected of bias
- Wallclock matters
- Exploration value > determinism value

## When NOT to use

- Subtasks have dependencies (serialize instead)
- Single-LLM verdict is sufficient (don't burn cross-family budget)
- The aggregator strategy isn't pre-decided (chaos)
- The queue cannot enforce single pickup and duplicate work would
  corrupt the measurement
- The bottleneck has not been measured and adding workers would only
  create WIP/rework

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

**ARTISANAL-SWARM**: dispatching or running one row at a time while
calling it a swarm. If the work items are repeated, build the queue,
station, and telemetry surface first.

**WORKER-BEFORE-BOTTLENECK**: adding workers before measuring station
cycle time. This can increase WIP while leaving throughput unchanged.

**DUPLICATE-CONSUMER-LAUNDERING**: multiple workers read the same queue
without atomic claim/lease and produce duplicate apparent throughput.
Use durable leases or disjoint shards.

**MEAN-CYCLE-TIME-LAUNDERING**: quoting mean throughput while the
central station has a heavy tail. Report tail cycle time when the
decision depends on reliability.

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
  central for the next decision

### 2026-05-20 GP-225 LeanSearch repair mill
The hard residual was not just a proof problem; it was a flow problem.
Path A produced compile closures and residuals, Path B governed closure
events, and Path C collected non-closures. The first queue used
append-only JSONL; the enforced queue used SQLite atomic claims/leases.
A two-worker benchmark initially failed to improve throughput because a
worker preclaimed both jobs; changing to claim-one/process-one let two
workers split the queue. This is now the canonical factory-overlay
lesson: parallelism must be enforced at the work-pickup boundary and
measured by station cycle time, not asserted by launching more workers.

## Cross-references

- `scripts/openmath_novel_ideas_swarm.py`, PY LLM-based instance
- `scripts/surgical_swarm_panel.py`, PY LLM-based for Lean closure
- `scripts/swarm_vitali_to_integral.py`, specific math instance
- `feedback_typed_companion_swarm_decomposition.md`, ZTARE swarm
  superpattern memory
- `agentic_engineering_patterns.md`, sister catalog
