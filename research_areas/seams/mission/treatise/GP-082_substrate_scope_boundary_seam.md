# GP-082: Substrate Scope Boundary — Where Abductive Compression Works and Where It Breaks

> **Seam metadata** · `seam_id:` GP-082 · `track:` mission · `status:` `note` (seam opened, no experiment yet) · `last_updated:` 2026-05-08


**Status:** `note` (seam opened, no experiment yet)
**Track:** Theory / Substrate Scope
**Opened:** 2026-04-17
**Activation condition:** After GP-080 Stage 2 (noise injection) closes, regardless of outcome.

---

## The Question

The verification engine performs abductive compression: raw data in, algebraic law out, holdout survival as the discriminator. GP-080 (score 98, 24:3 compression, exact holdout match) proves this works on continuous bivariate substrates with clean data. The question is: what is the scope boundary of this capability?

Three levels of generalization, each with a different structural claim:

1. **Phenomenological discovery (Kepler).** Extract the exact compressed mathematical law from data without knowing why it holds. GP-080 is this. GP-023 (Planck) is this. The engine finds the formula; the physics comes after.

2. **Generative mechanism discovery (Newton).** Derive the law from deeper axioms. The engine currently cannot do this unless the axioms are injected into the evidence or rubric. This is what GP-081 (Peircean Pipeline) addresses — piping the abductive output into a deductive prover.

3. **Vocabulary-bounded discovery.** The engine can only discover laws expressible in the grammar the topology synthesizer provides. If the target law requires primitives the grammar doesn't have (complex numbers, tensor calculus, Lie groups), the engine will build Ptolemaic epicycles from the wrong math.

---

## The Inversion: Five Ways the Engine Fails on New Substrates

1. **Noise kills the hard gate.** An absolute RMSE threshold on noisy data fires on perfect models. Decisive for Stage 2. Fix: noise-relative threshold.

2. **Grammar starvation.** The topology synthesizer's primitive library (exp, log, power, rational, reciprocal, COMPOSE) is sufficient for classical continuous dynamics. It is not sufficient for quantum mechanics (requires complex exponentials), discrete mathematics (requires modular arithmetic), or algebraic geometry (requires group operations). The engine will find the nearest continuous approximation and score well on it, hiding the fact that the true law lives outside the grammar.

3. **Phase transition blindness.** The engine assumes the generating law is continuous. A substrate with a regime change (phase transition, structural break) will produce a model that fits one regime and fails catastrophically in the other. The holdout gate catches this only if holdout points span both regimes.

4. **Dimensional explosion.** GP-080 is bivariate (x1, x2). A substrate with 10+ independent variables will overwhelm the fit primitive (SciPy curve_fit doesn't scale well beyond ~8 parameters) and the mutator (LLMs lose structural reasoning above ~5 variables).

5. **Degenerate symmetry.** When the target law has internal symmetries (like GP-023 sandbox_06's alpha/beta quotient collapse), the engine finds A solution but not THE solution. The fit primitive converges to one basin; the identifiability check catches this only if multi-start is configured.

---

## The Compression: What Generalizes

Three properties of the engine that are substrate-independent:

1. **Separation of form selection from parameter fitting.** LLM picks form, SciPy fits params, harness evaluates. This works on any substrate where the form is expressible in the grammar and the parameters are real-valued.

2. **Holdout survival as the discriminator.** Any substrate where held-out data can be constructed (i.e., the generating process can be evaluated at unseen points) benefits from Principle VI. This is universal.

3. **Adversarial pressure on parsimony.** The judge penalizes complexity. This is Principle VII (asymptotic scoring) and is substrate-independent.

---

## The Planck Test (gp023)

Planck's discovery is the cleanest substrate swap for the engine. Planck had spectral data (intensity vs. frequency at fixed temperature). He needed to find B(v,T) = 2hv^3/c^2 * 1/(exp(hv/kT) - 1). This is a rational-exponential composition — expressible in the current grammar as `reciprocal(COMPOSE(exp, -1))` scaled by a power term.

The current grammar has: reciprocal, exp, COMPOSE with +, *, /. The composition `a / (exp(b*n) - 1)` requires: COMPOSE(reciprocal, exp - const). This is expressible but at depth 2.

gp023 sandbox_07 has already been run. Check its closure for whether the engine found the Planck form.

---

## String Theory

The Gemini analysis is structurally correct that if you redefine "data" as mathematical anomalies (scattering amplitudes, crossing symmetry violations) and the "gate" as a symmetry-checking harness, the engine becomes a pure mathematician. This is theoretically sound but requires:

1. A symmetry-checking gate harness (unitarity, anomaly cancellation) — not RMSE
2. Algebraic geometry primitives in the topology synthesizer
3. A rubric whose persona is a mathematical physicist, not a skeptical statistician

This is at least two infrastructure layers beyond current capability. File under "conditional on grammar extension."

---

## Debate Log

**Turn 1 (2026-04-17, Operator).** Opened after GP-080 hit 98. The question: does abductive compression generalize to physics substrates? Structural answer: yes for phenomenological discovery (Kepler), no for generative discovery (Newton) without GP-081, and bounded by grammar for everything else. The decisive next experiment is GP-080 Stage 2 (noise robustness), then gp023 sandbox_07 closure review, then a new substrate swap (non-PK, non-Planck) to test the three-property claim.

---

## Next Actions

1. Complete GP-080 Stage 2 (noise injection) — tests noise robustness
2. Review gp023 sandbox_07 closure — did the engine find the Planck form?
3. If both succeed: design a substrate swap on a qualitatively different domain (e.g., logistic growth, predator-prey, or a financial time series) to test whether the three generalizing properties hold outside the current two domains
4. If grammar starvation is hit: open a grammar extension spec for complex exponentials and modular arithmetic
