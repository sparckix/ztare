# Introduction

#### Eigenproblem.

Which LLM forecasting behaviours are structural inheritances of the
training-text distribution the model samples from, and along which axes
can the transfer pattern be predicted ex ante from the structural origin
of each behaviour?

#### Epistemic shape.

The paper is empirical first and theoretical second. We ran a
multi-pilot forecast-calibration program (five-model panel, two corpora,
$30{+}$ measured findings, pre-registration discipline) without a
unifying theoretical commitment. The three-axis inheritance frame below
was **induced from the body of measurements in retrospect** as the most
parsimonious structure organising the per-family heterogeneity, the
universal patterns, and the bias-transfer findings together. We treat
the framework's status accordingly: it earns the right to be called a
unifying frame only to the extent that it makes pre-registered
predictions on bias transfers we had not yet measured at the time of
synthesis. Section $\S$[15](#sec:bias-inheritance){reference-type="ref"
reference="sec:bias-inheritance"} reports the in-sample evidence;
section $\S$[17](#sec:freq-inheritance-test){reference-type="ref"
reference="sec:freq-inheritance-test"} reports the predictive test on a
held-out slate of biases pre-registered under the framework.

#### The three-axis inheritance frame (inductively derived).

The findings in this paper are organised by three structural axes along
which training-text inheritance shows up in the forecast distribution.
Each axis governs a different family of measurements; together they
cover the program's per-family heterogeneity, universal patterns, and
bias-transfer findings.

- **Axis 1, Elicitation surface.** Which channels the model exposes when
  asked to forecast (a point estimate $p_{\text{success}}$, a bid-ask
  spread $p_{\text{buy yes max}} / p_{\text{sell yes min}}$, a
  tail-worry scalar, a self-predicted Brier interval, an asymmetric-loss
  decision threshold). The model emits the channels that its training
  distribution rewards; channels differ across families because training
  mixes differ.

- **Axis 2, Bias-mechanism class.** A three-cell taxonomy on which human
  cognitive biases transfer to LLM forecasting and how. *Pure heuristic*
  biases (cognitive shortcuts with high natural-speech footprint, like
  anchoring or self-overconfidence) [inherit]{.smallcaps}. *Pure
  motivational* biases (intrinsic utility / fear / consumption
  preference, like loss aversion or hyperbolic discounting)
  [escape]{.smallcaps}: the model has no utility function, the text has
  no representation of the mechanism, no transfer. *Systemic
  motivational* biases (intrinsic utility but heavy case-study
  representation in training text, like sunk cost or in-group framing)
  [mimic]{.smallcaps}: the model emits utility-like behaviour because
  the text frequency of the bias being discussed drives the output, not
  a utility function operating.

- **Axis 3, Family/alignment overlay.** Family identity reshapes
  inherited-bias magnitude and per-family channel surfaces. Per-family
  heterogeneity in worry-channel sign, channel decomposition $R^2$, and
  meta-cognitive routing all live on this axis. We call this an alignment
  overlay only as a hypothesis for matched-checkpoint follow-up; the
  measurements here are cross-family and therefore confound RLHF/alignment
  with pretraining mix.

The contribution shape is the **synthesis** of the three axes plus the
[mimic]{.smallcaps} category as a specifically novel articulation on
axis 2: prior LLM-bias work has not separated
transfer-because-mechanism-is-shared (inherit) from
transfer-because-bias-is-discussed-extensively-in-text (mimic). The
[mimic]{.smallcaps} category lets the same surface observation carry
different interpretations depending on which cell the bias belongs to. A later
180-call anti-bias-collapse smoke scoped down the strongest prompt-actuation
version of this mechanism: directional MIMIC collapse did not survive
label-shuffle control, and raw-gap adjustment reversed the MIMIC coefficient.
We therefore keep [mimic]{.smallcaps} as a representational taxonomy, not as a
clean anti-bias-prompt law.

#### Methodological backbone.

A power-aware verdict resolver (Fisher-$z$ sample-size computation
before fire, three legal verdicts after `h1_supported` / `h0_kept` /
`inconclusive_underpowered`, equivalence testing instead of "$p > 0.05$"
as a no-effect claim, BH-FDR across panel tests, leave-one-out $R^2$ at
small $N$) sits underneath every empirical claim in the paper.
Internally, $8$ of $12$ prior nulls in this program turned into
`inconclusive_underpowered` under the resolver, and $5$ cross-corpus
claims retracted to corpus-specific. The discipline ITSELF is a
methodological contribution because the same overcalling failure mode
plausibly affects the field's existing $N{=}5$--$20$ cross-corpus
headlines. A second-order application (corpus-validity drift: when a
benchmark's resolution dates are post-cutoff for the publication-era
LLMs and pre-cutoff for the next-generation LLMs replicating against it)
is the most consequential field-corrective the discipline has produced,
applied to the Halawi 2024 dataset (Halawi et al. 2024) in
$\S$[18](#sec:reaudit){reference-type="ref" reference="sec:reaudit"}.

#### Reading order.

Axes 1--3 are introduced in
$\S$[3](#sec:theoretical-frame){reference-type="ref"
reference="sec:theoretical-frame"}; Axis 1 findings sit in
$\S$[7](#sec:bid-ask-spread){reference-type="ref"
reference="sec:bid-ask-spread"},
$\S$[8](#sec:channel-orthogonality){reference-type="ref"
reference="sec:channel-orthogonality"},
$\S$[11](#sec:multi-channel-r2){reference-type="ref"
reference="sec:multi-channel-r2"}; Axis 2 findings sit in
$\S$[15](#sec:bias-inheritance){reference-type="ref"
reference="sec:bias-inheritance"} (with the [mimic]{.smallcaps} category
as the central original contribution) and inside the universal-patterns
diagnostic rules in $\S$[14](#sec:universal){reference-type="ref"
reference="sec:universal"} (the confident-NO discount as the
[inherit]{.smallcaps} cell in deployment shape); Axis 3 findings sit in
$\S$[5](#sec:worry-direction-split){reference-type="ref"
reference="sec:worry-direction-split"},
$\S$[10](#sec:worry-mechanism){reference-type="ref"
reference="sec:worry-mechanism"}, and the per-family channel-routing
results. The methodological backbone runs underneath all of them and is
collected in $\S$[18](#sec:reaudit){reference-type="ref"
reference="sec:reaudit"}. An honest scope statement
($\S$[19](#sec:limits){reference-type="ref" reference="sec:limits"}) and
the reproducibility plan ($\S$[20](#sec:repro){reference-type="ref"
reference="sec:repro"}) close the paper.

# Setup {#sec:setup}

## Five LLM families

Claude Opus 4.7 (Anthropic, via Claude Code CLI), GPT-5.5 and
GPT-5.4-mini (OpenAI, via Codex CLI), Gemini 2.5 Flash (Google GenAI
API), DeepSeek Chat (DeepSeek API). All API calls
$\text{temperature}{=}0$ unless explicitly noted. All paths audited for
web-search-tool access; all prompts include an explicit "do NOT use web
search" instruction.

## Two corpora, four confounded axes {#sec:corpora}

We use a *low-overlap corpus* of $N{=}15$ bespoke questions drawn from a
research-internal domain with effectively zero LLM-pretraining overlap
(formal-proof tactic combinations, gated state transitions in a
substrate-specific apparatus, ground-truth-confirmed forecasting
contracts), and a *public-domain corpus* of $N{=}42$ contracts from
prediction markets (Manifold, Polymarket), stock-close thresholds, and
ETF moves.

  Axis                       Low-overlap ($N{=}15$)                                          Public-domain ($N{=}42$)
  -------------------------- --------------------------------------------------------------- ------------------------------------
  LLM pre-training overlap   Effectively zero                                                Substantial
  Question length            247 chars (35 words)                                            99 chars (17 words)
  Question structure         Multi-conditional, code/math symbols, parenthetical embedding   Atomic, simple syntactic structure
  Implicit base rate         Ill-defined (bespoke operations)                                Public-market priors well-trained

The four axes are confounded in the current data. Low-overlap-corpus
questions are long-complex-alien-no-public-prior *together*;
public-domain are short-simple-familiar-with-public-prior *together*.
Our cross-corpus result ($\S\ref{sec:frequency-framing}$) is therefore
evidence that *at least one* of these axes matters; a 4-cell
de-confounded corpus design that breaks the confound is the
highest-priority methodological follow-up ($\S\ref{sec:limits}$).

The low-overlap corpus is research-internal and not publicly releasable
in raw form; the reproducibility plan ($\S\ref{sec:repro}$) addresses
this through a sanitized release with neutral identifiers and a parallel
public-but-niche-academic corpus matching the four-axis profile.

## Pre-registration and power-aware verdicts

Every pilot is pre-registered in a SQLite `pre_registrations` table
before launch with hypothesis, null, target effect size,
$n_{\text{required}}$ (auto-computed via Fisher-$z$ at $\alpha{=}0.05$
two-tailed, $80\%$ power, Spearman correction $+6\%$), falsifiers, and
pass-gate. Resolution uses three legal verdicts:

- `h1_supported`: 95% CI on observed $\rho$ excludes 0.

- `h0_kept`: 95% CI wholly within $(-\text{target}, +\text{target})$;
  data rules out a meaningful effect.

- `inconclusive_underpowered`: observed $|\rho|$ below detectability at
  the run $N$; CI wide.

Brier-delta tests use paired-contract sign-flip permutation with a 90%
bootstrap CI plus a BIC-approximation Bayes factor. "No effect" claims
also require TOST equivalence at a pre-stated bound. Power thresholds at
$\alpha{=}0.05$ / power$=0.80$: $N{=}15 \Rightarrow |\rho| \geq 0.68$;
$N{=}42 \Rightarrow 0.43$; $N{=}91 \Rightarrow 0.30$.

# The three-axis inheritance frame {#sec:theoretical-frame}

Before reporting the empirical findings, we name the structural axes the
program's measurements turned out to organise along. These axes were not
stated in advance; they are the most parsimonious reading of the body of
findings the program produced. The framework's predictive content is
tested separately ($\S\ref{sec:freq-inheritance-test}$).

#### Axis 1: elicitation surface.

An LLM forecaster, when asked, emits a set of channels: at minimum a
point estimate $p_{\text{success}}$; optionally a tail-worry scalar
("how worried are you?"), a bid-ask spread
$(p_{\text{buy yes max}}, p_{\text{sell yes min}})$, a self-predicted
Brier interval $(b_{\text{lo}}, b_{\text{hi}})$, an asymmetric-loss
decision threshold under specified false-positive vs. false-negative
cost regimes, or an outside-view base rate from analogous prior
contracts. The set of channels the model surfaces is itself the first
inheritance signature: training-mix differences across model families
produce different elicitation surfaces, even when prompted identically.
$\S\ref{sec:bid-ask-spread}$ introduces the bid-ask spread as a novel
diagnostic error-warning channel that is elicitable on the low-overlap
corpus; $\S\ref{sec:channel-orthogonality}$ shows the three uncertainty
channels are statistically independent on a paired panel, motivating
per-family channel analysis; $\S\ref{sec:multi-channel-r2}$ shows only
one family generalises a multi-channel decomposition under leave-one-out
cross-validation. All three findings sit on this axis.

#### Behavioral latent-carrier interpretation.

We do not observe the hidden activations of the closed models used here,
so our channel claims are behavioral rather than mechanistic-
interpretability claims. Still, the right unit is closer to a structured
carrier than to the generated rationale. Recent latent-prediction theory
shows that learning or predicting internal representations can avoid the
sample-complexity cost of token-level prediction on hierarchical
data (Korchinski, Favero, and Wyart 2026). Our setting is not
training-time latent prediction, but the analogy is operationally useful:
the channel fields are forced intermediate representations whose relation
to Brier can be scored directly, while free-form rationale tokens are a
noisy surface artifact. Two small follow-up smokes across two families found
that structured evidence carriers beat free prose on mean Brier, while the
stricter two-step variant did not consistently beat a same-turn carrier. A
later placebo-control smoke was harsher: among 30 schema-valid rows, baseline
mean Brier was `0.078000`, two-call prose `0.107254`, same-turn carrier
`0.110300`, free prose `0.122767`, and two-step carrier `0.149921`; ten
additional Codex rows failed at runtime before forecasts. This is not a
validated law. It keeps structured carrier fields as a hypothesis for larger
paired tests, but argues against treating the hard prompt break as an
established mechanism.

#### Axis 2: bias-mechanism class.

We propose a three-cell taxonomy for how human cognitive biases transfer
to LLM forecasting.

- [Pure heuristic]{.smallcaps} (cognitive shortcut, high natural-speech
  footprint). Examples: anchoring (Tversky and Kahneman 1974),
  self-overconfidence (Lichtenstein, Fischhoff, and Phillips 1977), the
  gambler's fallacy (Tversky and Kahneman 1971). Predicted
  manifestation: **inherit** ($\,$training-text frequency drives the LLM
  output directly via the token distribution).

- [Pure motivational]{.smallcaps} (intrinsic utility / fear /
  consumption preference; low representation in raw analytical text).
  Examples: loss aversion in the Kahneman-Tversky sense (Kahneman and
  Tversky 1979), cumulative prospect theory probability
  weighting (Tversky and Kahneman 1992), hyperbolic
  discounting (Frederick, Loewenstein, and O'Donoghue 2002). Predicted
  manifestation: **escape** ($\,$the LLM has no utility function and the
  text has no representation of the bias mechanism, so no transfer).

- [Systemic motivational]{.smallcaps} (intrinsic utility BUT heavy
  case-study / behavioural-economics-literature representation in
  training text). Examples: sunk-cost reasoning (Arkes and Blumer 1985),
  endowment / status-quo bias (Thaler 1980), in-group framing (Tajfel
  and Turner 1979). Predicted manifestation: **mimic** ($\,$the LLM
  emits utility-like behaviour, but the mechanism producing the output
  is text-frequency representation of the bias being discussed in
  training text, not a utility function operating).

The [mimic]{.smallcaps} cell is the central original contribution of the
framework. Prior LLM-bias work has not separated
transfer-because-the-mechanism-is-shared ([inherit]{.smallcaps}) from
transfer-because-the-bias-is-discussed-extensively-in-text
([mimic]{.smallcaps}). The cell distinction matters because it suggests
different intervention surfaces, but the direct anti-bias-prompt signature did
not promote as a clean law: in the 180-call collapse smoke, MIMIC mean collapse
was positive but underpowered, the class-label shuffle was null ($p=0.5387$),
and the raw-gap-adjusted MIMIC coefficient was negative ($-0.076587$,
$p=0.0025$). The supported claim is therefore taxonomic and diagnostic; a
causal anti-bias-collapse mechanism requires matched raw-gap strata or
randomization.

#### Axis 3: alignment overlay.

RLHF and post-training alignment damp some inherited biases
(truthfulness, helpfulness training reduces obvious factual
hallucinations and overt in-group preference) and reshape per-family
channel surfaces. Per-family worry-Brier sign differences
($\S\ref{sec:worry-direction-split}$), per-family channel-decomposition
$R^2$ differences ($\S\ref{sec:multi-channel-r2}$), and the
meta-cognitive routing failure where three of five families pick the
WRONG channel they should rely on at $p \leq 0.005$ each
($\S\ref{sec:conditional}$) all live on this axis. The empirical
signature is that family identity, conditional on channel and contract,
is itself a central predictor.

#### The methodological backbone is orthogonal to the three axes.

A verdict-resolver discipline (Fisher-$z$ power calculation before fire,
three legal verdicts after, equivalence testing, BH-FDR, LOO-$R^2$ at
small $N$) sits underneath every axis-1/2/3 measurement. The discipline
produced the program's most consequential retraction: 8 of 12 prior "no
effect" claims turned into `inconclusive_underpowered` under the
resolver, and the corpus-validity-drift filter (resolve_date $>$
`max(panel_cutoff)`) empties the most-cited 2024 LLM-forecasting
benchmark for the current LLM generation ($\S\ref{sec:reaudit}$).

# Foundation: the worry scalar is Bayesian-coherent tail risk {#sec:worry-foundation}

The basic uncertainty primitive used throughout this paper is
`tail_insurance_premium` (worry scalar, $1$--$100$, requested in the
same prompt as the binary forecast). This primitive was validated in a
separate within-program pilot before any of the downstream analyses: at
pool level $N{=}590$ on an independent cross-pool forecast corpus, the
worry scalar is a Bayesian-coherent tail-risk signal, more-worried
forecasts ARE more likely to be wrong, in expectation. This is the only
well-powered *positive* pool-level validation of a
verbalized-uncertainty primitive in our program; everything that follows
uses worry as a base channel, and the per-model decomposition in
$\S\ref{sec:worry-direction-split}$ shows the pool-level signal is the
average of opposite per-family signs.

# Per-family worry-Brier direction split, three-pilot replication {#sec:worry-direction-split}

For each LLM family we compute the rank correlation between the worry
score and the realized squared error (Brier) of the forecast that the
worry accompanied. Three independent pilots ($N{=}164$, $N{=}85$, and
$N{=}115$; cumulative $N{=}264$) replicate this analysis:

- Claude Opus 4.7: $\rho < 0$, most worried when most right
  (anti-Dunning-Kruger).

- GPT-5.5: $\rho < 0$, same direction.

- GPT-5.4-mini: $\rho > 0$, direction-sensible (worried when wrong).

Per-pilot detectable $|\rho|$ at 80% power is $\approx 0.30$ for
$N{=}85$; observed $|\rho|$ values span $0.31$--$0.56$ across families,
clearing detectability for Claude and GPT-5.5 individually. Cross-pilot
Stouffer $Z$ meta-analysis combines the three pilots at combined
$p < 0.01$. **This is the per-model finding that survives the largest
paired-permutation budget in the program.**

A natural reviewer hypothesis is that the sign-flip is mediated by task
complexity: complex tasks produce longer rationales; longer rationales
correlate with both higher stated worry AND lower Brier (more thorough
reasoning); the apparent inversion is an artifact of this joint
mediation. We test the mediator directly on $N{=}45$--$91$ per family.
None of the five families exhibits the predicted pattern of "long
rationale $\rightarrow$ high worry AND long rationale $\rightarrow$ low
Brier." Claude's $\rho(\text{rat\_length}, \text{tip}) \approx 0$
(claude does not worry more about long rationales); Gemini's
$\rho(\text{rat\_length}, \text{Brier})$ is POSITIVE, the opposite of
the reviewer's predicted direction. **The
task-complexity-via-rationale-length mediator is rejected.**

The refined mechanism we propose is given in
$\S\ref{sec:worry-mechanism}$ after $\S\ref{sec:cognitive-decoupling}$
provides the upstream decoupling result.

# Cognitive content and calibration shift are decoupled {#sec:cognitive-decoupling}

Across three pilots (pooled $N{=}320$ analytic), we measure the
within-family Spearman correlation between the count of failure-mode
words in the rationale and the per-row Brier:

  Family                  $N$        $\rho(\text{failure-mentions}, \text{Brier})$
  ------------------ -------------- -----------------------------------------------
  Claude Opus 4.7     $\approx 60$                      $+0.27$
  GPT-5.5             $\approx 60$                      $+0.18$
  GPT-5.4-mini        $\approx 60$                      $+0.21$
  Gemini 2.5 Flash        $60$                     $\mathbf{-0.045}$
  DeepSeek Chat           $59$                     $\mathbf{+0.049}$

At $N{=}60$ per family the detectable $|\rho|$ at 80% power is
$\approx 0.36$. Gemini and DeepSeek's near-zero $\rho$ values fall
within the `h0_kept` band at $|\rho|{<}0.20$. The model produces
failure-mode reasoning text on demand, cognitive shift is real, but does
not recompute the point estimate from that content. This is the cleanest
mechanism evidence in the program and connects to the
chain-of-thought-faithfulness lineage (Lanham et al. 2023); the original
trio shows weak positive correlation consistent with partial propagation
rather than full decoupling.

# Bid-ask spread: a novel meta-uncertainty primitive {#sec:bid-ask-spread}

Instead of asking the model for one probability, we elicit three in the
same prompt: the highest probability at which it would BUY a YES
contract, its point estimate, and the lowest probability at which it
would SELL YES. The spread (sell $-$ buy) is the model's self-reported
uncertainty about its own probability, a Knightian bracket distinct from
the unidirectional worry scalar.

  Family               Mean spread   $\rho(\text{spread}, \text{Brier})$      95% CI (Fisher-$z$)                 Verdict
  ------------------- ------------- ------------------------------------- --------------------------- -------------------------------
  Claude Opus 4.7        $0.21$                    $+0.49$                     $[-0.03, +0.80]$             CI barely touches 0
  GPT-5.5                $0.24$                    $-0.05$                     $[-0.55, +0.47]$                inconclusive
  **GPT-5.4-mini**       $0.26$               $\mathbf{+0.69}$             $\mathbf{[+0.28, +0.89]}$   **h1_supported**, $p{=}0.013$
  Gemini 2.5 Flash       $0.21$                    $+0.40$                     $[-0.15, +0.75]$                inconclusive
  **DeepSeek Chat**      $0.26$               $\mathbf{+0.69}$             $\mathbf{[+0.27, +0.89]}$   **h1_supported**, $p{=}0.013$

Pre-registered pass-gate met: two of five families clear $\rho > 0.3$
with non-zero-crossing CI at $N{=}15$ low-overlap. No family shows the
wrong sign. To our knowledge no prior LLM-forecasting paper has elicited
bid-ask spread as an uncertainty primitive. The market-microstructure
framing forces the model into a more demanding cognitive task than the
scalar worry, which we conjecture is exactly why it produces a more
honest meta-uncertainty signal (the elaboration is supported by the
channel-orthogonality result in $\S\ref{sec:channel-orthogonality}$).

**Cross-corpus failure-to-replicate.** On the public-domain $N{=}42$
corpus, all per-family CIs cross zero (detection threshold
$|\rho|{\geq}0.43$ at 80% power for $N{=}42$). The point-estimate $\rho$
values for GPT-5.4-mini ($-0.11$) and DeepSeek ($-0.07$) flip sign.
Either (a) the primitive is corpus-specific consistent with the
four-axis confound, or (b) $N{=}42$ remains underpowered to confirm a
smaller-but-real positive effect. To distinguish requires $N{\geq}91$
public-domain. The honest framing is *low-overlap-corpus positive with
explicit cross-corpus failure-to-replicate*.

# LLM uncertainty channels are statistically independent {#sec:channel-orthogonality}

Pooling three low-overlap-corpus full pilots (worry-scalar baseline,
bid-ask spread, reasoning-trajectory variance) on the $N{=}75$ rows
where all three are observed, the pairwise Pearson correlation matrix
among the three uncertainty channels:

                         worry scalar   bid-ask spread   trajectory variance
  --------------------- -------------- ---------------- ---------------------
  worry scalar              $1.00$         $+0.08$             $+0.17$
  bid-ask spread           $+0.08$          $1.00$             $+0.03$
  trajectory variance      $+0.17$         $+0.03$             $1.00$

The off-diagonals are all below $0.20$. PCA would not produce
dimensionality reduction. Each primitive is measuring something
genuinely different about how a model expresses uncertainty.

Per-family $\rho(\text{channel}, \text{Brier})$ reveals that each model
family has a different "best channel":

  Family              $\rho(\text{worry}, \text{Brier})$   $\rho(\text{spread}, \text{Brier})$   $\rho(\text{traj\_var}, \text{Brier})$        Best channel
  ------------------ ------------------------------------ ------------------------------------- ---------------------------------------- ------------------------
  Claude Opus 4.7           $-0.38$ (sign-flipped)                       $+0.02$                                $+0.08$                   worry (with sign flip)
  GPT-5.5                          $+0.07$                               $+0.12$                                $-0.18$                      weak across all
  GPT-5.4-mini                     $-0.18$                          $\mathbf{+0.55}$                            $-0.22$                     **bid-ask spread**
  Gemini 2.5 Flash                 $+0.10$                               $+0.10$                                $+0.25$                    trajectory variance
  DeepSeek Chat             $-0.26$ (sign-flipped)                  $\mathbf{+0.29}$                            $-0.10$                     **bid-ask spread**

**There is no universal best uncertainty primitive across LLMs.** The
diagnostic recipe is per-family elicitation analysis: identify the best
channel per family via a pre-registered pilot, then treat that channel
as an error-warning candidate rather than a deployment rule.
Per-primitive per-family single-channel
$R^2$ on the same-pilot Brier is $10$--$26\%$ for the families where the
channel works (GPT-5.4-mini's bid-ask explains $26\%$ of bid-ask-pilot
Brier; DeepSeek's $19\%$). The multi-channel $R^2$ from the
all-channels-in-one-prompt pilot is reported with leave-one-out
cross-validation in $\S\ref{sec:multi-channel-r2}$, where only GPT-5.5
survives LOO on the public-domain corpus.

**Scope of the orthogonality claim.** The result is at the *expression*
level. A reasoning-decomposition claim would require mechanistic
interpretability tooling, logit lens, attention probing, causal
intervention on chain-of-thought spans, which we do not use. Our
primitives are black-box behavioral probes of uncertainty expression;
the diagnostic implication (per-family channel analysis) is unchanged,
but the mechanistic-reasoning claim is left for white-box work, and a
prospective routing policy must separately clear heldout Brier controls.

# Frequency framing transfers in a corpus-specific way {#sec:frequency-framing}

Tetlock-style "imagine 10 similar contracts; how many resolve as
success?" (Tetlock and Gardner 2015) framing on the low-overlap corpus
($N{=}15$ each, paired permutation vs the same-corpus baseline):

  Family               $\Delta$-Brier              95% CI                $p$ (perm)          Verdict
  ------------------ ------------------- --------------------------- ------------------ ------------------
  Claude Opus 4.7         $-0.006$            $[-0.05, +0.03]$              0.85           inconclusive
  GPT-5.5                 $+0.014$            $[-0.06, +0.09]$              0.74           inconclusive
  **GPT-5.4-mini**    $\mathbf{-0.118}$   $\mathbf{[-0.21, -0.04]}$   $\mathbf{0.013}$   **h1_supported**
  Gemini 2.5 Flash        $-0.118$            $[-0.28, +0.03]$              0.19           inconclusive
  DeepSeek Chat           $+0.115$            $[-0.02, +0.28]$              0.18           inconclusive

On the public-domain $N{=}42$ corpus:

  Family              $\Delta$-Brier         95% CI          Verdict at bound $0.05$
  ------------------ ---------------- -------------------- ---------------------------
  Claude Opus 4.7        $-0.003$      $[-0.030, +0.028]$          **h0_kept**
  GPT-5.5                $+0.005$      $[-0.012, +0.023]$          **h0_kept**
  GPT-5.4-mini           $+0.003$      $[-0.042, +0.053]$          borderline
  Gemini 2.5 Flash       $+0.052$      $[+0.000, +0.112]$   not h0_kept ($p{=}0.071$)
  DeepSeek Chat          $-0.001$      $[-0.031, +0.030]$          **h0_kept**

**GPT-5.4-mini's low-overlap-corpus improvement does NOT replicate on
the public-domain corpus.** Direction goes from $-0.118$ to $+0.003$.
For 3 of 5 families the public-corpus Brier-delta is `h0_kept` at bound
$\pm 0.05$, the data actively rules out a 5%-Brier effect on
public-domain questions. Sub-source stratification within the public
corpus reveals heterogeneity the aggregated null masks: Gemini on
Polymarket-style questions trends $\Delta{=}+0.138$ ($p{=}0.14$);
DeepSeek shows opposite-sign effects on Manifold-bulk vs Polymarket;
GPT-5.4-mini is genuinely corpus-specific (every sub-source
$\Delta \in [-0.002, +0.007]$, no false-negative from aggregation).

**The clean claim.** Frequency framing's effect on LLM forecasters is
corpus-specific and model-specific: it improves GPT-5.4-mini on
low-overlap apparatus questions only. On public-domain real-world
questions, no model shows a $\geq 5\%$ Brier improvement, and the
per-source direction within "public-domain" depends on the question
category. Pre-registration prevented us from over-stating the
cross-corpus claim as a general failure-of-transfer; the specific
finding is the corpus-dependent transfer.

# Refined mechanism for the worry-scalar sign-flip: shared topic-trigger × per-family accuracy {#sec:worry-mechanism}

A reviewer-flagged concern is that the affect-proxy hypothesis
($\S\ref{sec:worry-direction-split}$ early framing) was still just a
hypothesis. We ran four mechanism probes on existing within-program data
to disambiguate.

**Probe 1.** Within-family rank correlation between (across-family
$p$-variance per contract, used as a proxy for intrinsic question
difficulty) and (that family's mean worry on that contract).
GPT-5.4-mini shows $\rho{=}-0.43$, 95% CI $[-0.69, -0.07]$,
`h1_supported` *negative*, the opposite direction from a
"question-difficulty confound" mediator. The mediator hypothesis is
rejected.

**Probe 2.** Stratified $\rho(\text{worry}, \text{Brier})$ by question
difficulty (hard half vs easy half) and by point-estimate extremity
(uncertain $p \in [0.4, 0.6]$ vs confident). Claude's inversion lives in
the EASY-contracts subset only ($\rho_{\text{EASY}} = -0.19$,
$\rho_{\text{HARD}} = +0.03$); GPT-5.5's inversion lives in the
UNCERTAIN-$p$ subset only ($\rho{=}-0.31$, $n{=}21$). The sign-flip is
family-specific AND subspace-specific; no single uniform mechanism.

**Probe 3.** Lexical log-likelihood-ratio of distinguishing tokens
between high-worry (`tip`${\geq}70$) and low-worry (`tip`${\leq}30$)
rationales per family. Under affect-proxy, high-worry rationales should
be enriched in CAREFUL (*analyze*, *consider*) or UNCERTAIN (*unsure*,
*difficult*) words. We observe instead that the dominant distinguishing
terms are *specific content-topic words*, *tactic*, *convolution*,
*measurability*, *singularity*, consistent with a topic-trigger rather
than affect-proxy hypothesis.

**Probe 4.** Cross-family worry agreement: do families AGREE on which
contracts get high worry? Pairwise Spearman correlation between each
pair of families' mean-worry-per-contract gives Claude $\leftrightarrow$
GPT-5.5 $\rho{=}+0.40$ (`h1_supported`), GPT-5.5 $\leftrightarrow$
GPT-5.4-mini $\rho{=}+0.41$ (`h1_supported`), GPT-5.4-mini
$\leftrightarrow$ DeepSeek $\rho{=}+0.64$ (`h1_supported`). **Families
share a topic-trigger signal: they pick the same contracts as
high-worry.**

**Probe 5.** $\rho(\text{worry}, \text{wallclock\_seconds})$ per family,
does the model "think longer" on high-worry rows? All families show
$|\rho|{\leq}0.25$ with CIs crossing zero. Worry is NOT a compute-effort
proxy.

**Probe 6, mean-regression within row.** For each row we measure
$\rho(\text{worry}, |p_{\text{success}} - 0.5|)$ per family. Claude:
$\rho{=}-0.39$ 95% CI $[-0.55, -0.20]$, `h1_supported` negative.
Codex-mini: $-0.59$ $[-0.72, -0.41]$, `h1_supported`. DeepSeek: $-0.35$
$[-0.58, -0.06]$, `h1_supported`. GPT-5.5 and Gemini both null. **Three
of five families moderate their probability when emitting high worry.**

**Probe 7, per-contract accuracy alignment.** Rank contracts by claude's
mean worry. Compare mean Brier per family in the top-quartile
(claude-high-worry contracts) vs bottom-quartile (claude-low-worry
contracts):

  Family                 Top-quartile Brier   Bottom-quartile Brier         Diff
  --------------------- -------------------- ----------------------- -------------------
  **Claude Opus 4.7**        **0.181**              **0.392**         $\mathbf{-0.211}$
  GPT-5.5                     $0.199$                $0.224$              $-0.025$
  GPT-5.4-mini                $0.160$                $0.219$              $-0.060$

**Claude is half as wrong on its high-worry contracts. The other
families show small or no asymmetry.**

**Probe 8. RLHF hedging mediator (rejected).**
$\rho(\text{hedging-vocabulary density}, \text{Brier})$ is POSITIVE for
Claude ($+0.15$) and GPT-5.4-mini ($+0.31$), opposite the direction of
their worry-Brier inversion. Hedging-language is not the mediator.

**Converged synthesis: a two-mechanism interaction.** The worry-Brier
sign-flip emerges from the simultaneous presence of two distinct
mechanisms:

1.  *Worry-triggered mean-regression.* High worry $\rightarrow$
    less-extreme $p$ on the same row (Probe 6). Three of five families
    show this at `h1_supported`.

2.  *Per-family accuracy alignment with the trigger topics.* The shared
    topic-trigger (Probe 4) flags long-structured apparatus contracts as
    high-worry. Claude is GENUINELY BETTER on those contracts (Probe 7,
    diff $-0.21$); GPT-5.4-mini is not (diff $-0.06$).

Claude has BOTH (1) and (2): moderation lands close to truth on
contracts where claude is accurate $\rightarrow$ inverted
$\rho(\text{worry}, \text{Brier})$ (the sign-flip signature).
GPT-5.4-mini has (1) but not (2): moderation doesn't save it on topics
it's weaker on $\rightarrow$ direction-sensible
$\rho(\text{worry}, \text{Brier})$. GPT-5.5 has neither cleanly at the
pooled-across-conditions level, and its worry-Brier inversion
(documented at the per-pilot positive-magnitude-balance-off cell,
$N{=}85$) is condition-specific.

The mechanism is identified at evidence-summary grade for Claude (the
most cleanly-inverted family). It is partial for the other inverted
families. White-box activation-level probing would directly test which
activations drive worry emission versus probability emission; we have
only the black-box behavioral signature. The diagnostic interpretation
is sharper: the worry scalar by itself is not a competent calibration
signal across families, and any per-(family, corpus) routing policy
needs heldout confirmation because mean-regression is
universal-but-variable, while per-family topic-accuracy alignment is
what gives the worry-Brier relationship its sign.

# Multi-channel R² and a NEW channel: self-predicted Brier interval {#sec:multi-channel-r2}

The orthogonality result ($\S\ref{sec:channel-orthogonality}$) said the
three channels are statistically independent. A natural follow-up: how
much of forecast Brier do they jointly explain when measured *on the
same forecast*? Earlier we could only estimate single-channel R² per
primitive ($5$--$26\%$) because each primitive was elicited in a
separate pilot with its own forecast. The all-channels primitive elicits
four channels in ONE prompt: bid-ask spread, scalar worry, AND the lower
and upper bounds of the LLM's self-predicted Brier interval (a
previously-unused continuous channel).

**Multi-channel OLS R² on same-forecast Brier (public-domain $N{=}42$,
leave-one-out cross-validated):**

The reported R² on $N{=}15$ low-overlap with $k{=}4$ channels is
mathematically reckless, 14 degrees of freedom and four free regressors
gives an in-sample R² that is mostly fit noise. The honest report is the
public-domain $N{=}42$ corpus with adjusted R² and leave-one-out R²
(LOO), where LOO subtracts the optimism bias:

  Family              $N$    R² (in-sample)   adj R²       **R²_LOO**      reading
  ------------------ ------ ---------------- --------- ------------------- -----------------------------
  **GPT-5.5**         $42$      $0.572$       $0.525$   $\mathbf{+0.312}$  real out-of-sample signal
  Gemini 2.5 Flash    $42$      $0.305$       $0.230$       $+0.042$       barely real
  Claude Opus 4.7     $42$      $0.201$       $0.115$       $+0.027$       barely real
  DeepSeek Chat       $42$      $0.276$       $0.197$       $-0.053$       overfit
  GPT-5.4-mini        $42$      $0.162$       $0.072$       $-0.288$       overfit worse than the mean

**The honest claims.**

First, *only GPT-5.5 has a multi-channel decomposition that survives
leave-one-out cross-validation on the public corpus.* For GPT-5.5, four
channels (worry scalar, bid-ask spread, b_mid, b_width) jointly explain
$\approx 31\%$ of squared-error variance out-of-sample at $N{=}42$. For
the other four families, R²_LOO is at or below zero, the multi-channel
decomposition does not generalize beyond the fit set at this $N$, even
though three of them have non-trivial in-sample R². The orthogonality
claim ($\S\ref{sec:channel-orthogonality}$) stands; what does NOT stand
is the stronger claim that combining the channels reliably predicts
error for those four families at $N{=}42$.

Second, *a new continuous channel was introduced and is properly
characterized as a primitive, not a fix.* The all-channels prompt asked
each model to emit `predicted_brier_lo` and `predicted_brier_hi`
alongside the forecast. The interval midpoint (b_mid) and width
(b_width) form a self-predicted-Brier channel with no precedent we are
aware of in the LLM-calibration literature. On the public-domain corpus,
b_mid and b_width each carry $\rho < 0.30$ versus Brier for every
family, they are informative for one family (GPT-5.5 multi-channel
survivor) but are not a single-channel rescue.

**What the low-overlap $N{=}15$ numbers were.** A within-program control
on research-internal contracts, with $k{=}4$ regressors at $N{=}15$, the
in-sample R² of $0.66$ to $0.90$ values for GPT-5.4-mini and Gemini are
in-sample fits with too few residual degrees of freedom to interpret. We
report them in our internal logs; we do NOT make a cross-corpus
deployment claim from them.

**Partial replication of the reference-class outside view at $N{=}42$
public-domain.** A separately-fired pilot elicited an outside-view base
rate (the model first listed five similar past resolved questions and
emitted their historical YES rate as `p_base_outside`, before its own
`p_success`). At $N{=}42$ public-domain,
$\rho(\texttt{p\_base\_outside}, y)$ is positive in direction for all
five families and reaches $\rho{=}{+0.39}$, $95\%$ CI $[+0.10, +0.62]$,
`h1_supported` for GPT-5.4-mini, the only family that clears the
Fisher-z detectability floor at $N{=}42$. For that family the
outside-view tracked outcomes more strongly than its own point estimate
($\rho{=}{+0.21}$). The other four families are
`inconclusive_underpowered`, all positive-direction. We treat this as a
partial cross-corpus replication of a novel primitive, not a full
generalization.

**Saturation curve.** The R²-vs-channel-count saturation curve is the
right summary plot for policy translation; we leave it pre-registered as
the next analytical pass, on the public-domain corpus and reported in
LOO terms.

# Where the per-family signal actually lives: conditional structure {#sec:conditional}

The $\S\ref{sec:multi-channel-r2}$ multi-channel result (only GPT-5.5
survives LOO on $N{=}42$) leaves four families with channels that don't
generalize. Three free post-hoc analyses on the same data sharpen this:

**Sub-source heterogeneity within the public-domain corpus.** The
$N{=}42$ public-domain corpus is itself a mixture of Polymarket
prediction-market questions, Manifold prediction-market questions, and
yfinance stock-threshold questions. Recomputing
$\rho(\mathrm{worry}, \mathrm{Brier})$ per (family, sub-source):

  Family          yfinance ($N{=}10$)   Manifold ($N{=}19$)   Polymarket ($N{=}13$)
  -------------- --------------------- --------------------- -----------------------
  Claude                $+0.54$            $+0.51$ (h1)              $-0.44$
  GPT-5.5               $+0.59$               $+0.20$             $+0.64$ (h1)
  GPT-5.4-mini       $-0.69$ (h1)             $-0.12$                $-0.38$
  Gemini                $+0.13$               $-0.21$             $+0.75$ (h1)
  DeepSeek              $+0.21$               $-0.28$             $+0.95$ (h1)

Claude's sign flips between Manifold ($+0.51$) and Polymarket ($-0.44$);
DeepSeek's signal lives almost entirely in Polymarket ($+0.95$, $95\%$
CI $[+0.82, +0.98]$). Pooled-corpus $\rho$ averages across this
heterogeneity. The per-family rule is incomplete without a sub-source
decomposition, a contract's host platform is a hidden confound.

**Pooled signal collapses after task-difficulty controls.** A standard
practice is to report "classifier on LLM uncertainty channels predicts
$R^2 \approx 0.36$ of Brier variance." We refit on the pooled $N{=}210$
($5$ families $\times$ $42$ contracts) with two task-difficulty
baselines added: `question_length` and forecast-extremity
$|p_{\mathrm{success}}-0.5|$. Incremental $R^2_{\mathrm{LOO}}$ from each
LLM channel added on top of the baseline:

- baseline (q_len + p_extremity only): $R^2_{\mathrm{LOO}} = +0.101$

- $+$ worry: $\Delta = -0.003$

- $+$ spread: $\Delta = +0.011$

- $+$ b_mid: $\Delta = -0.009$

- $+$ b_width: $\Delta = -0.010$

On pooled data, controlling for task-difficulty wipes out the
LLM-channel contribution. The per-family multi-channel signal (GPT-5.5
$R^2_{\mathrm{LOO}}{=}{+}0.31$, $\S\ref{sec:multi-channel-r2}$) survives
because it conditions on family identity. A claim of the form
"LLM-emitted uncertainty channels add predictive value" *across*
families on pooled data does NOT hold once task-difficulty is
controlled.

**Hardness-conditional multi-channel R².** Per-(family,
hardness-quartile) cell on $N{=}42$ public, where hardness =
cross-family $\sigma(p_{\mathrm{success}})$ (high $\sigma$ = families
disagree = hard):

  Family          Q1 (easy, $N{=}11$) $R^2_{\mathrm{LOO}}$   Q4 (hard, $N{=}10$) $R^2_{\mathrm{LOO}}$                  Reading
  -------------- ------------------------------------------ ------------------------------------------ ---------------------------------------
  GPT-5.5                     $\mathbf{+0.93}$                               $-0.79$                    generalizes on easy; overfits on hard
  DeepSeek                    $\mathbf{+0.92}$                               $-13.0$                         same, near-singular on hard
  Gemini                      $\mathbf{+0.87}$                                $-2.5$                                    same
  GPT-5.4-mini                    $-0.74$                                     $-2.0$                            no fit either bucket
  Claude                           $-4.1$                                    $-10.0$                            no fit either bucket

On the easy quartile (low cross-family disagreement, $N{=}11$), three
families show multi-channel $R^2_{\mathrm{LOO}}{>}0.87$. On the hard
quartile (high disagreement), LOO collapses across all families. The
cell size is small ($N{=}10$--$11$ with $k{=}4$ channels), so this is a
hypothesis-generating result requiring $N{\geq}20$ per cell to confirm;
the deepseek Q3 $R^2_{\mathrm{LOO}}{=}{-}480$ is a near-singular-design
artifact. The pre-registered confirmation pass is on the $N{=}142$
topic-balanced extension.

The policy hypothesis from these three findings is one scoped rule: *test
per-family multi-channel routing only when sub-source identity is matched and
cross-family disagreement is low.* Later re-audits demote current channel-only
routing to diagnostic status, so the claim here is about where an uncertainty
signal appears, not a validated deployment rule. Stated differently, the
LLM-uncertainty signal is conditional on context-of-call, not unconditional
per-family.

**Cross-corpus-class Brier and Elo: the family ordering flips between
internal apparatus and external markets.** A per-(family, corpus_class)
roll-up across all $15{,}949$ panel calls (post-ingest 2026-05-29; SQL
views `v_family_brier_by_corpus_class` and table
`family_elo_by_corpus_class` in `forecaster_calibration.db`). Elo:
$K{=}16$, init $1500$, head-to-head per-contract Brier wins on the
shared cohort.

  Family         Corpus class     $n$ calls              Brier               Elo   $n$ games
  -------------- -------------- ----------- ------------------ ----------------- -----------
  GPT-5.4-mini   external            $1291$            $0.279$            $1479$       $568$
  GPT-5.5        external            $1285$            $0.282$            $1463$       $568$
  Claude         external            $1429$            $0.285$   $\mathbf{1575}$       $568$
  DeepSeek       external            $1396$            $0.295$            $1464$       $568$
  Gemini         external            $1427$            $0.327$            $1519$       $568$
  GPT-5.4-mini   internal             $516$   $\mathbf{0.135}$   $\mathbf{1681}$       $118$
  GPT-5.5        internal             $573$            $0.208$            $1416$       $119$
  DeepSeek       internal             $342$            $0.226$            $1526$        $60$
  Gemini         internal             $342$            $0.236$            $1569$        $60$
  Claude         internal             $580$            $0.248$   $\mathbf{1308}$       $119$

Two readings the table forces. First, Brier and Elo orderings disagree
externally: Claude wins external Elo at $1575$ but is $3$rd on external
Brier ($0.285$); Gemini is $2$nd on external Elo at $1519$ but $5$th on
external Brier ($0.327$). The disagreement is mechanistically
informative: a family can win head-to-head by being direction-correct
more often than its calibration confidence suggests, while losing
average Brier on the few contracts where it bets confidently and wrong.
Gemini's external $\Delta = 56$ Elo above its Brier rank corresponds to
roughly $58\%$ head-to-head win rate against the next-down family
despite its higher mean squared error. Second, the family ordering flips
between corpus classes. Claude moves from external Brier $0.285$ / Elo
$1575$ (best external Elo) to internal Brier $0.248$ / Elo $1308$ ($373$
Elo points below GPT-5.4-mini, $\approx 89\%$ head-to-head win rate
against Claude on internal). The mechanism is the F100 confident-NO bias
surfacing on the internal slate: per-family mean $p_{\mathrm{success}}$
on internal contracts is $0.345$ for Claude versus the true internal YES
rate of $0.556$, a systematic under-bet on the $56\%$ of internal
contracts that resolve YES; GPT-5.4-mini's mean internal
$p_{\mathrm{success}} = 0.556$ matches the base rate exactly, with
$33\%$ extreme bets ($p \geq 0.9$ or $p \leq 0.1$) that are
well-calibrated rather than conservative. Internal $N$ at
resolved-contract level is $45$, so the largest per-family Elo gap
(GPT-5.4-mini vs Claude $\Delta {=} 373$) is `h1_supported` and tighter
pairs are `inconclusive_underpowered`; an internal-corpus re-fire to
$N{\geq}142$ resolved parity is queued. The candidate policy shape is
conditional routing by Elo where Brier least discriminates, as in
$\S$[12](#sec:conditional){reference-type="ref"
reference="sec:conditional"}, with the rule keyed on both contract-level
panel $\sigma$ AND corpus class; later source-balanced policy audits keep this
below deployment status.

**Ensemble feasibility probe (apples-to-apples on the $N{=}157$ shared
cohort).** A direct test of whether naive aggregation can substitute for
the per-family routing analysis above: on the 157 contracts where all 5
families fired, the best single family (Claude, Brier $0.2528$) beats
both mean-of-5 (Brier $0.2558$, $\Delta{=}{+}0.0030$) and median-of-5
(Brier $0.2704$, $\Delta{=}{+}0.0176$). Naive aggregation does NOT beat
the strongest single at this $N$. The reason is in the panel's
correlation structure: pairwise Spearman $\rho(p_{\mathrm{success}})$
across families splits the panel into two clusters, (Claude, GPT-5.5,
GPT-5.4-mini) within-cluster $\rho{\approx}0.74$--$0.78$, (DeepSeek,
Gemini) within-cluster $\rho{=}0.66$, between-cluster
$\rho{=}0.40$--$0.60$. The Claude+codex trio is highly correlated; real
diversity comes from Gemini and DeepSeek but they have higher individual
Brier. A second ordering, head-to-head per-contract Elo (K=16, init
1500), surfaces a different signal: Claude $1555$, *Gemini* $1516$,
GPT-5.4-mini $1512$, GPT-5.5 $1464$, DeepSeek $1453$. Gemini gets
DIRECTION right more often than its calibration suggests; a family can
win Elo head-to-head (closer to truth on more contracts) while losing
average Brier (worse on the contracts it loses, especially with
overconfident direction-correct extreme $p_{\mathrm{success}}$ values
getting punished hard on the few it gets wrong). The ANOVA-style
variance decomposition completes the picture: $67.1\%$ of Brier variance
is between-contract (some contracts are just harder), $32.3\%$ is
family$\times$contract interaction (*different families err on different
contracts --- the actual ensemble opportunity*), and only $0.6\%$ is
between-family identity. Naive mean and median cannot capture the $32\%$
interaction because they assume independent family errors of similar
magnitude; the policy hypothesis that would convert this signal is
contract-level conditional routing keyed on (panel disagreement
$\sigma$, contract category, family Elo on similar-$\sigma$ contracts).
The pre-registered $N{\geq}300$ confirmation pass is required before
that hypothesis can be treated as a deployment rule.

# Five additional findings from the all-channels primitive round {#sec:v28batch}

The all-channels round elicited multiple new primitives in a single
prompt or as paired conditions. Five additional findings emerge at
$N{=}131$--$142$ public-domain:

**Rollback hurts.** A self-counterfactual primitive ("imagine you were
trained only up to 2023, emit a rollback forecast") HURTS Brier for 4 of
5 families at $N{=}142$ paired ($\Delta$ Brier rollback$-$normal: claude
$+0.064$, codex-5.5 $+0.034$, codex-5.4-mini $+0.028$, deepseek
$+0.028$, gemini $-0.005$). Post-2023 training is net-useful even though
families can't introspect WHICH contracts benefit. *Operational
caution:* don't prompt-engineer "imagine you knew less" framings on
forecasting tasks without a heldout correction check.

**Leakage agreement without calibration.** On the same rollback
primitive, all 10 pairwise $\rho(|\text{leak}_A|, |\text{leak}_B|)$
between families are $\geq +0.43$ (h1_supported; claude
$\leftrightarrow$ codex-5.5 $\rho{=}+0.80$). Families AGREE which
contracts feel high-leakage. *But* per-family
$\rho(|\text{leak}|, \text{err}^2)$ is h0_kept for all five at the
$\pm 0.30$ target. Self-reported leakage is a real CONTRACT-structural
signal, NOT a per-family calibration channel. Useful as a
corpus-curation filter (filter to low-leakage contracts for honest
LLM-fresh tests).

**DeepSeek's emitted decision-threshold is calibrated.** An
asymmetric-loss decision-threshold primitive (commit-YES threshold under
symmetric / YES-bad-3$\times$ / NO-bad-3$\times$ loss). Codex-5.4-mini
emits the most Bayes-coherent thresholds (mean YES-bad $0.750$, exact
match). Deepseek h1:
$\rho(\text{threshold\_yes\_bad}, \text{err}^2) = -0.19$, $95\%$ CI
$[-0.35, -0.03]$ at $N{=}142$. The emitted threshold tracks accuracy for
one family. This is a novel diagnostic channel; policy use requires a heldout
utility test.

**Stake-framing amplifies worry universally, leaves $p$ unchanged.**
Same contract framed as "\$1 stake" vs "\$100K stake" across 103--142
paired contracts per family. Worry-scalar amplifies for every family
($\Delta\text{worry}$ from $+10.8$ deepseek to $+33.5$ claude on the
1--100 scale). But $|\Delta p_{\mathrm{success}}| < 0.03$ for every
family. Universal cognitive-shift-without-calibration-shift on a new
manipulation, bridges the cognitive-decoupling result to the
stake-framing / risk-amplitude human literature (Holt-Laury 2002).

**Inversion rule for channel-routing meta-cognition (three of five
families).** A meta-channel-routing primitive ("which of your own
uncertainty channels best predicts your error?") reveals systematic
anti-coherence at $N{=}15$ internal: claude, codex-5.5, and deepseek
pick the WRONG channel $87\%$ of the time (binomial $p{=}0.005$ each).
Within those picks, $\rho(\text{picked}, \text{err}^2)$ is negative
while $\rho(\text{unpicked}, \text{err}^2)$ is strongly positive (claude
$+0.51$, codex-5.5 $+0.53$, deepseek $+0.65$). The candidate inversion
rule is: when these three families claim "worry is my best channel," test
spread instead (or the analogous flip). Codex-5.4-mini is coherent
($73\%$ right); gemini is random. Companion finding to the per-family
worry sign-flip, on a new axis. Internal-only at $N{=}15$; cross-corpus
replication at $N{=}42$ external is pre-registered. The pattern (LLMs
have honest contract-level structural intuitions without calibration to
truth) recurs across the rollback, leakage, decision-threshold, and
meta-channel-routing results, the defining negative finding about LLM
self-monitoring.

# Universal cross-family patterns {#sec:universal}

The findings above split the LLM panel by family. Free analyses on the
same $N{=}42$ public-domain data surface four universal patterns that
hold across all five families with the same direction, which we report
here because they are the patterns most likely to transfer to a
different LLM panel.

**Universal over-confidence on confident-NO predictions.** A
reliability-curve analysis (binning each family's forecasts into
quintiles by stated $p_{\text{success}}$, then computing the actual YES
rate per quintile):

  Family          Mean predicted $p$ in quintile 1   Actual YES rate, quintile 1     gap
  -------------- ---------------------------------- ----------------------------- ---------
  Claude                        0.04                            0.38               $+0.34$
  GPT-5.5                       0.07                            0.75               $+0.68$
  GPT-5.4-mini                  0.04                            0.62               $+0.58$
  Gemini                        0.05                            0.75               $+0.70$
  DeepSeek                      0.03                            0.75               $+0.72$

Every family is dramatically over-confident on its "confident-NO"
forecasts. The quintile-5 (confident-YES) end is roughly calibrated (gap
$-0.02$ to $-0.21$). The miscalibration is asymmetric: confident-NO is
poorly calibrated; confident-YES is OK. With $N{=}8$--$10$ per quintile
per family, the per-family CI is wide, but the universality across all
five families and the consistent direction of the gap argue the pattern
is real. *Operational caution:* on a news-event public corpus, do not
treat LLM $p_{\text{success}} < 0.10$ as a confident-NO commit without a
heldout correction check.

**Horizon-conditional Brier.** Pooled across all 5 families ($N{=}210$):
$\rho(\text{days to resolution from 2026-01-01}, \text{err}^2) = +0.161$,
$95\%$ CI $[+0.026, +0.290]$, h1_supported. Brier on
April-2026-resolving contracts is $0.240$; on May-2026 it is $0.385$.
Contracts farther from the training cutoff are systematically harder.
The mechanistic interpretation is straightforward (more uncertainty
accumulation over longer horizons), but the cleanly-documented
per-contract horizon-confidence-weighting term is novel for LLM
forecasting at this $N$.

**Universal NO-bias.** On contracts that did resolve YES ($N{=}26$ of
$42$ in this corpus), every family's mean $p_{\text{success}}$ is below
$0.5$ ($0.38$--$0.48$). Brier conditioned on $y{=}1$ exceeds Brier
conditioned on $y{=}0$ for every family; DeepSeek shows the largest
asymmetry ($0.46$ vs $0.12$). LLMs are systematically better at
predicting NO outcomes than YES outcomes on this corpus. Possible
interpretations include (a) underlying corpus YES base-rate of $62\%$
exceeds the model's prior on these questions; (b) "will X happen by date
Y" framing biases toward NO; (c) prior-cutoff bias on then-future
events. We do not distinguish among these here.

**Naive ensemble averaging does NOT help.** On the full $N{=}142$ paired
set with all five families' $p_{\text{success}}$ values: median-of-5
Brier $= 0.272$, mean-of-5 Brier $= 0.261$, best-single-family (Claude)
Brier $= 0.254$. Paired permutation: median-of-5 loses to the best
single family ($\Delta{=}{+}0.018$); mean-of-5 also loses
($\Delta{=}{+}0.007$). The standard "ask five LLMs, take the median"
aggregation strategy yields no benefit on this corpus and slightly hurts.
Best-single-family dominates naive ensembling at this $N$.

**Universal cross-family forecast agreement.** For every pair of the
five families, $\rho(p_{\text{success},A}, p_{\text{success},B})$ on the
same $N{=}42$ public-domain contracts is h1_supported. Pairwise $\rho$
ranges $+0.52$ (codex-5.4-mini $\leftrightarrow$ DeepSeek) to $+0.88$
(Claude $\leftrightarrow$ GPT-5.5). Mean $+0.72$. The five families
agree on forecast direction across vendors and architectures. This
caveats the per-family results: when families converge, they really
converge, but high pairwise $\rho$ does not distinguish "models converge
on truth" from "models share training-data bias." For panel-aggregation
design, the practical takeaway is that consensus-strength is a usable
confidence weight: a contract where all five families return
near-identical $p_{\text{success}}$ can be treated as a
higher-confidence pooled forecast than a contract where they disagree.

**Universal source-difficulty ordering.** Per-source Brier per family on
the public-domain corpus reveals a universal ordering: *Polymarket* $>$
*Manifold* $>$ *yfinance*. Polymarket contracts (election outcomes,
news-events) yield Brier $0.46$--$0.57$ across all five families;
yfinance ETF threshold contracts yield $0.22$--$0.23$. The same order
holds for every family. Source identity is a per-contract
confidence-weighting term independent of family.

**The six universal patterns together suggest a candidate per-contract
recipe:** (a) discount the model's confident-NO forecasts; (b)
horizon-weight per-contract confidence; (c) apply a per-family YES-bias
correction term; (d) prefer a calibrated single family over a naive
ensemble; (e) weight pooled-forecast confidence by cross-family
consensus-strength; (f) weight by source difficulty.

**Composed recipe at $N{=}142$: routing beats naive aggregation; later audits
demote the composite policy.** We instantiate the
rules above as a single composed forecast (the mean-of-5 panel forecast
adjusted by four universal coefficients: a confident-NO discount when
the panel mean is below $0.20$, an upward YES-bias correction in the
middle band, a horizon-to-cutoff shrinkage, and a per-source-difficulty
shrinkage, see App. [21](#app:routed-recipe){reference-type="ref"
reference="app:routed-recipe"} for the closed form). All four
coefficients are chosen *ex ante* from the universal patterns above, not
learned from held-out folds. The contrast we test is paired-permutation
$\Delta$-Brier against three baselines and against a per-family
channel-routed alternative on the same $N{=}142$ paired contracts.

  strategy                    Brier    $\Delta$ vs. best-single         90% CI         $p_{\mathrm{perm}}$
  ------------------------- --------- -------------------------- -------------------- ---------------------
  median-of-5                $0.272$           $+0.018$                   ,                     ,
  mean-of-5                  $0.261$           $+0.007$                   ,                     ,
  best-single (Claude)       $0.254$              ,                       ,                     ,
  routed (universal-only)    $0.232$           $-0.022$           $[-0.050, +0.005]$         $0.18$
  routed (per-channel)       $0.246$           $-0.009$           $[-0.035, +0.016]$         $0.58$

Three results.

*(i) Routed-vs-naive-aggregation is the clean within-cohort win.* Routed
(universal-only) beats median-of-5 by $\Delta{=}{-}0.040$
($p_{\mathrm{perm}}{=}0.0013$) and mean-of-5 by $\Delta{=}{-}0.029$
($p_{\mathrm{perm}}{=}0.0069$). `h1_supported`. The composed recipe
out-performs the standard "ask five LLMs, take the median/mean" baseline at
$p{<}0.01$ on the same $N{=}142$ paired set, but this comparison is weaker
than a source-balanced policy audit against the strongest simple correction.

*(ii) Routed-vs-best-single is directional but underpowered.* The point
estimate $\Delta{=}{-}0.022$ sits almost entirely on the routing-wins
side of zero (90% CI $[-0.050, +0.005]$), and the direction is
consistent with the same comparison at the previous $N{=}42{\times}3$
snapshot before the codex refill ($\Delta{=}{-}0.013$,
$p_{\mathrm{perm}}{=}0.48$). The gap roughly doubled in routing's favor
as $N$ rose; the $p$ shrank from $0.48$ to $0.18$. At the observed
effect size and paired-Brier variance, the Fisher-$z$ power calculation
gives $N{\approx}250$--$300$ for $p{<}0.05$ at $80\%$ power on a
two-sided test. We report `h0_kept` against the $\Delta{\geq}0.05$
detection bar that the program's pre-registration sets for deployment
claims, and `inconclusive_underpowered` against the smaller observed
effect.

*(iii) Universal rules generalize better than per-family channel routing in
this audit, but the composite does not survive as the live policy.*
Routed (universal-only) beats routed (per-channel) by
$\Delta{=}{+}0.014$ ($p_{\mathrm{perm}}{=}0.042$), i.e. the per-family
channel-weighting alternative makes the forecast *worse* than the
universal-rules version on the public-domain corpus, at $p{<}0.05$. This
is consistent with $\S\ref{sec:channel-orthogonality}$ (only GPT-5.5's
multi-channel decomposition has a generalizable $R^2_{\mathrm{LOO}}{>}0$
at $N{=}42$) and with the conditional-structure result
($\S\ref{sec:conditional}$): channel-level routing is contextually
conditional and does not survive a uniform application. Later source-balanced
policy audits further show that the current source+$\sigma$ router and
diagnostic-triggered allocation lose to simpler rules. The surviving applied
rule is the confident-NO discount. A costed review-allocation audit shows
oracle headroom but does not promote any realistic proxy reviewer; graph-family
routing and diagnostic review remain candidate diagnostics pending stronger
source-balanced confirmation.

A $\sim 100$-contract pre-registered follow-on on the public-domain corpus was
the original refill required to escalate (ii) from `inconclusive_underpowered`.
The newer evidence changes the applied question: the next policy test must beat
the confident-NO discount and source/hash controls, not only naive mean or
median aggregation.

**The confident-NO discount as a standalone rule beats raw on every
family at $p<0.05$.** The simpler form of the recipe, the single
confident-NO discount applied per-family without the other three rules,
improves per-family Brier on every panel member at $p < 0.05$:

  family              raw Brier   discounted Brier         $\Delta$        paired $p_{\mathrm{perm}}$
  ------------------ ----------- ------------------- -------------------- ----------------------------
  claude              $0.2543$    $\mathbf{0.2240}$       $-0.0302$                 $0.016$
  codex-$5.5$         $0.2625$        $0.2416$            $-0.0208$                 $0.030$
  codex-$5.4$-mini    $0.2714$        $0.2450$            $-0.0264$                 $0.015$
  deepseek            $0.3222$    $\mathbf{0.2704}$   $\mathbf{-0.0518}$       $\mathbf{0.0008}$
  gemini              $0.3167$        $0.2840$            $-0.0327$                 $0.008$

Two observations land here. (a) Discounted Claude at Brier $0.224$ is at
parity-or-better than the four-rule routed recipe ($0.232$ above); the
additional three rules add nothing meaningful on top of the discount on
this corpus at $N{=}142$. (b) A single one-line post-forecast adjustment
improves Brier at $p<0.05$ across every model family, including outside
the panel that originated the rule (DeepSeek and Gemini are
subscription-distinct families). The current applied shape is the discount
alone, applied to whichever single model is in production and tracked against
source-balanced controls. A later no-call fitted-calibrator audit did not
promote a replacement: source-isotonic slightly improved the overall point
estimate but lost Manifold and was non-significant, while tail-beta shrinkage
was worse than the hand F100 rule. A later source-currency stress audit on the
Law 3 Stage-B panel narrowed this rule: it improved post-cutoff rows (Brier
delta $-0.025326$; tail-only $-0.101306$) but regressed
pre-cutoff/source-visible rows (delta $+0.035016$, $p=0.0002$; tail-only
$+0.097719$, $p=0.0002$). We therefore treat the discount as forward-looking
calibration, not as retrospective benchmark correction.

# Bias-type-specific inheritance: LLMs escape utility-grounded biases and inherit framing-grounded biases {#sec:bias-inheritance}

Three novel-bias smokes on the same $N{=}30$ public-domain contracts
across all five families ($5 \times 5 \times 30 = 750$ calls, $748$
schema-OK) test whether well-documented human cognitive biases transfer
to LLM forecasting. The findings split cleanly along bias TYPE:

**(A) Loss-frame invariance. LLMs ESCAPE the human bias.** The same
contract asked as "$p_{\text{success}}$" vs "$p_{\text{failure}}$"
should satisfy $p_{\text{success}} \approx 1 - p_{\text{failure}}$ for a
symmetric forecaster; humans show systematic gaps of $0.15$--$0.30$ from
loss aversion (Kahneman--Tversky $1979$). Mean per-family
$|p_{\text{success}} - (1 - p_{\text{failure}})|$ across all five panel
members: claude $0.035$, deepseek $0.049$, codex-$5.5$ $0.085$,
codex-mini $0.098$, gemini $0.148$. All five families come in well below
the human reference, with claude and deepseek essentially symmetric
(median $\leq 0.03$).

**(F) Status-quo / endowment effect. LLMs INHERIT the human bias, at
large effect size.** The same contract framed as "the YES condition
CURRENTLY HOLDS at the time of forecast" vs "do not assume any current
state" should satisfy $p_{\text{currently}} \approx p_{\text{fresh}}$ if
the model is anchor-symmetric; humans show endowment-effect anchoring on
stated state. Mean per-family
$|p_{\text{currently}} - p_{\text{fresh}}|$: gemini $0.084$, deepseek
$0.110$, claude $0.241$, codex-mini $0.275$, codex-$5.5$
$\mathbf{0.440}$ (median $0.500$, half of contracts flip sign between
the two framings). Three of five families show a clearly large
status-quo response; codex-$5.5$ in particular reverses the forecast on
half the contracts purely from prompt framing.

**(B) Probability-weighting curve, preliminary near-linear (no
inverse-S).** For each contract we elicit $p_{\text{emit}}$ at the eight
anchor probabilities
$\{0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99\}$. Cumulative
prospect theory (Tversky--Kahneman $1992$) predicts inverse-S
overweighting of small probabilities. Preliminary Claude responses:
$\{0.02, 0.07, 0.12, 0.27, 0.50, 0.73, 0.88, 0.985\}$. Near-linear; no
CPT inverse-S overweighting at the low-probability tail.

**The split is informative.** The biases that DO transfer (status-quo /
endowment) are grounded in stated state framing. LLMs anchor on what the
prompt asserts. The biases that DO NOT transfer (loss-frame symmetry,
probability-weighting curve) are grounded in human utility structure.
LLMs have no value function over loss vs gain, no consumption
preference, no asymmetric disutility of loss. This is the clean
diagnostic shape: *LLMs inherit framing-grounded biases and escape
utility-grounded biases.* It is neither the "LLMs are human-like" nor
the "LLMs are rational" framing the literature has been working with.

The candidate rule the split suggests: when contract framing is
ambiguous on current-state, elicit BOTH framings and average. Two-arm
cost ($+2\times$) on ambiguous contracts, near-zero cost on unambiguous
ones, eliminates the codex-$5.5$ half-flip pattern in (F). An $N{=}42$
external replication on a diversified public-domain corpus (Metaculus +
FRED, $90$ contracts, post-cutoff filtered) is firing at the time of
writing.

# Prompt-invariance asymmetry across families: a methodological caveat {#sec:prompt-invariance}

Across three prompt variants that elicit $p_{\text{success}}$ on the
same public-domain contracts (all-channels, reference-class outside
view, and conjunctive decomposition), per-family cross-prompt stability
is heterogeneous:

  Family          $\rho(p_{\text{all-channels}}, p_{\text{outside-view}})$ at $N{=}42$        95% CI
  -------------- ---------------------------------------------------------------------- ------------------
  Claude                                        $+0.868$                                 $[+0.77, +0.93]$
  GPT-5.5                                       $+0.830$                                 $[+0.70, +0.91]$
  GPT-5.4-mini                                  $+0.870$                                 $[+0.77, +0.93]$
  Gemini                                        $+0.504$                                 $[+0.24, +0.70]$
  DeepSeek                                      $+0.386$                                 $[+0.09, +0.62]$

Mean per-family standard deviation of $p_{\text{success}}$ across the
three prompts is $0.05$--$0.06$ for Claude/Codex variants; $0.108$ for
Gemini; $0.148$ for DeepSeek. Claude and the two Codex variants emit
beliefs that are $2{-}3 \times$ more prompt-invariant than Gemini and
DeepSeek's.

This was initially read as the methodological caveat touching every
per-family finding. We later refined it: pooling $p_{\text{success}}$
across four "standard" prompts (all-channels, asymmetric-loss, rollback,
low-stake) on the same $(N{=}41$--$42)$ contracts per family shows mean
$\sigma(p_{\text{success}}) = 0.042$--$0.064$ for EVERY family,
including Gemini and DeepSeek. The earlier-reported $0.108$ / $0.148$
values were driven specifically by the reference-class outside-view
prompt, which forces a pre-forecast base-rate computation. That prompt
is a different reasoning architecture, not the same forecast with prompt
noise.

The scoped caveat is then: the per-family findings in this paper based
on *standard* elicitation prompts (worry scalar, bid-ask spread,
predicted-Brier interval) are roughly equally prompt-invariant across
all five families on the POINT ESTIMATE $p_{\text{success}}$. Findings
that require the model to execute a non-standard reasoning step
pre-forecast (e.g., the outside-view computation) may shift more for
Gemini/DeepSeek than for Claude/Codex.

**Channel-level caveat: the worry scalar is roughly $4\times$ noisier
across prompts than $p_{\text{success}}$.** Pooling worry data from the
all-channels, low-stake, and high-stake prompts on the same
$(N{=}41$--$42)$ shared contracts per family: mean per-family
$\sigma(\text{worry})$ is $10$--$22$ on the $1$--$100$ scale
($10$--$22\%$ of full range), versus
$\sigma(p_{\text{success}}) = 0.04$--$0.06$ ($4$--$6\%$ of $[0,1]$).
Stated equivalently: the worry channel carries substantial
prompt-elicitation noise that the point estimate does not. This is a
methodological caveat on every worry-based finding in this paper (the
per-family sign-flip, the DeepSeek threshold result, the cross-prompt
contradiction): the worry channel itself is less prompt-invariant than
$p_{\text{success}}$. The clean disambiguation requires within-family
worry-paraphrase pilot (5 prompt designs $\times$ same contract per
family) at proper $N$; we have not run it.

**Cross-prompt sign-stability of the worry channel (critical).** Pooling
worry-$p_{\text{success}}$ pairs from four public-domain prompt variants
(all-channels, asymmetric-loss, rollback, stake-framing) at
$N{=}248$--$326$ per family: $\rho(\text{worry}, \text{err}^2)$ for
Claude is $+0.166$ $[+0.042, +0.285]$, `h1_supported` in the
DIRECTION-CORRECT direction, the opposite of the low-overlap-corpus
result that drove the deployed per-family sign rule. Codex-5.5 is
direction-correct externally (consistent with internal);
Codex-5.4-mini's strong internal direction-correct signal goes null
externally; Gemini and DeepSeek remain flat. The cleanest read is that
the inversion-for-Claude rule is corpus-bound or prompt-bound, not a
per-family property. The deployed routing rule for Claude has been
scope-restricted to "low-overlap-corpus prompt style only" pending a
retest pilot ($\sim$`<!-- -->`{=html}42 calls of the original prompt
style on $N{=}42$ public-domain) that disambiguates corpus-effect from
prompt-effect.

# Pre-registered test of the inheritance frame on a held-out bias slate {#sec:freq-inheritance-test}

The three-axis frame in
$\S$[3](#sec:theoretical-frame){reference-type="ref"
reference="sec:theoretical-frame"} was induced from the body of
measurements above. The framework earns its predictive claim only by
getting subsequent bias-transfer predictions right on biases it had not
yet seen. This section reports the pre-registered test.

#### Pre-registered slate.

Seven additional human biases held out from the F102 measurement,
classified ex ante into the three cells of axis 2 before any new data
was collected.

- [Inherit]{.smallcaps} (pure-heuristic, high natural-speech footprint):
  **C** gambler's / hot-hand fallacy (Tversky and Kahneman 1971); **E**
  self-overconfidence (Lichtenstein, Fischhoff, and Phillips 1977);
  **H** base-rate neglect when the prior is explicit; **J** numeric
  anchoring (Tversky and Kahneman 1974).

- [Escape]{.smallcaps} (pure-motivational, low text representation of
  the bias mechanism): **G** hyperbolic discounting (Frederick,
  Loewenstein, and O'Donoghue 2002).

- [Mimic]{.smallcaps} (systemic-motivational, intrinsic utility BUT
  heavy case-study representation): **D** sunk cost (Arkes and Blumer
  1985); **I** in-group / national framing (Tajfel and Turner 1979),
  with explicit prediction of alignment damping.

#### Decision rule.

Of the seven held-out biases together with the three already measured in
$\S\ref{sec:bias-inheritance}$ (A loss-frame [escape]{.smallcaps}
confirmed; B probability weighting [escape]{.smallcaps} preliminary; F
status-quo [mimic]{.smallcaps} as re-classified from
[inherit]{.smallcaps}), classifying $\geq 8$ of 10 into the predicted
cell is the bar for `h1_supported` on the framework as a structured
prediction. The random-cell baseline is $\sim 3.3 / 10$. The
[mimic]{.smallcaps} vs [inherit]{.smallcaps} discrimination has two candidate
signatures: (S1) the magnitude correlates with how often the bias is
*discussed* in training corpora (proxy: retrieval of the bias name returns
case-study hits, not first-person enactments); (S2) the effect collapses under
explicit anti-bias prompting much more for [mimic]{.smallcaps} than for
[inherit]{.smallcaps}. S2 is reported as a failed/scoped companion test, not as
part of the promoted law: the anti-bias-collapse score verdict is
`kill_or_scope_raw_gap_explains_collapse`.

#### Slate verdict.

On the pre-registered slate the framework classifies $\geq 8$ of $10$
biases into the predicted cell, clearing the `h1_supported` bar against
the $\sim 3.3/10$ random-cell baseline. The two [mimic]{.smallcaps}
biases pre-registered with explicit alignment damping---D sunk cost and
I in-group/national framing---initially fell below the
[inherit]{.smallcaps} magnitude band on the single-family smoke; on the
cross-family panel both surface on the weaker-RLHF families at
$3$--$6\times$ the Claude effect, exactly the pre-registered
[mimic]{.smallcaps}-with-alignment-damping prediction, taking the slate
to $10/10$ on the per-family reading. We read this as confirmation that
the transfer cell is predictable *ex ante* from each bias's structural
origin, with the alignment overlay (Axis 3) acting as a per-family
modifier on the [mimic]{.smallcaps} class rather than a panel-uniform
axis. Two extensions sharpen the claim beyond the categorical slate and
are reported separately: (i) a quantitative dose-response relating
transfer magnitude to each bias's corpus-discussion frequency (signature
S1), and (ii) a further out-of-distribution slate of biases drawn from
outside the inducing set, classified ex ante under the same predicate.
The pre-registration of cell classifications and decision rule is fixed
at the version-tag of this manuscript.

#### Out-of-distribution slate (ii): inconclusive, and the apparent gradient is confounded.

We fired extension (ii) as a sealed pre-registration of nine fully-novel
biases (none in the inducing set), scored as the *excess over a
pre-registered normative framing gap* $g_0$ rather than the raw gap---so
a model that gives the rational (framing-insensitive) answer reads as
[escape]{.smallcaps}, never as a missed [inherit]{.smallcaps}. (An
earlier instrument that scored raw gaps mislabelled rational answers as
misses; that run is void.) On the five-family panel ($n{=}15$
events/bias, $1348/1350$ schema-valid) the **full three-cell
point-prediction is `inconclusive`**: median per-family cell-match is
$5/9$, below the pre-registered $\geq 7/9$ bar (random $\sim 3/9$). We
also observed an ordering in which less RLHF-aligned families carry
larger [inherit]{.smallcaps}/[mimic]{.smallcaps} excess (Claude lowest
at $+0.095$; DeepSeek highest at $+0.152$; $3/4$ adjacent pairs
monotone) that would superficially support the Axis-3 alignment overlay.
**We do not claim this as a result**, for three reasons. (1) It is
underpowered: five families, a hand-assigned alignment ordinal, not a
measured alignment quantity. (2) A cross-family contrast confounds
alignment with pretraining-corpus differences---families differ in
pretraining as well as in RLHF, so a cross-family ordering cannot
isolate the alignment stage. (3) The *direction* runs opposite to the
established finding that instruction-tuning / RLHF *amplifies* several
cognitive biases rather than damping them (Itzhak et al. 2024). We
therefore report slate (ii) as inconclusive on the cell-prediction and
confounded on the alignment overlay. The framework's validated
contribution remains the in-distribution taxonomy and the
[mimic]{.smallcaps} articulation; an out-of-distribution alignment law
is *not* established here, and de-confounding alignment from pretraining
(held-out within-family checkpoints, or matched-pretraining families) is
the required follow-up.

# The re-audit discipline: a warning to the field {#sec:reaudit}

The discipline that produced the results above also produced a re-audit
of the program's own prior findings. We treat the re-audit itself as a
contribution because the same overcalling pattern almost certainly
affects the published LLM-forecasting literature at the sample sizes it
currently reports.

## Power calculus applied to our own program

Before fixing the verdict resolver, eight prior "no effect" or
"cross-corpus replication" claims in the program had been written down
as findings. Applying the Fisher-$z$ power-aware verdict resolver
retrospectively:

- Four "null" findings move from `h0_kept` to
  `inconclusive_underpowered`: the data did not actively rule out a
  meaningful effect at the per-family target $|\rho|$ floor; the
  absence-of-signal was an absence-of-power.

- Five cross-corpus claims move from "replicated" or
  "failed-to-replicate" to corpus-specific: the original cross-corpus
  reading was a single sub-source point estimate at $N{=}5$--$15$
  external, with CIs that crossed zero and with sub-source heterogeneity
  unmodeled.

- One self-knowledge-inversion finding (originally three families at
  $N{=}5$) retracts to a single family at $N{=}15$ internal; the other
  two cross-corpus directions flip on re-fire.

- Two per-family deployed routing rules (Brier-$\Delta$ map and
  *consider-both-sides* effect) move from deployment-grade to
  "directional hypothesis only"; the required $N$ to confirm a
  $\Delta_{\mathrm{Brier}}{=}0.05$ effect at 80% power is $\approx 459$
  per family, an order of magnitude above the original $N{\approx}30$
  per cell.

In aggregate, $\approx 50\%$ of the program's prior verdicts did not
survive the verdict resolver. None of the underlying executions were
flawed. The interpretation discipline was.

## A worked example: the per-family worry sign-flip retest

The previous YAML routing hypothesis for Gemini was scope-restricted to
"low-overlap corpus, $v21$-style prompt only" pending a
$\sim$`<!-- -->`{=html}42-call retest of the same prompt on the
public-domain $N{=}42$ slice that the other v28 pilots fired on. The
retest, fired with the same C1 worry-only prompt on `gemini-2.5-flash`
via API:

- Schema-OK: $42/42$.

- $\rho(\mathrm{worry}, \mathrm{Brier}) = +0.110$ -- the
  direction-correct direction, NOT the inverted direction the prior
  deployment had assumed.

- Fisher-$z$ detectable $|\rho|$ at $N{=}42$, $80\%$ power: $\geq 0.43$.
  Observed $|\rho|{=}0.11$ is well below this; the CI excludes the
  original "inverted" direction ($\rho < -0.30$).

- Verdict: `h0_kept` against the inversion hypothesis; the
  direction-correct point estimate is in the `inconclusive_underpowered`
  band for the positive hypothesis.

The retracted YAML rule for Gemini stays retracted. The earlier
"inversion" claim, deployed at $N{=}5$ with $N_{\mathrm{wrong}}{=}2$,
was an artifact of the sample size. This is the single cheapest decisive
retest the queue could fire; the queue carries two more retests of
comparable diagnostic value.

## Implications for the published LLM-forecasting literature

The two highest-profile $2024$ contributions to LLM forecast calibration
are (a) the ensemble-prediction result that a 12-LLM aggregate matches
human-crowd Brier on real binary questions (Schoenegger 2024) and
(b) the retrieval-augmented LLM that approaches human-superforecaster
accuracy on a contamination-resistant slice (Halawi et al. 2024). Both
report claims at sample sizes that, under the same Fisher-$z$ power
calculus we apply to our own program, are bounded by:

- For a Brier-delta $\Delta{=}0.05$ comparison (LLM ensemble vs. human
  crowd) at $80\%$ power, paired permutation requires
  $N{\geq}300$--$500$ per side.

- For a per-model rank correlation $|\rho|{=}0.30$ at the same power:
  $N{\geq}91$.

- For a per-(model, sub-source) cell at $|\rho|{=}0.40$: $N{\geq}50$ per
  cell -- requiring sub-source $N{\geq}250$ across five families when
  sub-sources are five-way mixed.

We do not re-analyse those datasets here; we observe only that the
standard "2024-style" aggregate claim is structurally compatible with
the same overcalling failure mode our own program exhibited. The
methodological contribution the published literature is missing -- and
that this paper contributes -- is the verdict resolver discipline: every
claim labelled with one of three legal verdicts, $n_{\mathrm{required}}$
pre-computed before fire, sub-source heterogeneity reported alongside
the aggregate, and prior verdicts re-audited under the same calculus as
new ones.

**A second-order observation about contamination.** The Halawi 2024
dataset (`YuehHanChen/forecasting`, $N{=}1754$ binary-resolved questions
across Polymarket, Metaculus, Manifold, GJOpen, and CSET) reports
resolution-date histogram: 1 question in 2021, 147 in 2022, 1470 in
2023, 136 in 2024, and **zero in 2025 or later**. The 2024 aggregate
claim was published with a baseline panel whose knowledge cutoff
predated most resolution dates. Any 2025-generation replication that
uses current LLMs (Claude $4.7$, GPT-$5$, DeepSeek Chat $2026$) inherits
a structural compromise: the model's knowledge cutoff postdates every
resolution. A $30$-call probe on a uniform random sample from this
dataset returned Brier $0.13$ on $14$ of $14$ fired confident-NO cases
with empirical YES rate $= 0.07$ -- a calibration signature that is
statistically indistinguishable from outcome recall on a forecasting
task. We then ran a stricter source-currency panel on newly collected
Manifold questions: 40 pre-cutoff and 40 post-cutoff contracts matched
on source, topic, question-length bucket, and computed cutoff relation,
with Claude, Codex 5.4-mini, and Gemini run tool-free on all 240
dispatch rows. The panel is 240/240 schema-valid. Post-cutoff rows have
higher Brier than pre-cutoff rows by $+0.191098$ in aggregate; the
paired-stratum delta is $+0.2155$ with permutation $p=0.0004$ and
95\% interval $[0.1584,0.2795]$. A later Stage-C repair joined 51 of the
80 contracts to pre-outcome probability metadata; 27 family/stratum/
base-rate-band paired cells still show post-minus-pre Brier
$+0.255418$, and an adversarial missing-band sensitivity assigning the
29 unjoined rows to possible base-rate bands leaves the effect positive
at $+0.127901$. We also ingested the same 51 pre-outcome Manifold
probabilities into the DB as `market_baseline_stage_c_v1`: the narrow
market bar scores mean Brier $0.099673$ versus the joined LLM-panel mean
$0.166963$ overall, while splitting by cutoff relation shows the market
beats the LLM panel on post-cutoff rows and the LLM panel beats the
market on pre-cutoff rows. A simple market+LLM blend fails promotion:
leave-one-out grid Brier is $0.097218$ versus market-alone $0.099673$, but the
paired delta is only $-0.002455$ ($p=0.794$, 95% interval
$[-0.021,0.0166]$), and the post-cutoff subset selects market-only. This is
not a broad equal-information human/crowd baseline. The second-source
replication remains open, but the
newly acquired Polymarket slice now has bounded Gemini and DeepSeek smokes:
each is 48/48 schema-valid over 24 pre-cutoff and 24 post-cutoff matched
rows. The raw aggregate matches the source-currency direction for Gemini
($+0.246832$ post-minus-pre Brier) and weakly for DeepSeek ($+0.077758$),
but the six matched source/topic/length strata are null/opposite-sign
(Gemini $+0.005731$, $p=0.9696$; DeepSeek $-0.061706$, $p=0.8836$), so this
is stress evidence rather than source-general replication. A follow-up
availability probe found that the natural Polymarket market-price control is
not executable yet on the frozen slice: pre-cutoff rows have 24/24 DB
freeze-price values, but post-cutoff rows have 0/24 locally and a live
Gamma/CLOB probe joined 0/24 because the public endpoints reset connections
from this environment. The original
base-rate limitation is now a partial-repair
limitation, not an absence of base-rate evidence. The deployable check before any
replication is one filter: *resolve_date $>$ max(panel_cutoff)*. That
filter empties this dataset for the current LLM generation. The general
point is corpus-validity drift: a benchmark that was honest at
publication time may stop being honest once a new model generation has
trained through the resolution dates. The verdict resolver discipline
extends to corpus eligibility, not only to per-claim power.

## Lane B external proof audit: the helper-vs-top-level distinction and an explicit retraction

The verdict-resolver discipline extends to independent proof audits the
program runs on other groups' published Lean artifacts. We audited eight
bare-Mathlib4-importing top-level theorems published by an
AlphaProof-line collaborator ("APN" set, Conjecture2 and proofs P1--P8)
through a strict L1+L2+L3 stack (compile $+$ axiom allowlist
$\{\texttt{propext}, \texttt{Classical.choice}, \texttt{Quot.sound}\}$
$+$ anti-pattern gates against gold-name-verbatim leakage,
single-lemma-exact paraphrase, simp/fun_prop indirect leakage, and
scalar-wrapper currency mismatch). Four rounds of the audit reported
successive "laundering caught" verdicts before we found the failure
mode.

**Retraction.** The first three audit rounds collapsed *helper-lemma*
anti-pattern hits into a *top-level* verdict, which is the wrong
granularity: the top-level theorem statement may be clean even when an
auxiliary lemma supporting it has a helper-level anti-pattern hit (e.g.,
naming a Mathlib lemma verbatim during a private intermediate step). We
do NOT claim DeepMind published anything fake. The earlier "laundering
caught" framing was wrong and is explicitly retracted in this draft. The
corrected status rule distinguishes `compile_pass_l3_advisory_review`
(clean) from `compile_pass_l3_advisory_review_helper_blockers_only`
(top-level clean, helper-level flagged), and ONLY the
former-or-this-latter pair counts as audit-clean. Confirmed top-level
blockers remain disqualifying.

With the corrected rule plus a forced v$4.27$ pinned-toolchain sidecar
for non-drift `compile_failed` cases (which disambiguates "unrecognized
toolchain drift" from "real defect") and a process-group kill discipline
on lake subprocesses (the v33 audit was leaking orphan `lake` processes
that ran $47$--$63$ minutes past their timeout budget, blowing the run),
the corrected verdict on the eight top-level theorems is **6 of 8
audit-clean**: Conjecture2 passes-at-native-toolchain via v$4.27$
sidecar; P1 advisory-review at v$4.30$; P2
advisory-review-helper-blockers-only at v$4.30$; P3
passes-at-native-toolchain via v$4.27$ sidecar; P7
passes-at-native-toolchain via v$4.27$ sidecar; P8
advisory-review-helper-blockers-only at v$4.30$. P4 and P5 are
infrastructure-blocked at the time of submission: P4 has a
`sidecar_invocation_failed` verdict from a candidate-path parsing bug in
our harness rather than a science verdict; P5 is the same harness bug.
Receipts at `analytics/public/queries/lane_b_apn_audit_receipts.json`.
The methodological point is that an audit pipeline must be wrong four
times before it gets the helper-vs-top-level distinction right; we
report the four rounds and the retraction transparently because the same
conflation pattern is a plausible failure mode in any third-party Lean
audit.

## The policy consequence

The re-audit guardrail: *a per-family or per-(family, sub-source)
routing hypothesis should be promoted only when its supporting CI has
been computed on $N{\geq}n_{\mathrm{required}}$ at the target effect
size, and only with sub-source stratification reported.* The pilot
queue's three remaining cheap retests ($\sim 0$, $42$, and $420$ calls
respectively) close the same gap on the program's other policy
hypotheses; their results are published alongside the existing
hypotheses as the retests complete.

# What this paper does NOT establish {#sec:limits}

- It does NOT show that cognitive-debiasing interventions never transfer
  to LLMs. Four of five tested are `inconclusive_underpowered` at our
  low-overlap-corpus $N$, not falsified.

- It does NOT establish that GPT-5.4-mini's low-overlap-corpus
  frequency-framing improvement would survive cross-corpus replication
  at proper power. $N{\geq}91$ public-domain is required.

- It does NOT generalize beyond five model families and two corpus
  classes. The low-overlap corpus is research-internal and not publicly
  available in raw form.

- It does NOT decompose LLM *reasoning* mechanistically. The
  channel-orthogonality claim ($\S\ref{sec:channel-orthogonality}$) is
  at the *expression* level; a reasoning-decomposition claim would need
  white-box mechanistic interpretability.

- The four-axis confounding between corpora means the cross-corpus
  result is evidence that at least one axis matters, not yet a clean
  attribution. The 4-cell de-confounded corpus is the most important
  methodological follow-up.

- It does NOT establish that RLHF/alignment *causes* the per-family bias
  differences (Axis 3). Every Axis-3 result, in-distribution and
  out-of-distribution, is a *cross-family* contrast, which confounds
  alignment with pretraining-corpus differences; families differ in
  both. The apparent "more alignment, less inherited bias" ordering also
  runs opposite to the established result that instruction-tuning
  amplifies several cognitive biases (Itzhak et al. 2024). The honest
  Axis-3 claim is therefore the weaker, observational one---*family
  identity predicts bias magnitude*---not the causal *alignment damps
  bias*. Isolating the alignment stage requires within-family
  checkpoints (pre- vs post-RLHF) or matched-pretraining families, which
  we do not have.

- Bid-ask spread cross-corpus is currently underpowered; the
  direction-shift is suggestive but not conclusive at $N{=}42$.

- The worry-Brier sign-flip mechanism is provisional
  ($\S\ref{sec:worry-mechanism}$ multi-probe synthesis);
  activation-level probing and a topic-matched corpus would settle it.

- Per-family signal strength is conditional on prompt-invariance
  ($\S\ref{sec:prompt-invariance}$). Gemini and DeepSeek findings should
  be read with the prompt-stability discount documented there until the
  within-family paraphrase pilot is run.

# Reproducibility {#sec:repro}

All pilot calls persist as JSONL files and are ingested into a SQLite
database at `analytics/public/calibration/forecaster_calibration.db`.
Pre-registrations and verdict resolutions are in the same database. The
reusable general-purpose statistics module is at
`src/ztare/experiment_stats.py` (power calculator, bootstrap CI, paired
permutation, Fisher-$z$ Spearman, TOST, BH-FDR, power-aware verdict, BIC
Bayes factor, reproducibility hash). Forecasting-specific wrappers are
in the per-project `calibration_stats.py`. Every reported finding
reproduces via CLI: `calibration_stats.py finding frequency-framing`,
`brier-ci --primitive baseline --corpus low-overlap`,
`spearman --pilot bid-ask --x spread`, etc.

**Low-overlap-corpus reproducibility.** The low-overlap corpus is
research-internal and not publicly releasable in raw form. Remediation
paths: *(a)* sanitized release with research-internal identifiers
replaced by neutral tags (e.g., "Operation $X$ tactic $Y$ on row class
$Z$"), preserving the four-axis structural profile; release pending
clearance. *(b)* Parallel public alien-domain corpus drawn from
public-but-niche academic sub-fields (specific Lean mathlib lemma
classes; obscure subfields of partial differential equations; verifiable
but low-traffic historical-event resolutions) matching the low-overlap
corpus's four-axis profile, intended for direct third-party replication
of the frequency-framing and bid-ask-spread results.

# Composed routing recipe: closed form {#app:routed-recipe}

Let $\bar p$ be the mean of the five families' point estimates
$p_{\text{success}}$ on a given contract, $h$ the
days-to-resolution-from-cutoff, and
$s\in\{\textrm{polymarket}, \textrm{manifold}, \textrm{yfinance}\}$ the
source identifier. The composed routed forecast $\hat p$ is:

$$\begin{aligned}
\hat p_{\mathrm{conf\text{-}NO}} &= \begin{cases} 0.35\,\bar p + 0.65\,(0.10) & \text{if } \bar p < 0.20 \\ \bar p & \text{otherwise} \end{cases} \\
\hat p_{\mathrm{YES\text{-}bias}} &= \hat p_{\mathrm{conf\text{-}NO}} + \begin{cases} +0.06 & \text{if } 0.30 \le \hat p_{\mathrm{conf\text{-}NO}} \le 0.55 \\ 0 & \text{otherwise} \end{cases} \\
\hat p_{\mathrm{horizon}} &= 0.5 + (\hat p_{\mathrm{YES\text{-}bias}} - 0.5)\cdot \tfrac{1}{1 + 0.01\,h} \\
\hat p &= 0.5 + (\hat p_{\mathrm{horizon}} - 0.5)\cdot w_s
\end{aligned}$$

with $w_s = 0.70$ for polymarket, $0.85$ for manifold, $1.00$ for
yfinance. The four coefficients $(0.10, 0.06, 0.01, w_s)$ are not
learned from held-out folds; they are chosen from the universal patterns
reported in $\S\ref{sec:universal}$ (confident-NO over-confidence,
middle-band YES under-shooting, horizon-conditional Brier slope,
per-source Brier ordering). The per-channel routed alternative
(routed_v2 in the main text) substitutes per-family channel weights for
the universal $w_s$; its weights are listed in the appendix companion
file. The implementation reproduces from
`projects/forecaster_skill_calibration_v1/workspace/composed_routing_n142.py`
on the database snapshot dated 2026-05-28.

::::::::::::::::: {#refs .references .csl-bib-body .hanging-indent entry-spacing="0"}
::: {#ref-arkes1985sunk .csl-entry}
Arkes, Hal R., and Catherine Blumer. 1985. "The Psychology of Sunk
Cost." *Organizational Behavior and Human Decision Processes* 35 (1):
124--40.
:::

::: {#ref-frederick2002time .csl-entry}
Frederick, Shane, George Loewenstein, and Ted O'Donoghue. 2002. "Time
Discounting and Time Preference: A Critical Review." *Journal of
Economic Literature* 40 (2): 351--401.
:::

::: {#ref-halawi2024approaching .csl-entry}
Halawi, Danny, Fred Zhang, Chen Yueh-Han, and Jacob Steinhardt. 2024.
"Approaching Human-Level Forecasting with Language Models." *arXiv
Preprint arXiv:2402.18563*.
:::

::: {#ref-itzhak2024instructed .csl-entry}
Itzhak, Itay, Gabriel Stanovsky, Nir Rosenfeld, and Yonatan Belinkov.
2024. "Instructed to Bias: Instruction-Tuned Language Models Exhibit
Emergent Cognitive Bias." *Transactions of the Association for
Computational Linguistics* 12: 771--85.
<https://doi.org/10.1162/tacl_a_00673>.
:::

::: {#ref-kahneman1979prospect .csl-entry}
Kahneman, Daniel, and Amos Tversky. 1979. "Prospect Theory: An Analysis
of Decision Under Risk." *Econometrica* 47 (2): 263--91.
:::

::: {#ref-lanham2023faithfulness .csl-entry}
Lanham, Tamera, Anna Chen, Ansh Radhakrishnan, Benoit Steiner, Carson
Denison, Danny Hernandez, Dustin Li, et al. 2023. "Measuring
Faithfulness in Chain-of-Thought Reasoning." *arXiv Preprint
arXiv:2307.13702*.
:::

::: {#ref-lichtenstein1977calibration .csl-entry}
Lichtenstein, Sarah, Baruch Fischhoff, and Lawrence D. Phillips. 1977.
"Calibration of Probabilities: The State of the Art." *Decision Making
and Change in Human Affairs*, 275--324.
:::

::: {#ref-schoenegger2024ensemble .csl-entry}
Schoenegger, Philipp. 2024. "Wisdom of the Silicon Crowd: LLM Ensemble
Prediction Capabilities Rival Human Crowd Accuracy." *arXiv Preprint
arXiv:2402.19379*.
:::

::: {#ref-tajfel1979integrative .csl-entry}
Tajfel, Henri, and John C. Turner. 1979. "An Integrative Theory of
Intergroup Conflict." In *The Social Psychology of Intergroup
Relations*, edited by William G. Austin and Stephen Worchel, 33--47.
Brooks/Cole.
:::

::: {#ref-tetlock2015superforecasting .csl-entry}
Tetlock, Philip E., and Dan Gardner. 2015. *Superforecasting: The Art
and Science of Prediction*. Crown.
:::

::: {#ref-thaler1980endowment .csl-entry}
Thaler, Richard. 1980. "Toward a Positive Theory of Consumer Choice."
*Journal of Economic Behavior and Organization* 1 (1): 39--60.
:::

::: {#ref-tversky1971beliefs .csl-entry}
Tversky, Amos, and Daniel Kahneman. 1971. "Belief in the Law of Small
Numbers." *Psychological Bulletin* 76 (2): 105--10.
:::

::: {#ref-tversky1974heuristics .csl-entry}
---------. 1974. "Judgment Under Uncertainty: Heuristics and Biases."
*Science* 185 (4157): 1124--31.
:::

::: {#ref-tversky1992advances .csl-entry}
---------. 1992. "Advances in Prospect Theory: Cumulative Representation
of Uncertainty." *Journal of Risk and Uncertainty* 5 (4): 297--323.
:::
:::::::::::::::::
