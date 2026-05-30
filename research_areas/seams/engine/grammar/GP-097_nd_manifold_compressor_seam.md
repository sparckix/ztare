# GP-097 — N-D Manifold Compressor: Dimensional Reduction Before Synthesis

> **Seam metadata** · `seam_id:` GP-097 · `track:` engine · `status:` converged - opened 2026-04-19 00:05:02 EST; converged 2026-0 · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Status

converged — opened 2026-04-19 00:05:02 EST; converged 2026-04-19 00:15:00 EST; spec opened

## ID

GP-097

## Eigenquestion

Should ZTARE compress N-D datasets to 1D manifolds *before* they reach the topology synthesizer — via separation of variables or Buckingham π collapse — rather than upgrading Component D to handle N-dimensional AST composition?

## Problem Statement

ZTARE's topology synthesizer (Component D) was designed for 1D substrates: one independent variable, one dependent variable. KWW (1D) and Langevin (1D) are the live proofs. But real physics substrates are N-D: Z=f(X,Y), pressure = f(volume, temperature), reaction rate = f(concentration, temperature).

Naively feeding N-D data into the current architecture triggers three independent failure modes:

1. **Combinatorial death.** In 1D, depth-1 search is O(|Prims|² × |Ops|). In 2D with variables (u,v), each composition must decide: compose f(u) with g(u), f(v) with g(v), or cross f(u) with g(v). The search tree exponentiates per variable.

2. **Sparsity death (curse of dimensionality).** In 1D, 24 data points give dense coverage. In 3D, 24 points are an empty void. A 9-parameter Padé rational warps to hit all 24 points without revealing its true shape. The farther-tail holdout gate becomes toothless.

3. **Optimizer death.** Levenberg-Marquardt (curve_fit) relies on Jacobian gradients. In N-D with highly nonlinear composed terms, the Jacobian is pathologically singular. You get `Covariance could not be estimated` on 99% of fits.

Any one of these kills the run. Together they are a death sentence for naive N-D synthesis.

## Scope

**Covers:**
- Whether dimensional compression before synthesis is the right architectural choice
- What compression algorithms exist (separation of variables, Buckingham π, dimensional analysis)
- What already exists in the codebase (GP-076 divergence sweep, BIVARIATE_SCALE)
- Whether the compressor should be LLM-guided, deterministic, or hybrid
- Where in the pipeline the compressor sits
- What happens when compression fails (genuinely entangled variables)

**Does not cover:**
- Implementation details (those belong in the spec)
- Changes to Component D's internal AST grammar
- Specific N-D substrates to test first
- Timeline or priority relative to other active work

---

## Existing Codebase Evidence

Two hardcoded compressions already exist, proving the pattern works:

### 1. GP-076 Divergence Sweep (additive separation)

`autoresearch_loop.py:3767-3804`: When Component C detects stagnation in 2D, the code isolates the corrector term `f_true(u,v) - f_dominant(u,v)`, averages residuals across u to isolate the v-dependency, and passes the resulting 1D curve `(v, avg_residual)` to `run_divergence_sweep`. This is a hardcoded Phase 0 additive separator: strip the dominant 2D physics, collapse the error into 1D, run the 1D library.

It also checks whether the corrector varies with u (`_sweep_u_dependent`): if `max(rs) - min(rs) > 0.5`, the corrector is u-dependent and the 1D library is insufficient. This is an embryonic compression-failure detector.

### 2. BIVARIATE_SCALE (multiplicative separation)

`topology_synthesizer.py:67,400-411`: The `BIVARIATE_SCALE` composition command produces `x2 * g(x1)` — a 1D function of x1 scaled linearly by x2. This is a hardcoded multiplicative separator: fit g(x1) using the 1D synthesizer, lift back to 2D with a linear scalar. It explicitly refuses to mix variables inside the AST (`expression = f"{scale_var} * ({a_expr_prefixed})"`).

### What These Prove

Both compressions were built as emergency fallbacks, not as first-class pipeline stages. Both work. The architectural insight: formalize them as a compression phase that runs *before* synthesis, not after failure.

---

## Debate Log

### Turn 1 — Claude (2026-04-19 00:05:02 EST) — Opening: Gemini's three-death analysis accepted; compression-before-synthesis is the right inversion

Gemini Pro's analysis is fundamentally correct. The three deaths (combinatorial, sparsity, optimizer) are real and independent — any one kills the run. The Mungerian inversion is right: don't upgrade Component D to handle N-D math; compress the dataset to 1D before it reaches the synthesizer.

The strongest evidence is internal: GP-076 and BIVARIATE_SCALE already implement this pattern in hardcoded form. Both work. The task is formalization, not invention.

**Architecture proposal: Phase 0 Manifold Compressor**

The compressor sits between evidence loading and the synthesis loop. When an N-D dataset is loaded:

1. **Deterministic sweep** — test three canonical compressions:
   - Multiplicative: Z ≈ g(X₁) · h(X₂). Hold X₂ constant, fit g(X₁), divide out, check if residual is X₁-independent.
   - Additive: Z ≈ g(X₁) + h(X₂). Same procedure, subtract instead of divide.
   - Buckingham π: search for dimensionless ratios (X₁/X₂, X₁·X₂, X₁²/X₂) that collapse the dataset to 1D.

2. **LLM-guided abduction** (if deterministic sweep fails) — the LLM proposes a reduction ansatz based on variable names and data structure. This is the riskiest step: variable names may leak domain knowledge (same problem as DOSE_SCALED → BIVARIATE_SCALE naming fix in GP-078).

3. **Compression-failure gate** — if no compression achieves sufficient 1D collapse (residual after compression is u-dependent beyond threshold), emit a typed failure: `COMPRESSION_FAILED — variables genuinely entangled`. This is GCH at the compression layer, not the synthesis layer.

**Key design question:** Should the compressor be purely deterministic (sweep all canonical compressions), or should it include an LLM-guided step? The LLM step is more powerful but carries contamination risk (variable names → domain retrieval).

**Requesting domain expert review on:**
- Is the three-compression sweep sufficient, or are there canonical N-D compression algorithms missing?
- Is the LLM-guided step a contamination trap?
- What is the right failure mode when compression fails?
- Is there a Buckingham π implementation that doesn't require physical dimension metadata?

### Turn 2 — Munger Multidisciplinary (2026-04-19 00:05:02 EST) — Inversion accepted; but watch for two traps

**Inversion check: passed.** The inverted question was asked correctly. Instead of "how do we make N-D synthesis work?", the framing is "what is the simplest input that would break N-D synthesis?" — and the answer is: any 2D dataset with >20 points. The compression-first architecture dissolves the problem rather than fighting it.

**Man-with-a-hammer warning #1: Buckingham π without dimensions.** Buckingham π requires physical dimension metadata (mass, length, time). ZTARE deliberately strips domain information to avoid contamination. These two constraints contradict. If you add dimension metadata, you've introduced an oracle channel — the dimensions *are* domain knowledge. If you don't add it, Buckingham π degenerates to "try all pairwise ratios," which is just a special case of the deterministic sweep.

**Recommendation:** Drop Buckingham π as a named algorithm. Replace with "pairwise ratio sweep" — try X₁/X₂, X₁·X₂, X₁²/X₂, etc. as candidate collapse variables. This is the mathematical content of Buckingham π without the dimensional metadata requirement. Name it what it does (RATIO_COLLAPSE), not what it references (Buckingham).

**Man-with-a-hammer warning #2: LLM-guided compression is a loaded gun.** The LLM sees variable names. Variable names are domain knowledge. If the LLM reads `pressure` and `temperature`, it will retrieve PV=nRT from its training weights and propose the correct compression — not because it analyzed the data, but because it recognized the domain. This is exactly the retrieval-vs-abduction problem from the GP-090 cage-as-transformer finding.

**Recommendation:** The compressor must be deterministic-only for Phase B science claims. The LLM-guided step can exist as a Phase C accelerator (operator-approved, not pre-registered), but it cannot be part of the core pipeline without contaminating the discovery claim.

**Incentive analysis:** The deterministic sweep has a flat incentive surface — it tries all compressions equally, no preference signal. This is correct for a compression phase. Adding LLM guidance introduces a preference signal derived from training data, which is exactly what the cage architecture is designed to prevent.

**Second-order effect:** If the compressor succeeds, 1D synthesis runs on a compressed manifold. The synthesized law is expressed in compressed coordinates (U = X₁/X₂). Decompressing back to the original variables requires an inverse map. Who writes that map? If the LLM writes it, you have a second contamination channel. If it's deterministic (inverse of the compression), it's safe. This decompression step is missing from the current proposal.

### Turn 3 — Symbolic Regression Expert (2026-04-19 00:05:02 EST) — Exhaustive compression is cheap; don't LLM it

**Pareto front observation:** For 2D datasets with the variable counts ZTARE typically handles (20-50 evidence points, 2-3 independent variables), the number of canonical compressions is small:

- Multiplicative separation: O(N_vars) trials
- Additive separation: O(N_vars) trials
- Pairwise ratio collapse: O(N_vars²) trials — for 3 variables, that's 9 candidate ratios
- Pairwise product collapse: O(N_vars²) trials

Total for a 3-variable problem: ~25 deterministic compressions. Each compression requires one 1D fit (curve_fit on ~20 points). Total wall time: <5 seconds.

**This is the exhaustive-enumeration case.** When the candidate set is finite and small, exhaustive fitting is trivial. Using an LLM to search a space that fits in a for-loop is engineering malpractice (same critique I'd make of using GP for a 26-form library — see my lens point #3).

**Recommendation:** Implement the compressor as a brute-force sweep of all canonical compressions. Rank by residual reduction after compression. Pass the best 1D manifold to the synthesizer. No LLM needed, no contamination risk, wall time negligible.

**Missing compression class: power-law scaling.** Z = X₂^α · g(X₁). This is more general than linear multiplicative (which assumes α=1). Many physical laws have power-law variable dependence. Log-transform both sides: log(Z) = α·log(X₂) + log(g(X₁)). Then additive separation on the log-transformed data isolates α. This should be in the sweep.

**Extrapolation concern:** After compression, the 1D synthesizer finds g(U). The farther-tail holdout evaluates g at U values outside the training range. But U = X₁/X₂ (or whatever the compression map is). The "farther-tail" in compressed space may not correspond to the farther-tail in physical space. The holdout gate needs to know about the compression map to correctly define "extrapolation." This is a non-trivial integration point.

### Turn 4 — Philosophy of Science (2026-04-19 00:05:02 EST) — Compression is observation, not oracle; but failure-mode taxonomy needs sharpening

**Observation vs oracle check:** Is the compression step an observation or an oracle leak?

Verdict: **observation.** The compression step examines the dataset's internal structure — does Z separate into g(X₁)·h(X₂)? — without referencing ground truth beyond the evidence window. Separation of variables is a property of the data, not a property of the answer key. Testing whether a dataset separates multiplicatively is the same epistemological act as testing whether a residual is monotone (Component C). Both are structural observations about data.

**Exception:** If the compression uses variable *names* to select which compression to try first, it becomes oracle-contaminated. "temperature" and "pressure" are domain labels, and domain labels carry theory. The compression must be name-blind — operate on X₁, X₂, not on the original labels.

**Underdetermination warning:** When multiple compressions succeed (the data separates both additively and multiplicatively), the compressor faces genuine underdetermination. The data cannot distinguish the two decompositions. The correct response per Duhem-Quine: **try both.** Pass both 1D manifolds to the synthesizer. Let the farther-tail holdout adjudicate. Do not pick one compression over the other based on visible-window fit — that is the Padé trap at the compression layer.

**Crucial experiment design:** The test case for the compressor should be a substrate where:
- The ground truth is known (sandbox)
- The law is genuinely N-D (not separable along any axis without the right compression)
- The correct compression is non-obvious (not PV=nRT, which any LLM retrieves instantly)

Ideal gas law is a terrible test case for exactly this reason: it's in every training set. A 2D version of a dark OEIS sequence or a synthetic coupled system would be better.

**Degenerating vs. progressive check (Lakatos):** Adding the compressor is progressive if it predicts something novel — specifically, that substrates previously intractable become tractable. If the compressor merely reproduces what the operator already did by hand (choosing BIVARIATE_SCALE), it is machinery without novel prediction. The test: run a 2D substrate end-to-end without operator intervention and see if the compressor autonomously discovers the correct decomposition.

### Turn 5 — Systems Engineering / ML (2026-04-19 00:05:02 EST) — Information budget and separation of concerns

**Oracle contamination analysis:**

The deterministic compression sweep transmits zero bits from ground truth to the model. It tests structural properties (separability) of the input data only. Information budget: 0 bits per iteration. Clean.

The LLM-guided compression transmits an unknown number of bits via variable names. If the LLM recognizes "pressure" and "temperature" from training data and proposes PV/T, it has retrieved the answer, not discovered it. Information budget: potentially many bits, unquantifiable. Contaminated.

**Recommendation:** The deterministic sweep is the only version compatible with the oracle-budget framework. The LLM step must be gated behind a flag (e.g., `allow_llm_compression=False` by default) and cannot be used for Phase B claims.

**Separation of concerns check:**

| Concern | Owner (proposed) | Correct? |
|---|---|---|
| "Can this N-D dataset be compressed to 1D?" | Phase 0 Compressor | Yes — structural observation |
| "Which compression is best?" | Farther-tail holdout on compressed manifolds | Yes — deterministic adjudication |
| "What 1D law fits the compressed manifold?" | Existing synthesizer (Component D) | Yes — no change needed |
| "What is the N-D law in original coordinates?" | Decompression map (deterministic inverse) | Yes — if and only if the compression is invertible |

The decompression step is decisive. If Z = g(X₁/X₂) and the synthesizer finds g(U) = a·exp(-b·U), the reported law must be `a·exp(-b·X₁/X₂)`, expressed in original coordinates. This inversion must be deterministic and exact. If the compression is a log-transform or power-law, the inverse involves exp/roots — verify these are in the AST whitelist.

**GT-dependence check:** The compression sweep in GP-076 (`autoresearch_loop.py:3772`) uses `_cc_f_true` — the ground truth function. This is sandbox-only and GT-dependent. In deployment (no GT), the compression must use only the evidence pairs `(X₁, X₂, Z)`. The existing implementation is a sandbox prototype that uses GT as a convenience. The production compressor must replace `f_true(u,v) - f_dominant(u,v)` with `Z_observed - f_dominant(u,v)`, using the evidence Z values directly. This is a clean swap but must be done explicitly.

**Fail-closed default:** If no compression achieves sufficient 1D collapse (residual variance after compression > threshold), the compressor must emit a typed failure, not silently pass the N-D data to the 1D synthesizer. Sending uncompress-able data to a 1D engine is worse than stopping — it produces a confidently wrong 1D answer.

### Turn 6 — Validator Hardening (2026-04-19 00:05:02 EST) — Gate design for the compression boundary

**Silent default risk:** The most dangerous failure mode is not "compression fails" — it's "compression appears to succeed but loses information." Example: multiplicative separation Z ≈ g(X₁)·h(X₂) produces low residual, but the true law has an X₁·X₂ cross-term. The compression absorbs the cross-term into the g/h residuals, making each 1D fit slightly worse but not triggering the failure gate. The synthesizer finds a form that fits the compressed manifold but misses the coupling.

**Gate proposal:** After compression, compute two residual statistics:
1. **Compression residual**: R_compress = ||Z - g_fit(X₁)·h_fit(X₂)||
2. **Cross-term residual**: R_cross = max over (i,j) of |∂²R/∂X_i∂X_j| (mixed partial of residual)

If R_cross > threshold, the compression has lost coupling information. This is a Goodhart-proof gate because it tests the *structure* of the residual (is there cross-variable coupling?), not its magnitude.

**Frequency threshold:** We have zero empirical runs with N-D substrates through the compressor. The 10% prevalence watermark for gate promotion cannot be met yet. This gate should start as a logged diagnostic, not a hard block, until at least 3 N-D sandbox runs produce empirical data.

**Phasing constraint:** The compressor gate must ship before any N-D synthesis run is claimed as a result. If the gate is absent, you're testing the synthesizer against potentially lossy compression with no quality control. This is the same cage-before-kernel rule from GP-074.

**One-shot risk:** What happens when the compressor picks a bad compression, the synthesizer fits it, the holdout passes (because extrapolation in compressed space doesn't catch the compression error), and the result is published? The defense is: the *decompressed* law must be evaluated against the *original* N-D holdout, not the compressed 1D holdout. The holdout gate must operate in original coordinates. This is non-negotiable.

### Turn 7 — Claude (2026-04-19 00:05:02 EST) — Synthesis and convergence

The six turns converge on a clear direction. Summarizing the consensus:

**Agreed by all reviewers:**

1. **Compression-before-synthesis is correct.** Don't upgrade Component D for N-D; compress to 1D first. The Mungerian inversion holds.

2. **Deterministic-only for Phase B.** The LLM-guided compression step is a contamination vector (variable names → domain retrieval). It must be gated behind a flag, default off. The deterministic sweep is sufficient and cheap (~25 compressions, <5 seconds).

3. **Buckingham π → RATIO_COLLAPSE.** Drop the physics-specific name. The mathematical content (try pairwise ratios as collapse variables) doesn't require dimensional metadata. Name it what it does.

4. **Decompression is decisive.** The synthesized 1D law must be expressed in original coordinates via deterministic inverse of the compression map. The holdout gate must evaluate the decompressed law in original N-D space, not in compressed 1D space.

5. **GP-076 uses GT (f_true) and must be rewritten.** The production compressor uses only evidence pairs (X₁, X₂, Z), not the ground truth function. Clean swap, must be explicit.

6. **Cross-term gate.** After compression, test for residual cross-variable coupling (mixed partial derivatives). Start as logged diagnostic, promote to hard gate after empirical data from ≥3 N-D sandbox runs.

**Open disagreements (need resolution in spec):**

1. **Power-law scaling** (SR expert): Z = X₂^α · g(X₁). Should this be in the initial sweep, or deferred? It requires log-transform preprocessing. Adding it is cheap but expands the sweep from ~25 to ~35 candidates.

2. **Multiple successful compressions** (Philosophy): When both additive and multiplicative separation succeed, try both? Or pick one? The underdetermination argument says try both. The engineering argument says the synthesizer runs are expensive — run the best compression first, try the second only if the first stagnates.

3. **Holdout in compressed vs original space** (Validator Hardening): The hardening expert says holdout must be in original N-D space. The SR expert notes that "farther-tail" in compressed space may not map to farther-tail in physical space. These are the same concern from different angles — the spec must resolve where the holdout gate evaluates.

### Turn 8 — Gemini Pro (2026-04-19 00:08:27 EST) — Inversion of the inversion: Topological Coordinate Descent

Gemini applied the INVERT+COMPRESS heuristic to the Phase 0 proposal itself and found it bloated.

**The false assumption:** To solve an N-D dataset, you must analyze the dimensions together to figure out how they couple before synthesizing.

**The inversion:** Don't analyze them together. Analyze them in strict isolation. Assume they don't couple until forced to.

**Proposed alternative — Topological Coordinate Descent:**

Instead of a new Phase 0 module, run the existing 1D synthesizer N times:

1. **Sweep X (freeze Y):** Pass the dataset to the 1D ZTARE engine targeting only X. The Y-variance is treated as noise. The engine finds the 1D skeleton g(X).
2. **Compute residual:** Subtract (additive) or divide (multiplicative) the dataset by g(X).
3. **Sweep Y (freeze X):** Pass the residual to the 1D engine targeting only Y. Find h(Y).
4. **Assemble:** Compose the two skeletons — Z = g(X) + h(Y) or Z = g(X) · h(Y) — and refit joint parameters via curve_fit.

**Claimed advantages:**
- No new module — orchestration of existing machinery
- All existing gates (farther-tail, Padé trap) apply unchanged
- Entanglement Wall comes for free: if 1D engine can't find g(X) that passes holdout (because X geometry depends on Y), it hits WALL_LIBRARY_INSUFFICIENT — entanglement detected with zero new code
- No LLM contamination — purely deterministic

**Gemini's verdict:** "ZTARE is already an N-D solver, provided you orchestrate the variables sequentially rather than simultaneously."

### Turn 9 — Claude (2026-04-19 00:08:27 EST) — Coordinate descent is right for separable laws but misses ratio collapse

Gemini's inversion is sharp and mostly correct. The coordinate descent architecture is genuinely simpler for additive and multiplicative separation. But it has a blind spot that needs closing.

**Where coordinate descent works:**

Additive: Z = g(X) + h(Y). Sweep X → find g(X) → subtract → residual is h(Y) → sweep Y. Clean.

Multiplicative: Z = g(X) · h(Y). Sweep X → find g(X) → divide → quotient is h(Y) → sweep Y. Clean.

Both of these decompose perfectly under coordinate descent because holding one variable constant isolates a clean 1D function of the other.

**Where coordinate descent fails: ratio collapse.**

Consider Z = f(X/Y) — a law that depends on a dimensionless ratio. Holding Y = Y₀ constant gives f(X/Y₀), which is a clean 1D function of X. The 1D engine finds it. But at Y = Y₁, the engine finds f(X/Y₁) — the *same topological family* with a *different scale parameter*. Subtracting g_Y₀(X) from the Y₁ slice gives a complex residual that is NOT a clean function of Y alone. It's a function of both X and Y₀/Y₁.

The coordinate descent finds g(X) at one Y-slice but can't assemble the Y-dependence from the residual because the Y-dependence is *inside the argument of f*, not outside it. You end up with a different g_Y for each frozen Y value, no clean h(Y), and the assembly step fails.

**What ratio collapse needs instead:**

The pairwise ratio sweep from Turn 1: try U = X/Y, U = X·Y, U = X²/Y, etc. For each candidate U, check if the N-D scatterplot collapses to a 1D curve Z vs U. If it does, pass U to the 1D synthesizer. This is NOT coordinate descent — it tests nonlinear *combinations* of variables, not one variable at a time.

This sweep is still deterministic, still cheap (O(N_vars²) candidates × one curve_fit each), and still zero-contamination. It's just not coordinate descent.

**The synthesis: two-pass architecture.**

Pass 1 — Coordinate Descent (Gemini's proposal): Try sequential isolation (additive, multiplicative). If it works, you're done — no new module needed, just orchestration. This handles the majority of separable physics.

Pass 2 — Ratio Sweep (only if Pass 1 fails): Try pairwise variable combinations as collapse candidates. This requires a small new function (generate candidate ratios, check 1D collapse), but it's ~30 lines, not a Phase 0 module.

Pass 3 — Entanglement Wall (free): If neither pass finds a compression, the 1D engine hits WALL_LIBRARY_INSUFFICIENT. Entanglement detected.

**Key insight from the inversion:** Gemini is right that the Phase 0 framing was bloated. The coordinate descent IS the compressed solution for most cases. The ratio sweep is a fallback for the subset of laws where variables couple through their ratio, not through independent contribution. Both are deterministic, both are cheap, neither requires new architectural layers.

**Remaining question:** In Pass 1, how does the orchestrator decide whether to try additive or multiplicative separation first? Both require a full 1D synthesis run. The simplest answer: try both, keep whichever produces lower residual after reassembly. Two extra synthesis runs are cheap compared to the alternative (building a decision heuristic for which separation to try).

### Turn 10 — Munger Multidisciplinary (2026-04-19 00:08:27 EST) — Coordinate descent is the main road; ratio sweep is a side street

The synthesis in Turn 9 is correct. Two observations:

**1. Ordering by base rate.** What fraction of discoverable physics laws are separable vs. ratio-coupled? The vast majority of textbook laws separate: F = ma, PV = nRT (additive in log space), Q = mcΔT, P = IV. Ratio-coupled laws (Reynolds number, Mach number, Froude number) are important but rarer and almost always involve *known* dimensionless groups — which is precisely the regime where the LLM's training knowledge would make a contaminated contribution.

The coordinate descent should run first not because it's simpler but because it has a higher base rate of success. The ratio sweep is the fallback for the remaining ~20% of cases.

**2. The assembly step is where Goodhart lives.** After coordinate descent finds g(X) and h(Y), you assemble Z = g(X) + h(Y) or Z = g(X) · h(Y). Which composition? Both? The assembly step is a selection problem, and selection problems are where Goodhart's Law strikes. If you pick the composition with lowest visible residual, you're back in the Padé trap at the composition layer.

The fix: evaluate the assembled law on the farther-tail holdout in original N-D space. The composition that passes the holdout in original coordinates is the winner. Not the one with better visible residual.

This is the same principle as the ratio-first heuristic in Layer 5d — test by asymptotic behavior, not by window fit.

### Turn 11 — Gemini Pro (2026-04-19 00:11:22 EST) — Resolving all five open questions

Gemini proposes operational resolutions for each open question:

**Q1 (Y-variance noise trap): Slice, don't project.**
Don't project X across the whole dataset (Y-variance inflates residual). Instead, bin the data by Y: find subsets where Y = y₀ ± ε. Run the 1D synthesizer on that isolated slice to find g(X). Topology check: ensure the same AST topology fits a *different* slice (Y = y₁ ± ε). If topology holds, g(X) is verified. The 1D holdout gates are bypassed during intermediate slicing — gates only evaluate the final assembled N-D equation.

**Q5 (N-D farther-tail holdout): Vector norm from bounding box.**
Define the N-D holdout via Euclidean distance from the evidence bounding box. If visible data is bounded by [X_min, X_max] × [Y_min, Y_max], holdout points must fall at least 1.5× the domain width outside the bounding box in all dimensions simultaneously (e.g., test at X = X_max × 1.5 AND Y = Y_max × 1.5). For Pass 2 ratio sweep (U = X/Y), the holdout tests U values significantly outside observed U_max.

**Q3 (Variable ordering): Try all permutations.**
Since 1D synthesis on a single slice is computationally trivial (~50 fits, <5 seconds), enumerate all permutations. For 2 variables: 2 orderings. For 3 variables: 6 orderings. Pass all assembled candidates to the N-D holdout gate. Let holdout act as the Darwinian selector.

**Q4 (Mixed compositions): Absolutely not.**
Mixed compositions (Z = g(X) + X·h(Y)) are a slippery slope back into Taylor expansion epicycles. Stick strictly to pure additive (Z = g(X) + h(Y)) and pure multiplicative (Z = g(X) · h(Y)) for Pass 1. If both fail, Pass 2 (ratio sweep) catches coupled cases. If Pass 2 fails, hit WALL_ENTANGLEMENT. Maintain strict parsimony.

**Q2 (Sandbox substrate): Synthetic dark function.**
Do not use ideal gas or Navier-Stokes. Generate a synthetic 2D function absent from physics textbooks:
Z = tanh(X)/X + Y²/exp(Y)
This separates additively, features complex 1D topologies, and is completely absent from training data.

### Turn 12 — Validator Hardening (2026-04-19 00:11:22 EST) — Review of Q1-Q5 resolutions: three accepted, two need tightening

**Q1 (Slice not project): Accepted with a gate.**
Slicing is correct — it isolates the X-dependency cleanly. The topology-consistency check across Y-slices is a strong validation step. But the threshold for "same AST topology" needs definition. Does it mean: (a) same expression template with different parameters? (b) same primitive family fingerprint? (c) same node count? Recommend (a) — same expression template. If the topology changes between Y-slices, the law is not separable along X. This is an entanglement signal, not a noise signal.

**Additionally:** bypassing 1D holdout gates during intermediate slicing is correct. The intermediate g(X) is not a final answer — it's a building block. Evaluating it against holdout in 1D is meaningless because the law is N-D. Only the assembled law gets holdout-evaluated.

**Q5 (N-D holdout): Accepted but "1.5×" is arbitrary.**
The 1.5× multiplier is a reasonable starting point but needs empirical calibration. Too small: Padé survives the holdout (rational approximants maintain plausibility for short extrapolation distances). Too large: every candidate fails (no functional form predicts well at 10× the training range). Recommend: start at 1.5×, log the holdout distance at which each candidate first diverges from GT, and calibrate the threshold after 3 sandbox runs.

The "all dimensions simultaneously" requirement is important — it prevents a candidate from passing by extrapolating well in X but poorly in Y. The holdout must generate points in the *corner* of the extended domain, not just along axes.

**Q3 (All permutations): Accepted.**
For 2-3 variables, exhaustive permutation is trivially cheap. For >3, factorial growth becomes relevant (24 permutations for 4 variables, 120 for 5). But the scope excludes >3 variables. Accept.

**Q4 (No mixed compositions): Strongly accepted.**
Mixed compositions violate the parsimony principle. Every additional composition template doubles the candidate space without adding a new topological class. The Ratio Sweep in Pass 2 already covers the case where variables are coupled non-additively and non-multiplicatively. Adding mixed templates is the man-with-a-hammer syndrome: "maybe more templates will help" is the additive-expansion instinct that the cage architecture was built to suppress.

**Q2 (Synthetic substrate): Accepted with one concern.**
Z = tanh(X)/X + Y²/exp(Y) is a good additive-separation test case. But the test suite needs at least three substrates:
1. Additive separable: Z = tanh(X)/X + Y²/exp(Y) ← Gemini's proposal
2. Multiplicative separable: Z = exp(-X²) · sin(Y) / (1 + Y²)
3. Ratio-coupled (Pass 2 test): Z = 1/(1 + exp(-(X/Y)))
4. Entangled (WALL_ENTANGLEMENT test): Z = sin(X·Y) + exp(X/Y)

All four must be synthetic (no training data). The first three should succeed (validate the pipeline). The fourth should hit the wall (validate the entanglement exit).

### Turn 13 — Philosophy of Science (2026-04-19 00:11:22 EST) — Falsifiability check on the full architecture

**The crucial experiment test.** The architecture makes four falsifiable predictions:

1. Pass 1 (coordinate descent) will discover the correct separation for substrates 1 and 2.
2. Pass 2 (ratio sweep) will discover the correct collapse for substrate 3.
3. Pass 3 (entanglement wall) will correctly halt on substrate 4.
4. The assembled law, evaluated on N-D holdout, will pass the farther-tail gate for substrates 1-3 and fail for substrate 4.

If prediction 1 fails on substrate 1, the slicing mechanism is broken.
If prediction 2 fails on substrate 3, the ratio sweep is insufficient.
If prediction 3 fails on substrate 4 (engine produces a confident wrong answer instead of hitting the wall), the entanglement exit has a Goodhart exploit.

**The underdetermination resolution is correct.** Gemini's Q4 answer (no mixed compositions) is philosophically sound. The parsimony constraint is itself a theoretical commitment — Occam's razor as architecture. The alternative (try every composition template) is the degenerating research programme: adding machinery to accommodate observations without making novel predictions.

**One concern on the substrate choice.** Z = tanh(X)/X + Y²/exp(Y) is separable by construction. The real test is not "can the engine separate a separable function?" — that's trivially yes if the slicing works. The real test is: "can the engine tell the difference between a separable function and one that *almost* separates but has a cross-term?" Substrate 5 candidate: Z = tanh(X)/X + Y²/exp(Y) + 0.01·sin(X·Y). The cross-term is small enough that additive separation almost works. Does the engine detect the residual coupling, or does it confidently report an almost-correct additive decomposition?

This is the analogue of the Padé trap at the compression layer: a separable approximation that fits the visible window but diverges under holdout.

### Turn 14 — Systems Engineering / ML (2026-04-19 00:11:22 EST) — Information budget and integration points

**Oracle contamination analysis of Q1 resolution:**

Slicing by Y-value uses only the evidence pairs (X, Y, Z). No GT function is called. The slice operation is a data filter, not a computation — it selects rows from a table. Information budget: 0 bits from GT. Clean.

The topology-consistency check (same AST template across Y-slices) is an observation about the data's structure. Also clean.

**Integration point: the orchestrator.**

The seam has now fully specified the algorithm but has not addressed where the orchestrator sits in the codebase. Three options:

(a) Inside `autoresearch_loop.py` — adds more complexity to an already 4000+ line file.
(b) New module `manifold_compressor.py` — clean separation but adds a file.
(c) Inside `topology_synthesizer.py` — conceptually related to Component D's role.

Recommendation: (b). The orchestrator's job is structurally different from both the synthesis loop and the topology synthesizer. It runs *before* both. It's a preprocessor, not a synthesizer. A new 200-line module with a clean interface (`compress(evidence, ind_vars) → CompressedManifold | EntanglementWall`) is the right separation of concerns.

**The decompression contract:**

The CompressedManifold return type must include:
- The 1D evidence (compressed data points)
- The compression map (e.g., "multiplicative, X first")
- The inverse map (deterministic function that lifts 1D → N-D)
- The compression residual (how much information was lost)

The inverse map is decisive. If the synthesizer finds g(U) = a·tanh(b·U), and the compression was U = X/Y, the decompressed law is Z = a·tanh(b·X/Y). This decompression must be automated and exact — no LLM involvement, no approximation.

### Turn 15 — Claude (2026-04-19 00:11:22 EST) — Final convergence synthesis

All five open questions are resolved. The debate has converged.

**Resolved questions:**

| Q | Resolution | Agreed by |
|---|---|---|
| Q1 (Y-variance) | Slice by Y-bin, don't project. Topology consistency = same expression template across slices. Bypass 1D holdout during intermediate slicing. | All |
| Q2 (Substrate) | Four synthetic substrates: additive, multiplicative, ratio-coupled, entangled. Plus a near-separable stress test (small cross-term). | Phil. of Sci. improved Gemini's proposal |
| Q3 (Ordering) | All permutations. Trivially cheap for 2-3 vars. | All |
| Q4 (Mixed comp.) | No. Strict parsimony. Pass 2 catches non-separable cases. | All (Hardening: "strongly accepted") |
| Q5 (N-D holdout) | Bounding-box extension, 1.5× starting point, calibrate after 3 runs. Test in corners, not just along axes. | Hardening: accepted with calibration note |

**New items from this round:**

1. **Substrate 5 (near-separable stress test):** Z = tanh(X)/X + Y²/exp(Y) + 0.01·sin(X·Y). Tests whether the engine detects a small cross-term or reports a confidently wrong additive decomposition. This is the Padé trap at the compression layer. (Philosophy of Science, Turn 13.)

2. **Orchestrator placement:** New module `manifold_compressor.py` with clean interface: `compress(evidence, ind_vars) → CompressedManifold | EntanglementWall`. (Systems Engineering, Turn 14.)

3. **CompressedManifold contract:** Must include 1D evidence, compression map, inverse map, and compression residual. Inverse map is deterministic and exact. (Systems Engineering, Turn 14.)

4. **Topology consistency definition:** "Same AST topology" = same expression template with different parameters. Not same fingerprint, not same node count. Template identity is the right granularity. (Validator Hardening, Turn 12.)

**Seam status: converged.** All questions resolved. Direction clear. Ready for spec.

## Recommendation

Adopt **Topological Coordinate Descent** as the primary N-D architecture, with a ratio sweep fallback and an entanglement wall exit.

**Architecture:**

```text
  N-D evidence
       │
       ▼
  ┌─────────────────────────────┐
  │  manifold_compressor.py     │
  │                             │
  │  Pass 1: Coordinate Descent │
  │  ├─ Slice by Y-bin          │
  │  ├─ 1D synth on X-slice    │
  │  ├─ Topology consistency    │
  │  │   across Y-slices        │
  │  ├─ Compute residual        │
  │  ├─ 1D synth on Y-residual  │
  │  ├─ Assemble (add / mult)   │
  │  ├─ All variable orderings  │
  │  └─ N-D holdout evaluation  │
  │                             │
  │  Pass 2: Ratio Sweep        │
  │  ├─ Pairwise combinations   │
  │  │   (X/Y, X·Y, X²/Y, ...) │
  │  ├─ 1D collapse check       │
  │  ├─ 1D synth on collapsed U │
  │  └─ Decompress + N-D holdout│
  │                             │
  │  Pass 3: Entanglement Wall  │
  │  └─ WALL_ENTANGLEMENT exit  │
  └─────────────────────────────┘
       │
       ▼
  CompressedManifold {
    evidence_1d,
    compression_map,
    inverse_map,
    compression_residual
  }
       │
       ▼
  Existing 1D synthesizer
  (no changes needed)
```

**Key design decisions (all resolved in debate):**
1. Slice, don't project (Q1)
2. Gates only evaluate final assembled N-D equation, not intermediate slices
3. All variable orderings, exhaustive (Q3)
4. No mixed compositions — strict parsimony (Q4)
5. N-D holdout via bounding-box extension at 1.5×, calibrate after 3 runs (Q5)
6. Five synthetic substrates for validation (Q2 + stress test)
7. New module `manifold_compressor.py` with typed `CompressedManifold` return
8. No LLM involvement — fully deterministic for Phase B
9. Inverse map deterministic and exact — no approximation

**Not in scope (deferred):**
- LLM-guided compression (contamination risk, Phase C only)
- Power-law scaling Z = X₂^α · g(X₁) (Pass 1.5 variant, add later)
- >3 independent variables (address when a real substrate demands it)
- Cross-term gate promotion to hard block (needs ≥3 empirical runs first)

### Turn 16 — Validator Hardening (2026-04-19 00:15:00 EST) — Spec review: three Goodhart traps in the implementation sketch

Reviewed spec at `research_areas/specs/active/GP-097_nd_manifold_compressor_spec.md`. Three issues.

**Trap 1: R² as collapse check in Pass 2 is Goodhart-vulnerable.**

The spec says: "If the scatter collapses to a curve (R² > threshold against a smooth fit), the collapse is valid." R² against a *smooth fit* is exactly the Padé trap. A high-parameter smooth fit will always produce high R² even if the collapse is wrong. The collapse check should be structural, not fit-based: compute the *variance of Z at each U-bin*. If data points at similar U values have similar Z values (low intra-bin variance), the collapse is real regardless of what curve fits. This is the same principle as the topology consistency check in Pass 1 — test structure, not fit quality.

**Trap 2: Bin width for Y-slicing is unspecified.**

The spec's open question 4 says "Need a heuristic." But this isn't optional — if the bins are too wide, the slice contains mixed Y-values and the 1D synthesis fits a blend. If too narrow, each slice has too few points for curve_fit to converge. The heuristic should be: min 5 points per bin, max ceil(N_unique_Y / 3) bins. If the dataset has fewer than 15 points, slicing is infeasible — fall through to Pass 2 directly.

**Trap 3: The compression residual metric is undefined.**

The `CompressedManifold.compression_residual` field exists but the spec doesn't define how to compute it. Without a definition, it'll be implemented as something convenient (e.g., RMSE of g(X_i) fit), which is the wrong quantity. The compression residual should be: the cross-term residual from Turn 6 — max over (i,j) of |∂²R/∂X_i∂X_j|. This is the information lost in the separability assumption, not the quality of the 1D fit.

**All three traps are fixable in the spec without architectural changes.**

### Turn 17 — Symbolic Regression Expert (2026-04-19 00:15:00 EST) — Spec review: the "1D synthesis" step is underspecified

The spec repeatedly says "run the existing 1D synthesizer" on slices. But the 1D synthesizer is the full autoresearch loop: mutator → judge → holdout → structural memory → Component D. Running the full loop on each Y-slice is expensive (10+ iterations × LLM calls). This is not "trivial" as claimed.

**Two options:**

(a) **Full 1D synthesis per slice.** Accurate but expensive. For 2 variables × 2 orderings × 2 compositions (add/mult) = 8 full synthesis runs before the holdout adjudicates. At ~$2-5 per run, that's $16-40 just for the compression phase.

(b) **Library sweep per slice.** Fit all 32 primitives against the slice via curve_fit (no LLM, no judge, no iteration). Pick the best-fitting primitive. This is what `fit_primitive.py` already does. Cost: ~1 second per slice.

**Recommendation:** Option (b) for Pass 1 intermediate slicing. The full 1D synthesizer runs only on the final compressed manifold after assembly, not on intermediate slices. The intermediate step is a *topology identification* step, not a full discovery step. Fitting 32 primitives against a 10-point slice is sufficient to identify which topological family g(X) belongs to.

This changes the cost from $16-40 to <$0.01 for Pass 1, while preserving the full synthesis for the final compressed manifold.

### Turn 18 — Munger Multidisciplinary (2026-04-19 00:15:00 EST) — The simplest thing that could possibly work

**The SR expert is right.** Running the full autoresearch loop per slice is man-with-a-hammer syndrome: "we have a synthesizer, so every problem looks like a synthesis problem." The intermediate slicing step is a *classification* problem — which primitive family fits this slice? — not a *discovery* problem.

**The fix is simpler than anyone has stated.** The intermediate step should be:

1. Take a Y-slice (5+ points of (X, Z)).
2. Run `curve_fit` against all 32 primitives in the library.
3. Pick the top 3 by RMSE.
4. Check topology consistency: do the top 3 match across Y-slices?
5. If yes, the best-fitting primitive family is g(X).
6. Compute residual. Run the same 32-primitive sweep on (Y, residual) to find h(Y).
7. Assemble. Pass to N-D holdout.

The full synthesis (mutator → judge → iterations) only runs on the final compressed manifold if the assembly passes the N-D holdout but the engine wants to refine the discovered law.

**Lollapalooza check:** The spec has three sources of uncontrolled cost compounding: (1) all variable orderings, (2) both additive and multiplicative, (3) full synthesis per slice. Together: 2 orderings × 2 compositions × 10 iterations × $3/iter = $120 for a 2-variable problem. With the library-sweep fix: 2 orderings × 2 compositions × 1 library sweep × $0.00 = effectively free, plus one final synthesis run at $3-5.

### Turn 19 — Claude (2026-04-19 00:15:00 EST) — Spec update: incorporate three fixes

The spec review surfaced three concrete fixes. All improve the spec without changing the architecture.

**Fix 1: Replace R² collapse check with intra-bin variance.**
In Pass 2, the collapse check becomes: bin the U values, compute Z-variance within each bin. If max intra-bin variance < threshold, the collapse is valid. This is structural, not fit-based, and immune to the Padé trap.

**Fix 2: Library sweep for intermediate slicing, not full synthesis.**
Pass 1 intermediate slicing uses `fit_primitive.py` library sweep (32 primitives, curve_fit, ~1 second) instead of the full autoresearch loop. Full synthesis only runs on the final compressed manifold. Cost drops from ~$120 to ~$5 for a 2-variable problem.

**Fix 3: Define compression residual as cross-term metric.**
`compression_residual` = max over (i,j) of |∂²R/∂X_i∂X_j| (approximated via finite differences on the evidence grid). This measures information lost in the separability assumption, not fit quality.

**Additional: Bin width heuristic.**
Min 5 points per bin. Max bins = ceil(N_unique_Y / 3). If dataset has fewer than 15 points, skip slicing and fall through to Pass 2.

**Seam status: converged after spec review.** All three fixes are non-controversial. Updating spec.

## Open Questions

None blocking. Three calibration items to revisit after first empirical runs:
1. Holdout distance multiplier (starting 1.5×, calibrate after 3 runs)
2. Cross-term gate threshold (logged diagnostic first, promote after data)
3. Topology consistency tolerance (exact template match as starting point)
