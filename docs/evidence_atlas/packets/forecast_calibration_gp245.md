---
description: "Evidence packet for the GP-245 LLM forecasting calibration program."
---
# GP-245 Forecast Calibration Packet

> **Up:** [Evidence Packets](README.md)

## Scoped Claim

The GP-245 program provides DB-backed apparatus evidence for a narrower
scientific claim than "LLMs forecast well": LLM forecasting behavior is
conditional on source currency, representational carrier, and auxiliary
elicitation channel. The strongest current public surface is a compact
two-document program summary plus a DB/tooling contract. The active law program
is:

1. alignment-modulated bias inheritance;
2. family-conditioned elicited-error surfaces;
3. cutoff-validity for forecasting benchmarks.

The packet also covers operational companions: no-poolability, routing, and
decision-use discipline. Deployment-policy claims remain unpromoted unless they
beat heldout Brier controls.

## Evidence Level

Mixed L2-L4 internally, depending on finding. Not L5.

- Law 1 is now a scoped negative mechanism result: the 180-call
  anti-bias-collapse smoke is executed and DB-ingested, but the clean
  `MIMIC`-specific collapse claim fails the raw-gap-adjusted control.
- Law 2 is L4 for diagnostic error-readout on the premium/worry rows because
  confidence and sham controls exist; it is not L4 for broad deployment policy.
- Law 3 is the strongest positive law candidate: the 240-call constrained
  Stage-B panel scored a post-minus-pre Brier gap of `+0.191098`; the Stage-C
  base-rate join scored `+0.255418` on joined base-rate cells; the F115
  missing-band sensitivity lower bound remains positive at `+0.127901`.
  The Stage-C market baseline audit additionally ingests 51 pre-outcome
  Manifold probabilities into the DB and shows the market bar beats the LLM
  panel overall on the joined subset while the pre-cutoff rows favor the LLM
  calls. That result is an information-timing finding, not a broad
  human/crowd comparison.
  The current blocker is second-source replication: the 2026-06-02
  Metaculus/Polymarket audit found 50 resolved post-cutoff rows but zero
  resolved pre-cutoff rows by resolution date, and emitted a 50-row
  pre-cutoff acquisition target manifest. The local void miner confirms the
  current repo/DB has 0 resolved pre-cutoff rows against that 50-row target.
- The latent/carrier intervention lane is still lower evidence than the three
  law spine. Two tiny DB-ingested smokes across Codex and Claude first favored
  structured carrier-over-prose on mean Brier (`0.098425` same-turn typed
  carrier, `0.103278` two-step carrier, `0.146103` free prose, `0.171038`
  baseline), but a later placebo-control smoke was negative for the stronger
  mechanism (`0.078000` baseline, `0.107254` two-call prose, `0.110300`
  same-turn carrier, `0.122767` free prose, `0.149921` two-step carrier over 30
  valid rows, plus 10 Codex runtime failures). The current evidence does not
  validate hard-break-beyond-carrier as a mechanism.

## Primary Sources

- [Public claim register, GP-245](../../public_claim_register.md#gp-245-forecast-calibration-program-llm-forecasting-channels--operationalization)
- [Project claim summary](../../../projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md)
- [Project methodology architecture](../../../projects/llm_forecasting_calibration_program/public/METHODOLOGY.md)
- [Forecast pool scorer](../../../scripts/public/control/forecast/pool.py)
- [Premium channel report generator](../../../projects/llm_forecasting_calibration_program/tools/premium_channel_report.py)
- [Channel holdout law report generator](../../../projects/llm_forecasting_calibration_program/tools/channel_holdout_law_report.py)
- [Channel policy-cell validator](../../../projects/llm_forecasting_calibration_program/tools/channel_policy_cell_validation.py)
- [Cutoff metadata audit generator](../../../projects/llm_forecasting_calibration_program/tools/cutoff_metadata_audit.py)
- [Cutoff candidate report generator](../../../projects/llm_forecasting_calibration_program/tools/cutoff_candidate_report.py)
- [Cutoff Stage-B balance report generator](../../../projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_slate.py)
- [Cutoff acquisition manifest generator](../../../projects/llm_forecasting_calibration_program/tools/cutoff_acquisition_manifest.py)
- [Cutoff candidate review generator](../../../projects/llm_forecasting_calibration_program/tools/cutoff_candidate_review.py)
- [Cutoff candidate ingest preview](../../../projects/llm_forecasting_calibration_program/tools/cutoff_candidate_ingest_preview.py)
- [Cutoff Stage-B freeze panel](../../../projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_freeze_panel.py)
- [Cutoff Stage-B dispatch runner](../../../projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_dispatch_runner.py)
- [Cutoff Stage-B call ingest](../../../projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_ingest_calls.py)
- [Cutoff Stage-B scorer](../../../projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_score.py)
- [Cutoff missing-band sensitivity scorer](../../../projects/llm_forecasting_calibration_program/tools/cutoff_stage_c_missing_sensitivity.py)
- [Stage-C market baseline audit](../../../projects/llm_forecasting_calibration_program/tools/market_baseline_stage_c_audit.py)
- [Truth-continuation report generator](../../../projects/llm_forecasting_calibration_program/tools/truth_continuation_report.py)
- [Cutoff second-source slate audit](../../../projects/llm_forecasting_calibration_program/tools/cutoff_second_source_slate_audit.py)
- [Cutoff second-source void miner](../../../projects/llm_forecasting_calibration_program/tools/cutoff_second_source_void_miner.py)
- [Anti-bias collapse slate builder](../../../projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_slate.py)
- [Anti-bias collapse dispatch packet generator](../../../projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_dispatch_packet.py)
- [Anti-bias collapse dispatch runner](../../../projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_dispatch_runner.py)
- [Anti-bias collapse scorer](../../../projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_score.py)
- [Law readiness report generator](../../../projects/llm_forecasting_calibration_program/tools/law_readiness_report.py)
- [High-worry action-control packet generator](../../../projects/llm_forecasting_calibration_program/tools/nurture_high_worry_action_packet.py)
- [Nurture intervention scorer](../../../projects/llm_forecasting_calibration_program/tools/nurture_intervention_score.py)
- [Hard-prompt-break packet generator](../../../projects/llm_forecasting_calibration_program/tools/nurture_hard_prompt_break_packet.py)
- [Hard-prompt-break runner](../../../projects/llm_forecasting_calibration_program/tools/nurture_hard_prompt_break_runner.py)
- [Paper claim-alignment report generator](../../../projects/llm_forecasting_calibration_program/tools/paper_claim_alignment_report.py)
- [Paper readiness report generator](../../../projects/llm_forecasting_calibration_program/tools/paper_readiness_report.py)
- [Conditional router rederivation report generator](../../../projects/llm_forecasting_calibration_program/tools/conditional_router_rederivation.py)
- [Source-balanced router audit](../../../projects/llm_forecasting_calibration_program/tools/source_balanced_router_audit.py)
- [Forecast pool README](../../../analytics/public/forecast_pool/README.md)
- [LLM forecast calibration draft](../../../papers/llm-forecast-calibration-cross-corpus/draft.md)

## Runnable Anchors

```bash
python scripts/public/control/forecast/pool.py smoke
python scripts/public/control/forecast/pool.py calibrate
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/premium_channel_report.py --out-dir projects/llm_forecasting_calibration_program/premium_channel_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/channel_holdout_law_report.py --out-dir projects/llm_forecasting_calibration_program/channel_holdout_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/channel_policy_cell_validation.py --out-dir projects/llm_forecasting_calibration_program/channel_policy_cell_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/cutoff_metadata_audit.py --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/cutoff_candidate_report.py --panel-cutoff-date 2025-10-01 --prefer-computed-cutoff --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_slate.py --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
ztare forecast cutoff-panel-run --mode preview --max-calls 6
ztare forecast cutoff-panel-run --mode live --family claude --cutoff-relation post_cutoff --max-calls 1 --timeout-seconds 180
ztare forecast cutoff-panel-run --mode live --contract-id fb_manifold_bulk_BcJbQTDX1rdmaLYGKUOz --max-calls 3 --timeout-seconds 180
ztare forecast cutoff-panel-ingest --dry-run
ztare forecast cutoff-panel-score --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/cutoff_stage_c_missing_sensitivity.py --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/market_baseline_stage_c_audit.py --commit
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/truth_continuation_report.py --out-dir projects/llm_forecasting_calibration_program/truth_continuation_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/cutoff_second_source_slate_audit.py --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/cutoff_second_source_void_miner.py --out-dir projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace
python projects/llm_forecasting_calibration_program/tools/cutoff_manifold_acquisition.py --selftest
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_slate.py --out-dir projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_dispatch_packet.py --out-dir projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace
ztare forecast anti-bias-run --mode preview --family codex_54mini --max-calls 1
ztare forecast anti-bias-score --out-dir projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace
python projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_score.py --selftest
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/law_readiness_report.py --out-dir projects/llm_forecasting_calibration_program/law_validation_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/paper_claim_alignment_report.py --out-dir projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/paper_readiness_report.py --out-dir projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/source_balanced_router_audit.py --out-dir projects/llm_forecasting_calibration_program/router_rederivation_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/nurture_high_worry_action_packet.py --out-dir projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace
ztare forecast nurture-score --pilot-id n3_high_worry_action_policy_v1 --queue projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace/n3_high_worry_action_policy_dispatch_queue.jsonl --out-dir projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace
```

## Evidence Summary

The project claim summary now compresses the prior split law matrices,
frontier scans, and protocol notes into one science-state surface. Stronger
current findings include repeated tail-premium signal, contamination analysis
for older forecasting corpora, the Stage-B/Stage-C cutoff-validity result, and
the inherit/escape/mimic bias taxonomy with raw-gap scoping.

The latest DB-backed Law 2 carrier is the premium-channel report:
`premium_batch1` plus `premium_crossfamily`, `n=341`, all rows with resolved
`y_known` and worry channels. Worry is positive against absolute error in 5/5
families and beats confidence plus sham controls in 4/5. The companion
channel-holdout report keeps the claim scoped: premium-clean has no strict
Brier-policy cell under the current filter, while `codex_55 / worry` on the
public v28 corpus-v25 holdout was the formerly sole broad strict policy
candidate.
The stricter policy-cell validator demotes that translation: temporal split
delta is only `-0.001033` with `p=0.5397`, Manifold fails source
leave-one-out, and 85.39% of positive gain comes from Polymarket. Law 2 is
therefore a diagnostic error-readout claim, not a current Brier-policy claim.
The paper claim-alignment report currently finds 0 deployment/policy overclaim
findings against the draft and TeX under that demoted policy state.
The broader paper-readiness report checks whether the draft carries the current
top-law maturity and hidden-law scoping, not just deployment wording.

The latest Law 3 carrier is the stricter cutoff-candidate report plus the
Stage-B balance report. It separates stored cutoff flags from computed
`(resolve_date, panel_cutoff_date)` relation and currently surfaces 13
stored/computed conflicts. After the 2026-06-01 Manifold ingest, the matched
candidate corpus has 40 pre-cutoff and 70 post-cutoff contracts across five
Manifold strata. The old call-level reuse evidence remains 13 pre-cutoff and
70 post-cutoff contracts with scored calls; aggregate post-minus-pre Brier is
`+0.0704` after contract/family/condition aggregation. This reuse signal is
directional only; the fresh constrained panel below is the scored Law 3
carrier.

The acquisition manifest now reports no minimum acquisition deficit. The live
API returned HTTP 503, but the official Manifold `2024-07-06` market dump
filled the minimum manifest: 27 selected rows, no remaining needs, and filters
for resolved binary rows, non-test markets, no platform self-reference, at
least 3 unique bettors, and volume at least 100. The candidate-review gate has
10 auto-clear rows and 17 advisory-flag rows. The ingest preview accepted and
inserted all 27 into the DB under
`law3_cutoff_acquisition_manifold_2026-06-01`.

The freeze panel report emits a 110-contract candidate corpus, an
80-contract balanced minimum panel, and a 240-row dispatch slate for Claude,
Codex 5.4-mini, and Gemini. The dispatch slate hash is
`6458bb811ec06f7c4b8fcf40dc16f8732df2d91a21ce3ebfa04dd1c5d679d553`.
The full panel has now fired, ingested, and scored: 240 / 240 schema-valid
calls under `cutoff_stage_b_panel_v1`, balanced 120 pre-cutoff / 120
post-cutoff rows, aggregate post-minus-pre Brier `+0.191098`, and paired
stratum delta `+0.2155` (`p=0.0004`). The current scorer verdict is
`promote_cutoff_validity_law_with_base_rate_limitation`. Its main limitation is
explicit: all 80 minimum-panel contracts have unknown base-rate band, so the
current panel is matched on source/topic/question length and computed cutoff
relation, not base rate.

The Stage-C repair now joins 51 / 80 contracts to pre-outcome probability
metadata and the joined-only base-rate cells remain positive at `+0.255418`.
Those 51 probabilities are also ingested as a narrow market baseline under
`market_baseline_stage_c_v1`: market mean Brier is `0.099673`, compared with
Claude `0.119920`, Codex 5.4-mini `0.160440`, and Gemini `0.220529` on the
same joined contracts. The relation split is the real mechanism read-out:
post-cutoff rows strongly favor the pre-outcome market bar (`0.085272` vs LLM
calls `0.309513`), while pre-cutoff rows favor the LLM calls (`0.108224`
market vs `0.082323` LLM calls). This supports the source-currency /
information-timing interpretation and is not a broad human/crowd baseline.
The F115 missing-band sensitivity report keeps the adversarial lower bound
positive at `+0.127901`. The second-source audit found that local
Metaculus/Polymarket data is post-cutoff-only by resolution date: 146
candidates, 130 joined resolution rows, 50 resolved rows, 0 pre-cutoff and 50
post-cutoff. It emitted a 16-cell, 50-row pre-cutoff acquisition target
manifest. Rows opened before cutoff are treated as an adjacent market-age
surface, not a substitute for the Law 3 resolution-date relation.
The void miner then checked the canonical DB and local source files, confirming
the current local target deficit is still 50 / 50 and that the next step is
external acquisition/backfill rather than model calls.

The latest Law 1 carrier is the executed anti-bias-collapse smoke:
`anti_bias_collapse_v1`, 180/180 schema-ok calls, 60 rows each for Claude,
Codex 5.4-mini, and Gemini, plus per-call traces. The dispatch packet validates
exact receipt coverage and the DB has one pilot run with 180 calls. The result
is a useful kill/scope: `MIMIC` mean collapse is positive (`0.0244`) versus the
`INHERIT_CONTROL` near-zero baseline (`0.000228`), but the label-shuffle
control is null (`p=0.5387`) and the raw-gap-adjusted model reverses the
MIMIC coefficient (`-0.076587`, `p=0.0025`). The original clean
MIMIC-collapse law should not be promoted without a new design that removes raw
normal-gap confounding.

The latest no-poolability companion report is mixed. A source+sigma
interpretable router beats train-best, mean, and median on a deterministic
34-row holdout, but fails source leave-one-out on Manifold and Polymarket. It
therefore supports source-fragile routing research, not a deployment-router
claim.
The newer source-balanced audit strengthens the demotion: on 123 balanced
complete-five contracts across Manifold, Polymarket, and premium-clean,
selected router + confident-NO scores Brier `0.264033`, worse than
confident-NO mean-panel `0.256288`, and only wins Polymarket among the three
major sources. Oracle family choice remains much better (`0.154933`), so
no-poolability/headroom is real but unrecovered by the current router.

The packet is strongest as an apparatus-internal forecasting-calibration
portfolio with DB-backed law candidates. It is not yet a reproducibility-grade
external benchmark.

## Non-Claims

- Does not claim LLMs cannot forecast.
- Does not claim five independent model families; codex variants are
  correlated.
- Does not claim second-lab replication.
- Does not solve corpus contamination or author-level selection leakage.
- Does not claim every finding is novel as a mechanism.
- Does not claim a universal worry sign or uniform worry-shrink policy.
- Does not claim the current conditional router is deployed; the registered
  F107 hand-router is negative on the complete-five check.
- Does not claim Halawi-style aggregate performance; the target is diagnostic
  law and validity filtering.
- Does not claim LLMs beat humans or prediction markets. The Stage-C market
  baseline is narrow and pre-outcome; broad equal-information human/crowd
  baselines are still locally absent.

## Missing Upgrade

A stronger external packet would include:

- a frozen contamination-clean external corpus;
- model cutoffs strictly before resolution dates;
- resolved contracts and per-agent calibration;
- prospective validation for any reopened routing or policy-cell improvement;
- decision-use rows showing whether forecasts changed actions;
- a prospective validation of the `codex_55 / worry` policy cell, or its
  demotion;
- second-source pre-cutoff acquisition and matched non-Manifold scoring for the
  benchmark-validity law;
- broad equal-information human/crowd or market baseline joins beyond the
  narrow Stage-C Manifold market bar;
- a redesigned anti-bias-collapse panel only if it removes the raw-gap
  confound exposed by the 180-call smoke.

This likely belongs under `projects/llm_forecasting_calibration_program/`
while the work is campaign-specific, with a public summary surfacing the result.
A reusable benchmark extracted from it can later live under `benchmarks/`.
