# GP-244 Research Operations Metrics Synthesis

Generated: 2026-05-20

## Question

What research-operations metrics should ZTARE collect, given that it is a recursive research organization with forecast markets, scientific-yield decomposition, catch ledgers, trajectory mining, experiment ledgers, and agent/human membrane workflows?

## Short Answer

ZTARE should not optimize for one “research productivity” number. The metric system should be a balanced read model with six families:

1. **Information yield**: what changed belief, route choice, or artifact quality.
2. **Decision use**: whether forecasts, catches, and reflexive surfaces actually changed action.
3. **Recursive learning**: whether a failure or insight becomes a reusable primitive, gate, pattern, or retired route.
4. **Research flow**: lead time from question to discriminating evidence, with failure and recovery rates.
5. **Reliability and calibration**: forecast calibration, high-confidence misses, source-health debt, and evidence coverage.
6. **Externality guardrails**: Goodhart, tunnel vision, human bottleneck, over-formalization, and false closure pressure.

The current ZTARE telemetry already covers parts of 1, 3, 4, and 5. The biggest missing layer is **decision-use and transfer accounting**: did a surfaced insight, forecast, catch, primitive, or recursive-gain candidate get consumed, and did it improve the next run?

## Literature Grounding

The strongest external lesson is multidimensionality. R&D performance does not reduce cleanly to one top-level metric; McKinsey’s R&D metrics review cites the need for suites of metrics across organizational levels rather than a single executive number. The SPACE framework for developer productivity makes the same point in software: productivity should be read through satisfaction/well-being, performance, activity, communication/collaboration, and efficiency/flow, and warns that simple activity measures miss collaboration, brainstorming, and quality. DORA’s delivery metrics are useful because they pair throughput with instability: change lead time and deployment frequency only make sense beside change-failure and recovery metrics.

Responsible research-metrics literature adds the anti-Goodhart discipline. The Leiden Manifesto argues that quantitative indicators should support qualitative expert judgment, be contextualized by mission, use multiple indicators, account for field differences, and be regularly scrutinized. DORA research-assessment guidance similarly warns against simplistic proxy use in academic evaluation. For ZTARE, that means every metric needs an explicit purpose, denominator, and known failure mode.

Organizational-learning literature gives the key theory of what “compounding” should mean. March’s exploration/exploitation model warns that systems that refine exploitation faster than exploration can become effective in the short run and self-destructive over time. Cohen and Levinthal’s absorptive-capacity frame says the ability to use external knowledge depends on prior related knowledge and internal R&D. For ZTARE, recursive improvement is not “more agent work”; it is improved absorption, transformation, and reuse of evidence across future ticks.

Prediction-market literature supports GP-230 as an information-aggregation primitive, but only when information is diverse, independent, and actually used in decisions. Markets that forecast without a decision-use ledger become calibration exercises, not allocation machinery.

Sources:

- DORA software delivery metrics: https://dora.dev/guides/dora-metrics/
- SPACE developer productivity framework: https://queue.acm.org/detail.cfm?id=3454124
- Leiden Manifesto for research metrics: https://www.nature.com/articles/520429a
- Cohen and Levinthal, absorptive capacity: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1504447
- March, exploration and exploitation: https://pubsonline.informs.org/doi/abs/10.1287/orsc.2.1.71
- Prediction markets in theory and practice: https://cepr.org/publications/dp5578

## Local Surfaces Already Available

| Surface | What it already measures | Gap |
|---|---|---|
| GP-227 trajectory mining | capability counts, autonomous actions, F-row creates/closures, paper-line growth, project artifacts, verified axioms, confounds, inflections | needs decision-use and transfer follow-through |
| Recursive-gain candidates | candidate primitives or routines that could compound apparatus capability | needs realized-gain closure rows |
| GP-230 forecast pool | contracts, aggregates, outcomes, scores, allocation hints | decision-use rows are sparse relative to aggregates |
| GP-233 yield decomposition | bottleneck, evidence pointer, verdict, decision changed | linkage remains markdown-heavy and hard to query |
| GP-243 action intelligence | source-health debt, shadow recommendations, action-impact ledger shape | action-impact and surfacing consumption rows are still thin |
| Catch ledger | failure modes, ratification, recurring categories | needs precision/recall against future avoided failures |
| Experiment track record | canonical E/F rows | table cells are rich prose; needs derived structured read model |
| Intelligence surface | focus-track joins, attention, learning candidates, dashboard source inventory | observer-only; no promoted learning-event lifecycle yet |

## Metric Families ZTARE Should Collect

### 1. Information Yield

Purpose: measure whether a run produced discriminating evidence, not whether it produced activity.

Recommended metrics:

- `belief_delta_count`: number of F-rows or equivalent finding rows created per week.
- `decision_changed_rate`: GP-233 rows where the decision changed divided by all GP-233 rows.
- `bottleneck_resolution_rate`: recurring bottlenecks that are retired, narrowed, or converted into a sharper test.
- `negative_result_value`: negative runs that killed a route, reduced search space, or prevented repeated work.
- `evidence_compression_ratio`: number of artifacts condensed into a durable F-row, primitive, gate, or paper claim.
- `claim_scope_accuracy`: share of claims with explicit stop-line/scope guard versus later catch-ledger overclaim.

ZTARE-specific note: on NS, yield should reward “recurrence killed” and “mechanism localized” even when no theorem closes. Otherwise the system will overfit to formal-positive artifacts.

### 2. Decision Use

Purpose: distinguish signals from signals that changed work.

Recommended metrics:

- `forecast_decision_use_rate`: forecast aggregates consumed in a logged action divided by eligible aggregates.
- `catch_preconditioner_use_rate`: catch rows referenced before a run or close.
- `surface_consumption_rate`: trajectory/reflexive/primitive surfaces shown to an agent and later recorded as consumed.
- `prediction_to_action_latency`: time from forecast aggregate to decision-use row.
- `ignored_high_signal_count`: high-confidence forecast/catch/source-health warning not acted on before a repeated failure.
- `allocation_action_mix`: run now, split, ask independent agent, defer, kill branch.

Current gap: source health already flags missing decision-use rows. This is the highest-priority metric repair because it is the bridge from measurement to allocation.

### 3. Recursive Learning

Purpose: measure whether the organization gets better because yesterday’s work changed today’s apparatus.

Recommended metrics:

- `learning_candidate_count`: observer-only candidates emitted by intelligence surfaces.
- `candidate_promotion_rate`: candidates promoted to seam, spec, primitive, gate, pattern, anti-pattern, or retired route.
- `candidate_time_to_resolution`: time from candidate emission to promote/defer/reject.
- `primitive_reuse_rate`: promoted primitives invoked by later ticks.
- `primitive_effect_size`: delta in yield, failure rate, or lead time after primitive adoption versus matched prior runs.
- `recurrence_suppression_rate`: previously caught failure modes that stop appearing in similar future runs.
- `transfer_distance`: whether a learning event transfers within one substrate, across substrates, or into general apparatus.

ZTARE-specific note: recursive learning should be measured at the transition level: `catch -> preconditioner`, `finding -> primitive`, `failed route -> amnesia basin`, `forecast miss -> calibration update`, `operator insight -> mechanized surface`.

### 4. Research Flow

Purpose: adapt DORA-style throughput/instability to research, without treating faster as automatically better.

Recommended metrics:

- `question_to_contract_lead_time`: first named question to forecast contract.
- `contract_to_evidence_lead_time`: forecast contract to discriminating artifact.
- `evidence_to_close_lead_time`: discriminating artifact to membrane close or ledger row.
- `rework_rate`: runs that required repair because of missing close lifecycle, bad forecast setup, stale artifact, or source-health debt.
- `recovery_time`: time from failed gate/source issue to repaired run.
- `parallelism_effectiveness`: information yield per parallel lane, not number of agents launched.
- `human_blocked_time`: time waiting for human action where the agent could not progress.

ZTARE-specific note: for hard math, flow metrics must be conditioned on depth requirements. A fast shallow close is worse than a slower run that satisfies pencil/tool/formal depth.

### 5. Reliability And Calibration

Purpose: make the market and ledgers trustworthy enough to allocate research work.

Recommended metrics:

- `forecast_brier_by_domain`: Brier and skill by substrate, effort class, and agent family.
- `probability_reliability_buckets`: observed success rate for 0-10%, 10-20%, etc.
- `effort_reliability`: predicted effort versus actual effort by contract type.
- `high_confidence_miss_incidents`: misses above a confidence threshold with failure-mode tags.
- `source_health_blocker_days`: age and count of blocking source-health issues.
- `evidence_ref_resolvability`: share of ledger refs that resolve to live files or daemon exports.
- `formal_claim_failure_rate`: later catches or audit failures per formal-positive artifact.

Current ZTARE note: calibration work exists, but the intelligence surface shows the system still needs better decision-use and source-health consumption before market outputs can be treated as strong allocation evidence.

### 6. Externality Guardrails

Purpose: prevent metric optimization from damaging research.

Recommended metrics:

- `activity_yield_divergence`: activity rises while F-row/taste/decision-change measures stagnate.
- `exploration_exploitation_balance`: share of runs opening genuinely new mechanisms versus refining existing routes.
- `route_treadmill_index`: repeated work on a known basin/recurrence without a new discriminator.
- `human_cognitive_load`: unresolved human decisions, manual gate time, repeated clarifications.
- `measurement_overhead_ratio`: time spent measuring/closing versus doing substantive research.
- `metric_churn_count`: new metrics added without a named decision they support.
- `metric_retirement_rate`: metrics retired because they were unused, misleading, or redundant.

ZTARE-specific note: this family is not secondary. It is how the apparatus keeps the market, dashboard, and recursive-gain surfaces from becoming new treadmills.

## Recommended P0 Collection Set

Collect these first because they are high-value and already close to existing artifacts:

| Metric | Source | Why first |
|---|---|---|
| `forecast_decision_use_rate` | GP-230 decision-use ledger + aggregates | tells whether the market affects allocation |
| `source_health_blocker_days` | GP-243 source health | prevents confident use of broken surfaces |
| `candidate_promotion_rate` | intelligence surface learning candidates + seams/specs/primitives | measures recursive learning follow-through |
| `recurrence_suppression_rate` | catch ledger + amnesia manifests + later runs | directly tests whether ZTARE stops repeating itself |
| `decision_changed_rate` | GP-233 | preserves information-yield objective |
| `activity_yield_divergence` | trajectory curves + F/E rows | detects busywork and consolidation phases |
| `question_to_evidence_lead_time` | forecast contracts + E/F rows + artifacts | maps flow without reducing work to speed |
| `high_confidence_miss_incidents` | forecast scores + catch ledger | improves calibration and adversarial discipline |

## Concrete Additions To The Intelligence Surface

Near-term additions should be read-only:

1. Add `dashboard_metric_inventory` with freshness, record count, and known caveat for every public-dashboard JSON feed.
2. Add `decision_use_gap` computed as `aggregates - decision_use_rows`, with age buckets.
3. Add `learning_candidate_lifecycle` by joining emitted candidates to later seam/spec/primitive/catch references.
4. Add `activity_yield_divergence` from trajectory curves and experiment/F-row counts.
5. Add `recurrence_suppression_candidates` by joining top catch categories to later GP-233/catch occurrences.
6. Add `metric_caveats` as first-class rows so every metric has a denominator, decision use, and failure mode.

Do not make these control gates until the read model has proven that the joins are stable.

Implementation note, 2026-05-20: GP-244 now implements these additions as an ETL-style private read model. The packet includes `etl_manifest`, `source_map`, `source_improvement_backlog`, `activity_yield`, `learning_candidate_lifecycle`, `recurrence_suppression_candidates`, and `metric_caveats`. The critical next source improvements are not downstream dashboard work: they are better decision-use rows, action-impact/surfacing-consumption rows, structured GP-233/experiment read models, and recurrence/avoidance labels in the catch source.

## Metric Design Rules

1. Every metric must name the decision it supports.
2. Every metric must carry denominator, source, freshness, and caveat.
3. Activity metrics must be paired with yield or instability metrics.
4. Forecast metrics must be paired with decision-use metrics.
5. Recursive-improvement metrics must track promotion and reuse, not just candidate creation.
6. Human bottleneck metrics must distinguish harmful waiting from valuable human judgment.
7. Any metric that has not been consumed in a decision for a set window should be retired or demoted.

## So What

ZTARE’s current apparatus is strongest at detecting negatives, catches, and trajectory changes. It is weaker at proving that those signals changed later work. The next research-ops layer should therefore optimize for **closed feedback loops**:

```text
signal emitted -> decision changed -> action taken -> outcome observed -> primitive/forecast/catch updated -> later recurrence reduced
```

That is the measurable unit of organizational learning for ZTARE.
