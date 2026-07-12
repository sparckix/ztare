---
schema: leanmill.campaign.v1
lane: axiompack
profile: quick
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs:
  - https://arxiv.org/abs/1210.3285
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - named identity lists beyond the frozen regular-unary base
  - literature lookup before finalist freeze
  - treating a syntactic variant or primitive operation collapse as information
  - treating bounded closure or failed finite search as unrestricted truth
  - treating an inverse-semigroup characterization as a hidden target
created_by: user
typed_blueprint: typed_blueprint_regular_unary.json
budget:
  wall_clock: 30m
  provider_calls: 12
  agent_turns: 12
  input_tokens: 240000
  output_tokens: 80000
  metered_api_usd: "0"
  workbench_actions: 48
  adapter_forge_attempts: 0
  context:
    models: 600000
    truth_cells: 55000000
  boundary:
    queries: 2
    smt_calls: 4
    smt_time: 4m
    formal_peer_attempts: 1
    formal_peer_time: 2m
    lean_attempts: 1
    lean_time: 10m
stop:
  max_finalists: 4
  low_yield_patience: 4
  min_marginal_information_per_cost: "0.05"
  coverage_target: "0.95"
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
---

Explore anonymous exact-two presentations over the frozen regular-unary
semigroup structure. Treat the complete operation-order-two census as an
orientation chart. If that chart cannot express the next discriminating
structural conjecture, use the typed frontier-formula action to add an equation
over the anonymous signature and continue in the rebuilt exact context.

Prefer mechanisms whose joint consequences survive the finite-structure
baseline and have a concrete countermodel under each singleton premise. A
receipted no-candidate result is legitimate. Do not nominate a tautology,
semantic duplicate, direct rewrite, or constant/projection collapse merely to
avoid a null result.

Host-authenticated prior conflicts may identify presentations or implications
already disposed of by replayable zero-residual or finite-countermodel
witnesses. Treat those as memory, not as a search procedure; choose the next
structural distinction yourself.
