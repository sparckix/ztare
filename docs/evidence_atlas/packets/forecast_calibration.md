---
description: "Review packet for the LLM forecasting calibration program."
---
# Forecast calibration packet

> **Up:** [Review Packets](README.md)

## Current paper surface

The current paper source and review bundle are organized under
`llm-forecast-calibration-cross-corpus/`, with the lean public paper mirror at
`papers/llm-forecast-calibration-cross-corpus/`. The paper claim is:
LLM forecasting rows require source currency, label-time, and equal-information
documentation before a proper score can support a forecasting comparison. After those
checks, the current evidence supports a source currency measurement result,
strict but small equal-information market comparisons that rule out raw model
panel superiority in the present evidence, and limited uses of model-derived
signal in calibration and pairwise relative judgment. The Gemini prompt result
is treated as a replication target; it is not stated as a general prompt method.

Current abstract:

> LLM forecasting benchmarks often score model calls before establishing whether
> the scored row is a valid forecast. A row may ask a model to recover an answer
> already visible to its generation, use an outcome label from a later data
> vintage, or compare against a market or human baseline measured under a
> different information state. We define the forecast row as the unit of evidence
> and introduce three validity requirements: source currency, label-time
> validity, and equal-information baselines. Applying this framework across five
> model families and more than 20,000 persisted calls changes the interpretation
> of the evidence. In a matched panel of 80 Manifold contracts, rows after the
> model cutoff are substantially harder than rows before the cutoff or visible in
> the model's sources (`+0.191` Brier in aggregate, paired-stratum delta
	> `+0.216`, permutation `p=0.0004`). The strict market comparisons remain small,
	> so we use them to bound claims rather than to estimate a general market
	> advantage. On 24 Polymarket contracts, the four-family panel scores `0.268`
	> Brier versus the market's `0.073` (`p=0.0068`). A 24-contract Manifold slice
	> also favors the market but is inconclusive; a separate 32-contract Manifold
	> same-day freeze expansion scores `0.215` for the five-family panel versus
	> `0.136` for the market (`p=0.0048`). These controls do not establish a general
	> result about markets and models, but they rule out raw model panel superiority
	> in the present evidence. After validity screening, model signal
> remains narrow. A simple rule that tempers very small model probabilities
> improves those estimates on eligible rows, and pairwise comparisons achieve
> `0.750` accuracy over 24 non-tie pairs when the pairs are balanced across
> sources. One expert-training prompt improves Brier in a completed 600-call
> Gemini experiment on public questions, but partial Claude and staged
> Codex+DeepSeek replications do not reproduce the effect, so we treat it as a
> Gemini result to replicate rather than a general prompting method. The contribution is forecast row validity: a practical
> documentation layer for source, label, and comparator timing; an empirical
> demonstration that these checks change conclusions; and a companion benchmark
> design that scores row validity, equal-information comparison, calibration,
> relative judgment, intervention, choosing among model families, open model
> replication, and public low-overlap replication as separate tracks.

## Scoped claim

The paper makes a measurement claim and two bounded applied claims.

- Measurement claim: a scored forecast row is not broad forecasting evidence
  until source currency, label-time validity, and equal-information comparison
  status are documented.
- Applied claim 1: a calibration rule improves eligible probability estimates,
  but regresses source-visible rows and therefore is not a universal
  retrospective correction.
- Applied claim 2: pairwise comparisons show useful relative
  judgment signal, but the current evidence does not establish a standalone
  probability layer.

The Gemini expert-training prompt is now described as a Gemini intervention
finding and replication target. It is not stated as a general prompting method
because the partial Claude and staged Codex+DeepSeek checks do not reproduce it.

## Evidence level

L4: controlled source currency checks, equal-information baselines,
calibration, and pairwise-judgment evidence over tracked public or reviewable
corpora. The paper is a scoped validity manuscript with no broad
model-superiority claim.

- Source-currency evidence: matched Manifold panel with 80 contracts and 240
  tool-free calls. Post-cutoff rows score `+0.191098` Brier worse in aggregate,
  paired-stratum delta `+0.2155`, permutation `p=0.0004`.
- Equal-information market controls: three strict same-contract slices.
  Polymarket decisively beats the four-family model panel (`0.072964` vs
  `0.267758`, `p=0.0068`). The first Manifold slice also favors the market, but
  inconclusively (`0.160977` vs `0.198723`, `p=0.5431`). A separate 32-contract
  Manifold same-day freeze expansion again favors the market (`0.135951` vs
  `0.214665`, `p=0.0048`). These controls block raw model panel superiority in
  the current evidence. They do not estimate a general effect comparing markets
  and models.
- Calibration evidence: the rule for very small model probabilities improves
  eligible estimates, with the important boundary that it regresses
  source-visible rows.
- Pairwise evidence: pairwise comparison has 24 unique non-tie
  pairs, accuracy `0.750`, utility `+0.583`, and `p=0.0044` against random.
- Prompt-intervention evidence: the 600-call Gemini public question comparison
  passes the paired Brier gate against bare, length-matched placebo, and
  calibrated bare forecasts. The partial Claude check is not supportive. The
  staged Codex+DeepSeek check has 445 scored calls and is worse than bare and
  placebo on mean Brier, with no sign-test support and no support across sources, so this
  remains a replication target, not a general prompt method.

## Primary sources

- [Tracked paper draft](../../../papers/llm-forecast-calibration-cross-corpus/draft.md)
- [Tracked TeX source](../../../papers/llm-forecast-calibration-cross-corpus/main.tex)
- [Tracked bibliography](../../../papers/llm-forecast-calibration-cross-corpus/refs.bib)
- [Project claim summary](../../../projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md)
- [Project methodology architecture](../../../projects/llm_forecasting_calibration_program/public/METHODOLOGY.md)

## Runnable anchors

```bash
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/paper_claim_alignment_report.py --out-dir projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/rendered_pdf_smoke_audit.py --out-dir projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/rendered_pdf_smoke_2026_06_17
PYTHONPATH=. ./venv/bin/python projects/llm_forecasting_calibration_program/tools/submission_readiness_audit.py --out-dir projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/submission_readiness_2026_06_16
```

## Evidence summary

Like strong evaluation-standard papers, this manuscript defines the unit of evidence, shows that the missing unit changes conclusions, states the bounded tools that survive, and makes the missing evidence explicit enough for another group to reproduce or extend.

The main denominator constraint is the equal-information market sample. The two
strict market control slices each have 24 contracts. That is enough to block a
raw model panel superiority reading in the present evidence, especially on
Polymarket, but it is not enough to characterize market and model
performance across sources, horizons, liquidity regimes, or event families.
The expansion protocol therefore requires either strict backfill from
auditable pre-outcome market histories or a prospective freeze before model
calls. The current local 100-row non-Polymarket export pass surfaced only 10
eligible Manifold request rows, so local backfill does not solve the denominator
problem.

On prompting, the design tested bare forecasting, length-matched placebo, expert-training, audit-informed, and failure-mode-specific prompts on the same public question rows. It asks whether a structured forecasting instruction moves scored probabilities, not whether the rationale sounds better. Gemini passes the primary paired gate. Claude and Codex+DeepSeek do not reproduce the effect. The paper therefore treats the prompt as a candidate interface to replicate, not a general improvement method.

Best-family-in-hindsight scores appear as headroom only. Families make different errors, but choosing the best family after seeing outcomes is not a usable rule. A future model-selection result needs observable features, outside review, market disagreement, or held-out model signals that recover some of that headroom prospectively after cost.

## Non-claims

- The paper does not show that LLMs beat humans, human crowds, or prediction
  markets.
- The paper does not estimate a general market control effect from the two
  24-contract equal-information slices.
- The paper does not establish the Gemini expert-training prompt as a method
  that generalizes across sources or providers.
- The paper does not establish external generality for the private
  low-overlap corpus diagnostics.
- The paper does not establish a working rule for choosing among model families.
- The paper does not claim a measured failure rate across the field.

## Missing upgrade

The strongest next upgrade is a prospective or strict-backfill
equal-information packet with at least 100 resolved contracts, at least two
market sources when source access permits, event family clustered uncertainty,
hidden market prices in the prompts, and predeclared comparisons among
market-only, raw model panel, calibration on eligible rows, pairwise-derived
ranking or probability where applicable, and
market-plus-model blends.

The second upgrade is a complete second-family replication of the
expert-training prompt under the same bare, placebo, calibrated bare, and
checks split by source. The active Codex+DeepSeek packet should be completed or
stood down under its predeclared gate. An open model packet is the next clean
provider-independent route. A positive prompt result should count only if it
beats those controls on the same rows and does not disappear when matched
market or human baselines are available.

The third upgrade is a public low-overlap substitute that separates novelty,
source, topic, question length, and base rates, which the current single
corpus contrast confounds together.

## Companion benchmark tool

The paper now includes a small runnable validator at
`papers/llm-forecast-calibration-cross-corpus/evidence/benchmark/`. It validates
forecast rows against the paper's row contract and scores only the rows whose
source, label, and comparator timing are documented. This is not the larger
market-control expansion. It is the tool that makes the row-validity
standard executable for future packets.
