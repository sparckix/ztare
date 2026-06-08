---
description: "Methodology, canonical database, and tooling contract for the GP-245 LLM forecasting calibration program."
---
# GP-245 Forecasting Calibration — Methodology / DB Contract

Updated 2026-06-04.

This is the public methodology and database contract for the GP-245 forecasting
program. Scientific claims and current law status live in `CLAIM_SUMMARY.md`.

## Canonical Database

Canonical DB:

`analytics/public/calibration/forecaster_calibration.db`

Current DB snapshot:

- contracts: `2,183`
- pilot runs: `158`
- pilot calls: `20,146`
- schema-ok calls: `19,502`
- calls with Brier: `10,945`
- resolved contracts: `525`

The DB is public evidence, not private scratch. Raw JSONL files are receipts,
but law claims must be queryable through the canonical tables unless a report
explicitly says it is a no-call/no-DB readiness audit.

### Tables

- `contracts(contract_id PK, question, source, source_corpus, horizon,
  y_known, post_training_cutoff, task_type, external_market_open,
  resolution_source_url, y_known_provenance, raw_json, created_at)`
  - one row per question/task/event surface;
  - `y_known in {0,1}` only when the outcome is resolved and binary;
  - `y_known = NULL` is allowed for unresolved or non-binary games;
  - `post_training_cutoff` is a stored flag and can be stale for Law 3 audits.
- `pilot_runs(pilot_id PK, pilot_name, primitive, corpus, source_jsonl_path,
  fired_at, n_calls, n_schema_ok, ...)`
  - one row per dispatch/run.
- `pilot_calls(call_id PK, pilot_id, contract_id, agent_id, family, condition,
  primitive, primitive_base, phase, role, pair_id, p_success, brier, schema_ok,
  parsed_json, fired_at, raw_json, ...)`
  - one row per model-family emission;
  - `brier = (p_success - y_known)^2` when `y_known` is binary;
  - channel fields such as worry, confidence, sham, bid-ask, action choice, or
    effort estimates live in `parsed_json`.
- `pre_registrations(...)`
  - power commitments and verdict targets fixed before a run.
- `family_elo_by_corpus_class(...)`
  - iterative Elo materialization, refreshed separately from SQL views.

### Views

- `v_corpus_class` — policy view separating internal vs external sources.
- `v_family_brier_by_pilot` — Brier by family and pilot.
- `v_family_brier_by_corpus_class` — headline family/corpus Brier roll-up.
- `v_family_brier_by_subsource` — platform/source drill-down.
- `v_family_brier_by_primitive_corpus` — primitive/corpus roll-up.
- `v_pilot_summary` — pilot-level summary.
- `v_intervention_vs_baseline` — paired intervention summaries.

### Current Source Coverage

Largest DB source buckets:

| source | contracts | resolved | pre_cutoff flag | post_cutoff flag |
|---|---:|---:|---:|---:|
| `f105_effort_estimation` | 510 | 0 | 0 | 0 |
| `bias_inheritance_ood` | 435 | 0 | 0 | 0 |
| `NULL` | 309 | 30 | 0 | 0 |
| `polymarket` | 168 | 74 | 33 | 127 |
| `legacy_orphan_backfill` | 163 | 0 | 0 | 0 |
| `fred` | 139 | 98 | 49 | 79 |
| `manifold` | 124 | 116 | 27 | 89 |
| `metaculus` | 72 | 0 | 0 | 60 |
| `premium_public_clean` | 71 | 71 | 0 | 0 |
| `f105_metacognition` | 45 | 45 | 0 | 0 |
| `apparatus_effort` | 34 | 34 | 34 | 0 |
| `apparatus_effort_v4` | 30 | 30 | 30 | 0 |

Important implication: the DB already has substantial post-cutoff
Metaculus/Polymarket material, but the current Law 3 second-source blocker is
pre-cutoff **resolution-date** supply, not merely open-date supply.

The 2026-06-02 public Polymarket acquisition probe partly unblocks that supply
problem without changing DB state. It found 33 / 33 requested Polymarket
pre-cutoff candidate rows with a CLOB history price at or before the seven-day
pre-resolution freeze datetime. The first selected manifest spanned 25 event
families and carried 16 sibling-family duplicate flags. Rerunning the strict
max-one-row-per-event-family cap over the full 296-row candidate pool fills
33 / 33 target rows with 33 unique event families. The rerun review removes
sibling-duplicate flags but remains not DB-ready: 33 / 33 rows require manual
review because the public Gamma payload lacks a structured resolution-source
URL. A separate manual provenance packet shows all 33 final outcome prices agree
with `y_known`. A bounded platform-resolver decision preview accepted all 33
rows under an explicit caveat -- Polymarket resolved outcome plus market-page
criteria text, not independent external-source verification -- and inserted
them into the calibration DB.

## Ingest Discipline

All forecasting games should use the same tables:

1. create or reuse a `contracts` row;
2. create a `pilot_runs` row for the dispatch;
3. insert one `pilot_calls` row per model-family emission;
4. compute Brier only from canonical `contracts.y_known`;
5. keep raw traces/JSONL as receipts, not alternate claim stores.

Nonstandard legacy ledgers must be explicitly mapped through:

- `projects/llm_forecasting_calibration_program/tools/ingest_nonstandard_ledgers.py`
- `projects/llm_forecasting_calibration_program/tools/backfill_orphan_contracts.py`
- `projects/llm_forecasting_calibration_program/tools/canonicalize_db_semantics.py`
- `projects/llm_forecasting_calibration_program/tools/master_db_hygiene.py`
- `projects/llm_forecasting_calibration_program/tools/fred_ingest_workspace_results.py`

Run hygiene with:

```bash
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/master_db_hygiene.py \
  --out-dir projects/llm_forecasting_calibration_program/master_db_hygiene/workspace
```

## Statistical Discipline

Reusable statistics live in `src/ztare/experiment_stats.py`:

- `n_required_for_rho`
- `detectable_rho_at_n`
- `n_required_for_brier_delta`
- `bootstrap_ci`
- `paired_permutation_test`
- `spearman_rho`
- `spearman_rho_with_ci`
- `tost_equivalence`
- `bh_fdr`
- `power_aware_verdict`
- `bf_bic_paired_t`

Verdict vocabulary:

- `h1_supported`: clears the predeclared effect and power bar in the predicted
  direction.
- `h0_kept`: equivalent within the predeclared no-effect bound.
- `inconclusive_underpowered`: everything else.

Do not treat `p > 0.05` as no effect.

## Law 3 Cutoff Discipline

For the cutoff/source-currency law:

- `cutoff_relation` is computed from **resolution date vs model cutoff date**;
- `freeze_datetime_value` or historical market probability is a base-rate /
  matching field, not the cutoff relation;
- `market_info_open_datetime` is an adjacent source-exposure/market-age field,
  not a substitute for the Law 3 resolution-date test;
- stored `contracts.post_training_cutoff` can be stale and must be checked
  against computed relation in Law 3 reports.

Current Law 3 executable surfaces:

```bash
PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast cutoff-panel-score \
  --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace

PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast cutoff-base-rate-join \
  --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace

PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast cutoff-missing-sensitivity \
  --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace

PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast cutoff-second-source-audit \
  --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace

PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast cutoff-second-source-void \
  --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
```

Current second-source audit outputs:

- `cutoff_second_source_slate_audit_report.md`
- `cutoff_second_source_resolved_manifest.jsonl`
- `cutoff_second_source_pre_cutoff_acquisition_targets.jsonl`
- `cutoff_second_source_void_miner_report.md`
- `cutoff_polymarket_pre_cutoff_acquisition_report.md`
- `cutoff_polymarket_pre_cutoff_candidate_manifest.jsonl`
- `cutoff_polymarket_candidate_review_report.md`
- `cutoff_polymarket_candidate_ingest_contract_rows.jsonl`
- `cutoff_polymarket_event_family_cap_report.md`
- `cutoff_polymarket_event_family_cap_selected.jsonl`
- `metaculus_api_access_probe_2026_06_03.md`
- `cutoff_general_source_cec_packet.md`
- `fred_forecastbench_manifest_audit.md/json`
- `fred_pre_cutoff_companion_manifest.md/json`
- `fred_cutoff_pair_packet.md/json`
- `fred_cutoff_pair_dispatch_queue.jsonl`
- `fred_cutoff_pair_calls.jsonl`
- `fred_cutoff_pair_score_report.md/json`
- `fred_blinded_value_control_packet.md/json`
- `fred_blinded_value_control_dispatch_queue.jsonl`
- `fred_blinded_value_control_calls.jsonl`
- `fred_blinded_value_control_score_report.md/json`
- `fred_ingest_workspace_results.py`
- `fred_vintage_timing_audit.md/json`
- `fred_vintage_timing_audit_rows.jsonl`
- `fred_vintage_bulk_repair.md/json`
- `fred_vintage_bulk_repair_rows.jsonl`
- `fred_vintage_rescore.md/json`
- `fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.md/json`
- `dataset_label_time_gate.md/json`
- `dataset_label_time_gate_rows.jsonl`
- `source_currency_gate.md/json`
- `source_currency_gate_rows.jsonl`

The target manifest has 16 source/probability/length cells totaling 50 desired
pre-cutoff non-Manifold rows. The void miner reports a full local deficit:
0 resolved pre-cutoff rows available against that 50-row target. The
Polymarket public CLOB probe fills the 33-row Polymarket acquisition slice.
Over the full 296-row candidate pool, strict event-family capping fills the
33-row Polymarket target with 33 unique event families, the manual provenance
packet confirms final outcome prices match `y_known` for all 33, and the
platform-resolver decision preview inserted all 33 reviewed rows into the DB.
Those rows do not replace the remaining Metaculus target cells. The
authenticated Metaculus API probe and credential-correct reprobe verified the
current endpoint and `Authorization: Token` header, with credentials loaded
from `.env`. The available token tier can read post/question payloads but does
not expose resolved Yes/No values or dated aggregate history in the probed
fields; the earlier data-download check returned restricted/403 and the
bounded reprobe hit Cloudflare 429. The capability evidence packet therefore
treats Metaculus bot-benchmarking/data-download access or a licensed export as
the existing-target route; FRED/yfinance-style dataset rows are allowed only as
a separate frozen source-currency replication design, not as a drop-in
substitute for the Metaculus source/freeze-probability/length manifest. A
credential-aware FRED probe on 2026-06-04 confirmed the FRED key loads and
11/12 sampled DB contracts return API data, with 7/12 carrying observations
on/before and after the existing freeze date. That verifies source access, not
manifest readiness or a human/market baseline. A follow-up FRED ForecastBench
manifest audit then mechanically joined the frozen question/resolution bundle
to official FRED observations: 49/50 rows were scoreable, 49/49 computed
outcomes matched the bundled `resolved_to` values, and all scoreable rows were
post-cutoff by resolution date. A fixed one-year historical companion supplied
49/49 scoreable pre-cutoff rows under the same observation rule. The resulting
FRED pair packet froze 49 paired series / 98 contracts and ran Gemini+DeepSeek
on 196/196 schema-ok tool-free calls. The scored paired post-minus-pre Brier is
`+0.016477` with 90% CI `[-0.006445,+0.043330]` and sign-flip p=`0.30375`;
the relation-specific empirical YES-rate baseline beats the model mean
(`0.213244` vs `0.226225`). These 98 FRED contracts and 196 calls are now
DB-ingested under `fred_forecastbench_manifest_2026_06_04`,
`fred_pre_cutoff_companion_2026_06_04`, and
`fred_cutoff_pair_tool_free_v1`.
A follow-up diagnostic control selected 24 outcome-balanced FRED series, hid
the cutoff relation from the prompt, and added a due-date-observed-value arm.
It ran 192/192 schema-ok Gemini+DeepSeek calls. The paired post-minus-pre Brier
is `+0.024719`, 90% CI `[+0.007125,+0.043730]`, sign-flip p=`0.02315`.
Because outcomes were used to construct the balanced diagnostic subset, this
control is a confound audit rather than a natural-distribution estimate. The
192 control calls are DB-ingested under `fred_blinded_value_control_v1`.
A no-call vintage timing audit then queried FRED with real-time
`realtime_start` / `realtime_end` dates. The first pass found `58/98`
vintage-scoreable rows before HTTP 429 rate limits. A follow-up bulk-vintage
repair used FRED `series/observations` with `output_type=2` and
`vintage_dates`, batching once per series, and reached `98/98`
vintage-scoreable rows with `49/49` series API-ok. Under label-time values,
`49/98` due values changed as-of due, `44/98` resolution values changed
as-of resolution, and `15/98` two-point real-time labels changed. Rescoring
existing calls on the complete repaired label set gives pair-panel
post-minus-pre Brier `+0.018721` under vintage labels, with mean Brier
worsening from `0.226225` current-label to `0.233266`; the blinded-control
current-label penalty collapses from `+0.024719` to `-0.002989` under vintage
labels. The DB rows remain queryable current-FRED-label artifacts, but they
should not be used as positive source-currency evidence.
A reusable dataset-source label-time gate now audits this condition over the
calibration DB. It finds `165` dataset-source rows, `108` resolved
dataset-source rows, `83` current-label rows supported by available
source-specific label-time receipts, and `25` ineligible current-label rows:
`15` FRED labels changed under vintage repair, while `10` yfinance/yfinance_etf
rows lack label-time receipts. The gate does not mutate the model-call tables,
but its row-level eligibility classifications are DB-ingested into
`dataset_label_time_gate_rows` when run with `--ingest-db`.
The same refresh also installs two SQL views: `v_label_time_eligible_contracts`
and `v_policy_scoreable_calls`. The 2026-06-04 F100 calibrator rerun now uses
`v_policy_scoreable_calls` by default. This excludes the `10` complete
yfinance/yfinance_etf panels lacking label-time receipts from the legacy
`142`-panel public-domain audit, leaving `132` policy-scoreable panels over
Manifold, Polymarket, and Kalshi. The verdict is unchanged:
source-isotonic remains `calibrator_not_promoted` (`-0.005248` Brier vs
confident-NO, paired p=`0.7099`), while raw mean-panel remains worse than
confident-NO (`+0.029598`, p=`0.0062`).
The F100 source-currency stress audit now also computes cutoff relation through
`classify_forecast_source_currency` rather than local fallback logic. On the
Stage-B panel this leaves the scores unchanged, but it records
cutoff-relation provenance and exposes `39 / 240` stored-flag-vs-computed
relation conflicts. Policy audits should consume the computed receipt when a
resolution date and panel cutoff date are available.
A reusable source-currency gate now materializes the same primitive into the
calibration DB. On `cutoff_stage_b_panel_v1`, `source_currency_gate_rows`
contains `240` call-level receipts, with `120` computed pre-cutoff rows, `120`
computed post-cutoff rows, and `39` stored/computed conflicts. It also installs
`v_source_currency_gate_conflicts` and `v_policy_scoreable_calls_source_currency`
so downstream audits can join computed cutoff receipts instead of re-consuming
`contracts.post_training_cutoff`.

### Stage-C Market Baseline

The narrow Stage-C Manifold market bar is DB-ingested as
`market_baseline_stage_c_v1`:

- condition: `stage_c_preoutcome_market_probability`
- family / agent: `manifold_market`
- role: `preoutcome_market_bar`
- rows: 51 / 51 schema-ok
- typed table/view: `external_baseline_observations` /
  `v_external_market_baselines`
- equal-information flag: `0 / 51`
- report:
  `projects/llm_forecasting_calibration_program/truth_continuation_v1/workspace/market_baseline_stage_c_report.md`

This is a pre-outcome market probability baseline, usually seven days before
resolution. It is not a broad equal-information human/crowd baseline and must
not be described that way.

A scoped market+LLM blend audit is also available:

- report:
  `projects/llm_forecasting_calibration_program/truth_continuation_v1/workspace/market_llm_blend_stage_c_2026_06_03/market_llm_blend_stage_c_report.md`
- baseline source: `v_external_market_baselines`
- rows: 51 joined contracts, 153 same-contract LLM calls
- equal-information baseline rows: `0`; not-equal-information rows: `51`
- market-alone Brier: `0.099673`
- LLM panel mean-probability Brier: `0.140459`
- fixed 50/50 blend Brier: `0.094480`
- leave-one-out tuned-grid blend Brier: `0.097218`
- leave-one-out tuned-grid delta vs market: `-0.002455`, paired p=`0.794`,
  CI `[-0.021, +0.0166]`, n_required=`12334`
- post-cutoff subset: market-only remains best (`0.085272`)
- verdict: `not_deployable_post_cutoff_prefers_market_only`

The companion effective-N audit is:

- report:
  `projects/llm_forecasting_calibration_program/truth_continuation_v1/workspace/market_llm_effective_n_stage_c_2026_06_03/market_llm_effective_n_stage_c_report.md`
- matched evidence unit: 51 contracts, not platform-level market users and not
  153 LLM calls
- outcome mix: 17 YES / 34 NO
- market rows with Brier `<0.05`: 32 / 51
- post-cutoff subset: market Brier `0.085272` vs LLM panel mean-probability
  Brier `0.285093`, paired p=`0.0034`
- fixed 50/50 blend on post-cutoff rows is worse than market-only, paired
  p=`0.0108`

Interpretation: the aggregate blend is a narrow within-Manifold hypothesis
generator, not a human/crowd superiority result. The paired test and
post-cutoff split fail the promotion gate. The market probability
aggregates many traders and changing information flows; the LLM comparator is a
small frozen prompt panel. The post-cutoff split is the deployment-relevant
warning: in the clean source-valid subset, adding the LLM panel does not improve
the grid result over market-only.

## Nurture / Intervention Discipline

Broad action prompting is not promoted. N2 failed confirmation:

- pilot: `n2_selective_action_confirmatory_v1`
- rows in DB: 71
- mean paired Brier delta: `+0.025779`
- paired permutation: `p=0.5649`
- mean utility: `-0.205882`

Later intervention smokes demote the automatic self-repair path:

- N3: high-worry action policy exposed construct-validity problems.
- N4: decision-only action policy failed its first utility smoke.
- N5: naive base-rate/reference-class repair overcorrected downward.
- N6: selection-aware repair overcorrected upward on a negative high-tail row.
- N7: guarded selection-aware repair ran a balanced 16-row smoke; it prevented
  the N6 overcorrection mode but mostly became a no-op and worsened pooled
  Brier (`+0.031079`, `n=8` paired).
- F118/N8: diagnostic-triggered allocation over 142 complete-five v28a panels
  loses to confident-NO mean-panel.
- N9: carrier-vs-prose ran a 32-row Codex smoke. Free prose worsened Brier
  (`+0.068441`, p=`0.238`); typed carrier weakly improved Brier
  (`-0.012225`, p=`0.8276`) and beat free prose on mean, but the
  carrier-to-action arm only tied the threshold-abstain utility control. Treat
  as underpowered continuation evidence, not a law claim.
- N10: hard-prompt-break ran paired Codex and Claude smokes. The first two
  smokes were directionally favorable to structured carrier fields over prose
  (`0.098425` same-turn typed carrier, `0.103278` hard break, `0.146103` free
  prose, `0.171038` baseline over 8 rows). The later two-call placebo-control
  continuation did not replicate that broader intervention story: among 30
  schema-valid rows, baseline mean Brier was `0.078000`, two-call prose
  `0.107254`, same-turn carrier `0.110300`, free prose `0.122767`, and hard
  break `0.149921`; 10 Codex rows failed at runtime before forecasts. Treat the
  carrier lane as a hypothesis only; hard-break-beyond-carrier is not confirmed.

Current applied rule:

- Do not claim an automatic correction policy from worry/tail-risk.
- The strongest practical DB rule is confident-NO mean-panel, now exposed by
  forecast-pool aggregation as `aggregate.confident_no_adjusted_p_success`
  while preserving the raw `aggregate.p_success`. Treat it as a calibrated view
  for live/source-valid rows with time-valid labels/baselines, not as a
  correction for retrospective or current-label dataset benchmarks.
- Deterministic rationale compression/NCD was tested as a candidate
  routing/escalation proxy on paired v28a/v28i external rows. It did not
  promote: inversion helped mean Brier, but NCD did not explain where it
  helped.
- Graph-family nearest-neighbor weighting was tested on complete-five v28a
  public-domain panels. It is suggestive but not deployed: graph+confident-NO
  slightly beat confident-NO, but the lift was small and source/hash-control
  fragile.
- A costed review-allocation audit tested diagnostic channels as triage
  features rather than probability repair. Oracle-family review shows headroom,
  but realistic train-fold proxy reviewers do not promote: the best non-oracle
  policy improves costed Brier by only `0.006156` over F100 and is
  non-significant.
- Nurture prompt failures are scoped by construct validity. A cross-pilot audit
  demotes the tested tool-free prompt families, but does not rule out
  tool-using, interactive, retrieval-grounded, expert-written, or heldout-tuned
  prompt programs.
- Use diagnostic channels as behavioral error-readouts unless a costed review
  allocation policy beats explicit controls.
- Use old stochastic contract rows for no-call policy audits first; spend new
  N=xx multi-family calls when the no-call audit leaves a discriminating
  uncertainty and the packet has source-valid rows plus fixed promotion/kill
  criteria.

Runnable surfaces:

```bash
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/rationale_compression_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/graph_family_interaction_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/nurture_prompt_design_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/diagnostic_triggered_allocation_audit.py \
  --out-dir projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/diagnostic_review_allocation_audit.py

PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast nurture-score \
  --pilot-id n7_guarded_selection_aware_repair_v1 \
  --queue projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace/n7_guarded_selection_aware_repair_combined_dispatch_queue.jsonl \
  --out-dir projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace
```

## Runnable Surfaces

Preferred public CLI invocation for forecast-pool operations and experiment
execution:

```bash
PYTHONPATH=. ./venv/bin/python -m src.ztare.cli forecast <verb> [args...]
```

Public CLI verbs intentionally kept user-facing:

- `pool`
- `resolve`
- `calibration-stats`
- `calibration-db`
- `score`
- `ingest-smoke`
- `cutoff-panel-run`
- `cutoff-panel-ingest`
- `cutoff-panel-score`
- `anti-bias-run`
- `anti-bias-score`
- `nurture-run`
- `nurture-ingest`
- `nurture-score`
- `elo-refresh`
- `brier-elo`
- `resolve-open-metaculus`

Project-local research scripts remain reproducible but are not public CLI
verbs. Examples include paper-readiness, law-readiness, F105 sibling analysis,
truth-frontier ranking, packet generation, and construct-validity audits.
Recent no-call audit surfaces:

```bash
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/f47_paired_delta_reaudit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/f47_contrastive_policy_consumer_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/f47_source_balanced_consumer_packet.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/f47_source_balanced_consumer_dispatch.py --smoke --families gemini,deepseek --max-pairs 2

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/f47_source_balanced_consumer_score.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/f47_production_readiness_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/channel_only_classifier_reaudit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/fred_vintage_bulk_repair.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/fred_vintage_rescore.py --audit projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/fred_vintage_bulk_repair_2026_06_04/fred_vintage_bulk_repair.json --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/dataset_label_time_gate.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/source_currency_gate.py --pilot-id cutoff_stage_b_panel_v1

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_acquisition_run.py --sleep-ms 150

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_export_packet.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_result_ingest.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/forecasting_science_spine_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/max_truth_frontier_report.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/paper_readiness_exhaustion_audit.py
```

Project-local tools live in:

`projects/llm_forecasting_calibration_program/tools/`

Reusable forecast-pool infrastructure lives in:

`scripts/public/control/forecast/`

## Public Surface Contract

The public folder is intentionally small:

- `CLAIM_SUMMARY.md` — current science state, law status, non-claims, and next
  truth-seeking queue.
- `METHODOLOGY.md` — this DB/tooling/statistics contract.

Detailed evidence remains in workspace reports and the append-only research
log. Do not create new public protocol files unless they replace one of the two
primary public documents.
