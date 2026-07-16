---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke_20m
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs: []
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts: []
created_by: user
budget:
  wall_clock: 30m
  provider_calls: 48
  agent_turns: 48
  input_tokens: 300000
  output_tokens: 120000
  metered_api_usd: '0'
  workbench_actions: 128
  adapter_forge_attempts: 1
  context:
    models: 25000
    truth_cells: 10000000
  boundary:
    queries: 4
    smt_calls: 4
    smt_time: 8m
    formal_peer_attempts: 1
    formal_peer_time: 180000ms
    lean_attempts: 1
    lean_time: 600000ms
stop:
  max_finalists: 6
  low_yield_patience: 6
  min_marginal_information_per_cost: '0.02'
  coverage_target: '0.95'
  when: Stop only for a nontrivial agent-origin law or compact basis that changes what can be derived or tested beyond the initial chart, with premise necessity, cross-order persistence, and unrestricted verification.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
typed_blueprint: campaign.typed_blueprint.json
---

Explore finite ternary quasigroups extensionally: an anonymous ternary operation whose missing input is uniquely recoverable in each coordinate. Compile executable finite semantics without supplying named axiom systems, standard identities, or candidate laws. Let isolated navigators invent derived operations, equations, quotients, observables, and compound theory programs; use counterexamples to revise both representation and theory. Test predictions on held-out order-4 and order-5 Latin-cube structures and in formal systems. Recovery of standard quasigroup consequences is calibration only. Stop only for a nontrivial agent-origin law or compact basis that changes what can be derived or tested beyond the initial chart, with premise necessity, cross-order persistence, and unrestricted verification.
