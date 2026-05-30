# GP-243 Action Intelligence Loop Spec

## Status

Active — opened 2026-05-19 14:39:32 EDT

## Seam

`research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md`

## Scope

This spec governs a conservative v0 action-intelligence loop for ZTARE:

- a durable action-impact ledger;
- a materialized action-intelligence read model;
- shadow recommendations for forecast operations;
- shadow recommendations for trajectory/primitives surfacing;
- observer-mode advisory recommendations that do not disturb RD pre-tick behavior by default.

Out of scope:

- live RL or bandit control over RD decisions;
- live LMSR or continuous price mechanics;
- replacing GP-230, GP-233, the catch ledger, the prediction ledger, or the trajectory archive;
- optimizing a single scalar research reward;
- NS theorem-frontier live route selection.

## Eigenquestion

Can ZTARE bind forecasts, yield decompositions, catches, and trajectory-mining evidence into a queryable action-impact loop while keeping recommendations advisory, auditable, and externality-aware?

## Decision

Implement GP-243 as a read-model layer over existing primitives.

The v0 loop is:

```text
forecast/state/trajectory evidence -> action-impact row
-> action-intelligence read model -> shadow recommendation
-> RD pre-tick surfacing -> later outcome linkage
```

The implementation must first repair and populate decision-use capture. Shadow recommendations are allowed only as advisory read-model rows. They must cite their source rows and include a confidence class. No GP-243 component may execute, resolve, score, open, close, or override a research tick.

The implementation must also fail diagnostic-first when source compilation is
weak. GP-243 is not allowed to turn missing or stale upstream rows into
apparently precise recommendations. If the source surfaces are too incomplete,
the output should recommend source-emitter repair rather than routing or
surfacing action.

GP-243 must not duplicate GP-230 allocation. Forecast-operations rows consume
GP-230's aggregate/read-model recommendation and evaluate whether it was used,
ignored, or overrode later action. A GP-243 "recommendation" in this domain is
an audit/read-model presentation of GP-230 state plus source-health status, not
a second allocator.

## Problem

ZTARE's current ledgers answer separate questions:

- GP-230 answers: what did forecasters believe, what did the market aggregate, and how were forecasts scored?
- GP-233 answers: where did scientific yield come from or fail?
- The catch ledger answers: what did the apparatus catch after the fact?
- The trajectory archive answers: what happened across runs and iterations?
- RD pre-tick brief answers: what should the RD be reminded of before acting?

What is missing is a binding object:

```text
At decision point D, these actions were available, action A was selected,
these signals influenced it, this outcome happened, these externalities
appeared, and this should or should not shift future routing/surfacing.
```

Without this object, ZTARE can have locally useful forecasts and locally useful trajectory mining while still failing to compound organizational learning.

## Options

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| A | Keep current ledgers separate | No new code; no extra bookkeeping | Does not answer whether signals changed useful action | Reject |
| B | Add an action-impact ledger only | Creates the missing binding object | Useful but not enough to surface recommendations | Accept as Phase 1 |
| C | Add ledger plus materialized read model and shadow recommendations | Turns historical rows into advisory routing/surfacing suggestions | Requires careful confidence and externality handling | Accept for v0 |
| D | Add live bandit/RL control | Adaptive allocation | Goodhart, unsafe exploration, delayed rewards, accountability blur | Reject for v0 |

## Architecture

### Files

New artifacts:

```text
analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl
analytics/public/ledgers/action_intelligence/surfacing_event_ledger.jsonl
analytics/public/action_intelligence/state/action_intelligence.json
analytics/public/action_intelligence/state/shadow_recommendations.json
analytics/public/action_intelligence/state/source_health.json
```

Rationale: the ledger belongs under `analytics/public/ledgers/` because it binds multiple primitives. The materialized read model belongs under `analytics/public/action_intelligence/` because it is a derived state surface, not a source ledger.

### CLI

Add a small public CLI:

```text
scripts/public/control/action_intelligence.py
```

Commands:

```text
materialize
record-impact
record-surfacing-event
shadow-recommend
health
smoke
```

`materialize` reads existing ledgers and writes read models.

`record-impact` appends a typed action-impact row. Most v0 rows should come from GP-230 decision-use rows, not manual entry.

`record-surfacing-event` appends a typed trajectory/primitives surfacing event.
Consumed or explicitly suppressed events are materialized into
`ActionImpactRow` rows with `domain=trajectory_surfacing`.

`shadow-recommend` emits advisory recommendations for forecast operations and trajectory/primitives surfacing.

`health` reports source freshness, row counts, and blocking instrumentation gaps.

`smoke` runs deterministic fixture checks.

## Schema

### Controlled Action Vocabularies

Forecast-operations actions:

```text
run_now
split_contract
ask_another_independent_agent
defer
kill_branch
ignore_forecast
override_forecast
repair_source_emitter
```

GP-230 `decision_use.used_for` mapping:

| GP-230 `used_for` | GP-243 action |
|---|---|
| `run` | `run_now` |
| `split` | `split_contract` |
| `ask_more` | `ask_another_independent_agent` |
| `defer` | `defer` |
| `kill` | `kill_branch` |
| `ignore` | `ignore_forecast` |
| `override` | `override_forecast` |

Trajectory/primitives surfacing actions:

```text
surface_pattern
surface_anti_pattern
surface_trajectory_cluster
surface_gp233_next_lever
surface_catch_preconditioner
suppress_surface_as_low_voi
repair_source_emitter
```

### ActionImpactRow

```json
{
  "schema_version": 1,
  "action_impact_id": "ai_<stable_or_uuid>",
  "recorded_at": "2026-05-19T18:39:32Z",
  "decision_point": {
    "decision_id": "string",
    "tick_id": "string|null",
    "project_id": "string|null",
    "domain": "forecast_ops|trajectory_surfacing|proof_repair|other",
    "stage": "pretick|membrane|posttick|manual|offline"
  },
  "candidate_actions": [
    "run_now",
    "split_contract",
    "ask_another_independent_agent",
    "defer",
    "kill_branch"
  ],
  "selected_action": "run_now",
  "policy_source": "rd|forecast_market|trajectory_miner|manual|shadow_policy|unknown",
  "logged_policy": {
    "logging_policy": "gp230_allocation|rd_manual|trajectory_surface|unknown",
    "propensity_or_selection_rule": "deterministic_rule|manual|unknown",
    "eligible_actions": [],
    "why_selected": "string|null",
    "why_not_selected": {}
  },
  "source_refs": {
    "forecast_contract_id": "string|null",
    "decision_use_id": "string|null",
    "forecast_aggregate_path": "string|null",
    "forecast_score_path": "string|null",
    "gp233_evidence_ref": "string|null",
    "catch_ids": [],
    "trajectory_refs": [],
    "prediction_ids": []
  },
  "context_features": {
    "p_success": 0.0,
    "expected_cost_agent_minutes": 0.0,
    "forecast_spread": 0.0,
    "top_failure_mode": "string|null",
    "current_bottleneck": "string|null",
    "next_lever": "string|null",
    "surface_kind": "string|null"
  },
  "outcome": {
    "known": false,
    "success_bool": null,
    "decision_impact": "string|null",
    "yield_signal": "string|null",
    "actual_cost_agent_minutes": null,
    "negative_externality_tags": [],
    "catch_ids_realized": []
  },
  "counterfactual": {
    "baseline_action": "string|null",
    "counterfactual_action": "string|null",
    "counterfactual_value_bucket": "string|null",
    "notes": "string|null"
  }
}
```

Validation:

- `selected_action` must be present in `candidate_actions`.
- `stage` must be controlled vocabulary.
- `policy_source=shadow_policy` is allowed only for offline evaluation rows, not live RD action rows.
- live rows may not use `policy_source=shadow_policy`.
- `outcome.known=false` must not be scored as success or failure.
- rows with `selected_action` in `ignore|override` equivalents must carry a reason in `counterfactual.notes`.

### SurfacingEvent

Trajectory/primitives surfacing cannot move beyond diagnostic-only until this
event shape is populated.

```json
{
  "schema_version": 1,
  "surface_id": "sf_<hash>",
  "surface_kind": "pattern|anti_pattern|trajectory_cluster|gp233_next_lever|catch_preconditioner",
  "surface_payload_ref": "path_or_id",
  "project_family": "string",
  "target_decision_id": "string|null",
  "shown_at": "2026-05-19T18:39:32Z",
  "rank": 1,
  "consumed_bool": false,
  "consumed_at": null,
  "consumed_by_tick": null,
  "suppressed_reason": null,
  "negative_externality_tags": [],
  "selected_action": "surface_trajectory_cluster",
  "policy_source": "trajectory_miner",
  "decision_impact": "string|null",
  "yield_signal": "string|null",
  "outcome_known": false,
  "notes": "string|null"
}
```

Validation:

- `surface_kind` must be one of `pattern`, `anti_pattern`,
  `trajectory_cluster`, `gp233_next_lever`, or `catch_preconditioner`.
- `surface_payload_ref` and `project_family` are required.
- `rank` must be an integer greater than zero.
- `consumed_bool=true` requires `consumed_by_tick`.
- unconsumed events do not become action-impact rows; consumed or explicitly
  suppressed events do.

### ShadowRecommendation

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-19T18:39:32Z",
  "recommendation_id": "sr_<hash>",
  "domain": "forecast_ops|trajectory_surfacing",
  "decision_id": "string",
  "recommended_action": "ask_another_independent_agent",
  "confidence": "diagnostic_only|low|medium",
  "rationale": "short typed reason",
  "evidence_refs": [],
  "externality_checks": {
    "negative_externality_risk": "low|medium|high|unknown",
    "goodhart_risk": "low|medium|high",
    "sample_size": 0,
    "min_sample_size_met": false,
    "confidence_interval": null,
    "uncertainty_note": "string|null"
  },
  "execution_authority": "none_advisory_only"
}
```

Validation:

- v0 may not emit `confidence=high`.
- `execution_authority` must always be `none_advisory_only`.
- `sample_size < 20` forces `confidence=diagnostic_only`.
- recommendations must cite at least one source artifact.
- `negative_externality_risk=high` forces `confidence=diagnostic_only`.
- no recommendation may imply a changed RD route without an action-impact row
  recording that the RD consumed it.

### SourceHealthIssue

```json
{
  "issue_id": "sh_<hash>",
  "severity": "info|warning|blocking",
  "scope": "global|forecast_ops|trajectory_surfacing|gp233|catch",
  "domain": "string|null",
  "issue_type": "missing_decision_use|weak_gp233_linkage|stale_trajectory_output|unconsumed_surface|missing_source|other",
  "expected_count": 0,
  "observed_count": 0,
  "denominator": "string",
  "freshness_window_days": 14,
  "affected_domains": [],
  "blocking_rule": "string",
  "recommended_action": "repair_source_emitter",
  "evidence_refs": []
}
```

## Source Adapters

### Source-Health Gate

Every materialization must compute source health before recommendation
generation.

Required checks:

- GP-230 aggregate count vs decision-use/action-impact row count;
- missing decision-use ledger while aggregates exist;
- GP-233 rows that cannot be linked to a project, tick, contract, or evidence pointer;
- catch rows with `load_bearing=true` but no later action-impact reference;
- trajectory miner outputs that are missing, stale, or unavailable as dated artifacts;
- recommendations with no later consumption evidence.

Blocking is scoped. A `trajectory_surfacing` blocker does not freeze
`forecast_ops`; a global blocker does. If a scoped blocking issue is present,
recommendations in that scope must include:

```json
{
  "confidence": "diagnostic_only",
  "blocking_checks": ["source_compilation_defect"],
  "recommended_action": "repair_source_emitter"
}
```

This gate prevents GP-243 from becoming a wrapper over weak compilation.

### GP-230 Adapter

Inputs:

- contracts;
- aggregates;
- scores;
- decision-use rows;
- market-state reliability/reflexive insights.

Behavior:

- convert each decision-use row into one action-impact row;
- preserve aggregate allocation action and selected action;
- include score/outcome fields when available;
- surface a source-health warning if decision-use rows are missing while aggregates exist.
- do not recompute GP-230 allocation except to report drift in a diagnostic
  audit row.

Required first fix:

- `start_tick.py` must read `allocation_recommendation.action`, while accepting legacy `allocation_recommendation.recommendation` as fallback.

### GP-233 Adapter

Inputs:

- `GP-233_EVIDENCE_LEDGER.md`.

Behavior:

- v0 may parse coarse project/tick/decision-impact references from markdown;
- future GP-233 emitters should add JSONL, but v0 must not block on that migration;
- attach `current_bottleneck`, `next_lever`, and `decision_impact` when a matching tick or contract can be inferred.
- any GP-233 linkage inferred only from markdown remains diagnostic-only.
  Medium-confidence claims require structured identifiers:
  `tick_id`, `project_id`, `contract_id`, or `lane_id`.

### Catch Adapter

Inputs:

- `catch_ledger.jsonl`.

Behavior:

- attach decisive catches by catch id when referenced by contract/outcome/tick rows;
- add negative externality tags when catch category indicates laundering, recurrence, false positive, missed preconditioner, or decision-policy failure.

### Trajectory Adapter

Inputs:

- trajectory archive;
- enriched trajectory archive when present;
- miner outputs that already summarize primitive ROI or trajectory clusters.

Behavior:

- create surfacing candidate rows for repeated failure basins, primitive suggestions, GP-233 next levers, and catch preconditioners;
- do not claim a surface helped unless a later action-impact row records decision use.
- emit `SurfacingEvent` rows before claiming surfacing consumption.
- materialize consumed or suppressed `SurfacingEvent` rows into
  `ActionImpactRow` rows with `source_refs.surface_event_id`.

## Shadow Recommendation Rules

### Forecast Operations

Use GP-230 aggregate and reliability state. GP-243 does not own these rules as
an allocator; it displays GP-230's own recommendation and records whether the
recommendation was consumed. The rules below are for audit comparison only.

Initial deterministic rules:

- fewer than two effective independent forecasts -> `ask_another_independent_agent`;
- high forecaster spread -> `ask_another_independent_agent`;
- medium success probability plus concentrated failure mode -> `split_contract`;
- low probability, negative expected value, no declared information value -> `kill_branch`;
- negative expected value but nonzero information value -> `defer`;
- high probability and positive expected value -> `run_now`.

These rules intentionally mirror GP-230's allocation vocabulary. GP-243 records and evaluates their downstream use; it does not create a second market.

### Trajectory / Primitives Surfacing

Use trajectory-mining summaries, GP-233 bottlenecks, and catch rows.

Initial deterministic rules:

- repeated catch category in current project family -> `surface_catch_preconditioner`;
- GP-233 `next_lever` unresolved in current project family -> `surface_gp233_next_lever`;
- trajectory cluster matches current failure basin -> `surface_trajectory_cluster`;
- pattern or anti-pattern has recent positive decision-use rows -> `surface_pattern` or `surface_anti_pattern`;
- surfaced primitive has repeated non-use or negative externality rows -> `suppress_surface_as_low_voi`.

All v0 trajectory recommendations are `diagnostic_only` unless at least 20 historical action-impact rows exist for the same surfacing domain.

If the trajectory/primitives adapter cannot show that a surface has been
consumed by a later action-impact row, it may recommend surfacing as a
diagnostic reminder, but it must not claim that surfacing improved future
decisions.

## Integration Points

### RD Tick Brief

GP-243 is observer-only by default. `rd_tick_brief.py` should not add a default
RD interruption until action-impact and surfacing-consumption evidence exists.

Once explicitly enabled by a later operator/RD decision, `rd_tick_brief.py` may
surface:

- action-intelligence source health;
- top 3 shadow recommendations;
- decision-use/action-impact row counts;
- warning when GP-230 aggregates exist but no corresponding action-impact rows exist.

### Start Tick

`start_tick.py` should continue auto-recording GP-230 decision use, with the key fix noted above. GP-243 should consume the resulting decision-use row rather than adding another start-tick side effect.

### Forecast Pool Materialization

`forecast_pool.py materialize-state` may remain GP-230-owned. GP-243 should call or read its outputs, not duplicate forecast aggregation.

### Cognitive-Firm Boundary

ZTARE owns this implementation as a tenant-specific action-intelligence read model. A future cognitive-firm interface may expose generic action-impact views, but this spec must not duplicate GP-230's opinionated forecast-market implementation in the kernel.

## Hard Invariants

- GP-243 may not write GP-230 contracts, forecasts, aggregates, outcomes, or scores.
- GP-243 may not open, close, resolve, score, or override research ticks.
- GP-243 may not automatically change RD routing.
- GP-243 may not optimize or publish a single scalar global reward.
- GP-243 may not emit `confidence=high` in v0.
- GP-243 may not promote a learned policy from shadow to live control.
- Any high negative-externality risk caps confidence at `diagnostic_only`.

## Acceptance Criteria

1. A new GP-243 spec exists and is linked from the seam.
2. A Claude CLI adversarial review is appended to the seam before implementation.
3. `action_intelligence.py smoke` passes on deterministic fixtures.
4. `forecast_pool.py materialize-state` still runs after GP-243 changes.
5. `start_tick.py` decision-use capture accepts `allocation_recommendation.action`.
6. `action_intelligence.py materialize` writes:
   - `analytics/public/action_intelligence/state/action_intelligence.json`;
   - `analytics/public/action_intelligence/state/shadow_recommendations.json`;
   - `analytics/public/action_intelligence/state/source_health.json`.
7. `action_intelligence.py record-surfacing-event` accepts shown and consumed
   trajectory/primitives surfaces. `materialize` derives consumed/suppressed
   events into trajectory-surfacing action-impact rows.
8. GP-243 is observer-only by default; any RD tick brief integration is absent-artifact tolerant and opt-in/proven-later.
9. No GP-243 artifact has execution authority.
10. Source-health defects force `diagnostic_only` recommendations and include a source-emitter repair recommendation.
11. Smoke fixtures cover:
    - missing decision-use with aggregates;
    - weak GP-233 linkage;
    - stale trajectory outputs;
    - unconsumed surfacing;
    - live `shadow_policy` row rejection;
    - `ignore/override` without reason;
    - surfacing-event-to-action-impact derivation;
    - source-health forcing `repair_source_emitter`.

## Open Questions

1. Should GP-233 JSONL emission become mandatory after v0?
2. Should surfacing recommendations be grouped by project family, substrate, or RD owner?
3. Should action-impact rows be linked back into GP-230 scores when the forecast directly changed execution?
4. What confidence thresholds should be used after enough rows exist for medium-confidence shadow recommendations?
