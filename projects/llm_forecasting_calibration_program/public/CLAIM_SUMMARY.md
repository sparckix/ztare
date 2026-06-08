---
description: "Public science-state summary for the GP-245 LLM forecasting calibration program."
---
# GP-245 Forecasting Calibration — Science State

Updated 2026-06-04.

This is the public science-state surface for the GP-245 LLM forecasting
calibration program. It replaces the older split set of law matrices, protocol
notes, and frontier scans. Methodology, database schema, ingestion, and tooling
live in `METHODOLOGY.md`.

## Current Claim

The program does **not** show that "LLMs forecast well" in general. The current
claim is narrower and stronger:

> LLM forecasting quality is representation-conditioned. It depends on whether
> the task is source-current for the model generation, which model family is
> queried, which auxiliary elicitation channel is used, and whether a proposed
> intervention is scored against explicit controls.

The cleaner program frame is evidence-function-first. Six buckets now govern
what gets called, scored, or promoted:

1. **Validity.** Decide whether a row can count as forecast evidence for this
   model generation: source/cutoff visibility, dataset label-time receipts,
   contamination, and equal-information scope.
2. **Calibration.** Transform valid probabilities only when the transform
   improves a proper score against controls. F100 confident-NO is the current
   live candidate under source-valid, forward-looking scope.
3. **Ranking.** Test whether LLMs are better at relative comparisons than
   absolute probabilities. F47 remains bounded to pairwise/tournament and
   experimental translation work.
4. **Allocation.** Decide when to buy outside information, abstain, or route
   across families. Oracle headroom is real; current cheap routers/reviewers
   are not deployable.
5. **External baselines.** Decide whether an LLM or LLM+market system adds
   value beyond market/human bars on matched contract-level evidence.
6. **Inheritance theory.** Explain transfer surfaces such as inherit/escape/
   mimic only after validity and calibration have been separated. It is theory
   and diagnostic design unless it selects a scored actuator.

This yields three active scientific laws plus two companion lanes:

1. **Source-currency / cutoff-validity law.** Forecast benchmarks lose validity
   for a model generation when the resolved answer is already source-visible to
   that generation. This is the strongest current positive result.
2. **Family-conditioned elicited-error law.** Auxiliary channels such as
   worry/tail-risk can expose error risk by family, but diagnostic signal does
   not automatically become a Brier-improving policy.
3. **Bias-transfer / representational-carrier law.** The inherit/escape/mimic
   frame is useful, but the clean anti-bias-collapse mechanism is scoped down
   by raw-gap controls.
4. **No-poolability / routing companion.** Family-by-contract interaction is
   real, but the current routers are source-fragile.
5. **Nurture / intervention companion.** Broad selective-action prompting,
   self-repair, and diagnostic-triggered allocation are demoted. A small
   carrier-vs-prose smoke keeps typed carrier probability elicitation alive,
   but not action execution. The current applied rule is the simple
  confident-NO mean-panel for forward-looking/source-valid rows with
  time-valid labels/baselines until stronger controls beat it.

## Evidence Summary

### Law 3: Source-Currency / Cutoff Validity

**Status:** strongest current paper-grade law, with a clear second-source
limitation.

Evidence:

- Halawi-style re-audit: older forecasting corpora can be structurally
  contaminated for current-generation LLMs when all resolutions precede model
  cutoffs.
- Stage-B matched panel: 240 / 240 schema-valid calls in
  `cutoff_stage_b_panel_v1`, balanced 120 pre-cutoff and 120 post-cutoff rows.
- Aggregate post-minus-pre Brier: `+0.191098`.
- Family deltas all point the same way: Claude `+0.211078`, Codex 5.4-mini
  `+0.157999`, Gemini `+0.204219`.
- Paired-stratum delta: `+0.2155`, permutation `p=0.0004`, CI
  `[0.1584, 0.2795]`.
- Stage-C base-rate join: 51 / 80 contracts joined to pre-outcome probability
  metadata; 27 family/stratum/base-rate-band paired cells still show
  post-minus-pre Brier `+0.255418`.
- Stage-C market baseline audit: the 51 joined pre-outcome Manifold
  probabilities are now DB-ingested as `market_baseline_stage_c_v1` and
  materialized in `external_baseline_observations` /
  `v_external_market_baselines`. All 51 carry `equal_information_flag=0`.
  On the same joined contracts, market mean Brier is `0.099673` versus Claude
  `0.119920`, Codex 5.4-mini `0.160440`, and Gemini `0.220529`.
- Stage-C market+LLM blend audit: on those same 51 rows, the best simple grid
  blend is 70% market / 30% LLM with Brier `0.090417` versus market-alone
  `0.099673`; the stricter leave-one-out tuned-grid Brier is `0.097218`, with
  paired delta `-0.002455`, p=`0.794`, CI `[-0.021, +0.0166]`, and
  n_required=`12334`. The post-cutoff subset prefers market-only, so this is
  not evidence that LLMs robustly add to markets under equal information. The
  2026-06-04 typed-table rerun leaves the verdict unchanged:
  `not_deployable_post_cutoff_prefers_market_only`.
- Effective-N audit: the matched evidence unit is the contract. The local
  market-vs-LLM comparison is `n=51` contracts, not "large market N" versus
  "153 LLM calls." Outcome mix is 17 YES / 34 NO; 32/51 market rows have Brier
  `<0.05`, so low Brier partly reflects an easy/narrow slice. In the 19-row
  post-cutoff subset, market Brier is `0.085272` versus LLM panel
  mean-probability Brier `0.285093` with paired p=`0.0034`; fixed 50/50
  blending is worse than market-only with p=`0.0108`.
- Equal-information baseline void audit: the Stage-B LLM panel has 80
  contracts / 240 calls, but only 51 contracts have an ingested market/human
  baseline, all from Manifold. The verdict is
  `broad_equal_information_baseline_absent`; broad LLM-vs-human/market or
  LLM+market claims need matched contract-level baselines across at least two
  independent sources.
- The split is mechanism-relevant: post-cutoff rows favor the market bar
  strongly (`0.085272` vs LLM calls `0.309513`), while pre-cutoff rows favor
  the LLM calls (`0.108224` market vs `0.082323` LLM calls). This is why
  pre-cutoff rows are not forward-looking benchmark evidence.
- F115 missing-band sensitivity: adversarially assigning the 29 unjoined
  contracts to possible base-rate bands leaves the effect positive at
  `+0.127901`.

Remaining falsifier:

- Second-source replication. The 2026-06-02 Metaculus/Polymarket audit found
  146 candidates, 130 joined resolution rows, and 50 resolved rows, but `0`
  resolved pre-cutoff rows by **resolution date** in the original local join.
- The corrected void miner now subtracts DB-ingested reviewed acquisition rows
  by source/freeze-band/question-length cell. It recognizes the 33 Polymarket
  pre-cutoff rows as filled and reports a remaining target deficit of 17
  Metaculus rows.
- The audit emits a 16-cell acquisition target manifest totaling 50 matched
  pre-cutoff non-Manifold rows:
  `cutoff_validity_v1/workspace/cutoff_second_source_pre_cutoff_acquisition_targets.jsonl`.
- A public Polymarket CLOB-history acquisition probe now fills the current
  Polymarket slice of that target: full-pool cap-aware selection gives 33 / 33
  selected pre-cutoff rows across 33 event families, all with a CLOB history
  price at or before the seven-day pre-resolution freeze datetime.
- The cap-aware review found 33 / 33 manual-review rows because the public
  Gamma payload lacks a structured resolution-source URL. A manual provenance
  packet shows all 33 final outcome prices agree with `y_known`; a bounded
  platform-resolver review accepted all 33 rows and inserted them into the
  calibration DB. This does not claim independent external-source verification,
  and these rows do not replace the need for the remaining Metaculus target
  cells.
- Bounded live Polymarket-only Gemini and DeepSeek smokes then used the
  acquired slice: each landed 48 / 48 schema-ok calls over 24 pre-cutoff and 24
  post-cutoff rows. The raw aggregate supports the Law 3 direction for Gemini
  (`post-minus-pre=+0.246832` Brier) and weakly for DeepSeek (`+0.077758`),
  but the six matched source/topic/length strata are null/opposite-sign:
  Gemini `+0.005731` (`p=0.9696`) and DeepSeek `-0.061706` (`p=0.8836`).
  This is useful smoke evidence, not a source-general replication.
- A follow-up Polymarket base-rate availability probe found the obvious
  market-price control is not executable yet on the frozen slice:
  pre-cutoff rows have 24 / 24 DB `freeze_datetime_value` prices, post-cutoff
  rows have 0 / 24 locally, and a live Gamma/CLOB probe joined 0 / 24 post rows
  because the public Polymarket Gamma/CLOB route resets connections from this
  environment (`[Errno 54] Connection reset by peer`). This leaves
  base-rate/source-topic confounding live rather than resolved.
- An equal-information export packet now makes the blocked acquisition exact:
  24 post-cutoff Polymarket rows, each with slug, market URL, target freeze
  date, outcome, stratum metadata, and required result fields for YES token ID,
  historical YES price, timestamp, source, and outcome mapping. The acceptance
  gate is still zero-filled: these rows must be populated through a reachable
  export/provider route before the Polymarket matched market baseline is
  executable.
- A companion filled-result validator/ingester now defines the return path:
  `valid_rows == requested_rows` and `missing_requested_rows == 0` before any
  equal-information Polymarket rows can enter `external_baseline_observations`
  with `equal_information_flag=1`. Current status remains `0 / 24` valid rows
  because no filled result JSONL exists yet.
- An authenticated Metaculus API correctness probe and a credential-correct
  reprobe used the current `/api/posts/` endpoint with the proper
  `Authorization: Token` header loaded from `.env`. The token can read
  authenticated post/question payloads, but this access tier does not expose
  resolved Yes/No values or aggregate-history/community-prediction fields for
  sampled resolved binary rows. The earlier data-download check returned
  restricted/403; the bounded reprobe hit Cloudflare 429 on that route. The
  remaining Metaculus target therefore requires bot-benchmarking/data-download
  access or a licensed export, not more endpoint guessing.
- A capability-evidence packet rejects FRED/yfinance-style dataset rows as a
  drop-in substitute for the Metaculus target cells. Dataset-source rows may
  open a separate frozen source-currency replication design, but cannot
  silently satisfy the current source/freeze-probability/length manifest.
- A no-call FRED/yfinance slate audit sharpens that boundary: the current
  ForecastBench bundle joins 98 resolved FRED/yfinance rows, all post-cutoff by
  resolution date and 0 pre-cutoff. These rows can supply post-cutoff source
  breadth, but a Law 3 replication needs matched historical pre-cutoff backfill
  before any model calls.
- A credential-aware FRED source-lane probe then verified the operational side:
  the local FRED key loads from `.env`, 11/12 sampled FRED DB contracts return
  API data, and 7/12 have observations both on/before and after the existing
  freeze date. This supports a separate official-time-series lane only after a
  frozen manifest with strict resolve dates and external y-known receipts; it
  still does not provide a human/market equal-information baseline.
- The follow-up FRED ForecastBench manifest audit is stronger: 49/50 frozen
  ForecastBench FRED rows are mechanically scoreable from official FRED
  observations, 49/49 computed y-known values match the bundled outcomes, and
  49 ingest-ready contract rows were emitted without DB mutation. All scoreable
  rows are post-cutoff by resolution date, so this is post-cutoff official-data
  supply only, not a pre/post Law 3 replication.
- A fixed one-year historical FRED companion then supplied the missing official
  pre-cutoff side: 49/49 rows scoreable, all pre-cutoff, with source series
  fixed before historical observations were inspected. The resulting frozen
  49-series pair packet ran Gemini+DeepSeek on 196/196 schema-ok calls. The
  full score is weakly direction-positive but not promotion-grade: paired
  post-minus-pre Brier `+0.016477`, 90% bootstrap CI
  `[-0.006445,+0.043330]`, sign-flip p=`0.30375`. The relation-specific
  empirical YES-rate baseline (`0.213244`) beats the model mean (`0.226225`),
  so outcome mix and tool-free prior effects remain central confounds. These
  98 contracts and 196 calls are now DB-ingested.
- A direct confound control then balanced outcomes and hid the cutoff label:
  24 FRED series, 48 contracts, 192/192 Gemini+DeepSeek schema-ok calls across
  blinded-prior and blinded-value-given arms. The post-cutoff penalty
  strengthens on this diagnostic slice: paired post-minus-pre Brier
  `+0.024719`, 90% CI `[+0.007125,+0.043730]`, sign-flip p=`0.02315`.
  DeepSeek is direction-positive (`+0.027290`, p=`0.0169`); Gemini is positive
  but not secure (`+0.022148`, p=`0.26775`). Giving the due-date observed value
  does not improve Brier in this prompt form (`0.212069` vs blinded prior
  `0.206790`). The 192 control calls are now DB-ingested under
  `fred_blinded_value_control_v1`.
- A no-call vintage timing audit then demoted the FRED current-label result.
  The first `realtime_start`/`realtime_end` pass found 58/98
  vintage-scoreable rows before rate limits. A follow-up bulk-vintage repair
  used FRED `series/observations` with `output_type=2` and `vintage_dates`,
  batching once per series, and scoreable coverage reached 98/98 rows with
  49/49 series API-ok. Current FRED values were not label-time stable:
  49/98 due values changed as-of due, 44/98 resolution values changed as-of
  resolution, and 15/98 two-point real-time binary labels changed. Rescoring
  existing calls on the complete repaired label set gives pair-panel
  post-minus-pre Brier `+0.018721` under vintage labels, with mean Brier
  worsening from `0.226225` current-label to `0.233266`; the blinded-control
  apparent current-label penalty collapses from `+0.024719` to `-0.002989`.
  Therefore the FRED lane is apparatus/source-validity evidence, not positive
  Law 3 evidence.
- Applied machinery update: `org/calibration/per_agent_prompt_policy.yaml` and
  forecast-pool aggregate metadata now scope F100 to live/source-valid
  forecasts with time-valid labels/baselines. Current-label dataset rows such
  as the unrepaired FRED slice are excluded as calibration evidence, while raw
  and F100-adjusted views remain separately emitted for audits.
- F100 policy-scoreable rerun: `v_policy_scoreable_calls` excludes `10`
  complete yfinance/yfinance_etf panels without label-time receipts from the
  legacy `142`-panel fitted-calibrator audit, leaving `132` policy-scoreable
  panels. Source-isotonic remains non-promoted (`-0.005248` Brier vs
  confident-NO, paired p=`0.7099`); raw mean-panel is still worse than
  confident-NO (`+0.029598`, p=`0.0062`).
- Dataset-source label-time gate: the current DB has `165` dataset-source rows
  and `108` resolved dataset-source rows. Only `83` current-label rows are
  supported by available source-specific label-time receipts; `25` current-label
  rows are ineligible (`15` FRED labels changed under vintage repair, and `10`
  yfinance/yfinance_etf rows lack label-time receipts). This gate is now the
  reusable DB-ingested screen (`dataset_label_time_gate_rows`) before
  dataset-source rows can support law or calibration policy evidence.
- Source-currency gate: the Stage-B panel now has a reusable DB-ingested
  call-level receipt table (`source_currency_gate_rows`) and conflict view
  (`v_source_currency_gate_conflicts`). It materializes `240` computed cutoff
  receipts, balanced `120/120` pre/post, and exposes the same `39` stored flag
  conflicts for policy consumers through `v_policy_scoreable_calls_source_currency`.
- Adjacent open-date surface: 58 candidates opened pre-cutoff and 8 are
  resolved. This tests market-age/source-exposure, not the current
  resolution-date cutoff law, and must not be substituted silently.

Next move:

- Get Metaculus bot-benchmarking/data-download access or a licensed export for
  the remaining 17 target cells. Local credentials are present and authenticate,
  but the required fields are not available through the probed access tier. For
  Polymarket, acquire post-cutoff
  pre-outcome prices from a reachable source before spending further
  family-expansion calls; the Gemini/DeepSeek smokes already make the
  matched-stratum surface a scoping warning. For FRED, the current-label
  positives are demoted by complete vintage timing repair and the dataset
  label-time gate; the next useful check is an ALFRED/bulk-export
  confirmation, yfinance as-of/corporate-action receipts, or a third official
  source, not more same-shape prompt calls.
  Open a separate dataset-source
  replication only with a frozen manifest and controls; do not use it as a
  substitute for the Metaculus target.

### Law 2: Family-Conditioned Elicited-Error Surfaces

**Status:** positive diagnostic law; deployment-policy translation demoted.

Evidence:

- Premium/worry channel rows are now queryable in the DB under
  `premium_batch1` and `premium_crossfamily`.
- Cross-family contamination-clean result: worry is positive against absolute
  error in 5 / 5 families and beats confidence plus sham controls in 4 / 5.
- Pooled effect is weak but directionally useful: pooled `r = +0.090` over
  `n = 341`.
- DeepSeek is near-null, which supports family heterogeneity rather than a
  universal channel.

Current scoped claim:

- Worry/tail-risk is an error-readout channel, not an automatic probability
  correction policy.
- Uniform worry shrink, rollback, and broad Brier-policy translations are not
  promoted.
- The formerly promising `codex_55 / worry` Brier-policy cell is demoted by
  temporal/source stress: broad external holdout passes, but temporal split is
  weak/null and gain concentrates in Polymarket.

Next move:

- If policy is reopened, do not add another self-repair prompt. Either join
  broad equal-information market/human baselines, or test review allocation
  with real review cost and utility. A narrow Stage-C Manifold market bar is
  already joined and DB-ingested, but it is not a broad human/crowd baseline.

Theory bridge:

- Treat emitted uncertainty channels as behavioral proxies for latent
  error-readouts, not as trustworthy token rationales. This matches the
  apparatus-level evidence that typed evidence-carrier contracts transfer
  intent better than free prose, and the latent-prediction literature's
  distinction between predicting surface tokens and predicting structured
  latent representations. In this forecasting project the claim remains
  behavioral: we observe emitted channels and outcomes, not model activations.

### Law 1: Bias Transfer / Representational Carrier

**Status:** useful taxonomy, but the clean anti-bias-collapse mechanism is
scoped down.

Evidence:

- F102/F104 support an inherit/escape/mimic representational taxonomy:
  utility-grounded motivational biases often escape; heavily represented
  case-study patterns may be mimicked; heuristic/text-footprint effects may
  transfer.
- F106/F107 showed the need for a normative baseline and alignment-damping
  interpretation.
- The 180-call anti-bias-collapse smoke is DB-ingested but does not support a
  clean MIMIC-collapse law. Directional class contrast appears, but class-label
  shuffle is null and raw-gap adjustment reverses the MIMIC coefficient.
- A follow-up no-call raw-gap matching audit found the existing rows
  insufficient for a matched raw-gap claim. At caliper `0.05`, within-family
  matching leaves only 16 with-replacement / 15 no-replacement pairs and flips
  the MIMIC-minus-control collapse estimate negative (`-0.072750`, `p=0.0008`;
  greedy no-replacement `-0.077561`, `p=0.0006`).

Current scoped claim:

- Keep inherit/escape/mimic as an in-distribution taxonomy and alignment
  overlay as a hypothesis.
- Do not claim that anti-bias prompting cleanly collapses MIMIC but not
  INHERIT.

Next move:

- Reopen Law 1 only with new matched raw-gap strata or direct raw-gap
  randomization. Do not rerun another broad OOD bias panel or reuse the current
  packet as confirmatory matched evidence.

## Companion Lanes

No hidden law currently outranks Law 3 on evidence strength plus immediate
truth yield. Lower-priority fragments remain tracked rather than discarded:
reasoning-probability decoupling, horizon/source fragments,
sealed-independence/exposure-herding, contrastive comparative elicitation,
confident-NO fragments, selective-action arbitration, no-poolability, and F105
effort calibration.

2026-06-03 no-call and live-packet closures:

- Forecasting science spine audit: broad progress now means source-valid
  measurement, external or sham controls, cross-source/family stress, an
  actuator that can change forecasts/actions, and a residual-to-lever kill
  test. Current grades: Law 3 and F100 are `applied_candidate`; Law 2 and
  no-poolability are `science_progress` diagnostics; F47 translation,
  prompt-nurture, market additivity, and Law 1 remain scoped/experimental.
- Contrastive comparative elicitation survives the proper paired-delta re-audit:
  persisted v26a `partner_contract_id` rows reproduce `rho(predicted_delta,
  y_a-y_b)` with all 10 corpus-family cells positive and 9/10
  `h1_supported`.
- Contrastive-to-policy translation is now bounded-promoted for pairwise
  ranking, not for direct probability repair. The first no-call consumer audit
  had strong repeated-call pairwise utility but only 6 unique non-tie A/B pairs
  after collapsing repeated family/condition calls. The source-balanced
  same-source/minimal-pair packet later ran across Gemini, DeepSeek, Claude,
  and Codex-mini: 144 total call records, 94 schema-ok valid rows, 24 unique
  non-tie pairs. The unique-pair collapse clears the frozen ranking gate:
  accuracy `0.750`, utility `+0.583`, p=`0.0044` vs random and p=`0.0002` vs
  source control. This supports A/B ranking/tournament use, not production
  action routing or calibrated single-contract probabilities.
- Channel-only classifier translation fails as broad applied policy: on 785
  v28a all-channel rows, 0/5 families have positive channel-only LOO R² and
  0/5 have positive incremental LOO R² over `question_len + p_success`
  shortcuts.
- Applied-config update from the same pass: `org/calibration/per_agent_prompt_policy.yaml`
  marks F47 contrastive elicitation as `ENABLE_PAIRWISE_RANKING_EXPERIMENTAL`
  after the source-balanced four-family packet, and forecast-pool F56 bid/ask
  spread emission now uses the non-negative ask-minus-bid convention.
- F47 translation pressure test: the overlapping tournament packet fixed the
  degree-1 graph problem in the source-balanced consumer packet. Gemini/DeepSeek
  alone did not promote, but the complete four-family graph did: 194 call
  records, 192 schema-ok rows, raw-context Brier `0.234719`, translated Brier
  `0.200417`, delta `-0.034302`, p=`0.0050`, with no source regression. This
  promotes an experimental pairwise-to-probability layer, not production use.
- F47 policy control: on the same 48-contract tournament panel, translated
  panel Brier is `0.178411` versus raw panel `0.198773` and mean-family F100
  `0.201126`; translated-minus-F100 delta is `-0.022714` with p=`0.0628`.
  Direction is favorable, but the production gate remains closed. Same-contract
  market overlap is only 3 contracts, so the packet cannot answer market
  additivity.
- F47 cross-packet transfer: training the translation on the source-balanced
  packet and testing on the tournament packet gives translated panel Brier
  `0.175687` versus mean-family F100 `0.201126`, delta `-0.025439`,
  p=`0.0314`. The reverse transfer is favorable but misses the panel gate:
  translated `0.171162` versus F100 `0.196125`, delta `-0.024963`,
  p=`0.0636`. This upgrades F47 from same-packet-only to one-direction
  cross-packet support, but production use still needs prospective or
  market/human-joined validation.
- F47 external-bar control: the manifest found only 3 existing market overlaps
  among 48 F47 contracts. Public Manifold acquisition added 5 one-day
  pre-resolution bars, and corrected Polymarket direct-slug plus
  intraday-fidelity acquisition recovered all 16 Polymarket rows, giving a
  24-row mixed joined slice. On that slice, translated F47 Brier is `0.169991`,
  50/50 market+F47 `0.170067`, raw panel `0.176079`, market-alone `0.183011`,
  and mean-family F100 `0.185751`; translated-vs-market p=`0.5783` and
  translated-vs-raw p=`0.7351`.
  This is too small for a broad market claim, but it blocks deploying F47 before
  it clears raw/F100/market controls on a larger joined or prospective design.
- F47 prospective market-freeze packet: a 2026-06-04 Polymarket packet now
  freezes market bars before any LLM calls: 24 pairs, 48 unique currently open
  markets, frozen timestamp `2026-06-04T12:24:01Z`, and no frozen price leakage
  into the dispatch queue. This is not outcome evidence; it is the executable
  queue for the next causal-order test after calls and market resolutions. The
  companion scorer currently joins 48/48 markets through direct Gamma slug
  lookup and returns `not_ready_unresolved_markets`, so Brier claims are capped
  until outcomes resolve.
- F47 production-readiness synthesis: the consolidated no-call gate keeps F47
  out of absolute-probability deployment. Failed gates are same-packet
  translated-vs-F100 p-gate, same-packet translated-vs-raw p-gate,
  bidirectional cross-packet transfer, joined market control, and prospective
  causal-order resolution. Current writeable claim is pairwise/ranking support;
  the forbidden claim is that translated F47 probabilities beat markets or
  should replace F100/raw in production.

### No-Poolability / Conditional Routing

Evidence:

- Brier and Elo rank families differently.
- Family-by-contract interaction carries substantial variance.
- Naive mean/median does not reliably beat best-single.
- A source+sigma router improved a small holdout but failed source
  leave-one-out on Manifold and Polymarket.
- F117 source-balanced audit over 123 complete-five contracts (41 each from
  Manifold, Polymarket, premium-clean) kills the current router as applied
  policy: selected router + confident-NO Brier `0.264033` loses to
  confident-NO mean-panel `0.256288` and fails Manifold/premium-clean.
- F118 diagnostic-triggered allocation over 142 complete-five v28a panels also
  fails against simple baselines; the best current applied policy is
  confident-NO mean-panel.
- A source-currency stress audit narrows F100: on the Law 3 Stage-B panel it
  improves post-cutoff rows (Brier delta `-0.025326`, tail-only `-0.101306`)
  but regresses pre-cutoff/source-visible rows (delta `+0.035016`, p=`0.0002`;
  tail-only `+0.097719`, p=`0.0002`). Treat F100 as forward-looking
  calibration with time-valid labels/baselines, not retrospective benchmark
  correction. A 2026-06-04 receipt repair reran this audit through the shared
  source-currency discriminator: scores and verdict stayed unchanged, while
  39/240 rows were exposed as stored-flag-vs-computed-relation conflicts. A
  follow-up no-call DB materializer now exposes those receipts in
  `source_currency_gate_rows`, `v_source_currency_gate_conflicts`, and
  `v_policy_scoreable_calls_source_currency`.
- A later costed review-allocation audit over the same 142 complete-five panels
  shows oracle headroom but no deployable proxy reviewer: oracle-family review
  reaches costed Brier `0.141930`, but the best non-oracle policy
  (`sigma_high_review_to_source_best`) reaches only `0.227372` vs F100
  `0.233528`, delta `-0.006156`, paired p=`0.3531`.
- Graph-family nearest-neighbor weighting over complete-five v28a panels is
  suggestive but not deployable. Full-cohort graph+confident-NO Brier is
  `0.231166` vs confident-NO `0.233528` (p=`0.3019`); balanced
  Manifold/Polymarket source-graph Brier is `0.238961` vs confident-NO
  `0.242317` (p=`0.0398`), but the lift is only `0.0034` and needs
  pre-registered replication against hash-neighbor controls.
- Expert-advice routing does not yet rescue the applied router. On 142
  complete-five panels, Hedge over raw families, F100-adjusted families, and
  simple pools scores Brier `0.226481` vs confident-NO mean-panel `0.233529`,
  but the paired delta is only `-0.0070` with p=`0.4671`. On the balanced
  Manifold/Polymarket slice it is `0.233990` vs `0.238435`, p=`0.7578`, and
  regresses on Manifold. Oracle-expert Brier is much lower (`0.117454`
  overall), so family-choice headroom is real but not yet recoverable by the
  current observable policies.

Status:

- No-poolability is a real companion law.
- No deployed router claim yet.
- Do not rerun source+sigma or tail-trigger allocation variants without a real
  independent reviewer source and fixed review cost.

Next move:

- Reopen only with new predeclared features or equal-information human/market
  baselines.

### Nurture / Intervention

Evidence:

- Generic rationale, self-distractor, skeptical, and failure-word prompts often
  change text without improving Brier.
- F28 and F30 show that premium/worry can help when wired as abstention or
  judge/reroute under explicit utility, not naive threshold shifting.
- N1 selective action looked promising adaptively.
- N2 failed confirmation: `n=35`, mean paired Brier delta `+0.025779`,
  paired-permutation `p=0.5649`, mean utility `-0.205882`.
- N3-N7 demote high-worry action policy and self-repair variants: naive
  base-rate repair overcorrects downward, selection-aware repair can
  overcorrect upward, and guarded repair mostly becomes a no-op while still
  worsening pooled Brier.
- F118 no-call DB audit: diagnostic-triggered allocation policies lose to
  confident-NO mean-panel on 142 complete-five panels.
- N9 carrier-vs-prose smoke: free prose worsens mean Brier (`+0.068441`,
  p=`0.238`); typed carrier weakly improves versus baseline (`-0.012225`,
  p=`0.8276`) and beats free prose on mean; the action arm only ties the
  threshold-abstain control. This is underpowered continuation evidence, not a
  law claim.
- N10 hard-prompt-break smokes: the Codex first-family run favored the
  two-stage carrier-only-then-execute arm, but the Claude replication scoped the
  stronger mechanism down. Combined means over the first 8 rows were baseline
  `0.171038`, free prose `0.146103`, same-turn typed carrier `0.098425`,
  hard prompt break `0.103278`. A later placebo-control continuation was
  negative for the stronger story: among 30 schema-valid rows, baseline mean
  Brier was `0.078000`, two-call prose `0.107254`, same-turn carrier
  `0.110300`, free prose `0.122767`, and hard prompt break `0.149921`; 10
  Codex rows failed at runtime before forecasts. This does not support
  hard-break-beyond-carrier as a law.
- Rationale compression/NCD was tested as a structural proxy on paired
  v28a/v28i external rows (`n=210`). Inversion improved mean Brier by
  `-0.052001`, but NCD did not explain where it helped
  (`rho=+0.016463` vs Brier delta), so compression distance is not promoted as
  a routing or escalation feature.

Current status:

- No intervention companion has a deployed Brier-improving claim.
- Confident-NO mean-panel is the best current applied rule in the DB and is now
  exposed directly by forecast-pool aggregation as an adjusted post-processing
  view, not a replacement for the raw aggregate. The adjusted view is scoped to
  live/source-valid rows with time-valid labels/baselines.
- Construct-validity audit: the N-series demotes the tested tool-free prompt
  families, not all prompt engineering. Tool-using, interactive,
  retrieval-grounded, expert-written, or development-set-optimized prompt
  programs remain untested.

Next move:

- Continue N9/N10 only if the next packet is larger, balanced after runtime
  failures, and able to beat both same-turn carrier and two-call prose controls.
  Higher-yield applied work remains equal-information human/market joining or
  real-cost review allocation.

### F105 Effort Calibration

F105 is a sibling paper lane, not evidence for the three-law binary Brier paper.
The DB rescue makes continuous effort-estimation rows queryable, but objective
hidden-test effort calibration still needs its own paper-grade design.

## Immediate Queue

The 2026-06-05 paper-readiness/exhaustion audit says the scoped paper is ready
to write as diagnostic/applied-candidate claims, but the broad landmark claim is
not ready. The not-ready claims are production F47 translated probability and
broad equal-information human/market comparison. Current DB evidence has `51`
external market-baseline rows, `0` equal-information market-baseline rows,
`240` source-currency gate receipts, and `39` stored/computed cutoff conflicts.

| Rank | Workstream | Next concrete move | Kill / scope condition |
|---:|---|---|---|
| 1 | Equal-information human/market baseline join | Broad baseline is mechanically absent locally: 51 matched market rows and 0 equal-information market rows; acquire Metaculus export/access or reachable post-cutoff Polymarket prices before more model calls | LLM panel loses once broad equal-information baselines are joined |
| 2 | Law 3 second-source replication | Complete Metaculus/general-source acquisition from the target manifest, or acquire source-valid post-cutoff Polymarket prices for matched controls | Second source shows no pre/post Brier gap after matching |
| 3 | F47 translated-probability control test | Compare translated F47 probabilities against F100 confident-NO, raw mean-panel, source controls, and joined market/human bars where available | Translation loses to F100/raw/market controls or source/template controls explain the lift |
| 4 | Independent-review allocation | Only after defining a real reviewer source (market/web/human/heldout family), run a fixed-cost source-balanced packet | Review allocation loses to confident-NO forecast-all plus sham triggers |
| 5 | Law 1 raw-gap redesign | Match or randomize raw frame-gap before testing anti-bias collapse | Class effect disappears after raw-gap control |
| 6 | F105 sibling | Hidden-test objective effort tasks with DB persistence | Real-factor arm fails fake-factor and raw baselines |

## Public Non-Claims

- No claim that LLMs beat humans or prediction markets. A narrow Stage-C
  Manifold market bar is joined, but broad local human/crowd baselines are not
  yet joined on the same contracts with equal information access. The narrow
  Stage-C blend audit fails promotion under leave-one-out tuning and is
  post-cutoff-negative for LLM addition. A follow-up void audit finds only 51
  matched baseline contracts, all Manifold.
- No claim that worry improves Brier uniformly.
- No claim that broad selective-action prompting improves forecasts.
- No claim that the current router is deployable.
- No claim that Law 3 is source-general until a non-Manifold pre/post panel is
  acquired and scored.
- No claim that non-empirical packets are findings. Finding IDs are reserved
  for empirical results or methodology results with executable evidence.

## Canonical Evidence

- Research log: `forecaster_skill_calibration_v1/workspace/research_log.md`.
- Operational queue: `forecaster_skill_calibration_v1/workspace/pilot_queue.md`.
- Database: `analytics/public/calibration/forecaster_calibration.db`.
- Methodology/DB/tooling: `public/METHODOLOGY.md`.
- Working paper: `papers/llm-forecast-calibration-cross-corpus/`.
- Evidence-atlas packet: `docs/evidence_atlas/packets/forecast_calibration_gp245.md`.
