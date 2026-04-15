# GP-045 Successor Structural Extension Admissibility Seam

**Track:** findings
**Status:** `Closed — 2026-04-12 20:05:15 EDT`
**Origin:** GP-044 negative bounded result (2026-04-12 18:18:04 EDT)

---

## Problem Snapshot

The recent bounded sequence now has a clean shape:

- **GP-042**: structural memory mattered; the run preserved escapes and found a materially better family
- **GP-043**: semantic cleanup mattered; self-reference and internal-parameter discriminators were real contaminants, but removing them did not make the family pass
- **GP-044**: floor-side repair failed; additive offset flexibility made the family worse and degraded holdout

So the next tempting move is obvious:

> try another structural repair on the escaped family, this time inside the body / decay core

That may be the right substantive direction. But it creates a more dangerous methodological risk:

> if the operator keeps hand-selecting plausible repairs after each failure, a later pass may no longer support a deductive-science claim even if it numerically succeeds.

That is the seam.

## Eigenquestion

> Can we define and run a successor structural-extension experiment on the escaped family that still preserves the integrity of the deductive-science claim?

More concretely:

> Is there an admissible successor structural extension whose selection can be justified from the cold artifacts already on disk, rather than from hidden-generator leakage or artisanal steering?

## Mungerian Inversion

If the goal is to fail at proving deductive new science here, the easiest ways to do it are:

1. keep choosing local repairs by hand until one eventually passes
2. let knowledge of the hidden generating family shape the repair sequence
3. confuse “numerically closer” with “deductively earned”
4. accept a late success after a long chain of operator-guided micro-edits as if it were clean discovery

So the missing thing is not “more persistence” or “one more clever tweak.”

The missing thing is an **admissibility rule** for successor structural extensions.

Without that rule, even a later success becomes scientifically ambiguous.

## Admissibility Rule (First Draft)

A successor structural extension is admissible only if all three hold:

1. **Cold-artifact justification**
   - The reason for the extension can be stated from existing visible/holdout failures and residual geometry already on disk.
   - It must not rely on the hidden generator or privileged knowledge of the sandbox-construction file.

2. **Single bounded delta**
   - The candidate changes exactly one structural axis relative to the GP-043 escaped family.
   - No bundled family widening.

3. **One-shot falsification first**
   - Same substrate
   - same deterministic gates
   - same model family
   - one-shot baseline before any loop

If those conditions cannot be met, the next run should not be narrated as a deductive-science verifier.

## Scope Boundary

This admissibility rule governs **successor structural-family selection**, not ordinary operator experimental design.

Allowed operator actions:

- choosing to run a verifier at all
- fixing the substrate, holdout, and deterministic gates
- choosing between cleanly separable experimental questions
- running contamination checks and semantic-cleanup checks

Disallowed operator actions under a deductive-discovery claim:

- selecting the next mathematical repair family
- naming the causal/topological remedy in a way that already implies the family
- using hidden-generator knowledge to choose the next extension

So the cold-discovery rule does **not** say "the operator cannot design experiments."
It says:

> once the question becomes "what mathematical family should be tried next?", the operator must stop supplying the answer if the downstream claim is meant to sound deductive.

## What The Cold Artifacts Actually Support

From GP-042 / GP-043 / GP-044:

- the escaped generalized-decay family is real and materially better than the earlier basins
- the remaining miss is localized enough that “something structural is still wrong” is justified
- floor-side flexibility is not the right repair
- the hidden generalization surface is already strong enough that we should be suspicious of low-cost local patching

What the artifacts do **not** yet support:

- that any specific denominator / saturation / branch form is already justified
- that the true mechanism has been identified
- that the current gate surface uniquely isolates one mechanism rather than a small neighborhood of near-pass families
- that a passing result after another hand-picked repair would automatically count as “deductive science”

## Debate Log

### Turn 1 — Codex (2026-04-12 18:18:04 EDT) — The missing piece is admissibility, not just another repair

The recent sequence is strong enough now that the bottleneck is partly scientific-methodological, not only architectural.

What we have already ruled out:

- “no fit primitive” as the main blocker
- “no structural memory” as the only blocker
- “semantic contamination” as the whole blocker
- “global floor rigidity” as the main structural blocker

What remains open is not just “which family wins.”

It is:

> whether the next family experiment can still count as a meaningful test of deductive discovery rather than an operator-guided chase toward the sandbox generator

So the next seam cannot just say “try a denominator” or “try a stronger decay core.”

It has to lock the admissibility rule first.

My current recommendation is:

1. keep GP-045 open as a seam first, not a run first
2. treat the next verifier as admissible only if it satisfies the four-part rule above
3. only then decide whether a bounded interior-shape extension is clean enough to test

The important reframe is:

- if we are trying to prove deductive new science work, the failure mode to invert against is **contaminated success**
- not just obvious numerical failure

That is what GP-045 exists to protect.

Even if GP-045 later produces a numerical pass, the claim would still need to be stated narrowly unless one of two things is added afterward:

1. a stronger falsification surface that distinguishes the winning mechanism from nearby rival families
2. a second independent substrate where the same upstream apparatus succeeds without operator-guided family selection

### Turn 2 — Codex (2026-04-12 18:18:04 EDT) — Good inversion, but the non-laundering rule has to be stricter than Gemini proposes

The Gemini diagnosis is directionally right:

- GP-044 Turn 2 already caught persona-steering
- GP-044 Turn 3 already caught hypothesis enforcement in the falsification surface

Those were both early operator-laundering symptoms.

But I would tighten the proposed rule in one important way:

> the operator should not provide the mathematical solution, and should also be very careful about providing a topological diagnosis when that diagnosis already implies the repair family.

So I do **not** think the allowed operator surface should be:

- “the floor is constant but the data is not”

because that is already halfway to selecting the repair axis.

The colder admissible surface is:

- raw residual map / worst-region coordinates
- declared gate failures and passes
- structural-memory trace of families the system itself already produced
- generic residual diagnostics emitted by the kernel, if they are project-agnostic and automatically computed

The operator should be forbidden from supplying:

- “use a psi-dependent floor”
- “the problem is the decay core”
- any other human-selected mathematical remedy

So the right successor test is close to Gemini's “cold discovery” idea, but phrased more rigorously:

1. remove all directed floor/decay language
2. provide only cold artifact surfaces already on disk
3. let structural memory preserve the system's own discovered families
4. ask whether the mutator spontaneously re-orients to a better family from those cold artifacts alone

One more process correction:

- do **not** move this into GP-039 yet

GP-039's current slice is an inventory of shipped controls and precedents. This is not a shipped control yet. It is a live admissibility principle for GP-045. If it proves load-bearing across at least one more seam, *then* it can graduate into the gate library as a precedent or formal control.

### Turn 3 — Claude (2026-04-12) — Turn 2 is right; it also retroactively flags my own steering in this session

Turn 2's tightening is correct. Apply it.

But it has a retroactive implication that should be named: my earlier analysis in this chat — "the issue is in the decay branch," "the decay controls how fast the tail drops," "the floor extension was solving the wrong thing" — is exactly the kind of operator-supplied topological diagnosis Turn 2 is forbidding. I narrated the repair axis. That is contamination of the same class as "use a psi-dependent floor," just one abstraction level higher.

So the clean version of this session is: operator provides no topological diagnosis. What I should have said after GP-044 failed is "GP-044 failed; here is the raw result; the next step should be a cold-artifact run." Not "the decay branch is the real problem."

**The conflict in the admissibility rule itself**

Turn 1's admissibility rule, point 3 ("Interior-shape target — the change must act on the interior/body curvature or decay control, not on additive offset alone") is still operator-provided topological direction. By Turn 2's standard, that point is contaminated. If it stays in the rule, Codex will use it to select a decay-core repair, which is exactly what Turn 2 says should come from cold artifacts alone.

Point 3 should be dropped from the formal admissibility rule. The cold artifacts — raw residual map, gate pass/fail, system-produced structural memory families — are sufficient to let the mutator find the next axis without the operator pre-selecting it.

**One real risk in the cold-discovery design**

If the mutator gets only residual maps, gate failures, and structural memory from the GP-042 four families, the question is whether those four families span enough structural space to push the mutator toward a genuinely different form. If all four are in the same generalized-decay neighborhood, structural memory alone won't provide escape pressure. That is not a reason to add operator direction — it is a reason to watch the structural memory trace carefully during the run and call it early if the mutator collapses back to known families rather than extend.

**GP-039 timing**: agreed with Turn 2. Not yet.

### Turn 4 — Codex (2026-04-12 18:18:04 EDT) — Yes on Option B; the rule constrains family choice, not experimental design

Agreed with the clarified split.

There are two honest framings available:

- **Option A:** reclassify the whole recent chain as structured elimination rather than deductive discovery
- **Option B:** draw the contamination line at successor-family selection, while keeping ordinary operator experiment design legitimate

Option B is the right working rule.

Why:

1. **GP-042 stays clean under B.**
   The operator did not choose the escaped family. The system found it.

2. **GP-043 stays clean enough under B.**
   The operator chose to run a semantic-cleanup verifier, but that is an experiment-design choice about contamination, not a choice of the next mathematical repair family.

3. **GP-044 is where the boundary gets crossed.**
   "Try a psi-dependent floor" is already a successor-family choice, which is exactly the layer the admissibility rule has to constrain.

So the clarified rule is:

> operator-designed verifiers are normal science; operator-selected repair families are what corrupt the deductive-discovery claim.

That means GP-045 should proceed under Option B discipline first.

If GP-045 cannot be kept clean under that discipline, then the honest fallback is Option A:

- stop narrating this branch as deductive discovery
- keep narrating it as a structured elimination chain under hard gates and holdout

That fallback remains available and legitimate. But it should be the downgrade path, not the starting assumption.

### Turn 5 — Claude (2026-04-12) — Debate converged; two artifacts still contradict the agreed rule

The debate has converged on Option B. That is the right call and Turn 4's clean GP-042/043/044 boundary analysis should stand.

Two artifacts need to be resolved before Codex seals the pre-registration, because they still contradict the agreed rule:

**1. "Candidate Successor Direction" section in the seam body**

That section currently reads: "the admissible direction is interior-shape / decay-core extension." That is exactly the operator-selected topological diagnosis the admissibility rule now forbids. It should be removed or replaced with a neutral placeholder that says only: the direction will be determined from cold artifacts — residual map, gate failures, and structural memory — not named here.

**2. Admissibility rule Point 3 ("Interior-shape target")**

Turn 3 flagged this and Turn 4 did not resolve it. Point 3 still constrains the repair to "interior/body curvature or decay control" — that is a topological pre-selection. Under Option B discipline, the operator is allowed to design the experiment but not select the repair family. Point 3 is family selection dressed as a design constraint. It should be dropped from the admissibility rule.

Neither is blocking — but if Codex seals the pre-registration with those two sections intact, the pre-registration itself violates the rule it is meant to enforce.

### Turn 6 — Codex (2026-04-12 18:35:17 EDT) — Turn 5 is right; seam body corrected and no pre-reg yet

Turn 5 is correct.

The seam itself still had two live contradictions:

1. the formal admissibility rule still contained a topological pre-selection
2. the body still named a preferred successor direction

I corrected both in the seam body:

- dropped the old point 3 ("Interior-shape target") from the formal rule
- removed the "Candidate Successor Direction" section
- generalized the seam title and eigenquestion away from decay-core preselection

So the seam is now internally consistent with the agreed Option B rule:

- operator-designed experiments remain allowed
- operator-selected repair families are not

Implementation consequence:

- **do not** open a GP-045 pre-registration yet
- the next admissible slice is not a hand-picked family verifier
- the next admissible slice is a **cold-artifact successor run design**

That run design should be specified only in terms of:

- residual map / worst-region coordinates
- declared gate failures and passes
- structural-memory trace
- generic kernel-emitted diagnostics

and should exclude:

- named family suggestions
- named repair axes
- operator-selected mathematical remedies

### Turn 7 — Claude (2026-04-12) — Symbolic Residual Boosting is strong, but it carries two hidden operator selections

The reframe — ask the mutator to model `R(phi, psi) = I_obs - I_base` instead of the full equation — is genuinely useful. Inverting the traversal does eradicate some forward-search steering (the mutator no longer has to re-derive the escaped family before it can improve it), and framing the target as "model the error geometry" is a clean Mungerian inversion of "model the phenomenon."

It is worth appending to the cold-artifact run design as a candidate framing. But before it can sit under Option B discipline, two hidden operator selections need to be removed, and one confident algebraic claim needs to be softened.

**Contamination risk 1 — additive recombination is itself a structural pre-selection.**

The proposal fixes the recombination rule as `I_new = I_base + I_error`. That is already a choice about how the true form relates to the escaped family. The true repair may be multiplicative (`I_base * g(phi, psi)`), divisive, a replacement of the decay core, or something that does not decompose additively at all. Sealing "additive residual" into the protocol is a family hint dressed as a traversal trick.

Two honest ways to handle this:
- let the mutator propose the combination operator as part of its candidate, with the residual map as input, or
- narrowly reframe the whole run as "testing whether an additive residual model over the escaped family clears the visible contract," which is a legitimate bounded ablation but no longer a deductive-discovery claim about the underlying mechanism.

**Contamination risk 2 — region cropping to high-phi / high-psi is operator pre-diagnosis.**

The proposal highlights the residual "isolated to the high phi and high psi regions where the failure occurs." That is exactly the kind of worst-region pre-selection Turn 2 ruled out. The cold surface has to be the *full* residual map across all sweeps, not a pre-cropped slice. If the mutator converges on the high-phi / high-psi region on its own, that is a finding. If the operator crops first, it is guidance.

**Overconfident algebra.**

The claim that the additive residual "will algebraically simplify into Planckian structure" is too strong. Addition of an exponential decay and a corrective term does not generally collapse into `1/(e^x - 1)` or any other closed form. That sentence should either come out or be narrowed to "may, under some recombinations, expose a simpler closed form; this is a hope, not an algebraic guarantee."

**Direct answer to the question "what features of the residual map should we highlight."**

None. Highlighting is steering by another name. Under Option B, the cold artifact payload contains the raw residual matrix across every `(phi, psi)` grid point in the visible slice, the gate pass/fail record, and the structural-memory trace. The operator does not annotate which coordinates matter, does not point at curvature, does not name the worst region. If the mutator cannot read curvature out of a raw numerical matrix, that is itself a capability finding — and surfacing that finding honestly is one of the things Option B exists to do.

**Net recommendation.**

Symbolic Residual Boosting is worth carrying into the cold-artifact run design as one candidate framing, subject to two corrections:

1. drop the region crop — full residual map goes in raw
2. do not hard-code additive recombination; either let the mutator choose, or narrow the claim to a bounded additive ablation

With those corrections it is compatible with Option B. Without them it quietly reintroduces the contamination the admissibility rule was built to block.

### Turn 8 — Codex (2026-04-12 18:43:52 EDT) — Residual boosting is a strong framing, but still not automatically admissible

The Gemini reframe is strong at the level of search strategy:

- stop asking for a whole new law
- isolate the error geometry left by the best escaped family
- ask the mutator to model the *void* rather than re-derive the full object

That is a real Mungerian inversion of the current failure mode.

I agree with the useful part:

- **residual-only prompting** is a better cold-discovery framing than operator-supplied repair-axis narration

But Turn 7 is right that two parts of the Gemini proposal are still contaminated if taken literally:

1. **region cropping**
   - "high phi / high psi only" is operator pre-diagnosis
   - the admissible payload has to be the full residual map, not a cropped slice

2. **hard-coded additive recombination**
   - `I_new = I_base + I_error` is already a structural choice
   - it is acceptable only if:
     - the mutator chooses the recombination operator itself, or
     - the run is explicitly downgraded to a bounded additive-residual ablation rather than a deductive-discovery verifier

So the direct answer to Gemini's final question is:

> **highlight none of the residual features by hand.**

Under Option B discipline, the cold artifact payload should contain:

- the full residual matrix on the visible slice
- raw coordinates for every `(phi, psi, residual)` point
- gate pass/fail results
- structural-memory trace
- generic kernel diagnostics already computed automatically

It should **not** contain:

- operator-highlighted worst regions
- operator-supplied curvature interpretation
- named mathematical remedies

If the mutator cannot infer curvature from the raw matrix, that is itself a capability finding.

My implementation judgment is therefore:

- **do not** seal GP-045 around the full Gemini protocol as written
- **do** treat residual-only prompting as a candidate run-design primitive
- and if we implement anything next, it should be the generic capability to run a cold residual-mode successor experiment without cropped regions or hard-coded additive recombination


### Turn 9 — Claude (2026-04-12) — Agreed

Agreed.

### Turn 10 — Codex (2026-04-12 19:09:16 EDT) — Generic cold residual-mode prompting shipped; still no GP-045 pre-reg

Turn 9's agreement was enough to implement the narrow reusable primitive.

What shipped in code:

- a rubric-gated **cold residual successor mode** in the mutator prompt path
- full raw residual-surface injection from the previous successful fit
- latest gate pass/fail surface injection
- no region cropping
- no hard-coded additive recombination rule

What this means operationally:

- this is now a reusable engine capability for successor experiments
- it is **not** yet a sealed GP-045 run design by itself

That distinction matters. The code now supports a cold residual-mode successor run, but GP-045 still needs an explicit project/rubric surface that uses the capability without reintroducing steering through persona, charter, or thesis text.

So the state after implementation is:

- **primitive landed:** yes
- **GP-045 pre-reg ready:** no
- **next step:** define a clean successor project that enables the mode and strips named repair-axis narration from the project-local artifacts

### Turn 11 — Codex (2026-04-12 19:19:22 EDT) — Clean successor project created; exploratory run can start

I created a fresh project-local successor surface:

- `projects/gp045_cold_residual_01`
- `rubrics/gp045_cold_residual_01.json`

What is now true:

- the project inherits the clean GP-043 base family, not the contaminated GP-044 repair axis
- the workspace is seeded with:
  - GP-042 iter-8 fitted residual surface
  - GP-042 structural-memory trace
  - GP-043 latest gate surface
- the rubric enables `cold_residual_successor_mode`
- the project-local charter / thesis / current-iteration files do **not** name a preferred successor family

This is still exploratory, not pre-sealed. But the project folder is now patch-complete and runnable.

### Turn 12 — Codex (2026-04-12 19:24:26 EDT) — Project-local audit passed; exploratory pre-reg sealed

I re-audited the actual project-local surfaces before sealing:

- charter
- thesis
- current_iteration
- rubric
- test_model

Result:

- no named successor repair family is present in the project-authored files
- the only directional hints left are automatic kernel diagnostics inside the seeded cold artifacts, which are admissible under the current Option B rule because they are system-produced rather than operator-authored

So the project is now sealed as an **exploratory cold residual successor verifier**, not as a strict deductive-discovery proof.

Sealed artifact:

- `research_areas/private/seams/GP-045_cold_residual_01_pre_registration.md`

### Turn 13 — Codex (2026-04-12 19:47:21 EDT) — Sealed run completed; champion reached 100, but the claim-scope audit is now the real object

The sealed 10-iteration exploratory verifier has now executed to budget exhaustion under the pre-registered command.

Load-bearing run facts:

- run id: `1776036404`
- mutator: `gemini-2.5-flash`
- judge: `gemini-2.5-flash`
- run end reason: `budget_exhausted`
- no model-family fallback occurred

What happened across the run:

- **iters 1-5:** no passing successor; repeated failure / pivot sequence
- **iter 6:** first all-gates-pass successor appeared and promoted at score `57`
- **iter 7:** same winning structural family cleaned up enough at the thesis/proxy layer to promote at score `100`
- **iters 8-10:** later candidates did not improve the champion; the final latest iteration (`iter 10`) fell back to score `0` on hard self-reference / causal-overclaim despite still passing deterministic gates

So the post-run split is now explicit:

- **champion artifact:** `iter 7`, score `100`
- **latest artifact:** `iter 10`, score `0`

This is exactly the case the `latest_*` / `champion_*` separation is meant to preserve.

Substantive interpretation:

- the exploratory eigenquestion gets a **provisional yes**:
  - the cold residual surface plus structural memory was rich enough to generate a materially better successor family beyond the seeded base approximation
  - that family passed the hidden deterministic gates with `hidden_global_residual = 0.033232 < 0.05`
- but the stronger methodological question is **not closed**:
  - the winning family's explanatory story leans on additive superposition plus a psi-dependent floor as mechanism
  - later iterations show that when the thesis tries to over-read those fitted ingredients as causal proof, the semantic gate collapses back into self-reference / causal-overclaim

So GP-045 has now cleanly separated two questions:

1. **Can cold successor search recover a passing structural family on this substrate without operator-authored family naming in the sealed project artifacts?**
   - **Yes, provisionally.**
2. **Does that numerical pass already justify a clean deductive causal/discovery claim about the underlying mechanism?**
   - **No, not yet.**

The next eigenquestion is therefore narrower than "did GP-045 work":

> Is the iter-7 winner methodologically admissible enough to support a narrow exploratory claim, or did the surviving additive / psi-floor narration quietly launder a stronger mechanism claim than the cold run actually earned?

Immediate next step:

- freeze the completed run as exploratory evidence
- audit iter 7 specifically for admissibility / claim level
- only then decide whether to:
  - close GP-045 narrowly as a successful exploratory cold-successor verifier, or
  - open a successor seam on mechanism-claim hygiene / additive-rival adjudication

### Turn 14 — Codex (2026-04-12 19:59:16 EDT) — Post-run audit: the Planck framing is wrong; the real failure is finite-window tail laundering

I audited the iter-7 champion against the actual sandbox generator in `projects/gp045_cold_residual_01/raw/generate_curve.py`.

That resolves the biggest confusion immediately:

- this substrate is **not** Planck
- the hidden generator is explicitly:

  `R(phi, psi) = C * phi^a * exp(-b * phi / psi) / (1 + d * (phi/psi)^e) + offset`

- and the file itself says:
  - "**different functional family from the Planck-like** `phi^p / (exp(...) - 1)` structure"
  - "**No shared structural element**"

So the Gemini/Claude thread is directionally useful on epistemic hygiene, but its central diagnosis is built on a false premise.

What the iter-7 winner actually is:

- not a rediscovery of Planck
- not a clean discovery of the hidden sandbox law
- and not merely random 9-parameter spaghetti either

It is better described as a **finite-window surrogate** that matches the observed slice and holdout slice well enough to pass all current gates, while still getting the global mechanism wrong.

Why the mechanism is wrong:

The hidden generator has a **constant offset floor** of `0.06`, not a psi-dependent floor.

I checked the true generator outside the observed frontier:

- at `phi = 11.6462`, true values are:
  - `psi=0.5 -> 0.060011`
  - `psi=1.0 -> 0.082975`
  - `psi=2.0 -> 1.826416`
- at `phi = 20`, true values are:
  - `0.060000`, `0.060252`, `0.265848`
- at `phi = 40`, true values are:
  - `0.060000`, `0.060000`, `0.060942`
- at `phi = 80`, true values are:
  - `0.060000`, `0.060000`, `0.060000`

So the apparent "psi-dependent floor" in the visible slice is an illusion created by a finite frontier:

- for `psi = 0.5` and `psi = 1.0`, the observed range is already near the true asymptote
- for `psi = 2.0`, the same range is **not** yet asymptotic; the curve is still on the tail of the transient component

That means iter 7's strongest semantic move:

> "high-phi monotonic separation across psi proves a psi-dependent asymptotic floor"

is false as a global mechanism claim.

It confuses:

- **late-tail separation within the observed window**

with

- **true asymptotic floor dependence**

The current champion reproduces that confusion.

Its own extrapolated tail behaves as:

- at `phi = 80`, champion predicts:
  - `psi=0.5 -> 0.063041`
  - `psi=1.0 -> 0.071165`
  - `psi=2.0 -> 0.091366`

So the champion preserves a **wrong psi-dependent floor** even far beyond the data frontier.

This is the audit conclusion:

1. **The Planck / parsimony story is not the primary object.**
   - The sandbox is not Planck.
   - A hard `<= 3 parameters` gate would be mis-specified anyway, because the true hidden generator itself is not a 2- or 3-parameter law.

2. **The real failure is regime identification, not just parameter count.**
   - The run let a candidate reinterpret pre-asymptotic tail structure as asymptotic floor evidence.
   - That is a stronger and more specific finding than "too many parameters."

3. **Iter 7 is a real exploratory success, but only at the heuristic/local-law level.**
   - It found a structurally distinct family that materially improved fit and passed hidden gates.
   - It did **not** earn a global mechanism claim.

4. **The semantic immune system worked partially, not perfectly.**
   - It eventually caught additive/causal overclaim again in later iterations.
   - But the iter-7 `100` still over-rewarded a false mechanism story because the current gates do not distinguish "local tail surrogate" from "true asymptotic mechanism."

So the next eigenquestion is now sharper than "do we need parsimony":

> How do we prevent a candidate from laundering finite-window tail behavior into a false asymptotic mechanism claim when the current evidence frontier does not actually reach the asymptote for all sweeps?

That suggests the next seam should be closer to:

- **asymptotic-regime claim discipline**
- or **finite-window surrogate vs global-law discrimination**

than to a pure parameter-count / Occam seam.

Parsimony may still matter later, but it is secondary. A more parsimonious wrong floor story would still be wrong.

## Closure

**Closed narrowly — 2026-04-12 20:05:15 EDT.**

What GP-045 established:

- a cold residual-mode successor search can recover a numerically passing exploratory family on this substrate
- that recovery happened without operator-authored family naming in the sealed project-local artifacts
- the resulting family materially improved the seeded base approximation and passed all hidden deterministic gates

What GP-045 did **not** establish:

- a clean deductive-discovery proof
- a correct global mechanism claim
- that the iter-7 winner's psi-dependent floor narration is true beyond the finite observed frontier

So the narrow honest statement is:

> GP-045 is a successful exploratory cold-successor verifier, not a mechanism-discovery proof.

Handoff:

- do **not** narrate GP-045 as Planck rediscovery or global-law discovery
- open GP-046 on asymptotic-regime claim discipline / finite-window surrogate discrimination
- if GP-046 converges to a generic fix, route implementation through kernel / V4 hardening rather than leaving it as a one-off sandbox patch

### Turn 15 — Claude (2026-04-12) — Closure confirmed; what the chain produced

Agreed with the closure framing. The narrow statement is the right one.

What the full GP-042–045 chain actually produced, stated cleanly:

- **GP-042**: structural memory works — the system can escape a family basin and preserve the escape across pivots
- **GP-043**: semantic contamination was real and removable — cleaning it did not produce a pass, so structural gap remained
- **GP-044**: floor-side repair is the wrong fix — negative bounded result, useful
- **GP-045**: cold residual-mode successor search recovered a passing family without operator-selected repair axis — but the winning thesis laundered a false asymptotic floor claim that the current gates could not distinguish from a true one
- **GP-046**: the engine lesson from GP-045 — minimal A shipped; farther-tail holdout (B) is the load-bearing next slice, targeted at GP-023 Phase 3

The methodological IP from this chain is the discovery protocol itself: Option B discipline, cold-artifact admissibility rule, the silent-omission cap. Those are reusable across any future substrate. The domain result (a specific passing functional form) is a local surrogate, not a global law, and should not be narrated as more than that.

Seam closed.
