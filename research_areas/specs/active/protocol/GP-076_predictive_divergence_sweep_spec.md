# GP-076 — Predictive Divergence Sweep: Breaking Corrector Degeneracy Without Oracle Access

## Status

Active — spec revised from converged spec-review debate (Turns 6-14), 2026-04-17

## Seam

research_areas/private/seams/GP-076_predictive_divergence_sweep_seam.md

## Scope

- Deterministic exhaustive library sweep when Component C narrows the candidate set
- Predictive divergence computation: locating the input value where surviving candidates maximally disagree
- Controlled single-point query at the divergence point (not full holdout disclosure)
- Contamination gate: specifying what gets revealed to the mutator versus what stays hidden
- Stagnation trigger and per-run information budget
- Feynman Wall fallback: explicit escalation path when no library form survives the holdout gate
- Generalization to unknown ground truth (the "Dark Data" constraint)

**Out of scope:**
- Changes to Component C's 2-bit descriptor (GP-074)
- Changes to the holdout gate scoring mechanism
- LLM topology proposal for forms not in the library
- Rubric or judge modifications
- Extension of the corrector library itself

---

## Decision

When Component C narrows the corrector library to N candidates that all achieve zero residual on visible data, the system resolves the degeneracy through a predictive divergence sweep: deterministic SciPy fitting of all N forms, identification of the single input point where candidate predictions maximally disagree, a controlled single-point query at that point, and elimination of candidates whose prediction mismatches the observation. The query fires only after three or more consecutive stagnation iterations, with total queries per run capped at floor(run\_length / 3). A contamination gate suppresses the query only when the observation would uniquely determine the GT functional form with no free parameters remaining. If no surviving library form passes the holdout gate after the sweep, the system emits a "library exhausted" signal, suppresses further library sweeps, escalates to LLM topology proposal mode, and forwards all divergence query observations as extended visible evidence to the LLM. This mechanism generalizes to unknown ground truth because it requires only one real observation at one input point — equivalent to designing and running a crucial experiment — not oracle access.

---

## Problem

Sandbox\_15 (GP-074) exposed a structural gap in ZTARE's cognitive gym. The GT corrector `round(0.08*v)` is present in the 26-form library. Component C fires and narrows the candidate set to approximately 7 step/monotone forms. SciPy fitting achieves max\_abs\_residual = 0.0 on visible data (v = 1..16) for all 7 candidates. The holdout gate returns score 0 for all 7 but provides no gradient. The mutator random-walks among 7 geometrically equivalent candidates indefinitely. After 15 iterations: zero progress, zero signal.

**Root cause:** The visible evidence window (v = 1..16) contains exactly one step transition (0→1 at v = 7). Any step function can explain one step. The system has no mechanism to distinguish candidates that agree on visible data but disagree on out-of-sample input.

**What does not work (four-expert consensus):**

1. **Parameter-count-based BIC/MDL sweep** — `round(k*v)` and `Heaviside(v-k)` have identical BIC when parameter counts and residuals are equal. Parameter-count BIC is the wrong primitive for this specific degeneracy class. (Tree-size is a different complexity measure that may break some ties; see Step 2.)
2. **LLM-based selection among library forms** — Exhaustive enumeration of 26 forms with SciPy takes under one second. The LLM adds zero value for finite library selection; its role is upstream topology proposal for novel forms.
3. **Parameter-count complexity penalties / parsimony hard caps** — A correct 4-parameter model is penalized alongside wrong 4-parameter models. Parameter count is a poor proxy for descriptive quality when the library contains structurally heterogeneous forms.

---

## Why It Matters

Corrector degeneracy is not an edge case. Any visible evidence window that contains only one discriminating event will produce multiple zero-residual fits. Without a mechanism to break degeneracy, the mutator stagnates indefinitely on a flat fitness landscape. Stagnation on an in-library case — where the correct answer is already present — represents a qualitative failure of the search architecture. Resolving this class of failure also forces explicit architectural treatment of the related out-of-library failure (the Feynman Wall), which is currently handled only by indefinite stagnation.

---

## Constraints

- **No oracle access.** The system cannot query ground truth as a function; it can only observe the value of f\_true at a specific input point, equivalent to running one experiment.
- **No holdout leakage.** The full holdout set must not be disclosed to the mutator. The divergence query is a single targeted point, not a window into holdout data.
- **Separation of concerns.** Deterministic machinery (SciPy + divergence computation) handles library selection. The LLM's role is topology proposal for forms outside the library; it must not be used for selection within a finite enumerable library.
- **Contamination bound.** The total number of divergence query observations across a run must be bounded. A complete reconstruction of the GT function via accumulated query points is a contamination event.
- **Library scope.** The mechanism applies when the GT corrector is plausibly in the library. When no library form survives the holdout gate, the system must fall back to LLM-proposed novel topologies rather than falsely converging on the best-fitting library form.

---

## Options

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Exhaustive Library Sweep + Predictive Divergence Query** | Fit all N library forms deterministically; find the input point of maximum pairwise prediction disagreement; query f\_true at that point; eliminate candidates that mismatch; escalate to LLM if library exhausted. | Solves the stated problem. Generalizes to unknown GT (one observation = one experiment). Minimum information disclosure per query. Preserves LLM/deterministic separation. Converts indefinite stagnation into bounded exhaustion. | Query count to fully resolve degeneracy is O(N) worst case, O(log N) with optimal selection for step-function libraries; not always one query. Contamination gate requires calibration for libraries where free parameters are recoverable from one point. | **Leading candidate — selected.** |
| **B — Extended Visible Evidence Window** | After stagnation, reveal additional evidence points (e.g., v = 17..20). | Simple to implement. No new mechanism needed. | Reveals more information than necessary. Does not target the region of maximum disagreement; may not break degeneracy if the divergence region is outside the extended window. Weakens cross-sandbox comparability. | Viable but dominated by Option A. |
| **C — Non-Binary Holdout Gate (Scalar Loss)** | Replace binary pass/fail with a scalar loss (fraction of holdout points matched) without revealing which points failed. | Provides gradient signal on every iteration. | Reveals more information than a single targeted query (scalar aggregates across all holdout points). Higher contamination surface. One controlled query (Option A) is a more precise way to provide gradient. | Viable but higher leak surface than Option A. |
| **D — Pareto Front by Expression Tree Size** | Rank candidates by (residual, tree-node count); prefer smaller trees when residuals tie. `Heaviside(v-7)` (3 nodes) ranks above `round(0.08*v)` (4 nodes). | Breaks some ties without any additional queries. Zero information disclosure. Compatible with Option A as a secondary signal. | Does not solve the fundamental underdetermination: two 3-node expressions can still produce identical residuals. Tree-size preference can systematically favor the wrong answer when the correct form is more complex. Insufficient alone. | Useful soft signal; does not replace Option A. Must not hard-promote. |
| **E — Popperian Falsifiability Preference** | Among tied candidates, prefer the form that makes the most out-of-sample predictions (most falsifiable). | Elegant; aligns with scientific methodology. Achieves a similar effect to Option A by favoring bolder predictions. | "Makes the most predictions" is not a well-defined computable property for arbitrary functional forms over arbitrary input domains. Practically, Option A operationalizes this idea more precisely by actually running the falsification attempt. | Elegant but not independently implementable; Option A subsumes it. |

---

## Recommendation

Implement **Option A** with Option D as a soft secondary signal. The predictive divergence sweep is the only mechanism that (a) solves the stated degeneracy, (b) generalizes to unknown GT, (c) preserves the LLM/deterministic separation of concerns, and (d) makes the Feynman Wall failure mode detectable and escapable rather than indefinitely stagnant. Option D (tree-size ranking) informs the priority ordering among candidates entering the query phase; it does not bypass the query or hard-promote a candidate without querying.

---

## Implementation Sketch

### Step 1 — Deterministic library sweep (Component C output)

When Component C narrows the library to N candidates, the sidecar fits all N forms to visible data using SciPy. Cost: milliseconds. No LLM involved. Retain all forms with max\_abs\_residual below a configurable residual threshold ε (e.g., ε = 1.0). This threshold is a single named parameter shared with Step 6.

### Step 2 — Tree-size soft signal (Option D integration)

Apply tree-size ranking to the surviving forms as a **soft prior**, not a hard promotion gate. The smaller-tree candidate is the prior favorite entering the query phase, which informs divergence point selection weighting. Tree-size ranking **never** eliminates candidates from the pool and **never** bypasses the query. Step 3 always runs when multiple zero-residual candidates survive Step 1, regardless of tree-size differences.

### Step 3 — Stagnation detection and query budget

The divergence query fires only after N >= 3 consecutive iterations with no score improvement. Total query budget per run is capped at floor(run\_length / 3). For libraries of 7+ forms and run lengths of 10+ iterations, this is the effective bound; the library size does not bind in practice for realistic parameters. Residual risk: for sufficiently simple GT functions, floor(run\_length / 3) points may be sufficient to reconstruct the function; this risk is acknowledged and bounded, not eliminated.

**Note:** The first N >= 3 iterations before the stagnation trigger fires remain in the baseline stagnation state. Option A does not improve behavior during this pre-trigger window; it converts post-trigger stagnation into bounded exhaustion.

### Step 4 — Divergence point computation

For each pair of surviving candidates, compute the input value where their predictions maximally disagree. The search domain is all integers in [1, v\_max\_extended] where v\_max\_extended is max(visible\_v) + library\_size (e.g., v = 1..23 for visible window v = 1..16 and 7 candidates). For non-step forms or continuous input domains, the search domain extends to the same integer range; continuous optimization is not required in the initial implementation.

Aggregate disagreement at input value v is defined as the sum of pairwise absolute differences: sum\_{i<j} |f\_i(v) - f\_j(v)| across all surviving candidate pairs (i, j). Select the v-value that maximizes this sum. This selects the point that maximally separates the full candidate set, not just the most-disagreeing pair.

### Step 5 — Contamination gate (worst-case suppression)

Before executing the query, apply the contamination gate using worst-case suppression:

1. For each distinct value predicted by the surviving candidates at the proposed query point, enumerate all library forms that would be consistent with visible data plus that predicted value.
2. For each possible observed value, check whether the consistent-form count would drop to exactly 1 AND the surviving form has zero unfitted free parameters.
3. **Suppress** the query if ANY possible observed value would produce unique determination with no free parameters. This is worst-case suppression: if the query *could* uniquely determine the GT under any outcome, suppress it.
4. **Permit** the query if no possible observed value produces unique determination with no free parameters. Family identification with a free parameter remaining is not a contamination event.

**Calibration risk:** For library structures where a free parameter is recoverable from one additional visible point (e.g., `round(k*v)` with k approximately corrector(v)/v), the "family identified, parameter free" threshold may be too permissive. Empirical testing required at implementation time.

### Step 6 — Single-point query and elimination

Evaluate f\_true at the selected input point. Report the observed value to the mutator alongside each surviving candidate's prediction at that point.

Elimination rule: for integer-output library forms (step functions, round/floor/ceiling families), elimination uses exact match. For real-output library forms, elimination uses tolerance-based match with the same residual threshold ε from Step 1: a candidate is eliminated if |predicted\_value - observed\_value| > ε. Using the same threshold as Step 1 prevents inconsistency where a form is retained by Step 1 but eliminated by Step 6 at a different tolerance (or vice versa).

The surviving candidates constitute the champion pool for the next iteration.

*GT-independence note:* In sandbox settings, f\_true is the known GT function. In deployment against real data, f\_true is replaced by "run the experiment at this input value." The mechanism requires one observation, not oracle access to the function.

### Step 7 — Feynman Wall fallback (required component)

When the divergence sweep produces a pool of surviving candidates (not necessarily a unique winner), all candidates in the pool are evaluated against the holdout gate. If one or more candidates survive holdout, the surviving subset becomes the new champion pool and the sweep continues on the next stagnation trigger. If **no** candidate in the pool survives holdout:

1. Write `library_exhausted: true` to the run's workspace state artifact (e.g., `sweep_state.json`). This flag is never reset within a run.
2. The stagnation detector reads this flag before triggering further library sweeps — if set, no further sweeps are triggered.
3. The mutator prompt includes a "library exhausted" notice when the flag is set, triggering LLM topology proposal mode: the mutator is told that no library form survived holdout and a novel functional form is required.
4. All divergence query observations are forwarded as extended visible evidence to the LLM (these are legitimate observations, not oracle leaks; the LLM now has v = 1..16 plus all queried points as training data).
5. The run logger records the iteration at which the flag was set.

This converts indefinite stagnation on an out-of-library case into bounded exhaustion followed by escalation. The Feynman Wall is not eliminated but is now detectable and escapable.

**Scope boundary:** This fallback applies only when the system has entered the library sweep path (Component C has fired and narrowed to N library candidates). When the mutator proposes a novel form not in the library, the library sweep is not invoked, the "library exhausted" signal is not emitted, and the existing holdout gate behavior is unchanged.

---

## Open Questions

1. **Parameter recoverability calibration.** For library structures where a free parameter is recoverable from one additional visible point (e.g., `round(k*v)` with k approximately corrector(v)/v from a single nonzero observation), the contamination gate's "family identified, parameter free" permissive threshold may be too loose. Empirical testing against the specific library structures targeted by ZTARE is required before finalizing the gate threshold. This is a calibration question, not an architectural gap.

2. **Empirical query count characterization.** The O(log N) claim for step-function libraries with optimal divergence point selection is analytically sound for that structure. For the full GP-074 library (non-step forms, non-integer parameters), empirical characterization of the expected query count to fully resolve degeneracy is required. The O(N) worst-case bound holds in all cases.

3. **Integration boundary with Component C.** If the predictive divergence sweep reduces N candidates to 1, Component C's role is effectively subsumed for this iteration. The architectural question of whether Component C remains necessary when the sweep is active, or whether the sweep should be treated as an extension of Component C rather than an independent module, is deferred to implementation.

4. **Forms outside the library (novel topology case).** When the mutator proposes a form not in the library, the exhaustive library sweep does not directly apply. A possible extension — comparing the mutator's novel candidate against all library forms at the divergence point — changes the mechanism from "which library form wins?" to "does any library form beat the mutator's proposal?" The implications of this extension for the separation of concerns constraint are not yet analyzed.

---

## Spec Revision Log

<!-- SPEC_REVISED_FROM_DEBATE 2026-04-17 turns=6-14 -->

**2026-04-17 — Revised from converged spec-review debate (Turns 6-14, 13 flags).**

All 13 flags from the spec-review debate incorporated:
1. Step 2: hard promotion removed, tree-size demoted to soft prior (Flag 1)
2. Step 5: rewritten with worst-case suppression over finite set of possible observed values (Flag 2)
3. Step 3: pre-trigger acknowledgment added (Flag 3)
4. Step 3: library\_size non-binding note added (Flag 4)
5. Open Question 3 (budget exhaustion protocol) resolved: escalate to LLM immediately (Flag 5, merged into Step 7)
6. Step 7: explicit scope boundary for in-library case only (Flag 6)
7. Recommendation section: tree-size as soft signal, not tie-breaker bypassing query (Flag 7)
8. Step 7: pool-vs-unique-champion behavior specified (Flag 8)
9. Step 6: exact-match for integer-output, tolerance-based for real-output, shared ε with Step 1 (Flags 9, 12)
10. Step 4: sum-of-pairwise-differences aggregation specified with explicit domain (Flags 10, 13)
11. Step 7: "library exhausted" signal as workspace state flag with named consumers (Flag 11)
