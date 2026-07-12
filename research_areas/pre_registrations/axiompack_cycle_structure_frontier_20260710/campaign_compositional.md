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
  provider_calls: 30
  agent_turns: 30
  input_tokens: 600000
  output_tokens: 180000
  metered_api_usd: "0"
  workbench_actions: 96
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
  low_yield_patience: 6
  min_marginal_information_per_cost: "0.005"
  coverage_target: "0.99"
  when: Stop only when late independent review finds that at least two agent-authored or language-expansion coordinates compose into an out-of-seed-chart prediction worth boundary verification; otherwise continue search or return an unresolved receipt.
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
---

Explore competing theory programs over the frozen anonymous signature. Treat
the finite chart as an instrument rather than the theory. The executable
blueprint alone owns the seed and withheld boundary strata; their separation
keeps orientation within the host budget without removing larger carriers from
the scientific question. Each isolated
lineage may inspect the current semantic quotient, author typed coordinates,
request a richer executable language, freeze hypotheses of any permitted
width, and nominate explicit predictions.

Prefer moves that create consequential predictive distinctions on contexts the
seed chart does not settle. A new coordinate by itself is an intermediate
representation result. The stronger outcome requires interaction among
multiple agent-authored coordinates, an actual host-witnessed disagreement
between frozen programs, and lift beyond the seed context. A familiar named law
recovered from the chart is a null for novelty. Return a receipted refusal or
exhaustion state when no such route survives.
