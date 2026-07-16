---
schema: leanmill.campaign.v1
lane: axiompack
profile: quick
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
  input_tokens: 400000
  output_tokens: 160000
  metered_api_usd: '0'
  workbench_actions: 192
  adapter_forge_attempts: 1
  context:
    models: 5000
    truth_cells: 5000000
  boundary:
    queries: 6
    smt_calls: 12
    smt_time: 12m
    formal_peer_attempts: 2
    formal_peer_time: 360000ms
    lean_attempts: 2
    lean_time: 600000ms
stop:
  max_finalists: 6
  low_yield_patience: 6
  min_marginal_information_per_cost: '0.01'
  coverage_target: '0.98'
  when: Stop only after either an agent-origin representation, obstruction, or compact law family survives held-out size 4/5 and unrestricted verification and changes a classification or construction question; an exact, receipted language insufficiency yields a concrete successor representation request; or budget exhaustion leaves per-candidate reject-all receipts without a mathematical absence claim.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 900
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: medium
      timeout_seconds: 900
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

Explore finite nondegenerate elementary set-theoretic tetrahedron maps without showing the cold navigators any theory name or published law. Compile with the registered generic_fol_finite.v1 adapter: one sort S0 and one total ternary operation op0. The frozen base theory has exactly two laws. First, middle-coordinate recoverability: for all x,y,z,y2, op0(x,y,z)=op0(x,y2,z) implies y=y2. Second, the middle-coordinate tetrahedron coherence identity: for all x,y,z,t,p,q, op0(op0(x,y,z),op0(x,t,p),q)=op0(x,op0(y,t,q),op0(z,p,q)). Use complete isomorphism-quotiented finite censuses at carrier sizes 2 and 3; these are known preflight-feasible. Use a bounded universal-equation grammar through total operation order 2 initially, while allowing the agents to request derived observables, quotients, or a successor grammar. Hold out carrier sizes 4 and 5 for counterexamples. Let four isolated navigators invent independent theory languages and compact basis fragments; exact finite geometry, SMT, Isabelle, and Lean are referees only. Projection, constant, base-law restatements, routine substitution consequences, and finite separation alone are calibration. Seek a representation-changing invariant, obstruction, or compact law family that survives cross-order tests and changes a classification or construction question. A null result must be receipted per candidate and may not be upgraded into a negative theorem.
