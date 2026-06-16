---
description: "Methodology, canonical database, and tooling contract for the GP-245 LLM forecasting calibration program."
---
# GP-245 Forecasting Calibration — Methodology / DB Contract

Updated 2026-06-16.

This is the public methodology and database contract for the GP-245 forecasting
program. Scientific claims and current claim status live in `CLAIM_SUMMARY.md`.

## Canonical Database

Canonical DB:

`analytics/public/calibration/forecaster_calibration.db`

Current DB snapshot:

- contracts: `2,207`
- pilot runs: `162`
- pilot calls: `20,294`
- schema-ok calls: `19,650`
- calls with Brier: `11,093`
- resolved contracts: `549`

The DB is public evidence, not private scratch. Raw JSONL files are supporting records,
but claims must be queryable through the canonical tables unless a report
explicitly says it is a stored-row/no-DB readiness audit.

### Tables

- `contracts(contract_id PK, question, source, source_corpus, horizon,
  y_known, post_training_cutoff, task_type, external_market_open,
  resolution_source_url, y_known_provenance, raw_json, created_at)`
  - one row per question/task/event surface;
  - `y_known in {0,1}` only when the outcome is resolved and binary;
  - `y_known = NULL` is allowed for unresolved or non-binary games;
  - `post_training_cutoff` is a stored flag and can be stale for source-currency claim audits.
- `pilot_runs(pilot_id PK, pilot_name, primitive, corpus, source_jsonl_path,
  fired_at, n_calls, n_schema_ok, ...)`
  - one row per dispatch/run.
- `pilot_calls(call_id PK, pilot_id, contract_id, agent_id, family, condition,
  primitive, primitive_base, phase, role, pair_id, p_success, brier, schema_ok,
  parsed_json, fired_at, raw_json, ...)`
  - one row per model-family emission;
  - `brier = (p_success - y_known)^2` when `y_known` is binary;
  - channel fields such as worry, confidence, placebo, bid-ask, action choice, or
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
| `bias_transfer_ood` | 435 | 0 | 0 | 0 |
| `NULL` | 309 | 30 | 0 | 0 |
| `polymarket` | 168 | 74 | 33 | 127 |
| `legacy_orphan_backfill` | 163 | 0 | 0 | 0 |
| `fred` | 139 | 98 | 49 | 79 |
| `manifold` | 124 | 116 | 27 | 89 |
| `metaculus` | 72 | 0 | 0 | 60 |
| `premium_public_clean` | 71 | 71 | 0 | 0 |
| `f105_metacognition` | 45 | 45 | 0 | 0 |
| `workflow_effort` | 34 | 34 | 34 | 0 |
| `workflow_effort_v4` | 30 | 30 | 30 | 0 |

Important implication: the DB already has substantial post-cutoff
Metaculus/Polymarket material, but the current source-currency claim second-source blocker is
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
5. keep raw traces/JSONL as supporting records, not alternate claim stores.

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

Verdict vocabulary used by the scoring scripts:

- supported: clears the predeclared effect and power bar in the predicted
  direction.
- equivalent: equivalent within the predeclared no-effect bound.
- underpowered or inconclusive: everything else.

Do not treat `p > 0.05` as no effect.

## source-currency claim Cutoff Discipline

For the cutoff/source-currency claim:

- `cutoff_relation` is computed from **resolution date vs model cutoff date**;
- `freeze_datetime_value` or historical market probability is a base-rate /
  matching field, not the cutoff relation;
- `market_info_open_datetime` is an adjacent source-exposure/market-age field,
  not a substitute for the source-currency claim resolution-date test;
- stored `contracts.post_training_cutoff` can be stale and must be checked
  against computed relation in source-currency claim reports.

Current source-currency claim executable surfaces:

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
A stored-row vintage timing audit then queried FRED with real-time
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
labels. The DB rows remain queryable current-FRED-label records, but they
should not be used as positive source-currency evidence.
A reusable dataset-source label-time screen now audits this condition over the
calibration DB. It finds `165` dataset-source rows, `108` resolved
dataset-source rows, `83` current-label rows supported by available
source-specific label-time records, and `25` ineligible current-label rows:
`15` FRED labels changed under vintage repair, while `10` yfinance/yfinance_etf
rows lack label-time records. The screen does not mutate the model-call tables,
but its row-level eligibility classifications are DB-ingested into
`dataset_label_time_gate_rows` when run with `--ingest-db`.
The same refresh also installs two SQL views: `v_label_time_eligible_contracts`
and `v_policy_scoreable_calls`. The 2026-06-04 low-probability calibration rerun now uses
`v_policy_scoreable_calls` by default. This excludes the `10` complete
yfinance/yfinance_etf panels lacking label-time records from the legacy
`142`-panel public-domain audit, leaving `132` policy-scoreable panels over
Manifold, Polymarket, and Kalshi. The verdict is unchanged:
source-isotonic remains unsupported (`-0.005248` Brier vs
low-probability adjustment, paired p=`0.7099`), while raw mean-panel remains worse than
low-probability adjustment (`+0.029598`, p=`0.0062`).
The low-probability adjustment source-currency stress audit now also computes cutoff relation through
`classify_forecast_source_currency` rather than local fallback logic. On the
Stage-B panel this leaves the scores unchanged, but it records
cutoff-relation provenance and exposes `39 / 240` stored-flag-vs-computed
relation conflicts. Policy audits should consume the computed row when a
resolution date and panel cutoff date are available.
A reusable source-currency screen now materializes the same classifier into the
calibration DB. On `cutoff_stage_b_panel_v1`, `source_currency_gate_rows`
contains `240` call-level rows, with `120` computed pre-cutoff rows, `120`
computed post-cutoff rows, and `39` stored/computed conflicts. It also installs
`v_source_currency_gate_conflicts` and `v_policy_scoreable_calls_source_currency`
so downstream audits can join computed cutoff rows instead of re-consuming
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
- equal-information baseline rows in this Stage-C overlap: `0`; not-equal-information rows: `51`
- market-alone Brier: `0.099673`
- LLM panel mean-probability Brier: `0.140459`
- fixed 50/50 blend Brier: `0.094480`
- leave-one-out tuned-grid blend Brier: `0.097218`

The separate Polymarket equal-information acquisition currently has 4 / 24
valid requested rows ingested under `equal_information_polymarket_baseline_v1`
with `equal_information_flag=1`. It is not part of the 51-row Stage-C Manifold
overlap and is still below the broad comparison threshold. A feasibility audit
classifies the remaining 20 / 24 rows as
`market_not_open_by_target_freeze`. A fixed day-horizon sweep over 7, 5, 3, 2,
1, and 0 days before resolution joins 4, 6, 9, 12, 12, and 12 rows
respectively; no tested day horizon fully rescues this packet. The next
equal-information experiment now has a baseline-only replacement packet: the
2026-06-15 acquisition scanned 800 closed post-cutoff Polymarket markets,
probed 81 CLOB histories, found 80 eligible candidates, and selected 24
one-per-event rows at a 2-day horizon. Outcome mix is 14 NO / 10 YES, with 16
selected freeze prices in `0.00-0.10` and 8 in `0.90-1.00`. The 24 replacement
market baselines are now ingested under
`equal_information_replacement_polymarket_baseline_v1`. The completed Claude,
Codex, Gemini, and DeepSeek model rows are ingested under
`equal_information_replacement_model_forecast_v1` and score as a same-information
market comparison favoring the market: Claude mean Brier `0.233184`, Codex mean Brier `0.264409`,
Gemini mean Brier `0.304696`, DeepSeek mean Brier `0.334775`, all model-call
mean Brier `0.284266`, four-family mean-probability panel Brier `0.267758`,
Polymarket mean Brier `0.072964`, panel-minus-market `+0.194794`, paired
permutation p=`0.0068`, n=`24` contracts / `96` model calls. This is not
evidence that LLMs beat markets.

A non-Polymarket Manifold acquisition now supplies the independent-source
comparison. The corrected packet selects 24 post-cutoff Manifold contracts
from local resolved rows that do not already have equal-information external
baseline observations: 15 NO / 9 YES. The public Manifold API fill validates
all 24 rows with a timestamped market-history probability at or before the
two-day pre-resolution freeze date plus an outcome-mapping record, and the
rows are DB-ingested under `equal_information_manifold_history_baseline_v1`.
Mean Manifold market Brier is `0.160977`. Against existing same-contract
five-family model calls, the selected full-coverage model pilot
`v28stake_full__v25_external::low` has model-panel Brier `0.198723`, Manifold
market Brier `0.160977`, panel-minus-market `+0.037746`, paired p=`0.5431`,
n=`24`. This satisfies the second-source acquisition check, but it is
post-hoc, favors the market, and is inconclusive; it is not evidence that LLMs beat
markets.
- leave-one-out tuned-grid delta vs market: `-0.002455`, paired p=`0.794`,
  CI `[-0.021, +0.0166]`, n_required=`12334`
- post-cutoff subset: market-only remains best (`0.085272`)
- verdict: `post_cutoff_prefers_market_only`

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
post-cutoff split fail the support check. The market probability
aggregates many traders and changing information flows; the LLM comparator is a
small frozen prompt panel. The post-cutoff split is the deployment-relevant
warning: in the clean source-valid subset, adding the LLM panel does not improve
the grid result over market-only.

## Prompt Intervention Discipline

Broad action prompting is unsupported. The confirmatory selective-action test failed:

- pilot: `n2_selective_action_confirmatory_v1`
- rows in DB: 71
- mean paired Brier delta: `+0.025779`
- paired permutation: `p=0.5649`
- mean utility: `-0.205882`

Later intervention checks narrow the automatic self-repair path:

- High-worry action policy exposed construct-validity problems.
- Decision-only action policy failed its first utility check.
- Naive base-rate/reference-class repair overcorrected downward.
- Selection-aware repair overcorrected upward on a negative high-tail row.
- Guarded selection-aware repair ran a balanced 16-row check; it prevented
  the earlier overcorrection mode but mostly became a no-op and worsened pooled
  Brier (`+0.031079`, `n=8` paired).
- Diagnostic-triggered allocation over 142 complete-five panels
  has higher Brier than the mean-panel with the low-probability adjustment.
- Structured-fields versus prose ran a 32-row Codex check. Free prose worsened Brier
  (`+0.068441`, p=`0.238`); structured fields weakly improved Brier
  (`-0.012225`, p=`0.8276`) and beat free prose on mean, but the
  structured-fields-to-action arm only tied the threshold-abstain utility control. Treat
  as underpowered continuation evidence, not a supported claim.
- Hard-prompt-break ran paired Codex and Claude checks. The first two
  checks were directionally favorable to structured fields over prose
  (`0.098425` same-turn structured fields, `0.103278` hard break, `0.146103` free
  prose, `0.171038` baseline over 8 rows). The later two-call placebo-control
  continuation did not replicate that broader intervention claim: among 30
  schema-valid rows, baseline mean Brier was `0.078000`, two-call prose
  `0.107254`, same-turn structured fields `0.110300`, free prose `0.122767`, and hard
  break `0.149921`; 10 Codex rows failed at runtime before forecasts. Treat the
  structured-fields lane as a hypothesis only; hard-break-beyond-structured-fields is not confirmed.

Current applied rule:

- Do not claim an automatic correction policy from worry/tail-risk.
- The strongest practical DB rule is mean-panel with the low-probability adjustment, now exposed by
  forecast-pool aggregation as `aggregate.confident_no_adjusted_p_success`
  while preserving the raw `aggregate.p_success`. Treat it as a calibrated view
  for live/source-valid rows with time-valid labels/baselines, not as a
  correction for retrospective or current-label dataset benchmarks.
- Deterministic rationale compression/NCD was tested as a candidate
  allocation/escalation proxy on paired external rows. It was not
  supported: inversion helped mean Brier, but NCD did not explain where it
  helped.
- Graph-family nearest-neighbor weighting was tested on complete-five
  public-domain panels. It is suggestive but not ready for use as an automated rule:
  graph plus low-probability adjustment
  slightly beat low-probability adjustment, but the lift was small and source/hash-control
  fragile.
- A costed review-allocation audit tested diagnostic channels as triage
  features rather than probability repair. Best-family review shows headroom,
  but realistic train-fold proxy reviewers do not yet support an applied rule: the best non-best-family
  policy improves costed Brier by only `0.006156` over low-probability adjustment and is
  non-significant.
- Prompt-intervention failures are scoped by construct validity. A cross-pilot audit
  narrows the tested tool-free prompt families, but does not rule out
  tool-using, interactive, retrieval-grounded, expert-written, or heldout-tuned
  prompt programs.
- Use diagnostic channels as behavioral error-readouts unless a costed review
  allocation policy beats explicit controls.
- Use old stochastic contract rows for stored-row policy audits first; spend new
  multi-family calls only when the stored-row audit leaves a discriminating
  uncertainty and the packet has source-valid rows plus fixed support/stop
  criteria.

Runnable surfaces:

```bash
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/rationale_compression_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/graph_family_interaction_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/diagnostic_triggered_allocation_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/diagnostic_review_allocation_audit.py
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
- `ingest-check`
- `cutoff-panel-run`
- `cutoff-panel-ingest`
- `cutoff-panel-score`
- `anti-bias-run`
- `anti-bias-score`
- `elo-refresh`
- `brier-elo`
- `resolve-open-metaculus`

Project-local research scripts remain reproducible but are not public CLI
verbs. Examples include paper-readiness, claim-readiness, objective-effort sibling analysis,
truth-frontier ranking, packet generation, and construct-validity audits.
Recent stored-row audit surfaces include pairwise ranking re-audits, source-balanced
ranking packets, translation-readiness checks, channel-only classifier audits,
FRED vintage repair/rescoring, label-time screens, source-currency screens, and
equal-information baseline acquisition. The field-wide validity-audit protocol
adds the external benchmark-family schema and seed matrix needed before making a
field-wide prevalence claim. The companion local-evidence script preserves the
Halawi date-distribution warning from the claim register while marking it as a
summary only, not a raw-row external audit. The historical script filenames in
`projects/llm_forecasting_calibration_program/tools/` retain their old
experiment prefixes; the public claim names above are the canonical reader-facing
names.

```bash
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/channel_only_classifier_reaudit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/fred_vintage_bulk_repair.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/fred_vintage_rescore.py --audit projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/fred_vintage_bulk_repair_2026_06_04/fred_vintage_bulk_repair.json --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/dataset_label_time_gate.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/source_currency_gate.py --pilot-id cutoff_stage_b_panel_v1

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_acquisition_run.py --sleep-ms 150

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_export_packet.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_result_from_post_probe.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_baseline_result_ingest.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_freeze_feasibility_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_horizon_sweep.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_replacement_sample_acquire.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_replacement_dispatch_packet.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_replacement_contract_ingest.py --commit

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/equal_information_replacement_score.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_export_packet.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_result_acquire.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_result_ingest.py --ingest-db --replace

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_score.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/forecasting_science_spine_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/paper_coherence_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/field_wide_validity_audit_protocol.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/field_wide_validity_local_evidence.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/harnessing_thesis_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/independent_equal_information_source_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/manifold_equal_information_reclassification_audit.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/max_truth_frontier_report.py

PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/paper_readiness_exhaustion_audit.py
```

Project-local tools live in:

`projects/llm_forecasting_calibration_program/tools/`

Reusable forecast-pool infrastructure lives in:

`scripts/public/control/forecast/`

## Public Surface Contract

The public folder is intentionally small:

- `CLAIM_SUMMARY.md` — current science state, claim status, non-claims, and next
  truth-seeking queue.
- `METHODOLOGY.md` — this DB/tooling/statistics contract.

Detailed evidence remains in workspace reports and the append-only research
log. Do not create new public protocol files unless they replace one of the two
primary public documents.
