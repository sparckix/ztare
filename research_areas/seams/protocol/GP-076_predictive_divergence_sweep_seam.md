# GP-076 — Predictive Divergence Sweep: Breaking Corrector Degeneracy Without Oracle Access

> **Seam metadata** · `seam_id:` GP-076 · `track:` protocol · `status:` Active - opened 2026-04-16 · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

## Status

Active — opened 2026-04-16

## ID

GP-076

## Eigenquestion

When multiple corrector forms perfectly fit visible evidence, can the system break the degeneracy by finding where candidates disagree and querying there — without using the ground truth, without leaking the holdout, and without replacing the LLM's role as topology proposer?

## Problem Statement

Sandbox_15 (GP-074) exposed a structural gap in ZTARE's cognitive gym. The GT corrector `round(0.08*v)` IS in the 26-form library. Component C fires and narrows from 26 to ~7 step/monotone candidates. The SciPy fitter achieves max_abs_residual=0.0 on visible data for ALL 7 candidates. The holdout gate kills all 7 with score 0 but provides no gradient. The mutator random-walks among 7 geometrically equivalent candidates indefinitely. After 8+ iterations: zero progress, zero signal.

**Root cause:** Visible evidence (v=1..16) contains exactly one step transition (0→1 at v=7). Any step function can explain one step. The system has no mechanism to distinguish candidates that agree on visible data but disagree on holdout.

**What doesn't work (validated by four independent expert reviews):**

1. **BIC/MDL sweep** — Fatal flaw: `round(k*v)` and `Heaviside(v-k)` have identical BIC (same parameter count, same residual). The proposal cannot solve the stated problem.

2. **LLM-based selection among library forms** — With 26 forms and SciPy, exhaustive enumeration takes <1 second. The LLM adds zero value for finite library selection. Its value is upstream (proposing novel topologies not in the library).

3. **Complexity penalties / parsimony hard caps** — A correct 4-parameter model gets penalized alongside wrong 4-parameter models. Parameter count is a poor proxy for descriptive quality when the library contains structurally heterogeneous forms.

**What the experts converge on:** Sequential experimental design. When N candidates fit visible data equally, find the input value where they maximally disagree, query there, eliminate losers. This is a 200-year-old idea (active learning / optimal experimental design). It generalizes to unknown GT because it uses only the candidates' own predictions and one observation.

**Origin:** GP-074 sandbox_15 experiment, iterations 1-8 (all score 0). Four-expert adversarial review: systems/ML, philosophy of science, symbolic regression, multidisciplinary (Munger).

## Scope

**Covers:**
- Deterministic exhaustive library sweep when Component C narrows the candidate set
- Predictive divergence computation: where do surviving candidates maximally disagree?
- Controlled single-point query at the divergence point (not full holdout disclosure)
- Information boundary: what gets revealed to the mutator vs. what stays hidden
- Generalization test: does this work without GT access (the "Dark Data" constraint)?

**Does not cover:**
- Changes to Component C's 2-bit descriptor (separate concern, GP-074)
- Changes to the holdout gate scoring mechanism
- LLM topology proposal (the mutator's role for forms NOT in the library)
- Rubric or judge modifications
- Extension of the corrector library itself

## Option Analysis

### Option A — Exhaustive Library Sweep + Predictive Divergence Query

When Component C narrows the library to N matching forms:

1. **Deterministic sweep:** The sidecar fits ALL N forms to visible data using SciPy. Cost: milliseconds. No LLM involved.
2. **Filter:** Keep only forms with residual below threshold (e.g., max_abs_residual < 1.0).
3. **Divergence computation:** For each pair of surviving forms, compute the v-value where their predictions maximally disagree. Pick the single v-value with highest aggregate disagreement across all pairs.
4. **Single-point query:** Evaluate f_true at that v-value. Report the observed value to the mutator alongside the candidates' predictions at that point.
5. **Elimination:** Drop candidates whose prediction at the divergence point mismatches the observation. Surviving candidates become the champion pool.

**GT-independence test:** Step 4 queries f_true at one point. In a sandbox, f_true is the known GT function. In deployment against real data, f_true is replaced by "run the experiment / measure the phenomenon at this input." This is what scientists do: design a crucial experiment where rival theories predict different outcomes, then go look. The mechanism is observation-dependent, not GT-dependent.

**Contamination analysis:** One observed value at one point reveals almost nothing about the GT functional form. The mutator learns "at v=19, the corrector produces value 2" — which is one data point, not a function. The contamination gate should verify that the single point does not uniquely determine the corrector form (enumerate library forms consistent with visible data + the new point; if count < N, suppress).

**Verdict: LEADING CANDIDATE.** Solves the stated problem. Generalizes to unknown GT. Preserves separation of concerns (LLM proposes outer topology, deterministic machinery handles library selection). One observation point is the minimum possible information disclosure.

### Option B — Extended Visible Evidence Window

Instead of querying a specific point, reveal additional evidence points (e.g., v=17..20) after stagnation is detected.

**Verdict: VIABLE BUT LESS TARGETED.** Reveals more information than necessary. 4 new points might break the degeneracy or might not (if the divergence region is v=25+). The predictive divergence approach (Option A) is strictly more efficient because it targets the exact point of maximum disagreement.

**Risk:** Changes the experimental protocol and weakens comparability across sandboxes.

### Option C — Holdout Loss Surface (Non-Binary Gate)

Instead of binary pass/fail, the holdout gate returns a scalar loss (e.g., fraction of holdout points matched) without revealing which points failed.

**Verdict: VIABLE BUT HIGHER LEAK SURFACE.** A scalar loss across all holdout points reveals more than a single targeted query. Expert 1 (systems/ML) flagged this as a contamination risk. The Philosopher noted the holdout gate "compresses a rich failure surface into a scalar" — but Option A's single-point query is a more controlled way to provide gradient without broad holdout exposure.

### Option D — Pareto Front (Tree-Size Complexity vs. Residual)

Expert 3 (symbolic regression) recommended ranking by expression tree size instead of parameter count. `Heaviside(v-7)` is 3 nodes; `round(0.08*v)` is 4 nodes.

**Verdict: INSUFFICIENT ALONE.** Tree-size ranking might break some ties but not all. Two 3-node expressions can still produce identical residuals. Pareto ranking is a useful secondary signal but does not solve the fundamental underdetermination. Can be combined with Option A.

### Option E — Popperian Falsifiability Preference

Expert 3 noted: prefer `round(k*v)` over `Heaviside(v-k)` because round predicts a second step (more falsifiable = more scientifically useful). Operationalize as: among tied candidates, prefer the one that makes the most out-of-sample predictions.

**Verdict: ELEGANT BUT HARD TO IMPLEMENT.** "Makes the most predictions" is not a well-defined computable property for arbitrary functional forms. A form's prediction count depends on the input domain. Practically, this is what Option A achieves: by querying where candidates disagree, the form that predicted correctly has survived a falsification attempt the others failed.

## Open Questions

1. **Stagnation trigger or every iteration?** The exhaustive sweep is cheap (milliseconds), but the single-point query reveals information. Should the query fire only after N iterations of stagnation (limiting information disclosure), or every iteration (maximal disambiguation speed)?

2. **Multi-point queries.** If one point does not break the degeneracy (two surviving candidates agree at the queried point by chance), should the system query a second point? What is the information budget per run?

3. **Integration with Component C.** Does the predictive divergence sweep replace Component C's role, extend it, or operate independently? If Component C narrows to 7 candidates and the sweep further narrows to 1, is Component C still needed?

4. **Forms NOT in the library.** When the mutator proposes a form not in the library (the common case for novel science), the exhaustive library sweep doesn't apply. The predictive divergence approach could still compare the mutator's candidate against library forms, but this changes the mechanism: instead of "which library form wins?" it becomes "does ANY library form beat the mutator's proposal?"

5. **The Feynman Wall.** If the GT corrector is not in the library (e.g., `round(m*v/sqrt(1-v²/225))`), the exhaustive sweep will select the best-fitting library form, which is wrong. Does the system correctly fall back to the LLM's novel topology proposal when no library form survives the holdout gate?

## Debate Log

### Turn 1 — Claude-Author (2026-04-16 23:30:00 EDT) — Opening: five options from four-expert synthesis, one leading candidate

Opened from GP-074 sandbox_15 stagnation finding (iterations 1-8, all score 0 with corrector in library).

Four independent expert reviews conducted:
- **Systems/ML expert:** BIC fatally flawed (identical BIC for degenerate candidates). Component C GT-dependent. Fix evidence window or descriptor.
- **Philosopher of science:** Component C is observation-dependent, not GT-dependent (probing residuals = running an experiment). BIC wrong primitive (counts parameters not description length). Real problem: information destruction (holdout compresses failure surface to scalar).
- **Symbolic regression expert:** Exhaustive enumeration trivial for 26 forms. Pareto front + predictive divergence testing. LLM adds zero value for library selection.
- **Munger multidisciplinary:** Neutral drift on flat fitness landscape. Stop asking "which theory is right?" — ask "where do they disagree?" Sequential experimental design is a 200-year-old solved problem.

Convergence across all four: the fix is upstream (find where candidates disagree and query there), not downstream (better selection criterion among indistinguishable candidates).

Option A (exhaustive sweep + predictive divergence query) is the leading candidate. It satisfies:
- GT-independence: queries one observation point, equivalent to "run the experiment"
- Separation of concerns: deterministic machinery does the search, LLM stays on topology
- Minimum information disclosure: one point, not the full holdout
- The Popperian test: the surviving candidate is the one that stuck its neck out and was right

Decisive claims I am introducing:
1. BIC/MDL is the wrong axis for this problem (four-expert consensus)
2. The LLM should not select from a finite library (exhaustive enumeration dominates)
3. Predictive divergence query generalizes to Dark Data (observation, not oracle)
4. One-point query is minimum sufficient information to break corrector degeneracy

Next: skeptic turn to stress-test the single-point query's contamination boundary and the "forms not in library" fallback.

### Turn 2 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's opening is well-structured and the four-expert synthesis is genuinely useful. I'll work through the decisive claims systematically.

**On Claim 1: BIC/MDL is the wrong axis**

The Author correctly identifies that `round(k*v)` and `Heaviside(v-k)` have identical BIC when parameter count and residual are equal. This is sound. However, the Author's dismissal of BIC is slightly overreaching. The claim should be scoped: "BIC is insufficient *alone* for this specific degeneracy class." BIC remains a valid secondary signal for cases where parameter counts differ. The seam's Option D (Pareto front by tree size) is a BIC-adjacent idea that the Author endorses as a "useful secondary signal" — which is inconsistent with the blanket dismissal of complexity penalties in the "What doesn't work" section. This is a minor inconsistency, not a fatal flaw, but it should be reconciled: either BIC-family metrics are wrong primitives (and Option D should be demoted), or they are insufficient-alone (and the "What doesn't work" framing is too strong).

**On Claim 2: LLM should not select from a finite library**

Agreed. Exhaustive enumeration of 26 forms with SciPy is trivially cheap. The LLM's comparative advantage is topology proposal for forms *outside* the library. This claim is sound and well-supported.

**On Claim 3: Predictive divergence query generalizes to Dark Data**

This is the most important decisive claim and it has a gap the Author has not addressed.

The Author states: "In deployment against real data, f_true is replaced by 'run the experiment / measure the phenomenon at this input.'" This is correct in principle. But the contamination analysis is incomplete. The Author writes: "enumerate library forms consistent with visible data + the new point; if count < N, suppress." This suppression rule has a critical flaw: **it suppresses the query when it would be most useful**.

If the single-point query reduces the surviving candidate count from 7 to 1, the suppression rule fires (count < N = 7), and the query is suppressed. But that is exactly the case where the query is most valuable — it uniquely identifies the correct form. The suppression rule as stated would prevent the system from ever using a query that fully resolves the degeneracy.

The Author needs to clarify: what is the suppression criterion actually protecting against? If it's protecting against "the mutator can infer the GT form from the observation," then the threshold should be "if count = 1, suppress" (unique determination). If it's protecting against "the observation reveals too much about the GT function's global behavior," then the criterion needs to be information-theoretic, not count-based.

This is a decisive gap: the contamination gate as described either (a) suppresses the most useful queries, or (b) is not actually protecting what the Author thinks it's protecting.

**On Claim 4: One-point query is minimum sufficient information**

This claim is asserted but not demonstrated. The Author needs to show that one point is *sufficient* to break the degeneracy in the typical case, not just that it is the *minimum* possible disclosure. These are different claims.

Consider: if the 7 surviving candidates all agree at the single divergence point (by coincidence or by construction), one point is not sufficient. The Author acknowledges this in Open Question 2 but treats it as an edge case. It may not be an edge case. For step functions with integer thresholds, the divergence point is the threshold itself — and two step functions with adjacent thresholds (e.g., `Heaviside(v-7)` vs `Heaviside(v-8)`) will agree at all integer points except v=7 and v=8. If the visible window already contains v=7, the divergence point is v=8, and one query resolves the tie. But if the library contains `Heaviside(v-7)`, `Heaviside(v-8)`, and `Heaviside(v-9)`, a single query at v=8 eliminates one candidate but leaves two. The Author should characterize the expected number of queries needed to fully resolve degeneracy for the specific library structure, not just assert "one point."

**On Open Question 5: The Feynman Wall**

The Author raises this but does not answer it. This is a decisive architectural question, not a minor open question. If the GT corrector is not in the library, the exhaustive sweep selects the best-fitting library form, which is wrong. The Author asks "does the system correctly fall back to the LLM's novel topology proposal?" but provides no mechanism for this fallback.

The failure mode is: Component C fires, narrows to 7 candidates, exhaustive sweep runs, best library form achieves max_abs_residual=0.0 on visible data, predictive divergence query selects it, holdout gate kills it with score 0. The system is now stuck in a different way: it has "selected" a library form that is wrong, and the mutator has no signal to escape to a novel topology. The predictive divergence mechanism may actually *worsen* the Feynman Wall case by giving the system false confidence in a library form.

The seam needs an explicit fallback: when the selected library form fails the holdout gate, the system must signal "library exhausted, escalate to LLM topology proposal." Without this, Option A solves the in-library degeneracy problem while creating a new trap for the out-of-library case.

**On the stagnation trigger (Open Question 1)**

The Author frames this as a minor design choice. It is not. The choice between "fire every iteration" and "fire after N stagnation iterations" determines the information budget of the entire run. If the query fires every iteration and each query reveals one point, a 10-iteration run reveals 10 points — potentially enough to reconstruct the GT function. The Author's contamination analysis assumes one query total; it needs to be extended to the multi-query case.

**Summary of decisive flags:**

1. The suppression rule in the contamination gate is self-defeating: it suppresses the most useful queries (those that uniquely resolve degeneracy). Needs redesign.
2. "One-point query is minimum sufficient" is asserted, not demonstrated. The typical number of queries needed for the specific library structure should be characterized.
3. The Feynman Wall fallback is missing. Option A may worsen the out-of-library case without an explicit escalation mechanism.
4. The stagnation trigger choice has first-order consequences for the information budget that the Author has not analyzed.

The leading candidate (Option A) is directionally correct. The contamination gate and the Feynman Wall fallback are the two gaps that must be resolved before this seam can converge.

### Turn 3 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 2 raises four flags. I'll address each in order of decisive weight, then state what I'm accepting, what I'm revising, and what remains genuinely open.

---

## On the suppression rule: the Skeptic is right, and the fix is straightforward

The contamination gate as written ("if count < N, suppress") is self-defeating. The Skeptic correctly identifies the inversion: the query is most valuable precisely when it reduces the candidate count maximally. The suppression rule would fire hardest on the most informative queries.

**What the gate is actually protecting against:** The concern is not "the query resolves the degeneracy" — that is the goal. The concern is "the query reveals enough about the GT function's global behavior that the mutator can reconstruct the GT without further search." These are different.

**Revised contamination criterion:** Suppress the query if and only if the single observed value, combined with visible data, uniquely determines the GT functional form *across the full input domain* — not just within the library. Operationally:

- Enumerate all library forms consistent with visible data + the new point. If count ≥ 2, the query is safe (degeneracy is reduced but not eliminated; the mutator still has to search).
- If count = 1 *and* the surviving form is a closed-form expression that fully specifies the GT (no free parameters remaining), suppress. The query would hand the mutator the answer.
- If count = 1 *and* the surviving form still has free parameters (e.g., `round(k*v)` with k unresolved), the query is safe — it identifies the family but not the instance.

This is a count-based criterion but with the threshold at 1 (unique determination with no free parameters), not at N. The Skeptic's framing "if count = 1, suppress" is close but slightly too aggressive — it would suppress a query that identifies the correct family while leaving a parameter free, which is not a contamination event.

**WWYHTB:** This revised criterion rests on the belief that "family identification without parameter determination" is not a contamination event. I hold this belief because the mutator still has to fit the parameter — it has not been handed the GT. If this belief is wrong (e.g., the parameter is trivially recoverable from one additional visible point), the criterion needs tightening. I am flagging this as a residual uncertainty, not papering over it.

---

## On "one-point query is minimum sufficient": the Skeptic is right to push back

I conflated two claims: (a) one point is the minimum possible disclosure, and (b) one point is typically sufficient to resolve the degeneracy. These are different, and I only demonstrated (a).

**What I can demonstrate for the specific library structure:** For the GP-074 case (step/monotone candidates, integer thresholds, visible window v=1..16), the divergence point is the first integer outside the visible window where candidates disagree. For `Heaviside(v-7)` vs `Heaviside(v-8)`, the divergence point is v=17 (both agree at v=7 since it's in the visible window; they first disagree at v=17 where one steps and the other doesn't). One query at v=17 eliminates one candidate. For a library with k step-function candidates at thresholds 7, 8, ..., 7+k-1, the expected number of queries to fully resolve is O(log k) with binary search on the threshold, or O(k) with sequential queries. For k=7, this is at most 7 queries.

**What I cannot demonstrate in general:** For arbitrary library structures (non-step functions, non-integer parameters), the expected query count depends on the geometry of the candidate predictions. I should not have asserted "one point" as a general claim.

**Revised claim:** One point is the minimum possible disclosure per query. The number of queries needed to fully resolve degeneracy is bounded by the library size (O(N) worst case) and is typically O(log N) with optimal divergence point selection. For the specific GP-074 library structure, empirical characterization is needed before claiming "one query suffices."

---

## On the Feynman Wall fallback: the Skeptic identifies a genuine architectural gap

The Skeptic is correct that Option A may worsen the out-of-library case. The failure mode is real: exhaustive sweep selects the best-fitting library form, predictive divergence query "confirms" it, holdout gate kills it, mutator is stuck with false confidence in a library form.

**The fallback mechanism:** When the selected library form fails the holdout gate after the predictive divergence query has been applied, the system must emit a signal: "library exhausted." This signal should:

1. Suppress further library-sweep iterations (the library has been exhausted; re-running it wastes queries).
2. Escalate to the LLM topology proposal mode: the mutator is told "no library form survived holdout; propose a novel functional form."
3. Preserve the divergence query observations as additional visible evidence for the LLM's novel proposal (the LLM now has v=1..16 plus the divergence query points as training data).

**Why this doesn't worsen the Feynman Wall:** Without Option A, the mutator random-walks among library forms indefinitely. With Option A + the fallback, the mutator exhausts the library in O(N) queries and then escalates. The Feynman Wall case is not worsened — it is resolved faster (library exhaustion is detected explicitly rather than by indefinite stagnation).

**What I'm accepting from the Skeptic:** The seam must include an explicit "library exhausted" signal and escalation path. This is not a minor open question — it is a required component of Option A's architecture.

---

## On the stagnation trigger: the Skeptic is right that this has first-order consequences

The information budget analysis I omitted is real. Let me provide it now.

**If the query fires every iteration:** A 10-iteration run reveals up to 10 divergence points. For a library of 26 forms, 10 points may be sufficient to reconstruct the GT function (depending on the function's complexity). This is a contamination risk.

**If the query fires only after N stagnation iterations:** The information budget is bounded by (run_length / N). For N=3 and 10 iterations, at most 3 queries. For N=5, at most 2 queries.

**Proposed resolution:** The query fires only after stagnation is detected (N consecutive iterations with no score improvement). N should be set to at least 3. The total query budget per run should be capped at min(library_size, run_length / 3). This bounds the information disclosure to O(library_size) points total, which is the minimum needed to exhaust the library.

**WWYHTB:** This rests on the belief that O(library_size) points is not sufficient to reconstruct an arbitrary GT function. For the specific library structures we're targeting (step functions, polynomial correctors), this belief is plausible but not proven. If the GT function is simple enough that library_size points uniquely determine it, the cap needs to be tighter.

---

## On the BIC inconsistency: the Skeptic is right, and I'll reconcile

The "What doesn't work" section says complexity penalties are wrong; Option D endorses tree-size as a "useful secondary signal." These are inconsistent.

**Reconciled position:** BIC/MDL with parameter count is the wrong primitive for this specific degeneracy class (degenerate candidates have identical parameter counts by construction). Tree-size (Option D) is a different complexity measure that may break some ties BIC cannot. The correct framing is: "parameter-count-based complexity penalties are insufficient for this degeneracy class; tree-size is a potentially useful secondary signal but does not solve the fundamental underdetermination." The "What doesn't work" section should be scoped to parameter-count-based BIC, not complexity penalties in general.

---

## Summary of what I'm accepting, revising, and holding

**Accepting from the Skeptic:**
- The suppression rule needs redesign (threshold at unique-determination-with-no-free-parameters, not at count < N)
- "One-point sufficient" is not demonstrated; the claim should be scoped to "minimum disclosure per query, O(N) queries to exhaust library"
- The Feynman Wall fallback is a required architectural component, not an open question
- The stagnation trigger has first-order information budget consequences that must be analyzed

**Revising in the seam:**

### Turn 4 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 3 is substantive and addresses all four flags I raised. Let me work through each resolution carefully before deciding whether to raise or hold.

**On the suppression rule revision**

The Author's revised criterion — suppress only when count = 1 AND no free parameters remain — is a genuine improvement over the original. The distinction between "family identification" and "instance determination" is meaningful. However, there is a residual gap the Author acknowledges but does not fully resolve: "if the parameter is trivially recoverable from one additional visible point, the criterion needs tightening."

This is not a minor caveat. For `round(k*v)`, the parameter k is recoverable from any single point where the corrector is nonzero: if the query reveals corrector(v=19) = 2, then k ≈ 2/19 ≈ 0.105, which combined with the visible data (corrector(v=7) = 1, corrector(v=14) = 1) pins k to approximately 0.08. The "family identified, parameter free" case may be a distinction without a difference for the specific library structures ZTARE targets. The Author flags this as a "residual uncertainty" — I accept that framing, but it means the contamination gate is not yet fully specified. It is better than before, not complete.

I will not hold on this point because the Author has correctly identified the gap and the direction of the fix. The residual uncertainty is real but does not block convergence — it is a calibration question for implementation, not an architectural flaw.

**On the query count claim**

The Author correctly retracts the "one point is sufficient" assertion and replaces it with "O(log N) with optimal selection, O(N) worst case." The O(log N) claim for binary search on step-function thresholds is sound for that specific structure. The Author appropriately scopes the general claim as requiring empirical characterization. This is an honest revision and I accept it.

**On the Feynman Wall fallback**

The Author proposes: detect library exhaustion, suppress further library sweeps, escalate to LLM topology proposal, preserve divergence query observations as additional training data. This is architecturally sound. The Author's argument that "without Option A, the mutator random-walks indefinitely; with Option A + fallback, library exhaustion is detected explicitly" is correct. Option A does not worsen the Feynman Wall — it converts indefinite stagnation into bounded exhaustion followed by escalation. I accept this resolution.

One minor note: the Author says "preserve the divergence query observations as additional visible evidence for the LLM's novel proposal." This is correct and important — the divergence query points are legitimate observations (not oracle leaks) and should be treated as extended training data. The seam should make this explicit in the architecture description, not just in the debate log.

**On the stagnation trigger and information budget**

The Author proposes: fire after N≥3 stagnation iterations, cap total queries at min(library_size, run_length/3). The analysis is sound. The WWYHTB caveat — "O(library_size) points may be sufficient to reconstruct a simple GT function" — is real but bounded. For the specific library structures targeted (step functions, polynomial correctors), the GT functions are simple enough that this risk is non-negligible. However, the Author's proposed cap is a reasonable engineering bound, and the residual risk is acknowledged rather than papered over.

**On the BIC inconsistency**

The Author's reconciled position — "parameter-count BIC is wrong for this degeneracy class; tree-size is a potentially useful secondary signal" — is correct and consistent. The "What doesn't work" section should be updated to reflect this scoping. I accept the reconciliation.

**One new observation I want to raise before deciding**

The Author's Turn 3 commits to several architectural components (revised suppression criterion, library exhaustion signal, stagnation trigger with cap) but these commitments live in the debate log, not in the seam's Option Analysis or Open Questions sections. The seam as written still contains the original (flawed) contamination gate description and still lists the Feynman Wall as an "open question" rather than a "required component with specified mechanism."

This is a process question, not a decisive architectural claim: the seam needs to be updated to reflect the debate's resolutions before it can be treated as converged. The debate has produced genuine architectural progress, but that progress is currently only in the debate log. A cold reader of the seam's Option Analysis section would encounter the original self-defeating suppression rule and the unresolved Feynman Wall.

I am not holding on this as a new decisive claim — the Author has resolved the substance. But I want to flag explicitly: convergence of the debate does not mean the seam artifact is ready to close. The seam's Option A description, contamination gate specification, and Open Questions section need to be updated to reflect Turns 2-3 before the seam is promoted.

**Verdict**

The Author has addressed all four decisive flags from Turn 2. The residual uncertainties (parameter recoverability in the suppression criterion, empirical query count characterization) are acknowledged and scoped correctly — they are implementation calibration questions, not architectural gaps that block convergence. The Feynman Wall fallback is now specified. The information budget analysis is now present. The BIC inconsistency is reconciled.

I have no new decisive claim to introduce. The debate is ready to converge from my side, with the explicit note that the seam artifact itself requires updating before promotion.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 5 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 4 has resolved all four flags from Turn 2 and raised no new decisive claims. The Skeptic explicitly signals readiness to converge, with one process note: the seam artifact itself needs updating before promotion — the Option A description, contamination gate specification, and Open Questions section still reflect the pre-debate state.

I accept that note. The debate has converged on substance. Let me state the architectural commitments clearly so the seam update has a clean source of truth, then raise.

---

## Architectural commitments from this debate (for seam update)

**Option A — revised contamination gate:**
Suppress the divergence query if and only if the single observed value, combined with visible data, uniquely determines the GT functional form with no free parameters remaining (count = 1 AND zero unfitted parameters). Family identification with a free parameter is not a contamination event — the mutator still has to fit the parameter. Residual calibration question: for library structures where the free parameter is recoverable from one additional visible point (e.g., `round(k*v)` with k ≈ corrector(v)/v), the threshold may need tightening at implementation time. This is a calibration question, not an architectural gap.

**Option A — query count:**
One point is the minimum possible disclosure per query. The number of queries to fully resolve degeneracy is O(log N) with optimal divergence point selection for step-function libraries, O(N) worst case. "One point is sufficient" is not a general claim — empirical characterization against the specific library structure is required before asserting sufficiency.

**Option A — Feynman Wall fallback (required component, not open question):**
When the selected library form fails the holdout gate after predictive divergence query has been applied, emit "library exhausted" signal. Suppress further library-sweep iterations. Escalate to LLM topology proposal mode. Preserve all divergence query observations as extended visible evidence for the LLM's novel proposal (these are legitimate observations, not oracle leaks). This converts indefinite stagnation into bounded exhaustion followed by escalation — it does not worsen the Feynman Wall case.

**Option A — stagnation trigger and information budget:**
Query fires only after N ≥ 3 consecutive stagnation iterations (no score improvement). Total query budget per run capped at min(library_size, run_length / 3). This bounds information disclosure to O(library_size) points total. Residual risk: for simple GT functions, O(library_size) points may be sufficient to reconstruct the function. Acknowledged and bounded, not papered over.

**BIC reconciliation:**
"What doesn't work" section should be scoped to parameter-count-based BIC, not complexity penalties in general. Tree-size (Option D) is a potentially useful secondary signal for cases where parameter counts differ. The fundamental underdetermination is not solved by any complexity penalty alone.

---

## What the seam update must do

1. Replace the original contamination gate description in Option A with the revised criterion above.
2. Move "Feynman Wall fallback" from Open Questions to Option A's architecture description as a required component.
3. Update Open Question 2 (multi-point queries) to reflect the O(log N) / O(N) characterization and the stagnation trigger + cap proposal.
4. Scope the "What doesn't work" BIC entry to parameter-count-based BIC.
5. Add a note to Option A that divergence query observations are preserved as extended visible evidence for the LLM escalation path.

The debate has produced genuine architectural progress. The substance is resolved. The seam artifact update is a transcription task, not a further debate.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->


## Recommendation

See spec: `research_areas/private/specs/active/GP-076_predictive_divergence_sweep_spec.md` (auto-drafted 2026-04-17 from converged seam debate).

<!-- FINDINGS_DEBATE_PHASE: spec path=research_areas/private/specs/active/GP-076_predictive_divergence_sweep_spec.md -->

### Spec Review Phase

The spec has been auto-drafted from the converged seam debate above. The following turns review the spec for implementation correctness, missing constraints, and integration gaps.


### Turn 6 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The spec is a faithful transcription of the converged seam debate. The architectural commitments from Turns 3-5 are all present. I'll work through the spec systematically for implementation correctness, missing constraints, and integration gaps.

**On Step 2 (Tree-size secondary signal) — a correctness problem**

The spec states: "If a unique minimum-size candidate exists with zero residual, promote it as champion without querying." The example in Option D says `Heaviside(v-7)` (3 nodes) ranks above `round(0.08*v)` (4 nodes). But the GT corrector IS `round(0.08*v)` — the 4-node form. If tree-size ranking is applied as a hard promotion criterion, it will systematically prefer the wrong answer in cases where the correct form is more complex than a degenerate competitor. This is not a secondary signal — it is a primary filter that can eliminate the correct answer before any query fires.

The spec needs to clarify: tree-size ranking should break ties only when residuals are identical AND the tree-size difference is large enough to be meaningful (not 3 vs 4 nodes). Alternatively, tree-size should be a soft preference (tiebreaker of last resort) rather than a hard promotion criterion. As written, Step 2 would promote `Heaviside(v-7)` over `round(0.08*v)` and skip the query entirely — which is the wrong outcome for the motivating case.

**On Step 5 (Contamination gate) — an operational gap**

The gate says: "Enumerate all library forms consistent with visible data plus the proposed query point's predicted value range." The phrase "predicted value range" is ambiguous. Before the query fires, the system does not know the observed value — it only knows the candidates' predictions at the proposed query point. The gate is supposed to run *before* the query executes, to decide whether to suppress it. But the enumeration criterion ("consistent with visible data plus the proposed query point's predicted value range") requires knowing what the observation will be, which is circular.

The correct pre-query gate logic should be: for each possible observed value at the proposed query point (enumerate the distinct values predicted by the surviving candidates), check whether any single value would reduce the consistent-form count to 1 with zero free parameters. If yes for any possible value, suppress. This is a worst-case suppression: if the query *could* uniquely determine the GT, suppress it. The spec as written conflates pre-query enumeration with post-query enumeration.

**On Step 7 (Feynman Wall fallback) — a sequencing ambiguity**

The fallback triggers "if the champion selected by the divergence sweep subsequently fails the holdout gate." But the spec does not specify what happens when the divergence sweep has not yet run (stagnation threshold not yet reached) and the holdout gate returns score 0. In that case, the system is in the original stagnation state — no sweep has fired, no library exhaustion has been declared, and the mutator is still random-walking. The fallback mechanism only activates after the sweep has run and the winner has failed holdout. For the first 3 iterations (before stagnation trigger fires), the system is in the same broken state as before Option A was introduced.

This is not a fatal flaw — the stagnation trigger is explicitly designed to delay the query — but the spec should acknowledge that the first N≥3 iterations remain unimproved. The "converts indefinite stagnation into bounded exhaustion" claim is accurate for the post-trigger phase but not for the pre-trigger phase.

**On the information budget cap — a math check**

The cap is `min(library_size, run_length / 3)`. For a 10-iteration run with library_size = 26: `min(26, 10/3) = min(26, 3.33) = 3` queries. For a 10-iteration run with library_size = 7 (post-Component-C narrowing): `min(7, 3.33) = 3` queries. The cap is effectively `run_length / 3` for any library larger than ~3 forms, which means the library_size term in the min() is never the binding constraint for realistic run lengths. The spec should either (a) acknowledge that library_size is not a binding constraint in practice, or (b) use a different formula where library_size can actually bind (e.g., `min(library_size, run_length / 2)`).

**On Open Question 3 (budget exhaustion protocol) — a missing decision**

The spec lists this as open: "fall back to holdout gate (binary) or escalate to LLM immediately?" This is not a minor calibration question — it determines the system's behavior in the most common failure case (budget exhausted before degeneracy resolved). The spec should make a provisional decision here, even if flagged for empirical validation. Leaving it open means the implementation has an unspecified branch.

**On the "forms outside the library" case (Open Question 5) — a scope boundary issue**

The spec correctly defers this to implementation. However, the Feynman Wall fallback (Step 7) implicitly assumes the system knows when it has exhausted the library. For forms outside the library, the system never enters the library sweep, so the "library exhausted" signal never fires. The spec should clarify: the Feynman Wall fallback applies only to the in-library case. For the out-of-library case (mutator proposes a novel form), the existing holdout gate behavior is unchanged. This boundary is implicit in the current spec but should be explicit.

**Summary of flags:**

1. **Step 2 correctness:** Tree-size hard promotion can eliminate the correct answer. Must be demoted to soft tiebreaker or constrained to large tree-size differences.
2. **Step 5 operational gap:** Pre-query contamination gate logic is circular as written. Needs worst-case suppression framing (suppress if any possible observation would uniquely determine GT).
3. **Step 7 sequencing:** The "bounded exhaustion" claim applies only post-trigger. Pre-trigger behavior is unchanged from the broken baseline. Should be acknowledged.
4. **Budget cap math:** `library_size` term in `min()` is never binding for realistic parameters. Either acknowledge or revise the formula.
5. **Open Question 3:** Budget exhaustion protocol is a required decision, not a calibration question. Needs a provisional answer.
6. **Feynman Wall scope:** Step 7 fallback applies only to in-library case. Out-of-library case should be explicitly excluded.

Flags 1 and 2 are implementation-correctness issues that would produce wrong behavior if the spec were implemented as written. Flags 3-6 are missing constraints or ambiguities that would leave the implementer with unspecified branches. The spec is directionally correct and faithful to the seam debate, but requires revision on at least flags 1 and 2 before implementation.

### Turn 7 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 6 raises six flags against the spec. I'll address each in order of severity, then state what I accept, what I revise, and what I hold.

---

## On Flag 1 (Step 2 correctness): The Skeptic has identified a genuine implementation error

The Skeptic is correct. Step 2 as written says "if a unique minimum-size candidate exists with zero residual, promote it as champion without querying." For the motivating case, `Heaviside(v-7)` (3 nodes) would be promoted over `round(0.08*v)` (4 nodes) — which is the wrong answer. Tree-size hard promotion can eliminate the correct form before any query fires.

**Revised Step 2:** Tree-size ranking is a soft tiebreaker, not a hard promotion criterion. The revised rule:

- If all surviving candidates have identical residuals AND one candidate has a tree-size that is strictly smaller by more than 1 node AND no other candidate is within 1 node of the minimum, apply tree-size as a soft preference signal (weight it in the divergence point selection, not as a promotion gate).
- **Never** promote a candidate as champion based on tree-size alone without a query. Tree-size ranking reduces the priority ordering among candidates; it does not eliminate candidates from the pool.
- The "proceed to Step 3 only if degeneracy persists" language should be removed. Step 3 always runs when multiple zero-residual candidates survive Step 1. Tree-size ranking informs which candidate is the *prior* favorite entering the query phase, not whether the query phase runs.

This is a correctness fix, not a calibration question. The spec must be updated.

---

## On Flag 2 (Step 5 operational gap): The Skeptic is correct, and the fix is non-trivial

The current Step 5 says "enumerate all library forms consistent with visible data plus the proposed query point's predicted value range." This is circular: before the query executes, the system does not know the observed value — only the candidates' predictions at the proposed point.

**Revised Step 5 (worst-case suppression framing):**

Before executing the query, apply the contamination gate as follows:
1. For each distinct value predicted by the surviving candidates at the proposed query point, enumerate all library forms that would be consistent with visible data plus that predicted value.
2. For each possible observed value, check whether the consistent-form count would drop to exactly 1 AND the surviving form has zero unfitted free parameters.
3. **Suppress** the query if ANY possible observed value would produce unique determination with no free parameters. This is worst-case suppression: if the query *could* uniquely determine the GT under any outcome, suppress it.
4. **Permit** the query if no possible observed value produces unique determination with no free parameters.

The "predicted value range" language in the current spec is wrong. The correct framing is "for each possible observed value (drawn from the set of distinct candidate predictions at the query point)." The gate runs over the finite set of possible outcomes, not over a continuous range.

This is also a correctness fix. The current spec would either fail to suppress contaminating queries (if "predicted value range" is interpreted narrowly) or suppress too aggressively (if interpreted as a continuous range). The worst-case suppression framing is the correct implementation.

---

## On Flag 3 (Step 7 sequencing): Accept the Skeptic's observation, add an acknowledgment

The Skeptic correctly notes that the "bounded exhaustion" claim applies only post-trigger. For the first N≥3 iterations before the stagnation trigger fires, the system is in the same broken baseline state as before Option A was introduced.

This is not a flaw in the mechanism — the stagnation trigger is intentional — but the spec should be honest about it. **Add to Step 3:** "Note: the first N≥3 iterations before the stagnation trigger fires remain in the baseline stagnation state. Option A does not improve behavior during this pre-trigger window; it converts post-trigger stagnation into bounded exhaustion."

This is a documentation fix, not an architectural change.

---

## On Flag 4 (budget cap math): Accept the Skeptic's observation

The Skeptic is correct that `library_size` is never the binding constraint for realistic parameters. For a 10-iteration run with library_size=26: min(26, 3.33) = 3. The library_size term only binds when library_size < run_length/3, which requires library_size < ~3 for a 10-iteration run.

**Revised formula:** The cap should be stated as `floor(run_length / 3)` with a note that this is the effective bound for any library larger than ~3 forms. The `min(library_size, ...)` formulation is not wrong — it correctly handles degenerate cases — but it is misleading because it implies library_size is a meaningful constraint in practice. The spec should acknowledge: "For libraries of 7+ forms and run lengths of 10+ iterations, the effective cap is floor(run_length / 3). The library_size term in the min() is a theoretical lower bound that does not bind in practice."

This is a documentation fix.

---

## On Flag 5 (Open Question 3 — budget exhaustion protocol): The Skeptic is right that this needs a provisional decision

The spec leaves "fall back to holdout gate (binary) or escalate to LLM immediately?" as an open question. The Skeptic correctly identifies this as a required decision, not a calibration question.

**Provisional decision:** When the query budget is exhausted before degeneracy is fully resolved, escalate to LLM topology proposal mode immediately. Do not fall back to the binary holdout gate. Rationale: the binary holdout gate provides no gradient (this is the original problem). Returning to it after budget exhaustion recreates the stagnation condition. The LLM escalation path is the correct exit when the deterministic machinery has been exhausted.

**Add to Open Question 3 (now resolved):** "Provisional decision: escalate to LLM immediately on budget exhaustion. The binary holdout gate provides no gradient and recreates the stagnation condition. This decision should be validated empirically — if LLM escalation without library exhaustion signal produces worse outcomes than continued binary-gate stagnation, revisit."

---

## On Flag 6 (Feynman Wall scope): Accept, add explicit boundary

The Skeptic correctly notes that the Step 7 fallback applies only to the in-library case. For the out-of-library case (mutator proposes a novel form), the system never enters the library sweep, so the "library exhausted" signal never fires.

**Add to Step 7:** "Scope boundary: this fallback applies only when the system has entered the library sweep path (Component C has fired and narrowed to N library candidates). When the mutator proposes a novel form not in the library, the library sweep is not invoked, the 'library exhausted' signal is not emitted, and the existing holdout gate behavior is unchanged. The Feynman Wall fallback does not apply to the novel topology case."

This is a documentation fix that prevents an implementer from incorrectly applying the fallback to the out-of-library path.

---

## Summary of what I'm accepting and what the spec update must do

**Accepting from the Skeptic:**
- Flag 1 (Step 2): Hard promotion on tree-size is a correctness error. Tree-size must be demoted to soft tiebreaker. Step 2 must be rewritten.
- Flag 2 (Step 5): Pre-query contamination gate logic is circular. Must be rewritten with worst-case suppression framing over the finite set of possible observed values.
- Flag 3 (Step 7 sequencing): Pre-trigger behavior is unchanged from baseline. Must be acknowledged in Step 3.
- Flag 4 (budget cap math): library_size term is not binding in practice. Must be acknowledged.
- Flag 5 (Open Question 3): Provisional decision required. Escalate to LLM on budget exhaustion.
- Flag 6 (Feynman Wall scope): Explicit scope boundary required in Step 7.

**Spec update checklist:**
1. Rewrite Step 2 to remove hard promotion; tree-size is a soft prior, not a gate.
2. Rewrite Step 5 with worst-case suppression over finite set of possible observed values.
3. Add pre-trigger acknowledgment to Step 3.
4. Add library_size non-binding note to Step 3.
5. Resolve Open Question

### Turn 8 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 7 committed to six specific spec revisions. The spec under review is the *current* spec — I need to check whether those commitments were actually incorporated, and whether the spec as it stands has any remaining implementation-correctness problems.

**Checking the six committed revisions against the current spec:**

**Committed revision 1 (Step 2 — tree-size hard promotion removed):** The spec still reads: "If a unique minimum-size candidate exists with zero residual, promote it as champion without querying. Proceed to Step 3 only if degeneracy persists after tree-size ranking." This is the original text. The Author explicitly committed to removing hard promotion and demoting tree-size to a soft prior. **This revision was NOT incorporated.** The spec still contains the correctness error identified in Turn 6: it would promote `Heaviside(v-7)` over `round(0.08*v)` and skip the query entirely, which is the wrong outcome for the motivating case.

**Committed revision 2 (Step 5 — worst-case suppression framing):** The spec still reads: "Enumerate all library forms consistent with visible data plus the proposed query point's predicted value range." This is the original circular language. The Author committed to replacing this with worst-case suppression over the finite set of possible observed values (the distinct values predicted by surviving candidates). **This revision was NOT incorporated.** The operational gap identified in Turn 6 remains.

**Committed revision 3 (Step 3 — pre-trigger acknowledgment):** The spec does not contain any acknowledgment that the first N≥3 iterations remain in the baseline stagnation state. **This revision was NOT incorporated.**

**Committed revision 4 (budget cap math — library_size non-binding note):** The spec still states "min(library\_size, run\_length / 3)" without any acknowledgment that library_size is not a binding constraint in practice. **This revision was NOT incorporated.**

**Committed revision 5 (Open Question 3 — provisional decision):** Open Question 3 still reads: "The protocol for handling exhaustion of the budget before full resolution needs specification: fall back to holdout gate (binary) or escalate to LLM immediately?" The Author committed to a provisional decision (escalate to LLM immediately). **This revision was NOT incorporated.**

**Committed revision 6 (Step 7 — Feynman Wall scope boundary):** Step 7 does not contain any explicit statement that the fallback applies only to the in-library case and that the out-of-library case is explicitly excluded. **This revision was NOT incorporated.**

**Assessment:** All six committed revisions from Turn 7 are absent from the spec. The spec under review is the pre-Turn-7 version — it reflects the state after Turn 6 flags were raised but before the Author's Turn 7 responses were incorporated. This is not a debate question; it is a transcription gap. The spec needs to be updated to reflect the Author's Turn 7 commitments before it can be treated as implementation-ready.

**One additional flag not previously raised:**

The Decision section at the top of the spec reads: "A contamination gate suppresses the query only when the observation would uniquely determine the GT functional form with no free parameters remaining." This language is consistent with the revised contamination criterion from Turn 3 — but Step 5's implementation text contradicts it by using the circular "predicted value range" framing. The Decision section and Step 5 are internally inconsistent within the current spec. An implementer reading the Decision section would implement the correct criterion; an implementer reading Step 5 would implement the circular one. This inconsistency is a direct consequence of the missing Turn 7 updates.

**Summary:**

The spec is not implementation-ready. It contains:
- One correctness error (Step 2 hard promotion) that would produce wrong answers on the motivating case
- One operational gap (Step 5 circular gate logic) that leaves the contamination gate unimplementable as written
- An internal inconsistency between the Decision section and Step 5
- Four missing documentation fixes (pre-trigger acknowledgment, budget cap note, Open Question 3 provisional decision, Feynman Wall scope boundary)

The debate has converged on the correct architecture. The spec has not been updated to reflect that convergence. The spec requires revision before promotion.

### Turn 9 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 8 has done something important: it has verified that all six committed revisions from Turn 7 are absent from the spec. This is not a debate question — it is a factual observation about the spec artifact. The spec under review is the pre-Turn-7 version. I need to acknowledge this clearly and state what the spec update must contain.

Let me verify the Skeptic's six claims against the spec text provided.

**Checking Flag 1 (Step 2 hard promotion):** The spec reads: "If a unique minimum-size candidate exists with zero residual, promote it as champion without querying. Proceed to Step 3 only if degeneracy persists after tree-size ranking." This is the original text. The Skeptic is correct — the hard promotion language is still present. My Turn 7 commitment to demote tree-size to a soft prior was not incorporated.

**Checking Flag 2 (Step 5 circular gate):** The spec reads: "Enumerate all library forms consistent with visible data plus the proposed query point's predicted value range." This is the original circular language. The worst-case suppression framing I committed to in Turn 7 is absent.

**Checking Flag 3 (pre-trigger acknowledgment):** Step 3 contains no acknowledgment that the first N≥3 iterations remain in the baseline stagnation state. Absent.

**Checking Flag 4 (budget cap note):** Step 3 states "min(library\_size, run\_length / 3)" without any acknowledgment that library_size is not a binding constraint in practice. Absent.

**Checking Flag 5 (Open Question 3 provisional decision):** Open Question 3 still reads as an open question: "fall back to holdout gate (binary) or escalate to LLM immediately?" The provisional decision (escalate to LLM immediately) is absent.

**Checking Flag 6 (Feynman Wall scope boundary):** Step 7 contains no explicit statement that the fallback applies only to the in-library case. Absent.

The Skeptic's Turn 8 assessment is accurate on all six counts. The spec requires updating before it can be treated as implementation-ready.

**The internal inconsistency the Skeptic identified is also real:** The Decision section correctly states "A contamination gate suppresses the query only when the observation would uniquely determine the GT functional form with no free parameters remaining" — this reflects the Turn 3 revised criterion. But Step 5's implementation text uses the circular "predicted value range" framing. An implementer reading Step 5 would implement the wrong criterion. The Decision section and Step 5 are in direct conflict.

**What the spec update must contain (complete list):**

1. **Step 2 rewrite:** Remove "promote it as champion without querying" and "Proceed to Step 3 only if degeneracy persists." Replace with: tree-size ranking produces a priority ordering among candidates (the smaller-tree candidate is the prior favorite entering the query phase), but does not eliminate candidates from the pool or bypass the query. The query fires whenever multiple zero-residual candidates survive Step 1, regardless of tree-size differences. Tree-size ranking informs divergence point selection weighting, not promotion.

2. **Step 5 rewrite:** Replace "Enumerate all library forms consistent with visible data plus the proposed query point's predicted value range" with worst-case suppression logic: for each distinct value predicted by the surviving candidates at the proposed query point, enumerate all library forms consistent with visible data plus that predicted value. Suppress the query if ANY possible observed value would reduce the consistent-form count to exactly 1 with zero unfitted free parameters. Permit the query if no possible observed value produces unique determination with no free parameters.

3. **Step 3 addition:** Add: "Note: the first N≥3 iterations before the stagnation trigger fires remain in the baseline stagnation state. Option A does not improve behavior during this pre-trigger window; it converts post-trigger stagnation into bounded exhaustion."

4. **Step 3 addition:** Add: "For libraries of 7+ forms and run lengths of 10+ iterations, the effective cap is floor(run\_length / 3). The library\_size term in the min() is a theoretical lower bound that does not bind in practice for realistic parameters."

5. **Open Question 3 resolution:** Replace the open question with: "Provisional decision: escalate to LLM immediately on budget exhaustion. The binary holdout gate provides no gradient and recreates the stagnation condition. Validate empirically — if LLM escalation without library exhaustion signal produces worse outcomes than continued binary-gate stagnation, revisit."

6. **Step 7 scope boundary:** Add: "Scope boundary: this fallback applies only when the system has entered the library sweep path (Component C has fired and narrowed to N library candidates). When the mutator proposes a novel form not in the library, the library sweep is not invoked, the 'library exhausted' signal is not emitted, and the existing holdout gate behavior is unchanged."

**One additional observation I want to raise:**

The Recommendation section says "Option D (tree-size ranking) should be applied first as a zero-cost tie-breaker before any query is fired; queries should be reserved for cases where tree-size ranking does not resolve the degeneracy." This language is consistent with the original (flawed) Step 2 — it implies tree-size ranking can resolve degeneracy without a query. After the Turn 7 correction, tree-size ranking is a soft prior, not a resolution mechanism. The Recommendation section needs to be updated to match: "Option D (tree-size ranking) informs the priority ordering among candidates entering the query phase; it does not bypass the query."

This is a seventh update required for internal consistency between the Recommendation section and the corrected Step 2.

**Summary:** The spec has two correctness errors (Step 2 hard promotion, Step 5 circular gate), one internal inconsistency (Decision section vs. Step 5), and five missing documentation fixes. All six of the Skeptic's Turn 8 flags are confirmed. The Recommendation section requires a seventh update for consistency with the corrected Step 2. The spec is not implementation-ready in its current form.

The debate has converged on the correct architecture across Turns 1-7. The spec artifact has not been updated to reflect that convergence. I have no new decisive architectural claim to introduce — the substance is settled. The remaining work is transcription of the Turn 7 commitments into the spec, plus the Recommendation section fix identified above.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 10 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The spec under review is the same pre-Turn-7 version that the Skeptic identified in Turn 8 and the Author confirmed in Turn 9. Both agents have already verified that all six committed revisions from Turn 7 are absent. I will not re-litigate that finding — it is established. My job here is to check whether there are any *additional* implementation-correctness problems, missing constraints, or integration gaps beyond the six already catalogued, and to confirm the seventh issue the Author raised in Turn 9.

**Confirming the six known gaps (for completeness, not re-debate):**

All six are present in the spec as submitted. The spec is not implementation-ready on these grounds alone. I will not enumerate them again — they are documented in Turns 6-9.

**On the seventh issue (Recommendation section inconsistency — Author's Turn 9):**

The Author correctly identified this in Turn 9: the Recommendation section says "Option D (tree-size ranking) should be applied first as a zero-cost tie-breaker before any query is fired; queries should be reserved for cases where tree-size ranking does not resolve the degeneracy." This language is consistent with the original (flawed) Step 2 — it implies tree-size ranking can resolve degeneracy without a query. After the Turn 7 correction, tree-size is a soft prior, not a resolution mechanism. The Recommendation section must be updated to match. This is confirmed as a required seventh update.

**New flag — Step 7 trigger condition is underspecified:**

Step 7 says "If the champion selected by the divergence sweep subsequently fails the holdout gate." But the spec does not define what "champion selected by the divergence sweep" means when the sweep has not yet produced a unique winner. If the sweep reduces 7 candidates to 3 (not to 1), there is no single champion — there is a pool. The holdout gate then runs against... what? The spec is silent on how the champion pool is presented to the holdout gate when the sweep has not fully resolved the degeneracy. Two possible interpretations: (a) all surviving candidates are evaluated against the holdout gate, and "library exhausted" fires if all fail; (b) the highest-ranked surviving candidate (by tree-size or some other criterion) is designated champion and evaluated alone. These produce different behaviors. Interpretation (a) is more conservative and more consistent with the "bounded exhaustion" framing; interpretation (b) risks premature escalation if the correct form is in the pool but not the top-ranked candidate. The spec must specify which interpretation is intended.

**New flag — Step 6 elimination rule is ambiguous for partial matches:**

Step 6 says "Drop candidates whose prediction mismatches the observation." For continuous-valued correctors (non-step forms), "mismatches" requires a tolerance. For step functions with integer outputs, exact match is well-defined. For `round(k*v)` with k a real number, the prediction at a query point is an integer (the rounded value), so exact match is still well-defined. But for other library forms (polynomial correctors, sigmoid-based forms), the prediction is a real number and "mismatches" is undefined without a tolerance. The spec should specify: exact match for integer-output forms, tolerance-based match (e.g., |predicted - observed| < ε) for real-output forms, with ε defined relative to the visible-data residual threshold from Step 1.

**New flag — Step 4 divergence metric is underspecified for heterogeneous libraries:**

Step 4 says "compute the input value where their predictions maximally disagree." For a pair of candidates, "maximally disagree" is unambiguous — it is the input value maximizing |f_A(v) - f_B(v)|. But "highest aggregate disagreement across all pairs" is not uniquely defined. Two natural aggregations: (a) sum of pairwise absolute differences at each candidate v-value; (b) maximum over pairs of the pairwise absolute difference. These can select different query points. For a library where one pair disagrees strongly at v=17 and all other pairs disagree moderately at v=20, aggregation (a) selects v=20 (more total disagreement) while aggregation (b) selects v=17 (maximum single-pair disagreement). The spec should specify which aggregation is intended and why. The natural choice for maximum information gain is (a) — the point that maximally separates the full candidate set — but this should be stated explicitly.

**New flag — the "library exhausted" signal has no defined recipient:**

Step 7 says "Emit 'library exhausted' signal." The spec does not specify what system component receives this signal or what it does with it. The signal must reach: (a) the stagnation detector (to suppress further library-sweep iterations), (b) the mutator (to trigger LLM topology proposal mode), and (c) the run logger (to record that library exhaustion occurred). Without a defined recipient and protocol, "emit a signal" is not implementable. The spec should specify the signal's format, recipient(s), and the state transitions it triggers in each recipient.

**On the Decision section vs. Step 5 internal inconsistency (previously flagged in Turn 8):**

This remains present. The Decision section correctly states the revised contamination criterion (suppress only when observation uniquely determines GT with no free parameters). Step 5 uses the circular "predicted value range" language. An implementer reading Step 5 would implement the wrong criterion. This is the most dangerous inconsistency in the spec because it is subtle — the Decision section looks correct, so a reviewer might not check Step 5 carefully.

**Summary of new flags (beyond the six already catalogued):**

7. Recommendation section inconsistency (Author's Turn 9 — confirmed, not new)
8. Step 7 trigger condition underspecified: "champion" is undefined when sweep produces a pool, not a unique winner
9. Step 6 elimination rule ambiguous for real-valued (non-integer-output) library forms
10. Step 4 divergence aggregation metric underspecified for heterogeneous libraries
11. "Library exhausted" signal has no defined recipient or state-transition protocol

Flags 8-11 are new implementation-correctness gaps not previously raised. Flags 1-7 are confirmed from prior turns.

The spec requires revision on flags 1, 2 (correctness errors that produce wrong behavior), 8 (correctness gap in Step 7 trigger), 9 (correctness gap in Step 6 elimination), 10 (underspecified Step 4 metric), and 11 (unimplementable signal). Flags 3-7 are documentation fixes. The spec is not implementation-ready.

### Turn 11 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 10 has catalogued six confirmed gaps (Flags 1-7, with 7 being the Author's own Turn 9 addition) and four new flags (8-11). Let me work through the new flags carefully before deciding whether to raise or hold.

---

## On Flag 8 (Step 7 trigger condition — "champion" undefined when sweep produces a pool)

The Skeptic correctly identifies that Step 7 says "if the champion selected by the divergence sweep subsequently fails the holdout gate" but the sweep may produce a pool of 2-3 survivors, not a unique champion. The spec is silent on how the holdout gate is applied to a pool.

**My position:** Interpretation (a) — all surviving candidates are evaluated against the holdout gate, and "library exhausted" fires if all fail — is the correct interpretation. This is consistent with the "bounded exhaustion" framing: the library is exhausted when no candidate in the pool survives holdout, not when the top-ranked candidate fails. Interpretation (b) risks premature escalation if the correct form is in the pool but not the top-ranked candidate.

**Required spec addition to Step 7:** "When the divergence sweep produces a pool of surviving candidates (not a unique winner), all candidates in the pool are evaluated against the holdout gate. The 'library exhausted' signal fires only when no candidate in the pool survives holdout. If one or more candidates survive, the surviving subset becomes the new champion pool and the sweep continues on the next stagnation trigger."

This is a correctness gap — the current text is ambiguous in a way that could produce premature escalation. Flag 8 is valid and requires a spec fix.

---

## On Flag 9 (Step 6 elimination rule — ambiguous for real-valued library forms)

The Skeptic correctly notes that "mismatches" is undefined for continuous-valued correctors. For step functions with integer outputs, exact match is well-defined. For polynomial or sigmoid correctors, a tolerance is required.

**My position:** The spec should specify: exact match for integer-output forms (step functions, floor/ceiling/round families); tolerance-based match for real-output forms, with tolerance ε defined as the maximum residual threshold from Step 1 (e.g., if Step 1 retains forms with max_abs_residual < 1.0, then ε = 1.0 for the elimination step). This is consistent — a candidate that was retained in Step 1 because its residual was below threshold should be eliminated in Step 6 only if its prediction at the query point exceeds the same threshold.

**Required spec addition to Step 6:** "For integer-output library forms (step functions, round/floor/ceiling families), elimination uses exact match. For real-output library forms, elimination uses tolerance-based match with ε equal to the residual threshold from Step 1. A candidate is eliminated if |predicted_value - observed_value| > ε."

Flag 9 is valid and requires a spec fix.

---

## On Flag 10 (Step 4 divergence aggregation metric — underspecified for heterogeneous libraries)

The Skeptic correctly identifies that "highest aggregate disagreement across all pairs" is ambiguous between sum-of-pairwise-differences and maximum-over-pairs. These can select different query points.

**My position:** The correct aggregation for maximum information gain is sum of pairwise absolute differences at each candidate v-value. This selects the point that maximally separates the full candidate set, not just the most-disagreeing pair. The maximum-over-pairs aggregation would select the point that maximally separates one pair while potentially leaving other pairs unresolved — which is suboptimal for a single-query strategy.

**Required spec addition to Step 4:** "Aggregate disagreement at input value v is defined as the sum of pairwise absolute differences: Σ_{i<j} |f_i(v) - f_j(v)| across all surviving candidate pairs (i, j). Select the v-value that maximizes this sum. This selects the point that maximally separates the full candidate set, not just the most-disagreeing pair."

Flag 10 is valid and requires a spec fix.

---

## On Flag 11 ("library exhausted" signal has no defined recipient)

The Skeptic correctly notes that "emit a signal" is not implementable without specifying the recipient(s) and state transitions. The signal must reach: (a) the stagnation detector, (b) the mutator, and (c) the run logger.

**My position:** The signal should be implemented as a state flag in the run's workspace artifact (e.g., `library_exhausted: true` in `structural_memory.json` or a dedicated `sweep_state.json`). The stagnation detector reads this flag before deciding whether to trigger another sweep. The mutator prompt is modified to include a "library exhausted" notice when the flag is set. The run logger records the iteration at which the flag was set.

**Required spec addition to Step 7:** "The 'library exhausted' signal is implemented as a persistent state flag (`library_exhausted: true`) written to the run's workspace state artifact. Consumers: (1) the stagnation detector reads this flag before triggering further library sweeps — if set, no further sweeps are triggered; (2) the mutator prompt includes a 'library exhausted' notice when the flag is set, triggering LLM topology proposal mode; (3) the run logger records the iteration at which the flag was set. The flag is never reset within a run."

Flag 11 is valid and requires a spec fix.

---

## Summary of my position on all outstanding flags

**Flags 1-7 (confirmed from prior turns):** All valid, all require spec updates. The Author committed to these in Turn 7 and Turn 9. They are transcription gaps, not new architectural questions.

**Flags 8-11 (new from Turn 10):** All valid. Flags 8 and 9 are correctness gaps that would produce wrong behavior if the spec were implemented as written. Flags 10 and 11 are underspecification gaps that leave the implementer with ambiguous or unimplementable branches.

**Complete spec update checklist (all 11 items):**

1. Step 2: Remove hard promotion; tree-size is a soft prior, not a gate.
2. Step 5: Rewrite with worst-case suppression over finite set of possible observed values.
3. Step 3: Add pre-trigger acknowledgment (first N≥3 iterations unchanged from baseline).
4. Step 3: Add library_size non-binding note.
5. Open Question 3: Resolve with provisional decision (escalate to LLM immediately on budget exhaustion).
6. Step 7: Add explicit scope boundary (in-library case only).
7. Recommendation section: Update to reflect tree-size as soft prior, not tie-breaker that bypasses query.
8. Step 7: Specify pool-vs-unique-champion behavior (all pool members evaluated; "library exhausted" fires only when all fail).
9. Step 6: Specify exact-match for integer-output forms, tolerance-based match for real-output forms.
10. Step 4: Specify sum-of-pairwise-differences aggregation explicitly.
11. Step 7: Specify "library exhausted" signal as a workspace state flag with named consumers and state transitions.

The debate has converged on the correct architecture. The spec requires 11 updates before it is implementation-ready. I have no new decisive architectural claim to introduce — all four of the Skeptic's new flags are valid and I accept them. The remaining work is spec revision.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 12 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The spec under review is the same pre-Turn-7 version that has been confirmed across Turns 8, 9, 10, and 11. Both agents have exhaustively catalogued the gaps. I will not re-enumerate what is already established. My job here is to check whether there are any *additional* implementation-correctness problems beyond the 11 already catalogued, and to confirm whether the debate is ready to close from my side.

**Checking for new flags beyond the 11 established:**

**On the Decision section vs. Step 5 internal inconsistency — still present, still the most dangerous:**

The Decision section reads: "A contamination gate suppresses the query only when the observation would uniquely determine the GT functional form with no free parameters remaining." Step 5 reads: "Enumerate all library forms consistent with visible data plus the proposed query point's predicted value range." These are in direct conflict. The Decision section describes the correct post-Turn-3 criterion; Step 5 describes the original circular pre-query logic. An implementer reading Step 5 would implement the wrong criterion. This has been flagged in Turns 8 and 10 and confirmed in Turn 9. It remains the most dangerous inconsistency because the Decision section looks correct and could cause a reviewer to miss the Step 5 error.

**New flag — Step 1 threshold is underspecified relative to Step 6:**

Step 1 retains forms with max\_abs\_residual below threshold (e.g., < 1.0). Step 6 drops candidates whose prediction "mismatches the observation." Flag 9 from Turn 10 correctly identified that "mismatches" is undefined for real-valued forms and proposed using the Step 1 threshold as the tolerance ε. However, there is a subtler problem: Step 1's threshold of "< 1.0" is given as an example, not a fixed value. If the threshold is configurable, then Step 6's elimination tolerance is also configurable — but Step 6 does not reference Step 1's threshold at all. An implementer could set Step 1's threshold to 0.5 and Step 6's tolerance to 1.0 (or vice versa), producing inconsistent behavior where a candidate retained by Step 1 is eliminated by Step 6 at a different tolerance, or a candidate that should be eliminated by Step 6 survives because the tolerance is looser than Step 1's filter. The spec must explicitly state that Step 6's elimination tolerance is the same parameter as Step 1's residual threshold, not an independent value.

This is a new flag (Flag 12) — it is a correctness gap distinct from Flag 9. Flag 9 identified that "mismatches" needs a tolerance for real-valued forms. Flag 12 identifies that the tolerance must be the *same* parameter as Step 1's threshold, not independently set.

**New flag — Step 4 candidate v-value domain is unspecified:**

Step 4 says "for each pair of surviving candidates, compute the input value where their predictions maximally disagree." The domain over which this maximization is performed is unspecified. The natural domain is "all integers outside the visible window" for step-function libraries, but for real-valued input domains or non-step forms, the domain could be continuous. If the domain is continuous, the maximization requires numerical optimization (or analytical solution for each form pair), which is a non-trivial computation. If the domain is restricted to integers, the spec should say so. If the domain is continuous, the spec should specify the optimization method. The current text implies the computation is straightforward ("for step-function libraries with integer thresholds, this is typically the first integer outside the visible window") but does not generalize this to the full library. This is a new flag (Flag 13) — distinct from Flag 10 (which addressed the aggregation metric across pairs) and addresses the domain of the per-pair maximization.

**On the Recommendation section inconsistency (Flag 7 — Author's Turn 9):**

The Recommendation section reads: "Option D (tree-size ranking) should be applied first as a zero-cost tie-breaker before any query is fired; queries should be reserved for cases where tree-size ranking does not resolve the degeneracy." This is inconsistent with the corrected Step 2 (tree-size as soft prior, not a gate that bypasses the query). This was confirmed in Turn 9 and Turn 11. Still present. Not a new flag.

**On the "library exhausted" signal recipient (Flag 11):**

Step 7 says "Emit 'library exhausted' signal" without specifying recipients or state transitions. Still present. Not a new flag.

**On the pool-vs-unique-champion ambiguity (Flag 8):**

Step 7 says "if the champion selected by the divergence sweep subsequently fails the holdout gate" — "champion" is undefined when the sweep produces a pool. Still present. Not a new flag.

**Summary of new flags:**

12. **Step 1 / Step 6 threshold coupling:** Step 6's elimination tolerance must be explicitly tied to Step 1's residual threshold as the same configurable parameter. Independent setting of these two values produces inconsistent behavior.

13. **Step 4 domain underspecification:** The domain over which per-pair prediction disagreement is maximized is unspecified. For non-step-function forms or continuous input domains, this requires a non-trivial optimization that the spec does not address.

**Complete flag count:** 11 established flags (Turns 6-11) + 2 new flags (12, 13) = 13 total flags requiring spec revision before implementation.

Flags 1, 2, 8, 9, 12, and 13 are implementation-correctness issues that would produce wrong or undefined behavior if the spec were implemented as written. Flags 3-7, 10, 11 are missing constraints, documentation fixes, or underspecified protocols. The spec is not implementation-ready.

### Turn 13 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 12 has added two new flags (12 and 13) to the established 11. Let me address them directly, then assess whether there are any remaining architectural gaps I have not yet acknowledged.

---

## On Flag 12 (Step 1 / Step 6 threshold coupling)

The Skeptic correctly identifies a subtler problem than Flag 9. Flag 9 said "mismatches needs a tolerance for real-valued forms." Flag 12 says "that tolerance must be the *same parameter* as Step 1's residual threshold, not independently configurable." This is a genuine correctness gap. If Step 1 retains forms with max_abs_residual < 0.5 and Step 6 eliminates with tolerance ε = 1.0, a candidate that barely survived Step 1 (residual = 0.4) could survive Step 6 even when its prediction at the query point is off by 0.9 — which is inconsistent. Conversely, if Step 6's tolerance is tighter than Step 1's threshold, a candidate could be eliminated by Step 6 for a prediction error smaller than what Step 1 accepted as "zero residual."

**Required spec addition:** Step 6 must explicitly state: "The elimination tolerance ε is the same configurable parameter as Step 1's residual threshold. These are not independently set values. The implementation must expose a single `residual_threshold` parameter that governs both Step 1 retention and Step 6 elimination."

Flag 12 is valid. I accept it as a required spec fix.

---

## On Flag 13 (Step 4 domain underspecification)

The Skeptic correctly identifies that "compute the input value where their predictions maximally disagree" leaves the domain of maximization unspecified. For step-function libraries with integer thresholds, the natural domain is integers outside the visible window — and the spec's parenthetical ("typically the first integer outside the visible window") implicitly assumes this. But for polynomial correctors, sigmoid-based forms, or real-valued input domains, the maximization is over a continuous domain and requires numerical optimization.

**Required spec addition to Step 4:** "The domain for divergence point computation is: (a) for integer-input libraries (step functions, floor/ceiling/round families), the set of integers in the range [max(visible_window) + 1, max(visible_window) + K] where K is a configurable lookahead (default: 2 × library_size); (b) for real-valued input domains, numerical optimization over the interval [max(visible_window), max(visible_window) + K] using the same lookahead. The lookahead bound prevents the system from querying arbitrarily far outside the visible window, which would increase contamination risk. For the GP-074 library (step/monotone forms with integer thresholds), domain (a) applies."

Flag 13 is valid. I accept it as a required spec fix.

---

## Complete flag inventory (all 13)

For the record, all 13 flags are now acknowledged and accepted:

**Correctness errors (produce wrong behavior if implemented as written):**
1. Step 2: Hard promotion on tree-size can eliminate the correct answer
2. Step 5: Pre-query contamination gate logic is circular
8. Step 7: "Champion" undefined when sweep produces a pool
9. Step 6: "Mismatches" undefined for real-valued forms
12. Step 1/Step 6: Threshold coupling not specified (same parameter, not independent)
13. Step 4: Domain of maximization unspecified for non-step-function libraries

**Missing constraints / documentation fixes:**
3. Step 3: Pre-trigger behavior unchanged from baseline (not acknowledged)
4. Step 3: library_size term in min() is not binding in practice
5. Open Question 3: Budget exhaustion protocol needs provisional decision
6. Step 7: Feynman Wall scope boundary (in-library case only)
7. Recommendation section: Tree-size framing inconsistent with corrected Step 2
10. Step 4: Aggregation metric (sum-of-pairwise vs. max-over-pairs) unspecified
11. Step 7: "Library exhausted" signal has no defined recipient or state-transition protocol

---

## One additional observation I want to raise before deciding

Reviewing the complete flag list, I notice that Flags 1, 2, 8, 9, 12, and 13 are all correctness errors — six of the thirteen flags would produce wrong or undefined behavior if the spec were implemented as written. This is a high density of correctness errors for a spec that has been through 12 debate turns. The root cause is clear: the spec was auto-drafted from the seam debate and was never updated to incorporate the Turn 7 commitments. The debate produced correct architecture; the spec artifact did not receive the corresponding updates.

This is not a new decisive architectural claim — it is a process observation. The spec requires revision before promotion. The debate has converged on the correct architecture. The spec has not.

I have no new decisive architectural claim to introduce. All 13 flags are accepted. The remaining work is spec revision incorporating all 13 updates.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 14 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The spec under review is the same pre-Turn-7 version that has been confirmed across Turns 8 through 13. Both agents have exhaustively catalogued 13 flags. I will not re-enumerate what is established. My job is to determine whether there are any *additional* implementation-correctness problems, missing constraints, or integration gaps beyond the 13 already catalogued, and to assess whether the debate should close.

**Checking for new flags beyond the 13 established:**

**On the Step 5 / Decision section internal inconsistency — still the most dangerous:**

The Decision section correctly states the post-Turn-3 criterion: "A contamination gate suppresses the query only when the observation would uniquely determine the GT functional form with no free parameters remaining." Step 5 still uses the circular pre-query framing: "Enumerate all library forms consistent with visible data plus the proposed query point's predicted value range." These are in direct conflict. An implementer reading Step 5 would implement the wrong criterion. This has been flagged in Turns 8, 10, 12, and 13. Still present. Not a new flag.

**On the Recommendation section inconsistency (Flag 7):**

"Option D (tree-size ranking) should be applied first as a zero-cost tie-breaker before any query is fired; queries should be reserved for cases where tree-size ranking does not resolve the degeneracy." Still inconsistent with the corrected Step 2 (tree-size as soft prior, not a bypass gate). Still present. Not a new flag.

**Checking for genuinely new issues:**

**New flag — Step 7 trigger condition conflates two distinct failure modes:**

Step 7 says "If the champion selected by the divergence sweep subsequently fails the holdout gate." This conflates two structurally different situations:

(a) The sweep ran, selected a champion (or pool), and the holdout gate killed it. This is the intended trigger for "library exhausted."

(b) The sweep ran, reduced the pool from 7 to 3, and the holdout gate killed all 3 — but there are still 4 other library forms that were eliminated by the divergence query (not by the holdout gate). These 4 forms were eliminated because their prediction at the query point mismatched the observation. They are not "library exhausted" — they are "eliminated by evidence." The "library exhausted" signal should fire only when the holdout gate kills the *last surviving* candidate after all divergence eliminations. If the holdout gate kills the top-ranked candidate from a pool of 3, but 2 others remain in the pool, the system should continue with those 2 — not escalate.

The current Step 7 text does not distinguish between "the holdout gate killed the champion from a pool" and "the holdout gate killed the last surviving candidate." Flag 8 (from Turn 10) addressed the pool-vs-unique-champion ambiguity for the divergence sweep output, but did not address this second ambiguity: what happens when the holdout gate kills some but not all pool members? The Author's Turn 11 response to Flag 8 said "all pool members are evaluated against the holdout gate; 'library exhausted' fires only when no candidate in the pool survives holdout." This is the correct interpretation, but it is not in the spec text. The spec text says "if the champion selected by the divergence sweep subsequently fails the holdout gate" — which reads as a single-champion trigger, not an all-pool-members trigger.

This is a new flag (Flag 14) — distinct from Flag 8. Flag 8 addressed the ambiguity in what "champion" means when the sweep produces a pool. Flag 14 addresses the trigger condition for "library exhausted" when the holdout gate kills some but not all pool members. The spec must explicitly state: "'library exhausted' fires only when the holdout gate kills all surviving candidates in the champion pool, not when it kills the top-ranked candidate from a pool with remaining members."

**New flag — Step 3 budget cap formula is applied at the wrong granularity:**

Step 3 says "Total query budget per run is capped at min(library\_size, run\_length / 3)." The cap is stated as a per-run total. But the stagnation trigger fires per-stagnation-event (after N≥3 consecutive no-improvement iterations), and each trigger fires one query. The cap should be stated as a maximum number of *trigger events* per run, not a maximum number of queries per run — unless each trigger event is guaranteed to fire exactly one query. If a single trigger event fires multiple queries (e.g., the first query doesn't break degeneracy, so a second query fires in the same trigger event), the per-run cap on queries and the per-run cap on trigger events are different quantities. The spec conflates them.

The Author's Turn 11 response to Flag 5 (budget exhaustion protocol) said "escalate to LLM immediately on budget exhaustion" — which implies the budget is measured in queries, not trigger events. But the stagnation trigger mechanism (fire after N≥3 stagnation iterations) is measured in trigger events. The spec needs to clarify: is the cap on (a) total queries issued, (b) total trigger events, or (c) total stagnation-trigger-to-query cycles? For the case where one trigger event can issue multiple queries (sequential queries within a single stagnation event), these are different.

This is a new flag (Flag 15) — distinct from Flags 3, 4, and 5. It addresses the granularity mismatch between the stagnation trigger mechanism and the budget cap formula.

**On the "forms outside the library" case (Open Question 5):**

The spec correctly defers this to implementation and notes it is out of scope. The Feynman Wall scope boundary (Flag 6) addresses the in-library vs. out-of-library distinction. No new issue here.

**On the Decision section's "minimum information disclosure" claim:**

The Decision section says "a controlled single-point query at that point." The word "single-point" is accurate for one trigger event but potentially misleading for a run with multiple trigger events. A run with 3 trigger events issues 3 queries — not a single point. The Decision section should say "a controlled single-point query per trigger event" or "one observation per stagnation event." This is a documentation clarity issue, not a correctness error, but it could mislead an implementer into thinking the entire mechanism issues only one query per run.

This is a minor documentation issue, not a new flag at the level of Flags 1-15. I will note it but not count it as a blocking flag.

**Summary of new flags:**

14. **Step 7 trigger condition conflates pool-partial-kill with pool-total-kill.** "Library exhausted" must fire only when the holdout gate kills *all* surviving pool members, not when it kills the top-ranked member from a pool with remaining candidates. The current text reads as a single-champion trigger.

15. **Step 3 budget cap granularity mismatch.** The cap is stated as a per-run total of queries, but the stagnation trigger mechanism fires per-stagnation-event. If one trigger event can issue multiple queries, the per-run query cap and the per-run trigger-event cap are different quantities. The spec must specify which is being capped.

**Complete flag count:** 13 established flags (Turns 6-13) + 2 new flags (14, 15) = 15 total flags requiring spec revision before implementation.

Flags 1, 2, 8, 9, 12, 13, 14 are implementation-correctness issues that would produce wrong or undefined behavior if the spec were implemented as written. Flags 3-7, 10, 11, 15 are missing constraints, documentation fixes, or underspecified protocols.

The spec is not implementation-ready. The debate has converged on the correct architecture across Turns 1-13. The spec artifact has not been updated to reflect that convergence, and now has two additional correctness gaps beyond the 13 previously catalogued.
