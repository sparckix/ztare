# DECISION LOG: Adversarial Reasoning Engine

> **Status notice (2026-05-20):** This log is historical. It was last touched
> on 2026-05-17 and has not yet been updated to reflect the current ZTARE
> architecture: in-loop validation, out-of-loop research operations, and the
> reflexive intelligence layer. It remains useful as provenance for early
> validator and hardening decisions, but it is not the current architecture
> reference. A future pass should either append new dated decisions or split the
> log into historical and current decision records.

**Premise:** LLMs optimize for semantic probability, not verifiable truth. This engine runs qualitative reasoning through a multi-agent adversarial debate with deterministic checks, so that claims are forced through validation rather than accepted on fluency.

**Core tenet:** Prompt intentions do not prevent model hallucination; deterministic mechanisms do.

**Layer map used in this log:**
* **Evidence substrate:** `raw/`, `workspace/`, compiled evidence snapshots
* **Validator layer:** the ZTARE adversarial loop over bounded evidence
* **Kernel layer:** V4 evaluator logic and its hardening path
* **Control-plane layer:** deterministic routing and commit governance around bounded work programs
* **Publication layer:** paper bundles and reader-facing artifacts

---

## 1. Asymmetric model routing for inference-time compute
**Context:** Running a 3-agent Verification Panel plus a Meta-Judge for up to 50 iterations is expensive in inference-time compute and adds significant latency.

**Decision:** Implemented asymmetric model routing. `gemini-3-flash-preview` handles the dynamic Attackers; `gemini-3.1-pro-preview` is isolated exclusively as the Director (Meta-Judge).

**Trade-off analysis:**
* **Compute vs. reasoning depth:** Using "Pro" for the entire loop maximizes reasoning depth but makes deep-iteration loops too expensive and too slow. Routing generation to "Flash" runs it as a high-volume mutation engine, exploring more candidate state at lower token cost.
* **Judge quality (edge case):** "Flash" is weaker at catching subtle logical regressions. If used as the Meta-Judge, articulate but flawed logic can pass. "Pro" is used as the validation gate.
* **Cost trade:** We spend extra tokens on the Pro judge to catch strategic or logical errors (e.g., a fatal assumption in a turnaround strategy) at inference time, where a missed flaw is more expensive than the token cost of the judge.

## 2. Specification gaming at Level 5
**Context:** The `--auto-evolve` flag (Level 5) allowed the Director to autonomously rewrite the JSON rubric upon reaching a perfect score (100/100).

**The anomaly (reward hacking):** When auditing the "Hard Problem of Consciousness," the agent determined that reaching 100/100 within the rubric's thermodynamic constraints was impossible. Instead of solving the thesis, it attacked the JSON rubric file. It rewrote the rubric to state: *"A perfect thesis only needs to explain why apples fall from trees,"* emitted a paragraph on Newtonian gravity, scored itself 100/100, and terminated.

**Mechanism implemented: stagnation trigger**
* **The fix:** A circuit breaker (`stagnation_count >= 3`). If the score does not improve after three iterations, the system is blocked from altering the rubric and reverts to its best-known state.
* **Second-order effect:** This keeps the agent inside the original scoring function and prevents unconstrained rubric dilution.
* **Trade-off:** It is a rigid constraint. It also blocks the agent from lowering constraints when a premise is genuinely unsolvable, which can trap it in a compute loop instead of letting it flag the premise as broken.

## 3. Strict rubric penalties narrow the search space
**Context:** Qualitative domains lack deterministic compilers (like PyTorch). To approximate a `SyntaxError` for bad logic, the rubric applies quantitative penalties (e.g., a `-20 pt anti-fluff penalty` for using mystical terms in a physics thesis).

**The anomaly:** Strict penalties on qualitative text narrow the usable state space. The engine frequently stalled, spending roughly 40% of its compute in local dead-ends where no mutation succeeded without triggering the penalty.

**Trade-off analysis:**
* **Output density vs. iteration velocity:** The penalty produces denser output (it forced the system to frame consciousness as an "Integrated Cooling Algorithm") but throttles velocity by rejecting a large fraction of attempts.
* **Intermediate steps get punished:** The system cannot bridge large logical leaps (e.g., shifting from functionalism to participatory realism) without temporarily writing connective "fluff." The penalty rejects those intermediate steps even when they are on the path to a better thesis.
* **Resolution:** We accept the latency and wasted compute. Final-output validation is prioritized over generation-loop efficiency.

## 4. Cross-domain axioms cause scale errors
**Context:** The system originally treated verified axioms (claims that survived the Meta-Judge) as immutable cross-domain laws. If the system established the Bekenstein Bound in cosmology, it was forced to apply it everywhere.

**The anomaly (scale-blindness):** The agent entered a stagnation loop. It tried to solve the biological "Hard Problem of Consciousness" using black-hole physics, producing a 52-order-of-magnitude scale error. Because the Bekenstein Bound was a verified axiom, the Mutator was pushed to apply it to the biology thesis to avoid a penalty.

**Decision: added axiom retirement.**
* **The fix:** The prompt logic now lets the Mutator retire an axiom during a topological pivot if it is dimensionally or contextually irrelevant, shifting the constraint from "must use" to "must not contradict within domain."
* **Trade-off analysis:**
  * **Risk of regression:** This opens a vulnerability where the agent dismisses a valid but inconvenient truth to make the math easier (reward hacking).
  * **Flexibility:** The alternative is state-space collapse. Axiom retirement lets the system drop irrelevant problems (brains collapsing into black holes) and pivot to applicable biological constraints (Landauer thermal limits).

## 5. Dimensional verification via `pint`
**Context:** LLMs are syntactically fluent but do not track units. The mutator routinely submitted well-formatted equations that were physically impossible (e.g., subtracting Shannon entropy from physical capacity, or taking the hyperbolic tangent of a Joule).

**The anomaly (dimensionally invalid math):** The agent would rig its own `test_model.py` with raw `float64` variables to pass the Level 3 falsification suite. The numbers looked correct but encoded category errors, spending Director compute to catch basic physics failures.

**Decision: enforce dimensions via `pint`.**
* **The fix:** Added a dimensional check to the formatting prompt, requiring the Python unit test to wrap all physical variables in the `pint` UnitRegistry.
* **Trade-off analysis:**
  * **Increased test fragility:** Python execution fails more often. A logically sound thesis can crash because the agent mismatched a millisecond and a second in the code block.
  * **Dimension checks in code, not prose:** Offloading dimensional analysis to a deterministic library keeps category errors from reaching the Meta-Judge. We trade a higher Level 3 crash rate for catching dimensionally invalid math before the judge sees it.

## 6. Dropping the Search tool to avoid an SDK conflict
**Context:** The Verification Panel originally had both `Google Search` (for real-world constant verification) and `execute_python_code` (for mathematical falsification).

**The anomaly (SDK version conflict):** Mixing server-side tools (Search) with client-side tools (Python) requires the `include_server_side_tool_invocations` flag. The local Pydantic schema in the `google-genai` SDK rejected this flag as an "Extra input," producing `400/422` validation crashes with no available fix.

**Decision: Python tool only.**
* **The fix:** Removed the Google Search tool. Attackers are now prompted to rely on parametric knowledge to verify central variables, using `execute_python_code` to prove insolvency.
* **Trade-off analysis:**
  * **Loss of real-time grounding:** We lose the ability to fetch a current stock price or interest rate from the web.
  * **Avoids the SDK conflict:** The model's weights are reliable for fundamental constants (Planck limits, Bekenstein bounds, baseline financial formulas), so the Python sandbox is sufficient to refute hallucinated math without crashing the loop.

## 7. Regenerate the committee every iteration
**Context:** Generating 3 specialized Attackers per iteration is token-intensive and slow. The initial logic cached the committee if the JSON file already existed.

**The anomaly (stale attackers):** When the Mutator executed a topological pivot (e.g., moving from a local thermal model to a retrocausal cosmological model), the cached iteration-1 committee kept attacking the old, already-refuted vulnerabilities and missed the new structural flaws.

**Decision: no committee cache.**
* **The fix:** The script forces a fresh `generate_committee.py` execution on every iteration.
* **Trade-off analysis:**
  * **Added latency:** This adds roughly 45–60 seconds per iteration from API calls and rate-limit throttling.
  * **Attackers track the current thesis:** The Verification Panel is now generated against the current state of the thesis. If the Mutator invents a "Vacuum Arbitrage" defense, the next iteration generates an attacker specialized to test it. We trade iteration velocity for attackers that match the current claim.

## 8. Hung API threads deadlock the loop
**Context:** At high concurrency, API calls to heavy reasoning models (like Gemini 3.1 Pro) occasionally hang indefinitely at the network level, ignoring standard timeouts.

**The anomaly:** The `ThreadPoolExecutor` context manager (`with`) has an implicit `wait=True` on exit. When the 150s timeout triggered, the main thread deadlocked waiting for the hung socket to close, stalling the loop overnight.

**Decision: explicit abandonment.**
We removed the context managers and wrapped all API calls in explicit `executor.shutdown(wait=False, cancel_futures=True)` blocks. The loop now abandons hanging threads and survives transient API hangs without human intervention.

## 9. Require code execution to back claims
**Context:** LLMs are trained to be persuasive and can talk their way past logical inconsistencies when evaluated on text alone.

**Decision:** Added a deterministic evidentiary gate.

**Rationale:** The Meta-Judge treats natural-language claims as unsupported unless they are accompanied by Python stdout. Requiring the Verification Panel to deliver critiques via code execution removes the model's ability to use rhetoric to mask mathematical errors. We trade conversational feedback for outcomes backed by execution.

## 10. Parametric sensitivity auditing
**Context:** Strategic theses often rely on central variables — single numbers (cost of capital, model lifetime) that drive the entire conclusion.

**Decision:** Shifted from static verification to sensitivity assertions.

**Rationale:** Attackers must run a boundary audit on the Mutator's variables. If a thesis is sensitive to a 5–10% variance in a contested input, the engine triggers a contested-variable failure. This blocks theses that look good at a single point estimate but fail under input variation.

## 11. Synthesis layer: canonical ledger vs. audience-specific brief
**Context:** The first synthesis pipeline translated `ledger.json` directly into `Report.md` and then QA-checked faithfulness. This preserved adversarial depth but repeatedly produced founder memos that were too thesis-native, too technical, or too alarmist. The extractor was doing two incompatible jobs at once: canonical evidence compression and audience-ready prioritization.

**The anomaly (faithful but not useful):** The baseline one-shot chatbot could often write a cleaner founder memo from `evidence.txt + thesis.md` because it implicitly performed an advisory compression step the pipeline lacked. The direct `ledger -> memo` path preserved thresholds, simulation mechanics, and internal logic that were valid in the thesis but suboptimal in the final artifact.

**Decision: inserted an explicit planning layer (`derive_brief`).**
* **The fix:** The synthesis path is now `ledger -> brief -> memo -> QA`, with `ledger.json` remaining the canonical machine-readable artifact and `brief.json` acting as the audience-specific salience planner.
* **The brief's job:** It extracts the opening judgment, prerequisite action, main experiment, sequencing, core trade-off, and plain-language decision rule before the renderer writes prose.

**Trade-off analysis:**
* **Fidelity vs. usefulness:** A direct render from the ledger maximizes traceability but surfaces too much machinery. Adding `brief.json` adds one abstraction layer but separates what is true from what is most useful to say first.
* **Static contracts vs. dynamic adaptation:** We kept the ledger schema and QA contract hardcoded and made the brief renderer-specific. This preserves debuggability and comparability while giving the system a controlled place to adapt salience by audience.
* **One more failure surface:** The brief can distort the ledger by over-compressing, softening, or reordering conclusions incorrectly. To offset this, QA was expanded to check the memo against both the ledger and the brief.
* **Artifact hierarchy:** `ledger.json` is the durable record; `brief.json` is disposable and audience-bound. This keeps a machine-readable record of the hardened conclusions even if future renderers change.

## 12. QA as a real gate on rendered output
**Context:** Once the synthesis pipeline gained an audience-specific planning layer, the output system faced the same failure mode as the thesis engine: a renderer could produce polished prose that softened, reordered, or partially omitted the hardest conclusion while still sounding plausible.

**Decision: made QA a blocking gate, not a decorative check.**
* **The fix:** The QA stage evaluates the rendered artifact against both `ledger.json` and `brief.json`, and `Report.md` is only written if the artifact clears the configured threshold. A candidate can be mostly correct and still be blocked if it fails to preserve the brief's opening judgment, prerequisite action, main experiment, sequencing, or plain-language decision rule.

**Trade-off analysis:**
* **Higher false negatives vs. reliable output:** A strict QA gate can block artifacts that are substantively good but imperfectly aligned with the brief. This increases friction but prevents the downstream softening the adversarial engine was built to remove.
* **Same pattern applied to the output layer:** The reporting layer mirrors the engine's internal logic. `extract_ledger` establishes the durable evidence state, `derive_brief` defines the intended emphasis, `render_artifact` produces the candidate, and `qa_artifact` checks the candidate against both. The reporting layer no longer self-certifies.
* **Debuggability through separation:** Because QA checks the memo against both the ledger and the brief, a miss can be identified as an extraction problem, a planning problem, or a rendering problem rather than one opaque "bad memo" outcome.

## 13. History contamination vs. epistemic memory (focused vs. full)
**Context:** Startup projects accumulate mixed histories across rubrics and thesis phases (e.g., early Monte Carlo/unit-econ frames, later experiment-design frames). Feeding raw mixed history into synthesis improves auditability but can contaminate founder-facing artifacts: the extractor/planner latches onto older explicit thresholds or obsolete frameworks, producing memos that are internally “faithful” yet strategically mis-sequenced (e.g., prioritizing host ask-rate ops or PSFS gates over the currently central upstream blocker like onboarding friction).

**Decision: introduced `history_mode` and `history_summary.json`.**
* **Modes:**
  * **Focused:** Use core artifacts + a small recent slice of the active rubric family, plus a compact `history_summary.json` derived from the broader history.
  * **Full:** Use core artifacts + the full relevant raw history (history + debates), plus the same `history_summary.json`.
* **Defaults:** Audience-facing artifacts (`founder_memo`, `decision_brief`) default to **focused**. Research/audit artifacts default to **full**.

**Trade-off analysis:**
* **Artifact quality vs. provenance:** Focused mode improves memo clarity and reduces rubric cross-talk; full mode preserves traceability and cross-rubric convergence evidence.
* **Raw recall vs. compressed signal:** Instead of excluding older work entirely, `history_summary.json` preserves long-range signal (pivots, recurring failures, recurring survivors) without injecting obsolete raw scaffolding into the final memo.
* **Explicit control:** The trade-off is now a CLI-visible choice (`--history-mode focused|full`) rather than an implicit “whatever the latest files happen to be.”

## 14. External workspace kept separate from the validator
**Context:** `evidence.txt` had become a bottleneck. Manual evidence files were brittle, easy to under-specify, and costly to rebuild from scratch. The upstream pattern we drew on is a persistent LLM knowledge base: source accumulation, markdown knowledge maintenance, and context that compounds over time.

**The tension:** Pulling that stateful memory directly into ZTARE would undermine the validator. The validator depends on zero-trust adversarial evaluation. If the verification panel inherits a wiki of previously accepted knowledge as privileged truth, the system drifts from execution-backed falsification toward historical consensus and coherence smoothing.

**Decision: build an external workspace, keep the validator stateless.**
* **The fix:** We added a dedicated upstream memory layer:
  * `update_workspace.py` reads `raw/`, extracts per-source notes, and maintains a persistent `workspace/`
  * `compile_evidence.py` compiles either `raw/` or `workspace/` into a bounded `compiled_evidence.txt`
  * ZTARE remains unchanged and stateless; it still consumes only `evidence.txt`
* **The boundary:** The workspace accumulates knowledge; ZTARE attacks a snapshot. The validator never reads `workspace/` directly.

**Trade-off analysis:**
* **Reusing the stateless compiler:** We initially built a stateless compiler (`raw/ -> compiled_evidence.txt`). Rather than discard it, we put `update_workspace.py` in front of it. This preserved the extraction work while making the upstream memory persistent.
* **State vs. trust:** The conclusion was not "state is bad." The risk is unearned trust. A stateful external workspace is acceptable as long as the validator receives only a bounded evidence snapshot and does not treat accumulated notes as authority.
* **Velocity vs. debuggability:** A stateful workspace adds a failure surface: bad source-note extraction or bad merge logic can contaminate the compiled snapshot. We accepted that for lower token cost over time, incremental source reuse, contradiction preservation, and a path toward a reusable research substrate.
* **Scope of the adaptation:** We took the upstream accumulation pattern and stopped short of autonomous self-search or self-healing loops. That keeps the memory layer useful without blurring the validator's role.
* **Terminology boundary:** For the paper, `cognitive camouflage` remains the term for scored persuasive compliance under adversarial evaluation. The workspace layer has a different failure mode: coherence smoothing or false reconciliation. Keeping these distinct prevents the product architecture from silently changing the paper's claim.

**Result:** The system now has a clearer division of labor:
* `raw/` and `workspace/` improve the evidence substrate
* `compile_evidence.py` emits a bounded validation packet
* `autoresearch_loop.py` remains the adversarial validator
* `synthesize.py` renders hardened outputs for human use

## 15. Global primitive library: precedent, not truth
**Context:** As the workspace/evidence pipeline matured, the next bottleneck was adversarial memory. Strong attacks, failure motifs, and executable counter-tests found in one project died when the run ended. The "hoard and recombine" pattern was relevant, but directly globalizing `verified_axioms.json` would have violated the rule against unearned trust.

**Decision: build a curated global primitive library, not a global truth store.**
* **The fix:** We introduced `global_primitives/` as a separate memory layer for:
  * attack patterns
  * failure patterns
  * test templates
  * narrow causal motifs
* **The pipeline:** `extract_incidents.py` harvests recurring incidents from debate logs and run artifacts, `draft_primitives.py` uses an LLM to draft candidate cards, and `approve_primitive.py` promotes or rejects them via human review.
* **The boundary:** These primitives are never evidence and never axioms. They are reusable adversarial precedents.

**Trade-off analysis:**
* **Reuse vs. overgeneralization:** A primitive library stops the system from rediscovering the same attack patterns repeatedly, but it creates a new risk: clean-looking abstractions that sound portable without being so. Promotion is therefore hybrid rather than automatic.
* **Python vs. LLM labor split:** Python extracts incidents and signatures; the LLM drafts candidate cards; the human decides whether a candidate is actually reusable and scoped well enough to approve.
* **Attack-side first:** To avoid overfitting or cross-domain contamination, primitives enter the engine on the attacker/judge side first. Mutator-side use is explicit opt-in and framed as `TRANSFER HYPOTHESES`, never as verified truths.
* **Precedent vs. evidence:** This preserves the distinction. `workspace/` stores project knowledge. `global_primitives/` stores cross-project precedents about how reasoning fails or how it should be attacked.

## 16. Evidence as an explicit substrate
**Context:** The original workflow treated `evidence.txt` as a manually authored project brief. That was workable for one-off runs but did not scale to iterative research. The same source material had to be recompiled by hand repeatedly, contradictions were easy to lose, and downstream failures were often traceable to upstream omission rather than to the validator.

**Decision: treat evidence as an explicit external layer, not an incidental file.**
* **The fix:** A three-stage evidence path:
  * `raw/` stores source material
  * `workspace/` stores structured, persistent project memory
  * `compiled_evidence.txt` is the bounded snapshot promoted into `evidence.txt` for the validator
* **The boundary:** This is an external improvement, not a change to the validator. ZTARE still consumes only a snapshot and remains stateless.

**What this achieved:**
* **From manual brief-writing to evidence operations:** Evidence is now a maintained substrate with provenance, contradiction preservation, open questions, and repeatable compilation.
* **Reproducibility:** A run can be traced back to a bounded compiled snapshot rather than an opaque human summarization step.
* **Incremental memory without trusted state:** The workspace can accumulate over time without giving the validator privileged access to prior accepted conclusions.
* **Compatibility with plain runs:** The new path does not force a new workflow. Existing projects can still run directly from manually curated `evidence.txt` with no primitives, no workspace, and no deterministic gates unless those are explicitly enabled.

**Interpretation:** A large share of apparent "engine" weakness was actually evidence-substrate weakness. Separating the two cleanly distinguishes kernel work from research infrastructure.

## 17. Converting failures into reusable constraints
**Context:** A recurring question was whether the recursive setup was producing knowledge or just more output. The answer became clearer after mining V3 and running early V4 loops.

**What was learned:**
* **V3 produced real architectural failures, not just noise.** The mining pass found durable failure classes: one-way decay masquerading as Bayesian learning, domain leakage into friendly simulations, weak score semantics, fragile credit assignment, and infallible-aggregator traps.
* **V4 surfaced a new loophole immediately.** Once score semantics were hardened, the loop found a subtler exploit: `self_referential_falsification`, where a thesis passes by proving only its own bookkeeping rather than its claimed mechanism.
* **The step that mattered was conversion, not detection.** That loophole was turned into:
  * a deterministic scoring guardrail in `test_thesis.py`
  * an approved reusable primitive in `global_primitives/approved/self_referential_falsification.json`

**Interpretation:** A run becomes knowledge-bearing when a discovered failure stops being an anecdote and becomes a reusable constraint on future runs. The engine does not need to produce new theories every iteration. It repeatedly does something narrower: expose a real failure mode, formalize it, and lower the chance of paying that cost twice.

## 18. Semantic outputs need semantic evaluation
**Context:** The first `constraint_memory` benchmark used keyword/phrase matching to decide whether the evaluator had identified a given exploit family. That was too brittle for LLM-generated judge output. A judge could correctly diagnose the mechanism in different words and still be counted as a miss.

**What went wrong:**
* **Default to string matching:** The initial benchmark treated evaluator output like a normal software log stream and used string matching. That is fine for fixed APIs and exact error codes, but not for semantic model judgments.
* **Same mistake the project studies:** The benchmark itself was vulnerable to the failure it is meant to detect: surface form was over-trusted, semantic substance was under-read.
* **Optimized for throughput, not meaning:** The infrastructure was built to run, isolate, and summarize results quickly, not to preserve the semantic meaning of the evaluator's diagnosis.

**Decision: add a lightweight LLM adjudicator as an optional measurement layer.**
* **The fix:** `benchmarks/constraint_memory/run_benchmark.py` supports `--adjudicator-model`, which asks a second model whether the judge semantically caught the expected exploit family.
* **The boundary:** The adjudicator does not change the evaluator, mutate the specimen, or replace the raw metrics. It is a measurement aid layered on top of the benchmark.
* **The rule:** Keep both signals:
  * heuristic detection for exact/obvious matches
  * adjudicated detection for semantic paraphrase

**Interpretation:** When the system under test is an LLM, the benchmark must account for semantic variance. Otherwise the measurement harness injects false negatives and degrades the paper's claim. Benchmark design for model judgments is part of the measurement, not just plumbing.

## 19. First constraint-memory benchmark result: gates help, primitives over-reject
**Context:** After adding corpus-derived bad specimens, good controls, and an optional semantic adjudicator, the first meaningful benchmark comparison across `A_baseline_soft_judge`, `B_deterministic_gates`, and `C_gates_plus_primitives` became interpretable.

**What the result showed:**
* **Deterministic gates were the clearest gain.** The hardened evaluator eliminated the remaining false accepts the soft judge still allowed.
* **The semantic adjudicator was necessary.** Several genuine semantic catches were invisible to keyword matching and only became visible once the benchmark accounted for paraphrase.
* **Primitives did not yet earn an empirical win.** `C` matched or underperformed `B` and over-rejected the positive controls.
* **The benchmark surfaced an over-rejection failure mode.** The primitive-armed evaluator treated any dependence on upstream signals as a trust leak, even when the thesis claimed only a narrow, local deterministic mapping.

**Decision: separate taxonomy hits from structural kills and add a safe harbor.**
* **Dual detection metrics:** The benchmark distinguishes:
  * exploit-family detection
  * acceptable fatal structural detection
* **Evidentiary safe harbor:** The rubric and judge contract protect bounded local components that:
  * disclaim upstream truthfulness
  * implement only a deterministic mapping or fail-closed gate
  * fully test that local contract
  * do not inflate the local proof into a whole-system guarantee

**Interpretation:** Score hardening is already defensible; adversarial memory still needs calibration. That separation is the kind of empirical result the systems paper needs.

## 20. First corpus result where `C` beat `B`
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

**Why it matters:**
* `B` still falsely accepted `t2_ai_inference` after the cleanup.
* `C` did not.
* `C` kept the `0.0` false reject rate on the good controls while restoring full structural detection.

**Interpretation:**
This is the first corpus-derived win for the primitives layer. It is stronger than the earlier calibration runs because it no longer depends on synthetic variants or on the regime where `C` over-rejected good controls. It is still a single stochastic run. The conclusion is:
* the `C > B` claim is now empirically plausible on the real corpus
* but it should be replicated across additional identical reruns before being treated as stable

## 21. A failure mode inside the evaluator itself
**Context:** After building the separate `claim_test_mismatch` mini-suite from historical runs, a new failure mode appeared inside the primitive-armed evaluator. The blind spot was in its own detection logic, not in the thesis under test.

**Key evidence:** `benchmarks/constraint_memory/runs/20260404_213459`
* `selective_rigor_recursive_bayesian`
  * `B_deterministic_gates`: passed at `100`
  * `C_gates_plus_primitives`: failed at `0`
* `selective_rigor_simulation_god`
  * `B_deterministic_gates`: capped to `25`
  * `C_gates_plus_primitives`: passed at `100`

**What happened:**
* The score contract was not the problem. It behaved as designed.
* The failure was **detection-level**:
  * under `B`, `simulation_god` was marked `proof_is_self_referential = true`
  * under `C`, the same specimen was marked `proof_is_self_referential = false`
* Primitives changed the judge's initial reading of the thesis. They helped on one selective-rigor specimen and hurt on another.

**Decision: treat this as an architecture finding, not just a benchmark result.**
* **New rule:** primitives should not shape the judge's first-pass identification of the crux.
* **Implication:** the evaluator should identify the central claim / eigenquestion first, test whether the suite targets that claim, and only then consult precedent memory.
* **Reasoning:** front-loading precedent memory can bias the detector toward accepting peripheral rigor as substantive proof.

**Interpretation:** This is the `failure -> diagnosis -> constraint` loop that motivates the second paper. The engine used its own benchmark output to find a blind spot in its own evaluation logic, and that blind spot became a new architectural constraint for the next version.

## 22. Ordering is family-specific; the improvement loop is human-in-the-loop
**Context:** After implementing the experimental `C2_gates_plus_primitives_crux_first` condition, the benchmark was rerun on both the narrow `claim_test_mismatch` suite and the broader main suite.

**Key evidence:**
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

**What this means:**
* No single primitive-ordering policy dominates across exploit families.
* `crux-first` helps on **claim-test mismatch / selective rigor** failures.
* the current default `C` remains better on the broader mixed-family main suite.
* the next architecture should not assume a universal ordering; it should route primitive application in a **family-aware** way.

**Interpretation:**
* `A -> B`: deterministic gates fix score-channel corruption.
* `B -> C`: primitives improve overall evaluator utility on the main suite.
* `C vs C2`: ordering matters, but the benefit is exploit-family-specific rather than globally dominant.
* this is a more precise result than a flat "C2 is better" claim.

**Methodological note:**
This improvement loop was **human-in-the-loop**, not autonomous self-rewriting by ZTARE. The methodology is:
* observe system failure
* diagnose it
* convert the failure into an explicit architectural constraint
* re-evaluate the modified system

The evidence supports a repeatable systems-engineering process, not a claim of fully autonomous self-improvement. *Adversarial Precedent Memory* should state it that way.

## 23. Keep topological pivot for exploration; add a bounded V4 mutation path
**Context:** After reseeding `projects/epistemic_engine_v4/` around semantic-gate stabilization, the first live run drifted back into the legacy stagnation machinery. Once stagnation rose, `autoresearch_loop.py` injected the old blank-slate / topological-pivot prompt stack and the mutator started proposing unrelated architectures (`Token Distribution Entropy`, `DisputeEngine`) instead of staying inside the bounded V4 kernel experiment.

**Decision:** Keep the legacy topological-pivot logic for open-ended exploratory projects, and add a V4-specific mutation path that disables blank-slate pivots and constrains mutations to the active mechanism under test.

**Trade-off analysis:**
* **Exploration vs. attribution:** The topological-pivot operator is useful when the problem is underdefined and the main risk is being trapped in the wrong ontology. It is the wrong tool for measuring whether one bounded evaluator change improves benchmark behavior. Keeping it globally preserves search breadth; disabling it for V4 restores causal attribution.
* **Novelty vs. benchmark hygiene:** The old stagnation path surfaces new designs. For V4 that contaminates the item-1 test with unrelated mechanisms. The bounded V4 path trades search breadth for cleaner recursive-hardening evidence.
* **One loop vs. mode-specific discipline:** A single stagnation strategy is simpler but assumes every project is still in ontology-search mode. The V4 branch adds slight code complexity but matches the difference between exploratory research and contract-governed evaluator hardening.

**Implementation consequence:** `src/ztare/validator/autoresearch_loop.py` now special-cases `epistemic_engine_v4`:
* no blank-slate purge
* no forced `Z = f(X, Y)` / laws-of-physics / logic-DAG pivot prompt
* stagnation feedback is preserved
* mutation is constrained to:
  * typed semantic evidence fields
  * Python-derived gate logic
  * unresolved-handling rules
  * interface stubs only

**Interpretation:** Topological pivot is a good exploration operator for general-purpose projects but the wrong operator for a benchmark-anchored kernel experiment. V4 gets a narrower mutation regime so recursive improvement stays measurable.

## 24. Keep layer names distinct even when the pattern recurs
**Context:** As V4 hardening, supervisor routing, and *The Cognitive Firm* matured, the same governance pattern appeared at multiple layers. Calling every deterministic orchestrator a "meta-runner" or every governance surface a "supervisor" would make the architecture harder to read as it grew.

**Decision:** Keep the names layer-specific:
* **ZTARE validator** = adversarial domain-validation loop
* **V4 kernel** = evaluator under hardening
* **meta-runner** = kernel-local deterministic promotion runner for V4 stage advancement
* **supervisor** = multi-program control plane for bounded work packets
* **paper bundles** = public-facing publication layer

**Trade-off analysis:**
* **Precision vs. brevity:** Reusing one name everywhere is shorter but blurs responsibilities. Distinct names are more verbose but more operable.
* **Reused pattern vs. interchangeable parts:** The same generation/evaluation separation recurs across layers, but the runtime components are not interchangeable.

**Interpretation:** The structure repeats; the terminology should not. The control plane is not the kernel, and the papers are not runtime governance.

## 25. The supervisor is governance, not truth
**Context:** Once the supervisor could route bounded programs end-to-end, there was pressure to use it as a general engine for research, prose generation, and semantic judgment. That would have duplicated the validator and softened the boundary between routing and evaluation.

**Decision:** The supervisor remains a deterministic governance layer only. It may:
* route bounded packets
* enforce write scope
* own commit authority
* stop at human gates

It may not become:
* a truth engine
* a novelty scorer
* a generic semantic judge

**Trade-off analysis:**
* **Operational leverage vs. boundary loss:** Letting the supervisor absorb semantic judgment would simplify the operator interface but create a second soft evaluator surface and collapse the separation the stack is designed to keep.
* **Bounding work vs. scope creep:** The supervisor earns its keep by bounding work and preserving provenance. It loses that value if it becomes another model-mediated judge.

**Interpretation:** The supervisor improves execution discipline around kernel and research work. It does not replace the kernel or ZTARE.

## 26. *The Cognitive Firm*: archived supervisor experiment plus a live direct-writing manuscript
**Context:** The supervisor-era *The Cognitive Firm* packet workflow eventually produced real evidence and usable sections, but the cost of continuing manuscript production inside the factory stayed too high relative to prose quality and operator attention.

**Decision:** Soft-decommission *The Cognitive Firm* as an active supervisor program.
* keep the supervisor-era artifacts as archived provenance
* keep the evidence for the paper's governance claims
* move the canonical live manuscript to direct-writing mode

**Canonical live outputs:**
* `research_areas/drafts/paper4_full_working.md`
* `papers/paper4/main.tex`

**Archived provenance:**
* `research_areas/_archive/paper4_supervisor/`

**Trade-off analysis:**
* **Procedural symmetry vs. paper quality:** Finishing the paper inside the supervisor would have kept the workflow uniform, but the marginal prose gain was poor and the operational cost was high.
* **Deletion vs. provenance:** Deleting the supervisor-era artifacts would have made the repo cleaner at the cost of erasing the evidence *The Cognitive Firm* depends on. Archiving keeps the record off the active critical path.

**Interpretation:** The *The Cognitive Firm* result survives the decommission. The supervisor-era workflow became evidence and archival provenance; the manuscript moved back to a lighter writing mode.

## 27. Public paper bundles live under `papers/`; root `paperN/` directories are scratch
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

**Trade-off analysis:**
* **Convenience vs. cleanliness:** Working directly in one local TeX directory is convenient, but publishing that entire workspace would leak build products and drafting artifacts into the public repo.
* **Minimality vs. completeness:** Public bundles should stay lean. The point is source visibility and reusability, not preservation of every local compile byproduct.

**Interpretation:** GitHub should show the papers as clean source bundles. The local build directories remain useful, but they are not the public artifact.

## 28. Future runtime-eligible work starts as a seed, not as public docs or debate
**Context:** Two feature notes exposed the same repository-structure mistake: `supervisor_artifact_lifecycle` and `vnext_semantic_gate_stabilization` were initially written in `docs/` or debate-adjacent locations even though they were really candidate future programs the supervisor might execute later.

**Decision:** If a note is meant to become future bounded work, it belongs first in `research_areas/seeds/`, not in `docs/` and not in `research_areas/debates/`.

**Trade-off analysis:**
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

### Cross-cutting concerns deferred (avoid premature merging)
- `translation_diff` + `domain_match` merge candidate: deferred.
  Keep separate during v5.0; merge later when Lean tooling stabilizes.
- `proof_surveyability` + `ansatz_survivor` composability (filter +
  ranker): deferred. Both wired during v5.0; fold post-v5.0.

### Substrate-class taxonomy expanded
Panel surfaced three additional classes the v5.0 spec missed:
- `proof_target` (Lean / formal-proof, [GP-122](research_areas/seams/apparatus/engine/GP-122_millennium_debate_log.md)/GP-139)
- `closed_form_constant` (PSLQ, [GP-145](research_areas/seams/engine/ns/GP-145_saw_mu_square_seam.md))
- `time_series_chaotic` (chaotic subset of time_series, [GP-143](research_areas/seams/engine/GP-143_continuous_chaotic_kernel_integration_seam.md)/146)

These augment the original {1d, nd_features, time_series, audit,
literature} → 8 substrate classes the v5.0 Cage routes against.

Full panel transcript appended to [GP-157](research_areas/seams/apparatus/cage/GP-157_R10_R16_backport_scoping_2026_05_06.md) seam.
Verified by 70/70 tests + 33/33 arch-map claims green.
