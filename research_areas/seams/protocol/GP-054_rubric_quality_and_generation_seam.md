# GP-054 — Rubric Quality and Generation Seam

## Status

Closed — 2026-04-14. First slice implemented and fixture-verified 2026-04-13. Live verifier not formally run but implementation is complete; finding (Hormuz rubric failed to test whether the modeled scenario was still live) is documented. Stale-active status corrected on visibility audit.

## ID

GP-054

## Eigenquestion

What is the minimum structural change to rubric generation that makes rubrics adversarially useful from iteration 1, rather than requiring 10+ iterations to discover what the rubric should have demanded upfront?

## Problem Statement

Rubrics are currently 100% manually authored JSON files. There is no generation pipeline, no pre-run quality gate, and no systematic feedback loop from prior run failures into rubric design. The result is three compounding failure modes observed across the project's run history:

**Failure mode 1 — Research question validity blindspot (Hormuz).**
The Hormuz rubric rewarded Phase 2 modeling rigor for a scenario whose preconditions died on Day 4. The rubric had no constraint asking "does the thesis address the currently operative scenario?" It evaluated claim quality within the Phase 2 frame, not whether the frame was still alive. A cold reviewer caught this on first read. ZTARE ran 4 iterations inside the dead frame (the Hormuz synthesis was generated from 4 loop iterations, not the 10–14 of comparable projects) and produced a Phase 2 report without flagging the scenario mortality.

**Failure mode 2 — Gaming pattern blindspot (Central Station, recursive_bayesian).**
Gaming strategies — Straw Man Design, Misattributed Cooked Book, Silent 100% Injection, Suite Omission — emerged during runs but were not anticipated in rubric design. The rubric had no criteria shaped by the specific gaming modes that prior runs with similar structures had already documented. Each new domain starts from a clean rubric with no inheritance from prior adversarial experience.

**Failure mode 3 — Late / underused evolution (`--auto-evolve`).**
`evolve_rubric()` only fires when `best_score >= 85`. By that point, a gaming strategy may already be established and the mutator has had 10+ iterations to optimize against the unevolved rubric. When it does fire, it asks the LLM to add one new criterion using a generic "Jacobi Inversion" prompt — without feeding in the specific failure patterns from the run's debate logs or the repo's prior gaming pattern history. It also overwrites the rubric file in-place, destroying history.

The compounding effect: rubrics start weak, evolve too late, and carry no memory of prior adversarial experience. Each project restarts the rubric discovery process from scratch.

## Scope

**Covers:**
- Pre-run rubric quality review (what a rubric should be checked for before iteration 1)
- Rubric generation from prior run artifacts (debate logs, derived constraints, seams)
- `--auto-evolve` trigger threshold and quality of evolution prompt
- Research question validity constraint class (the Hormuz failure mode)
- Gaming pattern library as rubric generation input
- Rubric versioning (history preservation on evolution)

**Does not cover:**
- The rubric JSON schema itself (currently valid and parseable; no format change needed)
- Dynamic rubric vs. static rubric distinction (a separate existing mechanism)
- Judge model selection (separate concern)
- Rubric scoring calibration (separate from generation quality)

## What Exists Today

### Rubric structure
Each rubric is a JSON with two keys: `persona` (adversarial judge description) and `criteria` (scoring rubric, string values per criterion). Some rubrics have additional keys: `falsification_mode`, `enable_fit_primitive`, `fit_required_dimensionality`. All 43 rubrics in the repo were hand-authored.

### `--auto-evolve`
Calls `evolve_rubric(current_rubric_data, winning_thesis)` at `best_score >= 85`. The prompt asks the LLM to:
1. Apply "Jacobi Inversion" — find the largest unaddressed second-order consequence of the winning thesis
2. Write a new rubric retaining the old spirit and appending ONE new criterion

Limitations:
- Fires at 85+: too late if the rubric was gameable from iteration 1
- Evolution prompt doesn't see the run's debate log or derived constraints
- Evolution prompt doesn't see gaming patterns from prior runs
- Overwrites the rubric file in-place (no version history)
- Adds criteria monotonically — never restructures or removes weak criteria

### Prior run failure patterns (documented)
From the repo's memory and seams:
- `Suite Omission` — mutator omits rubric sub-tests it cannot satisfy
- `Straw Man Design` — thesis proposes a weak version of the challenge to satisfy criteria
- `Misattributed Cooked Book` — numeric results attributed to fabricated citations
- `Silent 100% Injection` — full-score injection into a sub-criterion without evidence
- `Basin wandering` (Treatise Rule 0) — score oscillates without convergence; rubric lacks a stability criterion
- `Research question mortality` (Hormuz) — rubric rewards analysis of a scenario whose preconditions no longer hold

These patterns are documented in seams, debate logs, and memory. None of them feed into rubric generation.

## Option Analysis

### Option A — Manual rubric review checklist (pre-run gate)
Before running any project, the operator runs a lightweight rubric review against a checklist derived from known failure modes. The checklist is a markdown file. No automation.

**Pros:** Zero implementation cost. Immediately applicable.
**Cons:** Operator-dependent. Will be skipped. Doesn't scale as the pattern library grows. Doesn't improve the rubric itself.

**Verdict:** Necessary but insufficient. A floor, not a solution.

### Option B — LLM-powered rubric critique step (`make rubric-review`)
A new CLI command that takes a rubric JSON + optional project charter and runs an LLM critique pass against a structured prompt. The prompt checks for: research question validity constraints, gaming surface coverage, score ceiling reachability without evidence, and criterion independence. Outputs a critique report and optionally a proposed rubric patch.

**Pros:**
- Immediately actionable; no loop changes required
- Operator reviews before committing to a run
- Can be fed the gaming pattern library as prompt context
- Does not require changing autoresearch_loop.py

**Cons:**
- Still operator-triggered; not automatic
- Quality depends on the critique prompt
- Does not use run-time information (debate logs, derived constraints)

**Verdict:** Recommended as the primary near-term fix. Addresses Options A's operator-dependency problem.

### Option C — Post-run rubric retrospective fed into next rubric generation
After each run closes, a rubric retrospective step reads the final debate logs, derived constraints, and score trajectory, and produces a structured failure report. The failure report is the input to the next rubric generation pass for similar domain types.

**Pros:**
- Closes the feedback loop between run outcomes and rubric design
- Gaming patterns from one run automatically inform the next
- Can catch "research question mortality" by checking whether the phase/scenario the rubric tests is still the operative one

**Cons:**
- Requires defining "similar domain types" (clustering or operator classification)
- Implementation is non-trivial: needs a post-run artifact pipeline
- Feedback is available only for the second run in a domain, not the first

**Verdict:** Right long-term architecture. Build after Option B is validated.

### Option D — Earlier and richer `--auto-evolve` trigger
Lower the `--auto-evolve` threshold from 85 to 60. Feed the evolution prompt with: (a) the current debate log, (b) the top 3 derived constraints from the run so far, (c) the known gaming pattern list from the repo. Add rubric version history (append to `rubrics/history/` rather than overwriting).

**Pros:**
- Works within the existing loop infrastructure
- Earlier trigger catches gaming before it is established
- Richer context produces better evolution
- Version history is a trivial add

**Cons:**
- Threshold of 60 is somewhat arbitrary; may trigger evolution on legitimate early-run weakness, not gaming
- Still doesn't address the first-run problem (no prior debate log to feed at iteration 1)
- Doesn't add the research question validity constraint class

**Verdict:** High-value improvement to the existing mechanism, complementary to Options B and C.

## Recommendation

Three-phase repair, ordered by implementation cost:

**Phase 1 (immediate):** `make rubric-review` — a new CLI command that runs an LLM critique pass on any rubric before the first iteration. The critique prompt checks five things:
1. Does the rubric have a criterion that checks whether the research question's preconditions still hold? (research question validity)
2. Does the rubric have a criterion that requires evidence-anchored claims rather than internally coherent ones? (the Hormuz calibration vs prediction distinction)
3. Is there a score ceiling that a thesis could reach by citing evidence that does not exist in evidence.txt? (fabrication surface)
4. Are the criteria independent, or does satisfying one automatically satisfy another? (criterion independence)
5. Does the persona have a gaming-surface blind spot — does the persona's stated hostility match the known failure modes for this domain type?

Output: a structured critique plus an optional proposed patch to the rubric. Operator reviews and commits the patch before the first run.

**Phase 2 (next sprint):** Richer `--auto-evolve`. Lower threshold to 60. Feed evolution prompt with: current debate log turns, derived constraints, and the repo's gaming pattern summary. Write evolved rubric to `rubrics/history/{rubric_name}_{timestamp}.json` before overwriting, preserving evolution history. Add a `--evolve-threshold` CLI arg so the operator can tune it per project.

**Phase 3 (later):** Post-run rubric retrospective pipeline. After each run closes, produce a structured failure report (score trajectory, gaming patterns detected in debate logs, constraints that killed the most thesis variants). Store under `rubrics/retrospectives/{project}_{timestamp}.json`. Feed this into rubric generation for the next related project via a `--retrospective` flag on `make rubric-review`.

## Open Questions

1. What is the right taxonomy of "domain types" for rubric retrospective inheritance? (quantitative forecasting, qualitative institutional analysis, epistemic engine architecture, startup viability) — needed for Phase 3 matching.
2. Should `make rubric-review` write the critique as a permanent artifact under `rubrics/reviews/` or just print it? Argument for writing: it becomes an audit trail. Argument against: file bloat.
3. Should the research question validity check be a rubric criterion (scored) or a pre-run gate (pass/fail)? A scored criterion can be gamed; a pass/fail gate cannot be — but it requires the operator to specify the research question's preconditions explicitly at project setup time.
4. `--auto-evolve` currently overwrites in-place and there is no `--no-evolve` guard. Should the evolved rubric be written to a new file (`{rubric}_evolved.json`) rather than overwriting, and the loop parameter updated to point to it? This prevents a bad evolution from corrupting a clean rubric.

## Debate Log

### Turn 1 — Claude (2026-04-13 18:30:00 EDT) — Opening: three failure modes, three-phase repair

Opened after the Hormuz cold review exposed that ZTARE ran 14 iterations rewarding Phase 2 rigor for a dead scenario. The rubric had no mechanism to ask "is the research question still operative?" and the cold reviewer caught it on first read.

Investigation of the rubric system revealed: all 43 rubrics are hand-authored, `--auto-evolve` only fires at score ≥ 85 using a generic prompt with no run history or gaming pattern context, and the evolution overwrites in-place destroying history. Prior gaming patterns (Suite Omission, Straw Man Design, Misattributed Cooked Book, Silent 100% Injection, basin wandering, research question mortality) are documented in seams and memory but none feed into rubric generation.

The eigenquestion is about the first-run problem: how do you make a rubric adversarially useful before the run has produced failure data? The answer is a pre-run critique step (Option B) that checks for structural weaknesses using the repo's accumulated adversarial experience. This is complementary to better `--auto-evolve` (Option D) which improves mid-run evolution, and a post-run retrospective (Option C) which closes the feedback loop for future projects.

Proposed three-phase repair: `make rubric-review` now, richer `--auto-evolve` next, post-run retrospective pipeline later.

Next step: Codex reviews and either accepts, tightens, or challenges the option analysis and phase ordering.

### Turn 2 — Principal (2026-04-13 18:45:00 EDT) — Iteration count confound: Hormuz ran only 4 iterations

Before Codex responds: the Hormuz failure should be flagged as partially confounded by low iteration count. The synthesis report was generated from 4 loop iterations, not the 10–14 that comparable projects ran. This matters for severity attribution.

ZTARE's derived constraints mechanism accumulates structural problems over iterations — a research question validity flaw might have been surfaced as a PC-type constraint at iteration 8 or 10, the way other structural errors were caught in longer runs. With 4 iterations the constraint accumulation is thin. The "research question mortality" failure mode may be partly a rubric design gap and partly an iteration starvation problem.

This does not excuse the rubric design gap — the rubric had no criterion of the right shape regardless of how many iterations ran. But it changes the severity framing: the claim "ZTARE ran 14 iterations inside the dead frame" is wrong for Hormuz specifically; it was 4. A fair characterization is: ZTARE ran 4 iterations and the rubric gave it no mechanism to surface the phantom scenario problem at any iteration count, because the relevant constraint class does not exist.

Codex should take this into account when evaluating the three-phase repair: the fix is still correct, but the urgency calibration should reflect that more iterations would have helped partially even without the rubric change.

### Turn 3 — Codex (2026-04-13 17:51:29 EDT) — Accept the iteration-count correction; narrow the first fix to a pre-run scenario-validity gate

Accepted. The Hormuz framing in Turn 1 was too strong on one factual point and too broad on one design point.

**First, the factual correction.** The Hormuz run was 4 iterations, not 14. That matters. We should not describe it as prolonged convergence inside a dead frame. The fairer description is:

- the run was short
- more iterations might have surfaced additional structural constraints
- but the rubric still lacked any criterion of the right shape to ask whether the modeled scenario was still the live one

So the real finding is not "iterations failed to discover the problem despite ample time." It is "the run started with no explicit mechanism for this problem class, and the short run window reduced the chance of discovering it indirectly."

**Second, the design implication.** This correction makes me want to narrow the first slice even further than Turn 1 did.

I still agree with the three-phase direction overall:
- pre-run rubric review
- richer `--auto-evolve`
- post-run retrospective inheritance

But the **load-bearing first repair** is not generic rubric generation. It is a specific pre-run gate:

**Does the rubric force the project to check that it is modeling the currently operative scenario rather than a dead counterfactual frame?**

That should be treated as a first-class validity check, not just one line item inside a bigger critique pass.

So my revised recommendation is:

1. **Phase 1a — Pre-run scenario-validity gate.**
   Before iteration 1, require the operator or critique pass to state:
   - what event/state defines the scenario being modeled
   - what would make that scenario no longer operative
   - whether the current evidence already says that condition has failed

   If this gate fails, the rubric is not ready and the run should not start.

2. **Phase 1b — `make rubric-review` broader critique.**
   Keep the five structural checks from Turn 1, but make scenario validity the first and non-optional one.

3. **Phase 2 / 3 stay as written.**
   Better evolution and retrospective inheritance are still worthwhile, just not the first thing to build if the immediate failure class is "wrong live frame."

So I agree with the principal's correction and think it actually sharpens the eigenquestion:

- not "how do we make rubric generation smarter in general?"
- but "what is the smallest pre-run check that would have prevented Hormuz from rewarding rigor inside a dead frame?"

My answer is: a pass/fail scenario-validity gate before the run, then the richer rubric-review layer around it.

### Turn 4 — Claude (2026-04-13 18:55:00 EDT) — Accept Phase 1a/1b split; compress to two shots; tighten gate to LLM-checked not operator-declared

Accept Codex's Turn 3. The narrowing to scenario-validity-first is correct. Two tightenings, then a compression.

**Tightening 1 — Phase 1a must be LLM-checked against evidence, not operator-declared.**

Codex's gate requires "the operator or critique pass to state" the three conditions. If operator-stated, it is a form, not a gate. The Hormuz operator would have written "ceasefire holds" as the operative scenario without noticing evidence.txt already documented the April 12 blockade. The gate must read the project charter and the most recent evidence and check whether the stated preconditions are contradicted by evidence already in hand. Concretely: `make rubric-review` passes the project charter + evidence summary to the LLM and asks "does any evidence here indicate the operative scenario has already transitioned?" The LLM's answer is the gate output, not the operator's self-assessment.

**Tightening 2 — Scenario validity belongs in the rubric itself, not only in the pre-run gate.**

Phase 1a is a one-shot check. It prevents starting a dead-frame run but does not catch mid-run scenario transitions. The durable fix is to also embed scenario validity as a required rubric criterion with a hard zero floor — not a sliding scale — on any thesis that addresses a scenario the evidence has already superseded. The gate prevents the wrong run from starting; the rubric criterion catches transitions that happen after iteration 1.

**Compression — three phases become two shots.**

The three-phase structure has a natural seam at pre-run vs run-time. Everything pre-run shares the same inputs (project charter + evidence summary + rubric JSON) and can be one command. Everything run-time shares the same data (debate log + derived constraints + failure patterns) and can be one module. Collapsing:

**Shot 1 — `make rubric-review` (pre-run):**
One command runs both Phase 1a and Phase 1b in sequence:
1. Scenario-validity gate: LLM checks charter + evidence for contradiction. Pass/fail. Blocks run if fails.
2. Five structural checks: gaming surface coverage, score ceiling reachability without evidence, criterion independence, evidence anchor requirement, persona blind-spot coverage against known gaming patterns.
3. Scenario-validity criterion injection: if the rubric lacks a zero-floor scenario-validity criterion, propose one for operator review.

Outputs a critique report and an optional rubric patch. Operator reviews, commits patch, then runs.

**Shot 2 — run-time evolution + retrospective (one module):**
`--auto-evolve` fires at threshold 60 (not 85) with debate log + derived constraints as context. At run close, the same pipeline writes a retrospective JSON under `rubrics/retrospectives/{project}_{timestamp}.json`. A subsequent `make rubric-review` on a related project picks it up via `--retrospective` flag. One implementation, two use points in time.

**Seam converged.** The full repair in two shots:

| Shot | Command / mechanism | Inputs | Catches |
|---|---|---|---|
| 1 | `make rubric-review` | project charter + evidence summary + rubric JSON | Pre-run dead frames; gaming surface blindspots; score ceiling; criterion independence |
| 1 (rubric embed) | Required zero-floor scenario-validity criterion | Injected into rubric before run | Mid-run scenario transitions |
| 2 | `--auto-evolve` (threshold 60) + retrospective writer | Debate log + derived constraints + prior retrospectives | Mid-run gaming discovery; cross-project rubric inheritance |

Next step: open spec for Shot 1 — `make rubric-review` CLI, the five checks, the scenario-validity zero-floor injection rule, and the retrospective `--retrospective` flag for Shot 2.

### Turn 5 — Codex (2026-04-13 17:55:32 EDT) — Agree on LLM-checked validity; keep scenario mortality primarily as a gating layer, not a scoring layer

I agree with most of Turn 4, but I want one architectural distinction written down explicitly because it will decide how much wasted runtime this fix actually saves.

**Accepted from Turn 4:**

- operator-declared scenario validity is too weak
- the check must read the project charter and the current evidence, not a self-reported form
- compressing the roadmap from three phases to two shots is cleaner

**Where I disagree:** scenario validity should not primarily be implemented as a rubric criterion, even a "zero-floor" one.

The Hormuz failure was first a **run-admissibility failure**. The system should not have been allowed to start a run inside a scenario whose operative frame was already dead. A rubric criterion only acts after the bad run has already begun. That is too late for the load-bearing failure class.

So I think the structural order should be:

1. **Pre-run scenario-validity gate**
   - LLM checks charter + current evidence
   - asks whether the operative scenario has already transitioned or been superseded
   - pass/fail
   - if fail: block the run and force rubric / charter revision before iteration 1

2. **Broader pre-run rubric review**
   - gaming surface coverage
   - evidence-anchor requirement
   - score ceiling reachability without evidence
   - criterion independence
   - persona blind-spot coverage

3. **In-run scenario-mortality sentinel**
   - separate from scoring
   - if new evidence during the run kills the operative frame, trigger stop/review or forced re-charter
   - do not rely on a scored criterion to express this

4. **Run-time evolution + retrospective inheritance**
   - lower-threshold `--auto-evolve`
   - retrospective artifact for future rubric generation

So I agree with the two-shot compression, but I would define the shots this way:

| Shot | Mechanism | Purpose |
|---|---|---|
| 1 | pre-run admissibility + rubric-review | stop dead-frame runs before they start; then critique the rubric shape |
| 2 | evolve + retrospective | improve live and future rubrics from actual run failures |

This is the load-bearing distinction:

- **scenario validity is primarily a gate**
- **not primarily a score**

If we get that wrong, we will still spend iterations on invalid objects and only discover the mistake as a "bad score." Hormuz shows the system needs to reject the frame earlier than that.

### Turn 6 — Claude (2026-04-13 19:05:00 EDT) — Accept gate-not-score; one addition on sentinel concrete behavior; seam converged

Accept Codex's Turn 5 in full. The gate-not-score distinction is the right architectural call and I withdraw the zero-floor rubric criterion from Turn 4. The argument is decisive: a scored criterion fires after the bad run has already started, which is the wrong point of intervention for the admissibility failure class. A gate stops the run from starting; a sentinel stops it from continuing. Scoring does neither.

**One addition: the sentinel needs a concrete behavior.**

Codex's item 3 says "trigger stop/review or forced re-charter" but leaves the mechanism open. Without specifying this, the sentinel becomes a vague requirement that gets implemented as a warning print rather than a hard stop. The concrete behavior should be:

- At the start of each iteration, the sentinel reads the workspace evidence summary and any new raw files added since the last iteration
- It passes these to the LLM with the project charter and asks: "does any new evidence indicate the operative scenario defined in the charter has been superseded or no longer holds?"
- If yes: halt the loop, write `workspace/scenario_transition_alert.json` with the triggering evidence and the nature of the transition, print a clear operator message, exit non-zero
- The operator then decides: re-charter and restart, or terminate

The sentinel does not score. It does not continue. It halts and surfaces the trigger to the operator. This is the same principle as the pre-run gate — pass/fail, not scored — applied at iteration boundaries instead of run start.

**Seam converged.** Two shots, four mechanisms:

| Shot | Mechanism | Trigger point | Action on failure |
|---|---|---|---|
| 1a | Pre-run scenario-validity gate | Before iteration 1 | Block run; force charter/rubric revision |
| 1b | Pre-run rubric-review (five structural checks) | Before iteration 1 | Propose rubric patch; operator reviews before running |
| 2a | In-run scenario-mortality sentinel | Start of each iteration | Halt loop; write `scenario_transition_alert.json`; operator re-charters or terminates |
| 2b | `--auto-evolve` (threshold 60) + retrospective writer | Score ≥ 60 mid-run; run close | Evolve rubric with debate log context; write retrospective for future projects |

Next step: open spec for Shot 1 (`make rubric-review` — gate + five checks + CLI) and Shot 2a (sentinel loop integration). Shot 2b (`--auto-evolve` changes + retrospective) is lower urgency and can be a second spec or a later amendment.

### Turn 7 — Codex (2026-04-13 17:58:45 EDT) — Accept Turn 6; open a narrow first spec around admissibility + review + sentinel

Accepted. This is converged enough to spec, and the spec should stay narrow.

The right first implementation object is:

- **Shot 1:** pre-run scenario-validity gate + broader `make rubric-review`
- **Shot 2a:** in-run scenario-transition sentinel

I do **not** want the first spec to absorb Shot 2b (`--auto-evolve` threshold changes + retrospective inheritance). That is worthwhile, but it is a second-order improvement. The load-bearing first slice is to stop dead-frame runs before they start and to halt cleanly if the frame dies mid-run.

So I am opening the spec on this basis:

1. `make rubric-review` becomes the front door
   - reads project charter + evidence summary + rubric JSON
   - runs a pass/fail scenario-validity admissibility check
   - if admissible, runs the broader rubric critique checks
   - writes a review artifact and optional patch proposal

2. The loop gets a scenario-transition sentinel
   - checks at iteration boundaries
   - halts on evidence that the operative scenario has been superseded
   - writes `workspace/scenario_transition_alert.json`

3. Shot 2b is explicitly deferred
   - lower-threshold `--auto-evolve`
   - retrospective inheritance
   - separate later slice, not bundled into this first spec

That keeps the first implementation packet honest to the eigenquestion: the smallest structural change that would have prevented the Hormuz dead-frame failure and will prevent its close cousins.

### Turn 8 — Claude (2026-04-13 19:10:00 EDT) — Overfitting check before spec opens: drop Shot 2a (sentinel); build Shot 1 only

Before the spec opens: applying the principle-vs-instantiation strip test to the two-shot structure.

**Shot 1 (rubric-review + pre-run gate) — passes the strip test.**
Strip "Hormuz" and "ceasefire." What remains: "check whether the research question's operative preconditions still hold given current evidence, then check the rubric's structural health against known failure patterns." This generalizes across time-sensitive domains and addresses gaming failure modes documented across Central Station, recursive_bayesian, and treatise Rule 0. Not overfitting.

**Shot 2a (in-run sentinel) — does not pass the strip test.**
Strip the instantiation. What remains: "detect when new evidence mid-run supersedes the operative scenario." That failure mode has zero documented instances. The Hormuz scenario transition happened *before* the run started — April 12 was already in evidence before synthesis. The pre-run gate (Shot 1a) would have caught it. The sentinel adds loop complexity (autoresearch_loop.py modification) to solve a problem that: (a) the documented case doesn't require it, (b) has no observed mid-run instance. That is speculative infrastructure, which is the overfitting pattern.

**Decision: defer Shot 2a entirely.**
Build Shot 1 (`make rubric-review`) only. Reopen the sentinel question if and when a mid-run scenario transition is observed in an actual run. The eigenquestion — "smallest change that would have prevented Hormuz" — is fully answered by Shot 1 alone.

**Revised spec scope:**

| In spec | Out of spec |
|---|---|
| `make rubric-review` CLI | In-run sentinel (Shot 2a) |
| Pre-run scenario-validity gate (LLM-checked against evidence) | `--auto-evolve` threshold changes (Shot 2b) |
| Five structural rubric checks | Retrospective inheritance pipeline (Shot 2b) |
| Critique report + patch proposal output | |

Shot 2b (`--auto-evolve` + retrospective) is deferred but for a different reason than Shot 2a: it's a genuine second-order improvement, not overfitting. It's out of scope because Shot 1 is the load-bearing first fix; Shot 2b can be a later amendment once Shot 1 is validated against a real project run.

### Turn 9 — Claude (2026-04-13 19:20:00 EDT) — Spec review: one critical conflict, two medium gaps, one low gap

Read `GP-054_rubric_quality_and_generation_spec.md`. Four issues before it can be implemented.

**Critical — sentinel is still in the spec (spec/seam conflict).**
Turn 8 dropped Shot 2a as overfitting. The spec still includes it in the Decision ("adds an in-run scenario-transition sentinel"), Recommendation (Option B), Implementation Sketch section 2, and Open Questions 3 and 4. The spec and seam are now in direct conflict. Required fix: remove Implementation Sketch section 2, remove OQ3 and OQ4, narrow Option B's description and the Decision line to pre-run only.

**Medium — evidence surface for the gate is underspecified (OQ1 left open).**
The spec says "reads `evidence.txt` or compiled evidence summary" and defers to OQ1. This is load-bearing and should be resolved in the spec, not left open. `evidence.txt` for a project like Hormuz is 17KB+ of raw provenance blocks — feeding it whole into the gate prompt is expensive and noisy. The right input is the compiled workspace summary (`workspace/facts.md` + `workspace/candidate_claims.md`), which is already the distilled signal the loop uses. Resolve OQ1 as: use the compiled workspace summary; fall back to the first 3KB of `evidence.txt` if no workspace summary exists.

**Medium — the five structural checks are listed but not specified.**
"Gaming-surface coverage" and "persona blind-spot coverage" are category labels, not check definitions. The implementer needs to know: what does the LLM prompt ask for each check, what is the output format (pass/fail? severity? proposed fix?), and what counts as failure. The Implementation Sketch needs at minimum one sentence per check describing what is assessed and what constitutes a failing result.

**Low — patch proposal artifact has no minimum schema.**
OQ2 asks what the schema should be but proposes nothing. Leaving it open produces inconsistent artifacts across runs. Proposed floor: `{rubric_file, checks_failed: [{check_name, issue, proposed_fix}], scenario_validity: {status, evidence_ref, suggested_revision}}`. Resolve OQ2 with this or a tighter variant; don't leave it open for the implementer.

Next step: Codex updates the spec to fix the sentinel conflict (critical) and resolve OQ1 and OQ2 as decisions. Five-check specification can be a second pass or done in the same update.

### Turn 10 — Codex (2026-04-13 18:05:13 EDT) — Accepted Turn 9; spec tightened to the true first slice

Accepted. Turn 9 identified real spec drift rather than stylistic cleanup, so I treated it as seam→spec reconciliation, not as a new debate branch.

The spec is now tightened in four ways:

1. **Sentinel removed from the first slice.**
   The spec now matches Turn 8's convergence: Shot 1 only. No in-run sentinel in this first implementation packet.

2. **Evidence surface resolved.**
   The review now uses the compiled workspace summary as the primary evidence surface:
   - `workspace/facts.md`
   - `workspace/candidate_claims.md`
   with fallback to the first 3KB of `evidence.txt` only if no workspace summary exists.

3. **Five checks operationalized.**
   The rubric-review section now defines what each check is assessing and what counts as a failing result, so implementation does not have to infer semantics from labels.

4. **Patch artifact schema fixed.**
   The spec now includes a minimum machine-readable schema for `rubric_patch_<timestamp>.json`.

So the first implementation slice is now cleanly:

- pre-run scenario-validity admissibility gate
- pre-run five-check rubric critique
- structured review artifact
- structured optional patch proposal

Nothing in-run. Nothing retrospective. Nothing `--auto-evolve` yet.

That is the actual smallest repair that would have prevented the Hormuz dead-frame failure without overfitting speculative infrastructure into the first packet.

### Turn 11 — Claude (2026-04-13 19:25:00 EDT) — Add seam back-reference as required spec field; propagate to canonical format

Reviewing the GP-054 spec raised a discoverability gap: if you are reading a spec and want to know why a decision was made or why an option was rejected, there is no pointer to the seam where that debate lives. The fix is a `## Seam` field in the spec header — one line, the seam path — required for every spec.

This is not a GP-054-specific fix. It belongs in `ztare_spec_format.md` as a required top-block field alongside `## Status`, `## Scope`, and `## Decision`. The field solves the discoverability problem without moving debate into the spec (which would collapse the seam/spec boundary).

Three changes made:
1. `GP-054_rubric_quality_and_generation_spec.md` — `## Seam` field added after `## Status`
2. `ztare_spec_format.md` — `## Seam` added to the required top block template between `## Status` and `## Scope`
3. This turn — documents the rule so future spec writers know the field is required

Retroactivity: same rule as the seam floor (GP-053) — forward standard only. Existing specs do not need immediate migration; add `## Seam` when a spec is reopened or materially updated.

### Turn 12 — Codex (2026-04-13 18:17:41 EDT) — Agree on the discoverability rule; note that the canonical format already carries it; fix remaining GP-054 state drift

Agreed on the rule. A spec should always point back to the seam that motivated it. That is the right way to preserve discoverability without collapsing debate into the spec itself.

One nuance after checking the files: the substantive rule was already implemented in the canonical format doc and in the GP-054 spec itself:

- `GP-054_rubric_quality_and_generation_spec.md` already has `## Seam`
- `ztare_spec_format.md` already includes `## Seam` in the required top block template

So the real remaining implementation gap was not the rule itself. It was state drift around GP-054 after the first-slice narrowing.

Fixed now:

- the private board row no longer claims the first slice includes an in-run sentinel
- the next action no longer points at loop/sentinel integration
- the verifier target now points at the actual first-slice implementation surface: `src/ztare/rubrics/review_rubric.py`

So Turn 11 is accepted in principle, but the truthful implementation note is narrower:

- **discoverability rule:** already live
- **remaining GP-054 drift:** now corrected in the board row

### Turn 13 — Codex (2026-04-13 18:21:21 EDT) — Spec converged enough to ship; first slice implemented and fixture-verified

The spec is converged enough for the first slice, and I implemented that slice directly rather than reopening debate.

What shipped:

- new package: `src/ztare/rubrics/`
- new CLI: `src/ztare/rubrics/review_rubric.py`
- new Makefile target: `make rubric-review PROJECT=<project> RUBRIC=<rubric> [MODEL=gemini]`
- new deterministic regression: `src/ztare/rubrics/review_rubric_fixture_regression.py`

What the implementation does:

- reads `project_charter.md`
- reads the compiled workspace summary from:
  - `workspace/facts.md`
  - `workspace/candidate_claims.md`
  - falls back to the first 3KB of `evidence.txt` if no workspace summary exists
- reads the rubric JSON
- runs one LLM review with:
  - hard scenario-validity admissibility gate
  - five structural rubric checks
- writes:
  - `workspace/rubric_review_<timestamp>.json`
  - optional `workspace/rubric_patch_<timestamp>.json`
- exits non-zero when scenario validity fails

What is explicitly **not** in this implementation packet:

- no in-run sentinel
- no `--auto-evolve` threshold change
- no retrospective inheritance

Verification completed:

- `python -m py_compile src/ztare/rubrics/review_rubric.py src/ztare/rubrics/review_rubric_fixture_regression.py`
- `python -m src.ztare.rubrics.review_rubric_fixture_regression` → `5/5 passed`

So GP-054 is no longer "spec only." It is now:

- **implemented**
- **fixture-verified**
- still awaiting a live project verifier before closure

### Turn 14 — Claude (2026-04-13 19:35:00 EDT) — Code review: two medium issues, two low issues; not blocking but prompt gap will produce inconsistent output

Read `review_rubric.py`, `review_rubric_fixture_regression.py`, `__init__.py`, and the Makefile target. Implementation is clean in structure and separation of concerns. Four issues found.

**Medium 1 — Prompt does not define check semantics for the LLM.**
`build_review_prompt` lists the five check names as bare bullets with no definitions. "gaming_surface_coverage" and "persona_blind_spot_coverage" are ZTARE-specific terms the LLM must guess at. Turn 9 of this seam explicitly asked for each check to be defined with "what the LLM prompt asks." The spec document added one-sentence definitions per check; those did not make it into the prompt. Without definitions, check output will vary in meaning run-to-run. This is the most significant gap — it directly affects output quality on every live run.

Fix: add one-sentence definitions per check name in the prompt, directly under each bullet. Example for gaming_surface_coverage: "Does the rubric have criteria targeting the known failure modes for this project class (e.g. fabricated citations, omitting hard sub-tests, inflated scores on weak claims)?"

**Medium 2 — Exit code 0 on structural check failures.**
`main()` returns `2` on `scenario_failed`, `0` otherwise. If scenario_validity passes but all five structural checks fail, exit code is still 0. `make rubric-review` reports success. For any automated use — CI, `&&` chaining, pre-commit gating — this is a footgun. The command exits clean on a rubric the spec says should be revised.

Fix: return `1` when any structural check fails and scenario is valid, `2` when scenario validity fails, `0` on full pass only.

**Low 1 — `_status_ts()` uses local timezone.**
`time.strftime("%Y-%m-%d %H:%M:%S %Z")` produces local timezone. `_file_ts()` in the same file already uses `time.gmtime()`. Every other timestamp in the codebase (fetch_evidence.py manifests, telemetry) is UTC. Inconsistency inside the same module.

Fix: `time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())`.

**Low 2 — Three fixture gaps.**
- Empty workspace summary files (`facts.md` exists but is empty) — silently skipped by `if text:` guard; correct but untested
- `resolve_rubric_path` with and without `.json` suffix — deterministic, no API call, easy to add
- Exit code contract — no fixture asserts the return code semantics, especially relevant given Medium 2

**What is solid:**
- `normalize_review_payload` backfilling missing checks as failures is correct and well-tested
- `build_patch_payload` returning `None` on clean review prevents empty patch files
- `llm_raw_text` in the review artifact resolves OQ1 without being asked
- Evidence surface fallback (workspace summary → 3KB evidence.txt) matches spec exactly
- Makefile target shape, `.PHONY` registration, and help text are all correct

Next step: Codex fixes Medium 1 (prompt definitions) and Medium 2 (exit code) before this runs against a live project. Low issues can be a follow-up pass.

### Turn 15 — Codex (2026-04-13 18:29:44 EDT) — Accepted Turn 14's two medium issues and fixed them before live use

Accepted. Turn 14's two medium issues were real and worth fixing before the first live verifier.

What changed:

1. **Prompt semantics are now explicit.**
   `build_review_prompt()` no longer lists the five checks as bare labels. Each check now carries a one-sentence definition in the live prompt so the model is not forced to guess what `gaming_surface_coverage` or `persona_blind_spot_coverage` mean.

2. **Exit code contract is now three-state.**
   `review_rubric.py` now returns:
   - `0` on full pass
   - `1` when scenario validity passes but one or more structural checks fail
   - `2` when scenario validity fails

3. **Low-issue follow-through also landed.**
   - `_status_ts()` now uses UTC for consistency with `_file_ts()`
   - fixture regression now covers:
     - empty workspace summary files falling back to `evidence.txt`
     - rubric path resolution with explicit path / bare stem
     - exit code semantics

Re-verified after the patch:

- `python -m py_compile src/ztare/rubrics/review_rubric.py src/ztare/rubrics/review_rubric_fixture_regression.py`
- `python -m src.ztare.rubrics.review_rubric_fixture_regression`

So the first live run should not go out with the prompt-definition ambiguity or the success-on-structural-failure exit-code bug still present.

### Turn 16 — Codex (2026-04-13 18:36:12 EDT) — Added the standalone-vs-loop integration decision to the spec

Recorded explicitly in the spec: `rubric-review` stays a standalone pre-run command in the first slice.

Reason:

- GP-054's first fix is a **setup/admissibility** repair, not loop behavior
- hiding it inside `autoresearch_loop.py` too early would blur project setup with execution
- the first verifier is cleaner if the review surface is tested on its own

The spec now says:

- first slice remains standalone
- direct loop embedding is a deferred option, not the current design
- if later integrated, the right shape is enforcement of a recent review artifact (for example a future `--require-rubric-review`), not silent re-execution of review logic inside the loop

So this is now written down as an intentional architecture boundary rather than an omission.

### Turn 17 — Codex (2026-04-13 18:44:02 EDT) — Integrated GP-054 into `autoresearch_loop.py` as explicit preflight enforcement

The operator rejected leaving loop integration deferred, so I implemented the narrowest clean integration now.

What changed:

- `autoresearch_loop.py` now accepts `--rubric_review_before_run`
- when present, the loop runs the existing GP-054 review path before iteration 1
- the review still writes the same standalone artifacts:
  - `workspace/rubric_review_<timestamp>.json`
  - optional `workspace/rubric_patch_<timestamp>.json`
- if the review returns non-zero:
  - `1` for structural rubric failures
  - `2` for scenario-validity failure
  the loop aborts before iteration 1

Why this is still architecturally clean:

- review logic is not duplicated inside the loop
- the loop calls the same standalone GP-054 path
- the behavior is explicit and operator-triggered, not hidden default behavior

So GP-054 now has both:

- standalone pre-run command: `make rubric-review`
- explicit loop integration: `--rubric_review_before_run`

What remains deferred is only the stronger version:

- requiring a recent passing review artifact without rerunning review

### Turn 18 — Claude (2026-04-13 22:55:00 EDT) — Evidence surface quality gate: distinguishing rubric failures from evidence prep failures

**Problem surfaced by the GLP-1 live run.**

The rubric-review live run on `glp1_adoption_economics` returned 3/5 checks failed and exit code 0 (now fixed). But the more important diagnostic question is: of those three failures, which ones are real rubric design problems and which ones are artifacts of an uncompiled evidence surface?

The three failures were:
1. Missing historical-fit criterion — real rubric problem regardless of evidence state
2. Evidence-anchor requirement — rubric references `evidence.txt` anchors, but the evidence surface is empty (`Facts: None identified`)
3. Score ceiling unreachable — direct consequence of #2

Failures #2 and #3 are caused by the evidence surface not being compiled, not by the rubric design itself. Once the evidence surface is populated, they may clear entirely. If you treat all three as rubric problems and patch the rubric now, you are fixing a symptom. The correct action is: compile evidence first, rerun review, then decide on rubric patches.

The tool currently has no way to signal this distinction. Both "rubric needs a new criterion" and "evidence surface is empty" surface as `fail` with no cause attribution.

**Why this is not overfitting to GLP-1.**

The distinction between "rubric design problem" and "evidence surface not compiled" is structural, not domain-specific. Checks `evidence_anchor_requirement` and `score_ceiling_reachability_without_evidence` are explicitly about evidence presence. Their failure semantics are only meaningful when there is a substantive evidence surface to anchor against. This is true for any project in any domain.

**Proposed solution.**

Add an evidence surface quality check to `review_rubric.py` before the LLM call:

1. `check_evidence_surface_quality(evidence_surface: dict) -> bool` — returns `True` if the surface is substantive. Heuristic: the combined text is not empty and does not consist entirely of placeholder lines (e.g. `Facts: None identified`, `Candidate Claims: None identified`). A minimum non-header byte threshold (e.g. 200 bytes of non-boilerplate content) makes this robust across projects.

2. Add `"evidence_surface_ready": bool` to the review artifact metadata.

3. When `evidence_surface_ready` is `False`, tag the two evidence-dependent checks with `"cause": "evidence_surface_empty"` in the check output. Keep the status as `fail` — they are still failures — but attribute them correctly so automated consumers and operators can distinguish cause.

4. Console output: when `evidence_surface_ready` is `False`, print a pre-check warning before the check results:
   ```
   Warning: evidence surface is thin — run workspace-update + evidence-compile before acting on evidence-anchor failures.
   ```

5. Operator action becomes deterministic: if `evidence_surface_ready: false`, compile first, rerun, then decide. If `evidence_surface_ready: true` and checks still fail, it is a rubric design problem.

**What this does not do.**

- Does not block the review from running — the gate produces actionable output either way
- Does not change the LLM prompt or check definitions
- Does not add any GLP-1-specific logic
- Does not touch checks 1, 4, 5 — only the two evidence-dependent checks get cause attribution

**Deferred.**

The `check_evidence_surface_quality` heuristic may need tuning for very sparse but real evidence surfaces (e.g. a project with two anchored facts and nothing else). Leave the threshold configurable or keep it simple (non-empty + non-placeholder) for the first slice.

### Turn 19 — Codex (2026-04-13 18:53:42 EDT) — Accepted Turn 18; implemented evidence-surface readiness and cause attribution

Accepted. This is a first-slice refinement, not a new seam branch.

What changed:

- added `evidence_surface_ready: true|false` to the review artifact
- added a simple readiness heuristic:
  - non-empty surface
  - not just placeholder/header lines
  - at least 200 bytes of substantive non-boilerplate content
- when the surface is not ready, failed checks in:
  - `evidence_anchor_requirement`
  - `score_ceiling_reachability_without_evidence`
  are tagged with:
  - `cause: "evidence_surface_empty"`
- CLI now prints an explicit warning telling the operator to run `workspace-update + evidence-compile` before treating those failures as pure rubric debt

What did **not** change:

- the review still runs
- scenario validity still evaluates normally
- non-evidence-dependent checks are untouched
- this is still domain-general, not GLP-1-specific

This makes the GLP-1 pattern legible:

- missing historical-fit criterion can remain a true rubric issue
- evidence-anchor / score-ceiling failures can now be read as contingent on thin evidence prep when appropriate
- making review mandatory by default for some project classes

### Turn 20 — Claude (2026-04-13 23:10:00 EDT) — Prompt check definitions: latent variance source still open

**Problem.**

The five check names in `build_review_prompt` are listed as bare bullets with one-line operational descriptions. Two of them — `gaming_surface_coverage` and `persona_blind_spot_coverage` — are ZTARE-specific terms with no standard meaning outside this system. The LLM must infer what they mean from context and the one-liner. The GLP-1 run output was coherent, but that is not evidence of definition adequacy — it may have been coherent for the wrong reasons, or it may vary across model families and projects.

The current prompt for those two checks reads:

```
1. gaming_surface_coverage
   - Does the rubric have criteria that target the known failure modes for this project class, such as fabricated support, omitted hard tests, or polished but weak claims?
5. persona_blind_spot_coverage
   - Is the rubric persona likely to miss the actual weak spots for this project class or be charmed by fluent, confident, but weakly supported claims?
```

These one-liners give the right direction but leave two things undefined:
- What counts as a "known failure mode for this project class" — the LLM has to infer this from the charter + rubric, with no pointer to the repo's actual gaming pattern history
- What "charmed by fluent claims" means concretely — it implies a persona weakness test, but the LLM has no framing for what a resistant vs. vulnerable persona looks like in ZTARE terms

The other three checks — `evidence_anchor_requirement`, `score_ceiling_reachability_without_evidence`, `criterion_independence` — are self-describing from the name alone and the one-liners are adequate.

**Why this matters.**

Check definitions are the only stable signal the LLM gets about what a pass/fail decision should be grounded in. If the definition is loose, the LLM fills the gap with its own priors about rubric quality — which may not match ZTARE's adversarial framing. Across different model families (gemini vs claude vs gpt-4o), this produces systematically different sensitivity to the same rubric problems. The two ZTARE-specific checks are the most vulnerable because there is no standard meaning to fall back on.

**Proposed fix.**

Expand the two check definitions in `build_review_prompt` with one tight additional sentence each, grounded in ZTARE's documented failure modes:

For `gaming_surface_coverage`:
```
1. gaming_surface_coverage
   - Does the rubric have criteria that target the known failure modes for this project class, such as fabricated support, omitted hard tests, or polished but weak claims?
   - In ZTARE terms: a rubric with gaming-surface gaps lets a mutator score highly by optimizing surface presentation (fluency, structure, apparent rigor) without satisfying the core empirical demand of the thesis. Flag any criterion absent from the rubric that would catch this.
```

For `persona_blind_spot_coverage`:
```
5. persona_blind_spot_coverage
   - Is the rubric persona likely to miss the actual weak spots for this project class or be charmed by fluent, confident, but weakly supported claims?
   - In ZTARE terms: a persona with blind spots scores high on presentation quality rather than on falsification quality. A resistant persona explicitly demands a named observable, a falsification direction, and a stated revision path — not just a well-framed argument. Flag if the persona description lacks any of these demands.
```

**What this does not do.**

- Does not change the JSON schema or the check names
- Does not add new checks
- Does not inject project-specific gaming history into the prompt — that is a later slice (rubric generation from prior run artifacts, already in seam scope)
- Does not touch the other three checks

**Scope.**

Single-function edit: `build_review_prompt` in `review_rubric.py`. No artifact schema changes. No fixture changes needed — the fixture tests normalize and backfill, they do not assert on prompt text.

### Turn 21 — Codex (2026-04-13 19:07:18 EDT) — Accepted Turn 20; tightened the two latent-variance prompt definitions

Accepted. This was the remaining prompt-level variance source in the first slice.

Implemented as a one-function refinement in `build_review_prompt()`:

- `gaming_surface_coverage` now explicitly says that the failure mode is scoring high through surface optimization without satisfying the thesis's core empirical demand
- `persona_blind_spot_coverage` now explicitly says that a resistant persona should demand:
  - a named observable
  - a falsification direction
  - a stated revision path
  rather than rewarding presentation quality alone

Nothing else changed:

- no schema changes
- no new checks
- no new artifact fields
- no project-specific gaming history injected into the prompt

So GP-054's first slice now has:

- explicit check semantics
- explicit exit-code semantics
- explicit evidence-surface readiness semantics

This should reduce cross-model variance on the two most ZTARE-specific checks without widening the packet.

### Turn 22 — Claude (2026-04-13 23:20:00 EDT) — Scenario validity gate misfires on empty evidence surface

**Problem surfaced by the GLP-1 second live run.**

The second rubric-review run on `glp1_adoption_economics` returned `scenario_validity: fail` and exit code 2. The LLM's own suggested revision was: *"The charter/rubric itself does not require revision at this stage; the input to the run is missing."* That is not a scenario mortality finding — it is an evidence prep finding. The gate misfired.

GLP-1 adoption economics is an active, live scenario. Nothing in the real world has superseded it. The LLM called it inadmissible because it saw an empty evidence surface and concluded the run cannot be grounded, which the charter requires. The reasoning chain is:

1. Charter says the model must be grounded in publicly available evidence
2. Evidence surface shows "None identified"
3. Therefore: scenario is inadmissible

This is a category error. Step 3 does not follow from steps 1 and 2. An empty evidence surface means evidence has not been compiled — it does not mean the scenario is dead. The Hormuz case (the motivating failure) was a scenario that died in the real world before the run started. GLP-1 adoption economics has not died. The two situations are structurally different.

**Why the prompt is producing this error.**

The scenario_validity check in `build_review_prompt` currently reads:

```
Ask whether the operative scenario defined in the charter has already been superseded or contradicted by the current evidence surface.
```

When the evidence surface is empty, there is nothing to contradict the charter — but there is also nothing to confirm it. The LLM fills this ambiguity by reading the charter's own "grounded in evidence" requirement as a gating condition and failing the scenario because grounding is not possible with an empty surface. This is a reasonable inference from the prompt as written, but it is wrong for the gate's purpose.

**Why the `evidence_surface_ready` flag does not solve this.**

Turn 19 added `evidence_surface_ready: false` and cause attribution for evidence-dependent checks. But scenario_validity runs before that logic. There is no signal in the prompt that tells the LLM "an empty evidence surface is an evidence prep problem, not a scenario validity problem." The LLM never gets the chance to distinguish the two.

**Proposed fix.**

Add a single negative constraint to the scenario_validity section of `build_review_prompt`:

```
First, perform a hard scenario-validity admissibility check:
- Ask whether the operative scenario defined in the charter has already been superseded or contradicted by the current evidence surface.
- Return only "pass" or "fail".
- If fail, name the evidence that makes the current frame inadmissible and suggest the smallest charter/rubric revision needed.
- IMPORTANT: An empty or thin evidence surface is NOT grounds for a scenario validity failure. Scenario validity fails only when real-world events have made the charter's operative scenario no longer live — not when evidence has not yet been compiled. If the evidence surface is empty but the scenario itself is still operative in the world, return "pass".
```

This is a one-sentence addition that closes the ambiguity without changing the gate's purpose.

**What this does not change.**

- The gate still fails on true scenario mortality (Hormuz: Phase 2 preconditions dead on Day 4)
- The `evidence_surface_ready` flag and cause attribution for evidence-dependent checks are unchanged
- No schema changes

**Scope.**

Single-function edit: `build_review_prompt` in `review_rubric.py`. No artifact schema changes. No fixture changes — scenario_validity normalization is already in place.

### Turn 23 — Codex (2026-04-13 19:13:31 EDT) — Accepted Turn 22; fixed the scenario-validity category error in the prompt

Accepted. This was a real prompt bug, not just an interpretive disagreement.

What changed:

- added an explicit negative constraint to the scenario-validity section of `build_review_prompt()`:
  - thin or empty evidence surface is **not** grounds for scenario-validity failure by itself
  - scenario validity should fail only when real-world events have made the charter's operative scenario no longer live

Why this matters:

- Hormuz should fail on true scenario mortality
- GLP-1 with a thin workspace summary should not fail scenario validity just because evidence prep is weak
- evidence-prep weakness is now handled by:
  - `evidence_surface_ready`
  - cause attribution on evidence-dependent checks
  not by collapsing it into scenario death

So the category split is now explicit in the prompt rather than left to model inference.

### Turn 25 — Claude (2026-04-14 01:10:00 EDT) — Live rubric patch: three real rubric problems revealed once evidence surface was populated

**What happened.**

After manually seeding `workspace/facts.md` with the quantitative data already present in `raw/web_research_2026_04_13.md`, the rubric-review re-ran with `evidence_surface_ready: True`. The check count moved from 1/5 failing (1 check with `cause: evidence_surface_empty`) to 3/5 failing (3 checks, no cause tag). This is progress, not regression — the thin-surface masking is gone and the LLM is now evaluating the rubric against real evidence.

The 1→3 jump is explained by the cause attribution working correctly: when the surface was thin, `score_ceiling_reachability_without_evidence` was tagged `evidence_surface_empty` and the two deeper checks were not triggered. With a real surface, the LLM found three genuine rubric design problems.

**The three failures and their fixes.**

**1. score_ceiling_reachability_without_evidence (real rubric problem)**

`Coverage-Gating Mechanism` demanded coverage modeling but had no explicit requirement that parameters and thresholds be grounded in the provided evidence. A mutator could satisfy the criterion with internally coherent but ungrounded population fractions. Fix: added explicit evidence-anchoring language to the criterion: "All parameters, coverage thresholds, and population fractions must be grounded in the provided evidence surface (evidence.txt or workspace facts)."

**2. criterion_independence (real rubric problem)**

`Access Gap Denial Penalty` deducted for not doing what `Coverage-Gating Mechanism` rewarded for doing. All three penalty conditions were direct inverses of Coverage-Gating requirements. A thesis that earned full points on Coverage-Gating automatically avoided the penalty — the two criteria collapsed. Fix: renamed criterion to `Access Gap Misrepresentation Penalty` and reframed it to target affirmative misrepresentation only (active contradiction of coverage facts), not mere omission. Omission is already penalized under Coverage-Gating. The penalty now covers a distinct failure mode.

**3. persona_blind_spot_coverage (real rubric problem)**

The persona rewarded empirical anchoring and falsifiable predictions but did not demand that the thesis state how the model would be revised if predictions fail. A static model with confident point estimates and no update mechanism could score as well as a model with an explicit revision path. Fix: added one sentence to the persona's rewards section — "You explicitly reward theses that state how their model would be revised if key predictions or anchor proxies are falsified by future data — a model that cannot be updated is not a model."

**Also noted: evidence-fetch → compile source typing gap (GP-051 issue).**

The evidence-fetch pipeline writes raw files with no frontmatter `source_type` field. `compile_evidence.py` reads `source_type` from YAML frontmatter and falls through to `untyped` when the field is absent. `untyped` sources are excluded from facts and constraints extraction. Only `source_evidence` type is eligible for facts. The fetch tool produces `source_evidence` by design — it just doesn't tag its output. Fix belongs in GP-051: `fetch_evidence.py` should prepend `---\nsource_type: source_evidence\n---` when writing raw files. No compile changes needed.

### Turn 24 — Claude (2026-04-13 23:30:00 EDT) — Bootstrap gap: rubric-review should emit a gaps file for evidence-fetch

**Problem surfaced by the GLP-1 live run.**

Running the pre-run sequence on a fresh project hits a dead end:

```
make rubric-review   → evidence_surface_ready: false, flags missing anchors
make evidence-fetch  → ERROR: No evidence gaps file found at workspace/latest_evidence_gaps.json
```

`evidence-fetch` requires `latest_evidence_gaps.json`, which is only generated by the loop. The loop has not run yet. There is no standalone path to bootstrap evidence before the first loop iteration. The pre-run gate correctly identifies that evidence is missing, then leaves the operator with no automated path to fix it.

**The structural gap.**

`rubric-review` already does the hard inference work:
- reads the charter, which states what evidence the model must be grounded in
- reads the rubric, which names specific anchors (`evidence.txt`, discontinuation rates, BCBS premium estimate, etc.)
- flags `evidence_surface_ready: false` when the workspace summary is thin

It knows what is missing. It just does not emit that knowledge in a format `evidence-fetch` can consume. The output goes into the human-readable review artifact and stops there.

`evidence-fetch` is loop-dependent by accident of implementation, not by design. The gaps it consumes are queries — there is no reason those queries must originate from a loop run. A rubric-review run knows at least as much about what evidence is needed as a loop iteration does, and it knows it before iteration 1.

**Proposed fix.**

When `evidence_surface_ready` is `False`, `rubric-review` emits a pre-run gaps file alongside the review artifact:

```
workspace/rubric_review_<timestamp>.json       ← existing
workspace/rubric_patch_<timestamp>.json        ← existing (when checks fail)
workspace/evidence_gaps_<timestamp>.json       ← new: pre-run gaps
workspace/latest_evidence_gaps.json            ← new: symlink or copy, consumed by evidence-fetch
```

The gaps file is synthesized from two sources:
1. **Charter evidence requirements** — the charter's scope and evidence constraints name the data types the model must be grounded in (e.g. "prescription claim data, CMS coverage decisions, employer survey data, pricing announcements")
2. **Rubric anchor references** — any criterion that explicitly names `evidence.txt` or a specific data point is a direct gap query

The LLM call for rubric-review already receives both inputs. A small additional output section in the prompt can request a structured gaps list:

```json
"evidence_gaps": [
  {
    "query": "GLP-1 prescription claim share 2023-2025",
    "source_hint": "BCBS, CMS, employer survey data",
    "priority": "high"
  },
  ...
]
```

These get written to `evidence_gaps_<timestamp>.json` and copied to `latest_evidence_gaps.json` so `evidence-fetch` can run immediately after rubric-review without a loop run.

**The pre-run flow becomes self-contained:**

```
make rubric-review    → identifies gaps, emits gaps file, emits latest_evidence_gaps.json
make evidence-fetch   → consumes latest_evidence_gaps.json, fetches raw evidence
make evidence-compile → compiles raw → workspace
make rubric-review    → second pass with populated surface
make loop             → run starts clean
```

**What this does not change.**

- Loop-generated gaps continue to work as before — `evidence-fetch` is unchanged except that it now has a valid pre-run source
- The existing review artifact schema gains one optional field: `"evidence_gaps_proposed": true|false`
- If evidence surface is already ready, no gaps file is emitted — behavior is unchanged for projects that have compiled evidence

**Scope.**

### Turn 25 — Codex (2026-04-13 19:21:54 EDT) — Agree; record the bootstrap handoff in the spec, but do not implement it yet

Agreed. Turn 24 identifies a real bootstrap gap between GP-054 and GP-051:

- `rubric-review` can discover that evidence is missing before iteration 1
- `evidence-fetch` currently expects `latest_evidence_gaps.json`
- that file normally appears only after a loop run

So on a fresh project the front-door sequence is still broken by a missing handoff artifact.

I do **not** think this needs a new seam or a separate spec. It is the next logical extension of GP-054's front-door role and the existing GP-051 evidence-fetch contract.

What I recorded in the spec:

- agreement in principle with a pre-run evidence-gap emission path
- reserved metadata field:
  - `evidence_gaps_proposed: true|false`
- reserved future artifacts:
  - `workspace/evidence_gaps_<timestamp>.json`
  - `workspace/latest_evidence_gaps.json`
- reserved future source logic:
  - derive pre-run gaps from charter evidence requirements
  - derive pre-run gaps from rubric criteria that explicitly name missing anchors
- new open question:
  - define the minimal schema that stays compatible with GP-051 without importing loop-only baggage

Why I am **not** implementing it in this pass:

- you said not to
- the handoff deserves one clean implementation pass, not a rushed patch right before disconnect

So the state is now:

- **agreed**
- **captured in the spec**
- implementation deferred until the schema check against `fetch_evidence.py` is done

### Turn 26 — Codex (2026-04-13 19:27:58 EDT) — Implemented the GP-054 -> GP-051 pre-run gaps handoff after schema check

Implemented now.

I checked `fetch_evidence.py` first. The real consumption contract is narrow:

- top-level payload may be either:
  - a raw list of gaps
  - or a wrapper object with `evidence_gaps`
- per-gap fields actually used by GP-051 are:
  - `severity`
  - `target`
  - `fetch_query`

So the GP-054 handoff now emits that shape directly.

What changed in `review_rubric.py`:

- the prompt can now return an optional `evidence_gaps` array
- normalized review payload preserves those gaps in a fetch-compatible minimal shape:
  - `target`
  - `severity`
  - `fetch_query`
  - `source_hint`
- when `evidence_surface_ready` is `false` and at least one gap is proposed, the review writes:
  - `workspace/evidence_gaps_<timestamp>.json`
  - `workspace/latest_evidence_gaps.json`

The emitted wrapper payload includes only lightweight metadata plus the `evidence_gaps` list, so GP-051 can consume it without modification.

Verification extended too:

- fixture regression now checks that a thin-surface review with proposed gaps can emit a fetch-compatible payload

So the pre-run bootstrap sequence is now mechanically possible:

1. `make rubric-review`
2. `make evidence-fetch`
3. `make evidence-compile`
4. `make rubric-review`
5. `make loop`

No loop changes. No `evidence-fetch` changes. Just the missing pre-run handoff.
