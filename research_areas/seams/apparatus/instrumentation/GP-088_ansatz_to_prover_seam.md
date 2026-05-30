# GP-081 — Peircean Pipeline: Abductive Discovery → Deductive Verification

> **Seam metadata** · `seam_id:` GP-088 · `track:` apparatus · `status:` `note` - opened 2026-04-17, conditional on precipitating fin · `last_updated:` 2026-05-08


**Status:** `note` — opened 2026-04-17, conditional on precipitating findings
**Parent artifact:** Paper 5 (Treatise), Chapter 3 — Peircean residual; GP-050 Track 3 (Peirce abduction shims)
**Related:** GP-050 Track 7 (Wittgenstein / language-game bias → formal-gate trigger), AlphaProof (DeepMind 2024, IMO conjecture→proof pipeline)

---

## The Claim

ZTARE's abductive output (a typed, provenance-annotated algebraic law that survives holdout gates) can serve as the Ansatz input to a formal theorem prover (Lean/Coq), converting an unbounded search problem (discover the theorem) into a bounded verification problem (prove the theorem). The pipeline is: **ZTARE finds the destination; the prover builds the road.**

This is not the general "ML conjecture → formal proof" pattern (AlphaProof already does that for competition math). The differentiator is ZTARE's **typed provenance chain**: Component D records which primitives were composed, which residual statistic triggered each composition step, and which holdout surface the result survived. This provenance gives the prover a richer starting point than a bare formula — it provides structural hints about *why* the formula works, not just *that* it works.

---

## What Needs to Happen Before This Seam Activates

Each condition is independent. Any one met → the seam moves from `note` to `active`.

1. **Component D produces a novel composition that survives holdout on a non-trivial substrate.** Without this, the pipeline has no input to pipe. GP-080 (tacrolimus) or a future OEIS run (Hofstadter Q, A002865 extension) would provide the precipitating finding.

2. **The typed provenance chain is machine-parseable.** Currently, Component D's output is a JSON blob with `primitives`, `command`, `residual_trigger` fields. To feed a prover, this needs to be compiled into a formal expression — at minimum, a symbolic expression tree that Lean's `norm_num` or `polyrith` tactics can consume. This is engineering work that does not yet exist.

3. **A proof-of-concept on a known-provable target.** Before claiming the pipeline works on open problems, run it on a sequence whose closed form is known but non-trivial (e.g., partition function asymptotics where Hardy-Ramanujan is the GT). If ZTARE rediscovers the form and Lean proves it, the pipeline is validated end-to-end. If ZTARE finds an equivalent form Lean *cannot* prove, that is also informative — it means the provenance chain is insufficient as a proof hint.

---

## What This Seam Does Not Claim

- It does not claim ZTARE generates proofs. ZTARE is Ramanujan; the prover is Hardy.
- It does not claim the proof will be straightforward given the formula. The gap between empirical truth and deductive proof is the gap between combinatorial and analytic universes — bridging it (circle method, modular forms, etc.) is where the mathematical difficulty lives.
- It does not claim the pipeline eliminates the asymptotic catastrophe. Only a successful proof does that. The pipeline *reduces* the catastrophe risk by making proof attempts tractable (bounded search), not by replacing them.
- It does not claim originality of the general pattern. AlphaProof (2024) established ML→prover pipelines. The specific claim is that ZTARE's typed provenance is a better proof hint than a bare formula.

---

## Inversion: How This Seam Fails

1. **Component D never produces anything worth proving.** If all Component D outputs are epicyclic ASTs that fit data but have no generative mechanism, the prover has nothing meaningful to verify. The pipeline degenerates into "prove that this polynomial interpolation holds," which is trivially true and scientifically empty.

2. **The provenance chain is noise, not signal.** If the residual statistics that trigger composition (e.g., `multiplicativity_ratio`) do not correspond to mathematical structure the prover can exploit, then the "richer starting point" claim is false and ZTARE's output is no better than a bare formula.

3. **The Lean integration cost exceeds the value.** Building a ZTARE→Lean compiler is real engineering. If the class of discoveries ZTARE makes is narrow enough that a human mathematician can prove them faster than the compiler can be built, the pipeline is a net negative.

---

## Debate Log

- 2026-04-17 — opened as `note` after Gemini Pro conversation surfaced the Peircean Pipeline as a decisive next step. Most of the Gemini content (ZTARE as abductive engine, Ramanujan analogy, asymptotic catastrophe) is already covered in Paper 5 Chapter 3 and the Three Legs / Cognitive Gym philosophy docs. The genuinely new claim is the typed-provenance-as-proof-hint differentiator and the three activation conditions above. Conditional opening: seam activates when any of the three conditions is met, not before.

<!-- FINDINGS_DEBATE: note -->
