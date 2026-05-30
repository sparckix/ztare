---
id: PATTERN-017
name: frontier_state_ledger
version: 1
status: active
discovered: 2026-05-09
discovered_reason: |
  META-DARWIN audit on pattern architecture (2026-05-09 evening) flagged
  src/ztare/role_extensions/frontier_state.py + iter_action_policy.yaml
  as a missing pattern. This is the daemon-safe per-project state
  abstraction that PATTERN-016 (frontier_co_drive_protocol) writes to,
  paired with a hot-reloadable YAML policy mapping iter-loop events to
  RD actions.
triggers:
  lexical: [frontier_state, iter_action, daemon, hot-reload, atomic write]
  structural:
    - daemonized RD operating across multiple projects
    - need to persist route_ranking + active_escapes + obstruction_counters
    - policy mapping iter-loop event -> RD action evolves at runtime
  problem_classes: [orchestration_meta_architecture, state_persistence]
spawn:
  mode: kernel_state
  module: src.ztare.role_extensions.frontier_state
  policy_file: src/ztare/role_extensions/iter_action_policy.yaml
  storage_path: ztare_workspace/frontier_state/<project>.json
  storage_discipline: atomic_write
  schema_fields:
    - route_ranking
    - active_escapes
    - obstruction_counters
    - pending_actions
    - history
  policy_event_actions:
    - obstruction_repeated_fork: fork_substrate
    - verified_axiom_to_lean_cage: create_lean_cage
    - champion_shift_update_meaning: mutate_evidence
    - ambient_gate_repeated_cold_shot: queue_cold_shot
related_patterns:
  - id: PATTERN-016
    relation: paired_with  # frontier_co_drive_protocol writes to this state ledger
  - id: PATTERN-013
    relation: complementary  # pattern_deployment_ledger is the per-dispatch ledger; this is the per-project state
  - id: PATTERN-014
    relation: triggers  # ambient_gate_repeated_cold_shot policy event dispatches PATTERN-014
references:
  - existing kernel: src/ztare/role_extensions/frontier_state.py
  - existing policy: src/ztare/role_extensions/iter_action_policy.yaml
  - storage spec: ztare_workspace/frontier_state/*.json
falsifiable_test: |
  Once wired, over N>=20 simulated or real daemon restarts across >=3 projects,
  replaying frontier_state history must reproduce the exact next RD action the
  daemon would have produced without restart in >=95% of cases, AND state reads
  must return decision-relevant fields (route_ranking, obstruction_counters) in
  O(1) without a full project re-mine in >=95% of reads. If post-restart action
  agreement falls below 95%, or >5% of reads force a re-mine (stale-state
  laundering), the state contract is not central and demotes.
  metric_source: ztare_workspace/frontier_state/<project>.json history field
  replayed under simulated restart; action-agreement and re-mine events counted
  against the daemon action log.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-017 — Frontier State Ledger

## What this pattern is

A **daemon-safe per-project state abstraction** that tracks the RD's
view of each project's research-loop state, paired with a hot-
reloadable YAML policy that maps iter-loop events to RD actions.

State schema:
* `route_ranking`: ordered list of candidate routes with scores.
* `active_escapes`: routes the RD is currently exploring as escapes
  from the champion route.
* `obstruction_counters`: per-route counters of how many iters have
  failed to advance the route's score.
* `pending_actions`: queued RD actions awaiting execution.
* `history`: append-only audit trail of state transitions.

Storage: `ztare_workspace/frontier_state/<project>.json` via atomic
write (write-to-tmpfile + rename), so daemon restarts and concurrent
reads do not see partial state.

Policy: `src/ztare/role_extensions/iter_action_policy.yaml` — hot-
reloadable mapping from iter-loop events (`obstruction_repeated`,
`verified_axiom`, `champion_shift`, `ambient_gate_repeated`) to RD
actions (`fork_substrate`, `create_lean_cage`, `mutate_evidence`,
`queue_cold_shot`).

## Why this pattern is central

PATTERN-016 (frontier_co_drive_protocol) is the AUTHORIZATION layer;
PATTERN-017 is the STATE layer. Without state persistence, the RD
cannot reason about "have I tried this route 3 times already" without
re-mining the whole project history. With state persistence, decision-
relevant information lives in O(1) per-project state, and policy
decisions become deterministic.

This is the SECOND-ORDER daemon contract that makes PATTERN-001
(friction_debate) and PATTERN-011 (swarm_dispatch) orchestratable
across multi-day, multi-project research loops without operator
re-context.

## Falsifiable-asymmetry test (per PATTERN-005)

The pattern is "working" iff: when the daemon restarts, the RD
resumes from the prior state without operator re-context AND the
resumption produces the same actions the daemon would have produced
without restart. Empirically testable by replay of frontier_state
history under simulated daemon restarts.

## Anti-laundering catches

* **Atomic-write violation**: a non-atomic state write produces
  partial-state files that downstream readers misinterpret. Mitigation:
  always write-to-tmp + rename; never write in place.
* **Policy drift laundering**: hot-reloadable policy means a malicious
  edit can authorize unauthorized actions. Mitigation: policy file is
  in-repo; every edit is reviewable; runtime hot-reload logs the
  reload event with policy-file SHA to history.
* **Stale-state laundering**: daemon reads state file but doesn't check
  freshness against project's actual iter-history. Mitigation: each
  state-read validates that route_ranking corresponds to the project's
  most recent iter; mismatches force a re-mine.
