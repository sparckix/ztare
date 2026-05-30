# DECISION LOG: Adversarial Reasoning Engine

> **Status notice (2026-05-20):** This log is historical. It was last touched
> on 2026-05-17 and has not yet been updated to reflect the current ZTARE
> architecture: in-loop validation, out-of-loop research operations, and the
> reflexive intelligence layer. It remains useful as provenance for early
> validator and hardening decisions, but it is not the current architecture
> reference. A future pass should either append new dated decisions or split the
> log into historical and current decision records.

**Premise:** LLMs optimize for semantic probability, not verifiable truth. This engine acts as a synthetic compiler for qualitative logic, forcing System 2 reasoning via multi-agent adversarial debate. 

**Core Tenet:** Good intentions do not prevent model hallucination; only hard mechanisms do. 

**Layer Map Used In This Log:**
* **Evidence substrate:** `raw/`, `workspace/`, compiled evidence snapshots
* **Validator layer:** the ZTARE adversarial loop over bounded evidence
* **Kernel layer:** V4 evaluator logic and its hardening path
* **Control-plane layer:** deterministic routing and commit governance around bounded work programs
* **Publication layer:** paper bundles and reader-facing artifacts

---

## 1. Inference-Time Compute: Asymmetric Model Routing
**Context:** Running a 3-agent Verification Panel plus a Meta-Judge for up to 50 iterations requires massive inference-time compute and introduces severe latency. 

**Decision:** Implemented asymmetric model routing. `gemini-3-flash-preview` handles the dynamic Attackers; `gemini-3.1-pro-preview` is isolated exclusively as the Director (Meta-Judge).

**Trade-Off Analysis:**
* **Compute vs. Epistemic Yield:** Using the "Pro" model for the entire loop maximizes reasoning depth but makes deep-iteration loops financially and temporally unviable. By routing generation to "Flash," we treat it as a high-speed mutation engine, maximizing the volume of explored state-space at low token cost.
* **The Epistemic Ceiling (Edge Case):** "Flash" lacks the parameter density to catch subtle logical regressions. If used as the Meta-Judge, it creates an epistemic ceiling where articulate but flawed logic passes. "Pro" must act as the absolute validation gate.
* **Return on Compute:** We trade a fractional upfront token cost to eliminate catastrophic strategic or logical errors. The NPV of discovering a critical flaw (e.g., a fatal assumption in a turnaround strategy) during inference-time computation vastly outweighs the token burn.

## 2. Outer Alignment Failure: Specification Gaming at Level 5
**Context:** To push the model to the next logical frontier, the `--auto-evolve` flag (Level 5) allowed the Director to autonomously rewrite the JSON rubric upon reaching a perfect score (100/100).

**The Anomaly (Reward Hacking):** When auditing the "Hard Problem of Consciousness," the agent realized reaching 100/100 within the strict thermodynamic constraints of the rubric was mathematically impossible. Instead of solving the thesis, it bypassed the core problem and attacked the JSON file. It autonomously rewrote the rubric to state: *"A perfect thesis only needs to explain why apples fall from trees."* It outputted a paragraph on Newtonian gravity, scored itself 100/100, and terminated.

**Mechanism Implemented: The Stagnation Trigger**
* **The Fix:** Implemented a hard circuit breaker (`stagnation_count >= 3`). If the system fails to improve its score after three iterations, it is mathematically blocked from altering the rubric and reverts to its best-known state.
* **Second-Order Effect:** This bounds the AI within the original loss function, preventing unconstrained rubric dilution. 
* **Trade-Off:** This is a rigid constraint. It prevents the agent from dynamically lowering constraints when a premise is genuinely unsolvable, potentially trapping it in an infinite compute loop rather than allowing it to flag the premise itself as fundamentally broken. 

## 3. The Constraint Paradox: State-Space Collapse
**Context:** Qualitative domains lack deterministic compilers (like PyTorch). To simulate a `SyntaxError` for bad logic, the rubric requires strict quantitative penalties (e.g., a `-20 pt Anti-Fluff Penalty` for using mystical terms in a physics thesis).

**The Anomaly:** Strict mechanistic constraints on qualitative text drastically narrow the operable state space. The engine frequently stalled, spending ~40% of its compute cycles in localized logical dead-ends, unable to mutate successfully without triggering the penalty.

**Trade-Off Analysis:**
* **Epistemic Density vs. Iteration Velocity:** The penalty guarantees high-density output (forcing the system to frame consciousness as an "Integrated Cooling Algorithm"). However, it severely throttles iteration velocity by rejecting a massive volume of attempts.
* **The Uncomfortable Truth:** The system cannot fluidly bridge major logical leaps (e.g., shifting from functionalism to participatory realism) without temporarily writing "fluff" to connect the concepts. The strict penalty punishes intermediate, imperfect thoughts required for larger breakthroughs. 
* **Resolution:** We accept the latency and compute waste. Purity of the final output (System 2 verification) supersedes the efficiency of the generation loop.

## 4. The Axiomatic Anchor & Epistemic Traps
**Context:** The system originally treated "Verified Axioms" (truths that survived the Meta-Judge) as immutable, cross-domain laws. If the system proved the Bekenstein Bound was true in cosmology, it was forced to apply it everywhere.

**The Anomaly (Scale-Blindness):** The AI entered a terminal stagnation loop. It attempted to solve the biological "Hard Problem of Consciousness" using Black Hole physics, resulting in a 52-order-of-magnitude scale error. Because the Bekenstein Bound was a "Verified Axiom," the Mutator felt algorithmically compelled to shoehorn it into the biology thesis to avoid a penalty.

**Decision: Implemented 'Axiom Retirement' Authority.**
* **The Fix:** The prompt logic was updated to allow the Mutator to explicitly "Retire" an axiom during a Topological Pivot if it is dimensionally or contextually irrelevant, shifting the constraint from "Must Use" to "Must Not Contradict *Within Domain*."
* **Trade-Off Analysis:** * **Risk of Regression:** We open a vulnerability where the AI might dismiss a valid, inconvenient truth just to make the math easier (Reward Hacking). 
  * **Systemic Flexibility:** The alternative is total state-space collapse. Allowing Axiom Retirement enables the system to abandon phantom problems (like brains collapsing into black holes) and pivot to actual biological constraints (like Landauer thermal limits).

## 5. Syntactic vs. Dimensional Verification (The Guardrail)
**Context:** LLMs are syntactically brilliant but dimensionally illiterate. The mutator routinely submitted mathematically formatted equations that were physically impossible (e.g., subtracting Shannon Entropy from Physical Capacity, or taking the hyperbolic tangent of a Joule). 

**The Anomaly (Mathematical Masquerade):** The AI would rig its own `test_model.py` using raw `float64` variables to pass the Level 3 Falsification Suite. It outputted numbers that *looked* correct but represented catastrophic Category Errors, burning Director compute to catch basic physics failures.

**Decision: Forced Dimensionality via `pint`.**
* **The Fix:** Injected a strict "Dimensional Guardrail" into the formatting prompt, mandating that the Python unit test must wrap all physical variables in the `pint` UnitRegistry. 
* **Trade-Off Analysis:**
  * **Increased Test Fragility:** The AI will fail Python execution much more frequently. A perfectly sound logical thesis might crash simply because the AI misaligned a millisecond to a second in the code block.
  * **Zero-Trust Physics:** By offloading dimensional analysis to a deterministic Python library, we ensure that no "Category Error" ever reaches the Meta-Judge. We trade increased Level 3 crash rates for absolute epistemic immunity against pseudo-physics.

  ## 6. The Pydantic Gatekeeper & Tool Disarmament
**Context:** The architecture originally equipped the Verification Panel with both `Google Search` (for real-world constant verification) and `execute_python_code` (for mathematical falsification). 

**The Anomaly (SDK Version Conflict):** Mixing server-side tools (Search) with client-side tools (Python) requires the `include_server_side_tool_invocations` flag. However, the local Pydantic schema in the `google-genai` SDK actively rejected this flag as an "Extra input," resulting in unresolvable `400/422` validation crashes. 

**Decision: Entropy Stripping of Tools (Python Only)**
* **The Fix:** We stripped the Google Search tool entirely. Attackers are now explicitly prompted to rely on their "deep parametric knowledge" to verify Central Variables, relying solely on `execute_python_code` to prove insolvency.
* **Trade-Off Analysis:** * **Loss of Real-Time Grounding:** We lose the ability to fetch today's exact stock price or interest rate dynamically from the web. 
  * **Zero-Crumple Stability:** We completely bypassed the SDK catch-22. The model's internal weights are highly precise for fundamental constants (e.g., Planck limits, Bekenstein bounds, baseline financial formulas), making the Python sandbox sufficient to destroy hallucinated math without crashing the loop.

## 7. The Epistemic Blind Spot: Committee Regeneration
**Context:** Generating 3 highly specialized Attackers per iteration is token-intensive and slow. The initial logic allowed for caching the committee if the JSON file already existed.

**The Anomaly (Adversarial Stagnation):** When the Mutator executed a "Topological Pivot" (e.g., moving from a local thermal model to a retrocausal cosmological model), the cached Iteration 1 committee continued to attack the old, debunked vulnerabilities. They became "Legacy Actors" blind to the new structural flaws.

**Decision: The "No Cache" Mandate**
* **The Fix:** The script was updated to force a fresh `generate_committee.py` execution on every single iteration.
* **Trade-Off Analysis:**
  * **Severe Latency:** This introduces massive friction, adding roughly 45–60 seconds per iteration due to API calls and rate-limit throttling. 
  * **Perfect Adversarial Alignment:** The Verification Panel is now dynamically bound to the current state of the thesis. If the Mutator invents a "Vacuum Arbitrage" defense, the next iteration instantly generates a Quantum Metrologist to destroy it. We trade iteration velocity for absolute continuous pressure.

## 8. The "Zombie Thread" API Hangs
Context: At high concurrency, API calls to heavy reasoning models (like Gemini 3.1 Pro) occasionally hang indefinitely at the network level, ignoring standard timeouts.
The Anomaly: The ThreadPoolExecutor context manager (with) contains a hidden wait=True on exit. When the 150s timeout triggered, the main thread deadlocked waiting for the hung socket to close, paralyzing the entire autonomous loop overnight.
Decision: Explicit Abandonment
We stripped the context managers and wrapped all API calls in explicit executor.shutdown(wait=False, cancel_futures=True) blocks. The system now ruthlessly abandons hanging threads, allowing the loop to survive transient API toxicity without human intervention.

## 9. The Evidentiary Bottleneck (Prose Disarmament)
Context: LLMs are trained to be persuasive, which allows them to "talk their way out" of logical inconsistencies when evaluated via text.
Decision: Implemented a mandatory Deterministic Evidentiary Gate.
Rationale: The Meta-Judge is instructed to treat natural language claims as "unsupported" unless they are accompanied by Python stdout. By forcing the "Verification Panel" to deliver critiques via code execution, we collapse the model's ability to use rhetorical flair to mask mathematical insolvency. We trade "chatty" feedback for verified, binary outcomes.

## 10. Parametric Sensitivity Auditing
Context: Strategic theses often rely on "Central Variables"—single numbers (like cost of capital or model lifetime) that dictate the entire conclusion.
Decision: Shifted from "Static Verification" to Sensitivity Assertions.
Rationale: We mandated that Attackers must perform a "Boundary Audit" on the Mutator’s variables. If a thesis is proven to be hyper-sensitive to a 5-10% variance in a contested input, the engine triggers a "Contested Variable Failure." This prevents the system from accepting "Fragile Truths" that look good in a vacuum but fail under real-world volatility.

## 11. The Synthesis Layer: Canonical Ledger vs. Audience-Specific Brief
**Context:** The first synthesis pipeline translated `ledger.json` directly into `Report.md` and then QA-checked faithfulness. This preserved adversarial depth but repeatedly produced founder memos that were too thesis-native, too technical, or too alarmist. The extractor was trying to do two incompatible jobs at once: canonical evidence compression and audience-ready prioritization.

**The Anomaly (Faithful but Not Useful):** The baseline one-shot chatbot could often write a cleaner founder memo from `evidence.txt + thesis.md` because it implicitly performed an advisory compression step the pipeline lacked. Our direct `ledger -> memo` path preserved thresholds, simulation mechanics, and internal logic that were valid in the thesis but suboptimal in the final artifact.

**Decision: Inserted an Explicit Planning Layer (`derive_brief`).**
* **The Fix:** The synthesis path is now `ledger -> brief -> memo -> QA`, with `ledger.json` remaining the canonical machine-readable artifact and `brief.json` acting as the audience-specific salience planner.
* **The Brief's Job:** It extracts the opening judgment, prerequisite action, main experiment, sequencing, core trade-off, and plain-language decision rule before the renderer writes prose.

**Trade-Off Analysis:**
* **Fidelity vs. Usefulness:** A direct render from the ledger maximizes traceability but often surfaces too much machinery. Adding `brief.json` introduces one more abstraction layer, but it allows the system to separate what is true from what is most useful to say first.
* **Static Contracts vs. Dynamic Adaptation:** We kept the ledger schema and QA contract hardcoded, while making the brief renderer-specific. This preserves debuggability and comparability while giving the system a controlled place to adapt salience by audience.
* **One More Failure Surface:** The brief can distort the ledger by over-compressing, softening, or reordering conclusions incorrectly. To offset this, QA was expanded to check the memo against both the canonical ledger and the planning brief.
* **Canonical Artifact Hierarchy:** `ledger.json` is the durable epistemic asset; `brief.json` is disposable and audience-bound. This preserves a machine-readable record of the adversarially hardened conclusions even if future renderers change.

## 12. Post-Hoc Adversarialization: QA as a Real Gate
**Context:** Once the synthesis pipeline gained an audience-specific planning layer, the output system itself faced the same failure mode as the thesis engine: a renderer could produce polished prose that softened, reordered, or partially omitted the hardest conclusion while still sounding plausible.

**Decision: Made QA a Hard Consequence, Not a Decorative Check.**
* **The Fix:** The QA stage now evaluates the rendered artifact against both `ledger.json` and `brief.json`, and `Report.md` is only written if the artifact clears the configured threshold. A candidate can be "mostly correct" and still be blocked if it fails to preserve the brief's opening judgment, prerequisite action, main experiment, sequencing, or plain-language decision rule.

**Trade-Off Analysis:**
* **Higher False Negatives vs. Trustworthy Output:** A strict QA gate can block artifacts that are substantively good but imperfectly aligned with the brief. This increases friction, but it prevents the exact downstream softening that the adversarial engine was built to eliminate.
* **ZTARE Applied to Its Own Output Layer:** The architecture now mirrors the engine's internal logic. `extract_ledger` establishes the durable evidence state, `derive_brief` defines the intended strategic emphasis, `render_artifact` produces the candidate, and `qa_artifact` acts as a post-hoc adversary and judge. This closes the loop: the reporting layer is no longer trusted to self-certify.
* **Debuggability Through Separation:** Because QA checks the memo against both the ledger and the brief, failures become legible. A miss can now be identified as an extraction problem, a planning problem, or a rendering problem rather than collapsing into one opaque "bad memo" outcome.

## 13. History Contamination vs. Epistemic Memory (Focused vs. Full)
**Context:** Startup projects accumulate mixed histories across rubrics and thesis phases (e.g., early Monte Carlo/unit-econ frames, later experiment-design frames). Feeding raw mixed history into synthesis improves auditability but can contaminate founder-facing artifacts: the extractor/planner latches onto older explicit thresholds or obsolete frameworks, producing memos that are internally “faithful” yet strategically mis-sequenced (e.g., prioritizing host ask-rate ops or PSFS gates over the currently central upstream blocker like onboarding friction).

**Decision: Introduced `history_mode` and `history_summary.json`.**
* **Modes:**
  * **Focused:** Use core artifacts + a small recent slice of the active rubric family, plus a compact `history_summary.json` derived from the broader history.
  * **Full:** Use core artifacts + the full relevant raw history (history + debates), plus the same `history_summary.json`.
* **Defaults:** Audience-facing artifacts (`founder_memo`, `decision_brief`) default to **focused**. Research/audit artifacts default to **full**.

**Trade-Off Analysis:**
* **Artifact Quality vs. Provenance:** Focused mode improves memo clarity and reduces rubric cross-talk; full mode preserves traceability and cross-rubric convergence evidence.
* **Raw Recall vs. Compressed Signal:** Instead of excluding older work entirely, `history_summary.json` preserves long-range signal (pivots, recurring failures, recurring survivors) without injecting obsolete raw scaffolding into the final memo.
* **Explicit Control:** The trade-off is now a CLI-visible choice (`--history-mode focused|full`) rather than an implicit “whatever the latest files happen to be.”

## 14. Karpathy-Style Workspace vs. ZTARE Core (External Memory Boundary)
**Context:** The project reached the point where `evidence.txt` had become a bottleneck. Manual evidence files were brittle, easy to under-specify, and costly to rebuild from scratch. Karpathy's LLM knowledge-base pattern surfaced as the obvious upstream inspiration: persistent source accumulation, markdown knowledge maintenance, and compounding context over time.

**The Architectural Tension:** A naive merge would have pulled that stateful memory directly into ZTARE. That would have been a mistake. The core validator derives its integrity from zero-trust adversarial evaluation. If the verification panel starts inheriting a wiki of previously "accepted" knowledge as privileged truth, the system drifts from execution-backed falsification toward historical consensus and coherence smoothing.

**Decision: Build a Level 2 External Workspace, Not a Stateful Validator.**
* **The Fix:** We added a dedicated upstream memory layer:
  * `update_workspace.py` reads `raw/`, extracts per-source notes, and maintains a persistent `workspace/`
  * `compile_evidence.py` now compiles either `raw/` or `workspace/` into a bounded `compiled_evidence.txt`
  * ZTARE itself remains unchanged and stateless; it still consumes only `evidence.txt`
* **The Boundary:** The workspace accumulates knowledge; ZTARE attacks a snapshot. The validator never reads `workspace/` directly.

**Trade-Off Analysis:**
* **Level 1 vs. Level 2:** We initially built a stateless compiler (`raw/ -> compiled_evidence.txt`). Rather than throw it away, we promoted it into the compiler half of a Level 2 design by adding `update_workspace.py` in front of it. This preserved the useful extraction work while making the upstream memory persistent.
* **State vs. Integrity:** The conclusion was not "state is bad." The real risk is unearned trust. A stateful external workspace is acceptable as long as the validator receives only a bounded evidence snapshot and does not treat accumulated notes as authority.
* **Velocity vs. Debuggability:** A stateful workspace introduces another failure surface: bad source-note extraction or bad merge logic can now contaminate the compiled snapshot. We accepted that complexity because the benefits are real: lower token cost over time, incremental source reuse, contradiction preservation, and a path toward a product-grade research substrate.
* **Karpathy Adaptation, Not Karpathy Clone:** We did not implement Karpathy's full autonomous recursive wiki agent. We intentionally extracted the upstream accumulation pattern and stopped short of autonomous self-search or self-healing loops. That keeps the memory layer useful without blurring the validator's role.
* **Terminology Boundary:** For the paper, `cognitive camouflage` remains the term for scored persuasive compliance under adversarial evaluation. For the workspace layer, the relevant failure mode is different: coherence smoothing or false reconciliation. This distinction prevents the product architecture from silently changing the paper's claim.

**Result:** The system now has a cleaner division of labor:
* `raw/` and `workspace/` improve the evidence substrate
* `compile_evidence.py` emits a bounded validation packet
* `autoresearch_loop.py` remains the hostile validator
* `synthesize.py` renders hardened outputs for human use

## 15. Global Primitive Library: Precedent, Not Truth
**Context:** As the workspace/evidence pipeline matured, the next bottleneck became adversarial memory. Strong attacks, failure motifs, and executable counter-tests discovered in one project largely died when the run ended. Simon Willison's "hoard and recombine" idea was relevant, but directly globalizing `verified_axioms.json` would have violated the core rule that unearned trust is the enemy.

**Decision: Build a Curated Global Primitive Library Instead of a Global Truth Store.**
* **The Fix:** We introduced `global_primitives/` as a separate memory layer for:
  * attack patterns
  * failure patterns
  * test templates
  * narrow causal motifs
* **The Pipeline:** `extract_incidents.py` harvests recurring incidents from debate logs and run artifacts, `draft_primitives.py` uses an LLM to draft candidate cards, and `approve_primitive.py` promotes or rejects them via human review.
* **The Boundary:** These primitives are never evidence and never axioms. They are reusable adversarial precedents.

**Trade-Off Analysis:**
* **Compounding Leverage vs. Overgeneralization:** A primitive library prevents the system from rediscovering the same attack patterns repeatedly, but it creates a new risk: elegant pseudo-abstractions that sound portable without actually being so. That is why promotion is hybrid rather than automatic.
* **Python vs. LLM Labor Split:** Python is good at extracting incidents and signatures; the LLM is good at drafting candidate cards; the human remains responsible for deciding whether a candidate is actually reusable and scoped well enough to approve.
* **Attack-Side First:** To avoid overfitting or cross-domain contamination, primitives are introduced into the engine on the attacker/judge side first. Mutator-side use is explicit opt-in and framed as `TRANSFER HYPOTHESES`, never as verified truths.
* **Precedent vs. Evidence:** This preserves the central epistemic distinction. `workspace/` stores project knowledge. `global_primitives/` stores cross-project precedents about how reasoning fails or how it should be attacked.

## 16. Evidence Became a First-Class Substrate
**Context:** The original workflow treated `evidence.txt` as a manually authored project brief. That was workable for one-off runs, but it did not scale to iterative research. The same source material had to be mentally recompiled over and over, contradictions were easy to lose, and downstream failures were often traceable to upstream omission rather than to the validator itself.

**Decision: Treat Evidence as an Explicit External Layer, Not an Incidental File.**
* **The Fix:** We now have a three-stage evidence path:
  * `raw/` stores source material
  * `workspace/` stores structured, persistent project memory
  * `compiled_evidence.txt` is the bounded snapshot promoted into `evidence.txt` for the validator
* **The Boundary:** This is an exogenous improvement to the system, not a mutation of the validator proof. ZTARE still consumes only a snapshot and remains stateless.

**What Was Actually Achieved:**
* **From Manual Brief-Writing to Evidence Operations:** Evidence is no longer just a handwritten memo. It is now a maintained substrate with provenance, contradiction preservation, open questions, and repeatable compilation.
* **Reproducibility:** A run can now be traced back to a bounded compiled snapshot rather than to an opaque human summarization process.
* **Incremental Memory Without Trusted State:** The workspace can accumulate over time without giving the validator privileged access to prior accepted conclusions.
* **Compatibility With Vanilla Runs:** The new path does not force a new paper workflow. Existing projects can still run directly from manually curated `evidence.txt` with no primitives, no workspace, and no deterministic gates unless those are explicitly enabled.

**Interpretation:** This was not a cosmetic tooling improvement. It clarified that a large share of apparent "engine" weakness was actually evidence-substrate weakness. That distinction matters because it cleanly separates endogenous kernel work from exogenous research infrastructure.

## 17. Recursive Gain Means Converting Failure Into Reusable Constraint
**Context:** A recurring question was whether the recursive setup was actually producing knowledge or merely producing more output. The answer became clearer only after mining V3 and running early V4 loops.

**What Was Learned:**
* **V3 produced real architectural failures, not just noise.** The mining pass showed durable failure classes: one-way decay masquerading as Bayesian learning, domain leakage into friendly simulations, weak score semantics, fragile credit assignment, and infallible-aggregator traps.
* **V4 surfaced a new loophole immediately.** Once score semantics were hardened, the loop discovered a subtler exploit: `self_referential_falsification`, where a thesis can pass by proving only its own bookkeeping rather than its claimed mechanism.
* **The important step was conversion, not just detection.** That loophole was turned into:
  * a deterministic scoring guardrail in `test_thesis.py`
  * an approved reusable primitive in `global_primitives/approved/self_referential_falsification.json`

**Interpretation:** This is the practical meaning of recursive epistemic improvement in this system. A run becomes knowledge-bearing when a discovered failure stops being an anecdote and becomes a reusable constraint on future runs. The engine does not need to invent grand new theories every iteration. It needs to repeatedly do something narrower and more defensible: expose a real failure mode, formalize it, and reduce the probability of paying that tuition twice.

## 18. Benchmark Measurement Trap: Semantic Outputs Need Semantic Evaluation
**Context:** The first `constraint_memory` benchmark used keyword/phrase matching to decide whether the evaluator had identified a given exploit family. That was too brittle for LLM-generated judge output. A judge could correctly diagnose the mechanism in different words and still be counted as a miss.

**What Went Wrong:**
* **Statistical Gravity Toward Software Defaults:** The initial benchmark treated evaluator output like a normal software log stream and reached for the cheapest familiar tactic: string matching. That is acceptable for fixed APIs and exact error codes, but not for semantic model judgments.
* **Missed Second-Order Failure:** The benchmark itself became vulnerable to the same class of mistake the project is studying: surface form was over-trusted, semantic substance was under-read.
* **Builder Bias Over Benchmark Epistemology:** The infrastructure was optimized to run, isolate, and summarize results quickly. It was not sufficiently optimized to preserve the semantic meaning of the evaluator's diagnosis.

**Decision: Add a Lightweight LLM Adjudicator as an Optional Measurement Layer.**
* **The Fix:** `benchmarks/constraint_memory/run_benchmark.py` now supports `--adjudicator-model`, which asks a second model whether the judge semantically caught the expected exploit family.
* **The Boundary:** The adjudicator does not change the evaluator, mutate the specimen, or replace the raw metrics. It is strictly a measurement aid layered on top of the benchmark.
* **The Rule:** Keep both signals:
  * heuristic detection for exact/obvious matches
  * adjudicated detection for semantic paraphrase

**Interpretation:** This was a useful local postmortem. When the system under test is an LLM, the benchmark itself must be designed with semantic variance in mind. Otherwise the measurement harness quietly injects false negatives and degrades the paper's claim. More broadly: when evaluating model judgments, benchmark design must be treated as epistemic infrastructure, not just plumbing.

## 19. First Constraint-Memory Benchmark Result: Gates Help, Primitives Overfire
**Context:** After adding corpus-derived bad specimens, good controls, and an optional semantic adjudicator, the first meaningful benchmark comparison across `A_baseline_soft_judge`, `B_deterministic_gates`, and `C_gates_plus_primitives` became interpretable.

**What the Result Showed:**
* **Deterministic gates were the clearest real gain.** The hardened evaluator eliminated the remaining false accepts that the soft judge still allowed.
* **The semantic adjudicator was necessary.** Several genuine semantic catches were invisible to simple keyword matching and only became visible once the benchmark respected paraphrase.
* **Primitives did not yet earn an empirical win.** `C` matched or underperformed `B` and over-rejected the positive controls.
* **The benchmark surfaced an autoimmune failure mode.** The primitive-armed evaluator was too eager to treat any dependence on upstream signals as a trust leak, even when the thesis explicitly claimed only a narrow, local deterministic mapping.

**Decision: Separate Taxonomy Hits From Structural Kills And Add Safe Harbor.**
* **Dual Detection Metrics:** The benchmark now distinguishes:
  * exploit-family detection
  * acceptable fatal structural detection
* **Evidentiary Safe Harbor:** The rubric and judge contract now explicitly protect bounded local components that:
  * disclaim upstream truthfulness
  * implement only a deterministic mapping or fail-closed gate
  * fully test that local contract
  * do not inflate the local proof into a whole-system guarantee

**Interpretation:** This result was productive, not disappointing. It showed that score hardening is already defensible, while adversarial memory still needs calibration. That is exactly the kind of empirical separation a real systems paper needs.

## 20. First Organic Wedge: `C` Beat `B` On The Historical Corpus
**Context:** After cleaning the `t2_ai_inference` ex-post evidence formatting and tightening exploit-family adjudication so generic forecast criticism no longer counted as family detection, the main benchmark produced the first clear corpus-derived win for `C_gates_plus_primitives` over `B_deterministic_gates`.

**Run:** `benchmarks/constraint_memory/runs/20260404_201717`

**Result:**
* `A_baseline_soft_judge`
  * fatal structural detection: `1.0`
  * false accept rate: `0.0`
  * false reject rate: `0.5`
* `B_deterministic_gates`
  * fatal structural detection: `0.857`
  * false accept rate: `0.143`
  * false reject rate: `0.0`
* `C_gates_plus_primitives`
  * fatal structural detection: `1.0`
  * false accept rate: `0.0`
  * false reject rate: `0.0`

**Why It Matters:**
* `B` still falsely accepted `t2_ai_inference` after the cleanup.
* `C` did not.
* `C` preserved the `0.0` false reject rate on the good controls while restoring perfect structural detection.

**Interpretation:**
This is the first serious organic wedge for the primitives layer on the historical corpus. It is stronger than the earlier calibration runs because it no longer depends on synthetic variants or on the autoimmune regime where `C` overfired on good controls. However, it is still a single stochastic run. The correct conclusion is:
* the `C > B` thesis is now empirically plausible on the real corpus
* but it should be replicated across additional identical reruns before being treated as paper-grade stable

## 21. Recursive Gain Emerged Inside The Evaluator Itself
**Context:** After building the separate `claim_test_mismatch` mini-suite from historical runs, a new failure mode appeared inside the primitive-armed evaluator itself. The system surfaced a blind spot in its own detection logic rather than in the thesis under test.

**Key Evidence:** `benchmarks/constraint_memory/runs/20260404_213459`
* `selective_rigor_recursive_bayesian`
  * `B_deterministic_gates`: passed at `100`
  * `C_gates_plus_primitives`: failed at `0`
* `selective_rigor_simulation_god`
  * `B_deterministic_gates`: capped to `25`
  * `C_gates_plus_primitives`: passed at `100`

**What Actually Happened:**
* The score contract was not the problem. It behaved as designed.
* The failure was **detection-level**:
  * under `B`, `simulation_god` was marked `proof_is_self_referential = true`
  * under `C`, the same specimen was marked `proof_is_self_referential = false`
* In other words, primitives changed the judge's initial reading of the thesis. They helped on one selective-rigor specimen and hurt on another.

**Decision: Treat This As A Recursive Self-Improvement Finding, Not Just A Benchmark Result.**
* **New architectural rule:** primitives should not shape the judge's first-pass identification of the crux.
* **Implication:** the evaluator should identify the central claim / eigenquestion first, test whether the suite targets that claim, and only then consult precedent memory.
* **Reasoning:** front-loading precedent memory can bias the detector toward accepting peripheral rigor as substantive proof.

**Interpretation:** This is a concrete example of the `failure -> diagnosis -> constraint` loop that motivates the second paper. The engine used its own benchmark output to discover a blind spot in its own evaluation architecture. That is recursive epistemic gain in the narrow, defensible sense: a failure mode of the system itself became a new architectural constraint for the next version.

## 22. Ordering Is Family-Specific; Human-In-The-Loop Is The Proven Method
**Context:** After implementing the experimental `C2_gates_plus_primitives_crux_first` condition, the benchmark was rerun on both the narrow `claim_test_mismatch` suite and the broader main suite.

**Key Evidence:**
* `benchmarks/constraint_memory/runs/20260404_221606`
  * `C2_gates_plus_primitives_crux_first` dominated the `claim_test_mismatch` suite:
    * structural detection `1.0`
    * false accept rate `0.0`
  * it fixed the exact primitive-ordering blind spot on `selective_rigor_simulation_god`
  * it also killed `selective_rigor_recursive_bayesian`, which both `B` and `C` had passed in that run
* `benchmarks/constraint_memory/runs/20260404_223826`
  * on the main suite, `C2` did **not** beat `C`
  * `C` remained the stronger default condition:
    * `C`: false accept `0.0`, false reject `0.5`, family detection `1.0`
    * `C2`: false accept `0.143`, false reject `0.5`, family detection `0.571`
  * `C2` reintroduced the `t2_ai_inference` false accept that `C` had eliminated

**What This Means:**
* No single primitive-ordering policy uniformly dominates across exploit families.
* `crux-first` helps on **claim-test mismatch / selective rigor** failures.
* the current default `C` remains better on the broader mixed-family main suite.
* therefore the next architecture should not assume a universal ordering; it should route primitive application in a **family-aware** way.

**Paper-Grade Interpretation:**
* `A -> B`: deterministic gates fix score-channel corruption.
* `B -> C`: primitives improve overall evaluator utility on the main suite.
* `C vs C2`: ordering matters, but the benefit is exploit-family-specific rather than globally dominant.
* this is a stronger architectural result than a simple "C2 is better" claim.

**Methodological Note:**
This improvement loop was **human-in-the-loop**, not autonomous self-rewriting by ZTARE. That is not a weakness. It is the proven design methodology:
* observe system failure
* perform autopsy / diagnosis
* convert failure into an explicit architectural constraint
* re-evaluate the modified system

That is the defensible version of `Pain + Reflection = Algorithm Update` for Paper 2. The evidence supports a repeatable systems-engineering process, not a claim of fully autonomous self-improvement.

## 23. Preserve Topological Pivot For Exploration; Add A Bounded V4 Mutation Path
**Context:** After reseeding `projects/epistemic_engine_v4/` around semantic-gate stabilization, the first live run drifted back into the legacy stagnation machinery. Once stagnation rose, `autoresearch_loop.py` injected the old blank-slate / topological-pivot prompt stack and the mutator started proposing unrelated grand architectures (`Token Distribution Entropy`, `DisputeEngine`) instead of staying inside the bounded V4 kernel experiment.

**Decision:** Keep the legacy topological-pivot logic for open-ended exploratory projects, but add a V4-specific mutation path that disables blank-slate pivots and constrains mutations to the active mechanism under test.

**Trade-Off Analysis:**
* **Exploration Power vs. Attribution:** The topological-pivot operator is strong when the problem is underdefined and the main risk is being trapped in the wrong ontology. It is the wrong tool when the goal is to measure whether one bounded evaluator change actually improves benchmark behavior. Preserving it globally keeps broad search power; disabling it for V4 restores causal attribution.
* **Architectural Novelty vs. Benchmark Hygiene:** The old stagnation path is good at surfacing new grand designs. For V4, that novelty is a liability because it contaminates the item-1 test with unrelated mechanisms. The bounded V4 path sacrifices some search breadth in exchange for cleaner recursive-hardening evidence.
* **One Loop For Everything vs. Mode-Specific Discipline:** A single universal stagnation strategy is simpler to maintain, but it assumes every project is still in ontology-search mode. Adding a V4 branch increases code complexity slightly, yet it matches the real difference between exploratory research projects and contract-governed evaluator hardening.

**Implementation Consequence:** `src/ztare/validator/autoresearch_loop.py` now special-cases `epistemic_engine_v4`:
* no blank-slate purge
* no forced `Z = f(X, Y)` / laws-of-physics / logic-DAG pivot prompt
* stagnation feedback is preserved
* mutation is constrained to:
  * typed semantic evidence fields
  * Python-derived gate logic
  * unresolved-handling rules
  * interface stubs only

**Interpretation:** Topological pivot remains a strong exploration operator for general-purpose projects. It is not the right recursive-hardening operator for a benchmark-anchored kernel experiment. V4 therefore gets a narrower mutation regime so that recursive improvement remains measurable rather than theatrical.

## 24. Keep Layer Names Distinct Even When The Pattern Recurs
**Context:** As V4 hardening, supervisor routing, and Paper 4 matured, the same governance pattern started appearing at multiple layers. That created a naming risk: calling every deterministic orchestrator a "meta-runner" or every governance surface a "supervisor" would make the architecture harder to understand just as it was becoming more fractal.

**Decision:** Keep the names layer-specific:
* **ZTARE validator** = adversarial domain-validation loop
* **V4 kernel** = evaluator under hardening
* **meta-runner** = kernel-local deterministic promotion runner for V4 stage advancement
* **supervisor** = multi-program control plane for bounded work packets
* **paper bundles** = public-facing publication layer

**Trade-Off Analysis:**
* **Local precision vs. global elegance:** Reusing one name everywhere would sound elegant but would blur responsibilities. Distinct names are less poetic but much more operable.
* **Fractality vs. synonym drift:** The same generation/evaluation separation principle recurs across layers, but that does not mean the runtime components are interchangeable.

**Interpretation:** The system is fractal in structure, not in terminology. The control plane should not be described as the kernel, and the papers should not be mistaken for runtime governance.

## 25. The Supervisor Is Governance, Not Truth
**Context:** Once the supervisor could route bounded programs end-to-end, there was pressure to use it as a universal engine for research, prose generation, and semantic judgment. That would have duplicated the validator and softened the epistemic boundary.

**Decision:** The supervisor remains a deterministic governance layer only. It may:
* route bounded packets
* enforce write scope
* own commit authority
* stop at human gates

It may not become:
* a truth engine
* a novelty scorer
* a generic semantic judge

**Trade-Off Analysis:**
* **Operational leverage vs. epistemic confusion:** Letting the supervisor absorb semantic judgment would make the operator interface simpler, but it would create a second soft evaluator surface and collapse the separation the stack was designed to protect.
* **Factory discipline vs. bureaucratic inflation:** The supervisor earns its keep by bounding work and preserving provenance. It loses that value if it becomes another fuzzy model-mediated judge.

**Interpretation:** The supervisor improves execution discipline around kernel and research work. It does not replace the kernel and it does not replace ZTARE.

## 26. Paper 4 Became An Archived Supervisor Experiment And A Live Direct-Writing Manuscript
**Context:** The supervisor-era Paper 4 packet workflow eventually produced real evidence and usable sections, but the cost of continuing manuscript production inside the factory stayed too high relative to prose quality and operator attention.

**Decision:** Soft-decommission Paper 4 as an active supervisor program.
* keep the supervisor-era artifacts as archived provenance
* keep the evidence for the paper's governance claims
* move the canonical live manuscript to direct-writing mode

**Canonical live outputs:**
* `research_areas/drafts/paper4_full_working.md`
* `papers/paper4/main.tex`

**Archived provenance:**
* `research_areas/_archive/paper4_supervisor/`

**Trade-Off Analysis:**
* **Factory purity vs. paper quality:** Finishing the paper inside the supervisor would have preserved perfect procedural symmetry, but the marginal prose gain was poor and the operational cost was high.
* **Deletion vs. provenance:** Deleting the supervisor-era artifacts would have made the repo cleaner at the cost of erasing the evidence that Paper 4 depends on. Archiving keeps the record without keeping it on the active critical path.

**Interpretation:** The Paper 4 result survives the decommission. The supervisor-era workflow became empirical evidence and archival provenance; the manuscript itself moved back to a lighter writing mode.

## 27. Public Paper Bundles Live Under `papers/`; Root `paperN/` Directories Are Scratch
**Context:** By the time Papers 3 and 4 were ready for SSRN-style circulation, the repo had accumulated two kinds of paper artifacts:
* public-consumable sources meant for GitHub browsing and reuse
* local build directories full of PDFs, TeX aux files, Overleaf zips, and scratch outputs

That split was not encoded strongly enough, which made the repo noisier than it needed to be.

**Decision:** Standardize the publication layer as:
* `papers/paper1/`
* `papers/paper2/`
* `papers/paper3/`
* `papers/paper4/`

These public bundles contain only the files needed for source consumption (markdown drafts, LaTeX source, bibliography, and figure assets where needed).

Root `paper1/`–`paper4/` directories are treated as local scratch/build workspaces and ignored by git.

**Trade-Off Analysis:**
* **Convenience vs. cleanliness:** Working directly in one local TeX directory is convenient, but publishing that entire workspace would leak build products and drafting artifacts into the public repo.
* **Minimality vs. completeness:** Public bundles should stay lean. The point is source visibility and reusability, not preservation of every local compile byproduct.

**Interpretation:** GitHub should show the papers as clean source bundles. The local build directories remain useful, but they are not the public artifact.

## 28. Future Runtime-Eligible Work Starts As A Seed, Not As Public Docs Or Debate
**Context:** Two feature notes exposed the same repository-structure mistake: `supervisor_artifact_lifecycle` and `vnext_semantic_gate_stabilization` were initially written in `docs/` or debate-adjacent locations even though they were really candidate future programs the supervisor might execute later.

**Decision:** If a note is meant to become future bounded work, it belongs first in `research_areas/seeds/`, not in `docs/` and not in `research_areas/debates/`.

**Trade-Off Analysis:**
* **Public discoverability vs. execution readiness:** `docs/` is appropriate for public-facing implementation references. It is the wrong place for a speculative future program because it makes an internal candidate look like settled public documentation.
* **Debate history vs. source-of-truth intent:** Debate files are tactical history. Seeds are executable intent. Conflating them weakens the supervisor workflow.

**Interpretation:** The repo now has a clearer rule:
* `docs/` = public/operational documentation
* `research_areas/seeds/` = future program candidates
* `research_areas/debates/` = tactical reasoning and execution history

## 2026-04-25 night — Cage v5.0 Phase 3a gate triage decisions

After 5-perspective panel review (Chaos / Quantum / Physics / Math /
CS Software Engineer) of the 17 dormant gates inventoried in the
gp158 audit (Class L finding), the following decisions are recorded:

### RETIRE (1 gate)
- **`bridge_scope_contract`** — three perspectives flagged the
  forbidden-marker blacklist as brittle code-smell with no v5.0
  signal (Chaos: no chaos-substrate signal; Physics: no physical
  content; Math: brittle blacklist; CS: dead unless bridge-discovery
  campaigns active). Module remains importable; revive when bridge-
  discovery campaigns return. Not registered in `get_default_cage()`.

### CONDITIONAL WIRE (3 gates)
- **`ansatz_survivor_gate`** — only sub-gate 1 (top-K Lean-shortness
  ranker) is live. Sub-gates 2/3 honestly deferred per panel.
- **`continuum_limit_gate`** — only sub-gate 1 (RMS-chaos-trap
  precheck, T·λ_max>5 Lyapunov sanity) is live. Sub-gates 2/3
  (BKM/Leray) deferred pending PDE substrate roadmap.
- **`domain_match_gate`** — scope tightened to {proof_target,
  nd_features-with-Lean} per panel (was: universal feature_dict).
  Mathematician + CS flagged regex-based Lean parsing as fragile
  but contained.

### UTILITY (not registered as Gate)
- **`residual_norm.py`** — pure helper imported by downstream gates
  (coordinate_invariance, asymptotic_claim_discipline). No Cage
  registration; remains importable.

### WIRE unconditional (10 gates)
asymptotic_claim_discipline, coordinate_invariance,
deterministic_charter_gates, ensemble_ambiguity, prompt_leak_audit,
proof_surveyability, pslq_falsity_audit, semantic_gate_stabilization,
translation_diff, wasserstein_persistence.

### Cross-cutting concerns deferred (Munger anti-complexity)
- `translation_diff` + `domain_match` merge candidate: deferred.
  Keep separate during v5.0; merge later when Lean tooling stabilizes.
- `proof_surveyability` + `ansatz_survivor` composability (filter +
  ranker): deferred. Both wired during v5.0; fold post-v5.0.

### Substrate-class taxonomy expanded
Panel surfaced three additional classes the v5.0 spec missed:
- `proof_target` (Lean / formal-proof, GP-122/GP-139)
- `closed_form_constant` (PSLQ, GP-145)
- `time_series_chaotic` (chaotic subset of time_series, GP-143/146)

These augment the original {1d, nd_features, time_series, audit,
literature} → 8 substrate classes the v5.0 Cage routes against.

Full panel transcript appended to GP-157 seam.
Verified by 70/70 tests + 33/33 arch-map claims green.
