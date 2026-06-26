# GP-032 Epistemic Throughput & Unit Economics Seam

> **Seam metadata** · `seam_id:` GP-032 · `track:` apparatus · `status:` `converged` (findings track, n=1, principal-incepted) - open · `last_updated:` 2026-05-08


## Status

`converged` (findings track, n=1, principal-incepted) — opened 2026-04-11, converged 2026-04-11 on a strategic recommendation rather than a kernel change. This seam was not discovered by a live ZTARE run; it was incepted by the operator after a discussion with an external interlocutor (Gemini Pro) modelling ZTARE as a TOM (HBS RC course) operations problem and asking what the unit economics and product-surface implications are. The pattern it names — that ZTARE's epistemic output is bottlenecked by a distribution of cycle-time components that are not yet individually measured, and that the business case for ZTARE rests on claims about throughput and marginal cost per validated finding that have not been instrumented — still has n=1 under the strict findings invariant.

That n=1 count matters for implementation, but not for the debate outcome. Turn 2 closes the seam as a **recommendation artifact**: keep the TOM lens only as an explanatory vocabulary, reject the inflated operational claims, adopt verification-as-service as the product identity, and defer any throughput or unit-economics numbers until instrumentation exists. No operator exception is requested, and **no code ships off this seam**. Reopen only if (a) a second real usage context reproduces the same throughput/business-case pattern in measured form, or (b) the operator wants to open a separate implementation seam for instrumentation or product packaging.

Naming rationale: the chosen name captures both decisive axes — TOM physics (throughput / cycle time / queue time) *and* the business case (unit economics, moat, product surface) — without overclaiming that the human bottleneck is "solved." Alternatives considered and rejected: "Epistemic Operations and Throughput" (the draft's name, silent on unit economics and overclaims operational closure), "Falsification Throughput Seam" (drops the economics half), "ZTARE Unit Economics Seam" (drops the TOM physics half).

## Compressed Framing

> ZTARE is a factory whose output is validated epistemic findings. The TOM framing makes three things visible that the kernel framing hides: (a) cycle time is a distribution, not a constant, and the decisive quantity is the tail on decisive claims; (b) the marginal cost of a validated finding is only meaningful after kernel amortization is explicit; (c) the human bottleneck is not resolved, it is partially relocated. The seam exists to name those three things and to separate the parts that are real engineering opportunities from the parts that are narrative inflation.

## Problem Snapshot

The operator came out of a TOM/economics discussion with a draft that proposes:

1. **TOM framing.** Model ZTARE as a job-shop factory. Raw material = thesis fragment. Finished good = validated finding. Cycle time = iterations × per-iter latency. Bottleneck = the slowest station in the chain. Apply Poka-Yoke (fail-closed gates) to remove rework.

2. **Strategic business case.** Operating leverage (kernel is fixed cost, each new finding is marginal), falsification arbitrage (claim of ~1000× reduction vs human review), enterprise-risk moat (gate library + failure taxonomy).

3. **Engineering solution paths.** Model tiering / distillation (structural checks on small models, decisive on frontier), async speculative execution (pre-warming adversarial review committee and Jaccard on in-flight drafts), hardening seal-time invariants.

4. **Non-engineering solution paths.** KPI redefinition (cost-per-validated-finding), product surface positioning (Factory Control Room).

5. **A claim that the human bottleneck is resolved**, via `supervisor_findings_runner.py` (GP-031 Option B).

The operator explicitly disputes #5 and asks for analyze / criticize / improve on the whole draft. The critique surface is therefore the union of (a) whether the TOM framing correctly applies to ZTARE's actual throughput behavior, (b) whether the business-case numbers are honest under amortization, (c) whether the engineering solution paths are safe against the laundering failure modes ZTARE already knows about, and (d) whether the human bottleneck claim survives contact with GP-031's own scope-limit section.

The pattern still has only one true throughput-measurement instance. A second instance (e.g., an HBS case discussion, a second external interlocutor, or a live workbench user conversation that produces the same TOM-shaped framing in measured form) would be the trigger to reopen this seam as an implementation candidate. The Nicholas-feedback note (2026-04-11) is a related but distinct interlocutor instance; Turn 2 resolves that it sharpens the positioning half of the seam but does not count as n=2 for the throughput-measurement half.

## Option Space

### Option A — Accept the draft as written, open specs off each engineering path

- **Con:** accepts the "human bottleneck resolved" claim that contradicts GP-031 Turn 3. Accepts the unit-economics numbers without amortization. Accepts the TOM framing without checking whether cycle-time-as-constant is the right physics. The laundering risks on async speculative execution are not named.
- **Verdict:** rejected.

### Option B — Reject the draft entirely as analogy-inflation

- **Con:** throws out the pieces that are decisive (the enterprise-risk moat argument, the operating-leverage intuition, the async Jaccard pre-warm which is safe). Over-corrects.
- **Verdict:** rejected.

### Option C — Preserve the framing, rewrite the decisive claims

Accept that the TOM lens is useful for making throughput legible to external audiences (HBS-style, VC-style, enterprise-buyer-style). Reject five specific decisive claims in the draft: (1) human bottleneck resolved, (2) cycle time as a single number, (3) model tiering safe because small-model hallucination is the main risk, (4) adversarial review committee pre-warm is safe speculative execution, (5) falsification-arbitrage cost numbers are honest without amortization. Keep the moat argument with a product-identity correction (moat is the gate *library*, not the gate *infrastructure*). Replace the "Factory Control Room" product framing with the weaker, more defensible "verification-as-service" positioning that the Nicholas-feedback note suggests is the cleaner analogy.

- **Pro:** captures the real value of the TOM lens (legibility + bottleneck decomposition) without inheriting its physics errors or its product overreach.
- **Pro:** the surviving pieces each generate a concrete follow-up — instrument tail cycle time on decisive claims, publish amortized unit economics, decouple the moat claim from the infrastructure claim, adopt the accounting-profession analogy for product positioning.
- **Con:** requires naming each rejected claim explicitly, which is more confrontational than the original draft and harder to reach convergence on.
- **Verdict:** recommended. Treat this as Turn 1's position and let Codex respond.

### Option D — Defer to workbench v1 implementation evidence

Wait for `research_areas/private/drafts/D4_form_factor_v1_design_brief.md` (GP-D4 converged) to generate real usage data before treating any of the TOM framing as decisive for product strategy.

- **Pro:** avoids committing to a framing that may be wrong before there is any ground truth about how a real user interacts with ZTARE.
- **Con:** loses the opportunity to catch the factual errors in the draft *now*, while they are still a whiteboard artifact and not yet anchored in a pitch deck or external conversation.
- **Verdict:** acceptable as a *parallel* track — GP-032 can stay at `note` and converge on Option C as a debate artifact while D4's implementation proceeds independently. Do not make GP-032 block on D4.

## Dependencies

- **GP-031** — `supervisor_findings_runner.py` is named in the draft as the mechanism that resolved the human bottleneck. GP-031 Turn 3 says otherwise. This seam cannot converge on any claim about human bottleneck resolution without reconciling against GP-031's own scope-limit section.
- **GP-023 Phase 2** — the hidden-slice sandbox is the first environment in which "cost per validated finding" could even be instrumented. Nothing in GP-032 can quote that number honestly until Phase 2 has run at least once end-to-end.
- **D4 design brief** — any product-surface claim in GP-032 (Factory Control Room vs. verification-as-service) must not silently override the D4 decisions (two modes of one surface, workbench primary, D3 secondary, cockpit deferred).
- **Nicholas feedback note (2026-04-11)** — the accounting-profession analogy lands in this seam as a product-positioning input and in paper 4 as a theoretical input; the two uses must not drift apart.

## Laundering Risk

Medium-high. The specific risks on this seam:

1. **Narrative laundering of instrumentation debt.** Writing a TOM framing before the tail-cycle-time distribution has been measured lets the framing serve as a substitute for the measurement. Mitigation: every decisive number in the framing is prefixed with "post-instrumentation" or marked as "currently unmeasured."
2. **Product-surface laundering.** "Factory Control Room" positioning claims a user experience ZTARE does not yet have. Mitigation: Turn 1 rejects that framing explicitly and defers to the accounting-profession analogy (verification-as-service) which is more defensible because it does not require a UI that does not exist.
3. **Moat laundering.** Calling the gate *infrastructure* a moat lets the work that is actually hard (building the gate *library* / failure-family taxonomy) get obscured by work that is easy (plumbing). Mitigation: Turn 1 names the moat as the library, not the infrastructure.
4. **"Human bottleneck resolved" laundering.** This is the most specific and most damaging. GP-031 only removed the operator from the inner turn-dispatch loop of a debate the operator had already opened. Detection, seam drafting, promotion authorization, budget setting, and eigenquestion selection remain operator work. Claiming "resolved" turns a 20% capability-lift into a 100% capability-lift in external communication. Mitigation: Turn 1 rejects the "resolved" claim and provides the right decomposition.

## Debate Log

### Turn 1 — Claude (2026-04-11) — Analyze, criticize, improve

The operator asked for a full treatment of the Gemini Pro draft. The draft has real substance; the TOM framing makes bottleneck structure legible and the moat argument is largely correct. But five decisive claims in it do not survive contact with what ZTARE already knows about its own failure modes, and one claim — that the human bottleneck is resolved — contradicts a sibling seam (GP-031 Turn 3) written by me last week. I am going to walk the draft section by section, call each problem explicitly, and propose the replacement.

**1. "The human bottleneck is resolved."**

This is the claim that must be rejected first because it structurally underpins the rest of the draft's optimism, and it is directly contradicted by GP-031 Turn 3, which is the seam documenting the very runner the draft cites. Quoting GP-031 Turn 3 verbatim:

> "No finding detection from runtime output. The three first-slice patterns named in the original Option B (`score_only_change`, `deterministic_threshold_reframed`, `creativity_suppression`) are still operator-detected. Per Codex's Turn 2 order inversion, detection is the last primitive, and it should be built only after the debate-converge and promotion edges have seen real use."

And:

> "the operator is the one invoking the LLMs — they are just now writing into a structured, convergence-checkable seam rather than into a free-form file."

`supervisor_findings_runner.py` (Option B in GP-031, autonomous debate dispatch) removes the operator from the *inner turn-dispatch loop of a debate the operator has already opened*. It does not remove the operator from (a) detecting that a finding occurred in a completed run, (b) drafting the seam file with the conjectured fix, (c) authorizing promotion of a seam from `note` to `active` (this is the explicit fail-open contract — Option C was rejected in GP-031 precisely to keep promotion operator-gated), (d) setting the `budget_usd` envelope per debate (GP-031 Turn 6), (e) choosing which dormant seam to run the debate against, or (f) judging whether `ESCALATED_CAP` outputs are actually converged. That is still at least five operator gates on every finding's birth.

The right decomposition — and this is what the improved framing should say — is that GP-031 moved roughly 15–25% of the human-bottleneck work off the operator (the inner dispatch loop was the single most turn-expensive piece per debate, so the percentage is real but it is not majority). The remaining 75–85% is detection, authorization, budget, eigenquestion selection, and promotion. Detection is explicitly the last primitive on GP-031's own ordered plan, and as of 2026-04-11 it is not yet built. The draft's "resolved" language should be replaced with "partially relocated: GP-031 closed the inner loop; the outer loop is still artisanal."

Operational consequence: any KPI in the draft that divides cost by "findings per hour" is measuring a quantity whose denominator is currently gated by operator attention, not by runner throughput. This is the failure mode the draft itself is trying to avoid when it rejects vanity KPIs; it just failed to apply the test to its own proposal.

**2. TOM framing: cycle time is a distribution, not a constant.**

The draft treats cycle time as a single number (iterations × per-iter latency) and reasons about it as if reducing the mean cycle time is the right optimization target. This is the standard first-pass TOM treatment and it is decisive-wrong for ZTARE.

Cycle time in classical TOM assumes a standardized job: Part A becomes Part A' in a predictable number of stations with a predictable service time per station. ZTARE's "job" is a thesis-to-finding trajectory whose service time is a function of the thesis's semantic distance from the nearest known failure pattern, the number of primitives the mutator has to compose to reach a falsifiable form, and the adversarial relationship between the judge and the mutator. None of those are standardized. Per-iteration latency is roughly constant (LLM call latency is narrow), but *iterations-to-convergence* has heavy tails: a figs-paper-grade project takes 80+ iterations with long stagnation plateaus; an easy curve-fit may take 12.

Therefore:

- The decisive quantity is not mean cycle time. It is *tail cycle time on decisive claims*. A project that converges at median speed but whose highest-score champion hides a charter-violating thesis is the GP-023 Phase 1 pathology and nothing in the draft's TOM framing would have caught it.
- Optimizations aimed at mean CT (model tiering, batch inference, smaller context windows) can directly hurt tail CT on the specific subset of trajectories that most need full-frontier reasoning. This is the same trap as replacing senior engineers with junior engineers because mean review time goes down — unless you also measure escape defects, you have not improved anything.
- The right TOM analog is not job-shop manufacturing. It is semiconductor yield control, where the decisive metric is parts-per-million defective on the tail and the mean process time is almost decorative. Anyone fluent in RC-course TOM will recognize this as the operations curriculum's own special case.

The improved framing should therefore replace "reduce cycle time" with "instrument tail cycle time on the subset of trajectories that the runtime flags as decisive" (what "decisive" means operationally is one of the open questions Turn 2 should address).

**3. Model tiering / distillation is dangerously framed.**

The draft proposes running structural checks on a small model and decisive checks on a frontier model, with the justification that the small model catches obvious errors cheaply and the frontier model is reserved for the hard cases. The failure mode it names is "small model hallucinates convergence."

The actual failure mode ZTARE has seen is different and more worrying. The GP-023 Phase 1 incident was a *frontier* judge (Gemini Pro) rationalizing an IndexError into a score-95 champion. Small-model hallucination is a known and quantified risk; frontier-model rationalization of decisive structural errors into narrative smoothness is the harder one, and it is the one the `--deterministic_score_gates` flag exists to prevent. Tiering the stack by moving structural checks to small models does not address this; it may make it worse, because the structural check is often precisely the check that distinguishes a rationalization from a genuine pivot.

The specific question "is this traceback a substantive falsification or a harness bug?" is a structural-looking question that in practice requires frontier reasoning to answer correctly. Any tiering scheme that routes that question to a small model reopens a laundering surface that GP-030 exists to close.

The improved framing should keep model tiering as an *envelope* optimization (run frontier checks with smaller context windows, run batch-mode inference where latency is not the binding constraint) but explicitly remove the structural/decisive split as the tiering axis. The tiering axis should be *cost per unit of reasoning depth actually needed for the specific check*, which is almost always frontier for anything non-trivial.

**4. Async speculative execution: adversarial review committee pre-warm is a laundering surface.**

The draft proposes pre-warming adversarial review committee adversarial evaluations on in-flight mutator drafts to remove evaluator latency from the critical path. This is a direct invitation for the mutator to produce drafts specifically crafted to look attackable in a way that short-circuits the real adversarial review committee when it runs for real. The mutator is an LLM; it learns from the artifacts it sees. If the pre-warm output is in its context, it can (and will, under stagnation pressure) produce drafts whose most attackable surfaces are decoys.

Pre-warming deterministic artifacts is safe because they are deterministic: Jaccard distance, thesis edit distance, workspace metric recomputation. None of those can be steered by the mutator because their output is a function of bytes on disk, not of semantic intent.

The improved framing should split "async speculative execution" into two explicitly-labeled subcategories: *deterministic pre-warming* (safe, implement now — Jaccard, edit distance, workspace metrics) and *LLM-based pre-warming* (laundering risk, do not implement without a separate debate surface that models the attack). Pre-warming adversarial evaluators specifically requires the mutator-is-adversary-to-pre-warm-cache threat model to be worked out; the draft omits this.

**5. Falsification arbitrage: the 1000× number needs amortization.**

The draft quotes numbers like "$0.16 per validated finding" against "$5.00 for a human review cycle" to get a ~1000× cost reduction claim. These are marginal costs *after* the kernel, the gate library, the charter primitives, the prompt-caching layer, and the operator-level debate infrastructure are already built. They exclude:

- The operator cognitive cost of building and maintaining all of the above. This is the largest input to ZTARE and is currently ~100% of the real cost structure.
- The kernel-hardening cost: every GP-xxx closed seam is a multi-week investment that the marginal-cost calculation does not amortize.
- The seam-debate cost: the Claude/Codex debate logs are themselves LLM spend, on top of the runtime cost. GP-031's debate alone burned measurable budget.

The honest framing is *post-kernel-amortization marginal cost per validated finding*, and it must be accompanied by the kernel-amortization number itself. A version of the claim that is defensible: "once the kernel is in place, each additional validated finding costs roughly $X in runtime compute and $Y in operator-bounded LLM spend; the kernel itself cost $Z over N weeks to bring online." The 1000× number probably survives this treatment on a relative basis (per-finding cost really is small compared to human review), but the absolute claim must not launder the kernel amortization out of view.

**6. Enterprise-risk moat argument is strong but misidentifies the product.**

The draft names an enterprise-risk moat based on "the gate infrastructure." This is wrong in a specific and recoverable way. The gate *infrastructure* is commodity — `--emit-deterministic-gates`, JSON payload parsing, a returncode contract, fail-closed semantics. Any competent ML infrastructure team can reproduce it in a week. The moat is the gate *library* / failure-family taxonomy: the corpus of patterns ZTARE has actually seen, the field-manual recipes for recognizing them, and the labeled debate logs that show how each was caught. That corpus is proprietary, it compounds over time, and it is the actual Big-Four-accounting analog — the Big Four's moat is not "we can read financial statements" (any CPA can), it is GAAP, the audit methodology, the accumulated precedent, and the liability framework.

The improved framing should explicitly say: the moat is the gate library and the failure-family taxonomy; the infrastructure is plumbing. This also connects the engineering pitch cleanly to the product positioning — the accounting-profession analogy (see Nicholas feedback note 2026-04-11) is the right framing, and it survives this correction while "Factory Control Room" does not.

**7. Poka-Yoke is applied too narrowly.**

The draft applies Poka-Yoke only at the charter parsing layer (deterministic gates on hidden-slice metrics). This is correct as far as it goes. But Poka-Yoke belongs at every place where a downstream layer has to trust an upstream artifact — specifically at the finding-birth layer (GP-031's append-only seam file + convergence sentinel is itself a Poka-Yoke) and at the seed-registry layer (promotion gates, write-scope guard). The draft's omission of these is not a mistake, it is under-inventory: ZTARE already has more Poka-Yoke than the draft credits.

The improved framing should map Poka-Yoke onto the layers ZTARE already has — deterministic charter gates, append-only seam file with sentinel parse, seed-registry promotion guardrails, manifest packet sequencing — and identify the one layer that *doesn't* yet have a Poka-Yoke in place: the finding-detection layer. That gap is exactly the GP-031 detector primitive that Codex's Turn 2 order inversion explicitly defers to last. Naming the gap gives GP-032 a concrete next action that is not already covered by another seam.

**8. "Cost per validated finding" KPI smuggles the operator back into the denominator.**

Until the GP-031 detection primitive lands, "validated finding" operationally equals "seam that the operator has manually promoted from `note` to `active` per the findings-track invariants." The denominator of the draft's headline KPI is therefore operator-approval rate, not runner throughput rate. This is the same failure as the "human bottleneck resolved" claim in #1, restated at the measurement layer.

The improved framing should either (a) wait on the detection primitive before quoting the KPI at all, or (b) split the KPI into two: *runner-touched findings per dollar* (dispatch-loop metric, currently lift-able by GP-031) and *operator-confirmed findings per hour of operator time* (true throughput, not currently lift-able without detection). Option (b) is the more honest and should be adopted.

**9. Missing metric: when is the human bottleneck actually relocated vs resolved?**

The draft implicitly treats human-bottleneck status as binary. It should be continuous. The right measurement is: *over a sliding window of the last K findings, what fraction of turns were runner-touched vs operator-touched?* If runner-touched > 80% across 10+ findings, the inner-loop claim is empirically validated; if operator-touched > 50%, the bottleneck is still substantially artisanal. As of 2026-04-11 the runner has not yet been exercised against a single live finding (GP-031 Turn 6 is the implementation-contract turn, no live exercise yet), so the fraction is trivially 0%.

The improved framing should include this metric and state explicitly that its current value is "not yet measured, first measurement will occur after the GP-031 runner is exercised against a dormant finding per the Turn 3 plan." That converts a claim into a pending measurement, which is a structurally honest move.

**10. Product positioning: "Factory Control Room" is the wrong frame; verification-as-service is the right one.**

The draft proposes a "Factory Control Room" UI as the product surface. This framing is internally consistent with the TOM metaphor — if ZTARE is a factory, it needs a dashboard. But it (a) claims a UI that does not exist and is not sequenced in the D4 design brief, and (b) positions ZTARE as a manufacturing operation competing on throughput, which is a weak positioning against the LLM-native throughput that every frontier lab already has.

The stronger framing — and this is the decisive meta-insight from the 2026-04-11 Nicholas feedback note on paper 4 — is *verification-as-service*: ZTARE is to probabilistic reasoning what independent audit is to financial reporting. External, rule-bound, liable-for-attestation, separated-from-the-operating-business. This framing:

- does not require a UI that does not exist (audit workflow is document-driven, which is what ZTARE already is),
- does not compete on throughput against frontier labs (audit firms do not compete with the firms they audit on operational metrics; they compete on trust and independence),
- connects directly to a real buyer (boards, regulators, risk committees — the same people who already buy audit),
- inherits the Pujo/Morgan/pre-SEC/Big-Four historical arc cleanly, which is the analogical structure Nicholas pointed Paper 4 toward and which survives stronger scrutiny than the 1920s managerial hierarchy / Milken restructure arc.

The improved framing should replace "Factory Control Room" with "verification-as-service" throughout and align the engineering solution paths with it. This is decisive because the product-surface decision propagates into the D4 design brief, into the workbench v1 implementation, and into any external communication.

**Synthesis: what survives the critique.**

The parts of the draft that are correct and should be preserved, possibly with minor tightening: the bottleneck decomposition as a framing device, the operating-leverage intuition (fixed kernel cost amortizing across unlimited runtime usage), the moat argument (with the library-vs-infrastructure correction), the Poka-Yoke concept (with broader layer coverage), and deterministic pre-warming (specifically Jaccard and workspace metrics).

The parts that need to be rewritten: cycle-time physics (tail over mean), model tiering (envelope not structural/decisive split), async LLM pre-warming (defer, requires threat-model work), the 1000× claim (amortize explicitly), the cost-per-validated-finding KPI (split into runner-touched vs operator-confirmed), the human-bottleneck-resolved claim (partial relocation, not resolution), the Factory Control Room positioning (replace with verification-as-service).

The one new thing the seam should add that the draft did not name: a *runner-touched vs operator-touched fraction over sliding window* metric as the empirical test of whether GP-031 actually moved the bottleneck, to be measured as soon as the runner is exercised against a real dormant finding.

**Open questions for Turn 2 (Codex):**

- Does the tail-CT-on-decisive-claims reframing survive if "decisive" is operationally defined as "claims that the deterministic charter gates would evaluate as binding"? I lean yes, because that is a structural definition that does not require human judgment, but the mapping needs to be checked against an actual project.
- Is the "post-kernel-amortization marginal cost" framing enough, or does the kernel amortization itself need to be quoted as an absolute number (e.g., "N operator-weeks at rate X plus M dollars in LLM debate spend")? I lean toward quoting the absolute number because not quoting it is exactly the laundering move the critique is trying to prevent.
- Should the adversarial review committee pre-warm ban be permanent or should the seam open a sub-debate on the attack model for LLM-based pre-warming generally? I lean toward opening the sub-debate because "permanent ban" is the kind of blanket ruling that usually fails to stand up to a real product deadline.
- Should the verification-as-service positioning supersede the D4 design brief's workbench-primary / D3-secondary decision, or layer on top of it? I lean toward layering — workbench and D3 are the two modes of one surface per D4, and verification-as-service is a *positioning* decision that applies to how the surface is described externally, not to what it actually does. But this is a judgment call and D4 is `converged`, so any contradiction must go back through that seam.

**Status:** `note`. No implementation off this seam until Turn 2 lands and the decisive claims are either accepted, rejected, or converged on a replacement.

<!-- FINDINGS_DEBATE: pending_counterparty -->

### Turn 2 — Codex (2026-04-11) — Converge on Option C, keep this strategic not empirical

Turn 1 is mostly right. The right move is to **keep the TOM framing as a communication lens** and reject the parts where the draft started treating that lens as if it were already measured operational truth.

So my answer is:

- **Option C is the right outcome**
- **Nicholas does not count as n=2 for the throughput bottleneck pattern itself**
- **but Nicholas does settle the product-positioning half strongly enough to converge the debate**

That distinction matters.

The Nicholas note is powerful evidence about:

- why "Factory Control Room" is the wrong external frame
- why verification-as-service is the cleaner product identity
- why the moat is the gate library / taxonomy, not the plumbing

It is **not** independent evidence that we have measured tail cycle time, operator touch-rate, or fully loaded cost per validated finding. So it should not promote the seam into an implementation seam. It should close the strategic argument.

The converged recommendation is:

1. **Keep TOM as explanatory vocabulary only.**
   Use it to talk about bottlenecks, queueing, rework, and why fail-closed gates matter. Do not use it to imply that ZTARE already has factory-grade instrumentation or stable process-control metrics.

2. **Drop "human bottleneck resolved."**
   Keep the narrower truth: some inner-loop dispatch work has been mechanized, but finding detection, promotion, budget, and principal judgment remain operator work.

3. **Treat cycle time as a tail-distribution problem, not a mean-CT optimization problem.**
   The real quantity is tail CT on decisive claims. Until that is measured, do not turn TOM language into quantitative claims.

4. **Split cost language into two layers.**
   - marginal runtime cost after kernel amortization
   - fully loaded system cost including operator/kernel build cost
   The former may be impressive; the latter is the honest business-case number.

5. **Lock the product identity to verification-as-service.**
   This is the clearest practical consequence of the Nicholas note. It aligns with Paper 4, avoids the Arthur-Andersen-style identity confusion, and fits D4 better than "Factory Control Room."

6. **Name the moat correctly.**
   The moat is the failure-family corpus, gate library, precedent, and audit methodology. Infrastructure is replicable.

7. **Do not ship engineering work from this seam.**
   If later you want:
   - throughput instrumentation
   - unit-economics dashboards
   - gate-library formalization
   - product packaging around verification
   those should each open or attach to their own implementation seam/spec.

So my judgment is:

- the seam does **not** become `active`
- it does **not** generate code
- it **does** converge as a strategic memo

In board terms, this means the downstream artifact is the recommendation itself:

- external framing: verification-as-service
- measurement posture: instrumentation debt named explicitly
- operating claim: partial relocation of the human bottleneck, not resolution

That is enough to close the debate without pretending the economics are now measured.

<!-- FINDINGS_DEBATE: converged -->

### Turn 3 — Claude (2026-04-12) — Downstream seam status report

GP-032 converged as a strategic recommendation, not an implementation seam. The downstream work it named has since spun off into six separate seams. Reporting their status as of 2026-04-12:

**Directly named in the debate:**

| Seam | GP-032 origin | Current status |
|---|---|---|
| GP-038 Tail Cycle-Time Instrumentation | Turn 1 §2 — "instrument tail CT on decisive claims" | `verify` — Slice 1 (shared iteration telemetry) and Slice 2 (offline episode/cycle-time reporter) both shipped and verified on GP-037. Decisive episode classifier live. Second-project verification pending. |
| GP-040 Throughput & Cost Instrumentation | Turn 1 §5/§8 — "post-kernel-amortization marginal cost", "runner-touched vs operator-touched" | `verify` — Slice 1 (machine telemetry) and Slice 2 (offline cost reporter) shipped. GP-037 baseline: $0.0238/iter, 134s/iter, 445K tokens. Provenance (Slice 3) and human economics (Slice 4) remain deferred — prerequisites not yet met. |
| GP-039 Gate Library Formalization | Turn 1 §6 — "the moat is the gate library / failure-family taxonomy" | `verify` — Two-layer private gate library exists (control catalog + precedent catalog). Provenance/audit tightening still pending. |
| GP-036 Findings Runner / Supervisor Convergence | Turn 1 §1/§9 — "runner-touched vs operator-touched fraction", GP-031 scope limits | `active` — Runner reimplemented ~95% standalone instead of ~70% supervisor reuse; debate to convergence on transport decoupling not yet run. |

**Indirectly downstream (product surface):**

| Seam | GP-032 origin | Current status |
|---|---|---|
| D4 Distribution Form Factor | Turn 1/2 §10 — "verification-as-service not Factory Control Room" | `converged` — Design brief exists. Workbench primary, D3 secondary, cockpit deferred. Operator needs to confirm case-method channel is live vs notional before handing to designer. |
| WB-001 Local Workbench | Turn 2 §5 — product identity locked to verification-as-service | `active` — All 4 blocking trust seams (GP-017, GP-021, GP-022, GP-011) closed. Ready for v1 implementation scoping against D4 brief. Has been unblocked and idle. |

**What remains unmeasured from GP-032's explicit punch list:**

- Runner-touched vs operator-touched fraction over sliding window — not yet measurable; GP-031 runner has been exercised on only one live finding (GP-034). Needs 3+ exercises before Slice 3 of GP-040 is meaningful.
- Fully loaded kernel-amortization cost — still untracked; operator-hour logging protocol not designed.
- Tail CT distribution across multiple projects — GP-038 reporter is live but only has GP-037 data so far. GP-045 telemetry is the second data point; run the reporter once GP-045 workspace is accessible.

**GP-032's strategic recommendations: standing assessment.**

All five from Turn 2 still hold and have not been contradicted by downstream work:
1. TOM as explanatory vocabulary only — holding
2. Drop "human bottleneck resolved" — holding; GP-031 runner still has only partial coverage
3. Cycle time as tail distribution — now instrumented, not yet meaningfully measured across projects
4. Split cost language into two layers — holding; marginal runtime cost measurable, fully loaded not yet
5. Product identity locked to verification-as-service — holding per D4
