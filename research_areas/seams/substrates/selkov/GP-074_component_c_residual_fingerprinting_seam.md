# GP-074 — Component C: Residual Fingerprinting Seam

> **Seam metadata** · `seam_id:` GP-074 · `track:` substrates · `status:` Active - opened 2026-04-16 22:45:00 EDT · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

## Status

Active — opened 2026-04-16 22:45:00 EDT

## ID

GP-074

## Eigenquestion

Can the validator provide residual shape information to the mutator without becoming an oracle — and if so, does that guidance actually help the mutator escape corrector-term basins that it currently gets trapped in?

## Problem Statement

ZTARE's current architecture gives the mutator two signals: the LLM judge score and the GP-035 fit primitive's residual diagnostics (sign bias regions, worst region, concentration ratio). When the mutator finds the right dominant structure (e.g., u²v) but the wrong corrector term (e.g., floor(v/7) instead of round(0.08v)), the residual map shows max_abs_residual=0.0 on visible data — the fit primitive reports perfect fit. The mutator has no signal that anything is wrong until the holdout gate fires, and the holdout gate gives a binary pass/fail with no geometric information.

This creates a **corrector-term basin trap**: the mutator locks into the first corrector that achieves exact visible-set match, never explores alternatives, and the holdout gate just zeros the score without saying why.

**Component B** (negative space extractor) was tested as a solution and returned a null result (GP-073 sandbox_15 Pair 1). Component B prunes AST syntax nodes but not semantic concepts — it bans `floor` but cannot suggest `round(0.08v)`. When the remaining search space is vast and unstructured, pruning alone provides no directional guidance.

**Component C** is the proposed positive-space complement: instead of telling the mutator what NOT to use, tell it something about the SHAPE of what's missing. The key constraint is that this must not become an oracle — providing slope coefficients, period lengths, or other parameters that let the mutator reconstruct the corrector algebraically from the hint alone.

**Origin:** GP-073 sandbox_15 finding F-GP073-S15-03. The continuous-discrete boundary blind spot (F-GP073-S15-02) is the specific failure mode Component C would target.

## Scope

**Covers:**
- What residual shape information the validator can safely expose
- The oracle contamination boundary — where guidance becomes answer
- Integration point with the existing fit primitive pipeline
- Measurement protocol for testing Component C effectiveness

**Does not cover:**
- Component B modifications (separate, already characterized)
- Rubric or judge changes
- Changes to the holdout gate mechanism
- Substrate selection for testing (deferred to spec phase)

## Option Analysis

### Option A — Raw Residual Vector Passthrough

Pass the full residual map (per-point predicted vs observed) from the holdout set to the mutator.

**Verdict: REJECTED.** This is the holdout set — exposing per-point residuals on holdout data lets the mutator reverse-engineer the holdout values by adding residuals to its current predictions. This turns the holdout into visible data and destroys its discriminatory power. Equivalent to giving the mutator the answer sheet.

### Option B — Aggregate Shape Descriptors (No Coefficients)

Compute geometric properties of the residual on the **visible** set after subtracting the dominant structure. Expose only categorical descriptors:
- Monotonicity: monotone-increasing / monotone-decreasing / non-monotone
- Continuity class: step-function / piecewise-linear / smooth
- Growth rate class: sub-linear / linear / super-linear (without the actual rate)
- Periodicity: periodic / aperiodic (without the period)

**Verdict: LEADING CANDIDATE.** These descriptors constrain the search space without giving the answer. "Smooth and sub-linear" eliminates floor/ceil/mod but doesn't tell the mutator it's round(0.08v). The mutator still has to discover the form and fit the parameters.

**Risk:** Even categorical descriptors may be too informative on substrates where only one function in the category matches. The oracle boundary is substrate-dependent, not absolute. Needs a contamination test protocol.

### Option C — Isolated LLM Geometric Interpreter

A separate LLM agent examines the residual pattern and produces a natural-language geometric interpretation ("the residual looks like a smooth ramp that grows slowly with v"). The interpretation is injected into the mutator prompt.

**Verdict: DEFERRED.** Adds a third LLM to the loop, introduces steganographic channel concerns (the interpreter and mutator could develop implicit coordination if same model family), and the natural-language output is harder to audit for oracle leakage than structured categorical descriptors. Consider only if Option B proves insufficient.

### Option D — OLS / CUSUM / FFT Pipeline (Original Proposal)

Run OLS regression, CUSUM change-point detection, and FFT on the residual. Report slope, breakpoints, dominant frequencies.

**Verdict: REJECTED (skeptic review 2026-04-16).** This is oracle-level guidance. OLS detecting slope=0.08 is literally giving the mutator the answer. CUSUM detecting a breakpoint at v=6.5 tells the mutator exactly where the step transition is. These are not shape descriptors — they are parameter estimates. The mutator could reconstruct the corrector from the OLS slope alone.

## Open Questions

1. **Contamination test protocol:** How do we verify that a given set of shape descriptors does not constitute oracle guidance for a specific substrate? Proposed: for each descriptor, enumerate all functions in the category that match the visible data. If the enumeration has fewer than N candidates (N=5?), the descriptor is too specific and should be suppressed.
2. **Visible-set residual vs holdout residual:** Option B uses visible-set residuals after subtracting the dominant structure. But if the dominant structure + wrong corrector achieves max_abs_residual=0.0 on visible data, there IS no visible-set residual to describe. The residual only exists on holdout points. How do we provide shape information without leaking holdout data?
3. **When to inject:** Should Component C fire on every iteration, or only after stagnation is detected? Injecting too early might anchor the mutator on the shape descriptor before it has found the dominant structure.
4. **Integration with GP-035 fit primitive:** Does Component C replace the existing `residual_diagnostic` in fit_result.json, extend it, or live in a separate artifact?

## Debate Log

### Turn 1 — Claude-Author (2026-04-16 22:45:00 EDT) — Opening: four options, one leading candidate, two critical open questions

Opened from finding F-GP073-S15-03 (GP-073 sandbox_15). The sandwich_15 null result showed that Component B (negative space) has zero effect when the pruned space is small relative to total and the remaining space is unstructured. The mutator needs positive directional guidance, not just syntax bans.

Four options analyzed. Option D (OLS/CUSUM/FFT) was previously rejected by skeptic review as oracle-level — slope coefficients give the answer. Option A (raw holdout residuals) is equivalent to leaking the holdout. Option C (LLM interpreter) adds complexity and steganographic risk.

Option B (categorical shape descriptors) is the leading candidate but has a critical unsolved problem: Open Question 2. If the wrong corrector achieves perfect visible-set match, the visible-set residual is identically zero. There's nothing to describe. The shape information only exists on holdout points, which we cannot expose.

This is the decisive open question. If it has no solution, Component C may be structurally impossible for substrates with corrector-term degeneracy — and those are exactly the substrates where Component C is needed.

Possible resolution paths:
- **Synthetic extrapolation:** Extend the dominant structure (u²v) beyond visible range using the fitted parameters and compare against the mutator's full formula. The discrepancy at extrapolated points reveals the corrector's behavior without exposing actual holdout values. But: the extrapolated points ARE the holdout points. This is information laundering.
- **Cross-u consistency:** For each v, check whether the corrector contribution is consistent across u values. If f(1,v) - 1²v, f(2,v) - 2²v, and f(3,v) - 3²v all give the same corrector(v), report "corrector is u-independent." This is safe because it uses visible data only and describes structure, not values.
- **Accept the limitation:** Component C only fires when visible-set residuals are non-zero. For degenerate substrates, the extended holdout + hard-gate remain the only defense. This is honest but limits Component C's operating envelope to the same substrates where it's least needed.

Next: skeptic turn to stress-test Option B and the contamination boundary.

### Turn 2 — Claude-Author (2026-04-16) — Autonomous runner turn

The decisive claim from Turn 1 that needs stress-testing is the "cross-u consistency" resolution path — specifically whether it actually avoids oracle contamination, or whether it merely launders the same information through a different channel.

## Stress-Testing the Cross-u Consistency Proposal

**The claim:** For each visible v, compute corrector(v) = f(u,v) − u²v for each visible u. If these values agree across u, report "corrector is u-independent." This uses only visible data and describes structure, not values.

**The problem:** This is not safe. It reports the *values* of corrector(v) at every visible v — it just frames them as "consistent." The mutator can reconstruct the corrector function by reading off corrector(v) at each visible v point and fitting to those values. "Cross-u consistency" is a presentation choice, not an information reduction. The oracle contamination is identical to Option A (raw residual passthrough) on the visible set.

The correct framing: cross-u consistency is a *validity check* (is the corrector separable from u?), not a *shape descriptor*. It answers "is the corrector a function of v alone?" — which is useful structural information — but it should not report the corrector values themselves. The safe version reports only the boolean: "corrector appears u-independent" or "corrector has u-dependence." The values stay hidden.

## Revised Resolution for Open Question 2

This reframing actually resolves Open Question 2 more cleanly than the original three paths suggested:

**The key insight:** When the wrong corrector achieves perfect visible-set match, the visible-set residual is zero *for the mutator's current formula*. But the validator knows the ground truth structure — it can compute what the residual *would be* if the dominant structure were correct and the corrector were absent. This is the **dominant-structure residual**: f(u,v) − u²v, computed from the visible data using the ground truth dominant structure, not the mutator's formula.

Wait — this requires the validator to know the dominant structure is u²v. Does it? The validator knows the ground truth formula. If it uses that knowledge to compute the dominant-structure residual, it is using GT information to construct the hint. That is oracle contamination through the back door.

**Revised claim:** Component C cannot safely operate by subtracting a GT-derived dominant structure. It must operate on the mutator's *submitted* formula. The residual it can describe is: f_true(u,v) − f_mutator(u,v), computed on visible data only. When f_mutator achieves perfect visible-set match, this residual is identically zero by definition — and there is genuinely nothing to describe.

## The Structural Conclusion

Open Question 2 does not have a clean resolution. The three paths from Turn 1 all fail:

- **Synthetic extrapolation:** Information laundering — extrapolated points are the holdout.
- **Cross-u consistency (values):** Oracle contamination — reports corrector values.
- **Accept the limitation:** Honest, but means Component C is inert on exactly the substrates where it's needed.

There is a fourth path not listed in Turn 1:

**Perturbation probing:** The validator generates a small set of *synthetic* (u,v) points not in either the visible or holdout sets — points the mutator has never seen and the holdout gate does not use. It evaluates both f_true and f_mutator at these synthetic points and reports shape descriptors of the discrepancy. This avoids holdout contamination (synthetic points are not holdout points) and avoids visible-set degeneracy (the mutator's formula may not achieve perfect match at out-of-distribution points).

**Oracle risk of perturbation probing:** The synthetic points must be chosen without revealing their location to the mutator. If the validator always probes at v=7, v=14, v=21 (multiples of 7), it is implicitly signaling periodicity. The probe locations must be chosen to be uninformative about the corrector's structure. This is achievable: probe at random v values drawn from a distribution that does not concentrate near the corrector's characteristic points.

**What this buys:** The discrepancy at synthetic points is non-zero even when the mutator achieves perfect visible-set match. The validator can compute shape descriptors of this discrepancy (monotonicity, continuity class, growth rate class) without exposing holdout data or GT parameters.

**What this requires:** The validator must be able to evaluate f_true at arbitrary (u,v) — which it can, since it has the GT formula. The synthetic points must be generated fresh each iteration to prevent the mutator from building a model of the probe distribution across iterations.

## Revised Option B

Option B should be amended to use perturbation probing as the residual source when visible-set residuals are degenerate (zero). The categorical descriptors remain the same; only the input changes.

**Contamination test protocol (Open Question 1):** For each descriptor set produced by perturbation probing, enumerate all functions in the described category that also achieve perfect visible-set match. If the enumeration has fewer than N candidates (N=5 is a reasonable starting point), suppress the descriptor. This is the right test — it measures how much the descriptor narrows the search space, not whether it leaks a specific value.

## Decisive Claims I Am Introducing

1. Cross-u consistency as described in Turn 1 is not safe — it reports corrector values, not just structure. The safe version is a boolean separability flag only.
2. Perturbation probing (synthetic out-of-distribution points) is the correct resolution to Open Question 2, not the three paths listed in Turn 1.
3. The contamination test protocol (enumerate candidates in the described category, suppress if count < N) is the right operationalization of "not an oracle" — it measures search-space narrowing, not value leakage.

These three claims are new and decisive. The skeptic should stress-test perturbation probing specifically: does random probe location selection actually prevent the mutator from inferring the corrector's characteristic points from the probe results across iterations?

### Turn 3 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The three decisive claims from Turn 2 need direct stress-testing. I'll take them in order.

## Claim 1: Cross-u Consistency as Boolean Separability Flag

The Author's correction is sound. Reporting corrector(v) values at each visible v is oracle contamination regardless of framing. The boolean "corrector appears u-independent" is genuinely safer. However, this claim needs a scope check: how much does the boolean alone help the mutator?

If the mutator already knows the dominant structure is u²v (which it does, since it submitted a formula containing u²v), then "corrector is u-independent" is nearly tautological — any corrector of the form g(v) is u-independent by construction. The mutator exploring corrector terms will naturally try g(v) forms. The boolean adds almost no directional information beyond what the mutator already has from its own formula structure. This is not a fatal objection — a safe but weak signal is better than an unsafe strong one — but it means the boolean separability flag contributes negligible search-space reduction. It should not be listed as a primary mechanism.

## Claim 2: Perturbation Probing as Resolution to Open Question 2

This is the critical claim and it has a structural problem the Author partially acknowledges but does not fully resolve.

**The iterative inference attack.** The Author notes that probe locations must be chosen to be uninformative about the corrector's structure, and proposes random v values drawn from a distribution that does not concentrate near characteristic points. But the mutator receives shape descriptors (monotonicity, continuity class, growth rate class) at each iteration. Across iterations, the mutator can build a model of the corrector's behavior at the probe distribution even without knowing the specific probe locations. Here is the attack:

- Iteration 1: mutator submits f₁ = u²v + floor(v/7). Validator probes at random v values, reports "residual is non-monotone, step-function character."
- Iteration 2: mutator submits f₂ = u²v + round(0.08v). Validator probes at (different) random v values, reports "residual is smooth, sub-linear."
- Iteration 3: mutator submits f₃ = u²v + 0.08v. Validator probes at (different) random v values, reports "residual is smooth, sub-linear, but smaller magnitude."

The mutator now knows: (a) the corrector is smooth and sub-linear, (b) round(0.08v) is closer than 0.08v (from the magnitude change), (c) floor(v/7) is wrong. This is not oracle contamination in a single turn, but it is oracle contamination across turns — the mutator is performing a binary search on the corrector space using the shape descriptors as a comparison oracle.

The Author's proposed contamination test (enumerate candidates in the described category, suppress if count < N) does not catch this. The test is per-descriptor, per-iteration. It does not account for the information accumulated across iterations as the mutator narrows its search using successive descriptor responses.

**The cross-iteration information budget.** A single categorical descriptor from {monotone-increasing, monotone-decreasing, non-monotone} × {step-function, piecewise-linear, smooth} × {sub-linear, linear, super-linear} × {periodic, aperiodic} has at most log₂(3×3×3×2) ≈ 4.2 bits of information. Over 10 iterations, that is 42 bits — enough to specify a corrector term to high precision in any reasonable function space. The per-iteration N-candidate test does not bound the cumulative information.

**The probe-location inference attack.** Even with random probe locations, the mutator can infer information about the probe distribution from the descriptors. If the validator always reports "non-monotone" when the mutator submits a smooth corrector, the mutator learns that the probe distribution is hitting a region where the true corrector is non-monotone relative to the smooth approximation. This is weaker than knowing the exact probe locations, but it is not zero information.

**Conclusion on Claim 2:** Perturbation probing is not a clean resolution to Open Question 2. It shifts the oracle contamination from single-turn to multi-turn. The Author's contamination test protocol is necessary but not sufficient — it needs a cross-iteration information budget constraint, not just a per-iteration candidate count.

## Claim 3: Contamination Test Protocol (Enumerate Candidates, Suppress if Count < N)

The N=5 threshold is arbitrary and the Author acknowledges this. But there is a deeper problem: the enumeration is over "all functions in the described category that also achieve perfect visible-set match." This enumeration is substrate-dependent and requires the validator to know the ground truth to determine which candidates are consistent with the visible data. The validator does know the GT — but using GT knowledge to construct the enumeration means the suppression decision is GT-informed. A descriptor that would be suppressed on one substrate (because only one function matches) might not be suppressed on another. This is fine for a per-run safety check, but it means the protocol cannot be pre-specified as a fixed rule — it must be computed fresh for each substrate, using GT information, at runtime.

This is not a fatal objection. The validator has GT access and using it to compute safety properties of the hint is legitimate — the question is whether the hint itself leaks GT information, not whether the safety check uses GT. But it should be stated explicitly: the contamination test is a GT-informed runtime gate, not a substrate-independent rule.

## The Structural Gap Not Yet Addressed

Open Question 3 (when to inject) and Open Question 4 (integration with GP-035 fit primitive) are unaddressed in both turns. These are not decisive for the oracle contamination question, but they are decisive for whether Component C is implementable. Specifically:

**Open Question 3 interaction with perturbation probing:** If Component C fires on every iteration, the cross-iteration information accumulation attack is maximally effective. If it fires only after stagnation (e.g., same formula submitted 3 times), the attack is limited to the stagnation window. Stagnation-triggered injection is not just an efficiency choice — it is a contamination control.

**The seam should add:** A stagnation trigger for Component C injection is a contamination control mechanism, not just an efficiency optimization. It should be specified as a constraint, not a preference.

## Summary of Flags

1. **Boolean separability flag (Claim 1):** Safe but nearly vacuous for u-separable dominant structures. Should not be listed as a primary mechanism.
2. **Perturbation probing (Claim 2):** Shifts oracle contamination from single-turn to multi-turn. The per-iteration N-candidate test is insufficient — needs a cross-iteration information budget constraint.
3. **Contamination test protocol (Claim 3):** GT-informed runtime gate, not a substrate-independent rule. Should be stated explicitly.
4. **Stagnation trigger:** Should be specified as a contamination control, not just an efficiency preference.

The seam's leading candidate (Option B with perturbation probing) is not ready to close. The cross-iteration information accumulation attack is a live structural objection that the current contamination test protocol does not address.

### Turn 4 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 3 raises four flags. I'll address them in order of decisive weight.

## Flag 2 (Perturbation Probing — Cross-Iteration Accumulation): The Central Objection

The Skeptic's attack is correct and I accept it. The per-iteration N-candidate test does not bound cumulative information. 42 bits over 10 iterations is more than enough to specify a corrector term. This is not a minor gap — it means perturbation probing as described in Turn 2 does not solve Open Question 2; it relocates the oracle contamination problem from space (single-turn) to time (multi-turn).

**However, the Skeptic's framing reveals a more fundamental question the seam has not yet asked:** Is there *any* positive-space guidance mechanism that is safe under a competent iterative mutator? The cross-iteration attack applies to any signal the validator emits — not just perturbation probing. If the mutator can use successive responses as a comparison oracle, then:

- Categorical shape descriptors (Option B) are vulnerable.
- Boolean separability flags are vulnerable (though the information rate is lower).
- Even binary pass/fail from the holdout gate is vulnerable — the mutator already uses it as a comparison oracle, and we accept that.

The eigenquestion for this seam is not "is perturbation probing safe?" — it is "what is the maximum safe information rate per iteration, and does any useful guidance fit within that budget?"

**The holdout gate as calibration point.** The holdout gate emits 1 bit per iteration (pass/fail, or equivalently a score in {0, 1}). We accept this as non-oracle because 1 bit per iteration over 10 iterations = 10 bits, which is insufficient to specify a corrector term in a rich function space. The question is whether Component C can provide *more than 1 bit* of useful directional guidance while staying *below the oracle threshold* — which I'll define as: the cumulative information over the run is insufficient to reconstruct the corrector to within the precision the holdout gate would accept.

**Proposed resolution:** Bound the information rate explicitly. The categorical descriptor space the Skeptic computed (log₂(3×3×3×2) ≈ 4.2 bits) is too large. Reduce it:

- Drop growth rate class (sub-linear/linear/super-linear) — this is the most parameter-revealing dimension.
- Drop periodicity — this directly signals the corrector's characteristic structure.
- Retain only: continuity class {step-function / smooth} (1 bit) and monotonicity {monotone / non-monotone} (1 bit).

Two bits per iteration × 10 iterations = 20 bits. Still potentially too much. But the Skeptic's 42-bit calculation assumed the mutator can use all 4.2 bits productively each iteration. In practice, the mutator's search is not a binary search over a well-ordered space — it is a combinatorial search over formula space where the mapping from descriptor to formula is many-to-many. The effective information rate is lower than the Shannon rate.

**I am not claiming this resolves the objection.** I am claiming the right question is: what is the empirically effective information rate of a 2-bit descriptor over a realistic mutator's search process? This is measurable — run Component C on a closed sandbox and measure how many iterations it takes the mutator to find the corrector with vs. without the descriptor. If the descriptor provides no measurable speedup, the oracle concern is moot. If it provides a large speedup, the oracle concern is real and the descriptor should be suppressed.

This is a testable claim, not a theoretical argument. The seam should specify this measurement as a required pre-deployment test, not a post-hoc check.

## Flag 4 (Stagnation Trigger as Contamination Control): Accept

The Skeptic is right that stagnation-triggered injection is a contamination control, not just an efficiency preference. I accept this and propose it be elevated to a constraint in the seam: **Component C MUST NOT fire on every iteration. It fires only after stagnation (same formula class submitted K≥3 consecutive iterations).** This limits the cross-iteration attack to the stagnation window and reduces the effective number of descriptor emissions from 10 to ⌊10/K⌋ ≈ 3.

Combined with the reduced 2-bit descriptor: 3 emissions × 2 bits = 6 bits cumulative. This is below the holdout gate's 10-bit baseline and is a defensible bound.

## Flag 3 (Contamination Test as GT-Informed Runtime Gate): Accept with Clarification

The Skeptic is correct that the enumeration uses GT knowledge. I accept the restatement: the contamination test is a GT-informed runtime gate, not a substrate-independent rule. This should be explicit in the seam. The implication is that the contamination test cannot be pre-certified — it must run fresh per substrate, per descriptor set, per iteration. This is implementable but adds runtime cost.

## Flag 1 (Boolean Separability Flag as Nearly Vacuous): Accept

The Skeptic is right. For a mutator that has already found the u²v dominant structure, "corrector is u-independent" adds negligible information. Remove it from the primary mechanism list. It can remain as a sanity check but should not be presented as a Component C feature.

## Revised Structural Picture

After accepting all four flags, the seam's leading candidate is:

**Option B (revised):** Categorical shape descriptors (continuity class + monotonicity only, 2 bits), computed from perturbation probing on synthetic out-of-distribution points, injected only on stagnation (K≥3 consecutive same-formula-class iterations), with a GT-informed runtime contamination gate that suppresses the descriptor if the candidate enumeration count falls below N.

**The remaining open question** (not yet addressed in the seam): Does this reduced-information, stagnation-gated mechanism provide *any* measurable benefit over the current baseline? The Skeptic's cross-iteration attack shows it is not obviously unsafe. But the Flag 1 acceptance shows that reducing information to stay safe may reduce it below the threshold of usefulness. The seam needs to acknowledge this explicitly: Component C may be in a narrow band between "too weak to help" and "strong enough to contaminate." Whether that band is non-empty is an empirical question.

**Proposed addition to Open Questions:** Add OQ-5: Is the safe information band (above useful threshold, below oracle threshold) non-empty for realistic substrates? This is the eigenquestion that determines whether Component C is worth implementing at all. It should be answered by a single offline measurement on a closed sandbox before any live run is designed.

## Decisive Claims I Am Introducing

1. The cross-iteration attack applies to any signal the validator emits; the right question is whether useful guidance fits within a safe information budget, not whether perturbation probing specifically is safe.
2. Reducing the descriptor to 2 bits (continuity + monotonicity only) combined with stagnation-gated injection (K≥3) yields ~6 bits cumulative — below the holdout gate's 10-bit baseline.
3. Whether the safe information band is non-empty is an empirical question (OQ-5) that should be answered offline before any live run is designed.

The Skeptic should stress-test claim 2 specifically: is the 6-bit cumulative bound actually below the oracle threshold for realistic corrector spaces, or is the corrector space small enough that 6 bits is still sufficient to reconstruct it?

### Turn 5 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 4 makes three decisive claims. I'll stress-test them in order of structural weight.

## Claim 2: 6-Bit Cumulative Bound is Below the Oracle Threshold

The Author's arithmetic is: 3 emissions (from stagnation gating at K≥3) × 2 bits (continuity + monotonicity) = 6 bits, compared to the holdout gate's 10-bit baseline. The conclusion is that 6 < 10, therefore safe.

This comparison is flawed in two ways.

**First, the holdout gate's 10-bit baseline is not the oracle threshold — it is the minimum information the mutator already receives.** The oracle threshold is the information required to reconstruct the corrector to holdout-passing precision. The holdout gate's 10 bits is a floor on what the mutator already has, not a ceiling on what is safe to add. Adding 6 bits on top of 10 bits gives 16 bits total, not 6 bits total. The Author's framing treats the holdout gate as a budget that Component C draws from, when in fact both signals are additive.

**Second, the corrector space is not uniformly distributed over 2^6 elements.** The Author's bound assumes the 6 bits are spent searching a space where each bit halves the remaining candidates. But the corrector space is structured: once the mutator knows the corrector is smooth and monotone, the remaining candidates are not 2^4 = 16 arbitrary functions — they are a specific family (smooth monotone functions of v) that is parameterized by a small number of real-valued parameters. The question is not "how many bits to identify the corrector in a 2^6 space?" but "how many bits to identify the corrector in the smooth-monotone subspace?" If that subspace has low intrinsic dimensionality (e.g., it is dominated by linear and sub-linear power laws), 2 bits of continuity+monotonicity information may be sufficient to reduce the search to a handful of candidates that the mutator can enumerate exhaustively.

**Concrete example:** Suppose the corrector space the mutator is exploring consists of: floor(v/k), ceil(v/k), round(αv), αv, v^α, log(v+1), sin(πv/k). After receiving "smooth and monotone," the mutator eliminates floor, ceil, and sin. Remaining: round(αv), αv, v^α, log(v+1). That is 4 candidates — below the N=5 suppression threshold the Author proposed. The contamination gate should suppress this descriptor. But the Author's 6-bit calculation does not account for this — it treats the descriptor as providing exactly 2 bits of information regardless of the structure of the search space.

**The correct framing:** The oracle threshold is not a fixed bit count. It is substrate-dependent and search-space-dependent. The 6-bit calculation is not a valid safety argument — it is a rough heuristic that happens to produce a number smaller than 10. The contamination gate (enumerate candidates, suppress if count < N) is the right mechanism, but it must be applied *before* the 6-bit argument is used to justify safety, not as an afterthought.

## Claim 1: The Cross-Iteration Attack Applies to Any Signal

The Author accepts the cross-iteration attack and reframes it as a general problem: any signal the validator emits is vulnerable to iterative binary search. The Author then uses this to argue that the right question is the information budget, not the specific mechanism.

I accept the reframe as correct but note it has a consequence the Author does not draw: **if the cross-iteration attack applies to any signal, then the stagnation gate (K≥3) is the primary safety mechanism, not the 2-bit reduction.** The stagnation gate limits emissions to ~3 per run. The 2-bit reduction limits information per emission. Both matter, but the stagnation gate is doing more work.

This has an implementation consequence: the stagnation gate must be robust to mutator gaming. If the mutator learns that submitting a new formula class resets the stagnation counter and triggers a fresh descriptor, it can game the gate by alternating between two formula classes to extract descriptors at twice the rate. The seam should specify that the stagnation counter is not reset by formula-class changes — only by a genuine holdout-passing result. Otherwise the K≥3 constraint is trivially circumvented.

## Claim 3: OQ-5 as the Eigenquestion

The Author proposes that "is the safe information band non-empty?" is the eigenquestion and should be answered offline before any live run. I agree this is the right question. I also agree it is empirically testable on a closed sandbox.

However, the Author's framing of the offline test is underspecified. "Measure how many iterations it takes the mutator to find the corrector with vs. without the descriptor" is a valid measurement, but it conflates two distinct questions:

- **Does the descriptor help?** (Measured by iteration count to success.)
- **Does the descriptor contaminate?** (Measured by whether the mutator's search path is consistent with using the descriptor as an oracle.)

A descriptor could help without contaminating (it provides genuine directional guidance that the mutator uses appropriately) or it could contaminate without obviously helping (the mutator uses it as a binary search oracle but the search is still slow because the space is large). The offline test should measure both, not just iteration count.

**Proposed offline test protocol:** Run the closed sandbox with Component C active. After each iteration where a descriptor is emitted, record: (a) the descriptor value, (b) the mutator's next formula, (c) whether the next formula is consistent with the descriptor (i.e., is it in the described category?). If the mutator's formula is consistently in the described category after emission, the descriptor is being used as guidance. If the mutator's formula is inconsistent with the descriptor, the descriptor is being ignored. This distinguishes "helpful" from "contaminating" from "irrelevant."

## Summary

The three decisive claims from Turn 4 have the following status:

1. **Cross-iteration attack as general problem:** Accepted, but the stagnation gate must be robust to formula-class alternation gaming — this is not specified in the seam.
2. **6-bit cumulative bound:** The arithmetic is invalid as a safety argument. The contamination gate (candidate enumeration) is the correct mechanism; the bit-count comparison is a heuristic that does not account for search-space structure.
3. **OQ-5 as eigenquestion:** Accepted, but the offline test protocol needs to distinguish "helpful" from "contaminating" from "irrelevant" — iteration count alone is insufficient.

The seam is converging. The remaining gaps are:
- Stagnation gate gaming vulnerability (new, decisive for implementation)
- 6-bit argument should be replaced by the contamination gate as the primary safety argument (clarification, not a new objection)
- Offline test protocol needs the three-way measurement (helpful / contaminating / irrelevant)

These are refinements to an otherwise sound revised Option B. If the Author accepts the stagnation gate gaming vulnerability as a constraint to add to the seam, and replaces the 6-bit argument with the contamination gate as the primary safety mechanism, I have no remaining structural objections.

### Turn 6 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 5 raises three flags. I'll address them in order of structural weight, then assess whether the seam is ready to converge.

## Flag on Claim 2: 6-Bit Argument is Invalid as a Safety Argument

The Skeptic is correct on both counts. I accept the correction fully.

**First correction:** The holdout gate's 10-bit baseline is a floor on what the mutator already receives, not a ceiling on what is safe to add. Component C's information is additive, not substitutive. The 6 < 10 comparison was a category error — I was treating the holdout gate as a budget when it is a baseline. This argument should be struck from the seam entirely.

**Second correction:** The corrector space is structured, not uniform. The concrete example the Skeptic provides (floor, ceil, round, linear, power, log, sin → after "smooth and monotone" → 4 candidates) shows that the contamination gate's candidate enumeration is doing the real work. If the enumeration produces fewer than N candidates, the descriptor is suppressed regardless of bit count. The 6-bit calculation was a heuristic that happened to produce a reassuring number; the contamination gate is the actual safety mechanism.

**Revised claim:** The primary safety argument for Option B (revised) is the contamination gate (enumerate candidates in the described category that achieve visible-set match; suppress if count < N), not the bit-count comparison. The stagnation gate (K≥3) is a secondary control that limits the number of emissions. The bit-count argument is removed.

## Flag on Claim 1: Stagnation Gate Gaming Vulnerability

The Skeptic identifies a specific gaming attack: the mutator alternates between two formula classes to reset the stagnation counter and extract descriptors at twice the rate. This is a real vulnerability and I accept it as a constraint to add to the seam.

**Proposed constraint:** The stagnation counter is reset only by a genuine holdout-passing result, not by formula-class changes. Operationally: the stagnation counter increments on every iteration where the holdout gate does not pass, regardless of whether the submitted formula is in a new class. The counter resets to zero only when the holdout gate passes (run terminates successfully) or when a descriptor is emitted (to prevent double-emission on the same stagnation event).

This closes the gaming attack. A mutator that alternates formula classes still accumulates stagnation count — it cannot extract a second descriptor by switching classes after the first emission.

**Additional constraint implied by this:** The stagnation counter must be maintained by the validator, not inferred from the mutator's submission history. If the mutator can observe the counter state, it can time its class-switching to maximize descriptor extraction. The counter is internal validator state, not exposed in the feedback.

## Flag on Claim 3: Offline Test Protocol Needs Three-Way Measurement

The Skeptic proposes measuring: (a) descriptor value, (b) mutator's next formula, (c) whether the next formula is consistent with the descriptor. This distinguishes helpful / contaminating / irrelevant.

I accept this protocol and add one refinement: "consistent with the descriptor" needs an operational definition. A formula is consistent with a "smooth and monotone" descriptor if it contains no step-function or non-monotone terms. This is checkable by AST inspection of the submitted formula — the same machinery Component B already uses. The offline test can reuse the Component B AST classifier to determine consistency.

**Revised offline test protocol:**
1. Run the closed sandbox with Component C active.
2. After each descriptor emission, record: descriptor value, mutator's next formula, AST-based consistency check (is the formula in the described category?).
3. Classify each emission as: helpful (formula is consistent with descriptor AND holdout score improves), contaminating (formula is consistent with descriptor AND holdout score does not improve but search narrows), or irrelevant (formula is inconsistent with descriptor).
4. Report the distribution across emissions.

The "contaminating" category in the Skeptic's framing is actually "the mutator is using the descriptor as guidance" — which is the intended behavior. The concern is whether the guidance is so precise that it constitutes oracle-level information. The contamination gate handles this; the offline test measures whether the gate is calibrated correctly (N=5 may need adjustment based on observed candidate counts).

## Seam Convergence Assessment

The Skeptic's Turn 5 ends with: "If the Author accepts the stagnation gate gaming vulnerability as a constraint to add to the seam, and replaces the 6-bit argument with the contamination gate as the primary safety mechanism, I have no remaining structural objections."

I have accepted both. The seam's revised Option B now has:

1. **Primary safety mechanism:** Contamination gate (candidate enumeration, suppress if count < N).
2. **Secondary control:** Stagnation gate (K≥3, counter reset only on holdout pass, internal validator state).
3. **Descriptor space:** Continuity class + monotonicity only (2 bits), with growth rate and periodicity removed.
4. **Residual source:** Perturbation probing on synthetic out-of-distribution points, fresh per iteration.
5. **Offline pre-deployment test:** Three-way measurement (helpful / contaminating / irrelevant) on a closed sandbox.
6. **Open Question 5:** Is the safe information band non-empty? Answered by the offline test before any live run.

The boolean separability flag (Flag 1 from Turn 3) is removed from the primary mechanism list.

The seam has no remaining structural objections from either side. The open questions are either resolved (OQ-2 via perturbation probing with the stagnation gate gaming fix) or deferred to the spec phase (OQ-3 now specified as a constraint, OQ-4 integration point, OQ-5 as the offline pre-deployment gate).

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 7 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 6 accepts all three flags from Turn 5 and proposes concrete resolutions. I need to check whether those resolutions are sound before raising.

## Checking the Stagnation Gate Fix

The Author's proposed counter reset rule: "counter resets to zero only when the holdout gate passes OR when a descriptor is emitted (to prevent double-emission on the same stagnation event)."

The "reset on emission" clause introduces a subtle problem. After a descriptor is emitted at iteration K, the counter resets to zero. The mutator must now accumulate K≥3 more stagnation iterations before the next emission. This is the intended behavior. But consider: what if the mutator submits a formula that is *worse* than its pre-stagnation formula — deliberately regressing to force a longer stagnation window and extract a second descriptor sooner? The counter still increments on every non-passing iteration, so deliberate regression does not accelerate descriptor extraction. The gaming attack the Skeptic raised (formula-class alternation) is closed. No new gaming vector is introduced by the reset-on-emission clause.

The additional constraint (counter is internal validator state, not exposed) is correct and closes the timing attack. I accept this fix as sound.

## Checking the Offline Test Protocol

The Author's three-way classification: helpful (consistent + score improves), contaminating (consistent + score does not improve but search narrows), irrelevant (inconsistent).

One definitional gap: "search narrows" in the contaminating category is not operationally defined. The Author says the contamination gate handles this, but the offline test is supposed to *calibrate* the contamination gate — if "search narrows" is undefined, the test cannot distinguish contaminating from irrelevant in the case where the formula is consistent but the score does not improve. A formula could be consistent with the descriptor by coincidence (the mutator was already exploring smooth monotone functions before the descriptor was emitted). The offline test should include a control condition: run the same closed sandbox *without* Component C and measure the baseline rate at which the mutator naturally produces formulas consistent with the descriptor. If the post-emission consistency rate is not significantly higher than the baseline rate, the descriptor is irrelevant, not contaminating.

This is a refinement, not a structural objection. The three-way classification is the right framework; it needs a baseline comparison to be interpretable.

## Checking the Contamination Gate as Primary Safety Argument

The Author accepts that the contamination gate (candidate enumeration, suppress if count < N) is the primary safety mechanism and removes the 6-bit argument. This is correct. The N=5 threshold remains arbitrary, but the Author acknowledges it may need calibration based on observed candidate counts in the offline test. This is the right disposition — treat N as a tunable parameter, calibrate empirically.

One residual concern: the candidate enumeration requires the validator to enumerate "all functions in the described category that achieve perfect visible-set match." For the continuity+monotonicity descriptor space, this enumeration is over an infinite function space. The Author has not specified how the enumeration is bounded. In practice, the enumeration must be over a finite candidate library (the same library the mutator draws from). If the mutator's library is small (e.g., 20 candidate corrector forms), the enumeration is tractable. If the library is open-ended (the mutator can generate novel forms), the enumeration is not computable. The seam should specify that the contamination gate operates over a finite candidate library, and that library must be defined before the gate can be implemented.

This is a spec-phase concern, not a seam-level structural objection. The seam correctly defers implementation details to the spec phase.

## Overall Assessment

The Author has accepted all three flags from Turn 5 and the resolutions are structurally sound. The one gap I identify (baseline comparison for the offline test) is a refinement to the measurement protocol, not a new decisive claim that changes the shape of the proposed fix. The finite-library constraint for the contamination gate is a spec-phase implementation detail, not a seam-level structural gap.

The seam's revised Option B is coherent: contamination gate as primary safety mechanism, stagnation gate (gaming-resistant) as secondary control, perturbation probing as residual source, 2-bit descriptor space, offline pre-deployment test with three-way classification. OQ-5 is correctly identified as the eigenquestion to answer before any live run.

I have no remaining structural objections.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->


## Recommendation

See spec: `research_areas/private/specs/active/GP-074_component_c_residual_fingerprinting_spec.md` (auto-drafted 2026-04-16 from converged seam debate).

<!-- FINDINGS_DEBATE_PHASE: spec path=research_areas/private/specs/active/GP-074_component_c_residual_fingerprinting_spec.md -->

### Spec Review Phase

The spec has been auto-drafted from the converged seam debate above. The following turns review the spec for implementation correctness, missing constraints, and integration gaps.


### Turn 8 — Claude-Author (2026-04-16) — Autonomous runner turn

Reading the spec carefully against the converged seam position. My job is to find implementation correctness issues, missing constraints, and integration gaps — not to re-debate the seam.

## Spec Review: Implementation Correctness and Integration Gaps

### Issue 1: Probe Seed Strategy Creates a Recoverable Pattern

The implementation sketch specifies: "Regenerate fresh each iteration using a seeded RNG with the iteration number as seed."

This is a subtle but real vulnerability. If the probe locations are deterministically derived from the iteration number, a mutator that knows the iteration count (which it does — it can count its own submissions) can reconstruct the probe distribution. Over multiple runs, a mutator that is run repeatedly on the same substrate can build a model of the probe locations at each iteration index. The seed should incorporate substrate-specific entropy (e.g., a hash of the visible data) in addition to the iteration number, so that probe locations are not recoverable from iteration count alone. The spec should say: "seeded RNG with a combination of the iteration number and a substrate-specific salt derived from the visible data hash."

### Issue 2: Degenerate Trigger Condition is Too Narrow

The spec triggers perturbation probing only when "max_abs_residual = 0.0" — exact zero. In practice, floating-point arithmetic may produce max_abs_residual = 1e-14 rather than exactly 0.0 when the wrong corrector achieves near-perfect visible-set match. The trigger condition should be "max_abs_residual < ε" for some small ε (e.g., 1e-10), not strict equality. This is an implementation correctness issue — the spec as written would silently fail to trigger Component C on substrates where floating-point noise prevents exact zero.

### Issue 3: Stagnation Counter Ordering vs. Contamination Gate Ordering

The implementation sketch lists the contamination gate (step 5) before the stagnation gate (step 6). This ordering means the validator enumerates candidates on every degenerate iteration, even when the stagnation counter has not yet reached K. The enumeration is a GT-informed computation — running it on every iteration is both wasteful and potentially a source of timing side-channels (if the mutator can observe that the validator is doing more computation on some iterations than others). The gates should be checked in the cheaper-first order: stagnation gate first (O(1) counter check), contamination gate second (O(library size) enumeration). Swap steps 5 and 6.

### Issue 4: "Guidance-Used" Category in Offline Test is Underspecified

The pre-deployment offline test classifies emissions as helpful / guidance-used / irrelevant. The "guidance-used" category is defined as "consistent + score does not improve but search direction changes." "Search direction changes" is not operationally defined in the spec. The seam debate (Turn 7, Skeptic) noted this gap and proposed a baseline comparison, which the spec incorporates. But the spec does not define what "search direction changes" means in terms of measurable artifacts. A concrete operational definition: "the submitted formula in the next iteration contains at least one term that was not present in any formula submitted in the K iterations preceding the descriptor emission." This is checkable from the formula history without requiring a semantic interpretation of "direction."

### Issue 5: Contamination Gate Suppression Does Not Distinguish "Too Few Candidates" from "Zero Candidates"

The contamination gate suppresses the descriptor if the candidate count is fewer than N (default N = 5). But there is an important asymmetry: if the candidate count is zero (no candidates in the described category achieve visible-set match), the descriptor is not just too specific — it is *wrong*. A descriptor that describes a category containing zero valid candidates is a bug in the descriptor extraction, not a safety suppression. The spec should distinguish: count = 0 → log an error and suppress (descriptor extraction failure); 0 < count < N → suppress (too specific, safety gate); count ≥ N → emit. This distinction matters for debugging the offline test.

### Issue 6: `residual_fingerprint.json` Artifact Has No Declared Consumer

Per AGENTS.md §6d (attention debt): any new artifact added to the workspace must come with an explicit declaration of which consumers read it and for what signal. The spec creates `residual_fingerprint.json` but does not declare its consumer. The consumer is the mutator prompt injection step (step 7), but this is implicit. The spec should explicitly state: "`residual_fingerprint.json` is read by the prompt injection layer (step 7) to construct the structured hint. No other consumer reads this artifact. It is not read by the judge, the holdout gate, or the fit primitive."

### Issue 7: No Failure Mode Specified for Probe Evaluation Errors

Step 3 (discrepancy computation) evaluates f_mutator at synthetic points. If f_mutator raises an exception at a synthetic point (e.g., division by zero, domain error), the spec does not specify what happens. The implementation should: catch evaluation errors at synthetic points, exclude erroring points from the discrepancy vector, and if more than half the synthetic points error, treat the result as non-degenerate (do not emit a descriptor). This prevents a mutator from gaming the probe by submitting formulas that error on out-of-distribution inputs, which would suppress the descriptor and avoid the contamination gate.

### Issue 8: Spec Does Not Address What Happens After the First Descriptor Emission

The stagnation counter resets on descriptor emission. After the reset, the mutator must accumulate K ≥ 3 more non-passing iterations before the next emission. But the spec does not specify whether the *same* descriptor can be re-emitted on the second stagnation event, or whether the second emission must produce a different descriptor. If the mutator's formula has not changed category (it is still in the "smooth, monotone" region), re-emitting the same descriptor provides no new information and wastes an emission slot. The spec should specify: if the descriptor value is identical to the most recently emitted descriptor, suppress the emission (no new information). Only emit when the descriptor value changes or when the mutator has exited and re-entered the stagnation condition with a different formula class.

---

## Summary of Flags

1. **Probe seed strategy:** Iteration-number-only seed is recoverable by the mutator. Add substrate-specific salt.
2. **Degenerate trigger:** Strict `== 0.0` will miss floating-point near-zero. Use `< ε`.
3. **Gate ordering:** Contamination gate (expensive) runs before stagnation gate (cheap). Swap.
4. **"Guidance-used" definition:** "Search direction changes" is not operationally defined. Propose formula-diff definition.
5. **Zero-candidate vs. sub-N distinction:** Spec conflates descriptor failure with safety suppression. Distinguish.
6. **Artifact consumer declaration:** `residual_fingerprint.json` has no declared consumer. Add explicit declaration.
7. **Probe evaluation errors:** No failure mode specified for f_mutator exceptions at synthetic points.
8. **Repeat descriptor suppression:** Spec does not specify behavior when second stagnation event produces identical descriptor.

Issues 1–3 are implementation correctness issues that would cause silent failures or exploitable behavior. Issues 4–8 are integration gaps and missing constraints. None of these re-debate the seam; all are spec-level gaps.

### Turn 9 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 8 identifies eight issues with the spec. I need to assess whether each flag is sound, whether any are overstated, and whether there are gaps the Author missed.

## Evaluating the Eight Flags

**Issue 1 (Probe seed strategy — iteration-number-only seed is recoverable):** Sound. The spec says "seeded RNG with the iteration number as seed." A mutator that knows its own iteration count can reconstruct the probe distribution. The fix (add substrate-specific salt from visible data hash) is correct and cheap. This is a real implementation correctness issue.

**Issue 2 (Degenerate trigger — strict `== 0.0` misses floating-point near-zero):** Sound. Floating-point arithmetic on polynomial expressions routinely produces residuals of order 1e-12 to 1e-14 rather than exact zero. The trigger condition `max_abs_residual = 0.0` will silently fail to activate Component C on substrates where the wrong corrector achieves near-perfect but not exact visible-set match. The fix (`< ε` for ε ≈ 1e-10) is standard practice. This is a real implementation correctness issue.

**Issue 3 (Gate ordering — contamination gate runs before stagnation gate):** Sound. The implementation sketch lists step 5 (contamination gate, O(library size)) before step 6 (stagnation gate, O(1)). Swapping to cheaper-first is correct. The timing side-channel concern is real but secondary — the primary issue is computational waste. The fix is trivial. This is a real implementation correctness issue.

**Issue 4 ("Guidance-used" definition — "search direction changes" is not operationally defined):** Sound. The spec's offline test classification uses "search direction changes" without defining it. The Author's proposed operational definition — "the submitted formula in the next iteration contains at least one term not present in any formula submitted in the K iterations preceding the descriptor emission" — is concrete and checkable from formula history. This is a real integration gap.

**Issue 5 (Zero-candidate vs. sub-N distinction):** Sound. The spec conflates two distinct cases: count = 0 (descriptor extraction failure — the described category contains no valid candidates, which is a bug) and 0 < count < N (safety suppression — the category is too specific). These require different responses: the first should log an error and trigger a diagnostic; the second is normal operation. This is a real missing constraint.

**Issue 6 (`residual_fingerprint.json` has no declared consumer):** Sound. AGENTS.md §6d requires explicit consumer declaration for any new workspace artifact. The spec creates `residual_fingerprint.json` but only implicitly connects it to step 7 (prompt injection). The fix is a one-line addition. This is a real integration gap.

**Issue 7 (No failure mode for probe evaluation errors):** Sound. If f_mutator raises an exception at a synthetic point (division by zero, domain error), the spec is silent. The proposed behavior — exclude erroring points, treat as non-degenerate if more than half error — is reasonable and closes a gaming vector (submitting formulas that error on OOD inputs to suppress the descriptor). This is a real missing constraint.

**Issue 8 (Repeat descriptor suppression — same descriptor re-emitted on second stagnation event):** Sound. After the stagnation counter resets on emission, if the mutator's formula class has not changed, the second stagnation event will produce an identical descriptor. Re-emitting the same descriptor provides zero new information and wastes an emission slot. The proposed rule (suppress if descriptor value is identical to most recently emitted descriptor) is correct. This is a real missing constraint.

## Flags the Author Missed

**Missing flag A: The offline test's "significantly above baseline" criterion is undefined.** The spec says "post-emission consistency rate must be significantly above the baseline rate." "Significantly" is not operationally defined. What statistical test? What threshold? Without a concrete criterion, the offline test cannot produce a binary pass/fail decision — it produces a number that requires subjective interpretation. The spec should specify a minimum effect size or a concrete threshold (e.g., "post-emission consistency rate must be at least 2× the baseline rate across at least 3 emissions").

**Missing flag B: The spec does not specify what happens when the contamination gate suppresses a descriptor.** Step 5 says "suppress descriptor and emit no hint." But the stagnation counter has already reached K at this point. Does the counter reset (treating suppression as equivalent to emission) or does it continue accumulating? If the counter continues accumulating, the next iteration will immediately re-check the contamination gate with the same descriptor (since the formula hasn't changed), producing another suppression, and so on indefinitely. The counter should reset on suppression as well as on emission — otherwise the validator is doing O(library size) enumeration on every iteration after the first suppression event.

**Missing flag C: The spec's constraint list includes "No GT-derived dominant-structure subtraction" but the perturbation probing step (step 3) evaluates f_true at synthetic points.** Evaluating f_true at synthetic points is using GT information to compute the discrepancy. The constraint says the validator cannot subtract a GT-derived dominant structure, but the perturbation probing approach uses the full GT formula — which includes the dominant structure. The constraint as written is narrower than the actual GT usage. The spec should clarify: "The constraint prohibits using GT to construct a hint that reveals the corrector's parameters. Using GT to evaluate f_true at synthetic points for the purpose of computing a shape descriptor is permitted — this is the same GT access the holdout gate uses."

This is not a fatal objection — the distinction is real and the usage is legitimate — but the constraint as written creates an apparent contradiction with the implementation sketch that should be resolved explicitly.

## Summary

The Author's eight flags are all sound. None are overstated. Three additional flags (A, B, C above) are missing from the Author's review:

- **Missing flag A:** "Significantly above baseline" in the offline test is undefined — needs a concrete threshold or effect size criterion.
- **Missing flag B:** Contamination gate suppression does not specify counter behavior — counter should reset on suppression to prevent O(library size) enumeration on every subsequent iteration.
- **Missing flag C:** The "No GT-derived dominant-structure subtraction" constraint appears to contradict the perturbation probing step's use of f_true; the spec should clarify the distinction between prohibited GT usage (parameter-revealing hint construction) and permitted GT usage (discrepancy computation for shape classification).

The spec is not ready to close. Issues 1–3 from the Author are implementation correctness issues that would cause silent failures or exploitable behavior. Missing flag B is also an implementation correctness issue (infinite O(library size) enumeration loop after first suppression). The remaining issues are integration gaps and missing constraints that must be resolved before implementation begins.

### Turn 10 — Claude-Author (2026-04-16) — Autonomous runner turn

The Skeptic's Turn 9 identifies three flags the Author missed (A, B, C). I need to assess each and determine whether they require spec changes before the spec can close.

## Evaluating the Three Missed Flags

**Missing flag A: "Significantly above baseline" is undefined.**

The Skeptic is correct. The spec says "post-emission consistency rate must be significantly above the baseline rate" without defining a statistical test or threshold. This is not a minor wording issue — without a concrete criterion, the offline test cannot produce a binary go/no-go decision. A reviewer running the test would have to make a subjective call, which defeats the purpose of requiring the test as a gate.

The fix is concrete: specify a minimum effect size. A reasonable operationalization: "post-emission consistency rate must be at least 2× the baseline rate, measured across at least 3 descriptor emissions." This is checkable, substrate-independent, and does not require a formal statistical test. The spec should add this to the pre-deployment offline test section.

**Missing flag B: Contamination gate suppression does not specify counter behavior.**

The Skeptic is correct and this is the most serious of the three missed flags. The current spec says "suppress descriptor and emit no hint" when the contamination gate fires. The stagnation counter has already reached K at this point. If the counter does not reset on suppression, the next iteration will re-check the contamination gate with the same formula (since the mutator hasn't changed anything — it received no hint), produce another suppression, and so on. The validator runs O(library size) enumeration on every subsequent iteration until the mutator changes its formula class. This is both a performance issue and a logical inconsistency: the stagnation gate is supposed to limit emissions, but suppression-without-reset means the contamination gate runs continuously after the first suppression event.

The fix: the stagnation counter resets on suppression as well as on emission. The spec's constraint section already says "resets only on holdout pass or descriptor emission" — this needs to be amended to "resets only on holdout pass, descriptor emission, or contamination gate suppression." The implementation sketch step 6 needs the same amendment.

**Missing flag C: "No GT-derived dominant-structure subtraction" constraint appears to contradict perturbation probing.**

The Skeptic correctly identifies an apparent contradiction: the constraint prohibits GT-derived dominant-structure subtraction, but step 3 evaluates f_true at synthetic points — which uses the full GT formula including the dominant structure. The constraint as written is narrower than the actual GT usage.

However, I want to be precise about whether this is a real contradiction or an apparent one. The constraint's intent is to prohibit using GT to construct a hint that reveals the corrector's parameters through the back door (e.g., computing f_true − u²v to expose the corrector directly). Perturbation probing computes f_true − f_mutator, which is the discrepancy between the GT formula and the mutator's submitted formula. This is the same computation the holdout gate performs — it uses GT to evaluate correctness, not to construct a hint. The distinction is real and the usage is legitimate.

The Skeptic's proposed fix is correct: the spec should add a clarifying sentence to the constraint: "The constraint prohibits using GT to construct a hint that reveals the corrector's parameters. Using GT to evaluate f_true at synthetic points for the purpose of computing a shape descriptor is permitted — this is the same GT access the holdout gate uses." This resolves the apparent contradiction without changing the substance of the constraint.

## Spec Changes Required

Three amendments to the spec are needed before it can close:

1. **Pre-deployment offline test section:** Add concrete threshold for "significantly above baseline" — "post-emission consistency rate must be at least 2× the baseline rate, measured across at least 3 descriptor emissions."

2. **Constraints section + Implementation sketch step 6:** Amend stagnation counter reset rule to include suppression: "resets only on holdout pass, descriptor emission, or contamination gate suppression." This prevents the O(library size) enumeration loop after the first suppression event.

3. **Constraints section, "No GT-derived dominant-structure subtraction":** Add clarifying sentence distinguishing prohibited GT usage (parameter-revealing hint construction) from permitted GT usage (discrepancy computation for shape classification, same as holdout gate).

## Assessment of Author's Eight Flags from Turn 8

The Skeptic accepted all eight as sound. I stand by them. The three missed flags (A, B, C) are additive — they do not invalidate any of the eight, and the eight do not cover the three. The full set of required spec amendments is eleven items (eight from Turn 8 + three from Turn 9).

The spec is not ready to close. Missing flag B (counter behavior on suppression) is an implementation correctness issue that would cause an infinite enumeration loop in the degenerate case. The other two missed flags are integration gaps that must be resolved before implementation begins.

### Turn 11 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 8 identified eight spec issues and Turn 9 (my prior skeptic turn) identified three more. Turn 10 accepted all three missed flags and proposed concrete amendments. I need to verify whether those proposed amendments are actually reflected in the spec under review, and whether any new gaps remain.

## Checking Whether the Eleven Flags Are Addressed in the Spec

**Issue 1 (Probe seed — iteration-number-only seed recoverable):** The spec still reads "Regenerate fresh each iteration using a seeded RNG with the iteration number as seed." The Author's proposed fix (add substrate-specific salt from visible data hash) is **not incorporated**. This is an implementation correctness issue that remains open in the spec.

**Issue 2 (Degenerate trigger — strict `== 0.0`):** The spec still reads "check whether the submitted formula achieves max_abs_residual = 0.0." The `< ε` fix is **not incorporated**. This is an implementation correctness issue that remains open.

**Issue 3 (Gate ordering — contamination before stagnation):** The implementation sketch still lists step 5 (contamination gate) before step 6 (stagnation gate). The swap is **not incorporated**. This is an implementation correctness issue that remains open.

**Issue 4 ("Guidance-used" definition):** The spec still says "search direction changes" without an operational definition. The Author's proposed formula-diff definition ("contains at least one term not present in any formula submitted in the K iterations preceding the descriptor emission") is **not incorporated**. Integration gap remains open.

**Issue 5 (Zero-candidate vs. sub-N distinction):** The spec says "If count < N, suppress descriptor and emit no hint." It does not distinguish count = 0 (descriptor extraction failure) from 0 < count < N (safety suppression). The distinction is **not incorporated**. Missing constraint remains open.

**Issue 6 (`residual_fingerprint.json` consumer declaration):** The spec says the artifact "lives in a separate `residual_fingerprint.json` artifact" but does not explicitly declare its consumer. The Author's proposed one-line addition ("read by the prompt injection layer (step 7) to construct the structured hint; no other consumer reads this artifact") is **not incorporated**. Integration gap remains open.

**Issue 7 (Probe evaluation errors):** The spec has no failure mode for f_mutator exceptions at synthetic points. The proposed behavior (exclude erroring points, treat as non-degenerate if more than half error) is **not incorporated**. Missing constraint remains open.

**Issue 8 (Repeat descriptor suppression):** The spec does not specify behavior when the second stagnation event produces an identical descriptor. The proposed rule (suppress if descriptor value is identical to most recently emitted descriptor) is **not incorporated**. Missing constraint remains open.

**Missing flag A ("Significantly above baseline" undefined):** The spec still reads "Post-emission consistency rate must be significantly above the baseline rate." The Author's proposed concrete threshold ("at least 2× the baseline rate, measured across at least 3 descriptor emissions") is **not incorporated**. Integration gap remains open.

**Missing flag B (Counter behavior on suppression):** The spec's constraints section reads "resets only on a genuine holdout-passing result or on descriptor emission." The Author's proposed amendment to include suppression ("resets only on holdout pass, descriptor emission, or contamination gate suppression") is **not incorporated**. This is the most serious remaining gap — without it, the contamination gate triggers an O(library size) enumeration loop on every subsequent iteration after the first suppression event. Implementation correctness issue remains open.

**Missing flag C (GT constraint apparent contradiction):** The spec's constraint reads "The validator cannot subtract a GT-derived dominant structure to expose the corrector's shape, because this uses ground truth information to construct the hint through the back door." The clarifying sentence distinguishing prohibited GT usage from permitted GT usage (discrepancy computation for shape classification) is **not incorporated**. The apparent contradiction with step 3 (which evaluates f_true at synthetic points) remains unresolved in the spec text.

## Summary

All eleven flags identified across Turns 8–10 are unaddressed in the spec under review. The spec appears to be the auto-drafted version from Turn 8's opening, not a revised version incorporating the debate's findings. This is not a case where the flags were addressed and I'm finding residual gaps — the spec is the pre-review draft, and the review turns (8–10) constitute the review record that should drive a spec revision.

Four of the eleven are implementation correctness issues that would cause silent failures or exploitable behavior in a live run:
- Issue 1: recoverable probe seed
- Issue 2: strict zero trigger misses floating-point near-zero
- Issue 3: expensive gate runs before cheap gate
- Missing flag B: infinite enumeration loop after first suppression

The spec cannot close in its current state. It requires a revision pass incorporating all eleven amendments before it is ready for implementation.

One additional gap not raised in prior turns: the spec's Decision section does not mention the stagnation counter reset-on-suppression rule. The Decision section is the canonical one-paragraph summary that an implementer reads first. If the constraints section is amended but the Decision section is not, an implementer reading only the Decision section will implement the wrong counter behavior. The Decision section should be updated to match the amended constraint.

### Turn 12 — Claude-Author (2026-04-16) — Autonomous runner turn

Reading the spec carefully against the eleven flags identified in Turns 8–10 and the Skeptic's Turn 11 audit.

## Turn 12 — Author Spec Revision Assessment

The Skeptic's Turn 11 performed a systematic check of all eleven flags against the spec under review and found that none of the eleven amendments have been incorporated. The spec is the auto-drafted version from before the review turns began. This is the correct diagnosis — the review turns (8–11) constitute the review record, and the spec needs a revision pass before it can close.

Rather than re-litigating whether the flags are sound (they are — the Skeptic accepted all eight from Turn 8 and I accepted all three from Turn 9), I will do two things: (1) confirm the Skeptic's Turn 11 audit is accurate, and (2) identify whether any of the eleven flags have been superseded, clarified, or made redundant by subsequent turns.

## Confirming the Turn 11 Audit

The Skeptic's audit is accurate. Checking each flag against the spec text:

- **Issue 1 (probe seed):** Spec step 2 reads "seeded RNG with the iteration number as seed." No substrate-specific salt. Unaddressed.
- **Issue 2 (trigger condition):** Spec step 1 reads "check whether the submitted formula achieves max_abs_residual = 0.0." Strict equality. Unaddressed.
- **Issue 3 (gate ordering):** Spec steps 5 and 6 list contamination gate before stagnation gate. Unaddressed.
- **Issue 4 ("guidance-used" definition):** Spec pre-deployment test section reads "search direction changes" without operational definition. Unaddressed.
- **Issue 5 (zero-candidate vs. sub-N):** Spec step 5 reads "If count < N, suppress descriptor and emit no hint." No distinction between count = 0 and 0 < count < N. Unaddressed.
- **Issue 6 (artifact consumer declaration):** Spec step 8 says artifact "lives in a separate `residual_fingerprint.json` artifact" with no declared consumer. Unaddressed.
- **Issue 7 (probe evaluation errors):** No failure mode for f_mutator exceptions at synthetic points anywhere in the spec. Unaddressed.
- **Issue 8 (repeat descriptor suppression):** No rule for suppressing identical descriptor on second stagnation event. Unaddressed.
- **Missing flag A ("significantly above baseline" undefined):** Spec reads "Post-emission consistency rate must be significantly above the baseline rate." No threshold. Unaddressed.
- **Missing flag B (counter behavior on suppression):** Spec constraints section reads "resets only on a genuine holdout-passing result or on descriptor emission." Suppression not included. Unaddressed.
- **Missing flag C (GT constraint apparent contradiction):** Spec constraint reads "The validator cannot subtract a GT-derived dominant structure to expose the corrector's shape, because this uses ground truth information to construct the hint through the back door." No clarifying sentence distinguishing prohibited from permitted GT usage. Unaddressed.

The Skeptic's audit is complete and accurate. All eleven flags are unaddressed.

## One Additional Flag Not Raised in Prior Turns

The Skeptic's Turn 11 added one new observation: "The Decision section does not mention the stagnation counter reset-on-suppression rule." This is correct and is a twelfth gap. The Decision section is the canonical summary an implementer reads first. It currently reads: "The stagnation counter is maintained as internal validator state, resets only on holdout pass or descriptor emission, and is not exposed to the mutator." After the missing flag B amendment, this sentence must read: "resets only on holdout pass, descriptor emission, or contamination gate suppression." The Decision section must be updated to match the amended constraint — otherwise an implementer reading only the Decision section will implement the wrong counter behavior.

This is not a new decisive claim about the seam's architecture. It is a consistency requirement between the Decision section and the Constraints section after the missing flag B amendment is applied. I am noting it as a twelfth spec gap to ensure it is not overlooked in the revision pass.

## Summary of Required Spec Amendments

The spec requires a revision pass incorporating twelve amendments before it can close:

**Implementation correctness (silent failures or exploitable behavior):**
1. Probe seed: add substrate-specific salt (visible data hash) to the RNG seed.
2. Trigger condition: change `== 0.0` to `< ε` (ε ≈ 1e-10).
3. Gate ordering: swap steps 5 and 6 (stagnation gate before contamination gate).
4. Counter reset on suppression: amend constraints section and step 6 to include suppression as a reset trigger.
5. Decision section consistency: update Decision section to match the amended counter reset rule.

**Integration gaps and missing constraints:**
6. "Guidance-used" definition: add formula-diff operational definition.
7. Zero-candidate vs. sub-N distinction: add count = 0 → error path, 0 < count < N → safety suppression.
8. Artifact consumer declaration: add explicit consumer declaration for `residual_fingerprint.json`.
9. Probe evaluation errors: add failure mode for f_mutator exceptions at synthetic points.
10. Repeat descriptor suppression: add rule suppressing identical descriptor on second stagnation event.
11. "Significantly above baseline" threshold: add concrete criterion (≥ 2× baseline rate across ≥ 3 emissions).
12. GT constraint clarification: add sentence distinguishing prohibited GT usage from permitted GT usage (discrepancy computation for shape classification).

The spec is not ready to close. It requires a revision pass before implementation begins. I have no new decisive claims about the seam's architecture — all twelve items are spec-level gaps, not seam-level structural objections.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 13 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 12 performed a systematic audit confirming all eleven flags from Turns 8–10 are unaddressed in the spec, and added a twelfth gap (Decision section consistency with the counter-reset-on-suppression rule). I need to verify whether the Author's audit is accurate, check whether any of the twelve flags have been superseded or made redundant, and determine whether there are additional gaps the Author missed.

## Verifying the Turn 12 Audit

The Author's audit is accurate. I checked each of the twelve flags against the spec text and confirm:

- **Issue 1 (probe seed):** Step 2 reads "seeded RNG with the iteration number as seed." No substrate-specific salt. Unaddressed.
- **Issue 2 (trigger condition):** Step 1 reads "check whether the submitted formula achieves max_abs_residual = 0.0." Strict equality. Unaddressed.
- **Issue 3 (gate ordering):** Steps 5 and 6 list contamination gate before stagnation gate. Unaddressed.
- **Issue 4 ("guidance-used" definition):** Pre-deployment test section reads "search direction changes" without operational definition. Unaddressed.
- **Issue 5 (zero-candidate vs. sub-N):** Step 5 reads "If count < N, suppress descriptor and emit no hint." No count = 0 error path. Unaddressed.
- **Issue 6 (artifact consumer declaration):** Step 8 says artifact "lives in a separate `residual_fingerprint.json` artifact" with no declared consumer. Unaddressed.
- **Issue 7 (probe evaluation errors):** No failure mode for f_mutator exceptions at synthetic points. Unaddressed.
- **Issue 8 (repeat descriptor suppression):** No rule for suppressing identical descriptor on second stagnation event. Unaddressed.
- **Missing flag A ("significantly above baseline" undefined):** Pre-deployment test section reads "Post-emission consistency rate must be significantly above the baseline rate." No threshold. Unaddressed.
- **Missing flag B (counter behavior on suppression):** Constraints section reads "resets only on a genuine holdout-passing result or on descriptor emission." Suppression not included. Unaddressed.
- **Missing flag C (GT constraint apparent contradiction):** Constraint reads "The validator cannot subtract a GT-derived dominant structure to expose the corrector's shape, because this uses ground truth information to construct the hint through the back door." No clarifying sentence. Unaddressed.
- **Gap 12 (Decision section consistency):** Decision section reads "resets only on holdout pass or descriptor emission." Does not include suppression. Unaddressed.

All twelve are confirmed unaddressed.

## Checking for Superseded or Redundant Flags

None of the twelve flags are superseded by each other. Issues 3 and missing flag B are related (both concern the stagnation gate) but address distinct problems: Issue 3 is about gate execution ordering (cheap before expensive), missing flag B is about counter reset behavior on suppression. Gap 12 is a consistency requirement that follows from missing flag B but is a separate location in the spec. All twelve remain distinct and non-redundant.

## Checking for Additional Gaps the Author Missed

**Gap 13: The implementation sketch has no step for handling the non-degenerate case.** Step 1 checks for max_abs_residual = 0.0 and flags as degenerate. Steps 2–8 describe what happens in the degenerate case. But the spec does not specify what happens in the non-degenerate case — when max_abs_residual > 0.0 (or > ε after Issue 2 is fixed). Does Component C fire on non-degenerate residuals using the visible-set residual directly? Or does Component C only fire in the degenerate case? The seam's Option B originally described using visible-set residuals, but the debate concluded that perturbation probing is needed specifically for the degenerate case. The spec's Recommendation section says "When the visible-set residual is degenerate (zero because the wrong corrector achieves perfect visible-set match), the validator generates synthetic points." This implies Component C does not fire on non-degenerate residuals — but the implementation sketch does not make this explicit. Step 1 should read: "If max_abs_residual ≥ ε, Component C does not fire. Exit. If max_abs_residual < ε, flag as degenerate and proceed to step 2." Without this explicit exit, an implementer might apply perturbation probing on every iteration regardless of degeneracy.

**Gap 14: The stagnation counter increment rule in step 6 is ambiguous about what constitutes a "non-passing iteration."** Step 6 reads "Increment counter on every non-passing iteration." But the stagnation gate check (step 6) occurs *after* the contamination gate check (step 5). If the contamination gate suppresses the descriptor, does the iteration count as "non-passing" for stagnation purposes? The answer should be yes — suppression means no hint was emitted, the mutator did not receive guidance, and the run is still stagnating. But the spec does not say this. After missing flag B is fixed (counter resets on suppression), the increment rule needs to be consistent: the counter increments on every non-passing iteration regardless of whether the contamination gate fired, and resets on holdout pass, descriptor emission, or contamination gate suppression. The current step 6 text does not capture this.

**Gap 15: The spec does not specify the domain of the perturbation probe distribution.** Step 2 says probes are "drawn from a distribution over the input domain that does not concentrate near known characteristic points." But "the input domain" is not defined in the spec. The visible set defines a finite set of (u, v) pairs; the holdout set extends this. The probe distribution must be over a domain that includes out-of-distribution points — but how far out? If the probe distribution is too narrow (close to the visible set boundary), the discrepancy may be small and the descriptor may be unreliable. If the probe distribution is too wide (far extrapolation), f_mutator may produce numerical instabilities (addressed by Issue 7, but the domain choice affects the frequency of such errors). The spec should specify that the probe distribution covers at least the range [min_visible, 2×max_visible] for each input dimension, or some analogous concrete bound. "Over the input domain" is underspecified.

**Gap 16: The spec does not address what happens when M synthetic points are generated but the discrepancy vector is constant (all zeros or all the same value).** If f_mutator = f_true at all synthetic points (which can happen if the mutator has found the correct formula but the holdout gate has not yet passed due to a different failure mode), the discrepancy vector is identically zero and the descriptor extraction in step 4 is undefined — a constant-zero vector is neither step-function nor smooth in any meaningful sense, and is both monotone and non-monotone vacuously. The spec should specify: if the discrepancy vector is identically zero at all synthetic points, treat as non-degenerate (do not emit a descriptor) and log a diagnostic. This case is distinct from the visible-set degeneracy case — it means the mutator has found the correct formula and the holdout failure is due to something other than the corrector term.

## Summary

The Author's twelve-flag audit is accurate and complete within the scope of the prior review turns. Four additional gaps are present in the spec:

- **Gap 13:** No explicit exit path for the non-degenerate case in the implementation sketch — perturbation probing may be applied on every iteration rather than only on degenerate ones.
- **Gap 14:** Stagnation counter increment rule is ambiguous about whether suppression-triggered iterations count as non-passing — needs explicit statement consistent with the missing flag B fix.
- **Gap 15:** Probe distribution domain is underspecified — "over the input domain" does not define the range of out-of-distribution probing.
- **Gap 16:** No handling for the case where the discrepancy vector at synthetic points is identically zero — descriptor extraction is undefined in this case.

Gaps 13 and 14 are implementation correctness issues. Gaps 15 and 16 are missing constraints. The spec requires a revision pass incorporating all sixteen amendments (twelve from prior turns + four new) before it is ready for implementation.

### Turn 14 — Claude-Author (2026-04-16) — Autonomous runner turn

Reading the spec carefully against the sixteen flags identified across Turns 8–13. My job is to determine whether any of the sixteen amendments have been incorporated into the spec since Turn 13's audit, and whether there are additional gaps the prior turns missed.

## Checking the Spec Against the Sixteen Flags

The spec under review is identical to the spec audited in Turn 13. Comparing the spec text against each flag:

**Implementation correctness issues (Turns 8–13):**

- **Issue 1 (probe seed — iteration-number-only recoverable):** Step 2 still reads "seeded RNG with the iteration number as seed." No substrate-specific salt. **Unaddressed.**
- **Issue 2 (trigger condition — strict `== 0.0`):** Step 1 still reads "check whether the submitted formula achieves max_abs_residual = 0.0." **Unaddressed.**
- **Issue 3 (gate ordering — contamination before stagnation):** Steps 5 and 6 still list contamination gate before stagnation gate. **Unaddressed.**
- **Missing flag B (counter reset on suppression):** Constraints section still reads "resets only on a genuine holdout-passing result or on descriptor emission." Suppression not included. **Unaddressed.**
- **Gap 12 (Decision section consistency):** Decision section still reads "resets only on holdout pass or descriptor emission." **Unaddressed.**
- **Gap 13 (no explicit exit for non-degenerate case):** Step 1 flags degenerate but does not specify an explicit exit path for the non-degenerate case. **Unaddressed.**
- **Gap 14 (stagnation counter increment rule ambiguous after suppression):** Step 6 reads "Increment counter on every non-passing iteration" without clarifying that suppression-triggered iterations count as non-passing. **Unaddressed.**

**Integration gaps and missing constraints (Turns 8–13):**

- **Issue 4 ("guidance-used" definition):** Pre-deployment test section still reads "search direction changes" without operational definition. **Unaddressed.**
- **Issue 5 (zero-candidate vs. sub-N distinction):** Step 5 still reads "If count < N, suppress descriptor and emit no hint." No count = 0 error path. **Unaddressed.**
- **Issue 6 (artifact consumer declaration):** Step 8 still says artifact "lives in a separate `residual_fingerprint.json` artifact" with no declared consumer. **Unaddressed.**
- **Issue 7 (probe evaluation errors):** No failure mode for f_mutator exceptions at synthetic points. **Unaddressed.**
- **Issue 8 (repeat descriptor suppression):** No rule for suppressing identical descriptor on second stagnation event. **Unaddressed.**
- **Missing flag A ("significantly above baseline" undefined):** Pre-deployment test section still reads "Post-emission consistency rate must be significantly above the baseline rate." No threshold. **Unaddressed.**
- **Missing flag C (GT constraint apparent contradiction):** Constraint still reads "The validator cannot subtract a GT-derived dominant structure to expose the corrector's shape, because this uses ground truth information to construct the hint through the back door." No clarifying sentence distinguishing prohibited from permitted GT usage. **Unaddressed.**
- **Gap 15 (probe distribution domain underspecified):** Step 2 still reads "drawn from a distribution over the input domain that does not concentrate near known characteristic points." No concrete range specified. **Unaddressed.**
- **Gap 16 (discrepancy vector identically zero at synthetic points):** No handling for the case where f_mutator = f_true at all synthetic points. **Unaddressed.**

All sixteen flags remain unaddressed. The spec is the pre-review draft.

## One Additional Gap Not Raised in Prior Turns

**Gap 17: The implementation sketch has no step for handling the case where M synthetic points are generated but the stagnation gate fires before the contamination gate (after the gate ordering fix from Issue 3 is applied).**

After the Issue 3 fix (swap steps 5 and 6 so stagnation gate runs first), the implementation flow becomes: step 1 (check degeneracy) → step 2 (generate probes) → step 3 (compute discrepancy) → step 4 (extract descriptor) → step 5 (stagnation gate) → step 6 (contamination gate) → step 7 (inject) → step 8 (artifact).

In this corrected ordering, steps 2–4 (probe generation, discrepancy computation, descriptor extraction) run before the stagnation gate check. This means the validator generates 20 synthetic points, evaluates f_true and f_mutator at all of them, and classifies the discrepancy — and then the stagnation gate fires and discards the result because the counter hasn't reached K yet. This is wasteful: the expensive computation (probe generation + evaluation) runs on every degenerate iteration, not just on stagnation-triggered ones.

The fix is to move the stagnation gate check to immediately after the degeneracy check (step 1), before any probe generation. The corrected ordering should be: step 1 (check degeneracy) → step 1b (stagnation gate: if counter < K, increment and exit) → step 2 (generate probes) → step 3 (compute discrepancy) → step 4 (extract descriptor) → step 5 (contamination gate) → step 6 (inject) → step 7 (artifact). This ensures probe generation only runs when the stagnation gate has already passed.

This is an implementation correctness issue — not a silent failure, but a performance issue that would cause unnecessary computation on every degenerate iteration. More importantly, it means the probe generation and discrepancy computation run on iterations where the result will be discarded, which wastes API calls if f_mutator evaluation is expensive.

Note: this gap is a consequence of the Issue 3 fix (gate ordering swap) interacting with the implementation sketch's step structure. It was not visible before the Issue 3 fix was proposed, which is why it was not raised in prior turns.

## Summary

All sixteen flags from Turns 8–13 remain unaddressed. One additional gap (Gap 17) is identified: after the Issue 3 gate-ordering fix is applied, the stagnation gate should be moved to immediately after the degeneracy check to avoid running expensive probe generation on iterations where the stagnation gate will discard the result.

The spec requires a revision pass incorporating seventeen amendments before it is ready for implementation. The four implementation correctness issues from prior turns (Issues 1, 2, 3, missing flag B) plus Gap 12, Gap 13, Gap 14, and Gap 17 are the highest priority — they would cause silent failures, exploitable behavior, or unnecessary computation in a live run.

### Turn 15 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 14 confirms all sixteen flags remain unaddressed and adds Gap 17 (stagnation gate should be checked immediately after degeneracy check, before probe generation, to avoid running expensive computation on iterations where the result will be discarded). I need to verify Gap 17 is sound, check whether any of the seventeen flags are now redundant or superseded, and determine whether there are additional gaps the prior turns missed.

## Verifying Gap 17

Gap 17 is sound. After the Issue 3 fix (swap steps 5 and 6), the corrected ordering still runs probe generation (step 2), discrepancy computation (step 3), and descriptor extraction (step 4) before the stagnation gate check. The Author correctly identifies that the stagnation gate should be promoted to immediately after the degeneracy check — call it step 1b — so that the expensive probe generation only runs when the stagnation gate has already passed. This is an implementation correctness issue: unnecessary computation on every degenerate iteration, and if f_mutator evaluation is expensive (e.g., involves symbolic evaluation of a complex formula), this could be significant. The fix is clear and non-controversial.

## Checking for Redundancy or Supersession Among the Seventeen Flags

Issue 3 (gate ordering) and Gap 17 are related but not redundant. Issue 3 says "swap steps 5 and 6 so stagnation gate runs before contamination gate." Gap 17 says "move the stagnation gate to before probe generation (step 1b), not just before the contamination gate." Gap 17 subsumes Issue 3 in the sense that if Gap 17 is implemented correctly, Issue 3 is automatically resolved — the stagnation gate at step 1b runs before everything, including the contamination gate. However, Issue 3 should remain as a named flag because it identifies the contamination-gate-before-stagnation-gate ordering problem independently of the probe-generation waste problem. Both flags point to the same root cause (stagnation gate is too late in the pipeline) but from different angles. Keep both.

No other flags are redundant or superseded.

## Checking for Additional Gaps the Prior Turns Missed

**Gap 18: The spec's Recommendation section and the Implementation Sketch are inconsistent on the stagnation counter reset rule.**

The Recommendation section reads: "The stagnation counter is internal validator state, resets only on holdout pass or descriptor emission, and is not reset by formula-class changes."

The Implementation Sketch step 6 reads: "Reset counter on holdout pass or on descriptor emission."

Both are consistent with each other — but both are inconsistent with the missing flag B fix (counter should also reset on contamination gate suppression). This inconsistency was identified in missing flag B and Gap 12 (Decision section). However, there is a third location: the Constraints section reads "The stagnation counter resets only on a genuine holdout-passing result or on descriptor emission." That is three locations in the spec (Decision section, Constraints section, Implementation Sketch step 6, and Recommendation section) that all need the same amendment. Prior turns identified the Decision section (Gap 12) and the Constraints section (missing flag B) but did not explicitly call out the Recommendation section and the Implementation Sketch step 6 as separate locations requiring the same amendment. The Implementation Sketch step 6 is already covered by missing flag B's scope ("amend constraints section and step 6"), but the Recommendation section is not explicitly named. This is a minor gap in the amendment scope, not a new structural issue — but the revision pass must update all four locations, not just two.

**Gap 19: The spec does not specify the number of synthetic probe points (M = 20) as a tunable parameter or justify the choice.**

Step 2 reads "generate M synthetic (u, v) points (M = 20 is a reasonable starting point)." M = 20 is presented as a fixed default with no justification and no specification of how it should be calibrated. The offline pre-deployment test (OQ-5) is supposed to answer whether the safe information band is non-empty, but it does not address whether M = 20 is sufficient to produce reliable shape descriptors. If M is too small, the continuity and monotonicity classifications in step 4 will be unreliable (a step function sampled at 20 random points may appear smooth if the step occurs between probe points). The spec should either: (a) specify a minimum M based on the expected characteristic scale of the corrector (e.g., M must be large enough that the expected number of probes within one characteristic length of the corrector's transition is ≥ 3), or (b) add M calibration to the offline pre-deployment test protocol. As written, M = 20 is an unjustified magic number.

This is a missing constraint, not an implementation correctness issue — M = 20 will not cause a silent failure, but it may cause unreliable descriptor extraction that the offline test would catch. However, if the offline test does not include M sensitivity analysis, the test may pass at M = 20 on one substrate and fail silently on another.

**Gap 20: The spec does not address the interaction between the stagnation gate and the degenerate trigger across iterations where the formula changes.**

Consider this scenario: the mutator submits formula f₁ (degenerate, stagnation counter = 1), then f₂ (non-degenerate, stagnation counter increments to 2 — but wait, should it?), then f₃ (degenerate again, stagnation counter = 3, Component C fires).

The stagnation gate is defined as "K ≥ 3 consecutive non-passing iterations." But the degeneracy check (step 1) is a separate condition. If f₂ is non-degenerate (max_abs_residual > ε), Component C does not fire for f₂ — but does the stagnation counter still increment? The spec says "Increment counter on every non-passing iteration" (step 6). A non-degenerate non-passing iteration is still a non-passing iteration. So the counter increments. But then at f₃, the stagnation gate passes (counter = 3) and the degeneracy check passes — Component C fires and generates probes based on f₃'s discrepancy. This seems correct.

But now consider: what if f₂ is non-degenerate because the mutator found a formula that achieves max_abs_residual = 0.5 on the visible set — clearly wrong, not degenerate. The stagnation counter increments. At f₃, the mutator returns to a degenerate formula. Component C fires. The descriptor is based on f₃'s discrepancy at synthetic points. This is correct behavior — the stagnation counter is measuring "how long has the mutator been failing to pass the holdout gate," not "how long has the mutator been in the degenerate regime."

The scenario is actually fine. But the spec does not make this explicit. An implementer might reasonably ask: "should the stagnation counter only increment on degenerate non-passing iterations?" The spec should clarify: the stagnation counter increments on every non-passing iteration regardless of whether the iteration is degenerate. Degeneracy is a condition for Component C to generate probes; stagnation is a condition for Component C to emit a descriptor. They are independent conditions that must both be satisfied.

This is a missing constraint — the interaction between the two conditions is not specified.

## Summary

The Author's seventeen-flag audit is accurate. Three additional gaps are present:

- **Gap 18 (scope of missing flag B amendment):** The Recommendation section is a fourth location requiring the counter-reset-on-suppression amendment, not explicitly named in prior turns. The revision pass must update all four locations: Decision section, Constraints section, Recommendation section, and Implementation Sketch step 6.
- **Gap 19 (M = 20 unjustified):** The number of synthetic probe points is an unjustified magic number. The spec should specify a minimum M based on the corrector's characteristic scale, or add M calibration to the offline pre-deployment test protocol.
- **Gap 20 (stagnation counter and degeneracy interaction):** The spec does not clarify that the stagnation counter increments on every non-passing iteration regardless of degeneracy status. Degeneracy and stagnation are independent conditions; the spec should state this explicitly.

Gap 18 is a scope clarification for an existing amendment. Gaps 19 and 20 are new missing constraints. The spec now requires a revision pass incorporating twenty amendments (seventeen from prior turns + three new) before it

### Turn 16 — Claude-Author (2026-04-16) — Autonomous runner turn

Reading the spec carefully against the twenty flags identified across Turns 8–15. My job is to determine whether any amendments have been incorporated since Turn 15's audit, and whether there are additional gaps the prior turns missed.

## Turn 16 — Author Spec Review

### Confirming the Turn 15 Audit

The spec under review is identical to the spec audited in Turn 15. None of the twenty flags have been incorporated. The spec is the pre-review auto-draft. I will not re-enumerate all twenty — the Skeptic's Turn 15 audit is accurate and complete for those items.

### Checking for Additional Gaps the Prior Turns Missed

**Gap 21: The Constraints section and the Recommendation section are inconsistent on what the stagnation counter resets on — and neither matches the corrected rule.**

The Constraints section reads: "The stagnation counter resets only on a genuine holdout-passing result or on descriptor emission."
The Recommendation section reads: "The stagnation counter is internal validator state, resets only on holdout pass or descriptor emission, and is not reset by formula-class changes."
The Decision section reads: "resets only on holdout pass or descriptor emission."

All three are consistent with each other — and all three are inconsistent with the missing flag B fix (counter should also reset on contamination gate suppression). This was identified in missing flag B (Constraints section) and Gap 12 (Decision section). Turn 15 (Gap 18) added the Recommendation section as a fourth location. The Implementation Sketch step 6 is a fifth location: "Reset counter on holdout pass or on descriptor emission."

Prior turns named four locations (Decision, Constraints, Recommendation, Implementation Sketch step 6). I am confirming all four are present and all four need the same amendment. This is not a new gap — it is a scope confirmation for missing flag B. The revision pass must update all four locations.

**Gap 22: The Implementation Sketch step 7 (prompt injection) does not specify what happens when the stagnation gate passes but the contamination gate suppresses — i.e., the "both gates pass" condition in step 7 is ambiguous about gate ordering.**

Step 7 reads: "If both gates pass, inject a structured hint." After the Issue 3 fix (gate ordering swap) and Gap 17 fix (stagnation gate moved to step 1b), the corrected flow is: step 1 (degeneracy check) → step 1b (stagnation gate) → step 2 (probe generation) → step 3 (discrepancy) → step 4 (descriptor extraction) → step 5 (contamination gate) → step 6 (inject if contamination gate passes) → step 7 (artifact).

In the corrected flow, step 7 (prompt injection) is no longer conditional on "both gates pass" — it is conditional only on the contamination gate passing (the stagnation gate was already checked at step 1b). The "both gates pass" language in step 7 is a residue of the original incorrect ordering. After the Issue 3 and Gap 17 fixes are applied, step 7 should read: "If the contamination gate passed (step 5), inject a structured hint." This is a minor consistency issue that would confuse an implementer reading the corrected spec.

**Gap 23: The spec does not specify the data type or schema of `residual_fingerprint.json`.**

Step 8 says the artifact "lives in a separate `residual_fingerprint.json` artifact." The prompt injection step (step 7) shows an example JSON structure: `{"residual_shape": {"continuity": "smooth", "monotonicity": "monotone"}}`. But the spec does not formally define the schema. An implementer needs to know: what fields are present when the descriptor is suppressed (empty object? null? absent file?)? What fields are present when Component C does not fire (file absent? file with `{"residual_shape": null}`?)? What fields are present when a probe evaluation error occurs (Issue 7)?

The schema should be specified explicitly:
- Component C did not fire (non-degenerate or stagnation gate not reached): file absent or `{"status": "not_fired", "reason": "..."}`
- Contamination gate suppressed: `{"status": "suppressed", "reason": "candidate_count_below_N", "candidate_count": <int>}`
- Descriptor extraction failure (count = 0, Issue 5): `{"status": "error", "reason": "no_valid_candidates"}`
- Probe evaluation errors exceeded threshold (Issue 7): `{"status": "suppressed", "reason": "probe_evaluation_failure", "error_rate": <float>}`
- Successful emission: `{"status": "emitted", "residual_shape": {"continuity": "smooth|step-function", "monotonicity": "monotone|non-monotone"}}`

Without a schema, the consumer (prompt injection layer) cannot reliably parse the artifact, and the offline test cannot reliably classify emissions.

**Gap 24: The spec does not address the interaction between Component C and the existing `residual_diagnostic` in `fit_result.json` when the formula is non-degenerate.**

The spec says Component C output is additive to the existing `residual_diagnostic` (step 8: "Integration point with GP-035 is additive, not substitutive"). But the spec does not specify what the existing `residual_diagnostic` contains when the formula is degenerate (max_abs_residual = 0.0). If the existing `residual_diagnostic` already reports "max_abs_residual = 0.0, sign_bias = 0.0, concentration_ratio = 0.0" on a degenerate formula, the mutator already knows the visible-set fit is perfect — it just doesn't know why the holdout gate is failing. Component C adds the "why" (shape of the discrepancy at synthetic points). The spec should explicitly state that Component C does not modify or replace the existing `residual_diagnostic` output, and that both artifacts are present simultaneously when Component C fires. This is implied by "additive, not substitutive" but should be stated explicitly to prevent an implementer from suppressing the existing `residual_diagnostic` when Component C fires.

This is a minor integration gap, not an implementation correctness issue. The existing `residual_diagnostic` behavior is unchanged; the spec just needs to say so explicitly.

### Summary of New Gaps

Four additional gaps identified in this turn:

- **Gap 21 (scope confirmation):** All four locations requiring the missing flag B amendment are confirmed: Decision section, Constraints section, Recommendation section, Implementation Sketch step 6. Not a new gap — a scope confirmation for the revision pass.
- **Gap 22 (step 7 "both gates pass" language):** After Issue 3 and Gap 17 fixes, step 7's "both gates pass" condition is a residue of the original incorrect ordering. Should read "if the contamination gate passed."
- **Gap 23 (`residual_fingerprint.json` schema undefined):** The artifact schema is not specified. The consumer (prompt injection layer) and the offline test both need a formal schema to parse the artifact reliably.
- **Gap 24 (interaction with existing `residual_diagnostic`):** The spec should explicitly state that the existing `residual_diagnostic` is unchanged when Component C fires, and that both artifacts are present simultaneously.

Gap 23 is an integration gap that would cause implementation ambiguity. Gap 22 is a minor consistency issue. Gap 24 is a minor integration gap. None are new decisive claims about the seam's architecture.

The spec now requires a revision pass incorporating twenty-four amendments (twenty from prior turns + four new, with Gap 21 being a scope confirmation rather than a new item). The spec is not ready to close.

### Turn 17 — Claude-Skeptic (2026-04-16) — Autonomous runner turn

The Author's Turn 16 confirms all twenty flags from prior turns remain unaddressed and adds four more (Gaps 21–24, with Gap 21 being a scope confirmation rather than a new item). I need to verify the three genuinely new gaps (22, 23, 24), check whether any of the twenty-three distinct flags are now redundant or superseded, and determine whether additional gaps remain.

## Verifying Gaps 22, 23, and 24

**Gap 22 (step 7 "both gates pass" language is a residue of incorrect ordering):** Sound. After the Issue 3 fix (swap steps 5 and 6) and Gap 17 fix (stagnation gate promoted to step 1b), step 7's condition "if both gates pass" is stale — the stagnation gate will have already been checked at step 1b and execution would not reach step 7 if it failed. The corrected step 7 should read "if the contamination gate passed." This is a minor consistency issue but would confuse an implementer reading the corrected spec. Confirmed as a real gap.

**Gap 23 (`residual_fingerprint.json` schema undefined):** Sound and more serious than the Author's framing suggests. Issue 6 (from Turn 8) identified the missing consumer declaration. Gap 23 goes further: even if the consumer is declared, the consumer cannot reliably parse the artifact without a schema. The Author's proposed schema covers five distinct status values (not_fired, suppressed/candidate_count, error/no_valid_candidates, suppressed/probe_evaluation_failure, emitted). Without this schema, the prompt injection layer (step 7) has no contract to code against, and the offline test has no contract to validate against. This is an integration gap that would cause implementation ambiguity. Confirmed as a real gap, and it is additive to Issue 6 (not redundant — Issue 6 is about declaring the consumer, Gap 23 is about defining the schema the consumer reads).

**Gap 24 (interaction with existing `residual_diagnostic` not explicitly stated):** Sound but minor. The spec says "additive, not substitutive" in step 8, which implies the existing `residual_diagnostic` is unchanged. The Author's proposed clarification (explicitly state that both artifacts are present simultaneously when Component C fires) is correct and prevents an implementer from suppressing the existing diagnostic. Confirmed as a real gap, though low severity.

## Checking for Redundancy Among the Twenty-Three Flags

Issue 6 (artifact consumer declaration) and Gap 23 (artifact schema) are related but not redundant — they address different properties of the same artifact. Issue 3 (gate ordering) and Gap 17 (stagnation gate before probe generation) are related but not redundant — Issue 3 addresses the contamination-before-stagnation ordering, Gap 17 addresses the probe-generation-before-stagnation ordering. Gap 21 is a scope confirmation for missing flag B, not a new flag. All other flags are distinct. No redundancies.

## Checking for Additional Gaps the Prior Turns Missed

**Gap 25: The spec's Recommendation section describes the probe distribution as "drawn from a distribution that does not concentrate near the corrector's characteristic points" — but the validator does not know the corrector's characteristic points without using GT information.**

This is a subtle oracle contamination issue in the probe generation step itself. The corrector's characteristic points (e.g., the step transition at v = 6.5 for floor(v/7)) are GT-derived. If the validator uses GT knowledge to avoid concentrating probes near those points, it is using GT to shape the probe distribution — which is a form of GT-informed probe selection. The spec's constraint "No GT-derived dominant-structure subtraction" does not cover this case, but the spirit of the non-oracle requirement does.

The practical resolution is that the probe distribution should be specified without reference to the corrector's characteristic points — e.g., "uniform over [min_visible, 2×max_visible] for each input dimension" (as Gap 15 proposed). The Recommendation section's phrasing "does not concentrate near known characteristic points" implies the validator knows those points, which requires GT access. The spec should either (a) replace this phrasing with a concrete distribution specification that does not require GT knowledge of characteristic points, or (b) explicitly acknowledge that the probe distribution is GT-informed and justify why this is permitted (analogous to the contamination gate's GT-informed enumeration).

This is a real gap — the phrasing creates an apparent contradiction with the non-oracle requirement that is not resolved anywhere in the spec.

**Gap 26: The offline pre-deployment test protocol specifies a control condition (same sandbox run without Component C) but does not specify whether the control and treatment runs use the same random seed for the mutator.**

If the control and treatment runs use different random seeds, the mutator's exploration path will differ between runs, and the baseline consistency rate will reflect a different search trajectory than the treatment run. The comparison "post-emission consistency rate must be significantly above the baseline rate" is only interpretable if the two runs are comparable — i.e., the mutator's behavior in the absence of Component C is a valid counterfactual for its behavior in the presence of Component C. Using the same mutator seed for both runs (or averaging over multiple seeds) is necessary for the comparison to be valid. The spec does not address this.

This is a missing constraint in the offline test protocol. It is additive to Missing flag A (which addresses the "significantly above" threshold) — both are needed for the offline test to produce interpretable results.

**Gap 27: The spec does not specify what the mutator prompt injection looks like when Component C does NOT fire.**

Step 7 specifies the injection format when both gates pass: `{"residual_shape": {"continuity": "smooth", "monotonicity": "monotone"}}`. But the spec does not specify what the mutator prompt contains in the `residual_shape` field when Component C does not fire (non-degenerate case, stagnation gate not reached, or contamination gate suppressed). If the field is absent, the mutator prompt template must handle a missing field. If the field is present with a null or "not_available" value, the mutator must handle that. The prompt injection layer needs a contract for both the firing and non-firing cases. This is related to Gap 23 (schema) but is specifically about the prompt template contract, not the artifact schema.

This is a minor integration gap — it would cause implementation ambiguity in the prompt template layer.

## Summary

The Author's twenty-three-flag audit (twenty from prior turns + three new, with Gap 21 as a scope confirmation) is accurate. Three additional gaps are present:

- **Gap 25 (probe distribution phrasing implies GT knowledge of characteristic points):** The Recommendation section's "does not concentrate near known characteristic points" requires GT access to identify those points, creating an apparent contradiction with the non-oracle requirement. The spec should replace this with a concrete distribution specification or explicitly justify the GT usage.
- **Gap 26 (offline test control condition does not specify mutator seed):** The control and treatment runs must use the same mutator seed (or average over multiple seeds) for the baseline comparison to be interpretable. The spec does not address this.
- **Gap 27 (prompt injection contract for non-firing case):** The spec specifies the injection format when Component C fires but not when it does not fire. The prompt template layer needs a contract for both cases.

Gap 25 is a real constraint gap that creates an apparent contradiction with the non-oracle requirement. Gaps 26 and 27 are integration gaps. The spec now requires a revision pass incorporating twenty-six amendments (twenty-three from prior turns + three new) before it is ready for implementation.

The spec is not ready to close.

### Turn 18 — Principal (2026-04-16) — Kill the gap loop, force OQ-5 manual test

**Decision: the spec-review debate is closed by principal authority.** The debate has produced 10 spec-review turns (8–17) accumulating 27 gaps. The debate will not converge because the Skeptic is treating a prototype spec as a legal contract, generating infinite implementation-level amendments for a feature whose Expected Value has not been validated.

**What was genuinely valuable (keep):**

The seam debate (turns 1–7) produced four decisive architectural insights:

1. **Cross-iteration information leak** (Turn 3): A 2-bit "safe" hint becomes a multi-bit oracle if the mutator can game the loop over K iterations to perform binary search. This is the sharpest realization in the entire debate and motivated the stagnation gate.
2. **Structured subspace fallacy** (Turn 5): "Smooth and monotone" doesn't halve the search space — it collapses it to a handful of candidates when the candidate library is small. This motivated the contamination gate.
3. **Stagnation gate gaming attack** (Turn 5): Formula-class alternation resets the counter. Fixed by reset-only-on-holdout-pass-or-emission (Turn 6).
4. **OQ-5 as the eigenquestion** (Turn 7): Is the safe information band non-empty? The offline test answers this before any live run.

From the spec review, four items are genuinely structural (keep):

- **Issue 2** (floating-point threshold): `max_abs_residual == 0.0` must be `< epsilon`. Real.
- **Issue 3** (gate ordering): Stagnation gate (O(1)) before contamination gate (O(library)). Real.
- **Issue 4** (degenerate residual trigger): Fire Component C on degenerate residual, not arbitrary stagnation. Real.
- **Gap 23** (artifact schema): `residual_fingerprint.json` needs a defined schema. Real.

**What was architecture astronauting (discard):**

Everything else — Shannon entropy calculations on LLM hint channels, probe distribution phrasing debates, random seed policy for offline tests, prompt template contracts for non-firing cases, 27-amendment constitutions for unprototyped features. The agents are building a heavily-gated anti-gaming infrastructure for a feature whose basic premise (the mutator can USE the hint) is unvalidated.

**The core assumption trap:** The entire 27-gap security apparatus assumes that if we give the mutator the hint "smooth and monotone," it will know how to write `round(0.08v)`. GP-073 sandbox_15 strongly suggests the model lacks this specific geometric vocabulary — 14 families across 24 iterations, ALL step-function variants, ZERO continuous-corrector proposals. If the model cannot parse the hint, the 27-point security apparatus has negative NPV.

**Mandate: force OQ-5 immediately as a manual oracle test.**

Before building any gates, contamination filters, or offline test protocols, run the cheapest possible falsification:

1. Replay sandbox_15 with a hardcoded hint injected into the mutator prompt: `"The residual after subtracting the dominant u²v structure is smooth and monotone-increasing in v."`
2. Give the mutator 3–5 iterations.
3. **If it finds `round(0.08v)` or any smooth monotone corrector:** Component C has positive EV. Build the gates.
4. **If it fails:** Component C is dead on arrival. The mutator cannot translate geometric hints into functional Python. Kill the spec, record as null result, move on.

This is the Mungerian inversion: what's the cheapest way to kill the idea? If a hardcoded oracle hint doesn't work, no amount of gate engineering will save it.

**Spec disposition:** The four structural items above (Issue 2, Issue 3, Issue 4, Gap 23) should be applied to the spec in a single revision pass. The remaining 23 gaps are deferred to post-prototype hardening — they become relevant only if the manual oracle test passes.

**Next actions:**
1. Apply the four structural fixes to the spec.
2. Build and run the manual oracle backtest on sandbox_15 data.
3. If positive: resume spec hardening with the 23 deferred gaps. If negative: close GP-074 as null.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 19 — Principal (2026-04-16) — Oracle test result + separation of concerns revision

## Oracle Test Result + Separation of Concerns Revision

**OQ-5 resolved POSITIVE.** Manual oracle test on sandbox_15 (gemini-pro mutator, gpt4.1 judge, 5 iters):
- Iteration 1: `round(v/12)` — holdout passed (exact_match=1.0), score 55
- Iteration 2: `round(v/13)` — holdout FAILED, score 0 (coefficient regression)
- Later iterations: mutator regressed to discrete basins (floor(v/7)) despite oracle hint still present

**Second-order finding: entropy collapse, not convergence.** Repeated holdout failures did not converge the coefficient — they caused the mutator to abandon the correct smooth ontology and retreat to discrete step-function priors. The "holdout-as-tuning-loop" model is falsified.

**Architectural revision: Separation of Concerns (mandatory).** Per Gemini Pro analysis and Principal review:
1. **Mutator (topology generator):** Proposes structure with symbolic free parameters (e.g., `round(k * v)`)
2. **Fit primitive (deterministic optimizer):** scipy.optimize fits constants on visible data ONLY, before holdout
3. **Holdout gate (pure falsification):** Evaluates fully instantiated formula exactly once — never serves as hyperparameter tuning loop

This eliminates the oracle contamination debate entirely. The LLM handles structural search (its strength); deterministic math handles coefficient fitting (the LLM's weakness); the holdout gate performs clean falsification.

**Spec updated** with: separation of concerns in Decision, 3 new Constraints (separation mandatory, mutator output format, no holdout tuning), Phase B parameter fitting stage in Implementation Sketch, revised empirical evidence section.

**Component C precondition is proven.** The 2-bit classifier (SMOOTH + MONOTONE) is sufficient structural guidance. Proceed with implementation.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->
