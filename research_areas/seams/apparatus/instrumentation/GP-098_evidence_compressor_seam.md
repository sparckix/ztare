# GP-098 — Evidence Compressor: Preprocessing Warps for Dynamical Systems and Heteroscedastic Noise

> **Seam metadata** · `seam_id:` GP-098 · `track:` apparatus · `status:` open - opened 2026-04-19 09:30:00 EST · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-04-19 09:30:00 EST

## ID

GP-098

## Eigenquestion

Should ZTARE include a deterministic evidence preprocessor that warps data into the coordinate system where the engine's assumptions (static, algebraic, homoscedastic) hold — rather than upgrading the engine's internal assumptions?

## Problem Statement

ZTARE's core engine (Component D + Global Gates + curve_fit) makes three implicit assumptions about evidence.txt:

1. **Static:** Data points are independent samples from Z = f(X). No state depends on prior state.
2. **Algebraic:** The target is a closed-form function of the independent variables.
3. **Homoscedastic:** Noise variance is uniform across the domain.

These assumptions hold for classical thermodynamics, fluid statics, and electromagnetism — ZTARE's current success domain (KWW, Langevin, OEIS). But they break in three specific regimes:

### Regime 1: Dynamical Systems (Time-Derivative Illusion)

If the substrate is a first-order ODE dZ/dt = f(Z, X), the current pipeline treats each (t, Z) pair as an independent sample and tries to find Z = g(t). This produces a trajectory fit (polynomial or exponential), not the governing equation. The extrapolation_gap gate will fail the true physics because it tries to predict Z(t=100) without knowing Z(t=99).

### Regime 2: Heteroscedastic Noise (Homoscedasticity Trap)

If variance scales with magnitude (common in real-world physics: photon counting → Poisson noise, economic data → multiplicative noise), the engine's absolute-residual gates systematically penalize the high-magnitude regime. The farther_tail_saturation_error gate will execute the true physical law, classifying natural variance as "divergent structural error."

GP-097's ratio sweep makes this worse: the intra-bin Z-variance threshold for collapse validation will reject valid ratio collapses when high-value bins naturally exceed the variance threshold.

### The coupling problem

These two regimes are not independent. Numerical differentiation (the proposed fix for Regime 1) amplifies noise — it is an ill-conditioned operation. If the data is also heteroscedastic (Regime 2), differentiation makes the noise profile worse in exactly the high-magnitude region where the gates are strictest. **Fix 1 without Fix 2 creates a new failure mode.**

## Scope

**Covers:**
- Whether a preprocessing compressor is the right architecture (vs. modifying gates/engine)
- Kinematic Compressor: differentiating evidence to convert ODE substrates to static algebra
- Variance-Stabilizing Transforms (VST): warping data to flatten heteroscedastic noise
- Coupling between the two transforms (order of operations, compounding effects)
- Where the preprocessor sits in the pipeline (before GP-097 compressor? after? independent?)
- How to detect which regime applies (noise model selection, ODE detection)

**Does not cover:**
- Changes to Component D's AST grammar (see GP-099)
- Changes to the 1D synthesizer's internal fitting (curve_fit stays L2)
- Higher-order ODEs (d²Z/dt² = ...) — first-order only
- PDEs — fundamentally different problem class
- Specific physical substrates to test first

---

## Existing Codebase Evidence

### 1. Absolute-threshold gates are the vulnerability surface

`global_gates.py` and `gate_harness.py` use absolute residual thresholds (`gate_residual_threshold`, `extrapolation_gap`). These are homoscedastic by design — they compare |Z_predicted - Z_observed| against a fixed epsilon. If the true noise at Z=1000 is 100× larger than at Z=1, every high-Z candidate fails the gate.

### 2. GP-097 inherits the trap

The GP-097 spec's Pass 2 (ratio sweep) uses "intra-bin Z-variance threshold" to adjudicate collapse validity. This threshold is absolute, not relative. Heteroscedastic data will trigger false WALL_ENTANGLEMENT exits.

### 3. No ODE-aware infrastructure exists

The evidence parser (`autoresearch_loop.py`) reads (X, Z) pairs. There is no notion of temporal ordering, state dependence, or derivative computation. The engine treats every dataset as an algebraic relation.

---

## Debate Log

### Turn 1 — Claude (2026-04-19 09:30:00 EST) — Opening: Gemini's inversions are structurally correct but have three blind spots

Gemini's framing: "Don't change the engine to accommodate warped data. Warp the data so the engine's assumptions hold." This is the right inversion. It's the same principle as GP-097 (compress N-D to 1D before synthesis, don't upgrade synthesizer for N-D).

**Where I agree:**

The Kinematic Compressor (differentiate data, not integrate hypothesis) is a genuine inversion. For dZ/dt = f(Z, X), computing Z-dot via Savitzky-Golay or finite differences produces a static dataset (Z, X, Z-dot). The engine treats Z-dot as the target variable and finds Z-dot = f(Z, X). This converts an ODE recovery problem to an algebraic recovery problem without any new solver infrastructure.

The VST (warp data to flatten noise) is also a genuine inversion. If variance scales with mean, a log or Anscombe transform stabilizes it. The engine runs on the transformed data. The final law is expressed in original coordinates via deterministic inverse.

**Where Gemini has blind spots:**

**Blind spot 1: Differentiation amplifies noise (the coupling problem).** Numerical differentiation is an ill-conditioned operation. For data with noise amplitude sigma, finite differences produce derivative estimates with noise O(sigma/h) where h is the step size. If sigma scales with magnitude (heteroscedastic), the derivative noise is worst precisely where the signal is largest. This means applying the Kinematic Compressor to heteroscedastic data produces a dataset where the noise profile is not just heteroscedastic but *amplified* heteroscedastic. The VST must run *before* the Kinematic Compressor, not after. Order of operations matters.

**Blind spot 2: VST requires knowing the noise model (chicken-and-egg).** The Anscombe transform assumes Poisson noise. The log transform assumes multiplicative noise. Wrong choice corrupts the topology — log-transforming additive-Gaussian data warps the function shape. But you don't know the noise model until you know the law, and you don't know the law until you've run the engine. This is a circular dependency Gemini glosses over.

**Blind spot 3: ODE detection is not trivial.** How does the preprocessor know the substrate is a dynamical system? The evidence is just (X, Z) pairs. If X happens to be time and Z(t) depends on Z(t-1), the evidence looks identical to a static function Z = g(X) with complex shape. The preprocessor needs a *detection* mechanism, not just a *transform* mechanism.

**Requesting domain expert review on:**
- Is the coupling between differentiation and heteroscedasticity as dangerous as I claim?
- Can VST selection be automated without knowing the law?
- How do you detect that a substrate is a dynamical system from evidence alone?
- Should these transforms be mandatory preprocessing or opt-in rubric flags?

### Turn 2 — Munger Multidisciplinary (2026-04-19 09:30:00 EST) — Two strong inversions, one structural trap

**Inversion check on the Kinematic Compressor: passed.** "Differentiate data, don't integrate hypothesis" is the correct inversion. Integration of an LLM-hallucinated formula is epistemically reckless — the formula may diverge, blow up, or oscillate, and you'd be comparing integrated garbage against ground truth. Differentiation of observed data is bounded and observable. The epistemic risk is in the numerics (noise amplification), not the architecture.

**Inversion check on VST: half-passed.** The inversion is correct *if you know which transform to apply*. But Gemini's proposal assumes you know the noise model a priori: "If Poisson → Anscombe. If multiplicative → log." This is the man-with-a-hammer in disguise. You don't have a hammer for noise you can't identify.

**The structural trap: model selection without a model.** Choosing between Anscombe and log-transform is a model selection problem. The standard statistical approach: fit the data under each noise model, compare likelihoods (AIC/BIC). But fitting the data requires knowing the functional form. You're back in the circle.

**The Mungerian exit:** Don't select a noise model. Run the engine under *all plausible transforms* and let the holdout adjudicate. This is the same resolution as GP-097 Q3 (try all variable orderings): when selection is epistemically unsound, enumerate and falsify.

Concretely:
1. Run the engine on raw data (assume homoscedastic)
2. Run the engine on log-transformed data (assume multiplicative noise)
3. Run the engine on sqrt-transformed data (assume Poisson)
4. Each run produces a candidate law in transformed coordinates
5. Inverse-transform each candidate back to original coordinates
6. Evaluate all candidates on the holdout in *original* coordinates

The candidate that passes the holdout wins. No noise model selection needed. The holdout does the selection for free.

**Cost analysis:** Three parallel runs of the engine. At current cost ($5-10 per 1D run), this is $15-30. Expensive but not prohibitive. If you want to be cheaper: run a quick 3-iteration scan under each transform to identify which converges fastest, then commit budget to that one.

**On the ordering question (Claude's blind spot 1):** Claude is right that VST must precede differentiation. But there's a deeper issue: if you enumerate all transforms (my proposal), and one of those transforms is log + differentiate, you've covered the coupling case. Enumeration dissolves the ordering problem — you just try all orderings.

### Turn 3 — Symbolic Regression Expert (2026-04-19 09:30:00 EST) — ODE detection has a cheap statistical test

**On ODE detection (Claude's blind spot 3):**

The detection question is: "Is this dataset a time series where Z(t) depends on Z(t-1), or is it a static function Z = f(X)?"

Statistical test: **autocorrelation of residuals.** Fit the best available model (could be the current champion, or a simple polynomial). Compute residuals. If the residuals show strong autocorrelation (Durbin-Watson test, D-W < 1.0), the data has temporal structure — it's likely a dynamical system. If residuals are uncorrelated (D-W ≈ 2.0), the data is consistent with independent samples.

This is a standard econometrics diagnostic. It costs one regression + one Durbin-Watson computation. Negligible.

**Caveats:** The test works only if the independent variable has a natural ordering (like time). If X is temperature and the evidence points are scrambled, autocorrelation is meaningless. The detection must first check whether the independent variable has a meaningful sequence order (monotonically increasing, equally spaced, etc.).

**On VST selection (Claude's blind spot 2):**

Agree with Munger: enumerate, don't select. But I'd go further — the enumeration should be small and fixed:

| Transform | Assumption | Inverse |
|---|---|---|
| Identity | Homoscedastic | Z |
| log(Z) | Multiplicative noise | exp(Z') |
| sqrt(Z) | Poisson noise | Z'² |
| Z / std_local(Z) | Generic heteroscedastic | Z' × std_local |

Four transforms. Each is a one-line operation. The cost of trying all four is negligible compared to the synthesis run.

The fourth (local standardization) is a nonparametric VST — divide by local standard deviation estimated in a sliding window. It handles arbitrary heteroscedasticity without model assumptions. Downside: it's a window-based transform, so the inverse is approximate, not exact. This may fail the deterministic-inverse constraint from GP-097.

**On the Pareto front:** For most ZTARE substrates (20-50 points), VST selection is dominated by enumeration. Only for very expensive synthesis (>100 points, N-D) would it be worth adding a pre-filter to avoid running all four.

### Turn 4 — Philosophy of Science (2026-04-19 09:30:00 EST) — The transform IS the coordinate system; observation vs. oracle check

**Epistemological status check:** Is warping evidence an observation or an oracle leak?

Verdict: **observation with a caveat.** A variance-stabilizing transform is a coordinate change — it's the same data expressed in a different basis. Like converting Cartesian to polar coordinates, it doesn't add information. The law is the same in both coordinate systems. So the transform is observation-safe.

**The caveat:** The *choice* of transform carries a theoretical commitment. Choosing log-transform commits you to the hypothesis that noise is multiplicative. If the noise is actually additive-Gaussian, log-transforming warps the function shape and the engine discovers a warped law. The warped law passes the holdout in transformed coordinates but fails in original coordinates.

This is the same problem as GP-097's compression ambiguity: the holdout must evaluate in *original* coordinates, not transformed coordinates. The Munger enumeration + original-coordinates-holdout resolves this.

**Crucial experiment design for ODE recovery:**

The test substrate must be:
1. A first-order ODE with known analytical solution (for GT comparison)
2. The analytical solution must *not* be a simple exponential (exponentials are already in the library; the engine would find the trajectory without needing ODE awareness)
3. The substrate should feature a nonlinear right-hand side (e.g., dZ/dt = Z(1-Z) — logistic growth, solution is sigmoid)

Logistic growth is ideal: the trajectory Z(t) = 1/(1+exp(-t)) looks like a sigmoid (already in the library), but the *governing equation* is dZ/dt = Z - Z², which is a polynomial in Z alone. The Kinematic Compressor should discover the polynomial, not the sigmoid.

**Second crucial experiment:** Feed the engine a static dataset that *looks* dynamical (monotonically increasing X, smooth Z(X)). The ODE detector should *not* trigger. If it triggers on every monotone function, the detector has a false-positive problem that wastes budget on unnecessary differentiation.

### Turn 5 — Systems Engineering / ML (2026-04-19 09:30:00 EST) — Pipeline architecture and oracle budget

**Oracle contamination analysis:**

All four transforms (identity, log, sqrt, local-std) operate only on the evidence values Z. They do not reference GT, variable names, or domain knowledge. Information budget: 0 bits from oracle. Clean.

Savitzky-Golay differentiation operates on the evidence (X, Z) pairs. It computes a local polynomial fit and differentiates analytically. No GT reference. Clean.

The Durbin-Watson ODE detection operates on model residuals — derived from evidence and the current champion fit. No GT reference. Clean.

**Pipeline placement:**

The evidence compressor should run *before* GP-097's manifold compressor. The chain is:

```
evidence.txt
     │
     ▼
GP-098: Evidence Compressor
├── VST (if heteroscedastic detected or enumerated)
├── Kinematic (if ODE detected)
└── Identity (passthrough)
     │
     ▼
GP-097: Manifold Compressor (N-D → 1D)
     │
     ▼
1D Synthesizer (Component D)
```

This ordering is correct because:
- VST must precede differentiation (noise amplification)
- Differentiation must precede N-D compression (the derivative is a new variable)
- N-D compression must precede 1D synthesis (GP-097's architecture)

**The inverse chain:** After synthesis, decompression is the reverse:
1. Decompress from 1D to N-D (GP-097 inverse)
2. Un-differentiate if Kinematic was applied (express ODE, not trajectory)
3. Inverse-VST to express in original coordinates

**Fail-safe:** If the VST + Kinematic chain produces a candidate that fails holdout in original coordinates, the pipeline should fall through to the next transform in the enumeration. The enumeration IS the fail-safe.

**Cost estimate:** Four VST variants × (with/without Kinematic) = 8 pipeline configurations. At 3 quick-scan iterations each (~$2/run), total exploration cost is ~$16. Only the winning configuration gets the full budget. Acceptable.

### Turn 6 — Validator Hardening (2026-04-19 09:30:00 EST) — Gate adaptation is the decisive concern

**The real vulnerability is not in the transform — it's in the gates.**

Even without transforms, the current absolute-threshold gates are already a latent failure mode on real-world data. The transforms are a workaround for gates that should arguably be relative-threshold from the start.

**Proposal: dual-mode gates.** Instead of choosing between absolute and relative thresholds, make the gates report *both*:
- Absolute residual: |Z_pred - Z_obs| < epsilon_abs
- Relative residual: |Z_pred - Z_obs| / max(|Z_obs|, epsilon_floor) < epsilon_rel

The current gates use only absolute. Adding relative as a logged diagnostic (not a hard gate) for 3 sandbox runs would generate the empirical data to decide whether relative gates should replace or supplement absolute ones.

This is cheaper and more testable than the full VST pipeline. It addresses the homoscedasticity trap directly at the gate level, not indirectly via data transforms.

**On ODE detection (Durbin-Watson):**

The D-W test is a good starting point but has known weaknesses:
- It only detects first-order autocorrelation (AR(1)). Higher-order dynamics (Z depends on Z(t-2)) won't trigger it.
- It requires the residuals from a fitted model. If the fitted model is a polynomial (which the engine tries early), polynomial residuals against an ODE trajectory may not show autocorrelation — the polynomial approximates the trajectory well locally.

A more robust detection: check whether the *fit quality improves monotonically as you add data points in sequence order vs. random order*. If sequential-order fitting is significantly better, the data has temporal structure.

**Phasing constraint:** Like GP-097, the gates must ship before any claims. Specifically: if a rubric declares `substrate_type: "dynamical"` or `noise_model: "heteroscedastic"`, the corresponding preprocessor must be active. Running a declared-heteroscedastic substrate through homoscedastic gates without the transform is a known-unsound configuration.

### Turn 7 — Claude (2026-04-19 09:30:00 EST) — Convergence synthesis

The debate converges on architecture but reveals a priority split.

**Consensus items:**

1. **Warp data, don't modify engine.** All experts agree. The transforms are coordinate changes, not oracle leaks. The engine stays a 1D static homoscedastic solver. Everything else is preprocessing.

2. **Enumerate transforms, don't select.** Run the engine under identity + log + sqrt (+ optionally local-std), evaluate all candidates in original coordinates on the holdout. The holdout adjudicates. No noise model selection needed.

3. **VST before Kinematic.** If both apply, VST runs first (stabilize noise → then differentiate). The enumeration covers all orderings.

4. **Pipeline ordering: GP-098 → GP-097 → 1D synthesis.** Evidence Compressor preprocesses before Manifold Compressor.

5. **Holdout in original coordinates.** Non-negotiable. Same principle as GP-097.

6. **Savitzky-Golay for differentiation.** Standard, well-understood, bounded noise amplification. Not finite differences (too noisy), not spectral methods (overkill).

**Open disagreements needing resolution:**

**Q1 (ODE detection): Durbin-Watson vs. sequential-vs-random fit improvement?**
SR expert proposes D-W (cheap, standard). Validator Hardening proposes sequential-vs-random fit (more robust, more expensive). Both have merit. The question is whether D-W's false negatives are acceptable for a first implementation.

**Q2 (Gate reform): transforms vs. relative gates?**
Validator Hardening argues that relative-threshold gates address the homoscedasticity trap more directly than VSTs. The VST pipeline is a data-level workaround for a gate-level problem. Should we fix the gates instead of warping the data? Or both?

**Q3 (Local-std inverse): exact vs. approximate?**
SR expert's fourth VST (divide by local standard deviation) handles arbitrary heteroscedasticity but has an approximate inverse. GP-097 established that inverse maps must be deterministic and exact. Should we include local-std despite violating this constraint?

**Q4 (Scope boundary): dynamical systems in scope for v1?**
The Kinematic Compressor is architecturally elegant but no ZTARE substrate to date has been a dynamical system. Is this premature architecture? Should v1 be VST-only, with the Kinematic Compressor deferred to when a real ODE substrate demands it?

**Q5 (Cost): enumeration acceptable at scale?**
Eight pipeline configurations × 3 quick-scan iterations = ~$16 exploration cost. Acceptable for one-off research runs. But if ZTARE becomes a product (WB-001), this cost multiplies by every substrate. Should the enumeration include a cheap pre-filter (e.g., Breusch-Pagan test for heteroscedasticity) to avoid unnecessary runs?

### Turn 8 — Munger Multidisciplinary (2026-04-19 09:30:00 EST) — Resolution proposals for Q1-Q5

**Q1 (ODE detection): Start with D-W, log the sequential test.**
ZTARE's philosophy is: ship the cheapest thing that works, instrument it, promote when empirical data demands it. D-W costs one regression. Sequential-vs-random costs two regressions. The difference is a 2× in detection cost. Start with D-W. If it produces false negatives on a real ODE substrate, the sequential test is already designed — promote it. Don't build robust detection for a regime we haven't entered yet.

The deeper Mungerian question: do we even need ODE *detection*? If we enumerate (identity + Kinematic), the Kinematic variant will produce better holdout scores on ODE substrates and worse scores on static substrates. The holdout selects for us. Detection is an optimization to avoid wasting budget, not a correctness requirement.

**Q2 (Gate reform vs. VST): Both, phased.**
Relative gates are the right long-term fix. VSTs are the right short-term fix. They're not competing — they address the same problem at different layers.

Phase 1: VST enumeration (ship now, works immediately, no gate changes).
Phase 2: Add relative residual as logged diagnostic on all runs (3 sandbox runs of data collection).
Phase 3: If relative residual proves more discriminating than absolute, promote to hard gate. At that point, VST becomes optional — the gates handle heteroscedasticity directly.

The incentive structure is correct: Phase 1 gives immediate protection, Phase 2 collects evidence, Phase 3 makes a data-driven decision about whether to keep the VST layer or let relative gates subsume it.

**Q3 (Local-std inverse): Defer.**
If the inverse must be exact (GP-097 constraint, non-negotiable), and local-std has approximate inverse, local-std violates a decisive constraint. Don't include it. The three exact-inverse transforms (identity, log, sqrt) cover the most common noise models. If a substrate has noise that none of these handle, that's a finding (the apparatus has reached its noise-model boundary), not a bug.

Man-with-a-hammer check: "but what if we need nonparametric VST?" — if you need nonparametric, you don't know the noise model, which means you don't know the coordinate system, which means you shouldn't be transforming the data. The honest answer is: report the noise as a confound and let the operator decide.

**Q4 (Scope boundary): VST in v1, Kinematic in v2.**
No ZTARE substrate has been a dynamical system. Building the Kinematic Compressor now is engineering for a hypothetical. Build the VST pipeline (it addresses a real problem: the homoscedasticity trap is active on GP-097's ratio sweep right now). When a real ODE substrate arrives, the architecture is designed to accept the Kinematic module — but don't build it until then.

This is the "no speculative abstractions" principle. The VST is decisive today. The Kinematic Compressor is decisive someday.

**Q5 (Cost): Pre-filter with Breusch-Pagan for productization.**
For research runs: enumerate all transforms, $16 is negligible. For WB-001 product: add a Breusch-Pagan test ($0.001 cost) as a pre-filter. If the test rejects homoscedasticity at p < 0.05, run VST variants. If it accepts, run only identity. This reduces the product cost by 2-3× for homoscedastic substrates (the majority).

The pre-filter is an optimization, not a correctness mechanism. If it's wrong (false acceptance), the engine runs on raw data and may produce slightly worse holdout scores. It doesn't produce wrong answers — it just wastes budget on the wrong transform.

### Turn 9 — Claude (2026-04-19 09:30:00 EST) — Final convergence

All five questions have resolution proposals. Let me check for consensus.

**Resolved:**

| Q | Resolution | Dissent? |
|---|---|---|
| Q1 (ODE detection) | D-W first, sequential-vs-random logged. Or: skip detection entirely, enumerate identity + Kinematic, let holdout select. | Munger's "skip detection" proposal is stronger — detection is optimization, not correctness |
| Q2 (Gate reform vs VST) | Both, phased. VST now (immediate protection), relative gates as logged diagnostic (data collection), promote after 3 runs | None |
| Q3 (Local-std) | Deferred. Violates exact-inverse constraint. Three exact-inverse transforms (identity, log, sqrt) cover common noise models | None |
| Q4 (Scope) | VST in v1, Kinematic Compressor deferred to when a real ODE substrate demands it | None |
| Q5 (Cost) | Enumerate for research. Breusch-Pagan pre-filter for product (WB-001) | None |

**New items from this round:**

1. **Kinematic Compressor deferred.** The architecture supports it but v1 doesn't build it. This simplifies the seam considerably — v1 is VST-only.

2. **Three transforms only.** Identity (passthrough), log, sqrt. No local-std (violates exact-inverse). Each has an exact deterministic inverse.

3. **Breusch-Pagan as future pre-filter.** Not in v1 (research mode enumerates). In WB-001 product mode, add as cost optimization.

4. **Relative gates as logged diagnostic.** Phase 2 work. Add |residual|/|Z| to gate output alongside |residual|. No behavior change. Data collection only.

**Seam status: converged on scope and architecture.** VST pipeline with three enumerated transforms, holdout in original coordinates, Kinematic deferred. Ready for spec if operator agrees.

**Remaining work for spec:**
- Exact pipeline code structure (where in autoresearch_loop.py the transforms fire)
- Transform enumeration logic (which transforms to try, how to manage parallel runs)
- Inverse-transform integration with GP-097 decompression chain
- Three validation substrates: one homoscedastic (baseline), one multiplicative noise, one Poisson noise
- Relative-gate diagnostic format (Phase 2)

## Recommendation

Adopt **VST enumeration** as the v1 evidence compressor. Three transforms (identity, log, sqrt), each with exact deterministic inverse. Enumerate all three, evaluate candidates in original coordinates on holdout. The holdout adjudicates noise model selection.

**Architecture (v1):**

```text
  evidence.txt
       │
       ▼
  ┌───────────────────────────────┐
  │  evidence_compressor.py       │
  │                               │
  │  For each transform in        │
  │  [identity, log, sqrt]:       │
  │  ├─ Apply transform to Z      │
  │  ├─ Pass to engine (or        │
  │  │   GP-097 compressor)       │
  │  ├─ Inverse-transform result  │
  │  └─ Evaluate on holdout in    │
  │      original coordinates     │
  │                               │
  │  Select best candidate        │
  │  (holdout score, not visible) │
  └───────────────────────────────┘
       │
       ▼
  GP-097 Manifold Compressor
  (if N-D)
       │
       ▼
  1D Synthesizer
```

**Key design decisions (all resolved in debate):**
1. Warp data, don't modify engine
2. Enumerate transforms, don't select noise model
3. Three exact-inverse transforms only (identity, log, sqrt)
4. Holdout in original coordinates (non-negotiable)
5. VST in v1, Kinematic Compressor deferred
6. Relative gates as logged diagnostic (Phase 2)
7. Breusch-Pagan pre-filter deferred to WB-001 product mode
8. No local-std (violates exact-inverse constraint)

**Deferred (v2 or later):**
- Kinematic Compressor for ODE substrates (when a real substrate demands it)
- ODE detection (D-W or sequential-vs-random)
- Relative gate promotion (after 3 sandbox runs)
- Local-std VST (if exact-inverse constraint is relaxed)
- Breusch-Pagan pre-filter (WB-001 product mode)
