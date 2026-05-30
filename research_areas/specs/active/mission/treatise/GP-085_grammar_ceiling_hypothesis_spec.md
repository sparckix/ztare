# GP-085 — Grammar Ceiling Hypothesis: Static vs. Dynamic Dictionary

## Status

Active

## Seam

research_areas/private/seams/GP-085_grammar_ceiling_hypothesis_seam.md

## Scope

- Formal statement of the Grammar Ceiling Hypothesis (GCH) defensible against symbolic regression literature
- Determination of GCH scope: single-substrate confirmed finding (GCH-Planck) vs. general architectural principle (GCH-General)
- Paper placement decision for GCH within paper5 and any downstream publications
- Tacrolimus primitive library specification with evidence motivation standard
- Placement of the dynamic dictionary and Alien Math API arguments within paper5

---

## Decision

The Grammar Ceiling Hypothesis is confirmed as an empirical finding on the Planck substrate (GCH-Planck) but is not yet established as a general law. The operational ceiling is a function of grammar G, search procedure P, and compute budget — denoted C(G, P, budget) — not a pure property of G alone. GCH-Planck is presented in paper5 as the architectural motivation for the UNIVERSAL_DENOMINATOR primitive (Option D), with any general-principle claims confined to the discussion section and explicitly qualified as pending cross-substrate replication. The Feynman Wall detection is an operational heuristic, not a theorem, and must be described as such. The tacrolimus primitive library is to be locked before data analysis with written justification derived from general pharmacokinetic theory, not tacrolimus-specific literature. The dynamic dictionary argument receives one body paragraph in paper5 plus appendix treatment; the Alien Math API argument is confined to an appendix.

---

## Problem

ZTARE's symbolic regression engine stagnated at score 93 on the Planck substrate after 32 iterations, with 15 emergency-pivot iterations yielding zero structural progress. Adding the UNIVERSAL_DENOMINATOR primitive broke this stagnation and recovered Planck's law `x1^3/(exp(x1/x2)-1)` to four decimal places, with all farther-tail discriminator points passing at <0.13% error. This two-experiment chain motivates a formal claim about the relationship between grammar expressivity, compute, and structural discovery — but the precise scope and formal status of that claim have not been established. The seam must determine: what exactly was confirmed, at what generality, and how it should be stated, placed, and extended.

---

## Why It Matters

If grammar expressivity is the binding constraint on structural discovery — rather than compute budget or iteration count — then the correct investment for improving ZTARE's discovery capability is primitive library design, not hardware scaling or iteration budget increases. This has direct roadmap consequences: the tacrolimus pharmacokinetics application requires selecting the right primitive library before locking the grammar, and that selection must be motivated by principled domain theory rather than post-hoc rationalization. Additionally, the claim that the farther-tail discriminator makes grammar ceilings operationally visible and testable — something existing symbolic regression literature cannot do — is the core novelty claim ZTARE must defend. Imprecise framing of this claim exposes it to the obvious SR-literature objection that grammar-expressivity ceilings are already implicit in Koza (1992), Schmidt & Lipson (2009), and Cranmer (2023).

---

## Constraints

1. The two closed experiments (crucial_02_extended, crucial_03) confirm GCH on the Planck substrate only. Cross-substrate replication has not occurred. Any general-principle claim must carry an explicit replication caveat.
2. The experiments vary iteration count but not proposer capability. The ceiling C(G, P, budget) is an operational ceiling that conflates grammar expressivity limits with search limits; the evidence does not isolate these.
3. The Feynman Wall detection (stagnation ceiling + Component D composition saturation + no new structural moves in latent distance log) is a convergent operational signal, not a mathematical proof that the grammar is exhausted. It must not be described as a proof.
4. The farther-tail gate's discriminating power is substrate-conditional: it distinguishes structural class from grammar-ceiling-best-form only when the ground truth exhibits qualitatively distinct extrapolative behavior compared to all forms reachable within G. This is a precondition, not a universal guarantee.
5. The tacrolimus primitive library must be locked and documented before any tacrolimus data is analyzed, with per-primitive justification citing general PK theory. Post-hoc selection constitutes contamination of the GCH test on that substrate.
6. The aphorism "Compute buys interpolation; Grammar buys extrapolation" is a heuristic summary, not a precise claim. A sufficiently capable LLM with Planck's law in pretraining could one-shot the answer; the precise claim is substrate-and-grammar-conditional. The aphorism may appear in the paper only with a footnote pointing to the formal conditional statement.

---

## Options

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — GCH as result section in paper5** | Present GCH as a confirmed result, supported by crucial_02_extended + crucial_03, scoped to the Planck substrate | Strongest publication signal; directly supported by closed experiments | Requires explicitly scoping result to Planck substrate or waiting for cross-substrate replication; risks overclaiming if substrate qualifier is dropped | Viable only if result section language is explicitly GCH-Planck throughout |
| **B — GCH as theoretical claim with pending-confirmation caveat** | Present GCH as a theoretical architectural claim awaiting empirical confirmation | Conservative; avoids overclaiming | Under-evidenced for a result; the experiments are closed and do confirm GCH-Planck; this framing undersells what is actually known | Rejected — the finding is stronger than this framing allows |
| **C — GCH as a separate short paper** | Defer GCH to a standalone publication after cross-substrate replication | Allows full empirical grounding before publication; permits formalizing Feynman Wall detection across multiple substrates | Delays publication; may fragment the paper5 narrative unnecessarily | Viable after cross-substrate replication; premature now |
| **D — GCH as architectural motivation for UNIVERSAL_DENOMINATOR** | Frame GCH as the motivation and retrospective explanation for the grammar expansion that broke the ceiling; present GCH-General in discussion with replication caveat | Accurate to the experimental narrative; does not require Feynman Wall to be a theorem; defensible without additional experiments; honest about what was confirmed | Does not position GCH as a standalone contribution | **Recommended** — most defensible given current evidence |

---

## Recommendation

Adopt Option D. Present GCH-Planck in the paper5 results section as the empirical observation that motivated the UNIVERSAL_DENOMINATOR grammar expansion: stagnation was observed, a grammar ceiling was hypothesized, the ceiling was broken by adding a primitive motivated by the structural class of the ground truth. The general architectural principle (GCH-General) belongs in the discussion section with an explicit statement that cross-substrate replication is the next required step before claiming general law.

The formal statement to use throughout:

> **Grammar Ceiling Hypothesis (operational form):** For a symbolic regression engine operating under a bounded grammar G and a given search procedure P, there exists an empirically observable score ceiling C(G, P, budget) above which additional compute — iterations or model capability within P's exploration bounds and the given compute budget — yields no structural progress. C(G, P, budget) is determined by the expressivity of G relative to the ground truth structural class as effectively reachable by P within the given compute budget, not by the compute budget itself. Operator-guided grammar expansion, motivated by the Falsification Suite, is the correct mechanism for breaking C(G, P, budget) when the ground truth structural class exceeds G's expressivity beyond P's ability to discover it within the given compute budget.

> **Corollary (Static Dictionary and Falsification Suite):** A dynamic, self-expanding grammar degenerates to curve-fitting, sacrificing extrapolative validity for interpolative precision. The static dictionary is the epistemic friction that forces structural compression rather than data memorization. The Falsification Suite (holdout hard gate + farther-tail discriminator) makes the grammar ceiling operationally visible and testable by distinguishing structural class from grammar-ceiling-best-form when the ground truth exhibits qualitatively distinct extrapolative behavior compared to forms expressible within G.

The novelty claim for the Falsification Suite is: existing SR literature implicitly assumes grammar determines the reachable hypothesis space, but lacks an operational test that makes the ceiling detectable. The farther-tail discriminator provides this test, subject to the substrate-conditional precondition stated in the corollary.

---

## Implementation Sketch

**paper5 structure:**
- Results section: present GCH-Planck — stagnation at C(G, P, budget) ≈ 93, zero structural progress over 15 emergency-pivot iterations, ceiling broken by UNIVERSAL_DENOMINATOR addition, Planck's law recovered to four decimal places with all farther-tail points passing at <0.13% error. Describe Feynman Wall detection as a convergent operational signal, not a proof of grammar exhaustion.
- Discussion section: state GCH-General with explicit cross-substrate replication caveat. Note that C(G, P, budget) conflates grammar expressivity limits with search limits, and that isolating these requires experiments varying proposer capability while holding grammar fixed.
- Body paragraph on dynamic dictionary: one paragraph stating that the farther-tail gate provides the empirical test distinguishing static-grammar law from dynamic-grammar curve fit — something the existing SR literature cannot do because it has no such gate — with reference to the substrate-conditional precondition and the appendix for the full argument.
- Appendix A: Full dynamic dictionary argument — the progression from dynamic grammar to neural network to interpolation, and why the farther-tail gate is the discriminating mechanism.
- Appendix B: Alien Math API distillation bottleneck argument — the claim that distillation from an unconstrained representation space recovers only what the static grammar can express anyway; note that the middle case (approximate translation with bounded information loss) is unresolved and does not need to be closed in this paper.

**Tacrolimus primitive library (pre-lock requirement):**
The following six primitives are drawn from standard pharmacokinetic theory (Rowland & Tozer; Gabrielsson & Weiner) and are not tacrolimus-specific. Each must be documented with a PK-theory citation before the tacrolimus data is analyzed:

| Primitive | Form | PK justification |
|---|---|---|
| Michaelis-Menten saturation | `V_max * C / (K_m + C)` | Canonical hepatic enzyme saturation kinetics |
| First-order exponential elimination | `C_0 * exp(-k * t)` | Linear clearance, standard for drugs with first-order kinetics |
| Two-compartment distribution | Sum of two exponentials with separate rate constants | Standard for drugs with peripheral distribution volume |
| Hill function (sigmoid saturation) | `E_max * C^n / (EC50^n + C^n)` | Receptor-mediated pharmacodynamic effects |
| Linear protein binding correction | `C_free = C_total / (1 + f_bound)` | Free-fraction correction for highly protein-bound drugs |
| Non-linear clearance (capacity-limited) | `CL = CL_max / (1 + K_cl / C)` | Saturable clearance at high concentrations |

The library must be locked and the per-primitive justification document filed before any tacrolimus dataset is accessed. Selection motivated by tacrolimus-specific literature after seeing the data constitutes contamination of the GCH test on the tacrolimus substrate.

**Cross-substrate replication axis:**
Identify a second substrate with a ground truth structural class that (a) contains a transcendental or non-polynomial primitive, and (b) can be verified against a known analytical law. Run the same two-experiment chain: confirm the grammar ceiling on the initial grammar, then break it by adding a motivated primitive. If C(G, P, budget) behavior replicates on this substrate, GCH-General gains empirical credibility sufficient for a standalone short paper (Option C becomes viable).

---

## Open Questions

1. **Search ceiling vs. grammar ceiling isolation:** The current experiments vary iteration count but not proposer capability. A controlled experiment holding G fixed while varying the proposer (weaker vs. stronger LLM, different search heuristics) would determine how much of C(G, P, budget) is attributable to grammar expressivity vs. search limitations. Is this experiment worth running before the tacrolimus application, or is the distinction immaterial for practical purposes?

2. **Feynman Wall formalization:** The current detection (stagnation ceiling + Component D composition saturation + latent distance log stasis) is an operational heuristic. Under what conditions could this be formalized as a theorem — e.g., if all compositions in G reachable by P have been generated and scored, is the ceiling then provably tight? What would the formal object look like, and is formalizing it a priority?

3. **Second transcendental substrate selection:** What is the right substrate for cross-substrate replication? The substrate must contain a transcendental primitive in the ground truth and be verifiable against a known law. Candidate classes: Wien's displacement, Stefan-Boltzmann, Fermi-Dirac distribution. Which of these is feasible within the current ZTARE infrastructure and what is the expected ceiling behavior on the initial grammar?

4. **Tacrolimus contamination audit:** Has any member of the team seen tacrolimus PK literature that would make the six-primitive list a post-hoc rationalization rather than a principled prior? This needs to be established before the library is locked.

5. **Alien Math API middle case:** The approximate translation with bounded information loss (≈90% accuracy) is a real possibility that the paper does not close. Is this a meaningful alternative to the static-grammar approach for applications where exact structural recovery is not required? If so, does ZTARE need a position on it, or is it out of scope?