# GP-244 ZTARE Intelligence Surface Spec

## Status

Active - opened 2026-05-20

## Seam

`research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md`

## Scope

Implement a deterministic read-only intelligence compiler for the private ZTARE operator surface.

In scope:

- configured focus-track rows for NS, GNN/LeanMill, and epistemic-generation;
- forecast-market summary from GP-230 artifacts;
- scientific-yield summary from GP-233;
- experiment-ledger summary from `research_areas/EXPERIMENT_TRACK_RECORD.md`;
- action-intelligence and source-health summary from GP-243;
- catch-ledger summary;
- P0/reflexive summary from existing dashboard inputs;
- inventory of the JSON feeds already used by the public analytics dashboard;
- ETL manifest with extract, transform, validate, and load sections;
- source-to-aggregate map;
- source-readiness summary that marks each source `ready`, `partial`, or `blocked`;
- source-improvement backlog for gaps that should be fixed upstream;
- executive brief that states what the read model can and cannot be used for;
- observer-only learning candidates;
- markdown report for agents and humans that do not inspect JSON.
- optional single-file private HTML visualization for human inspection.

Out of scope:

- public dashboard UI work;
- live dashboard writes;
- RD route execution;
- membrane or official-store writes;
- live RL/bandit control;
- replacing source ledgers.

## Architecture

```text
src/ztare/reports/operations_intelligence.py
  -> analytics/private/intelligence/ztare_intelligence_surface.json
  -> analytics/private/intelligence/ztare_intelligence_surface.md
  -> optional analytics/private/intelligence/ztare_intelligence_surface.html

scripts/public/control/operations_intelligence_dashboard.py
  -> thin CLI wrapper
```

The compiler reuses the data already produced for `analytics/public/dashboard` by reading its source JSON feeds. It does not reuse or modify the dashboard UI.

## ETL Contract

The compiler must expose an `etl_manifest`:

- `extract`: source families read and read mode;
- `transform`: aggregate sections and join policy;
- `validate`: missing emitters, weak joins, stale source feeds, and blocking source issues;
- `load`: private output paths and `writes_official_state: false`.

Validation issues do not mutate source state. They feed `attention` and `source_improvement_backlog`.

## Read-Model Contract

Top-level schema:

```json
{
  "schema": "ztare-intelligence-surface-v1",
  "generated_at": "ISO-8601 UTC",
  "headline": {},
  "executive_brief": {},
  "attention": [],
  "learning_candidates": [],
  "etl_manifest": {},
  "source_map": {},
  "source_readiness": {},
  "source_improvement_backlog": [],
  "focus_tracks": {"summary": {}, "rows": []},
  "forecast_market": {},
  "scientific_yield": {},
  "experiment_ledger": {},
  "reflexive_intelligence": {},
  "dashboard_sources": {},
  "research_ops_metric_areas": {},
  "activity_yield": {},
  "learning_candidate_lifecycle": {},
  "recurrence_suppression_candidates": {},
  "metric_caveats": [],
  "catch_and_risk": {},
  "telemetry": {},
  "source_health": {}
}
```

`executive_brief` must include:

- `operating_status`: `ready_read_model|triage_ready|blocked_for_allocation`;
- `status_reason`;
- `source_readiness` summary;
- `first_action` with priority, kind, action, why, and evidence refs;
- `operator_questions`;
- `do_not_use_for`.

`attention` rows must include:

- `priority`: `p0|p1|p2`;
- `kind`;
- `title`;
- `why`;
- `evidence_refs`.

`learning_candidates` rows must include:

- `candidate_id`;
- `transition_kind`;
- `severity`;
- `rationale`;
- `source_kind`;
- `object_ref`;
- `suggested_owner_role`;
- `review_question`;
- `source_refs`;
- `proposed_payload`;
- `observer_only: true`.

## Focus Track Rules

The v1 focus tracks are configured joins, not official project records.

1. `ns_millennium_hunt` reads `projects/ns_millennium_hunt`.
2. `gnn_lemma_relevance` reads LeanMill/GNN public artifacts and command surfaces.
3. `epistemic_generation` reads public paper artifacts plus any configured
   local research overlay.
4. A track is active if it has a fresh durable artifact or recent GP-230/GP-233/experiment reference.
5. Linkage is `strong` when GP-230, GP-233, or the experiment ledger references the track. It is `medium` when fresh artifacts exist without those joins. It is `weak` otherwise.
6. The extractor may take the latest markdown heading/paragraph as `latest_summary`, but it must cite the file.

## Dashboard Feed Reuse

The compiler must summarize the data feeds used by the existing analytics dashboard:

- trajectory curves;
- inflection candidates;
- taste-weighted insight;
- reference graph;
- consequential artifacts by week;
- recursive-gain candidates;
- bifurcation report;
- graph so-what;
- P0 metrics.

This section is data reuse only. It must not add a public tab or stage private intelligence outputs into the public dashboard bundle.

## Private Visualization

The optional HTML output is a local human visualization of the private JSON packet. It should be generated from the same read model and remain under `analytics/private/intelligence/`.

Required views:

- executive brief with operating status, first action, boundaries, and source-readiness counts;
- overview cards for decision-use, ETL blockers, source gaps, tracks, experiments, and forecast contracts;
- attention and source-improvement backlog;
- process/input metric table;
- metric-area table;
- ETL pipeline and validation issues;
- source readiness, source map, and dashboard feed inventory;
- focus tracks and learning candidates;
- recurrence/catch bars;
- raw packet inspection.

The visualization is not a source of truth and must not write state. It is a rendering layer over the JSON packet.

## Source Map Rules

`source_map.rows[]` must include:

- `source_id`;
- `source_refs`;
- `feeds`;
- `aggregate_fields`;
- `source_gaps`.

`source_improvement_backlog[]` must include:

- `priority`;
- `source_id`;
- `gap`;
- `recommended_action`;
- `why_source_not_report`;
- `source_refs`.

The rule is source-first: if the compiler detects that better intelligence requires a better emitter or schema, record it as a source-improvement candidate rather than adding increasingly brittle downstream inference.

`source_readiness.rows[]` must include:

- `source_id`;
- `readiness`;
- `readiness_score`;
- `use_now`;
- `gap_count`;
- `blocking_validation_issues`;
- `next_source_fix`;
- `recommended_action`.

Readiness is not a truth score. It answers whether this source can support the
current read model: `ready` means no detected source gaps, `partial` means use
for triage only, and `blocked` means do not use it for allocation claims until
the source issue is repaired.

## Research-Ops Metrics

The first implemented metric groups are:

- metric-area interface for information yield, decision use, recursive learning, research flow, reliability/calibration, and externality guardrails;
- `forecast_decision_use_rate` and `decision_use_gap`;
- `activity_yield` from trajectory curves;
- `learning_candidate_lifecycle`;
- `recurrence_suppression_candidates`;
- `metric_caveats`;
- `source_health_summary`.

These metrics are diagnostic until their source joins are stable and consumed in a decision.

`research_ops_metric_areas.areas[]` must include:

- `area_id`;
- `purpose`;
- `implemented_metrics`;
- `primary_sources`;
- `status`;
- `source_gap`.

## Validation

Required checks:

1. Unit tests for markdown table parsing, focus-track extraction, experiment-ledger extraction, source-health attention rows, source map, and ETL manifest.
2. CLI smoke that writes JSON and markdown under `analytics/private/intelligence/`.
3. Confirm default outputs are ignored by git.

## Implementation Notes

Keep reusable logic in `src/ztare/reports/`. Keep `scripts/public/control/` as a command surface only.

Do not parse every possible historical artifact shape. The first implementation should expose weak standardization as source-health or linkage debt and make the next schema decision visible.
