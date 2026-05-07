# org/tasks/ — Task layer (GP-168 addendum, bottom tier; renamed from goals/ 2026-04-27)

Markdown-first task artifacts. The principal (or an agent) writes a
task file; any agent session picks it up on next wake. No Python
invocation required.

This directory was `org/goals/` until 2026-04-27. Renamed per Panel B
synthesis to make room for the Objective + Key Result layers above
it (`org/objectives/`, `org/key_results/`). The bottom-tier
work-item primitive is conceptually a *task*, not an *objective* —
the prior naming was task-shaped despite the label.

## Lifecycle

```
pending/<task_id>.md    ← principal or agent writes here
   │
   │  agent picks up at next wake; claims via sessions.claim_task()
   ▼
active/<task_id>.md     ← agent working on it
   │
   │  on completion, agent appends ## Result section
   │  daemon polls closure_deadline + budget_cap_usd; auto_resolution on expiry
   ▼
done/<task_id>.md       ← archived; audit trail in transitions.jsonl
```

## Schema

Frontmatter (canonical):

```yaml
---
task_id: <snake_case>                # stable id, never reused
objective_id: <parent_objective_id> | null   # foreign key into org/objectives/
kr_id: <kr_id> | null                # tighter link to a specific KR
title: "<short title>"
priority: low | medium | high | urgent
assigned_to: role.<role_id>          # role.manager | role.engineer | role.reviewer | role.principal
autonomous_scope_ok: true | false    # in-mandate without escalation?
status: pending | active | done | abandoned
closure_deadline: <iso> | null       # GP-168 time-pressure
warn_at_pct: 0.7                     # daemon warns at this fraction of deadline
escalate_at_pct: 0.9                 # daemon escalates at this fraction
auto_resolution: deny | approve | escalate | archive | defer
budget_cap_usd: <float> | null       # GP-168 budget-pressure
budget_spent_usd: 0.0                # mutated by agents on cost incurrence
budget_exhaust_action: close_partial | escalate | kill
execution_route: route_only | direct_work | expert_review | scripted_run | artifact_build | experiment_loop | docs_records
experiment_loop_allowed: true | false # product-generic loop; ZTARE is this repo's backend
ztare_allowed: true | false           # local backend compatibility flag
artifact_build_allowed: true | false
substrate_build_allowed: true | false
live_api_allowed: true | false
gpu_allowed: true | false
required_first_artifact: <path> | null
created_by: <member_id>
created_utc: <iso>
---

# <human title>

## Intent
<what the principal actually wants, in plain English>

## Context
<links to seams, specs, prior runs, related artifacts>

## Result
<appended by agent on completion: artifacts produced, costs incurred,
damage signals emitted, links to follow-up work>
```

## Closure pressure (GP-168 time + budget pressure)

The daemon polls each task on each cycle. Two pressures evaluated:

**Time pressure.**
- `pct = (now - created_utc) / (closure_deadline - created_utc)`
- At `warn_at_pct`, surfaces in Telegram digest as "imminent."
- At `escalate_at_pct`, opens an entry in `ztare_workspace/gates/pending/`.
- At `pct >= 1.0` (deadline passed), daemon submits state-transition
  request to GP-070 orchestrator: `auto_resolution` is the action.

**Budget pressure.**
- `pct = budget_spent_usd / budget_cap_usd`
- At `warn_at_pct: 0.8` (default), surfaces in Telegram digest.
- At `pct >= 1.0`, daemon submits `budget_exhaust_action` request.

Both pressures are independent. Either firing triggers resolution.

## Linking up the OKR tree

A task SHOULD have an `objective_id`. Orphan tasks (no parent
Objective) are allowed but surface in Orbit as "unattached" — the
principal should periodically attach or archive them.

A task MAY have a `kr_id` for tighter linkage. When set, completing
the task can trigger a measurement update on the linked KR (if the
KR's `measurement` is e.g. "count of done tasks under this KR").

## Agent contract

When an agent session starts:

1. List `org/tasks/pending/*.md`, sorted by:
   - priority (urgent > high > medium > low)
   - then by `closure_deadline` ascending (earliest first)
   - then by `created_utc` ascending (FIFO within tier)
2. For each task in order:
   - If `autonomous_scope_ok: true` AND the task references files
     within the agent's mandate scope → claim (move to `active/`,
     `sessions.claim_task(task_id=task_id)`) and execute.
   - If `autonomous_scope_ok: false` OR out-of-scope paths named →
     leave in pending, write an inbox escalation asking the principal
     to widen scope or reassign.
   - Before executing, classify or obey `execution_route`. The route is
     a work-mode contract, not a suggestion:
     - `route_only`: decide the correct route and create the next task.
     - `direct_work`: use direct operator-agent work; no paid run.
     - `expert_review`: prepare a bounded adversarial/expert review packet.
     - `scripted_run`: prepare a run packet with telemetry, gates, and
       notification before launch.
     - `artifact_build`: write/build a reusable implementation artifact or
       contract; if the current role is only a director/reviewer, create a
       handoff task for an authorized builder instead of editing artifacts.
     - `experiment_loop`: run the generic candidate-search loop only
       after preflight proves a stable substrate, gates, and closure plan.
       In this repo, the experiment-loop backend is ZTARE.
     - `docs_records`: update prose/records and MIRROR/public-private
       derivatives as required.
3. On completion, append a `## Result` section with artifacts
   produced, costs incurred (also update `budget_spent_usd`), any
   damage signals emitted, then move the file to `done/`.
4. On blocking, append `## Blocked` section with the blocker and an
   escalation reference, leave file in `active/` (claimed), fire
   inbox escalation to `ztare_workspace/gates/pending/`.

## Why markdown + filesystem, not a service?

- **No Python start required from the principal.** Write a file;
  agent finds it. Same as the GP-132 design.
- **Durable.** Files persist across sessions, crashes, daemon restarts.
- **Inspectable.** `ls org/tasks/pending/` shows state in one line.
- **Composable with mandate.** Agent's decision to execute vs
  escalate reads the mandate's Scope of Autonomous Action; no new
  authorization surface.
- **Body-first; agent-friendly.** Body is canonical natural language;
  frontmatter is machine-maintainable. An agent can author tasks for
  the principal to review (with `created_by: <agent_id>`) using the
  same schema the principal uses.

## Relationship to other layers

- **`org/objectives/`** — Objectives this task advances (parent of `kr_id`'s parent).
- **`org/key_results/`** — KRs this task directly advances (`kr_id` field).
- **GP-070** — formal goal orchestrator state machine; tasks
  represent ACTIVE-stage work for `target_type: science_sandbox` and
  similar. Not all tasks belong to a GP-070 lifecycle; one-offs are
  fine.
- **GP-128** — persistent manager-agent reads tasks at session wake.
- **`ztare_workspace/gates/pending/`** — escalation channel when
  task hits `escalate_at_pct` or `auto_resolution: escalate`.

## See also

- `org/objectives/README.md` — parent layer
- `org/key_results/README.md` — measurable outcomes
- `research_areas/private/seams/mission/GP-168_org_design_unfalsifiability_seam.md`
  — Addendum 2026-04-27 has the full schema + panel synthesis
