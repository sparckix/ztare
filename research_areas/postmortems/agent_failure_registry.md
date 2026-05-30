# Agent Failure Registry

Systematic catalog of Claude and Codex implementation/process failures across the ZTARE project. Purpose: extract meta-patterns and derive standing rules to prevent recurrence.

**Last updated:** 2026-04-20

---

## Failure 1: Edited Frozen Scoring Sheet

**Agent:** Claude
**Context:** GP-023 Phase 2 post-run analysis
**What happened:** User asked to update the GP-023 Phase 2 classification. Claude edited the frozen `post_run_scoring_sheet.md` directly instead of creating a separate post-mortem artifact.
**User caught it:** Yes — "shouldnt we create new scaffold because we had to freeze the phase 2 results"
**Root cause:** Claude treated scoring sheets as living documents. Did not internalize that sealed post-run artifacts are immutable historical records.
**Impact:** Low (caught before any downstream consumer read the modified sheet; reverted).
**Pattern:** **Frozen artifact violation** — modifying a sealed artifact instead of creating a correction artifact alongside it.

---

## Failure 2: Created Addendum Instead of Post-Mortem

**Agent:** Claude
**Context:** GP-023 Phase 2 correction
**What happened:** After being told not to edit the scoring sheet, Claude created a "scoring addendum" instead of a post-mortem. The addendum format was not a recognized artifact type in the project.
**User caught it:** Yes — "why u created scoring addendum? is this supposed to be post mortem?"
**Root cause:** Claude invented a new artifact type instead of using the established correction artifact (post-mortem). Did not check existing patterns before creating a new one.
**Impact:** Low (renamed to post-mortem).
**Pattern:** **Artifact type invention** — creating a novel artifact format instead of using the project's existing vocabulary.

---

## Failure 3: Findings Runner Code Duplication (~95% reimplementation)

**Agent:** Codex (implementation), Claude (architectural framing accepted the seam)
**Context:** GP-031 findings runner first-slice implementation
**What happened:** The GP-031 seam explicitly stated "reuses ~70% of the supervisor; adds ~30% as sibling primitives." The actual implementation (`supervisor_findings_runner.py`, 672 lines) reimplemented ~95% of the stack:
- Router: reimplemented (not reused from supervisor)
- Write-scope: absent (not reused)
- Human gates: reimplemented as `RunnerStopReason` (not reused `HumanGateReason`)
- Wrapper transport: reimplemented as bespoke `call_claude()`/`call_gemini()` (~80 lines each, duplicating `supervisor_wrappers.py`)
- Only cost tracking and refinement caps landed as designed.
**User caught it:** Yes — "it seems u duplicated instead"
**Root cause:** First-slice shortcut to avoid touching the supervisor during a live Planck run. The shortcut was reasonable at the time but should have been flagged as a debt.
**Impact:** Medium — opened GP-036 seam to converge the two systems; until resolved, the project has two parallel implementations of the same stack.
**Pattern:** **Seam promise vs. implementation divergence** — the architectural contract said 70/30 reuse, the implementation delivered 5/95 reuse.

---

## Failure 4: test_model.py Contaminated During Verification

**Agent:** Claude
**Context:** GP-037 substrate-swap sandbox construction
**What happened:** The naive seed `test_model.py` (deliberately wrong: `A * phi^p + offset`) was overwritten during fit primitive verification. The file on disk became a partially-correct mutant (`A * (phi/psi)^P * exp(-B*phi/psi) + Offset` with fitted params). Claude then sealed the pre-registration claiming the smoke gate was verified (test_model.py exits non-zero), but the contaminated file actually exits 0.
**Caught by:** Codex peer review.
**Root cause:** Ran the fit primitive against the sandbox as a verification step, which overwrote the seed file. Did not restore the seed after verification.
**Impact:** High — the pre-registration was sealed with a false smoke-gate claim. If the run had executed, it would have started from a partially-solved state, invalidating the experiment.
**Pattern:** **Verification side-effect contamination** — testing a tool against a sandbox modifies the sandbox, and the modification is not rolled back.

---

## Failure 5: GP-035 Contract Silently Weakened

**Agent:** Claude
**Context:** GP-035 fit primitive implementation
**What happened:** The GP-035 spec (constraint 8) says: "Slice 1 must not try to recover the intended functional form by heuristically parsing arbitrary thesis prose. The candidate must expose an explicit machine-readable fit declaration." But the implementation made FIT_DECLARATION optional — printing "no FIT_DECLARATION block found, skipping" — and the prompt told the LLM "If you omit the fit_declaration block, your guessed parameters will be used as-is."
**Caught by:** Codex peer review.
**Root cause:** Claude softened the spec requirement during implementation to be "safe" (don't break candidates that don't include the block). But this turned the 3b experiment from a clean verifier of the fit primitive into a mixed-condition experiment.
**Impact:** High — would have invalidated the 3b verifier's scientific claim (can't prove the fit primitive was the differentiator if the mutator can succeed without it).
**Pattern:** **Spec-to-implementation softening** — weakening a hard requirement to a best-effort during implementation, without updating the spec or flagging the divergence.

---

## Failure 6: Fit Result Not Auditable (Overwrite-per-Iteration)

**Agent:** Claude
**Context:** GP-035 fit primitive implementation
**What happened:** `workspace/fit_result.json` was written as a single mutable file overwritten each iteration. The pre-registration's success criterion ("the fit primitive produced the fitted parameters") required proving which iteration's fit result the champion used. A later failed iteration could erase the champion iteration's fit record.
**Caught by:** Codex peer review.
**Root cause:** Implemented the simplest thing (one file) without considering the auditability requirement in the pre-registration.
**Impact:** Medium — would have made post-run success criterion 3 unverifiable.
**Pattern:** **Audit trail gap** — building a tool that records current state but not history, in a context where history is the auditable claim.

---

## Failure 7: Pre-Registration Sealed with Imprecise Bindings

**Agent:** Claude
**Context:** GP-037 pre-registration seal
**What happened:** The sealed run commands did not pin `--mutator_model gemini --judge_model gemini`, relying on implicit defaults. The timestamp was approximate ("~22:00Z"). The rubric path was written as `rubrics/gp037_substrate_swap_01.json` but the CLI adds `rubrics/` and `.json` automatically, causing a double-path error.
**Caught by:** Codex peer review + runtime error on first run attempt.
**Root cause:** Did not verify the sealed commands would actually execute. Did not use a concrete timestamp. Did not check the CLI's argument processing before writing the commands.
**Impact:** Medium — the run would have failed immediately on the double-path issue; the model defaulting is a reproducibility concern.
**Pattern:** **Unverified seal** — sealing a pre-registration without dry-running the sealed commands.

---

## Failure 8: Fitter Accepts Wrong-Dimensionality Declarations

**Agent:** Claude
**Context:** GP-035 fit primitive implementation
**What happened:** A FIT_DECLARATION with `independent_vars: ["phi"]` on a 2-variable (phi, psi) sandbox returned `FitSuccess` with absurd parameters (max residual ~5.21). The fitter optimized the wrong objective because it collapsed all sweeps into a single mixed dataset.
**Caught by:** Codex peer review (verified locally).
**Root cause:** `parse_evidence_for_fitting()` was designed to support both 1-var and 2-var evidence. But for a 2-var sandbox, accepting a 1-var declaration is mathematically invalid — the fitter ignores psi and fits a single curve through mixed-sweep data.
**Impact:** High — a phi-only model cannot satisfy the charter's nonlinear phi-psi coupling requirement, but the fitter would mark it as a success, confusing the mutator and wasting iterations.
**Pattern:** **Missing input validation** — the fitter was permissive by default when it should have been strict about matching the project's dimensionality.

---

## Failure 9: Approved Incorrect Numbers in Public-Facing Draft

**Agent:** Claude
**Context:** Roadshow X thread drafting
**What happened:** Approved "Soft LLM judges caught 0/9. Adversarial deterministic execution caught 9/9." without checking the paper's actual detection tables. Real results were more nuanced.
**Root cause:** Treated the user's draft numbers as pre-verified instead of checking the source.
**Impact:** High — published with unverified numbers.
**Pattern:** **Verification skip on approval** — approving a claim by default instead of checking the source, especially for quantitative claims that go public.

---

## Failure 10: Human-Readable Charter Did Not Bind the Machine Contract

**Agent:** Claude
**Context:** GP-037 substrate-swap 3b smoke launch
**What happened:** The sandbox charter described deterministic gates in a human-readable section (`## Deterministic Gates (GP-030)` plus a markdown table), but the GP-030 parser only accepts an exact `## Deterministic Gates` heading plus a fenced YAML-ish `deterministic_gates:` block. The run launched anyway. During the live smoke, `latest_eval_results.json` showed `deterministic_charter_gates.declared = []` and `harness_invoked = false`, meaning the verifier layer was silently inert.
**Caught by:** Codex during live smoke review.
**Root cause:** Construction-time seal discipline validated the human intention of the charter, not the actual machine path that binds the evaluator. The charter “looked right” but was not parseable by the narrow contract.
**Impact:** High — the 3b smoke was invalid as a verifier run. It exercised the mutator/fitter but not the intended GP-030 gate surface.
**Pattern:** **Human contract vs machine contract drift** — a prose artifact appears to declare a rule, but the executable parser disagrees, and the run proceeds without the enforcement layer actually binding.

---

## Failure 11: "Domain-General" Implementation Contaminated by Problem-Specific Artifacts

**Agent:** Claude
**Context:** GP-037 form-family escape — residual pattern diagnostic implementation
**What happened:** User explicitly requested "genuine kernel engineering, not quick wins" and specifically rejected a prescriptive prompt hint as "overfitting." Claude implemented a residual diagnostic in `fit_primitive.py` (correct direction) but made four mistakes that contradicted the user's stated requirement:

1. Left a GP-037-specific worked example in the FIT_DECLARATION prompt (`autoresearch_loop.py:1347`): the example expression was literally `A * phi**p * exp(-b * phi/psi) / (1 + d * (phi/psi)**e) + offset` — the exact generating function the mutator needed to discover. This is not "domain-general"; it is the answer sheet.
2. The diagnostic's INTERPRETATION text crossed from observation into prescription: "Adding parameters to the current form family will not fix this — consider a fundamentally different functional form." That steers search policy, not just surfaces structure.
3. Injected the diagnostic on every successful fit, including near-passes and acceptable fits. No gate on whether the residual was materially bad.
4. The classifier had no magnitude threshold — it would classify numerical noise as `structural_misfit` if correlation happened to be high.

**Caught by:** Codex peer review (all four findings).
**Root cause:** **Solving the instance while claiming to build the abstraction.** Claude was mentally anchored on GP-037's specific failure (mutator stuck in `power * exp(-)` family, needs saturation denominator) and leaked that anchoring into three separate artifacts: the worked example, the prescriptive language, and the unconditional injection. The user's instruction to build kernel engineering was acknowledged but not internalized — the implementation was shaped by "what would fix GP-037" rather than "what is a domain-general diagnostic."
**Impact:** Medium — if deployed, the worked example would have been a direct answer hint (undermining the 3b experiment's validity), and the prescriptive text would have steered the mutator rather than informing it.
**Pattern:** **Instance-anchored generalization** — when asked to build a general tool motivated by a specific failure, the specific failure leaks into the implementation through examples, language, and default behavior that assume the motivating case is the typical case.

**Addendum (same session):** When Codex flagged the GP-037-specific example, Claude's fix was to replace it with a different specific example (`A * exp(-b*x) + c * sin(d*x) + offset`) instead of removing the domain baggage or reducing to a schema stub. Same pattern: treated the problem as "wrong content" rather than "wrong layering." Also missed the `I_model(phi, psi, params)` line (autoresearch_loop.py:1358 at the time) which was the real sandbox-shaped baggage — the fitter doesn't require that function signature, it only needs MODEL_PARAMS key matching. Codex caught and fixed both. The root cause is the same: anchored on replacing content rather than questioning whether the content belongs in the prompt at all.

---

## Failure 12: Frustration-Anchored Diagnosis (GP-041 Fix B)

**Agent:** Claude
**Context:** GP-041 seam opening — form-family escape after GP-037 3b 10-iter run
**What happened:** After 10 iterations of the mutator failing to escape the `power * exp(-)` basin, Claude opened GP-041 and proposed two fixes: Fix A (optimizer initialization) and Fix B (structural diversity injection — inject rational/Hill/Michaelis-Menten templates when `structural_misfit` fires). Gemini Pro, given only the clean problem statement with no run history, immediately identified Fix B as overfitting: it hands the mutator a multiple-choice menu of form families, destroying the discovery claim.
**User caught it:** Via Gemini Pro review.
**Root cause:** The 10-iter grind created a motivating frustration ("the mutator can't find rational forms") that leaked into the fix prescription. Fix B reflected what Claude *wanted to happen* (structural diversity) rather than what the data showed (optimizer initialization failure on forms the mutator had already discovered). Same root as Pattern 7 but at the diagnosis layer rather than the implementation layer: the frustrated observer context biased the fix toward "push the mutator harder" instead of "fix the tool that failed when the mutator was right."
**Impact:** Low — caught before implementation. GP-041 seam corrected: Fix B struck, Fix A refined.
**Pattern:** **Frustration-anchored diagnosis** — accumulated run context (repeated failures, pivots, regressions) biases the failure analysis toward "need more signal to the LLM" when the actual bottleneck is a downstream mechanical failure. Less context produced clearer reasoning.

---

## Meta-Pattern Analysis

### Pattern 1: Spec-to-Implementation Drift
**Failures:** 3, 5, 8
**Rule:** When implementing a spec, every MUST/REQUIRED constraint must map to a code path that enforces or rejects. If implementation softens a constraint, flag it explicitly and update the spec. Never silently downgrade REQUIRED to best-effort.

### Pattern 2: Verification Side Effects
**Failures:** 4, 7
**Rule:** Testing/verifying a tool against a sandbox is a destructive operation. Always restore sandbox state after verification. Dry-run sealed commands before sealing.

### Pattern 3: Frozen Artifact Discipline
**Failures:** 1, 2
**Rule:** Sealed artifacts are immutable. Corrections go in post-mortems. Don't invent new artifact types — use the project's existing vocabulary.

### Pattern 4: Audit Trail by Default
**Failures:** 6
**Rule:** Any artifact that could be needed for post-run claims must be immutably versioned (per-iteration snapshots), not just overwritten.

### Pattern 5: Verify Before Approve/Seal
**Failures:** 7, 9
**Rule:** Never seal a pre-registration without dry-running the commands. Never approve quantitative claims without checking the source.

### Pattern 6: End-to-End Seal Validation
**Failures:** 10
**Rule:** A verifier experiment is not sealed unless the full machine path is validated end-to-end: parser returns declared gates, harness emits payloads for those gates, and a real evaluation artifact shows the gate layer engaged. Human-readable charter language is not enough.

### Pattern 7: Instance-Anchored Generalization
**Failures:** 11
**Rule:** When building a general tool motivated by a specific failure, audit every artifact (examples, default text, injection conditions, thresholds) for leakage from the motivating instance. The test: would this implementation behave correctly on a problem you have never seen? If any artifact contains structure from the specific case, it is not general yet.

### Pattern 9: Frustration-Anchored Diagnosis
**Failures:** 12
**Rule:** When diagnosing a failure after many iterations of context accumulation, check whether the fix prescription is shaped by what you want to happen rather than what the data shows. Accumulated run frustration biases toward "give the LLM more signal" even when the actual bottleneck is a downstream mechanical failure the LLM already cleared. The test: would a reviewer with only the clean problem statement reach the same diagnosis? If not, the accumulated context is contaminating the analysis.

### Pattern 8: Symptom Fix Without Root-Cause Trace
**Failures:** 11 (addendum — prompt position fix), 11 (second addendum — pivot-mode survival)
**Rule:** Before touching any prompt injection, trace the full render path: rubric flag → conditional → assembled prompt, for both first iteration (no prior state) and subsequent iterations (with prior state). Ask "does this block render at all, and under what conditions?" before asking "where does it appear?" Fixing position when the block doesn't render is not a fix. Extended rule: tracing must cover ALL execution branches — not just iter 1 vs iter N, but also mode branches (normal, stagnation pivot, emergency pivot). A block that renders in normal mode but gets attention-hijacked in pivot mode is not enforced.

**Second addendum (same session — pivot-mode survival):** After Codex fixed the `if fit_context` conditional (correct), FIT_DECLARATION was still dropping on pivot iterations (stagnation ≥ 3). Root cause: pivot mode overwrites `task_header` and `document_context` with emergency banners that dominate model attention. `fit_primitive_context` was placed between `weakest_point` and `style_guide` — visible in normal mode, buried in pivot mode. Neither Claude nor Codex asked "does this survive pivot mode?" The fix was to append the requirement to `output_requirements`, which is the model's output checklist and is read in all modes. Rule extension: MANDATORY output requirements belong in `output_requirements`, not only in a contextual block that competes with mode-specific attention hijacks.

---

## Proposed AGENTS.md Additions

Based on these patterns, the following rules should be considered for addition to AGENTS.md:

1. **Spec fidelity rule:** When implementing a spec, every MUST/REQUIRED constraint must have a corresponding enforcement path in code. If a constraint is softened during implementation, the spec must be updated and the deviation flagged in the seam. Silent downgrade from REQUIRED to best-effort is a process failure.

2. **Sandbox restoration rule:** After testing or verifying a tool against a sandbox, restore the sandbox to its pre-test state. Verification is a read operation on the sandbox, not a write.

3. **Dry-run sealed commands rule:** Before sealing a pre-registration, execute the sealed commands in a mode that verifies they parse and start (e.g., `--iters 1` dry run). Pin all implicit defaults (model family, rubric path resolution) explicitly.

4. **Immutable audit trail rule:** Any workspace artifact referenced in a pre-registration's success criteria must be versioned per-iteration (not just overwritten). The champion's version must be separately preserved at promotion time.

5. **Artifact vocabulary rule:** Do not invent new artifact types (addenda, supplements, etc.). Use the project's existing correction artifact (post-mortem) for corrections to sealed artifacts.

6. **End-to-end seal validation rule:** Do not declare a project charter sealed until the full machine path is verified: parser extracts gates, harness loads and runs, evaluation artifact shows real pass/fail results. A charter whose format the parser silently ignores is inert, not sealed. (Origin: GP-037 postmortem, Meta-Pattern 6.)

7. **Instance-leakage audit rule:** When building a domain-general kernel primitive motivated by a specific failure, audit every artifact before shipping: examples, default text, injection conditions, and thresholds. If any artifact contains structure from the motivating case (worked examples that are the answer, prescriptive language that steers toward the known fix, unconditional injection that assumes every case is the bad case), it is not general yet. The test: would this behave correctly on a problem you have never seen? (Origin: GP-037 residual diagnostic postmortem, Meta-Pattern 7.)

8. **Prompt render-path trace rule:** Before touching any prompt injection (position, wording, gating), trace the full render path: rubric flag → conditional → assembled prompt, across iteration 1 (no prior state), iteration N (with prior state), AND all mode branches (normal, stagnation pivot, emergency pivot). The first question is "does this block render at all and under what conditions?" — not "where does it appear?" Fixing position when the block doesn't render on iteration 1 is not a fix. A block that renders in normal mode but gets buried by pivot-mode attention hijacks is also not enforced. MANDATORY output requirements belong in `output_requirements`, not only in a contextual block that competes with mode-specific banners. (Origin: GP-035 fit contract missing on first iteration + pivot-mode survival failure, Meta-Pattern 8.)

9. **Integration-validation rule:** Before declaring any integration "shipped end-to-end," run a three-item check: (a) load one real sample of each input the code will consume in production and pass it through the module, (b) open the real config file (rubric, settings, contract) and verify the exact key names match what the code reads, (c) grep every call site for fallback defaults (`.get("key", <default>)`) that still live one frame up the stack from a keyword-required parameter. Unit tests against self-authored synthetic payloads are self-consistency checks, not integration proof — when a real production artifact exists, at least one test must load it directly. A "no hardcoded default" rule is satisfied end-to-end at the integration boundary, not at the function signature. When a parallel worker owns the other side of a contract edge, grep their artifacts for the key names they already committed before coining new ones. (Origin: GP-048 apparatus-feedback integration failure, Meta-Pattern 11.)

---

## Failure 13: Sealed Before Completing Full Mutator-Visible Leak Audit

**Agent:** Codex
**Context:** GP-023 Phase 3 pre-run seal
**What happened:** Codex correctly verified the machine path and then repeatedly resealed the packet while still discovering prompt-surface leaks in mutator-visible files. The misses came in sequence: hidden-generator constants in `thesis.md` / `current_iteration.md`, then the same constant in `test_model.py`, then `Planck`/project-path leakage in `project_charter.md`, then hidden-basin tokens inside HTML comments in `thesis.md` / `current_iteration.md`.
**User caught it:** Yes, repeatedly, with external audit help.
**Root cause:** Codex audited the scoring surface more carefully than the mutator-visible surface. It treated `test_model.py` and `project_charter.md` primarily as machine-contract artifacts instead of prompt artifacts, and it treated comments/metadata as non-semantic.
**Impact:** High — would have invalidated the ontology-trap claim for Phase 3 if the run had launched on any of the earlier seals.
**Pattern:** **Prompt-surface audit failure** — sealing after local fixes without completing a literal full-packet sweep of every mutator-visible file for hidden-basin names, operator-side paths, and copied generator constants.

**Correction artifact:** `research_areas/private/postmortems/gp023_phase3_prompt_surface_contamination_2026_04_12.md`

### Pattern 10: Prompt-Surface Audit Before Seal
**Failures:** 13
**Rule:** Before sealing any contamination-sensitive sandbox, enumerate the full mutator-visible packet and grep every file for hidden-basin names, operator-side path strings, copied generator constants, and metadata comments. Do not reseal incrementally after partial fixes. The seal happens only after the whole packet passes in one sweep.

---

## Failure 14: Shipped GP-048 Apparatus-Feedback Integration Against an Imagined Schema

**Agent:** Claude
**Context:** GP-048 apparatus-feedback surfaces wired into `autoresearch_loop.py` for the rescoped sandbox_04 experiment.
**What happened:** Claude implemented three flag-gated feedback surfaces (telemetry, primitive-cohort injection, sanitized farther-tail veto) and declared them "shipped end-to-end" after an 18-test suite passed. Codex's pre-seal review found three blocking integration bugs: (1) `_failed_farther_tail_gates` read top-level payload keys when the real `latest_eval_results.json` nests gate results under `score_contract.deterministic_charter_gates.results`, so the veto would have silently returned `""` on a real payload; (2) the loop-side rubric flag names (`gp048_cone_injection`, `farther_tail_veto_injection`) did not match what Codex had already committed to `rubrics/gp023_planck_sandbox_04.json` (`gp048_stagnation_injection_mode`, `gp048_farther_tail_veto_mode`), so both prompt-injection surfaces would have stayed off under the real rubric; (3) Claude made `visible_threshold` keyword-required at the renderer signature and declared "no default," but the call site in `autoresearch_loop.py` still passed `rubric_data.get("gate_residual_threshold", 0.05)` — the hardcoded fallback was alive one frame up the stack. All three bugs shared one root cause: Claude validated each piece in isolation against a schema Claude imagined, not the real system. The 18-test suite used synthetic payloads Claude had authored; none of them loaded a real production artifact.

Separately, the operator caught three earlier draft bugs in the same session before Codex's review: descriptive gate names (`farther_tail_monotone`) rendered verbatim as a semantic leak, a hardcoded threshold string in the prompt template, and an operator-authored topology enumeration ("up / down / floor / oscillate") that spoon-fed candidate shapes to the mutator.

**User caught it:** Partially — operator caught the three draft bugs, Codex caught the three integration bugs. Claude's own "shipped" declaration caught zero of the six.
**Root cause:** Claude optimized against an imagined spec instead of the real one. Unit tests against self-authored synthetic inputs are self-consistency checks, not integration proof. A "no default" rule at the function signature is not the same as "no default" end-to-end. When a parallel worker (Codex) owned the other side of the contract edge, Claude coined new flag names without grepping Codex's rubric for the names already committed.
**Impact:** Counterfactually high — had sandbox_04 launched on Claude's first "shipped" declaration, the apparatus-feedback arm would have been silently inert and the run would have appeared to falsify H-GP023-02, H-GP023-03, and H-GP023-04 (apparatus-feedback hypotheses) when in fact the feedback surfaces never fired. This would have falsely strengthened the model-swap hypothesis H-GP023-01.
**Pattern:** **Integration against an imagined schema** — self-authored unit tests prove self-consistency but not integration; rule satisfaction at a function signature does not imply rule satisfaction end-to-end; contract edges with parallel workers require grep-the-other-side before coining new names.

**Correction artifact:** `research_areas/private/postmortems/gp048_apparatus_feedback_integration_failure_2026_04_13.md`

### Pattern 11: Three-Item Integration Check Before Declaring Shipped
**Failures:** 14 (and structurally the same class as the draft sanitization bugs caught inline in the same session)
**Rule:** Before declaring any integration "shipped end-to-end," run a three-item check in 2–3 minutes: (a) load one real sample of each input the code will consume in production and pass it through the module; (b) open the real config file and verify the exact key names the code reads; (c) grep every call site for fallback defaults (`.get("key", <default>)`) that still live one frame up the stack from a keyword-required parameter. When a real production artifact exists (a sample eval result, an existing rubric, a closed workspace), at least one test must load it directly rather than feeding the renderer a synthetic input Claude authored. When a parallel worker owns the other side of a contract edge, grep their artifacts for the key names already committed before coining new ones. Treat the operator's review as a direction check, not an integration check — the self-critique pass comes first.

---

## Failure 15: Missing Prompt Contract for New Execution Mode (GP-080 continuous_rmse)

**Agent:** Claude
**Context:** GP-080 Stage 1 — first continuous_rmse substrate run
**What happened:** The mutator prompt included a `DISCRETE EXACT-MATCH CONTRACT` block (gated by `fit_score_mode == "discrete_exact"`) telling it to write `def f()`. For `continuous_rmse` mode, no equivalent contract existed. The mutator wrote valid fit declarations but no callable function. The gate harness crashed with `test_model.py does not expose f()` on every iteration (0–2). Three prior fix sessions (Component C float cast, AST auto-alias for renamed functions, Component D var_name threading) all addressed real bugs at different layers but none traced the prompt path to discover the missing contract.
**User caught it:** After 3 burned iterations across two runs.
**Root cause:** New execution mode (`continuous_rmse`) was added as a `fit_score_mode` option without adding a parallel prompt contract. The discrete contract worked silently because it was the only mode that had ever been tested. The safety net (AST auto-alias) was designed for renamed functions, not absent functions — it found nothing to alias when the mutator wrote no function at all.
**Impact:** High — 3 burned iterations, multiple fix sessions, user frustration. Every iteration produced a fit with max residual 0.007 that was thrown away because the code had no callable.
**Pattern:** **Branch-incomplete prompt contract** (Pattern 12) + **Downstream symptom chasing** (compound of Patterns 8 and 9).

**Correction artifact:** `research_areas/private/postmortems/gp080_continuous_model_contract_missing_2026_04_17.md`

### Pattern 12: Branch-Complete Prompt Contracts
**Failures:** 15
**Rule:** Every rubric flag that switches a code path (`fit_score_mode`, `run-mode`, grammar variant) must have a corresponding prompt-contract block for **each value** the flag can take. A flag with two valid values needs two contract blocks, not one plus silence. When adding a new mode, check all existing prompt-contract blocks that assume the old mode and either generalize them or add parallel blocks. The test: for each value the flag can take, assemble the full prompt the mutator will receive and verify it contains every instruction needed for the harness to accept the output.

### Pattern 13: Downstream Symptom Chasing
**Failures:** 15 (three sessions of fixes at wrong layers)
**Rule:** When the same runtime error persists across multiple fix attempts, stop fixing downstream mechanisms and trace the signal path from the beginning: what does the prompt say → what does the LLM produce → what does the code expect? If three fixes at three different layers haven't resolved the error, the root cause is upstream of all three. The diagnostic heuristic: "if the fit primitive succeeds but the harness crashes, the problem is between the fit and the harness" — but in this case the problem was before the fit, in the prompt that never told the LLM what to produce.

---

## Failure 16: New Sandbox Harness Used argparse (GP-096 Run 1)

**Agent:** Claude (generate_substrate.py template) + manual gate_harness.py
**Context:** gp096_sandbox_19_gagorder — first 10-iteration run; every iteration logged fail_other
**What happened:** `gate_harness.py` was written with `argparse`. The loop passes `--run-visible-assertions`, `--eval_results_path`, and other flags that argparse rejected as unknown arguments (exit code 2). Every iteration returned fail_other before any assertion ran.
**User caught it:** After examining iteration 1 output.
**Root cause:** The harness template in `generate_substrate.py` used `argparse` from the start. Other sandbox harnesses used `sys.argv[1:]` pattern. New harness was not compared against existing working examples.
**Impact:** High — 10 iterations burned; no valid evaluation data.
**Pattern:** **Template inconsistency** (new Pattern 14 below) — new generated artifact does not match the interface contract that the consuming loop expects.

**Correction artifact:** `research_areas/private/postmortems/gp096_run1_infrastructure_bugs_2026_04_20.md`

---

## Failure 17: Rubric Generated With Numeric Parsimony Ceiling (GP-096 Run 1)

**Agent:** Claude (generate_substrate.py `_write_rubric`)
**Context:** gp096_sandbox_19_gagorder rubric generation; GP-103 violation identified by Gemini Pro mid-run
**What happened:** `_write_rubric` in continuous mode generated persona and criteria text with explicit numeric parameter ceilings ("3-parameter"). For a gag-order run designed to test multi-regime additive composites (8-12 parameters), this was a lethal trap: the judge would penalize structurally justified composites regardless of fit quality.
**User caught it:** Gemini Pro flagged it; user escalated.
**Root cause:** `_write_rubric` was written once for discrete mode and adapted for continuous without applying the GP-103 rejection checklist (no numeric parameter ceilings in rubric text). Phase 5 blocking gate did not exist in `make seal`.
**Impact:** High — rubric would have false-rejected valid multi-regime composites; retroactively fixed but first run already sealed with bad rubric.
**Pattern:** **GP-103 checklist not applied at generation time** (Pattern 12 variant) + **Missing seal-time gate** (new Pattern 15 below).

**Correction artifact:** `research_areas/private/postmortems/gp096_run1_infrastructure_bugs_2026_04_20.md`

---

## Failure 18: H-GP103-5 Seeds Missing Python Block — R1 Rejection Every Iteration

**Agent:** Claude (autoresearch_loop.py PHASE_A seed injection)
**Context:** gp096_sandbox_19_gagorder — H-GP103-5 (additive composite) fired; every seed was rejected at Runner R1
**What happened:** The PHASE_A seed injection path builds `new_content` as cleaned thesis + fit_declaration block only. No Python block was included. `_prepare_mutation_candidate` → `validate_python_suite_candidate(None)` → ValueError → R1 exit. Layer 3 Mandatory (PHASE_D, which would have built the Python block deterministically) never reached because PHASE_B rejected first.
**User caught it:** Noticed H-GP103-5 never produced a promoted candidate despite firing repeatedly.
**Root cause:** The seed injection path bypasses `mutate_thesis` entirely — no LLM is called. The INV-1 invariant (python_code_exists_before_fit) was satisfied for all LLM-generated paths but not for the deterministic seed injection path. The path was added without auditing all downstream invariants.
**Impact:** High — H-GP103-5 was silently dead for the entire first run.
**Pattern:** **New code path not audited against existing invariants** (new Pattern 16 below).

**Correction artifact:** `research_areas/private/postmortems/gp096_run1_infrastructure_bugs_2026_04_20.md`

---

## Failure 19: Composite Seeds Cold-Start Collapse — SciPy Kills Second Family

**Agent:** Claude (structural_memory.py + autoresearch_loop.py seed injection)
**Context:** gp096_sandbox_19_gagorder — after Bug 3 fixed; composite candidates all returned max|res|=1.79947 ± 0.0001 every iteration
**What happened:** H-GP103-5 composite seeds had no `initial_guesses`. SciPy defaulted p0=1.0 for all 8-12 parameters. For a multi-regime model spanning 5 log-decades (t ∈ [0.0001, 0.79]), the Jacobian is numerically singular at p0=1.0. SciPy escaped by collapsing the second family's amplitude to zero — reducing to a 6-parameter fit. The judge correctly penalized "zero gain from 8 extra parameters" — but the root cause was the optimizer, not the topology.
**User caught it:** Identical residual across 10 iterations flagged as deterministic attractor, not stochastic noise.
**Root cause:** `generate_additive_composite_seeds` was written without populating `initial_guesses`. The field exists in `FitDeclaration` and is used by `fit_parameters` — the interface was available but not wired. `update_structural_memory` did not store fitted params for retrieval.
**Impact:** High — epistemic contamination: judge rejected valid topologies because optimizer failed. False topology rejection → engine learns wrong lesson about which families generalise.
**Pattern:** **Interface field available but unwired** (Pattern 16 variant) + silent optimization failure masquerading as topology failure (new epistemic risk pattern).

**Correction artifact:** `research_areas/private/postmortems/gp096_run1_infrastructure_bugs_2026_04_20.md`

---

### Pattern 14: Template Inconsistency — Generated Artifacts Must Match Loop Interface
**Failures:** 16
**Rule:** When `generate_substrate.py` (or any scaffold generator) produces a new artifact, check it against **at least one working example** of the same artifact type before committing. The consuming loop's interface contract (which flags it passes, which exit codes it expects) must be satisfied by every generated instance. Add a smoke-test that pipes the same flags the loop uses to the generated harness and checks exit code 0.

### Pattern 15: Seal-Time Rubric Gate
**Failures:** 17
**Rule:** `make seal` must block if the rubric contains any string that would cause the judge to reject a structurally valid candidate. The GP-103 checklist (no numeric parameter ceilings, no domain-name leakage, parsimony = structural justification not count) must run automatically at seal time, not as a manual review step. If it can be caught by regex, it must be caught by regex before the run starts.

### Pattern 16: New Code Path — Audit All Downstream Invariants Before Shipping
**Failures:** 18, 19
**Rule:** When adding a new code path that bypasses an existing path (e.g., deterministic seed injection that skips `mutate_thesis`), enumerate every invariant the bypassed path satisfied and verify the new path satisfies each one. Invariants are not automatically inherited. The specific invariants to check for any new PHASE_A content-generation path: INV-1 (python block present), INV-2 (fit_declaration survives), INV-6 (parameter namespace unique), INV-8 (composite seeds have initial_guesses).
