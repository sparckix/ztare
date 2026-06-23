---
description: "Why predictions are gameable and how the append-only ledger + Brier scoring catch miscalibration."
---
# Prediction Ledger Pattern

> **Up:** [Documentation map](../README.md)

**Status:** PROMOTED to `org/patterns/PATTERN-012` on 2026-05-09 (operator override of the 1-campaign gate). Canonical source-of-truth lives at `org/patterns/prediction_ledger.md`; this doc is the reader-facing explainer. Demotion rules remain active (Brier worse than uniform after ≥20 predictions, or predictions gamed by under-confident hedging).
**Sibling:** `analytics/public/ledgers/catch/catch_ledger.jsonl` (catches actual self-overclaim); this ledger catches forecast miscalibration
**Pattern provenance:** operator observation 2026-05-08, "you always estimate wrongly by using human effort instead of actual agent effort"
**Data file:** `analytics/public/ledgers/prediction/prediction_ledger.jsonl` (one prediction per line)
**Demotion rules:** (1) if predictors converge on Brier scores worse than uniform after ≥20 predictions, pattern is curve-fitting calibration → demote; (2) if predictions get gamed (under-confident hedging to look calibrated, predictions stop driving action prioritization) → demote.

## What this pattern catches

Predictions are claims about the future. Like substrate-level claims, they are gameable. Unlike substrate-level claims, they have a deterministic resolver: time passing. The Prediction Ledger records every substantive prediction at the moment it is made, predicted odds, predicted effort, predicted cost, predicted robustness, predicted direction-of-effect, predicted category, predicted replication, predicted cascade, predicted information loss, and compares against the actual outcome when the result lands. A resolved prediction with a large calibration delta is a structured record the catch ledger can fire on.

The bug this is designed to catch is **systematic miscalibration of effort estimates**, specifically, a strong prior to estimate in human-effort units ("1 day," "1 week") for tasks that agents complete in agent-effort units (minutes, hours). Operator surfaced 2026-05-08 that the Research Director (Claude) was citing "1 working day" for tasks where an agent does the same work in ~30 minutes. Pilot data confirmed: 4 predictions, calibration ratios 8.1×, 8.5×, 11.1×, 11.8×, converging on **~10× systematic over-estimation**. Pattern is broader than this one bug; expanded estimation taxonomy added 2026-05-09 to cover cost, robustness, direction, category, replication, cascade, info-loss.

## What kinds of estimation belong (expanded 2026-05-09)

Any pre-resolution estimate that gates a downstream action:

| Estimation kind | Why log |
|---|---|
| Conditional odds | substrate-verdict probability gates promote/demote/extend |
| Effort estimates (agent-minutes, NOT human-hours) | calibration of dispatch decisions |
| Token / API cost | real-money calibration |
| Wall-clock time-to-resolution | distinct from agent-minutes; covers queueing, dependencies |
| Robustness / brittleness | pre-registers "I expect this to be brittle" upfront, catches post-hoc rationalization |
| Direction-of-effect (sign + magnitude) | sign-flip detection separate from odds |
| Categorical class | which catch fires, which agent succeeds |
| Replication | "this will replicate under condition K" |
| Cascade | "if A closes, P(B closes) updates to X" |
| Information-loss | "this compression will lose signal X" |

The unifying property: **pre-resolution claim → post-resolution scoring → calibration data**.

## Tier system (anti-bookkeeping-bloat)

Without tiering, the ledger becomes "track all the things." Tiers:

- **Tier 1 (MUST log).** Predictions that gate a typed action: dispatch, kill, promote, escalate. Substrate verdicts.
- **Tier 2 (SHOULD log).** Predictions that inform prioritization: atom-ordering, agent-selection.
- **Tier 3 (MAY log).** Exploratory or idle predictions. Not required.

**Anti-gaming counter-rule:** any prediction that *retrospectively gated a typed action* is Tier 1, regardless of original framing. Catch ledger fires on retroactive Tier promotion.

## Schema

Each row in `analytics/public/ledgers/prediction/prediction_ledger.jsonl`:

```json
{
  "prediction_id": "PL-001",
  "predicted_at": "2026-05-08T23:00:00Z",
  "predictor": "research_director_claude_opus_4_7",
  "substrate": "gravity / PMOND v5_locked",
  "question": "Spearman ρ of fitted gext_over_a0 vs independent environmental density across N UDGs",
  "conditional_odds": [
    {"event": "ρ >= 0.6", "p": 0.25},
    {"event": "0.3 <= ρ < 0.6", "p": 0.50},
    {"event": "ρ < 0.3", "p": 0.25}
  ],
  "effort_estimate_human_hours": 8,
  "effort_estimate_agent_minutes": 30,
  "effort_units_actually_used": null,
  "information_gain_predicted": "decisive on L1→L2 promotion",
  "value_if_event_1": "L2 promotion + X-post addition + paper §3.3 update",
  "value_if_event_2": "weak bounded regularity, conditional verdict",
  "value_if_event_3": "demote PMOND v5_locked to curve fit; close gravity track",
  "pre_registered_thresholds": "{0.6 promote / 0.3-0.6 bounded / <0.3 demote}",
  "prediction_artifact_path": "projects/gp163d_unified_accel/workspace/ns_pattern_application_2026_05_08/RD_CHARTER_2026_05_08.md",
  "resolved_at": null,
  "actual_outcome": null,
  "actual_effort_minutes": null,
  "calibration_delta": null,
  "meta_darwin_audit": null
}
```

When the prediction resolves, fill in `resolved_at`, `actual_outcome`, `actual_effort_minutes`, `calibration_delta`, `meta_darwin_audit`. Never edit prior fields.

## Information-gain-per-unit-effort metric

Define:

- **Information gain** = bits of decision-relevant signal. Operationally: does the result change a typed action (open atom closes, claim demotes, promotion-level shifts)? Binary outcomes: 1 bit. Three-bucket falsifier (promote/bounded/demote): ~1.6 bits. Continuous ρ value: hard to count in bits; use "decisive" / "informative" / "weak signal" / "noise" labels.
- **Effort unit** = **agent-minutes**, not human-hours. This is the central correction.
- **Cost-adjusted effort** = agent-minutes × token-cost-multiplier. (For Opus 4.7 at typical session cost, an agent-minute costs ~$X; for cheap-tier, ~$Y. Track both.)

The metric: `gain / agent_minutes`. High-leverage moves rank high. Use to prioritize between dispatchable tasks.

Example from the gravity Phase 1 campaign:

| Agent task | Predicted gain | Predicted agent-min | gain/min |
|---|---|---|---|
| Atom 3 (ρ test) | DECISIVE (1.6 bits) | 30 | 0.053 |
| DGSAT-I root cause | MEDIUM (0.6 bits) | 30 | 0.020 |
| Catch ratification (12) | HIGH (3 bits) | 60 | 0.050 |
| v5_2/v6 convergence | MEDIUM (0.6 bits) | 30 | 0.020 |

Atom 3 and catch ratification are the high-leverage moves; the other two are MEDIUM. All four ran in parallel, so the metric matters for priority when serial.

## How this pattern fits with existing discipline

- **Sibling to catch ledger.** Catch ledger fires on past overclaims. Prediction ledger fires on future overclaims by recording them ahead of resolution.
- **Pre-registration discipline (P15/P17).** The prediction ledger IS pre-registration, just with explicit calibration tracking added. Every pre-registered claim should generate a prediction ledger row.
- **Meta-Darwin strange loop (P18).** Predictions are themselves gameable, under-confident predictions to look "calibrated," padded effort estimates to look "humble." The strange-loop applies: if the predictor consistently shows a calibration bias (e.g., Brier score worse than chance, or agent-effort estimates 10× too high), the pattern catches that and demotes the predictor's authority to make further predictions.

## Forecast contract read model

The durable cross-project ledger remains
`analytics/public/ledgers/prediction/prediction_ledger.jsonl`. The forecast
pool already has two producer surfaces:
`analytics/public/forecast_pool/contracts/*.json` for GP-230 contracts and
`forecast_pool.py scratch-forecast` for uncertified RD/principal self-bets. A
scratch forecast may mirror into the prediction ledger with the existing fields
`prediction_id`, `predicted_at`, `predictor`, `substrate`, `question`,
`p_success`, `pre_registered_thresholds`, `prediction_artifact_path`,
`linked_scratch_id`, and `forecast_pool_semantics`.

[`src/ztare/forecasting/prediction_contract.py`](../../src/ztare/forecasting/prediction_contract.py)
is the shared read model over those existing rows plus project-local
autoresearch rows. It normalizes `question` to event, `substrate`/`domain` to
subject, `pre_registered_thresholds` or `resolution_predicate` to resolution
rule, and preserves provenance as `prediction_ledger`, `forecast_pool`,
`scratch_contract`, or `autoresearch_workspace`. Scratch rows remain marked by
their existing semantics: uncertified, excluded from GP-230 calibration, and not
eligible for membrane close. The shared read model enforces that boundary:
`certified` and `can_satisfy_membrane` only count for forecast-pool rows in
`forecast_pool` provenance mode, and membrane eligibility additionally requires
a resolved row. It also rejects non-causal timing: `predicted_at`/`forecasted_at`
must name the forecast instant, the seal cannot precede the forecast, and both
the forecast and seal must strictly precede `resolved_at`. Local autoresearch
rows and scratch rows may be scored as sealed measurement receipts, but they
cannot self-promote into close evidence.

[`src/ztare/validator/autoresearch_prediction_contract.py`](../../src/ztare/validator/autoresearch_prediction_contract.py)
is only an adapter for `ztare autoresearch trace`; it reads
`workspace/iteration_predictions.jsonl` or `workspace/prediction_contracts.jsonl`
through the shared model. When `resolved_at` plus `actual_success` or
`actual_outcome` lands, the read model computes binary Brier and a constant-0.5
baseline. This is a measurement receipt, not a scheduler: forecast, Elo, or
Brier scores should not steer DAG focus, mutator routing, or worker allocation
until repeated resolved rows beat simple baselines and carry a downstream
decision receipt.

## Positive externality: forecasts can improve execution

A forecast is not only a number to score later. It can also be a failure-mode
map that improves the action before the outcome resolves.

The useful case is:

1. read-only forecasters price a proposed action;
2. their rationales independently name the same concrete trap;
3. the executor changes the implementation plan to avoid that trap;
4. the resolver still scores probability and effort normally.

This matters because a pessimistic forecast can be operationally useful even
when the action succeeds. In the NS route-1 pressure branch on 2026-05-14, two
forecasters priced a Lean proof-surface split at aggregate `p_success=0.771`.
Both warned that the proposed `Route1PressureAngularCarrierIdentification`
could become a fake split if it only renamed
`l2Carrier_identifies_totalAngularMoment`, or if it replaced the equality with
Prop labels too weak to build the constructor. The subsequent Lean edit carried
the final equality explicitly while splitting projection, Riesz/angular
matching, normalization, and anti-tautology guards around it. The forecast did
not prove the theorem; it sharpened the execution constraint.

Log this as a separate field or resolution note such as
`failure_mode_preconditioner_used: true`. Do not blend it with calibration:
Brier and effort-error still score the numeric forecast. The positive
externality is a second artifact: the forecast prevented a known failure mode
from entering the implementation.

## Ex-post externality audit fields

The 2026-05-14 forecast-pool externalities audit found that calibration and
effort are measurable today, while positive externalities are mostly recoverable
only from [GP-233](../../research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md) prose and resolution notes. For future contracts, record:

- contract-level: `baseline_action`, `counterfactual_action`,
  `externality_hypotheses`;
- forecast-level: `specific_failure_mode_ids`,
  `action_change_recommendation`, `forecast_externality_tags`;
- outcome-level: `realized_failure_mode_ids`,
  `failure_mode_preconditioner_used`, `decision_changed_bool`,
  `old_next_action`, `new_next_action`, `externality_tags`,
  `negative_externality_tags`, `counterfactual_value_bucket`.

This lets the audit separate calibration from externality value: a forecast can
be numerically pessimistic and still useful if its named failure mode changed
execution before the run.

## Pilot implementation

The 4 gravity Phase 1 agents currently running constitute the pilot. Predictions logged at the moment of dispatch. Resolution will be recorded when each agent returns. After all 4 resolve, write a calibration summary to `projects/gp163d_unified_accel/workspace/ns_pattern_application_2026_05_08/phase1/CALIBRATION_RESULT.md` comparing predicted vs actual. If calibration is good (predictions within 1 SD of actuals on average), promote pattern to runbook (AGENTS.md §4c). If poor, debug the predictor before promoting.

## Meta-Darwin audit on this pattern (recursive)

Audit applied to this design at the moment of writing:

1. **Catch MM-A.** Am I designing this because the operator suggested it, or because it solves a real problem?
   - *Verdict: real bug.* I documented "1 day" for tasks an agent does in 30 minutes, that's 16× miscalibration on a single task, multiple times this session. Pattern addresses the actual systematic error.

2. **Catch MM-B.** Will the prediction ledger become its own gameable surface?
   - *Verdict: yes, predictably.* Predictors will under-confidently hedge to look calibrated. Mitigation: tier predictions by stake. Low-stake predictions (apparatus debug) don't count toward calibration scoring; high-stake (substrate verdict, promotion-level decisions) do. The strange-loop applies, if predictor games the ledger, the ledger catches itself.

3. **Catch MM-C.** Is "agent-minutes" the right effort unit, or should it be agent-minutes × cost?
   - *Verdict: starting approximation.* Agent-minutes is the easy first metric. Full version is `agent_minutes × tier_cost_multiplier × context_window_consumed`. Starting simple; revise if calibration drifts.

4. **Catch MM-D.** Am I installing this in the runbook before piloting?
   - *Verdict: avoiding that mistake.* Pattern is documented in this doc but NOT yet in `AGENTS.md`. Will promote to runbook only after the gravity Phase 1 calibration result lands. If calibration is bad, debug first.

5. **Catch MM-E** (recursive on MM-A through MM-D). Am I writing this audit performatively to look disciplined?
   - *Verdict: partially.* The audits are real but the format is conventional. The actual test of whether this audit matters is whether MM-B and MM-C correctly flag the pattern's known failure modes when they fire. Track over the next 2 weeks.

## Meta-Darwin audit on whether to promote this pattern (2026-05-09)

Applied the recursive demotion rule to the question "should this pattern be logged in `org/patterns/` (the orchestration catalog) or kept at `docs/concepts/` as documented-but-unpromoted?"

- **MM-PL1:** Promoting before pilot calibration evidence is the same anti-pattern as substrate-claim promotion before structural defenses pass. *Verdict: real risk; same class of failure as G10 sentiment-driven upgrade.*
- **MM-PL2:** Holding back a clearly-useful pattern is also a mistake. The bug it catches is real and recurrent. *Verdict: also real; net cost of holding back is information loss across session boundaries.*
- **MM-PL3:** What's the right promotion gate? *Answer: 2 independent campaigns + concrete bug caught by the pattern alone.* Today the pilot has 1 campaign with 4 predictions; gate not met.
- **MM-PL4:** What's the demotion rule for the pattern itself? *Answer: Brier worse than uniform after 20 predictions, OR predictions gamed by under-confident hedging.* Documented above.
- **MM-PL5 (recursive):** Am I being too cautious because I just got caught being too eager (G10)? *Verdict: possibly biased. But methodology promotion ≠ substrate promotion; these are different categories. The right answer for methodology is "try, measure, then promote", that IS the discipline applied to itself.*

**Decision (2026-05-09):** keep at `docs/concepts/`, mark PILOT. Run a second campaign (NS Track B continuation with explicit prediction-ledger entries before the next atom-closure attempt) before promoting.

The audit itself is logged here, not in chat, so the criterion is visible to future-me and to other agents.

## Insight-yield-per-min metric (added 2026-05-09 evening, PL-047 debate)

**Problem statement.** The operator surfaced two consecutive critiques of the original Shannon-info-per-wall-clock-min metric:

1. **Atomicity:** per-row insight/min penalizes agents for spending grunt-work minutes (build setup, Mathlib search, namespace fixes) that are PREREQUISITE to insight-yielding minutes. Skipping scaffolding produces unverified claims; charging the same row for both does the wrong thing.
2. **Telemetry validity:** the per-row numerator is currently agent-self-reported `actual_effort_minutes`, which empirically inflates 4-12× vs harness `duration_ms`. The metric has been consuming bad input.

### PATTERN-001 friction debate (3 rounds, PL-047 deliverable)

**Champion_atomic** (per-agent insight/min is fine):
- Grunt work IS part of cost; aggregating obscures bad agents
- Per-row penalty creates incentive to minimize scaffolding waste
- Mathlib-search and namespace-debug ARE forms of yield (they catch C-43 phantoms)

**Champion_aggregate** (campaign-aggregate is more honest):
- Grunt-work + insight-work are inseparable in a single agent's run
- Per-agent ratios penalize necessary scaffolding (Polanyi tacit-knowledge thesis)
- DORA / Forsgren-Humble-Kim 2018 explicitly flagged single-ratio metrics as anti-pattern; paired metrics (lead-time + change-failure-rate) are the correct shape

**Arbiter (PL-047 round 3):** 2:1 in favor of sharpening (Champion_aggregate on R1 precedent + R3 additivity; R2 was a tie that re-located the moral hazard from row-level to substrate-level). PATTERN-006 tautology-trap fired and the sharpened metric PASSED all three tautology checks conditional on pre-enumerated telemetry categories.

### Recommendation: 3-number form per substrate-campaign

Per-row metric is **demoted to calibration diagnostic**, not removed. Headline becomes a paired 3-number form:

1. **`campaign_yield_bits_per_min = Σ info_bits / Σ wall_clock_min`** (headline)
2. **`scaffolding_share = Σ scaffolding_min / Σ wall_clock_min`** ∈ [0,1] (orthogonal axis)
3. **`yield_per_yielding_minute = Σ info_bits / Σ (wall_clock_min − scaffolding_min)`** (cross-author normalizer)

### Required telemetry categories (must be pre-enumerated)

Default-on-fail is `derivation` (conservative against laundering scaffolding into yield):

- `build` (lake build, dependency resolution)
- `mathlib_search` (grep + symbol verification)
- `install` (lake update, lakefile changes)
- `namespace` (import collision fixes)
- `format` / `lint` (style cleanup)
- `deploy` (writing files, git ops)
- `derivation` (analytic content authoring) ← yield-bearing
- `proof` (Lean proof body) ← yield-bearing
- `argument` (prose reasoning) ← yield-bearing
- `experiment_run` (sweep / fit / sim) ← yield-bearing

### Operational kill criterion

**If telemetry-miss rate > 0% for the campaign window, headline reads N/A.** Don't propagate inflated agent-self-reported numbers as if they were canonical. Today's `analytics/public/telemetry/insight_yield_summary.json` shows 4 of 4 telemetry-inflated warnings, the 0.0717 number is uninterpretable until the harness join (`task_id` field on PL rows) lands. **The harness join fix is higher-leverage than further metric design.**

### Comparator discipline (Howard EVPI / DORA)

Report **Δyield vs previous campaign-week**, not absolute scalar. Howard 1966 / ISPOR 2020 incremental-cost-effectiveness-ratio (ICER) form:

```
Δyield_week = (yield_this_week - yield_last_week) / (cost_this_week - cost_last_week)
```

A standalone scalar (today's "0.0717 bits/min") is uninterpretable; only differential improvement matters.

### Precedents (pre-2026)

- **Howard 1966**, Value of Information / EVPI; ISPOR 2020 modernization for research prioritization
- **Forsgren / Humble / Kim 2018** *Accelerate* / DORA, paired metrics (lead-time + change-failure-rate); single-ratio metrics flagged as anti-pattern
- **Polanyi 1958** *Personal Knowledge*, tacit/scaffolding-knowledge thesis justifies amortizing prerequisite minutes rather than charging them to the row that incurs them
- **Considered and rejected:** Landauer 1961 (rate-distortion / minimum thermodynamic work for irreversible computation), wrong-scale framing; doesn't apply to discrete prediction-ledger rows

### Falsifiable prediction (PATTERN-005)

Pre-registered: across the next 4 weeks of NS Track B work, **`yield_per_yielding_minute` should be at least 2× higher than `campaign_yield_bits_per_min`** (because scaffolding_share is empirically > 0.5 on Lean substrate work). If the ratio is < 1.5× over ≥10 dispatches, the categorization is failing, agents are mis-tagging insight as scaffolding or vice versa.

### Out-of-scope-but-flagged

The `cost_*_usd` fields in the prediction ledger are deprecated as of 2026-05-09 (operator decision, the campaign runs on Max-subscription, marginal API cost ≈ 0). Future cost surfaces are: (a) rate-limit-window-consumed, (b) operator-attention-cost, (c) context-window pressure on the main session. None are USD.

### Implementation status

- ✅ `scripts/public/analytics_shared/score_insight_yield_per_minute.py` (per-row metric; demoted to diagnostic)
- ✅ `analytics/public/telemetry/agent_telemetry.jsonl` (canonical wall-clock from harness duration_ms; 19 rows captured)
- ✅ `analytics/public/ledgers/prediction/PREDICTION_LEDGER_README.md` documents the deprecation + sharpened form
- 🟡 Task-id join wiring (highest-leverage; needs PL row task_id field at dispatch + resolution)
- 🟡 Telemetry-category tagging (pre-enumeration in dispatch prompt; agent emits per-tool-use category)
- 🟡 3-number form computation (pending category-tagging wiring)

Full debate at `projects/methodology_synthesis/insight_yield_metric_debate_2026_05_09.md`.

## Open questions

1. Is Brier score the right calibration metric, or should we use log-score (for over-confidence penalty)?
2. How do we score predictions that have multiple buckets (e.g., 3-bucket promote/bounded/demote)?
3. Should the prediction ledger have a "concurring-agent gate" like the catch ledger? (Probably not, predictions can be solo; resolution is by time, which doesn't need a second agent.)
4. When a prediction resolves badly, does the predictor get a "demoted credibility" tag for future predictions? Implementation: a per-predictor calibration index that informs orchestration (predictor with low calibration index has their predictions discounted by other agents).
5. Does the 3-number form survive its own pre-registered falsifier (yield_per_yielding_minute ≥ 2× campaign_yield)? If not, pattern is mis-categorizing minutes; demote.
