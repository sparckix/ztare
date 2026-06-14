# GP-244 ZTARE Intelligence Surface Seam

> **Seam metadata** · `seam_id:` GP-244 · `track:` apparatus/instrumentation · `status:` active · `opened:` 2026-05-20 · `last_updated:` 2026-05-20

## Eigenquestion

Can ZTARE compose its existing telemetry, forecast, yield, catch, reflexive-mining, action-intelligence, and experiment surfaces into one private read model that helps humans and agents choose attention without inventing new authority?

## Status

Active. This seam promotes a private read-only intelligence compiler. It does not change RD tick mechanics, membrane semantics, GP-230 allocation, GP-233 interpretation, the experiment track record, or the official store.

## Context

ZTARE already has mature local instruments:

- GP-227 trajectory and recursive-gain dashboard;
- GP-230 forecast pool and decision-market state;
- GP-233 scientific-yield decomposition;
- GP-243 action-intelligence source-health/read model;
- catch ledger;
- experiment track record;
- GP-038/040 iteration telemetry;
- LeanSearch factory P0 rollups and live-state dashboards;
- the source JSON feeds already used by the public analytics dashboard;
- durable work surfaces in NS, GNN/LeanMill, and epistemic-generation.
- factory-style read models such as LeanMill factory intelligence, consumed as
  source surfaces rather than copied into this compiler.

The gap is not another source ledger. The gap is an ETL-style private intelligence surface that tells the operator:

1. Which instruments are producing usable signals.
2. Which joins are weak or stale.
3. Which unresolved forecast and source-health items block trust.
4. Which recurring bottlenecks should become learning candidates.
5. What the current focus tracks show without pretending they are standardized projects.
6. Which source emitters or schemas should be improved upstream.

## Decision

Build a deterministic read-model compiler:

```text
existing ledgers + configured focus tracks -> ztare_intelligence_surface.json
ztare_intelligence_surface.json -> private markdown, optional private static HTML
```

The compiler is a consumer only. It may read public analytics, project workspaces, research-output logs, working papers, and seam/spec metadata. It must not write official rows, forecast outcomes, GP-233 entries, catch rows, experiment rows, or membrane proposals.

The compiler should expose its own pipeline contract:

```text
extract: source files and freshness
transform: aggregate sections and join policy
validate: missing emitters, weak joins, stale sources, and caveats
load: private JSON/markdown outputs only
```

The optional HTML output is a private visualization of the same packet. It is not a new authority. It should make the ETL state, process/input metrics, source map, source gaps, focus tracks, and recurrence risks inspectable by a human without reading raw JSON.

## MECE Sections

| Section | Question answered | Primary sources |
|---|---|---|
| `attention` | What needs attention now? | source health, unresolved forecast contracts, weak joins |
| `learning_candidates` | What could become a durable learning transition after review? | source health, forecast debt, GP-233 bottlenecks |
| `etl_manifest` | What was extracted, transformed, validated, and loaded? | compiler source map and validation checks |
| `source_map` | Which sources feed which aggregates? | all read sources |
| `source_improvement_backlog` | Which gaps should be fixed at the source? | validation issues and source-health debt |
| `focus_tracks` | What do the current high-interest tracks expose? | NS, GNN/LeanMill, epistemic-generation, and agentic-workbench artifacts plus ledger/action joins |
| `forecast_market` | Is GP-230 producing usable allocation evidence? | contracts, aggregates, outcomes, scores, decision-use rows |
| `scientific_yield` | What bottlenecks and next levers are recurring? | GP-233 evidence ledger |
| `experiment_ledger` | What does the experiment track record say? | `research_areas/EXPERIMENT_TRACK_RECORD.md` |
| `reflexive_intelligence` | What is the apparatus learning about itself? | P0 metrics, recursive gain, bifurcation, action intelligence |
| `dashboard_sources` | Which existing dashboard data feeds are present and fresh? | trajectory, taste, reference graph, P0, recursive-gain, bifurcation JSONs |
| `research_ops_metric_areas` | Which metric families are implemented, partial, or source-blocked? | GP-244 synthesis, source map, metric caveats |
| `catch_and_risk` | What failure modes are recurring? | catch ledger, action-intelligence source health |
| `telemetry` | Is there enough runtime data to reason about speed/cost/tails? | iteration telemetry streams |

## Focus Track Layer

The first configured focus tracks are:

- `ns_millennium_hunt`;
- `gnn_lemma_relevance`;
- `epistemic_generation`;
- `agentic_ai_workbench`.

These are joins, not official project records. Each focus row carries:

```json
{
  "track_id": "ns_millennium_hunt",
  "label": "NS Millennium Hunt",
  "paths": ["projects/ns_millennium_hunt"],
  "latest_touch": "2026-05-20T12:00:00Z",
  "activity_state": "active|stale",
  "linkage_quality": "strong|medium|weak",
  "signals": {
    "forecast_refs": 0,
    "gp233_refs": 0,
    "catch_refs": 0,
    "experiment_refs": 0,
    "action_refs": 0,
    "status_files": 0
  },
  "latest_summary": "short extracted heading or paragraph",
  "evidence_refs": []
}
```

Weak linkage is an output, not a failure. It means the system can see activity but cannot yet join it confidently to forecast, yield, catch, or experiment evidence.

The `agentic_ai_workbench` track joins GP-243 `domain=agentic_workbench` rows
with autoresearch projection/dispatch seams and reflexive-mining outputs. It
exists to answer whether RD/out-of-loop agent labor is bypassing, preparing, or
feeding the in-loop workbench. It must not become a second scheduler.

## Learning Candidate Rule

The surface may emit observer-only learning candidates. These are review prompts, not state transitions. Required fields include:

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

No candidate may modify official state without a later membrane-approved path.

## Source-Health Rule

The surface is invalid if it turns missing emitters into confident prose. Examples:

- no decision-use rows while forecast aggregates exist -> show source-health debt;
- GP-233 rows with markdown-only linkage -> show weak linkage;
- focus tracks with artifacts but no forecast/yield/experiment joins -> show weak linkage;
- catch rows not linked to a track -> count globally, do not assign them unless the artifact text supports it.

## Source Map Rule

Every aggregate in the surface should be traceable to a source family. If an aggregate needs better source structure, the surface must emit a source-improvement row rather than burying the problem in prose. Examples:

- GP-230 aggregate without decision-use rows -> improve the decision-use emitter;
- GP-233 markdown rows that cannot be joined cleanly -> add a derived structured read model;
- catch categories that recur without suppression labels -> add recurrence/avoidance labels at the catch source;
- focus-track activity without ledger refs -> improve track-local status or source references.

## Metric-Area Interface

The metric interface has six areas:

- `information_yield`;
- `decision_use`;
- `recursive_learning`;
- `research_flow`;
- `reliability_calibration`;
- `externality_guardrails`.

Each area must state implemented metrics, primary sources, current status, and source gaps. This prevents the surface from implying that a metric family is complete when it is only partially instrumented.

## Outputs

`src/ztare/reports/operations_intelligence.py` compiles the read model.

`scripts/public/control/operations_intelligence_dashboard.py` is the CLI wrapper.

Default outputs are private and gitignored:

```text
analytics/private/intelligence/ztare_intelligence_surface.json
analytics/private/intelligence/ztare_intelligence_surface.md
analytics/private/intelligence/ztare_intelligence_surface.html  # optional
```

## Non-Goals

- Do not create a public dashboard tab in v0. Reuse dashboard data feeds, not the UI.
- Do not auto-route RD ticks.
- Do not normalize all projects into a forced schema.
- Do not collapse scientific yield into one score.
- Do not use activity volume as a substitute for progress.

## Promotion Criteria

The seam is useful if:

1. The surface can summarize GP-230, GP-233, experiment, catch, reflexive, and source-health signals in one packet.
2. The surface shows weak linkage instead of fabricating confident joins.
3. The markdown and JSON are enough for an operator or agent to inspect attention and learning candidates quickly.
4. At least one operator or agent decision uses the surface to repair an emitter, close a forecast contract, or retire a stale branch.
5. The implementation remains read-only and does not duplicate source-ledger authority.
