---
schema: leanmill.campaign.v1
lane: axiompack
profile: standard
source_mode: structure_first
requested_mode: anonymous_signature_census
evidence_refs:
  - smoke:axiompack-compositional-stdin-transport
deanchoring_intent: cold_after_signature_compilation
forbidden_shortcuts:
  - literature lookup or named-class recovery before finalist freeze
  - treating one finite profile as a mathematical result
  - treating a transport or budget failure as a scientific rejection
typed_blueprint: typed_blueprint_compositional.json
budget:
  wall_clock: 10m
  provider_calls: 18
  agent_turns: 18
  input_tokens: 180000
  output_tokens: 60000
  metered_api_usd: "0"
  workbench_actions: 48
  adapter_forge_attempts: 0
runtime:
  transport: subscription_agent_runtime
  profile: frontier
  role_overrides:
    navigator:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: low
      timeout_seconds: 600
      visible_workbench: false
    lineage_synthesizer:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: low
      timeout_seconds: 600
      visible_workbench: false
    lean_solver:
      runtime: codex
      model: gpt-5.5
      reasoning_effort: low
      timeout_seconds: 300
      governed_pool: false
      allow_subscription_failover: false
---

Transport and host-recovery smoke for the compositional frontier inlet.
Use the same anonymous typed context as the frontier campaign, but keep the
cheap Codex leaf and tight envelope until the shared prompt boundary has
survived a complete multi-lineage navigation slice. A result here is a
harness receipt only; it does not support a mathematical or novelty claim.
