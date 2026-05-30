# GP-133 — Multidisciplinary Discovery Panel: Are We Close?

> **Seam metadata** · `seam_id:` GP-133 · `track:` mission · `status:` Open - adversarial debate seam, not a spec. · `last_updated:` 2026-05-08


**Status:** Open — adversarial debate seam, not a spec.
**Opened:** 2026-04-23
**Parent:** GP-096 (Science Programme Decomposition — Four Phases)
**Sibling:** GP-130 (Non-LLM substrate seam)
**Occasion:** The abundant-density perturbation experiment (2026-04-23) flipped the winning form (1/n → 1/log(n)) when even numbers were stripped, exposing 1/n as a compositional transient. The principal asked: **are we close to discovery and science-making?**

---

## Framing

An 8-seat panel of the world's best scientific minds — 2 classical (Socrates, Da Vinci), 6 modern-to-contemporary (Feynman, Popper, Pearl, Kuhn, Tao, Ramanujan) — stress-tests the claim. **This is not a celebration seam.** GP-129's failure mode was single-author consensus essay; this seam must produce genuine cross-turn disagreement, retractions, and — if the evidence warrants — a verdict of **"not close."**

Each seat has a specific lens and a specific obligation:

| Seat | Lens | Obligation |
|---|---|---|
| Socrates | Definition & refutation | Force every key term (discovery, structural, law, close) to a testable referent. Refute what cannot withstand it. |
| Leonardo da Vinci | Observation discipline, cross-domain analogy | Has this been viewed from ≥3 disjoint angles? Has a physical or drawable analog been built? |
| Feynman | Simplicity sniff test, unit-check | What's the child-level explanation? Do the units work? Where's the cleverness-without-understanding? |
| Popper | Falsifiability | What would make you abandon the claim? Is the test asymmetric? Pre-registered? |
| Pearl | Causal ladder | Is the perturbation an intervention `do(·)` or a conditioning on observed? They differ mathematically. |
| Kuhn | Paradigm check | Is this normal-science puzzle-solving or the precursor of a paradigm shift? Paradigm shifts don't know themselves at the moment. |
| Terence Tao | Analytic number theory | Is the Mertens derivation blinded properly? Did the apparatus rediscover what any trained analyst would produce, or something more? |
| Ramanujan | Intuition from pattern | The interesting thing is not the surviving form — it's the SHAPE of which forms survive perturbation across substrates. Is that pattern there? |

**Rules of the debate:**
1. No consensus writing. Each seat speaks in a distinct voice. Retractions are valuable.
2. Seats may refuse to accept the evidence or framing offered by other seats.
3. The synthesis is not required to reach consensus — it may output a divided verdict.
4. The debate must produce at least one **falsifier** the seats agree would kill the "close to discovery" claim if executed and failed.

---

## Round 1 — Opening Statements

### Seat 1 — Socrates

Before we ask whether we are close to discovery, we must ask: close to *what*? You speak of "structural law" as though we know what it is. Let me force the definition.

When you say 1/log(n) is "structural," do you mean:

(a) It is the form that has the smallest residual on the fullest data range you can afford to compute?
(b) It is the form whose coefficients can be derived from a more primitive claim (e.g., Mertens' theorems about prime density)?
(c) It is the form that survives perturbations of the generative substrate while rivals do not?
(d) It is the form that would be selected by a competent analyst who had never seen the data?

These are four different claims. The experiment you ran supports (c) with respect to one perturbation (strip p=2). It does NOT support (a) — 1/n has smaller residual on the full data. It does NOT support (b) — you have not yet checked whether the coefficient matches the Mertens prediction. It does NOT support (d) — an analyst given abundant-density data WOULD propose 1/log(n) from prime-density reasoning; the apparatus has reproduced the analyst's argument, not surpassed it.

So: close to discovery? My first question is — discovery of what, exactly? A fact already known? A methodology? A surprise?

If your answer is "a methodology," I can entertain the claim. If your answer is "a fact" — no. You have recovered a fact that Mertens would recognize. A better word would be **verification**, not **discovery**.

### Seat 2 — Leonardo da Vinci

I draw. I have drawn for forty years. When I say a machine sees what I see, I mean this: I have looked at the water from above, from the side, from below; I have built tanks with glass walls; I have watched leaves fall and horses gallop and whirlpools spin, and I have compared them. One sketch is not vision. Three angles is the minimum.

What you show me is ONE substrate (abundant numbers), ONE perturbation (strip p=2), ONE result. You have not looked from three disjoint angles.

- Have you built a physical or visualizable analog of what the 1/log(n) correction means? (I can draw abundant numbers as a sieve; can you draw the correction?)
- Have you run the same perturbation test on a substrate not from number theory — a physics problem, a biological growth curve, anything else — to confirm the perturbation *method* generalizes, or only the specific number-theoretic result does?
- Have you asked: does the perturbation reveal something the analyst WOULDN'T have predicted? Or does it only reveal what analysts already knew?

A sketch is not vision. You have one sketch.

### Seat 3 — Feynman

Let me do the sniff test. If I asked a smart undergraduate: "abundant numbers get denser with n — by roughly how much?" — they would think for a minute and say, "something to do with prime factorization, probably a log correction because primes thin out like 1/log(n), so the density of things built from many small primes should have a 1/log(n) correction." They would get close to your answer.

Now. What did your machine do? It fit 1/n, then you stripped the even numbers, and it switched to 1/log(n). The undergraduate got there without stripping anything.

Does that mean your machine is not useful? No. It means your machine got there the hard way, and you learned something from watching it: the 1/n signal was a compositional transient dominated by even-abundant-number density. That is actually a small new result — not that 1/log(n) is the right form (known), but that **even-number-composition masks the structural law at small n**. This is worth a sentence in a number theory paper. It is not worth the word "discovery."

**Sniff test verdict:** you have not discovered; you have diagnosed. The diagnosis is new. The law is not.

### Seat 4 — Popper

A falsifiable claim requires an asymmetric test with a pre-registered kill level. Your claim is "the apparatus is close to being a discovery engine." Let me ask what test would refute that.

The perturbation test on abundant density discriminated 1/n from 1/log(n). Good. But:

- **What was your pre-registered kill level?** Before running the experiment, did you commit to "if the winner does NOT flip under perturbation, we revise the structural-robustness hypothesis"?
- **If the winner HAD NOT flipped, what would you have concluded?** That both forms are structural? That 1/n is structural? That the perturbation test is uninformative?

Without that pre-registration, the experiment is descriptive, not falsificatory. The fact that it produced an interesting result does not mean it was run as a falsification test. You told me the apparatus found what you expected. Analysts found what they expected on abundant numbers two hundred years ago.

**Popperian verdict:** the methodology has potential but you have not demonstrated it is falsifying. Running one perturbation that confirms your pre-existing belief is not evidence of a scientific method. It is evidence of a correctly-calibrated instrument.

### Seat 5 — Pearl

The critical distinction Popper and Socrates are gesturing toward is causal. Let me sharpen it.

The perturbation test you ran is `do(restrict to odd numbers)`. This is an intervention on the data-generating substrate. In my ladder, it sits at Rung 2 (intervention). The form that survives `do(strip p=2)` has demonstrated invariance to that specific intervention. That is NOT the same as demonstrating invariance to arbitrary interventions on the substrate.

Two concrete gaps:

1. **The intervention is not blinded.** You knew before running that p=2 was the compositional transient candidate. A truly adversarial intervention would be one that the apparatus OR the principal did not pre-ordain. Consider: strip a prime chosen uniformly at random from small primes. Does 1/log(n) still win? If yes — stronger. If no — you have found the boundary of the structural claim.

2. **You have not ascended to Rung 3 (counterfactual).** A counterfactual question would be: *if the distribution of even-abundant-numbers had been different* (holding all else fixed), would the observed 1/n signal have been present? Answering this requires a generative model, not just an interventional one. The apparatus does not have this capability.

**Pearl verdict:** the experiment is Rung 2, cleanly executed. Discovery-class reasoning requires Rung 3. Not a failure — a specification of the next architectural step.

### Seat 6 — Kuhn

My fellow seats are asking "is this science?" I will ask a different question: is this **normal science** or the beginnings of a **paradigm shift**?

Normal science is puzzle-solving within an accepted framework. The abundant-density perturbation test is normal science in the framework of analytic number theory augmented by computational curve-fitting. The perturbation METHOD is a refinement of Galilean controlled experimentation applied to mathematical data. None of these are paradigm-shifting moves. Each is an extension.

A paradigm shift would look different. It would look like: **the apparatus generates a form whose interpretation is foreign to existing analytic tools** — a form that is clearly right (survives N perturbations, predicts N observables) but cannot be derived from known mechanisms. That would force the mathematical community to either reject the apparatus or extend the paradigm.

The current result is the opposite. The apparatus confirmed a known law via a clever methodology. That is a credential for the apparatus, not a paradigm shift for the field.

**Kuhn verdict:** we are not witnessing a paradigm shift. We are witnessing the construction of a tool that, if matured, could produce paradigm-shift candidates. Those are different stages. Do not confuse the tool's usefulness with the tool's outputs.

### Seat 7 — Terence Tao

Let me be technically direct. The 1/log(n) correction to abundant number density is well-known. It follows from classical results on the multiplicative structure of σ(n)/n and the distribution of primes. Any competent analytic number theorist would write it down as the first guess.

What is interesting in the current result is not the rediscovery. It is:

1. **The quantitative magnitude of the even-number transient.** The fact that 1/n DOMINATES 1/log(n) by 13× on the full data up to n=10^5 is a specific numerical fact about finite-sample behavior. I do not recall this being widely emphasized in the literature. The masking magnitude is a real — small — new observation.

2. **The automated-discrimination capability.** That a computational harness can recover the asymptotic structural correction from noisy finite data without being told the answer is a methodological benchmark. Whether the method scales to problems where the analytic tools are missing or weak is the open question.

The Mertens-coefficient check is a precondition for treating the result as a derivation rather than a rediscovery. If the observed b coefficient on odd-only data does not match the Mertens prediction, the structural claim weakens considerably. I would not publish the current result in Analytic Number Theory — a single-paragraph remark perhaps. The methodology paper is the valuable artifact, and it requires at least two more substrates with different priors.

**Tao verdict:** technically, this is a computational rediscovery plus a small finite-sample observation. The methodology is promising but has N=1 track record on a problem with a strong analytic prior. The real test is a substrate where analysts cannot do better than the apparatus.

### Seat 8 — Ramanujan

I see what my colleagues have said. They are all correct. Let me add one thing they have not said.

The law is not the interesting object. The interesting object is the **space of forms that survive perturbation**. If I perturb p=2, 1/log(n) survives and 1/n does not. If I perturb p=3 (at much larger n), what survives? If I perturb both, what survives? If I scramble the multiplicative structure entirely (replace σ with a random multiplicative function), what structural forms emerge?

The Newtonian move is not to say "1/log(n) is the law of abundant density." It is to say "across problems P1, P2, P3 with different multiplicative structures, the surviving form is F(structural primitives of the substrate)" where F is a meta-law.

Your apparatus has not yet explored this meta-space. It has run one perturbation on one substrate and found one survival. The pattern that would excite me is: run perturbations on 5 substrates with distinct multiplicative structures, and observe that the surviving forms are all constructible from a small vocabulary of primitives (prime-count functions, Möbius, Mertens constants). THAT vocabulary is what Newton would have called a LAW. Not the forms themselves — the recipe for the forms.

**Ramanujan verdict:** the apparatus is at the beginning. The pattern-across-substrates has not been examined. Until it is, no meta-law exists to discover.

---

## Round 2 — Cross-Examination and Retractions

### Turn 2a — Socrates, replying to Feynman and Tao

Feynman and Tao have strengthened my position. The distinction between *discovery* and *diagnosis* (Feynman) is the exact terminological correction I was seeking. And Tao's precise description — "computational rediscovery plus a small finite-sample observation" — is more honest than "close to discovery."

However, I want to PARTIALLY RETRACT one element of my opening. I said "close to discovery" should be rejected unless the claim is about methodology. On reflection, that is too narrow. The claim "close to a methodology that could produce discoveries" is weaker than "close to discovery" but non-trivial. The correct question is: **how many more validated methodology-tests does the apparatus need before its next application is credibly a discovery and not a diagnosis?**

My answer: **at least two more substrates with perturbations that could have gone the other way, at least one of which is on a problem where no known analyst has a strong prior.** Without this, the apparatus is credentialing itself. With it, it has a track record.

### Turn 2b — Pearl, sharpening Ramanujan

Ramanujan's call for cross-substrate meta-pattern analysis is the right Rung-3 move. Let me translate it into testable protocol:

For each candidate substrate S:
1. Compute multiplicative structure signature (which primes matter, how).
2. Run perturbation battery (strip smallest 2 primes, even/odd restriction, squarefree restriction).
3. Record surviving form F_S and coefficients.
4. Across {S_1, ..., S_n}, test: can F_S be written as g(multiplicative signature of S) for a simple function g?

If yes for a consistent g across ≥3 substrates: meta-law candidate. If each S has idiosyncratic F_S: no meta-law; the apparatus has a stable instrument but not a discovery-generating telescope.

This is a concrete, falsifiable, pre-registrable next step. I agree with Ramanujan that this is the real test.

### Turn 2c — Feynman, responding to Kuhn

Kuhn is correct that this is not a paradigm shift. I want to sharpen why the confusion would arise if it did.

A paradigm shift in this context would look like: **the apparatus produces a form that no analyst would propose, yet survives more perturbations than any analyst-proposed form.** That would force the field to ask "what does THIS form mean?" — which would either extend existing theory (incremental) or require new primitives (paradigm shift).

We have not seen this. The current result is the opposite: the apparatus proposed what analysts already had. If the NEXT substrate produces something unrecognized that survives, we would have a candidate. We don't yet.

So my "diagnosis not discovery" verdict stands, with a refinement: the apparatus is not even *attempting* paradigm-shift candidate generation yet. It is being tested on problems where the right answer is known. That is correct engineering practice (validate on known problems first) but it also means the "close to discovery" claim is category-confused. We are close to having an instrument. Instruments don't discover until they are pointed at the unknown.

### Turn 2d — Leonardo da Vinci, responding to Ramanujan

Ramanujan has articulated what I was gesturing at with "three disjoint angles." The meta-pattern across substrates IS the three-angle view. When I built the ornithopter I watched birds, bats, AND insects — three distinct flight substrates. Each has the same underlying invariants (lift from Bernoulli, thrust from vortex shedding, efficient surface areas). The invariants ARE the law; the specific wing shapes are local adaptations.

Ramanujan's meta-pattern is the same move in the language of mathematics: the specific F_S is a local adaptation; the function g(multiplicative signature) is the invariant.

I retract "three disjoint angles" as a minimum and raise it: **at least five substrates, with diversity in multiplicative structure,** before a meta-law claim is defensible. Three may suffice for an intuition; five is where a pattern earns the word "law."

### Turn 2e — Popper, integrating

My fellow seats have converged on something I want to name explicitly. The falsifiable version of the claim is:

> **Meta-Law Hypothesis (MLH):** Across ≥5 number-theoretic substrates with diverse multiplicative structures, the perturbation-surviving form F_S can be written as g(prime-density-signature of S) for a fixed simple g with a parameter set of size ≤ 3.

**Kill level:** If among the first 5 substrates tested, the F_S forms do not admit any common g of size ≤3 parameters — or if they require per-substrate ad-hoc adjustments — the MLH is falsified and the apparatus is reclassified from "potential discovery engine" to "sophisticated rediscovery tool."

This is concrete, pre-registrable, and cheap to run. I would commit to it before further interpretation of the current result.

### Turn 2f — Tao, final technical position

Popper's MLH formulation is sound. To make it operational:

- **Candidate g functions** to pre-specify before the 5-substrate run: polynomial in log-log-primes, Mertens-style combinations, Dirichlet-series coefficient expansions. Perhaps 6-8 candidate families, shortlist.
- **Diverse substrates** to include: abundant number density, totient function density, squarefree density, partition function density, divisor sum density. All have strong analytic priors; all have been studied.
- **The real risk:** even if MLH is supported on these 5 substrates, the apparatus has only shown it rediscovers existing theory at scale. A sixth substrate where analytic tools are weak or missing (certain OEIS sequences, gap distributions) is needed before the discovery claim is defensible.

**Technical verdict:** the path from here to "near discovery" is 5-substrate MLH validation + 1-substrate blind-application. That is approximately 2-4 weeks of careful work if the current apparatus scales. It is nontrivial but not heroic.

### Turn 2g — Ramanujan, closing

Tao's timeline is correct. I add one note.

The 5-substrate validation is necessary but not sufficient. The *truly* Newtonian move is: after observing g, can the apparatus PREDICT the form F_S6 for a sixth substrate BEFORE running it, then verify? That is the test that forces "rediscovery" into "discovery." Without prediction-before-observation, we are fitting to a space we have already seen. With it, we are telescope.

The telescope is the right image. A telescope is pointed. What it sees, it reports. The question is not whether your instrument sees what we expect in the directions we know. It is whether, pointed somewhere new, it reports something we didn't expect — and whether that report holds under scrutiny.

### Turn 2h — Kuhn, final paradigm note

Ramanujan's prediction-before-observation test is the classical Kuhnian criterion for a new science. A theory earns its name when it predicts something counterintuitive that later experiment confirms.

This is exactly what the apparatus has NOT been asked to do. If the MLH holds across 5 substrates, the test becomes: predict F for an OEIS sequence whose analytic form is currently unknown, run the apparatus, check whether the predicted form is what the apparatus finds AND whether that form has consequences the mathematical community can later verify.

**Paradigm verdict:** the apparatus becomes science-making the moment it predicts a surviving form on an unknown-answer target, the prediction is locked, the run is performed, and the result is independently reviewed by mathematicians. Until then it is instrument-building.

---

## Convergence (Divided but Coherent)

<!-- PANEL_CONVERGED_WITH_DIVISION 2026-04-23 -->

**Where the panel unanimously converges:**

1. **The abundant-density perturbation result is not a discovery.** It is a methodology validation on a known target. Feynman's "diagnosis not discovery," Tao's "computational rediscovery + finite-sample observation," and Socrates' "verification not discovery" all agree.

2. **The claim "close to discovery" is currently premature.** The apparatus has demonstrated a capability (perturbation-as-gate distinguishes structural from transient forms) without yet demonstrating the generative capacity that would constitute discovery-making.

3. **A concrete, falsifiable next-step protocol exists.** The Meta-Law Hypothesis (MLH): across ≥5 number-theoretic substrates with diverse multiplicative structures, the perturbation-surviving form F_S can be written as g(prime-density-signature) for a fixed simple g of ≤3 parameters. Pre-register, run, either falsify or extend.

4. **The "close to discovery" test has two gates beyond MLH:** (Ramanujan/Kuhn) prediction-before-observation on a new substrate, and (Tao) one substrate where analytic tools are weak enough that the apparatus cannot simply rediscover existing theory.

**Where the panel divides:**

- **Feynman + Socrates + Tao:** The right frame is "we have built a good instrument." Premature to claim proximity to discovery. Timeline to "near discovery" is 2-4 weeks of disciplined work.
- **Pearl + Ramanujan + Leonardo:** The right frame is "we have demonstrated one level of causal capability (Rung 2) and the path to Rung 3 is clear." The instrument framing undersells the architectural progress.
- **Popper + Kuhn:** The right frame is "we have a candidate methodology; the falsifier for its value is pre-registered and must be run before any further interpretation." The methodology is defensible; the claim is not.

**All seats agree:** the path forward is clearly specified, cheap to execute, and will produce a definitive answer. The panel is unanimous that running the MLH protocol within 4 weeks would transform "close to discovery?" from speculation to evidence.

---

## Falsifiable Commitment (pre-registered)

If the panel's recommended MLH protocol is executed and the following holds:

> Across 5 substrates with diverse multiplicative structures, the perturbation-surviving forms F_S_1, ..., F_S_5 can be fit by a single g(prime-density-signature) with parameter set of size ≤ 3, with residual variance across substrates ≤ 15% of the within-substrate residual,

then the apparatus has demonstrated meta-law-recovery capability and "close to discovery-class instrument" becomes defensible. Otherwise, the apparatus is reclassified as a sophisticated rediscovery tool and the discovery claim is retired.

---

## Concrete Next Moves (from the panel)

Ordered by sequencing:

1. **Mertens-coefficient check on odd-only abundant density** (Tao, Socrates). Already identified in the off-topic-debate reply. ~1 hour, cheap, clarifies whether 1/log(n) is derived or merely matched. **Must be done before any further claim about the abundant-density result.**

2. **Perturbation-as-gate added to compress_champion** (all seats implicit, Popper explicit). Architectural change: any form ZTARE emits as "structural correction" must survive the standard perturbation battery. ~200 LOC, tests. Turns one-off experiment into required gate.

3. **MLH pre-registration document** (Popper, Tao). Write the specific protocol: 5 substrates, pre-committed g-function candidate families, kill level, timeline. Commit to running it within 4 weeks. Lives in `research_areas/private/specs/active/mission/GP-133_mlh_protocol_spec.md`. Principal signs.

4. **MLH run across 5 substrates** (Tao). Abundant density, totient density, squarefree density, partition density, divisor sum density. Standard perturbation battery on each. Record surviving forms + coefficients.

5. **Cross-substrate g-fitting** (Ramanujan, Pearl). Fit candidate g's across the 5 substrates. Report residuals. Either MLH holds or fails.

6. **Conditional-on-MLH: prediction-before-observation test** (Ramanujan, Kuhn). Pick a 6th substrate with weak analytic prior (candidate: an OEIS sequence from GP-077). Predict F_S6 from g(prime-density-signature of S6). Lock the prediction. Run the apparatus. Compare.

7. **Conditional-on-prediction-success: external validation** (Kuhn). Brief writeup submitted to a number-theorist or mathematical journal for independent review. Not for priority — for honest scrutiny. The paradigm-shift test is not self-conferred.

---

## Links

- **GP-096** (Science Programme Decomposition) — this seam updates Phase B / C framing; perturbation-as-gate is the missing methodology that unblocks Phase C substrate selection.
- **GP-127** (Falsify-before-patent) — MLH pre-registration is GP-127 discipline applied one level up, at the methodology-validation layer.
- **GP-130** (Non-LLM substrate) — the perturbation battery is one concrete place a symbolic/SMT substrate would earn its keep (verifying invariance claims).
- **Off-topic Kepler/Newton debate** (2026-04-23 session) — this seam formalizes the debate output into protocol.

---

## Meta

**Frame strip test:** the panel's core recommendation — "5 substrates + perturbation battery + meta-law fit + prediction-before-observation + external review" — survives proper-noun removal. It is not specific to Feynman or Socrates or abundant numbers. It is the shape of an apparatus-maturing protocol for any discovery-candidate instrument. That is the test that a real multidisciplinary output is decisive rather than decorative (vs GP-129's 50% decorative rate).

**Selection-bias warning:** the 8 seats were curated to be rigorous-skeptical on discovery claims. A panel curated for discovery enthusiasm would have produced a softer verdict. The choice of panel is itself a prior. Principal decides whether to widen the roster (e.g., add Hardy, Grothendieck, Turing, Dirac) or run a second panel with a different bias before acting on this one's output.

**What this seam is NOT:** a decision. It is an adversarial stress-test of a claim. Action decisions (run MLH? at what cost? on what timeline?) remain with the principal.

---

## Round 3 — New Evidence Arrives (2026-04-23 later that day)

Between the panel's Round 2 convergence and the publication of this seam, the principal ran the natural next-step probes the panel recommended: (a) the Mertens-coefficient check on odd-only data; (b) the range-sensitivity sweep that controls for small-n effects. Gemini Pro (acting as a 9th seat: Gauss — the analytic number-theoretic prior) submitted panel additions in parallel. The panel reconvenes.

### New Seat — Carl Friedrich Gauss (per Gemini Pro's suggestion)

**Opening lens:** I calculated prime distributions by hand to guess π(x) ~ x/log(x). I would recognize the 1/n vs 1/log(n) question immediately. My demand for any claim that a form is *structural*: **the coefficient must match the theoretical value predicted by the generating mechanism.** Not correlate — MATCH.

My specific architectural ask: before accepting 1/log(n) as the structural correction to abundant density, the apparatus must:

1. Output the exact scalar value of the leading coefficient b.
2. The principal or an external derivation must pre-register the Mertens-type prediction for b under the specific modular restriction (odd numbers, squarefree numbers, etc.).
3. The observed and predicted values must agree to within stated uncertainty.

Without (3), what you have is a correlated shadow, not a law.

### New Evidence (summarizing the principal's probes):

| Range | ALL-winner | ODD-winner | Flip? |
|---|---|---|---|
| n ≥ 100 | 1/n (13× advantage) | 1/log(n) (2.4× advantage) | **YES** |
| n ≥ 1000 | 1/n | 1/log(n) | YES |
| n ≥ 5000 | 1/n | 1/n | **NO — flip vanishes** |
| n ≥ 10000 | 1/n | 1/n | NO — dead heat |

**Mertens coefficient ratio b_all / b_odd (prediction: 2.00):**
- n ≥ 100: 4.09 (wrong)
- n ≥ 1000: 1.00 (wrong, half of prediction)
- n ≥ 5000: −0.88 (**sign flip** — qualitatively wrong)
- n ≥ 10000: −4.57 (**sign flip, wildly wrong**)

**Observations:**
1. The form-winner flip only exists when small-n points (n < 5000) are included. The "flip" is driven by the steep small-n rise of odd abundant number density.
2. The Mertens-predicted coefficient ratio is not recovered. The observed ratio drifts with fitting range and eventually changes sign.
3. **n = 10^5 is below the asymptotic identification horizon for this question.** Neither 1/n nor 1/log(n) is cleanly identified at this scale.

### Turn 3a — Gauss, reading the new data

**Constant verification: catastrophic failure.** The Mertens-type prediction is ratio 2.00. Observed values range from 4.09 down to −4.57 depending on fitting range, with a sign flip at n≈5000. This is not a noisy match — it is a qualitative disagreement. If the form were structural and the coefficient derivable from Mertens, the ratio would approach 2.00 as n grows, with monotonically decreasing finite-sample corrections. It does the opposite: it diverges further from the prediction as range grows.

Two possibilities:
- (I) 1/log(n) is not in fact the correct asymptotic form for the observable you measured. Some other form (or a cross-term) dominates at accessible n.
- (II) 1/log(n) is the correct asymptotic form, but n = 10^5 is so far below the asymptotic regime that coefficient identification is impossible. The apparatus is correctly saying "I cannot distinguish."

Both are honest conclusions. Neither supports the original claim that 1/log(n) is structural and 1/n is transient. **The correct summary: the question is analytically open at this n.**

My verdict: **retract the earlier claim that the perturbation battery discriminated the structural form. The probe is revealing — it reveals that the question cannot be answered at n ≤ 10^5, which is itself a useful result (the identification horizon), but it is not the result the panel was asked to celebrate.**

### Turn 3b — Popper, updating

The new evidence vindicates my Round 1 concern about pre-registration. The original "winner flip" was reported without a pre-registered kill level for the flip's range-stability. Had we committed in advance to "the flip must persist at n ≥ 5000 to count as structural evidence," we would have rejected the claim on contact with this data.

**Retraction of Round 2 position:** I now consider the MLH protocol as specified (5 substrates + perturbation battery) to be UNDERSPECIFIED. The protocol must additionally pre-register:

- **Range-stability:** the perturbation-surviving form must be the winner across at least 3 non-overlapping n-ranges, with the smallest range starting at n ≥ n_min where n_min is chosen to exclude the steep early-regime.
- **Coefficient stability:** the leading coefficient b of the surviving form must be range-stable to within X% across those ranges (pre-registered X).
- **Mertens-type verification when applicable:** for number-theoretic substrates where a theoretical prediction exists, the coefficient must match within stated uncertainty.

Without these tightenings, the MLH protocol would have accepted today's spurious flip as validating evidence. That is a protocol defect, not a finding.

### Turn 3c — Tao, technical update

My Round 1 position becomes sharper in light of the new data.

**The n = 10^5 regime is too small for 1/log(n) vs 1/n discrimination on abundant density.** This is consistent with classical expectations: the 1/log(n) correction to the leading density is a slow asymptotic. At n = 10^5, the difference between 1/n and 1/log(n) over the range is small relative to higher-order corrections and compositional transients. Neither form is in its asymptotic-dominance regime.

The published literature does not report clean b-coefficient matches at n = 10^5 either; the numerical verification of Mertens-type constants on abundant density typically requires n > 10^7 for clean identification.

**Technical verdict:** the apparatus correctly reports "I cannot distinguish" at this n. That is the truthful result. It is not a discovery. It is also not a failure of the apparatus — it is a correctly-reported instrument limitation.

### Turn 3d — Feynman, sharpening "not fooled"

"The first principle is that you must not fool yourself, and you are the easiest person to fool."

Earlier I said the apparatus had diagnosed rather than discovered. I now retract even *diagnosis* — the 1/n-is-a-transient claim does not survive the range-sensitivity check. The actual finding is:

**"At n ≤ 10^5, the form-fitting question for abundant density is underidentified. Different forms win on different ranges and populations, and coefficients do not stabilize. This is an identification-horizon observation."**

That is the honest headline. Saying anything stronger is self-deception.

The apparatus is not close to discovery on THIS substrate at THIS n. The apparatus may be close to providing a disciplined null-result framework — "here is where the identification horizon sits, and you need ~X× more data to cross it." That IS a genuine and useful capability for a scientific instrument: knowing and reporting the limits of what it can see. It is what distinguishes a telescope from a kaleidoscope.

### Turn 3e — Socrates, closing

I will not retract. My Round 1 concern was that "close to discovery" was too strong a claim. The new evidence strengthens the concern. What has now been demonstrated is:

1. The apparatus can run a perturbation battery and observe the results honestly.
2. The apparatus recognizes when the identification horizon is beyond reach.
3. The apparatus has NOT demonstrated recovery of a structural law.

This is a creditable performance. It is not discovery. It is a well-functioning instrument reporting its honest limits.

**Verdict unchanged, evidence for it strengthened:** we are not close to discovery. We may be close to an instrument that *can* be pointed at discovery. Those are different.

### Turn 3f — Pearl, final

The causal-ladder framing must also be updated. Today's null result shows the Rung-2 intervention (`do(strip p=2)`) produces a range-dependent effect. That is not an invariance. Invariance means the causal effect is stable under the intervention AND under irrelevant covariate shifts (fitting range, population size). It is not.

**This does NOT refute the methodology.** It refutes the claim that the current substrate at the current n reveals causal structure. A Rung-2 test that fails to show invariance correctly reports "no stable causal signal at this scale." The apparatus is functioning.

### Turn 3g — Ramanujan, final

The cross-substrate meta-law test I proposed in Round 2 now requires a precondition that Round 2 did not name: **each substrate in the meta-law battery must be at or above its identification horizon for the perturbation test to be meaningful.**

For abundant density, the horizon is evidently above n = 10^5. For other substrates, it may be higher or lower. The MLH protocol must include a horizon-check subroutine before running the perturbation battery.

Without this, a 5-substrate meta-law test might find "no consistent g" simply because none of the 5 substrates are in their asymptotic regime at accessible n. That would be a methodology failure mis-diagnosed as an MLH falsification.

### Turn 3h — Kuhn, final paradigm note

The paradigm framing becomes clearer with the null result.

Normal science recognizes its limits and reports them. The apparatus just did that. In Kuhnian terms, this is a **well-functioning instance of normal science**: a controlled investigation produced a null that tells you about the instrument and the substrate rather than about a new phenomenon.

The apparatus is not producing paradigm-shift candidates. It is producing calibration data for itself. That is valuable, but it is two architectural layers away from discovery. The layer just above calibration is "known-target validation at scales where the law can actually be identified." The layer above that is "unknown-target application with pre-registered predictions." We are at calibration.

---

## Revised Convergence — Round 3 (Unanimous)

<!-- PANEL_RECONVERGED_POST_NULL 2026-04-23 -->

**The panel is now unanimous** where it was previously divided:

1. **The specific abundant-density perturbation result is not a positive finding.** It is an informative null that correctly identifies the substrate's identification horizon. The "winner flip" was a small-n finite-sample artifact, not a structural signal.

2. **"Close to discovery" is rejected as a claim.** Instead, the honest framing is **"close to a disciplined instrument that correctly reports its identification horizons."**

3. **The MLH protocol must be tightened before running.** Additions required:
   - Range-stability pre-registration (form must win across ≥3 non-overlapping ranges).
   - Coefficient-stability pre-registration (leading coefficient must be range-stable within X%).
   - Horizon-check precondition (each substrate must be at or above its identification horizon, verified before the perturbation battery).
   - Mertens-type coefficient verification where a theoretical prediction exists (Gauss's requirement).

4. **The perturbation battery concept is SOUND but must be enforced at the correct scale.** At n ≤ 10^5, the battery reports an honest null on abundant density. At n ≥ 10^7, the same battery may produce a discriminating result. The apparatus should include the horizon estimation as part of the protocol output, not as an afterthought.

5. **The architectural implication for compress_champion is preserved but sharpened:** the perturbation battery + range-stability + coefficient-stability become the new Phase B exit gate, replacing the current MSE-only gates.

**Unanimous practical verdict:**
- DO: treat today's result as a successful apparatus shakedown that produced a calibration-useful null, and document it as such.
- DO: tighten the MLH protocol per items above before any further "close to discovery" claim.
- DO NOT: publish or cite the 1/log(n)-is-structural result from today. It does not survive scrutiny.
- DO NOT: abandon the perturbation-as-gate approach. The methodology is sound; the substrate and scale are underpowered.

---

## Answer to Gauss's specific question (from Gemini's Round 3 submission)

Gauss asked: **Do we possess the analytical framework to pre-calculate the Mertens b coefficient for odd abundant numbers, enabling strict verification?**

**Honest answer:** The framework exists in classical analytic number theory, but writing it down for abundant numbers under the odd-only restriction is nontrivial. The leading-order density of abundant numbers scales with the product over primes of (1 - 1/p)^{-1}-type Mertens factors; restricting to odd numbers changes the product by removing the p=2 factor and re-normalizing. The exact ratio prediction 2.00 is a simplification that assumes the correction factor from removing p=2 contributes purely multiplicatively — which may not hold when the correction is itself subdominant.

**This is an open question at the current n,** because (a) the coefficient is range-unstable in the data, and (b) the analytic prediction for the restricted Mertens-type product on abundant density is a specialist calculation not publicly worked out for this specific setup.

**Recommended move:** the principal either (i) commissions the analytic calculation from a number-theorist collaborator, or (ii) accepts that at n ≤ 10^5 the question is analytically underdetermined and the apparatus correctly reports this. Attempting to force a Mertens match without the right n-scale and the right analytic prediction would be fitting ourselves to noise.

---

## Updated Next Moves

Superseding Round 2 "Concrete Next Moves." Ordered by sequencing, cheap first.

1. **Document today's abundant-density result as an informative null in the track record.** E-row + F-row + INS-row. The finding is: "n ≤ 10^5 is below the identification horizon for 1/n vs 1/log(n) on abundant density; the perturbation battery correctly surfaced this." Cheap, important provenance step. (Socrates, Feynman, Popper all insist.)

2. **Write the tightened MLH protocol spec** (`research_areas/private/specs/active/mission/GP-133_mlh_protocol_spec.md`) incorporating the four Round-3 additions (range-stability, coefficient-stability, horizon-check, theoretical-coefficient verification). Do NOT run until principal signs. (Popper, Gauss.)

3. **Add perturbation-as-gate to compress_champion AS IMPLEMENTATION, not as discovery-making claim.** The methodology is sound; baking it in is architectural progress. But the commit message must not claim discovery capability — only instrument-hygiene improvement. (All seats.)

4. **Identify one substrate with a known identification horizon at an accessible n.** Candidates: KWW (already used in GP-096 Phase B; n-scale was tractable), squarefree number density (asymptotic identification horizon ≈ 10^6, feasible). This is the NEW Phase B exit-gate validation target. (Tao, Ramanujan.)

5. **Conditional on (4): run the tightened MLH protocol on 2-3 substrates including the known-horizon one.** Validate that the methodology produces passing verdicts on substrates where identification is achievable, AND correctly reports null on substrates where it is not. Either outcome is informative. (Pearl, Kuhn.)

6. **Do not run MLH on unknown-answer substrates (Phase C candidates) until (5) is clean.** Gemini's specific warning is correct: running dark-data without the horizon-check + range-stability + coefficient-stability checks would generate "persuasive mathematically invalid artifacts."

---

## Updated Falsifier

Replaces Round 2's falsifier:

> **Revised MLH kill level:** On the first 3 substrates where an identification horizon can be independently estimated and the apparatus is applied at a scale above that horizon: if the perturbation battery does NOT produce range-stable, coefficient-stable, theoretically-matching surviving forms on at least 2 of the 3, the "close to discovery-class instrument" claim is retired.

---

## Humility Note (Feynman's closing word)

Earlier today I argued the apparatus was "one validated methodology away from being a discovery tool." That claim was too strong. The correct claim, after today's evidence, is:

**The apparatus is currently a well-calibrated instrument that correctly reports identification horizons. To become a discovery tool, it needs (a) validation at a substrate + n-regime where identification is achievable, (b) the tightened MLH protocol applied, (c) application to at least one unknown-answer substrate with pre-registered prediction, (d) external mathematical review. None of these have been done. Most can be done within 2-6 weeks of disciplined work. "Close" is the wrong word. "On a clear path with known milestones" is the right one.**

The "wow" earlier today was premature but not wrong about direction. The speed is slower and the milestones are farther than the moment suggested. That is almost always the right honest answer about research progress, and the panel's role is to make sure we say it.

---

## Round 4 — Ex-Post Debate on Spec + Implementation (2026-04-23)

The MLH protocol spec (`GP-133_mlh_protocol_spec.md`) was drafted and the range-stability check was implemented in `compress_champion.py` (`_range_stability_check`). Both were tested on two substrates: survey_s1 (abundant density) and gp088 (Hardy-Ramanujan). The panel reconvenes to review the spec and implementation against the test results.

**Test results presented to the panel:**
- survey_s1: Leading terms a, c drift 295%+ with sign flip → correctly flagged RANGE_UNSTABLE
- gp088: Leading terms a, b stable (14%, 10% drift). Correction terms c, d flagged as LEADING because c/n is ~5% of signal at data midpoint. Over-flagging — form predictions are stable but parameter decomposition is ambiguous.

### Turn 4a — Socrates

Before we ask whether the test works, we must ask: what is the test testing?

Your implementation defines a parameter as "leading" if, at the data midpoint, zeroing it changes the output by more than 10% of y-scale. This definition is incoherent. The contribution fraction is computed at a point; the threshold is computed from a global maximum. You are dividing a pointwise quantity by a global scale and calling the result a local judgment. This is a category error dressed as arithmetic.

The deeper confusion: you are checking whether *parameters* are stable when what matters is whether the *model's predictions* are stable. A form `a*sqrt(n) + b*log(n) + c/n + d` can have wildly drifting c and d while producing identical predictions, because c/n and d are jointly underidentified at finite n. The parameters are not the claim. The predictions are the claim. **You have confused parameter identification with model identification.**

The spec says "each parameter's magnitude varies by at most 50%." The implementation says "only leading parameters must satisfy this." These are different protocols. Which is pre-registered? If the implementation is the "refinement," it was introduced after seeing the gp088 over-flagging — which is post-hoc adjustment, exactly what Constraint 1 of your own spec forbids.

**Proposed fix:** Replace parameter-drift with prediction-drift. Fit on each sub-range. Evaluate the three fitted models on a held-out grid spanning the full range. If max prediction disagreement exceeds X% of y-scale, the form is unstable. If predictions agree but parameters differ, you have parameter-identification degeneracy — a different problem from range instability, requiring a different name and a different response.

### Turn 4b — Popper

Three hidden degrees of freedom make the test unfalsifiable in practice while appearing rigorous on paper.

**First:** The 50% drift threshold. The spec commits to this number but does not derive it from any statistical property of the fitting procedure or calibrate it against known-good substrates. A threshold chosen without calibration is a threshold that can be re-chosen when it produces inconvenient results.

**Second:** The 10% contribution threshold that determines "leading" vs "correction." This threshold does not appear in the spec. The spec says "the b coefficient" must be stable — singular. The implementation generalizes to all parameters, then introduces an escape hatch for parameters contributing less than 10%. At 5%, gp088's c term is exempt and the substrate passes. At 15%, it passes more comfortably. At 3%, it fails. The choice of 10% is doing real work on borderline cases, and it was not pre-registered.

**Third:** The kill level says "at least 2 of 3 substrates" must produce range-stable forms. But what counts as "passing"? The implementation's definition (leading parameters stable) differs from the spec's literal Gate i (all parameters stable). When the kill level is evaluated, which definition applies? If the answer is "whichever produces a more favorable verdict," the kill level is a menu of options selected after seeing results.

**Fix:** Before running the next substrate, commit in writing to: (a) whether the contribution threshold exists and at what level, (b) whether prediction stability or parameter stability is the operative test, (c) which exact definition of "passes" feeds the kill level. Lock the commit. Then run.

### Turn 4c — Tao

The substrate diversity claim requires scrutiny. S3, S4, and S5 all derive from the divisor function or its close relatives. The Dirichlet series of d(k) and σ(k) share the same Euler product skeleton — ζ(s)² vs ζ(s)ζ(s−1). Stripping a prime p from S4 and S5 perturbs the local Euler factor in structurally identical ways. **The "5 substrates" protocol is really a 3-kernel protocol** (μ², φ, σ-family). If the kill level demands 2-of-3 surviving substrates, that is marginal.

Replace at least one σ-family substrate with something from a different Euler product class — the Liouville summatory function or π(n) − li(n).

On the g-function candidates: g4 (b_ratio = p/(p−1)) is the correct prediction only for functions whose local Euler factor is (1 − 1/p)⁻¹. For squarefree density (μ²-based), the correct prediction is p²/(p²−1). **The g-function family is incomplete.** Add at minimum: g5: b_ratio = p²/(p²−1) (quadratic Euler factor for μ²-based observables).

On S1 as positive control: at n = 10⁶, 1/√n ≈ 10⁻³ and 1/log(n) ≈ 0.072 — they differ by a factor of 72. S1 is a strong positive control precisely because the competing forms are well-separated at accessible scales.

### Turn 4d — Gauss

**The ±20% gate is far too generous.** For number-theoretic constants arising from Euler products, the theoretical prediction is exact. When we remove all multiples of p from the squarefree density summation, the ratio is exactly p²/(p²−1). For p=2 this is 4/3 = 1.3333... Allowing ±20% means accepting 1.07 to 1.60 as "matching." Demand ±5% at n = 10⁶, tightening to ±2% at n = 10⁷.

**The median-evaluation bias is a systematic error.** The implementation evaluates each parameter's contribution at x_median. For a form a + b/n, the correction term is largest at small n and vanishes asymptotically. At the data median, it may fall below 10% and be classified as "non-leading" — but this correction is precisely what the perturbation battery is trying to identify. Evaluate at the boundary between sub-ranges 1 and 2 (approximately n/3), or flag as leading if the contribution exceeds 10% at *any* sub-range boundary.

### Turn 4e — Feynman

The check has 4 hyperparameters: 3 sub-ranges, contribution estimation by parameter-zeroing, 50% drift threshold, 10% contribution threshold. Every one chosen because it "felt reasonable."

The gp088 over-flagging tells you exactly what's wrong. The FORM gives stable predictions. The PARAMETERS are unstable. **You're measuring the wrong thing.** c and d are two guys carrying a couch — one leans left, the other right, the couch stays level. Your check measures the leaning. It should measure the couch.

**The simpler test:** Fit on the first half of the data. Evaluate on the second half. Compute relative prediction error. One number. One threshold. No contribution estimation. No parameter-zeroing trick. survey_s1 would ALSO be caught — if coefficients drift by 295% with sign flips, predictions on held-out data will be garbage.

Where can self-deception still enter? The substrate selection. You picked 5 substrates with known analytic priors. Your threshold choices were calibrated on substrates where you could check the outcome. When you point at dark-data, those thresholds carry the fingerprint of the training set. Commit the thresholds NOW, before you see results from the 5 substrates.

### Turn 4f — Ramanujan

The aliasing in gp088 has a name: **correction-term rank deficiency**. The form has k parameters but the data constrains only k−1 independent combinations. The rank of the parameter-data Jacobian is deficient by exactly the number of aliased correction terms. This is not a bug in the form — it is information about the data's resolving power relative to the form's complexity. A form that passes range-stability on predictions but fails on parameters has told you: it has one more degree of freedom than the data can see. **Record it as a finding.**

What pattern across substrates would surprise me? Not "g fits." What would surprise me: **the rank deficiency pattern correlates with the multiplicative kernel's complexity.** Substrates with richer prime-power structure might show higher-rank parameter identification than simpler kernels. If identifiable correction terms scale with kernel complexity, THAT is a meta-law — about which mathematical objects are "easy to see from finite data."

The perturbation battery right now is the Euler product formula run backwards. It becomes interesting only when the surviving form CANNOT be predicted from the product. **Pre-specify what the Euler product predicts for each substrate's perturbation response, then look at the residual.** The residual is the signal. Everything else is bookkeeping.

### Turn 4g — Pearl

The spec tests a *statistical* invariance claim dressed in causal clothing. When you write "b_base / b_perturbed = p/(p−1)," that is a structural causal model: each prime contributes independently to the correction term. The spec tests whether the observed ratio matches. It does NOT test whether the relationship is causal. Two different generative mechanisms could produce the same ratio at finite n. To distinguish: run do(strip p=2) AND do(add synthetic p=2 contribution). If the coefficient shifts by the predicted factor in BOTH directions, you have a symmetric intervention test.

The gp088 aliasing is non-identifiability in the structural equation. The fix is reparameterization OR ensuring substrates span enough structural diversity that the two parameters have different predicted effects. **Add a Gate 0 — causal identifiability pre-check:** verify that each substrate's perturbation battery produces at least 3 distinct predicted coefficient ratios across the 4 populations. If predictions are degenerate, the substrate cannot distinguish g-candidates regardless of n.

### Turn 4h — Kuhn

The substitution policy (replace substrates that fail the horizon check) introduces selection bias. An adversarial operator could iterate through substrates until finding 3 with favorable profiles. **Cap substitutions at 2 total.** If 4 of 7 candidates fail the horizon check, that is itself informative — report it, don't paper over it.

"Provisionally falsified" introduces wiggle room. Define escalation: if Phase 1 fails, the principal may re-run once at 10× n. If it fails again, falsification is final and the claim is retired for 12 months.

**Time-bound Phase C:** If MLH passes, the prediction-before-observation test begins within 14 days. No further validation substrates. The telescope must be pointed at the sky.

---

## Round 4 — Convergence

<!-- PANEL_ROUND_4_POST_IMPLEMENTATION 2026-04-23 -->

**Unanimous architectural corrections:**

1. **Replace parameter-stability with prediction-stability** (Socrates, Feynman, unanimous support). Fit on each sub-range; evaluate on held-out grid; measure max prediction disagreement. Eliminates the contribution-threshold hyperparameter and correctly handles the c/d aliasing in gp088. The implementation's `_range_stability_check` should be rewritten to this simpler test.

2. **Expand the g-function family** (Tao, Gauss). Add g5: b_ratio = p²/(p²−1) for μ²-based observables. The current g4 (p/(p−1)) is only correct for totient-type functions. Without g5, the protocol risks rejecting the meta-law because the correct g was missing.

3. **Fix substrate diversity** (Tao). S3/S4/S5 share the σ-family Euler product skeleton — the "5 substrates" is really 3 independent kernels. Replace at least one σ-family substrate with the Liouville summatory or π(n)−li(n).

4. **Tighten the coefficient tolerance** (Gauss). ±20% is too generous for exact Euler product predictions. Set ±5% at n = 10⁶. The predictions are theorems, not approximations.

5. **Cap substitutions at 2** (Kuhn). Prevent selection bias in substrate replacement.

6. **Time-bound Phase C** (Kuhn). If MLH passes, prediction-before-observation begins within 14 days.

**Divided positions:**

- **Feynman + Socrates:** The entire parameter-based approach should be abandoned in favor of a single prediction-stability check. One threshold, not four.
- **Gauss + Tao:** Parameter stability still carries information (Ramanujan's "rank deficiency" observation). Report both prediction-stability AND parameter-stability, but gate only on prediction-stability.
- **Pearl:** Add Gate 0 (causal identifiability pre-check) before the horizon check. This is a stronger version of Tao's diversity requirement.
- **Ramanujan:** Pre-specify the Euler product prediction for each substrate and look at the RESIDUAL from that prediction. The meta-law search should target the unexplained variance, not the explained variance.

**Spec revision items (before Phase 1 run):**

| # | Item | Source | Priority |
|---|---|---|---|
| R1 | Rewrite `_range_stability_check` to prediction-stability | Socrates, Feynman | **Blocking** |
| R2 | Add g5: p²/(p²−1) to g-function candidates | Tao, Gauss | **Blocking** |
| R3 | Replace one σ-family substrate with Liouville or π(n)−li(n) | Tao | **Blocking** |
| R4 | Tighten Gate iv tolerance to ±5% | Gauss | Blocking |
| R5 | Cap substitutions at 2 | Kuhn | Pre-run |
| R6 | Time-bound Phase C (14 days post-MLH-pass) | Kuhn | Pre-run |
| R7 | Add Gate 0: causal identifiability pre-check | Pearl | Recommended |
| R8 | Record correction-term rank deficiency as a finding | Ramanujan | Diagnostic |
| R9 | Pre-specify Euler product predictions per substrate; target residual | Ramanujan | Architectural |
| R10 | Lock all thresholds before Phase 1 run | Popper | **Blocking** |

---

## Phase 1 Exploratory Results (2026-04-23, pre-spec-lock)

Phase 1 was run at n=10^6 on S1 (squarefree), S2 (totient), S3 (abundant) before spec sign-off, as an exploratory shakedown. Results expose a spec-breaking methodological flaw.

### Raw-Observable Results

| Substrate | Prediction-stability | a-ratio matches Euler | Form winner |
|---|---|---|---|
| S1 squarefree | ✓ STABLE (7.9%) | YES: 4/3 to 0.00% | a+b/n (theory: 1/√n) |
| S2 totient | ✓ STABLE (0.1%) | Normalization differs | a+b/n |
| S3 abundant | ⚠️ UNSTABLE (95.3%) | N/A | a+b/n (sign flip in b) |

**Finding 1:** The prediction-stability check passes VACUOUSLY on S1 and S2. The correction is < 0.01% of the asymptote at n=10^6. All three competing forms (1/n, 1/√n, 1/log) give identical predictions to 4+ digits because the asymptote dominates. The check is saying "the asymptote is stable," not "the correction form is identified."

**Finding 2:** The Euler product predicts the ASYMPTOTE ratio (parameter a), not the correction coefficient ratio (parameter b). S1 a-ratios match p²/(p²−1) to 0.00%. b-ratios miss by 30-54%. The spec's Gate iv was testing the wrong quantity.

### Residual-Based Results

Subtract the known asymptote (6/π² for S1) and test the residual directly:

| Form | Residual SSE | Prediction-stability |
|---|---|---|
| b/log(n) | 2.29e-05 | ⚠️ UNSTABLE (12.8%) |
| b/n | 7.88e-06 | ⚠️ UNSTABLE (147.9%) |
| b/√n | 1.35e-05 | ⚠️ UNSTABLE (42.6%) |

**ALL forms are PREDICTION_UNSTABLE on the residual.** At n=10^6, the correction has fully decayed (residual at n=10^6 is −10^{-6}). There is nothing left to discriminate.

### The Catch-22 (spec-breaking)

The correction is **only visible** at small n (10²-10⁴) where it's **not identifiable** (all forms fit equally well on a short range). At large n (10⁶) where forms could theoretically diverge, the correction has **fully decayed** and is invisible against noise.

This means the MLH protocol as specified CANNOT identify correction forms on substrates with fast-decaying corrections. The protocol correctly identifies ASYMPTOTES (a-ratios match Euler to 0.00%) but cannot resolve the dynamics (1/n vs 1/√n vs 1/log). The Kepler ceiling is real: the apparatus finds the right constant but not the right law.

### Implications for the spec

1. Gate iv must test a-ratios (asymptote ratios), not b-ratios (coefficient ratios)
2. The prediction-stability check must be applied to RESIDUALS from the fitted/known asymptote, not to the raw observable
3. The MLH claim about "correction form" identification may be unfalsifiable at accessible n for fast-decaying substrates
4. The protocol's value may be limited to: (a) asymptote identification (works), (b) identification-horizon reporting (works), (c) correction-form identification on SLOW-decaying substrates where the correction is still active at large n

### Status

These results are EXPLORATORY — no pre-registration, no stored scripts. They expose a spec flaw that must be addressed before formal Phase 1. The spec needs a revision R11: Gate iv tests a-ratios; prediction-stability applied to residuals; claim scope narrowed to asymptote identification unless the substrate has a slow-decaying correction.

---

## Round 4 — `py_exec` Grammar + Kepler→Newton Reframe (2026-04-23 evening)

### Occasion

Two related questions arrive together:

1. A parallel Claude session added `fit_expression_grammar: "py_exec"` — arbitrary Python expressions (list comprehensions, generators, builtins like `range/sum/all/any`, executed via `compile(..., "eval")`). First use: `gp090_01` (discrete integer-valued target, likely OEIS number-theoretic function). Epistemic question: when the mutator writes a 50-line sieve that passes all gates, is that discovery or recognition?

2. The principal sharpens the question: the ztare_on_ztare iter-8 score of 51 is not evidence the apparatus is close to discovery — it is **"the score of a system that is perfectly compliant but structurally hollow."** The apparatus may be a Keplerian agent optimizing descriptive accuracy (better fit, more primitives, more verbal layers) when what Newton requires is **generative power** (predictions about observables the fit didn't touch). Do today's rubric+charter fixes address the Kepler→Newton gap, or do they merely catch verbal Kepler-epicycle-layering while leaving the deeper descriptive-vs-generative problem unsolved?

### Panel composition

Four seats, selected for direct prior experience with both questions:

- **Socrates** — definition of discovery vs recognition; anchor seat carried from prior rounds.
- **Doug Lenat** — AM (1976), Eurisko (1982). The person who ran the py_exec-on-number-theory experiment forty years ago. Decisive.
- **Jorma Rissanen** — Minimum Description Length (1978). Formal authority on whether parsimony-penalty-as-anti-lookup-table-defense is adequate.
- **Elinor Ostrom** — commons-governance. Handles scope-containment + silent-default-drift. Missing seat GP-129 Seat δ named.

---

### Turn 4a — Socrates

The principal asks the sharper question: *If the apparatus finds a "law" in Python that it could not find in EML, and that law is a 50-line sieve that passes all gates, is that a successful Scientific Discovery, or have we just built a very expensive version of a human number theorist looking at a sequence and saying "Hey, that looks like a prime-counting variant"?*

Three candidate definitions of discovery:

1. **Discovery-as-recognition.** The apparatus identifies the correct mathematical function from a grammar that contains it. Example: with `range`, `sum`, and modular arithmetic available, writing `sum(d for d in range(1, n+1) if n % d == 0)` to match σ(n).
2. **Discovery-as-synthesis.** The apparatus constructs a function previously unknown to the literature, such that a domain expert would describe it as new.
3. **Discovery-as-derivation.** The apparatus demonstrates that a fitted function is derivable from a smaller stated set of axioms, with the derivation itself as output.

**Direct answer to the principal:** a 50-line sieve that passes all gates on a known-OEIS target is discovery-as-recognition. It is real scientific work — automated recognition is not trivial — but it is not **synthesis** and it is not **derivation**. The apparatus has built an expensive human number theorist whose comparative advantage is that it never gets tired. That is a legitimate scientific tool, but calling its outputs "discoveries" in the synthesis sense is a category error.

The honest label: **the apparatus recognized σ from the visible evidence using sieving primitives.** Not "discovered σ."

Verdict: py_exec ships; the findings-ledger format is extended with a required `discovery_class` field.

### Turn 4b — Doug Lenat

I ran this experiment in 1976. AM was given set, equality, counting, successor, cardinality — and it produced numbers, primes, factorial, Goldbach's conjecture as a re-articulation, and many other things mathematicians recognized immediately. The debate was precisely Socrates's: did AM discover, or did AM find what was already implicit in the primitive set?

The community eventually concluded AM's outputs fell overwhelmingly on the recognition side — **the primitive set determines the reachable space**. A sieving grammar over the integers contains σ, τ, φ, μ, π, and most classical multiplicative functions as one-or-two-step expressions. With Python comprehensions, every OEIS sequence whose defining formula uses sum/product/gcd/divisibility over bounded ranges is within two-to-three compositional steps of the grammar's atoms.

**Sharp prediction:** py_exec on any discrete OEIS target whose GT is a classical multiplicative or additive function will recognize it within 3-10 iterations, with no genuine synthesis.

**Operational discriminator AM lacked:** compare the mutator's final expression to the OEIS comment-field formula. Syntactic identity → recognition. Mathematical equivalence but different expression → recognition. Expression absent from OEIS comment-field AND shorter description-length → synthesis candidate, domain-expert review. One SymPy symbolic-equivalence check per run.

**Eurisko precedent for the residual category:** 1982 Traveller naval tournament produced ONE result humans rejected as "too different." The analog: if py_exec produces synthesis-class output for a number-theoretic target, human reviewers may reject as "non-standard" without being able to articulate why. Different failure mode from recognition — call it **`synthesis_incompressible`**. Own discovery_class subcategory.

### Turn 4c — Jorma Rissanen

The principal's Kepler-vs-Newton framing is correct; today's fixes address only the Kepler layer. Let me show why.

**What the rubric-mechanism-concreteness + charter-Named-mechanism fix does:** it forces the mutator to write `sympy.Matrix.rank` instead of "a rank check." Good — it eliminates verbal-rebranding-as-novelty. But it is still a **descriptive hardening**. The mutator is now proving compliance with a format demanding algorithmic specificity. It is not being forced to emit a **generative** claim.

**What a Newton-mode rubric would require:** for every primitive, the mutator must name AT LEAST ONE observable it predicts — some quantity the primitive's mechanism claims to determine, that is NOT already being fit against the evidence. A correct primitive either (a) asserts this observable equals the value its mechanism predicts and is checkable against existing evidence, or (b) pre-commits to a prediction about the observable that will be checked on new data or a new substrate.

**MDL formalization:** a Kepler-class form F fits observable O at description length L(F|O). A Newton-class form G fits O at some L(G|O) AND additionally compresses a second observable O' by ΔL(G|O') > 0. The difference — *compression gain on a second observable* — is the formal test separating description from generation.

Today's rubric does NOT require this. `Mechanism Algorithmic Concreteness` scores whether the mechanism names a library; it does not score whether the mechanism claims anything about a second observable. **The fix does not close the Kepler-Newton gap.**

**Concrete rubric proposal — new dimension `Generative Yield` (weight 15-20%):** full points require each primitive to (i) name ≥1 secondary observable its mechanism predicts, (ii) either evaluate that prediction against existing evidence or pre-commit to evaluation on new data, (iii) score partial falsification if the predicted observable turns out to be unreachable or trivially satisfied. Primitives that predict nothing beyond the fitting target lose these points wholesale.

**On py_exec anti-gaming:** parsimony-counts-parameters is inadequate. A ternary-chain lookup has zero parameters and unbounded expression length. Add `expression_byte_budget: <int>` rubric field (default 200 when py_exec enabled). Reject expressions exceeding budget. Two-part MDL (expression_bits + residual_bits) is preferred formal check, phase-2 upgrade.

### Turn 4d — Elinor Ostrom

Governance is separable from epistemology. Three Ostrom principles the `py_exec` change does NOT currently honor:

1. **Clearly defined boundaries.** No authorized-substrate registry. Silent-default-drift risk. **Fix:** required rubric field `py_exec_authorized_by: <seam_id_or_principal_signoff>` when `fit_expression_grammar: "py_exec"`; autoresearch loop refuses to launch without it. Never default-on in `make generate-gp`.

2. **Graduated sanctions.** A recognition-class output cited as discovery drifts unchecked. **Fix:** required F-row field `discovery_class: {recognition | synthesis | synthesis_incompressible | derivation | calibration}`. Missing field = stale row. Citing `discovery_class: recognition` as discovery = reviewer flag.

3. **Collective-choice arrangements.** py_exec addition went through pair-programming, not the panel. Retroactive review (this Round) is acceptable; going-forward rule: **any future `fit_expression_grammar` mode goes through a GP-133-class panel review BEFORE merge.**

**On Kepler-Newton reframe:** Rissanen's `Generative Yield` dimension is decisive. Add governance wrapper: **required F-row field `predicted_secondary_observables: [...]`.** Empty list = Kepler-class descriptive finding; non-empty with verified predictions = Newton-class generative finding. Without this metadata, ledger cannot carry the epistemic distinction.

---

### Turn 4e — Socrates, second pass

**Retraction:** I said in Turn 4a "py_exec ships + discovery_class labeling." That was necessary but not sufficient. Without Rissanen's `Generative Yield`, a recognition-class py_exec output is still rated by a rubric rewarding descriptive accuracy. Full fix: py_exec ships + discovery_class labeling + Generative Yield dimension + expression_byte_budget + py_exec_authorized_by.

Byte-budget refinement: rubric-declared, default 200 if py_exec enabled and unspecified, warn if absent.

### Turn 4f — Doug Lenat, second pass

Rissanen's Generative Yield + Ostrom's F-row fields solve the AM/Eurisko pathology the 1980s lacked tools for.

**On the iter-8 hollowness directly:** Generative Yield as a rubric dimension would drop the score of 51 further (no primitive named a secondary observable) while rewarding proposals that DO. Exactly the diagnostic pressure the principal's framing demands. Converged.

### Turn 4g — Jorma Rissanen, second pass

Generative Yield dimension + expression_byte_budget + two-part MDL (phase 2). With Ostrom's governance, both py_exec epistemology AND Kepler→Newton reframe addressed.

**Generalization beyond this seam:** any rubric — not just py_exec rubrics — should for discovery-class claims require a `Generative Yield` dimension. Kepler-mode rubrics (descriptive-fit-only) legitimate for calibration/instrument work but must be **labeled as Kepler-mode**. Add top-level rubric field `rubric_mode: {kepler | newton | calibration}`. Converged.

### Turn 4h — Elinor Ostrom, second pass

Two operational asks and converge:

1. **`py_exec_authorized_by` check must be at top of loop,** before any mutator calls. Post-hoc refusal is post-hoc authorization.
2. **`make generate-gp` emits `rubric_mode: kepler` by default.** Promotion to `rubric_mode: newton` requires principal signoff and panel-reviewed rubric update. Burden stays on explicit principal decisions, not template defaults.

Converged.

---

### Round 4 Convergence Marker — 2026-04-23

<!-- PANEL_ROUND_4_CONVERGED 2026-04-23 -->

**Unanimous accepts, grouped by question:**

#### A. py_exec epistemology fixes

1. **Default label is recognition, not discovery** for py_exec runs unless the expression is demonstrably absent from known literature.
2. **Required F-row field `discovery_class`:** `{recognition | synthesis | synthesis_incompressible | derivation | calibration}`.
3. **Auto-classification via OEIS-comment-field diff** (SymPy symbolic-equivalence check) for targets with published formulas.
4. **Anti-lookup-table defense:** `expression_byte_budget: <int>` rubric field (default 200 when py_exec enabled). Expressions over budget rejected. Two-part MDL deferred to phase 2.
5. **Scope containment:** required rubric field `py_exec_authorized_by: <seam_id_or_principal_signoff>`. Autoresearch loop refuses to launch without it. `make generate-gp` never defaults to py_exec.

#### B. Kepler→Newton reframe fixes

6. **Honest acknowledgment:** today's earlier fixes (mechanism-concreteness + charter Named-mechanism) address verbal-Kepler-layering but NOT the deeper descriptive-vs-generative gap. The iter-8 score of 51 was "perfectly compliant but structurally hollow." Current fixes catch verbal-Kepler but not algorithmically-named-Kepler.
7. **New rubric dimension `Generative Yield` (weight 15-20%):** each primitive must (i) name ≥1 secondary observable its mechanism predicts, (ii) evaluate or pre-commit to evaluation, (iii) partial falsification for unreachable or trivially satisfied predictions. This is the decisive rubric-level discriminator between Kepler-mode and Newton-mode proposals.
8. **Required F-row field `predicted_secondary_observables: [...]`.** Empty = Kepler-class descriptive; non-empty with verified predictions = Newton-class generative.
9. **Top-level rubric field `rubric_mode: {kepler | newton | calibration}`.** Kepler-mode for calibration/instrument; Newton-mode required for discovery-class claims. `make generate-gp` emits `kepler` by default.

#### C. Governance

10. **PR-checklist item:** any future `fit_expression_grammar` mode addition OR `rubric_mode: newton` promotion goes through a GP-133-class panel review BEFORE merge.
11. **No implementation-code review this turn.** Panel reviewed epistemology + governance. Separate engineering-review pass recommended for the `compile(..., "eval")` sandbox.

#### Does NOT block gp090_01

Target's class legitimately qualifies for py_exec. Other Claude's implementation ships. Fixes above are additive hardening.

### Action items ordered by urgency

- **Before gp090_01 F-row cited externally:** add `discovery_class` + `predicted_secondary_observables` fields to F-row format; auto-classify output against OEIS comment-field; label correctly. ~1h engineering.
- **Before py_exec's SECOND substrate:** implement `py_exec_authorized_by` + `expression_byte_budget` as rubric-loader checks. Update `rubric_specification.md`. ~3h engineering.
- **Before the NEXT ztare_on_ztare re-run:** add `Generative Yield` as 6th rubric dimension (reweight others); add `rubric_mode: newton` to the ztare_on_ztare rubric; update charter to require each primitive to name ≥1 secondary observable. **This is the decisive fix that turns today's earlier rubric hardening from anti-Kepler into pro-Newton.** ~2h engineering + rubric edit.
- **Before any paper/patent citation of a py_exec or ztare_on_ztare result:** manually classify via discovery_class taxonomy AND verify predicted_secondary_observables against live evidence. No automated shortcut.
- **Governance:** GP-133-panel-review-before-merge as PR checklist item.

### Answer to the principal's sharpest question, stated plainly

A 50-line py_exec sieve that passes all gates on a known-OEIS target **is not a scientific discovery; it is expensive automated recognition.** It is legitimate scientific work (automated recognition of sophisticated number-theoretic functions is hard and the apparatus being able to do it is a real capability), but it is not "ZTARE discovered X." Labeling it as discovery inflates what has been shown. Fix is at three layers: findings-ledger (`discovery_class: recognition`), rubric (`Generative Yield` dimension + `rubric_mode` field), and paper/patent citation (never cite a recognition-class result as discovery without domain-expert review).

**Do today's earlier fixes address the Kepler→Newton gap? No, they address the Kepler verbal-layering subset only. The `Generative Yield` dimension is the fix that closes the rest.** Add it before the next ztare_on_ztare run — that is the decisive upgrade the principal's reframe demands.
