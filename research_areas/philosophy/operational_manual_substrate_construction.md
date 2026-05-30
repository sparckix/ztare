# ZTARE Operational Manual for Scientific Discovery

**Status:** Public — mandatory reading before adding any substrate, grammar construct, or pipeline component
**Date:** 2026-04-17
**Provenance:** Distilled from GP-027→GP-080. Updated continuously as new failure modes are earned.
**Relationship to Paper 5 (Treatise):** The Treatise explains *why* the principles work — permanent,
academic, no runbook. This manual explains *how not to break them* — paranoid, updatable, engineering.
If GPT-5 can do gradient descent in its head tomorrow, Chapter 2 changes. Chapter 2 of the Treatise does not.

---

## Chapter 1: The Three Non-Substitutable Legs

*Distilled from `three_legs_of_ztare.md`. Read that document for full derivation.*

ZTARE rests on three legs. Remove any one and the apparatus collapses into something already in
the literature (curve fitting, model selection, or LLM-as-judge).

### Leg 1 — Invert (Falsification is cheaper than construction)

ZTARE's first move on any candidate is *how would I kill this?*, not *does this fit?*
Gates, quarantines, and the bounded discriminator exist so a failed hypothesis is diagnosed
in seconds, not absorbed as free parameters.

**Operational consequence:** Never merge RAM-layer state into the validator. Accumulation belongs
outside the ALU. Negative evidence must be terminal, not absorbed as regularization.

### Leg 2 — Compress (Asymptotic survival, not parameter count)

A claim earns status only by surviving outside the window it was fit in.
ZTARE does **not** reward minimum parameter count — it enforces farther-tail holdout survival.
A parsimonious finite-window surrogate is *more* dangerous than a messy global law,
because parsimony is what makes the surrogate persuasive.

**Operational consequence:** The holdout set must be authored outside the candidate's claim region.
Any test surface derived from the candidate's own output is suspect.

### Leg 3 — Adversarial Disagreement (Truth survives structured disagreement)

Invert + Compress leave a single verifier in the loop, and a single verifier is gameable.
The third leg is:
- **Firing Squad** — independent judges scoring the same candidate; disagreement is signal
- **Meta-Judge** — a judge of judges when the firing squad splits
- **Semantic escalation gate** — where the apparatus admits it cannot decide alone

**Operational consequence:** Never make a single oracle central. "Use a bigger model as
the judge" is not leg 3. Leg 3 requires disagreement surface, not scale.

| Remove | ZTARE becomes |
|---|---|
| Invert | A model-selection harness that absorbs failure as complexity |
| Compress | A fitter with a falsifier — wins the window, loses the law |
| Adversarial disagreement | LLM-as-judge with extra steps. Gameable by a good mutator |

---

## Chapter 2: The Cognitive Gym — Caging the LLM

*Distilled from `cognitive_gym.md`. Read that document for full derivation and evolution history.*

An LLM inside a constrained validation loop produces better science than an unconstrained LLM,
for the same reason a weightlifter inside a squat rack lifts more without dying. The cage is not
the obstacle. The cage is what lets you push harder.

### The Four Layers

| Layer | Owner | Does | Does NOT |
|---|---|---|---|
| **Semantic Router** | LLM | Picks functional form (topological "gear") | Compute coefficients |
| **Topological Sieve** | Component C | Probes GT corrector shape, emits 2-bit descriptor | Select the form |
| **Deterministic Sidecar** | SciPy `curve_fit` | Fits parameter values to evidence | Search function space |
| **Contamination Gate** | Code | Suppresses hints that narrow search below threshold | Inject information |

### The Separation of Concerns Rule

When these boundaries blur, the system breaks. Every GP-074 integration bug traced to a boundary violation:

| Concern | Owner | NOT the owner |
|---|---|---|
| "What family of functions might fit?" | LLM | SciPy, Component C |
| "What are the optimal parameter values?" | SciPy | LLM |
| "What shape is the residual?" | Component C | LLM |
| "Is this hint safe to inject?" | Contamination Gate | LLM, operator |
| "Does this formula generalize?" | Holdout gate (deterministic) | LLM, judge |

**Operational check:** Read any LLM prompt. Find every number the LLM is asked to produce.
If any of those numbers will be used directly as parameter values → rewrite the prompt to
ask for structure only.

### The Evolution of the Cage

Each layer was added because the previous configuration hit a specific failure mode:

| GP | Failure mode | Layer added |
|---|---|---|
| GP-027 | Numerical hallucination (LLM guessing 0.081234) | Deterministic Sidecar (SciPy) |
| GP-035 | Combinatorial explosion (10,000 random forms) | Components A+B (structural pruning) |
| GP-061 | Null result on Selkov (search space too large) | Component B (negative space) |
| GP-074 | Shape guessing (LLM couldn't characterize residual) | Component C (residual fingerprint) |
| GP-080 | Grammar semantic leak (DOSE_SCALED named the domain) | Contamination Gate at grammar layer |

### Why "Gym" Not "Prison"

The cage doesn't make the LLM dumber. It removes failure modes that prevent the LLM from
proposing ambitious functional forms it could otherwise explore:
- Removing arithmetic → LLM stops hallucinating precision, starts proposing bolder topologies
- Contamination gate → LLM keeps searching instead of stopping when the hint leaked the answer
- Corrector library → LLM's structural intuition has tested vocabulary to land on

---

## Chapter 3: Epistemic Hygiene — Hard Rules for Substrate Construction

*Original content of this manual.*

### Why This Chapter Exists

Every time a new substrate is added to ZTARE, there is pressure to name things after the domain,
inject domain knowledge into the grammar, or shorten the contamination gate "just this once."
Each of these moves destroys the epistemic validity of the run without leaving a visible error.
The engine still runs. The score still rises. But the discovery claim is hollow.

This manual collects every anti-pattern we have paid for in lost iterations and invalid results.
It is not theory — it is a checklist with teeth.

---

## Rule 1: Name the Math, Not the Physics

**Trap:** When extending the grammar (Component D `CompositionCommand` enum, rubric penalty lists,
prompt templates), naming constructs after the physical domain you are currently testing.

**Why it breaks:** The LLM sees the command name in its prompt. A domain name activates training-weight
retrieval. The mutator stops reasoning from residuals and starts retrieving "pharmacokinetics" or
"quantum mechanics" from memory. The discovery is memorization, not inference.

**Examples:**
| Wrong (semantic leak) | Correct (math op) |
|---|---|
| `DOSE_SCALED` | `BIVARIATE_SCALE` |
| `SCHRODINGER_DECAY` | `COMPOSE(exp_decay, sinusoid)` |
| `PHARMACOKINETIC_ABSORPTION` | `exp_decay` (already in library) |
| `ECONOMIC_MULTIPLIER` | `BIVARIATE_SCALE` |
| `time_var`, `dose_var` | `primary_var`, `scale_var` (or just `x1`, `x2`) |

**Test before committing:** Read every new grammar construct name aloud without context.
Can you describe what it does without mentioning the application domain? If no — rename.

**Canonical fix:** `DOSE_SCALED → BIVARIATE_SCALE`. Documented 2026-04-17, GP-080.

---

## Rule 2: The LLM Is a Semantic Router, Not a Calculator

**Trap:** Prompting the LLM to propose or refine numerical parameter values.

**Why it breaks:** LLMs hallucinate precision. Asking "what is the value of ke?" invites a confident
fabrication. The engine's separation of concerns is:

| Layer | Owner | What it does |
|---|---|---|
| Semantic Router | LLM | Selects topological "gear" — picks functional form from grammar |
| Deterministic Sidecar | SciPy `curve_fit` | Fits parameter values to evidence |
| Contamination Gate | Code | Suppresses hints that narrow search below suppression threshold |

Any prompt that asks the LLM to output a coefficient, rate constant, or threshold value
is a contract violation. The LLM output must be a structural choice (a command + operand labels),
never a numerical claim.

**Operational check:** Read the LLM prompt. Find every number the LLM is being asked to produce.
If any of those numbers will be used directly as parameter values → rewrite the prompt to ask for structure only.

---

## Rule 3: Variable Substitution Is Typographic, Not Semantic

**Trap:** Confusing "rename the variable" (safe) with "inject domain knowledge" (unsafe).

**The distinction:**
- `n → t`: Typographic. The letter `t` does not tell the LLM what `t` represents.
  It is a continuous float instead of an integer. Required for `curve_fit` to work without crashing.
  **Safe.**
- Naming the variable `time_hours_post_dose`: Semantic. The LLM infers the domain.
  **Unsafe — rename to `x1`.**

**Operational rule:**
- Variable names in Division B artifacts (evidence.txt, charter, rubric) must be opaque:
  `x1`, `x2`, or single letters without domain meaning.
- Division A artifacts (GT script, holdout, denylist) may use domain names internally —
  Division B never reads them.
- `generate_substrate.py --variables x1,x2` is the correct invocation for bivariate substrates.

**Corollary — dimensionality vs. axiology:**
Telling the engine there are two columns of floats is dimensionality — not a cheat.
Telling the engine the second column represents an administered dose is an axiom — a cheat.
The number and type of independent variables is physics. What they represent is oracle knowledge.

---

## Rule 4: The Contamination Gate Is Non-Negotiable

**Trap:** Weakening or bypassing the contamination gate because "it's just a hint."

**Why it breaks:** The contamination gate is what separates ZTARE from "give the LLM more signal."
Any hint that narrows the search space below the suppression threshold — even a true, well-intentioned
hint — converts discovery into retrieval.

**The test (from Component C spec):** If the hint were given directly to a competent expert,
would it let them identify the ground-truth functional form without seeing the data?
If yes → suppress the hint.

**Corollary — rubric penalty lists:** Rubric penalties for specific named models
(e.g., "penalty: proposes Michaelis-Menten by name") are fine — they prevent name-retrieval gaming.
Rubric penalties for mathematical structures (e.g., "penalty: uses any exponential") are contamination —
they artificially narrow the search space.

---

## Rule 5: The GT Script Is Division A. Always.

**Trap:** Putting any GT information (parameters, functional form, derivation) in Division B artifacts.

**Division A / Division B boundary (GP-072 protocol):**

| Artifact | Division | What it may contain |
|---|---|---|
| GT script (`*_gt.py`) | A | Parameters, formula, evidence grid, f_true, f_dominant |
| Evidence holdout | A | Held-out (x1, x2, z) triples |
| Denylist | A | GT-specific vocabulary |
| Evidence visible | B | (x1, x2, z) triples — opaque variable names, no domain context |
| Charter | B | Neutral problem statement — "find a law governing z(x1, x2)" |
| Thesis seed | B | Empty axioms or single neutral sentence |
| Rubric | B | Scoring criteria — no GT form, no named parameters |
| Gate harness | B | Evaluates predicted vs. observed — no formula |

**The sentinel enforces this mechanically.** But the sentinel only catches denylist vocabulary.
It does not catch implicit leaks (e.g., a charter that says "the law has two phases").
Human review of Division B artifacts is required before `make seal`.

---

## Rule 6: `make seal` Runs Before the Loop, Never After

**Trap:** Running the sentinel after the loop has already written GT vocabulary into `thesis.md`.

**Why:** `thesis.md` accumulates the mutator's discovered hypotheses across iterations.
By iteration 3, it will contain whatever structure the mutator found — including terms from the
denylist if the engine correctly identified the GT. Running the sentinel post-loop will always
produce hits. Those hits are expected and correct: they are evidence the engine converged.

**The seal attests to the state of the sandbox at construction time**, before the loop has written
anything. Run `make seal PROJECT=... RUBRIC=...` immediately after `generate_substrate.py`, before
any loop invocation.

---

## Rule 7: Stage 1 Is Apparatus Validation, Not Discovery

**Trap:** Publishing Stage 1 (synthetic data) results as evidence that the engine "discovered" the law.

**Why:** Synthetic data is generated by the law the engine is trying to find. The data surface is
perfectly shaped for the answer. If the engine finds `exp_decay + exp_decay` on biexponential
synthetic data, that is standard nonlinear regression — not discovery. The surface was designed
to match the answer key.

**Epistemic scope of Stage 1:**
- Claims: infrastructure works, `curve_fit` handles continuous floats, variable substitution correct
- Does not claim: engine discovered the law, law is novel, result generalizes

**Stage 2 (real data with structural noise) is required for discovery claims.**

Log Stage 1 results as `apparatus_verified`, not `discovery`. Do not include Stage 1 in any
publication or ledger entry that uses discovery language.

---

## Substrate Construction Checklist

Before running `generate_substrate.py` for any new substrate:

- [ ] **Grammar constructs named after math ops**, not domain (Rule 1)
- [ ] **LLM prompt outputs structure**, not numerical values (Rule 2)
- [ ] **Division B variable names opaque** (`x1`, `x2`, not domain terms) (Rule 3)
- [ ] **Division A/B boundary drawn** — GT script, holdout, denylist all in Division A (Rule 5)
- [ ] **Charter contains no functional form hints** — "find a law governing z(x1, x2)" only (Rule 5)
- [ ] **Rubric penalties target named models**, not mathematical structures (Rule 4)
- [ ] **`make seal` planned for immediately post-generation**, before any loop (Rule 6)
- [ ] **Stage 1 / Stage 2 scope documented** in seam if synthetic data is used (Rule 7)

---

---

## Chapter 4: The Evidence-Grammar Diagnostic — What Hardy Actually Is

*Distilled from GP-080→GP-083 crucial experiment sequence. Updated 2026-04-18.*

When the engine hits a plateau (stagnation at a high-scoring champion that fails the farther-tail
discriminator), the bottleneck is in one of two places:

1. **Evidence** — the data grid cannot discriminate the champion from the true form. The engine
   found the simplest survivor consistent with the visible window. This is the correct empirical
   behavior — the engine is doing exactly what a competent Kepler should do.

2. **Grammar** — the engine's AST vocabulary cannot express the true form, even if the data would
   discriminate it. The mutator lacks the "Lego bricks" to build the correct topological structure.

These are independently testable, and **must be tested independently.** A confounded experiment
(enriched data + grammar patch simultaneously) cannot distinguish which intervention was central.

### The Hardy Inversion

The question "what would it take to build a Hardy?" (a mechanism that rejects score-97 empirical
fits on structural grounds) admits two competing answers:

**Answer A (Formal Verification):** Build a deductive proof engine (Lean/Coq) that receives axioms
and attempts to derive the champion form. If the proof fails, reject the champion. This is the
textbook "Hardy checks Ramanujan's work" framing.

**Answer B (Evidence Grid Design):** Build a mechanism that computes where the champion and its
nearest structural rival diverge most, and proposes the next measurement there. Hardy is not a proof
engine — Hardy is the system that tells Ramanujan what to measure next.

**Answer A fails because the axiom selection problem IS the eigenquestion selection problem.**
If the operator feeds `E=hv` into the prover, the operator has already done the discovery.
The prover confirms; it does not discover. This is oracle contamination through the axiom channel
(identified independently by the Systems ML reviewer, GP-083 Turn 2).

**Answer B is architecturally consistent** — it produces a typed, stateless, deterministic operation
(compute divergence surface, propose measurement point). It belongs in the decomposed operations
(Treatise Chapter 1), not in the residual (Chapter 3). It extends the farther-tail gate from a
static discriminator to a dynamic one.

**The synthesis (earned from the Claude-vs-Gemini debate, 2026-04-18):** Answer B solves the
*necessary* condition (the engine must see discriminating data). It does not guarantee the
*sufficient* condition (the engine must have the grammar to express the true form). Both conditions
must hold. But the evidence test is $1 and the grammar test is $1, so test them sequentially,
cheapest first.

### Rule 8: Test Evidence Before Grammar

**Trap:** When the engine hits a plateau, immediately extending the grammar (adding primitives,
composition modes, or series expansion rules) to "help" it find the truth.

**Why it breaks:** Grammar extensions are Lakatosian auxiliary hypotheses. Each extension weakens
the "same grammar works across domains" progressive-programme claim. If you quietly patch the
grammar before testing whether data alone would suffice, you have (a) confounded the experiment
and (b) added an epicycle the programme must now defend.

**Protocol:**

| Stage | Intervention | Expected outcome | What it proves |
|---|---|---|---|
| 3a | Add discriminating data to visible evidence. Same grammar. | Champion falsified. Engine either finds true form (data was bottleneck) or hits WALL (grammar is bottleneck). | Resolves evidence vs. grammar ambiguity. |
| 3b | If 3a fails: add targeted grammar primitive (e.g., two-term composition). Same enriched data. | Engine finds true form with grammar extension. | Confirms grammar was the sufficient condition. Data was necessary but not sufficient. |
| 3c | If 3b fails: add structural primitive (e.g., truncated series expansion). Same enriched data. | Engine finds true form via bottom-up series stacking. | The true form requires a fundamentally different construction mode. |

**Total cost of the three-stage diagnostic: ~$3.** Total cost of Lean/Coq integration: months.
Run the cheap experiments first. Each failure is a clean architectural finding.

**The Gemini objection (acknowledged):** "Structure dictates Reach — if the machine doesn't have
the math Lego bricks, the anomaly will just cause it to crash." This is a real constraint. The
mutator's token-probability distribution is biased toward epicycles (polynomial patches, log
adjustments) rather than large topological restructuring (moving subtraction inside a denominator).
Stage 3a will likely produce epicycles before restructuring, and may hit WALL without finding
the true form. **This is the expected and informative outcome.** The failure signature at Stage 3a
is what makes Stage 3b a controlled experiment rather than a premature grammar patch.

### The General Principle

When a verification system hits a plateau, the operator faces a choice between adding evidence
and adding grammar. The Mungerian inversion: "How do I guarantee I never find the truth?" reveals
that *either* insufficient evidence *or* insufficient grammar is individually sufficient to block
discovery. But they are not interchangeable fixes. Testing evidence first is cheaper, preserves
Lakatosian programme status, and produces a clean failure signature if the grammar is the bottleneck.

**The one-sentence compression:** Hardy is not a proof engine. Hardy is the system that decides
what to measure next. The farther-tail gate is half of Hardy. Automated evidence grid design
(Component F) is the other half. Both are cheap, typed, stateless, deterministic operations.
They belong in Chapter 1 of the Treatise, not Chapter 3.

---

## Canonical Anti-Pattern Register

| ID | Name | First observed | Rule violated | Fix |
|---|---|---|---|---|
| AP-001 | `DOSE_SCALED` semantic leak | GP-080, 2026-04-17 | Rule 1 | Renamed `BIVARIATE_SCALE` |
| AP-002 | Post-loop sentinel | GP-078, 2026-04-17 | Rule 6 | Seal before loop |
| AP-003 | Charter GT derivation | GP-072 seam, 2026-04-16 | Rule 5 | Charter is Division B — no formulas |
| AP-004 | `int()` cast on continuous GT | GP-080 analysis, 2026-04-17 | Rule 3 | `generate_substrate.py` continuous mode |
| AP-005 | Stage 1 overclaim | GP-080 seam debate, 2026-04-17 | Rule 7 | Two-stage strategy; Stage 1 = `apparatus_verified` |
| AP-006 | Within-withheld-class feature collapse | gp163d v2 backtest, 2026-04-26 | Rule 9 (new) | R26 G-CROSS-CLASS-FEATURE-SUPPORT + per-system enrichment |
| AP-007 | Vacuum gate verdicts (form_str-key bug) | gp154 audit, 2026-04-26 | Rule 10 (new) | Suppress write when gate refused upstream; surfaced by 2B effectiveness audit |

---

## Chapter 5: Cross-Class Feature Discipline (added 2026-04-26)

The gp163d 17-form exhaustive backtest established a class of failure modes the original
Operational Manual did not name: a substrate can pass every per-class validity check (Rule 1
through Rule 8) and still be structurally insufficient to support the discovery the operator
believes it is asking for. This chapter exists because two real runs (gp163d v2, gp154 v2)
both capped below the Newton-step threshold for the same underlying reason — a reason invisible
to the visible-class diagnostic primitives that R13 substrate_critic ran with.

### Rule 9: Within-Withheld-Class Feature Support

For every (withheld_class, feature) pair the substrate exposes, the within-class span on that
feature must be non-trivial — at minimum a 0.5 dex relative range, ideally matching the visible
class's span. A withheld class with a single feature value (a "surrogate") cannot be discriminated
within-class by any closed-form law that uses that feature as a bridge axis. Joint forms across
multiple features fail when ≥2 withheld classes are each collapsed on different features
(the gp163d cross-class joint-form blocker pattern).

**Operational consequence:** Run R26 G-CROSS-CLASS-FEATURE-SUPPORT (the new substrate critic
detector) before any 3-class substrate goes live. If R26 flags a `cross_class_joint_form_blocker`,
the substrate cannot honestly support cross-class discovery via joint(feature_a, feature_b)
forms. Either enrich (per-system data via the EGE workflow) or formally abstain on the affected
class via `r11_excluded_classes` / `honest_null_rows()`. Do not run the apparatus against
the structurally insufficient substrate.

**Concretely (the gp163d v2 example):** Class B (clusters) had `mass_log10 = 14.5` constant
across all 84 cluster rows. Class C (binaries) had `radius_log10 = -2.0` constant across
all 12 binary rows. Disjoint-feature collapse → no joint(mass, radius) form has within-class
DoF for either class → 17 form families exhaustively tested, none cleared MRE < 0.5 cross-class.
The fix was Umetsu+2016 per-cluster M_500c (real, citable) for B and per-bin Gaia DR3 separations
(real) for C. Class C mass remains synthesized + flagged because per-row binary mass does not
exist in the source data (the rows are aggregate g_bar bins, not individual binaries). See
`projects/gp163d_unified_accel/CHANGELOG.md` for v3 provenance.

### Rule 10: Meta-Gate Cadence

The apparatus has four meta-gates that detect *its own* blind spots. Run them on the schedule
their cost structure dictates:

| Gate | When | Default | Why |
|---|---|---|---|
| 2A static scope linter | Pre-commit hook on changes to `src/ztare/{diagnostics,gates,orchestrator}/` | always-on (~50 ms) | catches scope-narrowing in diagnostic primitives at write time |
| 2B dynamic effectiveness audit | Weekly OR after gate-dispatcher edit | always-on (~5 sec, no LLM) | mines run logs for "gate engages but never flags" patterns (the form_str-key bug fingerprint) |
| 2C post-run LLM auditor | End of every CAPPED run, opt-in via `enable_post_run_meta_audit: true` | OFF by default (~$0.005, ~6 sec) | the LLM identifies which gate would have moved the score, with scope-extension suggestions |
| EGE evidence-gap-enrichment | Pre-iter-1 IF R26 flagged a collapse, opt-in via `enable_evidence_gap_enrichment_proposals: true` | OFF by default (~$0.05, ~30 sec) | proposes literature sources to fill substrate feature gaps; operator-actioned via separate `make enrich-substrate` |

**Operational consequence:** 2A and 2B should be on for every developer; 2C and EGE are opt-in
per substrate to control LLM cost. Production runs (paper-grade) should set both flags true so
the operator gets a structured audit + enrichment proposal artifact for every capped run.

### Rule 10a: The Karpathy ALU/RAM Split (architectural framing)

ZTARE has two improvement loops, not one:

- **ALU loop (apparatus self-improvement):** Cage gates, AST-distance enforcement, R20-R24
  anti-laundering, score caps, scope-narrowing detection (2A), effectiveness audit (2B).
  Tools the apparatus uses to *improve itself*.
- **RAM loop (substrate self-improvement):** R26 cross-class feature support detection,
  EGE enrichment proposals, manual `make enrich-substrate` workflow. Tools the apparatus uses
  to *propose substrate improvements*.

When a run caps below the Newton-step threshold, the post-run meta-audit (2C) decides which
loop to act on. If the cap is due to apparatus gaps ("R10 didn't engage"), the action is
apparatus-side. If the cap is due to substrate gaps ("Class B has collapsed mass axis"), the
action is substrate-side. Conflating the two loops is the recurring meta-failure pattern this
chapter exists to prevent.

**Operational consequence:** When you read a meta-audit recommendation, classify it as ALU-loop
or RAM-loop before acting. Apparatus-side fixes are typically small code changes; substrate-side
fixes are typically per-system data enrichment + provenance bookkeeping (real-vs-synthesized
flag honesty). Both are valid; neither subsumes the other.

---

## Chapter 6: Substrate-Prober Paradigm (added 2026-04-26)

A substrate that is structurally insufficient for the operator's research question is itself
a publishable finding. The gp163d run produced no Newton-step result on RAR universality, but
it did produce a methodological contribution: an exhaustive 17-form symbolic regression search
+ the apparatus's own diagnosis of why no form bridges all three regimes (Class B mass-collapsed,
Class C radius-collapsed, joint-form blockers). This is the substrate-prober paradigm.

The relationship to scientific publication: a stoic null result is a real contribution when
the apparatus has *exhausted* the form space and the diagnosis is precise enough to motivate
substrate enrichment or methodological replacement. The methodological paper (paper7/draft.md,
5113 words) makes this case for gp163d.

**Operational consequence:** When a run caps below threshold AND the apparatus has explored
≥10 form families AND R26 / 2C has produced a structural diagnosis, the result is a *substrate
ceiling finding* — write it up. Do not interpret the cap as apparatus failure or mutator
laziness without first running the meta-audit.
