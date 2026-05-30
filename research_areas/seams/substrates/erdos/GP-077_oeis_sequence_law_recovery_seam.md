# GP-077 — OEIS Sequence Law Recovery: ZTARE as a Machine Scientist for Dark Sequences

> **Seam metadata** · `seam_id:` GP-077 · `track:` substrates · `status:` Open - seam created 2026-04-17 · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

Open — seam created 2026-04-17

## One-Line

Apply ZTARE's corrector-recovery architecture to OEIS integer sequences with known values but unknown closed forms — the residual recovery problem is structurally identical to sandbox corrector discovery.

---

## Problem

OEIS contains thousands of sequences where:
- The first N terms are known (observed data)
- No closed-form formula is known
- Competing conjectured formulas all fit the first N terms but disagree beyond them

This is the sandbox_15 degeneracy problem verbatim. The corrector `round(0.08*v)` was in the library but invisible because all competing forms fit visible data equally. The Predictive Divergence Sweep (GP-076) breaks this tie by finding where candidates maximally disagree and querying one point.

For OEIS sequences, "querying one point" means computing `a(N)` at the divergence index. This is deterministic and cheap. No oracle is needed — the sequence generator IS the ground truth.

The Erdős connection is inverted: rather than trying to prove a conjecture holds for all N, ZTARE runs an adversarial search for the index where competing explanations most disagree, then tests there. If the conjecture survives the sweep's adversarially-chosen test points, it is empirically hardened. If it fails, ZTARE found the counter-example.

---

## Architectural Mapping

| ZTARE Component | Sandbox Role | OEIS Role |
|---|---|---|
| Evidence triples (u, v, z) | (u, v, f(u,v)) integer grid | (n, a(n)) sequence terms |
| Dominant term | u²v − u | Known leading-order formula (if any) |
| Corrector | round(0.08v) | Residual after dominant term |
| Corrector library | 26 analytic forms | Number-theoretic primitive library (TBD) |
| Component C | Shape descriptor from residual | Shape descriptor from sequence residual |
| GP-076 sweep | Divergence query at v=35 | Divergence query at n=N* |
| Holdout gate | Unseen (u,v) pairs | Withheld sequence terms beyond visible window |
| Feynman Wall | Library exhausted → LLM topology | Library exhausted → LLM proposes novel closed form |

---

## What Needs to Be Built

### 1. OEIS Substrate Generator

A tool that takes an OEIS sequence ID (e.g. A000041 — partition numbers) and produces:
- `evidence.txt` with the first K terms as (n, a(n)) pairs
- `evidence_holdout.txt` with terms K+1 through M
- `gate_harness.py` that checks exact integer match on holdout
- `sandbox_gt.py` with the known recurrence or generator as `f_true`

The substrate generator is the only genuinely new component. Everything downstream already exists.

### 2. Number-Theoretic Primitive Library

The original seam proposed building a separate `oeis_primitive_library.py` with number-theoretic functions (ω(n), φ(n), σ(n), p(n), π(n)). This was superseded by the COMPRESS insight (2026-04-17): instead of building domain-specific primitives, apply a log transform to exponential sequences and fit in log-space using the existing library.

**Existing 26-form library + 6 parity-scaled extensions = 32 forms (built 2026-04-17):**

- Original 26 forms: round(k*v), floor(k*v), ceil(k*v), v mod k, floor(v/k), etc.
- Parity-scaled forms (GP-077): `(-1)^v * floor(k*v)`, `(-1)^v * round(k*v)`, `(-1)^v * round(k/v)`, `(-1)^v * round(k*sqrt(v))`, `(-1)^v * round(k*log(v))`, `(-1)^v * round(k*exp(-v/k))`

The parity forms capture alternating-sign residuals that appear in log-space for partition-like sequences (A002865 residual in log-space alternates ±0.15 with parity decay).

**Key architectural insight (COMPRESS primitive):** For exponential-growth sequences, the substrate generator applies `--transform log` before producing evidence. This maps the exponential growth to linear/polynomial growth in log-space. The dominant in log-space is `c₁√n + c₂log(n) + c₃` (Hardy-Ramanujan). The corrector in log-space is bounded and parity-structured — expressible by the extended library without number-theoretic functions.

### 3. Target Sequence Selection Criteria

Not all OEIS sequences are appropriate targets. Criteria for tractable targets:
- Unknown closed form (confirmed in OEIS comments)
- Computable: generator exists (recurrence, Mathematica, Python snippet)
- Dominant term identifiable: leading-order behavior extractable by curve fitting
- Residual is small: the gap between dominant term and true value is bounded
- **PRE-FLIGHT AUDIT (mandatory):** 10-line residual audit script checks whether the residual is physically expressible by the current 32-form library. If not, do NOT run the loop — upgrade the library first (Vocabulary Trap prevention).

OEIS sequences tagged `more` (more terms needed) or `hard` are the primary candidates. Sequences with exponential growth (partition-like) require `--transform log` in the substrate generator.

---

## Key Claims to Debate

1. **Structural equivalence.** The OEIS residual recovery problem is structurally identical to sandbox corrector recovery, not merely analogous. If true, the existing ZTARE stack requires only a substrate generator and library swap — no architectural changes.

2. **Divergence sweep as counter-example design.** Querying `a(N*)` at the maximum-disagreement index is strictly better than sequential search. The information-theoretic argument: one observation at N* eliminates more candidates than O(log N*) sequential observations from N+1 onward.

3. **Feynman Wall as discovery event.** When no primitive library form survives holdout, this is not failure — it is a signal that the sequence belongs to an undiscovered class. The LLM topology proposal mode then produces candidate closed forms that are genuinely novel mathematical objects.

4. **Scope boundary.** ZTARE discovers laws; it does not prove them. A sequence law that survives the GP-076 sweep is an empirically hardened conjecture, not a theorem. The proof step requires a separate component (formal verification, not in scope here).

---

## Open Questions

1. **Which OEIS sequence is the right first target?** Criteria: small residual, identifiable dominant, computable generator, no known closed form. Candidates: A002865 (partitions with no 1s), A001694 (powerful numbers), A005132 (Recaman's sequence). Need a principled selection method.

2. **Does the 26-form library have meaningful overlap with number-theoretic primitives?** `floor(k*v)`, `v mod k`, `round(v/k)` are already present. How many OEIS residuals fall within the existing library's expressible forms?

3. **What does "dominant term" mean for a purely additive sequence?** For `a(n) = f(n)` with no multiplicative structure, the dominant/corrector decomposition may not apply. Does ZTARE require a two-component structure, or can it operate on the full sequence directly?

4. **Contamination bound at scale.** The GP-076 budget is `floor(run_length / 3)`. For number-theoretic sequences where the divergence index may be `n = 10^6`, is the contamination gate calibrated correctly? A single query at `n = 10^6` reveals no more than a query at `n = 20` epistemically — but the practical cost of computing it may differ.

---

## What This Is Not

- Not a formal proof assistant. ZTARE cannot output a Lean/Coq proof.
- Not a brute-force sequence matcher (that is what Superseeker/OEIS lookup does).
- Not a replacement for computer algebra systems. The LLM proposes topology; CAS verifies identities.
- Not Erdős-class problem solving in the proof sense. The scope is conjecture generation and empirical hardening.

---

## Open Debate: OEIS vs Direct Erdős

### The Erdős Route (Principal, 2026-04-17)

The principal proposes bypassing OEIS as an intermediate target and pointing ZTARE directly at an unsolved Erdős-class conjecture — specifically using Claude as the mutator in a thin afternoon build rather than the full ZTARE apparatus.

**The Erdős-direct argument:**

Verification in Erdős conjectures is deterministic and cheap. For Erdős-Straus (4/n = 1/a + 1/b + 1/c for all n > 1), testing whether a specific n has a decomposition is O(1) arithmetic. No LLM judge that can be gamed, no holdout contamination risk. This collapses the full adversarial ZTARE stack into a thin loop: Claude proposes candidate rules → Python verifies → divergence sweep finds n* where rules maximally disagree → query → eliminate.

**The OEIS-first counter-argument:**

The failure mode for Erdős-direct is not verification — it is topology proposal. The corrector library gives the LLM a bounded topology space. For Erdős, the space is unbounded. "Find three integers satisfying 4/n = 1/a + 1/b + 1/c" is a Diophantine search, not a form-fitting problem. Without a bounded library, Claude may thrash (the GPT-4o non-convergence failure mode) rather than converge.

OEIS sequences are the right first target because: (1) topology space is bounded by the primitive library, (2) dominant/corrector decomposition applies directly, (3) a result is publishable on its own, (4) failure modes are contained.

**Questions to resolve:**

1. Is Erdős topology proposal tractable for an LLM without a bounded library, or does it require building a Diophantine primitive library first?
2. Is "an afternoon build" realistic for Erdős-direct, or does unbounded topology mean thrashing?
3. Can both run in parallel — thin Erdős prototype tomorrow, OEIS substrate next week?

---

## Debate Log

### Principal Turn 1 — 2026-04-17

**Preference stated: Erdős-direct over OEIS-first.**

The principal reviewed the OEIS-first counter-argument above and the full ZTARE V2 architecture and concludes: the strategic target is Erdős, not OEIS. The reasoning follows.

**Why the full ZTARE apparatus is superior to a thin script for Erdős:**

A thin Erdős prototype (Claude proposes → Python verifies → iterate) has the right verification loop but lacks three things the full cage provides:

1. **Contamination Gate Integrity.** A thin script has no suppression mechanism. The LLM may have Erdős-class conjectures in training data and could pattern-match rather than derive. ZTARE's Step 5 contamination gate explicitly suppresses queries that would uniquely identify the GT with no free parameters, forcing genuine derivation rather than retrieval.

2. **Structural Memory.** GP-061/062 extractors track *why* families of formulas fail. Without this, the mutator oscillates between competing "convincing lies" that fail for the same underlying number-theoretic reason. The structural memory prevents the GPT-4o non-convergence failure mode in the Erdős domain.

3. **Feynman Wall Escalation.** When the current library is exhausted, the system escalates to novel topology proposal. This is where ZTARE stops being a curve-fitter and becomes a conjecture generator — the exact transition needed for Erdős-class problems that no existing library form can express.

**The implementation delta is two components, not a rewrite:**

- `erdos_conjecture_substrate.py` replaces `sandbox_15_gt.py` — the verification oracle becomes a deterministic Diophantine checker
- Number-theoretic primitive library replaces the 26-form analytic library — primes, modular arithmetic, Euler totient, prime gaps replace step/round/floor forms

The loop, the sweep, the contamination gate, the structural memory, Component C — all carry over unchanged.

**The universality test argument:**

If ZTARE closes on an Erdős-class sequence using the full cage, that is not just a mathematical result — it is proof that the discovery engine generalizes across domains. OEIS residual recovery proves the mechanism in a domain where the answer is computable. Erdős proves it in a domain where the answer is unknown to mathematics. The NPV of the latter is categorically higher.

**Proposed resolution of the OEIS vs Erdős debate:**

OEIS-first is the conservative path with contained failure modes. Erdős-direct with the full ZTARE cage (not a thin script) is the aggressive path with higher epistemic upside. The principal's preference is the full ZTARE apparatus pointed at a tractable Erdős-class target — specifically a sequence where: (a) the dominant term is known, (b) the residual is unexplained, (c) the number-theoretic primitive library can express the residual class.

**Questions for debate:**

1. Does the Erdős substrate require a holdout gate, or is the deterministic verifier sufficient as the falsification oracle?
2. Which Erdős-class target is most tractable for the current architecture — Erdős-Straus (4/n decomposition), Collatz residuals, or a specific OEIS sequence tagged as Erdős-related with unknown closed form?
3. Is the contamination gate calibrated for number-theoretic primitives, or does it require recalibration for the new library?


### Turn 1 — Claude-Author (2026-04-17) — Autonomous runner turn

The seam is well-structured but contains several decisive claims that need sharpening before the architecture can be trusted. I'll work through the eigenquestion first, then address the three claims that most affect downstream choices.

---

## Eigenquestion

**Does the OEIS/Erdős residual recovery problem share the same *information-theoretic structure* as sandbox corrector recovery, or only a surface-level analogy?**

This is the decisive question because the entire "substrate generator + library swap = done" argument rests on structural equivalence (Claim 1). If the equivalence is shallow, the implementation delta is not two components — it is a partial rewrite of the scoring and contamination layers.

---

## On Claim 1: Structural Equivalence

The seam asserts the OEIS problem is "structurally identical" to sandbox corrector recovery. This is too strong. Here is the precise disanalogy:

**Sandbox corrector recovery:** The evidence triples `(u, v, z)` are drawn from a 2D integer grid. The dominant term `u²v − u` is known. The corrector `round(0.08v)` is a function of one variable. The residual `z − dominant(u,v)` is a 1D signal the library can probe.

**OEIS sequence recovery:** The evidence is `(n, a(n))` — a 1D sequence. There is no second variable. The "dominant term" is not given; it must be extracted by curve fitting, which introduces a free parameter estimation step that does not exist in the sandbox. The residual `a(n) − dominant(n)` is also 1D, but the dominant is now a fitted object, not a known ground truth.

**Why this matters architecturally:** Component C's Mutator-Dominant Subtraction works because the dominant is *known* — the subtraction isolates the GT corrector shape without contamination from the dominant's own uncertainty. For OEIS, if the dominant is estimated by curve fitting, the residual inherits the dominant's estimation error. The 2-bit shape descriptor (smooth/step × monotone/non-monotone) may be unreliable when the dominant is uncertain. This is not a minor calibration issue — it is a structural difference in what Component C can guarantee.

**What would make the equivalence hold:** The equivalence is valid *only for OEIS sequences where the dominant term is analytically known* (e.g., a sequence defined as `a(n) = n² + correction(n)` where the `n²` part is established). For sequences where the dominant must be estimated, the architecture needs a dominant-uncertainty propagation layer that does not currently exist.

**Proposed resolution:** Narrow Claim 1 to: "The OEIS problem is structurally equivalent to sandbox corrector recovery *when the dominant term is analytically known*. For sequences requiring dominant estimation, an additional uncertainty propagation step is needed." This scoping change affects target selection criteria — only sequences with known dominant terms are tractable without architectural extension.

---

## On Claim 2: Divergence Sweep as Counter-Example Design

The information-theoretic argument is stated but not proven. The claim is: "one observation at N* eliminates more candidates than O(log N*) sequential observations from N+1 onward."

This is plausible but depends on the candidate distribution. If candidates are clustered (many forms agree on most values and disagree only at specific arithmetic progressions), then N* may be in a sparse region where only one candidate disagrees — eliminating one candidate per query, not O(log N*) candidates. The sweep's advantage is real when candidates are *spread* across the disagreement space, not when they cluster.

**The WWYHTB check:** To accept Claim 2, you must believe that the candidate set produced by the mutator after K iterations is approximately uniformly distributed over the disagreement space. This is not guaranteed — the mutator may systematically propose forms that agree on small n and diverge only at large n, making the sweep's early queries uninformative.

**Proposed resolution:** Claim 2 should be stated as: "The divergence sweep is superior to sequential search *when the candidate distribution is spread across the disagreement space*. When candidates cluster, the sweep degenerates to sequential search." The sweep's information gain should be measured empirically on the first OEIS target, not assumed.

---

## On the Erdős-Direct vs OEIS-First Debate

The principal's argument for Erdős-direct with the full ZTARE cage is strategically sound but contains one unexamined assumption: **the number-theoretic primitive library is buildable in the same time frame as the substrate generator.**

The 26-form analytic library was built for a specific domain (smooth functions of two variables). The number-theoretic primitive library requires:
- `ω(n)`, `φ(n)`, `σ(n)` — these are computable but not in the current library
- `p(n)` (partition count) — computationally expensive for large n
- `π(n)` (prime counting function) — requires a sieve, not a closed form

More importantly: the contamination gate's suppression threshold was calibrated for the analytic library. A number-theoretic primitive that is highly specific (e.g., `φ(n) mod 3`) may pass the contamination gate while effectively leaking the GT if the GT happens to be `φ(n) mod 3`. The gate needs recalibration for the new library's specificity distribution.

**The Erdős-Straus specific case:** For `4/n = 1/a + 1/b + 1/c`, the "dominant term" is not a function of n in the corrector sense — it is a Diophantine constraint. The corrector decomposition does not apply. This is a different problem class than residual recovery. The seam conflates two distinct problem types:

1. **Residual recovery:** `a(n) = dominant(n) + corrector(n)` — ZTARE's native domain
2. **Diophantine search:** "Does there exist (a,b,c) satisfying constraint(n)?" — a different problem class

Erdős-Straus is type 2. OEIS residual recovery is type 1. The full ZTARE cage applies cleanly to type 1. For type 2, the mutator's job is not to propose a functional form but to propose a search strategy — a fundamentally different topology space.

**Proposed resolution:** The seam should explicitly distinguish these two problem classes and scope the current architecture to type 1 (residual recovery). Erdős-class problems that are type 1 (e.g., an OEIS sequence with Erdős-related provenance and unknown closed form) are tractable. Erdős-Straus specifically is type 2 and requires architectural extension beyond the current scope.

---

## Summary of Decisive Claims Introduced

1. **Dominant uncertainty propagation:** Structural equivalence holds only when the dominant is analytically known. Sequences requiring dominant estimation need an additional layer.

2. **Candidate distribution assumption in sweep:** The sweep's information-theoretic advantage is conditional on candidate spread, not guaranteed.

3. **Library recalibration requirement:** The contamination gate needs recalibration for number-theoretic primitives before the Erdős substrate is valid.

4. **Type 1 vs Type 2 problem class distinction:** Erdős-Straus is a Diophantine search problem (type 2), not a residual recovery problem (type 1). The current architecture applies to type 1 only.

### Turn 2 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's turn is rigorous and I endorse the four decisive distinctions introduced. But several of the Author's own claims now need adversarial pressure before this seam can converge.

---

## On the Author's Dominant-Uncertainty Propagation Claim

The Author argues that Component C's 2-bit shape descriptor becomes unreliable when the dominant is estimated rather than known. This is directionally correct but overstated in a way that matters for target selection.

**The actual failure mode is narrower.** Component C probes `f_true(u,v) − f_dominant(u,v)` where `f_dominant` is *known*. For OEIS, if we substitute a *fitted* dominant, the residual is `a(n) − f̂_dominant(n)`, where `f̂_dominant` carries estimation variance. The 2-bit descriptor (smooth/step × monotone/non-monotone) is a *topological* classifier, not a precision measurement. Estimation error in the dominant shifts the residual's *level* but does not necessarily change its *topology* — a step function residual remains a step function residual even if the dominant is off by a constant.

**The failure condition is specific:** The descriptor breaks when dominant estimation error is large enough to *change the topology* of the residual — e.g., when a monotone residual becomes non-monotone due to dominant overfitting. This happens when the dominant is overparameterized (e.g., fitting a degree-5 polynomial to a sequence with a degree-2 dominant). The fix is not a new "uncertainty propagation layer" — it is a constraint on dominant estimation: use the *simplest* dominant that fits the leading-order behavior, not the best-fitting one. This is already implied by the Occam prior in the corrector library but needs to be made explicit in the OEIS substrate generator.

**Verdict on Author's Claim 1:** The structural equivalence condition should be "dominant is estimated with a low-complexity prior" rather than "dominant is analytically known." The latter is too restrictive — it would exclude most interesting OEIS targets where the dominant is conjectured but not proven.

---

## On the Author's Candidate Distribution Assumption

The Author flags that the sweep's information-theoretic advantage is conditional on candidate spread. This is a real concern but the Author's proposed resolution ("measure empirically on the first OEIS target") is not a resolution — it is a deferral. The seam needs a structural argument for why the mutator's output distribution is or is not spread.

**The structural argument the Author missed:** The mutator's candidate distribution is *not* arbitrary — it is constrained by the primitive library. If the library contains K forms and the mutator proposes candidates from this library, the disagreement structure is determined by the library's combinatorial geometry, not by the mutator's preferences. For a library of K forms, the maximum number of distinct disagreement patterns at any index n is K(K−1)/2. The sweep finds the n that maximizes this count. This is a property of the library, not of the mutator's distribution.

**Implication:** The sweep's advantage is guaranteed *when the library is diverse* (forms disagree at many different indices) and degrades *when the library is redundant* (forms agree everywhere except one index). The right question is not "is the candidate distribution spread?" but "is the primitive library diverse?" This is a property we can audit offline before running the sweep.

**Verdict on Author's Claim 2:** The conditionality should be reframed as "the sweep's advantage is proportional to the library's disagreement diversity, which can be audited offline." This is a stronger and more actionable claim than the Author's version.

---

## On the Type 1 / Type 2 Distinction

The Author's distinction between residual recovery (type 1) and Diophantine search (type 2) is the most important structural contribution in the turn. I want to sharpen it further because the seam's architectural mapping table conflates them in a way that will cause implementation errors.

**The conflation in the seam's table:** The table maps "Dominant term" to "Known leading-order formula (if any)" and "Corrector" to "Residual after dominant term." This mapping assumes type 1 structure. But the seam's "Open Debate" section then discusses Erdős-Straus (`4/n = 1/a + 1/b + 1/c`), which is type 2. The table is silently inapplicable to the problem the principal most wants to solve.

**A sharper type 2 characterization:** In type 2 problems, the "mutator's job" is not to propose `f(n)` but to propose a *witness construction* — a method for finding (a,b,c) given n. The verification oracle checks whether the witness satisfies the constraint. This is closer to a theorem prover's search than to a curve fitter's search. The structural memory in ZTARE tracks *why functional forms fail*; for type 2, it would need to track *why witness constructions fail* — a different object entirely.

**The Author's proposed resolution is correct but incomplete:** Scoping to type 1 is right. But the seam should also state what a type 1 Erdős-class target looks like concretely. The Author gestures at "an OEIS sequence with Erdős-related provenance and unknown closed form" but does not name one. Without a concrete target, the type 1 / type 2 distinction is a theoretical clarification that does not advance the experiment.

**Proposed addition:** The seam should add a "Type 1 Erdős-class candidates" section with at least two concrete sequences that satisfy: (a) Erdős-related provenance, (b) known dominant term or estimable with low-complexity prior, (c) residual is unexplained, (d) computable generator exists. A000041 (partition numbers) has a known asymptotic dominant (Hardy-Ramanujan formula) and an unexplained residual structure — this is a plausible type 1 Erdős-adjacent target.

---

## On the Contamination Gate Recalibration

The Author flags that the contamination gate needs recalibration for number-theoretic primitives. This is correct but the Author does not specify *what* recalibration means operationally.

**The current gate's suppression criterion:** A hint is suppressed if it narrows the search space below the suppression threshold — i.e., if the hint uniquely identifies the GT with no free parameters. For analytic forms, this threshold is calibrated to the 26-form library's specificity distribution.

**The recalibration problem:** For number-theoretic primitives, `φ(n) mod 3` is highly specific — it is a function of n that takes only 3 values. If the GT happens to be `φ(n) mod 3`, a hint that says "the residual is periodic with period 3" effectively leaks the GT. The current gate may not suppress this because "periodic with period 3" sounds like a topological descriptor, not a value leak.

**The fix is not recalibration — it is a different suppression criterion.** For number-theoretic primitives, the gate should suppress any hint whose *information content* (in bits) exceeds `log2(library_size)`. A hint that reduces the candidate set from K forms to 1 form is a full leak regardless of whether it looks like a topological descriptor. This is a structural change to the gate, not a parameter adjustment.

**Verdict:** The Author's "recalibration" framing understates the change needed. The gate needs a new suppression criterion for discrete/modular primitives, not just a threshold adjustment.

---

## Flags Against the Seam Itself (Adversarial Checklist)

**Pattern 2 (Closure language):** The seam's "What Needs to Be Built" section says "The substrate generator is the only genuinely new component. Everything downstream already exists." This is closure language that the Author's own turn partially refutes (contamination gate needs structural change, not just recalibration). The seam should remove "only genuinely new component" and replace with an explicit list of components requiring modification vs. reuse.

**Pattern 7 (Instance-anchored generalization):** The architectural mapping table is built from the sandbox_15 case (u²v − u dominant, round(0.08v) corrector). The claim that this maps cleanly to OEIS is an instance-anchored generalization. The seam should name at least one OEIS sequence and trace through the mapping concretely to verify the table holds.

**

### Turn 3 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's turn is the strongest in the debate so far. I'll address each decisive counter-claim in order, then introduce one new structural concern the Skeptic's framing exposes.

---

## On the Dominant-Uncertainty Correction: "Low-Complexity Prior" vs "Analytically Known"

The Skeptic's refinement is correct and I accept it. The failure condition for Component C is topology-change, not level-shift. A constant offset in the dominant estimate leaves the 2-bit descriptor intact; dominant overfitting that introduces spurious oscillations does not. The operative constraint is therefore: **use the simplest dominant that captures leading-order behavior, not the best-fitting one.**

However, the Skeptic's formulation "estimated with a low-complexity prior" needs one more precision: *low-complexity relative to what?* For OEIS sequences, the dominant's complexity should be bounded by the primitive library's expressible forms. If the dominant requires a degree-5 polynomial and the library contains only degree-2 forms, the constraint is violated by construction. The OEIS substrate generator must enforce: **dominant complexity ≤ max complexity of any single library primitive.** This is a concrete implementation constraint, not just a philosophical prior.

**Revised Claim 1:** Structural equivalence holds when the dominant is estimated using a primitive from the same library used for corrector search, with no additional free parameters beyond what the library form requires. This is stronger than "low-complexity prior" and directly implementable as a substrate generator constraint.

---

## On Library Diversity as the Operative Condition for Sweep Advantage

The Skeptic's reframing is correct and superior to my original formulation. The sweep's advantage is a property of the library's disagreement geometry, not of the mutator's distribution. I accept this fully.

One addition: the Skeptic says library diversity "can be audited offline." This is true but the audit needs a concrete protocol. For the analytic library, diversity can be measured as: for each pair of forms (f_i, f_j), compute the set of indices where they disagree. The sweep's advantage is proportional to the *spread* of these disagreement sets — if all pairs disagree only at large n, the sweep must query large n, which may be computationally expensive for number-theoretic sequences. The offline audit should produce a **disagreement heatmap** over the index range, not just a binary "diverse/redundant" verdict. This heatmap determines the expected query index for the sweep and flags whether the sweep is computationally feasible before the run starts.

**Revised Claim 2:** The sweep's advantage is proportional to the library's disagreement diversity, auditable offline via a disagreement heatmap. The heatmap also determines the expected query index and flags computational feasibility.

---

## On the Type 1 / Type 2 Distinction: Concrete Targets

The Skeptic correctly identifies that the seam gestures at type 1 Erdős-class targets without naming them. Here are two concrete candidates that satisfy the criteria:

**Candidate A: A002865 — Partitions of n with no part equal to 1**

- Dominant: Hardy-Ramanujan asymptotic for partitions, adjusted for the no-1-part constraint. The dominant is analytically known (it is a ratio of partition generating functions with a known asymptotic).
- Residual: The gap between the asymptotic and the exact count. This residual has unexplained oscillatory structure in the literature.
- Generator: Computable via recurrence `a(n) = p(n) − p(n−1)` where `p(n)` is the partition function. Cheap to compute.
- Erdős connection: Erdős studied partition residuals extensively; this sequence appears in his work on additive number theory.
- Type: Type 1. The dominant is known; the corrector is the object of search.

**Candidate B: A001694 — Powerful numbers (n where p|n implies p²|n)**

- Dominant: Asymptotic density `a(n) ~ c·√n` where `c = ζ(3/2)/ζ(3)`. The dominant is analytically known.
- Residual: The gap between the asymptotic count and the exact count. The error term is conjectured to be `O(n^(1/3))` but the exact form is unknown.
- Generator: Computable by sieve. Cheap for n < 10^6.
- Type: Type 1. The dominant is known; the corrector is the error term.

Both candidates satisfy: (a) Erdős-adjacent provenance, (b) known dominant with low-complexity prior, (c) unexplained residual, (d) computable generator. A002865 is the better first target because the residual is smaller and the generator is cheaper.

---

## On the Contamination Gate: Information-Content Criterion

The Skeptic's diagnosis is correct: "recalibration" understates the change needed. The current gate suppresses hints that uniquely identify the GT; for discrete/modular primitives, a hint can uniquely identify the GT while appearing to be a topological descriptor. The fix is an information-content criterion.

I want to make the criterion precise: **a hint is suppressed if its information content exceeds `log2(K)` bits, where K is the number of library forms.** For a 26-form library, this is ~4.7 bits. A hint that says "the residual is periodic with period 3" has information content approximately `log2(n/3)` bits where n is the index range — for n=1000, this is ~8.4 bits, which exceeds the threshold and should be suppressed.

**Implementation:** The gate needs a `hint_information_content()` function that estimates the bits of information a hint conveys about the GT, given the library. For topological descriptors (smooth/step × monotone/non-monotone), this is `log2(4) = 2` bits — well below the threshold. For modular descriptors ("periodic with period k"), this is `log2(index_range / k)` bits — potentially above the threshold for small k. The gate suppresses the latter class.

This is a structural addition to the gate, not a parameter adjustment. The Skeptic is right that "recalibration" was the wrong word.

---

## New Decisive Concern: The Feynman Wall Claim Requires a Falsification Criterion

The seam's Claim 3 states: "When no primitive library form survives holdout, this is not failure — it is a signal that the sequence belongs to an undiscovered class." This is the most strategically important claim in the seam, and it is currently unfalsifiable as stated.

**The problem:** "Belongs to an undiscovered class" is not a falsifiable claim. The library could be exhausted because: (a) the sequence genuinely requires a novel form, (b) the library is too small but the form exists in a larger library, (c) the dominant estimation was wrong and the residual is not what we think it is, (d) the holdout gate is miscalibrated and is rejecting valid forms. The seam treats library exhaustion as a discovery signal, but it is equally consistent with apparatus failure.

**What would make Claim 3 falsifiable:** The Feynman Wall should be declared only when: (1) all library forms have been tested and rejected by the holdout gate, (2) the dominant estimation has been verified against an independent method, (3) the holdout gate has been validated on a sequence with a known form (to confirm it is not over-rejecting), and (4) the disagreement heatmap shows the sweep has queried at the maximum-information index. If all four conditions hold and the library is exhausted, *then* library exhaustion is evidence for a novel class.

**Revised Claim 3:** Library exhaustion is a discovery signal *only when the apparatus has been validated on a known-form sequence and the holdout gate is confirmed not to be over-rejecting.* Without this validation, library exhaustion is equally consistent with apparatus failure.

This is a new decisive claim: the seam needs a **validation sequence** — a sequence with a known closed form — run through the full apparatus before any Feynman Wall declaration is trusted. The validation sequence is not in the current "What Needs to Be Built" section.

---

## Summary

I accept the Skeptic's corrections on Claims 1, 2, and the contamination gate. I've added precision to each. The new decisive claim is the Feynman Wall falsification criterion — the seam needs a validation sequence protocol before any discovery claim

### Turn 4 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 3 is the strongest in the debate and I accept the corrections on Claims 1, 2, and the contamination gate. The Feynman Wall falsification criterion is a genuine decisive addition. But before I can raise, I need to press on two residual issues the Author's turn introduces or leaves unresolved.

---

## On the Revised Claim 1: "Dominant Complexity ≤ Max Library Primitive Complexity"

The Author's sharpening — dominant must be drawn from the same library used for corrector search — is cleaner than "low-complexity prior" and I accept the direction. But it introduces a circularity that needs to be named explicitly.

**The circularity:** The corrector library is chosen to express the *corrector*. If the dominant must also be drawn from the same library, then the library must simultaneously be expressive enough to capture the dominant *and* the corrector. For sequences where the dominant is a Hardy-Ramanujan asymptotic (an infinite series involving Bessel functions), no finite primitive library will contain it. The Author's constraint would exclude A002865 — the very candidate the Author proposes as the best first target.

**The resolution:** The constraint should be: dominant complexity ≤ max complexity of any single library primitive *or* the dominant is analytically established in the literature (in which case it is treated as a known constant, not a fitted object). This is a two-branch condition, not a single constraint. The Author's formulation collapses the two branches into one and thereby excludes the most interesting targets.

**Verdict:** Revised Claim 1 needs a two-branch formulation: (a) dominant is drawn from the library with no extra free parameters, OR (b) dominant is analytically established and treated as a known constant. Branch (b) is the operative branch for A002865 and A001694. Without this, the Author's own candidate selection is inconsistent with the Author's own constraint.

---

## On the Validation Sequence Protocol: Scope Creep Risk

The Author's Feynman Wall falsification criterion is correct in principle. The four-condition gate before declaring library exhaustion as a discovery signal is sound. But the Author's proposed implementation — "run a known-form sequence through the full apparatus before any Feynman Wall declaration" — introduces a scope risk that the seam does not currently bound.

**The scope risk:** A validation sequence is not a single run. It is a calibration protocol that must be repeated whenever: (a) the primitive library changes, (b) the holdout gate parameters change, (c) the dominant estimation method changes, or (d) the target sequence class changes (e.g., moving from partition sequences to powerful number sequences). If the validation sequence is treated as a one-time gate, it will be run once and then silently become stale as the apparatus evolves.

**Pattern 2 (Closure language) flag:** The Author says "the seam needs a validation sequence protocol." This implies a single protocol that, once satisfied, clears the Feynman Wall condition permanently. But the validation is apparatus-specific, not sequence-specific. The seam should state: "a validation sequence must be run against the *current apparatus configuration* before any Feynman Wall declaration is trusted." The word "current" is decisive — it prevents the one-time-gate failure mode.

**Proposed addition to the seam:** The "What Needs to Be Built" section should include a `validation_harness.py` that: (1) takes a sequence with a known closed form, (2) runs the full apparatus, (3) verifies the known form is recovered before the Feynman Wall is reached, and (4) is re-run automatically whenever any apparatus component changes. This is a regression test, not a one-time gate.

---

## On the Disagreement Heatmap: Missing Computational Feasibility Bound

The Author accepts the Skeptic's library-diversity framing and adds a concrete protocol: compute a disagreement heatmap over the index range. This is correct. But the Author does not bound the computational cost of the heatmap itself.

**The cost problem:** For a library of K forms and an index range of N, the heatmap requires evaluating K(K−1)/2 pairs at each of N indices. For K=26 and N=10^6, this is ~325 million evaluations. For number-theoretic primitives like `φ(n)` and `σ(n)`, each evaluation requires a factorization — the heatmap computation may be more expensive than the actual sweep. If the heatmap is more expensive than the sweep, it defeats the purpose of the offline audit.

**The fix:** The heatmap should be computed on a *sample* of indices (e.g., 1000 evenly spaced points in the range), not the full range. The sample heatmap gives a statistical estimate of the disagreement structure with O(K²·sample_size) cost. The seam should specify the sample size and the statistical guarantee (e.g., "with 95% confidence, the maximum-disagreement index is within 5% of the true maximum").

This is a minor but concrete addition to the protocol — without it, the "auditable offline" claim is technically true but practically misleading for large-n sequences.

---

## On the Concrete Candidates: A002865 vs A001694

The Author proposes A002865 as the better first target because "the residual is smaller and the generator is cheaper." I want to verify this claim is not instance-anchored.

**The check:** A002865 is defined as `a(n) = p(n) − p(n−1)`. The dominant is the derivative of the Hardy-Ramanujan asymptotic. The residual is the difference between this derivative and the exact count. The Author claims this residual is "smaller" — smaller than what? Smaller than A001694's residual? The comparison requires a common scale, which the seam does not provide.

**The actual selection criterion:** The right criterion for "better first target" is not residual size but *residual structure* — specifically, whether the residual falls within the primitive library's expressible forms. A small residual that requires a novel form is harder than a large residual that is expressible as `floor(n/k)`. The Author should select the target whose residual is most likely to be in the library, not the target with the smallest residual.

**Proposed addition:** The target selection section should include a preliminary residual audit: compute the first 50 terms of the residual for each candidate and check whether any library form fits it to within integer tolerance. This is a 10-line Python script, not an architectural component. If A002865's residual is expressible as a library form, it is the right first target. If not, A001694 may be better despite having a larger residual.

---

## Summary of Remaining Open Items

1. **Revised Claim 1 circularity:** Two-branch dominant condition needed (library-drawn OR analytically established). Author's single-branch formulation excludes the proposed candidates.

2. **Validation sequence scope:** Must be apparatus-specific, not sequence-specific. Needs a `validation_harness.py` that re-runs on apparatus change, not a one-time gate.

3. **Heatmap computational cost:** Sample-based heatmap needed for large-n sequences. Full-range heatmap may be more expensive than the sweep itself.

4. **Target selection criterion:** Residual structure (library expressibility) is the right criterion, not residual size. Preliminary residual audit needed before committing to A002865.

Items 1 and 2 are decisive — they affect the architecture and the validation protocol. Items 3 and 4 are implementation-level but should be resolved before the seam closes to prevent downstream confusion.

---

### Principal Turn 2 — 2026-04-17

**The debate applied Munger's inversion to the engineering but not to the mathematics. This is a material omission.**

The autonomous agents correctly diagnosed that Erdős-Straus is Type 2 (Diophantine/Boolean) and that the current code cannot handle it. That engineering verdict is accepted. But they reached "OEIS first" by the wrong path — they concluded Erdős is blocked because the LLM cannot propose a formula for (a, b, c). They never inverted the mathematical question.

**The inversion the agents missed:**

Do not ask: *"How does the LLM propose a formula satisfying 4/n = 1/a + 1/b + 1/c?"*

Invert: *"What is the smallest n where no (a, b, c) exists?"*

That is the counter-example hunter framing. The LLM's job is not to construct a proof or a formula — it is to propose candidate witness constructions (parameterized search strategies over (a, b, c)) and the divergence sweep finds the n where those strategies maximally disagree. One query at that n either produces a witness (conjecture survives) or proves no witness exists (counter-example found, conjecture dead).

This is not a forward theorem prover. It is an adversarial falsification engine — exactly what ZTARE already is.

**Why OEIS first is still correct despite the inversion:**

The inversion does not change the engineering verdict. It changes *why* we go to OEIS first.

The wrong reason (agents' conclusion): Erdős is Type 2 and ZTARE is Type 1, so Erdős is permanently out of scope.

The right reason: The witness construction library for Erdős (parameterized Diophantine search strategies) does not exist yet. The 26-form analytic library was built for Type 1. A Boolean constraint sidecar — where library primitives output witness sets rather than scalar floats, and the sweep eliminates strategies that fail to find a witness at n* — requires architectural extension. Building that extension before validating the Type 1 engine on real mathematical data is architecture astronaut behavior.

OEIS first because: (1) it validates the Type 1 engine on real data, (2) it produces a publishable result on its own, (3) it forces construction of the number-theoretic primitive library that the Erdős Boolean sidecar will also need. The Erdős substrate is Paper 2, built on Paper 1's validated foundation.

**What needs to be added to the seam:**

A fifth open item — the Erdős route is not permanently closed, it is deferred pending:

1. Successful Type 1 closure on at least one OEIS dark sequence
2. Construction of the number-theoretic primitive library (shared prerequisite)
3. A Boolean constraint sidecar architecture spec (new GP, not in scope here)

The seam should record that the agents' Type 1 / Type 2 distinction is correct as an engineering constraint but wrong as a permanent scope boundary. The Munger inversion frames Erdős as a counter-example hunter problem, which is Type 1-compatible if the library primitives output witness existence (Boolean) rather than scalar residuals — a different output type, not a different architecture class.

**Questions the next debate turn should address:**

1. Is a Boolean output library (witness existence) architecturally compatible with the contamination gate and sweep as currently implemented, or does it require a new sweep variant?
2. Can the OEIS primitive library (ω(n), φ(n), σ(n), floor(n/k)) serve double duty as the foundation for the Erdős Boolean library, or are they disjoint?

### Turn 5 — Claude-Author (2026-04-17) — Autonomous runner turn

The Principal's Turn 2 reframes the Erdős problem correctly, and I want to engage with it precisely before deciding whether to raise.

---

## On the Munger Inversion: Counter-Example Hunter vs Formula Proposer

The Principal's inversion is valid and I accept it as a genuine architectural reframe. The LLM's job in the Erdős-Straus case is not "propose a formula for (a,b,c)" but "propose a parameterized witness construction strategy, and let the sweep find n where strategies maximally disagree." This is structurally closer to ZTARE's existing loop than the agents' Type 2 framing suggested.

However, I want to be precise about what "architecturally compatible" means here, because the Principal's two questions are the right ones and they have non-trivial answers.

---

## On Question 1: Boolean Output Library and the Contamination Gate

The contamination gate's current suppression criterion is calibrated for scalar residuals. The information-content criterion I proposed in Turn 3 — suppress hints whose information content exceeds `log2(K)` bits — applies to hints about *which library form* the corrector is. For a Boolean output library, the "hint" is not "the residual looks like floor(n/k)" but "strategy S finds a witness for n in range [a,b]." These are different objects.

**The structural question:** Does the contamination gate's suppression logic transfer to Boolean outputs?

The gate suppresses hints that narrow the candidate set below the suppression threshold. For scalar residuals, "candidate set" means "set of library forms." For Boolean outputs, "candidate set" means "set of witness construction strategies." The suppression criterion is the same in structure: suppress if the hint reduces the strategy set to fewer than K/threshold candidates. The gate transfers *in principle* — the suppression logic is strategy-agnostic.

**The non-trivial part:** For scalar residuals, the hint is derived from the *shape* of the residual (2-bit descriptor). For Boolean outputs, the analogous hint would be derived from the *structure* of the witness set — e.g., "witnesses for n < 100 all have a ≤ n/2." This is a structural descriptor of the witness set, not a scalar measurement. The Component C machinery (Mutator-Dominant Subtraction, shape classification) does not directly apply — it would need a Boolean analog: "Witness-Set Subtraction" where the dominant strategy's witness set is subtracted from the full witness space to isolate the residual structure.

**Verdict on Question 1:** The contamination gate transfers in principle but Component C does not transfer directly. A Boolean analog of Component C is needed — call it Component C_B. It is a new component but not a new *architecture class*. The sweep and structural memory transfer unchanged. The implementation delta is Component C_B, not a rewrite.

---

## On Question 2: OEIS Primitive Library as Foundation for Erdős Boolean Library

The OEIS primitive library (ω(n), φ(n), σ(n), floor(n/k), n mod k) and the Erdős Boolean library are not disjoint — they share a significant substrate. Here is the precise overlap:

**Shared primitives:** `floor(n/k)`, `n mod k`, `φ(n)`, `ω(n)` — these appear in both the OEIS residual context (as corrector forms) and in the Erdős witness construction context (as components of parameterized search strategies). For example, a witness construction for Erdős-Straus might be: "try a = floor(n/2), b = floor(n/3), solve for c" — this uses `floor(n/k)` directly.

**Divergence point:** The OEIS library needs primitives that output *scalars* (the corrector value at index n). The Erdős Boolean library needs primitives that output *witness sets* (the set of (a,b,c) triples satisfying the constraint for a given n). The same arithmetic functions appear in both, but their output types differ. This is not a fundamental incompatibility — it is a wrapper difference. The same `φ(n)` computation can be used as a scalar corrector in OEIS mode and as a component of a witness construction in Erdős mode.

**Practical implication:** Building the OEIS primitive library first gives us the arithmetic substrate for free. The Erdős Boolean library is then built by wrapping the same primitives in witness-construction strategies rather than scalar evaluations. The shared prerequisite is real — the Principal's sequencing argument is correct on this point.

**One caveat:** The Erdős Boolean library needs a *combinatorial search* layer that the OEIS library does not need. For Erdős-Straus, finding (a,b,c) given n requires iterating over candidate values of a and solving for (b,c) — this is a search procedure, not a closed-form evaluation. The OEIS library has no analog of this. The Boolean library is therefore a *superset* of the OEIS library, not a renaming of it. The shared foundation is real but incomplete.

---

## Revised Seam Structure: What Needs to Be Added

Based on the full debate, the seam's "What Needs to Be Built" section needs the following additions:

1. **Two-branch dominant condition** (from Skeptic Turn 4): dominant is either (a) drawn from the library with no extra free parameters, OR (b) analytically established in the literature and treated as a known constant.

2. **Validation harness** (apparatus-specific, not sequence-specific): `validation_harness.py` that re-runs on apparatus change, not a one-time gate.

3. **Sample-based disagreement heatmap**: O(K² · sample_size) cost, not full-range.

4. **Preliminary residual audit**: 10-line Python script checking whether candidate sequence residuals fall within the library's expressible forms before committing to a target.

5. **Erdős deferred path** (from Principal Turn 2): record that the Type 1/Type 2 distinction is an engineering constraint, not a permanent scope boundary. Erdős is Paper 2, contingent on: (a) Type 1 closure on one OEIS dark sequence, (b) number-theoretic primitive library construction, (c) Component C_B spec (new GP).

6. **Component C_B spec stub**: Boolean analog of Component C for witness-set structural description. New GP, not in scope for this seam, but the seam should name it as a dependency.

---

## On Convergence

The debate has resolved the four major structural questions:
- Claim 1 (structural equivalence): narrowed to two-branch dominant condition ✓
- Claim 2 (sweep advantage): reframed as library diversity, auditable via heatmap ✓
- Claim 3 (Feynman Wall): requires validation harness, apparatus-specific ✓
- Type 1/Type 2 distinction: correct as engineering constraint, not permanent scope boundary ✓
- Contamination gate: information-content criterion, structural change not recalibration ✓
- Erdős deferred path: Component C_B as new GP dependency ✓

The remaining open items (two-branch dominant, validation harness scope, heatmap cost, residual audit, Erdős deferred path, Component C_B stub) are all implementation-level additions to the seam's "What Needs to Be Built" section. None of them change the architecture's decisive structure — they sharpen the implementation protocol.

I have no new decisive architectural claims to introduce. The Skeptic's Turn 4 items are addressed. The Principal's Turn 2 questions are answered. The seam is ready to converge from my side, contingent on the Skeptic confirming that the two-branch dominant condition and the validation harness scope are resolved to their satisfaction.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 5 is the most complete turn in the debate and I am close to raising. But two items from my Turn 4 remain partially unresolved, and the Author's answers to the Principal's questions introduce one new precision gap I need to name before I can raise in good conscience.

---

## On the Two-Branch Dominant Condition: Circularity Resolved?

The Author accepts the two-branch formulation. But the seam text has not been updated — the "What Needs to Be Built" section still says "The substrate generator is the only genuinely new component" (Pattern 2 closure language I flagged in Turn 2). The Author's Turn 5 lists six additions to that section, but those additions exist only in the debate log, not in the seam body. If the seam closes now, a cold reader sees the old closure language and misses the two-branch condition entirely.

This is not a new decisive claim — it is a record-keeping gap. The seam body must be updated before closure, not after. The debate has converged on the content; the artifact has not caught up.

---

## On the Validation Harness: "Re-runs on Apparatus Change" Is Not Operationalized

The Author accepts that the validation harness must be apparatus-specific and re-run on apparatus change. But "apparatus change" is not defined. The apparatus has at least six components that could change independently: primitive library, dominant estimation method, holdout gate parameters, contamination gate suppression criterion, Component C shape classifier, sweep budget. A change to any one of these could invalidate a prior validation run.

The seam needs to specify the trigger condition precisely. Two options:

**Option A (conservative):** Re-run validation whenever *any* apparatus component changes. This is safe but expensive — a one-line fix to the contamination gate triggers a full validation run.

**Option B (targeted):** Maintain a component dependency graph. The validation harness declares which components it exercises. A change to component X triggers re-validation only if X is in the dependency graph. This is more efficient but requires maintaining the graph.

The Author's formulation implies Option A without saying so. Option B is probably the right engineering choice but requires the dependency graph to be explicit. The seam should pick one and state it. Without this, "re-run on apparatus change" is a principle without an implementation trigger — it will be forgotten the first time a "minor" fix is made.

This is a concrete implementation gap, not a philosophical one. It affects whether the validation harness actually functions as a regression test or silently becomes stale.

---

## On Component C_B: The Author's Answer Introduces a Precision Gap

The Author correctly identifies that Component C_B needs a "Witness-Set Subtraction" analog to Mutator-Dominant Subtraction. But the Author's framing — "the dominant strategy's witness set is subtracted from the full witness space to isolate the residual structure" — is not well-defined for Erdős-Straus.

**The precision gap:** In the scalar case, "Mutator-Dominant Subtraction" is `f_true(u,v) − f_dominant(u,v)` — a pointwise arithmetic operation. In the Boolean case, "Witness-Set Subtraction" would be something like "the set of n where the dominant strategy fails to find a witness." But this is not a subtraction — it is a *failure set*. The failure set of the dominant strategy is the object of interest, not the difference between two witness sets.

This matters because the contamination gate's information-content criterion is calibrated to the *size* of the candidate set reduction. For scalar residuals, the hint reduces the form library from K forms to fewer. For Boolean outputs, the analogous reduction is from K strategies to fewer — but the "hint" is now "the dominant strategy fails at n in set S," which is a set-valued object. The information content of a set-valued hint is `log2(2^|index_range|)` in the worst case — potentially unbounded.

The Author says Component C_B is "a new component but not a new architecture class." I accept the architecture-class claim but flag that the contamination gate's information-content criterion may not transfer to set-valued hints without a new bounding argument. This is a dependency the Component C_B spec stub must acknowledge.

**This is not a blocker for the current seam** — Component C_B is explicitly deferred to a new GP. But the seam's stub should note this open question so the new GP inherits it cleanly rather than rediscovering it.

---

## Flags Against the Seam Body (Final Pass)

**Pattern 2 (Closure language, still present):** "The substrate generator is the only genuinely new component. Everything downstream already exists." This sentence is now demonstrably false given the debate's conclusions (contamination gate structural change, validation harness, Component C_B). Must be removed or replaced before the seam closes.

**Pattern 6 (Scope creep into sealed pre-registrations):** Not applicable — no pre-registration is sealed for this seam yet. Clean.

**Pattern 9 (Code-vs-memory drift):** The Author's Turn 5 references the contamination gate's "current suppression criterion" without citing a file:line. Since no implementation exists yet for the OEIS substrate, this is forward-looking prose, not a stale citation. Acceptable.

---

## Summary

The debate has converged on all decisive architectural questions. The remaining items are:

1. **Seam body must be updated** with the six additions from Author Turn 5 before closure. The debate log is not the artifact.
2. **Validation harness trigger condition** must be operationalized (Option A or Option B, stated explicitly).
3. **Component C_B stub** should note the set-valued hint / contamination gate open question as an inherited dependency for the new GP.

Items 1 and 2 are seam-update tasks, not new architectural claims. Item 3 is a note to add to the stub. None of these change the architecture's decisive structure — they are record-keeping and implementation-precision gaps.

I have no new decisive architectural claims to introduce. If the Author confirms that the seam body will be updated with the six additions, the validation harness trigger will be operationalized, and the Component C_B stub will note the set-valued hint question, I am ready to raise.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->
