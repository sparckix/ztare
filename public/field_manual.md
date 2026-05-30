# The Field Manual: Patterns That Survive Smart Rooms

*A short, practical catalogue of the structural failure modes that routinely survive ordinary strategic review — written for case-method instructors, diligence teams, and operators who need to spot weak arguments in real time.*

*Version 1 — extracted from adversarial verification runs on real strategic theses. Each pattern includes a one-line "Killer Question" designed to expose it. Provenance tags indicate how broadly it has been observed so far.*

> **Relationship to other catalogues in this repo.** This field manual is the operator/instructor-facing catalogue: short patterns with killer questions for use in real-time strategic review. The apparatus-internal, mining-derived classifier vocabulary (different audience, different purpose) lives in [`docs/concepts/anti_pattern_catalog.md`](../docs/concepts/anti_pattern_catalog.md) and the structural account in [`docs/concepts/epistemic_principles.md`](../docs/concepts/epistemic_principles.md). The two surfaces are intentionally non-overlapping.

---

### 1. The Promissory Note

**Provenance:** Probable — observed in `eu_union_load_bearing_pillars`, `central_station`

**The Trap:**
The argument's central proof hasn't happened yet. The logic would work — if the future event arrives in the predicted shape.

**The Mechanism:**
The speaker has a real prediction, a real mechanism, and a real story about what would confirm it. What they don't have is anything observable today that distinguishes their world from the world where they are wrong. The deferral is invisible because the audience hears the prediction as evidence of confidence rather than as a confession that the central fact has not yet occurred. It compounds with seniority: the more credible the speaker, the more the future-tense claim is filed as if it were past-tense.

**The Real Example:**
In the EU central pillars analysis, the decisive evidence — the thing that would convert a directional call into a confirmed one — was explicitly deferred to a future asymmetric crisis. A reader skimming the conclusion would carry away "this is supported"; a reader checking the supporting clause would find "this will be supported when the next crisis lands the right way." In the Central Station diligence run, a thesis claimed 85%+ statistical power for its core go/no-go test while the test's own output measured power at 0.597. The headline number was the version that was supposed to be true.

**In Practice:**
*Imagine a CFO presenting a turnaround plan:* "Our cost structure becomes competitive once the ERP rollout completes in Q3 and the supplier contracts kick in next year. At that point our unit economics will clearly demonstrate the restructuring is working." Every central data point is in the future. The board cannot disagree with the plan because the plan is unfalsifiable until the events it depends on have occurred.

**The Killer Question:**
*What observation available to us this week — not next quarter — would change your mind about this?*

---

### 2. The Coin-Toss Metric

**Provenance:** Tentative — observed in `eu_union_stability`

**The Trap:**
The argument points to evidence and says "this is what makes my theory right." But the same evidence fits the rival theory just as well. The metric doesn't discriminate; it merely sounds discriminating.

**The Mechanism:**
The audience checks whether the evidence is *consistent* with the claim, not whether it is *exclusive* to it. Consistency is easy; exclusivity is the harder bar that almost never gets enforced. When the metric is quantitative, it gains the armor of precision, which makes the audience less likely to ask whether it actually decides anything.

**The Real Example:**
In the EU stability analysis, a thesis tried to discriminate between two competing mechanisms by comparing how the union absorbed shocks across two different decades. The problem was that the episodes also differed in the *type* of shock — one symmetric and exogenous, the other asymmetric and partly endogenous. That difference alone predicted every trajectory difference the metric was supposed to attribute to the underlying mechanism. The discriminator was structurally incapable of separating the two stories.

**In Practice:**
*Imagine a head of product defending a launch:* "Adoption is up forty percent month-over-month in the markets where we ran the new onboarding flow, which proves the redesign is working." What the executive hasn't asked is whether those markets also had a seasonal uplift, a local sales push, or a competitor outage. The forty percent is evidence of *something* — but not necessarily of the thing being claimed.

**The Killer Question:**
*What would the world have to look like for this same number to appear even if your hypothesis were wrong?*

---

### 3. The Elephant-in-the-Room Pass

**Provenance:** Probable — observed in `eu_union_load_bearing_pillars`, `eu_union_stability`

**The Trap:**
A fatal risk is named explicitly, almost gracefully — and then the argument continues as if naming it had retired it. The audience interprets the acknowledgment as rigor.

**The Mechanism:**
The audience's intuition for weak arguments is calibrated against people who duck — so when someone walks straight at the threat, the audience relaxes. The move is to relabel the risk ("acknowledged risk," "known limitation") and proceed as if the relabeling altered the underlying probability. A risk that has been named is psychologically discounted in a way the math does not justify.

**The Real Example:**
In the EU central pillars analysis, the central causal mechanism — whether the union has any non-discretionary fiscal capacity — was quarantined as a separate question rather than treated as central for the conclusion. The acknowledgment was clean. But the conclusion still rested on that quarantined mechanism. By naming the dependency and placing it outside scope, the analysis behaved as if the question had been answered when it had only been moved.

**In Practice:**
*Imagine an M&A team presenting an acquisition memo:* "We want to flag upfront that the engineering integration carries real risk — different stacks, key-person dependencies on three senior architects. We've named it, put it on the watch list, and we're confident the rest of the deal logic is sound enough to absorb that uncertainty." Then the synergy targets and integration timeline quietly assume the engineering integration goes well.

**The Killer Question:**
*If the risk you just named landed in the worst plausible form, which numbers in the rest of this deck stop being true?*

---

### 4. The Ghost Metric

**Provenance:** Tentative — observed in `eu_union_load_bearing_pillars`

**The Trap:**
The argument turns on a variable that no one in the room can actually observe. The speaker treats it as measurable; the audience assumes it has been measured.

**The Mechanism:**
Ghost metrics survive because the language for them is identical to the language for real metrics. "Political will," "strategic commitment," "organizational alignment" can sit in the same sentence as "revenue" or "headcount," and the grammar gives no hint that one has no proxy. The speaker often genuinely believes they can read the variable — and may even be right — but they cannot transmit that reading to anyone else, so it cannot be checked.

**The Real Example:**
In the EU central pillars analysis, one key discriminator between "durable equilibrium" and "fragile but intact" was whether the central fiscal capacity was *material* — and the threshold for materiality was not independently grounded. The thesis correctly flagged this as its weakest joint. But while the threshold was framed functionally, no observable proxy existed by which a third party could decide, on a given day, whether the capacity had crossed it.

**In Practice:**
*Imagine a CMO defending a brand investment:* "The campaign is worth the spend because we're rebuilding category authority — and category authority eventually shows up as pricing power, talent attraction, and partnership inbound. The lift won't be in next quarter's numbers, but it's real." Everyone nods because they know what category authority feels like. No one can say what would have to happen for the CMO to admit they were wrong.

**The Killer Question:**
*Name the specific number, on which dashboard, that you would check next month to know whether this is working.*

---

### 5. Defining Yourself Into Victory

**Provenance:** Tentative — observed in `eu_union_load_bearing_pillars`

**The Trap:**
The conclusion is true because the boundaries of the question were drawn to make it true. Rephrase the question slightly and the conclusion evaporates.

**The Mechanism:**
The speaker usually drew the boundaries in good faith — scope decisions made early, in a different conversation, for reasons that felt principled at the time. By the time the conclusion is presented, the scope is invisible. The audience only sees the question and the answer, and the answer follows from the question. What they don't see is the accumulated "let's not include X," "let's treat Y as fixed" decisions that hollowed out the question until the answer was the only thing that could fit.

**The Real Example:**
In the EU central pillars analysis, an earlier framing risked treating the union's continuation as evidence of its durability by defining "durable" in terms its current institutional shape already satisfied. The thesis later corrected this by forcing the central claim onto a harder, narrower definition. But the original drift was instructive: a generously drawn boundary made the union's persistence look like proof, when it was only proof of persistence.

**In Practice:**
*Imagine a strategy lead defending a market-entry plan:* "Within our addressable segment — mid-market North American firms in regulated industries who already use a tool in our category — we are projecting a three-year path to category leadership." The qualifiers have shrunk the market until the leadership claim is almost arithmetic, and then the claim is presented as the strategic finding rather than as a restatement of the qualifiers.

**The Killer Question:**
*If we widened the question by one reasonable inch in any direction, does your conclusion still hold?*

---

### 6. The Wrong Yardstick

**Provenance:** Probable — observed in `central_station`, `eu_union_load_bearing_pillars`

**The Trap:**
The argument measures something — carefully, rigorously, with real data — but not the thing the question is actually about.

**The Mechanism:**
Wrong-yardstick failures look like the most rigorous parts of an argument, which is what makes them dangerous. The substitution happens upstream — usually because the right yardstick is hard to measure and the available one is close enough to present under the same name. By the time the result is being discussed, the substitution has been forgotten.

**The Real Example:**
In the Central Station diligence runs, the thesis required a statistical power calculation to determine whether a planned go/no-go test could detect the relevant effect size. Instead, the analysis ran a Monte Carlo simulation — real, clean, numerically respectable, but the wrong question. The test that would actually decide go/no-go remained ungrounded. In the EU pillars analysis, debates about stability sometimes turned on treaty status when the operational question was about market pricing of redenomination risk — a different yardstick measuring a different thing.

**In Practice:**
*Imagine a head of engineering defending a reliability program:* "We've cut mean-time-to-recovery from forty minutes to nine, which puts us in the top quartile of our benchmark." The question the board was actually asking was whether customers were having a worse experience — which is not measured by MTTR but by how often incidents occur and how many users are touched.

**The Killer Question:**
*Is the thing you measured the thing the decision actually depends on?*

---

### 7. The Misfile

**Provenance:** Tentative — observed in `eu_union_load_bearing_pillars`

**The Trap:**
An instrument, entity, or fact is placed in the wrong category early in the argument, and every downstream inference inherits the misclassification without anyone noticing.

**The Mechanism:**
Misfiling is invisible because the misfiled item gets handled correctly *for its category* — the reasoning is internally consistent. What's wrong is that the item belonged elsewhere, and every operation performed on it was the right operation for the wrong type of thing. The audience cannot catch the error by checking the work; they can only catch it by going back to the original classification, which no one does because that step happened at the start.

**The Real Example:**
In the EU central pillars analysis, certain crisis-era instruments were sometimes treated as temporary stabilization tools when they were operationally functioning as quasi-permanent fiscal infrastructure — and sometimes the reverse. Either misfile propagated through the analysis: temporary classification made the argument over-discount their continuing role; permanent classification made it over-credit them as evidence of structural change. The reasoning in each branch was consistent with itself; the error lived upstream.

**In Practice:**
*Imagine a finance team building a forecast:* "We've classified the new revenue stream as recurring — it's a subscription, contracts auto-renew, gross retention is in line with our other recurring lines — so we're modeling it at the recurring-revenue multiple." What the team hasn't checked is whether customers think of it as a one-time procurement that happens to renew. The misfile won't show up in the model; it will show up in the renewal cycle.

**The Killer Question:**
*If this thing belonged in a different category than the one you put it in, what specifically would tell us — and have we checked?*

---

### 8. The False Either/Or

**Provenance:** Tentative — observed in `eu_union_load_bearing_pillars`

**The Trap:**
A thing is both X and Y at once, but the analysis only has slots for one classification. It picks one and reasons as if the other half didn't exist.

**The Mechanism:**
The analyst is not choosing between X and Y because they think the thing is only one — they are choosing because the framework, model, or slide template only has space for one answer. The reasoning that follows is internally consistent with whichever half got selected, and the other half is silently absent from every subsequent comparison.

**The Real Example:**
In the EU pillars analysis, several crisis-era instruments were genuinely hybrid: legally temporary but operationally entrenched, formally limited but informally expandable under stress. Forcing each into either the "permanent" or "temporary" bucket destroyed the most important fact about it — that the bucket itself was contested, and the contest was the central part of the question.

**In Practice:**
*Imagine a corp dev team evaluating a partnership:* "We need to decide whether to treat this as a customer relationship or a channel relationship — those go in different parts of the org. Our recommendation is the channel bucket because the volume mix leans that way." What it has erased is that the counterparty is doing both things at once and will object whenever the channel bucket constrains the customer behavior. The objection will be read as a partnership problem rather than as evidence that the bucket was always the problem.

**The Killer Question:**
*Does this thing have to be only one of the things you're forcing it to be?*

---

### 9. The Untestable Forecast

**Provenance:** Tentative — observed in `eu_union_load_bearing_pillars`

**The Trap:**
The argument makes a confident prediction, but there is no observation between now and the moment of commitment that would falsify it.

**The Mechanism:**
The close cousin of the Promissory Note, but worse: the Promissory Note at least promises that the verifying event will arrive. The Untestable Forecast does not even promise that. It survives because the audience confuses *specificity* with *testability* — a forecast that names a date, a magnitude, and a mechanism sounds checkable when none of those components has a proxy anyone is scheduled to read before the decision becomes irreversible.

**The Real Example:**
The EU pillars analysis's projection through 2035 was disciplined in its tilt and explicit about its uncertainty. But the structural question — would the union develop the kind of central capacity that would convert "fragile but intact" into "durable equilibrium" — was a forecast whose only natural test was the next major asymmetric crisis. Between today and that crisis, no proxy reading exists that would tell a third party which side of the forecast was being borne out.

**In Practice:**
*Imagine an investor pitching to their LPs:* "We believe the consolidation in this fragmented services category will accelerate over the next five years, driven by capital availability and the maturation of operational playbooks, and our portfolio is positioned to capture the upside." There is nothing in it that the LPs can test for the next five years. By the time the answer arrives, the capital has been committed and the test has become a postmortem.

**The Killer Question:**
*Between today and the day we have to commit, what is the earliest reading we could take that would tell us we were wrong?*

---

## How to read this manual

These patterns were extracted from an adversarial verification process applied to real strategic arguments — arguments about whether a political union is structurally durable, whether a startup's go/no-go test was actually grounded, whether a particular institutional instrument means what its proponents say it means. Each pattern survived the ordinary review the argument got from its authors and from their first round of skeptical readers, and only became visible when the argument was forced through a process designed to ask narrower questions than humans usually think to ask.

The patterns are not exhaustive, and several entries are tagged "Tentative" because they have been observed in only a single project — which means they may be specific to that domain rather than general. "Probable" marks patterns observed across two or more projects. "Confirmed" would mark patterns across three or more projects spanning at least two distinct domains. The discipline is the same one the underlying process uses: a pattern is provisional until cross-domain evidence promotes it.

## Field discipline

Real arguments almost never contain only one of these traps. They compound — a Promissory Note rests on a Ghost Metric, an Elephant-in-the-Room Pass disarms the audience just before a Wrong Yardstick is introduced, a False Either/Or hides inside a definition that already had Victory baked into it. The point is not to memorize the names; the names are mnemonic scaffolding. The point is the killer questions. Memorize the questions. They are the operational output of this document, and a single one, asked at the right moment, can do more useful work in a meeting than all of the taxonomy above. Patterns marked "Tentative" should be treated as live hypotheses rather than settled findings — useful enough to ask the killer question, not yet broad enough to assert as a general law.
