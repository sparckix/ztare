# org/key_results/ — Key Result layer (GP-168 addendum, mid tier)

Markdown-first KR artifacts, one file per KR. KRs are first-class
files (not YAML array entries on Objectives) per Panel B synthesis —
gives clean git diffs, KR-level audit trail, reassignability,
agent-friendly mutation, no future migration cost.

## Why this layer exists

A Key Result is a measurable outcome that proves a parent Objective
is being achieved. Without KRs, an Objective's success is
self-graded by the principal (intrinsic measurement) and drifts toward
self-flattering scores — biologist seat in Panel B: *"Cells that
measure their own success become tumors."*

KRs force the principal to commit to *how the world will tell us
this Objective worked*, not how the principal feels about it.

## Lifecycle

```
org/key_results/<kr_id>.md
   │
   │  status: pending → on_track | at_risk → done | failed
   │
   │  daemon polls measurement_source on review_overdue_threshold_days
   │  if measurement_source: daemon, daemon attempts re-measurement
   │  if measurement_source: principal, daemon nudges via Telegram
   ▼
   status: done | failed   ← parent Objective closure scores 0.0–1.0
```

## Schema

Frontmatter (canonical):

```yaml
---
kr_id: <snake_case>                          # stable id, never reused
objective_id: <parent_objective_id>          # foreign key into org/objectives/
description: "<one sentence — what changes in the world>"
measurement: "<concrete: how is this measured, by what tool/source>"
measurement_source: daemon | principal       # who reads the metric
measurement_locus: self | world              # WHERE the measurement comes from
kr_type: output | outcome | health_metric    # required tag
target: "<numeric or boolean threshold>"     # e.g., ">= 3", "<= 2 weeks", "true"
status: pending | on_track | at_risk | done | failed
score: float | null                          # 0.0–1.0, set at parent closure
score_rationale: "<one line>" | null
last_measured_utc: <iso> | null
review_overdue_threshold_days: 14            # daemon escalates after this
check_ins:                                   # append-only confidence log
  - {utc: <iso>, confidence: 0.7, note: "<one line>"}
created_utc: <iso>
---

# <human title>

<optional context — measurement methodology details, links to evidence,
data source pointers>
```

## Field semantics

**`measurement_locus`** — controlling.
- `self`: principal grades the KR himself ("I think paper 5 is on track"). Drifts toward self-flattery. At least one `world`-locus KR per Objective is required.
- `world`: external signal (Google Scholar citation count, journal acceptance email, arxiv view count, count of done tasks, external review tone). Honest by construction.

**`kr_type`** — forces output-vs-outcome discipline.
- `output`: things the principal can directly produce ("submit paper 5"). Easy to author, low signal.
- `outcome`: state-of-the-world the principal wants to be true ("3+ external citations within 90d"). Hard to author, high signal.
- `health_metric`: ongoing baseline ("personal sustainable cadence: ≤ 50h/week"). Not progress-shaped; just maintained.

**`measurement_source: daemon`** is preferred. Solo-scale OKR practice
collapses when KRs require principal-driven measurement. Where
possible, write KRs whose measurement is something the daemon can
poll (file count, git commits, external API).

**`check_ins`** — append-only. The daemon adds entries when it
re-measures; the principal can append entries via Telegram thumbs-up
("confidence unchanged"). Two consecutive declining check-ins with no
task work toward the KR triggers `at_risk` flag.

## Closure pressure

Daemon polls each KR on schedule. If `last_measured_utc` is older than
`review_overdue_threshold_days`:
- `measurement_source: daemon` → attempt re-measurement; on success
  update `last_measured_utc` and append check-in. On failure, flag
  `at_risk`, surface in Telegram digest.
- `measurement_source: principal` → nudge in Telegram digest;
  principal can ack with thumbs-up to extend, or write the
  measurement, or accept `at_risk` flag.

Second consecutive overdue cycle → `at_risk` permanent, surfaces in
parent Objective's closure prompt.

## Required invariants

- **`objective_id` must reference an existing `org/objectives/` file
  with `status: active`.** Daemon validates on creation.
- **`measurement` field is concrete and self-contained.** The
  daemon (or principal) must be able to perform the measurement
  without asking clarifying questions.
- **At least one KR per parent Objective has `measurement_locus:
  world` AND `kr_type: outcome`.** Enforced at Objective creation.

## Anti-patterns (refuse to author these)

- KR with `measurement: "TBD"` or `measurement: "see Objective"` —
  if you don't know how to measure it, you don't have a KR.
- KR with all `measurement_source: principal` AND `measurement_locus:
  self` — pure self-grading, will drift into theatre.
- KR with `kr_type: output` and `measurement_locus: world` — usually
  inconsistent (your direct outputs are not world-state).

## See also

- `org/objectives/README.md` — parent layer
- `org/tasks/README.md` — child layer (tasks reference KRs via `kr_id`)
- `research_areas/private/seams/mission/GP-168_org_design_unfalsifiability_seam.md`
  — Panel B synthesis (KRs as files, measurement_locus, kr_type)
