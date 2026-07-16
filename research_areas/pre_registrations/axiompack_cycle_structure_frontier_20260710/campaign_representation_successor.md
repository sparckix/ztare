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
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - Do not use literature or familiar theory names before a candidate is frozen.
  - Do not nominate a coordinate that merely identifies its supplied finite witness pair.
budget:
  wall_clock: 30m
  provider_calls: 24
  agent_turns: 24
  metered_api_usd: "0"
  workbench_actions: 96
  adapter_forge_attempts: 1
  boundary:
    queries: 4
    smt_calls: 8
    smt_time: 8m
    formal_peer_attempts: 1
    formal_peer_time: 3m
    lean_attempts: 1
    lean_time: 5m
stop:
  max_finalists: 6
  low_yield_patience: 6
  when: Stop only when late independent review finds that at least two agent-authored or language-expansion coordinates compose into an out-of-seed-chart prediction worth boundary verification; otherwise continue search or return an unresolved receipt.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.6-sol
      reasoning_effort: high
      timeout_seconds: 1500
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.6-sol
      reasoning_effort: high
      timeout_seconds: 1500
    adapter_forge:
      runtime: codex
      model: gpt-5.6-sol
      reasoning_effort: high
      timeout_seconds: 1500
    adapter_reviewer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 900
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
      governed_pool: false
      allow_subscription_failover: false
---

Begin with the exact observational partition after consuming the frozen
predecessor coordinates. Investigate the remaining non-singleton classes as
evidence about a missing theory language, rather than assuming another short
equation is the right object. Each independent lineage may work inside the
current typed formula language or request a typed language expansion.

A successful lineage turns an anonymous exact contrast into a reusable theory
program with a prediction elsewhere in the chart or on a larger stratum. A
coordinate that only separates its supplied pair, repeats a witnessed no-good,
falls inside the named cheap baseline, or behaves like source identity is a
reason to change representation, not a finalist. Late synthesis may combine
independently developed lineages, but nomination requires residual consequence
beyond every coordinate alone. If the available language cannot do this,
return the receipted representation gap without inventing a discovery claim.
