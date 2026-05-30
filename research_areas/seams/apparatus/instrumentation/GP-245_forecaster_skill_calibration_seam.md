# GP-245 Forecaster Skill Calibration Seam

> **Seam metadata** · `seam_id:` GP-245 · `track:` apparatus · `status:` `v1-open` - opened 2026-05-24 as the umbrella seam for the apparatus's forecast-skill discipline (insurance second-moment elicitation, Elo-style tournament metrics, and prompt-augmentation skill-lift experiments) · `last_updated:` 2026-05-24


## Status

`v1-open` — opened 2026-05-24 as the umbrella seam covering three previously-uncoordinated work threads on the apparatus's forecasting layer:

1. The forecast-insurance second-moment pilot (`projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/`)
2. Ex-post Elo tournament metric on the existing forecast pool + prediction ledger
3. The forecaster-skill-calibration prompt-ablation + ensemble-lift study (`projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/`, opening alongside this seam)

GP-230 (forecast pool / prediction market) is the primitive this seam composes; this seam is the *epistemic-discipline* layer on top of that primitive — measuring not just whether forecasts resolve but what makes some forecasts better-calibrated than others, and what prompt-level or ensemble-level interventions move that calibration in a measurable direction.

This seam records a contract. It names the minimum measurement protocol that lets the apparatus claim "agent A is a better forecaster than agent B on this corpus by X effect size" with controls against the failure modes Codex's adversarial review of the 2026-05-24 design draft flagged (training-data contamination, double-dipping on agent selection, prompt-instruction-compliance confounding with skill, and rediscovery of the published LLM-calibration literature).


## Eigenquestion

Given the apparatus's forecast pool (GP-230) and the prediction ledger, can the apparatus measure forecaster-skill heterogeneity in a way that survives (i) training-data contamination of the resolved-contract corpus, (ii) sample-selection winner's curse from same-data ranking-then-validation, and (iii) Goodhart attack on lexical or stylistic signatures — and if so, what prompt-level or ensemble-level interventions produce skill-lift that replicates across model families?


## Framing

Tetlock & the Good Judgment Project identified human "superforecasters" by repeated tournaments with thousands of forecasters, scoring on Brier across many years of resolved questions, and isolating cognitive and behavioral patterns of the top ~2%. **The published 2024 LLM-forecasting literature (ForecastBench, Approaching Human-Level Forecasting) tests bare-prompt LLMs against human crowds, not LLMs equipped with a metacognition stack.** The ZTARE apparatus is in a structurally different experimental condition: it ships an executable metacognition layer (33 patterns + 19 anti-patterns in `org/{patterns,anti-patterns}/*.md`; `src/ztare/research_director/pattern_action_contract.py` for typed action contracts; `analytics/public/ledgers/catch/catch_ledger.jsonl` for refutation feedback; `AGENTS.md` §0b2 for effort-calibration discipline; the anti-rehash gate from NS work; the scientific-amnesia precheck; ideas_felices §14 negative-evidence backpressure now live in the eigenquestion-generator). **Whether an apparatus-equipped agent forecasts at or above human-superforecaster level is an open empirical question this seam contracts to test, not a settled fact.** The published literature's "humans > LLMs" finding bounds vanilla LLM forecasting, not apparatus-augmented forecasting.

The naive port to AI agents — without acknowledging the apparatus's contribution — fails for three reasons documented in the published literature:

1. **Resolved-corpus contamination.** Resolved questions may leak into LLM training data (paraphrases, named-entity overlap, downstream discussion). The contamination literature [Sainz et al. 2024, Li et al. 2023] shows that "screen for resolved/succeeded/failed in the question text" catches only the blatant forms, not the typical leakage. The contamination-resistant approach is the ForecastBench design — questions about future events with no answer at submission time.

2. **AI forecasters are not the natural unit Tetlock studied.** Mellers/Tetlock 2015 identified four explanations for superforecaster performance: cognitive ability/style, task-specific skill, motivation, and enriched environments. None reduce to surface lexical signatures (the failure mode of the 2026-05-24 v0 design draft). The legitimate AI port is: (a) the GJP 40-minute training intervention's *content* (biases + statistics + Bayesian reasoning) ported to a system-prompt augmentation, and (b) the ensemble-aggregation finding (`Wisdom of the Silicon Crowd`, Schoenegger et al. 2024) which shows a 12-LLM ensemble matches human-crowd Brier on real binary questions.

3. **The right metric is not raw Brier.** Raw mean Brier penalizes agents who participate in different subsets of contracts equally; it doesn't yield a skill-gap that's interpretable across models. Elo-from-Brier (pairwise: agent with lower Brier on the same contract "wins") gives a rating scale where a 200-point gap corresponds to ~76% expected win rate and a 400-point gap to ~91%, which is the interpretable skill measure the published Tetlock literature lacks for cross-platform comparison.

The seam's framing is: forecaster-skill calibration is a *measurement* problem the apparatus has under-instrumented. The mining-side and validator-side have rich calibration; the forecaster-side has only `aggregate Brier`. This seam contracts in the minimum measurement set that fixes that, *and* the discipline contracts that prevent the measurement from over-claiming.


## Contract

Every artifact in the forecaster-skill calibration sub-program (projects, scripts, dashboards) MUST attach a `forecaster_skill_measurement` object with these required properties:

```yaml
corpus_provenance:
  source: "gp230_resolved" | "gp230_open" | "external_benchmark" | "synthetic"
  contamination_resistance:
    contracts_before_model_cutoff: int
    contracts_after_model_cutoff: int
    blind_to_agents: bool
    notes: string

split_discipline:
  protocol: "single" | "nested_holdout" | "cross_fitting"
  n_discovery: int | null
  n_validation: int | null
  n_test: int
  seed: int

agent_dispatch:
  agents: list[{agent_id, runtime, model_id_or_default}]
  prompt_class: "baseline" | "augmented" | "placebo_length_matched"
  ensemble: bool
  ensemble_method: "median" | "mean" | "logit_pool" | null
  dispatch_primitive: "src.ztare.common.subscription_agent_runtime"

scoring:
  primary_metric: "brier" | "log_score" | "elo_from_brier"
  secondary_metrics: list[string]
  realized_signal_field: string  # e.g., "success_bool"

pre_registered_hypotheses:
  list of {hypothesis_id, statement, falsifier, sample_size_power_note}

honest_non_claims:
  list of statements about what the experiment cannot establish
```

A study artifact missing `corpus_provenance.contamination_resistance` or `split_discipline.protocol = nested_holdout` SHOULD be tagged `apparatus_internal_pilot` and MAY NOT inform any public claim about LLM forecasting skill without a follow-up study that has both.

The Elo-from-Brier metric (`scoring.primary_metric = elo_from_brier`) is the canonical ranking primitive for this seam. Implementation: pairwise tournament where on each resolved contract, all agents that forecast on it are matched pairwise; agent with lower Brier wins, K-factor = 24, initial rating = 1500. The first implementation at `projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/compute_ex_post_elo.py` (2026-05-24) is the canonical reference; future consumers should import or reproduce its semantics, not invent a parallel ranking.

The forecast pool (GP-230) already produces the per-contract per-agent forecast files needed; this seam does NOT modify GP-230's schema. It composes downstream.


## Existing artifacts and pilots covered by this seam

### Active projects

| Path | Status | Headline |
|---|---|---|
| `projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/` | v1 done, v2 done, v3 dispatching | H2 (premium spread > p_success spread) SUPPORTED at v2 N=30; H3 (premium → outcome calibration) NULL at v2; v3 tests H3' (premium → interval coverage) at N=50 × 3 agents |
| `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/` | opening alongside this seam | Tests GJP-training-port + ensemble-lift on a contamination-aware subset of GP-230 |

### Canonical scripts

| Path | Role |
|---|---|
| `projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/compute_ex_post_elo.py` | Canonical Elo-from-Brier implementation. Run ex-post on any resolved-contract corpus + per-agent forecasts. |
| `projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/run_pilot_dispatch.py` (v1), `run_pilot_v2_dispatch.py` (v2), `run_pilot_v3_dispatch.py` (v3) | Subscription-CLI dispatchers; canonical pattern for blind-retro forecast elicitation with the second-moment fields (premium, tail loss, credible interval). |

### Adversarial reviews on file

| Path | Reviewer | Verdict on |
|---|---|---|
| `projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/codex_review_tetlock_design.md` | Codex (subscription, gpt-5.4-mini, reasoning-effort high) | Killed the v0 Tetlock-for-AI design draft 2026-05-24. Substantive critique on (i) contamination, (ii) double-dipping, (iii) placebo prompts, (iv) lexical signatures vs real GJP findings, (v) sample-size hand-waving, (vi) rediscovery of published LLM-calibration work. |


## Literature anchors

The following published work is decisive for this seam's framing. Any future consumer should treat these as starting bibliography, not exhaustive.

### Contamination-resistant LLM forecasting benchmarks

- **[ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities](https://arxiv.org/abs/2409.19839)** — 1,000 forecasting questions about future events (no known answer at submission), with explicit comparison vs human forecasters. Expert forecasters outperform top LLM (p<0.001). The canonical contamination-resistant benchmark and the right corpus to cite for any "AI forecasting skill" claim.
- **[Approaching Human-Level Forecasting with Language Models](https://arxiv.org/abs/2402.18563) (Halawi et al. 2024)** — Retrieval-augmented LM "nears the crowd aggregate of competitive forecasters, and in some settings surpasses it." Test set is explicitly post-knowledge-cutoff. Establishes that retrieval + aggregation, not bare prompting, is what closes the human gap.
- **[LLM Prediction Capabilities: Evidence from a Real-World Forecasting Tournament](https://arxiv.org/abs/2310.13014)** — GPT-4 tested in a live tournament, found to lag the human crowd. The empirical baseline against which Tetlock-for-AI claims need to be calibrated.

### Ensemble methods (the strongest published "Tetlock-for-AI" signal)

- **[Wisdom of the Silicon Crowd: LLM Ensemble Prediction Capabilities Match Human Crowd Accuracy](https://arxiv.org/abs/2402.19379) (Schoenegger et al. 2024)** — 12-LLM ensemble of frontier models matched a 925-person human-crowd Brier on 31 binary questions. Median-human-prediction-as-input boosted individual model accuracy by 17–28%. **The decisive finding: aggregation drives improvement, not prompt engineering.**

### LLM calibration shaping (where naive Tetlock ports rediscover)

- **[Just Ask for Calibration](https://arxiv.org/abs/2305.14975) (Tian et al. 2023)** — Verbalized confidence (model outputs probability as text) is ~50% better-calibrated than RLHF-tuned model's conditional probabilities. Cross-model (ChatGPT, GPT-4, Claude). **The apparatus's current `p_success` elicitation already gets this lift for free.**
- **[Linguistic Calibration of Language Models](https://arxiv.org/abs/2404.00474)** — Calibration via natural-language probability expressions.
- **[Calibration-Tuning](https://aclanthology.org/2024.uncertainlp-1.1/)** — Direct training of LLMs on calibration objectives.
- **[Calibrating Verbalized Probabilities for LLMs](https://arxiv.org/abs/2410.06707)** — Post-hoc methods for re-scaling verbalized probabilities.

### Training-data contamination (the decisive risk for any retro study)

- **[Benchmark Data Contamination of Large Language Models: A Survey](https://arxiv.org/abs/2406.04244) (Sainz et al. 2024)** — Survey of contamination types, detection methods, and mitigation strategies.
- **[Task Contamination: Language Models May Not Be Few-Shot Anymore](https://arxiv.org/abs/2312.16337) (Li et al. 2023)** — Evidence that LLMs may be solving "few-shot" tasks they've actually seen in training.
- **[LatestEval](https://ojs.aaai.org/index.php/AAAI/article/view/29822) (AAAI 2024)** — Contamination-resistant evaluation construction methodology.

### Human superforecaster literature (the real Tetlock signal)

- **[Identifying and Cultivating Superforecasters as a Method of Improving Probabilistic Predictions](https://stanford.edu/~knutson/nfc/mellers15.pdf) (Mellers, Tetlock et al. 2015)** — Four explanations for superforecaster performance: cognitive ability/style, task-specific skill, motivation, enriched environment. **A 40-minute training intervention (biases + basic statistics + Bayesian reasoning) produced measurable forecasting lift.** The legitimate AI port is the 4-topic *content* of that training, ported to a system prompt — NOT lexical signatures of top-quartile forecasters.
- **[Psychological Strategies for Winning a Geopolitical Forecasting Tournament](https://journals.sagepub.com/doi/10.1177/0956797614524255)** — Granular probabilities, frequent small Bayesian updates, multi-perspective reasoning ("dragonfly cognition"). Cited in design-draft v0 with the warning that the signal is in reasoning structure, not surface tokens.
- **[How generalizable is good judgment? A multi-task, multi-benchmark study](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/EF0490D9631D0D6061F0414DF502AD16/S1930297500006240a.pdf/how_generalizable_is_good_judgment_a_multitask_multibenchmark_study.pdf)** — Forecasting skill partly transfers across domains for human superforecasters; bound on the analogy strength.


## Honest non-claims this seam enforces

- This seam does not claim that AI agents are "superforecasters" in Tetlock's sense — that requires comparison against an independent benchmark forecast (crowd average on a contamination-resistant corpus), which the apparatus does not currently have.
- This seam does not claim any prompt augmentation produces forecasting skill in a deployment-grade sense. The strongest claim it admits is: "augmentation X produces a measurable Brier delta on a sealed N-contract test set, under controls Y, Z."
- The Elo-from-Brier ratings (canonical implementation at `projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/compute_ex_post_elo.py`) are *retrospective* skill measures on the apparatus's own forecasting corpus. They do NOT generalize to non-apparatus forecasting domains (politics, geopolitics, weather) without explicit transfer experiments.
- Sample sizes in the current pilots (N=3 to N=50) are inadequate for claims about interaction effects across model families. Any cross-family claim requires N≥100 with at least three genuinely independent model families.


## Promotion / demotion path

A study artifact under this seam moves out of pilot status via three checks:

1. **Contamination check passed.** Either corpus is provably contamination-resistant (post-cutoff, OPEN at study start, or external benchmark) OR contamination is bounded and reported as a residual.
2. **Nested-split discipline passed.** Ranking + signature discovery + augmentation validation happen on disjoint splits.
3. **Replication.** The lift (if any) replicates on at least one additional model family OR on at least one fresh corpus.

A pilot that fails any of the three is documented as a demotion under this seam, dated, and its findings tagged `apparatus_internal_pilot_only`.


## Open obligations

- Build a contamination-resistant apparatus-internal corpus by accumulating OPEN GP-230 contracts at dispatch time and sealing them for prospective study. (Currently only 14 OPEN contracts exist; insufficient for N≥50 studies. Need 90-day accumulation cycle.)
- Decide whether to subscribe to ForecastBench as the external comparator (operator decision; bandwidth + cost question).
- Wire the canonical Elo metric into the analytics dashboard so it surfaces alongside per-agent Brier. (Currently the Elo computation is a one-off script; promotion to standing dashboard panel is gated on operator confirmation that the metric is the right one.)
- Extend `ideas_felices.md` §9 (tail-risk insurance sidecar) and §16 (cross-predictor cost-disagreement triage) with cross-pointers to this seam.


## Cross-references

- **Parent seam (primitive):** [`research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`](../../protocol/GP-230_forecast_pool_decision_market_seam.md). GP-230 owns the forecast-pool / prediction-market PRIMITIVE (sealed contracts, scoring, resolution); this seam (GP-245) owns the EPISTEMIC-DISCIPLINE layer (skill measurement, agent-tournament structure, prompt-augmentation ablations, contamination-resistance contracts).
- Adjacent: `analytics/public/forecast_pool/README.md` (GP-230 implementation surface)
- Adjacent: `analytics/public/ledgers/prediction/PREDICTION_LEDGER_README.md` (prediction-ledger schema, the precursor to the forecast pool that recorded effort/conditional-odds estimates per predictor)
- Adjacent: `docs/concepts/prediction_ledger_pattern.md` (public-surface description of the prediction-ledger pattern)
- Calibration discipline: `AGENTS.md` §0b2 (effort-estimate calibration self-rule, the operator-facing analog of this seam's measurement discipline)
- Idea backlog entries: `docs/internal/drafts/ideas_felices.md` §9 (tail-risk insurance sidecar), §15 (calibration-aware dispatch wrapper), §16 (cross-predictor cost-disagreement triage)

## v2 / v3 candidate sub-experiments (roadmap)

Operator-prioritized after v1.3 dispatch lands. Ordered by leverage and cost.

### Add to v1.3 readout (free post-hoc, no extra dispatch)

- **Honest non-claim density (#2).** Regex+lexicon classifier over `rationale_short` for hedge markers ("uncertain", "I don't know", "no evidence on X", "could be either"). Per-(agent, condition) density + correlation with Brier. Tests whether the apparatus's "honest non-claim" imperative actually produces more honest non-claims, and whether that's correlated with better calibration. Implementation: `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/score_honest_nonclaims.py` (post-hoc on v1.3-B logs).

### Separate small pilots (require fresh dispatch)

- **Anti-pattern contract as 5th condition (C_antipattern) (#3).** +120 calls (1 cond × 3 agents × 40 contracts). Per contract, inject the matching `org/anti-patterns/*.md` for `task_type`. Tests whether the H18 finding (anti-pattern contracts → 5.8× action accuracy lift in epistemic-generation) ports cross-task to forecasting. If C_antipattern beats C_apparatus, the apparatus's lift mechanism is SPECIFICALLY typed-failure-mapping, not generic metacognition. Direct test of the strongest apparatus empirical anchor. Requires Codex pre-dispatch review and length-parity check at ~160-word block.

- **Ensemble herding pilot (#4).** ~240 calls (6 directional pairs × 40 contracts). Present agent B with agent A's already-issued forecast + rationale; measure whether B's forecast collapses toward A's (herding) or diverges productively. Schoenegger 2024 explicitly notes they did NOT test non-independent aggregation. Novel finding either direction. Standalone pilot.

- **Cross-agent discipline transfer (#5).** ~360 calls. Agent A in C_apparatus issues forecast + rationale; agent B in C_bare receives ONLY A's rationale (not p_success) and is asked to forecast. Tests whether apparatus discipline is COMMUNICABLE — the strongest possible claim for the apparatus's "metacognition is portable" implicit claim. No literature analogue.

### Parked

- **Self-cost calibration (#1).** Operator note: subscription-mode dispatch does NOT report token cost; only wallclock latency is measurable, which is a weak proxy. Park until either (a) we get a cost reporter on the subscription primitive, or (b) we run a parallel API-mode pilot where cost is reported (operator-rejected for now per AGENTS.md subscription-only rule).

### Non-prediction-market apparatus-unique innovations (roadmap)

These extend the seam's scope from "market-binary forecasting skill" to "reasoning-forecasting skill measured against apparatus ground truth." #6 and #7 are operator-prioritized for build now; #8-10 are parked behind their first reads.

- **#6 — Lean-proof completability forecasting.** Agent reads a Lean proof goal + tactic history; predicts whether the next 10-tactic search closes the goal. Ground truth = actual LeanMill outcome (hard binary, no contamination). Apparatus-unique: nobody else runs a 24×7 proof mill with a backlog of resolved attempts. **If positive →** LeanMill queue moves from FIFO to yield-predicted-priority (self-scheduling proof mill, real design change). Tests *reasoning-forecasting* — the literature can't test this at all.

- **#7 — Reflexive self-cost meta-calibration.** Ask agent: "Before you start, predict your own cost-prediction error ratio against your historical class baseline." Then measure. Does Claude actually know it's 8.11× off-band per AGENTS.md §0b2? Apparatus-unique: only place with per-predictor calibration history. **If reflexive works →** §0b2 deprecates (agent self-corrects); **if fails →** rule stays + becomes externally publishable evidence that subscription-class LLMs lack meta-calibration.

- **#8 — Catch-ledger backpressure efficacy.** Compare eigenquestion generation WITH vs WITHOUT the §14 FALSIFIED-block injection on a held-out prior corpus. Does the FALSIFIED block actually suppress generation of similar-already-falsified claims? **If null →** §14 demoted as theater; **if real →** §14 becomes canonical "learning from failure" primitive, promoted to mandatory in mutator prompts. ~80 calls.

- **#9 — Cross-domain H18 port.** Replicate the H18 finding (anti-pattern contracts → 5.8× action accuracy lift) on (a) Lean-tactic selection, (b) code-edit correctness, (c) retrieval-relevance ranking. Each is independent. **If positive on N domains →** anti-pattern contracts graduate from `org/anti-patterns/` discoverability to first-class apparatus primitive. May warrant its own parent seam under epistemic-generation rather than living here. ~150 calls per port × 3 ports.

- **#10 — RD decision longitudinal verdict.** Every recorded RD decision (`$SEAM_CHOICE`, `$DEMOTE`, `$RATIFY`) gets operator-ticked 30/60/90-day "held up / should have reversed" verdict. Compute per-RD-instance hit rate and per-decision-type calibration. **If bad →** the "AI-research-director feasibility" claim is hollow; **if good →** externally publishable AI-RD feasibility paper. Apparatus-unique substrate. Free — pure operator-tick + analysis. May graduate to its own RD-audit seam.

### Cross-field-method innovations (roadmap, added 2026-05-24)

- **#11 — Causal probing of forecast determinants** (from causal inference / interventional methods). Generate 20 base contracts; for each create 5 minimal-edit variants (swap key terms, reorder evidence, change horizon ±10%). Dispatch all 100 contracts × 3 agents. Compute *(forecast variance within base-contract's variant family)* / *(forecast variance across base contracts)*. **High ratio = surface-matching; low ratio = deep signal tracking.** Apparatus-unique because we can systematically perturb. If agents are surface-matching, F8/F10/F13/F15/F17 all have a generalizability ceiling. ~150 calls.

- **#12 — Anytime / thinking-budget forecasting** (from anytime algorithms / inference scaling). Same forecast asked of same agent under 3 budgets: no-scratchpad, 200-token scratchpad, 800-token scratchpad. Does forecast quality scale with thinking budget, plateau, or degrade? Practical deployment question — most apparatus dispatches don't currently request explicit scratchpads. ~270 calls.

- **#13 — External forecast-meta-classifier** (from OOD-detection / meta-learning). Train a gradient-boosted classifier on existing pool forecasts + outcomes (n=590) to predict per-row Brier from contract features (text length, agent_id, domain, prompt tokens). Apply to NEW forecasts as pre-resolution reliability score. Fundamentally different from self-introspection — third-party prediction of agent calibration. If accurate, gives the apparatus an external watchdog that doesn't depend on agent honesty. **~0 LLM calls** (pure classifier on banked data); ~30 min build.

### Format/structure innovations (motivated by F19/v6 null + apparatus H32→H35 analogy)

- **#14 — Typed-rationale exchange.** F19/F22 showed free-form rationale exposure doesn't reliably help receiver Brier. The H32→H35 apparatus finding showed: same task, different format → opposite outcome (free-form compilation fails, typed-class compilation succeeds). Test the cross-task port: receivers see senders' rationales as STRUCTURED JSON (`{key_evidence: [...], specific_failure_modes: [...], confidence_in_evidence: int}`) instead of free prose. If typed format rescues transfer, F19's null is about FORMAT not CONTENT. ~360 calls (120 fresh structured senders + 240 receivers).

- **#15 — Honest abstention / refusal-as-calibration-signal.** Tian 2023 / Halawi 2024 measure calibration on what LLMs DO predict; never elicit refusal. For each contract, ask the agent BOTH "should this be forecasted by an LLM at all?" AND "if yes, p_success." Test whether abstention CORRECTLY identifies contracts where the agent's unrequested p_success would have been mis-calibrated. If yes, abstention is informative; if no, it's noise. Could become a deployment-time triage signal. ~120 calls.

- **#16 — Compositional second-moment elicitation.** F8/F10/F20 establish individual second-moment channels (tail_premium, decomposed failure-mode probs, verbal-confidence) work. Untested: asking for all simultaneously. Super-additive (more signal) vs sub-additive (attention dilution / field conflict)? Determines whether deployment should request one channel or all five. ~180 calls.

### Repo-improvement directions (added 2026-05-24 — build-on-where-prior-research-is-weak)

- **#17 — Self-generated distractors** (arXiv:2509.25532 motivated). Generate 2-3 distractor hypotheses before forecasting; tests suggestibility mechanism. ~180 calls. **Firing now.**

- **#18 — Failure Mode Atlas paper.** Honest catalog of F12/F14/F19/F22/F24 negatives with operational implications. Published literature is positive-result-biased; ours features failures with structural diagnosis. Scaffold: `papers/failure_mode_atlas/DESIGN.md`.

- **#19 — Apparatus-as-Reproducible-Testbed paper.** Infrastructure paper proposing ZTARE forecast pool + prediction ledger + meta-Darwin discipline + sealed-GT protocol as reusable evaluation testbed for LLM-forecasting calibration. Most labs build ad-hoc setups; we have multi-year-stable infrastructure with pre-fire audit discipline. Scaffold: `papers/apparatus_testbed/DESIGN.md`.

- **#20 — Per-Agent Personalized Calibration Rules.** F17 shows §0b2 helps claude not codex_55. Generalize to a tool that learns per-agent calibration rules from historical data and applies at dispatch. RecSys-style but for LLM calibration. Scaffold: `projects/llm_forecasting_calibration_program/per_agent_calibration_v18/workspace/DESIGN.md`.

- **#21 — Cross-Domain Calibration Transfer Benchmark.** F12 (Lean) vs F8 (market) vs F21 (game-theory) shows calibration differs by domain. Standardized 5-domain × 50-contract benchmark. Scaffold: `projects/llm_forecasting_calibration_program/cross_domain_benchmark_v19/workspace/DESIGN.md`.

- **#22 — Forecast-as-Decision Utility Framework.** Brier measures symmetric quadratic loss; deployment cares about decision quality under asymmetric costs. Framework with per-contract cost_of_wrong + decision_threshold. tail_insurance_premium channel (F8) is the natural input. Scaffold: `projects/llm_forecasting_calibration_program/decision_utility_v20/workspace/DESIGN.md`.


## Updates log

- 2026-05-24 — seam opened. v1/v2/v3 of the forecast-insurance pilot landed. v3 result (N=50, 3 agents, blind retro): H2 supported (median premium/p_success spread ratio = 1.45, above 1.2 threshold); H3' (higher-premium agent's credible interval contains realized outcome) **exactly 0.500** across 146 paired comparisons (premium signal carries zero information about interval honesty); H4 (within-agent premium-vs-interval-width correlation) MIXED: claude=+0.09, codex-gpt5.5=−0.12, codex-gpt5.4mini=−0.40. The cleanest reading across v1→v2→v3: insurance premium extracts SOMETHING distinct from point estimate (H2 robust, three replications), but that something is not outcome calibration (H3 null) and is not coherent self-reported uncertainty (H4 mixed/negative). Likely candidate: premium measures perceived *asymmetric loss* plus agent-idiosyncratic priors, not Bayesian-coherent tail-risk. §9 stays in `ideas_felices.md` with this refined scope. v4 (if pursued) should test asymmetric-loss elicitation directly.
- 2026-05-24 — pilot v4 (N=100 power rescue) dispatched. Smoke green (6/6 parsed; H2 supported with normalized premium spread 0.36, premium/p_success ratio 3.6×). Full dispatch in flight at ~2 rows/min pace. Will report H3' at N=100 (the decisive question: power problem or genuine non-Bayesian-coherence?).
- 2026-05-24 — v1.3-B amendment to the forecaster_skill_calibration project: all 4 condition prompts now collect `tail_insurance_premium` + `tail_loss_magnitude` (1-100). Adds H_ζ (apparatus condition shifts premium pattern). Doubles experimental yield on the same 480 calls.
- 2026-05-24 — consolidated cross-pilot Elo computed. Top: codex_55 1647 > codex_54mini 1538 > codex_v2 1478 > claude_v2 1421 > claude_v3 1417. **Spearman ρ = −1.00 between v2 and v3** on the 2 overlapping families. Caveat: degenerate test (n=2 families), prompts differed between v2 and v3 (v3 added CI fields), so flip may be prompt-shift artifact, not skill drift. H_ε unsupported on existing data; v1.3's within-condition prompt-held-fixed design is a much cleaner H_ε probe.
- 2026-05-24 — codex CLI hang on long prompts diagnosed (stdin pipe inheritance in subprocess.run). One-line fix landed in `src/ztare/common/subscription_agent_runtime.py:127` (`stdin=subprocess.DEVNULL`).
- 2026-05-24 — Codex v1.3 verdict: `do-not-run` (2 surviving kills after closing collision/parity/dispatch-order): post-hoc contamination filter = stopping-rule problem; runner checkpoint marks failed rows as done. v1.4 fixes both: pre-registered primary readout = full N=40 with filter relegated to sensitivity analysis; `load_completed` now only marks `parsed.p_success`-present rows as done.
- 2026-05-24 — **F8 [publishable-candidate]**: pilot v4 N=100 settled. Strict-coverage proxy on binary outcomes is STRUCTURALLY DEGENERATE (mean coverage = 0 across all 300 rows; CIs sit strictly inside (0,1)). Replaced with premium-vs-Brier Spearman: **+0.36 pooled, all 3 agents same sign** (+0.38, +0.37, +0.49). Verbalized tail-insurance premium extracts calibration signal beyond point estimate. Methodological + empirical contribution.
- 2026-05-24 — **F10 [strong]**: F8 replicates on existing forecast pool (n=590) with decomposed failure-mode probabilities (p_dependency_issue, p_needs_new_lemma, p_regression). Same direction, same magnitude. RD elicitation schema is accidentally empirically validated.
- 2026-05-24 — **F12 [publishable-candidate, NEGATIVE]**: pilot v7 N=180 Lean-proof completability. All 3 agents WORSE than constant-0.5 baseline (Brier 0.46-0.57 vs 0.25). All 3 Spearmans NEGATIVE (anti-correlated). Mean p shows pessimistic bias (claude 0.22 when truth is 50/50). LeanMill self-scheduling claim shut down for subscription-class LLMs. Distinguished from AlphaProof generation work (Tsoukalos 2026): F12 is about PREDICTION before attempt, AlphaProof is about GENERATION.
- 2026-05-24 — F12 rescue attempts on v7 data: ensemble median got WORSE (0.537 vs 0.456 best single agent). Pairwise ranking accuracy = 0.251 (chance 0.500). Top-quartile-confidence pairs ranking = **0.075** — agents most wrong when most confident. Either real anti-calibration OR sampling artifact (stratification picked agent-hostile cases). v7.2 fires natural-distribution + 5-condition test to distinguish.
- 2026-05-24 — **F13 [publishable-candidate]**: pilot v9 N=90 paired. LLMs CAN predict their own response wallclock at Spearman +0.50 to +0.90 (claude best at 0.90 with 0.87 width-error correlation). BUT intervals systematically over-confident (90% nominal covers 27-73% actual). Tian 2023 extended to quantitative-self-prediction.
- 2026-05-24 — **F14 [derived, publishable-candidate dual-result]**: F12 + F13 contrast establishes: introspection on OWN future behavior succeeds; prediction of EXTERNAL reasoning system fails. Same model trio, same primitive, same elicitation. Differs only in WHO RUNS THE PROCESS.
- 2026-05-24 — **F15 [publishable-candidate]**: pilot v5 N=239 triples. LLMs herd toward shown prior forecasts ~74% of the time, mean shift −0.067 p_success. ALL 6 directional pairs herd. Counter to Schoenegger 2024 ensemble-independence assumption. Asymmetric (codex_54mini most contagious sender; claude most anchorable receiver). v5.1 firing to test whether explicit skeptical framing reduces effect.
- 2026-05-24 — **F15 implication for H_γ ensemble in v1.3-B**: H_γ assumes independence; v1.3-B dispatch keeps agents blind to each other (single-shot per agent, no exposure). Independence preserved IN that setup. F15 caveat applies only to contexts where agents see each other's outputs (multi-round debate, second-opinion protocols, RD review chains).
- 2026-05-29 — **F100 / F101 / F102 / F103 landed in workspace/research_log.md**: confident-NO discount per-family at p<0.05 on N=142 v28a (F100, YAML deployed in `org/calibration/per_agent_prompt_policy.yaml`); Halawi 2024 dataset structurally contaminated for 2025+ panel (F101, added to working paper §Implications); novel-bias smokes split — loss-frame symmetry ESCAPED, status-quo / endowment bias INHERITED, prob-weighting near-linear (F102 at n=30 → n=42 external on diversified pool IN FLIGHT); Lane B canonical L1+L2+L3 audit corrected over 4 rounds for helper-vs-top-level conflation (F103 — under the corrected status rule with forced sidecar, top-level theorems are largely audit-clean; earlier "DeepMind laundered" framing retracted).
- 2026-05-29 — **Findings completeness ledger committed** at `workspace/findings_completeness_ledger.md`. Every F-row tagged with verdict + state + next-best retest + cost + whether corpus_v26 (90 Metaculus future-resolving + FRED-constructed contracts) helps. Buckets: settled 15, scoped 8, underpowered 3, pending-retest-unlocked-by-corpus_v26 7, in-flight 2, superseded 1, retracted 4.
- 2026-05-29 — **Tracking commitment 1: ex-post yield calibration on the pilot queue.** Every pilot with an ex-ante ★-rating receives a `realised_yield` score once it lands (h1_supported published +3 / internal +2 / h0_kept +1 / inconclusive_underpowered 0 / retracted −2). Spearman ρ(ex-ante ★, realised yield) is recomputed every 10 pilots. Current ρ over 11-pilot window = 0.74 (non-decorative). Threshold: if ρ < 0.5 at a checkpoint, revise the formula. Tracked in `workspace/yield_formula_calibration_analytic.md`.
- 2026-05-29 — **Tracking commitment 2: counterfactual ranking against alternative yield formulas.** At each checkpoint also compute ρ under (a) max-impact-only, (b) max-novelty-only, (c) Sharpe-style E[yield]/σ, (d) EVoI-style. If any alternative beats the current formula by Δρ ≥ 0.1, switch. Current 11-pilot window: all alternatives rank below the current formula. Documented in the same calibration file.
- 2026-05-29 — **Corpus diversification landed**: `corpus_v26_diversification_2026_05_29` carries 60 future-resolving Metaculus binary questions + 30 FRED-constructed macro threshold contracts (all `post_training_cutoff=1`). Used for elicitation-consistency retests (bias smokes, channel orthogonality replication, wrong-channel inversion external N=42). Brier-calibration retests blocked until resolved-Metaculus outcome extraction works (resolution value absent in /api2/questions/; alternate endpoint deferred as task #40).
- 2026-05-29 — **Audit-code consolidation (leanmill side)**: v33 gates moved from `scripts/public/control/v33_*.py` to canonical `src/ztare/gates/v33_*.py` with backward-compat shims; Lane B audit script renamed `leanmill_lane_b_audit.py` → `leanmill_external_proof_audit.py` and all campaign-specific values (candidates dir, candidate glob, sidecar lean root, sidecar display name, drift signals, force-sidecar default) upleveled to `operations.external_proof_audit` in the factory policy; new `src/ztare/gates/lean_compile_primitives.py` hosts the canonical Lean compile + axiom-probe primitives; `src/ztare/leanmill/solver/contract.py` hosts the SolverActionContract building + validation + matched-negative-control primitives. The solver worker + canonical proof_audit now import from these libraries via thin wrappers.
