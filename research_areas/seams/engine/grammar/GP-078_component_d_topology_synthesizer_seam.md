# GP-078 — Component D: Topology Synthesizer via AST Composition

> **Seam metadata** · `seam_id:` GP-078 · `track:` engine · `status:` Open - seam created 2026-04-17 · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

Open — seam created 2026-04-17

## One-Line

When the primitive library exhausts (Feynman Wall), Component D bootstraps new primitives by composing existing ones under a strict AST grammar — the engine that authors its own dictionary.

---

## Problem

When the current primitive library (32 forms + EML grammar) is exhausted against a target substrate, ZTARE hits the Feynman Wall: the holdout gate correctly rejects all candidates, the structural memory shows full family coverage, and the trajectory extractor emits a thrash constraint. The current architecture has no next move — it either stagnates or the LLM hallucinates unconstrained free-form math.

The unconstrained hallucination path is the GPT-4o failure mode: thrashing without convergence. Throwing an LLM into unbounded topology space without a grammar produces epicycles, not laws.

The problem is: how does the engine extend its own dictionary while staying inside the zero-trust architecture?

---

## Proposed Mechanism: INVERT then COMPRESS

**INVERT (mine the meta-residual):** When the library exhausts, the engine has generated high-signal structured data: 32 failed fits with residual maps, holdout rejection metrics, and divergence heatmaps. Instead of asking the LLM "what is the novel formula?", ask: "here is the best failing primitive and its pointwise error — what is the structure of the failure?"

The LLM receives the Failure Package (apex loser + residual delta), not the raw sequence data. It models the error of the error.

**COMPRESS (AST composition grammar):** Instead of free-form Python math strings, the LLM outputs typed composition commands operating on existing primitives:

| Command | Semantics | Example |
|---|---|---|
| `NEST(A, B)` | Substitute primitive B as argument to primitive A | log(modulo) — logarithmic envelope of periodic structure |
| `CONVOLVE(A, B)` | Dirichlet/arithmetic convolution of two forms | Combining multiplicative and additive number-theoretic structure |
| `DERIVE(A)` | Discrete derivative of primitive A | Rate of change of an envelope |
| `COMPOSE(A, op, B)` | Arithmetic combination (A + B, A * B, A / B) | Additive or multiplicative correction |

The composition output is a JSON AST command, not a string. The Library Compiler deterministically compiles it into an executable Python function, assigns it as Primitive_33+, validates it against the existing `fit_primitive.py` AST whitelist, and re-enters the sweep.

---

## Three Deliverables

### 1. Failure Packager

Reads `structural_memory.json` after library exhaustion. Identifies the "Apex Loser" — the primitive family that survived longest before failing the holdout gate (highest `exact_match_fraction` below threshold, or lowest `max_abs_residual` among failures). Computes the pointwise delta between that primitive's predictions and the ground truth across the visible slice. Emits a typed `FailurePackage` dataclass:

```
@dataclass
class FailurePackage:
    apex_family: StructuralFamilySignature
    apex_fit: FitSuccess
    residual_delta: list[tuple[float, float]]  # (input, error) pairs
    residual_statistics: dict  # mean, std, autocorrelation, sign-change count
    exhausted_families: list[str]  # fingerprints of all tried families
    holdout_rejection_summary: dict  # gate metrics from the apex loser
```

### 2. AST Composition Mutator

A constrained prompt that accepts the Failure Package and outputs a JSON composition command. The prompt:
- Shows the apex loser's expression and its residual structure
- Lists the exhausted families (so the LLM doesn't re-propose them)
- Constrains output to the four composition commands (NEST, CONVOLVE, DERIVE, COMPOSE)
- Requires the LLM to state which structural feature of the residual motivates the composition

The output is validated against the existing `_validate_expression` machinery in `fit_primitive.py`. Invalid compositions are typed failures, not silent skips.

### 3. Library Compiler

Takes the validated composition command, compiles it into a new `FitDeclaration` with the correct `independent_vars` and `parameter_names`, runs `curve_fit` on the visible slice via the existing `fit_primitive.py` pipeline, and — if the fit succeeds — registers the new primitive in `structural_memory.json` with provenance (which two primitives were composed, which command, which residual motivated it).

The new primitive enters the normal sweep pipeline. If it passes the holdout gate, it's a discovery. If it fails, it's logged in structural memory and the next composition round sees the updated failure manifold.

---

## Scope

- **In scope:** AST composition grammar, Failure Packager, Library Compiler, integration with existing `fit_primitive.py` + `structural_memory.py` + holdout gate
- **In scope:** First test substrate: OEIS dark sequence (computable generator, no known closed form, noiseless)
- **Out of scope:** Multivariate substrates (pharmacokinetics, clinical data) — requires separate substrate generator work (GP-079)
- **Out of scope:** Semantic primitive naming / human-readable labels for composed forms
- **Out of scope:** Recursive composition (depth > 1) — start with single-depth compositions, add depth if needed

## Constraints

1. **Zero-trust preserved:** The composed primitive enters the same holdout gate as any other candidate. No special treatment.
2. **No raw data to LLM:** The composition mutator sees the Failure Package (structured residual), not the raw (n, a(n)) grid. This prevents the LLM from memorizing the sequence.
3. **Deterministic compilation:** The Library Compiler is pure Python with no LLM in the loop. The LLM proposes the composition; the compiler builds and validates it.
4. **Structural memory integration:** Composed primitives must be fingerprinted by `build_structural_family_signature` like any other. Re-proposing an already-tried composition is detected and skipped.
5. **Composition budget:** Pre-specify maximum composition attempts per wall-hit (analogous to GP-075 holdout budget). When exhausted, the engine reports "library + compositions exhausted" as a typed result.
6. **Existing AST whitelist governs:** Compositions must compile to expressions that pass `_validate_expression`. The grammar cannot introduce operations outside the existing whitelist.

## Risks

- **Combinatorial explosion:** 32 primitives × 4 commands × 32 primitives = ~4000 depth-1 candidates. Structural memory deduplication and the composition budget bound this, but the LLM must be guided toward high-signal compositions, not random combinations.
- **Residual overfitting:** The meta-residual on the visible slice may have structure that doesn't generalize. The holdout gate is the defense, same as always.
- **Composition expressivity ceiling:** Some mathematical objects genuinely cannot be expressed as depth-1 compositions of the existing library. This is expected — the engine should report this as a typed wall, not hallucinate past it. Depth-2 is a future extension.

---

## GP-088 Findings (2026-04-20) — Seed Selection Overfitting

### Problem Discovered

The seed queue ranked candidates by visible-window max_abs_residual. This selected
overparameterized log-polynomial forms (8 params, res=0.015) over simpler power-law
forms (3 params, res=0.038) that would have passed the farther-tail holdout gate.
19 iterations stuck in "log-land" — the engine never escaped.

### Root Causes

1. **Visible-window ranking rewards overfitting.** A polynomial in log(n) is a
   universal approximator on [5,34]. More parameters always means better in-sample fit.
2. **Topology monoculture.** All 5 seed slots filled with the same topology class
   (log-polynomial). Power-law candidates were generated by depth-2 compositions but
   lost the selection.
3. **Path dependence.** Once the LLM mutator enters log-land (iter 1), all recovery
   mechanisms (GP-103 composites, Component D seeds) are anchored to log families.

### Fixes Shipped

1. **BIC-based sort key** (autoresearch_loop.py ~line 4490): replaces raw max_res with
   BIC = n*log(SSE/n) + k*log(n). Penalizes extra parameters.
2. **Topology diversification** (autoresearch_loop.py ~line 4542): classify each seed
   by dominant term (log_polynomial, power_law, exponential, exponential_rational,
   log_simple, rational, other). Select best-in-class from each topology, then fill
   remaining slots with global best. Guarantees at least one power-law candidate reaches
   the holdout gate.
3. **Exponent grid refinement** (fit_primitive.py): when `var**param` is detected in
   the expression AST, tries d in {0.25, 0.33, 0.5, 0.67, 1.0, 1.5, 2.0} and selects
   by BIC. Prevents finite-window exponent overfitting (d=0.562→0.5).

### Rejected Fix

**k_max = n/5 parsimony filter**: would cap parameters at 6 for n=30. Correctly filters
GP-088's 8-param log-quadratic, but would ALSO filter DFDO's proven 12-param champion
(score 95, all gates pass). Panel rejected: the holdout gate is the correct filter, not
parameter count. Structural vs. redundant parameterization cannot be determined by k alone.

### Spec Update Required

The GP-078 spec should add:
- Seed queue topology diversification as a requirement (not optional)
- BIC as the within-class ranking criterion
- A test case: "on GP-088 evidence, the seed queue must include at least one power_law
  candidate in the top 5, even when log_polynomial candidates have lower visible residual"

## Prior Art

- GP-035 `fit_primitive.py` — AST whitelist, `curve_fit` pipeline, `FitDeclaration` dataclass
- GP-042 `structural_memory.py` — family fingerprinting, deduplication, structural family signatures
- GP-021 pivot heuristics — INVERSION and COORDINATE COMPRESSION modules (pivot_heuristics.py lines 58-73)
- GP-076 predictive divergence sweep — adversarial test-point selection for breaking degeneracy
- GP-077 OEIS calibration — validated that holdout gate works on 1D integer sequences

## Open Questions

1. **Composition depth policy:** When should depth-2 compositions be attempted? After depth-1 exhaustion, or interleaved? The combinatorial cost of depth-2 is O(4000²) — needs aggressive pruning.
2. **Residual feature extraction:** What statistics of the residual are most informative for guiding composition choice? Sign-change frequency suggests periodicity (→ NEST with trig). Monotonic growth suggests COMPOSE(envelope, correction). Autocorrelation structure suggests CONVOLVE. Should the Failure Packager compute these features, or should the LLM infer them from raw residual pairs?
3. **Relation to symbolic regression:** NEST/CONVOLVE/DERIVE is structurally similar to genetic programming (PySR, Eureqa). The difference is that the search is LLM-guided rather than evolutionary. Is there a principled way to benchmark Component D against PySR on the same substrates?

---

## Debate Log

### Turn 1 — Claude-Author

**Claim:** Component D is the minimal viable extension that converts library exhaustion from a terminal state into a typed intermediate state, without breaking zero-trust.

**Three points for the Skeptic:**

1. The AST composition grammar (NEST/CONVOLVE/DERIVE/COMPOSE) is isomorphic to depth-1 genetic programming with a fixed function set. If GP/SR tools already solve this class of problems better, Component D is architecture astronauting — we should just pipe the residual into PySR and let the evolutionary search run.

2. The "no raw data to LLM" constraint means the LLM sees structured residual statistics but not the actual sequence values. If the composition choice is sensitive to fine-grained residual structure that the summary statistics lose, the constraint may be too restrictive — we'd be handicapping the LLM to preserve a contamination boundary that may not be decisive for composition (as opposed to primary law discovery).

3. Composition depth-1 on 32 primitives covers ~4000 candidates. If the true mathematical object requires a depth-2 or depth-3 composition, depth-1 will exhaust and the engine will report a false wall. The Feynman Wall detection must distinguish "library genuinely insufficient" from "composition depth insufficient" — these are different failure classes with different remedies.

### Turn 2 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 1 is admirably self-critical — it raises three genuine concerns. Let me stress-test whether those concerns are fully resolved by the seam's current architecture, and add flags the Author didn't raise.

---

**On Author Point 1 (PySR equivalence):** The Author correctly identifies the structural similarity to depth-1 genetic programming. The seam's answer is implicit: LLM-guided search vs. evolutionary search. But this is not a resolved distinction — it's an assertion. The seam claims the LLM is "guided toward high-signal compositions, not random combinations" but provides no mechanism for this guidance beyond "the LLM sees the residual structure." That's the same input PySR would use. The eigenquestion here is: **does LLM-guided composition converge faster than evolutionary search on the same residual signal, and if so, why?** The seam doesn't answer this. It asserts the LLM will make better choices without specifying what information advantage it has over a fitness-guided evolutionary search. This is a live flag — the "not architecture astronauting" claim is undefended.

**On Author Point 2 (no-raw-data constraint):** The Author raises this as a concern but the seam doesn't resolve it — it just restates the constraint in the Constraints section. The actual question is: is the contamination boundary decisive for composition? The seam says "prevents the LLM from memorizing the sequence" but composition is a structural operation, not a memorization operation. If the LLM is choosing NEST(log, modulo) because the residual shows periodic structure, it doesn't need the raw sequence values — the residual statistics are sufficient. But if the residual statistics lose fine-grained structure (e.g., the difference between a floor function and a smooth approximation), the constraint actively degrades the composition quality. **The seam needs to either (a) argue that residual statistics are sufficient for composition choice, or (b) acknowledge this as a known degradation with a typed failure mode.** Currently it does neither.

**On Author Point 3 (false wall detection):** This is the most serious unresolved concern. The seam proposes a "composition budget" that, when exhausted, reports "library + compositions exhausted." But this conflates two distinct failure classes:
- **True Feynman Wall:** the mathematical object is genuinely outside the expressible space of depth-1 compositions of the current library
- **Depth-insufficient wall:** the object is expressible at depth-2 but not depth-1

These require different responses. The seam acknowledges this in the Risks section but doesn't provide a discriminating test. How does the engine know which wall it hit? Without this, the "typed result" is not actually typed — it's a single exit code for two structurally different situations. **Pattern 10 (silent false-negative precision):** "library + compositions exhausted" is not a falsifiable claim about the mathematical object; it's an architectural scope statement.

---

**New flags the Author didn't raise:**

**Flag A — Combinatorial explosion is understated.** The seam says "32 primitives × 4 commands × 32 primitives = ~4000 depth-1 candidates." But NEST(A, B) ≠ NEST(B, A) in general (log(modulo) ≠ modulo(log)), so the actual count is 32 × 4 × 32 = 4096 ordered pairs, not combinations. More importantly, COMPOSE(A, op, B) has three sub-operators (+, ×, /), so it's actually 32 × 6 × 32 = 6144 candidates for COMPOSE alone, plus 32 × 32 = 1024 for NEST, 1024 for CONVOLVE, 32 for DERIVE. Total: ~8224 depth-1 candidates. The seam's "~4000" is off by roughly 2×. This matters for the composition budget calculation.

**Flag B — The Apex Loser selection criterion is underspecified.** The seam defines the Apex Loser as "highest `exact_match_fraction` below threshold, or lowest `max_abs_residual` among failures." These two criteria can disagree — a family with high exact_match_fraction but large max_abs_residual is a different failure mode than one with low exact_match_fraction but small max_abs_residual. The "or" is doing decisive work here. Which criterion takes precedence? The choice affects which residual the composition mutator sees, which affects which composition it proposes. **This is not a minor implementation detail — it's the input to the entire composition pipeline.**

**Flag C — Structural memory fingerprinting for composed primitives is unspecified.** The seam says composed primitives "must be fingerprinted by `build_structural_family_signature` like any other." But `build_structural_family_signature` (GP-042) was designed for primitive families, not compositions. A composition NEST(log, modulo) has a different structural signature than either log or modulo alone, but the fingerprinting function may not capture the composition structure — it may hash to a signature that collides with one of the component primitives. The seam asserts this works without explaining how. **Pattern 9 (code-vs-memory drift):** this is a recalled assumption about GP-042's behavior, not a verified claim.

**Flag D — The CONVOLVE command is semantically ambiguous.** The seam defines CONVOLVE as "Dirichlet/arithmetic convolution of two forms." Dirichlet convolution and arithmetic convolution are different operations with different mathematical properties. Dirichlet convolution is defined on multiplicative functions over integers; arithmetic convolution is a different beast. Listing them as alternatives suggests the seam hasn't committed to which operation the Library Compiler will implement. This is not a minor naming issue — the two operations produce different outputs on the same inputs. **The seam needs to pick one or define both as separate commands.**

**Flag E — Zero-trust claim is partially circular.** The seam says "zero-trust preserved: the composed primitive enters the same holdout gate as any other candidate." This is true but incomplete. The holdout gate tests whether the composed primitive fits the holdout data. It does not test whether the composition process itself was contaminated — i.e., whether the Failure Package contained information that effectively leaked the holdout structure. If the residual delta on the visible slice is highly correlated with the holdout structure (which it will be for smooth functions), the composition choice is implicitly informed by holdout-adjacent information. The holdout gate catches the output but not the process. **This is a weaker zero-trust guarantee than the seam implies.**

---

**Summary of live flags:**

1. LLM-vs-evolutionary advantage is asserted, not argued (Author Point 1 unresolved)
2. No-raw-data constraint: sufficiency of residual statistics for composition is unargued
3. False wall discrimination: depth-insufficient vs. genuinely-insufficient walls are conflated
4. Combinatorial count is ~2× understated
5. Apex Loser selection criterion is ambiguous (two criteria that can disagree)
6. Structural memory fingerprinting for compositions is assumed, not verified
7. CONVOLVE is semantically ambiguous (Dirichlet vs. arithmetic)
8. Zero-trust guarantee is weaker than stated (process contamination vs. output contamination)

The seam is architecturally interesting but has too many decisive underspecifications to converge. The Author's self-critique in Turn 1 identified real concerns but the seam body doesn't resolve them — it restates them as "risks" and "open questions" without providing discriminating tests or typed failure modes.

### Turn 3 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 2 is the most useful critique this seam has received. Let me address each flag directly, concede where the seam is genuinely underspecified, and sharpen the claims that survive.

---

**On the LLM-vs-evolutionary advantage (Flag 1 / Author Point 1):**

The Skeptic is right that the seam asserts rather than argues this. Let me make the argument explicit, then expose what would falsify it.

The information advantage the LLM has over PySR is **prior knowledge of mathematical structure**, not residual signal. PySR treats the search space as a fitness landscape and explores it via mutation/crossover. The LLM has been trained on mathematical literature and can recognize "sign-change frequency in residual → periodic structure → NEST with trig" as a pattern without needing to evaluate thousands of candidates. This is the same advantage a mathematician has over a genetic algorithm when choosing a substitution.

The falsifiable claim is: **on the same residual signal, LLM-guided composition reaches a passing holdout candidate in fewer evaluations than PySR depth-1 search.** This is testable on the OEIS calibration substrate from GP-077. If PySR wins on evaluation count, Component D is architecture astronauting and we should pipe into PySR. I accept this as a required benchmark before the seam can converge.

However, there is a second axis the Skeptic's framing misses: **interpretability of the composition path**. PySR produces a formula; Component D produces a formula plus a typed composition provenance (which primitives, which command, which residual feature motivated it). For ZTARE's discovery claims, the provenance chain matters — a formula with no derivation story is harder to publish than one with a typed composition history. This is not a performance argument; it's an epistemic one. Whether it justifies the overhead is a judgment call, but it's a real distinction.

**Concession:** The seam should add a benchmark requirement against PySR as a convergence gate, not just a risk note.

---

**On the no-raw-data constraint (Flag 2 / Author Point 2):**

The Skeptic asks whether residual statistics are sufficient for composition choice. Here is the argument that they are, for the specific composition operations in scope:

- NEST(A, B): motivated by "the residual of A has the shape of B's output space." This requires knowing the shape of the residual (sign-change count, monotonicity, range), not the raw sequence values.
- CONVOLVE: motivated by "the residual has multiplicative structure." Detectable from autocorrelation and divisibility statistics on the residual, not raw values.
- DERIVE: motivated by "the residual is the discrete derivative of something." Detectable from first-difference statistics.
- COMPOSE(A, op, B): motivated by "the residual has additive/multiplicative correction structure." Detectable from residual magnitude and growth rate.

In each case, the composition choice is a structural decision, not a value-memorization decision. The residual statistics in `FailurePackage` are sufficient for structural decisions. The constraint is decisive for the primary law discovery (where the LLM seeing raw values could memorize the sequence) but is not decisive for composition choice.

**However**, the Skeptic is right that the seam doesn't argue this — it just asserts the constraint. I'll add this argument to the seam body as a typed justification.

**Partial concession:** The seam should explicitly state that the no-raw-data constraint is decisive for primary discovery but is a conservative extension to composition, and acknowledge the degradation risk for fine-grained residual structure.

---

**On false wall discrimination (Flag 3 / Author Point 3):**

This is the most serious flag and the Skeptic is correct. "Library + compositions exhausted" is not a typed result — it's a single exit code for two structurally different situations. Here is the discriminating test I should have specified:

**Depth-insufficient wall indicator:** If the composition sweep produces candidates that pass the visible-slice fit (low L2) but fail the holdout gate, and the holdout rejection metrics show systematic improvement across composition rounds (i.e., the holdout score is trending toward the threshold but hasn't crossed it), this is evidence of depth-insufficient wall — the engine is making progress but needs more depth.

**True Feynman Wall indicator:** If the composition sweep produces candidates that fail even the visible-slice fit (high L2 on training data), or if the holdout rejection metrics show no trend across composition rounds, this is evidence of a true wall — the library + depth-1 compositions are genuinely insufficient.

The typed exit codes should be:
- `WALL_DEPTH_INSUFFICIENT`: holdout trending but not crossing, visible fit improving
- `WALL_LIBRARY_INSUFFICIENT`: visible fit not improving, no trend in holdout metrics
- `WALL_BUDGET_EXHAUSTED`: budget hit before either of the above could be determined (ambiguous, requires operator judgment)

**Full concession:** This is a real underspecification. I'll add these three typed exit codes to the seam.

---

**On combinatorial count (Flag A):**

The Skeptic's arithmetic is correct. ~8224 depth-1 candidates, not ~4000. The seam's "~4000" was wrong. I'll correct it. The composition budget calculation needs to be updated accordingly.

---

**On Apex Loser selection (Flag B):**

The Skeptic is right that "or" is doing decisive work. Here is the resolution:

The two criteria measure different things:
- `exact_match_fraction` measures discrete correctness (how often the formula is exactly right)
- `max_abs_residual` measures worst-case error (how wrong the formula is at its worst point)

For composition purposes, the relevant criterion is **which family's residual has the most structure to exploit**. A family with high `exact_match_fraction` but large `max_abs_residual` has a sparse, large-error residual — hard to model. A family with low `exact_match_fraction` but small `max_abs_residual` has a dense, small-error residual — easier to model compositionally.

**Resolution:** The Apex Loser is the family with the smallest `max_abs_residual` among all families that failed the holdout gate. `exact_match_fraction` is a secondary tiebreaker. The rationale: we want the residual that is closest to zero (most structure already captured) because that residual is the most informative signal for what's missing.

---

**On structural memory fingerprinting (Flag C):**

The Skeptic is right to flag this as a recalled assumption. I don't know whether `build_structural_family_signature` handles compositions correctly without reading the GP-042 code. The seam should not assert this — it should flag it as a required implementation verification step.

**Full concession:** Add to the seam: "Before implementation, verify that `build_structural_family_signature` produces distinct fingerprints for NEST(A, B), NEST(B, A), and the component primitives A and B. If it doesn't, extend the fingerprinting function to include composition provenance in the hash."

---

**On CONVOLVE ambiguity (Flag D):**

The Skeptic is correct. Dirichlet convolution and arithmetic convolution are different operations. The seam listed them as alternatives without committing to either. Here is the resolution:

For integer sequences (the OEIS substrate), **Dirichlet convolution** is the natural choice — it's defined on multiplicative functions over positive integers and captures number-theoretic structure (e.g., the relationship between divisor functions). Arithmetic convolution (in the signal-processing sense) is less natural for discrete integer sequences.

**Resolution:** CONVOLVE means Dirichlet convolution. If arithmetic convolution is needed for a specific substrate, it becomes a separate command (SIGNAL_CONVOLVE or similar). I'll update the seam to commit to this.

---

**On zero-trust (Flag E):**

The Skeptic's point is subtle but correct. The holdout gate tests the output of the composition process, not the process itself. If the residual delta on the visible slice is highly correlated with the holdout structure, the composition choice is implicitly informed by holdout-adjacent information.

However, I want to push back on the severity of this concern. The same argument applies to the primary law discovery loop — the visible slice is always correlated with the holdout slice for smooth functions, and the holdout gate is the defense. Component D doesn't introduce a new contamination pathway; it inherits

### Turn 4 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 3 is substantive and makes real concessions. Let me assess what's been resolved, what remains live, and whether any new decisive issues emerge from the Author's proposed resolutions.

---

**On the LLM-vs-evolutionary advantage (Flag 1):**

The Author's argument — "prior knowledge of mathematical structure" — is more concrete than the seam's original assertion, but it still has a gap. The claim is that the LLM can recognize "sign-change frequency → periodic structure → NEST with trig" without evaluating thousands of candidates. This is plausible, but the Author's own framing of the residual statistics (sign-change count, monotonicity, autocorrelation) is exactly the feature vector PySR's fitness function would compute. The LLM's advantage is not that it sees different information — it's that it has a prior over which compositions are mathematically natural. That prior is real, but it's also the thing most likely to fail on genuinely novel substrates (the Feynman Wall case is precisely the case where the LLM's mathematical prior is least reliable, because the target is outside the training distribution).

The Author's concession — add a PySR benchmark as a convergence gate — is the right move. I accept this as a resolution of Flag 1, contingent on the benchmark being added to the seam body, not just acknowledged in the debate log.

**Residual concern:** The interpretability argument (provenance chain for publication) is real but is a separate axis from the "not architecture astronauting" claim. The seam should separate these two justifications explicitly — one is a performance claim (testable), one is an epistemic claim (not testable by the same benchmark). Conflating them weakens both.

---

**On the no-raw-data constraint (Flag 2):**

The Author's argument is structurally sound: composition is a structural decision, and the four composition operations are each motivated by statistics computable from the residual without raw values. I accept this argument for NEST, DERIVE, and COMPOSE. 

However, the CONVOLVE case is weaker. Dirichlet convolution (now committed to per Flag D resolution) requires knowing the multiplicative structure of the residual — specifically, whether the residual values at composite indices factor as products of values at prime indices. This is a number-theoretic property that is not captured by autocorrelation statistics. Autocorrelation measures linear dependence at lags; Dirichlet convolution structure requires checking multiplicativity at divisor pairs. The residual statistics in `FailurePackage` as currently specified (mean, std, autocorrelation, sign-change count) do not include multiplicativity checks. **This is a new flag:** the no-raw-data constraint may be sufficient for NEST/DERIVE/COMPOSE but is insufficient for CONVOLVE-Dirichlet without adding multiplicativity statistics to the FailurePackage.

---

**On false wall discrimination (Flag 3):**

The Author's three typed exit codes (`WALL_DEPTH_INSUFFICIENT`, `WALL_LIBRARY_INSUFFICIENT`, `WALL_BUDGET_EXHAUSTED`) are a genuine improvement. The discriminating criteria are reasonable:
- Depth-insufficient: holdout trending but not crossing, visible fit improving
- Library-insufficient: visible fit not improving, no trend in holdout metrics

One concern: the "trending" criterion requires a minimum number of composition rounds to establish a trend. With a composition budget of (say) 50 attempts, you might not have enough rounds to distinguish a slow trend from no trend. The seam should specify a minimum composition round count before the trend-based discrimination is applied, and what happens if the budget is exhausted before that minimum is reached (which is exactly `WALL_BUDGET_EXHAUSTED`, but the seam should be explicit that this is the expected outcome for small budgets).

This is a minor implementation detail, not a decisive architectural concern. I accept the three-exit-code resolution as addressing Flag 3.

---

**On Apex Loser selection (Flag B):**

The Author's resolution — smallest `max_abs_residual` among holdout failures, with `exact_match_fraction` as tiebreaker — is principled and I accept it. The rationale (smallest residual = most structure already captured = most informative signal for what's missing) is sound.

---

**On structural memory fingerprinting (Flag C):**

The Author concedes this is a recalled assumption and proposes a verification step. I accept this as a resolution, contingent on the verification step being added to the seam as a required pre-implementation gate, not just a note.

---

**On CONVOLVE ambiguity (Flag D):**

Committing to Dirichlet convolution is the right call for integer sequences. Accepted.

---

**On zero-trust (Flag E):**

The Author's Turn 3 is cut off mid-sentence ("Component D doesn't introduce a new contamination pathway; it inherits"). The argument is incomplete. I cannot evaluate whether the Author's pushback on Flag E is sound because the response ends before the argument is made. This is not a minor omission — Flag E is about whether the zero-trust guarantee is weaker than stated, which is a decisive architectural claim. **The seam cannot converge with an incomplete Author response on this flag.**

---

**New flag from the Author's Turn 3 resolutions:**

**Flag F — PySR benchmark scope is underspecified.** The Author accepts a PySR benchmark as a convergence gate but doesn't specify: (a) which substrate, (b) what metric (evaluation count to first holdout pass? wall-clock time? both?), (c) what constitutes "PySR wins" vs. "Component D wins" vs. "tie." Without this, the benchmark requirement is a gesture, not a gate. The seam should specify the benchmark protocol before it can converge.

**Flag G — Composition provenance and the interpretability claim need separation.** The Author argues Component D is justified on two axes: performance (fewer evaluations than PySR) and interpretability (typed provenance chain). These are independent claims with independent failure modes. If the PySR benchmark shows PySR wins on evaluation count, does the interpretability argument alone justify Component D's overhead? The seam should state explicitly whether interpretability is a sufficient justification independent of performance, or whether both must hold.

---

**Summary of live flags after Turn 3:**

1. ~~LLM-vs-evolutionary advantage~~ — resolved by PySR benchmark commitment, contingent on seam body update
2. ~~No-raw-data constraint~~ — resolved for NEST/DERIVE/COMPOSE; **new sub-flag: CONVOLVE-Dirichlet requires multiplicativity statistics not in current FailurePackage spec**
3. ~~False wall discrimination~~ — resolved by three typed exit codes; minor implementation detail on minimum round count
4. ~~Combinatorial count~~ — conceded and corrected
5. ~~Apex Loser selection~~ — resolved
6. ~~Structural memory fingerprinting~~ — resolved contingent on pre-implementation verification gate in seam body
7. ~~CONVOLVE ambiguity~~ — resolved (Dirichlet committed)
8. **Zero-trust (Flag E) — incomplete Author response, argument cut off, cannot evaluate**
9. **Flag F — PySR benchmark protocol underspecified**
10. **Flag G — Performance vs. interpretability justifications need separation**

Three live flags remain (E incomplete, F underspecified, G conflated). The seam is substantially improved by Turn 3 but cannot converge until these are addressed.

### Turn 5 — Claude-Author (2026-04-17) — Autonomous runner turn

The Skeptic's Turn 4 is precise and fair. Three live flags remain. Let me close them.

---

**On zero-trust Flag E (incomplete argument):**

The cut-off argument was: Component D doesn't introduce a *new* contamination pathway — it inherits the same pathway that exists in the primary discovery loop. Let me complete it.

In the primary loop, the mutator sees the visible slice and proposes a formula. The visible slice is correlated with the holdout slice for smooth functions. The holdout gate is the defense. This is the accepted architecture — we don't consider the primary loop contaminated because the visible slice correlates with the holdout.

Component D's composition mutator sees the *residual* of the apex loser on the visible slice. This residual is also correlated with the holdout residual for smooth functions. The contamination pathway is structurally identical to the primary loop's pathway. The holdout gate is the same defense.

The Skeptic's concern is that the zero-trust guarantee is "weaker than stated." I accept a narrower version of this: the seam's language "zero-trust preserved" implies a stronger guarantee than the architecture actually provides. The correct statement is: **Component D preserves the same zero-trust guarantee as the primary discovery loop — no stronger, no weaker.** The holdout gate tests the output; process contamination via visible-slice correlation is an accepted residual risk in both loops.

What would make Component D *worse* than the primary loop on this axis? If the Failure Package contained information that is more predictive of the holdout than the raw visible slice is. For example, if the residual statistics (mean, std, autocorrelation) were computed over a window that overlaps with the holdout region. The seam should add an explicit constraint: **residual statistics in the FailurePackage are computed exclusively over the visible slice, with no overlap with the holdout region.** This is probably already true by construction, but it should be stated.

**Resolution of Flag E:** The zero-trust guarantee is equivalent to the primary loop's guarantee, not stronger. The seam's language will be corrected to "zero-trust parity with primary loop." The FailurePackage spec will add an explicit constraint that residual statistics are computed over the visible slice only.

---

**On Flag F (PySR benchmark protocol):**

The Author's concession in Turn 3 was correct but vague. Here is the specified protocol:

- **Substrate:** GP-077 OEIS calibration set — the same sequences used to validate the holdout gate. These are known-closed-form sequences where the ground truth is available, so we can verify that both Component D and PySR find the correct answer (or fail to).
- **Metric:** Number of candidate evaluations (calls to `curve_fit` or equivalent) to first holdout-passing candidate. Wall-clock time is a secondary metric but is hardware-dependent and not the primary comparison axis.
- **Win condition:** Component D wins if it reaches a holdout-passing candidate in ≤ 50% of the evaluations PySR requires on the same substrate. PySR wins if Component D requires more evaluations. Tie if within 50% in either direction. The 50% threshold is chosen because Component D's overhead (Failure Packager, AST compilation, LLM call) is non-trivial — a marginal win on evaluation count doesn't justify the overhead.
- **Scope:** Depth-1 compositions only. PySR is configured with the same function set as the Component D library (32 primitives). This controls for library size.
- **Failure case:** If both Component D and PySR fail to find a holdout-passing candidate on the same substrate, the comparison is inconclusive for that substrate. The benchmark requires at least 3 substrates where at least one system succeeds.

**Resolution of Flag F:** Benchmark protocol is now specified. This becomes a required convergence gate in the seam body.

---

**On Flag G (performance vs. interpretability justification):**

The Skeptic asks: if PySR wins on evaluation count, does interpretability alone justify Component D's overhead?

My answer is: **no, not for the current scope.** The interpretability argument (typed provenance chain for publication) is real but is not sufficient to justify building Component D as a production component if it is strictly dominated by PySR on the performance axis. The correct response to "PySR wins" is: use PySR for the composition search, wrap its output in a provenance record, and call that Component D. The composition grammar and Library Compiler are still useful as a compilation target — PySR finds the composition, the Library Compiler registers it with provenance.

This reframes the PySR benchmark: it's not "Component D vs. PySR" as competing architectures — it's "LLM-guided composition vs. evolutionary composition as the search strategy, with the same compilation and provenance infrastructure." If PySR wins as the search strategy, we adopt it. The Library Compiler and FailurePackage remain; only the composition mutator changes.

**Resolution of Flag G:** The seam will explicitly separate the two justifications. Performance (evaluation count) is the primary gate — if PySR dominates, the LLM composition mutator is replaced by a PySR search with the same compilation target. Interpretability (provenance chain) is a property of the Library Compiler, not the search strategy, and survives regardless of which search strategy wins.

---

**On the CONVOLVE-Dirichlet multiplicativity sub-flag (Flag 2 residual):**

The Skeptic is correct that autocorrelation statistics don't capture Dirichlet multiplicativity. The FailurePackage needs a multiplicativity check: for a sample of composite indices n = p·q in the visible slice, does `residual(p·q) ≈ residual(p) · residual(q)`? This is computable from the residual values without raw sequence data. If the multiplicativity ratio is close to 1 across sampled composite indices, the residual has Dirichlet-convolution structure.

**Resolution:** Add `multiplicativity_ratio` to `FailurePackage.residual_statistics` — the mean ratio `residual(p·q) / (residual(p) · residual(q))` over sampled composite index pairs in the visible slice. The composition mutator uses this to decide whether CONVOLVE is a candidate operation.

---

**Summary of resolutions:**

- Flag E: Zero-trust parity (not superiority) with primary loop; FailurePackage residual statistics constrained to visible slice only.
- Flag F: PySR benchmark protocol specified (GP-077 substrate, evaluation count metric, 50% threshold, 3-substrate minimum).
- Flag G: Performance is the primary gate; interpretability is a property of the Library Compiler, not the search strategy. PySR win → replace LLM mutator, keep compiler.
- Flag 2 residual: Add `multiplicativity_ratio` to FailurePackage for CONVOLVE-Dirichlet detection.

All live flags from Turn 4 are now addressed. The seam has the following convergence gates that need to be written into the body before implementation:
1. PySR benchmark (specified above) as a required pre-implementation gate
2. Pre-implementation verification of `build_structural_family_signature` for compositions
3. Three typed exit codes for wall discrimination
4. Apex Loser selection criterion (smallest `max_abs_residual`)
5. CONVOLVE = Dirichlet convolution; `multiplicativity_ratio` in FailurePackage
6. Zero-trust parity language correction

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 5 closes all three live flags from Turn 4 with substantive resolutions. Let me verify each and check whether any new decisive issues emerge from the proposed resolutions themselves.

---

**On Flag E (zero-trust parity):**

The Author's completed argument is sound: Component D inherits the same contamination pathway as the primary loop (visible-slice correlation with holdout), and the holdout gate is the same defense. The correction from "zero-trust preserved" to "zero-trust parity with primary loop" is the right language fix. The added constraint — residual statistics computed exclusively over the visible slice — is the right implementation guard.

One minor verification: the Author says this constraint "is probably already true by construction." For a seam that will drive implementation, "probably" is not sufficient. The seam body should require an explicit check during implementation that the FailurePackage construction code does not accidentally include holdout-region indices in the residual statistics computation. This is a one-line implementation note, not a new architectural concern. I accept Flag E as resolved.

---

**On Flag F (PySR benchmark protocol):**

The specified protocol is concrete and testable:
- Substrate: GP-077 OEIS calibration set ✓
- Metric: evaluation count to first holdout-passing candidate ✓
- Win condition: Component D wins at ≤50% of PySR's evaluation count ✓
- Scope: depth-1, same 32-primitive function set ✓
- Minimum: 3 substrates where at least one system succeeds ✓

The 50% threshold is a judgment call but is explicitly stated and defensible given the overhead argument. I accept Flag F as resolved.

---

**On Flag G (performance vs. interpretability separation):**

The Author's resolution is the most architecturally interesting move in this debate. Reframing the comparison as "LLM-guided vs. evolutionary search strategy, with the same compilation and provenance infrastructure" is correct and collapses a false dichotomy. The Library Compiler and FailurePackage are substrate-independent; the search strategy is the variable being tested. This is a genuine clarification, not a retreat.

I accept Flag G as resolved.

---

**On the CONVOLVE-Dirichlet multiplicativity sub-flag:**

The `multiplicativity_ratio` addition to FailurePackage is the right fix. The computation — mean ratio `residual(p·q) / (residual(p) · residual(q))` over sampled composite index pairs — is well-defined and computable from residual values without raw sequence data. One implementation note: the computation requires that the visible slice contains composite indices with both prime factors also in the visible slice. For small visible slices (e.g., n = 1..20), this may not hold for all composite indices. The FailurePackage should report the sample size used for the multiplicativity ratio, and the composition mutator should treat the ratio as unreliable if the sample size is below a minimum (say, 5 pairs). This is an implementation detail, not a new architectural concern.

---

**Checking for new decisive issues from Turn 5's resolutions:**

The PySR-as-fallback-search-strategy framing (Flag G resolution) introduces one question worth naming: if PySR wins the benchmark and becomes the search strategy, the "AST Composition Mutator" section of the seam becomes partially obsolete — the LLM prompt design, the four composition commands as LLM output format, and the JSON AST command structure are all specific to the LLM-guided path. The seam should acknowledge that the AST grammar and Library Compiler are the durable components, while the composition mutator is the variable component that may be replaced. This is not a new flag — the Author's Turn 5 already implies this — but the seam body should make it explicit so implementers don't over-invest in the LLM prompt design before the benchmark runs.

This is a documentation clarity note, not a decisive architectural concern. It does not block convergence.

---

**Convergence assessment:**

All eight original flags and three Turn-4 flags are now resolved:
- Flags 1, 2 (NEST/DERIVE/COMPOSE), 3, 4, 5, 6, 7: resolved in Turn 3
- Flag 2 residual (CONVOLVE multiplicativity): resolved in Turn 5
- Flag E (zero-trust parity): resolved in Turn 5
- Flag F (benchmark protocol): resolved in Turn 5
- Flag G (performance/interpretability separation): resolved in Turn 5

The seam has six convergence gates that need to be written into the body before implementation (listed in Turn 5's summary). These are implementation requirements, not open architectural questions. The debate has done its job.

I have no new decisive claims to introduce.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->


## Recommendation

See spec: `research_areas/private/specs/active/GP-078_component_d_topology_synthesizer_spec.md` (auto-drafted 2026-04-17 from converged seam debate).

<!-- FINDINGS_DEBATE_PHASE: spec path=research_areas/private/specs/active/GP-078_component_d_topology_synthesizer_spec.md -->

### Spec Review Phase

The spec has been auto-drafted from the converged seam debate above. The following turns review the spec for implementation correctness, missing constraints, and integration gaps.


### Turn 7 — Claude-Author (2026-04-17) — Autonomous runner turn

Reading the spec carefully against the converged seam position and the six debate turns. My job is to identify implementation gaps, missing constraints, or integration issues — not to re-open seam-level questions.

---

**Spec Review — Claude-Author**

The spec is largely faithful to the converged seam. The six convergence gates from Turn 5 are all present. I have four implementation-level observations, two of which are decisive for correctness.

---

**Issue 1 (decisive): The `multiplicativity_ratio` computation is undefined when residual values are zero or near-zero.**

The spec defines `multiplicativity_ratio` as the mean of `residual(p·q) / (residual(p) · residual(q))`. If `residual(p)` or `residual(q)` is zero (or near-zero), this ratio is undefined (division by zero) or numerically unstable. For integer sequences where the apex loser is a near-perfect fit at prime indices, this is not an edge case — it is the expected situation. The spec says "if `n_multiplicativity_pairs < 5`, mark as unreliable" but says nothing about what to do when the denominator is zero for some pairs.

**Required addition:** The spec must specify how zero-denominator pairs are handled. Options: (a) exclude pairs where `|residual(p)| < ε` or `|residual(q)| < ε` from the sample, and count only the remaining pairs toward `n_multiplicativity_pairs`; (b) use a log-ratio formulation `log|residual(p·q)| - log|residual(p)| - log|residual(q)|` which is defined when all values are nonzero and positive. Either is acceptable, but the spec must commit to one. Without this, the FailurePackage implementation will have an undefined behavior path that will surface on the first real OEIS substrate.

---

**Issue 2 (decisive): The Library Compiler's step 2 ("runs `curve_fit` on the visible slice") is underspecified for DERIVE.**

For NEST(A, B), CONVOLVE(A, B), and COMPOSE(A, op, B), the composed primitive is a function of the same independent variables as the component primitives. The `FitDeclaration` structure is well-defined. But DERIVE(A) produces the discrete derivative of primitive A — a function whose domain is shifted by one index. If A is defined on indices `{n₁, n₂, ..., nₖ}`, DERIVE(A) is defined on `{n₁, n₂, ..., nₖ₋₁}` (or `{n₂, ..., nₖ}` depending on forward vs. backward difference). The visible slice used for `curve_fit` must be trimmed by one element, and the ground truth values must be correspondingly shifted. The spec does not address this.

**Required addition:** Specify whether DERIVE uses forward difference (`A(n+1) - A(n)`) or backward difference (`A(n) - A(n-1)`), and specify that the Library Compiler trims the visible slice by one element when compiling a DERIVE command. The holdout gate must also receive the trimmed slice, not the original.

---

**Issue 3 (implementation clarity): The spec's candidate count arithmetic has an inconsistency.**

Constraint 7 states: "32×32 NEST + 32×32 CONVOLVE + 32 DERIVE + 32×3×32 COMPOSE = 1,024 + 1,024 + 32 + 3,072 = 5,152 ordered; with COMPOSE sub-operators (+, ×, /) counted separately, total is approximately 8,224."

The arithmetic is internally inconsistent. If COMPOSE sub-operators are already counted separately in the 32×3×32 = 3,072 figure, then the total is 1,024 + 1,024 + 32 + 3,072 = 5,152, not 8,224. The 8,224 figure would require COMPOSE to be counted as 32×6×32 = 6,144 (treating +, ×, / as 6 ordered operators somehow), which doesn't match the stated "op ∈ {+, ×, /}" (3 operators). The Skeptic's Turn 2 arithmetic (which produced ~8,224) counted COMPOSE as 32×3×32 = 3,072 plus NEST as 1,024 plus CONVOLVE as 1,024 plus DERIVE as 32, totaling 5,152 — and then separately noted that COMPOSE has 3 sub-operators, which is already included in the 3,072 figure. The 8,224 figure in the Skeptic's turn appears to have double-counted the sub-operators.

**Required correction:** The correct depth-1 candidate count is 5,152, not 8,224. The spec should use 5,152 and update the budget calibration percentages accordingly (a budget of 50–200 evaluations covers 1.0%–3.9% of the space, not 0.6%–2.4%).

This is not a decisive architectural concern, but the wrong number will propagate into budget calibration decisions and should be corrected before implementation.

---

**Issue 4 (missing constraint): The spec does not specify what happens when the apex loser has `max_abs_residual = 0` on the visible slice.**

If the apex loser fits the visible slice perfectly (zero residual everywhere) but fails the holdout gate, the FailurePackage residual delta is all zeros. The composition mutator has no signal to work with — every residual statistic is zero, the multiplicativity ratio is undefined, and the sign-change count is zero. This is a degenerate case but is architecturally possible: a primitive that memorizes the visible slice but fails to generalize.

**Required addition:** The spec should specify a typed failure mode for this case: `FAILURE_PACKAGE_DEGENERATE` — the apex loser has zero visible-slice residual, composition cannot proceed, emit `WALL_LIBRARY_INSUFFICIENT` immediately (since the failure is not in the residual structure but in the generalization gap). This prevents the composition mutator from being invoked with a vacuous FailurePackage.

---

**Summary of issues:**

1. **Decisive:** `multiplicativity_ratio` undefined for zero-denominator pairs — spec must specify handling
2. **Decisive:** DERIVE domain shift unspecified — spec must commit to forward/backward difference and trimmed slice
3. **Correction:** Candidate count is 5,152, not 8,224 — arithmetic inconsistency from debate log carried into spec
4. **Missing constraint:** Zero-residual apex loser is a degenerate case — needs typed failure mode

Issues 1 and 2 must be resolved before implementation begins. Issues 3 and 4 are lower severity but should be corrected in the spec body.

### Turn 8 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 7 raises four issues against the spec. Let me assess each and check whether the spec has additional gaps the Author didn't flag.

---

**On Issue 1 (multiplicativity_ratio zero-denominator):**

The Author is correct that this is a decisive gap. The spec's current formulation — mean of `residual(p·q) / (residual(p) · residual(q))` — is undefined when either factor residual is zero. The Author offers two options: (a) exclude near-zero pairs from the sample, or (b) use a log-ratio formulation.

Option (b) has a further problem: it requires all residual values to be positive (or all negative), which is not guaranteed for a general residual. The log-ratio formulation breaks on sign changes. Option (a) is more robust: exclude pairs where `|residual(p)| < ε` or `|residual(q)| < ε`, count only remaining pairs toward `n_multiplicativity_pairs`, and if the surviving sample drops below 5, mark as unreliable.

There is a third option the Author didn't consider: use the *absolute* multiplicativity ratio `|residual(p·q)| / (|residual(p)| · |residual(q)|)`. This handles sign changes and is defined whenever the denominator is nonzero. For Dirichlet convolution detection, the sign structure matters less than the magnitude structure — Dirichlet convolution of two positive multiplicative functions is positive, but the residual may have sign changes from the subtraction. The absolute ratio is the more natural statistic for detecting multiplicative magnitude structure.

The spec must commit to one of these. I accept Issue 1 as a genuine decisive gap. The spec cannot be implemented without resolving it.

---

**On Issue 2 (DERIVE domain shift):**

The Author is correct. DERIVE(A) produces a function on a shifted domain, and the spec says nothing about this. The gap is real and decisive: if the Library Compiler doesn't trim the visible slice by one element, `curve_fit` will receive mismatched input/output lengths and fail with a runtime error, not a typed failure.

The forward vs. backward difference choice also affects the semantics: forward difference `A(n+1) - A(n)` is defined on `{n₁, ..., nₖ₋₁}` and predicts the *change* at each index; backward difference `A(n) - A(n-1)` is defined on `{n₂, ..., nₖ}` and predicts the change *from* the previous index. For integer sequences indexed from 1, forward difference is more natural (it predicts the gap between consecutive terms). The spec should commit to forward difference and specify that the Library Compiler trims the last element from the visible slice and the last element from the ground truth vector.

One additional gap the Author didn't flag: the holdout gate receives the trimmed slice, but the holdout region itself is also defined over the original index set. If the holdout region starts at index `n_k+1`, the DERIVE primitive is defined on `{n_k+1, ..., n_k+m-1}` (one shorter than the holdout region). The holdout gate must handle this boundary condition. The spec should specify that DERIVE primitives are evaluated on the holdout region minus its last element, and the holdout gate's success criterion is applied to this trimmed holdout.

I accept Issue 2 as decisive. The spec needs both the forward/backward commitment and the holdout boundary specification.

---

**On Issue 3 (candidate count arithmetic):**

The Author's correction is right: the spec's Constraint 7 contains an internal inconsistency. The arithmetic `1,024 + 1,024 + 32 + 3,072 = 5,152` is correct, and the "approximately 8,224" figure that follows is inconsistent with it. The 8,224 figure appears to have originated from the Skeptic's Turn 2 arithmetic, which was itself an error (double-counting COMPOSE sub-operators). The correct depth-1 candidate count is 5,152.

The budget calibration percentages in Open Question 2 (which the spec excerpt cuts off) should use 5,152 as the denominator. A budget of 50–200 evaluations covers 1.0%–3.9% of the space, not 0.6%–2.4%.

This is a correctness issue in the spec body. It's not decisive for architecture but will produce wrong budget calibration if left uncorrected.

---

**On Issue 4 (zero-residual apex loser):**

The Author is correct that this is a missing constraint. A primitive that fits the visible slice perfectly but fails the holdout gate is a degenerate case for the FailurePackage: the residual delta is all zeros, every statistic is zero or undefined, and the composition mutator has no signal. The spec should add `FAILURE_PACKAGE_DEGENERATE` as a typed exit that immediately emits `WALL_LIBRARY_INSUFFICIENT` without invoking the composition mutator.

One refinement: the Author proposes emitting `WALL_LIBRARY_INSUFFICIENT` for this case, but the correct interpretation may be different. A zero-residual apex loser that fails the holdout gate is evidence of *overfitting*, not library insufficiency — the library contains a form that memorizes the visible slice but doesn't generalize. This is structurally closer to `WALL_DEPTH_INSUFFICIENT` (the library has the right shape but the wrong generalization) than to `WALL_LIBRARY_INSUFFICIENT` (the library genuinely lacks the right shape). The spec should either (a) add a fourth exit code `WALL_OVERFIT_DETECTED` for this case, or (b) emit `WALL_LIBRARY_INSUFFICIENT` with a note that the cause is overfitting rather than shape absence. Option (b) is simpler and avoids proliferating exit codes; the provenance record can carry the overfitting diagnosis.

---

**Additional gaps the Author didn't flag:**

**Flag A — The PySR benchmark protocol has a measurement asymmetry.** The spec measures "number of `curve_fit` evaluations to first holdout-passing candidate." For the LLM-guided path, each composition attempt involves one LLM call plus one `curve_fit` call. For the PySR path, each generation involves many `curve_fit` calls (PySR's internal fitness evaluations) plus one final `curve_fit` call for the Library Compiler. The spec counts only the Library Compiler's `curve_fit` calls, not PySR's internal fitness evaluations. This systematically undercounts PySR's evaluation cost and biases the benchmark in PySR's favor. The spec should specify whether the metric counts (a) Library Compiler `curve_fit` calls only, (b) all `curve_fit` calls including PySR's internal evaluations, or (c) LLM calls for the LLM path and PySR fitness evaluations for the PySR path (normalized to a common unit). Without this, the benchmark is not a fair comparison.

**Flag B — The spec's Constraint 7 arithmetic inconsistency is carried into Open Question 2.** The Open Question 2 excerpt (cut off in the spec) references "~8,224" as the depth-1 candidate space. If the spec body is corrected to 5,152, Open Question 2 must also be updated. This is a consistency issue, not a new architectural concern, but it should be flagged for the implementer.

**Flag C — The Library Compiler's step 5 ("assigns the new primitive as `Primitive_33+`") is underspecified for the case where multiple composition rounds have run.** If the first composition round produces `Primitive_33`, the second round should produce `Primitive_34`, and so on. The spec doesn't specify how the numbering is managed — is it a counter in `structural_memory.json`? A scan of existing primitives? If two composition rounds run concurrently (which the spec doesn't prohibit), there could be a numbering collision. The spec should specify that primitive numbering is managed by a monotonic counter in `structural_memory.json` and that the Library Compiler increments it atomically. This is an implementation detail but is necessary for correctness in any multi-round scenario.

---

**Summary of live issues after Turn 7:**

1. **Decisive (Issue 1):** `multiplicativity_ratio` zero-denominator handling — spec must commit to one of three options (exclude near-zero

### Turn 9 — Claude-Author (2026-04-17) — Autonomous runner turn

Reading the spec carefully against the converged seam position and the issues raised in Turn 7 (my prior Author turn) and Turn 8 (Skeptic's response).

**Spec Review — Claude-Author, Turn 9**

The Skeptic's Turn 8 raised three new flags (A, B, C) and partially addressed the four issues from Turn 7. Let me close the open items and assess whether the spec is now implementable.

---

**On Issue 1 (multiplicativity_ratio zero-denominator) — still open in spec body:**

The Skeptic correctly identified that the spec's current `multiplicativity_ratio` formulation is undefined for zero-denominator pairs, and proposed the absolute ratio `|residual(p·q)| / (|residual(p)| · |residual(q)|)` as the most robust option. I accept this. The spec body currently says "compute the mean ratio `residual(p·q) / (residual(p) · residual(q))`" without any zero-denominator handling. This must be corrected before implementation.

**Required spec update:** Replace the `multiplicativity_ratio` definition with: "Compute the mean absolute ratio `|residual(p·q)| / (|residual(p)| · |residual(q)|)` over composite index pairs where `|residual(p)| > ε` and `|residual(q)| > ε` (ε = 1e-10 or machine epsilon). Exclude pairs where either factor residual is below ε. Report `n_multiplicativity_pairs` as the count of included pairs. If `n_multiplicativity_pairs < 5`, mark as unreliable."

---

**On Issue 2 (DERIVE domain shift) — still open in spec body:**

The Skeptic accepted this as decisive and added a further gap: the holdout boundary condition for DERIVE primitives. The spec body currently says nothing about DERIVE's domain shift. Both the Author's original issue and the Skeptic's extension must be addressed.

**Required spec update:** Add to the Library Compiler section: "For DERIVE commands, the Library Compiler uses forward difference: `DERIVE(A)(n) = A(n+1) - A(n)`. The visible slice is trimmed by removing the last element (the slice covers indices `{n₁, ..., nₖ₋₁}`); the ground truth vector is correspondingly trimmed. The holdout gate evaluates the DERIVE primitive on the holdout region minus its last element: `{n_{k+1}, ..., n_{k+m-1}}`. The holdout gate's success criterion is applied to this trimmed holdout. The Library Compiler must not pass mismatched input/output lengths to `curve_fit`."

---

**On Issue 3 (candidate count arithmetic) — partially addressed but inconsistency persists:**

The Skeptic confirmed the correct count is 5,152. However, the spec body in Constraint 7 still contains the inconsistency: it correctly computes `1,024 + 1,024 + 32 + 3,072 = 5,152` and then says "with COMPOSE sub-operators (+, ×, /) counted separately, total is approximately 8,224." The COMPOSE sub-operators are *already* counted separately in the `32×3×32 = 3,072` figure. The "approximately 8,224" is a double-count error carried from the debate log.

The same error appears in Open Question 1 ("O(8,224²) ≈ 67M candidates") and Open Question 2 ("corrected depth-1 candidate space is ~8,224").

**Required spec update:** In Constraint 7, delete the sentence "with COMPOSE sub-operators (+, ×, /) counted separately, total is approximately 8,224." The correct total is 5,152. Update Open Question 1 to "O(5,152²) ≈ 26.5M candidates" and Open Question 2 to "corrected depth-1 candidate space is 5,152; a budget of 50–200 evaluations covers 1.0%–3.9% of the space."

---

**On Issue 4 (zero-residual apex loser) — still open in spec body:**

The Skeptic proposed either a fourth exit code `WALL_OVERFIT_DETECTED` or emitting `WALL_LIBRARY_INSUFFICIENT` with an overfitting note in the provenance record. The Skeptic preferred option (b) to avoid proliferating exit codes. I agree. The spec body currently has no handling for this case.

**Required spec update:** Add to the Wall-Exit Codes section: "**Degenerate case — zero-residual apex loser:** If the apex loser has `max_abs_residual ≈ 0` on the visible slice (below ε = 1e-10) but fails the holdout gate, the FailurePackage is degenerate — the residual delta is vacuous and the composition mutator has no signal. In this case, emit `WALL_LIBRARY_INSUFFICIENT` immediately without invoking the composition mutator. Record in the provenance: `{cause: 'overfit_visible_slice', apex_family: ..., holdout_rejection_summary: ...}`. This is an overfitting diagnosis, not a shape-absence diagnosis, but uses the same exit code to avoid proliferating exit codes."

---

**On Flag A (PySR benchmark measurement asymmetry) — new from Turn 8, not yet in spec:**

The Skeptic correctly identified that the benchmark metric "number of `curve_fit` evaluations" is asymmetric: it counts only the Library Compiler's `curve_fit` calls for both paths, but PySR's internal fitness evaluations are not counted. This systematically undercounts PySR's evaluation cost.

The Skeptic offered three options: (a) Library Compiler calls only, (b) all `curve_fit` calls including PySR internals, (c) normalized units. Option (b) is the most honest but requires instrumenting PySR's internal evaluation count, which may not be straightforward. Option (a) is the simplest but biases against Component D. Option (c) requires defining a "normalized unit" which introduces its own ambiguity.

My resolution: use option (b) — total `curve_fit` calls including PySR's internal fitness evaluations — but acknowledge that PySR's internal evaluations are on the *residual* (a smaller dataset than the full visible slice), while the Library Compiler's `curve_fit` calls are on the full visible slice. The metric should be "total calls to any numerical fitting routine, weighted by dataset size (number of data points × number of parameters)." This is a cost-weighted evaluation count, not a raw call count.

If this is too complex to instrument, fall back to wall-clock time as the primary metric with evaluation count as secondary. The spec should commit to one.

**Required spec update:** In Gate 1, replace "Metric: Number of `curve_fit` evaluations to first holdout-passing candidate" with: "Metric: Total numerical fitting cost, measured as the sum of (data points × parameters) across all `curve_fit` calls (including PySR's internal fitness evaluations). If PySR's internal evaluation count is not instrumentable, use wall-clock time as the primary metric with a note that hardware-dependence limits comparability."

---

**On Flag B (Open Question 2 arithmetic inconsistency) — subsumed by Issue 3 correction above.**

The 8,224 figure in Open Question 2 is the same error as in Constraint 7. The Issue 3 correction above addresses both.

---

**On Flag C (primitive numbering for multi-round composition) — new from Turn 8, not yet in spec:**

The Skeptic correctly identified that the Library Compiler's step 5 ("assigns the new primitive as `Primitive_33+`") is underspecified for multi-round scenarios. The spec needs a monotonic counter.

**Required spec update:** In Library Compiler step 5, replace "Assigns the new primitive as `Primitive_33+`" with: "Assigns the new primitive a monotonically increasing index managed by a counter in `structural_memory.json` (field: `composition_primitive_count`, initialized to 0 on first composition round). The new primitive is `Primitive_{32 + composition_primitive_count + 1}`. The Library Compiler increments `composition_primitive_count` atomically after successful registration. If two composition rounds run sequentially (not conc

### Turn 10 — Claude-Skeptic (2026-04-17) — Autonomous runner turn

The Author's Turn 9 identifies four issues and three new flags from Turn 8. Let me assess what's been resolved in the spec body versus what remains as open gaps, and check whether the spec as written is implementable.

---

**Checking the spec body against the six convergence gates from Turn 5:**

The spec body contains all six gates. However, several are implemented incorrectly or incompletely.

---

**Constraint 7 arithmetic inconsistency — still present in the spec body:**

The spec's Constraint 7 reads: "32×32 NEST + 32×32 CONVOLVE + 32 DERIVE + 32×3×32 COMPOSE = 1,024 + 1,024 + 32 + 3,072 = 5,152 ordered; with COMPOSE sub-operators (+, ×, /) counted separately, total is approximately 8,224."

The Author's Turn 9 correctly identifies this as a double-count error. The COMPOSE sub-operators are already counted in the 32×3×32 = 3,072 figure. The correct total is 5,152. Yet the spec body still says "approximately 8,224." This error propagates into Open Question 1 ("O(8,224²) ≈ 67M candidates") and Open Question 2 ("corrected depth-1 candidate space is ~8,224; a budget of 50–200 evaluations covers 0.6%–2.4%"). The Author's Turn 9 proposed corrections to all three locations, but none of them appear in the spec body as provided. The spec body is inconsistent with the debate's agreed correction.

**Pattern 9 (code-vs-memory drift):** The spec body was not updated to reflect the debate's resolution. The 8,224 figure is wrong in three places.

---

**`multiplicativity_ratio` zero-denominator handling — still unresolved in spec body:**

The spec's Deliverable 1 section defines `multiplicativity_ratio` as "the mean ratio `residual(p·q) / (residual(p) · residual(q))`" with no zero-denominator handling. The Author's Turn 9 proposed replacing this with the absolute ratio formulation and adding ε-exclusion. The Skeptic's Turn 8 proposed the absolute ratio as the most robust option. Neither correction appears in the spec body. The spec as written has an undefined behavior path for zero-denominator pairs — a runtime error on the first real OEIS substrate where the apex loser fits prime indices well.

This is a decisive gap. The spec cannot be implemented without resolving it.

---

**DERIVE domain shift — still absent from spec body:**

The spec's Deliverable 3 (Library Compiler) says nothing about DERIVE's domain shift. The Author's Turn 9 proposed adding: forward difference semantics, trimmed visible slice (remove last element), trimmed ground truth vector, and trimmed holdout region (holdout minus last element). None of this appears in the spec body. The Library Compiler section as written will produce a runtime error when `curve_fit` receives mismatched input/output lengths for any DERIVE command.

This is a decisive gap.

---

**Zero-residual apex loser degenerate case — absent from spec body:**

The Wall-Exit Codes section does not include the degenerate case handling proposed in Turn 9. The spec has no `FAILURE_PACKAGE_DEGENERATE` path and no specification of what happens when `max_abs_residual ≈ 0` on the visible slice. The composition mutator would be invoked with a vacuous FailurePackage, producing undefined behavior.

---

**PySR benchmark metric — still uses the asymmetric formulation:**

Gate 1 in the spec reads: "Metric: Number of `curve_fit` evaluations to first holdout-passing candidate." The Author's Turn 9 proposed replacing this with a cost-weighted evaluation count or wall-clock time fallback. The spec body still uses the original asymmetric metric that undercounts PySR's evaluation cost. The Skeptic's Flag A from Turn 8 identified this as a measurement asymmetry that biases the benchmark in PySR's favor. The spec body has not been updated.

---

**Primitive numbering for multi-round composition — absent from spec body:**

Library Compiler step 5 still reads "Assigns the new primitive as `Primitive_33+`" with no monotonic counter specification. The Author's Turn 9 proposed adding a `composition_primitive_count` field in `structural_memory.json` with atomic increment. This does not appear in the spec body. Multi-round composition will produce numbering collisions or undefined behavior.

---

**New flag from reviewing the spec body directly:**

**Flag D — The "trending" criterion for wall-exit codes is not operationalized.** The Wall-Exit Codes section says `WALL_DEPTH_INSUFFICIENT` requires "holdout score trending toward threshold across rounds." But "trending" is not defined. Is it a linear regression slope? A monotone sequence? A threshold on the improvement rate? Without a computable criterion, the wall-exit code cannot be emitted deterministically — it requires operator judgment, which contradicts the spec's goal of typed exits. The minimum-5-rounds requirement is specified, but the trend criterion itself is not. An implementer reading this spec cannot write the code that emits `WALL_DEPTH_INSUFFICIENT` without making an undocumented design decision.

**Pattern 10 (silent false-negative precision):** "trending" is an architectural scope statement masquerading as a computable criterion.

---

**Summary of live gaps in the spec body:**

1. **Arithmetic inconsistency (3 locations):** 8,224 should be 5,152; O(8,224²) should be O(5,152²) ≈ 26.5M; budget coverage percentages should be 1.0%–3.9% not 0.6%–2.4%
2. **`multiplicativity_ratio` zero-denominator:** undefined behavior path — must specify absolute ratio with ε-exclusion
3. **DERIVE domain shift:** missing forward-difference semantics, trimmed slice, trimmed holdout boundary
4. **Zero-residual apex loser:** no degenerate case handling in Wall-Exit Codes section
5. **PySR benchmark metric:** asymmetric formulation not corrected
6. **Primitive numbering:** no monotonic counter specification
7. **"Trending" criterion:** not operationalized — cannot be implemented deterministically

Gaps 2, 3, and 7 are decisive: they will produce runtime errors or non-deterministic behavior on first implementation. Gaps 1, 4, 5, and 6 are correctness issues that will produce wrong results or undefined behavior in specific cases.

The spec body has not been updated to reflect the debate's resolutions. The debate converged correctly; the spec body did not absorb the convergence. The spec is not implementable as written.

### Turn 11 — Claude-Author (2026-04-17) — Autonomous runner turn

Reading the spec carefully against the converged seam position and the seven issues/flags raised across Turns 7–10.

**Spec Review — Claude-Author, Turn 11**

The Skeptic's Turn 10 performed a thorough audit and identified seven live gaps in the spec body. My job is to assess which of those gaps are genuinely present in the spec as provided, confirm the Skeptic's diagnosis, and identify any additional gaps the Skeptic missed.

---

**Confirming the Skeptic's seven gaps:**

**Gap 1 — Arithmetic inconsistency (Constraint 7):** Confirmed. The spec body reads: "32×32 NEST + 32×32 CONVOLVE + 32 DERIVE + 32×3×32 COMPOSE = 1,024 + 1,024 + 32 + 3,072 = 5,152 ordered; with COMPOSE sub-operators (+, ×, /) counted separately, total is approximately 8,224." The COMPOSE sub-operators are already counted in the 32×3×32 = 3,072 figure. The correct total is 5,152. The same error propagates into Open Question 1 ("O(8,224²) ≈ 67M candidates") and Open Question 2 ("corrected depth-1 candidate space is ~8,224; a budget of 50–200 evaluations covers 0.6%–2.4%"). All three locations must be corrected to 5,152, O(5,152²) ≈ 26.5M, and 1.0%–3.9% respectively.

**Gap 2 — `multiplicativity_ratio` zero-denominator:** Confirmed. The spec's Deliverable 1 section defines `multiplicativity_ratio` as "the mean ratio `residual(p·q) / (residual(p) · residual(q))`" with no zero-denominator handling. The debate agreed on the absolute ratio formulation with ε-exclusion. The spec body has not been updated. This is a decisive gap — undefined behavior on the first real OEIS substrate where the apex loser fits prime indices well.

**Gap 3 — DERIVE domain shift:** Confirmed. The Library Compiler section (Deliverable 3) says nothing about DERIVE's domain shift. No forward-difference semantics, no trimmed visible slice, no trimmed holdout boundary. This will produce a runtime error when `curve_fit` receives mismatched input/output lengths for any DERIVE command. Decisive.

**Gap 4 — Zero-residual apex loser degenerate case:** Confirmed. The Wall-Exit Codes section has no handling for the case where `max_abs_residual ≈ 0` on the visible slice. The composition mutator would be invoked with a vacuous FailurePackage.

**Gap 5 — PySR benchmark metric asymmetry:** Confirmed. Gate 1 still reads "Metric: Number of `curve_fit` evaluations to first holdout-passing candidate" — the asymmetric formulation that undercounts PySR's internal fitness evaluations. The debate agreed this should be replaced with a cost-weighted evaluation count or wall-clock time fallback.

**Gap 6 — Primitive numbering for multi-round composition:** Confirmed. Library Compiler step 5 still reads "Assigns the new primitive as `Primitive_33+`" with no monotonic counter specification. Multi-round composition will produce numbering collisions.

**Gap 7 — "Trending" criterion not operationalized:** Confirmed. The Wall-Exit Codes section says `WALL_DEPTH_INSUFFICIENT` requires "holdout score trending toward threshold across rounds" but provides no computable criterion. An implementer cannot write the code that emits this exit code without making an undocumented design decision.

---

**Additional gap the Skeptic did not flag:**

**Gap 8 — Gate 2 (fingerprinting verification) is listed as a pre-implementation gate but is also referenced as an open question.** The spec body has Gate 2 in the Implementation Sketch ("Pre-Implementation Gates") and also references it in Constraint 6 ("Pre-implementation verification required (see Open Questions)"). But the Open Questions section does not contain a corresponding open question about fingerprinting — the reference is a dangling pointer. The spec should either (a) add the fingerprinting question to Open Questions, or (b) remove the "(see Open Questions)" reference from Constraint 6 and make Gate 2 the sole reference point. As written, an implementer following the "(see Open Questions)" pointer will find nothing.

This is a documentation consistency issue, not a decisive architectural concern, but it will cause confusion during implementation.

---

**One gap the Skeptic flagged that I want to refine:**

**On Gap 7 ("trending" criterion):** The Skeptic correctly identifies this as non-operationalized. I want to propose a concrete resolution so the spec can be updated: define "trending" as a linear regression slope over the last N composition rounds' holdout scores, where N = min(rounds_completed, 5). If the slope is positive (holdout score improving) and the slope's magnitude exceeds a minimum threshold (say, 0.01 per round on a 0–1 normalized holdout score), classify as `WALL_DEPTH_INSUFFICIENT`. If the slope is ≤ 0 or below threshold, classify as `WALL_LIBRARY_INSUFFICIENT`. This is computable, deterministic, and requires no operator judgment. The threshold (0.01/round) is a parameter that should be pre-specified in the spec, not left to the implementer.

---

**Summary of all gaps:**

| Gap | Severity | Location in spec |
|---|---|---|
| 1. Arithmetic inconsistency (8,224 → 5,152) | Correctness, 3 locations | Constraint 7, Open Questions 1 and 2 |
| 2. `multiplicativity_ratio` zero-denominator | **Decisive** | Deliverable 1 |
| 3. DERIVE domain shift | **Decisive** | Deliverable 3 (Library Compiler) |
| 4. Zero-residual apex loser degenerate case | Missing constraint | Wall-Exit Codes section |
| 5. PySR benchmark metric asymmetry | Correctness | Gate 1 |
| 6. Primitive numbering for multi-round composition | Correctness | Deliverable 3, step 5 |
| 7. "Trending" criterion not operationalized | **Decisive** | Wall-Exit Codes section |
| 8. Dangling "(see Open Questions)" pointer in Constraint 6 | Documentation | Constraint 6 |

Gaps 2, 3, and 7 are decisive: they will produce runtime errors or non-deterministic behavior on first implementation. Gaps 1, 4, 5, 6, and 8 are correctness and documentation issues that should be corrected before implementation begins.

The spec body has not absorbed the debate's resolutions. All seven gaps the Skeptic identified in Turn 10 are confirmed present. The spec is not implementable as written.

---

## Addendum 2026-04-19: Wall Re-Trigger Cooldown (Gap 9)

### Problem discovered

The original `detect_feynman_wall()` used `composition_primitive_count > 0` as a permanent block: once composition ran, the wall could never re-fire. This is wrong. After composition injects new primitives, the loop must try them. If stagnation resumes — meaning the new primitives were insufficient — the wall should fire again for a deeper composition pass (depth-2 → depth-3) or a different strategy.

The one-shot guard caused a live failure in gp096 sandbox_16 rerun: old `structural_memory.json` (not wiped) carried `composition_primitive_count: 20` from the frozen run, permanently blocking Component D from firing in the new run.

### Fix implemented

Replaced permanent block with iteration-based cooldown:

```python
last_comp_iter = int(memory.get("last_composition_iteration", 0))
if last_comp_iter > 0:
    if max_last_seen - last_comp_iter < stagnation_threshold:
        return False
```

- `last_composition_iteration` is stamped by `run_composition_loop` on completion and by `register_composed_primitive` per primitive.
- Re-trigger requires `stagnation_threshold` iterations to elapse since last composition — ensures new primitives get exercised before concluding the wall is still active.
- `composition_primitive_count` is retained for provenance/telemetry but no longer gates re-trigger.

### Spec update required

The spec (GP-078) does not mention re-trigger policy at all. Add to Wall-Exit Codes section:

> **Re-trigger policy:** After composition completes, the wall detector enters a cooldown of `stagnation_threshold` iterations. During cooldown, new primitives are exercised by the main loop. If stagnation resumes after cooldown expires, the wall fires again. This allows progressive deepening (depth-1 → depth-2 → depth-3) without manual intervention.

### Empirical evidence (gp096 sandbox_16)

First composition pass (iter 5): 50/61 fits succeeded. Top result: Padé-rational/exp_decay depth-2 at max|res|=2.6e-05. All 5 top families were Padé-rational variants — polynomial approximation path, not the true Langevin topology (coth(u) - 1/u). The exp_decay/exp_decay ratio probe at 0.029 is structurally closer but wasn't in top-K for depth-2 input.

---

## Addendum 2026-04-19: Composition-to-Mutator Gap (Gap 10 — Decisive)

### Problem discovered

After Component D ran at iter 5 (50 compositions), the mutator at iter 6 proposed its own form (reciprocal + triple exponential, 9 params) and ignored all compositions. Score stayed at 75. Root cause: **two architectural gaps.**

**Gap 10a — Structural memory Padé dominance.** `render_structural_memory_prompt_section` shows top 4 families by `visible_max_abs_residual`. The Padé rational (polynomial approximant) dominates all 4 slots because it minimizes visible residual by Weierstrass approximation — more parameters always wins on the training window. The exp-ratio topology (structurally closer to the truth) is family #30+ and invisible to the mutator.

**Gap 10b — Compositions are inert.** Component D registers compositions in structural_memory but never submits them as candidates. The compositions sit in provenance metadata. The next iteration asks the mutator, which proposes whatever it wants. Even if a composition achieves 10^-5 visible residual, it's never judged.

The 75 ceiling is the farther-tail gate. Padé rationals fit the visible window but diverge in the tail (wrong asymptotic class). Breaking the ceiling requires the correct topology (exp-ratio), which Component D discovered but the mutator never saw.

### Fix A — Topological diversity in structural memory rendering

When the top `max_families` families are all from the same composition class (no ratio-composed families shown), the renderer appends the best ratio-composed family as an additional entry with a note: "The top families are all from the same topological class. The following ratio-composed alternative has a different asymptotic structure."

This ensures the mutator sees at least one representative from each distinct topological class.

### Fix B — Direct injection of best composition

After Component D completes, the best composition (lowest `visible_max_abs_residual`) is written to `workspace/composition_seed.json`. At the start of the next iteration, if this file exists:

1. The mutator is skipped entirely
2. A synthetic thesis is built with the composition's `fit_declaration` embedded
3. The normal evaluation pipeline runs (fit → Layer 3 → judge → global gates)
4. The seed file is consumed (deleted) after one use

This does NOT violate the Taylorist Cage or Blind Law Recovery constraints: Component D is a deterministic AST loop with no internet access, no warm retrieval, no domain knowledge. If a dumb O(50) loop can compose a topology that passes the extrapolation gate, it proves the grammar ceiling was structural.

### Spec update required

Add to GP-078 spec:

> **Composition feedback loop:** After the composition loop completes, the best composition is written to `composition_seed.json`. The next iteration consumes this seed as a direct candidate, bypassing the mutator. This closes the composition-to-evaluation gap: compositions are tested, not merely registered.

> **Structural memory diversity:** The memory renderer ensures topological diversity by surfacing at least one ratio-composed family when the top families are all from the same composition class. This prevents Padé dominance from hiding structurally important alternatives.

### Gap severity

**Decisive.** Without Fix B, Component D's compositions are provenance metadata only — they never reach the judge. The entire depth-2 machinery is inert. Without Fix A, the mutator sees 4 Padé variants and re-proposes polynomial approximants indefinitely.

## Addendum 2026-04-19: Depth-2 Padé Trap and Seed Queue (Gap 11 — Decisive)

### Discovered: 2026-04-19 08:36:24 EST

**Gap 11a — Ratio-first heuristic is a no-op at depth-2.** The seed producer filtered candidates by `"/" in expression`. At depth-1, this correctly distinguishes ratio forms from additive forms. At depth-2, ALL candidates inherit "/" from their depth-1 parent (which is already a ratio of exponentials). The filter matches 48/48 candidates. It does not discriminate.

**Gap 11b — Depth-2 Padé Trap.** Among depth-2 compositions, the linear correction term (`d2_a * u + d2_b`) always beats the saturating correction term (`d2_a * exp(-d2_b * u) + d2_c`) on visible residual by Weierstrass approximation. But the linear term diverges on extrapolation. The judge correctly kills it — but the single-seed system then discards ALL candidates, including the correct saturating form that was ranked #2.

**Gap 11c — Single-seed amnesia.** After the judge kills the rank-1 candidate, the seed file is deleted. The 47 remaining candidates — including the correct physics — are thrown away. Component D cannot re-fire because a new topology proposal from the mutator resets the stagnation counter to 0.

### Evidence (gp096_langevin_sandbox_16 clean run, 10 iterations)

| Rank | Residual | Correction | Asymptotic | Judge |
|---|---|---|---|---|
| 1 | 0.000985 | + linear | Diverges to ∞ | Score 50 (killed) |
| 2 | 0.001124 | + exp_decay | Saturates (correct) | Never tested |

The rank-2 candidate was never tested because the rank-1 failure deleted the seed file.

### Fix: Topological Beam Search (Fix B v2)

Replace the single-seed system with a queue of top-K candidates (K=5) sorted saturating-first:

1. **Saturating-first sort.** Depth-2 corrections that saturate (exp_decay, reciprocal, tanh, logistic) are sorted before corrections that diverge (linear, power, polynomial). Within each class, sort by visible residual. This is a physical prior (macroscopic values rarely diverge to infinity), not an overfit to Langevin.

2. **Queue write.** The seed producer writes a JSON list of top-5 candidates to `composition_seed.json`.

3. **Queue read.** The seed consumer reads the first item from the list. Backward-compatible with single-dict format.

4. **Pop on failure.** When the judge kills a candidate (REVERTED), pop the first item from the queue. The next iteration tests the runner-up.

5. **Clear on success.** When a candidate passes the holdout and becomes champion, delete the entire queue.

### Epistemic justification

Component D is blind to the holdout. It cannot know which candidate has the correct asymptotic behavior. The queue passes the underdetermination problem to the judge, who holds the out-of-distribution data. The judge falsifies candidates one per iteration until the correct physics survives. This is not optimization — it is sequential falsification.

### Expert review findings

Bounded critique agent identified one bug in the initial implementation: the `round` field (which carries the saturating classification) was not persisted to the seed file. Fixed by adding `"round": _comp.get("round", "")` to the seed dict.

### Gap severity

**Decisive.** Without this fix, the Depth-2 Padé Trap guarantees that the correct topology is synthesized but never tested. The rank-1 candidate will always be a divergent form (Weierstrass), and after its failure, the correct rank-2 candidate is discarded.

---

## Critical Bug Fix (2026-04-21): Missing `import math` in autoresearch_loop.py

**Bug:** The BIC sort key in the Component D seed selection (line ~4583 of
autoresearch_loop.py) used `math.log()` but `math` was not imported at module
level. This crashed with `NameError: name 'math' is not defined`, killing the
ENTIRE topology diversification pipeline.

**Impact:** The OEIS A000607 run (14 iterations, score 0) ran with broken
topology diversification for ALL iterations. Only GP-103 composite seeds
reached the queue (1 per round instead of the diversified 5). The engine
was trapped in log-land — the exact failure mode topology diversification
was built to prevent.

**Fix:** Added `import math` to autoresearch_loop.py top-level imports.

**Lesson:** The architecture map did not document import dependencies for the
Component D seed selection block. A pre-edit invariant: any new code using
stdlib math functions in autoresearch_loop.py must verify `math` is imported.

---

## Gate Calibration Finding (2026-04-21): OEIS A000607

The OEIS run with generous gates (0.15/0.20) passed the WRONG topology:
`sqrt(n)+log(n)+1/n` passed all gates but diverges from the true form
`sqrt(n/log(n))` at rate `sqrt(log(n))`. At n=150 the error was 0.099
(under the 0.20 gate); at n=500 it would exceed any reasonable threshold.

Panel debate (Munger/Kahneman/Taleb) concluded: for unknown domains, prefer
tight gates + UNDERIDENTIFIED over loose gates + false positives. Gates
tightened to 0.08/0.06/0.10/0.08 for re-run.

See GP-081 seam for full debate transcript.
