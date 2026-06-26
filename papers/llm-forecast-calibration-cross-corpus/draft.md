# When Does an LLM Forecasting Benchmark Measure Forecasting?

Source Currency, Label-Time Validity, and Equal-Information Controls

## Abstract

LLM forecasting benchmarks often score model calls before establishing whether
the scored row is a valid forecast. A row may ask a model to recover an answer
already visible to its generation, use an outcome label from a later data
vintage, or compare against a market or human baseline measured under a
different information state. We define the forecast row as the unit of evidence
and introduce three validity requirements: source currency, label-time validity,
and equal-information baselines. The database contains more than 20,000
persisted calls, but the inferential units in this paper are not calls: the
central source-currency and market-control tests use 24--80 contracts, pairwise
ranking uses 24 non-tie pairs, and prompt-intervention checks use 90--120
contract-condition blocks. In a matched panel of 80 Manifold contracts, rows
after the model cutoff are substantially harder than rows before the cutoff or
visible in the model's sources (`+0.191` Brier in aggregate, paired-stratum
delta `+0.216`, permutation `p=0.0004`, BH `q=0.0031`, BY `q=0.0115`). The
strict market comparisons remain small, so we use them to bound claims rather
than to estimate a general market effect. On 24 Polymarket contracts, the
four-family panel scores `0.268` Brier versus the market's `0.073`
(`p=0.0068`, BH `q=0.0163`, BY `q=0.0616`). In a 24-contract Manifold slice,
the market Brier is lower but the paired test is inconclusive; a separate
32-contract Manifold same-day freeze expansion scores `0.215` for the
five-family panel versus `0.136` for the market (`p=0.0048`, BH `q=0.0163`, BY
`q=0.0616`). Smaller Manifold horizon checks are reported only as overlapping
sensitivity checks. These controls do not establish a general result about
markets and models, and they do not support raw model panel superiority: two
strict slices have much lower market Brier under the raw paired tests and BH
correction, but the BY column treats them as sensitivity rather than
arbitrary-dependence significance at `0.05`; the third strict slice is
inconclusive. After validity screening, model signal remains narrow. A selected rule
that tempers very small model probabilities improves those estimates on eligible
rows, and pairwise comparisons achieve `0.750` accuracy over 24 non-tie pairs
when the pairs are balanced across sources. One expert-training prompt improves
Brier in a completed 600-call Gemini experiment on public questions, but a
591/600-call Claude run remains underpowered and below the replication gate and
a staged Codex+DeepSeek check does not reproduce the effect. We therefore treat
it as a Gemini-specific candidate, not a general prompting method. The
contribution is forecast row validity: a practical documentation layer for
source, label, and comparator timing; an empirical demonstration that these
checks change conclusions; a power-aware re-audit that reclassifies underpowered
prior results instead of treating them as nulls; a consolidated multiplicity and
effective-denominator audit; and a companion benchmark design
that scores row validity, equal-information comparison, calibration, relative
judgment, intervention, choosing among model families, open model replication,
and public low-overlap replication as separate tracks.

# Introduction

This paper introduces forecast row validity as a documentation standard for LLM
forecasting benchmarks. The motivating questions are simple: when is a scored
row actually measuring future-event prediction, and what conditions are needed
before model outputs can be interpreted or used?

The central result is that LLM forecast output becomes interpretable only
after the information state of each row is made explicit. The starting point is
an estimand problem. A forecasting leaderboard can assign a proper score to
every row and still mix three different tasks:
predicting a future event, recovering an answer already latent in the model's
sources, and comparing against a human or market that saw different
information. A benchmark row is
suitable for broad conclusions only after three conditions are documented.
First, *source currency*: the resolved answer was not already visible in the
sources available to the model generation being tested. Second, *label-time
validity*: the outcome label matches what would have been knowable under the
data vintage at forecast time. Third, *equal-information baselines*: human or
market comparison bars are measured on the same contract under the same
information rule before outcome.
In our data, the main Manifold source-currency audit is strong enough to report
as a measurement result for that source. It is not yet a source-general
prevalence estimate. Broad claims that the models beat humans or markets are not
supported: the database has 170 typed external market baseline rows and 119
ingested equal-information market rows, but the completed strict controls are
still modest. They include 24 Polymarket contracts, a 24-contract Manifold fill,
a separate 32-contract Manifold same-day freeze expansion, and smaller Manifold
one-day, two-day, and seven-day checks on overlapping rows. We use them as
strict controls on the present evidence, not as population estimates of market
or LLM performance. Within that scope, Polymarket has lower market Brier than
the four-family model panel on the same 24 contracts, the first Manifold fill has lower market Brier
but an inconclusive paired test, and the 32-contract Manifold expansion again
has lower market Brier under the raw paired test and BH correction, with BY
sensitivity reported below. The smaller one-day, two-day, and seven-day Manifold
checks are sensitivity rows because they overlap the same source and remain too
small for a population claim.

The empirical order matters. A black-box LLM forecaster first has to be
tested on rows that are valid for its generation. Only then does it make
sense to ask which emitted channel improves scoring for a particular
family and source: point estimate, worry scalar, bid-ask spread,
self-predicted Brier interval, reference-class base rate, or cross-family
disagreement.
Only after those two questions can we ask whether a prompt, abstention
rule, review rule, or allocation rule improves Brier or utility
against explicit controls.

The paper therefore has one main argument with two parts. The validity
part is that source currency, label-time, and equal-information checks
change what one is allowed to conclude from LLM forecasting benchmarks.
The applied part is narrower: some model information survives the validity
checks, but it appears through specific interfaces rather than a general
forecasting ability. Very small model probabilities can be tempered on
forward-looking rows that pass the source currency check; pairwise comparisons
can rank harder and easier contracts better than chance when the pairs are
balanced across sources; and one Gemini prompt improves Brier against bare and
placebo prompts in a balanced comparison on public questions. That prompt result
is not treated as a general method because the 591/600-call Claude run remains
underpowered and below gate, and Codex+DeepSeek does not reproduce it. Differences across model families also create measurable
headroom, but the paper treats that headroom as a target for future selection
methods, not as a present decision rule. The practical output is a small set of
controlled uses: a deterministic calibration rule for one row class, a ranking
interface for relative judgment, a Gemini prompt result to replicate, and
negative controls showing where not to spend inference budget.

This framing also explains why the paper is not organized as a single model
leaderboard. The same score can mean different things depending on the row. A
correction for very small probabilities is useful only after source and label checks; a
pairwise comparison can be useful for ranking without being a calibrated
probability; a prompt can improve one family while failing to replicate in
others; and a market comparison is meaningful only when the market price is
frozen at the same information time. The paper's contribution is to keep those
cases separate and score each on the comparison it is actually allowed to
answer.

#### Contributions.

The paper makes five contributions. First, it states a documentation
test for LLM forecasting rows: a row is not broad forecast evidence
unless source currency, label-time validity, and equal-information
comparison status are known. Second, it gives an empirical
source-currency audit in which Manifold rows after the model cutoff are
substantially harder than matched rows before the cutoff or visible in the
model's sources. Third, it reports equal-information market controls that do not
support raw model panel superiority in the current evidence while remaining too
small to estimate market performance in general. Fourth, it separates current
usable results from design evidence. The current usable results are a selected
calibration rule for eligible rows and pairwise ranking balanced by source. The
completed Gemini expert-training prompt is reported as a model-specific
intervention candidate and a replication target, not as a general prompt
method. Additional structured outputs and differences across model families are
design evidence for future interfaces rather than current applied results. These
results are not claims that LLMs are superior to markets or humans. Fifth, it
treats the power-aware re-audit as a methodological result and converts the
missing-evidence map into a companion benchmark design: row
validity fields, equal-information comparators, calibration, relative judgment,
prompt intervention, choosing among model families, open model replication, and
public low-overlap substitute tracks are evaluated separately rather than
collapsed into one leaderboard.

#### Broader measurement route.

The paper also makes the broader measurement route concrete without claiming
prevalence across the field. It does not report a failure rate across the field. The public
ForecastBench audit scores 70 processed-forecast files over 521 resolved
binary row keys and 230 event family keys, finds equal-information market
slices in 68 files, and finds only 6 files beating the prior-day market
baseline before and after event family capping. A second public ForecastBench
audit on the 2024 human-comparator round scores 141 files over 7,259 row keys
and 766 event family keys; the human-super and public aggregate files each
have 577 resolved non-imputed rows, but each has only two strict
equal-information market rows. A Prophet Arena source-access pilot fetches 68
public task rows across four sample releases, including 26 resolved rows, but
the fetched samples contain no submitted forecast probabilities or same time
baseline probabilities; a public repository check over five AI Prophet
repositories finds no committed Prophet Arena submission, leaderboard, or
per-model trace archive. The PredictionMarketBench replay-row pilot
reconstructs 370,254 same-time market-baseline rows but finds no stored model
forecast rows in the released episodes; the PolyBench pilot verifies the
repository/schema surface but cannot score the linked database from the
noninteractive release path. These public audits show how the row validity
machinery extends beyond this study, while leaving prevalence and
conclusion-change rates as future claims.

#### Benchmark design implication.

The companion benchmark implied by the audit has eight separate tracks:
row validity, equal-information comparators, calibration, relative judgment,
intervention, choosing among model families or outside review, open model
replication, and a public low-overlap substitute. The companion benchmark table
gives the track structure. Keeping those tracks separate is part of the claim.
A system can improve a calibrated probability without beating a market, rank
pairs without supplying a reliable absolute probability, or show that model
families make different errors without providing a working selection rule.
During a new study, the same split tells the researcher which claim a packet can
test before outcomes are scored: market comparison, calibration rule,
relative-judgment interface, prompt intervention, selection rule, provider
replication, or low-overlap diagnostic. The benchmark design is therefore
both a way to collect the decisive missing evidence and a guard against turning
one successful track into a broader claim. It is not a current claim about a
measured failure rate across the field.

The row validity track is implemented as a required row schema, expanded in the
broader validity protocol table: source currency, label-time validity,
equal-information comparator timing, effective sample size, and decision-rule
status. That schema is what makes the benchmark useful before scoring rather
than only after a result looks surprising.

Used prospectively, the benchmark becomes an experiment-planning tool. Before
calls are run or outcomes are known, each track asks what would make a positive
result uninformative. If the answer is source visibility, label vintage,
comparator timing, prompt length, family mix, or market overlap, that variable
has to be recorded before scoring. This is the useful form of the inversion in
practice: the question changes the design while there is still time to add the
missing field or control, and a positive result is informative only when the
simpler explanation it invites has already been made measurable.

| Track | Question tested | Primary output |
|---|---|---|
| Row validity core | Does each row state what the model could have known and which label is admissible? | Source-currency, label-time, and event family eligibility labels. |
| Equal-information comparators | Does the model beat a human, crowd, or market measured on the same contract at the same pre-outcome time? | Paired proper-score deltas with event family and source caps. |
| Probability calibration | Does a simple adjustment improve model probabilities on rows that pass the source currency check? | Calibrated-versus-raw Brier deltas by source, family, and cutoff relation. |
| Relative judgment | Are pairwise comparisons a better interface than direct probabilities? | Pairwise accuracy, utility, and predeclared graph-calibrated probabilities when justified. |
| Intervention | Does a prompt or procedure beat bare, placebo, calibrated bare, and matched comparator baselines? | Paired Brier deltas with source and family replication checks. |
| Family selection or review | Can observable features or outside review recover best-family headroom after cost? | Cost-adjusted Brier or utility against simple pools and calibrated baselines. |
| Open-model replication | Which scoped findings survive outside proprietary-provider snapshots? | Replication or bounded failure on public rows with open models. |
| Public low-overlap substitute | Do low-overlap elicitation diagnostics reproduce on a releasable corpus? | Channel and prompt diagnostics after novelty, source, topic, length, and horizon are separated. |

Companion benchmark tracks. The design keeps row validity,
equal-information comparison, calibration, ranking, intervention, family
selection, open model replication, and low-overlap replication as separate
scored tasks rather than a single aggregate leaderboard.

#### Positioning.

The closest related work falls into several groups: future-question benchmarks
such as ForecastBench and Prophet Arena , system papers such as AIA
Forecaster , belief-updating benchmarks such as EVOLVECAST , numerical
forecast-interval benchmarks such as QuantSightBench , automated
question-generation and resolution work, confidence-elicitation and
fictional-market framing work, and market or replay environments such as
Prediction Arena, PolyBench, PredictionMarketBench, Foresight Arena, MarketBench,
and Reppo-style market infrastructure . These systems evaluate
broader capabilities: generating forecasts, updating after new information,
expressing calibrated intervals over continuous quantities, generating and
resolving questions, eliciting confidence or wagers, trading with real or
replayed market frictions, or coordinating through market-like
designs. Their scores can mix probability accuracy with retrieval
timing, execution quality, liquidity, fees, position sizing, interval width,
confidence reporting, automated resolution quality, and the moment at which a
human or market comparison was sampled. Nearby work also studies market
relationships and relative judgment: Semantic Trading uses agentic AI to cluster
prediction markets and identify correlated or anti-correlated market pairs,
while a fully prospective venture tournament finds strong model rankings from
pairwise comparisons against human managers and investors . These results are
closest to this paper's pairwise-ranking result, while our main contribution
remains different. This paper studies the narrower evidentiary unit underneath
those comparisons. Before a system-level score is interpreted as
forecasting evidence, each row has to state what the model could have
known, which label vintage is admissible, and whether the comparator was
measured under the same information rule. The paper is therefore closest
in spirit to recent evaluation-warning work on temporal leakage and
benchmark extrapolation , but adds a scored empirical audit and
controlled tests for using model output after the validity checks.

#### Evidence discipline.

Table <a href="#tab:claim-map" data-reference-type="ref"
data-reference="tab:claim-map">1</a> states the paper’s main claims and
their limits. It is included near the front because the main risk in
this area is not a missing benchmark but a wrong comparison: rows that
are source-visible, labels that use a later data vintage, market bars
measured at a different information time, or decision rules adopted
from diagnostic correlations. Read in the opposite direction, the test is
simple: if the answer, label, or comparator comes from a different
information state than the forecast, the row may still be useful for
diagnosis, but it cannot support a broad forecasting comparison.

<div id="tab:claim-map">

| Claim unit | Evidence in this paper | Conservative interpretation |
|:---|:---|:---|
| Validity checks | Source-currency, label-time, and equal-information audits over the database | A row without these checks is not broad forecast evidence. |
| Raw LLM panels vs markets | Three strict equal-information controls: Polymarket and the 32-contract Manifold expansion have much lower market Brier under raw paired tests and BH correction, with BY `q=0.0616`; the 24-contract Manifold fill is inconclusive. | Does not support raw model panel superiority in the current evidence; too small for a general market-performance estimate. |
| Calibration for very small probabilities | Rule for very small probabilities improves every family on the public-domain panel and improves the forward-looking slice | Point-probability use for rows that pass the source currency check, not retrospective correction. |
| Pairwise ranking | Pairwise ranking balanced by source and partial probability-translation evidence | Ranking/tournament support; absolute-probability use needs larger controls. |
| Expert-training prompt | 600-call Gemini public question comparison: expert-training improves paired Brier versus bare, length-matched placebo, and same row calibrated bare forecasts; two other structured prompt variants do not beat placebo | A Gemini-specific result and replication target; current market overlap has lower market Brier, the 591/600-call Claude run remains underpowered and below the replication gate, and a 448-call Codex+DeepSeek staged run does not clear the bare, placebo, sign-test, or source-split checks. |
| Evidence fields and family choice | Mixed structured-field tests; best-family-in-hindsight headroom not recovered by simple allocation rules | Headroom is a design target, not a predictive asset until an observable selector recovers it prospectively. |
| Generic prompt intervention | Selective action, self-revision, and diagnostic allocation mostly fail controls | Evidence against unvalidated prompt-only interventions. |

Main claims and limits. The central contribution is the validity layer
plus the controlled tests for using LLM forecast information once
invalid comparisons are removed.

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
<td style="text-align: left;">Equal-information baseline</td>
<td style="text-align: left;">What did a market or human comparator know
at the same pre-outcome time?</td>
<td style="text-align: left;">Decides whether raw model probabilities
add value under the same information rule.</td>
</tr>
<tr>
<td style="text-align: left;">Controlled use</td>
<td style="text-align: left;">Which model-derived output improves a
proper score or ranking task after the checks above?</td>
<td style="text-align: left;">Admits only calibration on rows that pass the source currency check,
pairwise ranking, or future differences across model families rules that beat controls.</td>
</tr>
</tbody>
</table>
<figcaption>Evidence flow. The paper’s unit is a forecast row with
documented validity checks, an equal-information baseline, and a
controlled test of which model-derived output improves scoring or
ranking.</figcaption>
</figure>

The paper is empirical first and theoretical second. We ran a
calibration study across five model families and two corpus classes,
with more than 30 measured findings and pre-registered tests. The main
text keeps the forecasting argument in front: validity checks,
equal-information baselines, and controlled uses of model output.
Bias-transfer and prompt-stability results are treated as secondary
diagnostics because they help explain why generic prompting is
unreliable, but they do not carry the paper’s main claim.

#### Statistical audit.

Every reported test is checked with the same power-aware procedure:
Fisher-$`z`$ sample-size computation before an experiment runs, three
possible outcomes after scoring (supported, ruled out at the target effect size,
or underpowered), equivalence testing instead of treating “$`p > 0.05`$” as
evidence of no effect, and leave-one-out $`R^2`$ at small $`N`$. The manuscript
reports one global BH-FDR correction over all p-values used for its main
statistical comparisons and a Benjamini-Yekutieli column as a conservative
robustness check for arbitrary dependence across overlapping panels. Table 2
gives the effective denominator, raw p-value, BH $`q`$, and BY $`q`$ for each
test. For the Polymarket and 32-contract Manifold market rows, BH gives
`q=0.0163` while BY gives `q=0.0616`; we therefore treat those rows as current
controls and BY sensitivity evidence, not as arbitrary-dependence-significant
market effects at `0.05`. The class column separates diagnostic, exploratory, replication, and
continuation rows; none of the exploratory or sensitivity rows is promoted
solely by a multiplicity-adjusted threshold. Under the broader audit, $`8`$ of
$`12`$ prior nulls in the study became underpowered rather than negative
findings, and $`5`$ cross-corpus claims narrowed to corpus-specific results.
That procedure is a methodological contribution because the same overcalling
problem plausibly affects existing $`N{=}5`$–$`20`$ cross-corpus headlines. A
second-order application is corpus-validity drift: a benchmark whose resolution
dates were post-cutoff for publication-era LLMs can become pre-cutoff for the
next model generation. We apply this point to the Halawi 2024 dataset in
$`\S`$<a href="#sec:reaudit" data-reference-type="ref"
data-reference="sec:reaudit">10</a>.

<div id="tab:multiplicity-audit">

| Test | Class | Unit | Effective N | Effect | p | BH q | BY q |
|:---|:---|:---|---:|:---|---:|---:|---:|
| Manifold source-currency audit | Diagnostic | Contract / paired stratum | 80 / 15 | Post-minus-pre Brier `+0.191`; paired delta `+0.216` | 0.0004 | 0.0031 | 0.0115 |
| Polymarket market control | Diagnostic | Contract | 24 | Panel-minus-market `+0.195` | 0.0068 | 0.0163 | 0.0616 |
| Manifold market control | Diagnostic | Contract | 24 | Panel-minus-market `+0.0377` | 0.5431 | 0.6207 | 1.0000 |
| Manifold same-day freeze | Diagnostic | Contract | 32 | Panel-minus-market `+0.0787` | 0.0048 | 0.0163 | 0.0616 |
| Manifold one-day freeze | Sensitivity | Contract | 18 | Panel-minus-market `+0.1026` | 0.0122 | 0.0244 | 0.0921 |
| Manifold two-day freeze | Sensitivity | Contract | 10 | Panel-minus-market `+0.1225` | 0.0152 | 0.0281 | 0.1060 |
| Manifold seven-day freeze | Sensitivity | Contract | 7 | Panel-minus-market `+0.0346` | 0.5045 | 0.6054 | 1.0000 |
| Very-small-probability rule vs raw panel | Exploratory | Contract panel | 132 | Raw-minus-tempered Brier `+0.0296` | 0.0062 | 0.0163 | 0.0616 |
| Very-small-probability rule, forward-looking rows | Diagnostic | Calls / contracts | 120 / 40 | Tempered-minus-raw Brier `-0.0253` | 0.0688 | 0.1032 | 0.3897 |
| Very-small-probability rule, source-visible rows | Diagnostic | Calls / contracts | 120 / 40 | Tempered-minus-raw Brier `+0.0350` | 0.0002 | 0.0024 | 0.0091 |
| Pairwise ranking vs random | Exploratory | Unique non-tie pair | 24 | Accuracy `0.750`; utility `+0.583` | 0.0044 | 0.0163 | 0.0616 |
| Pairwise ranking vs source control | Exploratory | Unique non-tie pair | 24 | Utility `+1.583` | 0.0002 | 0.0024 | 0.0091 |
| Pairwise probabilities vs raw panel | Continuation | Contract | 24 | Candidate-minus-baseline Brier `-0.0061` | 0.7351 | 0.7436 | 1.0000 |
| Pairwise probabilities vs low-probability rule | Continuation | Contract | 24 | Candidate-minus-baseline Brier `-0.0158` | 0.3229 | 0.4559 | 1.0000 |
| Pairwise probabilities vs market | Continuation | Contract | 24 | Candidate-minus-market Brier `-0.0130` | 0.5783 | 0.6309 | 1.0000 |
| Gemini expert-training vs bare | Exploratory | Contract-condition block | 120 | Expert-minus-bare Brier `-0.0606` | 0.0005 | 0.0031 | 0.0115 |
| Gemini expert-training vs placebo | Exploratory | Contract-condition block | 120 | Expert-minus-placebo Brier `-0.0243` | 0.0067 | 0.0163 | 0.0616 |
| Gemini expert-training vs tempered bare | Exploratory | Contract-condition block | 120 | Expert-minus-tempered-bare Brier `-0.0525` | 0.0022 | 0.0103 | 0.0390 |
| Gemini expert-training vs all matched markets | Diagnostic | Contract with market | 51 | Expert-minus-market Brier `+0.1510` | 0.0110 | 0.0239 | 0.0904 |
| Gemini expert-training vs equal-information markets | Diagnostic | Contract with market | 33 | Expert-minus-market Brier `+0.0931` | 0.0351 | 0.0601 | 0.2271 |
| Claude replication vs bare | Replication | Paired block | 115 | Expert-minus-bare Brier `-0.0036` | 0.7436 | 0.7436 | 1.0000 |
| Claude replication vs placebo | Replication | Paired block | 112 | Expert-minus-placebo Brier `-0.0042` | 0.0530 | 0.0848 | 0.3202 |
| Codex+DeepSeek replication vs bare | Replication | Paired block | 90 | Expert-minus-bare Brier `+0.0072` | 0.4704 | 0.5942 | 1.0000 |
| Codex+DeepSeek replication vs placebo | Replication | Paired block | 90 | Expert-minus-placebo Brier `+0.0652` | 0.3891 | 0.5187 | 1.0000 |

Consolidated multiplicity and effective-denominator audit. Lower Brier is
better. Positive panel-minus-market or expert-minus-market values mean the model
or prompt is worse than the market. BH values use one global
Benjamini-Hochberg family over the 24 p-values reported here; BY values apply
Benjamini-Yekutieli as an arbitrary-dependence robustness check. The generated
audit is in `projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/multiple_testing_effective_n_2026_06_20/`.

</div>

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
allocation consequences, including the calibration for very small probabilities and
pairwise-ranking results. Section
$`\S`$<a href="#sec:controlled-use" data-reference-type="ref"
data-reference="sec:controlled-use">8</a> synthesizes the controlled-use
result under the same source, label-time, and market-baseline constraints.
Section
$`\S`$<a href="#sec:bias-transfer" data-reference-type="ref"
data-reference="sec:bias-transfer">9</a> gives the secondary
bias-transfer and prompt-stability diagnostics. The main measurement
audit is collected in
$`\S`$<a href="#sec:reaudit" data-reference-type="ref"
data-reference="sec:reaudit">10</a>: corpus-validity drift,
source currency checks, label-time checks, market-prior repair, and
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
not required for the paper’s central source currency, label-time,
equal-information, market control, or calibration claims on rows that pass the source currency check.
Those claims are scored from the public database, market-history
files, official-data label-time checks, and audit scripts listed in
$`\S\ref{sec:repro}`$. Low-overlap rows are retained as secondary
diagnostics about elicitation channels, prompt stability, and external
generality.

## Forecast row validity and the comparison estimand

The paper’s comparison unit is a scored forecast row, not a model call by
itself. A row contains a question or contract, a model family, a forecast
timestamp, the model’s cutoff or retrieval window, a probability, an
outcome label with data vintage or settlement rule, source metadata, and
any human or market comparator with its own timestamp. A broad
model-vs-comparator claim is estimated only on rows for which the validity
indicator $`V_{\mathrm{row}}`$ is one: the resolved answer was not
source-visible to the model at generation time; the outcome label is
admissible under the relevant data vintage or settlement rule; and the
comparator probability, if used, was measured on the same contract under
the same pre-outcome information rule. Rows with $`V_{\mathrm{row}}=0`$
are still useful for diagnosing retrieval, source familiarity, label
revision, or market-timing effects, but they are not in the denominator
for broad claims that an LLM, human, crowd, or market is the better
forecaster. This is the estimand behind the tables below: differences in
Brier score are interpreted only after the row’s information state is
fixed.

The same rule is applied before a new packet is scored. For each planned
result, we write the plain counter-explanation that would make a positive
result uninformative: a comparator observed at the wrong time, an answer
visible in the source, a later label vintage, a prompt-length or placebo
effect, an imbalanced pair orientation, or a source mix that makes the
denominator misleading. The experiment then has to include the row field
or control that could rule out that explanation. The rule is meant to
change the test while it is still being planned, not to explain a result
after the score is known. If it cannot be satisfied, the result may still
be useful for diagnosis or design, but it is not counted as a broad
performance claim.

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

| Result | Status and denominator | Evidence | Paper use |
|:---|:---|:---|:---|
| Source-currency validity matters | Diagnostic; 80 contracts / 15 paired strata. | Matched Manifold panel: 80 contracts / 240 tool-free calls; post-minus-pre Brier $`+0.191098`$, paired-stratum delta $`+0.2155`$, $`p=0.0004`$, BH $`q=0.0031`$, BY $`q=0.0115`$. | Manifold measurement result; source-general prevalence remains unmeasured. |
| Current market controls do not support raw panel superiority | Diagnostic controls; 24 Polymarket contracts, 24 Manifold contracts, and one 32-contract Manifold expansion. Smaller horizon fills are sensitivity rows only. | Polymarket: panel $`0.267758`$ vs market $`0.072964`$, $`p=0.0068`$, BH $`q=0.0163`$, BY $`q=0.0616`$. Manifold fill: market Brier lower but paired test inconclusive ($`p=0.5431`$). Manifold same-day expansion: panel $`0.214665`$ vs market $`0.135951`$, $`p=0.0048`$, BH $`q=0.0163`$, BY $`q=0.0616`$. | Boundary: current controls do not support claims that LLMs are superior to markets or humans. |
| Calibration for very small probabilities improves point probabilities under scope | Exploratory selected rule; 132 contract panels. | Raw mean-panel remains $`+0.029598`$ Brier worse than the correction for very small probabilities on rows with adequate source and label-time documentation ($`p=0.0062`$, BH $`q=0.0163`$, BY $`q=0.0616`$), but the rule regresses source-visible rows. | Selected calibration rule for rows that pass the source currency check, not a universal correction. |
| Pairwise ranking gives controlled relative-judgment evidence | Exploratory; 24 unique non-tie pairs. | Source-balanced pairwise comparison: accuracy $`0.750`$, utility $`+0.583`$, $`p=0.0044`$ vs random, BH $`q=0.0163`$, BY $`q=0.0616`$; source-control comparison has BY $`q=0.0091`$. | Ranking/tournament support, not standalone probability. |
| Expert-training prompt passes a narrow public question test | Exploratory Gemini result; 120 contract-condition blocks; replications are continuation rows. | Completed 600-call Gemini comparison: expert-training improves paired Brier versus bare prompt (BH $`q=0.0031`$, BY $`q=0.0115`$), length-matched placebo (BH $`q=0.0163`$, BY $`q=0.0616`$), and the calibrated bare forecast; audit-informed and failure-mode-specific prompts do not beat placebo. | Gemini-specific candidate; current market overlap has lower market Brier, the 591/600-call Claude run remains underpowered and below the replication gate, and Codex+DeepSeek does not reproduce the effect. |
| Generic prompt intervention mostly fails | Negative guidance; denominators vary by packet. | Selective action, generic self-revision, and diagnostic allocation fail or regress against controls. | Generic prompting is not enough. |

Core empirical results. The diagnostic sections explain how these
results were found and where they fail; this table states the claims
that remain after source, label-time, and market-baseline controls.

</div>

This ordering is deliberate. The paper’s positive claims are downstream
of the equal-information market controls. A controlled-use result is
included only when it either improves a proper score on valid rows,
improves a balanced bare/placebo prompt comparison, supports a controlled
ranking use, or identifies structure that a future decision rule could try to
recover. Mechanisms that only change
rationales, increase stated effort, or improve a source-visible
retrospective slice are reported as diagnostics or failed interventions.

![Equal-information market controls](evidence/figures/equal_information_market_controls.png)

Equal-information market controls. Lower Brier is better. The plot is
generated from the stored Polymarket replacement and Manifold history
score reports by `evidence/reproducers/make_equal_information_figure.py`. Polymarket
has much lower market Brier than the model panel; in the first Manifold fill the
market has lower Brier, but the paired test is inconclusive. These controls
do not support a raw model panel superiority reading for the current evidence,
but do not estimate a general market control effect.

# Why emitted forecast channels differ by family

Before reporting the elicitation findings, we name the structural
distinctions that organized the measurements. These were not stated in
advance; they are a compact reading of the body of findings the study
produced. Their role in this paper is explanatory: they help explain why
side channels and prompt interventions are family- and
source-conditional, not evidence that LLMs beat markets.

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
mechanistic-interpretability claims. The measurable object is the forecast row
and its scored side fields, not the generated rationale by itself. Recent
latent-prediction theory shows that learning or
predicting hidden representations can avoid the sample-complexity cost
of token-level prediction on hierarchical data . Our setting is not
training-time latent prediction, but the comparison clarifies the
measurement problem: uncertainty channels and source-bound evidence
fields can be scored against outcomes, while free-form rationale text is
a noisy surface output. In two small follow-up tests across two
families, structured
evidence fields beat free prose on mean Brier, while the stricter
two-step variant did not consistently beat a same-turn field. The
combined means were baseline $`0.171038`$, free prose $`0.146103`$,
two-step field $`0.103278`$, and same-turn field $`0.098425`$. A later
placebo-control test weakened the claim: among the 30 rows with complete structured outputs,
baseline mean Brier was $`0.078000`$, two-call prose $`0.107254`$,
same-turn field $`0.110300`$, free prose $`0.122767`$, and two-step
field $`0.149921`$; ten additional Codex rows failed at runtime before
emitting forecasts. The current data justify a larger paired study of
structured evidence fields, but not their use as a scoring rule.

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

#### Scoring discipline across diagnostics.

A power-aware scoring discipline (Fisher-$`z`$ power calculation before
launch, three possible outcomes after scoring, equivalence testing,
global BH-FDR with BY robustness where many reported tests are compared, and
LOO-$`R^2`$ at small $`N`$) is used for every diagnostic above. The
discipline produced the study’s most consequential
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
self-assessments about which channel the model expected to predict error.
The pattern is consistent across these probes: LLMs emit useful side information
about contracts, families, and sources, but the side information is
conditional. It changes sign by family, weakens under task-difficulty
controls, and often fails when moved from a low-overlap corpus to
public-domain market questions.

<div id="tab:elicitation-diagnostics">

| Diagnostic | Main evidence | Manuscript role |
|:---|:---|:---|
| Worry scalar | Pool-level worry is a positive tail-risk signal at $`N{=}590`$, but per-family worry-Brier signs split. Claude and GPT-5.5 can be most worried when most right, while GPT-5.4-mini is direction-sensible. Topic-trigger and mean-regression probes explain the sign flip better than rationale length, wallclock time, or hedging vocabulary. | Use worry as a behavioral channel only after conditioning on family, corpus, and source. It is not a universal calibration transform. |
| Cognitive text versus calibration | Failure-mode words in rationales are weakly positive for the original trio but near zero for Gemini and DeepSeek at roughly $`N{=}60`$ per family. Stake framing raises worry for every family while leaving point probabilities nearly unchanged. | The model can produce diagnostic language without recomputing the forecast from that language. This supports interface discipline, not free-form chain-of-thought reliance. |
| Bid-ask and frequency probes | Bid-ask spread is positive on the low-overlap corpus for GPT-5.4-mini and DeepSeek, but public-domain replication is underpowered or sign-flipped. Frequency framing improves GPT-5.4-mini on low-overlap questions and does not transfer to the public question. | These are promising elicitation probes. They do not justify use across sources. |
| Orthogonality and multi-channel fits | Worry, spread, and trajectory variance are nearly uncorrelated at expression level. Early same-forecast $`R^2`$ survives leave-one-out only for GPT-5.5 on the $`N{=}42`$ public question; the larger five-family audit gives negative leave-one-out $`R^2`$ for channel-only Brier prediction across all five families. | Channels are distinct measurements, but distinct does not mean ready for use. They are useful for diagnosis and design of later scoring rules. |
| Conditional structure and family allocation | Sub-source decomposition flips channel signs across yfinance, Manifold, and Polymarket cells. Pooled channel value collapses after task-difficulty controls. Easy-contract cells show headroom, hard cells overfit, and naive mean/median panels do not beat the best single family. | Model information appears in family-by-source-by-contract interactions. Current observable allocation rules find headroom but do not yet recover it under controls. |

Uncertainty-channel experiments as diagnostics. The shared lesson is
conditionality: emitted channels can locate signal, but they have not
become probability rules across sources.

</div>

The channel material has a narrow role in the argument. The diagnostics
support one claim needed for controlled use: raw LLM forecasts
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
These failures motivate the paper’s emphasis on rows that pass the source currency check
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
for one family. This is a novel diagnostic channel; applied use requires
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
$`+0.51`$, codex-5.5 $`+0.53`$, deepseek $`+0.65`$). A testable
inversion pattern is: when these three families claim “worry is my best
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
evidence grades: robust enough for a calibration on rows that pass the source currency check view,
useful as a design clue, and unsupported as an applied rule.

<div id="tab:applied-patterns">

| Pattern | Evidence | Status |
|:---|:---|:---|
| Overconfidence on very small probabilities | In the lowest forecast quintile, every family underpredicts YES outcomes; gaps range from $`+0.34`$ to $`+0.72`$. | Basis for the rule for very small probabilities, subject to source currency checks. |
| Horizon and source difficulty | Longer horizons have higher Brier ($`\rho=+0.161`$, 95% CI $`[+0.026,+0.290]`$); Polymarket is harder than Manifold, which is harder than yfinance for every family. | Design clue; not enough alone for an applied rule. |
| YES underprediction | On contracts resolving YES ($`N=26/42`$), every family’s mean $`p_{\text{success}}`$ is below $`0.5`$. | Supports calibration diagnostics. |
| Panel agreement and naive ensembles | Cross-family forecast correlations are high (mean $`\rho=+0.72`$); mean/median-of-five have higher Brier than the best single family on the $`N=142`$ paired set. | Warns against naive averaging. |

Cross-family regularities that motivated calibration and allocation
tests. They are useful only when converted into a scored rule and
compared with simple baselines.

</div>

The composed four-rule recipe converted these patterns into a scored
forecast by applying a discount for very small probabilities, a middle-band YES
correction, a horizon shrinkage, and a source-difficulty shrinkage to
the mean panel forecast. The recipe beats naive aggregation on the same
$`N=142`$ paired set, but it does not clear the stronger best-single and
evaluation bars balanced by source.

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
observed effect. Third, later audits balanced by source weaken the
composite. The current source+$`\sigma`$ allocation rule and
diagnostic-triggered allocation have higher Brier than simpler rules;
Hedge over raw-family, calibrated-family, and simple-pool
experts is directionally better but nonsignificant ($`0.226481`$ versus
$`0.233529`$, $`p=0.4671`$) and regresses on Manifold in the balanced
slice. Choosing the best family in hindsight remains far better
($`0.117454`$ Brier), so there is headroom across model families, but the
observable rules have not recovered it.

The pairwise ranking experiment supports a controlled relative-judgment use.
A four-family contrastive comparison supports pairwise
ranking over 24 unique non-tie pairs (accuracy $`0.750`$, utility
$`+0.583`$, $`p=0.0044`$ versus random). Translation tests are favorable
but not yet ready as a probability layer: translated probabilities beat the
calibrated baseline by $`-0.022714`$ Brier within the experiment, with
$`p=0.0628`$; one
cross-experiment direction clears $`p=0.0314`$, the reverse direction misses
at $`p=0.0636`$; and the joined market control slice is only 24 rows
with translated-vs-market $`p=0.5783`$. A prospective Polymarket comparison
has frozen 24 pairwise market bars before model calls, but unresolved
outcomes cannot support a current scoring claim. Pairwise ranking
therefore appears in the paper as a controlled use, while the current
probability rule remains the calibration rule for very small probabilities.

**The correction for very small probabilities as a standalone rule beats raw on every
family at $`p<0.05`$.** The rule applies only when the panel forecast is
below $`0.20`$, shrinking that low forecast toward $`0.10`$ by
$`\hat p_{\mathrm{low}} = 0.35\bar p + 0.65(0.10)`$. The simpler form of
the recipe, the single discount for very small probabilities applied per-family
without the other three rules, improves per-family Brier on every panel
member at $`p < 0.05`$:

| family | raw Brier | discounted Brier | $`\Delta`$ | paired $`p_{\mathrm{perm}}`$ |
|:---|:--:|:--:|:--:|:--:|
| claude | $`0.2543`$ | $`\mathbf{0.2240}`$ | $`-0.0302`$ | $`0.016`$ |
| codex-$`5.5`$ | $`0.2625`$ | $`0.2416`$ | $`-0.0208`$ | $`0.030`$ |
| codex-$`5.4`$-mini | $`0.2714`$ | $`0.2450`$ | $`-0.0264`$ | $`0.015`$ |
| deepseek | $`0.3222`$ | $`\mathbf{0.2704}`$ | $`\mathbf{-0.0518}`$ | $`\mathbf{0.0008}`$ |
| gemini | $`0.3167`$ | $`0.2840`$ | $`-0.0327`$ | $`0.008`$ |

Per-family correction for very small probabilities. The single rule
improves Brier for each tested family on the public-domain panel, but later
source currency checks restrict its use to eligible forward-looking rows.

Discounted Claude at Brier $`0.2240`$ is at parity or better than the
four-rule adjusted aggregate ($`0.232`$), so the additional features add
little on this corpus. The single adjustment for very small probabilities improves Brier
at $`p<0.05`$ across every model family, including DeepSeek and Gemini,
which were not the panel that originated the rule. A
fitted-calibrator audit using the stored rows did not identify a better
replacement: source-isotonic slightly improved the overall point
estimate but lost Manifold and was nonsignificant, while tail-beta
shrinkage was worse. The 2026-06-04 source-documented rerun excludes 10
yfinance/yfinance\_etf complete panels lacking label-time documentation,
leaving 132 panels; source-isotonic remains unsupported at
$`-0.005248`$ Brier versus the correction for very small probabilities with paired
$`p=0.7099`$, while raw mean-panel is $`+0.029598`$ worse. A later
source currency stress audit narrows the rule: it improves post-cutoff
rows ($`-0.025326`$, tail-only $`-0.101306`$) and regresses
pre-cutoff/source-visible rows ($`+0.035016`$, $`p=0.0002`$; tail-only
$`+0.097719`$, $`p=0.0002`$). A row-level rerun through the shared
source currency discriminator leaves those scores unchanged while
exposing 39/240 stored-flag-vs-computed-relation conflicts. The
rule for very small probabilities is therefore forward-looking calibration tied to
computed cutoff and label-time documentation, not retrospective
benchmark correction.
# Controlled use under source and market constraints

Equal-information market controls set the scoring problem. Once the row, label,
and comparator information state are fixed, the question becomes whether a
named model-derived output improves a scored task under the same controls.
Three current uses pass that bar within the paper's scope: the correction for very small probabilities
improves forward-looking rows that pass the source currency check and fails on source-visible rows;
pairwise comparisons rank contracts better than chance but are not yet a
probability model; and one Gemini expert-training prompt beats bare and
placebo prompts in a balanced public question comparison. A fourth line, family
choice, has measurable headroom but no reliable selection rule. These results
belong in the same paper because each depends on the same row validity checks
that make the market controls interpretable.

The controlled-use map separates current uses from design evidence and
negative guidance. The table states what can be used now, what only motivates
the next experiment, and what current controls leave unsupported.

| Output or signal | Current role | Boundary |
|:---|:---|:---|
| Calibration for very small probabilities | Deterministic post-processing rule for rows that pass the source currency check, forward-looking rows with very low panel probabilities. | Regresses on source-visible rows; not a retrospective benchmark correction. |
| Pairwise ranking | Ranking or tournament interface when the task is relative difficulty or relative likelihood. | Probability translation and market-additive use still need larger and prospective controls. |
| Expert-training prompt | One Gemini public question intervention that beats bare, placebo, and same row calibrated bare forecasts. | Does not beat the market on current overlap; the 591/600-call Claude run remains underpowered and below gate, and Codex+DeepSeek does not reproduce it. |
| Structured fields | Candidate interface for forcing comparable evidence fields instead of relying on rationale prose. | Mixed small tests; design evidence only until a larger placebo-controlled packet clears. |
| Differences across model families headroom | Evidence that different families contain conditional signal worth selection or review. | Current cheap selection rules do not recover the hindsight headroom. |
| Negative controls | Evidence that generic reflection, self-revision, and selective action are weak prompt-only interventions. | Does not rule out tool-using, retrieval-grounded, expert-written, or heldout-tuned systems. |

Controlled-use map. The paper’s applied contribution is a bounded account of
which model signals are usable now, which remain design evidence, and where the
present evidence says to stop.

**A scored-use procedure.** The current evidence supports a simple order
of operations for any new forecast packet. First, attach forecast time,
model cutoff, source, label vintage, event family key, and comparator
timestamp to each row; rows that fail source currency or label-time
checks can be studied diagnostically, but are excluded from broad score
comparisons. Second, score any equal-information market or human baseline
before reporting model gains. When that baseline wins, the model result
is reported as diagnostic unless a predeclared calibrated rule or blend
beats it on the same rows. Third, on forward-looking rows that pass the source currency check
apply the correction for very small probabilities only to very low panel
probabilities and report the uncorrected score beside it. Fourth, use
pairwise comparisons for prioritization or ranking; absolute-probability
translation waits for prospective checks against raw, calibrated, and
market baselines. Fifth, treat prompt variants as candidates only when
they beat bare, placebo, calibrated bare, and source-split checks.
This procedure is deliberately narrow, but it turns the market-negative
results into a usable rule for when to score, adjust, rank, or leave
model output alone.

**The rule for very small probabilities is the current selected probability rule.** The
discount for very small probabilities is the best practical rule in the database, but
only under conditions where the source currency check passes. It was selected
after earlier calibration work, so the paper treats it as a scoped rule requiring
independent replication rather than as a general principle. It improves every tested family on
the public-domain panel, including families that were not used to
originate the rule. On source-documented rows the raw mean-panel remains
worse than the correction for very small probabilities by $`+0.029598`$ Brier with
paired $`p=0.0062`$, BH $`q=0.0163`$, and BY $`q=0.0616`$. On the source currency stress panel, the same rule
improves post-cutoff rows by $`-0.025326`$ while regressing
pre-cutoff/source-visible rows by $`+0.035016`$ with $`p=0.0002`$ and
$`q=0.0024`$. This
is the pattern in miniature: the rule helps on the forward-looking slice
and damages retrospective/source-visible rows. It is therefore a
calibration result for rows that pass the source currency check, not a universal correction.

**Pairwise ranking is the current relative-judgment use case.** The
strongest positive ranking evidence supports relative judgment rather
than absolute probability. A same source/minimal-pair comparison balanced by source
comparison gives 24 unique non-tie pairs with accuracy $`0.750`$, utility
$`+0.583`$, $`p=0.0044`$ versus random, and $`p=0.0002`$ versus source
control. Later probability-translation tests are favorable in one
direction, while the required single-contract probability checks remain
unmet: within-experiment translated-vs-calibrated and translated-vs-raw
checks, bidirectional cross-experiment transfer, joined market control, and
prospective causal-order resolution are not all satisfied. The supported
use is pairwise ranking or tournament support.

**Expert-training prompting is a Gemini-specific candidate.**
The completed public question prompt comparison tests five conditions on the
same 120 contracts across FRED, Manifold, and Polymarket: bare prompt,
length-matched placebo, expert-training prompt, audit-informed prompt,
and failure-mode-specific prompt. In the Gemini run, expert-training
improves paired Brier versus bare prompt by `-0.060569` (63 wins, 29
losses, 28 ties; sign `p=0.0005`, BH `q=0.0031`, BY `q=0.0115`) and versus length-matched placebo by
`-0.024287` (60 wins, 33 losses, 27 ties; sign `p=0.0067`, BH `q=0.0163`, BY `q=0.0616`). Mean Brier
improves in all three sources. The two other structured prompt variants
do not beat placebo. A no-new-call external-control audit adds two
boundaries. First, expert-training still beats the same row
calibrated bare prompt by `-0.052503` Brier (64 wins, 33
losses, 23 ties; sign `p=0.0022`, `q=0.0103`). Second, it does not beat markets on
the current overlap: expert-training minus all matched market rows is
`+0.150950` Brier over 51 matched rows (`p=0.0110`, `q=0.0239`), and expert-training minus
equal-information market rows is `+0.093130` over 33 matched rows
(`p=0.0351`, BH `q=0.0601`, BY `q=0.2271`). A
591/600-call Claude run has 112 complete
contract blocks: expert-training is directionally better than the bare prompt
on mean Brier by `-0.003638` (40 wins, 44 losses, 31 ties; sign p=`0.7436`,
`q=0.7436`)
and directionally better than length-matched placebo by `-0.004175` Brier
(53 wins, 34 losses, 25 ties; sign p=`0.0530`, `q=0.0848`). It does not pass either sign
test or the source split: Manifold is directionally favorable, while
FRED regresses versus bare and Polymarket regresses versus placebo. The
audit-informed Claude arm has favorable mean deltas against bare and placebo
(`-0.006726` and `-0.005266`), but neither sign test is significant and the source split remains
fragile. A staged Codex+DeepSeek
check now has 448 scored calls (89 complete five-condition family-contract blocks;
90 expert-training paired blocks: 41 Codex and 49 DeepSeek). Across both
families, expert-training is worse than bare prompt on mean Brier by `+0.007173`,
does not pass the sign test (`p=0.4704`, `q=0.5942`), is worse than placebo by `+0.065223`
(`p=0.3891`, `q=0.5187`),
and fails the source split because only FRED is directionally better than placebo.
Codex remains directionally favorable on mean Brier in the current slice but is
not clean across sources; DeepSeek regresses. This
leaves the completed Gemini finding as a narrow candidate: one model
family, scored after outcomes were known, weaker than matched market rows, with
the Claude run underpowered and below gate and Codex+DeepSeek not reproducing the effect.

**Structured fields and family choice remain design evidence.** Some small tests favor typed evidence fields over free prose,
but the placebo-control continuation is negative for the stronger
two-step claim. Family choice has real headroom: choosing the best
family in hindsight reaches much lower Brier than current decision
rules, and family-by-contract interaction is substantial. Current
observable selection rules do not recover that headroom: Hedge over raw,
calibrated, and simple-pool experts is directionally
better but not significant, and graph-family weighting is small and
fragile. These results identify where model information appears; they do
not yet supply a reliable rule for choosing among model families.

**Generic prompt intervention is still weak evidence.** Generic reflective
prompting, selective action, and self-revision do not reliably improve
forecasts under controls. The tested generic variants either fail
confirmation, overcorrect, produce no measurable change, or underperform
calibration for very small probabilities. The Gemini expert-training comparison shows that a
prompt can improve Brier under a tighter design, but it does not rescue
the broader claim that asking the model to reason harder, repair itself,
or act selectively is enough to improve forecast probabilities.

These results are analyzed together because the positive findings depend on
the same validity checks that make the market controls interpretable. The
common unit is a forecast row whose information state is documented before any
calibration, ranking, or selection rule is evaluated, not an isolated prompt or
model family.

# Secondary diagnostics: bias transfer and prompt stability

<span id="sec:prompt-invariance" label="sec:prompt-invariance"></span>
<span id="sec:freq-framing-test" label="sec:freq-framing-test"></span>

The bias-transfer and prompt-stability experiments are not the paper’s
central contribution. They appear in the main text as diagnostics for
why naive prompt interventions and family-general allocation do not yet
support decisions.

**Bias transfer.** Three novel-bias tests on the same $`N=30`$
public-domain contracts across five families found a structured split:
loss-frame and probability-weighting probes were close to symmetric or
near-linear, while current-state/status-quo framing moved several
families substantially. A held-out seven-bias slate later supported the
representational distinction between text-discussed motivational cases
and direct utility-like mechanisms. The anti-bias-prompt follow-up
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

These diagnostics bound the controlled-use result: model output does not
become reliable through generic reflection, debiasing, or self-revision.
It can be used only when the interface is tied to a scored channel, a
calibration on rows that pass the source currency check rule, a pairwise ranking task, or a predeclared
allocation rule that beats simpler controls.

# The re-audit discipline: a warning to the field

The discipline that produced the results above also produced a re-audit
of the study’s own prior findings. We treat the re-audit itself as a
contribution because the same overcalling pattern is a plausible risk in
LLM-forecasting studies with small per-source or per-family cells.

## Power calculus applied to our own study

Before applying the power-aware audit, eight prior “no effect” or
“cross-corpus replication” claims in the study had been written down as
findings. Applying the Fisher-$`z`$ audit retrospectively:

- Four “null” findings move from ruled out to underpowered: the data did
  not actively rule out a meaningful effect at the per-family target
  $`|\rho|`$ floor; the apparent lack of effect was mainly a lack of
  power.

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
flawed. The unsupported step was the earlier interpretation.

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
need for resolved, equal-information scoring. The methodological gap this
paper targets is a consistent power-aware audit: every claim labelled
with one of three possible outcomes, $`n_{\mathrm{required}}`$
pre-computed before launch, sub-source heterogeneity reported alongside
the aggregate, and prior verdicts re-audited under the same calculus as
new ones.

Recent work has expanded the comparison set since those papers. The closest
related work now also includes automated question-generation and resolution,
confidence-elicitation, and fictional-market framing work. These are adjacent
to the paper's row validity and side-channel evidence, but still require
resolved rows and equal-information baselines before they become forecasting
evidence. Table <a
href="#tab:lit-positioning" data-reference-type="ref"
data-reference="tab:lit-positioning">6</a> summarizes the recent
benchmark classes and the boundary this paper draws around them.

<div id="tab:lit-positioning">

| Class | Examples | What they measure | Boundary in this paper |
|:---|:---|:---|:---|
| Future-question and system benchmarks | ForecastBench, Prophet Arena, and AIA Forecaster | Forecast generation, expert comparison, and system performance on live or future questions. | The comparison row still needs source currency, label-time, and equal-information documentation. |
| Belief updating | EVOLVECAST | Whether forecasts move appropriately when new post-cutoff information is supplied. | The information state at the original forecast time is part of the row definition, not an afterthought. |
| Numerical forecast intervals | QuantSightBench | Prediction intervals for continuous future quantities, scored by coverage and interval sharpness. | Interval calibration is a different output interface; the present paper studies binary-event rows, equal-information baselines, and controlled use after row validation. |
| Question generation and resolution | Automated forecasting-question generation and resolution | Generation and resolution of forecasting questions for AI evaluation. | Automatic resolution still needs label-time, settlement-rule, and equal-information-comparator metadata before row scores support model-vs-comparator claims. |
| Confidence elicitation and fictional markets | Confidence elicitation and fictional prediction-market framing | Whether models can emit useful confidence or wager-like signals about answer correctness. | A confidence or stake signal becomes forecasting evidence only after it is joined to resolved rows and equal-information baselines. |
| Trading and replay benchmarks | Prediction Arena, PolyBench, and PredictionMarketBench | Profit, loss, execution, fees, liquidity, timing, and position sizing. | Trading profit is not the same object as same-contract Brier under equal information. |
| Market-style evaluation and coordination | Foresight Arena, MarketBench, and Reppo | Market-style scoring, coordination, or infrastructure for AI forecasting and training data. | The market comparison still needs a dated baseline and enough resolved rows to distinguish small edges. |
| Market relationship discovery | Semantic Trading | Agentic discovery of correlated, anti-correlated, and otherwise linked prediction-market pairs. | Market-pair structure can motivate relative judgment, but probability use still needs resolved outcomes and equal-information controls. |
| Relative judgment | Strategic Foresight venture tournament | Pairwise model rankings against human managers and investors. | Supports pairwise ranking as a credible evaluation format, but not standalone probability translation. |
| Evaluation warnings | Pitfalls and consistency checks | Temporal leakage, extrapolation risk, circular comparisons, and pre-resolution coherence. | This paper adds scored database audits and equal-information market controls. |

Related benchmark classes and the boundary used in this paper. The present
study is not a live-trading or autonomous-system benchmark; it audits the
row-level evidence needed before model, human, and market comparisons
are interpreted as forecasting evidence.

</div>

Read against that literature, the present paper is not a live-market
benchmark or an autonomous-trading evaluation. Its distinct contribution
is the row-level documentation needed to interpret those benchmarks:
before comparing an LLM, a market, and a human, the row must specify what was
source-visible, what label vintage is admissible, and whether the
baseline was measured under equal information. This is also why evidence
that markets score better is scientifically useful. If an LLM has higher
Brier after the information state is equalized, the remaining question
is whether any model-derived outputs remain useful under calibration,
ranking, and family/source constraints.

**What a audit would measure.** The evidence in this paper is
enough to show that row-level validity can change conclusions in this
program. It is not yet enough to claim that the same failure rate holds
across the field. A audit would treat each benchmark row as
the unit of analysis and record the following checks before comparing
model, human, or market scores:

| Audit check | What must be recorded | Why it matters |
|:---|:---|:---|
| Source currency | Forecast timestamp, model cutoff or retrieval window, resolution date, and whether the resolved answer was source-visible at generation time. | Separates future-event prediction from retrieval or source familiarity. |
| Label-time validity | Outcome label, label source, data vintage, and any later revisions or settlement-rule changes. | Prevents scoring against values that were not admissible at resolution time. |
| Equal-information comparator | Human, crowd, market, or agent baseline measured on the same contract at the same pre-outcome information time. | Prevents comparing a model forecast with a comparator that knew more or less. |
| Effective sample size | Event-family identifiers, source strata, repeated sibling markets, and family/model repetition. | Prevents row-rich but event-thin conclusions. |
| Decision rule status | Whether the tested rule was predeclared, tuned on the same rows, or evaluated prospectively. | Separates exploratory diagnostics from supported use. |

Broader validity audit protocol. The present manuscript supplies this
protocol, a scored within-program audit, and the public-audit status
summarized below; a cross-benchmark failure-rate claim requires applying
the protocol to several public benchmark families.

For reproducibility,
`projects/llm_forecasting_calibration_program/tools/field_wide_validity_audit_protocol.py`
emits the row schema and benchmark seed matrix over twelve benchmark or
evaluation families. The source inventory records the current external access
surface: ForecastBench and PredictionMarketBench are high-access
row-level routes, four routes are medium-access, and six still
require a public trace or row-release check before scoring.

| Route | Row-level status | Completed check | Remaining limit |
|:---|:---|:---|:---|
| ForecastBench | Public forecast rows and question rows available. | 500 question rows inspected; 475 have core validity fields; 250 have timestamped same-contract market rows. The 2026 processed-forecast audit scores 70 files over 521 unique resolved binary row keys and 230 event family keys; 68 files have an equal-information market slice. Only 6 files beat the prior-day market baseline before and after event family capping; the median file-level delta is +0.0866 Brier points in both views. A 2024 human-comparator audit scores 141 files over 7,259 row keys and 766 event family keys; the human-super/public aggregate Briers are 0.1186/0.1532. | Official-data rows still need data-vintage documentation; the human aggregate files each have only two strict equal-information market rows, so this is not a broad human/market comparison. |
| PredictionMarketBench | Public replay episodes available. | Four replay episodes contain 33 settled tickers, 378,596 orderbook rows, 297,273 trade rows, and 370,254 reconstructable same-time market-baseline rows. | Released episodes contain no stored LLM forecast rows; model comparisons require submitted agent traces or a new benchmark run. |
| Prophet Arena | Public sample task rows available. | Four public sample releases contain 68 task rows with task ids, source/event tickers, prediction deadlines, context, metadata close times, and 26 resolved rows; five public AI Prophet repositories were checked for trace files. | The fetched samples contain no submitted forecast probabilities, model input timestamps, or same-time market/human baseline probabilities, and no public Prophet Arena submission/leaderboard trace archive was found, so no conclusion-change score is available. |
| PolyBench | Repository and database schema available; released database unavailable in this run. | The source-access check verifies the public repository/schema surface, confirms zero GitHub releases and zero committed database/CSV/parquet row files, and records that the OneDrive link resolves to HTML rather than a direct database file. | A released database or equivalent row export is required before scoring. |
| Halawi 2024 binary-resolved benchmark | Local date summary only. | The local summary records the corpus-validity warning that no 2025-or-later resolutions are present in the stored date distribution. | The raw benchmark rows are not present locally, so this is not a completed external row audit. |

Current public benchmark audit status. These checks strengthen the
measurement-validity route, but they are not evidence of
prevalence.

The public-audit results are deliberately limited. ForecastBench
supports public forecast-score and human-comparator audits,
PredictionMarketBench supports a public replay-row market-baseline audit, and
Prophet Arena supports task-row source-access checks. The ForecastBench human
aggregate files are useful because they are scoreable and public, but their
equal-information market overlap is only two rows per aggregate file. Prophet
Arena and PredictionMarketBench still need submitted forecast traces before
model-vs-baseline conclusions can be recomputed; the public Prophet Arena
repositories checked here expose task rows and evaluation code, not a
submission archive. PolyBench and Halawi currently remain data-access cases.
These files therefore support the
row-level validity argument and specify the missing joins; they do not yet
establish a cross-benchmark failure rate.

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
broader validity protocol.

<div id="tab:reaudit-sources">

| Check | Current evidence | Conclusion |
|:---|:---|:---|
| Manifold source currency panel | 80 matched contracts / 240 tool-free calls; post-minus-pre Brier $`+0.191098`$, paired-stratum delta $`+0.2155`$, permutation $`p=0.0004`$, BH $`q=0.0031`$, BY $`q=0.0115`$. Partial market-prior repair joins 51 contracts and leaves the effect positive under adversarial missing-band sensitivity. | Manifold measurement result: source-visible and post-cutoff rows cannot be pooled without documentation; source-general prevalence remains unmeasured. |
| Manifold pre-outcome market bar | On the 51 repaired contracts, market Brier is $`0.099673`$ versus joined LLM-panel $`0.166963`$ overall; market+LLM blending is unsupported ($`p=0.794`$). These rows are typed as not-equal-information external baselines. | Useful diagnostic comparison, but not a broad human/crowd baseline. |
| Polymarket source check | Gemini and DeepSeek aggregate post-minus-pre directions are positive, but matched source/topic/length strata are null or opposite-sign. The initial seven-day market-price freeze design only fills 4/24 rows; horizon sweep tops out at 12/24. | Diagnostic evidence, not replication across sources or a usable equal-information design. |
| Polymarket replacement equal-information sample | Replacement sampling on 2026-06-15 selects 24 one-per-event rows from 80 eligible candidates at a two-day freeze horizon, 14 NO / 10 YES, all open-by-target with nonempty CLOB history. The four-family panel has higher Brier than the market: panel $`0.267758`$ vs market $`0.072964`$, paired $`p=0.0068`$, BH $`q=0.0163`$, BY $`q=0.0616`$. | Lower market Brier in this slice under the raw paired test and BH correction; BY treats it as sensitivity rather than arbitrary-dependence significance at `0.05`. |
| Manifold equal-information sample | Public API history fill validates 24/24 rows, 15 NO / 9 YES. Selected five-family panel Brier is $`0.198723`$ vs Manifold $`0.160977`$, panel-minus-market $`+0.037746`$, paired $`p=0.5431`$, BH $`q=0.6207`$, BY $`q=1.0000`$. | Second-source comparison; the market Brier is lower, but the paired test is inconclusive. |
| Manifold same-day freeze expansion | Public API history fill validates 32/34 request rows, with two unsupported or unfetched rows excluded, 15 NO / 17 YES. Selected five-family panel Brier is $`0.214665`$ vs Manifold $`0.135951`$, panel-minus-market $`+0.078714`$, paired $`p=0.0048`$, BH $`q=0.0163`$, BY $`q=0.0616`$. | Larger same-contract Manifold check; market Brier is lower under the raw paired test and BH correction, but BY treats it as sensitivity and this is still not a population estimate. |
| Manifold horizon sensitivity | Public API history fills validate 18/18 one-day, 10/10 two-day, and 7/7 seven-day request rows. Selected five-family panel versus Manifold market Brier is $`0.202270`$ vs $`0.099699`$ at one day ($`p=0.0122`$, BH $`q=0.0244`$, BY $`q=0.0921`$), $`0.231846`$ vs $`0.109365`$ at two days ($`p=0.0152`$, BH $`q=0.0281`$, BY $`q=0.1060`$), and $`0.228263`$ vs $`0.193649`$ at seven days ($`p=0.5045`$, BH $`q=0.6054`$, BY $`q=1.0000`$). | Overlapping sensitivity check only; these rows are not used as independent core market-control evidence. |
| FRED official-data check | Fixed one-year FRED series supplies 49 pre-cutoff rows; full paired post-minus-pre delta is only $`+0.016477`$ ($`p=0.30375`$). In the vintage repair, 15 of 98 binary labels changed. Across 192 blinded-control calls, the apparent current-label post-minus-pre penalty collapses from $`+0.024719`$ to $`-0.002989`$ after vintage repair. | Official-data diagnostic; label-time checks are required before current-label positives count. |
| Metaculus target cells | Current authenticated endpoints expose post/question payloads but not resolved binary values plus dated aggregate history for the sampled rows; data-download endpoint is restricted. | Remains a data-access question, not a negative result. |

Re-audit evidence by source. The paper’s broad comparison claims depend on
source currency, label-time validity, and equal-information status, not
merely on model call volume.

</div>

The source currency panel is matched on source, topic, question-length
bucket, and cutoff relation. Reliable base-rate bands are not available
for that panel, so base-rate matching remains a stated limitation rather
than a hidden control. The database now contains 170 external market
baseline rows: 51 not-equal-information Manifold diagnostic rows, 4
equal-information Polymarket rows from the failed seven-day sample, 24
equal-information Polymarket rows from the replacement sample, 24
equal-information Manifold rows from the 2026-06-15 history fill, 32
equal-information Manifold rows from the same-day freeze expansion, and 35
additional Manifold horizon-sensitivity rows at one, two, and seven days before
resolution. The
51-contract Manifold market-prior join is useful as a diagnostic repair,
but not as the paper's market comparison: market mean Brier is
$`0.099673`$, leave-one-out tuned market+LLM blend Brier is
$`0.097218`$, paired delta is $`-0.002455`$ with $`p=0.794`$, and the
post-cutoff subset prefers market-only. Its effective unit is 51
contracts with outcome mix 17 YES / 34 NO, and 32 of 51 market rows have
Brier below $`0.05`$. The baseline availability audit also leaves 29 of
the 80 source currency-panel contracts without a joined market or human comparison.
The three primary equal-information slices are therefore the relevant market
controls for this manuscript, with the smaller horizon fills used only as
sensitivity checks. They do not support raw-panel superiority: Polymarket has much
lower market Brier than the model panel, the first Manifold fill has lower
market Brier but an inconclusive paired test, and the 32-contract Manifold
expansion is again lower-Brier for the market under the raw paired test and BH
correction, with BY sensitivity reported in the multiplicity table. The
one-day, two-day, and seven-day Manifold horizon checks are reported only as
sensitivity rows.

This audit changes what the paper can support. The Manifold
source currency result is strong enough to report as a
measurement-validity contribution. The FRED check gives the clearest
label-time example: scoring the same official-data question against a
current value and against the admissible vintage can reverse the
apparent pre/post difficulty contrast. The equal-information market rows
do not support a broad reading that LLMs are superior to markets or humans while narrowing the
applied result: LLM-derived information has to be tested through
source-specific calibration, pairwise ranking, structured interfaces, or
future allocation rules that beat the market or human bar under the same
information rule.

Because these controls are still small and post-hoc, they are not used as a
high-power filter for every downstream calibration or prompt claim. They are used
to state that the current evidence does not support raw model panel superiority and to define the larger
equal-information acquisition that the benchmark still needs.

## Claim rule after re-audit

The re-audit leaves a simple rule for interpreting applied results. A
per-family or per-source decision rule is treated as supported only when
the scored rows pass the source currency and label-time screens, the
effective denominator is stated at the contract, pair, or event family
level, and the result survives the relevant equal-information, placebo,
source split, or held-out family control. Results that fail one of those
checks remain useful as diagnostics or entries in the continuation
matrix, but they do not become present-tense applied claims. This is why
the manuscript keeps the correction for very small probabilities, pairwise ranking,
and Gemini prompt result under explicit scope while leaving family
selection, structured fields, source currency beyond Manifold, and broader
market/human comparisons as next tests.

# What this paper does not establish

- It does not show that LLMs beat humans, human crowds, or prediction
  markets. The database has 170 external market baseline rows, including
  119 equal-information market rows across Polymarket and Manifold. On
  the completed 24-contract Claude+Codex+Gemini+DeepSeek Polymarket
  replacement slice, the market baseline beats the four-family model
  panel. On the separate 24-contract Manifold fill, the market Brier is lower
  than the selected five-family low-stake model panel, but the
  paired comparison is inconclusive. On the 32-contract Manifold same-day
  freeze expansion, the market Brier is again lower than the selected five-family panel under the raw paired test and BH correction. The
  smaller Manifold one-day, two-day, and seven-day horizon checks are overlapping sensitivity rows, not additional independent market-control evidence.
  Broad superiority would require predeclared or sufficiently powered baselines
  balanced by source under the same pre-outcome information rule.

- It does not estimate a general market control effect from the three
  equal-information slices. The slices are strict but still modest. They do not
  support a raw superiority claim in this dataset, especially on Polymarket and
  the 32-contract Manifold expansion, but they are not enough to
  characterize market and model performance across sources, horizons, liquidity
  regimes, or event families.

- It does not establish translated pairwise probabilities as a
  standalone probability layer. Pairwise ranking survives as
  source heldout evidence with promising translation tests, but
  within-experiment, cross-experiment, market control, and prospective
  causal-order checks remain incomplete.

- It does not establish a source currency beyond Manifold result beyond
  the main Manifold panel. Polymarket tests are aggregate-positive but
  matched-stratum null/opposite-sign, and FRED current-label positives
  weaken under label-time/vintage repair.

- It does not establish a prompt method that generalizes across sources or beats markets. The
  completed Gemini public question comparison supports one expert-training prompt
  against bare, placebo, and same row calibrated bare forecasts,
  but generic reflection, selective action, and self-revision fail or regress
  in other audits. Current matched market rows remain stronger. The 591/600-call
  Claude run remains underpowered and below the replication gate:
  expert-training is directionally better than bare and placebo on mean Brier,
  but does not clear the sign tests and does not pass the source split.
  The audit-informed arm is only directionally favorable and fragile
  across sources. A 448-call
  Codex+DeepSeek staged replication is worse than bare and placebo on mean
  Brier and does not clear the sign-test or source-split checks. The prompt result is therefore a Gemini-specific
  candidate until a second completed family run clears the
  same checks.

- It does not establish external generality or provider-independent generality. The
  low-overlap corpus is private and not publicly available in raw form;
  the low-overlap frequency-framing, bid-ask, worry-sign, and channel
  findings need public replication at proper power. The current
  low-overlap/public split also confounds novelty, source, topic, question
  length, and implicit base rates, so a four-cell de-confounded corpus remains
  the main methodological follow-up. The scored calls use proprietary APIs or
  CLIs; an replication on open models and public questions is required before
  claiming provider-independent generality.

- It does not establish a working rule for choosing among model families. Best-family-in-
  hindsight scores show that different families make different errors, but
  choosing the best family after seeing outcomes is not an intervention.
  Differences across model families headroom becomes useful only if observable features, outside
  review, market disagreement, or held-out model signals recover that headroom
  prospectively after cost.

- It does not decompose LLM reasoning mechanistically or identify the
  causal role of post-training. Channel-orthogonality results are
  expression-level measurements, not white-box interpretability. Family
  identity predicts several bias and channel differences, but the
  comparisons are cross-family and confound post-training with
  pretraining data. Isolating an alignment effect requires within-family
  checkpoints or matched-pretraining families.

#### Effective denominators.

The main results are not counted at the model call level. Repeated model calls
over one contract improve a panel estimate, but they do not create new events;
this prevents model call rows from being treated as independent events.
Table <a href="#tab:effective-denominators" data-reference-type="ref"
data-reference="tab:effective-denominators">7</a> records the denominator used
for the central slices; the support audit also records source counts and
evidence paths.

<div id="tab:effective-denominators">

| Evidence slice | Scored rows | Denominator used | Boundary |
|:---|:---|:---|:---|
| Source-currency panel | 240 calls over 80 contracts | Contract | Manifold-supported measurement result; extension beyond Manifold still needs non-Manifold matched pre/post rows. |
| Equal-information market controls | 24 Polymarket contracts, 24 Manifold contracts, a 32-contract Manifold same-day expansion, and smaller Manifold horizon checks | Contract at a matched market time | Market controls for this manuscript, not a broad market/human result. |
| Prompt comparison | 600 calls over 120 contract-condition blocks | Contract-condition block | Gemini-specific public question result and replication target; current market overlap has lower market Brier; the 591/600-call Claude run remains underpowered and below gate, and Codex+DeepSeek does not replicate it. |
| Pairwise ranking | 94 calls over 24 non-tie pairs | Unique pair | Ranking result only; probability translation and prospective market freeze scoring remain incomplete. |
| FRED label-time repair | 196 calls over 98 series/event rows | FRED series/event row | Label-time diagnostic; vintage repair changes labels but does not create an improvement rule. |
| ForecastBench public score audits | 2026 score audit: 70 forecast files, 521 row keys / 230 event family keys. 2024 human-comparator audit: 141 files, 7,259 row keys / 766 event family keys; human aggregate files have 577 resolved rows each. | Public row key, with event family-capped market check | Public-audit feasibility and human-comparator coverage; human aggregate market overlap is only two rows per file, so this is not a broad human/market comparison. |

Effective denominators for the central evidence slices. The support audit at
`projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.md`
gives the full per-slice source and event-group status.

</div>

#### Next tests.

Table <a href="#tab:next-tests" data-reference-type="ref"
data-reference="tab:next-tests">8</a> states the evidence
required to strengthen each claim. The most direct route to a broader
measurement contribution is an audit of public
forecasting benchmarks and market-replay environments. That route does
not require LLMs to beat markets; it requires showing that row-level
source currency, label-time, or equal-information checks are often
missing and can change conclusions. A broad LLM-vs-market or
LLM-vs-human claim requires a predeclared or substantially larger
equal-information sample that beats the market or human
baseline under the same pre-outcome information rule, not more calls on
the current rows. A source currency beyond Manifold claim requires
Metaculus/export access or another non-Manifold panel with matched
pre/post resolution-date coverage and label-time documentation. Pairwise
ranking becomes a standalone probability layer only if within experiment,
cross-experiment, market control, and prospective causal-order checks all
clear. The prompt result becomes broader only if a structured-prompt arm
replicates in another completed model-family run and beats a larger
same-time market or human overlap.

The immediate unblocking protocol for the `N=24` market control bottleneck has
two admissible paths. The first is strict backfill: mine existing pre-outcome
model calls only when the same contract has an auditable market-history export
at or before the model timestamp or a predeclared freeze timestamp; keep one row
per event family unless a clustered analysis is reported; and reject rows with
unresolved YES-token mapping, final-page odds, or post-outcome price selection.
A 100-row non-Polymarket export pass using the current local database surfaced
only 10 eligible Manifold request rows, so local backfill alone does not solve
the denominator problem. The second path is prospective acquisition: freeze
market prices before model calls, hide the prices from the prompts, persist the
prompt/output packet before resolution, and score only after outcomes settle.
The target for a stronger market control result is `N >= 100` resolved
contracts, balanced by source across at least two market sources, with
event family clustered uncertainty and predeclared comparisons among
market-only, raw panel, calibration on rows that pass the source currency check, pairwise-derived rankings or
probabilities where applicable, and market+model blends.

The immediate experimental roadmap has two jobs. First, turn the current
post-hoc equal-information controls into a predeclared `N >= 100` packet, using
strict backfill where timestamps are auditable and prospective freezes where
they are not. The new Manifold horizon fills show that local acquisition can add
valid rows, but also that the remaining denominator is source- and
event-family-limited. Second, test whether the Gemini expert-training result
generalizes by completing a full second-family packet. The current staged
evidence makes Codex-only completion more informative than more mixed
Codex+DeepSeek aggregation; an open model is the next independent replication
target. A positive prompt result is useful only if it beats bare, placebo,
calibrated bare, and same-time market or human baselines on the same rows and
does not vanish in the source split.

The low-overlap corpus findings become externally general only after a
sanitized release or a public niche-domain replication that breaks the current
novelty/source/topic/length/base-rate confound.
Provider-independent generality requires repeating the public question
validity and controlled-use checks on open models. A separate
evidence matrix records each candidate result, the checks it has passed,
the checks still missing, and the next decisive test. A separate
follow-up priority matrix ranks the follow-up tests by claim impact,
minimum next step, what would strengthen each claim, and what would
rule it out.

<div id="tab:next-tests">

| Claim | Present treatment | Evidence that would change the status | If the evidence is absent or negative |
|:---|:---|:---|:---|
| Benchmark validity beyond this study | Protocol, within-program audit, ForecastBench public score and human-comparator audits, Prophet Arena source-access pilot, PredictionMarketBench row-schema pilot, and PolyBench source-access pilot. | Row-level audit of several public benchmark families, recording source currency, label-time validity, equal-information status, and conclusion changes after repair. | Keep claims about prevalence across the field out of the paper. |
| LLM vs. market/human performance | Not supported; current equal-information slices have lower market Brier or are inconclusive, and the strict controls are still small and partly overlapping. | Predeclared, equal-information sample with at least `N >= 100` resolved rows, event family clustered uncertainty, and market/history timestamps frozen before model scoring. | Keep raw-panel superiority claims out of the paper. |
| Source currency beyond Manifold | Supported on the main Manifold panel; other sources remain diagnostic. | Non-Manifold panel with matched pre/post rows, admissible label vintage, and base-rate documentation. | Treat source currency as a Manifold-supported measurement result plus a general audit requirement. |
| Pairwise ranking as probability layer | Ranking use supported; probability translation remains provisional. | Within experiment and cross-experiment ranking replication plus prospective probability translation against raw, calibrated, and market controls. | Use pairwise comparisons only for ranking or tournament support. |
| Structured prompting intervention | Expert-training improves paired Brier versus bare, length-matched placebo, and calibrated bare forecasts on the same Gemini rows; two other prompt variants do not beat placebo; current market overlap has lower market Brier; the 591/600-call Claude run remains underpowered and below the replication gate, while Codex+DeepSeek does not reproduce it. | Complete a full second-family packet, prioritizing Codex-only completion over more mixed Codex+DeepSeek aggregation; then run an open-model replication; require survival by source and larger market or human overlap measured at the same time. | Treat the current result as a Gemini-specific candidate interface. |
| Structured evidence fields | Hypothesis only. | Larger balanced paired test that beats free prose, same-turn fields, and two-call prose after runtime failures are included. | Treat structured fields as a future paired-test design until that comparison is run. |
| Family allocation | Best-family-in-hindsight headroom exists; current allocation rules do not recover it. | Predeclared observable features, outside review, market disagreement, or held-out model signals that recover best-family headroom after cost. | Report headroom as a design target without claiming a working selector. |
| External generality of low-overlap results | Not yet established. | Sanitized release or public niche-domain replication that breaks the current novelty/source/topic/length/base-rate confound. | Keep low-overlap results as secondary diagnostics. |
| Open model replication | Not yet established. | Repeat the public question source currency, market control, calibration for very small probabilities, and pairwise-ranking checks with open models. | Treat current model-family results as provider-snapshot evidence. |

Claim-status table. The paper separates current claims from the evidence
that would change their status; missing or negative follow-up evidence
leaves the manuscript at its present measurement-validity and
controlled-use scope.

</div>

# Conclusion

The main lesson is practical: scored probabilities do not become
forecasting evidence until the row says what the model could have
known. Each row must specify what was source-visible to the model
generation, whether the label uses an admissible time vintage, and
whether the human or market comparison was measured under the same
information rule. In this study, those checks change the claim:
the Manifold source currency panel supports a measurement-validity
result, while the equal-information Polymarket and Manifold market
comparisons do not support a raw model panel superiority reading of the current
evidence and do not estimate a general effect comparing markets and models.

The applied claim is limited but nontrivial because it identifies where model
information survives strong controls. The current evidence supports
calibration for very small probabilities and pairwise ranking as a
relative-judgment task. It also records one Gemini expert-training prompt
result, structured evidence fields, and headroom across model families as follow-up
targets rather than general deployed methods. Generic reflection,
self-revision, and selective action are not enough. The resulting order of use
is concrete: screen rows before scoring, apply the correction for very small probabilities
only on eligible forward-looking rows, use pairwise comparisons for relative
triage rather than standalone probabilities, treat the expert-training prompt
as a Gemini replication target, and leave generic reflection,
self-revision, selective-action prompts, and model-family selection unsupported
until they clear the same controls.

A broader claim requires new evidence rather than more calls on the
same rows. The decisive tests are a broader row validity audit,
prospective or larger equal-information samples,
non-Manifold source currency panels with label-time documentation, and
predeclared methods that beat raw, calibrated, and market controls
under the same information state. The market control upgrade is especially
concrete: strict backfill is allowed only with auditable pre-outcome market
histories, and the cleaner route is a prospective freeze packet with at least
100 resolved rows, source balance, event family clustering, hidden market
prices, and predeclared scoring. These requirements also define the
companion benchmark design: row validity metadata, equal-information
baselines, calibrated probabilities, relative judgments, prompt
interventions, family selection, open model replication, and public
low-overlap substitutes are scored as separate tracks rather than
collapsed into one aggregate leaderboard. The same design is useful
during research, not only after publication, because it tells a live packet what
comparison it is allowed to answer before the outcome is scored.

# Reproducibility

All model calls persist as JSONL files and are ingested into the SQLite
database at `analytics/public/calibration/forecaster_calibration.db`.
Pre-registrations and verdict resolutions are in the same database. The
reusable general-purpose statistics module is at
`src/ztare/experiment_stats.py` (power calculator, bootstrap CI, paired
permutation, Fisher-$`z`$ Spearman, TOST, BH-FDR, BY robustness, power-aware verdict,
BIC Bayes factor, reproducibility hash). Forecasting-specific wrappers
are in `src/ztare/forecasting/calibration_stats.py`; the public methodology
file lists the exact commands for each finding.

**Reproducing the scope checks.** Three audit scripts define the scope
boundary:

- `projects/llm_forecasting_calibration_program/tools/paper_readiness_exhaustion_audit.py`
- `projects/llm_forecasting_calibration_program/tools/paper_coherence_audit.py`
- `projects/llm_forecasting_calibration_program/tools/independent_equal_information_source_audit.py`

Equal-information acquisition is split into deterministic scripts:

- `projects/llm_forecasting_calibration_program/tools/equal_information_baseline_export_packet.py`

- `projects/llm_forecasting_calibration_program/tools/equal_information_baseline_result_ingest.py`

- `projects/llm_forecasting_calibration_program/tools/equal_information_freeze_feasibility_audit.py`

- `projects/llm_forecasting_calibration_program/tools/equal_information_horizon_sweep.py`

- `projects/llm_forecasting_calibration_program/tools/equal_information_replacement_sample_acquire.py`

- `projects/llm_forecasting_calibration_program/tools/equal_information_replacement_dispatch_packet.py`

- `projects/llm_forecasting_calibration_program/tools/equal_information_replacement_score.py`

- `projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_export_packet.py`: emits Manifold equal-information request rows.

- `projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_result_acquire.py`: fills Manifold request rows from public market history.

- `projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_result_ingest.py`: ingests the validated Manifold rows.

- `projects/llm_forecasting_calibration_program/tools/non_polymarket_equal_information_score.py`: scores the joined Manifold model-vs-market comparison.

- `projects/llm_forecasting_calibration_program/tools/field_wide_validity_audit_protocol.py`: emits the row schema and 12-route seed matrix for the broader validity-audit route.

- `projects/llm_forecasting_calibration_program/tools/field_wide_validity_source_inventory.py`: records the current external-source access status for those 12 routes and names the next row-level extraction step for each.

- `projects/llm_forecasting_calibration_program/tools/field_wide_forecastbench_row_schema_pilot.py`: applies the row schema to the local ForecastBench 2026-04-12 question bundle and reports validity-field coverage.

- `projects/llm_forecasting_calibration_program/tools/field_wide_forecastbench_score_audit.py`: scores public ForecastBench processed-forecast files and compares eligible market-source rows with the prior-day market value; the manuscript uses it for the 2026 score audit and the 2024 human-comparator audit.

- `projects/llm_forecasting_calibration_program/tools/field_wide_prophet_arena_row_schema_pilot.py`: fetches public Prophet Arena sample releases, audits their task rows against the paper's row schema, and checks public AI Prophet repositories for submitted forecast trace files.

- `projects/llm_forecasting_calibration_program/tools/field_wide_predictionmarketbench_row_schema_pilot.py`: inspects public
  PredictionMarketBench replay episodes and reconstructs same time
  market-baseline rows from orderbook snapshots and settlements.

- `projects/llm_forecasting_calibration_program/tools/field_wide_polybench_source_pilot.py`: verifies the public PolyBench
  repository/schema surface, GitHub release/file status, and
  noninteractive OneDrive dataset status.

- `projects/llm_forecasting_calibration_program/tools/field_wide_validity_local_evidence.py`:
  emits the provenance-limited Halawi date-distribution summary used as a warning, not as a completed audit.

- `projects/llm_forecasting_calibration_program/tools/claim_gap_matrix.py`: emits an evidence matrix separating supported results from
  underpowered results, claims not valid for broad conclusions, and claims requiring external data.

- `projects/llm_forecasting_calibration_program/tools/decisive_continuation_matrix.py`: ranks the follow-up tests by claim impact,
  minimum next step, what would strengthen the claim, and what would rule it out.

- `projects/llm_forecasting_calibration_program/tools/evidence_upgrade_plan.py`: emits a clean evidence-upgrade plan separating the public-benchmark
  audit route, the structured-prompting test, and the larger equal-information
  baseline sample.

- `projects/llm_forecasting_calibration_program/tools/experiment_coverage_summary.py`: reads the historical findings ledger and current queue,
  then emits a reader-facing count summary for included, compressed, deferred,
  and excluded experiment families.

- `projects/llm_forecasting_calibration_program/tools/applied_signal_coverage_audit.py`: records each applied signal as supported, bounded,
  diagnostic, negative guidance, or a future evidence route, with a
  manuscript anchor and next check.

- `projects/llm_forecasting_calibration_program/tools/scored_use_procedure_audit.py`: checks that the scored-use procedure has manuscript text,
  support files, and a stop condition for each operational step.

- `projects/llm_forecasting_calibration_program/tools/prospective_counterexplanation_design_audit.py`: checks that each planned positive result has
  a counter-explanation and a before-scoring design check before it can support
  a broader claim.

- `projects/llm_forecasting_calibration_program/tools/reviewer_concern_coverage_audit.py`: checks that likely reviewer concerns have explicit
  manuscript answers, evidence files, remaining boundaries, and paper anchors.

- `projects/llm_forecasting_calibration_program/tools/forecast_row_validity_benchmark_blueprint.py`: converts the claim-gap and continuation matrices
  into a companion public-benchmark design, including row validity fields,
  equal-information comparators, applied tracks, and failure conditions.

- `llm-forecast-calibration-cross-corpus/evidence/benchmark/run_benchmark.py`: validates and scores a small row-contract packet under the paper's validity rules. The validator requires model-family and evaluation-track fields, separates source-visible rows, label-time failures, eligible forecast rows, and equal-information comparator rows, then reports track and family counts, calibration deltas, pairwise accuracy, and one-row-per-event-family comparator summaries. It is a companion tool, not a new result.

- `projects/llm_forecasting_calibration_program/tools/numeric_claim_trace_audit.py`: checks the manuscript's headline numerical
  statements against the SQLite database and stored score reports.

- `projects/llm_forecasting_calibration_program/tools/central_evidence_effective_n_audit.py`: records calls, contracts or pairs,
  market rows, source counts, and event-group documentation for the central
  evidence slices.

- `projects/llm_forecasting_calibration_program/tools/literature_positioning_audit.py`: checks that each related-work class in
  Table 6 has a bibliography key, source URL, and explicit paper boundary.

- `projects/llm_forecasting_calibration_program/tools/submission_readiness_audit.py`: checks required sections, table/figure labels,
  generated support files, evidence-count floors, broad-claim boundaries, and
  LaTeX log health.

- `projects/llm_forecasting_calibration_program/tools/rendered_pdf_smoke_audit.py`: extracts the compiled PDF text and checks freshness, page count,
  required rendered sections, boundary sentences, and absence of internal draft
  language.

- `llm-forecast-calibration-cross-corpus/evidence/reproducers/make_equal_information_figure.py`: regenerates Figure 2 from the stored equal-information market control score reports.

Together these tools let a reader verify the current market-baseline
coverage, inspect the replacement sample before forecasts, reproduce the
first same-contract market comparison, trace the paper's headline numbers
to current score files, audit central denominators and event-group coverage,
audit related-work positioning, audit how the historical experiment log was
compressed, inspect which applied signals are supported or bounded, check the scored-use procedure and its stop conditions, check the before-scoring counter-explanations for planned positive results, score the public ForecastBench processed-forecast round under the
paper's row checks, inspect Prophet Arena public task-row access and submitted-trace status, inspect
PredictionMarketBench replay-row validity, inspect the PolyBench source-access
gap, check where likely reviewer concerns are answered, inspect the companion benchmark blueprint implied by the missing evidence, run a minimal row-validity benchmark packet end to end, rank the decisive follow-up tests, inspect the evidence-upgrade plan, and
verify that the compiled PDF still contains the required claim boundaries, and
see exactly what evidence is still missing for a broad human/crowd claim,
broader validity claim, or stronger intervention claim.

**Reproduction status.**
Table <a href="#tab:reproduction-status" data-reference-type="ref"
data-reference="tab:reproduction-status">8</a> separates what is
reproducible now from what requires a sanitized or substitute release.
The private low-overlap corpus is the main unreleased component, but it
affects only the secondary low-overlap elicitation findings. The
source currency, label-time, equal-information, market control, and
calibration claims on rows that pass the source currency check are represented by public-market,
official-data, database, scoring, and audit machinery in the repository.

<div id="tab:reproduction-status">

| Component | Current status | Reproduction role |
|:---|:---|:---|
| SQLite evidence database | Present at `analytics/public/calibration/forecaster_calibration.db`. | Reproduces call counts, score joins, source currency screens, 165 label-time rows, and market-baseline coverage. |
| Scoring/audit scripts | Present in the project tool directories and listed above. | Recomputes the paper’s readiness, coherence, equal-information, and label-time checks without new model calls. |
| Evidence, follow-up, and upgrade matrices | Present; generated by the claim-gap, continuation, and evidence-upgrade scripts listed above. | Lists candidate results, missing checks, interpretation changes, and next actions. |
| Applied signal coverage audit | Present; generated by the applied-signal script listed above. | Lists applied components, evidence, use case, boundary, next check, and manuscript anchor. |
| Scored-use procedure audit | Present; generated by the scored-use script listed above. | Checks the operational steps for row screening, equal-information baselines, scoped calibration, ranking-only pairwise use, and prompt-variant gates. |
| Prospective counter-explanation design audit | Present; generated by the prospective counter-explanation script listed above. | Checks that planned positive results name the simpler explanation they must rule out before scoring. |
| Reviewer concern coverage audit | Present; generated by the reviewer-concern script listed above. | Maps likely reviewer concerns to the manuscript answer, evidence files, remaining boundary, and paper anchor. |
| Forecast row validity benchmark blueprint and runner | Present as both a design report and a runnable row-contract validator under `llm-forecast-calibration-cross-corpus/evidence/benchmark/`. | Specifies and tests the companion benchmark shape implied by the missing evidence: row validity core, equal-information comparators, calibration, relative judgment, intervention, choosing among model families, open model replication, and public low-overlap substitute tracks. The bundled example exercises explicit model-family and track fields, calibration output, a pairwise judgment, source-visible rows, and a label-time failure. |
| Broader audit protocol and pilots | Present; generated by the broader-audit scripts listed above. | Supplies the row schema, 12-route source inventory, ForecastBench audits, Prophet Arena task-row check, PredictionMarketBench replay-row coverage, PolyBench source-access status, and Halawi warning; it is not evidence of prevalence across the field. |
| Numeric claim trace | Present; generated by the numeric-trace script listed above. | Checks headline numerical statements against the current database and stored score reports. |
| Central evidence denominator audit | Present; generated by the effective-N script listed above. | Records calls, contracts or pairs, market rows, source counts, and event-group status for the main evidence slices. |
| Literature positioning audit | Present; generated by the literature-positioning script listed above. | Checks that related-work classes have bibliography keys, source URLs, and a clear boundary against the present paper's claim. |
| Submission-readiness audit | Present; generated by the submission-readiness script listed above. | Checks manuscript structure, generated support files, evidence-count floors, broad-claim boundaries, and build-log health. |
| Rendered-PDF smoke audit | Present; generated by the rendered-PDF script listed above. | Checks the compiled PDF, not only the source, for freshness, required rendered sections, boundary text, and internal-language leaks. |
| Public-market samples | Present for Polymarket and Manifold equal-information comparisons. | Reproduces the market control boundary claims. |
| Open-model replication | Not yet run. | Needed for provider-independent generality; not required for the paper's current provider-snapshot claims. |
| Raw low-overlap questions | Not publicly releasable in raw form. | Needed only for direct replication of the private low-overlap elicitation findings. |
| Sanitized or substitute low-overlap corpus | Planned release path: neutralized identifiers plus a public niche-domain substitute with the same four-axis profile. | Enables third-party replication of the frequency-framing, bid-ask, and low-overlap channel findings without exposing private workflow details. |

Reproduction status. The central source currency and equal-information
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
| Universal calibration regularities | Overconfidence on very small probabilities, horizon/source difficulty, YES underprediction, and high family agreement recur across families. | Supplies the candidate features tested by the rule for very small probabilities and composed adjustment. |
| Composed adjustment and model-family headroom | The adjusted aggregate beats mean/median in-cohort but fails stronger scrutiny balanced by source; choosing the best family in hindsight remains much better than observed allocation rules. | Separates real headroom from established allocation evidence. |
| Pairwise ranking and translation | Pairwise contrastive ranking is stronger than raw probability translation; translation remains promising but is not yet supported as a standalone probability model. | Retains pairwise ranking as a controlled use, not evidence that LLMs are superior to markets or humans. |
| Source and label-time audits | Manifold source currency, FRED vintage repair, failed Polymarket freeze design, replacement Polymarket, and Manifold equal-information fill show that validity checks change conclusions. | Forms the measurement-validity contribution and bounds the applied claims. |
| Prompt intervention | Expert-training improves paired Brier versus bare and placebo prompts in a completed Gemini public question comparison; generic reflection, self-revision, and diagnostic allocation mostly fail or produce no measurable change under controls. | Keeps a Gemini-specific candidate for replication while rejecting broad prompt-only improvement. |

Evidence-preservation table for compressed diagnostics. Compression
changes placement, not the underlying scope boundaries.

</div>

# Coverage audit for omitted or deferred work

The project log contains many more experiments than the main paper
reports. The inclusion rule is conservative: a result appears in the
main text only if it changes the validity layer, a supported use case, a
stated limit, or a continuation test.
The
`projects/llm_forecasting_calibration_program/tools/experiment_coverage_summary.py`
script parses both the full research log and the curated findings ledger
before compression. In the current snapshot it detects 111 unique numbered
rows in the full research log, with 74 outside the curated paper ledger. The
curated ledger then classifies 37 paper-relevant rows: 3 central
validity/control/calibration rows, 19 secondary diagnostics retained in the
paper, 7 retractions/supersessions/underpowered boundaries, 7 sibling workflow
or non-forecasting findings excluded from this manuscript, and 1
execution/persistence row with no paper claim. The
`projects/llm_forecasting_calibration_program/tools/applied_signal_coverage_audit.py`
script separately records 8 applied components: 6 supported or scoped candidate
components, 1 negative guidance row, and 1 external evidence route. The structured-prompt
comparison is now complete at 600/600 scored Gemini calls across 120
contracts; the expert-training arm passes the bare/placebo and same row
calibrated bare checks, while market checks remain unfavorable, the near-complete
Claude run does not clear the replication gate at 591/600 calls, and the 448-call
Codex+DeepSeek staged run does not pass the replication gate.
Table <a href="#tab:coverage-audit" data-reference-type="ref"
data-reference="tab:coverage-audit">10</a> records the main excluded or
deferred families so that compression does not hide evidence.

<div id="tab:coverage-audit">

| Work family | Why it is not a main claim | How the insight is preserved |
|:---|:---|:---|
| Prompt-intervention variants | One expert-training prompt beats bare and placebo prompts in the completed Gemini public question comparison; generic reflection, selective action, self-revision, and diagnostic-triggered allocation do not beat the relevant controls. | Reported as a Gemini-specific candidate plus negative evidence against unvalidated prompt-only interventions. |
| Objective effort / coding-task calibration | This is a sibling problem about effort prediction and hidden-test performance, not the same forecast row validity question. | Excluded from this paper unless it later supplies a forecasting-specific intervention that clears source and market controls. |
| Proof-audit and workflow-only findings | These improve the research workflow but ask reviewers to switch domains away from event forecasting. | Excluded from the main manuscript; relevant only as provenance for the audit discipline. |
| Low-overlap elicitation retests | Several channel findings are promising but still corpus-bound or underpowered for claims across sources. | Preserved as diagnostics and continuation tests: replicate on a public niche corpus or sanitized release before generalizing. |
| Fitted calibrators and allocation rules | Source-isotonic, graph-family weighting, and diagnostic allocation have not beaten simpler controls robustly. | Reported as headroom evidence; applied use waits for panels balanced by source or an external reviewer/market expert. |
| Prospective market freeze comparisons | Frozen market bars exist for some future comparisons, but unresolved outcomes cannot score current claims. | Listed as continuation tests; no standalone probability layer until outcomes resolve and market, raw, and calibrated controls are passed. |
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
reported in $`\S\ref{sec:universal}`$ (overconfidence on very small probabilities,
middle-band YES underprediction, horizon-conditional Brier slope,
per-source Brier ordering). The per-channel alternative described in the
main text substitutes per-family channel weights for the universal
$`w_s`$; its weights are listed in the appendix support file. The
implementation is in the forecasting-calibration workspace and
reproduces on the database snapshot dated 2026-05-28.
