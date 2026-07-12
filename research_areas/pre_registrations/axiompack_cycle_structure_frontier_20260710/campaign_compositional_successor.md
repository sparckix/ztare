---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke_20m
source_mode: structure_first
requested_mode: anonymous_signature_census
created_by: user
typed_blueprint: typed_blueprint_compositional.json
predecessor_synthesis_ref:
  path: research_areas/pre_registrations/axiompack_cycle_structure_frontier_20260710/frozen_synthesis_input_wave1.json
  input_sha256: cb589f64cfc00d841e299234d7e87482aca1cb3974dd537fa12830f0dd40310b
budget:
  wall_clock: 20m
  provider_calls: 16
  agent_turns: 16
  metered_api_usd: "0"
  workbench_actions: 64
  adapter_forge_attempts: 0
  boundary:
    queries: 3
    smt_calls: 6
    smt_time: 6m
    formal_peer_attempts: 1
    formal_peer_time: 2m
    lean_attempts: 1
    lean_time: 4m
stop:
  max_finalists: 4
  low_yield_patience: 4
  when: Stop only when late independent review finds that at least two agent-authored or language-expansion coordinates compose into an out-of-seed-chart prediction worth boundary verification; otherwise continue search or return an unresolved receipt.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 1200
    lineage_synthesizer:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 1200
    lean_solver:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 600
      governed_pool: false
      allow_subscription_failover: false
---

Consume the frozen predecessor coordinates through the typed admission
transition. Rebuild the exact context, test their pairwise and joint
consequences, and nominate boundary queries only when the enriched chart shows
a prediction unavailable to each coordinate alone. Preserve the anonymous
signature and return a receipted unresolved state if composition adds no
consequential distinction.
