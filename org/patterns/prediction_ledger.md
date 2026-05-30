---
id: PATTERN-012
name: prediction_ledger
version: 2  # version bumped 2026-05-09 after META-META-DARWIN MODIFY verdict
status: active_conditional  # MODIFY verdict; auto-demote to PILOT in 7 days or at N=20 unless gating fixes land
discovered: 2026-05-08
promoted: 2026-05-09  # operator override of META-DARWIN hold-back; pilot calibration data was 8-12x miscalibration ratio across N=4 predictions in gravity Phase 1 campaign
meta_meta_audit: analytics/public/audits/META_META_DARWIN_PATTERN_012_2026_05_09.md  # MODIFY verdict; 2 gating fixes + 3 post-hoc fixes
auto_demote_tripwire: 2026-05-16 OR ledger N=20 — whichever comes first; if validate_prediction_ledger.py is NOT wired into CI by then AND N<20 across <2 substrates AND <2 predictors, status flips back to PILOT
triggers:
  lexical: [predict, estimate, odds, probability, timeline, will take, days, weeks, hours]
  structural: [conditional_odds_assertion, effort_estimate, promotion_decision, pre_registration]
  problem_classes: [apparatus_self_audit, calibration_drift, decision_under_uncertainty]
spawn:
  mode: inline_record
  rounds: 1  # not a debate; single-step ledger row creation
  subagents:
    - role: predictor
      description: Author the prediction. May be the operator, the Research Director, or a dispatched substrate agent.
      tools: [write]
    - role: resolver
      description: When the predicted event resolves (time passes / experiment runs / agent returns), fill the resolution fields. Same predictor or different — does not require a concurring-agent gate.
      tools: [write]
output_schema: prediction_ledger_row_v1
fallback: PATTERN-008  # three_leg_verification — if a prediction lacks evidence anchors
preconditions:
  - substantive_prediction: a prediction that gates a typed action (promotion, dispatch, kill, escalation). Idle predictions ("the weather might be sunny") are NOT logged.
  - effort_in_agent_units: effort estimates MUST be expressed in agent-minutes (or agent-hours), NOT human-hours. The operator-flagged calibration bug was systematic over-estimation by 8-12x using human-effort units.
  - pre_resolution_capture: row written BEFORE resolution. Backfilling a prediction after the result is known is automatic INSUFFICIENT_EVIDENCE on the calibration claim.
deployment_rules:
  - rule_1_log_substantive_predictions: any prediction that gates a typed action gets a ledger row before the action commits.
  - rule_2_agent_minutes_not_human_hours: effort estimates in agent units. If you find yourself estimating in human-hours, that's the bug the pattern was designed to catch.
  - rule_3_resolve_when_resolved: when the predicted event resolves, fill `actual_outcome`, `actual_effort_minutes`, `calibration_delta_*` fields. Never edit prior fields.
  - rule_4_meta_darwin_audit: each resolution writes a `meta_darwin_audit` field naming any structural lessons (e.g., "predictor systematically under-confident on event_X").
  - rule_5_demotion_thresholds: if predictors converge on Brier scores worse than uniform after >=20 predictions, pattern is curve-fitting calibration → demote. If predictions get gamed (under-confident hedging to look calibrated) → demote.
chain_position: lateral  # this pattern lives alongside other patterns; not a chain starter or terminator
related_patterns:
  - PATTERN-005 (falsifiable_asymmetry — predictions are pre-registered falsifiers)
  - PATTERN-008 (three_leg_verification — applied to verdicts derived FROM predictions)
  - ANTI-PATTERN-005 (narrative_inflation — predictions caught padded for sentiment)
references:
  - "Tetlock, Philip E. & Gardner, Dan (2015). Superforecasting: The Art and Science of Prediction. Crown."
  - "Brier, Glenn W. (1950). Verification of forecasts expressed in terms of probability. Monthly Weather Review."
falsifiable_test: |
  After N>=20 resolved prediction-ledger rows across >=2 substrates and >=2
  predictors, the aggregate Brier score on probabilistic predictions must be
  strictly better (lower) than a uniform/base-rate forecast by >=0.05, AND mean
  effort-calibration error (predicted vs actual agent-minutes) must be within 2x.
  If Brier is no better than uniform, or effort estimates revert to >2x systematic
  error (the original ~10x bug returning), demote — this restates and quantifies
  the pattern's own existing rule_5.
  metric_source: prediction_ledger.jsonl resolved rows (conditional_odds vs
  actual_outcome_bucket; effort_estimate_agent_minutes vs actual_effort_minutes);
  Brier computed by validate_prediction_ledger.py.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 12 — Prediction Ledger

## Problem

The Research Director and substrate agents make predictions throughout an orchestration cycle: conditional odds on outcomes, effort estimates for tasks, expected information gain per move. These predictions gate decisions — which agent to dispatch, which atom to close first, when to stop. When predictions are wrong systematically, decisions cascade off the miscalibration.

The specific bug this pattern catches: **systematic over-estimation of effort in human-effort units rather than agent-effort units.** Operator surfaced 2026-05-08 that the RD was citing "1 working day" for tasks an agent completes in 30 minutes. Pilot data from the gravity Phase 1 campaign confirmed: 4 predictions, 4 effort miscalibrations, ratios of 8.1×, 8.5×, 11.1×, 11.8× — converging on **~10× systematic over-estimation**.

Without a typed surface for predictions, calibration drift is invisible. With one, it's a JSONL the catch ledger can fire on.

## What kinds of estimation belong in the ledger (collapsed to 6 canonical axes per META-META P-FIX-3)

The original 10-slot taxonomy collapsed three slots that were structurally instances of others. Final 6 canonical axes:

| Axis | Schema field | Subsumes | Example |
|---|---|---|---|
| 1. Probabilistic | `conditional_odds` | (also covers robustness as `P(robust\|main_passes)`; also covers categorical as multinomial conditional_odds) | `P(rho >= 0.6) = 0.25`; `P(robust\|main_passes) = 0.30`; `P(failure_class=outlier) = 0.40` |
| 2. Effort | `effort_estimate_agent_minutes` | (NOT human-hours; bug-canonical) | 30 |
| 3. Cost | `cost_estimate_usd` | API + token + GPU spend | 0.50 |
| 4. Direction | `direction_prediction` (sign + magnitude) | distinct from odds because it pre-registers a continuous expectation, not a bucketed probability | "v5_2 lands within 1% of v5_locked" |
| 5. Cascade | `cascade_prediction` | multi-step conditional-belief updates | "if atom 3 closes, P(L2 in 1 week) updates to 0.80" |
| 6. Info-loss | `info_loss_prediction` | predictions about what compression / summarization will discard | "single-statistic threshold will hide bootstrap fragility" |

**Collapsed slots (per audit Item 2):**
- ~~Wall-clock time-to-resolution~~ → derivable from effort + queueing latency, which is an apparatus property not a prediction. Removed.
- ~~Robustness / brittleness~~ → expressible as conditional_odds `P(robust|main_test_passes)`. Removed as separate slot; logged via odds.
- ~~Categorical class~~ → expressible as multinomial conditional_odds. Removed as separate slot; logged via odds.

The unifying property: **pre-resolution claim → post-resolution scoring → calibration data.** A row populates only the axes the prediction actually covers.

## Tier system (mitigation against bookkeeping bloat)

Per META-META audit catch MM-MM-2: without tiering, the ledger becomes "track all the things" and compliance replaces calibration. Tiers:

- **Tier 1 (MUST log).** Predictions that gate a typed action: agent dispatch, kill decision, promotion-level shift, escalation to operator. Substrate-verdict predictions.
- **Tier 2 (SHOULD log).** Predictions that inform prioritization: atom-ordering, which-agent-first, which-substrate-to-pursue.
- **Tier 3 (MAY log).** Exploratory or idle predictions. Not required.

Anti-gaming counter-rule (catch MM-MM-5): any prediction that *retrospectively gated a typed action* is Tier 1, regardless of how it was originally framed. The catch ledger fires on retroactive Tier promotion (i.e., framing a Tier 1 as Tier 3 to dodge logging).

## Output schema (`prediction_ledger_row_v1`)

```json
{
  "prediction_id": "PL-NNN",
  "predicted_at": "ISO-8601",
  "predictor": "agent_or_operator_id",
  "substrate": "domain / project / track",
  "tier": 1,
  "question": "what's being predicted, in one sentence",
  "conditional_odds": [{"event": "...", "p": 0.NN}, ...],
  "effort_estimate_agent_minutes": N,
  "effort_estimate_human_hours": N,
  "cost_estimate_usd": null,
  "resolution_eta_wallclock_minutes": null,
  "robustness_prediction": null,
  "direction_prediction": null,
  "category_prediction": null,
  "replication_prediction": null,
  "cascade_prediction": null,
  "info_loss_prediction": null,
  "information_gain_predicted": "DECISIVE / HIGH / MEDIUM / LOW (description)",
  "value_if_event_K": "what unlocks if this event occurs",
  "pre_registered_thresholds": "the deterministic rule that converts result -> verdict",
  "prediction_artifact_path": "path to RD charter or pre-reg seam",
  "resolved_at": null,
  "actual_outcome": null,
  "actual_outcome_bucket": null,
  "actual_effort_minutes": null,
  "actual_effort_seconds": null,
  "actual_cost_usd": null,
  "actual_resolution_eta_minutes": null,
  "calibration_delta_odds": null,
  "calibration_delta_effort": null,
  "calibration_delta_cost": null,
  "calibration_delta_robustness": null,
  "meta_darwin_audit": null,
  "next_actions_unlocked": []
}
```

Most fields are nullable — populate only the dimensions actually being predicted. A pure odds prediction has just `conditional_odds`; a pure effort estimate has just `effort_estimate_agent_minutes`. A multi-dimensional prediction (e.g., "atom 3 will pass threshold but be brittle, in 30 agent-min, $0.20") fills the corresponding fields.

Data file: `analytics/public/ledgers/prediction/prediction_ledger.jsonl` (one row per line).

## Information-gain-per-unit-effort metric

Define:
- **Information gain** = bits of decision-relevant signal. Binary outcome: 1 bit. 3-bucket falsifier: ~1.6 bits. Continuous metric: label as DECISIVE / HIGH / MEDIUM / LOW.
- **Effort unit** = **agent-minutes**, not human-hours. Central correction. Operationalized per META-META P-FIX-5: agent-minutes = wall-clock seconds during which the agent process is actively executing tool calls (not waiting on queue, not waiting on subagent dispatch return, not idle), divided by 60. In practice, derive from the agent's telemetry `duration_ms` field (provided in completion notifications) divided by 60_000 and rounded. Subagent dispatch within the agent counts toward the parent agent's clock if the parent is blocking; if dispatched in background mode and the parent does other work in parallel, only parent's active execution time counts.
- **Cost-adjusted effort** = agent-minutes × tier-cost-multiplier × context-window-consumed (Opus full context costs more than Haiku).

The metric: `gain / agent_minutes`. Use to prioritize between dispatchable tasks. High-leverage moves rank high.

Pilot example (gravity Phase 1 campaign):

| Agent task | Predicted gain | Predicted agent-min | Actual agent-min | gain / actual-min |
|---|---|---|---|---|
| Atom 3 (ρ test) | DECISIVE (1.6 bits) | 30 | 3.7 | 0.43 |
| Catch ratification (12) | HIGH (3 bits) | 60 | 5.4 | 0.56 |
| DGSAT-I root cause | MEDIUM (0.6 bits) | 30 | 3.55 | 0.17 |
| v5_2/v6 convergence | MEDIUM (0.6 bits) | 30 | 2.55 | 0.24 |

Recompute the metric on **actual** effort once available. The metric drives prioritization on the next campaign.

## How this pattern fits with existing discipline

- **Sibling to catch ledger.** Catch ledger fires on past overclaims. Prediction ledger fires on future overclaims by recording them ahead of resolution.
- **Pre-registration discipline (P15/P17 in `docs/concepts/epistemic_principles.md`).** The prediction ledger IS pre-registration with explicit calibration tracking added.
- **META-DARWIN external audit cycle (corrected from "strange loop" per META-META P-FIX-4).** The pattern's claimed "self-catching" is structurally an external audit cycle: a separate analyzer (or a future review pass) reads the ledger, scores calibration, and demotes the predictor or the pattern itself. This is NOT a Hofstadter strange loop in the strict sense (recursive self-application of the demotion rule producing a fixed-point). To make the loop genuinely strange-loop-style, the pattern would need to log a meta-prediction *about the ledger's own calibration* INSIDE the ledger itself, then audit that meta-prediction by the same demotion rule that audits substrate predictions. **TBD enhancement** (PL-meta-prediction): once N ≥ 10 predictions are resolved, the pattern should require a meta-prediction row predicting the next 10 rows' aggregate Brier score, logged inside the ledger and audited at N+10. Until that's wired, claim accurately as "external audit," not "strange loop."

## Positive externality: forecasts as failure-mode preconditioners

Resolved success does not mean the forecast was useless when the forecast
priced the tick lower than the outcome. A read-only forecaster can improve
execution before scoring by naming the exact failure mode the executor must
avoid. In that case the forecast has two outputs:

1. the scored probability/effort estimate;
2. the pre-execution failure-mode map.

The second output can be valuable even when the first output is pessimistic.
For example, in the NS route-1 pressure branch on 2026-05-14, two forecasters
priced the `Route1PressureAngularCarrierIdentification` split at aggregate
`p_success=0.771` and both independently flagged the same trap: a fake split
that only renames `l2Carrier_identifies_totalAngularMoment` or carries Prop
labels without an equality strong enough to build the constructor. The
subsequent Lean edit explicitly carried the final equality while separating
projection, Riesz/angular matching, normalization, and anti-tautology fields.
That is prediction-market value even before Brier scoring.

Operational rule: when a forecast changes execution by naming a trap to avoid,
the resolver should record `failure_mode_preconditioner_used: true` or include
the equivalent phrase in `meta_darwin_audit`. This must not be used to excuse
bad calibration. Score odds and effort normally; log the failure-mode map as a
separate positive externality.

Anti-gaming catch: do not let agents write generic risks such as "may fail to
compile" and claim preconditioner credit. Credit requires a specific failure
mode that appears in the implementation diff, resolution artifact, or closure
row as a constraint the executor actually honored.

## Ex-post externality audit rule

As of the 2026-05-14 GP-230 audit, forecast-pool scoring can measure Brier,
log score, effort error, routing hints, rough failure-mode distributions, and
temporal drag. It cannot yet cleanly measure the positive externality "the
forecast changed the next action" because that fact mostly lives in GP-233
prose and resolution notes.

When a market is used to guide a material action, the contract and outcome
should carry enough counterfactual structure for a later audit:

- contract fields: `baseline_action`, `counterfactual_action`,
  `externality_hypotheses`;
- forecast fields: `specific_failure_mode_ids`,
  `action_change_recommendation`, `forecast_externality_tags`;
- outcome fields: `realized_failure_mode_ids`,
  `failure_mode_preconditioner_used`, `decision_changed_bool`,
  `old_next_action`, `new_next_action`, `externality_tags`,
  `negative_externality_tags`, `counterfactual_value_bucket`.

Resolution rule: if the forecast changed execution, name the old action, the
new action, and the forecast IDs that caused the change. Score probability and
effort normally; externality credit is a separate audit dimension. Generic risk
lists do not count. The named failure mode must appear in the artifact, diff, or
closure row as a constraint that was actually honored.

Reference audit: `analytics/public/forecast_pool/forecast_pool_externalities_audit_20260514.json`.

## Promotion criteria (rewritten 2026-05-09 per META-META-DARWIN G-FIX-2)

Required for promotion to `org/patterns/` (active state):

- **N ≥ 20 prediction-ledger rows** AND
- **≥ 2 distinct substrates** (e.g., gravity AND NS, not gravity-only) AND
- **≥ 2 distinct predictors** (different agent identities, not one RD-Claude in two role hats) AND
- **≥ 1 concrete bug caught by the pattern alone, reproduced across substrates** AND
- **`scripts/public/validators/validate_prediction_ledger.py` passing on the full ledger** (G-FIX-1).

**Current state vs gate:** N=8 rows, 1 substrate (gravity), 1 predictor (research_director_claude_opus_4_7). **Pattern is operating under conditional promotion** — operator override of 2026-05-09 authorized active state ahead of the gate, but per G-FIX-2 the override is structurally identical to ANTI-PATTERN-007 (deployment_time_pre_spec_laundering). The override therefore comes with a **7-day or N=20 tripwire**: if the gate is not closed by 2026-05-16 OR by the time the ledger reaches N=20 rows, pattern auto-demotes back to PILOT (`docs/concepts/` only).

The original META-DARWIN audit pre-promotion recommended a 2-campaign gate. The META-META-DARWIN audit post-promotion (`analytics/public/audits/META_META_DARWIN_PATTERN_012_2026_05_09.md`) ratified PARTIAL VALIDITY of the override but specified gating fixes. This section reflects those fixes.

**Pre-condition for full promotion:** at least one NS Track B prediction (atom 8c, W6, PR-A1, or any other NS atom) must be logged with full calibration data, BY a predictor distinct from the gravity campaign's RD. Likely candidates: a Codex agent, a different Claude session-instance, or the operator authoring directly.

Demotion rules remain active and will fire if subsequent calibration data shows Brier worse than uniform after 20 predictions, OR if predictions get gamed by under-confident hedging (operational signal: predicted-event probabilities concentrated near the empirical base rate without independent justification).

## Demotion rules

- Brier score worse than uniform after ≥20 predictions → demote (pattern is curve-fitting calibration).
- Predictions become gamed (under-confident hedging to look calibrated, predictions stop driving action prioritization) → demote.
- Predictors stop using agent-minutes and revert to human-hours → demote (the original bug returns).

## When to invoke

Default ON for any orchestration that:
- Dispatches ≥2 agents in parallel with different expected returns.
- Makes a promote/demote/extend decision on a substrate atom.
- Estimates effort for a multi-day or multi-week campaign.

Default OFF for:
- Idle musings ("we might want to do X someday").
- Trivial single-step actions where the prediction adds no information.

## Self-demotion notice

This pattern was promoted under operator override of a 1-campaign gate. The recommended 2-campaign gate is the safer rule; if the operator override turns out to be premature (pattern's predictions worse than uniform across 20 rows), this pattern self-demotes per its own rule_5. The promotion is conditional on the demotion rules holding.

## META-META audit log (recursive applied 2026-05-09)

The expanded ledger scope (cost, time-to-resolution, robustness, direction, category, replication, cascade, info-loss) was added under META-META audit. The audit caught two real risks the original draft missed: (MM-MM-2) unwieldy "track everything" mode, mitigated by Tier 1/2/3 system; (MM-MM-5) tier-gaming via retrospective Tier promotion, mitigated by the anti-gaming counter-rule that any prediction that retrospectively gated a typed action is Tier 1 regardless of original framing.

Recursive catch (MM-MM-6): the META-META audits in this doc could be performed for show rather than substance. The test of whether they matter: do they produce specific design changes? MM-MM-2 added the tier system; MM-MM-5 added the anti-gaming counter-rule. Both are mechanical changes to the pattern's deployment, not just rhetoric. Audit verdict: not theater — but track for drift over the next 4 weeks.
