---
id: PATTERN-016
name: frontier_co_drive_protocol
version: 1
status: active
discovered: 2026-05-09
discovered_reason: |
  META-DARWIN audit on pattern architecture (2026-05-09 evening) flagged
  src/ztare/orchestration/execution_routing.py + the RD-1.12 mandate as
  a missing pattern. This is a role-level execution protocol that
  authorizes the Research Director to live co-drive a research loop —
  reading iter outputs, mutating substrate (evidence/charter/rubric),
  forking successor projects, queuing cold-shots, writing Lean cages
  from verified axioms — subject to per-action budget gates and damage-
  signal audit.
triggers:
  lexical: [co-drive, frontier, RD direct, route_rd_active]
  structural:
    - RD action requires direct substrate mutation (not just dispatch)
    - per-action budget gate exists and is reachable
    - damage-signal audit is wired
  problem_classes: [orchestration_meta_architecture, execution_routing]
spawn:
  mode: kernel_route
  module: src.ztare.orchestration.execution_routing
  authorized_actions:
    - fork_substrate
    - create_lean_cage
    - demote_route
    - mutate_evidence
    - mutate_charter
    - queue_cold_shot
    - escalate_to_principal
  guards:
    - spend_tracker
    - agent_utilization_tracker
    - damage_signal_audit
related_patterns:
  - id: PATTERN-017
    relation: pairs_with  # frontier_state_ledger is the daemon-safe state contract this protocol writes to
  - id: PATTERN-014
    relation: dispatches  # one of the authorized actions is queue_cold_shot
  - id: PATTERN-019
    relation: dispatches  # eigenquestion regeneration is a queue_cold_shot variant
references:
  - existing kernel: src/ztare/orchestration/execution_routing.py
  - RD-1.12 mandate: org/directives/2026-04-30T155808Z_principal_research_director_mandate_v1_5_proposal.json
  - related route schema: org/directives/2026-05-03T125433Z_research_director_ztare_frontier_prior_update.json
falsifiable_test: |
  Once the protocol is the routed standard, over N>=25 authorized RD
  substrate-mutation actions, the rate of post-action catches (catches that flag a
  co-drive action as wrong after the fact) per authorized action must DECLINE
  across the deployment window — the last-15-action post-action catch rate must be
  <=0.5x the first-15-action rate — while the 8-action vocabulary is held constant.
  If the post-action catch rate does not at least halve (action quality not
  improving) or rises, the protocol's damage-signal audit earns nothing and
  demotes.
  metric_source: catch_ledger.jsonl entries joined to the action audit log
  (authorized-action records tagged PATTERN-016 in pattern_deployment_ledger.jsonl),
  post-action catch rate computed per rolling 15-action window.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-016 — Frontier Co-Drive Protocol

## What this pattern is

A **role-level execution protocol** (RD-1.12, established 2026-05-02)
authorizing the Research Director to live co-drive a research loop
without requiring per-action operator approval, subject to:

1. Bounded action vocabulary (8 authorized actions, listed above).
2. Per-action budget gates (spend_tracker + agent_utilization_tracker).
3. Damage-signal audit (any action that would meaningfully degrade an
   existing artifact requires explicit operator confirmation).

Distinct from:
* **route_only handoff**: pre-RD-1.12 protocol where the RD authored
  specs but a separate executor performed the substrate mutation.
* **agent-based dispatch**: Claude Code Agent tool spawning a subagent
  for a task; the agent does NOT have substrate-mutation authority by
  default.

## When to deploy

This is the **RD's authorized standard route** since 2026-05-02. It
fires whenever the RD is operating directly on the substrate (versus
authoring a spec for a downstream executor). Most current RD work is
under this protocol.

## Damage-signal audit

The discipline that keeps frontier_co_drive safe is the damage-signal
audit. Before any action with potentially-destructive scope (e.g.
`demote_route` on a central route, `mutate_charter` on a
shipped artifact), the RD checks the action against:

* Recent operator-stated guard rules.
* Existing artifact provenance and central status.
* The catch ledger for similar prior-action catches.

If any signal fires, the action upgrades from co-drive (autonomous) to
operator-gated.

## Falsifiable-asymmetry test (per PATTERN-005)

The protocol is "working" iff: catches that fired AFTER an RD action
(i.e. caught the action as wrong post-hoc) decrease in rate per
authorized action over time, while the action vocabulary is held
constant. Empirically testable from `analytics/public/ledgers/catch/catch_ledger.jsonl`
joined with action audit logs.

## Anti-laundering catches

* **Scope drift**: an action authorized as `mutate_evidence` that
  silently mutates the charter too (cross-action laundering). Mitigation:
  per-action input/output filepath whitelisting.
* **Damage-signal bypass**: skipping the damage-signal audit because
  "it's a small change" — exactly the conditions where the audit
  catches the most. Mitigation: damage-signal audit is REQUIRED for
  every authorized action, not optional.
