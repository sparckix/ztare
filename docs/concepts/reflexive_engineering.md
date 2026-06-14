---
description: "Reflexive engineering primitives, patterns the apparatus applies to itself."
---
# Reflexive Engineering Primitives

> **Up:** [Documentation map](../README.md)

**Status:** public companion to `docs/concepts/architecture.md`
**Companion docs:** [docs/guides/reflexive_audit_workflow.md](../guides/reflexive_audit_workflow.md) (discovery mechanism), [docs/concepts/agentic_engineering_patterns.md](agentic_engineering_patterns.md) (LLM-pipeline test patterns, sibling concept at the engineering layer)
**Philosophical parent:** Three Legs of ZTARE (Invert, Compress, Adversarial Disagreement)

> **How this differs from `agentic_engineering_patterns.md`.** Agentic
> engineering patterns are ordinary software practices adapted to LLM pipelines:
> record/replay testing, contract checks, AST canonicalization, and provenance.
> Reflexive primitives are narrower. They are cases where ZTARE applies its own
> research principles to its own infrastructure. The same mechanism can appear in
> both places: as a reusable engineering pattern in the agentic catalog, and as a
> reflexive primitive when ZTARE uses it to improve its own loop.

---

## What reflexive primitives are

ZTARE uses three recurring research moves: invert the claim, compress the useful
structure, and force disagreement between roles. Reflexive engineering means
using those same moves on the engine itself.

The test for inclusion is practical. A primitive belongs here when a concrete
infrastructure failure happened, the failure was not just "the science was hard,"
and the fix is a reusable move the engine can apply to itself again.

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
| Operator-Replay Mechanization | Compress + Invert | Operator-agent discovery loop | Recover the operator's next-test choices from durable artifacts and convert them into typed discriminators |
| Research Taste Router | Compress | Principal preference surface | Score next moves against configurable taste axes before spending GPU/API/human attention |
| Reflexive Forecast Market | Adversarial Disagreement + Compress + Invert | Research allocation / tick actions | Price proposed actions, learn from scored outcomes, and use named failure modes to precondition execution |

---

## Primitive 1: Token-Optimized Self-Modeling

**Leg applied:** Compress (Leg 2)
**Target:** The agent's own understanding of its operational substrate

**The move:** The agent reads large files through a narrow context window. Partial views cause globally wrong local edits. The standard fix (more documentation) adds tokens and hopes the agent reads the right ones. The Compress move: build a minimal structural cache that gives the agent the global dependency graph in fewer tokens than reading any single region of the source file.

**What makes it reflexive:** Compress is a principle ZTARE applies to candidate models, prefer the form that survives outside the fit window with fewer assumptions. Token-Optimized Self-Modeling applies the same principle to the agent's own cognition, prefer the representation that prevents errors with fewer tokens consumed.

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

**The move:** The agent proposes code changes without understanding the validation pipeline those changes will pass through. Standard fix: add more validation (more gates). Inverted fix: give the agent a pre-computed model of the gates so it can simulate rejection before proposing. This is not "prompting the agent to be careful", it is providing a deterministic integrity specification the agent can check against.

**What makes it reflexive:** Invert is a principle ZTARE applies to candidate evaluation, ask "how would I kill this?" before asking "does this fit?" The Inception Pattern applies the same principle to the agent's own edit process, the agent asks "which gate would reject this?" before proposing the edit.

**Analogy:** Lipson et al.'s self-modeling robots build an internal model of their own body to simulate motor commands before executing them. The Inception Pattern is the same move for a code-editing agent, the architectural map is the "body model."

**Instantiation checklist:**
- Agent operates inside a multi-stage validation pipeline
- Errors arise from the agent not knowing which downstream gate rejects its output
- Build: typed dependency chain (PHASE_A output → PHASE_B input, etc.)
- Inject: into agent context before task, not after failure
- Format: edit-intent lookup table ("I want to do X -> I must consult Y")

---

## Primitive 3: Hybrid Persona Router (Cache-Route-Generate-Promote)

**Leg applied:** Adversarial Disagreement (Leg 3)
**Target:** The review layer's own expertise selection

**The move:** Static personas are expert lenses that focus adversarial review on specific failure types. But the set of failure types is not closed, novel substrates produce novel failure families no pre-authored persona covers. Standard fix: author more personas (linear scaling, requires operator domain knowledge). Reflexive fix: the review system applies adversarial disagreement to its own persona selection, an LLM evaluates which static lenses are insufficient and generates a novel lens when needed.

**The promotion loop is the compression step:** A dynamically generated persona that proves useful gets compressed into a static, cached, versioned file. Compress applied to the Adversarial Disagreement layer, successful dynamic expertise crystallizes into reusable structure.

**Instantiation checklist:**
- Static persona catalog exists (avoid regeneration cost for proven lenses)
- LLM router selects from catalog based on observed failure signal (zero-oracle)
- Dynamic generation as fallback for unrecognized failure families
- Promotion on convergence: dynamic → static when proven effective
- Fallback to static routing table when LLM unavailable

---

## Primitive 4: Residual Isomorphism (abducing the missing primitive from the failure residual)

**Leg applied:** Compress (Leg 2) + Invert (Leg 1)
**Target:** The grammar expansion mechanism itself

**The move:** When the engine's grammar ceiling is reached (best form fails the farther-tail gate), the failure residual, the structured discrepancy between the best static form and the observed data, encodes the mathematical shape of what the grammar is missing. Standard fix: operator injects a new primitive based on domain intuition (not scalable). Reflexive fix: the engine inverts its own failure (Leg 1) and compresses the residual into a primitive proposal (Leg 2).

**Observability constraint:** A missing primitive can only be discovered by visible-window search if it produces a detectable residual in the observation window. Residual Isomorphism gets around this by using the farther-tail gate's failure signal, which the engine already computes, as the diagnostic input. The farther-tail gate registers failure even when the visible window looks clean.

**Known limitation:** Works when the missing primitive is an additive correction. Multiplicative or nested corrections produce residuals that don't match the primitive library in their raw shape. This is accepted for n=1 and is a scope boundary.

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
**Status:** n=0, conceptual, not yet implemented

**The move:** When a goal fails repeatedly at a specific stage, the failure is usually attributed to the hypothesis (the science was wrong). But sometimes the failure is in the process, the stage description is ambiguous, the gate criteria are miscalibrated, or a structural requirement is missing from the config. Standard fix: the operator manually audits and patches the config. Reflexive fix: the supervisor launches an Orchestration Audit goal that treats transition logs as evidence and uses the Hybrid Persona Router to convene a Process Committee that identifies structural friction.

**The discriminator:** Did the goal fail because of the science or because of the process? If removing or rewording one stage description would have changed the outcome, the failure was process. If no config change would have helped, the failure was science. The Orchestration Audit must make this distinction explicit.

**Open question:** Is this a new primitive or an instantiation of Hybrid Persona Router applied to a different layer? The mechanism (route personas to failure signal, generate if missing, promote on success) is identical, only the target changes from "review layer" to "orchestration layer." The answer depends on whether the implementation reveals new failure modes the router doesn't handle.

---

## The Pattern Class: What These Have in Common

1. **Each applies a ZTARE leg to the engine itself**, not to the candidate models the engine evaluates.
2. **Each was discovered from a specific failure.** None was designed from first principles. Token-Optimized Self-Modeling and Inception came from a partial-view edit mistake. The Persona Router came from static personas being insufficient for novel failure families. Residual Isomorphism came from the symbolic-regression path's visible-window blindness.
3. **Each is testable against the failure that motivated it.** The architectural map prevents the class of errors that motivated it. The persona router selects better lenses than the static table. Residual Isomorphism should break the grammar ceiling it was designed for.
4. **None requires new theoretical machinery.** Each is a straightforward application of an existing ZTARE principle to a new target. The novelty is the reflexive application, not the principle.

### Recognizing when a new primitive is needed

A new reflexive primitive is indicated when:
- The engine exhausts all known recovery mechanisms and still doesn't improve **in the same way** (zero-variance stagnation: the same gate fails with similar residual across K+ iterations)
- The failure can be traced to a **structural constraint in the infrastructure**, not to the difficulty of the substrate
- An existing ZTARE leg, applied reflexively to the stuck layer, would prevent the failure from recurring

The signature is zero-variance stagnation rather than thrashing: the engine is not exploring across different failure modes, it is stuck at one structural constraint.

For the periodic discovery mechanism that detects this signature automatically, see `docs/guides/reflexive_audit_workflow.md`.

### Current candidate boundary

Autoresearch workbench routing is intentionally treated as an implementation of
the agentic Pattern 16 contract compiler, not as a new reflexive primitive yet.
It is inward-facing infrastructure: the apparatus decides when its own in-loop
workbench should be used instead of manual RD/agent work, and records the route
as an action-impact row. That is valuable, but the REP bar is higher. Promotion
would require evidence across more than one context that the route receipt
changes behavior: fewer unexplained out-of-loop bypasses, more prepared
workbench surfaces, or better reuse of failed-branch constraints. Until then it
belongs in OP-AWR/action-intelligence machinery rather than in the primitive
catalogue.

---

## Primitive 6: Procedural Self-Audit (Discipline Isomorphism)

**Leg applied:** Compress (Leg 2) + Invert (Leg 1)
**Target:** The agent's own task execution discipline

**The move:** Agents (LLM workers operating on the repo) systematically skip procedural steps defined in AGENTS.md, experiment closure rows, board updates, paper format synchronization, substrate validation checks. The failure mode is not capability (the agent knows the steps) but procedural drift (partial task completion under context pressure). Standard fix: "be more careful" (not scalable, not deterministic). Reflexive fix: the agent compresses its own task into a typed task-type declaration (Leg 2: compress), then inverts against the required checklist (Leg 1: what steps would I need to have skipped for this task to be incomplete?) before declaring done.

**What makes it reflexive:** The apparatus applies typed-input/typed-output validation to candidate models (Principle III). Procedural Self-Audit applies the same pattern to the agent's own work: task type is the input type, required steps are the contract, the validator is the gate.

**Instantiation:**
- Task discipline map: local task-discipline rules compiled from `AGENTS.md`
- Validator: `scripts/public/validators/validate_agent_task_discipline.py {pre,post,show,audit}`
- Session log: `workspace/agent_session_log.jsonl` (gitignored, per-session)
- Six task types: experiment_run, substrate_build, paper_edit, seam_update, recording, infrastructure
- Each type has typed pre-checks and post-checks derived from AGENTS.md

**The test:** Run `python scripts/public/validators/validate_agent_task_discipline.py post experiment_run` after any experiment. If post-checks are incomplete, the agent fixes them before responding. The validator is the deterministic gate; AGENTS.md is the specification.

**Known limitation:** The session log is manually maintained by the agent. A dishonest agent can skip logging. The defense is the same as for any self-report system: the operator can audit `workspace/agent_session_log.jsonl` against actual repo state. The validator catches honest mistakes (forgot a step); it does not catch adversarial evasion.

---

## Primitive 7: Operator-Replay Mechanization

**Leg applied:** Compress (Leg 2) + Invert (Leg 1)
**Target:** The operator-agent research loop itself

**The move:** The fastest scientific progress often happens outside the formal validator: the operator notices a weak point, Codex/Claude writes a narrow script, the result changes the next discriminator, and only afterward does the durable engine learn from it. Standard failure mode: the insight remains trapped in chat, so ZTARE looks stale even though the surrounding operator-agent loop is advancing. Reflexive fix: replay the durable artifacts from that manual loop and ask whether the operator's next-test choice is recoverable without chat history. If yes, compile it into a typed `next_discriminator_queue.jsonl` proposal. If not, the artifact trail is incomplete.

**Instantiation:**
- Replay reader: `src/ztare/orchestrator/operator_replay_audit.py`
- Queue contract: `src/ztare/orchestrator/discriminator_queue.py`
- Primary artifact: `projects/<slug>/workspace/next_discriminator_queue.jsonl`
- Typical recovered moves: empty-box background gate, large-box boundary gate, tensor-rotation gate, background-debt ladder, dynamic-admissibility gate

**The discriminator:** Could a cold agent open the repo tomorrow and reconstruct the next decisive test without reading chat? If not, the loop has not mechanized the operator. The fix is not to ask the operator to remember harder; it is to improve artifact closure or add a replay template.

**Known limitation:** This is template-based, not taste-complete. It captures recurring discriminator shapes, not the final abductive act of choosing which scientific question matters most.

---

## Primitive 8: Research Taste Router

**Leg applied:** Compress (Leg 2)
**Target:** Principal preference and opportunity selection

**The move:** “Good next question” is not a scalar truth score. It mixes scientific importance, prize/money potential, architecture fit, self-recursive governance value, infrastructure fragility, and public-claim risk. Standard failure mode: the agent either treats all queued tests equally or smuggles its own academic preference surface into the decision. Reflexive fix: make the principal's taste configurable and score candidate next moves against that explicit profile before routing attention.

**Instantiation:**
- Profile: `org/preferences/principal.yaml`
- Scorer: `src/ztare/orchestrator/research_taste.py`
- Output: ranked opportunity cards with axis scores, penalties, and route labels (`pursue_now`, `queue`, `defer`)

**The discriminator:** If two candidate next moves are both scientifically valid, does the router explain why one better matches the principal's stated preferences? If it cannot, the choice remains manual and should be labeled as such.

**Known limitation:** Taste routing is an attention router, not a truth oracle and not an auto-dispatch license. A high taste score does not promote a claim; it only says the candidate is worth scarce attention.

---

## Primitive 9: Reflexive Forecast Market

**Leg applied:** Adversarial Disagreement + Compress + Invert
**Target:** ZTARE's own research allocation and tick-level action choices

**The move:** The apparatus prices its own proposed actions before execution,
records independent-agent forecasts, aggregates them into branch/effort priors,
then scores the outcome so future routing learns from the miss. The forecast is
not only a scorecard; its named failure modes can precondition the current
execution.

**What makes it reflexive:** The object being evaluated is the engine's own
next move: which branch to run, which failure mode to guard, how much effort to
spend, and when a forecast should change the action. The agentic implementation
is Pattern 12, but the inward application of disagreement/calibration to the
engine's own choices is the reflexive primitive.

**Instantiation:**
- Agentic implementation pattern: `docs/concepts/agentic_engineering_patterns.md`
  Pattern 12, Sealed Forecast Pool for Execution Control
- Seam/spec: `research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`
  and `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`
- Child seam where the apparatus's operational rules were empirically derived:
  `research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md`,
  with the per-finding evidence ledger in
  `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`
- Generated reflexive read model:
  `analytics/public/forecast_pool/market_state/reflexive_insights.json`
- Generated hygiene queue:
  `analytics/public/forecast_pool/market_state/maintenance_plan.json`
- Audit/validator: `scripts/public/analytics_shared/audit_forecast_pool_externalities.py`
  and `scripts/public/control/forecast/pool.py externalities`

**The discriminator:** Does a forecast change the engine's behavior before the
result is known, either by routing away from a weak branch, tightening an
artifact constraint, naming a failure mode the executor explicitly guards, or
triggering escalation to a different-family judge when the apparatus's own
tail-risk channel reports high worry? If forecasts only produce after-the-fact
Brier scores, the primitive is not doing reflexive work; if every escalation is
"flag for human review," the apparatus has not learned to use scored
disagreement on itself.

**Operational falsifier:** The primitive fails in practice if recurring audits
show that forecasts are not scored, resolved contracts leave stale transport
messages, forecast wakes do not produce aggregates or explicit no-update
statuses, macro/meso decisions omit causal forecast-use fields, the apparatus's
own forecasters can see each other's prior outputs (silently breaking the
independence Schoenegger-style aggregation depends on), or scored history stops
improving branch/effort routing across contexts.

**Known limitation:** This is a sealed, properly-scored decision market with
agentic transport. It is deliberately not a live LMSR/AMM or continuous price
tape; the market is used to precondition and calibrate research decisions, not
to create a tradable public asset.

---

## Closure: internal vs exogenous (gp168 v3 run-2 finding F4, 2026-05-02)

paper7 §11.6 established that **coordination closure** (when to stop
searching, what to fund next, when to abandon a branch) requires
*exogenous* resource pressure, bicameral architectures cannot decide
their own termination. A v3-run-2 iteration over-extended this to
"closure of any kind requires exogenous pressure" and was correctly
penalized by the judge. The over-extension is worth forestalling
explicitly.

**Internal closure (works without exogenous pressure):**

Technical-validation closures are checks whose stopping condition is internal to
the artifact. They do not need a budget, deadline, or principal to terminate.

- `validate_substrate_meta`, schema validation
- `validate_rubric.py`, rubric pre-flight
- Deterministic cage gates (R8, R9, R10, R11, ...)
- Lean cages, formal-proof termination
- R1 mutation_suite_guard, Python-importability guarantee
- Type-checks, lint, signature checks
- Cryptographic primitives (when present)

**Exogenous closure (needs principal / budget / deadline / mortality):**

Coordination closures, choices among epistemically-valid
alternatives. They cannot terminate from internal coherence alone
because no internal property distinguishes the "correct" answer.

- Choosing which Objective to fund next
- Deciding whether a paper is ready to publish
- Allocating principal attention across competing seams
- Deciding when a research direction is exhausted
- Promotion of a thesis from "passes gates" to "is a paper claim"

**Why this distinction matters operationally:**

Conflating the two creates two opposite mistakes. If "all closure needs
exogenous pressure," even schema validation becomes a management decision. If
"all closure can be internal," the system can deliberate forever over choices
that require taste, budget, or priority. The practical rule is: technical
validation closes internally; coordination closure requires an external
constraint. Schema validators do not ask the principal for permission; OKR
closure does.

---

## Where This Does NOT Belong

- **Not Epistemic Verification.** The treatise makes claims about the decomposition of epistemic verification. These primitives are engineering patterns. They are evidence that the decomposition is useful, not claims about the world.
- **Not the Operational Manual (pre-run checklist).** The manual is for run-time checks. These primitives are design-time decisions, they are made when building a new component of the engine, not when launching a run.
- **This document is the right home.** It is a companion to the architecture doc
  (what the engine is) and the constrained validation loop (how the engine
  separates model proposals from deterministic checks). The reflexive
  primitives are how the engine improves that loop.
