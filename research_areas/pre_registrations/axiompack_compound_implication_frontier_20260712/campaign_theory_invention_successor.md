---
schema: leanmill.campaign.v1
lane: axiompack
profile: standard
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs:
  - https://github.com/teorth/equational_theories
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - equation numbers, named laws, or literature lookup before finalist freeze
  - single-premise implications
  - treating a logical product as one prediction coordinate
  - treating finite persistence as unrestricted proof
created_by: user
typed_blueprint: typed_blueprint_theory_invention.json
budget:
  wall_clock: 20m
  provider_calls: 24
  agent_turns: 24
  input_tokens: 480000
  output_tokens: 120000
  metered_api_usd: "0"
  workbench_actions: 72
  adapter_forge_attempts: 1
  context:
    models: 25000
    truth_cells: 15000000
  boundary:
    queries: 6
    smt_calls: 12
    smt_time: 8m
    formal_peer_attempts: 2
    formal_peer_time: 3m
    lean_attempts: 2
    lean_time: 8m
stop:
  max_finalists: 6
  low_yield_patience: 6
  min_marginal_information_per_cost: "0.005"
  coverage_target: "0.99"
  when: Stop only when late independent review finds a representation or theory program that changes what can be derived or tested beyond the initial chart and is worth cross-order or formal verification; otherwise evolve the theory language or return an unresolved receipt. Catalog selection alone does not satisfy this condition.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 1200
      visible_workbench: false
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 1200
      visible_workbench: false
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
      governed_pool: false
      allow_subscription_failover: false
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
frozen_context_ref:
  path: research_areas/pre_registrations/axiompack_gp251_smoke_20260710/formal_context.materialized.json
  context_hash: d22e5a390f117cbcbd4f1972dfb93d88b0e10db2bb5eaef1cf7b59c1f3e87206
  snapshot_sha256: 78192e763416d1ebca20072d1b171742fb70021d82bee026d17a629efa6fe24e
---

Explore anonymous theories over one total binary operation. Treat the frozen
formula-model chart as an exact instrument and allow its counterexamples and
blind spots to change the representation. Choose or invent the coordinates,
definitions, theory language, hypotheses, and consequential predictions.

Develop two host-isolated conjectural lineages without assigning them mechanism
families. Each lineage may navigate the initial chart, author a typed formula,
or request a new observable, quotient, primitive, or abstraction. A boundary
candidate must make every premise consequential and must justify why its
prediction changes derivability or testability beyond the current chart.
Counterexamples should update the next conjecture across the whole survivor
pool. Late synthesis owns the boundary decision.
