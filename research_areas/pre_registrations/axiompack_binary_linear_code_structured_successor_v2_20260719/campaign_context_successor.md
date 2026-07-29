---
schema: leanmill.campaign.v1
lane: axiompack
profile: overnight
source_mode: structure_first
requested_mode: evidence_induced
typed_blueprint: predecessor_blueprint.json
frozen_context_ref:
  path: research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/predecessor_evidence_context.json
  context_hash: cea626fbdabe2c53ebdb61966a32ce9ab5161d9349a8a802874efa9442bedab9
  snapshot_sha256: f256b6793486004299403ba77440a9064ce4ebbd9ec69b104f808a3393d4f15d
evidence_refs:
- research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/experiment_contract.md
- research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/lane_cold_family.md
- research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/lane_family_adversary.md
- research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/lane_literature_frontier.md
- research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/cold_family_stress.md
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/external_target_snapshot.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/fresh_source_replay.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/binary_code_control_replay.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/campaign_adapter_config.json
deanchoring_intent: family_authored_before_target_enumeration_with_carried_adapter_identity
forbidden_shortcuts:
- resuming unconstrained raw generator-matrix proposals
- replacing the carried binary_linear_code.v1 adapter identity from prose similarity
- treating a sampled family as an exhausted family
- treating a family-scoped null as nonexistence of a binary linear code
- crediting a matrix before exact rank and all-nonzero-message distance replay
- crediting deterministic host verification as kernel ratification
- allowing the host to select generator rows, generator polynomials, family parameters, or a construction composition
- accepting an unreviewed or non-finite construction-family schema
- mutating a global adapter registry from a campaign leaf
- claiming priority without a fresh table and primary-source replay
created_by: codex:RD
budget:
  wall_clock: 7h
  provider_calls: 56
  agent_turns: 90
  input_tokens: 2400000
  output_tokens: 820000
  metered_api_usd: '0'
  workbench_actions: 440
  adapter_forge_attempts: 4
  context:
    models: 100000
    truth_cells: 10000000
  boundary:
    queries: 80
    smt_calls: 0
    smt_time: 0ms
    formal_peer_attempts: 12
    formal_peer_time: 7200000ms
    lean_attempts: 12
    lean_time: 7200000ms
stop:
  max_finalists: 8
  low_yield_patience: 3
  min_marginal_information_per_cost: '0.03'
  coverage_target: '1.0'
  when: Stop after an exact rank-20 length-50 generator reaches minimum distance at least 14 and enters current-policy construction-artifact ratification; one campaign-authored finite construction family is completely enumerated with replayable member-level rejection receipts and a typed next representation; the remaining split expires; or a typed runtime failure prevents the family from becoming executable. Never infer global code nonexistence from a family result.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    semantic_reviewer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 1800
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
    witness_constructor:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 7200
      visible_workbench: true
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
    formalizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
      visible_workbench: true
    faithfulness_reviewer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 1800
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
      visible_workbench: true
    post_freeze_interpreter:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 1800
    external_science_reviewer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 1800
---

# Binary linear `[50,20,14]`: context-carried structured-family successor

Preserve the reviewed `binary_linear_code.v1` adapter and the exact frozen
evidence context named above. The adapter identity is inherited; it is not a
new scientific choice. Begin with navigation over that context.

The navigator must choose one finite, nontrivial structured construction
family before any member is tested. The witness constructor must author the
family identity, rationale, canonical parameter domain, deterministic lowering
to binary generator matrices, and any symmetry quotient. The host may validate
and execute a reviewed data-only family, but may not choose its rows,
polynomials, parameters, or construction composition.

If `binary_linear_code.v1` lacks the executable vocabulary for the chosen
family, emit one typed capability request against that adapter. AdapterForge
may return a reviewed, campaign-local, data-only capability. Rejection or
runtime unavailability must return to navigation as typed evidence. Do not
invent a replacement adapter identity and do not mutate a global registry.

For every lowered matrix \(G\), exact success requires

\[
\operatorname{rank}_{\mathbf F_2}(G)=20,
\qquad
\min_{0\ne u\in\mathbf F_2^{20}}\operatorname{wt}(uG)\ge14.
\]

Every rejection needs a replayable dependent-row witness or nonzero message
with a low-weight codeword. Exhausting the frozen family supports only that
family's statement. A positive matrix is a candidate until separately bound
kernel governance accepts its construction certificate. Keep discovery,
ratification, and novelty as distinct statuses.
