---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke_20m
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs: []
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - named textbook axiom lists
  - source or literature lookup before finalist freeze
  - treating bounded closure as unrestricted truth
created_by: user
typed_blueprint: typed_blueprint_exact_two.json
budget:
  wall_clock: 20m
  provider_calls: 16
  agent_turns: 16
  input_tokens: 200000
  output_tokens: 80000
  metered_api_usd: "0"
  workbench_actions: 32
  adapter_forge_attempts: 0
  context:
    models: 25000
    truth_cells: 10000000
  boundary:
    queries: 2
    smt_calls: 2
    smt_time: 5m
    lean_attempts: 1
    lean_time: 15m
stop:
  max_finalists: 8
  low_yield_patience: 3
  min_marginal_information_per_cost: "0.05"
  coverage_target: "0.9"
runtime:
  transport: subscription_agent_runtime
  profile: smoke
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: low
      timeout_seconds: 1200
      visible_workbench: false
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: low
      timeout_seconds: 1200
      governed_pool: false
      allow_subscription_failover: false
frozen_context_ref:
  path: research_areas/pre_registrations/axiompack_gp251_smoke_20260710/formal_context.materialized.json
  context_hash: d22e5a390f117cbcbd4f1972dfb93d88b0e10db2bb5eaef1cf7b59c1f3e87206
  snapshot_sha256: 78192e763416d1ebca20072d1b171742fb70021d82bee026d17a629efa6fe24e
---

## Hypothesis

An exact-two anonymous campaign can separate a conjunction-specific theorem
from a proof script that merely happens to mention both premises when the
boundary checks every singleton against a frozen external implication relation.

## Eigenquestion

Can the navigator freeze a positive-residual two-law presentation whose target
is source-refuted under each law separately and then proved from the pair?

## Discriminating outcome

The host enforces exactly two premises. After freeze, source evidence runs
before SMT or Lean. A source-known singleton implication is rejected without
boundary spend. A target earns `proved_exact_two_synergy` only when both
singleton implications are source-refuted and the governed conditional proof
passes. Any other proved result remains proof-attributed only.

The known Equation 99/359 to Equation 8 implication is the low-difficulty
positive control for the source-ablation boundary, not a discovery target: both
singletons are source-refuted, the pair is proved, and the cheap endogenous
baseline already removes it from anonymous selection.

## Kill conditions

- a singleton presentation freezes;
- a source-known singleton implication reaches SMT or Lean;
- saved-proof leave-one-out failure is reported as logical premise minimality;
- source bytes or status semantics are not digest-bound;
- a no-candidate outcome lacks host-produced residual receipts.

No novelty claim follows from one run. A null is informative about the search
only after the positive-control boundary replay passes.
