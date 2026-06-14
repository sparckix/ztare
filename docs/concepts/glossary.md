---
description: "Plain-English definitions for every ZTARE term that matters."
---
# ZTARE Glossary

> **Up:** [Documentation map](../README.md)

> **Last revised:** 2026-05-31. The canonical principle set is [epistemic_principles.md](epistemic_principles.md) (P1-P16); this glossary surfaces only the plain-language terms.

Plain-English definitions for every term that matters. If a term isn't here, it's either standard (Google it) or jargon inflation that should be removed.

---

## Core Concepts

**GP-NNN (project / seam tracking ID)**
A numbered identifier the repository uses to tag a project, a seam (a design contract), a primitive, or a sealed result — *not* a part of any public API. The convention is read-only for outside readers: an entry such as "[GP-225](../../research_areas/seams/engine/lean/GP-225_gnn_lemma_relevance_ranker_seam.md) (LeanMill)" is a pointer into the internal ledger, not a commitment about an interface. The mapping from GP-NNN to artifacts is maintained in `docs/internal/repo_audits/gp_index.md`. Recurring examples a public reader will encounter: [GP-191](../../research_areas/seams/engine/GP-191_typed_cold_shot_portfolio_seam.md) (cognitive-firm kernel overlay), [GP-225](../../research_areas/seams/engine/lean/GP-225_gnn_lemma_relevance_ranker_seam.md) (LeanMill / GNN lemma-relevance work), [GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md) (forecast pool), [GP-233](../../research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md) (research-yield decomposition seam), [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md) (commit-membrane daemon), [GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md) (action intelligence).

**ZTARE (Zero-Trust Adversarial Reasoning Engine)**
A system that stress-tests claims by having one AI propose an answer and another AI attack it, with hard numeric checks that neither can override. Think of it as an independent audit for any claim, the same idea as hiring an auditor who doesn't work for the company being audited.

**Model-Environment Thesis**
The core intuition behind ZTARE, also called the *nurture thesis*: model
capability is talent, but research quality depends on the environment around
that talent. Task framing, evidence boundaries, role separation, source
readiness, falsifiers, durable memory, and demotion rules decide whether a
strong model produces auditable work or persuasive overclaim. The slogan form is
"scale the environment, not the model."

**Leaf (swappable model)**
The frozen frontier model inside the apparatus (Claude, GPT, or Gemini). It is
interchangeable: a stronger model plugs in as a new leaf under the same
governance, so the discipline carries over rather than being rebuilt.

**Constrained Validation Loop**
The in-loop validation stack around the model. It lets the model propose
structures such as functional forms and analogies, while deterministic
machinery owns fitting, holdouts, gates, and evidence-bearing verdicts.
The historical document filename is [cognitive_gym.md](cognitive_gym.md).

**Mutator**
The AI that proposes answers. It writes a thesis (the argument) and a test suite (code that checks the argument against data). Named "mutator" because each iteration mutates/improves the previous answer.

**Verification Panel**
Three adversarial AI agents that attack the mutator's answer. They look for the weakest assumption and write counter-tests. Named for the obvious reason, they're trying to kill the thesis.

**Meta-Judge**
The AI that scores the result. It only looks at what the code produced when it ran, never the prose. This prevents the mutator from writing a convincing essay that hides a wrong answer.

**Champion**
The current best answer. When a new iteration scores higher than the champion, it gets promoted. Think of it as "the leading candidate."

**Iteration**
One cycle of: mutator proposes → verification panel evaluates → judge scores → best answer kept. A typical run does 10-100 iterations.

---

## Evidence & Data

**Evidence (evidence.txt)**
The data the AI is allowed to see. This is the bounded input, everything the mutator and judge work from. It's a snapshot, not a live feed.

**Hidden Holdout**
Data points the mutator never sees. Used to check if the answer actually generalizes vs. just memorizing the visible data. Standard machine learning practice, like a teacher keeping some exam questions secret.

**Visible Slice / Hidden Slice**
The split between data the mutator can see (visible, typically 75%) and data reserved for checking (hidden, typically 25%).

**Workspace**
The persistent memory layer where source material accumulates over time. Think of it as a research folder that grows as you add documents. The validator never trusts it directly, it only sees the bounded evidence snapshot extracted from it.

**Human Operator / Principal**
The accountable person operating or directing the research system. Owns taste,
strategic direction, public-claim approval, budget/risk acceptance, and final
authority when evidence does not decide the question.

**Agentic Operator**
A tool-using AI agent operating inside the workbench, such as Codex, Claude
Code, or a role-bound Research Director. It can inspect files, run probes,
edit artifacts, repair proofs, and leave receipts. It can execute or recommend
within mandate, but it is not the final accountability holder for public claims
unless the repo explicitly delegates a narrow decision.

**Evidence Atlas**
The reviewer-facing evidence map at [../evidence_atlas/README.md](../evidence_atlas/README.md).
It does not create new claims; it links public claims, project summaries,
patterns, primitives, runnable checks, evidence packets, non-claims, and
caveats.

**Evidence Level (L0-L5)**
The atlas confidence shorthand for how much support a claim or primitive has:
L0 = named only; L1 = implemented artifact exists; L2 = linked to an
experiment, project, or stored result; L3 = changed a public claim, next
action, demotion, or routing decision; L4 = controlled, ablated, baselined, or
benchmark-compared; L5 = externally checked by a second lab, outside expert,
upstream adoption, or peer review. Most strong current ZTARE claims sit in
L2-L4. L5 is intentionally rare.

**LeanMill Proof-Audit L1/L2/L3**
Different from the atlas evidence levels. In the LeanMill/APN audit packet,
L1/L2/L3 refer to proof-audit layers: kernel cleanliness, allowlisted axioms,
and top-level anti-laundering checks. A proof can be "L3-clean" in that local
audit sense without being atlas-evidence-level L3 or L4.

**Evidence Packet**
A short reviewer-facing packet assembled from existing public artifacts. A
good packet states the scoped claim, evidence level, primary sources, runnable
anchors, non-claims, confusers, falsifiers, and external-readiness status. In
this repo, retrospective packets live under `docs/evidence_atlas/packets/`.

**Claim Card**
A curated atlas entry for a high-signal claim family. Claim cards are index
routes, not proof by themselves; they point to source artifacts, evidence
levels, commands, non-claims, and next falsifiers.

**Public Claim Register**
The canonical public claim-status page at [../public_claim_register.md](../public_claim_register.md).
It says what the repo is willing to claim publicly, what it refuses to claim,
what evidence exists, and what would change the claim.

**Public Claim Summary (`public/CLAIM_SUMMARY.md`)**
The project-level public surface for a campaign. It summarizes the claim,
status, evidence, retest tags, caveats, and non-claims without exposing private
or sealed working material.

**Non-Claim**
An explicit boundary around what the evidence does not establish. Non-claims
are part of the evidence surface, not legal boilerplate; they prevent a scoped
result from being read as a broader result.

**Next Falsifier**
The cheapest or clearest test that would change the current interpretation.
Good claim surfaces name the next falsifier so the reader knows what evidence
would promote, demote, or kill the claim.

**Retest Tag**
A status label saying how much re-checking a finding has survived: for example
original-run-only, cross-corpus replicated, benchmarked, demoted, or externally
checked. Retest tags help prevent a one-off result from reading like a stable
law.

---

## Scoring & Gates

**Hard Gates (formally: Deterministic Charter Gates, [GP-030](../../research_areas/seams/engine/mutator/GP-030_deterministic_charter_gate_seam.md))**
Numeric pass/fail tests that no AI judge can override. Example: "the model's prediction must be within 5% of the actual data on the hidden points." If a hard gate fails, the score is capped at 50 regardless of how good the prose looks. This prevents the judge from rationalizing a wrong answer into a high score.

**Rubric**
A JSON file that defines what "good" looks like for a specific project. Contains scoring criteria, the AI persona, and feature flags. Think of it as the grading rubric for an exam.

**Score Regime**
The scoring context, which evidence, rubric, and model combination produced a score. When the evidence changes, old scores become incomparable (like changing the exam and comparing grades). The system detects this automatically.

**Stagnation**
When the score stops improving across iterations. After 3 stagnant iterations, the system changes strategy (rotates the attack angle). After sustained stagnation, it may reset the approach entirely.

---

## Research Process

**Seam**
An open investigation or problem being tracked. Contains the problem description, debate turns between Claude and Codex, and status. Think of it as an issue tracker entry with a built-in debate log.

**Bounded Discriminator (formally: Bounded-Discriminator Mode)**
A "show your work" mode where the AI must: (1) break the problem into distinct regimes, (2) name a specific rival explanation, (3) point to a numeric feature in the data that distinguishes its answer from the rival, and (4) cite actual numbers from the evidence. Prevents hand-wavy arguments that sound good but aren't testable.

**Ontology Trap**
When the AI recognizes what the data is (e.g., "this looks like Planck radiation") and imports the known formula instead of deriving it from the data. Named "trap" because it looks like success, the formula fits perfectly, but the AI cheated by recognizing the pattern rather than discovering it. This is a specific form of data contamination.

**Fit Primitive ([GP-035](../../research_areas/seams/engine/grammar/GP-035_mutator_missing_fit_primitive_seam.md))**
A tool that lets the AI propose the shape of an equation, then uses a numerical optimizer (scipy) to find the best parameters. Without this, the AI has to guess the numbers, which it's bad at. With this, the AI proposes structure and the computer finds the numbers. Like giving a student a calculator after they set up the equation.

**Findings Track**
A ledger of patterns discovered during actual runs (not planned in advance). Each finding needs to be observed at least twice (the "two-strike rule") before it's promoted to active status. This prevents over-reacting to one-off flukes.

**Two-Strike Rule (formally: Findings-Track Invariant)**
A pattern must be observed in at least two independent contexts before the project acts on it. Exception: a controlled experiment designed to produce the second observation counts.

**Recursive Self-Improvement**
Turning repeated ZTARE failures into reusable machinery: tests, gates, source
contracts, anti-patterns, preconditioners, or explicit non-goals. A vivid
one-off failure is not enough; promotion needs a repeated failure class or a
controlled verifier.

**Organizational Learning**
The repo-level memory system that helps ZTARE allocate attention better over
time: forecast records, yield decomposition, experiment rows, catch rows,
action-impact records, and intelligence read models. It is a source-backed
record of what changed in the project's behavior in response to a recorded
finding, not just accumulated documentation.

---

## Loop Control

**Structural Pivot / Strategy Rotation**
When the AI is stuck, the system changes the attack angle. Different project types get different rotation strategies. The goal is to avoid grinding the same failed approach. Some telemetry still uses the historical `topological_pivot` key for compatibility.

**Underidentified**
When the loop runs out of iterations without finding a satisfactory answer. The system stops and says "I couldn't solve this with the current evidence and approach" rather than pretending to have an answer.

**Early Stop**
Stopping the loop before the full iteration budget if the answer is already good enough (all gates pass, score is high, minimum iterations completed).

---

## Architecture

**Validator**
The adversarial engine itself, the mutator/verification-panel/judge loop. Stateless: every run starts fresh from the evidence snapshot.

**Supervisor**
The work-management layer for improvement programs. Routes tasks, tracks progress, enforces budgets. Does NOT decide truth, that's the validator's job.

**Kernel**
The core evaluator code being improved. When we say "kernel hardening," we mean making the scoring and evaluation more resistant to gaming.

**Discovery Kernel**
The full scientific-discovery engine: validator, rubrics, substrate contracts,
fit primitives, gates, proof bridges, and anti-Goodhart machinery. It is the
part of ZTARE that pressure-tests hypotheses and returns a bounded verdict.

**leanmill**
The governed Lean proof-search subsystem (`src/ztare/leanmill/`). Swappable
agent "leaves" propose proofs; one governance kernel decides whether a proof
counts as a closure. It owns a work queue, an event log, and the space of moves
the solver searches over.

**Exogenous move**
A solver step that brings in a result computed outside the language model — for
example a witness found by symbolic computation — and hands it to the proof. The
Lean kernel still verifies the finished proof, so the outside computation can
suggest a step but never certify it.

**Target-conditioned move router**
A selector that reads the goal's structure and the last failure signal and
promotes the move most likely to apply, so a useful move is tried first instead
of after the budget is already spent.

**Hard Problem Campaign**
A bounded research campaign on a difficult substrate, such as Navier-Stokes,
neural scaling, modified gravity, theorem/prover work, or successor
architecture search. A campaign is allowed to fail if it leaves a clearer
residual, source-design target, falsifier, or scoped claim.

---

## Project Types

**Sandbox**
A controlled test environment with synthetic (fake) data. Used to test whether a tool works before using it on real problems. The data is generated from a known formula, so we can check if the AI discovers the right answer.

**Substrate Swap**
Testing a tool on a completely different type of problem to separate "the tool works" from "we got lucky on this specific problem."

**Pre-Registration**
A document written BEFORE running an experiment that specifies: what we'll test, how we'll run it, what counts as success/failure, and the exact commands. Prevents moving the goalposts after seeing the results. Borrowed from scientific practice.

---

## Artifacts

**Thesis (thesis.md)**
The current best argument/answer for a project. Written by the mutator, evaluated by the verification panel, scored by the judge.

**Test Model (test_model.py)**
Code that implements the thesis's claims in a testable way. For curve-fitting projects: a Python function that takes inputs and returns predictions. The gates evaluate this against hidden data.

**Post-Mortem**
A correction document created when something goes wrong. Sealed artifacts (scoring sheets, pre-registrations) are never edited, corrections go in post-mortems instead.

**Scoring Sheet**
A sealed record of what was believed at the end of a run. Immutable, never edited after the run. If the conclusions change, the correction goes in a post-mortem.

---

## Supervisor Sub-Layers

**OS Layer**
The state machine driver inside the supervisor. Owns hard gates and state transitions (A1 → A2 → B → C → D). No agent can bypass an OS-level gate.

**Config Layer**
Typed goal-lifecycle contracts that sit between the OS state machine and the agent runtime. The goal orchestrator ([GP-070](../../research_areas/seams/apparatus/supervisor/GP-070_meta_supervisor_goal_orchestrator_seam.md)) lives here, it tracks active goals, defines their stages, and routes advancement commands.

**App Layer**
The agent runtime that operates within the fences set by OS and Config. Agents read staged requests, produce artifacts, and submit them back through the supervisor's commit path.

**Goal Orchestrator (GP-070)**
A Config-layer component that tracks active goals in `AGENTS.md` and advances them through typed lifecycle stages via `python -m src.ztare.orchestration.cli advance <goal_id>`.

---

## Governance Concepts

**M-Form (Multi-Divisional Form)**
The organizational structure borrowed from Chandler/Williamson applied to AI governance. In ZTARE, Division A generates and Division B verifies, with structural separation enforced by the supervisor. See *Cognitive Firm*.

**Division A / Division B**
The two structural divisions in the M-Form. Division A is the generation side (mutator, workspace, synthesis). Division B is the verification side (verification panel, judge, hard gates). The governance claim is that they must not share a gradient.

**Closure / Ratification**
In leanmill, a proof counts as a *closure* only after governance *ratifies* it: the Lean kernel compiles the proof, its axioms are on an allowlist, a matched negative control fails (so the gate is not trivially passable), and a statement-integrity check confirms the proved statement is the one that was asked. The agent that proposed the proof never ratifies its own work.

**Composite ratification**
Assembling a proof of a parent goal from sub-lemmas proved independently. The assembled chain is re-checked by the kernel and rejected unless every sub-lemma is used, none of them merely restates the goal, and the chain type-checks — which blocks the circular or vacuous "decompositions" that would otherwise manufacture a false closure.

**Anti-laundering kernel (governance kernel)**
The single deterministic gate that ratifies closures. "Laundering" is when a proof compiles but does not actually establish the claim — citing the target, assuming the conclusion, or exploiting a vacuous hypothesis. A clean compile is necessary but not sufficient; this kernel exists to catch the rest.

**Subliminal Learning**
A training-time phenomenon (Cloud et al. 2026, Nature 652) where models sharing base initialization transmit behavioral traits through semantically unrelated data during fine-tuning. Distinct from steganography, the signal is not human-readable. Operates during gradient descent, not during inference-time in-context reading.

---

## Evidence Pipeline

**Source Type Map (source_type_map.json)**
A JSON file in a project's `raw/` directory that maps filenames to source types (e.g., `source_evidence`, `source_counter`). Used by `compile_evidence.py` as a fallback for raw files that lack frontmatter, so sources can be typed without modifying their content.

---

## Science Track (Asymptotic Discovery)

**Compression Primitive ([GP-103](../../research_areas/seams/engine/GP-103_topology_induction_gap.md))**
A template enumeration engine that strips overparameterized surrogates to their minimal gate-passing form. Stage 1 tests 22 additive templates (combinations of sqrt, log, power, exp, 1/n). Stage 2 tests 13 depth-1 compositional templates (sqrt(n/log(n)), etc.). Selection by BIC. No LLM in the loop. The compression primitive is the core of `make discover` Phase 2.

**Farther-Tail Holdout**
Data points beyond both the visible and holdout windows. Tests extrapolation, not interpolation. The key instrument for catching finite-window parameter overfitting (e.g., a free exponent of 0.562 vs the true 0.500).

**Gate Normalization**
Dividing residuals by the maximum observable magnitude before testing against a threshold. Prevents large-scale observables (z values in the hundreds) from failing gates designed for unit-scale data. Implemented in `src/ztare/gates/residual_norm.py`.

**Exponent Grid**
A discrete set of candidate exponents {0.25, 1/3, 0.5, 2/3, 1.0, 1.5, 2.0} used when fitting power-law terms. Free continuous exponents overfit in finite windows. The grid constrains the fit; BIC selects among grid values.

**PSLQ Bridge**
Maps fitted floating-point parameters to exact mathematical constants using the PSLQ integer relation algorithm (via `mpmath.identify()`) and a curated constant library (pi, sqrt(2), euler_gamma, etc.). Transforms a numerical regression into a falsifiable mathematical conjecture.

**Rival Exclusion Test**
A post-discovery closure test that fits alternative functional forms (the "rivals" flagged by the judge's weakest-point feedback) against the same evidence and gates. If all rivals fail, the judge's concern is closed. Part of Phase 2.5 ([GP-111](../../research_areas/seams/engine/diagnostics/GP-111_proactive_closure_seam.md)).

**UNDERIDENTIFIED**
The correct output when no template in the library passes the holdout gates. Means the template library cannot express the target's asymptotic form. This is a finding, not a failure. The Ulam density result (A002858) is the canonical example.

**Statistical Fingerprint ([GP-110](../../research_areas/seams/engine/diagnostics/GP-110_statistical_fingerprint_seam.md))**
A characterization of sequences that resist closed-form compression. Measures spectral slope, Hurst exponent (via DFA), phase linearity (via Hilbert transform), and amplitude envelope. Used for UNDERIDENTIFIED sequences.

**Lean Proof Stubs**
Lean 4 files generated by `lean_compiler.py` from ZTARE gate results. Gate passes become `#eval` checks on `Float` bounds (sorry-free, decidable). Gate failures become exclusion witnesses. PSLQ identifications become named axiom conjectures.

---

## Extraction Components

**Structural-Presence Extractor ([GP-061](../../research_areas/seams/apparatus/supervisor/GP-061_R4_retrospective_audit.md))**
Extracts structural constraints from failed candidate families by computing feature-bag intersections across iterations. Lives in `src/ztare/validator/`.

**Negative-Space Extractor ([GP-061](../../research_areas/seams/apparatus/supervisor/GP-061_R4_retrospective_audit.md))**
Detects void operators, mathematical operations absent from all tried candidate families. Identifies what the search space has systematically avoided, which may indicate structural gaps in the mutator's exploration.

---

## Epistemic Supervision Principles (glossary-surfaced subset)

The full set is P1-P16 in [epistemic_principles.md](epistemic_principles.md) (the canonical owner). Only the two terms most often used as standalone vocabulary are restated here.

**Enforcement Completeness (P13)**
The principle that an enforcement surface must cover every branch of every conditional it touches. A deterministic enforcement floor with a gap on one branch is structurally equivalent to no enforcement on that branch. Added after [GP-080](../../research_areas/seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) postmortem (2026-04-17). See [epistemic_principles.md](epistemic_principles.md).

**Downstream Symptom Chasing (P14)**
The anti-pattern of fixing downstream effects of a root cause across multiple sessions without tracing upstream to the root. Diagnostic: if three fixes at three layers don't resolve the same error, the root cause is in the part of the path no fix has touched. Added after GP-080 postmortem (2026-04-17). See [epistemic_principles.md](epistemic_principles.md).

---

## Org Runtime And 2026 Vocabulary

Terms from the org-runtime and post-[GP-128](../../research_areas/seams/mission/org/GP-128_persistent_manager_agent_seam.md) arc, the part of the project the older sections above predate.

**Cognitive-Firm Kernel / Tenant Overlay ([GP-191](../../research_areas/seams/engine/GP-191_typed_cold_shot_portfolio_seam.md))**
The substrate-agnostic governance kernel is the separate public repo `cognitive-firm`. This repo carries only a thin *tenant overlay* of it; a fresh public clone here runs kernel-only. The overlay is the project-specific configuration on top of the shared kernel.

**Commit-Membrane Daemon ([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md))**
An epistemic-verificator daemon that is the sole writer of the official store (the experiment record and ledgers). The agent cannot hand-edit official state; it submits a proposal and the daemon stamps or quarantines it. A hand-written record is non-authoritative by construction.

**Post-Tick Gate (`post_tick_check.py`)**
The fail-closed close-out gate any agent must run before declaring a tick or run closed. Hard-fails on unresolved prediction-ledger debt, unclosed contracts, or a decision-change with no evidence-ledger update.

**Structural-Anchor Registry / `residual_target`**
The substrate-agnostic amnesia defense (GP-238). Each substrate declares a small registry of its route-invariant residual targets; every tick must name which target it addresses via a blocking `residual_target` field. Human-declared and derivation-adjudicated, not a similarity model. The NS `ns_residual_manifest` is the reference instance.

**Reflexive Primitive**
A capability the apparatus runs on its own infrastructure (the audit that demoted the project's own measurement instrument is one). Catalogued in [reflexive_engineering.md](reflexive_engineering.md).

**Forecast Pool ([GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md))**
A sealed primitive that records macro/meso/micro branch choices as forecast contracts with ex-post scoring, so routing decisions are calibrated rather than asserted.

**Mandate / Role Daemon / Transition Log / Damage Signal**
The org-runtime primitives: a *mandate* is a role's standing authority and scope; a *role daemon* is the persistent process that claims tasks under it; the *transition log* is the append-only record of state changes; a *damage signal* is a typed alert a role emits on failure. State is files under `org/`.

**Meta-Darwin**
An adversarial self-review move: take a just-produced claim and attack its own closing for laundering (a sound narrow kill reframed as a foreclosing universal) before trusting it.

**Cold Cross-Provider Pass**
A self-serve check that dispatches a consequential architecture or closure question to an independent external model at high reasoning effort, then splits the verdict and Meta-Darwins its closing. Defends against single-author monoculture.

**Canonical-Owner Convention**
The documentation rule that each overlapping topic has one canonical owner doc; sibling docs carry a short relation block pointing to it instead of re-deriving the content. Keeps the concept tree mutually exclusive and collectively exhaustive.
