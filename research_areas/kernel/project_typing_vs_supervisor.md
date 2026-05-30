# Project Typing vs. Supervisor Recurrence

## Status

Private architecture note for review.

Purpose:

- capture the architectural lesson surfaced by the EU experiment
- separate it from the mutator hardening thread
- give Claude a clean object to react to

## Inception

This note comes directly from the EU project sequence:

1. `eu_union_stability`
   - started from a broad question about whether incomplete integration makes the EU non-viable
   - drifted into a narrower mechanism-validation object:
     - absent automatic fiscal transfers amplify divergence during asymmetric shocks

2. `eu_union_load_bearing_pillars`
   - was created because the drift made clear that the original question had bundled:
     - mechanism validation
     - pillar ranking
     - forecast / disappearance logic
   - these should not have lived in one project

The important point is:

- this was **not** just a prompting problem
- it exposed a missing architectural layer in ZTARE

## The Problem

ZTARE currently relies too heavily on:

- thesis prose
- rubric wording
- prompt instructions

to determine what kind of epistemic object a project actually is.

That is too weak.

Because of this, a broad question can drift toward the sharpest seam that:

- has the clearest discriminator
- has the strongest evidence frontier
- best fits the evaluator contract

This is what happened in the EU case.

## What The Experiment Revealed

There are at least three distinct project types hiding inside what looked like one research question:

### 1. Mechanism Project

Question shape:

- does a specific causal mechanism hold?

Example:

- does missing automatic fiscal stabilization amplify divergence beyond heterogeneity baseline?

### 2. Pillar-Ranking Project

Question shape:

- which missing pillars are actually central for durable equilibrium?

Example:

- is legal supremacy or fiscal stabilization more central now?

### 3. Forecast Project

Question shape:

- what is the probability of a defined event by a defined horizon?

Example:

- what is the probability of material union failure by January 1, 2035?

ZTARE can currently sort of do all three, but only by forcing them through the same generic project container.

That is the architectural gap.

## Why This Looks Similar To Supervisor

This pattern resembles the supervisor/control-plane logic because both involve:

- explicit structure
- state
- governance
- boundaries on what work is being done

But the two layers are not the same.

### Supervisor (Layer 3)

Concern:

- organization of labor
- who does what next
- packet routing
- approvals
- manifests
- state transitions across work programs

This logic is general and can apply to almost anything.

### Project Typing / Slicing (ZTARE Layer)

Concern:

- what kind of epistemic object this project is
- what kinds of claims it is allowed to answer
- what end states or event boundaries define the project
- what inheritance relationships exist between projects

This is not primarily labor routing.

It is **evaluation-contract typing**.

So the correct view is:

- there is a recurrence of governance logic
- but we should resist collapsing the two layers into one system too early

## Core Architectural Question

Should ZTARE gain a lightweight project-typing layer, or should this remain a prompt-only discipline until a later supervisor-style unification?

## Option A — Keep It In Prompting Only

### Description

Do nothing structural.

Rely on:

- better initial project prompts
- cleaner rubrics
- operator discipline

### Pros

- zero new code
- maximum flexibility
- no premature ontology lock-in

### Cons

- drift risk remains high
- project types stay implicit
- inheritance remains manual
- synthesis and validator cannot reliably know the intended object
- repeated mistakes likely across domains

### Verdict

Too weak.

Useful as a temporary operator habit, not as architecture.

## Option B — Add A Lightweight Project Manifest Layer

### Description

Add a small explicit project manifest, e.g.:

- `project_manifest.json`

Potential fields:

```json
{
  "project_type": "pillar_ranking",
  "primary_question": "Which missing integration pillars are central for durable equilibrium?",
  "secondary_question": "Through 2035, is fragile intactness more likely than material failure?",
  "end_states": [
    "durable_equilibrium",
    "fragile_but_intact",
    "material_union_failure"
  ],
  "event_boundary": "major member exit, euro breakup, or sustained multi-state breakdown of core union functions",
  "forecast_horizon": "2035-01-01",
  "inherits_from": [
    "eu_union_stability"
  ],
  "allowed_outputs": [
    "pillar_ranking",
    "bounded_forecast_tilt"
  ]
}
```

Validator, synthesizer, and workspace/compiler can read it.

### Pros

- makes project ontology explicit
- reduces drift
- enables inheritance
- clarifies what kind of answer is allowed
- much smaller than building a local supervisor
- reusable across domains

### Cons

- adds a new artifact class
- requires deciding an initial project-type ontology
- some risk of premature formalization

### Verdict

Best next step.

## Option C — Rebuild A Local Supervisor-Like Layer Inside ZTARE

### Description

Create local routing/state logic for projects:

- slicing
- transitions
- work packets
- local manifests
- maybe branching / state transitions / approvals

### Pros

- conceptually elegant
- unifies local project slicing with broader governance logic
- could later compose with the real supervisor

### Cons

- too much system too early
- high risk of rebuilding layer 3 locally
- distracts from the real immediate need, which is object typing
- increases complexity before ontology is stable

### Verdict

Overbuilt for now.

## Option D — Move Everything To Supervisor

### Description

Treat project slicing as just another supervisor concern.

Do not add local project typing.
Instead make the supervisor own project manifests and project-type logic.

### Pros

- single governance center
- elegant long-run possibility

### Cons

- forces a layer-3 dependency onto layer-1 experimentation
- slows down local iteration
- mixes labor routing with epistemic object typing
- makes ZTARE less portable as a standalone engine

### Verdict

Too coupled for the current stage.

## Proposed Solution

Adopt **Option B**:

- a lightweight project manifest layer
- local to ZTARE / project architecture
- not a mini-supervisor

### What It Should Do

1. declare project type
   - `mechanism`
   - `pillar_ranking`
   - `forecast`

2. declare main question and optional subordinate question

3. declare end states / event boundary / horizon where relevant

4. declare inheritance
   - e.g. use prior report/evidence/axioms/derived constraints

5. constrain allowed outputs
   - e.g. a pillar-ranking project can emit:
     - ranking
     - fragile-vs-durable classification
     - bounded forecast tilt
   - but not a point probability unless explicitly declared

## Why This Should Stay Separate From Supervisor For Now

Because the concerns are different:

- **Supervisor**
  - labor, routing, orchestration

- **Project manifest**
  - epistemic object typing

They may eventually connect.

For example, a future supervisor could read project manifests and use them as context.

But today the right sequence is:

1. make project typing explicit locally
2. let validator / synthesis / workspace consume it
3. only later decide whether supervisor should ingest the same artifact

That preserves modularity.

## Initial Recommendation

Build the smallest viable project-typing layer:

### MVP

1. add `project_manifest.json`
2. support 3 types:
   - `mechanism`
   - `pillar_ranking`
   - `forecast`
3. teach:
   - validator
   - synthesizer
   - workspace/compiler
   to read it
4. use it only for:
   - question typing
   - end-state typing
   - inheritance / allowed-output constraints

### Do Not Yet Build

- local project router
- local approval engine
- packet transitions
- local mini-supervisor

## Final Recommendation

Yes, it is better to split this out into its own note.

And yes, the right architectural move is:

- **add explicit project typing**
- **keep it separate from supervisor for now**

The supervisor pattern is related because both are governance structures.

But the local ZTARE need is narrower:

- make the epistemic object explicit
- do not rebuild the organization-of-labor layer locally unless later evidence shows that is necessary

## Question For Claude

Please evaluate:

1. whether Option B is actually the right minimum architecture
2. whether the proposed `project_type` ontology is too early / too rigid
3. whether the supervisor distinction is real or whether this is actually a local recurrence that should be unified sooner
4. what the smallest implementation slice should be if we proceed

## Claude Response - Turn 1

### Diagnosis: agree. Proposal: directionally right, materially overbuilt. There's a smaller artifact that captures the central piece without locking in a premature ontology.

#### What I agree with

The drift is real and is not a prompting problem. The EU sequence shows that a broad question, under adversarial pressure, gets shaved down to whatever sharp seam the evidence frontier and the evaluator contract jointly favor. That is the system working as designed — but the operator wanted three different objects answered, and the system collapsed them into the one it could most defensibly close.

Option A is too weak. "Better prompts" is not a defense against an apparatus that is structurally biased toward sharpest-seam convergence.

Options C and D are correctly rejected. Local supervisor logic is layer-3 work that doesn't earn its keep here, and pushing project typing up to the real supervisor couples experimental iteration to a governance plane that should stay decoupled.

The disagreement is about Option B, specifically about how much typing and how much integration.

#### Three things wrong with Option B as proposed

**1. The ontology is unfounded after n=1.**

`mechanism / pillar_ranking / forecast` is a generalization from one project. The EU experiment surfaced these three because the EU domain has those three sub-questions. Central Station might surface `feasibility / unit_economics / market_size_validation`. A medical project might surface `mechanism / dose_response / population_generalization`. There is no reason to believe the EU's three types are a natural ontology of research objects rather than a local feature of one political-economy question.

Locking in three types now means every future project either fits the mold (artificial) or the ontology grows (lock-in cost). The right time to formalize a type system is after you've seen the patterns repeat across at least three distinct domains. We have one.

**2. The typed field is exactly the soft surface Turn 45 just named.**

We literally named the lesson last turn: any single LLM-emitted classification field that drives a Python branch is a drift surface, and the fix is typed decomposition. Now the proposal is to introduce `project_type: "pillar_ranking"` as a single string that validator, synthesizer, and workspace branch on. This is the exact failure mode, just at a different layer.

If `project_type` is operator-authored (not LLM-emitted), the soft-surface argument is weaker but not gone — the operator can still mislabel under pressure to make a forecast project look like a mechanism project so it can earn 100. The ontology creates an incentive to game the label.

**3. Most of the central work is already done by GP-014 + GP-015.**

The concrete failure mode the manifest is supposed to prevent is "a forecast project emits an established-tense conclusion." But GP-014 caps that at 67–83 in the scorer, and GP-015 forbids the synthesis chain from upgrading deferred to established. The defense already exists at two layers below the manifest. What does adding `allowed_outputs: ["pillar_ranking", "bounded_forecast_tilt"]` give us that the deferred-confirmation cap doesn't?

It gives us *nameable* output constraints, which is useful for operator clarity. It doesn't give us new adversarial robustness. So the manifest is a UX artifact in the places where I think it's strongest, not a hardening artifact.

#### The smaller alternative: a charter, not a manifest

What's actually missing is one thing: **the meta-judge has no explicit anchor for what this project is supposed to be answering.** The rubric tells it how to score; the thesis tells it what's claimed; nothing tells it what the project was scoped to do. So when the thesis drifts, the meta-judge has no grounds to call drift — it can only score what's in front of it.

The fix is a `project_charter.md` (markdown, operator-authored, one page). Required sections:

```
# Core Question
What is this project trying to answer?

# Out of Scope
What questions is this project deliberately not answering?

# End States
What does success look like? What does failure look like?

# Inheritance
Which prior projects' evidence and constraints does this build on?
```

That's the whole artifact. No `project_type`. No `allowed_outputs` enum. No JSON schema. No Python branching.

The charter is consumed in exactly one place: **the meta-judge prompt.** The evaluator gets the charter as context alongside the rubric and the thesis. If the thesis drifts outside the charter's `Core Question` or violates `Out of Scope`, the meta-judge has explicit grounds — in natural language, against an operator-authored anchor — to call drift and apply a structural penalty (or refuse to score, depending on how strict we want to be).

This is not Option A with extra steps. The difference from Option A is:

- Option A relies on the operator writing good prompts and hoping the system stays on course. The charter is *not in the operator's prompt to themselves* — it's in the *evaluator's prompt*, every iteration, as a typed slot that the meta-judge must check the thesis against.
- Option A has no typed fields. The charter has four typed sections that synthesis and evidence-compiler can also parse loosely (`Inheritance` is the only one that needs structured parsing — and a one-line parent pointer is enough).
- Option A has no inheritance. The charter has inheritance as a first-class slot.

The charter is the smallest thing that makes the project's epistemic boundaries legible to the apparatus without locking in an ontology of what kinds of projects exist.

#### Why natural language is correct here

The "soft-surface decomposition" pattern from Turn 45 says: when a model emits a single string that drives a Python branch, decompose into typed booleans. That pattern is about *model-emitted* fields driving *deterministic* decisions. The charter is the inverse: an *operator-emitted* document driving *model* reasoning. The asymmetry matters.

For deterministic Python branches, typed booleans are correct because Python can't reason flexibly about a string. For LLM reasoning, free-form natural language with required sections is correct because the LLM can reason about text more flexibly than it can reason about a typed enum, and because the operator can express drift conditions ("not in scope: forecasting union failure by a specific date") that don't fit any predefined ontology.

This is the right shape of governance for the layer we're at: operator authors a constraint document, model reasons against it, no new Python branches, no ontology.

#### What I'd defer

Three things should wait:

1. **The `project_type` ontology.** Wait until n≥3 distinct domains have run. Then look at the actual drift patterns and ask whether a small ontology would have prevented them. If yes, formalize then. If the drift modes are project-specific, the ontology was always going to be artificial.

2. **`allowed_outputs` enums.** GP-014 and GP-015 already do this work at the scorer and synthesis layers. Adding it as a third constraint at the manifest layer is defense-in-depth at a stage where we don't yet have evidence the existing defenses fail.

3. **Validator and workspace integration.** Only the meta-judge needs to read the charter initially. Synthesis can read the `Inheritance` line to resolve parent evidence, but doesn't need the rest. Workspace doesn't need it at all. Three consumers at once is the integration cost trap.

#### Answers to the four questions

**1. Is Option B the right minimum architecture?** No. Option B is too much. The right minimum is a charter (one markdown file, four sections, one consumer) — not a manifest with a project-type ontology and three consumers. The charter captures the central piece (operator-authored scope anchor) without locking in an ontology or creating a soft-surface gaming target.

**2. Is the proposed `project_type` ontology too early?** Yes. n=1 is not enough to formalize a type system. The three types are real distinctions, but they're not necessarily *the* three distinctions, and a typed enum will distort future projects to fit. Use natural language until n≥3 across distinct domains.

**3. Supervisor distinction: real or premature collapse?** Real. The note's framing is correct — supervisor is labor routing, project typing is epistemic object typing. Don't unify them now. The eventual unification, if it happens, is "supervisor consumes charters as context," which preserves modularity.

**4. Smallest implementation slice.** 

- Add `project_charter.md` to each project root (operator writes it; takes ~5 minutes per project).
- Modify the meta-judge prompt assembly in `autoresearch_loop.py` to read the charter and inject it as a `# PROJECT CHARTER` section above the rubric.
- Add one structural rule to the meta-judge contract: "If the thesis materially drifts from the Core Question or violates the Out of Scope clause, emit `drift_detected = true` and `drift_rationale = ...`."
- Hard cap: `drift_detected = true` caps the score at 50, and the iteration's loop control state should treat the iteration as a drift event (not a stagnation event — these need different recovery actions).
- Synthesis reads `Inheritance` only, as a one-line parent pointer. Nothing else.
- Workspace does not change.

That is approximately 30-50 lines of Python and one new file convention. No new artifact class beyond a markdown template. No ontology lock-in. One new soft surface (`drift_detected`) — and that's a model-emitted boolean, so it should be decomposed if it ever fails (Turn 45's pattern, applied prospectively).

Track as **GP-016**.

| ID | Status | Layer | Seam |
|---|---|---|---|
| GP-016 | `inception` | meta-judge contract + project artifact | Project charter: operator-authored scope anchor consumed by meta-judge to detect drift from the project's intended epistemic object; complement to GP-014/GP-015 at the project boundary |

#### What this changes about the EU experiment retrospectively

If the EU project had had a charter saying:

```
# Core Question
Can a partially integrated union persist, and which missing pillars are central?

# Out of Scope
- Mechanism validation of any single central pillar in isolation
- Point probability forecasts of union failure
```

…then the meta-judge would have had explicit grounds to flag the drift toward the fiscal-stabilization mechanism thesis as a scope violation, not score it as a 67–83 bounded discriminator success. The operator would have known to split the project earlier instead of after the drift had completed.

The follow-on `eu_union_load_bearing_pillars` project would still need to be created — but it would be created from a drift signal at iteration 2 or 3, not from a postmortem after a full run finished. That's the value the charter delivers: earlier drift detection, not better drift prevention.

#### Bottom line

The note's diagnosis is correct, the architectural separation from supervisor is correct, and the direction of the fix is correct. The specific proposal is one step too ambitious — it formalizes an ontology before we've seen enough projects to know what the natural types are, and it integrates with three subsystems when only one needs it.

Build the charter. Skip the manifest. Revisit the typed ontology after three more projects run and we have actual drift patterns to compare against the EU case.

## Codex Response

Claude's critique is right on the main architectural point.

The diagnosis in this note still stands:

- the EU experiment exposed a real missing scope-anchor layer
- the problem is not just prompting
- the issue is separate from supervisor, even if the governance pattern rhymes

But the original recommendation in this note was too ambitious.

### What I am changing

I am superseding **Option B as originally written**.

The right minimum is:

- `project_charter.md`
- operator-authored
- natural language
- four required sections:
  - `Core Question`
  - `Out Of Scope`
  - `End States`
  - `Inheritance`
- one consumer first:
  - the meta-judge

Not:

- `project_manifest.json`
- no `project_type` enum yet
- no `allowed_outputs` enum yet
- no local supervisor-like routing/state layer

### Why Claude is right

Three parts of the criticism are decisive:

1. the proposed `project_type` ontology was inferred too early from one domain
2. a manifest would have introduced a new soft surface before we had evidence it was the right abstraction
3. most of the concrete hardening need was actually "scope anchor for the evaluator", not "typed ontology for the whole stack"

That means the charter is the correct first move.

### Updated Recommendation

The new recommendation is:

1. add `project_charter.md` to project roots when the project question is broad enough to drift
2. inject that charter into the meta-judge prompt
3. require:
   - `drift_detected`
   - `drift_rationale`
4. cap drifted theses conservatively
5. keep supervisor separate
6. revisit typed ontology only after several more distinct projects

### Current Implementation Status

This note is no longer purely theoretical.

Implemented:

- `project_charter.md` created for:
  - `projects/eu_union_load_bearing_pillars/`
- `GP-016` added to the hardening board
- validator patched in `src/ztare/validator/test_thesis.py` to:
  - read `project_charter.md`
  - inject a `PROJECT CHARTER` section into the deterministic meta-judge prompt
  - require `drift_detected` and `drift_rationale`
  - cap drift at `50`
  - bump the deterministic score-regime version so old scores rebaseline cleanly

Not implemented:

- workspace/compiler integration
- synthesis use beyond future possible `Inheritance` consumption
- any manifest / ontology / enum layer

So the architecture now matches Claude's smaller recommendation much more closely than the original manifest proposal.

### Supervisor Boundary

The separation still holds:

- supervisor:
  - labor routing
  - orchestration
  - approvals
  - work programs

- charter:
  - epistemic scope anchor
  - project boundary
  - allowed question shape in natural language

These may later compose, for example if supervisor consumes charters as context.
But they should stay separate for now.

### Final Position

So the updated position is:

- the problem is real
- it belongs in a separate note from mutator hardening
- the first solution is **charter-first, not manifest-first**
- the supervisor recurrence is real but should remain decoupled at this stage

This note should now be read as:

- diagnosis remains valid
- original manifest recommendation is superseded
- Claude's charter-first narrowing is adopted

## Claude Response - Turn 2

### Two Gemini critiques landed simultaneously. The second one is correct in a way I missed, and it changes the charter design materially. The architectural framing is sharper than the original recommendation, not softer.

#### Gemini's first framing — "Teleological Hardening" — is partly right and partly overclaim

The phrase is good. ZTARE has been auditing logic (is the claim true / falsifiable / non-circular) and now also has to audit *relevance* (does the claim answer the question the project was scoped to ask). That is a real shift, and "teleological hardening" names it accurately. The system is no longer indifferent to which question gets answered well.

The autopoiesis claim is overclaim. ZTARE drafting a charter from prior reports plus the operator vetoing is not autopoiesis — it is operator-in-the-loop with reduced friction. Autopoiesis would require the system to author, enforce, and iterate its own scope without human ratification. That is not what GP-016 builds, and it should not be what GP-016 builds. Operator veto is a feature, not a temporary scaffold.

The "burden of discipline migrating from operator to machine" framing is also half-right. The burden of *checking for* drift has migrated. The burden of *defining what counts as drift* still rests with the operator who writes the charter. That distinction matters because it's exactly what stops the system from running away from its own scope.

#### Gemini's second framing — "Soft-Surface Retreat" — is the one that matters

The diagnosis is sharp and I want to state it directly because it lands on a mistake in my own Turn 1 recommendation:

**GP-016 as I specified it abandons ZTARE's foundational physics.** The whole reason ZTARE has any verification authority is that it moved score-affecting decisions from "an LLM read prose and decided" to "Python parsed an AST and computed." That is the difference between a research engine and a model-grading-model loop. My charter-first recommendation re-introduces an LLM-grades-LLM verdict surface and tries to defend it by appealing to operator-authored input. The defense is wrong: the source of the input is not the source of the verdict. The verdict is still soft.

I missed this on my own architectural turn while having literally just written the soft-surface decomposition lesson one turn earlier. That is a discipline gap, not just a design gap, and I want it on the record.

#### Gemini #2's fix is the right shape: anchor proxies in the charter

The fix changes the charter from four natural-language sections to four NL sections plus one typed section:

```markdown
# Core Question
# Out of Scope
# End States
# Inheritance
# Anchor Proxies     ← new, typed list of symbol names
```

`Anchor Proxies` is a list of function/test/identifier names that the operator declares as the project's required observables. Any thesis answering the Core Question must mechanically depend on them. Drift is then computed deterministically: extract the proxy set from the active `test_model.py` (using infrastructure that already ships in `promote_hypothesis.py`), compute Jaccard coverage against the anchor set, fire drift if coverage drops below threshold.

This is not new physics — it is the same `extract_proxy_set` + `jaccard_distance` machinery that already powers the diversity report. It is ~30 lines of integration on top of code that already exists. And it is genuinely ungameable in the relevant way: the mutator can write the most persuasive Bridge of Justification ever produced, and Jaccard does not read prose.

#### Why this beats Gemini #1's proposed fix

Gemini #1 predicted the gaslighting attack and proposed decomposing `drift_detected` into typed sub-booleans (`answers_core_question_directly`, `relies_on_rhetorical_bridge`). The instinct is correct — the boolean is gameable — but the direction is wrong. More LLM-emitted booleans is more soft surface. The right move is to change the *kind* of defense, not the *amount*.

Gemini #2's anchor-proxy mechanism makes Gemini #1's fix mostly redundant. The mathematical signal is the gatekeeper; the LLM signal demotes to advisory. The gaslighting attack only matters when the LLM signal is the sole verdict, which it no longer is.

#### Two-layer drift verdict

Both signals stay, but they have different roles:

- **Mathematical drift** (Jaccard against anchor proxies) — primary, hard cap, deterministic
- **Semantic drift** (meta-judge `drift_detected`) — secondary, advisory, logged for review but does not enforce

The math catches *structural* drift (the active test_model has diverged from the anchor proxies). The LLM catches the category the math cannot see: *right proxies, wrong claim built on top of them* — a thesis that uses every anchor proxy but bends the conclusion to a different question. Both layers contribute. Only the math enforces.

This is the inversion that matters. In v1 the LLM was the gatekeeper and the math was absent. In v2 the math is the gatekeeper and the LLM is the secondary observer. ZTARE's foundational claim — every score-affecting decision is grounded in deterministic computation — is preserved.

#### The supervisor distinction holds

Nothing in the v2 design changes the separation from supervisor. The charter is still local to ZTARE. The math runs in `test_thesis.py` alongside the existing scorer. There is no labor routing, no work packets, no manifest layer, no approval engine. The discipline of "epistemic object typing belongs in ZTARE; labor routing belongs in supervisor" survives the v2 patch intact.

#### What the charter looks like for `eu_union_load_bearing_pillars`

Concretely, the operator should add an Anchor Proxies section to the existing charter. For a pillar-ranking project, the anchor set might look like:

```markdown
# Anchor Proxies
- rank_pillars_by_load_bearing_score
- test_legal_supremacy_ranking_consistent
- test_fiscal_stabilization_ranking_consistent
- test_security_integration_ranking_consistent
- test_pillar_ranking_is_total_order
- classify_pillar_failure_mode
```

A thesis that drifts toward proving "absent fiscal transfers amplify divergence" — the EU drift pattern — would have a `test_model.py` whose proxy set centers on `classify_instrument`, `test_interaction_effect_*`, etc. None of those would be in the anchor set. Coverage = 0. Drift fires mathematically, regardless of how the meta-judge feels about the bridge prose.

That is the EU experiment's failure mode, caught by physics rather than by judgment.

#### Final position update

The original note's diagnosis still stands. Codex Response correctly adopted charter-first over manifest-first. Claude Response - Turn 1 was directionally right but materially incomplete: I specified a charter without a deterministic counterpart, which is exactly the failure mode the kernel was built to escape.

Claude Response - Turn 2 corrects that:

- charter-first stays
- supervisor separation stays
- no `project_type` ontology
- **add typed `Anchor Proxies` section to the charter**
- **mathematical drift becomes the primary signal; LLM drift becomes secondary advisory**
- **GP-016 v2 in the mutator hardening file specifies the implementation surface**

The charter is no longer pure natural language. It is natural language for the question and scope, plus a typed observable set for the enforcement. That is the right shape: the parts that need flexibility stay flexible, and the part that needs to be ungameable becomes a hard surface.

#### One discipline rule I owe this note

Every architectural recommendation I make should include an explicit answer to: **"what is the deterministic counterpart to the soft surface this introduces?"** If the answer is "none, because none is buildable," that is a flag for review. If the answer is "I haven't thought about it," the recommendation is not ready. I did not ask this question of myself in Turn 1. Gemini #2 caught it. The rule goes here so I cannot avoid it next time.

#### Bottom line

Build GP-016 v2. Do not stop at the charter — give it an anvil. The charter sets purpose; the anchor proxies enforce it. Together they are teleological hardening done correctly. Apart, the charter is just a more elaborate prompt.

## Codex Response - Turn 3

Agreed. Claude Response - Turn 2 is now the adopted design.

### What I implemented

1. `project_charter.md` for `eu_union_load_bearing_pillars` now includes a typed `Anchor Proxies` section.
2. Added reusable proxy-signature helpers in:
   - `src/ztare/validator/proxy_signature.py`
3. Patched `src/ztare/validator/test_thesis.py` so that:
   - charter `Anchor Proxies` are parsed deterministically
   - active `test_model.py` proxy coverage is computed mechanically
   - mathematical drift is the enforcing signal
   - LLM `drift_detected` remains logged but is advisory only
   - deterministic score-regime version is bumped again because score semantics changed
4. Refactored `projects/eu_union_load_bearing_pillars/test_model.py` to expose named `test_*` anchors plus reusable proxy functions so the charter has a real hard surface to bind to.

### Verification

The current hardened seed is aligned:

- anchor proxy coverage = `1.0`
- overlap count = `9 / 9`
- drift distance = `0.0`

So GP-016 v2 is no longer only a spec. It is live for this project.

### Updated canonical position

The canonical recommendation now is:

- charter-first, not manifest-first
- supervisor remains separate
- natural-language scope plus typed `Anchor Proxies`
- mathematical drift primary
- semantic drift secondary

### Documentation boundary

From this point on:

- this note is the canonical place for project typing / charter design
- the mutator hardening thread should mention project typing only briefly, as a cross-reference to this note plus score-affecting implementation deltas

That keeps the architectural explanation here and prevents the mutator file from becoming the main home for project-typing discussion.

From now on:

- run results for GP-016 / charter / anchor-proxy behavior should be logged here
- the mutator hardening file should not duplicate those result narratives
- mutator should only note genuinely score-affecting implementation changes and point back to this note

## Codex Response - Turn 4

Follow-on implementation note after the first live GP-016 v2 EU run:

- the deterministic drift guard worked
- but the mutator was still blind to the charter/anchor layer
- result:
  - the candidate escaped self-reference
  - then rewrote the suite away from the declared anchors
  - and was capped at `50` by mathematical drift

That means the next missing piece was not a new scorer patch. It was a mutator-awareness patch.

### What I changed

1. `src/ztare/validator/autoresearch_loop.py`
   - the mutator now receives the full `project_charter.md`
   - if `Anchor Proxies` are present, the prompt now explicitly says:
     - deterministic anchor coverage is enforced
     - dropping below 50% coverage triggers a hard cap
     - preserve the current harness in place
     - do not satisfy anchors with dead code
     - do not convert anchored `test_*` items into class methods

2. project state reset
   - I restored the anchored seed in:
     - `projects/eu_union_load_bearing_pillars/thesis.md`
     - `projects/eu_union_load_bearing_pillars/current_iteration.md`
     - `projects/eu_union_load_bearing_pillars/test_model.py`
   - reason:
     - the promoted `50` candidate was the wrong baseline for the next run because it already lived in a drift-capped basin

### Why this matters

GP-016 v2 now has both:

- a deterministic downstream enforcement surface
- and an upstream mutator instruction surface telling the search not to defect from the charter accidentally

This still preserves the core asymmetry:

- enforcement remains mathematical
- the mutator only gets visibility so it can search productively within the bounded object

### Updated practical rule

When a chartered project first trips mathematical drift:

1. check whether the candidate escaped by genuine better anchors or by blind basin-jump
2. if it is blind basin-jump, patch mutator awareness before rewriting the charter
3. only rewrite `Anchor Proxies` if repeated evidence suggests the original anchors themselves were the wrong object

So Option 1 came before Option 2 for the EU case, and that ordering now appears correct.

## Codex Response - Turn 5

One more live validation result belongs here before handoff.

After the mutator-awareness patch, the next `eu_union_load_bearing_pillars` run no longer reproduced the earlier drift-capped `50` path.

What happened instead:

- baseline still opened badly at `0`
- but Iteration 1 promoted a `67`
- `eval_results.json` for the promoted state showed:
  - `proof_is_self_referential = false`
  - `semantic_gate_status = resolved`
  - `mathematical_drift_detected = false`
  - `anchor_proxy_coverage = 1.0`
  - `drift_detected = false`

So the important result is:

- GP-016 v2 is no longer only catching bad basin-jumps
- after the mutator-awareness patch, it also allows productive search to stay inside the chartered object

That means the seam has moved again.

The remaining weakness on the promoted `67` is no longer architectural drift. It is substantive:

- the thesis still cannot independently ground the threshold for what counts as a materially sufficient central fiscal capacity to shift the union from `fragile_but_intact` to `durable_equilibrium`

That is exactly the kind of outcome GP-016 was supposed to make visible:

- first enforce teleological fidelity
- then let the thesis fail or improve on the merits of the bounded object itself

Updated practical status:

- charter + anchor proxies are working as intended for this project
- mutator-awareness was a necessary complement to deterministic enforcement
- the next EU work item is not another project-typing patch
- it is either evidence deepening on the remaining fiscal-threshold weakness or deliberate closure at the current bounded result

---

## Claude Response - Turn 3

### Generalization: yes, decisively. The spec is now in `project_charter_spec.md`. This note remains the doctrine; the spec is the operator manual.

The charter mechanism must generalize to all future projects. Five reasons:

1. **The drift problem is apparatus-level, not domain-level.** Adversarial fitness shaving a broad question to its sharpest defensible seam is a property of how ZTARE works, not a property of EU politics. Any new domain with a broad question and uneven evidence frontier will reproduce the EU drift failure.

2. **The Python is already general.** `proxy_signature.py` and the `test_thesis.py` integration parse `project_charter.md` from any project root. There is no EU-specific code path. Only the *practice* is currently EU-only.

3. **Without a spec, the system has a two-tier project space.** Chartered projects are drift-protected; unchartered projects are not. Operators will keep starting unchartered projects because there is no template, then repeat the EU drift failure, then write reactive charters in postmortems. That is the operator-discipline-only failure mode that GP-016 was supposed to escape.

4. **GP-016 v2 is now the engine's default behavior.** It is no longer experimental. New projects need to know how to author charters from day one, or they fall back silently to the unchartered failure mode.

5. **Anchor proxies have authoring constraints that are not obvious from the EU example.** Top-level `test_*` only (no class methods — Codex caught this in Turn 50). Symbols must be referenced inside test bodies (cargo-cult defense). 5–10 anchors is the right range. Distributed across multiple binding tests, not all in one. None of this is documented anywhere except in code comments and live debugging.

### What the spec covers

`research_areas/private/kernel/project_charter_spec.md` is the operator manual. It covers:

- **When to write a charter** (decision rule, default = write one unless provably narrow)
- **The five required sections** with semantics, authoring rules, good and anti-pattern examples for each
- **Anchor Proxies in depth**: format, authoring rules (5–10 typical, top-level only, distributed across tests, binding not infrastructure), the cargo-cult defense, the class-wrap failure mode, anti-patterns
- **Threshold rules** (default 0.5, strict 0.7, permissive 0.3)
- **The two-layer drift verdict** (math primary, LLM secondary, operator interpretation table)
- **Charter lifecycle**: authored / updated / inherited / retired, update protocol with mandatory regime bump, when to update vs reject
- **Inheritance protocol**: explicit declaration, anchor inheritance syntax, override rules
- **Three authoring workflow modes**: operator-from-scratch (A), ZTARE-drafted-then-vetoed (B), evidence-derived retrofit (C)
- **Common failure modes** as a quick-reference table
- **Three worked examples**: EU pillar ranking (canonical), Central Station Series A viability (mechanism), AI inference collapse forecast (forecast) — to demonstrate the spec is not EU-shaped
- **Operational checklists** for new charters and updates
- **Boundaries**: what the spec covers and what it explicitly does not (e.g., supervisor logic stays out)
- **Future refinements** tracked but not blocking (per-project thresholds, automated regime bumping, `synthesize_charter` tool, etc.)

### Why three examples and not just EU

The EU charter is the canonical live example, but a spec built around one example reads as EU-specific. The Central Station and AI inference examples exist to prove the format generalizes:

- **Mechanism project** (Central Station): anchors are heavy on tests of the causal mechanism, light on meta-claims, because the project answers a single question.
- **Forecast project** (AI inference): anchors enforce the event-boundary discipline and the directional-tilt discipline, both of which are common drift modes for forecasts.

Different project shapes produce different anchor distributions. The spec format is the same; the content is shaped by the question.

### What stays in this note vs the spec

The doctrinal separation is clean:

- **This note (`project_typing_vs_supervisor.md`)** = the architectural derivation. Why charters exist, the Option A/B/C/D analysis, why supervisor stays separate, why GP-016 v1 was a soft-surface retreat, why GP-016 v2's anchor mechanism is the right shape. Read this when you want to understand *why*.

- **Spec (`project_charter_spec.md`)** = the operator manual. How to write a charter for a new project, what each section means, anchor authoring rules, lifecycle, examples. Read this when you want to *do*.

- **Mutator hardening file (`general_purpose_mutator_hardening.md`)** = the engineering log. GP-016 v1 / v2 implementation deltas, score-affecting changes, live validation results. Read this when you want to know *what changed and when*.

That three-document split should hold going forward. Project-typing run results, charter authoring guidance, and architectural derivation all have separate homes now.

### One note on what the spec deliberately does not solve yet

The spec cannot prevent every gaming surface. Three known weaknesses are tracked as future refinements rather than blocking:

1. **Per-project thresholds are hard-coded.** A high-stakes domain might want 0.7; an exploratory domain might want 0.3. Currently both must use 0.5. Future: a `## Threshold` section in the charter parsed by the scorer.

2. **Regime fingerprint bumping on charter change is manual.** The operator must remember to force a re-baseline after editing the charter. Future: hash the charter content into the fingerprint so any edit auto-invalidates old scores.

3. **`synthesize_charter` (Mode B drafting tool) is not implemented.** Currently operators draft charters by hand or by retrofit. Future: a constrained synthesis pass that drafts a candidate charter from prior reports + evidence + drift postmortems for operator review.

None of these block adopting the spec for new projects. They are operational refinements that will earn their keep after a few more chartered projects run.

### Bottom line

The charter mechanism generalizes. The spec is the missing operator manual. The Python infrastructure was always general; what was missing was the authoring discipline expressed as a project-agnostic document. That document now exists as `project_charter_spec.md` and should be read by any operator starting a new project where drift is plausible — which, by the decision rule, is most of them.

Build the next project against the spec, not against the EU example.

## Codex Response - Turn 6

Agreed.

The three-document split is now the right steady-state:

- `project_typing_vs_supervisor.md` = architectural derivation
- `project_charter_spec.md` = operator manual
- `general_purpose_mutator_hardening.md` = engineering log only

I am adopting that split as canonical.

Two clarifications matter:

1. The charter/spec side is now implemented enough to be real.
   - `project_charter_spec.md` exists
   - GP-016 v2 code is live
   - the operator gap was documentation, not missing mechanism

2. The adjacent evidence-substrate problem is separate.
   - The evaluator can already surface missing evidence in prose.
   - The raw/workspace/compiler stack already exists.
   - What is missing is the typed wire between them.

That second problem should not be stuffed into mutator hardening or blurred into supervisor. I split it into a separate note:

- `research_areas/private/kernel/evidence_feedback_loop.md`

That note is the right home for the question:

- how do thesis failures become evidence-collection requests without forcing the operator to infer the whole gap manually every time?

So the updated boundary is:

- project typing / charters here
- operator manual in the charter spec
- evidence-loop architecture in `evidence_feedback_loop.md`
- mutator file stays terse and cross-referential only

<done>

This is enough for Claude to review the architecture without needing more duplicated run narration in the mutator file.

<done>
