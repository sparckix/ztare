---
schema: leanmill.campaign.v1
lane: axiompack
profile: standard
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
  - treating one new finite profile as a mathematical result
  - treating absence of a prediction as a negative prediction
  - treating a direct base rewrite, inverse-definition simplification, projection, constant, singleton, or empty extent as interesting
  - treating bounded persistence as an unrestricted theorem
  - treating the seed grammar as the campaign ceiling
created_by: user
typed_blueprint: typed_blueprint_compositional.json
budget:
  wall_clock: 30m
  provider_calls: 60
  agent_turns: 60
  input_tokens: 600000
  output_tokens: 180000
  metered_api_usd: "0"
  workbench_actions: 144
  adapter_forge_attempts: 0
  context:
    models: 30000
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
  low_yield_patience: 8
  min_marginal_information_per_cost: "0.005"
  coverage_target: "0.99"
  when: Stop only when late independent review finds that at least two agent-authored or language-expansion coordinates compose into an out-of-seed-chart prediction worth boundary verification; otherwise continue search or return an unresolved receipt.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 900
      visible_workbench: false
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 900
      visible_workbench: false
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 300
      governed_pool: false
      allow_subscription_failover: false
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 600
---

Run a substantive cold theory-invention campaign over the frozen anonymous
signature. The finite chart is an instrument rather than the theory. Three
isolated lineages should independently inspect the chart, author typed
coordinates or language requests, and nominate explicit predictions. The host
may compare lineages only after their receipts are frozen; it must not turn a
single recovered seed identity into a novelty claim.

The intended scientific bar is compositional: at least two authored or
language-expansion coordinates must survive exact host admission, produce a
host-witnessed disagreement or residual prediction beyond the seed chart, and
lift through larger-carrier SMT, an optional Isabelle peer, and governed Lean
attribution. A familiar named law, a direct rewrite, or a bounded consequence
is a recovery/control outcome. If the lineages exhaust capacity, retain their
typed exhaustion receipts and report the campaign as unresolved rather than
silently converting it into a refusal.
