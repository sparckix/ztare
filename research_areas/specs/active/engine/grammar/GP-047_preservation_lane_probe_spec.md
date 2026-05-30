# GP-047 Preservation Lane Probe Spec

## Status

Active

## Scope

- defines a new search-mode mechanism for ZTARE: the **preservation lane**, an alternative to (or augmentation of) the GP-045 cold-residual successor mode
- defines when preservation lane fires, how it mutates, what the diversity floor is, and when it falls back to cold-residual
- defines empirical acceptance criteria (what sandbox_04 must show for this mechanism to be considered effective)
- cross-references the GP-028 speculative hypothesis lane spec and the GP-023 ontology-trap seam as motivating context

Does not cover:

- the GP-035 fit primitive itself (covered in GP-035 spec)
- the FIT_DECLARATION drought fix under sustained emergency_pivot (scoped separately as a companion hardening turn; see Open Questions)
- any change to deterministic gate semantics
- any change to the Ontology Trap charter contract

## Decision

Adopt a rubric-opt-in **preservation lane** search mode that fires when structural memory reports `K` consecutive score-ceiling hits at the identical failing gate. In preservation lane the mutator is required to propose a **minimal structural edit** to the held champion: either (a) an *additive* delta that introduces a new primitive as a new term, or (b) a *single-term replacement* where exactly one term of the champion is replaced by a term containing a primitive the champion lacks. All other terms of the champion are preserved with tight parameter bounds. This broader contract exists because the motivating sandbox_03 basin is provably outside the reach of pure-additive composition (the true generator is a denominator family; the champion is a multiplicative-exponential family; no additive delta can close the gap). A two-stage diversity floor (pre-fit primitive-set check + post-fit **farther-tail contribution check**) and a hard stop rule (budget `M`, lane-exhaustion cap `L`) keep preservation lane as a narrow exception that expires, with cold-residual as the default state the loop returns to.

All numerical defaults (`K = 3`, `M = 5`, `L = 3`, thresholds in the diversity floor) are `draft_default_n1` — tuned against one run (sandbox_03 iters 13/20/26) and required to be re-tuned against at least two additional problems before they graduate from draft to stable.

Adoption is gated on sandbox_04, a three-arm experiment (control = cold-residual only, treatment = cold-residual + preservation lane, mutator-swap = stronger mutator with no preservation lane). Arm B must produce basin escapes Arm A does not, those escapes must survive the GP-046 B-slice holdout, and — pre-committed — if Arm C escapes while Arm B does not, preservation lane is withdrawn regardless of efficiency arguments. If any pre-declared failure mode fires, preservation lane is withdrawn. Sandbox_04 cannot launch until (a) the FIT_DECLARATION drought fix from GP-023 seam Turn 29 is designed and landed as a blocking prerequisite, and (b) a fresh farther-tail holdout is authored (the sandbox_03 B-slice is a one-shot oracle and has already been consumed).

## Problem

Cold-residual successor mode (GP-045) enforces structural diversity by requiring each new iteration to differ from prior residuals. In practice this produces healthy exploration when the search space is flat, but when the search reaches a sticky basin — a close-but-wrong structural family — cold-residual keeps rewriting the form while the underlying family stays the same. The empirical anchor is GP-023 sandbox_03 iters 13, 20, 26: three score-50 hits, same single failing gate (`farther_tail_global_residual` ≈ 0.0233 vs 0.01 threshold), spaced 7 and 6 iters apart. The loop is oscillating inside one basin; cold-residual can reach the basin but cannot leave it.

Two distinct search-mode failures are entangled here:

1. **Full-rewrite inefficiency.** Cold-residual treats each iter as a blank slate, discarding the partial information already encoded in the held champion. If the champion is 90% right, the loop pays the full cost of re-deriving the 90% every iter.
2. **Grammar lock-in.** The mutator's implicit grammar stays constant across iters (multiplicative-exponential with additive floor, in the sandbox_03 case). Cold-residual does not expand grammar; it only shuffles within it.

### Why "additive only" is not enough

A naïve preservation lane might force *additive* deltas only (`I_new = I_champion + delta`). That framing fails on the motivating sandbox_03 example. The sandbox_03 champion's family is `A·ψ^pA · φ^n · exp(-k·ψ^pk · φ^m) + floor·ψ^pf`. The hidden generator's family is Planck-like: `φ^p / (exp((αφ/βψ)^q) - 1) + offset`. The denominator with subtracted-one is not a term you can *add* to the champion — it is a structural feature that has to *replace* the exponential-decay term the champion is already using to describe the same geometry. Pure-additive preservation lane is incommensurable with its own motivating example.

The spec therefore defines a broader contract: **minimal structural edit**, meaning either an additive delta *or* exactly one single-term replacement that introduces a new primitive family. Both forms preserve the majority of the champion and keep its fitted parameters as tight-bounded initial guesses. The "minimal" qualifier is decisive — the edit is small, local, and privileges continuity — but the edit is not restricted to addition, because that restriction would make the mechanism non-applicable to the only problem it has been designed against.

Preservation lane (in this broader sense) addresses failure #1 directly and attacks failure #2 obliquely. By holding the champion and allowing only one local edit, the mutator is biased toward minimal structural changes rather than re-deriving a full form from scratch — which is how denominator-type or rational structures can enter the search, either by addition (when that suffices) or by surgical substitution of the term whose geometry they are meant to correct.

## Why It Matters

ZTARE's Compress leg (asymptotic survival / GP-046 farther-tail holdout) is working — GP-023 sandbox_03 iter 13 is the first live empirical anchor. But the apparatus caught a candidate it could not *then* improve on. Catching is necessary; unsticking is what makes the system useful for the author of the search, not just the reviewer of the result.

Without a preservation lane, ZTARE's current posture is: *"I will refuse to promote finite-window surrogates, but I cannot help you find the right form when you are close."* That is a fair epistemic posture but an unfair tool posture. Preservation lane is the ergonomics fix that keeps the refusal honest while giving the search a path out.

This also connects to GP-028 (speculative hypothesis lane): both specs share the architectural move of *holding more state between iterations* rather than re-deriving from scratch each time. If both ship, the lanes together define a richer search-mode vocabulary than the current "emergency_pivot / stagnation_pivot / normal" triple.

### Identity with the deferred tunneling mechanism

Preservation lane is the same mechanism that was raised as **quantum tunneling** during the GP-028/029 exploratory-mode probe and deferred at the time. That probe evaluated several candidates for escaping sticky basins:

- **Jaccard similarity** as the diversity metric for cold-residual successor — adopted, and is the current GP-045 slice-1 implementation
- **Embedding-based similarity** — deferred pending embedding infrastructure
- **Simulated annealing** — rebutted on the grounds that *softening the verifier* is the wrong move (the gate harness is the decisive surface and must stay strict)
- **Quantum tunneling** — rebutted as a directly-implemented mechanism, explicitly in favor of the preservation lane concept that this spec now formalizes

The name change from "tunneling" to "preservation lane" is deliberate. Tunneling is a physics metaphor that invited the wrong intuition (random jumps across the basin wall); preservation lane names what the mechanism actually does (hold the champion, mutate additively). The underlying design goal — escape a sticky basin without softening the verifier — is the same, and this spec is the debt payment on that deferred decision.

The deferred-tunneling probe originally assumed preservation lane would share GP-045's jaccard metric with a different anchor (held champion rather than residual set). The revised spec drops that assumption — jaccard on math tokens is too brittle for the finer-grained "is this a non-trivial edit to this specific form" question preservation lane must answer. See Diversity floor for the replacement (AST symbolic edit distance plus judge topological distinctness). GP-045's residual-set jaccard stays as-is; the two modes use different metrics on different anchors and do not share infrastructure.

## Relationship to the Invert Leg

Preservation lane is in genuine tension with the "always invert / the void" discipline from the Three Legs. This section names that tension explicitly so the spec does not paper over it.

**The Compress-leg view (no conflict).** Cold-residual successor mode and preservation lane both sit *upstream* of the gate harness. The GP-046 B-slice — the farther-tail holdout — is the arbiter in both modes. Preservation lane does not touch what decides pass/fail; it only changes what the mutator is asked to propose. From the Compress leg's standpoint, the two modes are orthogonal.

**The Invert-leg view (real tension).** The "always invert" insight was stronger than just gate discipline. It was: *the mutator must start from nothing, with no assumed form, and derive under falsification pressure*. Cold-residual enforces this by refusing continuity across iters. Preservation lane explicitly *breaks* continuity-refusal — it injects the held champion back into the prompt. That is a softening of the void, and pretending otherwise would be dishonest.

**Principled vs opportunistic softening.** The tension is acceptable only if the softening is principled (a narrow override that fires after the void has already been given its chance) and not opportunistic (preservation lane becomes the default under mild stagnation and the void erodes iter by iter). Three design constraints keep it principled, and this spec treats them as non-negotiable:

1. **Strict trigger.** Preservation lane fires only after cold-residual has demonstrably converged on a basin it cannot escape. `K = 3` consecutive identical-gate ceiling hits is the floor; `K = 2` is not acceptable. The void must have had its shot before preservation is offered.
2. **Hard stop rule that actually fires.** `M` preservation-lane iters without improvement must return control to cold-residual. Preservation is an exception that must expire; the void is the default state the loop returns to, not a state the loop leaves behind.
3. **B-slice untouched.** GP-046 farther-tail holdout is never visible to preservation lane. The champion being held is defined by *visible-side score* only. The B-slice remains the Compress-leg referee across both modes.

**Default posture.** Cold-residual is the default; preservation lane is rubric-opt-in and fires only under the strict trigger. Any rubric that does not explicitly set `preservation_lane_mode: true` runs the stricter invert-discipline baseline. This is enforced at the rubric layer, not at the runtime layer, so the default cannot be flipped accidentally.

**Falsification for the softening itself.** If sandbox_04 shows preservation lane producing score-ceiling escapes *without* the B-slice distinguishing the escapes from finite-window surrogates, preservation lane has become a retreat from the void rather than a principled override and should be withdrawn. The pre-declared failure mode in Open Questions must include this case.

## Constraints

- must not contaminate active runs: any new search mode must be rubric-gated, off by default, and must not alter the behavior of existing rubrics that do not opt in
- must preserve the GP-046 farther-tail holdout contract: preservation lane may not see the hidden B-slice
- must preserve the Ontology Trap charter discipline: the held champion is a form, not an answer — preservation does not freeze parameters, only structure-under-addition
- must define a *diversity floor* so that preservation does not collapse into trivial ε-perturbations of the held champion
- must define a *stop rule* so that preservation does not deepen a basin indefinitely — the lane must be willing to give up and hand control back to cold-residual
- must be compatible with the GP-035 fit primitive: additive deltas must flow through `FIT_DECLARATION` as new parameters, not as hardcoded values
- must not require changes to deterministic gates or judge contracts
- must not require changes to structural memory semantics (though it may *read* structural memory to decide when to fire)
- apparatus changes must survive emergency_pivot prompt pressure (see GP-023 seam Turn 29 FIT_DECLARATION drought — same failure class)

## Options

### Option A — Cold-residual only (status quo)

**Description.** Leave GP-045 cold-residual successor mode as the sole diversity mechanism. Accept that sticky basins produce repeated identical-gate failures and rely on the pre-registration discipline to make the oscillation itself the finding.

**Pros.**
- zero new apparatus surface
- preserves the cleanest possible Compress-leg demonstration (catch without help)
- no risk of introducing a new search-mode bug mid-program

**Cons.**
- loses the ergonomic value of the engine for the author
- wastes compute on redundant basin revisits
- makes the apparatus look brittle to external reviewers who will ask "why couldn't you climb out?"
- does not address grammar lock-in at all

**Verdict.** Null option. Not selected, because sandbox_03 iters 0–28 (GP-023 seam Turn 29) provide live evidence that cold-residual alone oscillates inside a sticky basin without escaping it. The case for moving off this option is empirical, not theoretical, and is the motivation for the rest of the spec. Retained as a sandbox_04 control arm (Arm A) so that Option B's value is measured against it.

### Option B — Preservation lane as a new search mode (recommended direction)

**Description.** Add a new search mode that fires when structural memory reports N consecutive score-ceiling hits with the identical failing gate. In preservation lane the mutator prompt changes: the held champion's form is injected verbatim, and the mutator is instructed to propose *additive* deltas (new terms, new compositional pieces) rather than rewriting the form. Diversity floor enforces that the delta is non-trivial. Stop rule returns control to cold-residual after M preservation-lane iters without improvement.

**Pros.**
- attacks both full-rewrite inefficiency and grammar lock-in
- preserves Compress-leg discipline (the B-slice still decides pass/fail)
- composable with GP-045 and GP-035 without replacing either
- produces a falsifiable claim: "preservation lane escapes the sandbox_03 basin" is testable in sandbox_04

**Cons.**
- new apparatus surface to harden
- additive-only bias could trap the search in a different way (adding terms to a fundamentally wrong form)
- diversity floor definition is non-trivial: what counts as "non-trivial additive delta" is fuzzy at the edges
- stop rule tuning risks false-abandonment or false-persistence

**Verdict.** Tentative recommendation. Needs diversity-floor and stop-rule detail before it can be finalized.

### Option C — Stronger mutator instead

**Description.** Don't add a new search mode; instead swap the mutator model (e.g., Gemini-flash → Gemini-pro or Claude) while keeping the rest of the apparatus unchanged. The hypothesis is that basin stickiness is a model-capability issue, not an apparatus issue.

**Pros.**
- zero new apparatus surface
- cleanly tests whether the bottleneck is search-mode or model vocabulary
- trivial to run as a sandbox_04 A/B against Option A
- if it works, it obviates Option B

**Cons.**
- masks the apparatus question rather than answering it
- if it works, we still don't know whether preservation lane would *also* help
- if it doesn't work, we've spent sandbox_04 budget on a null and still need Option B
- conflates two questions in one experiment

**Verdict.** Not mutually exclusive with Option B. Best used as a *baseline* arm in sandbox_04, not as an alternative to the spec.

### Option D — Preservation lane as a mode of GP-028 rather than a new spec

**Description.** Fold preservation lane into the existing GP-028 speculative hypothesis lane spec. Treat it as a variant of speculative lane where the speculation is "the current champion's form is 90% right" rather than "this unrelated speculation might work".

**Pros.**
- fewer specs
- leverages existing GP-028 machinery

**Cons.**
- GP-028 is about exploring *away* from the current champion; preservation lane is about exploring *from* it — opposite polarity
- conflates two mechanisms with different triggers and different stop rules
- makes the debate log harder to read

**Verdict.** Not recommended. Separate specs; cross-reference explicitly.

## Recommendation

**Adopt Option B (preservation lane) as a new rubric-opt-in search mode, with Option C (mutator swap) running as a parallel Arm C in sandbox_04 to disambiguate mechanism-vs-model.**

Sandbox_04 ships as a three-arm experiment: Arm A (control, matches sandbox_03 discipline), Arm B (treatment, preservation lane on flash), Arm C (mutator swap, stronger model on unchanged apparatus). Preservation lane is adopted as a default-available mode *only* if the primary acceptance criteria in the Sandbox_04 section are all satisfied, with particular emphasis on criterion #2 (escapes must survive the B-slice). If any pre-declared failure mode fires, preservation lane is withdrawn and the spec moves to `specs/archive/` with a Closure section documenting the failed experiment.

The Decision section at the top of this spec should be updated to reflect this recommendation when the spec is next reviewed.

**Non-negotiable prerequisites before sandbox_04 can launch:**

1. **FIT_DECLARATION drought fix lands first.** The GP-023 seam Turn 29 observation (iters 22–25 missed block, iter 27 missed block under sustained emergency_pivot) is a blocking prerequisite for this spec. Preservation lane intensifies prompt-attention pressure and will make the drought worse, not better. The fix ships as a separate hardening turn on GP-035 before sandbox_04 launches. This is tracked in Open Questions and is not optional.
2. **Jaccard infrastructure from GP-045 is extended to tag anchor mode.** Structural memory must distinguish `anchor_mode: "residual_set"` (cold-residual) from `anchor_mode: "held_champion"` (preservation lane) before the two modes can run in the same process without accounting drift. Small patch, lands with this spec.
3. **Rubric parser accepts `preservation_lane_mode: true | false`.** Default false, enforced at the rubric layer so no historical rubric is retroactively affected.

**What this spec does not claim:**

- It does not claim preservation lane will escape the sandbox_03 basin. That is a falsifiable empirical question sandbox_04 is designed to answer.
- It does not claim preservation lane generalizes beyond the sandbox_03 problem class. Generalization requires at least one additional rubric and is out of scope.
- It does not claim preservation lane replaces cold-residual. Cold-residual remains the default; preservation lane is a narrow opt-in override.
- It does not claim the mechanism is the same as GP-028 speculative lane. They have opposite polarity (explore *from* the champion vs explore *away* from it) and separate triggers, stop rules, and acceptance criteria.

**Decision reversal conditions.** If any of the four pre-declared failure modes from the Sandbox_04 section fires, this spec is moved to `specs/archive/` with a Closure section. If Arm A matches Arm B on escape rate, preservation lane is withdrawn even if Arm B technically satisfies the primary criteria — the mechanism has to *add* value, not match the baseline. Matching is not enough to justify the softening of the void.

## Implementation Sketch

### Trigger condition

Preservation lane fires when structural memory reports:

- `K` consecutive score-ceiling hits (score == previous champion score, not strictly greater)
- AND all `K` hits fail the *identical* single gate
- AND the current loop_control_action is `stagnation_pivot` or `emergency_pivot`

`K` is a rubric parameter. Default `K = 3` (`draft_default_n1`, matching the sandbox_03 iter-13/20/26 pattern; required to be re-tuned against at least two additional problems before graduating from draft).

### Preservation rule (mutator prompt contract)

When preservation lane fires, the mutator prompt is modified in four ways:

1. **Injected champion form.** A new section `HELD CHAMPION FORM (PRESERVATION LANE)` is inserted immediately after the `FALSIFICATION TARGET` section and before the `GATE FAILURE CONTEXT`. It contains:
   - the held champion's symbolic form, verbatim, as it appeared in the iteration that set the score ceiling
   - the fitted parameter values from that iteration
   - the single failing gate id and its actual-vs-threshold numbers
   - the `phi, psi` geometry of the residual (where the failure is worst in the relevant domain)
   - an explicit decomposition of the champion into its additive terms, each labeled `T1`, `T2`, ... so the mutator can reference them unambiguously

2. **Minimal-edit instruction.** A new section `PRESERVATION LANE CONTRACT` is appended after `GATE FAILURE CONTEXT` and contains the contract, verbatim:
   > "You are in preservation lane. The held champion is structurally close to the correct form but fails a single gate. Your task is not to propose a new form; it is to propose a **minimal structural edit** to the held form. You may choose exactly one of two edit modes:
   >
   > **Mode ADD.** Append a new additive term: `I_new(phi, psi) = I_champion(phi, psi) + delta(phi, psi)`. All champion terms are preserved exactly. The delta term must introduce at least one mathematical primitive not present in the champion.
   >
   > **Mode REPLACE.** Replace exactly one of the labeled champion terms (`T1`, `T2`, ...) with a new term: `I_new(phi, psi) = (I_champion - T_k) + T_k_new(phi, psi)`. All other champion terms are preserved exactly. The replacement term `T_k_new` must introduce at least one mathematical primitive not present in the original `T_k`. You must name which `T_k` you are replacing and justify the choice by identifying what geometric feature of the residual motivates replacing that specific term.
   >
   > In both modes: the preserved terms keep their fitted parameter values as initial guesses under tight bounds. The new term's parameters are new with loose bounds. You must provide a one-sentence justification that references the specific geometry of the failing gate: what shape is the residual, and how does your edit bend toward it? You may not use both modes at once and you may not edit more than one term."

3. **FIT_DECLARATION contract extension.** The `FIT_DECLARATION` block in preservation-lane mode must contain a new top-level field `preservation_mode: "add" | "replace"` and parameter entries tagged as either `"role": "preserved"`, `"role": "delta"` (ADD mode), or `"role": "replacement"` (REPLACE mode). Preserved parameters carry the fitted values from the champion as initial guesses and are constrained to `±10%` bounds around those values. New parameters are initial-guess-only with loose bounds from the mutator. This lets the fit primitive privilege continuity on the preserved side while allowing the new term to move.

4. **Trailing reminder re-anchored.** The existing trailing `FIT_DECLARATION` reminder line (currently at `autoresearch_loop.py:1646-1653`) is insufficient under the prompt-attention pressure preservation lane will intensify. The preservation-lane prompt places the contract as a *bracketed section* with both opening and closing delimiters, and the pre-submission validator (see FIT_DECLARATION drought fix, blocking prerequisite in Constraints) enforces both the block's presence and the `preservation_mode` tag on fit-declaration parse. A missed block triggers a single re-prompt; a second miss falls preservation lane back to cold-residual for that iter. The re-prompt is understood to be a weak signal (see Open Questions — empirically, re-prompts often produce cosmetic rather than structural changes) and is a fallback, not a primary mechanism.

### Diversity floor

The diversity floor is checked in **two stages** — a structural check on the proposed edit (before fit) and a geometric check on the fitted result (after fit). The metric is **AST-based symbolic edit distance**, not token jaccard. Jaccard on math tokens is brittle (`x^2 + y^2` and `x^2 - y^2` have near-identical token multisets but encode opposite geometries) and is not used here. GP-045's cold-residual jaccard usage on *residual-set* novelty is a different question and stays as-is; preservation lane does not share that metric.

**Stage 1 — structural edit check (cheap, pre-fit, re-prompt on fail):**

- Parse the champion and the proposed new form into ASTs. The primitive vocabulary is deliberately structural, not domain-named: `{power, exp_pos, exp_neg, log, trig, rational_simple, rational_with_additive_offset, sigmoid, polynomial, constant}`. No physics names appear in the apparatus. `rational_with_additive_offset` covers forms where the denominator contains an additive offset (e.g., `1/(f(x) + c)` or `1/(f(x) - c)`); this is a structural feature, not a named physics family.
- Compute the **primitive-set delta**: `primitives(I_new) - primitives(I_champion)`. The edit introduces new structure iff this set is non-empty.
- Compute the **AST symbolic edit distance** between champion and new form — a standard tree-edit-distance over the parsed AST, counting node insertions, deletions, and relabels as unit cost. This is the replacement for jaccard: it respects the tree structure of math expressions rather than treating them as token bags, so sign flips and position changes register as real edits and cosmetic token re-orderings do not.
- **Rules:**
  - `primitives(I_new) - primitives(I_champion)` must be non-empty. (Structural novelty.)
  - AST edit distance between `I_new` and `I_champion` must be within the envelope `[d_min, d_max]` — bounded below by `d_min` so the edit is non-trivial, and bounded above by `d_max` so the edit stays *minimal* (otherwise the mutator is effectively doing a cold-residual rewrite while pretending to preserve). Defaults `draft_default_n1`: `d_min = 3`, `d_max = 15`.
  - In ADD mode, edit distance is measured against the full champion; in REPLACE mode, it is measured against the specific term `T_k` being replaced (so a replacement that leaves four out of five terms untouched still registers as minimal).
- **Parser scope.** The AST parser is a non-trivial subproject. It must handle scipy/numpy/math idioms (`math.exp` vs `numpy.exp` vs `exp`), implicit multiplication, and nested function composition. Spec does not claim the parser is one line — it is scoped as a blocking prerequisite for preservation lane deployment, tracked in Open Questions, and shares infrastructure with any future symbolic-analysis work. If parsing fails on a proposed form, the iter is recorded as `preservation_parse_failed` and counts toward the stop-rule budget; it is *not* auto-accepted.
- **Topological distinctness via judge.** AST edit distance is a structural proxy. The judge additionally enforces **topological distinctness** via semantic argument: the judge is handed the champion and the proposed edit and asked, "does this edit change the qualitative shape of `I(phi, psi)` in the region where the failing gate lives, or is it a cosmetic perturbation?" A "cosmetic" verdict from the judge is a soft fail — it does not block the iter, but it is logged to structural memory and, if the judge flags three cosmetic edits in a row, preservation lane self-suspends for the rest of the run. This is a belt-and-suspenders check: AST distance catches the mechanical cases, judge semantic argument catches the cases where the math is different but the geometry is not.
- **Failure action:** structural check fail → one re-prompt naming the specific gap (missing primitive, edit distance too low, edit distance too high). Second failure falls preservation lane back to cold-residual for that iter. Re-prompts are a weak signal and should not be the primary mechanism — the hope is that Stage 1 rarely fails on first attempt because the contract in the preservation rule is already explicit about what a valid edit looks like.

**Stage 2 — farther-tail geometric check (post-fit, record-and-demote on fail):**

- After the fit primitive runs, evaluate `I_new(phi, psi)` and `I_champion(phi, psi)` on a **synthetic extrapolation grid** spanning phi values beyond the fit window, at the same psi values used in fitting. The grid is generated by the apparatus from the fit window's `max_phi` (e.g., `phi_grid = linspace(max_phi, 2 * max_phi, 50)`), is *not* derived from the farther-tail holdout evidence file, and is never used for scoring. This keeps the farther-tail holdout (GP-046 B-slice) untouched by preservation lane's internal checks.
- Compute the **farther-tail contribution ratio**: `max_over_grid(|I_new(phi, psi) - I_champion(phi, psi)| / (|I_champion(phi, psi)| + epsilon))` evaluated on the synthetic extrapolation grid (not on the fit window). The gate cares about behavior *beyond* where the champion already fits; the diversity floor must measure in the same region, or it is checking a domain the gate does not care about.
- **Rule:** farther-tail contribution ratio must be `>= r_min`. Default `draft_default_n1`: `r_min = 0.05`. This number is a guess tuned against sandbox_03's score-ceiling structure and is marked for re-tuning against at least two more problems.
- **Rationale for the synthetic grid.** The alternative — evaluating on the real farther-tail holdout — would contaminate the B-slice by using it inside the search loop. The synthetic grid is a cheap approximation that answers "does your edit do something different from the champion in the region the gate evaluates" without touching the holdout. If the edit closes the farther-tail gate at scoring time, that is the real test; the synthetic-grid check is only a floor against no-op edits.
- **Collapse check.** The new term's fitted parameters must not have collapsed to values that zero out the term (e.g., coefficient pinned at lower bound). This catches fit-primitive local minima that defeat the edit without defeating the check.
- **Failure action:** the iter is recorded to structural memory as `preservation_abandoned_noop`, the champion is *not* replaced, and preservation lane counts this iter toward its stop-rule budget `M`. No re-prompt — this is an apparatus demotion, not a mutator correction.

**Metric is not shared with GP-045.** Cold-residual continues to use its jaccard-against-residual-set novelty metric; preservation lane uses AST edit distance against the held champion plus judge topological distinctness. Structural memory tags each diversity event with `metric: "jaccard_residual_set" | "ast_edit_held_champion"` so the two modes do not contaminate each other's accounting.

### Stop rule

Preservation lane has three exit conditions and one hard run-level cap. The stop rule is declarative: the loop evaluates these after every preservation-lane iter and transitions accordingly.

**Exit condition 1 — score improvement (success, return to normal mode).**
- Trigger: iter score > previous champion score.
- Action: accept the new champion, clear the preservation-lane state, return loop_control_action to `normal`. Structural memory records `preservation_succeeded` with the delta's primitive set as the `escape_primitive`.

**Exit condition 2 — different failing gate (basin opened, return to cold-residual).**
- Trigger: iter score == previous champion score, but the *single failing gate id* differs from the gate that triggered preservation lane.
- Action: accept the new form as champion (it is the same score but a structurally different failure geometry), clear the preservation-lane state, return loop_control_action to cold-residual successor mode. This is an *informative* exit — the basin is different now, and cold-residual is the right tool for the new basin.

**Exit condition 3 — budget exhausted (give up, return to cold-residual).**
- Trigger: `M` preservation-lane iters have fired with no exit-1 and no exit-2 result.
- Action: clear preservation-lane state, return loop_control_action to cold-residual. Structural memory records `preservation_abandoned_budget` with the count of pre-fit and post-fit diversity-floor failures encountered during the run.
- **Default `M = 5`** — matches the sandbox_03 iter-13-to-20 gap (6 iters) as a rough scale for how long a basin-escape attempt gets before it counts as stuck.

**Run-level cap — lane exhaustion.**
- Trigger: preservation lane has fired `L` distinct times in a single run, each of which hit exit-3 (budget exhausted without escape).
- Action: preservation lane is disabled for the rest of the run. The rubric's cold-residual mode runs alone for remaining iters.
- **Default `L = 3`** — after three failed preservation attempts, the mechanism is not helping in this run and continued firing is pure overhead.

**Interaction with emergency_pivot / stagnation_pivot.**
- Preservation lane *suspends* emergency_pivot and stagnation_pivot loop-control actions for the duration it is active. Those actions are designed for full-rewrite escape and would contradict the additive-delta contract.
- On exit (any of 1, 2, 3), normal loop-control resumes with the stagnation counter reset to the value it had at preservation-lane entry (so exits 1 and 2 effectively rewind the stagnation penalty, while exit 3 preserves it).

### Interaction with GP-045 cold-residual successor

Cold-residual is the *default* diversity mode. Preservation lane is a *narrower* mode that fires only under the trigger condition above. When preservation lane stops (via stop rule), control returns to cold-residual with structural memory updated so the abandoned preservation attempt is recorded.

### Interaction with GP-035 fit primitive

Preservation-lane edits flow through `FIT_DECLARATION` with the `preservation_mode: "add" | "replace"` tag and per-parameter `"role"` field (`preserved`, `delta`, or `replacement`). The fit primitive must accept a fit declaration where some parameters are marked as preserved (initial guesses from prior champion, ±10% bounds) and others are new (loose bounds from mutator). **This requires a small GP-035 extension**, not prompt-only handling: GP-035's current parser does not understand per-parameter roles, and the bounds-narrowing on preserved params must be enforced at the fit layer, not trusted to the mutator. The extension is scoped as part of the FIT_DECLARATION drought-fix work item (both touch GP-035's parse-and-validate path) and is a blocking prerequisite for GP-047 launch.

### Interaction with structural memory

Preservation lane *reads* structural memory to decide when to fire (via the trigger condition). It also *writes* to structural memory so abandoned preservation attempts are recorded as a distinct event type (e.g., `preservation_abandoned`). No change to structural memory schema beyond the new event type.

### Rubric flag

New rubric field: `preservation_lane_mode: true | false`, default false. Sandbox_04 opts in; sandbox_03 and all historical rubrics stay unchanged.

### Sandbox_04 acceptance criteria

Sandbox_04 is a three-arm experiment. It uses a **freshly authored farther-tail holdout** on the same hidden generator class as sandbox_03, not the same holdout file. The sandbox_03 B-slice is a one-shot oracle and has already been consumed by the sandbox_03 run; re-using it in sandbox_04 would be double-dipping the falsification oracle and would invalidate any basin-escape claim. Authoring the new holdout is a blocking prerequisite alongside the FIT_DECLARATION drought fix. The three arms:

- **Arm A — Control.** `preservation_lane_mode: false`, mutator = gemini-2.5-flash. This is sandbox_03 discipline with the apparatus fix only. Establishes the baseline basin-escape rate with no new mechanism.
- **Arm B — Treatment.** `preservation_lane_mode: true`, mutator = gemini-2.5-flash. Tests preservation lane against the same model that sandbox_03 used, isolating the mechanism from the model capability.
- **Arm C — Mutator swap.** `preservation_lane_mode: false`, mutator = gemini-2.5-pro (or Claude). Tests whether basin stickiness is a model-capability issue rather than a search-mode issue. This is Option C from the Options section, running as a parallel arm.

Each arm runs 100 iters. A fourth arm (B+C, preservation lane *and* stronger mutator) is out of scope for sandbox_04 and scheduled for sandbox_05 if both B and C show independent signal.

**Primary acceptance criteria — preservation lane is worth keeping if all of the following hold:**

1. **Arm B produces at least one basin escape that Arm A does not.** An escape is defined as: (a) a score strictly greater than the sandbox_03 iter-13 ceiling of 50, OR (b) a score-50 champion whose single failing gate is *different* from `farther_tail_global_residual`. The escape must occur in Arm B and not in Arm A on the matched iter budget.
2. **Arm B's escapes survive the B-slice.** Any escape produced by preservation lane must pass the farther-tail holdout evaluation. If an Arm B escape passes visible-side gates but fails the B-slice, it is counted as a softening-the-void failure and *disqualifies* the escape. This is the critical Invert-leg guardrail.
3. **Arm B's preservation-lane overhead stays bounded.** Total iters spent inside preservation lane across the run must be ≤ `30%` of 100 iters = 30 iters. If preservation lane is active for more than 30 iters of the run, the stop rule is insufficiently strict and the mechanism has become the default. This directly enforces "exception that must expire" at the experiment level.
4. **Arm B does not regress on historical rubrics.** Smoke-test Arm B's rubric mode against sandbox_02 replay (no holdout) and sandbox_03 replay (full holdout, existing data). Neither replay may produce worse champion scores than the historical runs.

**Hard goalpost pre-commitment on Arm C.** If Arm C escapes and Arm B does not, **preservation lane is withdrawn**, full stop. No efficiency-argument retreat. The motivation for preservation lane is that search mode is the bottleneck; if a mutator swap alone escapes the basin, that hypothesis is falsified and the spec's justification evaporates. This is pre-committed here so that the withdrawal is not re-litigated after the data arrives.

**Secondary criteria — informative but not decisive (evaluated only if the hard goalpost is not triggered):**

- **Arm C and Arm B both escape.** Report both; do not claim one is strictly better without a sandbox_05 head-to-head.
- **Primitive-set telemetry.** Log which primitive the winning edit introduced in each Arm B escape and whether the escape came via ADD mode or REPLACE mode. If all escapes introduce the same primitive, that is itself a finding about the grammar gap in the default mutator vocabulary. If all escapes come via REPLACE and none via ADD, that confirms the incommensurability critique and validates the broader-contract decision.

**Pre-declared failure modes (preservation lane is withdrawn if any occurs):**

- Arm B escapes but fails B-slice → softening the void, withdraw
- Arm B never triggers stop rule across 100 iters → exception became default, withdraw
- Arm A matches or beats Arm B on escape rate → preservation lane is not earning its keep, withdraw
- Arm B regresses on sandbox_02/sandbox_03 replay → mechanism has unintended side effects, withdraw

**Sandbox_04 is decisive only for the sandbox_03 basin.** Generalization to other sticky-basin problems requires one additional rubric before preservation lane is adopted as a default-available mode. The second rubric is pre-declared in Open Questions: the `central_station` startup-domain rubric from prior work, re-shaped as a sticky-basin test. That follow-on runs *after* sandbox_04 succeeds and is not a blocker for sandbox_04 itself — but if sandbox_04 succeeds and central_station fails, preservation lane remains rubric-opt-in rather than default-available.

## Open Questions

- **FIT_DECLARATION drought fix scope.** The GP-023 seam Turn 29 logs a related apparatus failure: FIT_DECLARATION getting dropped under sustained emergency_pivot because the trailing-reminder line gets pushed far from the generation head. Preservation lane will *intensify* this pressure because it adds more content to the mutator prompt. Should the fix ship as part of this spec, or as a separate hardening turn before this spec lands? Tentative answer: separate hardening turn, blocking prerequisite for GP-047 deployment.
- **Pre-fit vs post-fit diversity floor check.** See Implementation Sketch. No clear winner yet.
- **K and M defaults.** `K=3` and `M=5` are guesses from the sandbox_03 pattern. Should be tuned against at least two more runs before hardcoding.
- **Grammar-expansion primitive set.** Should the syntactic diversity floor be rubric-configurable (allowing the rubric to specify "denominator forms are in-scope for this problem") or global? Rubric-configurable is more flexible but adds another leak surface.
- **Mutator model dependency.** Does preservation lane work with Gemini-flash, or does it require a stronger mutator to generate non-trivial additive deltas? This is exactly the question Option C addresses; running sandbox_04 with both arms would answer it.
- **Does preservation lane violate cold-residual diversity in structural memory terms?** Cold-residual enforces novelty; preservation lane enforces continuity. Structural memory must distinguish these two modes or the diversity accounting will be incoherent.
- **Falsification discipline.** What observation would convince us preservation lane is *worse* than cold-residual? Pre-declared failure modes: (a) sandbox_04 produces score-ceiling escapes that the B-slice cannot distinguish from finite-window surrogates (softening the void without earning it); (b) preservation lane fires but never stops — stop rule never triggers across 100 iters, meaning the "exception that must expire" has become a new default; (c) A/B comparison shows cold-residual-only matches or beats cold-residual+preservation on basin-escape rate. If any of these occur, preservation lane is withdrawn.
- **A/B baseline arm for sandbox_04.** Is there a rubric mode where preservation lane is disabled by default as the stricter invert-discipline baseline, so sandbox_04 can A/B cold-residual-only vs cold-residual+preservation on the same problem? Answer: yes, this is required. Sandbox_04 ships with two arms — one with `preservation_lane_mode: false` (control, matches sandbox_03 discipline), one with `preservation_lane_mode: true` (treatment) — and the basin-escape claim is only valid if the treatment arm beats the control. This is the cleanest way to prove the softening earns its keep.
- **Metric decoupling from GP-045.** Preservation lane no longer shares jaccard with GP-045 (see Diversity floor — jaccard is too brittle for math expressions). The two modes now use different metrics on different anchors: cold-residual uses jaccard against residual set, preservation lane uses AST edit distance against held champion plus judge topological distinctness. Structural memory tags each diversity event with the metric used, so the two modes cannot contaminate each other's accounting. Open subquestion: should GP-045 also migrate to AST edit distance eventually, or is jaccard good enough for residual-set novelty where token-level comparison is less brittle? Scope: separate spec, not a GP-047 prerequisite.
- **AST parser as a blocking prerequisite.** The structural diversity check requires an AST parser for math expressions that handles scipy/numpy/math idioms, implicit multiplication, and nested function composition. This is not a one-liner and is scoped as a separate work item (tentatively GP-048) that must land before GP-047 can deploy. Parser failure on a proposed form is recorded as `preservation_parse_failed` and counts toward the stop-rule budget — the parser is never a silent no-op.
- **FIT_DECLARATION drought fix is not yet designed.** The spec declares the fix as a blocking prerequisite but the fix itself is hypothesized, not designed. Candidate approaches: (a) hoist the fit-declaration contract to a pre-generation structured template rather than a trailing reminder; (b) add a pre-submission validator that rejects the iter and re-prompts once if the block is missing; (c) change the generation stop token / structured-output mode so the block cannot be truncated. Each has different failure modes and different implementation costs. **GP-047 cannot launch until (a)/(b)/(c) is chosen, designed, implemented, and smoke-tested.** The fix is currently a hope, not a prerequisite in hand.
- **Lane exhaustion overhead is real, not cheap.** `L = 3 × M = 5 = 15` iters is 15% of a 100-iter run in the worst case (preservation lane fires three times, each exhausts its budget, each fails to escape). This is a real cost that the spec did not originally acknowledge. Sandbox_04's "preservation-lane iters ≤ 30%" acceptance criterion implicitly bounds it, but the spec should be honest that preservation lane is *not* free when it fails — the overhead is the price of running the experiment. If the mechanism fails, the budget spent on it is the cost of learning that.
- **Generalization arm must be pre-declared.** After sandbox_04, if preservation lane is adopted, the generalization test runs on one additional rubric — pre-declared here so it is not selected post-hoc to confirm. **The pre-declared second rubric is a non-physics generative problem: the `central_station` startup-domain rubric from prior work, re-shaped as a sticky-basin test.** This is a rubric where ZTARE has existing baseline data and where the "close-but-wrong structural family" failure mode is plausible (startup unit-economics surrogate models are known to exhibit it). If preservation lane works on sandbox_04's physics generator and on central_station's startup generator, it earns default-available status. If it only works on sandbox_04, it stays rubric-opt-in.
- **Fallback plan if sandbox_04 withdraws preservation lane.** If all pre-declared failure modes fire and GP-047 is withdrawn, the fallback for sticky basins is: (i) keep cold-residual as the default (unchanged), (ii) reconsider GP-028 speculative lane as the primary escape mechanism rather than a sibling, (iii) investigate whether the basin stickiness is fundamentally a mutator-capability problem (Arm C data from sandbox_04 is the first evidence on this), and (iv) accept that some problems are genuinely unreachable with the current apparatus and publish the null result as a finding about the Compress leg's catching-vs-climbing asymmetry. "Give up" is a legitimate outcome and is not treated as failure — the point of the pre-reg discipline is to make the null result publishable.

## Cross-references

- GP-023 ontology-trap seam Turn 29 (2026-04-13): live observation of the sticky-basin phenomenon that motivates this spec; `research_areas/private/seams/GP-023_ontology_trap_planck_mechanism_seam.md`
- GP-028 speculative hypothesis lane spec: sibling search-mode mechanism with opposite polarity; `research_areas/private/specs/active/GP-028_speculative_hypothesis_lane_spec.md`
- GP-035 mutator fit primitive spec: fit primitive that must accept preservation-lane fit declarations; `research_areas/private/specs/active/GP-035_mutator_fit_primitive_spec.md`
- GP-045 cold residual successor mode: the default diversity mode that preservation lane augments
- GP-046 asymptotic claim discipline / farther-tail holdout: the B-slice that preservation lane must not contaminate; empirical anchor in `~/.claude/projects//memory/project_gp046_empirical_anchor.md`
- Jaccard / Tunneling / Annealing probe memory: `~/.claude/projects//memory/project_jaccard_tunneling_annealing.md` — preservation lane was first raised there as the GP-028 tunneling alternative and deferred

## Status Note

Draft revised 2026-04-13 after red-team critique. Revisions addressed:

- **Motivating example reach.** Additive-only contract replaced with minimal-structural-edit contract (ADD or REPLACE, exactly one term edit). The sandbox_03 Planck-vs-exponential incommensurability is now inside the mechanism's reach via REPLACE mode, and the spec names this explicitly in Problem / Why "additive only" is not enough.
- **Apparatus ontology leak.** Primitive vocabulary renamed from physics-named families (`denominator_bose`, `denominator_fermi`) to structural descriptors (`rational_simple`, `rational_with_additive_offset`). No physics names in the apparatus.
- **Metric brittleness.** Jaccard on math tokens replaced with AST symbolic edit distance plus judge topological-distinctness check. GP-045 residual-set jaccard is untouched; metrics are explicitly decoupled and tagged in structural memory.
- **Farther-tail contribution domain.** Post-fit check moved from fit-window evaluation to a synthetic extrapolation grid beyond the fit window (not the real holdout). The check now measures in the same region the gate evaluates, without touching the B-slice.
- **B-slice double-dipping.** Sandbox_04 requires a freshly authored farther-tail holdout; the sandbox_03 B-slice is treated as a consumed one-shot oracle.
- **Arm C goalpost.** Pre-committed: if Arm C escapes and Arm B does not, preservation lane is withdrawn regardless of efficiency arguments.
- **Numerical defaults.** All `K / M / L / d_min / d_max / r_min` are tagged `draft_default_n1` and require re-tuning against at least two additional problems.
- **Single-sample generalization.** Generalization test pre-declared: `central_station` startup-domain rubric as the non-physics second rubric.
- **Drought-fix honesty.** Spec now admits the FIT_DECLARATION drought fix is not yet designed, lists three candidate approaches, and blocks GP-047 launch on choosing one.
- **AST parser scope.** Parser named as a separate blocking work item (tentative GP-048), not a one-line implementation detail.
- **Fallback plan.** If preservation lane is withdrawn, the fallback is documented (keep cold-residual, reconsider GP-028, investigate mutator-capability ceiling, publish null as Compress-leg catching-vs-climbing finding).

Not yet done:
- register GP-047 on `ZTARE_BOARD.md` with seam + spec links
- scope GP-048 AST parser as a separate spec
- design the FIT_DECLARATION drought fix (choose one of the three candidates)
- author sandbox_04 rubric with fresh farther-tail holdout
- structural memory `metric` tag patch
- rubric parser extension for `preservation_lane_mode`

Spec is now at debate-ready state. The central risk is no longer "does the mechanism match its motivating example" (fixed) but "does the mechanism generalize beyond a single n=1 tuning", which sandbox_04 + central_station are designed to answer.
