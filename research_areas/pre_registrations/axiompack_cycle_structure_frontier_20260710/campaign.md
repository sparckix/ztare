---
schema: leanmill.campaign.v1
lane: axiompack
profile: quick
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs:
  - https://arxiv.org/abs/2501.14363
  - https://arxiv.org/abs/2311.07112
  - https://arxiv.org/abs/2008.04483
  - https://github.com/vendramin/enumeration
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - literature lookup or named-class recovery before finalist freeze
  - treating reproduction of published finite counts as a discovery
  - treating a direct base rewrite or inverse-definition simplification as information
  - treating a constant, projection, singleton, or empty extent as an interesting region
  - treating bounded finite persistence as an unrestricted theorem
  - treating the seed grammar as the campaign ceiling
created_by: user
typed_blueprint: typed_blueprint.json
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
    models: 25000
    truth_cells: 10000000
  boundary:
    queries: 3
    smt_calls: 6
    smt_time: 8m
    formal_peer_attempts: 1
    formal_peer_time: 2m
    lean_attempts: 1
    lean_time: 10m
stop:
  max_finalists: 3
  low_yield_patience: 4
  min_marginal_information_per_cost: "0.01"
  coverage_target: "0.98"
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
      runtime: claude
      model: fable
      reasoning_effort: medium
      timeout_seconds: 600
---

Explore exact-two axiom packs over the frozen anonymous signature. The
operation-order-two universe is an orientation chart, not a restriction on
conjecture authorship. If its semantic profiles only expose routine regions,
use the typed formula-proposal action to add a structurally motivated equation
and continue in the rebuilt exact context.

Prefer pairs whose conjunction selects a nonempty, nontrivial family; whose
consequences are absent from either singleton premise; and whose residual
survives the host's equational and finite-structure baselines. A receipted
reject-all is preferable to nominating a definitional simplification. Freeze
before any source interpretation, then spend boundary work only on finalists
that retain nonzero residual information.
