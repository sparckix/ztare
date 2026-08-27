---
description: "Architecture audit for model-discriminating research acquisition in JaggedThoughts."
---

# JaggedThoughts × Model Discovery Agent architecture audit

**Status:** architecture audit and bounded activation proposal  
**Date:** 2026-08-25  
**Scope:** public-market research acquisition and private-company operating experiments. This does not alter GP-252 or grant capital-allocation authority.

## Bottom line

The Model Discovery Agent (MDA) is relevant to JaggedThoughts, but its useful contribution is narrower than “apply Bayesian experiment design to markets.” MDA maintains competing mechanistic structures, fits uncertainty within each structure, chooses the next controlled probe from cross-structure predictive disagreement, predicts before observing, and reopens structure search when every incumbent model misses. That is a strong template for an institution that learns.

ZTARE already has carriers for structure proposal, typed research programs, guarded experiment identity, finite categorical structure beliefs, prospective forecasts, external settlement, residual-driven reopening, and shadow policy tournaments. It does **not** infer a calibrated market-structure prior, perform SMC/SBI, or supply a broad-equity likelihood/simulator. Adding those inference components would require a defensible generative contract that broad qualitative public-equity theses do not yet supply.

The first useful activation is now implemented: before activation research receives web access, a separate web-disabled subscription call freezes a categorical probability vector for every thesis × rival × null response across the research-question frontier. A finite uniform-design belief ranks questions by posterior-predictive mutual information per declared source-call unit; the guarded categorical selector remains an internal control. The browsing agent receives the executed program and hash-bound assignment, never the response matrix or rival predictions. Later source-bound evidence updates the finite weights. These are elicited design probabilities and declared cost estimates, never calibrated conviction, measured acquisition efficiency, expected return, alpha, or inferred market-structure evidence.

Its evaluation is a nested activation experiment because this choice occurs after initial discovery and dossier construction. Each adjacent-rank pair receives an independent frozen arm coin before browsing. The dossier must copy its execution identity, and settlement rejects another program. The policy outcome is realized information bits per declared source-call unit; committee-wide failure scores zero and opens a new model-set epoch. Reviews occur only at 20 × 2^k completion-ordered pairs under a geometric alpha-spending budget, with a declared useful-effect and power boundary. Between looks the reviewed population stays fixed. A qualifying winner may receive 80% of later activation questions while 20% remain an audit arm; neither policy can select a security or change capital.

## The paper's exact loop

[Murphy's MDA paper](https://arxiv.org/abs/2608.09696) defines an experiment as an initial state, an intervention on mechanism parameters, and an input/control sequence. Its [algorithms and likelihood constructions](https://arxiv.org/pdf/2608.09696) implement this loop:

1. An LLM proposes a pool of executable mechanistic model structures.
2. Each structure's parameters are inferred with adaptive-tempering sequential Monte Carlo (SMC); marginal likelihood supplies model evidence and therefore a posterior over structures.
3. The next experiment maximizes an approximation to expected information gain: noise-whitened between-model posterior-predictive variance, averaged over within-model parameter particles.
4. Before observation, the agent may predict a task query. It then executes the chosen experiment, observes the response, and computes a prequential query or summary residual.
5. A large residual re-enables LLM structure proposal. New structures are conditioned on the previous pool and its residuals, then evidence-pruned with incumbents.
6. Deterministic trace likelihood, particle-filter likelihood, or synthetic likelihood/SBI is selected according to the environment.

Two qualifications matter for transfer. The reported benchmarks are controlled interactive scientific systems with agent-addressable interventions. The paper's reported runs use summary residuals rather than the preferred query residual; it notes that lossy summaries could collude with a model class by omitting the decision target. JaggedThoughts should require a prospective decision-query response, with summary checks only as diagnostics.

## Existing carrier map

| MDA identity and job | Existing ZTARE carrier | Fit and boundary |
|---|---|---|
| Structure proposer | `src/ztare/validator/autoresearch_loop.py` | LLM candidate synthesis, residual prompts, Newton/Lagrangian modes, and candidate preflights. No Bayesian structure posterior. |
| Grammar-constrained structure search | `src/ztare/composition/symbolic_regression_synthesizer.py` | Typed AST search, holdout gate, and residual failure packages. Suitable when the hypothesis is an executable expression. |
| Public-market query grammar and frontier | `src/ztare/investment/research_questions.py` | Recursively enumerates one- and two-probe programs and takes a Pareto frontier over decision relevance, rival discrimination, coverage, and source efficiency. It explicitly marks information gain as unestimated. |
| Experiment identity, costs, guards, and equivalence | `src/ztare/common/guarded_experiment_protocol.py` | Sealed protocol/assignment identities, explicit cost dimensions, guard admission, and canonicalization by induced prediction partition. Closest common carrier for acquisition choice. |
| Finite structure belief and question price | `src/ztare/common/finite_structure_belief.py`, `src/ztare/common/information_yield_pricing.py` | Freezes caller-supplied model weights and categorical predictions, computes exact posterior-predictive mutual information per cost, and performs source-bound categorical updates. Committee-wide failure terminates the model-set epoch. It does not infer or calibrate the starting weights. |
| Prospective response matrix | `src/ztare/investment/prospective_response_matrix.py` | Freezes the complete rival-model × research-program response matrix before acquisition, lowers it to guarded protocols, settles the assigned dossier response, and compiles matched incumbent-versus-matrix policy evidence. No capital authority. |
| Public-source acquisition and dossier settlement | `src/ztare/investment/research_jobs.py` | Binds candidate, selected question frontier, acquisition budgets, dossier, rival view, decisive observation, falsifiers, source timestamps, and outcomes in the existing alphabet `supports_thesis`, `supports_rival`, `mixed`, `unresolved`. Selection authority is limited to research. |
| Subscription chronology | `src/ztare/investment/research_agent.py` | Runs the response forecast with `web_research=False`, persists its hash, then starts the browsing activation role and settles the frozen cells from source-bound dossier outcomes. |
| Prospective forecast and point-in-time comparison | `src/ztare/worldmodel/evaluation.py` | Immutable forecasts, external episode settlement, chronology checks, complete candidate-by-episode matrices, and conservative paired comparisons. |
| M-open residual routing | `src/ztare/worldmodel/engine_router.py` | Routes unresolved disagreement and holdout residuals back to open-world/autoresearch paths. It is deterministic routing rather than a predictive posterior check. |
| Active distinguishing play | `src/ztare/worldmodel/distinguishing_play.py` | Chooses a play from version-space disagreement and prunes hypotheses after observation. Directly applicable only where the agent may control the environment. |
| Prospective acquisition-policy evaluation | `src/ztare/investment/research_budget_tournament.py` | Shadow arms, frozen assignments, source-bound settlement, decision-impact-per-cost outcomes, independent blocks, confidence intervals, and multiplicity control. Correct first landing surface. |
| Strategy adoption and outcome linkage | `src/ztare/investment/strategy_learning.py` | Exact adoption events, outcome contracts, and causal-readiness boundaries. |
| Causal law evaluation | `src/ztare/investment/institutional_learning.py` | Source-bound panels, cohorts, DiD evaluation, and parallel-trend diagnostics. Evaluation carrier; observational adoption is not an assigned intervention. |
| Fitting and complexity control | `src/ztare/fit/fit_primitive.py`, `src/ztare/fit/mdl.py` | Parameter fitting plus BIC/MDL-style penalties. Neither integrates parameter uncertainty into model evidence. |

## Core autoresearch comparison

The overlap is substantial, but the engines adjudicate candidates differently.

| Capability | MDA v4 | ZTARE as built | Verdict |
|---|---|---|---|
| Open-ended structure proposal | The LLM proposes executable mechanisms conditioned on the whole prior pool and its residuals. | Autoresearch mutates executable Python, typed ASTs, Newton laws, Lagrangian declarations, or world-model carriers from residual and weakest-link surfaces. | ZTARE is broader in candidate languages and failure routing. |
| Candidate authority | Marginal likelihood integrates parameters; an outer posterior weights structures. | Deterministic grammar, replay, holdout, residual, rubric, and kernel gates dispose candidates; LLM judging is bounded by those gates. | MDA has the stronger uncertainty semantics when a defensible likelihood exists. |
| Complexity | Integrated evidence supplies an Occam factor, augmented by `exp(-lambda * free_parameter_count)`. | BIC/MDL ranks fitted forms, tracks DAG/program description length, measures compression progress, and retires non-compressing reusable artifacts. | ZTARE has the wider compression institution; MDA has Bayesian evidence rather than point-estimate approximations. |
| Experiment value | `MODEL` prices between-structure disagreement; `JOINT` also prices within-structure parameter uncertainty; `TASK` prices information about a target functional on a query distribution. | The common kernel prices model-outcome mutual information, expected committee description-length retirement, novelty, residual information beyond a baseline, and learned task credit. `posterior_predictive_task_information_bits` now supplies the exact finite categorical `TASK` analogue and is consumed by the household mandate frontier. | MODEL and finite TASK exist. JOINT needs parameter particles; target contracts are absent from most JaggedThoughts acquisition menus. |
| M-open reaction | A prequential target-space miss beyond a threshold triggers another LLM structure proposal and full-pool refit. | Information-yield stagnation, holdout residuals, committee refutation, zero-mass outcomes, and engine routing trigger pivot, underidentification, or autoresearch. | Similar outer reaction; ZTARE does not yet use a calibrated posterior predictive check to trigger it. |
| Prediction | Bayes model averaging over structures and parameter particles. | Champion, committee, tournament, or separately compiled forecast paths. | Model averaging is missing where members have statistical likelihoods. |

NumPyro is an executable probabilistic-program representation and inference
runtime, not the contribution by itself. A NumPyro-shaped leaf without a
generative contract, point-in-time observations, calibration checks, and a
target query would add syntax while leaving the discovery claim unsupported.

The current division of labor is therefore:

| Tool | Job in ZTARE | Add now? |
|---|---|---|
| SymPy | simplify, differentiate, solve, and canonicalize candidate symbolic laws before validation | already used |
| exact finite Bayes | update a small frozen model committee and price MODEL/TASK information | already used |
| particle filter | infer a latent state trajectory inside one specified state-space model | only with a typed transition and observation likelihood |
| SMC / SMC² | approximate parameter, latent-state, and possibly outer structure uncertainty when exact integration is intractable | leaf backend after a matched calibration win |
| NumPyro | express and execute differentiable probabilistic models with supported inference algorithms | optional backend, never a kernel dependency |

SymPy and SMC are complementary. SymPy can propose or normalize the equation;
SMC can represent uncertainty over that equation's parameters and hidden state.
Neither supplies the observation model, causal identification, or investment
advantage by itself.

## JaggedThoughts utilization audit

JaggedThoughts uses more of the common apparatus than a cold reading suggests:

- the prospective thesis-response matrix freezes model weights and stochastic
  predictions before browsing, ranks source questions by posterior-predictive
  mutual information per declared source-call unit, and updates the finite
  belief after source-bound settlement;
- the learning scheduler prices law-scope separation, expected law-description
  retirement, novelty, cohort gaps, and prospective world-model residuals;
- the market-state, company-path, and probability-current projects execute the
  main autoresearch runner through the signed-in Codex subscription transport,
  with Newton rubrics, chronological holdouts, BIC/parsimony pressure, and
  deterministic gates.

Three disconnects remain. First, a capital-cycle autoresearch job is deliberately
bounded to one mutator/judge iteration; repeated jobs can learn, but the main
cycle does not maintain one MDA-like posterior spanning those iterations.
Second, scheduler components are upper bounds and declared priors in different
units, so they do not yet arbitrate candidate generation versus evidence
acquisition versus settlement on a common expected-target-information-per-cost
currency. Third, the strategy frontier, valuation mechanisms, and Newton leaves
have separate committees; a strategy mechanism that forecasts a decision target
does not automatically enter a joint posterior with its rivals.

The right next integration is therefore a posterior-producing leaf contract,
not a NumPyro dependency in the kernel. The contract must name an executable
model, parameter prior, observation likelihood or simulator, experiment/action
space, downstream target functional, evidence epoch, and posterior predictive
diagnostics. Exact finite inference, conjugate inference, SMC, or SBI are leaf
backends behind that identity. No backend earns general use merely by existing.

## ARC-AGI-3 transfer

MDA cannot be assumed to multiply current ARC performance. The existing ARC
kernel already keeps executable transition candidates, prunes them by exact
replay, seeks a reachable disagreement frontier, validates held-out rollouts,
and has recovered all eight expressible synthetic environments without a false
ratification. On deterministic fully observed levels, hard version-space
elimination is cheaper and can be sharper than SMC.

The Bayesian inner engine becomes a credible upgrade for three ARC regimes:
noisy observations, partially observed latent state, or continuous/discrete
parameters shared by a model family. There it can preserve near-miss candidates,
separate structural uncertainty from parameter uncertainty, and choose actions
that improve the task prediction rather than maximize the raw count of distinct
next grids.

The discriminating harness is a four-arm sealed comparison on environments with
a known likelihood and hidden parameter or latent state:

1. current exact committee plus disagreement-frontier planning;
2. the same committee with exact finite Bayesian weighting;
3. parameter-particle `JOINT` and task-directed action selection;
4. SMC only when exact inference is intractable.

Measure held-out interventional log loss, task completion per environment step,
false ratification, model recovery where identifiable, and compute. Promotion
requires an advantage over both the current kernel and the exact finite arm.
An SMC win only over uniform random action is insufficient.

## Missing carriers

The prospective response contract is implemented. Three missing identities remain for the fuller MDA comparison:

1. **Calibrated structure belief producer.** The common pricing kernel can consume nonuniform structure weights and stochastic predictions, but no reusable producer infers those weights or within-structure parameter beliefs from evidence. Confidence fields and uniform committees cannot substitute for this identity.
2. **Likelihood/simulator contract.** SMC/SBI requires an executable generative model, observation model or simulator, summary identity, and calibration checks. This is absent for broad qualitative public-market theses.
3. **Private-operation authority adapter.** `GuardedProtocolAssignment` seals an assignment, but private-company intervention needs an external receipt for owner authority, affected units, consent/legal review where applicable, risk limit, reversibility, stop rule, and execution scope.

The first two remaining items should be added only for a domain where prospective outcomes demonstrate calibration and an executable simulator or likelihood exists. The authority adapter is mandatory before any operating intervention.

## Smallest market-safe activation

The implemented carrier supplies the first five legs of a shadow arm named `prospective_committee_acquisition`:

1. Take already-compiled frontier programs from `research_questions.py`.
2. Lower each program into `GuardedExperimentProtocol`: source plan as preparation; atom/program as probe; candidate and decision boundary as target; source calls as cost; public-source/currentness rules as guards; irreversibility fixed at zero.
3. Freeze a committee containing the source-bound thesis, rival view, and at most one explicit null/control. Before fetching, each member predicts one of `supports_thesis`, `supports_rival`, `mixed`, or `unresolved` for every eligible program and cites its rationale inputs.
4. Rank the complete stochastic predictions by posterior-predictive mutual information per declared source-call unit. Retain `select_guarded_protocol` as the categorical-partition control diagnostic.
5. Fetch only public information through the existing research job. Settle the selected program against timestamped dossier evidence, update model weights from its observed categorical response, and score realized information bits per declared source-call unit. Actual acquisition-call calibration remains absent; decision impact is a separate diagnostic.
6. Freeze a matched activation-policy assignment before the browsing call. One arm executes the incumbent frontier program; the other executes the matrix-selected program. Only the executed question is scored.
7. Compile exact paired settlements in immutable completion order. Review only at 20 × 2^k pairs, spend familywise alpha geometrically across looks, and require the look-adjusted confidence interval to clear the declared useful information-per-declared-source-call-unit delta plus its power boundary. Between looks, newly settled pairs are collected but do not change the reviewed sample.
8. After a winner, route 80% of future activation questions to it and retain a 20% audit arm. Research-budget scheduling remains a different question and keeps its existing tournament.
9. If every frozen committee member misses, or the observation falls outside the response alphabet, route to the existing open-world/autoresearch path and begin a new thesis epoch. A structure proposed after seeing the outcome must earn support prospectively in later acquisitions.

This activation uses public evidence acquisition as the controllable action. Buying a security is not treated as a causal experiment, and passive market observations do not receive intervention language.

## Private operations boundary

For a controlled portfolio company, the same abstract loop may choose an operating experiment only after the missing authority adapter issues a valid receipt. The experiment then lowers to `GuardedExperimentProtocol`, is assigned through `GuardedProtocolAssignment`, and is evaluated through strategy/institutional learning. Public-market and private-operation actions share hypothesis, response, cost, guard, forecast, and settlement identities; they have different authority adapters. No public-equity adapter may lower a research question into a company or market intervention.

## Acceptance and kill conditions

The activation earns promotion only if a scheduled sequential review shows that realized information bits per declared source-call unit clear the incumbent by the declared useful-effect threshold, look-specific alpha boundary, confidence interval, and power requirement. Proper predictive scores, decision impact, redundant acquisition, rival resolution, and out-of-alphabet outcomes remain diagnostics rather than substitute objectives. Calibration against actual acquisition-call receipts remains future work.

Kill or redesign the arm if its advantage disappears under candidate-time blocking, predictions are written after source access, committee members collapse to paraphrases of one thesis, or the score mainly rewards source availability. Do not add SMC/SBI merely to mirror MDA: first require a market subdomain with an executable simulator/likelihood, timestamped prospective observations, calibration diagnostics, and evidence that posterior weighting beats the uniform committee out of sample.

## Operating verification

The 2026-08-22 capital cycle completed through the same public-source and
subscription-agent path used by the periodic service. It froze the stochastic
matrix before browsing, advanced four ambiguous filings through a sealed Codex
subscription call with web and shell disabled, rebuilt content-and-transform
addressed SEC event/outcome lakes, and compiled the causal-law frontier. A
chronology guard exposed SEC facts whose filed date preceded the claimed period
end; the parser now excludes them and versions that rule in the transform hash.
This verifies the loop's execution and failure routing. It supplies no return-
advantage result; the matched stochastic challenger and strategy-path tournament
still require later settlements.

## Decision

Adopt MDA's **learning-loop shape**, not its inference machinery wholesale. The common information-yield kernel now accepts posterior-weighted stochastic predictions, includes finite task-directed mutual information, and reproduces the prior uniform deterministic result exactly. The prospective response contract, matched assignment, subscription chronology, exact execution binding, paired learner, future routing rule, and workbench projection are implemented. SMC or SBI remains a leaf-owned inference method until a domain supplies an executable simulator or likelihood and demonstrates calibration. Lagrangian/Newton/autoresearch remain downstream structure proposers when residuals demand a new mechanism; they should not choose public-market evidence or allocate capital directly.
