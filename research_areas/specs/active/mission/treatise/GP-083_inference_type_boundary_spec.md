# GP-083 Inference Type Boundary — Spec

## Status

Active

## Scope

- Validate the "automated Kepler" claim across a second domain (Planck spectrum, GP-023)
- Add underdetermination and degenerating-programme language to the boundary claim
- Downgrade Bridge 2 from "theorem proving" to "ODE-class tagging (deferred)"
- Defer Bridge 3 with explicit failure criterion

Does not cover:

- Building Bridge 2 (ODE-class recognition) — deferred until an automated pipeline needs it
- Building Bridge 3 (cross-domain unification) — research programme, not engineering task
- Theorem prover integration (Lean/Coq/Isabelle) — category error per Turn 2 debate
- Grammar extensions — if needed for GP-023, that is a result, not a prerequisite
- String Theory substrate — no grammar, gate, or data exist (appendix only)

## Decision

The seam's central claim — "the engine automates Kepler" — is currently grounded on one substrate (GP-080, bi-exponential PK). Four independent domain reviews (Philosophy of Science, Munger Multidisciplinary, Symbolic Regression, Systems ML) converged on a single next action: run the crucial experiment. The spec is: validate Bridge 1 cross-domain with explicit Lakatosian pass/fail criteria.

Bridge 2 is downgraded from theorem proving to ODE-class tagging, deferred until a concrete automated pipeline needs it. Bridge 3 is honestly deferred as a research programme. The degenerating-programme failure criterion is defined so the boundary is falsifiable.

## The Crucial Experiment

**Substrate:** GP-023 Planck black-body spectrum.

**Condition:** Same grammar, same gate configuration, same rubric persona as GP-080. No grammar extensions, no new operators, no substrate-specific accommodations.

**Pass/fail criteria (Lakatosian):**

| Outcome | Classification | Implication |
|---------|---------------|-------------|
| Same grammar recovers Planck form | Progressive programme | "Automated Kepler" earned cross-domain. Same machinery, novel prediction. |
| Grammar extension needed, then succeeds | Lakatosian grey zone | Record precisely what was added. Was the addition predicted by the prior failure mode, or ad hoc? |
| Fails without grammar extension | Scope-limited | Downgrade to "Kepler-for-PK." Grammar is a domain-specific auxiliary, not a general-purpose discovery engine. |
| Fails even with grammar extension | Falsified | The bi-exponential PK recovery was a lucky hit, not a capability. |

**Preconditions:**
1. GP-080 Stage 2 (noisy substrate) completes — confirms abduction survives noise
2. GP-023 sandbox_07 results reviewed — baseline for grammar coverage
3. If sandbox_07 already found the Planck form: check whether grammar was modified. If so, the experiment is already in the grey zone.

## Constraints

1. **No grammar modification for the crucial experiment.** The whole point is testing whether the existing grammar generalizes. Modifying it is running a different experiment.
2. **Same gate harness type.** RMSE threshold may differ (Planck values are on a different scale) but the gate structure must be identical.
3. **GP-072 Division A/B protocol.** Substrate construction uses information isolation. No GT form in the charter.
4. **Explicit recording of any failure.** If the engine fails on Planck, the failure mode must be diagnosed: grammar starvation, noise sensitivity, dimensional mismatch, or something novel. The failure mode IS the finding.

## Degenerating-Programme Failure Criterion

**The test:** If 3+ substrates each require grammar extension to succeed, the "automated Kepler" claim downgrades to "domain-specific curve fitting with an LLM frontend."

**Why this matters:** A programme that adds auxiliary hypotheses for each new domain is degenerating (Lakatos). The engine's value proposition is general-purpose abductive compression. If it needs bespoke vocabulary per domain, the generality claim fails.

## Bridge 2: Downgraded

Original proposal: feed engine output to Lean/Coq as proof goal.

Four-domain review finding (3/4 convergence):
- Systems ML: axiom set selection IS the oracle contamination — the decisive bits are in the axiom choice, not the proof
- Munger: man-with-a-hammer — recommending formal verification because that's what proof people reach for
- Munger (inverted): deductive verification can introduce false negatives — correct formulas rejected when axiom set is incomplete
- Systems ML: the proof's information content is zero — it confirms logical consistency, adds no new knowledge

**Downgraded to:** ODE-class tagging via SymPy lookup. If `exp(-kt)` is recovered, tag it as solution to `dy/dt = -ky`. This is a convenience feature for automated pipelines, not a capability upgrade. Build when a pipeline needs it. Estimated effort: one afternoon.

**Inversion (Turn 4):** What fails if we DON'T build ODE-class tagging? Nothing. Domain scientists already know what `exp(-kt)` means. The tag adds routing metadata for automation, not explanatory power.

## Bridge 3: Honestly Deferred

Cross-domain unification (Kepler → Newton) is a research programme.

Turn 2 findings:
- Munger: "automated unification produces taxonomies, not theories"
- SR: "clustering by tree topology is a weekend project, not Newton"
- Systems ML: "substrate selection channel leaks the answer"

No spec. No timeline. No roadmap. The seam is a boundary to respect, not a roadmap to build.

## Underdetermination Acknowledgment

What the engine recovers is the simplest law consistent with evidence and holdout — the simplest survivor, not necessarily the true generating process (Duhem-Quine). The grammar's topology acts as an implicit Kolmogorov complexity prior. This must be stated in any publication claiming "law recovery."

## Cross-References

- GP-080: Stage 1 result (bi-exponential PK, score 98) — the single current empirical anchor
- GP-080 Stage 2: Noisy substrate — does abduction survive noise?
- GP-023: Planck substrate — the crucial experiment target
- GP-081: Peircean Pipeline — conditional on Component D, subsumed by Bridge 2 downgrade
- GP-082: Substrate Scope Boundary — complementary seam on where abduction works/breaks
- Paper 5: Chapter 3 §3.1 — claims the engine performs abduction, must not overclaim

## Debate Provenance

Spec drafted from GP-083 seam Turns 1-5. Four independent domain reviews (Turn 2) reached convergence (Turn 5) on: run the crucial experiment, downgrade Bridge 2, defer Bridge 3, define the failure criterion. No dissent on the compression: "Kepler is sufficient. More substrates through Bridge 1."
