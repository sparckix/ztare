---
description: "Public science-state summary for the GP-245 LLM forecasting calibration program."
---
# GP-245 Forecasting Calibration — Science State

Updated 2026-06-16.

This is the public science-state surface for the GP-245 LLM forecasting
calibration program. It replaces the older split set of claim matrices, protocol
notes, and frontier scans. Methodology, database schema, ingestion, and tooling
live in `METHODOLOGY.md`.

## Current Claim

The program does **not** show that "LLMs forecast well" in general or that raw
LLM panels beat equal-information markets. The current claim is narrower and
stronger:

> Raw LLM forecasts do not beat equal-information market bars in the current
> evidence, but LLM forecast signal can be harnessed under source-currency,
> label-time, calibration, ranking, and family/source constraints.

The cleaner program frame is evidence-first. Six buckets now govern
what is tested, scored, or treated as supported:

1. **Validity.** Decide whether a row can count as forecast evidence for this
   model generation: source/cutoff visibility, dataset label-time records,
   contamination, and equal-information scope.
2. **Calibration.** Transform valid probabilities only when the transform
   improves a proper score against controls. The low-probability calibration adjustment is the
   current candidate under source-valid, forward-looking scope.
3. **Ranking.** Test whether LLMs are better at relative comparisons than
   absolute probabilities. The current evidence supports pairwise and
   tournament-style ranking; probability translation remains experimental.
4. **Allocation.** Decide when to buy outside information, abstain, or choose
   among model families. Best-family headroom is real; current observable
   selection rules still need larger controlled confirmation.
5. **External baselines.** Decide whether an LLM or LLM+market system adds
   value beyond market/human bars on matched contract-level evidence.
6. **Bias-transfer theory.** Explain when cognitive-bias categories appear in
   model forecasts only after validity and calibration have been separated. It
   is theory and diagnostic design unless it selects a scored intervention.

This yields three active scientific claims plus two companion lanes:

1. **Source-currency / cutoff-validity claim.** Forecast benchmarks are not valid
   for a model generation when the resolved answer is already source-visible to
   that generation. This is the strongest current positive result.
2. **Family-conditioned elicited-error claim.** Auxiliary channels such as
   worry/tail-risk can expose error risk by family, but diagnostic signal does
   not automatically become a Brier-improving policy.
3. **Bias-transfer / structured-evidence claim.** The representational
   distinction between text-heavy bias cases and utility-like bias cases is
   useful, but the clean anti-bias-prompt mechanism is scoped down by raw-gap
   controls.
4. **Conditional allocation companion.** Family-by-contract interaction is
   real, but the current allocation rules are source-fragile.
5. **Prompt intervention companion.** Broad selective-action prompting,
   self-repair, and diagnostic-triggered allocation are narrowed. A small
   structured-fields versus prose test keeps structured probability elicitation
   alive, but not action execution. The current applied rule is the simple
  mean-panel with the low-probability adjustment for forward-looking/source-valid rows with
  time-valid labels/baselines until stronger controls beat it.

The 2026-06-15 paper-readiness audit keeps this as one integrated paper for
now. The split trigger is future positive prospective evidence on calibration,
pairwise translation, or allocation strong enough to stand as an independent
mechanisms paper.

## Evidence Summary

### Source-Currency / Cutoff Validity

**Status:** strongest current paper-grade claim, with a clear second-source
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
  `post_cutoff_prefers_market_only`.
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
- Missing-band sensitivity: adversarially assigning the 29 unjoined
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
- Bounded live Polymarket-only Gemini and DeepSeek checks then used the
  acquired slice: each landed 48 / 48 schema-ok calls over 24 pre-cutoff and 24
  post-cutoff rows. The raw aggregate supports the source-currency claim direction for Gemini
  (`post-minus-pre=+0.246832` Brier) and weakly for DeepSeek (`+0.077758`),
  but the six matched source/topic/length strata are null/opposite-sign:
  Gemini `+0.005731` (`p=0.9696`) and DeepSeek `-0.061706` (`p=0.8836`).
  This is useful preliminary evidence, not a source-general replication.
- A follow-up Polymarket base-rate availability probe originally failed on the
  frozen post-cutoff slice because the list-style Gamma slug route returned no
  markets. The repaired probe uses Gamma's direct `/markets/slug/{slug}`
  endpoint and recovers 4 / 24 post-cutoff rows with CLOB history at or before
  the seven-day freeze timestamp; the remaining rows split into 10 empty
  histories and 10 with no history before the target. A freeze-feasibility
  audit then classifies all 20 unfilled rows as
  `market_not_open_by_target_freeze`, so the current seven-day packet is
  design-ineligible for those rows rather than merely missing an export route.
  This leaves base-rate/source-topic confounding live rather than resolved.
- A predeclared horizon sweep over the same 24 post-cutoff Polymarket rows
  tests day horizons 7, 5, 3, 2, 1, and 0 before resolution. Joined rows are
  `4 / 24`, `6 / 24`, `9 / 24`, `12 / 24`, `12 / 24`, and `12 / 24`
  respectively. No tested day horizon fully rescues the packet; the best
  available day horizon is 2 days but still leaves half the sample without
  usable CLOB history.
- A replacement-sample acquisition run on 2026-06-15 scanned 800 closed
  post-cutoff Polymarket markets, probed 81 CLOB histories, found 80 eligible
  candidates, and selected 24 one-per-event rows at a 2-day horizon. The
  selected packet has outcome mix 14 NO / 10 YES, freeze bands 16 in
  `0.00-0.10` and 8 in `0.90-1.00`, and verdict
  `replacement_sample_ready_for_model_packet`.
- The completed Claude+Codex+Gemini+DeepSeek slice on that replacement packet is a
  same-contract negative market control: Claude mean Brier `0.233184`, Codex
  mean Brier `0.264409`, Gemini mean Brier `0.304696`, DeepSeek mean Brier
  `0.334775`, all model-call mean Brier `0.284266`, four-family
  mean-probability panel Brier `0.267758`, Polymarket mean Brier `0.072964`,
  panel-minus-market `+0.194794`, paired permutation `p=0.0068`, n=`24`
  contracts / `96` model calls. This is four-family evidence against an
  LLM-beats-market claim, not a broad human/crowd comparison.
- An equal-information export packet now makes the blocked acquisition exact:
  24 post-cutoff Polymarket rows, each with slug, market URL, target freeze
  date, outcome, stratum metadata, and required result fields for YES token ID,
  historical YES price, timestamp, source, and outcome mapping. The current
  filled-result file has 4 / 24 valid rows.
- A companion filled-result validator/ingester now defines the return path:
  `valid_rows == requested_rows` and `missing_requested_rows == 0` before any
  equal-information Polymarket rows can enter `external_baseline_observations`
  with `equal_information_flag=1`. Current status is `4 / 24` valid rows,
  `20 / 24` design-ineligible under the seven-day freeze target, all 4 valid
  rows post-cutoff Polymarket YES outcomes with mean Brier `0.065782`; this is
  partial acquisition, not a broad market/human comparison. The next legitimate
  experiment is a replacement sample restricted to markets open by the target
  with nonempty CLOB history before model calls.
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
- A stored-row FRED/yfinance slate audit sharpens that boundary: the current
  ForecastBench bundle joins 98 resolved FRED/yfinance rows, all post-cutoff by
  resolution date and 0 pre-cutoff. These rows can supply post-cutoff source
  breadth, but a source-currency claim replication needs matched historical pre-cutoff backfill
  before any model calls.
- A credential-aware FRED source-lane probe then verified the operational side:
  the local FRED key loads from `.env`, 11/12 sampled FRED DB contracts return
  API data, and 7/12 have observations both on/before and after the existing
  freeze date. This supports a separate official-time-series lane only after a
  frozen manifest with strict resolve dates and external outcome records; it
  still does not provide a human/market equal-information baseline.
- The follow-up FRED ForecastBench manifest audit is stronger: 49/50 frozen
  ForecastBench FRED rows are mechanically scoreable from official FRED
  observations, 49/49 computed y-known values match the bundled outcomes, and
  49 ingest-ready contract rows were emitted without DB mutation. All scoreable
  rows are post-cutoff by resolution date, so this is post-cutoff official-data
  supply only, not a pre/post source-currency claim replication.
- A fixed one-year historical FRED companion then supplied the missing official
  pre-cutoff side: 49/49 rows scoreable, all pre-cutoff, with source series
  fixed before historical observations were inspected. The resulting frozen
  49-series pair packet ran Gemini+DeepSeek on 196/196 schema-ok calls. The
  full score is weakly direction-positive but not support-grade: paired
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
- A stored-row vintage timing audit then narrowed the FRED current-label result.
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
  Therefore the FRED lane is workflow/source-validity evidence, not positive
  source-currency claim evidence.
- Applied machinery update: `org/calibration/per_agent_prompt_policy.yaml` and
  forecast-pool aggregate metadata now scope the low-probability calibration adjustment to live/source-valid
  forecasts with time-valid labels/baselines. Current-label dataset rows such
  as the unrepaired FRED slice are excluded as calibration evidence, while raw
  and adjusted views remain separately emitted for audits.
- low-probability adjustment policy-scoreable rerun: `v_policy_scoreable_calls` excludes `10`
  complete yfinance/yfinance_etf panels without label-time records from the
  legacy `142`-panel fitted-calibrator audit, leaving `132` policy-scoreable
  panels. Source-isotonic remains unsupported (`-0.005248` Brier vs
  low-probability adjustment, paired p=`0.7099`); raw mean-panel is still worse than
  low-probability adjustment (`+0.029598`, p=`0.0062`).
- Dataset-source label-time screen: the current DB has `165` dataset-source rows
  and `108` resolved dataset-source rows. Only `83` current-label rows are
  supported by available source-specific label-time records; `25` current-label
  rows are ineligible (`15` FRED labels changed under vintage repair, and `10`
  yfinance/yfinance_etf rows lack label-time records). This screen is now the
  reusable DB-ingested screen (`dataset_label_time_gate_rows`) before
  dataset-source rows can support claim or calibration policy evidence.
- Source-currency screen: the Stage-B panel now has a reusable DB-ingested
  call-level row table (`source_currency_gate_rows`) and conflict view
  (`v_source_currency_gate_conflicts`). It materializes `240` computed cutoff
  rows, balanced `120/120` pre/post, and exposes the same `39` stored flag
  conflicts for policy consumers through `v_policy_scoreable_calls_source_currency`.
- Adjacent open-date surface: 58 candidates opened pre-cutoff and 8 are
  resolved. This tests market-age/source-exposure, not the current
  resolution-date cutoff claim, and must not be substituted silently.

Next move:

- Get Metaculus bot-benchmarking/data-download access or a licensed export for
  the remaining 17 target cells. Local credentials are present and authenticate,
  but the required fields are not available through the probed access tier. For
  Polymarket, acquire post-cutoff
  pre-outcome prices from a reachable source before spending further
  family-expansion calls; the Gemini/DeepSeek small tests already make the
  matched-stratum surface a scoping warning. For FRED, the current-label
  positives are narrowed by complete vintage timing repair and the dataset
  label-time screen; the next useful check is an ALFRED/bulk-export
  confirmation, yfinance as-of/corporate-action records, or a third official
  source, not more same-design prompt calls.
  Open a separate dataset-source
  replication only with a frozen manifest and controls; do not use it as a
  substitute for the Metaculus target.

### Family-Conditioned Elicited-Error Surfaces

**Status:** positive diagnostic claim; deployment-policy translation narrowed.

Evidence:

- Premium/worry channel rows are now queryable in the DB under
  `premium_batch1` and `premium_crossfamily`.
- Cross-family contamination-clean result: worry is positive against absolute
  error in 5 / 5 families and beats confidence plus placebo controls in 4 / 5.
- Pooled effect is weak but directionally useful: pooled `r = +0.090` over
  `n = 341`.
- DeepSeek is near-null, which supports family heterogeneity rather than a
  universal channel.

Current scoped claim:

- Worry/tail-risk is an error-readout channel, not an automatic probability
  correction policy.
- Uniform worry shrink, rollback, and broad Brier-policy translations are not
  supported.
- The formerly promising `codex_55 / worry` Brier-policy cell is narrowed by
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
  project-level evidence that structured evidence fields transfer
  intent better than free prose, and the latent-prediction literature's
  distinction between predicting surface tokens and predicting structured
  latent representations. In this forecasting project the claim remains
  behavioral: we observe emitted channels and outcomes, not model activations.

### bias-transfer claim: Bias Transfer / Structured Evidence

**Status:** useful taxonomy, but the clean anti-bias-collapse mechanism is
scoped down.

Evidence:

- Earlier bias-transfer tests support a representational distinction:
  utility-grounded motivational biases often show weak transfer; heavily
  represented case-study patterns can appear in model outputs; heuristic and
  high-text-footprint effects may transfer more directly.
- Later checks showed the need for a normative baseline and alignment-damping
  interpretation.
- The 180-call anti-bias-prompt check is DB-ingested but does not support a
  clean collapse claim. Directional class contrast appears, but class-label
  shuffle is null and raw-gap adjustment reverses the text-discussed-bias
  coefficient.
- A follow-up stored-row raw-gap matching audit found the existing rows
  insufficient for a matched raw-gap claim. At caliper `0.05`, within-family
  matching leaves only 16 with-replacement / 15 no-replacement pairs and flips
  the estimated treatment-minus-control collapse effect negative (`-0.072750`,
  `p=0.0008`; greedy no-replacement `-0.077561`, `p=0.0006`).

Current scoped claim:

- Keep the bias-transfer taxonomy as an in-distribution diagnostic and keep
  the alignment overlay as a hypothesis.
- Do not claim that anti-bias prompting cleanly improves the text-discussed
  bias class while leaving other classes unchanged.

Next move:

- Reopen bias-transfer claim only with new matched raw-gap strata or direct raw-gap
  randomization. Do not rerun another broad OOD bias panel or reuse the current
  packet as confirmatory matched evidence.

## Companion Lanes

No hidden claim currently outranks source-currency claim on evidence strength plus immediate
truth yield. Lower-priority fragments remain tracked rather than discarded:
reasoning-probability decoupling, horizon/source fragments,
sealed-independence/exposure-herding, contrastive comparative elicitation,
low-probability adjustment fragments, selective-action arbitration, no-poolability, and
objective effort calibration.

2026-06-03 stored-row and live-packet closures:

- Program evidence audit: broad progress now means source-valid
  measurement, external or placebo controls, cross-source/family stress, a
  scored intervention that can change forecasts/actions, and a discriminating
  follow-up test. Current grades: source-currency and low-probability adjustment calibration are
  applied candidate; elicited-error and family-interaction findings are
  science-progress diagnostics; pairwise translation,
  prompt-intervention, market additivity, and bias-transfer claim remain scoped/experimental.
- Contrastive comparative elicitation survives the proper paired-delta re-audit:
  persisted paired-contract rows reproduce `rho(predicted_delta,
  y_a-y_b)` with all 10 corpus-family cells positive and 9/10
  the predeclared support threshold.
- Contrastive-to-policy translation is now supported within scope for pairwise
  ranking, not for direct probability repair. The first stored-row consumer audit
  had strong repeated-call pairwise utility but only 6 unique non-tie A/B pairs
  after collapsing repeated family/condition calls. The source-balanced
  same-source/minimal-pair packet later ran across Gemini, DeepSeek, Claude,
  and Codex-mini: 144 total call records, 94 schema-ok valid rows, 24 unique
  non-tie pairs. The unique-pair collapse clears the frozen ranking check:
  accuracy `0.750`, utility `+0.583`, p=`0.0044` vs random and p=`0.0002` vs
  source control. This supports A/B ranking/tournament use, not automated
  action allocation or calibrated single-contract probabilities.
- Channel-only classifier translation fails as broad applied policy: on 785
  all-channel rows, 0/5 families have positive channel-only LOO R² and
  0/5 have positive incremental LOO R² over `question_len + p_success`
  shortcuts.
- Applied-config update from the same pass: `org/calibration/per_agent_prompt_policy.yaml`
  marks contrastive elicitation as `ENABLE_PAIRWISE_RANKING_EXPERIMENTAL`
  after the source-balanced four-family packet, and forecast-pool bid/ask
  spread emission now uses the non-negative ask-minus-bid convention.
- Pairwise-translation pressure test: the overlapping tournament packet fixed the
  degree-1 graph problem in the source-balanced consumer packet. Gemini/DeepSeek
  alone was not supported, but the complete four-family graph did: 194 call
  records, 192 schema-ok rows, raw-context Brier `0.234719`, translated Brier
  `0.200417`, delta `-0.034302`, p=`0.0050`, with no source regression. This
  supports an experimental pairwise-to-probability layer, not a general
  single-contract probability method.
- Pairwise-translation policy control: on the same 48-contract tournament panel,
  translated panel Brier is `0.178411` versus raw panel `0.198773` and
  mean-family low-probability adjustment `0.201126`; translated-minus-low-probability adjustment delta is
  `-0.022714` with p=`0.0628`.
  Direction is favorable, but the applied-use check remains closed. Same-contract
  market overlap is only 3 contracts, so the packet cannot answer market
  additivity.
- Pairwise-translation cross-packet transfer: training the translation on the source-balanced
  packet and testing on the tournament packet gives translated panel Brier
  `0.175687` versus mean-family low-probability adjustment `0.201126`, delta `-0.025439`,
  p=`0.0314`. The reverse transfer is favorable but misses the panel check:
  translated `0.171162` versus low-probability adjustment `0.196125`, delta `-0.024963`,
  p=`0.0636`. This upgrades pairwise translation from same-packet-only to one-direction
  cross-packet support, but single-contract probability use still needs prospective or
  market/human-joined validation.
- Pairwise-translation external-bar control: the manifest found only 3 existing market overlaps
  among 48 translated-probability contracts. Public Manifold acquisition added 5 one-day
  pre-resolution bars, and corrected Polymarket direct-slug plus
  intraday-fidelity acquisition recovered all 16 Polymarket rows, giving a
  24-row mixed joined slice. On that slice, translated-probability Brier is
  `0.169991`, 50/50 market+translation `0.170067`, raw panel `0.176079`,
  market-alone `0.183011`, and mean-family low-probability adjustment `0.185751`;
  translated-vs-market p=`0.5783` and
  translated-vs-raw p=`0.7351`.
  This is too small for a broad market claim, but it blocks using translated
  probabilities before they clear raw/low-probability adjustment/market controls on a larger
  joined or prospective design.
- Pairwise-translation prospective market-freeze packet: a 2026-06-04 Polymarket packet now
  freezes market bars before any LLM calls: 24 pairs, 48 unique currently open
  markets, frozen timestamp `2026-06-04T12:24:01Z`, and no frozen price leakage
  into the dispatch queue. It supplies the executable queue for the next
  causal-order test after calls and market resolutions, but it is not outcome evidence. The
  companion scorer currently joins 48/48 markets through direct Gamma slug
  lookup and returns `not_ready_unresolved_markets`, so Brier claims are capped
  until outcomes resolve.
- Pairwise-translation readiness synthesis: the consolidated stored-row audit keeps
  translated probabilities out of absolute-probability use. Failed checks are
  same-packet translated-vs-low-probability adjustment p-value, same-packet translated-vs-raw p-value,
  bidirectional cross-packet transfer, joined market control, and prospective
  causal-order resolution. Current writeable claim is pairwise/ranking support;
  the unsupported claim is that translated probabilities beat markets or should
  replace low-probability adjustment/raw probabilities.

### No-Poolability / Conditional Allocation

Evidence:

- Brier and Elo rank families differently.
- Family-by-contract interaction carries substantial variance.
- Naive mean/median does not reliably beat best-single.
- A source+sigma allocation rule improved a small holdout but failed source
  leave-one-out on Manifold and Polymarket.
- Source-balanced audit over 123 complete-five contracts (41 each from
  Manifold, Polymarket, premium-clean) rules out the current allocation rule as applied
  policy: selected-family + low-probability adjustment Brier `0.264033` is worse than
  mean-panel with the low-probability adjustment `0.256288` and fails Manifold/premium-clean.
- Diagnostic-triggered allocation over 142 complete-five panels also
  fails against simple baselines; the best current applied policy is
  mean-panel with the low-probability adjustment.
- A source-currency stress audit narrows low-probability adjustment calibration: on the source-currency Stage-B panel it
  improves post-cutoff rows (Brier delta `-0.025326`, tail-only `-0.101306`)
  but regresses pre-cutoff/source-visible rows (delta `+0.035016`, p=`0.0002`;
  tail-only `+0.097719`, p=`0.0002`). Treat low-probability adjustment as forward-looking
  calibration with time-valid labels/baselines, not retrospective benchmark
  correction. A 2026-06-04 record repair reran this audit through the shared
  source-currency discriminator: scores and verdict stayed unchanged, while
  39/240 rows were exposed as stored-flag-vs-computed-relation conflicts. A
  follow-up stored-row DB materializer now exposes those rows in
  `source_currency_gate_rows`, `v_source_currency_gate_conflicts`, and
  `v_policy_scoreable_calls_source_currency`.
- A later costed review-allocation audit over the same 142 complete-five panels
  shows best-family headroom but no confirmed proxy reviewer: best-family review
  reaches costed Brier `0.141930`, but the best non-best-family policy
  (`sigma_high_review_to_source_best`) reaches only `0.227372` vs low-probability adjustment
  `0.233528`, delta `-0.006156`, paired p=`0.3531`.
- Graph-family nearest-neighbor weighting over complete-five panels is
  suggestive but not ready for use as an automated rule. Full-cohort graph plus low-probability adjustment Brier is
  `0.231166` vs low-probability adjustment `0.233528` (p=`0.3019`); balanced
  Manifold/Polymarket source-graph Brier is `0.238961` vs low-probability adjustment
  `0.242317` (p=`0.0398`), but the lift is only `0.0034` and needs
  pre-registered replication against hash-neighbor controls.
- Expert-advice allocation does not yet rescue the applied allocation rule. On 142
  complete-five panels, Hedge over raw families, low-probability-adjusted families, and
  simple pools scores Brier `0.226481` vs mean-panel with the low-probability adjustment `0.233529`,
  but the paired delta is only `-0.0070` with p=`0.4671`. On the balanced
  Manifold/Polymarket slice it is `0.233990` vs `0.238435`, p=`0.7578`, and
  regresses on Manifold. Best-family expert Brier is much lower (`0.117454`
  overall), so family-choice headroom is real but not yet recoverable by the
  current observable policies.

Status:

- Conditional allocation is a real companion claim.
- No deployed allocation claim yet.
- Do not rerun source+sigma or tail-trigger allocation variants without a real
  independent reviewer source and fixed review cost.

Next move:

- Reopen only with new predeclared features or equal-information human/market
  baselines.

### Prompt Intervention

Evidence:

- Generic rationale, self-distractor, skeptical, and failure-word prompts often
  change text without improving Brier.
- Earlier premium/worry tests show that these channels can help when wired as
  abstention or review under explicit utility, not naive threshold shifting.
- Selective action looked promising adaptively.
- Confirmatory selective-action test failed: `n=35`, mean paired Brier delta `+0.025779`,
  paired-permutation `p=0.5649`, mean utility `-0.205882`.
- High-worry action policy and self-repair variants were narrowed: naive
  base-rate repair overcorrects downward, selection-aware repair can
  overcorrect upward, and guarded repair mostly becomes a no-op while still
  worsening pooled Brier.
- stored-row DB audit: diagnostic-triggered allocation policies have higher Brier than
  mean-panel with the low-probability adjustment on 142 complete-five panels.
- Structured-fields versus prose test: free prose worsens mean Brier (`+0.068441`,
  p=`0.238`); structured fields weakly improve versus baseline (`-0.012225`,
  p=`0.8276`) and beats free prose on mean; the action arm only ties the
  threshold-abstain control. This is underpowered continuation evidence, not a
  claim.
- Hard-prompt-break tests: the Codex first-family run favored the
  two-stage structured-fields-only-then-execute arm, but the Claude replication scoped the
  stronger claim down. Combined means over the first 8 rows were baseline
  `0.171038`, free prose `0.146103`, same-turn structured fields `0.098425`,
  hard prompt break `0.103278`. A later placebo-control continuation was
  negative for the stronger claim: among 30 schema-valid rows, baseline mean
  Brier was `0.078000`, two-call prose `0.107254`, same-turn structured fields
  `0.110300`, free prose `0.122767`, and hard prompt break `0.149921`; 10
  Codex rows failed at runtime before forecasts. This does not support
  hard-break-beyond-structured-fields as a claim.
- Rationale compression/NCD was tested as a structural proxy on paired
  external rows (`n=210`). Inversion improved mean Brier by
  `-0.052001`, but NCD did not explain where it helped
  (`rho=+0.016463` vs Brier delta), so compression distance is not supported as
  an allocation or escalation feature.

Current status:

- No intervention companion has a deployed Brier-improving claim.
- low-probability adjustment mean-panel is the best current applied rule in the DB and is now
  exposed directly by forecast-pool aggregation as an adjusted post-processing
  view, not a replacement for the raw aggregate. The adjusted view is scoped to
  live/source-valid rows with time-valid labels/baselines.
- Construct-validity audit: the intervention series narrows the tested tool-free prompt
  families, not all prompt engineering. Tool-using, interactive,
  retrieval-grounded, expert-written, or development-set-optimized prompt
  programs remain untested.

Next move:

- Continue structured-field and hard-break tests only if the next packet is larger, balanced after runtime
  failures, and able to beat both same-turn structured fields and two-call prose controls.
  Higher-yield applied work remains equal-information human/market joining or
  real-cost review allocation.

### Objective Effort Calibration

Objective effort calibration is a sibling paper lane, not evidence for the three-claim binary Brier paper.
The DB rescue makes continuous effort-estimation rows queryable, but objective
hidden-test effort calibration still needs its own paper-grade design.

## Immediate Queue

The 2026-06-15 paper-readiness/exhaustion audit says the scoped paper is ready
to write as diagnostic/applied-candidate claims, but the broad market/human
comparison is not ready. The not-ready claims are translated-probability use and
broad equal-information human/market comparison. Current DB evidence has `103`
external market-baseline rows, `52` equal-information market-baseline rows,
`240` source-currency rows, and `39` stored/computed cutoff conflicts.

| Rank | Workstream | Next concrete move | Scope condition |
|---:|---|---|---|
| 1 | Field-wide validity audit | Run `field_wide_validity_audit_protocol.py` and `field_wide_validity_local_evidence.py`, then fill row-level audit fields for at least ForecastBench, the Halawi 2024 binary-resolved benchmark, and AIA Forecaster before claiming field-wide prevalence. The Halawi local summary is a date-distribution warning only; raw rows and before/after scores are still missing locally | Audited benchmark families show low validity-field missingness or no conclusion changes after repair |
| 2 | Equal-information human/market baseline join | The Polymarket replacement slice favors the market across all four model families: Claude Brier `0.233184`, Codex `0.264409`, Gemini `0.304696`, DeepSeek `0.334775`, four-family panel `0.267758`, Polymarket `0.072964` on 24 same-contract rows. The 24-row Manifold second-source fill also favors the market but is inconclusive: five-family low-stake model panel `0.198723`, Manifold `0.160977`, panel-minus-market `+0.037746`, paired p=`0.5431`. The next broad-claim test is prospective or larger source-balanced evidence, not more same-design model calls | LLM panel has higher Brier or remains inconclusive once equal-information market baselines are joined |
| 3 | source-currency claim second-source replication | Complete Metaculus/general-source acquisition from the target manifest, or acquire source-valid post-cutoff Polymarket prices for matched controls | Second source shows no pre/post Brier gap after matching |
| 4 | Translated-probability control test | Compare translated probabilities against low-probability adjustment, raw mean-panel, source controls, and joined market/human bars where available | Translation has higher Brier than low-probability adjustment/raw/market controls or source/template controls explain the lift |
| 5 | Independent-review allocation | Only after defining a real reviewer source (market/web/human/heldout family), run a fixed-cost source-balanced packet | Review allocation has higher Brier than low-probability adjustment forecast-all plus placebo triggers |
| 6 | bias-transfer claim raw-gap redesign | Match or randomize raw frame-gap before testing anti-bias collapse | Class effect disappears after raw-gap control |
| 7 | Objective effort sibling paper | Hidden-test objective effort tasks with DB persistence | Real-factor arm fails fake-factor and raw baselines |

## Public Non-Claims

- No claim that LLMs beat humans or prediction markets. A narrow Stage-C
  Manifold market bar is joined as a diagnostic comparison, and a later
  equal-information Polymarket replacement slice is now complete. On that
  24-contract same-information slice, Claude, Codex, Gemini, and DeepSeek all
  have higher Brier than Polymarket; the four-family panel Brier is `0.267758` versus
  Polymarket `0.072964` with paired p=`0.0068`. A separate 24-row Manifold
  equal-information fill is now validated and DB-ingested; the selected
  same-contract five-family low-stake model panel has Brier `0.198723` versus Manifold
  `0.160977`, panel-minus-market `+0.037746`, paired p=`0.5431`. This supplies
  a second market source, but it is post-hoc and inconclusive, not LLM
  superiority. The 51 Stage-C Manifold rows cannot be upgraded by reflagging:
  their records explicitly mark them as not-equal-information base-rate repair
  rows.
- No claim that worry improves Brier uniformly.
- No claim that broad selective-action prompting improves forecasts.
- No claim that the current allocation rule is deployable.
- No claim that source-currency claim is source-general until a non-Manifold pre/post panel is
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
