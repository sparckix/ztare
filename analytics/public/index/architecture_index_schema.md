# Architecture Index Schema (`analytics/public/index/architecture_index.jsonl`)

**Purpose**: Discoverability meta-graph for ZTARE architectural primitives. Analogous
to `seam_graph` but for code/runtime capabilities. Wired into
`org/mandates/research_director_mandate.md` so every Director dispatch sees the
catalog of available primitives — pattern-matched by lexical triggers.

**Context (2026-05-08)**: The motivating discoverability failure — ~60+ gates,
GP-216/GP-219 ops, Lagrangian derivation, eigenquestion generator, mining
infrastructure, fit primitives all underused tonight until operator prompted.
Index is the load-bearing fix.

## File format

`analytics/public/index/architecture_index.jsonl` is JSON Lines. One row per primitive.
Render via `scripts/render_architecture_index.py` to `src/ztare/architecture_index/INDEX.md`.

## Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable identifier, SCREAMING-KEBAB-CASE (e.g. `LAGRANGIAN-DERIVATION`, `MINE-CLIMB-TRIGGERS`). |
| `path` | string | yes | Repo-relative path. Must exist on disk. |
| `kind` | string | yes | One of: `gate` / `op` / `mining` / `primitive` / `pattern` / `anti-pattern` / `reflexive_primitive` / `validator` / `orchestrator` / `script`. The `reflexive_primitive` kind (added 2026-05-08) catalogs load-bearing self-referential architectural components — third class parallel to `pattern` (orchestration) and `anti-pattern` (failure modes); see `org/reflexive_primitives/INDEX.md`. |
| `description` | string | yes | One-line capability summary. |
| `applicability` | array<string> | yes | Lexical/structural triggers when to deploy. Director pattern-matches these. |
| `impact_factor_expost` | int | yes | 0-5 honest score. Criteria: catch ledger refs + climb-trigger mining + tonight's session usage producing load-bearing output. |
| `last_used` | string | yes | ISO date `YYYY-MM-DD`, or `"never"`. |
| `dependencies` | array<string> | yes | Other primitive `id`s this composes with. |

## Impact factor scoring rubric (anti-laundering)

- **5**: Tonight produced a load-bearing catch via this primitive AND it appears in catch ledger / top climb trigger.
- **4**: Used tonight + produced load-bearing output, OR appears in ≥1 ratified catch.
- **3**: Used in recent (last 14 days) substrate work with verified output, but no catch ledger row.
- **2**: Wired and validated but only intermittent recent use.
- **1**: Exists but rarely fired in last 30 days. Architectural debt candidate.
- **0**: Never observed firing in catch ledger or any recent F-row. Strong retire candidate.

DO NOT inflate. If a primitive was untouched all session AND absent from catch ledger, score it 0-1. Honest 0-scoring surfaces architectural debt.

## Counting + querying

```
# Count by impact tier
grep '"impact_factor_expost": 5' analytics/public/index/architecture_index.jsonl | wc -l

# Find primitives matching a trigger
python scripts/render_architecture_index.py --grep "lagrangian"
```

The render script outputs `src/ztare/architecture_index/INDEX.md` grouped by `kind`,
sorted by `impact_factor_expost` descending, with a TOP-10 high-impact section.

## Discoverability wiring

`org/mandates/research_director_mandate.md` references this index:

> Before dispatching agents on a hard problem, check
> `src/ztare/architecture_index/INDEX.md` for available primitives — pattern matching by
> lexical triggers / problem class. The index is impact-weighted from the
> catch ledger + climb-trigger mining.

Future agents read the mandate (which is in CLAUDE.md / AGENTS.md context),
so wiring the index there makes capabilities discoverable by default.

## Maintenance

Append-only by default. Update `impact_factor_expost` + `last_used` when a
primitive fires in a load-bearing way. Periodic prune of `impact_factor_expost: 0`
entries during retirement reviews (don't auto-delete; flag for principal).
