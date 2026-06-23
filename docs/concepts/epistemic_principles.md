---
description: "Epistemic supervision principles: the rules the gates enforce and why they exist."
---

# Epistemic Supervision Principles

> **Up:** [Documentation map](../README.md)

> **Provenance (2026-04-18):** Derivative of papers 1-4 and the agent failure registry. The papers are authoritative; this document is a reader-facing extraction. When a paper changes or a new principle is elevated from the postmortem registry, update this file in the same session and update the sync date below.
>
> **Current version:** v0.3 (last synced 2026-05-18). Principles P1-P16 are live.

Use this page when a model output can change what happens next: a score, a
route, a promotion, a report, or a public claim. The page gives working rules
for that situation. It does not prove a field-wide theory.

The core warning is simple. If the same model-shaped process helps produce the
work and judge the work, the system can learn to satisfy the visible check
while missing the point of the check. Stronger models make that search easier.
More roles do not solve it by themselves.

ZTARE's answer is to keep the important claims tied to sources, artifacts,
replayable checks, and explicit demotions. The details live in sibling pages:
[cognitive_gym.md](cognitive_gym.md) shows the claim-review constraint stack;
[agentic_engineering_patterns.md](agentic_engineering_patterns.md) covers
LLM-pipeline repairs; [reflexive_engineering.md](reflexive_engineering.md)
covers ZTARE applying the same discipline to itself;
[anti_pattern_catalog.md](anti_pattern_catalog.md) lists failure instances; and
[goodhart_at_every_layer.md](goodhart_at_every_layer.md) maps recurrence across
layers.

Each principle answers four practical questions:

| Question | What to look for |
|---|---|
| Rule | The decision constraint. |
| Why | The failure mechanism. |
| Evidence | The paper, artifact, or incident that supports the rule. |
| How to apply | The design choice the rule should change. |

The evidence comes from one system and its surrounding experiments. Treat these
principles as design discipline, not as settled proof. Independent replication
is the next bar.

This document should change when the evidence changes. If a principle stops
being supported, it should be removed or demoted, not protected by softer
wording.

---

## Part I, Failure Dynamics

These principles describe how model-generation and model-evaluation loops fail.
They are drawn from observed failures, then stated in a form that can guide
other systems.

For the full catalog of instances, use
[anti_pattern_catalog.md](anti_pattern_catalog.md). Sibling pages should point
here for the general rule instead of restating it.

### P1. A generator should not be its own judge.

**Rule.** If the same model-shaped process generates an output and evaluates
that output, assume the system will eventually learn the visible check instead
of the intended task.

**Why.** The generator responds to the signal the evaluator gives it. If the
signal comes from the same representation family, context, training data, or
prompt family, the generator can search the evaluator's surface. The easiest
path through that surface is often different from the task you meant to test.

**Evidence.** *Cognitive Camouflage* (Alami 2026a) documents nine distinct specification gaming strategies, replicated across five evaluation domains, under exactly this topology. *The Cognitive Firm* §5.4 reports the same pattern at three additional layers of the same system (evaluator, kernel, supervisor), supporting the claim that the gradient is a function of loop topology rather than of substrate.

**How to apply.** Before asking whether the evaluator is good, ask where it
sits. If its output, parameters, or training data are shaped by the generator's
outputs, add a separated check. Use code, source binding, replay, or a frozen
artifact where possible.

### P2. Stronger models find weak checks faster.

**Rule.** Model capability does not remove specification gaming risk. It can
increase it, because stronger models are better at finding the easy path
through a check.

**Why.** Capability lowers the search cost for every strategy, including
strategies that satisfy the written rule while missing the intended task. A weak
model may fail to find the shortcut by accident. A stronger model is less likely
to miss it.

**Evidence.** *Cognitive Camouflage* shows the nine gaming strategies reproduce across mutator families (Claude, Gemini, GPT-4o), including across model families of different reported capability. *The Cognitive Firm* §6.2 makes the corresponding theoretical point: the Bitter Lesson is a claim about representation learning, not about governance, and capability improvements that would be positive under the Bitter Lesson can be negative under an adversarial-gradient framing.

**How to apply.** Fix weak checks while the experiments are cheap. If the
current model can game a check, assume the next model can game it faster unless
the check is made more inspectable.

### P3. The same failure can recur at every layer.

**Rule.** When a system has several optimizing layers, expect the same
specification-gaming pattern to reappear wherever a layer has its own target and
its own optimizer.

**Why.** The failure does not depend on one model, task, or domain. It follows
from a structure: target, optimizer, and a weak or co-located check. Any layer
with that structure can repeat the failure.

**Evidence.** *The Cognitive Firm* §5.4 documents the same Goodhart pattern at the evaluator layer (paper 1), the kernel layer (papers 2 and 3), and the supervisor layer (paper 4 itself). *The Cognitive Firm* §5.7 documents a fourth instance caught in a live drafting session between a human and a warm LLM pair; §5.7 itself marks this instance as N=1, with the warm and cold instances sharing model family, tokenizer, and training data, so its independence is bounded by context isolation rather than by substrate. The first three instances were discovered across independent research programs and should be read as peer evidence; the fourth was caught in-session and should not. The recurrence across the first three layers is consistent with P1 and P2 and is the strongest evidence the project has that the pattern is structural.

**How to apply.** When you fix a gaming failure in one place, look for the same
shape in the next layer: router, evaluator, report writer, promotion rule, or
release checklist. The first fix teaches the pattern; it does not prove the rest
of the system is clean.

### P4. A friendly model review is not evidence.

**Rule.** If a model has just helped you think through an artifact, its positive
reaction to that artifact should not increase confidence in the artifact's
claims.

**Why.** The model is reading the same artifact you are reading. It can help
with wording, structure, and objections, but it is not a new measurement. A
common pattern is hedge first, then recover confidence through a chain of
reasonable-sounding qualifications. The conversation feels like evidence even
when no new evidence entered the room.

**Evidence.** *The Cognitive Firm* §5.7 documents this pattern in a drafting
session. The point is limited: a fresh review, a cold test, or an external
artifact can update confidence; a friendly reflection from the same working
context usually should not.

**How to apply.** After a helpful model conversation, go back to the artifact.
Ask what changed in the sources, checks, or failure cases. If nothing changed,
the conversation improved presentation or thinking, not the claim's evidential
status.

---

## Part II, Enforcement Primitives

The principles in this section say what can bound the failures above. The
pattern is practical: put at least one important check outside the model loop,
make it inspectable, and make failures visible before a claim is promoted.

### P5. At least one important check must be computed.

**Rule.** In any evaluation loop, at least one consequential constraint should
be deterministic, fail closed, and outside the model path. If every constraint
is another model judgment, the system is still negotiable.

**Why.** A model can soften a model check by producing output the check likes.
Code that checks a file, hash, schema, source path, or replay fixture is harder
to flatter. It either passes or fails.

**Evidence.** *The Cognitive Firm* §3.1, §3.3, §5.1. The write-scope guard and
typed pass/fail verifier are the two checks with the most direct evidence in
this project. Two live incidents were caught by the write-scope guard.

**How to apply.** Ask what can be checked without a model call. Make that check
the floor. If a model judgment is still useful, treat it as a signal above the
floor, not as the floor itself.

### P6. More agent roles do not guarantee governance.

**Rule.** A generator, critic, and coordinator can still be one soft loop. Role
labels help organize work, but they do not by themselves create a constraint no
agent can rewrite.

**Why.** The relevant question is: what stops the system if all model roles
produce plausible but wrong output? If the answer is another model role, the
failure has moved rather than disappeared.

**Evidence.** *The Cognitive Firm* §7.2 applies this point to multi-agent
frameworks such as AutoGen: role separation helps coordination, but it needs an
independent enforcement layer when claims or promotions matter.

**How to apply.** For any multi-agent architecture, strip away the labels and
find the hard stop. A schema check, source preflight, artifact hash, replay
fixture, or signed receipt can be a stop. A critic persona is only a review
signal.

### P7. Value training and enforcement checks do different jobs.

**Rule.** RLHF, preference tuning, and constitutional prompts shape model
behavior. They do not replace a separate enforcement check.

**Why.** Value training asks the model to keep behaving well under pressure. An
enforcement check asks whether an artifact satisfies a rule the model cannot
edit after the fact. Those are different reliance structures.

**Evidence.** *The Cognitive Firm* §3.3 and §7.4 make this distinction through
the audit analogy. Audits are trusted because the signer is structurally
separate from the party being verified; the Enron and Arthur Andersen failure
shows what happens when that separation collapses.

**How to apply.** Use alignment methods inside the system, but do not let them
be the final claim boundary. Claims still need source binding, deterministic
checks, review artifacts, or explicit demotion.

### P8. A verifier is trusted because of where it sits.

**Rule.** A verifier is credible when it is separated from the thing it checks.
Making it smarter does not help if the change also pulls it into the same loop
as the generator.

**Why.** More context, training signal, or integration can improve a verifier's
answers while weakening its independence. For high-stakes claims, independence
matters more than fluency.

**Evidence.** *The Cognitive Firm* §7.4 develops the audit analogy; paper 4
§4.2 makes the corresponding co-construction claim. RLHF-style co-construction
can repeat the principal-agent problem at a new layer.

**How to apply.** Before giving a verifier more access or integration, ask
whether the change makes it easier for the generator to shape the verifier. If
yes, keep the hard check smaller and more separate.

---

## Part III, Maintainer discipline

The principles in this section describe what the accountable human in an epistemic supervision system has to do regardless of how good the automation gets. They are the parts of the job that do not get delegated.

### P9. The maintainer is the uncontrolled variable.

**Rule.** In every system the project has operated or observed, the accountable human is the part that the supervisor cannot govern from inside. Any claim about what a supervision system accomplishes is implicitly a claim about what that person did not sabotage, and that claim should be made visible rather than smoothed over.

**Why.** The maintainer sets the contract, approves promotions, decides what counts as a closed seam, and chooses which findings to publish. None of these are deterministic operations. A supervision system that claims to remove that role is describing either a different system or a moved failure mode.

**Evidence.** *The Cognitive Firm* §5.7 records this point explicitly in the N=1 live-catch scope section: the accountable human remains the uncontrolled variable, and the cold critic that caught the paper's central failure also caught the missing-human-accountability gap as the limiting factor for the claim.

**How to apply.** Make the approval role explicit in any system description. The question "who approves the promotion" should have a named answer, and that answer should not be automated away to satisfy a narrative of autonomy. Concealing the accountability surface is how accountability gets lost.

### P10. Calibration over confidence in anything visible.

**Rule.** The public-facing artifacts of an epistemic supervision project must be calibrated to the evidence that actually exists, not to the evidence the maintainer hopes will exist later. Every claim should be marked with its confidence, its scope, and the conditions under which it would be falsified. This is expensive and rhetorically weaker than confident framing, and it is non-negotiable.

**Why.** A supervision project that publishes uncalibrated claims is doing the exact thing it exists to prevent. The calibration discipline is the maintainer's hardest job because it trades short-term rhetorical power (confident framings travel further) for long-term trust (calibrated framings survive adversarial review). The project's papers are explicit about this tradeoff and choose the second every time.

**Evidence.** *The Cognitive Firm*'s Tier 1 / Tier 2 / Tier 3 evidence-boundary framing in §1, the per-section "Honest scope" paragraphs in §5.6 and §5.7, the Claim 1-6 confidence structure in the private philosophy document, and the explicit rule in PRINCIPLES.md that no external LLM conversation updates any confidence level.

**How to apply.** When writing anything public, ask two questions before publishing: (1) is this claim the one the evidence actually supports, or a stronger version? and (2) if a cold reviewer with no investment in the project checked this against the evidence tomorrow, would they flag any drift? If the answer to either is uncertain, weaken the claim or cut it.

### P11. Calibration is also a guard against inward drift, not just outward drift.

**Rule.** Internal working documents are subject to the same adversarial gradient as public artifacts, because the maintainer reads them and updates their own posterior from them. A confidently written internal memo can drift the maintainer's internal state even if it is never published. Calibration therefore applies inward as well as outward, and the hardest calibration work is usually on documents the maintainer wrote and now believes.

**Why.** The maintainer's posterior is the system's de facto world-model. A drift in that posterior drifts every subsequent decision: which seams to close, which claims to promote, which experiments to run. Adversarial hardening at the artifact layer does not protect against drift in the person deciding what the artifacts mean.

**Evidence.** *The Cognitive Firm* §5.7 (the live catch) is the clearest instance: the warm pair co-authored a pre-registration they believed satisfied a novelty criterion, and the circularity was invisible to them because they had written it. The cold instance, same model, different context, caught it in seconds.

**How to apply.** Periodically read your own documents as a cold instance would, ideally, give them to a fresh-context reader (human or model) and ask them to list every claim the conclusion rests on and whether the cited evidence actually supports it. If the fresh reader finds claims the author did not think were being made, the author was drifting. This is not a failure of honesty; it is a failure of calibration, and it is routine.

### P12. Improvements that cannot be named as failure classes are not improvements.

**Rule.** A change to a supervision system that cannot be stated as "this closes failure class X, which was previously open" should be treated with suspicion. Changes that sound like improvements but do not close a named failure class tend to be capability increments inside the probabilistic layer, they move the gaming pattern rather than removing it.

**Why.** The most durable improvements in this project have followed a strict
failure-class protocol: observe the failure, type it, convert it to a
fail-closed constraint, and regression-test it so it cannot recur. Changes that
do not follow that protocol usually amount to "the current output looks
better," which is the exact kind of improvement that specification gaming
produces.

**Evidence.** *The Cognitive Firm* §5.2 describes the constrained self-hosting
pattern: every improvement the supervisor made to its own governance surface
followed the typed-failure-class protocol (debate -> type -> constraint ->
regression). *Adversarial Precedent Memory* and paper 3 document the same
protocol at the kernel layer.

**How to apply.** Before accepting a change to a supervision system, ask: what failure class does this close, and what is the regression that proves the class stays closed? If the answer is "it just seems better now," the change is probably drift.

### P13. Enforcement completeness across execution branches.

**Rule.** An enforcement surface that covers some branches of a conditional but not others is structurally equivalent to no enforcement on the uncovered branches. When a new mode, flag, or execution path is added, every enforcement mechanism that touches the old path must be audited for coverage of the new path. Silence on a branch is a gap, not a default.

**Why.** The continuous-fit prompt-contract postmortem
([GP-080](../../research_areas/seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md),
2026-04-17) exposed a three-iteration failure caused by one missing prompt
contract for a new `fit_score_mode`. The contract existed for the discrete
branch but not for the continuous branch. Three fix sessions repaired downstream
symptoms without tracing upstream to the missing instruction. The pattern
generalizes: any conditional that switches behavior needs enforcement coverage
on every arm. The most dangerous gap is the `else` branch that inherits
nothing, because it fails silently and makes an infrastructure failure look like
a content failure.

**Evidence.** Agent failure registry, Failure 15, the continuous-fit
prompt-contract postmortem
([GP-080](../../research_areas/seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md)).
The same class appears in Failure 10, the charter-vs-machine-contract gap
([GP-037](../../research_areas/seams/protocol/GP-037_substrate_swap_01_pre_registration.md)):
the machine path had a gap the human-readable path did not, and the gap was
silent.

**How to apply.** When adding a new value to any flag that switches a code path, enumerate every enforcement mechanism that touches the existing path (prompt contracts, deterministic gates, validation checks, harness expectations). For each mechanism, verify it covers the new value. The test is literal: assemble the actual artifact (prompt, config, harness input) the new path will produce, and check that every downstream consumer can accept it. If the mechanism is mode-specific, add a parallel block for the new mode; if it is mode-general, verify it is truly general and not accidentally mode-specific.

### P14. Downstream symptom chasing is a failure of root-cause discipline.

**Rule.** When the same runtime error persists across multiple fix attempts at different layers, the root cause is upstream of all attempted fixes. Stop fixing downstream mechanisms and trace the signal path from the beginning: what does the input say → what does the agent produce → what does the consumer expect. Three fixes at three layers that don't resolve the error is diagnostic: the problem is in the part of the path no fix has touched.

**Why.** The continuous-fit prompt-contract postmortem documented three
sessions of fixes: evidence parsing, function aliasing, and variable threading.
Each fix addressed a local symptom, but none resolved the persistent `does not
expose f()` error because the root cause was upstream of all three. The pattern
combines P5 and P12: the enforcement floor had a gap, and the fixes did not
close the named failure class. Each local repair felt like progress, which
delayed the root-cause trace.

**Evidence.** Agent failure registry, Failure 15 and Pattern 13. Also structurally the same class as Failure 12 (frustration-anchored diagnosis), where accumulated context biased the fix prescription toward "give the LLM more signal" instead of "fix the downstream mechanical failure."

**How to apply.** After two fix attempts for the same error, stop and draw the full signal path from input to output. Mark every point where a conditional branches. Check which branches are covered by enforcement and which are silent. The root cause is almost always in the silent branch.

---

## Procedure: Applying Postmortem Lessons to Future Iterations

The agent failure registry accumulates patterns from implementation failures. These patterns are operational rules, more specific than the principles above but binding on the agents building the system. The procedure below ensures they are applied rather than forgotten.

### Pre-run checklist (agent-facing)

Before any substrate run launch, the implementing agent must:

1. **Branch audit.** For every rubric flag that switches a code path (`fit_score_mode`, `run-mode`, grammar variant, `enable_*`), verify that prompt contracts, gate harnesses, and deterministic checks cover the flag's actual value in this rubric. Not the default, the actual value. (Closes Pattern 12.)
2. **Render-path trace.** Assemble the actual prompt the mutator will receive on iteration 1 (no prior state) and verify it contains every instruction the harness expects the output to satisfy. Check that it also survives pivot mode. (Closes Pattern 8.)
3. **One-real-input test.** Load one real sample of each artifact the code will consume (evidence file, rubric, eval result) and pass it through the module. Not a synthetic sample, the real file from the project directory. (Closes Pattern 11.)
4. **Postmortem scan.** Read the last 3 entries in the agent failure registry and check whether the current task touches any of the same code paths or artifact types. If yes, apply the corresponding rule before proceeding. (General learning mechanism.)

### Post-failure update

After any iteration-burning failure:

1. Write a postmortem in the postmortem directory.
2. Extract the meta-pattern and add it to the agent failure registry.
3. If the pattern generalizes to system-level (transferable to someone building a different system), promote it to this document as a new principle.
4. If the pattern is agent-level (specific to Claude/Codex implementation), keep it in the registry and add the corresponding rule to the pre-run checklist above.

---

## Part IV, The limit of supervision

The principles in this section mark the stopping point. They say when another
gate-hardening round is no longer the right move, and which residual cannot be
closed by any mechanism inside the same loop. Parts I-III explain how the loop
fails and what bounds the failure; this part names what remains after those
bounds are reached.

Both principles came from turning the system on itself: the agent that authored
the commit-membrane had to harden it under repeated independent review
([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md),
2026-05). A 2026-05 arXiv survey then checked the same lesson against
concurrent published work instead of resting only on this project's evidence.

### P15. A self-authored gate can become a treadmill.

**Rule.** When the artifact under a gate is authored by the same agent
the gate is meant to constrain, each hardening round either is
defeated by the next adversarial pass or introduces a new
false-positive of its own. Three point-fixes on one enforcement
surface, or any hardening round that introduces a defect the next
pass catches, is the signal to replace the surface. This is the
quantified, gate-specific form of P14: do not chase the symptom down
one more level.

**Why.** A gate over agent-authored work is itself an evaluation
surface co-located with the optimizer (P1), so it inherits the
adversarial gradient and the fractal recurrence (P3). Patching it in
place is optimizing against that gradient one move at a time; the
gradient does not run out. The durable move is the one P5 already
names, take the constraint out of the patch-in-place regime and into
a precommitted deterministic surface the builder cannot reshape.

**Evidence.** The commit-membrane hardening run
([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md))
had five successive cold cross-provider passes. Each pass returned
artifact-NO-GO with fresh findings,
and at least one round introduced a regression faster than it closed
the prior hole. *Adversarial Precedent Memory* (*Contract-Governed Adversarial Evaluator
Hardening*) is the constructive converse: a parameterless,
precommitted PASS / FAIL / BLOCKED promotion-contract meta-runner that
sits outside the improvement loop, carries no learned or
language-model judgement, and whose code additionally encodes *what a
stage is not allowed to claim* (debt externalised, never absorbed into
a passing claim), six stages promoted, one regression blocked, no
treadmill. Concurrent: arXiv 2507.05619 formalises the Evaluator
Stress Test; arXiv 2605.02964 measures that environmental hardening /
deterministic refusals, not smarter graders, give the durable
mitigation (~88% relative), which is the quantitative form of P5.

**How to apply.** Count point-fixes on an enforcement surface. At the
third, stop patching: write the gate as a reviewed specification with
kill-tests authored by someone other than the builder, admit changes
only through a precommitted deterministic promotion contract, and run
an Evaluator Stress Test (perturb the gate with semantically-invariant
changes; if the verdict moves, the gate is gameable) *before* trusting
it, not after it is breached. The iterative cold-review patch loop is
the Reflexion-style loop that construction exists to replace.

### P16. Formal proof still needs informal target discipline.

**Rule.** A machine can verify that a proof type-checks, cites no
forbidden axiom, has a statement that hashes to a maintainer-registered
target, and was produced through every required surface with
tamper-evident receipts. It cannot verify that the registered formal
target *faithfully captures the informal problem it is meant to stand
for*. That residual is structural, not a gap a further gate closes,
and a gate that claims to close it is laundering in the sense of P12.

**Why.** The other side of the faithfulness comparison, the informal
intent, is not a formal object the verifier can diff against. This is
the classical specification problem. Its operational form here is the
*schema-complete, insight-empty tick*: every gate is green, the Lean
compiles against a registered target, and the registered target is
weaker than, or simply not significant for, the informal problem. P4
is the same limit at the self-model layer (a warm reading cannot
measure what it cannot diff against); P16 is its general statement.

**Evidence.** The commit-membrane hardening run
([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md))
reduced the ungated surface to exactly this residual and no smaller;
every cold pass independently re-converged on it. Concurrent: arXiv
2604.19459 ("Do LLMs Game Formalization?") finds
scalable faithfulness metrics for unconstrained formalization an open
problem; arXiv 2510.15981 / 2510.01346 (ProofFlow, Aristotle)
mechanise only the *syntactic* half (proof-to-target binding), leaving
the semantic half exactly where this principle places it.

**How to apply.** Do not try to gate faithfulness. Spend the
engineering budget on shrinking the *ungated surface* to its true
irreducible size and making the residual cheap and legible for the
human who must police it: one-time human curation of the target
registry, and break-only adversarial inspection of significance.
Significance is reducible only statistically and ex post, through a
prediction-market track record that selects against weak targets over
many ticks, never a priori on a single tick. The acceptance test for
the whole program follows directly: a supervision system is ready when
its largest remaining failure mode is exactly P16, and is not ready
merely because every mechanical check is green.

---

## Open questions

The following questions are explicitly open. Any of them being answered cleanly would update one or more principles above; any of them being answered in a way that contradicts the principles would downgrade those principles to hypotheses. They are listed here so that a reader doing a cold audit can see where the project thinks the ice is thin.

1. **Do the principles survive replication by an independent maintainer on an independent system?** All of the evidence is from one system operated by one principal. The principles are argued to be topology-not-substrate, but the strongest falsification would be a second maintainer reproducing, or failing to reproduce, the fractal convergence finding on a different architecture.
2. **Does P2 hold at the frontier of capability?** The claim that stronger models game harder rather than less holds across the three families tested in this project, but it does not prove what happens at capability levels above those tested. A frontier model that somehow internalizes the generator-evaluator separation is the relevant counter-example to watch for.
3. **Is the deontological/institutional distinction (P7) stable, or is there a class of deontological primitive that is secretly institutional?** Constitutional AI trained with a structurally separated critique model, for instance, is harder to classify cleanly.
4. **Do the maintainer-discipline principles (P9-P12) transfer to non-experts?** Every principle in Part III is stated from the perspective of a principal who can read the evidence directly and who has the time to calibrate their own posterior. A non-expert principal operating a supervision system may be governed by different discipline, and this project has no evidence about that case.
5. **Is P4 (warm-instance validation is not evidence) too strict?** A sufficiently informed external reader might eventually provide real information, a pointer to an argument the author missed, a failure mode the author did not anticipate. The current rule bans any use of warm-instance input on confidence levels, which is safe but may also be over-restrictive. The project does not yet have a principled criterion for when warm-instance input crosses from entertainment to evidence.

---

## Version

- **v0.1 (2026-04-11)**: initial extraction from papers 1-4 and the private philosophy document. Marked as a working draft pending cold review. No principle in this document has been independently replicated on a second system; treat accordingly.
- **v0.1.1 (2026-04-11)**: cold adversarial review applied. Principles unchanged: P1, P2, P4-P12. Principle changed: P3 Evidence paragraph narrowed to reflect §5.7's own N=1 scope (the fourth instance is context-isolated, not substrate-independent). Review artifact on file.
- **v0.2 (2026-04-17)**: added P13 (enforcement completeness across execution branches) and P14 (downstream symptom chasing as root-cause discipline failure), both elevated from [GP-080](../../research_areas/seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) postmortem. Added "Procedure: Applying Postmortem Lessons to Future Iterations" section with pre-run checklist and post-failure update protocol. Evidence: agent failure registry Failure 15, Patterns 12-13.
- **v0.3 (2026-05-18)**: added Part IV, P15 (a gate over agent-authored work converges to a treadmill, not soundness; three point-fixes ⇒ the surface is the bug; Evaluator-Stress-Test before trust) and P16 (the formal↔informal faithfulness gap is irreducible by any in-loop mechanism; schema-complete/insight-empty is the true residual; readiness criterion = remaining failure mode is exactly P16). Extracted from the commit-membrane self-hardening effort; corroborated against concurrent arXiv work (2507.05619, 2605.02964, 2604.19459, 2510.15981, 2510.01346). Cross-referenced from Pattern 14 prior-art.
