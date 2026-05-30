---
id: PATTERN-022
name: bundle_discriminator_stack
version: 1
status: candidate
discovered: 2026-05-13
discovered_reason: |
  GP-225 v18.21-v18.25 compressed shard generation, deterministic/public
  baseline subtraction, residual sizing, and CPU-vs-text comparison into
  one staged discriminator stack. Operator correctly flagged that this was
  more specific than "pull forward" or "swarm": the missing move was to
  prewire downstream gates whose artifact contracts were already known.
  Prior sequential ticks were over-cautious after the strict witness stack
  stabilized.
triggers:
  lexical: [bundle, bundling, 10x, bridge, compress, "why not faster", "pull forward", "maximum progress"]
  structural:
    - upstream_run_has_stable_artifact_contract
    - downstream_gate_is_deterministic_given_upstream_artifact
    - repeated_single_discriminator_ticks_delay_gate_answer
    - strict_witness_or_resolver_stack_already_stable
    - operator_generic_speed_pressure_changes_lane_choice
  problem_classes:
    - apparatus_self_audit.local_hillclimb_or_promotion_gate_stall
    - too_complex_direct_attack.lane_compression_needed
composition:
  derives_from:
    - PATTERN-020  # meta_arc_stall_resolution: identify stalled local hillclimb
    - PATTERN-012  # prediction_ledger: pre-register bundle gates and effort
    - PATTERN-011  # swarm_dispatch: only for independent sub-lanes inside bundle
  not_a_replacement_for:
    - PATTERN-005  # falsifiable_asymmetry: bundle still needs pass/fail gates
    - PATTERN-006  # tautology_trap: bundle can accelerate tautology if gates are weak
spawn:
  mode: staged_runner_or_agent_plan
  required_bundle_contract:
    - upstream_artifact_path
    - downstream_scripts_or_gates
    - pre_registered_thresholds_for_each_gate
    - stop_conditions
    - false_positive_controls
    - closure_plan
output_schema: bundle_discriminator_stack_v1
references:
  - GP-225 v18.21-v18.25 F-row: F-GP225-BUNDLE-DISCRIMINATOR-STACK-SHOULD-BE-ORCHESTRATION-PRIMITIVE-20260513-207
  - scripts/public/models/gnn_lemma_relevance/v1821_third_hard_decoy_shard.py
  - scripts/public/models/gnn_lemma_relevance/v1822_three_shard_residual_bridge.py
  - scripts/public/models/gnn_lemma_relevance/v1824_four_shard_residual_bridge.py
  - scripts/public/models/gnn_lemma_relevance/v1825_cpu_vs_text_cross_encoder_gate.py
falsifiable_test: |
  Over N>=8 bundled discriminator stacks, the bundle must reach the promotion-gate
  answer in <=0.5x the wallclock (or <=0.5x the dispatch count) of the matched
  sequential single-tick baseline for the same gate, WITHOUT raising the downstream
  false-positive rate by more than 5 percentage points versus that baseline. If the
  bundle does not at least halve time-to-gate-answer, or it inflates false
  positives by >5 points (the speed-theater / false-positive-amnesia anti-pattern),
  demote.
  metric_source: F-rows / E-rows for bundled-stack runs (e.g. F-GP225-BUNDLE-...)
  compared against sequential-tick F-rows on the same gate; false-positive rate
  from the witness-stack control logs.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-022 — Bundle Discriminator Stack

## What This Pattern Is

Bundle Discriminator Stack is a **composition pattern**: when the current
run has a stable artifact contract and the next discriminators are already
known, build the upstream run and downstream gates as one staged stack.

It is not generic parallelism. It is not merely "pull forward." It is the
discipline of prewiring the whole evidence ladder:

1. generate or harvest the next artifact;
2. immediately subtract locked deterministic/public baselines;
3. recompute the residual;
4. run the next cheap model or falsifier gate;
5. close the whole bundle with predictions and E/F rows.

## When To Deploy

Deploy when all are true:

- The witness/resolver stack is stable enough that false-positive controls
  are not being actively redesigned.
- The upstream artifact path is predictable.
- The downstream gate can run deterministically from that artifact.
- The question is gate movement, not exploratory interpretation.
- The operator or RD notices repeated single-step ticks around the same
  promotion boundary.

## When Not To Deploy

Do not bundle when:

- the witness filter is still changing;
- downstream gates require subjective interpretation;
- the next step depends on unknown human theory choices;
- independent subtasks would race on the same write set;
- the bundle would hide a failed precondition.

## Required Contract

Before dispatch, write or log:

- `upstream_artifact_path`
- downstream gate scripts or planned commands
- per-gate success thresholds
- false-positive controls
- stop conditions
- closure artifacts

If any downstream gate is speculative, split it out. Bundle only stable
derivations from known artifacts to known discriminators.

## Anti-Laundering Catches

- **Bundle-as-speed-theater:** bundling weak gates only makes bad evidence
  arrive faster. Every sub-gate must have a falsifiable threshold.
- **Hidden dependency:** if gate B cannot run unless gate A is interpreted
  by a human, the stack is not bundle-ready.
- **Generator overfit:** repeated bundled shards from the same generator
  can manufacture confidence. Add source/generator-family holdout before
  model-class claims.
- **False-positive amnesia:** bundling is allowed only after the witness
  stack is stable; otherwise the bundle accelerates bad labels.

## GP-225 Instance

The GP-225 pre-GNN lane stalled because each tick answered one piece:
shard generation, residual recomputation, BM25 subtraction, then cheap
model comparison. Once the strict witness stack was stable, these were
deterministic derivations from one artifact to the next. Bundling v18.21
through v18.25 compressed the lane and showed:

- row scale increased to four shards;
- BM25/type-kind absorbed accessible declaration refs;
- non-BM25 residual reached the CPU-vs-cross-encoder gate;
- compact text interaction lost to CPU features;
- GNN stayed blocked with better evidence.

That is the intended use: faster gate movement without relaxing controls.
