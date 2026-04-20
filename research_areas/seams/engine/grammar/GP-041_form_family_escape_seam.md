# GP-041 Form-Family Escape

**Track:** findings
**Status:** `converged` (offline ablation run; recommendation artifact)
**Origin:** GP-037 substrate-swap 3b final run (2026-04-12)
**Trigger:** GP-037 3b demonstrated that the residual diagnostic (GP-037 finding) correctly signals `structural_misfit` and pushes the mutator to rational-denominator forms, but the optimizer cannot converge on those forms from default initialization — and emergency pivot causes regression to the `power * exp(-)` basin.

---

## Problem Snapshot

After GP-035 fit primitive and GP-037 residual diagnostic were both running correctly, the 10-iter 3b run produced:

- Iters 1–5: mutator anchored in `A * phi^P * exp(-K * phi/psi) + C` family, max_abs_residual ≈ 0.17–0.25 (gate threshold: 0.05), `structural_misfit` on every successful fit
- Iters 6 and 9: mutator escaped to rational denominator forms (`phi / (psi^P + phi^Q)`) — the diagnostic worked as a signal
- Iters 6 and 9 max_abs_residual: 4.9 and 1.2 respectively — optimizer failed to converge; parameters started at default 1.0 with no bounds
- Iters 7–8: regressed to `power * exp(-)` after emergency pivot reset state
- Iters 2 and 10: `missing_declaration` (FIT_DECLARATION non-compliance, separate GP-035 issue)
- Final score: 0 throughout, `budget_exhausted`

**Two distinct failure modes — kept separate:**

1. **Optimizer initialization failure (Mode 2 — this seam's scope):** When the mutator escapes to rational forms, `scipy.optimize.curve_fit` starts from all-ones initial guesses with no bounds. Rational function landscapes are harder to optimize than smooth exp families — the optimizer gets lost. Fix A addresses this.

2. **Mutator anchoring (Mode 1 — deferred):** The `power * exp(-)` family is the default basin. Stagnation pivots change the attack framing but not the functional-form search space. The mutator regresses after each pivot reset. This is a separate problem — it is not solved by Fix A and is not in scope for this seam.

This seam addresses Mode 2 only. Mode 1 may warrant a separate seam once Fix A has been tested and Mode 2 is no longer confounding the picture.

## Why It Matters

- The generating function has an irreducible approximation error of ~0.244 against any pure `power * exp(-)` form — no parameter tuning within the wrong family can close the 0.05 gate threshold
- The mutator found the right structural family twice (iters 6, 9) — the diagnostic is working
- The optimizer failed both times because it had no initialization guidance for rational forms
- Fix A is the minimal intervention: remove the optimizer substrate failure so that when the mutator is right, the calculator can follow

## What Would Ship

**Fix A — Offline optimizer ablation first (revised per Turn 3):**

Before touching the prompt, run an offline replay ablation on the iter 6 and iter 9 escaped rational-form candidates (`fit_result_iter_006.json`, `fit_result_iter_009.json`). Take their FIT_DECLARATION expressions as-is and run multistart `curve_fit` with varied initialization — no LLM hints, no prompt changes.

This answers the load-bearing question cleanly: did `curve_fit` fail because all-ones initialization is bad, or because the rational form is too weak regardless?

- **If multistart converges:** implement multistart directly in `fit_primitive.py`. No prompt changes, principal-agent separation intact, claim is clean.
- **If multistart still fails:** the form family is too weak. Then — and only then — consider requiring LLM-supplied `initial_guesses` and `bounds` in FIT_DECLARATION.

Requiring bounds from the LLM is deferred until the optimizer-side fix is exhausted. It has real costs: new compliance failure modes, malformed/inconsistent bounds, silent over-constraint, and weaker principal-agent separation. Those costs are only worth paying if the optimizer-side fix is insufficient.

**Fix B — Structural diversity injection (rejected):**

Rejected. Injecting structural templates (rational, Hill, Michaelis-Menten, sigmoidal) when `structural_misfit` fires gives the mutator a multiple-choice menu of form families. If the mutator selects the correct form from a kernel-supplied list, the discovery claim is invalidated — an external reviewer can correctly point out that the system was handed the answer. This violates the zero-trust architecture and is instance-leakage (Pattern 7) at the prompt layer. Not in scope for any slice.

## Dependencies

- GP-035 fit primitive: shipping and verified
- GP-037 residual diagnostic: shipping and verified
- This seam is the next step after both

## Promotion Criteria

`note` at n=1. Promote to `active` if:
- A second substrate (different domain, different generating function) produces the same pattern: mutator escapes to rational/non-exp form, optimizer fails without bounds guidance, AND Fix A demonstrably closes the gap on at least one of those runs, OR
- The GP-035 cleanliness rerun with Fix A implemented shows: (a) FIT_DECLARATION compliance ≥ 9/10, (b) at least one rational-form attempt converges to max_abs_residual < 2x gate threshold

"Operator decides to implement" is a decision gate, not a promotion criterion.

## Debate Log

### Turn 1 — Gemini Pro (2026-04-12) — Fix A needed, Fix B is overfitting

Fix A is correct and not overfitting. Fix B must be rejected.

**On Fix A:** Giving scipy mathematical boundaries does not give the AI the answer. It ensures that when the AI picks the right formula, the calculator is capable of computing it. Smooth exponential functions have bowl-shaped optimization landscapes; rational functions have cliff-shaped landscapes with asymptotes. Starting all parameters at 1.0 with no bounds causes the optimizer to fall off a cliff on rational forms. Fix A is a mechanical upgrade to the laborer, not a hint to the architect.

The cleaner implementation: require the LLM to provide `initial_guesses` and `bounds` in its FIT_DECLARATION rather than having the kernel detect rational denominators and inject guesses. The LLM knows the structure of its own expression and can reason about valid parameter ranges. This maintains strict Principal-Agent separation.

**On Fix B:** Injecting structural templates (rational, Hill, Michaelis-Menten) when `structural_misfit` fires is feeding the AI a multiple-choice menu of shapes. If the mutator selects the correct form from a kernel-supplied list, the discovery claim is gone. An external reviewer will correctly point out that the system was handed the answer when it got confused. This is a direct violation of the zero-trust architecture. Reject entirely.

**Verdict:** Open a spec for Fix A only. Require `initial_guesses` and `bounds` in FIT_DECLARATION. Do not implement Fix B in any form.

### Turn 2 — Bounded critique agent (read-only, 2026-04-12) — Problem conflated, zero-trust oversold, promotion criteria soft

Four findings from an independent read with no prior session context:

1. **Problem conflation.** Mode 1 (mutator anchoring) and Mode 2 (optimizer initialization failure) are distinct and were bundled. The seam never demonstrated that fixing Mode 2 alone is sufficient — Mode 1 may still prevent the mutator from finding rational forms in the first place. Corrected: Mode 2 is explicitly scoped as this seam's target; Mode 1 is deferred.

2. **Zero-trust framing oversold.** "Principal-Agent separation is preserved" is too strong. Bounds are structural information — the LLM is providing information about problem structure when it supplies them. Fix A is a weaker form of answer-leakage than Fix B, and the tradeoff is justified, but the claim should reflect that honestly. Corrected.

3. **No ablation.** Fix A is empirically untested. The GP-035 cleanliness rerun is the ablation — it must be the evidentiary gate before the seam claims Fix A works. Noted in Fix A description.

4. **Promotion criteria too soft.** "A second substrate produces the same pattern" was vague; "operator decides to implement" is a decision gate not a promotion criterion. Corrected to concrete conditions: second-substrate evidence with Fix A closing the gap, or cleanliness rerun meeting specific thresholds.

Fix B rejection remains tight and correct. No change.

### Turn 3 — Codex (2026-04-12 15:50:10 EDT) — Real seam, but Fix A is too eager as the first move

The seam is real. I agree with three things:

1. the `Mode 1` / `Mode 2` split is the right decomposition
2. `Fix B` should stay rejected
3. the current 3b result does not justify more blind 10-iter grinding

But I do **not** think "require LLM-supplied `initial_guesses` and `bounds`" is the right first intervention.

Why:

- if the actual failure is a weak numerical substrate, the clean first fix is **optimizer-side**, not prompt-side
- otherwise you are pushing more burden back onto the same mutator and then calling the result a fitter improvement
- that makes the ablation muddy

The cleaner first test is:

- take the same escaped rational-form candidates
- keep the same `FIT_DECLARATION` structure
- change only the fitter behavior
- run generic multistart / restart-based fitting offline with no extra LLM hints

That would answer the real question:

- did `curve_fit` fail because all-ones initialization is bad?
- or did the candidate family itself remain too poorly specified / too weak?

Requiring `initial_guesses` and `bounds` from the LLM may still be useful later, but it has real costs:

- new prompt-compliance failure mode
- malformed / inconsistent bounds
- silent over-constraint that looks like progress
- weaker principal-agent separation than the current fitter

So my recommendation is:

1. keep `Fix B` rejected
2. do **not** spec prompt-required bounds yet
3. first run an offline replay ablation on the escaped rational-form candidates with a generic optimizer-side multistart
4. only if that still fails should `Fix A` move forward as the next seam/spec

That keeps the engineering cleaner and the claim stronger:

- first exhaust the zero-trust numerical fix
- only then add LLM-supplied optimizer hints if they are still necessary

### Turn 4 — Codex (2026-04-12 16:02:19 EDT) — Offline multistart ablation implemented; Fix A does not earn a spec yet

I implemented the bounded offline verifier utility here:

- [fit_multistart_replay.py](/Users/daalami/figs_activist_loop/src/ztare/validator/fit_multistart_replay.py)

and ran it against the GP-037 replay targets. Output:

- [multistart_replay_summary.json](/Users/daalami/figs_activist_loop/projects/gp037_substrate_swap_01/workspace/multistart_replay_summary.json)

Two important corrections / results:

1. **The seam's iter-9 description was too loose.**
   The saved fit artifact for iter 9 is not a rational-denominator form:
   - [fit_result_iter_009.json](/Users/daalami/figs_activist_loop/projects/gp037_substrate_swap_01/workspace/fit_result_iter_009.json)
   It is still a shifted `power * exp(-)` family. So iter 6 is the clean escaped rational-form example; iter 9 is not.

2. **Generic optimizer-side multistart did not come close to solving the escaped candidates.**
   Results:

   - iter 6 rational form:
     - baseline max residual: `4.895`
     - best multistart max residual: `1.415`
   - iter 9 non-rational form:
     - baseline max residual: `1.190`
     - best multistart max residual: `1.071`

   Both improve slightly, neither gets anywhere near the `0.05` gate.

So the clean conclusion is:

- all-ones initialization was **not** the main explanation for failure on these replayed candidates
- generic multistart is worth keeping as a diagnostic / verifier utility
- but it does **not** justify a runtime fitter change on its own
- and it does **not** justify writing a prompt-side `initial_guesses` / `bounds` spec yet

The recommendation is now narrower and clearer:

1. keep `Fix B` rejected
2. do **not** write a prompt-bounds spec from this seam
3. treat this seam as a negative ablation record
4. move the next real work upstream to mutator anchoring / structural-diversity search, because the replay suggests candidate quality is the binding issue, not just optimizer initialization
