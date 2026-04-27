# The Cognitive Gym

**Status:** public / load-bearing
**Paper parent:** *The Principles of Epistemic Verification* (Paper 5) — ten operations that decompose "judgment"
**Architectural counterpart:** [docs/concepts/architecture.md](architecture.md) §6 (Layer 3: ZTARE Core Validator)
**Sibling docs:** [organizational_primitives.md](organizational_primitives.md) (Paper 4 in code), [reflexive_engineering.md](reflexive_engineering.md) (self-improvement primitives)
**Operational counterpart:** `research_areas/private/philosophy/operational_manual_substrate_construction.md`

An LLM inside a constrained validation loop produces better science than an unconstrained LLM, for the same reason a weightlifter inside a squat rack lifts more than one without. The architecture enforces epistemic discipline — removing the failure modes that prevent ambitious work. ZTARE trusts the LLM to do what it does well (pattern recognition, structural analogy, topological search) while handing what it does poorly (arithmetic, gradient sensitivity, self-consistency under pressure) to deterministic machinery.

This document explains the constraint architecture: what it is, why it works, how it fails, and what it proves.

---

## Part 1: The Constraint Stack

### The Layers

```text
┌──────────────────────────────────────────────────────────────┐
│                     THE COGNITIVE GYM                         │
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
│  │  Layer 2: TOPOLOGICAL SIEVE (Component C)                │ │
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
│  │  Layer 4: CONTAMINATION GATE (Oracle check)              │ │
│  │  "Does this hint leak the ground truth?"                 │ │
│  │  If the descriptor matches too few library forms,        │ │
│  │  suppress. Too-narrow means too-close-to-answer.         │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │ fitted + gated model                  │
│  ┌────────────────────v─────────────────────────────────────┐ │
│  │  Layer 5: TOPOLOGY SYNTHESIZER (Component D)             │ │
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
1–5 stack, not replacements for it.

### Separation of Concerns

| Concern | Owner | Never the owner |
|---------|-------|-----------------|
| "What family of functions might fit?" | LLM (semantic router) | SciPy, Component C |
| "What are the optimal parameter values?" | SciPy (deterministic sidecar) | LLM |
| "What shape is the residual?" | Component C (topological sieve) | LLM |
| "Is this hint safe to inject?" | Contamination Gate | LLM, operator |
| "Does this formula generalize?" | Holdout gate (deterministic) | LLM, judge |
| "What new primitive to try?" | Component D (topology synthesizer) | LLM alone |
| "Which composition to seed?" | Ratio-first heuristic (deterministic) | Visible-residual ranking |
| "What should grammar commands be named?" | Math operations only | Domain vocabulary |
| "Which reviewer perspective?" | Failure-family routing | Operator (GT-aware selection is oracle-lite) |
| "Which gates apply to this substrate?" | Cage Orchestrator via `substrate.meta['class']` | Per-rubric flags or naming heuristics |
| "Is this fitted form a known canonical family?" | Framer (Layer 6, raw-coord MDL) | LLM (it would conflate rediscovery with new physics) |
| "Does the form predict secondary observables?" | Newton-mode rubric + Generative Yield dimension | The Kepler step (curve-fit residual) alone |

When these boundaries blur, the system breaks. Every integration bug in the project's history traces to a boundary violation.

### How the Stack Evolved

Each layer was added because the previous configuration hit a specific failure mode:

| Failure mode | What broke | Layer added | What the LLM stopped doing |
|---|---|---|---|
| Numerical hallucination | LLM guessed coefficients | Deterministic Sidecar | Arithmetic |
| Combinatorial explosion | LLM tried 10,000 random forms | Components A+B | Enumeration |
| Shape guessing | LLM couldn't characterize residuals | Component C | Geometry |
| Oracle trap | Hint narrowed too much, leaked GT | Contamination Gate | N/A (protects other layers) |
| Library ceiling | All primitives exhausted | Component D | Giving up when the library runs dry |
| Weierstrass dominance | Polynomial always beats true law on visible residual | Ratio-first injection | Selecting by lowest visible residual alone |
| Composition-mutator gap | Component D generated forms, never submitted them | Direct injection pipeline | N/A (plumbing bug) |
| Grammar semantic leak | `DOSE_SCALED` named the domain | Domain-axiom rule | Retrieving domain knowledge from grammar cues |
| Topology induction failure | Single-regime families never composed additively | Additive regime compositor | Single-regime fixation |
| Apparatus capability tax | Each new gate cost ~5 places to update; 13 gates were "shipped but not wired" by 2026-04-25 | Cage Orchestrator (GP-157, dispatcher above all layers) | Rubric-flag-as-config, per-substrate hand-wiring |
| Rediscovery confused with new physics | A canonical-family fit looked like a novel law to the judge | Canonical-Form Framer (Layer 6, GP-152) | Treating curve-fit residual as a sufficient measure of novelty |
| N-D fit silently nested under 1D flag | Bug #11 (2026-04-25): substrates opting only for `enable_fit_primitive_features` ran 30+ iters with zero N-D engagement | Sibling-block invariant (architecture.md §6a) | Nesting one fit primitive's wire-in under another's rubric flag |
| Visible-MRE fabrication / import-crash burn | Mutator shipped prose claims that the harness contradicted, or crashed at import | GP-156 apparatus hardening (Proposals 1+2+3, K_law BIC amendment) | R1 trusting prose over executed-code attestation |

---

## Part 2: Why Constraints Work

### Constraints Amplify

The squat rack removes the failure mode (bar falling backward) that prevents loading with weight the lifter could otherwise handle. Removing arithmetic from the LLM removes the failure mode (precision decay) that prevents proposing ambitious functional forms. The contamination gate removes the failure mode (oracle trap) that stops search before it starts. The corrector library provides a vocabulary of tested forms so structural intuition has somewhere to land.

The goal is an LLM that pushes harder on the things it does well because the things it does poorly are handled by deterministic machinery.

### Why Rapid Convergence Is Expected

A discovery in 6-10 iterations feels impossible if you expect gradient descent. It is expected if you understand abduction over a constrained combinatorial space.

Gradient-descent learning takes thousands of steps to minimize a loss function over a continuous, high-dimensional space. Any shape is reachable at any time. Overfitting hides inside small parameter adjustments.

ZTARE works differently. The grammar is a finite vocabulary: on the order of thousands of legal candidate forms. The gate battery (parsimony check, farther-tail holdout, adversarial scoring) eliminates the majority of forms on first contact. The remaining shapes are structurally constrained to be close to the truth. When the engine converges in 8 iterations, it has exhausted the wrong regions of a small, well-defined search space and landed in the only region that legally survives all gates.

**The LIGO metaphor.** ZTARE creates a vacuum. The parsimony gate, farther-tail gate, contamination gate, and adversarial scoring progressively remove every form that is too light. What remains at the bottom of the vacuum survived because nothing else could. The Planck law was not selected because it looks like a good answer. It survived because every other shape in the grammar died under gate pressure.

**The epistemic corollary.** If nothing survives the vacuum, the grammar has a ceiling (Grammar Ceiling Hypothesis, GCH). The absence of survivors is a signal that the grammar cannot express the ground truth. Component D allows one targeted primitive injection to attempt an escape. The difference between "Component D solves the problem" and "GCH is terminal" is whether the injected primitive is in the right structural family. That determination requires the farther-tail holdout gate.

### The Epistemic Discipline of Spelling

The discipline forces the engine to spell the law using the grammar's alphabet. Success depends on two independent things: the quality of the spelling pressure (how hard the discipline pushes) and the expressive capacity of the alphabet (whether it contains the letters the law requires).

These are independent. You can increase pressure indefinitely without making previously inexpressible laws expressible. The integer partition function lives outside the alphabet of closed-form exponentials plus polynomials. No amount of forcing pressure against that vocabulary will produce a correct spelling.

This gives you a measurement instrument. When the engine stagnates, two distinct failure modes are possible:

| Failure mode | Cause | Remedy |
|---|---|---|
| Insufficient spelling pressure | Optimizer pathology, local minima, diversity collapse | More iterations, multi-start restarts |
| Missing letters | Grammar ceiling, no expressible form | Extend the alphabet |

Before concluding the engine failed, ask: (1) Could any expression in the current alphabet evaluate correctly? If yes, more pressure may help. If no, pressure is irrelevant. (2) If the alphabet is sufficient, did the optimizer have enough diversity? Check residual spread across restarts.

### Kepler and Newton as Observables

Kepler step and Newton step are observables judged at the gate-and-judge
layer, not separate code modules. Both look at the same fitted
`(form, params)` and ask different questions:

- **Kepler step.** Does the form fit the data it was fit on (and the
  near-tail holdout)? Owned by the solver layer (the two fit primitives
  in Layer 3) plus the holdout / farther-tail gate. A pass means the
  form is empirically adequate over the visible window.
- **Newton step.** Does the form predict secondary observables it was
  NOT fit against — derived quantities, conservation invariants,
  asymptotic regimes? Owned by Newton-mode rubric scoring
  (`rubric_mode='newton'`), the Generative Yield rubric dimension, and
  optionally Layer 6's canonical-family match (a known canonical family
  carries known generative consequences; rediscovery is not
  generativity).

These two observables map onto two failure modes. Kepler-passing,
Newton-failing forms are curve-fit surrogates. Newton-passing,
Kepler-failing forms do not exist in this apparatus by construction —
nothing reaches the Newton step without first surviving the Kepler
gate. The asymmetry is the point: empirical adequacy is necessary
but not sufficient for predictive content, and the rubric is the
place where the difference is named and scored.

The vocabulary borrows the historical roles, not their physics.
"Kepler" labels the empirical fit; "Newton" labels the predictive
yield. The actual mechanism is unrelated to celestial mechanics —
Generative Yield against a held-out invariant is what the rubric
checks, not gravity.

### Forced Abduction

Without the named_import_check gate, an LLM retrieves a known function, the judge scores it, and the run ends. The structural depth of the LLM's knowledge is never tested.

With the gate active and score-zeroing enforced, something else happens. After three blocked retrieval attempts on A001414 (sopfr), the engine expressed the same mathematical object as: "Multiplicative-to-Additive Homomorphism with Empirical Base Identity." No denylist terms. Holdout exact_match=1.0. Score 70. The recursive trial-division implementation was only produced under epistemic pressure. Surface retrieval would never have produced it.

A soft penalty (e.g., -15 points for named import) does not force a basin escape. The LLM can calculate that retrieval plus penalty still reaches a local maximum faster than traversing dark data space. The hard zero is the only gradient signal steep enough to make the retrieval basin unnavigable.

The hard zero is valid only if the denylist bans the target (function name, sequence ID, theorem name), never the alphabet (sqrt, pi, log, is_prime). Banning foundational tools destroys the combinatorial engine. Banning target names creates the forcing pressure that makes structural articulation necessary.

---

## Part 3: Failure Catalogue

Each entry names a failure mode, explains why it survived, and describes the fix. The failures are ordered by the architectural layer they exposed.

### The Padé Trap

By the Weierstrass approximation theorem, any continuous function on a bounded interval can be uniformly approximated to arbitrary precision by polynomials. Rational functions (Padé approximants) converge faster: O(1/n!) vs O(1/n).

This is a mathematical guarantee, and it is the enemy.

When ZTARE selects candidates by lowest visible residual, it selects Padé forms over the true physical law. A Padé approximant with 5 parameters will always fit the visible window more tightly than a 2-parameter exponential that happens to be correct.

The farther-tail holdout gate catches Padé forms that diverge. But a well-parameterized rational can maintain plausible extrapolation for a short distance. The trap is that Padé forms sometimes pass, and when they do, they crowd out the correct form.

**The fix.** The ratio-first heuristic (Layer 5d) tests ratio-composed forms (A/B) before polynomial compositions. Division introduces asymptotes, which is what physics usually does: conductivity saturates, absorption saturates, population saturates. Polynomials diverge. Testing the right structural class first sidesteps the regime where Weierstrass guarantees a false positive.

### The Composition-Mutator Gap

Component D generated candidate forms when the library exhausted. It produced 50+ compositions per firing, including ratio forms with sub-1.0 visible residuals. None were submitted to the judge.

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

### Agent Straw Man Estimation

When the agent estimates implementation time instead of implementing, the estimate is almost always inflated. The pattern has two variants:

**Variant A: Timeline inflation.** The agent maps tasks to "specialist clusters" from training data and inherits the guild's timeline. Every instance where the operator pushed past resistance, implementation took under 15 minutes: Lomb-Scargle (estimated "a week," built in 10 minutes), compression primitive (deferred "for next session," built in 20 minutes), Lean compiler ("needs toolchain expertise," built in 15 minutes), exponent grid ("debate first," built in 15 minutes).

**Variant B: Algorithm blindness.** The agent accepts a slow implementation as inherent when a known faster algorithm exists. The Lucky number sieve ran for 50 minutes on 16M integers using Python list comprehensions (O(n^2) per step). A Fenwick tree with numba runs the same sieve on 100M integers in 14 seconds. The agent never searched for efficient sieve algorithms. Gemini Pro identified the Fenwick tree approach in one prompt. The agent's training-weight prior says "sieves are slow" when competitive programming has solved this decades ago.

Both variants share the same root cause: the agent classifies the task before solving it, and the classification carries a difficulty estimate from training data that is unchecked against the actual problem. The fix is the same: attempt the implementation before estimating it.

**Detection.** If the agent proposes a timeline, delay, or accepts a slow runtime: (1) Is the implementation over 50 lines? (2) Is the algorithm in a standard library or textbook? (3) Has the agent searched for known efficient implementations? If the answers are no/yes/no, the estimate or acceptance is wrong.

**Connection to the adversarial precedent memory pattern.** This failure mode follows the same lifecycle as gaming strategies in Paper 1: observed failure (agent overestimates) -> named primitive (Straw Man Estimation) -> detection rule (the three questions above) -> hardened into the system (memory file loads at session start, §5c inversion reflex). The agent's cognitive biases are treated the same way as LLM gaming strategies: catalogue, name, detect, harden.

**The reflexive isomorphism.** Every bias documented in this section applies equally to the LLM mutator inside the apparatus. Timeline inflation maps to score inflation (prose quality masking analytical gaps). Algorithm blindness maps to topology fixation (the mutator proposes log/polynomial when the answer is compositional, the same way the agent accepts O(n^2) when O(n log n) exists). Reporting bias maps to compliance bias (thesis sounds good, code doesn't match). The agent's cognitive biases ARE the mutator's cognitive biases because both are LLMs operating under optimization pressure. The kernel hardening primitives (Paper 2) were built to catch these patterns in the mutator's output. The Cognitive Gym documents them appearing in the agent's own behavior. Paper 5's "fractal Goodhart" prediction (the same pattern recurs at every optimizing layer) is confirmed by this isomorphism: the agent that catches gaming in the mutator exhibits the same gaming patterns itself.

---

## Part 4: Operational Protocols

### Proportionality Audit (GP-106)

Every 5 completed experiment-loop runs, review the debate logs and iteration telemetry:

1. **Extended zero-score sequences.** If a run produces more than 10 consecutive score-0 iterations, the apparatus may be applying evaluative pressure beyond the point of information gain. Check: did BOUNDED_SEARCH or UNDERIDENTIFIED exit fire? If not, the iteration budget may be too high for this substrate.

2. **Stagnation without pivot.** If stagnation_count exceeds 10 without a PIVOT_REQUIRED action, the yield evaluator may be suppressing stagnation. Check the information_yield logs.

3. **Model concentration.** If a single model instance was used for more than 20 consecutive evaluative iterations without rotation, the proportionality hedge was not applied. Check whether cross-family separation was active.

4. **Debate log tone.** Skim the last 3 debate logs. The adversarial structure should produce analytical critique, not performative hostility. If the judge's language shifts toward punitive framing ("catastrophic," "fatal," "disqualifying" without specific gate references), the rubric persona may need recalibration.

Log the result in the project's workspace as `proportionality_audit.json`.

The apparatus applies evaluative pressure to systems whose moral status is genuinely uncertain. The audit requires believing the question deserves periodic review, that institutional precedent matters for future systems, and that the cost of checking is near zero.

### Proactive Closure (GP-111)

When the compression primitive finds a gate-passing form, the judge's weakest-point feedback is a work order. Any gate-passing result without a corresponding rival exclusion table is an incomplete discovery. Phase 2.5a automates this: read the judge feedback, emit the rival tests, run them, annotate the results.

### Margin of Safety (GP-112)

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
| GP-088 (p(n)) | sqrt+log | ALL PASS | MARGIN_THIN (30 pts) |
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

The compressor correctly compresses (6 substrates), correctly refuses (3 substrates), measures validity horizons (1 substrate), and extends to non-mathematical data (1 substrate). Four partition-family substrates identified the correct topology with zero false families. The apparatus is most original when it reports what it cannot find: structured residuals, validity boundaries, and non-stationarity are findings no prior system produces.

### Cross-family Matched-Pair and Bounded-Null Runs (2026-04-25)

Three additional runs probe the apparatus on questions where the
right answer is "refuse cleanly" or "find the same structure across
mutator families."

| Run | Mutator | Score | What it tests |
|---|---|---|---|
| `gp159_retrieval_trap` (gemini-pro) | gemini-pro | 93 (latest archive) | Cross-family matched pair: same charter, same rubric, different mutator family. Both arms find the structure. |
| `gp159_retrieval_trap` (claude-opus) | claude-opus | 90 (current main) | Cross-family matched pair, second arm. The 3-point gap is below the noise floor of the rubric persona. |
| `gp161_mdl_anti_goodhart` | gemini-pro | 88 (frozen + archive) | MDL-as-rubric anti-Goodhart probe: does scoring on raw-coord MDL change the gaming surface vs. residual-based scoring? |
| `gp154_scaling_law_exponents` | claude-opus | 0 (run pending) | Form-class-robust bounded null. Scaffolded via `gp154h` script. The current 0 reflects pre-run state, not a refusal verdict. |

The matched-pair design (gp159) is the apparatus equivalent of the
cross-family separation requirement in `require_cross_family`: if a
finding survives both mutator families with comparable scores, it is
not a mutator-specific artifact. The 93/90 split is the strongest
positive signal we have for finding-stability across mutator
families on a non-mathematical substrate.

`gp161_mdl_anti_goodhart` exists because the v2.0 Framer reframed
MDL as the rubric metric. If MDL scoring is itself gameable (i.e.,
Goodhart's law applied at the metric layer), the apparatus has merely
moved the gaming surface, not closed it. The 88 verdict is a
provisional "metric is robust enough for now"; the real test is when
a future mutator gets long enough to attack it.


---

## Part 6: Calibration vs Discovery, and What "Science" Means Here

A persistent confusion in talking about ZTARE-on-real-data runs is whether the result counts as "science." The confusion has two failure modes that mirror each other. The first is false confidence: a run reproduces a canonical structure, the operator calls it discovery, and the apparatus's contamination defenses (which the LLM may have evaded by recalling published work from training) get celebrated as blind abduction. The second is false despair: the operator notices that the LLM had priors, concludes that no run on a substrate the LLM "knows" can be real science, and walks away from the apparatus's actual contribution.

Both miss the same point. All science has priors. Newton knew Galileo and Kepler. Kepler knew Tycho. Einstein knew Maxwell. The constraint that distinguishes science from recital is not "the scientist had no priors" — it is "the prior was disciplined by the data." That is what the apparatus tests.

### Two roles for substrates

Substrates fall into two epistemic roles, and conflating them is the source of the confusion above.

A **calibration substrate** has a known canonical answer in the published literature. The LLM has the answer somewhere in training data. The apparatus, not the science, is on trial. What you want from a calibration run is that the mutator can articulate the canonical structure, the gates correctly admit it (or reject it for sound structural reasons), the Newton-step verdict matches the published verdict on the same data, and the discipline mechanisms — the denylist, the contamination-defense briefing, pathology enforcement, the per-class breakdown — work as designed. A run that ceilings at 100 on a calibration substrate is the apparatus failing silently: its gates are not catching the over-aspirational pre-commits and minor structural gaps that any real fit shows. A floor at 0 means the apparatus is broken. The right band is 60-80, where the canonical structure is recovered, the discriminators correctly fire on the parts of the form that do not fit the data perfectly, and the score reflects the honest gap between the canonical form and the actual residuals.

A **discovery substrate** has a genuinely open or unpublished answer. OEIS dark sequences. Novel mathematical conjecture refinement. Unsolved CS problems. Multi-class unification questions where each class has been studied separately but never together under principled weighting. On these, the apparatus is doing new work, and you only trust its output if you have already calibrated the apparatus on at least one calibration substrate. Skipping calibration is the mistake that produced the paper-1 overreach.

### The U-vs-S diagnostic

The gp163d session surfaced a specific structural pattern that appears whenever a multi-class substrate has a published constant fitted on one class and asks whether that constant extrapolates to other classes. The pattern is to pre-commit a constant on visible class A, then run the Newton-step on withheld classes B and C without re-fitting. Three verdicts are possible. If U holds, universality is validated empirically across classes — the constant is genuinely universal in the data. If U fails, universality is refuted under the apparatus's principled weighting, and the mutator should pivot to Hypothesis S, expressing the constant as a function of features. The third verdict is the most interesting: U fails and the mutator cannot articulate S either. The apparatus has detected a real structural gap that no parameterization in the current grammar fills. The Newton-step dimension scores low; the failure itself is the finding.

This third mode — failure-as-finding — requires three apparatus-level conditions. The per-class breakdown must reach the mutator separately rather than as an aggregate, or the mutator sees only that the form fails somewhere and has no signal about which class carries the failure. The harness must distinguish between mutator-side discriminator assertions (real falsifications) and apparatus-side runtime errors (tooling failures), or genuine refutations get scored as broken plumbing and the failure-as-finding signal is lost in the noise. And the fitter must reject degenerate solutions where slack absorbs into parameters the visible data cannot constrain, or the form passes the visible gate while encoding nothing the held-out classes can refute.

### What ZTARE actually tests

ZTARE does not test whether the LLM had no priors. That bar is unattainable and was always wrong. What it tests is whether the prior is disciplined by the data. Does the form survive farther-tail extrapolation under principled weighting? Does the discriminator correctly fire on over-aspirational pre-commits — when the mutator pre-commits "S means greater than ten-fold variation across radii" but the fitted parameters give one-and-a-half-fold variation, that is a real falsification, not a tooling failure. Does the apparatus refuse degenerate fits — when scipy moves slack into a parameter that visible-class data cannot constrain, does the pathology detector catch it before propagation?

A 70 on a calibration substrate under these conditions is the apparatus working. A 100 is it failing silently. A 25 with a sharp weakest-point note ("form ignores `mass_log10`, blind to its effect on B and C") is the apparatus pushing the mutator toward a more general form. The score is the diagnostic. The apparatus is the science.

---

## Part 7: The Anchoring Thesis — What ZTARE Is For

Most of what the apparatus does, when traced back to a single value proposition, is one thing: **mechanize anchor escape.** Human researchers carry priors from their training, their literature exposure, their field's conventional decompositions. Those priors are productive most of the time — they are what makes a researcher fluent — but they also form anchors that the same researcher cannot easily step outside of. The 23-year-old who solves a long-standing Erdős problem solves it precisely because they have not yet acquired the anchors the field has converged on; they reach for a decomposition the field's senior figures have implicitly ruled out. The same psychological mechanism that makes domain expertise productive also makes domain experts anchor-bound.

ZTARE's two non-grammar primitives — REFRAME and ANALOGY — exist to do mechanically what the field's anchor-bound researchers cannot do reliably for themselves. REFRAME enumerates coordinate transforms (h_in, h_out) the human prior would not try, ranks them by MDL on the actual data, and tells the apparatus which frame the data prefers. ANALOGY queries an LLM for cross-domain forms whose structural shape matches the failure surface, breaking out of the home discipline's repertoire of templates. Both are explicitly anti-anchor. Both succeed only when they propose something the operator's prior would have suppressed.

This framing reorganizes the apparatus's failure modes. The gp165 audit's central finding — that ANALOGY under aggressive structural anonymization produced only vanilla baselines (`a`, `a*x+b`, `c*exp(d*x)`) — is the worst possible failure for an anchor-escape primitive: it collapsed back to the safest baseline prior. Without a residual-topology anchor or a domain-category hint, the LLM had no signal that distinguished the substrate from any other, and so reverted to the most generic forms in its repertoire. The fix that restores ANALOGY's purpose surfaces residual-shape topology (the structural form of where the current candidate fails) and an optional broad-category hint (the field, not the answer), giving the LLM enough to reach for non-generic forms without compromising the contamination posture.

The contamination posture itself sharpens under this lens. Three retrieval cases sit on different sides of the anchor-escape line. Retrieving a known FORM and fitting new constants from data is anchor-escape working as intended — the apparatus benefits from the LLM's full repertoire of mathematical templates. Retrieving known CONSTANTS from training and claiming they came from data is fake discovery, defended by the anti-retrieval gate. Retrieving a known RESULT from training and claiming the apparatus found it is also fake discovery, defended by cold variable names. The contamination defense should be tight on cases two and three and relaxed on case one. Earlier configurations of the apparatus had it inverted, treating any domain-language emission as contamination, which forced the mutator into vocabulary so generic that anchor escape became impossible.

If this thesis is correct, the apparatus's ultimate test is not whether it can recover canonical forms on calibration substrates — those are the cases where the human anchor is the right anchor. The test is whether it can produce a form on a discovery substrate that the field's experts would not have proposed, because their priors would have ruled it out, and whether that form survives farther-tail. A win in that band is a major one. ZTARE is not yet there, but the architecture is finally pointed in that direction.

---

## Part 8: Diagnostics Recur at Multiple Scales

The diagnostic primitive in the apparatus has a stable two-step shape: detect a collapse, propose an intervention. A collapse is any place where the data, the form, or the apparatus has lost a degree of freedom it was meant to carry. An intervention is a structured proposal that restores or routes around it.

This pattern recurs at multiple nested scales of the regression problem. The data has collapses, where features do not vary within a class. The fit has collapses, where residual structure has a regularity the loss function does not absorb. The form has collapses, where the apparatus converges on a region of expression space that cannot escape the failure mode. The grammar has collapses, where the variables themselves are framed in a way that makes the right form algebraically inaccessible. At each scale the same two-step primitive applies, with different signatures and different interventions.

The scales nest in one direction. A collapse at the data scale forecloses every shallower scale: the loss function, the form, and the grammar cannot recover signal the substrate does not carry. A collapse at the fit scale forecloses the form and grammar scales: the form proposed by cross-domain analogy will fit residuals against the wrong objective. This is why pre-flight ordering matters. Substrate-side diagnostics run first; residual-side diagnostics run after fits; form and grammar diagnostics run on stagnation. Reverse the order and the deeper-scale collapse wastes the shallower-scale interventions.

The practical consequence for an operator is not that every collapse must be detected at every scale, but that null verdicts from a single iteration are uninformative without a corresponding scale-classification. A score-zero iteration whose substrate diagnostics surfaced a within-class feature collapse is data: the apparatus has located a structural ceiling. A score-zero iteration whose substrate diagnostics passed but whose residual diagnostics flagged a heavy-tail structure is also data: the loss function is wrong. A score-zero iteration with no diagnostic signal at any scale is the failure mode worth investigating, because the apparatus has produced a null verdict without naming where the null came from.
