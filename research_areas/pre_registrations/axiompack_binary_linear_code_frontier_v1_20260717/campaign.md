---
schema: leanmill.campaign.v1
lane: axiompack
profile: overnight
source_mode: residual_directed
requested_mode: evidence_induced
evidence_refs:
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/external_target_snapshot.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/fresh_source_replay.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/binary_code_control_replay.json
- research_areas/pre_registrations/axiompack_binary_linear_code_frontier_v1_20260717/campaign_adapter_config.json
deanchoring_intent: target_visible_construction_family_deanchored
forbidden_shortcuts:
- treating a bounded family failure as nonexistence of a binary linear code
- crediting a matrix before exact rank and all-nonzero-message distance replay
- crediting deterministic host verification as kernel ratification
- allowing the host to select generator rows, polynomials, or a construction composition
- mutating the global adapter registry from a campaign leaf
- claiming priority without a fresh table, derived-code, and primary-source replay
created_by: user
budget:
  wall_clock: 12h
  provider_calls: 120
  agent_turns: 180
  input_tokens: 5000000
  output_tokens: 1800000
  metered_api_usd: '0'
  workbench_actions: 720
  adapter_forge_attempts: 8
  context:
    models: 100000
    truth_cells: 10000000
  boundary:
    queries: 120
    smt_calls: 0
    smt_time: 0ms
    formal_peer_attempts: 24
    formal_peer_time: 21600000ms
    lean_attempts: 24
    lean_time: 21600000ms
stop:
  max_finalists: 12
  low_yield_patience: 4
  min_marginal_information_per_cost: '0.02'
  coverage_target: '0.9'
  when: Stop only after an explicit rank-20 length-50 generator reaches exact minimum distance at least 14 and enters construction-artifact ratification; a typed representation gap produces an executable successor-language request; or budget exhaustion leaves family-scoped reject receipts and a resumable frontier. Never infer code nonexistence from search exhaustion.
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

# Binary linear `[50,20,14]` construction campaign

**Status:** budget-stopped with the target unmet. The frozen run is replayable,
its six candidate rejections are exact, and the remaining construction and
certificate frontier is recorded in `campaign_scientific_disposition.md`.

Construct a binary linear code with parameters

\[
[n,k,d]=[50,20,14].
\]

The current source snapshot records

\[
13\le d_2(50,20)\le14.
\]

One explicit generator matrix \(G\in\mathbf F_2^{20\times50}\) succeeds exactly
when

\[
\operatorname{rank}_{\mathbf F_2}(G)=20,
\qquad
\min_{0\ne u\in\mathbf F_2^{20}}\operatorname{wt}(uG)\ge14.
\]

Compile this as an evidence-induced theory program with the registered
`binary_linear_code.v1` adapter and the byte-identical configuration in
`campaign_adapter_config.json`. The declared panel contains three matched
controls: the published `[50,20,13]` quasicyclic code, its `[51,20,14]` parity
extension, and a rank-preserving distance-12 perturbation. Exactness covers
only those three objects and their six declared coordinates; it is not a
census of codes or construction families.

The campaign sees the target, reviewed construction interface, control
receipts, and public source artifacts. It may choose any representation or
composition and may request a reviewed successor capability. The navigator
authors the theory program and construction request. A distinct visible-
workbench witness constructor authors the generator matrix and a structured
orientation record. The host may canonicalize row operations, enumerate all
`2^20-1` nonzero messages, and return a low-weight codeword when the target
fails; it may not invent or repair generator rows.

A matrix accepted by the exact verifier remains pending until a separately
bound, kernel-pure construction certificate passes LeanMill governance. A
successful certificate triggers a fresh replay of the code table, derived-code
relations, and primary literature before any priority statement. If search
stagnates, preserve family-scoped failures and move through a typed language
successor; do not convert them into a global negative result.
