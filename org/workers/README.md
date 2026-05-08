# org/workers/ — Ephemeral Tool-Invocation Membranes

Workers are **ephemeral, per-call actors** that a role invokes as a tool. They have no persistent identity, no session, no inbox, no mandate of their own. They execute a bounded task, deposit a trace, and die.

The purpose of this folder is **not** to give workers org-chart positions — they have none. The purpose is to document each worker as a **membrane**: what it reads (input contract) and what it writes (output contract). This is the GP-129 Margulis pull-forward. When a new agent substrate is added, integration cost concentrates at the membrane; treating workers as membrane specs (not subordinates) keeps that attention focused.

## Schema

```yaml
schema_version: 1
worker_id: <snake_case>
description: >
  One-to-three-sentence summary of what this worker does and when to invoke it.

invocation:
  substrate: <e.g. claude_code_sub_agent | api_direct>
  tool_name: <the tool the invoking role calls>
  fan_out_ok: true | false         # can be invoked N times in parallel

input_contract:
  accepts:
    - <named input class, e.g. "task_prompt: string">
  reads_from:
    - <filesystem path prefix, or "none">
  must_receive:
    - <required fields the caller must set, e.g. "description", "prompt">

output_contract:
  produces:
    - <named output class, e.g. "summary: markdown">
  deposits_to:
    - <filesystem path prefix, or "return value only">
  contract_guarantees:
    - <invariants the worker upholds, e.g. "does not edit files">

permissions:
  read: [...]                      # path prefixes, or ["*"]
  write: []                        # typically empty for read-only workers
  forbidden: [...]

limits:
  single_action_cost_cap_usd: <float or null>
  wall_clock_cap_seconds: <int or null>

opened_date: "YYYY-MM-DD"
opened_by: <member_id>
```

## Relationship to roles

- Roles are **persistent positions** with mandates, SLAs, session logs, and gate-signing authority.
- Workers are **tool calls** with an input/output contract and a kill-after-return lifecycle.

The manager role's `delegates_to` list names workers (e.g. `worker.explore_agent`); the `org/workers/<id>.yaml` file is the membrane spec for that worker.
