# GP-230 — Forecast Pool / Decision-Market Primitive Seam

> **Seam metadata** · `seam_id:` GP-230 · `track:` protocol · `status:` Open - 2026-05-12 · `last_updated:` 2026-05-14


## Status

Open — 2026-05-12

## Compression

The primitive is not "agents gambling." The primitive is:

```text
forecast -> aggregate -> resolve -> score -> update routing weights
```

Macro decisions may use market-style aggregation. Meso decisions use sealed
forecast auctions. Micro decisions use proper-scored forecasts attached to
actions. A live LMSR daemon is deferred until the file-backed contract,
resolver, and scoring surfaces are clean.

The newer articulation is:

```text
read-only price discovery -> failure-mode preconditioning -> isolated execution
-> objective resolution -> proper scoring -> calibrated routing priors
```

This is why the primitive belongs primarily in the agentic/orchestration layer,
with a reflexive sub-loop. It is agentic because it controls how LLM agents are
dispatched, separated, and scored. It is reflexive because the apparatus audits
its own decision forecasts and effort estimates, then feeds calibrated priors
back into later RD ticks.

## Eigenquestion

Can ZTARE price action risk before dispatch without turning orchestration into
bookkeeping, subjective arbitration, or agent gaming?

## Decision

Build a sealed, file-backed forecast pool first.

Do:

- create objective contracts with resolver commands / thresholds;
- collect sealed forecasts from read-only pricing agents, requiring both a
  point estimate (`p_success`, effort, decomposed risk channels) and a
  separately elicited tail-worry token (`tail_insurance_premium`, int
  1-100) that does not reduce to `1 - p_success`;
- aggregate with calibration-weighted log-odds;
- treat a high tail-worry signal on a material contract as a route to
  abstain-and-escalate (or to commission a fresh forecaster from a
  different model family that re-prices the same contract without prior-
  agent context), not as a re-scaling of the original act-threshold;
- resolve with build/test/goal/count/artifact-hash outcomes;
- score with Brier/log score, surfacing per-row second-moment channels
  alongside point-estimate Brier;
- keep domain-specific calibration weights;
- surface macro gate prices in RD ticks.

Do not yet:

- run live LMSR on every micro-action;
- let forecasters execute the action they priced;
- let builders see aggregate price during execution;
- use global wallet wealth as general epistemic authority;
- score subjective "elegance" contracts.

## Layer Contract

| Layer | Mechanism | Examples | Resolution |
|---|---|---|---|
| Macro | sealed pool now; LMSR later if needed | GNN launch, GPU spend, novelty claim, large swarm | artifact validator / fixed metric gate |
| Meso | sealed forecast auction | branch choice, candidate source, proof strategy | selected action outcome + exploration audit |
| Micro | proper-scored forecast row | tactic closes, patch compiles, lemma retrieval works | Lean/test/goal-count/runtime result |

## Failure Modes To Guard

1. **Sabotage:** pricing agents must be read-only; builders must have no stake.
2. **Beauty contest:** sealed batch forecasts; no live price tape initially.
3. **Counterfactual non-resolution:** rejected branches need occasional
   exploration audits.
4. **Capital monopoly:** use per-domain calibration weights, not global bankroll.
5. **Arbitration drift:** micro contracts must be auto-resolvable.
6. **Bookkeeping bloat:** only attach forecasts to typed commitments or batched
   micro-actions with cheap objective resolution.
7. **Cross-agent exposure → herding:** the read-only / sealed-pool discipline
   is not aesthetic. When a second forecaster can see another's prior
   forecast or rationale before pricing the same contract, its probability
   shifts toward the prior at a rate that violates the independence the
   calibration-weighted log-odds aggregator assumes. Aggregation paths
   must keep per-role forecast rows sealed from other forecasters until
   resolution.
8. **Rationale-exchange ensembles on single-shot binary contracts:** showing
   forecaster B forecaster A's prose rationale before B emits its own
   probability does not reliably improve B's Brier and frequently anchors;
   the conditions that make adversarial debate work for code or seam
   review (concrete errors, pre-resolution verification, compounding error
   propagation, kill-finder/builder/arbiter role specialization, decidable
   arbitration) do not hold for binary forecasting. Default to independent
   aggregation; introduce exchange only when the contract supplies those
   preconditions.
9. **LLM-yield-prediction for reasoning-mill scheduling:** subscription-class
   forecasters used to predict proof-search / reasoning-attempt completability
   on stratified corpora have been observed to perform worse than a
   constant-0.5 baseline across multiple families. Do not let GP-230
   schedule LeanMill or other reasoning queues by such predictions; use FIFO
   or domain heuristics until the predict-vs-execute capability is shown to
   dissociate in the agent class deployed.

## Minimal Interfaces

Primary CLI:

```text
scripts/public/control/forecast/pool.py
```

Artifacts:

```text
analytics/public/forecast_pool/contracts/*.json
analytics/public/forecast_pool/forecasts/<contract_id>/*.json
analytics/public/forecast_pool/aggregates/*.json
analytics/public/forecast_pool/outcomes/*.json
analytics/public/forecast_pool/scores/*.json
analytics/public/forecast_pool/calibration_summary.json
analytics/public/forecast_pool/status/daemon_once_latest.json
analytics/public/forecast_pool/calibration_weights.json
```

## Belief-Update Boundary

Scores are observations. Belief updates are a separate explicit reducer:

```text
scripts/public/control/forecast/pool.py calibrate --write --write-weights
```

`score` MUST NOT silently mutate weights. `calibrate` reads closed score
artifacts and writes a code-backed calibration summary plus optional
domain-specific weights/effort priors. Probability calibration and effort
calibration stay separate: Brier/log score updates reliability weights; cost
error updates expected-effort priors. Small samples use shrinkage and advisory
flags. RD agents must consult the summary before costly GP-230-priced macro or
meso dispatches, and either use the adjusted effort prior or explicitly state
why the new task is structurally different.

Do not create a standalone prediction-agent role yet. GP-230 owns calibration
mechanics, RD owns use/override in research ticks, and PM audits whether the
primitive earns its overhead. Add a role only if forecast volume becomes
cross-role, adversarial, or large enough that RD self-scoring becomes a conflict.

## Warm Forecaster Role Boundary

2026-05-14 update: forecast volume and repeated macro/meso NS decisions now
justify a narrow `forecasting_agent` role, but only as a ZTARE tenant overlay
on the general cognitive-firm A2A substrate.

General-purpose layer:

- cognitive-firm owns role-to-role A2A messages, durable inboxes, obligation
  lifecycle, artifact dependencies, and future remote adapters;
- any improvement to those mechanics belongs in the sibling `cognitive-firm`
  repo unless it is GP-230-specific.

ZTARE overlay:

- GP-230 owns contracts, forecast rows, aggregation, outcome scoring, effort
  calibration, externality audit, and research evidence packets;
- `forecasting_agent` is read-only and exists to consume GP-230 wake
  obligations, not to execute research work.

Warm reactivation should be pull-style:

```text
evidence delta -> wake event -> A2A request -> short independent-agent session
-> one forecast/no-update -> exit
```

This avoids continuously running subscription CLI sessions. The daemon may
scan and enqueue file-backed work while idle; it must not keep subscription
runtimes alive waiting for work.

Launch constraint for v0: two independent-agent adapters, currently backed by
the existing runtime identities. A larger panel is a new market decision, not a
default, because it changes both spend and independence assumptions.

Operational policy:

- preferred publisher path: `init-contract --emit-warm-wake
  --warm-emit-agent-channel`, so contract creation and wake publication are one
  artifact-backed event;
- default path: run `warm-daemon-once` after material contract/evidence changes;
- service path: run `warm-daemon-loop` at a coarse interval as a scanner only;
- subscription agents are pull consumers of `org/channels/forecasting_agent`
  through `warm-consumer-once` or a coarse `warm-consumer-loop`;
- Codex consumer launches default to `gpt-5.4-mini` through
  `ZTARE_CODEX_FORECAST_MODEL`; stronger Codex models require explicit
  RD/principal override;
- Claude consumers are disabled unless `ZTARE_ENABLE_CLAUDE_FORECASTER=1`
  after subscription auth mode is verified; insufficient-balance responses are
  blocked-runtime events, not retry loops. Claude-runtime subprocesses strip
  `ANTHROPIC_API_KEY` and related provider flags so they cannot silently fall
  back to Console/API billing;
- consumer `live` mode is the default production path: claim one message,
  launch exactly one subscription CLI process, require a forecast or explicit
  no-update, record output, and exit. `preview` is an explicit dry run that
  renders a prompt without claiming work; `stub` claims and closes a lifecycle
  test without launching a subscription runtime;
- scoring remains an explicit resolver action and is now a hard post-tick
  close condition for micro contracts; after scoring, the post-tick runner may
  enqueue a bounded calibration-reflection/no-update wake.
- belief updates are append-only and attributed to stable role identities
  (`claude_forecaster`, `codex_forecaster`); market aggregation uses each role's
  latest row, while the full update history remains auditable.
- forecasters can read the project/evidence/proof surfaces needed for pricing;
  their write surface remains limited to forecast/update rows, channel responses,
  and consumer-state artifacts.
- continuity follows the cognitive-firm daemon pattern: role inbox messages wake
  ticks; Claude can resume a durable session id across ticks; Codex uses
  artifact-backed memory until its CLI has a comparable resume adapter; neither
  runtime polls while idle.

Tech debt: `forecast_pool.py` now contains a local consumer/continuity shim so
the GP-230 path can be tested before VPS deployment. This must remain a ZTARE
tenant overlay, not a fork of cognitive-firm. Production migration should run
`forecasting_agent` as a cognitive-firm role-bound daemon worker, with GP-230
kept as the market-specific publisher/tooling layer. Concrete migration steps:
delegate session continuity to cognitive-firm, keep the role inbox as the queue,
map GP-230 wake metadata into cognitive-firm task claims, preserve the
read-broad/write-narrow forecast role policy, and only then add a VPS supervisor
unit.

## Transport Boundary: Pub/Sub Without Live-Market Drift

2026-05-19 update: if a forecast agent is running on the VPS, the architecture
is good enough for sealed micro/meso use only if the file-backed role channel is
treated as a durable event bus with explicit publish, claim, response, expiry,
and aggregate-ready semantics. The market should not transition to live LMSR or
continuous price tape merely because the transport became asynchronous.

## Classification: Reflexive Primitive 9, Agentic Transport

Per `docs/concepts/primitive_classification_criteria.md`, GP-230 is best
classified as **Reflexive Primitive 9: Reflexive Forecast Market** with
**agentic engineering subcomponents**.

Why reflexive: the apparatus applies adversarial disagreement, compression, and
calibration inward to its own research allocation decisions. The priced object
is not an external substrate alone; it is the engine's own next action, effort,
failure mode, and branch choice.

Why not merely agentic: the role inbox, warm-consumer, ordering guard, score
closure, and transport-health checks are agentic plumbing. They make the
reflexive market enforceable, but the core move is the apparatus using its own
forecast/evidence/scoring discipline to govern itself.

This is not a mutually exclusive classification. GP-230 intentionally has both
a public AEP entry for the reusable sealed-forecast-pool infrastructure and a
REP entry for the inward ZTARE self-application.

Recommended architecture:

```text
contract.created / evidence.changed
-> GP-230 publisher writes wake event + role-inbox message
-> forecasting_agent atomically claims one message
-> writes forecast or NO_UPDATE
-> aggregator writes aggregate.ready
-> RD pre-tick consumes aggregate/status, not raw forecaster chatter
-> resolver/score closes the calibration loop
```

This is a pub/sub-style event pipeline, not a live market. Use it to remove
polling ambiguity and VPS/local skew; keep the economic primitive sealed,
proper-scored, and artifact-backed.

Rules:

- Micro contracts may use short-deadline asynchronous wakes, but RD pre-tick
  must proceed only after either `min_forecasts` is met or a recorded timeout /
  no-update policy fires.
- Meso contracts should require an aggregate-ready artifact before branch
  choice unless an explicit principal/RD override records why forecast latency
  would dominate value.
- Macro contracts should stay sealed-panel and audit-heavy; use the event bus
  for notification and traceability, not for real-time price discovery.
- Research directors consume the aggregate/status artifact in pre-tick. They
  should not hand-read live channel chatter as if it were resolved market
  evidence.
- The transport layer must expose stale-open claims, expired wakes, blocked
  runtimes, missing aggregate, and resolved-unscored contracts in one health
  report.
- Single-writer authority remains the membrane/VPS official store. Local
  laptop runs are observers/proposers, never authoritative market state.

## DAG / Void Use In Forecasting

Autoresearch probability DAGs and graph-basin outputs are useful as evidence,
not as a required market engine. Warm events may attach:

```text
projects/<slug>/latest_probability_dag.json
projects/<slug>/champion_probability_dag.json
projects/ns_millennium_hunt/workspace/queries/ns_graph_unified_intelligence.jsonl
analytics/public/queries/neural_hunt/neural_hunt_basin_graph.json
```

Forecasters should use these artifacts to decompose premise risk, identify the
weakest dependency, and name what the graph misses. The void matters as much as
the nodes: missing observables, unpriced residuals, hidden coupling, stale
evidence, or absent negative cases should flow into existing GP-230 fields
(`failure_mode_distribution`, `specific_failure_mode_ids`,
`action_change_recommendation`, externality tags). Do not run a fresh
autoresearch DAG generator for every forecast unless the contract itself is a
forecast-DAG experiment.

## Positive Externality: Failure-Mode Preconditioning

The forecast pool has a second value channel besides calibration. Forecast
rationales can name the failure mode the executor must avoid. This is not a
substitute for Brier/log scoring; it is a separate execution-control artifact.

Example: on 2026-05-14, two read-only NS forecasters priced a route-1 Lean
split at aggregate `p_success=0.771` and independently identified the same
trap: the proposed carrier-identification station could become a cosmetic
rename of `l2Carrier_identifies_totalAngularMoment`, or could replace the
needed equality with weak Prop labels. The executor then carried the equality
explicitly while splitting recovered pressure-Hessian projection,
Riesz/angular matching, normalization, and anti-tautology guards around it.
The useful output was the pre-execution constraint, not only the later score.

Resolver rule: when a forecast rationale materially changes execution, record
that fact separately from probability calibration, e.g.
`failure_mode_preconditioner_used: true`, with a pointer to the diff or outcome
artifact that shows the trap was actually handled. Generic risks such as "may
fail to compile" do not count.

### 2026-05-14 externality panel result

Two-agent panel review plus a local artifact audit found that GP-230 already
measures ordinary calibration well enough for RD use, but not externality value
well enough for meta-learning. The audit covered `134` contracts, `272`
forecasts, `124` outcomes, and `246` score rows. It found:

- mean Brier `0.1929`, Brier skill `0.2285` versus uniform binary baseline;
- median expected/actual effort ratio `1.8197`;
- `148` GP-233 rows with forecast/market/calibration references;
- positive externalities mostly in prose rather than machine fields;
- negative signals: hedge-band forecasts, high-entropy failure-mode
  distributions, unresolved contracts, and forecast-drag cases.

Conclusion: GP-230 should preserve normal Brier/log/effort scoring, but add a
separate structured externality channel. A forecast can be numerically wrong or
pessimistic and still valuable if it changes execution by naming a concrete
failure mode. That value must not be blended into calibration.

Artifacts:

```text
analytics/public/forecast_pool/forecast_pool_externalities_audit_20260514.json
analytics/public/forecast_pool/forecast_pool_externalities_review_20260514.md
scripts/public/analytics_shared/audit_forecast_pool_externalities.py
```

Optional externality fields now belong on the file-backed contract surface:

- contract: `baseline_action`, `counterfactual_action`,
  `externality_hypotheses`;
- forecast: `specific_failure_mode_ids`, `action_change_recommendation`,
  `forecast_externality_tags`;
- outcome: `realized_failure_mode_ids`,
  `failure_mode_preconditioner_used`, `preconditioner_source`,
  `preconditioner_effect`, `decision_changed_bool`, `old_next_action`,
  `new_next_action`, `externality_tags`, `negative_externality_tags`,
  `counterfactual_value_bucket`, `changed_by_forecast_ids`.

Externality audit rule: score the forecast normally, then separately report
specific failure-mode hit rate, realized failure-mode probability mass,
decision-change coverage, positive preconditioner usage, negative externality
tags, and forecast drag. Do not award externality credit for generic risk lists.

Positioning relative to prior art: prediction markets, proper scoring rules,
and software-project forecasting are established. GP-230's narrower claim is a
specific orchestration composition: sealed read-only agent forecasts, execution
isolation, artifact-backed resolution, macro/meso/micro routing, effort
calibration in agent-minutes, and failure-mode preconditioning. Treat novelty
claims conservatively until a deeper literature pass is done, but this exact
combination is not the standard LMSR/project-forecasting setup.

### 2026-05-13 panel-mediated boundary

Panel participants converged on a hybrid boundary:

- GP-230 owns the machine loop: contract, sealed forecasts, aggregation,
  outcome, score, explicit calibration reducer, and advisory routing weights.
- RD owns scientific use: when the forecast is worth the overhead, whether the
  calibrated effort prior applies, and any override rationale.
- PM audits overhead and decision impact once enough scorecards exist.
- No standalone prediction-agent role exists in v1; reconsider only if forecast
  volume becomes cross-role, adversarial, or conflict-prone.

The same panel flagged overuse risk during GP-225: forecasting every
saved-artifact taxonomy creates bookkeeping drag. Use GP-230 for replay/Lean
batches, GNN/GPU/training gates, public claims, large swarms, and branch choices
with real opportunity cost. Use PATTERN-012 plus GP-233 inline yield fields for
cheap saved audits and taxonomies. Calibration priors inform effort estimates;
they do not block cheap discriminators or override objective gates.

First daemon step:

```text
scripts/public/control/forecast/pool.py daemon-once --write
```

This is a read-only scan over forecast-pool contracts and the public prediction
ledger. It writes a status artifact with per-contract next actions and recent
unresolved PL rows; it does not dispatch forecasters, resolve outcomes, or score
contracts.

RD tick integration should show:

- open macro contracts;
- contracts with enough forecasts but no aggregate;
- resolved contracts lacking scores;
- aggregate routing hints for GNN/GPU/public-claim gates.

### 2026-05-19 ZTARE market-utilization audit

Principal-side reflexive audit, not an RD tick: the forecast pool is producing
real value, but it is not yet maximizing the decision-market idea. The current
state is a useful scored forecast pool with partial market behavior, not a full
price-discovery instrument.

Snapshot from `scripts/public/analytics_shared/audit_forecast_pool_externalities.py`
plus the local market-utilization probe that has now been folded into the
audit requirements:

- coverage: `338` contracts, `640` forecasts, `333` outcomes, `281`
  aggregates, `473` score rows;
- calibration: mean Brier `0.1626`, skill `0.3495` versus uniform binary
  baseline;
- `ns_route1_pde`: `168` scored rows, mean Brier `0.1543`, skill `0.383`;
- preconditioning exists: `79` outcomes record
  `failure_mode_preconditioner_used`, `126` record decision-change status, and
  `80` record realized failure-mode IDs;
- structured failure-mode scoring is promising where available: top-1 hit
  rate `0.4615`, specific-ID hit rate `0.4336`, realized-mode probability mass
  `0.2683`.

Observed gaps:

- no current forecast-update artifacts: price movement after new evidence is
  essentially unused;
- post-2026-05-15 identity hygiene still has noncanonical `agent_id` rows,
  weakening calibration-weight routing;
- failure-mode distributions are often too diffuse to precondition execution:
  high entropy should warn unless paired with `specific_failure_mode_ids` or
  `action_change_recommendation`;
- effort estimates still overprice agent work: median expected/actual ratio
  `1.5`, mean `2.3536`, with many 3x+ overestimates;
- resolved-but-unscored contracts remain the highest-leverage hygiene gap;
- transport debt is visible: `12` open forecasting-agent inbox messages point
  at already-resolved contracts, and `28` fulfilled messages are missing
  aggregate artifacts;
- raw prediction-ledger rows are not equivalent to forecast-pool evidence
  unless their resolved/scored coverage is reported separately.

Seam update: the externality audit is now also the market-utilization audit. It
must report not only "were forecasts calibrated?" but also:

- market depth: forecast-count bins, single-forecaster contracts, p-success
  spread across forecasters;
- identity hygiene: post-binding noncanonical `agent_id` rows and alias counts;
- domain hygiene: domain alias families that fragment calibration;
- belief-update usage: count and recency of forecast update files;
- failure-mode quality: normalized entropy, `other` mass, and specific-ID
  coverage;
- causal externality capture: `changed_by_forecast_ids`,
  `counterfactual_value_bucket`, old/new action fields, and decision-change
  coverage;
- calibration debt: resolved outcomes lacking score rows;
- raw-ledger caveat: prediction-ledger resolved/scored coverage separate from
  GP-230 forecast-pool scoring.

2026-05-19 implementation update: `forecast_pool.py materialize-state` now
writes `analytics/public/forecast_pool/market_state/reflexive_insights.json`.
This generated read model turns positive externalities, calibration incidents,
decision-use gaps, effective-independence gaps, forecast-update absence, score
debt, and transport debt into a small pre-tick nudge surface. It also writes
`market_state/maintenance_plan.json` as a generated hygiene queue. The RD
consumes those surfaces; the RD does not need to author a separate meta-analysis
to discover the same reflexive lessons.

2026-05-20 scratch update: the pool has an explicit scratch layer for macro,
meso, and micro orientation bets. Scratch rows remain uncertified and excluded
from GP-230 calibration, but RD-like owners mirror to the local prediction
ledger by default with numeric tiers so calibration debt is not hidden behind
"informal" language. Forecaster aliases stay forecast-pool-only unless
explicitly mirrored. `record-decision-use` and `status` now treat scratch ids as
scratch-only artifacts: they can expose latest decision-use and action-change
rows, but they do not fabricate aggregate/outcome/score semantics and do not
make scratch usable for membrane close.

Do not promote to live LMSR/AMM until this read-only audit is clean enough to
show that the sealed pool reliably changes decisions, names realized traps, and
closes its own scoring debt.

## Promotion Gate

Promote from seam/spec to org primitive only if the pilot shows:

- at least `3` macro/meso contracts resolved;
- all contracts resolve without manual settlement;
- added overhead is below `15` agent-minutes per contract;
- at least one aggregate forecast changes or sharpens an RD decision;
- no forecast agent has write access to the outcome it priced.

## Kill / Defer Condition

If the primitive produces mainly stale forecasts, subjective disputes, or
additional latency without changing decisions, keep PATTERN-012 prediction
ledger plus occasional concurring forecasts and do not build a daemon/LMSR.

