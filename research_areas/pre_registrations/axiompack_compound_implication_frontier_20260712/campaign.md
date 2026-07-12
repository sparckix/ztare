---
schema: leanmill.campaign.v1
lane: axiompack
profile: standard
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs:
  - https://github.com/teorth/equational_theories
  - https://github.com/teorth/equational_theories/wiki/Plan-of-paper
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - equation numbers, named laws, or literature lookup before finalist freeze
  - single-premise implications
  - seed-refuted or vacuous predictions
  - treating a new finite profile as a theory result
  - treating finite persistence as unrestricted proof
  - forcing the seed equation grammar to remain the hypothesis horizon
created_by: user
typed_blueprint: typed_blueprint.json
budget:
  wall_clock: 30m
  provider_calls: 30
  agent_turns: 30
  input_tokens: 600000
  output_tokens: 180000
  metered_api_usd: "0"
  workbench_actions: 96
  adapter_forge_attempts: 0
  context:
    models: 25000
    truth_cells: 15000000
  boundary:
    queries: 4
    smt_calls: 8
    smt_time: 10m
    formal_peer_attempts: 2
    formal_peer_time: 4m
    lean_attempts: 2
    lean_time: 10m
stop:
  max_finalists: 6
  low_yield_patience: 6
  min_marginal_information_per_cost: "0.005"
  coverage_target: "0.99"
  when: Stop only when late independent review finds an irreducible compound prediction supported by the exact seed chart and worth larger-carrier verification; otherwise evolve the theory language, continue search, or return an unresolved receipt.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 1800
      visible_workbench: false
    lineage_synthesizer:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 1800
      visible_workbench: false
    lean_solver:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 600
      governed_pool: false
      allow_subscription_failover: false
    post_freeze_interpreter:
      runtime: codex
      model: sol
      reasoning_effort: medium
      timeout_seconds: 600
frozen_context_ref:
  path: research_areas/pre_registrations/axiompack_gp251_smoke_20260710/formal_context.materialized.json
  context_hash: d22e5a390f117cbcbd4f1972dfb93d88b0e10db2bb5eaef1cf7b59c1f3e87206
  snapshot_sha256: 78192e763416d1ebca20072d1b171742fb70021d82bee026d17a629efa6fe24e
---

Explore anonymous theories over one total binary operation. Use the frozen
equation chart only for orientation. Develop multiple isolated conjectural
lineages and search for presentations of two to four hypotheses with explicit
predictions.

A promising compound prediction holds on the complete seed chart while every
leave-one-premise-out theory has a concrete countermodel. Prefer predictions
that cross distinct semantic regions and cannot be explained by the frozen
single-premise implication baseline. If the seed language aliases the needed
distinction, author a typed formula or request a richer theory language.

Counterexamples return a program to search. Freeze only a surviving prediction
whose larger-carrier test could change the theory. The finite chart is the
referee for this stage, not the campaign's theory identity.
