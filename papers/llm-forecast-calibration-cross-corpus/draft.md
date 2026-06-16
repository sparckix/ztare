# Introduction

This paper asks two questions: when is an LLM forecasting benchmark
actually measuring future-event prediction, and what has to be done
before the resulting model signal is usable?

The central result is a controlled-use claim. Some model signal remains
useful after invalid comparisons are removed, and that usefulness
depends on the information state of the row. A benchmark row should not
be used for broad conclusions until three conditions are documented.
First, *source currency*: the resolved answer was not already
source-visible to the model generation being tested. Second, *label-time
validity*: the outcome label matches what would have been knowable under
the forecast-time data vintage. Third, *equal-information baselines*:
human or market comparison bars are measured on the same contract under
the same pre-outcome information rule. In our data, the source-currency
result is strong enough to report as a measurement result. Broad human-
or market-superiority claims are not: the database has 103 typed
external market baseline rows and 52 ingested equal-information market
rows; Polymarket beats the four-family model panel on the same 24
contracts, and the separate Manifold fill favors the market but is
inconclusive.

The empirical order matters. A black-box LLM forecaster first has to be
tested on rows that are valid for its generation. Only then does it make
sense to ask which emitted channel is useful for a particular family and
source: point estimate, worry scalar, bid-ask spread, self-predicted
Brier interval, reference-class base rate, or cross-family disagreement.
Only after those two questions can we ask whether a prompt, abstention
rule, review policy, or allocation rule improves Brier or utility
against explicit controls.

The paper therefore has one main argument with two parts. The validity
part is that source-currency, label-time, and equal-information checks
change what one is allowed to conclude from LLM forecasting benchmarks.
The constructive part is that the surviving model signal is specific
rather than global: overconfident low-probability forecasts can be corrected on
source-valid forward-looking rows; pairwise comparisons can rank
harder/easier contracts better than chance under source-balanced
controls; and family-choice differences create measurable headroom that
current simple selection rules do not yet recover. The bias-transfer
material is kept only where it explains why prompt-only interventions
were fragile. This separation prevents the manuscript from becoming an
inventory of experiments.

#### Contributions.

The paper makes four contributions. First, it states a documentation
test for LLM forecasting rows: a row is not broad forecast evidence
unless source currency, label-time validity, and equal-information
comparison status are known. Second, it gives an empirical
source-currency audit in which post-cutoff Manifold rows are
substantially harder than matched pre-cutoff/source-visible rows. Third,
it reports two same-information market controls that show why raw LLM
panels are not the right unit of comparison. Fourth, it identifies the
model-derived signals that still work under controls: a source-valid
low-probability calibration rule, source-balanced pairwise ranking, mixed
but informative structured evidence-field tests, and family-choice
headroom. These are positive results, but they are not a market- or
human-superiority claim.

#### Positioning.

The closest related work now falls into four groups: future-question
benchmarks such as ForecastBench , system papers such as AIA
Forecaster , belief-updating benchmarks such as EVOLVECAST , and market
or replay environments such as Prediction Arena, PolyBench,
PredictionMarketBench, Foresight Arena, MarketBench, and Reppo-style
market infrastructure . Those systems ask how well agents forecast,
update, trade, or coordinate through market-like mechanisms. This paper
asks what has to be true before such comparisons are
interpretable at the row level. It is therefore closest in spirit to
recent evaluation-warning work on temporal leakage and benchmark
extrapolation , but adds a scored empirical audit and controlled
mechanisms for using model signal after the validity checks.

#### Evidence discipline.

Table <a href="#tab:claim-map" data-reference-type="ref"
data-reference="tab:claim-map">1</a> states the paper’s main claims and
their limits. It is included near the front because the main risk in
this area is not a missing benchmark but a wrong comparison: rows that
are source-visible, labels that use a later data vintage, market bars
measured at a different information time, or decision rules adopted
from diagnostic correlations.

<div id="tab:claim-map">

| Claim unit | Evidence in this paper | Conservative interpretation |
|:---|:---|:---|
| Validity checks | Source-currency, label-time, and equal-information audits over the database | A row without these checks is not broad forecast evidence. |
| Raw LLM panels vs markets | Polymarket scores much better than the model panel; Manifold also scores better, but inconclusively | No broad market/human superiority claim. |
| Low-probability calibration | Source-valid low-probability rule improves every family on the public-domain panel and improves the forward-looking slice | Point-probability use for source-valid rows, not retrospective correction. |
| Pairwise ranking | Source-balanced pairwise ranking and partial probability-translation evidence | Ranking/tournament support; absolute-probability use needs larger controls. |
| Evidence fields and family choice | Mixed structured-field tests; best-family-in-hindsight headroom not recovered by simple allocation rules | Evidence of where signal lives; selection rules need prospective confirmation. |
| Prompt intervention/self-repair | Selective action, self-repair, and diagnostic allocation mostly fail controls | Evidence against unvalidated prompt-only interventions. |

Main claims and limits. The central contribution is the validity layer
plus the controlled mechanisms that can extract or locate LLM forecast
signal once invalid comparisons are removed.

</div>

<figure id="fig:evidence-flow">
<table style="width:90%;">
<colgroup>
<col style="width: 22%" />
<col style="width: 34%" />
<col style="width: 34%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;"><strong>Stage</strong></th>
<th style="text-align: left;"><strong>Question answered</strong></th>
<th style="text-align: left;"><strong>Consequence</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;">Forecast row</td>
<td style="text-align: left;">What probability, source, timestamp, and
side channels did the model emit?</td>
<td style="text-align: left;">Defines the unit to be scored.</td>
</tr>
<tr>
<td style="text-align: left;">Validity checks</td>
<td style="text-align: left;">Was the answer source-visible, and is the
label valid at the relevant data vintage?</td>
<td style="text-align: left;">Decides whether the row can count as
forecast evidence.</td>
</tr>
<tr>
<td style="text-align: left;">Same-information baseline</td>
<td style="text-align: left;">What did a market or human comparator know
at the same pre-outcome time?</td>
<td style="text-align: left;">Decides whether raw model probabilities
add value under the same information rule.</td>
</tr>
<tr>
<td style="text-align: left;">Controlled use</td>
<td style="text-align: left;">Which model-derived signal improves a
proper score or ranking task after the checks above?</td>
<td style="text-align: left;">Admits only source-valid calibration,
pairwise ranking, or future family-choice rules that beat controls.</td>
</tr>
</tbody>
</table>
<figcaption>Evidence flow. The paper’s unit is a forecast row with
documented validity checks, a same-information baseline, and a
controlled decision about which model-derived signal is
usable.</figcaption>
</figure>

The paper is empirical first and theoretical second. We ran a
calibration study across five model families and two corpus classes,
with more than 30 measured findings and pre-registered tests. The main
text keeps the forecasting spine in front: validity checks,
same-information baselines, and controlled uses of model signal.
Bias-transfer and prompt-stability results are treated as secondary
diagnostics because they help explain why generic prompting is
unreliable, but they do not carry the paper’s main claim.

#### Statistical audit.

Every empirical claim is checked with the same power-aware procedure:
Fisher-$`z`$ sample-size computation before an experiment runs, three
possible outcomes after scoring (supported, ruled out at the target
effect size, or underpowered), equivalence testing instead of treating
“$`p > 0.05`$” as evidence of no effect, BH-FDR across panel tests, and
leave-one-out $`R^2`$ at small $`N`$. Under this audit, $`8`$ of $`12`$
prior nulls in the study became underpowered rather than negative
findings, and $`5`$ cross-corpus claims narrowed to corpus-specific
results. That statistical procedure is a methodological contribution
because the same overcalling problem plausibly affects existing
$`N{=}5`$–$`20`$ cross-corpus headlines. A second-order application is
corpus-validity drift: a benchmark whose resolution dates were
post-cutoff for publication-era LLMs can become pre-cutoff for the next
model generation. We apply this point to the Halawi 2024 dataset  in
$`\S`$<a href="#sec:reaudit" data-reference-type="ref"
data-reference="sec:reaudit">10</a>.

#### Reading order.

Section $`\S`$<a href="#sec:setup" data-reference-type="ref"
data-reference="sec:setup">2</a> defines the panel, corpora, and verdict
rules; $`\S`$<a href="#sec:core-results" data-reference-type="ref"
data-reference="sec:core-results">3</a> states the paper’s core
empirical results before the diagnostics. Sections
$`\S`$<a href="#sec:theoretical-frame" data-reference-type="ref"
data-reference="sec:theoretical-frame">4</a>–$`\S`$<a href="#sec:conditional" data-reference-type="ref"
data-reference="sec:conditional">[sec:conditional]</a> give the
elicitation-surface and family-heterogeneity measurements that motivated
the validity audits. Section
$`\S`$<a href="#sec:universal" data-reference-type="ref"
data-reference="sec:universal">7</a> reports the applied calibration and
allocation consequences, including the source-valid low-probability calibration and
pairwise-ranking results. Section
$`\S`$<a href="#sec:harnessing" data-reference-type="ref"
data-reference="sec:harnessing">8</a> synthesizes the supported
harnessing thesis and explains why this remains one integrated paper
rather than a split paper. Section
$`\S`$<a href="#sec:bias-transfer" data-reference-type="ref"
data-reference="sec:bias-transfer">9</a> gives the secondary
bias-transfer and prompt-stability diagnostics. The main measurement
audit is collected in
$`\S`$<a href="#sec:reaudit" data-reference-type="ref"
data-reference="sec:reaudit">10</a>: corpus-validity drift,
source-currency checks, label-time checks, market-prior repair, and
equal-information market baselines. The paper closes with explicit
limits, next tests, a conclusion, and a reproducibility plan.

# Setup

## Five LLM families

Claude Opus 4.7 (Anthropic, via Claude Code CLI), GPT-5.5 and
GPT-5.4-mini (OpenAI, via Codex CLI), Gemini 2.5 Flash (Google GenAI
API), DeepSeek Chat (DeepSeek API). All API calls
$`\text{temperature}{=}0`$ unless explicitly noted. All paths were
audited for web-search-tool access; all prompts included an explicit
instruction not to use web search.

## Two corpora, four confounded axes

We use a *low-overlap corpus* of $`N{=}15`$ bespoke questions drawn from
a private research domain with effectively zero LLM-pretraining overlap
(formal-proof tactic combinations, state-transition questions from a
private research workflow, and ground-truth-confirmed forecasting
contracts), and a *public-domain corpus* of $`N{=}42`$ contracts from
prediction markets (Manifold, Polymarket), stock-close thresholds, and
ETF moves.

| Axis | Low-overlap ($`N{=}15`$) | Public-domain ($`N{=}42`$) |
|:---|:---|:---|
| LLM pre-training overlap | Effectively zero | Substantial |
| Question length | 247 chars (35 words) | 99 chars (17 words) |
| Question structure | Multi-conditional, code/math symbols, parenthetical embedding | Atomic, simple syntactic structure |
| Implicit base rate | Ill-defined (bespoke operations) | Public-market priors well-trained |

The four axes are confounded in the current data. Low-overlap-corpus
questions are long, complex, unfamiliar, and without public priors
*together*; public-domain questions are short, simple, familiar, and
public-prior-rich *together*. The cross-corpus result
($`\S\ref{sec:frequency-framing}`$) is therefore evidence that *at least
one* of these axes matters; a 4-cell de-confounded corpus design that
breaks the confound is the highest-priority methodological follow-up
($`\S\ref{sec:limits}`$).

The low-overlap corpus is private and not publicly releasable in raw
form; the reproducibility plan ($`\S\ref{sec:repro}`$) addresses this
through a sanitized release with neutral identifiers and a parallel
public-but-niche-academic corpus matching the four-axis profile. It is
not required for the paper’s central source-currency, label-time,
equal-information, market-control, or source-valid calibration claims.
Those claims are scored from the public database, market-history
packets, official-data label-time checks, and audit scripts listed in
$`\S\ref{sec:repro}`$. Low-overlap rows are retained as secondary
diagnostics about elicitation channels, prompt stability, and external
generality.

## Pre-registration and power-aware verdicts

Every experiment is pre-registered before launch with hypothesis, null,
target effect size, $`n_{\text{required}}`$ (computed via Fisher-$`z`$
at $`\alpha{=}0.05`$ two-tailed, $`80\%`$ power, Spearman correction
$`+6\%`$), falsifiers, and success criterion. Resolution uses three
possible outcomes:

- **Supported**: 95% CI on observed $`\rho`$ excludes 0.

- **Ruled out at the target effect size**: 95% CI wholly within
  $`(-\text{target}, +\text{target})`$; data rules out a meaningful
  effect.

- **Underpowered**: observed $`|\rho|`$ below detectability at the run
  $`N`$; CI wide.

Brier-delta tests use paired-contract sign-flip permutation with a 90%
bootstrap CI plus a BIC-approximation Bayes factor. “No effect” claims
also require TOST equivalence at a pre-stated bound. Power thresholds at
$`\alpha{=}0.05`$ / power$`=0.80`$:
$`N{=}15 \Rightarrow |\rho| \geq 0.68`$; $`N{=}42 \Rightarrow 0.43`$;
$`N{=}91 \Rightarrow 0.30`$.

# Core empirical results

The rest of the manuscript gives the diagnostics behind these claims.
The core evidence is the following.

<div id="tab:core-results">

| Result | Evidence | Paper use |
|:---|:---|:---|
| Source-currency validity matters | Matched Manifold Stage-B panel: 80 contracts / 240 tool-free calls; post-minus-pre Brier $`+0.191098`$, paired-stratum delta $`+0.2155`$, permutation $`p=0.0004`$. | Candidate measurement result: forecast rows need source-currency checks. |
| Raw panels do not beat same-information markets | Polymarket replacement: panel $`0.267758`$ vs market $`0.072964`$, $`p=0.0068`$. Manifold second source: panel $`0.198723`$ vs market $`0.160977`$, $`p=0.5431`$. | Boundary: no LLM market/human superiority claim. |
| Low-probability calibration extracts point-probability signal under scope | Raw mean-panel remains $`+0.029598`$ Brier worse than the low-probability correction on rows with adequate source and label-time documentation, but the rule regresses source-visible rows. | Source-valid calibration view, not universal correction. |
| Pairwise ranking extracts relative signal under scope | Source-balanced pairwise packet: 24 unique non-tie pairs, accuracy $`0.750`$, utility $`+0.583`$, $`p=0.0044`$ vs random. | Ranking/tournament support, not standalone probability. |
| Prompt intervention/self-repair mostly fails | Selective action, generic self-repair, and diagnostic allocation fail or regress against controls. | Simple prompting is not enough. |

Core empirical results. The diagnostic sections explain how these
results were found and where they fail; this table states the claims
that remain after source, label-time, and market-baseline controls.

</div>

This ordering is deliberate. The paper’s constructive claims are
downstream of the same-information market controls. A harnessing
mechanism is included only when it either improves a proper score on
valid rows, supports a controlled ranking use, or locates signal that a
future decision rule could try to recover. Mechanisms that only change
rationales, increase stated effort, or improve a source-visible
retrospective slice are reported as diagnostics or failed interventions.

| Same-information slice | Model panel Brier | Market Brier |
|:---|---:|---:|
| Polymarket, 24 contracts | 0.267758 | 0.072964 |
| Manifold, 24 contracts | 0.198723 | 0.160977 |

Equal-information market controls. Lower Brier is better. Polymarket
clearly scores better than the model panel; Manifold also scores better,
but inconclusively. These controls rule out a raw LLM-superiority claim
for the current evidence.

# Why emitted forecast channels differ by family

Before reporting the elicitation findings, we name the structural
distinctions that organized the measurements. These were not stated in
advance; they are a compact reading of the body of findings the study
produced. Their role in this paper is explanatory: they help explain why
side channels and prompt interventions are family- and
source-conditional, not why LLMs should be expected to beat markets.

#### Elicitation surface.

An LLM forecaster, when asked, emits a set of channels: at minimum a
point estimate $`p_{\text{success}}`$; optionally a tail-worry scalar
(“how worried are you?”), a bid-ask spread
$`(p_{\text{buy yes max}}, p_{\text{sell yes min}})`$, a self-predicted
Brier interval $`(b_{\text{lo}}, b_{\text{hi}})`$, an asymmetric-loss
decision threshold under specified false-positive vs. false-negative
cost regimes, or an outside-view base rate from analogous prior
contracts. Training-mix differences across model families produce
different elicitation surfaces, even when prompted identically.
$`\S\ref{sec:bid-ask-spread}`$ introduces the bid-ask spread as a
diagnostic error-warning channel that is elicitable on the low-overlap
corpus; $`\S\ref{sec:channel-orthogonality}`$ shows the three
uncertainty channels are statistically independent on a paired panel,
motivating per-family channel analysis; $`\S\ref{sec:multi-channel-r2}`$
shows only one family generalises a multi-channel decomposition under
leave-one-out cross-validation.

#### Behavioral structured-field interpretation.

We do not observe the hidden activations of the closed models used here,
so our channel claims are behavioral rather than
mechanistic-interpretability claims. Still, the right unit is closer to
a structured intermediate representation than to the generated
rationale. Recent latent-prediction theory shows that learning or
predicting hidden representations can avoid the sample-complexity cost
of token-level prediction on hierarchical data . Our setting is not
training-time latent prediction, but the analogy is useful here:
uncertainty channels and source-bound evidence fields can be scored
against outcomes, while free-form rationale text is a noisy surface
output. In two small follow-up tests across two families, structured
evidence fields beat free prose on mean Brier, while the stricter
two-step variant did not consistently beat a same-turn field. The
combined means were baseline $`0.171038`$, free prose $`0.146103`$,
two-step field $`0.103278`$, and same-turn field $`0.098425`$. A later
placebo-control test weakened the claim: among the 30 rows with complete structured outputs,
baseline mean Brier was $`0.078000`$, two-call prose $`0.107254`$,
same-turn field $`0.110300`$, free prose $`0.122767`$, and two-step
field $`0.149921`$; ten additional Codex rows failed at runtime before
emitting forecasts. This is not an established mechanism. It leaves structured
evidence fields as a hypothesis for larger paired tests, but argues
against treating the stronger two-step break as an established
mechanism.

#### Bias-transfer diagnostic.

We also tested whether human-style cognitive-bias categories predicted
LLM forecast distortions. The useful distinction is representational:
some biases have a large natural-language footprint, some depend on
human utility or affect, and some are heavily discussed in case-study
text even though the model has no corresponding utility function. This
distinction helped organize prompt-risk and family-sensitivity tests,
but it did not establish a forecasting intervention. In the 180-call
anti-bias-prompt test, the average collapse pattern was underpowered,
the class-label shuffle was null ($`p=0.5387`$), and the
raw-gap-adjusted coefficient for text-discussed motivational cases was
negative ($`-0.076587`$, $`p=0.0025`$). A matched audit using the stored rows also
found poor support overlap: at raw-gap caliper $`0.05`$, within-family
matching left only 16 with-replacement / 15 no-replacement pairs and
flipped the estimated collapse effect negative ($`-0.072750`$,
$`p=0.0008`$; greedy no-replacement $`-0.077561`$, $`p=0.0006`$), while
the no-caliper positive estimate relied on large raw-gap distances. The
supported claim is therefore diagnostic: bias-category measurements help
explain prompt fragility, but a causal cognitive-debiasing intervention
requires new matched strata or randomization.

#### Family/post-training overlay.

Family identity and post-training choices reshape per-family channel
surfaces, but this paper observes only cross-family contrasts and does
not identify the causal role of RLHF. Family-level worry/error sign
differences ($`\S\ref{sec:worry-direction-split}`$), per-family
channel-decomposition $`R^2`$ differences
($`\S\ref{sec:multi-channel-r2}`$), and the self-assessed channel-choice
failure where three of five families pick the worse channel at
$`p \leq 0.005`$ each ($`\S\ref{sec:conditional}`$) all live on this
axis. The empirical signature is that family identity, conditional on
channel and contract, is itself a central predictor.

#### The methodological backbone is orthogonal to the three axes.

A power-aware scoring discipline (Fisher-$`z`$ power calculation before
launch, three possible outcomes after scoring, equivalence testing,
BH-FDR, LOO-$`R^2`$ at small $`N`$) sits underneath every axis-1/2/3
measurement. The discipline produced the study’s most consequential
retraction: 8 of 12 prior “no effect” claims became underpowered rather
than negative findings, and the corpus-validity-drift filter
(resolve_date $`>`$ `max(panel_cutoff)`) empties the most-cited 2024
LLM-forecasting benchmark for the current LLM generation
($`\S\ref{sec:reaudit}`$).

# Elicitation diagnostics: channels are conditional, not decision rules

<span id="sec:worry-direction-split"
label="sec:worry-direction-split"></span>
<span id="sec:cognitive-decoupling"
label="sec:cognitive-decoupling"></span> <span id="sec:bid-ask-spread"
label="sec:bid-ask-spread"></span> <span id="sec:channel-orthogonality"
label="sec:channel-orthogonality"></span>
<span id="sec:frequency-framing" label="sec:frequency-framing"></span>
<span id="sec:worry-mechanism" label="sec:worry-mechanism"></span>
<span id="sec:multi-channel-r2" label="sec:multi-channel-r2"></span>
<span id="sec:conditional" label="sec:conditional"></span>

The uncertainty-channel experiments explain why raw probabilities alone
are insufficient, but they are not themselves decision rules. We
elicited worry scalars, bid-ask spreads, trajectory variance, frequency
framings, self-predicted Brier intervals, outside-view base rates, and
self-assessments about which channel should predict error. The pattern
is consistent across these probes: LLMs emit useful side information
about contracts, families, and sources, but the side information is
conditional. It changes sign by family, weakens under task-difficulty
controls, and often fails when moved from a low-overlap corpus to
public-domain market questions.

<div id="tab:elicitation-diagnostics">

| Diagnostic | Main evidence | Manuscript role |
|:---|:---|:---|
| Worry scalar | Pool-level worry is a positive tail-risk signal at $`N{=}590`$, but per-family worry-Brier signs split. Claude and GPT-5.5 can be most worried when most right, while GPT-5.4-mini is direction-sensible. Topic-trigger and mean-regression probes explain the sign flip better than rationale length, wallclock time, or hedging vocabulary. | Use worry as a behavioral channel only after conditioning on family, corpus, and source. It is not a universal calibration transform. |
| Cognitive text versus calibration | Failure-mode words in rationales are weakly positive for the original trio but near zero for Gemini and DeepSeek at roughly $`N{=}60`$ per family. Stake framing raises worry for every family while leaving point probabilities nearly unchanged. | The model can produce diagnostic language without recomputing the forecast from that language. This supports interface discipline, not free-form chain-of-thought reliance. |
| Bid-ask and frequency probes | Bid-ask spread is positive on the low-overlap corpus for GPT-5.4-mini and DeepSeek, but public-domain replication is underpowered or sign-flipped. Frequency framing improves GPT-5.4-mini on low-overlap questions and does not transfer to the public corpus. | These are promising elicitation probes. They do not justify a source-general policy. |
| Orthogonality and multi-channel fits | Worry, spread, and trajectory variance are nearly uncorrelated at expression level. Early same-forecast $`R^2`$ survives leave-one-out only for GPT-5.5 on the $`N{=}42`$ public corpus; the larger five-family audit gives negative leave-one-out $`R^2`$ for channel-only Brier prediction across all five families. | Channels are distinct measurements, but distinct does not mean ready for use. They are useful for diagnosis and design of later scoring rules. |
| Conditional structure and family allocation | Sub-source decomposition flips channel signs across yfinance, Manifold, and Polymarket cells. Pooled channel value collapses after task-difficulty controls. Easy-contract cells show headroom, hard cells overfit, and naive mean/median panels do not beat the best single family. | Forecast signal lives in family-by-source-by-contract interactions. Current observable allocation rules find headroom but do not yet recover it under controls. |

Uncertainty-channel experiments as diagnostics. The shared lesson is
conditionality: emitted channels can locate signal, but they have not
become source-general probability rules.

</div>

The channel material has a narrow role in the argument. The diagnostics
support one claim needed for the harnessing thesis: raw LLM forecasts
contain more structure than a single probability, and that structure
requires label-time-valid scoring, source and family splits, and
comparison against simple baselines before use.

Several negative results are central. Channel-only decision rules that
look attractive in small or low-overlap cells fail under larger
leave-one-out checks or source controls. Models can identify contracts
that feel leaky or risky without translating that feeling into better
probabilities. Self-assessed channel selection can even be
anti-coherent: in the low-overlap channel-choice probe, three of five
families often selected the channel that was worst for their own error.
These failures motivate the paper’s emphasis on source-valid
calibration, pairwise ranking, source-specific checks, and future
allocation tests rather than generic self-monitoring or prompt-only
intervention.

# Additional all-channel diagnostics

The all-channel prompts collected several side measurements in a single
forecast pass or as paired conditions. Five additional findings emerge
at $`N{=}131`$–$`142`$ public-domain:

**Rollback hurts.** A self-counterfactual prompt (“imagine you were
trained only up to 2023, emit a rollback forecast”) worsens Brier for 4
of 5 families at $`N{=}142`$ paired ($`\Delta`$ Brier
rollback$`-`$normal: claude $`+0.064`$, codex-5.5 $`+0.034`$,
codex-5.4-mini $`+0.028`$, deepseek $`+0.028`$, gemini $`-0.005`$).
Post-2023 training is net-useful even though families cannot introspect
which contracts benefit. *Practical caution:* avoid “imagine you knew
less” framings on forecasting tasks without a heldout correction check.

**Leakage agreement without calibration.** On the same rollback prompt,
all 10 pairwise $`\rho(|\text{leak}_A|, |\text{leak}_B|)`$ between
families are $`\geq +0.43`$ (claude $`\leftrightarrow`$ codex-5.5
$`\rho{=}+0.80`$). Families agree on which contracts feel high-leakage.
Per-family $`\rho(|\text{leak}|, \text{err}^2)`$ is nevertheless
equivalent to zero for all five at the $`\pm 0.30`$ target.
Self-reported leakage is a contract-structural signal, not a per-family
calibration channel. It is useful as a corpus-curation filter for
low-leakage LLM-fresh tests.

**DeepSeek’s emitted decision threshold is calibrated.** In an
asymmetric-loss decision-threshold prompt (commit-YES threshold under
symmetric / YES-bad-3$`\times`$ / NO-bad-3$`\times`$ loss),
Codex-5.4-mini emits the most Bayes-coherent thresholds (mean YES-bad
$`0.750`$, exact match). For DeepSeek,
$`\rho(\text{threshold\_yes\_bad}, \text{err}^2) = -0.19`$, $`95\%`$ CI
$`[-0.35, -0.03]`$ at $`N{=}142`$. The emitted threshold tracks accuracy
for one family. This is a novel diagnostic channel; policy use requires
a heldout utility test.

**Stake-framing amplifies worry universally, leaves $`p`$ unchanged.**
Same contract framed as “\$1 stake” vs “\$100K stake” across 103–142
paired contracts per family. Worry-scalar amplifies for every family
($`\Delta\text{worry}`$ from $`+10.8`$ deepseek to $`+33.5`$ claude on
the 1–100 scale). But $`|\Delta p_{\mathrm{success}}| < 0.03`$ for every
family. This cognitive-shift-without-calibration-shift result connects
the cognitive-decoupling result to the stake-framing and risk-amplitude
literature in human decision-making .

**Self-assessed channel choice fails for three of five families.** A
channel-choice prompt (“which of your own uncertainty channels best
predicts your error?”) reveals systematic anti-coherence at $`N{=}15`$
on the low-overlap corpus: claude, codex-5.5, and deepseek pick the
worse channel $`87\%`$ of the time (binomial $`p{=}0.005`$ each). Within
those picks, $`\rho(\text{picked}, \text{err}^2)`$ is negative while
$`\rho(\text{unpicked}, \text{err}^2)`$ is strongly positive (claude
$`+0.51`$, codex-5.5 $`+0.53`$, deepseek $`+0.65`$). The candidate
inversion rule is: when these three families claim “worry is my best
channel,” test spread instead (or the analogous flip). Codex-5.4-mini is
coherent ($`73\%`$ right); gemini is random. Companion finding to the
per-family worry sign-flip, on a new axis. This result is
low-overlap-only at $`N{=}15`$; cross-corpus replication at $`N{=}42`$
external is pre-registered. The pattern (LLMs have contract-level
structural intuitions without calibration to truth) recurs across the
rollback, leakage, decision-threshold, and channel-choice results, the
defining negative finding about LLM self-monitoring.

# Applied calibration and allocation consequences

The channel and family diagnostics become useful only if they change a
scored forecast or a decision rule. This section separates three
evidence grades: robust enough for a source-valid calibration view,
useful as a design clue, and unsupported as an applied rule.

<div id="tab:applied-patterns">

| Pattern | Evidence | Status |
|:---|:---|:---|
| Low-probability overconfidence | In the lowest forecast quintile, every family underpredicts YES outcomes; gaps range from $`+0.34`$ to $`+0.72`$. | Basis for the low-probability calibration rule, subject to source-currency checks. |
| Horizon and source difficulty | Longer horizons have higher Brier ($`\rho=+0.161`$, 95% CI $`[+0.026,+0.290]`$); Polymarket is harder than Manifold, which is harder than yfinance for every family. | Design clue; not enough alone for an applied rule. |
| YES underprediction | On contracts resolving YES ($`N=26/42`$), every family’s mean $`p_{\text{success}}`$ is below $`0.5`$. | Supports calibration diagnostics. |
| Panel agreement and naive ensembles | Cross-family forecast correlations are high (mean $`\rho=+0.72`$); mean/median-of-five have higher Brier than the best single family on the $`N=142`$ paired set. | Warns against naive averaging. |

Cross-family regularities that motivated calibration and allocation
tests. They are useful only when converted into a scored rule and
compared with simple baselines.

</div>

The composed four-rule recipe converted these patterns into a scored
forecast by applying a low-probability discount, a middle-band YES
correction, a horizon shrinkage, and a source-difficulty shrinkage to
the mean panel forecast. The recipe beats naive aggregation on the same
$`N=142`$ paired set, but it does not clear the stronger best-single and
source-balanced policy bars.

<div id="tab:composed-adjustment">

| strategy | Brier | $`\Delta`$ vs. best-single | 90% CI | $`p_{\mathrm{perm}}`$ |
|:---|:--:|:--:|:--:|:--:|
| median-of-5 | $`0.272`$ | $`+0.018`$ | – | – |
| mean-of-5 | $`0.261`$ | $`+0.007`$ | – | – |
| best-single (Claude) | $`0.254`$ | – | – | – |
| adjusted aggregate (universal-only) | $`0.232`$ | $`-0.022`$ | $`[-0.050, +0.005]`$ | $`0.18`$ |
| adjusted aggregate (per-channel) | $`0.246`$ | $`-0.009`$ | $`[-0.035, +0.016]`$ | $`0.58`$ |

Composed adjustment on the $`N=142`$ paired public-domain set. The
within-cohort win is against naive aggregation, not against the
strongest simple correction.

</div>

Three points matter. First, the adjusted aggregate improves over naive
aggregation within this cohort: it beats median-of-five by $`-0.040`$
Brier ($`p=0.0013`$) and mean-of-five by $`-0.029`$ ($`p=0.0069`$).
Second, the comparison with the best single family remains underpowered:
the point estimate is favorable ($`-0.022`$) but the paired test is
$`p=0.18`$, with an estimated $`N\approx250`$–$`300`$ required for the
observed effect. Third, later source-balanced audits weaken the
composite. The current source+$`\sigma`$ allocation rule and
diagnostic-triggered allocation have higher Brier than simpler rules;
Hedge over raw-family, low-probability-adjusted-family, and simple-pool
experts is directionally better but nonsignificant ($`0.226481`$ versus
$`0.233529`$, $`p=0.4671`$) and regresses on Manifold in the balanced
slice. Choosing the best family in hindsight remains far better
($`0.117454`$ Brier), so family-choice headroom exists, but the
observable rules have not recovered it.

The pairwise ranking packet supports a controlled relative-judgment use.
A source-balanced four-family contrastive packet supports pairwise
ranking over 24 unique non-tie pairs (accuracy $`0.750`$, utility
$`+0.583`$, $`p=0.0044`$ versus random). Translation tests are favorable
but not yet ready as a point-probability layer: same-packet
translated-minus-low-probability-correction is $`-0.022714`$ with $`p=0.0628`$; one
cross-packet direction clears $`p=0.0314`$, the reverse direction misses
at $`p=0.0636`$; and the joined market-control slice is only 24 rows
with translated-vs-market $`p=0.5783`$. A prospective Polymarket packet
has frozen 24 pairwise market bars before model calls, but unresolved
outcomes cannot support a current scoring claim. Pairwise ranking
therefore appears in the paper as a controlled use, while the current
point-probability rule remains the low-probability calibration rule.

**The low-probability correction as a standalone rule beats raw on every
family at $`p<0.05`$.** The rule applies only when the panel forecast is
below $`0.20`$, shrinking that low forecast toward $`0.10`$ by
$`\hat p_{\mathrm{low}} = 0.35\bar p + 0.65(0.10)`$. The simpler form of
the recipe, the single low-probability discount applied per-family
without the other three rules, improves per-family Brier on every panel
member at $`p < 0.05`$:

| family | raw Brier | discounted Brier | $`\Delta`$ | paired $`p_{\mathrm{perm}}`$ |
|:---|:--:|:--:|:--:|:--:|
| claude | $`0.2543`$ | $`\mathbf{0.2240}`$ | $`-0.0302`$ | $`0.016`$ |
| codex-$`5.5`$ | $`0.2625`$ | $`0.2416`$ | $`-0.0208`$ | $`0.030`$ |
| codex-$`5.4`$-mini | $`0.2714`$ | $`0.2450`$ | $`-0.0264`$ | $`0.015`$ |
| deepseek | $`0.3222`$ | $`\mathbf{0.2704}`$ | $`\mathbf{-0.0518}`$ | $`\mathbf{0.0008}`$ |
| gemini | $`0.3167`$ | $`0.2840`$ | $`-0.0327`$ | $`0.008`$ |

Discounted Claude at Brier $`0.2240`$ is at parity or better than the
four-rule adjusted aggregate ($`0.232`$), so the additional features add
little on this corpus. The single low-probability adjustment improves Brier
at $`p<0.05`$ across every model family, including DeepSeek and Gemini,
which were not the panel that originated the rule. A
fitted-calibrator audit using the stored rows did not identify a better
replacement: source-isotonic slightly improved the overall point
estimate but lost Manifold and was nonsignificant, while tail-beta
shrinkage was worse. The 2026-06-04 source-documented rerun excludes 10
yfinance/yfinance\_etf complete panels lacking label-time documentation,
leaving 132 panels; source-isotonic remains unsupported at
$`-0.005248`$ Brier versus the low-probability correction with paired
$`p=0.7099`$, while raw mean-panel is $`+0.029598`$ worse. A later
source-currency stress audit narrows the rule: it improves post-cutoff
rows ($`-0.025326`$, tail-only $`-0.101306`$) and regresses
pre-cutoff/source-visible rows ($`+0.035016`$, $`p=0.0002`$; tail-only
$`+0.097719`$, $`p=0.0002`$). A row-level rerun through the shared
source-currency discriminator leaves those scores unchanged while
exposing 39/240 stored-flag-vs-computed-relation conflicts. The
low-probability rule is therefore forward-looking calibration tied to
computed cutoff and label-time documentation, not retrospective
benchmark correction.
# Harnessing LLM forecast signal under constraints

The equal-information market controls change the paper’s question. The
defensible unit is a validated and controlled forecast row: the
completed Polymarket slice clearly favors the market, and the Manifold
second-source slice favors the market but is inconclusive. The useful
finding is that the market result does not make the LLM signal
disappear. It changes which part of the signal can be used. In the
current evidence, the usable pieces are a source-valid calibration rule,
a pairwise ranking task, and measurable family-choice headroom. These
mechanisms belong in the same paper because they depend on the same
measurement foundation that makes the market controls interpretable.

**The low-probability rule is the current point-probability use case.** The
low-probability discount is the strongest practical rule in the database.
It improves every tested family on the public-domain panel, including
families that were not used to originate the rule. On source-documented
rows the raw mean-panel remains worse than the low-probability correction by $`+0.029598`$
Brier with paired $`p=0.0062`$. On the source-currency stress panel, the
same rule improves post-cutoff rows by $`-0.025326`$ while regressing
pre-cutoff/source-visible rows by $`+0.035016`$ with $`p=0.0002`$. This
is the pattern in miniature: the rule extracts signal from the
forward-looking slice and damages retrospective/source-visible rows. It
is therefore a source-valid calibration view, not a universal
correction.

**Pairwise ranking is the current relative-judgment use case.** The
strongest positive ranking evidence supports relative judgment rather
than absolute probability. A source-balanced same-source/minimal-pair
packet gives 24 unique non-tie pairs with accuracy $`0.750`$, utility
$`+0.583`$, $`p=0.0044`$ versus random, and $`p=0.0002`$ versus source
control. Later probability-translation tests are favorable in one
direction, while the required single-contract probability checks remain
unmet: same-packet translated-vs-low-probability-corrected and translated-vs-raw
checks, bidirectional cross-packet transfer, joined market control, and
prospective causal-order resolution are not all satisfied. The supported
use is pairwise ranking or tournament support.

**Interface and family-choice evidence shows where the next gain could
come from.** Structured evidence fields are plausible because some small
tests favor typed fields over free prose, but the placebo-control
continuation is negative for the stronger two-step claim. Family choice
has real headroom: choosing the best family in hindsight reaches much
lower Brier than current decision rules, and family-by-contract
interaction is substantial. Current observable selection rules do not
recover that headroom: source-balanced selection fails source controls,
Hedge over raw, low-probability-corrected, and simple-pool experts is directionally better but not
significant, and graph-family weighting is small and fragile. These
results locate signal; they do not yet supply a reliable
family-selection rule.

**Prompt-only improvement survives only as failed evidence plus a
narrower interface hypothesis.** Generic reflective prompting, selective
action, and self-repair do not reliably improve forecasts under
controls. The tested prompt-intervention variants either fail
confirmation, overcorrect, produce no measurable change, or underperform
low-probability calibration. This does not rule out tool-using,
retrieval-grounded, expert-written, or heldout-tuned prompting systems.
It does rule out the simple claim that asking the model to reason
harder, repair itself, or act selectively is enough to improve forecast
probabilities.

The manuscript therefore stays integrated for now. The positive
mechanisms depend on the same validity checks that make the market
controls interpretable. A later split is justified only if prospective
ranking, calibration, and family-choice evidence becomes large enough to
support an independent mechanisms paper.

# Secondary diagnostics: bias transfer and prompt stability

<span id="sec:prompt-invariance" label="sec:prompt-invariance"></span>
<span id="sec:freq-framing-test" label="sec:freq-framing-test"></span>

The bias-transfer and prompt-stability experiments are not the paper’s
central contribution. They appear in the main text as diagnostics for
why naive prompt interventions and family-general allocation should not
be trusted.

**Bias transfer.** Three novel-bias tests on the same $`N=30`$
public-domain contracts across five families found a structured split:
loss-frame and probability-weighting probes were close to symmetric or
near-linear, while current-state/status-quo framing moved several
families substantially. A held-out seven-bias slate later supported the
representational distinction between text-discussed motivational cases
and direct utility-like mechanisms. The anti-bias-prompt companion test
was weakened by raw-gap controls, and the out-of-distribution slate was
inconclusive and confounded by cross-family pretraining differences. We
therefore use these results only to interpret family/source sensitivity
and prompt-risk, not to claim that cognitive-debiasing prompts improve
forecasting skill.

**Prompt stability.** The prompt-invariance audits give the same warning
from another angle. Standard forecast prompts yield relatively stable
point estimates across all five families, but reference-class
outside-view prompting is a different reasoning architecture rather than
a harmless paraphrase. The worry channel is much noisier across prompts
than $`p_{\text{success}}`$, and cross-prompt worry-Brier signs can
reverse relative to the low-overlap experiment. Any decision rule that
depends on a verbal uncertainty channel must therefore be treated as
family-, corpus-, and prompt-bound until it clears heldout controls.

These diagnostics bound the harnessing thesis: model signal does not
become reliable through generic reflection, debiasing, or self-repair.
It becomes usable only when the interface is tied to a scored channel, a
source-valid calibration rule, a pairwise ranking task, or a predeclared
allocation rule that beats simpler controls.

# The re-audit discipline: a warning to the field

The discipline that produced the results above also produced a re-audit
of the study’s own prior findings. We treat the re-audit itself as a
contribution because the same overcalling pattern almost certainly
affects the published LLM-forecasting literature at the sample sizes it
currently reports.

## Power calculus applied to our own study

Before applying the power-aware audit, eight prior “no effect” or
“cross-corpus replication” claims in the study had been written down as
findings. Applying the Fisher-$`z`$ audit retrospectively:

- Four “null” findings move from ruled out to underpowered: the data did
  not actively rule out a meaningful effect at the per-family target
  $`|\rho|`$ floor; the absence-of-signal was an absence-of-power.

- Five cross-corpus claims move from “replicated” or
  “failed-to-replicate” to corpus-specific: the original cross-corpus
  reading was a single sub-source point estimate at $`N{=}5`$–$`15`$
  external, with CIs that crossed zero and with sub-source heterogeneity
  unmodeled.

- One self-knowledge-inversion finding (originally three families at
  $`N{=}5`$) retracts to a single family at $`N{=}15`$ on the
  low-overlap corpus; the other two cross-corpus directions flip on
  rerun.

- Two per-family decision rules (Brier-$`\Delta`$ map and
  *consider-both-sides* effect) move from usable to “directional
  hypothesis only”; the required $`N`$ to confirm a
  $`\Delta_{\mathrm{Brier}}{=}0.05`$ effect at 80% power is
  $`\approx 459`$ per family, an order of magnitude above the original
  $`N{\approx}30`$ per cell.

In aggregate, $`\approx 50\%`$ of the study’s prior conclusions changed
under the power-aware re-audit. None of the underlying executions were
flawed. The interpretation discipline was.

## A worked example: the per-family worry sign-flip retest

The previous Gemini worry-channel hypothesis was scope-restricted to
“low-overlap corpus, original prompt only” pending a
$`\sim`$<!-- -->42-call retest of the same prompt on the public-domain
$`N{=}42`$ slice used by the other public-domain tests. The retest, run
with the same worry-only prompt on `gemini-2.5-flash` via API:

- Schema-OK: $`42/42`$.

- $`\rho(\mathrm{worry}, \mathrm{Brier}) = +0.110`$ – the
  direction-correct direction, not the inverted direction the prior rule
  had assumed.

- Fisher-$`z`$ detectable $`|\rho|`$ at $`N{=}42`$, $`80\%`$ power:
  $`\geq 0.43`$. Observed $`|\rho|{=}0.11`$ is well below this; the CI
  excludes the original “inverted” direction ($`\rho < -0.30`$).

- The inversion hypothesis is ruled out at the target effect size; the
  direction-correct point estimate remains underpowered for the positive
  hypothesis.

The Gemini channel rule stays withdrawn. The earlier “inversion” claim,
estimated from $`N{=}5`$ with $`N_{\mathrm{wrong}}{=}2`$, was a
sample-size effect. This is the lowest-cost decisive retest available;
two comparable retests remain open.

## Implications for the published LLM-forecasting literature

Two prominent $`2024`$ contributions to LLM forecast calibration are
(a) the ensemble-prediction result that a 12-LLM aggregate matches
human-crowd Brier on real binary questions  and (b) the
retrieval-augmented LLM that approaches human-superforecaster accuracy
on a contamination-resistant slice . Both report claims at sample sizes
that, under the same Fisher-$`z`$ power calculus we apply to our own
study, are limited by:

- For a Brier-delta $`\Delta{=}0.05`$ comparison (LLM ensemble vs. human
  crowd) at $`80\%`$ power, paired permutation requires
  $`N{\geq}300`$–$`500`$ per side.

- For a per-model rank correlation $`|\rho|{=}0.30`$ at the same power:
  $`N{\geq}91`$.

- For a per-(model, sub-source) cell at $`|\rho|{=}0.40`$: $`N{\geq}50`$
  per cell – requiring sub-source $`N{\geq}250`$ across five families
  when sub-sources are five-way mixed.

We do not re-analyse those datasets here; we observe only that the
standard “2024-style” aggregate claim is structurally compatible with
the same overcalling failure mode our own study exhibited. Paleka et
al.  make the broader version of the same warning: LLM forecasting
evaluation is unusually vulnerable to temporal leakage, unreliable
date-restricted retrieval, benchmark extrapolation errors, and circular
comparisons against human forecasts already visible to the model or
retrieval system. Consistency-check benchmarks offer a complementary way
to probe coherence before outcomes resolve , but they do not remove the
need for resolved, same-information scoring. The methodological gap this
paper targets is a consistent power-aware audit: every claim labelled
with one of three possible outcomes, $`n_{\mathrm{required}}`$
pre-computed before launch, sub-source heterogeneity reported alongside
the aggregate, and prior verdicts re-audited under the same calculus as
new ones.

The external bar has also moved since those papers. The recent
literature now has four distinct benchmark classes.

- **Future-question benchmarks.** ForecastBench makes future-only
  benchmark generation explicit and reports expert forecasters
  outperforming the top LLM on its initial human/LLM sample . AIA
  Forecaster reports human-superforecaster-level performance on
  ForecastBench and additive value when ensembled with market consensus,
  while also finding that the system underperforms market consensus
  alone on a harder liquid-market benchmark .

- **Belief-updating benchmarks.** EVOLVECAST tests whether LLM forecasts
  move appropriately when new post-cutoff information is supplied, and
  reports partial responsiveness but inconsistent or overly conservative
  updates relative to human references . That result is complementary to
  our label-time and source-currency checks: both settings show that a
  forecast row is not defined only by the final event label, but also by
  the information state available when the probability is produced.

- **Trading and replay benchmarks.** Prediction Arena evaluates agents
  with real capital on Kalshi and Polymarket and finds platform-specific
  performance differences rather than a generic forecasting edge .
  PolyBench records timestamp-locked Polymarket order-book/news
  snapshots and reports that most models have negative returns despite
  high stated confidence . PredictionMarketBench emphasizes
  execution-realistic replay because profit and loss mix probability
  accuracy with fees, liquidity, position sizing, and settlement risk .

- **Market-as-evaluation infrastructure and coordination.** Reppo-style
  systems position prediction markets as an AI-training and evaluation
  substrate . Foresight Arena separates proper probabilistic scoring
  from trading profit by using commit-reveal forecasts and an
  alpha-over-market score; its power analysis estimates that detecting a
  small edge over market consensus requires hundreds of resolved binary
  predictions . MarketBench studies a related coordination problem:
  agents are miscalibrated about their own success probability and cost,
  and capability information improves that calibration only modestly .
  That result aligns with our family-choice findings: conditional
  headroom can exist even when current observable selection rules do not
  safely recover it.

Read against that literature, the present paper is not a live-market
benchmark or an autonomous-trading evaluation. Its distinct contribution
is the validity layer those benchmarks now make unavoidable: before
comparing an LLM, a market, and a human, the row must specify what was
source-visible, what label vintage is admissible, and whether the
baseline was measured under equal information. This is also why evidence
that markets score better is scientifically useful. If an LLM has higher
Brier after the information state is equalized, the remaining question
is whether any model-derived signals remain usable under calibration,
ranking, and family/source constraints.

**What a field-wide audit would measure.** The evidence in this paper is
enough to show that row-level validity can change conclusions in this
program. It is not yet enough to claim that the same failure rate holds
across the field. A field-wide audit would treat each benchmark row as
the unit of analysis and record the following checks before comparing
model, human, or market scores:

| Audit check | What must be recorded | Why it matters |
|:---|:---|:---|
| Source currency | Forecast timestamp, model cutoff or retrieval window, resolution date, and whether the resolved answer was source-visible at generation time. | Separates future-event prediction from retrieval or source familiarity. |
| Label-time validity | Outcome label, label source, data vintage, and any later revisions or settlement-rule changes. | Prevents scoring against values that were not admissible at resolution time. |
| Equal-information comparator | Human, crowd, market, or agent baseline measured on the same contract at the same pre-outcome information time. | Prevents comparing a model forecast with a comparator that knew more or less. |
| Effective sample size | Event-family identifiers, source strata, repeated sibling markets, and family/model repetition. | Prevents row-rich but event-thin conclusions. |
| Decision rule status | Whether the tested rule was predeclared, tuned on the same rows, or evaluated prospectively. | Separates exploratory diagnostics from supported use. |

Field-wide validity-audit protocol. The present manuscript supplies this
protocol and a scored within-program audit; a cross-benchmark
failure-rate claim requires applying the protocol to several public
benchmark families.

For reproducibility, `field_wide_validity_audit_protocol.py` emits the
row schema and benchmark seed matrix. The companion
`field_wide_validity_local_evidence.py` records the local Halawi
date-distribution summary with its limitation: the raw benchmark rows
are not present locally, so this is a warning about a likely replication
filter, not a completed external row audit.

## Source-currency, label-time, and equal-information audit

The central re-audit result is that benchmark validity is a moving
target. A dataset that was a fair future-event benchmark for one model
generation can become a retrieval or source-familiarity benchmark for a
later generation. The local claim register records a Halawi 2024
binary-resolved date histogram with no 2025-or-later resolutions; for
current model generations, the corresponding eligibility filter,
*resolve_date $`>`$ max(panel_cutoff)*, would leave zero rows in that
local summary. This is not a replacement for a raw-row external audit,
but it is the concrete corpus-validity drift warning that motivates the
field-wide protocol.

<div id="tab:reaudit-lanes">

| Audit lane | Current evidence | Conclusion |
|:---|:---|:---|
| Manifold source-currency panel | 80 matched contracts / 240 tool-free calls; post-minus-pre Brier $`+0.191098`$, paired-stratum delta $`+0.2155`$, permutation $`p=0.0004`$. Partial market-prior repair joins 51 contracts and leaves the effect positive under adversarial missing-band sensitivity. | Strong candidate measurement result: source-visible and post-cutoff rows cannot be pooled without documentation. |
| Manifold pre-outcome market bar | On the 51 repaired contracts, market Brier is $`0.099673`$ versus joined LLM-panel $`0.166963`$ overall; market+LLM blending is unsupported ($`p=0.794`$). These rows are typed as not-equal-information external baselines. | Useful diagnostic comparison, but not a broad human/crowd baseline. |
| Polymarket source check | Gemini and DeepSeek aggregate post-minus-pre directions are positive, but matched source/topic/length strata are null or opposite-sign. The initial seven-day market-price freeze design only fills 4/24 rows; horizon sweep tops out at 12/24. | Diagnostic evidence, not a source-general replication or usable equal-information design. |
| Polymarket replacement equal-information packet | Replacement sampling on 2026-06-15 selects 24 one-per-event rows from 80 eligible candidates at a two-day freeze horizon, 14 NO / 10 YES, all open-by-target with nonempty CLOB history. The four-family panel has higher Brier than the market: panel $`0.267758`$ vs market $`0.072964`$, paired $`p=0.0068`$. | Clear same-information market advantage. |
| Manifold equal-information packet | Public API history fill validates 24/24 rows, 15 NO / 9 YES. Selected five-family panel Brier is $`0.198723`$ vs Manifold $`0.160977`$, panel-minus-market $`+0.037746`$, paired $`p=0.5431`$. | Second-source comparison; market advantage is directional and inconclusive. |
| FRED / official-data lane | Fixed one-year FRED companion supplies 49 pre-cutoff rows; full paired post-minus-pre delta is only $`+0.016477`$ ($`p=0.30375`$). Blinded-control apparent current-label penalty collapses from $`+0.024719`$ to $`-0.002989`$ after vintage repair. | Official-data diagnostic lane; label-time checks are required before current-label positives count. |
| Metaculus target cells | Current authenticated endpoints expose post/question payloads but not resolved binary values plus dated aggregate history for the sampled rows; data-download endpoint is restricted. | Remains a data-access question, not a negative result. |

Re-audit evidence by lane. The paper’s broad comparison claims depend on
source currency, label-time validity, and equal-information status, not
merely on model-call volume.

</div>

The source-currency panel is matched on source, topic, question-length
bucket, and cutoff relation. Reliable base-rate bands are not available
for that panel, so base-rate matching remains a stated limitation rather
than a hidden control. The database now contains 103 external market
baseline rows: 51 not-equal-information Manifold diagnostic rows, 4
equal-information Polymarket rows from the failed seven-day packet, 24
equal-information Polymarket rows from the replacement packet, and 24
equal-information Manifold rows from the 2026-06-15 history fill. The
two completed 24-row equal-information slices are the relevant market
controls for this manuscript. They do not support raw LLM superiority:
Polymarket is decisively better, and Manifold is directionally better
but underpowered.

This audit changes what the paper can support. The Manifold
source-currency result is strong enough to report as a
measurement-validity contribution. The FRED work shows why label-time
repair is not optional for official-data questions. The
equal-information market rows rule out a broad market/human superiority
claim while sharpening the harnessing thesis: useful LLM signal has to
be extracted through source-specific calibration, pairwise ranking,
structured interfaces, or future allocation rules that beat the
market/human bar under the same information rule.

## The applied consequence

The re-audit rule: *a per-family or per-(family, sub-source) decision
rule should be treated as supported only when its supporting CI has been
computed on $`N{\geq}n_{\mathrm{required}}`$ at the target effect size,
and only with sub-source stratification reported.* Three remaining
low-cost retests ($`\sim 0`$, $`42`$, and $`420`$ calls respectively)
close the same gap on the study’s other decision-rule hypotheses; their
results are published alongside the existing rules as the retests
complete.

# What this paper does not establish

- It does not show that LLMs beat humans, human crowds, or prediction
  markets. The database has 103 external market baseline rows, including
  52 equal-information market rows across Polymarket and Manifold. On
  the completed 24-contract Claude+Codex+Gemini+DeepSeek Polymarket
  replacement slice, the market baseline beats the four-family model
  panel. On the separate 24-contract Manifold fill, the market is also
  ahead of the selected five-family low-stake model panel, but the
  paired comparison is inconclusive. Broad superiority would require
  predeclared or sufficiently powered source-balanced baselines under
  the same pre-outcome information rule.

- It does not establish translated pairwise probabilities as a
  standalone probability layer. Pairwise ranking survives as
  source-heldout evidence with promising translation tests, but
  same-packet, cross-packet, market-control, and prospective
  causal-order checks remain incomplete.

- It does not establish a source-general source-currency result beyond
  the main Manifold panel. Polymarket tests are aggregate-positive but
  matched-stratum null/opposite-sign, and FRED current-label positives
  weaken under label-time/vintage repair.

- It does not show that cognitive-debiasing interventions never transfer
  to LLMs. Four of five tested effects are underpowered at our
  low-overlap-corpus $`N`$, not falsified.

- It does not establish that GPT-5.4-mini’s low-overlap-corpus
  frequency-framing improvement would survive cross-corpus replication
  at proper power. $`N{\geq}91`$ public-domain is required.

- It does not generalize beyond five model families and two corpus
  classes. The low-overlap corpus is private and not publicly available
  in raw form.

- It does not decompose LLM *reasoning* mechanistically. The
  channel-orthogonality claim ($`\S\ref{sec:channel-orthogonality}`$) is
  at the *expression* level; a reasoning-decomposition claim would need
  white-box mechanistic interpretability.

- The four-axis confounding between corpora means the cross-corpus
  result is evidence that at least one axis matters, not yet a clean
  attribution. The 4-cell de-confounded corpus is the most important
  methodological follow-up.

- It does not establish that RLHF/alignment *causes* the per-family bias
  differences. Every result in that group, in-distribution and
  out-of-distribution, is a *cross-family* contrast, which confounds
  alignment with pretraining-corpus differences; families differ in
  both. The apparent “more alignment, less bias transfer” ordering also
  runs opposite to the established result that instruction-tuning
  amplifies several cognitive biases . The supported claim is therefore
  observational—*family identity predicts bias magnitude*—not a causal
  post-training explanation. Isolating the alignment stage requires
  within-family checkpoints (pre- vs post-RLHF) or matched-pretraining
  families, which we do not have.

- Bid-ask spread cross-corpus is currently underpowered; the
  direction-shift is suggestive but not conclusive at $`N{=}42`$.

- The worry-Brier sign-flip mechanism is provisional
  ($`\S\ref{sec:worry-mechanism}`$ multi-probe synthesis);
  activation-level probing and a topic-matched corpus would settle it.

- Per-family signal strength is conditional on prompt-invariance
  ($`\S\ref{sec:prompt-invariance}`$). Gemini and DeepSeek findings
  should be read with the prompt-stability discount documented there
  until the within-family paraphrase test is run.

#### Next tests.

Table <a href="#tab:next-tests" data-reference-type="ref"
data-reference="tab:next-tests">7</a> states the evidence
required to strengthen each claim. The most direct route to a broader
measurement contribution is a field-wide validity audit of public
forecasting benchmarks and market-replay environments. That route does
not require LLMs to beat markets; it requires showing that row-level
source-currency, label-time, or equal-information checks are often
missing and can change conclusions. A broad LLM-vs-market or
LLM-vs-human claim requires a predeclared or substantially larger
source-balanced equal-information packet that beats the market/human
baseline, not more calls on the current rows. A source-general
source-currency claim
requires Metaculus/export access or another non-Manifold panel with
matched pre/post resolution-date coverage and label-time documentation.
Pairwise ranking becomes a standalone probability layer only if
same-packet, cross-packet, market-control, and prospective causal-order
checks all clear. The main route to a stronger intervention paper is a
public structured-metacognition experiment: bare prompt, length-matched
placebo, expert-training prompt, audit-informed prompt, and
failure-mode-specific prompt on the same source-valid external corpus.
The low-overlap-corpus findings become externally general only after a
sanitized release or a public niche-domain replication. A companion
evidence matrix records each candidate result, the checks it has
passed, the checks still missing, and the next decisive test. If those
tests fail or remain underpowered, the paper remains what the present
evidence supports: a measurement-validity contribution with controlled
calibration and ranking consequences.

<div id="tab:next-tests">

| Claim to strengthen | Evidence required | Current status |
|:---|:---|:---|
| Field-wide benchmark validity | Row-level audit of public forecasting benchmarks and market-replay environments, recording source currency, label-time validity, equal-information status, and conclusion changes after repair. | Not claimed here; current evidence shows the failure mode inside this program, not field-wide prevalence. |
| LLM vs. market/human performance | Predeclared, source-balanced equal-information packet with enough resolved rows to beat the market or human baseline under proper scoring. | Not supported; current equal-information slices favor markets or are inconclusive. |
| Source-general source-currency result | Non-Manifold panel with matched pre/post rows, admissible label vintage, and base-rate documentation. | Supported on the main Manifold panel; other sources remain diagnostic. |
| Pairwise ranking as probability layer | Same-packet and cross-packet ranking replication plus prospective probability translation against raw, calibrated, and market controls. | Ranking use supported; probability translation remains provisional. |
| Structured metacognition intervention | Pre-reviewed public-corpus experiment comparing bare prompt, length-matched placebo, expert-training prompt, audit-informed prompt, and failure-mode-specific prompt under source-valid scoring. | Designed as the strongest continuation test; the partial 131/600 Gemini run does not yet support the intervention claim. |
| Structured evidence fields | Larger balanced paired test that beats free prose, same-turn fields, and two-call prose after runtime failures are included. | Hypothesis only. |
| Family allocation | Predeclared observable features or independent reviewer source that recovers best-family headroom after cost. | Headroom exists; current allocation rules do not recover it. |
| External generality of low-overlap results | Sanitized release or public niche-domain replication that breaks the current novelty/source/topic/horizon confound. | Not yet established. |

Next tests. These are evidence requirements, not additional claims
made by the present manuscript.

</div>

# Conclusion

The main lesson is measurement-first. LLM forecasting evaluations are
not interpretable merely because the model output is a probability and
the event later resolves. The row must specify what was source-visible
to the model generation, whether the label uses an admissible time
vintage, and whether the human or market comparison was measured under
the same information rule. In this study, those checks change the claim:
the Manifold source-currency panel supports a measurement-validity
result, while the same-information Polymarket and Manifold market
comparisons rule out a raw LLM-superiority reading of the current
evidence.

The constructive claim is substantive because it identifies where model
signal survives strong controls. The usable unit is not the raw panel
probability. The current evidence supports source-valid low-probability
calibration, pairwise ranking as a relative-judgment task, structured
evidence fields as a hypothesis, and family-choice headroom as a target
for future selection rules. It also shows that generic reflection,
self-repair, and simple prompt intervention are not enough. The paper’s
contribution is therefore a validity layer plus a map of which
model-derived signals remain worth testing once invalid comparisons are
removed.

Future work should not try to rescue the broad claim with more calls on
the same rows. The decisive tests are a field-wide row-validity audit,
prospective or larger source-balanced equal-information packets,
non-Manifold source-currency panels with label-time documentation, and
predeclared mechanisms that beat raw, calibrated, and market controls
under the same information state.

# Reproducibility

All model calls persist as JSONL files and are ingested into the SQLite
database at `analytics/public/calibration/forecaster_calibration.db`.
Pre-registrations and verdict resolutions are in the same database. The
reusable general-purpose statistics module is at
`src/ztare/experiment_stats.py` (power calculator, bootstrap CI, paired
permutation, Fisher-$`z`$ Spearman, TOST, BH-FDR, power-aware verdict,
BIC Bayes factor, reproducibility hash). Forecasting-specific wrappers
are in the per-project `calibration_stats.py`; the public methodology
file lists the exact commands for each finding.

**Reproducing the scope checks.** Three audit scripts define the scope
boundary:

- `paper_readiness_exhaustion_audit.py`
- `paper_coherence_audit.py`
- `independent_equal_information_source_audit.py`

Equal-information acquisition is split into deterministic scripts:

- `equal_information_baseline_export_packet.py`

- `equal_information_baseline_result_ingest.py`

- `equal_information_freeze_feasibility_audit.py`

- `equal_information_horizon_sweep.py`

- `equal_information_replacement_sample_acquire.py`

- `equal_information_replacement_dispatch_packet.py`

- `equal_information_replacement_score.py`

- `non_polymarket_equal_information_export_packet.py`: emits the current 24-row Manifold packet for a second
  equal-information source.

- `non_polymarket_equal_information_result_acquire.py`: fills the packet from public Manifold history.

- `non_polymarket_equal_information_result_ingest.py`: ingests the validated rows.

- `non_polymarket_equal_information_score.py`: scores the joined model-vs-market comparison.

- `claim_gap_matrix.py`: emits an evidence matrix separating supported results from
  underpowered results, claims not valid for broad conclusions, and claims requiring external data.

Together these tools let a reader verify the current market-baseline
coverage, inspect the replacement packet before forecasts, reproduce the
first same-contract market comparison, and see exactly what evidence is
still missing for a broad human/crowd claim or stronger intervention
claim.

**Reproduction status.**
Table <a href="#tab:reproduction-status" data-reference-type="ref"
data-reference="tab:reproduction-status">8</a> separates what is
reproducible now from what requires a sanitized or substitute release.
The private low-overlap corpus is the main unreleased component, but it
affects only the secondary low-overlap elicitation findings. The
source-currency, label-time, equal-information, market-control, and
source-valid calibration claims are represented by public-market,
official-data, database, scoring, and audit machinery in the repository.

<div id="tab:reproduction-status">

| Component | Current status | Reproduction role |
|:---|:---|:---|
| SQLite evidence database | Present at `analytics/public/calibration/forecaster_calibration.db`. | Reproduces call counts, score joins, source-currency screens, label-time screens, and market-baseline coverage. |
| Scoring/audit scripts | Present in the project tool directories and listed above. | Recomputes the paper’s readiness, coherence, equal-information, and label-time checks without new model calls. |
| Evidence matrix | Present at `projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.csv`. | Lists each candidate result, its current evidence, missing checks, what would change the interpretation, and next action. |
| Public-market packets | Present for Polymarket and Manifold equal-information comparisons. | Reproduces the market-control boundary claims. |
| Raw low-overlap questions | Not publicly releasable in raw form. | Needed only for direct replication of the private low-overlap elicitation findings. |
| Sanitized or substitute low-overlap corpus | Planned release path: neutralized identifiers plus a public niche-domain substitute with the same four-axis profile. | Enables third-party replication of the frequency-framing, bid-ask, and low-overlap channel findings without exposing private workflow details. |

Reproduction status. The central source-currency and equal-information
claims are reproducible from public project files; the low-overlap
channel findings require a sanitized or substitute corpus.

</div>

# Evidence ledger for compressed diagnostics

The main text compresses several experiment families for readability.
Table <a href="#tab:evidence-ledger" data-reference-type="ref"
data-reference="tab:evidence-ledger">9</a> records what was compressed
and what insight is retained. The detailed run records remain in the
SQLite database, the project workspace, and the public
methodology/claim-summary files referenced in $`\S\ref{sec:repro}`$.

<div id="tab:evidence-ledger">

| Compressed family | Retained insight | Where it is used |
|:---|:---|:---|
| Uncertainty channels | Worry, spread, trajectory variance, self-predicted Brier, and outside-view base rates expose distinct side information, but their sign and value are family/source conditional. | Motivates source/family conditioning and prevents a universal channel-rule claim. |
| Self-assessed channel choice | Several families misidentify which emitted uncertainty channel predicts their own error. | Supports the negative self-monitoring result and the need for scored interfaces. |
| Universal calibration regularities | Low-probability overconfidence, horizon/source difficulty, YES underprediction, and high family agreement recur across families. | Supplies the candidate features tested by the low-probability rule and composed adjustment. |
| Composed adjustment and family-choice headroom | The adjusted aggregate beats mean/median in-cohort but fails stronger source-balanced scrutiny; choosing the best family in hindsight remains much better than observed allocation rules. | Separates real headroom from established allocation evidence. |
| Pairwise ranking and translation | Pairwise contrastive ranking is stronger than raw probability translation; translation remains promising but is not yet supported as a standalone probability model. | Retains pairwise ranking as a controlled use, not a market/human superiority claim. |
| Source and label-time audits | Manifold source-currency, FRED vintage repair, failed Polymarket freeze design, replacement Polymarket, and Manifold equal-information fill show that validity checks change conclusions. | Forms the measurement-validity contribution and bounds the constructive claims. |
| Prompt intervention/self-repair | Generic reflection, self-repair, and diagnostic allocation mostly fail or produce no measurable change under controls. | Turns prompt-only improvement into a narrower interface hypothesis rather than a standalone claim. |

Evidence-preservation table for compressed diagnostics. Compression
changes placement, not the underlying scope boundaries.

</div>

# Coverage audit for omitted or deferred work

The project log contains many more experiments than the main paper
reports. The inclusion rule is conservative: a result appears in the
main text only if it changes the validity layer, a supported use case, a
stated limit, or a continuation test.
Table <a href="#tab:coverage-audit" data-reference-type="ref"
data-reference="tab:coverage-audit">10</a> records the main excluded or
deferred families so that compression does not hide evidence.

<div id="tab:coverage-audit">

| Work family | Why it is not a main claim | How the insight is preserved |
|:---|:---|:---|
| Prompt-intervention variants | Generic reflection, selective action, self-repair, and diagnostic-triggered allocation do not beat the relevant controls. | Reported as negative evidence for unvalidated prompt-only interventions and as a test for future tool-using or retrieval-grounded systems. |
| Objective effort / coding-task calibration | This is a sibling problem about effort prediction and hidden-test performance, not the same forecast-row validity question. | Excluded from GP-245 unless it later supplies a forecasting-specific intervention that clears source and market controls. |
| Proof-audit and workflow-only findings | These improve the research workflow but ask reviewers to switch domains away from event forecasting. | Excluded from the main manuscript; relevant only as provenance for the audit discipline. |
| Low-overlap elicitation retests | Several channel findings are promising but still corpus-bound or underpowered for source-general claims. | Preserved as diagnostics and continuation tests: replicate on a public niche corpus or sanitized release before generalizing. |
| Fitted calibrators and allocation rules | Source-isotonic, graph-family weighting, and diagnostic allocation have not beaten simpler controls robustly. | Reported as headroom evidence; applied use waits for source-balanced panels or an external reviewer/market expert. |
| Prospective market-freeze packets | Frozen market bars exist for some future comparisons, but unresolved outcomes cannot score current claims. | Listed as continuation tests; no standalone probability layer until outcomes resolve and market/raw/low-probability controls are passed. |
| Deconfounded corpus design | The current low-overlap/public split confounds novelty, source, topic, and horizon. | Treated as the key methodological follow-up for external generality, not as evidence already in hand. |

Coverage audit for work compressed out of the main text. The table
separates omission for irrelevance, omission for weak evidence, and
deferral because the right outcome data or control does not yet exist.

</div>

# Composed adjustment recipe: closed form

Let $`\bar p`$ be the mean of the five families’ point estimates
$`p_{\text{success}}`$ on a given contract, $`h`$ the
days-to-resolution-from-cutoff, and
$`s\in\{\textrm{polymarket}, \textrm{manifold}, \textrm{yfinance}\}`$
the source identifier. The composed adjusted forecast $`\hat p`$ is:

``` math
\begin{aligned}
\hat p_{\mathrm{low}} &= \begin{cases} 0.35\,\bar p + 0.65\,(0.10) & \text{if } \bar p < 0.20 \\ \bar p & \text{otherwise} \end{cases} \\
\hat p_{\mathrm{YES\text{-}bias}} &= \hat p_{\mathrm{low}} + \begin{cases} +0.06 & \text{if } 0.30 \le \hat p_{\mathrm{low}} \le 0.55 \\ 0 & \text{otherwise} \end{cases} \\
\hat p_{\mathrm{horizon}} &= 0.5 + (\hat p_{\mathrm{YES\text{-}bias}} - 0.5)\cdot \tfrac{1}{1 + 0.01\,h} \\
\hat p &= 0.5 + (\hat p_{\mathrm{horizon}} - 0.5)\cdot w_s
\end{aligned}
```

with $`w_s = 0.70`$ for polymarket, $`0.85`$ for manifold, $`1.00`$ for
yfinance. The four coefficients $`(0.10, 0.06, 0.01, w_s)`$ are not
learned from held-out folds; they are chosen from the universal patterns
reported in $`\S\ref{sec:universal}`$ (low-probability overconfidence,
middle-band YES underprediction, horizon-conditional Brier slope,
per-source Brier ordering). The per-channel alternative described in the
main text substitutes per-family channel weights for the universal
$`w_s`$; its weights are listed in the appendix companion file. The
implementation is in the forecasting-calibration workspace and
reproduces on the database snapshot dated 2026-05-28.
