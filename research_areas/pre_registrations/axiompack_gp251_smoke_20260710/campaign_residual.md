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
  - literature lookup before finalist freeze
  - treating bounded closure as unrestricted truth
created_by: user
typed_blueprint: typed_blueprint.json
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

Explore the anonymous landscape of two-law theories for one total binary
operation. Choose a presentation only when its visible, host-computed
consequence residual justifies boundary verification after the named cheap
deduction baseline is removed. A receipted no-candidate outcome is legitimate.
