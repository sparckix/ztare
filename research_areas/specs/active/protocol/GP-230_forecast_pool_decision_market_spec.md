# GP-230 Forecast Pool / Decision-Market Primitive Spec

## Status

Active — opened 2026-05-12

## Seam

`research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`

## Scope

This spec governs a forecast-pool primitive for ZTARE orchestration:

- macro decision pricing;
- meso branch auctions;
- micro proper-scored action forecasts;
- objective contract resolution;
- calibration-weighted aggregation;
- scoring and future routing weights;
- RD tick surfacing.

Out of scope:

- live LMSR/AMM exchange as the first implementation;
- subjective research-taste contracts;
- granting forecasters write access to outcomes;
- replacing PATTERN-012 prediction ledger.

## Eigenquestion

Can a sealed forecast pool improve research allocation decisions before
dispatch while remaining cheaper than the compute/operator attention it saves?

## Architecture

The universal loop is:

```text
contract -> sealed forecasts -> aggregate -> execute -> resolve -> score -> update weights
```

The decision-control loop is:

```text
read-only price discovery -> failure-mode preconditioning -> isolated execution
-> objective artifact resolution -> proper scoring -> calibrated routing priors
```

Layer interpretation:

- `macro`: decision pricing, file-backed forecast pool now; live LMSR only after
  promotion gates pass;
- `meso`: sealed batch auctions over branch or strategy choices;
- `micro`: proper-scored forecasts attached to typed actions.

This layer split may become an execution-scheduler substrate for adversarial
formal theorem proving, where macro markets price proof-search budget, meso
auctions choose strategy branches, and micro forecasts price individual proof
tactics or patches. That is a future promotion path, not a claim of current
capability. The current primitive remains a conservative scored forecast pool:
read-only pricing agents, isolated execution agents, objective auto-resolution,
and artifact-backed scoring only.

### Pattern Classification

GP-230 is primarily an agentic/orchestration engineering pattern. It governs
how LLM agents price, route, execute, and resolve work. It contains a reflexive
sub-loop because calibration artifacts feed back into later routing priors and
effort estimates.

Classification criteria:

- `agentic_engineering`: repeatable engineering discipline for LLM-mediated
  workflows: dispatch separation, objective resolution, telemetry, contract
  enforcement, or scoring.
- `reflexive_engineering`: ZTARE applies its own epistemic principles to its
  infrastructure: auditing forecast quality, compressing decision history, or
  calibrating the agent's own effort estimates.
- `orchestration_pattern`: action selection or coordination layer, without
  asserting a substrate theorem or scientific result.

Under these criteria, GP-230 is:

- `agentic_engineering`: yes, because it separates forecasters from executors
  and makes forecasts machine-resolvable;
- `orchestration_pattern`: yes, because it routes macro/meso/micro action
  choices;
- `reflexive_engineering`: partial, because scoring/calibration reducers audit
  the decision apparatus's prior forecasts.

### Contract

Required fields:

- `contract_id`
- `layer`: `macro | meso | micro`
- `task_type`
- `question`
- `objective_resolver`
- `success_threshold`
- `horizon`
- `budget_agent_minutes`
- `value_if_success`
- `cost_penalty`
- `risk_penalty`
- `information_value`
- `void_conditions`
- `execution_layer_policy`

Optional externality fields:

- `baseline_action`
- `counterfactual_action`
- `externality_hypotheses`

### Forecast

Required fields:

- `agent_id` — see **Agent ID Naming Convention** below
- `domain`
- `p_success`
- `expected_cost_agent_minutes`
- `p_regression`
- `p_dependency_issue`
- `p_needs_new_lemma`
- `failure_mode_distribution`
- `rationale_short`
- `read_only_attestation`

Probabilities are clipped to `[0.02, 0.98]`.

### Agent ID Naming Convention (binding, 2026-05-15; transport aliases updated 2026-05-19)

Canonical forecast families are:

- `claude` — generic Claude runtime forecaster (no specific role)
- `codex` — generic Codex runtime forecaster (no specific role)
- `claude_rd` — Claude research-director forecaster
- `codex_rd` — Codex research-director forecaster

The `forecasting_agent` transport may still emit persistent role aliases such
as `claude_forecaster` and `codex_forecaster`. Readers, ordering guards, and
audits canonicalize those aliases to the corresponding independent-agent family
while preserving the raw string in provenance. New hand-authored RD forecasts
should use the canonical family IDs; role-consumer artifacts may use the
role-stable aliases until a deliberate migration is run.

**Forbidden patterns** (each is an anti-pattern caught in 2026-05-15
session):

- Custom aliases (`meta_darwin_proxy`, `forecaster_alice`, etc.) — use
  `claude_rd` or `codex_rd` instead. Adversarial-vs-default role lives
  in the `domain` field, NOT in `agent_id`.
- Mislabeling a Claude-runtime dispatch as `codex_rd` (or vice versa).
  The `agent_id` MUST match the actual runtime that produced the
  forecast. If the dispatch was via `Agent` tool / Claude general-purpose
  subagent → `agent_id = claude_rd`. If via `codex exec` /
  `forecast_pool warm-consumer-once --runtime codex` → `agent_id = codex_rd`.
- Verbose ex-post relabels (e.g., `claude_rd_mislabeled_ex_post_*`) —
  use the canonical four IDs above and let provenance audit logs
  carry the correction history.

**Legacy correction rule:** new hand-authored forecast writes should use one
of the canonical IDs, while the `forecasting_agent` role aliases remain
accepted compatibility inputs. Older rows may remain on disk as historical
artifacts. Readers and audits should report a read-time canonicalization/alias
view plus the raw string, rather than silently rewriting history. A bulk rewrite
is allowed only as an explicit migration with backup files and a provenance
note.

Optional externality fields:

- `specific_failure_mode_ids`
- `action_change_recommendation`
- `forecast_externality_tags`

If `failure_mode_distribution` is high-entropy, a forecast is weak as a
preconditioner unless it also supplies `specific_failure_mode_ids` or an
`action_change_recommendation`. High-entropy risk lists still count for
calibration but should not be treated as strong execution guidance.

### Aggregate

Initial aggregation:

- success probability: calibration-weighted log-odds average;
- cost/risk: calibration-weighted arithmetic average;
- routing hint from expected value:

```text
EV = p_success * value_if_success
     - cost_penalty * expected_cost
     - risk_penalty * p_regression
     + information_value
```

### Outcome

Objective resolver fields:

- `success_bool`
- `actual_cost_agent_minutes`
- `compile_status`
- `sorry_delta`
- `goal_delta`
- `error_type`
- `artifact_hash`
- `artifact_path`
- `voided`

Optional externality resolver fields:

- `realized_failure_mode_ids`
- `failure_mode_preconditioner_used`
- `preconditioner_source`
- `preconditioner_effect`
- `decision_changed_bool`
- `old_next_action`
- `new_next_action`
- `externality_tags`
- `negative_externality_tags`
- `counterfactual_value_bucket`
- `changed_by_forecast_ids`

For new `macro` and `meso` contracts that can change route choice,
`baseline_action`, `counterfactual_action`, and `externality_hypotheses` are
required in practice even though legacy artifacts remain valid. If an outcome
sets `decision_changed_bool=true` or
`failure_mode_preconditioner_used=true`, it should also name
`changed_by_forecast_ids` and `counterfactual_value_bucket` unless the resolver
explicitly states why attribution is unavailable.

### Score

Binary success forecasts use:

- Brier score;
- log score.

Cost estimates record absolute error in agent-minutes. Calibration weights are
domain-specific; global bankroll authority is explicitly disallowed.

Externality scoring is separate from calibration. Score artifacts SHOULD report:

- whether structured realized failure modes were available;
- top-1 failure-mode hit against `realized_failure_mode_ids`;
- probability mass assigned to realized failure modes;
- whether forecast-level `specific_failure_mode_ids` hit;
- presence of counterfactual fields and decision-change fields.

These fields never improve Brier/log score. They measure whether a forecast
changed execution or named a realized trap.

### Calibration / Belief Update

Score artifacts are immutable observations. Belief updates occur only through an
explicit reducer:

```text
./venv/bin/python scripts/public/control/forecast/pool.py calibrate --write --write-weights
```

The reducer reads `analytics/public/forecast_pool/scores/*.json` and writes:

- `analytics/public/forecast_pool/calibration_summary.json`
- `analytics/public/forecast_pool/calibration_weights.json` when
  `--write-weights` is passed

Required semantics:

- `score` does not silently mutate calibration state;
- probability calibration and effort calibration are separate;
- Brier/log score may adjust domain-specific reliability weights;
- cost error may adjust domain effort priors;
- small-N samples are flagged and shrinkage-bounded;
- effort priors are advisory, not vetoes;
- RD ticks consume the summary and may override it only by naming the structural
  difference from prior contracts.

No standalone prediction-agent role is required for v1. GP-230 owns mechanics;
RD owns use/override; PM audits overhead and decision impact. Reconsider a
dedicated role only after forecast volume is cross-role/adversarial enough that
RD self-scoring creates a conflict.

Panel-mediated policy from 2026-05-13:

- do not use GP-230 as a hard stop for cheap saved-artifact diagnostics;
- use GP-230 for replay/Lean batches, GNN/GPU/training gates, public claims,
  large swarms, or branch choices with real opportunity cost;
- use PATTERN-012 raw prediction rows plus GP-233 research-yield decomposition
  for cheap saved audits/taxonomies;
- the status/daemon surface MUST expose stale calibration state and concise
  domain effort priors so RD can learn from repeated effort overestimation
  without opening raw score files;
- probability calibration and effort calibration remain separate: effort
  overestimation changes expected-cost priors, not success probability.

### Warm Forecaster A2A Reactivation

The warm forecaster architecture is subscription-safe and tenant-overlaid:

- the general-purpose role messaging substrate is cognitive-firm A2A;
- this ZTARE overlay owns GP-230 contracts, forecast semantics, role/mandate
  scope, and research evidence paths;
- the daemon creates durable wake artifacts and A2A requests, but does not keep
  Claude or Codex sessions alive.

Warm forecaster flow:

```text
contract/evidence delta
-> warm-daemon-once
-> wake event with stable wake_key
-> cognitive-firm A2A request to forecasting_agent
-> short independent-agent subscription session
-> one forecast or no-update response
-> exit
```

Implementation surface:

```text
./venv/bin/python scripts/public/control/forecast/pool.py warm-daemon-once \
  --contract-id <id> \
  --forecasters claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent \
  --write \
  --emit-agent-channel
```

For new contracts, the preferred publisher path is to emit the wake in the
same command that creates the contract:

```text
./venv/bin/python scripts/public/control/forecast/pool.py init-contract ... \
  --emit-warm-wake \
  --warm-emit-agent-channel
```

This is the file-backed pub/sub boundary. `init-contract --emit-warm-wake`
publishes wake events and optional A2A messages immediately after the contract
artifact is written. It still must not launch a subscription runtime, score,
resolve, or consume the message.

The pub/sub boundary is transport, not market semantics. GP-230 remains a
sealed forecast pool: contracts are objective, forecasts are append-only,
aggregation is artifact-backed, and outcomes are scored after resolution. Do
not infer live price discovery, LMSR/AMM behavior, or continuous trader state
from the presence of a VPS forecaster or role inbox.

Required event states for production use:

- `contract_created`: contract artifact exists and, if relevant, a wake event
  was published;
- `forecast_requested`: role-inbox message exists with `contract_id`,
  `wake_key`, runtime, agent id, and evidence fingerprint;
- `forecast_claimed`: exactly one consumer has atomically claimed the message;
- `forecast_fulfilled`: consumer wrote a forecast row, belief update, or
  explicit `NO_UPDATE`;
- `forecast_expired`: contract resolved or timeout elapsed before fulfillment;
- `aggregate_ready`: aggregate artifact exists and names participant forecasts;
- `pre_tick_consumed`: RD pre-tick consumed the aggregate/status artifact or
  recorded an override;
- `resolved_scored`: outcome and score artifacts both exist.

RD pre-tick behavior must consume `aggregate_ready` or a status artifact that
states why it is unavailable. It should not consume raw channel chatter as a
substitute for market evidence.

### Materialized Read Models and RD Fast Path

The forecast market MUST maintain raw append/artifact stores and a compact
read model. RDs and membrane nudges should read the compact model first, then
open raw artifacts only when the compact state names a live obligation.

Canonical generated artifacts:

```text
analytics/public/forecast_pool/market_state/global_health.json
analytics/public/forecast_pool/market_state/calibration_by_agent.json
analytics/public/forecast_pool/market_state/reliability.json
analytics/public/forecast_pool/market_state/reflexive_insights.json
analytics/public/forecast_pool/market_state/maintenance_plan.json
analytics/public/forecast_pool/market_state/contracts/<contract_id>.json
analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl
```

Refresh command:

```text
./venv/bin/python scripts/public/control/forecast/pool.py materialize-state
./venv/bin/python scripts/public/control/forecast/pool.py materialize-state \
  --contract-id <contract_id>
```

`materialize-state` derives lifecycle state from the canonical artifacts and
surfaces malformed contracts / malformed forecasts as explicit obligations
rather than aborting RD orientation. Contract read models carry:

- compact contract metadata and artifact paths;
- lifecycle state, next action, missing obligations, and whether the state
  blocks post-tick close;
- latest forecasts and participant summaries;
- aggregate `p_success`, expected effort, routing hint, and top failure modes;
- effective independence lower bound for the latest forecast set;
- outcome and score summary;
- latest decision-use row;
- `rd_fast_read`, the small object an RD should consume before scientific work.

`market_state/reliability.json` carries the calibration surfaces that make the
market auditable as a research allocator, not only as a Brier-score log:

- probability reliability buckets with empirical success rate and calibration
  gap;
- effort predicted-vs-actual reliability, including large over/underestimate
  counts;
- failure-mode precision and realized-probability-mass recall proxy;
- per-agent and per-domain drift over recent vs prior scored rows;
- high-confidence miss incident rows for postmortem and weight updates.

`market_state/reflexive_insights.json` is generated by the market itself. It
turns scored forecasts, externality fields, decision-use coverage, calibration
incidents, effective-independence gaps, forecast-update absence, and transport
debt into a short list of reflexive nudges. RDs should consume this artifact
through the pre-tick brief or membrane read model instead of writing separate
meta-analysis to discover the same issues.

`market_state/maintenance_plan.json` is also generated by `materialize-state`.
It lists score debt, aggregate debt, resolved-without-forecast contracts, and
decision-use coverage in command-oriented form. This is a hygiene queue, not a
research task list.

Current lifecycle states:

- `malformed`: contract JSON must be repaired;
- `malformed_forecast`: forecast JSON must be repaired or quarantined;
- `forecast_requested`: contract exists but usable forecasts are absent;
- `forecast_fulfilled`: usable forecasts exist but aggregate is absent;
- `aggregate_ready`: aggregate exists and objective outcome is still pending;
- `resolved_without_forecasts`: outcome exists but no usable pre-resolution
  forecasts exist; post-tick close is blocked unless explicitly voided /
  backfilled under the ordering override discipline;
- `resolved_unscored`: outcome exists but score artifact is absent; post-tick
  close is blocked;
- `resolved_scored`: outcome and score artifacts exist;
- `voided`: outcome declares voided and does not enter calibration.

The contract read model also carries an `allocation_recommendation` in
`rd_fast_read`. Allowed recommendations are:

- `run_now`;
- `split_contract`;
- `ask_another_independent_agent`;
- `defer`;
- `kill_branch`.

The recommendation is a market-routing hint, not execution authority. It uses
aggregate expected value, probability, information value, cross-forecaster
spread, and top failure-mode concentration to turn forecasts into a small
research-allocation action.

Mutation commands that create contracts, forecasts, aggregates, outcomes, or
scores refresh the relevant read model best-effort. `warm-daemon-once` and
`warm-consumer-once` also refresh the global model after channel changes.
If a read model is missing or stale, RD tooling should run `materialize-state`
rather than reconstructing state from raw ledgers.

### Decision-Use Ledger

Forecasts are only reflexive when they can be shown to have affected the
apparatus before or during execution. Every RD/membrane use of a GP-230
aggregate SHOULD write one decision-use row:

```text
./venv/bin/python scripts/public/control/forecast/pool.py record-decision-use \
  --contract-id <contract_id> \
  --tick-id <tick_id> \
  --owner <rd_owner> \
  --decision-stage pretick \
  --used-for run \
  --decision-changed-bool \
  --failure-modes-adopted-json '["mode_a","mode_b"]' \
  --notes "forecast confirmed branch, guarded mode_a"
```

Allowed `--used-for` values:

- `run`: forecast supported the planned action;
- `split`: forecast caused a decomposition/split before execution;
- `defer`: forecast caused the action to be delayed;
- `kill`: forecast caused the action to be abandoned;
- `ask_more`: forecast caused another independent forecast/evidence request;
- `ignore`: forecast was intentionally ignored;
- `override`: forecast was overridden by RD/principal judgment.

`ignore` and `override` require `--ignored-forecast-reason`. Recording a
decision-use row normally requires an aggregate; `--allow-missing-aggregate`
is permitted only with an explicit ignored/override reason. This keeps the
pre-step fast: the RD reads `rd_fast_read`, records one use row, and then moves
to scientific work.

The sanctioned action-boundary wrapper `scripts/public/control/start_tick.py`
auto-records a decision-use row after a successful start when the referenced
forecast contract already has an aggregate. This turns decision-use capture
into infrastructure: the RD should not need to remember a separate meta-ledger
step for ordinary tick starts. If no aggregate exists, the wrapper leaves the
gap to the generated read models instead of fabricating use.

For local or VPS service testing, use the bounded polling wrapper:

```text
./venv/bin/python scripts/public/control/forecast/pool.py warm-daemon-loop \
  --forecasters claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent \
  --interval-seconds 300 \
  --max-iterations 12 \
  --write \
  --emit-agent-channel
```

The loop is a scanner only. It launches no LLM runtime; it repeatedly calls the
same deduped wake-event producer. A production service should run the loop
under the VPS process supervisor with a finite interval and log file, while the
independent-agent subscription sessions remain separate pull consumers of
`org/channels/forecasting_agent/inbox/`.

Micro / meso / macro policy:

- micro: allow short-deadline asynchronous forecast wakes; proceed after
  `min_forecasts` or an explicit timeout/no-update status;
- meso: require `aggregate_ready` before branch choice unless an RD/principal
  override records why latency costs more than the missing forecast signal;
- macro: keep sealed panels and audit-heavy evidence packets; use pub/sub for
  traceability and notification, not live price movement.

Scratch forecast policy (2026-05-20):

- `scratch-forecast` may be used at macro, meso, or micro grain for
  uncertified orientation and self-bets. It is not a GP-230 contract, cannot
  satisfy membrane close, and is excluded from forecast-pool calibration.
- RD-like scratch owners mirror to PATTERN-012 by default with numeric tiers:
  branch/program gating scratch rows are Tier 1; ordinary micro/status smokes
  are Tier 2 unless explicitly escalated by the action they gate. Forecaster
  role aliases do not mirror by default.
- `record-decision-use` and `status` must support scratch ids as scratch-only
  artifacts. They may show decision-use coverage and latest action change, but
  must not fabricate aggregate/outcome/score semantics or call scratch rows
  certified market evidence.
- If a scratch decision becomes consequential enough to close a tick or settle
  a public claim, open a real GP-230 contract or record the decision through the
  membrane path; do not promote the scratch artifact after the fact.

The local pull-consumer surface is:

```text
./venv/bin/python scripts/public/control/forecast/pool.py warm-consumer-once \
  --runtime codex \
  --agent-id codex_forecaster

./venv/bin/python scripts/public/control/forecast/pool.py warm-consumer-once \
  --runtime claude \
  --agent-id claude_forecaster
```

Consumer modes:

- `live` (default): atomically claim one message, run the configured
  subscription CLI once, require either a new forecast row or an explicit
  `NO_UPDATE`, write stdout / stderr to `consumer_state/outputs/`, and
  terminate;
- `preview`: render the exact prompt and command preview without claiming the
  A2A obligation or launching a subscription runtime. This is a dry run, not an
  operational consumer result;
- `stub`: atomically claim one message, mark it in progress, write a response
  artifact, and close it without launching a subscription runtime. This is for local
  lifecycle regression checks only.

`warm-consumer-loop` is allowed only as a coarse pull loop around one-shot
consumer invocations. It must not keep an LLM process resident. If no message
is available, the loop sleeps without spending subscription runtime.

Continuity policy follows the cognitive-firm daemon model rather than fresh
stateless workers:

- forecaster identity remains role-stable (`claude_forecaster`,
  `codex_forecaster`);
- Claude consumers use a durable session id with `--session-id` on first use and
  `--resume` on later wake ticks, rotating by age/tick count;
- Codex currently has no equivalent resume adapter in this CLI surface, so its
  durable memory is artifact-backed: prior forecasts, scores, calibration,
  GP-233, wake prompts, and channel responses;
- no LLM process stays alive while idle. Persistence is session/artifact
  continuity across event-driven ticks, not resident polling.

Tech debt and migration target:

The local GP-230 consumer intentionally mirrors cognitive-firm daemon behavior
for fast local validation. This is acceptable as a tenant overlay, but should
not fork into a second general-purpose daemon. The clean production target is a
`forecasting_agent` role launched by cognitive-firm's daemon machinery with the
GP-230 contract/forecast CLI as its task-specific tool surface.

Migration steps:

1. Keep GP-230-specific contract, forecast, aggregate, score, and calibration
   logic in `scripts/public/control/forecast/pool.py`.
2. Move or replace duplicated runtime continuity (`runtime_sessions`,
   `--session-id` / `--resume`, tick count / age rotation) with cognitive-firm's
   daemon continuity primitive.
3. Treat `org/channels/forecasting_agent/inbox/` as the canonical queue; the
   forecast pool may publish messages, but cognitive-firm should own claim /
   retry / lifecycle policy for role workers.
4. Preserve the subscription-safety invariant: role daemon ticks may resume
   runtime, but no subscription process remains resident while idle.
5. Preserve ZTARE tenant restrictions: forecasters can read evidence broadly and
   write only forecast/update/channel/consumer artifacts; they cannot resolve,
   score, mutate proof/code, or execute the priced work.
6. Add a VPS supervisor unit only after local `preview`, `stub`, and one bounded
   `live` tick pass for both configured forecasters or for the available
   runtime plus an explicit unavailable-runtime note.

Required semantics:

- `warm-daemon-once` never launches an LLM runtime;
- Independent-agent runtimes start only after a wake exists and terminate after
  one forecast or explicit no-update response;
- Codex forecast consumers default to the cheap configured model
  `gpt-5.4-mini` through `ZTARE_CODEX_FORECAST_MODEL`; stronger Codex models
  require an explicit RD/principal override for that tick;
- Claude consumers are disabled unless `ZTARE_ENABLE_CLAUDE_FORECASTER=1`
  after subscription auth mode is verified. An insufficient-balance CLI response
  is a blocked-runtime event, not a retry loop. Claude-runtime subprocesses
  strip `ANTHROPIC_API_KEY` and related provider flags so they cannot silently
  fall back to Console/API billing;
- v0 launch pool is capped at two independent-agent adapters.
  Adding more independent agents requires a separate GP-230 contract because it
  changes subscription spend and cross-agent anchoring risk;
- wake dedup uses `wake_key = hash(contract_id, agent_id, reason,
  evidence_fingerprint)`;
- reactivation is evidence-driven, not idle polling;
- rescoring is explicit: when a contract resolves, run `score`, refresh
  calibration when needed, and require the post-tick manifest to see the score
  artifact before close. The post-tick runner may then enqueue one
  calibration-reflection/no-update wake per independent agent/evidence
  fingerprint. Independent agents do not score their own markets, and
  closed-contract reflection wakes MUST NOT create new forecast rows or
  belief-update rows;
- prior forecasts, scores, calibration summaries, and GP-233 rows provide
  persistent belief memory;
- belief updates are timestamped artifacts under `forecast_updates/`; aggregation
  and scoring use the latest forecast per stable `agent_id`, while history
  remains available for calibration, positive/negative externality analysis, and
  forecast-postmortem audits;
- `actual_cost_agent_minutes` defaults to wall-clock minutes from contract
  creation to resolution unless the outcome note explicitly declares a different
  basis such as active operator time or summed parallel agent-minutes. Forecast
  calibration should not mix effort bases silently;
- forecaster identity is role-stable rather than session-stable:
  `claude_forecaster` and `codex_forecaster` are persistent market
  participants backed by artifacts, not claims about continuity of an LLM
  session;
- forecasters may read project files, seams/specs, evidence ledgers, proof
  surfaces, and referenced artifacts needed for pricing; write authority remains
  narrow: forecast rows, forecast updates, channel responses, and local consumer
  state only. They cannot mutate contracts, outcomes, scores, calibration
  weights, source code, experiment harnesses, or proof artifacts;
- A2A messages are obligations for response, not execution authority.

Envelope discipline follows the useful subset of public event/task standards:

- CloudEvents-style fields: `id`, `source`, `type`, `subject`, `created_at`,
  `schema_version`;
- cognitive-firm A2A role inbox: `request`, `expects_response`, artifacts,
  references, causality id;
- durable pull-consumer behavior: queue first, consume only when a worker is
  available, acknowledge by forecast/no-update artifact, retry by reissuing
  only when the evidence fingerprint changes or an operator forces it.

The current ZTARE repository has a local A2A projection. The canonical
general-purpose implementation is the sibling `cognitive-firm` package. ZTARE
code may use a local fallback for development, but protocol improvements that
are not GP-230-specific should be made in cognitive-firm and consumed here as
the tenant overlay.

### DAG / Void Guidance for Forecasters

Probability DAGs and graph-basin packets are forecast evidence, not market
state. A forecaster should use them when supplied to:

- decompose the forecast into premises and dependencies;
- identify the weakest premise or bottleneck node;
- name what the DAG omits: missing observables, hidden coupling, unpriced
  residuals, stale evidence, or absent negative cases;
- map those findings into existing forecast fields:
  `failure_mode_distribution`, `specific_failure_mode_ids`,
  `action_change_recommendation`, and externality tags.

Do not generate a fresh autoresearch DAG for every GP-230 forecast. Most DAGs
are produced inside ZTARE loops (`latest_probability_dag.json`,
`champion_probability_dag.json`) or by project-specific graph-basin scripts.
Warm events SHOULD attach existing DAG/graph artifacts with `--evidence-path`
when they materially affect the contract. The absence of a DAG is itself
useful: it should be logged as a void or missing decomposition when it changes
forecast confidence.

### Multi-Field RD Forecasts

For minefield RD ticks, one binary success price is not enough. Forecast rows
SHOULD include the fields already supported by the CLI:

- `p_success`;
- `expected_cost_agent_minutes`;
- `p_regression`;
- `p_dependency_issue`;
- `p_needs_new_lemma`;
- `failure_modes_json`.

Resolution MUST record `actual_cost_agent_minutes` when it is knowable, so the
forecast pool can audit both truth calibration and effort calibration. A good
forecast contract prices the outcome and the expected friction class; it is not
only a pass/fail bet.

### Failure-Mode Preconditioning

Forecast rationales are part of the contract output. A useful forecast may
improve the action even when its probability estimate is pessimistic or later
miscalibrated, provided it identifies a concrete failure mode that the executor
then avoids.

Required resolver field or note when this happens:

```json
{
  "failure_mode_preconditioner_used": true,
  "preconditioner_source": "forecast agent id / aggregate path",
  "preconditioner_effect": "specific implementation constraint honored"
}
```

This field is advisory and separate from scoring. Brier/log score and
agent-minute effort error still resolve normally. Do not credit generic risks;
the failure mode must be specific enough to appear in the implementation diff,
outcome, E-row, or GP-233 decomposition.

### Structured Externality Audit

The 2026-05-14 panel and audit added a machine-readable externality layer.
The implementation target is:

```text
scripts/public/control/forecast/pool.py
scripts/public/analytics_shared/audit_forecast_pool_externalities.py
```

The audit MUST remain read-only by default and report:

- coverage of contract/forecast/outcome externality fields;
- positive externalities: preconditioner usage, decision-change count,
  forecast IDs that changed execution, GP-233 linked rows;
- negative externalities: hedge-band fraction, high-entropy failure-mode
  forecasts, unresolved contracts, forecast drag, negative externality tags;
- failure-mode precision: top-1 hit, specific-ID hit, and realized probability
  mass when `realized_failure_mode_ids` are present.

As of the 2026-05-19 ZTARE market-utilization audit, the same read-only report
MUST also cover whether GP-230 is behaving as a decision market rather than
only as a forecast log:

- market depth: forecast-count bins per contract, single-forecaster contracts,
  and p-success spread across multi-forecaster contracts;
- identity hygiene: post-binding noncanonical `agent_id` rows and alias counts;
- domain hygiene: domain families that fragment calibration, such as route-name
  variants that should share priors;
- belief-update usage: count and recency of forecast update artifacts;
- failure-mode quality: normalized entropy, `other` mass, and specific-ID
  coverage;
- causal externality capture: `changed_by_forecast_ids`,
  `counterfactual_value_bucket`, `old_next_action`, `new_next_action`, and
  decision-change coverage;
- calibration debt: resolved contracts that lack score rows;
- raw-ledger caveat: PATTERN-012 prediction-ledger resolved/scored coverage
  reported separately from GP-230 forecast-pool scoring.

Backward compatibility rule: old contracts remain valid. Externality fields are
optional until at least `20` scored contracts have the structured fields. The
daemon/status layer may warn about missing externality fields but must not
invalidate older score artifacts.

Promotion warning: do not move to a live LMSR/AMM until the sealed-pool audit
shows reliable causal use of forecasts: decision changes are attributed,
named failure modes are scored against realized traps, resolved contracts are
scored, and forecaster identity/domain aliases no longer fragment calibration.

Concrete 2026-05-14 NS example:

- contract:
  `ns_route1_angular_carrier_identification_split_micro_20260514_tick316`;
- aggregate: `p_success=0.771`, expected effort `19` agent-minutes;
- shared preconditioner: avoid a cosmetic split that merely renames
  `l2Carrier_identifies_totalAngularMoment`, or a split with Prop labels too
  weak to construct `Route1PressureAngularCarrierEstimate`;
- execution response: carry the equality explicitly while separating recovered
  pressure-Hessian projection, projected Riesz/angular matching,
  normalization, and anti-tautology guards.

### Literature Positioning

Prediction markets and proper scoring rules are established. Prior work covers
prediction markets for collective intelligence, IT project-management
forecasting/communication, market-scoring rules such as LMSR, and artificial
prediction markets for human-AI collaboration.

Reference anchors for the positioning pass:

- Hanson, "Logarithmic Market Scoring Rules for Modular Combinatorial
  Information Aggregation" (`https://hanson.gmu.edu/mktscore.pdf`);
- Barbu and Lay, "An Introduction to Artificial Prediction Markets for
  Classification" (`https://www.jmlr.org/papers/v13/barbu12a.html`);
- Barberis Canonico, Flathmann, and McNeese, "The Wisdom of the Market:
  Using Human Factors to Design Prediction Markets for Collective Intelligence"
  (`https://doi.org/10.1177/1071181319631282`);
- Chakravorti et al., "A prototype hybrid prediction market for estimating
  replicability of published work" (`https://arxiv.org/abs/2303.00866`).

GP-230 should therefore not claim novelty for "prediction markets" or "proper
scoring." The ZTARE contribution is the composition:

```text
sealed read-only agent forecasts
+ isolated builders
+ artifact-backed objective resolution
+ macro/meso/micro research-routing layers
+ agent-minute effort calibration
+ failure-mode preconditioning
+ explicit calibration reducer
```

Treat first-known novelty claims separately from the architecture. The
architecture is the sealed, scored, reflexive research-decision market described
above; literature positioning should cite the nearest external ancestors
without weakening the pattern itself.

## CLI

Initial command surface:

```text
./venv/bin/python scripts/public/control/forecast/pool.py init-contract ...
./venv/bin/python scripts/public/control/forecast/pool.py add-forecast ...
./venv/bin/python scripts/public/control/forecast/pool.py aggregate ...
./venv/bin/python scripts/public/control/forecast/pool.py resolve ...
./venv/bin/python scripts/public/control/forecast/pool.py score ...
./venv/bin/python scripts/public/control/forecast/pool.py calibrate ...
./venv/bin/python scripts/public/control/forecast/pool.py status
./venv/bin/python scripts/public/control/forecast/pool.py materialize-state ...
./venv/bin/python scripts/public/control/forecast/pool.py record-decision-use ...
./venv/bin/python scripts/public/control/forecast/pool.py daemon-once --write
./venv/bin/python scripts/public/control/forecast/pool.py warm-daemon-once --write --emit-agent-channel
./venv/bin/python scripts/public/control/forecast/pool.py warm-consumer-once --runtime codex
```

`daemon-once` is the first promotion step toward a daemon primitive. It does
not dispatch agents, resolve contracts, score contracts, or expose live market
prices. It scans forecast-pool contracts plus
`analytics/public/ledgers/prediction/prediction_ledger.jsonl`, classifies each
contract's next action, summarizes unresolved prediction-ledger rows, and writes
`analytics/public/forecast_pool/status/daemon_once_latest.json` when `--write`
is passed.

`materialize-state` is the RD/membrane fast-read builder. `record-decision-use`
is the causal-use ledger writer that records whether the aggregate changed,
confirmed, split, deferred, killed, escalated, or was intentionally ignored.

## RD Tick Integration

`scripts/public/control/rd_tick_brief.py` should surface:

- open forecast contracts;
- contracts with forecasts but missing aggregate;
- resolved contracts missing scores;
- latest aggregate routing hints for macro gates.

The tick should not hard-stop on open micro contracts unless a typed dispatch
depends on them. Macro contracts for GNN/GPU/public-claim gates should be
blocking when explicitly referenced by the active decision.

## Daemon Design

Do not start with free-form agents watching the ledger.

Safe daemon design:

0. `daemon-once` status scan produces the latest open-contract and open-ledger
   artifact without dispatching agents;
1. file watcher detects eligible open contracts;
2. dispatches read-only pricing agents with the contract and relevant artifact
   packet;
3. agents write forecast JSON only;
4. daemon aggregates when quorum is reached;
5. no builder sees aggregate price unless RD explicitly releases it;
6. resolver/score stage runs after objective outcome exists.

Daemon promotion is blocked until CLI contracts resolve cleanly for at least
three pilot decisions.

## Tests / Smoke Gates

Minimum local smoke tests:

1. create a micro `patch_compile` contract;
2. add two forecasts;
3. aggregate;
4. resolve success;
5. score;
6. verify status reports all artifact stages.

Minimum invariants:

- probabilities are clipped;
- forecast files are per-agent, avoiding write conflicts;
- aggregate can run with `N>=1`;
- scoring refuses missing outcome;
- resolving refuses missing contract;
- CLI exits nonzero on malformed failure-mode JSON.
- smoke output includes cost-error scoring and `daemon-once` ledger scan.

## Promotion Gate

Promote to org primitive only after:

- `>=3` contracts resolved;
- `>=1` decision materially changed or sharpened by aggregate;
- no manual settlement disputes;
- no sabotage/write-access violation;
- overhead below `15` agent-minutes per contract.

## Open Questions

1. Should certified micro forecast rows also append to PATTERN-012, or remain
   separate to prevent ledger bloat? Scratch RD-like micro rows now mirror as
   numeric-tier prediction-ledger rows by default, while forecaster aliases
   remain forecast-pool-only unless explicitly mirrored.
2. Should rejected-branch exploration audits be scheduled by fixed percentage
   or uncertainty threshold?
3. Should calibration weights be updated automatically after `N>=10` scores, or
   reviewed by RD before use?
