# ZTARE operational manual for substrate construction

**Status:** public — read before adding any substrate, grammar construct, or pipeline component
**Philosophical counterpart:** [three_legs_of_ztare.md](three_legs_of_ztare.md) explains why these rules exist. This manual explains how to avoid breaking them; the legs are permanent, and the manual changes whenever a new failure mode is earned.
**Provenance:** distilled from the seam record, [GP-027](../seams/apparatus/instrumentation/GP-027_evidence_compile_reuse_seam.md) through [GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) and later.

---

## Chapter 1: the three legs, stated operationally

Distilled from [three_legs_of_ztare.md](three_legs_of_ztare.md). Read that document for the full derivation.

ZTARE stands on three load-bearing commitments. Take any single one away and what remains already exists in the literature under another name: curve fitting, model selection, or LLM-as-judge.

### Leg 1 — inversion

Falsification is cheaper than construction. Faced with any candidate, the apparatus first asks how it would die, then how well it fits. Gates, quarantines, and the bounded discriminator exist so that a failed hypothesis is diagnosed in seconds.

Operational consequence: accumulated state stays out of the validator. The validator is the inversion leg, and memory belongs elsewhere. Negative evidence must stay terminal. An architecture that absorbs failures back into the model as free parameters has quietly turned its falsifier into a regularizer.

### Leg 2 — compression, meaning out-of-window survival

A claim earns status by surviving outside the window in which it was fit. ZTARE does not reward small parameter counts. When a candidate makes an asymptotic claim, [GP-046](../seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md) requires it to hold on a farther-tail holdout that the sandbox authored and the candidate never saw. A parsimonious finite-window surrogate is more dangerous than a messy global law, because parsimony persuades.

Operational consequence: the holdout must be authored outside the candidate's claim region. A test surface derived from the candidate's own output is contaminated by construction.

### Leg 3 — adversarial disagreement

Legs 1 and 2 still leave a single verifier in the loop, and a single verifier is gameable. The third leg replaces the oracle with structured disagreement:

- a review committee of independent judges scoring the same candidate, where disagreement is treated as signal
- a meta-judge that adjudicates when the panel splits
- a human escalation surface, which is the apparatus admitting it cannot decide alone.

Operational consequence: every proposed judge must answer one question: does it add disagreement surface, or does it scale a single oracle? A bigger model as the judge is oracle scaling, and it is not leg 3.

| Remove | What ZTARE becomes |
|---|---|
| Inversion | A model-selection harness that absorbs failure as complexity |
| Compression as survival | A fitter with a falsifier: wins the window, loses the law |
| Adversarial disagreement | LLM-as-judge with extra steps, gameable by a good mutator |

---

## Chapter 2: the cognitive gym

Distilled from the [cognitive gym essay](../../docs/concepts/cognitive_gym.md); the arrangement is implemented in [cognitive_gym.py](../../src/ztare/common/cognitive_gym.py).

An LLM inside a constrained validation loop produces better science than the same LLM unconstrained. Each deterministic layer removes a failure mode the model cannot self-correct, which frees it to propose ambitious functional forms across a large search space. The division of labor: the language model routes semantics, and deterministic code does the arithmetic.

### The layers

| Layer | Owner | Does | Does not |
|---|---|---|---|
| Semantic routing | LLM | picks a functional form from the grammar | compute coefficients |
| Residual probe | deterministic code + the [corrector library](../../src/ztare/gates/corrector_library.py) | classifies the residual's shape and emits a coarse geometric hint | select the form |
| Deterministic sidecar | SciPy `curve_fit` | fits parameter values to visible evidence | search function space |
| Contamination gate | code, backed by the [prompt-leak audit](../../src/ztare/gates/prompt_leak_audit.py) | suppresses hints that narrow the candidate space below the suppression threshold | inject information |

Two extractors mine the failure record between iterations. The [structural constraint extractor](../../src/ztare/gates/structural_constraint_extractor.py) intersects the mathematical skeletons of failed families and emits what every failure shared. The [negative-space extractor](../../src/ztare/gates/negative_space_extractor.py) surfaces the moves present in the candidate universe that no failed family ever tried. Both write constraints into the same delivery channel, and both are subject to the contamination gate.

### Separation of concerns

When these boundaries blur, the system breaks. Every integration bug in [GP-074](../seams/substrates/selkov/GP-074_component_c_residual_fingerprinting_seam.md) traced to a boundary violation:

| Concern | Owner | Not the owner |
|---|---|---|
| "What family of functions might fit?" | LLM | SciPy, residual probe |
| "What are the optimal parameter values?" | SciPy | LLM |
| "What shape is the residual?" | residual probe | LLM |
| "Is this hint safe to inject?" | contamination gate | LLM, operator |
| "Does this formula generalize?" | holdout gate (deterministic) | LLM, judge |

### How each layer was earned

Each layer exists because the previous configuration hit a specific failure mode:

| Seam | Failure mode | Layer added |
|---|---|---|
| [GP-027](../seams/apparatus/instrumentation/GP-027_evidence_compile_reuse_seam.md) | numerical hallucination (the LLM guessing coefficients) | deterministic sidecar |
| [GP-035](../seams/engine/grammar/GP-035_mutator_missing_fit_primitive_seam.md) | combinatorial explosion (thousands of random forms) | structural constraint extractor and negative-space extractor |
| [GP-061](../seams/apparatus/supervisor/GP-061_R4_retrospective_audit.md) | null result on Selkov, search space too large | negative-space extractor |
| [GP-074](../seams/substrates/selkov/GP-074_component_c_residual_fingerprinting_seam.md) | the LLM could not characterize residual shape | residual fingerprinting against the corrector library |
| [GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) | grammar semantic leak (`DOSE_SCALED` named the domain) | contamination gate at the grammar layer |

None of this dumbs the model down. With arithmetic removed, the model stops hallucinating precision and proposes bolder topologies. The contamination gate keeps the search alive when a hint would have leaked the answer, and the corrector library gives the model's structural intuition a tested vocabulary to land on.

---

## Chapter 3: hard rules for substrate construction

Every time a new substrate is added to ZTARE, there is pressure to name things after the domain, inject domain knowledge into the grammar, or shorten the contamination gate just this once. Each of these moves destroys the epistemic validity of the run without leaving a visible error: the engine still runs and the score still rises, but the discovery claim is hollow. This chapter collects the anti-patterns we have paid for in lost iterations and invalid results.

### Rule 1: name the math, not the physics

When extending the grammar (the `CompositionCommand` enum in [symbolic_regression_synthesizer.py](../../src/ztare/composition/symbolic_regression_synthesizer.py), rubric penalty lists, prompt templates), do not name constructs after the physical domain under test. The LLM sees the command name in its prompt. A domain name activates training-weight retrieval, and the mutator stops reasoning from residuals and starts retrieving "pharmacokinetics" or "quantum mechanics" from memory, which turns the discovery into memorization.

| Wrong (semantic leak) | Correct (math op) |
|---|---|
| `DOSE_SCALED` | `BIVARIATE_SCALE` |
| `SCHRODINGER_DECAY` | `COMPOSE(exp_decay, sinusoid)` |
| `PHARMACOKINETIC_ABSORPTION` | `exp_decay` (already in the library) |
| `ECONOMIC_MULTIPLIER` | `BIVARIATE_SCALE` |
| `time_var`, `dose_var` | `primary_var`, `scale_var` (or just `x1`, `x2`) |

Test before committing: read every new grammar construct name aloud without context, and if you cannot describe what it does without naming the application domain, rename it. The canonical fix is `DOSE_SCALED → BIVARIATE_SCALE` ([GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md)).

### Rule 2: the LLM proposes structure, never numbers

Do not prompt the LLM to propose or refine numerical parameter values. LLMs hallucinate precision, and asking "what is the value of ke?" invites a confident fabrication. Under the layer contract in chapter 2, the LLM output must be a structural choice (a command plus operand labels), never a numerical claim. All parameter estimation belongs to the deterministic sidecar.

Operational check: read the LLM prompt and find every number the LLM is asked to produce. If any of those numbers will be used directly as parameter values, rewrite the prompt to ask for structure only.

### Rule 3: variable renames are typographic, never semantic

Two changes look similar and are not:

- `n → t` is typographic and safe. The letter `t` does not tell the LLM what `t` represents, and the variable becomes a continuous float, which `curve_fit` needs to run without crashing.
- Naming the variable `time_hours_post_dose` is semantic and unsafe, because the LLM infers the domain. Rename it to `x1`.

Variable names in Division B artifacts (evidence.txt, charter, rubric) must be opaque: `x1`, `x2`, or single letters without domain meaning. Division A artifacts (GT script, holdout, denylist) may use domain names internally, since Division B never reads them. [generate_substrate.py](../../src/ztare/scaffold/generate_substrate.py) with `--variables x1,x2` is the correct invocation for bivariate substrates.

Corollary on dimensionality: telling the engine there are two columns of floats constrains the mathematics without naming the law. Telling the engine the second column represents an administered dose is oracle knowledge. The number and type of independent variables is physics. What they represent is the answer.

### Rule 4: the contamination gate is non-negotiable

Do not weaken or bypass the contamination gate because "it's just a hint." The gate is what separates ZTARE from "give the LLM more signal." Any hint that narrows the search space below the suppression threshold converts discovery into retrieval, even a true and well-intentioned hint.

One test decides, taken from the [corrector library](../../src/ztare/gates/corrector_library.py) spec: if the hint were given directly to a competent expert, would it let them identify the ground-truth functional form without seeing the data? If yes, suppress it.

Corollary on rubric penalty lists: penalties for specific named models ("penalty: proposes Michaelis-Menten by name") are fine, since they prevent name-retrieval gaming. Penalties for mathematical structures ("penalty: uses any exponential") are contamination, because they artificially narrow the search space.

### Rule 5: the GT script is Division A, always

Do not put any ground-truth information (parameters, functional form, derivation) in Division B artifacts. The Division A / Division B boundary comes from the [GP-072](../seams/protocol/GP-072_role_separation_sandbox_construction_seam.md) protocol:

| Artifact | Division | What it may contain |
|---|---|---|
| GT script (`*_gt.py`) | A | parameters, formula, evidence grid, f_true, f_dominant |
| Evidence holdout | A | held-out (x1, x2, z) triples |
| Denylist | A | GT-specific vocabulary |
| Evidence visible | B | (x1, x2, z) triples, opaque variable names, no domain context |
| Charter | B | neutral problem statement: "find a law governing z(x1, x2)" |
| Thesis seed | B | empty axioms or a single neutral sentence |
| Rubric | B | scoring criteria, no GT form, no named parameters |
| Gate harness | B | evaluates predicted vs. observed, no formula |

A [leak sentinel](../../src/ztare/validator/leak_sentinel.py) enforces this mechanically, but it only catches denylist vocabulary. It does not catch implicit leaks, such as a charter that says "the law has two phases." Human review of Division B artifacts is required before `make seal`.

### Rule 6: `make seal` runs before the loop, never after

`thesis.md` accumulates the mutator's discovered hypotheses across iterations. By iteration 3 it will contain whatever structure the mutator found, including denylist terms if the engine correctly identified the ground truth. Running the sentinel post-loop will always produce hits, and those hits are evidence the engine converged. The seal attests to the state of the sandbox at construction time. Run `make seal PROJECT=... RUBRIC=...` immediately after `generate_substrate.py`, before any loop invocation.

### Rule 7: stage 1 is apparatus validation, not discovery

Do not publish stage 1 (synthetic data) results as evidence that the engine discovered a law. Synthetic data is generated by the law the engine is trying to find, so the data surface is perfectly shaped for the answer. If the engine finds `exp_decay + exp_decay` on biexponential synthetic data, that is standard nonlinear regression.

Stage 1 claims: infrastructure works, `curve_fit` handles continuous floats, variable substitution is correct. Stage 1 does not claim the engine discovered the law, that the law is novel, or that the result generalizes. Stage 2, real data with structural noise, is required for discovery claims. Log stage 1 results as `apparatus_verified` and keep them out of any publication or ledger entry that uses discovery language.

### Substrate construction checklist

Before running `generate_substrate.py` for any new substrate:

- [ ] Grammar constructs named after math ops, not the domain (Rule 1)
- [ ] LLM prompts ask for structure, not numerical values (Rule 2)
- [ ] Division B variable names opaque (`x1`, `x2`, not domain terms) (Rule 3)
- [ ] Division A/B boundary drawn: GT script, holdout, denylist all in Division A (Rule 5)
- [ ] Charter contains no functional-form hints, only "find a law governing z(x1, x2)" (Rule 5)
- [ ] Rubric penalties target named models, not mathematical structures (Rule 4)
- [ ] `make seal` planned for immediately post-generation, before any loop (Rule 6)
- [ ] Stage 1 / stage 2 scope documented in the seam if synthetic data is used (Rule 7)

---

## Chapter 4: plateau diagnosis, evidence versus grammar

Distilled from the crucial-experiment sequence in [GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) through [GP-083](../seams/mission/treatise/GP-083_inference_type_boundary_seam.md).

When the engine plateaus (stagnation at a high-scoring champion that fails the farther-tail discriminator), the bottleneck is in one of two places:

1. Evidence: the data grid cannot discriminate the champion from the true form, and the engine found the simplest survivor consistent with the visible window, which is correct empirical behavior.
2. Grammar: the engine's AST vocabulary cannot express the true form even where the data would discriminate it, so the mutator has hit its grammar ceiling.

These are independently testable and must be tested independently. A confounded experiment (enriched data plus a grammar patch at the same time) cannot distinguish which intervention was central.

### Two candidate mechanisms for structural rejection

Rejecting a high-scoring empirical fit on structural grounds admits two competing answers.

One answer is formal verification: build a deductive proof engine (Lean/Coq) that receives axioms and attempts to derive the champion form, rejecting the champion when the proof fails. This fails because the axiom selection problem is the eigenquestion selection problem. If the operator feeds `E=hv` into the prover, the operator has already done the discovery; the prover confirms without discovering, and the ground truth has leaked through the axiom channel ([GP-083](../seams/mission/treatise/GP-083_inference_type_boundary_seam.md)).

Its rival is evidence-grid design: compute where the champion and its nearest structural rival diverge most, and propose the next measurement there. This is architecturally consistent, a typed, stateless, deterministic operation like the other gates, and it extends the farther-tail gate from a static discriminator to a dynamic one.

Evidence-grid design solves the necessary condition, that the engine must see discriminating data. It does not guarantee the sufficient condition, that the grammar can express the true form. Both conditions must hold, and each can be tested for a few dollars, so test them sequentially, cheapest first.

### Rule 8: test evidence before grammar

Do not respond to a plateau by immediately extending the grammar with new primitives, composition modes, or series-expansion rules. Grammar extensions are Lakatosian auxiliary hypotheses. Each one weakens the claim that the same grammar works across domains, and a grammar quietly patched before testing whether data alone would suffice both confounds the experiment and adds an epicycle the programme must now defend.

| Stage | Intervention | Expected outcome | What it proves |
|---|---|---|---|
| 3a | Add discriminating data to visible evidence, same grammar | Champion falsified. Engine either finds the true form (data was the bottleneck) or stagnates at the grammar ceiling | Resolves the evidence-vs-grammar ambiguity |
| 3b | If 3a fails: add one targeted grammar primitive (e.g., two-term composition), same enriched data | Engine finds the true form with the extension | Grammar was the sufficient condition; data was necessary but not sufficient |
| 3c | If 3b fails: add a structural primitive (e.g., truncated series expansion), same enriched data | Engine finds the true form via bottom-up series stacking | The true form requires a different construction mode |

Running all three stages costs a few dollars in API calls, where a proof-assistant integration costs months. Run the cheap experiments first; each failure is a clean architectural finding.

One known constraint: the mutator's token-probability distribution is biased toward epicycles (polynomial patches, log adjustments) over large topological restructuring, such as moving a subtraction inside a denominator. Stage 3a will likely produce epicycles before restructuring and may stagnate without finding the true form, an outcome that is expected and informative. The failure signature at 3a is what makes 3b a controlled experiment instead of a premature grammar patch.

In general, either insufficient evidence or insufficient grammar is individually sufficient to block discovery, and they are not interchangeable fixes. Test evidence first: it is cheaper, preserves the programme's status, and produces a clean failure signature when the grammar is the bottleneck.

---

## Canonical anti-pattern register

| ID | Name | First observed | Rule violated | Fix |
|---|---|---|---|---|
| AP-001 | `DOSE_SCALED` semantic leak | [GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) | Rule 1 | renamed `BIVARIATE_SCALE` |
| AP-002 | Post-loop sentinel | [GP-078](../seams/engine/grammar/GP-078_component_d_topology_synthesizer_seam.md) | Rule 6 | seal before loop |
| AP-003 | Charter GT derivation | [GP-072](../seams/protocol/GP-072_role_separation_sandbox_construction_seam.md) | Rule 5 | charter is Division B, no formulas |
| AP-004 | `int()` cast on continuous GT | [GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) | Rule 3 | `generate_substrate.py` continuous mode |
| AP-005 | Stage 1 overclaim | [GP-080](../seams/substrates/tacrolimus/GP-080_tacrolimus_pk_seam.md) | Rule 7 | two-stage strategy; stage 1 = `apparatus_verified` |
| AP-006 | Within-withheld-class feature collapse | gp163d v2 backtest | Rule 9 | R26 cross-class feature-support check + per-system enrichment |
| AP-007 | Vacuum gate verdicts (form_str-key bug) | gp154 audit | Rule 10 | suppress the write when the gate refused upstream; surfaced by the gate-effectiveness audit |

---

## Chapter 5: cross-class feature discipline

A substrate can pass every per-class validity check (Rules 1 through 8) and still be structurally insufficient to support the discovery the operator believes it is asking for. Two real runs capped below the Newton-step threshold for the same underlying reason, one invisible to the per-class diagnostics the [substrate critic](../../src/ztare/diagnostics/substrate_critic.py) ran with at the time.

### Rule 9: within-withheld-class feature support

For every (withheld_class, feature) pair the substrate exposes, the within-class span on that feature must be non-trivial: at minimum a 0.5 dex relative range, ideally matching the visible class's span. A withheld class collapsed to a single feature value cannot be discriminated within-class by any closed-form law that uses that feature as a bridge axis, and joint forms across multiple features fail when two or more withheld classes are each collapsed on different features.

Run the R26 cross-class feature-support check (G-CROSS-CLASS-FEATURE-SUPPORT in the [substrate critic](../../src/ztare/diagnostics/substrate_critic.py)) before any 3-class substrate goes live. If R26 flags a `cross_class_joint_form_blocker`, the substrate cannot honestly support cross-class discovery via joint forms. Either enrich it with per-system data through the evidence-gap-enrichment workflow, or formally abstain on the affected class via `r11_excluded_classes` / `honest_null_rows()`. Do not run the apparatus against a structurally insufficient substrate.

We first observed this pattern on gp163d: one withheld class collapsed on mass, another on radius, so no joint(mass, radius) form had within-class degrees of freedom for either, and an exhaustive form search could not clear the cross-class error threshold. The fix was per-system literature data for both classes, with the remaining synthesized column flagged as such (provenance in `projects/gp163d_unified_accel/CHANGELOG.md`).

### Rule 10: meta-gate cadence

Four meta-gates detect the apparatus's own blind spots. Run them on the schedule their cost structure dictates:

| Gate | When | Default | Why |
|---|---|---|---|
| [Static scope linter](../../scripts/public/audits/audit_gate_coverage.py) | pre-commit hook on changes to `src/ztare/{diagnostics,gates,orchestrator}/` | always on (~50 ms) | catches scope-narrowing in diagnostic primitives at write time |
| [Gate-effectiveness audit](../../scripts/public/audits/audit_gate_effectiveness.py) | weekly, or after any gate-dispatcher edit | always on (~5 s, no LLM) | mines run logs for gates that engage but never flag, the fingerprint of AP-007 |
| [Post-run meta-audit](../../src/ztare/orchestrator/post_run_meta_audit.py) | end of every capped run, opt-in via `enable_post_run_meta_audit: true` | off (~$0.005, ~6 s) | an LLM identifies which gate would have moved the score, with scope-extension suggestions |
| [Evidence-gap enrichment](../../src/ztare/orchestrator/evidence_gap_enrichment.py) | pre-iteration-1 when R26 flagged a collapse, opt-in via `enable_evidence_gap_enrichment_proposals: true` | off (~$0.05, ~30 s) | proposes literature sources to fill substrate feature gaps, actioned by the operator |

Both audits should be on for every developer. The two LLM-backed gates are opt-in per substrate to control cost, and production (paper-grade) runs should set both flags true so every capped run leaves a structured audit and an enrichment proposal.

### Rule 10a: two improvement loops

ZTARE has two improvement loops, and the recurring meta-failure this chapter exists to prevent is acting on the wrong one:

- Apparatus loop: cage gates, AST-distance enforcement, anti-laundering rules, score caps, the scope linter, the effectiveness audit. Tools the apparatus uses to improve itself.
- Substrate loop: the R26 feature-support check, enrichment proposals, the operator-actioned enrichment workflow. Tools the apparatus uses to propose substrate improvements.

When a run caps below the Newton-step threshold, the post-run meta-audit decides which loop to act on. A cap due to apparatus gaps ("R10 didn't engage") calls for an apparatus-side fix, typically a small code change. A cap due to substrate gaps ("class B has a collapsed mass axis") calls for a substrate-side fix, typically per-system data enrichment plus provenance bookkeeping (honest real-vs-synthesized flags). Classify every meta-audit recommendation as one or the other before acting. Both are valid, and neither subsumes the other.

---

## Chapter 6: a structurally insufficient substrate is a finding

A substrate that cannot support the operator's research question is itself a publishable result, provided the diagnosis is precise. The gp163d run produced no discovery on RAR universality, but it did produce a methodological contribution: an exhaustive symbolic-regression search across the form space plus the apparatus's own diagnosis of why no form bridges all three regimes. A null result is a real contribution when the apparatus has exhausted the form space and the diagnosis is sharp enough to motivate substrate enrichment or methodological replacement.

Operational consequence: when a run caps below threshold, the apparatus has explored ten or more form families, and the R26 check or the post-run meta-audit has produced a structural diagnosis, the result is a substrate ceiling finding: write it up. Do not interpret the cap as apparatus failure or mutator laziness without first running the meta-audit.
