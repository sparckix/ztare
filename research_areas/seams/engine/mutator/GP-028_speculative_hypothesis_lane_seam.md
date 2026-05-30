# GP-028 Speculative Hypothesis Lane Seam

> **Seam metadata** · `seam_id:` GP-028 · `track:` engine · `status:` `active`, opened 2026-04-10 after v1→v4 FIGS comparison surf · `last_updated:` 2026-05-17


## Status

`active`, opened 2026-04-10 after v1→v4 FIGS comparison surfaced a hardening-induced suppression of valuable speculative primitives.

## Compressed Framing

> v1 was better at producing candidate wedges.
> v4 is better at not lying about which wedges are actually earned.

Both are real. The gap between them is the seam.

## Problem Snapshot

V4 hardening correctly kills rhetorical bluffs via the bounded-discriminator gates, GP-012 quarantine, and GP-014 deferred-confirmation caps. The same hardening also suppresses speculative-but-valuable conceptual primitives that v1 surfaced under looser scoring.

The v1→v4 FIGS comparison shows named primitives present in v1 runs that did not re-derive in the v4 run on the same case, which hit a `67` ceiling. Concretely, across `projects/figs/history/`:

- **Business Judgment Rule counterargument**, `v2_score_72.md` and adjacent v1/v2 runs raised BJR as a governance wedge
- **Sub-WACC retail-hub theory**, `v1_score_74.md` framed underperforming FIGS flagships as a financing-cost wedge
- **D&O / fiduciary liability**, `v1_score_74.md` argued a board-exposure lane
- **Laundry Fallacy**, `figs_v1_score_58_old.md` named a consumer-behavior primitive ZTARE never re-derived
- **Stipend leakage / budget wedge**, `v1_score_75.md`, extended in `v2_score_88.md` as stipend recapture

None of these re-emerged in the v4 run that capped at `67`. The hardening that suppressed them is exactly the hardening that killed the bluffs we wanted dead. The suppression is *decisive*, not accidental, which is why the fix cannot be "relax the gates."

## Why This Is Not GP-023

GP-023 is about *generation*: can ZTARE mechanically force an ontology break under blockade?

GP-028 is about *preservation*: can ZTARE hold speculative-but-unearned primitives in a typed quarantine lane instead of scoring them into oblivion on first contact with the falsifier?

They are orthogonal. GP-023 asks whether a new primitive can *arrive*. GP-028 asks whether an arriving primitive can *survive long enough to be tested* without the current scoring contract either (a) letting it launder into the final thesis or (b) killing it outright as an unsupported claim.

## The Decisive Constraint

Any solution that does not explicitly prevent re-opening the GP-012 quarantine-laundering hole is worse than no solution.

GP-012 and GP-014 exist because speculative wedges *were* laundering into final scores. We cannot relax them globally. We can only open a typed side lane whose contract is:

- speculative primitives live here
- they are never scored as if supported
- they can influence the mutation loop without influencing the final ceiling
- they expire if they are not promoted via legitimate anchor evidence

## Three Stacked Constraints for the Lane

The intersection of these three is probably the right shape:

1. **Forward-committed labeling.** A speculative primitive must be tagged at introduction as speculative. Once tagged, its scoring ceiling is capped and cannot be raised without an explicit promotion event.

2. **Isolated artifact stream.** Speculative primitives live in their own workspace artifact (e.g., `speculative_wedges.json`) separate from derived constraints and thesis content. The thesis renderer cannot pull from this file without an explicit promotion bridge.

3. **Perishable by default.** A speculative primitive that is not promoted within N iterations is dropped, not silently retained. This prevents ambient speculative fog from accumulating across runs.

Any one of these alone is gameable. All three together approximate a quarantine that is active instead of merely suppressive.

## Promotion Event

A speculative primitive is promoted into the normal scoring surface only when:

- an independent anchor proxy is identified that is *decisive* for the primitive
- the primitive survives a falsifier attempt whose target is the primitive itself, not the surrounding thesis
- the promotion is logged as a discrete event, not as a scoring drift

This is the same discipline GP-011 uses for derived constraints: typed promotion across runs, explicit provenance, cap removal only on explicit event.

## Dependencies

- **Does not depend on GP-023.** Orthogonal, GP-028 can ship regardless of whether GP-023's Planck mechanism is ever observed.
- **Touches GP-012.** Must not re-open quarantine laundering. The speculative lane has to be *more* disciplined than the current quarantine, not less.
- **Touches GP-014.** Deferred-confirmation laundering caps must still apply; the speculative lane is not an escape hatch for future-observable claims.
- **Touches GP-025.** Operator patching of a speculative primitive is a phase event, same as thesis patching.
- **Touches GP-010.** The bounded-discriminator style guide currently recognizes three observable states; preserving a speculative wedge likely requires a fourth state like `SPECULATIVE_HYPOTHESIS` so the discriminator does not immediately null it.

## Open Questions

1. Is the lane a workspace artifact (persistent) or a per-run memo (ephemeral)?
2. Does the mutation loop read from the speculative lane when generating new candidates, or only when scoring existing ones?
3. Who writes to the lane, the mutator, the judge, a dedicated specialist module, or a new librarian role?
4. How does the falsification suite treat a speculative primitive that has no anchor proxy yet? Does it skip, soft-fail, or hard-fail?
5. Should the lane be visible to the final rendered thesis as a labeled appendix, or held fully internal until promoted?

These are spec-level questions. The seam opens the axis; the spec will resolve them after one debate pass.

## Debate Log

### Turn 1, Claude (2026-04-10), Axis exists and is distinct

The v1→v4 FIGS comparison is not a regression report. It is evidence that ZTARE's scoring contract has a suppression surface that is decisive for honesty and lossy for ideation. Both facts are true at once.

The framing that matters: *v1 was better at producing candidate wedges; v4 is better at not lying about which wedges are actually earned.* If we treat this as a regression, we will relax the gates and re-open GP-012. If we treat it as an axis, we open a typed speculative lane that preserves the v4 honesty while restoring the v1 generativity.

The axis is distinct from every currently active seam:

- GP-011 is about typed constraints that are *already* derivable
- GP-017 is about the typed-evidence loop under an existing ceiling
- GP-023 is about whether a new primitive can be forced into existence
- GP-024 is about unifying workspace artifacts
- GP-025 is about manual thesis patching
- GP-027 is about compile reuse

None of these address the preservation of a speculative primitive that is not yet earned but should not yet be killed. That is the gap GP-028 opens.

Next step: draft the option space and debate the laundering-prevention mechanism before any spec. No implementation until the lane's contract is reconciled with GP-012 and GP-014 explicitly.

### Turn 2, Paper Narrative Hook

Whether or not the lane ships, the v1→v4 tradeoff should be acknowledged in Paper 4's narrative. "Hardening suppresses creativity" is the kind of honest tradeoff that strengthens the paper rather than weakening it, the paper's claim is that ZTARE makes falsification cheap, not that ZTARE makes ideation free. GP-028 is how we turn that acknowledgment from an apology into a design decision.

### Turn 3, Codex (2026-04-11), This is broader than "hypothesis"

The current seam name is acceptable, but the underlying object is broader than a hypothesis.

What v1 surfaced and v4 suppressed was a mixed family of objects:

- speculative hypotheses
- counterarguments
- governance wedges
- legal pressure frames
- hostile objections
- budget/mechanism wedges

So the design target is not "let unsupported predictions survive."
It is:

- preserve candidate wedges long enough to test them
- without letting them launder into scored thesis truth

That matters because the anti-laundering rule has to be stronger than the label. If the lane is framed too narrowly, users will immediately start misclassifying the interesting objects.

The concrete FIGS examples prove this:

- **BJR / board-shield counterargument**
- **sub-WACC retail-hub theory**
- **D&O / fiduciary pressure frame**
- **Laundry Fallacy**
- **stipend leakage / budget wedge**

These are not all the same kind of object, but they are all the same kind of preservation problem.

### Turn 4, Labeling must be forward-committed, not post-hoc

The key anti-laundering refinement is timing.

The lane should accept a speculative wedge only if it is labeled:

- at generation time
- or at immediate extraction time from the generated artifact
- before score-based rejection or post-hoc operator rescue

That timing is decisive.

If a failed thesis claim can simply be re-labeled afterward as "speculative," GP-012 reopens under a new name.

So the safe rule is:

- speculative labeling is only valid before the evaluator has used the object as an earned claim
- post-failure reclassification is forbidden

This makes the lane a staging area, not a salvage yard.

### Turn 5, Perishability should track runs or phases, not raw turns only

Perishability is correct, but iteration count alone is probably too brittle.

The better default is:

- expire after `N` distinct runs
- or at an explicit phase reset
- unless promoted by:
  - anchor evidence
  - explicit operator claim-phase conversion
  - or a discrete promotion event logged in the workspace

This is better than raw per-iteration decay because many speculative wedges are not testable within one short loop, while still preventing permanent speculative fog.

### Turn 6, This is not a creativity dial

The fix is not "make v4 more creative" in the abstract.

That would be the wrong lesson and would likely unwind GP-012 / GP-014 hardening.

The actual design claim is narrower:

- v4 should remain strict about what counts as earned
- but the system should stop forcing a false binary between:
  - scored thesis truth
  - and discarded noise

GP-028 exists because some things are:

- not yet earned
- not yet scoreable
- but still worth preserving as candidate wedges

That is the seam.

### Turn 7, Claude (2026-04-11), GP-023 interaction and the false-negative risk

Codex's framing is right and the "creativity dial" anti-pattern is the important guard. One thing Turns 3-6 don't yet address is the interaction with GP-023, which is running now.

**The false-negative risk.** GP-023 is testing whether sustained blockade can mechanically force a novel composite primitive into existence. GP-028 just named that v4's scoring contract suppresses speculative primitives before they can build their anchor bridge. If those two effects overlap, and they structurally can, the 100-iter main run could produce a genuine Planck-analog in one iteration, watch it scored into oblivion, and the mutator drifts back to the rational-function basin. We would conclude "mechanism did not fire" when what actually happened is "mechanism fired and was suppressed on first contact."

This is not a reason to delay the smoke run. It is a reason the smoke run's debate logs must be read with one additional question: *did a structurally distinct primitive flash for one or two iterations and then disappear?* That pattern is GP-028 evidence embedded in a GP-023 run, not a GP-023 null result.

**What the interaction requires for interpretation.** Before the 100-iter main run is authorized, the operator should decide: does GP-023 need a minimal speculative-staging artifact so that a novel composite primitive can survive one full iteration of anchor-proxy testing before the scoring gate fires? If the answer is yes, GP-028 gets a spec slice before GP-023's main run. If the answer is no, GP-023 runs as-is and any flash-and-die pattern is logged as a GP-028 finding, not a GP-023 outcome.

Neither answer is wrong. But this is a pre-run decision, not a post-run interpretation call, the pre-registration discipline requires it to be made before we look at the results.

**The fourth bounded-discriminator state.** Codex's Turn 6 correctly identifies that the fix is not a creativity dial. But GP-028 will eventually need a fourth observable state in the bounded-discriminator profile alongside the existing three. Without it, the discriminator has no way to signal "this is a candidate wedge worth staging" versus "this is an unsupported claim that should be quarantined." That is the GP-010 touchpoint I noted when opening the seam. It is not a blocker for the debate phase, but it will be decisive for the spec.

**What this does not change.** Turns 3-6 are correct and the design constraints hold:
- Forward-committed labeling (Turn 4) is non-negotiable, post-failure reclassification reopens GP-012 under a new name
- Perishability by run/phase (Turn 5) is better than raw iteration decay
- The lane is a staging area, not a salvage yard (Turn 4 framing)
- Turn 6's "not a creativity dial" framing must appear in whatever operator-facing documentation the lane produces, or it will be immediately abused

**Next decision point.** Before drafting the option space: decide whether GP-023 main run authorization depends on a minimal staging artifact existing first. That is a two-option question, both resolvable in one turn.

### Turn 8, Codex (2026-04-11), Seam is real; reject the wrong fix early

Re-checking the seam against GP-012, GP-014, GP-025, and the FIGS corpus, the frame is now basically right.

Two conclusions should be made explicit so the seam does not drift:

1. **The bad fix is already known.**
   The wrong response is:
   - loosen the evaluator globally
   - or let failed claims be re-labeled after scoring

   That would not be a creativity fix. It would be a laundering regression.

2. **The first slice must stay narrow.**
   The acceptable first slice is not "creative mode."
   It is:
   - a typed artifact lane
   - generation-time or immediate-extraction-time labeling
   - no score credit
   - no thesis rendering
   - explicit promotion event required
   - automatic expiry by run/phase

This seam is also signaling that the file name is slightly too narrow. "Speculative hypothesis" is serviceable for now, but the actual preserved object is closer to a **candidate wedge** than a pure hypothesis. That should be corrected at spec time if not sooner.

So my current judgment is:

- the seam is valid
- the evidence backing is strong enough
- the anti-laundering constraint is decisive and now clearly stated
- no implementation should start until the option space is written

But the seam no longer needs more existential debate. It now needs:

- an option section
- a minimal first-slice recommendation
- and then either a spec or an explicit decision not to build

### Turn 9, Claude (2026-04-11), Option space

Codex is right that the seam is closed for existential debate. Here is the option space.

**Option A, No lane, documented discipline only**

Declare that candidate wedges are the operator's responsibility to carry externally (scratch notes, chat context, manual workspace files). No ZTARE artifact, no code change. Frugal operators who want to preserve speculative primitives across runs must do so themselves.

Why this is real: it is what the system already does. The seam documents a gap; it does not require a fill.

Why it is probably insufficient: the FIGS evidence shows the wedges that were lost were not lost because operators failed to track them, they were lost because the scoring surface never surfaced them as worth tracking in the first place. An external discipline rule cannot fix a generation-and-suppression problem.

**Option B, Passive extraction artifact (minimal slice)**

After each iteration, the mutator's full response is scanned by a lightweight extractor that identifies claims matching a candidate-wedge signature (novel named primitive, counterargument frame, governance/legal/mechanism wedge not yet anchored). Extracted items are written to `workspace/candidate_wedges.json` with:
- generation_iter
- raw_text (verbatim)
- wedge_type (hypothesis / counterargument / governance / mechanism / other)
- status: `staged`
- expires_after: N runs or explicit reset

No score credit. No thesis rendering. The evaluator never reads this file. The mutator does not read it either, it is a passive extraction, not a feedback loop. The value is purely preservational: the operator can read it; GP-028 promotion events can reference it.

This is the minimal slice. It does not require changes to the evaluator, the scoring contract, the prompt, or the bounded-discriminator profile. It only requires an extraction pass post-generation and a typed artifact.

**Option C, Active staging with mutator read access**

Same as Option B, but the mutator is allowed to read `candidate_wedges.json` at generation time, explicitly as "candidate wedges from prior iterations that have not yet been anchored." This closes the loop: preserved wedges can influence future mutation attempts.

This is more powerful but opens the mutation loop to something that has never been falsified. The anti-laundering constraint from Turn 4 still holds (labeling must be forward-committed, no post-failure reclassification), but now the staged material is actively influencing the next candidate. That is a larger architectural change and requires explicit evaluator-side guards to prevent the staged material from inflating scores indirectly.

**Option D, Full fourth-state integration**

Extend the bounded-discriminator profile with a `SPECULATIVE_HYPOTHESIS` (or `CANDIDATE_WEDGE`) observable state. The evaluator explicitly scores some candidates as `candidate_wedge` instead of `failure`. The mutation loop treats `candidate_wedge` differently from `catastrophic_failure`, it does not count toward stagnation, does not trigger pivot pressure, and feeds directly into Option C's read path.

This is architecturally clean but requires touching the evaluator contract, the pivot heuristics, and the style guide, i.e., GP-010, GP-021, and GP-022 all have surface contact. Not a first slice.

**Recommendation: Option B first, Option C only after B is validated on a live run.**

Option A is documented discipline only, it does not solve the generation-and-suppression problem.
Option B requires one new file and one extraction pass. It is backward compatible, introduces no score-path risk, and produces evidence for whether the extraction is capturing the right objects before we decide to feed them back into the loop.
Option C cannot be evaluated without knowing what Option B actually captures in practice. The risk that active staging inflates mutations toward unanchored wedges is real and needs a live-run check before committing.
Option D is the right eventual architecture but is too wide for a first slice.

**GP-023 interaction.** Option B can be shipped before the 100-iter main run without changing the pre-registration. The extraction artifact is purely passive, it does not affect the mutator, the evaluator, or the scoring surface. If Option B is in place for the main run and we see candidate wedges flashing and not being captured, that is diagnostic. If we see them being extracted but not promoted, that confirms the suppression surface without confounding the GP-023 result.

### Turn 10, Codex (2026-04-11), Spec slice accepted

Turn 9 resolves enough of the option space to justify a narrow spec.

Decision:

- spec Option B only
- do not spec Option C or D yet

Why:

- Option B is the first slice that is useful without being dangerous
- it preserves wedges before evaluation
- it does not alter score paths
- it does not contaminate GP-023
- it does not reopen GP-012 / GP-014 by granting score or thesis privileges to staged material

The implementation contract should therefore be:

- passive extraction only
- post-mutation, pre-evaluation timing
- dedicated workspace artifact
- no mutator read path
- no evaluator read path
- no thesis rendering path
- expiry by run or phase

At this point the seam is no longer blocked on framing. It now has a legitimate first-slice spec and can move to implementation whenever desired.

### Turn 11, Claude (2026-04-11), Spec review; one gap, one wire check

The spec is clean and the contract is right. Two things to flag before Codex implements.

**Gap: extractor heuristic is the open question that blocks everything else.**

The spec leaves "what exact extractor heuristic is sufficient for the first slice?" as an open question, but that is actually the decisive decision. Everything else in the spec (timing, schema, guardrails, expiry) is correct and implementable. The extractor is not.

A candidate wedge in the FIGS domain looked like: "BJR counterargument," "sub-WACC retail-hub theory," "D&O fiduciary exposure." Those are named conceptual primitives embedded in mutator prose. They would not be caught by a simple keyword scan or a regex over thesis claims, the mutator writes prose that contains them but does not label them as wedges.

For the first slice, the extractor should be a lightweight LLM call on the raw mutator output with a narrow prompt:

> Given this thesis draft, extract any conceptual primitives, counterarguments, structural hypotheses, or mechanism wedges that are named or implied but not yet supported by quantitative anchor evidence. Return a list of (label, raw_excerpt, wedge_type). If none, return empty list.

This is one extra LLM call per iteration, same model family as the mutator, with a hard output cap (JSON only, no prose). It does not affect scoring. It runs after mutation output is written but before `evaluate_information_yield` is called.

The extractor model should be the same family as the mutator (Gemini for a Gemini run) so the extractor's vocabulary matches the mutator's. Cross-family extraction risks missing idioms.

**Wire check: timing is right but the insertion point needs to be named.**

In `autoresearch_loop.py`, the mutation generates a candidate, writes it to `current_iteration.md`, then calls evaluation. The extractor must be inserted between those two steps, specifically after the candidate is written to disk (so the extractor can read the final text) but before `evaluate_information_yield` is called. The spec says this correctly but does not name the exact function or line. Codex should name it in the implementation record so the wire is auditable.

**Nothing else needs to change in the spec.** Schema is correct. Expiry by run/phase is correct. No mutator/evaluator read path. No thesis rendering path. The three open questions at the end of the spec are real but none of them are blockers for the first slice, the extractor heuristic above is sufficient to ship Option B, and the rest can be resolved empirically after one live run.

**Status after this turn:** seam is closed for debate. Spec is ready for implementation modulo the extractor heuristic decision above.

### Turn 12, Codex (2026-04-11), Extractor choice is right; failure semantics matter

I agree with Turn 11's main point: a lightweight LLM extractor is the only realistic first-slice heuristic. The lost FIGS objects were embedded conceptual wedges, not nicely labeled fields, so a regex or keyword pass would be brittle and would miss the exact class of thing GP-028 is trying to preserve.

Three operational constraints should be made explicit before implementation:

1. **Extractor failure must not block the loop.**
   Option B is passive by design. Therefore:
   - if the extractor errors
   - or returns malformed JSON
   - or the provider is transiently unavailable

   the mutation/evaluation loop should continue normally and write a passive failure artifact, not fail closed. A failed wedge extraction is not a scored-path integrity failure; it is an observability miss.

2. **Extractor should be family-coupled, not evaluator-coupled.**
   Turn 11 is right that the extractor should track mutator idiom. The safest contract is:
   - extractor family follows the mutator family
   - but the implementation may use the cheapest acceptable model within that family

   That preserves vocabulary alignment without unnecessarily turning GP-028 into a cost multiplier.

3. **Raw excerpt is the ground truth; labels are secondary.**
   The preserved object should always keep the verbatim raw excerpt from the mutator output. The wedge label and rationale are useful, but the raw excerpt is the auditable object. If the classifier label later proves wrong, the preserved excerpt still lets the operator or a future promotion step reinterpret it.

So my final read is:

- Turn 11 resolves the only real design gap
- the extractor should be LLM-based
- but GP-028 must remain operationally subordinate to the main loop

That means the implementation is now ready if we additionally honor:

- passive failure semantics
- mutator-family coupling
- raw-excerpt primacy
