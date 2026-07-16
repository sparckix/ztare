---
schema: leanmill.campaign.v1
lane: axiompack
profile: overnight
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs: []
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
- pre-freeze literature lookup or named-theory recovery
- decorative cycle, orbit, gcd, retraction, or decomposition metadata without an executable capability receipt
- treating reproduction of the published finite-multipermutation implication as discovery
- treating bounded counterexample absence as an unrestricted implication
- treating a finite correlation as a decomposition proof
created_by: user
budget:
  wall_clock: 12h
  provider_calls: 144
  agent_turns: 180
  input_tokens: 5000000
  output_tokens: 1600000
  metered_api_usd: '0'
  workbench_actions: 576
  adapter_forge_attempts: 8
  context:
    models: 1000000
    truth_cells: 500000000
  boundary:
    queries: 72
    smt_calls: 72
    smt_time: 21600000ms
    formal_peer_attempts: 36
    formal_peer_time: 10800000ms
    lean_attempts: 36
    lean_time: 21600000ms
stop:
  max_finalists: 8
  low_yield_patience: 3
  min_marginal_information_per_cost: '0.05'
  coverage_target: '0.9'
  when: null
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
    adapter_forge:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
    adapter_reviewer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 1800
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 1800
typed_blueprint: campaign_v3.typed_blueprint.json
---

Investigate the unrestricted Ramírez–Vendramin coprime-cycle decomposability question for finite cycle sets. Compile the initial exact substrate using the already executable definitional expansion with one carrier S0, a primary binary operation op0, its rowwise inverse binary operation op1, and the inverse op2 of the diagonal map. The base theory must contain exactly these executable laws: op0(x,op1(x,y))=y; op1(x,op0(x,y))=y; op0(op0(x,y),op0(x,z))=op0(op0(y,x),op0(y,z)); op2(op0(x,x))=x; and op0(op2(x),op2(x))=x. These equations encode bijective left translations and nondegeneracy on finite carriers. Do not introduce orbit, cycle, gcd, retraction, transitivity, or decomposition relation symbols unless a registered adapter actually evaluates them. Start from exact small-order tables, and let isolated navigators request a typed language expansion or campaign-local reviewed capability for left-translation cycle lengths, carrier-size coprimality, action orbits, retraction, and decomposition. The target asks whether a nontrivial cycle in some left translation whose length is coprime to the carrier size forces decomposability, without assuming finite multipermutation level. Seek either a fully checked indecomposable counterexample or a compact invariant/representation that advances the unrestricted implication. Recovery of the published finite-primitive or multipermutation theorem is calibration. Bounded no-counterexample output is not a theorem.
