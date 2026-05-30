# GP-134 — Apparatus-layer prompt contamination incident

> **Seam metadata** · `seam_id:` GP-134 · `track:` apparatus · `status:` Closed (2026-04-23). Cleanup shipped; CI audit pending. · `last_updated:` 2026-05-08


**Status:** Closed (2026-04-23). Cleanup shipped; CI audit pending.
**Opened:** 2026-04-23 (same day as incident).
**Parent:** GP-134 (ztare_on_ztare / discrete algebraic substrate work).
**Related:** GP-096 (science programme decomposition), GP-133 (multidisciplinary panel).

---

## Summary

A substrate-specific mutator prompt section contained an explicit worked example that matched the blinded substrate's target law verbatim. The mutator (o3) reproduced the example in iteration 1 with zero residual. This was briefly celebrated as a one-iteration cold recovery before principal-led audit exposed it as prompt-layer contamination.

Two follow-on findings emerged from post-incident blind-reader audits:

1. Cleanup of the worked examples is necessary but not sufficient. The primitive names themselves — in particular `factorint(n) -> {prime: multiplicity}` — remain sufficient to let a cold cross-family reader identify the target at ≥95% confidence on this substrate.
2. Charter-layer contamination audits do not cover apparatus-layer prompt sections. The author had run charter audits and cleared them; the leak was in `autoresearch_loop.py`, not `project_charter.md`.

---

## Timeline

- Morning: substrate-specific primitives (isprime, factorint, primefactors, divisors, gcd, prime_vector, is_coprime) added to the py_exec sandbox to support discrete arithmetic substrates.
- Same morning: the py_exec mutator prompt section was extended with an "ascending multiplicity ladder" of five worked examples including `sum(p*v for p,v in factorint(n).items())`. The example was labeled "sum of prime factors weighted by multiplicity"; the target law on the active blinded substrate is this exact expression.
- Afternoon: switched mutator model to a reasoning-class model. Iteration 1 returned the ladder example verbatim with max residual 0.0.
- Afternoon: principal flagged as contamination and cancelled the run. Full debrief.
- Cleanup: examples stripped; primitive names retained.
- Post-cleanup blind-reader audit: still HOT. Primitive availability plus evidence pattern is sufficient on this substrate class.

---

## Root cause analysis

**Intermediate cause.** A Tier-5 contamination example ("full worked expression with concrete operators") was placed in the live mutator prompt under the rationalization "teaching the primitives, not the answer." That rationalization does not hold for any substrate where a concrete example happens to coincide with the target law.

**Structural cause.** Two disciplines were coupled that should be separated:

- "Make primitives usable by a non-reasoning mutator" — a pedagogy concern.
- "Preserve blinded-recovery protocol on the current substrate" — a protocol concern.

These drifted into the same file (apparatus-level prompt). Any concrete composition example serves the first and violates the second if the example matches any current or future substrate's target. The contamination continuum argument (external panel Q1) applies: there is no stable middle ground at Tier 3-5 as long as a common apparatus prompt is shared across substrates with different targets.

**Procedural cause.** The charter-layer contamination audit (blind reader given charter + evidence) ran and passed. The apparatus-layer prompt was not in the audit's read set. Apparatus-layer leaks therefore cannot be caught by charter audits alone; a dedicated prompt-layer audit is required.

---

## Decisions logged

1. **Tier-2 ceiling on live mutator prompts.** Primitive names with signatures and one-line semantic glosses are the hard upper bound for live-prompt primitive documentation. Concrete composition examples (Tier 3-5) are forbidden in prompts that run against blinded substrates.
2. **Primitive availability is substrate-specific contamination.** Adding a substrate-aligned primitive (e.g., `factorint` for arithmetic-function substrates) is structurally a hint. Runs using such primitives must be classified as primitive-assisted recovery (Path B), not cold recovery (Path A). The track record entry wording must reflect this distinction at the time the run is logged, not retroactively.
3. **Composition teaching moves to pre-run calibration on retired substrates.** Workforce-style primitive orientation belongs in one-time warm-up runs whose target corpora are never reused for live recovery claims.
4. **CI audit to be added.** A prompt-layer leak audit as a make-target pre-flight gate, using a cold cross-family auditor against the fully-built mutator prompt plus the substrate evidence, comparing top-k guesses against the sealed target via the existing AST-canonicalization proxy signature. Fails on top-1 signature match, top-3 subexpression AST overlap ≥70%, or auditor self-reported confidence ≥0.6. Specification at `docs/concepts/prompt_leak_audit_spec.md` (to be authored).

---

## What did not fail

- The charter-layer audit correctly cleared the charter. No charter-layer leak was introduced by this incident.
- The gate harness, once executed, would have correctly scored the fit. The contamination was in the proposal-space upstream, not in the verification-space downstream.
- Pivot heuristics and DAG steering are unaffected — the incident was about what the mutator was told, not how its proposals were scored after the fact.
- The discovery-class taxonomy correctly classifies this run as `recognition` rather than `synthesis`. Had it been promoted to a claim, the taxonomy would have flagged it.

---

## What this incident is evidence for

- The external OpenAI-family reviewer's reframe (2026-04-23 same day) is strengthened: single-substrate runs are being asked to carry three burdens simultaneously (cage-forces-abduction, engine-recovers-structure, result-is-genuine-science). The response to apparent under-performance in one burden was to help the engine across another, contaminating the first. The blur is the failure mode; separating the burdens via a meta-law family program is the response.
- The two-ceiling framework in the Experimental Mathematics letter (grammar ceiling + space ceiling) is unchanged as a finding. It was written before this run and is about why the engine was stuck, not what appeared to unstick it.
- The incident is evidence for the architectural decision to prefer pre-registered cross-substrate invariant claims over single-substrate recovery claims going forward. A family-level prediction is harder to contaminate; the contamination would have to apply uniformly across the family, which is harder to accidentally author than a single-substrate hint.

---

## Follow-ups

- [ ] Author `docs/concepts/prompt_leak_audit_spec.md` per external panel Q2.
- [ ] Ship `src/ztare/gates/prompt_leak_audit.py` implementing the spec. Wire as `make audit-prompt` pre-flight gate.
- [ ] Decide per-substrate: remove primitives (Path A, likely null) or rename to primitive-assisted (Path B). Log decision at run-start, not retroactively.
- [ ] Add this incident to the Experimental Mathematics letter's Limitations section as a disclosed methodology failure (transparent record of what was learned during the programme).
- [ ] Add to Paper 5's Limitations / Methodology section per the same principle.
- [ ] Retire the contaminated gp090 iter-1 run from any "recovery" framing. Log as a primitive-availability datapoint only.

---

## Meta

This seam exists because the incident is informative about the apparatus's failure modes even though it produced no publishable result on the substrate itself. The decomposition's Principle I (separation of generation from verification) was not violated by the apparatus; it was violated by the author at apparatus-construction time. That is a narrower and more specific failure than "the apparatus leaks," and it belongs on the record.
