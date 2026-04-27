# Reflexive Engineering Primitives

**Status:** public companion to `docs/concepts/architecture.md`
**Companion docs:** `docs/internal/autoresearch_loop_architectural_map.md` (structural map), `docs/guides/reflexive_audit_workflow.md` (discovery mechanism)
**Philosophical parent:** Three Legs of ZTARE (Invert, Compress, Adversarial Disagreement)

---

## The Meta-Move

ZTARE rests on three legs: Invert, Compress, Adversarial Disagreement. These were derived as principles for the *science* the engine does — how to evaluate candidate models, how to test claims, how to detect gaming.

The reflexive engineering primitives are what happens when you apply those same legs to *the engine itself*. Each primitive is a specific instance of a ZTARE leg turned inward.

This is not circular. A weightlifter who applies progressive overload to their own training program (not just their lifts) is making the same move. ZTARE applying Compress to its own context management is the engine improving its own infrastructure using the same principles it uses to improve its candidates.

Every primitive below was discovered the same way: a specific failure occurred, the failure was recognized as infrastructure (not science), a ZTARE leg was applied reflexively, and a primitive emerged. None was designed from first principles. Each is testable against the failure that motivated it.

---

## Summary Table

| Primitive | Leg Applied | Target | Operational Goal |
|-----------|------------|--------|-----------------|
| Token-Optimized Self-Modeling | Compress | Agent's own cognition | Minimize error rate per token via structural caches |
| Inception Pattern | Invert | Agent's environment model | Force the agent to model the validation cage before proposing edits |
| Hybrid Persona Router | Adversarial Disagreement | Review layer expertise | Dynamically synthesize the sharpest committee for a failure family |
| Residual Isomorphism | Compress + Invert | Grammar expansion | Use farther-tail residuals to abduce missing mathematical primitives |
| Reflexive Orchestration | Adversarial Disagreement + Compress | Goal configs / lifecycle | Analyze audit logs to identify and patch structural friction in the workflow |
| Procedural Self-Audit | Compress + Invert | Agent's own task discipline | Typed task declaration + checklist gate catches skipped procedural steps |

---

## Primitive 1: Token-Optimized Self-Modeling

**Leg applied:** Compress (Leg 2)
**Target:** The agent's own understanding of its operational substrate

**The move:** The agent reads large files through a narrow context window — the same problem as observing a system through a narrow instrument window. Partial views cause globally wrong local edits. The standard fix (more documentation) is Ptolemaic: add tokens, hope the agent reads the right ones. The Compress move: build a minimal structural cache that gives the agent the global dependency graph in fewer tokens than reading any single region of the source file.

**What makes it reflexive:** Compress is a principle ZTARE applies to candidate models — prefer the form that survives outside the fit window with fewer assumptions. Token-Optimized Self-Modeling applies the same principle to the agent's own cognition — prefer the representation that prevents errors with fewer tokens consumed.

**Instantiation checklist:**
- File exceeds agent context capacity and partial reads cause ordering mistakes
- Pipeline ordering contracts exist (phase A must complete before phase C)
- A demonstrated error occurred from partial-view reading
- Build: region index + dependency chain + invariant contracts + edit-intent lookup table
- Format: structured blocks with typed DEPENDS_ON edges (not prose narrative)

---

## Primitive 2: Inception (Machine-Readable Environment Model)

**Leg applied:** Invert (Leg 1)
**Target:** The agent's awareness of the machinery it operates inside

**The move:** The agent proposes code changes without understanding the validation pipeline those changes will pass through. Standard fix: add more validation (more gates). Inverted fix: give the agent a pre-computed model of the gates so it can simulate rejection before proposing. This is not "prompting the agent to be careful" — it is providing a deterministic integrity specification the agent can check against.

**What makes it reflexive:** Invert is a principle ZTARE applies to candidate evaluation — ask "how would I kill this?" before asking "does this fit?" The Inception Pattern applies the same principle to the agent's own edit process — the agent asks "which gate would reject this?" before proposing the edit.

**Analogy:** Lipson et al.'s self-modeling robots build an internal model of their own body to simulate motor commands before executing them. The Inception Pattern is the same move for a code-editing agent — the architectural map is the "body model."

**Instantiation checklist:**
- Agent operates inside a multi-stage validation pipeline
- Errors arise from the agent not knowing which downstream gate rejects its output
- Build: typed dependency chain (PHASE_A output → PHASE_B input, etc.)
- Inject: into agent context before task, not after failure
- Format: edit-intent lookup table ("I want to do X → I MUST consult Y")

---

## Primitive 3: Hybrid Persona Router (Cache-Route-Generate-Promote)

**Leg applied:** Adversarial Disagreement (Leg 3)
**Target:** The review layer's own expertise selection

**The move:** Static personas are expert lenses that focus adversarial review on specific failure types. But the set of failure types is not closed — novel substrates produce novel failure families no pre-authored persona covers. Standard fix: author more personas (linear scaling, requires operator domain knowledge). Reflexive fix: the review system applies adversarial disagreement to its own persona selection — an LLM evaluates which static lenses are insufficient and generates a novel lens when needed.

**The promotion loop is the compression step:** A dynamically generated persona that proves useful gets compressed into a static, cached, versioned file. Compress applied to the Adversarial Disagreement layer — successful dynamic expertise crystallizes into reusable structure.

**Instantiation checklist:**
- Static persona catalog exists (avoid regeneration cost for proven lenses)
- LLM router selects from catalog based on observed failure signal (zero-oracle)
- Dynamic generation as fallback for unrecognized failure families
- Promotion on convergence: dynamic → static when proven effective
- Fallback to static routing table when LLM unavailable

---

## Primitive 4: Residual Isomorphism (Solving for the Shape of Ignorance)

**Leg applied:** Compress (Leg 2) + Invert (Leg 1)
**Target:** The grammar expansion mechanism itself

**The move:** When the engine's grammar ceiling is reached (best form fails the farther-tail gate), the failure residual — the structured discrepancy between the best static form and the observed data — encodes the mathematical shape of what the grammar is missing. Standard fix: operator injects a new primitive based on domain intuition (not scalable). Reflexive fix: the engine inverts its own failure (Leg 1) and compresses the residual into a primitive proposal (Leg 2).

**The Observability Axiom:** A missing primitive can only be discovered by visible-window search if it produces a detectable residual in the observation window. Residual Isomorphism breaks this constraint by using the farther-tail gate's failure signal — which the engine already computes — as the diagnostic input. The farther-tail gate sees catastrophic failure even when the visible window looks clean.

**Known limitation:** Works when the missing primitive is an additive correction. Multiplicative or nested corrections produce residuals that don't match the primitive library in their raw shape. This is accepted for n=1 and acknowledged as a scope boundary.

**Instantiation checklist:**
- Grammar ceiling reached (best form fails held-out gate)
- Farther-tail gate computes failure residual (already in `latest_eval_results.json`)
- Primitive library exists with known functional shapes
- Matcher emits primitive names only (no residual values leak to mutator)
- Composition seed format unchanged (information boundary preserved)

---

## Primitive 5: Reflexive Orchestration (Orchestration Isomorphism)

**Leg applied:** Adversarial Disagreement (Leg 3) + Compress (Leg 2)
**Target:** The goal lifecycle and declarative configs
**Status:** n=0 — conceptual, not yet implemented

**The move:** When a goal fails repeatedly at a specific stage, the failure is usually attributed to the hypothesis (the science was wrong). But sometimes the failure is in the process — the stage description is ambiguous, the gate criteria are miscalibrated, or a structural requirement is missing from the config. Standard fix: the operator manually audits and patches the config. Reflexive fix: the supervisor launches an Orchestration Audit goal that treats transition logs as evidence and uses the Hybrid Persona Router to convene a Process Committee that identifies structural friction.

**The discriminator:** Did the goal fail because of the science or because of the process? If removing or rewording one stage description would have changed the outcome, the failure was process. If no config change would have helped, the failure was science. The Orchestration Audit must make this distinction explicit.

**Open question:** Is this a new primitive or an instantiation of Hybrid Persona Router applied to a different layer? The mechanism (route personas to failure signal, generate if missing, promote on success) is identical — only the target changes from "review layer" to "orchestration layer." The answer depends on whether the implementation reveals new failure modes the router doesn't handle.

---

## The Pattern Class: What These Have in Common

1. **Each applies a ZTARE leg to the engine itself**, not to the candidate models the engine evaluates.
2. **Each was discovered from a specific failure.** None was designed from first principles. Token-Optimized Self-Modeling and Inception came from a partial-view edit mistake. The Persona Router came from static personas being insufficient for novel failure families. Residual Isomorphism came from Component D's visible-window blindness.
3. **Each is testable against the failure that motivated it.** The architectural map prevents the class of errors that motivated it. The persona router selects better lenses than the static table. Residual Isomorphism should break the grammar ceiling it was designed for.
4. **None requires new theoretical machinery.** Each is a straightforward application of an existing ZTARE principle to a new target. The novelty is the reflexive application, not the principle.

### Recognizing when a new primitive is needed

A new reflexive primitive is indicated when:
- The engine exhausts all known recovery mechanisms and still doesn't improve **in the same way** (zero-variance stagnation: the same gate fails with similar residual across K+ iterations)
- The failure can be traced to a **structural constraint in the infrastructure**, not to the difficulty of the substrate
- An existing ZTARE leg, applied reflexively to the stuck layer, would prevent the failure from recurring

This is the Groundhog Day signature: the engine is not exploring (which looks like thrashing across different failure modes) — it is stuck at a structural wall.

For the periodic discovery mechanism that detects this signature automatically, see `docs/guides/reflexive_audit_workflow.md`.

---

## Primitive 6: Procedural Self-Audit (Discipline Isomorphism)

**Leg applied:** Compress (Leg 2) + Invert (Leg 1)
**Target:** The agent's own task execution discipline

**The move:** Agents (LLM workers operating on the repo) systematically skip procedural steps defined in AGENTS.md — experiment closure rows, board updates, paper format synchronization, substrate validation checks. The failure mode is not capability (the agent knows the steps) but procedural drift (partial task completion under context pressure). Standard fix: "be more careful" (not scalable, not deterministic). Reflexive fix: the agent compresses its own task into a typed task-type declaration (Leg 2: compress), then inverts against the required checklist (Leg 1: what steps would I need to have skipped for this task to be incomplete?) before declaring done.

**What makes it reflexive:** The apparatus applies typed-input/typed-output validation to candidate models (Principle III). Procedural Self-Audit applies the same pattern to the agent's own work: task type is the input type, required steps are the contract, the validator is the gate.

**Instantiation:**
- Task discipline map: `docs/internal/agent_task_discipline_map.md`
- Validator: `scripts/validate_agent_task_discipline.py {pre,post,show,audit}`
- Session log: `workspace/agent_session_log.jsonl` (gitignored, per-session)
- Six task types: experiment_run, substrate_build, paper_edit, seam_update, recording, infrastructure
- Each type has typed pre-checks and post-checks derived from AGENTS.md

**The test:** Run `python scripts/validate_agent_task_discipline.py post experiment_run` after any experiment. If post-checks are incomplete, the agent fixes them before responding. The validator is the deterministic gate; AGENTS.md is the specification.

**Known limitation:** The session log is manually maintained by the agent. A dishonest agent can skip logging. The defense is the same as for any self-report system: the operator can audit `workspace/agent_session_log.jsonl` against actual repo state. The validator catches honest mistakes (forgot a step); it does not catch adversarial evasion.

---

## Where This Does NOT Belong

- **Not Paper 5 (the treatise).** The treatise makes claims about the decomposition of epistemic verification. These primitives are engineering patterns. They are evidence that the decomposition is useful, not claims about the world.
- **Not the Operational Manual (pre-run checklist).** The manual is for run-time checks. These primitives are design-time decisions — they are made when building a new component of the engine, not when launching a run.
- **This document is the right home.** It is a companion to the architecture doc (what the engine is) and the cognitive gym (why the engine cages the LLM). The reflexive primitives are how the engine improves its own cage.
