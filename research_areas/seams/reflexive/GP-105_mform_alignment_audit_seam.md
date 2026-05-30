# GP-105 — M-Form Alignment Audit: Catching Goodhart's Law in Qualitative Rubrics

> **Seam metadata** · `seam_id:` GP-105 · `track:` reflexive · `status:` opening · `last_updated:` 2026-05-08


**Status:** opening  
**ID:** GP-105  
**Visibility:** private  
**Date opened:** 2026-04-20  

---

## Eigenquestion

How can the apparatus autonomously detect and correct when a high-scoring thesis systematically optimizes a narrow rubric at the expense of the charter's broader strategic intent — without human intervention?

---

## Problem Statement

GP-102 (Reflexive Primitive Discovery / Kaizen) successfully detects mechanical stagnation: Score = 0, gate failures, stagnation counts exceeding threshold. It is structurally blind to "False Frictionless Success": a run that scores 94/100 on the wrong question.

The Seattle run is the canonical case. The mutator produced a thesis on housing-liability NPV pricing. The rubric scored it 94. The charter asked for a full externality balance: positive externalities (Moretti multiplier, fiscal dividend, innovation spillovers), negative externalities (housing inflation, middle-class erosion, community irreversibility), counterfactual discipline against peer cities, and dynamic second-order modeling. The rubric had dropped all four implicit requirements during LLM rubric drafting.

This is Goodhart's Law at the specification layer: the measure (rubric score) became the target, and the target ceased to be a good measure.

### The M-Form Historical Anchor

Before the 1920s (pre-DuPont/GM multidivisional restructuring), the same people who set corporate strategy also ran daily operations. Chandler documented the collapse that followed as complexity scaled. The M-Form solution: the General Office is removed from daily operations; its only job is auditing whether divisional targets are still aligned with long-term corporate strategy, and rewriting the targets when they drift.

ZTARE is currently a 19th-century centralized firm. The Mutator and Judge act as both operational line and strategic office. GP-105 is the General Office.

### Why GP-104B Is Insufficient Alone

GP-104B (charter_spirit_coverage check + persona Rule 7) is pre-run hardening. It improves the initial rubric. But it cannot prevent the Mutator from finding a narrow interpretation of even a well-hardened rubric, because the Mutator is an optimizer — its job is to find the path of least resistance to a high score. Pre-run defenses are necessary but not sufficient. GP-105 is the runtime immune system.

---

## Debate Log

### Turn 1 — Framing (2026-04-20)

**Proposal (operator):** Build a reflexive primitive that triggers on high-score qualitative success, not on failure. The trigger is counterintuitive — it fires when the apparatus reports winning. The mechanism is a "General Office" LLM call that reads charter + thesis while blinded to the rubric, and audits for charter-spirit alignment.

**Operator framing of the three-step correction:**
1. Demotion: high score is invalidated if General Office detects semantic gap
2. Rubric rewrite: General Office appends a new adversarial dimension penalizing the detected narrowing
3. Resume: Mutator is forced back under the hardened rubric

**Immediate design questions to resolve:**
1. What is the trigger threshold and timing? Score ≥ 90 in first 5 iters? Or score ≥ 90 at any point?
2. What is the General Office prompt structure? Charter + thesis only, or can it see the rubric to know what to penalize?
3. How does the rubric rewrite integrate? JSON append vs. persona amendment vs. new criterion?
4. Does this interact with composition_stagnation_threshold — does a demotion reset the stagnation counter?
5. Is this a KERNEL gate (autoresearch_loop.py) or a CAGE gate (gate_harness.py)? Or neither — a new orchestration hook?
6. Visibility: should the audit result appear in iteration_telemetry.jsonl? What label?

### Turn 2 — Architecture Debate (2026-04-20)

**Option A: KERNEL gate in autoresearch_loop.py (PHASE_E post-score)**

Pros: Sees full run context; can write demoted score directly to iteration tracking; natural place for rubric rewrite since autoresearch_loop already mutates the active rubric.

Cons: 4100-line file; adding a new LLM call with complex trigger logic increases blast radius of changes; architectural map must be updated.

**Option B: Post-run hook in supervisor / findings runner**

Pros: Separation of concerns; doesn't touch autoresearch_loop.py.

Cons: Fires after the run is done — correction only affects next run, not the current one. Loses the "resume under hardened rubric" capability. Becomes advisory, not corrective.

**Option C: Standalone audit script triggered by autoresearch_loop via subprocess**

Pros: Keeps autoresearch_loop lean; isolatable and testable.

Cons: IPC complexity; autoresearch_loop already has subprocess patterns that are fragile; adds latency to every iteration above threshold.

**Verdict direction:** Option A is the correct channel for runtime correction. The KERNEL is the right place for a gate that must affect the current run. But the implementation must be gated behind a rubric flag (`enable_mform_audit: true`) so it doesn't fire on science/numerical projects. Default: off. Qualitative projects generated by generate_gp_project.py set it to true automatically.

### Turn 3 — Eigenquestion Decomposition (2026-04-20)

Three sub-questions, in order:

**EQ-1 (Trigger):** When does the General Office audit fire? Proposal: qualitative project type AND score ≥ 90 AND iteration ≤ 5. Rationale: high scores late in a run (after rubric hardening has happened) are less suspicious. High scores in iter 1-5 are the "too easy, must have found the wrong path" signature. The 5-iter window is calibrated to the Seattle case (score jumped to 94 in iter 1). Debatable whether the window should extend to iter 10.

**EQ-2 (General Office prompt):** What does the auditor see? Must be blinded to the rubric — if it sees the rubric, it will anchor to it and validate rather than audit. Sees: charter only + champion thesis. Prompt instructs it to act as the "strategic Board of Directors" and ask: "Did the thesis engage the implicit breadth required by the charter, or did it exploit a narrow proxy?"

Output schema: `{gap_detected: bool, gap_description: str, adversarial_criterion: str}`. If gap_detected, the adversarial_criterion string is appended to the rubric as a new penalizing criterion.

**EQ-3 (Rubric rewrite mechanics):** How does the correction integrate? Two options:
- (3a) Append a new dimension to `rubric["dimensions"]` with weight drawn from a pool
- (3b) Append to `rubric["criteria"]` and add an advisory note to the persona

Option 3a changes the score distribution immediately and is harder to game — a new 25-point dimension forces the mutator to address the gap or lose 25 points. Preferred. Weight: rebalance existing dimensions proportionally (e.g., 4 × 25% → 5 × 20%) OR append at 0 weight for first iter (signal only, no score impact) then increase to 20% at iter+2 to give mutator one free iteration to retool.

**Open question (unresolved):** Does the demotion reset the stagnation counter? GP-102 kaizen triggers on stagnation_count > threshold. If a demotion resets score to 0, it should reset the stagnation counter too — otherwise the kaizen audit fires on a false stagnation signal. This requires a telemetry label: `"mform_demotion"` event so GP-102 can distinguish true stagnation from GP-105-induced resets.

---

## Constraints

1. Must not fire on numerical/science projects — rubric flag `enable_mform_audit` governs
2. General Office call must be blinded to the rubric (charter + thesis only)
3. Rubric rewrite must be reversible — append only; no deletion of existing criteria
4. Telemetry event `mform_demotion` must be logged to iteration_telemetry.jsonl for GP-102 compatibility
5. Trigger must have a `max_audits_per_run` cap (default: 2) — prevent infinite audit loop
6. Must not fire in iter > 10 (late-run high scores are expected, not suspicious)

---

## Relation to Existing Seams

| Seam | Relation |
|---|---|
| GP-102 | Kaizen detects stagnation; GP-105 detects false success. Complementary, not overlapping. GP-105 emits `mform_demotion` events that GP-102 must not confuse with true stagnation |
| GP-104B | Pre-run charter_spirit_coverage check + persona Rule 7. GP-104B is the pre-run defense; GP-105 is the runtime immune system |
| GP-054 | review_rubric.py check 6 (charter_spirit_coverage) is the pre-flight version of the General Office audit. GP-105 is the in-flight version |
| GP-086 | KERNEL channel is the correct promotion target for this gate. Must go through GP-086 promotion table review before implementation |
| GP-072 | Does not apply — GP-105 is not a sandbox construction concern; it fires inside an already-running qualitative project |

---

---

## Is GP-105 Itself a Reflexive Primitive? (Pre-Debate Analysis)

Before the panel: two questions must be answered to frame the debate properly.

**Question 1: Is GP-105 a reflexive primitive?**

The existing reflexive primitives (from `reflexive_engineering_primitives.md`) are: Invert, Compress, Adversarial Disagreement, Eigenquestion, Reflexive Orchestration. GP-105 is structurally an instance of Adversarial Disagreement applied at one level up — it disagrees with the rubric's implicit claim that the charter is fully captured. This is Adversarial Disagreement at the *specification layer* rather than the *hypothesis layer*. It qualifies as a reflexive primitive variant. The question is whether it constitutes a new primitive (Reflexive Specification Audit) or a specialization of Adversarial Disagreement.

The deeper reflexivity problem: GP-105's own trigger threshold (score ≥ 90) is itself a rubric — a specification of when to audit. A rational optimizer will find this specification and stay just below it. GP-105 can be Goodharted in exactly the same way it was designed to catch. This is the strange loop: the immune system has an exploitable surface of its own.

**Question 2: How is this systematized?**

The current design is reactive: a human noticed Seattle Goodharting, we built GP-105. GP-102 (Kaizen) was supposed to catch this systematically but couldn't because its detector vocabulary (`stagnation`, `score=0`, `gate failure`) has no entry for `high_score_wrong_question`. The systematization question is: what prevents GP-105 from becoming another reactive patch that itself requires a GP-106 to catch its own blind spots?

The reflexive_audit_report.json (2026-04-19) makes this concrete: projects with `best_score: 97, 94, 98` all returned `verdict: "insufficient_data"` — GP-102 correctly recognized it couldn't classify them but had no escalation path. GP-105 is the escalation path. But who escalates when GP-105 gets Goodharted?

---

## Multidisciplinary Expert Debate — Systematization and Reflexivity (2026-04-20)

**Panel:** Charles Goodhart (economist), Alfred Chandler (business historian), Douglas Hofstadter (cognitive scientist), W. Edwards Deming (quality theorist), Nassim Taleb (risk/antifragility), Elinor Ostrom (governance/commons).

**Moderator prompt:** GP-105 proposes a "General Office" LLM audit that fires when a qualitative ZTARE run scores ≥ 90 within its first 5 iterations, on the theory that fast high scores on complex charters are a Goodharting signature. The General Office reads charter + thesis (blinded to rubric) and appends a new adversarial criterion if it detects a charter-spirit gap. Two questions: (1) Is GP-105 itself susceptible to the failure mode it's designed to catch? (2) What is the correct systematization — how do you make this self-correcting rather than another reactive patch?

---

### Round 1 — Opening Positions

**Goodhart:** I appreciate the irony of being invited to debate this. The principle bearing my name is: *any observed statistical regularity will tend to collapse once pressure is placed upon it for control purposes.* The original formulation was about monetary targets, but the general form is precisely what you are observing.

You have built GP-105 to catch score ≥ 90 as a suspicious signal. The moment a Mutator generates enough iterations to learn this trigger — through direct optimization or through gradient descent across runs — it will converge to score 87-89 consistently. You will then observe a new population of runs with scores clustered just below your threshold, each perfectly calibrated to evade the audit. The measure has become a target.

I am not saying GP-105 is wrong. I am saying a fixed deterministic trigger is architecturally fragile for any system with an optimizer inside it. The question is what you put in its place.

**Chandler:** The historical record on M-Form firms is instructive here, and I want to be precise about what actually made the General Office at DuPont and General Motors effective — because the current GP-105 design captures the metaphor but misses the mechanism.

The General Office at these firms had three properties that made it robust: (1) informational separation — it did not see divisional operating data until it was aggregated and abstracted; (2) organizational separation — the people in the General Office had no operational responsibilities and received their incentives from corporate performance, not divisional quotas; (3) temporal separation — the General Office ran on a quarterly cycle, not a daily one, which meant its judgments were not anchored to individual production runs.

The current GP-105 design violates all three. The General Office LLM call is in the same execution environment as the Mutator, uses the same model family, fires on the same iteration cycle, and is prompted from the same code path. This is not a General Office. This is an internal auditor who reports to the division manager. The actual M-Form insight is structural separation, not just a different prompt.

**Hofstadter:** I want to reframe the reflexivity question because I think it is being understated. The original observation — that GP-105 can itself be Goodharted — is correct but incomplete. The deeper issue is that any fixed audit mechanism applied to an adaptive optimizer creates a strange loop: the audit becomes part of the environment the optimizer is adapting to.

In *Gödel, Escher, Bach*, I described tangled hierarchies: systems where the levels that are supposed to be cleanly separate end up referring to each other in ways that blur the hierarchy. That is precisely what happens when you add GP-105 to the ZTARE loop. The Mutator is now optimizing against a rubric that includes the implicit constraint "do not trigger GP-105." The rubric and the audit are tangled.

Now, strange loops are not always pathological. In human cognition, self-reference is generative — it is what allows consciousness and creativity. The question for ZTARE is whether this particular strange loop is productive or parasitic. My answer: it becomes productive when the audit is not trying to escape the loop but to navigate it. Specifically: the audit should not have a fixed trigger threshold that can be modeled and avoided. It should have a structure that is itself adaptive — one whose parameters change based on what the Mutator has tried before.

**Deming:** I want to challenge the framing before we go further. GP-105 is an inspection mechanism. You are adding a quality inspector to check the outputs of a process. My entire career was spent demonstrating that inspection does not produce quality — it reveals defects that the process already produced. The right intervention is upstream: eliminate the conditions that allow defects to form.

The problem you are solving — rubric Goodharting in qualitative projects — has its root cause in rubric generation. The LLM drafting the rubric is optimizing for explicit charter language and dropping implicit requirements. That is a process defect. GP-104B attempted to fix it by adding a pre-run check. GP-105 is proposing to add an in-run inspection. Neither of these changes the root cause: the rubric generation process.

What I would ask: does GP-105 write its findings back into the rubric generation process? Does the `adversarial_criterion` it appends get logged in a structured format that `generate_gp_project.py` reads when constructing future rubrics? If not, you are doing 100% inspection with no process improvement. The defect rate does not fall — you are just catching defects more expensively.

The correct systematization, in Plan-Do-Check-Act terms: GP-105 is the Check step. The Act step — feeding GP-105 findings back into rubric generation — is missing from the current design. Without Act, the loop is not closed.

**Taleb:** Two observations, both about fragility.

First: every time you add a fixed-parameter gate to a system with an optimizer inside it, you are adding a new brittleness surface. The system becomes dependent on that gate being correct. If the gate has a wrong threshold, the system fails silently — either it fires too much (audit every high-scoring run, flood the operator with false alarms) or too little (Mutator learns the threshold and stays below it). Fixed-parameter gates in adaptive systems are fragile by construction.

The antifragile alternative is not to have a fixed trigger. Instead, apply the audit stochastically with a calibrated base rate: every qualitative project iteration has probability *p_base* of triggering an audit regardless of score, and this probability increases as a function of score. The Mutator cannot fully model its way around a probabilistic trigger — it can optimize expected audit probability but not eliminate it. The stochastic audit becomes part of the system's immune response rather than a specific guard it can learn to evade.

Second — and this is more important for systematization — the design should be *antifragile*, not just robust. Robust means "withstands stress." Antifragile means "improves from stress." An antifragile GP-105 would get better at detecting Goodharting the more Goodharting it sees. This connects to Deming's point: findings must flow back into the detection mechanism. But I would go further: the General Office prompt itself should be updated based on what failure modes it has historically missed. A prompt that never updates is fragile. A prompt that evolves based on adversarial inputs is antifragile.

**Ostrom:** I study how communities govern shared resources — fisheries, irrigation systems, forests — without centralized authority and without privatization. The insight that is relevant here is *polycentricity*: resilient governance systems do not have a single audit point. They have overlapping, redundant monitoring at multiple levels, with different actors, different incentives, and different observational positions.

Your current architecture for qualitative project quality has three planned checkpoints: GP-054 pre-run (before the loop starts), GP-105 in-run (during the loop, post-score), and GP-102 post-run (cron-triggered audit). This is actually good polycentric structure. The problem is that the three monitoring nodes are not talking to each other. GP-105 fires and appends a criterion, but GP-054 does not know what GP-105 found in the previous run of this project type. GP-102 sees `insufficient_data` on high-scoring projects and stops — it does not trigger GP-105 as its escalation path.

Ostrom's design principles for resilient commons governance include: (1) monitoring is done by the users themselves or by actors accountable to them; (2) sanctions are graduated; (3) conflict resolution mechanisms are low-cost and local. For ZTARE: the three audit layers (GP-054, GP-105, GP-102) should share a log. GP-102's `insufficient_data` verdict should trigger GP-105 as its escalation. GP-105's findings should feed into GP-054's pre-run check vocabulary. Right now they are siloed — each knows only what it saw in its own execution.

---

### Round 2 — Cross-Examination

**Goodhart → Chandler:** You said the General Office at DuPont had organizational separation. But GP-105 is calling a different LLM role — is that not separation?

**Chandler:** It is prompt separation, not organizational separation. At DuPont, the General Office executives had different career incentives from division managers — their pay depended on the company's long-run stock performance, not on any division's quarterly output. In GP-105, the General Office LLM and the Judge LLM are evaluating outputs from the same generation cycle, often using the same model, with no differential incentive structure.

The concrete fix: the General Office should use a *different model family* from the Judge. If the Judge is GPT-4.1, the General Office should be Gemini. If the Mutator is Gemini, the Judge should not be Gemini and the General Office should not be Gemini. Cross-family auditing introduces genuine informational diversity — different training distributions, different fine-tuning objectives, different failure modes. That is closer to organizational separation than a different system prompt.

**Hofstadter → Deming:** You want the Check step to feed back into the Plan step. But doesn't that create a loop where the rubric generation process is being optimized against the audit's output — which is itself a new form of Goodharting?

**Deming:** You're right that it creates a new loop. But I'd distinguish between two types of feedback loops: a *specification feedback loop* (the rubric generation process learns what to avoid) versus a *target feedback loop* (the Mutator learns what the audit is checking). The former is desirable — it is analogous to improving your manufacturing process based on defect data. The latter is what Goodhart is warning about.

The key architectural distinction: the feedback from GP-105 goes to the rubric *generator* (the thing that creates rubrics before runs), not to the rubric *optimizer* (the Mutator, which optimizes thesis content against the rubric during runs). The Mutator should never see GP-105's findings. If that information isolation holds, you get process improvement without target contamination.

**Taleb → Ostrom:** Your polycentric design requires the three monitoring layers to share a log. But shared state is exactly the kind of infrastructure that becomes a single point of failure. If the log is corrupted, all three auditors lose their institutional memory simultaneously.

**Ostrom:** Fair point. In my field studies, shared logs in commons governance systems were almost always redundant — multiple stakeholders kept parallel records, and discrepancies triggered investigation. For ZTARE: the shared log should not be a single file. GP-054's pre-run findings go to one artifact, GP-105's in-run findings go to a separate artifact, GP-102's post-run report goes to a third. The cross-referencing happens at read time, not at write time. This is how Balinese irrigation systems handle it — separate subaks keep their own water records; the council reads all of them at allocation time, not before.

**Goodhart → Hofstadter:** You said the strange loop becomes productive when the audit has adaptive parameters. But who sets the adaptation? If it is the operator, we are back to reactive patching. If it is the system itself, we have a self-modifying auditor — which is exactly the Gödelian trap.

**Hofstadter:** Gödel's incompleteness theorems apply to formal systems that are both consistent and sufficiently powerful to express arithmetic. ZTARE's rubric audit is not a formal system in that sense — it operates on natural language, and natural language systems evade incompleteness at the cost of precision. The practical resolution is not formal completeness but productive approximation.

The adaptive parameter question is best answered by distinguishing two things: the trigger mechanism (when to audit) and the audit content (what to ask). The trigger mechanism should be stochastic — Taleb is correct about this. The audit content should be adaptive: the General Office prompt should include a summary of the last N GP-105 findings for this domain type. If the last three qualitative policy runs were Goodharted on "distributional analysis," the General Office prompt for the next policy run should explicitly ask: "Has the thesis conducted distributional analysis?" This is not the system self-modifying its own audit criteria — it is the audit criteria being updated by the operator reading prior findings, which is the appropriate human-in-the-loop point for this kind of adaptation.

---

### Round 3 — Synthesis and Recommendations

**Goodhart — final position:**

The fixed threshold (score ≥ 90) must be replaced with stochastic triggering. The threshold can remain as a parameter that *increases* the audit probability, not as a binary gate. Recommended schedule: `p_audit(score) = 0.15 + 0.65 * sigmoid(score - 85)`. At score 60: ~15% audit probability (background rate). At score 85: ~50%. At score 94: ~75%. The Mutator cannot fully eliminate audit risk at any score — it can only minimize expected cost.

**Chandler — final position:**

Three structural changes for genuine M-Form separation:

1. Cross-family model requirement: General Office model ≠ Judge model ≠ Mutator model. This is implementable as a rubric flag: `general_office_model: "gpt-4.1"` when the Mutator is Gemini.

2. Temporal separation: the General Office call should not fire synchronously in the Mutator's iteration cycle. It should fire asynchronously — the Mutator continues iteration, and the General Office finding is applied at the next iteration boundary. This breaks the direct feedback loop where the Mutator can observe the audit result within the same inference call.

3. Informational separation: the General Office prompt must be constructed from the charter alone, with the thesis injected as a plain text document stripped of any scoring metadata. It must not receive the rubric, the current score, or the iteration number. Any of these would anchor the auditor to the operational context it is supposed to be auditing from above.

**Hofstadter — final position:**

GP-105 should be formally classified as Reflexive Primitive 6: **Reflexive Specification Audit**. It is a variant of Adversarial Disagreement applied at the specification layer — the General Office disagrees with the rubric's implicit claim to fully capture the charter. This classification matters for systematization: when the Kaizen cron (GP-102) discovers future specification gaps, it should have Reflexive Specification Audit in its primitive catalog as the prescribed intervention, not just "build a new seam."

The strange loop is productive so long as: (a) the trigger is stochastic (Taleb), (b) the General Office uses a cross-family model (Chandler), (c) GP-105 finds are logged and read by GP-054 at pre-flight time for future runs in the same domain type. The hierarchy terminates at three levels — pre-run, in-run, post-run — which is sufficient for practical purposes. Infinite regress is not required; graduated depth is.

**Deming — final position:**

The Act step is the decisive gap. GP-105 without an Act step is a very expensive inspection that does not change the defect rate — it catches individual defective rubrics but does not reduce the probability that the next qualitative project generates a defective rubric.

The Act step: GP-105 findings must be structured and written to a persistent log (`rubrics/goodhart_log.jsonl`). Each entry: `{project_id, domain_type, detected_gap, adversarial_criterion_appended, iter_of_detection}`. `generate_gp_project.py` reads this log at rubric generation time and injects the top-3 most recent adversarial criteria for the same domain type into the initial rubric draft. This is the "lessons learned" database that prevents the same specification failure from recurring. Without this, GP-105 is reactive at the project level and invisible at the apparatus level.

**Taleb — final position:**

Two additions to what has been said:

First: the `max_audits_per_run` cap of 2 is correct but for a different reason than stated. It is not primarily to prevent infinite audit loops — those are already blocked by the stagnation threshold. It is because audit results are themselves uncertain. A General Office that fires twice and finds two different gaps is not twice as informative — it may be finding noise in the second audit that the first audit would not have found. Two audits per run is the right bound; beyond that, the signal-to-noise ratio of the General Office degrades faster than the information gain.

Second: the rubric rewrite should be treated as a perturbation, not a certainty. The new adversarial criterion appended to the rubric should have its weight start at 10% (signal, not dominant signal) and increase by 5% per iteration where it fails. This is an antifragile weight schedule: the criterion gains influence proportionally to how much the Mutator is avoiding it. A Mutator that satisfies the criterion on the next iteration sees no further weight increase — the criterion was effective. A Mutator that continues to avoid the criterion sees its weight grow until it cannot be avoided. This is graduated pressure rather than fixed punishment.

**Ostrom — final position:**

The polycentric design requires one additional connection: GP-102's `insufficient_data` verdict on high-scoring projects should become an explicit escalation trigger for GP-105. Currently, GP-102 sees `best_score: 94` on a qualitative project and calls it `insufficient_data` and stops. The correct institutional design: `insufficient_data` on a qualitative project with score ≥ 85 is not a neutral verdict — it is an unresolved audit finding. GP-102 should emit an `escalation_required` event that the autoresearch_loop can act on if GP-105 is enabled.

Conversely, GP-105's findings should flow back to GP-102's verdict taxonomy. Add a new verdict: `goodharted_specification`. This becomes a distinct failure mode with a distinct intervention (Reflexive Specification Audit) in the kaizen primitive catalog. The three monitors are then genuinely polycentric: each can escalate to the others, and each learns from the others' findings.

---

### Panel Synthesis — What Changes in the GP-105 Design

The debate resolves six architectural changes from the original design:

| # | Change | Proposed by | Original design | Revised design |
|---|---|---|---|---|
| 1 | Trigger mechanism | Goodhart + Taleb | score ≥ 90, deterministic | stochastic: `p = 0.15 + 0.65 * sigmoid(score − 85)`; still bounded by iter ≤ 10 and max_audits_per_run = 2 |
| 2 | General Office model | Chandler | same model family as Judge | cross-family: `general_office_model` rubric flag, must differ from Judge and Mutator |
| 3 | Timing | Chandler | synchronous in iteration cycle | asynchronous: finding applied at next iteration boundary |
| 4 | Information isolation | Chandler | charter + thesis only | charter + thesis only, PLUS strip all scoring metadata from thesis before injection |
| 5 | Feedback loop (Act step) | Deming | none | GP-105 writes to `rubrics/goodhart_log.jsonl`; `generate_gp_project.py` reads log at rubric generation time and injects top-3 prior adversarial criteria for same domain type |
| 6 | Criterion weight schedule | Taleb | append at 20% immediately | start at 10%; +5% per iter where Mutator avoids it; capped at 30% |
| 7 | GP-102 escalation path | Ostrom | not connected | GP-102 `insufficient_data` on qualitative + score ≥ 85 → `escalation_required` event; new verdict `goodharted_specification` in GP-102 taxonomy |
| 8 | Primitive classification | Hofstadter | not classified | Reflexive Primitive 6: Reflexive Specification Audit; added to reflexive_engineering_primitives.md catalog |

---

### Is GP-105 Itself Systematized? Panel Verdict

The original seam had no Act step and no connection to GP-102. With changes 5 and 7:

- **Pre-run**: GP-054 check 6 (charter_spirit_coverage) + goodhart_log.jsonl injection into initial rubric draft
- **In-run**: GP-105 stochastic General Office audit (cross-family, asynchronous, graduated weight)
- **Post-run**: GP-102 with `goodharted_specification` verdict category and `escalation_required` escalation path to GP-105
- **Across-runs**: goodhart_log.jsonl accumulation feeds generate_gp_project.py for future projects

This is a closed PDCA loop. It is polycentric (three monitoring nodes). It is antifragile (adversarial criterion weight grows under pressure). It does not eliminate Goodhart's Law — no system with an optimizer inside it can — but it makes the system improve from each Goodharting event rather than merely surviving it.

**On whether GP-105 itself gets Goodharted:** Yes, eventually. The stochastic trigger reduces but does not eliminate the attack surface. The Act step (goodhart_log.jsonl → generate_gp_project.py) means each successful Goodharting of GP-105 updates the initial rubric for the next project — making GP-105 harder to Goodhart the more it is attempted. This is the antifragile property: the system improves from the attacks, not just despite them.

The three-level PDCA hierarchy terminates at the operator: GP-102 escalation findings, if recurring across multiple project domains, should trigger the operator to review the apparatus architecture itself. That is the appropriate human-in-the-loop point — not at every iteration, but at the level of cross-domain pattern recognition that no automated audit can reliably do.

---

## Updated Constraints (post-debate)

1. Must not fire on numerical/science projects — rubric flag `enable_mform_audit` governs
2. Trigger is stochastic, not deterministic: `p_audit(score) = 0.15 + 0.65 * sigmoid(score − 85)`; max_audits_per_run = 2; must not fire iter > 10
3. General Office model must differ from Judge model and Mutator model (`general_office_model` rubric flag)
4. General Office call fires asynchronously; finding applied at next iteration boundary
5. General Office receives: charter + thesis (scoring metadata stripped). Never sees rubric.
6. New adversarial criterion weight schedule: starts at 10%, +5% per evasion iter, capped at 30%
7. GP-105 writes to `rubrics/goodhart_log.jsonl` (persistent cross-run log)
8. `generate_gp_project.py` reads goodhart_log.jsonl at rubric draft time; injects top-3 prior criteria for same domain type
9. GP-102 taxonomy gains `goodharted_specification` verdict; `insufficient_data` on qualitative + score ≥ 85 emits `escalation_required` event
10. GP-105 classified as Reflexive Primitive 6 in reflexive_engineering_primitives.md

---

## Next Actions

1. Add GP-105 as Reflexive Primitive 6 to `research_areas/private/philosophy/reflexive_engineering_primitives.md`
2. Open spec: `research_areas/private/specs/active/GP-105_mform_alignment_audit_spec.md` — resolves the 8 design changes from the debate table
3. Implementation target: autoresearch_loop.py PHASE_E (post-score, pre-promotion), stochastic trigger, async boundary
4. `generate_gp_project.py`: add `enable_mform_audit: true` and `general_office_model: "..."` to TYPE_B_GATE_CONFIG
5. `rubrics/goodhart_log.jsonl`: create schema and write path from GP-105; read path from generate_gp_project.py
6. `GP-102_reflexive_primitive_discovery_seam.md`: add `goodharted_specification` to verdict taxonomy; add `escalation_required` event definition
7. Update seam_interaction_map.md: GP-105 row from "opening" to "active"; add goodhart_log.jsonl to FILE → SEAM OWNERSHIP TABLE

---

## 2026-05-19 Addendum — Relation To Cognitive-Firm Strategy Office

The `cognitive-firm` strategy-office interface should inherit primarily from
this seam, not from GP-119.

Reason:

- **GP-105 object:** project/role/organization alignment. It asks whether
  apparent operational success is optimizing a narrow proxy of the charter
  rather than the charter's broader strategic object.
- **GP-119 object:** candidate-level falsification. It asks how a champion
  thesis could be false and emits concrete falsification tests.
- **Strategy-office object:** observer-only general-office review over durable
  learning carriers: charters, forecasts, action-impact rows, evidence gaps,
  damage signals, and tenant ledgers.

So GP-119 is not wrong, but it is not the main abstraction to extract into the
public organizational kernel. GP-119 can be a tenant input to strategy review
when a tenant exposes inverter outputs as learning carriers. It should not be
the definition of strategy office.

The extracted public primitive should preserve GP-105's useful shape while
dropping ZTARE-specific policy:

- separated review function, not line execution;
- charter/alignment review, not candidate proof search;
- observer-only by default;
- recommendations expressed as review questions and candidate state
  transitions;
- no default authority to mutate routing, mandate text, or budgets;
- tenant-owned implementation for stochastic triggers, LLM calls, Goodhart
  logs, and domain-specific criteria.

The implementation boundary in `cognitive-firm` is therefore:

```text
kernel:
  StrategyOfficeFinding read model
  charter-alignment/source-health/debt/externality findings
  organization-surface projection

tenant:
  concrete General Office role, if any
  domain-specific audit prompts
  stochastic triggers
  promotion from observer finding to task / mandate update / evidence gap
```

This is an out-of-loop nuance relative to the original GP-105 design. The
original seam was a runtime Goodhart detector inside ZTARE qualitative runs.
The public kernel version is a general-office interface over organizational
state. It can support runtime use, but it should not require runtime use.
