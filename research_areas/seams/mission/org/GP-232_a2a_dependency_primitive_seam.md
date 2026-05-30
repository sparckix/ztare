# GP-232 — A2A obligation lifecycle + artifact-dependency primitive

> **Seam metadata** · `seam_id:` GP-232 · `track:` mission · `status:` open - three-panel verdict shipped 2026-05-07; implementatio · `last_updated:` 2026-05-08


**Status:** open — three-panel verdict shipped 2026-05-07; implementation queued.
**Created:** 2026-05-07
**Owner:** principal + research_director
**Related:** GP-167 (multi-agent interface form factor), GP-129 (biological-org-design panel), GP-231 (MCP outbox + capability tokens)

## Eigenquestion

cognitive-firm shipped local typed agent channels (`agent_channels.py`) and an A2A/ACP-compatible agent-card projection (`a2a_projection.py`). Per GP-167 the design choice was "ship local primitive now; A2A/ACP remote adapters later." But two structural gaps remain unfilled:

1. There is no first-class **agent-task obligation lifecycle** distinct from the message lifecycle (currently messages have `open|acknowledged|closed`, but obligations have no separate state).
2. There is no first-class **dependency primitive** for "task B waits on task A's artifact X with property Y."

What is the right shape for both, and can they share substrate?

## Three-panel verdict (2026-05-07)

Three adversarial panels reviewed the gap independently:

- **A2A best-in-class auditor** — verdict: cognitive-firm's local-first A2A is structurally sound (separation of authority/routing is more correct than Google A2A's task-state-machine, which conflates them). Top gap that matters at T1+T2 is **obligation lifecycle distinct from message lifecycle**. Streaming + push-notification + cross-org identity federation are A2A features for use cases cognitive-firm does not have; skip.
- **Distributed-systems dependency panel** — verdict: add **content-addressed artifact promises on the transition log**. Reuse `transitions.jsonl` (the GP-231 outbox) as the substrate. Schema: `task.artifact.fulfilled(task_id, artifact_key, sha256, predicate_hash, predicate_eval)`. Downstream tasks declare `awaits: [{artifact_key, predicate_hash}]` in role yaml; work-discovery filters non-ready tasks. Static cycle / predicate-drift checker at task admission.
- **Biological-systems comparative panel** — verdict: same primitive arrived at via marker-deposit reasoning. Honest admission per GP-129 rule: framing decorative, mechanism is **content-addressed typed pub-sub with TTL**. Adds one calibration nudge on top: **gradient lock-in monitor on the `ready/` filename distribution**, since marker-deposit systems suffer trail reinforcement.

The three panels converged on the same architectural answer from independent threat models. The convergence is the substrate's main signal that this is the right primitive.

## The shipped primitive (combined verdict)

### Layer 1: obligation lifecycle on AgentMessage

Extend `AgentMessage` with:

```python
obligation_state: Optional[Literal[
    "pending", "accepted", "in_progress",
    "blocked_input", "fulfilled", "refused", "expired"
]] = None
parent_obligation_id: Optional[str] = None  # saga chain
```

Distinct from `status` (which is the message lifecycle). The obligation lifecycle is what the manager-role daemon and Orbit render to the principal: "B is blocked-input waiting on A" becomes structurally visible instead of inferred from open messages.

### Layer 2: artifact-promise events on transitions.jsonl

Two new event names on the existing transition log (GP-231 outbox substrate):

```jsonc
// Producer side
{
  "event": "task.artifact.promised",
  "ts_utc": "...",
  "actor": "research_director",
  "role_id": "research_director",
  "task_id": "task_validate_X_018",
  "causality_id": "obj_GP-240",
  "payload": {
    "artifact_key": "validator_results.X",
    "predicate": "schema_version >= 2 AND score >= 0.7",
    "predicate_hash": "p_h7c2",
    "expires_at_utc": "2026-05-14T..."
  }
}

// Producer side (after producing)
{
  "event": "task.artifact.fulfilled",
  "ts_utc": "...",
  "task_id": "task_validate_X_018",
  "payload": {
    "artifact_key": "validator_results.X",
    "artifact_path": "ztare_workspace/validator/X.json",
    "sha256": "9af3...",
    "predicate_hash": "p_h7c2",
    "predicate_eval": {"schema_version_ge_2": true, "score_ge_0.7": true}
  }
}
```

### Layer 3: consumer declaration in task / role yaml

```yaml
awaits:
  - artifact_key: validator_results.X
    predicate_hash: p_h7c2
```

`work_discovery.discover_open_todos` (and siblings) filters task candidates whose `awaits` array does not have a matching `task.artifact.fulfilled` row in transitions.jsonl. Tasks with unsatisfied awaits are non-candidates.

### Layer 4: secondary index + cycle checker

- Secondary index keyed `artifact_key → [fulfillment offsets]`, rebuildable from the log on startup (GP-231 outbox-relay pattern).
- Static cycle detection over `awaits` + `promises` graph at task admission. Predicate-drift detector: if a mandate revision changes a `predicate_hash` but downstream consumers reference the old hash, flag a `predicate_hash_drift` damage signal.
- Optional: gradient lock-in monitor (per biological panel calibration) on the distribution of `artifact_key` reuse — flag if one key dominates >70% of fulfillments.

### Layer 5: saga compensation

`parent_obligation_id` chains let "agent A handed off to B, B failed, undo A's writes" become a typed compensation flow. Phase 2 of this seam, after Layers 1-4 ship.

## Why this is best-in-class for the threat model

- **At T1 (single principal):** obligation lifecycle gives the principal structural visibility into agent-blocking-on-agent without inference. Artifact-promise events make "stale upstream output silently consumed" impossible — the predicate hash changes when the producer's contract changes, blocking downstream consumers until they update their `awaits`.
- **At T2 (regulated enterprise):** saga compensation closes the rollback gap that GP-167 already flagged. Obligation lifecycle is the prerequisite primitive for saga (you cannot compensate what you cannot lifecycle).
- **Substrate reuse:** uses `transitions.jsonl` (already the GP-231 outbox), `org/roles/*.yaml` for the awaits declaration, no new file types. The biological panel's `org/signals/ready/*.ready` proposal was downgraded by the panel itself in favor of transition-log events to avoid split-brain with GP-231.

## What this primitive REJECTS

- **Airflow-style separate DAG.** Distributed-systems panel: cognitive-firm inverts Airflow's "scheduler owns task state" — filesystem-as-truth + transitions.jsonl + git-history are the truth, in-memory DAG is a projection. Separate DAG drifts the moment a human edits a task yaml or a daemon crashes mid-execution.
- **Streaming + push-notification + cross-org identity federation** (Google A2A features). Solves use cases cognitive-firm does not have at T1 or T2.
- **Per-action capability grants for the obligation primitive.** Per C4 verdict (GP-230 absorption): directory-scoped capability lifetimes, not per-action. The same discipline applies here.

## Implementation phasing

- **Phase A (decisive, agent-day or two):** AgentMessage.obligation_state + parent_obligation_id + tests; obligation rendering in Orbit.
- **Phase B (decisive, similar scope):** transition-log artifact-promise/fulfilled events; awaits filter in work_discovery; secondary index; cycle checker.
- **Phase C (queued, T2 prereq):** saga compensation primitive + tests.
- **Phase D (queued, decoration):** gradient-lock-in monitor on artifact_key distribution.

Phase A + B together close cognitive-firm's two structural gaps and bring the kernel close to publishable-reference-implementation parity for the single-principal threat model. Phase C closes the regulated-enterprise gap. Phase D is the biological-panel calibration nudge.

## Distance to publishable A2A parity (per audit panel)

If we wanted to ship cognitive-firm A2A as a 2026 published reference implementation (NOT currently a goal): ~80-120 agent-hours, broken down per the audit panel's estimate. Phases A + B above account for ~32 of those hours. The remaining ~50-90 are remote A2A adapter, FIPA-ACL performative expansion, idempotency-keys-on-inbox, conformance test suite, spec document. Hold all of that until a concrete adopter signals interest.

## Closure criteria

- Phase A: obligation_state field + state-machine validator + 5+ tests pass.
- Phase B: transition-log events shipped + awaits filter in work_discovery + secondary index rebuildable + cycle checker rejects malformed graphs at admission + 5+ tests pass.
- Phase C: saga compensation flow demonstrated end-to-end with an intentional failure that triggers compensation.
- Phase D: gradient-lock-in monitor surfaces a real concentration on artifact_key reuse from existing transitions.

When Phases A+B close, GP-167 v3 is updated to mark the local A2A primitive as best-in-class for single-principal governance, with the explicit honest scope ("not yet a published-protocol-ready open-source artifact").
