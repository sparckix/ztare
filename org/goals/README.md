# org/goals/ — Principal → Agent Goal Inbox (GP-132)

Markdown-first goal artifacts. The principal writes a goal file; any agent session picks it up on next wake. No Python invocation required.

## Lifecycle

```
pending/<goal_id>.md    ← principal writes here
   │
   │  agent picks up at next wake; claims via sessions.claim_task()
   ▼
active/<goal_id>.md     ← agent working on it
   │
   │  on completion, agent appends ## Result section
   ▼
done/<goal_id>.md       ← archived; audit trail preserved
```

## Creating a goal

Write `org/goals/pending/<goal_id>.md` with YAML frontmatter:

```markdown
---
goal_id: <snake_case_id>
priority: low | medium | high | urgent
deadline: YYYY-MM-DD         # or null for no hard deadline
estimated_cost_usd: <float>  # 0.0 if no spend expected
assigned_to: role.manager    # or role.engineer | role.reviewer | role.principal
autonomous_scope_ok: true | false   # principal's read on whether this is in-mandate
created_by: daniel_alami
created_utc: 2026-04-23T14:00:00Z
---

# <human-readable title>

<intent — what for, not how>

<context — files, seams, prior work the agent needs>

<success criteria — how will we know it's done>

<escalation triggers — when should the agent stop and ask>
```

## Agent contract

When an agent session starts, it:

1. Lists `org/goals/pending/*.md`, sorted by priority + deadline.
2. For each goal:
   - If `autonomous_scope_ok: true` AND the goal path is within the agent's mandate scope → claim (move to `active/`, `sessions.claim_task(task_id=goal_id)`) and execute.
   - If `autonomous_scope_ok: false` OR the goal names out-of-scope actions → leave in pending, write an inbox escalation asking the principal to widen scope or reassign.
3. On completion, append a `## Result` section with artifacts produced, costs incurred, any damage signals emitted, then move the file to `done/`.
4. On blocking: append `## Blocked` section with the blocker and an escalation reference, move to `active/` (leave claimed), fire inbox escalation.

## Agent's first line of code on wake

```python
from src.ztare.orchestration.goals_inbox import list_pending_goals, claim_goal, mark_goal_done
for goal in list_pending_goals():
    if goal.autonomous_scope_ok and goal.assigned_to == "role.manager":
        claimed = claim_goal(goal_id=goal.goal_id, session_id=my_session.session_id, ...)
        if claimed:
            # execute — the file is now in active/
            ...
```

## Why markdown + filesystem, not a service?

- **No Python start required from the principal.** Write a file; agent finds it. This is the chasm GP-128 left open.
- **Durable.** Files persist across sessions, crashes, and daemon restarts.
- **Inspectable.** `ls org/goals/pending/` shows state in one line.
- **Composable with mandate.** The agent's decision to execute vs escalate reads the mandate's Scope of Autonomous Action; no new authorization surface.
- **Version-controllable (if desired).** `org/goals/` could be tracked in git for provenance; currently gitignored since most goals will reference personal context. Principal decides per-goal.

## Relationship to other work

- **Inverse of GP-131.** GP-131 is agent → principal (daemon discovers work, writes proposal). GP-132 is principal → agent (principal writes goal, agent picks up). Same underlying filesystem-as-message-queue pattern.
- **Complements GP-070.** GP-070 is the formal state-machine goal system with SCOPING/ACTIVE/REVIEW stages, invoked via Python CLI. GP-132 is the lightweight alternative for goals that don't need the full state machine. Use GP-070 for multi-agent coordinated research programs; use GP-132 for "please do X this week."
