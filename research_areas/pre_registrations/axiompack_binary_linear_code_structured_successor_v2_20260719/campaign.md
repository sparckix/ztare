---
schema: leanmill.campaign.v1
lane: axiompack
profile: overnight
source_mode: residual_directed
requested_mode: evidence_induced
evidence_refs:
- research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/experiment_contract.md
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/external_target_snapshot.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/fresh_source_replay.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/binary_code_control_replay.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/campaign_adapter_config.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/campaign_scientific_disposition.md
deanchoring_intent: family_authored_before_target_enumeration
forbidden_shortcuts:
- resuming unconstrained raw generator-matrix proposals
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
  wall_clock: 8h
  provider_calls: 60
  agent_turns: 96
  input_tokens: 2600000
  output_tokens: 900000
  metered_api_usd: '0'
  workbench_actions: 480
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
  when: Stop after an exact rank-20 length-50 generator reaches minimum distance at least 14 and enters current-policy construction-artifact ratification; one campaign-authored finite construction family is completely enumerated with replayable member-level rejection receipts and a typed next representation; the 480-minute split expires; or a typed runtime failure prevents the family from becoming executable. Never infer global code nonexistence from a family result.
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    blueprint_compiler:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: ultra
      timeout_seconds: 3600
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

# Binary linear `[50,20,14]`: structured-family successor

**Status:** pre-registered; not yet executed.

The current source replay records

\[
13\le d_2(50,20)\le14.
\]

The predecessor campaign produced six exact rank-20 rejections with distances
`12,12,12,10,11,12` and then stopped on budget. Do not propose another
unconstrained matrix. The first scientific action is to author one finite,
nontrivial structured construction family and freeze its complete parameter
domain before any member is tested against the target.

The family specification must be data-only and must state:

1. its construction identity and mathematical rationale;
2. a finite canonical parameter domain and exact cardinality;
3. a deterministic lowering from every parameter tuple to a binary generator
   matrix;
4. any symmetry quotient and a check that it does not omit inequivalent
   parameters relevant to the family claim;
5. immutable provenance tying the family to the organ that authored it.

The navigator chooses the construction category. The witness constructor
authors the family parameters or grammar. The host may validate the schema,
enumerate the frozen domain, lower it deterministically, canonicalize row
operations, and run the exact verifier. The host may not select the family,
polynomials, rows, or composition. An independent reviewer must accept the
family identity and finite extent before enumeration.

If the registered adapter cannot consume the chosen family, emit a typed
language-capability request through the normal successor route. AdapterForge
may return a reviewed data-only family materialization or a general finite-
family lowering capability; generated Python is quarantined and no global
registry mutation is permitted. Rejection or unavailable execution returns a
typed input to navigation.

For every lowered matrix \(G\), exact success requires

\[
\operatorname{rank}_{\mathbf F_2}(G)=20,
\qquad
\min_{0\ne u\in\mathbf F_2^{20}}\operatorname{wt}(uG)\ge14.
\]

Store a dependent-row witness for rank failure or a nonzero message and its
low-weight codeword for distance failure. A positive candidate remains
pending until a separately bound, kernel-pure construction certificate passes
LeanMill governance. If the family is exhausted, issue only the finite-family
statement and bind a typed next representation chosen from the observed
rejection geometry. Keep discovery, ratification, and novelty as separate
statuses.
