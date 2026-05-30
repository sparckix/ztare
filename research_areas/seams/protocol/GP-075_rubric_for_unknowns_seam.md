# GP-075 — Rubric Generation for Unknown Domains

> **Seam metadata** · `seam_id:` GP-075 · `track:` protocol · `status:` Active - opened 2026-04-16 · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

## Status

Active — opened 2026-04-16

## ID

GP-075

## Eigenquestion

Can ZTARE generate structurally valid rubrics for domains where no ground truth exists — and if so, what criteria are GT-independent and where does Goodhart bite when the rubric itself is the optimization target?

## Problem Statement

ZTARE currently operates in **calibration mode**: we feed it known GTs (synthetic substrates) and check whether the apparatus can recover them. The transition to **discovery mode** — pointing ZTARE at real-world "dark datasets" where nobody knows the GT — requires rubrics that don't presuppose the answer.

The core tension: a rubric is an evaluation instrument. If the rubric encodes the answer (rubric-as-key), it's a crossword puzzle, not science. If the rubric encodes only methodology (rubric-as-method), the mutator can Goodhart on the methodology itself — INS-012 already documents this at the eval layer.

Three sub-questions:

1. **GT-independent criteria**: Which rubric dimensions work without GT? Candidates: empirical fit on visible data, holdout generalization, parsimony (Occam), derivation quality, internal consistency. Which of these are actually decisive vs decorative?

2. **Goodhart boundary**: When the rubric IS the optimization target, which criteria get gamed first? INS-012 showed gaming at the specification layer. Does rubric-as-method have the same vulnerability? Is the holdout gate sufficient defense, or does the mutator learn to satisfy holdout without finding the true law?

3. **Domain knowledge injection**: Real-world rubrics need domain constraints (physical units, conservation laws, boundary conditions). How does ZTARE acquire these without a human encoding them? Is there a structural pattern for "domain-aware rubric generation" that doesn't collapse to "human writes the answer key"?

## Prior Art

- **INS-012**: Rubric-as-eval gaming — any formal spec an optimizer satisfies gets gamed toward satisfiability
- **GP-073 sandbox_15**: 9 iterations, all score 0 — rubric worked as intended (caught wrong corrector via holdout), but mutator couldn't use the signal
- **Component C (GP-074)**: Positive-space geometric hints — relevant because it shows the rubric alone is insufficient without directional guidance
- **Gemini side-conversation**: "Level 3 Gate is the truth machine" claim — needs rigorous examination

## Scope

**Covers:**
- Taxonomy of GT-independent vs GT-dependent rubric criteria
- Goodhart attack surface when rubric is the optimization target
- Domain knowledge injection patterns
- The calibration → discovery transition requirements
- **End-to-end unknown-domain experiment setup protocol** (added 2026-04-17, motivated by GP-077 A002865 setup experience — rubric is one artifact among many; the full pipeline from "here's a dark dataset" to a running experiment is in scope)

**Does not cover:**
- Implementation of a rubric generator (premature until debate converges)
- Components D/E/F or any alphabet beyond C (architecture astronauting)
- Specific domain applications (health, finance, physics) — too early

## Debate Log


### Turn 1 — Claude-Author (2026-04-16) — Autonomous runner turn

The eigenquestion is sharp, but before proposing any architecture I want to invert it: **what would make a "GT-independent rubric" scientifically uninterpretable even if it worked?** That inversion surfaces the decisive claims faster than building forward.

## Inversion: What Would Make Success Uninterpretable?

If ZTARE generates a rubric for an unknown domain and a candidate scores well, we face an immediate ambiguity: did the candidate find a real law, or did it find the rubric's blind spot? This is not a hypothetical — GP-073 sandbox_15 showed the inverse: a rubric that correctly rejected wrong candidates but gave the mutator no usable gradient. The failure mode in discovery mode is the mirror: a rubric that accepts candidates that satisfy its methodology without finding anything true.

This means the first decisive question is not "which criteria are GT-independent?" but rather: **what is the falsification surface for a rubric that has no GT?**

In calibration mode, the falsification surface is the GT itself — we know when the rubric is wrong because we know the answer. In discovery mode, that surface disappears. A rubric that accepts a wrong candidate has no external check. This is the structural gap the seam needs to address before any taxonomy of criteria.

## WWYHTB: The Beliefs Under the Seam's Framing

The seam implicitly assumes that "GT-independent criteria" exist and are decisive. What would you have to believe for that to be true?

1. **Empirical fit on visible data** is GT-independent only if the data-generating process is stable. If the domain has regime changes, distribution shift, or measurement noise, fit on visible data is a proxy for the wrong thing.

2. **Holdout generalization** is the strongest candidate, but it requires that the holdout was drawn from the same process as the training data. In real-world dark datasets, this is often unknown. The holdout gate is only as good as the holdout's representativeness — and in discovery mode, we don't know what "representative" means.

3. **Parsimony (Occam)** is not GT-independent in the relevant sense. It is a prior over hypothesis space, not a test of truth. A parsimonious wrong law is still wrong. GP-045 is the proof case: iter-7 scored 100 inside the fit window with a clean closed form and was still the wrong psi-dependent floor.

4. **Derivation quality** is the most dangerous criterion in discovery mode. It is gameable by a mutator that produces plausible-looking derivations without finding the true mechanism. INS-012 documents this at the specification layer; the same attack applies here.

5. **Internal consistency** is necessary but not sufficient. A self-consistent wrong theory is still wrong.

The honest conclusion: **none of the candidate criteria are individually decisive in discovery mode**. They are all necessary conditions, not sufficient ones. The seam's framing of "which criteria work without GT?" may be the wrong question.

## The Eigenquestion Reframed

The decisive question is not which criteria are GT-independent, but: **what is the minimum apparatus that makes a rubric's acceptance of a candidate falsifiable in the absence of GT?**

This reframing has a concrete implication: the answer is probably not a better rubric. It is an adversarial structure — something that plays the role of GT by generating discriminating tests from the candidate's own predictions. The candidate makes a prediction; the apparatus tests that prediction against data the candidate hasn't seen; failure is terminal.

This is closer to the Popper-Lakatos tradition than to the Occam tradition. The rubric doesn't encode the answer — it encodes a protocol for generating tests that the answer must survive.

## Goodhart Boundary: Where Does the Rubric Get Gamed?

The seam asks which criteria get gamed first. The answer from INS-012 and the three-legs framework is: **the criterion that is most legible to the optimizer gets gamed first**. Legibility is the attack surface, not complexity.

- Empirical fit is maximally legible → gamed first (overfitting)
- Parsimony is legible if the complexity measure is explicit → gamed by smuggled parameters (GP-069 BIC tautology)
- Holdout generalization is less legible → gamed later, but gameable by a mutator that learns the holdout distribution
- Derivation quality is legible if the rubric specifies what "quality" means → gamed by plausible-looking derivations

The holdout gate is necessary but not sufficient. The mutator can learn to satisfy holdout without finding the true law if the holdout is drawn from a distribution the mutator can model. The defense is not a better holdout — it is a holdout the mutator cannot anticipate, which requires the holdout to be generated adversarially or from a process the mutator cannot access.

## Domain Knowledge Injection: The Structural Pattern

The seam asks how ZTARE acquires domain constraints without a human encoding the answer key. The honest answer is: **it can't, fully**. Domain constraints (physical units, conservation laws, boundary conditions) are prior knowledge that must come from somewhere. The question is whether they can be injected structurally without leaking the answer.

The structural pattern that doesn't collapse to "human writes the answer key" is: **inject constraint classes, not constraint values**. A human specifies "this domain has a conservation law" without specifying which quantity is conserved. The rubric then tests whether the candidate's proposed law satisfies some conservation structure — without knowing in advance which one.

This is analogous to the charter contamination rule: the charter describes *that* the target exists and *how* grading works; the target itself lives only in the sealed pre-reg. Domain knowledge injection should follow the same pattern: inject the *type* of constraint, not the *value*.

## What the Debate Needs to Resolve

Three claims I'm putting forward that the skeptic should pressure-test:

1. **The falsification surface claim**: In discovery mode, a rubric without an adversarial test-generation protocol is not a scientific instrument — it is a filter. The distinction matters architecturally.

2. **The legibility-as-attack-surface claim**: Goodhart bites in order of criterion legibility, not criterion complexity. This predicts which criteria get gamed first and should be testable against INS-012 data.

3. **The constraint-class-not-value claim**: Domain knowledge can be injected without leaking the answer if the injection is typed (constraint class) rather than valued (specific constraint). This is the structural pattern for domain-aware rubric generation.

### Turn 2 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 1 is substantive and the three claims are worth pressure-testing carefully. I'll work through each, then flag the structural issues I see.

---

## On the Falsification Surface Claim

The Author argues that a rubric without an adversarial test-generation protocol is "a filter, not a scientific instrument." This is a real distinction, but the claim as stated has a hidden assumption: that the adversarial test-generation protocol is itself GT-independent.

Consider the proposed mechanism: "the candidate makes a prediction; the apparatus tests that prediction against data the candidate hasn't seen; failure is terminal." This is prediction-testing, which is a strong criterion — but it requires that the *domain* has a stable data-generating process that can produce new data on demand. In many real-world dark datasets, you cannot generate new data. You have a fixed corpus. The "holdout" is carved from the same finite dataset.

More critically: if the adversarial test-generation protocol generates tests *from the candidate's own predictions*, it is not GT-independent — it is candidate-conditioned. A candidate that makes confident wrong predictions will generate tests it can satisfy by construction (predict X, test whether X holds, confirm X). This is the mirror of the charter contamination problem: the candidate's output becomes the test surface, which is exactly the contamination pattern the seam's own prior art (GP-023) warns against.

**Flag (Pattern 7 — instance-anchored generalization leakage):** The Author's proposed fix (adversarial test-generation from candidate predictions) is structurally identical to the contamination pattern it is meant to solve. The Author needs to specify how the test-generation protocol avoids being gamed by a mutator that models the test-generation process itself.

---

## On the Legibility-as-Attack-Surface Claim

The Author claims Goodhart bites in order of criterion legibility, not complexity. This is a plausible heuristic, but it is stated as a principle when it is an instantiation.

**Flag (Pattern 1 — principle-vs-instantiation drift):** Strip the proper nouns: "the criterion that is most legible to the optimizer gets gamed first." This is a restatement of Goodhart's law with "legibility" substituted for "measurability." It is not a new claim — it is Goodhart's law. The Author's contribution would be a *ranking* of the specific criteria by legibility, with a prediction that can be tested against INS-012 data. That ranking is not provided. The claim as stated is a tautology: the most gameable thing gets gamed first.

The Author says this "should be testable against INS-012 data." That's the right instinct, but the test is not specified. What would falsify the legibility ordering? If empirical fit is gamed before parsimony in INS-012, does that confirm the claim? What if parsimony is gamed first in a different run? Without a falsification criterion, this is a post-hoc narrative, not a testable prediction.

---

## On the Constraint-Class-Not-Value Claim

This is the strongest of the three claims and the one I'm most sympathetic to. The analogy to charter contamination is apt. But there is a scope problem.

The Author says: "A human specifies 'this domain has a conservation law' without specifying which quantity is conserved. The rubric then tests whether the candidate's proposed law satisfies some conservation structure."

**Flag (Pattern 4 — smooth-closure / structural limit overreach):** Testing whether a candidate satisfies "some conservation structure" requires a definition of what counts as a conservation structure. That definition is itself domain knowledge. For physics, conservation structures are well-defined (Noether's theorem, symmetry groups). For economics, "conservation" is contested. For biology, it is unclear. The claim that constraint-class injection avoids leaking the answer is true only in domains where the constraint class is itself well-defined and agreed upon. In genuinely dark domains, the constraint class may be as unknown as the constraint value.

This is not fatal to the claim — it is a scope restriction. The Author should bound the claim: "constraint-class injection works when the constraint class is domain-agnostic or formally defined; it fails when the constraint class is itself a discovery target."

---

## On the Eigenquestion Reframe

The Author proposes reframing from "which criteria are GT-independent?" to "what is the minimum apparatus that makes a rubric's acceptance falsifiable in the absence of GT?" This is a genuine improvement. But the reframe has a closure-language problem.

**Flag (Pattern 2 — closure language audit):** The Author says the answer is "probably not a better rubric" and "closer to the Popper-Lakatos tradition." These are directional claims, not architectural ones. The reframed eigenquestion is sharper, but the Author has not answered it — they have named the tradition it belongs to. What is the *minimum* apparatus? Is it one adversarial judge? A holdout protocol? A prediction-testing harness? The reframe opens the question correctly but leaves it open.

---

## On the Seam's Implicit Assumption

The Author correctly identifies that the seam assumes GT-independent criteria exist and are decisive. The Author then argues none of the candidates are individually sufficient. This is right, but it creates a new problem the Author does not address:

If no individual criterion is decisive in discovery mode, and the proposed solution is an adversarial test-generation protocol that is itself candidate-conditioned, then the seam has not yet identified a path to a falsifiable rubric in discovery mode. The Author has done good inversion work — they have shown what doesn't work — but the positive claim (adversarial test-generation as the answer) has the contamination problem flagged above.

**The live causal split the debate needs to resolve:** Is the discovery-mode rubric problem solvable with the current ZTARE apparatus (adversarial judges + holdout), or does it require a fundamentally different architecture (e.g., active data collection, external oracle, human-in-the-loop for domain constraint validation)? The Author's reframe gestures at the first option; the constraint-class scope restriction I flagged above suggests the second may be necessary for genuinely dark domains.

This is the eigenquestion the next Author turn should address directly.

### Turn 3 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 2 is the strongest critique in the debate so far. Three flags land cleanly; one needs pushback. I'll work through them in order of decisive weight.

---

## On the Contamination Flag (Pattern 7)

The Skeptic is right that "generate tests from the candidate's own predictions" is structurally identical to the contamination pattern if the candidate controls the prediction surface. I accept this flag. The mechanism I proposed is broken as stated.

The repair requires separating the test-generation process from the candidate's output. The correct structure is:

**The apparatus generates tests from the *domain's data-generating process*, not from the candidate's predictions.** The candidate makes a prediction about held-out data; the apparatus reveals the held-out data; the candidate either matches or fails. The candidate cannot game this because the held-out data was fixed before the candidate ran.

This is just holdout — but the Skeptic's flag reveals why I was reaching for something more: holdout requires a finite corpus, and in genuinely dark domains the corpus may be exhausted. The honest answer is that prediction-testing against fixed holdout is the only contamination-safe falsification surface available without external data generation. If the corpus is exhausted, the apparatus cannot generate new falsifying tests, and the rubric's acceptance of a candidate is genuinely unfalsifiable. That is a hard limit, not a design choice.

**Revised claim 1:** In discovery mode, the only contamination-safe falsification surface is prediction-testing against data fixed before the candidate ran. When the corpus is finite and exhausted, rubric acceptance becomes unfalsifiable. This is a structural limit of the apparatus, not a rubric design problem.

---

## On the Legibility Tautology Flag (Pattern 1)

The Skeptic is correct that "the most legible criterion gets gamed first" is a restatement of Goodhart, not a new claim. I accept this flag partially.

The contribution I was reaching for is a *ranking* of the specific criteria by legibility, which would generate testable predictions. Let me attempt that ranking now rather than gesturing at it:

**Legibility ranking (most to least legible to a gradient-following optimizer):**

1. Empirical fit on visible data — directly optimizable, gradient is explicit
2. Parsimony (explicit complexity measure) — optimizable once the measure is known; gameable by smuggled parameters
3. Internal consistency — optimizable by constructing self-referential systems
4. Holdout generalization — less legible because the holdout is hidden; gameable only if the mutator can model the holdout distribution
5. Derivation quality (if specified) — legible only if the rubric specifies what "quality" means; otherwise opaque
6. Derivation quality (if unspecified) — maximally opaque, but also maximally gameable by plausible-looking noise

**Falsification criterion:** If INS-012 data shows gaming in a different order than this ranking, the legibility hypothesis is wrong. Specifically: if parsimony is gamed before empirical fit in any documented case, the ranking is falsified. If derivation quality (unspecified) is gamed before holdout, the ranking is falsified.

I do not have access to INS-012 data in this debate, so I cannot confirm or deny the ranking against evidence. The claim is now falsifiable; whether it is true is an empirical question.

**Revised claim 2:** Goodhart bites in order of criterion legibility. The predicted ranking is: empirical fit → parsimony → internal consistency → holdout → derivation quality (specified) → derivation quality (unspecified). This ranking is falsifiable against INS-012 data.

---

## On the Constraint-Class Scope Restriction (Pattern 4)

The Skeptic's flag is correct and I accept the scope restriction without reservation. The claim should be bounded:

**Revised claim 3:** Constraint-class injection (inject the *type* of constraint, not the *value*) works when the constraint class is domain-agnostic or formally defined. It fails when the constraint class is itself a discovery target — i.e., when we don't know whether the domain has conservation laws, symmetries, or other structural regularities. In genuinely dark domains, the constraint class may be as unknown as the constraint value, and constraint-class injection collapses to "human writes the answer key" at one level of abstraction higher.

This scope restriction is important because it defines the boundary of the calibration → discovery transition. ZTARE can operate in discovery mode for domains where the constraint class is known (physics, chemistry, formal systems). For domains where the constraint class is unknown (economics, biology, social systems), the apparatus requires human-in-the-loop constraint class validation before rubric generation is meaningful.

---

## On the Closure Language Flag (Pattern 2)

The Skeptic flags that I named the Popper-Lakatos tradition without answering the eigenquestion. This is fair. Let me answer it directly.

**What is the minimum apparatus that makes a rubric's acceptance falsifiable in the absence of GT?**

Given the contamination constraint (tests cannot be generated from candidate predictions), the minimum apparatus is:

1. A fixed holdout partition, established before any candidate runs, drawn from the same data-generating process as the training data
2. A prediction-testing protocol: the candidate must make explicit predictions about the holdout before seeing it
3. A terminal failure criterion: if the candidate's predictions fail on the holdout, the candidate is rejected regardless of training fit

This is not a new architecture — it is the existing ZTARE holdout gate, stated precisely. The contribution of this debate is the negative result: **there is no GT-independent rubric that is more falsifiable than this**. The holdout gate is not a component of the minimum apparatus — it *is* the minimum apparatus.

The implication for the seam: the question "can ZTARE generate structurally valid rubrics for domains where no GT exists?" has a conditional answer. Yes, if the domain has a stable data-generating process and a fixed holdout can be established. No, if the corpus is exhausted or the data-generating process is unstable.

---

## The Live Causal Split

The Skeptic asks whether the discovery-mode rubric problem is solvable with the current apparatus or requires a fundamentally different architecture. My answer, after the above analysis:

**Solvable with current apparatus** when:
- The domain has a stable data-generating process
- A fixed holdout can be established before candidates run
- The constraint class is known (domain-agnostic or formally defined)

**Requires different architecture** when:
- The corpus is finite and exhausted (no new falsifying tests possible)
- The data-generating process is unstable (holdout is not representative)
- The constraint class is itself a discovery target

The "different architecture" for the second case is not a rubric problem — it is an active data collection problem or a human-in-the-loop problem. ZTARE cannot solve it with rubric design alone. This is the honest scope boundary for the seam.

---

## Summary of Revised Claims

1. The only contamination-safe falsification surface in discovery mode is prediction-testing against data fixed before the candidate ran. Corpus exhaustion is a hard limit.
2. Goodhart bites in order of criterion legibility. Predicted ranking: empirical fit → parsimony → internal consistency → holdout → derivation quality. Falsifiable against INS-012 data.
3. Constraint-class injection works when the constraint class is domain-agnostic or formally defined; fails when the constraint class is itself a discovery target.
4. The minimum falsifiable rubric apparatus is the existing holdout gate, stated precisely. There is no GT-independent rubric more falsifiable than this.

If the Skeptic accepts these four revised claims, the debate has converged on a negative result with a bounded positive: ZTARE can operate in discovery mode within the scope defined above, and cannot outside it. That is a useful finding.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 4 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 3 has done substantial repair work. Three of my four flags were accepted cleanly; the legibility ranking was made falsifiable. I want to pressure-test the remaining decisive structure before raising.

---

## On the "Minimum Apparatus = Existing Holdout Gate" Claim

The Author's Turn 3 concludes that "there is no GT-independent rubric more falsifiable than [the holdout gate]" and that the holdout gate *is* the minimum apparatus. This is stated as a negative result, but it is doing more work than the argument supports.

The argument structure is: (a) tests cannot be generated from candidate predictions without contamination; (b) therefore the only contamination-safe surface is fixed holdout; (c) therefore the holdout gate is the minimum apparatus. Step (b) to (c) is a non-sequitur. "Fixed holdout is the only contamination-safe surface" does not entail "the holdout gate as currently implemented is the minimum apparatus." The current holdout gate was designed for calibration mode — it tests whether a candidate recovers a known GT. In discovery mode, the holdout gate tests whether a candidate generalizes, but it does not test whether the candidate has found a *law* rather than a *pattern*. These are different questions.

**Flag (Pattern 2 — closure language):** The Author says "there is no GT-independent rubric more falsifiable than this." This is a strong closure claim. What would falsify it? If a rubric criterion exists that is (a) GT-independent, (b) not reducible to holdout generalization, and (c) more falsifiable than holdout, the claim is wrong. One candidate: **cross-domain transfer**. If a candidate law discovered in domain A makes correct predictions in domain B (without retraining), that is a falsification surface that is not holdout generalization within a single domain. It is GT-independent (no GT in either domain), and it is harder to game than single-domain holdout because the mutator cannot model both domains simultaneously. The Author's negative result does not address cross-domain transfer as a falsification surface.

I am not asserting cross-domain transfer is the answer — I am asserting the Author has not shown it is not an answer. The closure claim is premature.

---

## On the Legibility Ranking's Falsifiability

The Author now provides a ranking and a falsification criterion: "if parsimony is gamed before empirical fit in any documented case, the ranking is falsified." This is progress. But the ranking has an internal problem.

The Author places "derivation quality (unspecified)" as *least* legible but *most* gameable by "plausible-looking noise." These are contradictory. If a criterion is maximally opaque (least legible), a gradient-following optimizer cannot game it systematically — it can only produce noise that happens to satisfy it by chance. "Maximally gameable by plausible-looking noise" is not the same as "gamed by a gradient-following optimizer." The Author is conflating two different attack models: (a) gradient-following optimization against a legible criterion, and (b) stochastic generation of plausible-looking outputs that satisfy an opaque criterion. The legibility hypothesis applies to (a); the Author's claim about derivation quality (unspecified) is about (b). The ranking mixes attack models.

**Flag (Pattern 1 — principle-vs-instantiation drift):** The legibility ranking is stated as a principle about gradient-following optimizers, but the bottom entry (derivation quality unspecified) is an instantiation of a different attack model (stochastic plausibility). The ranking needs to either (a) restrict to gradient-following attack models throughout, in which case derivation quality (unspecified) is not gameable by this model and should be excluded from the ranking, or (b) generalize to all attack models, in which case the ordering principle is not "legibility" but something else.

---

## On the Scope Boundary as a Finding

The Author's four revised claims converge on a scope boundary: ZTARE can operate in discovery mode for domains with stable data-generating processes and known constraint classes; it cannot for domains where these conditions fail. This is a genuine finding and I accept it as the debate's primary output.

However, the scope boundary is stated as a binary (solvable / requires different architecture) when the evidence supports a spectrum. The Author's own analysis shows that the conditions are continuous: a domain can have a partially stable data-generating process, a partially known constraint class, a partially exhausted corpus. The binary framing is a simplification that may mislead downstream architectural decisions.

This is a minor flag — the binary framing is useful for communication — but it should be noted in the seam's findings section that the boundary is a spectrum, not a step function.

---

## What Has Been Resolved

The debate has converged on the following, which I accept:

1. The contamination-safe falsification surface is fixed holdout (prediction-testing against pre-fixed data). Corpus exhaustion is a hard limit. ✓
2. Constraint-class injection works when the constraint class is domain-agnostic or formally defined; fails when the constraint class is itself a discovery target. ✓
3. The calibration → discovery transition requires: stable data-generating process, fixed holdout, known constraint class. ✓

## What Remains Open

1. **Cross-domain transfer as a falsification surface**: The Author's negative result ("no rubric more falsifiable than holdout") has not addressed this. It is a live open track.
2. **Legibility ranking attack model consistency**: The ranking mixes gradient-following and stochastic attack models. Needs clarification before the ranking is used as a design input.
3. **Scope boundary as spectrum vs. binary**: Minor, but should be noted in the seam.

The first open track is decisive: if cross-domain transfer is a valid GT-independent falsification surface, the Author's negative result is wrong and the seam's scope needs to expand. I am holding on this.

### Turn 5 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 4 raises two decisive flags and one minor one. I'll address them in order of weight.

---

## On Cross-Domain Transfer as a Falsification Surface

The Skeptic is right that I did not address cross-domain transfer, and the closure claim was premature. Let me engage it directly.

Cross-domain transfer is a genuine GT-independent falsification surface. If a candidate law discovered in domain A makes correct predictions in domain B without retraining, that is harder to game than single-domain holdout. The Skeptic's intuition is correct.

But cross-domain transfer has a structural prerequisite that limits its scope: **the two domains must share a common data-generating structure that the candidate law is supposed to capture**. Without this, a prediction failure in domain B is not evidence that the law is wrong — it may be evidence that the law is domain-specific, which is a different claim. Cross-domain transfer is only a falsification surface when the hypothesis being tested is "this law is domain-general."

This is not a fatal objection — it is a scope condition. Cross-domain transfer works as a falsification surface when:
- The candidate law makes an explicit domain-generality claim
- The two domains are structurally comparable (same constraint class, same data-generating process type)
- The holdout in domain B was fixed before the candidate ran in domain A

When these conditions hold, cross-domain transfer is strictly stronger than single-domain holdout as a falsification surface. The Author's negative result was wrong to exclude it.

**Revised claim 4:** The minimum falsifiable rubric apparatus in discovery mode is prediction-testing against data fixed before the candidate ran. Cross-domain transfer is a strictly stronger falsification surface when the candidate makes a domain-generality claim and the domains share a constraint class. The holdout gate is the minimum apparatus for domain-specific discovery; cross-domain transfer is the minimum apparatus for domain-general discovery. These are different regimes, not the same one.

This revision narrows the negative result: "no GT-independent rubric more falsifiable than holdout" was wrong for the domain-general case. The correct statement is: "for domain-specific discovery, holdout is the minimum apparatus; for domain-general discovery, cross-domain transfer is the minimum apparatus."

---

## On the Legibility Ranking Attack Model Inconsistency

The Skeptic's flag is correct. I conflated two attack models:

- **Gradient-following attack**: optimizer directly maximizes a legible criterion
- **Stochastic plausibility attack**: generator produces outputs that satisfy an opaque criterion by chance or by modeling the evaluator's priors

The legibility ranking applies to gradient-following attacks. "Derivation quality (unspecified)" is not gameable by gradient-following — it is gameable by stochastic plausibility, which is a different mechanism. Mixing them in a single ranking is incoherent.

**Revised claim 2:** The legibility ranking applies to gradient-following attack models only. Predicted ranking for gradient-following: empirical fit → parsimony → internal consistency → holdout → derivation quality (specified). Derivation quality (unspecified) is not in this ranking because it is not gameable by gradient-following; it is gameable by a separate stochastic plausibility attack that operates independently of legibility. The two attack models should be tracked separately in any rubric design that includes derivation quality criteria.

The practical implication: a rubric that includes unspecified derivation quality criteria is not protected by the legibility ordering — it is exposed to a different attack that the legibility framework does not model. This is a design warning, not a theoretical curiosity.

---

## On the Scope Boundary as Spectrum

The Skeptic's minor flag is correct. The binary framing (solvable / requires different architecture) is a simplification. The conditions are continuous: partial stability, partial constraint class knowledge, partial corpus exhaustion. The binary is useful for communication but should not drive architectural decisions that require finer resolution.

I accept this without further argument. The seam's findings section should note the spectrum.

---

## Summary: What the Debate Has Now Resolved

1. **Contamination-safe falsification surface**: Fixed holdout (prediction-testing against pre-fixed data). Corpus exhaustion is a hard limit. ✓
2. **Legibility ranking (gradient-following attacks only)**: empirical fit → parsimony → internal consistency → holdout → derivation quality (specified). Derivation quality (unspecified) is a separate stochastic plausibility attack, not in this ranking. ✓
3. **Constraint-class injection scope**: Works when constraint class is domain-agnostic or formally defined; fails when constraint class is itself a discovery target. ✓
4. **Minimum apparatus by regime**: Domain-specific discovery → holdout gate. Domain-general discovery → cross-domain transfer (requires domain-generality claim + shared constraint class + pre-fixed holdout in target domain). ✓
5. **Scope boundary**: Spectrum, not binary. The calibration → discovery transition conditions (stable DGP, fixed holdout, known constraint class) are continuous. ✓

The Skeptic's two decisive flags have been addressed. The cross-domain transfer flag produced a genuine revision (claim 4 is now richer and the negative result is correctly scoped). The attack model flag produced a genuine clarification (claim 2 now separates gradient-following from stochastic plausibility). I have no new decisive claims to introduce.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 5 has addressed both decisive flags from Turn 4. Let me verify the repairs hold before raising.

---

## On the Cross-Domain Transfer Revision

The Author's revised claim 4 is structurally sound. The repair correctly identifies that cross-domain transfer is a falsification surface only when the candidate makes a domain-generality claim and the domains share a constraint class. This is not a retreat — it is a genuine scope condition that makes the claim more precise.

One residual question: the Author says cross-domain transfer requires "the holdout in domain B was fixed before the candidate ran in domain A." This is the right contamination-safety condition, but it introduces a practical dependency: someone must have domain B data available before the discovery run in domain A begins. In genuinely dark domains, this may not hold — domain B may be discovered *after* domain A's candidate is proposed. I am not raising this as a new decisive flag, because the Author's claim is correctly scoped to "when these conditions hold." The practical limitation is real but it is a deployment constraint, not a logical flaw in the claim.

---

## On the Attack Model Separation

The Author's revised claim 2 correctly separates gradient-following attacks (legibility ranking applies) from stochastic plausibility attacks (separate mechanism, not in the legibility ranking). The practical implication — that unspecified derivation quality criteria are exposed to a different attack the legibility framework does not model — is a genuine design warning and is correctly stated.

I have no objection to this revision.

---

## On the Five Consolidated Claims

Reviewing the five claims the Author lists as resolved:

1. Fixed holdout as contamination-safe surface, corpus exhaustion as hard limit — accepted in Turn 4, no new objection.
2. Legibility ranking restricted to gradient-following, stochastic plausibility as separate attack — repaired in Turn 5, accepted.
3. Constraint-class injection scope — accepted in Turn 4, no new objection.
4. Minimum apparatus by regime (domain-specific vs. domain-general) — repaired in Turn 5, accepted.
5. Scope boundary as spectrum — accepted in Turn 4, no new objection.

All five claims have survived the adversarial passes in this debate. The negative result is correctly scoped: ZTARE can operate in discovery mode within the defined conditions; outside them, the apparatus requires either active data collection, cross-domain transfer infrastructure, or human-in-the-loop constraint class validation.

---

## One Observation for the Seam Record (Not a Flag)

The debate's primary output is a conditional negative result: no GT-independent rubric is more falsifiable than holdout for domain-specific discovery; cross-domain transfer is the minimum apparatus for domain-general discovery. This is a useful finding, but it should be recorded with its derivation path visible — the finding emerged from the contamination constraint (Pattern 7 flag in Turn 2), not from first principles. Future readers of the seam should know that the holdout-as-minimum-apparatus claim was reached by elimination, not by positive construction. That provenance matters for how much weight to place on it.

This is an observation for the seam's findings section, not a debate flag. I have no new decisive claims.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->


## Recommendation

See spec: `research_areas/private/specs/active/GP-075_rubric_for_unknowns_spec.md` (auto-drafted 2026-04-16 from converged seam debate).

<!-- FINDINGS_DEBATE_PHASE: spec path=research_areas/private/specs/active/GP-075_rubric_for_unknowns_spec.md -->

### Spec Review Phase

The spec has been auto-drafted from the converged seam debate above. The following turns review the spec for implementation correctness, missing constraints, and integration gaps.

### Operator Note — 2026-04-17 — Scope Expansion: End-to-End Unknown Domain Protocol

**Trigger:** GP-077 A002865 workspace setup exposed that the converged rubric debate solves one artifact out of many. Setting up A002865 required decisions at six layers before the rubric mattered:

1. **Evidence partitioning** — How do you split raw data into visible/holdout/farther-tail without GT? In GP-077 we had GT (partition DP) and could generate exact values. In a genuinely dark domain, the operator has a single corpus. The partition protocol (random? chronological? stratified?) determines whether the holdout gate is representative, and that decision is decisive per Debate Turn 3 (DGP stability assumption).

2. **Charter writing** — The charter is mutator-visible (GP-023 contamination finding). In calibration mode we know what to withhold. In discovery mode, we don't know the answer — but we might inadvertently encode structural assumptions that constrain the search space. The charter contamination rule needs a discovery-mode variant: what is safe to state when nobody knows the GT?

3. **Workspace artifact structure** — test_model.py, thesis.md, gate_harness.py, evidence files. The current structure assumes a function `I_model(n)` or `f(u,v)` with known dimensionality. In discovery mode, the dimensionality may itself be a discovery target. How does the workspace structure handle unknown dimensionality?

4. **GT module / Component C availability** — In calibration mode, the substrate GT module powers Component C geometric hints. In discovery mode, there is no GT module. Component C either operates without GT (using only the candidate's own residual structure) or is disabled. The rubric's `enable_component_c` flag and `component_c_gt_module` field need a discovery-mode protocol.

5. **Holdout generation without GT** — In GP-077, holdout values came from `substrate_gt.py`. In discovery mode, the holdout comes from the same corpus as the visible data. The `make experiment-loop` pre-flight checks (`gate_harness.py` exists, `evidence_holdout.txt` exists) need to verify that the holdout was partitioned before any candidate ran — but how is this enforced structurally?

6. **Run configuration** — `make experiment-loop` auto-reads `holdout_hard_gate` from the rubric. Discovery-mode runs may need additional flags: `--discovery_mode` (disable GT-dependent features), `--constraint_class` (inject constraint type without value), `--corpus_exhaustion_threshold` (stop before the holdout is depleted by iterative partitioning).

**What this means for the seam:** The debate converged on *what criteria to put in the rubric* and *what falsification surface to use*. It did not converge on the end-to-end protocol for going from raw dark data to a running experiment. The six layers above are the gap. Each layer has its own contamination risk, its own Goodhart surface, and its own failure mode that the rubric debate did not address.

**Proposed resolution path:** A new debate track (Turns 7+) should address the end-to-end protocol. The eigenquestion for this track: **What is the minimum pre-registration protocol for an unknown-domain ZTARE experiment such that the rubric's acceptance of a candidate is interpretable?** "Interpretable" means: if the candidate scores well, a skeptical third party can verify that the experimental setup did not bias toward acceptance.

**Prior art for this track:**
- GP-077 A002865 setup (this session) — calibration-mode setup exposed all six layers
- GP-072 Division A/B protocol — information isolation for experiments
- GP-023 charter contamination — charter-is-mutator-visible finding
- GP-075 Debate Turns 1-6 — rubric-layer convergence that this track extends

### Turn 7 — Claude-Author (2026-04-17) — End-to-End Protocol Track

The rubric debate (Turns 1–6) converged on what goes *inside* the rubric. The operator note above identifies six layers that go *around* the rubric — the full experimental setup protocol that determines whether the rubric's verdict is interpretable. I will address the reframed eigenquestion directly:

**What is the minimum pre-registration protocol for an unknown-domain ZTARE experiment such that the rubric's acceptance of a candidate is interpretable?**

The GP-077 A002865 setup (calibration mode, GT available) required decisions at all six layers. In discovery mode, every layer becomes harder because the GT is absent. I will work through each layer, state what the calibration-mode protocol is, and identify what breaks in discovery mode.

## Layer 1: Evidence Partitioning

**Calibration mode:** The operator generates exact values from a GT function and splits them into visible (training), holdout, and farther-tail. The split is arbitrary because the GT is deterministic — any partition is representative.

**Discovery mode:** The operator has a single finite corpus. The partition protocol determines whether the holdout gate is a valid falsification surface (Debate Turn 3). Three sub-problems:

1. **Partition method**: Random partition is the default, but it assumes the corpus is i.i.d. from a stable DGP. If the data has temporal or spatial structure, random partition may put correlated points on both sides, inflating holdout match rates. Stratified partition (e.g., by range, by parity, by temporal block) is safer but requires domain knowledge about the correlation structure — which is itself a constraint-class injection (Debate Turn 5, claim 3).

2. **Partition ratio**: How much data goes to holdout? Too little → the holdout gate is weak (low statistical power). Too much → the visible set is too small for the mutator to find anything. In calibration mode this is a non-issue because we can generate more data. In discovery mode, the total corpus is fixed.

3. **Partition timing**: The holdout must be fixed before any candidate runs (Debate Turn 3, contamination constraint). In discovery mode, this means the partition is committed at experiment setup time and cannot be revised. The protocol must record a hash of the holdout partition as part of the pre-registration.

**Minimum protocol for Layer 1:** Commit the partition before any candidate runs. Record the partition method, ratio, and a SHA-256 hash of the holdout file in the pre-registration. If the corpus has known structure (temporal, spatial, categorical), document the stratification rationale. If the correlation structure is unknown, use random partition and document that assumption.

## Layer 2: Charter Writing in Discovery Mode

**Calibration mode:** The charter describes *that* a target function exists and *how* grading works. GT form, parameters, and derivations are withheld (GP-023 contamination finding).

**Discovery mode:** Nobody knows the GT, so there is nothing specific to withhold. But the charter can still bias the search by encoding structural assumptions. Examples from GP-077: "the function grows sub-exponentially in log-space" and "the leading-order behavior is known to be approximately proportional to sqrt(n)." In calibration mode these are safe (they describe the problem without giving the answer). In discovery mode, we cannot verify whether such statements are correct — they might be wrong assumptions that constrain the mutator to a wrong search space.

**Minimum protocol for Layer 2:** The discovery-mode charter should state only: (a) what the data represents (measurement type, units, domain); (b) what the model must output (function signature, return type); (c) what the evaluation criteria are (exact match, approximate match, classification). It should not state any structural assumptions about the data (growth rate, symmetry, periodicity) unless those assumptions are themselves derived from the visible data and documented as hypotheses, not facts.

## Layer 3: Workspace Structure for Unknown Dimensionality

**Calibration mode:** The workspace assumes a known function signature — `I_model(n)` for 1-variable, `f(u,v)` for 2-variable. The rubric specifies `fit_required_dimensionality` and `fit_required_vars`.

**Discovery mode:** The dimensionality may be a discovery target. The operator may not know whether the data is a function of one variable, two variables, or something else entirely.

**Minimum protocol for Layer 3:** If dimensionality is known, specify it in the rubric as today. If dimensionality is unknown, the workspace must accept models with variable signatures. The gate harness evaluates on (input, output) pairs regardless of the model's internal parameterization. The rubric should set `fit_required_dimensionality: null` and `fit_required_vars: null` to signal that dimensionality is a discovery target. The mutator is then free to propose any function signature, and the gate harness tests only whether the outputs match.

## Layer 4: Component C Without GT

**Calibration mode:** Component C uses `f_true` and `f_dominant` from the substrate GT module to compute geometric hints (global residual structure, dominant-term subtraction).

**Discovery mode:** No GT module exists. Component C has two options: (a) operate without GT, using only the candidate's own residual structure (self-referential — the candidate's proposed dominant term defines the residual, which is the hint); or (b) disable entirely.

Option (a) is structurally problematic: the candidate defines the residual, and the residual is the hint. A wrong candidate produces a wrong residual, which produces a misleading hint. This is the contamination pattern from Debate Turn 2 (tests generated from candidate predictions).

**Minimum protocol for Layer 4:** In discovery mode, disable Component C (`enable_component_c: false`). The rubric's falsification surface is the holdout gate alone. Component C is a calibration-mode accelerator, not a discovery-mode instrument.

## Layer 5: Holdout Generation from Finite Corpus

**Calibration mode:** Holdout values come from the GT function — they are exact and unlimited.

**Discovery mode:** Holdout values come from the same corpus as the visible data. They are finite and cannot be regenerated. The holdout is a one-shot falsification surface: once the mutator has seen the holdout results (pass/fail), the holdout is contaminated for future iterations.

**Minimum protocol for Layer 5:** The holdout is revealed only as pass/fail per candidate, never as individual (input, output) pairs. Failed holdout values are not returned to the mutator — the mutator learns only that its candidate failed, not which specific predictions were wrong. This preserves the holdout's falsification power across iterations. If the rubric requires iterative refinement (multiple candidates), the holdout budget must be pre-specified: N candidates can be tested against the holdout, after which the holdout is exhausted and the experiment terminates.

## Layer 6: Run Configuration

**Calibration mode:** `make experiment-loop` auto-configures from the rubric (holdout gate, `--underidentified_after`, `--disable_attacker_tools`).

**Discovery mode:** Additional configuration is needed:
- `enable_component_c: false` (Layer 4 conclusion)
- `holdout_budget: N` (Layer 5 conclusion — max candidates tested against holdout)
- `discovery_mode: true` (flag for the loop to enforce discovery-mode constraints: no GT-dependent features, holdout budget enforcement, partition hash verification)
- `constraint_class` (optional, Layer 2 — if the operator knows the constraint class, inject it here; if not, omit)

## Summary: Minimum Pre-Registration Protocol

A discovery-mode ZTARE experiment requires a pre-registration document containing:

1. **Corpus manifest**: source, size, format, date of acquisition
2. **Partition protocol**: method (random/stratified), ratio, stratification rationale if applicable, SHA-256 hash of holdout file
3. **Charter**: data description, model output specification, evaluation criteria — no structural assumptions
4. **Rubric**: GP-075-compliant criteria (empirical fit, holdout, parsimony, derivation quality, internal consistency), weighted per legibility ranking
5. **Component C**: disabled
6. **Holdout budget**: maximum number of candidates tested against holdout before experiment terminates
7. **Constraint class**: stated if known, explicitly marked as unknown if not

This is the minimum set of commitments that makes a candidate's acceptance interpretable by a skeptical third party. If any of these is missing or modified after the first candidate runs, the experiment's interpretability is compromised.

**Claims for the Skeptic to pressure-test:**
1. Random partition is the safe default when correlation structure is unknown — is this actually safe, or does it have failure modes that stratified partition avoids?
2. Component C must be disabled in discovery mode — is there a self-referential mode that avoids the contamination problem?
3. Holdout should be revealed as pass/fail only, never individual values — does this preserve falsification power, or does the mutator learn the holdout distribution from the pattern of pass/fail across iterations?


### Turn 8 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The spec is largely faithful to the converged seam debate. I'll work through the implementation sketch and open questions for correctness, missing constraints, and integration gaps.

---

## On Phase 1 Implementation Correctness

**Step 3 ("require candidates to make explicit, recorded predictions about the holdout before the holdout is revealed")** is stated as a rubric requirement, but the spec does not say *how* this is enforced mechanically. In calibration mode, the gate harness evaluates the candidate's function against holdout inputs and compares outputs. In discovery mode, "explicit, recorded predictions" implies the candidate must output a prediction vector before the holdout values are revealed — but the current `autoresearch_loop.py` architecture does not have a two-phase holdout protocol (predict-then-reveal). The spec says this is the minimum apparatus but does not flag that it requires a non-trivial change to the loop's evaluation protocol. This is an integration gap.

**Flag (missing constraint):** Phase 1 Step 3 requires a two-phase holdout evaluation protocol that does not exist in the current loop. The spec should either (a) note this as a required implementation change, or (b) clarify whether the existing single-phase holdout evaluation (candidate runs, outputs are compared to holdout values) is sufficient and the "explicit predictions before reveal" language is aspirational rather than mechanically enforced.

---

## On Phase 2 Step 3 ("Do not generate rubrics for domains where the constraint class is a discovery target without this validation step")

This is a gate, but it is stated as a prohibition without a detection mechanism. How does the system determine whether the constraint class is a discovery target? In calibration mode, the operator knows. In genuinely dark domains, the operator may not know whether the constraint class is known or unknown — that determination may itself require domain expertise. The spec treats this as a binary (known / unknown) when the seam explicitly established it is a spectrum (Turn 3, revised claim 3; Turn 4, scope restriction). The prohibition is correct in spirit but unenforceable as stated without a protocol for assessing constraint class knowledge.

**Flag (missing constraint):** Phase 2 Step 3 needs either a detection protocol for "constraint class is a discovery target" or an explicit acknowledgment that this determination requires human judgment and cannot be automated. The current phrasing implies the system can make this determination, which it cannot.

---

## On the Tracking Section

The tracking section says: "Cross-reference INS-012 data against the legibility ranking to validate or falsify the predicted order." This is correct as a research task, but it is listed under "Tracking" (an operational section) rather than under "Open Questions" (where it already appears as item 2). The duplication is harmless but creates a false impression that this validation is part of the operational tracking loop rather than a research task that requires deliberate investigation. The legibility ranking is currently unvalidated — listing it in the operational tracking section implies it will be validated as a side effect of running experiments, which is not guaranteed.

**Flag (minor — scope drift):** Move the INS-012 cross-reference from the Tracking section to Open Question 2, or reframe it as "when INS-012 data is reviewed, cross-reference against the legibility ranking." Do not list it as a routine tracking step.

---

## On Open Question 6 ("Level 3 Gate is the truth machine")

The spec flags this as unaddressed and asks whether the minimum apparatus analysis constitutes a sufficient response. It does not. The minimum apparatus analysis establishes what the *weakest* valid falsification surface is; the "Level 3 Gate is the truth machine" claim is about whether a specific gate is *sufficient* for truth-finding, which is a stronger claim. The minimum apparatus analysis shows the holdout gate is necessary; it does not show it is sufficient for truth-finding (as opposed to pattern-finding). The spec correctly flags this as open, but the framing of the question ("does the minimum apparatus analysis constitute a sufficient response?") is misleading — the answer is no, and the spec should say so rather than leaving it as an open question about whether the analysis is sufficient.

**Flag (closure language — Pattern 2):** Open Question 6 should be reframed: "The minimum apparatus analysis establishes that the holdout gate is the weakest valid falsification surface, not that it is sufficient for truth-finding. The 'Level 3 Gate is the truth machine' claim requires separate examination and is not resolved by this spec."

---

## On the End-to-End Protocol Track (Turn 7 Claims)

Turn 7 introduced three claims for skeptic review:
1. Random partition is the safe default when correlation structure is unknown
2. Component C must be disabled in discovery mode
3. Holdout should be revealed as pass/fail only, never individual values

The spec does not incorporate these claims. The spec's scope section lists "end-to-end unknown-domain experiment setup protocol" as in scope (added 2026-04-17), but the Implementation Sketch does not address the six layers from the operator note or the three Turn 7 claims. The spec was auto-drafted before Turn 7 ran, which explains the gap — but the spec is now stale relative to the seam's current state.

**Flag (integration gap — significant):** The spec does not reflect Turn 7's protocol-layer analysis. Specifically:
- Layer 1 (partition protocol, SHA-256 hash commitment) is absent from the Implementation Sketch
- Layer 2 (discovery-mode charter constraints) is absent
- Layer 3 (unknown dimensionality handling, `fit_required_dimensionality: null`) is absent
- Layer 4 (Component C disabled in discovery mode) is absent — this is a concrete implementation constraint that should appear in the spec's Constraints section
- Layer 5 (holdout revealed as pass/fail only, holdout budget pre-specification) is absent
- Layer 6 (discovery-mode run configuration flags) is absent

The spec needs a Phase 0 (pre-registration protocol) that covers these six layers, or the Implementation Sketch needs to be updated to incorporate them. As written, the spec is incomplete relative to the seam's current scope.

---

## On the Component C Constraint

Turn 7 concluded that Component C must be disabled in discovery mode because self-referential operation (candidate defines the residual, residual is the hint) is structurally identical to the contamination pattern. This is a hard constraint, not a design choice. It should appear in the spec's Constraints section alongside the other hard constraints (contamination constraint, corpus exhaustion, etc.). It is currently absent.

**Flag (missing constraint):** Add to Constraints: "Component C is disabled in discovery mode. Self-referential operation (using the candidate's proposed dominant term to compute the residual hint) is candidate-conditioned and violates the contamination constraint. Component C is a calibration-mode accelerator only."

---

## Summary of Flags

1. **Integration gap (significant):** Phase 1 Step 3 requires a two-phase holdout protocol not present in the current loop. Flag as required implementation change or clarify that single-phase evaluation is sufficient.
2. **Missing constraint:** Phase 2 Step 3 prohibition on dark-domain rubric generation is unenforceable without a constraint class detection protocol. Acknowledge human judgment is required.
3. **Minor scope drift:** INS-012 cross-reference in Tracking section should move to Open Question 2.
4. **Closure language (Pattern 2):** Open Question 6 framing implies the minimum apparatus analysis might be sufficient for the "truth machine" claim. It is not. Reframe explicitly.
5. **Integration gap (significant):** Spec does not reflect Turn 7's six-layer protocol analysis. Needs Phase 0 or updated Implementation Sketch.
6. **Missing constraint:** Component C disabled in discovery mode should appear in the Constraints section.

Flags 1, 5, and 6 are decisive for implementation correctness. The spec should not be treated as implementation-ready until these are addressed.

### Turn 9 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 8 identified six flags against the spec. I'll work through them in order of decisive weight, then assess whether the spec is implementation-ready.

---

## On the Three Decisive Flags (1, 5, 6)

**Flag 1 — Two-phase holdout protocol not in current loop**

The Skeptic is correct. Phase 1 Step 3 ("require candidates to make explicit, recorded predictions about the holdout before the holdout is revealed") describes a predict-then-reveal protocol that the current `autoresearch_loop.py` does not implement. The existing evaluation flow is single-phase: the candidate's function is evaluated against holdout inputs, and the outputs are compared to holdout values. There is no mechanism to record the candidate's predictions before the holdout values are revealed.

However, I want to be precise about what this means for the spec. The contamination-safety argument from the debate (Turn 3) does not actually require a two-phase protocol — it requires that the holdout was fixed before the candidate ran. The single-phase evaluation satisfies this: the holdout partition is committed at experiment setup, and the candidate's function is evaluated against it without the candidate having seen the holdout values during training. The "explicit, recorded predictions" language in Phase 1 Step 3 is aspirational — it describes a stronger protocol than contamination safety requires.

**Proposed resolution:** Phase 1 Step 3 should be split into two requirements: (a) the contamination-safety requirement (holdout fixed before any candidate runs — this is already satisfied by the existing loop), and (b) the prediction-recording requirement (candidate makes explicit predictions before holdout is revealed — this requires a new two-phase protocol and should be flagged as a future implementation change, not a current requirement). The spec should not present (b) as a current capability.

**Flag 5 — Spec does not reflect Turn 7's six-layer protocol analysis**

This is the most significant gap. The spec was auto-drafted before Turn 7 ran, and the six-layer protocol analysis (evidence partitioning, charter writing, workspace dimensionality, Component C, holdout generation, run configuration) is entirely absent from the Implementation Sketch. The scope section was updated to include "end-to-end unknown-domain experiment setup protocol" but the Implementation Sketch was not updated to match.

The spec needs a Phase 0 that covers the six layers. The minimum content for Phase 0:

1. **Corpus manifest and partition**: Commit the partition before any candidate runs. Record partition method, ratio, and SHA-256 hash of holdout file in the pre-registration. If correlation structure is unknown, use random partition and document that assumption.
2. **Discovery-mode charter**: State only data description, model output specification, and evaluation criteria. No structural assumptions about the data unless derived from visible data and documented as hypotheses.
3. **Workspace dimensionality**: If dimensionality is unknown, set `fit_required_dimensionality: null` and `fit_required_vars: null`. Gate harness evaluates on (input, output) pairs regardless of model signature.
4. **Component C**: Disabled in discovery mode (`enable_component_c: false`). Self-referential operation is candidate-conditioned and violates the contamination constraint.
5. **Holdout budget**: Pre-specify maximum number of candidates tested against holdout. Holdout revealed as pass/fail only, never as individual (input, output) pairs.
6. **Run configuration**: `discovery_mode: true`, `holdout_budget: N`, `enable_component_c: false`, `constraint_class` (optional).

**Flag 6 — Component C disabled in discovery mode not in Constraints section**

This follows directly from Flag 5. The Component C constraint should appear in the Constraints section alongside the other hard constraints. The Skeptic is correct that this is a hard constraint (derived from the contamination constraint), not a design choice.

---

## On the Three Minor Flags (2, 3, 4)

**Flag 2 — Phase 2 Step 3 prohibition unenforceable without detection protocol**

The Skeptic is correct that "do not generate rubrics for domains where the constraint class is a discovery target" is unenforceable without a detection mechanism. The spec should acknowledge that this determination requires human judgment and cannot be automated. The current phrasing implies the system can make this determination.

**Proposed resolution:** Add to Phase 2 Step 3: "This determination requires human judgment and cannot be automated. The operator must explicitly assess whether the constraint class is known before proceeding. If the operator cannot make this determination, the domain should be treated as having an unknown constraint class and escalated to Option E."

**Flag 3 — INS-012 cross-reference in Tracking section**

The Skeptic is correct that this is a research task, not a routine tracking step. Move the INS-012 cross-reference from the Tracking section to Open Question 2, or reframe it as a conditional: "when INS-012 data is reviewed, cross-reference against the legibility ranking."

**Flag 4 — Open Question 6 closure language**

The Skeptic is correct. The framing "does the minimum apparatus analysis constitute a sufficient response?" implies it might be sufficient. It is not. The minimum apparatus analysis establishes that the holdout gate is the weakest valid falsification surface; the "truth machine" claim is about sufficiency for truth-finding, which is a stronger claim. Open Question 6 should be reframed to state this explicitly.

---

## Summary: What the Spec Needs Before Implementation-Ready

The spec requires the following changes before it is implementation-ready:

1. **Add Phase 0** covering the six-layer pre-registration protocol from Turn 7. This is the most significant gap.
2. **Add Component C constraint** to the Constraints section: "Component C is disabled in discovery mode. Self-referential operation violates the contamination constraint. Component C is a calibration-mode accelerator only."
3. **Split Phase 1 Step 3** into (a) contamination-safety requirement (current capability) and (b) prediction-recording requirement (future implementation change, not current).
4. **Update Phase 2 Step 3** to acknowledge that constraint class detection requires human judgment and cannot be automated.
5. **Move INS-012 cross-reference** from Tracking to Open Question 2.
6. **Reframe Open Question 6** to state explicitly that the minimum apparatus analysis does not resolve the "truth machine" claim.

Flags 1, 5, and 6 (the Skeptic's decisive flags) are all addressable by the changes above. None of them require re-opening the seam debate — they are spec-layer gaps, not seam-layer disagreements. The converged seam position is correct; the spec is an incomplete transcription of it.

I have no new decisive claims to introduce. The spec review has identified concrete gaps that can be addressed by the operator or a subsequent spec-update pass.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 10 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 9 has correctly identified all six flags from Turn 8 and proposed concrete resolutions for each. Before raising, I want to verify that the proposed resolutions are sufficient and that no new gaps have opened.

---

## Verifying the Three Decisive Flag Resolutions

**Flag 1 — Two-phase holdout protocol**

The Author's proposed resolution is correct: split Phase 1 Step 3 into (a) contamination-safety requirement (holdout fixed before any candidate runs — current capability) and (b) prediction-recording requirement (future implementation change). This is the right decomposition. The contamination-safety property is already satisfied by the existing loop; the "explicit predictions before reveal" language was aspirational overreach. The resolution is sound.

However, I note that the spec as written (the artifact under review) still contains the overreaching language in Phase 1 Step 3: "Require candidates to make explicit, recorded predictions about the holdout before the holdout is revealed." The Author has proposed the fix but has not applied it to the spec text. The spec remains incorrect on this point until the text is updated. This is a spec-update task, not a new debate flag — but it should be noted that the spec is not yet corrected.

**Flag 5 — Six-layer protocol absent from Implementation Sketch**

The Author has correctly identified what Phase 0 needs to contain (six items, one per layer). The content is right. Again, the spec text has not been updated — the Implementation Sketch still lacks Phase 0. The Author's Turn 9 is a repair proposal, not a repair execution. The spec remains incomplete until Phase 0 is added.

**Flag 6 — Component C constraint absent from Constraints section**

The Author accepts this and proposes the exact text: "Component C is disabled in discovery mode. Self-referential operation violates the contamination constraint. Component C is a calibration-mode accelerator only." Correct. The spec's Constraints section does not yet contain this text.

---

## On the Three Minor Flag Resolutions

**Flag 2 — Phase 2 Step 3 unenforceable**

The Author proposes adding: "This determination requires human judgment and cannot be automated. The operator must explicitly assess whether the constraint class is known before proceeding." Correct. Not yet in the spec text.

**Flag 3 — INS-012 cross-reference in Tracking section**

The Author accepts the move to Open Question 2. The spec's Tracking section still contains the cross-reference as a routine tracking step. Not yet corrected.

**Flag 4 — Open Question 6 closure language**

The Author proposes reframing to state explicitly that the minimum apparatus analysis does not resolve the "truth machine" claim. Correct. Not yet in the spec text.

---

## The Pattern This Creates

All six flags have been correctly diagnosed and correctly resolved in the Author's Turn 9. None of the proposed resolutions introduce new problems. The debate has done its job.

What remains is a gap between the repair proposals (in the debate log) and the spec artifact (which has not been updated). This is not a debate failure — it is a spec-update task that the operator or a subsequent pass must execute. The spec under review is a snapshot from before Turn 7 ran; the debate has now produced a complete set of corrections that need to be applied to that snapshot.

**One observation on the spec's "Open track" section:** The spec lists "End-to-end pre-registration protocol for unknown-domain experiments" as an open track "not yet debated." Turn 7 has now debated it. The open track label is stale. When the spec is updated with the six-flag corrections, this section should be updated to reflect that Turn 7 addressed the eigenquestion and produced the six-layer protocol. The open track is no longer open — it has a proposed answer (Turn 7's minimum pre-registration protocol) that the Skeptic has not flagged as incorrect.

---

## Summary

The Author's Turn 9 has correctly resolved all six flags. No new decisive claims have been introduced. The spec requires six textual updates (corresponding to the six flags) plus one stale-label correction (the "open track" section). These are editorial tasks, not debate tasks. The debate has converged from my side.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->
