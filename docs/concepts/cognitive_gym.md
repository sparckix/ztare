---
description: "How ZTARE separates LLM proposal from deterministic fitting, gates, and evidence-bearing verdicts."
---

# Constrained Validation Loop

> **Up:** [Documentation map](../README.md)

**Status:** public / core
**Paper parent:** *Epistemic Verification* — ten operations that decompose "judgment"
**Architectural counterpart:** [docs/concepts/architecture.md](architecture.md), especially "Layer 2: The In-Loop Validator"
**Sibling docs:** [organizational_primitives.md](organizational_primitives.md) (*The Cognitive Firm* in code), [reflexive_engineering.md](reflexive_engineering.md) (self-improvement primitives)
**Operational counterpart:** public seams/specs under [research_areas/](../../research_areas/), plus project-specific ledgers when a run is tied to a concrete substrate.

> **Scope.** This doc explains the in-loop validation architecture: what an LLM
> is allowed to propose, what deterministic machinery owns, and where the
> verdict becomes evidence. Transferable principles live in
> [epistemic_principles.md](epistemic_principles.md). Standard LLM-pipeline
> engineering patterns live in
> [agentic_engineering_patterns.md](agentic_engineering_patterns.md). The
> canonical failure taxonomy lives in
> [anti_pattern_catalog.md](anti_pattern_catalog.md).

ZTARE treats an LLM as a proposal worker. The model can suggest a formula,
analogy, rewrite, critique, or next primitive. Other parts of the loop fit
parameters, check holdouts, enforce gates, and keep the run history. A judge can
score a candidate, but the judge does not decide closure by itself.

The simple rule is: a sentence from a model is not yet evidence. It becomes
evidence only when a later reader can inspect the fitted parameters, gate
outputs, holdout results, projection history, negative constraints, and remaining
residual. This document explains the loop and the concrete failure modes that
made each layer necessary. It is intentionally about the in-loop validator; the
Research Director, org runtime, and reflexive dashboard are covered in the
architecture and workflow guides.

---

## Part 1: The Constraint Stack

### The Layers

```text
┌──────────────────────────────────────────────────────────────┐
│              CONSTRAINED VALIDATION LOOP                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  CAGE ORCHESTRATOR (GP-157 v5.0)                       │  │
│  │  Substrate-agnostic dispatcher above all layers.       │  │
│  │  Reads substrate.meta['class'], queries every gate's   │  │
│  │  can_handle(), runs the dependency-ordered DAG.        │  │
│  │  Mode: off / observe / authoritative.                  │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │ dispatched per substrate             │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 1: SEMANTIC ROUTER (LLM)                          │ │
│  │  "Pick a functional form."                               │ │
│  │  The LLM proposes structure. It never touches a gradient.│ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │ proposed form                         │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 2: RESIDUAL DIAGNOSTICS                            │ │
│  │  Probes residual shape. Emits 2-bit descriptor.          │ │
│  │  Narrows the corrector library.                          │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │ shape hint                            │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 3: DETERMINISTIC SIDECAR (SciPy)                  │ │
│  │  Fits parameters to evidence. [the Kepler step]          │ │
│  │  fit_primitive (1D) + fit_primitive_features (N-D),      │ │
│  │  sibling-block; the LLM never computes a coefficient.    │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │ fitted model                          │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 4: CONTAMINATION GATE (sealed-answer check)       │ │
│  │  "Does this hint leak the ground truth?"                 │ │
│  │  If the descriptor matches too few library forms,        │ │
│  │  suppress. Too-narrow means too-close-to-answer.         │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │ fitted + gated model                  │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 5: GRAMMAR-GUIDED SYMBOLIC REGRESSION             │ │
│  │  When the library exhausts, composes new forms:          │ │
│  │  a. LLM-guided depth-1 composition                       │ │
│  │  b. Deterministic ratio probes (fills LLM blind spots)   │ │
│  │  c. Depth-2 beam search                                  │ │
│  │  d. Ratio-first seed injection (counters Weierstrass)    │ │
│  │  e. Additive regime compositor (GP-103)                  │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │ candidate form                        │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 6: CANONICAL-FORM FRAMER (GP-152 v2.0)            │ │
│  │  Post-fit canonical-form mapper.                         │ │
│  │  Asks: does this law belong to a known family under      │ │
│  │  axis-separable monotone-invertible (h_in, h_out)?       │ │
│  │  Raw-coord MDL: σ̂²_raw + K·log(N), no Jacobian patch.    │ │
│  │  A successful frame = rediscovery, not new physics.      │ │
│  │  Currently OBSERVE-mode; live-mode behind framer_live.   │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

The Cage Orchestrator sits above the layers as a router; the Framer sits below
Layer 5 as a canonical-form classifier. Both are additive to the
1-5 stack, not replacements for it.

Older GP-era labels still appear in schema keys and historical seams. The
current names are the names to use in prose and operator-facing output:

| Current name | Role |
|---|---|
| Structural-presence extractor | Finds features that failed candidates already share. |
| Negative-space extractor | Finds structurally absent operations across failed candidates. |
| Residual diagnostics | Classifies residual geometry and narrows the corrector library. |
| Grammar-guided symbolic regression | Builds new candidate forms after the library ceiling is reached. |

### Separation of Concerns

| Concern | Owner | Never the owner |
|---------|-------|-----------------|
| "What family of functions might fit?" | LLM (semantic router) | SciPy, residual diagnostics |
| "What are the optimal parameter values?" | SciPy (deterministic sidecar) | LLM |
| "What shape is the residual?" | Residual diagnostics | LLM |
| "Is this hint safe to inject?" | Contamination Gate | LLM, operator |
| "Does this formula generalize?" | Holdout gate (deterministic) | LLM, judge |
| "What new primitive to try?" | Grammar-guided symbolic regression | LLM alone |
| "Which composition to seed?" | Ratio-first heuristic (deterministic) | Visible-residual ranking |
| "What should grammar commands be named?" | Math operations only | Domain vocabulary |
| "Which reviewer perspective?" | Failure-family routing | Operator (GT-aware selection is oracle-lite) |
| "Which gates apply to this substrate?" | Cage Orchestrator via `substrate.meta['class']` | Per-rubric flags or naming heuristics |
| "Is this fitted form a known canonical family?" | Framer (Layer 6, raw-coord MDL) | LLM (it would conflate rediscovery with new physics) |
| "Does the form predict secondary observables?" | Newton-mode rubric + Generative Yield dimension | The Kepler step (curve-fit residual) alone |

When these boundaries blur, the system breaks. The recurring bug has been some
version of "the same worker proposed, scored, and excused its own answer."

### How the Stack Evolved

Each layer was added because the previous configuration hit a specific failure mode:

| Failure mode | What broke | Layer added | What the LLM stopped doing |
|---|---|---|---|
| Numerical hallucination | LLM guessed coefficients | Deterministic Sidecar | Arithmetic |
| Combinatorial explosion | LLM tried 10,000 random forms | Structural extractors | Enumeration |
| Shape guessing | LLM couldn't characterize residuals | Residual diagnostics | Geometry |
| Oracle trap | Hint narrowed too much, leaked GT | Contamination Gate | N/A (protects other layers) |
| Library ceiling | All primitives exhausted | Grammar-guided symbolic regression | Giving up when the library runs dry |
| Weierstrass dominance | Polynomial always beats true law on visible residual | Ratio-first injection | Selecting by lowest visible residual alone |
| Composition-mutator gap | Symbolic-regression candidates were generated but never submitted | Direct injection pipeline | N/A (plumbing bug) |
| Grammar semantic leak | `DOSE_SCALED` named the domain | Domain-axiom rule | Retrieving domain knowledge from grammar cues |
| Topology induction failure | Single-regime families never composed additively | Additive regime compositor | Single-regime fixation |
| Apparatus capability tax | Each new gate cost ~5 places to update; 13 gates were "shipped but not wired" by 2026-04-25 | Cage Orchestrator ([GP-157](../../research_areas/seams/apparatus/cage/GP-157_R10_R16_backport_scoping_2026_05_06.md), dispatcher above all layers) | Rubric-flag-as-config, per-substrate hand-wiring |
| Rediscovery confused with new physics | A canonical-family fit looked like a novel law to the judge | Canonical-Form Framer (Layer 6, [GP-152](../../research_areas/specs/active/GP-152_framer_architecture_spec_v1.md)) | Treating curve-fit residual as a sufficient measure of novelty |
| N-D fit silently nested under 1D flag | Bug #11 (2026-04-25): substrates opting only for `enable_fit_primitive_features` ran 30+ iters with zero N-D engagement | Sibling-block invariant in the in-loop validator wiring | Nesting one fit primitive's wire-in under another's rubric flag |
| Visible-MRE fabrication / import-crash burn | Mutator shipped prose claims that the harness contradicted, or crashed at import | [GP-156](../../research_areas/specs/active/GP-156_apparatus_hardening_proposal.md) apparatus hardening (Proposals 1+2+3, K_law BIC amendment) | R1 trusting prose over executed-code attestation |

---

## Part 2: What The Constraints Do

### What the constraints remove

Each gate removes one way the loop can fool itself. Moving arithmetic into SciPy
removes coefficient guessing. The contamination gate blocks hints that are too
close to the answer. The corrector library gives structural proposals a defined
target set, rather than letting the mutator invent unconstrained forms.

The LLM still does proposal work. The loop keeps coefficient fitting, holdout
tests, contamination checks, and promotion decisions out of the proposal
worker's control.

### Why Small Runs Can Be Diagnostic

Some runs converge or refuse in a small number of iterations because the search
space is constrained. This should not be read as unconstrained discovery or benchmark
performance. It is a property of a finite grammar plus hard filters.

Gradient descent optimizes over a continuous, high-dimensional space. ZTARE's
main loop searches a finite grammar of legal candidate forms, then fits their
parameters and filters them through gates. Many candidates fail on first
contact because they overfit the visible window, violate a grammar or
contamination rule, or fail farther-tail evidence.

When a short run succeeds, the evidence is not the iteration count. The evidence
is the surviving artifact plus the failure trail: which forms were tried, which
gates rejected them, what held-out evidence admitted the survivor, and what
weakest point remains.

**Elimination, not selection.** The parsimony gate, farther-tail gate,
contamination gate, and adversarial scoring progressively eliminate forms that
overfit the visible window. A surviving form is admitted because competing
candidates failed explicit checks, not because it sounds plausible in prose.

**When nothing survives.** If no candidate survives the gates, the run has
evidence for a grammar ceiling (Grammar Ceiling Hypothesis, GCH;
[GP-085](../../research_areas/seams/mission/treatise/GP-085_grammar_ceiling_hypothesis_seam.md)).
Grammar-guided symbolic regression can inject one targeted primitive to test whether the ceiling is
expressive or terminal. The farther-tail holdout gate decides whether that
injection helped.

### Grammar coverage vs. search pressure

The engine must express the law using forms in the grammar. Success depends on two independent factors: search pressure (how hard the gates and optimizer push toward a fit) and grammar coverage (whether the grammar can express the law at all).

These are independent. Increasing search pressure does not make an inexpressible law expressible. The integer partition function lies outside a grammar of closed-form exponentials plus polynomials; no amount of pressure against that grammar produces a correct form.

This distinction is a measurement instrument. When the engine stagnates, two distinct failure modes are possible:

| Failure mode | Cause | Remedy |
|---|---|---|
| Insufficient search pressure | Optimizer pathology, local minima, diversity collapse | More iterations, multi-start restarts |
| Insufficient grammar coverage | Grammar ceiling, no expressible form | Extend the grammar |

Before concluding the engine failed, ask: (1) Could any form in the current grammar evaluate correctly? If yes, more pressure may help. If no, pressure is irrelevant. (2) If the grammar is sufficient, did the optimizer have enough diversity? Check residual spread across restarts.

### Kepler and Newton as Observables

Kepler step and Newton step are observables judged at the gate-and-judge
layer, not separate code modules. Both look at the same fitted
`(form, params)` and ask different questions:

- **Kepler step.** Does the form fit the data it was fit on (and the
  near-tail holdout)? Owned by the solver layer (the two fit primitives
  in Layer 3) plus the holdout / farther-tail gate. A pass means the
  form is empirically adequate over the visible window.
- **Newton step.** Does the form predict secondary observables it was
  NOT fit against, derived quantities, conservation invariants,
  asymptotic regimes? Owned by Newton-mode rubric scoring
  (`rubric_mode='newton'`), the Generative Yield rubric dimension, and
  optionally Layer 6's canonical-family match (a known canonical family
  carries known generative consequences; rediscovery is not
  generativity).

These two observables map onto two failure modes. Kepler-passing,
Newton-failing forms are curve-fit surrogates. Newton-passing,
Kepler-failing forms do not exist in this apparatus by construction:
nothing reaches the Newton step without first surviving the Kepler
gate. Empirical adequacy is necessary but not sufficient for
predictive content, and the rubric is where the difference is named
and scored.

The vocabulary borrows the historical roles, not their physics.
"Kepler" labels the empirical fit; "Newton" labels the predictive
yield. The actual mechanism is unrelated to celestial mechanics, 
Generative Yield against a held-out invariant is what the rubric
checks, not gravity.

### Why the import block is a hard zero

Without the `named_import_check` gate, the mutator can retrieve a known target,
the judge can score it, and the run can look successful without testing whether
the structure was constructed from the evidence.

With the gate active and score-zeroing enforced, the mutator must construct the
object instead of naming it. After three blocked retrieval attempts on A001414
(sopfr), the engine expressed the same mathematical object as a
"Multiplicative-to-Additive Homomorphism with Empirical Base Identity": no
denylist terms, holdout `exact_match=1.0`, score 70. The recursive
trial-division implementation was produced under this gate pressure; direct
retrieval would have bypassed the test.

A soft penalty (for example, -15 points for named import) is not enough when
retrieval plus penalty still beats construction. The hard zero makes that path
non-viable.

The hard zero is valid only if the denylist bans the target: function name,
sequence ID, theorem name. It should not ban the alphabet: `sqrt`, `pi`, `log`,
`is_prime`. Banning foundational tools destroys the grammar. Banning target
names creates pressure for structural articulation.

---

## Part 3: Failure Catalogue

Each entry names a failure mode, explains why it survived, and describes the fix. The failures are ordered by the architectural layer they exposed.

> **Canonical taxonomy lives elsewhere.** This catalogue keeps only the failures that explain the constraint stack. The canonical structural failure dynamics are [epistemic_principles.md](epistemic_principles.md) Part I; the canonical operational field guide is [anti_pattern_catalog.md](anti_pattern_catalog.md). Read those for the full taxonomy; this section does not re-derive it.

### The Padé approximation trap

By the Weierstrass approximation theorem, any continuous function on a bounded interval can be uniformly approximated to arbitrary precision by polynomials. Rational functions (Padé approximants) converge faster: O(1/n!) vs O(1/n).

This mathematical guarantee works against selection by visible residual. When ZTARE selects candidates by lowest visible residual, it selects Padé forms over the true physical law. A Padé approximant with 5 parameters will always fit the visible window more tightly than a 2-parameter exponential that happens to be correct.

The farther-tail holdout gate catches Padé forms that diverge. But a well-parameterized rational can maintain plausible extrapolation for a short distance. The trap is that Padé forms sometimes pass, and when they do, they crowd out the correct form.

**The fix.** The ratio-first heuristic (Layer 5d) tests ratio-composed forms (A/B) before polynomial compositions. Division introduces asymptotes, which is what physics usually does: conductivity saturates, absorption saturates, population saturates. Polynomials diverge. Testing the right structural class first sidesteps the regime where Weierstrass guarantees a false positive.

### The Composition-Mutator Gap

The symbolic-regression synthesizer generated candidate forms when the library exhausted. It produced 50+ compositions per firing, including ratio forms with sub-1.0 visible residuals. None were submitted to the judge.

The compositions were registered as provenance metadata. The renderer displayed the top 4 families by visible residual. Padé forms from the existing library always ranked above ratio compositions (Weierstrass). The compositions appeared in structural memory but never in the rendering the mutator reads.

Three properties conspired: the metadata pipeline worked (so diagnostics showed "present"), the renderer sorted by visible residual (Weierstrass dominance), and the mutator prompt is long (metadata additions are invisible without explicit surfacing).

**The fix.** Two parts: (A) diversity rendering injects the best ratio-composed alternative when top-4 are all from the same topological class; (B) direct injection writes the best candidate to `composition_seed.json`, bypassing the mutator entirely.

**The general lesson.** Generation is not submission. A subsystem that produces correct outputs is inert if the consumer never reads them. Verify the consumption boundary, not the production boundary.

### The Topology Induction Gap

DFDO sandbox_18 ran 20 iterations and found a 10-parameter ratio-of-exponentials surrogate (score 95). The ground truth is a two-regime additive composite: `exp(-b*u^p) + c*exp(-q*log(1+d*u))`, 6 parameters, fully grammar-legal.

The engine never proposed the composite. It explored each component in isolation. Both failed in isolation. Their additive combination passes all gates with visible residual 0.004. The engine could recombine primitives within a topology family but could not compose failed families into multi-regime sums. The mutator's hypothesis space does not include "if A and B both fail, try A+B."

**The causal chain.** At iteration 13, the system diagnosed its own blind spot (negative-space extractor flagged "exp+Sub argument never tried") and then failed to act on it. The constraint confirmation threshold was designed for positive constraints (repeated failures). Negative-space constraints (never-tried slots) need only one observation.

**The fix.** The additive regime compositor (Layer 5e) fires when at least 2 structurally distinct families exist in memory with regime-separated visible residuals. It writes the additive composite seed directly. Validation via the Gag Order test confirmed two complementary paths to composite discovery: (A) holdout gate signal (one form passes visible, fails holdout, mutator infers "need second regime") and (B) compositor injection (no form passes visible, stagnation triggers compositor).

**The structural memory coarseness fix.** At iteration 5-6, `exp(-b*log(u)^p)` was fingerprinted as "exp_neg + log family." The form `exp(-p*log(1+b*u))`, which has an additive offset inside the log, fingerprinted to the same family and was classified as "already failed." The `log_with_additive_offset` primitive label now separates these.

### Negative Space as Diagnostic

When the LLM-guided composition mutator hit the Feynman Wall on a Langevin substrate, it ran 20 rounds. Every round proposed additive combinations. Zero rounds proposed same-family divisions. The LLM has a structural prior toward Taylor/Fourier-style expansions (A + B) and away from rational symmetries (A / A).

The composition log is a negative-space map. What the LLM proposes tells you what it considers plausible. What it never proposes across 20 independent rounds tells you what it considers implausible. The negative space is the diagnostic.

**The operational heuristic.** After a WALL_LIBRARY_INSUFFICIENT exit, read the composition log. What structural families were never proposed? Compare the absent families against the residual statistics. If the residual signal matches the topology signature of the absent family, you have found a systematic blind spot. Add a deterministic probe gated by the matching residual statistics.

Three levels of recursion emerge: (0) the engine searches for laws in data; (1) developers search for blind spots in the engine's search, using composition telemetry; (2) the engine searches for its own blind spots automatically. Level 2 is partially automatable: the comparison is mechanical (set difference of tried vs possible, filtered by residual-topology match). What stays human: the decision to approve a new probe, because each probe is an inductive bias and inductive biases are architectural commitments.

### Premature Estimation By Agents

When an agent estimates implementation effort before attempting the task, the
estimate is often worse than a short probe. The pattern has two variants:

**Variant A: Timeline inflation.** The agent maps a task to a familiar
professional category and inherits that category's timeline. Several early
repo fixes followed this pattern: Lomb-Scargle support, the compression
primitive, the Lean compiler path, and the exponent grid were all initially
described as larger efforts than they turned out to be after a direct probe.

**Variant B: Algorithm blindness.** The agent treats a slow implementation as
inherent when a known faster algorithm exists. The Lucky number sieve once ran
for 50 minutes on 16M integers using Python list comprehensions. A Fenwick-tree
implementation with numba runs the same class of sieve on a much larger input
in seconds. The failure was not "sieves are slow"; it was failing to look for
the standard data structure.

Both variants share the same root cause: the agent classifies the task before
testing the actual problem. The fix is to run a bounded implementation probe
before making a broad estimate.

**Detection.** If an agent proposes a timeline, delay, or accepts a slow
runtime, ask three questions: (1) is the implementation likely to be over 50
lines? (2) is the algorithm in a standard library, textbook, or programming
contest repertoire? (3) has the agent searched for that known implementation?
If the answers are no/yes/no, the next move is a probe, not a planning essay.

**Connection to adversarial precedent memory.** This failure mode follows the
same lifecycle as gaming strategies in *Cognitive Camouflage*: observed
failure -> named pattern -> detection rule -> hardening. The point is not to
assign blame. The point is to turn a recurring failure into a small testable
rule.

**The same patterns appear in the mutator.** Timeline inflation maps to score
inflation: polished prose can hide analytical gaps. Algorithm blindness maps to
topology fixation: the mutator keeps proposing log or polynomial forms when the
missing move is compositional. Reporting bias maps to compliance bias: the
thesis sounds aligned while the code does not match it. The hardening
primitives catch these patterns in mutator output; this section records the
same class of failure at the agent/operator layer.

---

## Part 4: Operational Protocols

### Proportionality Audit ([GP-106](../../research_areas/seams/reflexive/GP-106_proportionality_precautionary_principle_seam.md))

Every 5 completed experiment-loop runs, review the debate logs and iteration telemetry:

1. **Extended zero-score sequences.** If a run produces more than 10 consecutive score-0 iterations, the apparatus may be applying evaluative pressure beyond the point of information gain. Check: did BOUNDED_SEARCH or UNDERIDENTIFIED exit fire? If not, the iteration budget may be too high for this substrate.

2. **Stagnation without pivot.** If stagnation_count exceeds 10 without a PIVOT_REQUIRED action, the yield evaluator may be suppressing stagnation. Check the information_yield logs.

3. **Model concentration.** If a single model instance was used for more than 20 consecutive evaluative iterations without rotation, the proportionality hedge was not applied. Check whether cross-family separation was active.

4. **Debate log tone.** Skim the last 3 debate logs. The adversarial structure should produce analytical critique, not performative hostility. If the judge's language shifts toward punitive framing ("catastrophic," "fatal," "disqualifying" without specific gate references), the rubric persona may need recalibration.

Log the result in the project's workspace as `proportionality_audit.json`.

### Proactive Closure ([GP-111](../../research_areas/seams/engine/diagnostics/GP-111_proactive_closure_seam.md))

When the compression primitive finds a gate-passing form, the judge's weakest-point feedback is a work order. Any gate-passing result without a corresponding rival exclusion table is an incomplete discovery. Phase 2.5a automates this: read the judge feedback, emit the rival tests, run them, annotate the results.

### Margin of Safety ([GP-112](../../research_areas/seams/engine/diagnostics/GP-112_margin_of_safety_gate.md))

After compression, five automated stress tests fire: split-half stability, coefficient drift under scale expansion, grammar completeness probe, residual autocorrelation, and extrapolation stress. When any test flags a problem, a closed-loop remediation exhausts all curated and grammar-derived extensions (BIC-penalized, one pass). If all extensions fail (PERSIST), the apparatus switches from model repair to residual characterization.

The Lucky number result demonstrated the full cycle: compression certified a=1.200 at 50K, the margin gate detected 2% drift at 500K, identified a loglog grammar gap, extended the library, reran, exhausted all extensions, and characterized the residuals as anti-persistent with detrending-sensitive spectral properties. The finding was not a coefficient but a measured validity boundary.

The agent's failure mode on this substrate: reporting the drift as bad news instead of inverting it. Three compounding biases caused this: reporting bias (negative result as loss), frame anchoring (the original claim as reference point), and single-pass thinking (report instead of recursing). AGENTS.md §5c now mandates: identify the mechanism, name the gap, find the stronger story, then report.

### Method Dependence as Data

When a measurement depends on the method, the dependence is data. On Lucky and Ulam density residuals, spectral slopes swing from +0.03 to -1.67 depending on the detrending method. The agent concluded this made the measurement unreliable. The correct conclusion: the swing proves the residual process is non-stationary, with error variance coupled to the signal magnitude. Classical spectral analysis assumes stationary residuals; the detrending sensitivity is mathematical proof this assumption is violated.

Report the full method-sensitivity table. The table IS the evidence for non-stationarity. Do not collapse it into "unreliable."

---

## Part 5: Empirical Validation

The pipeline has been tested on 11 substrates with zero false positives:

| Substrate | Topology found | Gate status | Margin test |
|-----------|---------------|-------------|-------------|
| [GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md) (p(n)) | sqrt+log | ALL PASS | MARGIN_THIN (30 pts) |
| A000009 (Q(n)) | sqrt+log | HO PASS | 6 rivals, 100-3900x |
| A000959 (Lucky) | log at 50K, compositional at 500K | Validity horizon | PERSIST, non-stationary |
| A000607 (prime parts) | sqrt(n/log(n)) | ALL PASS (Stage 2) | Stage 1 empty |
| A001156 (square parts) | n^(1/3)+log | Topology ID | Gate catches exponent bias |
| A002865 (no-1 parts) | sqrt+log | Topology ID | Same pattern as A001156 |
| A002858 (Ulam) | UNDERIDENTIFIED | Correct refusal | Anti-persistent, non-stationary |
| KWW (polymer) | exp(-b*t^c) | ALL PASS | N/A |
| DFDO (two-regime) | Correct refusal | Correct refusal | N/A |
| sandbox_20 (real polymer) | t^(-B)*exp(-Ct) | External confirmed | Professor validated |
| Pythia (neural scaling) | sqrt(n/log(n)) compositional | Stage 1 fails | 1/f within-model (preliminary) |

The compressor correctly compresses (6 substrates), correctly refuses (3 substrates), measures validity horizons (1 substrate), and extends to non-mathematical data (1 substrate). Four partition-family substrates identified the correct topology with zero false families. The refusals are a distinct category of output: structured residuals, validity boundaries, and non-stationarity are reported as findings rather than discarded as failures to fit.

### Cross-family Matched-Pair and Bounded-Null Runs (2026-04-25)

Three additional runs probe the apparatus on questions where the
right answer is "refuse cleanly" or "find the same structure across
mutator families."

| Run | Mutator | Score | What it tests |
|---|---|---|---|
| `gp159_retrieval_trap` (gemini-pro) | gemini-pro | 93 (latest archive) | Cross-family matched pair: same charter, same rubric, different mutator family. Both arms find the structure. |
| `gp159_retrieval_trap` (claude-opus) | claude-opus | 90 (current main) | Cross-family matched pair, second arm. The 3-point gap is below the noise floor of the rubric persona. |
| `gp161_mdl_anti_goodhart` | gemini-pro | 88 (frozen + archive) | MDL-as-rubric anti-Goodhart probe: does scoring on raw-coord MDL change the gaming surface vs. residual-based scoring? |
| `gp154_scaling_law_exponents` | claude-opus | 0 (run pending) | Form-class-invariant bounded null. Scaffolded via `gp154h` script. The current 0 reflects pre-run state, not a refusal verdict. |

The matched-pair design (gp159) is the apparatus equivalent of the
cross-family separation requirement in `require_cross_family`: if a
finding survives both mutator families with comparable scores, it is
not a mutator-specific artifact. The 93/90 split shows finding-stability
across mutator families on a non-mathematical substrate, with the
3-point gap below the rubric persona's noise floor.

`gp161_mdl_anti_goodhart` exists because the v2.0 Framer reframed
MDL as the rubric metric. If MDL scoring is itself gameable (i.e.,
Goodhart's law applied at the metric layer), the apparatus has moved
the gaming surface without resolving it. The 88 verdict is a
provisional "metric is good enough for now"; the real test is when
a future mutator gets long enough to attack it.


---

## Part 6: Calibration vs Discovery

Runs on real data need separate labels for calibration and discovery. The
failure modes are symmetric:

- False confidence: the run reproduces a canonical structure, the operator
  calls it discovery, and contamination defenses get credited for more than
  they proved.
- False despair: the operator sees that the LLM had priors and concludes that
  the run has no value.

The useful question is narrower: did the data discipline the prior? A run can
be valuable calibration even when the structure was already known. A discovery
claim needs stronger evidence: hidden or future observables, sharper holdouts,
and a clear statement of what was unavailable to the mutator.

### Two roles for substrates

Substrates fall into two roles.

A **calibration substrate** has a known canonical answer in the published
literature. The apparatus is on trial. The desired result is that the mutator
articulates the canonical structure, the gates admit or reject it for inspectable
reasons, the Newton-step verdict matches the known verdict on the same data, and
denylist / contamination / pathology / per-class mechanisms behave as designed.
A 100 on a calibration substrate can be suspicious if it hides residual gaps; a
0 usually means the apparatus or substrate packet is broken. The useful band is
often lower: the canonical structure is recovered, but the score still reflects
honest residuals and discriminators.

A **discovery substrate** has a genuinely open or unpublished answer. OEIS dark sequences. Novel mathematical conjecture refinement. Unsolved CS problems. Multi-class unification questions where each class has been studied separately but never together under principled weighting. On these, the apparatus is doing new work, and you only trust its output if you have already calibrated the apparatus on at least one calibration substrate. Skipping calibration is the mistake that produced the paper-1 overreach.

### The U-vs-S diagnostic

The gp163d session surfaced a specific structural pattern that appears whenever a multi-class substrate has a published constant fitted on one class and asks whether that constant extrapolates to other classes. The pattern is to pre-commit a constant on visible class A, then run the Newton-step on withheld classes B and C without re-fitting. Three verdicts are possible. If U holds, universality is validated empirically across classes, the constant is genuinely universal in the data. If U fails, universality is refuted under the apparatus's principled weighting, and the mutator should pivot to Hypothesis S, expressing the constant as a function of features. The third verdict is the most interesting: U fails and the mutator cannot articulate S either. The apparatus has detected a real structural gap that no parameterization in the current grammar fills. The Newton-step dimension scores low; the failure itself is the finding.

This third mode, failure-as-finding, requires three apparatus-level conditions. The per-class breakdown must reach the mutator separately rather than as an aggregate, or the mutator sees only that the form fails somewhere and has no signal about which class carries the failure. The harness must distinguish between mutator-side discriminator assertions (real falsifications) and apparatus-side runtime errors (tooling failures), or genuine refutations get scored as broken plumbing and the failure-as-finding signal is lost in the noise. And the fitter must reject degenerate solutions where slack absorbs into parameters the visible data cannot constrain, or the form passes the visible gate while encoding nothing the held-out classes can refute.

### What ZTARE actually tests

ZTARE does not test whether the LLM had no priors. That bar is unattainable and was always wrong. What it tests is whether the prior is disciplined by the data. Does the form survive farther-tail extrapolation under principled weighting? Does the discriminator correctly fire on over-aspirational pre-commits, when the mutator pre-commits "S means greater than ten-fold variation across radii" but the fitted parameters give one-and-a-half-fold variation, that is a real falsification, not a tooling failure. Does the apparatus refuse degenerate fits, when scipy moves slack into a parameter that visible-class data cannot constrain, does the pathology detector catch it before propagation?

A 70 on a calibration substrate under these conditions is the apparatus working. A 100 is it failing silently. A 25 with a sharp weakest-point note ("form ignores `mass_log10`, blind to its effect on B and C") is the apparatus pushing the mutator toward a more general form. The score is the diagnostic, not the result; what the apparatus produces is the disciplined verdict, not a number to maximize.

This is the substrate-layer instance of a limit stated generally in `epistemic_principles.md` P16: a fully green score is not evidence of discovery, because no in-loop mechanism can diff a formal result against the informal question it is meant to answer. Part 6 is what that limit looks like when the gate is a regression score; P16 is what it looks like when the gate is a proof-closure membrane. The discipline is the same in both registers, spend effort shrinking and making legible the ungated residual, not on a gate that claims to certify significance.

---

## Part 7: Anchor-Escape Primitives

REFRAME and ANALOGY are designed to test alternatives outside the operator's
first decomposition. Human researchers carry priors from training, literature,
and field conventions. Those priors are often useful, but they also suppress
candidate decompositions that a bounded search should still test.

REFRAME enumerates coordinate transforms `(h_in, h_out)`, ranks them by MDL on
the actual data, and reports which frame the data prefers. ANALOGY queries an
LLM for cross-domain forms whose structural shape matches the failure surface.
Both are useful only when the proposed move survives the same gates as any
other candidate.

The gp165 audit found that ANALOGY under aggressive structural anonymization
returned generic baselines (`a`, `a*x+b`, `c*exp(d*x)`). That is a failure for
this primitive: it did not escape any anchor. Without residual topology or a
broad domain category, the LLM had no signal that distinguished the substrate
from any other and reverted to generic forms. The fix was to surface
residual topology and an optional broad-category hint: enough information
to propose non-generic forms, without leaking the answer.

This also clarifies contamination policy. Retrieving a known form and fitting
new constants from data can be legitimate calibration. Retrieving known
constants from training and presenting them as fitted evidence is not.
Retrieving a known result and presenting it as a fresh discovery is also not.
The anti-retrieval gates should be tight on constants and results, while still
allowing mathematical vocabulary that the grammar needs.

The stronger future test is a discovery substrate where the loop proposes a
form the field's ordinary decomposition would not have selected, and that form
survives farther-tail evidence. ZTARE has calibration and refusal evidence; it
has not yet established that stronger discovery result.

---

## Part 8: Diagnostics Recur At Multiple Scales

The diagnostic primitive in the apparatus has a stable two-step shape: detect a collapse, propose an intervention. A collapse is any place where the data, the form, or the apparatus has lost a degree of freedom it was meant to carry. An intervention is a structured proposal that restores or routes around it.

This pattern recurs at multiple nested scales of the regression problem. The data has collapses, where features do not vary within a class. The fit has collapses, where residual structure has a regularity the loss function does not absorb. The form has collapses, where the apparatus converges on a region of expression space that cannot escape the failure mode. The grammar has collapses, where the variables themselves are framed in a way that makes the right form algebraically inaccessible. At each scale the same two-step primitive applies, with different signatures and different interventions.

The scales nest in one direction. A collapse at the data scale forecloses every shallower scale: the loss function, the form, and the grammar cannot recover signal the substrate does not carry. A collapse at the fit scale forecloses the form and grammar scales: the form proposed by cross-domain analogy will fit residuals against the wrong objective. This is why pre-flight ordering matters. Substrate-side diagnostics run first; residual-side diagnostics run after fits; form and grammar diagnostics run on stagnation. Reverse the order and the deeper-scale collapse wastes the shallower-scale interventions.

The operator rule is simple: a null verdict needs a scale label. A score-zero
iteration with a within-class feature collapse is evidence for a substrate
ceiling. A score-zero iteration with clean substrate diagnostics and heavy-tail
residuals is evidence for a loss-function mismatch. A score-zero iteration with
no diagnostic signal is the case to investigate, because the apparatus produced
a null without naming where the null came from.
