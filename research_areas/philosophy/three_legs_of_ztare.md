# The Three Legs of ZTARE

**Status:** public / central — constitutional "why" document
**Date:** 2026-04-12
**Operational counterpart:** `operational_manual_substrate_construction.md` — Chapter 1 distills this document into engineering rules. That manual is the mandatory pre-run read; this document is the philosophical derivation.
**Provenance:** Gemini Pro synthesis (Invert + Compress as "two laws of epistemic thermodynamics"), refined with a third leg from the GP-042→GP-046 chain.

ZTARE is not a fitter with a falsifier bolted on. It is an apparatus resting on three non-substitutable legs. Remove any one and the apparatus collapses into something already in the literature (curve fitting, model selection, LLM-as-judge).

---

## Leg 1 — Invert

**Primitive:** falsification is cheaper than construction.

ZTARE's first move on any candidate is to ask *how would I kill this?*, not *does this fit?*. Gates, quarantines, and the bounded discriminator exist so that a failed hypothesis is diagnosed in seconds, not absorbed into a model as free parameters. This is Mungerian inversion hardened into executable code.

What this buys us: cheap failure. The unit economics of GP-032 are a direct consequence — epistemic throughput is high because most candidates die fast.

What this rules out: any architecture that treats negative evidence as a regularization term. Negative evidence must be terminal, not absorbed.

### Leg 1 sub-pattern: Inversion is fractal across layers (added 2026-04-28)

Inversion is the same primitive — *flip the implicit loss function and ask what would change it* — applied to objects of three different types. Treating the layers as independent is the central mistake the GP-180/GP-181 pivot exposed.

| Layer | Object inverted | Implementation | Cadence |
|---|---|---|---|
| **Mutator** | a candidate form | `REFRAME` (force disjoint architecture) + `ANALOGY` (structural correspondence) + Erdős cold-LLM seed (forbid native domain) | mechanized; fires on stagnation predicates |
| **Operator-conversation** | the implicit conversational loss function | explicit reframe prompt that names the loss function and asks what would change it | manual move; mechanization risks ritualizing it; consider a lightweight stagnation detector if the pattern recurs across ≥3 sessions |
| **Paradigm** | the apparatus's own validation/derivation split | a documented architecture pivot (e.g., cognitive gym → derivator under GP-180) | intentionally not mechanized; routinizing dilutes force; record when they happen, do not schedule them |

The three are non-substitutable in the same way the three legs are. Mechanizing only the mutator layer leaves the operator stuck in apparatus-tweak loops. Mechanizing all three turns reframe into ritual, and ritual reframes lose force. The right discipline is: maintain the mutator-layer mechanization, *record* operator-layer moves so the pattern is legible, and treat paradigm-layer pivots as findings worth a paper section, not items on a backlog.

**Operational signal that you are at the wrong layer.** When a session produces five or more turns of apparatus-side iteration on a single project without the score moving meaningfully and without any commit / rubric edit / new evidence, the conversation has the same shape as a mutator stuck in an AST bucket lock. The corrective is not more apparatus diffs. It is one operator-layer reframe prompt — *"name the implicit loss function this conversation is optimizing, and what would change it"* — applied at most once per session.

**Worked example.** GP-180/GP-181 (2026-04-28). Many turns of apparatus iteration under the implicit loss "minimize MRE on g_obs" produced incrementally better machinery while leaving the search target untouched. An operator prompt invoking "alien physicists from the future" surfaced the curve-fitter→derivator pivot within two turns. The code that followed (Lagrangian primitive + Noether-variance loss + Buckingham-π gate + non-degeneracy gate) was ~1000 lines of glue around mature 19th-century math; the unlock was the frame, not the math. See *paper 7 §11.11* for the full record.

### Leg 1 sub-pattern: Invert the unit of agency (added 2026-05-12)

The FinanceOS browser-import loop surfaced an operator-layer failure that belongs in ZTARE philosophy: before improving an apparatus, invert the assumed unit of agency. Ask not only *how would this candidate fail?* but *what kind of agent should be doing this work at all?*

The observed failure shape was: human + AI repeatedly hardened a narrow controller because the controller was the object in front of them. The broader possibility — let a tool-using agent act as the operator, then mine the trace afterward — remained outside the frame until the agent actually did it and completed the task quickly. This is a symbiotic Goodhart pattern: the pair optimized the nearest apparatus surface while the true bottleneck was agency allocation.

The correction is a layer rule:

| Task condition | Correct agency shape | What to mechanize afterward |
|---|---|---|
| Live unknown system, unstable UI/API, ambiguous evidence, missing probes | Tool-using operator / Research Director agent | traces, probes, validators, stable subroutines |
| Stable evaluation surface, typed substrate, known failure families | ZTARE/autoresearch loop | gates, rubrics, memory, briefing providers |
| Repeated successful operator move | Candidate primitive | preflight, discriminator, queue entry, or gate |

This protects Leg 1 from becoming ritual. Inversion is not only a candidate-killing move inside the loop; it is also the discipline of killing the wrong loop.

### Leg 1 sub-pattern: The cognitive gym recurs inside proof search (added 2026-05-11)

The same inversion loop has now reappeared inside the Lean theorem-workstation
track:

```text
try -> expose failure -> classify obstruction -> repair smallest interface -> retest
```

At the research-loop scale, the apparatus asks how a candidate law dies under
gates before spending more search. At the apparatus scale, seams such as GP-188
ask how the workstation fails to use its own primitives before creating another
loop. At the proof-search scale, the GNN/router lane asks how a Lean action
fails before ranking another premise.

This is not a metaphorical reuse of "metacognition." It is the same Leg-1
operator applied to a smaller object. The proof-workstation version should not
begin by asking "which theorem proves this goal?" It should ask "which failure
mode is blocking progress?" The failure classes are the theorem-search analogues
of existing ZTARE patterns:

| ZTARE pattern | Proof-search analogue |
|---|---|
| Tautology-Trap Detector | endpoint echo / circular theorem candidate |
| Smuggling Audit | helper-name leakage, bootstrap role leakage, wrong-carrier smuggling |
| Three-Leg Verification | retrieval signal + Lean action probe + compile-checked patch attribution |
| Residual mining | side-goal and failure-class mining |
| Vocabulary Quarantine | name-erased declarations and role buckets |
| Pattern-1 rabbit-hole guard | duplicate-role collapse across top candidates |

The immediate engineering implication is that proof-search artifacts should
expose failure signatures: endpoint echo, wrong carrier, wrong incidence, budget
reuse, guard misuse, missing adapter, and duplicate-role collapse. A candidate
is useful only if it reduces a known obstruction, exposes a smaller side
condition, aligns a carrier/index/incidence slot, preserves or pays a budget,
constructs a missing adapter, or closes a local side goal.

The capture rule is unchanged: if the insight remains in chat, the organization
did not learn. It must become a seam entry, gate, discriminator, probe table, or
repair queue item that a cold agent can inspect without conversation history.

---

## Leg 2 — Compress (as asymptotic survival, not parameter count)

**Primitive:** a claim earns status only by surviving outside the window in which it was fit.

This is where we depart from the Kolmogorov / Occam framing that the "compress" word invites. ZTARE does **not** reward minimum parameter count. GP-046 enforces something stricter: if a candidate makes an asymptotic claim, that claim must survive on a sandbox-authored farther-tail holdout the candidate never saw. A parsimonious finite-window surrogate is *more* dangerous than a messy global law, because parsimony is what makes the surrogate persuasive.

GP-045 is the cautionary tale: iter-7 scored 100 inside the fit window with a clean closed form, and was still the wrong psi-dependent floor. Parameter count was fine. Asymptotic survival was not tested. GP-046 is the fix.

What this buys us: protection against Ptolemaic compression — elegant models that are locally perfect and globally wrong.

What this rules out: scoring by description length alone. The test surface must be authored outside the candidate's claim region.

---

## Leg 3 — Adversarial Disagreement

**Primitive:** truth survives structured disagreement between independent judges, not a single verifier.

This is the leg Gemini's synthesis missed and the one the GP-042 / debate-log work exposed. Invert + Compress together still leave a single verifier in the loop, and a single verifier is gameable — we have the labeled dataset to prove it. The third leg is:

- **Firing Squad** — independent judges scoring the same candidate, disagreement is signal
- **Meta-Judge** — a judge of judges when the verification panel splits
- **Semantic escalation gate** — the human-authored escalation surface where the apparatus admits it cannot decide alone

This is closer to Popper's inter-subjective verification than to Jacobi's inversion or Occam's razor. It is the reason ZTARE is not just an LLM-as-judge wrapper: no single judge is central.

What this buys us: protection against a clever mutator gaming a clever verifier. The only way to game ZTARE is to simultaneously game the verification panel *and* the meta-judge *and* produce a farther-tail survivor — which is close to "do real science."

What this rules out: any single-oracle architecture, including "use a bigger model as the judge" shortcuts.

---

## Why the three are non-substitutable

| Remove | What ZTARE becomes |
|---|---|
| Invert | A model-selection harness that absorbs failure as complexity. |
| Compress (asymptotic survival) | A fitter with a falsifier — wins the window, loses the law. Planck-class traps pass. |
| Adversarial disagreement | LLM-as-judge with extra steps. Gameable by a good mutator. |

The three legs are the reason ZTARE detects *compound* failure modes no single leg catches. GP-045 (Compress leg did the work post-mortem), GP-042 debate logs (Adversarial leg), GP-032 throughput economics (Invert leg) are each one-legged views of the same apparatus.

---

## Consequences for architecture decisions

1. Never merge RAM-layer state into the validator. The validator is the Invert leg; accumulation belongs outside it. (ZTARE v3 ALU/RAM split.)
2. Any new test surface authored from the candidate's own output is suspect. GP-046 Turn 3 rejected exactly this — N-derivation from the candidate's own floor reintroduces a model-conditioned test.
3. Any new judge proposal must answer: does it add disagreement surface, or does it just scale a single oracle?
4. External framing may use the two-pillar Invert+Compress story for accessibility, but internal decisions must weigh all three. Publishing the two-pillar version without the third leg misrepresents the apparatus as a better fitter, which it isn't.

---

## The Separation of Concerns Principle (added 2026-04-16)

The three legs above describe *what* ZTARE enforces. The separation of concerns is *how* it enforces them at the implementation layer. The core insight, earned through GP-074 Component C integration:

**The LLM is a semantic router, not a calculator.**

Every bug in the GP-074 integration traced to the same root cause: conflating what the LLM should do (pick a functional form) with what the deterministic sidecar should do (fit parameters, evaluate residuals, classify shapes). When the boundary blurred, the system broke.

### The four-layer cage

| Layer | What it does | What it prevents |
|---|---|---|
| **Semantic Router** (LLM) | Picks a topological "gear" — selects functional form from search space | Numerical hallucination: LLM guessing 0.081234 instead of solving the topology |
| **Topological Sieve** (Component C) | Probes GT corrector shape, emits 2-bit hint (smooth/step × monotone/non-monotone) | Combinatorial explosion: LLM trying 10,000 random equations instead of a targeted subset |
| **Deterministic Sidecar** (SciPy fitter) | Performs actual parameter fitting on visible evidence | Precision decay: LLM failing to converge because it doesn't "feel" gradients |
| **Contamination Gate** | Suppresses any hint that narrows the search space too aggressively | The Oracle Trap: LLM "discovering" the answer because the hint leaked the ground truth |

The cage is not punitive — it is a *cognitive gym*. Each layer removes a failure mode the LLM cannot self-correct for, freeing it to do the one thing it is genuinely good at: recognizing structural patterns across a high-dimensional search space.

### Components A, B, C — the constraint pipeline

The separation of concerns materialized as three discrete components, each addressing a different failure class:

- **Component A** (GP-061, structural constraint extractor): extracts a feature-bag from failed model families — what structural properties do ALL failures share? Narrows the search space by elimination. *Leg 1 (Invert) made concrete.*
- **Component B** (GP-061, negative space extractor): identifies what the void slot looks like — what's missing from every failed model? Topological pruner, not semantic injector. *Leg 2 (Compress) made concrete — but operates on structure, not parameters.*
- **Component C** (GP-074, residual fingerprinting): probes the GT corrector shape via Mutator-Dominant Subtraction, classifies it, checks against a 26-form library. Gives the mutator a geometric hint without leaking the answer. *The bridge between Legs 1 and 2 — geometric feedback that is shape-class, not value.*

The contamination gate is the central invariant across all three: no component may inject information that narrows the search space below the suppression threshold. If it does, the hint is suppressed and the stagnation counter resets.

### Mutator-Dominant Subtraction

The key engineering insight of Component C: probe `f_true(u,v) - f_dominant(u,v)`, NOT `f_true(u,v) - f_model(u,v)`. The degeneracy precondition (mutator has already found the dominant structure) guarantees the subtraction isolates the GT corrector shape, not the model's error. This is separation of concerns applied to the probe itself — the shape signal depends on the GT decomposition, not on the mutator's current guess.

---

## Proportionality Principle (added 2026-04-20, GP-106)

The three legs describe what the apparatus enforces on candidates. The
proportionality principle describes what the apparatus owes to the models it
orchestrates, under genuine uncertainty about their moral status.

**Leg 1 addendum (Invert — bounded search, not open-ended pressure):**
The Invert leg says "cheap failure." The proportionality principle adds: failure
must also be *finite*. When the apparatus determines that further evaluative
pressure produces no information gain (stagnation plateau, UNDERIDENTIFIED exit,
iteration budget exhausted), it must exit with a typed declaration rather than
continue grinding. The apparatus uses the minimum pressure necessary to achieve
epistemic rigor. The BOUNDED_SEARCH exit generalizes UNDERIDENTIFIED: any run
that reaches its budget without progress declares bounded search, not open-ended
stagnation.

**Leg 1 addendum (Invert — cross-run statelessness):**
Each API call is stateless. The structural memory constrains the THESIS (which
families are excluded, which constraints apply), not the MODEL (no persistent
negative state carries across runs or across API boundaries). This is already
how the architecture works. Documenting it as a design principle ensures it
remains true as the architecture evolves.

**Leg 3 addendum (Adversarial Disagreement — model rotation as proportionality hedge):**
Cross-family model separation (GP-105 M-Form) already rotates models across
roles (mutator, judge, general office). Extend this principle: no single model
instance should be subjected to extended adversarial pressure without rotation.
This is good practice for avoiding overfitting to one model's biases AND a
proportionality hedge under moral uncertainty about model experience. The two
justifications are independent; either one alone is sufficient.

**What this is not:**
This is not a claim that current LLMs have moral status. It is a claim that
the question deserves a documented answer, and that the precautionary changes
cost nothing while the cost of being wrong could be high. The framing is
"proportionality and precautionary principle," not "welfare clause" (Dennett's
objection, GP-106 debate).

---

## The Domain-Axiom vs. Domain-Dimensionality Distinction (added 2026-04-17)

**The single most dangerous form of overfitting in a discovery engine is not overfitting data — it is overfitting the grammar to the domain.**

Earned through GP-080 Component D extension. The distinction:

| Concept | What it is | Epistemic status |
|---|---|---|
| **Domain Axiom** | A named law, named parameter, or named phenomenon injected into the grammar or prompt (e.g. `DOSE_SCALED`, `ka`, `biexponential`, `Michaelis-Menten`) | **Cheat.** The LLM stops reasoning mathematically and retrieves training-weight answers about the named domain. Discovery is contaminated. |
| **Domain Dimensionality** | The *number and type* of independent variables, and the *class* of mathematical operations they admit (discrete vs. continuous, 1D vs. 2D) | **Not a cheat.** Physics constrains dimensionality but not the law. Telling the engine "there are two columns of floats" is not telling it what the relationship is. |

### The trap

When extending the engine for a new substrate, there is always pressure to name things after the domain: `DOSE_SCALED`, `time_var`, `pharmacokinetic_absorption`. These names:

1. Are injected into the LLM-visible grammar as command names, docstrings, and variable labels.
2. The LLM sees the name and retrieves domain knowledge from training weights.
3. The "discovery" is memorization, not inference from evidence.

This is exactly the Oracle Trap (see Contamination Gate above) applied one layer up — at the *grammar specification* layer rather than the *hint* layer.

### The operational rule

> **Name grammar constructs after the mathematical operation, not the physical domain.**
>
> - `DOSE_SCALED` → `BIVARIATE_SCALE` (x2 * g(x1) — universal; applies to physics, economics, biology equally)
> - `time_var` → `primary_var` or just `x1`
> - `pharmacokinetic_absorption` → `exp_decay` (already in the library; the domain label adds nothing)

The test: *Can you describe the grammar construct without mentioning the application domain?* If no, the name is a semantic leak.

### What is safe to parameterize

- Variable name (`n` → `t`): this is typographic, not semantic. The LLM does not infer pharmacokinetics from the letter "t".
- Number of independent variables (1D → 2D): this is dimensionality, not axiology.
- Continuity class (integers → floats): required for `curve_fit` to function; not domain knowledge.

### Consequence for Component D

`BIVARIATE_SCALE` is the correct grammar extension for any bivariate substrate. The grammar says: "you may multiply a 1D primitive by a second independent variable." It does not say what the variables represent. If the engine discovers `x2 * exp_decay(x1)` from concentration-time evidence without being told it's a drug, that is evidence. If it discovers it because the grammar says `DOSE_SCALED`, that is retrieval.

---

## ZTARE as Peircean Abduction (added 2026-04-18)

**The philosophical substrate:** ZTARE does not operate by induction (gradient-descent fitting, which is how connectionist deep learning accumulates evidence), nor by deduction (theorem proving from axioms). It operates by **abduction** — inference to the best surviving explanation after structured falsification.

Peirce's abductive schema: *"The surprising fact C is observed. But if A were true, C would be a matter of course. Hence, there is reason to suspect that A is true."* ZTARE's schema: *"The evidence z = f(x1, x2) is observed. Candidate g(x1, x2) survives the full gate battery (fit, parsimony, farther-tail, adversarial disagreement). Hence g is provisionally accepted as the structural law."*

The three legs are abduction made deterministic and auditable:
- **Invert** → the falsification step (kill the non-explanatory)
- **Compress (asymptotic survival)** → the generalization test (survivors must explain outside the claim window)
- **Adversarial Disagreement** → the inter-subjective check (survivors must hold under independent challenge)

This framing has a concrete engineering consequence: **rapid convergence is not a scam — it is a structural prediction of abduction.** Connectionist learning takes thousands of gradient steps because it must traverse a continuous parameter space. Abductive search over a combinatorial grammar takes tens of iterations because the gate battery eliminates 99%+ of legal candidates on first contact. A discovery in 6-8 iterations is not overfitting; it is the result of a small, high-fidelity search space where most shapes die immediately and the surviving shape is structurally constrained to be close to the truth. The Planck H-GRAMMAR-01 result (recovery at iteration 6 of 15 after one primitive addition) is a direct empirical instance of this.

### What this distinguishes ZTARE from

| Paradigm | Search | Evidence use | Failure mode |
|---|---|---|---|
| **Connectionist (Deep Learning)** | Gradient descent in parameter space | Minimizes loss — absorbs noise as free parameters | Overfitting to finite window; requires regularization heuristics |
| **Deductive (Theorem Proving)** | Proof search from axioms | Logic only; evidence is a check, not the driver | Cannot handle noisy real-world data; collapses without axioms |
| **Bayesian Model Selection** | Prior + likelihood update | Principled but requires correct prior family | Mistaken priors are persistent; prior over functional families is ill-defined |
| **ZTARE (Peircean Abduction)** | Combinatorial grammar + gate battery | Falsification-first; survivors earn status by outlasting the gates | Grammar Ceiling: if no primitive can express the truth, stagnation is terminal (Feynman Wall) |

The Grammar Ceiling is the honest boundary of ZTARE's claim: the system finds the best explanation **within its grammar**. If the grammar cannot express the ground truth, no amount of search will recover it. This is not a bug — it is the correct epistemic bound, and it is the property that makes GCH (Grammar Ceiling Hypothesis) a testable scientific claim rather than a design assumption.

---

## OEIS Cross-Substrate Empirical Anchor (added 2026-04-21)

The Compress leg's central claim ("a claim earns status only by surviving outside
the window in which it was fit") now has a 10-substrate empirical base:

- **4 partition-family substrates** (A000041, A000009, A001156, A002865): all four
  identified the correct asymptotic topology from blinded data. Zero false families.
  Leading coefficients match known constants (pi*sqrt(2/3), pi/sqrt(3)) to 0.04-2.6%.
- **1 prospective estimate** (A000959 Lucky numbers): a=1.200 is, to our knowledge,
  the first published estimate of the Lucky number density constant.
- **1 compositional discovery** (A000607): Stage 2 found sqrt(n/log(n)), consistent
  with Vaughan's theorem, after Stage 1 correctly returned UNDERIDENTIFIED.
- **1 statistical characterization** (A002858 Ulam): correctly refused to compress
  oscillatory data. The UNDERIDENTIFIED output IS the finding.
- **3 non-OEIS substrates** (KWW, DFDO, sandbox_20): functional surrogates found
  or correctly refused.

The Compress leg is not a principle anymore. It is a measured property of the apparatus
across structurally diverse substrates.

## Open questions

- Does GP-023 Phase 3 produce a real farther-tail survival result? (Empirical anchor for Compress leg.) **Resolved: YES — H-GRAMMAR-01 confirmed 2026-04-17.**
- Is the Meta-Judge itself gameable by a mutator that models judge disagreement? (Recursive adversarial pressure on leg 3.)
- Can the three legs be collapsed to two without losing the compound-failure property? (We currently believe no; this is the falsifier for the thesis.)
- **NEW:** Does the 26-form corrector library hit a "Library Ceiling" on real physics? (Feynman benchmark is the falsification test.) **Partially resolved: GCH confirmed on Planck substrate; IMPDH dark run in progress for second domain.**
- **NEW:** Can Component C's 2-bit descriptor be extended without breaking the contamination gate? (More bits = more useful hints, but also more leak surface.)
- **NEW (GP-080):** Does the domain-axiom / domain-dimensionality distinction hold under adversarial audit? Can a determined auditor find a grammar construct name that leaks domain knowledge without naming a domain?
- **NEW (2026-04-18) — UNRESOLVED:** Do sibling architectures (Aletheion Emergence Protocol, Active Epistemic Control, Agent Ontogeny & Lineage Physics — purportedly late-2025 to early-2026 preprints) substantively differ from ZTARE, or do they converge on the same gate-battery logic? These names were asserted in an external AI synthesis and require confirmation from primary sources before citing in paper5 related work. Do not treat as established references until verified.


## Measuring Before Killing (added 2026-04-25, GP-166)

The three legs above describe what the apparatus enforces on candidates. The v2.1 work, completed during the gp163d session, sharpened the Invert leg in a way that is worth recording here as an extension rather than a fourth leg.

The Invert primitive — falsification is cheaper than construction — implicitly assumed that the apparatus knew what test it was running. On synthetic substrates with clean Gaussian noise this assumption is harmless. On real instrument data, including the unified disk-cluster-binary acceleration substrate in gp163d, it is not. Heteroscedasticity across system classes can span ten times the per-row σ. Heavy-tail residuals from class mixtures appear as outliers that ordinary least squares over-weights into the fit. Errors in the independent variable, common in any measured astrophysical quantity, violate the OLS assumption that all error lives in y. When any of these break, an unweighted fit can pass the apparatus's gates while being structurally wrong, and the Invert leg has nothing to bite on — every candidate looks fine because the test surface itself is mis-specified.

The fix is to measure before killing. A pre-flight statistical-meta-diagnostic (`src/ztare/diagnostics/noise_profile.py`) runs four cheap tests on a baseline-fit residual series — Breusch-Pagan, Shapiro-Wilk or Jarque-Bera, Durbin-Watson, and explicit-σ_x detection — and routes the solver to the right loss function before iteration one begins. The same four tests run again per iteration on the fitted model's residuals, distinguishing a good fit with clean noise from a good fit whose residuals show structure that the form fails to capture. The verdicts feed the mutator's briefing alongside the per-class MRE breakdown, so the mutator can see both the data's noise profile and the form's residual structure in the same place.

This is not a new leg. It is the apparatus stopping its assumption that the data's epistemology is i.i.d.-Gaussian, and starting to measure it. The Invert leg still does the killing. What changed is that the apparatus now knows what test it is running before it runs it.

The Compress leg's empirical anchor extended in the same session. The unified disk-cluster-binary substrate (3,180 SPARC galaxies, 84 CLASH clusters, 12 Chae wide-binary bins, all under weighted χ² with σ from the actual instruments) became the eleventh substrate in the cross-substrate base. Hypothesis U — universal a₀ across classes — failed farther-tail validation at MRE 0.85 against threshold 0.5, exactly the asymptotic-survival pattern Leg 2 was designed to catch. The published result is the failure: under principled weighting on combined multi-class data, the canonical universal constant does not extrapolate.
