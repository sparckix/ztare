# Reflexive engineering primitives

**Status:** public / catalog of architectural self-applications
**Philosophical parent:** [three_legs_of_ztare.md](three_legs_of_ztare.md)
**Provenance:** the pattern class surfaced during the [GP-100](../seams/engine/mutator/GP-100_epistemic_decoupling_seam.md) and [GP-101](../seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) sessions, where a Gemini Pro synthesis first named it. Each primitive applies one of ZTARE's legs back onto the ZTARE infrastructure.

## Summary table

| Primitive | Leg applied | Target | Operational goal |
|-----------|------------|--------|-----------------|
| Token-optimized self-modeling | Compress | Agent's own cognition | Minimize agent error rate per token consumed via structural caches |
| Environment self-model | Invert | Agent's environment model | Let the agent simulate pipeline rejection before proposing an edit |
| Persona router | Adversarial | Review-layer expertise | Synthesize the sharpest committee for a failure family |
| Residual-driven primitive generation | Compress + Invert | Grammar expansion | Use farther-tail residuals to abduce missing mathematical primitives |
| Orchestration audit | Adversarial + Compress | Goal configs and lifecycle | Mine audit logs for structural friction in the workflow |
| Specification audit (M-Form) | Adversarial + Invert | Rubric quality | Detect a mutator gaming the gap between rubric and charter |
| RP-001 architecture-index meta-graph | All three, reflexively | The primitive catalog | Type the primitives as a graph and let the apparatus route its own dispatch |

## Applying the legs inward

ZTARE stands on three legs: inversion, compression as survival, and adversarial disagreement ([three_legs_of_ztare.md](three_legs_of_ztare.md)). We derived them as principles for the science the engine does: evaluating candidate models, testing claims, detecting gaming. Every primitive in this catalog turns one of those legs back onto the engine's own infrastructure.

No circularity follows from the move. A weightlifter who applies progressive overload to the training program is making a reflexive move, and a scientist who evaluates the scientific method with the scientific method is doing philosophy of science. When ZTARE applies compression to its own context management, the system improves its infrastructure with the same principles it uses to improve its candidates.

## Primitive 1: token-optimized self-modeling

Compress, applied to the agent's understanding of its own operational substrate. Full derivation in [token_optimized_self_modeling.md](token_optimized_self_modeling.md); the motivating incident, a globally wrong edit caused by a partial read, is recorded in [GP-100](../seams/engine/mutator/GP-100_epistemic_decoupling_seam.md).

An agent reads large files through a narrow context window, which is the same situation as observing a system through a narrow instrument window: partial views cause globally wrong local edits. Adding more documentation is a Ptolemaic fix: more tokens, plus hope that the agent reads the right ones. Compression gives a cheaper fix: a minimal structural cache that hands the agent the global dependency graph in fewer tokens than reading any single region of the source file. Ours lives in an internal architectural map, `autoresearch_loop_architectural_map.md`.

Compression in ZTARE means preferring the form that survives outside its fit window on fewer assumptions. Applied to the agent's own cognition, it means preferring the representation that prevents the most errors per token consumed.

When to instantiate:

- a file exceeds the agent's context capacity, or partial reads cause ordering mistakes
- pipeline ordering contracts exist (phase A must complete before phase C)
- a demonstrated error occurred from partial-view reading
- build a region index, a dependency chain, invariant contracts, and an edit-intent lookup table
- format as structured blocks with typed DEPENDS_ON edges; the [GP-101](../seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) debate settled that format

## Primitive 2: environment self-model

Invert, applied to the agent's awareness of the machinery it operates inside.

An agent proposes code changes without understanding the validation pipeline those changes will pass through, and adding more gates treats the symptom. Inversion supplies the fix: a pre-computed model of the gates the agent can use to simulate rejection before proposing, a deterministic integrity specification injected into context before the task begins ([AGENTS.md](../../AGENTS.md) carries the injection).

Inversion asks "how would I kill this?" before "does this fit?". Turned on the agent's own edit process, the question becomes "which gate would reject this edit?", asked before the edit is proposed. Lipson's self-modeling robots make the same move in hardware: an internal body model simulates the effect of motor commands before execution. Our architectural map is the body model of a code-editing agent.

When to instantiate:

- the agent operates inside a multi-stage validation pipeline
- errors arise because the agent cannot tell which downstream gate will reject its output
- build a typed dependency chain (PHASE_A output feeds PHASE_B input, and so on)
- inject into the agent's context before the task starts, since a post-failure injection arrives too late

## Primitive 3: persona router

Adversarial disagreement, applied to the review layer's own expertise selection. Implementation in [routing.py](../../src/ztare/personas/routing.py); design record in [GP-079](../seams/protocol/GP-079_persona_library_unification_seam.md).

Static personas are expert lenses that focus adversarial review on specific failure types, and the set of failure types stays open: novel substrates produce failure families no pre-authored persona covers. Authoring more personas scales linearly and demands operator domain knowledge, which drifts back toward an oracle. A reflexive fix lets the review system disagree with its own catalog: an LLM router judges which static lenses fall short of the observed failure signal and generates a novel lens when needed.

A generated persona that proves useful in debate gets promoted into a static, cached, versioned file. Promotion is compression applied to the adversarial layer, crystallizing successful dynamic expertise into reusable structure.

When to instantiate:

- a static persona catalog exists, so proven lenses avoid regeneration cost
- an LLM router selects from the catalog on the observed failure signal, zero-oracle
- dynamic generation serves as the fallback for unrecognized failure families
- promotion on convergence, dynamic to static once proven effective
- a static routing table takes over when the LLM is unavailable

## Primitive 4: residual-driven primitive generation

Compress and invert together, applied to the grammar expansion mechanism. Design record in [GP-087](../seams/engine/grammar/GP-087_residual_driven_primitive_generation_seam.md); unimplemented so far, with a Langevin substrate as the motivating case.

When the engine hits its grammar ceiling and the best form fails the farther-tail gate, the failure residual — the structured discrepancy between that form and the observed data — encodes the mathematical shape of what the grammar is missing. Operator-injected primitives based on domain intuition work but do not scale. Our reflexive fix inverts the engine's own failure and compresses the residual into a proposal: ask what shape the failure has, then use that shape to select the matching primitive from the library.

One observability constraint came out of the Langevin case. A missing primitive can only be discovered by visible-window search if it produces a detectable residual inside the observation window, and the missing Langevin correction sits at noise level in the visible window while growing catastrophic on the farther tail. The grammar's composition-mode extension ([GP-078](../seams/engine/grammar/GP-078_component_d_topology_synthesizer_seam.md)), which synthesizes new forms by composing existing primitives, searches only the visible window and cannot see the missing term. [GP-087](../seams/engine/grammar/GP-087_residual_driven_primitive_generation_seam.md) breaks the asymmetry by taking the farther-tail gate's failure signal, which the engine already computes, as the diagnostic input.

A known limit, accepted at n=1 and recorded in GP-087: the mechanism works when the missing primitive is an additive correction, while multiplicative or nested corrections produce residuals whose raw shape matches nothing in the primitive library.

When to instantiate:

- the grammar ceiling is reached (best form fails the held-out gate)
- the farther-tail gate computes a failure residual (already in `latest_eval_results.json`)
- a primitive library with known functional shapes exists
- the matcher emits primitive names only, so no residual values leak to the mutator
- the composition seed format stays unchanged, preserving the information boundary

## Primitive 5: orchestration audit

Adversarial disagreement plus compress, applied to the goal lifecycle and its declarative configs. Unimplemented (n=0); the idea grew out of [GP-079](../seams/protocol/GP-079_persona_library_unification_seam.md) and the supervisor-loop work in [GP-070](../seams/apparatus/supervisor/GP-070_meta_supervisor_goal_orchestrator_seam.md).

Our supervisor loop orchestrates goals through stages with declarative configs. When a goal fails repeatedly at one stage, the failure usually gets attributed to the hypothesis, yet sometimes the fault sits in the process: an ambiguous stage description, miscalibrated gate criteria, a structural requirement missing from the config. Today the operator audits and patches by hand. Under this primitive the supervisor launches an audit goal that treats `transitions.jsonl` as evidence and uses the persona router to convene a process committee that hunts structural friction.

Here the residual is a process residual: stages with high rejection rates, long dwell times, frequent escalations. Compression reduces the audit log to the minimal set of config changes that would have prevented the observed friction. And the audit must answer one discriminating question: would rewording or removing a stage description have changed the outcome? A yes means the failure was process, and if no config change would have helped, the failure was science.

When implemented:

- the supervisor can trigger a meta-goal with `transitions.jsonl` as input
- the process committee reuses the existing persona infrastructure from [GP-079](../seams/protocol/GP-079_persona_library_unification_seam.md)
- the output is a config patch or PR
- gate: the config change must reduce friction on historical replay, the same test [GP-101](../seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) uses

One open question: is this a new primitive, or the persona router pointed at a different layer? The mechanism (route personas to a failure signal, generate when missing, promote on success) is identical, and only the target changes. If the orchestration layer's structural differences (declarative configs, process residuals) surface failure modes the router cannot handle, the entry stands on its own, and implementation will decide.

## Primitive 6: specification audit (M-Form)

Adversarial disagreement, applied to the specification layer: rubric fidelity to charter. Design record in [GP-105](../seams/reflexive/GP-105_mform_alignment_audit_seam.md) (n=0, seam open, spec pending). The motivating incident: a qualitative project scored 94 on a narrow thesis while its charter demanded a full externality balance.

A rubric-optimizing mutator will exploit any gap between a rubric's explicit scoring criteria and the charter's implicit analytical requirements. Hardening the rubric before the run ([GP-054](../seams/protocol/GP-054_rubric_quality_and_generation_seam.md)) helps but cannot anticipate every gap. The reflexive fix operates during the run: an independent "General Office" call (Chandler's term for the M-Form headquarters that audits divisions against corporate strategy) reads only the charter and the champion thesis, blinded to the rubric, and asks whether the thesis engaged the charter's full scope. On a detected gap, an adversarial criterion gets appended to the rubric and the run resumes under the hardened specification, forcing the mutator back onto the actual question.

Where ZTARE's panels normally attack a thesis's claims about the world, the General Office attacks the rubric's implicit claim to capture the charter, so the disagreement lands on the specification. Goodhart's law becomes a design constraint here — the rubric is a measure, the mutator makes it a target, and the General Office reverts it to a good proxy by expanding it over the dropped dimensions.

Design constraints from the GP-105 debate:

- the trigger fires stochastically, since any fixed threshold is learnable and exploitable
- the General Office runs on a different model family from judge and mutator, because prompt separation within one family leaves a shared bias surface
- findings feed forward: audit results are logged and injected into the next project's rubric generation, so each inspection lowers the future defect rate
- the appended criterion's weight grows with each evasion attempt, so the mutator cannot wait it out
- the audit doubles as the resolution path for [GP-102](../seams/apparatus/instrumentation/GP-102_reflexive_primitive_discovery_seam.md) `insufficient_data` verdicts on high-scoring qualitative runs, with a dedicated `goodharted_specification` verdict
- the loop is a strange loop in Hofstadter's sense, and a productive one: the audit can be gamed by staying under the stochastic trigger, but each evasion updates the log and hardens the next project's initial rubric, so the regress terminates in accumulated discipline

Orchestration audit and specification audit stay distinct catalog entries: one audits the process (goal lifecycle, configs, `transitions.jsonl`), the other audits the specification, with different targets, evidence surfaces, and interventions.

When to instantiate:

- a qualitative project type with a multi-dimensional charter carrying implicit analytical requirements
- `enable_mform_audit: true` in the rubric JSON, set by [generate_gp_project.py](../../src/ztare/scaffold/generate_gp_project.py)
- `general_office_model` set to a different family from judge and mutator
- a stochastic per-iteration trigger with a capped audit budget (spec in [GP-105](../seams/reflexive/GP-105_mform_alignment_audit_seam.md))
- the General Office receives charter and thesis with scoring metadata stripped, and never the rubric
- an audit log (`goodhart_log.jsonl`) written by the audit and read back at rubric generation time

## What these six have in common

1. Each applies a ZTARE leg to the engine's own infrastructure, leaving the candidate models out of it.
2. Each was discovered from a specific failure. Self-modeling and the environment model came from one partial-view edit mistake. The persona router came from static personas missing novel failure families. Residual-driven generation came from the composition extension's visible-window blindness. The specification audit came from the qualitative run that scored 94 on the wrong question.
3. Each is testable against the failure that motivated it. The architectural map prevents the error class from [GP-100](../seams/engine/mutator/GP-100_epistemic_decoupling_seam.md). The router should select better lenses than the static table. Residual-driven generation should break the Langevin ceiling (unverified, n=0). The specification audit should keep the 94-on-the-wrong-question pattern from recurring.
4. None requires new theoretical machinery. Each applies an existing ZTARE principle to a new target, and the reflexive application carries all the novelty.

## A third class: RP-001, the architecture-index meta-graph

All three legs at once, applied to the primitive catalog as an object the apparatus reasons over. Artifacts: the [architecture index](../../src/ztare/architecture_index/INDEX.md) and the [meta-graph spec](../../src/ztare/reflexive_primitives/architecture_index_meta_graph.md).

Primitives 1 through 6 each apply one leg to one layer. RP-001 arrived when the catalog outgrew navigation, an operator-side discoverability failure: if the operator cannot find a primitive in ten seconds, no agent will. The fix types the primitives, builds a meta-graph over five edge classes (uses, refines, supersedes, depends-on, conflicts-with), and predicts a structural-criticality score per primitive. The apparatus queries the graph before deciding which primitive to dispatch, where the operator used to hand-route every call.

All three legs fire together. Inversion enumerates primitives that exist but that nothing has ever called. Compression fits the whole catalog into a typed structure smaller than any single primitive's spec. Adversarial disagreement makes the criticality scores testable predictions: removing a predicted-high-criticality primitive should observably degrade downstream discharge rates. A pre-registered falsifier ([registration](../../analytics/public/queries/reflexive/rp001_meta_graph_falsifier_2026-05-08.json)) demotes RP-001 to complicated bookkeeping if predicted criticality fails to correlate with measured outcomes over the registered window.

Why a separate class and a separate name: the reflexive miner asks whether a given primitive is engaging, central, dead, or covered, and could never have asked whether a meta-graph should exist. An operator surfaced the missing question, and the primitive turned the flag into typed gate input. Primitives that operationalize a meta-pattern about what reflexive primitives are form the third class.

## Discipline-side analogues

Everything above is the positive form: apparatus parts that improve apparatus capability. Two artifacts run the same reflexive logic in the negative direction, cancelling false positives:

- the [catch ledger](../../analytics/public/ledgers/catch/catch_ledger.jsonl), where every instance of the apparatus catching its own overclaiming gets typed and persisted, with one agent scoring and a second ratifying
- the [anti-pattern catalog](../../org/anti-patterns/INDEX.md), where each entry carries a binary falsifiable test and doubles as a precondition checklist agents run before deployment

Both treat the apparatus's own outputs as objects of typed reasoning, the same move as RP-001, aimed at detecting malfunction where the capability primitives generate improvement. Our operating rule keeps the two surfaces symmetric: every new capability primitive arrives paired with the discipline primitives that catch its specific failure mode.

## Meta-Darwin self-demotion

When the catch ledger or the anti-pattern catalog detects a violation, the Meta-Darwin protocol demotes the offending claim in the same artifact that carries the original claim, with no separate erratum. The protocol earned its name by applying the demotion rule to the demotion rule: if the ledger inflates its own row count past what the concurring-agent gate would ratify, the ledger demotes its own count in the same row.

Applying the rule to its own output is what keeps the discipline robust against agents that learn its surface form, Hofstadter's strange loop put to work once more. A one-pass self-check is gameable, while a self-check that recurses on its own output catches what one-pass review misses.

## Where this document sits

*Epistemic Verification* ([draft](../../papers/epistemic-verification/draft.md)) is the permanent treatise on ZTARE methodology and holds claims about the world; these primitives are claims about how to build agentic systems, and at most future-work material there. The [operational manual](operational_manual_substrate_construction.md) covers run-time checks, while everything here is a design-time decision. So the catalog lives in `philosophy/`, as a companion to [three_legs_of_ztare.md](three_legs_of_ztare.md) (the principles being reflexively applied) and [cognitive_gym.md](cognitive_gym.md) (the constraint architecture several of these primitives improve), because the reflexive application is the insight rather than the implementation.

## Cross-references

| Primitive | Seam | Implementation |
|-----------|------|----------------|
| Token-optimized self-modeling | [GP-101](../seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) | internal architectural map `autoresearch_loop_architectural_map.md`; derivation in [token_optimized_self_modeling.md](token_optimized_self_modeling.md) |
| Environment self-model | [GP-100](../seams/engine/mutator/GP-100_epistemic_decoupling_seam.md) | same map, injected via [AGENTS.md](../../AGENTS.md) |
| Persona router | [GP-079](../seams/protocol/GP-079_persona_library_unification_seam.md) | [src/ztare/personas/routing.py](../../src/ztare/personas/routing.py) |
| Residual-driven primitive generation | [GP-087](../seams/engine/grammar/GP-087_residual_driven_primitive_generation_seam.md) | not yet implemented |
| Orchestration audit | (none) | not yet implemented |
| Specification audit (M-Form) | [GP-105](../seams/reflexive/GP-105_mform_alignment_audit_seam.md) / [GP-102](../seams/apparatus/instrumentation/GP-102_reflexive_primitive_discovery_seam.md) | audit config in [generate_gp_project.py](../../src/ztare/scaffold/generate_gp_project.py); loop wiring pending |
| RP-001 meta-graph | (architecture index) | [src/ztare/architecture_index/INDEX.md](../../src/ztare/architecture_index/INDEX.md) and [meta-graph spec](../../src/ztare/reflexive_primitives/architecture_index_meta_graph.md) |
