---
schema: leanmill.campaign.v1
lane: axiompack
profile: standard
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs: []
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - named ternary-quasigroup laws or literature lookup before finalist freeze
  - seed-chart residuals erased by the declared equational baseline
  - treating finite separation or formal provability as novelty
created_by: user
budget:
  wall_clock: 20m
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
      timeout_seconds: 600
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
typed_blueprint: campaign.typed_blueprint.json
---

Re-enter the anonymous finite ternary-quasigroup context after correcting its
equational residual baseline. Treat the initial equation chart as a diagnostic
instrument. Let isolated navigators choose which blind spot, derived operation,
observable, quotient, or formula should change the representation. Admit an
expensive boundary question only when an authored coordinate participates in
the nominated theory program and its prediction is separately identified.

The causal discriminator is whether removing the false seed residual causes a
leaf to change the theory language. Exact finite evaluation, larger-carrier
countermodels, and formal systems remain referees; they do not choose the move.
