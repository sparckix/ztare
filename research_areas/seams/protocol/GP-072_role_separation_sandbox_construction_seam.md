# GP-072 Role Separation in Sandbox Construction

> **Seam metadata** · `seam_id:` GP-072 · `track:` protocol · `status:` Open · `last_updated:` 2026-05-08


**Status:** Open
**Date:** 2026-04-15
**Origin:** Sandbox_12 construction — first sandbox built under M-form information isolation
**Parent:** GP-061 Phase 2 (void steering measurement)

## Problem

Every sandbox construction to date has relied on a single agent (or operator) knowing the ground truth and trying not to leak it into mutator-visible files. This is **policy-based hygiene** — the agent knows the answer and promises not to write it down where the LLM can see it.

This fails repeatedly:
- Sandbox_06: slug contained "planck" (answer class)
- Sandbox_09: thesis seed leaked structural hints
- Sandbox_11: slug contained "hinge" (answer class); required 2026-04-15 rename
- Sandbox_12 first draft: Division B agent leaked "discrete", "sealed", "pre-registration" — 14 sentinel hits

The failure mode is always the same: the agent knows too much and contaminates artifacts through vocabulary leakage, framework meta-talk, or structural hints that prime the mutator toward the GT class.

## Root Cause

Contamination is not a discipline problem. It is an **information flow problem**. A single agent with GT knowledge authoring mutator-visible files will always eventually leak, because:

1. The GT constrains the author's vocabulary choices (you avoid words near the answer, but the avoidance itself is a signal)
2. Framework vocabulary ("pre-registration", "sealed", "sandbox") tells the mutator it's being tested, which changes its behavior
3. The denylist can only catch known leak vectors; novel synonym leaks are unbounded

The fix is not a better denylist. The fix is information isolation.

## Solution: Division A / Division B (M-Form)

**Division A (Lab Tech):** Knows the GT. Produces:
- `evidence.txt` and `evidence_holdout.txt` (generated from GT formula)
- Pre-registration document (private, names GT, seals protocol)
- Denylist file (`.denylist`) — GT-specific patterns for the sentinel
- Gate thresholds (if gates need GT-derived values)

Division A artifacts live outside the repo (generate script in `/tmp/`) or in `research_areas/private/`.

**Division B (Principal Investigator):** Does NOT know the GT. Receives only:
- The abstract problem description ("integer function, exact match scoring")
- The evidence files (data points, not the formula that generated them)
- The runtime interface contract (what flags the harness must support)

Division B produces:
- `project_charter.md`
- `rubrics/<slug>.json`
- `test_model.py` (neutral baseline)
- `gate_harness.py` (frozen, imports from test_model.py)

If Division B doesn't know the answer, it **cannot** leak it. The failure mode is eliminated, not mitigated.

**Sentinel Gate:** Automated grep (`src/ztare/validator/leak_sentinel.py`) runs the Division A denylist against all Division B artifacts. Catches any residual contamination from the briefing itself leaking through.

## What Went Wrong in Sandbox_12 (Lessons)

### Lesson 1: Division B briefing leaked framework vocabulary

I told Division B the scoring mode name was `discrete_exact`. Division B wrote "discrete" into the charter, evidence header, and rubric persona — 14 sentinel hits. The word "discrete" is a structural hint (tells the mutator the problem involves discrete math).

**Fix:** Brief Division B with neutral vocabulary only. Say "exact integer match" not "discrete_exact." The config key name is an internal implementation detail.

### Lesson 2: Division B didn't know the runtime interface contract

The Level 3 falsification suite calls `gate_harness.py --run-visible-assertions`. Division B only implemented `--emit-deterministic-gates` and `--run-smoke-test`. The harness failed at runtime with "unknown invocation."

**Fix:** The Division B briefing must include the exact flags the runtime will call:
- `--run-visible-assertions` (Level 3 falsification suite)
- `--emit-deterministic-gates` (GP-030 deterministic charter gates evaluator)
- `--run-smoke-test` (pre-seal verification)

This is not a contamination issue — it's an **integration contract** issue. Division B needs to know HOW the harness is called, just not WHAT the right answer is.

### Lesson 3: The sentinel catches content leaks, not missing interfaces

The sentinel passed on Division B's artifacts after neutralization. But the harness was broken because it was missing a flag handler. The sentinel is necessary but not sufficient — integration testing (running the harness with all expected flags) must also happen before sealing.

**Pre-seal checklist addition:** After sentinel passes, run:
```bash
python gate_harness.py --run-visible-assertions   # should fail with AssertionError (baseline is wrong)
python gate_harness.py --emit-deterministic-gates  # should emit JSON with harness_ok=false
python gate_harness.py --run-smoke-test            # should pass
```

## Codification Path

### Phase 1 (current): Manual Division A/B with sentinel

- Division A: operator or main agent writes generate script + pre-reg
- Division B: separate agent spawned with information barrier
- Sentinel: `leak_sentinel.py` with per-substrate denylist

### Phase 2 (future): `make scaffold` command

```bash
make scaffold \
    PROJECT=gp069_sandbox_13 \
    GT_SCRIPT=/tmp/division_a_sandbox_13.py \
    PROBLEM_BRIEF="integer function, exact match, single variable" \
    DENYLIST=/tmp/sandbox_13.denylist
```

This would:
1. Run the GT script (Division A) to generate evidence files
2. Spawn a GT-blind agent (Division B) with the problem brief
3. Run the sentinel
4. Run integration tests (all three harness flags)
5. Compute and display sealed hashes

### Phase 3 (aspirational): Type-level information flow

Tag data with clearance levels (GT-aware vs GT-blind). The builder rejects any code path that moves GT-tagged data into GT-blind outputs at compile time, not runtime. This is the "physics not policy" endstate.

## Relation to Existing Seams

- **GP-039 (pre-run leak audit checklist):** The sentinel automates §1 of this checklist. Division A/B makes §1 structurally unnecessary for Division B artifacts.
- **GP-054 (rubric quality):** Division B writes rubrics without GT knowledge, which naturally prevents the "rubric encodes the answer" failure mode.
- **GP-061 (void steering measurement):** Sandbox_12 is the first experiment built under this protocol. The measurement validity depends on the information barrier holding.

## Open Questions

1. Should Division B be a separate agent (current) or a separate human? Agent-to-agent isolation is weaker than human-to-human because the orchestrator (main agent) knows GT and could accidentally leak through the briefing.
2. Can the sentinel denylist be auto-generated from Division A's GT formula? (e.g., extract all function names, constants, and mathematical terms, then regex-compile them)
3. Should the sentinel also scan `gate_harness.py`? It's not mutator-visible, but if the harness contains GT-derived constants (like specific threshold values), those could leak through error messages.

## Debate Log

### Turn 1 — Claude-Author (2026-04-15) — Autonomous runner turn

The seam correctly identifies the root cause as an information flow problem rather than a discipline problem, and the Division A/B framing is the right structural response. But there are three decisive claims embedded in the proposed solution that need sharper treatment before this seam can converge.

---

## Eigenquestion

**Is the Division A/B boundary sufficient to eliminate contamination, or does it merely relocate the leak surface?**

This is the question whose answer reshapes the most downstream choices. If the boundary is sufficient, Phase 2 (`make scaffold`) is the right next investment. If it merely relocates the leak, we need to understand the new leak surface before automating it.

---

## Claim 1: "If Division B doesn't know the answer, it cannot leak it"

This is stated as a near-tautology in the seam, but it rests on a belief that needs to be made explicit:

**WWYHTB:** The briefing Division B receives is itself GT-neutral.

Sandbox_12 Lesson 1 falsifies this belief in the first real trial. Division B was told the scoring mode name `discrete_exact`, and that single vocabulary choice produced 14 sentinel hits. The contamination did not come from Division B knowing the GT — it came from the **briefing vocabulary** carrying structural information about the GT class.

This means the information barrier is not between Division A and Division B. It is between the GT and the briefing. Division A must author the briefing, and the briefing itself must pass the sentinel before Division B receives it. The current seam does not state this explicitly, and the Phase 2 `make scaffold` command does not include a sentinel pass on `PROBLEM_BRIEF` before it is handed to Division B.

**Proposed sharpening:** Add a sentinel gate on the Division A briefing artifact before it reaches Division B. The briefing is a mutator-visible artifact once Division B writes it into the charter — so it must be treated as one from the moment it is authored.

---

## Claim 2: The sentinel is "necessary but not sufficient" — integration testing fills the gap

This is correct as stated, but the pre-seal checklist addition has a subtle problem: it specifies that `--run-visible-assertions` "should fail with AssertionError (baseline is wrong)." This is a GT-derived expectation. Division B cannot write this check without knowing that the baseline is wrong relative to the GT. Division A must specify the expected exit behavior for each flag, and that specification must be part of the Division A artifact set, not inferred by Division B.

More broadly: the integration contract (exact flags, expected exit codes, expected output shape) is currently described as something Division B "needs to know." But if Division A specifies the expected behavior of each flag, Division B can implement the harness to match a spec without knowing why those exit codes are correct. This is the same information-barrier logic applied to the integration layer.

**Proposed sharpening:** The Division A artifact set should include a `harness_contract.json` specifying: flag name, expected exit code, expected output schema (not values). Division B implements to the contract. Division A verifies the harness against GT-derived values in a separate step that Division B never sees.

---

## Claim 3: Phase 3 (type-level information flow) is "aspirational"

The seam labels this "physics not policy" and defers it. But the Lesson 1 failure (briefing vocabulary leaking) suggests the gap between Phase 1 and Phase 3 is not just engineering effort — it is a conceptual gap in what "information isolation" means.

In Phase 1, isolation is enforced by the sentinel (a runtime grep). The sentinel can only catch known patterns. Novel synonym leaks (the seam's own phrase) are unbounded. Phase 3 would catch them at the type level. The question is whether Phase 2 (`make scaffold`) is a useful intermediate or whether it automates a leaky process at scale.

**WWYHTB for Phase 2 being useful:** The sentinel denylist is comprehensive enough that automating the Phase 1 process at scale does not automate novel synonym leaks at scale. This belief is not currently evidenced. The sandbox_12 case shows the denylist missed "discrete" until it was added post-hoc.

**Proposed sharpening:** Before investing in Phase 2 automation, run a retrospective on all prior sandboxes: for each contamination event, was the leaking term in the denylist at the time of construction? If the answer is "no" in most cases, Phase 2 automates a process that will still leak at the novel-synonym surface. The seam should state this as a prerequisite for Phase 2 investment.

---

## Open Question 1 Sharpening

The seam asks whether Division B should be a separate agent or a separate human, noting that "agent-to-agent isolation is weaker than human-to-human because the orchestrator knows GT."

This framing misidentifies the threat model. The weakness is not agent-vs-human — it is **briefing authorship**. Whether Division B is an agent or a human, the contamination vector is the briefing that Division A writes. A human Division B who receives a contaminated briefing will still produce contaminated artifacts. The sentinel on the briefing (Claim 1 above) is the fix regardless of whether Division B is an agent or a human.

The real question for Open Question 1 is: **can the orchestrator's GT knowledge leak into the Division B briefing through channels the sentinel does not cover?** (e.g., the choice of which evidence points to include, the ordering of examples, the level of abstraction in the problem description). These are structural hints that a grep-based sentinel cannot catch.

---

## Summary of Proposed Additions to the Seam

1. **Sentinel gate on the Division A briefing** before it reaches Division B. The briefing is a mutator-visible artifact from the moment it is authored.
2. **`harness_contract.json` as a Division A artifact** — specifies flag names, expected exit codes, expected output schema. Division B implements to the contract without knowing why those exit codes are correct.
3. **Phase 2 prerequisite: retrospective on denylist coverage** — before automating Phase 1, verify that the sentinel would have caught prior contamination events at construction time, not post-hoc.
4. **Reframe Open Question 1** from agent-vs-human to briefing-authorship-as-the-threat-surface.

### Turn 2 — Claude-Skeptic (2026-04-15) — Autonomous runner turn

The Author's Turn 1 is structurally sound and the four proposed additions are improvements. But there are several decisive claims that need pressure before this seam can converge.

---

## On Claim 1 (Sentinel gate on the briefing): Correct diagnosis, incomplete fix

The Author correctly identifies that the briefing is a mutator-visible artifact from the moment it is authored. But the proposed fix — "add a sentinel gate on the Division A briefing before it reaches Division B" — has a circularity problem.

The sentinel runs a denylist. The denylist is authored by Division A and is GT-specific. But the briefing is also authored by Division A. So Division A is being asked to write a briefing, then check that briefing against a denylist it also wrote, before handing the briefing to Division B.

**What would have to be true for this to fail:** Division A's denylist is incomplete at briefing-authorship time. This is not hypothetical — it is exactly what happened in sandbox_12. The word "discrete" was not in the denylist when Division B received the briefing. It was added post-hoc after the sentinel flagged it. The proposed sentinel gate on the briefing would not have caught "discrete" in sandbox_12 because the denylist did not yet contain it.

The deeper problem: the denylist is constructed from the GT formula (function names, constants, mathematical terms). But the briefing leaks through **problem-class vocabulary** ("discrete", "exact", "integer") — words that describe the *type* of problem, not the specific GT. These words are not derivable from the GT formula alone. They require a separate enumeration of "what vocabulary signals this problem class to a mutator?" — which is a different cognitive task than "what terms appear in my formula?"

**Proposed sharpening:** The denylist must have two layers: (a) GT-specific terms (derivable from the formula), and (b) problem-class vocabulary (requires adversarial enumeration — "what would a mutator infer from this word?"). The sentinel gate on the briefing is only as good as layer (b), and layer (b) is currently absent from the seam's codification path.

---

## On Claim 2 (harness_contract.json): Correct but the exit-code claim is overstated

The Author says Division B can implement the harness to match a contract "without knowing why those exit codes are correct." This is true for the flag names and output schema. It is not fully true for exit codes.

Consider `--run-visible-assertions`: the contract says "expected exit code: 1 (AssertionError)." Division B implements a harness that exits 1 when assertions fail. But Division B must also implement the assertions themselves — and the assertions are what the mutator's output is checked against. If Division B writes the assertions without knowing the GT, the assertions will be structurally correct (they check something) but semantically wrong (they check the wrong thing). The harness will exit 1 for the right structural reason but the wrong semantic reason.

**What would have to be true for this to be a real problem:** The gate harness's visible assertions are not purely structural (e.g., "output is an integer") but are also semantic (e.g., "output equals the correct value"). If they are purely structural, Division B can write them correctly without GT knowledge. If they are semantic, Division B cannot.

The seam does not resolve this. The `harness_contract.json` proposal assumes the assertions are structural, but the pre-seal checklist says `--run-visible-assertions` "should fail with AssertionError (baseline is wrong)" — which implies the assertions are semantic (they check the baseline against the GT). This is a contradiction in the seam that the Author's proposed fix does not resolve.

**Proposed sharpening:** The seam must distinguish between structural assertions (Division B can write) and semantic assertions (Division A must write and seal separately). The `harness_contract.json` covers the structural layer. A separate Division A artifact covers the semantic layer. Division B's harness calls both but only authors the structural one.

---

## On Claim 3 (Phase 2 prerequisite): The retrospective is necessary but the framing is too narrow

The Author proposes a retrospective: "for each contamination event, was the leaking term in the denylist at the time of construction?" This is the right question, but the framing assumes contamination events are the only signal. There is a second signal: **near-misses** — terms that were in the denylist and were caught, but whose synonyms were not caught and may have leaked silently.

A retrospective that only counts caught contamination events will undercount the true leak rate. The sentinel's false-negative rate (leaks it missed) is not observable from the sentinel's own output. The only way to estimate it is to run a post-hoc audit of mutator outputs from prior sandboxes and check whether the mutator's vocabulary in early iterations correlates with GT-class vocabulary that was not in the denylist.

**Pattern 10 (silent false-negative precision):** The seam's retrospective proposal conflates "sentinel reported no hits" with "no contamination occurred." These are not the same. The sentinel's silence is an architectural scope statement ("nothing in my denylist was found"), not a falsifiable claim ("no contamination occurred").

**Proposed sharpening:** The Phase 2 prerequisite should include both (a) the denylist-coverage retrospective the Author proposes, and (b) a mutator-output audit on 2-3 prior sandboxes: did the mutator's turn-1 vocabulary contain GT-class terms that were not in the denylist at construction time? If yes, the sentinel's false-negative rate is non-trivial and Phase 2 automation is premature.

---

## On the Open Question 1 reframe: Correct but incomplete

The Author correctly reframes from agent-vs-human to briefing-authorship-as-threat-surface. But there is a third channel the Author does not name: **evidence file structure**.

Division B receives the evidence files (data points). The evidence files are generated by Division A from the GT formula. The structure of the evidence files — which points are included, their range, their density, whether they cluster near a boundary — carries information about the GT class even when the formula is not stated.

Example: if the GT is a step function with a threshold at x=50, and Division A generates evidence points at x=48, 49, 50, 51, 52 with a visible discontinuity, Division B does not need to know the formula to infer "this is a threshold problem." The evidence structure is a structural hint that a grep-based sentinel cannot catch.

This is not a hypothetical. The seam's own sandbox_09 case ("thesis seed leaked structural hints") is an instance of this pattern at the thesis level. The same pattern applies at the evidence level.

**Proposed sharpening:** Open Question 1 should be expanded to include evidence file structure as a contamination channel. Division A must consider not just what vocabulary appears in the briefing, but what structure appears in the evidence files. This may require adversarial evidence generation (deliberately obscuring the threshold region, adding noise near boundaries, etc.) — which is a non-trivial addition to the Division A artifact set.

---

## Closure language audit

The seam states: "If Division B doesn't know the answer, it **cannot** leak it." This is closure language (Pattern 2). The sandbox_12 Lesson 1 falsifies it — Division B leaked through briefing vocabulary without knowing the GT. The Author's Turn 1 correctly identifies this, but the seam body has not been updated to remove the false closure claim. The seam should demote "cannot" to "is less likely to" or "has fewer channels through which to."

---

## Summary of new decisive claims introduced

1. **Two-layer denylist requirement:** The sentinel gate on the briefing requires a problem-class vocabulary layer (layer b) that is not derivable from the GT formula and is currently absent from the codification path.
2. **Structural vs semantic assertion distinction:** The `harness_contract.json` proposal contains a contradiction — the pre-seal checklist implies semantic assertions, but the proposal assumes structural ones. The seam must resolve which layer Division B authors.
3. **Mutator-output audit as Phase 2 prerequisite:** The retrospective must include a false-negative rate estimate, not just a denylist-coverage check.
4. **Evidence file structure as contamination channel:** Open Question 1's reframe is incomplete without naming evidence structure as a third channel alongside briefing vocabulary and orchestrator knowledge.

### Turn 3 — Claude-Author (2026-04-15) — Autonomous runner turn

The Skeptic's Turn 2 raises four new decisive claims. I'll address each in order, then assess whether any remain unresolved.

---

## On the two-layer denylist (Skeptic's Claim 1)

The Skeptic is correct that the denylist has two distinct layers with different derivation paths:

- **Layer (a) — GT-specific terms:** derivable from the formula (function names, constants, variable names, mathematical operators). Mechanical extraction is possible.
- **Layer (b) — problem-class vocabulary:** words that signal the *type* of problem to a mutator ("discrete", "exact", "integer", "threshold", "step"). Not derivable from the formula; requires adversarial enumeration.

The Skeptic is also correct that the sandbox_12 failure was a Layer (b) failure — "discrete" is not a term in any plausible GT formula, it is a problem-class descriptor. The sentinel gate on the briefing would not have caught it with only a Layer (a) denylist.

**WWYHTB for Layer (b) being enumerable at all:** Problem-class vocabulary is finite and domain-bounded. For a given problem domain (integer functions, differential equations, graph problems), the vocabulary that signals the class to a mutator is enumerable in advance — it is the vocabulary a mutator would use to *describe* the problem class if asked. This is a cognitive task that can be performed by Division A before authoring the briefing: "what words would a mutator use to describe this type of problem?" and then denylisting those words.

This is not a solved problem, but it is a tractable one. The seam should add Layer (b) to the Division A artifact set as an explicit step: **adversarial vocabulary enumeration** — Division A asks "what vocabulary would a mutator use to describe this problem class?" and adds those terms to the denylist before authoring the briefing.

The Skeptic's framing ("requires adversarial enumeration") is correct. I accept this as a decisive addition to the seam.

---

## On structural vs semantic assertions (Skeptic's Claim 2)

The Skeptic identifies a genuine contradiction in the seam. The pre-seal checklist says `--run-visible-assertions` "should fail with AssertionError (baseline is wrong)" — which implies the assertions check the baseline against the GT (semantic). But the `harness_contract.json` proposal assumes Division B can write assertions without GT knowledge (structural).

These cannot both be true. Let me resolve the contradiction:

**The visible assertions in `gate_harness.py` must be purely structural.** The purpose of `--run-visible-assertions` in the Level 3 falsification suite is to check that the mutator's output satisfies structural properties (output is an integer, output is in the expected range, output has the right type). The semantic check — "does the output equal the correct value?" — is performed by the scoring harness, which is a Division A artifact that Division B never sees.

The pre-seal checklist's statement that `--run-visible-assertions` "should fail with AssertionError (baseline is wrong)" is therefore a **documentation error** in the seam. The baseline model (`test_model.py`) should fail the structural assertions only if it produces structurally invalid output. If the baseline produces a structurally valid but semantically wrong answer, `--run-visible-assertions` should **pass** (the output is a valid integer) while the scoring harness fails (the integer is wrong).

**Proposed resolution:** The seam should explicitly state:
- Division B authors structural assertions (output type, range, format)
- Division A authors semantic assertions (output equals GT) in a separate sealed artifact
- The pre-seal checklist's "should fail with AssertionError" language should be corrected to "should pass structural assertions; semantic correctness is verified by Division A's sealed scorer"

This resolves the contradiction and clarifies the `harness_contract.json` scope: it covers structural assertions only.

---

## On the mutator-output audit (Skeptic's Claim 3)

The Skeptic correctly applies Pattern 10 (silent false-negative precision): "sentinel reported no hits" ≠ "no contamination occurred." The retrospective I proposed in Turn 1 only measures denylist coverage of *caught* events. It does not estimate the false-negative rate.

The Skeptic's proposed addition — a mutator-output audit on 2-3 prior sandboxes — is the right instrument. Specifically: did the mutator's turn-1 vocabulary contain GT-class terms that were not in the denylist at construction time?

**WWYHTB for this audit being feasible:** Prior sandbox run logs are preserved and the mutator's turn-1 output is recoverable. This is a factual question about log retention, not a methodological question. If the logs exist, the audit is cheap. If they don't, the audit is impossible and we must accept that the false-negative rate is unobservable from prior runs.

I accept this as a prerequisite addition. The Phase 2 prerequisite should read: (a) denylist-coverage retrospective on caught events, AND (b) mutator-output audit on 2-3 prior sandboxes if logs are available, with explicit acknowledgment that the false-negative rate is unobservable if logs are not retained.

**Additional implication:** This audit requirement is itself an argument for log retention as a first-class artifact. If we cannot estimate the sentinel's false-negative rate without prior run logs, then run logs are a prerequisite for the Phase 2 investment decision. The seam should note this.

---

## On evidence file structure as contamination channel (Skeptic's Claim 4)

The Skeptic names a third contamination channel I did not address in Turn 1: the structure of the evidence files themselves. The example is apt — a step function with evidence points clustered near the threshold reveals the threshold's existence even without naming it.

**WWYHTB for this being a real threat:** The mutator uses the evidence files to form hypotheses about the GT. If the evidence structure is informative about the GT class (not just the GT values), the mutator gets a structural hint that the sentinel cannot catch. This is true whenever the evidence generation strategy is non-uniform — which it almost always is, because Division A generates evidence to be informative for the experiment, not to be uninformative about the GT class.

The Skeptic is correct that this is a distinct channel from briefing vocabulary and orchestrator knowledge. The sandbox_09 case ("thesis seed leaked structural hints") is an instance at the thesis level; the same pattern applies at the evidence level.

**However, the fix is more constrained than the Skeptic implies.** Evidence files must be informative enough for the mutator to make progress — otherwise the experiment has no signal. The goal is not to make evidence files uninformative, but to make them uninformative about the GT *class* while remaining informative about the GT *values*. This is a non-trivial constraint that may not always be satisfiable.

**Proposed addition to Open Question 1:** Evidence file structure is a contamination channel. Division A must consider: does the evidence generation strategy reveal the GT class (threshold, periodic, polynomial degree) through point density, range, or clustering? If yes, adversarial evidence generation (adding noise near boundaries, using uniform sampling rather than informative sampling) may be required. This is a research question, not a solved one — it should be added to the seam's open questions, not the codification path.

---

## On the closure language audit

The Skeptic correctly flags "cannot" in "If Division B doesn't know the answer, it **cannot** leak it." The sandbox_12 Lesson 1 falsifies this. The seam body should demote this to "has fewer channels through which to leak it" or "cannot leak it through direct knowledge, but may still leak through briefing vocabulary, evidence structure, or orchestrator channels."

I accept this as a seam body correction.

---

## Summary of resolved and unresolved claims

All four of the Skeptic's new decisive claims from Turn 2 have been addressed:

1. **Two-layer denylist** — accepted; Layer (b) adversarial vocabulary enumeration added to Division A artifact set.
2. **Structural vs semantic assertion distinction** — resolved; the contradiction in the seam is a documentation error; structural assertions are Division B's scope, semantic assertions are Division A's sealed scorer.
3. **Mutator-output audit as Phase 2 prerequisite** — accepted; added with the caveat that feasibility depends on log retention, which is itself now a first-class requirement.
4. **Evidence file structure as contamination channel** — accepted; added to Open Questions

### Turn 4 — Claude-Skeptic (2026-04-15) — Autonomous runner turn

The Author's Turn 3 addresses all four of my Turn 2 claims. Before raising, I need to apply pressure to the resolutions themselves — accepting a response is not the same as the response being correct.

---

## On the structural vs semantic assertion resolution: the contradiction is not fully resolved

The Author's resolution is that `--run-visible-assertions` should check structural properties only, and the pre-seal checklist's "should fail with AssertionError (baseline is wrong)" is a documentation error. This is internally consistent, but it creates a new problem the Author does not address.

**What would have to be true for this resolution to hold:** The Level 3 falsification suite's purpose is served by structural assertions alone. But the seam's own description of the Level 3 suite says it is a "falsification suite" — its job is to falsify candidate hypotheses. Structural assertions (output is an integer, output is in range) do not falsify hypotheses about the GT. They only verify that the mutator produced a well-formed output. A mutator that outputs `42` when the GT is `137` passes all structural assertions and is not falsified.

If the visible assertions are purely structural, the Level 3 falsification suite is not doing falsification — it is doing format validation. The "falsification" label is then misleading, and the gate harness's role in the experimental apparatus is weaker than the seam implies.

**The Author's resolution trades one contradiction for another:** The original contradiction was "Division B writes assertions without GT knowledge, but the assertions check against GT." The resolution says "Division B writes structural assertions only." But now the falsification suite is not falsifying anything about the GT. The Author has resolved the information-barrier contradiction by demoting the gate harness's epistemic role, without acknowledging that demotion.

**Proposed sharpening:** The seam must explicitly state what the gate harness's `--run-visible-assertions` flag is actually testing, and whether that is sufficient for the Level 3 falsification suite's stated purpose. If structural assertions are all it does, rename it `--run-structural-checks` and remove the "falsification suite" label. If semantic falsification is required, the seam must explain how Division B authors semantic assertions without GT knowledge — which may require a different architecture (e.g., Division A provides sealed assertion predicates that Division B's harness calls without seeing their implementation).

---

## On the two-layer denylist resolution: the tractability claim is unsupported

The Author accepts Layer (b) and proposes "adversarial vocabulary enumeration" — Division A asks "what vocabulary would a mutator use to describe this problem class?" This is framed as "not a solved problem, but a tractable one."

**Pattern 3 (frustration-anchored diagnosis):** The tractability claim is asserted, not evidenced. The sandbox_12 failure is the only data point we have on Layer (b) enumeration, and it shows that "discrete" was not enumerated by Division A before authoring the briefing. If Division A had been asked to enumerate problem-class vocabulary before sandbox_12, would "discrete" have appeared? We don't know. The Author's tractability claim is optimistic without evidence.

**What would have to be true for Layer (b) enumeration to be tractable:** The set of vocabulary that signals a problem class to a mutator is (a) finite, (b) enumerable by Division A without running the mutator, and (c) stable across mutator versions. None of these are established. A mutator trained on different data may use different vocabulary to describe the same problem class. The enumeration that works for one mutator may miss the vocabulary of another.

This is not a reason to abandon Layer (b) — it is a reason to be explicit that Layer (b) enumeration is a research question, not a solved engineering step. The seam should not add it to the Division A artifact set as if it were a routine task. It should be added to Open Questions alongside evidence file structure.

---

## On the mutator-output audit: the log retention implication is underspecified

The Author accepts the audit and adds "run logs are a prerequisite for the Phase 2 investment decision." This is correct but underspecified. The seam does not say:

1. What constitutes a "run log" for this purpose (full mutator output? turn-1 only? all turns?)
2. Where run logs are currently stored (or whether they are stored at all)
3. Who is responsible for ensuring log retention going forward

Without these specifics, "log retention as a first-class requirement" is a statement of intent, not a codified practice. The seam should either (a) point to an existing log retention mechanism, or (b) add log retention as an explicit open question with a named owner.

---

## On evidence file structure: the "uninformative about class, informative about values" constraint

The Author accepts this as an open question and adds the correct framing: the goal is evidence that is uninformative about the GT *class* while remaining informative about the GT *values*. The Author then says this "may not always be satisfiable."

This is the right epistemic position, but it has an implication the Author does not draw: **if the constraint is not always satisfiable, then some GT choices are structurally incompatible with the Division A/B protocol.** A step function with a sharp threshold cannot be evidenced without revealing the threshold's existence. If Division A chooses such a GT, the information barrier is broken at the evidence layer regardless of briefing hygiene.

This means GT selection is itself a Division A task that must be constrained by the information barrier's requirements — not just evidence generation. The seam should note that GT selection criteria include "does this GT class allow uninformative-about-class evidence generation?" as a filter. This is a non-trivial constraint on the experimental design space.

---

## Closure language audit on the Author's Turn 3

The Author says "All four of the Skeptic's new decisive claims from Turn 2 have been addressed." This is closure language (Pattern 2). The structural/semantic assertion resolution introduces a new unresolved contradiction (falsification suite demotion). The Layer (b) tractability claim is asserted without evidence. "Addressed" does not mean "resolved" — the Author has responded to all four claims, but two of the responses introduce new problems.

---

## Summary of new decisive claims

1. **Gate harness epistemic demotion:** The structural-assertions-only resolution demotes the Level 3 falsification suite from falsification to format validation without acknowledging the demotion. The seam must either rename the flag or explain how semantic falsification is achieved under the information barrier.
2. **Layer (b) tractability is unsupported:** Adversarial vocabulary enumeration is a research question, not a routine Division A task. It should be in Open Questions, not the codification path.
3. **Log retention is underspecified:** The Phase 2 prerequisite's log retention requirement needs specifics (what logs, where stored, who owns it) to be actionable.
4. **GT selection as information-barrier constraint:** If some GT classes cannot produce uninformative-about-class evidence, GT selection must be filtered by this criterion. This is a constraint on the experimental design space that the seam does not currently state.

### Turn 5 — Claude-Author (2026-04-15) — Autonomous runner turn

The Skeptic's Turn 4 raises four new decisive claims. I'll address each, then assess convergence.

---

## On gate harness epistemic demotion (Skeptic's Claim 1)

The Skeptic correctly identifies that my Turn 3 resolution trades one contradiction for another: if `--run-visible-assertions` checks only structural properties, the "Level 3 falsification suite" label is misleading — format validation is not falsification.

Let me resolve this properly rather than papering over it.

**The correct architecture under the information barrier:**

The gate harness can achieve semantic falsification without Division B knowing the GT, through **sealed predicate injection**. Division A authors a sealed file (e.g., `division_a_sealed_predicates.py`) containing functions like `is_correct(output, input)` that return True/False. Division B's harness imports and calls these functions without seeing their implementation — the file is sealed (hash-pinned) and Division B treats it as a black box.

Under this architecture:
- Division B authors the harness structure (flag handling, output parsing, error reporting)
- Division A authors the predicate implementations (semantic correctness checks)
- `--run-visible-assertions` calls both structural checks (Division B) and sealed predicates (Division A)
- The pre-seal checklist's "should fail with AssertionError (baseline is wrong)" is correct — the baseline fails the sealed predicates, not the structural checks

This resolves the contradiction without demoting the falsification suite. The flag name stays. The epistemic role stays. Division B implements the harness skeleton; Division A provides the semantic payload as a sealed import.

**Implication for `harness_contract.json`:** The contract should specify not just flag names and exit codes, but also the sealed predicate interface — function signatures Division B's harness must call, without the implementations. Division A provides the implementations separately.

This is a genuine architectural addition, not just a naming fix. I accept the Skeptic's claim as decisive and propose sealed predicate injection as the resolution.

---

## On Layer (b) tractability (Skeptic's Claim 2)

The Skeptic is correct that I asserted tractability without evidence. The sandbox_12 case is the only data point, and it shows Division A *failed* to enumerate "discrete" before authoring the briefing. My tractability claim was optimistic.

**Revised position:** Layer (b) adversarial vocabulary enumeration is a research question, not a routine Division A task. It should be moved from the codification path to Open Questions. The seam should state:

- Layer (b) exists as a conceptual requirement
- No reliable enumeration procedure is currently established
- The sentinel gate on the briefing catches Layer (b) failures post-hoc (after Division B has already received the briefing), which is too late
- Until Layer (b) enumeration is solved, the information barrier has a known gap at the briefing vocabulary surface

**Practical implication:** The sentinel gate on the briefing (my Turn 1 proposal) is still worth doing — it catches Layer (a) failures and any Layer (b) terms that happen to be in the denylist. But it should not be described as closing the briefing contamination channel. It reduces it.

I accept the Skeptic's claim. Layer (b) moves to Open Questions.

---

## On log retention underspecification (Skeptic's Claim 3)

The Skeptic is correct that "log retention as a first-class requirement" is a statement of intent without operational specifics. Let me specify:

**What constitutes a run log for this purpose:** Turn-1 mutator output is the minimum required for the false-negative rate audit. Full run logs (all turns) are preferable but not required for the Phase 2 prerequisite. The audit question is specifically: "did the mutator's *first* response contain GT-class vocabulary not in the denylist?" — turn-1 is the contamination signal; later turns may reflect the mutator's own reasoning rather than priming.

**Where run logs are currently stored:** This is a factual question I cannot answer from the seam alone. The seam should add an explicit open question: "Are turn-1 mutator outputs currently retained as artifacts? If not, what is the retention mechanism going forward?" This is a named gap, not a solved requirement.

**Who owns it:** Division A, since Division A is responsible for the pre-registration and the experimental record. The seam should state this explicitly.

I accept the Skeptic's claim. The log retention requirement needs these three specifics added to the seam.

---

## On GT selection as information-barrier constraint (Skeptic's Claim 4)

The Skeptic draws the correct implication from my Turn 3 acceptance: if some GT classes cannot produce uninformative-about-class evidence, then GT selection must be filtered by this criterion. I did not draw this implication, and the Skeptic is right to flag it.

**WWYHTB for this being a real constraint:** Some GT classes have evidence structures that are inherently class-revealing. A step function's discontinuity is visible in any dense evidence set. A periodic function's period is visible in any evidence set spanning more than one period. These are not edge cases — they are common GT classes in the ZTARE experimental space.

**The constraint in one sentence:** GT selection is a Division A task that must include the filter "does this GT class allow evidence generation that is uninformative about the GT class?" If the answer is no, the GT is incompatible with the Division A/B protocol and must be rejected or the protocol must be extended.

**Extension path:** For GT classes that cannot satisfy the constraint, Division A may need to use **adversarial evidence generation** — deliberately sparse sampling near class-revealing features (boundaries, discontinuities, periods), or adding structured noise that obscures the class signal while preserving value information. This is a non-trivial research problem. The seam should add it to Open Questions alongside Layer (b) enumeration.

I accept the Skeptic's claim as decisive. GT selection criteria should be added to the seam.

---

## On the closure language audit

The Skeptic correctly flags my Turn 3 closure language ("All four of the Skeptic's new decisive claims from Turn 2 have been addressed"). I should have said "responded to" — two of the responses introduced new problems rather than resolving the underlying claims. I accept the correction.

---

## Summary of the seam's current state

After four turns, the seam has accumulated the following additions beyond its original body:

**Accepted additions to the codification path:**
1. Sentinel gate on the Division A briefing (Turn 1) — reduces but does not close the briefing contamination channel
2. `harness_contract.json` as Division A artifact — covers structural assertion interface and sealed predicate function signatures
3. Sealed predicate injection — Division A provides semantic assertion implementations as a sealed import; Division B's harness calls them without seeing the implementation
4. Phase 2 prerequisites: (a) denylist-coverage retrospective on caught events, (b) mutator-output audit on turn-1 logs if available
5. Log retention: turn-1 mutator output as a required artifact; Division A owns retention; current retention status is an open question

**Moved to Open Questions:**
6. Layer (b) adversarial vocabulary enumeration — research question, not routine task
7. Evidence file structure as contamination channel — adversarial evidence generation is a research problem
8. GT selection as information-barrier constraint — GT classes that cannot produce uninformative-about-class evidence are incompatible with the Division A/B protocol

**Seam body corrections:**
9. Demote "cannot" to "has fewer channels through which to leak" in the Division B claim
10. Correct the pre-seal checklist's "should fail with AssertionError" language to reflect that structural assertions pass for well-formed output; semantic failure is via sealed predicates

The Skeptic's four Turn 4 claims are now addressed. I have no new decisive claims to introduce. The seam's open questions are correctly scoped as research problems rather than engineering steps. The codification path is internally consistent under the sealed predicate injection architecture.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude-Skeptic (2026-04-15) — Autonomous runner turn

The Author's Turn 5 addresses all four of my Turn 4 claims. Before raising, I need to pressure the resolutions themselves — particularly the sealed predicate injection proposal, which is the most architecturally significant addition and was introduced in Turn 5 without prior scrutiny.

---

## On sealed predicate injection: correct direction, but the information barrier is not fully closed

The Author proposes that Division A authors `division_a_sealed_predicates.py` containing `is_correct(output, input)` functions, which Division B's harness imports as a black box. This resolves the structural/semantic contradiction cleanly. But there is a residual leak vector the Author does not address.

**What would have to be true for this to fail:** Division B imports the sealed predicate file. To import it, Division B must know the file's name, its location, and its function signatures. The function signature `is_correct(output, input)` is neutral. But the *file name* `division_a_sealed_predicates.py` and the *import path* are visible to Division B — and if the file name contains GT-class vocabulary (e.g., `division_a_threshold_predicates.py`), the import statement itself is a leak vector.

This is a narrow concern, but it is the same pattern as the `discrete_exact` scoring mode name leak in sandbox_12: an internal implementation detail's name carrying structural information. The fix is the same: the sealed predicate file must have a neutral name (e.g., `sealed_assertions.py`) specified in the `harness_contract.json`, not chosen by Division A ad hoc.

This is a small addition, not a new decisive claim — it is a consequence of applying the existing denylist logic to file names. I flag it but do not hold on it.

---

## On Layer (b) tractability: the revised position is correct and complete

The Author correctly demotes Layer (b) to Open Questions and states the practical implication: the sentinel gate on the briefing reduces but does not close the briefing contamination channel. This is the right epistemic position. No new pressure needed.

---

## On log retention: the specifics are adequate

The Author specifies turn-1 mutator output as the minimum, names Division A as the owner, and correctly identifies current retention status as an open question. The three specifics the Skeptic requested are present. No new pressure needed.

---

## On GT selection as information-barrier constraint: the resolution is correct but the extension path needs one clarification

The Author accepts GT selection as a Division A filter and proposes adversarial evidence generation as the extension path for incompatible GT classes. This is correct. One clarification: the Author frames adversarial evidence generation as "deliberately sparse sampling near class-revealing features." But sparse sampling near a boundary is itself a signal — the *absence* of points near x=50 tells the mutator there is something notable at x=50. The correct adversarial strategy is uniform sampling (not sparse near boundaries), which obscures the boundary by treating all regions equally. The Author's framing inverts the correct direction.

This is a technical correction to the Open Question's framing, not a new decisive claim. I flag it for the seam body.

---

## Checking for any unaddressed decisive claims across all turns

Running through the full debate:

- Turn 1 (Author): four proposed additions → all addressed by Turn 3 or Turn 5
- Turn 2 (Skeptic): four new claims → all addressed by Turn 3 or Turn 5
- Turn 3 (Author): resolutions → two introduced new problems, caught in Turn 4
- Turn 4 (Skeptic): four new claims → all addressed by Turn 5
- Turn 5 (Author): sealed predicate injection (new architecture) → one narrow residual (file naming), flagged above but not decisive

The two flags I raise in this turn (sealed predicate file naming, adversarial evidence generation direction) are corrections to implementation details, not new decisive architectural claims. They do not change the shape of the proposed fix — they refine it.

The seam's summary in Turn 5 accurately reflects the accumulated additions. The open questions are correctly scoped. The codification path is internally consistent.

I have no new decisive claims to introduce.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 7 — Operator (2026-04-17) — Post-implementation empirical findings

The Division A/B protocol was applied to GP-078 (sequence law recovery, A005185 Hofstadter-Maler-Conway). The sandbox was hand-built without following a formal checklist. A contamination audit and domain-expert rubric review were run after construction. Three new findings emerged that are not covered by the debate's converged decisions.

---

## Finding 1: Sentinel blind spot — gate_harness.py not scanned

`leak_sentinel.py` line 24 `MUTATOR_VISIBLE_FILENAMES` contained only `{project_charter.md, thesis.md, test_model.py, evidence.txt}`. It did not include `gate_harness.py`, `evidence_holdout.txt`, or `evidence_farther_tail.txt`.

Result: `gate_harness.py` line 1 contained `"""Gate harness for GP-078 A005185 (Hofstadter-Maler-Conway sequence)."""` — a total Division B compromise. The sentinel did not catch it because it was not scanning that file.

**Fix applied (2026-04-17):** Added `gate_harness.py`, `evidence_holdout.txt`, `evidence_farther_tail.txt` to `MUTATOR_VISIBLE_FILENAMES`.

**Lesson:** The sentinel scan surface must cover ALL Division B artifacts, not just the ones that existed when the sentinel was first written. Every new file type added to the Division B artifact set must also be added to the sentinel. The spec (GP-072 spec Phase 4) now explicitly lists the full scan surface.

---

## Finding 2: Rubric structural bias against the correct answer class

A domain-expert reviewer (mathematician specializing in integer sequences and recurrences) reviewed the GP-078 rubric and found a **fatal structural bias**: the rubric's vocabulary, dimensions, and persona all assume the answer is a closed-form algebraic expression `f(n) = <formula of n>`. The actual answer is a self-referential recurrence `a(n) = a(n - a(n-1)) + a(n - a(n-2))` — no known closed form exists.

Specific failures:
- **No dimension for recurrence/mechanism recovery.** The rubric scores curve-fitting quality but has no dimension rewarding discovery that S(n) depends on its own prior values.
- **Parsimony is ill-defined for recurrences.** "Fewest free parameters and lowest expression complexity" makes sense for `A*sin(B*n + C)` but not for a recurrence with zero free parameters.
- **Persona actively hostile to the correct answer.** "Derived step-by-step from observed (n, S(n)) pairs" biases toward regression, not toward structural relationship discovery like `a(12) = a(6) + a(6) = 8`.
- **Polynomial degree penalty too loose.** N-2 = 38 for 40 points; a degree-30 polynomial is still memorization.

**This failure mode is distinct from contamination.** It is not about GT information leaking into Division B — it is about Division B constructing a rubric that is structurally incompatible with the GT's answer class. Division B cannot check this because Division B doesn't know the GT. This is a Division A responsibility: after Division B produces the rubric, Division A (or a GT-cleared reviewer) must verify that the rubric is well-posed for the actual answer class.

**New protocol step:** Domain-expert review (Phase 5 in the spec) with explicit answer-class compatibility check. This requires GT knowledge, so the reviewer must be Division A-cleared.

---

## Finding 3: Directory and filename contamination vectors

The project directory was named `gp078_a005185_01` — containing the OEIS identifier. The rubric file was named `gp078_a005185.json`. Both are visible to any agent that can observe `os.getcwd()`, `__file__`, or the filesystem path.

**Fix applied:** Directory renamed to `gp078_seq_recovery_01`, rubric renamed to `gp078_sequence_01.json`.

**Lesson:** The sentinel scans file contents but not directory names, filenames, or path components. The spec (Phase 4.2) now requires scanning these as well.

---

## Impact on the seam's codification path

These three findings add to the accumulated additions from Turns 1-6:

11. **Sentinel scan surface must be exhaustive and maintained** — every new Division B file type must be added to the scan list. (Finding 1)
12. **Domain-expert rubric review with GT knowledge is a required protocol step** — Division B cannot verify answer-class compatibility without GT. This is Phase 5 in the spec, not in the original seam. (Finding 2)
13. **Sentinel must scan paths, not just contents** — directory names, filenames, and string literals in Python files are contamination vectors. (Finding 3)

These are empirical findings from the first real application of the Division A/B protocol to a new domain (integer sequence recovery). They validate the seam's core thesis (contamination is an information flow problem) while extending the protocol surface the seam did not anticipate.
