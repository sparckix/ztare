---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke_20m
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs:
  - https://arxiv.org/abs/1210.3285
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - named identity lists beyond the frozen regular-unary base
  - literature lookup before finalist freeze
  - treating bounded closure or failed finite search as unrestricted truth
  - treating an inverse-semigroup characterization as a hidden target
created_by: user
typed_blueprint: typed_blueprint_regular_unary.json
budget:
  wall_clock: 20m
  provider_calls: 12
  agent_turns: 12
  input_tokens: 160000
  output_tokens: 50000
  metered_api_usd: "0"
  workbench_actions: 40
  adapter_forge_attempts: 0
  context:
    models: 600000
    truth_cells: 50000000
  boundary:
    queries: 2
    smt_calls: 4
    smt_time: 3m
    lean_attempts: 1
    lean_time: 10m
stop:
  max_finalists: 4
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
      timeout_seconds: 600
      governed_pool: false
      allow_subscription_failover: false
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: low
      timeout_seconds: 300
---

Explore short, anonymous, exact-two theory presentations over regular unary
semigroups: an associative binary operation together with a selected inverse
for each element. Prefer candidates whose residual survives the cheap
equational baseline and whose target has a concrete countermodel under each
singleton premise. A receipted no-candidate outcome is legitimate.

Inverse semigroups are a post-freeze comparison region, not a hidden target.
The navigator sees anonymous operations, formulas, finite profiles,
countermodels, costs, and receipts.
