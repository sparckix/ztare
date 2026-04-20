# Paper 5 — Draft Additions and Section Notes

This file tracks additions to `main.tex` in plain text so they are grep-able and readable without compiling LaTeX. Each entry names the section, the date added, and the plain-language version of the content.

---

## Added 2026-04-18: Grammar Expressiveness as a Measurable Quantity (§2.9 corollary)

**Location in main.tex:** New `\subsubsection*{Grammar Expressiveness as a Measurable Quantity}` inserted at the end of §2.9 (The Static Grammar as Falsification Guarantee), immediately before §2.10 (The Epistemological Ledger).

**Core claim:**
Grammar expressiveness is a measurable property of the verification apparatus, not merely a design choice. Whether a score ceiling reflects optimizer pathology or grammar insufficiency determines the remedy: more restarts vs. primitive injection. The apparatus must provide the instrument that separates these two failure modes.

**The discrete evaluation mode special case:**
In discrete exact-match scoring (where there is no continuous surface for the optimizer to descend), a stagnation ceiling at maximum error is classification-complete. Optimizer pathology is ruled out by architecture — there is no optimizer foothold. Grammar insufficiency is the only remaining interpretation. The ceiling becomes a direct measurement of a property of the grammar on the given substrate.

**Required conceptual separation:**
Grammar insufficiency and retrieval blocking are distinct mechanisms that both produce score ceilings but require separate evidence:

| Mechanism | What it means | Evidence required |
|---|---|---|
| Grammar insufficiency | No form in the vocabulary evaluates correctly | Discrete-mode stagnation, or continuous-mode with multi-start spread analysis |
| Retrieval blocking | Correct form exists, but named-import gate + score-zeroing prevents retrieval | Comparison of gated vs. ungated runs on the same grammar and substrate |

The conservative claim after a stagnation experiment is always: "confirmed grammar insufficiency" (or "confirmed optimizer pathology"), never "confirmed retrieval blocking" unless the gated/ungated comparison exists. The A000009 (integer partition function) case confirms the former; the latter claim is not yet separately evidenced.

**Honest framing for A000009 as concrete example:**
The partition function case (Hardy-Ramanujan asymptotic class) is a good concrete anchor for grammar insufficiency. The available symbolic vocabulary cannot correctly enumerate partitions under discrete scoring. This is a clean instance of the "missing letters" failure mode. It does not additionally confirm that the same engine, given unrestricted access to the function's name and formula, would retrieve the correct answer — that is a separate claim about a different run condition.

---

---

## Added 2026-04-18: Stretched Exponential Recovery — Second Empirical Chain (Conclusion extension)

**Location in main.tex:** Four paragraphs inserted in the Conclusion section, immediately after the Grammar Ceiling Hypothesis paragraph (ending "What determines the ceiling is what the generator can say, not how long it is permitted to speak.") and before the "One natural extension deserves naming" paragraph.

**Paragraph 1 — The experiment and result:**
A pre-registered single-variable decay law recovery task (sealed before any iteration, ground truth withheld from model and judge) presented 20 cold evidence points, no domain labels, and a grammar restricted to exponential, logarithmic, and root primitives with arithmetic including algebraic powers. True law: Kohlrausch stretched exponential v(t) = A·exp(-(t/τ)^β)+C, β=0.63. Standard exponential (β=1) fits visible window but misses farther tail by ~0.18 at t=20, above threshold. Engine recovered a·exp(-b·t^c)+d with c=0.630 (GT: 0.63), all pre-registered gates at residuals ~1e-06, seven discriminator tests across early decay / mid-divergence / deep tail at zero relative error vs ground truth.

**Paragraph 2 — Prony series epistemic ceiling:**
98/100 is correct epistemology. Any decaying curve can be approximated arbitrarily closely by a weighted sum of standard exponentials (Prony series) on finite data. Uniqueness of the stretched-exponential topology cannot be proved from observable data alone; judge withholds 2 points on that ground. Gate enforces correctness up to evidential limit; judge states the underdetermination the gate cannot resolve.

**Paragraph 3 — Structural contrast with Planck chain:**
H-COMPUTE-01/H-GRAMMAR-01: binding constraint was a missing denominator primitive; adding it resolved the ceiling in 6 iterations where 32 more budget iterations could not. Present experiment: required primitive (algebraic power composition inside an exponential) was already in the grammar; ceiling is evidential, not structural. Same pattern across different constraint types: cold data, no domain priors, deterministic gates, correct topology, ceiling at the evidential falsifiability boundary.

**Paragraph 4 — Generalisation claim:**
The two chains together support what the single Planck experiment could not: the apparatus generalises across substrate types. Blind recovery is achievable when the target topology lies within the grammar's range; when it does not, the ceiling classifies the failure unambiguously.

---

## Added 2026-04-18: Apparatus Rigidity and LLM Cognitive Limits — Langevin Dead End (Conclusion extension)

**Location in main.tex:** Two paragraphs inserted after the generalisation claim ("The cage enforces correctness...") and before "One natural extension deserves naming."

**Paragraph 1 — The dead end:**
A saturation law recovery task (same grammar as KWW) produced a champion at 75/100 that stagnated for 10 consecutive iterations. The composition engine ran 20 guided rounds — every one proposed additive combinations of different primitive families. Zero proposed a ratio of two instances of the same family. The telemetry negative space revealed a systematic LLM structural bias: Taylor/Fourier-style additive expansions favoured, rational symmetries (A/A compositions) systematically avoided. The correct topology (ratio of exponential sums) is expressible in the grammar but unreachable by the model's search.

**Paragraph 2 — The apparatus-rigidity claim:**
The apparatus didn't fix this by making the model smarter. It fixed it by making the failure legible. Rigid gates refused polynomial mimics. Composition telemetry logged every proposal and every omission. Human operators read the negative space, identified the self-ratio blind spot as systematic (not random), and added deterministic probes gated by residual statistics (not domain knowledge). The apparatus does not require the model to be omniscient — it requires the cage to be rigid enough to force the engineers to confront the model's actual cognitive limits. The dead end is a product of the system, more informative than a clean success.

**Logged as:** INS-028 (insights ledger), E-GP096-LAN-01 (track record, frozen), Cognitive Gym section "Search Telemetry as Negative-Space Map"

---

## Added 2026-04-19: Reflexive Application — Verification Principles Applied to Verification Infrastructure (Conclusion extension)

**Location in main.tex:** One paragraph inserted after the "One natural extension deserves naming" paragraph (theorem prover), as a second named extension.

**The paragraph:**
A third extension is reflexive: applying the verification principles to the verification infrastructure itself. Each principle in this treatise was derived for evaluating candidate models. The same principles can be applied one level up, to the engine that implements them. Token-Optimized Self-Modeling applies Compress to the agent's own cognition: build a minimal structural cache that prevents partial-view editing errors. The Inception Pattern applies Invert to the agent's awareness of its own pipeline: give the agent a pre-computed model of the gates so it can check for likely rejection before proposing an edit. The Hybrid Persona Router applies Adversarial Disagreement to the review layer's own expertise selection: when no existing reviewer profile fits the observed failure type, the system generates a new one rather than defaulting to a generic lens. Each instance was discovered from a specific failure, not derived in advance. Each is testable against the failure that motivated it. The application is not circular: a scientist who applies the scientific method to evaluate the scientific method is doing philosophy of science, not reasoning in a loop. Whether this process terminates, whether there is a level at which the verification infrastructure no longer benefits from applying verification principles to itself, is an empirical question this treatise names but does not answer.

**Logged as:** reflexive_engineering_primitives.md (catalog), GP-102 (mechanization seam)

---

## Existing content inventory (for cross-reference)

- §2.9 main argument: static grammar as falsification guarantee; dynamic grammar collapses epistemic traceability
- Conclusion §: H-COMPUTE-01 (doubling budget at grammar ceiling yields zero lift) and H-GRAMMAR-01 (single primitive injection → Planck law recovery in 6 iters); Grammar Ceiling Hypothesis formalized as C(G, P, budget) where budget contributes zero marginal lift beyond primitive exhaustion
- §2.8: The library-as-Goodhart-target problem; gate turnover requirement
- Appendix Formalization: typed signatures of the ten operations; Inspection Principle
