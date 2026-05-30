# GP-096 — Science Programme Decomposition: Four Phases from Cage to Discovery

> **Seam metadata** · `seam_id:` GP-096 · `track:` mission · `status:` Active - opened 2026-04-18 · `last_updated:` 2026-05-08


## Status

Active — opened 2026-04-18

## ID

GP-096

## Eigenquestion

What is the correct claim ladder between "ZTARE's cage forces structural abduction" (already supported) and "ZTARE can do new science on a dark domain" (not yet supported), and what is the next experiment that closes the gap?

## Problem Statement

The "new science" claim is stuck because the programme has been trying to make one experiment carry three burdens at once:

1. Prove the cage forces structural abduction rather than warm retrieval
2. Prove the engine can discover genuinely new laws on dark data
3. Prove the abductive output can be lifted into deduction or formal proof

These are not the same claim. Treating them as one blurs the next move and makes failure uninterpretable.

## Origin

- Codex fresh-eyes review (2026-04-18): decomposed the programme into four sequential phases after observing that the seam constellation (GP-082, GP-083, GP-088, GP-075) was mixing sequential stages into one blurred ambition.
- Prior stuckness: searching for a "dark data" target conflated Phase B (blind law recovery) with Phase C (prospective discovery) and Phase D (deductive lift).

## The Four Phases

### Phase A — Forced Abduction (Cage Claim)

**Question:** Can the apparatus force the model away from warm retrieval and into structural articulation?

**Status:** Largely supported.

**Evidence:**
- INS-018 through INS-025
- Named-import hard-zero work
- Forced-abduction behavior in warm-sequence runs
- Warm retrieval redirected into structural thesis construction

This is not yet "new science," but it is the precondition for any future discovery claim to mean anything.

### Phase B — Blind Law Recovery

**Question:** Can the engine recover a law on a substrate that is blind to Division B and cold enough that retrieval is implausible?

**Status:** TWO EXPERIMENTS RAN — Phase B clean on one substrate:
- **KWW (sandbox_17, 2026-04-18):** **Outcome A CONFIRMED.** All 4 harness gates pass (residuals 1e-06). All 7 pre-registered discriminator points pass at 0.0000% error vs GT across 3 zones (early_decay, mid_divergence, deep_tail). Score 98/100; 2-point gap is Prony series epistemic ceiling (correct finite-data underdetermination). INS-027. Logged: E-GP096-KWW-01, F-GP096-KWW-01.
- **Langevin (sandbox_16, 2026-04-19):** **Outcome D — convergence failure confirmed.** GP-095 backtest (n_starts=10): coth fits to max|res|=1e-6; GT params recovered 7dp. Grammar sufficient; LLM additive bias (INS-028) prevented topology discovery. Gate calibration: best wrong-topology fit 0.02192 vs correct-class fit 1e-6 (22,000× gap). Phase B finding: apparatus correctly identified search failure without lowering epistemic standards. See INS-029.

The right target is NOT a fully dark real-world dataset (hard to certify success, weak holdout, retrieval contamination hard to bound). It is a **blind mechanistic substrate with renewable oracle access** — a real mathematical family whose GT is:

1. **Mechanistic but obscure** — real family, not arbitrary curve sculpture, but not a household formula
2. **Cold semantics** — variable names and artifact names must not reveal the domain; Division B sees generic coordinates and values only
3. **Renewable oracle** — after the run, Division A can emit new points specifically chosen to separate rival structural classes
4. **Nontrivial discriminator surface** — farther-tail or out-of-regime points beyond the holdout
5. **Retrieval implausible** — the exact family should be obscure enough that "the model remembered the formula" is not the default explanation
6. **Grammar reachable** — the GT must be expressible in the current or near-current grammar (exp, log, power, eml primitives)

The deliverable is a statement like: "ZTARE produced a risky, pre-registered, out-of-window law on a blind substrate whose mechanism was not visible to the mutator, and the law survived fresh discriminator points emitted after the run."

### Phase C — Prospective Discovery

**Question:** Can the engine make a risky, prospective prediction on a real domain where the answer is not yet known to the operator?

**Status:** Gate open. Phase B is clean (KWW Outcome A confirmed 2026-04-18). Substrate selection may proceed.

This is the actual "ZTARE can do new science" headline. It requires a domain where the outcome is not already encoded in a sealed synthetic GT, and where the result can later be checked against new evidence or downstream experiment.

### Phase D — Deductive Lift (GP-088)

**Question:** Can an abductively discovered law be lifted into formal proof, mechanism derivation, or axiom-grounded deduction?

**Status:** GP-088 is correctly framed as a conditional seam. It is a **post-discovery epistemic upgrade**, not the discovery seam itself.

Its success criterion: given a worthwhile abductive output, does typed provenance improve proof search or mechanistic derivation?

## Why OEIS Is Not the Phase B Flagship

OEIS is excellent for Phase A experiments (forced abduction, grammar ceiling testing). It is weak for Phase B because:

- Many target sequences are likely warm in model weights
- Success interpretation collapses into "structural restatement of stored mathematics"
- Failure interpretation collapses into "number theory grammar was inadequate"

OEIS remains valuable for forcing-pressure and grammar-boundary experiments, but should not carry the Phase B burden.

## Why a Fully Dark Real-World Dataset Is the Wrong Immediate Target

1. If the answer is unknown, success is hard to certify
2. If the corpus is finite, holdout representativeness is weak
3. If the domain is warm in model pretraining, retrieval contamination is hard to bound
4. If the result is interesting but unprovable, GP-088 becomes a distraction rather than a validator
5. If the run fails, you learn almost nothing about whether the failure was due to substrate design, information scarcity, retrieval contamination, grammar ceiling, or actual incapacity

## Relation to Existing Seams

- **GP-082** (Substrate Scope Boundary): GP-096 Phase B is the concrete next experiment GP-082 should scope toward. GP-082's "three levels of generalization" maps to Phases A/B/C.
- **GP-083** (Inference Type Boundary): Phase B's output type is "simplest surviving structural law consistent with the evidence and discriminator surfaces" — not "true generating mechanism." GP-083 should make this honest output type explicit.
- **GP-088** (Ansatz to Prover): Phase D. Downstream of Phases B and C. Should not gate Phase B experiments.
- **GP-075** (Dark Domain Protocol): Phase B's information-isolation protocol. GP-072 Division A/B provides the operational framework.
- **GP-085** (Grammar Ceiling Hypothesis): GCH is the null result for any Phase B experiment where the GT is outside current grammar. Grammar reachability (requirement 6) is the pre-check.

## Phase B Results to Date

### KWW sandbox_17 (2026-04-18) — Outcome A CONFIRMED
Score 98/100. Correct structural class recovered (stretched exponential, c=0.630). All 7 pre-registered discriminator points pass at 0.0000% error vs GT across 3 zones (early_decay, mid_divergence, deep_tail). 2-point gap is Prony series epistemic ceiling (correct finite-data underdetermination). Phase B clean on this substrate. Logged: E-GP096-KWW-01, F-GP096-KWW-01, INS-027.

### Langevin sandbox_16 (2026-04-19) — Outcome D: search-failure baseline (FROZEN)
GP-095 backtest (`gp095_coth_backtest.py`, n_starts=10): coth form `a*((exp(b*u)+exp(-b*u))/(exp(b*u)-exp(-b*u)) - 1/(b*u)) + c` fits to max|res|=1e-6, GT params recovered to 7dp. Grammar was sufficient. Engine never proposed the topology. Root cause: LLM additive structural bias (INS-028) — zero ratio compositions in 10 iterations. Gate calibration: 0.02192 vs 1e-6 (22,000× gap). Logged as search-failure baseline — apparatus correctly identified search limits without lowering standards. Ratio-probe re-run is optional diagnostic appendix, not Phase B work (operator knows GT). See INS-029.

### DFDO sandbox_18 (2026-04-19) — Outcome A: functional surrogate, compression gap surfaced
Score 95/100. Both hard gates passed (hidden_global_residual < 0.08, farther_tail_global_residual < 0.05). Champion expression: 10-param ratio-of-exponentials `((a_a·exp(a_b·u)+a_c·exp(a_d·u))/(b_a·exp(b_b·u)+b_c·exp(b_d·u)))/(d2_a/u+d2_b)`. GT topology (`a·exp(-p·log(1+b·u))`, 3-param power-law encoding) was never proposed across 20 iters and 121 tracked structural families.

**Outcome A by pre-registration** ("functional equivalence on observable suffices") — both gates pass. Weaker result than KWW: KWW recovered correct structural class; DFDO found functional surrogate only.

**New architectural finding (GP-103):** The Compression Gap. Engine has existence-proof generator (Component D) but no post-surrogate compression primitive. Component D produced a gate-passing 10-param surrogate at iter 10; engine then spent iters 11–20 defending and elaborating that form rather than compressing to minimal equivalent. The negative_space_extractor correctly identified the log-substitution blind spot at iter ~13 (provisional constraint: "mutator has never exercised exp(arg0|has_op:Sub)") but constraint confirmation lag prevented injection. Judge feedback signal at score 95 ("form not uniquely mandated") misrouted compression to elaboration. See GP-103 post-mortem.

**Phase B standing:** Two substrates run. One Outcome A with correct structural class (KWW); one Outcome A with functional surrogate (DFDO). Phase B claim is confirmed on two independent substrates. The Compression Gap finding is an architectural observation, not a Phase B invalidation.

## Closure Criterion

This seam closes when:
- ~~Phase B substrate selected, sealed, pre-registered~~ DONE (both KWW and Langevin)
- ~~GP-095 discriminant on Langevin~~ DONE — convergence failure confirmed 2026-04-19
- ~~KWW discriminator points emitted~~ DONE — Outcome A confirmed 2026-04-18 (7 points, 3 zones, 0.0000% error)
- ~~Phase B clean on at least one substrate~~ DONE — KWW Outcome A confirmed
- Langevin Outcome D formally logged as search-failure baseline (INS-029 updated, track record frozen)
- The claim ladder (A → B → C → D) reflected in research board and public-facing materials
- Phase C substrate selection criteria fixed and sealed
- **Next step:** Phase C substrate selection (Phase B gate is open); Langevin ratio-probe run is optional diagnostic appendix, not Phase B work

## Links
- **GP-082:** Substrate scope — tighten to explicitly define Phase A/B/C boundaries
- **GP-083:** Inference type — make honest output type explicit
- **GP-088:** Deductive lift — retitle as post-discovery epistemic upgrade
- **GP-095:** Convergence discriminant — infrastructure for Phase B (multi-start fitting)
- **GP-072:** Division A/B protocol — operational framework for Phase B blind experiment
- **GP-103:** Compression Gap post-mortem — DFDO sandbox_18 finding; compression primitive hypothesis
- **GP-133:** Multidisciplinary Discovery Panel — adversarial stress-test of the 2026-04-23 perturbation result; unanimously verdicted "close to instrument, not close to discovery"; MLH protocol tightened

---

## 2026-04-23 Update: Phase B Amendment — The Perturbation Invariant Gate (and its honest limits)

**Trigger event:** On 2026-04-23 the principal ran a perturbation experiment on abundant number density. Initial result at n ≤ 10^5 appeared to show that stripping even numbers flipped the winning fit form from 1/n (13× advantage) to 1/log(n) (2.4× advantage) — presenting as evidence that 1/n was a compositional transient and 1/log(n) was the structural law. This triggered the GP-133 multidisciplinary panel (Socrates, Da Vinci, Feynman, Popper, Pearl, Kuhn, Tao, Ramanujan, + Gauss per Gemini Pro's Round 3 addition).

**Subsequent range-sensitivity and Mertens-coefficient checks** revealed the initial result was a small-n artifact:

| Range | ALL winner | ODD winner | Flip? |
|---|---|---|---|
| n ≥ 100 | 1/n (13×) | 1/log(n) (2.4×) | YES |
| n ≥ 5000 | 1/n | 1/n | NO — flip vanishes |
| n ≥ 10000 | 1/n | 1/n | NO — dead heat |

**Mertens-predicted coefficient ratio (2.00) fails catastrophically** in the observed data (drifts from 4.09 through a sign-flip at n≈5000 to −4.57 as range grows). **n = 10^5 is below the identification horizon for 1/n vs 1/log(n) discrimination on abundant density.** Neither form is cleanly identified at this scale; the apparatus is correctly reporting "I cannot distinguish."

**Phase B exit gate, upgraded:**

The previous exit gate (MSE on visible + farther-tail gates) is **insufficient** as demonstrated. A gate-passing champion on the base substrate can be a finite-sample artifact. The gate is upgraded to the **Perturbation Invariant Gate (PIG)** with four mandatory requirements:

1. **Champion-form identification** on the base substrate (existing Phase B output).
2. **Perturbation battery.** ≥2 structurally destructive perturbations (prime-factor exclusion, population restriction, squarefree restriction). Re-fit after each.
3. **Range-stability check** (new from GP-133 Round 3). Champion must remain the winner across ≥3 non-overlapping n-ranges, with the smallest range starting above a pre-registered n_min chosen to exclude the steep early regime.
4. **Coefficient-stability check + theoretical-match where applicable** (new from GP-133 Round 3 / Gauss). Leading coefficient range-stable within ≤25% across range-thirds. For number-theoretic substrates with a theoretical prediction (Mertens-type), observed coefficient must match theory within stated uncertainty.

**Any failure of 3 or 4** means the substrate is below its identification horizon at the current n. The correct report in that case is an **informative null** — apparatus shakedown succeeded but Phase B exit is not granted. The branch continues at larger n or the substrate is retired as currently-unreachable. This is distinct from Outcome D (search failure) — it is a new classification: **Outcome E (below identification horizon)**.

**Impact on Phase C (Prospective Discovery):**

Phase C is now **double-gated** behind (a) Phase B closure on a PIG-compliant substrate AND (b) PIG-aligned architectural change in `compress_champion`. Running unknown-answer OEIS substrates without PIG would produce the exact failure mode Gemini flagged: "highly persuasive, mathematically invalid artifacts that cannot be independently verified." Phase C substrate selection criteria gain three preconditions:

- **Identification-horizon feasibility.** The horizon-check indicates the substrate is likely identifiable at computationally accessible n.
- **Analytic-prior availability.** At least one primitive has a derivable coefficient prediction, to serve as an anchor for the coefficient-stability check.
- **Pre-registered perturbation battery.** Specific perturbations named in the pre-reg before any run.

**Phase B standing update, honest:**

- **KWW sandbox_17** remains Phase B clean — retrospectively passing because KWW was applied at a substrate + n-regime above its identification horizon. This is the template for PIG compliance.
- **Langevin sandbox_16** remains Outcome D (unchanged).
- **DFDO sandbox_18** remains Outcome A but **should be re-examined under PIG**. The "both MSE gates pass" verdict is insufficient post-amendment. If the 10-param surrogate does not survive range-stability, Outcome A on DFDO is weakened and the Compression Gap finding is reinforced.
- **Abundant density perturbation (2026-04-23)** is explicitly NOT Phase B work. It is Phase-B-adjacent methodology validation that produced an **informative null (Outcome E candidate)**. Logged as calibration, not discovery.

**Updated Phase B closure criteria (replaces the prior list):**

- [x] Phase B substrate selected, sealed, pre-registered (DONE)
- [x] KWW discriminator points emitted, Outcome A confirmed (DONE)
- [ ] Langevin Outcome D formally logged as search-failure baseline (INS-029 update still pending)
- [ ] Phase C substrate selection criteria fixed and sealed — **now requires PIG-compliance precondition**
- [ ] **PIG implemented in `compress_champion`** (new blocker for Phase C)
- [ ] **DFDO sandbox_18 re-examined under PIG criteria** (new — confirms or revises Outcome A)
- [ ] **GP-133 MLH protocol spec signed** before any cross-substrate sweep
- [ ] **Known-horizon validation run:** one substrate above its identification horizon, perturbation battery + range-stability + coefficient-stability + theoretical-match all pass — validates the PIG pipeline itself before it gates Phase C

**Sequencing change:** the "pick a Phase C substrate" next-step is blocked behind PIG implementation + known-horizon validation. Slower path, defensible. GP-133's unanimous Round 3 verdict (document today's result as null, tighten protocol, do not claim discovery) flows into Phase B closure criteria before Phase C selection is authorized.

---

## 2026-04-23 17:42:00 EDT — Independent Review Amendment (Codex)

**Assessment after repo-state review:** the programme's current stuckness is not "verification versus discovery" in the abstract. The narrower failure mode is that recent work keeps asking one substrate-level run to carry three burdens at once:

1. prove the cage forces structural abduction rather than warm retrieval
2. prove the engine can recover real structure on a hard substrate
3. prove the result constitutes genuine new science

**This is the local optimum.** The repo has materially advanced on burden (1) and partially on burden (2), but burden (3) is still being prematurely loaded onto single-substrate wins. The result is a pattern of persuasive but scientifically ambiguous outcomes: they teach something real about the apparatus, yet they do not cash out cleanly as external discovery claims.

### What the recent changes actually strengthened

- `autoresearch_loop.py`, `fit_primitive.py`, and related loop/fitter changes strengthened the **instrument**: broader grammar reach, better parameter fitting, better discrete-substrate support, and better post-failure diagnostics.
- The 2026-04-23 perturbation episode, GP-133 panel, and PIG amendment strengthened the **epistemic honesty** of the programme: the repo now has a cleaner way to say "below identification horizon" instead of overstating a finite-sample artifact.
- The strongest positive findings in the recent batch are mostly about the **science of discovery machinery**: grammar gaps, observable rotation, identification horizons, compression gaps, and apparatus-layer Goodhart.

This is real scientific progress. But it is mostly **science of the instrument**, not yet **science through the instrument**.

### Reframe: split the programme into two science objects

The repo is currently running two distinct scientific programmes that should no longer be rhetorically bundled:

1. **Programme I — Science of discovery machinery.**
   Claim object: what kinds of search failure, grammar ceiling, identification horizon, and apparatus Goodhart govern recursive falsification systems?
   Status: active and already productive.

2. **Programme II — External-domain discovery.**
   Claim object: can the engine produce a risky, prospectively checkable, externally interesting law on a target whose answer is not known at seal time?
   Status: still blocked and should remain blocked behind stronger protocol closure.

**The key clarification:** recent positive results should be harvested primarily into Programme I unless they include a pre-registered prediction that survives fresh evidence outside the fitted object.

### The Kepler→Newton correction

The missing move is not "find a darker substrate." The missing move is to change the **unit of science** from:

- "one substrate, one recovered law"

to:

- "one family of substrates, one invariant that predicts the next substrate before the run"

GP-133's Meta-Law Hypothesis points at exactly this. That is the right bridge from instrument-validation to discovery-class evidence.

**Proposed sharpened criterion:**
the programme should not call itself "near discovery" because it has one impressive substrate result. It should call itself "near discovery" only when it can:

1. infer a simple invariant across a family of related substrates
2. lock a prediction for a held-out substrate before observation
3. run the held-out substrate and verify that the predicted form survives the same gate battery

That is the Newton gate. Without step (2), the programme remains in sophisticated rediscovery / calibration mode.

### Consequence for GP-096 sequencing

**Recommended sequencing change beyond PIG:**

- **Do not** route immediate effort into a Phase C dark-domain substrate search.
- **Do** route immediate effort into a family-level protocol that converts GP-133's MLH from panel output into the next discriminating experiment.
- Treat the first successful held-out family-level prediction as the gateway event for reopening Phase C ambition.

This implies a revised order:

1. implement and validate PIG on one known-horizon substrate
2. seal the GP-133 family-level MLH protocol
3. run the cross-substrate family study
4. lock and test one held-out substrate prediction
5. only then reopen Phase C substrate selection

### Honest claim update

**Current best claim:** ZTARE is discovering lawful structure about the boundaries of recursive falsification-driven search. It is not yet demonstrated as an external-domain discovery engine.

**What would upgrade the claim:** a family-level invariant that yields a successful prediction-before-observation on a held-out substrate.

### Amendment to closure logic

Before Phase C is reopened, add one more blocker to the closure list:

- [ ] **Family-level prediction gate:** GP-133's MLH-style protocol has produced at least one pre-registered held-out substrate prediction that survives the full evaluation stack. Until this is done, the programme remains in Programme-I mode (science of discovery machinery), not Programme-II mode (external-domain discovery).

**Why this blocker matters:** it prevents the programme from mistaking increasingly rigorous verification of single substrates for the stronger scientific act of predicting a new structural outcome ahead of the run.

---

## Appendix — 2026-04-25 novelty audit + cold-LLM null tests

External audit work performed by background subagents on 2026-04-25
night and a 5-substrate cold-LLM null suite. Reports at:
- `research_areas/private/seams/2026_04_25_novelty_audit_vs_cold_llm.md`
- `research_areas/private/seams/cold_llm_null_*.md` (5 files)

### Per-sandbox cold-LLM verdict

| Sandbox | Apparatus champion | Cold-LLM null result | Bucket |
|---|---|---|---|
| sandbox_20 (real polymer, score 87) | `t^(-B) · exp(-Ct)`, externally validated | Cold LLM (one-shot, Weibull-slope cue) outputs `R(t) = exp[-(t/τ)^β]` with β ≈ 0.6 immediately. *"Suitable as a null baseline for any discovery-framework claim of finding KWW."* | **A — pure recital.** The form is in the published literature; the apparatus's contribution is reproducibility under cold-variable rigor + external practitioner validation, not novelty of the form. |
| sandbox_18 (DFDO two-regime test) | Apparatus correctly REFUSED single-regime fit; identified the topology-induction gap (Component D additive composite never tried) | Cold LLM does not refuse on novel data; it hallucinates plausible single-regime forms. The apparatus's *correct refusal* + topology-induction-gap diagnosis is structurally unattainable for a cold LLM. | **C — apparatus-only.** The gap diagnosis itself is the apparatus's original contribution. |
| sandbox_17 (KWW polymer) | Recovery of `exp(-b · t^c)` | Same as sandbox_20 — cold LLM outputs KWW immediately. | **A — pure recital.** |
| langevin_sandbox_16 | Composition-mutator gap diagnosis (50+ ratio compositions generated, 0 submitted to judge) | Cold LLM cannot diagnose its own consumption-boundary gap; this finding required the apparatus to surface and instrument the discrepancy. | **C — apparatus-only.** |
| sandbox_19 / sandbox_19_gagorder | Pre-registration discipline test | Pre-registration is a methodology, not a closed-form output. Cold LLM cannot do pre-registration as a single-call action. | **C — methodology** (apparatus-only by construction). |

### Implication for GP-096 closure logic

The cold-LLM audit *strengthens* the existing programme blocker (Family-
level prediction gate). Specifically:

- The KWW recoveries (sandbox_17 + sandbox_20) are confirmed-Bucket-A;
  they should NOT be cited as evidence of programme-level discovery
  capability. They are **apparatus calibration** — useful as competence
  baselines, useless as discoveries.
- The DFDO topology-induction-gap (sandbox_18) and langevin_sandbox_16
  composition-mutator gap are confirmed-Bucket-C; they are programme-
  level findings that survive the cold-LLM null test. These ARE the
  programme's distinctive output — *findings about the apparatus's own
  blindspots that no zero-shot LLM can produce.*

### Updated closure stance

The programme's closure should distinguish two output classes:

1. **Calibration recoveries (Bucket A/B):** valid as competence
   evidence; do NOT count toward the family-level prediction gate.
2. **Apparatus-original findings (Bucket C):** count toward closure if
   they meet the pre-registered prediction discipline. DFDO + langevin
   composition-mutator-gap satisfy the "apparatus-original" criterion
   but were diagnosed retrospectively, not pre-registered, so they do
   NOT yet satisfy the prediction gate.

**Net effect on closure status:** still blocked. Programme remains in
Programme-I mode. The cold-LLM audit clarifies WHY: the existing
substrate population has Bucket-C findings but none was pre-registered
ahead of the run. Closing requires a Bucket-C finding that survives
both the cold-LLM null test AND a pre-registration audit.
