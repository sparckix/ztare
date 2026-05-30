# Forecast Pool Externalities Review

**Date:** 2026-05-14
**Contracts:** `meta_prediction_market_externalities_review_20260514`, `gp230_externality_fields_schema_impl_20260514`
**Report:** `analytics/public/forecast_pool/forecast_pool_externalities_audit_20260514.json`
**Script:** `scripts/public/analytics_shared/audit_forecast_pool_externalities.py`

## Question

Do the GP-230 / prediction-market artifacts support ex-post analysis of positive and negative externalities, beyond ordinary Brier and effort calibration?

## Verdict

Partially, now upgraded. The existing forecast pool already supports calibration, effort-error, routing-hint, failure-mode, and temporal-drag audits. The initial gap was that positive externalities were mostly indirect through GP-233 prose and resolution notes. The implementation now adds optional structured fields so a resolver can record when forecasts changed execution by naming a trap to avoid, while still scoring Brier and effort normally.

## Current Evidence

The latest audit covered `136` contracts, `276` forecasts, `127` outcomes, and `252` score rows.

- Overall mean Brier: `0.1929`.
- Brier skill versus uniform binary baseline: `0.2285`.
- Median expected/actual effort ratio: `1.8197`.
- `ns_route1_pde` is strong so far: `126` score rows, mean Brier `0.152`, skill `0.3921`.
- `gp225_repair_micro` and `navier_stokes_route1` are weak on raw calibration: mean Brier `0.2999` and `0.3097`.
- Positive externality evidence remains mostly legacy prose, but the new structured path is live: `1` contract has counterfactual fields, `2` forecasts have specific failure-mode IDs/action-change recommendations, and `1` outcome records `decision_changed_bool`, `failure_mode_preconditioner_used`, and realized failure-mode IDs.
- Failure-mode text scoring is still weak: top-1 text hit rate is `0.0078`. Structured failure-mode scoring now works where fields exist: `2` scoreable forecasts, specific-ID hit rate `1.0`, mean realized failure-mode probability mass `0.42`.
- Negative externality flags exist: `41` hedge-band rows, `258` high-entropy failure-mode forecasts, `10` unresolved contracts, and two forecast-drag cases where forecast-to-resolution time was much larger than actual effort.

## Rule Recommendations

Implemented these optional fields and made the audit script consume them:

- Contract: `baseline_action`, `counterfactual_action`, `externality_hypotheses`.
- Forecast: `specific_failure_mode_ids`, `action_change_recommendation`, `forecast_externality_tags`.
- Outcome: `realized_failure_mode_ids`, `failure_mode_preconditioner_used`, `preconditioner_source`, `preconditioner_effect`, `decision_changed_bool`, `old_next_action`, `new_next_action`, `externality_tags`, `negative_externality_tags`, `counterfactual_value_bucket`, `changed_by_forecast_ids`.

Score these derived metrics:

- `failure_mode_top1_hit_rate` and probability mass on realized failure modes.
- `decision_changed_rate` and forecast IDs that changed execution.
- `externality_adjusted_value`, separate from Brier.
- Forecaster effective-n / correlation.
- Forecast drag: forecast latency versus actual task effort.
- Hedging rate: share of forecasts clustered near noncommittal probability bands.

## Anti-Gaming Rules

- Do not award externality credit for generic risks such as "may fail to compile".
- Externality credit requires a named trap that appears in the implementation, artifact, or closure row.
- Do not blend externality credit into Brier; score the probability normally.
- If a forecast changes the action, the resolver should name the old and new action.
- If a forecast is pessimistic and the action succeeds because the executor avoided its named trap, record both facts.

## Next Mechanization

Keep `audit_forecast_pool_externalities.py` read-only. The next improvement is not more schema; it is usage discipline: material GP-230 contracts should fill these fields when forecasts change execution, and the audit should be rerun after the next `20` structured outcomes.
