---
task_id: research_director_candidate_review
objective_id: null
kr_id: null
title: "Research Director candidate review"
priority: high
assigned_to: role.research_director
autonomous_scope_ok: true
status: pending
closure_deadline: null
warn_at_pct: 0.7
escalate_at_pct: 0.9
auto_resolution: defer
budget_cap_usd: 5.0
budget_spent_usd: 0.0
budget_exhaust_action: escalate
created_by: principal
created_utc: "2026-04-30T00:00:00Z"
---

# Research Director candidate review

## Intent

Rank the next research moves against the principal's preference profile and
identify the cheapest discriminator that would change what should be built or
believed next.

## Context

- Preference profile: `org/preferences/principal.yaml`
- Research Director role: `org/roles/research_director.yaml`
- Research Director mandate: `org/mandates/research_director_mandate.md`
- Source queue: `projects/<project>/workspace/next_discriminator_queue.jsonl`

## Required Output

Produce one of:

- a ranked next-move report under the relevant project workspace
- a directive under `org/directives/` if principal approval is needed
- a damage signal if the current artifacts make the ranking uninterpretable

Do not promote a scientific claim from taste score alone. Taste routes
attention; discriminator closure licenses promotion.

## Result
