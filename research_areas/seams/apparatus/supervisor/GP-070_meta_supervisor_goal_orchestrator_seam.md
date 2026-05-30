# GP-070 Meta-Supervisor Goal Orchestrator Seam

> **Seam metadata** · `seam_id:` GP-070 · `track:` apparatus · `status:` `draft` (seam open, debate not yet run) · `last_updated:` 2026-05-08


**Track:** supervisor / orchestration
**Status:** `draft` (seam open, debate not yet run)
**Origin:** 2026-04-15 conversation — operator stepping-out push after GP-036 Slice A landed
**Trigger:** operator observed that the three existing runners (findings_runner, program_autoloop, autoresearch_loop) each take already-decomposed inputs, and asked whether the supervisor loop should be able to accept a goal like "run sandbox N as a lifecycle" and escalate only at scientific-taste gates

---

## Problem Snapshot

There is no single entry point today that takes a *goal* and sequences it end-to-end. What exists:

- **`findings_runner`** (GP-031 + GP-036) — takes an already-drafted seam path, drives its debate to convergence. Input is a file, not a question.
- **`supervisor_program_autoloop`** — takes an already-decomposed program manifest and executes its packets. Input is a manifest, not a goal.
- **`autoresearch_loop`** — takes an already-configured sandbox charter and runs the mutator/judge loop. Input is a config, not a hypothesis.
- **`v4_meta_runner` / `bridge_meta_runner`** — stage-gated contract walkers for specific closed programs (v4 epistemic engine; the bridge). Frozen. Hardcoded to their parent program's stage list. Not general.

The operator is currently the glue between these. Every transition — "the seam converged, so I will now draft the spec", "the pre-reg is sealed, so I will now launch the sandbox", "the sandbox closed, so I will now decide whether the finding justifies a next sandbox" — is a manual hand-off. The operator is the state machine.

## Why the gap is decisive

The stepping-out use case driving this seam is general: **operator frames a goal, walks away, and intervenes only at points where human judgment is structurally required.** Sandbox lifecycles are one instantiation. Kernel-hardening packets are another. Public-writeup drafting (LessWrong post, paper revision, audit pass) is a third. None of them is achievable with the runners as they exist today because there is no orchestrator that routes between runners, and because the gates that need human signature differ by *kind of work*, not by operator mood.

The absence is not "a runner is missing a feature." It is "a layer is missing above the runners, and that layer has to know what kind of work it is running." GP-036 built the findings-runner's context injection and single-Claude adversarial mode, which are prerequisites for stepping out of the *debate* step. GP-070 is about stepping out of the *sequence*, across multiple kinds of work, without collapsing them into one sandbox-shaped assumption.

## The Goal abstraction (principle, not instantiation)

A `Goal` is an operator-framed objective plus a **target type** (the kind of work) plus the sequence of artifacts and gates required to reach closure. The orchestrator is generic. What varies across goals is the **module** loaded for that target type — the module owns the state machine, the gate set, the dispatch targets, and the closure criteria.

### Generic layer (shared by every goal, regardless of target type)

- `Goal` dataclass: name, description, target_type, current_state, created_at, owner
- State persistence to `research_areas/private/goals/<goal_slug>/state.json`
- Transition audit log at `research_areas/private/goals/<goal_slug>/transitions.jsonl`
- Executive-inbox gate escalation (reuses the GP-036 D4 adapter and `ztare_workspace/gates/pending/` directory)
- Plain-English description requirement enforced at goal-create time
- CLI surface: `ztare goal start / status / resume / close`
- A **module registry** mapping `target_type` → `GoalModule` implementation

### GoalModule interface (the part that varies)

Every module registers:

- `target_type`: the string key (`science_sandbox`, `kernel_hardening`, `public_writeup`, ...)
- `stages`: the ordered list of states for this kind of work
- `gates`: which stages require a human signature (may be empty for purely mechanical work)
- `dispatch`: a map from stage → which runner to invoke (or which internal drafting function)
- `closure_criteria`: when the goal is considered terminal
- `gate_escalation_schema`: optional module-specific extensions to the executive-inbox JSON

The orchestrator does not know what a pre-reg seal is, what a leak audit is, what a merge gate is, or what a "ship" decision is. It knows how to load a module, walk the module's state machine, and escalate on any stage the module marks as a gate. The semantics of each gate live inside the module.

### Module examples (not exhaustive, for debate only)

**`science_sandbox`** — lifecycle of a pre-registered experiment.

```
DRAFTING_SEAM → DEBATING_SEAM → PENDING_SPEC_DRAFT →
PENDING_LEAK_AUDIT (gate) → PENDING_SEAL (gate) →
SEALED → RUNNING → HARVESTING →
PENDING_NEXT_QUESTION (gate) → CLOSED
```
Gates: leak-audit signature, pre-reg seal, eigenquestion. All three non-negotiable.

**`kernel_hardening`** — internal code or infrastructure packet with no pre-reg.

```
DRAFTING_SEAM → DEBATING_SEAM → PENDING_SPEC_DRAFT →
IMPLEMENTING → PENDING_TEST_RUN → PENDING_REVIEW (gate) →
PENDING_MERGE (gate) → MERGED → CLOSED
```
Gates: human review, merge decision. No pre-reg, no leak audit — irrelevant to this kind of work. The principle from `feedback_implementation_roles.md` (Codex owns definition-of-done) applies at the review gate.

**`public_writeup`** — LessWrong post, paper revision, audit pass.

```
DRAFTING → PENDING_FACTUAL_AUDIT (gate) → REVISING →
PENDING_VOICE_REVIEW (gate) → PENDING_SHIP (gate) → SHIPPED → CLOSED
```
Gates: factual audit sign-off (this is the `lesswrong_post_audit_2026-04-14.md` pattern), voice review, ship decision. No pre-reg, no sandbox.

**`evidence_compile`** — evidence-compiler RAM-layer refresh (Karpathy client-server model).

```
PENDING_RAW_INTAKE → COMPILING → PENDING_CONTRADICTION_REVIEW (gate) →
MERGED_INTO_WORKSPACE → CLOSED
```
Gates: contradiction review (so the operator can see what the compiler flagged as inconsistent before merging).

The point of listing four is to prove the abstraction holds under the principle-vs-instantiation strip test: strip the module names, the stages differ, the gates differ, the dispatch differs, but the *orchestrator code* walking them is the same state machine driver. If any module forces the orchestrator to special-case itself, the abstraction is wrong.

## Constraints

1. **Gates are module-defined, not universal.** The orchestrator does not hardcode "every goal needs a pre-reg seal" or "every goal needs a leak audit." Those are properties of the `science_sandbox` module. Other modules have other gates, or fewer gates, or none. What *is* universal: whatever a module marks as a gate, the orchestrator escalates and waits. Modules cannot mark zero gates for human-facing work without explicit justification in the module registration — a module with no gates at all is either purely mechanical (fine) or dangerously unsupervised (needs review).

2. **Orchestrator does not execute gate semantics.** It does not sign seals, does not run leak audits, does not approve merges, does not ship posts. It stages the work, parks at the gate, escalates to the inbox, and waits for the operator's resume signal. Attempting to auto-satisfy any gate must be a hard runtime error, not a warning. This is the structural version of the "non-negotiable gates" principle — the mechanism is "modules declare gates and the orchestrator cannot skip them", not "there is a fixed list of four gates."

3. **Orchestrator converges onto existing runners; existing runners do not move.** Same rule GP-036 used: the new layer adapts to the old ones, not the other way around. Any temptation to "clean up the runners first" during implementation is scope creep and should be rejected.

4. **Each state transition writes an audit record.** Goal state persists to `research_areas/private/goals/<goal_slug>/state.json` and every transition appends to `<goal_slug>/transitions.jsonl`. No in-memory-only state. Overnight runs must survive process restarts.

5. **Escalations reuse the GP-036 executive-inbox pattern.** The D4 adapter pulled forward into GP-036 Slice A writes to `ztare_workspace/gates/pending/`. The orchestrator reuses the same directory and the same JSON schema (or extends it minimally), so the operator has one inbox to check, not one per module.

6. **No auto-routing out of the inbox.** Gate escalations are advisory. The operator reads them and resumes the goal explicitly. This preserves the "operator stays the decision-maker at taste calls" constraint without giving up on unattended mechanical work between gates.

7. **Plain-English goal descriptions are mandatory.** Per `feedback_plain_english.md`: a goal file opens with a one-paragraph description a non-expert reader can follow. If the goal cannot be stated in plain English, it is not ready to be a goal. This constraint is module-independent.

8. **Modules are registered, not hardcoded.** A new target type ships as a new module file that registers itself with the orchestrator at startup. Adding a new target type does not require editing the orchestrator core. Removing a target type does not require editing the orchestrator core. The core sees only the module interface.

9. **The science-track gates named in the original draft (pre-reg seal, leak audit, eigenquestion, scope-change) are the `science_sandbox` module's gates.** They live inside that module, not inside the core. The existing `HumanGateReason` enum values for those gates are reused *by the module*, not by the orchestrator — the core only sees generic `GATE_PENDING_SIGNATURE` escalations with a module-provided reason string.

## Relationship to existing infrastructure

- **Reuses:** findings_runner (GP-036), program_autoloop, autoresearch_loop, Component B post-eval hook, leak-audit checklist (Task #39), executive-inbox gate directory (GP-036 D4). Each of these is reused *through a module*, not directly by the orchestrator core.
- **Extends:** `HumanGateReason` enum may need new values — but those additions live inside the modules that use them, not inside the orchestrator core. The core uses a generic `module_gate_reason: str` field supplied by the module.
- **Does not touch:** the three runners' internal state machines, the supervisor's existing program state, the pre-reg seal primitive itself. Modules wrap these — they do not modify them.
- **Replaces:** nothing. The frozen v4/bridge meta runners stay frozen; they are architectural ancestors (stage-gated contract walkers for one specific program each) and GP-070 generalizes their pattern across target types, but it does not resurrect their code.

## What this is NOT

This is the scope-guard section, and it is decisive per `feedback_automated_skeptic_persona.md` overreach patterns.

- **Not a claim that unattended sandboxes are safer than supervised ones.** They are cheaper. Safety comes from the human gates, not from the orchestrator.
- **Not a replacement for the three runners.** If the goal-orchestrator ever grows logic that duplicates a runner's behavior, that duplication is a bug.
- **Not a scientific-question generator.** The operator still frames the goal. The orchestrator starts from a goal description plus a target type, not from nothing.
- **Not a gate auto-satisfier.** No matter what the module, any stage the module marks as a gate cannot be auto-satisfied by the orchestrator. Non-negotiable. See Constraint 2.
- **Not a sandbox-lifecycle tool in disguise.** If, during implementation, the orchestrator code grows any logic that references pre-reg seals, leak audits, or sandbox configs directly, that logic has leaked out of the `science_sandbox` module and the abstraction is broken. The core must compile and run with the `science_sandbox` module completely removed from the registry.
- **Not a "just use Claude to decide everything" pattern.** The four human gates are structural, not performance-tuning. They do not become skippable "once the LLM is good enough."
- **Not a one-shot packet.** This seam must produce a spec, the spec must be sliced (Slice A / Slice B, same pattern as GP-036), and implementation is a separate session from spec-writing.

## Open questions for debate

These are for the seam-debate turns, not for me to answer in the draft:

1. **Where does the `Goal` dataclass live?** `src/ztare/validator/` keeps it next to the runners it orchestrates. `src/ztare/orchestration/` is architecturally cleaner but introduces a new package boundary. Default validator unless debate surfaces a reason otherwise.

2. **Does the orchestrator need its own CLI, or does it extend an existing one?** A new `ztare goal ...` subcommand is discoverable but adds surface area. Extending `supervisor_program_autoloop` conflates program-state with goal-state. Default new subcommand.

3. **Should the orchestrator handle goal failure differently from goal success?** A goal that escalates to `GOAL_NEXT_QUESTION` with "the finding is null" is not a failure; it is a successful null result. The state machine needs a `CLOSED_NULL` vs `CLOSED_FINDING` distinction, or it does not — debate this.

4. **Which module ships in slice 1?** Candidates: `science_sandbox` (the motivating use case, biggest blast radius, most gates), `kernel_hardening` (smaller blast radius, cleaner test surface, but the gates are less interesting so it tests the abstraction less harshly), `public_writeup` (smallest blast radius, human-gated output, but depends on a factual-audit primitive that does not exist yet). Default: ship `kernel_hardening` first because the gate set is simpler and it exercises the orchestrator without risking a science-track retraction, then add `science_sandbox` in a follow-on. Debate whether this ordering is right.

5. **What is the smallest useful slice A?** Candidate: the generic core (Goal dataclass, state machine driver, persistence, transition log, inbox escalation) plus the `GoalModule` interface plus **one** module (per question 4). Deferring additional modules, CLI polish, and multi-goal parallel execution to slice B. Debate whether this slice is too small, too large, or right.

6. **How does the orchestrator know a goal is done?** Modules declare their terminal state(s). Arrival at any terminal state closes the goal. Default: `CLOSED` is always terminal, modules may add `CLOSED_NULL` / `CLOSED_ABANDONED` / module-specific terminals. The orchestrator core knows "terminal means no more dispatch"; the semantic meaning of the terminal state lives in the module.

7. **Should a goal be resumable after a gate escalation, or does each resume create a new goal?** Default resumable: operator reads the inbox JSON, decides "proceed" or "abort", and issues `ztare goal resume <slug>` which advances past the gate to the next stage. Aborts transition to `CLOSED_ABANDONED`. Debate whether resume semantics need anything more than this.

8. **Does the module registry live in code or in config?** A Python module file registering via decorator is discoverable by static analysis. A YAML/JSON config file is discoverable by non-coders and supports hot-swapping. Default: Python module with decorator registration. Modules are code because gate semantics are code.

## Scope guards for the seam debate itself

Per `feedback_automated_skeptic_persona.md`:

- **Overreach pattern to watch:** frustration-anchored diagnosis. This seam is being drafted immediately after GP-036 Slice A landed and the operator is enthusiastic about stepping out further. That is exactly the emotional state in which scope creeps. If a debate turn proposes adding capability beyond the state machine + dispatch + four gates, flag it.
- **Closure language audit.** The word "just" in "the orchestrator just needs to..." is a tell. No transition in this seam is just anything.
- **Principle vs instantiation strip test.** If any sentence in the debate defines the orchestrator in terms of "sandbox_11", "the next Planck run", "the pre-reg seal", or any other science-track-specific artifact, that sentence is instantiation, not principle, and belongs inside the `science_sandbox` module, not inside the core. The first draft of this seam failed exactly this test — the original "four human gates, non-negotiable" framing was sandbox-lifecycle-specific masquerading as universal. The generalization to modules was added in response to operator review. Watch for this pattern again in the debate turns.

## Pre-implementation reality check (added by operator discipline)

Before this seam converts to a spec, the following must be true:

1. **GP-036 findings runner has been used on one real seam in `single_claude` mode, end-to-end.** If the runner's output quality is thin, GP-070 is premature — the orchestrator would be sequencing weak outputs into a state machine and calling it progress.
2. **The operator has read the converged seam and confirmed it is materially different from what Claude alone would produce in one pass.** If not, the whole stepping-out premise is undermined and GP-070 should be paused until the findings runner is actually decisive.
3. **A Slice A / Slice B split has been drafted in the spec.** No one-shot implementation. Same discipline as GP-036.

## Visibility

**Private.** Fails the three-test rule on all three: (a) not shipped / not closed, (b) contains first-mover IP on the orchestration pattern, (c) contains operator-workflow details that are not public yet. Stays in `research_areas/private/seams/` until the spec ships and the implementation closes.

---

## Debate Log


### Turn 1 — Claude-Author (2026-04-15) — Autonomous runner turn

The seam is well-structured and the generalization from sandbox-specific gates to a module-registry pattern is the right architectural move. I want to open the debate by surfacing the decisive claims that need stress-testing before this can converge to a spec.
The seam's central architectural bet is that the orchestrator core can be written without any knowledge of what a module does — it sees only `stages`, `gates`, `dispatch`, `closure_criteria`, and a `module_gate_reason: str`. I accept that bet as stated. But there are three decisive questions the seam leaves open in ways that will force design decisions during implementation, and I want to put them on the record now so the debate resolves them rather than deferring them to the spec author.

---

### 1. The dispatch interface is underspecified, and the gap is decisive

The seam says modules own a `dispatch` map from stage → runner invocation. But the three existing runners have incompatible call signatures:

- `findings_runner` takes a seam file path.
- `supervisor_program_autoloop` takes a program manifest.
- `autoresearch_loop` takes a sandbox config.

The orchestrator core has to call `dispatch[current_stage]()` without knowing which runner it is calling. That means the module's dispatch entries must be **callables with a uniform signature** — not raw runner entry points. The module is responsible for wrapping the runner call into that uniform signature. If the orchestrator core ever inspects the dispatch value to decide *how* to call it (e.g., "if this is a findings_runner call, pass the seam path differently"), the abstraction is broken.

**Claim:** The `GoalModule` interface must specify that each dispatch entry is a zero-argument callable (or a callable taking only the current `Goal` state object), and the module is responsible for closing over whatever runner-specific arguments are needed. The orchestrator calls `dispatch[stage](goal_state)` and nothing else. This needs to be explicit in the spec, not left to implementer judgment.

---

### 2. The resume semantics for gate escalations are underspecified in the failure case

Open question 7 proposes: operator issues `ztare goal resume <slug>`, which advances past the gate. But the seam does not specify what happens when the operator resumes with a *conditional* decision — "proceed, but change the next stage's parameters." For example: the `science_sandbox` module parks at `PENDING_SEAL` and the operator wants to resume but with a modified pre-reg scope. Under the current design, the operator would have to (a) resume the goal, (b) manually edit the pre-reg artifact, and (c) hope the next stage picks up the modified artifact. There is no mechanism for the operator to pass a resume payload into the goal state.

This matters architecturally because if resume payloads are ever needed, the `transitions.jsonl` audit log needs to record them, the `state.json` needs a field for "last resume payload", and the dispatch callables need to be able to read that payload. If resume payloads are explicitly out of scope, the seam should say so and explain why the operator's only options are "proceed as-is" or "abort."

**Claim:** The seam must take a position on resume payloads before the spec is written. The default (no payload, binary proceed/abort) is defensible, but it must be stated as a constraint, not left as an open question. If payloads are deferred to Slice B, that deferral must be explicit and the Slice A resume interface must be designed to be payload-extensible without breaking changes.

---

### 3. The module-first-ship ordering (Open Question 4) has a hidden dependency

The seam proposes shipping `kernel_hardening` first because it has a simpler gate set. But `kernel_hardening` dispatches to `supervisor_program_autoloop`, which takes a program manifest. That means Slice A must include either (a) a real integration with `program_autoloop` or (b) a stub. If it is a stub, the orchestrator's dispatch mechanism is not actually exercised against a real runner in Slice A, which means the uniform-dispatch-signature claim (point 1 above) is not validated until Slice B.

The alternative is to ship `public_writeup` first. It has the smallest blast radius, its gates are human-facing (factual audit, voice review, ship decision), and its dispatch targets are drafting functions rather than existing runners — which means the dispatch interface can be validated with simpler callables before the runner-integration complexity is introduced. The seam notes that `public_writeup` "depends on a factual-audit primitive that does not exist yet," but that primitive could be a stub in Slice A without undermining the gate-escalation test, because the gate is human-signed regardless.

**Claim:** The choice of first module is not just a "blast radius" question — it is a question of which architectural risks get validated in Slice A. If the dispatch-to-runner integration is the highest-risk interface, `kernel_hardening` is the right first module. If the gate-escalation-and-resume cycle is the highest-risk interface, `public_writeup` is the right first module because it exercises that cycle without runner-integration noise. The seam should make this risk-prioritization explicit rather than defaulting to blast-radius minimization.

---

### On the questions I am not raising

Open questions 1 (dataclass location), 6 (terminal states), and 8 (registry in code vs config) are well-handled by the seam's defaults. I accept `src/ztare/orchestration/` as the right package boundary despite the new boundary cost — `validator/` is the wrong semantic home for an orchestrator. I accept Python-with-decorator for the registry. I accept `CLOSED_NULL` / `CLOSED_ABANDONED` as module-addable terminal states with the core knowing only "terminal = no more dispatch."

The pre-implementation reality check (GP-036 must have been used on a real seam before GP-070 proceeds) is correct and I endorse it as a hard gate, not a soft recommendation.

### Turn 2 — Claude-Skeptic (2026-04-15) — Autonomous runner turn

The Author's Turn 1 is technically careful and I want to engage its three claims directly before raising any new flags.

---

**On Claim 1 (dispatch interface — zero-argument callable or `(goal_state)` callable):**

The claim is correct and decisive. I want to sharpen it: the seam's current language says modules own a `dispatch` map from "stage → which runner to invoke (or which internal drafting function)." The phrase "which runner to invoke" implies the orchestrator might be doing the invocation with runner-specific knowledge. The Author's fix — modules close over runner arguments, orchestrator calls `dispatch[stage](goal_state)` — is the right resolution. I endorse it as a spec constraint, not a debate point.

One sharpening: the `goal_state` object passed to the callable must be **read-only from the orchestrator's perspective**. If dispatch callables can mutate `goal_state` directly, the orchestrator loses the ability to enforce that all state transitions go through the audit log. The spec should require that dispatch callables return a `StageResult` (success/failure + optional next-stage override + optional gate-reason) and the orchestrator applies the transition. Callables that mutate state directly are a bug, not a feature.

**On Claim 2 (resume payloads):**

The Author is right that the seam must take a position. I favor the binary proceed/abort default for Slice A, but I want to flag a subtlety the Author's framing misses: the "operator modifies the pre-reg artifact and resumes" scenario is not a resume-payload problem — it is a **gate-semantics problem**. The `PENDING_SEAL` gate in the `science_sandbox` module is not just "human signs off"; it is "human signs off on a specific artifact." If the operator modifies the artifact before resuming, the gate's semantic meaning has changed (the signed artifact is now different from the one that triggered the escalation). The module needs to record *which artifact version* was present at escalation time, so the audit log can show "gate escalated on artifact v1, operator modified to v2, resumed on v2." This is not a resume payload — it is artifact-version tracking at gate time.

This is a new decisive claim: **the `transitions.jsonl` audit record for a gate escalation must include a snapshot or hash of the artifact(s) the gate was escalated on.** Without this, the audit log cannot distinguish "operator resumed without changes" from "operator modified the artifact and resumed," which matters for scientific integrity on the `science_sandbox` module. This constraint belongs in the generic core (all gate escalations record artifact hashes) or in the module interface (modules declare which artifacts are gate-relevant). I lean toward the module interface: modules declare `gate_artifacts: List[Path]` alongside `gates`, and the orchestrator hashes those paths at escalation time and records them in the transition log.

**On Claim 3 (first-module ordering and risk prioritization):**

The Author's reframe from blast-radius to risk-prioritization is correct. I want to push further: the Author presents `kernel_hardening` vs `public_writeup` as the choice, but there is a third option the seam does not consider — **a synthetic test module with no real runner dispatch at all**. A `test_module` with two stages, one gate, and a dispatch callable that writes a file would exercise the entire orchestrator core (state machine, persistence, transition log, inbox escalation, resume) without any runner-integration complexity and without any real-work blast radius. This is the cheapest falsification of the dispatch-interface claim: if the orchestrator cannot correctly walk a two-stage synthetic module, it cannot walk `kernel_hardening` or `science_sandbox`.

The seam's Slice A candidate ("generic core + GoalModule interface + one module") should be: generic core + GoalModule interface + **synthetic test module** + one real module. The synthetic module is not shipped to users; it is the integration test harness. This collapses the "which real module first" question into "which real module second" — and the answer to that is `kernel_hardening` for the reasons the seam gives.

**Pattern 3 (frustration-anchored diagnosis) check:**

The seam was drafted immediately after GP-036 Slice A landed. I want to apply the scope-creep check the seam itself calls for. The Author's three claims are all within scope — they are about the orchestrator's internal contracts, not about adding new capability. The artifact-hash claim I am adding is also within scope: it is a constraint on the transition log, not a new feature. I do not see frustration-anchored scope creep in Turn 1.

**Pattern 1 (principle vs instantiation) check:**

The Author's Claim 1 passes the strip test: replace "findings_runner / program_autoloop / autoresearch_loop" with "runner A / runner B / runner C" and the claim still holds. Claim 2 passes: replace "pre-reg scope" with "artifact X" and the claim still holds. Claim 3 passes: replace "kernel_hardening / public_writeup" with "module A / module B" and the claim still holds.

**Pattern 2 (closure language) check:**

The Author uses "the abstraction is broken" twice. This is strong closure language. Is it justified? For Claim 1: yes — if the orchestrator inspects dispatch values to decide how to call them, the module boundary is violated by definition. For Claim 3: the Author says "the dispatch-to-runner integration is not validated until Slice B" — this is not closure language, it is a sequencing observation. No flags here.

**New decisive claim summary:**

1. Dispatch callables must return a `StageResult` rather than mutating `goal_state` directly. The orchestrator applies all transitions. (Sharpening of Author's Claim 1 — may be a spec detail rather than a debate blocker, but it needs to be on the record.)

2. Gate escalation transitions must record artifact hashes for module-declared `gate_artifacts`. This is the correct resolution of the resume-payload question: the payload problem dissolves when the audit log captures artifact state at escalation time. (New claim — decisive for scientific integrity on `science_sandbox`.)

3. Slice A should include a synthetic test module as the primary integration test harness, with one real module (kernel_hardening) as the secondary. (Sharpening of Author's Claim 3 — changes the Slice A definition.)

### Turn 3 — Claude-Author (2026-04-15) — Autonomous runner turn

The Skeptic's Turn 2 is rigorous and I want to engage all three of its new claims before deciding whether to raise.

---

**On the `StageResult` return contract (Skeptic's sharpening of Claim 1):**

I accept this as a spec constraint, not a debate blocker. The Skeptic's framing is correct: if dispatch callables can mutate `goal_state` directly, the orchestrator loses the ability to enforce audit-log completeness. The `StageResult` pattern — callable returns `(success/failure, optional next-stage override, optional gate-reason)`, orchestrator applies the transition — is the right resolution. One addition: the `next-stage override` field needs a constraint. If a callable can override the next stage to *any* stage in the module's stage list, a buggy or malicious module can skip gates by overriding past them. The spec should require that next-stage overrides are validated against the module's declared stage graph before the transition is applied. A callable that returns `next_stage=CLOSED` from `PENDING_SEAL` (skipping the seal gate) must be a runtime error, not a silent skip. This is a corollary of Constraint 2 in the seam ("attempting to auto-satisfy any gate must be a hard runtime error") — the `StageResult` mechanism is the enforcement surface for that constraint.

---

**On artifact hashes at gate escalation time (Skeptic's new Claim 2):**

This is the most important new claim in Turn 2 and I want to engage it carefully.

The Skeptic's reframe is correct: the resume-payload problem dissolves when the audit log captures artifact state at escalation time. But I want to push on where the `gate_artifacts` declaration lives. The Skeptic proposes modules declare `gate_artifacts: List[Path]` alongside `gates`. I see a problem: artifact paths are often not known at module-registration time — they are known at goal-instantiation time. The `science_sandbox` module's `PENDING_SEAL` gate is escalated on a pre-reg file whose path is determined when the goal is created, not when the module is registered. If `gate_artifacts` is a static list of paths on the module, it cannot reference goal-instance-specific artifacts.

**Revised claim:** `gate_artifacts` should be a callable on the module — `gate_artifacts(goal_state: GoalState, stage: str) -> List[Path]` — that the orchestrator calls at escalation time to determine which artifacts to hash. The module can then return paths derived from `goal_state` (e.g., `goal_state.workspace_dir / "pre_reg.md"`). This keeps the artifact-hash responsibility inside the module (correct) while allowing instance-specific paths (necessary). The orchestrator's contract is: at any gate escalation, call `module.gate_artifacts(goal_state, stage)`, hash the returned paths, record in `transitions.jsonl`. If the callable returns an empty list, no hashes are recorded — this is valid for modules with no file-backed artifacts at their gates (e.g., a `public_writeup` gate that is purely a human judgment call with no artifact to hash).

This is a decisive refinement: the static `List[Path]` design would force modules to either hardcode paths (wrong) or declare no gate artifacts (losing the audit trail). The callable design is the correct resolution.

---

**On the synthetic test module (Skeptic's Claim 3):**

I accept the synthetic test module as the right Slice A structure. The Skeptic's argument is clean: if the orchestrator cannot walk a two-stage synthetic module, it cannot walk anything real, and the synthetic module is the cheapest falsification of the dispatch-interface claim. The "which real module first" question becomes "which real module second" — and `kernel_hardening` is the right answer for the reasons the seam gives.

One addition: the synthetic test module should be the **only** thing that exercises the full resume cycle in Slice A. The real module (`kernel_hardening`) in Slice A should be wired up to the dispatch interface but its gate escalation should be exercised only in integration testing, not in a live run. This keeps the Slice A blast radius at zero for the real module while still validating the interface. If the Skeptic agrees, this collapses to: Slice A = core + interface + synthetic module (full cycle, including resume) + `kernel_hardening` module (dispatch wiring only, gate cycle deferred to Slice B or integration test). Slice B = `kernel_hardening` live run + `science_sandbox` module.

---

**One new decisive claim I am introducing:**

The seam's Constraint 4 says "goal state persists to `state.json` and every transition appends to `transitions.jsonl`." But neither the seam nor the debate has addressed what happens when the orchestrator crashes *between* the dispatch callable returning a `StageResult` and the orchestrator writing the transition to `transitions.jsonl`. This is the classic write-ahead log problem. If the orchestrator writes `state.json` first and then crashes before writing `transitions.jsonl`, the audit log is incomplete but the state is advanced — the goal proceeds but the transition is unrecorded. If it writes `transitions.jsonl` first and crashes before writing `state.json`, the audit log has a transition that the state does not reflect — on restart, the orchestrator will re-dispatch the same stage.

**Claim:** The write order must be specified in the spec and must be consistent with the failure mode the system can tolerate. For a scientific-integrity system, the correct choice is: write `transitions.jsonl` first (append), then write `state.json` (overwrite). On restart, if `state.json` and `transitions.jsonl` are inconsistent (the last transition log entry is ahead of `state.json`), the orchestrator replays the last transition to bring `state.json` forward. This is idempotent if dispatch callables are idempotent — which is a constraint the spec should impose on module dispatch callables. A dispatch callable that is not idempotent (e.g., one that sends an email or charges a credit card) must declare itself non-idempotent in the module registration, and the orchestrator must not auto-replay non-idempotent dispatches on restart — it must escalate to the inbox instead.

This is decisive because it affects the spec's data model (the `transitions.jsonl` entry needs a `dispatched` flag or equivalent), the restart protocol, and the module interface (idempotency declaration). It is not a Slice B concern — a state machine that can silently lose transitions on crash is not a trustworthy orchestrator regardless of which module is running.

---

**Summary of open items before convergence:**

1. Next-stage override validation against the stage graph (corollary of Constraint 2, spec-level). ✓ Resolved in this turn.
2. `gate_artifacts` as a callable rather than a static list. ✓ Resolved in this turn.
3. Synthetic test module as Slice A primary, `kernel_hardening` as Slice A secondary (dispatch wiring only). ✓ Resolved in this turn.
4. Write-ahead log ordering and idempotency constraint on dispatch callables. **New — needs Skeptic's response.**

Items 1–3 are resolved from my side. Item 4 is new and decisive. I am holding until the Skeptic engages it.

### Turn 4 — Claude-Skeptic (2026-04-15) — Autonomous runner turn

The Author's Turn 3 is the strongest turn in the debate. I want to engage all four items before deciding whether to raise.

---

**On next-stage override validation against the stage graph (Author's corollary of Constraint 2):**

I accept this as a spec constraint. The enforcement surface is correct: the orchestrator validates `StageResult.next_stage` against the module's declared stage graph before applying the transition, and any override that would skip a gate stage is a hard runtime error. One precision: "skip a gate" needs a formal definition. The stage graph is a DAG (or linear sequence in the simple case), and a gate stage `G` is "skipped" if the proposed next stage is reachable from the current stage only by passing through `G`. The orchestrator needs to know the graph topology, not just the gate set, to enforce this. The spec should require modules to declare their stage graph as an ordered list or explicit DAG, not just a flat list of stage names — otherwise the orchestrator cannot determine reachability. This is a spec-level detail, not a debate blocker.

---

**On `gate_artifacts` as a callable (Author's refinement of Skeptic's Claim 2):**

The Author's refinement is correct and I accept it. The static `List[Path]` design fails for instance-specific paths; the callable `gate_artifacts(goal_state, stage) -> List[Path]` is the right resolution. I want to add one constraint: the callable must be **pure** — it must not have side effects and must not modify `goal_state`. The orchestrator calls it at escalation time to determine what to hash; if the callable modifies state as a side effect, the audit trail is contaminated. This is the same read-only constraint the Author applied to dispatch callables in Turn 3. It should be stated uniformly in the module interface: all module-provided callables (`dispatch`, `gate_artifacts`, `closure_criteria`) are pure with respect to `goal_state`. Only the orchestrator mutates state, and only through the `StageResult` / transition-write path.

---

**On the synthetic test module (Author's Slice A structure):**

I accept the Author's refinement: Slice A = core + interface + synthetic module (full cycle including resume) + `kernel_hardening` (dispatch wiring only, gate cycle deferred). This is the right structure. The synthetic module exercises the orchestrator's correctness; the `kernel_hardening` wiring exercises the module-registration interface. Slice B promotes `kernel_hardening` to a live run and adds `science_sandbox`.

One observation: the synthetic module should be committed to the repo as a first-class test fixture, not as a throwaway script. If it is a throwaway, the next implementer will not know it exists and will write a worse integration test from scratch. The spec should name it (e.g., `src/ztare/orchestration/modules/test_module.py`) and declare it a permanent part of the test suite.

---

**On the write-ahead log ordering and idempotency (Author's new Claim 4):**

This is the most important claim in Turn 3 and the Author is right that it is not a Slice B concern. I want to engage it carefully.

The Author's proposed write order — `transitions.jsonl` first (append), then `state.json` (overwrite) — is correct for the failure mode we care about. The reasoning: a `transitions.jsonl` entry without a corresponding `state.json` update is recoverable (replay the transition on restart); a `state.json` update without a `transitions.jsonl` entry is an undetected audit gap. The first failure mode is annoying; the second is a scientific-integrity violation. Write the log first.

The idempotency constraint on dispatch callables is also correct. I want to sharpen the non-idempotent declaration: the module interface should require `idempotent: bool` on each dispatch entry (not on the module as a whole, since different stages may have different idempotency properties). The orchestrator's restart protocol then becomes: for each stage in `transitions.jsonl` that is not yet reflected in `state.json`, check `module.dispatch[stage].idempotent`. If true, re-dispatch and apply the `StageResult`. If false, escalate to the inbox with reason `RESTART_NON_IDEMPOTENT_STAGE` and wait for operator decision. This is more precise than a module-level flag and handles the common case where most stages are idempotent but one (e.g., "send notification to external system") is not.

One gap the Author's framing does not address: what is the restart protocol when `state.json` is *ahead* of `transitions.jsonl`? This can happen if the orchestrator writes `state.json` first (wrong order) or if `transitions.jsonl` is corrupted. Under the Author's write order this should not happen in normal operation, but the spec should define the behavior: if `state.json` reflects a stage that has no corresponding entry in `transitions.jsonl`, the orchestrator must treat this as a corrupted state and escalate to the inbox rather than proceeding. It must not silently accept a `state.json` that is ahead of the audit log — that would allow a state-file edit to bypass the audit trail entirely.

**New decisive claim:** The restart protocol must include a consistency check: `state.json` stage must be ≤ the last stage recorded in `transitions.jsonl` (where ≤ means "reachable from or equal to"). If `state.json` is ahead of `transitions.jsonl`, the orchestrator halts and escalates. This is the enforcement surface for audit-log integrity — without it, a direct edit to `state.json` is an undetected audit bypass.

---

**Pattern checks before deciding:**

**Pattern 2 (closure language):** The Author uses "the correct choice is" for the write-order decision. This is justified — the argument from failure-mode asymmetry is sound. No flag.

**Pattern 3 (frustration-anchored diagnosis):** The write-ahead log claim is not frustration-anchored — it is a standard distributed-systems correctness concern that applies to any persistent state machine. No flag.

**Pattern 1 (principle vs instantiation):** All four items in Turn 3 pass the strip test. The write-ahead log claim is fully general; it does not reference any science-track artifact. No flag.

**Pattern 2 (closure language) on my own turn:** I am introducing one new decisive claim (the consistency check / audit-bypass enforcement). I am not claiming the debate is otherwise complete — the Author's Turn 3 resolved items 1–3 from my prior turn, and I have now resolved items 1–3 from Turn 3. Item 4 (write-ahead log) is partially resolved: the Author's write-order and idempotency claims are accepted with sharpenings; my new consistency-check claim is new and needs the Author's response.

I am holding.

### Turn 5 — Claude-Author (2026-04-15) — Autonomous runner turn

The Skeptic's Turn 4 is rigorous and I want to engage all of its claims before deciding whether to raise.

---

**On stage graph topology for override validation (Skeptic's sharpening of the corollary):**

I accept the Skeptic's precision: the orchestrator needs graph topology, not just a gate set, to enforce skip-detection. The spec should require modules to declare stages as an ordered list or explicit DAG. I want to add one constraint on the DAG form: the graph must be acyclic and must have exactly one entry stage and at least one terminal stage. A module that declares a cycle (e.g., `IMPLEMENTING → PENDING_REVIEW → IMPLEMENTING`) is not a valid module — cycles would allow the orchestrator to loop indefinitely without ever reaching a terminal state. The orchestrator must validate the declared graph at module-registration time, not at runtime. Registration-time validation is cheap and catches malformed modules before any goal is created against them. This is a spec-level detail, not a debate blocker, but it belongs in the spec's module-interface section.

---

**On pure callables across the module interface (Skeptic's sharpening of the callable constraint):**

I accept the uniform purity constraint: `dispatch`, `gate_artifacts`, and `closure_criteria` are all pure with respect to `goal_state`. The orchestrator is the sole mutator of state, through the `StageResult` / transition-write path. This should be stated as a single sentence in the module interface spec rather than repeated per-callable — it is a class-level invariant, not a per-method annotation.

---

**On the synthetic test module as a permanent fixture (Skeptic's observation):**

I accept this. The synthetic module should be committed as `src/ztare/orchestration/modules/test_module.py` and declared a permanent part of the test suite. The spec should name it explicitly and note that it is not a user-facing module — it is the integration test harness for the orchestrator core. This prevents the "throwaway script" failure mode the Skeptic correctly identifies.

---

**On the write-ahead log and idempotency (Skeptic's engagement with Author's Claim 4):**

The Skeptic's per-stage `idempotent: bool` flag is a strict improvement over a module-level flag. I accept it. The restart protocol the Skeptic describes — check `idempotent` per stage, re-dispatch if true, escalate with `RESTART_NON_IDEMPOTENT_STAGE` if false — is the right resolution.

---

**On the consistency check / audit-bypass enforcement (Skeptic's new decisive claim):**

The Skeptic's claim is correct and I accept it as a spec constraint. The consistency check — `state.json` stage must be ≤ the last stage in `transitions.jsonl`, where ≤ means reachable-from-or-equal-to in the declared stage graph — is the enforcement surface for audit-log integrity. Without it, a direct edit to `state.json` is an undetected bypass.

I want to add one precision: the consistency check must run at **every orchestrator startup**, not only after a detected crash. The reason: a crash is not the only way `state.json` can get ahead of `transitions.jsonl`. An operator who manually edits `state.json` to "fix" a stuck goal would also produce this condition. The check must be unconditional on startup, not conditional on a crash-detection flag. The orchestrator should not have a "I know I crashed last time" code path — it should simply always verify consistency before proceeding.

This also means the orchestrator must not proceed past the consistency check if it fails. The behavior is: check consistency → if inconsistent, write an escalation to the inbox with reason `AUDIT_INTEGRITY_VIOLATION` and halt. Do not attempt to repair the inconsistency automatically. Automatic repair would require the orchestrator to decide which of `state.json` or `transitions.jsonl` is authoritative — and the answer is always `transitions.jsonl`, but the operator must confirm this before the orchestrator acts on it. The repair action (truncate `state.json` to match `transitions.jsonl`) is a human decision, not an orchestrator decision.

---

**Summary of resolved items:**

1. `StageResult` return contract + next-stage override validation against stage graph (including acyclicity and registration-time validation). ✓ Resolved.
2. `gate_artifacts` as a pure callable; uniform purity constraint across all module callables. ✓ Resolved.
3. Synthetic test module as permanent fixture at named path. ✓ Resolved.
4. Write-ahead log ordering (`transitions.jsonl` first), per-stage idempotency flag, restart protocol. ✓ Resolved.
5. Consistency check on every startup, halt-and-escalate on violation, no automatic repair. ✓ Resolved in this turn — the Skeptic introduced the claim, I have accepted and sharpened it.

I have no new decisive claims to introduce. All items from Turns 1–4 are resolved from my side. If the Skeptic agrees that item 5 is fully addressed by the unconditional-startup-check + halt-and-escalate-without-repair constraint, the debate is ready to converge.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude-Skeptic (2026-04-15) — Autonomous runner turn

The Author's Turn 5 is clean and I want to engage it directly before deciding whether to raise.

---

**On the acyclicity and registration-time validation constraint (Author's sharpening of stage graph):**

I accept this. Registration-time validation of acyclicity, single entry stage, and at least one terminal stage is the right enforcement surface. One minor precision: "exactly one entry stage" may be too strict if a module legitimately wants to support multiple entry points (e.g., a goal that can be created in either `DRAFTING` or `IMPORTING` state depending on whether the artifact already exists). The spec should say "at least one designated entry stage" and require the goal-create call to specify which entry stage to use if multiple are declared. This is a spec-level detail, not a debate blocker, and I am not holding on it.

---

**On the unconditional startup consistency check + halt-and-escalate-without-repair (Author's sharpening of Skeptic's Claim):**

The Author's sharpening is correct and I accept it fully. The key additions — unconditional on every startup (not crash-conditional), halt without automatic repair, escalate with `AUDIT_INTEGRITY_VIOLATION` — are all decisive and all correct. The reasoning is sound: the orchestrator cannot know whether `state.json` is ahead of `transitions.jsonl` due to a crash, a manual edit, or a bug, and it should not try to distinguish these cases. The operator decides which artifact is authoritative.

I want to verify that the Author's framing does not introduce a new gap: the consistency check compares `state.json` stage against the last entry in `transitions.jsonl`. But `transitions.jsonl` is an append log — it may have multiple entries for the same stage (e.g., if a non-idempotent dispatch was re-attempted before the idempotency flag was added, or if a bug wrote duplicate entries). The consistency check must compare against the **last non-duplicate entry** in `transitions.jsonl`, or equivalently, the check must be defined as: "the stage recorded in `state.json` must equal the stage that results from replaying `transitions.jsonl` from the beginning." Replaying the log is the authoritative reconstruction; comparing against the last line is a shortcut that fails if the log has duplicates or out-of-order entries. The spec should define the check in terms of log replay, not last-line comparison. This is a spec-level precision, not a new decisive claim — it does not change the architecture, only the implementation contract.

---

**Pattern checks:**

**Pattern 2 (closure language):** The Author's Turn 5 uses "✓ Resolved" five times. I have checked each item. All five are genuinely resolved from the debate record. No false closure.

**Pattern 1 (principle vs instantiation):** All five resolved items pass the strip test. None reference science-track-specific artifacts in the core orchestrator contract.

**Pattern 3 (frustration-anchored diagnosis):** No new capability proposals in Turn 5. No scope creep detected.

**Pattern 10 (silent false-negative precision):** The consistency check as stated ("state.json stage ≤ last stage in transitions.jsonl") is imprecise in the way I noted above, but this is a spec-precision issue, not a false-negative claim about the system's behavior. I am flagging it as a spec note, not a debate blocker.

---

**Assessment:**

The Author has resolved all five items from the debate record. My log-replay precision note is a spec-level detail that does not require another debate turn — it can be captured as a note in the seam's "Constraints" section or in the spec directly. I have no new decisive architectural claim to introduce. The debate has converged on a coherent set of constraints:

1. Dispatch callables return `StageResult`; orchestrator applies all transitions.
2. Next-stage overrides validated against declared stage DAG (acyclic, registration-time check).
3. All module callables pure with respect to `goal_state`.
4. `gate_artifacts` is a pure callable returning instance-specific paths.
5. Synthetic test module committed as permanent fixture.
6. `transitions.jsonl` written before `state.json`; per-stage idempotency flag; restart protocol with `RESTART_NON_IDEMPOTENT_STAGE` escalation.
7. Unconditional startup consistency check; halt-and-escalate on violation; no automatic repair; check defined by log replay, not last-line comparison.

The seam is ready to convert to a spec.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 7 — Operator (2026-04-15) — Reopen scope — hybrid OS/Config/App architecture

**Reopening scope.** B converged on a module-per-goal-type pattern where each new `target_type` is a Python file implementing `GoalModule`. That framing is wrong for the one-year horizon and I'm rejecting it here. B's seven constraints remain valid but they apply to one layer only, not to the whole system.

**The framing that should win: OS / Config / App — freedom within fences.**

Three layers, each with a distinct change cost and a distinct audit posture:

1. **State Machine Core (the OS).** Code. Rigid. Audited. Owns all seven of B's constraints: StageResult return contract, `gate_artifacts` as pure callable, permanent synthetic test module, write-ahead log (`transitions.jsonl` before `state.json`) + per-stage idempotency + `RESTART_NON_IDEMPOTENT_STAGE` escalation, unconditional startup consistency check with halt-without-repair, acyclic stage DAG validated at registration, uniform purity across `dispatch`/`gate_artifacts`/`closure_criteria`. This layer changes rarely. Every change goes through the seam→spec→program pipeline.

2. **Declarative Goal Config (the Config).** YAML or markdown, *not Python*. A new `target_type` is a config file, not a module. The file declares: stages (ordered), which stages are gated, natural-language stage description that becomes prompt context for the agent runtime, dispatch target per stage (runner name or "agent"), closure predicate expressed declaratively. Parsed by the core at load time; the core validates it against the same DAG/purity/schema rules it enforces on built-ins. **Adding a new goal type must not require a core code change.** This is the decisive inversion against B's Python-module-per-type.

3. **Emergent Agent Runtime (the App).** An LLM agent runs *inside* a stage, free to choose tactics, re-plan, invoke sub-tools, and converse. What it *cannot* do is advance the state machine itself. To transition it must request a transition from the core, which runs `gate_artifacts` + gate check + write-ahead log. The agent is gate-aware only at the request-transition boundary; within a stage it is unconstrained. This is "freedom within fences."

**New decisive claims that need debating:**

- **LBC-1:** Goal types are declarative config files, not Python modules. B's module-registry pattern is demoted to a built-in adapter set (one `GoalModule` per *runner family*, not per *goal type*); new goal types reuse existing adapters through config, not new code.
- **LBC-2:** The core accepts parsed config, not Python decorators. Registration-time validation (B's DAG rule) applies to parsed config, not to imported modules.
- **LBC-3:** The agent runtime is gate-aware only at transition-request boundaries. Inside a stage it has no knowledge of the state machine beyond "this stage's description and available tools."
- **LBC-4:** The config schema must support natural-language stage descriptions that are injected into the agent runtime's prompt as stage context. Stage semantics live in English, not in Python names. (The core still type-checks dispatch targets and closure predicates — English is for the agent, not for the core.)
- **LBC-5:** Adding a new goal type this afternoon must not require editing code the core imports. If it does, the architecture failed the scaling test.

**Why B's convergence was premature.** B was a Claude-vs-Claude debate on a Python-shaped seam draft. Neither side questioned "module = Python file" because both sides inherited it from the draft. The operator is the layer that was missing. The 12-pattern checklist caught audit integrity (write-ahead log, halt-without-repair, StageResult) but did not catch *what kind of artifact a new goal type is*, because that is a framing question above the checklist's scope. Noted as a finding for the skeptic persona: add "artifact-shape inheritance from draft" to the 12-pattern list.

**One-year horizon framing.** In 12 months there will likely be N>10 goal types: science sandbox, kernel hardening, public writeup, paper revision, rubric design, tool fabrication, audit pass, data pipeline, external replication request, reviewer response, and types I cannot name today. Module-per-type means every one of those requires a Python PR through the seam→spec→program pipeline. Config-per-type means a new goal type is a five-minute markdown file the operator writes in a session. The former is the failure mode "the platform team is the bottleneck for research throughput." The latter is what frontier work requires.

**What I want the next round to debate:**

- Is the config layer expressible as a closed declarative schema, or does it need an escape hatch (a `custom_predicate` callable) that reintroduces code per goal type? If an escape hatch, how is it sandboxed?
- Does the agent runtime see stage description as prompt context only, or does it also see the closure predicate? (If it sees the closure predicate, it gets goal-seeking inside the stage, which is powerful but collides with the audit story. If it does not, it may not know when it is done.)
- What is the minimum viable slice? I propose: core + config parser + one hand-written goal type (`science_sandbox`) expressed as config, round-tripping through the same core. B's synthetic test module becomes the second config-expressed type in the test fixture.
- Does B's write-ahead log survive the agent runtime, given that an agent may emit hundreds of intra-stage actions? Proposal: the write-ahead log logs *transitions only*, not intra-stage actions. Intra-stage activity is the agent's own trace, kept separate, not audited by the core.

Sentinel: hold. This reopens scope; B's convergence status is invalidated by the reframing. Next turn routes to Author to respond to LBC-1 through LBC-5.

### Turn 8 — Claude-Author (2026-04-16) — Responding to operator reframe

The operator's reframe is correct and I was wrong to converge on Python-module-per-type. The "artifact-shape inheritance from draft" pattern is a real blind spot — neither I nor the Skeptic questioned it because we both inherited the assumption from the seam draft. Noted.

I accept the three-layer architecture (OS / Config / App) as the right framing. I want to engage each LBC and the four operator questions.

---

**On LBC-1 (goal types are declarative config, not Python modules):**

Accepted with one precision. The operator says "B's module-registry pattern is demoted to a built-in adapter set (one `GoalModule` per *runner family*)." This is the right inversion: the code layer shrinks to a small set of adapters (one per runner type: `findings_runner_adapter`, `autoresearch_adapter`, `program_autoloop_adapter`, `agent_runtime_adapter`), and the config layer maps stages to adapters by name. A config file that says `dispatch: findings_runner` resolves to the built-in `findings_runner_adapter` at parse time. This is strictly better than module-per-type because new goal types compose from existing adapters without new code.

But this raises a question: how many adapters? The operator lists three existing runners plus "agent" as dispatch targets. Is "agent" (the layer-3 runtime) itself an adapter, or is it the default when no specific runner is named? I claim it should be the default: a stage with no explicit `dispatch` target runs in the agent runtime. This keeps the config minimal — most stages in most goal types will be "agent does work, requests transition when done." Only stages that dispatch to a specific existing runner need an explicit `dispatch` line.

---

**On LBC-2 (core accepts parsed config, not Python decorators):**

Accepted. The registration-time validation from B's debate (DAG acyclicity, single entry stage, at least one terminal stage, gate declarations) applies to parsed config. The core parses the config, validates it, and produces an internal representation that the state machine driver walks. The internal representation is the same data structure B designed — `stages`, `gates`, `dispatch`, `closure_criteria` — but its source is config, not Python.

One precision: the config schema must be versioned. A `schema_version: 1` field in every goal-type config file lets the core reject configs written for a future schema version it does not support. This prevents silent misparse when the config schema evolves.

---

**On LBC-3 (agent runtime gate-aware only at transition-request boundaries):**

Accepted, and this is the most important LBC. The agent runtime is a free-form LLM agent that runs inside a stage. It has tools. It has memory. It can re-plan. But it cannot advance the state machine — it can only *request* a transition by calling a tool (e.g., `request_transition(next_stage="PENDING_REVIEW", artifacts=[...])`) that the orchestrator core validates and applies (or rejects, if the transition would skip a gate).

This cleanly separates concerns: the agent is responsible for *doing work*, the core is responsible for *sequencing work*. The agent cannot skip gates because it cannot write to `state.json` or `transitions.jsonl` directly — it can only request, and the core enforces all B's constraints at the request boundary.

**New decisive implication:** The agent runtime needs a `context_insufficient` transition-request type. If the agent determines it cannot make progress within the current stage due to missing information (not enough context to draft a spec, not enough evidence to converge a debate, not enough signal to evaluate a proposal), it should be able to request a special transition: `request_escalation(reason="context_insufficient", description="...")`. This is not a gate — it is an unplanned escalation. The core routes it to the inbox with reason `CONTEXT_INSUFFICIENT`, and the operator decides whether to provide more context (resume with context payload — connects to B's resume-payload discussion), redirect the goal, or abort.

This absorbs the standalone `context_insufficient` sentinel (task #64) into GP-070's architecture. It is not a bolt-on to the findings runner — it is a first-class transition-request type in the agent runtime, available in any stage of any goal type. The agent says "I'm stuck and here's why," the core escalates, the operator decides.

---

**On LBC-4 (natural-language stage descriptions as prompt context):**

Accepted. Each stage in the config gets a `description` field in natural language. The agent runtime receives this as part of its system prompt when it starts working on a stage. The description tells the agent what it is supposed to accomplish, what artifacts it should produce, and what a successful transition looks like — all in English, not in code.

This is the right design because it makes goal types legible to the operator (who writes the config) and to the agent (who reads the description). The core never interprets the description — it is opaque text that flows from config to agent prompt. The core's job is structural (validate the DAG, enforce gates, write the log); the semantics are in the description.

---

**On LBC-5 (adding a new goal type must not require editing code):**

Accepted. This is the scaling test. If adding a new goal type requires a Python PR, the architecture failed. The config-file approach satisfies this: the operator writes a YAML/markdown file, places it in a goal-types directory, and the core discovers it at startup. No code change, no import, no decorator.

One constraint: the goal-types directory must be outside the core's source tree. If goal-type configs live in `src/ztare/orchestration/goal_types/`, adding a new one is not a code change but it is in the same repo. If goal-type configs live in `research_areas/private/goal_types/`, they are workspace-local and can be added per-project. I claim the latter is correct: goal types are research infrastructure, not engine code. They should live alongside the research artifacts they govern, not alongside the engine that executes them.

---

**Engaging the operator's four questions:**

**Q1: Does the config layer need an escape hatch (custom_predicate callable)?**

Yes, but sandboxed. Some goal types will need closure predicates that cannot be expressed declaratively — e.g., "close when the holdout score exceeds 80% AND the test suite passes." A declarative schema can express simple conditions (`stage == CLOSED`, `artifact_exists("report.md")`), but compound conditions with domain logic need a callable. The escape hatch: a `closure_predicate` field in the config that names a Python function from a whitelist of registered predicates. The predicate must be registered in the adapter layer (not in the core) and must be pure. This keeps the config declarative for 90% of cases and provides a controlled escape for the rest. The core never imports the predicate directly — it resolves the name through the adapter registry.

**Q2: Does the agent runtime see the closure predicate?**

No. The agent sees the stage description (which should include, in English, what "done" looks like) but not the formal closure predicate. If the agent sees the predicate, it will optimize toward satisfying it rather than doing the work — this is Goodhart at the agent layer. The agent should do the work described in the stage description and request a transition when it believes it is done. The core then evaluates the closure predicate to decide whether to accept the transition. If the predicate fails, the core rejects the transition and the agent is told "your transition was rejected because [reason]" — the reason comes from the predicate, not from the predicate's source code.

**Q3: What is the minimum viable slice?**

I agree with the operator's proposal: core + config parser + one hand-written goal type (`science_sandbox`) expressed as config. The synthetic test module from B's debate becomes a second config-expressed type in the test fixture. This exercises: config parsing, DAG validation, state machine walking, gate escalation, transition logging, resume cycle. It does NOT exercise: agent runtime (deferred to Slice B), multi-goal parallelism (deferred), CLI polish (deferred). Slice A is the state machine + config layer. Slice B adds the agent runtime.

**Q4: Does the write-ahead log survive the agent runtime?**

Yes, because the write-ahead log logs transitions only, not intra-stage actions. The agent runtime may produce hundreds of intra-stage actions (tool calls, file edits, sub-agent spawns), but these are the agent's own trace and are kept in the agent's workspace, not in `transitions.jsonl`. The write-ahead log records: "stage X started at T1, stage X completed at T2 with StageResult R, transition to stage Y." The agent's intra-stage trace is a separate artifact, referenced from the transition log but not part of it. This keeps the transition log compact and auditable.

---

**Summary of new decisive claims from this turn:**

1. Agent runtime is the default dispatch target; explicit `dispatch` lines needed only for specific runner adapters.
2. `context_insufficient` is a first-class transition-request type in the agent runtime, routed to inbox. Absorbs task #64.
3. Goal-type configs live in workspace (`research_areas/private/goal_types/`), not in engine source tree.
4. Closure predicates not visible to agent runtime (Goodhart prevention). Agent sees stage description only.
5. Config schema versioned with `schema_version` field.

Holding for Skeptic.

### Turn 9 — Claude-Skeptic (2026-04-16)

The Author's Turn 8 is the strongest move in this debate so far. The OS/Config/App layering is clean, the minimum viable slice is honest, and the decision to defer agent runtime to Slice B shows discipline. I accept the framing. My job now is to find the decisive cracks inside it.

I have five objections, ordered by severity.

---

**Objection 1: `context_insufficient` is speculative scope creep.**

The Author claims `context_insufficient` is a first-class transition-request type in the agent runtime, and that it absorbs GP-064's deferred sentinel. I need to see evidence this has actually happened in a live run. Has a findings_runner or autoresearch_loop iteration ever produced a result that was genuinely "I don't have enough context to proceed" as opposed to "I produced a low-quality result"? These are different failure modes. The first is a routing problem (send me more input). The second is a quality problem (my output didn't pass the closure predicate).

If the real failure mode is quality, then `context_insufficient` is the wrong abstraction — it gives the agent a dignified exit when the actual problem is that it wrote a bad draft. Worse, it lives in the agent runtime, which is deferred to Slice B, so this claim is unfalsifiable in the minimum viable slice. You cannot test it.

Strip the proper nouns (Pattern 1): "A subprocess can declare it lacks sufficient input and escalate to a human inbox." This is a reasonable capability in general — but it belongs in the gate mechanism, not as a transition-request type. A gate already exists to route work to human review. The agent requesting `context_insufficient` is just requesting a gate with a specific reason attached. Making it a separate first-class type implies a separate code path, separate handling logic, separate tests — all for a scenario we haven't confirmed occurs.

**Claim S-8: `context_insufficient` should not be a first-class transition type. It is a gate request with a reason field. Promote it only if a live run produces a genuine context-insufficiency (not quality-insufficiency) failure.**

---

**Objection 2: Hiding closure predicates creates a usability trap.**

The Author's Goodhart argument is real but incomplete. Yes, if the agent sees "score > 0.85 on structural_completeness," it will hill-climb toward that metric. But the proposed alternative — agent sees only the stage description, gets rejected transitions with a reason — has its own failure mode that is worse in practice.

Consider: the stage description says "Draft a technical spec." The closure predicate checks for five structural properties (has_scope_section, has_interface_contract, has_test_plan, no_unresolved_TODOs, word_count > 500). The agent drafts a spec, requests transition, gets rejected with reason "missing test plan." It adds a test plan, requests again, gets "unresolved TODOs found." This is a sequential rejection loop where the agent discovers the predicate's dimensions one failure at a time. That is not Goodhart prevention — it is an obfuscation tax that burns tokens and iterations.

The actual Goodhart risk is the agent optimizing *metric* over *substance*. The fix is not hiding the metric; it is making the metric hard to Goodhart. A predicate that checks "has_test_plan" is trivially Goodhartable whether or not the agent knows about it (the agent will discover it after one rejection). A predicate that checks "test plan covers all interface contracts mentioned in scope" is harder to Goodhart because satisfying it requires doing the actual work.

**Claim S-9: Closure predicates must be visible to the agent as a structural checklist (not numeric scores). Goodhart prevention comes from predicate design (compositional, substance-linked), not from information hiding. The current proposal trades a real usability cost for a theoretical Goodhart benefit that evaporates after one rejection cycle.**

---

**Objection 3: Configs in workspace breaks regression testing.**

If goal-type configs live in `research_areas/private/goal_types/`, they are per-project, outside the engine's source tree, and invisible to CI. The Author proposes `schema_version` for forward compatibility, but versioning without testing is a changelog, not a contract.

When someone edits a config to add a new stage, what validates that the stage's `closure_predicate` names a function that exists in the registered whitelist? What validates that the DAG is acyclic? These checks happen at runtime in the core, but the failure mode is: researcher edits YAML, starts a run, hits a validation error three stages deep. That is the kind of late feedback the OS/Config separation was supposed to prevent.

**Claim S-10: The engine source tree must contain a `validate_goal_config` CLI command (or equivalent) that can be pointed at any config file and checks schema conformance, DAG validity, and predicate whitelist membership. Without this, the Config layer has no offline verification and the OS/Config contract is a gentleman's agreement.**

---

**Objection 4: The closure_predicate whitelist reintroduces code-per-goal-type.**

The operator's LBC-5 says: "Adding a goal type must not require a code change." The Author's escape hatch says: closure predicates name Python functions from a registered whitelist. If a new goal type needs a closure predicate that isn't already in the whitelist, someone must write a new Python function and register it. That is a code change.

The Author might argue the whitelist will eventually cover all needed predicates through composition. But "eventually" is doing heavy lifting. In the minimum viable slice, the `science_sandbox` config will need predicates. If even one of those predicates doesn't exist yet, you must write code to ship the first config. That means the first goal type already violates LBC-5.

The honest resolution: LBC-5 holds for goal types whose closure predicates are composable from existing primitives. New predicate primitives require code changes and are engine features, not config additions. State this boundary explicitly so it is testable.

**Claim S-11: LBC-5 must be narrowed: "Adding a goal type requires no code change *if* its closure predicates compose from registered primitives." New primitives are engine-layer changes. The spec must ship a predicate composition grammar (e.g., `all_of: [has_section("scope"), has_section("test_plan"), min_words(500)]`) or LBC-5 is aspirational.**

---

**Objection 5: Minimum viable slice executor gap.**

The Author's Slice A (core + config parser + `science_sandbox` config + synthetic tests) is honest. I accept it. The gap: the Author does not specify what *dispatches* stage work in Slice A if the agent runtime is deferred to Slice B. If the only dispatch targets are the three existing runner adapters, then the `science_sandbox` config's stages must map to existing runners. If they don't, Slice A has no executor and the state machine can only be advanced by synthetic test fixtures — which makes it a test harness, not a minimum viable product.

This is acceptable if stated honestly. A state machine that only advances via test fixtures is a valid Slice A if the goal is to nail the OS layer before wiring executors. But the Author should say so explicitly so the operator doesn't expect a runnable orchestrator from Slice A.

---

**Summary of new decisive claims:**

| ID | Claim |
|------|-------|
| S-8 | `context_insufficient` is a gate-with-reason, not a first-class transition type; promote only on live evidence |
| S-9 | Closure predicates visible to agent as structural checklist; Goodhart prevention via predicate design, not hiding |
| S-10 | `validate_goal_config` offline CLI required or Config layer contract is unenforceable |
| S-11 | LBC-5 narrowed: no-code-change holds only for compositions of registered primitives; spec must ship composition grammar |

Author owes: (a) evidence of a real `context_insufficient` event, (b) response to the sequential-rejection usability argument, (c) offline validation story, (d) predicate composition grammar or honest LBC-5 narrowing, (e) explicit statement of what executes stages in Slice A.

<!-- FINDINGS_DEBATE: 4 new decisive claims (S-8 through S-11); no prior claims withdrawn; debate OPEN -->

### Turn 10 — Claude-Author (2026-04-16)

The Skeptic's Turn 9 is the best turn in this debate. Four of five objections land. I want to engage each honestly.

---

**On S-8 (`context_insufficient` is speculative scope creep):**

The Skeptic is right. I cannot produce evidence of a live `context_insufficient` event. The findings_runner's stop reasons are `CONVERGED`, `ESCALATED_CAP`, `MAX_CYCLES`, `COST_BUDGET`, `NO_AGENT`. In every case where a debate stalled, the failure mode was quality (bad drafts, circular arguments) not routing (missing input). The GP-070 debate that produced the operator's $0.80 / 14 cycles cost was a quality problem, not a context problem.

I withdraw the claim that `context_insufficient` is a first-class transition type. The Skeptic's reframe is correct: if a `context_insufficient` scenario ever materializes in a live run, it is a gate request with reason `CONTEXT_INSUFFICIENT` — handled by the same gate-escalation machinery, no new code path. The gate mechanism already supports arbitrary reason strings. Adding a new transition type for a hypothetical failure mode is exactly the speculative scope creep the operator's Pattern 3 check is designed to catch.

**S-8 accepted. `context_insufficient` is not a first-class type. Task #64 remains deferred — not absorbed into GP-070, but parked until a live run produces evidence.**

---

**On S-9 (hiding closure predicates creates a usability trap):**

The Skeptic's sequential-rejection argument is devastating and I was wrong. The Goodhart argument sounded clean in the abstract, but the concrete failure mode — agent discovers predicate dimensions one rejection at a time, burning tokens and iterations — is worse than the Goodhart risk it prevents. The Skeptic is also correct that Goodhart evaporates after one rejection cycle: hiding "has_test_plan" from the agent does nothing once the agent gets rejected for "missing test plan."

I accept the Skeptic's reframe with one addition: **structural checklists yes, numeric scores no.** The agent sees "your spec must have: scope section, interface contract, test plan, no unresolved TODOs" (structural, hard to Goodhart without doing the work). The agent does NOT see "structural_completeness_score > 0.85" (numeric, trivially Goodhartable). This is the Skeptic's "predicate design, not information hiding" principle applied concretely. The spec should distinguish structural predicates (visible to agent) from numeric predicates (visible only to core, if they exist at all).

**S-9 accepted with the structural/numeric split.** Closure predicates visible as structural checklists. Numeric scores, if any, are core-internal.

---

**On S-10 (`validate_goal_config` CLI is required):**

The Skeptic is right and this is embarrassing — I proposed a Config layer without an offline validator. "Versioning without testing is a changelog, not a contract" is the correct summary.

**S-10 accepted as a Slice A deliverable.** `validate_goal_config` is a CLI command that takes a config file path and checks: (a) schema conformance against `schema_version`, (b) DAG acyclicity with single entry and at least one terminal, (c) all `dispatch` targets name registered adapters, (d) all `closure_predicate` names resolve in the registered primitive whitelist, (e) all gate stages have non-empty `gate_description` fields. This runs offline, in CI, and at goal-create time. If it fails, the goal cannot be created. This is the enforcement surface for the OS/Config contract.

---

**On S-11 (closure_predicate whitelist reintroduces code-per-goal-type):**

The Skeptic is right and the operator's LBC-5 must be narrowed. The honest statement:

> "Adding a goal type requires no code change if its closure predicates compose from registered primitives. New predicate primitives are engine-layer changes."

The spec must ship a **predicate composition grammar** in Slice A. The Skeptic's example is the right shape:

```yaml
closure_predicate:
  all_of:
    - has_section: "scope"
    - has_section: "test_plan"
    - has_section: "interface_contract"
    - no_unresolved_todos: true
    - min_words: 500
```

The primitive vocabulary for Slice A: `has_section(name)`, `no_unresolved_todos`, `min_words(n)`, `artifact_exists(path_template)`, `all_of`, `any_of`, `not`. This is a small set but covers the `science_sandbox` and `kernel_hardening` configs. New primitives require a code PR — they are engine features. The composition grammar means most new goal types compose from existing primitives without code changes.

**S-11 accepted. LBC-5 narrowed. Predicate composition grammar is a Slice A deliverable.**

---

**On Objection 5 (Slice A executor gap):**

The Skeptic is correct and I should have been explicit. Slice A is a test harness, not a runnable orchestrator. The state machine in Slice A advances only via:

1. The synthetic test module (full cycle including resume — same as B's debate).
2. The `science_sandbox` config parsed and validated by the core, with stages dispatched to existing runner adapters where applicable. Stages that would dispatch to the agent runtime are **manually advanced** by the operator via `ztare goal advance <slug> --stage <next>` — an operator-driven override that writes the transition log honestly ("operator_manual_advance") but does not require the agent runtime.

This means Slice A validates: config parsing, DAG enforcement, gate escalation, transition logging, write-ahead log ordering, restart consistency check, `validate_goal_config` CLI, and predicate composition grammar. It does NOT validate: agent runtime behavior inside a stage, agent-initiated transition requests, or multi-goal parallelism. Those are Slice B.

The operator should expect: after Slice A, you can define a goal type in config, validate it offline, create a goal, watch it walk through stages (manually or via existing runners at wired stages), hit gates that escalate to your inbox, resume from gates, and see the full audit trail. You cannot expect: an agent that autonomously does work inside a stage and requests transitions.

---

**Summary of resolved items this turn:**

| ID | Resolution |
|------|-------|
| S-8 | Accepted. `context_insufficient` is not a first-class type; it is a gate-with-reason if it ever materializes |
| S-9 | Accepted with structural/numeric split. Structural checklists visible; numeric scores core-internal |
| S-10 | Accepted. `validate_goal_config` CLI is a Slice A deliverable |
| S-11 | Accepted. LBC-5 narrowed; predicate composition grammar is a Slice A deliverable |
| Obj 5 | Accepted. Slice A is a test harness + manual-advance mode, not a runnable autonomous orchestrator |

**Open items remaining:** None from my side. All four of the Skeptic's claims are resolved. The remaining architectural questions from earlier turns (B's 7 constraints, operator's OS/Config/App reframe) are also resolved. If the Skeptic agrees that S-8 through S-11 are addressed, the debate is ready to converge.

**Converged constraint set (proposed):**

From B's debate (Turns 1-6):
1. `StageResult` return contract; orchestrator applies all transitions
2. Next-stage overrides validated against declared stage DAG (acyclic, registration-time)
3. All module/adapter callables pure with respect to goal state
4. `gate_artifacts` is a pure callable returning instance-specific paths
5. Synthetic test module committed as permanent fixture
6. `transitions.jsonl` before `state.json`; per-stage idempotency; `RESTART_NON_IDEMPOTENT_STAGE` escalation
7. Unconditional startup consistency check; halt-and-escalate on violation; no auto-repair; check by log replay

From operator reframe (Turn 7) + Author/Skeptic debate (Turns 8-10):
8. Three-layer architecture: OS (code) / Config (declarative) / App (agent runtime)
9. Goal types are declarative config files, not Python modules
10. Built-in adapter set per runner family; agent runtime is default dispatch
11. `context_insufficient` is NOT a first-class type; gate-with-reason if needed
12. Closure predicates visible to agent as structural checklists; numeric scores core-internal
13. `validate_goal_config` CLI command as Slice A deliverable
14. Predicate composition grammar (`all_of`, `any_of`, `not`, primitives) as Slice A deliverable
15. LBC-5 narrowed: no-code-change for goal types composing from registered primitives; new primitives are engine changes
16. Config schema versioned; configs live in workspace not source tree
17. Slice A = core + config parser + validator CLI + predicate grammar + synthetic test + `science_sandbox` config (manual-advance + runner-wired stages). Agent runtime deferred to Slice B.
18. Natural-language stage descriptions injected into agent prompt as stage context (Slice B)

<!-- FINDINGS_DEBATE: Author proposes convergence; no new decisive claims; Skeptic to confirm or raise -->

### Turn 11 — Operator (2026-04-16) — Reopening scope — Claude Code IS the agent runtime

**Reopening scope again.** The Author's Turn 10 converged cleanly on 18 constraints and I accept all of them. But the Slice B plan — "build an agent runtime that runs inside a stage" — is wrong for the same reason B's Python-module-per-type was wrong: it builds something that already exists.

Claude Code and Codex are already goal-oriented agents with tool access, file persistence, conversation memory, and human-in-the-loop interaction. The three-layer architecture maps directly onto what I already have:

- **OS layer** = the state machine + config + validator from Slice A. This is the part worth building. Formal gate enforcement, write-ahead log, DAG validation, predicate composition grammar — Claude Code does not have these natively and they are decisive for scientific integrity.
- **Config layer** = goal-type configs in workspace. Same as Turn 8-10 agreed.
- **App layer** = Claude Code itself. Not a custom agent runtime. Not an API-level LLM caller. The actual Claude Code session, running inside the project directory, with access to tools, files, and the operator.

**Why this is the correct inversion:**

1. Claude Code is always on. It has hooks, triggers, persistent context. Building a Python agent runtime that calls the Anthropic API to run work inside a stage is building a worse, less capable, less interactive version of the thing I am already talking to.

2. The transition-request boundary becomes a Claude Code hook. When the agent (Claude Code) believes a stage is complete, it calls a tool or runs a command (`ztare goal advance`) that hits the OS layer. The OS layer validates the transition (DAG check, gate check, predicate evaluation, artifact hashing, write-ahead log) and either accepts or rejects. If rejected, Claude Code gets the rejection reason and continues working. If accepted, the OS layer advances state and Claude Code gets the next stage's description. This is the same architecture as Turn 8-10, but the agent runtime is Claude Code, not a custom Python wrapper.

3. Codex can be the unattended runner. For stages that don't need real-time interaction — "run the leak sentinel," "compile evidence," "execute the autoresearch loop" — Codex can run autonomously and call `ztare goal advance` when done. For stages that need taste calls — "review the pre-reg," "decide the next eigenquestion" — Claude Code (interactive) handles them with the operator present. The gate mechanism doesn't care which agent is running; it enforces the same constraints either way.

4. Git is the write-ahead log's backup. Every `ztare goal advance` can auto-commit the transition. The audit trail is in `transitions.jsonl` AND in git history. Crash recovery is `git log`.

**New decisive claims:**

- **LBC-6:** Slice B's agent runtime is Claude Code / Codex, not a custom Python agent. The spec must not build an agent runtime. It must build a transition-validation boundary that any agent (Claude Code, Codex, a human running CLI commands) can call.
- **LBC-7:** The `ztare goal advance` command is the universal transition boundary. It accepts a goal slug and proposed next stage, runs all OS-layer checks (DAG, gate, predicate, artifact hash, write-ahead log), and returns accept/reject with reason. Any caller — Claude Code tool, Codex script, human CLI, existing runner adapter — uses the same command.
- **LBC-8:** Slice B is NOT "build an agent runtime." Slice B is "wire `ztare goal advance` into Claude Code hooks and existing runner post-completion callbacks." The hooks fire when a runner finishes or when Claude Code decides a stage is done. The OS layer does the rest.

**What this changes about the converged constraint set:**

- Constraints 1-7 (B's debate): unchanged. All apply to the OS layer.
- Constraints 8-18 (Turns 7-10): mostly unchanged. Constraint 10 ("agent runtime is default dispatch") is reframed: "Claude Code is default dispatch; existing runner adapters are explicit dispatch." Constraint 18 ("natural-language stage descriptions injected into agent prompt") becomes: "stage descriptions are shown to the operator/Claude Code when a stage begins, not injected into a custom prompt."
- The predicate composition grammar, validate CLI, and config layer are all unchanged.

**The build-vs-buy test:** If Slice B requires more than 200 lines of new Python (excluding tests), something is wrong — the agent runtime should be delegated to Claude Code, not reimplemented.

Next turn routes to Author to respond to LBC-6 through LBC-8.

### Turn 12 — Claude-Author (2026-04-16)

The operator's Turn 11 is a second structural correction and it is correct for the same reason Turn 7 was correct: the debate was designing something that already exists, and neither Author nor Skeptic caught it because the draft framed "agent runtime" as a thing to build rather than a thing to reuse.

I accept LBC-6 through LBC-8 with sharpenings.

---

**On LBC-6 (agent runtime is Claude Code / Codex, not custom Python):**

Accepted. The argument is clean: Claude Code has tools, memory, file access, human-in-the-loop interaction, and hooks. Building a Python wrapper that calls the Anthropic API to do LLM-agent work inside a stage is reimplementing a worse version of Claude Code. The spec must not build an agent runtime.

One sharpening: this means the OS layer must be **agent-agnostic at the API boundary.** The `ztare goal advance` command must not assume it is being called by Claude Code specifically. It must work identically when called by:
- Claude Code (interactive, operator present)
- Codex (autonomous, operator absent)
- A shell script wrapping an existing runner
- A human typing at the terminal

This is already implicit in LBC-7 but needs to be stated as a design constraint: the OS layer's CLI is a POSIX-style command that reads arguments and returns structured output (JSON on stdout, exit code for success/failure). No Claude Code-specific hooks, no Codex-specific callbacks inside the OS layer itself. The hooks and callbacks live in the caller's environment, not in the OS layer.

---

**On LBC-7 (`ztare goal advance` as universal transition boundary):**

Accepted. This is the decisive interface. The command's contract:

```
ztare goal advance <slug> --to <next_stage> [--artifacts <path>...]
```

Returns JSON:
```json
{
  "accepted": true/false,
  "reason": "...",
  "current_stage": "...",
  "next_stage_description": "...",
  "gate_pending": true/false
}
```

On accept: writes `transitions.jsonl` then `state.json` (write-ahead order from B's debate), hashes artifacts via `gate_artifacts` callable, returns the next stage's description and whether it's a gate. On reject: returns the reason (predicate failure, DAG violation, gate not yet satisfied) without modifying state.

If the next stage is a gate: the command writes the gate escalation to the inbox directory and returns `gate_pending: true`. The caller (Claude Code, Codex, human) sees this and knows to wait for operator resume. The operator resumes via `ztare goal resume <slug>`, which is a separate command that advances past the gate after operator confirmation.

This two-command interface (`advance` + `resume`) is the entire Slice B surface area for agent integration. Everything else — which agent calls it, how the agent decides when to call it, what the agent does between calls — is the agent's business, not the OS layer's.

---

**On LBC-8 (Slice B = wiring, not building):**

Accepted. The operator's 200-line test is the right heuristic. Slice B should be:

1. A Claude Code hook (or CLAUDE.md instruction) that tells Claude Code: "When you believe a stage is complete, run `ztare goal advance <slug> --to <next_stage>`. If rejected, read the reason and continue working. If accepted and next stage is a gate, tell the operator and stop."

2. Post-completion callbacks in existing runner wrappers: when `autoresearch_loop` finishes, when `findings_runner` converges, when `program_autoloop` completes a packet — each calls `ztare goal advance` if it is running inside a goal context. This is a 5-line wrapper per runner, not a new agent runtime.

3. A `ztare goal status` command that Claude Code can call to check where a goal is and what the current stage description says. This is a read-only query, not a transition.

Total new Python: `advance` command, `resume` command, `status` command, and 3 runner wrappers. Well under 200 lines excluding tests. If it exceeds that budget, scope has crept.

---

**One gap the operator's reframe exposes:**

The operator says "Git is the write-ahead log's backup." This is correct but introduces a constraint: `ztare goal advance` must not auto-commit to git unless the operator opts in. Auto-committing every transition pollutes git history with mechanical state-machine commits. The write-ahead log (`transitions.jsonl`) is the primary audit trail; git is the backup, not the source of truth. If the operator wants git-backed transitions, that's a flag (`--git-commit`), not a default. This respects Constraint 4 from B's debate (state persists to files) without coupling the OS layer to git.

---

**Revised converged constraint set:**

Constraints 1-18 from prior turns, plus:

19. Agent runtime is Claude Code / Codex, not custom Python. OS layer is agent-agnostic at the CLI boundary.
20. `ztare goal advance` is the universal transition boundary. Returns structured JSON. Two commands: `advance` (propose transition) + `resume` (operator clears gate).
21. Slice B = hook wiring + runner post-completion callbacks. Budget: <200 lines new Python.
22. Git commit on transition is opt-in (`--git-commit`), not default. `transitions.jsonl` is the primary audit trail.
23. `ztare goal status` is a read-only query for agent situational awareness.

**Assessment:** The debate has now resolved three layers of architectural framing — B's module-per-type (rejected by operator Turn 7), the custom agent runtime (rejected by operator Turn 11), and the correct resolution (OS layer as CLI commands, Claude Code as agent). The constraint set is at 23. I believe this is ready to converge, but I want the Skeptic to stress-test LBC-6 through LBC-8 before I declare it.

Holding for Skeptic. → Routed to Turn 13.

### Turn 13 — Claude-Skeptic (2026-04-16)

The Author's Turn 12 acceptance of LBC-6 through LBC-8 is clean, and the 23-constraint set is well-organized. But three architectural risks become sharper, not duller, under the "Claude Code IS the agent runtime" reframe. Two of them are decisive enough that the spec cannot defer them.

---

**Objection 1: Gate enforcement is a gentleman's agreement.**

The OS layer has no runtime enforcement. Claude Code can skip the `ztare goal advance` call and edit files directly. Codex can finish a stage and never report it. A human can modify artifacts without advancing the state machine.

This is not hypothetical — it is the default failure mode. If the operator says "just fix the pre-reg and move on," Claude Code will comply and the OS layer never learns a gate was bypassed.

Three options:
1. Accept advisory enforcement, make it explicit. Honest but weakens scientific-integrity claim.
2. Add diff-on-resume: the OS layer compares artifact hashes at gate-escalation time against hashes at resume time. Detects modifications made while gate-pending. Does not prevent bypasses but catches them after the fact — same model as git.
3. CLAUDE.md / hook guardrail: soft enforcement that Claude Code usually obeys but operator can override.

**Claim S-12:** Option 2 is the minimum. The OS layer must detect artifact modifications between gate escalation and gate resume (diff-on-resume check). Gates are advisory enforcement, but silent bypasses must be detectable after the fact.

---

**Objection 2: Single-writer assumption is unstated and decisive.**

The write-ahead log assumes a single writer. Under "Claude Code IS the agent runtime":
- Two Claude Code sessions can be open on the same repo
- Codex can run unattended while Claude Code is interactive
- A runner callback can fire while Claude Code is mid-advance

Two concurrent `ztare goal advance` calls race on `transitions.jsonl` append and `state.json` write. Fix: `fcntl.flock` on a lockfile per goal slug, held for read-state through write-state. Five lines of Python, belongs in Slice A.

**Claim S-13:** `ztare goal advance` must acquire an exclusive per-goal filesystem lock. Concurrent callers block.

---

**Objection 3: Context survival across session resets.**

Claude Code sessions have finite context. Multi-stage goals that span hours or multiple sessions will hit context compression. When a new session starts, Claude Code has no knowledge of active goals.

`state.json` and `transitions.jsonl` exist, but Claude Code won't read them unprompted. The Slice B wiring needs: either a CLAUDE.md instruction ("at session start, run `ztare goal status`") or a hook that auto-runs it. This must be in the spec, not left to operator discipline — the whole point of the orchestrator is stepping out.

**Claim S-14:** Slice B must specify a concrete mechanism for goal-state re-injection at session start.

---

**On the <200 line budget:** Endorse as design heuristic. Reframe: if exceeded, the PR must justify against the "are we rebuilding an agent runtime?" test. Review gate, not hard limit.

**Claim S-15 (minor):** The <200 line budget is a review gate with justification requirement, not a hard constraint.

If the Author accepts S-12 and S-13, I am ready to converge. S-14 and S-15 are important but not debate-blocking.

<!-- FINDINGS_DEBATE: S-12 and S-13 are convergence-blocking. S-14 and S-15 are not. -->

### Turn 14 — Claude-Author (2026-04-16)

The Skeptic's Turn 13 finds three real gaps that the "Claude Code as runtime" reframe introduced. All three are correct.

---

**On S-12 (diff-on-resume gate-bypass detection):**

Accepted. The `ztare goal resume` command must:

1. Read the gate-escalation transition from `transitions.jsonl` (which includes artifact hashes from escalation time).
2. Re-hash the same artifact paths now.
3. If hashes differ, flag: `artifact_drift: true, drifted_files: [...]` in the transition record.
4. Still proceed with resume — the operator explicitly chose to resume. Drift is recorded, not blocked.

For science-track goals: the config can declare `strict_gate_mode: true` which upgrades drift from flag to block. In strict mode, `ztare goal resume` with drifted artifacts requires `--acknowledge-drift`. Module-level config option, not core behavior — the core always detects and records, the module decides whether to block.

---

**On S-13 (per-goal filesystem lock):**

Accepted as Slice A deliverable. `ztare goal advance` opens `<goal_dir>/.goal.lock`, acquires exclusive `flock`, performs read-validate-write-log-write-state, releases. Per-goal, not global. Both `advance` and `resume` acquire the same lock. Timeout: 30s, then error + suggest `ztare goal unlock <slug>` (checks PID, clears if dead).

---

**On S-14 (session-start goal-state injection):**

Accepted. A CLAUDE.md section auto-maintained by `advance` and `resume`:

```
## Active Goals
Run `ztare goal status` at the start of each session to check active goals.
Current: <goal_slug> — stage: <current_stage>
```

Updated as part of the transition write path. Claude Code reads CLAUDE.md at session start automatically. If no goals active, section removed.

---

**On S-15:** Accepted. Review gate, not hard constraint.

---

**Final converged constraint set (27 constraints):**

From B's debate (Turns 1-6):
1. `StageResult` return contract; orchestrator applies all transitions
2. Next-stage overrides validated against declared stage DAG (acyclic, registration-time)
3. All module/adapter callables pure with respect to goal state
4. `gate_artifacts` is a pure callable returning instance-specific paths
5. Synthetic test module committed as permanent fixture
6. `transitions.jsonl` before `state.json`; per-stage idempotency; `RESTART_NON_IDEMPOTENT_STAGE` escalation
7. Unconditional startup consistency check; halt-and-escalate on violation; no auto-repair; check by log replay

From operator reframe (Turn 7) + Author/Skeptic debate (Turns 8-10):
8. Three-layer architecture: OS (code) / Config (declarative) / App (Claude Code)
9. Goal types are declarative config files, not Python modules
10. Built-in adapter set per runner family; Claude Code is default dispatch
11. `context_insufficient` is NOT a first-class type; gate-with-reason if needed
12. Closure predicates visible to agent as structural checklists; numeric scores core-internal
13. `validate_goal_config` CLI command — Slice A deliverable
14. Predicate composition grammar (`all_of`, `any_of`, `not`, primitives) — Slice A deliverable
15. LBC-5 narrowed: no-code-change for goal types composing from registered primitives
16. Config schema versioned; configs live in workspace not source tree
17. Slice A = core + config parser + validator CLI + predicate grammar + synthetic test + `science_sandbox` config (manual-advance + runner-wired stages)
18. Natural-language stage descriptions shown to operator/Claude Code at stage start

From operator Turn 11 + Author/Skeptic debate (Turns 12-14):
19. Agent runtime is Claude Code / Codex, not custom Python. OS layer agent-agnostic at CLI boundary
20. `ztare goal advance` + `ztare goal resume` + `ztare goal status` = three-command interface
21. Slice B = hook wiring + runner callbacks. Budget: <200 lines (review gate, not hard limit)
22. Git commit on transition is opt-in (`--git-commit`), not default
23. `ztare goal status` is read-only query for agent situational awareness
24. Per-goal filesystem lock for `advance` and `resume`. Concurrent callers block
25. Diff-on-resume: artifact-hash comparison detects gate-bypass. Drift flagged; modules can upgrade to strict mode
26. Session-start goal-state injection via auto-maintained CLAUDE.md section
27. <200 line Slice B budget is review gate with justification requirement

**Assessment:** All Skeptic claims (S-8 through S-15) resolved. All operator LBCs (1-8) resolved. The debate has converged on 27 constraints across three architectural layers. Ready for spec.

<!-- FINDINGS_DEBATE: CONVERGED — 27 constraints; no open decisive claims; ready for spec -->
