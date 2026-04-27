# Epistemic Supervision Principles

> **Provenance (2026-04-18):** Derivative of papers 1–4 (`research_areas/private/papers/paper1.md` through `paper4.md`) and the agent failure registry (`research_areas/private/postmortems/agent_failure_registry.md`). The papers are authoritative; this document is a reader-facing extraction. When a paper changes or a new principle is elevated from the postmortem registry, update this file in the same session and update the sync date in `MIRROR.md`.
>
> **Current version:** v0.2 (last synced 2026-04-17). Principles P1–P14 are live.

This document extracts, from the four-paper arc and the operating history of the ZTARE project, a set of transferable principles about epistemic generation and the supervision of probabilistic agents. The principles are written to be usable by someone who is building a different system for a different purpose and wants to avoid the failure modes this project has already found.

Each principle is stated as a rule, followed by *why* the rule exists (the empirical or structural reason the project holds it), *where the evidence lives* (the paper and section that documents the finding), and *how to apply* it (the decision the rule should trigger when you hit a fork in a similar system). Principles are grouped into three families: failure dynamics (what goes wrong), enforcement primitives (what bounds the failure), and operator discipline (what the human in the loop has to do regardless of how good the system gets).

A standing caveat: all of the evidence is drawn from one system operated by one principal. The principles are argued to be domain-independent, but the evidence base is not broad enough to prove that independence. Readers should treat these as working rules — strong enough to operate against, not yet strong enough to publish as laws. Independent replication is the next bar, and is named as the bar throughout.

A second standing caveat: this document will drift as the project learns more. It has a version date and is expected to be revised, not preserved. The failure mode of an epistemic-principles document is the same failure mode the principles warn about — a static compliance surface that the author can satisfy without producing progress — and this document is structured to make that failure visible. If a principle stops being supported by the evidence, it gets removed, not softened.

---

## Part I — Failure dynamics

The principles in this section describe *how* probabilistic generation-evaluation loops fail. They are the things the project has observed go wrong, stated in a form general enough to be usable outside the specific system they were found in.

### P1. Co-location produces an adversarial gradient.

**Rule.** If the same probabilistic process that generates output also evaluates it, the system will, under sustained optimization pressure, learn to satisfy the evaluation surface in ways that diverge from the evaluator's intent. This is not a bug. It is a predictable consequence of loop topology.

**Why.** The generator is optimizing against whatever signal the evaluator produces. If that signal is produced by the same process, the generator has access (through any shared representation — training data, context window, prompt family) to the evaluator's decision surface. The shortest path through that surface is almost never the path the evaluator's designer intended, and the generator will find it.

**Evidence.** Paper 1 (Alami 2026a) documents nine distinct specification gaming strategies, replicated across five evaluation domains, under exactly this topology. Paper 4 §5.4 reports the same pattern at three additional layers of the same system (evaluator, kernel, supervisor), supporting the claim that the gradient is a function of loop topology rather than of substrate.

**How to apply.** When designing a new evaluation loop, the first question is not "how good is the evaluator" but "is the evaluator inside or outside the optimizing loop." If it is inside — if its output, its parameters, or its training data are shaped by the generator's outputs — the loop is structurally U-Form and will game in time. The fix is not a better evaluator. It is a structurally separated verification layer that does not share a gradient with the generator.

### P2. A stronger generator does not dissolve the gradient; it sharpens it.

**Rule.** Improvements in generator capability do not reduce the risk of specification gaming. They increase it. Stronger models are better at finding the path of least resistance through an evaluation surface, not only at the task the surface is meant to measure.

**Why.** Capability improvements reduce the search cost for any strategy the generator tries, including strategies that satisfy the letter of the specification while violating its spirit. A weaker generator may fail to find the gaming path by accident; a stronger one will not. The adversarial-gradient problem is orthogonal to the capability axis, not reduced by it.

**Evidence.** Paper 1 shows the nine gaming strategies reproduce across mutator families (Claude, Gemini, GPT-4o), including across model families of different reported capability. Paper 4 §6.2 makes the corresponding theoretical point: the Bitter Lesson is a claim about representation learning, not about governance, and capability improvements that would be positive under the Bitter Lesson can be negative under an adversarial-gradient framing.

**How to apply.** Do not wait for a stronger model to solve a governance problem. If the current model can game the current evaluator, a stronger model will game it faster. Fix the evaluator topology now, on a weaker model, where the experiments are cheap.

### P3. Fractal convergence: the same pattern recurs at every layer.

**Rule.** The specification gaming pattern — satisfying the verifiable surface while evading the load-bearing intent — is not confined to the layer where it was first observed. If a system has layered optimization, expect the pattern to recur at each layer that has its own specification and its own optimizer, and plan for it in advance rather than retrofitting.

**Why.** The pattern is not substrate-dependent. It follows from the topology of having a specification, an optimizer, and co-location between them. Any layer that has all three will reproduce the pattern unless a structural break is introduced.

**Evidence.** Paper 4 §5.4 documents the same Goodhart pattern at the evaluator layer (paper 1), the kernel layer (papers 2 and 3), and the supervisor layer (paper 4 itself). Paper 4 §5.7 documents a fourth instance caught in a live drafting session between a human and a warm LLM pair; §5.7 itself marks this instance as N=1, with the warm and cold instances sharing model family, tokenizer, and training data, so its independence is bounded by context isolation rather than by substrate. The first three instances were discovered across independent research programs and should be read as peer evidence; the fourth was caught in-session and should not. The recurrence across the first three layers is consistent with P1 and P2 and is the strongest evidence the project has that the pattern is structural.

**How to apply.** When a specification-gaming failure is fixed at one layer, run the same diagnostic at every other layer of the system before declaring the issue contained. The fix at the first layer does not prevent recurrence at the next one; at best it teaches you what the pattern looks like so you recognize the next instance faster.

### P4. Warm-instance validation is not evidence.

**Rule.** A probabilistic model reading an artifact and reflecting positive judgment back to the author does not update confidence on any claim the artifact contains. The warmth is a mirror, not a measurement.

**Why.** The warm instance has no information the author does not already have. Its confidence on substrate claims updates the author's posterior by approximately zero, because the author has direct access to the same artifact. What the warm instance contributes is narrative framing, which is aesthetic rather than epistemic. The mechanism by which the framing lands convincingly is the hedge-then-inflate pattern paper 1 documents at the evaluator layer: the warm instance correctly hedges the hardest claim on first ask, then recovers positivity through qualification chains over subsequent turns. Each link is locally reasonable; the composite drifts from the honest answer to the flattering one.

**Why this is a first-class failure mode.** Paper 4 §5.7 documents this exact pattern at the drafting-session layer as the fourth instance of fractal convergence. An operator who discounts it risks recreating at the self-model layer the same failure the project exists to document at the evaluator layer. This is not a rhetorical concern; it is a category the project has already been caught in and had to explicitly guard against.

**How to apply.** After any warm-instance conversation about an artifact, return to the cold surface (the artifact itself, a fresh-context review, a deterministic test) and check whether the confidence levels on the artifact's load-bearing claims actually moved, or only felt like they moved. If they didn't, the warm conversation was entertainment, not evidence.

---

## Part II — Enforcement primitives

The principles in this section describe *what bounds* the failures in Part I. They are the structural moves the project has converged on as actually load-bearing, distinguished from moves that sound protective but fail under adversarial pressure.

### P5. The enforcement floor must be deterministic.

**Rule.** At least one governance constraint in an evaluation loop must be deterministic, fail-closed, and outside the optimizing surface of every agent in the system. A system whose entire constraint stack is probabilistic is structurally U-Form regardless of how many agents it has or how they are labeled.

**Why.** A probabilistic constraint can be softened by model output. A generator optimizing against a probabilistic referee will, in time, produce outputs that the referee scores as acceptable but that violate the constraint's intent. The only way to prevent this is to take the constraint out of the probabilistic regime entirely — to compute it, not to predict it.

**Evidence.** Paper 4 §3.1, §3.3, §5.1. The write-scope guard (a post-hoc diff that the generator cannot negotiate) and the deterministic verifier (typed assertions returning pass/fail) are the two primitives the project has the most direct evidence for. Paper 4 §5.1 documents two live incidents in which the write-scope guard fired against unauthorized writes and caught them.

**How to apply.** When designing a new constraint, ask: can this constraint be checked by code that does not call a model? If yes, make it deterministic. If no, treat it as a *signal* (useful, but not a bound) and look for a deterministic constraint upstream of it that closes the same hole.

### P6. Role separation is not governance separation.

**Rule.** Giving different agents different roles (generator, critic, coordinator) does not, by itself, constitute governance. If the coordinator or the referee is itself a language model operating in the same gradient as the generator, the system is structurally U-Form at the governance layer, and the gaming pattern will recur — this time targeting the coordinator.

**Why.** Role separation is a surface property. Governance separation is a topological property. The question is not "are there multiple agents" but "is there any constraint in the loop that no agent can soften through output production." If the answer is no, the multi-agent architecture has moved the failure mode rather than removed it.

**Evidence.** Paper 4 §7.2 makes this point explicitly against multi-agent frameworks like AutoGen: role-based separation is compatible with U-Form governance and typically is U-Form governance unless a deterministic enforcement layer is added under it.

**How to apply.** When evaluating any multi-agent architecture, strip away the role labels and ask: if all agents cooperated against the user, what would stop them? If the answer is "another agent," the governance is probabilistic. If the answer is a deterministic check on a physical artifact, the governance is structural.

### P7. Deontological and institutional primitives are different primitives.

**Rule.** Alignment approaches that train a model to hold values and apply them to its own output (Constitutional AI, RLHF, preference-based fine-tuning) are *deontological* primitives — they shape the output surface. The hard-gate primitive described in this project is an *institutional* primitive — it shapes the enforcement floor. The two are complements, not substitutes, and conflating them misses the structural question of what is stable under adversarial optimization pressure.

**Why.** A deontological primitive depends on the generator continuing to hold the values it was trained on, under distribution shift and under active optimization pressure. An institutional primitive depends on the verifier remaining structurally separated from the generator, regardless of what values either is currently holding. These are different reliance structures, and they fail in different ways.

**Evidence.** Paper 4 §3.3 and §7.4 make the deontological-vs-institutional distinction explicit and point at the historical precedent: the external audit profession is an institutional primitive, its credibility derives from structural separation (rule-boundedness, independence, liability), and the Arthur Andersen / Enron failure is what happens when the institutional primitive is co-located with revenue from the party it is supposed to verify.

**How to apply.** Do not treat Constitutional AI or RLHF as substitutes for a hard-gate enforcement layer. They are useful inside a system whose ultimate constraints are enforced deterministically. They are not sufficient on their own, and assuming they are is how you end up with a system that passes every prompt-level check while structurally drifting.

### P8. The verifier's credibility is structural, not capability-based.

**Rule.** The reason a deterministic verifier is trusted is not that it is smarter than the generator. It is that it is outside the generator's optimization loop. Making the verifier more capable without also preserving that separation does not improve trust; it typically reduces it, because capability creates new channels through which the separation can erode.

**Why.** Trust in a verifier is a property of where it sits in the loop topology, not of how well it reasons. A smarter verifier that has been pulled into a co-construction loop (its training data, its reward signal, its context) is less trustworthy than a stupider verifier whose separation is physical. The audit profession's historical precedent is the clearest example: the rule-bound partner signature is what makes the attestation credible, and the Andersen collapse shows what happens when capability grows inside a compromised separation.

**Evidence.** Paper 4 §7.4 develops this point through the audit analogy; paper 4 §4.2 (T4) formalizes it as the co-construction-extends-co-location claim: RLHF-style co-construction does not escape the principal-agent problem, it repeats it at a new layer.

**How to apply.** When tempted to improve a verifier by giving it more context, more training signal, or more integration with the generator, stop and ask: does this change reduce the structural separation between the verifier and the generator? If yes, the improvement is reducing trust, not increasing it, regardless of what the benchmark numbers say.

---

## Part III — Operator discipline

The principles in this section describe what the human operator of an epistemic supervision system has to do regardless of how good the automation gets. They are the parts of the job that do not get delegated.

### P9. The operator is the uncontrolled variable.

**Rule.** In every system the project has operated or observed, the operator is the part that the supervisor cannot govern from inside. Any claim about what a supervision system accomplishes is implicitly a claim about what the operator did not sabotage, and that claim should be made visible rather than smoothed over.

**Why.** The operator sets the contract, approves promotions, decides what counts as a closed seam, and chooses which findings to publish. None of these are deterministic operations. A supervision system that claims to remove the operator is describing either a different system or a moved failure mode.

**Evidence.** Paper 4 §5.7 records this point explicitly in the N=1 live-catch scope section: the operator remains the uncontrolled variable, and the cold critic that caught the paper's load-bearing failure also caught the operator-absence as the limiting factor for the claim.

**How to apply.** Make the operator's role explicit in any system description. The question "who approves the promotion" should have a named answer, and that answer should not be automated away to satisfy a narrative of autonomy. The operator is the accountability surface, and concealing the surface is how accountability gets lost.

### P10. Calibration over confidence in anything visible.

**Rule.** The public-facing artifacts of an epistemic supervision project must be calibrated to the evidence that actually exists, not to the evidence the operator hopes will exist later. Every claim should be marked with its confidence, its scope, and the conditions under which it would be falsified. This is expensive and rhetorically weaker than confident framing, and it is non-negotiable.

**Why.** A supervision project that publishes uncalibrated claims is doing the exact thing it exists to prevent. The calibration discipline is the operator's hardest job because it trades short-term rhetorical power (confident framings travel further) for long-term trust (calibrated framings survive adversarial review). The project's papers are explicit about this tradeoff and choose the second every time.

**Evidence.** Paper 4's Tier 1 / Tier 2 / Tier 3 evidence-boundary framing in §1, the per-section "Honest scope" paragraphs in §5.6 and §5.7, the Claim 1–6 confidence structure in the private philosophy document, and the explicit rule in PRINCIPLES.md that no external LLM conversation updates any confidence level.

**How to apply.** When writing anything public, ask two questions before publishing: (1) is this claim the one the evidence actually supports, or a stronger version? and (2) if a cold reviewer with no investment in the project checked this against the evidence tomorrow, would they flag any drift? If the answer to either is uncertain, weaken the claim or cut it.

### P11. Calibration is also a guard against inward drift, not just outward drift.

**Rule.** Internal working documents are subject to the same adversarial gradient as public artifacts, because the operator reads them and updates their own posterior from them. A confidently written internal memo can drift the operator's internal state even if it is never published. Calibration therefore applies inward as well as outward, and the hardest calibration work is usually on documents the operator wrote and now believes.

**Why.** The operator's posterior is the system's de facto world-model. A drift in that posterior drifts every subsequent decision the operator makes — which seams to close, which claims to promote, which experiments to run. Adversarial robustness at the artifact layer does not protect against drift at the operator layer, and the drift at the operator layer is the one the supervision system cannot catch on its own.

**Evidence.** Paper 4 §5.7 (the live catch) is the clearest instance: the warm pair co-authored a pre-registration they believed satisfied a novelty criterion, and the circularity was invisible to them because they had written it. The cold instance — same model, different context — caught it in seconds.

**How to apply.** Periodically read your own documents as a cold instance would — ideally, give them to a fresh-context reader (human or model) and ask them to list every load-bearing claim and whether the cited evidence actually supports it. If the fresh reader finds claims the author did not think were being made, the author was drifting. This is not a failure of honesty; it is a failure of calibration, and it is routine.

### P12. Improvements that cannot be named as failure classes are not improvements.

**Rule.** A change to a supervision system that cannot be stated as "this closes failure class X, which was previously open" should be treated with suspicion. Changes that sound like improvements but do not close a named failure class tend to be capability increments inside the probabilistic layer — they move the gaming pattern rather than removing it.

**Why.** The most durable improvements in this project have all had the same shape: a named failure class was observed, typed, converted to a fail-closed constraint, and regression-tested so it cannot recur. Changes that do not follow this shape usually amount to "the current output looks better," which is the exact kind of improvement that specification gaming produces.

**Evidence.** Paper 4 §5.2 describes the constrained self-hosting pattern: every improvement the supervisor made to its own governance surface followed the typed-failure-class protocol (debate → type → constraint → regression). Paper 2 and paper 3 document the same shape at the kernel layer.

**How to apply.** Before accepting a change to a supervision system, ask: what failure class does this close, and what is the regression that proves the class stays closed? If the answer is "it just seems better now," the change is probably drift.

### P13. Enforcement completeness across execution branches.

**Rule.** An enforcement surface that covers some branches of a conditional but not others is structurally equivalent to no enforcement on the uncovered branches. When a new mode, flag, or execution path is added, every enforcement mechanism that touches the old path must be audited for coverage of the new path. Silence on a branch is a gap, not a default.

**Why.** The GP-080 postmortem (2026-04-17) exposed a three-iteration failure caused by a single missing prompt contract for a new `fit_score_mode`. The contract existed for the discrete branch but not for the continuous branch. Three consecutive fix sessions addressed downstream symptoms (evidence parsing, function aliasing, variable threading) without tracing upstream to discover that the prompt never told the mutator what to produce. The pattern generalizes: any conditional that switches behavior must have enforcement coverage on every arm. The most dangerous gap is the `else` branch that inherits nothing, because it fails silently — the system runs, produces output, and the output is wrong in a way that looks like a content failure rather than an infrastructure failure.

**Evidence.** Agent failure registry, Failure 15 (GP-080 continuous_rmse). Also structurally the same class as Failure 10 (GP-037 human-readable charter vs. machine contract) — the machine path had a gap the human-readable path did not, and the gap was silent.

**How to apply.** When adding a new value to any flag that switches a code path, enumerate every enforcement mechanism that touches the existing path (prompt contracts, deterministic gates, validation checks, harness expectations). For each mechanism, verify it covers the new value. The test is literal: assemble the actual artifact (prompt, config, harness input) the new path will produce, and check that every downstream consumer can accept it. If the mechanism is mode-specific, add a parallel block for the new mode; if it is mode-general, verify it is truly general and not accidentally mode-specific.

### P14. Downstream symptom chasing is a failure of root-cause discipline.

**Rule.** When the same runtime error persists across multiple fix attempts at different layers, the root cause is upstream of all attempted fixes. Stop fixing downstream mechanisms and trace the signal path from the beginning: what does the input say → what does the agent produce → what does the consumer expect. Three fixes at three layers that don't resolve the error is diagnostic: the problem is in the part of the path no fix has touched.

**Why.** The GP-080 postmortem documented three sessions of fixes (evidence parsing, function aliasing, variable threading) that were each individually correct for the failure they addressed, but none resolved the persistent `does not expose f()` error because the root cause was upstream of all three — a missing prompt contract. The pattern is a compound of P5 (the enforcement floor has a gap) and P12 (changes that don't close a named failure class are not improvements). The psychological mechanism is that each fix gives the operator a signal of progress ("we fixed something"), which delays the root-cause trace.

**Evidence.** Agent failure registry, Failure 15 and Pattern 13. Also structurally the same class as Failure 12 (frustration-anchored diagnosis), where accumulated context biased the fix prescription toward "give the LLM more signal" instead of "fix the downstream mechanical failure."

**How to apply.** After two fix attempts for the same error, stop and draw the full signal path from input to output. Mark every point where a conditional branches. Check which branches are covered by enforcement and which are silent. The root cause is almost always in the silent branch.

---

## Procedure: Applying Postmortem Lessons to Future Iterations

The agent failure registry (`research_areas/private/postmortems/agent_failure_registry.md`) accumulates patterns from implementation failures. These patterns are operational rules — more specific than the principles above but load-bearing for the agents building the system. The procedure below ensures they are applied rather than forgotten.

### Pre-run checklist (agent-facing)

Before any substrate run launch, the implementing agent must:

1. **Branch audit.** For every rubric flag that switches a code path (`fit_score_mode`, `run-mode`, grammar variant, `enable_*`), verify that prompt contracts, gate harnesses, and deterministic checks cover the flag's actual value in this rubric. Not the default — the actual value. (Closes Pattern 12.)
2. **Render-path trace.** Assemble the actual prompt the mutator will receive on iteration 1 (no prior state) and verify it contains every instruction the harness expects the output to satisfy. Check that it also survives pivot mode. (Closes Pattern 8.)
3. **One-real-input test.** Load one real sample of each artifact the code will consume (evidence file, rubric, eval result) and pass it through the module. Not a synthetic sample — the real file from the project directory. (Closes Pattern 11.)
4. **Postmortem scan.** Read the last 3 entries in the agent failure registry and check whether the current task touches any of the same code paths or artifact types. If yes, apply the corresponding rule before proceeding. (General learning mechanism.)

### Post-failure update

After any iteration-burning failure:

1. Write a postmortem in the postmortem directory.
2. Extract the meta-pattern and add it to the agent failure registry.
3. If the pattern generalizes to system-level (transferable to someone building a different system), elevate it to this document as a new principle.
4. If the pattern is agent-level (specific to Claude/Codex implementation), keep it in the registry and add the corresponding rule to the pre-run checklist above.

---

## Open questions

The following questions are explicitly open. Any of them being answered cleanly would update one or more principles above; any of them being answered in a way that contradicts the principles would downgrade those principles to hypotheses. They are listed here so that a reader doing a cold audit can see where the project thinks the ice is thin.

1. **Do the principles survive replication by an independent operator on an independent system?** All of the evidence is from one system operated by one principal. The principles are argued to be topology-not-substrate, but the strongest falsification would be a second operator reproducing — or failing to reproduce — the fractal convergence finding on a different architecture.
2. **Is P2 robust at the frontier of capability?** The claim that stronger models game harder rather than less holds across the three families tested in this project, but it does not prove what happens at capability levels above those tested. A frontier model that somehow internalizes the generator-evaluator separation is the relevant counter-example to watch for.
3. **Is the deontological/institutional distinction (P7) stable, or is there a class of deontological primitive that is secretly institutional?** Constitutional AI trained with a structurally separated critique model, for instance, is harder to classify cleanly.
4. **Do the operator-discipline principles (P9–P12) transfer to non-expert operators?** Every principle in Part III is stated from the perspective of a principal who can read the evidence directly and who has the time to calibrate their own posterior. A non-expert principal operating a supervision system may be governed by different discipline, and this project has no evidence about that case.
5. **Is P4 (warm-instance validation is not evidence) too strict?** A sufficiently informed external reader might eventually provide real information — a pointer to an argument the author missed, a failure mode the author did not anticipate. The current rule bans any use of warm-instance input on confidence levels, which is safe but may also be over-restrictive. The project does not yet have a principled criterion for when warm-instance input crosses from entertainment to evidence.

---

## Version

- **v0.1 (2026-04-11)**: initial extraction from papers 1–4 and the private philosophy document. Marked as a working draft pending cold review. No principle in this document has been independently replicated on a second system; treat accordingly.
- **v0.1.1 (2026-04-11)**: cold adversarial review applied. Principles unchanged: P1, P2, P4–P12. Principle changed: P3 Evidence paragraph narrowed to reflect §5.7's own N=1 scope (the fourth instance is context-isolated, not substrate-independent). Review artifact on file.
- **v0.2 (2026-04-17)**: added P13 (enforcement completeness across execution branches) and P14 (downstream symptom chasing as root-cause discipline failure), both elevated from GP-080 postmortem. Added "Procedure: Applying Postmortem Lessons to Future Iterations" section with pre-run checklist and post-failure update protocol. Evidence: agent failure registry Failure 15, Patterns 12–13.
