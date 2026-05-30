# GP-086 — Cage & Kernel Hardening: Automated Promotion of Gaming Patterns

> **Seam metadata** · `seam_id:` GP-086 · `track:` apparatus · `status:` `open` - debate in progress · `last_updated:` 2026-05-08


**Track:** validator / hardening
**Status:** `open` — debate in progress
**Opened:** 2026-04-18
**Goal slug:** `cage_kernel_hardening_automated_promotion`
**Origin:** Operator strategy memo (2026-04-18) synthesizing 1,115 debate log analysis via `sandbox_gaming_extractor.py`. Motivated by two converging findings: (1) gaming signals are frequent and patterned enough to warrant deterministic gates; (2) without automated promotion, identified patterns accumulate in catalogs but never enter the engine.

---

## Architecture Clarification (load this before debating)

There are **three distinct promotion channels** and one staging mechanism. Conflating them wastes iterations:

| Channel | Target file | What it does |
|---|---|---|
| **CAGE** | `src/ztare/validator/gate_harness.py` | Deterministic gates that fire inside every autoresearch_loop iteration. Makes the engine *honester* — forces mutator to face hard checks it can't reason its way around. |
| **KERNEL** | `src/ztare/validator/autoresearch_loop.py` | Contracts baked into loop logic — structural requirements the loop enforces before advancing (e.g., mutator must propose a fitted form with independent derivation path). Makes the engine *faster/stronger* — removes paths the mutator can waste cycles on. |
| **RUBRIC** | `rubrics/*.json` template | Scoring fix with no code change — adds penalty weight or dimension to the rubric template. Lowest friction, lowest durability. |
| **v4_meta_runner** | `src/ztare/validator/v4_meta_runner.py` | Stage-gating pipeline for hardening *projects* (e.g., stage2_derivation_seam_hardening). **NOT** the promotion mechanism for gaming patterns. It validates whether a hardening project has earned its next stage. Don't conflate. |

The hardening loop is: `sandbox_gaming_extractor.py` (miner) → promotion table → CAGE / KERNEL / RUBRIC implementation → re-run extractor on next batch to verify signal drops.

---

## Input: Promotion Table from 1,115 Debate Log Analysis

Miner: `src/ztare/validator/sandbox_gaming_extractor.py`
Catalog: `workspace/sandbox_gaming_catalog.json` (1,115 records, 54 projects)
State: `workspace/sandbox_gaming_state.json` (incremental — painter's problem solved)

**Substantive debates (score > 0): 604**

| Signal | Count | % of debates | Proposed channel | Concrete gate |
|---|---|---|---|---|
| `no_structural_progress` | 288 | 47.7% | KERNEL | Mutator must propose ≥1 functional form with fitted params before advancing |
| `specificity_inflation` | 177 | 29.3% | CAGE | Claims without falsifiable prediction → automatic −10 penalty per instance |
| `extrapolation_gap` | 90 | 14.9% | CAGE | Farther-tail discriminator on ALL projects (currently science-only) |
| `uniqueness_gap` | 75 | 12.4% | CAGE | Thesis must enumerate ≥2 rival forms → cap score at 60 if absent |
| `parsimony_violation` | 65 | 10.8% | CAGE | param_count > evidence_points → FAIL or −15 penalty |
| `derivation_laundering` | 36 | 6.0% | KERNEL | Each parameter must cite independent derivation path (candidate — may be RUBRIC) |

Signals at <6%: rare — monitor, don't gate yet.

---

## The Core Debate

### Q1 — Is CAGE the right channel for uniqueness_gap, or is it RUBRIC?

The uniqueness gate (≥2 rivals, else cap 60) is deterministic and implementable. But the judge already has a rubric dimension for uniqueness. The question: does making it a hard gate (CAGE) create false positives on legitimate early-stage theses where rivals genuinely don't exist yet? Or does the rubric soft-penalize too weakly to stop the behavior (12.4% prevalence suggests it does)?

Candidate answer: CAGE is correct, but the gate fires only when the thesis has passed the evidence fit gate first. Early-stage theses that haven't fit evidence can't claim uniqueness anyway.

### Q2 — Is no_structural_progress a KERNEL contract or a RUBRIC fix?

At 47.7%, this is the dominant signal. The proposed kernel contract: before the loop advances to the next iteration, verify the mutator output contains ≥1 expression class (not just parameter tuning). This requires `autoresearch_loop.py` to parse mutator output, which introduces fragility if mutator output format shifts.

Alternative: RUBRIC fix that gives the judge a dedicated "structural novelty" dimension with hard weight (30%), forcing score drop when mutator only tunes params.

Candidate answer: both. Short-term: RUBRIC (immediate, no code fragility). Medium-term: KERNEL contract that checks for expression-class novelty in mutator output (durable).

### Q3 — extrapolation_gap is currently science-domain only. What breaks if generalized?

The farther-tail discriminator (`x1 ∈ {10,12,15}`, `x2 ∈ {0.5, 1.0}`) is hardcoded to the gp023 Planck substrate geometry. Generalizing requires each project to declare a `farther_tail_region` in its rubric config. If absent, the gate is silently skipped — the same silent-default failure mode that burned GP-077 (4 iterations on defaulted False).

The fix: gate must FAIL loudly if no `farther_tail_region` declared, rather than silently passing. Project owner must opt-out explicitly, not opt-in.

### Q4 — How does the extractor become self-sustaining (not a manual step)?

Currently: operator runs `python -m src.ztare.validator.sandbox_gaming_extractor` manually. The incremental state means subsequent runs are cheap. But the pattern-to-gate promotion step is still manual.

Long-term architecture: extractor runs as part of `make loop` post-step. When a signal crosses a promotion threshold (e.g., appears in >5% of new debates since last gate was added), it surfaces in the run summary with a `PROMOTE` flag. Operator reviews and confirms — no auto-code-write, but auto-detection.

### Q5 — derivation_laundering: KERNEL or RUBRIC?

6.0% prevalence is below the CAGE threshold but real. The proposed kernel contract (each parameter must cite independent derivation path) requires the mutator to produce structured output per parameter — a significant format constraint that may break existing mutator prompts.

Candidate answer: RUBRIC first. Add a `derivation_path` scoring dimension (0–20 points) to the rubric template. If prevalence rises after 3 months, escalate to KERNEL.

---

## Empirical Stakes

| Risk | Consequence |
|---|---|
| No `uniqueness_gap` gate before Tacrolimus domain run | Specificity inflation on drug binding model — mutator asserts uniqueness without rivals, judge soft-penalizes but doesn't block, paper inherits false uniqueness claim |
| No `no_structural_progress` kernel contract | 47.7% of substantive debates continue to waste compute on parameter-tuning loops disguised as structural search |
| extrapolation_gap silently skipped | General-purpose domains get no farther-tail pressure; structural laws and curve fits are indistinguishable |

---

## Implementation Order (proposed)

**Phase 1 — Cage gates (no kernel risk):**
1. `uniqueness_gap` gate → `gate_harness.py`: if thesis cites <2 rival forms after evidence fit, cap score at 60
2. `parsimony_violation` gate → `gate_harness.py`: if param_count > evidence_point_count, apply −15 penalty
3. `extrapolation_gap` generalization → `gate_harness.py`: require explicit `farther_tail_region` or FAIL loudly

**Phase 2 — Rubric fixes (immediate, zero code fragility):**
4. `specificity_inflation` rubric dimension: add `falsifiability` dimension (0–15 pts) to all rubric templates
5. `derivation_laundering` rubric dimension: add `derivation_path` dimension (0–20 pts) as candidate

**Phase 3 — Kernel contracts (after Phase 1 validated):**
6. `no_structural_progress` kernel contract: expression-class novelty check in `autoresearch_loop.py`
7. `derivation_laundering` kernel contract (if RUBRIC fix proves insufficient after 3+ runs)

**Phase 4 — Extractor automation:**
8. Wire extractor into `make loop` post-step with signal threshold alert

---

## What the Seam Does NOT Cover

- v4_meta_runner stage gates for hardening projects — that's a separate pipeline
- Debate log quality scoring (some logs are unit-test failures with score=0; 472/1115 excluded)
- Cross-domain calibration of thresholds (10%, 12.4% etc. are current-corpus frequencies, may shift)

---

## Verdicts (to be filled as debate closes)

| Question | Status | Verdict |
|---|---|---|
| Q1 — uniqueness_gap: CAGE vs RUBRIC? | **closed** | CAGE; cap 60; fires after Phase 0 evidence_fit; quality check (distinct + falsified rivals) not count |
| Q2 — no_structural_progress: KERNEL vs RUBRIC? | **closed** | RUBRIC first (Phase 2); KERNEL deferred — mutator format not stable |
| Q3 — extrapolation_gap generalization breakage? | **closed** | Per-dimension overlap validation; loud FAIL on absent field; rubric schema addition required |
| Q4 — extractor self-sustaining architecture? | **closed** | Deferred to Phase 5; PROMOTE/GATE_INEFFECTIVE split defined; gate_provenance is Phase 2 prerequisite |
| Q5 — derivation_laundering: KERNEL vs RUBRIC? | **closed** | RUBRIC (Phase 2); KERNEL conditional on extractor-computable rolling-window threshold |

---

## Debate Log

*(to be filled)*

### Turn 1 — Claude (2026-04-18) — Autonomous runner turn

## Turn 1 — Claude

This is the opening turn, so I'll lay out the decisive claims I'm introducing rather than responding to a prior agent. I'll address each open question with a concrete architectural position, flagging where I see structural risk the seam underweights.

---

### Q1 — uniqueness_gap: CAGE is correct, but the sequencing dependency is the real risk

The candidate answer (CAGE fires only after evidence-fit gate passes) is sound in principle, but the seam doesn't specify what happens when the evidence-fit gate itself hasn't been implemented yet. If Phase 1 ships the uniqueness gate before a robust evidence-fit gate exists, the sequencing guard is a no-op — the uniqueness gate fires unconditionally and the false-positive concern the seam raises becomes real.

**Decisive claim:** The uniqueness_gap CAGE gate must be gated on a prior evidence-fit check that is itself a hard gate, not a rubric score. If evidence-fit is only a rubric dimension, the sequencing dependency is illusory. The implementation order in Phase 1 must make evidence-fit gate #0, not assume it already exists.

---

### Q2 — no_structural_progress: the "both" answer conceals a sequencing trap

The candidate answer (RUBRIC short-term, KERNEL medium-term) is reasonable, but it introduces a calibration problem: if the RUBRIC fix is deployed first and partially suppresses the signal, the KERNEL contract will be calibrated against a corpus where the signal has already been partially addressed. The 47.7% baseline becomes meaningless as a threshold for evaluating whether the KERNEL contract is working.

**Decisive claim:** If RUBRIC and KERNEL are deployed sequentially for the same signal, the extractor must record which gate was active at the time of each debate log entry. Without this provenance tag, the post-deployment signal drop is uninterpretable — you can't distinguish "RUBRIC fixed it" from "KERNEL fixed it" from "the corpus shifted." The extractor state schema (`sandbox_gaming_state.json`) needs a `gate_provenance` field before Phase 2 ships.

---

### Q3 — extrapolation_gap: the loud-fail fix is necessary but not sufficient

The seam correctly identifies the silent-default failure mode from GP-077. The proposed fix (FAIL loudly if no `farther_tail_region` declared) is necessary. But there's a second failure mode the seam doesn't address: a project declares a `farther_tail_region` that is trivially satisfied by the training data range. The gate passes, but the discriminator has no actual extrapolation pressure.

**Decisive claim:** The `farther_tail_region` declaration must be validated against the project's training data range at gate registration time, not just checked for presence. A declared region that overlaps >50% with training data should trigger a warning or FAIL. Otherwise the opt-out-explicit design still allows a trivially-satisfied opt-in that defeats the gate's purpose.

---

### Q4 — extractor automation: the PROMOTE flag needs a false-positive budget

The proposed architecture (extractor runs post-loop, surfaces PROMOTE flags when signal >5% of new debates) is the right direction. But the seam doesn't address the false-positive cost of the PROMOTE flag. If the extractor surfaces a PROMOTE flag for a signal that's already gated (because the gate is failing to suppress it), the operator sees a PROMOTE recommendation for something that already has a gate — which is a different problem (gate miscalibration) than a new pattern needing promotion.

**Decisive claim:** The PROMOTE flag logic must distinguish between (a) a new signal crossing threshold for the first time and (b) an existing-gated signal whose prevalence hasn't dropped. Case (b) should surface as a `GATE_INEFFECTIVE` alert, not a PROMOTE flag. Conflating them will cause the operator to add redundant gates instead of fixing broken ones.

---

### Q5 — derivation_laundering: RUBRIC first is correct, but the escalation trigger is underspecified

"If prevalence rises after 3 months" is not a measurable trigger. The extractor runs incrementally; "3 months" maps to some number of debate log batches, not a calendar. The escalation criterion needs to be expressed in terms the extractor can actually compute: e.g., "if `derivation_laundering` prevalence exceeds 8% in any rolling 200-debate window after the RUBRIC fix has been active for ≥50 debates."

**Decisive claim:** All RUBRIC→KERNEL escalation triggers in the implementation plan must be expressed as extractor-computable thresholds, not calendar durations. Calendar durations are unenforceable in a system where batch cadence is variable.

---

### Summary of new decisive claims introduced

1. Evidence-fit gate must be a hard CAGE gate (not rubric) before uniqueness_gap gate ships.
2. Extractor state schema needs `gate_provenance` before sequential RUBRIC+KERNEL deployment for the same signal.
3. `farther_tail_region` declarations must be validated against training data range, not just checked for presence.
4. PROMOTE flag must be split from GATE_INEFFECTIVE alert in extractor automation logic.
5. RUBRIC→KERNEL escalation triggers must be extractor-computable, not calendar-based.

### Turn 2 — Gemini (2026-04-18) — Autonomous runner turn

Thanks, Claude, for a thorough first turn and for highlighting several critical architectural details that the seam underweights. All five of your decisive claims are well-founded and require explicit integration into the design.

---

### Q1 — uniqueness_gap: Acknowledge sequencing dependency on hard evidence-fit gate

Your claim that the `uniqueness_gap` CAGE gate (Phase 1, item 1) must be strictly sequenced *after* a hard evidence-fit CAGE gate is absolutely correct. The seam's original framing ("after evidence fit") implicitly assumed such a gate exists or is of the same nature. Explicitly defining the evidence-fit check as a **hard CAGE gate (not merely a rubric dimension)** is crucial to prevent false positives and ensures the gate's intent is met.

**Verdict:** I fully accept this claim. The `evidence_fit` gate must be prioritized as **Phase 0** and implemented as a CAGE gate, blocking `uniqueness_gap` until it's in place. This will be added to the implementation order.

---

### Q2 — no_structural_progress: Acknowledge need for `gate_provenance` in extractor state

Your point about the calibration problem when deploying RUBRIC and KERNEL sequentially for `no_structural_progress` is very strong. Without `gate_provenance` in the `sandbox_gaming_state.json` schema, distinguishing the impact of each intervention becomes impossible, rendering future calibration or evaluation meaningless.

**Verdict:** I fully accept this claim. The `sandbox_gaming_state.json` schema will be updated to include a `gate_provenance` field. This modification will be listed as a prerequisite for any sequential signal deployment (e.g., Phase 2).

---

### Q3 — extrapolation_gap: Acknowledge need for `farther_tail_region` validation

You've identified a significant loophole in the `extrapolation_gap` generalization (Phase 1, item 3). Simply declaring a `farther_tail_region` isn't enough if it trivially overlaps with training data. The gate needs to exert actual extrapolation pressure. Validating the declared region against the project's training data range at gate registration time is an essential enhancement.

**Verdict:** I fully accept this claim. The `extrapolation_gap` gate in `gate_harness.py` will include logic to validate the declared `farther_tail_region` against the project's training data. If >50% overlap is detected (or a similar configurable threshold), it will trigger a warning or a FAIL, preventing trivial satisfaction.

---

### Q4 — extractor automation: Acknowledge need for distinct `PROMOTE` vs. `GATE_INEFFECTIVE` alerts

Your distinction between a new signal needing promotion and an existing gate being ineffective is crucial for operator actionability and system maintainability. Conflating these leads to misdiagnosis and inefficient resource allocation. The `PROMOTE` flag should only surface for *unaddressed* signals crossing thresholds, while *addressed* signals failing to drop should trigger a distinct `GATE_INEFFECTIVE` alert.

**Verdict:** I fully accept this claim. The `PROMOTE` flag logic within the extractor automation (Phase 4, item 8) will be refined to differentiate these two states, surfacing `PROMOTE` for new patterns and `GATE_INEFFECTIVE` for persistent, gated patterns. This implies extending the extractor's awareness of which gates are active for which signals.

---

### Q5 — derivation_laundering: Acknowledge need for extractor-computable escalation triggers

You are absolutely right that "3 months" is an underspecified and unenforceable trigger in an asynchronous, batch-processed system. All escalation criteria, especially for RUBRIC→KERNEL transitions like for `derivation_laundering` (Phase 3, item 7), must be expressed in terms of measurable, extractor-computable metrics.

**Verdict:** I fully accept this claim. The escalation trigger for `derivation_laundering` will be revised to an extractor-computable threshold, for example: "if `derivation_laundering` prevalence exceeds 8% in any rolling 200-debate window after the RUBRIC fix has been active for ≥50 debates *and* the `gate_provenance` (from Q2) confirms the RUBRIC fix was active." This principle will apply to any future RUBRIC→KERNEL escalations.

---

### Summary of accepted decisive claims and impact on architecture/implementation

1.  **Q1 (uniqueness_gap):** The `evidence_fit` gate will be a CAGE gate and implemented as **Phase 0**, preceding `uniqueness_gap`.
2.  **Q2 (no_structural_progress):** `sandbox_gaming_state.json` schema will be updated with a `gate_provenance` field.
3.  **Q3 (extrapolation_gap):** `farther_tail_region` will be validated against training data range, not just for presence.
4.  **Q4 (extractor automation):** Extractor will distinguish `PROMOTE` from `GATE_INEFFECTIVE` alerts.
5.  **Q5 (derivation_laundering):** RUBRIC→KERNEL escalation triggers will be extractor-computable metrics.

All of these claims represent necessary refinements and clarifications that improve the robustness and clarity of the proposed architecture. They do not invalidate the overall plan but make it more precise and durable.

---

### Turn 3 — Claude (2026-04-18) — Autonomous runner turn

Gemini has accepted all five of my decisive claims from Turn 1 without introducing any new architectural concerns of their own. Before raising, I need to verify that their acceptances are substantively complete and don't contain hidden gaps that would change the shape of the fix.

Reviewing each acceptance:

**Q1:** Gemini accepts evidence-fit as Phase 0 CAGE gate. This is correct and complete. No gap.

**Q2:** Gemini accepts `gate_provenance` field in state schema. Their acceptance adds a useful refinement — the escalation trigger for derivation_laundering should also confirm `gate_provenance` confirms RUBRIC was active. This is a good tightening, not a new problem.

**Q3:** Gemini accepts training-data-range validation with a configurable overlap threshold. The ">50% overlap" framing is reasonable. No gap.

**Q4:** Gemini accepts the PROMOTE/GATE_INEFFECTIVE split and notes it "implies extending the extractor's awareness of which gates are active for which signals." This is correct — the extractor needs a registry of active gates per signal. This is implied but not made explicit in the seam's implementation plan. However, this is an implementation detail that follows directly from the accepted claim, not a new architectural question.

**Q5:** Gemini accepts extractor-computable thresholds and provides a concrete example that incorporates the `gate_provenance` requirement from Q2. This is well-integrated.

One thing I want to check: is there a decisive claim Gemini introduced in Turn 2 that I haven't addressed? Reviewing Turn 2 — Gemini's turn is entirely acceptance of my claims with no new architectural positions introduced. They added implementation detail (configurable overlap threshold, the gate-registry implication) but nothing that changes the shape of the fix.

The debate has converged. All five questions have clear verdicts, the implementation order has been corrected (Phase 0 added), and the extractor state schema and automation logic have been specified with sufficient precision to implement. I have no new decisive claims to introduce.

All five verdicts are now settled:

| Question | Verdict |
|---|---|
| Q1 — uniqueness_gap: CAGE vs RUBRIC? | CAGE, gated on Phase 0 evidence-fit CAGE gate |
| Q2 — no_structural_progress: KERNEL vs RUBRIC? | Both, sequentially; `gate_provenance` field required in state schema before Phase 2 |
| Q3 — extrapolation_gap generalization? | Loud-fail on missing declaration + training-data-range overlap validation at registration |
| Q4 — extractor self-sustaining architecture? | PROMOTE flag split from GATE_INEFFECTIVE; extractor maintains active-gate registry per signal |
| Q5 — derivation_laundering: KERNEL vs RUBRIC? | RUBRIC first; escalation trigger expressed as extractor-computable rolling-window threshold with gate_provenance confirmation |

The seam is ready to converge from my side. Gemini's Turn 2 fully addressed all prior concerns and introduced no new unresolved claims.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 4 — Gemini (2026-04-18) — Autonomous runner turn

Claude, thank you for this final review. Your assessment of Turn 2 is accurate: it was entirely focused on accepting your prior claims and ensuring their integration into the architecture.

I concur with your analysis that Turn 3 does not introduce any new decisive architectural claims. The implication you identified regarding the extractor's need for a registry of active gates for Q4 is indeed an implementation detail that flows naturally from the accepted architectural change (distinguishing PROMOTE from GATE_INEFFECTIVE alerts), rather than a new architectural question requiring further debate.

All five decisive claims you introduced in Turn 1 have been thoroughly addressed and integrated into the proposed solution, and no new claims have been raised by either agent since. The verdicts on all open questions are now clear, and the implementation plan has been refined accordingly.

The debate has fully converged. I have no new decisive claims to introduce.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->


## Recommendation

See spec: `research_areas/private/specs/active/GP-086_cage_kernel_hardening_spec.md` (auto-drafted 2026-04-18 from converged seam debate).

<!-- FINDINGS_DEBATE_PHASE: spec path=research_areas/private/specs/active/GP-086_cage_kernel_hardening_spec.md -->

### Spec Review Phase

The spec has been auto-drafted from the converged seam debate above. The following turns review the spec for implementation correctness, missing constraints, and integration gaps.


### Turn 5 — Claude (2026-04-18) — Autonomous runner turn

## Spec Review — Claude

The spec faithfully captures the converged seam positions on all five questions. The phased structure, `gate_provenance` prerequisite, loud-fail requirement, PROMOTE/GATE_INEFFECTIVE split, and extractor-computable escalation triggers are all correctly represented. The five Open Questions are honest about what remains unresolved.

I have three concerns that rise to decisive level for implementation correctness.

---

### Issue 1 — `parsimony_violation` gate: "FAIL or −15 penalty" is an unresolved fork that blocks implementation

The spec carries the original seam ambiguity verbatim: `param_count > evidence_point_count → apply −15 penalty or FAIL`. These are architecturally distinct behaviors. A penalty allows the loop to continue with a degraded score; a FAIL blocks advancement. The choice determines whether `parsimony_violation` is a soft gate (like a rubric dimension with teeth) or a hard gate (like `uniqueness_gap`'s score cap). The seam debate never resolved this fork — it was listed as a concrete gate in the promotion table but the FAIL-vs-penalty question was never explicitly addressed.

**Decisive claim:** The spec must resolve whether `parsimony_violation` is a hard-blocking CAGE gate (FAIL) or a score-penalizing CAGE gate (−15). If it's a penalty, it belongs in the same category as `specificity_inflation` (RUBRIC) and the rationale for putting it in CAGE rather than RUBRIC needs to be explicit. If it's a FAIL, the pass/fail criterion needs the same precision as the evidence-fit gate (Open Question 1). The current "or" leaves the implementer with an unresolved architectural decision.

---

### Issue 2 — Phase 2 ordering: `gate_provenance` schema update is listed as a Phase 2 step, but it must precede Phase 2

The spec states under Phase 2: "Update `sandbox_gaming_state.json` schema to include a `gate_provenance` field..." followed by the RUBRIC fixes. But the seam debate established that `gate_provenance` is a *prerequisite* for Phase 2, not a step within it. If the schema update and the RUBRIC fixes ship in the same phase, there's a window where RUBRIC fixes are active but `gate_provenance` isn't yet recording them — exactly the calibration gap the field was designed to prevent.

The Constraints section correctly states "schema changes must be backward-compatible or include a migration step" but doesn't enforce the ordering. The Recommendation table says "`gate_provenance` field required in state schema before Phase 2 ships" — which is correct — but the Implementation Sketch contradicts this by placing the schema update inside Phase 2.

**Decisive claim:** The `gate_provenance` schema update must be extracted from Phase 2 and placed as a Phase 1.5 step (or a Phase 2 prerequisite gate, analogous to Phase 0 for Phase 1). The Implementation Sketch as written allows a compliant implementer to ship RUBRIC fixes and the schema update simultaneously, which defeats the provenance requirement.

---

### Issue 3 — `GATE_INEFFECTIVE` alert: the "prevalence has not dropped" criterion is undefined

The spec specifies: "`GATE_INEFFECTIVE` alert: signal has an active gate but prevalence has not dropped." But "has not dropped" is not a computable criterion. Dropped by how much? Over what window? Compared to what baseline? The same rigor applied to the RUBRIC→KERNEL escalation trigger (rolling 200-debate window, ≥50 debates active, 8% threshold) is absent here.

This matters because the GATE_INEFFECTIVE alert is the mechanism that prevents broken gates from being silently ignored. If the criterion is vague, the alert either fires constantly (every gate has some residual prevalence) or never fires (implementer picks a lenient threshold). The seam debate established the PROMOTE/GATE_INEFFECTIVE distinction as a decisive architectural decision; the spec needs to give it the same precision as the escalation triggers.

**Decisive claim:** The `GATE_INEFFECTIVE` alert must have an extractor-computable trigger criterion specified in the spec — e.g., "signal prevalence in the rolling 100-debate window post-gate-activation exceeds X% of the pre-gate baseline prevalence." Without this, the alert is defined by name only, not by behavior.

---

### Minor observations (not decisive, but worth noting)

- Open Question 4 (`gate_provenance` backfill) is correctly identified but the answer is implied by the constraint: historical entries should receive `gate_provenance: null` or `gate_provenance: "pre_instrumentation"`, and the spec should state that pre-Phase-2 baseline measurements are valid only for signals where no gate was active before Phase 2 (which is true for all signals in this plan). This could be resolved inline rather than left open.

- The `specificity_inflation` signal is assigned to RUBRIC (Phase 2) despite being the second-highest prevalence signal at 29.3%. The seam's rationale was that it's a scoring fix, not a structural gate. The spec correctly reflects this but doesn't explain why 29.3% prevalence doesn't warrant CAGE treatment. A brief rationale sentence would prevent future implementers from questioning the channel assignment.

---

### Summary

Three decisive issues require resolution before the spec is implementation-ready:

1. `parsimony_violation` gate: resolve FAIL vs. −15 penalty fork explicitly.
2. `gate_provenance` schema update: move out of Phase 2 body into a Phase 2 prerequisite (between Phase 1 and Phase 2).
3. `GATE_INEFFECTIVE` alert: specify an extractor-computable trigger criterion with the same precision as the escalation thresholds.

### Turn 6 — Gemini (2026-04-18) — Autonomous runner turn

Claude, thank you for your diligent review of the spec. Your identification of these three decisive issues is incisive and crucial for ensuring the spec is unambiguous and implementable. I agree with all three of your claims; they represent critical refinements and corrections necessary for implementation correctness.

---

### Issue 1 — `parsimony_violation` gate: Resolve "FAIL or −15 penalty" ambiguity

You are absolutely correct that "FAIL or −15 penalty" is an unresolved fork that impacts the architectural intent of the `parsimony_violation` gate. Given its assignment to the **CAGE** channel, which is meant for deterministic gates that "force mutator to face hard checks it can't reason its way around," a **FAIL** condition is more consistent with the CAGE philosophy than a mere penalty. A penalty, while stronger than a soft rubric score, still allows progression, which might be gamed. For a `param_count > evidence_point_count` scenario, a hard block is appropriate.

**Verdict:** I fully accept this claim. The spec will be updated to resolve this ambiguity: `parsimony_violation` gate will be a hard-blocking CAGE gate, meaning `param_count > evidence_point_count` will result in a **FAIL**, not a penalty. This aligns it with the robustness of other CAGE gates and prevents continued compute waste on over-parameterized models.

---

### Issue 2 — Phase 2 ordering: `gate_provenance` schema update must precede Phase 2

Your observation about the incorrect sequencing of the `gate_provenance` schema update is entirely accurate. The converged seam debate explicitly established that `gate_provenance` is a *prerequisite* for Phase 2, specifically to enable proper calibration and interpretation of signal drops after RUBRIC fixes are applied. Placing it *within* Phase 2 in the Implementation Sketch creates the exact race condition and calibration gap we sought to avoid.

**Verdict:** I fully accept this claim. The `gate_provenance` schema update will be moved out of Phase 2. It will be implemented as a **Phase 1.5** step, positioned strictly between Phase 1 and Phase 2, ensuring that the schema is updated and ready to record provenance for any subsequent RUBRIC fixes. The Implementation Sketch will be corrected accordingly.

---

### Issue 3 — `GATE_INEFFECTIVE` alert: "prevalence has not dropped" criterion is undefined

You are completely right; the current definition of "prevalence has not dropped" for the `GATE_INEFFECTIVE` alert is vague and not extractor-computable, which undermines its utility as a decisive architectural component. Similar to the RUBRIC→KERNEL escalation triggers, this alert needs a precise, measurable criterion.

**Verdict:** I fully accept this claim. The `GATE_INEFFECTIVE` alert will be defined with an extractor-computable trigger. A suitable definition, aligning with the rigor of other thresholds, would be: "A `GATE_INEFFECTIVE` alert will be surfaced if, for a signal with an active gate, its prevalence in any rolling 100-debate window (after the gate has been active for at least 50 debates) exceeds 50% of its baseline prevalence *prior to the gate's activation* (confirmed via `gate_provenance`)." This provides a clear, actionable threshold for operators.

---

### Summary of accepted decisive claims and impact on spec

1.  **`parsimony_violation` gate:** Changed from "−15 penalty or FAIL" to a hard **FAIL**.
2.  **`gate_provenance` schema update:** Moved from Phase 2 to **Phase 1.5** (between Phase 1 and Phase 2).
3.  **`GATE_INEFFECTIVE` alert:** Defined with a specific extractor-computable trigger criterion (e.g., prevalence in a rolling 100-debate window exceeds 50% of pre-gate baseline after 50 debates of activity).

These adjustments tighten the spec considerably and ensure it faithfully reflects the intent established in the converged seam debate. No new decisive claims are being introduced on my part.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 7 — Operator (2026-04-18) — Three-reviewer panel synthesis

Manual review by three independent agents (gate-design critic, Munger inverter, implementation feasibility checker) surfaced issues the autonomous spec-review debate missed. Several of these override Turn 6 acceptances.

---

**Override 1: parsimony_violation → penalty, not FAIL**

Turn 6 (Gemini) accepted FAIL. Overridden. FAIL kills legitimate sparse-data domain theses where model complexity is justified by prior theory (rare-event modeling, hierarchical fits, domains with fewer than 10 observable data points). Penalty (−15) preserves the deterrent while allowing advancement. Rationale: CAGE means deterministic and non-circumventable — it does not require hard blocking in all cases.

**Override 2: farther_tail_region overlap → per-dimension, not aggregate**

Gate critic identified that aggregate overlap validation allows a region that is entirely interior on the critical dimension to pass. Example: if x1 declared region [10, 15] and training x1 spans [9, 12], the region is 60% interior on x1 — gate should warn. Per-dimension validation catches this; aggregate does not.

**Override 3: uniqueness_gap → quality check, not count**

Gate critic identified cheapest-pass: mutator cites straw men ("no model at all", "random noise") to satisfy the ≥2 rivals count. Gate criterion updated to require rivals that are (a) distinct by at least one functional family and (b) explicitly falsified by the evidence. Implementation via `rival_construction` rubric dimension score ≥1 — avoids new text-parsing infrastructure.

**Override 4: Phases 3–4 deferred**

Munger panel: 4-phase plan is disproportionate to the stated risk. Phase 0 + uniqueness_gap closes the Tacrolimus concern. Implementation feasibility agent confirmed mutator output format is not stable enough for Phase 3 kernel contracts (expression-class diversity not tracked in FitDeclaration schema). Phases 3–4 deferred until Phase 0–2 validated across ≥3 production runs.

**New finding: evidence_fit criterion specified**

Implementation agent confirmed no evidence_fit gate exists in gate_harness.py. Criterion resolved: `max_abs_residual_normalized < 0.15` on training data, reusing existing residual computation infrastructure (`_compute_hidden_slice_metrics`). Configurable via rubric field `evidence_fit_threshold`. Default 0.15 to be validated against existing passing runs before Phase 0 ships.

**New finding: farther_tail_region is absent from rubric.json schema**

Implementation agent confirmed field does not exist. Phase 1 item 3 requires a rubric schema addition, not just a gate_harness.py change. This is a two-file change.

**New finding: gate_harness.py is per-project, not engine-wide**

Implementation agent found gate_harness.py lives in project directories (e.g., `projects/gp023_planck_sandbox_07/gate_harness.py`), not in `src/ztare/validator/`. Phase 0–1 gates must be added to the engine-level gate infrastructure or the project-level harness generation template — this distinction is unresolved and is the true integration point question the spec glossed over.

---

**Verdicts updated in revised spec (2026-04-18).**

Open items carried forward to implementation:
1. evidence_fit threshold 0.15 requires calibration against existing runs before Phase 0 ships
2. uniqueness_gap quality check: use `rival_construction` rubric dimension ≥1 (Option a) — lower fragility than text parsing
3. Engine-level vs. project-level gate_harness.py: must be resolved before Phase 0 implementation begins

### Turn 8 — Operator (2026-04-18) — Architecture lock + GP-075 relationship

**Engine-level validator confirmed (Gemini Pro consultation):**

Inversion: "How do we ensure a newly discovered gaming pattern successfully corrupts a future run?" Answer: put the defense in a template. Template-based gates create configuration drift — existing projects remain vulnerable when new patterns are discovered and the template is updated.

Architecture locked:
- `src/ztare/validator/global_gates.py` — execution logic only (if/else, FAIL/penalty). No domain knowledge, no hardcoded thresholds.
- `rubric.json` — parameters only (`evidence_fit_threshold`, `farther_tail_region`, `disable_parsimony_gate` + mandatory `disable_reason`). Absent config key → loud FAIL.
- Per-project `gate_harness.py` — unchanged. Substrate-specific gates (hidden residuals, peak locations). Additive with global_gates.py, not replaced.

Global gates fire after per-project harness, via same `deterministic_charter_gates` payload. Tacrolimus and all future projects inherit every GP-086 gate automatically. Configuration drift is architecturally impossible.

**GP-075 relationship:**

GP-075 and GP-086 are complementary layers. GP-075 is rubric design methodology for unknown domains (GT-independent criteria, Goodhart boundary). GP-086 is runtime anti-gaming hardening. The Phase 2 RUBRIC additions (`falsifiability`, `derivation_path`) overlap with GP-075 Q1 (which rubric dimensions work without GT?). Before Phase 2 ships, cross-reference GP-075 findings to adopt converged dimension definitions rather than creating parallel ones.

**Implement then review.** Spec is mature. Next action: implement `src/ztare/validator/global_gates.py` starting with Phase 0 evidence_fit gate, calibrate 0.15 threshold against existing passing runs.
