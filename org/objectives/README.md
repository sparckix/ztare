# org/objectives/ — Objective layer (GP-168 addendum, top tier)

Markdown-first Objective artifacts. The principal writes one file per
durable Objective; the body is canonical, the YAML frontmatter is a
small machine-maintainable projection used by the closure daemon and
Orbit dashboard.

## Why this layer exists

The pre-2026-04-27 `org/goals/` was task-shaped and ZTARE-flavored —
no Objective layer above it (the "why" was implicit) and no
measurable Key Results alongside it (success was undefined). This
directory adds the Objective layer per the Panel B synthesis recorded
in `GP-168 (internal seam)`
(Addendum 2026-04-27, §"Composed decision").

## Lifecycle

```
org/objectives/<obj_id>.md
   │
   │  status: active   ← principal authors here
   │
   │  daemon polls closure_deadline; on expiry posts notification closure prompt
   │  principal taps done | abandon | extend
   ▼
   status: done | abandoned   ← daemon writes archive_with_postmortem if no response
```

Objectives stay in the same file; status moves through frontmatter,
not through directory moves. Lifecycle is recorded in
`transitions.jsonl` (GP-070 write-ahead log).

## Schema

Frontmatter (canonical):

```yaml
---
objective_id: <snake_case>            # stable id, never reused
title: "<short title>"
horizon: target_date | open           # 'open' for durable rolling Objectives
target_date: 2026-06-30 | null        # required when horizon == target_date
status: active | done | abandoned
created_by: principal
created_utc: <iso>
closure_deadline: <iso> | null        # daemon-enforced; defaults to target_date
auto_resolution: archive_with_postmortem
authoring_mode: human | agent_proposed
---

# <human title>

<intent — what for, why this matters>

<context — links to seams, prior runs, related Objectives>

<success criteria — qualitative; measurable specifics live in linked KRs>

<connection to longer-term intent — how this serves the principal's
multi-year direction>
```

The body is what the principal writes; the frontmatter is what the
daemon reads. Keep frontmatter small.

## Required invariants

- **At least one Key Result with `measurement_locus: world`.** Enforced
  at Objective creation by daemon (`scripts/closure_daemon.py`).
  Objectives with only self-measured KRs drift into theatre.
- **`auto_resolution: archive_with_postmortem` is the only safe
  default.** Other resolutions (e.g., extend) require principal
  action — daemon never auto-extends an Objective.
- **Strip-test on title.** If the title only makes sense to ZTARE
  insiders, rewrite it. Objectives are general-purpose; ZTARE-specific
  vocabulary belongs in the body or in linked KRs/tasks.

## Closure pressure

Daemon evaluates `closure_deadline` against wall clock on each poll.
At `warn_at_pct` (default 80%), surfaces in the notification digest with
Objective title + KR statuses + scores. At `closure_deadline`, posts
closure prompt with options: `done | abandon | extend`. Default after
7 days no response: `archive_with_postmortem`.

## Theatre-detection

Daemon computes per-Objective **honesty score** at closure:
`(count of world-measured KRs with non-null last_measured_utc in the
closure window) / (count of world-measured KRs)`. If <0.5 for two
consecutive Objective closures, daemon posts: *"OKR honesty score
declining. The system may have collapsed into theatre. Consider
deleting or simplifying."*

## Minimum viable practice (solo scale)

~30 minutes per quarter:
- Score each closing KR 0.0–1.0 with one-line rationale.
- Read auto-postmortems for archived Objectives; edit if wrong.
- Author or refine 1–3 Objectives for next horizon.

If you find yourself spending 30 min/week on Objectives, the system
is being misused — prune the system, not your behavior.

## See also

- `org/key_results/README.md` — KR layer schema
- `org/tasks/README.md` — Task layer schema (renamed from goals/)
- `GP-168 (internal seam)`
  — origin of the closure-pressure model and full panel synthesis
