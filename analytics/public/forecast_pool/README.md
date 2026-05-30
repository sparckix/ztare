# analytics/public/forecast_pool/

The prediction / forecast layer (~76 code references). The RD and
agents register pre-registered forecasts here, the calibration scorer
resolves them, the P0 page consumes the summary. Owned by the
calibration track; P0 only consumes, it never recomputes calibration
here. Every top file and child tree is listed.

## Top-level files

- `p0_calibration.json` - the stable contract the P0 rollup reads
  (schema p0_calibration.v1: brier_per_period, cross-family
  disagreement, resolution, externalities, as_of).
- `calibration_summary.json`, `calibration_weights.json` - rolled-up
  calibration + per-predictor weights.
- `externalities_rollup.json`,
  `forecast_pool_externalities_audit_20260514.json`,
  `forecast_pool_externalities_review_20260514.md` - externality
  accounting + the dated audit/review.
- `market_events.jsonl` - the forecast-market event stream.
- `v34_contract_closeout_report.md` - the v34 contract close-out
  report.

## Child trees

- `contracts/` - pre-registered forecast contracts (claim, p,
  resolution rule, as-of). Large; one file per contract.
- `forecasts/` - per-question forecast records keyed by tick/topic.
- `outcomes/` - resolved outcomes per forecast.
- `scores/` - per-forecast Brier / calibration scores.
- `forecast_updates/` - mid-flight forecast revisions.
- `aggregates/` - rolled-up calibration (bulk; gitignored).
- `consumer_state/` - the warm-consumer loop state + prompts +
  runtime sessions (large, regenerable).
- `warm_state/`, `status/` - consumer warm-state + pool status
  snapshots.
- `wake_events/` - consumer wake-event records.
- `_quarantine/` - quarantined malformed/contested forecast rows.
- `gp230_3_attacks_clay_closure_2026_05_15/`,
  `gp230_silent_flat_branch_closure_2026_05_14/`,
  `gp230_tick473_non_existence_2026_05_15/` - dated GP-230 Clay-closure
  forecast bundles.

Individual generated files inside these trees are not separately
documented (they are pipeline output); this README is their map.
